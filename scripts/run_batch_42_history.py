#!/usr/bin/env python3
"""Stage Batch 42 private/public candidates without touching shared confirmation state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_42 import BATCH_42_MANIFEST, BATCH_42_TICKERS, BATCH_42_VALUATION_DATE
from app.us_valuation.batch_42_history import BATCH_42_HISTORY_VERSION, build_batch_42_history_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_38_history import _public as _prior_public


def _public(issuer, result):
    value = _prior_public(issuer, result)
    value["public_assumptions"]["forecast_policy_version"] = BATCH_42_HISTORY_VERSION
    value["forecast_quality"]["policy_version"] = BATCH_42_HISTORY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_42_HISTORY_VERSION
    value["issuer"]["classification_reason"] = "Frozen Batch 42 source, history, event and model review."
    value["model_policy"]["reason"] = result["warning"]
    value["public_assumptions"]["share_count_basis"] = "The calculator's diluted-share fields are governed scenario denominators anchored to the latest reported common shares. H1 weighted diluted shares are diagnostic only; the +/-1.5% range is an explicit dilution stress, not a reported point-in-time diluted count."
    if result["availability_type"] == "not_available":
        value["public_assumptions"]["forecast_mode"] = "unavailable_negative_resource_cycle_base"
        value["public_assumptions"]["history_years_used"] = result["governed_assumptions"]["history_years_used"]
    value.pop("automated_review", None)
    value = sanitize_public_artifact(value)
    if value["availability_type"] != result["availability_type"] or value["scenario_range"]["base"] != result["scenario_range"]["base"] or value["model_policy"]["primary"] != "fcff_dcf":
        raise RuntimeError(issuer.ticker)
    return value


def run(*, source_root: Path, structural_root: Path, event_root: Path, output_root: Path, structural_cache_root: Path):
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_hash = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases, reliability_counts = [], {"High": 0, "Medium": 0, "Low": 0}
    for issuer in BATCH_42_MANIFEST:
        result = build_batch_42_history_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
        public = _public(issuer, result)
        outcome = "pass" if result["availability_type"] == "available" else "conditional" if result["availability_type"] == "conditional_estimate" else "withheld"
        label = result["history_reliability"]["label"] if result["history_reliability"] else None
        if label:
            reliability_counts[label] += 1
        case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": result["availability_type"], "reliability": label, "method": result["method"], **result["scenario_range"], "history_years_used": result["governed_assumptions"].get("history_years_used"), "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-42-HISTORY-1", "batch": 42, "valuation_date": BATCH_42_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "history_backed": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watchlist_hash != hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld_hash != hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():
        raise RuntimeError("protected state changed")
    report = {"schema_version": "FINSIGHT-BATCH-42-HISTORY-REPORT-1", "batch": 42, "valuation_date": BATCH_42_VALUATION_DATE, "policy_version": BATCH_42_HISTORY_VERSION, "denominator_tickers": list(BATCH_42_TICKERS), "attempted_count": 10, "pass_count": sum(row["outcome"] == "pass" for row in cases), "conditional_count": sum(row["outcome"] == "conditional" for row in cases), "withheld_count": sum(row["outcome"] == "withheld" for row in cases), "numeric_count": sum(row["outcome"] != "withheld" for row in cases), "pass_tickers": [row["ticker"] for row in cases if row["outcome"] == "pass"], "conditional_tickers": [row["ticker"] for row in cases if row["outcome"] == "conditional"], "withheld_tickers": [row["ticker"] for row in cases if row["outcome"] == "withheld"], "reliability_counts": reliability_counts, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_changed": False, "withheld_register_sha256": withheld_hash, "batch_41_dependency_status": "confirmed_batch_41_recovery_catalog_and_bookkeeping_bound", "cases": cases}
    _immutable(output_root / "batch-42-report.json", _json(report))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--event-root", type=Path, required=True)
    parser.add_argument("--structural-cache-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "reliability_counts", "batch_41_dependency_status")}, sort_keys=True))


if __name__ == "__main__":
    main()
