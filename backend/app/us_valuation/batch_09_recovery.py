"""One controlled recovery attempt for Batch 09's withheld CLX issuer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_conditional_estimates import five_year_fcff_dcf
from .batch_02_practical_inputs import _annual_cash_fcff, _normalizer, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point
from .batch_07_history import _structural_flow
from .batch_09 import BATCH_09_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION, build_cash_fcff_history_profile
from .reliability import assess_reliability


BATCH_09_RECOVERY_VERSION = "BATCH-09-CLX-RECOVERY-1.0"


def _dimensioned_flow(
    structural: dict[str, Any], *, name: str, start: str, end: str, expected: float, member: str
) -> dict[str, Any]:
    rows = [
        row for row in structural["facts"]
        if row.get("local_name") == name
        and row.get("period_start") == start
        and row.get("period_end") == end
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) == expected
        and any(member in str(value) for _, value in (row.get("dimensions") or []))
    ]
    if not rows:
        raise ValueError(f"{name}/{member}: expected {expected} absent")
    row = rows[0]
    return {
        "source_kind": "structural_xbrl",
        "accession": structural["source_accession"],
        "filed": structural.get("filed_date"),
        "form": structural.get("form"),
        "period_start": start,
        "period_end": end,
        "concept": row.get("qname"),
        "dimensions": row.get("dimensions"),
        "unit": row.get("unit") or "USD",
        "value": expected,
        "reported_vs_estimated": "reported",
    }


def build_clx_recovery_result(
    *, source_root: Path, recovered_structural: Path
) -> dict[str, Any]:
    packet = Path(source_root) / "CLX"
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads(Path(recovered_structural).read_text())
    filing = _controlling(manifest, submissions)
    if (
        filing["accession"] != "0000021076-26-000034"
        or filing["period_end"] != "2026-06-30"
        or structural["source_accession"] != filing["accession"]
        or len(structural.get("facts", ())) < 1_000
    ):
        raise ValueError("CLX recovered source identity or completeness mismatch")

    start, end = "2025-07-01", "2026-06-30"
    reported_revenue = _structural_flow(structural, name="RevenueFromContractWithCustomerExcludingAssessedTax", start=start, end=end, expected=6_720_000_000.)
    operating_cash = _structural_flow(structural, name="NetCashProvidedByUsedInOperatingActivities", start=start, end=end, expected=612_000_000.)
    capex = _structural_flow(structural, name="PaymentsToAcquirePropertyPlantAndEquipment", start=start, end=end, expected=207_000_000.)
    interest = _structural_flow(structural, name="InterestExpense", start=start, end=end, expected=130_000_000.)
    pretax = _structural_flow(structural, name="IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", start=start, end=end, expected=791_000_000.)
    income_tax = _structural_flow(structural, name="IncomeTaxExpenseBenefit", start=start, end=end, expected=190_000_000.)
    venture_payment = _structural_flow(structural, name="PaymentForVentureAgreementTermination", start=start, end=end, expected=476_000_000.)
    pro_forma_revenue = _dimensioned_flow(structural, name="BusinessAcquisitionsProFormaRevenue", start=start, end=end, expected=7_331_000_000., member="GOJOIndustriesMember")
    prior_pro_forma_revenue = _dimensioned_flow(structural, name="BusinessAcquisitionsProFormaRevenue", start="2024-07-01", end="2025-06-30", expected=7_882_000_000., member="GOJOIndustriesMember")
    tax_rate = 190_000_000. / 791_000_000.
    reported_cash_fcff = cash_fcff_from_reported(
        operating_cash_flow=612_000_000.,
        capital_expenditures=207_000_000.,
        spectrum_investment=0.,
        interest_expense=130_000_000.,
        tax_rate=tax_rate,
    )

    normalizer = _normalizer(submissions, facts)
    _, _, annual_sources = _annual_cash_fcff(
        normalizer,
        spectrum_required=False,
        spectrum_floor=0.,
        spectrum_source={},
        scope_adjustment=0.,
    )
    profile = build_cash_fcff_history_profile(
        annual_cash_states=annual_sources,
        ttm_revenue=6_720_000_000.,
        ttm_cash_fcff=reported_cash_fcff,
        ttm_period_end=end,
        ttm_sources=(reported_revenue, operating_cash, capex, interest, pretax, income_tax, venture_payment, pro_forma_revenue),
        valuation_date=BATCH_09_VALUATION_DATE,
    )
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None:
        raise ValueError("CLX history is insufficient after source recovery")

    # The recovery range deliberately stays inside the reported FY22-FY26
    # cash/growth history instead of treating one quarter of acquired GOJO
    # revenue or a one-time cash payment as a recurring run rate.
    margins = (.0798, .0869, .1092)
    growth = (-.0297, -.0193, .0301)
    wacc = (.115, .10, .09)
    terminal_growth = (0., .01, .02)
    shares = (122_132_000. * 1.025, 122_132_000., 122_132_000. * .975)
    debt = 1_086_000_000. + 1_000_000. + 3_981_000_000. + 16_000_000. + 62_000_000.
    cash, nci = 143_000_000., 162_000_000.
    rows = []
    for index, name in enumerate(("bear", "base", "bull")):
        raw = five_year_fcff_dcf(
            revenue=6_720_000_000.,
            fcff_margin=margins[index],
            growth=growth[index],
            wacc=wacc[index],
            terminal_growth=terminal_growth[index],
            cash_and_investments=cash,
            debt=debt,
            noncontrolling_interests=nci,
            shares=shares[index],
        )
        value = max(0., float(raw["value_per_share"]))
        rows.append({
            "name": name,
            "conditional_value_per_share": value,
            "raw_value_per_share": float(raw["value_per_share"]),
            "reported_revenue": 6_720_000_000.,
            "cash_conversion_margin": margins[index],
            "growth": growth[index],
            "wacc": wacc[index],
            "terminal_growth": terminal_growth[index],
            "shares": shares[index],
            "limited_liability_floor_applied": value == 0. and float(raw["value_per_share"]) < 0.,
        })
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError("CLX recovery produced an invalid range")
    warning = "Conditional Low estimate. The current 10-K is now structurally complete, but the GOJO acquisition, acquisition debt, one-time Glad venture payment, integration, and weaker pro-forma sales make the range wide. The one-time payment is disclosed but not silently added back."
    invalidation = "Invalidate if GOJO integration cash, pro-forma revenue, debt and leases, NCI, shares, or normalized cash conversion leaves the recorded range."
    reliability = assess_reliability(
        accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"],
        scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"],
        model_cap="Low", source_cap="High", reasons=("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"),
    )
    assumptions = {
        **profile.public_metadata(),
        "normalization_basis": "company_history_plus_reported_GOJO_pro_forma",
        "assumption_source_mix": "reported_history_pro_forma_and_finsight_policy",
        "cash_conversion_margin": margins,
        "growth": growth,
        "scenario_calibration": "Conservative governed states bounded by reported FY2022-FY2026 cash conversion and revenue history; reported GOJO pro-forma figures are event context, not the DCF scale.",
        "wacc": wacc,
        "terminal_growth": terminal_growth,
        "shares": shares,
        "equity_floor_basis": "limited-liability floor after negative bear residual" if scenario["low"] == 0 else "not applied",
        "calculator_calibration": "Calculator is calibrated to the published base; private source history and bridge remain fixed.",
        "invalidation": invalidation,
    }
    baseline = BaselineValuation(
        ticker="CLX", method="post_acquisition_history_cash_fcff", method_version=BATCH_09_RECOVERY_VERSION,
        low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label,
        availability_type=AvailabilityType.CONDITIONAL,
        key_assumptions=(
            BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Five source-linked annual periods bound cash conversion and ordinary growth."),
            BaselineAssumption("reported current revenue", "6720000000", AssumptionClassification.REPORTED, "The controlling filing's FY2026 revenue anchors the DCF; GOJO pro-forma revenue remains context only."),
            BaselineAssumption("recovery policy", str(assumptions), AssumptionClassification.FINSIGHT_ASSUMPTION, "Discount rates, terminal growth, share sensitivity, and the limited-liability floor are transparent policy inputs."),
        ),
        warnings=(warning, invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link="/api/us-valuations/CLX/calculator",
    )
    bridge_sources = [
        _point(structural, name="CashAndCashEquivalentsAtCarryingValue", expected=143_000_000., period_end=end),
        _point(structural, name="CommercialPaper", expected=1_086_000_000., period_end=end),
        _point(structural, name="LongTermDebtCurrent", expected=1_000_000., period_end=end),
        _point(structural, name="LongTermDebtNoncurrent", expected=3_981_000_000., period_end=end),
        _point(structural, name="FinanceLeaseLiabilityCurrent", expected=16_000_000., period_end=end),
        _point(structural, name="FinanceLeaseLiabilityNoncurrent", expected=62_000_000., period_end=end),
        _point(structural, name="MinorityInterest", expected=162_000_000., period_end=end),
        _point(structural, name="PreferredStockValue", expected=0., period_end=end),
        _point(structural, name="SupplierFinanceProgramObligationCurrent", expected=229_000_000., period_end=end),
        _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=122_132_000., period_start=start, period_end=end),
    ]
    return {
        "ticker": "CLX", "method": "post_acquisition_history_cash_fcff", "model_version": BATCH_09_RECOVERY_VERSION,
        "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario,
        "reported_inputs": {"reported_revenue": 6_720_000_000., "GOJO_pro_forma_revenue_diagnostic": 7_331_000_000., "operating_cash_flow": 612_000_000., "capital_expenditures": 207_000_000., "interest_expense": 130_000_000., "venture_termination_payment_disclosed_not_added_back": 476_000_000., "reported_cash_fcff": reported_cash_fcff},
        "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(),
        "source_ledger": {"controlling_filing": filing, "current_flow_sources": [reported_revenue, operating_cash, capex, interest, pretax, income_tax, venture_payment], "GOJO_pro_forma_sources": [pro_forma_revenue, prior_pro_forma_revenue], "company_history_profile": profile.as_private_dict(), "bridge_sources": bridge_sources, "bridge_reconciliation": {"cash_and_investments": cash, "commercial_paper_long_term_debt_and_finance_leases": debt, "noncontrolling_interests": nci, "operating_leases_and_supplier_finance": "Remain in operating cash flow and are not subtracted again."}, "structural_fact_count": len(structural["facts"])},
        "warning": warning, "baseline": baseline.as_private_dict(),
    }
