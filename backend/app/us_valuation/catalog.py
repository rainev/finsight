"""Manifest-controlled serving for the confirmed U.S. valuation batches.

The website must never infer its published universe from whichever loose JSON
artifacts happen to be checked in.  The active catalog pointer selects one
immutable manifest whose entries bind ticker identity and artifact bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


CATALOG_SCHEMA = "FINSIGHT-US-VALUATION-CATALOG-1.0"
ACTIVE_SCHEMA = "FINSIGHT-US-VALUATION-ACTIVE-1.0"
TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
AVAILABILITY_TYPES = {"available", "conditional_estimate", "not_available"}


class CatalogIntegrityError(ValueError):
    """Raised when the selected catalog cannot prove its exact contents."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogIntegrityError(f"{label} is missing or invalid") from exc
    if not isinstance(value, dict):
        raise CatalogIntegrityError(f"{label} must be a JSON object")
    return value


def _safe_relative_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise CatalogIntegrityError("active catalog path is missing")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise CatalogIntegrityError("active catalog path is unsafe")
    return Path(*path.parts)


@dataclass(frozen=True)
class CatalogEntry:
    ticker: str
    cik: str
    batch: int
    availability_type: str
    artifact_sha256: str
    source_audit: str


@dataclass(frozen=True)
class ValuationCatalog:
    root: Path
    version: str
    universe_version: str
    valuation_date: str
    included_batches: tuple[int, ...]
    entries: tuple[CatalogEntry, ...]
    manifest_sha256: str

    @property
    def artifacts_root(self) -> Path:
        return self.root / "artifacts"

    @property
    def entry_by_ticker(self) -> dict[str, CatalogEntry]:
        return {entry.ticker: entry for entry in self.entries}

    def verify_artifact(self, ticker: str) -> Path:
        entry = self.entry_by_ticker.get(ticker)
        if entry is None:
            raise KeyError(ticker)
        path = self.artifacts_root / f"{ticker}.json"
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise CatalogIntegrityError(f"{ticker}: catalog artifact is missing") from exc
        if _sha256(raw) != entry.artifact_sha256:
            raise CatalogIntegrityError(f"{ticker}: catalog artifact hash mismatch")
        return path

    def public_metadata(self) -> dict[str, Any]:
        return {
            "catalog_version": self.version,
            "universe_version": self.universe_version,
            "valuation_date": self.valuation_date,
            "included_batches": list(self.included_batches),
            "artifact_count": len(self.entries),
        }


def _tree_hash(entries: list[Mapping[str, Any]]) -> str:
    ledger = "".join(
        f"{entry['ticker']}\0{entry['artifact_sha256']}\n"
        for entry in sorted(entries, key=lambda row: str(row["ticker"]))
    ).encode("utf-8")
    return _sha256(ledger)


def load_catalog(root: Path, *, manifest_sha256: str | None = None) -> ValuationCatalog:
    root = Path(root).resolve()
    manifest_path = root / "manifest.json"
    try:
        manifest_raw = manifest_path.read_bytes()
    except OSError as exc:
        raise CatalogIntegrityError("catalog manifest is missing") from exc
    digest = _sha256(manifest_raw)
    if manifest_sha256 and digest != manifest_sha256:
        raise CatalogIntegrityError("active catalog manifest hash mismatch")
    manifest = _read_object(manifest_path, "catalog manifest")
    if manifest.get("schema_version") != CATALOG_SCHEMA:
        raise CatalogIntegrityError("catalog manifest schema is unsupported")

    version = manifest.get("catalog_version")
    universe = manifest.get("universe_version")
    valuation_date = manifest.get("valuation_date")
    batches = manifest.get("included_batches")
    rows = manifest.get("entries")
    if not isinstance(version, str) or not version:
        raise CatalogIntegrityError("catalog version is missing")
    if not isinstance(universe, str) or not universe:
        raise CatalogIntegrityError("catalog universe version is missing")
    if not isinstance(valuation_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valuation_date):
        raise CatalogIntegrityError("catalog valuation date is invalid")
    if not isinstance(batches, list) or batches != list(range(1, 11)):
        raise CatalogIntegrityError("website catalog must contain confirmed batches 1 through 10")
    if not isinstance(rows, list) or len(rows) != 100 or manifest.get("artifact_count") != 100:
        raise CatalogIntegrityError("website catalog must contain exactly 100 batch artifacts")
    if rows != sorted(rows, key=lambda row: str(row.get("ticker", ""))):
        raise CatalogIntegrityError("catalog entries must be sorted")
    if manifest.get("artifact_tree_sha256") != _tree_hash(rows):
        raise CatalogIntegrityError("catalog artifact tree hash mismatch")

    tickers: set[str] = set()
    ciks: set[str] = set()
    counts = {name: 0 for name in sorted(AVAILABILITY_TYPES)}
    entries: list[CatalogEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            raise CatalogIntegrityError("catalog entry is invalid")
        ticker = row.get("ticker")
        cik = row.get("cik")
        batch = row.get("batch")
        availability = row.get("availability_type")
        artifact_digest = row.get("artifact_sha256")
        source_audit = row.get("source_audit")
        if not isinstance(ticker, str) or not TICKER.fullmatch(ticker) or ticker in tickers:
            raise CatalogIntegrityError("catalog ticker is invalid or duplicated")
        if not isinstance(cik, str) or not re.fullmatch(r"\d{10}", cik) or cik in ciks:
            raise CatalogIntegrityError(f"{ticker}: catalog CIK is invalid or duplicated")
        if not isinstance(batch, int) or batch not in batches:
            raise CatalogIntegrityError(f"{ticker}: catalog batch is invalid")
        if availability not in AVAILABILITY_TYPES:
            raise CatalogIntegrityError(f"{ticker}: availability type is invalid")
        if not isinstance(artifact_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", artifact_digest):
            raise CatalogIntegrityError(f"{ticker}: artifact digest is invalid")
        if not isinstance(source_audit, str) or not source_audit:
            raise CatalogIntegrityError(f"{ticker}: source audit is missing")
        tickers.add(ticker)
        ciks.add(cik)
        counts[availability] += 1
        entries.append(CatalogEntry(ticker, cik, batch, availability, artifact_digest, source_audit))

    if manifest.get("availability_counts") != counts:
        raise CatalogIntegrityError("catalog availability counts are invalid")
    artifact_files = {path.stem for path in (root / "artifacts").glob("*.json")}
    if artifact_files != tickers:
        raise CatalogIntegrityError("catalog artifact files do not exactly match the manifest")

    catalog = ValuationCatalog(root, version, universe, valuation_date, tuple(batches), tuple(entries), digest)
    for entry in entries:
        path = catalog.verify_artifact(entry.ticker)
        artifact = _read_object(path, f"{entry.ticker} artifact")
        issuer = artifact.get("issuer")
        if (
            not isinstance(issuer, dict)
            or issuer.get("ticker") != entry.ticker
            or str(issuer.get("cik", "")).zfill(10) != entry.cik
        ):
            raise CatalogIntegrityError(f"{entry.ticker}: artifact identity mismatch")
    return catalog


def load_active_catalog(catalogs_root: Path) -> ValuationCatalog:
    catalogs_root = Path(catalogs_root).resolve()
    active = _read_object(catalogs_root / "active.json", "active catalog pointer")
    if active.get("schema_version") != ACTIVE_SCHEMA:
        raise CatalogIntegrityError("active catalog pointer schema is unsupported")
    relative = _safe_relative_path(active.get("catalog_path"))
    expected_version = active.get("catalog_version")
    expected_manifest = active.get("manifest_sha256")
    if not isinstance(expected_manifest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest):
        raise CatalogIntegrityError("active catalog manifest digest is invalid")
    catalog = load_catalog(catalogs_root / relative, manifest_sha256=expected_manifest)
    if catalog.version != expected_version:
        raise CatalogIntegrityError("active catalog version mismatch")
    return catalog
