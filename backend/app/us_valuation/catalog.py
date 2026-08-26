"""Manifest-controlled U.S. valuation catalogs.

The serving API must never infer its universe from whichever JSON files happen
to be present in a directory.  A catalog is immutable: its manifest names every
artifact and binds its identity and bytes.  ``active.json`` is the only mutable
pointer and can be switched atomically after a candidate catalog is verified.
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
    """Raised when a catalog cannot prove its exact contents."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def artifact_tree_sha256(entries: list[Mapping[str, Any]]) -> str:
    ledger = "".join(
        f"{entry['ticker']}\0{entry['artifact_sha256']}\n"
        for entry in sorted(entries, key=lambda row: str(row["ticker"]))
    ).encode("utf-8")
    return sha256_bytes(ledger)


def _read_object(path: Path, *, label: str) -> dict[str, Any]:
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
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise CatalogIntegrityError("active catalog path is unsafe")
    return Path(*pure.parts)


@dataclass(frozen=True)
class CatalogEntry:
    ticker: str
    cik: str
    batch: int | None
    availability_type: str
    artifact_sha256: str
    source_audit: str


@dataclass(frozen=True)
class ValuationCatalog:
    root: Path
    manifest_path: Path
    manifest_sha256: str
    catalog_version: str
    universe_version: str
    valuation_date: str
    included_batches: tuple[int, ...]
    entries: tuple[CatalogEntry, ...]
    manifest: Mapping[str, Any]

    @property
    def artifacts_root(self) -> Path:
        return self.root / "artifacts"

    @property
    def entry_by_ticker(self) -> dict[str, CatalogEntry]:
        return {entry.ticker: entry for entry in self.entries}

    def artifact_path(self, ticker: str) -> Path:
        entry = self.entry_by_ticker.get(ticker)
        if entry is None:
            raise KeyError(ticker)
        return self.artifacts_root / f"{entry.ticker}.json"

    def verify_artifact(self, ticker: str) -> Path:
        entry = self.entry_by_ticker.get(ticker)
        if entry is None:
            raise KeyError(ticker)
        path = self.artifacts_root / f"{entry.ticker}.json"
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise CatalogIntegrityError(f"{ticker}: catalog artifact is missing") from exc
        if sha256_bytes(raw) != entry.artifact_sha256:
            raise CatalogIntegrityError(f"{ticker}: catalog artifact hash mismatch")
        return path

    def public_metadata(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "universe_version": self.universe_version,
            "valuation_date": self.valuation_date,
            "included_batches": list(self.included_batches),
            "artifact_count": len(self.entries),
        }


def load_catalog_version(
    root: Path,
    *,
    expected_manifest_sha256: str | None = None,
    verify_artifacts: bool = True,
) -> ValuationCatalog:
    root = Path(root).resolve()
    manifest_path = root / "manifest.json"
    try:
        manifest_raw = manifest_path.read_bytes()
    except OSError as exc:
        raise CatalogIntegrityError("catalog manifest is missing") from exc
    manifest_digest = sha256_bytes(manifest_raw)
    if expected_manifest_sha256 and manifest_digest != expected_manifest_sha256:
        raise CatalogIntegrityError("active catalog manifest hash mismatch")
    manifest = _read_object(manifest_path, label="catalog manifest")
    if manifest.get("schema_version") != CATALOG_SCHEMA:
        raise CatalogIntegrityError("catalog manifest schema is unsupported")

    catalog_version = manifest.get("catalog_version")
    universe_version = manifest.get("universe_version")
    valuation_date = manifest.get("valuation_date")
    included_batches = manifest.get("included_batches")
    raw_entries = manifest.get("entries")
    if not isinstance(catalog_version, str) or not catalog_version:
        raise CatalogIntegrityError("catalog version is missing")
    if not isinstance(universe_version, str) or not universe_version:
        raise CatalogIntegrityError("catalog universe version is missing")
    if not isinstance(valuation_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valuation_date):
        raise CatalogIntegrityError("catalog valuation date is invalid")
    if (
        not isinstance(included_batches, list)
        or any(not isinstance(batch, int) or isinstance(batch, bool) or batch < 1 for batch in included_batches)
        or included_batches != sorted(set(included_batches))
    ):
        raise CatalogIntegrityError("catalog included batches are invalid")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise CatalogIntegrityError("catalog entries are missing")
    if manifest.get("artifact_count") != len(raw_entries):
        raise CatalogIntegrityError("catalog artifact count does not match entries")

    entries: list[CatalogEntry] = []
    tickers: set[str] = set()
    ciks: set[str] = set()
    availability_counts = {name: 0 for name in sorted(AVAILABILITY_TYPES)}
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise CatalogIntegrityError("catalog entry is invalid")
        ticker = raw_entry.get("ticker")
        cik = raw_entry.get("cik")
        batch = raw_entry.get("batch")
        availability = raw_entry.get("availability_type")
        digest = raw_entry.get("artifact_sha256")
        source_audit = raw_entry.get("source_audit")
        if not isinstance(ticker, str) or not TICKER.fullmatch(ticker):
            raise CatalogIntegrityError("catalog ticker is invalid")
        if ticker in tickers:
            raise CatalogIntegrityError(f"{ticker}: duplicate catalog ticker")
        if not isinstance(cik, str) or not re.fullmatch(r"\d{10}", cik):
            raise CatalogIntegrityError(f"{ticker}: catalog CIK is invalid")
        if cik in ciks:
            raise CatalogIntegrityError(f"{ticker}: duplicate catalog CIK")
        if batch is not None and (
            not isinstance(batch, int) or isinstance(batch, bool) or batch not in included_batches
        ):
            raise CatalogIntegrityError(f"{ticker}: catalog batch is invalid")
        if availability not in AVAILABILITY_TYPES:
            raise CatalogIntegrityError(f"{ticker}: availability type is invalid")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise CatalogIntegrityError(f"{ticker}: artifact hash is invalid")
        if not isinstance(source_audit, str) or not source_audit:
            raise CatalogIntegrityError(f"{ticker}: source audit is missing")
        tickers.add(ticker)
        ciks.add(cik)
        availability_counts[availability] += 1
        entries.append(
            CatalogEntry(
                ticker=ticker,
                cik=cik,
                batch=batch,
                availability_type=availability,
                artifact_sha256=digest,
                source_audit=source_audit,
            )
        )

    if raw_entries != sorted(raw_entries, key=lambda row: str(row["ticker"])):
        raise CatalogIntegrityError("catalog entries are not sorted by ticker")
    if manifest.get("availability_counts") != availability_counts:
        raise CatalogIntegrityError("catalog availability counts do not match entries")
    if manifest.get("artifact_tree_sha256") != artifact_tree_sha256(raw_entries):
        raise CatalogIntegrityError("catalog artifact tree hash does not match entries")

    artifacts_root = root / "artifacts"
    files = sorted(artifacts_root.glob("*.json")) if artifacts_root.is_dir() else []
    if {path.stem for path in files} != tickers:
        raise CatalogIntegrityError("catalog artifact files do not exactly match the manifest")

    catalog = ValuationCatalog(
        root=root,
        manifest_path=manifest_path,
        manifest_sha256=manifest_digest,
        catalog_version=catalog_version,
        universe_version=universe_version,
        valuation_date=valuation_date,
        included_batches=tuple(included_batches),
        entries=tuple(entries),
        manifest=manifest,
    )
    if verify_artifacts:
        for entry in catalog.entries:
            path = catalog.verify_artifact(entry.ticker)
            artifact = _read_object(path, label=f"{entry.ticker} artifact")
            issuer = artifact.get("issuer")
            top_level_ticker = artifact.get("ticker")
            if (
                (top_level_ticker is not None and top_level_ticker != entry.ticker)
                or not isinstance(issuer, dict)
                or issuer.get("ticker") != entry.ticker
                or str(issuer.get("cik", "")).zfill(10) != entry.cik
            ):
                raise CatalogIntegrityError(f"{entry.ticker}: artifact identity mismatch")
    return catalog


def load_active_catalog(catalogs_root: Path) -> ValuationCatalog:
    catalogs_root = Path(catalogs_root).resolve()
    active_path = catalogs_root / "active.json"
    active = _read_object(active_path, label="active catalog pointer")
    if active.get("schema_version") != ACTIVE_SCHEMA:
        raise CatalogIntegrityError("active catalog pointer schema is unsupported")
    relative = _safe_relative_path(active.get("catalog_path"))
    expected_version = active.get("catalog_version")
    expected_manifest = active.get("manifest_sha256")
    if not isinstance(expected_version, str) or not expected_version:
        raise CatalogIntegrityError("active catalog version is missing")
    if not isinstance(expected_manifest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_manifest):
        raise CatalogIntegrityError("active catalog manifest hash is invalid")
    catalog = load_catalog_version(
        catalogs_root / relative,
        expected_manifest_sha256=expected_manifest,
    )
    if catalog.catalog_version != expected_version:
        raise CatalogIntegrityError("active catalog version does not match its manifest")
    return catalog
