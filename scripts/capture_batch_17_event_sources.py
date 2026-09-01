#!/usr/bin/env python3
"""Capture the cutoff-eligible AbbVie Apogee financing event for Batch 17."""
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

SOURCE = {"ticker": "ABBV", "cik": "0001551152", "accession": "0001104659-26-091269", "form": "8-K", "filed": "2026-08-05", "report_date": "2026-08-04", "primary_document": "tm2621452d4_8k.htm", "role": "signed_post_balance_sheet_pre_close_financing"}


def run(*, output_root: Path, user_agent: str | None = None, refresh: bool = False):
    output_root = Path(output_root)
    roots = tuple(Path(root) for root in PROTECTED_ROOTS)
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    client = SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    raw = client.filing_attachment(SOURCE["cik"], SOURCE["accession"], SOURCE["primary_document"], refresh=refresh, max_bytes=8 * 1024 * 1024)
    text = raw.decode("utf-8", errors="replace")
    for token in ("$500,000,000", "$1,500,000,000", "$9.93", "Apogee", "August", "18, 2026"):
        if token not in text:
            raise RuntimeError(f"AbbVie financing-event term changed: {token}")
    digest = hashlib.sha256(raw).hexdigest()
    target = output_root / "ABBV"
    target.mkdir(parents=True, exist_ok=True)
    document = target / SOURCE["primary_document"]
    if document.exists() and document.read_bytes() != raw:
        raise FileExistsError(f"immutable event document differs: {document}")
    if not document.exists():
        document.write_bytes(raw)
    receipt = {"schema_version": "FINSIGHT-BATCH-17-EVENT-SOURCE-1", "valuation_date": "2026-08-14", **SOURCE, "url": sec_archive_url(SOURCE["cik"], SOURCE["accession"], SOURCE["primary_document"]), "document_sha256": digest, "document_bytes": len(raw), "reported_terms": {"aggregate_principal_usd": 10_000_000_000.0, "expected_net_proceeds_usd": 9_930_000_000.0, "expected_close_date": "2026-08-18", "purpose": "fund part of Apogee acquisition and general corporate purposes including possible debt repayment", "delayed_draw_commitment_reduction_usd": 10_000_000_000.0, "cutoff_status": "signed_not_closed_not_issued"}, "treatment": "Do not add principal or proceeds at the 2026-08-14 cutoff; publish current standalone value and invalidate on closing or changed terms."}
    _immutable_json(target / "source-receipt.json", receipt)
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after:
        raise RuntimeError("serving changed")
    summary = {"attempted": 1, "captured": 1, "failed": 0, "cases": [{"ticker": "ABBV", "accession": SOURCE["accession"], "filed": SOURCE["filed"], "form": SOURCE["form"], "document_sha256": digest}], "serving_hash_before": before, "serving_hash_after": after, "serving_artifacts_changed": False}
    _immutable_json(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    print(json.dumps(run(**vars(parser.parse_args())), sort_keys=True))
    return 0

if __name__ == "__main__": raise SystemExit(main())
