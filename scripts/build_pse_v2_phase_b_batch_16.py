#!/usr/bin/env python3
"""Build exact cumulative Batch 16 beside the active Batch 15 serving root."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.phase_b_batch_16 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
ACTIVE_POINTER = SERVING_ROOT / "active.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-16-candidate-a"
PARENT_CATALOG_VERSION = "PSE-V2-PHASE-B-B15-2026-09-23-1.0"
PARENT_MANIFEST_SHA256 = "641265728e673864851eeffaf3a989f9e18f41bba498aa5b523b383e60921aa3"
CATALOG_VERSION = "PSE-V2-PHASE-B-B16-2026-09-25-1.0"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, value: dict) -> bytes:
    raw = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def snapshot_parent() -> tuple[bytes, bytes, Path, dict]:
    pointer_raw = ACTIVE_POINTER.read_bytes()
    pointer = json.loads(pointer_raw)
    if pointer.get("status") != "active" or pointer.get("catalog_version") not in {PARENT_CATALOG_VERSION, CATALOG_VERSION, "PSE-V2-PHASE-B-B17-2026-09-25-1.0", "PSE-V2-PHASE-B-B18-2026-09-25-1.0", "PSE-V2-PHASE-B-B19-2026-09-25-1.0", "PSE-V2-PHASE-B-B20-2026-09-25-1.0", "PSE-V2-PHASE-B-B21-2026-09-25-1.0", "PSE-V2-PHASE-B-B22-2026-09-25-1.0", "PSE-V2-PHASE-B-B23-2026-09-25-1.0", "PSE-V2-PHASE-B-B24-2026-09-25-1.0", "PSE-V2-PHASE-B-B25-2026-09-25-1.0", "PSE-V2-PHASE-B-B26-2026-09-25-1.0", "PSE-V2-PHASE-B-B27-2026-09-25-1.0", "PSE-V2-PHASE-B-B28-2026-09-26-1.0"}:
        raise RuntimeError("unexpected active catalog")
    active_manifest_raw = (SERVING_ROOT / pointer["catalog_path"] / "manifest.json").read_bytes()
    if sha256(active_manifest_raw) != pointer["manifest_sha256"]:
        raise RuntimeError("active pointer and manifest differ")
    parent_root = SERVING_ROOT / PARENT_CATALOG_VERSION
    parent_manifest_raw = (parent_root / "manifest.json").read_bytes()
    if sha256(parent_manifest_raw) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("confirmed Batch 15 parent hash differs")
    parent_manifest = json.loads(parent_manifest_raw)
    if parent_manifest["artifact_count"] != 158:
        raise RuntimeError("Batch 15 parent count differs")
    return pointer_raw, active_manifest_raw, parent_root, parent_manifest


def build(output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    output_root = Path(output_root).resolve()
    serving_root = SERVING_ROOT.resolve()
    if output_root == serving_root or serving_root in output_root.parents:
        raise RuntimeError("candidate must remain outside serving root")
    pointer_before, manifest_before, parent_root, parent_manifest = snapshot_parent()
    config = load_batch_config()
    if config["catalog_version"] != CATALOG_VERSION:
        raise RuntimeError("Batch 16 catalog version mismatch")
    batch = build_batch_artifacts(config)
    parent_entries = {row["ticker"]: row for row in parent_manifest["entries"]}
    if set(parent_entries) & set(FROZEN_BATCH_TICKERS):
        raise RuntimeError("Batch 16 overlaps confirmed parent")
    catalog_root = output_root / CATALOG_VERSION
    entries = []
    for ticker in sorted(parent_entries):
        raw = (parent_root / "artifacts" / f"{ticker}.json").read_bytes()
        if sha256(raw) != parent_entries[ticker]["artifact_sha256"]:
            raise RuntimeError(f"{ticker}: parent artifact digest mismatch")
        target = catalog_root / "artifacts" / f"{ticker}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        entries.append(dict(parent_entries[ticker]))
    for ticker in FROZEN_BATCH_TICKERS:
        artifact = batch[ticker]
        references, receipt_raw = source_receipt(ticker, config)
        if sha256(receipt_raw) != references[0]["sha256"]:
            raise RuntimeError(f"{ticker}: reviewed receipt hash mismatch")
        evidence_path = catalog_root / "evidence" / f"{ticker}.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(receipt_raw)
        artifact_raw = write_json(catalog_root / "artifacts" / f"{ticker}.json", artifact.model_dump(mode="json"))
        entries.append({"ticker": ticker, "availability_type": artifact.availability_type, "publication_state": artifact.publication_state, "primary_model": artifact.primary_model, "artifact_sha256": sha256(artifact_raw), "source_audit": f"PSE-V2-PHASE-B-B16-{ticker}-SOURCE-1.0"})
    entries.sort(key=lambda row: row["ticker"])
    if len(entries) != 168 or {row["ticker"] for row in entries} != set(parent_entries) | set(FROZEN_BATCH_TICKERS):
        raise RuntimeError("candidate must contain exact 158 plus confirmed ten")
    availability = {key: 0 for key in ("intrinsic_valuation", "market_relative_only", "not_available")}
    publication = {key: 0 for key in ("approved", "provisional", "blocked")}
    for entry in entries:
        availability[entry["availability_type"]] += 1
        publication[entry["publication_state"]] += 1
    manifest = {"schema_version": CATALOG_SCHEMA, "catalog_version": CATALOG_VERSION, "universe_version": config["universe_version"], "valuation_date": config["valuation_date"], "catalog_status": "staged", "artifact_count": 168, "availability_counts": availability, "publication_counts": publication, "batch": {"batch_version": config["batch_version"], "frozen_tickers": list(FROZEN_BATCH_TICKERS), "active_parent_catalog": parent_manifest["catalog_version"], "active_parent_manifest_sha256": PARENT_MANIFEST_SHA256}, "entries": entries}
    manifest_raw = write_json(catalog_root / "manifest.json", manifest)
    write_json(output_root / "staged.json", {"schema_version": POINTER_SCHEMA, "status": "staged", "catalog_version": CATALOG_VERSION, "catalog_path": CATALOG_VERSION, "manifest_sha256": sha256(manifest_raw)})
    if len(load_pointer(output_root).entries) != 168:
        raise RuntimeError("candidate validation failed")
    pointer_after, manifest_after, _, _ = snapshot_parent()
    if pointer_after != pointer_before or manifest_after != manifest_before:
        raise RuntimeError("active catalog changed during build")
    return catalog_root


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    print(build(args.output))
