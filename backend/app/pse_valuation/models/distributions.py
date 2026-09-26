"""Sustainable-distribution valuation for REITs and similar vehicles."""

from __future__ import annotations

from typing import Any


def distribution_valuation(
    *,
    current_distribution_per_share: float,
    explicit_growth: float,
    cost_of_equity: float,
    terminal_growth: float | None = None,
    forecast_years: int = 5,
    finite_life_years: int | None = None,
) -> dict[str, Any]:
    if current_distribution_per_share < 0:
        raise ValueError("current_distribution_per_share must not be negative")
    if cost_of_equity <= -1:
        raise ValueError("cost_of_equity must exceed -100%")
    if forecast_years < 1 or forecast_years > 30:
        raise ValueError("forecast_years must be between 1 and 30")
    if finite_life_years is not None and finite_life_years != forecast_years:
        raise ValueError("finite_life_years must equal the explicit forecast horizon")

    distribution = current_distribution_per_share
    pv_distributions = 0.0
    schedule: list[dict[str, float | int]] = []
    for year in range(1, forecast_years + 1):
        distribution *= 1 + explicit_growth
        present_value = distribution / (1 + cost_of_equity) ** year
        pv_distributions += present_value
        schedule.append(
            {"year": year, "distribution_per_share": distribution, "present_value": present_value}
        )

    terminal_value = 0.0
    pv_terminal = 0.0
    if finite_life_years is None:
        if terminal_growth is None:
            raise ValueError("continuing distributions require terminal_growth")
        if cost_of_equity <= terminal_growth:
            raise ValueError("cost_of_equity must exceed terminal_growth")
        next_distribution = distribution * (1 + terminal_growth)
        terminal_value = next_distribution / (cost_of_equity - terminal_growth)
        pv_terminal = terminal_value / (1 + cost_of_equity) ** forecast_years
    return {
        "model": "sustainable_distributions",
        "value_per_share": pv_distributions + pv_terminal,
        "present_value_distributions": pv_distributions,
        "terminal_value": terminal_value,
        "present_value_terminal": pv_terminal,
        "schedule": schedule,
        "finite_life": finite_life_years is not None,
    }
