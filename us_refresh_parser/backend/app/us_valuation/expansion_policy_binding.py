"""Approved, source-pinned expansion policy preparation; no valuation execution.

This opt-in private consumer compiles policy semantics, binds the frozen source
ledgers and enforces every named gate. It does not import valuation engines,
make forecasts, create valuation recipes or change live refresh policies.
Reported facts, derived accounting inputs and reviewed assumptions stay distinct.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from .catalog import canonical_json_bytes

VERSION = "US-EXPANSION-POLICY-BINDING-1"
APPROVAL_VERSION = "FINSIGHT-US-EXPANSION-POLICY-APPROVAL-1"
MODELS = {"cash_schedule", "enterprise_cash_fcff"}
CORE_FIELDS = ("revenue", "operating_cash_flow", "capital_expenditures", "sbc")
FORBIDDEN_OUTPUT_KEYS = {"intrinsic_value_per_share", "present_value", "enterprise_value", "equity_value",
                         "forecast_schedule", "terminal_value", "cash_flows", "recipe"}
SOURCE_HASH_KEYS = {"input_sha256", "period_sha256", "source_packet_sha256", "review_sha256"}


def sha256_format(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(value: Mapping[str, Any]) -> str:
    return digest(canonical_json_bytes(value))


def number(value: Any, name: str) -> float:
    require(not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value), f"{name}: finite number required")
    return float(value)


def _no_valuation_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        require(not FORBIDDEN_OUTPUT_KEYS.intersection(value), "valuation/forecast output is outside this stage")
        for child in value.values():
            _no_valuation_keys(child)
    elif isinstance(value, list):
        for child in value:
            _no_valuation_keys(child)


def validate_approval(pack: Mapping[str, Any], pack_sha256: str, approval: Mapping[str, Any]) -> None:
    require(approval.get("schema_version") == APPROVAL_VERSION, "approval schema")
    require(approval.get("assumption_pack_sha256") == pack_sha256, "approved assumption pack changed")
    require(sha256_format(pack_sha256) and content_hash(pack) == approval.get("assumption_pack_canonical_sha256"), "approved pack content changed independently of caller hash")
    require(approval.get("approved_scope") == "private_policy_binding_and_accounting_input_readiness_only", "approval scope")
    require(approval.get("approved_by") == "human_user_in_current_chat", "human approval missing")
    require(set(approval.get("forced_held", [])) == {"FELE", "WCC"}, "forced holds changed")
    require(approval.get("evidence_cutoff") == pack.get("evidence_cutoff") == pack.get("valuation_date") == approval.get("valuation_date"), "approval cutoff mismatch")
    for key in ("forecast_execution_authorized", "valuation_execution_authorized", "catalog_admission_authorized", "active_policy_promotion_authorized"):
        require(approval.get(key) is False, f"{key}: wider authority is not this stage")


def compile_contract(pack: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any] | None:
    """Consume the approved parameters, but emit no future monetary schedule."""
    if row["recommendation"] == "held":
        require(row["model"] is None and row["initial_growth"] is None and row["discount_rates"] is None, "held issuer has executable assumptions")
        return None
    model = row["model"]
    require(model in MODELS, "unsupported expansion model")
    equity = model == "cash_schedule"
    require(pack["scenario_order"] == ["bear", "base", "bull"], "scenario ordering")
    require(row["growth_metric"] == ("revenue" if equity else "cash_fcff"), "growth metric/engine mismatch")
    require(row["discount_metric"] == ("cost_of_equity" if equity else "wacc"), "discount metric/engine mismatch")
    require(row["years"] == (5 if equity else 8), "forecast horizon contract")
    require(pack["cash_normalization_multiplier_basis"] == "pre_investment_cash_apply_once_before_total_investment", "normalization double-count basis")
    require(pack["starting_cash_basis_by_model"][model] == ("pre_investment_after_interest_owner_cash" if equity else "net_fcff_after_total_investment"), "starting cash basis")
    scenarios = {}
    vectors = [row["initial_growth"], row["discount_rates"], pack["terminal_growth"], row["cash_normalization_multiplier"], pack["investment_budget_multiplier"]]
    require(all(len(vector) == 3 for vector in vectors), "scenario vector coverage")
    for index, name in enumerate(pack["scenario_order"]):
        growth, discount, terminal, cash_multiplier, investment_multiplier = [number(vector[index], name) for vector in vectors]
        require(-1 < growth < 1 and 0 <= terminal <= .025 and discount - terminal >= .025, "growth/discount/terminal contract")
        require(cash_multiplier > 0 and investment_multiplier >= 1, "cash/investment stress")
        scenarios[name] = {"initial_growth": growth, "terminal_growth": terminal, "discount_rate": discount,
                           "pre_investment_cash_multiplier": cash_multiplier, "investment_budget_multiplier": investment_multiplier,
                           "classification": "FINSIGHT_ASSUMPTION"}
        if not equity:
            for value in (pack["enterprise_cash_credit_fraction"][index], pack["positive_book_nci_proxy_multiplier"][index]):
                number(value, "bridge policy multiplier")
            require(0 <= pack["enterprise_cash_credit_fraction"][index] <= 1 and pack["positive_book_nci_proxy_multiplier"][index] >= 1, "bridge cash/NCI proxy range")
            scenarios[name].update(cash_credit_fraction=pack["enterprise_cash_credit_fraction"][index],
                                  positive_book_nci_multiplier=pack["positive_book_nci_proxy_multiplier"][index])
    require(row["initial_growth"] == sorted(row["initial_growth"]), "growth scenario ordering")
    require(row["discount_rates"] == sorted(row["discount_rates"], reverse=True), "discount scenario ordering")
    result = {"model": model, "years": row["years"], "growth_metric": row["growth_metric"],
              "discount_metric": row["discount_metric"], "scenarios": scenarios,
              "growth_rule": "absolute_initial_growth_linear_fade_to_terminal_no_observed_growth_override",
              "normalization_basis": row.get("normalization_basis", "lower_current_and_comparable_history_pre_investment_cash"),
              "investment_consumption": "annual_ratio_in_later_equity_schedule" if equity else "subtract_once_from_pre_investment_cash_to_form_net_FCFF_seed",
              "operating_lease_policy": "rent_inside_CFO_no_operating_lease_debt_addition",
              "finance_lease_policy": "after_interest_owner_cash_requires_principal_if_present" if equity else "claim_in_debt_once_asset_additions_in_investment_no_second_principal_deduction",
              "ownership_policy": "SBC_expense_proxy_point_common_shares_not_fully_diluted",
              "acquisition_policy": "no_future_acquisitions_no_unsourced_synergies_no_second_historical_purchase_deduction",
              "future_funding_assumption": "zero_new_net_borrowing_existing_maturities_refinanced",
              "tax_proxy": None if equity else pack["financing_tax_proxy"],
              "future_capex_schedule_supported": equity,
              "enterprise_future_reinvestment": None if equity else "sustainable_burden_assumed_in_FCFF_fade_not_an_explicit_capex_schedule",
              "source_claims_and_assumptions_count_once": True}
    if row.get("finance_lease_allowance"):
        allowance = deepcopy(row["finance_lease_allowance"])
        require(allowance["current_reported_value"] is None and allowance["not_current_fact"] is True and allowance["not_upper_bound"] is True, "dated lease allowance mislabeled")
        require(allowance["count_once"] == "gross_debt_bridge_if_not_included" and allowance.get("expiry"), "allowance nonoverlap/expiry")
        result["finance_lease_allowance"] = allowance
    if row.get("FY2026_total_capex_plan_USD"):
        result["annual_equivalent_cash_capex_seed_override"] = deepcopy(row["FY2026_total_capex_plan_USD"])
    if not equity:
        require(0 <= number(pack["financing_tax_proxy"], "tax proxy") <= 1, "tax proxy range")
    _no_valuation_keys(result)
    return result


def required_gates(pack: Mapping[str, Any], row: Mapping[str, Any]) -> list[str]:
    if row["recommendation"] == "held":
        return list(row["gates"])
    shared = pack["shared_equity_blocking_gates"] if row["model"] == "cash_schedule" else pack["shared_enterprise_blocking_gates"]
    lease = pack["shared_lease_allowance_blocking_gates"] if row.get("finance_lease_allowance") else []
    return sorted(set([*row["gates"], *shared, *lease]))


def _validate_period_fact(fact: Mapping[str, Any], cutoff: str, *, unit="USD") -> None:
    number(fact.get("value"), "fact value")
    require(str(fact.get("unit", "")).removeprefix("xbrli:") == unit, "source fact unit")
    require(fact.get("source_accession") and fact.get("qname"), "source fact identity")
    end = fact.get("period_end")
    require(isinstance(end, str) and date.fromisoformat(end).isoformat() <= cutoff, "source period cutoff")
    filed = fact.get("filed_date")
    if filed is not None:
        require(date.fromisoformat(filed).isoformat() <= cutoff, "source filing cutoff")


def bind_core_sources(row: Mapping[str, Any], inputs: Mapping[str, Any], periods: Mapping[str, Any], cutoff: str) -> dict[str, Any]:
    require(inputs["ticker"] == row["ticker"] == periods["ticker"], "source ticker mismatch")
    require(inputs["cik"] == row["cik"] == periods["cik"], "source CIK mismatch")
    filing = periods["controlling_filing"]
    require(filing["filingDate"] <= cutoff and filing["reportDate"] <= cutoff and periods["cutoff"] == cutoff, "controlling source cutoff")
    annual_ends = periods["requested_recent_annual_ends"]
    require(len(annual_ends) == len(set(annual_ends)) == 5 and annual_ends == sorted(annual_ends), "recent annual source count/order")
    result = {"controlling_filing": deepcopy(filing), "cutoff": cutoff, "fiscal_fields": {}, "shares": deepcopy(inputs["shares"]),
              "reported_balances": deepcopy(inputs["reported_balances"]), "reported_debt": deepcopy(inputs["debt"])}
    for field in CORE_FIELDS:
        series = deepcopy(periods["fields"][field])
        require([fact["period_end"] for fact in series["annual"]] == annual_ends, f"{field}: stale/incomplete recent annual history")
        for fact in series["annual"]:
            _validate_period_fact(fact, cutoff)
            require(fact.get("form") in {"10-K", "10-K/A"} and fact.get("filed_date"), "annual source form/filing date missing")
            require(fact.get("period_start") and 330 <= (date.fromisoformat(fact["period_end"]) - date.fromisoformat(fact["period_start"])).days + 1 <= 385, "source period is not annual")
        if filing["form"] in {"10-Q", "10-Q/A"}:
            current, prior, rolling = series["current_fiscal_ytd"], series["prior_fiscal_ytd"], series["derived_ttm"]
            require(current is not None and prior is not None and rolling is not None, f"{field}: fiscal comparative/TTM missing")
            _validate_period_fact(current, cutoff)
            _validate_period_fact(prior, cutoff)
            require(current["source_accession"] == prior["source_accession"] == filing["accessionNumber"], "different-accession fiscal comparatives")
            require(current["period_end"] == filing["reportDate"], "noncurrent YTD")
            require(rolling["value"] == series["annual"][-1]["value"] + current["value"] - prior["value"], "TTM arithmetic changed")
            require(rolling["alignment"]["fiscal_start_match"] and rolling["alignment"]["annual_to_current_adjacent"], "unmatched fiscal windows")
            require(330 <= rolling["duration_days"] <= 385, "nonannual TTM window")
        result["fiscal_fields"][field] = series
    for index in range(5):
        windows = {(result["fiscal_fields"][field]["annual"][index]["period_start"], result["fiscal_fields"][field]["annual"][index]["period_end"]) for field in CORE_FIELDS}
        require(len(windows) == 1, "historical cash/revenue/SBC/capex periods differ")
    point = result["shares"]["balance_date"]
    if row["point_shares"] is not None:
        require(point.get("qname") or (point.get("classification") == "derived" and point.get("operands")), "point shares lack reported or derived source identity")
        require(str(point.get("unit", "")).removeprefix("xbrli:") == "shares", "point shares unit missing")
        if point.get("qname"):
            _validate_period_fact(point, cutoff, unit="shares")
            require(point["source_accession"] == filing["accessionNumber"], "point shares not from controlling filing")
        require(number(point["value"], "point shares") == row["point_shares"] > 0, "point share count changed")
        require(point["period_end"] == filing["reportDate"], "point shares are not balance-date shares")
        if point.get("operands"):
            for fact in point["operands"]:
                _validate_period_fact(fact, cutoff, unit="shares")
                require(fact["period_end"] == point["period_end"], "share operand dates differ")
            formula = point["formula"].lower()
            values = [number(fact["value"], "share operand") for fact in point["operands"]]
            calculated = values[0] - values[1] if "issued shares - treasury shares" in formula else sum(values)
            require(calculated == point["value"], "share operand arithmetic changed")
    return result


def equity_normalization(sources: Mapping[str, Any], contract: Mapping[str, Any], source_plans: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Historical cash-input normalization only; no forecast or discounting."""
    require(contract["model"] == "cash_schedule", "equity normalization lane")
    require(sources["controlling_filing"]["form"] == "10-K", "equity compiler requires full FY, not YTD annualization")
    fields = sources["fiscal_fields"]
    revenue = [number(fact["value"], "revenue") for fact in fields["revenue"]["annual"]]
    cfo = [number(fact["value"], "CFO") for fact in fields["operating_cash_flow"]["annual"]]
    sbc = [number(fact["value"], "SBC") for fact in fields["sbc"]["annual"]]
    capex = [number(fact["value"], "capex") for fact in fields["capital_expenditures"]["annual"]]
    require(min(revenue) > 0 and min(sbc + capex) >= 0, "source cash/spending sign")
    pre = [cash - award for cash, award in zip(cfo, sbc)]
    margins = [cash / sales for cash, sales in zip(pre, revenue)]
    investment_ratios = [spending / sales for spending, sales in zip(capex, revenue)]
    margin = min(margins[-1], median(margins))
    investment = max(investment_ratios[-1], median(investment_ratios))
    require(cfo[-1] - sbc[-1] - capex[-1] > 0, "nonpositive current owner cash needs funded recovery")
    checks = {}
    source_plans = source_plans or {}
    capex_plan = source_plans.get("annual_equivalent_total_cash_capex")
    dated_claims = source_plans.get("dated_acquisition_claims", [])
    known_claim_total = sum(number(claim["amount_USD"], "dated acquisition claim") for claim in dated_claims)
    require(known_claim_total >= 0, "negative dated cash claim")
    if capex_plan:
        require(capex_plan.get("scope") == "total_capex_replaces_not_adds_to_normal_budget" and capex_plan.get("source_reference"), "source capital-plan scope")
        require(set(capex_plan["amounts_USD"]) == set(contract["scenarios"]), "capital-plan scenario coverage")
        low = number(capex_plan.get("reported_guidance_low_USD"), "source guidance low")
        high = number(capex_plan.get("reported_guidance_high_USD"), "source guidance high")
        require(0 < low <= high and capex_plan.get("source_accession") and capex_plan.get("filed_date") <= sources["cutoff"], "capital-plan source/range identity")
        amounts = [number(capex_plan["amounts_USD"][name], "source capex scenario") for name in ("bear", "base", "bull")]
        require(all(low <= value <= high for value in amounts) and amounts == sorted(amounts, reverse=True), "capital-plan budget outside supported guide/order")
    for claim in dated_claims:
        require(claim.get("source_accession") and claim.get("source_date") <= sources["cutoff"] and claim.get("reported_payment_window"), "dated claim identity/window missing")
    for name, scenario in contract["scenarios"].items():
        cash_margin = margin * scenario["pre_investment_cash_multiplier"]
        if name == "bull":
            cash_margin = min(cash_margin, max(margins))
        investment_ratio = investment * scenario["investment_budget_multiplier"]
        if capex_plan:
            investment_ratio = max(investment_ratio, number(capex_plan["amounts_USD"][name], "source-linked total capex budget") / revenue[-1])
        owner_budget = revenue[-1] * (cash_margin - investment_ratio)
        require(owner_budget - known_claim_total > 0, f"{name}: nonpositive normalized owner cash after known cash claims requires recovery")
        checks[name] = {"cash_margin": cash_margin, "full_investment_ratio": investment_ratio,
                        "anchor_period_owner_cash_budget_USD": owner_budget,
                        "positive_cash_after_all_known_acquisition_claims": owner_budget - known_claim_total > 0,
                        "cash_margin_basis": "pre_investment_after_interest_CFO_less_SBC", "investment_deductions": 1}
    return {"classification": "derived_accounting_inputs_and_approved_FINSIGHT_ASSUMPTIONS",
            "period_ends": fields["revenue"]["annual_period_ends_observed"], "reported_revenue_USD": revenue,
            "reported_CFO_USD": cfo, "reported_SBC_USD": sbc, "reported_total_capex_USD": capex,
            "pre_investment_owner_cash_USD": pre, "historical_pre_investment_cash_margins": margins,
            "base_pre_investment_cash_margin": margin, "base_full_investment_ratio": investment,
            "current_owner_cash_USD": cfo[-1] - sbc[-1] - capex[-1], "scenario_anchor_checks": checks,
            "source_aware_plan_bindings": deepcopy(source_plans), "known_dated_claim_total_USD": known_claim_total,
            "claim_cash_timing": "source_windows_retained_later_forecast_must_deduct_once_no_extra_enterprise_bridge",
            "interest_addbacks": 0, "cash_bridge_additions": 0, "gross_debt_subtractions": 0,
            "extra_generic_dilution_factors": 0, "forecasts_built": False}


def enterprise_normalization(sources: Mapping[str, Any], contract: Mapping[str, Any], accounting: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize historical and rolling input cash, never forecast net FCFF.

    All component series must cover the exact cash windows. A complete-statement
    scope proof can declare that no separate intangible line is to be added;
    it does not manufacture reported intangible zeroes. Financing expense is
    represented income-positive/expense-negative. Reverse net financing using
    the approved tax proxy, then remove the full noncash fee amount already in
    CFO. This also removes the assumed fee tax shield; the shield is a reviewed
    tax-normalization assumption, not a reported incremental cash-tax fact.
    """
    require(contract["model"] == "enterprise_cash_fcff", "enterprise normalization lane")
    require(accounting.get("financing_basis") in {"signed_net_financing", "gross_components_role_and_cash_reconciled"}, "role-qualified financing basis required")
    require(accounting.get("role_qualified") is True and accounting.get("role_evidence"), "accounting role evidence missing")
    require(accounting.get("net_fee_scope") == "reported_accrual_includes_noncash_fee_expense", "declared net financing fee scope required")
    require(accounting.get("fee_tax_policy") == "full_CFO_fee_reversal_after_financing_tax_proxy_conservative_fee_shield_removal", "fee-tax reconciliation policy missing")
    fields = sources["fiscal_fields"]
    anchors = fields["operating_cash_flow"]
    concepts = {"noncash_financing_fees", "financed_asset_additions", "pretax_income"}
    concepts.update({"net_financing"} if accounting["financing_basis"] == "signed_net_financing" else {"gross_expense", "interest_income"})
    intangible_scope = accounting.get("intangible_scope")
    require(intangible_scope in {"separately_reported_disjoint", "complete_investing_statement_no_separate_line"}, "intangible cash scope unresolved")
    if intangible_scope == "separately_reported_disjoint":
        concepts.add("intangible_investment")
    components = {}
    for name in concepts:
        series = accounting.get(name)
        require(isinstance(series, Mapping) and len(series.get("annual", [])) == 5, f"{name}: complete five-period binding required")
        for fact, reference in zip(series["annual"], anchors["annual"]):
            require(fact is not None, f"{name}: missing annual fact is not zero")
            _validate_period_fact(fact, sources["cutoff"])
            require((fact["period_start"], fact["period_end"]) == (reference["period_start"], reference["period_end"]), f"{name}: annual windows differ")
        for role in ("current_fiscal_ytd", "prior_fiscal_ytd"):
            fact, reference = series.get(role), anchors.get(role)
            if reference is not None:
                require(fact is not None, f"{name}: missing cumulative comparison is not zero")
                _validate_period_fact(fact, sources["cutoff"])
                require((fact["period_start"], fact["period_end"], fact["source_accession"]) == (reference["period_start"], reference["period_end"], reference["source_accession"]), f"{name}: fiscal/current filing identity differs")
        components[name] = series
    require(accounting.get("interest_income_second_subtraction") is False, "net financing plus second income subtraction")
    require(accounting.get("capitalized_interest_treatment") == "retained_inside_source_total_asset_investment_not_added_to_expense_again", "capitalized-interest scope not reviewed")
    def at(series, index):
        if index == "rolling":
            rolling = series.get("derived_ttm")
            require(rolling is not None, "missing component accounting TTM")
            return number(rolling["value"], "rolling component")
        return number(series["annual"][index]["value"], "annual component")
    def cash_row(index):
        revenue = at(fields["revenue"], index)
        cfo = at(fields["operating_cash_flow"], index)
        sbc = at(fields["sbc"], index)
        capex = at(fields["capital_expenditures"], index)
        fees, leased, pretax = [at(components[name], index) for name in ("noncash_financing_fees", "financed_asset_additions", "pretax_income")]
        if accounting["financing_basis"] == "signed_net_financing":
            require(accounting.get("signed_net_convention") == "income_positive_expense_negative", "signed financing convention missing")
            net = at(components["net_financing"], index)
        else:
            gross, income = at(components["gross_expense"], index), at(components["interest_income"], index)
            require(gross >= 0 and income >= 0, "gross expense/income signs")
            net = income - gross
        require(revenue > 0 and min(sbc, capex, fees, leased) >= 0, "historical cash/asset-investment sign")
        intangible = at(components["intangible_investment"], index) if "intangible_investment" in components else None
        require(intangible is None or intangible >= 0, "intangible investment sign")
        tax = contract["tax_proxy"] if pretax >= 0 else 0.0
        adjustment = -net * (1 - tax) - fees
        pre = cfo - sbc + adjustment
        investment = capex + leased + (intangible if intangible is not None else 0.0)
        return {"revenue_USD": revenue, "CFO_USD": cfo, "SBC_USD": sbc, "signed_net_financing_USD": net,
                "noncash_financing_fees_excluded_USD": fees, "financing_tax_proxy": tax,
                "fee_tax_shield_removed_by_proxy_USD": fees * tax,
                "financing_adjustment_USD": adjustment, "pre_investment_cash_USD": pre,
                "cash_capex_USD": capex, "separately_reported_intangible_USD": intangible,
                "financed_asset_additions_USD": leased, "full_economic_investment_USD": investment,
                "reported_period_net_cash_input_USD": pre - investment}
    history = [cash_row(index) for index in range(5)]
    current = cash_row("rolling")
    require(current["reported_period_net_cash_input_USD"] > 0, "nonpositive current full-cycle cash requires funded recovery; historical median cannot repair it")
    revenue = current["revenue_USD"]
    if (contract["normalization_basis"].startswith("comparable_pre_investment_dollar_cash")
        or accounting.get("normalization_scope") == "reviewed_dollar_group_cash_no_organic_comparability"):
        anchor = min(current["pre_investment_cash_USD"], median(row["pre_investment_cash_USD"] for row in history))
    else:
        anchor = min(current["pre_investment_cash_USD"], median(row["pre_investment_cash_USD"] / row["revenue_USD"] for row in history) * revenue)
    investment_ratio = max(current["full_economic_investment_USD"] / revenue,
                           median(row["full_economic_investment_USD"] / row["revenue_USD"] for row in history))
    scenarios = {}
    for index, (name, scenario) in enumerate(contract["scenarios"].items()):
        pre = anchor * scenario["pre_investment_cash_multiplier"]
        if name == "bull":
            pre = min(pre, max(row["pre_investment_cash_USD"] for row in history))
        budget = revenue * investment_ratio * scenario["investment_budget_multiplier"]
        if contract.get("annual_equivalent_cash_capex_seed_override"):
            budget = contract["annual_equivalent_cash_capex_seed_override"][index] + current["financed_asset_additions_USD"]
            if current["separately_reported_intangible_USD"] is not None:
                budget += current["separately_reported_intangible_USD"]
        seed = pre - budget
        scenarios[name] = {"pre_investment_cash_anchor_USD": pre, "full_investment_budget_USD": budget,
                           "net_FCFF_starting_input_USD": seed, "investment_deductions": 1,
                           "positive_seed": seed > 0, "classification": "derived_inputs_with_approved_FINSIGHT_ASSUMPTIONS"}
    require(all(row["positive_seed"] for row in scenarios.values()), "one or more normalized FCFF starting inputs are nonpositive; no floor allowed")
    require(scenarios["bear"]["net_FCFF_starting_input_USD"] <= scenarios["base"]["net_FCFF_starting_input_USD"] <= scenarios["bull"]["net_FCFF_starting_input_USD"], "normalization scenarios cross; review assumptions rather than reorder")
    return {"classification": "derived_accounting_inputs_with_approved_FINSIGHT_ASSUMPTIONS",
            "historical_inputs": history, "rolling_inputs": current, "base_pre_investment_cash_anchor_USD": anchor,
            "base_full_investment_ratio": investment_ratio, "scenario_starting_inputs": scenarios,
            "financing_basis": accounting["financing_basis"], "full_CFO_fee_reversal": True,
            "fee_tax_policy": accounting["fee_tax_policy"],
            "normalization_scope": accounting.get("normalization_scope", contract["normalization_basis"]),
            "interest_income_second_subtraction": False, "intangible_scope": intangible_scope,
            "capitalized_interest_treatment": accounting["capitalized_interest_treatment"],
            "forecasts_built": False, "capex_investment_deducted_once": True}


def prepare_enterprise_inputs(sources: Mapping[str, Any], contract: Mapping[str, Any], normalization: Mapping[str, Any], bridge: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble undiscounted engine arguments without instantiating its state."""
    balances = sources["reported_balances"]
    cash = balances.get("cash")
    require(cash is not None and bridge.get("cash_source") == cash, "available cash source binding differs")
    debt = sources["reported_debt"].get("gross_principal_source")
    require(debt is not None and bridge.get("gross_debt_source") == debt, "gross debt source incomplete/different")
    cash_value, debt_value = number(cash["value"], "cash credit basis"), number(debt["value"], "gross financing claim")
    require(min(cash_value, debt_value) >= 0, "cash/debt bridge sign")
    require(bridge.get("finance_leases_included_once") is True and bridge.get("operating_leases_added_to_debt") is False, "lease bridge double count")
    require(bridge.get("cash_scope") == "reported_unrestricted_cash_no_unbound_investment_addition", "cash scope not proven")
    require(bridge.get("income_removed_once") is True, "asset credit and investment income overlap")
    nci, preferred = number(bridge.get("nci_claim_basis_USD"), "NCI claim basis"), number(bridge.get("preferred_claim_basis_USD"), "preferred claim basis")
    require(min(nci, preferred) >= 0 and bridge.get("ownership_scope_proof"), "owner claims missing/source negative NCI cannot be a credit")
    require(bridge.get("NCI_distribution_second_deduction") is False, "NCI double deduction")
    require(bridge.get("known_additional_claims_review") and isinstance(bridge.get("nonoperating_adjustment_USD"), (int, float)), "separate known claims not reviewed")
    shares = number(sources["shares"]["balance_date"]["value"], "point common shares")
    result = {}
    for name, scenario in contract["scenarios"].items():
        result[name] = {
            "cash_fcff": normalization["scenario_starting_inputs"][name]["net_FCFF_starting_input_USD"],
            "initial_growth": scenario["initial_growth"], "terminal_growth": scenario["terminal_growth"],
            "wacc": scenario["discount_rate"], "cash_and_investments": cash_value * scenario["cash_credit_fraction"],
            "interest_bearing_debt": debt_value, "preferred_equity": preferred,
            "noncontrolling_interests": nci * scenario["positive_book_nci_multiplier"],
            "diluted_shares": shares, "nonoperating_adjustment": number(bridge["nonoperating_adjustment_USD"], "signed separate claim adjustment")}
    return {"engine": "enterprise_cash_fcff", "arguments_not_executed": result,
            "forecast_years": contract["years"], "denominator_field_semantics": "engine_diluted_shares_slot_contains_approved_point_common_share_proxy_not_reported_diluted_shares",
            "source_bridge": deepcopy(bridge), "model_instantiated": False, "valuation_called": False}


def _seal(record: dict[str, Any]) -> dict[str, Any]:
    _no_valuation_keys(record)
    return {**record, "integrity_sha256": content_hash(record)}


def bind_policy(pack: Mapping[str, Any], row: Mapping[str, Any], approval: Mapping[str, Any], *,
                pack_sha256: str, approval_sha256: str, inputs: Mapping[str, Any], periods: Mapping[str, Any],
                provenance: Mapping[str, Any], gate_reviews: Mapping[str, Any], accounting_inputs: Mapping[str, Any] | None = None,
                source_plans: Mapping[str, Any] | None = None, bridge_inputs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    validate_approval(pack, pack_sha256, approval)
    require(sha256_format(approval_sha256) and content_hash(approval) == approval_sha256, "approval content/hash mismatch")
    contract = compile_contract(pack, row)
    require(isinstance(periods, Mapping) and "source_ledger" in periods, "complete frozen period record required")
    sources = bind_core_sources(row, inputs, periods["source_ledger"], pack["evidence_cutoff"])
    require(all(sha256_format(provenance.get(key)) for key in SOURCE_HASH_KEYS), "source fingerprints missing/invalid")
    require(content_hash(inputs) == provenance["input_sha256"], "input bytes/content disagree")
    require("source_ledger" in periods and content_hash(periods) == provenance["period_sha256"], "period record bytes/content disagree")
    summary = provenance.get("step4_summary")
    require(isinstance(summary, Mapping) and content_hash(summary) == pack["step4_summary_sha256"], "frozen Step4 source authority mismatch")
    summary_rows = [value for value in summary["rows"] if value["ticker"] == row["ticker"]]
    require(len(summary_rows) == 1 and summary_rows[0]["input_sha256"] == provenance["input_sha256"], "issuer input not approved frozen summary")
    require(inputs["source_packet_sha256"] == provenance["source_packet_sha256"] and inputs["step4_source_reconciliation"]["period_ledger_sha256"] == provenance["period_sha256"], "source chain changed")
    require(isinstance(provenance.get("verified_review"), Mapping) and content_hash(provenance["verified_review"]) == provenance["review_sha256"], "review content/hash mismatch")
    require(approval.get("implemented_review_canonical_sha256") == provenance["review_sha256"], "source-review decisions not pinned by implementation record")
    require(provenance["verified_review"].get("gate_reviews", {}).get(row["ticker"], {}) == gate_reviews, "gate decisions differ from pinned source review")
    for key, actual in (("accounting_inputs", accounting_inputs), ("source_plans", source_plans), ("bridge_inputs", bridge_inputs)):
        require(provenance["verified_review"].get(key, {}).get(row["ticker"]) == actual, f"{key}: supplied inputs differ from pinned source review")
    evidence_registry = provenance["verified_review"].get("evidence_registry", {})
    required = required_gates(pack, row)
    unknown = set(gate_reviews) - set(required)
    require(not unknown, "unknown gate cannot bypass compiler: " + str(sorted(unknown)))
    gates = {}
    for name in required:
        gate = deepcopy(gate_reviews.get(name, {"status": "open", "reason": "No source-qualified gate proof bound."}))
        require(gate.get("status") in {"verified", "open", "pending_derived"}, "unrecognized gate status")
        if gate["status"] in {"verified", "pending_derived"}:
            require(gate.get("reason") and gate.get("evidence") and gate.get("verified_by") == "main_agent", "gate proof/review missing")
            require(all(reference in evidence_registry for reference in gate["evidence"]), "gate cites nonexistent/unverified source evidence")
        gates[name] = gate
    forced = row["ticker"] in approval["forced_held"]
    require(not forced or row["recommendation"] == "held", "forced hold changed into candidate")
    normalization = None
    def derived_pass(name, check, reason, pointers):
        if name not in gates:
            return
        original = gates[name]
        # A deliberately open source scope cannot be cleared by arithmetic.
        require(original["status"] == "pending_derived" and original.get("binding_check") == check, f"{name}: derived check was not declared in pinned review")
        gates[name] = {**original, "status": "verified", "reason": reason,
                       "evidence_type": "binder_derived_reconstructed_from_pinned_inputs_not_reported_fact",
                       "output_pointers": pointers}
    if not forced and contract["model"] == "cash_schedule":
        try:
            normalization = equity_normalization(sources, contract, source_plans)
            # A positive arithmetic check does not substitute for other gates.
            for name in ("positive_owner_cash",):
                derived_pass(name, "equity_positive_cash_check", "Current and three normalized anchor-period owner-cash budgets are positive without a floor or median recovery.",
                             ["normalization/current_owner_cash_USD", "normalization/scenario_anchor_checks"])
            for name in ("fixed_growth_override", "fixed_growth_fiscal_input_binder_implemented"):
                if name in gates:
                    derived_pass(name, "fixed_growth_fiscal_contract_check", "The source-policy compiler consumes absolute rates and exact FY anchors; the observed-growth/delta builder is not invoked. Future forecast execution is not claimed.",
                                 ["contract/growth_rule", "contract/scenarios", "sources/fiscal_fields"])
        except ValueError as error:
            if gates["positive_owner_cash"]["status"] != "open":
                gates["positive_owner_cash"] = {"status": "open", "reason": str(error)}
    elif not forced and contract["model"] == "enterprise_cash_fcff":
        try:
            require(accounting_inputs is not None, "complete role-qualified financing/investment inputs not bound; no zero defaults")
            normalization = enterprise_normalization(sources, contract, accounting_inputs)
            derived_pass("positive_normalized_cash_fcff", "enterprise_positive_cash_check", "Current full-cycle cash and every normalized FCFF input are positive, with investment deducted once and no floor.",
                         ["normalization/rolling_inputs", "normalization/scenario_starting_inputs"])
            if "positive_normalized_cash" in gates:
                derived_pass("positive_normalized_cash", "enterprise_positive_cash_check", "Normalized cash input arithmetic passed; named unknown obligations remain separate blocking gates.", ["normalization/scenario_starting_inputs"])
            if "full_cycle_positive_cash" in gates:
                derived_pass("full_cycle_positive_cash", "enterprise_positive_cash_check", "Full-season current accounting cash and normalized inputs are positive; H1 is not annualized.", ["normalization/rolling_inputs"])
        except ValueError as error:
            gates["positive_normalized_cash_fcff"] = {"status": "open", "reason": str(error)}
    remaining = [name for name, gate in gates.items() if gate["status"] != "verified"]
    prepared_inputs = None
    if not forced and contract["model"] == "enterprise_cash_fcff" and normalization is not None and not remaining:
        try:
            require(bridge_inputs is not None, "complete equity-bridge inputs not bound")
            prepared_inputs = prepare_enterprise_inputs(sources, contract, normalization, bridge_inputs)
        except ValueError as error:
            gates["cash_asset_scope_and_income_nonoverlap"] = {"status": "open", "reason": str(error)}
            remaining = [name for name, gate in gates.items() if gate["status"] != "verified"]
    ready = not forced and not remaining
    record = {"schema_version": VERSION, "ticker": row["ticker"], "cik": row["cik"],
              "valuation_date": pack["valuation_date"], "evidence_cutoff": pack["evidence_cutoff"],
              "approved_assumption_pack_sha256": pack_sha256, "approval_sha256": approval_sha256,
              "approval_scope": approval["approved_scope"], "provenance": deepcopy(provenance),
              "policy_status": "ready_for_separately_authorized_forecast_and_calculation" if ready else "held_gate_enforced",
              "policy_ready": ready, "forced_held": forced, "contract_implemented": contract is not None,
              "contract": contract, "sources": sources, "normalization": normalization,
              "accounting_inputs": deepcopy(accounting_inputs), "source_aware_plan_bindings": deepcopy(source_plans),
              "bridge_inputs": deepcopy(bridge_inputs), "prepared_engine_inputs": prepared_inputs,
              "gates": gates, "remaining_gates": remaining,
              "denominator_proxy": {"type": pack["share_denominator_proxy_type"], "not_fully_diluted": pack["not_fully_diluted"],
                                    "source_date": sources["shares"]["balance_date"]["period_end"], "class_scope_and_operands": deepcopy(sources["shares"]["balance_date"])},
              "forecast_execution_authorized": False, "valuation_execution_authorized": False,
              "forecasts_built": False, "recipes_built": False, "valuations_calculated": False,
              "changes_active_catalog": False, "economic_calibration": "unvalidated"}
    return _seal(record)


def validate_bound_policy(record: Mapping[str, Any], *, pack: Mapping[str, Any], pack_sha256: str,
                          approval: Mapping[str, Any], approval_sha256: str, source_hashes: Mapping[str, str],
                          inputs: Mapping[str, Any], periods: Mapping[str, Any], provenance: Mapping[str, Any],
                          gate_reviews: Mapping[str, Any], accounting_inputs: Mapping[str, Any] | None = None,
                          source_plans: Mapping[str, Any] | None = None, bridge_inputs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Real private consumer: reject stale sources, tampering and false readiness."""
    validate_approval(pack, pack_sha256, approval)
    require(set(source_hashes) == SOURCE_HASH_KEYS and all(sha256_format(value) for value in source_hashes.values()), "complete trusted source hash set required")
    require(content_hash(approval) == approval_sha256, "approval fingerprint mismatch")
    value = deepcopy(dict(record))
    seal = value.pop("integrity_sha256", None)
    require(seal == content_hash(value), "bound policy integrity changed")
    require(value["schema_version"] == VERSION, "binding version")
    require(value["approved_assumption_pack_sha256"] == pack_sha256 and value["approval_sha256"] == approval_sha256, "policy approval fingerprint drift")
    require(value["evidence_cutoff"] == pack["evidence_cutoff"], "bound cutoff drift")
    for key, expected in source_hashes.items():
        require(value["provenance"].get(key) == expected, f"{key}: frozen source drift")
    rows = [row for row in pack["issuers"] if row["ticker"] == value["ticker"] and row["cik"] == value["cik"]]
    require(len(rows) == 1, "bound issuer not in approved selection")
    require(value["contract"] == compile_contract(pack, rows[0]), "approved scenario semantics changed")
    required = required_gates(pack, rows[0])
    require(set(value["gates"]) == set(required), "required gate was removed")
    remaining = sorted(name for name, gate in value["gates"].items() if gate["status"] != "verified")
    require(remaining == sorted(value["remaining_gates"]), "remaining gate register differs")
    forced = value["ticker"] in approval["forced_held"]
    require(value["forced_held"] == forced and value["policy_ready"] == (not forced and not remaining), "false readiness/forced hold bypass")
    require(value["policy_status"] == ("ready_for_separately_authorized_forecast_and_calculation" if value["policy_ready"] else "held_gate_enforced"), "status/readiness mismatch")
    for key in ("forecast_execution_authorized", "valuation_execution_authorized", "forecasts_built", "recipes_built", "valuations_calculated", "changes_active_catalog"):
        require(value[key] is False, f"{key}: scope violation")
    _no_valuation_keys(value)
    rebuilt = bind_policy(pack, rows[0], approval, pack_sha256=pack_sha256, approval_sha256=approval_sha256,
                          inputs=inputs, periods=periods, provenance=provenance, gate_reviews=gate_reviews,
                          accounting_inputs=accounting_inputs, source_plans=source_plans, bridge_inputs=bridge_inputs)
    require(content_hash(rebuilt) == content_hash(record), "binding no longer reconstructs from frozen source authority")
    return dict(record)


__all__ = ["VERSION", "bind_policy", "compile_contract", "required_gates", "validate_bound_policy", "equity_normalization", "enterprise_normalization"]
