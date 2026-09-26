"""Fail-closed controls for recovering legacy FCFF bridge artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


_MISSING_FIELDS = re.compile(r"bridge incomplete \(missing ([^)]+)\)", re.IGNORECASE)


@dataclass(frozen=True)
class LegacyFcffCase:
    ticker: str
    cik: str
    valuation_date: str
    missing_fields: tuple[str, ...]
    path: Path
    artifact: dict[str, Any]


@dataclass(frozen=True)
class RecoveryDecision:
    accepted: bool
    reasons: tuple[str, ...]


def missing_bridge_fields(artifact: Mapping[str, Any]) -> tuple[str, ...]:
    """Read the explicit missing-field list from a governed legacy warning."""
    warnings = artifact.get("review", {}).get("warnings", [])
    for warning in warnings if isinstance(warnings, list) else []:
        match = _MISSING_FIELDS.search(str(warning))
        if match:
            fields = tuple(
                field.strip() for field in match.group(1).split(",") if field.strip()
            )
            if fields:
                return fields
    raise ValueError("Legacy FCFF artifact does not identify its missing bridge fields")


def discover_legacy_fcff_cases(data_root: str | Path) -> list[LegacyFcffCase]:
    """Discover only explicit FCFF fallback artifacts, in deterministic order."""
    cases: list[LegacyFcffCase] = []
    for path in sorted(Path(data_root).glob("*.json")):
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if artifact.get("model_policy", {}).get("fallback_from") != "fcff_dcf":
            continue
        issuer = artifact.get("issuer", {})
        ticker = str(issuer.get("ticker") or "").upper()
        cik = str(issuer.get("cik") or "")
        if not ticker or ticker != path.stem.upper() or not cik:
            continue
        cases.append(
            LegacyFcffCase(
                ticker=ticker,
                cik=cik,
                valuation_date=str(artifact.get("valuation_date") or ""),
                missing_fields=missing_bridge_fields(artifact),
                path=path,
                artifact=artifact,
            )
        )
    return cases


def controlling_filing_record(
    submissions: Mapping[str, Any], accession: str
) -> dict[str, str]:
    """Return exact filing metadata for an accession or fail closed."""
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    if accession not in accessions:
        raise ValueError(f"Controlling SEC accession not found: {accession}")
    index = accessions.index(accession)

    def value(key: str) -> str:
        values = recent.get(key, [])
        return str(values[index]) if index < len(values) and values[index] else ""

    record = {
        "accession": accession,
        "form": value("form"),
        "report_date": value("reportDate"),
        "filing_date": value("filingDate"),
        "primary_document": value("primaryDocument"),
    }
    if not all(record.values()):
        raise ValueError(f"Controlling SEC filing metadata is incomplete: {accession}")
    return record


def recovery_source_metadata(
    *, ticker: str, cik: str, filing: Mapping[str, str]
) -> dict[str, str]:
    """Build extractor metadata tied to one exact SEC primary document."""
    cik_digits = "".join(character for character in str(cik) if character.isdigit())
    accession_digits = "".join(
        character for character in filing["accession"] if character.isdigit()
    )
    source_url = (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(cik_digits)}/{accession_digits}/{filing['primary_document']}"
    )
    return {
        "ticker": ticker.upper(),
        "cik": cik_digits.zfill(10),
        "form": filing["form"],
        "period_end": filing["report_date"],
        "filing_date": filing["filing_date"],
        "source_accession": filing["accession"],
        "source_url": source_url,
    }


def relevant_filing_evidence(
    records: Iterable[Mapping[str, Any]], missing_fields: Iterable[str]
) -> list[dict[str, Any]]:
    """Keep evidence scoped to fields the fresh candidate actually lacks."""
    materialized = [dict(record) for record in records]
    requested = set(missing_fields)
    if requested & {"finance_lease_current", "finance_lease_noncurrent"}:
        requested.add("finance_lease_total")
    requested -= set(conflicting_resolved_evidence_fields(materialized))
    return [record for record in materialized if record.get("field") in requested]


def conflicting_resolved_evidence_fields(
    records: Iterable[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Identify fields with multiple incompatible resolved parser values."""
    values: dict[str, set[float]] = {}
    for record in records:
        value = record.get("value")
        if (
            record.get("status") != "resolved"
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
        ):
            continue
        values.setdefault(str(record.get("field") or ""), set()).add(float(value))
    return tuple(sorted(field for field, observed in values.items() if field and len(observed) > 1))


def evaluate_recovery_candidate(
    private: Mapping[str, Any], public: Mapping[str, Any]
) -> RecoveryDecision:
    """Accept only complete, valued FCFF candidates with no fallback residue."""
    reasons: list[str] = []
    private_policy = private.get("model_policy", {})
    public_policy = public.get("model_policy", {})
    if (
        private_policy.get("fallback_from") == "fcff_dcf"
        or public_policy.get("fallback_from") == "fcff_dcf"
    ):
        reasons.append("legacy_fallback")
    if private_policy.get("primary") != "fcff_dcf" or public_policy.get("primary") != "fcff_dcf":
        reasons.append("not_fcff_primary")

    bridge = private.get("financials", {}).get("balance_sheet", {})
    if not bridge.get("bridge_complete") or bridge.get("bridge_missing_fields"):
        reasons.append("bridge_incomplete")

    if public.get("review", {}).get("publication_state") == "withheld":
        reasons.append("public_withheld")
    model = public.get("models", {}).get("fcff_dcf", {})
    if model.get("intrinsic_value_per_share") is None:
        reasons.append("missing_intrinsic_value")
    if model.get("publication_state") == "withheld":
        reasons.append("model_withheld")
    for scenario in public.get("scenarios", {}).values():
        scenario_model = scenario.get("fcff_dcf", {}) if isinstance(scenario, Mapping) else {}
        if scenario_model.get("publication_state") == "withheld":
            reasons.append("scenario_withheld")
            break

    unique_reasons = tuple(dict.fromkeys(reasons))
    return RecoveryDecision(accepted=not unique_reasons, reasons=unique_reasons)
