#!/usr/bin/env python3
"""Stage one whole-batch Batch 12 recovery attempt without serving/bookkeeping writes."""
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
from app.us_valuation.batch_12 import (
    BATCH_12_MANIFEST,
    BATCH_12_TICKERS,
    BATCH_12_VALUATION_DATE,
)
from app.us_valuation.batch_12_recovery import (
    BATCH_12_RECOVERY_VERSION,
    EQUITY_TICKERS,
    build_batch_12_recovery_result,
)
from run_batch_07_history import PROTECTED, WATCHLIST, _immutable, _json, _tree
from run_batch_12_history import WITHHELD_REGISTER, _public as _initial_public


APPROVED_INITIAL_REPORT_SHA256 = "cf1cd837c534b375bb8ca531b300097efdec07a14c01ac05d6c103fccb0f64c9"
APPROVED_INITIAL_TREE_SHA256 = "6fc362a70a07dc00364a4096e7a084478f07585ba7ceb3f6a517c3c0b688a159"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _validate_roots(
    initial_root: Path,
    source_root: Path,
    structural_root: Path,
    output_root: Path,
) -> None:
    protected = tuple(Path(root) for root in PROTECTED)
    for root in (initial_root, source_root, structural_root):
        if not root.is_dir():
            raise ValueError(f"required recovery root is missing: {root}")
    if any(_inside(output_root, root) or _inside(root, output_root) for root in (*protected, initial_root, source_root, structural_root)):
        raise ValueError("recovery output overlaps immutable input or protected serving state")


def _validate_initial(initial_root: Path) -> dict:
    report_path = initial_root / "batch-12-report.json"
    report = json.loads(report_path.read_text())
    if (
        report.get("schema_version") != "FINSIGHT-BATCH-12-HISTORY-REPORT-1"
        or tuple(report.get("denominator_tickers", ())) != BATCH_12_TICKERS
        or (report.get("pass_count"), report.get("conditional_count"), report.get("withheld_count")) != (0, 9, 1)
    ):
        raise ValueError("initial Batch 12 evidence is not the approved comparison surface")
    if _sha(report_path) != APPROVED_INITIAL_REPORT_SHA256 or _tree(initial_root) != APPROVED_INITIAL_TREE_SHA256:
        raise ValueError("initial Batch 12 evidence hash differs from approved candidate-i")
    report_cases = {row["ticker"]: row for row in report["cases"]}
    for issuer in BATCH_12_MANIFEST:
        private_path = initial_root / "generated" / issuer.ticker / "valuation-private.json"
        public_path = initial_root / "staged-public" / f"{issuer.ticker}.json"
        if not private_path.is_file():
            raise ValueError(f"{issuer.ticker}: initial private evidence is missing")
        if not public_path.is_file():
            raise ValueError(f"{issuer.ticker}: initial public evidence is missing")
        private = json.loads(private_path.read_text())
        public = json.loads(public_path.read_text())
        case = report_cases.get(issuer.ticker)
        if private.get("controlled_outcome") != case:
            raise ValueError(f"{issuer.ticker}: initial private/report outcome mismatch")
        if (
            public.get("availability_type") != case["availability_type"]
            or public.get("scenario_range", {}).get("low") != case["low"]
            or public.get("scenario_range", {}).get("base") != case["base"]
            or public.get("scenario_range", {}).get("high") != case["high"]
        ):
            raise ValueError(f"{issuer.ticker}: initial public/report outcome mismatch")
    return report


def _public(issuer, result: dict) -> dict:
    value = _initial_public(issuer, result)
    assumptions = result["governed_assumptions"]
    public = value["public_assumptions"]
    public["forecast_policy_version"] = BATCH_12_RECOVERY_VERSION
    public["recovery_attempt"] = 1
    if result["availability_type"] == "not_available":
        public["forecast_mode"] = "unavailable_post_period_multi_event_state"
        value["forecast_quality"]["policy_version"] = BATCH_12_RECOVERY_VERSION
        value["methodology"]["forecast_policy"] = BATCH_12_RECOVERY_VERSION
        value["model_policy"]["reason"] = result["warning"]
        value = sanitize_public_artifact(value)
        if value["availability_type"] != "not_available" or value["scenario_range"]["base"] is not None:
            raise RuntimeError(f"{issuer.ticker}: withheld recovery public mismatch")
        return value
    if issuer.ticker in EQUITY_TICKERS:
        public["forecast_mode"] = "normalized_equity_earnings"
        public["valuation_basis"] = "residual_income_recovery"
        public["earnings_multiple"] = assumptions["earnings_multiples"][1]
        public["normalized_earnings_factor"] = 1.0
    else:
        public["forecast_mode"] = "faded_cash_fcff_recovery"
        public["forecast_years"] = assumptions["forecast_years"]
        public["initial_revenue_growth"] = assumptions["growth"][1]
        public["policy_wacc"] = assumptions["wacc"][1]
        public["terminal_growth"] = assumptions["terminal_growth"][1]
    value["forecast_quality"]["policy_version"] = BATCH_12_RECOVERY_VERSION
    value["methodology"]["forecast_policy"] = BATCH_12_RECOVERY_VERSION
    value["model_policy"]["reason"] = result["warning"]
    value = sanitize_public_artifact(value)
    if (
        value["availability_type"] != "conditional_estimate"
        or value["scenario_range"]["base"] != result["scenario_range"]["base"]
    ):
        raise RuntimeError(f"{issuer.ticker}: recovery public mismatch")
    return value


def run(
    *,
    initial_root: Path,
    source_root: Path,
    structural_root: Path,
    output_root: Path,
) -> dict:
    initial_root, source_root, structural_root, output_root = map(
        Path, (initial_root, source_root, structural_root, output_root)
    )
    _validate_roots(initial_root, source_root, structural_root, output_root)
    initial = _validate_initial(initial_root)
    initial_tree_sha256 = _tree(initial_root)
    before = {str(root): _tree(root) for root in PROTECTED}
    watch_before = _sha(WATCHLIST)
    withheld_before = _sha(WITHHELD_REGISTER)
    initial_by_ticker = {row["ticker"]: row for row in initial["cases"]}
    cases = []
    attempt_receipts = {}
    for issuer in BATCH_12_MANIFEST:
        result = build_batch_12_recovery_result(
            ticker=issuer.ticker,
            source_root=source_root,
            structural_root=structural_root,
        )
        public = _public(issuer, result)
        initial_case = initial_by_ticker[issuer.ticker]
        availability = result["availability_type"]
        outcome = "conditional" if availability == "conditional_estimate" else "withheld"
        reliability = None if result["history_reliability"] is None else result["history_reliability"]["label"]
        case = {
            "ticker": issuer.ticker,
            "attempt_number": 1,
            "initial_outcome": initial_case["outcome"],
            "initial_availability_type": initial_case["availability_type"],
            "initial_low": initial_case["low"],
            "initial_base": initial_case["base"],
            "initial_high": initial_case["high"],
            "outcome": outcome,
            "availability_type": availability,
            "reliability": reliability,
            "method": result["method"],
            **result["scenario_range"],
            "history_years_used": result["governed_assumptions"]["history_years_used"],
            "warning": result["warning"],
        }
        private = {
            "schema_version": "FINSIGHT-BATCH-12-RECOVERY-1",
            "batch": 12,
            "valuation_date": BATCH_12_VALUATION_DATE,
            "issuer": {
                "ticker": issuer.ticker,
                "cik": issuer.cik,
                "issuer_name": issuer.issuer_name,
            },
            "recovery": result,
            "controlled_outcome": case,
        }
        _immutable(
            output_root / "generated" / issuer.ticker / "valuation-private.json",
            _json(private),
        )
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", _json(public))
        cases.append(case)
        attempt_receipts[issuer.ticker] = dict(result["source_ledger"]["recovery_attempt"])
    after = {str(root): _tree(root) for root in PROTECTED}
    watch_after = _sha(WATCHLIST)
    withheld_after = _sha(WITHHELD_REGISTER)
    if before != after or watch_before != watch_after or withheld_before != withheld_after:
        raise RuntimeError("Batch 12 recovery staging changed protected or bookkeeping state")
    unsupported = [row for row in cases if row["outcome"] not in {"pass", "conditional", "withheld"}]
    if unsupported:
        raise RuntimeError("Batch 12 recovery produced an unsupported outcome")
    pass_rows = [row for row in cases if row["outcome"] == "pass"]
    conditional_rows = [row for row in cases if row["outcome"] == "conditional"]
    withheld_rows = [row for row in cases if row["outcome"] == "withheld"]
    numeric_rows = [row for row in cases if row["outcome"] != "withheld"]
    newly_numeric_rows = [
        row
        for row in cases
        if row["initial_availability_type"] == "not_available"
        and row["availability_type"] != "not_available"
    ]
    reliability_counts = Counter(row["reliability"] for row in cases if row["reliability"] is not None)
    report = {
        "schema_version": "FINSIGHT-BATCH-12-RECOVERY-REPORT-1",
        "batch": 12,
        "valuation_date": BATCH_12_VALUATION_DATE,
        "policy_version": BATCH_12_RECOVERY_VERSION,
        "denominator_tickers": list(BATCH_12_TICKERS),
        "initial_report_sha256": _sha(initial_root / "batch-12-report.json"),
        "initial_tree_sha256": initial_tree_sha256,
        "recovery_attempted_count": 10,
        "recovery_attempted_tickers": list(BATCH_12_TICKERS),
        "recovery_attempts_per_ticker": {ticker: 1 for ticker in BATCH_12_TICKERS},
        "recovery_attempt_receipts": attempt_receipts,
        "newly_numeric_count": len(newly_numeric_rows),
        "newly_numeric_tickers": [row["ticker"] for row in newly_numeric_rows],
        "final_pass_count": len(pass_rows),
        "final_conditional_count": len(conditional_rows),
        "final_withheld_count": len(withheld_rows),
        "final_numeric_count": len(numeric_rows),
        "final_pass_tickers": [row["ticker"] for row in pass_rows],
        "final_conditional_tickers": [row["ticker"] for row in conditional_rows],
        "final_withheld_tickers": [row["ticker"] for row in withheld_rows],
        "reliability_counts": {name: reliability_counts.get(name, 0) for name in ("High", "Medium", "Low")},
        "serving_artifacts_changed": False,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "watchlist_changed_during_staging": False,
        "watchlist_sha256": watch_before,
        "withheld_register_changed_during_staging": False,
        "withheld_register_sha256": withheld_before,
        "cases": cases,
    }
    _immutable(output_root / "batch-12-recovery-report.json", _json(report))
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
                    "recovery_attempted_count",
                    "newly_numeric_count",
                    "final_pass_count",
                    "final_conditional_count",
                    "final_withheld_count",
                    "final_numeric_count",
                    "serving_artifacts_changed",
                    "watchlist_changed_during_staging",
                    "withheld_register_changed_during_staging",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
