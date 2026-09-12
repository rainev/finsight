#!/usr/bin/env python3
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
from app.us_valuation.batch_31 import BATCH_31_MANIFEST
from app.us_valuation.batch_31_recovery import BATCH_31_RECOVERY_VERSION, build_batch_31_recovery_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_31_history import _public as _initial_public


APPROVED_INITIAL_REPORT_SHA256 = "709e69c3eab54028f395dad7c60ece82c486509da9d013d5d9e9a21999ecd166"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _public(issuer, result):
    value = _initial_public(issuer, result)
    value["public_assumptions"]["forecast_policy_version"] = BATCH_31_RECOVERY_VERSION
    value["forecast_quality"]["policy_version"] = BATCH_31_RECOVERY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_31_RECOVERY_VERSION
    value["model_policy"]["reason"] = result["warning"]
    if issuer.ticker == "ORCL":
        value["public_assumptions"]["forecast_years"] = 10
        value["public_assumptions"]["history_years_used"] = 5
        value["public_assumptions"]["forecast_mode"] = "withheld_after_infrastructure_recovery"
        value["public_assumptions"]["normalization_basis"] = "history_bounded_infrastructure_recovery_attempt"
    value = sanitize_public_artifact(value)
    if value["availability_type"] != result["availability_type"] or value["scenario_range"]["base"] != result["scenario_range"]["base"]:
        raise RuntimeError(issuer.ticker)
    return value


def run(*, initial_root: Path, source_root: Path, structural_root: Path, output_root: Path):
    initial_report_path = Path(initial_root) / "batch-31-report.json"
    initial_report = json.loads(initial_report_path.read_text())
    if _sha(initial_report_path) != APPROVED_INITIAL_REPORT_SHA256 or (initial_report["pass_count"], initial_report["conditional_count"], initial_report["withheld_count"]) != (2, 7, 1):
        raise ValueError("confirmed Batch 31 initial result required")
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = _sha(WATCHLIST)
    withheld_hash = _sha(WITHHELD_REGISTER)
    cases = []
    for issuer in BATCH_31_MANIFEST:
        result = build_batch_31_recovery_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root)
        public = _public(issuer, result)
        outcome = "pass" if result["availability_type"] == "available" else "conditional" if result["availability_type"] == "conditional_estimate" else "withheld"
        case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": result["availability_type"], "reliability": result["history_reliability"]["label"] if result["history_reliability"] else None, "method": result["method"], **result["scenario_range"], "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-31-RECOVERY-1", "batch": 31, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik}, "recovery": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    if before != {str(path): _tree(path) for path in PROTECTED} or watchlist_hash != _sha(WATCHLIST) or withheld_hash != _sha(WITHHELD_REGISTER):
        raise RuntimeError("protected or bookkeeping state changed")
    report = {"schema_version": "FINSIGHT-BATCH-31-RECOVERY-REPORT-1", "batch": 31, "attempted_count": 1, "attempted_tickers": ["ORCL"], "recovered_to_conditional_tickers": [], "still_withheld_tickers": ["ORCL"], "pass_count": sum(case["outcome"] == "pass" for case in cases), "conditional_count": sum(case["outcome"] == "conditional" for case in cases), "withheld_count": sum(case["outcome"] == "withheld" for case in cases), "numeric_count": sum(case["outcome"] != "withheld" for case in cases), "cases": cases, "serving_artifacts_changed": False, "watchlist_changed": False, "withheld_register_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_sha256": withheld_hash}
    _immutable(output_root / "batch-31-recovery-report.json", _json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "attempted_tickers", "recovered_to_conditional_tickers", "still_withheld_tickers", "pass_count", "conditional_count", "withheld_count", "numeric_count")}, sort_keys=True))


if __name__ == "__main__":
    main()
