#!/usr/bin/env python3
"""Capture the cutoff-eligible Southwest revolving-credit event for Batch 20."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.sec_client import SecClient, sec_archive_url
from capture_batch_02_sources import PROTECTED_ROOTS, _assert_non_serving, _tree_hash
from capture_batch_02_structural_sources import _immutable_json


SOURCE = {
    "ticker": "LUV",
    "cik": "0000092380",
    "accession": "0000092380-26-000098",
    "form": "8-K",
    "filed": "2026-08-12",
    "report_date": "2026-08-10",
    "primary_document": "luv-20260810.htm",
    "required_tokens": ("$2 billion", "five-year revolving credit facility", "no amounts outstanding"),
    "reported_terms": {
        "committed_revolving_capacity_usd": 2_000_000_000.0,
        "accordion_maximum_capacity_usd": 3_000_000_000.0,
        "amount_outstanding_usd": 0.0,
        "maturity": "2031-08-10",
    },
    "treatment": "Record the facility as liquidity capacity and add no debt or cash because the filing reports zero outstanding at the cutoff.",
}


def run(*, output_root: Path, user_agent: str | None = None, refresh: bool = False):
    output_root = Path(output_root)
    roots = tuple(Path(root) for root in PROTECTED_ROOTS)
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    client = SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    raw = client.filing_attachment(SOURCE["cik"], SOURCE["accession"], SOURCE["primary_document"], refresh=refresh, max_bytes=8 * 1024 * 1024)
    text = raw.decode("utf-8", errors="replace")
    for token in SOURCE["required_tokens"]:
        if token not in text:
            raise RuntimeError(f"LUV event term changed: {token}")
    digest = hashlib.sha256(raw).hexdigest()
    target = output_root / "LUV"
    target.mkdir(parents=True, exist_ok=True)
    document = target / SOURCE["primary_document"]
    if document.exists() and document.read_bytes() != raw:
        raise FileExistsError(f"immutable event document differs: {document}")
    if not document.exists():
        document.write_bytes(raw)
    receipt = {"schema_version": "FINSIGHT-BATCH-20-EVENT-SOURCE-1", "valuation_date": "2026-08-14", **{key: value for key, value in SOURCE.items() if key != "required_tokens"}, "url": sec_archive_url(SOURCE["cik"], SOURCE["accession"], SOURCE["primary_document"]), "document_sha256": digest, "document_bytes": len(raw)}
    _immutable_json(target / "source-receipt.json", receipt)
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after:
        raise RuntimeError("serving changed")
    summary = {"attempted": 1, "captured": 1, "failed": 0, "cases": [{"ticker": "LUV", "accession": SOURCE["accession"], "filed": SOURCE["filed"], "form": SOURCE["form"], "document_sha256": digest}], "serving_hash_before": before, "serving_hash_after": after, "serving_artifacts_changed": False}
    _immutable_json(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    print(json.dumps(run(**vars(parser.parse_args())), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
