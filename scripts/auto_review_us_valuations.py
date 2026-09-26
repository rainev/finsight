#!/usr/bin/env python3
"""Refresh, repair, and review every generated U.S. valuation artifact."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.us_valuation.artifacts import (  # noqa: E402
    public_result,
    sanitize_public_artifact,
    write_json,
)
from app.us_valuation.automated_review import (  # noqa: E402
    assess_artifact,
    discover_issuers,
    run_repair_loop,
)
from build_us_valuation_pipeline import build_issuer_artifacts  # noqa: E402


DATA_ROOT = ROOT / "backend" / "app" / "data" / "us_valuations"
DEFAULT_REPORT = ROOT / "output" / "autonomous-review" / "us-valuation-review.json"


def _load_candidate(paths: dict[str, Path]) -> dict[str, Any]:
    private = json.loads(paths["private"].read_text(encoding="utf-8"))
    submissions = json.loads(paths["submissions_fixture"].read_text(encoding="utf-8"))
    return public_result(private, submissions, sanitize=False)


def review_issuer(
    issuer: dict[str, str],
    *,
    refresh: bool,
    max_attempts: int,
) -> dict[str, Any]:
    ticker = issuer["ticker"]
    output_root = ROOT / "archive" / "local-audit" / "us" / ticker.lower()
    paths: dict[str, Path] | None = None

    def rebuild(current: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
        nonlocal paths
        if not assessment.get("repair_actions"):
            return current
        paths = build_issuer_artifacts(
            issuer["cik"],
            ticker,
            issuer["short_name"],
            issuer["subsector"],
            output_root,
            valuation_date=current.get("valuation_date", "2026-08-01"),
            refresh=bool(os.environ.get("SEC_USER_AGENT")),
        )
        return _load_candidate(paths)

    try:
        paths = build_issuer_artifacts(
            issuer["cik"],
            ticker,
            issuer["short_name"],
            issuer["subsector"],
            output_root,
            valuation_date="2026-08-01",
            refresh=refresh,
        )
        initial = _load_candidate(paths)
        result = run_repair_loop(initial, repair=rebuild, max_attempts=max_attempts)
        final_artifact = result["artifact"]
        final_assessment = result["assessment"]
        final_artifact["automated_review"] = {
            **final_assessment,
            "repair_attempts": result["repair_attempts"],
        }
        final_artifact = sanitize_public_artifact(final_artifact)
        if paths is not None:
            write_json(paths["backend_public"], final_artifact)
            write_json(paths["frontend_audit"], final_artifact)
        return {
            "ticker": ticker,
            "decision": final_assessment["decision"],
            "publication_state": final_assessment["publication_state"],
            "blocking_reasons": final_assessment["blocking_reasons"],
            "repair_actions": final_assessment["repair_actions"],
            "repair_attempts": result["repair_attempts"],
        }
    except Exception as exc:  # keep the batch moving and explain technical failures
        return {
            "ticker": ticker,
            "decision": "failed",
            "publication_state": "error",
            "blocking_reasons": [f"technical_error:{type(exc).__name__}:{exc}"],
            "repair_actions": [],
            "repair_attempts": [],
        }


def run_batch(
    *,
    tickers: set[str] | None = None,
    refresh: bool = False,
    max_attempts: int = 3,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    issuers = discover_issuers(DATA_ROOT)
    if tickers:
        issuers = [issuer for issuer in issuers if issuer["ticker"] in tickers]
    results = [review_issuer(issuer, refresh=refresh, max_attempts=max_attempts) for issuer in issuers]
    counts: dict[str, int] = {}
    for result in results:
        counts[result["decision"]] = counts.get(result["decision"], 0) + 1
    report = {
        "review_version": "US-AUTO-REVIEW-1.0",
        "count": len(results),
        "counts": counts,
        "results": results,
    }
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", help="Comma-separated tickers; default is every generated artifact")
    parser.add_argument("--refresh", action="store_true", help="Refresh SEC inputs instead of replaying local fixtures/cache")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if args.max_attempts < 1:
        parser.error("--max-attempts must be at least 1")
    tickers = {ticker.strip().upper() for ticker in args.tickers.split(",")} if args.tickers else None
    report = run_batch(
        tickers=tickers,
        refresh=args.refresh,
        max_attempts=args.max_attempts,
        report_path=args.report,
    )
    print(json.dumps({"count": report["count"], "counts": report["counts"], "report": str(args.report)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
