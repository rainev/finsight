"""Consumer disclosures for the staged Quality Batch 02 public contract.

This module is deliberately a presentation-only boundary. It does not select a
model, calculate a range, mutate a catalog, or turn private source evidence
into reported facts. The companion ``quality02_staged`` context owns the
compiled anchors, 19-target/31-carry-held scope, and proof-reader contract.
"""

from __future__ import annotations

from copy import deepcopy
import json
from math import isfinite


PUBLIC_POLICY_VERSION = "US-QUALITY02-PUBLIC-LOW-1"
PUBLIC_SCHEMA_VERSION = "US-QUALITY02-PUBLIC-LOW-1"
FINANCIAL_CUTOFF = "2026-10-08"

# Safe scalar policy fields. Anything containing source bindings, paths,
# recipes, raw facts, hashes, or private IDs is intentionally excluded.
PUBLIC_FORECAST_FIELDS = frozenset(
    {
        "accounting_bound_scope",
        "budget_basis",
        "cash_anchor_mode",
        "cash_debt_bridge",
        "debt_net_borrowing_assumption",
        "equity_risk_premium",
        "financing_assumption",
        "forecast_years",
        "future_acquisition_cash_budget_fraction",
        "future_payout_ratio",
        "incremental_growth_cash_intensity",
        "initial_growth_cap",
        "rate_kind",
        "risk_free_rate",
        "sector_assignment",
        "sector_beta_prior",
        "sector_risk_prior",
        "terminal_return_bound",
        "uncertainty_premium",
        "cash_rejection",
        "no_claim_of_reconciled_owner_cash",
        "reinvestment_assumption",
        "full_reported_capex_and_sbc",
        "excess_cash_credit",
        "lease_absence_not_inferred_from_missing_tags",
        "unknown_essential_claims_held",
    }
)
SAFE_WARNING_FIELDS = frozenset({"cycle_warnings", "risk_warnings", "relevant_cycle_warnings"})
FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "source_bindings",
        "source_binding",
        "source_bindings_sha256",
        "source_paths",
        "source_ledger",
        "source_inventory",
        "source_packet",
        "raw_financials",
        "raw_facts",
        "recipes",
        "recipe",
        "private_policy_id",
        "private_policy_sha256",
        "model_inputs",
    }
)


def _context_module():
    # Root supplies this module beside the helper. Lazy import keeps this leaf
    # importable in ordinary parent-record consumers before the staged context
    # is selected by the router.
    from . import quality02_staged

    return quality02_staged


def _require(condition, reason):
    if not condition:
        raise ValueError("quality02 disclosure rejected: " + reason)


_NUMERIC_FIELDS = frozenset({
    "cash_debt_bridge", "equity_risk_premium", "forecast_years",
    "future_acquisition_cash_budget_fraction", "incremental_growth_cash_intensity",
    "initial_growth_cap", "risk_free_rate", "sector_beta_prior",
    "uncertainty_premium", "future_payout_ratio", "terminal_return_bound",
})
_BOOL_FIELDS = frozenset({
    "full_reported_capex_and_sbc", "excess_cash_credit",
    "lease_absence_not_inferred_from_missing_tags", "unknown_essential_claims_held",
    "no_claim_of_reconciled_owner_cash",
})


def _scalar(key, value):
    if value is None or isinstance(value, str):
        return True
    if key in _BOOL_FIELDS:
        return isinstance(value, bool)
    if key in _NUMERIC_FIELDS:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
    return isinstance(value, (int, float, bool)) and (not isinstance(value, float) or isfinite(value))


def _safe_warning_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value):
        return list(value)
    raise ValueError("quality02 disclosure rejected: warning list must contain strings")


def public_forecast_assumptions(policy):
    """Return only the approved per-issuer public analyst-assumption DTO."""
    if not isinstance(policy, dict):
        raise ValueError("quality02 disclosure rejected: policy must be an object")

    # Per-issuer rows commonly wrap the actual assumptions.
    source = policy.get("forecast_assumptions")
    if not isinstance(source, dict):
        source = policy
    result = {}
    for key in PUBLIC_FORECAST_FIELDS:
        value = source.get(key)
        if value is not None:
            _require(_scalar(key, value), "invalid public policy field " + key)
            result[key] = value

    warning_values = []
    for key in SAFE_WARNING_FIELDS:
        warning_values.extend(_safe_warning_list(source.get(key)))
    if warning_values:
        result["relevant_cycle_warnings"] = list(dict.fromkeys(warning_values))

    _require(all(key not in result for key in FORBIDDEN_PUBLIC_KEYS), "forbidden public policy key")
    _require(all(_scalar(key, value) or (key == "relevant_cycle_warnings" and isinstance(value, list)) for key, value in result.items()), "non-scalar public policy value")
    result["forecast_policy_version"] = PUBLIC_POLICY_VERSION
    result["classification"] = "ANALYST_ASSUMPTIONS_NOT_REPORTED_FACTS"
    return result


def _binding(root, manifest, proof_reader):
    context = _context_module()
    anchors = context.anchors()
    context_require = getattr(context, "require", _require)
    context_require(callable(proof_reader), "verified proof reader missing")
    targets = getattr(context, "TARGETS", None)
    carry = getattr(context, "CARRY_HELD", None)
    if carry is None:
        carry = getattr(context, "HELD", None)
    context_require(targets is not None and carry is not None, "quality02 scope constants missing")
    context_require(len(targets) == 19 and len(carry) == 31 and not (set(targets) & set(carry)), "quality02 scope is not exact19/31")
    binding_sha = anchors.get("binding_sha256") or anchors.get("quality_source_binding_sha256")
    context_require(isinstance(binding_sha, str) and len(binding_sha) == 64, "quality binding anchor missing")
    context_proof = getattr(context, "proof", None)
    context_require(callable(context_proof), "quality02 context proof helper missing")
    binding = context_proof(root, "quality-source-binding.json", binding_sha, proof_reader)
    context_require(isinstance(binding, dict) and isinstance(binding.get("records"), dict), "quality binding malformed")
    context_require(set(binding["records"]) >= set(targets) | set(carry), "quality binding scope incomplete")
    return context, anchors, frozenset(targets), frozenset(carry), binding


def _review_warnings(artifact):
    warnings = artifact.get("review", {}).get("warnings", [])
    _require(isinstance(warnings, list) and all(isinstance(x, str) for x in warnings), "artifact warnings malformed")
    return warnings


def consumer_disclosures(root, manifest, artifact, payload, *, proof_reader):
    """Attach the safe staged Quality Batch 02 disclosure DTO.

    Only the authenticated 19-target plus 31-carry-held binding is handled.
    Unrelated parent records return the original payload object unchanged.
    """
    ticker = artifact.get("ticker", artifact.get("issuer", {}).get("ticker"))
    context, anchors, targets, carry, binding = _binding(root, manifest, proof_reader)
    handled = targets | carry
    if ticker not in handled:
        return payload

    record = binding["records"].get(ticker)
    _require(isinstance(record, dict), ticker + " missing quality binding record")
    result = deepcopy(payload)
    warnings = list(dict.fromkeys([*result.get("warnings", []), *_review_warnings(artifact)]))

    source_header = artifact.get("source_financial_statement") or {}
    artifact_date = artifact.get("valuation_date")
    financial_reference_date = source_header.get("period_end")
    assumptions = None
    if ticker in targets:
        policy = record.get("forecast_assumptions")
        if policy is None:
            policy = record.get("public_forecast_assumptions")
        _require(isinstance(policy, dict), ticker + " missing approved forecast assumptions")
        assumptions = public_forecast_assumptions(policy)
        warnings.append("Forecast assumptions, not reported facts: " + json.dumps(assumptions, sort_keys=True, ensure_ascii=False))
    else:
        warnings.append("No revised forecast assumptions are exposed for this record; the prior dated public estimate and recipe are retained while the private quality update remains held.")

    warnings.append(
        "Financial reference date is the source filing period_end "
        + str(financial_reference_date)
        + "; artifact valuation_date is "
        + str(artifact_date)
        + ". Review date does not create a new financial cutoff."
    )

    existing_readiness = record.get("existing_refresh_readiness")
    new_filing_hold = not bool(existing_readiness)
    prior_retained = ticker in carry
    private_held = record.get("private_held_update")
    if private_held is None:
        private_held = record.get("confirmed_quality_review_hold")

    result["warnings"] = list(dict.fromkeys(warnings))
    scope = result.get("staged_scope")
    if not isinstance(scope, dict):
        scope = {}
    scope.update(
        {
            "schema_version": context.REVIEW_SCHEMA,
            "read_only": True,
            "admission": False,
            "activation": False,
            "publication": False,
            "valuation_date": artifact_date,
            "financial_reference_date": financial_reference_date,
            "sourceDate": financial_reference_date,
            "financial_evidence_cutoff": FINANCIAL_CUTOFF,
            "new_filing_hold": new_filing_hold,
            "quality_update_held": bool(private_held),
            "quality_update_status": "private_held_update" if private_held else "revised_value_staged",
            "revised_value_staged": ticker in targets,
            "prior_dated_public_estimate_retained": prior_retained,
            "source_public_approved_low_version": PUBLIC_POLICY_VERSION,
            "facts_and_forecast_assumptions_separate": True,
        }
    )
    result["staged_scope"] = scope
    if assumptions is not None:
        result["quality_forecast_assumptions"] = assumptions
    return result
