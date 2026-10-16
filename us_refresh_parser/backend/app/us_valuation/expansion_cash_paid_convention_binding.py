"""Approved private WTS convention metadata; no normalization or model execution."""
from copy import deepcopy

from .expansion_policy_binding import _no_valuation_keys, content_hash, require

VERSION = "US-WTS-PRIVATE-CASH-PAID-CONVENTION-BINDING-1"
APPROVAL_VERSION = "US-WTS-CASH-PAID-CONVENTION-APPROVAL-1"
DEFERRED = ("normalization_execution_authorized", "forecast_execution_authorized", "valuation_execution_authorized",
            "catalog_admission_authorized", "activation_authorized", "publication_authorized", "live_refresh_promotion_authorized")


def bind_convention(prior, proposal, approval, evidence, *, authority):
    require(approval["schema_version"] == APPROVAL_VERSION
            and approval["approved_by"] == "human_user_in_current_chat"
            and approval["approved_scope"] == "WTS_financing_convention_only_private_still_held", "approval scope")
    require(approval["binding_authorized"] is True and approval["preserve_all_unresolved_gates"] is True, "binding/hold authority missing")
    require(all(approval[key] is False for key in DEFERRED), "wider execution/release authority forbidden")
    require(approval["pins"] == authority, "external authority pins differ")
    require(content_hash(prior) == authority["prior_policy_sha256"], "prior policy content changed")
    require(content_hash(proposal) == authority["proposal_canonical_sha256"], "approved proposal content changed")
    require(content_hash(evidence) == authority["source_proof_canonical_sha256"], "source proof content changed")
    require(prior["ticker"] == proposal["ticker"] == approval["ticker"] == evidence["ticker"] == "WTS", "WTS-only binding")
    require(prior["cik"] == proposal["cik"] == approval["cik"] == evidence["cik"] == "0000795403", "CIK mismatch")
    require(prior["evidence_cutoff"] == proposal["evidence_cutoff"] == approval["evidence_cutoff"] == evidence["evidence_cutoff"] == "2026-10-03", "cutoff changed")
    require(proposal["status"] == "unbound_proposal_pending_explicit_approval", "historical proposal rewritten")
    require(prior["policy_ready"] is False and prior["normalization"] is None
            and prior["prepared_engine_inputs"] is None and len(prior["remaining_gates"]) == 11, "prior held scope changed")
    require(prior["accounting_inputs"] is None and prior["bridge_inputs"] is None, "prior inputs unexpectedly present")
    financing = deepcopy(proposal["financing_proposal"])
    require(financing["financing_tax_proxy"] == prior["contract"]["tax_proxy"] == 0.25, "tax convention changed")
    require(financing["fees"]["annual_measurements_USD"] == [None]*5
            and financing["fees"]["current_measurement_USD"] is None and financing["fees"]["prior_measurement_USD"] is None
            and financing["fees"]["assumed_zero"] is False and financing["fees"]["separate_fee_addback_or_reversal_proposed"] is False, "fee unknown/double-adjustment changed")
    require([row["period"] for row in financing["source_observations_USD"]] == ["FY2021","FY2022","FY2023","FY2024","FY2025","current_fiscal_YTD","prior_fiscal_YTD"], "source period membership")
    require(evidence["cash_fact_count"] == 7 and evidence["income_fact_count"] == 6 and evidence["nil_presentation_count"] == 1, "source proof incomplete")
    require(proposal["leased_asset_assessment"]["selected_budget_USD"] is None
            and proposal["leased_asset_assessment"]["scenario_budgets_USD"] is None, "lease budget was authorized by financing approval")
    require(financing["source_observations_USD"][0]["reported_interest_income"] is None
            and financing["FY2021_income_dash"]["exact_tagged_zero_claimed"] is False, "source nil replaced with exact zero")
    # Only interpretation constants are compiled; no monetary formula is evaluated.
    bound = {"schema_version":VERSION,"ticker":"WTS","cik":"0000795403","evidence_cutoff":"2026-10-03",
        "valuation_date":prior["valuation_date"],"analysis_scope":"private_low_still_held_convention_only",
        "private_only":True,"reliability":"Low","convention_component_bound":True,
        "convention_status":"approved_private_symbolic_convention_execution_deferred",
        "prior_policy_sha256":authority["prior_policy_sha256"],"proposal_sha256":authority["proposal_sha256"],
        "proposal_canonical_sha256":authority["proposal_canonical_sha256"],
        "approval_canonical_sha256":content_hash(approval),"source_proof_sha256":authority["source_proof_sha256"],
        "source_proof_canonical_sha256":authority["source_proof_canonical_sha256"],
        "cash_paid_financing_convention":financing,
        "FY2021_nil_interpretation":{"classification":"FINSIGHT_ASSUMPTION_reported_nil_at_statement_precision",
            "reported_numeric_source_value_USD":None,"approved_model_presentation_proxy_USD":0,
            "exact_tagged_zero":False,"cash_receipt_fact":False,"upper_bound":False,"formula_executed":False},
        "contract":deepcopy(prior["contract"]),"gates":deepcopy(prior["gates"]),
        "remaining_gates":deepcopy(prior["remaining_gates"]),"policy_ready":False,
        "policy_status":"held_gate_enforced_convention_component_bound","forced_held":prior["forced_held"],
        "normalization":None,"accounting_inputs":None,"bridge_inputs":None,"prepared_engine_inputs":None,
        "leased_asset_assessment":deepcopy(proposal["leased_asset_assessment"]),
        "source_qualification":{"exact_period_source_facts_verified":True,"cash_accrual_reconciliation_complete":False,
            "fees_measured":False,"lease_interest_disaggregation_proven":False,
            "operating_CFO_scope_cleared":False,"cash_asset_income_gate_cleared":False},
        "warnings":["Private Low cash/accrual proxy; not a measured cash-tax shield or complete financing reconciliation.",
            "Fees remain unknown, not zero; no inferred fee reversal or second gross-interest addback.",
            "Lease-interest inclusion remains unproven; mixed lease payments are not added as interest/principal/investment.",
            "FY2021 source income remains null; model-facing nil interpretation is a presentation assumption only.",
            "All unresolved source/lease/investment/ownership/positivity gates are preserved; no readiness or release approval."],
        **{key:False for key in DEFERRED},"changes_active_catalog":False,
        "normalization_calculated":False,"forecasts_built":False,"recipes_built":False,"valuations_calculated":False,
        "public_or_source_complete_release_ready":False,"economic_calibration":"unvalidated"}
    _no_valuation_keys(bound)
    return {**bound,"integrity_sha256":content_hash(bound)}


def validate_convention(record, prior, proposal, approval, evidence, *, authority):
    expected = bind_convention(prior,proposal,approval,evidence,authority=authority)
    require(record == expected, "convention does not reconstruct from frozen sources/proposal/approval")
    return record
