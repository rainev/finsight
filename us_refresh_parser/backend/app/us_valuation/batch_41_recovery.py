"""One-attempt recovery for Batch 41 APD, IFF, and IP."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from app.valuation.bank import residual_income_valuation

from .baseline import AvailabilityType, BaselineValuation
from .batch_35_history import _instant, _period_flow, _rows, _source
from .batch_40_history import _latest_shares
from .batch_41 import BATCH_41_VALUATION_DATE
from .batch_41_history import build_batch_41_history_result
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, summarize_history_metric
from .reliability import assess_reliability


BATCH_41_RECOVERY_VERSION = "BATCH-41-RECOVERY-1.0"
RECOVERY_TICKERS = ("APD", "IFF", "IP")
RECOVERED_CONDITIONAL_TICKERS = frozenset({"APD"})
STILL_WITHHELD_TICKERS = frozenset({"IFF", "IP"})


def _annual_parent_earnings(companyfacts: dict, concept: str = "NetIncomeLoss") -> tuple[dict, ...]:
    selected = {}
    for row in _rows(companyfacts, concept):
        if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > BATCH_41_VALUATION_DATE or not row.get("start") or not row.get("end") or not isinstance(row.get("val"), (int, float)):
            continue
        try:
            span = (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
        except (TypeError, ValueError):
            continue
        if not 300 <= span <= 380:
            continue
        prior = selected.get(row["end"])
        if prior is None or (row.get("filed", ""), row.get("accn", "")) > (prior.get("filed", ""), prior.get("accn", "")):
            selected[row["end"]] = row
    ends = sorted(selected)[-5:]
    if len(ends) != 5:
        raise ValueError("five annual parent-earnings periods required")
    return tuple({"period_end": end, "value": float(selected[end]["val"]), "source": _source(selected[end], concept)} for end in ends)


def _dimension_point(structural: dict, name: str, period: str, member: str) -> dict:
    rows = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_start") is None and row.get("period_end") == period and row.get("unit") == "USD" and isinstance(row.get("value"), (int, float)) and any(dimension_member.endswith(f":{member}") for _, dimension_member in row.get("dimensions", []))]
    if len(rows) != 1:
        raise ValueError(f"{name} {member}: exact dimensional point unresolved")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural.get("source_accession"), "filed": structural.get("filed_date"), "form": structural.get("form"), "period_start": None, "period_end": period, "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "dimensions": row.get("dimensions"), "reported_vs_estimated": "reported"}


def _recover_apd(initial: dict, source_root: Path, structural_root: Path) -> dict:
    ticker = "APD"
    packet = Path(source_root) / ticker
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    period = "2026-06-30"
    annual = _annual_parent_earnings(companyfacts)
    current = _period_flow(structural, ("NetIncomeLoss",), period, target_days=270)
    prior = _period_flow(structural, ("NetIncomeLoss",), "2025-06-30", target_days=270)
    raw_ttm = annual[-1]["value"] + current["value"] - prior["value"]
    after_tax_exit_charge = _period_flow(structural, ("RestructuringChargesAttributableToParentAfterTax",), period, target_days=270)
    normalized_ttm = raw_ttm + after_tax_exit_charge["value"]
    equity = _instant(structural, ("StockholdersEquity",), period)
    share = _latest_shares(ticker, structural)
    recognized_exit_reserve = _dimension_point(structural, "RestructuringReserveCurrent", period, "A2026ProjectExitCostsMember")
    prior_exit_reserve = _dimension_point(structural, "RestructuringReserveCurrent", period, "A2025ProjectExitCostsMember")
    maximum_exit_cash = 925_000_000.0
    maximum_unrecognized_excess = max(0.0, maximum_exit_cash - recognized_exit_reserve["value"])
    observations = [HistoryObservation("annual", row["period_end"], int(row["period_end"][:4]), row["value"], "USD", "reported annual parent earnings", (row["source"],)) for row in annual]
    observations.append(HistoryObservation("operating_ttm", period, None, normalized_ttm, "USD", "latest FY + current nine months - prior nine months + current after-tax project-exit charge", (annual[-1]["source"], current, prior, after_tax_exit_charge)))
    metric = summarize_history_metric("normalized_parent_earnings", observations)
    if metric is None or normalized_ttm <= 0:
        raise ValueError("APD normalized parent earnings do not support recovery")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "financial_equity_residual_income", BATCH_41_VALUATION_DATE, tuple(row["period_end"] for row in annual), (metric,), True, "reported_and_company_history")
    shares = (share["value"] * 1.015, share["value"], share["value"] * 0.985)
    roes = (0.08, 0.12, min(0.16, normalized_ttm / equity["value"] * 1.05))
    payout = (0.25, 0.35, 0.45)
    cost = (0.11, 0.095, 0.085)
    terminal_roe = (0.08, 0.10, 0.115)
    terminal_growth = (0.01, 0.02, 0.025)
    excess_claims = (maximum_unrecognized_excess, maximum_unrecognized_excess / 2.0, 0.0)
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        scenario_equity = equity["value"] - excess_claims[index]
        trace = residual_income_valuation(book_value_per_share=scenario_equity / shares[index], current_roe=roes[index], cost_of_equity=cost[index], current_payout_ratio=payout[index], terminal_roe=terminal_roe[index], terminal_growth=terminal_growth[index], years=5)
        value = float(trace["intrinsic_value"])
        rows.append({"name": name, "raw_value_per_share": value, "conditional_value_per_share": value, "book_value_per_share": scenario_equity / shares[index], "current_roe": roes[index], "current_payout_ratio": payout[index], "cost_of_equity": cost[index], "terminal_roe": terminal_roe[index], "terminal_growth": terminal_growth[index], "shares": shares[index], "recognized_project_exit_reserve": recognized_exit_reserve["value"], "additional_exit_cash_sensitivity": excess_claims[index], "limited_liability_floor_applied": False})
        traces[name] = trace
    scenario = dict(zip(("low", "base", "high"), (row["raw_value_per_share"] for row in rows)))
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError("APD recovery range is invalid")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("SPECIALIST_MODEL_UNCERTAINTY", "PROJECT_EXIT_CASH_SENSITIVITY"))
    warning = "Conditional Low industrial-gas parent-equity residual-income recovery. Reported common equity already includes recognized project-exit reserves; the current after-tax exit charge is removed from recurring earnings, while only the FY2026 maximum cash exposure above the FY2026 recognized reserve is sensitivity-charged. NGHC VIE debt/NCI stay inside parent equity economics."
    invalidation = "Revalue when project-exit settlements, NGHC funding/offtake, parent earnings, common equity, shares or remaining capex leave the bounded recovery range."
    assumptions = {**profile.public_metadata(), "forecast_years": 5, "normalization_basis": "reported_parent_equity_with_nonrecurring_exit_charge_removed", "assumption_source_mix": "reported_parent_earnings_history_and_governed_residual_income_scenarios", "earnings_multiples": tuple(row["raw_value_per_share"] * row["shares"] / normalized_ttm for row in rows), "current_roe": roes, "current_payout_ratio": payout, "cost_of_equity": cost, "terminal_roe": terminal_roe, "terminal_growth": terminal_growth, "shares": shares, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "calculator_calibration": "Exact residual-income default replay.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker=ticker, method="industrial_gas_parent_equity_residual_income_equity_earnings", method_version=BATCH_41_RECOVERY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(warning, invalidation))
    return {"ticker": ticker, "method": baseline.method, "model_version": BATCH_41_RECOVERY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"raw_ttm_parent_earnings": raw_ttm, "normalized_ttm_parent_earnings": normalized_ttm, "ending_common_equity": equity["value"], "share_count": share["value"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {**initial["source_ledger"], "recovery_attempt": {"attempt_number": 1, "initial_outcome": "withheld", "recovery_outcome": "conditional_numeric_low", "annual_parent_earnings": list(annual), "current_nine_months": current, "prior_nine_months": prior, "raw_ttm_parent_earnings": raw_ttm, "after_tax_project_exit_charge": after_tax_exit_charge, "normalized_ttm_parent_earnings": normalized_ttm, "ending_parent_common_equity": equity, "current_share_count": share, "recognized_fy2026_project_exit_reserve": recognized_exit_reserve, "recognized_fy2025_project_exit_reserve": prior_exit_reserve, "maximum_fy2026_exit_cash": maximum_exit_cash, "maximum_unrecognized_fy2026_excess": maximum_unrecognized_excess, "double_count_prevention": "The FY2026 recognized reserve is already inside reported common equity; only the FY2026 maximum cash exposure above that reserve is sensitivity-charged. The separate FY2025 reserve is not netted against the FY2026 maximum.", "residual_income_trace": {"states": traces}}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_41_recovery_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path) -> dict:
    if ticker not in RECOVERY_TICKERS:
        raise ValueError(ticker)
    initial = build_batch_41_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
    if initial["availability_type"] != "not_available":
        raise ValueError(f"{ticker}: confirmed initial Withheld result required")
    if ticker == "APD":
        return _recover_apd(initial, Path(source_root), Path(structural_root))
    value = dict(initial)
    value["model_version"] = BATCH_41_RECOVERY_VERSION
    value["source_ledger"] = dict(initial["source_ledger"])
    if ticker == "IFF":
        structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
        value["source_ledger"]["disposal_group_liabilities"] = _dimension_point(structural, "LiabilitiesOfDisposalGroupIncludingDiscontinuedOperationCurrent", "2026-06-30", "SegmentDiscontinuedOperationsMember")
        value["source_ledger"]["other_held_for_sale_group"] = {
            "name": "CitraSource",
            "assets": _dimension_point(structural, "AssetsOfDisposalGroupIncludingDiscontinuedOperation", "2026-06-30", "CitraSourceMember"),
            "liabilities": _dimension_point(structural, "LiabilitiesOfDisposalGroupIncludingDiscontinuedOperation", "2026-06-30", "CitraSourceMember"),
            "included_in_food_ingredients_scl_discontinued_net_assets": False,
        }
    value["source_ledger"]["recovery_attempt"] = {"attempt_number": 1, "initial_outcome": "withheld", "recovery_outcome": "withheld", "release_condition_retested": True, "result": "The named economic-object/comparability release condition remains unmet; no positive range was invented."}
    return value


if RECOVERED_CONDITIONAL_TICKERS | STILL_WITHHELD_TICKERS != set(RECOVERY_TICKERS):
    raise RuntimeError("Batch 41 recovery policy mismatch")
