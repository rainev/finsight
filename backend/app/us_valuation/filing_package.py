"""Reproducible local caches for the structural XBRL resources in one SEC filing."""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from pathlib import Path
from typing import Any

from .sec_client import (
    SecClient,
    normalize_accession,
    normalize_cik,
    sec_archive_url,
)


class FilingPackageIncomplete(RuntimeError):
    """Raised when a parser would receive an incomplete structural filing package."""


_LINKBASE_SUFFIXES = ("_pre.xml", "_cal.xml", "_def.xml", "_lab.xml")
_LOCAL_SCHEMA_REFERENCE = re.compile(
    r"(?:href|schemaLocation)\s*=\s*['\"]([^'\"]+\.xsd(?:[?#][^'\"]*)?)['\"]",
    re.IGNORECASE,
)


def cache_structural_filing_package(
    client: SecClient,
    *,
    cik: str,
    accession: str,
    primary_document: str,
    output_dir: Path,
    refresh: bool = False,
) -> Path:
    """Cache the primary document and only the files needed for XBRL structure.

    The resulting directory is self-describing and suitable for offline parser replay.
    """
    normalized_cik = normalize_cik(cik)
    archive_accession = normalize_accession(accession)
    _require_safe_filename(primary_document)
    index = client.filing_index(cik, accession, refresh=refresh)
    filenames = _filing_directory_names(index)
    resources: dict[str, bytes] = {}
    resources[primary_document] = _fetch_structural_resource(
        client,
        cik=cik,
        accession=accession,
        filename=primary_document,
        refresh=refresh,
    )
    referenced_schemas = _local_schema_references(resources[primary_document])
    selected = _select_structural_filenames(
        filenames,
        primary_document,
        referenced_schemas=referenced_schemas,
    )

    for filename in selected:
        if filename == primary_document:
            continue
        resources[filename] = _fetch_structural_resource(
            client,
            cik=cik,
            accession=accession,
            filename=filename,
            refresh=refresh,
        )

    _ensure_referenced_schemas_are_present(referenced_schemas, resources)

    package_dir = output_dir / f"CIK{normalized_cik}-{archive_accession}"
    package_dir.mkdir(parents=True, exist_ok=True)
    cached_at_epoch = time.time()
    manifest_files: list[dict[str, Any]] = []
    for filename in selected:
        raw = resources[filename]
        (package_dir / filename).write_bytes(raw)
        manifest_files.append(
            {
                "filename": filename,
                "source_url": sec_archive_url(
                    normalized_cik, archive_accession, filename
                ),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "cached_at_epoch": cached_at_epoch,
            }
        )
    manifest = {
        "accession": accession,
        "archive_accession": archive_accession,
        "cik": normalized_cik,
        "primary_document": primary_document,
        "cached_at_epoch": cached_at_epoch,
        "files": manifest_files,
    }
    (package_dir / "package-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return package_dir / primary_document


def _fetch_structural_resource(
    client: SecClient,
    *,
    cik: str,
    accession: str,
    filename: str,
    refresh: bool,
) -> bytes:
    try:
        return client.filing_attachment(
            cik,
            accession,
            filename,
            refresh=refresh,
        )
    except (KeyError, OSError, RuntimeError) as exc:
        raise FilingPackageIncomplete(
            f"Structural filing resource is unavailable: {filename}"
        ) from exc


def _filing_directory_names(index: dict[str, Any]) -> list[str]:
    directory = index.get("directory")
    if not isinstance(directory, dict):
        raise FilingPackageIncomplete("SEC filing index has no directory listing")
    items = directory.get("item")
    if not isinstance(items, list):
        raise FilingPackageIncomplete("SEC filing index has no directory items")
    names: list[str] = []
    for item in items:
        name = item.get("name") if isinstance(item, dict) else None
        if isinstance(name, str):
            names.append(name)
    return names


def _select_structural_filenames(
    filenames: list[str],
    primary_document: str,
    *,
    referenced_schemas: set[str],
) -> list[str]:
    selected = {primary_document}
    schema_stems = {
        Path(filename).stem.lower() for filename in referenced_schemas
    }
    for filename in filenames:
        if not _is_safe_basename(filename):
            continue
        lower = filename.lower()
        if lower.endswith(".xsd") or lower.endswith(_LINKBASE_SUFFIXES):
            selected.add(filename)
        elif (
            lower.endswith(".xml")
            and lower != "filingsummary.xml"
            and Path(filename).stem.lower() in schema_stems
        ):
            selected.add(filename)
    return sorted(selected)


def _local_schema_references(primary_bytes: bytes) -> set[str]:
    primary_text = primary_bytes.decode("utf-8", errors="replace")
    references: set[str] = set()
    for reference in _LOCAL_SCHEMA_REFERENCE.findall(primary_text):
        schema_name = html.unescape(reference).split("?")[0].split("#")[0]
        if "://" in schema_name:
            continue
        if not _is_safe_basename(schema_name):
            raise FilingPackageIncomplete(
                f"Locally referenced extension schema is unavailable: {schema_name}"
            )
        references.add(schema_name)
    return references


def _ensure_referenced_schemas_are_present(
    referenced_schemas: set[str], resources: dict[str, bytes]
) -> None:
    for schema_name in referenced_schemas:
        if schema_name not in resources:
            raise FilingPackageIncomplete(
                f"Locally referenced extension schema is unavailable: {schema_name}"
            )


def _require_safe_filename(filename: str) -> None:
    if not _is_safe_basename(filename):
        raise ValueError("primary_document must use a safe file name")


def _is_safe_basename(filename: str) -> bool:
    return (
        bool(filename)
        and filename not in {".", ".."}
        and "/" not in filename
        and "\\" not in filename
        and Path(filename).name == filename
    )
