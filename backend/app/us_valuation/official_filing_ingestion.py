"""Manifest-driven, serving-safe official SEC filing ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from .official_evidence import (
    EvidenceCandidate,
    EvidenceDecision,
    EvidenceRequest,
    unresolved_package_failure,
)
from .sec_client import normalize_cik, sec_archive_url


SCHEMA_VERSION = "FINSIGHT-OFFICIAL-FILING-INGESTION-1"
ELIGIBLE_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})
ANNUAL_FORMS = frozenset({"10-K", "10-K/A"})


@dataclass(frozen=True)
class FilingPair:
    controlling: dict[str, str]
    latest_annual: dict[str, str]


class FilingPackageFailure(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _inside(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _validate_output(output_dir: Path, protected_serving_roots: Sequence[Path]) -> None:
    target = Path(output_dir).resolve(strict=False)
    for root in protected_serving_roots:
        protected = Path(root).resolve(strict=False)
        if _inside(target, protected):
            raise ValueError("official evidence output must remain outside protected serving roots")


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    root = Path(root)
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _filing_record(value: Mapping[str, Any]) -> dict[str, str]:
    aliases = {
        "accession": value.get("accession", value.get("accessionNumber")),
        "form": value.get("form"),
        "filed": value.get("filed", value.get("filingDate")),
        "report_date": value.get("report_date", value.get("reportDate")),
        "primary_document": value.get("primary_document", value.get("primaryDocument")),
    }
    result: dict[str, str] = {}
    for key, raw in aliases.items():
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"filing {key} is required")
        result[key] = raw.strip()
    if result["form"].upper() not in ELIGIBLE_FORMS:
        raise ValueError(f"unsupported filing form: {result['form']}")
    result["form"] = result["form"].upper()
    for field in ("filed", "report_date"):
        try:
            date.fromisoformat(result[field])
        except ValueError as error:
            raise ValueError(f"filing {field} must be an ISO date") from error
    return result


def select_filing_pair(
    filings: Iterable[Mapping[str, Any]], *, valuation_date: str
) -> FilingPair:
    """Select the latest cutoff-eligible 10-K/Q and latest eligible 10-K."""

    try:
        date.fromisoformat(valuation_date)
    except ValueError as error:
        raise ValueError("valuation_date must be an ISO date") from error
    eligible = []
    for item in filings:
        if str(item.get("form", "")).upper() not in ELIGIBLE_FORMS:
            continue
        filing = _filing_record(item)
        if filing["filed"] <= valuation_date:
            eligible.append(filing)
    if not eligible:
        raise ValueError("no cutoff-eligible 10-K/Q filing")
    controlling = max(
        eligible,
        key=lambda item: (item["filed"], item["report_date"], item["accession"]),
    )
    annual = [item for item in eligible if item["form"] in ANNUAL_FORMS]
    if not annual:
        raise ValueError("no cutoff-eligible annual filing")
    latest_annual = max(
        annual,
        key=lambda item: (item["filed"], item["report_date"], item["accession"]),
    )
    return FilingPair(controlling=controlling, latest_annual=latest_annual)


def material_gap_requires_filing(
    *,
    companyfacts: Mapping[str, Any],
    controlling_accession: str,
    material_fields: Sequence[str],
    expected_units: Mapping[str, str] | None = None,
    expected_period_end: str | None = None,
    valuation_date: str | None = None,
) -> bool:
    """Trigger raw filing ingestion for accession drift or any missing material field."""

    companyfacts_accession = companyfacts.get("accession")
    if companyfacts_accession != controlling_accession:
        return True
    fields = companyfacts.get("fields")
    if not isinstance(fields, Mapping):
        return bool(material_fields)
    for field in material_fields:
        record = fields.get(field)
        if not isinstance(record, Mapping):
            return True
        value = record.get("value")
        if value is None or isinstance(value, bool):
            return True
        source_accession = record.get("source_accession")
        if source_accession is not None and source_accession != controlling_accession:
            return True
        expected_unit = (expected_units or {}).get(field)
        if expected_unit is not None and record.get("unit") != expected_unit:
            return True
        if expected_period_end is not None and record.get("period_end") not in {None, expected_period_end}:
            return True
        filed_date = record.get("filed_date")
        if valuation_date is not None and filed_date is not None and filed_date > valuation_date:
            return True
    return False


def _requests(raw: object, valuation_date: str) -> tuple[EvidenceRequest, ...]:
    if not isinstance(raw, list):
        raise ValueError("material_requests must be a list")
    requests = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("material request must be an object")
        payload = dict(item)
        payload.setdefault("valuation_date", valuation_date)
        requests.append(EvidenceRequest.from_dict(payload))
    if len({item.request_id for item in requests}) != len(requests):
        raise ValueError("material request identifiers must be unique")
    return tuple(requests)


def _parsed_value(value: object) -> dict[str, Any]:
    payload = value.as_dict() if hasattr(value, "as_dict") else value
    if not isinstance(payload, Mapping):
        raise ValueError("parsed filing must be an object")
    return dict(payload)


def _enrich_parsed_payload(
    payload: Mapping[str, Any], *, filing: Mapping[str, str]
) -> dict[str, Any]:
    result = dict(payload)
    result.setdefault("source_accession", filing["accession"])
    result.setdefault("form", filing["form"])
    result["filed_date"] = filing["filed"]
    result["report_date"] = filing["report_date"]
    facts = result.get("facts")
    if isinstance(facts, list):
        enriched = []
        for raw in facts:
            if not isinstance(raw, Mapping):
                enriched.append(raw)
                continue
            fact = dict(raw)
            fact.setdefault("source_accession", filing["accession"])
            fact.setdefault("filing_form", filing["form"])
            fact["filed_date"] = filing["filed"]
            fact["report_date"] = filing["report_date"]
            enriched.append(fact)
        result["facts"] = enriched
    return result


def _package_identity(
    entrypoint: Path, *, cik: str, filing: Mapping[str, str]
) -> dict[str, str]:
    entrypoint = Path(entrypoint)
    manifest_path = entrypoint.parent / "package-manifest.json"
    if manifest_path.is_file():
        manifest_raw = manifest_path.read_bytes()
        manifest = json.loads(manifest_raw)
        if (
            normalize_cik(manifest.get("cik", "")) != normalize_cik(cik)
            or manifest.get("accession") != filing["accession"]
            or manifest.get("form") != filing["form"]
            or manifest.get("entrypoint_local_path") != entrypoint.name
        ):
            raise ValueError("captured package identity does not match the selected filing")
        generation = str(manifest.get("generation") or "")
        if not generation:
            raise ValueError("captured package generation is missing")
        manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    else:
        # Hermetic injected test packages have no full SEC manifest. They are still
        # content-bound and cannot be promoted outside the private test contract.
        generation = "fixture-" + hashlib.sha256(entrypoint.read_bytes()).hexdigest()
        manifest_sha = generation.removeprefix("fixture-")
    return {
        "cik": normalize_cik(cik),
        "accession": filing["accession"],
        "form": filing["form"],
        "filed": filing["filed"],
        "report_date": filing["report_date"],
        "primary_document": filing["primary_document"],
        "package_generation": generation,
        "package_manifest_sha256": manifest_sha,
    }


def _validate_parsed_payload(
    payload: Mapping[str, Any], *, filing: Mapping[str, str]
) -> None:
    accession = payload.get("source_accession", payload.get("accession"))
    if accession is not None and accession != filing["accession"]:
        raise ValueError("cached parsed output accession mismatch")
    if payload.get("form") not in {None, filing["form"]}:
        raise ValueError("cached parsed output form mismatch")
    for key, filing_key in (("filed_date", "filed"), ("report_date", "report_date")):
        if payload.get(key) not in {None, filing[filing_key]}:
            raise ValueError(f"cached parsed output {key} mismatch")
    facts = payload.get("facts")
    if not isinstance(facts, list) or not facts:
        raise ValueError("cached parsed output must contain facts")


def _parsed_cache_value(
    payload: Mapping[str, Any], *, package: Mapping[str, str]
) -> dict[str, Any]:
    return {
        "schema_version": "FINSIGHT-OFFICIAL-PARSED-FILING-1",
        "package": dict(package),
        "parsed": dict(payload),
    }


def _write_immutable(path: Path, value: object) -> None:
    raw = _canonical_bytes(value)
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}-", delete=False) as handle:
        handle.write(raw)
        staging = Path(handle.name)
    try:
        staging.replace(path)
    finally:
        staging.unlink(missing_ok=True)


def _default_dependencies() -> tuple[Callable[..., Path], Callable[..., Any]]:
    from .arelle_adapter import parse_structural_filing
    from .filing_package import cache_structural_filing_package

    def capture(**kwargs: Any) -> Path:
        client = kwargs.pop("client")
        return cache_structural_filing_package(client, **kwargs)

    return capture, parse_structural_filing


def _failure_decisions(
    requests: Sequence[EvidenceRequest], *, valuation_date: str, filing: Mapping[str, str], error: Exception
) -> list[dict[str, Any]]:
    code = str(getattr(error, "code", "OFFICIAL_PACKAGE_FAILURE"))
    return [
        unresolved_package_failure(
            request,
            valuation_date=valuation_date,
            code=code,
            accession=filing["accession"],
            detail=str(error),
        ).as_dict()
        for request in requests
    ]


def _pending_decisions(
    requests: Sequence[EvidenceRequest], *, valuation_date: str, completeness_proof: Sequence[str]
) -> list[dict[str, Any]]:
    return [
        EvidenceDecision(
            request=request,
            selected=None,
            selected_range=None,
            rejected_candidates=(),
            status="unresolved",
            completeness_proof=tuple(completeness_proof),
            reason_codes=("PENDING_SEMANTIC_EVIDENCE_DECISION",),
            valuation_date=valuation_date,
        ).as_dict()
        for request in requests
    ]


def _companyfacts_coverage_decisions(
    requests: Sequence[EvidenceRequest], *, valuation_date: str
) -> list[dict[str, Any]]:
    return [
        EvidenceDecision(
            request=request,
            selected=None,
            selected_range=None,
            rejected_candidates=(),
            status="unresolved",
            completeness_proof=("companyfacts_checked", "filing_ingestion_not_triggered"),
            reason_codes=("COMPANYFACTS_COVERAGE_PRESENT_PENDING_EVIDENCE_PROJECTION",),
            valuation_date=valuation_date,
        ).as_dict()
        for request in requests
    ]


def _pending_one(
    request: EvidenceRequest,
    *,
    valuation_date: str,
    proof: Sequence[str],
    reason_codes: Sequence[str],
    rejected_candidates: Sequence[Mapping[str, Any]] = (),
) -> EvidenceDecision:
    return EvidenceDecision(
        request=request,
        selected=None,
        selected_range=None,
        rejected_candidates=tuple(dict(item) for item in rejected_candidates),
        status="unresolved",
        completeness_proof=tuple(proof),
        reason_codes=tuple(reason_codes),
        valuation_date=valuation_date,
    )


def _candidate_from_structural_fact(
    *,
    request: EvidenceRequest,
    fact: Any,
    filing: Mapping[str, str],
    cik: str,
    accepted_scope: bool,
) -> EvidenceCandidate:
    metadata = dict(fact.filing_metadata)
    return EvidenceCandidate(
        field=request.required_field,
        value=fact.value,
        tag=fact.qname,
        dimensions=fact.dimensions,
        unit=fact.unit,
        period_start=fact.period_start,
        period_end=fact.period_end,
        accession=fact.source_accession,
        filed_date=fact.filed_date or filing["filed"],
        report_date=fact.report_date or filing["report_date"],
        source_url=metadata.get("primary_source_url")
        or sec_archive_url(cik, filing["accession"], filing["primary_document"]),
        extraction_method="arelle_inline_xbrl",
        form=fact.filing_form or filing["form"],
        source_kind="structural_xbrl",
        cik=normalize_cik(cik),
        entity_identifier=fact.entity_identifier,
        entity_scheme=fact.entity_scheme,
        consolidation_scope="consolidated_parent" if accepted_scope else "unknown",
    )


def _structural_evidence_decisions(
    requests: Sequence[EvidenceRequest],
    *,
    parsed: Mapping[str, Any],
    filing: Mapping[str, str],
    cik: str,
    valuation_date: str,
    proof: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from .concept_resolver import load_structural_rules, resolve_concept
    from .evidence_field_registry import load_field_registry
    from .structural_xbrl import ResolutionRequest, StructuralFiling

    try:
        structural = StructuralFiling.from_dict(parsed)
        rules = load_structural_rules()
        field_registry = load_field_registry()
    except (KeyError, TypeError, ValueError) as error:
        decisions = [
            _pending_one(
                request,
                valuation_date=valuation_date,
                proof=proof,
                reason_codes=("STRUCTURAL_OUTPUT_INVALID", type(error).__name__),
            ).as_dict()
            for request in requests
        ]
        return decisions, []

    decisions: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for request in requests:
        metric = rules.get(request.required_field)
        governed_field = field_registry.get(request.required_field)
        if (
            not isinstance(metric, Mapping)
            or not isinstance(metric.get("unit"), str)
            or governed_field is None
        ):
            decisions.append(
                _pending_one(
                    request,
                    valuation_date=valuation_date,
                    proof=proof,
                    reason_codes=("FIELD_NOT_IN_GOVERNED_EVIDENCE_REGISTRY",),
                ).as_dict()
            )
            continue
        resolution = resolve_concept(
            ResolutionRequest(
                normalized_concept=request.required_field,
                period_end=filing["report_date"],
                source_accession=filing["accession"],
                unit=metric["unit"],
                statement_role="balance_sheet",
                form=filing["form"],
                valuation_date=valuation_date,
            ),
            structural.facts,
        )
        fact = resolution.evidence.fact if resolution.evidence is not None else None
        if fact is None:
            decisions.append(
                _pending_one(
                    request,
                    valuation_date=valuation_date,
                    proof=proof,
                    reason_codes=resolution.reason_codes or ("NO_STRUCTURAL_CANDIDATE",),
                ).as_dict()
            )
            continue
        try:
            entity_matches = (
                fact.entity_identifier is not None
                and normalize_cik(fact.entity_identifier) == normalize_cik(cik)
                and fact.entity_scheme is not None
            )
        except ValueError:
            entity_matches = False
        candidate = _candidate_from_structural_fact(
            request=request,
            fact=fact,
            filing=filing,
            cik=cik,
            accepted_scope=resolution.status == "accepted" and entity_matches,
        )
        registry_allows = governed_field.matches_concept(candidate.tag) and governed_field.allows(
            unit=candidate.unit,
            period_role=request.period_role,
            statement_role="balance_sheet",
            consolidation_scope=candidate.consolidation_scope,
            dimensions=candidate.dimensions,
        )
        candidates.append(candidate.as_dict())
        if resolution.status == "accepted" and entity_matches and registry_allows:
            decision = EvidenceDecision(
                request=request,
                selected=candidate,
                selected_range=None,
                rejected_candidates=(),
                status="explicit_zero" if candidate.value == 0 else "reported",
                completeness_proof=tuple(proof),
                reason_codes=("EXACT_CONTROLLING_FILING_FACT",) + resolution.reason_codes,
                valuation_date=valuation_date,
            )
        else:
            rejection_reasons = resolution.reason_codes or ("STRUCTURAL_CANDIDATE_REQUIRES_REVIEW",)
            if not entity_matches:
                rejection_reasons = ("ENTITY_IDENTITY_MISMATCH",) + tuple(rejection_reasons)
            if not registry_allows:
                rejection_reasons = ("FIELD_REGISTRY_POLICY_MISMATCH",) + tuple(rejection_reasons)
            decision = _pending_one(
                request,
                valuation_date=valuation_date,
                proof=proof,
                reason_codes=("STRUCTURAL_CANDIDATE_REJECTED",),
                rejected_candidates=(
                    {"candidate": candidate.as_dict(), "reason_codes": rejection_reasons},
                ),
            )
        decisions.append(decision.as_dict())
    return decisions, candidates


def _ingest_manifest_unlocked(
    manifest: Mapping[str, Any],
    *,
    output_dir: Path,
    package_capture: Callable[..., Path] | None = None,
    parse: Callable[..., Any] | None = None,
    protected_serving_roots: Sequence[Path] = (),
    client: object | None = None,
) -> dict[str, Any]:
    """Capture and parse the controlling/annual filing pair for arbitrary issuers.

    Reusing the same immutable output returns the existing receipt without invoking the
    package or parser again. A package/parse error becomes an explicit decision for every
    material request instead of disappearing as a missing field.
    """

    output_dir = Path(output_dir)
    _validate_output(output_dir, protected_serving_roots)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("official filing ingestion manifest schema mismatch")
    valuation_date = str(manifest.get("valuation_date") or "")
    # select_filing_pair performs lexical ISO cutoff comparisons; validate here first.
    from datetime import date
    try:
        date.fromisoformat(valuation_date)
    except ValueError as error:
        raise ValueError("valuation_date must be an ISO date") from error
    issuers = manifest.get("issuers")
    if not isinstance(issuers, list) or not issuers:
        raise ValueError("ingestion manifest needs issuers")

    receipt_path = output_dir / "official-filing-ingestion.json"
    manifest_hash = _digest(manifest)
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("input_manifest_sha256") != manifest_hash:
            raise FileExistsError("immutable ingestion output belongs to another manifest")
        return existing

    if package_capture is None or parse is None:
        default_capture, default_parse = _default_dependencies()
        package_capture = package_capture or default_capture
        parse = parse or default_parse

    serving_hash_before = {
        str(Path(root).resolve(strict=False)): _tree_hash(Path(root))
        for root in protected_serving_roots
    }

    cases: list[dict[str, Any]] = []
    seen_identities: set[tuple[str, str]] = set()
    for raw_issuer in issuers:
        if not isinstance(raw_issuer, Mapping):
            raise ValueError("issuer manifest entry must be an object")
        ticker = str(raw_issuer.get("ticker") or "").upper()
        cik = normalize_cik(raw_issuer.get("cik", ""))
        if not ticker:
            raise ValueError("issuer ticker is required")
        if (ticker, cik) in seen_identities:
            raise ValueError("duplicate issuer identity")
        seen_identities.add((ticker, cik))
        filings = raw_issuer.get("filings")
        if not isinstance(filings, list):
            raise ValueError(f"{ticker}: filings must be a list")
        pair = select_filing_pair(filings, valuation_date=valuation_date)
        requests = _requests(raw_issuer.get("material_requests", []), valuation_date)
        companyfacts = raw_issuer.get("companyfacts")
        if not isinstance(companyfacts, Mapping):
            raise ValueError(f"{ticker}: companyfacts coverage record is required")
        triggered = material_gap_requires_filing(
            companyfacts=companyfacts,
            controlling_accession=pair.controlling["accession"],
            material_fields=tuple(
                request.required_field for request in requests if request.materiality == "material"
            ),
            expected_units={
                request.required_field: request.expected_unit
                for request in requests
                if request.expected_unit is not None
            },
            expected_period_end=pair.controlling["report_date"],
            valuation_date=valuation_date,
        )

        package_records: list[dict[str, Any]] = []
        failures_by_accession: dict[str, dict[str, Any]] = {}
        parsed_accessions: set[str] = set()
        parsed_payloads: dict[str, dict[str, Any]] = {}
        if triggered:
            unique_filings = {
                filing["accession"]: filing
                for filing in (pair.latest_annual, pair.controlling)
            }
            for accession, filing in sorted(unique_filings.items()):
                parsed_path = output_dir / "parsed" / ticker / f"{accession}.json"
                try:
                    relevant = raw_issuer.get("relevant_attachments")
                    if relevant is not None and not isinstance(relevant, Mapping):
                        raise ValueError("relevant_attachments must be an accession mapping")
                    attachment_inventory = (
                        relevant.get(accession)
                        if isinstance(relevant, Mapping) and accession in relevant
                        else None
                    )
                    entrypoint = package_capture(
                        client=client,
                        cik=cik,
                        accession=accession,
                        primary_document=filing["primary_document"],
                        form=filing["form"],
                        filed_date=filing["filed"],
                        report_date=filing["report_date"],
                        relevant_attachments=attachment_inventory,
                        output_dir=output_dir / "packages" / ticker,
                    )
                    package_identity = _package_identity(
                        Path(entrypoint), cik=cik, filing=filing
                    )
                    if parsed_path.is_file():
                        cached = json.loads(parsed_path.read_text(encoding="utf-8"))
                        if (
                            not isinstance(cached, Mapping)
                            or cached.get("schema_version") != "FINSIGHT-OFFICIAL-PARSED-FILING-1"
                            or cached.get("package") != package_identity
                            or not isinstance(cached.get("parsed"), Mapping)
                        ):
                            raise ValueError("cached parsed output is not bound to the selected package generation")
                        parsed = dict(cached["parsed"])
                        if _enrich_parsed_payload(parsed, filing=filing) != parsed:
                            raise ValueError("cached parsed output is missing selected filing metadata")
                        parsed_cache = dict(cached)
                    else:
                        parsed = _parsed_value(
                            parse(Path(entrypoint), accession=accession, form=filing["form"])
                        )
                        parsed = _enrich_parsed_payload(parsed, filing=filing)
                        _validate_parsed_payload(parsed, filing=filing)
                        parsed_cache = _parsed_cache_value(parsed, package=package_identity)
                        _write_immutable(parsed_path, parsed_cache)
                    _validate_parsed_payload(parsed, filing=filing)
                    parsed_accessions.add(accession)
                    parsed_payloads[accession] = parsed
                    package_records.append(
                        {
                            **filing,
                            "package_generation": package_identity["package_generation"],
                            "package_manifest_sha256": package_identity["package_manifest_sha256"],
                            "parsed_path": parsed_path.relative_to(output_dir).as_posix(),
                            "parsed_sha256": _digest(parsed),
                            "parsed_cache_sha256": _digest(parsed_cache),
                            "status": "parsed",
                        }
                    )
                except Exception as error:  # converted to explicit private evidence outcomes
                    failure = {
                        "accession": accession,
                        "code": str(getattr(error, "code", "OFFICIAL_PACKAGE_FAILURE")),
                        "detail": str(error),
                    }
                    failures_by_accession[accession] = failure
                    package_records.append(
                        {**filing, "status": "failed", "failure_code": failure["code"], "failure": failure["detail"]}
                    )

        candidate_records: list[dict[str, Any]] = []
        if not triggered:
            decisions = _companyfacts_coverage_decisions(
                requests, valuation_date=valuation_date
            )
        elif pair.controlling["accession"] in failures_by_accession:
            failure = failures_by_accession[pair.controlling["accession"]]
            error = FilingPackageFailure(failure["code"], failure["detail"])
            decisions = _failure_decisions(
                requests,
                valuation_date=valuation_date,
                filing=pair.controlling,
                error=error,
            )
        else:
            proof = ["companyfacts_checked", "controlling_filing_parsed"]
            annual_accession = pair.latest_annual["accession"]
            if annual_accession == pair.controlling["accession"] or annual_accession in parsed_accessions:
                proof.append("latest_annual_filing_parsed")
            elif annual_accession in failures_by_accession:
                proof.append("latest_annual_package_failed")
            decisions, candidate_records = _structural_evidence_decisions(
                requests,
                parsed=parsed_payloads[pair.controlling["accession"]],
                filing=pair.controlling,
                cik=cik,
                valuation_date=valuation_date,
                proof=proof,
            )
        cases.append(
            {
                "ticker": ticker,
                "cik": cik,
                "triggered": triggered,
                "trigger_reasons": [
                    reason
                    for reason, active in (
                        ("CONTROLLING_ACCESSION_MISSING", companyfacts.get("accession") != pair.controlling["accession"]),
                        ("MATERIAL_FIELD_MISSING", any(not isinstance(companyfacts.get("fields", {}).get(request.required_field), Mapping) or companyfacts.get("fields", {}).get(request.required_field, {}).get("value") is None for request in requests if request.materiality == "material")),
                    )
                    if active
                ],
                "controlling_filing": pair.controlling,
                "latest_annual_filing": pair.latest_annual,
                "packages": package_records,
                "package_failures": list(failures_by_accession.values()),
                "requests": [request.as_dict() for request in requests],
                "candidates": candidate_records,
                "decisions": decisions,
            }
        )

    serving_hash_after = {
        str(Path(root).resolve(strict=False)): _tree_hash(Path(root))
        for root in protected_serving_roots
    }
    if serving_hash_before != serving_hash_after:
        raise RuntimeError("protected serving artifacts changed during official ingestion")
    result = {
        "schema_version": SCHEMA_VERSION,
        "valuation_date": valuation_date,
        "input_manifest_sha256": manifest_hash,
        "issuer_count": len(cases),
        "request_count": sum(len(case["requests"]) for case in cases),
        "decision_count": sum(len(case["decisions"]) for case in cases),
        "parsed_package_count": sum(
            item["status"] == "parsed"
            for case in cases for item in case["packages"]
        ),
        "failed_package_count": sum(
            item["status"] == "failed" for case in cases for item in case["packages"]
        ),
        "serving_hash_before": serving_hash_before,
        "serving_hash_after": serving_hash_after,
        "serving_artifacts_changed": False,
        "issuers": cases,
    }
    _write_immutable(receipt_path, result)
    return result


def ingest_manifest(
    manifest: Mapping[str, Any],
    *,
    output_dir: Path,
    package_capture: Callable[..., Path] | None = None,
    parse: Callable[..., Any] | None = None,
    protected_serving_roots: Sequence[Path] = (),
    client: object | None = None,
) -> dict[str, Any]:
    """Run one immutable ingestion writer, returning an identical existing receipt."""

    output_dir = Path(output_dir)
    _validate_output(output_dir, protected_serving_roots)
    receipt_path = output_dir / "official-filing-ingestion.json"
    manifest_hash = _digest(manifest)
    if receipt_path.is_file():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("input_manifest_sha256") != manifest_hash:
            raise FileExistsError("immutable ingestion output belongs to another manifest")
        return existing

    output_dir.mkdir(parents=True, exist_ok=True)
    lock = output_dir / ".official-ingestion.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        if receipt_path.is_file():
            existing = json.loads(receipt_path.read_text(encoding="utf-8"))
            if existing.get("input_manifest_sha256") == manifest_hash:
                return existing
        raise RuntimeError(
            "official filing ingestion already has an active or stale writer lock"
        ) from error
    owner_path = lock / "owner.json"
    owner_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "created_at_epoch": time.time(),
                "input_manifest_sha256": manifest_hash,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        return _ingest_manifest_unlocked(
            manifest,
            output_dir=output_dir,
            package_capture=package_capture,
            parse=parse,
            protected_serving_roots=protected_serving_roots,
            client=client,
        )
    finally:
        try:
            owner_path.unlink(missing_ok=True)
            lock.rmdir()
        except OSError:
            pass
