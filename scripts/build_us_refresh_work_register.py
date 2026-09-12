#!/usr/bin/env python3
"""Build the FinSight 440-company work register and plain-language report.

This command is offline and reporting-only.  It reads existing runtime receipts
and writes the requested report files; it never acquires filings or activates a
catalog.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.refresh_work_register import (  # noqa: E402
    DEFAULT_EXPECTED_COUNT,
    build_work_register,
    canonical_json_bytes,
    render_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=ROOT / "output" / "us-refresh-runtime",
        help="Frozen refresh runtime root (default: output/us-refresh-runtime)",
    )
    parser.add_argument(
        "--source-report",
        action="append",
        type=Path,
        dest="source_reports",
        help="Optional source receipt; repeat to restrict/lock report selection.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=ROOT / "output" / "us-refresh-work-register.json",
    )
    parser.add_argument(
        "--output-markdown",
        type=Path,
        default=ROOT / "output" / "us-refresh-work-register.md",
    )
    parser.add_argument("--expected-count", type=int, default=DEFAULT_EXPECTED_COUNT)
    args = parser.parse_args()

    register = build_work_register(
        args.runtime_root,
        source_reports=args.source_reports,
        expected_count=args.expected_count,
    )
    json_bytes = canonical_json_bytes(register)
    markdown = render_markdown(register).encode("utf-8")
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_bytes(json_bytes)
    args.output_markdown.write_bytes(markdown)
    print(
        json.dumps(
            {
                "json": str(args.output_json),
                "markdown": str(args.output_markdown),
                "companies": register["scope"]["registry_count"],
                "recipes": register["scope"]["recipe_count"],
                "source_reports": len(register["source_reports"]["considered"]),
                "source_reports_composable": register["source_reports"]["composable"],
                "counts": register["counts"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
