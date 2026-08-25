"""Deterministic, fail-closed automated review for public U.S. artifacts."""

from __future__ import annotations

from math import isfinite
from typing import Any


REVIEW_VERSION = "US-AUTO-REVIEW-1.0"

_PUBLICATION_STATES = {"pass", "review_required", "withheld"}
_HARD_WARNING_MARKERS = (
    "manual review is required",
    "terminal value exceeds 85%",
    "negative dcf intrinsic value",
    "non-positive dcf intrinsic value",
    "fallback",
    "bridge incomplete",
    "withheld",
)


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _is_hard_warning(message: str) -> bool:
    return any(marker in message.lower() for marker in _HARD_WARNING_MARKERS)


def _local_review_messages(
    value: dict[str, Any],
    *,
    context: str,
    identity: str,
    caveat_prefix: str,
) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    caveats: list[str] = []
    errors, error_problem = _review_messages(
        value.get("errors", []), f"invalid_{context}_errors:{identity}"
    )
    warnings, warning_problem = _review_messages(
        value.get("warnings", []), f"invalid_{context}_warnings:{identity}"
    )
    if error_problem:
        _add_reason(reasons, error_problem)
    elif errors:
        _add_reason(reasons, f"{context}_errors:{identity}")
    if warning_problem:
        _add_reason(reasons, warning_problem)
    for warning in warnings:
        if _is_hard_warning(warning):
            _add_reason(reasons, f"{context}_hard_warning:{identity}")
        else:
            caveat = f"{caveat_prefix}: {warning}"
            if caveat not in caveats:
                caveats.append(caveat)
    return reasons, caveats


def _source_check(artifact: dict[str, Any]) -> tuple[list[str], list[str], str]:
    source = artifact.get("source_financial_statement")
    if not isinstance(source, dict):
        return ["missing_sec_provenance"], ["refresh_sec_provenance"], "missing"

    url = str(source.get("url") or "")
    exact_url = "/Archives/edgar/data/" in url and url.endswith(
        (".htm", ".html", ".txt")
    )
    required = (
        source.get("filed_date"),
        source.get("period_end"),
        source.get("accession"),
    )
    if not exact_url or any(value in (None, "") for value in required):
        return ["weak_sec_provenance"], ["refresh_sec_provenance"], "incomplete"
    return [], [], "complete"


def _value_problem(value: object, *, missing: str, nonfinite: str) -> str | None:
    if value is None:
        return missing
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
    ):
        return nonfinite
    return None


def _scenario_check(artifact: dict[str, Any]) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    caveats: list[str] = []

    policy = artifact.get("model_policy")
    primary: str | None = None
    supporting: list[str] = []
    if isinstance(policy, dict):
        raw_primary = policy.get("primary")
        raw_supporting = policy.get("supporting", [])
        if isinstance(raw_primary, str) and raw_primary:
            primary = raw_primary
        if (
            isinstance(raw_supporting, list)
            and all(isinstance(name, str) and name for name in raw_supporting)
            and len(raw_supporting) == len(set(raw_supporting))
            and primary not in raw_supporting
        ):
            supporting = raw_supporting
        else:
            _add_reason(reasons, "invalid_model_policy")
    if primary is None:
        _add_reason(reasons, "invalid_model_policy")
    declared = ({primary} if primary is not None else set()) | set(supporting)

    models = artifact.get("models", {})
    if not isinstance(models, dict) or not models:
        reasons.append("missing_model_outputs")
    else:
        if primary is not None and primary not in models:
            _add_reason(reasons, f"missing_primary_model:{primary}")
        for name in sorted(models):
            model = models[name]
            if not isinstance(model, dict):
                _add_reason(reasons, f"invalid_model_output:{name}")
                continue
            if name not in declared:
                _add_reason(reasons, f"undeclared_model_output:{name}")
            local_reasons, local_caveats = _local_review_messages(
                model,
                context="model",
                identity=name,
                caveat_prefix=f"Model '{name}'",
            )
            for reason in local_reasons:
                _add_reason(reasons, reason)
            for caveat in local_caveats:
                if caveat not in caveats:
                    caveats.append(caveat)
            state = model.get("publication_state")
            if state not in _PUBLICATION_STATES:
                _add_reason(reasons, f"invalid_model_state:{name}")
            elif state == "withheld":
                _add_reason(reasons, f"model_not_pass:{name}")
            value_field = (
                "conditional_value_per_share"
                if name == "conditional_estimate"
                else "intrinsic_value_per_share"
            )
            value_problem = _value_problem(
                model.get(value_field),
                missing=f"missing_model_value:{name}",
                nonfinite=f"nonfinite_model_value:{name}",
            )
            if value_problem is not None:
                _add_reason(reasons, value_problem)
            elif state == "review_required":
                role = "Primary" if name == primary else "Supporting"
                warning = f"{role} model '{name}' is review_required."
                if warning not in caveats:
                    caveats.append(warning)

    scenarios = artifact.get("scenarios")
    if scenarios:
        if not isinstance(scenarios, dict):
            reasons.append("invalid_scenarios")
        else:
            for name in sorted(scenarios):
                scenario = scenarios[name]
                if not isinstance(scenario, dict) or not scenario:
                    _add_reason(reasons, f"invalid_scenario:{name}")
                    continue
                for model_name in sorted(scenario):
                    model = scenario[model_name]
                    if not isinstance(model, dict):
                        _add_reason(
                            reasons,
                            f"invalid_scenario_output:{name}:{model_name}",
                        )
                        continue
                    local_reasons, local_caveats = _local_review_messages(
                        model,
                        context="scenario_model",
                        identity=f"{name}:{model_name}",
                        caveat_prefix=(
                            f"Scenario '{name}' model '{model_name}'"
                        ),
                    )
                    for reason in local_reasons:
                        _add_reason(reasons, reason)
                    for caveat in local_caveats:
                        if caveat not in caveats:
                            caveats.append(caveat)
                    state = model.get("publication_state")
                    if state not in _PUBLICATION_STATES:
                        _add_reason(
                            reasons,
                            f"invalid_scenario_state:{name}:{model_name}",
                        )
                    elif state == "withheld":
                        _add_reason(
                            reasons,
                            f"scenario_not_pass:{name}:{model_name}",
                        )
                        continue
                    value_problem = _value_problem(
                        model.get("intrinsic_value_per_share"),
                        missing=(
                            f"missing_scenario_value:{name}:{model_name}"
                        ),
                        nonfinite=(
                            f"nonfinite_scenario_value:{name}:{model_name}"
                        ),
                    )
                    if value_problem is not None:
                        _add_reason(reasons, value_problem)
                    elif state == "review_required":
                        warning = (
                            f"Scenario '{name}' model '{model_name}' "
                            "is review_required."
                        )
                        if warning not in caveats:
                            caveats.append(warning)
    return reasons, caveats


def _review_messages(value: object, invalid_reason: str) -> tuple[list[str], str | None]:
    if value in (None, []):
        return [], None
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return [], invalid_reason
    return value, None


def assess_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Return a concrete versioned review DTO without mutating ``artifact``."""
    blocking: list[str] = []
    repair_actions: list[str] = []
    warnings: list[str] = []

    if not isinstance(artifact, dict):
        artifact = {}

    source_reasons, source_actions, evidence_status = _source_check(artifact)
    for reason in source_reasons:
        _add_reason(blocking, reason)
    for action in source_actions:
        _add_reason(repair_actions, action)

    issuer = artifact.get("issuer", {})
    confidence = (
        issuer.get("classification_confidence")
        if isinstance(issuer, dict)
        else None
    )
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not isfinite(float(confidence))
    ):
        _add_reason(blocking, "missing_classification_confidence")
        _add_reason(repair_actions, "reclassify_issuer_or_switch_model")
    elif confidence < 0.8:
        warnings.append(
            "Classification confidence is below the 0.80 review threshold."
        )
        _add_reason(repair_actions, "reclassify_issuer_or_switch_model")

    review = artifact.get("review", {})
    if not isinstance(review, dict):
        _add_reason(blocking, "missing_review_payload")
    else:
        if review.get("publication_state") == "withheld":
            _add_reason(blocking, "review_state_withheld")
        errors, error_problem = _review_messages(
            review.get("errors", []), "invalid_review_errors"
        )
        review_warnings, warning_problem = _review_messages(
            review.get("warnings", []), "invalid_review_warnings"
        )
        if error_problem:
            _add_reason(blocking, error_problem)
        if warning_problem:
            _add_reason(blocking, warning_problem)
        if errors:
            _add_reason(blocking, "review_errors_present")
        for warning in review_warnings:
            if _is_hard_warning(warning):
                _add_reason(blocking, "review_hard_warning")
            elif warning not in warnings:
                warnings.append(warning)

    scenario_reasons, scenario_caveats = _scenario_check(artifact)
    for reason in scenario_reasons:
        _add_reason(blocking, reason)
        if (
            reason.startswith("model_not_pass")
            or reason.startswith("missing_model_value")
            or reason.startswith("nonfinite_model_value")
            or reason.startswith("missing_primary_model")
            or reason.startswith("missing_scenario_value")
            or reason.startswith("nonfinite_scenario_value")
            or reason.startswith("model_errors:")
            or reason.startswith("invalid_model_")
            or reason.startswith("scenario_model_errors:")
            or reason.startswith("invalid_scenario_model_")
        ):
            _add_reason(repair_actions, "rebuild_valuation_models")
    for warning in scenario_caveats:
        if warning not in warnings:
            warnings.append(warning)

    if any("hard_warning" in reason for reason in blocking):
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
