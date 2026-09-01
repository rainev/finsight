#!/usr/bin/env python3
"""Capture the cutoff-eligible Agilent debt event required by Batch 16."""
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

SOURCE = {"ticker": "A", "cik": "0001090872", "accession": "0001193125-26-282845", "form": "8-K", "filed": "2026-06-25", "report_date": "2026-06-25", "primary_document": "d75293d8k.htm", "role": "post_balance_sheet_debt_issuance"}


def run(*, output_root: Path, user_agent: str | None = None, refresh: bool = False):
    output_root = Path(output_root)
    roots = tuple(Path(root) for root in PROTECTED_ROOTS)
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    client = SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    raw = client.filing_attachment(SOURCE["cik"], SOURCE["accession"], SOURCE["primary_document"], refresh=refresh, max_bytes=8 * 1024 * 1024)
    text = raw.decode("utf-8", errors="replace")
    if "$600" not in text or "4.900%" not in text or "January" not in text or "2032" not in text:
        raise RuntimeError("Agilent debt-event terms changed")
    digest = hashlib.sha256(raw).hexdigest()
    target = output_root / "A"
    target.mkdir(parents=True, exist_ok=True)
    document = target / SOURCE["primary_document"]
    if document.exists() and document.read_bytes() != raw:
        raise FileExistsError(f"immutable event document differs: {document}")
    if not document.exists():
        document.write_bytes(raw)
    receipt = {"schema_version": "FINSIGHT-BATCH-16-EVENT-SOURCE-1", "valuation_date": "2026-08-14", **SOURCE, "url": sec_archive_url(SOURCE["cik"], SOURCE["accession"], SOURCE["primary_document"]), "document_sha256": digest, "document_bytes": len(raw), "reported_terms": {"principal_usd": 600_000_000, "issue_price_ratio": .99968, "gross_cash_proceeds_before_fees_usd": 599_808_000., "coupon_rate": .049, "maturity": "2032-01-15", "status": "issued_and_outstanding"}}
    _immutable_json(target / "source-receipt.json", receipt)
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after:
        raise RuntimeError("serving changed")
    summary = {"attempted": 1, "captured": 1, "failed": 0, "cases": [{"ticker": "A", "accession": SOURCE["accession"], "filed": SOURCE["filed"], "form": SOURCE["form"], "document_sha256": digest}], "serving_hash_before": before, "serving_hash_after": after, "serving_artifacts_changed": False}
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
