"""One controlled recovery attempt for Batch 47 merchant-energy issuers."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.valuation.bank import residual_income_valuation
from .baseline import AvailabilityType, BaselineValuation
from .batch_46_history import _annual_fact, _structural_flow

RECOVERY_VERSION = "BATCH-47-MERCHANT-RECOVERY-1.0"
ATTEMPTED_TICKERS = ("NRG", "VST", "CEG")
REASON_CODES = {
    "NRG": ("POST_ACQUISITION_HISTORY_INCOMPLETE", "HEDGE_SETTLEMENT_NORMALIZATION_UNRESOLVED", "VALUATION_WITHHELD"),
    "VST": ("MERCHANT_EARNINGS_NORMALIZATION_UNRESOLVED", "HEDGE_SETTLEMENT_NORMALIZATION_UNRESOLVED", "VALUATION_WITHHELD"),
    "CEG": ("POST_ACQUISITION_HISTORY_INCOMPLETE", "MERCHANT_NUCLEAR_NORMALIZATION_UNRESOLVED", "VALUATION_WITHHELD"),
}
HARD_BLOCKERS = {ticker: ("MODEL_UNSUPPORTED",) for ticker in ATTEMPTED_TICKERS}
WARNINGS = {
    "NRG": "Withheld after recovery: post-LS Power/CPower merchant earnings are not comparable to FY2024/FY2025, and derivative marks, collateral, preferred claims, project debt and post-balance repurchases/dividends are not reconciled into normalized parent earnings.",
    "VST": "Withheld after recovery: merchant generation/retail earnings are not normalized for hedge settlement timing, NDT/ARO/Moss Landing effects, preferred claims, nuclear fuel, project financing or pending Cogentrix/Meta/Helix economics.",
    "CEG": "Withheld after recovery: post-Calpine merchant-nuclear earnings are not comparable to FY2024/FY2025, while hedge/fair-value effects, decommissioning, tax credits, integration, asset sales, project debt and NCI remain unnormalized.",
}
RELEASE = {
    "NRG": "Revalue with comparable post-LS Power/CPower parent earnings or cash, settled-hedge reconciliation, current capital returns, preferred/collateral and recourse/nonrecourse debt allocation.",
    "VST": "Revalue with a payment-dated hedge schedule and normalized merchant generation/retail cash after Cogentrix, including NDT/ARO/Moss Landing, preferred/NCI and project financing.",
    "CEG": "Revalue with comparable post-Calpine or issuer-filed pro-forma parent earnings plus decommissioning, hedge/tax-credit, PPA, project-debt, NCI and asset-sale reconciliation.",
}


def _diagnostic(initial: dict[str, Any]) -> dict[str, Any]:
    state = initial["source_ledger"]["ttm_common_equity_state"]
    beginning = state["beginning_common_equity"]["value"]
    ending = state["ending_common_equity"]["value"]
    income = state["common_net_income"]["value"]
    shares = initial["reported_inputs"]["share_count"]
    roe = income / ((beginning + ending) / 2)
    terminal_roe = min(0.105, max(0.075, roe))
    rows = []
    for name, cost in zip(("bear", "base", "bull"), (0.095, 0.085, 0.075)):
        trace = residual_income_valuation(book_value_per_share=ending / shares, current_roe=roe, cost_of_equity=cost, current_payout_ratio=0.65, terminal_roe=terminal_roe, terminal_growth=0.02, years=5)
        rows.append({"name": name, "value_per_share": trace["intrinsic_value"], "current_roe": roe, "cost_of_equity": cost})
    return {"publication_eligible": False, "diagnostic_only": True, "book_value_per_share": ending / shares, "ttm_common_earnings": income, "current_roe": roe, "scenario_rows": rows, "reason": "The raw parent-common residual calculation is finite but its earnings denominator is not a comparable normalized merchant economic state."}


def _event_reference(initial: dict[str, Any], accession: str, *, facts: dict[str, Any]) -> dict[str, Any]:
    row = next(item for item in initial["source_ledger"]["event_sources"]["screened_filings"] if item["accession"] == accession)
    return {"source_kind": "captured_sec_event_document", "accession": accession, "filed": row["filed"], "form": row["form"], "primary_document": row["primary_document"], "documents": row["documents"], "reported_facts": facts, "reported_vs_estimated": "reported_narrative"}


def _nrg(initial: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_equity_and_claims": initial["source_ledger"]["equity_allocation"],
        "earnings_event": _event_reference(initial, "0001013871-26-000018", facts={"post_balance_common_repurchases_through_2026_07_31": 932_000_000.0, "post_balance_common_dividends_through_2026_07_31": 202_000_000.0, "acquired_scope": "LS Power and CPower assets are included in current earnings; comparable post-acquisition annual GAAP earnings are unavailable."}),
        "pjm_capacity_event": _event_reference(initial, "0001104659-26-083743", facts={"cleared_capacity_mw": 6839.0, "average_price_per_mw_day": 325.0, "delivery_period": "2028-2029", "used_as_current_value": False}),
        "normalization_conclusion": "Raw GAAP history combines unlike acquisition perimeters and asymmetric economic-hedge marks; arbitrary ROE or earnings haircuts would not create source-backed parent distributability.",
    }


def _vst(initial: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_equity_and_claims": initial["source_ledger"]["equity_allocation"],
        "earnings_event": _event_reference(initial, "0001692819-26-000017", facts={"q2_2026_unrealized_hedge_loss": 472_000_000.0, "settlement_timing": "future years", "pending_or_future_scope": ["Cogentrix acquisition", "Meta PPAs", "Helix Digital Infrastructure"], "used_as_current_value": False}),
        "financing_events": [_event_reference(initial, accession, facts={"treatment": "financing context only; does not normalize parent merchant earnings"}) for accession in ("0001140361-26-028619", "0001140361-26-026944")],
        "normalization_conclusion": "Preferred-adjusted common equity produces extreme raw ROE while hedge, NDT, ARO, environmental, nuclear-fuel and project-financing cash schedules remain unmatched.",
    }


def _ceg(initial: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    annual = _annual_fact(facts, "CEG", ("UnrealizedGainLossOnDerivatives",), 2025)
    current = _structural_flow(structural, ("UnrealizedGainLossOnDerivatives",), "2026-01-01", "2026-06-30")
    prior = _structural_flow(structural, ("UnrealizedGainLossOnDerivatives",), "2025-01-01", "2025-06-30")
    ttm_derivative = {"value": annual["value"] + current["value"] - prior["value"], "unit": "USD", "method": "FY2025+H1_2026-H1_2025", "sources": [annual, current, prior], "reported_vs_estimated": "derived_reported_components"}
    acquisition = _structural_flow(structural, ("PaymentsToAcquireBusinessesNetOfCashAcquired",), "2026-01-01", "2026-06-30")
    long_debt = _structural_flow(structural, ("ProceedsFromIssuanceOfLongTermDebt",), "2026-01-01", "2026-06-30")
    short_debt = _structural_flow(structural, ("ProceedsFromShortTermDebtMaturingInMoreThanThreeMonths",), "2026-01-01", "2026-06-30")
    return {
        "current_equity_and_claims": initial["source_ledger"]["equity_allocation"],
        "ttm_unrealized_derivative_gain": ttm_derivative,
        "h1_acquisition_cash": acquisition,
        "h1_long_term_debt_issuance": long_debt,
        "h1_short_term_debt_issuance": short_debt,
        "earnings_event": _event_reference(initial, "0001868275-26-000097", facts={"post_calpine_state": True, "pending_brazos_valley_sale": 860_000_000.0, "pending_sale_used_as_current_value": False}),
        "normalization_conclusion": "June parent equity more than doubled after Calpine; pre-combination annual ROEs, current hedge marks and acquisition/integration financing cannot define one recurring post-Calpine parent earnings base.",
    }


def recover_batch_47_withheld(*, initial: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    ticker = initial["ticker"]
    if ticker not in ATTEMPTED_TICKERS or initial.get("availability_type") != "not_available":
        raise ValueError("Batch 47 recovery accepts only the three confirmed withheld issuers")
    evidence = _nrg(initial) if ticker == "NRG" else _vst(initial) if ticker == "VST" else _ceg(initial, facts, structural)
    result = deepcopy(initial)
    result["model_version"] = RECOVERY_VERSION
    result["warning"] = WARNINGS[ticker]
    result["baseline"] = BaselineValuation(ticker=ticker, method=result["method"], method_version=RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(WARNINGS[ticker], RELEASE[ticker])).as_private_dict()
    result["governed_assumptions"] = {**result["governed_assumptions"], "recovery_attempts": 1, "recovery_status": "withheld_after_recovery", "invalidation": RELEASE[ticker]}
    result["source_ledger"] = {**result["source_ledger"], "recovery_attempt": {"attempt_number": 1, "policy_version": RECOVERY_VERSION, "reason_codes": REASON_CODES[ticker], "hard_blockers": HARD_BLOCKERS[ticker], "reported_recovery_evidence": evidence, "private_residual_income_diagnostic": _diagnostic(initial), "final_availability_type": "not_available", "decision": "withheld", "release_condition": RELEASE[ticker], "zero_substitution_used": False}}
    return result


if set(ATTEMPTED_TICKERS) != {"NRG", "VST", "CEG"}:
    raise RuntimeError("Batch 47 recovery contract invalid")
