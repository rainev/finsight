#!/usr/bin/env python3
"""Build immutable private narrative receipts from cached filing packages."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes
from app.us_valuation.refresh_job import atomic
from app.us_valuation.refresh_narrative_evidence import extract_narrative_evidence, narrative_policy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--package-manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT / "output")
    parser.add_argument("--runtime-root", type=Path, default=ROOT / "output/us-refresh-runtime")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    receipt = extract_narrative_evidence(
        narrative_policy(ticker), args.package_manifest, source_root=args.source_root
    )
    destination = args.runtime_root / "narrative-evidence" / f"{ticker}.json"
    if destination.is_file():
        previous=destination.read_bytes()
        atomic(args.runtime_root/'narrative-evidence-history'/f'{sha256_bytes(previous)}.json',previous)
    # The current receipt is a versioned runtime input, not an append-only
    # history file.  Its source/policy hashes make replacement explicit.
    atomic(destination, canonical_json_bytes(receipt), immutable=False)
    print(destination)


if __name__ == "__main__":
    main()
