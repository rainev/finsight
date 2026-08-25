"""Bounded, immutable structural-XBRL filing package acquisition."""

from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import urljoin, urlparse, urlunparse

from .sec_client import (
    SecClient,
    canonicalize_legacy_taxonomy_url,
    normalize_accession,
    normalize_cik,
    sec_archive_url,
    validate_taxonomy_url,
)
from .structural_xbrl import ELIGIBLE_FILING_FORMS, normalize_filing_form


MANIFEST_VERSION = "FINSIGHT-XBRL-PACKAGE-1"
DEFAULT_MAX_RESOURCE_COUNT = 128
DEFAULT_MAX_FILE_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 128 * 1024 * 1024
DEFAULT_MAX_DEPENDENCY_DEPTH = 32


class FilingPackageIncomplete(RuntimeError):
    """Raised when a complete governed DTS cannot be published."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class _Resource:
    source_url: str
    local_path: str
    raw: bytes
    depth: int
    retrieval_url: str | None = None
    archive_member: str | None = None


_LINKBASE_SUFFIXES = ("_pre.xml", "_cal.xml", "_def.xml", "_lab.xml")
_REFERENCE_ATTRIBUTE = re.compile(
    r"(?:xlink:)?href\s*=\s*['\"]([^'\"]+)['\"]|"
    r"schemaLocation\s*=\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
_TARGET_NAMESPACE = re.compile(
    rb"targetNamespace\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE
)
_TAXONOMY_VERSION = re.compile(
    r"(?<!\d)(20\d{2}(?:-\d{2}-\d{2})?)(?!\d)"
)


def cache_structural_filing_package(
    client: SecClient,
    *,
    cik: str,
    accession: str,
    primary_document: str,
    output_dir: Path,
    form: str = "10-K",
    refresh: bool = False,
    max_resource_count: int = DEFAULT_MAX_RESOURCE_COUNT,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_dependency_depth: int = DEFAULT_MAX_DEPENDENCY_DEPTH,
    filed_date: str | None = None,
    report_date: str | None = None,
    relevant_attachments: Mapping[str, str] | None = None,
) -> Path:
    """Acquire a complete DTS plus governed relevant attachments immutably."""

    normalized_form = normalize_filing_form(form)
    if normalized_form not in ELIGIBLE_FILING_FORMS:
        raise FilingPackageIncomplete(
            "INELIGIBLE_FILING_FORM", f"unsupported filing form {normalized_form!r}"
        )
    for value, name in (
        (max_resource_count, "max_resource_count"),
        (max_file_bytes, "max_file_bytes"),
        (max_total_bytes, "max_total_bytes"),
        (max_dependency_depth, "max_dependency_depth"),
    ):
        if value <= 0:
            raise ValueError(f"{name} must be positive")

    normalized_cik = normalize_cik(cik)
    archive_accession = normalize_accession(accession)
    _require_safe_filename(primary_document)
    for value, name in ((filed_date, "filed_date"), (report_date, "report_date")):
        if value is not None:
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be an ISO date") from exc
    attachments_governed = relevant_attachments is not None
    attachment_roles = dict(relevant_attachments or {})
    for filename, role in attachment_roles.items():
        _require_safe_filename(filename)
        if not isinstance(role, str) or not role.strip():
            raise ValueError("relevant attachment roles must be nonempty text")
    index = client.filing_index(cik, accession, refresh=refresh)
    filenames = _filing_directory_names(index)
    filing_names = {name for name in filenames if _is_safe_basename(name)}
    zip_prefetched: dict[str, tuple[bytes, str, str]] = {}
    xbrl_zip_names = sorted(
        name for name in filing_names if name.casefold().endswith("-xbrl.zip")
    )
    if len(xbrl_zip_names) > 1:
        raise FilingPackageIncomplete(
            "XBRL_PACKAGE_INCOMPLETE", "multiple filing XBRL archives are ambiguous"
        )
    if xbrl_zip_names:
        zip_name = xbrl_zip_names[0]
        zip_url = sec_archive_url(normalized_cik, archive_accession, zip_name)
        zip_raw = _fetch_filing_resource(
            client,
            cik=cik,
            accession=accession,
            filename=zip_name,
            refresh=refresh,
            max_file_bytes=max_file_bytes,
        )
        try:
            with zipfile.ZipFile(io.BytesIO(zip_raw)) as archive:
                members = [item for item in archive.infolist() if not item.is_dir()]
                if len(members) > max_resource_count:
                    raise FilingPackageIncomplete(
                        "XBRL_RESOURCE_COUNT_LIMIT", zip_url
                    )
                if sum(item.file_size for item in members) > max_total_bytes:
                    raise FilingPackageIncomplete("XBRL_PACKAGE_SIZE_LIMIT", zip_url)
                for member in members:
                    basename = Path(member.filename).name
                    if not _is_safe_basename(basename):
                        raise FilingPackageIncomplete(
                            "XBRL_PACKAGE_INCOMPLETE",
                            f"unsafe XBRL archive member: {member.filename}",
                        )
                    if member.file_size > max_file_bytes:
                        raise FilingPackageIncomplete(
                            "XBRL_FILE_SIZE_LIMIT", f"{zip_url}#{member.filename}"
                        )
                    logical_url = sec_archive_url(
                        normalized_cik, archive_accession, basename
                    )
                    if logical_url in zip_prefetched:
                        raise FilingPackageIncomplete(
                            "XBRL_PACKAGE_INCOMPLETE",
                            f"duplicate XBRL archive member: {basename}",
                        )
                    zip_prefetched[logical_url] = (
                        archive.read(member),
                        zip_url,
                        member.filename,
                    )
                    filing_names.add(basename)
        except (OSError, zipfile.BadZipFile) as exc:
            raise FilingPackageIncomplete(
                "XBRL_PACKAGE_INCOMPLETE", f"invalid filing XBRL archive: {zip_name}"
            ) from exc
    primary_url = sec_archive_url(normalized_cik, archive_accession, primary_document)
    primary_raw = _fetch_filing_resource(
        client,
        cik=cik,
        accession=accession,
        filename=primary_document,
        refresh=refresh,
        max_file_bytes=max_file_bytes,
    )
    primary_schema_names = {
        Path(urlparse(url).path).name
        for url in _dependency_urls(primary_raw, primary_url)
        if urlparse(url).path.lower().endswith(".xsd")
        and _is_same_filing_url(url, normalized_cik, archive_accession)
    }

    initial_names = _select_structural_filenames(
        filenames,
        primary_document,
        referenced_schemas=primary_schema_names,
        additional_filenames=frozenset(attachment_roles),
    )
    pending: list[tuple[str, str, int]] = [
        (
            sec_archive_url(normalized_cik, archive_accession, filename),
            filename,
            0,
        )
        for filename in initial_names
    ]
    resources: dict[str, _Resource] = {}
    prefetched = {primary_url: primary_raw}
    total_bytes = 0

    while pending:
        source_url, local_path, depth = pending.pop(0)
        source_url = _without_fragment(source_url)
        if source_url in resources:
            continue
        if depth > max_dependency_depth:
            raise FilingPackageIncomplete(
                "XBRL_DEPENDENCY_DEPTH_LIMIT", source_url
            )
        if len(resources) >= max_resource_count:
            raise FilingPackageIncomplete("XBRL_RESOURCE_COUNT_LIMIT", source_url)

        if _is_same_filing_url(source_url, normalized_cik, archive_accession):
            filename = Path(urlparse(source_url).path).name
            if filename not in filing_names and filename != primary_document:
                raise FilingPackageIncomplete(
                    "XBRL_PACKAGE_INCOMPLETE",
                    f"locally referenced resource is unavailable: {filename}",
                )
            raw = prefetched.pop(source_url, None)
            retrieval_url = source_url
            archive_member = None
            zipped = zip_prefetched.get(source_url)
            if raw is None and zipped is not None:
                raw, retrieval_url, archive_member = zipped
            elif raw is None:
                raw = _fetch_filing_resource(
                    client,
                    cik=cik,
                    accession=accession,
                    filename=filename,
                    refresh=refresh,
                    max_file_bytes=max_file_bytes,
                )
        else:
            try:
                validate_taxonomy_url(source_url)
            except ValueError as exc:
                raise FilingPackageIncomplete("XBRL_URL_NOT_ALLOWED", source_url) from exc
            raw = _fetch_taxonomy_resource(
                client,
                source_url,
                refresh=refresh,
                max_file_bytes=max_file_bytes,
            )
            retrieval_url = source_url
            archive_member = None
        if len(raw) > max_file_bytes:
            raise FilingPackageIncomplete("XBRL_FILE_SIZE_LIMIT", source_url)
        total_bytes += len(raw)
        if total_bytes > max_total_bytes:
            raise FilingPackageIncomplete("XBRL_PACKAGE_SIZE_LIMIT", source_url)
        resource = _Resource(
            source_url,
            local_path,
            raw,
            depth,
            retrieval_url=retrieval_url,
            archive_member=archive_member,
        )
        resources[source_url] = resource

        for dependency_url in _dependency_urls(raw, source_url):
            if dependency_url in resources or any(item[0] == dependency_url for item in pending):
                continue
            dependency_path = _local_path_for_url(
                dependency_url, normalized_cik, archive_accession
            )
            pending.append((dependency_url, dependency_path, depth + 1))

    if primary_url not in resources:
        raise FilingPackageIncomplete("XBRL_PACKAGE_INCOMPLETE", primary_document)
    missing_attachments = sorted(set(attachment_roles) - {item.local_path for item in resources.values()})
    if missing_attachments:
        raise FilingPackageIncomplete(
            "RELEVANT_ATTACHMENT_MISSING", ", ".join(missing_attachments)
        )

    cached_at_epoch = time.time()
    manifest_files = [
        {
            "source_url": resource.retrieval_url or resource.source_url,
            "logical_url": resource.source_url,
            "local_path": resource.local_path,
            "sha256": hashlib.sha256(resource.raw).hexdigest(),
            "byte_count": len(resource.raw),
            "retrieved_at_epoch": cached_at_epoch,
            "dependency_depth": resource.depth,
            "taxonomy_namespace": _taxonomy_namespace(resource.raw),
            "taxonomy_version": _taxonomy_version(
                resource.source_url, resource.raw
            ),
            **(
                {"archive_member": resource.archive_member}
                if resource.archive_member is not None
                else {}
            ),
        }
        for resource in sorted(resources.values(), key=lambda item: item.source_url)
    ]
    generation = _generation_digest(
        normalized_cik,
        archive_accession,
        normalized_form,
        primary_url,
        manifest_files,
        filed_date=filed_date,
        report_date=report_date,
        relevant_attachments=(attachment_roles if attachments_governed else None),
    )
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "generation": generation,
        "accession": accession,
        "archive_accession": archive_accession,
        "cik": normalized_cik,
        "form": normalized_form,
        "primary_document": primary_document,
        "primary_source_url": primary_url,
        "entrypoint_local_path": resources[primary_url].local_path,
        "cached_at_epoch": cached_at_epoch,
        "resource_count": len(resources),
        "total_bytes": total_bytes,
        "limits": {
            "max_resource_count": max_resource_count,
            "max_file_bytes": max_file_bytes,
            "max_total_bytes": max_total_bytes,
            "max_dependency_depth": max_dependency_depth,
        },
        "files": manifest_files,
    }
    if filed_date is not None:
        manifest["filed_date"] = filed_date
    if report_date is not None:
        manifest["report_date"] = report_date
    if attachments_governed:
        manifest["relevant_attachments"] = [
            {"filename": filename, "role": attachment_roles[filename]}
            for filename in sorted(attachment_roles)
        ]
    package_root = Path(output_dir) / f"CIK{normalized_cik}-{archive_accession}"
    package_root.mkdir(parents=True, exist_ok=True)
    generation_dir = package_root / generation
    if generation_dir.exists():
        _verify_existing_generation(generation_dir, manifest)
        return generation_dir / resources[primary_url].local_path

    temp_path = Path(tempfile.mkdtemp(prefix=".building-", dir=package_root))
    try:
        for resource in resources.values():
            destination = temp_path / resource.local_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(resource.raw)
        (temp_path / "package-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _verify_existing_generation(temp_path, manifest)
        try:
            os.replace(temp_path, generation_dir)
        except FileExistsError:
            _verify_existing_generation(generation_dir, manifest)
        return generation_dir / resources[primary_url].local_path
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path)


def _fetch_filing_resource(
    client: SecClient,
    *,
    cik: str,
    accession: str,
    filename: str,
    refresh: bool,
    max_file_bytes: int,
) -> bytes:
    try:
        return client.filing_attachment(
            cik,
            accession,
            filename,
            refresh=refresh,
            max_bytes=max_file_bytes,
        )
    except (KeyError, OSError, RuntimeError) as exc:
        raise FilingPackageIncomplete(
            "XBRL_PACKAGE_INCOMPLETE", f"resource unavailable: {filename}"
        ) from exc


def _fetch_taxonomy_resource(
    client: SecClient,
    url: str,
    *,
    refresh: bool,
    max_file_bytes: int,
) -> bytes:
    try:
        return client.taxonomy_resource(
            url, refresh=refresh, max_bytes=max_file_bytes
        )
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        raise FilingPackageIncomplete(
            "XBRL_PACKAGE_INCOMPLETE", f"taxonomy resource unavailable: {url}"
        ) from exc


def _dependency_urls(raw: bytes, source_url: str) -> tuple[str, ...]:
    text = raw.decode("utf-8", errors="replace")
    dependencies: set[str] = set()
    for match in _REFERENCE_ATTRIBUTE.finditer(text):
        value = html.unescape(match.group(1) or match.group(2) or "").strip()
        tokens = value.split() if match.group(2) else [value]
        for token in tokens:
            candidate = canonicalize_legacy_taxonomy_url(
                _without_fragment(urljoin(source_url, token))
            )
            path = urlparse(candidate).path.lower()
            if path.endswith((".xsd", ".xml")):
                dependencies.add(candidate)
    return tuple(sorted(dependencies))


def _without_fragment(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def _is_same_filing_url(url: str, cik: str, accession: str) -> bool:
    prefix = sec_archive_url(cik, accession, "placeholder").rsplit("/", 1)[0] + "/"
    return url.startswith(prefix)


def _local_path_for_url(url: str, cik: str, accession: str) -> str:
    parsed = urlparse(url)
    basename = Path(parsed.path).name
    if _is_same_filing_url(url, cik, accession) and _is_safe_basename(basename):
        return basename
    safe_basename = basename if _is_safe_basename(basename) else "resource.xml"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return PurePosixPath("taxonomy", f"{digest}-{safe_basename}").as_posix()


def _generation_digest(
    cik: str,
    accession: str,
    form: str,
    primary_url: str,
    files: list[dict[str, Any]],
    *,
    filed_date: str | None = None,
    report_date: str | None = None,
    relevant_attachments: Mapping[str, str] | None = None,
) -> str:
    identity = {
        "manifest_version": MANIFEST_VERSION,
        "cik": cik,
        "accession": accession,
        "form": form,
        "primary_source_url": primary_url,
        "files": [
            {
                "source_url": item["source_url"],
                "logical_url": item.get("logical_url", item["source_url"]),
                "local_path": item["local_path"],
                "sha256": item["sha256"],
                "byte_count": item["byte_count"],
                "archive_member": item.get("archive_member"),
            }
            for item in files
        ],
    }
    if filed_date is not None:
        identity["filed_date"] = filed_date
    if report_date is not None:
        identity["report_date"] = report_date
    if relevant_attachments is not None:
        identity["relevant_attachments"] = [
            {"filename": filename, "role": relevant_attachments[filename]}
            for filename in sorted(relevant_attachments)
        ]
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _taxonomy_namespace(raw: bytes) -> str:
    match = _TARGET_NAMESPACE.search(raw)
    if match is None:
        return ""
    return html.unescape(match.group(1).decode("utf-8", errors="replace")).strip()


def _taxonomy_version(source_url: str, raw: bytes) -> str:
    namespace = _taxonomy_namespace(raw)
    candidates = _TAXONOMY_VERSION.findall(f"{source_url} {namespace}")
    return candidates[-1] if candidates else "unknown"


def _verify_existing_generation(path: Path, expected: dict[str, Any]) -> None:
    try:
        manifest = json.loads((path / "package-manifest.json").read_text(encoding="utf-8"))
        if manifest.get("generation") != expected["generation"]:
            raise ValueError("generation mismatch")
        for key in (
            "manifest_version",
            "accession",
            "archive_accession",
            "cik",
            "form",
            "primary_document",
            "primary_source_url",
            "entrypoint_local_path",
            "filed_date",
            "report_date",
            "relevant_attachments",
        ):
            if key in expected and manifest.get(key) != expected[key]:
                raise ValueError(f"manifest {key} mismatch")
        expected_by_path = {item["local_path"]: item for item in expected["files"]}
        actual_by_path = {item["local_path"]: item for item in manifest["files"]}
        if {
            key: (
                value["source_url"],
                value.get("logical_url", value["source_url"]),
                value.get("archive_member"),
                value["sha256"],
                value["byte_count"],
            )
            for key, value in actual_by_path.items()
        } != {
            key: (
                value["source_url"],
                value.get("logical_url", value["source_url"]),
                value.get("archive_member"),
                value["sha256"],
                value["byte_count"],
            )
            for key, value in expected_by_path.items()
        }:
            raise ValueError("manifest content mismatch")
        for local_path, item in actual_by_path.items():
            candidate = (path / local_path).resolve()
            if not candidate.is_relative_to(path.resolve()):
                raise ValueError("unsafe local path")
            raw = candidate.read_bytes()
            if len(raw) != item["byte_count"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("resource hash mismatch")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FilingPackageIncomplete(
            "XBRL_IMMUTABLE_CONFLICT", f"invalid generation at {path}"
        ) from exc


def _filing_directory_names(index: dict[str, Any]) -> list[str]:
    directory = index.get("directory")
    if not isinstance(directory, dict):
        raise FilingPackageIncomplete("XBRL_PACKAGE_INCOMPLETE", "no directory listing")
    items = directory.get("item")
    if not isinstance(items, list):
        raise FilingPackageIncomplete("XBRL_PACKAGE_INCOMPLETE", "no directory items")
    return [
        item["name"]
        for item in items
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    ]


def _select_structural_filenames(
    filenames: list[str],
    primary_document: str,
    *,
    referenced_schemas: set[str],
    additional_filenames: frozenset[str] = frozenset(),
) -> list[str]:
    selected = {primary_document}
    selected.update(additional_filenames)
    schema_stems = {Path(filename).stem.lower() for filename in referenced_schemas}
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
