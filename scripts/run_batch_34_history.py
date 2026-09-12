#!/usr/bin/env python3
"""Reproducible private/public Batch 34 history run (never serving data)."""
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
from app.us_valuation.batch_34 import BATCH_34_MANIFEST, BATCH_34_TICKERS, BATCH_34_VALUATION_DATE
from app.us_valuation.batch_34_history import BATCH_34_HISTORY_VERSION, build_batch_34_history_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_08_history import _public as _prior_public
from run_batch_15_history import WITHHELD_REGISTER


def _public(issuer, result):
    value = _prior_public(issuer, result)
    value["issuer"]["classification_reason"] = "Frozen Batch 34 financial-equity source and history review."
    value["public_assumptions"]["forecast_policy_version"] = BATCH_34_HISTORY_VERSION
    value["public_assumptions"]["forecast_years"] = result["governed_assumptions"]["forecast_years"]
    value["forecast_quality"]["policy_version"] = BATCH_34_HISTORY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_34_HISTORY_VERSION
    value["model_policy"]["reason"] = result["warning"]
    value = sanitize_public_artifact(value)
    if value["availability_type"] != result["availability_type"] or value["scenario_range"]["base"] != result["scenario_range"]["base"]:
        raise RuntimeError(issuer.ticker)
    return value


def run(*, source_root: Path, structural_root: Path, event_root: Path | None, output_root: Path):
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_hash = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases, reliability_counts = [], {"High": 0, "Medium": 0, "Low": 0}
    for issuer in BATCH_34_MANIFEST:
        result = build_batch_34_history_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root)
        public = _public(issuer, result)
        outcome = "pass" if result["availability_type"] == "available" else "conditional" if result["availability_type"] == "conditional_estimate" else "withheld"
        reliability = result["history_reliability"]["label"]
        reliability_counts[reliability] += 1
        case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": result["availability_type"], "reliability": reliability, "method": result["method"], **result["scenario_range"], "history_years_used": result["governed_assumptions"].get("history_years_used"), "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-34-HISTORY-1", "batch": 34, "valuation_date": BATCH_34_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "history_backed": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watchlist_hash != hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld_hash != hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():
        raise RuntimeError("protected state changed")
    report = {"schema_version": "FINSIGHT-BATCH-34-HISTORY-REPORT-1", "batch": 34, "valuation_date": BATCH_34_VALUATION_DATE, "policy_version": BATCH_34_HISTORY_VERSION, "denominator_tickers": list(BATCH_34_TICKERS), "attempted_count": 10, "pass_count": sum(c["outcome"] == "pass" for c in cases), "conditional_count": sum(c["outcome"] == "conditional" for c in cases), "withheld_count": sum(c["outcome"] == "withheld" for c in cases), "numeric_count": sum(c["outcome"] != "withheld" for c in cases), "pass_tickers": [c["ticker"] for c in cases if c["outcome"] == "pass"], "conditional_tickers": [c["ticker"] for c in cases if c["outcome"] == "conditional"], "withheld_tickers": [c["ticker"] for c in cases if c["outcome"] == "withheld"], "reliability_counts": reliability_counts, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_changed": False, "withheld_register_sha256": withheld_hash, "cases": cases}
    _immutable(output_root / "batch-34-report.json", _json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--event-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "reliability_counts")}, sort_keys=True))


if __name__ == "__main__":
    main()
