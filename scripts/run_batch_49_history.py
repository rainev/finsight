#!/usr/bin/env python3
"""Stage Batch 49 REIT candidates without confirmation-state writes."""
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
from app.us_valuation.batch_49 import BATCH_49_MANIFEST, BATCH_49_TICKERS, BATCH_49_VALUATION_DATE
from app.us_valuation.batch_49_history import BATCH_49_HISTORY_VERSION, build_batch_49_history_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_08_history import _base
from run_batch_15_history import WITHHELD_REGISTER


def _public(issuer, result):
    assumptions, scenario = result["governed_assumptions"], result["scenario_range"]
    common = {"forecast_policy_version": BATCH_49_HISTORY_VERSION, "forecast_years": assumptions["forecast_years"], "history_policy_version": assumptions["history_policy_version"], "history_years_used": assumptions["history_years_used"], "normalization_basis": assumptions["normalization_basis"], "assumption_source_mix": assumptions["assumption_source_mix"], "equity_floor_applied": False, "equity_floor_basis": assumptions["equity_floor_basis"], "source_policy": "Cutoff-safe SEC-filed REIT metrics and transparent recurring-capital/discount assumptions; no stock price or analyst target."}
    if result["availability_type"] == "not_available":
        model = {"model": "affo_dcf", "output_type": "intrinsic_value_per_share", "currency": "USD", "intrinsic_value_per_share": None, "publication_state": "withheld", "errors": [result["warning"]], "warnings": [assumptions["invalidation"]]}
        public_assumptions = {**common, "forecast_mode": "unavailable_pending_reit_transaction"}
        value = _base(issuer, result, primary="affo_dcf", model=model, assumptions=public_assumptions, review_state="withheld")
        value["review"]["errors"] = [result["warning"]]
    else:
        base = result["scenario_rows"][1]
        model = {"model": "affo_dcf", "output_type": "intrinsic_value_per_share", "currency": "USD", "intrinsic_value_per_share": scenario["base"], "publication_state": "review_required", "errors": [], "warnings": [result["warning"]]}
        public_assumptions = {**common, "forecast_mode": "reit_affo_exact", "initial_revenue_growth": base["growth_rate"], "cost_of_equity": base["discount_rate"], "terminal_growth": base["terminal_growth"], "normalized_affo_per_share": base["normalized_affo_per_share"], "nonrecurring_value_adjustment_per_share": 0.0, "recurring_cost_ratio": 0.0}
        value = _base(issuer, result, primary="affo_dcf", model=model, assumptions=public_assumptions)
    value["primary_valuation_method"] = result["method"]
    value["model_policy"]["primary"] = "affo_dcf"
    value["model_policy"].pop("fallback_from", None)
    value["model_policy"]["reason"] = result["warning"]
    value["models"] = {"affo_dcf": model}
    value["scenarios"] = {} if result["availability_type"] == "not_available" else {name: {"affo_dcf": {"model": "affo_dcf", "intrinsic_value_per_share": scenario[key], "publication_state": "review_required"}} for name, key in zip(("bear", "base", "bull"), ("low", "base", "high"))}
    value["issuer"]["classification_reason"] = "Frozen Batch 49 REIT source, recurring-capital, event and specialist review."
    value["methodology"]["forecast_policy"] = BATCH_49_HISTORY_VERSION
    value["methodology"]["sector_framework"] = result["method"]
    value["forecast_quality"]["policy_version"] = BATCH_49_HISTORY_VERSION
    if result["history_reliability"] is not None:
        value["reliability"] = result["history_reliability"]
    value = sanitize_public_artifact(value)
    if result["availability_type"] == "conditional_estimate" and value["availability_type"] == "available":
        value["availability_type"] = "conditional_estimate"
    if result["availability_type"] == "not_available":
        value["review"]["confidence_grade"] = "withheld"
    if value["availability_type"] != result["availability_type"] or value["scenario_range"]["base"] != scenario["base"] or value["model_policy"]["primary"] != "affo_dcf":
        raise RuntimeError(issuer.ticker)
    return value


def run(*, source_root: Path, structural_root: Path, event_root: Path, output_root: Path, structural_cache_root: Path):
    before = {str(path): _tree(path) for path in PROTECTED}
    watch, withheld = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest(), hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases, reliability = [], {"High": 0, "Medium": 0, "Low": 0}
    for issuer in BATCH_49_MANIFEST:
        result = build_batch_49_history_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
        public = _public(issuer, result)
        label = result["history_reliability"]["label"] if result["history_reliability"] else None
        if label:
            reliability[label] += 1
        outcome = "conditional" if result["availability_type"] == "conditional_estimate" else "withheld"
        case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": result["availability_type"], "reliability": label, "method": result["method"], **result["scenario_range"], "history_years_used": result["governed_assumptions"].get("history_years_used", 0), "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-49-HISTORY-1", "batch": 49, "valuation_date": BATCH_49_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "history_backed": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watch != hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld != hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():
        raise RuntimeError("protected state changed")
    report = {"schema_version": "FINSIGHT-BATCH-49-HISTORY-REPORT-1", "batch": 49, "valuation_date": BATCH_49_VALUATION_DATE, "policy_version": BATCH_49_HISTORY_VERSION, "denominator_tickers": list(BATCH_49_TICKERS), "attempted_count": 10, "pass_count": 0, "conditional_count": sum(row["outcome"] == "conditional" for row in cases), "withheld_count": sum(row["outcome"] == "withheld" for row in cases), "numeric_count": sum(row["outcome"] != "withheld" for row in cases), "pass_tickers": [], "conditional_tickers": [row["ticker"] for row in cases if row["outcome"] == "conditional"], "withheld_tickers": [row["ticker"] for row in cases if row["outcome"] == "withheld"], "reliability_counts": reliability, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watch, "withheld_register_changed": False, "withheld_register_sha256": withheld, "batch_48_dependency_status": "confirmed_batch_48_recovery_catalog_and_bookkeeping_bound", "cases": cases}
    _immutable(output_root / "batch-49-report.json", _json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--event-root", type=Path, required=True)
    parser.add_argument("--structural-cache-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "reliability_counts", "batch_48_dependency_status")}, sort_keys=True))


if __name__ == "__main__":
    main()
