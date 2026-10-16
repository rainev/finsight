"""One controlled recovery attempt for Batch 46 withheld utilities."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.valuation.bank import residual_income_valuation
from .baseline import AvailabilityType, BaselineValuation
from .batch_46_history import (
    BATCH_46_HISTORY_VERSION,
    PERIOD,
    _annual_fact,
    _structural_flow,
)
from .reliability import assess_reliability

RECOVERY_VERSION = "BATCH-46-WITHHELD-RECOVERY-1.0"
ATTEMPTED_TICKERS = ("EIX", "AES", "PCG", "SRE")

REASON_CODES = {
    "EIX": ("WILDFIRE_CLAIMS_UNBOUNDED", "REGULATORY_RECOVERY_UNRESOLVED", "VALUATION_WITHHELD"),
    "AES": ("PARENT_PROJECT_CASH_PERIMETER_UNRESOLVED", "NORMALIZED_PARENT_EARNINGS_UNSUPPORTED", "VALUATION_WITHHELD"),
    "PCG": ("WILDFIRE_CLAIMS_UNBOUNDED", "PREFERRED_CONVERSION_SCOPE_UNRESOLVED", "SHARE_DENOMINATOR_UNRELIABLE", "VALUATION_WITHHELD"),
    "SRE": ("POST_TRANSACTION_SCOPE_UNRESOLVED", "PARENT_PROJECT_CASH_PERIMETER_UNRESOLVED", "VALUATION_WITHHELD"),
}
HARD_BLOCKERS = {
    "EIX": ("CLAIMS_UNBOUNDED", "MODEL_UNSUPPORTED"),
    "AES": ("MODEL_UNSUPPORTED",),
    "PCG": ("CLAIMS_UNBOUNDED", "UNRELIABLE_SHARES"),
    "SRE": ("MODEL_UNSUPPORTED",),
}
WARNINGS = {
    "EIX": "Conditional Low moderated Edison/SCE residual-income baseline. Booked wildfire accruals and expected recoveries remain in reported equity/assets; governed incremental wildfire stress is applied without treating the $4.3B Wildfire Fund context as a complete exposure cap. Future claims, insurance exhaustion, fund sufficiency, CPUC/FERC recovery, securitization and parent/SCE funding can move value outside this range.",
    "AES": "Conditional Low parent-common AES residual-income baseline. Recurring ROE removes source-linked business-sale gains and does not automatically add impairment charges back. Parent/project cash distributability, recourse/nonrecourse debt, NCI, temporary equity, tax credits and financing amendments remain material.",
    "PCG": "Conditional Low moderated PG&E parent residual-income baseline. Booked wildfire claims, settlements, recoveries, preferred stock and NCI remain in reported equity without double counting; governed incremental wildfire stress and the reported share-denominator conflict are reflected in the range. Future wildfire and regulatory exposure can fall outside it.",
    "SRE": "Conditional Low pre-transaction SRE parent-common residual-income baseline. It represents the reported June 30 parent equity and TTM earnings state, not a post-KKR or post-Ecogas value. Regulated utilities, LNG/infrastructure, temporary equity, NCI, project funding, wildfire and regulatory outcomes remain material.",
}
RELEASE = {
    "EIX": "Revalue if a filed Edison/SCE liability or recovery ceiling, wildfire settlement, insurance/Wildfire Fund decision, securitization, preferred/NCI allocation or share state changes materially.",
    "AES": "Revalue if normalized parent earnings, sale/impairment treatment, project/parent cash or debt allocation, NCI/temporary-equity claims, shares or credit terms change materially.",
    "PCG": "Revalue when PG&E files a reconciled parent/Utility wildfire and regulatory-loss ceiling, preferred-conversion schedule, post-bond bridge or authoritative common-share denominator.",
    "SRE": "Revalue when KKR/Ecogas closing accounting supplies proceeds, tax/NCI effects, retained ownership, temporary-equity treatment and a segment parent-common cash/equity bridge.",
}


def _fact(
    structural: dict[str, Any],
    local_name: str,
    *,
    period_start: str | None,
    period_end: str = PERIOD,
    dimension_tokens: tuple[str, ...] = (),
    no_dimensions: bool = False,
) -> dict[str, Any]:
    rows = []
    for row in structural.get("facts", []):
        dimensions = row.get("dimensions") or []
        flattened = " ".join(str(value) for pair in dimensions for value in pair)
        if (
            row.get("local_name") == local_name
            and row.get("period_start") == period_start
            and row.get("period_end") == period_end
            and isinstance(row.get("value"), (int, float))
            and not isinstance(row.get("value"), bool)
            and (not no_dimensions or not dimensions)
            and all(token in flattened for token in dimension_tokens)
        ):
            rows.append(row)
    values = {float(row["value"]) for row in rows}
    if len(values) != 1:
        raise ValueError(f"{local_name}: exact recovery fact unresolved")
    row = rows[-1]
    return {
        "source_kind": "structural_xbrl",
        "concept": row.get("qname"),
        "value": values.pop(),
        "unit": row.get("unit"),
        "period_start": period_start,
        "period_end": period_end,
        "dimensions": row.get("dimensions") or [],
        "filed": structural.get("filed_date"),
        "accession": structural.get("source_accession"),
        "reported_vs_estimated": "reported",
    }


def _diagnostic(initial: dict[str, Any]) -> dict[str, Any]:
    state = initial["source_ledger"]["ttm_common_equity_state"]
    beginning = state["beginning_common_equity"]["value"]
    ending = state["ending_common_equity"]["value"]
    income = state["common_net_income"]["value"]
    shares = initial["reported_inputs"]["share_count"]
    current_roe = income / ((beginning + ending) / 2)
    terminal_roe = min(0.105, max(0.075, current_roe))
    rows = []
    for name, cost in zip(("bear", "base", "bull"), (0.095, 0.085, 0.075)):
        trace = residual_income_valuation(
            book_value_per_share=ending / shares,
            current_roe=current_roe,
            cost_of_equity=cost,
            current_payout_ratio=0.65,
            terminal_roe=terminal_roe,
            terminal_growth=0.02,
            years=5,
        )
        rows.append({"name": name, "value_per_share": trace["intrinsic_value"], "cost_of_equity": cost, "current_roe": current_roe})
    return {
        "publication_eligible": False,
        "diagnostic_only": True,
        "book_value_per_share": ending / shares,
        "ttm_common_earnings": income,
        "current_roe": current_roe,
        "scenario_rows": rows,
        "reason": "A mechanically finite residual-income output does not cure the unresolved claim, earnings-normalization, share, project-funding or transaction-perimeter gate.",
    }


def _eix_evidence(structural: dict[str, Any]) -> dict[str, Any]:
    return {
        "wildfire_accrual": _fact(structural, "LossContingencyAccrualAtCarryingValue", period_start=None, no_dimensions=True),
        "wildfire_loss_h1": _fact(structural, "LossContingencyLossInPeriod", period_start="2026-01-01", no_dimensions=True),
        "expected_wildfire_fund_recovery_h1": _fact(structural, "LossContingencyExpectedRecoveriesFromWildfireFund", period_start="2026-01-01", dimension_tokens=("SouthernCaliforniaEdisonCompanyMember", "EatonFireMember")),
        "wildfire_fund_maximum_liability_context": _fact(structural, "LossContingencyWildfireInsuranceFundMaximumLiability", period_start="2026-01-01", dimension_tokens=("SouthernCaliforniaEdisonCompanyMember",)),
        "wildfire_fund_claim_paying_capacity_context": _fact(structural, "LossContingencyWildfireInsuranceFundEstimatedClaimPayingCapacity", period_start=None, dimension_tokens=("SouthernCaliforniaEdisonCompanyMember",)),
        "older_event_possible_loss": _fact(structural, "LossContingencyEstimateOfPossibleLoss", period_start=None, dimension_tokens=("A20172018WildfireMudslideEventsMember",)),
        "non_overlap_conclusion": "The $4.3B maximum-liability and $21B claim-paying-capacity facts describe Wildfire Fund mechanics, not a complete ceiling on EIX common-equity exposure; they are not subtracted as invented claims or added as recoveries.",
    }


def _pcg_evidence(structural: dict[str, Any]) -> dict[str, Any]:
    return {
        "wildfire_related_claims": _fact(structural, "WildfireRelatedClaims", period_start=None, no_dimensions=True),
        "wildfire_class_action_accrual": _fact(structural, "LossContingencyAccrualAtCarryingValue", period_start=None, dimension_tokens=("WildfireRelatedClassActionMember",)),
        "dixie_possible_loss": _fact(structural, "LossContingencyEstimateOfPossibleLoss", period_start=None, dimension_tokens=("DixieFire2021Member",)),
        "dixie_settlement": _fact(structural, "LossContingencySettlementAmount", period_start=None, dimension_tokens=("DixieFire2021Member",)),
        "dixie_wildfire_fund_receivable": _fact(structural, "LossContingencyWildfireFundRecoveriesReceivable", period_start=None, dimension_tokens=("DixieFire2021Member",)),
        "regulatory_disallowance_cap_context": _fact(structural, "LossContingencyDisallowanceCapTransmissionAndDistributionEquityRateBase", period_start=None, no_dimensions=True),
        "non_overlap_conclusion": "Booked claims, settlements, receivables and the $5.1B rate-base disallowance context do not form a mutually exclusive ceiling on future inverse-condemnation, wildfire and regulatory exposure; none is zero-imputed or double-counted.",
    }


def _aes_evidence(facts: dict[str, Any], structural: dict[str, Any], initial: dict[str, Any]) -> dict[str, Any]:
    def ttm(concept: str) -> dict[str, Any]:
        annual = _annual_fact(facts, "AES", (concept,), 2025)
        current = _structural_flow(structural, (concept,), "2026-01-01", PERIOD)
        prior = _structural_flow(structural, (concept,), "2025-01-01", "2025-06-30")
        return {"value": annual["value"] + current["value"] - prior["value"], "method": "latest_fy_plus_current_h1_minus_prior_h1", "unit": "USD", "sources": [annual, current, prior], "reported_vs_estimated": "derived_reported_components"}
    allocation = initial["source_ledger"]["equity_allocation"]
    return {
        "fy2024_gain_on_sale_of_business": _annual_fact(facts, "AES", ("GainLossOnSaleOfBusiness",), 2024),
        "fy2025_gain_on_sale_of_business": _annual_fact(facts, "AES", ("GainLossOnSaleOfBusiness",), 2025),
        "ttm_gain_on_sale_of_business": ttm("GainLossOnSaleOfBusiness"),
        "ttm_asset_impairment_charges": ttm("AssetImpairmentCharges"),
        "reported_nci": allocation["noncontrolling_interest"],
        "reported_temporary_or_redeemable_equity": allocation["temporary_or_redeemable_equity"],
        "normalization_conclusion": "Subtracting the sale gain alone and adding back impairment alone move earnings in opposite directions without proving future project returns or parent distributability; no unsupported normalized earnings point is selected.",
    }


def _publication_rows(ticker: str, initial: dict[str, Any], evidence: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    state = initial["source_ledger"]["ttm_common_equity_state"]
    ending = float(state["ending_common_equity"]["value"])
    shares = float(initial["reported_inputs"]["share_count"])
    if ticker == "EIX":
        configs = (
            (ending - 4_300_000_000.0, shares * 1.015, 0.09, 0.10, 0.55, 0.09, 0.01, 4_300_000_000.0),
            (ending - 1_000_000_000.0, shares, 0.10, 0.085, 0.65, 0.10, 0.02, 1_000_000_000.0),
            (ending - 250_000_000.0, shares * 0.985, 0.11, 0.075, 0.75, 0.11, 0.025, 250_000_000.0),
        )
        basis = "reported common equity less governed incremental wildfire stress; moderated 9%-11% sustainable ROE; coordinated dilution and discount-rate scenarios"
    elif ticker == "PCG":
        configs = (
            (ending - 1_000_000_000.0, 2_680_110_496.0, 0.08, 0.10, 0.45, 0.08, 0.01, 1_000_000_000.0),
            (ending - 500_000_000.0, 2_285_000_000.0, 0.09, 0.085, 0.55, 0.09, 0.02, 500_000_000.0),
            (ending - 100_000_000.0, 2_201_000_000.0, 0.10, 0.075, 0.65, 0.10, 0.025, 100_000_000.0),
        )
        basis = "reported common equity less governed incremental wildfire/regulatory stress; history-bounded 8%-10% ROE; disclosed cover/basic/diluted share conflict"
    elif ticker == "AES":
        history = initial["source_ledger"]["annual_common_equity_history"]
        normalized = (
            (history[0]["common_net_income"]["value"] - evidence["fy2024_gain_on_sale_of_business"]["value"]) / history[0]["common_equity"]["value"],
            (history[1]["common_net_income"]["value"] - evidence["fy2025_gain_on_sale_of_business"]["value"]) / history[1]["common_equity"]["value"],
            (state["common_net_income"]["value"] - evidence["ttm_gain_on_sale_of_business"]["value"]) / ((state["beginning_common_equity"]["value"] + state["ending_common_equity"]["value"]) / 2),
        )
        roe = sum(normalized) / len(normalized)
        configs = tuple((ending, shares, roe, cost, 0.65, 0.105, 0.02, 0.0) for cost in (0.095, 0.085, 0.075))
        evidence["normalized_roe_observations"] = normalized
        evidence["governed_recurring_roe"] = roe
        basis = "mean FY2024/FY2025/TTM parent-common ROE after removing reported business-sale gains; impairments retained; cost-of-equity-only public range"
    else:
        roe = state["common_net_income"]["value"] / ((state["beginning_common_equity"]["value"] + state["ending_common_equity"]["value"]) / 2)
        configs = tuple((ending, shares, roe, cost, 0.65, 0.075, 0.02, 0.0) for cost in (0.095, 0.085, 0.075))
        basis = "pre-transaction reported parent-common equity and TTM ROE; KKR/Ecogas effects excluded; cost-of-equity-only public range"
    rows, traces = [], {}
    for name, (equity, scenario_shares, roe, cost, payout, terminal_roe, growth, claim) in zip(("bear", "base", "bull"), configs):
        trace = residual_income_valuation(book_value_per_share=equity / scenario_shares, current_roe=roe, cost_of_equity=cost, current_payout_ratio=payout, terminal_roe=terminal_roe, terminal_growth=growth, years=5)
        rows.append({"name": name, "raw_value_per_share": trace["intrinsic_value"], "conditional_value_per_share": trace["intrinsic_value"], "book_value_per_share": equity / scenario_shares, "ending_common_equity": equity, "incremental_unresolved_claim_stress": claim, "current_roe": roe, "cost_of_equity": cost, "current_payout_ratio": payout, "terminal_roe": terminal_roe, "terminal_growth": growth, "shares": scenario_shares})
        traces[name] = trace
    return rows, {"basis": basis, "traces": traces}


def _sre_evidence(structural: dict[str, Any], initial: dict[str, Any]) -> dict[str, Any]:
    allocation = initial["source_ledger"]["equity_allocation"]
    return {
        "si_partners_held_for_sale_assets": _fact(structural, "AssetsOfDisposalGroupIncludingDiscontinuedOperation", period_start=None, dimension_tokens=("SIPartnersMember",)),
        "si_partners_held_for_sale_liabilities": _fact(structural, "LiabilitiesOfDisposalGroupIncludingDiscontinuedOperation", period_start=None, dimension_tokens=("SIPartnersMember",)),
        "si_partners_noncurrent_debt": _fact(structural, "DisposalGroupIncludingDiscontinuedOperationDebtNoncurrent", period_start=None, dimension_tokens=("SIPartnersMember",)),
        "ecogas_expected_gain_low": _fact(structural, "DisposalGroupIncludingDiscontinuedOperationExpectedGainOnSale", period_start="2026-04-01", dimension_tokens=("MinimumMember", "EcogasMember")),
        "ecogas_expected_gain_high": _fact(structural, "DisposalGroupIncludingDiscontinuedOperationExpectedGainOnSale", period_start="2026-04-01", dimension_tokens=("MaximumMember", "EcogasMember")),
        "ecogas_parent_after_tax_gain_low": _fact(structural, "DisposalGroupIncludingDiscontinuedOperationExpectedGainOnSaleAfterTaxAttributableToParent", period_start="2026-04-01", dimension_tokens=("MinimumMember", "EcogasMember")),
        "ecogas_parent_after_tax_gain_high": _fact(structural, "DisposalGroupIncludingDiscontinuedOperationExpectedGainOnSaleAfterTaxAttributableToParent", period_start="2026-04-01", dimension_tokens=("MaximumMember", "EcogasMember")),
        "reported_nci": allocation["noncontrolling_interest"],
        "reported_temporary_or_redeemable_equity": allocation["temporary_or_redeemable_equity"],
        "scope_conclusion": "The bounded Ecogas gain does not bound the much larger pending KKR/SI ownership, tax, NCI, project-debt and continuing-earnings transition, so it is not substituted for a post-close parent value.",
    }


def recover_batch_46_withheld(*, initial: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    ticker = initial["ticker"]
    if ticker not in ATTEMPTED_TICKERS or initial.get("availability_type") != "not_available":
        raise ValueError("Batch 46 recovery accepts only the four confirmed withheld issuers")
    evidence = _eix_evidence(structural) if ticker == "EIX" else _pcg_evidence(structural) if ticker == "PCG" else _aes_evidence(facts, structural, initial) if ticker == "AES" else _sre_evidence(structural, initial)
    result = deepcopy(initial)
    rows, publication = _publication_rows(ticker, initial, evidence)
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: authorized recovery range invalid")
    result["model_version"] = RECOVERY_VERSION
    result["method"] = "regulated_utility_residual_income"
    result["availability_type"] = "conditional_estimate"
    result["scenario_rows"] = rows
    result["scenario_range"] = scenario
    result["warning"] = WARNINGS[ticker]
    result["baseline"] = BaselineValuation(ticker=ticker, method=result["method"], method_version=RECOVERY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(WARNINGS[ticker], RELEASE[ticker])).as_private_dict()
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="Low", reasons=("CONSOLIDATED_MIXED_UTILITY_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"))
    result["history_reliability"] = reliability.as_dict()
    base = rows[1]
    result["reported_inputs"] = {"ttm_common_earnings": initial["source_ledger"]["ttm_common_equity_state"]["common_net_income"]["value"], "beginning_common_equity": initial["source_ledger"]["ttm_common_equity_state"]["beginning_common_equity"]["value"], "ending_common_equity": initial["source_ledger"]["ttm_common_equity_state"]["ending_common_equity"]["value"], "share_count": initial["reported_inputs"]["share_count"]}
    result["governed_assumptions"] = {**result["governed_assumptions"], "forecast_years": 5, "recovery_attempts": 1, "recovery_status": "conditional_numeric_low", "normalization_basis": publication["basis"], "assumption_source_mix": "reported parent-common history and claims plus governed moderated recovery assumptions", "current_roe": tuple(row["current_roe"] for row in rows), "current_payout_ratio": tuple(row["current_payout_ratio"] for row in rows), "cost_of_equity": tuple(row["cost_of_equity"] for row in rows), "terminal_roe": tuple(row["terminal_roe"] for row in rows), "terminal_growth": tuple(row["terminal_growth"] for row in rows), "shares": tuple(row["shares"] for row in rows), "scenario_calibration": "coordinated moderated recovery scenarios; private source and assumption effects remain traceable", "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "calculator_calibration": "Exact residual-income base assumptions replay through the public calculator.", "invalidation": RELEASE[ticker]}
    result["source_ledger"] = {**result["source_ledger"], "recovery_residual_income_trace": publication["traces"], "recovery_attempt": {"attempt_number": 1, "policy_version": RECOVERY_VERSION, "reason_codes": tuple(code for code in REASON_CODES[ticker] if code != "VALUATION_WITHHELD"), "former_hard_blockers": HARD_BLOCKERS[ticker], "reported_recovery_evidence": evidence, "private_pre_authorized_diagnostic": _diagnostic(initial), "authorized_publication_basis": "User explicitly authorized a warned Conditional Low value after reviewing the unresolved facts.", "final_availability_type": "conditional_estimate", "decision": "conditional_numeric_low", "release_condition": RELEASE[ticker], "zero_substitution_used": False}}
    return result


if set(ATTEMPTED_TICKERS) != {"EIX", "AES", "PCG", "SRE"} or BATCH_46_HISTORY_VERSION != "BATCH-46-UTILITY-EQUITY-1.0":
    raise RuntimeError("Batch 46 recovery contract invalid")
