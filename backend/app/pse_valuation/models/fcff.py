"""Reinvestment-aware FCFF valuation for continuing or finite-life businesses."""

from __future__ import annotations

from typing import Any


def fcff_valuation(
    *,
    starting_nopat: float,
    growth_rate: float,
    roic: float,
    wacc: float,
    shares_outstanding: float,
    forecast_years: int = 5,
    terminal_growth: float | None = None,
    terminal_roic: float | None = None,
    finite_life_years: int | None = None,
    residual_value: float = 0.0,
    cash: float = 0.0,
    nonoperating_assets: float = 0.0,
    debt: float = 0.0,
    preferred_claims: float = 0.0,
    minority_value: float = 0.0,
    other_claims: float = 0.0,
) -> dict[str, Any]:
    """Return enterprise and common-equity value in the caller's units.

    Positive growth is funded through ``growth / ROIC`` reinvestment. A
    continuing valuation requires an independently supplied terminal ROIC;
    finite-life valuations omit a perpetuity and may include a reviewed final
    residual value net of closure obligations.
    """

    if starting_nopat <= 0:
        raise ValueError("starting_nopat must be positive")
    if roic <= 0:
        raise ValueError("roic must be positive")
    if wacc <= -1:
        raise ValueError("wacc must exceed -100%")
    if shares_outstanding <= 0:
        raise ValueError("shares_outstanding must be positive")
    if forecast_years < 1 or forecast_years > 30:
        raise ValueError("forecast_years must be between 1 and 30")
    if finite_life_years is not None and finite_life_years != forecast_years:
        raise ValueError("finite_life_years must equal the explicit forecast horizon")

    schedule: list[dict[str, float | int]] = []
    nopat = starting_nopat
    pv_fcff = 0.0
    explicit_reinvestment_rate = max(growth_rate, 0.0) / roic
    if explicit_reinvestment_rate >= 1:
        raise ValueError("growth requires reinvestment of at least 100% of NOPAT")

    for year in range(1, forecast_years + 1):
        nopat *= 1 + growth_rate
        reinvestment = nopat * explicit_reinvestment_rate
        fcff = nopat - reinvestment
        discount_factor = (1 + wacc) ** year
        present_value = fcff / discount_factor
        pv_fcff += present_value
        schedule.append(
            {
                "year": year,
                "nopat": nopat,
                "growth_rate": growth_rate,
                "roic": roic,
                "reinvestment": reinvestment,
                "fcff": fcff,
                "present_value": present_value,
            }
        )

    terminal_value = 0.0
    pv_terminal = 0.0
    if finite_life_years is not None:
        pv_terminal = residual_value / (1 + wacc) ** forecast_years
    else:
        if terminal_growth is None or terminal_roic is None:
            raise ValueError("continuing FCFF requires terminal_growth and terminal_roic")
        if wacc <= terminal_growth:
            raise ValueError("wacc must exceed terminal_growth")
        if terminal_roic <= 0:
            raise ValueError("terminal_roic must be positive")
        terminal_reinvestment_rate = max(terminal_growth, 0.0) / terminal_roic
        if terminal_reinvestment_rate >= 1:
            raise ValueError("terminal growth requires reinvestment of at least 100% of NOPAT")
        terminal_nopat = nopat * (1 + terminal_growth)
        terminal_fcff = terminal_nopat * (1 - terminal_reinvestment_rate)
        terminal_value = terminal_fcff / (wacc - terminal_growth)
        pv_terminal = terminal_value / (1 + wacc) ** forecast_years

    enterprise_value = pv_fcff + pv_terminal
    common_equity_value = (
        enterprise_value
        + cash
        + nonoperating_assets
        - debt
        - preferred_claims
        - minority_value
        - other_claims
    )
    return {
        "model": "fcff_dcf",
        "enterprise_value": enterprise_value,
        "common_equity_value": common_equity_value,
        "value_per_share": common_equity_value / shares_outstanding,
        "schedule": schedule,
        "terminal_value": terminal_value,
        "present_value_terminal": pv_terminal,
        "finite_life": finite_life_years is not None,
    }

