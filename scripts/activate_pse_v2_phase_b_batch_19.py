#!/usr/bin/env python3
"""Preflight user-confirmed Batch 19; activate only on a later explicit request."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from app.pse_valuation.catalog import POINTER_SCHEMA, load_pointer
from app.pse_valuation.phase_b_batch_19 import FROZEN_BATCH_TICKERS


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
DEFAULT_CANDIDATE_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-19-candidate-a"
CATALOG_VERSION = "PSE-V2-PHASE-B-B19-2026-09-25-1.0"
CONFIRMED_MANIFEST_SHA256 = "2eb66b33f1dc545d6ae5584040db43234699911cc643ece3f98b5b3613c31b2f"
PREVIOUS_CATALOG_VERSION = "PSE-V2-PHASE-B-B18-2026-09-25-1.0"
PREVIOUS_MANIFEST_SHA256 = "bef1cca0c41bf093c146068a688b1b35829886f281089bd6f0674142439626d1"
PREVIOUS_POINTER_SHA256 = "ad0bd9eed2daa8a7e5c1f2288ead9f8355029dd1002722bdd358eb8971b4deb0"
CONFIRMED_BLOCKED_TICKERS = {"CDC", "HOUSE", "IS", "PAX", "PRIM"}


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
    catalog_root = root / CATALOG_VERSION
    if sha256(catalog_root / "manifest.json") != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("candidate differs from the user-confirmed Batch 19 manifest")
    staged = json.loads((root / "staged.json").read_text())
    if (
        staged.get("schema_version") != POINTER_SCHEMA
        or staged.get("status") != "staged"
        or staged.get("catalog_version") != CATALOG_VERSION
        or staged.get("catalog_path") != CATALOG_VERSION
        or staged.get("manifest_sha256") != CONFIRMED_MANIFEST_SHA256
    ):
        raise RuntimeError("invalid staged pointer")
    candidate = load_pointer(root)
    if len(candidate.entries) != 198 or candidate.version != CATALOG_VERSION:
        raise RuntimeError("candidate does not contain 198 confirmed records")
    if {entry.ticker for entry in candidate.entries if entry.publication_state == "blocked"} != CONFIRMED_BLOCKED_TICKERS:
        raise RuntimeError("confirmed blocked set differs")
    manifest = json.loads((catalog_root / "manifest.json").read_text())
    if tuple(manifest.get("batch", {}).get("frozen_tickers", ())) != FROZEN_BATCH_TICKERS:
        raise RuntimeError("confirmed Batch 19 issuer set differs")
    if manifest.get("availability_counts") != {"intrinsic_valuation": 34, "market_relative_only": 159, "not_available": 5}:
        raise RuntimeError("confirmed availability counts differ")

    active_path = serving_root / "active.json"
    before = json.loads(active_path.read_text())
    if before.get("status") != "active" or before.get("catalog_version") not in {PREVIOUS_CATALOG_VERSION, CATALOG_VERSION} or before.get("catalog_path") != before.get("catalog_version"):
        raise RuntimeError("unexpected active catalog")
    parent_root = serving_root / PREVIOUS_CATALOG_VERSION
    parent_path = parent_root / "manifest.json"
    if sha256(parent_path) != PREVIOUS_MANIFEST_SHA256:
        raise RuntimeError("Batch 18 rollback catalog differs from confirmed parent")
    parent_manifest = json.loads(parent_path.read_text())
    if len(parent_manifest.get("entries", [])) != 188:
        raise RuntimeError("Batch 18 parent count differs")
    if before["catalog_version"] == PREVIOUS_CATALOG_VERSION and (before.get("manifest_sha256") != PREVIOUS_MANIFEST_SHA256 or sha256(active_path) != PREVIOUS_POINTER_SHA256):
        raise RuntimeError("active Batch 18 pointer differs from confirmed parent")
    if before["catalog_version"] == CATALOG_VERSION and before.get("manifest_sha256") != CONFIRMED_MANIFEST_SHA256:
        raise RuntimeError("active Batch 19 pointer differs from confirmed candidate")
    candidate_by_ticker = candidate.entry_by_ticker
    parent_tickers = {entry["ticker"] for entry in parent_manifest["entries"]}
    if parent_tickers & set(FROZEN_BATCH_TICKERS) or set(candidate_by_ticker) != parent_tickers | set(FROZEN_BATCH_TICKERS):
        raise RuntimeError("candidate issuer set or parent overlap differs")
    for entry in parent_manifest["entries"]:
        ticker = entry["ticker"]
        parent_artifact = parent_root / "artifacts" / f"{ticker}.json"
        candidate_artifact = catalog_root / "artifacts" / f"{ticker}.json"
        if sha256(parent_artifact) != entry["artifact_sha256"] or candidate_artifact.read_bytes() != parent_artifact.read_bytes():
            raise RuntimeError(f"{ticker}: inherited artifact differs from confirmed parent")
    for ticker in FROZEN_BATCH_TICKERS:
        receipt_path = catalog_root / "evidence" / f"{ticker}.json"
        artifact = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        if sha256(receipt_path) != artifact["sources"][0]["sha256"]:
            raise RuntimeError(f"{ticker}: reviewed receipt differs from artifact source hash")
    destination = serving_root / CATALOG_VERSION
    if destination.exists() and tree(destination) != tree(catalog_root):
        raise RuntimeError("existing Batch 19 catalog differs from confirmed candidate")
    return {"candidate": CATALOG_VERSION, "manifest_sha256": CONFIRMED_MANIFEST_SHA256, "count": 198, "active_before": before["catalog_version"], "rollback_preserved": True, "ready_for_separate_activation": True}


def activate(root: Path = DEFAULT_CANDIDATE_ROOT, serving_root: Path = SERVING_ROOT) -> dict:
    """Call only after separate authorization to activate Batch 19 locally."""
    checks = preflight(root, serving_root)
    root = Path(root).resolve()
    serving_root = Path(serving_root).resolve()
    staged = json.loads((root / "staged.json").read_text())
    catalog_root = root / CATALOG_VERSION
    destination = serving_root / CATALOG_VERSION
    if not destination.exists():
        shutil.copytree(catalog_root, destination)
    write_pointer(serving_root / "staged.json", staged)
    write_pointer(serving_root / "active.json", {**staged, "status": "active"})
    active = load_pointer(serving_root, "active.json")
    if active.version != CATALOG_VERSION or len(active.entries) != 198:
        raise RuntimeError("local Batch 19 activation failed")
    return {"previous": checks["active_before"], "active": active.version, "count": 198, "manifest_sha256": active.manifest_sha256, "rollback_preserved": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--activate", action="store_true", help="Mutate the local active pointer; requires separate user authorization")
    args = parser.parse_args()
    print(activate(args.candidate_root) if args.activate else preflight(args.candidate_root))
