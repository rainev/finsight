#!/usr/bin/env python3
"""Stage the exceptional whole-Batch-16 baseline repair without serving/bookkeeping writes."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_16 import BATCH_16_MANIFEST, BATCH_16_TICKERS, BATCH_16_VALUATION_DATE
from app.us_valuation.batch_16_whole_repair import (
    BATCH_16_WHOLE_REPAIR_VERSION,
    LEGAL_TAIL_TICKERS,
    build_batch_16_whole_repair_result,
)
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_16_history import _public as _initial_public


APPROVED_INITIAL_REPORT_SHA256 = "9e06770e13fbf523b7a0512f11f40a85a62a57083c1f7aa0d7a0449525567959"
# Canonical run_batch_07_history._tree digest. Audit 78's older digest used a
# different tree-hash helper; the report/file identities below are also checked.
APPROVED_INITIAL_TREE_SHA256 = "c7de409215df71c371f84ddebcfe27ac7d57bb6f869248719c33cdf2d9bfd107"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_initial(initial_root: Path) -> dict:
    report_path = Path(initial_root) / "batch-16-report.json"
    report = json.loads(report_path.read_text())
    if (
        report.get("schema_version") != "FINSIGHT-BATCH-16-HISTORY-REPORT-1"
        or tuple(report.get("denominator_tickers", ())) != BATCH_16_TICKERS
        or (report.get("pass_count"), report.get("conditional_count"), report.get("withheld_count")) != (2, 2, 6)
        or _sha(report_path) != APPROVED_INITIAL_REPORT_SHA256
        or _tree(initial_root) != APPROVED_INITIAL_TREE_SHA256
    ):
        raise ValueError("Batch 16 whole repair requires the approved confirmed initial candidate")
    return report


def _public(issuer, result: dict) -> dict:
    value = _initial_public(issuer, result)
    value["public_assumptions"]["forecast_policy_version"] = BATCH_16_WHOLE_REPAIR_VERSION
    value["forecast_quality"]["policy_version"] = BATCH_16_WHOLE_REPAIR_VERSION
    value["methodology"]["forecast_policy"] = BATCH_16_WHOLE_REPAIR_VERSION
    value["model_policy"]["reason"] = result["warning"]
    if issuer.ticker in LEGAL_TAIL_TICKERS:
        if issuer.ticker == "ELV":
            value["public_assumptions"].update(
                {
                    "forecast_mode": "normalized_equity_earnings",
                    "valuation_basis": "managed_care_parent_common_equity_residual_income",
                }
            )
        else:
            value["public_assumptions"]["forecast_mode"] = "reported_operations_with_unquantified_legal_tail"
    value = sanitize_public_artifact(value)
    if (
        value["availability_type"] != result["availability_type"]
        or any(value["scenario_range"].get(key) != result["scenario_range"][key] for key in ("low", "base", "high"))
    ):
        raise RuntimeError(f"{issuer.ticker}: whole-repair public mismatch")
    return value


def run(
    *,
    initial_root: Path,
    source_root: Path,
    structural_root: Path,
    event_root: Path,
    output_root: Path,
) -> dict:
    initial_root, source_root, structural_root, event_root, output_root = map(
        Path, (initial_root, source_root, structural_root, event_root, output_root)
    )
    initial = _validate_initial(initial_root)
    before = {str(root): _tree(root) for root in PROTECTED}
    watch_before = _sha(WATCHLIST)
    withheld_before = _sha(WITHHELD_REGISTER)
    initial_cases = {row["ticker"]: row for row in initial["cases"]}
    cases = []
    for issuer in BATCH_16_MANIFEST:
        result = build_batch_16_whole_repair_result(
            ticker=issuer.ticker,
            source_root=source_root,
            structural_root=structural_root,
            event_root=event_root,
        )
        public = _public(issuer, result)
        availability = result["availability_type"]
        outcome = "pass" if availability == "available" else "conditional" if availability == "conditional_estimate" else "withheld"
        initial_case = initial_cases[issuer.ticker]
        case = {
            "ticker": issuer.ticker,
            "initial_outcome": initial_case["outcome"],
            "initial_availability_type": initial_case["availability_type"],
            "outcome": outcome,
            "availability_type": availability,
            "reliability": None if result["history_reliability"] is None else result["history_reliability"]["label"],
            "method": result["method"],
            **result["scenario_range"],
            "history_years_used": result["governed_assumptions"].get("history_years_used"),
            "warning": result["warning"],
        }
        private = {
            "schema_version": "FINSIGHT-BATCH-16-WHOLE-REPAIR-1",
            "batch": 16,
            "valuation_date": BATCH_16_VALUATION_DATE,
            "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name},
            "whole_repair": result,
            "controlled_outcome": case,
        }
        _immutable(output_root / "generated" / issuer.ticker / "valuation-private.json", _json(private))
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)

    after = {str(root): _tree(root) for root in PROTECTED}
    watch_after = _sha(WATCHLIST)
    withheld_after = _sha(WITHHELD_REGISTER)
    if before != after or watch_before != watch_after or withheld_before != withheld_after:
        raise RuntimeError("Batch 16 whole repair changed protected or cumulative state during staging")
    counts = Counter(row["outcome"] for row in cases)
    reliability = Counter(row["reliability"] for row in cases if row["reliability"])
    report = {
        "schema_version": "FINSIGHT-BATCH-16-WHOLE-REPAIR-REPORT-1",
        "batch": 16,
        "valuation_date": BATCH_16_VALUATION_DATE,
        "policy_version": BATCH_16_WHOLE_REPAIR_VERSION,
        "denominator_tickers": list(BATCH_16_TICKERS),
        "repair_scope": "exceptional_user_authorized_whole_batch_revisit",
        "automatic_recovery_attempt_reset": False,
        "prior_recovery_evidence_preserved": True,
        "attempted_count": len(cases),
        "pass_count": counts["pass"],
        "conditional_count": counts["conditional"],
        "withheld_count": counts["withheld"],
        "numeric_count": counts["pass"] + counts["conditional"],
        "newly_numeric_tickers": [row["ticker"] for row in cases if row["initial_outcome"] == "withheld" and row["outcome"] != "withheld"],
        "upgraded_to_pass_tickers": [row["ticker"] for row in cases if row["initial_outcome"] != "pass" and row["outcome"] == "pass"],
        "pass_tickers": [row["ticker"] for row in cases if row["outcome"] == "pass"],
        "conditional_tickers": [row["ticker"] for row in cases if row["outcome"] == "conditional"],
        "withheld_tickers": [row["ticker"] for row in cases if row["outcome"] == "withheld"],
        "reliability_counts": {name: reliability.get(name, 0) for name in ("High", "Medium", "Low")},
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "watchlist_changed_during_staging": False,
        "watchlist_sha256": watch_before,
        "withheld_register_changed_during_staging": False,
        "withheld_register_sha256": withheld_before,
        "cases": cases,
    }
    _immutable(output_root / "batch-16-whole-repair-report.json", _json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-root", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--event-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({key: report[key] for key in ("attempted_count", "pass_count", "conditional_count", "withheld_count", "numeric_count", "newly_numeric_tickers", "upgraded_to_pass_tickers", "reliability_counts", "serving_artifacts_changed", "watchlist_changed_during_staging", "withheld_register_changed_during_staging")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
