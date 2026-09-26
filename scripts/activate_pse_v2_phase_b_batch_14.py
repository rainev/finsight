#!/usr/bin/env python3
"""Preflight the confirmed Batch 14 candidate; activate only on a later request."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from app.pse_valuation.catalog import POINTER_SCHEMA, load_pointer


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-14-candidate-a"
CATALOG_VERSION = "PSE-V2-PHASE-B-B14-2026-09-23-1.0"
CONFIRMED_MANIFEST_SHA256 = "3afe1ac6f26b5e8751a714cf15776cc8e05a00304735d4b8b77b3c2922e54d38"
PREVIOUS_CATALOG_VERSION = "PSE-V2-PHASE-B-B13-2026-09-23-1.0"
PREVIOUS_MANIFEST_SHA256 = "beea44ae0f261aedf5c0d832253c45714ffebc50f7b59868b4a39b881740cc3c"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root: Path) -> dict:
    return {path.relative_to(root): sha256(path) for path in root.rglob("*") if path.is_file()}


def write_pointer(path: Path, value: dict) -> None:
    raw = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)


def preflight(root: Path = DEFAULT_CANDIDATE_ROOT, serving_root: Path = SERVING_ROOT) -> dict:
    root = Path(root).resolve()
    serving_root = Path(serving_root).resolve()
    catalog = root / CATALOG_VERSION
    if sha256(catalog / "manifest.json") != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("candidate differs from the user-confirmed Batch 14 manifest")
    staged = json.loads((root / "staged.json").read_text())
    if staged.get("schema_version") != POINTER_SCHEMA or staged.get("status") != "staged" or staged.get("catalog_version") != CATALOG_VERSION or staged.get("catalog_path") != CATALOG_VERSION or staged.get("manifest_sha256") != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("invalid staged pointer")
    candidate = load_pointer(root)
    if len(candidate.entries) != 148 or candidate.version != CATALOG_VERSION:
        raise RuntimeError("candidate does not contain 148 confirmed records")
    before = json.loads((serving_root / "active.json").read_text())
    if before.get("status") != "active" or before.get("catalog_version") not in {PREVIOUS_CATALOG_VERSION, CATALOG_VERSION}:
        raise RuntimeError("unexpected active catalog")
    parent = serving_root / PREVIOUS_CATALOG_VERSION / "manifest.json"
    if sha256(parent) != PREVIOUS_MANIFEST_SHA256:
        raise RuntimeError("Batch 13 rollback catalog differs from confirmed parent")
    if before["catalog_version"] == PREVIOUS_CATALOG_VERSION and before.get("manifest_sha256") != PREVIOUS_MANIFEST_SHA256:
        raise RuntimeError("active Batch 13 pointer differs from confirmed parent")
    if before["catalog_version"] == CATALOG_VERSION and before.get("manifest_sha256") != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("active Batch 14 pointer differs from confirmed candidate")
    destination = serving_root / CATALOG_VERSION
    if destination.exists() and tree(destination) != tree(catalog):
        raise RuntimeError("existing Batch 14 catalog differs from confirmed candidate")
    return {"candidate": CATALOG_VERSION, "manifest_sha256": CONFIRMED_MANIFEST_SHA256, "count": 148, "active_before": before["catalog_version"], "rollback_preserved": True, "ready_for_separate_activation": True}


def activate(root: Path = DEFAULT_CANDIDATE_ROOT, serving_root: Path = SERVING_ROOT) -> dict:
    """Call only after separate authorization to activate Batch 14 locally."""
    checks = preflight(root, serving_root)
    root = Path(root).resolve()
    serving_root = Path(serving_root).resolve()
    staged = json.loads((root / "staged.json").read_text())
    catalog = root / CATALOG_VERSION
    destination = serving_root / CATALOG_VERSION
    if not destination.exists():
        shutil.copytree(catalog, destination)
    write_pointer(serving_root / "staged.json", staged)
    write_pointer(serving_root / "active.json", {**staged, "status": "active"})
    active = load_pointer(serving_root, "active.json")
    if active.version != CATALOG_VERSION or len(active.entries) != 148:
        raise RuntimeError("local Batch 14 activation failed")
    return {"previous": checks["active_before"], "active": active.version, "count": 148, "manifest_sha256": active.manifest_sha256, "rollback_preserved": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--activate", action="store_true", help="Mutate the local active pointer; requires separate user authorization")
    args = parser.parse_args()
    print(activate(args.candidate_root) if args.activate else preflight(args.candidate_root))
