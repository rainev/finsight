"""Pure, input-explicit adapters for specialist U.S. valuation lanes.

These helpers implement mechanical model transformations only. They deliberately
provide no issuer defaults, market multiples, cap rates, asset lives, or missing
values. Callers must supply governed, source-linked inputs before a lane can move
out of experimental maturity.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from statistics import median
from typing import Mapping, Sequence


def _finite(value: object, field: str, *, nonnegative: bool = False) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if nonnegative and result < 0:
        raise ValueError(f"{field} must be nonnegative")
    return result


@dataclass(frozen=True)
class ResearchAdjustment:
    research_asset: float
    research_amortization: float
    adjusted_ebit: float
    adjusted_operating_capital: float


def capitalize_research_and_development(
    *,
    rd_history_newest_first: Sequence[float],
    amortization_life_years: int,
    reported_ebit: float,
    reported_operating_capital: float,
) -> ResearchAdjustment:
    """Capitalize R&D with straight-line amortization and no assumed asset life."""

    if isinstance(amortization_life_years, bool) or not isinstance(
        amortization_life_years, int
    ):
        raise ValueError("amortization_life_years must be an integer")
    if amortization_life_years < 1:
        raise ValueError("amortization_life_years must be positive")
    if len(rd_history_newest_first) < amortization_life_years + 1:
        raise ValueError(
            "R&D history must include the current year plus one observation "
            "for every amortization year"
        )
    history = tuple(
        _finite(value, "R&D history", nonnegative=True)
        for value in rd_history_newest_first
    )
    current_rd = history[0]
    life = amortization_life_years
    research_asset = sum(
        history[age] * (life - age) / life for age in range(life)
    )
    research_amortization = sum(history[age] / life for age in range(1, life + 1))
    adjusted_ebit = (
        _finite(reported_ebit, "reported_ebit")
        + current_rd
        - research_amortization
    )
    adjusted_capital = _finite(
        reported_operating_capital,
        "reported_operating_capital",
        nonnegative=True,
    ) + research_asset
    return ResearchAdjustment(
        research_asset=research_asset,
        research_amortization=research_amortization,
        adjusted_ebit=adjusted_ebit,
        adjusted_operating_capital=adjusted_capital,
    )


@dataclass(frozen=True)
class CycleNormalization:
    normalized_revenue: float
    normalized_margin: float
    observed_margin_low: float
    observed_margin_high: float


def normalize_complete_cycle(
    *,
    revenue_history: Sequence[float],
    operating_income_history: Sequence[float],
    complete_cycle_evidence: bool,
) -> CycleNormalization:
    """Return medians only when the caller proves the history spans a full cycle."""

    if complete_cycle_evidence is not True:
        raise ValueError("complete-cycle evidence is required")
    if len(revenue_history) != len(operating_income_history) or len(revenue_history) < 3:
        raise ValueError("aligned revenue and operating-income histories are required")
    revenues = tuple(
        _finite(value, "revenue history", nonnegative=True)
        for value in revenue_history
    )
    if any(value <= 0 for value in revenues):
        raise ValueError("cycle revenue must be positive")
    income = tuple(
        _finite(value, "operating-income history")
        for value in operating_income_history
    )
    margins = tuple(value / revenue for value, revenue in zip(income, revenues))
    return CycleNormalization(
        normalized_revenue=float(median(revenues)),
        normalized_margin=float(median(margins)),
        observed_margin_low=min(margins),
        observed_margin_high=max(margins),
    )


@dataclass(frozen=True)
class BankCommonEquity:
    beginning_common_equity: float
    ending_common_equity: float
    average_common_equity: float
    ttm_common_net_income: float
    current_roe: float


def derive_bank_common_equity(
    *,
    beginning_total_equity: float,
    beginning_preferred_equity: float,
    ending_total_equity: float,
    ending_preferred_equity: float,
    prior_fiscal_common_net_income: float,
    current_ytd_common_net_income: float,
    prior_ytd_common_net_income: float,
) -> BankCommonEquity:
    """Construct average common equity and TTM common earnings for residual income."""

    beginning_common = _finite(
        beginning_total_equity, "beginning_total_equity", nonnegative=True
    ) - _finite(
        beginning_preferred_equity,
        "beginning_preferred_equity",
        nonnegative=True,
    )
    ending_common = _finite(
        ending_total_equity, "ending_total_equity", nonnegative=True
    ) - _finite(
        ending_preferred_equity, "ending_preferred_equity", nonnegative=True
    )
    if beginning_common <= 0 or ending_common <= 0:
        raise ValueError("common equity must be positive at both aligned dates")
    average_common = (beginning_common + ending_common) / 2
    ttm_income = (
        _finite(prior_fiscal_common_net_income, "prior_fiscal_common_net_income")
        + _finite(current_ytd_common_net_income, "current_ytd_common_net_income")
        - _finite(prior_ytd_common_net_income, "prior_ytd_common_net_income")
    )
    return BankCommonEquity(
        beginning_common_equity=beginning_common,
        ending_common_equity=ending_common,
        average_common_equity=average_common,
        ttm_common_net_income=ttm_income,
        current_roe=ttm_income / average_common,
    )


def capital_constrained_payout_ratio(
    *,
    ttm_common_net_income: float,
    beginning_required_cet1: float,
    ending_required_cet1: float,
) -> float:
    """Cap payout by income remaining after growth in required CET1 capital."""

    income = _finite(ttm_common_net_income, "ttm_common_net_income")
    if income <= 0:
        raise ValueError("positive TTM common net income is required")
    capital_growth = _finite(
        ending_required_cet1, "ending_required_cet1", nonnegative=True
    ) - _finite(
        beginning_required_cet1,
        "beginning_required_cet1",
        nonnegative=True,
    )
    distributable = max(0.0, income - max(0.0, capital_growth))
    return min(1.0, distributable / income)


def sum_of_parts_equity_per_share(
    *,
    component_values: Mapping[str, float],
    excess_cash: float,
    debt: float,
    preferred_equity: float,
    noncontrolling_interests: float,
    corporate_claims: float,
    diluted_shares: float,
) -> float:
    """Combine non-overlapping component values and subtract each claim exactly once."""

    if not isinstance(component_values, Mapping) or not component_values:
        raise ValueError("at least one named component value is required")
    components = tuple(
        _finite(value, f"component {name}")
        for name, value in component_values.items()
        if isinstance(name, str) and name.strip()
    )
    if len(components) != len(component_values):
        raise ValueError("component names must be nonempty text")
    shares = _finite(diluted_shares, "diluted_shares")
    if shares <= 0:
        raise ValueError("diluted_shares must be positive")
    equity = (
        sum(components)
        + _finite(excess_cash, "excess_cash", nonnegative=True)
        - _finite(debt, "debt", nonnegative=True)
        - _finite(preferred_equity, "preferred_equity", nonnegative=True)
        - _finite(
            noncontrolling_interests,
            "noncontrolling_interests",
            nonnegative=True,
        )
        - _finite(corporate_claims, "corporate_claims", nonnegative=True)
    )
    if equity <= 0:
        raise ValueError("sum-of-parts equity value must be positive")
    return equity / shares


def normalized_affo(
    *,
    ffo: float,
    straight_line_rent_adjustment: float,
    recurring_capital_expenditures: float,
    other_recurring_adjustments: float,
) -> float:
    """Calculate AFFO only from explicitly supplied recurring adjustments."""

    result = (
        _finite(ffo, "ffo")
        - _finite(
            straight_line_rent_adjustment,
            "straight_line_rent_adjustment",
        )
        - _finite(
            recurring_capital_expenditures,
            "recurring_capital_expenditures",
            nonnegative=True,
        )
        + _finite(other_recurring_adjustments, "other_recurring_adjustments")
    )
    if result <= 0:
        raise ValueError("normalized AFFO must be positive")
    return result


def property_nav_per_share(
    *,
    normalized_noi: float,
    cap_rate: float,
    other_assets: float,
    net_debt: float,
    preferred_equity: float,
    noncontrolling_interests: float,
    diluted_shares: float,
) -> float:
    """Capitalize normalized NOI and bridge property value to common equity."""

    noi = _finite(normalized_noi, "normalized_noi")
    rate = _finite(cap_rate, "cap_rate")
    shares = _finite(diluted_shares, "diluted_shares")
    if noi <= 0 or rate <= 0 or shares <= 0:
        raise ValueError("positive NOI, cap rate, and diluted shares are required")
    property_value = noi / rate
    equity = (
        property_value
        + _finite(other_assets, "other_assets", nonnegative=True)
        - _finite(net_debt, "net_debt", nonnegative=True)
        - _finite(preferred_equity, "preferred_equity", nonnegative=True)
        - _finite(
            noncontrolling_interests,
            "noncontrolling_interests",
            nonnegative=True,
        )
    )
    if equity <= 0:
        raise ValueError("property NAV common equity must be positive")
    return equity / shares
