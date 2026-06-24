"""Discover and register predefined SQL-backed tools."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from ..db import fetch_all

# A query opts into runtime filtering by embedding this marker where the
# generated `AND ...` conditions should be spliced in. Because it is a SQL
# comment, a query file with the marker is still valid SQL on its own (handy
# for debugging) and simply applies no filter when run directly.
FILTER_MARKER = "/* FILTERS */"

# Column references come from the trusted in-repo .toml sidecars, but we still
# validate them so a typo can never produce malformed (or injectable) SQL.
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class PredefinedTool:
    """A SQL query exposed as an MCP tool, declared via a .sql + .toml pair.

    `car_column`/`date_column` (from the optional `[filters]` table in the
    sidecar) name the columns the runtime filters bind against. `default_days`
    supplies a default look-back window applied only when no explicit
    `start_date` is given, so heavy positions/drives scans stay bounded by
    default while callers can still widen or narrow the range at will.
    """

    name: str
    description: str
    sql: str
    source: str  # filename, for diagnostics
    car_column: str | None = None
    date_column: str | None = None
    default_days: int | None = None


def _queries_dir() -> Path:
    """Locate the bundled `queries/` directory inside the installed package."""
    resource = files("teslamate_mcp").joinpath("queries")
    with as_file(resource) as path:
        return Path(path)


def _safe_column(column: str, *, source: str) -> str:
    """Validate a sidecar-declared column reference before splicing it into SQL."""
    if not _IDENT.match(column):
        raise ValueError(f"{source}: invalid filter column {column!r}")
    return column


def discover_predefined_tools(directory: Path | None = None) -> list[PredefinedTool]:
    """Scan a directory for .sql files and load each one's sidecar .toml metadata.

    Each .sql file must have a sibling .toml with `name` and `description` keys.
    Missing sidecars raise FileNotFoundError so misconfiguration fails fast at
    startup rather than silently producing a half-empty tool list.

    An optional `[filters]` table declares the columns that the `car_id` /
    `start_date` / `end_date` parameters bind against.
    """
    base = directory or _queries_dir()
    tools: list[PredefinedTool] = []
    for sql_path in sorted(base.glob("*.sql")):
        toml_path = sql_path.with_suffix(".toml")
        if not toml_path.exists():
            raise FileNotFoundError(
                f"Missing sidecar metadata for {sql_path.name}: expected {toml_path.name}"
            )
        meta = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        try:
            name = meta["name"]
            description = meta["description"]
        except KeyError as exc:
            raise ValueError(f"{toml_path.name} is missing required key {exc.args[0]!r}") from exc

        filters = meta.get("filters", {})
        car_column = filters.get("car_column")
        date_column = filters.get("date_column")
        default_days = filters.get("default_days")
        if car_column is not None:
            car_column = _safe_column(car_column, source=toml_path.name)
        if date_column is not None:
            date_column = _safe_column(date_column, source=toml_path.name)
        if (car_column or date_column) and FILTER_MARKER not in sql_path.read_text(
            encoding="utf-8"
        ):
            raise ValueError(f"{sql_path.name} declares filters but has no {FILTER_MARKER} marker")

        tools.append(
            PredefinedTool(
                name=name,
                description=description,
                sql=sql_path.read_text(encoding="utf-8"),
                source=sql_path.name,
                car_column=car_column,
                date_column=date_column,
                default_days=default_days,
            )
        )
    return tools


def build_filter_clause(
    tool: PredefinedTool,
    *,
    car_id: int | None,
    start_date: str | None,
    end_date: str | None,
) -> tuple[str, list[Any]]:
    """Build the `AND ...` fragment and ordered params for the requested filters.

    Values are always emitted as `%s` placeholders (never interpolated); only
    the trusted, pre-validated column names are formatted into the SQL text.
    """
    conditions: list[str] = []
    params: list[Any] = []

    if car_id is not None:
        if not tool.car_column:
            raise ValueError(f"{tool.name} does not support filtering by car_id")
        conditions.append(f"AND {tool.car_column} = %s")
        params.append(car_id)

    if (start_date is not None or end_date is not None) and not tool.date_column:
        raise ValueError(f"{tool.name} does not support filtering by date")

    if tool.date_column:
        for label, value in (("start_date", start_date), ("end_date", end_date)):
            if value is not None and not _DATE.match(value):
                raise ValueError(f"{label} must be in YYYY-MM-DD format, got {value!r}")

        if start_date is not None:
            conditions.append(f"AND {tool.date_column} >= %s::date")
            params.append(start_date)
        elif tool.default_days is not None:
            conditions.append(f"AND {tool.date_column} >= CURRENT_DATE - make_interval(days => %s)")
            params.append(tool.default_days)

        if end_date is not None:
            # Exclusive upper bound on the day after, so a date end is inclusive.
            conditions.append(f"AND {tool.date_column} < (%s::date + INTERVAL '1 day')")
            params.append(end_date)

    return " ".join(conditions), params


def render_sql(sql: str, clause: str, params: list[Any]) -> str:
    """Splice the filter clause into the query, escaping literal `%` when binding.

    psycopg only treats `%` as a placeholder marker when params are bound, so a
    literal `%` in the static SQL (e.g. "100%" in a comment) must be doubled
    first. The clause is spliced in afterwards so its own `%s` markers survive.
    """
    sql_text = sql.replace("%", "%%") if params else sql
    if FILTER_MARKER in sql_text:
        return sql_text.replace(FILTER_MARKER, clause)
    return sql_text


def register_predefined_tools(mcp: FastMCP, tools: list[PredefinedTool]) -> None:
    """Attach each predefined tool to the FastMCP server.

    A small factory captures the SQL per tool so the registered coroutine
    closes over only its own query — without a factory, every registered
    coroutine would share the loop variable and run the same SQL.
    """
    annotations = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    for tool in tools:
        _register_one(mcp, tool, annotations)


async def _execute(
    tool: PredefinedTool,
    ctx: Context,
    *,
    car_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Splice in any requested filters and run the tool's query."""
    clause, params = build_filter_clause(
        tool, car_id=car_id, start_date=start_date, end_date=end_date
    )
    final_sql = render_sql(tool.sql, clause, params)

    pool = ctx.request_context.lifespan_context.pool
    await ctx.info(f"Running {tool.name} ({tool.source})" + (f" with {clause}" if clause else ""))
    rows = await fetch_all(pool, final_sql, tuple(params) or None)
    await ctx.info(f"{tool.name} returned {len(rows)} row(s)")
    return rows


_CAR_ID_FIELD = Field(
    default=None,
    description="Limit results to a single car by its TeslaMate car id (the `cars.id` column).",
)
_START_DATE_FIELD = Field(
    default=None,
    description="Inclusive lower bound on the date range, formatted YYYY-MM-DD.",
)
_END_DATE_FIELD = Field(
    default=None,
    description="Inclusive upper bound on the date range, formatted YYYY-MM-DD.",
)


def _register_one(mcp: FastMCP, tool: PredefinedTool, annotations: ToolAnnotations) -> None:
    # Expose only the parameters the query can actually honour, so the tool
    # schema never advertises a filter that would just raise at call time.
    if tool.date_column:

        async def handler(
            ctx: Context,
            car_id: int | None = _CAR_ID_FIELD,
            start_date: str | None = _START_DATE_FIELD,
            end_date: str | None = _END_DATE_FIELD,
        ) -> list[dict[str, Any]]:
            return await _execute(
                tool, ctx, car_id=car_id, start_date=start_date, end_date=end_date
            )

    elif tool.car_column:

        async def handler(  # type: ignore[misc]
            ctx: Context,
            car_id: int | None = _CAR_ID_FIELD,
        ) -> list[dict[str, Any]]:
            return await _execute(tool, ctx, car_id=car_id)

    else:

        async def handler(ctx: Context) -> list[dict[str, Any]]:  # type: ignore[misc]
            return await _execute(tool, ctx)

    handler.__name__ = tool.name
    handler.__doc__ = tool.description
    handler.__annotations__["ctx"] = Context
    mcp.tool(name=tool.name, description=tool.description, annotations=annotations)(handler)
