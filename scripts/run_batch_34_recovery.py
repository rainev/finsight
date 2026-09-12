#!/usr/bin/env python3
"""Run the single conservative Batch 34 recovery attempt without promotion."""
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
from app.us_valuation.batch_34_recovery import BATCH_34_RECOVERY_VERSION, build_batch_34_recovery_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_08_history import _public as _initial_public
from run_batch_15_history import WITHHELD_REGISTER


CONFIRMED_INITIAL_REPORT_SHA256 = "920a679e0ce7c6f30dbb3246afff29da1ad1008507b494cb1935a7fcdf1ae995"
CONFIRMED_INITIAL_COUNTS = {
    "attempted_count": 10,
    "pass_count": 0,
    "conditional_count": 10,
    "withheld_count": 0,
    "numeric_count": 10,
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _public(issuer, result):
    value = _initial_public(issuer, result)
    # Batch 34 uses residual income for financial-equity issuers.  The shared
    # compatibility builder defaults Pass rows to FCFF; leaving that surface
    # in place would advertise a model and bridge that were never used.
    if result["availability_type"] == "available":
        model = dict(value.get("models", {}).get("fcff_dcf", {}))
        model["model"] = "residual_income"
        model["output_type"] = "intrinsic_value_per_share"
        value["models"] = {"residual_income": model}
        value["model_policy"] = {
            **value.get("model_policy", {}),
            "primary": "residual_income",
            "fallback_from": None,
        }
        value.pop("bridge_quality", None)
    value["public_assumptions"]["forecast_policy_version"] = BATCH_34_RECOVERY_VERSION
    value["forecast_quality"]["policy_version"] = BATCH_34_RECOVERY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_34_RECOVERY_VERSION
    value["model_policy"]["reason"] = result["warning"]
    return sanitize_public_artifact(value)


def run(*, initial_root: Path, source_root: Path, structural_root: Path, event_root: Path | None, output_root: Path):
    initial_root = Path(initial_root)
    initial_report_path = initial_root / "batch-34-report.json"
    initial_report = json.loads(initial_report_path.read_text())
    if _sha(initial_report_path) != CONFIRMED_INITIAL_REPORT_SHA256:
        raise ValueError("confirmed Batch 34 initial report hash mismatch")
    if (
        initial_report.get("batch") != 34
        or tuple(initial_report.get("denominator_tickers", ())) != BATCH_34_TICKERS
        or any(initial_report.get(key) != expected for key, expected in CONFIRMED_INITIAL_COUNTS.items())
    ):
        raise ValueError("confirmed Batch 34 initial report order/count mismatch")
    before = {str(path): _tree(path) for path in PROTECTED}
    watch_hash = _sha(WATCHLIST)
    withheld_hash = _sha(WITHHELD_REGISTER)
    cases = []
    reliability_counts = {"High": 0, "Medium": 0, "Low": 0}
    for issuer in BATCH_34_MANIFEST:
        result = build_batch_34_recovery_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root)
        public = _public(issuer, result)
        outcome = "pass" if result["availability_type"] == "available" else "conditional" if result["availability_type"] == "conditional_estimate" else "withheld"
        reliability = result["history_reliability"]["label"]
        reliability_counts[reliability] += 1
        case = {"ticker": issuer.ticker, "initial_outcome": "conditional", "outcome": outcome, "availability_type": result["availability_type"], "reliability": reliability, "method": result["method"], **result["scenario_range"], "recovery_outcome": result["source_ledger"]["recovery_attempt"]["recovery_outcome"], "repair_tested": result["source_ledger"]["recovery_attempt"]["repair_tested"], "repair_status": result["source_ledger"]["recovery_attempt"]["repair_status"], "release_condition": result["source_ledger"]["recovery_attempt"]["release_condition"]}
        private = {"schema_version": "FINSIGHT-BATCH-34-RECOVERY-1", "batch": 34, "valuation_date": BATCH_34_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "recovery": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watch_hash != _sha(WATCHLIST) or withheld_hash != _sha(WITHHELD_REGISTER):
        raise RuntimeError("recovery changed protected state")
    report = {"schema_version": "FINSIGHT-BATCH-34-RECOVERY-REPORT-1", "batch": 34, "valuation_date": BATCH_34_VALUATION_DATE, "policy_version": BATCH_34_RECOVERY_VERSION, "initial_report_sha256": CONFIRMED_INITIAL_REPORT_SHA256, "initial_report_denominator_tickers": list(BATCH_34_TICKERS), "initial_report_counts": dict(CONFIRMED_INITIAL_COUNTS), "attempted_count": 10, "recovery_attempted_tickers": list(BATCH_34_TICKERS), "recovered_pass_tickers": [c["ticker"] for c in cases if c["outcome"] == "pass"], "recovered_conditional_tickers": [c["ticker"] for c in cases if c["outcome"] == "conditional"], "recovered_withheld_tickers": [c["ticker"] for c in cases if c["outcome"] == "withheld"], "pass_count": sum(c["outcome"] == "pass" for c in cases), "conditional_count": sum(c["outcome"] == "conditional" for c in cases), "withheld_count": sum(c["outcome"] == "withheld" for c in cases), "numeric_count": sum(c["outcome"] != "withheld" for c in cases), "reliability_counts": reliability_counts, "serving_artifacts_changed": False, "watchlist_changed": False, "withheld_register_changed": False, "watchlist_sha256": watch_hash, "withheld_register_sha256": withheld_hash, "cases": cases}
    _immutable(output_root / "batch-34-recovery-report.json", _json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--event-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "reliability_counts")}, sort_keys=True))


if __name__ == "__main__":
    main()
