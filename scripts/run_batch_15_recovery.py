#!/usr/bin/env python3
"""Stage the one Batch 15 withheld-company recovery attempt without bookkeeping writes."""
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

from app.us_valuation.batch_15 import BATCH_15_MANIFEST, BATCH_15_VALUATION_DATE
from app.us_valuation.batch_15_recovery import BATCH_15_RECOVERY_TICKERS, BATCH_15_RECOVERY_VERSION, build_batch_15_recovery_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER, _public


ISSUERS = {issuer.ticker: issuer for issuer in BATCH_15_MANIFEST}


def run(*, source_root: Path, structural_root: Path, recovery_source_root: Path, confirmed_public_root: Path, output_root: Path):
    source_root, structural_root, recovery_source_root, confirmed_public_root, output_root = map(Path, (source_root, structural_root, recovery_source_root, confirmed_public_root, output_root))
    before = {str(root): _tree(root) for root in PROTECTED}
    watchlist_hash = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_hash = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    cases = []
    for ticker in BATCH_15_RECOVERY_TICKERS:
        issuer = ISSUERS[ticker]
        result = build_batch_15_recovery_result(ticker=ticker, source_root=source_root, structural_root=structural_root, recovery_source_root=recovery_source_root)
        public = _public(issuer, result)
        case = {"ticker": ticker, "initial_outcome": "withheld", "recovery_outcome": "withheld", "availability_type": result["availability_type"], "reliability": None, "method": result["method"], "low": None, "base": None, "high": None, "warning": result["warning"]}
        private = {"schema_version": "FINSIGHT-BATCH-15-RECOVERY-1", "batch": 15, "valuation_date": BATCH_15_VALUATION_DATE, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "recovery": result, "controlled_outcome": case}
        _immutable(output_root / "generated" / ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{ticker}.json", _json(public))
        cases.append(case)
    after = {str(root): _tree(root) for root in PROTECTED}
    watchlist_after = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    withheld_after = hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
    if before != after or watchlist_hash != watchlist_after or withheld_hash != withheld_after:
        raise RuntimeError("Batch 15 recovery changed protected or cumulative state before bookkeeping")
    recovery_public = {path.stem: path.read_bytes() for path in (output_root / "staged-public").glob("*.json")}
    for issuer in BATCH_15_MANIFEST:
        raw = recovery_public.get(issuer.ticker)
        if raw is None:
            source = confirmed_public_root / f"{issuer.ticker}.json"
            raw = source.read_bytes()
        _immutable(output_root / "final-public" / f"{issuer.ticker}.json", raw)
    if len(tuple((output_root / "final-public").glob("*.json"))) != 10:
        raise RuntimeError("Batch 15 recovery final public denominator changed")
    report = {"schema_version": "FINSIGHT-BATCH-15-RECOVERY-REPORT-1", "batch": 15, "valuation_date": BATCH_15_VALUATION_DATE, "model_version": BATCH_15_RECOVERY_VERSION, "attempted_tickers": list(BATCH_15_RECOVERY_TICKERS), "attempted_count": 3, "recovered_pass_count": 0, "recovered_conditional_count": 0, "remaining_withheld_count": 3, "remaining_withheld_tickers": list(BATCH_15_RECOVERY_TICKERS), "final_batch_counts": {"pass": 4, "conditional": 3, "withheld": 3, "numeric": 7}, "final_public_count": 10, "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after, "watchlist_changed_before_bookkeeping": False, "watchlist_sha256_before_bookkeeping": watchlist_hash, "withheld_register_changed_before_bookkeeping": False, "withheld_register_sha256_before_bookkeeping": withheld_hash, "cases": cases}
    _immutable(output_root / "batch-15-recovery-report.json", _json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--recovery-source-root", required=True, type=Path)
    parser.add_argument("--confirmed-public-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "recovered_pass_count", "recovered_conditional_count", "remaining_withheld_count", "final_batch_counts", "final_public_count", "serving_artifacts_changed", "watchlist_changed_before_bookkeeping", "withheld_register_changed_before_bookkeeping")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
