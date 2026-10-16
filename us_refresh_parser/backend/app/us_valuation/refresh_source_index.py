"""Immutable, reusable index of cached U.S. filing sources.

The source index is deliberately a catalogue, not a selector.  A packet that
contains several eligible filings contributes one entry per filing and lookup
returns every matching entry.  Consumers must choose a filing according to
their existing cutoff and policy rules; this module only makes the candidates
cheap to find and proves that the cached bytes have not changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import os
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence
import time

from .catalog import canonical_json_bytes, sha256_bytes
from .sec_client import normalize_cik


SOURCE_INDEX_SCHEMA = "FINSIGHT-US-REFRESH-SOURCE-INDEX-3"
_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SourceIndexError(ValueError):
    """Base class for source-index integrity and lookup errors."""


class SourceIndexIntegrityError(SourceIndexError):
    """The index or a selected source no longer proves its recorded bytes."""


class SourceIndexIdentityError(SourceIndexIntegrityError):
    """A source's current issuer identity does not match the index entry."""


class SourceIndexAmbiguityError(SourceIndexError):
    """Reserved for callers that explicitly require one unambiguous result."""


def _json(path: Path, label: str) -> dict[str, Any]:
    import json

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceIndexIntegrityError(f"{label} is missing or invalid") from exc
    if not isinstance(value, dict):
        raise SourceIndexIntegrityError(f"{label} must be a JSON object")
    return value


def _safe_relative(path: Path, root: Path) -> str:
    """Return a stable POSIX path, rejecting symlink/path escapes."""

    root_real = root.resolve()
    try:
        real = path.resolve(strict=True)
    except OSError as exc:
        raise SourceIndexIntegrityError(f"source path is unavailable: {path}") from exc
    try:
        relative = real.relative_to(root_real)
    except ValueError as exc:
        raise SourceIndexIntegrityError(f"source path escapes allowed output root: {path}") from exc
    pure = PurePosixPath(relative.as_posix())
    if not pure.parts or pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise SourceIndexIntegrityError(f"unsafe source path: {path}")
    return pure.as_posix()


def _under_root(path: Path, root: Path) -> Path:
    """Resolve an indexed relative path and prove it remains under root."""

    if path.is_absolute():
        candidate = path
    else:
        candidate = root / path
    _safe_relative(candidate, root)
    return candidate


def _validate_destination(path: Path, root: Path) -> None:
    """Validate an output destination before it exists (or after, if it does)."""

    if path.exists() or path.is_symlink():
        _safe_relative(path, root)
        return
    parent = path.parent.resolve()
    try:
        parent.relative_to(root.resolve())
    except ValueError as exc:
        raise SourceIndexIntegrityError(f"index destination escapes allowed output root: {path}") from exc
    if not path.name or path.name in {".", ".."}:
        raise SourceIndexIntegrityError(f"unsafe index destination: {path}")


def _hash_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise SourceIndexIntegrityError(f"cannot read source bytes: {path}") from exc


def _normal_cik(value: Any) -> str:
    try:
        return normalize_cik(str(value))
    except (TypeError, ValueError) as exc:
        raise SourceIndexIdentityError(f"invalid CIK: {value!r}") from exc


def _date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _accession(value: Any) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _filing_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = {
        "accession": _accession(row.get("accession", row.get("accessionNumber"))),
        "form": row.get("form"),
        "report_date": _date(row.get("report_date", row.get("reportDate", row.get("period_end")))),
        "filed_date": _date(row.get("filed", row.get("filed_date", row.get("filingDate")))),
    }
    errors = []
    for key in ("report_date", "filed_date"):
        raw = row.get(key)
        if raw is None:
            raw = row.get("reportDate" if key == "report_date" else "filed")
        if raw is None:
            raw = row.get("filingDate" if key == "filed_date" else "reportDate")
        if raw is None:
            raw = row.get("period_end" if key == "report_date" else "filed_date")
        if isinstance(raw, str) and raw and metadata[key] is None:
            errors.append(f"{key} is not a valid ISO date: {raw!r}")
    if errors:
        metadata["_errors"] = errors
    return metadata


def _issuer_from_packet(packet_dir: Path, manifest: Mapping[str, Any], submissions: Mapping[str, Any], facts: Mapping[str, Any]) -> tuple[str, str, list[str]]:
    issuer = manifest.get("issuer") if isinstance(manifest.get("issuer"), Mapping) else {}
    ticker = str(issuer.get("ticker") or packet_dir.name).upper()
    errors: list[str] = []
    if not _TICKER.fullmatch(ticker):
        errors.append(f"invalid ticker: {ticker!r}")
    candidates = [issuer.get("cik"), submissions.get("cik"), facts.get("cik")]
    present = [str(value) for value in candidates if value not in (None, "")]
    cik = ""
    if present:
        try:
            normalized = [_normal_cik(value) for value in present]
            cik = normalized[0]
            if any(value != cik for value in normalized[1:]):
                errors.append("packet CIK identity mismatch across issuer/submissions/companyfacts")
        except SourceIndexIdentityError as exc:
            errors.append(str(exc))
    else:
        errors.append("packet CIK is missing")
    issuer_tickers = submissions.get("tickers")
    if isinstance(issuer_tickers, Sequence) and not isinstance(issuer_tickers, (str, bytes)):
        normalized_tickers = {str(value).upper() for value in issuer_tickers}
        if normalized_tickers and ticker not in normalized_tickers:
            errors.append("packet ticker is not present in submissions tickers")
    return ticker, cik, errors


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    relative = _safe_relative(path, root)
    digest = _hash_file(path)
    return {"path": relative, "sha256": digest, "byte_count": path.stat().st_size}


def _manifest_hashes(manifest: Mapping[str, Any], files: Mapping[str, Any], packet_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, metadata in sorted(files.items()):
        path = packet_dir / name
        if path.is_file():
            hashes[name] = _hash_file(path)
        if isinstance(metadata, Mapping) and isinstance(metadata.get("sha256"), str):
            hashes[f"{name}:declared"] = metadata["sha256"]
    return hashes


def _packet_entries(packet_dir: Path, root: Path) -> list[dict[str, Any]]:
    manifest_path = packet_dir / "source-manifest.json"
    files = {
        path.name: path for path in sorted(packet_dir.iterdir(), key=lambda value: value.name)
        if path.is_file()
    }
    base: dict[str, Any] = {
        "kind": "packet",
        "path": _safe_relative(packet_dir, root),
        "files": {},
        "raw_hashes": {},
        "package_hashes": {},
        "parser_definition_sha256": None,
        "content_sha256": None,
        "content_hashes": {},
        "accession": None,
        "form": None,
        "report_date": None,
        "filed_date": None,
        "validation_errors": [], "filings":[], "filing":None,
    }
    try:
        raw={name:path.read_bytes() for name,path in files.items()}
        base['files']={name:{'path':_safe_relative(files[name],root),'sha256':sha256_bytes(value),'byte_count':len(value)} for name,value in raw.items()}
        manifest=json.loads(raw['source-manifest.json']) if 'source-manifest.json' in raw else {}
        submissions=json.loads(raw['submissions.json']);facts=json.loads(raw['companyfacts.json'])
        if not all(isinstance(value,dict) for value in (manifest,submissions,facts)):
            raise SourceIndexIntegrityError('packet JSON inputs must contain objects')
        ticker, cik, errors = _issuer_from_packet(packet_dir, manifest, submissions, facts)
        base.update(ticker=ticker, cik=cik, validation_errors=errors)
        declared_files=manifest.get('files',{}) if isinstance(manifest.get('files'),Mapping) else {}
        base["raw_hashes"]={name:base['files'][name]['sha256'] for name in declared_files if name in base['files']}
        base['declared_raw_hashes']={name:record.get('sha256') for name,record in declared_files.items() if isinstance(record,Mapping) and isinstance(record.get('sha256'),str)}
        declared = manifest.get("packet_payload_sha256")
        base["content_hashes"] = {
            name: record["sha256"] for name, record in base["files"].items()
            if name in {"submissions.json", "companyfacts.json"}
        }
        if isinstance(declared, Mapping):
            base["declared_content_hashes"] = dict(declared)
        candidates = manifest.get("eligible_filings")
        if not isinstance(candidates, list):
            candidates = []
        for row in candidates:
            filing=_filing_metadata(row) if isinstance(row,Mapping) else {'accession':None,'form':None,'report_date':None,'filed_date':None,'_errors':['eligible filing is not an object']}
            filing_errors=filing.pop('_errors',[])
            if filing['accession'] is None: filing_errors.append('eligible filing has no accession')
            if filing_errors:
                filing['validation_errors']=filing_errors
                base['validation_errors'].extend(f"eligible filing {filing.get('accession') or 'unknown'}: {error}" for error in filing_errors)
            base['filings'].append(filing)
        base['filings']=sorted(base['filings'],key=lambda row:(str(row.get('accession')),str(row.get('form')),str(row.get('report_date')),str(row.get('filed_date'))))
        base['content_sha256']=sha256_bytes(canonical_json_bytes(base['content_hashes']))
        base['entry_id']=sha256_bytes(canonical_json_bytes({key:base.get(key) for key in ('kind','path','ticker','cik','filings','content_sha256')}))
        return [base]
    except (OSError,UnicodeDecodeError,json.JSONDecodeError,SourceIndexIntegrityError) as exc:
        base["validation_errors"] = [str(exc)];base['ticker']=packet_dir.name if _TICKER.fullmatch(packet_dir.name) else None;base['cik']=''
        base["entry_id"] = sha256_bytes(canonical_json_bytes({"kind": "packet", "path": base["path"]}))
        return [base]


def _structural_entry(path: Path, root: Path) -> dict[str, Any]:
    structural_dir = path.parent
    package_path = structural_dir / "package-manifest.json"
    receipt_path = structural_dir / "source-receipt.json"
    files = {name: candidate for name, candidate in (("structural-filing.json", path), ("package-manifest.json", package_path), ("source-receipt.json", receipt_path)) if candidate.is_file()}
    entry: dict[str, Any] = {
        "kind": "structural",
        "path": _safe_relative(path, root),
        "files": {name: _file_record(candidate, root) for name, candidate in sorted(files.items())},
        "raw_hashes": {},
        "package_hashes": {},
        "parser_definition_sha256": None,
        "content_sha256": _hash_file(path),
        "content_hashes": {"structural-filing.json": _hash_file(path)},
        "accession": None,
        "form": None,
        "report_date": None,
        "filed_date": None,
        "validation_errors": [],
        "filing": None,
        "entry_id": None,
    }
    try:
        structural = _json(path, "structural-filing.json")
        package = _json(package_path, "package-manifest.json") if package_path.is_file() else {}
        receipt = _json(receipt_path, "source-receipt.json") if receipt_path.is_file() else {}
        metadata = _filing_metadata({
            "accession": structural.get("source_accession") or package.get("accession") or (receipt.get("filing") or {}).get("accession"),
            "form": structural.get("form") or package.get("form") or (receipt.get("filing") or {}).get("form"),
            "report_date": structural.get("report_date") or package.get("report_date") or (receipt.get("filing") or {}).get("report_date"),
            "filed_date": structural.get("filed_date") or package.get("filed_date") or (receipt.get("filing") or {}).get("filed_date"),
        })
        entry["validation_errors"].extend(metadata.pop("_errors", []))
        identifiers = {str(row.get("entity_identifier")) for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("entity_identifier") is not None}
        receipt_cik = receipt.get("cik")
        package_cik = package.get("cik")
        ciks = [_normal_cik(value) for value in (*identifiers, receipt_cik, package_cik) if value not in (None, "")]
        cik = ciks[0] if ciks else ""
        if any(value != cik for value in ciks[1:]):
            entry["validation_errors"].append("structural CIK identity mismatch across facts/receipt/package")
        ticker = str(receipt.get("ticker") or structural_dir.name).upper()
        if not _TICKER.fullmatch(ticker):
            # Verification/reparse directories need not be ticker-named. The
            # unique fact CIK remains authoritative and callers route it
            # through the frozen registry rather than trusting a folder name.
            ticker = None
        expected_accession = package.get("accession") or (receipt.get("filing") or {}).get("accession")
        if expected_accession and metadata["accession"] and expected_accession != metadata["accession"]:
            entry["validation_errors"].append("structural accession identity mismatch")
        fact_rows=[row for row in structural.get('facts',[]) if isinstance(row,Mapping)]
        fact_identity_complete=bool(fact_rows) and all(str(row.get('entity_identifier','')).zfill(10)==cik for row in fact_rows)
        entry.update(ticker=ticker, cik=cik, filing=metadata, fact_identity_complete=fact_identity_complete, **metadata)
        entry["package_hashes"] = {
            "package-manifest.json": entry["files"].get("package-manifest.json", {}).get("sha256")
        }
        package_files = package.get("files")
        if isinstance(package_files, list):
            # Keep package resource hashes from the immutable package manifest
            # without eagerly rereading a potentially multi-gigabyte cache.
            # The structural entrypoint and package manifest are rehashed on
            # every selected read; consumers that need a resource can use the
            # declared local_path/sha256 pair for a targeted read.
            for resource in package_files:
                if not isinstance(resource, Mapping) or not isinstance(resource.get("local_path"), str):
                    entry["validation_errors"].append("package manifest contains an invalid file record")
                    continue
                local_path = resource["local_path"]
                declared_hash = resource.get("sha256")
                if isinstance(declared_hash, str):
                    entry["package_hashes"][local_path] = declared_hash
        entry["parser_definition_sha256"] = receipt.get("parser_definition_sha256")
        package_generation = package.get("package_generation")
        if package_generation:
            entry["package_generation"] = package_generation
    except (SourceIndexIntegrityError, ValueError, TypeError) as exc:
        entry["validation_errors"].append(str(exc))
    identity = {key: entry.get(key) for key in ("kind", "path", "ticker", "cik", "filing", "content_sha256")}
    entry["entry_id"] = sha256_bytes(canonical_json_bytes(identity))
    return entry


def _candidate_dirs(root: Path) -> tuple[list[Path], list[Path]]:
    packets: set[Path] = set()
    structural: set[Path] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "submissions.json" and (path.parent / "companyfacts.json").is_file():
            packets.add(path.parent)
        elif path.name == "structural-filing.json":
            structural.add(path)
    return sorted(packets, key=lambda value: value.as_posix()), sorted(structural, key=lambda value: value.as_posix())


def _input_fingerprint(entries: Iterable[Mapping[str, Any]]) -> str:
    descriptors = []
    for entry in entries:
        descriptors.append({
            "kind": entry.get("kind"), "path": entry.get("path"), "files": entry.get("files"),
            "raw_hashes": entry.get("raw_hashes"), "package_hashes": entry.get("package_hashes"),
            "content_hashes": entry.get("content_hashes"), "declared_content_hashes": entry.get("declared_content_hashes"),
            "parser_definition_sha256": entry.get("parser_definition_sha256"), "content_sha256": entry.get("content_sha256"),
            "ticker": entry.get("ticker"), "cik": entry.get("cik"), "filing": entry.get("filing"), "filings":entry.get('filings'),
            "fact_identity_complete":entry.get('fact_identity_complete'),
        })
    return sha256_bytes(canonical_json_bytes(sorted(descriptors, key=lambda value: (value.get("kind") or "", value.get("path") or "", canonical_json_bytes(value)))))


def _write_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise SourceIndexIntegrityError(f"refusing to overwrite immutable source index: {path}")
        return
    fd, name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _without_index_digest(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "index_sha256"}


def _index_digest_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Select the deterministic, source-bound portion of an index payload."""

    return {
        key: value for key, value in payload.items()
        if key not in {"index_sha256", "created_at_epoch", "created_at_utc", "measurement"}
    }


def build_source_index(output_root: Path, index_path: Path | None = None, *, created_at_epoch: float | None = None) -> dict[str, Any]:
    """Build and optionally persist an index by explicitly scanning ``output_root``."""

    started = time.perf_counter()
    root = Path(output_root).resolve()
    if not root.is_dir():
        raise SourceIndexError(f"allowed output root is not a directory: {root}")
    packets, structural = _candidate_dirs(root)
    entries: list[dict[str, Any]] = []
    for packet in packets:
        entries.extend(_packet_entries(packet, root))
    for path in structural:
        entries.append(_structural_entry(path, root))
    entries.sort(key=lambda entry: (str(entry.get("kind")), str(entry.get("path")), str(entry.get("entry_id"))))
    fingerprint = _input_fingerprint(entries)
    finished = time.perf_counter()
    created = float(created_at_epoch if created_at_epoch is not None else time.time())
    payload: dict[str, Any] = {
        "schema_version": SOURCE_INDEX_SCHEMA,
        "allowed_output_root": str(root),
        "input_fingerprint_sha256": fingerprint,
        "created_at_epoch": created,
        "created_at_utc": datetime.fromtimestamp(created, tz=timezone.utc).isoformat(),
        "measurement": {"scan_elapsed_seconds": finished - started, "candidate_packet_dirs": len(packets), "candidate_structural_files": len(structural), "entry_count": len(entries)},
        "entries": entries,
    }
    payload["index_sha256"] = sha256_bytes(canonical_json_bytes(_index_digest_payload(payload)))
    if index_path is not None:
        target = Path(index_path).resolve()
        _validate_destination(target, root)
        # An immutable index is safely reusable.  Preserve its original
        # creation/measurement metadata when the exact indexed inputs are
        # already present, instead of failing a normal second build merely
        # because wall-clock timing differs.
        if target.is_file():
            existing = _json(target, "source index")
            if existing.get("input_fingerprint_sha256") == fingerprint:
                return existing
        _write_immutable(target, canonical_json_bytes(payload))
    return payload


def persist_source_index(payload: Mapping[str, Any], index_path: Path, *, output_root: Path) -> Path:
    """Persist a previously built index at a content-addressed immutable path."""

    root = Path(output_root).resolve()
    target = Path(index_path).resolve()
    _validate_destination(target, root)
    if payload.get("schema_version") != SOURCE_INDEX_SCHEMA:
        raise SourceIndexIntegrityError("unsupported source index schema")
    if Path(str(payload.get("allowed_output_root", ""))).resolve() != root:
        raise SourceIndexIntegrityError("source index output root mismatch")
    expected = payload.get("index_sha256")
    actual = sha256_bytes(canonical_json_bytes(_index_digest_payload(payload)))
    if expected != actual:
        raise SourceIndexIntegrityError("source index hash mismatch")
    _write_immutable(target, canonical_json_bytes(payload))
    return target


@dataclass(frozen=True)
class SourceIndex:
    """Loaded index with lookup and byte-drift checked reads."""

    path: Path
    allowed_output_root: Path
    payload: Mapping[str, Any]

    @property
    def entries(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self.payload.get("entries", ()))

    def lookup(self, *, ticker: str | None = None, cik: str | None = None, accession: str | None = None, kind: str | None = None) -> tuple[Mapping[str, Any], ...]:
        wanted_ticker = ticker.upper() if ticker else None
        wanted_cik = _normal_cik(cik) if cik else None
        return tuple(entry for entry in self.entries if
                     (wanted_ticker is None or entry.get("ticker") == wanted_ticker) and
                     (wanted_cik is None or entry.get("cik") == wanted_cik) and
                     (accession is None or (entry.get("filing") or {}).get("accession") == accession or any(row.get('accession')==accession for row in entry.get('filings',[]) if isinstance(row,Mapping))) and
                     (kind is None or entry.get("kind") == kind))

    def read(self, entry: Mapping[str, Any] | str) -> dict[str, Any]:
        selected = next((item for item in self.entries if item.get("entry_id") == entry or item.get("path") == entry), None) if isinstance(entry, str) else entry
        if selected is None:
            raise KeyError(entry)
        errors = list(selected.get("validation_errors") or [])
        if errors:
            raise SourceIndexIntegrityError(f"indexed source is invalid: {'; '.join(errors)}")
        source_path = _under_root(Path(str(selected["path"])), self.allowed_output_root)
        files = selected.get("files")
        if not isinstance(files, Mapping):
            raise SourceIndexIntegrityError("indexed source has no file records")
        for name, record in files.items():
            if not isinstance(record, Mapping) or not _SHA256.fullmatch(str(record.get("sha256", ""))):
                raise SourceIndexIntegrityError(f"invalid hash record for {name}")
            path = _under_root(Path(str(record.get("path"))), self.allowed_output_root)
            actual = _hash_file(path)
            if actual != record["sha256"]:
                raise SourceIndexIntegrityError(f"source bytes drifted: {path}")
        if selected.get("kind") == "packet":
            manifest_path = source_path / "source-manifest.json"
            manifest = _json(manifest_path, "source-manifest.json") if manifest_path.is_file() else {}
            submissions = _json(source_path / "submissions.json", "submissions.json")
            facts = _json(source_path / "companyfacts.json", "companyfacts.json")
            ticker, cik, identity_errors = _issuer_from_packet(source_path, manifest, submissions, facts)
            if identity_errors or ticker != selected.get("ticker") or cik != selected.get("cik"):
                raise SourceIndexIdentityError("packet identity no longer matches indexed identity")
            current_candidates = manifest.get("eligible_filings")
            if isinstance(current_candidates,list):
                current_filing_keys=sorted(tuple(_filing_metadata(row).get(key) for key in ('accession','form','report_date','filed_date')) for row in current_candidates if isinstance(row,Mapping))
                indexed_filing_keys=sorted(tuple(row.get(key) for key in ('accession','form','report_date','filed_date')) for row in selected.get('filings',[]) if isinstance(row,Mapping))
                if current_filing_keys!=indexed_filing_keys: raise SourceIndexIdentityError('eligible filing metadata no longer matches packet manifest')
            declared = manifest.get("packet_payload_sha256")
            if isinstance(declared, Mapping):
                for name, expected in declared.items():
                    if not isinstance(expected, str):
                        continue
                    declared_path = source_path / str(name)
                    if declared_path.is_file() and _hash_file(declared_path) != expected:
                        raise SourceIndexIntegrityError(f"declared packet hash mismatch: {declared_path}")
            return {"kind": "packet", "path": str(source_path), "ticker": ticker, "cik": cik, "manifest": manifest or None, "submissions": submissions, "companyfacts": facts, "filings":selected.get('filings',[])}
        structural = _json(source_path, "structural-filing.json")
        current = _structural_entry(source_path, self.allowed_output_root)
        if (current.get("validation_errors") or current.get("ticker") != selected.get("ticker") or current.get("cik") != selected.get("cik")
            or current.get("filing") != selected.get("filing") or current.get('fact_identity_complete')!=selected.get('fact_identity_complete')):
            raise SourceIndexIdentityError("structural identity no longer matches indexed identity")
        package_path = source_path.parent / "package-manifest.json"
        if package_path.is_file():
            package = _json(package_path, "package-manifest.json")
            entrypoint = package.get("entrypoint_local_path")
            if isinstance(entrypoint, str) and entrypoint:
                pure=PurePosixPath(entrypoint)
                if pure.is_absolute() or '..' in pure.parts or '.' in pure.parts:
                    raise SourceIndexIntegrityError('package entrypoint path is unsafe')
                entrypoint_path=source_path.parent/Path(*pure.parts)
                declared = next((row.get("sha256") for row in package.get("files", []) if isinstance(row, Mapping) and row.get("local_path") == entrypoint), None)
                if isinstance(declared, str) and entrypoint_path.is_file() and _hash_file(entrypoint_path) != declared:
                    raise SourceIndexIntegrityError(f"package entrypoint bytes drifted: {entrypoint_path}")
        return {"kind": "structural", "path": str(source_path), "ticker": selected.get("ticker"), "cik": selected.get("cik"), "structural": structural, "filing": selected.get("filing"),
            'package_entrypoint_rehashed':bool(package_path.is_file() and isinstance(package.get('entrypoint_local_path'),str) and (source_path.parent/package['entrypoint_local_path']).is_file())}


def load_source_index(index_path: Path, *, allowed_output_root: Path | None = None) -> SourceIndex:
    path = Path(index_path).resolve()
    payload = _json(path, "source index")
    if payload.get("schema_version") != SOURCE_INDEX_SCHEMA:
        raise SourceIndexIntegrityError("unsupported source index schema")
    root = Path(allowed_output_root or payload.get("allowed_output_root", path.parent)).resolve()
    _safe_relative(path, root)
    expected = payload.get("index_sha256")
    actual = sha256_bytes(canonical_json_bytes(_index_digest_payload(payload)))
    if expected != actual:
        raise SourceIndexIntegrityError("source index hash mismatch")
    if not isinstance(payload.get("entries"), list):
        raise SourceIndexIntegrityError("source index entries are invalid")
    return SourceIndex(path=path, allowed_output_root=root, payload=payload)


def lookup_source_entries(index: SourceIndex | Path, **filters: str | None) -> tuple[Mapping[str, Any], ...]:
    loaded = load_source_index(index) if not isinstance(index, SourceIndex) else index
    return loaded.lookup(**filters)


def read_index_entry(index: SourceIndex | Path, entry: Mapping[str, Any] | str) -> dict[str, Any]:
    loaded = load_source_index(index) if not isinstance(index, SourceIndex) else index
    return loaded.read(entry)
