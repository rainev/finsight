"""Practical, transparent scenario models for bounded Batch 01 uncertainty."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from numbers import Real
from statistics import median
from typing import Any, Mapping, Sequence

from app.valuation.bank import residual_income_valuation

from .models import fcff_dcf
from .practical_policy import ValueRange
from .specialist_model_adapters import capitalize_research_and_development


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{name} must be finite")
    result = float(value)
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _apply_operating_state(
    assumptions: dict[str, Any],
    *,
    growth_delta: float,
    margin_delta: float,
    capital_efficiency_multiplier: float,
) -> None:
    assumptions["initial_revenue_growth"] += growth_delta
    assumptions["target_operating_margin"] += margin_delta
    assumptions["sales_to_capital"] *= capital_efficiency_multiplier
    if assumptions["sales_to_capital"] <= 0:
        raise ValueError("sales_to_capital must remain positive")
    assumptions["initial_marginal_roic"] = (
        assumptions["target_operating_margin"]
        * (1 - assumptions["normalized_tax_rate"])
        * assumptions["sales_to_capital"]
    )
    segment_forecast = assumptions.get("segment_forecast")
    if segment_forecast:
        for segment in segment_forecast["segments"].values():
            segment["initial_revenue_growth"] += growth_delta
            margin_key = (
                "target_operating_margin"
                if segment_forecast["mode"] == "segment_operating_income"
                else "target_gross_margin"
            )
            segment[margin_key] += margin_delta


PRACTICAL_FCFF_STATES = {
    "bear": {
        "growth_delta": -0.02,
        "margin_delta": -0.02,
        "wacc_delta": 0.01,
        "terminal_growth_delta": -0.005,
        "capital_efficiency_multiplier": 0.75,
    },
    "base": {
        "growth_delta": 0.0,
        "margin_delta": 0.0,
        "wacc_delta": 0.0,
        "terminal_growth_delta": 0.0,
        "capital_efficiency_multiplier": 1.0,
    },
    "bull": {
        "growth_delta": 0.015,
        "margin_delta": 0.02,
        "wacc_delta": -0.005,
        "terminal_growth_delta": 0.003,
        "capital_efficiency_multiplier": 1.10,
    },
}


def practical_fcff_scenarios(
    *,
    assumptions: Mapping[str, Any],
    discount_rate: Mapping[str, Any],
    financials: Mapping[str, Any],
    capital_efficiency_multipliers: Mapping[str, float] | None = None,
) -> dict[str, dict[str, Any]]:
    """Run coupled growth/margin/risk/capital-intensity economic states."""

    results = {}
    for name, state in PRACTICAL_FCFF_STATES.items():
        capital_multiplier = (
            float(capital_efficiency_multipliers[name])
            if capital_efficiency_multipliers is not None
            else state["capital_efficiency_multiplier"]
        )
        scenario_assumptions = deepcopy(dict(assumptions))
        scenario_rate = deepcopy(dict(discount_rate))
        _apply_operating_state(
            scenario_assumptions,
            growth_delta=state["growth_delta"],
            margin_delta=state["margin_delta"],
            capital_efficiency_multiplier=capital_multiplier,
        )
        scenario_rate["wacc"] += state["wacc_delta"]
        scenario_assumptions["terminal_marginal_roic"] = scenario_rate["wacc"]
        scenario_assumptions["terminal_growth"] += state[
            "terminal_growth_delta"
        ]
        if scenario_rate["wacc"] <= scenario_assumptions["terminal_growth"]:
            raise ValueError("scenario WACC must exceed terminal growth")
        model = fcff_dcf(
            assumptions=scenario_assumptions,
            discount_rate=scenario_rate,
            financials=dict(financials),
        )
        results[name] = {
            "fcff_dcf": model,
            "assumptions": {
                **state,
                "capital_efficiency_multiplier": capital_multiplier,
                "sales_to_capital": scenario_assumptions["sales_to_capital"],
                "wacc": scenario_rate["wacc"],
                "terminal_growth": scenario_assumptions["terminal_growth"],
            },
        }
    values = {
        name: row["fcff_dcf"]["intrinsic_value_per_share"]
        for name, row in results.items()
    }
    if not values["bear"] <= values["base"] <= values["bull"]:
        raise ValueError("practical FCFF states must produce bear <= base <= bull")
    return results


def fcff_value_with_capital_efficiency(
    *,
    assumptions: Mapping[str, Any],
    discount_rate: Mapping[str, Any],
    financials: Mapping[str, Any],
    capital_efficiency_multiplier: float,
) -> float:
    """Isolate capital intensity: lower efficiency means more reinvestment."""

    scenario_assumptions = deepcopy(dict(assumptions))
    _apply_operating_state(
        scenario_assumptions,
        growth_delta=0.0,
        margin_delta=0.0,
        capital_efficiency_multiplier=capital_efficiency_multiplier,
    )
    result = fcff_dcf(
        assumptions=scenario_assumptions,
        discount_rate=dict(discount_rate),
        financials=dict(financials),
    )
    value = result.get("intrinsic_value_per_share")
    return _finite(value, "intrinsic_value_per_share", positive=True)


def practical_fcff_one_way_sensitivities(
    *,
    assumptions: Mapping[str, Any],
    discount_rate: Mapping[str, Any],
    financials: Mapping[str, Any],
    base_capital_efficiency_multiplier: float,
    share_range: tuple[float, float, float] | None = None,
) -> list[dict[str, Any]]:
    """Recalculate one-way sensitivities from the practical base state."""

    base_sales_to_capital = float(assumptions["sales_to_capital"])

    def calculate(
        *,
        wacc_delta: float = 0.0,
        capital_multiplier: float = base_capital_efficiency_multiplier,
        shares: float | None = None,
    ) -> float:
        scenario_assumptions = deepcopy(dict(assumptions))
        scenario_rate = deepcopy(dict(discount_rate))
        _apply_operating_state(
            scenario_assumptions,
            growth_delta=0.0,
            margin_delta=0.0,
            capital_efficiency_multiplier=capital_multiplier,
        )
        scenario_rate["wacc"] += wacc_delta
        scenario_assumptions["terminal_marginal_roic"] = scenario_rate["wacc"]
        model = fcff_dcf(
            assumptions=scenario_assumptions,
            discount_rate=scenario_rate,
            financials=dict(financials),
        )
        if shares is None and share_range is not None:
            shares = share_range[1]
        if shares is not None:
            return _finite(model["equity_value"] / shares, "share sensitivity", positive=True)
        return _finite(
            model["intrinsic_value_per_share"],
            "intrinsic_value_per_share",
            positive=True,
        )

    rows = []
    for delta in (-0.01, 0.0, 0.01):
        rows.append(
            {
                "field": "wacc",
                "input": float(discount_rate["wacc"]) + delta,
                "delta": delta,
                "intrinsic_value_per_share": calculate(wacc_delta=delta),
                "publication_state": "review_required",
            }
        )
    for multiplier in (
        base_capital_efficiency_multiplier * 0.80,
        base_capital_efficiency_multiplier,
        base_capital_efficiency_multiplier * 1.20,
    ):
        rows.append(
            {
                "field": "sales_to_capital",
                "input": base_sales_to_capital * multiplier,
                "delta": multiplier - base_capital_efficiency_multiplier,
                "intrinsic_value_per_share": calculate(
                    capital_multiplier=multiplier
                ),
                "publication_state": "review_required",
            }
        )
    if share_range is not None:
        for shares in share_range:
            rows.append(
                {
                    "field": "diluted_shares",
                    "input": shares,
                    "delta": shares - share_range[1],
                    "intrinsic_value_per_share": calculate(shares=shares),
                    "publication_state": "review_required",
                }
            )
    return rows


def research_profitability_sensitivity(
    *,
    rd_history_newest_first: Sequence[float],
    reported_ebit: float,
    reported_operating_capital: float,
    reported_fcff: float,
    lives: Sequence[int] = (3, 5, 7),
) -> dict[str, Any]:
    """Interpret R&D lives without changing already expensed current cash FCFF."""

    rows = []
    for life in lives:
        adjustment = capitalize_research_and_development(
            rd_history_newest_first=rd_history_newest_first,
            amortization_life_years=life,
            reported_ebit=reported_ebit,
            reported_operating_capital=reported_operating_capital,
        )
        rows.append(
            {
                "life_years": life,
                "research_asset": adjustment.research_asset,
                "research_amortization": adjustment.research_amortization,
                "adjusted_ebit": adjustment.adjusted_ebit,
                "adjusted_operating_capital": adjustment.adjusted_operating_capital,
                "current_cash_fcff": float(reported_fcff),
            }
        )
    return {
        "rows": rows,
        "current_cash_fcff": float(reported_fcff),
        "cash_flow_adjustment": 0.0,
        "basis": (
            "R&D life changes adjusted profitability and reinvestment interpretation; "
            "reported current FCFF already expenses R&D cash and is not increased."
        ),
    }


@dataclass(frozen=True)
class BankPracticalInputs:
    beginning_total_equity: float
    ending_total_equity: float
    beginning_preferred_low: float
    beginning_preferred_high: float
    ending_preferred_low: float
    ending_preferred_high: float
    ttm_common_net_income: float
    ending_common_shares: float
    cost_of_equity: float
    terminal_growth: float
    forecast_years: int
    terminal_roe: float


@dataclass(frozen=True)
class EquityCashFlowState:
    """One coupled equity-level cash-flow state."""

    cash_flow: float
    growth_rate: float
    terminal_growth: float
    cost_of_equity: float


@dataclass(frozen=True)
class EnterpriseCashFlowState:
    """One coupled enterprise cash-FCFF state with a complete equity bridge.

    This is intentionally simpler than the revenue/margin FCFF model.  It is
    for issuers whose reported operating cash flow already contains material
    content, subscriber-acquisition, or other cash conversion that a generic
    sales-to-capital formula would miss.  Every financing claim is still
    bridged exactly once.
    """

    cash_fcff: float
    initial_growth: float
    terminal_growth: float
    wacc: float
    cash_and_investments: float
    interest_bearing_debt: float
    preferred_equity: float
    noncontrolling_interests: float
    diluted_shares: float
    nonoperating_adjustment: float = 0.0


def enterprise_cash_flow_dcf(
    state: EnterpriseCashFlowState,
    *,
    forecast_years: int = 8,
    allow_nonpositive_equity_trace: bool = False,
) -> dict[str, Any]:
    """Discount a source-normalized cash FCFF with a linear growth fade."""

    if not isinstance(state, EnterpriseCashFlowState):
        raise ValueError("state must be an EnterpriseCashFlowState")
    if not isinstance(forecast_years, int) or forecast_years < 2:
        raise ValueError("forecast_years must be an integer of at least two")
    cash_fcff = _finite(state.cash_fcff, "cash_fcff", positive=True)
    initial_growth = _finite(state.initial_growth, "initial_growth")
    terminal_growth = _finite(state.terminal_growth, "terminal_growth")
    wacc = _finite(state.wacc, "wacc", positive=True)
    if terminal_growth < -0.10 or terminal_growth > 0.025:
        raise ValueError("terminal_growth must be between -10% and 2.5%")
    if wacc - terminal_growth < 0.025:
        raise ValueError("wacc must exceed terminal_growth by at least 2.5%")
    cash_and_investments = _finite(
        state.cash_and_investments, "cash_and_investments"
    )
    debt = _finite(state.interest_bearing_debt, "interest_bearing_debt")
    preferred = _finite(state.preferred_equity, "preferred_equity")
    nci = _finite(state.noncontrolling_interests, "noncontrolling_interests")
    shares = _finite(state.diluted_shares, "diluted_shares", positive=True)
    adjustment = _finite(state.nonoperating_adjustment, "nonoperating_adjustment")
    # This is an additive signed adjustment: positive nonoperating assets,
    # negative separately source-bound claims. Gross bridge fields stay >= 0.
    if min(cash_and_investments, debt, preferred, nci) < 0:
        raise ValueError("bridge inputs must be nonnegative")

    schedule = []
    present_value = 0.0
    current_cash = cash_fcff
    for year in range(1, forecast_years + 1):
        fade_weight = (forecast_years - year) / (forecast_years - 1)
        growth = terminal_growth + (initial_growth - terminal_growth) * fade_weight
        current_cash *= 1 + growth
        discounted = current_cash / (1 + wacc) ** year
        present_value += discounted
        schedule.append(
            {
                "year": year,
                "growth": growth,
                "cash_fcff": current_cash,
                "present_value": discounted,
            }
        )
    terminal_cash = current_cash * (1 + terminal_growth)
    terminal_value = terminal_cash / (wacc - terminal_growth)
    present_terminal = terminal_value / (1 + wacc) ** forecast_years
    enterprise_value = present_value + present_terminal
    equity_value = (
        enterprise_value
        + cash_and_investments
        + adjustment
        - debt
        - preferred
        - nci
    )
    per_share = equity_value / shares
    if not math.isfinite(per_share):
        raise ValueError("enterprise cash-FCFF state produces nonfinite equity value")
    if per_share <= 0 and not allow_nonpositive_equity_trace:
        raise ValueError("enterprise cash-FCFF state produces nonpositive equity value")
    return {
        "model": "fcff_dcf",
        "output_type": "intrinsic_value_per_share",
        "currency": "USD",
        "intrinsic_value_per_share": per_share,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "publication_state": "withheld" if per_share <= 0 else "review_required",
        "errors": [],
        "warnings": [
            "Practical cash-FCFF model; source-linked cash conversion and scenarios require review.",
            *(
                ["Raw residual equity is nonpositive and may be retained only as a private limited-liability-floor trace."]
                if per_share <= 0
                else []
            ),
        ],
        "detail": {
            "forecast_schedule": schedule,
            "pv_explicit_fcff": present_value,
            "terminal_fcff": terminal_cash,
            "terminal_value": terminal_value,
            "pv_terminal_value": present_terminal,
            "terminal_value_share": present_terminal / enterprise_value,
            "cash_and_nonoperating_investments": cash_and_investments,
            "interest_bearing_debt": debt,
            "preferred_equity": preferred,
            "noncontrolling_interests": nci,
            "nonoperating_adjustment": adjustment,
            "shares_proxy": shares,
            "wacc": wacc,
            "terminal_growth": terminal_growth,
        },
    }


def practical_cash_fcff_range(
    states: Mapping[str, EnterpriseCashFlowState],
    *,
    forecast_years: int = 8,
) -> tuple[ValueRange, dict[str, dict[str, Any]]]:
    """Value coupled bear/base/bull cash-FCFF states without mixing extrema."""

    if set(states) != {"bear", "base", "bull"}:
        raise ValueError("states must contain exactly bear, base, and bull")
    results = {
        name: enterprise_cash_flow_dcf(state, forecast_years=forecast_years)
        for name, state in states.items()
    }
    value_range = ValueRange(
        results["bear"]["intrinsic_value_per_share"],
        results["base"]["intrinsic_value_per_share"],
        results["bull"]["intrinsic_value_per_share"],
    )
    return value_range, results


def mixed_utility_fcfe(
    *,
    operating_cash_flow: float,
    capital_expenditures: float,
    net_income: float,
    debt_funding_share: float,
    parent_cash_flow_share: float,
) -> float:
    """Derive parent FCFE from consolidated utility reinvestment and funding."""

    cfo = _finite(operating_cash_flow, "operating_cash_flow")
    capex = _finite(capital_expenditures, "capital_expenditures", positive=True)
    income = _finite(net_income, "net_income", positive=True)
    funding = _finite(debt_funding_share, "debt_funding_share")
    parent = _finite(parent_cash_flow_share, "parent_cash_flow_share")
    if not 0 <= funding <= 1 or not 0 < parent <= 1:
        raise ValueError("utility funding and parent shares must be within zero and one")
    reinvestment = capex + income - cfo
    return (cfo - capex + funding * reinvestment) * parent


def captive_finance_owner_cash_flow(
    *, adjusted_free_cash_flow: float,
    finance_asset_growth: float,
    debt_to_equity: float,
) -> float:
    """Charge adjusted FCF once for the equity-funded share of finance growth."""

    cash = _finite(adjusted_free_cash_flow, "adjusted_free_cash_flow", positive=True)
    growth = _finite(finance_asset_growth, "finance_asset_growth")
    leverage = _finite(debt_to_equity, "debt_to_equity")
    if growth < 0 or leverage < 0:
        raise ValueError("finance asset growth and leverage must be nonnegative")
    return cash - growth / (1 + leverage)


@dataclass(frozen=True)
class CyclicalOperatingState:
    issuer: str
    period_end: str
    revenue: float
    operating_margin: float
    depreciation_ratio: float
    capex_ratio: float


def _weighted_quantile(
    values: Sequence[tuple[float, float]], quantile: float
) -> float:
    if not 0 <= quantile <= 1 or not values:
        raise ValueError("weighted quantile requires values and a 0-1 quantile")
    ordered = sorted(values, key=lambda row: row[0])
    total = sum(weight for _, weight in ordered)
    if total <= 0:
        raise ValueError("weighted quantile weights must be positive")
    threshold = quantile * total
    cumulative = 0.0
    for value, weight in ordered:
        if weight <= 0:
            raise ValueError("weighted quantile weights must be positive")
        cumulative += weight
        if cumulative >= threshold:
            return value
    return ordered[-1][0]


def practical_cyclical_fcff_range(
    *,
    current_state: CyclicalOperatingState,
    observed_states: Sequence[CyclicalOperatingState],
    operating_nwc_ratio: float,
    normalized_tax_rate: float,
    wacc: float,
    cash: float,
    debt: float,
    other_claims: ValueRange,
    diluted_shares: float,
) -> tuple[ValueRange, dict[str, Any]]:
    """Value issuer-balanced paired cycle excursions that recover to one normal state."""

    if len(observed_states) < 6:
        raise ValueError("cyclical model requires a multi-year observed state set")
    shares = _finite(diluted_shares, "diluted_shares", positive=True)
    rate = _finite(wacc, "wacc", positive=True)
    tax = _finite(normalized_tax_rate, "normalized_tax_rate")
    nwc = _finite(operating_nwc_ratio, "operating_nwc_ratio")
    if not 0 <= tax <= 0.50 or nwc < 0:
        raise ValueError("cyclical tax and NWC policies are out of bounds")
    issuers = sorted({state.issuer for state in observed_states})
    if len(issuers) != 2:
        raise ValueError("cyclical benchmark requires exactly two issuers")
    issuer_states = {
        issuer: [state for state in observed_states if state.issuer == issuer]
        for issuer in issuers
    }
    if any(len(rows) < 3 for rows in issuer_states.values()):
        raise ValueError("each cyclical issuer requires at least three states")
    weights = {
        (state.issuer, state.period_end): 0.5 / len(issuer_states[state.issuer])
        for state in observed_states
    }
    revenue_medians = {
        issuer: median([state.revenue for state in rows])
        for issuer, rows in issuer_states.items()
    }
    terminal_margin = _weighted_quantile(
        [
            (state.operating_margin, weights[(state.issuer, state.period_end)])
            for state in observed_states
        ],
        0.5,
    )
    terminal_state = min(
        observed_states,
        key=lambda state: (
            abs(state.operating_margin - terminal_margin),
            state.issuer,
            state.period_end,
        ),
    )
    wdc_median_revenue = revenue_medians[current_state.issuer]
    terminal_revenue = (
        terminal_state.revenue
        / revenue_medians[terminal_state.issuer]
        * wdc_median_revenue
    )
    terminal_capex_ratio = max(
        terminal_state.capex_ratio, terminal_state.depreciation_ratio
    )

    results: list[dict[str, Any]] = []
    for state in observed_states:
        mapped_revenue = (
            state.revenue / revenue_medians[state.issuer] * wdc_median_revenue
        )
        present = 0.0
        schedule = []
        for year in range(1, 11):
            if year <= 5:
                progress = year / 5
                start = current_state
                end = state
                start_revenue = current_state.revenue
                end_revenue = mapped_revenue
            else:
                progress = (year - 5) / 5
                start = state
                end = terminal_state
                start_revenue = mapped_revenue
                end_revenue = terminal_revenue
            revenue = start_revenue * (end_revenue / start_revenue) ** progress
            margin = start.operating_margin + progress * (
                end.operating_margin - start.operating_margin
            )
            depreciation_ratio = start.depreciation_ratio + progress * (
                end.depreciation_ratio - start.depreciation_ratio
            )
            capex_ratio = start.capex_ratio + progress * (
                end.capex_ratio - start.capex_ratio
            )
            ebit = revenue * margin
            taxes = max(0.0, ebit * tax)
            fcff = (
                ebit
                - taxes
                + revenue * depreciation_ratio
                - revenue * capex_ratio
                - revenue * nwc
            )
            discounted = fcff / (1 + rate) ** year
            present += discounted
            schedule.append(
                {
                    "year": year,
                    "revenue": revenue,
                    "operating_margin": margin,
                    "depreciation_ratio": depreciation_ratio,
                    "capex_ratio": capex_ratio,
                    "operating_nwc_ratio": nwc,
                    "fcff": fcff,
                    "present_value": discounted,
                }
            )
        terminal_fcff = terminal_revenue * terminal_state.operating_margin * (
            1 - tax
        ) + terminal_revenue * (
            terminal_state.depreciation_ratio - terminal_capex_ratio
        )
        if terminal_fcff <= 0:
            raise ValueError("normalized cyclical terminal FCFF must be positive")
        terminal_value = terminal_fcff / rate
        terminal_present = terminal_value / (1 + rate) ** 10
        enterprise_value = present + terminal_present
        midpoint_equity = enterprise_value + cash - debt - other_claims.base
        value = midpoint_equity / shares
        results.append(
            {
                "issuer": state.issuer,
                "period_end": state.period_end,
                "weight": weights[(state.issuer, state.period_end)],
                "mapped_revenue": mapped_revenue,
                "enterprise_value": enterprise_value,
                "midpoint_value_per_share": value,
                "terminal_value": terminal_value,
                "terminal_present_value": terminal_present,
                "terminal_share": terminal_present / enterprise_value,
                "schedule": schedule,
            }
        )
    weighted = [
        (row["midpoint_value_per_share"], row["weight"]) for row in results
    ]
    midpoint_values = {
        "low": _weighted_quantile(weighted, 0.25),
        "base": _weighted_quantile(weighted, 0.50),
        "high": _weighted_quantile(weighted, 0.75),
    }
    bridge_low_delta = (other_claims.base - other_claims.high) / shares
    bridge_high_delta = (other_claims.base - other_claims.low) / shares
    value_range = ValueRange(
        midpoint_values["low"] + bridge_low_delta,
        midpoint_values["base"],
        midpoint_values["high"] + bridge_high_delta,
    )
    return value_range, {
        "states": results,
        "issuer_weights": {issuer: 0.5 for issuer in issuers},
        "revenue_medians": revenue_medians,
        "terminal_state": {
            "issuer": terminal_state.issuer,
            "period_end": terminal_state.period_end,
            "revenue": terminal_revenue,
            "operating_margin": terminal_state.operating_margin,
            "depreciation_ratio": terminal_state.depreciation_ratio,
            "capex_ratio": terminal_capex_ratio,
        },
        "midpoint_weighted_quantiles": midpoint_values,
        "other_claims": other_claims.as_dict(),
        "cash": cash,
        "debt": debt,
        "shares": shares,
        "normalized_tax_rate": tax,
        "wacc": rate,
        "operating_nwc_ratio": nwc,
    }


def practical_equity_cash_flow_range(
    *,
    states: Mapping[str, EquityCashFlowState],
    diluted_shares: float,
    forecast_years: int = 10,
    maximum_terminal_share: float = 0.85,
) -> tuple[ValueRange, dict[str, Any]]:
    """Discount coupled equity cash flows without an EV-to-equity bridge."""

    if tuple(states) != ("bear", "base", "bull"):
        raise ValueError("equity cash-flow states must be bear, base, bull")
    shares = _finite(diluted_shares, "diluted_shares", positive=True)
    if not 0 < maximum_terminal_share < 1:
        raise ValueError("maximum_terminal_share must be between zero and one")
    values: dict[str, float] = {}
    traces: dict[str, Any] = {}
    for name, state in states.items():
        cash = _finite(state.cash_flow, f"{name} cash_flow", positive=True)
        cost = _finite(state.cost_of_equity, f"{name} cost_of_equity", positive=True)
        if cost - state.terminal_growth < 0.025:
            raise ValueError(
                "cost of equity minus terminal growth must be at least 2.5%"
            )
        present = 0.0
        schedule = []
        for year in range(1, forecast_years + 1):
            flow = cash * (1 + state.growth_rate) ** year
            discounted = flow / (1 + cost) ** year
            present += discounted
            schedule.append(
                {"year": year, "cash_flow": flow, "present_value": discounted}
            )
        terminal_flow = schedule[-1]["cash_flow"] * (1 + state.terminal_growth)
        terminal_value = terminal_flow / (cost - state.terminal_growth)
        terminal_present = terminal_value / (1 + cost) ** forecast_years
        total = present + terminal_present
        terminal_share = terminal_present / total
        if terminal_share > maximum_terminal_share:
            raise ValueError("terminal value share exceeds the policy maximum")
        values[name] = total / shares
        traces[name] = {
            "cash_flow": cash,
            "growth_rate": state.growth_rate,
            "terminal_growth": state.terminal_growth,
            "cost_of_equity": cost,
            "shares": shares,
            "forecast_schedule": schedule,
            "terminal_value": terminal_value,
            "terminal_present_value": terminal_present,
            "terminal_share": terminal_share,
        }
    return ValueRange(values["bear"], values["base"], values["bull"]), traces


def practical_bank_residual_income_range(
    inputs: BankPracticalInputs,
) -> tuple[ValueRange, dict[str, Any]]:
    """Value common equity across conservative preferred/capital/ROE states."""

    begin_total = _finite(
        inputs.beginning_total_equity, "beginning_total_equity", positive=True
    )
    end_total = _finite(
        inputs.ending_total_equity, "ending_total_equity", positive=True
    )
    shares = _finite(inputs.ending_common_shares, "ending_common_shares", positive=True)
    income = _finite(inputs.ttm_common_net_income, "ttm_common_net_income", positive=True)
    cost = _finite(inputs.cost_of_equity, "cost_of_equity", positive=True)
    states = {
        "bear": {
            "begin_preferred": inputs.beginning_preferred_high,
            "end_preferred": inputs.ending_preferred_high,
            "roe_multiplier": 0.80,
            "payout": 0.20,
            "cost_delta": 0.01,
            "terminal_roe_delta": -0.02,
        },
        "base": {
            "begin_preferred": (
                inputs.beginning_preferred_low + inputs.beginning_preferred_high
            )
            / 2,
            "end_preferred": (
                inputs.ending_preferred_low + inputs.ending_preferred_high
            )
            / 2,
            "roe_multiplier": 1.0,
            "payout": 0.30,
            "cost_delta": 0.0,
            "terminal_roe_delta": 0.0,
        },
        "bull": {
            "begin_preferred": inputs.beginning_preferred_low,
            "end_preferred": inputs.ending_preferred_low,
            "roe_multiplier": 1.05,
            "payout": 0.40,
            "cost_delta": -0.005,
            "terminal_roe_delta": 0.01,
        },
    }
    values = {}
    traces = {}
    for name, state in states.items():
        begin_common = begin_total - _finite(
            state["begin_preferred"], "beginning preferred"
        )
        end_common = end_total - _finite(
            state["end_preferred"], "ending preferred"
        )
        if begin_common <= 0 or end_common <= 0:
            raise ValueError("bank common equity must remain positive")
        average_common = (begin_common + end_common) / 2
        roe = income / average_common * state["roe_multiplier"]
        scenario_cost = cost + state["cost_delta"]
        terminal_roe = inputs.terminal_roe + state["terminal_roe_delta"]
        if terminal_roe <= inputs.terminal_growth:
            raise ValueError("terminal ROE must exceed terminal growth")
        value = residual_income_valuation(
            book_value_per_share=end_common / shares,
            current_roe=roe,
            cost_of_equity=scenario_cost,
            current_payout_ratio=state["payout"],
            terminal_roe=terminal_roe,
            terminal_growth=inputs.terminal_growth,
            years=inputs.forecast_years,
            current_price=None,
        )["intrinsic_value"]
        values[name] = value
        traces[name] = {
            **state,
            "beginning_common_equity": begin_common,
            "ending_common_equity": end_common,
            "average_common_equity": average_common,
            "ttm_common_net_income": income,
            "roe": roe,
            "cost_of_equity": scenario_cost,
            "terminal_roe": terminal_roe,
            "shares": shares,
        }
    value_range = ValueRange(values["bear"], values["base"], values["bull"])
    return value_range, traces


def two_stage_cash_flow_value(
    *,
    cash_flow_per_share: float,
    growth_rate: float,
    growth_years: int,
    terminal_growth: float,
    discount_rate: float,
) -> float:
    cash = _finite(cash_flow_per_share, "cash_flow_per_share", positive=True)
    discount = _finite(discount_rate, "discount_rate", positive=True)
    if discount <= terminal_growth:
        raise ValueError("discount rate must exceed terminal growth")
    if growth_years < 1:
        raise ValueError("growth_years must be positive")
    present = 0.0
    for year in range(1, growth_years + 1):
        flow = cash * (1 + growth_rate) ** year
        present += flow / (1 + discount) ** year
    terminal_flow = cash * (1 + growth_rate) ** growth_years * (1 + terminal_growth)
    terminal = terminal_flow / (discount - terminal_growth)
    return present + terminal / (1 + discount) ** growth_years


def practical_reit_range(
    *,
    ffo: float,
    straight_line_rent: float,
    maintenance_capex_range: ValueRange,
    diluted_shares: float,
    annualized_lease_income: float,
    cap_rate_range: ValueRange,
    cash: float,
    debt: float,
    preferred_equity: float,
    noncontrolling_interests: float,
) -> tuple[ValueRange, dict[str, Any]]:
    """Combine an AFFO DCF and transparent gross-lease capitalization support."""

    shares = _finite(diluted_shares, "diluted_shares", positive=True)
    affo_states = {
        "bear": ffo - straight_line_rent - maintenance_capex_range.high,
        "base": ffo - straight_line_rent - maintenance_capex_range.base,
        "bull": ffo - straight_line_rent - maintenance_capex_range.low,
    }
    if any(value <= 0 for value in affo_states.values()):
        raise ValueError("AFFO must remain positive in every state")
    affo_values = {
        "bear": two_stage_cash_flow_value(
            cash_flow_per_share=affo_states["bear"] / shares,
            growth_rate=0.02,
            growth_years=8,
            terminal_growth=0.015,
            discount_rate=0.105,
        ),
        "base": two_stage_cash_flow_value(
            cash_flow_per_share=affo_states["base"] / shares,
            growth_rate=0.04,
            growth_years=8,
            terminal_growth=0.02,
            discount_rate=0.095,
        ),
        "bull": two_stage_cash_flow_value(
            cash_flow_per_share=affo_states["bull"] / shares,
            growth_rate=0.055,
            growth_years=8,
            terminal_growth=0.025,
            discount_rate=0.085,
        ),
    }
    property_values = {
        "bear": annualized_lease_income / cap_rate_range.high,
        "base": annualized_lease_income / cap_rate_range.base,
        "bull": annualized_lease_income / cap_rate_range.low,
    }
    nav_values = {
        name: (
            property_value
            + cash
            - debt
            - preferred_equity
            - noncontrolling_interests
        )
        / shares
        for name, property_value in property_values.items()
    }
    # Both views must be positive. AFFO DCF is the primary method; gross-lease
    # capitalization is a private reasonableness diagnostic, not NAV.
    if any(value <= 0 for value in nav_values.values()):
        raise ValueError("property capitalization support must remain positive")
    return ValueRange(
        affo_values["bear"],
        affo_values["base"],
        affo_values["bull"],
    ), {
        "affo": affo_states,
        "affo_dcf_values": affo_values,
        "cap_rates": cap_rate_range.as_dict(),
        "property_values": property_values,
        "gross_lease_capitalization_support_per_share": nav_values,
        "property_support_is_primary": False,
        "cash": cash,
        "debt": debt,
        "preferred_equity": preferred_equity,
        "noncontrolling_interests": noncontrolling_interests,
        "shares": shares,
    }
