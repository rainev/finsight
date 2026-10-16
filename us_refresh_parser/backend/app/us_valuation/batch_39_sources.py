"""Receipt verification for Batch 39 inputs."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

from .batch_39 import BATCH_39_MANIFEST, BATCH_39_VALUATION_DATE


def _verify_source_bundle(*, ticker: str, packet: Path, structural_packet: Path, structural_cache_root: Path, filing: dict[str, Any]) -> dict[str, Any]:
    issuer = next(row for row in BATCH_39_MANIFEST if row.ticker == ticker)
    source_manifest_path = packet / "source-manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text())
    if source_manifest.get("issuer", {}).get("ticker") != ticker or source_manifest.get("issuer", {}).get("cik") != issuer.cik:
        raise ValueError(f"{ticker}: source packet identity mismatch")
    packet_hashes = {}
    for name, expected in source_manifest.get("packet_payload_sha256", {}).items():
        path = packet / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != expected:
            raise ValueError(f"{ticker}: source packet hash mismatch for {name}")
        packet_hashes[name] = actual
    receipt_path = structural_packet / "source-receipt.json"
    structural_path = structural_packet / "structural-filing.json"
    package_path = structural_packet / "package-manifest.json"
    receipt = json.loads(receipt_path.read_text())
    package = json.loads(package_path.read_text())
    expected_filing = {"accession": filing["accession"], "filed": filing["filed"], "form": filing["form"], "report_date": filing["period_end"]}
    if receipt.get("schema_version") != "FINSIGHT-BATCH-39-STRUCTURAL-SOURCE-1" or receipt.get("ticker") != ticker or receipt.get("cik") != issuer.cik or receipt.get("valuation_date") != BATCH_39_VALUATION_DATE or any((receipt.get("filing") or {}).get(key) != value for key, value in expected_filing.items()):
        raise ValueError(f"{ticker}: structural receipt identity mismatch")
    structural_hash = hashlib.sha256(structural_path.read_bytes()).hexdigest()
    package_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
    if structural_hash != receipt.get("structural_filing_sha256") or package_hash != receipt.get("package_manifest_sha256"):
        raise ValueError(f"{ticker}: structural source hash mismatch")
    entrypoint = package.get("entrypoint_local_path")
    entry = next((row for row in package.get("files", []) if row.get("local_path") == entrypoint), None)
    html_path = next((Path(structural_cache_root) / "filings" / ticker).glob(f"**/{entrypoint}"), None) if entrypoint else None
    if entry is None or html_path is None or hashlib.sha256(html_path.read_bytes()).hexdigest() != entry.get("sha256"):
        raise ValueError(f"{ticker}: primary filing document hash mismatch")
    return {"source_kind": "runtime_verified_source_bundle", "ticker": ticker, "cik": issuer.cik, "source_manifest_sha256": hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(), "packet_payload_sha256": packet_hashes, "structural_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "structural_filing_sha256": structural_hash, "package_manifest_sha256": package_hash, "primary_document": entrypoint, "primary_document_sha256": entry["sha256"], "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "verified": True}
