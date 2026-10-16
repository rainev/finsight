"""History-backed launch-first baselines for controlled Batch 07."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .baseline import (
    AssumptionClassification,
    AvailabilityType,
    BaselineAssumption,
    BaselineValuation,
)
from .batch_02_conditional_estimates import five_year_fcff_dcf
from .batch_02_practical_inputs import (
    _annual_cash_fcff,
    _normalizer,
    _normalized_tax_rate,
    cash_fcff_from_reported,
)
from .batch_04_launch_first import (
    _controlling,
    _duration,
    _point,
    _source_proven_no_other_equity_claims,
)
from .batch_05_launch_first import _source_proven_no_debt
from .batch_06_launch_first import _annual_owner_cash
from .batch_07 import BATCH_07_TICKERS, BATCH_07_VALUATION_DATE
from .history import build_cash_fcff_history_profile
from .reliability import assess_reliability


BATCH_07_HISTORY_VERSION = "BATCH-07-HISTORY-LAUNCH-FIRST-1.0"
PASS_TICKERS = frozenset({"EBAY", "TPR", "GRMN", "DPZ"})


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
    development_cash_reserve: tuple[float, float, float] = (0., 0., 0.)
    cash_dependency_reserve: tuple[float, float, float] = (0., 0., 0.)
    cash_range: tuple[float, float, float] | None = None


def _shares(base: float, *, bull: float | None = None) -> tuple[float, float, float]:
    return (base * 1.025, base, bull if bull is not None else base * 0.975)


P = {
    "EL": Policy("brand_turnaround_normalized_cash_fcff", "2026-03-31", 3_126_000_000., 7_312_000_000., (0., 0., 0.), _shares(364_500_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low estimate. Brand turnaround, restructuring and margin recovery remain material even after five-year normalization.", "Invalidate if restructuring, brand cash conversion, debt or diluted shares leave the recorded ranges."),
    "EBAY": Policy("marketplace_normalized_cash_fcff", "2026-06-30", 3_620_000_000., 6_735_000_000., (0., 0., 0.), _shares(457_000_000.), (.105, .09, .08), (0., .015, .02), "History-backed marketplace cash-FCFF estimate. Reported customer accounts are reserved from excess cash and are not bridge-debited again.", "Invalidate if customer-fund classification, debt, investments or diluted shares no longer reconcile."),
    "BKNG": Policy("travel_marketplace_normalized_cash_fcff", "2026-06-30", 12_006_500_000., 20_300_000_000., (0., 0., 0.), _shares(782_000_000.), (.10, .085, .075), (0., .015, .025), "Conditional Low estimate. Deferred merchant bookings mix supplier funds and future margin, so excess cash uses an explicit full/midpoint/restricted-cash reserve range.", "Invalidate if merchant balances, debt, cash, diluted shares or normalized travel cash leave the recorded ranges.", cash_range=(7_093_000_000., 12_006_500_000., 16_920_000_000.)),
    "TPR": Policy("brand_portfolio_normalized_cash_fcff", "2026-06-27", 1_152_000_000., 2_396_600_000., (0., 0., 0.), _shares(210_200_000.), (.105, .09, .08), (0., .015, .02), "History-backed brand-portfolio cash-FCFF estimate. Brand mix and integration costs remain ordinary scenario risks.", "Invalidate if portfolio scope, debt, investments, shares or normalized cash conversion materially changes."),
    "GRMN": Policy("consumer_technology_owner_cash", "2026-06-27", 4_369_870_000., 0., (0., 0., 0.), _shares(193_515_000.), (.10, .085, .075), (0., .015, .025), "History-backed owner-cash estimate. The latest H1 filing is reconstructed directly because SEC Companyfacts had not incorporated it.", "Invalidate if the H1 reconstruction, securities, debt-absence evidence or diluted shares changes."),
    "WYNN": Policy("casino_cycle_normalized_cash_fcff", "2026-06-30", 1_573_353_000., 10_825_466_000., (737_216_000., 368_608_000., 0.), _shares(103_390_000.), (.12, .105, .095), (0., .01, .02), "Conditional Low estimate. Casino cyclicality, development spending and negative book NCI make attribution materially uncertain.", "Invalidate if development capex, property cash conversion, debt or NCI attribution leaves the recorded range."),
    "DPZ": Policy("franchise_normalized_cash_fcff", "2026-06-14", 192_474_000., 4_883_644_000., (0., 0., 0.), _shares(33_566_494.), (.105, .09, .08), (0., .015, .02), "History-backed franchise cash-FCFF estimate. Securitized debt and finance leases are included once in the bridge.", "Invalidate if franchise cash, combined debt and leases, investments or diluted shares changes materially."),
    "LVS": Policy("casino_cycle_normalized_cash_fcff", "2026-06-30", 3_376_000_000., 15_402_000_000., (316_000_000., 316_000_000., 316_000_000.), _shares(663_000_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low estimate. Casino-cycle normalization, Macao concession reinvestment, Singapore expansion and NCI remain material.", "Invalidate if normalized property cash, development commitments, debt, NCI or shares changes materially.", (888_000_000., 444_000_000., 222_000_000.)),
    "TSLA": Policy("auto_energy_capex_normalized_cash_fcff", "2026-06-30", 43_524_000_000., 9_342_000_000., (661_000_000., 661_000_000., 661_000_000.), _shares(3_949_000_000., bull=3_949_000_000.), (.12, .105, .095), (0., .015, .025), "Conditional Low estimate. Product mix, regulatory credits, AI/factory capex and recent share issuance can move value materially.", "Invalidate if capex, regulatory-credit dependence, debt, NCI or current shares leaves the recorded range.", (0., 0., 0.), (1_052_000_000., 526_000_000., 0.)),
    "EXPE": Policy("travel_marketplace_normalized_cash_fcff", "2026-06-30", 4_725_000_000., 5_459_000_000., (1_262_000_000., 1_262_000_000., 1_262_000_000.), _shares(123_763_000.), (.105, .09, .08), (0., .015, .02), "Conditional Low estimate. Merchant cash uses a full-liability/restricted-cash/no-reserve range, and reported nonredeemable NCI is deducted separately.", "Invalidate if merchant balances, debt, NCI, investments, diluted shares or normalized travel cash leave the recorded ranges.", cash_range=(445_000_000., 4_725_000_000., 7_127_000_000.)),
}


POINT_SPECS = {
    "EL": (("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 3_126_000_000.), ("NotesAndLoansPayableCurrent", 502_000_000.), ("LongTermDebtAndCapitalLeaseObligations", 6_810_000_000.)),
    "EBAY": (("CashAndCashEquivalentsAtCarryingValue", 2_310_000_000.), ("AvailableForSaleSecuritiesDebtSecurities", 2_541_000_000.), ("CustomerAccounts", 1_231_000_000.), ("DebtAndCapitalLeaseObligations", 6_735_000_000.)),
    "BKNG": (("CashAndCashEquivalentsAtCarryingValue", 17_214_000_000.), ("RestrictedCashAndCashEquivalentsAtCarryingValue", 294_000_000.), ("DeferredMerchantBookings", 10_121_000_000.), ("DebtInstrumentCarryingAmount", 20_300_000_000.)),
    "TPR": (("CashAndCashEquivalentsAtCarryingValue", 974_700_000.), ("ShortTermInvestments", 177_300_000.), ("LongTermDebtNoncurrent", 2_396_600_000.), ("PreferredStockValue", 0.)),
    "GRMN": (("CashAndCashEquivalentsAtCarryingValue", 2_334_235_000.), ("AvailableForSaleSecuritiesDebtSecurities", 2_035_635_000.)),
    "WYNN": (("CashAndCashEquivalentsAtCarryingValue", 1_573_353_000.), ("DebtInstrumentCarryingAmount", 10_825_466_000.), ("MinorityInterest", -737_216_000.), ("PreferredStockValue", 0.)),
    "DPZ": (("CashAndCashEquivalentsAtCarryingValue", 164_836_000.), ("MarketableSecuritiesNoncurrent", 27_638_000.), ("LongTermDebtAndCapitalLeaseObligations", 4_876_221_000.), ("LongTermDebtAndCapitalLeaseObligationsCurrent", 7_423_000.)),
    "LVS": (("CashAndCashEquivalentsAtCarryingValue", 3_376_000_000.), ("LongTermDebtAndLeaseObligationIncludingCurrentMaturitiesGross", 15_402_000_000.), ("MinorityInterest", 316_000_000.), ("PreferredStockValue", 0.)),
    "TSLA": (("CashAndCashEquivalentsAtCarryingValue", 15_219_000_000.), ("ShortTermInvestments", 28_305_000_000.), ("LongTermDebtAndFinanceLeasesCurrent", 1_418_000_000.), ("LongTermDebtAndFinanceLeasesNoncurrent", 7_924_000_000.), ("MinorityInterest", 607_000_000.), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 54_000_000.), ("PreferredStockValue", 0.)),
    "EXPE": (("CashAndCashEquivalentsAtCarryingValue", 6_682_000_000.), ("RestrictedCashAndCashEquivalentsAtCarryingValue", 2_402_000_000.), ("ShortTermInvestments", 445_000_000.), ("DeferredMerchantBookingsLiabilityCurrent", 15_426_000_000.), ("LongTermDebtNoncurrent", 5_459_000_000.), ("NonredeemableNoncontrollingInterest", 1_262_000_000.)),
}

SHARE_STARTS = {
    "EL": "2025-07-01", "EBAY": "2026-01-01", "BKNG": "2026-01-01",
    "TPR": "2025-06-29", "GRMN": "2025-12-28", "WYNN": "2026-01-01",
    "DPZ": "2025-12-29", "LVS": "2026-01-01", "EXPE": "2026-01-01",
}


def _structural_flow(structural: dict[str, Any], *, name: str, start: str, end: str, expected: float) -> dict[str, Any]:
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") == start and row.get("period_end") == end and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and float(row["value"]) == expected]
    if not rows:
        raise ValueError(f"{name}: expected {expected} absent for {start}/{end}")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "filed": structural.get("filed"), "form": structural.get("form"), "period_start": start, "period_end": end, "concept": row.get("qname"), "unit": row.get("unit") or "USD", "value": expected, "reported_vs_estimated": "reported"}


def _structural_instant(structural: dict[str, Any], *, name: str, end: str, expected: float, unit: str) -> dict[str, Any]:
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") is None and row.get("period_end") == end and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and float(row["value"]) == expected and row.get("unit") == unit]
    if not rows:
        raise ValueError(f"{name}: expected {expected} {unit} absent for {end}")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "period_end": end, "concept": row.get("qname"), "unit": unit, "value": expected, "reported_vs_estimated": "reported"}


def _grmn_ttm(structural: dict[str, Any], normalizer: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    specs = {
        "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", 3_775_582_000., 3_349_663_000.),
        "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities", 939_544_000., 593_959_000.),
        "capital_expenditures": ("PaymentsToAcquirePropertyPlantAndEquipment", 194_395_000., 85_738_000.),
    }
    values = {}
    for field, (name, current, prior) in specs.items():
        annual = normalizer.annual_series(field, 1)[0]
        current_source = _structural_flow(structural, name=name, start="2025-12-28", end="2026-06-27", expected=current)
        prior_source = _structural_flow(structural, name=name, start="2024-12-29", end="2025-06-28", expected=prior)
        value = float(annual.value) + current - prior
        values[field] = {"field": field, "value": value, "period_end": "2026-06-27", "method": "latest_fy_plus_current_h1_minus_prior_h1", "sources": [annual.as_dict(), current_source, prior_source]}
    return values["revenue"], values["operating_cash_flow"], values["capital_expenditures"]


def _bridge_sources(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT_SPECS[ticker]]
    if ticker == "TSLA":
        rows.append(_structural_instant(structural, name="CommonStockSharesOutstanding", end=policy.period, expected=3_949_000_000., unit="xbrli:shares"))
    else:
        rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=policy.shares[1], period_start=SHARE_STARTS[ticker], period_end=policy.period))
    if ticker == "GRMN":
        rows.extend((_source_proven_no_debt(structural, period_end=policy.period), _source_proven_no_other_equity_claims(structural, period_end=policy.period)))
    elif ticker not in {"WYNN", "LVS", "TSLA", "EXPE"}:
        rows.append(_source_proven_no_other_equity_claims(structural, period_end=policy.period))
    if ticker == "WYNN":
        rows.append({"source_kind": "source_bounded_policy", "field": "negative_book_nci_attribution", "period_end": policy.period, "reported_vs_estimated": "estimated_range", "value_range": {"bear": policy.nci[0], "base": policy.nci[1], "bull": policy.nci[2]}, "basis": "The absolute reported negative minority-interest balance caps the conservative attribution reserve; the model never treats a missing claim as zero."})
    if ticker == "LVS":
        rows.append({"source_kind": "issuer_filing_text_and_governed_policy", "accession": structural["source_accession"], "field": "macao_concession_forward_reinvestment", "period_end": policy.period, "unit": "USD", "reported_commitment": 4_440_000_000., "reported_vs_estimated": "reported_commitment_with_estimated_timing", "annual_cash_range": {"bear": policy.development_cash_reserve[0], "base": policy.development_cash_reserve[1], "bull": policy.development_cash_reserve[2]}, "basis": "The filing reports a $4.44 billion Macao concession commitment. FinSight allocates it over five, ten, or twenty years because exact annual timing is not reported; Singapore expansion remains an additional Conditional warning."})
        rows.append({"source_kind": "issuer_filing_text_and_cash_flow_reconciliation", "accession": structural["source_accession"], "field": "singapore_expansion_nonoverlap", "period_end": policy.period, "unit": "USD", "reported_incurred_approx": 3_000_000_000., "current_ttm_capex": 1_029_000_000., "reported_vs_estimated": "reported_incurred_and_reported_cash_flow", "basis": "Roughly $3 billion described as already incurred is not deducted again. Current TTM capex is already inside OCF-minus-capex and the company-history cash margins used by every scenario; construction timing uncertainty through 2029-30 keeps the result Conditional."})
    if ticker == "TSLA":
        current = [row for row in structural["facts"] if row.get("local_name") == "RevenueFromContractWithCustomerExcludingAssessedTax" and row.get("period_start") == "2026-01-01" and row.get("period_end") == "2026-06-30" and isinstance(row.get("value"), (int, float)) and float(row["value"]) == 526_000_000. and any("AutomotiveRegulatoryCreditsMember" in str(value) for _, value in (row.get("dimensions") or []))]
        prior = [row for row in structural["facts"] if row.get("local_name") == "RevenueFromContractWithCustomerExcludingAssessedTax" and row.get("period_start") == "2025-01-01" and row.get("period_end") == "2025-06-30" and isinstance(row.get("value"), (int, float)) and float(row["value"]) == 1_034_000_000. and any("AutomotiveRegulatoryCreditsMember" in str(value) for _, value in (row.get("dimensions") or []))]
        if not current or not prior:
            raise ValueError("TSLA regulatory-credit comparison is absent")
        rows.append({"source_kind": "structural_xbrl_and_governed_policy", "accession": structural["source_accession"], "field": "automotive_regulatory_credit_cash_dependency", "period_start": "2026-01-01", "period_end": policy.period, "unit": "USD", "current_h1": 526_000_000., "prior_h1": 1_034_000_000., "reported_vs_estimated": "reported_comparison_with_estimated_cash_stress", "annual_cash_range": {"bear": policy.cash_dependency_reserve[0], "base": policy.cash_dependency_reserve[1], "bull": policy.cash_dependency_reserve[2]}, "basis": "Current H1 credits are annualized and removed in bear, current H1 is removed in base, and no separate removal is made in bull. Because credit revenue is already inside reported OCF, each reserve is subtracted once from forecast cash."})
    return rows


def build_batch_07_history_result(*, ticker: str, source_root: Path, structural_root: Path) -> dict[str, Any]:
    policy = P[ticker]
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if filing["period_end"] != policy.period or structural["source_accession"] != filing["accession"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    normalizer = _normalizer(submissions, facts)
    if ticker == "GRMN":
        revenue_flow, operating_flow, capex_flow = _grmn_ttm(structural, normalizer)
        interest_flow = None
        current_cash = float(operating_flow["value"]) - float(capex_flow["value"])
        annual_cash, annual_revenue, annual_sources = _annual_owner_cash(normalizer)
        cash_formula = "operating cash flow - capex; no interest addback because current filing proves no interest-bearing debt"
    else:
        revenue_flow = normalizer.ttm_flow("revenue")
        operating_flow = normalizer.ttm_flow("operating_cash_flow")
        capex_flow = normalizer.ttm_flow("capital_expenditures")
        interest_flow = normalizer.ttm_flow("interest_expense")
        tax_rate = _normalized_tax_rate(normalizer)[0]
        current_cash = cash_fcff_from_reported(operating_cash_flow=float(operating_flow["value"]), capital_expenditures=float(capex_flow["value"]), spectrum_investment=0., interest_expense=abs(float(interest_flow["value"])), tax_rate=tax_rate)
        annual_cash, annual_revenue, annual_sources = _annual_cash_fcff(normalizer, spectrum_required=False, spectrum_floor=0., spectrum_source={}, scope_adjustment=0.)
        cash_formula = "OCF - capex + after-tax interest"
    ttm_sources = []
    for flow in (revenue_flow, operating_flow, capex_flow, interest_flow or {}):
        ttm_sources.extend(dict(source) for source in flow.get("sources", []) if isinstance(source, dict))
    profile = build_cash_fcff_history_profile(annual_cash_states=annual_sources, ttm_revenue=float(revenue_flow["value"]), ttm_cash_fcff=current_cash, ttm_period_end=filing["period_end"], ttm_sources=ttm_sources, valuation_date=BATCH_07_VALUATION_DATE)
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None:
        raise ValueError(f"{ticker}: at least three source-linked annual periods are required")
    margins = tuple(max(.001, min(.60, value)) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    pandemic_downturn_stress = ticker in {"WYNN", "LVS"}
    if pandemic_downturn_stress:
        # The positive-history selector intentionally excludes negative cash years.
        # Restore an explicit near-zero bear state for casino shutdown/cycle risk.
        margins = (.001, margins[1], margins[2])
    margins = tuple(max(.001, margin - (policy.development_cash_reserve[index] + policy.cash_dependency_reserve[index]) / float(revenue_flow["value"])) for index, margin in enumerate(margins))
    growth = tuple(max(-.10, min(.20, value)) for value in (growth_metric.low, growth_metric.base, growth_metric.high))
    rows = []
    for index, name in enumerate(("bear", "base", "bull")):
        cash_and_investments = policy.cash_range[index] if policy.cash_range is not None else policy.cash
        raw = five_year_fcff_dcf(revenue=float(revenue_flow["value"]), fcff_margin=margins[index], growth=growth[index], wacc=policy.wacc[index], terminal_growth=policy.terminal_growth[index], cash_and_investments=cash_and_investments, debt=policy.debt, noncontrolling_interests=policy.nci[index], shares=policy.shares[index])
        value = max(0., float(raw["value_per_share"]))
        rows.append({"name": name, "conditional_value_per_share": value, "raw_value_per_share": float(raw["value_per_share"]), "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": policy.wacc[index], "terminal_growth": policy.terminal_growth[index], "shares": policy.shares[index], "limited_liability_floor_applied": value == 0 and float(raw["value_per_share"]) < 0})
    scenario_range = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not (0 <= scenario_range["low"] <= scenario_range["base"] <= scenario_range["high"] and scenario_range["base"] > 0):
        raise ValueError(f"{ticker}: finite ordered positive-base range required")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario_range["base"], accounting_base=scenario_range["base"], accounting_high=scenario_range["base"], scenario_low=scenario_range["low"], scenario_base=scenario_range["base"], scenario_high=scenario_range["high"], model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons)
    assumptions = {**profile.public_metadata(), "cash_conversion_margin": margins, "growth": growth, "wacc": policy.wacc, "terminal_growth": policy.terminal_growth, "shares": policy.shares, "cash_formula": cash_formula, "pandemic_downturn_stress": pandemic_downturn_stress, "forward_development_cash_reserve": policy.development_cash_reserve, "cash_dependency_reserve": policy.cash_dependency_reserve, "cash_and_investments_range": policy.cash_range or (policy.cash, policy.cash, policy.cash), "equity_floor_basis": "limited-liability floor after negative residual" if scenario_range["low"] == 0 else "not applied", "calculator_calibration": "Calculator is calibrated to the published base; issuer history and bridge remain fixed.", "invalidation": policy.invalidation}
    key_assumptions = (BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual history supplies cash-conversion and growth scenarios."), BaselineAssumption("reported anchors", str({"revenue": revenue_flow["value"], "operating_cash_flow": operating_flow["value"], "capex": capex_flow["value"]}), AssumptionClassification.REPORTED, "Cutoff-safe reported facts anchor current cash generation."), BaselineAssumption("scenario policy", str(assumptions), AssumptionClassification.FINSIGHT_ASSUMPTION, "Discount rates, terminal growth and share sensitivity are transparent FinSight assumptions."))
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_07_HISTORY_VERSION, low=scenario_range["low"], base=scenario_range["base"], high=scenario_range["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=key_assumptions, warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    merchant_treatment = {
        "EBAY": "Reported customer accounts are deducted from cash and securities to determine excess cash; the matching operating payable is not subtracted again.",
        "BKNG": "Excess cash spans full deferred-merchant reserve, midpoint reserve, and restricted-traveler-cash reserve; the operating liability is not subtracted again.",
        "EXPE": "Excess cash spans full deferred-merchant reserve, restricted-traveler-cash reserve, and no deferred reserve; the operating liability is not subtracted again.",
    }.get(ticker, "not applicable")
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_07_HISTORY_VERSION, "availability_type": baseline.availability_type.value, "scenario_rows": rows, "scenario_range": scenario_range, "reported_inputs": {"ttm_revenue": revenue_flow["value"], "ttm_operating_cash_flow": operating_flow["value"], "ttm_capex": capex_flow["value"], "ttm_interest_expense": None if interest_flow is None else interest_flow["value"]}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": {"revenue": revenue_flow, "operating_cash_flow": operating_flow, "capital_expenditures": capex_flow, "interest_expense": interest_flow}, "annual_sources": annual_sources, "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge_sources(ticker, structural, policy), "bridge_reconciliation": {"cash_and_investments": policy.cash, "cash_and_investments_range": policy.cash_range or (policy.cash, policy.cash, policy.cash), "debt_and_finance_leases": policy.debt, "nci_range": policy.nci, "merchant_or_customer_funds_treatment": merchant_treatment, "operating_lease_treatment": "Operating lease cash remains in OCF and is not subtracted again as debt."}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


if set(P) != set(BATCH_07_TICKERS):
    raise RuntimeError("Batch 07 policy denominator mismatch")
