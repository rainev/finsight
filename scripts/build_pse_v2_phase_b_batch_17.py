#!/usr/bin/env python3
"""Build the frozen 178-record Batch 17 candidate outside active serving."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.phase_b_batch_17 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
ACTIVE_POINTER = SERVING_ROOT / "active.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-17-candidate-a"
PARENT_CATALOG_VERSION = "PSE-V2-PHASE-B-B16-2026-09-25-1.0"
PARENT_MANIFEST_SHA256 = "729e2272ddb7674592212cef7682b496e1814e68b0d326a6b3c4e0e75b628b93"
PARENT_POINTER_SHA256 = "f86e87818993602af954ebb7f0c334307add93c687004d59e725e13797377888"
CATALOG_VERSION = "PSE-V2-PHASE-B-B17-2026-09-25-1.0"
ACTIVE_POINTER_SHA256 = "baea93d879687860442a50512fc6a4253b2a4a6d355df972cf59d17d5e5b5aa2"
ACTIVE_MANIFEST_SHA256 = "63790df2c3df426b0b5c2e6e0ec8ca3c25c204717eee71a0b3a665f95f1efb92"


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
    if pointer.get("status") != "active" or pointer.get("catalog_version") not in {PARENT_CATALOG_VERSION, CATALOG_VERSION, "PSE-V2-PHASE-B-B18-2026-09-25-1.0", "PSE-V2-PHASE-B-B19-2026-09-25-1.0", "PSE-V2-PHASE-B-B20-2026-09-25-1.0", "PSE-V2-PHASE-B-B21-2026-09-25-1.0", "PSE-V2-PHASE-B-B22-2026-09-25-1.0", "PSE-V2-PHASE-B-B23-2026-09-25-1.0", "PSE-V2-PHASE-B-B24-2026-09-25-1.0", "PSE-V2-PHASE-B-B25-2026-09-25-1.0", "PSE-V2-PHASE-B-B26-2026-09-25-1.0", "PSE-V2-PHASE-B-B27-2026-09-25-1.0", "PSE-V2-PHASE-B-B28-2026-09-26-1.0"} or pointer.get("catalog_path") != pointer.get("catalog_version"):
        raise RuntimeError("unexpected active catalog while reproducing Batch 17")
    expected_pointer = {PARENT_CATALOG_VERSION: PARENT_POINTER_SHA256, CATALOG_VERSION: ACTIVE_POINTER_SHA256, "PSE-V2-PHASE-B-B18-2026-09-25-1.0": "ad0bd9eed2daa8a7e5c1f2288ead9f8355029dd1002722bdd358eb8971b4deb0", "PSE-V2-PHASE-B-B19-2026-09-25-1.0": "f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e", "PSE-V2-PHASE-B-B20-2026-09-25-1.0": "cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f", "PSE-V2-PHASE-B-B21-2026-09-25-1.0": "7d20dc192b2859f109f8400158592e7ce6cd33c4f19e3ccdf718f3dffac0fe0c", "PSE-V2-PHASE-B-B22-2026-09-25-1.0": "8355c4838a6ff48ebdcb06d582570b391e9f29af6d2bcb29ce3a81ef3411f193", "PSE-V2-PHASE-B-B23-2026-09-25-1.0": "5ad7fb97f37a443d025f09841bee2643222f201d1fbd6af527e8bf4c40ccd8c4", "PSE-V2-PHASE-B-B24-2026-09-25-1.0": "f3afe66297cf939e595bbcfc12ae7fb2c6b2ee19ca4851e0dbd2485a1dc67e53", "PSE-V2-PHASE-B-B25-2026-09-25-1.0": "c476841f32dcaeef1995477f566ddfc0ce0c6ea6fddcaf490342c519b2c9338e", "PSE-V2-PHASE-B-B26-2026-09-25-1.0": "ebc67e971ec52323e56ce2b3e909dbf71d4f0400c237f3746ea0d80a5667f371", "PSE-V2-PHASE-B-B27-2026-09-25-1.0": "c1edb4294e00c8e986e5336b2f3b1a226e08b3dd8a074bc1169e4f3ec8218e08", "PSE-V2-PHASE-B-B28-2026-09-26-1.0": "50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92"}[pointer["catalog_version"]]
    expected_manifest = {PARENT_CATALOG_VERSION: PARENT_MANIFEST_SHA256, CATALOG_VERSION: ACTIVE_MANIFEST_SHA256, "PSE-V2-PHASE-B-B18-2026-09-25-1.0": "bef1cca0c41bf093c146068a688b1b35829886f281089bd6f0674142439626d1", "PSE-V2-PHASE-B-B19-2026-09-25-1.0": "2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f", "PSE-V2-PHASE-B-B20-2026-09-25-1.0": "50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23", "PSE-V2-PHASE-B-B21-2026-09-25-1.0": "eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3", "PSE-V2-PHASE-B-B22-2026-09-25-1.0": "f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26", "PSE-V2-PHASE-B-B23-2026-09-25-1.0": "84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631", "PSE-V2-PHASE-B-B24-2026-09-25-1.0": "89b78a2fa1597a5b4d8cfd1e606f567554be18c222d7c782bc02a5879fc27ef0", "PSE-V2-PHASE-B-B25-2026-09-25-1.0": "ae8f1e0b0fc13eab2f39ea5a6f7c2d419cb425ef792c845f8f9f89f1005a308c", "PSE-V2-PHASE-B-B26-2026-09-25-1.0": "d1d929b164286168f77d6e0e9d9dbbe93f7af4f73610cc47ec20b88606ebf60a", "PSE-V2-PHASE-B-B27-2026-09-25-1.0": "9799ff5e8f536d914d1addaa37b10946b402f06c6ec6fe8aca8e570454b44f85", "PSE-V2-PHASE-B-B28-2026-09-26-1.0": "8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7"}[pointer["catalog_version"]]
    if sha256(pointer_raw) != expected_pointer or pointer.get("manifest_sha256") != expected_manifest:
        raise RuntimeError("active pointer differs from the confirmed catalog")
    active_manifest_raw = (SERVING_ROOT / pointer["catalog_path"] / "manifest.json").read_bytes()
    if sha256(active_manifest_raw) != expected_manifest:
        raise RuntimeError("active manifest differs from the confirmed catalog")
    parent_root = SERVING_ROOT / PARENT_CATALOG_VERSION
    manifest_raw = (parent_root / "manifest.json").read_bytes()
    if sha256(manifest_raw) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("Batch 16 active parent manifest differs")
    manifest = json.loads(manifest_raw)
    if manifest.get("artifact_count") != 168:
        raise RuntimeError("Batch 16 parent count differs")
    return pointer_raw, active_manifest_raw, parent_root, manifest


def build(output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    output_root = Path(output_root).resolve()
    serving_root = SERVING_ROOT.resolve()
    if output_root == serving_root or serving_root in output_root.parents:
        raise RuntimeError("Batch 17 candidate must remain outside serving root")
    pointer_before, manifest_before, parent_root, parent_manifest = snapshot_parent()
    config = load_batch_config()
    if config["catalog_version"] != CATALOG_VERSION:
        raise RuntimeError("Batch 17 catalog version mismatch")
    batch = build_batch_artifacts(config)
    parent_entries = {row["ticker"]: row for row in parent_manifest["entries"]}
    if set(parent_entries) & set(FROZEN_BATCH_TICKERS):
        raise RuntimeError("Batch 17 overlaps the confirmed parent")
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
        entries.append({"ticker": ticker, "availability_type": artifact.availability_type, "publication_state": artifact.publication_state, "primary_model": artifact.primary_model, "artifact_sha256": sha256(artifact_raw), "source_audit": f"PSE-V2-PHASE-B-B17-{ticker}-SOURCE-1.0"})
    entries.sort(key=lambda row: row["ticker"])
    if len(entries) != 178 or {row["ticker"] for row in entries} != set(parent_entries) | set(FROZEN_BATCH_TICKERS):
        raise RuntimeError("candidate must contain exact 168 plus confirmed ten")
    availability = {key: 0 for key in ("intrinsic_valuation", "market_relative_only", "not_available")}
    publication = {key: 0 for key in ("approved", "provisional", "blocked")}
    for entry in entries:
        availability[entry["availability_type"]] += 1
        publication[entry["publication_state"]] += 1
    manifest = {"schema_version": CATALOG_SCHEMA, "catalog_version": CATALOG_VERSION, "universe_version": config["universe_version"], "valuation_date": config["valuation_date"], "catalog_status": "staged", "artifact_count": 178, "availability_counts": availability, "publication_counts": publication, "batch": {"batch_version": config["batch_version"], "frozen_tickers": list(FROZEN_BATCH_TICKERS), "active_parent_catalog": parent_manifest["catalog_version"], "active_parent_manifest_sha256": PARENT_MANIFEST_SHA256}, "entries": entries}
    manifest_raw = write_json(catalog_root / "manifest.json", manifest)
    write_json(output_root / "staged.json", {"schema_version": POINTER_SCHEMA, "status": "staged", "catalog_version": CATALOG_VERSION, "catalog_path": CATALOG_VERSION, "manifest_sha256": sha256(manifest_raw)})
    if len(load_pointer(output_root).entries) != 178:
        raise RuntimeError("Batch 17 candidate validation failed")
    pointer_after, manifest_after, _, _ = snapshot_parent()
    if pointer_after != pointer_before or manifest_after != manifest_before:
        raise RuntimeError("active catalog changed during build")
    return catalog_root


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    print(build(args.output))
