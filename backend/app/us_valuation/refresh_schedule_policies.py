"""Source-bound refresh adapter for the migrated cash-schedule family.

The migrated AAPL recipe contains calculated cash flows, rather than selectors
for the next filing.  This module is the successor adapter: it re-selects the
current filing from a cached SEC packet, rebuilds source-dependent normalized
inputs, and regenerates the five-year FCFF schedule and terminal cash flow.

Only this module owns the AAPL cash-schedule policy for now.  It deliberately
does not mutate a recipe in place, publish a catalog, or use old cash flows as
new inputs.  The policy contains assumptions and selectors only; accession
numbers, dates, balances, and flow amounts enter through the source packet.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
from statistics import median
from typing import Any, Mapping

from .calculation_recipe import evaluate_recipe, number
from .models import fcff_dcf
from .xbrl import CompanyFactsNormalizer, load_concept_config


SCHEMA = "FINSIGHT-CASH-SCHEDULE-REFRESH-POLICY-1"
POLICY_VERSION = f"{SCHEMA}-AAPL"
SUPPORTED_TICKER = "AAPL"
SUPPORTED_ENGINE = "cash_schedule"
ROUTINE_EVENT_ITEMS = frozenset({"2.02", "9.01"})
SUPPORTED_TICKERS = frozenset({"AAPL", "MSFT"})


class CashScheduleRefreshError(ValueError):
    """The source packet cannot support a safe cash-schedule refresh."""


def _finite(value: Any, field: str) -> float:
    result = number(value, field)
    if not isfinite(result):
        raise CashScheduleRefreshError(f"{field} must be finite")
    return result


def _iso(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise CashScheduleRefreshError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise CashScheduleRefreshError(f"{field} must be an ISO date") from exc


def _records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    if not isinstance(accessions, list):
        raise CashScheduleRefreshError("SEC submissions recent accession list is missing")
    return [
        {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(len(accessions))
    ]


def _select_filing(records: list[dict[str, Any]], cutoff: str) -> dict[str, Any]:
    eligible = [
        row
        for row in records
        if row.get("form") in {"10-K", "10-Q"}
        and isinstance(row.get("accessionNumber"), str)
        and isinstance(row.get("reportDate"), str)
        and isinstance(row.get("filingDate"), str)
        and row["filingDate"] <= cutoff
        and row["reportDate"] <= cutoff
    ]
    if not eligible:
        raise CashScheduleRefreshError("no cutoff-eligible regular filing")
    return max(eligible, key=lambda row: (row["reportDate"], row["filingDate"], row["accessionNumber"]))


def _validate_identity(policy: Mapping[str, Any], packet: Mapping[str, Any], *, ticker: str) -> str:
    cik = str(policy.get("cik", ""))
    if not cik.isdigit() or len(cik) > 10:
        raise CashScheduleRefreshError("policy CIK is invalid")
    digits = cik.zfill(10)
    submissions = packet.get("submissions")
    companyfacts = packet.get("companyfacts")
    if not isinstance(submissions, Mapping) or not isinstance(companyfacts, Mapping):
        raise CashScheduleRefreshError("SEC source packet is incomplete")
    if str(submissions.get("cik", "")).zfill(10) != digits or str(companyfacts.get("cik", "")).zfill(10) != digits:
        raise CashScheduleRefreshError("SEC source packet CIK identity conflict")
    if policy.get("ticker") != ticker or ticker not in SUPPORTED_TICKERS:
        raise CashScheduleRefreshError("cash-schedule adapter does not support this ticker")
    return digits


def compile_cash_schedule_policy(recipe: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    """Compile an executable AAPL policy without freezing source facts.

    The growth, margin, tax, and reinvestment rules are the approved Batch 01
    assumptions.  No accession, period, source amount, or baseline cash-flow
    value is copied into this policy.
    """
    scenarios = recipe.get("scenarios", {})
    ticker = recipe.get("ticker")
    if ticker not in SUPPORTED_TICKERS or set(scenarios) != {"bear", "base", "bull"}:
        raise ValueError("cash-schedule compiler supports only the explicitly mapped AAPL/MSFT families")
    if {spec.get("engine") for spec in scenarios.values()} != {SUPPORTED_ENGINE}:
        raise ValueError("recipe is not an all-cash-schedule family recipe")
    for name, spec in scenarios.items():
        inputs = spec.get("inputs", {})
        if not isinstance(inputs, Mapping) or not isinstance(inputs.get("discount_rate"), (int, float)):
            raise ValueError(f"{name}: discount rate is missing")
        if inputs.get("terminal_growth") is None:
            raise ValueError(f"{name}: terminal growth is missing")
    if ticker == "MSFT":
        from .refresh_msft_model import compile_msft_approved_policy
        # The successor cannot safely rebuild this family from Companyfacts
        # alone.  The approved model is segment operating-income based and
        # requires current inline-XBRL segment tables plus intangible/R&D
        # treatment.  Keep this metadata declarative; no stale segment amounts
        # or accession-bound table values are embedded here.
        return {
            "schema_version": SCHEMA,
            "version": f"{SCHEMA}-MSFT-2",
            "ticker": ticker,
            "cik": str(registry_entry.get("cik", "")).zfill(10),
            "supported_engine": SUPPORTED_ENGINE,
            "model_profile": "segment_operating_income_intangible_investment",
            "policy_status": "source_validation_pending",
            "approved_forecast_policy": compile_msft_approved_policy(recipe),
            "concept_config": load_concept_config(),
            "statement_required_fields": {'revenue':'flow','total_assets':'instant'},
            "source_requirements": {
                "companyfacts": True,
                "regular_filing": True,
                "structural_bridge": True,
                "structural": True,
                "segment_filing_table": True,
                "r_and_d_history": True,
                "event_exhibits": True,
            },
            "routine_8k_items": sorted(ROUTINE_EVENT_ITEMS),
            "normalization_version": "US-MSFT-SEGMENT-OPERATING-INCOME-SOURCE-NORMALIZATION-2",
            "policy_assumptions": {
                "forecast_years": 8,
                "forecast_policy_version": "MSFT-ENTERPRISE-CLOUD-1.0",
                "segment_mode": "segment_operating_income",
                "reinvestment_treatment": "governed intangible-investment/R&D policy required; total reported capex remains source input",
            },
            "scenario_assumptions": {
                "bear": {"growth_delta": -0.02, "margin_delta": -0.02},
                "base": {"growth_delta": 0.0, "margin_delta": 0.0},
                "bull": {"growth_delta": 0.015, "margin_delta": 0.02},
            },
            "unsupported_cases": [
                "missing current inline-XBRL segment operating-income table package",
                "unresolved R&D/intangible-investment treatment",
                "unresolved preferred, NCI, finance-lease, or other equity claims",
                "non-routine 8-K items between recipe cutoff and refresh cutoff",
            ],
        }
    return {
        "schema_version": SCHEMA,
        "version": POLICY_VERSION,
        "ticker": ticker,
        "cik": str(registry_entry.get("cik", "")).zfill(10),
        "supported_engine": SUPPORTED_ENGINE,
        "concept_config": load_concept_config(),
        "statement_required_fields": {'revenue':'flow','operating_income':'flow','cash':'instant'},
        "source_requirements": {
            "companyfacts": True,
            "structural": True,
            "regular_filing": True,
            "structural_bridge": True,
            "event_exhibits": True,
        },
        "routine_8k_items": sorted(ROUTINE_EVENT_ITEMS),
        "normalization_version": "US-CASH-SCHEDULE-SOURCE-NORMALIZATION-1",
        "policy_assumptions": {
            "forecast_years": 5,
            "growth_weights": {
                "ttm_history": 0.375,
                "annual_history": 0.375,
                "archetype_anchor": 0.25,
            },
            "archetype_median_growth": 0.05,
            "company_margin_weight": 0.70,
            "archetype_target_operating_margin": 0.25,
            "sales_to_capital_anchor": 2.5,
            "growth_persistence": 0.70,
            "margin_persistence": 0.70,
            "tax_rate_cap": 0.30,
            "reinvestment_formula": "positive revenue growth / marginal ROIC",
            "terminal_roic_formula": "scenario discount rate",
            "capex_treatment": "total reported capex; no maintenance/growth split inferred",
        },
        "scenario_assumptions": {
            "bear": {"growth_delta": -0.02, "margin_delta": -0.02, "capital_efficiency_multiplier": 0.75, "wacc_delta": 0.01, "terminal_growth_delta": -0.005},
            "base": {"growth_delta": 0.0, "margin_delta": 0.0, "capital_efficiency_multiplier": 1.0, "wacc_delta": 0.0, "terminal_growth_delta": 0.0},
            "bull": {"growth_delta": 0.015, "margin_delta": 0.02, "capital_efficiency_multiplier": 1.0, "wacc_delta": -0.005, "terminal_growth_delta": 0.003},
        },
        "bridge_policy": {
            "cash": "reported cash + current marketable securities + noncurrent marketable securities",
            "debt": "reported current debt + noncurrent debt + commercial paper; finance leases require current evidence",
            "preferred_equity": "explicit structural absence proof or reported claim",
            "noncontrolling_interests": "explicit structural absence proof or reported claim",
            "shares": "latest filed common-share count plus current cumulative incremental dilutive shares",
        },
        "unsupported_cases": [
            "non-routine 8-K items between recipe cutoff and refresh cutoff",
            "unresolved preferred, NCI, or finance-lease claims",
            "non-calendar or 52/53-week fiscal calendars without an approved mapping",
            "recipes with an engine other than cash_schedule or ticker other than AAPL",
        ],
    }


def _selected_rows(normalizer: CompanyFactsNormalizer, field: str, *, end: str | None = None) -> list[dict[str, Any]]:
    """Return source rows through the normalizer's configured concept aliases."""
    candidates = normalizer._candidates(field)  # existing selector source, kept private by xbrl module
    rows = []
    for namespace, concept, unit, fact in candidates:
        if end is not None and fact.get("end") != end:
            continue
        if not isinstance(fact.get("val"), (int, float)) or isinstance(fact.get("val"), bool):
            continue
        row = {
            "field": field,
            "namespace": namespace,
            "concept": concept,
            "unit": unit,
            "value": float(fact["val"]),
            "start": fact.get("start"),
            "end": fact.get("end"),
            "accession": fact.get("accn"),
            "form": fact.get("form"),
            "filed": fact.get("filed"),
            "fiscal_year": fact.get("fy"),
            "fiscal_period": fact.get("fp"),
        }
        rows.append(row)
    return rows


def _instant(normalizer: CompanyFactsNormalizer, field: str, period: str) -> dict[str, Any]:
    selected = normalizer.instant(field, end=period)
    if selected is None:
        raise CashScheduleRefreshError(f"{field}: current filing fact is missing")
    return selected.as_dict()


def _share_rows(normalizer: CompanyFactsNormalizer, controlling_accession: str, period: str) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = _selected_rows(normalizer, "common_shares_outstanding")
    rows = [row for row in rows if row.get("accession") == controlling_accession and row.get("filed")]
    if not rows:
        raise CashScheduleRefreshError("common shares: controlling filing fact is missing")
    cover = max(rows, key=lambda row: (row.get("end", ""), row.get("filed", "")))
    # Quarterly filings use the current cumulative YTD fact.  A current 10-K
    # may have no YTD pair, so accept its exact annual fact only when accession
    # and period both match the selected controlling filing.
    annual = normalizer.annual_series("incremental_dilutive_shares", 1)
    pair = normalizer.latest_ytd_pair(
        "incremental_dilutive_shares",
        after_end=annual[-1].end if annual else None,
    ) if annual else None
    incremental_fact = pair[0] if pair and pair[0].end == period else None
    if incremental_fact is None and annual:
        candidate = annual[-1]
        if candidate.end == period and candidate.accession == controlling_accession:
            incremental_fact = candidate
    if incremental_fact is None:
        raise CashScheduleRefreshError(
            "incremental dilutive shares require current cumulative YTD or matching annual fact"
        )
    incremental = incremental_fact.as_dict()
    return cover, incremental


def _annual_tax(normalizer: CompanyFactsNormalizer, cap: float) -> tuple[float, list[dict[str, Any]]]:
    rows = []
    rates = []
    for pretax in normalizer.annual_series("pretax_income", 5):
        tax = normalizer.annual_at_end("income_tax", pretax.end)
        if tax is None or pretax.value <= 0:
            continue
        rate = min(cap, max(0.0, float(tax.value) / float(pretax.value)))
        rates.append(rate)
        rows.append({"period_end": pretax.end, "pretax_income": pretax.as_dict(), "income_tax": tax.as_dict(), "effective_tax_rate": rate})
    if len(rates) < 3:
        raise CashScheduleRefreshError("fewer than three annual effective-tax observations")
    return float(median(rates)), rows


def _annual_margin_growth(normalizer: CompanyFactsNormalizer, assumptions: Mapping[str, Any]) -> dict[str, Any]:
    annual_revenue = normalizer.annual_series("revenue", 5)
    annual_operating = normalizer.annual_series("operating_income", 5)
    by_end = {row.end: row for row in annual_revenue}
    margins = [row.value / by_end[row.end].value for row in annual_operating if row.end in by_end and by_end[row.end].value > 0]
    if len(margins) < 3:
        raise CashScheduleRefreshError("fewer than three annual operating-margin observations")
    ttm_revenue = normalizer.ttm_flow("revenue")
    ttm_operating = normalizer.ttm_flow("operating_income")
    ttm_margin = float(ttm_operating["value"]) / float(ttm_revenue["value"])
    annual_capex = normalizer.annual_series("capital_expenditures", 5)
    capex_by_end = {row.end: row for row in annual_capex}
    capex_ratios = [capex_by_end[end].value / by_end[end].value for end in capex_by_end if end in by_end and by_end[end].value > 0]
    ttm_capex = normalizer.ttm_flow("capital_expenditures")
    if len(capex_ratios) < 3 or float(ttm_revenue["value"]) <= 0:
        raise CashScheduleRefreshError("insufficient total-capex history for reinvestment normalization")
    current_capex_ratio = float(ttm_capex["value"]) / float(ttm_revenue["value"])
    historical_capex_ratio = float(median(capex_ratios[-5:]))
    base_capital_multiplier = min(1.25, max(0.50, historical_capex_ratio / current_capex_ratio))
    normalized_margin = float(median([ttm_margin, *margins]))
    target_margin = assumptions["company_margin_weight"] * normalized_margin + (1.0 - assumptions["company_margin_weight"]) * assumptions["archetype_target_operating_margin"]
    history = normalizer.ttm_history("revenue", 4)
    ttm_yoy = None
    if len(history) >= 2:
        latest_end = date.fromisoformat(history[-1]["period_end"])
        comparable = [
            row for row in history[:-1]
            if 350 <= abs((latest_end - date.fromisoformat(row["period_end"])).days) <= 380
        ]
        if not comparable:
            raise CashScheduleRefreshError(
                "TTM growth requires a comparable annual-period TTM observation"
            )
        prior = max(comparable, key=lambda row: row["period_end"])
        ttm_yoy = history[-1]["value"] / prior["value"] - 1.0
    if ttm_yoy is None:
        raise CashScheduleRefreshError(
            "TTM growth requires at least two aligned TTM observations"
        )
    latest_three = annual_revenue[-3:]
    annual_cagr = (latest_three[-1].value / latest_three[0].value) ** (1.0 / (len(latest_three) - 1)) - 1.0
    weights = assumptions["growth_weights"]
    initial_growth = weights["ttm_history"] * ttm_yoy + weights["annual_history"] * annual_cagr + weights["archetype_anchor"] * assumptions["archetype_median_growth"]
    return {
        "starting_revenue": float(ttm_revenue["value"]),
        "starting_revenue_source": ttm_revenue,
        "starting_operating_margin": ttm_margin,
        "starting_operating_margin_source": ttm_operating,
        "normalized_operating_margin": normalized_margin,
        "target_operating_margin": target_margin,
        "initial_revenue_growth": max(-0.10, min(0.20, initial_growth)),
        "base_capital_multiplier": base_capital_multiplier,
        "current_capex_ratio": current_capex_ratio,
        "historical_capex_ratio": historical_capex_ratio,
        "growth_evidence": {"ttm_yoy_growth": ttm_yoy, "annual_cagr": annual_cagr, "annual_revenue": [row.as_dict() for row in annual_revenue], "annual_operating_income": [row.as_dict() for row in annual_operating], "annual_capex": [row.as_dict() for row in annual_capex], "ttm_capex": ttm_capex},
    }


def _schedule(
    *,
    normalized: Mapping[str, Any],
    tax_rate: float,
    scenario: Mapping[str, Any],
    base_inputs: Mapping[str, Any],
    policy_assumptions: Mapping[str, Any],
    bridge: Mapping[str, float],
) -> dict[str, Any]:
    """Rebuild the schedule through the existing pure FCFF evaluator.

    Scenario discount rates and terminal growth are already approved inputs in
    each recipe case.  The policy's operating deltas affect only growth,
    margin, and capex-derived sales-to-capital; applying rate deltas here would
    double-shock the migrated recipe.
    """
    target_margin = normalized["target_operating_margin"] + scenario["margin_delta"]
    sales_to_capital = (
        float(policy_assumptions["sales_to_capital_anchor"])
        * float(normalized["base_capital_multiplier"])
        * float(scenario["capital_efficiency_multiplier"])
    )
    wacc = float(base_inputs["discount_rate"])
    terminal_growth = float(base_inputs["terminal_growth"])
    assumptions = {
        "starting_revenue": float(normalized["starting_revenue"]),
        "starting_operating_margin": float(normalized["starting_operating_margin"]),
        "initial_revenue_growth": float(normalized["initial_revenue_growth"]) + float(scenario["growth_delta"]),
        "target_operating_margin": target_margin,
        "normalized_operating_margin": float(normalized["normalized_operating_margin"]),
        "normalized_tax_rate": float(tax_rate),
        "sales_to_capital": sales_to_capital,
        "initial_marginal_roic": target_margin * (1.0 - float(tax_rate)) * sales_to_capital,
        "terminal_marginal_roic": wacc,
        "terminal_growth": terminal_growth,
        "forecast_years": int(policy_assumptions["forecast_years"]),
        "growth_persistence": float(policy_assumptions["growth_persistence"]),
        "margin_persistence": float(policy_assumptions["margin_persistence"]),
        "segment_forecast": None,
    }
    financials = {
        "balance_sheet": {
            "cash_and_nonoperating_investments": float(bridge["cash_and_investments"]),
            "total_interest_bearing_debt": float(bridge["debt"]),
            "preferred_equity": float(bridge["preferred_equity"]),
            "noncontrolling_interests": float(bridge["noncontrolling_interests"]),
            "fully_diluted_shares_proxy": float(bridge["shares"]),
        }
    }
    model = fcff_dcf(
        assumptions=assumptions,
        discount_rate={"wacc": wacc},
        financials=financials,
    )
    if model.get("errors"):
        raise CashScheduleRefreshError(
            "existing FCFF evaluator rejected refreshed assumptions: "
            + "; ".join(str(error) for error in model["errors"])
        )
    detail = model.get("detail")
    if not isinstance(detail, Mapping) or not isinstance(detail.get("forecast_schedule"), list):
        raise CashScheduleRefreshError("existing FCFF evaluator returned no forecast schedule")
    rows = [dict(row) for row in detail["forecast_schedule"]]
    return {
        "cash_flows": [float(row["fcff"]) for row in rows],
        "terminal_cash_flow": float(detail["terminal_fcff"]),
        "rows": rows,
        "assumptions": {
            **assumptions,
            "wacc": wacc,
            "terminal_growth": terminal_growth,
            "terminal_reinvestment_rate": detail["terminal_reinvestment_rate"],
        },
        "model_trace": model,
    }


def _msft_segment_source_gate(
    *,
    policy: Mapping[str, Any],
    packet: Mapping[str, Any],
    structural_packet: Mapping[str, Any] | None,
    controlling: Mapping[str, Any],
    cutoff: str,
) -> dict[str, Any]:
    """Extract MSFT's current segment table and return source-gate evidence.

    The captured filing is a FY 10-K, so the current and comparative segment
    columns are annual periods.  Segment members are selected by their full
    QName/dimension member, never by a copied amount or a stale period.
    """
    if not isinstance(structural_packet, Mapping):
        raise CashScheduleRefreshError("MSFT refresh blocked: current segment-table structural package is unavailable")
    accession = str(controlling.get("accessionNumber") or controlling.get("accession") or "")
    period_end = str(controlling.get("reportDate") or controlling.get("period_end") or "")
    if structural_packet.get("source_accession") != accession:
        raise CashScheduleRefreshError("MSFT structural package does not match controlling filing")
    facts = structural_packet.get("facts")
    if not isinstance(facts, list):
        raise CashScheduleRefreshError("MSFT structural package has no fact rows")
    cik = str(policy.get("cik", "")).zfill(10)
    relevant = [row for row in facts if isinstance(row, Mapping) and row.get("source_accession") == accession]
    if not relevant or any(
        str(row.get("entity_identifier", "")).zfill(10) != cik
        or row.get("entity_scheme") != "http://www.sec.gov/CIK"
        for row in relevant
    ):
        raise CashScheduleRefreshError("MSFT structural package issuer identity is incomplete or conflicting")
    segment_members = {
        "productivity_and_business_processes": "ProductivityAndBusinessProcessesMember",
        "intelligent_cloud": "IntelligentCloudMember",
        "more_personal_computing": "MorePersonalComputingMember",
    }
    annual_ends = sorted({
        str(row.get("period_end"))
        for row in relevant
        if row.get("local_name") in {"RevenueFromContractWithCustomerExcludingAssessedTax", "OperatingIncomeLoss"}
        and row.get("period_start")
        and row.get("unit") == "USD"
        and isinstance(row.get("value"), (int, float))
        and 330 <= (date.fromisoformat(str(row["period_end"])) - date.fromisoformat(str(row["period_start"]))).days + 1 <= 385
    })
    if len(annual_ends) < 3 or period_end not in annual_ends:
        raise CashScheduleRefreshError("MSFT segment evidence has fewer than three aligned annual periods")
    annual_ends = annual_ends[-3:]
    segments: dict[str, Any] = {}
    segment_sources: list[dict[str, Any]] = []
    for key, member in segment_members.items():
        revenues: list[float] = []
        operating: list[float] = []
        for end in annual_ends:
            rev_rows = [
                row for row in relevant
                if row.get("local_name") == "RevenueFromContractWithCustomerExcludingAssessedTax"
                and row.get("period_end") == end and row.get("unit") == "USD"
                and any(str(member) == str(pair[1]).split(":")[-1] for pair in (row.get("dimensions") or []))
            ]
            op_rows = [
                row for row in relevant
                if row.get("local_name") == "OperatingIncomeLoss"
                and row.get("period_end") == end and row.get("unit") == "USD"
                and any(str(member) == str(pair[1]).split(":")[-1] for pair in (row.get("dimensions") or []))
            ]
            if len(rev_rows) != 1 or len(op_rows) != 1:
                raise CashScheduleRefreshError(f"MSFT segment evidence is missing or ambiguous for {key} {end}")
            revenues.append(float(rev_rows[0]["value"]))
            operating.append(float(op_rows[0]["value"]))
            segment_sources.extend([
                {"concept": rev_rows[0].get("qname"), "value": rev_rows[0]["value"], "period_start": rev_rows[0].get("period_start"), "period_end": end, "accession": accession, "dimensions": rev_rows[0].get("dimensions")},
                {"concept": op_rows[0].get("qname"), "value": op_rows[0]["value"], "period_start": op_rows[0].get("period_start"), "period_end": end, "accession": accession, "dimensions": op_rows[0].get("dimensions")},
            ])
        segments[key] = {"label": key.replace("_", " ").title(), "annual_revenue": revenues, "annual_operating_income": operating, "latest_ytd_revenue": revenues[-1], "prior_ytd_revenue": revenues[-2], "latest_ytd_operating_income": operating[-1], "prior_ytd_operating_income": operating[-2], "ttm_revenue": revenues[-1], "ttm_operating_income": operating[-1], "archetype_growth_anchor": float({"productivity_and_business_processes": 0.07, "intelligent_cloud": 0.10, "more_personal_computing": 0.03}[key])}
    consolidated = {
        "revenue": sum(segment["ttm_revenue"] for segment in segments.values()),
        "operating_income": sum(segment["ttm_operating_income"] for segment in segments.values()),
    }
    non_dim = lambda name: [row for row in relevant if row.get("local_name") == name and row.get("period_end") == period_end and row.get("period_start") and not row.get("dimensions") and row.get("unit") == "USD"]
    consolidated_rows = {name: non_dim(name) for name in ("RevenueFromContractWithCustomerExcludingAssessedTax", "OperatingIncomeLoss")}
    consolidated_unique = {name: {float(row["value"]): row for row in rows} for name, rows in consolidated_rows.items()}
    if any(len(rows) != 1 for rows in consolidated_unique.values()):
        raise CashScheduleRefreshError("MSFT consolidated segment reconciliation fact is missing")
    consolidated_reported = {"revenue": float(next(iter(consolidated_unique["RevenueFromContractWithCustomerExcludingAssessedTax"]))), "operating_income": float(next(iter(consolidated_unique["OperatingIncomeLoss"]))) }
    if any(abs(consolidated[key] - consolidated_reported[key]) / max(abs(consolidated_reported[key]), 1.0) > 0.001 for key in consolidated):
        raise CashScheduleRefreshError("MSFT segment totals do not reconcile to consolidated reported facts")
    rd_rows = [
        {"concept": row.get("qname"), "value": row.get("value"), "period_start": row.get("period_start"), "period_end": row.get("period_end"), "accession": accession, "unit": row.get("unit")}
        for row in relevant
        if row.get("local_name") in {"ResearchAndDevelopmentExpense", "FinitelivedIntangibleAssetsAcquired1", "AcquisitionsNetOfCashAcquiredAndPurchasesOfIntangibleAndOtherAssets"}
        and row.get("period_end") == period_end and row.get("period_start") and not row.get("dimensions")
    ]
    return {"status": "segment_evidence_reconciled", "period_end": period_end, "accession": accession, "annual_periods": annual_ends, "segments": segments, "consolidated_reported": consolidated_reported, "segment_sources": segment_sources, "rd_intangible_sources": rd_rows, "rd_policy_status": "source_amounts_present_but_asset_life_and_amortization_policy_unapproved", "cutoff": cutoff}


def bind_cash_schedule_sources(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, structural_packet: Mapping[str, Any] | None, cutoff: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind a cached AAPL SEC packet and return a fresh recipe plus exact ledger."""
    cutoff = _iso(cutoff, "cutoff")
    cik = _validate_identity(policy, packet, ticker=str(recipe.get("ticker")))
    submissions = packet["submissions"]
    companyfacts = packet["companyfacts"]
    records = _records(submissions)
    prior_cutoff = _iso(recipe.get("evidence_cutoff"), "recipe evidence_cutoff")
    if prior_cutoff > cutoff:
        raise CashScheduleRefreshError('recipe evidence cutoff is after refresh cutoff')
    allowed = set(policy.get("routine_8k_items", ROUTINE_EVENT_ITEMS))
    for event in records:
        if event.get("form") in {"8-K", "8-K/A"} and prior_cutoff < str(event.get("filingDate", "")) <= cutoff:
            items = {item.strip() for item in str(event.get("items", "")).split(",") if item.strip()}
            if not items or items - allowed:
                raise CashScheduleRefreshError("new corporate-event filing requires an approved event rule")
    controlling = packet.get('_selected_controlling_filing') or _select_filing(records, cutoff)
    if controlling not in records or controlling.get('filingDate', '') > cutoff:
        raise CashScheduleRefreshError('selected controlling filing is not eligible cached evidence')
    period = controlling["reportDate"]
    if policy.get("model_profile") == "segment_operating_income_intangible_investment":
        if not isinstance(structural_packet, Mapping):
            gate = {"status": "blocked", "ticker": "MSFT", "controlling_filing": controlling, "period_end": period, "source_gate": "current inline-XBRL segment-operating-income package required", "source_packet_has_structural_filing": False}
            error = CashScheduleRefreshError("MSFT refresh blocked: current segment-table structural package is unavailable")
            error.source_gate = gate  # type: ignore[attr-defined]
            raise error
        from .refresh_msft_model import build_msft_forecast
        forecast = build_msft_forecast({**packet,'structural_filing':structural_packet,
            '_selected_controlling_filing':controlling}, recipe, cutoff=cutoff,
            approved_policy=policy['approved_forecast_policy'])
        segment_gate = forecast['source_ledger']['segment_evidence']
        from .refresh_financials import structural_bridge_evidence
        bridge_evidence, receipt = structural_bridge_evidence(
            {**packet, "structural_filing": structural_packet},
            period=period, cutoff=cutoff, cik=cik,
        )
        normalizer = CompanyFactsNormalizer(
            companyfacts, fiscal_year_end=submissions.get("fiscalYearEnd"),
            as_of_date=cutoff, filing_records=records, concept_config=load_concept_config(),
        )
        balance = normalizer.normalize_balance_sheet(
            period_end=period, filing_evidence=packet.get("filing_evidence", ()),
            bridge_evidence=bridge_evidence,
        )["balance_sheet"]
        resolution = balance["bridge_precheck"]
        bridge_gate = {
            "status": "resolved" if resolution.get("can_value") else "source_extracted_bridge_unresolved",
            "missing_fields": list(resolution.get("blocking_fields", ())),
            "resolution": resolution,
            "structural_receipt": receipt,
        }
        if not resolution.get('can_value'):
            error = CashScheduleRefreshError('MSFT source bridge unresolved: ' + ', '.join(bridge_gate['missing_fields']))
            error.source_gate = {'ticker':'MSFT','segment_evidence':segment_gate,'bridge':bridge_gate}
            raise error
        shares = number(balance['fully_diluted_shares_proxy'],'MSFT source shares')
        if shares <= 0:
            raise CashScheduleRefreshError('MSFT source share count is not positive')
        refreshed = deepcopy(recipe)
        for name,spec in refreshed['scenarios'].items():
            cash_stat = {'bear':'low','base':'midpoint','bull':'high'}[name]
            claim_stat = {'bear':'high','base':'midpoint','bull':'low'}[name]
            detail = forecast['scenarios'][name]['model']['detail']
            spec['inputs'].update(cash_flows=[number(row['fcff'],'forecast FCFF') for row in detail['forecast_schedule']],
                terminal_cash_flow=number(detail['terminal_fcff'],'terminal FCFF'), shares=shares,
                net_bridge=resolution['cash_and_investments'][cash_stat]-sum(resolution[field][claim_stat]
                    for field in ('total_debt','preferred_equity','noncontrolling_interests')))
        refreshed.update(evidence_cutoff=cutoff,source_accession=controlling['accessionNumber'],forecast_metric='cash_fcff',model_version=policy['version'])
        evaluated = evaluate_recipe(refreshed)
        from .bridge_policy import BridgeResolution, assess_bridge_materiality
        enterprise = evaluated['scenarios']['base']['raw_value'] * shares - refreshed['scenarios']['base']['inputs']['net_bridge']
        ledger = {'controlling_filing':controlling,'period_end':period,'frozen_cutoff':cutoff,'cik':cik,
            'recipe_engine':'cash_schedule','policy_version':policy['version'],
            'sources':{**forecast['source_ledger'],'normalized_bridge':bridge_gate},
            'values':{'shares':shares,'cash_and_investments':resolution['cash_and_investments']['midpoint'],
                'debt':resolution['total_debt']['midpoint'],'preferred_equity':resolution['preferred_equity']['midpoint'],
                'noncontrolling_interests':resolution['noncontrolling_interests']['midpoint']},
            'normalization':{'method':'reported segment FY or FY plus comparable YTD; approved growth and reinvestment policy',
                'assumptions':forecast['normalized_assumptions'],'r_and_d_treatment':forecast['source_ledger']['r_and_d_treatment']},
            'scenario_results':forecast['scenarios'],
            'bridge_quality':{**assess_bridge_materiality(BridgeResolution.from_dict(resolution),enterprise_value=enterprise).as_dict(),'complete':resolution['complete']},
            'result':{'range':evaluated['range'],'recipe_hash':evaluated['recipe_hash'],'effective_recipe_hash':evaluated['effective_recipe_hash']}}
        return refreshed, ledger
    normalizer = CompanyFactsNormalizer(companyfacts, fiscal_year_end=submissions.get("fiscalYearEnd"), as_of_date=cutoff, filing_records=records, concept_config=load_concept_config())
    policy_assumptions = policy["policy_assumptions"]
    normalized = _annual_margin_growth(normalizer, policy_assumptions)
    tax_rate, tax_rows = _annual_tax(normalizer, float(policy_assumptions["tax_rate_cap"]))
    flows = {field: normalizer.ttm_flow(field) for field in ("revenue", "operating_income", "capital_expenditures", "operating_cash_flow")}
    if any(flow["period_end"] != period for flow in flows.values()):
        raise CashScheduleRefreshError("source-derived operating flow periods are not aligned")
    capex = flows["capital_expenditures"]
    if float(capex["value"]) < 0:
        raise CashScheduleRefreshError("reported total capex has an unsupported negative sign")
    if structural_packet is None or structural_packet.get("source_accession") != controlling["accessionNumber"]:
        raise CashScheduleRefreshError("structural filing package is required and must match controlling filing")
    # Reuse the same official-evidence and balance-only normalizer as the
    # ordinary FCFF refresh path.  Missing claims remain missing; structural
    # absence is never inferred from an empty Companyfacts concept list.
    from .refresh_financials import structural_bridge_evidence
    bridge_evidence, structural_receipt = structural_bridge_evidence(
        {**packet, "structural_filing": structural_packet},
        period=period,
        cutoff=cutoff,
        cik=cik,
    )
    balance_result = normalizer.normalize_balance_sheet(
        period_end=period,
        filing_evidence=packet.get("filing_evidence", ()),
        bridge_evidence=bridge_evidence,
    )
    balance = balance_result["balance_sheet"]
    precheck = balance["bridge_precheck"]
    shares = balance.get("fully_diluted_shares_proxy")
    if not isinstance(shares, (int, float)) or shares <= 0:
        raise CashScheduleRefreshError("normalized bridge has no positive diluted-share proxy")
    missing = tuple(precheck.get("missing_fields", ()))
    bridge_ledger = {
        "normalized_balance_sheet": balance,
        "structural_receipt": structural_receipt,
        "bridge_quality": precheck,
        "missing_fields": list(missing),
    }
    ledger_base: dict[str, Any] = {
        "controlling_filing": controlling,
        "period_end": period,
        "frozen_cutoff": cutoff,
        "cik": cik,
        "recipe_engine": SUPPORTED_ENGINE,
        "policy_version": policy.get("version"),
        "sources": {"flows": flows, "tax_history": tax_rows, "normalized_bridge": bridge_ledger},
        "bridge_quality": precheck,
        "values": {
            "cash_and_investments": precheck["cash_and_investments"]["midpoint"],
            "debt": precheck["total_debt"]["midpoint"],
            "preferred_equity": precheck["preferred_equity"]["midpoint"],
            "noncontrolling_interests": precheck["noncontrolling_interests"]["midpoint"],
            "net_bridge": precheck["bridge_adjustment"]["midpoint"],
            "shares": shares,
            "total_reported_capex": float(capex["value"]),
            "normalized_tax_rate": tax_rate,
            **{key: normalized[key] for key in ("starting_revenue", "starting_operating_margin", "normalized_operating_margin", "target_operating_margin", "initial_revenue_growth")},
        },
        "normalization": {
            "formula": "source TTM revenue/op income; annual tax median capped at policy maximum; total reported capex",
            "capex_treatment": policy_assumptions["capex_treatment"],
            "tax_history": tax_rows,
            "growth_and_margin": normalized,
        },
    }
    if not precheck.get("can_value"):
        error = CashScheduleRefreshError(
            "source-bound cash schedule unresolved: " + ", ".join(missing or precheck.get("blocking_fields", ()))
        )
        error.ledger = ledger_base  # type: ignore[attr-defined]
        raise error
    bridge = {
        "cash_and_investments": float(precheck["cash_and_investments"]["midpoint"]),
        "debt": float(precheck["total_debt"]["midpoint"]),
        "preferred_equity": float(precheck["preferred_equity"]["midpoint"]),
        "noncontrolling_interests": float(precheck["noncontrolling_interests"]["midpoint"]),
        "shares": float(shares),
    }
    refreshed = deepcopy(recipe)
    for name in ("bear", "base", "bull"):
        cash_stat = {'bear':'low','base':'midpoint','bull':'high'}[name]
        claim_stat = {'bear':'high','base':'midpoint','bull':'low'}[name]
        case_bridge = {**bridge,
            'cash_and_investments':float(precheck['cash_and_investments'][cash_stat]),
            'debt':float(precheck['total_debt'][claim_stat]),
            'preferred_equity':float(precheck['preferred_equity'][claim_stat]),
            'noncontrolling_interests':float(precheck['noncontrolling_interests'][claim_stat])}
        base_inputs = recipe["scenarios"][name]["inputs"]
        scenario = policy["scenario_assumptions"][name]
        calc = _schedule(normalized=normalized, tax_rate=tax_rate, scenario=scenario, base_inputs=base_inputs, policy_assumptions=policy_assumptions, bridge=case_bridge)
        inputs = refreshed["scenarios"][name]["inputs"]
        inputs["cash_flows"] = calc["cash_flows"]
        inputs["terminal_cash_flow"] = calc["terminal_cash_flow"]
        inputs["net_bridge"] = case_bridge["cash_and_investments"] - case_bridge["debt"] - case_bridge["preferred_equity"] - case_bridge["noncontrolling_interests"]
        inputs["shares"] = bridge["shares"]
        # Keep the approved scenario rate/growth inputs exactly as stored in
        # the recipe; the model evaluator already used those values above.
        ledger_base.setdefault("scenario_results", {})[name] = calc
    refreshed["evidence_cutoff"] = cutoff
    refreshed["source_accession"] = controlling["accessionNumber"]
    evaluated = evaluate_recipe(refreshed)
    from .bridge_policy import BridgeResolution, assess_bridge_materiality
    base_equity = evaluated['scenarios']['base']['raw_value'] * bridge['shares']
    base_enterprise = base_equity - refreshed['scenarios']['base']['inputs']['net_bridge']
    ledger_base['bridge_quality'] = {**assess_bridge_materiality(BridgeResolution.from_dict(precheck),enterprise_value=base_enterprise).as_dict(),
                                   'complete':precheck['complete']}
    refreshed['forecast_metric'] = 'cash_fcff'
    ledger_base["result"] = {"range": evaluated["range"], "recipe_hash": evaluated["recipe_hash"], "effective_recipe_hash": evaluated["effective_recipe_hash"]}
    return refreshed, ledger_base


def bind_and_evaluate_cash_schedule_recipe(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, structural_packet: Mapping[str, Any] | None, cutoff: str) -> dict[str, Any]:
    refreshed, ledger = bind_cash_schedule_sources(policy, recipe, packet, structural_packet=structural_packet, cutoff=cutoff)
    return {"bound": ledger["values"], "baseline_replay": dict(recipe.get("replay", evaluate_recipe(recipe)["range"])), "refreshed_recipe": refreshed, "refreshed_replay": ledger["result"]["range"], "source_ledger": ledger}


# Naming symmetry with the residual-income adapter makes future integration a
# small dispatch change while keeping this file independently callable today.
bind_and_evaluate_existing_cash_schedule_recipe = bind_and_evaluate_cash_schedule_recipe
