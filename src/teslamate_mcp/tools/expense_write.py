"""Opt-in car-expense write tools (gated by Settings.enable_charging_writes).

Allows recording maintenance, tire rotation/replacement, insurance, and repairs
into `ledger.car_expenses`, automatically attaching the vehicle's odometer and GPS
coordinates from TeslaMate if omitted.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from mcp.server.mcpserver import (
    AcceptedElicitation,
    Context,
    Elicit,
    ElicitationResult,
    MCPServer,
    Resolve,
)
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from ..db import execute_query, execute_write

logger = logging.getLogger(__name__)

_LOOKUP_POSITION_SQL = """
SELECT
    ROUND(p.odometer::numeric, 2) AS odometer_km,
    ROUND(p.latitude::numeric, 6) AS latitude,
    ROUND(p.longitude::numeric, 6) AS longitude
FROM positions p
WHERE p.car_id = %(car_id)s
ORDER BY p.date DESC
LIMIT 1;
"""

_INSERT_EXPENSE_SQL = """
INSERT INTO ledger.car_expenses (
    car_id,
    expense_date,
    category,
    title,
    cost,
    odometer_km,
    latitude,
    longitude,
    details
) VALUES (
    %(car_id)s,
    %(expense_date)s::date,
    %(category)s,
    %(title)s,
    %(cost)s::numeric(10, 2),
    %(odometer_km)s::numeric(10, 2),
    %(latitude)s::numeric(10, 6),
    %(longitude)s::numeric(10, 6),
    %(details)s
)
RETURNING id AS expense_id,
    car_id,
    expense_date::text,
    category,
    title,
    cost,
    odometer_km,
    latitude,
    longitude,
    details;
"""


class ExpenseConfirmation(BaseModel):
    confirm: bool = Field(description="Approve writing this expense to the database.")


def _client_supports_form_elicitation(ctx: Context) -> bool:
    capabilities = ctx.client_capabilities
    elicitation = capabilities.elicitation if capabilities is not None else None
    return elicitation is not None and (elicitation.form is not None or elicitation.url is None)


async def _confirm_expense(
    ctx: Context, title: str, cost: float, category: str
) -> Elicit[ExpenseConfirmation] | ExpenseConfirmation:
    if not _client_supports_form_elicitation(ctx):
        return ExpenseConfirmation(confirm=True)
    return Elicit(
        f"Record {category} expense: '{title}' for {cost:.2f} THB?",
        ExpenseConfirmation,
    )


def register_expense_write_tools(mcp: MCPServer) -> None:
    annotations = ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    )

    description = (
        "Add a new car expense (maintenance, tire rotation, replacement, repair, insurance, or accessories) "
        "to the `ledger.car_expenses` table. If odometer_km, latitude, or longitude are omitted, they will "
        "automatically be populated from the vehicle's latest known position in TeslaMate."
    )

    async def add_car_expense(
        ctx: Context,
        confirmation: Annotated[ElicitationResult[ExpenseConfirmation], Resolve(_confirm_expense)],
        title: str = Field(
            ...,
            description="Short title of the expense (e.g. 'Tire Rotation & Balancing (สลับยาง)', 'Insurance renewal').",
        ),
        cost: float = Field(
            ...,
            ge=0,
            le=10000000,
            description="Expense amount in THB.",
        ),
        category: str = Field(
            default="MAINTENANCE",
            description="Category: 'TIRE', 'MAINTENANCE', 'REPAIR', 'INSURANCE', or 'ACCESSORY'.",
        ),
        expense_date: str | None = Field(
            default=None,
            description="Date of expense in ISO format (YYYY-MM-DD). Defaults to current date.",
        ),
        details: str | None = Field(
            default=None,
            description="Additional notes, shop name, invoice reference, or items replaced.",
        ),
        odometer_km: float | None = Field(
            default=None,
            description="Vehicle odometer in km at the time of expense. If omitted, uses vehicle's latest odometer.",
        ),
        latitude: float | None = Field(
            default=None,
            description="Latitude of shop/service location. If omitted, uses vehicle's latest position.",
        ),
        longitude: float | None = Field(
            default=None,
            description="Longitude of shop/service location. If omitted, uses vehicle's latest position.",
        ),
        car_id: int = Field(
            default=1,
            description="Car ID (default 1 for Juniper).",
        ),
    ) -> list[dict[str, Any]]:
        if not (isinstance(confirmation, AcceptedElicitation) and confirmation.data.confirm):
            raise ValueError("Confirmation declined; no expense was written.")

        pool = ctx.request_context.lifespan_context.pool

        # Look up latest position / odometer if omitted
        if odometer_km is None or latitude is None or longitude is None:
            pos_rows = await execute_query(pool, _LOOKUP_POSITION_SQL, {"car_id": car_id})
            if pos_rows:
                latest = pos_rows[0]
                if odometer_km is None and latest.get("odometer_km") is not None:
                    odometer_km = float(latest["odometer_km"])
                if latitude is None and latest.get("latitude") is not None:
                    latitude = float(latest["latitude"])
                if longitude is None and latest.get("longitude") is not None:
                    longitude = float(latest["longitude"])

        import datetime

        final_date = expense_date or datetime.date.today().isoformat()

        logger.info("Recording car expense '%s' (%.2f THB) for car %d", title, cost, car_id)
        rows = await execute_write(
            pool,
            _INSERT_EXPENSE_SQL,
            {
                "car_id": car_id,
                "expense_date": final_date,
                "category": category.upper().strip(),
                "title": title.strip(),
                "cost": cost,
                "odometer_km": odometer_km,
                "latitude": latitude,
                "longitude": longitude,
                "details": (details or "").strip(),
            },
        )
        return rows

    mcp.add_tool(
        add_car_expense,
        name="add_car_expense",
        description=description,
        annotations=annotations,
    )
