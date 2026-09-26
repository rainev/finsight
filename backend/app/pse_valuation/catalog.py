"""Immutable, hash-bound catalogs for staged PSE V2 valuation artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any

from .contract import PseValuationArtifact


CATALOG_SCHEMA = "FINSIGHT-PSE-VALUATION-CATALOG-1.0"
POINTER_SCHEMA = "FINSIGHT-PSE-VALUATION-POINTER-1.0"
AVAILABILITY_TYPES = {"intrinsic_valuation", "market_relative_only", "not_available"}
PUBLICATION_STATES = {"approved", "provisional", "blocked"}
TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")


class CatalogIntegrityError(ValueError):
    pass


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
        raise CatalogIntegrityError("catalog path is missing")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise CatalogIntegrityError("catalog path is unsafe")
    return Path(*path.parts)


@dataclass(frozen=True)
class CatalogEntry:
    ticker: str
    availability_type: str
    publication_state: str
    primary_model: str
    artifact_sha256: str
    source_audit: str


@dataclass(frozen=True)
class PseValuationCatalog:
    root: Path
    version: str
    universe_version: str
    valuation_date: str
    status: str
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
            raise CatalogIntegrityError(f"{ticker}: artifact is missing") from exc
        if _sha256(raw) != entry.artifact_sha256:
            raise CatalogIntegrityError(f"{ticker}: artifact hash mismatch")
        artifact = PseValuationArtifact.model_validate_json(raw)
        if artifact.ticker != ticker or not artifact.verify_artifact_hash():
            raise CatalogIntegrityError(f"{ticker}: artifact identity or internal hash mismatch")
        if (
            artifact.availability_type != entry.availability_type
            or artifact.publication_state != entry.publication_state
            or artifact.primary_model != entry.primary_model
        ):
            raise CatalogIntegrityError(f"{ticker}: manifest metadata differs from the artifact")
        return path

    def public_metadata(self) -> dict[str, Any]:
        return {
            "catalog_version": self.version,
            "universe_version": self.universe_version,
            "valuation_date": self.valuation_date,
            "catalog_status": self.status,
            "artifact_count": len(self.entries),
        }


def load_catalog(root: Path, *, manifest_sha256: str | None = None) -> PseValuationCatalog:
    root = Path(root).resolve()
    manifest_path = root / "manifest.json"
    try:
        manifest_raw = manifest_path.read_bytes()
    except OSError as exc:
        raise CatalogIntegrityError("catalog manifest is missing") from exc
    digest = _sha256(manifest_raw)
    if manifest_sha256 and digest != manifest_sha256:
        raise CatalogIntegrityError("catalog manifest hash mismatch")
    manifest = _read_object(manifest_path, "catalog manifest")
    if manifest.get("schema_version") != CATALOG_SCHEMA:
        raise CatalogIntegrityError("catalog schema is unsupported")
    rows = manifest.get("entries")
    artifact_count = manifest.get("artifact_count")
    if (
        not isinstance(rows, list)
        or not rows
        or not isinstance(artifact_count, int)
        or artifact_count != len(rows)
    ):
        raise CatalogIntegrityError("catalog artifact count is invalid")
    if rows != sorted(rows, key=lambda row: str(row.get("ticker", ""))):
        raise CatalogIntegrityError("catalog entries must be sorted")

    tickers: set[str] = set()
    entries: list[CatalogEntry] = []
    availability_counts = {key: 0 for key in sorted(AVAILABILITY_TYPES)}
    publication_counts = {key: 0 for key in sorted(PUBLICATION_STATES)}
    for row in rows:
        ticker = row.get("ticker")
        availability = row.get("availability_type")
        state = row.get("publication_state")
        digest_value = row.get("artifact_sha256")
        if not isinstance(ticker, str) or not TICKER.fullmatch(ticker) or ticker in tickers:
            raise CatalogIntegrityError("catalog ticker is invalid or duplicated")
        if availability not in AVAILABILITY_TYPES or state not in PUBLICATION_STATES:
            raise CatalogIntegrityError(f"{ticker}: catalog state is invalid")
        if not isinstance(digest_value, str) or not re.fullmatch(r"[0-9a-f]{64}", digest_value):
            raise CatalogIntegrityError(f"{ticker}: artifact digest is invalid")
        tickers.add(ticker)
        availability_counts[availability] += 1
        publication_counts[state] += 1
        entries.append(
            CatalogEntry(
                ticker=ticker,
                availability_type=availability,
                publication_state=state,
                primary_model=str(row.get("primary_model") or ""),
                artifact_sha256=digest_value,
                source_audit=str(row.get("source_audit") or ""),
            )
        )
    if manifest.get("availability_counts") != availability_counts:
        raise CatalogIntegrityError("catalog availability counts are invalid")
    if manifest.get("publication_counts") != publication_counts:
        raise CatalogIntegrityError("catalog publication counts are invalid")
    artifact_files = {path.stem for path in (root / "artifacts").glob("*.json")}
    if artifact_files != tickers:
        raise CatalogIntegrityError("catalog artifact files do not exactly match the manifest")

    catalog = PseValuationCatalog(
        root=root,
        version=str(manifest.get("catalog_version") or ""),
        universe_version=str(manifest.get("universe_version") or ""),
        valuation_date=str(manifest.get("valuation_date") or ""),
        status=str(manifest.get("catalog_status") or ""),
        entries=tuple(entries),
        manifest_sha256=digest,
    )
    if catalog.status not in {"staged", "active"}:
        raise CatalogIntegrityError("catalog manifest status is invalid")
    for entry in entries:
        catalog.verify_artifact(entry.ticker)
    return catalog


def load_pointer(catalogs_root: Path, pointer_name: str = "staged.json") -> PseValuationCatalog:
    catalogs_root = Path(catalogs_root).resolve()
    pointer = _read_object(catalogs_root / pointer_name, "catalog pointer")
    if pointer.get("schema_version") != POINTER_SCHEMA:
        raise CatalogIntegrityError("catalog pointer schema is unsupported")
    relative = _safe_relative_path(pointer.get("catalog_path"))
    expected_manifest = pointer.get("manifest_sha256")
    if not isinstance(expected_manifest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest):
        raise CatalogIntegrityError("catalog pointer manifest digest is invalid")
    catalog = load_catalog(catalogs_root / relative, manifest_sha256=expected_manifest)
    pointer_status = pointer.get("status")
    if pointer_status not in {"staged", "active"}:
        raise CatalogIntegrityError("catalog pointer status is invalid")
    if catalog.version != pointer.get("catalog_version"):
        raise CatalogIntegrityError("catalog pointer version or status mismatch")
    return replace(catalog, status=pointer_status)
