#!/usr/bin/env python3
"""Build a staged cumulative 18-issuer candidate without touching active PSE V2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.contract import PseValuationArtifact
from app.pse_valuation.phase_b_batch_01 import (
    FROZEN_BATCH_TICKERS,
    build_batch_artifacts,
    load_batch_config,
    source_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
SERVING_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"
ACTIVE_POINTER = SERVING_ROOT / "active.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output/pse-valuation-candidates/phase-b-batch-01"
PARENT_CATALOG_VERSION = "PSE-V2-PILOT-2026-09-21-1.1"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: dict) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _write_json(path: Path, value: dict) -> bytes:
    raw = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _serving_snapshot() -> tuple[bytes, bytes, Path, dict]:
    pointer_raw = ACTIVE_POINTER.read_bytes()
    pointer = json.loads(pointer_raw)
    active_root = SERVING_ROOT / pointer["catalog_path"]
    manifest_raw = (active_root / "manifest.json").read_bytes()
    parent_root = SERVING_ROOT / PARENT_CATALOG_VERSION
    parent_manifest = json.loads((parent_root / "manifest.json").read_text())
    if pointer.get("status") != "active":
        raise RuntimeError("PSE active pointer is not active")
    if parent_manifest.get("artifact_count") != 8:
        raise RuntimeError("confirmed eight-company parent catalog is invalid")
    return pointer_raw, manifest_raw, parent_root, parent_manifest


def build(output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    output_root = output_root.resolve()
    if output_root == SERVING_ROOT.resolve() or SERVING_ROOT.resolve() in output_root.parents:
        raise RuntimeError("Phase B candidates must remain outside the active serving catalog root")

    pointer_before, manifest_before, parent_root, parent_manifest = _serving_snapshot()
    config = load_batch_config()
    batch_artifacts = build_batch_artifacts(config)
    catalog_root = output_root / config["catalog_version"]
    artifacts_root = catalog_root / "artifacts"
    evidence_root = catalog_root / "evidence"
    entries: list[dict] = []

    active_entries = {row["ticker"]: row for row in parent_manifest["entries"]}
    for ticker in sorted(active_entries):
        source = parent_root / "artifacts" / f"{ticker}.json"
        raw = source.read_bytes()
        target = artifacts_root / f"{ticker}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        if _sha256(raw) != active_entries[ticker]["artifact_sha256"]:
            raise RuntimeError(f"{ticker}: active artifact digest mismatch")
        entries.append(dict(active_entries[ticker]))

    for ticker in FROZEN_BATCH_TICKERS:
        artifact = batch_artifacts[ticker]
        receipt_reference, receipt_raw = source_receipt(ticker, config)
        receipt_path = evidence_root / f"{ticker}.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_bytes(receipt_raw)
        if _sha256(receipt_raw) != receipt_reference["sha256"]:
            raise RuntimeError(f"{ticker}: reviewed fact receipt digest mismatch")
        raw = _write_json(artifacts_root / f"{ticker}.json", artifact.model_dump(mode="json"))
        entries.append(
            {
                "ticker": ticker,
                "availability_type": artifact.availability_type,
                "publication_state": artifact.publication_state,
                "primary_model": artifact.primary_model,
                "artifact_sha256": _sha256(raw),
                "source_audit": f"PSE-V2-PHASE-B-B01-{ticker}-SOURCE-1.0",
            }
        )

    entries.sort(key=lambda row: row["ticker"])
    expected = sorted([*active_entries, *FROZEN_BATCH_TICKERS])
    if [row["ticker"] for row in entries] != expected or len(entries) != 18:
        raise RuntimeError("cumulative candidate does not contain the exact active-eight plus frozen-ten issuer set")

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
    if len(candidate.entries) != 18:
        raise RuntimeError("candidate validation did not return 18 entries")

    pointer_after, manifest_after, _parent_root_after, _manifest = _serving_snapshot()
    if pointer_after != pointer_before or manifest_after != manifest_before:
        raise RuntimeError("active PSE catalog changed during Phase B candidate generation")
    return catalog_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    print(build(args.output))


if __name__ == "__main__":
    main()
