"""Read-only diagnostics for replaying evidence-aware bridge policy."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from .bridge_policy import (
    BridgeAssessment,
    BridgeResolution,
    reconcile_bridge,
)
from .field_availability import (
    FieldAvailability,
    availability_from_normalized_field,
)


_PRIVATE_SCHEMA_VERSION = "US-VALUATION-RESULT-1.0"
_CANONICAL_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")
_LEASE_COMPONENTS = ("finance_lease_current", "finance_lease_noncurrent")
_LEGACY_AGGREGATE_ALIASES = frozenset({"total_interest_bearing_debt"})
_DIAGNOSTIC_DECISIONS = ("bounded_candidate", "complete", "withheld")


class ArtifactEvaluationError(ValueError):
    """A deterministic private-artifact validation failure."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def _require_mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtifactEvaluationError(
            "PRIVATE_ARTIFACT_SCHEMA_INVALID", f"{field} must be a mapping"
        )
    return value


def _require_nonempty_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactEvaluationError(
            "PRIVATE_ARTIFACT_SCHEMA_INVALID", f"{field} must be nonempty"
        )
    return value


def _canonical_ticker(artifact: Mapping[str, Any]) -> str:
    issuer = _require_mapping(artifact.get("issuer"), "issuer")
    ticker = issuer.get("ticker")
    top_level_ticker = artifact.get("ticker")
    if top_level_ticker is not None and top_level_ticker != ticker:
        raise ArtifactEvaluationError(
            "TICKER_MISMATCH", "top-level and issuer tickers must agree"
        )
    ticker = _require_nonempty_text(ticker, "issuer.ticker")
    if not _CANONICAL_TICKER.fullmatch(ticker):
        raise ArtifactEvaluationError(
            "INVALID_TICKER", "issuer.ticker must be a canonical uppercase symbol"
        )
    return ticker


def _legacy_summary(balance: Mapping[str, Any]) -> dict[str, Any]:
    bridge_complete = balance.get("bridge_complete")
    if not isinstance(bridge_complete, bool):
        raise ArtifactEvaluationError(
            "PRIVATE_ARTIFACT_SCHEMA_INVALID",
            "balance_sheet.bridge_complete must be a boolean",
        )
    raw_missing = balance.get("bridge_missing_fields")
    if not isinstance(raw_missing, (list, tuple)) or any(
        not isinstance(field, str) or not field.strip() for field in raw_missing
    ):
        raise ArtifactEvaluationError(
            "PRIVATE_ARTIFACT_SCHEMA_INVALID",
            "balance_sheet.bridge_missing_fields must be an array of fields",
        )
    return {
        "bridge_complete": bridge_complete,
        "bridge_missing_fields": sorted(set(raw_missing)),
    }


def _deserialize_modern_availability(
    raw_availability: object,
) -> dict[str, FieldAvailability]:
    availability_payload = _require_mapping(
        raw_availability, "balance_sheet.availability"
    )
    if not availability_payload:
        raise ArtifactEvaluationError(
            "AVAILABILITY_INVALID", "balance_sheet.availability must not be empty"
        )

    availability: dict[str, FieldAvailability] = {}
    try:
        for field in sorted(availability_payload):
            payload = _require_mapping(
                availability_payload[field], f"availability.{field}"
            )
            record = FieldAvailability.from_dict(payload)
            if record.field != field:
                raise ArtifactEvaluationError(
                    "AVAILABILITY_FIELD_MISMATCH",
                    f"availability key {field} does not match record field",
                )
            if record.as_dict() != dict(payload):
                raise ArtifactEvaluationError(
                    "AVAILABILITY_INVALID",
                    f"availability record {field} is not canonical",
                )
            availability[field] = record
    except ArtifactEvaluationError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise ArtifactEvaluationError(
            "AVAILABILITY_INVALID", f"invalid serialized availability: {error}"
        ) from error
    return availability


def _reconstruct_legacy_availability(
    balance: Mapping[str, Any], period_end: str
) -> dict[str, FieldAvailability]:
    values = _require_mapping(balance.get("values"), "balance_sheet.values")
    sources = _require_mapping(balance.get("sources"), "balance_sheet.sources")
    states = _require_mapping(
        balance.get("field_states"), "balance_sheet.field_states"
    )
    value_fields = set(values) - _LEGACY_AGGREGATE_ALIASES
    source_fields = set(sources) - _LEGACY_AGGREGATE_ALIASES
    state_fields = set(states) - _LEGACY_AGGREGATE_ALIASES
    if value_fields != source_fields or value_fields != state_fields:
        raise ArtifactEvaluationError(
            "LEGACY_FIELD_MAP_MISMATCH",
            "legacy values, sources, and field_states must have identical keys",
        )

    availability: dict[str, FieldAvailability] = {}
    try:
        for field in sorted(value_fields):
            raw_source = sources[field]
            if raw_source is not None and not isinstance(raw_source, Mapping):
                raise ArtifactEvaluationError(
                    "LEGACY_SOURCE_INVALID",
                    f"legacy source for {field} must be a mapping or null",
                )
            legacy_state = states[field]
            if not isinstance(legacy_state, str):
                raise ArtifactEvaluationError(
                    "LEGACY_STATE_INVALID",
                    f"legacy state for {field} must be text",
                )
            availability[field] = availability_from_normalized_field(
                field=field,
                value=values[field],
                source=raw_source,
                legacy_state=legacy_state,
                period_end=period_end,
                covered_fields=(
                    _LEASE_COMPONENTS if field == "finance_lease_total" else ()
                ),
            )
    except ArtifactEvaluationError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise ArtifactEvaluationError(
            "LEGACY_AVAILABILITY_INVALID",
            f"legacy availability reconstruction failed: {error}",
        ) from error
    return availability


def _validated_assessment(
    balance: Mapping[str, Any], resolution: BridgeResolution
) -> dict[str, Any] | None:
    if "bridge_uncertainty" not in balance:
        return None
    try:
        raw_assessment = _require_mapping(
            balance["bridge_uncertainty"], "balance_sheet.bridge_uncertainty"
        )
        assessment = BridgeAssessment.from_dict(raw_assessment)
    except ArtifactEvaluationError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise ArtifactEvaluationError(
            "BRIDGE_ASSESSMENT_INVALID",
            f"stored bridge assessment is invalid: {error}",
        ) from error
    if assessment.as_dict() != dict(raw_assessment):
        raise ArtifactEvaluationError(
            "BRIDGE_ASSESSMENT_INVALID",
            "stored bridge assessment is not canonical",
        )
    if (
        assessment.blocking_fields != resolution.blocking_fields
        or assessment.bounded_fields != resolution.bounded_fields
        or assessment.policy_version != resolution.policy_version
    ):
        raise ArtifactEvaluationError(
            "BRIDGE_ASSESSMENT_MISMATCH",
            "stored bridge assessment does not match the recomputed precheck",
        )
    return assessment.as_dict()


def _stored_precheck_match(
    balance: Mapping[str, Any], resolution: BridgeResolution
) -> bool | None:
    if "bridge_precheck" not in balance:
        return None
    try:
        raw_precheck = _require_mapping(
            balance["bridge_precheck"], "balance_sheet.bridge_precheck"
        )
        stored = BridgeResolution.from_dict(raw_precheck)
    except (ArtifactEvaluationError, KeyError, TypeError, ValueError):
        return False
    return (
        stored.as_dict() == dict(raw_precheck)
        and stored.as_dict() == resolution.as_dict()
    )


def _diagnostic_decision(resolution: BridgeResolution) -> str:
    if resolution.blocking_fields:
        return "withheld"
    if resolution.bounded_fields:
        return "bounded_candidate"
    return "complete"


def _field_evidence(
    availability: Mapping[str, FieldAvailability],
) -> dict[str, dict[str, Any]]:
    return {
        field: {
            "authority": record.authority,
            "covered_fields": list(record.covered_fields),
            "period_end": record.period_end,
            "reason_code": record.reason_code,
            "source_accession": record.source_accession,
            "state": record.state,
        }
        for field, record in sorted(availability.items())
    }


def _structural_candidate_present(artifact: Mapping[str, Any]) -> bool:
    diagnostics = artifact.get("structural_shadow_diagnostics")
    if not isinstance(diagnostics, Mapping):
        return False
    if diagnostics.get("publication_effect") != "none_shadow_only":
        return False
    decisions = diagnostics.get("decisions")
    return isinstance(decisions, list) and any(
        isinstance(decision, Mapping)
        and isinstance(decision.get("availability_candidate"), Mapping)
        and decision["availability_candidate"].get("authority") == "shadow"
        for decision in decisions
    )


def evaluate_private_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute bridge eligibility without changing the private artifact."""

    if not isinstance(artifact, Mapping):
        raise ArtifactEvaluationError(
            "PRIVATE_ARTIFACT_NOT_OBJECT", "private artifact must be an object"
        )
    snapshot = deepcopy(artifact)
    if artifact.get("schema_version") != _PRIVATE_SCHEMA_VERSION:
        raise ArtifactEvaluationError(
            "NOT_PRIVATE_VALUATION_ARTIFACT",
            f"schema_version must equal {_PRIVATE_SCHEMA_VERSION}",
        )

    ticker = _canonical_ticker(artifact)
    financials = _require_mapping(artifact.get("financials"), "financials")
    balance = _require_mapping(
        financials.get("balance_sheet"), "financials.balance_sheet"
    )
    period_end = _require_nonempty_text(
        balance.get("period_end"), "balance_sheet.period_end"
    )
    financial_period_end = artifact.get("financial_period_end")
    if financial_period_end is not None and financial_period_end != period_end:
        raise ArtifactEvaluationError(
            "FINANCIAL_PERIOD_MISMATCH",
            "financial_period_end must match balance_sheet.period_end",
        )

    legacy = _legacy_summary(balance)
    if "availability" in balance:
        source_schema = "modern"
        availability = _deserialize_modern_availability(balance["availability"])
    else:
        source_schema = "legacy"
        availability = _reconstruct_legacy_availability(balance, period_end)

    try:
        resolution = reconcile_bridge(
            availability,
            fully_diluted_shares=balance.get("fully_diluted_shares_proxy"),
        )
    except (TypeError, ValueError) as error:
        raise ArtifactEvaluationError(
            "BRIDGE_POLICY_VALIDATION_ERROR",
            f"bridge recomputation failed: {error}",
        ) from error

    stored_precheck_match = _stored_precheck_match(balance, resolution)
    assessment = (
        None
        if stored_precheck_match is False
        else _validated_assessment(balance, resolution)
    )
    decision = _diagnostic_decision(resolution)
    complete = resolution.complete
    can_value = resolution.can_value
    reason_codes = list(resolution.reason_codes)
    if stored_precheck_match is False:
        decision = "withheld"
        complete = False
        can_value = False
        reason_codes = ["BRIDGE_PRECHECK_MISMATCH"]

    field_state_counts = dict(
        sorted(Counter(record.state for record in availability.values()).items())
    )
    legacy_decision = "complete" if legacy["bridge_complete"] else "withheld"
    report = {
        "ticker": ticker,
        "financial_period_end": period_end,
        "source_schema": source_schema,
        "legacy": legacy,
        "evidence_aware": {
            "complete": complete,
            "can_value": can_value,
            "decision": decision,
            "blocking_fields": list(resolution.blocking_fields),
            "bounded_fields": list(resolution.bounded_fields),
            "reason_codes": reason_codes,
            "recomputed_precheck": resolution.as_dict(),
        },
        "bridge_uncertainty": assessment,
        "stored_precheck_match": stored_precheck_match,
        "field_state_counts": field_state_counts,
        "field_evidence": _field_evidence(availability),
        "structural_shadow_candidate_present": _structural_candidate_present(
            artifact
        ),
        "eligibility_changed": legacy_decision != decision,
        "serving_artifact_changed": False,
    }
    if artifact != snapshot:
        raise ArtifactEvaluationError(
            "ARTIFACT_MUTATED", "bridge shadow evaluation mutated its input"
        )
    return report


def _requested_tickers(tickers: Iterable[str]) -> tuple[str, ...]:
    if isinstance(tickers, (str, bytes)):
        raise ValueError("tickers must be an iterable of canonical uppercase symbols")
    normalized: set[str] = set()
    for ticker in tickers:
        if not isinstance(ticker, str) or not _CANONICAL_TICKER.fullmatch(ticker):
            raise ValueError("requested ticker must be a canonical uppercase symbol")
        normalized.add(ticker)
    return tuple(sorted(normalized))


def _path_ticker(path: Path) -> str:
    candidate = path.parent.name
    return candidate if _CANONICAL_TICKER.fullmatch(candidate) else "UNKNOWN"


def _candidate_ticker(payload: object, path: Path) -> str:
    if isinstance(payload, Mapping):
        issuer = payload.get("issuer")
        if isinstance(issuer, Mapping):
            ticker = issuer.get("ticker")
            if isinstance(ticker, str) and _CANONICAL_TICKER.fullmatch(ticker):
                return ticker
        ticker = payload.get("ticker")
        if isinstance(ticker, str) and _CANONICAL_TICKER.fullmatch(ticker):
            return ticker
    return _path_ticker(path)


def _error_case(
    *,
    ticker: str,
    source_path: str,
    reason_code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "financial_period_end": None,
        "source_schema": None,
        "legacy": {
            "bridge_complete": False,
            "bridge_missing_fields": [],
        },
        "evidence_aware": {
            "complete": False,
            "can_value": False,
            "decision": "withheld",
            "blocking_fields": [],
            "bounded_fields": [],
            "reason_codes": [reason_code],
            "recomputed_precheck": None,
        },
        "bridge_uncertainty": None,
        "stored_precheck_match": None,
        "field_state_counts": {},
        "field_evidence": {},
        "structural_shadow_candidate_present": False,
        "eligibility_changed": False,
        "serving_artifact_changed": False,
        "source_path": source_path,
        "valid_artifact": False,
        "error": {"reason_code": reason_code, "message": message},
    }


def _mark_case_invalid(
    case: dict[str, Any], *, reason_code: str, message: str
) -> None:
    evidence = case["evidence_aware"]
    evidence["complete"] = False
    evidence["can_value"] = False
    evidence["decision"] = "withheld"
    evidence["reason_codes"] = [reason_code]
    case["eligibility_changed"] = (
        case["legacy"]["bridge_complete"] is True
    )
    case["valid_artifact"] = False
    case["error"] = {"reason_code": reason_code, "message": message}


def _read_candidate(path: Path, source_path: str) -> tuple[str, object, dict[str, Any] | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        ticker = _path_ticker(path)
        return (
            ticker,
            None,
            _error_case(
                ticker=ticker,
                source_path=source_path,
                reason_code="MALFORMED_JSON",
                message=f"malformed JSON at line {error.lineno} column {error.colno}",
            ),
        )
    except (OSError, UnicodeError) as error:
        ticker = _path_ticker(path)
        return (
            ticker,
            None,
            _error_case(
                ticker=ticker,
                source_path=source_path,
                reason_code="INPUT_READ_ERROR",
                message=f"input could not be read: {type(error).__name__}",
            ),
        )
    ticker = _candidate_ticker(payload, path)
    if not isinstance(payload, Mapping):
        return (
            ticker,
            payload,
            _error_case(
                ticker=ticker,
                source_path=source_path,
                reason_code="PRIVATE_ARTIFACT_NOT_OBJECT",
                message="private artifact must be an object",
            ),
        )
    return ticker, payload, None


def _evaluate_candidate(
    *, ticker: str, payload: Mapping[str, Any], source_path: str
) -> dict[str, Any]:
    try:
        case = evaluate_private_artifact(payload)
    except ArtifactEvaluationError as error:
        return _error_case(
            ticker=ticker,
            source_path=source_path,
            reason_code=error.reason_code,
            message=str(error),
        )
    case["source_path"] = source_path
    case["valid_artifact"] = True
    case["error"] = None
    if case["stored_precheck_match"] is False:
        _mark_case_invalid(
            case,
            reason_code="BRIDGE_PRECHECK_MISMATCH",
            message="stored bridge precheck does not match recomputation",
        )
    return case


def _increment(counter: Counter[str], values: Iterable[str]) -> None:
    for value in values:
        counter[value] += 1


def evaluate_corpus(
    input_root: str | Path, tickers: Iterable[str] = ()
) -> dict[str, Any]:
    """Evaluate every selected private-artifact candidate exactly once."""

    requested = _requested_tickers(tickers)
    root = Path(input_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("input_root must resolve to a directory")
    candidates = sorted(
        (
            Path(directory) / name
            for directory, subdirectories, filenames in os.walk(
                root, followlinks=False
            )
            for name in (*subdirectories, *filenames)
            if name == "valuation-private.json"
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )

    selected: list[tuple[str, object, dict[str, Any] | None, str]] = []
    discovered_tickers: set[str] = set()
    for path in candidates:
        source_path = path.relative_to(root).as_posix()
        ticker, payload, error_case = _read_candidate(path, source_path)
        if requested and ticker not in requested:
            continue
        discovered_tickers.add(ticker)
        selected.append((ticker, payload, error_case, source_path))

    cases: list[dict[str, Any]] = []
    for ticker, payload, error_case, source_path in selected:
        if error_case is not None:
            cases.append(error_case)
            continue
        assert isinstance(payload, Mapping)
        cases.append(
            _evaluate_candidate(
                ticker=ticker,
                payload=payload,
                source_path=source_path,
            )
        )

    ticker_counts = Counter(case["ticker"] for case in cases)
    duplicate_tickers = sorted(
        ticker for ticker, count in ticker_counts.items() if count > 1
    )
    for case in cases:
        if case["ticker"] in duplicate_tickers:
            _mark_case_invalid(
                case,
                reason_code="DUPLICATE_TICKER",
                message="ticker appears in more than one candidate artifact",
            )

    cases.sort(key=lambda case: (case["ticker"], case["source_path"]))
    decision_counts = Counter({decision: 0 for decision in _DIAGNOSTIC_DECISIONS})
    blocker_frequencies: Counter[str] = Counter()
    bounded_field_frequencies: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    reason_code_frequencies: Counter[str] = Counter()
    for case in cases:
        evidence = case["evidence_aware"]
        decision_counts[evidence["decision"]] += 1
        _increment(blocker_frequencies, evidence["blocking_fields"])
        _increment(bounded_field_frequencies, evidence["bounded_fields"])
        for state, count in case["field_state_counts"].items():
            state_counts[state] += count
        _increment(reason_code_frequencies, evidence["reason_codes"])

    valid_artifact_count = sum(case["valid_artifact"] is True for case in cases)
    invalid_artifact_count = len(cases) - valid_artifact_count
    missing_tickers = sorted(set(requested) - discovered_tickers)
    serving_artifacts_changed = sum(
        case["serving_artifact_changed"] is True for case in cases
    )
    artifact_count = len(cases)
    return {
        "artifact_count": artifact_count,
        "valid_artifact_count": valid_artifact_count,
        "invalid_artifact_count": invalid_artifact_count,
        "decision_counts": dict(sorted(decision_counts.items())),
        "blocker_frequencies": dict(sorted(blocker_frequencies.items())),
        "bounded_field_frequencies": dict(
            sorted(bounded_field_frequencies.items())
        ),
        "state_counts": dict(sorted(state_counts.items())),
        "reason_code_frequencies": dict(
            sorted(reason_code_frequencies.items())
        ),
        "serving_artifacts_changed": serving_artifacts_changed,
        "requested_tickers": list(requested),
        "matched_tickers": sorted(discovered_tickers),
        "missing_tickers": missing_tickers,
        "duplicate_tickers": duplicate_tickers,
        "evidence_gate_passed": (
            artifact_count > 0
            and invalid_artifact_count == 0
            and not missing_tickers
            and not duplicate_tickers
            and serving_artifacts_changed == 0
        ),
        "cases": cases,
    }
