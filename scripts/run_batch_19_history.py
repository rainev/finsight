#!/usr/bin/env python3
"""Stage initial Batch 19 historical/practical outcomes without protected-state writes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_19 import BATCH_19_MANIFEST, BATCH_19_TICKERS, BATCH_19_VALUATION_DATE
from app.us_valuation.batch_19_history import BATCH_19_HISTORY_VERSION, EQUITY_EARNINGS_TICKERS, build_batch_19_history_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_08_history import _public as _prior_public
from run_batch_15_history import WITHHELD_REGISTER


def _public(issuer, result):
    value = _prior_public(issuer, result)
    value["issuer"]["classification_reason"] = "Frozen Batch 19 Industrials lane plus issuer-specific source, history, continuing-company, finance, event, settlement, and claim review."
    value["public_assumptions"]["forecast_policy_version"] = BATCH_19_HISTORY_VERSION
    value["forecast_quality"]["policy_version"] = BATCH_19_HISTORY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_19_HISTORY_VERSION
    value["model_policy"]["reason"] = result["warning"]
    if issuer.ticker in EQUITY_EARNINGS_TICKERS:
        value["public_assumptions"]["forecast_mode"] = "normalized_equity_earnings"
        value["public_assumptions"]["valuation_basis"] = "mixed_industrial_finance_or_insurance_residual_income"
    else:
        value["public_assumptions"]["forecast_mode"] = "history_backed_normalized_cash_conversion"
        value["public_assumptions"]["forecast_years"] = result["governed_assumptions"]["forecast_years"]
    value = sanitize_public_artifact(value)
    if value["availability_type"] != result["availability_type"] or value["scenario_range"]["base"] != result["scenario_range"]["base"]:
        raise RuntimeError(f"{issuer.ticker}: public mismatch")
    return value


def run(*, source_root: Path, structural_root: Path, event_root: Path, output_root: Path):
    source_root, structural_root, event_root, output_root = map(Path, (source_root, structural_root, event_root, output_root))
    before = {str(root): _tree(root) for root in PROTECTED}
    watch = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases = []
    reliability = {"High": 0, "Medium": 0, "Low": 0}
    for issuer in BATCH_19_MANIFEST:
        result = build_batch_19_history_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root)
        public = _public(issuer, result)
        availability = result["availability_type"]
        outcome = "pass" if availability == "available" else "conditional" if availability == "conditional_estimate" else "withheld"
        label = None if result["history_reliability"] is None else result["history_reliability"]["label"]
        if label:
            reliability[label] += 1
        case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": availability, "reliability": label, "method": result["method"], **result["scenario_range"], "history_years_used": result["governed_assumptions"].get("history_years_used"), "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-19-HISTORY-1", "batch": 19, "valuation_date": BATCH_19_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "history_backed": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    after = {str(root): _tree(root) for root in PROTECTED}
    watch_after = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_after = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    if before != after or watch != watch_after or withheld != withheld_after:
        raise RuntimeError("Batch 19 changed protected or cumulative state")
    report = {"schema_version": "FINSIGHT-BATCH-19-HISTORY-REPORT-1", "batch": 19, "valuation_date": BATCH_19_VALUATION_DATE, "policy_version": BATCH_19_HISTORY_VERSION, "denominator_tickers": list(BATCH_19_TICKERS), "attempted_count": 10, "pass_count": sum(row["outcome"] == "pass" for row in cases), "conditional_count": sum(row["outcome"] == "conditional" for row in cases), "withheld_count": sum(row["outcome"] == "withheld" for row in cases), "numeric_count": sum(row["outcome"] != "withheld" for row in cases), "pass_tickers": [row["ticker"] for row in cases if row["outcome"] == "pass"], "conditional_tickers": [row["ticker"] for row in cases if row["outcome"] == "conditional"], "withheld_tickers": [row["ticker"] for row in cases if row["outcome"] == "withheld"], "reliability_counts": reliability, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watch, "withheld_register_changed": False, "withheld_register_sha256": withheld, "cases": cases}
    _immutable(output_root / "batch-19-report.json", _json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--event-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "reliability_counts", "serving_artifacts_changed", "watchlist_changed", "withheld_register_changed")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
