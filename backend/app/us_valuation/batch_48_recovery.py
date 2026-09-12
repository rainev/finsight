"""One controlled recovery attempt for Batch 48 withheld REIT issuers."""
from __future__ import annotations

from copy import deepcopy
from statistics import median
from typing import Any

from app.valuation.ddm import ddm_valuation
from .baseline import AvailabilityType, BaselineValuation
from .practical_models import two_stage_cash_flow_value
from .reliability import assess_reliability

RECOVERY_VERSION = "BATCH-48-REIT-RECOVERY-1.0"
ATTEMPTED_TICKERS = ("WY", "EQR")


def _fact_source(row: dict[str, Any], concept: str, unit: str) -> dict[str, Any]:
    return {"source_kind": "companyfacts", "concept": f"us-gaap:{concept}", "value": float(row["val"]), "unit": unit, "period_start": row.get("start"), "period_end": row.get("end"), "filed": row.get("filed"), "accession": row.get("accn"), "form": row.get("form"), "reported_vs_estimated": "reported"}


def _annual_dividends(facts: dict[str, Any]) -> list[dict[str, Any]]:
    concept = "CommonStockDividendsPerShareCashPaid"
    rows = facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD/shares", [])
    result = []
    for year in range(2021, 2026):
        candidates = [row for row in rows if row.get("form") in {"10-K", "10-K/A"} and row.get("start") == f"{year}-01-01" and row.get("end") == f"{year}-12-31" and row.get("filed", "") <= "2026-08-14" and isinstance(row.get("val"), (int, float)) and not isinstance(row.get("val"), bool)]
        if not candidates:
            raise ValueError(f"WY: annual dividend {year} absent")
        result.append(_fact_source(max(candidates, key=lambda row: (row.get("filed", ""), row.get("accn", ""))), concept, "USD/share"))
    return result


def _event_document(initial: dict[str, Any], accession: str, document_name: str) -> dict[str, Any]:
    event = initial["source_ledger"]["event_sources"]
    rows = [document for document in event["documents"] if document.get("accession") == accession and str(document.get("path", "")).endswith(document_name)]
    if len(rows) != 1:
        raise ValueError(f"event document unresolved: {accession}/{document_name}")
    return rows[0]


def _wy(initial: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    annual = _annual_dividends(facts)
    if [row["value"] for row in annual] != [1.18, 2.17, 1.66, 0.94, 0.84]:
        raise ValueError("WY: dividend history drifted")
    diagnostic = initial["source_ledger"]["private_pre_publication_diagnostic"]
    shares = 721_787_000.0
    adjusted_fad_h1 = 265_000_000.0
    distributions = (adjusted_fad_h1 * 2 * 0.75 / shares, 0.84, median(row["value"] for row in annual))
    rows, traces = [], {}
    for name, distribution in zip(("bear", "base", "bull"), distributions):
        trace = ddm_valuation(last_dividend=distribution, growth_rate=0.0, discount_rate=0.10)
        value = float(trace["intrinsic_value"])
        rows.append({"name": name, "owner_distribution_per_share": distribution, "distribution_growth": 0.0, "cost_of_equity": 0.10, "conditional_value_per_share": value, "raw_value_per_share": value})
        traces[name] = trace
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError("WY: invalid recovered range")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("NORMALIZED_CYCLICAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY"))
    warning = "Conditional Low synthetic timber total-payout baseline, not a dividend-only promise or timberland NAV. Bear maps 75% of annualized H1 Adjusted FAD to per-share owner cash even though the stated framework may use repurchases or supplemental dividends; base uses the current $0.84 annual dividend although H1 coverage is not demonstrated; bull uses the five-year median total dividend."
    invalidation = "Revalue if the stated 75-80% Adjusted-FAD cash-return framework, base dividend, annual dividend history, shares, debt or timber/environmental obligations leave the recorded bounds."
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 6, "forecast_years": 1, "normalization_basis": "current trough cash-return capacity, current base dividend, and five-year median total distribution", "assumption_source_mix": "reported SEC cash-return framework, Adjusted FAD, dividends and diluted shares", "owner_distribution_per_share": distributions, "distribution_growth": (0.0, 0.0, 0.0), "cost_of_equity": (0.10, 0.10, 0.10), "equity_floor_basis": "not applied", "scenario_calibration": "one-driver distribution range; discount and growth remain fixed", "calculator_calibration": "Exact Gordon distribution DDM base replay with locked reported distribution.", "recovery_attempts": 1, "recovery_status": "recovered_to_conditional", "invalidation": invalidation}
    baseline = BaselineValuation(ticker="WY", method="timber_total_payout_ddm", method_version=RECOVERY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(warning, invalidation))
    result = deepcopy(initial)
    result.update({"method": "timber_total_payout_ddm", "model_version": RECOVERY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"h1_adjusted_fad": adjusted_fad_h1, "cash_return_target": (0.75, 0.80), "current_annual_base_dividend_per_share": 0.84, "five_year_dividend_per_share": tuple(row["value"] for row in annual), "h1_diluted_weighted_shares": shares, "current_common_shares_diagnostic": initial["reported_inputs"]["share_count"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "warning": warning, "baseline": baseline.as_private_dict()})
    result["source_ledger"] = {**initial["source_ledger"], "recovery_attempt": {"attempt_number": 1, "policy_version": RECOVERY_VERSION, "decision": "conditional", "final_availability_type": "conditional_estimate", "reason_codes": ("TIMBER_CASH_RETURN_FALLBACK", "NORMALIZED_CYCLICAL_RANGE", "SPECIALIST_MODEL_UNCERTAINTY"), "hard_blockers": (), "zero_substitution_used": False}, "cash_return_evidence": {"q2_earnings_exhibit": _event_document(initial, "0001193125-26-326124", "wy-ex99_1.htm"), "controlling_filing": initial["source_ledger"]["controlling_filing"], "h1_adjusted_fad": {"value": adjusted_fad_h1, "unit": "USD", "period_start": "2026-01-01", "period_end": "2026-06-30", "accession": "0001193125-26-326124", "reported_vs_estimated": "reported"}, "cash_return_target": {"low": 0.75, "high": 0.80, "basis": "Company plans base dividend plus variable cash return to achieve 75-80% of annual Adjusted FAD.", "accession": "0001193125-26-328606", "reported_vs_estimated": "reported_policy"}, "annual_dividend_history": annual, "h1_diluted_weighted_shares": {"value": shares, "unit": "shares", "period_start": "2026-01-01", "period_end": "2026-06-30", "accession": "0001193125-26-328606", "reported_vs_estimated": "reported"}, "current_h1_dividend_per_share": 0.42, "current_annualized_base_dividend_per_share": 0.84}, "distribution_ddm_trace": traces, "rejected_initial_fcff_diagnostic": {**diagnostic, "reason": "The negative bear enterprise residual is not floored or published; recovery uses a separate source-linked owner-distribution model."}}
    return result


def _eqr(initial: dict[str, Any]) -> dict[str, Any]:
    recurring_per_share = 94_566_000.0 / 384_527_893.0 * 2
    standalone_affo = 4.02 - recurring_per_share
    standalone = {name: two_stage_cash_flow_value(cash_flow_per_share=standalone_affo, growth_rate=0.02, growth_years=8, terminal_growth=0.02, discount_rate=rate) for name, rate in zip(("bear", "base", "bull"), (0.0975, 0.0925, 0.0875))}
    warning = "Withheld after recovery: EQR withdrew standalone guidance on July 22, shareholders approved the AvalonBay merger on August 12, and closing was expected August 17. The filed combined-company statements remain preliminary GAAP pro formas without source-bounded AFFO, final debt/cash, closing shares, purchase accounting or integration costs."
    release = "Revalue after a cutoff-safe closed-company filing and combined AFFO/capital reconciliation, or after explicit authorization of a standalone pre-close-only valuation that expires at closing."
    result = deepcopy(initial)
    result["model_version"] = RECOVERY_VERSION
    result["warning"] = warning
    result["baseline"] = BaselineValuation(ticker="EQR", method="reit_affo_per_share_dcf", method_version=RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(warning, release)).as_private_dict()
    result["governed_assumptions"] = {**result["governed_assumptions"], "recovery_attempts": 1, "recovery_status": "withheld_after_recovery", "invalidation": release}
    result["source_ledger"] = {**result["source_ledger"], "recovery_attempt": {"attempt_number": 1, "policy_version": RECOVERY_VERSION, "decision": "withheld", "final_availability_type": "not_available", "reason_codes": ("MAJOR_EVENT_UNBOUNDED", "POST_COMBINATION_HISTORY_INCOMPLETE", "VALUATION_WITHHELD"), "hard_blockers": ("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"), "zero_substitution_used": False}, "standalone_preclose_diagnostic": {"publication_eligible": False, "annualized_normalized_ffo_per_share": 4.02, "annualized_recurring_capex_per_share": recurring_per_share, "normalized_affo_proxy_per_share": standalone_affo, "scenario_values": standalone, "reason": "Short-lived standalone EQR object; guidance withdrawn and invalid at closing."}, "combined_proforma_diagnostic": {"source": _event_document(initial, "0001193125-26-328612", "eqr-ex99_1.htm"), "fixed_exchange_ratio": 2.793, "h1_2026_common_income": 499_515_000.0, "h1_2026_depreciation": 1_110_483_000.0, "h1_2026_gain_on_sale_and_other_income": 163_667_000.0, "h1_2026_diluted_shares": 779_245_000.0, "fy2025_common_income": 470_999_000.0, "fy2025_depreciation": 2_833_542_000.0, "fy2025_gain_on_sale_and_other_income": 983_019_000.0, "fy2025_diluted_shares": 789_325_000.0, "publication_eligible": False, "reason": "Preliminary Article 11 GAAP pro forma lacks combined AFFO, final closing bridge and integration/PPA scope."}}
    return result


def recover_batch_48_withheld(*, initial: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    ticker = initial["ticker"]
    if ticker not in ATTEMPTED_TICKERS or initial.get("availability_type") != "not_available":
        raise ValueError("Batch 48 recovery accepts only the two confirmed withheld issuers")
    return _wy(initial, facts) if ticker == "WY" else _eqr(initial)


if set(ATTEMPTED_TICKERS) != {"WY", "EQR"}:
    raise RuntimeError("Batch 48 recovery contract invalid")
