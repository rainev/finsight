#!/usr/bin/env python3
"""Combine deterministic official-ingestion partitions into one master receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_official_filing_ingestion import build_manifest


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def combine(
    *,
    source_root: Path,
    valuation_root: Path | None,
    valuation_date: str,
    partition_roots: list[Path],
    output_dir: Path,
) -> dict[str, Any]:
    master = build_manifest(
        source_root=source_root,
        valuation_date=valuation_date,
        valuation_root=valuation_root,
    )
    master_by_ticker = {item["ticker"]: item for item in master["issuers"]}
    cases: dict[str, dict[str, Any]] = {}
    partition_hashes = []
    serving_before = None
    serving_after = None
    for root in partition_roots:
        manifest_path = root / "input-manifest.json"
        receipt_path = root / "official-filing-ingestion.json"
        manifest = _read(manifest_path)
        receipt = _read(receipt_path)
        if receipt.get("valuation_date") != valuation_date:
            raise ValueError(f"{root}: valuation date mismatch")
        if receipt.get("serving_artifacts_changed") is not False:
            raise ValueError(f"{root}: serving mutation reported")
        expected_hash = hashlib.sha256(_canonical(manifest)).hexdigest()
        if receipt.get("input_manifest_sha256") != expected_hash:
            raise ValueError(f"{root}: receipt is not bound to its partition manifest")
        if serving_before is None:
            serving_before = receipt["serving_hash_before"]
            serving_after = receipt["serving_hash_after"]
        elif (
            receipt["serving_hash_before"] != serving_before
            or receipt["serving_hash_after"] != serving_after
        ):
            raise ValueError("partition protected hashes disagree")
        partition_hashes.append(
            {
                "partition": root.name,
                "manifest_sha256": expected_hash,
                "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            }
        )
        for case in receipt["issuers"]:
            ticker = case["ticker"]
            if ticker not in master_by_ticker:
                raise ValueError(f"unexpected partition ticker {ticker}")
            if ticker in cases:
                prior_failures = len(cases[ticker].get("package_failures", []))
                replacement_failures = len(case.get("package_failures", []))
                if prior_failures == 0 or replacement_failures >= prior_failures:
                    raise ValueError(f"duplicate partition ticker without a safer repair: {ticker}")
            cases[ticker] = case
    if set(cases) != set(master_by_ticker):
        missing = sorted(set(master_by_ticker) - set(cases))
        raise ValueError(f"partition receipts do not cover master manifest: {missing}")
    ordered = [cases[item["ticker"]] for item in master["issuers"]]
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_raw = _canonical(master)
    manifest_path = output_dir / "input-manifest.json"
    receipt_path = output_dir / "official-filing-ingestion.json"
    result = {
        "schema_version": master["schema_version"],
        "valuation_date": valuation_date,
        "input_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "issuer_count": len(ordered),
        "request_count": sum(len(case["requests"]) for case in ordered),
        "decision_count": sum(len(case["decisions"]) for case in ordered),
        "parsed_package_count": sum(
            item["status"] == "parsed" for case in ordered for item in case["packages"]
        ),
        "failed_package_count": sum(
            item["status"] == "failed" for case in ordered for item in case["packages"]
        ),
        "partition_receipts": partition_hashes,
        "serving_hash_before": serving_before,
        "serving_hash_after": serving_after,
        "serving_artifacts_changed": False,
        "issuers": ordered,
    }
    receipt_raw = _canonical(result)
    for path, raw in ((manifest_path, manifest_raw), (receipt_path, receipt_raw)):
        if path.exists() and path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite combined receipt: {path}")
        path.write_bytes(raw)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--valuation-root", type=Path)
    parser.add_argument("--valuation-date", required=True)
    parser.add_argument("--partition-root", action="append", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = combine(
        source_root=args.source_root,
        valuation_root=args.valuation_root,
        valuation_date=args.valuation_date,
        partition_roots=args.partition_root,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "issuer_count": result["issuer_count"],
        "request_count": result["request_count"],
        "parsed_package_count": result["parsed_package_count"],
        "failed_package_count": result["failed_package_count"],
        "serving_artifacts_changed": result["serving_artifacts_changed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
