#!/usr/bin/env python3
"""Build the immutable, staged eight-company PSE V2 Phase A catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.pse_valuation import CATALOG_VERSION
from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.pipeline import VALUATION_DATE, build_pilot_artifacts


ROOT = Path(__file__).resolve().parents[1]
CATALOGS_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
UNIVERSE_VERSION = "PSE-V2-PILOT-8-1.0"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, value: dict) -> bytes:
    raw = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def build(output_root: Path = CATALOGS_ROOT) -> Path:
    artifacts = build_pilot_artifacts(ROOT)
    catalog_root = output_root / CATALOG_VERSION
    artifacts_root = catalog_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    entries = []
    for ticker, artifact in artifacts.items():
        path = artifacts_root / f"{ticker}.json"
        raw = _write_json(path, artifact.model_dump(mode="json"))
        entries.append(
            {
                "ticker": ticker,
                "availability_type": artifact.availability_type,
                "publication_state": artifact.publication_state,
                "primary_model": artifact.primary_model,
                "artifact_sha256": _sha256(raw),
                "source_audit": f"PSE-V2-PILOT-{ticker}-SOURCE-1.0",
            }
        )

    availability = {name: 0 for name in ("intrinsic_valuation", "market_relative_only", "not_available")}
    publication = {name: 0 for name in ("approved", "provisional", "blocked")}
    for entry in entries:
        availability[entry["availability_type"]] += 1
        publication[entry["publication_state"]] += 1
    manifest = {
        "schema_version": CATALOG_SCHEMA,
        "catalog_version": CATALOG_VERSION,
        "universe_version": UNIVERSE_VERSION,
        "valuation_date": VALUATION_DATE.isoformat(),
        "catalog_status": "staged",
        "artifact_count": len(entries),
        "availability_counts": availability,
        "publication_counts": publication,
        "entries": entries,
    }
    manifest_raw = _write_json(catalog_root / "manifest.json", manifest)
    pointer = {
        "schema_version": POINTER_SCHEMA,
        "status": "staged",
        "catalog_version": CATALOG_VERSION,
        "catalog_path": CATALOG_VERSION,
        "manifest_sha256": _sha256(manifest_raw),
    }
    _write_json(output_root / "staged.json", pointer)
    load_pointer(output_root)
    return catalog_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=CATALOGS_ROOT)
    args = parser.parse_args()
    print(build(args.output.resolve()))


if __name__ == "__main__":
    main()
