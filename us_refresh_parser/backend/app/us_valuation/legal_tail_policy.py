"""Transparent policy for reported-operations baselines with unquantified legal tails."""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any


LEGAL_TAIL_POLICY_VERSION = "PRACTICAL-REPORTED-CLAIMS-BASELINE-1.0"


def apply_unquantified_legal_tail_policy(
    result: dict[str, Any],
    *,
    model_version: str,
    matter_summary: str,
    recorded_claim_treatment: str,
    invalidation: str,
) -> dict[str, Any]:
    """Keep unknown loss unknown while publishing a conditional operating baseline.

    This is not a legal-loss estimator. It verifies that the underlying valuation is
    finite, retains only source-reported claims in the model, and labels the unknown
    tail as outside the published range.
    """

    value = deepcopy(result)
    scenario = value.get("scenario_range", {})
    ordered = tuple(scenario.get(key) for key in ("low", "base", "high"))
    if (
        len(ordered) != 3
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) or not isfinite(float(item)) for item in ordered)
        or not 0 <= float(ordered[0]) <= float(ordered[1]) <= float(ordered[2])
        or float(ordered[1]) <= 0
    ):
        raise ValueError("legal-tail policy requires a finite ordered positive-base valuation")

    warning = (
        "Conditional Low reported-operations baseline. The model uses source-reported "
        f"operations and recorded claims only. Unquantified legal matters—{matter_summary}—"
        "have no filed total loss range, remain outside the valuation range, and can move "
        "actual value materially."
    )
    reasons = ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    value.update(
        {
            "model_version": model_version,
            "availability_type": "conditional_estimate",
            "warning": warning,
        }
    )
    reliability = dict(value["history_reliability"])
    reliability.update({"label": "Low", "model_cap": "Low", "reasons": list(reasons)})
    value["history_reliability"] = reliability
    assumptions = dict(value["governed_assumptions"])
    assumptions.update(
        {
            "normalization_basis": "reported_operations_and_recorded_claims_only",
            "assumption_source_mix": "reported_history_recorded_claims_and_finsight_scenarios",
            "unquantified_legal_loss_amount": None,
            "unquantified_legal_loss_assumed_zero": False,
            "range_scope": "going_concern_operations_and_source_reported_claims_not_total_legal_loss",
            "invalidation": invalidation,
        }
    )
    value["governed_assumptions"] = assumptions
    ledger = dict(value["source_ledger"])
    ledger["unquantified_legal_tail_policy"] = {
        "policy_version": LEGAL_TAIL_POLICY_VERSION,
        "matter_summary": matter_summary,
        "recorded_claim_treatment": recorded_claim_treatment,
        "unquantified_loss_amount": None,
        "reported_vs_estimated": "unavailable_not_substituted",
        "zero_substitution_used": False,
        "valuation_scope": "reported_operations_baseline_not_a_legal_loss_bound",
        "reliability_cap": "Low",
        "invalidation": invalidation,
    }
    value["source_ledger"] = ledger
    baseline = dict(value["baseline"])
    baseline.update(
        {
            "method_version": model_version,
            "availability_type": "conditional_estimate",
            "confidence": "Low",
            "confidence_reasons": list(reasons),
            "warnings": [warning, invalidation],
        }
    )
    value["baseline"] = baseline
    return value
