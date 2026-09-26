"""Common-equity residual-income model for banks and balance-sheet firms."""

from __future__ import annotations

from typing import Any


def residual_income_valuation(
    *,
    opening_common_equity: float,
    shares_outstanding: float,
    current_roe: float,
    terminal_roe: float,
    cost_of_equity: float,
    payout_ratio: float,
    terminal_growth: float,
    forecast_years: int = 5,
) -> dict[str, Any]:
    if opening_common_equity <= 0:
        raise ValueError("opening_common_equity must be positive")
    if shares_outstanding <= 0:
        raise ValueError("shares_outstanding must be positive")
    if not 0 <= payout_ratio <= 1:
        raise ValueError("payout_ratio must be between 0 and 1")
    if min(current_roe, terminal_roe, cost_of_equity) <= 0:
        raise ValueError("ROE and cost_of_equity must be positive")
    if cost_of_equity <= terminal_growth:
        raise ValueError("cost_of_equity must exceed terminal_growth")
    if terminal_growth >= terminal_roe:
        raise ValueError("terminal_growth must be below terminal_roe")
    if forecast_years < 1 or forecast_years > 30:
        raise ValueError("forecast_years must be between 1 and 30")

    book = opening_common_equity
    pv_residual_income = 0.0
    schedule: list[dict[str, float | int]] = []
    terminal_payout = 1 - terminal_growth / terminal_roe

    for year in range(1, forecast_years + 1):
        progress = year / forecast_years
        roe = current_roe + (terminal_roe - current_roe) * progress
        payout = payout_ratio + (terminal_payout - payout_ratio) * progress
        net_income = book * roe
        dividends = net_income * payout
        residual_income = net_income - cost_of_equity * book
        present_value = residual_income / (1 + cost_of_equity) ** year
        pv_residual_income += present_value
        closing_book = book + net_income - dividends
        schedule.append(
            {
                "year": year,
                "opening_common_equity": book,
                "roe": roe,
                "payout_ratio": payout,
                "net_income": net_income,
                "dividends": dividends,
                "residual_income": residual_income,
                "closing_common_equity": closing_book,
            }
        )
        book = closing_book

    next_residual_income = (terminal_roe - cost_of_equity) * book
    continuing_value = next_residual_income / (cost_of_equity - terminal_growth)
    pv_continuing = continuing_value / (1 + cost_of_equity) ** forecast_years
    common_equity_value = opening_common_equity + pv_residual_income + pv_continuing
    justified_pb = (terminal_roe - terminal_growth) / (cost_of_equity - terminal_growth)
    return {
        "model": "residual_income",
        "common_equity_value": common_equity_value,
        "value_per_share": common_equity_value / shares_outstanding,
        "present_value_forecast_residual_income": pv_residual_income,
        "present_value_continuing_residual_income": pv_continuing,
        "justified_pb": justified_pb,
        "schedule": schedule,
    }

