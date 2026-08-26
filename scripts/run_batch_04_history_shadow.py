#!/usr/bin/env python3
"""Stage the Batch 04 company-history shadow without serving or watchlist writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_04 import (
    BATCH_04_MANIFEST,
    BATCH_04_TICKERS,
    BATCH_04_VALUATION_DATE,
)
from app.us_valuation.batch_04_launch_first import (
    BATCH_04_HISTORY_SHADOW_VERSION,
    PASS_TICKERS,
    build_batch_04_launch_first_result,
)
from run_batch_04_launch_first import PROTECTED, WATCHLIST, _immutable, _json, _public, _tree
from run_batch_04_reclassification import _pass_public


HISTORY_PUBLIC_FIELDS = (
    "history_policy_version",
    "history_years_used",
    "normalization_basis",
    "assumption_source_mix",
)


def _history_public(issuer, result):
    is_pass = issuer.ticker in PASS_TICKERS
    public = _pass_public(issuer, result) if is_pass else _public(issuer, result)
    assumptions = result["governed_assumptions"]
    for field in HISTORY_PUBLIC_FIELDS:
        if field in assumptions:
            public["public_assumptions"][field] = assumptions[field]
    reliability = result["history_reliability"]
    if reliability is None:
        raise RuntimeError(f"{issuer.ticker}: missing history reliability")
    public["reliability"] = reliability
    public["confidence"] = {
        "label": reliability["label"],
        "reasons": reliability["reasons"],
    }
    public["forecast_quality"]["policy_version"] = BATCH_04_HISTORY_SHADOW_VERSION
    public["methodology"]["forecast_policy"] = BATCH_04_HISTORY_SHADOW_VERSION
    value = sanitize_public_artifact(public)
    expected = "available" if is_pass else "conditional_estimate"
    if value["availability_type"] != expected:
        raise RuntimeError(f"{issuer.ticker}: history availability mismatch")
    if value["scenario_range"]["base"] != result["scenario_range"]["base"]:
        raise RuntimeError(f"{issuer.ticker}: history public/private base mismatch")
    return value


def run(*, source_root: Path, structural_root: Path, output_root: Path) -> dict:
    source_root = Path(source_root)
    structural_root = Path(structural_root)
    output_root = Path(output_root)
    before = {str(root): _tree(root) for root in PROTECTED}
    watch_before = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    cases = []
    reliability_counts = {"High": 0, "Medium": 0, "Low": 0}

    for issuer in BATCH_04_MANIFEST:
        prior = build_batch_04_launch_first_result(
            ticker=issuer.ticker,
            source_root=source_root,
            structural_root=structural_root,
        )
        result = build_batch_04_launch_first_result(
            ticker=issuer.ticker,
            source_root=source_root,
            structural_root=structural_root,
            history_backed=True,
        )
        public = _history_public(issuer, result)
        availability = result["baseline"]["availability_type"]
        outcome = "source_bounded_numeric" if availability == "available" else "conditional_numeric"
        reliability = result["history_reliability"]["label"]
        reliability_counts[reliability] += 1
        prior_base = prior["scenario_range"]["base"]
        base = result["scenario_range"]["base"]
        case = {
            "ticker": issuer.ticker,
            "outcome": outcome,
            "availability_type": availability,
            "reliability": reliability,
            "method": result["method"],
            "prior_base": prior_base,
            "low": result["scenario_range"]["low"],
            "base": base,
            "high": result["scenario_range"]["high"],
            "base_change_pct": (base - prior_base) / prior_base,
            "history_years_used": result["governed_assumptions"].get("history_years_used"),
            "normalization_basis": result["governed_assumptions"].get("normalization_basis"),
            "assumption_source_mix": result["governed_assumptions"].get("assumption_source_mix"),
            "reliability_reasons": result["history_reliability"]["reasons"],
        }
        private = {
            "schema_version": "FINSIGHT-BATCH-04-HISTORY-SHADOW-1",
            "batch": 4,
            "valuation_date": BATCH_04_VALUATION_DATE,
            "issuer": {
                "ticker": issuer.ticker,
                "cik": issuer.cik,
                "issuer_name": issuer.issuer_name,
            },
            "prior_baseline": prior["scenario_range"],
            "history_backed": result,
            "shadow_outcome": case,
        }
        _immutable(
            output_root / "generated" / issuer.ticker / "valuation-private.json",
            _json(private),
        )
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)

    after = {str(root): _tree(root) for root in PROTECTED}
    watch_after = hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    if before != after or watch_before != watch_after:
        raise RuntimeError("Batch 04 history shadow changed protected state")
    report = {
        "schema_version": "FINSIGHT-BATCH-04-HISTORY-SHADOW-REPORT-1",
        "batch": 4,
        "valuation_date": BATCH_04_VALUATION_DATE,
        "policy_version": BATCH_04_HISTORY_SHADOW_VERSION,
        "denominator_tickers": list(BATCH_04_TICKERS),
        "attempted_count": len(cases),
        "pass_count": sum(case["availability_type"] == "available" for case in cases),
        "conditional_count": sum(case["availability_type"] == "conditional_estimate" for case in cases),
        "withheld_count": sum(case["availability_type"] == "not_available" for case in cases),
        "numeric_count": sum(case["base"] > 0 for case in cases),
        "reliability_counts": reliability_counts,
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "watchlist_changed": False,
        "watchlist_sha256": watch_before,
        "cases": cases,
    }
    _immutable(output_root / "history-shadow-report.json", _json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    report = run(**vars(parser.parse_args()))
    print(json.dumps({
        key: report[key]
        for key in (
            "attempted_count",
            "pass_count",
            "conditional_count",
            "withheld_count",
            "numeric_count",
            "reliability_counts",
            "serving_artifacts_changed",
            "watchlist_changed",
        )
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
