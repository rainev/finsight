#!/usr/bin/env python3
"""Build the immutable cached-filing source index used by refresh verification.

This command performs the one explicit recursive scan.  Subsequent consumers
load ``source-index.json`` and use indexed lookup; they do not rediscover
candidate packet directories or structural files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.refresh_source_index import build_source_index, persist_source_index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "output",
        help="Allowed root containing cached packet and structural candidates (default: output).",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        help="Immutable index destination (default: OUTPUT_ROOT/source-index.json).",
    )
    parser.add_argument(
        "--created-at-epoch",
        type=float,
        help="Optional fixed creation timestamp for reproducible fixtures/tests.",
    )
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    index_path = args.index_path.resolve() if args.index_path else None
    payload = build_source_index(
        output_root,
        index_path,
        created_at_epoch=args.created_at_epoch,
    )
    if index_path is None:
        index_path = output_root / 'us-refresh-runtime' / 'source-indexes' / f"{payload['input_fingerprint_sha256']}.json"
        persist_source_index(payload,index_path,output_root=output_root)
    summary = {
        "index_path": str(index_path),
        "schema_version": payload["schema_version"],
        "index_sha256": payload["index_sha256"],
        "input_fingerprint_sha256": payload["input_fingerprint_sha256"],
        "measurement": payload["measurement"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
