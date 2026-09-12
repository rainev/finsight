#!/usr/bin/env python3
"""Run the one authorized Batch 47 merchant-energy recovery attempt."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_47 import BATCH_47_MANIFEST, BATCH_47_TICKERS, BATCH_47_VALUATION_DATE
from app.us_valuation.batch_47_recovery import ATTEMPTED_TICKERS, RECOVERY_VERSION, recover_batch_47_withheld
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_47_history import _public

CONFIRMED_INITIAL_REPORT_SHA256 = "17455670739f86ca707e9cbf1ce44aa0e6f8f17d9bde6a271b62f9431b4d628a"


def run(*, initial_root: Path, source_root: Path, structural_root: Path, output_root: Path) -> dict:
    initial_root, source_root, structural_root, output_root = map(Path, (initial_root, source_root, structural_root, output_root))
    report_path = initial_root / "batch-47-report.json"
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != CONFIRMED_INITIAL_REPORT_SHA256:
        raise ValueError("confirmed Batch 47 initial report drifted")
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_hash = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases = []
    for issuer in BATCH_47_MANIFEST:
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
            result = recover_batch_47_withheld(initial=initial, facts=json.loads(facts_path.read_text()), structural=json.loads(structural_path.read_text()))
            case = {"ticker": issuer.ticker, "initial_outcome": "withheld", "recovery_outcome": "withheld", "availability_type": "not_available", "reliability": None, "method": result["method"], "low": None, "base": None, "high": None, "warning": result["warning"]}
            private = {**private, "schema_version": "FINSIGHT-BATCH-47-RECOVERY-1", "history_backed": result, "controlled_outcome": case}
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
    report = {"schema_version": "FINSIGHT-BATCH-47-RECOVERY-REPORT-1", "batch": 47, "valuation_date": BATCH_47_VALUATION_DATE, "policy_version": RECOVERY_VERSION, "denominator_tickers": list(BATCH_47_TICKERS), "attempted_recovery_tickers": list(ATTEMPTED_TICKERS), "recovery_attempt_count": 3, "recovered_to_conditional_count": 0, "still_withheld_count": 3, "still_withheld_tickers": list(ATTEMPTED_TICKERS), "pass_count": 0, "conditional_count": 7, "withheld_count": 3, "numeric_count": 7, "reliability_counts": {"High": 0, "Medium": 0, "Low": 7}, "confirmed_initial_report_sha256": CONFIRMED_INITIAL_REPORT_SHA256, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_changed": False, "withheld_register_sha256": withheld_hash, "cases": cases}
    _immutable(output_root / "batch-47-recovery-report.json", _json(report))
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
