"""A separately approved private claim overlay; no exact-source or release waiver.

Original frozen policies remain immutable. The consumer first validates the
prior policy against its source authority, then reconstructs this overlay.
No model state, future cash schedule, discounting or valuation is executed.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .expansion_policy_binding import (
    _no_valuation_keys, content_hash, number, prepare_enterprise_inputs, require,
    sha256_format,
)

VERSION = "US-EXPANSION-PRIVATE-CLAIM-OVERLAY-1"
APPROVAL_VERSION = "US-EXPANSION-CLAIM-ALLOWANCE-APPROVAL-1"
GATE = "acquisition_perimeter"
AMOUNTS = {"bear":127600000, "base":63800000, "bull":63800000}


def validate_claim_approval(prior, proposal, approval, *, prior_sha256, proposal_sha256, approval_canonical_sha256):
    require(approval.get("schema_version") == APPROVAL_VERSION, "claim approval version")
    require(approval.get("approved_by") == "human_user_in_current_chat", "explicit human claim approval missing")
    require(approval.get("approved_scope") == "SITE_only_private_low_claim_allowance_binding_no_valuation", "claim approval scope")
    require(sha256_format(prior_sha256) and content_hash(prior) == prior_sha256 == approval.get("prior_policy_sha256"), "approved prior policy content changed")
    require(sha256_format(proposal_sha256) and proposal_sha256 == approval.get("proposal_sha256"), "approved raw proposal hash")
    require(content_hash(proposal) == approval.get("proposal_canonical_sha256"), "approved proposal content changed")
    require(content_hash(approval) == approval_canonical_sha256, "claim approval content/hash mismatch")
    require(prior["ticker"] == proposal["ticker"] == approval["ticker"] == "SITE", "SITE-only overlay issuer")
    require(prior["cik"] == proposal["cik"] == approval["cik"] == "0001650729", "claim CIK mismatch")
    require(prior["evidence_cutoff"] == proposal["evidence_cutoff"] == approval["evidence_cutoff"] == "2026-10-03", "claim cutoff changed")
    require(prior["valuation_date"] == proposal["valuation_date"] == approval["valuation_date"], "claim valuation date changed")
    require(proposal["classification"] == "FINSIGHT_ASSUMPTION", "claim proxy relabeled as fact")
    require(proposal["status"] == "proposed_unapproved_not_bound", "historical proposal was rewritten")
    require(approval.get("accepts_incomplete_coverage") is True and approval.get("accepts_remeasurement_risk") is True, "claim risk acceptance missing")
    require(approval.get("allowance_location") == "negative_nonoperating_adjustment_once", "wrong/double claim location")
    require(proposal["scenario_allowance_USD"] == approval["approved_allowance_USD"] == AMOUNTS, "approved allowance amounts changed")
    require(proposal["scale_anchor_USD"] == sum(number(row["value_USD"], "vintage") for row in proposal["source_vintages"]) == 63800000, "claim scale arithmetic")
    require(len(proposal["source_vintages"]) == len({row["fiscal_year"] for row in proposal["source_vintages"]}) == 7, "duplicated claim vintages")
    require(proposal["all_legacy_cohorts_source_complete"] is False and proposal["exact_source_gate_cleared"] is False, "incomplete claim coverage silently cleared")
    require(all(proposal[key] is None for key in ("exact_current_aggregate_claim_USD", "hard_upper_bound_USD", "contractual_maximum_USD")), "assumption presented as balance/bound")
    require(proposal["payments_netted"] is False and proposal["second_cash_budget_allowed"] is False, "claim payment/deduction double count")
    for key in ("exact_reconciliation_approved", "forecast_execution_authorized", "valuation_execution_authorized",
                "public_release_authorized", "catalog_admission_authorized", "live_refresh_promotion_authorized"):
        require(approval.get(key) is False, f"{key}: private binding does not confer wider authority")
    require(prior["forced_held"] is False and prior["policy_ready"] is False and prior["remaining_gates"] == [GATE], "prior policy has other unresolved/forced holds")
    require(prior["contract"]["model"] == "enterprise_cash_fcff" and prior["normalization"] is not None, "supported enterprise inputs missing")
    require(prior["prepared_engine_inputs"] is None, "prior policy already has a claim bridge; reapply forbidden")


def validate_common_owner_proof(proof, sources):
    values = proof["facts"]
    for key in ("assets", "liabilities", "parent_equity"):
        require(values[key] == sources["reported_balances"][key], "owner proof differs from frozen balance source")
    require(values["assets"]["value"] - values["liabilities"]["value"] == values["parent_equity"]["value"], "NCI proof residual")
    require(proof["NCI_claim_basis_USD"] == proof["preferred_claim_basis_USD"] == 0, "owner allocation changed")
    if values["preferred"] is not None:
        require(values["preferred"]["value"] == 0, "preferred claim unresolved")
    else:
        require(all(values[key] is not None for key in ("common", "apic", "retained", "aoci", "treasury")), "preferred component proof incomplete")
        subtotal = sum(number(values[key]["value"], key) for key in ("common", "apic", "retained", "aoci")) - number(values["treasury"]["value"], "treasury")
        require(subtotal == values["parent_equity"]["value"], "preferred component residual")


def bind_claim_allowance(prior: Mapping[str, Any], proposal: Mapping[str, Any], approval: Mapping[str, Any], *,
                         prior_sha256: str, proposal_sha256: str, approval_canonical_sha256: str,
                         evidence_sha256: str, owner_proof: Mapping[str, Any]) -> dict[str, Any]:
    validate_claim_approval(prior, proposal, approval, prior_sha256=prior_sha256, proposal_sha256=proposal_sha256,
                            approval_canonical_sha256=approval_canonical_sha256)
    require(sha256_format(evidence_sha256) and evidence_sha256 == approval.get("evidence_sha256"), "claim evidence fingerprint missing/does not match approved evidence")
    pinned_proof = prior["provenance"]["verified_review"]["source_checks"]["SITE"]["equity_scope_proof"]
    require(owner_proof == pinned_proof, "owner proof not from validated prior source review")
    validate_common_owner_proof(owner_proof, prior["sources"])
    sources = prior["sources"]
    base_bridge = {
        "cash_source": sources["reported_balances"]["cash"],
        "gross_debt_source": sources["reported_debt"]["gross_principal_source"],
        "cash_scope": "reported_unrestricted_cash_no_unbound_investment_addition",
        "income_removed_once": True, "finance_leases_included_once": True, "operating_leases_added_to_debt": False,
        "nci_claim_basis_USD": owner_proof["NCI_claim_basis_USD"], "preferred_claim_basis_USD": owner_proof["preferred_claim_basis_USD"],
        "ownership_scope_proof": deepcopy(owner_proof), "NCI_distribution_second_deduction": False,
        "known_additional_claims_review": {"classification":"FINSIGHT_ASSUMPTION", "policy_name":proposal["policy_name"],
            "approved_proxy_for_unreconciled_legacy_claim_deduction":True, "exact_remaining_claim_USD":None,
            "source_complete":False, "maximum_claim_USD":None, "second_cash_budget":False},
    }
    prepared, bridges = {}, {}
    for name in ("bear", "base", "bull"):
        bridge = {**deepcopy(base_bridge), "nonoperating_adjustment_USD": -number(AMOUNTS[name], name)}
        # Compose the existing source bridge argument compiler. This only
        # creates input dictionaries and does not instantiate/call a model.
        compiled = prepare_enterprise_inputs(sources, prior["contract"], prior["normalization"], bridge)
        args = compiled["arguments_not_executed"][name]
        require(args["nonoperating_adjustment"] == -AMOUNTS[name], "claim allowance sign/location")
        require(args["cash_fcff"] == prior["normalization"]["scenario_starting_inputs"][name]["net_FCFF_starting_input_USD"], "claim was charged to recurring cash too")
        require(args["interest_bearing_debt"] == sources["reported_debt"]["gross_principal_source"]["value"], "claim was also added to debt")
        require(args["noncontrolling_interests"] == args["preferred_equity"] == 0, "Devil Mountain/current preferred double charge")
        prepared[name], bridges[name] = args, bridge
    gate = {"status":"approved_assumption_private_only", "closure_basis":"explicit_human_acceptance_of_incomplete_claim_proxy",
            "source_reconciliation_status":"unresolved", "exact_source_gate_cleared":False,
            "classification":"FINSIGHT_ASSUMPTION", "evidence_sha256":evidence_sha256,
            "proposal_sha256":proposal_sha256, "approval_canonical_sha256":approval_canonical_sha256}
    result = {
        "schema_version":VERSION, "ticker":"SITE", "cik":"0001650729", "evidence_cutoff":prior["evidence_cutoff"],
        "valuation_date":prior["valuation_date"], "prior_policy_sha256":prior_sha256,
        "prior_policy_integrity_sha256":prior["integrity_sha256"], "proposal_sha256":proposal_sha256,
        "proposal_canonical_sha256":content_hash(proposal), "approval_canonical_sha256":approval_canonical_sha256,
        "evidence_sha256":evidence_sha256, "analysis_scope":"private_low_reliability_only",
        "policy_ready_for_private_low_analysis":True, "public_or_source_complete_release_ready":False,
        "remaining_private_policy_gates":[], "remaining_exact_source_gates":[GATE],
        "acquisition_claim_gate":gate, "unchanged_other_gate_statuses":deepcopy({name:value for name,value in prior["gates"].items() if name != GATE}),
        "claim_policy":{"name":proposal["policy_name"],"classification":"FINSIGHT_ASSUMPTION",
            "allowance_USD":deepcopy(AMOUNTS),"deductions_per_scenario":1,"location":"negative_nonoperating_adjustment",
            "exact_current_aggregate_claim_USD":None,"hard_upper_bound_USD":None,"contractual_maximum_USD":None,
            "all_legacy_cohorts_source_complete":False,"payments_netted":False,"second_cash_budget_allowed":False,
            "accepted_incomplete_coverage":True,"accepted_remeasurement_risk":True,
            "source_vintages":deepcopy(proposal["source_vintages"]),"excludes":deepcopy(proposal["excludes"]),
            "invalidation":deepcopy(proposal["invalidation"])},
        "contract":deepcopy(prior["contract"]),"normalization":deepcopy(prior["normalization"]),
        "denominator_proxy":deepcopy(prior["denominator_proxy"]), "source_provenance":deepcopy(prior["provenance"]),
        "prepared_engine_inputs":{"engine":"enterprise_cash_fcff","arguments_not_executed":prepared,
            "source_bridge_by_scenario":bridges,"forecast_years":prior["contract"]["years"],
            "model_instantiated":False,"valuation_called":False,
            "denominator_field_semantics":"engine_diluted_shares_slot_uses_approved_point_common_proxy_not_reported_diluted"},
        "economic_calibration":"unvalidated","valuation_result":None,
        "forecast_execution_authorized":False,"valuation_execution_authorized":False,"forecasts_built":False,
        "recipes_built":False,"valuations_calculated":False,"changes_active_catalog":False,
        "public_release_authorized":False,"catalog_admission_authorized":False,"live_refresh_promotion_authorized":False,
    }
    _no_valuation_keys(result)
    return {**result,"integrity_sha256":content_hash(result)}


def validate_claim_binding(record: Mapping[str, Any], prior, proposal, approval, **arguments):
    value = deepcopy(dict(record))
    seal = value.pop("integrity_sha256", None)
    require(content_hash(value) == seal, "claim binding integrity changed")
    expected = bind_claim_allowance(prior, proposal, approval, **arguments)
    require(content_hash(record) == content_hash(expected), "claim binding does not reconstruct from frozen prior/proposal/approval")
    return dict(record)
