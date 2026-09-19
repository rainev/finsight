"""Explicit, source-bound cash-only bridge scope.

This module is intentionally standalone.  It does not decide whether cash is
economically excess, project debt, infer NCI, or add any investment security.
It only proves that an already-approved private cash-only scope can be carried
to a current filing through the same reported cash concept.
"""

from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "FINSIGHT-APPROVED-CASH-ONLY-SCOPE-1"
PROFILE_NAME = "cash_only"
DEFAULT_CASH_QNAME = "us-gaap:CashAndCashEquivalentsAtCarryingValue"
DEFAULT_UNIT = "USD"
_SCENARIOS = ("bear", "base", "bull")


class CashOnlyScopeError(ValueError):
    """The requested scope or source package cannot be proven."""


def _cik(value: Any) -> str:
    text = str(value or "").strip()
    if not text.isdigit() or len(text) > 10:
        raise CashOnlyScopeError("issuer CIK is invalid")
    return text.zfill(10)


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise CashOnlyScopeError(f"{field} must be a finite number")
    return float(value)


def _same_number(left: Any, right: Any, field: str) -> bool:
    return math.isclose(_number(left, field), _number(right, field), rel_tol=0.0, abs_tol=0.0)


def _project_root(project_root: str | Path | None) -> Path:
    if project_root is not None:
        return Path(project_root).expanduser().resolve()
    # backend/app/us_valuation/<this file> -> worktree root
    return Path(__file__).resolve().parents[3]


def _metadata_map(value: Any) -> dict[str, Any]:
    if not isinstance(value, list):
        raise CashOnlyScopeError("current cash package filing metadata is missing")
    result: dict[str, Any] = {}
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != 2 or not isinstance(row[0], str):
            raise CashOnlyScopeError("current cash package filing metadata is invalid")
        result[row[0]] = row[1]
    required = {
        "accession",
        "form",
        "primary_document",
        "package_generation",
        "manifest_version",
        "primary_source_url",
        "retrieved_at_epoch",
        "resource_count",
        "total_bytes",
        "filed_date",
        "report_date",
    }
    missing = sorted(key for key in required if result.get(key) in (None, ""))
    if missing:
        raise CashOnlyScopeError("current cash package filing metadata is incomplete: " + ", ".join(missing))
    return result


def _requested_profile(requested_profile: Any) -> Mapping[str, Any]:
    if isinstance(requested_profile, str):
        if requested_profile != PROFILE_NAME:
            raise CashOnlyScopeError("cash-only scope requires an explicit cash_only profile")
        return {"name": PROFILE_NAME}
    if not isinstance(requested_profile, Mapping) or requested_profile.get("name") != PROFILE_NAME:
        raise CashOnlyScopeError("cash-only scope requires an explicit cash_only profile")
    return requested_profile


def _private_packet(recipe: Mapping[str, Any], *, project_root: str | Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    provenance = recipe.get("provenance")
    if not isinstance(provenance, Mapping):
        raise CashOnlyScopeError("recipe private provenance is missing")
    source_path = provenance.get("source_path")
    expected_hash = provenance.get("private_sha256")
    if not isinstance(source_path, str) or not source_path:
        raise CashOnlyScopeError("recipe private provenance source path is missing")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise CashOnlyScopeError("recipe private provenance hash is missing")
    root = _project_root(project_root)
    path = Path(source_path).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    output_root = (root / "output").resolve()
    try:
        path.relative_to(output_root)
    except ValueError as exc:
        raise CashOnlyScopeError("recipe private provenance source must be inside project output") from exc
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CashOnlyScopeError("recipe private provenance source is unavailable") from exc
    actual_hash = sha256(raw).hexdigest()
    if actual_hash != expected_hash.lower():
        raise CashOnlyScopeError("recipe private provenance hash mismatch")
    try:
        import json

        packet = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise CashOnlyScopeError("recipe private provenance source is not valid JSON") from exc
    if not isinstance(packet, dict):
        raise CashOnlyScopeError("recipe private provenance source is not an object")
    return packet, {"source_path": str(path), "sha256": actual_hash}


def _issuer_identity(recipe: Mapping[str, Any], packet: Mapping[str, Any]) -> tuple[str, str]:
    recipe_ticker = recipe.get("ticker")
    issuer = packet.get("issuer")
    if not isinstance(recipe_ticker, str) or not isinstance(issuer, Mapping):
        raise CashOnlyScopeError("recipe/private issuer identity is missing")
    ticker = issuer.get("ticker")
    if ticker != recipe_ticker:
        raise CashOnlyScopeError("recipe/private issuer ticker conflict")
    cik = _cik(issuer.get("cik"))
    history = packet.get("history_backed")
    if not isinstance(history, Mapping) or history.get("ticker") != ticker:
        raise CashOnlyScopeError("private history issuer identity is missing or mismatched")
    return ticker, cik


def _private_cash_scope(recipe: Mapping[str, Any], packet: Mapping[str, Any], *, qname: str, unit: str) -> dict[str, Any]:
    history = packet.get("history_backed")
    if not isinstance(history, Mapping):
        raise CashOnlyScopeError("private history-backed packet is missing")
    ledger = history.get("source_ledger")
    if not isinstance(ledger, Mapping):
        raise CashOnlyScopeError("private source ledger is missing")
    bridge = ledger.get("bridge_reconciliation")
    rows = ledger.get("bridge_sources")
    if not isinstance(bridge, Mapping) or not isinstance(rows, list):
        raise CashOnlyScopeError("private cash bridge provenance is incomplete")
    cash_rows = [row for row in rows if isinstance(row, Mapping) and row.get("concept") == qname]
    if len(cash_rows) != 1:
        raise CashOnlyScopeError("private cash scope requires one sole reported cash-qname source")
    row = cash_rows[0]
    if row.get("unit") != unit or row.get("dimensions", []) not in ([], None):
        raise CashOnlyScopeError("private cash source unit or dimensions are not exact")
    if row.get("reported_vs_estimated") != "reported":
        raise CashOnlyScopeError("private cash source is not reported evidence")
    cash_value = _number(row.get("value"), "private cash source")
    if cash_value < 0:
        raise CashOnlyScopeError("private cash source cannot be negative")
    bridge_value = _number(bridge.get("cash_and_investments"), "private bridge cash")
    if not _same_number(cash_value, bridge_value, "private cash bridge"):
        raise CashOnlyScopeError("private bridge cash does not equal the sole cash source")
    scenarios = recipe.get("scenarios")
    if not isinstance(scenarios, Mapping) or set(scenarios) != set(_SCENARIOS):
        raise CashOnlyScopeError("recipe must contain bear, base, and bull scenarios")
    for name in _SCENARIOS:
        inputs = scenarios[name].get("inputs") if isinstance(scenarios[name], Mapping) else None
        if not isinstance(inputs, Mapping) or "cash_and_investments" not in inputs:
            raise CashOnlyScopeError(f"recipe {name} cash input is missing")
        if not _same_number(inputs["cash_and_investments"], bridge_value, f"recipe {name} cash input"):
            raise CashOnlyScopeError(f"recipe {name} cash input is not approved private cash")
    return {
        "qname": qname,
        "unit": unit,
        "value": cash_value,
        "accession": row.get("accession"),
        "period_end": row.get("period_end"),
        "filed": row.get("filed"),
        "source_kind": row.get("source_kind"),
    }


def compile_approved_cash_only_scope(
    recipe: Mapping[str, Any],
    *,
    requested_profile: Any,
    cash_qname: str = DEFAULT_CASH_QNAME,
    unit: str = DEFAULT_UNIT,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Compile a cash-only scope only when explicitly requested by the caller."""
    profile = _requested_profile(requested_profile)
    if cash_qname != profile.get("cash_qname", cash_qname) or unit != profile.get("unit", unit):
        raise CashOnlyScopeError("requested cash-only profile conflicts with source selector")
    packet, provenance = _private_packet(recipe, project_root=project_root)
    ticker, cik = _issuer_identity(recipe, packet)
    cash = _private_cash_scope(recipe, packet, qname=cash_qname, unit=unit)
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": PROFILE_NAME,
        "ticker": ticker,
        "cik": cik,
        "cash_qname": cash_qname,
        "unit": unit,
        "private_cash": cash,
        "private_provenance": provenance,
        "excluded": {
            "other_investments": "unknown_outside_scope_not_zero",
            "restricted_cash": "unknown_outside_scope_not_zero",
        },
        "limitations": [
            "Uses cash and cash equivalents only.",
            "Other investments and restricted cash remain outside scope and are not asserted to be zero.",
            "Debt and noncontrolling interests are intentionally not projected by this helper.",
        ],
    }


def _unwrap_package(package: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    parsed = package.get("parsed")
    if isinstance(parsed, Mapping):
        return package, parsed
    return package, package


def _package_identity(
    outer: Mapping[str, Any],
    parsed: Mapping[str, Any],
    *,
    current_accession: str,
    expected_period_end: str,
    expected_cik: str,
) -> dict[str, Any]:
    metadata = _metadata_map(parsed.get("filing_metadata"))
    if metadata.get("accession") != current_accession or parsed.get("source_accession") != current_accession:
        raise CashOnlyScopeError("current cash package accession does not match requested accession")
    if metadata.get("form") not in {"10-K", "10-Q"} or parsed.get("form") != metadata.get("form"):
        raise CashOnlyScopeError("current cash package report form identity is invalid")
    if metadata.get("report_date") != parsed.get("report_date") or metadata.get("report_date") != expected_period_end:
        raise CashOnlyScopeError("current cash package report period does not match requested period")
    outer_accession = outer.get("accession")
    if outer_accession is not None and outer_accession != current_accession:
        raise CashOnlyScopeError("current cash package wrapper accession does not match")
    outer_form = outer.get("form")
    if outer_form is not None and outer_form != metadata.get("form"):
        raise CashOnlyScopeError("current cash package wrapper form does not match")
    outer_report = outer.get("report_date")
    if outer_report is not None and outer_report != expected_period_end:
        raise CashOnlyScopeError("current cash package wrapper report period does not match")
    outer_cik = outer.get("cik")
    if outer_cik is not None and _cik(outer_cik) != expected_cik:
        raise CashOnlyScopeError("current cash package CIK does not match approved scope")
    return metadata


def bind_current_cash_only_scope(
    scope: Mapping[str, Any],
    package: Mapping[str, Any],
    *,
    current_accession: str,
    cik: str,
    period_end: str,
    unit: str = DEFAULT_UNIT,
    current_form: str | None = None,
) -> dict[str, Any]:
    """Bind the same reported cash concept from an exact current package."""
    if scope.get("schema_version") != SCHEMA_VERSION or scope.get("profile") != PROFILE_NAME:
        raise CashOnlyScopeError("cash-only scope is not a compiled approved scope")
    expected_cik = _cik(cik)
    if scope.get("cik") != expected_cik:
        raise CashOnlyScopeError("requested CIK does not match approved scope")
    approved_qname = scope.get("cash_qname")
    if not isinstance(approved_qname, str) or not approved_qname or scope.get("unit") != unit:
        raise CashOnlyScopeError("current cash selector conflicts with approved scope")
    outer, parsed = _unwrap_package(package)
    facts = parsed.get("facts")
    if not isinstance(facts, list):
        raise CashOnlyScopeError("current cash package facts are missing")
    metadata = _package_identity(
        outer,
        parsed,
        current_accession=current_accession,
        expected_period_end=period_end,
        expected_cik=expected_cik,
    )
    if current_form is not None and metadata.get("form") != current_form:
        raise CashOnlyScopeError("current cash package form does not match requested form")
    matches = []
    for fact in facts:
        if not isinstance(fact, Mapping) or fact.get("qname") != approved_qname:
            continue
        if fact.get("period_end") != period_end or fact.get("unit") != unit:
            continue
        if fact.get("period_start") not in (None, ""):
            raise CashOnlyScopeError("current cash fact is duration-based, not instantaneous")
        if fact.get("dimensions") not in ([], None) or fact.get("typed_dimensions") not in ([], None):
            raise CashOnlyScopeError("current cash fact has dimensions")
        if fact.get("source_accession") != current_accession:
            raise CashOnlyScopeError("current cash fact accession does not match requested accession")
        if fact.get("entity_scheme") != "http://www.sec.gov/CIK" or fact.get("entity_identifier") in (None, ""):
            raise CashOnlyScopeError("current cash fact entity identity is missing or invalid")
        if _cik(fact.get("entity_identifier")) != expected_cik:
            raise CashOnlyScopeError("current cash fact entity identity does not match")
        matches.append(fact)
    if not matches:
        raise CashOnlyScopeError("current package has no exact undimensioned cash fact")
    values = {_number(fact.get("value"), "current cash fact") for fact in matches}
    if len(values) != 1:
        raise CashOnlyScopeError("current package has conflicting exact cash facts")
    value = next(iter(values))
    if value < 0:
        raise CashOnlyScopeError("current cash fact cannot be negative")
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": PROFILE_NAME,
        "ticker": scope.get("ticker"),
        "cik": expected_cik,
        "cash_and_cash_equivalents": value,
        "source": {
            "accession": current_accession,
            "period_end": period_end,
            "qname": approved_qname,
            "unit": unit,
            "dimensions": [],
            "reported_vs_estimated": "reported",
            "duplicate_exact_fact_count": len(matches),
        },
        "private_provenance": scope["private_provenance"],
        "excluded": dict(scope["excluded"]),
        "limitations": list(scope["limitations"]),
    }
