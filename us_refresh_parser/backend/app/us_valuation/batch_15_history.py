"""History-backed practical baselines for controlled Universe Reset Batch 15."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point
from .batch_05_launch_first import _companyfacts_duration, _source_proven_no_debt
from .batch_06_launch_first import _annual_owner_cash
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _dimension_fact, _no_preferred
from .batch_15 import BATCH_15_TICKERS, BATCH_15_VALUATION_DATE
from .equity_fact_selection import annual_facts
from .history import (
    HISTORY_POLICY_VERSION,
    CompanyHistoryProfile,
    HistoryObservation,
    build_cash_fcff_history_profile,
    summarize_history_metric,
)
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_15_HISTORY_VERSION = "BATCH-15-HEALTH-CARE-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"DVA", "HSIC", "DGX", "MTD"})
OWNER_CASH_TICKERS = frozenset({"ISRG", "ALGN"})
CONDITIONAL_TICKERS = frozenset({"RMD", "WAT", "CNC"})
WITHHELD_TICKERS = frozenset({"LH", "ISRG", "ALGN"})


def _share_range(weighted: float, current: float) -> tuple[float, float, float]:
    return (weighted, (weighted + current) / 2., current)


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: tuple[float, float, float]
    claims: tuple[float, float, float]
    shares: tuple[float, float, float]
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str
    claim_formula: str


P = {
    "LH": Policy(
        "diagnostics_laboratory_faded_fcff", "2026-06-30", 141_800_000.,
        (5_924_800_000.,) * 3, (111_900_000.,) * 3,
        _share_range(82_400_000., 81_100_000.), (-.02, .03, .06), (.105, .09, .08), (.01, .02, .025),
        "Source-bounded diagnostics-laboratory baseline. Recent acquisitions, contingent consideration, finance leases, and redeemable NCI are included once; ordinary legal and operating-lease exposures remain in cash conversion.",
        "Invalidate if laboratory cash conversion, DOJ/legal exposure, acquisitions, debt/leases, NCI, contingent consideration, or diluted shares changes materially.",
        "$95.5M reported contingent consideration plus $16.4M redeemable NCI; finance leases are included with debt.",
    ),
    "DVA": Policy(
        "dialysis_provider_faded_fcff", "2026-06-30", 727_242_000.,
        (10_781_013_000.,) * 3, (1_883_997_000.,) * 3,
        _share_range(67_476_000., 63_800_000.), (-.02, .02, .05), (.11, .095, .085), (.01, .02, .025),
        "Source-bounded dialysis-provider baseline. Debt/capital leases, acquisition obligations, marketable securities, redeemable NCI, nonredeemable NCI, and current shares reconcile explicitly; the historical range retains the 2025 cyber-related collection disruption and current recovery rather than hiding it.",
        "Invalidate if treatment volumes, reimbursement, debt/leases, redeemable NCI, minority ownership, or diluted shares changes materially.",
        "$1.561416B redeemable NCI plus $0.283118B nonredeemable NCI plus $39.463M acquisition obligations/other notes payable; operating leases remain post-rent operating items.",
    ),
    "RMD": Policy(
        "post_matrixcare_sleep_health_faded_fcff", "2026-06-30", 1_469_234_000.,
        (659_365_000.,) * 3, (35_000_000., 18_000_000., 1_000_000.),
        _share_range(146_054_000., 144_252_306.), (0., .04, .07), (.105, .09, .08), (.01, .02, .025),
        "Conditional Low sleep-health estimate. MatrixCare is held for sale, current acquisitions and disposal accounting affect comparability, and the $490M disposal consideration is not credited before closing.",
        "Invalidate if MatrixCare closes, terminates, or changes; or if acquisition cash, litigation exposure, debt, or diluted shares changes materially.",
        "Bear reserves the reported $34M possible legal loss plus $1M accrual; base reserves $18M; bull reserves the $1M accrual. MatrixCare proceeds are excluded until realized.",
    ),
    "HSIC": Policy(
        "dental_medical_distribution_faded_fcff", "2026-06-27", 157_000_000.,
        (3_462_000_000.,) * 3, (1_624_000_000.,) * 3,
        _share_range(115_238_506., 111_446_542.), (-.02, .02, .05), (.11, .095, .085), (.01, .02, .025),
        "Source-bounded health-care distribution baseline. Short-term borrowings, debt/finance leases, temporary equity, nonredeemable NCI, and contingent consideration are separated explicitly.",
        "Invalidate if distribution cash conversion, borrowing scope, temporary equity/NCI, contingent consideration, restructuring, or diluted shares changes materially.",
        "$906M temporary/redeemable equity plus $660M nonredeemable NCI plus $58M contingent consideration; current and long-term financing are counted once.",
    ),
    "WAT": Policy(
        "post_bds_life_sciences_faded_fcff", "2026-07-04", 539_000_000.,
        (5_086_000_000.,) * 3, (0.,) * 3,
        (100_704_314., 98_248_111., 95_791_908.), (-.02, .01, .04), (.12, .105, .095), (0., .01, .02),
        "Conditional Low post-BDS life-sciences estimate. The $13B combination, 38.542M issued shares, assumed debt, acquisition accounting, and only a partial combined cash period materially limit predictability.",
        "Invalidate if BDS pro-forma revenue, combined cash conversion, acquisition accounting, debt, restructuring, or cover shares changes materially.",
        "No additional common-equity claim is invented. Current reported debt includes the $4B assumed debt; the reliable 98.248M cover shares replace the structurally mis-scaled weighted-share tag.",
    ),
    "DGX": Policy(
        "diagnostics_laboratory_faded_fcff", "2026-06-30", 626_000_000.,
        (5_642_000_000.,) * 3, (483_000_000.,) * 3,
        _share_range(112_000_000., 110_373_360.), (-.01, .03, .06), (.105, .09, .08), (.01, .02, .025),
        "Source-bounded diagnostics-laboratory baseline. Current debt, NCI, redeemable NCI, contingent consideration, and malpractice/legal reserves are captured without substituting stale claims.",
        "Invalidate if laboratory cash conversion, malpractice/legal reserves, acquisitions, debt, NCI, or diluted shares changes materially.",
        "$303M NCI + $80M redeemable NCI + $100M contingent consideration. The $174M malpractice and $17M litigation reserves remain recorded operating liabilities and are not deducted again.",
    ),
    "ISRG": Policy(
        "debt_free_robotic_surgery_owner_cash", "2026-06-30", 8_625_500_000.,
        (0.,) * 3, (129_300_000.,) * 3,
        _share_range(358_500_000., 353_278_038.), (.02, .07, .10), (.105, .09, .08), (.01, .02, .025),
        "Source-bounded robotic-surgery owner-cash baseline. No interest addback is used; cash, the complete securities total, source-proven debt absence, NCI, and shares reconcile.",
        "Invalidate if system/procedure growth, reinvestment, securities, debt absence, NCI, acquisitions, or diluted shares changes materially.",
        "$129.3M reported NCI is deducted once; no debt is deducted because current source evidence proves no interest-bearing debt balance.",
    ),
    "MTD": Policy(
        "precision_instruments_faded_fcff", "2026-06-30", 51_383_000.,
        (2_111_963_000.,) * 3, (0.,) * 3,
        _share_range(20_251_532., 20_036_559.), (0., .04, .07), (.105, .09, .08), (.01, .02, .025),
        "Source-bounded precision-instruments baseline. Current debt, cash, shares, small acquisition payments, and restructuring are traceable across stable annual cash history.",
        "Invalidate if instrument demand, cash conversion, debt, acquisitions, restructuring, or diluted shares changes materially.",
        "No reported current preferred or noncontrolling equity claim; debt is deducted once using the current combined amount.",
    ),
    "ALGN": Policy(
        "dental_technology_owner_cash", "2026-06-30", 1_102_591_000.,
        (300_000_000., 150_000_000., 0.), (69_314_000., 53_414_000., 37_514_000.),
        _share_range(71_629_000., 71_039_852.), (0., .04, .07), (.11, .095, .085), (.01, .02, .025),
        "Source-bounded dental-technology owner-cash baseline. No interest addback or invented zero debt is used; unused credit capacity and current legal/VAT exposures are conservatively ranged.",
        "Invalidate if owner cash, facility borrowing, legal/VAT exposure, investments, restructuring, or diluted shares changes materially.",
        "Bear/base/bull reserve $300M/$150M/$0 of disclosed revolving capacity plus $31.8M legal accrual and $37.514M/$21.614M/$5.714M residual VAT/legal sensitivity without double-counting reported expenses.",
    ),
}


POINT_SPECS = {
    "LH": (("CashAndCashEquivalentsAtCarryingValue", 141_800_000.), ("LongTermDebtCurrent", 900_000.), ("LongTermDebtNoncurrent", 5_857_600_000.), ("FinanceLeaseLiabilityCurrent", 4_700_000.), ("FinanceLeaseLiabilityNoncurrent", 61_600_000.), ("BusinessCombinationContingentConsiderationLiability", 95_500_000.), ("NoncontrollingInterestMezzanineEquity", 16_400_000.)),
    "DVA": (("CashAndCashEquivalentsAtCarryingValue", 668_963_000.), ("MarketableSecurities", 58_279_000.), ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities", 10_781_013_000.), ("MinorityInterest", 283_118_000.), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 1_561_416_000.), ("PreferredStockValue", 0.)),
    "RMD": (("CashAndCashEquivalentsAtCarryingValue", 1_469_234_000.), ("DebtLongtermAndShorttermCombinedAmount", 659_365_000.), ("PreferredStockValue", 0.), ("AssetsOfDisposalGroupIncludingDiscontinuedOperation", 457_386_000.), ("LiabilitiesOfDisposalGroupIncludingDiscontinuedOperationCurrent", 41_156_000.)),
    "HSIC": (("CashCashEquivalentsAndShortTermInvestments", 157_000_000.), ("LongTermDebtAndFinanceLeaseObligationsIncludingCurrentMaturities", 2_438_000_000.), ("ShortTermBorrowings", 1_024_000_000.), ("TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests", 906_000_000.), ("MinorityInterest", 660_000_000.), ("BusinessCombinationContingentConsiderationLiability", 58_000_000.), ("PreferredStockValueOutstanding", 0.)),
    "WAT": (("CashAndCashEquivalentsAtCarryingValue", 539_000_000.), ("DebtAndCapitalLeaseObligations", 5_086_000_000.), ("DebtAssumedInBusinessCombination", 4_000_000_000.), ("EntityCommonStockSharesOutstanding", 98_248_111.), ("PreferredStockValue", 0.)),
    "DGX": (("CashAndCashEquivalentsAtCarryingValue", 626_000_000.), ("LongTermDebtCurrent", 10_000_000.), ("LongTermDebtNoncurrent", 5_632_000_000.), ("MinorityInterest", 303_000_000.), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 80_000_000.), ("BusinessCombinationContingentConsiderationLiability", 100_000_000.)),
    "ISRG": (("CashandCashEquivalentsandDebtSecuritiesAvailableforsaleFairValue", 8_625_500_000.), ("MinorityInterest", 129_300_000.), ("PreferredStockValue", 0.)),
    "MTD": (("CashAndCashEquivalentsAtCarryingValue", 51_383_000.), ("DebtLongtermAndShorttermCombinedAmount", 2_111_963_000.), ("PreferredStockValue", 0.)),
    "ALGN": (("CashAndCashEquivalentsAtCarryingValue", 1_102_591_000.), ("UKVATLossContingency", 37_514_000.), ("PreferredStockValue", 0.)),
}


SHARE_STARTS = {
    "LH": "2026-01-01", "DVA": "2026-01-01", "RMD": "2025-07-01", "HSIC": "2025-12-28",
    "DGX": "2026-01-01", "ISRG": "2026-01-01", "MTD": "2026-01-01", "ALGN": "2026-01-01",
}


def _history_source(fact: Any) -> dict[str, Any]:
    return {"concept": fact.concept, "value": fact.value, "unit": fact.unit, "period_start": fact.period_start, "period_end": fact.period_end, "filed_date": fact.filed_date, "accession": fact.accession, "form": fact.form, "fiscal_year": fact.fiscal_year}


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [_point(structural, name=name, expected=value, period_end=policy.period if name != "EntityCommonStockSharesOutstanding" else "2026-08-07") for name, value in POINT_SPECS[ticker]]
    if ticker != "WAT":
        rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=policy.shares[0], period_start=SHARE_STARTS[ticker], period_end=policy.period))
    else:
        rows.extend((
            _dimension_fact(structural, name="BusinessAcquisitionEquityInterestsIssuedOrIssuableNumberOfSharesIssued", expected=38_542_000., start="2026-01-01", end=policy.period, member="BDSBusinessMember"),
            _dimension_fact(structural, name="BusinessCombinationConsiderationTransferred1", expected=13_000_000_000., start="2026-02-09", end="2026-02-09", member="BDSBusinessMember"),
            _dimension_fact(structural, name="BusinessAcquisitionsProFormaRevenue", expected=1_300_000_000., start="2026-01-01", end=policy.period, member="BDSBusinessMember"),
            _structural_flow(structural, name="RevenueFromContractWithCustomerExcludingAssessedTax", start="2026-01-01", end=policy.period, expected=2_912_000_000.),
            _structural_flow(structural, name="NetCashProvidedByUsedInOperatingActivities", start="2026-01-01", end=policy.period, expected=198_000_000.),
            _structural_flow(structural, name="PaymentsToAcquireProductiveAssets", start="2026-01-01", end=policy.period, expected=87_000_000.),
            _structural_flow(structural, name="BusinessAcquisitionsProFormaRevenue", start="2026-01-01", end=policy.period, expected=3_185_000_000.),
            _structural_flow(structural, name="BusinessAcquisitionsProFormaNetIncomeLoss", start="2026-01-01", end=policy.period, expected=-201_000_000.),
        ))
    if ticker == "DVA":
        rows.append(_dimension_fact(structural, name="AcquisitionObligationsAndOtherNotesPayable", expected=39_463_000., start=None, end=policy.period, member="NotesPayableOtherPayablesMember"))
    if ticker == "ISRG":
        rows.append(_source_proven_no_debt(structural, period_end=policy.period))
    if ticker == "MTD":
        rows.extend((
            _dimension_fact(structural, name="CommonStockSharesOutstanding", expected=20_036_559., start=None, end=policy.period, member="CommonStockMember"),
            _point(structural, name="CommonStockSharesOutstanding", expected=21_683_802., period_end=policy.period),
        ))
    if ticker in {"LH", "RMD", "MTD"}:
        rows.append(_no_preferred(structural, policy.period))
    return rows


def _cash_result(*, ticker: str, filing: dict[str, Any], structural: dict[str, Any], submissions: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    policy = P[ticker]
    normalizer = _normalizer(submissions, facts)
    flows = {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow", "capital_expenditures")}
    interest = None
    tax_sources: list[dict[str, Any]] = []
    if ticker in OWNER_CASH_TICKERS:
        current_cash = float(flows["operating_cash_flow"]["value"]) - float(flows["capital_expenditures"]["value"])
        annual = _annual_owner_cash(normalizer)[2]
    else:
        interest = normalizer.ttm_flow("interest_expense")
        try:
            tax_rate, tax_rows = _normalized_tax_rate(normalizer)
            tax_sources = list(tax_rows)
        except ValueError:
            tax_rate = .21
        if tax_rate < .05:
            tax_rate = .21
        current_cash = cash_fcff_from_reported(
            operating_cash_flow=float(flows["operating_cash_flow"]["value"]),
            capital_expenditures=float(flows["capital_expenditures"]["value"]),
            spectrum_investment=0., interest_expense=abs(float(interest["value"])), tax_rate=tax_rate,
        )
        annual = _annual_cash_with_losses(normalizer)[2]
    ttm_sources = [dict(row) for flow in (*flows.values(), interest or {}) if isinstance(flow, dict) for row in flow.get("sources", []) if isinstance(row, dict)]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=current_cash, ttm_period_end=policy.period, ttm_sources=ttm_sources, valuation_date=BATCH_15_VALUATION_DATE)
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None:
        raise ValueError(f"{ticker}: history insufficient")
    margins = tuple(max(.001, value) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (
        max(-.03, min(.04, growth_metric.low)),
        max(0., min(.06, growth_metric.base)),
        max(.02, min(.09, growth_metric.high)),
    )
    valuation_revenue = revenue
    exclusions: list[str] = []
    if ticker == "WAT":
        valuation_revenue = 6_370_000_000.
        margins = (111_000_000. / 2_912_000_000., .08, .12)
        growth = policy.growth
        exclusions.append("Ordinary historical margins are overridden because the February BDS acquisition changed scale. Valuation revenue is 2 × the source-reported $3.185B H1 pro-forma revenue. Bear cash conversion is the reported combined H1 owner-cash ratio ($198M OCF less $87M productive-asset spend, divided by $2.912B reported revenue); base/bull remain below the 17.87% lowest comparable pre-combination annual cash margin, while the reported $201M pro-forma net loss prevents a higher assumption.")
    rows: list[dict[str, Any]] = []
    traces: dict[str, Any] = {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(
            cash_fcff=valuation_revenue * margins[index], initial_growth=growth[index], terminal_growth=policy.terminal[index],
            wacc=policy.wacc[index], cash_and_investments=policy.cash, interest_bearing_debt=policy.debt[index],
            preferred_equity=0., noncontrolling_interests=policy.claims[index], diluted_shares=policy.shares[index],
        )
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "conditional_value_per_share": max(0., raw), "raw_value_per_share": raw, "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": policy.wacc[index], "terminal_growth": policy.terminal[index], "cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt[index], "other_equity_claims": policy.claims[index], "shares": policy.shares[index], "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: invalid scenario range")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons)
    public_history = profile.public_metadata()
    if exclusions or not is_pass:
        public_history.update({"normalization_basis": "company_history_with_material_event_override", "assumption_source_mix": "reported_history_and_finsight_policy"})
    assumptions = {**public_history, "forecast_years": FORECAST_YEARS, "cash_conversion_margin": margins, "growth": growth, "wacc": policy.wacc, "terminal_growth": policy.terminal, "cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "shares": policy.shares, "normalization_exclusions": tuple(exclusions), "equity_floor_basis": "limited-liability floor after negative bear residual" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator is calibrated to the faded-cash base; private source, bridge, and event schedules remain fixed.", "invalidation": policy.invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_15_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and comparable current cash history supplies the ordinary cash-conversion range."), BaselineAssumption("faded operating states", str({"growth": growth, "wacc": policy.wacc, "terminal": policy.terminal}), AssumptionClassification.FINSIGHT_ASSUMPTION, "Growth fades over eight years to a terminal rate no higher than 2.5%.")), warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_15_HISTORY_VERSION, "availability_type": "available" if is_pass else "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "valuation_revenue": valuation_revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_capex": flows["capital_expenditures"]["value"], "ttm_interest": None if interest is None else interest["value"], "ttm_cash_fcff_or_owner_cash": current_cash}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": {**flows, "interest_expense": interest}, "tax_rate_sources": tax_sources, "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge(ticker, structural, policy), "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "other_equity_claim_formula": policy.claim_formula, "shares": policy.shares, "history_normalization_exclusions": exclusions, "history_sensitivity": "The source history retains the 2025 cyber-related collection disruption and current recovery." if ticker == "DVA" else None, "share_reconciliation": "The 20.036559M cover count and dimensioned common-stock count agree exactly. The conflicting unqualified 21.683802M tag is retained as extraction evidence but excluded; H1 diluted weighted shares of 20.251532M provide the conservative bear denominator." if ticker == "MTD" else None, "owner_cash_treatment": "OCF minus capex; no interest addback and no fabricated zero interest." if ticker in OWNER_CASH_TICKERS else None, "operating_liability_treatment": "Operating leases and ordinary operating/legal reserves already represented in cash conversion are not subtracted again."}, "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


def _lh_withheld(*, filing: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    warning = "Withheld. Labcorp signed a DOJ settlement on 2026-07-15, but the controlling filing provides no amount, reserve, payment schedule, or defensible upper bound; subtracting zero would invent certainty."
    invalidation = "Release only after the DOJ settlement amount or a source-supported finite bound is available, or reliable evidence proves it immaterial to common equity."
    baseline = BaselineValuation(ticker="LH", method="unavailable_unbounded_doj_settlement_claim", method_version=BATCH_15_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(warning, invalidation))
    policy = P["LH"]
    return {"ticker": "LH", "method": baseline.method, "model_version": BATCH_15_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {}, "governed_assumptions": {"history_policy_version": HISTORY_POLICY_VERSION, "history_years_used": 0, "normalization_basis": "material_unbounded_doj_settlement_claim", "assumption_source_mix": "reported_settlement_event_without_reported_amount", "invalidation": invalidation}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "bridge_sources": _bridge("LH", structural, policy), "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "known_other_equity_claims": policy.claims, "shares": policy.shares, "unbounded_claim": "DOJ settlement agreement dated 2026-07-15; no amount, reserve, payment, or upper bound in the controlling filing."}, "release_condition": invalidation, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _claims_withheld(*, ticker: str, filing: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    policy = P[ticker]
    if ticker == "ISRG":
        claim = "Current product-liability disclosures say claims may exceed accruals and no excess-loss range can be estimated."
        release = "Release only after product-liability exposure has a source-supported finite bound demonstrably immaterial to common equity, or is included once in a conservative range."
        warning = "Withheld. Intuitive Surgical's operating cash and debt-free bridge are usable, but current product-liability exposure may exceed accruals and the filing cannot estimate the excess-loss range."
    else:
        claim = "Current legal/IP proceedings and the EU competition investigation cannot be ranged; adverse outcomes may include substantial fines and follow-on litigation."
        release = "Release only after legal/IP and EU competition exposures have source-supported finite bounds, and the material private-investment and borrowing-capacity bridge is resolved once."
        warning = "Withheld. Align's owner cash is usable, but current legal/IP proceedings and the EU competition investigation have no estimable loss range and may produce substantial fines or follow-on claims."
    method = "unavailable_unbounded_product_liability_claims" if ticker == "ISRG" else "unavailable_unbounded_legal_competition_claims"
    baseline = BaselineValuation(ticker=ticker, method=method, method_version=BATCH_15_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(warning, release))
    return {"ticker": ticker, "method": method, "model_version": BATCH_15_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {}, "governed_assumptions": {"history_policy_version": HISTORY_POLICY_VERSION, "history_years_used": 0, "normalization_basis": "material_unbounded_claims", "assumption_source_mix": "reported_current_claim_disclosure_without_estimable_range", "invalidation": release}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "bridge_sources": _bridge(ticker, structural, policy), "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "known_other_equity_claims": policy.claims, "shares": policy.shares, "unbounded_claim": claim, "known_model_correction": "ISRG cash/securities uses the $8.6255B aggregate fair-value fact, avoiding a $357M overlap." if ticker == "ISRG" else "Unused $300M revolving capacity is not treated as debt; any later recovery must separately reconcile $327.8M private investments."}, "release_condition": release, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _cnc_result(*, filing: dict[str, Any], structural: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    gaap = facts["facts"]["us-gaap"]
    net = annual_facts(gaap, concepts=("NetIncomeLoss",), unit="USD", valuation_date=BATCH_15_VALUATION_DATE)
    nci = annual_facts(gaap, concepts=("NetIncomeLossAttributableToNoncontrollingInterest",), unit="USD", valuation_date=BATCH_15_VALUATION_DATE)
    observations: list[HistoryObservation] = []
    for year in (2021, 2022, 2023, 2024):
        fact = net[year]
        nci_fact = nci.get(year)
        value = float(fact.value) - (float(nci_fact.value) if nci_fact else 0.)
        sources = (_history_source(fact),) + ((_history_source(nci_fact),) if nci_fact else ())
        observations.append(HistoryObservation("annual", fact.period_end, fact.fiscal_year, value, "USD", "reported parent-attributable earnings", sources))
    current_net = _structural_flow(structural, name="NetIncomeLoss", start="2026-01-01", end="2026-06-30", expected=2_632_000_000.)
    current_nci = _structural_flow(structural, name="NetIncomeLossAttributableToNoncontrollingInterest", start="2026-01-01", end="2026-06-30", expected=-6_000_000.)
    impairment_2025 = _companyfacts_duration(facts, concept="GoodwillImpairmentLoss", accession="0001071739-26-000049", start="2025-07-01", end="2025-09-30", expected=6_723_000_000.)
    normalized_2025 = float(net[2025].value) - float(nci[2025].value) + impairment_2025["value"]
    observations.append(HistoryObservation("annual", "2025-12-31", 2025, normalized_2025, "USD", "reported parent loss plus source-reported noncash goodwill impairment", (_history_source(net[2025]), _history_source(nci[2025]), impairment_2025)))
    current_pretax = _structural_flow(structural, name="IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", start="2026-01-01", end="2026-06-30", expected=3_585_000_000.)
    current_tax = _structural_flow(structural, name="IncomeTaxExpenseBenefit", start="2026-01-01", end="2026-06-30", expected=959_000_000.)
    risk_adjustment = _structural_flow(structural, name="AffordableCareActRiskAdjustmentPreTaxExpenseBenefit", start="2026-01-01", end="2026-06-30", expected=-481_000_000.)
    current_tax_rate = current_tax["value"] / current_pretax["value"]
    after_tax_risk_benefit = abs(risk_adjustment["value"]) * (1. - current_tax_rate)
    annualized_current = 2. * (current_net["value"] - current_nci["value"] - after_tax_risk_benefit)
    observations.append(HistoryObservation("operating_ttm", "2026-06-30", None, annualized_current, "USD", "2 × (reported H1 parent earnings less the after-tax $481M favorable prior-year risk-adjustment item)", (current_net, current_nci, current_pretax, current_tax, risk_adjustment)))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    if metric is None:
        raise ValueError("CNC: normalized earnings history unavailable")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "managed_care_residual_income", BATCH_15_VALUATION_DATE, tuple(row.period_end for row in observations if row.period_role == "annual"), (metric,), True, "reported_and_company_history")
    beginning_equity, ending_equity = 19_953_000_000., 22_562_000_000.
    average_equity = (beginning_equity + ending_equity) / 2.
    shares = (496_605_000., (496_605_000. + 493_995_000.) / 2., 493_995_000.)
    earnings = (metric.low, metric.base, metric.high)
    cost_of_equity, terminal_roe, terminal_growth = (.12, .10, .085), (.06, .10, .14), (.01, .02, .025)
    rows: list[dict[str, Any]] = []
    traces: dict[str, Any] = {}
    multiples: list[float] = []
    for index, name in enumerate(("bear", "base", "bull")):
        trace = residual_income_valuation(book_value_per_share=ending_equity / shares[index], current_roe=earnings[index] / average_equity, cost_of_equity=cost_of_equity[index], current_payout_ratio=0., terminal_roe=terminal_roe[index], terminal_growth=terminal_growth[index], years=5)
        raw = float(trace["intrinsic_value"])
        multiple = raw * shares[index] / earnings[index]
        multiples.append(multiple)
        traces[name] = trace
        rows.append({"name": name, "conditional_value_per_share": raw, "raw_value_per_share": raw, "normalized_common_earnings": earnings[index], "book_value_per_share": ending_equity / shares[index], "current_roe": earnings[index] / average_equity, "current_payout_ratio": 0., "cost_of_equity": cost_of_equity[index], "terminal_roe": terminal_roe[index], "terminal_growth": terminal_growth[index], "earnings_multiple": multiple, "shares": shares[index], "limited_liability_floor_applied": False})
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError("CNC: invalid range")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"))
    warning = "Conditional Low managed-care residual-income estimate. Medical claims, regulated capital, risk adjustment, the 2025 loss year, and Magellan held-for-sale treatment make normalized common earnings materially uncertain."
    invalidation = "Invalidate if normalized common earnings/equity, medical claims, regulated capital, risk adjustment, Magellan disposal, NCI, or shares changes materially."
    assumptions = {**profile.public_metadata(), "normalization_basis": "reported_common_equity_and_normalized_earnings_history", "assumption_source_mix": "reported_common_equity_earnings_and_finsight_policy", "normalized_common_earnings": earnings, "earnings_multiples": tuple(multiples), "shares": shares, "book_equity": ending_equity, "average_common_equity": average_equity, "cost_of_equity": cost_of_equity, "terminal_roe": terminal_roe, "terminal_growth": terminal_growth, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "normalization_adjustments": ("2025 parent earnings add back the source-reported $6.723B noncash goodwill impairment, leaving $52M residual normalized earnings.", "Current annualized H1 earnings remove the after-tax effect of the source-reported $481M favorable prior-year risk-adjustment item; the broad Low range also covers the absence of a current Medicare Advantage premium-deficiency reserve."), "calculator_calibration": "Calculator varies normalized common earnings and the residual-income-implied multiple around the published base.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker="CNC", method="managed_care_residual_income_normalized_equity_earnings", method_version=BATCH_15_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", ending_equity, AssumptionClassification.REPORTED, "Current common equity supplies the residual-income opening anchor."), BaselineAssumption("normalized earnings history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Four ordinary annual periods plus current annualized H1 parent earnings supply the transparent range."), BaselineAssumption("managed-care residual-income policy", str({"cost_of_equity": cost_of_equity, "terminal_roe": terminal_roe}), AssumptionClassification.FINSIGHT_ASSUMPTION, "Claims and regulated capital remain inside common earnings and equity; no EV debt bridge is applied.")), warnings=(warning, invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link="/api/us-valuations/CNC/calculator")
    context = [
        _point(structural, name="StockholdersEquity", expected=beginning_equity, period_end="2025-12-31"),
        _point(structural, name="StockholdersEquity", expected=ending_equity, period_end="2026-06-30"),
        _point(structural, name="LiabilityForClaimsAndClaimsAdjustmentExpense", expected=20_262_000_000., period_end="2026-06-30"),
        _point(structural, name="DebtAndCapitalLeaseObligations", expected=16_105_000_000., period_end="2026-06-30"),
        _point(structural, name="RedeemableNoncontrollingInterestEquityCarryingAmount", expected=23_000_000., period_end="2026-06-30"),
        _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=496_605_000., period_start="2026-01-01", period_end="2026-06-30"),
    ]
    return {"ticker": "CNC", "method": baseline.method, "model_version": BATCH_15_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"annualized_current_parent_earnings": annualized_current, "beginning_common_equity": beginning_equity, "ending_common_equity": ending_equity, "reported_2025_net_loss": net[2025].value, "normalized_2025_parent_earnings": normalized_2025, "h1_risk_adjustment_pre_tax_benefit": abs(risk_adjustment["value"])}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "company_history_profile": profile.as_private_dict(), "equity_model_context": context, "residual_income_trace": {"states": traces}, "bridge_treatment": "Equity-level managed-care model: medical claims, member funds, debt, investments, regulated capital, and NCI remain inside parent earnings/common equity. No EV debt bridge and no claims-liability double count.", "normalization_sources": {"reported_2025_net_loss": _history_source(net[2025]), "goodwill_impairment": impairment_2025, "current_pretax": current_pretax, "current_tax": current_tax, "risk_adjustment": risk_adjustment, "current_tax_rate": current_tax_rate, "after_tax_risk_benefit": after_tax_risk_benefit}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_15_history_result(*, ticker: str, source_root: Path, structural_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_15_TICKERS:
        raise ValueError(f"unexpected Batch 15 ticker {ticker}")
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural["source_accession"] != filing["accession"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    if ticker == "LH":
        return _lh_withheld(filing=filing, structural=structural)
    if ticker in {"ISRG", "ALGN"}:
        return _claims_withheld(ticker=ticker, filing=filing, structural=structural)
    if ticker == "CNC":
        return _cnc_result(filing=filing, structural=structural, facts=facts)
    if filing["period_end"] != P[ticker].period:
        raise ValueError(f"{ticker}: controlling period mismatch")
    return _cash_result(ticker=ticker, filing=filing, structural=structural, submissions=submissions, facts=facts)


if set(P) | {"CNC"} != set(BATCH_15_TICKERS):
    raise RuntimeError("Batch 15 denominator mismatch")
