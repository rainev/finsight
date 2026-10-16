"""History-backed practical baselines for controlled Universe Reset Batch 29."""
from __future__ import annotations

import copy
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
from .batch_02_practical_inputs import (
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
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _no_preferred
from .batch_16_history import _share_point
from .batch_29 import BATCH_29_TICKERS, BATCH_29_VALUATION_DATE
from .history import build_cash_fcff_history_profile
from .legal_tail_policy import apply_unquantified_legal_tail_policy
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_29_HISTORY_VERSION = "BATCH-29-TECHNOLOGY-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"CIEN", "NTAP", "VRSN"})
CONDITIONAL_TICKERS = frozenset({"TRMB", "ROP", "SNPS", "INTU", "NVDA", "FFIV", "AKAM"})
WITHHELD_TICKERS = frozenset()


def _shares(weighted: float, current: float) -> tuple[float, float, float]:
    high = max(weighted, current)
    low = min(weighted, current)
    return high, (high + low) / 2, low


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: tuple[float, float, float]
    debt: float
    claims: tuple[float, float, float]
    shares: tuple[float, float, float]
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str
    bridge_formula: str


def _cash(value: float) -> tuple[float, float, float]:
    return value, value, value


P = {
    "TRMB": Policy(
        "post_acquisition_geospatial_software_faded_fcff",
        "2026-07-03",
        (214_400_000., 560_100_000., 831_800_000.),
        1_459_300_000.,
        (0.,) * 3,
        _shares(233_700_000., 233_179_848.),
        (-.03, .02, .06),
        (.11, .095, .085),
        (0., .015, .025),
        "Conditional Low geospatial-software baseline. Current cash history is finite, while first-half acquisitions, a $562M goodwill impairment, equity-method operations, and $625.8M of non-cancellable operating commitments make normalization provisional.",
        "Invalidate if acquired cash conversion, the impaired/equity-method perimeter, purchase commitments, debt, investments, or diluted shares changes materially.",
        "$214.4M cash plus a $0/$345.7M/$617.4M governed nonoperating-investment overlay; less $1.4593B complete carrying debt. Equity-method income is immaterial and the investment range is added once. Ordinary commitments are not deducted again as debt.",
    ),
    "ROP": Policy(
        "pre_indicor_divestiture_vertical_software_faded_fcff",
        "2026-06-30",
        (1_664_900_000., 1_911_000_000., 2_157_100_000.),
        11_319_400_000.,
        (0.,) * 3,
        _shares(102_600_000., 98_900_874.),
        (.03, .08, .12),
        (.105, .09, .08),
        (.01, .02, .025),
        "Conditional Low pre-Indicor-divestiture vertical-software baseline. Five-year operating cash history reconciles, while the announced approximately $5B Indicor sale has not closed. The current stake and expected approximately $1.3B pre-tax proceeds are included once as a governed nonoperating-asset range; final tax and purchase-price adjustments remain unknown.",
        "Invalidate if the Indicor sale closes, terminates, or changes; or if software cash conversion, debt/revolver funding, repurchases, acquisitions, equity-method scope, or diluted shares changes materially.",
        "$364.9M cash plus a $1.3B/$1.5461B/$1.7922B Indicor stake range anchored by expected pre-tax proceeds and current Level-3 carrying value; less $11.3194B debt. Indicor is an equity-method nonoperating investment outside consolidated operating revenue/cash flow, and the stake/proceeds are added only once.",
    ),
    "SNPS": Policy(
        "post_ansys_eda_simulation_faded_fcff",
        "2026-04-30",
        _cash(2_484_438_000.),
        10_035_962_000.,
        (0.,) * 3,
        (192_144_000., 191_811_662.5, 191_479_325.),
        (.02, .10, .15),
        (.11, .095, .085),
        (.01, .02, .025),
        "Conditional Low post-Ansys EDA/simulation baseline. The $34.9B acquisition, partial-period acquired history, debt, restructuring, acquired amortization, integration, and new share base remain material.",
        "Invalidate if Ansys conversion, integration/restructuring, debt, securities, NCI, or diluted shares changes materially.",
        "$2.412472B cash plus $71.966M AFS securities; $10.035962B statement net carrying debt. The $10.111691B gross debt diagnostic is retained in source evidence but not deducted a second time. Operating leases remain post-rent operating items.",
    ),
    "INTU": Policy(
        "customer_funds_segregated_financial_software_faded_fcff",
        "2026-04-30",
        _cash(6_956_000_000.),
        6_162_000_000.,
        (0.,) * 3,
        _shares(279_000_000., 273_537_000.),
        (.05, .12, .18),
        (.105, .09, .08),
        (.01, .02, .025),
        "Conditional Low financial-software baseline. Customer funds are fully segregated, while business-loan portfolio reinvestment, the $300M-$340M restructuring plan, and unquantified free-tax-preparation/Ontario proceedings remain material.",
        "Invalidate if customer-fund ownership, business-loan reinvestment/credit losses, restructuring, legal/regulatory matters, tax/software cash conversion, debt, investments, buybacks, or diluted shares changes materially.",
        "$4.681B issuer cash plus $2.099B current and $176M long-term issuer investments; $7.760B customer funds exactly match customer payables and are excluded. $750M current plus $5.412B noncurrent debt is deducted once.",
    ),
    "CIEN": Policy(
        "optical_networking_cycle_faded_fcff",
        "2026-05-02",
        _cash(1_402_940_000.),
        1_536_188_000.,
        (0.,) * 3,
        (146_314_000., 143_933_461., 141_552_922.),
        (-.03, .07, .14),
        (.115, .10, .09),
        (0., .015, .025),
        "Source-bounded optical-networking cycle baseline. Five-year history includes the down-cycle; cash/investments, complete debt/current finance lease, warranties, preferred/NCI absence, and shares reconcile. Partly adjustable component orders remain operating inputs.",
        "Invalidate if purchase-order cancellability, inventory demand, warranty cash, debt/finance leases, securities, or diluted shares changes materially.",
        "$1.045126B cash plus $157.708M short-term and $200.106M noncurrent marketable securities; the $468.377M aggregate AFS fact overlaps cash equivalents and is not added again. $1.531119B debt plus $5.069M current finance lease. Purchase orders remain operating inputs.",
    ),
    "NTAP": Policy(
        "data_storage_cycle_faded_fcff",
        "2026-04-24",
        _cash(3_584_000_000.),
        2_487_000_000.,
        (0.,) * 3,
        _shares(201_000_000., 195_919_927.),
        (0., .03, .06),
        (.105, .09, .08),
        (.01, .02, .025),
        "Source-bounded data-storage baseline. Five-year cash history, cash/securities, complete debt, restructuring, warranties, preferred absence, repurchases, and shares reconcile; disclosed purchase commitments fit available cash and operating conversion.",
        "Invalidate if storage demand, purchase commitments, restructuring/warranty cash, debt, securities, patent claims, or diluted shares changes materially.",
        "$2.070B cash plus $1.514B short-term investments; $2.487B complete debt. The $1.4B operating commitment, including $1.1B due in fiscal 2027, remains inside cash conversion and is not deducted twice.",
    ),
    "VRSN": Policy(
        "domain_registry_recurring_cash_faded_fcff",
        "2026-06-30",
        _cash(484_100_000.),
        1_785_100_000.,
        (0.,) * 3,
        _shares(91_400_000., 90_300_000.),
        (.02, .05, .07),
        (.10, .085, .075),
        (.01, .02, .025),
        "Source-bounded domain-registry baseline. Five-year recurring cash, securities, dividends, buybacks, preferred absence, and shares reconcile; the July 20 redemption is reflected in post-period cash and debt.",
        "Invalidate if registry economics, pricing/regulatory terms, the July redemption, debt, securities, buybacks, or diluted shares changes materially.",
        "$840.9M cash plus $193.2M marketable securities less $550M July redemption cash; post-redemption debt is the $1.7851B reported noncurrent senior-note carrying amount.",
    ),
    "NVDA": Policy(
        "ai_semiconductor_investment_adjusted_faded_fcff",
        "2026-04-26",
        (76_294_500_000., 94_694_750_000., 123_936_000_000.),
        8_470_000_000.,
        (38_245_000_000., 23_351_000_000., 8_457_000_000.),
        _shares(24_391_000_000., 24_200_000_000.),
        (.05, .20, .30),
        (.12, .10, .09),
        (0., .015, .025),
        "Conditional Low AI-semiconductor baseline. Cash generation is exceptional but $119B manufacturing/supply/capacity commitments, $30B cloud commitments, $6B other vendor commitments, $27B contingent investment commitments, the Groq license payable, volatile investments, export controls, litigation, and growth fade remain material.",
        "Invalidate if AI demand/growth fade, export controls, investment/manufacturing/cloud commitments, Groq consideration, securities values, litigation, debt, or diluted shares changes materially.",
        "$50.335B cash/marketable debt securities plus governed haircuts on $30.237B marketable and $43.364B nonmarketable equity securities; $8.470B debt is deducted once. Claims before the future-lease reserve are the $3.957B Groq payable, $4.5B unrecognized-tax-benefit liability, $27B/13.5B/$0 contingent investment reserve, and $2.788B/$1.394B/$0 net guarantee exposure.",
    ),
    "FFIV": Policy(
        "cyber_incident_application_security_owner_cash_faded_fcff",
        "2026-06-30",
        _cash(1_605_782_000.),
        0.,
        (0.,) * 3,
        _shares(57_674_000., 56_627_182.),
        (0., .04, .07),
        (.105, .09, .08),
        (.01, .02, .025),
        "Conditional Low debt-free application-security baseline. Five-year owner-cash history and the current bridge reconcile, while the disclosed cyber incident, $26.5M response costs, $5.3M insurance recoveries, and possible customer/third-party claims remain outside a filed loss range.",
        "Invalidate if application-security demand, owner-cash conversion, debt absence, cyber claims/recoveries, acquisitions, investments, restructuring, or diluted shares changes materially.",
        "$1.605782B cash and source-proven no debt. Cash-equivalent fair-value disclosures are not added again; the $21.991M equity investment is conservatively excluded.",
    ),
    "AKAM": Policy(
        "post_layerx_cloud_security_faded_fcff",
        "2026-06-30",
        _cash(4_411_305_000.),
        7_562_828_000.,
        (0.,) * 3,
        (153_686_000., 148_701_304.5, 143_716_609.),
        (0., .05, .08),
        (.11, .095, .085),
        (.005, .015, .025),
        "Conditional Low post-LayerX cloud/security baseline. LayerX closed after the balance sheet for approximately $205M cash, while $3.5B of new convertibles fund accelerated cloud capex and note conversion/dilution remains material.",
        "Invalidate if LayerX purchase accounting/conversion, accelerated cloud capex, convertible debt/hedges/warrants, securities, or diluted shares changes materially.",
        "$1.480257B cash plus $3.136048B marketable securities less $205M LayerX cash consideration; $7.562828B current/noncurrent convertible carrying debt.",
    ),
}


POINT = {
    "TRMB": (("CashAndCashEquivalentsAtCarryingValue", 214_400_000.), ("DebtLongtermAndShorttermCombinedAmount", 1_459_300_000.), ("EquityMethodInvestments", 345_700_000.)),
    "ROP": (("CashAndCashEquivalentsAtCarryingValue", 364_900_000.), ("LongTermDebtCurrent", 718_300_000.), ("LongTermDebtNoncurrent", 10_601_100_000.), ("EquityMethodInvestments", 1_792_200_000.)),
    "SNPS": (("CashAndCashEquivalentsAtCarryingValue", 2_412_472_000.), ("AvailableForSaleSecuritiesDebtSecurities", 71_966_000.), ("LongTermDebt", 10_035_962_000.), ("DebtInstrumentCarryingAmount", 10_111_691_000.), ("MinorityInterest", -1_066_000.)),
    "INTU": (("CashAndCashEquivalentsAtCarryingValue", 4_681_000_000.), ("DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent", 2_099_000_000.), ("LongTermInvestments", 176_000_000.), ("AvailableForSaleSecuritiesDebtSecuritiesFundsHeldForCustomers", 377_000_000.), ("FundsReceivableAndAmountsHeldForCustomers", 7_760_000_000.), ("FundsPayableAndAmountsDueToCustomers", 7_760_000_000.), ("LongTermDebtCurrent", 750_000_000.), ("LongTermDebtNoncurrent", 5_412_000_000.)),
    "CIEN": (("CashAndCashEquivalentsAtCarryingValue", 1_045_126_000.), ("ShortTermInvestments", 157_708_000.), ("MarketableSecuritiesNoncurrent", 200_106_000.), ("AvailableForSaleSecuritiesDebtSecurities", 468_377_000.), ("LongTermDebtCurrent", 11_580_000.), ("LongTermDebtNoncurrent", 1_519_539_000.), ("FinanceLeaseLiabilityCurrent", 5_069_000.)),
    "NTAP": (("CashAndCashEquivalentsAtCarryingValue", 2_070_000_000.), ("ShortTermInvestments", 1_514_000_000.), ("LongTermDebt", 2_487_000_000.)),
    "VRSN": (("CashAndCashEquivalentsAtCarryingValue", 840_900_000.), ("MarketableSecuritiesCurrent", 193_200_000.), ("SeniorNotesCurrent", 549_300_000.), ("SeniorLongTermNotes", 1_785_100_000.)),
    "NVDA": (("CashAndCashEquivalentsAtCarryingValue", 13_237_000_000.), ("DebtSecuritiesCurrent", 37_098_000_000.), ("EquitySecuritiesFvNi", 30_237_000_000.), ("NonMarketableSecurities", 43_364_000_000.), ("DebtCurrent", 1_000_000_000.), ("LongTermDebtNoncurrent", 7_470_000_000.), ("BusinessCombinationConsiderationPayable", 3_957_000_000.)),
    "FFIV": (("CashAndCashEquivalentsAtCarryingValue", 1_605_782_000.), ("LongTermInvestments", 21_991_000.)),
    "AKAM": (("CashAndCashEquivalentsAtCarryingValue", 1_480_257_000.), ("MarketableSecuritiesCurrent", 1_875_130_000.), ("MarketableSecuritiesNoncurrent", 1_260_918_000.), ("ConvertibleLongTermNotesPayable", 5_857_252_000.), ("ConvertibleNotesPayableCurrent", 1_705_576_000.)),
}

WEIGHTED = {"TRMB": 233_700_000., "ROP": 102_600_000., "SNPS": 191_580_000., "INTU": 279_000_000., "CIEN": 146_078_000., "NTAP": 201_000_000., "VRSN": 91_400_000., "NVDA": 24_391_000_000., "FFIV": 57_674_000., "AKAM": 151_854_000.}
START = {"TRMB": "2026-01-03", "ROP": "2026-01-01", "SNPS": "2025-11-01", "INTU": "2025-08-01", "CIEN": "2025-11-02", "NTAP": "2025-04-26", "VRSN": "2026-01-01", "NVDA": "2026-01-26", "FFIV": "2025-10-01", "AKAM": "2026-01-01"}
CURRENT = {"TRMB": 233_179_848., "ROP": 98_900_874., "SNPS": 191_479_325., "INTU": 273_537_000., "CIEN": 141_552_922., "NTAP": 195_919_927., "VRSN": 90_300_000., "NVDA": 24_200_000_000., "FFIV": 56_627_182., "AKAM": 143_716_609.}
END = {"TRMB": "2026-08-07", "ROP": "2026-07-28", "SNPS": "2026-05-22", "INTU": "2026-05-14", "CIEN": "2026-05-29", "NTAP": "2026-05-28", "VRSN": "2026-07-17", "NVDA": "2026-05-15", "FFIV": "2026-08-03", "AKAM": "2026-08-03"}
QUARTER_DILUTED = {"SNPS": (192_144_000., "2026-02-01", "2026-04-30"), "CIEN": (146_314_000., "2026-02-01", "2026-05-02"), "AKAM": (153_686_000., "2026-04-01", "2026-06-30")}


def _fact(structural, name, value, start, end, allow_dimensions=False):
    rows = [
        row for row in structural["facts"]
        if row.get("local_name") == name
        and row.get("period_start") == start
        and row.get("period_end") == end
        and (allow_dimensions or not row.get("dimensions"))
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) == value
    ]
    if not rows:
        raise ValueError(f"{name}={value} absent")
    row = rows[0]
    return {
        "source_kind": "structural_xbrl",
        "accession": structural["source_accession"],
        "filed": structural.get("filed_date"),
        "period_start": start,
        "period_end": end,
        "concept": row.get("qname"),
        "unit": row.get("unit"),
        "value": value,
        "dimensions": row.get("dimensions", []),
        "reported_vs_estimated": "reported",
    }


def _bridge(ticker, structural, policy):
    rows = [
        _point(structural, name=name, expected=value, period_end=policy.period)
        for name, value in POINT[ticker]
    ]
    rows.append(
        _duration(
            structural,
            name="WeightedAverageNumberOfDilutedSharesOutstanding",
            expected=WEIGHTED[ticker],
            period_start=START[ticker],
            period_end=policy.period,
        )
    )
    rows.append(_share_point(structural, expected=CURRENT[ticker], end=END[ticker]))
    if ticker in QUARTER_DILUTED:
        value, start, end = QUARTER_DILUTED[ticker]
        rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=value, period_start=start, period_end=end))
    rows.append(_no_preferred(structural, policy.period))
    if ticker != "SNPS":
        rows.append(_source_proven_no_other_equity_claims(structural, period_end=policy.period))
    else:
        rows.append({"source_kind": "structural_xbrl_treatment", "accession": structural["source_accession"], "period_end": policy.period, "field": "minority_interest", "reported_value": -1_066_000., "unit": "USD", "treatment": "Negative minority-interest deficit is retained in evidence but not deducted as a positive common-equity claim.", "reported_vs_estimated": "reported_with_policy_treatment"})
    if ticker == "FFIV":
        rows.append(_source_proven_no_debt(structural, period_end=policy.period))
    return rows


def _events(ticker, filing, structural, policy, package, source_receipt):
    rows = [{
        "source_kind": "controlling_filing_narrative",
        "accession": filing["accession"],
        "filed": filing["filed"],
        "period_end": filing["period_end"],
        "matter": policy.warning,
        "reported_vs_estimated": "reported_narrative",
    }]
    specs = {
        "TRMB": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 230_500_000., "2026-01-03", "2026-07-03", False), ("GoodwillImpairmentLoss", 562_000_000., "2026-01-03", "2026-07-03", False), ("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 625_800_000., None, "2026-07-03", False)),
        "ROP": (("PaymentsForRepurchaseOfCommonStock", 2_726_700_000., "2026-01-01", "2026-06-30", False), ("PaymentsToAcquireBusinessesNetOfCashAcquired", 27_500_000., "2026-01-01", "2026-06-30", False), ("ProceedsFromDivestitureOfBusinesses", 5_000_000_000., "2026-05-05", "2026-05-05", True), ("ExpectedProceedsFromDivestitureOfBusiness", 1_300_000_000., "2026-07-01", "2026-12-31", True)),
        "SNPS": (("BusinessCombinationConsiderationTransferred1", 34_900_000_000., "2025-07-17", "2025-07-17", True), ("RestructuringReserve", 104_000_000., None, "2026-04-30", False)),
        "INTU": (("PaymentsForRepurchaseOfCommonStock", 3_341_000_000., "2025-08-01", "2026-04-30", False),),
        "CIEN": (("PurchaseObligation", 2_800_000_000., None, "2026-05-02", False), ("ProductWarrantyAccrualClassifiedCurrent", 60_356_000., None, "2026-05-02", False)),
        "NTAP": (("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 1_400_000_000., None, "2026-04-24", False), ("UnrecordedUnconditionalPurchaseObligationBalanceOnFirstAnniversary", 1_100_000_000., None, "2026-04-24", False)),
        "VRSN": (("PaymentsForRepurchaseOfCommonStock", 426_800_000., "2026-01-01", "2026-06-30", False),),
        "NVDA": (("BusinessCombinationConsiderationPayable", 3_957_000_000., None, "2026-04-26", False), ("VariableInterestEntityEntityMaximumLossExposureAmount", 2_300_000_000., None, "2026-04-26", True)),
        "FFIV": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 47_619_000., "2025-10-01", "2026-06-30", False), ("OtherNonrecurringExpense", 26_500_000., "2025-10-01", "2026-06-30", True), ("InsuranceRecoveries", 5_300_000., "2025-10-01", "2026-06-30", False)),
        "AKAM": (("PaymentsToAcquireBusinessesGross", 205_000_000., "2026-07-01", "2026-07-31", True),),
    }
    rows.extend(
        _fact(structural, name, value, start, end, allow_dimensions)
        for name, value, start, end, allow_dimensions in specs.get(ticker, ())
    )
    if ticker == "ROP":
        for row in rows:
            if str(row.get("concept", "")).endswith(":ExpectedProceedsFromDivestitureOfBusiness"):
                row["reported_vs_estimated"] = "reported_forecast"
                row["treatment"] = "Expected pre-tax proceeds are transaction guidance, not current cash or historical realized proceeds."
    if ticker == "INTU":
        rows.extend((
            {"source_kind": "customer_funds_reconciliation", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "reported_terms": {"funds_receivable_and_held": 7_760_000_000., "funds_payable_and_due": 7_760_000_000., "restricted_customer_cash": 7_233_000_000., "customer_afs": 377_000_000., "processor_receivable": 150_000_000.}, "reported_vs_estimated": "reported"},
            {"source_kind": "controlling_filing_business_loan_reinvestment", "accession": filing["accession"], "filed": filing["filed"], "period_start": "2025-08-01", "period_end": policy.period, "reported_terms": {"originations_and_purchases": 4_930_000_000., "sales": 1_389_000_000., "principal_repayments": 3_125_000_000., "net_portfolio_reinvestment": 416_000_000.}, "governed_scenario_adjustment": {"bear": 554_666_666.6666666, "base": 416_000_000., "bull": 0.}, "reported_vs_estimated": "reported_nine_month_cash_with_governed_forward_range"},
            {"source_kind": "controlling_filing_restructuring_plan", "accession": filing["accession"], "filed": filing["filed"], "period_end": "2026-05-20", "reported_terms": {"expected_low": 300_000_000., "expected_high": 340_000_000., "primarily_cash": True, "expected_completion": "fiscal_2027_q1"}, "treatment": "The company-history range remains Conditional and the plan is an invalidation/replay trigger; no unavailable exact charge is inserted as zero.", "reported_vs_estimated": "reported_range"},
        ))
    if ticker == "NVDA":
        rows.extend((
            {"source_kind": "controlling_filing_investment_and_operating_commitments", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "reported_terms": {"investment_commitments": 27_000_000_000., "investment_expected_by": "fiscal_2027_remainder", "investment_subject_to_contingencies": True, "manufacturing_supply_capacity_commitments": 119_000_000_000., "manufacturing_due_fiscal_2027_remainder": 95_000_000_000., "cloud_service_commitments": 30_000_000_000., "other_vendor_commitments": 6_000_000_000., "marketable_equity": 30_237_000_000., "nonmarketable_securities": 43_364_000_000.}, "reported_vs_estimated": "reported"},
            {"source_kind": "controlling_filing_lease_and_guarantee_commitments", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "reported_terms": {"existing_operating_lease_minimum_payments": 5_604_000_000., "existing_operating_lease_liability": 4_344_000_000., "future_not_commenced_lease_obligations": 32_400_000_000., "future_lease_commencement_window": "fiscal_2027_q2_through_fiscal_2033", "guarantee_gross_exposure": 3_500_000_000., "partner_escrow": 712_000_000., "guarantee_net_exposure": 2_788_000_000.}, "reported_vs_estimated": "reported"},
            {"source_kind": "controlling_filing_tax_and_legal_state", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "reported_terms": {"unrecognized_tax_benefits_including_interest_penalties": 4_500_000_000., "included_interest_and_penalties": 439_000_000., "securities_class_certified": "2026-03-25", "legal_loss_range": None}, "reported_vs_estimated": "reported_unknown_legal_tail"},
        ))
        rows.append({"source_kind": "controlling_filing_vie_exposure_treatment", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "reported_terms": {"infrastructure_fund_investment": 1_000_000_000., "maximum_loss_exposure_including_invested_and_future_committed_amounts": 2_300_000_000.}, "treatment": "Not separately deducted: the maximum exposure is a subset of infrastructure-fund invested/future committed amounts already covered by the reported investment assets, scenario haircuts, and $27B investment-commitment reserve.", "reported_vs_estimated": "reported_with_no_double_count_policy"})
    if ticker == "VRSN":
        rows.append({"source_kind": "controlling_filing_subsequent_debt_event", "accession": filing["accession"], "filed": filing["filed"], "period_end": "2026-07-20", "reported_terms": {"redeemed_principal": 550_000_000., "balance_sheet_current_carrying_amount": 549_300_000., "funding": "2026_notes_net_proceeds_and_cash_on_hand", "status": "redeemed"}, "treatment": "Subtract $550M from reported cash/securities and remove the $549.3M current carrying debt; retain the 2026 and other noncurrent notes.", "reported_vs_estimated": "reported"})
    if ticker == "FFIV":
        rows.append({"source_kind": "controlling_filing_cyber_claim_state", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "reported_terms": {"response_costs": 26_500_000., "insurance_recoveries": 5_300_000., "legal_contingency_accrual": None, "customer_and_third_party_claims_possible": True}, "treatment": "Reported operations remain numeric and Low; no unavailable claim is replaced with zero or deducted as a guessed amount.", "reported_vs_estimated": "reported_unknown_claim_tail"})
    if ticker == "AKAM":
        rows.append({"source_kind": "controlling_filing_debt_terms", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "reported_terms": {"may_2026_new_convertible_principal": 3_500_000_000., "total_note_par": 7_640_000_000., "purpose": "accelerated_cloud_capex_and_general_corporate"}, "reported_vs_estimated": "reported"})
        for row in rows:
            if row.get("value") == 205_000_000.:
                row["treatment"] = "Approximate LayerX cash consideration deducted once; subject to post-closing adjustments and therefore Conditional."
    primary_name = package.get("primary_document")
    primary = next((item for item in package.get("files", []) if item.get("local_path") == primary_name), None)
    if not isinstance(primary, dict) or not primary.get("sha256") or not primary.get("source_url"):
        raise ValueError(f"{ticker}: primary filing provenance unavailable")
    provenance = {"primary_document": primary_name, "source_url": primary["source_url"], "document_sha256": primary["sha256"], "package_manifest_sha256": source_receipt["package_manifest_sha256"]}
    for row in rows:
        if row.get("source_kind") != "structural_xbrl":
            row.update(provenance)
    return rows


def _ffiv_annual(normalizer):
    rows = []
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        capex = normalizer.annual_at_end("capital_expenditures", operating.end)
        revenue = normalizer.annual_at_end("revenue", operating.end)
        if capex is None or revenue is None or revenue.value <= 0:
            continue
        rows.append({
            "period_end": operating.end,
            "operating_cash_flow": operating.as_dict(),
            "capital_expenditures": capex.as_dict(),
            "interest_expense": None,
            "pretax_income": None,
            "income_tax": None,
            "revenue": revenue.as_dict(),
            "cash_fcff": operating.value - capex.value,
            "formula": "OCF - capex; source-proven no debt, so no interest addback",
        })
    return tuple(rows)


def _annual_with_software(normalizer):
    rows = []
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        capex = normalizer.annual_at_end("capital_expenditures", operating.end)
        software = normalizer.annual_at_end("software_development", operating.end)
        interest = normalizer.annual_at_end("interest_expense", operating.end)
        revenue = normalizer.annual_at_end("revenue", operating.end)
        pretax = normalizer.annual_at_end("pretax_income", operating.end)
        tax = normalizer.annual_at_end("income_tax", operating.end)
        if capex is None or software is None or interest is None or revenue is None or revenue.value <= 0:
            continue
        tax_rate = max(0., min(.30, tax.value / pretax.value)) if pretax is not None and tax is not None and pretax.value > 0 else .21
        value = cash_fcff_from_reported(operating_cash_flow=operating.value, capital_expenditures=capex.value + software.value, spectrum_investment=0., interest_expense=abs(interest.value), tax_rate=tax_rate)
        rows.append({"period_end": operating.end, "operating_cash_flow": operating.as_dict(), "capital_expenditures": capex.as_dict(), "software_development": software.as_dict(), "interest_expense": interest.as_dict(), "pretax_income": pretax.as_dict() if pretax else None, "income_tax": tax.as_dict() if tax else None, "revenue": revenue.as_dict(), "cash_fcff": value, "formula": "OCF - PP&E capex - capitalized software + after-tax interest"})
    return tuple(rows)


def build_batch_29_history_result(*, ticker: str, source_root: Path, structural_root: Path):
    if ticker not in BATCH_29_TICKERS:
        raise ValueError(ticker)
    policy = P[ticker]
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural_packet = Path(structural_root) / ticker
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    package = json.loads((structural_packet / "package-manifest.json").read_text())
    source_receipt = json.loads((structural_packet / "source-receipt.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural["source_accession"] != filing["accession"] or filing["period_end"] != policy.period:
        raise ValueError(f"{ticker}: controlling source mismatch")
    normalizer = _normalizer(submissions, facts)
    flow_names = ("revenue", "operating_cash_flow", "capital_expenditures") if ticker == "FFIV" else ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense", "software_development") if ticker == "ROP" else ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")
    flows = {name: normalizer.ttm_flow(name) for name in flow_names}
    tax_sources = ()
    tax_fallback = False
    if ticker == "FFIV":
        tax_rate = 0.
        current_cash = float(flows["operating_cash_flow"]["value"]) - float(flows["capital_expenditures"]["value"])
        annual = _ffiv_annual(normalizer)
        flows["interest_expense"] = {"field": "interest_expense", "value": 0., "period_end": policy.period, "method": "source_proven_no_debt_no_interest_addback", "sources": []}
    else:
        try:
            tax_rate, tax_sources = _normalized_tax_rate(normalizer)
        except ValueError:
            tax_rate, tax_sources = .21, ()
            tax_fallback = True
        if not .05 <= tax_rate <= .30:
            tax_rate = .21
            tax_fallback = True
        current_cash = cash_fcff_from_reported(
            operating_cash_flow=float(flows["operating_cash_flow"]["value"]),
            capital_expenditures=float(flows["capital_expenditures"]["value"]) + (float(flows["software_development"]["value"]) if ticker == "ROP" else 0.),
            spectrum_investment=0.,
            interest_expense=abs(float(flows["interest_expense"]["value"])),
            tax_rate=tax_rate,
        )
        annual = _annual_with_software(normalizer) if ticker == "ROP" else _annual_cash_with_losses(normalizer)[2]
    sources = [dict(source) for flow in flows.values() for source in flow.get("sources", [])]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(
        annual_cash_states=annual,
        ttm_revenue=revenue,
        ttm_cash_fcff=current_cash,
        ttm_period_end=policy.period,
        ttm_sources=sources,
        valuation_date=BATCH_29_VALUATION_DATE,
    )
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if cash_metric is None or growth_metric is None or not profile.full_history:
        raise ValueError(f"{ticker}: history unavailable")
    margins = tuple(max(.001, float(value)) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    cash_reinvestment_adjustment = (0., 0., 0.)
    if ticker == "INTU":
        cash_reinvestment_adjustment = (554_666_666.6666666, 416_000_000., 0.)
        margins = tuple(max(.001, margins[index] - cash_reinvestment_adjustment[index] / revenue) for index in range(3))
    growth = (
        max(-.10, min(policy.growth[0], growth_metric.low)),
        max(-.08, min(policy.growth[1], growth_metric.base)),
        max(0., min(policy.growth[2], growth_metric.high)),
    )
    rows = []
    traces = {}
    scenario_claims = policy.claims
    future_lease_schedule = None
    if ticker == "NVDA":
        lease_years = (8, 12, 20)
        lease_total = 32_400_000_000.
        annual_lease = tuple(lease_total / years for years in lease_years)
        lease_present_value = tuple(sum(annual_lease[index] / ((1 + policy.wacc[index]) ** year) for year in range(1, lease_years[index] + 1)) for index in range(3))
        scenario_claims = tuple(policy.claims[index] + lease_present_value[index] for index in range(3))
        future_lease_schedule = {"reported_total": lease_total, "expected_commencement_window": "fiscal_2027_q2_through_fiscal_2033", "governed_payment_years": lease_years, "annual_payment": annual_lease, "present_value_reserve": lease_present_value, "treatment": "Scenario-timed present-value reserve deducted once; existing commenced leases remain post-rent operating items."}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(
            revenue * margins[index],
            growth[index],
            policy.terminal[index],
            policy.wacc[index],
            policy.cash[index],
            policy.debt,
            0.,
            scenario_claims[index],
            policy.shares[index],
        )
        trace = enterprise_cash_flow_dcf(
            state,
            forecast_years=FORECAST_YEARS,
            allow_nonpositive_equity_trace=True,
        )
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({
            "name": name,
            "conditional_value_per_share": max(0., raw),
            "raw_value_per_share": raw,
            "starting_cash_fcff": state.cash_fcff,
            "cash_conversion_margin": margins[index],
            "growth": growth[index],
            "wacc": policy.wacc[index],
            "terminal_growth": policy.terminal[index],
            "cash_and_investments": policy.cash[index],
            "debt_and_finance_leases": policy.debt,
            "other_equity_claims": scenario_claims[index],
            "shares": policy.shares[index],
            "limited_liability_floor_applied": raw < 0,
        })
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: invalid range")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(
        accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"],
        scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"],
        model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons,
    )
    public_history = profile.public_metadata()
    if not is_pass:
        public_history.update({"normalization_basis": "company_history_with_named_material_dependency", "assumption_source_mix": "reported_history_and_finsight_policy"})
    assumptions = {
        **public_history,
        "forecast_years": FORECAST_YEARS,
        "cash_conversion_margin": margins,
        "growth": growth,
        "wacc": policy.wacc,
        "terminal_growth": policy.terminal,
        "cash_and_investments": policy.cash,
        "claims": scenario_claims,
        "cash_reinvestment_adjustment": cash_reinvestment_adjustment,
        "shares": policy.shares,
        "tax_rate_basis": "source-proven no debt; no interest addback" if ticker == "FFIV" else "governed 21% fallback" if tax_fallback else "normalized filing history",
        "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0 else "not applied",
        "calculator_calibration": "Calculator is calibrated to the exact faded-cash base.",
        "invalidation": policy.invalidation,
    }
    if future_lease_schedule is not None:
        assumptions["future_not_commenced_lease_schedule"] = future_lease_schedule
    if ticker == "ROP":
        assumptions["indicor_nonoperating_asset_range"] = (1_300_000_000., 1_546_100_000., 1_792_200_000.)
    if ticker == "TRMB":
        assumptions["nonoperating_investment_overlay"] = (0., 345_700_000., 617_400_000.)
    if ticker == "NTAP":
        assumptions["purchase_commitment_coverage"] = {"reported_total": 1_400_000_000., "due_fiscal_2027": 1_100_000_000., "current_cash_and_investments": 3_584_000_000., "ttm_cash_fcff": current_cash, "treatment": "Operating purchase commitments are covered by current liquidity and post-cost cash conversion; not deducted again as debt."}
    if ticker == "NVDA":
        assumptions["operating_commitment_coverage"] = {"manufacturing_supply_capacity": 119_000_000_000., "cloud_services": 30_000_000_000., "other_vendors": 6_000_000_000., "treatment": "These inputs procure supply, capacity, and R&D services that support forecast revenue. Bear/base/bull use post-cost historical cash margins and growth fade; no second financing claim is deducted."}
    baseline = BaselineValuation(
        ticker=ticker,
        method=policy.method,
        method_version=BATCH_29_HISTORY_VERSION,
        low=scenario["low"], base=scenario["base"], high=scenario["high"],
        confidence=reliability.label,
        availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL,
        key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and current cash conversion anchors the range."),),
        warnings=(policy.warning, policy.invalidation),
        confidence_reasons=tuple(reliability.reasons),
        calculator_link=f"/api/us-valuations/{ticker}/calculator",
    )
    reported_reinvestment = float(flows["capital_expenditures"]["value"]) + (float(flows["software_development"]["value"]) if ticker == "ROP" else 0.)
    bridge_reconciliation = {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": scenario_claims, "other_equity_claim_formula": policy.bridge_formula, "shares": policy.shares, "operating_liability_treatment": "Operating leases, supplier obligations, customer funds, warranties, and ordinary working capital remain inside operating cash conversion and are not deducted twice."}
    if future_lease_schedule is not None:
        bridge_reconciliation["future_not_commenced_lease_schedule"] = future_lease_schedule
    if ticker == "NVDA":
        bridge_reconciliation["infrastructure_fund_maximum_loss_exposure_treatment"] = "The $2.3B maximum loss exposure includes invested and future committed infrastructure-fund amounts already covered by reported investments, asset haircuts, and the $27B investment-commitment reserve; no second claim is deducted."
        bridge_reconciliation["operating_commitment_coverage"] = assumptions["operating_commitment_coverage"]
    if ticker == "NTAP":
        bridge_reconciliation["purchase_commitment_coverage"] = assumptions["purchase_commitment_coverage"]
    result = {
        "ticker": ticker,
        "method": policy.method,
        "model_version": BATCH_29_HISTORY_VERSION,
        "availability_type": "available" if is_pass else "conditional_estimate",
        "scenario_rows": rows,
        "scenario_range": scenario,
        "reported_inputs": {"ttm_revenue": revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": reported_reinvestment, "ttm_interest": flows["interest_expense"]["value"], "tax_rate": tax_rate, "ttm_cash_fcff": current_cash},
        "governed_assumptions": assumptions,
        "history_reliability": reliability.as_dict(),
        "source_ledger": {
            "controlling_filing": filing,
            "flow_sources": flows,
            "annual_cash_sources": list(annual),
            "tax_rate_sources": list(tax_sources),
            "tax_rate_treatment": {"fallback_applied": tax_fallback, "rate": tax_rate},
            "company_history_profile": profile.as_private_dict(),
            "bridge_sources": _bridge(ticker, structural, policy),
            "event_sources": _events(ticker, filing, structural, policy, package, source_receipt),
            "bridge_reconciliation": bridge_reconciliation,
            "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces},
            "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False},
        },
        "warning": policy.warning,
        "baseline": baseline.as_private_dict(),
    }
    if ticker in {"INTU", "NVDA", "FFIV"}:
        legal = {
            "INTU": ("free-tax-preparation and Ontario class-action/regulatory proceedings", "No filed loss range is inserted; the operating range separately deducts business-loan reinvestment."),
            "NVDA": ("certified securities-class and related derivative litigation", "No filed legal loss is inserted; reported tax, guarantee, lease, investment, and Groq claims are modeled separately."),
            "FFIV": ("customer, third-party, and government claims related to the October 2025 cyber incident", "Reported response costs and insurance recoveries remain in cash history; no unavailable future claim is inserted."),
        }[ticker]
        result = apply_unquantified_legal_tail_policy(result, model_version=BATCH_29_HISTORY_VERSION, matter_summary=legal[0], recorded_claim_treatment=legal[1], invalidation=policy.invalidation)
        combined_warning = f"{policy.warning} {result['warning']}"
        result["warning"] = combined_warning
        baseline_private = dict(result["baseline"])
        baseline_private["warnings"] = [combined_warning, policy.invalidation]
        result["baseline"] = baseline_private
    return result


if set(P) != set(BATCH_29_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_29_TICKERS):
    raise RuntimeError("Batch 29 policy mismatch")
