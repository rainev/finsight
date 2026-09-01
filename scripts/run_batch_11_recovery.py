#!/usr/bin/env python3
"""Apply the single authorized SYY/BG recovery attempt to confirmed Batch 11."""
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

from app.us_valuation.batch_11 import (
    BATCH_11_MANIFEST,
    BATCH_11_TICKERS,
    BATCH_11_VALUATION_DATE,
)
from app.us_valuation.batch_11_recovery import (
    BATCH_11_RECOVERY_VERSION,
    build_bg_recovery_result,
    build_syy_recovery_result,
)
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_11_history import _public


WITHHELD_REGISTER = (
    ROOT / "backend/app/us_valuation/config/universe_reset_withheld.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _case(ticker: str, result: dict) -> dict:
    availability = result["availability_type"]
    outcome = (
        "pass"
        if availability == "available"
        else "conditional"
        if availability == "conditional_estimate"
        else "withheld"
    )
    reliability = result.get("history_reliability")
    return {
        "ticker": ticker,
        "outcome": outcome,
        "availability_type": availability,
        "reliability": None if reliability is None else reliability["label"],
        "method": result["method"],
        **result["scenario_range"],
        "history_years_used": result["governed_assumptions"]["history_years_used"],
        "warning": result["warning"],
    }


def run(
    *,
    initial_root: Path,
    source_root: Path,
    structural_root: Path,
    output_root: Path,
) -> dict:
    initial_root = Path(initial_root)
    source_root = Path(source_root)
    structural_root = Path(structural_root)
    output_root = Path(output_root)
    before = {str(root): _tree(root) for root in PROTECTED}
    watchlist_hash = _sha(WATCHLIST)
    withheld_hash = _sha(WITHHELD_REGISTER)
    cases = []
    attempt_receipts = {}

    for issuer in BATCH_11_MANIFEST:
        if issuer.ticker == "SYY":
            result = build_syy_recovery_result(
                source_root=source_root, structural_root=structural_root
            )
            case = _case("SYY", result)
            private = {
                "schema_version": "FINSIGHT-BATCH-11-RECOVERY-1",
                "batch": 11,
                "valuation_date": BATCH_11_VALUATION_DATE,
                "issuer": {
                    "ticker": issuer.ticker,
                    "cik": issuer.cik,
                    "issuer_name": issuer.issuer_name,
                },
                "recovery": result,
                "controlled_outcome": case,
            }
            public = _public(issuer, result)
            attempt_receipts[issuer.ticker] = result["source_ledger"][
                "recovery_attempt"
            ]
            _immutable(
                output_root / "generated" / "SYY" / "valuation-private.json",
                _json(private),
            )
            _immutable(output_root / "staged-public" / "SYY.json", _json(public))
        elif issuer.ticker == "BG":
            result = build_bg_recovery_result(
                source_root=source_root, structural_root=structural_root
            )
            case = _case("BG", result)
            private = {
                "schema_version": "FINSIGHT-BATCH-11-RECOVERY-1",
                "batch": 11,
                "valuation_date": BATCH_11_VALUATION_DATE,
                "issuer": {
                    "ticker": issuer.ticker,
                    "cik": issuer.cik,
                    "issuer_name": issuer.issuer_name,
                },
                "recovery": result,
                "controlled_outcome": case,
            }
            public = _public(issuer, result)
            attempt_receipts[issuer.ticker] = result["source_ledger"][
                "recovery_attempt"
            ]
            _immutable(
                output_root / "generated" / "BG" / "valuation-private.json",
                _json(private),
            )
            _immutable(output_root / "staged-public" / "BG.json", _json(public))
        else:
            private_path = (
                initial_root
                / "generated"
                / issuer.ticker
                / "valuation-private.json"
            )
            public_path = initial_root / "staged-public" / f"{issuer.ticker}.json"
            private = json.loads(private_path.read_text())
            public = json.loads(public_path.read_text())
            case = private["controlled_outcome"]
            _immutable(
                output_root
                / "generated"
                / issuer.ticker
                / "valuation-private.json",
                _json(private),
            )
            _immutable(
                output_root / "staged-public" / f"{issuer.ticker}.json",
                _json(public),
            )
        cases.append(case)

    after = {str(root): _tree(root) for root in PROTECTED}
    watchlist_hash_after = _sha(WATCHLIST)
    withheld_hash_after = _sha(WITHHELD_REGISTER)
    if (
        before != after
        or watchlist_hash != watchlist_hash_after
        or withheld_hash != withheld_hash_after
    ):
        raise RuntimeError("Batch 11 recovery changed protected or cumulative state")

    report = {
        "schema_version": "FINSIGHT-BATCH-11-RECOVERY-REPORT-1",
        "batch": 11,
        "valuation_date": BATCH_11_VALUATION_DATE,
        "policy_version": BATCH_11_RECOVERY_VERSION,
        "denominator_tickers": list(BATCH_11_TICKERS),
        "attempted_count": 10,
        "recovery_attempted_count": 2,
        "recovery_attempted_tickers": ["SYY", "BG"],
        "recovered_tickers": ["SYY"],
        "remaining_withheld_tickers": ["BG"],
        "recovery_attempts_per_ticker": {"SYY": 1, "BG": 1},
        "pass_count": sum(row["outcome"] == "pass" for row in cases),
        "conditional_count": sum(row["outcome"] == "conditional" for row in cases),
        "withheld_count": sum(row["outcome"] == "withheld" for row in cases),
        "numeric_count": sum(row["outcome"] != "withheld" for row in cases),
        "pass_tickers": [row["ticker"] for row in cases if row["outcome"] == "pass"],
        "conditional_tickers": [
            row["ticker"] for row in cases if row["outcome"] == "conditional"
        ],
        "withheld_tickers": [
            row["ticker"] for row in cases if row["outcome"] == "withheld"
        ],
        "recovery_attempt_receipts": attempt_receipts,
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "watchlist_changed": False,
        "watchlist_sha256": watchlist_hash,
        "withheld_register_changed": False,
        "withheld_register_sha256": withheld_hash,
        "cases": cases,
    }
    _immutable(output_root / "batch-11-recovery-report.json", _json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-root", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    report = run(**vars(parser.parse_args()))
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "pass_count",
                    "conditional_count",
                    "withheld_count",
                    "numeric_count",
                    "recovery_attempted_tickers",
                    "recovered_tickers",
                    "remaining_withheld_tickers",
                    "serving_artifacts_changed",
                    "watchlist_changed",
                    "withheld_register_changed",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
