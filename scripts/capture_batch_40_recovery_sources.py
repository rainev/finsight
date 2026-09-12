#!/usr/bin/env python3
"""Capture the missing COIN Q2 earnings exhibit for the Batch 40 recovery."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.sec_client import SecClient, sec_archive_url
from capture_batch_37_event_sources import _immutable, _json


CIK = "0001679788"
ACCESSION = "0001679788-26-000087"
PRIMARY_DOCUMENT = "coin-20260730.htm"
EXHIBIT = "q226earningsdeck_sec.htm"


def run(*, output_root: Path) -> dict:
    initial_primary = (
        ROOT
        / "output/batch-40-event-review-20260907/COIN"
        / ACCESSION
        / PRIMARY_DOCUMENT
    )
    if not initial_primary.exists() or f'href="{EXHIBIT}"' not in initial_primary.read_text(errors="ignore"):
        raise ValueError("COIN earnings exhibit is not linked from the captured 8-K")

    output_root = Path(output_root).resolve()
    client = SecClient(
        user_agent=os.environ.get("SEC_USER_AGENT"),
        cache_dir=output_root / ".cache",
    )
    raw = client.filing_attachment(CIK, ACCESSION, EXHIBIT, max_bytes=20 * 1024 * 1024)
    exhibit_path = output_root / "COIN" / ACCESSION / EXHIBIT
    _immutable(exhibit_path, raw)
    receipt = {
        "schema_version": "FINSIGHT-BATCH-40-COIN-RECOVERY-SOURCE-1",
        "ticker": "COIN",
        "cik": CIK,
        "accession": ACCESSION,
        "filed": "2026-07-30",
        "form": "8-K",
        "linked_from_primary_document": PRIMARY_DOCUMENT,
        "document": {
            "filename": EXHIBIT,
            "path": str(exhibit_path.relative_to(ROOT)),
            "source_url": sec_archive_url(CIK, ACCESSION, EXHIBIT),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        },
        "reported_vs_estimated": "reported",
    }
    _immutable(output_root / "COIN" / "recovery-source-receipt.json", _json(receipt))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    receipt = run(**vars(parser.parse_args()))
    print(json.dumps(receipt["document"], sort_keys=True))


if __name__ == "__main__":
    main()
