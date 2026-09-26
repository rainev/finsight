#!/usr/bin/env python3
"""Preflight confirmed Batch 16; activate only on a later explicit request."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from app.pse_valuation.catalog import POINTER_SCHEMA, load_pointer


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-16-candidate-a"
CATALOG_VERSION = "PSE-V2-PHASE-B-B16-2026-09-25-1.0"
CONFIRMED_MANIFEST_SHA256 = "729e2272ddb7674592212cef7682b496e1814e68b0d326a6b3c4e0e75b628b93"
PREVIOUS_CATALOG_VERSION = "PSE-V2-PHASE-B-B15-2026-09-23-1.0"
PREVIOUS_MANIFEST_SHA256 = "641265728e673864851eeffaf3a989f9e18f41bba498aa5b523b383e60921aa3"


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
        raise RuntimeError("candidate differs from the user-confirmed Batch 16 manifest")
    staged = json.loads((root / "staged.json").read_text())
    if staged.get("schema_version") != POINTER_SCHEMA or staged.get("status") != "staged" or staged.get("catalog_version") != CATALOG_VERSION or staged.get("catalog_path") != CATALOG_VERSION or staged.get("manifest_sha256") != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("invalid staged pointer")
    candidate = load_pointer(root)
    if len(candidate.entries) != 168 or candidate.version != CATALOG_VERSION:
        raise RuntimeError("candidate does not contain 168 confirmed records")
    if {entry.ticker for entry in candidate.entries if entry.publication_state == "blocked"} != {"CDC", "HOUSE"}:
        raise RuntimeError("confirmed blocked set differs")
    before = json.loads((serving_root / "active.json").read_text())
    if before.get("status") != "active" or before.get("catalog_version") not in {PREVIOUS_CATALOG_VERSION, CATALOG_VERSION}:
        raise RuntimeError("unexpected active catalog")
    parent = serving_root / PREVIOUS_CATALOG_VERSION / "manifest.json"
    if sha256(parent) != PREVIOUS_MANIFEST_SHA256:
        raise RuntimeError("Batch 15 rollback catalog differs from confirmed parent")
    if before["catalog_version"] == PREVIOUS_CATALOG_VERSION and before.get("manifest_sha256") != PREVIOUS_MANIFEST_SHA256:
        raise RuntimeError("active Batch 15 pointer differs from confirmed parent")
    if before["catalog_version"] == CATALOG_VERSION and before.get("manifest_sha256") != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("active Batch 16 pointer differs from confirmed candidate")
    destination = serving_root / CATALOG_VERSION
    if destination.exists() and tree(destination) != tree(catalog):
        raise RuntimeError("existing Batch 16 catalog differs from confirmed candidate")
    return {"candidate": CATALOG_VERSION, "manifest_sha256": CONFIRMED_MANIFEST_SHA256, "count": 168, "active_before": before["catalog_version"], "rollback_preserved": True, "ready_for_separate_activation": True}


def activate(root: Path = DEFAULT_CANDIDATE_ROOT, serving_root: Path = SERVING_ROOT) -> dict:
    """Call only after separate authorization to activate Batch 16 locally."""
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
    if active.version != CATALOG_VERSION or len(active.entries) != 168:
        raise RuntimeError("local Batch 16 activation failed")
    return {"previous": checks["active_before"], "active": active.version, "count": 168, "manifest_sha256": active.manifest_sha256, "rollback_preserved": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--activate", action="store_true", help="Mutate the local active pointer; requires separate user authorization")
    args = parser.parse_args()
    print(activate(args.candidate_root) if args.activate else preflight(args.candidate_root))
