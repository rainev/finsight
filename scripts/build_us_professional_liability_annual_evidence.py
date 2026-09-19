#!/usr/bin/env python3
"""Build private deterministic annual professional-liability evidence."""
import argparse
import json
from pathlib import Path

from capture_batch_02_structural_sources import _immutable_json
from app.us_valuation.refresh_professional_liability_annual_evidence import extract_annual_professional_liability_evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--package-manifest", action="append", required=True)
    parser.add_argument("--structural", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.package_manifest) != len(args.structural):
        raise ValueError("one annual structural file per manifest required")
    sources = [{"package_manifest_path": manifest, "structural_path": structural}
               for manifest, structural in zip(args.package_manifest, args.structural)]
    receipt = extract_annual_professional_liability_evidence(args.ticker, sources, source_root=args.source_root, cutoff=args.cutoff)
    _immutable_json(args.output, receipt)
    print(json.dumps({"output": str(args.output), "receipt_sha256": receipt["receipt_sha256"], "status": receipt["status"]}, sort_keys=True))
