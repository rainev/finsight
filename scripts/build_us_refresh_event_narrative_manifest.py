#!/usr/bin/env python3
"""Convert a legacy event receipt into a clean hashed narrative source manifest.

The resulting manifest carries only filing identity and document bytes.  It
deliberately omits remembered or previously derived financial terms; the
versioned narrative extractor must recover every value from the document.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.catalog import canonical_json_bytes
from app.us_valuation.refresh_job import atomic


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source_path = args.source_receipt.resolve()
    source = json.loads(source_path.read_bytes())
    required = ("ticker", "cik", "accession", "form", "filed", "report_date", "primary_document", "document_sha256")
    if any(not isinstance(source.get(key), str) or not source[key] for key in required):
        raise ValueError("legacy event receipt filing identity is incomplete")
    document = (source_path.parent / source["primary_document"]).resolve()
    if document.parent != source_path.parent or not document.is_file():
        raise ValueError("legacy event document path is unavailable or unsafe")
    raw = document.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != source["document_sha256"]:
        raise ValueError("legacy event document hash mismatch")
    manifest = {
        "manifest_version": "FINSIGHT-NARRATIVE-SOURCE-MANIFEST-1",
        "ticker": source["ticker"], "cik": str(source["cik"]).zfill(10),
        "accession": source["accession"], "form": source["form"],
        "filed_date": source["filed"], "report_date": source["report_date"],
        "entrypoint_local_path": document.name,
        "files": [{"local_path": document.name, "sha256": digest, "byte_count": len(raw)}],
        "method": "identity_and_sha256_only; financial terms intentionally omitted",
    }
    output = (args.output or source_path.parent / "narrative-source-manifest.json").resolve()
    if output.parent != source_path.parent:
        raise ValueError("event narrative manifest must stay beside its source document")
    atomic(output, canonical_json_bytes(manifest))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
