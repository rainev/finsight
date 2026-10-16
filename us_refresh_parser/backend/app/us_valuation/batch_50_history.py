"""Source-bounded practical baselines for controlled Universe Reset Batch 50."""
from __future__ import annotations

import hashlib
from html import unescape
import json
from pathlib import Path
import re
from statistics import median
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_04_launch_first import _controlling
from .batch_35_history import _instant
from .batch_40_history import _latest_shares
from .batch_50 import BATCH_50_TICKERS, BATCH_50_VALUATION_DATE
from .batch_50_sources import verify_source_bundle
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf, two_stage_cash_flow_value
from .reliability import assess_reliability

BATCH_50_HISTORY_VERSION = "BATCH-50-MIXED-REAL-ESTATE-1.0"
PERIOD = "2026-06-30"
PASS_TICKERS = frozenset()
WITHHELD_TICKERS = frozenset()
CONDITIONAL_TICKERS = frozenset(BATCH_50_TICKERS)
OPERATING_TICKERS = frozenset({"CSGP", "CBRE"})


REIT_INPUTS: dict[str, dict[str, Any]] = {
    "AMT": {"accession": "0001053507-26-000131", "document": "pressreleaseq22026.htm", "metric": "2026 AFFO attributable to AMT common stockholders per share", "tokens": ("11.00", "11.17", "467,000"), "flow": (11.00, 11.085, 11.17), "conversion": 1.0, "basis": "Issuer-reported AFFO already deducts capital-improvement and corporate capital expenditures and incorporates unconsolidated/NCI adjustments.", "conversion_source": {"affo_guidance_millions": (5135.0, 5215.0), "capital_improvement_guidance_millions": (170.0, 180.0), "corporate_capital_guidance_millions": 15.0, "diluted_shares_thousands": 467000.0}},
    "SPG": {"accession": "0001104659-26-093361", "document": "tm2620726d2_ex99-1.htm", "metric": "2026 Real Estate FFO per diluted share", "tokens": ("13.20", "13.30", "2,158,431", "2.457"), "flow": (13.20, 13.25, 13.30), "conversion": 2_158.431 / 2_457.0, "basis": "H1 funds available for distribution divided by reported H1 Real Estate FFO; tenant allowances and operational capital are deducted while development remains outside the recurring conversion.", "conversion_source": {"h1_funds_available_for_distribution_millions": 2158.431, "h1_real_estate_ffo_millions": 2457.0}},
    "HST": {"accession": "0001070750-26-000122", "document": "hst-supplementalfinanciali.htm", "metric": "2026 Adjusted FFO per diluted share midpoint", "tokens": ("Adjusted FFO per diluted share", "2.16", "550", "630", "688.6"), "flow": (2.16, 2.16, 2.16), "conversion": (2.16 - 590.0 / 688.6) / 2.16, "basis": "The full $550m-$630m capital forecast is conservatively deducted from Adjusted FFO because lodging renovation and maintenance capital are not separately forecast.", "conversion_source": {"adjusted_ffo_millions": 1489.0, "capital_expenditure_guidance_millions": (550.0, 630.0), "diluted_shares_millions": 688.6}},
    "EXR": {"accession": "0001289490-26-000048", "document": "q22026ex991earningsrelease.htm", "metric": "2026 Core FFO per diluted share", "tokens": ("8.25", "8.40", "1,870"), "flow": (8.25, 8.325, 8.40), "conversion": ((1_389.711 / 1_478.310) + (1.65 / 1.95)) / 2.0, "basis": "Exact issuer recurring-capital guidance is unavailable; the explicit Conditional-Low peer-proxy policy uses the midpoint of cutoff-safe PSA FAD/Core FFO and INVH AFFO/Core FFO conversions, never as a Pass input.", "conversion_source": {"psa_h1_fad_to_core_ffo": 1389.711 / 1478.310, "psa_source_accession": "0001628280-26-050608", "invh_guidance_affo_to_core_ffo": 1.65 / 1.95, "invh_source_accession": "0001687229-26-000041", "fallback": "mean of two cutoff-safe storage/residential REIT cash conversions", "peer_proxy_policy": "BATCH-50-EXR-OWNER-CASH-PROXY-1.0", "conditional_low_only": True, "pass_eligible": False}},
    "DLR": {"accession": "0001104659-26-086270", "document": "dlr-20260723xex99d1.htm", "metric": "2026 Core FFO per share excluding net promote", "tokens": ("8.15", "8.20", "1,563,339", "187,871", "1,483,956", "136,339"), "flow": (8.15, 8.175, 8.20), "conversion": (1_563.339 - 187.871) / 1_483.956, "basis": "H1 AFFO is first reduced by reported net promote income, then divided by H1 Core FFO excluding net promote. Recurring capital remains included while promote and non-recurring development are excluded from the owner-cash anchor.", "conversion_source": {"h1_affo_millions": 1563.339, "h1_net_promote_income_millions": 187.871, "h1_affo_excluding_promote_millions": 1375.468, "h1_core_ffo_excluding_net_promote_millions": 1483.956, "h1_recurring_capital_millions": 136.339, "h1_nonrecurring_capital_millions": 1490.745, "insurance_recovery_in_core_ffo_millions": 27.0, "insurance_recovery_treatment": "retained as disclosed one-time sensitivity; result remains Conditional Low"}},
    "PSA": {"accession": "0001628280-26-050608", "document": "psa-072926xex99_1.htm", "metric": "2026 Core FFO per share", "tokens": ("16.75", "17.05", "1,389,711", "1,478,310"), "flow": (16.75, 16.90, 17.05), "conversion": 1_389.711 / 1_478.310, "basis": "H1 reported Funds Available for Distribution divided by H1 reported Core FFO; maintenance capital is deducted once.", "conversion_source": {"h1_fad_millions": 1389.711, "h1_core_ffo_millions": 1478.310, "h1_maintenance_capital_millions": 88.908}},
    "INVH": {"accession": "0001687229-26-000041", "document": "q22026supplemental.htm", "metric": "2026 AFFO per diluted share", "tokens": ("1.62", "1.68", "82,273"), "flow": (1.62, 1.65, 1.68), "conversion": 1.0, "basis": "Issuer-reported AFFO already deducts recurring repairs, maintenance and turnover capital, including its unconsolidated-JV share.", "conversion_source": {"h1_recurring_capital_millions": 82.273, "h1_affo_millions": 510.757, "h1_affo_per_share": 0.85}},
    "VICI": {"accession": "0001705696-26-000088", "document": "viciq22026earningsrelease.htm", "metric": "2026 AFFO per diluted share", "tokens": ("2.45", "2.47", "1,090.3"), "flow": (2.45, 2.46, 2.47), "conversion": 1.0, "basis": "Issuer-reported parent-common AFFO guidance incorporates partnership-unit NCI and recurring lease/financing adjustments; no second capex deduction is made.", "conversion_source": {"affo_guidance_millions": (2675.0, 2695.0), "weighted_average_shares_millions": 1090.3}},
}

OPERATING_SPECS = {
    "CSGP": {"revenue": "RevenueFromContractWithCustomerExcludingAssessedTax", "ocf": "NetCashProvidedByUsedInOperatingActivities", "capex": "PaymentsToAcquirePropertyPlantAndEquipment", "interest": "InterestPaidNet", "wacc": (0.105, 0.095, 0.085)},
    "CBRE": {"revenue": "RevenueFromContractWithCustomerExcludingAssessedTax", "ocf": "NetCashProvidedByUsedInOperatingActivities", "capex": "PaymentsToAcquireProductiveAssets", "interest": "InterestPaidNet", "wacc": (0.11, 0.10, 0.09)},
}

WARNINGS = {
    "AMT": "Conditional Low tower-REIT AFFO baseline. Tenant churn, foreign exchange and tax, CoreSite/JV ownership, leverage and refinancing remain material.",
    "CSGP": "Conditional Low operating FCFF baseline—not a REIT AFFO model. Homes.com growth investment, acquisitions, capitalized software, SBC/dilution and marketplace cash conversion remain material.",
    "SPG": "Conditional Low retail-REIT owner-cash baseline. Redevelopment, tenant allowances, platform investments, JV/preferred-unit scope, dispositions and leverage remain material.",
    "HST": "Conditional Low lodging-REIT owner-cash baseline. The full capital plan is deducted conservatively; RevPAR, Maui recovery, renovations, dispositions and hotel/JV scope remain material.",
    "CBRE": "Conditional Low real-estate-services operating FCFF baseline—not a REIT AFFO model. Advisory cycles, working capital, acquisitions, development/warehouse funding, leases, NCI and SBC remain material.",
    "EXR": "Conditional Low self-storage REIT baseline. A transparent PSA/INVH recurring-capital conversion is used because issuer AFFO guidance is unavailable; Life Storage integration, acquisitions, occupancy and OP-unit scope remain material.",
    "DLR": "Conditional Low specialist data-center REIT baseline. Reported AFFO conversion excludes promote income but retains an approximately $27m insurance recovery as a disclosed sensitivity; development, power/interconnection commitments, foreign/JV scope, preferred conversion and financing remain material.",
    "PSA": "Conditional Low self-storage REIT FAD baseline. Current acquisitions/financing, occupancy, development, preferred claims and integration remain material.",
    "INVH": "Conditional Low single-family-rental AFFO baseline. Reported recurring capital is deducted, but insurance, turnover, acquisitions/dispositions, securitization, JV/OP-unit scope and leverage remain material.",
    "VICI": "Conditional Low gaming net-lease AFFO baseline. Tenant concentration, master-lease coverage, acquisitions, CECL, partnership units and cutoff financing remain material.",
}

EVENT_TREATMENTS = {
    "AMT": "The July earnings filing defines the cutoff outlook; foreign sales, CoreSite growth and financing are consumed through reported AFFO and no proceeds or opportunity value is added.",
    "CSGP": "The July earnings and leadership filings are operating context. Guidance is not substituted for cash flow and no acquisition, Homes.com or SBC value is added outside reported cash history.",
    "SPG": "The August earnings filing defines the cutoff guidance. Secured debt, euro notes and term-loan activity already reflected at quarter-end are not overlaid again.",
    "HST": "The August earnings/supplement defines the lodging forecast; the Four Seasons sale, special dividend, repurchases and future capital allocation are not added as surplus value.",
    "CBRE": "The July earnings filing is operating context only. Advisory/GWS performance and investment-management assets are not substituted for consolidated owner cash.",
    "EXR": "The July earnings and credit-agreement filings are recorded; future acquisitions and unused credit capacity are excluded from intrinsic value.",
    "DLR": "The July earnings and preferred-security filing are recorded. Promote/insurance items, ATM proceeds, development backlog and financing are not added outside the normalized AFFO anchor.",
    "PSA": "The NSA/PS Canada acquisition and July financing filings remain integration and claim context; consideration, debt proceeds and forecast accretion are not added outside reported Core FFO/FAD.",
    "INVH": "July earnings, note and credit filings define current financing and disposition context; future acquisitions, dispositions and unused capacity are excluded.",
    "VICI": "The July earnings plus August credit/note filings define the cutoff state; investment consideration and financing proceeds are not added separately to AFFO value.",
}


def _events(ticker: str, root: Path, manifest_sha: str) -> dict[str, Any]:
    inventory = root / ticker / "inventory.json"
    rows = json.loads(inventory.read_text())
    if not rows or any(row.get("filed", "") > BATCH_50_VALUATION_DATE for row in rows):
        raise ValueError(f"{ticker}: invalid event inventory")
    documents = []
    for row in rows:
        for document in row.get("documents", []):
            path = Path(document["path"])
            if not path.is_absolute():
                path = root.parent.parent / path
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != document.get("sha256"):
                raise ValueError(f"{ticker}: event hash mismatch")
            documents.append({**document, "accession": row["accession"], "filed": row["filed"], "form": row["form"]})
    return {"source_kind": "sec_event_screening", "screened_filings": rows, "documents": documents, "inventory_sha256": hashlib.sha256(inventory.read_bytes()).hexdigest(), "source_manifest_sha256": manifest_sha, "treatment": EVENT_TREATMENTS[ticker], "reported_vs_estimated": "reported_and_screened"}


def _specialist_source(ticker: str, event: dict[str, Any], event_root: Path) -> dict[str, Any]:
    spec = REIT_INPUTS[ticker]
    matches = [row for row in event["documents"] if row["accession"] == spec["accession"] and Path(row["path"]).name == spec["document"]]
    if len(matches) != 1:
        raise ValueError(f"{ticker}: specialist exhibit unresolved")
    row = matches[0]
    path = Path(row["path"])
    if not path.is_absolute():
        path = event_root.parent.parent / path
    text = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", path.read_text(errors="ignore")))).casefold()
    if any(token.casefold() not in text for token in spec["tokens"]):
        raise ValueError(f"{ticker}: specialist metric row/period values not found in filed exhibit")
    return {"source_kind": "sec_filed_earnings_exhibit", "accession": spec["accession"], "filed": row["filed"], "period_end": PERIOD, "document": spec["document"], "sha256": row["sha256"], "metric": spec["metric"], "reported_low_base_high_per_share": spec["flow"], "unit": "USD/share", "reported_vs_estimated": "issuer_reported_guidance_or_midpoint"}


def _reit_numeric(ticker: str, *, filing, verification, event, specialist, structural):
    spec = REIT_INPUTS[ticker]
    owner_cash = spec["flow"][1] * spec["conversion"]
    discounts = (0.0975, 0.0925, 0.0875)
    rows = []
    for name, discount in zip(("bear", "base", "bull"), discounts):
        value = two_stage_cash_flow_value(cash_flow_per_share=owner_cash, growth_rate=0.02, growth_years=8, terminal_growth=0.02, discount_rate=discount)
        rows.append({"name": name, "reported_ffo_or_affo_per_share": spec["flow"][1], "locked_cash_conversion": spec["conversion"], "normalized_affo_per_share": owner_cash, "growth_rate": 0.02, "forecast_years": 8, "terminal_growth": 0.02, "discount_rate": discount, "raw_value_per_share": value, "conditional_value_per_share": value})
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("REPORTED_AFFO_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if reported FFO/AFFO, recurring capital, property/tenant/JV scope, preferred/NCI, dilution, financing or cutoff events leave the recorded bounds."
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 1, "forecast_years": 8, "normalization_basis": "cutoff-safe issuer guidance with a reported or explicitly peer/governed owner-cash conversion", "assumption_source_mix": "SEC-filed specialist guidance and transparent source-linked recurring-capital conversion", "reported_flow_per_share": spec["flow"], "cash_conversion": (spec["conversion"],) * 3, "normalized_affo_per_share": (owner_cash,) * 3, "growth_rate": (0.02,) * 3, "discount_rate": discounts, "terminal_growth": (0.02,) * 3, "equity_floor_basis": "not applied", "scenario_calibration": "one-driver public range: normalized owner cash is fixed while cost of equity varies", "calculator_calibration": "Exact locked AFFO DCF base replay.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker=ticker, method="reit_affo_per_share_dcf", method_version=BATCH_50_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(WARNINGS[ticker], invalidation))
    return {"ticker": ticker, "method": "reit_affo_per_share_dcf", "model_version": BATCH_50_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"reported_flow_per_share": spec["flow"], "flow_metric": spec["metric"], "input_kind": "issuer_reported_guidance_or_midpoint"}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "specialist_metric_source": specialist, "owner_cash_conversion": {"ratio": spec["conversion"], "basis": spec["basis"], "direct_source": {**spec["conversion_source"], "accession": spec["accession"], "document": spec["document"], "reported_vs_estimated": "reported_or_explicit_peer_bounded_components"}, "missing_values_zero_imputed": False}, "event_sources": event, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def _fact_rows(facts: dict[str, Any], concept: str) -> list[dict[str, Any]]:
    return [row for row in facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", []) if isinstance(row.get("val"), (int, float)) and not isinstance(row.get("val"), bool) and row.get("filed", "") <= BATCH_50_VALUATION_DATE]


def _fact(facts: dict[str, Any], concept: str, start: str, end: str, form: str, accession: str | None = None) -> dict[str, Any]:
    rows = [row for row in _fact_rows(facts, concept) if row.get("start") == start and row.get("end") == end and row.get("form") == form and (accession is None or row.get("accn") == accession)]
    if not rows:
        raise ValueError(f"{concept}/{start}/{end}: fact absent")
    row = max(rows, key=lambda item: (item.get("filed", ""), item.get("accn", "")))
    return {"source_kind": "companyfacts", "concept": f"us-gaap:{concept}", "value": float(row["val"]), "unit": "USD", "period_start": start, "period_end": end, "filed": row.get("filed"), "accession": row.get("accn"), "form": row.get("form"), "reported_vs_estimated": "reported"}


def _operating_history(ticker: str, facts: dict[str, Any], accession: str) -> tuple[list[dict[str, Any]], dict[str, Any], float, float]:
    spec = OPERATING_SPECS[ticker]
    annual = []
    for year in range(2021, 2026):
        start, end = f"{year}-01-01", f"{year}-12-31"
        fields = {name: _fact(facts, concept, start, end, "10-K") for name, concept in spec.items() if name in {"revenue", "ocf", "capex", "interest"}}
        pretax = _fact(facts, "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", start, end, "10-K")
        tax = _fact(facts, "IncomeTaxExpenseBenefit", start, end, "10-K")
        rate = max(0.0, min(0.30, tax["value"] / pretax["value"])) if pretax["value"] > 0 else 0.21
        fcff = fields["ocf"]["value"] - fields["capex"]["value"] + fields["interest"]["value"] * (1.0 - rate)
        annual.append({"period_end": end, **fields, "pretax_income": pretax, "income_tax": tax, "tax_rate": rate, "cash_fcff": fcff, "cash_fcff_margin": fcff / fields["revenue"]["value"], "formula": "OCF - capex + after-tax cash interest"})
    current = {}
    for name, concept in ((name, spec[name]) for name in ("revenue", "ocf", "capex", "interest")):
        current_h1 = _fact(facts, concept, "2026-01-01", PERIOD, "10-Q", accession)
        prior_h1 = _fact(facts, concept, "2025-01-01", "2025-06-30", "10-Q", accession)
        current[name] = {"value": annual[-1][name]["value"] + current_h1["value"] - prior_h1["value"], "method": "latest_fy_plus_current_h1_minus_prior_h1", "period_end": PERIOD, "sources": [annual[-1][name], current_h1, prior_h1]}
    tax_rate = median(row["tax_rate"] for row in annual)
    current["tax_rate"] = tax_rate
    current["cash_fcff"] = current["ocf"]["value"] - current["capex"]["value"] + current["interest"]["value"] * (1.0 - tax_rate)
    current["cash_fcff_margin"] = current["cash_fcff"] / current["revenue"]["value"]
    normalized_margin = median([row["cash_fcff_margin"] for row in annual] + [current["cash_fcff_margin"]])
    observed_revenue_cagr = (current["revenue"]["value"] / annual[0]["revenue"]["value"]) ** (1.0 / 5.0) - 1.0
    normalized_growth = min(0.08, max(0.02, observed_revenue_cagr * 0.5))
    current["observed_revenue_cagr"] = observed_revenue_cagr
    return annual, current, normalized_margin, normalized_growth


def _bridge(ticker: str, structural: dict[str, Any]) -> dict[str, Any]:
    def point(*names: str) -> dict[str, Any]:
        return _instant(structural, names, PERIOD)
    shares = _latest_shares(ticker, structural)
    if ticker == "CSGP":
        cash = point("CashAndCashEquivalentsAtCarryingValue")
        debt_parts = [point("LongTermDebt"), point("FinanceLeaseLiability")]
        claim_parts = [point("MinorityInterest")]
        excluded = {"restricted_cash": 0.0, "operating_leases": point("OperatingLeaseLiability")["value"]}
    elif ticker == "CBRE":
        cash = point("CashAndCashEquivalentsAtCarryingValue")
        debt_parts = [point("LongTermDebtCurrent"), point("LongTermDebtNoncurrent"), point("ShortTermBorrowings"), point("FinanceLeaseLiabilityCurrent"), point("FinanceLeaseLiabilityNoncurrent")]
        claim_parts = [point("MinorityInterest"), point("RedeemableNoncontrollingInterestEquityCarryingAmount")]
        excluded = {"restricted_cash": point("RestrictedCashAndCashEquivalentsAtCarryingValue")["value"], "equity_method_investments": point("EquityMethodInvestments")["value"], "operating_lease_liability": point("OperatingAndFinancingLeaseLiability")["value"] - point("FinanceLeaseLiabilityCurrent")["value"] - point("FinanceLeaseLiabilityNoncurrent")["value"], "warehouse_borrowing_in_short_term_debt": point("WarehouseAgreementBorrowings")["value"]}
    else:
        raise ValueError(ticker)
    return {"cash": cash["value"], "debt": sum(row["value"] for row in debt_parts), "claims": sum(row["value"] for row in claim_parts), "shares": shares["value"], "source_rows": {"cash": cash, "debt_parts": debt_parts, "claim_parts": claim_parts, "latest_shares": shares}, "preferred_claim_status": {"reported_preferred_equity": None, "modeled_preferred_equity": 0.0, "basis": "No issued/outstanding or economic preferred claim is presented in the controlling statement; authorized shares alone are not a claim."}, "excluded_or_separately_treated": excluded, "missing_values_zero_imputed": False}


def _operating_numeric(ticker: str, *, filing, verification, event, structural, facts):
    annual, ttm, normalized_margin, normalized_growth = _operating_history(ticker, facts, filing["accession"])
    bridge = _bridge(ticker, structural)
    rows = []
    for name, wacc in zip(("bear", "base", "bull"), OPERATING_SPECS[ticker]["wacc"]):
        state = EnterpriseCashFlowState(cash_fcff=ttm["revenue"]["value"] * normalized_margin, initial_growth=normalized_growth, terminal_growth=0.02, wacc=wacc, cash_and_investments=bridge["cash"], interest_bearing_debt=bridge["debt"], preferred_equity=0.0, noncontrolling_interests=bridge["claims"], diluted_shares=bridge["shares"])
        value = enterprise_cash_flow_dcf(state, forecast_years=8)
        rows.append({"name": name, "starting_cash_fcff": state.cash_fcff, "locked_normalized_cash_margin": normalized_margin, "growth_rate": state.initial_growth, "forecast_years": 8, "terminal_growth": state.terminal_growth, "wacc": state.wacc, "cash": state.cash_and_investments, "debt": state.interest_bearing_debt, "preferred_and_nci": state.preferred_equity + state.noncontrolling_interests, "shares": state.diluted_shares, "raw_value_per_share": value["intrinsic_value_per_share"], "conditional_value_per_share": value["intrinsic_value_per_share"], "trace": value})
    scenario = dict(zip(("low", "base", "high"), (row["conditional_value_per_share"] for row in rows)))
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: invalid operating range")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"))
    invalidation = "Revalue if operating perimeter, cash conversion, capex/software investment, acquisition funding, debt/lease/NCI claims, dilution or cutoff events leave the recorded bounds."
    assumptions = {"history_policy_version": "US-COMPANY-HISTORY-1.0", "history_years_used": 6, "forecast_years": 8, "normalization_basis": "median of five exact annual plus current TTM cash-FCFF margins; negative investment-cycle years are retained", "assumption_source_mix": "reported five-year and TTM cash history plus a complete current enterprise bridge", "cash_conversion_margin": (normalized_margin,) * 3, "starting_cash_fcff": (rows[1]["starting_cash_fcff"],) * 3, "observed_revenue_cagr": ttm["observed_revenue_cagr"], "growth_rate": (normalized_growth,) * 3, "growth_policy": "half of the observed five-year revenue CAGR, bounded to 2%-8%", "wacc": OPERATING_SPECS[ticker]["wacc"], "terminal_growth": (0.02,) * 3, "equity_floor_basis": "not applied", "scenario_calibration": "one-driver public range: normalized cash FCFF, growth and bridge are fixed while WACC varies", "calculator_calibration": "Exact enterprise cash-FCFF base replay.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker=ticker, method="operating_enterprise_fcff", method_version=BATCH_50_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence="Low", availability_type=AvailabilityType.CONDITIONAL, warnings=(WARNINGS[ticker], invalidation))
    return {"ticker": ticker, "method": "operating_enterprise_fcff", "model_version": BATCH_50_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": ttm["revenue"]["value"], "ttm_cash_fcff": ttm["cash_fcff"], "normalized_cash_fcff_margin": normalized_margin, "share_count": bridge["shares"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "annual_cash_sources": annual, "ttm_cash_sources": ttm, "bridge_context": bridge, "event_sources": event, "model_trace": {"states": rows}, "runtime_source_verification": verification, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": WARNINGS[ticker], "baseline": baseline.as_private_dict()}


def build_batch_50_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path, structural_cache_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_50_TICKERS:
        raise ValueError(ticker)
    packet, structural_packet = Path(source_root) / ticker, Path(structural_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural.get("source_accession") != filing["accession"] or structural.get("report_date") != PERIOD:
        raise ValueError(f"{ticker}: controlling mismatch")
    verification = verify_source_bundle(ticker=ticker, packet=packet, structural_packet=structural_packet, structural_cache_root=Path(structural_cache_root), filing=filing)
    event = _events(ticker, Path(event_root), verification["source_manifest_sha256"])
    if ticker in OPERATING_TICKERS:
        return _operating_numeric(ticker, filing=filing, verification=verification, event=event, structural=structural, facts=facts)
    specialist = _specialist_source(ticker, event, Path(event_root))
    return _reit_numeric(ticker, filing=filing, verification=verification, event=event, specialist=specialist, structural=structural)


if PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_50_TICKERS):
    raise RuntimeError("Batch 50 classification mismatch")
