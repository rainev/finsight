"""Fail-closed model eligibility for U.S. valuation routing."""

from __future__ import annotations

from typing import Any

from .classification import load_archetype_config


def _governed_models() -> dict[str, str]:
    """Read the primary model registry from the classification configuration."""
    config = load_archetype_config()
    policies = config.get("valuation_policies", {})
    if not isinstance(policies, dict):
        return {}
    return {
        archetype: policy["primary_model"]
        for archetype, policy in policies.items()
        if isinstance(archetype, str)
        and isinstance(policy, dict)
        and isinstance(policy.get("primary_model"), str)
        and policy["primary_model"]
    }


def model_eligibility(classification: dict[str, Any]) -> dict[str, Any]:
    """Return whether the classified issuer may use its configured primary model."""
    if not isinstance(classification, dict):
        return {
            "eligible": False,
            "model": "unknown",
            "reason": "Classification must be a mapping with a governed archetype.",
        }
    raw_archetype = classification.get("primary_archetype")
    policy = classification.get("valuation_policy")
    raw_model = policy.get("primary_model") if isinstance(policy, dict) else None
    archetype = raw_archetype if isinstance(raw_archetype, str) else ""
    model = raw_model if isinstance(raw_model, str) and raw_model else "unknown"
    expected_model = _governed_models().get(archetype)
    if expected_model is None:
        return {
            "eligible": False,
            "model": model,
            "reason": (
                f"{archetype or 'unknown'} is not a governed U.S. valuation archetype; "
                f"{model} is ineligible."
            ),
        }
    if model == expected_model:
        return {
            "eligible": True,
            "model": model,
            "reason": f"{archetype} is eligible for {model}.",
        }
    return {
        "eligible": False,
        "model": model,
        "reason": (
            f"{archetype} is not eligible for {model}; "
            f"expected {expected_model}."
        ),
    }
