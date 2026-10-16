"""Fail-closed automated review and bounded repair orchestration.

This module does not invent financial facts. It classifies the current artifact,
describes permitted repair actions, and optionally reruns a caller-supplied
repair function until the artifact passes or no progress is made.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable


REVIEW_VERSION = "US-AUTO-REVIEW-1.0"

_HARD_WARNING_MARKERS = (
    "manual review is required",
    "terminal value exceeds 85%",
    "negative dcf intrinsic value",
    "non-positive dcf intrinsic value",
    "fallback",
    "bridge incomplete",
    "withheld",
)


def repair_provenance_from_submissions(
    artifact: dict[str, Any], submissions: dict[str, Any]
) -> dict[str, Any]:
    """Repair a source record using an already-fetched SEC submissions payload."""
    repaired = deepcopy(artifact)
    source = repaired.setdefault("source_financial_statement", {})
    recent = submissions.get("filings", {}).get("recent", {})
    accession = source.get("accession")
    accessions = recent.get("accessionNumber", [])
    index = accessions.index(accession) if accession in accessions else None
    if index is None:
        return repaired

    def value(name: str) -> Any:
        values = recent.get(name, [])
        return values[index] if index < len(values) else None

    cik = str(submissions.get("cik") or repaired.get("issuer", {}).get("cik") or "")
    cik_digits = "".join(character for character in cik if character.isdigit()).lstrip("0") or "0"
    document = value("primaryDocument")
    if document:
        source["url"] = (
            f"https://www.sec.gov/Archives/edgar/data/{cik_digits}/"
            f"{accession.replace('-', '')}/{document}"
        )
    source["filed_date"] = value("filingDate") or source.get("filed_date")
    source["period_end"] = value("reportDate") or source.get("period_end")
    source["form"] = value("form") or source.get("form")
    return repaired


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def discover_issuers(data_root: str | Path) -> list[dict[str, str]]:
    """Discover valid issuer identities from generated public artifacts."""
    root = Path(data_root)
    issuers: list[dict[str, str]] = []
    for path in sorted(root.glob("*.json")):
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        issuer = artifact.get("issuer")
        if not isinstance(issuer, dict):
            continue
        ticker = str(issuer.get("ticker") or "").upper()
        cik = str(issuer.get("cik") or "")
        if not ticker or ticker != path.stem.upper() or not cik or not issuer.get("issuer_name"):
            continue
        issuers.append({
            "ticker": ticker,
            "cik": cik,
            "short_name": str(issuer["issuer_name"]),
            "subsector": str(issuer.get("finsight_sector") or "unknown"),
        })
    return issuers


def _source_check(artifact: dict[str, Any]) -> tuple[list[str], list[str], str]:
    source = artifact.get("source_financial_statement")
    if not isinstance(source, dict):
        return ["missing_sec_provenance"], ["refresh_sec_provenance"], "missing"

    url = str(source.get("url") or "")
    exact_url = "/Archives/edgar/data/" in url and url.endswith((".htm", ".html", ".txt"))
    required = (source.get("filed_date"), source.get("period_end"), source.get("accession"))
    if not exact_url or any(value in (None, "") for value in required):
        return ["weak_sec_provenance"], ["refresh_sec_provenance"], "incomplete"
    return [], [], "complete"


def _scenario_check(artifact: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    models = artifact.get("models", {})
    if not isinstance(models, dict) or not models:
        reasons.append("missing_model_outputs")
    for name, model in models.items():
        if not isinstance(model, dict):
            _add_reason(reasons, f"invalid_model_output:{name}")
            continue
        state = model.get("publication_state")
        if state not in {"pass", "review_required"}:
            _add_reason(reasons, f"invalid_model_state:{name}")
        if state == "withheld":
            _add_reason(reasons, f"model_not_pass:{name}")
        if model.get("intrinsic_value_per_share") is None:
            _add_reason(reasons, f"missing_model_value:{name}")

    scenarios = artifact.get("scenarios")
    if scenarios:
        for name, scenario in scenarios.items():
            if not isinstance(scenario, dict):
                _add_reason(reasons, f"invalid_scenario:{name}")
                continue
            for model_name, model in scenario.items():
                if not isinstance(model, dict):
                    _add_reason(reasons, f"invalid_scenario_output:{name}:{model_name}")
                    continue
                state = model.get("publication_state")
                if state not in {"pass", "review_required"}:
                    _add_reason(reasons, f"invalid_scenario_state:{name}:{model_name}")
                if state == "withheld":
                    _add_reason(reasons, f"scenario_not_pass:{name}:{model_name}")
    return reasons


def assess_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Assess a public artifact without changing it.

    ``approved`` means the artifact meets the automated publication gate. A
    warning that is not a hard blocker becomes ``approved_with_caveat``.
    """
    blocking: list[str] = []
    repair_actions: list[str] = []
    warnings: list[str] = []

    source_reasons, source_actions, evidence_status = _source_check(artifact)
    for reason in source_reasons:
        _add_reason(blocking, reason)
    for action in source_actions:
        _add_reason(repair_actions, action)

    issuer = artifact.get("issuer", {})
    confidence = issuer.get("classification_confidence") if isinstance(issuer, dict) else None
    if not isinstance(confidence, (int, float)):
        _add_reason(blocking, "missing_classification_confidence")
        _add_reason(repair_actions, "reclassify_issuer_or_switch_model")
    elif confidence < 0.8:
        warnings.append("Classification confidence is below the 0.80 review threshold.")
        _add_reason(repair_actions, "reclassify_issuer_or_switch_model")

    review = artifact.get("review", {})
    if not isinstance(review, dict):
        _add_reason(blocking, "missing_review_payload")
    else:
        if review.get("publication_state") == "withheld":
            _add_reason(blocking, "review_state_withheld")
        for error in review.get("errors", []) or []:
            _add_reason(blocking, f"review_error:{error}")
        for warning in review.get("warnings", []) or []:
            warning_text = str(warning)
            source_bound_negated_owner = False
            if artifact.get('model_version') == 'US-B06-B10-PUBLIC-COMMON-RI-1':
                try:
                    from .staged_batches0610_inheritance import source_bound_negated_owner_warning
                    source_bound_negated_owner = source_bound_negated_owner_warning(artifact,warning_text)
                except (ImportError,ValueError,KeyError,TypeError):
                    source_bound_negated_owner = False
            elif artifact.get('model_version') == 'US-B11-B15-PUBLIC-COMMON-RI-1':
                try:
                    from .staged_batches1115_inheritance import source_bound_negated_owner_warning
                    source_bound_negated_owner = source_bound_negated_owner_warning(artifact,warning_text)
                except (ImportError,ValueError,KeyError,TypeError):
                    source_bound_negated_owner = False
            if any(marker in warning_text.lower() for marker in _HARD_WARNING_MARKERS) and not source_bound_negated_owner:
                _add_reason(blocking, f"hard_warning:{warning_text}")
            else:
                warnings.append(warning_text)

    for reason in _scenario_check(artifact):
        _add_reason(blocking, reason)
        if reason.startswith("model_not_pass") or reason.startswith("missing_model_value"):
            _add_reason(repair_actions, "rebuild_valuation_models")

    if any(reason.startswith("hard_warning:") for reason in blocking):
        _add_reason(repair_actions, "resolve_model_warnings")

    if blocking:
        decision = "blocked"
        publication_state = "withheld"
    elif warnings:
        decision = "approved_with_caveat"
        publication_state = "review_required"
    else:
        decision = "approved"
        publication_state = "pass"

    return {
        "review_version": REVIEW_VERSION,
        "decision": decision,
        "publication_state": publication_state,
        "evidence_status": evidence_status,
        "blocking_reasons": blocking,
        "repair_actions": repair_actions,
        "warnings": warnings,
    }


def _fingerprint(artifact: dict[str, Any]) -> str:
    payload = json.dumps(artifact, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_repair_loop(
    artifact: dict[str, Any],
    *,
    repair: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    max_attempts: int = 3,
) -> dict[str, Any]:
    """Run a bounded repair callback until the artifact passes or stalls."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    current = deepcopy(artifact)
    assessment = assess_artifact(current)
    attempts: list[dict[str, Any]] = []
    for attempt_number in range(1, max_attempts + 1):
        if assessment["decision"] in {"approved", "approved_with_caveat"}:
            break
        before = _fingerprint(current)
        repaired = repair(deepcopy(current), assessment)
        if not isinstance(repaired, dict):
            attempts.append({
                "attempt": attempt_number,
                "status": "invalid_repair",
                "blocking_reasons": assessment["blocking_reasons"],
            })
            break
        after = _fingerprint(repaired)
        if after == before:
            attempts.append({
                "attempt": attempt_number,
                "status": "no_progress",
                "blocking_reasons": assessment["blocking_reasons"],
            })
            break
        current = repaired
        next_assessment = assess_artifact(current)
        attempts.append({
            "attempt": attempt_number,
            "status": "repaired",
            "blocking_reasons_before": assessment["blocking_reasons"],
            "decision_after": next_assessment["decision"],
        })
        assessment = next_assessment

    return {
        "artifact": current,
        "assessment": assessment,
        "repair_attempts": attempts,
        "review_version": REVIEW_VERSION,
    }
