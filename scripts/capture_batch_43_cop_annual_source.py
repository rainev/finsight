#!/usr/bin/env python3
"""Capture COP's FY2025 filing to recover recent capex-and-investment history."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.sec_client import SecClient
from capture_batch_02_structural_sources import _dependencies, _immutable_json


CIK = "0001163165"
ACCESSION = "0001163165-26-000009"
PRIMARY = "cop-20251231.htm"


def run(*, output_root: Path, cache_root: Path, user_agent: str | None = None) -> dict:
    output_root, cache_root = Path(output_root), Path(cache_root)
    sec, package_capture, parse = _dependencies()
    client = sec(user_agent=user_agent, cache_dir=cache_root / ".sec-cache")
    entry = package_capture(client, cik=CIK, accession=ACCESSION, primary_document=PRIMARY, form="10-K", output_dir=cache_root / "filings/COP", refresh=False, filed_date="2026-02-17", report_date="2025-12-31")
    parsed = parse(entry, accession=ACCESSION, form="10-K", timeout_seconds=300)
    structural = parsed.as_dict() if hasattr(parsed, "as_dict") else parsed
    package = json.loads((entry.parent / "package-manifest.json").read_text())
    receipt = {"schema_version": "FINSIGHT-BATCH-43-COP-ANNUAL-SOURCE-1", "valuation_date": "2026-08-14", "ticker": "COP", "cik": CIK, "filing": {"accession": ACCESSION, "filed": "2026-02-17", "form": "10-K", "report_date": "2025-12-31", "primary_document": PRIMARY}, "package_manifest_sha256": hashlib.sha256((json.dumps(package, indent=2, sort_keys=True) + "\n").encode()).hexdigest(), "structural_filing_sha256": hashlib.sha256((json.dumps(structural, indent=2, sort_keys=True) + "\n").encode()).hexdigest()}
    target = output_root / "COP"
    _immutable_json(target / "package-manifest.json", package)
    _immutable_json(target / "structural-filing.json", structural)
    _immutable_json(target / "source-receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    print(json.dumps(run(**vars(parser.parse_args())), sort_keys=True))


if __name__ == "__main__":
    main()
