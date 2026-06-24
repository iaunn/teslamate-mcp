"""Unit tests for predefined-tool discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from teslamate_mcp.config import Settings
from teslamate_mcp.server import create_server
from teslamate_mcp.tools.registry import (
    FILTER_MARKER,
    PredefinedTool,
    build_filter_clause,
    discover_predefined_tools,
)


def test_discover_finds_all_eighteen_bundled_tools() -> None:
    tools = discover_predefined_tools()
    names = {t.name for t in tools}
    assert len(tools) == 18
    # Spot-check that a few expected tools are present.
    assert "get_basic_car_information" in names
    assert "get_battery_health_summary" in names
    assert "get_unusual_power_consumption" in names


def test_each_tool_has_nonempty_metadata() -> None:
    for tool in discover_predefined_tools():
        assert tool.name.startswith("get_")
        assert len(tool.description) > 20
        assert tool.sql.strip().upper().startswith(("SELECT", "WITH"))


def test_missing_sidecar_raises(tmp_path: Path) -> None:
    (tmp_path / "orphan.sql").write_text("SELECT 1", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Missing sidecar"):
        discover_predefined_tools(tmp_path)


def test_malformed_sidecar_raises(tmp_path: Path) -> None:
    (tmp_path / "q.sql").write_text("SELECT 1", encoding="utf-8")
    (tmp_path / "q.toml").write_text('name = "x"\n', encoding="utf-8")  # missing description
    with pytest.raises(ValueError, match="description"):
        discover_predefined_tools(tmp_path)


@pytest.mark.asyncio
async def test_tool_schemas_do_not_expose_context_argument() -> None:
    settings = Settings(database_url="postgresql://teslamate:secret@example.test/teslamate")  # type: ignore[call-arg]
    mcp = create_server(settings)

    tools = {tool.name: tool for tool in await mcp.list_tools()}

    for name in [
        "get_basic_car_information",
        "get_database_schema",
        "run_sql",
    ]:
        schema = tools[name].inputSchema
        assert "ctx" not in schema.get("properties", {})
        assert "ctx" not in schema.get("required", [])
    assert tools["run_sql"].inputSchema["required"] == ["query"]


# --- Filter metadata and clause building -----------------------------------


def test_every_bundled_tool_supports_car_filtering() -> None:
    for tool in discover_predefined_tools():
        assert tool.car_column, f"{tool.name} should declare a car_column"
        assert FILTER_MARKER in tool.sql, f"{tool.name} is missing the {FILTER_MARKER} marker"


@pytest.mark.asyncio
async def test_filterable_tools_expose_only_supported_params() -> None:
    settings = Settings(database_url="postgresql://teslamate:secret@example.test/teslamate")  # type: ignore[call-arg]
    mcp = create_server(settings)
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    # A drive-based tool filters by both car and date.
    assert set(tools["get_monthly_driving_summary"].inputSchema["properties"]) == {
        "car_id",
        "start_date",
        "end_date",
    }
    # A "latest snapshot" tool only filters by car.
    assert set(tools["get_current_car_status"].inputSchema["properties"]) == {"car_id"}
    assert set(tools["get_basic_car_information"].inputSchema["properties"]) == {"car_id"}


_DRIVE = PredefinedTool(
    name="t",
    description="d",
    sql="SELECT 1 WHERE true /* FILTERS */",
    source="t.sql",
    car_column="d.car_id",
    date_column="d.start_date",
    default_days=365,
)
_CAR_ONLY = PredefinedTool(name="t", description="d", sql="...", source="t.sql", car_column="c.id")


def test_clause_combines_car_and_explicit_date_range() -> None:
    clause, params = build_filter_clause(
        _DRIVE, car_id=2, start_date="2024-01-01", end_date="2024-03-31"
    )
    assert clause == (
        "AND d.car_id = %s AND d.start_date >= %s::date "
        "AND d.start_date < (%s::date + INTERVAL '1 day')"
    )
    assert params == [2, "2024-01-01", "2024-03-31"]


def test_default_window_applies_only_without_start_date() -> None:
    clause, params = build_filter_clause(_DRIVE, car_id=None, start_date=None, end_date=None)
    assert clause == "AND d.start_date >= CURRENT_DATE - make_interval(days => %s)"
    assert params == [365]

    # An explicit start_date overrides the default window instead of stacking.
    clause, params = build_filter_clause(
        _DRIVE, car_id=None, start_date="2020-01-01", end_date=None
    )
    assert clause == "AND d.start_date >= %s::date"
    assert params == ["2020-01-01"]


def test_no_filters_yields_empty_clause() -> None:
    tool = PredefinedTool(name="t", description="d", sql="...", source="t.sql")
    assert build_filter_clause(tool, car_id=None, start_date=None, end_date=None) == ("", [])


def test_date_filter_rejected_when_unsupported() -> None:
    with pytest.raises(ValueError, match="does not support filtering by date"):
        build_filter_clause(_CAR_ONLY, car_id=None, start_date="2024-01-01", end_date=None)


def test_car_filter_rejected_when_unsupported() -> None:
    tool = PredefinedTool(name="t", description="d", sql="...", source="t.sql")
    with pytest.raises(ValueError, match="does not support filtering by car_id"):
        build_filter_clause(tool, car_id=1, start_date=None, end_date=None)


@pytest.mark.parametrize("bad", ["01-2024", "2024/01/01", "2024-1-1", "yesterday", ""])
def test_malformed_dates_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        build_filter_clause(_DRIVE, car_id=None, start_date=bad, end_date=None)


def test_sidecar_with_filters_but_no_marker_raises(tmp_path: Path) -> None:
    (tmp_path / "q.sql").write_text("SELECT 1", encoding="utf-8")  # no marker
    (tmp_path / "q.toml").write_text(
        'name = "get_q"\ndescription = "a long enough description here"\n'
        '[filters]\ncar_column = "c.id"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"no .* marker"):
        discover_predefined_tools(tmp_path)


def test_sidecar_with_invalid_column_raises(tmp_path: Path) -> None:
    (tmp_path / "q.sql").write_text(f"SELECT 1 WHERE true {FILTER_MARKER}", encoding="utf-8")
    (tmp_path / "q.toml").write_text(
        'name = "get_q"\ndescription = "a long enough description here"\n'
        '[filters]\ncar_column = "c.id; DROP TABLE cars"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid filter column"):
        discover_predefined_tools(tmp_path)
