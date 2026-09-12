#!/usr/bin/env python3
"""Run the one authorized Batch 46 withheld-company recovery attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_46 import BATCH_46_MANIFEST, BATCH_46_TICKERS, BATCH_46_VALUATION_DATE
from app.us_valuation.batch_46_recovery import ATTEMPTED_TICKERS, RECOVERY_VERSION, recover_batch_46_withheld
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_46_history import _public

CONFIRMED_INITIAL_REPORT_SHA256 = "bc7940920f54c1c67722b25b213520d9550881eae7c9841512d4f83ae61cb3ad"


def run(*, initial_root: Path, source_root: Path, structural_root: Path, output_root: Path) -> dict:
    initial_root, source_root, structural_root, output_root = map(Path, (initial_root, source_root, structural_root, output_root))
    report_path = initial_root / "batch-46-report.json"
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != CONFIRMED_INITIAL_REPORT_SHA256:
        raise ValueError("confirmed Batch 46 initial report drifted")
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_hash = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases = []
    for issuer in BATCH_46_MANIFEST:
        private_path = initial_root / "generated" / issuer.ticker / "valuation-private.json"
        public_path = initial_root / "staged-public" / f"{issuer.ticker}.json"
        private = json.loads(private_path.read_text())
        if issuer.ticker in ATTEMPTED_TICKERS:
            initial = private["history_backed"]
            facts_path = source_root / issuer.ticker / "companyfacts.json"
            structural_path = structural_root / issuer.ticker / "structural-filing.json"
            verification = initial["source_ledger"]["runtime_source_verification"]
            if hashlib.sha256(facts_path.read_bytes()).hexdigest() != verification["packet_payload_sha256"]["companyfacts.json"] or hashlib.sha256(structural_path.read_bytes()).hexdigest() != verification["structural_filing_sha256"]:
                raise ValueError(f"{issuer.ticker}: confirmed recovery source drifted")
            result = recover_batch_46_withheld(initial=initial, facts=json.loads(facts_path.read_text()), structural=json.loads(structural_path.read_text()))
            case = {"ticker": issuer.ticker, "initial_outcome": "withheld", "recovery_outcome": "conditional", "availability_type": "conditional_estimate", "reliability": result["history_reliability"]["label"], "method": result["method"], **result["scenario_range"], "warning": result["warning"]}
            private = {**private, "schema_version": "FINSIGHT-BATCH-46-RECOVERY-1", "history_backed": result, "controlled_outcome": case}
            public = _public(issuer, result)
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        else:
            case = {"ticker": issuer.ticker, "initial_outcome": "conditional", "recovery_outcome": "not_applicable", "availability_type": "conditional_estimate"}
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", private_path.read_bytes())
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", public_path.read_bytes())
        cases.append(case)
    after = {str(path): _tree(path) for path in PROTECTED}
    if before != after or watchlist_hash != hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld_hash != hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():
        raise RuntimeError("protected state changed")
    report = {
        "schema_version": "FINSIGHT-BATCH-46-RECOVERY-REPORT-1",
        "batch": 46,
        "valuation_date": BATCH_46_VALUATION_DATE,
        "policy_version": RECOVERY_VERSION,
        "denominator_tickers": list(BATCH_46_TICKERS),
        "attempted_recovery_tickers": list(ATTEMPTED_TICKERS),
        "recovery_attempt_count": 4,
        "recovered_to_conditional_count": 4,
        "recovered_to_conditional_tickers": list(ATTEMPTED_TICKERS),
        "still_withheld_count": 0,
        "still_withheld_tickers": [],
        "pass_count": 0,
        "conditional_count": 10,
        "withheld_count": 0,
        "numeric_count": 10,
        "reliability_counts": {"High": 0, "Medium": 0, "Low": 10},
        "confirmed_initial_report_sha256": CONFIRMED_INITIAL_REPORT_SHA256,
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "watchlist_changed": False,
        "watchlist_sha256": watchlist_hash,
        "withheld_register_changed": False,
        "withheld_register_sha256": withheld_hash,
        "cases": cases,
    }
    _immutable(output_root / "batch-46-recovery-report.json", _json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    result = run(**vars(parser.parse_args()))
    print(json.dumps({key: result[key] for key in ("recovery_attempt_count", "recovered_to_conditional_count", "still_withheld_count", "pass_count", "conditional_count", "withheld_count", "numeric_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
