#!/usr/bin/env python3
"""Build the 208-entry Batch 20 candidate outside active serving."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.phase_b_batch_20 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
ACTIVE_POINTER = SERVING_ROOT / "active.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-20-candidate-a"
PARENT_CATALOG_VERSION = "PSE-V2-PHASE-B-B19-2026-09-25-1.0"
PARENT_MANIFEST_SHA256 = "2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f"
PARENT_POINTER_SHA256 = "f4002d7a63c89938df3380f0d64da00742b6717b9ea65a1716d72810735e214e"
CATALOG_VERSION = "PSE-V2-PHASE-B-B20-2026-09-25-1.0"
ACTIVE_POINTER_SHA256 = "cac24ffdb3f4a795ee3c204bd48c096d31491b1874a7e34580c156eaa5a1e20f"
ACTIVE_MANIFEST_SHA256 = "50227c8db032133bf191da95ba4f8b9de94b717dc423fa8b027607a9b061ea23"
SUCCESSOR_CATALOG_VERSION = "PSE-V2-PHASE-B-B21-2026-09-25-1.0"
SUCCESSOR_POINTER_SHA256 = "7d20dc192b2859f109f8400158592e7ce6cd33c4f19e3ccdf718f3dffac0fe0c"
SUCCESSOR_MANIFEST_SHA256 = "eddf03189b851c60a4c8166de1cf8d57ad37ea7b0510791b152ae3e939a992a3"
LATER_CATALOG_VERSION = "PSE-V2-PHASE-B-B22-2026-09-25-1.0"
LATER_POINTER_SHA256 = "8355c4838a6ff48ebdcb06d582570b391e9f29af6d2bcb29ce3a81ef3411f193"
LATER_MANIFEST_SHA256 = "f173bcc9b8854563f5bce9655c2f7c88e08187e9447ae115c1b012e5bb6c9f26"
NEWEST_CATALOG_VERSION = "PSE-V2-PHASE-B-B23-2026-09-25-1.0"
NEWEST_POINTER_SHA256 = "5ad7fb97f37a443d025f09841bee2643222f201d1fbd6af527e8bf4c40ccd8c4"
NEWEST_MANIFEST_SHA256 = "84f33618d2cf063028ec0bac58e5742e1dbd0f51a595ed7f625a4d26ccbfe631"
NEXT_CATALOG_VERSION = "PSE-V2-PHASE-B-B24-2026-09-25-1.0"
NEXT_POINTER_SHA256 = "f3afe66297cf939e595bbcfc12ae7fb2c6b2ee19ca4851e0dbd2485a1dc67e53"
NEXT_MANIFEST_SHA256 = "89b78a2fa1597a5b4d8cfd1e606f567554be18c222d7c782bc02a5879fc27ef0"
FOLLOWING_CATALOG_VERSION = "PSE-V2-PHASE-B-B25-2026-09-25-1.0"
FOLLOWING_POINTER_SHA256 = "c476841f32dcaeef1995477f566ddfc0ce0c6ea6fddcaf490342c519b2c9338e"
FOLLOWING_MANIFEST_SHA256 = "ae8f1e0b0fc13eab2f39ea5a6f7c2d419cb425ef792c845f8f9f89f1005a308c"
AFTER_CATALOG_VERSION = "PSE-V2-PHASE-B-B26-2026-09-25-1.0"
AFTER_POINTER_SHA256 = "ebc67e971ec52323e56ce2b3e909dbf71d4f0400c237f3746ea0d80a5667f371"
AFTER_MANIFEST_SHA256 = "d1d929b164286168f77d6e0e9d9dbbe93f7af4f73610cc47ec20b88606ebf60a"
POST_B26_CATALOG_VERSION = "PSE-V2-PHASE-B-B27-2026-09-25-1.0"
POST_B26_POINTER_SHA256 = "c1edb4294e00c8e986e5336b2f3b1a226e08b3dd8a074bc1169e4f3ec8218e08"
POST_B26_MANIFEST_SHA256 = "9799ff5e8f536d914d1addaa37b10946b402f06c6ec6fe8aca8e570454b44f85"
POST_B27_CATALOG_VERSION = "PSE-V2-PHASE-B-B28-2026-09-26-1.0"
POST_B27_POINTER_SHA256 = "50652bb9490f77d73d8cddb8b98058197910a0271c935d6685339370e0f7da92"
POST_B27_MANIFEST_SHA256 = "8145c9d5c9b1ff4c05400fdd0ead4d6528594ed32cb424ab70c481c0f245c5a7"


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
    if pointer.get("status") != "active" or pointer.get("catalog_version") not in {PARENT_CATALOG_VERSION, CATALOG_VERSION, SUCCESSOR_CATALOG_VERSION, LATER_CATALOG_VERSION, NEWEST_CATALOG_VERSION, NEXT_CATALOG_VERSION, FOLLOWING_CATALOG_VERSION, AFTER_CATALOG_VERSION, POST_B26_CATALOG_VERSION, POST_B27_CATALOG_VERSION} or pointer.get("catalog_path") != pointer.get("catalog_version"):
        raise RuntimeError("unexpected active catalog while reproducing Batch 20")
    expected_pointer = {PARENT_CATALOG_VERSION: PARENT_POINTER_SHA256, CATALOG_VERSION: ACTIVE_POINTER_SHA256, SUCCESSOR_CATALOG_VERSION: SUCCESSOR_POINTER_SHA256, LATER_CATALOG_VERSION: LATER_POINTER_SHA256, NEWEST_CATALOG_VERSION: NEWEST_POINTER_SHA256, NEXT_CATALOG_VERSION: NEXT_POINTER_SHA256, FOLLOWING_CATALOG_VERSION: FOLLOWING_POINTER_SHA256, AFTER_CATALOG_VERSION: AFTER_POINTER_SHA256, POST_B26_CATALOG_VERSION: POST_B26_POINTER_SHA256, POST_B27_CATALOG_VERSION: POST_B27_POINTER_SHA256}[pointer["catalog_version"]]
    expected_manifest = {PARENT_CATALOG_VERSION: PARENT_MANIFEST_SHA256, CATALOG_VERSION: ACTIVE_MANIFEST_SHA256, SUCCESSOR_CATALOG_VERSION: SUCCESSOR_MANIFEST_SHA256, LATER_CATALOG_VERSION: LATER_MANIFEST_SHA256, NEWEST_CATALOG_VERSION: NEWEST_MANIFEST_SHA256, NEXT_CATALOG_VERSION: NEXT_MANIFEST_SHA256, FOLLOWING_CATALOG_VERSION: FOLLOWING_MANIFEST_SHA256, AFTER_CATALOG_VERSION: AFTER_MANIFEST_SHA256, POST_B26_CATALOG_VERSION: POST_B26_MANIFEST_SHA256, POST_B27_CATALOG_VERSION: POST_B27_MANIFEST_SHA256}[pointer["catalog_version"]]
    if sha256(pointer_raw) != expected_pointer or pointer.get("manifest_sha256") != expected_manifest:
        raise RuntimeError("active pointer differs from confirmed catalog")
    if sha256((SERVING_ROOT / pointer["catalog_path"] / "manifest.json").read_bytes()) != expected_manifest:
        raise RuntimeError("active manifest differs from confirmed catalog")
    parent_root = SERVING_ROOT / PARENT_CATALOG_VERSION
    manifest_raw = (parent_root / "manifest.json").read_bytes()
    if sha256(manifest_raw) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("Batch 19 manifest differs from confirmed parent")
    manifest = json.loads(manifest_raw)
    if manifest.get("artifact_count") != 198:
        raise RuntimeError("Batch 19 parent count differs")
    return pointer_raw, manifest_raw, parent_root, manifest


def build(output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    output_root = Path(output_root).resolve()
    serving_root = SERVING_ROOT.resolve()
    if output_root == serving_root or serving_root in output_root.parents:
        raise RuntimeError("Batch 20 candidate must remain outside serving root")
    pointer_before, manifest_before, parent_root, parent_manifest = snapshot_parent()
    config = load_batch_config()
    if config["catalog_version"] != CATALOG_VERSION:
        raise RuntimeError("Batch 20 catalog version mismatch")
    batch = build_batch_artifacts(config)
    parent_entries = {row["ticker"]: row for row in parent_manifest["entries"]}
    if set(parent_entries) & set(FROZEN_BATCH_TICKERS):
        raise RuntimeError("Batch 20 overlaps confirmed parent")
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
            raise RuntimeError(f"{ticker}: reviewed fact-receipt digest mismatch")
        evidence_path = catalog_root / "evidence" / f"{ticker}.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(receipt_raw)
        artifact_raw = write_json(catalog_root / "artifacts" / f"{ticker}.json", artifact.model_dump(mode="json"))
        entries.append({"ticker": ticker, "availability_type": artifact.availability_type, "publication_state": artifact.publication_state, "primary_model": artifact.primary_model, "artifact_sha256": sha256(artifact_raw), "source_audit": f"PSE-V2-PHASE-B-B20-{ticker}-SOURCE-1.0"})
    entries.sort(key=lambda row: row["ticker"])
    if len(entries) != 208 or {row["ticker"] for row in entries} != set(parent_entries) | set(FROZEN_BATCH_TICKERS):
        raise RuntimeError("candidate must contain exact 198 plus confirmed ten")
    availability = {key: 0 for key in ("intrinsic_valuation", "market_relative_only", "not_available")}
    publication = {key: 0 for key in ("approved", "provisional", "blocked")}
    for entry in entries:
        availability[entry["availability_type"]] += 1
        publication[entry["publication_state"]] += 1
    manifest = {"schema_version": CATALOG_SCHEMA, "catalog_version": CATALOG_VERSION, "universe_version": config["universe_version"], "valuation_date": config["valuation_date"], "catalog_status": "staged", "artifact_count": 208, "availability_counts": availability, "publication_counts": publication, "batch": {"batch_version": config["batch_version"], "frozen_tickers": list(FROZEN_BATCH_TICKERS), "active_parent_catalog": PARENT_CATALOG_VERSION, "active_parent_manifest_sha256": PARENT_MANIFEST_SHA256}, "entries": entries}
    manifest_raw = write_json(catalog_root / "manifest.json", manifest)
    write_json(output_root / "staged.json", {"schema_version": POINTER_SCHEMA, "status": "staged", "catalog_version": CATALOG_VERSION, "catalog_path": CATALOG_VERSION, "manifest_sha256": sha256(manifest_raw)})
    if len(load_pointer(output_root).entries) != 208:
        raise RuntimeError("Batch 20 candidate validation failed")
    pointer_after, manifest_after, _, _ = snapshot_parent()
    if pointer_after != pointer_before or manifest_after != manifest_before:
        raise RuntimeError("active catalog changed during build")
    return catalog_root


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    print(build(args.output))
