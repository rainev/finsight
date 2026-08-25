#!/usr/bin/env python3
"""Freeze all future universe-reset batch manifests in one deterministic run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.batch_01 import BATCH_01_MANIFEST
from app.us_valuation.batch_partition import (
    FAMILY_BY_SECTOR,
    FAMILY_TAXONOMY_VERSION,
    PARTITION_VERSION,
    build_partition,
)
from app.us_valuation.universe import UNIVERSE_VERSION, load_universe


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _immutable(path: Path, raw: bytes) -> None:
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable batch file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent)) / path.name
    try:
        temp.write_bytes(raw)
        temp.replace(path)
    finally:
        temp.parent.rmdir()


def freeze(*, output_root: Path, config_root: Path) -> dict[str, Any]:
    universe = load_universe()
    batches = build_partition(universe)
    batch_payloads = {
        f"batch_{batch['batch']:02d}.json": _json_bytes(batch) for batch in batches
    }
    routing_snapshot = {
        "family_taxonomy_version": FAMILY_TAXONOMY_VERSION,
        "purpose": "partition-only preflight; final source-backed model routing may change without swapping batch membership",
        "records": [
            {
                "cik": row.cik,
                "ticker": row.ticker,
                "gics_sector": row.gics_sector,
                "gics_sub_industry": row.gics_sub_industry,
                "partition_model_family": FAMILY_BY_SECTOR[row.gics_sector],
            }
            for row in universe
        ],
    }
    routing_raw = _json_bytes(routing_snapshot)
    digest = hashlib.sha256()
    for name, raw in sorted(batch_payloads.items()):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).digest())
        digest.update(b"\n")
    partition_root_hash = digest.hexdigest()
    universe_path = ROOT / "backend/app/us_valuation/config/universe_2026_08_14.json"
    receipt = {
        "partition_version": PARTITION_VERSION,
        "universe_version": UNIVERSE_VERSION,
        "valuation_date": "2026-08-14",
        "batch_01_grandfathered_mixed_model_exception": True,
        "future_batch_composition_rule": "8 core + 2 economically predeclared boundary; at most 2 partition cohort families",
        "future_batch_count": 49,
        "future_issuer_count": 490,
        "batch_numbers": list(range(2, 51)),
        "batch_01_ciks": sorted(issuer.cik for issuer in BATCH_01_MANIFEST),
        "family_taxonomy_version": FAMILY_TAXONOMY_VERSION,
        "family_taxonomy": FAMILY_BY_SECTOR,
        "input_hashes": {
            "universe_manifest": _sha(universe_path.read_bytes()),
            "batch_01_contract": _sha((ROOT / "backend/app/us_valuation/batch_01.py").read_bytes()),
            "partition_code": _sha((ROOT / "backend/app/us_valuation/batch_partition.py").read_bytes()),
            "routing_snapshot": _sha(routing_raw),
        },
        "batch_sha256": {
            name: _sha(raw) for name, raw in sorted(batch_payloads.items())
        },
        "partition_root_sha256": partition_root_hash,
        "exact_cover": {
            "universe_count": 500,
            "batch_01_count": 10,
            "future_count": 490,
            "pairwise_disjoint": True,
            "all_universe_ciks_covered": True,
        },
        "prohibited_partition_inputs": [
            "valuation result",
            "publication state",
            "source availability",
            "reliability",
            "intrinsic value",
            "processing cost",
        ],
    }
    receipt_raw = _json_bytes(receipt)
    for root in (output_root, config_root):
        for name, raw in batch_payloads.items():
            _immutable(root / name, raw)
        _immutable(root / "routing_snapshot.json", routing_raw)
        _immutable(root / "partition_receipt.json", receipt_raw)
    return {
        "future_batch_count": 49,
        "future_issuer_count": 490,
        "partition_root_sha256": partition_root_hash,
        "batch_02_tickers": [
            row["ticker"] for row in batches[0]["members"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--config-root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(freeze(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
