#!/usr/bin/env python3
"""Stage the one-attempt Batch 41 recovery while pinning seven confirmed artifacts."""
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
from app.us_valuation.batch_41 import BATCH_41_MANIFEST
from app.us_valuation.batch_41_recovery import BATCH_41_RECOVERY_VERSION, RECOVERY_TICKERS, build_batch_41_recovery_result
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_39_history import _public as _residual_public


APPROVED_INITIAL_REPORT_SHA256 = "a1d1825266595ac1ef84c75eded8f6c7cf511608703710a158827d4837c483f8"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _apd_public(issuer, result):
    value = _residual_public(issuer, result)
    value["public_assumptions"]["forecast_policy_version"] = BATCH_41_RECOVERY_VERSION
    value["forecast_quality"]["policy_version"] = BATCH_41_RECOVERY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_41_RECOVERY_VERSION
    value["issuer"]["classification_reason"] = "Frozen Batch 41 APD recovery review."
    value["model_policy"]["reason"] = result["warning"]
    value.pop("automated_review", None)
    value = sanitize_public_artifact(value)
    if value["availability_type"] != "conditional_estimate" or value["scenario_range"]["base"] != result["scenario_range"]["base"] or value["model_policy"]["primary"] != "residual_income":
        raise RuntimeError("APD recovery public mismatch")
    return value


def run(*, initial_root: Path, source_root: Path, structural_root: Path, event_root: Path, output_root: Path, structural_cache_root: Path):
    initial_root = Path(initial_root)
    initial_report_path = initial_root / "batch-41-report.json"
    initial_report = json.loads(initial_report_path.read_text())
    if _sha(initial_report_path) != APPROVED_INITIAL_REPORT_SHA256 or initial_report["withheld_tickers"] != ["APD", "IFF", "IP"]:
        raise ValueError("confirmed Batch 41 initial result required")
    before = {str(path): _tree(path) for path in PROTECTED}
    watchlist_hash = _sha(WATCHLIST)
    withheld_hash = _sha(WITHHELD_REGISTER)
    initial_cases = {row["ticker"]: row for row in initial_report["cases"]}
    cases = []
    for issuer in BATCH_41_MANIFEST:
        initial_private = initial_root / "generated" / issuer.ticker / "valuation-private.json"
        initial_public = initial_root / "staged-public" / f"{issuer.ticker}.json"
        if issuer.ticker not in RECOVERY_TICKERS:
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", initial_private.read_bytes())
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", initial_public.read_bytes())
            cases.append(initial_cases[issuer.ticker])
            continue
        result = build_batch_41_recovery_result(ticker=issuer.ticker, source_root=source_root, structural_root=structural_root, event_root=event_root, structural_cache_root=structural_cache_root)
        if issuer.ticker == "APD":
            public = _apd_public(issuer, result)
            outcome = "conditional"
            label = result["history_reliability"]["label"]
            case = {"ticker": issuer.ticker, "outcome": outcome, "availability_type": result["availability_type"], "reliability": label, "method": result["method"], **result["scenario_range"], "history_years_used": result["governed_assumptions"]["history_years_used"], "warning": result["warning"]}
            private = {"schema_version": "FINSIGHT-BATCH-41-RECOVERY-1", "batch": 41, "valuation_date": "2026-08-14", "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "recovery": result, "controlled_outcome": case}
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
            cases.append(case)
        else:
            case = initial_cases[issuer.ticker]
            private = {"schema_version": "FINSIGHT-BATCH-41-RECOVERY-1", "batch": 41, "valuation_date": "2026-08-14", "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "recovery": result, "controlled_outcome": case}
            _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
            _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", initial_public.read_bytes())
            cases.append(case)
    if before != {str(path): _tree(path) for path in PROTECTED} or watchlist_hash != _sha(WATCHLIST) or withheld_hash != _sha(WITHHELD_REGISTER):
        raise RuntimeError("protected state changed")
    report = {"schema_version": "FINSIGHT-BATCH-41-RECOVERY-REPORT-1", "batch": 41, "valuation_date": "2026-08-14", "policy_version": BATCH_41_RECOVERY_VERSION, "approved_initial_report_sha256": APPROVED_INITIAL_REPORT_SHA256, "attempted_count": 3, "attempted_tickers": list(RECOVERY_TICKERS), "recovered_to_conditional_tickers": ["APD"], "still_withheld_tickers": ["IFF", "IP"], "pass_count": sum(row["outcome"] == "pass" for row in cases), "conditional_count": sum(row["outcome"] == "conditional" for row in cases), "withheld_count": sum(row["outcome"] == "withheld" for row in cases), "numeric_count": sum(row["outcome"] != "withheld" for row in cases), "serving_artifacts_changed": False, "watchlist_changed": False, "watchlist_sha256": watchlist_hash, "withheld_register_changed": False, "withheld_register_sha256": withheld_hash, "cases": cases}
    _immutable(output_root / "batch-41-recovery-report.json", _json(report))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--event-root", type=Path, required=True)
    parser.add_argument("--structural-cache-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_tickers", "recovered_to_conditional_tickers", "still_withheld_tickers", "pass_count", "conditional_count", "withheld_count", "numeric_count")}, sort_keys=True))


if __name__ == "__main__":
    main()
