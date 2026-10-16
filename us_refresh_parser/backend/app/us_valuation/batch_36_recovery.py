"""One authorized VLO recovery attempt for Universe Reset Batch 36."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_35_history import _instant, _share, _source
from .batch_36 import BATCH_36_TICKERS
from .batch_36_history import build_batch_36_history_result
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf


BATCH_36_RECOVERY_VERSION = "BATCH-36-VLO-RECOVERY-1.0"
FORECAST_YEARS = 8
RECOVERED_PASS_TICKERS = frozenset()
RECOVERED_CONDITIONAL_TICKERS = frozenset(set(BATCH_36_TICKERS) - {"VLO"})
RECOVERED_WITHHELD_TICKERS = frozenset({"VLO"})


def _companyfacts_annual(facts: dict[str, Any], concept: str, year: int) -> dict[str, Any]:
    start, end = f"{year}-01-01", f"{year}-12-31"
    rows = [row for row in facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", []) if row.get("start") == start and row.get("end") == end and row.get("form") in {"10-K", "10-K/A"} and row.get("filed", "") <= "2026-08-14" and isinstance(row.get("val"), (int, float))]
    if not rows:
        raise ValueError(f"VLO: {concept}/{year} absent")
    row = max(rows, key=lambda value: (value.get("filed", ""), value.get("accn", "")))
    return _source(row, concept)


def _custom_capex_history(normalizer: Any, facts: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    values = []
    for year in (2023, 2024, 2025):
        end = f"{year}-12-31"
        revenue = normalizer.annual_at_end("revenue", end)
        ocf = normalizer.annual_at_end("operating_cash_flow", end)
        interest = normalizer.annual_at_end("interest_expense", end)
        pretax = normalizer.annual_at_end("pretax_income", end)
        tax = normalizer.annual_at_end("income_tax", end)
        if any(value is None for value in (revenue, ocf, interest, pretax, tax)) or revenue.value <= 0:
            raise ValueError(f"VLO: annual FCFF inputs incomplete for {year}")
        capex = _companyfacts_annual(facts, "SegmentExpenditureAdditionToLongLivedAssets", year)
        tax_rate = max(0., min(.30, tax.value / pretax.value)) if pretax.value > 0 else .21
        cash_fcff = cash_fcff_from_reported(operating_cash_flow=ocf.value, capital_expenditures=capex["value"], spectrum_investment=0., interest_expense=abs(interest.value), tax_rate=tax_rate)
        values.append({"period_end": end, "revenue": revenue.as_dict(), "operating_cash_flow": ocf.as_dict(), "capital_expenditures": capex, "interest_expense": interest.as_dict(), "pretax_income": pretax.as_dict(), "income_tax": tax.as_dict(), "tax_rate": tax_rate, "cash_fcff": cash_fcff, "cash_fcff_margin": cash_fcff / revenue.value, "formula": "OCF - SegmentExpenditureAdditionToLongLivedAssets + after-tax interest"})
    if [round(row["capital_expenditures"]["value"] / 1_000_000) for row in values] != [1916, 2057, 1885]:
        raise ValueError("VLO: custom capex lineage changed")
    return tuple(values)


def _vlo_attempt(initial: dict[str, Any], submissions: dict[str, Any], facts: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    normalizer = _normalizer(submissions, facts)
    revenue = normalizer.ttm_flow("revenue")
    ocf = normalizer.ttm_flow("operating_cash_flow")
    interest = normalizer.ttm_flow("interest_expense")
    capex_2025 = _companyfacts_annual(facts, "SegmentExpenditureAdditionToLongLivedAssets", 2025)
    current_capex = _companyfacts_flow(facts, "SegmentExpenditureAdditionToLongLivedAssets", "2026-01-01", "2026-06-30")
    prior_capex = _companyfacts_flow(facts, "SegmentExpenditureAdditionToLongLivedAssets", "2025-01-01", "2025-06-30")
    ttm_capex = capex_2025["value"] + current_capex["value"] - prior_capex["value"]
    if ttm_capex != 1_617_000_000.:
        raise ValueError("VLO: custom TTM capex changed")
    tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    ttm_cash_fcff = cash_fcff_from_reported(operating_cash_flow=ocf["value"], capital_expenditures=ttm_capex, spectrum_investment=0., interest_expense=abs(interest["value"]), tax_rate=tax_rate)
    annual = _custom_capex_history(normalizer, facts)
    # FY2025/FY2024/FY2023 are deliberately used as bear/base/bull.  The
    # unusually strong current TTM is diagnostic only and never a forecast floor.
    margins = (annual[2]["cash_fcff_margin"], annual[1]["cash_fcff_margin"], annual[0]["cash_fcff_margin"])
    cash_row = _instant(structural, ("CashAndCashEquivalentsAtCarryingValue",), "2026-06-30")
    debt_current = _instant(structural, ("DebtCurrent",), "2026-06-30")
    debt_noncurrent = _instant(structural, ("LongTermDebtAndCapitalLeaseObligations",), "2026-06-30")
    nci = _instant(structural, ("MinorityInterest",), "2026-06-30")
    shares = _share(structural, facts, "2026-06-30")
    preferred_absence = {"source_kind": "structural_statement_absence_check", "accession": structural.get("source_accession"), "period_end": "2026-06-30", "searched_concepts": ["PreferredStockLiquidationPreferenceValue", "PreferredStockCarryingValue", "PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", "PreferredStockValue", "PreferredStockSharesOutstanding"], "statement_scope": "The controlling balance sheet and equity facts contain common stock but no preferred class or preferred dividend line.", "treatment": "Source-bounded absence check; this is not a blank-to-zero substitution.", "reported_vs_estimated": "source_bounded_absence_check"}
    debt_repayment = 100_000_000.
    post_cash = cash_row["value"] - debt_repayment
    post_debt = debt_current["value"] + debt_noncurrent["value"] - debt_repayment
    share_values = (shares["value"] * 1.015, shares["value"], shares["value"] * .985)
    growth = (-.03, 0., .02)
    wacc = (.115, .105, .095)
    terminal_growth = (0., .01, .015)
    traces = []
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(revenue["value"] * margins[index], growth[index], terminal_growth[index], wacc[index], post_cash, post_debt, 0., nci["value"], share_values[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        traces.append({"name": name, "raw_pre_port_arthur_claim_value_per_share": trace["intrinsic_value_per_share"], "state": {"starting_cash_fcff": state.cash_fcff, "growth": state.initial_growth, "wacc": state.wacc, "terminal_growth": state.terminal_growth, "cash": state.cash_and_investments, "debt_and_finance_leases": state.interest_bearing_debt, "nci": state.noncontrolling_interests, "preferred": state.preferred_equity, "shares": state.diluted_shares}, "trace": trace})
    diagnostic = tuple(row["raw_pre_port_arthur_claim_value_per_share"] for row in traces)
    if not 0 < diagnostic[0] < diagnostic[1] < diagnostic[2]:
        raise ValueError("VLO: pre-claim diagnostic range invalid")
    event = initial["source_ledger"]["event_sources"][0]
    terms = event["reported_terms"]
    if terms.get("port_arthur_claims_estimable") is not False:
        raise ValueError("VLO: claim gate changed")
    reason = "Recovery attempted; VLO remains withheld. The exact FY2025/TTM capex lineage and a complete pre-claim refining FCFF replay are now recovered, but the controlling filing says Port Arthur third-party losses and possible regulatory exposure cannot reasonably be estimated. Property insurance, recorded repairs, and planned incident capital do not cap those separate claims."
    release = "Revalue only after cutoff-safe evidence provides finite low/base/high Port Arthur third-party and regulatory claim bounds, or explicit evidence that the exposure is immaterial to common-equity value."
    baseline = BaselineValuation(ticker="VLO", method="resource_cycle_fcff", method_version=BATCH_36_RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, release))
    value = deepcopy(initial)
    value.update({"model_version": BATCH_36_RECOVERY_VERSION, "warning": reason, "baseline": baseline.as_private_dict(), "governed_assumptions": {"history_policy_version": initial["governed_assumptions"]["history_policy_version"], "history_years_used": 3, "forecast_years": FORECAST_YEARS, "normalization_basis": "three_year_same_concept_pre_benicia_cycle_with_current_ttm_diagnostic", "assumption_source_mix": "reported_company_history_and_finsight_policy", "cash_fcff_margin": margins, "growth": growth, "wacc": wacc, "terminal_growth": terminal_growth, "shares": share_values, "ttm_cash_fcff_not_used_as_scenario_floor": True, "equity_floor_basis": "not published because claim gate remains open", "reason_codes": ["NORMALIZED_CYCLICAL_RANGE", "MAJOR_EVENT_UNBOUNDED", "VALUATION_WITHHELD"], "invalidation": release}})
    value["source_ledger"] = {**initial["source_ledger"], "capex_recovery": {"annual_same_concept_history": list(annual), "ttm": {"latest_fy": capex_2025, "current_h1": current_capex, "prior_h1": prior_capex, "value": ttm_capex, "formula": "FY2025 + current H1 2026 - prior H1 2025", "stale_standard_capex_rejected": True}}, "reported_ttm_reconstruction": {"revenue": revenue, "operating_cash_flow": ocf, "interest_expense": interest, "capital_expenditures": ttm_capex, "tax_rate": tax_rate, "tax_sources": list(tax_sources), "cash_fcff": ttm_cash_fcff}, "pre_claim_diagnostic": {"publication_allowed": False, "scenario_values": diagnostic, "scenario_traces": traces, "formula": "eight-year enterprise cash-FCFF DCF plus post-repayment cash less post-repayment debt/finance leases and NCI; Port Arthur claim intentionally unresolved and therefore diagnostic is private", "benicia_treatment": "All three margin anchors predate completed April 2026 idling; they cap rather than validate the current TTM and keep recovery withheld.", "bridge": {"reported_cash_2026_06_30": cash_row, "reported_debt_current": debt_current, "reported_debt_noncurrent": debt_noncurrent, "reported_nci": nci, "shares": shares, "preferred_absence": preferred_absence, "july_debt_repayment": debt_repayment, "post_repayment_cash": post_cash, "post_repayment_debt_and_finance_leases": post_debt, "net_debt_change": 0.}}, "port_arthur_claim_gate": {"estimable": False, "insurance_receivable": terms.get("port_arthur_insurance_receivable"), "repair_costs": terms.get("port_arthur_repair_costs"), "planned_incident_capital": terms.get("port_arthur_planned_incident_capital"), "third_party_claim_low": None, "third_party_claim_base": None, "third_party_claim_high": None, "why_property_amounts_do_not_bound_claims": "They address property repair/capital recovery, not personal-injury, property-damage, nuisance, or possible regulatory claims.", "source": event, "release_condition": release}, "recovery_attempt": {"attempted": True, "initial_availability_type": "not_available", "final_availability_type": "not_available", "capex_gate_closed": True, "port_arthur_claim_gate_closed": False, "market_price_used": False, "analyst_target_used": False, "competitor_value_used": False}}
    return value


def _companyfacts_flow(facts: dict[str, Any], concept: str, start: str, end: str) -> dict[str, Any]:
    rows = [row for row in facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", []) if row.get("start") == start and row.get("end") == end and row.get("form") in {"10-Q", "10-Q/A"} and row.get("filed", "") <= "2026-08-14" and isinstance(row.get("val"), (int, float))]
    if not rows:
        raise ValueError(f"VLO: {concept}/{start}/{end} absent")
    row = max(rows, key=lambda value: (value.get("filed", ""), value.get("accn", "")))
    return _source(row, concept)


def build_batch_36_recovery_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path | None = None) -> dict[str, Any]:
    if ticker not in BATCH_36_TICKERS:
        raise ValueError(ticker)
    initial = build_batch_36_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
    if ticker != "VLO":
        value = deepcopy(initial)
        value["model_version"] = BATCH_36_RECOVERY_VERSION
        value["baseline"] = {**value["baseline"], "method_version": BATCH_36_RECOVERY_VERSION}
        return value
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    return _vlo_attempt(initial, submissions, facts, structural)


if RECOVERED_PASS_TICKERS | RECOVERED_CONDITIONAL_TICKERS | RECOVERED_WITHHELD_TICKERS != set(BATCH_36_TICKERS):
    raise RuntimeError("Batch 36 recovery classification mismatch")
