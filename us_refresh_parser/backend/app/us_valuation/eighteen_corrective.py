"""Private, evidence-gated corrections for the reviewed 18-company cohort.

This module changes model eligibility and descriptions, never forecast inputs or
the calculation recipe. The preceding numeric artifact remains in the pinned
predecessor catalog and is also retained by the staging script for held names.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .automated_review import assess_artifact


OUTCOMES = {"provisional", "retain_reviewed_cash", "hold_model_scope"}


def formula_identity(recipe: Mapping[str, Any]) -> tuple[str, str]:
    """Name the economic formula, rather than an inherited sector label."""
    scenarios = recipe.get("scenarios", {})
    engines = {row.get("engine") for row in scenarios.values() if isinstance(row, Mapping)}
    if len(scenarios) != 3 or len(engines) != 1:
        raise ValueError("corrective review requires one consistent three-case recipe")
    engine = engines.pop()
    if recipe.get("family_policy") and engine == "cash_schedule":
        return "residual_income", "parent_common_equity_residual_income"
    if engine == "residual_income":
        return "residual_income", "parent_common_equity_residual_income"
    if recipe.get("cash_policy") and engine == "cash_schedule":
        return "fcfe_dcf", "operating_equity_cash_fcfe"
    if engine == "enterprise_cash_fcff":
        return "conditional_estimate", "owner_cash_enterprise_fcff"
    raise ValueError("unreviewed formula identity")


def apply_corrective_decision(
    artifact: Mapping[str, Any], recipe: Mapping[str, Any], decision: Mapping[str, str]
) -> dict[str, Any]:
    """Return a corrected private artifact without touching numeric recipe inputs."""
    result = deepcopy(dict(artifact))
    ticker = result.get("ticker")
    if not isinstance(ticker, str) or ticker != recipe.get("ticker"):
        raise ValueError("artifact and recipe issuer mismatch")
    outcome = decision.get("outcome")
    reason = decision.get("reason")
    evidence = decision.get("next_evidence")
    audit = decision.get("audit")
    if outcome not in OUTCOMES or not all(isinstance(x, str) and x for x in (reason, evidence, audit)):
        raise ValueError("incomplete corrective decision")
    primary, framework = formula_identity(recipe)
    if result.get("primary_valuation_method") != primary or result.get("model_policy", {}).get("primary") != primary:
        raise ValueError("source artifact has a different primary formula")

    result["methodology"] = {
        **result.get("methodology", {}),
        "sector_framework": framework,
        "forecast_policy": recipe["recipe_version"],
    }
    result["model_policy"] = {
        **result["model_policy"],
        "reason": "Private corrective review: " + reason,
    }
    result["private_corrective_review"] = {
        "outcome": outcome,
        "reason": reason,
        "next_evidence": evidence,
        "source_audit": audit,
        "formula_identity": framework,
        "prior_numeric_recipe_retained": outcome == "hold_model_scope",
    }
    review = result["review"]
    warnings = list(review.get("warnings", []))
    for message in ("Private corrective review: " + reason, "Next evidence: " + evidence):
        if message not in warnings:
            warnings.append(message)
    review["warnings"] = warnings

    if outcome == "hold_model_scope":
        # Remove numeric outputs from the current candidate. Keep the exact
        # predecessor bytes separately; a diagnostic is not a current value.
        model = deepcopy(result["models"][primary])
        model["intrinsic_value_per_share" if primary != "conditional_estimate" else "conditional_value_per_share"] = None
        model["publication_state"] = "withheld"
        model["errors"] = [reason]
        model["warnings"] = [evidence]
        result["models"] = {primary: model}
        result["scenarios"] = {}
        result["scenario_range"] = {"low": None, "base": None, "high": None,
                                    "label": "withheld pending source and model review"}
        result["availability_type"] = "not_available"
        result["methodology"]["forecast_policy"] = "withheld_model_scope"
        review["publication_state"] = "withheld"
        review["confidence_grade"] = "withheld"
        review["errors"] = [reason]
        result["public_assumptions"] = {"forecast_mode": "withheld_model_scope"}
        result["normalization_explanation"] = (
            "Prior arithmetic diagnostic retained privately; current model scope is not supported. " + reason
        )
        if "confidence" in result:
            result["confidence"] = {**result["confidence"], "label": "withheld"}
    else:
        if result.get("review", {}).get("publication_state") != "review_required":
            raise ValueError("provisional correction cannot promote publication")
        result["availability_type"] = "conditional_estimate"
    result["automated_review"] = assess_artifact(result)
    if outcome == "hold_model_scope" and result["automated_review"]["decision"] != "blocked":
        raise ValueError("withheld correction did not block automated review")
    return result
