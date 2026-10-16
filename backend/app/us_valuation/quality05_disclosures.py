"""Raw-free public disclosure DTOs for the staged Quality05 candidate."""
from copy import deepcopy
from math import isfinite
import json

from . import quality05_staged as stage


# This is intentionally a scalar allowlist.  In particular, no private source
# paths, traces, ledgers, CompanyFacts, recipe payloads or diagnostic envelopes
# may cross the consumer boundary.
PUBLIC_FIELDS = frozenset({
    "forecast_policy_version", "classification", "forecast_mode", "forecast_years", "terminal_growth",
    "automatic_new_filing_revaluation", "sustainable_income_or_cash_proven", "legal_absence_of_unrecorded_claims_proven",
    "share_count_basis", "cost_of_equity", "initial_forecast_roe_seed", "future_payout_ratio", "terminal_roe",
    "clean_surplus_and_payout_recurrence_proven", "no_reconciled_owner_cash_claim", "first_year_reported_income_fade_and_event_drag_once",
    "physical_share_anchor", "fully_diluted_forward_share_proof", "claim_allowance_bear", "claim_allowance_base", "claim_allowance_bull",
    "claim_allowance_is_reported_preferred_carrying_value", "all_preferred_distributions_reconciled", "wacc", "initial_growth",
    "cash_statement_SBC_TTM_cost", "SBC_economic_cost_charged_once", "cash_paid_financing_newly_reconciled", "retained_tax_convention",
    "net_loan_reinvestment_TTM_cost", "loan_reinvestment_charged_once", "customer_funds_excluded_from_owner_CFO_and_EV",
    "finance_lease_allowance_bear", "finance_lease_allowance_base", "finance_lease_allowance_bull", "finance_lease_allowance_exactly_reconciled",
    "other_claim_reserve_bear", "other_claim_reserve_base", "other_claim_reserve_bull", "future_lease_PV_reserve_bear",
    "future_lease_PV_reserve_base", "future_lease_PV_reserve_bull", "legacy_claim_field_is_preferred_stock_fact", "claim_reserves_charged_once",
    "groq_payable_reserve", "contingent_investment_reserve_bear", "contingent_investment_reserve_base", "contingent_investment_reserve_bull",
    "net_guarantee_exposure_bear", "net_guarantee_exposure_base", "net_guarantee_exposure_bull",
    "unrecognized_tax_benefit_liability", "reserve_components_are_governed_not_all_reported_liabilities",
    "forward_common_earnings_drag_bear", "forward_common_earnings_drag_base", "forward_common_earnings_drag_bull", "forward_event_drag_charged_once",
    "legacy_claim_container_role", "legacy_claim_field_is_preferred_stock_fact", "noncontrolling_interest_model_allowance", "preferred_stock_model_claim", "claim_reserves_charged_once", "financing_source_convention",
})


def _scalar(value):
    return isinstance(value, (str, bool, int, float)) and not (isinstance(value, float) and not isfinite(value))


def public_forecast_assumptions(value, *, issuer=None):
    """Validate the reviewed base-policy DTO, not an arbitrary scalar dict."""
    stage.require(isinstance(value, dict) and set(value) <= PUBLIC_FIELDS, "safe Quality05 analyst assumptions only")
    result = deepcopy(value)
    stage.require(all(_scalar(item) for item in result.values()), "scalar assumption DTO")
    stage.require(result.get("forecast_policy_version") == stage.MODEL_VERSION, "assumption policy version")
    stage.require(result.get("classification") == "ANALYST_ASSUMPTIONS_NOT_REPORTED_FACTS", "assumption classification")
    stage.require(result.get("forecast_mode") in {"residual_income_exact", "enterprise_cash_fcff_exact", "constant_growth_fcff_exact"}, "reviewed model mode")
    stage.require(result.get("automatic_new_filing_revaluation") is False, "no new-source permission")
    stage.require(result.get("sustainable_income_or_cash_proven") is False and result.get("legal_absence_of_unrecorded_claims_proven") is False, "unproven sustainability/claims")
    stage.require(isinstance(result.get("forecast_years"), int) and result["forecast_years"] > 0, "forecast horizon")
    stage.require("terminal_growth" in result, "terminal growth")
    if result["forecast_mode"] == "residual_income_exact":
        for key in ("cost_of_equity", "initial_forecast_roe_seed", "future_payout_ratio", "terminal_roe", "first_year_reported_income_fade_and_event_drag_once"):
            stage.require(key in result, "reviewed RI policy: " + key)
        stage.require(result.get("clean_surplus_and_payout_recurrence_proven") is False and result.get("no_reconciled_owner_cash_claim") is True, "RI policy semantics")
        if any(key in result for key in ("forward_common_earnings_drag_bear", "forward_common_earnings_drag_base", "forward_common_earnings_drag_bull")):
            stage.require(result.get("forward_event_drag_charged_once") is True, "forward event drag semantics")
    else:
        for key in ("wacc", "initial_growth", "cash_statement_SBC_TTM_cost", "SBC_economic_cost_charged_once", "cash_paid_financing_newly_reconciled"):
            stage.require(key in result, "reviewed cash policy: " + key)
        stage.require(result.get("SBC_economic_cost_charged_once") is True and result.get("cash_paid_financing_newly_reconciled") is False, "cash compensation semantics")
        if "reserve_components_are_governed_not_all_reported_liabilities" in result:
            stage.require(result["reserve_components_are_governed_not_all_reported_liabilities"] is True, "governed reserve semantics")
    if issuer == "MCO" or "legacy_claim_container_role" in result:
        required = ("SBC_economic_cost_charged_once", "cash_statement_SBC_TTM_cost", "cash_paid_financing_newly_reconciled", "financing_source_convention", "legacy_claim_container_role", "legacy_claim_field_is_preferred_stock_fact", "noncontrolling_interest_model_allowance", "preferred_stock_model_claim", "claim_reserves_charged_once")
        stage.require(all(key in result for key in required), "complete MCO semantic DTO")
        stage.require(result.get("SBC_economic_cost_charged_once") is True and result.get("cash_statement_SBC_TTM_cost") == 232000000.0 and result.get("cash_paid_financing_newly_reconciled") is False and result.get("financing_source_convention") == "cash_paid_InterestPaidNet", "MCO paid-financing/SBC semantics")
        stage.require(result.get("legacy_claim_container_role") == "noncontrolling_interests" and result.get("legacy_claim_field_is_preferred_stock_fact") is False, "MCO claim semantics")
        stage.require(result.get("noncontrolling_interest_model_allowance") == 141000000.0 and result.get("preferred_stock_model_claim") == 0.0 and result.get("claim_reserves_charged_once") is True, "MCO NCI allowance")
    return result


def consumer_disclosures(root, manifest, artifact, payload, *, proof_reader):
    """Add staged scope and reviewed assumptions to all native read surfaces."""
    ticker = artifact["issuer"]["ticker"]
    a = stage.anchors()
    binding = stage.proof(root, "quality-source-binding.json", a["binding_sha256"], proof_reader)
    stage.require(set(binding["records"]) == stage.TARGETS | stage.CARRY_FORWARD, "disclosure scope")
    if ticker not in binding["records"]:
        return payload
    record = binding["records"][ticker]
    result = deepcopy(payload)
    warnings = list(dict.fromkeys([*result.get("warnings", []), *artifact.get("review", {}).get("warnings", [])]))
    source_date = artifact["source_financial_statement"]["period_end"]
    valuation_date = artifact["valuation_date"]
    updated = ticker in stage.TARGETS
    if updated:
        assumptions = public_forecast_assumptions(record["forecast_assumptions"], issuer=ticker)
        result["quality_forecast_assumptions"] = assumptions
        warnings.append("Forecast assumptions, not reported facts: " + json.dumps(assumptions, sort_keys=True))
        filing_hold = True
    else:
        warnings.append("Authentic prior dated public estimate and recipe retained; no revised private diagnostic or held-update assumptions are exposed.")
        filing_hold = not bool(record.get("existing_refresh_contract_ready"))
    warnings.append("Financial reference date is " + str(source_date) + "; artifact valuation date is " + str(valuation_date) + ". Review date does not advance the financial cutoff.")
    if ticker in stage.CONTROLS:
        status = "unchanged_control"
    elif ticker in stage.PRIVATE_ONLY:
        status = "private_only_diagnostic"
    elif ticker in stage.HELD:
        status = "private_held_update"
    else:
        status = "revised_value_staged"
    result["warnings"] = list(dict.fromkeys(warnings))
    result["staged_scope"] = {
        "schema_version": stage.REVIEW_SCHEMA, "read_only": True, "admission": False, "activation": False, "publication": False,
        "valuation_date": valuation_date, "financial_reference_date": source_date, "sourceDate": source_date,
        "financial_evidence_cutoff": record.get("proposed_evidence_cutoff", valuation_date) if updated else valuation_date,
        "new_filing_hold": filing_hold, "quality_update_held": ticker in stage.HELD or ticker in stage.PRIVATE_ONLY,
        "quality_update_status": status, "revised_value_staged": updated, "prior_dated_public_estimate_retained": not updated,
        "private_only_recovery_diagnostic": ticker in stage.PRIVATE_ONLY, "unchanged_control": ticker in stage.CONTROLS,
        "source_public_approved_low_version": stage.MODEL_VERSION, "facts_and_forecast_assumptions_separate": True,
        "updated_recipe_source_adapter_ready": False if updated else bool(record.get("existing_refresh_contract_ready")),
    }
    return result
