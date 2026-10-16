"""One controlled recovery attempt for Batch 42 EXE and ALB."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_35_history import _instant, _period_flow
from .batch_42 import BATCH_42_TICKERS
from .batch_42_history import BATCH_42_HISTORY_VERSION, build_batch_42_history_result
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf


BATCH_42_RECOVERY_VERSION = "BATCH-42-EXE-ALB-RECOVERY-1.0"
PERIOD = "2026-06-30"
RECOVERED_PASS_TICKERS = frozenset()
RECOVERED_CONDITIONAL_TICKERS = frozenset(set(BATCH_42_TICKERS) - {"EXE", "ALB"})
RECOVERED_WITHHELD_TICKERS = frozenset({"EXE", "ALB"})


def _exe_attempt(initial: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(initial)
    flows = initial["source_ledger"]["flow_sources"]
    tax_rate = initial["source_ledger"]["tax_rate"]
    fields = ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")
    fy = {field: flows[field]["latest_fy"]["value"] for field in fields}
    h1_2025 = {field: flows[field]["prior_h1"]["value"] for field in fields}
    h2_2025 = {field: fy[field] - h1_2025[field] for field in fields}
    h1_2026 = {field: flows[field]["current_h1"]["value"] for field in fields}

    def cash_fcff(row):
        return row["operating_cash_flow"] - row["capital_expenditures"] + abs(row["interest_expense"]) * (1 - tax_rate)

    windows = []
    for label, start, end, row, source_kind in (
        ("H1 2025", "2025-01-01", "2025-06-30", h1_2025, "reported_comparative_h1"),
        ("H2 2025", "2025-07-01", "2025-12-31", h2_2025, "derived_fy_less_reported_h1"),
        ("H1 2026", "2026-01-01", "2026-06-30", h1_2026, "reported_current_h1"),
    ):
        fcff = cash_fcff(row)
        windows.append({"label": label, "period_start": start, "period_end": end, **row, "cash_fcff": fcff, "cash_conversion_margin": fcff / row["revenue"], "source_kind": source_kind, "reported_vs_estimated": "reported" if source_kind.startswith("reported") else "derived_reported_components"})
    if any(abs(h1_2025[field] + h2_2025[field] - fy[field]) > 1 for field in fields):
        raise ValueError("EXE recovery windows do not reconcile")
    margins = tuple(row["cash_conversion_margin"] for row in windows)
    observed_low = min(margins)
    scenario_margins = (observed_low * .5, observed_low, min(.20, sorted(margins)[1]))
    bridge = initial["source_ledger"]["bridge_context"]
    share_base = bridge["base_share_count"]
    shares = (share_base * 1.015, share_base, share_base * .985)
    assumptions = ((-.08, .13, -.02), (-.01, .11, 0.), (.04, .095, .0125))
    diagnostics = []
    for index, name in enumerate(("bear", "base", "bull")):
        growth, wacc, terminal = assumptions[index]
        state = EnterpriseCashFlowState(flows["revenue"]["value"] * scenario_margins[index], growth, terminal, wacc, bridge["cash"], bridge["debt"], 0., bridge["claims"][index], shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        diagnostics.append({"name": name, "value_per_share": float(trace["intrinsic_value_per_share"]), "cash_conversion_margin": scenario_margins[index], "growth": growth, "wacc": wacc, "terminal_growth": terminal, "shares": shares[index], "publication_allowed": False, "trace": trace})
    reason = "Recovery attempted; EXE remains withheld. Three non-overlapping post-combination half-year cash windows reconcile exactly, but they cover only 18 months and H2 2025 is derived as FY less H1. That cannot establish a natural-gas cycle, while Twin Eagle remains signed but unclosed."
    release = "Revalue after at least three comparable combined-company annual periods or issuer-filed pro-forma cash history, with Twin Eagle closing/funding, hedges, gathering commitments and ARO reconciled."
    baseline = BaselineValuation(ticker="EXE", method="post_combination_gas_resource_cycle_fcff", method_version=BATCH_42_RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, release))
    value.update({"model_version": BATCH_42_RECOVERY_VERSION, "warning": reason, "baseline": baseline.as_private_dict()})
    value["governed_assumptions"] = {**initial["governed_assumptions"], "normalization_basis": "three_nonoverlapping_half_year_windows_rejected_as_insufficient_cycle_history", "comparable_operating_windows_used": 3, "diagnostic_cash_conversion_margin": scenario_margins, "reason_codes": ["POST_COMBINATION_HISTORY_INCOMPLETE", "SPECIALIST_MODEL_REQUIRED", "VALUATION_WITHHELD"], "invalidation": release}
    value["source_ledger"] = {**initial["source_ledger"], "post_combination_nonoverlapping_windows": windows, "window_reconciliation": {field: {"fy2025": fy[field], "h1_2025": h1_2025[field], "h2_2025_derived": h2_2025[field], "difference": fy[field] - h1_2025[field] - h2_2025[field]} for field in fields}, "rejected_short_history_diagnostic": {"scenario_rows": diagnostics, "publication_allowed": False, "why_rejected": "Three half-year observations over 18 months, including one derived residual period, do not span a defensible commodity cycle."}, "recovery_attempt": {"attempted": True, "initial_availability_type": "not_available", "final_availability_type": "not_available", "nonoverlapping_window_gate_closed": True, "through_cycle_history_gate_closed": False, "market_price_used": False, "analyst_target_used": False, "competitor_value_used": False}}
    return value


def _share_fact(structural: dict[str, Any], name: str) -> dict[str, Any]:
    rows = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_start") == "2026-01-01" and row.get("period_end") == PERIOD and row.get("unit") == "xbrli:shares" and not row.get("dimensions") and isinstance(row.get("value"), (int, float))]
    values = {float(row["value"]) for row in rows}
    if len(values) != 1:
        raise ValueError(f"ALB {name} unresolved")
    row = rows[-1]
    return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": row["period_start"], "period_end": row["period_end"], "concept": row.get("qname"), "unit": row["unit"], "value": float(row["value"]), "reported_vs_estimated": "reported"}


def _alb_attempt(initial: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(initial)
    flows = initial["source_ledger"]["flow_sources"]
    annual = initial["source_ledger"]["annual_cash_sources"]
    margins = tuple(row["cash_fcff"] / row["revenue"]["value"] for row in annual)
    conversion = _share_fact(structural, "IncrementalCommonSharesAttributableToConversionOfPreferredStock")
    stock_comp = _share_fact(structural, "IncrementalCommonSharesAttributableToShareBasedPaymentArrangements")
    diluted_average = _share_fact(structural, "WeightedAverageNumberOfDilutedSharesOutstanding")
    preferred_dividend = _period_flow(structural, ("DividendsPreferredStock",), PERIOD, target_days=180)
    preferred_claim = _instant(structural, ("PreferredStockValue",), PERIOD)
    common = initial["source_ledger"]["bridge_context"]["latest_common_shares"]
    full_proxy = common["value"] + conversion["value"] + stock_comp["value"]
    if abs(full_proxy - diluted_average["value"]) > diluted_average["value"] * .002:
        raise ValueError("ALB mandatory-conversion proxy does not reconcile")
    scenario_margins = (min(margins), max(0., margins[-1] * .5), min(.15, margins[-1]))
    bridge = initial["source_ledger"]["bridge_context"]
    quarterly_dividend = preferred_dividend["value"] / 2
    claims = (bridge["claims"][0] + quarterly_dividend * 3, bridge["claims"][1] + quarterly_dividend * 2, bridge["claims"][2] + quarterly_dividend)
    shares = (full_proxy * 1.015, full_proxy, full_proxy * .985)
    assumptions = ((-.10, .13, -.02), (-.02, .11, 0.), (.03, .095, .0125))
    diagnostics = []
    for index, name in enumerate(("bear", "base", "bull")):
        growth, wacc, terminal = assumptions[index]
        starting = flows["revenue"]["value"] * max(0., scenario_margins[index])
        if starting == 0:
            raw = (bridge["cash"] - bridge["debt"] - claims[index]) / shares[index]
            trace = {"model": "zero_operating_value_bridge", "intrinsic_value_per_share": raw}
        else:
            state = EnterpriseCashFlowState(starting, growth, terminal, wacc, bridge["cash"], bridge["debt"], 0., claims[index], shares[index])
            trace = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
            raw = float(trace["intrinsic_value_per_share"])
        diagnostics.append({"name": name, "raw_value_per_share": raw, "conditional_value_per_share": max(0., raw), "historical_cash_conversion_margin": scenario_margins[index], "starting_cash_fcff": starting, "growth": growth, "wacc": wacc, "terminal_growth": terminal, "shares": shares[index], "fixed_nci_and_operating_claims": bridge["claims"][index], "preferred_dividend_reserve": claims[index] - bridge["claims"][index], "other_equity_claims": claims[index], "publication_allowed": False, "trace": trace})
    reason = "Recovery attempted; ALB remains withheld. A negative-bear/positive-base diagnostic is mechanically finite, but the proposed base depends on one positive pre-Ketjen year and current cash affected by Talison dividend and working-capital timing. The reported mandatory-conversion shares reconcile only to an H1 weighted-average proxy, not a cutoff-date fully diluted count."
    release = "Revalue after positive comparable post-Ketjen cash history and a point-in-time mandatory-conversion/share schedule reconcile lithium, specialties, Talison distributions, working capital, capex and preferred dividends."
    baseline = BaselineValuation(ticker="ALB", method="lithium_specialty_resource_cycle_fcff", method_version=BATCH_42_RECOVERY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason, release))
    value.update({"model_version": BATCH_42_RECOVERY_VERSION, "warning": reason, "baseline": baseline.as_private_dict()})
    value["governed_assumptions"] = {**initial["governed_assumptions"], "normalization_basis": "negative_cycle_history_and_event_distorted_positive_periods_rejected", "diagnostic_cash_conversion_margin": scenario_margins, "reason_codes": ["NEGATIVE_THROUGH_CYCLE_BASE", "CURRENT_OBJECT_HISTORY_INCOMPLETE", "PREFERRED_CONVERSION_SCOPE_UNRESOLVED", "VALUATION_WITHHELD"], "invalidation": release}
    value["source_ledger"] = {**initial["source_ledger"], "mandatory_convertible_reconciliation": {"current_common_shares": common, "incremental_conversion_shares": conversion, "incremental_share_compensation": stock_comp, "fully_diluted_proxy": full_proxy, "reported_h1_diluted_average": diluted_average, "difference": full_proxy - diluted_average["value"], "preferred_claim": preferred_claim, "preferred_claim_deducted": False, "treatment": "Diagnostic only: conversion shares are included and preferred principal is not deducted; remaining preferred dividends are reserved separately."}, "preferred_dividend_schedule": {"reported_h1_dividends": preferred_dividend, "quarterly_run_rate": quarterly_dividend, "scenario_remaining_quarters": (3, 2, 1), "reported_vs_estimated": "reported_h1_dividend_with_governed_remaining_quarters"}, "rejected_current_recovery_diagnostic": {"scenario_rows": diagnostics, "publication_allowed": False, "why_rejected": "Positive base/bull rely on non-comparable positive periods and a weighted-average conversion proxy rather than a cutoff-date diluted schedule."}, "recovery_attempt": {"attempted": True, "initial_availability_type": "not_available", "final_availability_type": "not_available", "negative_history_preserved": True, "positive_base_diagnostic_found": diagnostics[1]["conditional_value_per_share"] > 0, "post_ketjen_history_gate_closed": False, "point_in_time_conversion_gate_closed": False, "market_price_used": False, "analyst_target_used": False, "competitor_value_used": False}}
    return value


def build_batch_42_recovery_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_42_TICKERS:
        raise ValueError(ticker)
    initial = build_batch_42_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
    if ticker not in {"EXE", "ALB"}:
        value = deepcopy(initial)
        value["model_version"] = BATCH_42_RECOVERY_VERSION
        value["baseline"] = {**value["baseline"], "method_version": BATCH_42_RECOVERY_VERSION}
        return value
    if ticker == "EXE":
        return _exe_attempt(initial)
    structural = json.loads((Path(structural_root) / "ALB/structural-filing.json").read_text())
    return _alb_attempt(initial, structural)


if RECOVERED_PASS_TICKERS | RECOVERED_CONDITIONAL_TICKERS | RECOVERED_WITHHELD_TICKERS != set(BATCH_42_TICKERS):
    raise RuntimeError("Batch 42 recovery classification mismatch")
