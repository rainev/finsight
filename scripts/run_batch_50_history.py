#!/usr/bin/env python3
"""Stage Batch 50 candidates without confirmation-state writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_50 import BATCH_50_MANIFEST, BATCH_50_TICKERS, BATCH_50_VALUATION_DATE
from app.us_valuation.batch_50_history import BATCH_50_HISTORY_VERSION, OPERATING_TICKERS, build_batch_50_history_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_08_history import _base
from run_batch_15_history import WITHHELD_REGISTER


def _public(issuer, result):
    assumptions, scenario = result["governed_assumptions"], result["scenario_range"]
    common = {"forecast_policy_version": BATCH_50_HISTORY_VERSION, "forecast_years": assumptions["forecast_years"], "history_policy_version": assumptions["history_policy_version"], "history_years_used": assumptions["history_years_used"], "normalization_basis": assumptions["normalization_basis"], "assumption_source_mix": assumptions["assumption_source_mix"], "equity_floor_applied": False, "equity_floor_basis": assumptions["equity_floor_basis"], "source_policy": "Cutoff-safe SEC filings and filed earnings exhibits with transparent cash conversion; no stock price or analyst target."}
    base = result["scenario_rows"][1]
    if issuer.ticker in OPERATING_TICKERS:
        primary = "fcff_dcf"
        public_assumptions = {**common, "forecast_mode": "enterprise_cash_fcff_exact", "starting_cash_fcff_per_share": base["starting_cash_fcff"] / base["shares"], "cash_conversion": 1.0, "initial_revenue_growth": base["growth_rate"], "policy_wacc": base["wacc"], "terminal_growth": base["terminal_growth"], "bridge_adjustment_per_share": (base["cash"] - base["debt"] - base["preferred_and_nci"]) / base["shares"]}
    else:
        primary = "affo_dcf"
        public_assumptions = {**common, "forecast_mode": "reit_affo_exact", "initial_revenue_growth": base["growth_rate"], "cost_of_equity": base["discount_rate"], "terminal_growth": base["terminal_growth"], "normalized_affo_per_share": base["normalized_affo_per_share"], "nonrecurring_value_adjustment_per_share": 0.0, "recurring_cost_ratio": 0.0}
    model = {"model": primary, "output_type": "intrinsic_value_per_share", "currency": "USD", "intrinsic_value_per_share": scenario["base"], "publication_state": "review_required", "errors": [], "warnings": [result["warning"]]}
    value = _base(issuer, result, primary=primary, model=model, assumptions=public_assumptions)
    value["primary_valuation_method"] = result["method"]
    value["model_policy"]["primary"] = primary
    value["model_policy"].pop("fallback_from", None)
    value["model_policy"]["reason"] = result["warning"]
    value["models"] = {primary: model}
    value["scenarios"] = {name: {primary: {"model": primary, "intrinsic_value_per_share": scenario[key], "publication_state": "review_required"}} for name, key in zip(("bear", "base", "bull"), ("low", "base", "high"))}
    value["issuer"]["classification_reason"] = "Frozen Batch 50 source, route, recurring-capital, event and specialist review; CSGP/CBRE override partition metadata with operating FCFF."
    value["methodology"]["forecast_policy"] = BATCH_50_HISTORY_VERSION
    value["methodology"]["sector_framework"] = result["method"]
    value["forecast_quality"]["policy_version"] = BATCH_50_HISTORY_VERSION
    value["reliability"] = result["history_reliability"]
    if issuer.ticker in OPERATING_TICKERS:
        value["bridge_quality"] = {"blocking_fields": [], "bounded_fields": [], "complete": True, "decision": "complete", "intrinsic_value_range": {"low": scenario["base"], "midpoint": scenario["base"], "high": scenario["base"], "spread_ratio": 0.0, "spread_limit": 0.01}, "reason_codes": [], "usable": True}
        value["review"]["confidence_grade"] = "conditional_low"
    value = sanitize_public_artifact(value)
    if value["availability_type"] == "available":
        value["availability_type"] = "conditional_estimate"
    if value["availability_type"] != "conditional_estimate" or value["scenario_range"]["base"] != scenario["base"] or value["model_policy"]["primary"] != primary:
        raise RuntimeError(issuer.ticker)
    return value


def run(*, source_root: Path, structural_root: Path, event_root: Path, output_root: Path, structural_cache_root: Path):
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_hash = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases, reliability = [], {"High": 0, "Medium": 0, "Low": 0}
    for issuer in BATCH_50_MANIFEST:
        result = build_batch_50_history_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
        public = _public(issuer, result)
        label = result["history_reliability"]["label"]
        reliability[label] += 1
        case = {"ticker": issuer.ticker, "outcome": "conditional", "availability_type": result["availability_type"], "reliability": label, "method": result["method"], **result["scenario_range"], "history_years_used": result["governed_assumptions"]["history_years_used"], "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-50-HISTORY-1", "batch": 50, "valuation_date": BATCH_50_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "history_backed": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watchlist_hash != hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld_hash != hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():
        raise RuntimeError("protected state changed")
    report = {"schema_version": "FINSIGHT-BATCH-50-HISTORY-REPORT-1", "batch": 50, "valuation_date": BATCH_50_VALUATION_DATE, "policy_version": BATCH_50_HISTORY_VERSION, "denominator_tickers": list(BATCH_50_TICKERS), "attempted_count": 10, "pass_count": 0, "conditional_count": 10, "withheld_count": 0, "numeric_count": 10, "pass_tickers": [], "conditional_tickers": list(BATCH_50_TICKERS), "withheld_tickers": [], "reliability_counts": reliability, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_changed": False, "withheld_register_sha256": withheld_hash, "batch_49_dependency_status": "confirmed_batch_49_recovery_catalog_and_bookkeeping_bound", "cases": cases}
    _immutable(output_root / "batch-50-report.json", _json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--event-root", type=Path, required=True)
    parser.add_argument("--structural-cache-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "reliability_counts", "batch_49_dependency_status")}, sort_keys=True))


if __name__ == "__main__":
    main()
