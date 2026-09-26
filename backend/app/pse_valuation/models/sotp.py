"""Attributable parent-equity NAV/SOTP aggregator."""

from __future__ import annotations

from typing import Any


def sotp_valuation(
    *,
    components: list[dict[str, Any]],
    shares_outstanding: float,
    parent_cash: float = 0.0,
    parent_debt: float = 0.0,
    present_value_parent_costs: float = 0.0,
    other_parent_assets: float = 0.0,
    other_parent_claims: float = 0.0,
) -> dict[str, Any]:
    if not components:
        raise ValueError("components must not be empty")
    if shares_outstanding <= 0:
        raise ValueError("shares_outstanding must be positive")

    rows: list[dict[str, Any]] = []
    attributable_total = 0.0
    names: set[str] = set()
    for component in components:
        name = component.get("name")
        equity_value = component.get("equity_value")
        ownership = component.get("ownership")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("every SOTP component needs a unique name")
        if not isinstance(equity_value, (int, float)):
            raise ValueError(f"{name}: equity_value is missing")
        if not isinstance(ownership, (int, float)) or not 0 <= ownership <= 1:
            raise ValueError(f"{name}: ownership must be between 0 and 1")
        names.add(name)
        attributable = float(equity_value) * float(ownership)
        attributable_total += attributable
        rows.append(
            {
                "name": name,
                "equity_value": float(equity_value),
                "ownership": float(ownership),
                "attributable_equity_value": attributable,
            }
        )

    common_equity_value = (
        attributable_total
        + parent_cash
        + other_parent_assets
        - parent_debt
        - present_value_parent_costs
        - other_parent_claims
    )
    return {
        "model": "sotp",
        "components": rows,
        "attributable_component_value": attributable_total,
        "common_equity_value": common_equity_value,
        "value_per_share": common_equity_value / shares_outstanding,
    }

