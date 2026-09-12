#!/usr/bin/env python3
"""Stage the authorized GPN/CPAY recovery attempt without bookkeeping writes."""
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
from app.us_valuation.batch_38 import BATCH_38_MANIFEST
from app.us_valuation.batch_38_recovery import BATCH_38_RECOVERY_VERSION, build_batch_38_recovery_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_38_history import _public as _initial_public


APPROVED_INITIAL_REPORT_SHA256 = "750d2d6ecce8f5ae2aff4fe49fcf3f8181adb2176d287a721d6e2fa2b90070f9"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _public(issuer, result):
    value = _initial_public(issuer, result)
    value["public_assumptions"]["forecast_policy_version"] = BATCH_38_RECOVERY_VERSION
    value["forecast_quality"]["policy_version"] = BATCH_38_RECOVERY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_38_RECOVERY_VERSION
    value["model_policy"]["reason"] = result["warning"]
    if issuer.ticker == "GPN":
        value["public_assumptions"].update({"forecast_years": 8, "history_years_used": 0, "forecast_mode": "withheld_after_post_worldpay_cash_recovery_attempt", "source_policy": "Reported post-close cash and favorable bridge stress remain nonpositive after debt."})
    elif issuer.ticker == "CPAY":
        value["public_assumptions"].update({"forecast_years": 5, "history_years_used": 3, "forecast_mode": "residual_income_exact", "source_policy": "Reported parent/common earnings and equity; customer and restricted cash remain inside funding economics and are not free cash."})
    value.pop("automated_review", None)
    value = sanitize_public_artifact(value)
    if value["availability_type"] != result["availability_type"] or value["scenario_range"]["base"] != result["scenario_range"]["base"]:
        raise RuntimeError(issuer.ticker)
    return value


def run(*, initial_root: Path, source_root: Path, structural_root: Path, event_root: Path, output_root: Path, structural_cache_root: Path | None = None):
    initial_report_path = Path(initial_root) / "batch-38-report.json"
    initial_report = json.loads(initial_report_path.read_text())
    if _sha(initial_report_path) != APPROVED_INITIAL_REPORT_SHA256 or (initial_report["pass_count"], initial_report["conditional_count"], initial_report["withheld_count"]) != (0, 8, 2):
        raise ValueError("confirmed Batch 38 initial result required")
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = _sha(WATCHLIST)
    withheld_hash = _sha(WITHHELD_REGISTER)
    cases = []
    for issuer in BATCH_38_MANIFEST:
        result = build_batch_38_recovery_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
        public = _public(issuer, result)
        outcome = "conditional" if result["availability_type"] == "conditional_estimate" else "withheld" if result["availability_type"] == "not_available" else "pass"
        case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": result["availability_type"], "reliability": result["history_reliability"]["label"] if result["history_reliability"] else None, "method": result["method"], **result["scenario_range"], "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-38-RECOVERY-1", "batch": 38, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik}, "recovery": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    if before != {str(path): _tree(path) for path in PROTECTED} or watchlist_hash != _sha(WATCHLIST) or withheld_hash != _sha(WITHHELD_REGISTER):
        raise RuntimeError("protected or bookkeeping state changed")
    report = {"schema_version": "FINSIGHT-BATCH-38-RECOVERY-REPORT-1", "batch": 38, "attempted_count": 2, "attempted_tickers": ["GPN", "CPAY"], "recovered_to_conditional_tickers": ["CPAY"], "still_withheld_tickers": ["GPN"], "pass_count": sum(row["outcome"] == "pass" for row in cases), "conditional_count": sum(row["outcome"] == "conditional" for row in cases), "withheld_count": sum(row["outcome"] == "withheld" for row in cases), "numeric_count": sum(row["outcome"] != "withheld" for row in cases), "cases": cases, "serving_artifacts_changed": False, "watchlist_changed": False, "withheld_register_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_sha256": withheld_hash}
    _immutable(output_root / "batch-38-recovery-report.json", _json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--event-root", type=Path, required=True)
    parser.add_argument("--structural-cache-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "attempted_tickers", "recovered_to_conditional_tickers", "still_withheld_tickers", "pass_count", "conditional_count", "withheld_count", "numeric_count")}, sort_keys=True))


if __name__ == "__main__":
    main()
