#!/usr/bin/env python3
"""Extract auditable bridge evidence from one cached SEC filing document."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.filing_evidence import extract_filing_evidence  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--cik", required=True)
    parser.add_argument("--form", default="10-Q")
    parser.add_argument("--period-end", required=True)
    parser.add_argument("--filing-date", required=True)
    parser.add_argument("--accession", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    metadata = {
        "ticker": args.ticker,
        "cik": args.cik,
        "form": args.form,
        "period_end": args.period_end,
        "filing_date": args.filing_date,
        "source_accession": args.accession,
        "source_url": args.source_url,
    }
    records = extract_filing_evidence(
        args.html.read_text(encoding="utf-8", errors="ignore"),
        metadata=metadata,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ticker": args.ticker.upper(), "records": len(records), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
