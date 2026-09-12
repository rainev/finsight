#!/usr/bin/env python3
"""Run the one authorized Batch 49 AVB recovery attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_49 import BATCH_49_MANIFEST, BATCH_49_TICKERS, BATCH_49_VALUATION_DATE
from app.us_valuation.batch_49_recovery import ATTEMPTED_TICKERS, RECOVERY_VERSION, recover_batch_49_withheld
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_49_history import _public

CONFIRMED_INITIAL_REPORT_SHA256 = "680369362c54e41bb3187372ee11b7ea611f6da947813859e786772a7e92ecaa"


def run(*, initial_root: Path, output_root: Path) -> dict:
    initial_root, output_root = Path(initial_root), Path(output_root)
    report_path = initial_root / "batch-49-report.json"
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != CONFIRMED_INITIAL_REPORT_SHA256:
        raise ValueError("authorized Batch 49 initial report drifted")
    before = {str(path): _tree(path) for path in PROTECTED}
    watch, withheld = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest(), hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases = []
    for issuer in BATCH_49_MANIFEST:
        private_path, public_path = initial_root / "generated" / issuer.ticker / "valuation-private.json", initial_root / "staged-public" / f"{issuer.ticker}.json"
        private = json.loads(private_path.read_text())
        if issuer.ticker in ATTEMPTED_TICKERS:
            initial = private["history_backed"]
            result = recover_batch_49_withheld(initial=initial)
            case = {"ticker": "AVB", "initial_outcome": "withheld", "recovery_outcome": "withheld", "availability_type": "not_available", "reliability": None, "method": result["method"], "low": None, "base": None, "high": None, "warning": result["warning"]}
            private = {**private, "schema_version": "FINSIGHT-BATCH-49-RECOVERY-1", "history_backed": result, "controlled_outcome": case}
            public = _public(issuer, result)
            public["public_assumptions"]["forecast_policy_version"] = RECOVERY_VERSION
            public["methodology"]["forecast_policy"] = RECOVERY_VERSION
            public["forecast_quality"]["policy_version"] = RECOVERY_VERSION
            public["review"]["confidence_grade"] = "withheld"
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        else:
            case = {"ticker": issuer.ticker, "initial_outcome": "conditional", "recovery_outcome": "not_applicable", "availability_type": "conditional_estimate"}
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", private_path.read_bytes())
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", public_path.read_bytes())
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watch != hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld != hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():
        raise RuntimeError("protected state changed")
    report = {"schema_version": "FINSIGHT-BATCH-49-RECOVERY-REPORT-1", "batch": 49, "valuation_date": BATCH_49_VALUATION_DATE, "policy_version": RECOVERY_VERSION, "denominator_tickers": list(BATCH_49_TICKERS), "attempted_recovery_tickers": ["AVB"], "recovery_attempt_count": 1, "recovered_to_conditional_count": 0, "still_withheld_count": 1, "still_withheld_tickers": ["AVB"], "pass_count": 0, "conditional_count": 9, "withheld_count": 1, "numeric_count": 9, "reliability_counts": {"High": 0, "Medium": 0, "Low": 9}, "authorized_initial_report_sha256": CONFIRMED_INITIAL_REPORT_SHA256, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watch, "withheld_register_changed": False, "withheld_register_sha256": withheld, "cases": cases}
    _immutable(output_root / "batch-49-recovery-report.json", _json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("recovery_attempt_count", "recovered_to_conditional_count", "still_withheld_count", "pass_count", "conditional_count", "withheld_count", "numeric_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
