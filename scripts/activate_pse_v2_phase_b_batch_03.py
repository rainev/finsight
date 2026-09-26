#!/usr/bin/env python3
"""Activate the confirmed PSE V2 Phase B Batch 3 catalog locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from app.pse_valuation.catalog import POINTER_SCHEMA, load_pointer


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-03-candidate-a"
CATALOG_VERSION = "PSE-V2-PHASE-B-B03-2026-09-22-1.0"
CONFIRMED_MANIFEST_SHA256 = "fb420ec53ea1878743e3c3debd9082ecd57de867837a2080b2820d94259cc35a"
PREVIOUS_CATALOG_VERSION = "PSE-V2-PHASE-B-B02-2026-09-22-1.0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(root: Path) -> dict[Path, str]:
    return {path.relative_to(root): _sha256(path) for path in root.rglob("*") if path.is_file()}


def _write_pointer(path: Path, value: dict) -> None:
    raw = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)


def activate(candidate_root: Path = DEFAULT_CANDIDATE_ROOT) -> dict:
    candidate_root = candidate_root.resolve()
    candidate_catalog = candidate_root / CATALOG_VERSION
    candidate_manifest = candidate_catalog / "manifest.json"
    if _sha256(candidate_manifest) != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("candidate manifest does not match the confirmed Batch 3 result")
    staged_pointer = json.loads((candidate_root / "staged.json").read_text())
    if (
        staged_pointer.get("schema_version") != POINTER_SCHEMA
        or staged_pointer.get("catalog_version") != CATALOG_VERSION
        or staged_pointer.get("manifest_sha256") != CONFIRMED_MANIFEST_SHA256
    ):
        raise RuntimeError("candidate staged pointer is invalid")

    active_before = json.loads((SERVING_ROOT / "active.json").read_text())
    if active_before.get("catalog_version") not in {PREVIOUS_CATALOG_VERSION, CATALOG_VERSION}:
        raise RuntimeError("unexpected active catalog; refusing to replace it")
    if not (SERVING_ROOT / PREVIOUS_CATALOG_VERSION / "manifest.json").is_file():
        raise RuntimeError("previous 28-company catalog is missing; rollback would be unavailable")

    destination = SERVING_ROOT / CATALOG_VERSION
    if destination.exists():
        if _tree(destination) != _tree(candidate_catalog):
            raise RuntimeError("existing Batch 3 catalog differs from the confirmed candidate")
    else:
        shutil.copytree(candidate_catalog, destination)

    serving_staged = dict(staged_pointer)
    serving_staged["status"] = "staged"
    serving_active = dict(staged_pointer)
    serving_active["status"] = "active"
    _write_pointer(SERVING_ROOT / "staged.json", serving_staged)
    _write_pointer(SERVING_ROOT / "active.json", serving_active)

    active = load_pointer(SERVING_ROOT, "active.json")
    if active.version != CATALOG_VERSION or active.status != "active" or len(active.entries) != 38:
        raise RuntimeError("activated Batch 3 catalog failed validation")
    return {
        "previous_catalog_version": active_before["catalog_version"],
        "active_catalog_version": active.version,
        "artifact_count": len(active.entries),
        "manifest_sha256": active.manifest_sha256,
        "rollback_catalog_preserved": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    args = parser.parse_args()
    print(activate(args.candidate_root))


if __name__ == "__main__":
    main()
