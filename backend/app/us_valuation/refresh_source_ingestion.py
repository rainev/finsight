"""Reusable, cutoff-bound source capture for valuation refresh.

This module acquires only source packets.  It does not choose valuation inputs,
edit recipes, or interpret unfamiliar events.  Cached submissions/companyfacts
can be replayed without a network User-Agent; any cache miss or refresh requires
an explicit monitored SEC User-Agent.
"""

from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urljoin, urlparse

from .catalog import canonical_json_bytes
from .arelle_adapter import parse_structural_filing
from .filing_package import cache_structural_filing_package
from .official_filing_ingestion import FilingPair, ingest_manifest, select_filing_pair
from .sec_client import SecClient, normalize_cik, sec_archive_url
from .structural_xbrl import StructuralFiling


SOURCE_PACKET_SCHEMA = "FINSIGHT-REFRESH-SOURCE-PACKET-1"
EVENT_FORMS = frozenset({"8-K", "8-K/A"})
DEFAULT_EVENT_ITEMS = frozenset({"2.02", "9.01"})


class _FilingLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._text: list[str] = []
        self._anchor_open = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if isinstance(href, str) and href:
            self.links.append({"href": href, "text": ""})
            self._anchor_open = True

    def handle_data(self, data: str) -> None:
        if self._anchor_open and self.links and data.strip():
            self.links[-1]["text"] += " ".join(data.split())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == 'a':
            self._anchor_open = False


def _sgml_exhibits(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8", errors="replace")
    found: list[dict[str, str]] = []
    for document in re.split(r"(?i)<DOCUMENT>", text):
        type_match = re.search(r"(?im)^\s*<TYPE>\s*(EX-[0-9.]+)\s*$", document)
        filename_match = re.search(r"(?im)^\s*<FILENAME>\s*([^\s<]+)\s*$", document)
        if not type_match or not filename_match:
            continue
        document_type = type_match.group(1).upper()
        if not document_type.startswith("EX-"):
            continue
        filename = filename_match.group(1)
        if '/' in filename or '\\' in filename or filename in {'.','..'}:
            continue
        found.append({"name": filename, "type": document_type, "basis": "submission_sgml_document_type"})
    return found


def _definition_hash() -> str:
    module_root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in ("arelle_adapter.py", "arelle_worker.py"):
        path = module_root / name
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class SourceCaptureError(RuntimeError):
    """Source acquisition or identity is incomplete."""


class UnfamiliarMaterialEvent(SourceCaptureError):
    """An event item is outside the explicitly approved routine screen."""


def _iso(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_record(digest: str, *, basis: str) -> dict[str, str]:
    return {"algorithm": "sha256", "basis": basis, "digest": digest}


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes(value)
    if path.exists():
        if path.read_bytes() != payload:
            raise SourceCaptureError(f"immutable parsed structural cache drift: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _cache_structural_payload(
    *,
    path: Path,
    accession: str,
    filing: Mapping[str, Any],
    cik: str,
    cutoff: str,
    parser_hash: str,
    source_descriptor: Mapping[str, Any],
    parse_payload: Any,
    parsed_path: Path,
) -> tuple[dict[str, Any], str, bool]:
    if filing["filed"] > cutoff or filing["report_date"] > cutoff:
        raise SourceCaptureError("structural filing is after requested cutoff")
    source_hash = hashlib.sha256(canonical_json_bytes(source_descriptor)).hexdigest()
    cache_key = f"{accession}-{source_hash[:16]}-{parser_hash[:16]}.json"
    cache_path = parsed_path / cache_key
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            payload = cached["parsed"]
            if (
                cached.get("schema_version") != "FINSIGHT-REFRESH-PARSED-STRUCTURAL-1"
                or cached.get("accession") != accession
                or cached.get("form") != filing["form"]
                or cached.get("report_date") != filing["report_date"]
                or cached.get("cik") != cik
                or cached.get("parser_definition_sha256") != parser_hash
                or cached.get("source_package_sha256") != source_hash
                or hashlib.sha256(canonical_json_bytes(payload)).hexdigest() != cached.get("parsed_sha256")
            ):
                raise SourceCaptureError("parsed structural cache identity or digest mismatch")
            validated = _validate_structural_payload(payload, cik=cik, filing=filing)
            return validated, hashlib.sha256(canonical_json_bytes(validated)).hexdigest(), True
        except SourceCaptureError:
            raise
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SourceCaptureError(f"parsed structural cache is invalid: {cache_path}") from exc
    payload = parse_payload() if callable(parse_payload) else parse_payload
    parsed_sha = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    _atomic_json(
        cache_path,
        {
            "schema_version": "FINSIGHT-REFRESH-PARSED-STRUCTURAL-1",
            "cik": cik,
            "accession": accession,
            "form": filing["form"],
            "report_date": filing["report_date"],
            "validated_filed_date": filing["filed"],
            "validated_report_date": filing["report_date"],
            "parser_definition_sha256": parser_hash,
            "source_package_sha256": source_hash,
            "parsed_sha256": parsed_sha,
            "parsed": payload,
        },
    )
    validated = _validate_structural_payload(payload, cik=cik, filing=filing)
    return validated, hashlib.sha256(canonical_json_bytes(validated)).hexdigest(), False


def _records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    if not isinstance(accessions, list):
        raise SourceCaptureError("submissions recent accession list is missing")
    return [
        {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(len(accessions))
    ]


def _validate_identity(submissions: Mapping[str, Any], companyfacts: Mapping[str, Any], cik: str) -> None:
    if normalize_cik(submissions.get("cik", "")) != cik or normalize_cik(companyfacts.get("cik", "")) != cik:
        raise SourceCaptureError("SEC source packet CIK identity conflict")


def _cached_packet(packet_dir: Path, *, cik: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    packet_dir = Path(packet_dir)
    submissions_path = packet_dir / "submissions.json"
    companyfacts_path = packet_dir / "companyfacts.json"
    try:
        submissions_raw = submissions_path.read_bytes()
        companyfacts_raw = companyfacts_path.read_bytes()
        submissions = json.loads(submissions_raw)
        companyfacts = json.loads(companyfacts_raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceCaptureError("cached SEC source packet is missing or invalid") from exc
    if not isinstance(submissions, Mapping) or not isinstance(companyfacts, Mapping):
        raise SourceCaptureError("cached SEC source packet must contain JSON objects")
    _validate_identity(submissions, companyfacts, cik)
    hashes: dict[str, Any] = {
        "submissions.json": _hash_record(hashlib.sha256(submissions_raw).hexdigest(), basis="offline_packet_raw_bytes"),
        "companyfacts.json": _hash_record(hashlib.sha256(companyfacts_raw).hexdigest(), basis="offline_packet_raw_bytes"),
    }
    manifest_path = packet_dir / "source-manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_bytes())
            files = manifest.get('files', {})
            for name in ('submissions.json', 'companyfacts.json'):
                record = files.get(name, {})
                expected = record.get('sha256') if isinstance(record, Mapping) else None
                if expected is not None and expected != hashes[name]['digest']:
                    raise SourceCaptureError(f'cached SEC source manifest hash mismatch: {name}')
        except (ValueError, TypeError, AttributeError) as exc:
            raise SourceCaptureError('cached SEC source manifest is invalid') from exc
        hashes["source-manifest.json"] = _hash_record(_sha(manifest_path), basis="offline_packet_raw_bytes")
    return dict(submissions), dict(companyfacts), hashes


def _event_records(
    records: Sequence[Mapping[str, Any]],
    *,
    cik: str,
    cutoff: str,
    event_since: str | None,
    allowed_items: frozenset[str],
) -> list[dict[str, Any]]:
    since = _iso(event_since, "event_since") if event_since else None
    events: list[dict[str, Any]] = []
    for record in records:
        filed = record.get("filingDate")
        if record.get("form") not in EVENT_FORMS or not isinstance(filed, str) or filed > cutoff or (since and filed <= since):
            continue
        items = tuple(sorted(item.strip() for item in str(record.get("items", "")).split(",") if item.strip()))
        unfamiliar = tuple(item for item in items if item not in allowed_items)
        try:
            event_url = sec_archive_url(cik, record.get("accessionNumber", ""), record.get("primaryDocument", "")) if record.get("primaryDocument") else None
        except ValueError:
            event_url = None
        events.append(
            {
                "accession": record.get("accessionNumber"),
                "form": record.get("form"),
                "filed_date": filed,
                "report_date": record.get("reportDate"),
                "items": list(items),
                "source_url": event_url,
                "primary_document": record.get("primaryDocument"),
                "relationships_status": "not_requested",
                "relationships": [],
                "review_status": "unfamiliar_material_event" if unfamiliar else "screened",
                "unfamiliar_items": list(unfamiliar),
            }
        )
    return events


def _select_refresh_pair(
    records: Sequence[Mapping[str, Any]],
    *,
    cutoff: str,
) -> tuple[FilingPair, list[dict[str, Any]]]:
    """Keep amendments as evidence while binding the underlying regular filing."""

    pair = select_filing_pair(records, valuation_date=cutoff)
    amendments = [
        {
            **dict(row),
            "accession": row.get("accessionNumber"),
            "filed": row.get("filingDate"),
            "report_date": row.get("reportDate"),
            "primary_document": row.get("primaryDocument"),
            "amendment_kind": "financial_amendment" if row.get("reportDate") in {pair.controlling["report_date"], pair.latest_annual["report_date"]} else "unmatched_amendment",
            "review_status": "financial_amendment_requires_structural_proof" if row.get("reportDate") in {pair.controlling["report_date"], pair.latest_annual["report_date"]} else "unknown_amendment_requires_review",
        }
        for row in records
        if row.get("form") in {"10-K/A", "10-Q/A"}
        and isinstance(row.get("filingDate"), str)
        and row["filingDate"] <= cutoff
    ]
    controlling = pair.controlling
    if controlling["form"].endswith("/A"):
        underlying = [
            row for row in records
            if row.get("form") == controlling["form"].removesuffix("/A")
            and row.get("reportDate") == controlling["report_date"]
            and isinstance(row.get("filingDate"), str)
            and row["filingDate"] <= cutoff
        ]
        if not underlying:
            raise SourceCaptureError("latest amendment has no same-period underlying regular filing")
        regular = max(underlying, key=lambda row: (row["filingDate"], row["accessionNumber"]))
        controlling = {
            "accession": regular["accessionNumber"],
            "form": regular["form"],
            "filed": regular["filingDate"],
            "report_date": regular["reportDate"],
            "primary_document": regular["primaryDocument"],
        }
    latest_annual = pair.latest_annual
    if latest_annual["form"].endswith("/A"):
        underlying_annual = [
            row for row in records
            if row.get("form") == "10-K"
            and row.get("reportDate") == latest_annual["report_date"]
            and isinstance(row.get("filingDate"), str)
            and row["filingDate"] <= cutoff
        ]
        if not underlying_annual:
            raise SourceCaptureError("latest annual amendment has no same-period underlying regular filing")
        regular = max(underlying_annual, key=lambda row: (row["filingDate"], row["accessionNumber"]))
        latest_annual = {
            "accession": regular["accessionNumber"],
            "form": regular["form"],
            "filed": regular["filingDate"],
            "report_date": regular["reportDate"],
            "primary_document": regular["primaryDocument"],
        }
    return FilingPair(controlling=controlling, latest_annual=latest_annual), amendments


def _event_with_index(client: SecClient, event: dict[str, Any], *, cik: str, refresh: bool) -> dict[str, Any]:
    index = client.filing_index(cik, event["accession"], refresh=refresh)
    files = index.get("directory", {}).get("item", [])
    directory_listing = [
        {"name": item.get("name"), "type": item.get("type"), "size": item.get("size")}
        for item in files
        if isinstance(item, Mapping) and isinstance(item.get("name"), str)
    ]
    by_name = {row["name"]: row for row in directory_listing}
    review_exceptions: list[dict[str, Any]] = []
    discovered: dict[str, dict[str, str]] = {}
    document_sources = []

    primary = event.get("primaryDocument") or event.get("primary_document")
    if not isinstance(primary, str) or "/" in primary or "\\" in primary:
        review_exceptions.append({"reason": "primary_filing_body_unavailable_or_unsafe"})
    else:
        try:
            body = client.filing_attachment(cik, event["accession"], primary, refresh=refresh)
            primary_url = sec_archive_url(cik,event['accession'],primary)
            document_sources.append({'name':primary,'source_url':primary_url,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'role':'primary_filing'})
            parser = _FilingLinkParser()
            parser.feed(body.decode("utf-8", errors="replace"))
            for link in parser.links:
                target = urlparse(urljoin(primary_url,link['href']))
                expected_root = urlparse(primary_url).path.rsplit('/',1)[0] + '/'
                name = target.path.rsplit('/',1)[-1]
                explicit_exhibit = re.search(r'(?i)(?:exhibit\s*|ex-)?\b\d{1,3}\.\d+\b|\bexhibit\b|\bpress release\b',link['text'])
                if (target.scheme in {'http','https'} and target.hostname in {'www.sec.gov','sec.gov'}
                    and target.path == expected_root + name and name in by_name and name != primary and explicit_exhibit):
                    discovered.setdefault(name, {"name": name, "basis": "primary_filing_html_link",'link_text':link['text']})
        except Exception as exc:
            review_exceptions.append({"reason": f"primary_filing_body_unavailable:{type(exc).__name__}"})

    submission_name = f"{event['accession']}.txt"
    try:
        sgml = client.filing_attachment(cik, event["accession"], submission_name, refresh=refresh)
        document_sources.append({'name':submission_name,'source_url':sec_archive_url(cik,event['accession'],submission_name),
            'sha256':hashlib.sha256(sgml).hexdigest(),'bytes':len(sgml),'role':'complete_submission'})
        for exhibit in _sgml_exhibits(sgml):
            if exhibit["name"] in by_name:
                discovered[exhibit["name"]] = exhibit
    except Exception as exc:
        review_exceptions.append({"name": submission_name, "reason": f"submission_sgml_unavailable:{type(exc).__name__}"})

    relationships: list[dict[str, Any]] = []
    attachments: list[dict[str, Any]] = []
    for name, relation in sorted(discovered.items()):
        if "/" in name or "\\" in name:
            review_exceptions.append({"name": name, "reason": "nested_attachment_path_not_supported_by_safe_attachment_client"})
            continue
        try:
            raw = client.filing_attachment(cik, event["accession"], name, refresh=refresh)
        except Exception as exc:
            review_exceptions.append({"name": name, "reason": f"attachment_fetch_failed:{type(exc).__name__}"})
            continue
        digest = hashlib.sha256(raw).hexdigest()
        attachment = {
            "name": name,
            "sha256": digest,
            "source_url": sec_archive_url(cik, event["accession"], name),
            "bytes": len(raw),
        }
        attachments.append(attachment)
        relationships.append({**relation, "attachment_sha256": digest})
    if not relationships:
        review_exceptions.append({"reason": "no exhibit relationship proven by filing body or submission SGML"})
    return {
        **event,
        "relationships_status": "exhibit_relationships_captured" if relationships and not review_exceptions else "review_exception",
        "directory_listing": directory_listing,
        "relationships": relationships,
        "attachments": attachments,
        "document_sources": document_sources,
        "review_exceptions": review_exceptions,
        "index_sha256": hashlib.sha256(json.dumps(index, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }


def _structural_payload(path: Path, *, cik: str, filing: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    return _validate_structural_payload(payload, cik=cik, filing=filing), hashlib.sha256(raw).hexdigest()


def _validate_structural_payload(payload: Mapping[str, Any], *, cik: str, filing: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise SourceCaptureError("structural filing output is not an object")
    expected_accession = filing.get("accessionNumber", filing.get("accession"))
    expected_period = filing.get("reportDate", filing.get("report_date"))
    if payload.get("source_accession") != expected_accession or payload.get("form") != filing["form"]:
        raise SourceCaptureError("structural filing identity does not match selected filing")
    try:
        structural = StructuralFiling.from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceCaptureError(f"structural filing output is invalid: {exc}") from exc
    entity_ids = {str(fact.entity_identifier) for fact in structural.facts if fact.entity_identifier is not None}
    if not entity_ids or any(normalize_cik(entity) != cik for entity in entity_ids):
        raise SourceCaptureError("structural filing entity identity does not match issuer")
    if structural.report_date is not None and structural.report_date != expected_period:
        raise SourceCaptureError("structural filing report_date does not match selected filing")
    fact_report_dates = {fact.report_date for fact in structural.facts if fact.report_date is not None}
    if fact_report_dates and fact_report_dates != {expected_period}:
        raise SourceCaptureError("structural fact report_date does not match selected filing")
    validated = dict(payload)
    if structural.report_date is None:
        validated['report_date'] = expected_period
        validated['report_date_basis'] = 'validated_sec_submission_reporting_period'
        validated['legacy_top_level_period_diagnostic'] = payload.get('period_end')
    return validated


def capture_company_source(
    *,
    ticker: str,
    cik: str | int,
    cutoff: str,
    cache_dir: Path | None = None,
    offline_packet_dir: Path | None = None,
    structural_path: Path | None = None,
    output_dir: Path | None = None,
    user_agent: str | None = None,
    refresh: bool = False,
    event_since: str | None = None,
    allowed_event_items: Sequence[str] = tuple(DEFAULT_EVENT_ITEMS),
    capture_event_relationships: bool = False,
    require_structural: bool = False,
    structural_paths: Mapping[str, Path] | None = None,
    structural_output_dir: Path | None = None,
    parsed_cache_dir: Path | None = None,
    arelle_timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Capture one dynamic-cutoff source packet for ``refresh_bindings``.

    ``offline_packet_dir`` is preferred for cached replay.  If it is absent,
    ``cache_dir`` is used through ``SecClient``; a cache miss or refresh raises
    before any network request unless ``user_agent`` contains ``@``.
    """

    cutoff = _iso(cutoff, "cutoff")
    cik_normalized = normalize_cik(cik)
    if offline_packet_dir is not None:
        submissions, companyfacts, raw_hashes = _cached_packet(Path(offline_packet_dir), cik=cik_normalized)
        client = None
        network_mode = "offline_cache"
    else:
        cache_ready = bool(cache_dir and (Path(cache_dir) / f"CIK{cik_normalized}-submissions.json").is_file() and (Path(cache_dir) / f"CIK{cik_normalized}-companyfacts.json").is_file())
        if (not user_agent or "@" not in user_agent) and (refresh or not cache_ready):
            raise ValueError("SEC_USER_AGENT with monitored contact is required for source acquisition")
        client = SecClient(user_agent=user_agent, cache_dir=cache_dir or Path(".sec-cache"))
        submissions = client.submissions(cik_normalized, refresh=refresh)
        companyfacts = client.companyfacts(cik_normalized, refresh=refresh)
        _validate_identity(submissions, companyfacts, cik_normalized)
        raw_hashes = {}
        for cache_name, value in ((f"CIK{cik_normalized}-submissions.json", submissions), (f"CIK{cik_normalized}-companyfacts.json", companyfacts)):
            cache_path = Path(cache_dir or ".sec-cache") / cache_name
            if cache_path.is_file():
                raw_hashes[cache_name] = _hash_record(_sha(cache_path), basis="sec_client_cache_raw_bytes")
            else:
                raw_hashes[cache_name] = _hash_record(hashlib.sha256(canonical_json_bytes(value)).hexdigest(), basis="canonical_json_fallback_no_cache_file")
        network_mode = "network_or_sec_cache"
    records = _records(submissions)
    pair, amendment_records = _select_refresh_pair(records, cutoff=cutoff)
    events = _event_records(records, cik=cik_normalized, cutoff=cutoff, event_since=event_since, allowed_items=frozenset(allowed_event_items))
    if capture_event_relationships and events:
        if client is None:
            events = [
                {
                    **event,
                    "relationships_status": "review_exception",
                    "review_exceptions": ["event index/attachment cache unavailable in offline packet"],
                }
                for event in events
            ]
        else:
            events = [_event_with_index(client, event, cik=cik_normalized, refresh=refresh) for event in events]
    structural = None
    structural_hash = None
    annual_structural = None
    annual_structural_hash = None
    structural_receipts: list[dict[str, Any]] = []
    parsed_structural: dict[str, dict[str, Any]] = {}
    amendment_structural_receipts: list[dict[str, Any]] = []
    amendment_acquisition_failures: list[dict[str, Any]] = []
    if not require_structural and structural_path is None and not structural_paths and client is None:
        amendment_acquisition_failures.extend({
            "accession": item.get("accession"),
            "status": "acquisition_failed",
            "reason": "financial amendment structural body was not requested in offline capture",
        } for item in amendment_records if item.get("amendment_kind") == "financial_amendment")
    if require_structural and structural_path is None and not structural_paths and client is None:
        raise SourceCaptureError("required structural capture needs cached structural paths or an SEC client")
    if require_structural or structural_path is not None or structural_paths:
        parser_hash = _definition_hash()
        parsed_cache_root = Path(parsed_cache_dir or (structural_output_dir or cache_dir or Path(".sec-cache"))) / "parsed-structural"
        selected_filings = {
            pair.controlling["accession"]: pair.controlling,
            pair.latest_annual["accession"]: pair.latest_annual,
        }
        for amendment in amendment_records:
            if amendment.get("amendment_kind") == "financial_amendment":
                selected_filings.setdefault(amendment["accession"], amendment)
        for accession, filing in selected_filings.items():
            path = None
            if structural_paths and accession in structural_paths:
                path = Path(structural_paths[accession])
            elif accession == pair.controlling["accession"] and structural_path is not None:
                path = Path(structural_path)
            elif client is not None:
                package_root = Path(structural_output_dir or (cache_dir or Path(".sec-cache"))) / "structural" / ticker.upper() / accession
                try:
                    path = cache_structural_filing_package(
                        client,
                        cik=cik_normalized,
                        accession=accession,
                        primary_document=filing["primary_document"],
                        form=filing["form"],
                        filed_date=filing["filed"],
                        report_date=filing["report_date"],
                        output_dir=package_root,
                    )
                except Exception as exc:
                    raise SourceCaptureError(f"structural package capture failed for {accession}: {exc}") from exc
            if path is None:
                if accession in {item.get("accession") for item in amendment_records if item.get("amendment_kind") == "financial_amendment"}:
                    amendment_acquisition_failures.append({
                        "accession": accession,
                        "status": "acquisition_failed",
                        "reason": "financial amendment structural body is unavailable",
                    })
                    continue
                if require_structural:
                    raise SourceCaptureError(f"required structural package is unavailable for {accession}")
                continue
            try:
                package_manifest = path.parent / "package-manifest.json"
                source_descriptor = {
                    "entrypoint_sha256": _sha(path),
                    "package_manifest_sha256": _sha(package_manifest) if package_manifest.is_file() else None,
                    "entrypoint_name": path.name,
                }
                def parse_payload():
                    if path.suffix.lower() == '.json':
                        return json.loads(path.read_text(encoding='utf-8'))
                    return parse_structural_filing(path, accession=accession, form=filing['form'], timeout_seconds=arelle_timeout_seconds,
                        cpu_limit_seconds=arelle_timeout_seconds).as_dict()
                payload, digest, cache_reused = _cache_structural_payload(
                    path=path,
                    accession=accession,
                    filing=filing,
                    cik=cik_normalized,
                    cutoff=cutoff,
                    parser_hash=parser_hash,
                    source_descriptor=source_descriptor,
                    parse_payload=parse_payload,
                    parsed_path=parsed_cache_root,
                )
            except Exception as exc:
                raise SourceCaptureError(f"structural parsing failed for {accession}: {exc}") from exc
            parsed_structural[accession] = payload
            structural_receipts.append({
                "accession": accession,
                "form": filing["form"],
                "filed_date": filing["filed"],
                "report_date": filing["report_date"],
                "structural_sha256": digest,
                "raw_payload_sha256": _sha(path),
                "package_manifest_sha256": _sha(package_manifest) if package_manifest.is_file() else None,
                "source_package_sha256": hashlib.sha256(canonical_json_bytes(source_descriptor)).hexdigest(),
                "parser_definition_sha256": parser_hash,
                "parsed_cache_reused": cache_reused,
                'parse_timeout_seconds':arelle_timeout_seconds,
                "path": str(path),
            })
            if accession in {item.get("accession") for item in amendment_records if item.get("amendment_kind") == "financial_amendment"}:
                amendment_structural_receipts.append({
                    "accession": accession,
                    "status": "structural_capture_verified",
                    "structural_sha256": digest,
                    "source_package_sha256": hashlib.sha256(canonical_json_bytes(source_descriptor)).hexdigest(),
                })
        structural = parsed_structural.get(pair.controlling["accession"])
        structural_hash = next((item["structural_sha256"] for item in structural_receipts if item["accession"] == pair.controlling["accession"]), None)
        annual_structural = parsed_structural.get(pair.latest_annual["accession"])
        annual_structural_hash = next((item["structural_sha256"] for item in structural_receipts if item["accession"] == pair.latest_annual["accession"]), None)
    elif structural_path is not None:
        structural, structural_hash = _structural_payload(Path(structural_path), cik=cik_normalized, filing=pair.controlling)
    def public_filing(filing: Mapping[str, Any]) -> dict[str, Any]:
        return {
            **dict(filing),
            "accessionNumber": filing["accession"],
            "filingDate": filing["filed"],
            "reportDate": filing["report_date"],
            "primaryDocument": filing["primary_document"],
        }

    packet = {
        "schema_version": SOURCE_PACKET_SCHEMA,
        "issuer": {"ticker": ticker.upper(), "cik": cik_normalized},
        "cutoff": cutoff,
        "network_mode": network_mode,
        "controlling_filing": public_filing(pair.controlling),
        "latest_annual_filing": public_filing(pair.latest_annual),
        "amendment_filings": amendment_records,
        "amendment_structural_receipts": amendment_structural_receipts,
        "amendment_acquisition_failures": amendment_acquisition_failures,
        "submissions": submissions,
        "companyfacts": companyfacts,
        "source_urls": {
            "submissions": f"https://data.sec.gov/submissions/CIK{cik_normalized}.json",
            "companyfacts": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_normalized}.json",
            "controlling_filing": sec_archive_url(cik_normalized, pair.controlling["accession"], pair.controlling["primary_document"]),
            "latest_annual_filing": sec_archive_url(cik_normalized, pair.latest_annual["accession"], pair.latest_annual["primary_document"]),
        },
        "raw_hashes": raw_hashes,
        "events": events,
        "structural_filing": structural,
        "structural_sha256": structural_hash,
        "annual_structural_filing": annual_structural,
        "annual_structural_sha256": annual_structural_hash,
        "structural_receipts": structural_receipts,
        "structural_packets": {item["accession"]: parsed_structural.get(item["accession"]) for item in structural_receipts if item["accession"] in parsed_structural},
        "provenance": {
            "source_capture_policy": "dynamic_submissions_cutoff_with_existing_sec_client_and_official_package_contracts",
            "event_since": event_since,
            "allowed_event_items": sorted(set(allowed_event_items)),
        },
    }
    if output_dir is not None:
        path = Path(output_dir) / "source-packet.json"
        payload = canonical_json_bytes(packet)
        if path.exists() and path.read_bytes() != payload:
            raise FileExistsError("immutable source packet belongs to another cutoff or source state")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(payload)
        packet["packet_path"] = str(path)
        packet["packet_sha256"] = hashlib.sha256(payload).hexdigest()
    return packet


def ingest_official_source_manifest(
    manifest: Mapping[str, Any],
    *,
    output_dir: Path,
    client: SecClient | None = None,
    protected_serving_roots: Sequence[Path] = (),
) -> dict[str, Any]:
    """Run the existing immutable official package/Arelle ingestion boundary."""

    return ingest_manifest(
        manifest,
        output_dir=Path(output_dir),
        protected_serving_roots=protected_serving_roots,
        client=client,
    )


__all__ = [
    "SOURCE_PACKET_SCHEMA",
    "SourceCaptureError",
    "UnfamiliarMaterialEvent",
    "capture_company_source",
    "ingest_official_source_manifest",
]
