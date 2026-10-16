"""History-backed launch-first baselines for controlled Batch 08."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_conditional_estimates import five_year_fcff_dcf
from .batch_02_practical_inputs import _annual_cash_fcff, _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point, _source_proven_no_other_equity_claims
from .batch_05_launch_first import _source_proven_no_debt
from .batch_06_launch_first import _annual_owner_cash
from .batch_07_history import _structural_flow
from .batch_08 import BATCH_08_TICKERS, BATCH_08_VALUATION_DATE
from .equity_fact_selection import annual_facts
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .reliability import assess_reliability


BATCH_08_HISTORY_VERSION = "BATCH-08-HISTORY-LAUNCH-FIRST-1.0"
PASS_TICKERS = frozenset({"ULTA", "HLT"})
EQUITY_EARNINGS_TICKERS = frozenset({"GM", "CVNA"})


def _shares(base: float) -> tuple[float, float, float]:
    return (base * 1.025, base, base * 0.975)


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: float
    nci: tuple[float, float, float]
    shares: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal_growth: tuple[float, float, float]
    warning: str
    invalidation: str
    cash_range: tuple[float, float, float] | None = None
    capex_range: tuple[float, float, float] = (0., 0., 0.)
    margin_stress: tuple[float, float, float] = (0., 0., 0.)


P = {
    "LULU": Policy("apparel_owner_cash_fcff", "2026-05-03", 1_514_729_000., 0., (0., 0., 0.), _shares(115_482_000.), (.11, .095, .085), (0., .015, .02), "Conditional Low owner-cash estimate. Tariff pressure, uncertain refunds, China demand, supplier finance, and exchangeable shares remain material.", "Invalidate if tariffs/refunds, debt, exchangeable-share dilution, capex, cash, or historical conversion changes.", margin_stress=(.05, .025, 0.)),
    "ULTA": Policy("specialty_retail_owner_cash_fcff", "2026-05-02", 221_300_000., 144_899_000., (0., 0., 0.), _shares(43_964_000.), (.11, .095, .085), (0., .015, .02), "History-backed specialty-retail owner-cash estimate with current borrowings included once.", "Invalidate if debt, inventory conversion, cash, investments, or diluted shares changes."),
    "KDP": Policy("post_acquisition_beverage_cash_fcff", "2026-06-30", 1_517_000_000., 31_006_000_000., (9_096_000_000., 8_939_000_000., 8_614_000_000.), _shares(1_364_200_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low estimate. The $17.4B JDE Peet's acquisition, acquisition debt, convertible preferred, NCI, inventory step-up, and integration costs make legacy history only a broad cash-conversion guide.", "Invalidate when pro-forma revenue, acquisition debt/preferred/NCI, restructuring, shares, or combined cash conversion leaves the range."),
    "NCLH": Policy("unavailable_cruise_cycle_history", "2026-06-30", 218_100_000., 15_034_785_000., (0., 0., 0.), _shares(465_388_927.), (.13, .11, .095), (0., .01, .02), "Withheld. Current and median historical cash FCFF are negative, while newbuild commitments and leverage prevent a defensible positive normalized base.", "Revalue after a source-backed positive through-cycle cash range and explicit newbuild funding schedule are available."),
    "APTV": Policy("post_spin_comparative_cash_fcff", "2026-06-30", 821_000_000., 5_354_000_000., (0., 0., 0.), _shares(212_530_000.), (.12, .10, .09), (0., .01, .02), "Conditional Low post-Versigent estimate. Only current and comparative continuing H1 cash are economically comparable.", "Invalidate when post-spin annual cash, debt, reinvestment, or shares leaves the range."),
    "ABNB": Policy("travel_marketplace_bounded_capex_fcff", "2026-06-30", 12_069_000_000., 2_500_000_000., (0., 0., 0.), _shares(602_000_000.), (.105, .09, .08), (0., .015, .02), "Conditional Low estimate. Customer funds are segregated, while current capex comes from the filing FCF table and is annualized over a broad range.", "Invalidate if customer-fund segregation, capex, debt, investments, or diluted shares changes.", capex_range=(84_000_000., 42_000_000., 21_000_000.)),
    "HLT": Policy("asset_light_hotel_cash_fcff", "2026-06-30", 1_009_000_000., 13_343_000_000., (33_000_000., 33_000_000., 33_000_000.), _shares(230_000_000.), (.105, .09, .08), (0., .015, .02), "History-backed asset-light hotel cash-FCFF with debt, leases, and NCI reconciled once.", "Invalidate if franchise cash, debt/capital leases, NCI, cash, or diluted shares changes."),
    "DASH": Policy("marketplace_acquisition_cash_fcff", "2026-06-30", 5_939_000_000., 2_727_000_000., (11_000_000., 11_000_000., 11_000_000.), _shares(440_833_000.), (.11, .095, .085), (0., .015, .02), "Conditional Low estimate. Deliveroo/SevenRooms integration, zero-coupon convertible dilution, SBC, and marketplace working capital remain material.", "Invalidate if acquisition scope, convertible dilution, SBC, customer balances, or normalized cash leaves the range.", cash_range=(5_662_000_000., 5_939_000_000., 6_216_000_000.)),
}


EARNINGS = {
    "GM": {"method": "captive_finance_consolidated_equity_earnings", "period": "2026-06-30", "shares": _shares(918_000_000.), "concepts": ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"), "ttm": 1_857_000_000., "fy": 3_180_000_000., "current_h1": 3_901_000_000., "prior_h1": 5_224_000_000., "warning": "Conditional Low consolidated equity-earnings estimate. GM Financial remains inside earnings and no EV debt bridge is applied."},
    "CVNA": {"method": "inventory_finance_consolidated_equity_earnings", "period": "2026-06-30", "shares": _shares(740_174_000.), "concepts": ("NetIncomeLoss",), "ttm": 1_568_000_000., "fy": 1_407_000_000., "current_h1": 560_000_000., "prior_h1": 399_000_000., "warning": "Conditional Low consolidated equity-earnings estimate. Inventory, floorplan, securitization, NCI, and rapid turnaround economics remain inside consolidated earnings."},
}


POINT_SPECS = {
    "LULU": (("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 1_514_729_000.), ("OtherBorrowings", 0.), ("SupplierFinanceProgramObligationCurrent", 39_900_000.), ("PreferredStockValue", 0.)),
    "ULTA": (("CashAndCashEquivalentsAtCarryingValue", 166_300_000.), ("ShortTermInvestments", 55_000_000.), ("ShortTermBorrowings", 144_899_000.), ("ContractWithCustomerLiabilityCurrent", 541_199_000.)),
    "KDP": (("CashAndCashEquivalentsAtCarryingValue", 1_517_000_000.), ("DebtCurrent", 8_394_000_000.), ("LongTermDebtNoncurrent", 21_586_000_000.), ("FinanceLeaseLiability", 1_026_000_000.), ("MinorityInterest", 4_196_000_000.), ("TemporaryEquityCarryingAmountAttributableToParent", 4_418_000_000.), ("TemporaryEquityLiquidationPreference", 4_500_000_000.), ("SupplierFinanceProgramObligationCurrent", 2_099_000_000.), ("PreferredStockValue", 0.)),
    "NCLH": (("CashAndCashEquivalentsAtCarryingValue", 218_100_000.), ("LongTermDebtAndCapitalLeaseObligationsCurrent", 1_141_370_000.), ("LongTermDebtAndCapitalLeaseObligations", 13_893_415_000.), ("ContractWithCustomerLiabilityCurrent", 3_651_201_000.)),
    "APTV": (("CashAndCashEquivalentsAtCarryingValue", 761_000_000.), ("AvailableForSaleSecuritiesDebtSecurities", 60_000_000.), ("DebtAndCapitalLeaseObligations", 5_354_000_000.), ("MinorityInterest", 0.), ("PreferredStockValue", 0.)),
    "ABNB": (("CashAndCashEquivalentsAtCarryingValue", 6_821_000_000.), ("ShortTermInvestments", 5_248_000_000.), ("CashAndCashEquivalentsIncludedInFundsReceivableAndAmountsHeldOnBehalfOfCustomers", 12_161_000_000.), ("ContractWithCustomerLiability", 12_224_000_000.), ("DebtInstrumentCarryingAmount", 2_500_000_000.)),
    "HLT": (("CashAndCashEquivalentsAtCarryingValue", 1_009_000_000.), ("LongTermDebtAndCapitalLeaseObligations", 12_719_000_000.), ("LongTermDebtAndCapitalLeaseObligationsCurrent", 624_000_000.), ("MinorityInterest", 28_000_000.), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 5_000_000.), ("DeferredRevenueCurrent", 818_000_000.), ("DeferredRevenueNoncurrent", 1_714_000_000.), ("TotalLiabilitiesOfVariableInterestEntities", 313_000_000.)),
    "DASH": (("CashAndCashEquivalentsAtCarryingValue", 4_424_000_000.), ("AvailableForSaleSecuritiesDebtSecuritiesCurrent", 923_000_000.), ("AvailableForSaleSecuritiesDebtSecuritiesNoncurrent", 869_000_000.), ("RestrictedCashCurrent", 308_000_000.), ("RestrictedCashAndInvestmentsNoncurrent", 114_000_000.), ("ContractWithCustomerLiability", 554_000_000.), ("ConvertibleLongTermNotesPayable", 2_727_000_000.), ("TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests", 11_000_000.)),
}

SHARE_STARTS = {"LULU": "2026-02-02", "ULTA": "2026-02-01", "KDP": "2026-01-01", "NCLH": "2026-01-01", "APTV": "2026-01-01", "ABNB": "2026-01-01", "HLT": "2026-01-01", "DASH": "2026-01-01"}


def _history_source(fact):
    return {"concept": fact.concept, "value": fact.value, "unit": fact.unit, "period_start": getattr(fact, "period_start", getattr(fact, "start", None)), "period_end": getattr(fact, "period_end", getattr(fact, "end", None)), "filed_date": getattr(fact, "filed_date", getattr(fact, "filed", None)), "accession": getattr(fact, "accession", getattr(fact, "accn", None)), "form": fact.form, "fiscal_year": fact.fiscal_year}


def _annual_cash_with_losses(normalizer) -> tuple[tuple[float, ...], tuple[float, ...], tuple[dict[str, Any], ...]]:
    cash, revenue_values, rows = [], [], []
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        capex = normalizer.annual_at_end("capital_expenditures", operating.end)
        interest = normalizer.annual_at_end("interest_expense", operating.end)
        revenue = normalizer.annual_at_end("revenue", operating.end)
        pretax = normalizer.annual_at_end("pretax_income", operating.end)
        tax = normalizer.annual_at_end("income_tax", operating.end)
        if capex is None or interest is None or revenue is None or revenue.value <= 0:
            continue
        tax_rate = max(0., min(.30, tax.value / pretax.value)) if pretax is not None and tax is not None and pretax.value > 0 else .21
        value = cash_fcff_from_reported(operating_cash_flow=operating.value, capital_expenditures=capex.value, spectrum_investment=0., interest_expense=abs(interest.value), tax_rate=tax_rate)
        cash.append(value); revenue_values.append(float(revenue.value)); rows.append({"period_end": operating.end, "operating_cash_flow": operating.as_dict(), "capital_expenditures": capex.as_dict(), "interest_expense": interest.as_dict(), "pretax_income": pretax.as_dict() if pretax else None, "income_tax": tax.as_dict() if tax else None, "revenue": revenue.as_dict(), "cash_fcff": value, "formula": "OCF - capex + after-tax interest; negative cycle observations retained"})
    return tuple(cash), tuple(revenue_values), tuple(rows)


def _dash_owner_cash(normalizer) -> tuple[tuple[float, ...], tuple[float, ...], tuple[dict[str, Any], ...]]:
    cash, revenue_values, rows = [], [], []
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        ppe = normalizer.annual_at_end("capital_expenditures", operating.end)
        software = normalizer.annual_at_end("software_development", operating.end)
        revenue = normalizer.annual_at_end("revenue", operating.end)
        if ppe is None or software is None or revenue is None or revenue.value <= 0:
            continue
        value = operating.value - ppe.value - software.value
        cash.append(value); revenue_values.append(float(revenue.value)); rows.append({"period_end": operating.end, "operating_cash_flow": operating.as_dict(), "capital_expenditures": ppe.as_dict(), "software_development": software.as_dict(), "interest_expense": None, "pretax_income": None, "income_tax": None, "revenue": revenue.as_dict(), "cash_fcff": value, "formula": "OCF - PP&E capex - capitalized software; current convertible note is zero-coupon"})
    return tuple(cash), tuple(revenue_values), tuple(rows)


def _ocf_history(normalizer, *, ttm_revenue: float, ttm_ocf: float, ttm_period: str, ttm_sources) -> CompanyHistoryProfile:
    observations, annual_periods, growth_rows, prior = [], [], [], None
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        revenue = normalizer.annual_at_end("revenue", operating.end)
        if revenue is None or revenue.value <= 0:
            continue
        annual_periods.append(operating.end); observations.append(HistoryObservation("annual", operating.end, revenue.fiscal_year, operating.value / revenue.value, "ratio", "reported annual OCF / annual revenue before bounded capex", (_history_source(operating), _history_source(revenue))))
        if prior is not None:
            growth_rows.append(HistoryObservation("annual", operating.end, revenue.fiscal_year, revenue.value / prior.value - 1, "ratio", "current annual revenue / prior annual revenue - 1", (_history_source(prior), _history_source(revenue))))
        prior = revenue
    observations.append(HistoryObservation("operating_ttm", ttm_period, None, ttm_ocf / ttm_revenue, "ratio", "reported TTM OCF / TTM revenue before bounded capex", tuple(dict(row) for row in ttm_sources)))
    metrics = tuple(metric for metric in (summarize_history_metric("cash_conversion_margin", observations), summarize_history_metric("revenue_growth", growth_rows)) if metric is not None)
    periods = tuple(annual_periods[-5:]); full = len(set(periods)) >= 3
    return CompanyHistoryProfile(HISTORY_POLICY_VERSION, "operating_cash_before_bounded_capex", BATCH_08_VALUATION_DATE, periods, metrics, full, "reported_and_company_history" if full else "reported_history_and_finsight_policy")


def _post_spin_profile(structural) -> CompanyHistoryProfile:
    current_revenue = _structural_flow(structural, name="RevenueFromContractWithCustomerExcludingAssessedTax", start="2026-01-01", end="2026-06-30", expected=6_306_000_000.)
    prior_revenue = _structural_flow(structural, name="RevenueFromContractWithCustomerExcludingAssessedTax", start="2025-01-01", end="2025-06-30", expected=6_186_000_000.)
    current_ocf = _structural_flow(structural, name="NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", start="2026-01-01", end="2026-06-30", expected=82_000_000.)
    prior_ocf = _structural_flow(structural, name="NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", start="2025-01-01", end="2025-06-30", expected=531_000_000.)
    current_capex = _structural_flow(structural, name="PaymentsToAcquireProductiveAssets", start="2026-01-01", end="2026-06-30", expected=278_000_000.)
    prior_capex = _structural_flow(structural, name="PaymentsToAcquireProductiveAssets", start="2025-01-01", end="2025-06-30", expected=267_000_000.)
    observations = (HistoryObservation("comparative_h1", "2025-06-30", 2025, (531_000_000.-267_000_000.)/6_186_000_000., "ratio", "continuing H1 owner cash / revenue", (prior_revenue, prior_ocf, prior_capex)), HistoryObservation("current_h1", "2026-06-30", 2026, (82_000_000.-278_000_000.)/6_306_000_000., "ratio", "continuing H1 owner cash / revenue", (current_revenue, current_ocf, current_capex)))
    growth = HistoryObservation("current_h1", "2026-06-30", 2026, 6_306_000_000./6_186_000_000.-1, "ratio", "current H1 revenue / comparative H1 revenue - 1", (prior_revenue, current_revenue))
    metrics = tuple(metric for metric in (summarize_history_metric("cash_conversion_margin", observations), summarize_history_metric("revenue_growth", (growth,))) if metric is not None)
    return CompanyHistoryProfile(HISTORY_POLICY_VERSION, "post_spin_comparative_h1", BATCH_08_VALUATION_DATE, ("2025-06-30", "2026-06-30"), metrics, False, "reported_history_and_finsight_policy")


def _bridge_sources(ticker, structural, policy):
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT_SPECS[ticker]]
    rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=policy.shares[1], period_start=SHARE_STARTS[ticker], period_end=policy.period))
    if ticker == "LULU":
        rows.append(_source_proven_no_debt(structural, period_end=policy.period))
    if ticker in {"LULU", "ULTA", "NCLH", "ABNB"}:
        rows.append(_source_proven_no_other_equity_claims(structural, period_end=policy.period))
    if ticker == "KDP":
        rows.extend(({"source_kind": "structural_xbrl_and_governed_policy", "accession": structural["source_accession"], "field": "jde_peets_integration_reserve", "period_end": policy.period, "reported_vs_estimated": "reported_range", "value_range": {"bear": 400_000_000., "base": 325_000_000., "bull": 0.}, "basis": "The filing reports $325M-$400M expected integration costs; the reserve is deducted once with NCI and temporary equity."}, {"source_kind": "structural_xbrl_pro_forma", "accession": structural["source_accession"], "field": "combined_revenue_anchor", "period_start": "2026-01-01", "period_end": policy.period, "reported_h1": 14_129_000_000., "annualized_value": 28_258_000_000., "unit": "USD", "reported_vs_estimated": "reported_h1_annualized", "basis": "The filing reports pro-forma combined H1 revenue; doubling it supplies scale but not a forecast and keeps the result Conditional."}))
    if ticker == "APTV":
        rows.extend((_structural_flow(structural, name="CashPaymentsRelatedToSpinOff", start="2026-01-01", end=policy.period, expected=282_000_000.), {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "field": "versigent_equity_distribution", "period_end": policy.period, "value": -2_598_000_000., "unit": "USD", "reported_vs_estimated": "reported", "basis": "The controlling filing reports the Versigent spin-off distribution; only continuing comparative H1 cash is used."}))
    if ticker == "ABNB":
        rows.append({"source_kind": "issuer_filing_fcf_table_and_governed_policy", "accession": structural["source_accession"], "field": "current_capex", "period_start": "2026-01-01", "period_end": policy.period, "reported_h1": 21_000_000., "reported_vs_estimated": "reported_h1_annualized_range", "value_range": {"bear": 84_000_000., "base": 42_000_000., "bull": 21_000_000.}, "basis": "The filing FCF table reports $21M H1 capex. FinSight annualizes it for base, doubles that annual rate for bear, and never substitutes zero."})
    if ticker == "DASH":
        rows.extend(({"source_kind": "governed_policy", "field": "customer_contract_cash_reserve", "period_end": policy.period, "reported_vs_estimated": "estimated_range", "value_range": {"bear": 554_000_000., "base": 277_000_000., "bull": 0.}, "basis": "The reported contract liability is reserved from excess cash over full/half/zero endpoints and is not subtracted again as an operating liability."}, _structural_flow(structural, name="PaymentsToDevelopSoftware", start="2026-01-01", end=policy.period, expected=258_000_000.)))
    if ticker == "LULU":
        rows.append({"source_kind": "issuer_filing_text_and_governed_policy", "accession": structural["source_accession"], "field": "tariff_margin_stress", "period_end": policy.period, "reported_vs_estimated": "reported_condition_with_estimated_cash_impact", "cash_margin_reduction": {"bear": .05, "base": .025, "bull": 0.}, "basis": "The filing describes a roughly 500bp Americas margin impact and uncertain tariff refunds. The cash-margin stress is applied once and keeps the result Conditional."})
    if ticker == "NCLH":
        rows.append({"source_kind": "issuer_filing_text_and_cash_flow_reconciliation", "accession": structural["source_accession"], "field": "newbuild_commitments", "period_end": policy.period, "reported_commitment": 18_648_000_000., "current_ttm_capex": 3_295_106_000., "unit": "USD", "reported_vs_estimated": "reported_commitment_and_reported_cash_flow", "basis": "Twelve non-cancelable newbuild contracts total $18.648B. Current TTM capex is already inside cash FCFF and approximates a six-year straight-line commitment rate, so it is not subtracted twice."})
    return rows


def _equity_profile(facts, concepts) -> CompanyHistoryProfile:
    gaap = facts["facts"]["us-gaap"]
    selected = annual_facts(gaap, concepts=concepts, unit="USD", valuation_date=BATCH_08_VALUATION_DATE)
    rows = [HistoryObservation("annual", fact.period_end, fact.fiscal_year, fact.value, "USD", "reported consolidated annual earnings", (_history_source(fact),)) for _, fact in sorted(selected.items())[-5:]]
    metric = summarize_history_metric("normalized_consolidated_earnings", rows)
    periods = tuple(row.period_end for row in rows)
    return CompanyHistoryProfile(HISTORY_POLICY_VERSION, "consolidated_equity_earnings", BATCH_08_VALUATION_DATE, periods, (metric,) if metric else (), len(set(periods)) >= 3, "reported_and_company_history" if len(set(periods)) >= 3 else "reported_history_and_finsight_policy")


def _equity_result(ticker, filing, structural, facts):
    spec = EARNINGS[ticker]; profile = _equity_profile(facts, spec["concepts"]); metric = profile.metric("normalized_consolidated_earnings")
    if metric is None or not profile.full_history:
        raise ValueError(f"{ticker}: earnings history is insufficient")
    earnings = (metric.low, metric.base, metric.high); multiples = (4., 7., 10.); rows = []
    for index, name in enumerate(("bear", "base", "bull")):
        raw = earnings[index] * multiples[index] / spec["shares"][index]
        rows.append({"name": name, "conditional_value_per_share": max(0., raw), "raw_value_per_share": raw, "normalized_consolidated_earnings": earnings[index], "earnings_multiple": multiples[index], "shares": spec["shares"][index], "limited_liability_floor_applied": raw < 0})
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if scenario["base"] <= 0 or not scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError(f"{ticker}: equity-earnings range invalid")
    shares_source = _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=spec["shares"][1], period_start="2026-01-01", period_end=spec["period"])
    equity_points = [_point(structural, name="StockholdersEquity", expected=62_000_000_000. if ticker == "GM" else 4_028_000_000., period_end=spec["period"]), _point(structural, name="StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", expected=63_641_000_000. if ticker == "GM" else 5_138_000_000., period_end=spec["period"]), shares_source]
    current_concept = "NetIncomeLossAvailableToCommonStockholdersBasic" if ticker == "GM" else "NetIncomeLoss"
    current = _structural_flow(structural, name=current_concept, start="2026-01-01", end=spec["period"], expected=spec["current_h1"])
    prior = _structural_flow(structural, name=current_concept, start="2025-01-01", end="2025-06-30", expected=spec["prior_h1"])
    assumptions = {**profile.public_metadata(), "normalized_consolidated_earnings": earnings, "earnings_multiples": multiples, "shares": spec["shares"], "ev_debt_bridge_applied": False, "equity_floor_basis": "limited-liability floor after negative normalized earnings" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator directly varies normalized earnings and the earnings multiple around the published base.", "invalidation": "Invalidate if consolidated earnings, finance/floorplan scope, NCI/unit denominator, or capital structure leaves the recorded evidence."}
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"))
    baseline = BaselineValuation(ticker=ticker, method=spec["method"], method_version=BATCH_08_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("company earnings history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Five-year source-linked consolidated earnings supply the normalized range."), BaselineAssumption("current earnings", str(spec["ttm"]), AssumptionClassification.REPORTED, "FY plus current H1 less prior H1."), BaselineAssumption("equity earnings policy", str(assumptions), AssumptionClassification.FINSIGHT_ASSUMPTION, "Earnings multiples and share sensitivity are transparent governed assumptions.")), warnings=(spec["warning"], assumptions["invalidation"]), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker": ticker, "method": spec["method"], "model_version": BATCH_08_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_consolidated_earnings": spec["ttm"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "company_history_profile": profile.as_private_dict(), "current_earnings_reconstruction": {"fy": spec["fy"], "current_h1": current, "prior_h1": prior, "ttm": spec["ttm"], "formula": "FY + current H1 - prior H1"}, "equity_context": equity_points, "bridge_treatment": "Equity-level model; finance/floorplan funding remains inside consolidated earnings and equity. No EV debt bridge is applied.", "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": spec["warning"], "baseline": baseline.as_private_dict()}


def _aptv_withheld(filing, structural):
    reason = "Versigent was spun off on 2026-04-01. Annual Companyfacts cash history is pre-spin, while only current and comparative H1 continuing cash are available; combining them would value the wrong economic object."
    context = [_structural_flow(structural, name="NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", start="2026-01-01", end="2026-06-30", expected=82_000_000.), _structural_flow(structural, name="NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", start="2025-01-01", end="2025-06-30", expected=531_000_000.), _structural_flow(structural, name="CashPaymentsRelatedToSpinOff", start="2026-01-01", end="2026-06-30", expected=282_000_000.)]
    baseline = BaselineValuation(ticker="APTV", method="unavailable_post_spin_history", method_version=BATCH_08_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(reason,))
    return {"ticker": "APTV", "method": "unavailable_post_spin_history", "model_version": BATCH_08_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {}, "governed_assumptions": {"history_policy_version": HISTORY_POLICY_VERSION, "history_years_used": 0, "normalization_basis": "post_spin_comparable_history_unavailable", "assumption_source_mix": "reported_current_comparative_only", "invalidation": "Revalue after at least three comparable continuing annual periods or a filed continuing-history reconstruction."}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "post_spin_context": context, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": reason, "baseline": baseline.as_private_dict()}


def _nclh_withheld(filing, structural, submissions, facts):
    normalizer = _normalizer(submissions, facts); revenue = normalizer.ttm_flow("revenue"); operating = normalizer.ttm_flow("operating_cash_flow"); capex = normalizer.ttm_flow("capital_expenditures"); interest = normalizer.ttm_flow("interest_expense"); tax_rate = _normalized_tax_rate(normalizer)[0]; current_cash = cash_fcff_from_reported(operating_cash_flow=float(operating["value"]), capital_expenditures=float(capex["value"]), spectrum_investment=0., interest_expense=abs(float(interest["value"])), tax_rate=tax_rate); _, _, annual_sources = _annual_cash_with_losses(normalizer); sources=[]
    for flow in (revenue,operating,capex,interest):sources.extend(dict(row) for row in flow.get("sources",[]) if isinstance(row,dict))
    profile=build_cash_fcff_history_profile(annual_cash_states=annual_sources,ttm_revenue=float(revenue["value"]),ttm_cash_fcff=current_cash,ttm_period_end="2026-06-30",ttm_sources=sources,valuation_date=BATCH_08_VALUATION_DATE);metric=profile.metric("cash_conversion_margin")
    reason="Current TTM and median historical cash FCFF are negative. One positive recovery year cannot bound a positive normalized base while $18.648B of newbuild contracts and $15.035B carrying debt remain load-bearing."
    baseline=BaselineValuation(ticker="NCLH",method="unavailable_cruise_cycle_history",method_version=BATCH_08_HISTORY_VERSION,low=None,base=None,high=None,confidence=None,availability_type=AvailabilityType.NOT_AVAILABLE,warnings=(reason,))
    return {"ticker":"NCLH","method":"unavailable_cruise_cycle_history","model_version":BATCH_08_HISTORY_VERSION,"availability_type":"not_available","scenario_rows":[],"scenario_range":{"low":None,"base":None,"high":None},"reported_inputs":{"ttm_revenue":revenue["value"],"ttm_operating_cash_flow":operating["value"],"ttm_capex":capex["value"],"ttm_cash_fcff":current_cash},"governed_assumptions":{"history_policy_version":HISTORY_POLICY_VERSION,"history_years_used":profile.history_years_used,"normalization_basis":"negative_cycle_history_no_positive_base","assumption_source_mix":"reported_and_company_history","cash_conversion_margin":None if metric is None else (metric.low,metric.base,metric.high),"invalidation":"Revalue after a source-backed positive through-cycle cash range and explicit newbuild funding schedule are available."},"history_reliability":None,"source_ledger":{"controlling_filing":filing,"flow_sources":{"revenue":revenue,"operating_cash_flow":operating,"capital_expenditures":capex,"interest_expense":interest},"company_history_profile":profile.as_private_dict(),"bridge_sources":_bridge_sources("NCLH",structural,P["NCLH"]),"bridge_reconciliation":{"carrying_debt":15_034_785_000.,"gross_principal_diagnostic":15_467_745_000.,"advance_ticket_sales_treatment":"Operating customer funding; not subtracted again as an enterprise claim."},"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":reason,"baseline":baseline.as_private_dict()}


def build_batch_08_history_result(*, ticker: str, source_root: Path, structural_root: Path) -> dict[str, Any]:
    packet = Path(source_root) / ticker; submissions = json.loads((packet / "submissions.json").read_text()); facts = json.loads((packet / "companyfacts.json").read_text()); manifest = json.loads((packet / "source-manifest.json").read_text()); structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text()); filing = _controlling(manifest, submissions)
    if structural["source_accession"] != filing["accession"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    if ticker == "APTV":
        return _aptv_withheld(filing, structural)
    if ticker == "NCLH":
        return _nclh_withheld(filing, structural, submissions, facts)
    if ticker in EQUITY_EARNINGS_TICKERS:
        return _equity_result(ticker, filing, structural, facts)
    policy = P[ticker]
    if filing["period_end"] != policy.period:
        raise ValueError(f"{ticker}: controlling period mismatch")
    normalizer = _normalizer(submissions, facts)
    if ticker == "APTV":
        profile = _post_spin_profile(structural); revenue_value = 12_612_000_000.; operating_value = 164_000_000.; capex_value = 556_000_000.; current_cash = -392_000_000.; interest = None; margins = (-.03108, .0054, .04268); growth = (-.05, 0., .03); flow_sources = {"basis": "annualized current continuing H1", "revenue": 6_306_000_000., "operating_cash_flow": 82_000_000., "capital_expenditures": 278_000_000.}
    else:
        revenue = normalizer.ttm_flow("revenue"); operating = normalizer.ttm_flow("operating_cash_flow"); revenue_value = float(revenue["value"]); operating_value = float(operating["value"])
        if ticker in {"LULU", "ULTA"}:
            capex = normalizer.ttm_flow("capital_expenditures"); capex_value = float(capex["value"]); interest = None; current_cash = operating_value - capex_value; annual_cash, annual_revenue, annual_sources = _annual_owner_cash(normalizer)
        elif ticker == "DASH":
            ppe = normalizer.ttm_flow("capital_expenditures"); software = normalizer.ttm_flow("software_development"); capex = {"field": "total_reinvestment", "value": float(ppe["value"])+float(software["value"]), "period_end": policy.period, "sources": list(ppe["sources"])+list(software["sources"]), "components": {"ppe": ppe, "software": software}}; capex_value = float(capex["value"]); interest = None; current_cash = operating_value-capex_value; annual_cash, annual_revenue, annual_sources = _dash_owner_cash(normalizer)
        elif ticker == "ABNB":
            capex = None; capex_value = policy.capex_range[1]; interest = normalizer.ttm_flow("interest_expense"); tax_rate = _normalized_tax_rate(normalizer)[0]; current_cash = operating_value - capex_value - abs(float(interest["value"])) * (1-tax_rate); profile = _ocf_history(normalizer, ttm_revenue=revenue_value, ttm_ocf=operating_value, ttm_period=policy.period, ttm_sources=revenue.get("sources", []) + operating.get("sources", [])); annual_sources = (); annual_cash = annual_revenue = ()
        elif ticker == "NCLH":
            capex = normalizer.ttm_flow("capital_expenditures"); interest = normalizer.ttm_flow("interest_expense"); capex_value = float(capex["value"]); tax_rate = _normalized_tax_rate(normalizer)[0] if True else .21; current_cash = cash_fcff_from_reported(operating_cash_flow=operating_value, capital_expenditures=capex_value, spectrum_investment=0., interest_expense=abs(float(interest["value"])), tax_rate=tax_rate); annual_cash, annual_revenue, annual_sources = _annual_cash_with_losses(normalizer)
        else:
            capex = normalizer.ttm_flow("capital_expenditures"); interest = normalizer.ttm_flow("interest_expense"); capex_value = float(capex["value"]); tax_rate = _normalized_tax_rate(normalizer)[0]; current_cash = cash_fcff_from_reported(operating_cash_flow=operating_value, capital_expenditures=capex_value, spectrum_investment=0., interest_expense=abs(float(interest["value"])), tax_rate=tax_rate); annual_cash, annual_revenue, annual_sources = _annual_cash_fcff(normalizer, spectrum_required=False, spectrum_floor=0., spectrum_source={}, scope_adjustment=0.)
        if ticker != "ABNB":
            ttm_sources = []
            for flow in (revenue, operating, capex, interest or {}):
                if isinstance(flow, dict): ttm_sources.extend(dict(row) for row in flow.get("sources", []) if isinstance(row, dict))
            profile = build_cash_fcff_history_profile(annual_cash_states=annual_sources, ttm_revenue=revenue_value, ttm_cash_fcff=current_cash, ttm_period_end=policy.period, ttm_sources=ttm_sources, valuation_date=BATCH_08_VALUATION_DATE)
        cash_metric = profile.metric("cash_conversion_margin"); growth_metric = profile.metric("revenue_growth")
        if cash_metric is None or growth_metric is None:
            raise ValueError(f"{ticker}: history metrics missing")
        margins = (cash_metric.low, cash_metric.base, cash_metric.high); growth = tuple(max(-.10, min(.20, value)) for value in (growth_metric.low, growth_metric.base, growth_metric.high))
        if ticker == "NCLH": margins = (.001, .167, .20); growth = (-.05, .03, .07)
        if ticker == "ABNB":
            tax_rate = _normalized_tax_rate(normalizer)[0]; interest_adjustment = abs(float(interest["value"])) * (1-tax_rate); margins = tuple(max(.001, margin-(policy.capex_range[index]+interest_adjustment)/revenue_value) for index, margin in enumerate(margins))
        if ticker == "KDP":
            revenue_value = 28_258_000_000.; growth = (0., .03, .06)
        margins = tuple(max(.001, margin-policy.margin_stress[index]) for index, margin in enumerate(margins))
        flow_sources = {"revenue": revenue, "operating_cash_flow": operating, "capital_expenditures": capex, "interest_expense": interest}
    rows = []
    for index, name in enumerate(("bear", "base", "bull")):
        cash_value = policy.cash_range[index] if policy.cash_range else policy.cash
        raw = five_year_fcff_dcf(revenue=revenue_value, fcff_margin=margins[index], growth=growth[index], wacc=policy.wacc[index], terminal_growth=policy.terminal_growth[index], cash_and_investments=cash_value, debt=policy.debt, noncontrolling_interests=policy.nci[index], shares=policy.shares[index]); value = max(0., float(raw["value_per_share"])); rows.append({"name": name, "conditional_value_per_share": value, "raw_value_per_share": float(raw["value_per_share"]), "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": policy.wacc[index], "terminal_growth": policy.terminal_growth[index], "shares": policy.shares[index], "limited_liability_floor_applied": value == 0 and float(raw["value_per_share"]) < 0})
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    is_pass = ticker in PASS_TICKERS
    if not (0 <= scenario["low"] <= scenario["base"] <= scenario["high"]): raise ValueError(f"{ticker}: range invalid")
    if scenario["base"] <= 0 and not (not is_pass and scenario["low"] == scenario["base"] == 0 and scenario["high"] > 0): raise ValueError(f"{ticker}: positive base or conditional equity-at-risk range required")
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"); reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons)
    public_history = profile.public_metadata()
    if not is_pass: public_history.update({"normalization_basis": "company_history_with_material_event_override", "assumption_source_mix": "reported_history_and_finsight_policy"})
    assumptions = {**public_history, "cash_conversion_margin": margins, "growth": growth, "wacc": policy.wacc, "terminal_growth": policy.terminal_growth, "shares": policy.shares, "cash_and_investments_range": policy.cash_range or (policy.cash,)*3, "capex_range": policy.capex_range, "equity_floor_basis": "limited-liability floor after negative residual" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator is calibrated to the published base; private history and bridge remain fixed.", "invalidation": policy.invalidation}
    key = (BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked history supplies ordinary cash-conversion and growth states, with event overrides identified separately."), BaselineAssumption("reported anchors", str({"revenue": revenue_value, "operating_cash_flow": operating_value, "capex": capex_value}), AssumptionClassification.REPORTED, "Cutoff-safe filing facts anchor current cash generation."), BaselineAssumption("scenario policy", str(assumptions), AssumptionClassification.FINSIGHT_ASSUMPTION, "Discount rates, terminal growth, share sensitivity, and named fallback ranges are transparent FinSight assumptions."))
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_08_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=key, warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_08_HISTORY_VERSION, "availability_type": baseline.availability_type.value, "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"revenue_anchor": revenue_value, "ttm_operating_cash_flow": operating_value, "ttm_capex": capex_value}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flow_sources, "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge_sources(ticker, structural, policy), "bridge_reconciliation": {"cash_and_investments_range": policy.cash_range or (policy.cash,)*3, "debt_and_finance_leases": policy.debt, "nci_or_event_claim_range": policy.nci, "operating_liability_treatment": "Operating customer, loyalty, and contract liabilities remain inside cash conversion and are not subtracted again."}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


if set(P) | set(EARNINGS) != set(BATCH_08_TICKERS):
    raise RuntimeError("Batch 08 policy denominator mismatch")
