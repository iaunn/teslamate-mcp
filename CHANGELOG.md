# Changelog

All notable changes to this project are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Optional `car_id`, `start_date`, and `end_date` parameters on the predefined query tools. Each tool exposes only the filters it can honour (drive/charge/position-based tools get all three; "latest snapshot" and car-info tools get `car_id` only). Filter columns are declared per query in a `[filters]` table in each `.toml` sidecar and spliced into the SQL at a `/* FILTERS */` marker; values are always passed as bound parameters, and column names are validated against an identifier allowlist.
- Unit tests covering filter-clause building, default-window override semantics, malformed-date rejection, unsupported-filter errors, and per-tool schema exposure.

### Changed
- The four queries that previously hard-coded a look-back window (battery degradation 24mo, daily battery usage 30d, monthly efficiency 12mo, tire pressure 90d) now apply that window as a `default_days` default that an explicit `start_date` overrides, so callers can widen or narrow the range instead of being silently capped.

## [0.3.1] - 2026-05-21

### Fixed
- FastMCP exposed the internal `Context` parameter (`ctx`) as a required client-facing tool argument on every tool, so MCP clients failed every call with `ctx Field required`. `from __future__ import annotations` made FastMCP see the annotation as a string and miss the Context-detection branch; the fix patches `__annotations__["ctx"]` back to the real `Context` class before registering each tool. ([#7](https://github.com/cobanov/teslamate-mcp/pull/7))

### Added
- Regression test that constructs the server and asserts `ctx` is absent from every tool's MCP-facing `inputSchema` while `run_sql` still requires `query`.

## [0.3.0] - 2026-05-21

### Added
- Single `teslamate-mcp` console script with `stdio`, `http`, `gen-token`, and `list-tools` subcommands.
- `src/teslamate_mcp` package using a proper src-layout, distributable via hatchling.
- Six MCP prompts for common analyses: battery health, driving summary, charging behaviour, anomalies, weather efficiency, and a quick status report.
- Two MCP resources: `teslamate://queries` (index) and `teslamate://queries/{name}` (raw SQL per tool).
- `Context.info`/`Context.warning` streaming from every tool, including elapsed time on `run_sql`.
- `/health` liveness route and Docker `HEALTHCHECK`.
- Multi-stage Dockerfile producing a slim runtime image with OCI labels.
- Release workflow: pushing a `v*` tag builds and publishes a multi-arch image to GHCR and opens a GitHub release.
- GitHub Actions CI: ruff lint/format check, pytest on Python 3.11/3.12/3.13, Docker build smoke test.
- pytest suite with testcontainers-backed Postgres for end-to-end coverage of the read-only execution path.

### Changed
- `run_sql` now runs inside a PostgreSQL `READ ONLY` transaction with `statement_timeout`, `lock_timeout`, and `idle_in_transaction_session_timeout` enforced via `SET LOCAL`. When the user omits `LIMIT`, the query is wrapped in a capped subselect.
- `get_database_schema` reads `information_schema` at runtime instead of a checked-in JSON snapshot.
- Decimal column values are serialised as `float` so language models can do arithmetic on them.
- Bearer-token comparison switched to `hmac.compare_digest` (timing-safe).
- Configuration moved to `pydantic-settings` with full `.env` support.

### Removed
- `main.py` and `main_remote.py` (replaced by the CLI subcommands).
- `utils/generate_token.py` (replaced by `teslamate-mcp gen-token`).
- `data/all_db_info.json` (replaced by live introspection).
- Direct dependency on the standalone `fastmcp` PyPI package; the project now uses only the official `mcp[cli]` SDK.

## [0.2.0]

Previous baseline. See git history for details.
