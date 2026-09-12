"""Build a fail-closed public record when a current valuation is unavailable.

The builder is deliberately separate from the refresh job.  It does not
capture, publish, or activate anything.  It turns a prior public artifact into
a current withheld record while retaining the prior filing only as an
explicitly historical reference.  A supplied source packet is reference-only
evidence and is accepted only after its submission identity is checked.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Mapping

from .artifacts import sanitize_public_artifact


class UnavailableRecordError(ValueError):
    """Raised when a withheld record or current source reference is invalid."""


_DEFAULT_MODEL_VERSION = "FINSIGHT-UNAVAILABLE-REVALIDATION-1"


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnavailableRecordError(f"{field} is missing")
    return value.strip()


def _iso(value: Any, field: str) -> str:
    raw = _text(value, field)
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise UnavailableRecordError(f"{field} is not an ISO date") from exc
    return raw


def _cik(value: Any, field: str = "CIK") -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise UnavailableRecordError(f"{field} is missing")
    raw = str(value).strip()
    if not raw:
        raise UnavailableRecordError(f"{field} is missing")
    if not raw.isdigit() or len(raw) > 10:
        raise UnavailableRecordError(f"{field} is invalid")
    return raw.zfill(10)


def _payload(source_packet: Mapping[str, Any]) -> Mapping[str, Any]:
    packet = source_packet.get("packet")
    if isinstance(packet, Mapping):
        return packet
    return source_packet


def _recent_rows(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent") if isinstance(submissions.get("filings"), Mapping) else None
    if not isinstance(recent, Mapping):
        raise UnavailableRecordError("source packet submissions.recent is missing")
    accessions = recent.get("accessionNumber")
    if not isinstance(accessions, list):
        raise UnavailableRecordError("source packet accession history is missing")
    rows: list[dict[str, Any]] = []
    for index in range(len(accessions)):
        rows.append({key: values[index] for key, values in recent.items() if isinstance(values, list) and index < len(values)})
    return rows


def _verified_source_reference(
    source_packet: Mapping[str, Any],
    *,
    expected_ticker: str,
    expected_cik: str,
    cutoff: str,
) -> dict[str, Any]:
    outer_cik = source_packet.get("cik")
    if outer_cik is not None and _cik(outer_cik, "source packet CIK") != expected_cik:
        raise UnavailableRecordError("source packet CIK mismatch")
    outer_ticker = source_packet.get("ticker")
    if outer_ticker is not None and str(outer_ticker) != expected_ticker:
        raise UnavailableRecordError("source packet ticker mismatch")
    payload = _payload(source_packet)
    packet_cutoff = payload.get("cutoff")
    if packet_cutoff is not None and _iso(packet_cutoff, "source packet cutoff") != cutoff:
        raise UnavailableRecordError("source packet cutoff mismatch")
    packet_ticker = payload.get("ticker") or payload.get("issuer", {}).get("ticker")
    if packet_ticker is not None and str(packet_ticker) != expected_ticker:
        raise UnavailableRecordError("source packet ticker mismatch")
    submissions = payload.get("submissions")
    if not isinstance(submissions, Mapping):
        raise UnavailableRecordError("source packet submissions are missing")
    submissions_cik = _cik(submissions.get("cik"), "source submissions CIK")
    if submissions_cik != expected_cik:
        raise UnavailableRecordError("source submissions CIK mismatch")
    companyfacts = payload.get("companyfacts")
    if isinstance(companyfacts, Mapping) and companyfacts.get("cik") is not None:
        if _cik(companyfacts.get("cik"), "source companyfacts CIK") != expected_cik:
            raise UnavailableRecordError("source companyfacts CIK mismatch")
    controlling = payload.get("controlling_filing")
    if not isinstance(controlling, Mapping):
        raise UnavailableRecordError("source controlling filing is missing")
    accession = _text(controlling.get("accession") or controlling.get("accessionNumber"), "source accession")
    filed_date = _iso(controlling.get("filed") or controlling.get("filingDate"), "source filed date")
    report_date = _iso(controlling.get("reportDate") or controlling.get("report_date"), "source report date")
    form = _text(controlling.get("form"), "source form")
    primary_document = _text(controlling.get("primaryDocument") or controlling.get("primary_document"), "source primary document")
    if filed_date > cutoff:
        raise UnavailableRecordError("source filing is after cutoff")
    if report_date > filed_date:
        raise UnavailableRecordError("source reporting period is after filing date")
    if form not in {'10-Q', '10-Q/A', '10-K', '10-K/A'}:
        raise UnavailableRecordError("source is not a supported financial filing")
    matches = [row for row in _recent_rows(submissions) if row.get("accessionNumber") == accession]
    if len(matches) != 1:
        raise UnavailableRecordError("source accession is not uniquely present in submissions")
    row = matches[0]
    expected = {
        "form": form,
        "filingDate": filed_date,
        "reportDate": report_date,
        "primaryDocument": primary_document,
    }
    if any(row.get(key) != value for key, value in expected.items()):
        raise UnavailableRecordError("source controlling filing disagrees with submissions")
    return {
        "form": form,
        "period_end": report_date,
        "filed_date": filed_date,
        "accession": accession,
        "note": "Current source reference verified from the supplied packet; no URL inferred or published.",
    }


def _historical_reference(previous: Mapping[str, Any]) -> dict[str, Any]:
    source = previous.get("source_financial_statement")
    if not isinstance(source, Mapping):
        return {"note": "No prior successful source reference was present."}
    result = {key: deepcopy(source[key]) for key in ("form", "period_end", "filed_date", "accession", "url") if key in source}
    result["note"] = "Historical last successful reference only; not current evidence for this unavailable record."
    return result


def build_unavailable_public_record(
    previous_public: Mapping[str, Any],
    reason: str,
    cutoff: str,
    *,
    source_packet: Mapping[str, Any] | None = None,
    cik: str | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    """Return a sanitized current withheld record without mutating ``previous_public``."""

    if not isinstance(previous_public, Mapping):
        raise UnavailableRecordError("previous public record is missing")
    reason = _text(reason, "unavailability reason")
    cutoff = _iso(cutoff, "cutoff")
    previous = deepcopy(dict(previous_public))
    issuer = previous.get("issuer") if isinstance(previous.get("issuer"), Mapping) else {}
    ticker = _text(previous.get("ticker") or issuer.get("ticker"), "ticker")
    expected_cik = _cik(cik or previous.get("issuer", {}).get("cik"), "issuer CIK")
    if model_version is not None:
        model_version = _text(model_version, "model version")
    current_source = None
    if source_packet is not None:
        if not isinstance(source_packet, Mapping):
            raise UnavailableRecordError("source packet must be an object")
        current_source = _verified_source_reference(
            source_packet,
            expected_ticker=ticker,
            expected_cik=expected_cik,
            cutoff=cutoff,
        )
    source = current_source or _historical_reference(previous)
    source_note = source.get("note", "")
    unavailable_reason = f"Unavailable as of {cutoff}: {reason}"
    value: dict[str, Any] = {
        "schema_version": "US-PUBLIC-VALUATION-1.2",
        "valuation_date": cutoff,
        "assumption_date": cutoff,
        "model_version": model_version or _DEFAULT_MODEL_VERSION,
        "market": previous.get("market", "US"),
        "currency": previous.get("currency", "USD"),
        "ticker": ticker,
        "issuer": {**deepcopy(dict(issuer)), "cik": expected_cik, "ticker": ticker, "source_accessions": ([current_source["accession"]] if current_source else [])},
        "source_financial_statement": source,
        "model_policy": {
            "primary": "conditional_estimate",
            "supporting": [],
            "blend_models": False,
            "reason": unavailable_reason,
        },
        "public_assumptions": {
            "forecast_mode": "unavailable_current_source_revalidation_required",
            "normalization_basis": "current_unavailable_source_revalidation_required",
            "assumption_source_mix": ("source_identity_verified_economic_estimate_unavailable" if current_source else "current_source_not_verified"),
        },
        "models": {
            "conditional_estimate": {
                "model": "conditional_estimate",
                "output_type": "conditional_value_per_share",
                "currency": previous.get("currency", "USD"),
                "conditional_value_per_share": None,
                "publication_state": "withheld",
                "errors": ["CURRENT_VALUATION_UNAVAILABLE"],
                "warnings": [unavailable_reason],
            }
        },
        "scenarios": {},
        "scenario_range": {"low": None, "base": None, "high": None, "label": "withheld; no current numeric valuation"},
        "sensitivities": [],
        "forecast_quality": {"policy_version": model_version or _DEFAULT_MODEL_VERSION, "status": "withheld", "errors": ["CURRENT_VALUATION_UNAVAILABLE"], "warnings": [unavailable_reason], "checks": {}},
        "review": {
            "publication_state": "withheld",
            "confidence_grade": "unavailable",
            "errors": ["CURRENT_VALUATION_UNAVAILABLE"],
            "warnings": [unavailable_reason, source_note] if source_note else [unavailable_reason],
            "price_dependent_inputs_used": False,
            "prohibited_output_check": {"current_price": False, "upside_downside": False, "buy_hold_sell": False, "trading_multiples": False},
        },
        "availability_type": "not_available",
        "primary_valuation_method": "conditional_estimate",
        "confidence": {"label": None, "reasons": ["CURRENT_SOURCE_UNAVAILABLE"]},
        "reliability": {"label": "Unavailable", "reasons": ["CURRENT_SOURCE_UNAVAILABLE"]},
        "methodology": {"forecast_policy": model_version or _DEFAULT_MODEL_VERSION, "sector_framework": "unavailable_current_source", "source_policy": "Current valuation withheld until source identity and economic inputs are revalidated."},
        "data_boundary": {"raw_financial_statement_values_included": False, "stock_prices_used": False, "public_payload_contains": "withheld state and source-reference status only"},
    }
    return sanitize_public_artifact(value)


__all__ = ["UnavailableRecordError", "build_unavailable_public_record"]
