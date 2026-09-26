#!/usr/bin/env python3
"""Activate the exact confirmed Batch 13 candidate only on separate authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from app.pse_valuation.catalog import POINTER_SCHEMA, load_pointer


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-13-candidate-a"
CATALOG_VERSION = "PSE-V2-PHASE-B-B13-2026-09-23-1.0"
CONFIRMED_MANIFEST_SHA256 = "beea44ae0f261aedf5c0d832253c45714ffebc50f7b59868b4a39b881740cc3c"
PREVIOUS_CATALOG_VERSION = "PSE-V2-PHASE-B-B12-2026-09-23-1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root: Path) -> dict:
    return {path.relative_to(root): sha256(path) for path in root.rglob("*") if path.is_file()}


def write_pointer(path: Path, value: dict) -> None:
    raw = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)


def activate(root: Path = DEFAULT_CANDIDATE_ROOT) -> dict:
    root = Path(root).resolve()
    catalog = root / CATALOG_VERSION
    manifest = catalog / "manifest.json"
    if sha256(manifest) != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("unconfirmed candidate")
    staged = json.loads((root / "staged.json").read_text())
    if staged.get("schema_version") != POINTER_SCHEMA or staged.get("catalog_version") != CATALOG_VERSION or staged.get("manifest_sha256") != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("invalid staged pointer")
    before = json.loads((SERVING_ROOT / "active.json").read_text())
    if before.get("catalog_version") not in {PREVIOUS_CATALOG_VERSION, CATALOG_VERSION}:
        raise RuntimeError("unexpected active catalog")
    previous = SERVING_ROOT / PREVIOUS_CATALOG_VERSION
    if not (previous / "manifest.json").is_file():
        raise RuntimeError("Batch 12 rollback catalog missing")
    destination = SERVING_ROOT / CATALOG_VERSION
    if destination.exists():
        if tree(destination) != tree(catalog):
            raise RuntimeError("existing catalog differs from confirmed candidate")
    else:
        shutil.copytree(catalog, destination)
    write_pointer(SERVING_ROOT / "staged.json", {**staged, "status": "staged"})
    write_pointer(SERVING_ROOT / "active.json", {**staged, "status": "active"})
    active = load_pointer(SERVING_ROOT, "active.json")
    if active.version != CATALOG_VERSION or len(active.entries) != 138:
        raise RuntimeError("activation failed")
    return {"previous": before["catalog_version"], "active": active.version, "count": 138, "manifest_sha256": active.manifest_sha256, "rollback_preserved": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()
    print(activate(args.candidate_root))
