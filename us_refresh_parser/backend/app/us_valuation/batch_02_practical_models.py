"""Practical, source-linked cash-FCFF policy for numeric Batch 02 cases."""

from __future__ import annotations

from dataclasses import asdict, replace
from statistics import median
from typing import Any

from .assumptions import US_BASE, build_discount_rate
from .batch_02_practical_inputs import CashFcffInputs
from .classification import load_archetype_config
from .practical_models import (
    EnterpriseCashFlowState,
    enterprise_cash_flow_dcf,
    practical_cash_fcff_range,
)
from .practical_policy import (
    BoundedAssumption,
    HardSafetyInput,
    InputRange,
    PracticalOutcome,
    SourceTrace,
    decide_practical_outcome,
)
from .reliability import assess_reliability, relative_movement


BATCH_02_POLICY_VERSION = "BATCH-02-PRACTICAL-CASH-FCFF-1.0"
_POLICY_BY_TICKER = {
    "VZ": "telecom",
    "T": "telecom",
    "NFLX": "internet_digital_services",
    "TMUS": "telecom",
    "META": "internet_digital_services",
}
_MODEL_REASON = {
    "VZ": (
        "Telecom enterprise cash FCFF captures network and spectrum cash conversion; "
        "the completed Frontier acquisition was described by the issuer as immaterial "
        "to consolidated revenue and earnings, while all current financing claims are reconciled."
    ),
    "T": (
        "Telecom enterprise cash FCFF uses continuing-operations cash evidence and a "
        "source-bounded range for the held-for-sale Forged Fiber net assets."
    ),
    "NFLX": (
        "Content-aware enterprise cash FCFF uses operating cash flow after content cash "
        "spending and removes the reported one-time WBD termination fee."
    ),
    "TMUS": (
        "Wireless enterprise cash FCFF captures network reinvestment and reconciles current "
        "short-term debt, long-term debt, and finance leases exactly once."
    ),
    "META": (
        "Growth enterprise cash FCFF keeps reported AI/data-center capital spending load-bearing "
        "and ranges that spending without adding unproven incremental cash flow."
    ),
}


def _filing_trace(inputs: CashFcffInputs, *, unit: str) -> SourceTrace:
    return SourceTrace(
        source_kind="filing_evidence",
        accession=inputs.accession,
        policy_reference=None,
        period_end=inputs.period_end,
        unit=unit,
        reported_vs_estimated="reported",
    )


def _policy_trace(reference: str, *, unit: str) -> SourceTrace:
    return SourceTrace(
        source_kind="governed_policy",
        accession=None,
        policy_reference=f"{BATCH_02_POLICY_VERSION}:{reference}",
        period_end="2026-08-14",
        unit=unit,
        reported_vs_estimated="estimated",
    )


def _cash_range(inputs: CashFcffInputs) -> InputRange:
    current = inputs.normalized_cash_fcff
    if inputs.ticker == "META":
        stress = inputs.ttm_capex * 0.10
        return InputRange(current - stress, current, current + stress)
    recent = tuple(inputs.annual_cash_fcff[-2:])
    center = float(median((current, *recent)))
    result = InputRange(
        min((current, *recent)) * 0.85,
        center,
        max((current, *recent)) * 1.15,
    )
    if inputs.ticker == "T":
        scope = inputs.specialist_context["scope_adjustment_range"]
        result = InputRange(
            result.low - (scope[2] - scope[1]),
            result.base,
            result.high + (scope[1] - scope[0]),
        )
    return result


def _growth_range(inputs: CashFcffInputs) -> tuple[float, float, float]:
    revenues = inputs.annual_revenue[-3:]
    if len(revenues) < 3 or revenues[0] <= 0 or revenues[-1] <= 0:
        raise ValueError("three positive annual revenue states are required")
    cagr = (revenues[-1] / revenues[0]) ** (1 / (len(revenues) - 1)) - 1
    if inputs.ticker in {"VZ", "T", "TMUS"}:
        base = min(0.05, max(-0.02, cagr))
    else:
        base = min(0.12, max(0.02, cagr))
    return base - 0.02, base, base + 0.015


def _states(
    inputs: CashFcffInputs,
) -> tuple[dict[str, EnterpriseCashFlowState], dict[str, Any]]:
    config = load_archetype_config()
    policy_name = _POLICY_BY_TICKER[inputs.ticker]
    discount = build_discount_rate(
        policy=config["valuation_policies"][policy_name],
        tax_rate=inputs.normalized_tax_rate,
        market=US_BASE,
    )
    base_wacc = float(discount["wacc"])
    cash_range = _cash_range(inputs)
    growth = _growth_range(inputs)
    shares = (
        inputs.bridge.diluted_shares * 1.05,
        inputs.bridge.diluted_shares,
        inputs.bridge.diluted_shares * 0.98,
    )
    event = inputs.bridge.nonoperating_range
    states = {
        "bear": EnterpriseCashFlowState(
            cash_fcff=cash_range.low,
            initial_growth=growth[0],
            terminal_growth=0.015,
            wacc=base_wacc + 0.01,
            cash_and_investments=inputs.bridge.cash_and_investments,
            interest_bearing_debt=inputs.bridge.interest_bearing_debt,
            preferred_equity=inputs.bridge.preferred_equity,
            noncontrolling_interests=inputs.bridge.noncontrolling_interests,
            diluted_shares=shares[0],
            nonoperating_adjustment=event[0],
        ),
        "base": EnterpriseCashFlowState(
            cash_fcff=cash_range.base,
            initial_growth=growth[1],
            terminal_growth=0.02,
            wacc=base_wacc,
            cash_and_investments=inputs.bridge.cash_and_investments,
            interest_bearing_debt=inputs.bridge.interest_bearing_debt,
            preferred_equity=inputs.bridge.preferred_equity,
            noncontrolling_interests=inputs.bridge.noncontrolling_interests,
            diluted_shares=shares[1],
            nonoperating_adjustment=event[1],
        ),
        "bull": EnterpriseCashFlowState(
            cash_fcff=cash_range.high,
            initial_growth=growth[2],
            terminal_growth=0.025,
            wacc=base_wacc - 0.01,
            cash_and_investments=inputs.bridge.cash_and_investments,
            interest_bearing_debt=inputs.bridge.interest_bearing_debt,
            preferred_equity=inputs.bridge.preferred_equity,
            noncontrolling_interests=inputs.bridge.noncontrolling_interests,
            diluted_shares=shares[2],
            nonoperating_adjustment=event[2],
        ),
    }
    return states, {
        "discount_rate": discount,
        "cash_fcff_range": cash_range.as_dict(),
        "initial_growth": {
            "bear": growth[0],
            "base": growth[1],
            "bull": growth[2],
        },
        "diluted_shares": {
            "bear": shares[0],
            "base": shares[1],
            "bull": shares[2],
        },
        "nonoperating_adjustment": {
            "bear": event[0],
            "base": event[1],
            "bull": event[2],
        },
    }


def _sensitivities(
    base_state: EnterpriseCashFlowState,
    cash_range: InputRange,
) -> list[dict[str, Any]]:
    rows = []
    for delta in (-0.01, 0.0, 0.01):
        value = enterprise_cash_flow_dcf(
            replace(base_state, wacc=base_state.wacc + delta)
        )["intrinsic_value_per_share"]
        rows.append(
            {
                "field": "wacc",
                "delta": delta,
                "intrinsic_value_per_share": value,
                "publication_state": "review_required",
            }
        )
    for value in (cash_range.low, cash_range.base, cash_range.high):
        result = enterprise_cash_flow_dcf(
            replace(base_state, cash_fcff=value)
        )["intrinsic_value_per_share"]
        rows.append(
            {
                "field": "cash_fcff",
                "delta": value - cash_range.base,
                "intrinsic_value_per_share": result,
                "publication_state": "review_required",
            }
        )
    for shares in (
        base_state.diluted_shares * 0.98,
        base_state.diluted_shares,
        base_state.diluted_shares * 1.05,
    ):
        result = enterprise_cash_flow_dcf(
            replace(base_state, diluted_shares=shares)
        )["intrinsic_value_per_share"]
        rows.append(
            {
                "field": "diluted_shares",
                "delta": shares - base_state.diluted_shares,
                "intrinsic_value_per_share": result,
                "publication_state": "review_required",
            }
        )
    return rows


def build_cash_fcff_result(
    inputs: CashFcffInputs,
) -> tuple[dict[str, Any], PracticalOutcome]:
    """Build one private practical result from immutable Batch 02 evidence."""

    states, calibration = _states(inputs)
    calibration["current_cash_fcff_reconciliation"] = {
        "operating_cash_flow": inputs.ttm_operating_cash_flow,
        "pp_and_e_capital_expenditures": inputs.ttm_capex,
        "spectrum_license_investment": inputs.ttm_spectrum_investment,
        "interest_expense_absolute": inputs.ttm_interest_expense,
        "normalized_tax_rate": inputs.normalized_tax_rate,
        "after_tax_interest_addback": inputs.ttm_interest_expense
        * (1 - inputs.normalized_tax_rate),
        "cash_fcff_before_one_time_and_scope_adjustments": inputs.reported_cash_fcff,
        "one_time_cash_adjustment": inputs.one_time_cash_adjustment,
        "scope_adjustment_midpoint": inputs.specialist_context[
            "scope_adjustment_range"
        ][1],
        "normalized_cash_fcff": inputs.normalized_cash_fcff,
    }
    value_range, scenarios = practical_cash_fcff_range(states)
    impact = relative_movement(
        low=value_range.low,
        base=value_range.base,
        high=value_range.high,
    )
    cash_range = InputRange(**calibration["cash_fcff_range"])
    growth = calibration["initial_growth"]
    shares = calibration["diluted_shares"]
    wacc = {
        name: state.wacc for name, state in states.items()
    }
    assumptions = [
        BoundedAssumption(
            name="normalized enterprise cash FCFF",
            value_range=cash_range,
            sources=(
                _filing_trace(inputs, unit="USD"),
                _policy_trace("company-history-cash-range", unit="USD"),
            ),
            fallback_level="company_history_cash_conversion",
            basis=(
                "Operating cash flow less capital spending plus after-tax interest; "
                "the range uses current TTM and recent annual issuer cash states."
            ),
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="initial cash-flow growth factor",
            value_range=InputRange(
                1 + growth["bear"],
                1 + growth["base"],
                1 + growth["bull"],
            ),
            sources=(
                _filing_trace(inputs, unit="ratio"),
                _policy_trace("issuer-history-growth-fade", unit="ratio"),
            ),
            fallback_level="company_history_growth_fade",
            basis="Recent issuer revenue history is capped by governed mature/growth ranges.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="policy WACC",
            value_range=InputRange(wacc["bull"], wacc["base"], wacc["bear"]),
            sources=(_policy_trace("wacc-plus-minus-100bp", unit="ratio"),),
            fallback_level="governed_discount_rate",
            basis="FinSight U.S. rate policy with a plus/minus 100bp scenario range.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
        BoundedAssumption(
            name="diluted share range",
            value_range=InputRange(
                shares["bull"], shares["base"], shares["bear"]
            ),
            sources=(
                _filing_trace(inputs, unit="shares"),
                _policy_trace("five-percent-dilution-stress", unit="shares"),
            ),
            fallback_level="current_diluted_shares_with_stress",
            basis="Current reported diluted shares are stressed upward without adding SBC back to cash flow.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=impact,
            material_provisional=True,
        ),
    ]
    if inputs.one_time_cash_adjustment:
        assumptions.append(
            BoundedAssumption(
                name="one-time cash-flow normalization",
                value_range=InputRange(
                    inputs.one_time_cash_adjustment,
                    inputs.one_time_cash_adjustment,
                    inputs.one_time_cash_adjustment,
                ),
                sources=(_filing_trace(inputs, unit="USD"),),
                fallback_level="reported_one_time_item_removal",
                basis="The reported WBD termination fee is removed from recurring Netflix cash FCFF.",
                accounting_impact_ratio=0.0,
                scenario_impact_ratio=impact,
                material_provisional=True,
            )
        )
    if inputs.bridge.nonoperating_range[2] > 0:
        assumptions.append(
            BoundedAssumption(
                name="held-for-sale net asset realization",
                value_range=InputRange(*inputs.bridge.nonoperating_range),
                sources=(
                    _filing_trace(inputs, unit="USD"),
                    _policy_trace("zero-to-net-carrying-value", unit="USD"),
                ),
                fallback_level="current_reported_event_range",
                basis="The pending controlling-interest sale is bounded from zero to reported net held-for-sale assets.",
                accounting_impact_ratio=impact,
                scenario_impact_ratio=impact,
                material_provisional=True,
            )
        )
    if inputs.ticker == "META":
        assumptions.append(
            BoundedAssumption(
                name="AI and data-center capital spending",
                value_range=InputRange(
                    inputs.ttm_capex * 0.90,
                    inputs.ttm_capex,
                    inputs.ttm_capex * 1.10,
                ),
                sources=(
                    _filing_trace(inputs, unit="USD"),
                    _policy_trace("current-capex-plus-minus-ten-percent", unit="USD"),
                ),
                fallback_level="reported_capex_cash_conversion_sensitivity",
                basis="Higher capital spending lowers cash FCFF dollar-for-dollar unless additional cash flow is proven.",
                accounting_impact_ratio=0.0,
                scenario_impact_ratio=impact,
                material_provisional=True,
            )
        )
    if inputs.ttm_spectrum_investment > 0:
        assumptions.append(
            BoundedAssumption(
                name="spectrum-license cash reinvestment",
                value_range=InputRange(
                    inputs.ttm_spectrum_investment,
                    inputs.ttm_spectrum_investment,
                    inputs.ttm_spectrum_investment,
                ),
                sources=(_filing_trace(inputs, unit="USD"),),
                fallback_level="reported_spectrum_cash_investment",
                basis=(
                    "Spectrum-license purchases are deducted in addition to PP&E "
                    "capital spending and retain annual/current filing lineage."
                ),
                accounting_impact_ratio=0.0,
                scenario_impact_ratio=impact,
                material_provisional=True,
            )
        )
    scope = inputs.specialist_context.get("scope_adjustment_range")
    if scope and scope[2] > 0:
        assumptions.append(
            BoundedAssumption(
                name="continuing-versus-consolidated capex scope",
                value_range=InputRange(*scope),
                sources=(
                    _filing_trace(inputs, unit="USD"),
                    _policy_trace("zero-to-discontinued-capital-additions", unit="USD"),
                ),
                fallback_level="current_reported_scope_adjustment",
                basis=(
                    "AT&T continuing OCF is paired with a cash-capex measure whose "
                    "discontinued-operation scope is bounded from zero to the filed "
                    "held-for-sale capital additions."
                ),
                accounting_impact_ratio=impact,
                scenario_impact_ratio=impact,
                material_provisional=True,
            )
        )
    content = inputs.specialist_context.get("content_commitments")
    if content:
        content_increase = float(content["h1_additions_increase"])
        cash_bear_stress = cash_range.base - cash_range.low
        if content_increase <= 0 or cash_bear_stress < content_increase:
            raise ValueError(
                "Netflix bear cash state does not bound reported content-addition growth"
            )
        assumptions.append(
            BoundedAssumption(
                name="forward content commitment cash stress",
                value_range=InputRange(
                    content_increase,
                    content_increase,
                    cash_bear_stress,
                ),
                sources=(
                    _filing_trace(inputs, unit="USD"),
                    _policy_trace("cash-bear-covers-content-addition-growth", unit="USD"),
                ),
                fallback_level="reported_content_commitment_schedule",
                basis=(
                    "Content obligations remain operating commitments, not bridge debt. "
                    "The bear cash-FCFF reduction must at least cover the filed H1 increase "
                    "in streaming-content additions; current OCF already includes content cash payments."
                ),
                accounting_impact_ratio=0.0,
                scenario_impact_ratio=impact,
                material_provisional=True,
            )
        )
        calibration["content_commitments"] = content
    reasons = (
        "CONSOLIDATED_MODEL_FALLBACK",
        "CAPEX_CASH_CONVERSION_SENSITIVITY",
        "SPECIALIST_MODEL_UNCERTAINTY",
    )
    outcome = decide_practical_outcome(
        value_range=value_range,
        model_version=BATCH_02_POLICY_VERSION,
        model_selection_reason=_MODEL_REASON[inputs.ticker],
        assumptions=tuple(assumptions),
        reason_codes=reasons,
        safety=HardSafetyInput(),
        reliability="Low",
    )
    reliability = assess_reliability(
        accounting_low=value_range.base,
        accounting_base=value_range.base,
        accounting_high=value_range.base,
        scenario_low=value_range.low,
        scenario_base=value_range.base,
        scenario_high=value_range.high,
        model_cap="Low",
        source_cap="Low",
        reasons=reasons,
    ).as_dict()
    result = {
        "model_version": BATCH_02_POLICY_VERSION,
        "model_selection_reason": _MODEL_REASON[inputs.ticker],
        "source_financial_statement": {
            "form": inputs.form,
            "period_end": inputs.period_end,
            "filed_date": inputs.filing_date,
            "accession": inputs.accession,
            "url": inputs.source_url,
            "note": "Controlling cutoff-eligible SEC filing used for the cash-FCFF result.",
        },
        "models": {"fcff_dcf": scenarios["base"]},
        "scenarios": {
            name: {"fcff_dcf": value} for name, value in scenarios.items()
        },
        "scenario_range": {
            **value_range.as_dict(),
            "label": "practical source-linked cash-FCFF range",
        },
        "sensitivities": _sensitivities(states["base"], cash_range),
        "public_assumptions": {
            "forecast_policy_version": BATCH_02_POLICY_VERSION,
            "forecast_years": 8,
            "forecast_mode": "consolidated_cash_fcff",
            "initial_revenue_growth": growth["base"],
            "terminal_growth": states["base"].terminal_growth,
            "discount_policy_version": US_BASE.policy_version,
            "discount_calibration_type": calibration["discount_rate"][
                "calibration_type"
            ],
            "policy_wacc": states["base"].wacc,
            "risk_free_rate": US_BASE.risk_free_rate,
            "risk_free_effective_date": US_BASE.risk_free_effective_date,
            "risk_free_source_url": US_BASE.risk_free_source_url,
            "equity_risk_premium": US_BASE.equity_risk_premium,
            "adjusted_fcf_low": cash_range.low,
            "adjusted_fcf_base": cash_range.base,
            "adjusted_fcf_high": cash_range.high,
            "normalized_tax_rate": inputs.normalized_tax_rate,
            "diluted_shares": inputs.bridge.diluted_shares,
            "diluted_shares_low": shares["bull"],
            "diluted_shares_high": shares["bear"],
            "bridge_claims_basis": "Current reported cash/investments less interest-bearing debt, preferred equity, and NCI exactly once.",
        },
        "reliability": reliability,
        "forecast_quality": {
            "policy_version": BATCH_02_POLICY_VERSION,
            "status": "review_required",
            "errors": [],
            "warnings": [
                "Cash conversion and company-history scenarios are provisional; reliability is capped at Low."
            ],
            "checks": {
                "normalized_period": {
                    "status": "pass",
                    "normalized_period_end": inputs.period_end,
                }
            },
        },
        "review": {
            "publication_state": "review_required",
            "confidence_grade": "low",
            "errors": [],
            "warnings": [
                "Practical source-linked cash-FCFF valuation; reliability is capped at Low."
            ],
            "price_dependent_inputs_used": False,
            "prohibited_output_check": {
                "current_price": False,
                "upside_downside": False,
                "buy_hold_sell": False,
                "trading_multiples": False,
            },
        },
        "calibration": calibration,
        "input_provenance": {
            "flows": inputs.flow_sources,
            "bridge": inputs.bridge.sources,
        },
        "practical_policy": {
            "version": BATCH_02_POLICY_VERSION,
            "outcome": asdict(outcome),
            "scenario_inputs": {
                name: asdict(state) for name, state in states.items()
            },
        },
    }
    return result, outcome
