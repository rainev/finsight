#!/usr/bin/env python3
"""Build a staged cumulative 48-issuer Batch 4 candidate without activation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.phase_b_batch_04 import (
    FROZEN_BATCH_TICKERS,
    build_batch_artifacts,
    load_batch_config,
    source_receipts,
)


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
ACTIVE_POINTER = SERVING_ROOT / "active.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-04-candidate-a"
PARENT_CATALOG_VERSION = "PSE-V2-PHASE-B-B03-2026-09-22-1.0"
PARENT_MANIFEST_SHA256 = "fb420ec53ea1878743e3c3debd9082ecd57de867837a2080b2820d94259cc35a"
CATALOG_VERSION = "PSE-V2-PHASE-B-B04-2026-09-22-1.0"
SUCCESSOR_CATALOG_VERSIONS = {
    "PSE-V2-PHASE-B-B05-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B06-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B07-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B08-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B09-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B10-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B11-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B12-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B13-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B14-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B15-2026-09-23-1.0",
    "PSE-V2-PHASE-B-B16-2026-09-25-1.0",
    "PSE-V2-PHASE-B-B17-2026-09-25-1.0",
    "PSE-V2-PHASE-B-B18-2026-09-25-1.0", "PSE-V2-PHASE-B-B19-2026-09-25-1.0", "PSE-V2-PHASE-B-B20-2026-09-25-1.0", "PSE-V2-PHASE-B-B21-2026-09-25-1.0", "PSE-V2-PHASE-B-B22-2026-09-25-1.0", "PSE-V2-PHASE-B-B23-2026-09-25-1.0", "PSE-V2-PHASE-B-B24-2026-09-25-1.0", "PSE-V2-PHASE-B-B25-2026-09-25-1.0", "PSE-V2-PHASE-B-B26-2026-09-25-1.0", "PSE-V2-PHASE-B-B27-2026-09-25-1.0", "PSE-V2-PHASE-B-B28-2026-09-26-1.0",
}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, value: dict) -> bytes:
    raw = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _active_snapshot() -> tuple[bytes, bytes, Path, dict]:
    pointer_raw = ACTIVE_POINTER.read_bytes()
    pointer = json.loads(pointer_raw)
    if pointer.get("status") != "active" or pointer.get("catalog_version") not in {
        PARENT_CATALOG_VERSION,
        CATALOG_VERSION,
        *SUCCESSOR_CATALOG_VERSIONS,
    }:
        raise RuntimeError("unexpected active catalog while reproducing Phase B Batch 4")
    active_root = SERVING_ROOT / pointer["catalog_path"]
    manifest_raw = (active_root / "manifest.json").read_bytes()
    parent_root = SERVING_ROOT / PARENT_CATALOG_VERSION
    parent_manifest_raw = (parent_root / "manifest.json").read_bytes()
    if _sha256(parent_manifest_raw) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("confirmed Batch 3 parent manifest hash differs")
    parent_manifest = json.loads(parent_manifest_raw)
    if parent_manifest.get("artifact_count") != 38:
        raise RuntimeError("confirmed Batch 3 parent catalog does not contain exactly 38 artifacts")
    return pointer_raw, manifest_raw, parent_root, parent_manifest


def build(output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    output_root = output_root.resolve()
    if output_root == SERVING_ROOT.resolve() or SERVING_ROOT.resolve() in output_root.parents:
        raise RuntimeError("Phase B candidates must remain outside the active serving catalog root")
    pointer_before, manifest_before, parent_root, parent_manifest = _active_snapshot()
    config = load_batch_config()
    batch_artifacts = build_batch_artifacts(config)
    catalog_root = output_root / config["catalog_version"]
    artifacts_root = catalog_root / "artifacts"
    evidence_root = catalog_root / "evidence"
    entries: list[dict] = []

    parent_entries = {row["ticker"]: row for row in parent_manifest["entries"]}
    overlap = sorted(set(parent_entries) & set(FROZEN_BATCH_TICKERS))
    if overlap:
        raise RuntimeError(f"Batch 4 overlaps the active parent catalog: {', '.join(overlap)}")
    for ticker in sorted(parent_entries):
        raw = (parent_root / "artifacts" / f"{ticker}.json").read_bytes()
        if _sha256(raw) != parent_entries[ticker]["artifact_sha256"]:
            raise RuntimeError(f"{ticker}: active parent artifact digest mismatch")
        target = artifacts_root / f"{ticker}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        entries.append(dict(parent_entries[ticker]))

    for ticker in FROZEN_BATCH_TICKERS:
        artifact = batch_artifacts[ticker]
        for index, (reference, receipt_raw) in enumerate(source_receipts(ticker, config), start=1):
            receipt_path = evidence_root / f"{ticker}-{index:02d}.json"
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_bytes(receipt_raw)
            if _sha256(receipt_raw) != reference["sha256"]:
                raise RuntimeError(f"{ticker}: reviewed fact receipt digest mismatch")
        raw = _write_json(artifacts_root / f"{ticker}.json", artifact.model_dump(mode="json"))
        entries.append(
            {
                "ticker": ticker,
                "availability_type": artifact.availability_type,
                "publication_state": artifact.publication_state,
                "primary_model": artifact.primary_model,
                "artifact_sha256": _sha256(raw),
                "source_audit": f"PSE-V2-PHASE-B-B04-{ticker}-SOURCE-1.0",
            }
        )

    entries.sort(key=lambda row: row["ticker"])
    expected = sorted([*parent_entries, *FROZEN_BATCH_TICKERS])
    if len(entries) != 48 or [row["ticker"] for row in entries] != expected:
        raise RuntimeError("cumulative candidate does not contain the exact active-38 plus frozen-10 issuer set")
    availability = {name: 0 for name in ("intrinsic_valuation", "market_relative_only", "not_available")}
    publication = {name: 0 for name in ("approved", "provisional", "blocked")}
    for entry in entries:
        availability[entry["availability_type"]] += 1
        publication[entry["publication_state"]] += 1
    manifest = {
        "schema_version": CATALOG_SCHEMA,
        "catalog_version": config["catalog_version"],
        "universe_version": config["universe_version"],
        "valuation_date": config["valuation_date"],
        "catalog_status": "staged",
        "artifact_count": len(entries),
        "availability_counts": availability,
        "publication_counts": publication,
        "batch": {
            "batch_version": config["batch_version"],
            "frozen_tickers": list(FROZEN_BATCH_TICKERS),
            "active_parent_catalog": parent_manifest["catalog_version"],
            "active_parent_manifest_sha256": PARENT_MANIFEST_SHA256,
        },
        "entries": entries,
    }
    manifest_raw = _write_json(catalog_root / "manifest.json", manifest)
    _write_json(
        output_root / "staged.json",
        {
            "schema_version": POINTER_SCHEMA,
            "status": "staged",
            "catalog_version": config["catalog_version"],
            "catalog_path": config["catalog_version"],
            "manifest_sha256": _sha256(manifest_raw),
        },
    )
    candidate = load_pointer(output_root)
    if candidate.status != "staged" or len(candidate.entries) != 48:
        raise RuntimeError("candidate validation did not return 48 staged entries")
    pointer_after, manifest_after, _root_after, _manifest_after = _active_snapshot()
    if pointer_after != pointer_before or manifest_after != manifest_before:
        raise RuntimeError("active PSE catalog changed during Batch 4 candidate generation")
    return catalog_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    print(build(args.output))


if __name__ == "__main__":
    main()
