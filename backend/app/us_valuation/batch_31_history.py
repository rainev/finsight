"""History-backed practical baselines for controlled Universe Reset Batch 31."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json
from pathlib import Path

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point, _source_proven_no_other_equity_claims
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _no_preferred
from .batch_16_history import _share_point
from .batch_31 import BATCH_31_TICKERS, BATCH_31_VALUATION_DATE
from .history import build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_31_HISTORY_VERSION = "BATCH-31-TECHNOLOGY-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"CDW", "VRSK"})
CONDITIONAL_TICKERS = frozenset({"PANW", "WDAY", "NOW", "SMCI", "NXPI", "ACN", "CRWD"})
WITHHELD_TICKERS = frozenset({"ORCL"})


def _shares(high: float, low: float) -> tuple[float, float, float]:
    return high, (high + low) / 2, low


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: float
    claims: float
    shares: tuple[float, float, float]
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str
    bridge_formula: str


P = {
    "PANW": Policy("post_cyberark_security_platform_faded_fcff", "2026-04-30", 6_992_000_000., 1_352_000_000., 390_000_000., (815_000_000., 808_000_000., 801_000_000.), (.06, .14, .20), (.11, .095, .085), (.01, .02, .025), "Conditional Low post-acquisition security-platform baseline. Current cash history is finite, while $4.563B acquisition cash, $18.862B issued/issuable equity consideration, acquired goodwill, $8.529B purchase obligations, $1.314B YTD SBC, contingent consideration, and legal claims remain material.", "Invalidate if acquired cash conversion, purchase accounting, commitments, SBC/net dilution, debt, contingent consideration, claims, or shares changes materially.", "$2.364B cash plus $747M short- and $3.881B long-term investments; $160M current and $1.192B noncurrent convertible debt; $240M contingent consideration plus $150M loss contingency deducted once."),
    "WDAY": Policy("subscription_software_sbc_faded_fcff", "2026-04-30", 4_353_000_000., 2_988_000_000., 0., _shares(268_117_000., 254_313_000.), (.04, .10, .15), (.105, .09, .08), (.01, .02, .025), "Conditional Low subscription-software baseline. Five-year cash history is finite, while $409M quarterly SBC, the rapid share-count change, repurchase funding, debt, and acquisition-intangible conversion remain material.", "Invalidate if subscription cash conversion, SBC/net dilution, repurchases, debt, investments, acquired-intangible economics, or shares changes materially.", "$559M cash plus $3.794B current marketable securities; $998M current and $1.990B noncurrent debt. Equity and other long-term investments are conservatively excluded."),
    "ORCL": Policy("unavailable_cloud_infrastructure_commitment_model", "2026-05-31", 31_894_000_000., 137_242_000_000., 5_502_000_000., _shares(2_914_000_000., 2_880_471_000.), (0., 0., 0.), (.12, .105, .095), (0., .01, .02), "Withheld. Oracle's current cloud/infrastructure state combines $55.663B annual capex, $39.973B construction in progress, $129.541B debt, $7.701B finance leases, $4.954B preferred equity, $13.309B purchase obligations, and $260B of not-yet-commenced lease commitments. Their timing and revenue support cannot be bounded by the ordinary fixed-cash model without guessing.", "Revalue after a source-bounded cloud/software/infrastructure schedule reconciles capex, lease starts, purchase obligations, debt/refinancing, preferred conversion, and supported cash flow.", "$31.289B cash plus $605M current AFS securities; $129.541B debt plus $7.701B finance leases; $4.954B preferred equity plus $548M NCI."),
    "NOW": Policy("post_acquisition_subscription_cloud_faded_fcff", "2026-06-30", 6_707_000_000., 7_517_000_000., 0., _shares(1_037_206_000., 1_034_000_000.), (.08, .15, .22), (.11, .095, .085), (.01, .02, .025), "Conditional Low post-acquisition subscription-cloud baseline. Five-year owner-cash history is finite, while $8.776B H1 acquisition cash, acquired goodwill, commercial paper/debt, $1.199B H1 SBC, $6.302B of timed cloud/IT purchase obligations, and the growth premium remain material.", "Invalidate if acquired conversion, purchase accounting, subscription growth/cash conversion, cloud/IT commitments, SBC/net dilution, securities, commercial paper/debt, or shares changes materially.", "$2.503B cash plus $4.204B AFS securities counted once; $5.435B long-term debt plus $2.082B short-term borrowings. The $2.073B other-long-term-investment caption overlaps the AFS noncurrent balance and is diagnostic only."),
    "SMCI": Policy("ai_server_working_capital_cycle_faded_fcff", "2026-03-31", 1_290_324_000., 4_113_744_000., 161_000., _shares(692_189_000., 601_418_482.), (-.10, .03, .10), (.13, .11, .10), (0., .01, .015), "Conditional Low AI-server cycle baseline. Five-year history contains both positive and negative owner cash, while current TTM cash is deeply negative from working-capital expansion; $10.1B purchase obligations, debt/convertible-note carrying scope, warranty, impairment, concentration, and SBC remain material.", "Invalidate if filing integrity, inventory/receivables/payables, AI-server demand, purchase commitments, debt/convertibles, warranty, impairment, SBC/dilution, or shares changes materially.", "$1.290324B cash; $4.113744B combined debt carrying amount; $0.161M NCI. A separate $4.659357B convertible-note caption is retained as a scope diagnostic, not added to the combined debt total. The $10.1B operating purchase obligation remains inside post-cost cash conversion."),
    "CDW": Policy("technology_distribution_working_capital_faded_fcff", "2026-06-30", 361_800_000., 5_817_000_000., 0., _shares(128_400_000., 125_017_426.), (-.03, .02, .05), (.105, .09, .08), (.01, .02, .025), "Source-bounded technology-distribution baseline. Four-year plus current cash history, cash, debt, leases, shares, ordinary working capital, repurchases, and immaterial acquisition cash reconcile.", "Invalidate if IT demand, gross margin, vendor terms, working-capital conversion, supplier finance, debt/leases, acquisitions, or shares changes materially.", "$361.8M cash; $1.0089B current and $4.8081B noncurrent debt. Operating leases and ordinary vendor working capital remain inside cash conversion."),
    "NXPI": Policy("post_divestiture_semiconductor_cycle_faded_fcff", "2026-06-28", 3_227_000_000., 10_976_000_000., 1_562_000_000., _shares(254_021_000., 252_164_174.), (-.05, .02, .07), (.115, .10, .09), (0., .01, .02), "Conditional Low post-divestiture semiconductor-cycle baseline. Current H1 lineage is structurally repaired, while $878M disposal proceeds/$627M gain, $1.2B infrastructure-investment obligation, $2.908B purchase obligations, restructuring, debt/commercial paper, NCI, SBC, and cycle mix remain material.", "Invalidate if disposal scope, infrastructure-investment overlap, purchase obligations, restructuring, automotive/industrial cycle cash, debt/commercial paper, NCI, SBC/dilution, or shares changes materially.", "$3.222B cash plus $5M marketable securities; $10.976B debt/capital leases; $362M NCI plus the $1.2B aggregate infrastructure-investment obligation deducted once. The $379M/$653M investee contexts are diagnostic components and not added again."),
    "VRSK": Policy("recurring_insurance_analytics_faded_fcff", "2026-06-30", 551_400_000., 4_473_500_000., 0., _shares(133_036_554., 130_156_012.), (0., .05, .08), (.105, .09, .08), (.01, .02, .025), "Source-bounded recurring analytics baseline. Five-year cash history and current cash, debt/finance leases, zero NCI, shares, repurchases, and ordinary data-platform operations reconcile.", "Invalidate if recurring retention/pricing, data-platform cash conversion, debt/leases, regulatory/customer concentration, acquisitions, or shares changes materially.", "$551.4M cash; $4.4735B combined current/noncurrent debt and finance leases; source-reported zero NCI."),
    "ACN": Policy("acquisition_active_it_consulting_faded_fcff", "2026-05-31", 10_171_567_000., 5_142_265_000., 1_617_147_000., _shares(621_337_104., 615_593_409.), (0., .05, .08), (.10, .085, .075), (.01, .02, .025), "Conditional Low acquisition-active IT-consulting baseline. Five-year cash history is finite, while $3.004B YTD acquisition cash, acquired goodwill, $1.645B YTD SBC, restructuring, labor utilization, FX, debt, and NCI remain material.", "Invalidate if acquired cash conversion, utilization/margins, discretionary IT demand, FX, restructuring, SBC/net dilution, debt, NCI, or shares changes materially.", "$10.165245B cash plus $6.322M short-term investments; $112.816M current plus $5.029449B long-term debt/leases; $1.123273B NCI plus $493.874M redeemable NCI. Long-term investments are excluded."),
    "CRWD": Policy("post_acquisition_cybersecurity_owner_cash_faded_fcff", "2026-04-30", 4_552_801_000., 745_843_000., 102_358_000., _shares(257_881_000., 254_564_820.), (.10, .20, .28), (.115, .10, .09), (.01, .02, .025), "Conditional Low post-acquisition cybersecurity baseline. Five-year cash history is finite, while $881.376M acquisition cash, acquired goodwill, $297.703M quarterly SBC, $2.722459B recorded/unrecorded purchase obligations, contingent consideration, claims, and high-growth fade remain material.", "Invalidate if acquired conversion, purchase accounting, cybersecurity growth/cash conversion, SBC/net dilution, purchase obligations, contingent consideration, claims, debt, NCI, or shares changes materially.", "$4.552801B unrestricted cash; $745.843M debt; $41.455M NCI, $43.8M contingent consideration, and $17.103M loss contingency deducted once. Restricted cash and equity-method investments are excluded."),
}


POINT = {
    "PANW": (("CashAndCashEquivalentsAtCarryingValue", 2_364_000_000.), ("ShortTermInvestments", 747_000_000.), ("LongTermInvestments", 3_881_000_000.), ("ConvertibleDebtCurrent", 160_000_000.), ("ConvertibleDebtNoncurrent", 1_192_000_000.), ("BusinessCombinationContingentConsiderationLiabilityCurrent", 124_000_000.), ("BusinessCombinationContingentConsiderationLiabilityNoncurrent", 116_000_000.), ("LossContingencyAccrualAtCarryingValue", 150_000_000.)),
    "WDAY": (("CashAndCashEquivalentsAtCarryingValue", 559_000_000.), ("MarketableSecuritiesCurrent", 3_794_000_000.), ("LongTermDebtCurrent", 998_000_000.), ("LongTermDebtNoncurrent", 1_990_000_000.)),
    "ORCL": (("CashAndCashEquivalentsAtCarryingValue", 31_289_000_000.), ("AvailableForSaleSecuritiesDebtSecuritiesCurrent", 605_000_000.), ("DebtLongtermAndShorttermCombinedAmount", 129_541_000_000.), ("FinanceLeaseLiability", 7_701_000_000.), ("PreferredStockValue", 4_954_000_000.), ("MinorityInterest", 548_000_000.)),
    "NOW": (("CashAndCashEquivalentsAtCarryingValue", 2_503_000_000.), ("AvailableForSaleSecuritiesDebtSecurities", 4_204_000_000.), ("LongTermDebt", 5_435_000_000.), ("ShortTermBorrowings", 2_082_000_000.)),
    "SMCI": (("CashAndCashEquivalentsAtCarryingValue", 1_290_324_000.), ("DebtLongtermAndShorttermCombinedAmount", 4_113_744_000.), ("MinorityInterest", 161_000.)),
    "CDW": (("CashAndCashEquivalentsAtCarryingValue", 361_800_000.), ("LongTermDebtCurrent", 1_008_900_000.), ("LongTermDebtNoncurrent", 4_808_100_000.)),
    "NXPI": (("CashAndCashEquivalentsAtCarryingValue", 3_222_000_000.), ("MarketableSecurities", 5_000_000.), ("DebtAndCapitalLeaseObligations", 10_976_000_000.), ("MinorityInterest", 362_000_000.), ("EquityMethodInvestmentsAdditionalInfrastructureInvestmentObligations", 1_200_000_000.)),
    "VRSK": (("CashAndCashEquivalentsAtCarryingValue", 551_400_000.), ("DebtLongtermAndShorttermCombinedAmount", 4_473_500_000.), ("MinorityInterest", 0.)),
    "ACN": (("CashAndCashEquivalentsAtCarryingValue", 10_165_245_000.), ("ShortTermInvestments", 6_322_000.), ("DebtCurrent", 112_816_000.), ("LongTermDebtAndCapitalLeaseObligations", 5_029_449_000.), ("MinorityInterest", 1_123_273_000.), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 493_874_000.)),
    "CRWD": (("CashAndCashEquivalentsAtCarryingValue", 4_552_801_000.), ("LongTermDebtNoncurrent", 745_843_000.), ("MinorityInterest", 41_455_000.), ("BusinessCombinationContingentConsiderationLiability", 43_800_000.), ("LossContingencyAccrualAtCarryingValue", 17_103_000.)),
}


def _point_unit(structural: dict, name: str, value: float, period: str) -> dict:
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") is None and row.get("period_end") == period and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and float(row["value"]) == value]
    if not rows:
        raise ValueError(f"{name}={value} absent")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "period_end": period, "concept": row.get("qname"), "unit": row.get("unit"), "value": value, "reported_vs_estimated": "reported"}


def _companyfacts_share_duration(facts: dict, *, expected: float, start: str, end: str) -> dict:
    rows = [row for row in facts.get("facts", {}).get("us-gaap", {}).get("WeightedAverageNumberOfDilutedSharesOutstanding", {}).get("units", {}).get("shares", []) if row.get("start") == start and row.get("end") == end and row.get("filed", "") <= BATCH_31_VALUATION_DATE and isinstance(row.get("val"), (int, float)) and float(row["val"]) == expected]
    if not rows:
        raise ValueError(f"companyfacts diluted shares {expected} absent")
    row = max(rows, key=lambda value: (value.get("filed", ""), value.get("accn", "")))
    return {"source_kind": "companyfacts", "accession": row.get("accn"), "filed": row.get("filed"), "form": row.get("form"), "period_start": start, "period_end": end, "concept": "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", "unit": "shares", "value": expected, "reported_vs_estimated": "reported"}


def _bridge(ticker: str, structural: dict, policy: Policy, facts: dict) -> list[dict]:
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT[ticker]]
    if ticker == "WDAY":
        rows.extend((_companyfacts_share_duration(facts, expected=268_117_000., start="2025-02-01", end="2026-01-31"), _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=254_313_000., period_start="2026-02-01", period_end="2026-04-30")))
    elif ticker == "ACN":
        rows.extend((_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=621_337_104., period_start="2025-09-01", period_end="2026-05-31"), _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=615_593_409., period_start="2026-03-01", period_end="2026-05-31")))
    else:
        specs = {
            "PANW": (744_000_000., "2025-08-01", 815_000_000., "2026-05-26"),
            "ORCL": (2_914_000_000., "2025-06-01", 2_880_471_000., "2026-06-12"),
            "NOW": (1_037_206_000., "2026-01-01", 1_034_000_000., "2026-06-30"),
            "SMCI": (673_598_000., "2025-07-01", 601_418_482., "2026-04-30"),
            "CDW": (128_400_000., "2026-01-01", 125_017_426., "2026-07-31"),
            "NXPI": (253_836_000., "2026-01-01", 252_164_174., "2026-07-24"),
            "VRSK": (133_036_554., "2026-01-01", 130_156_012., "2026-07-24"),
            "CRWD": (257_881_000., "2026-02-01", 254_564_820., "2026-05-28"),
        }
        weighted, start, current, end = specs[ticker]
        rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=weighted, period_start=start, period_end=policy.period))
        rows.append(_share_point(structural, expected=current, end=end))
        if ticker == "SMCI":
            rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=692_189_000., period_start="2026-01-01", period_end="2026-03-31"))
        if ticker == "NXPI":
            rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=254_021_000., period_start="2026-03-30", period_end="2026-06-28"))
        if ticker == "ORCL":
            rows.append(_duration(structural, name="IncrementalCommonSharesAttributableToShareBasedPaymentArrangements", expected=54_000_000., period_start="2025-06-01", period_end="2026-05-31"))
    if ticker != "ORCL":
        rows.append(_no_preferred(structural, policy.period))
    if ticker in {"PANW", "WDAY", "NOW", "CDW", "VRSK"}:
        rows.append(_source_proven_no_other_equity_claims(structural, period_end=policy.period))
    return rows


def _fact(structural: dict, name: str, value: float, start: str | None, end: str, allow_dimensions: bool = False) -> dict:
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") == start and row.get("period_end") == end and (allow_dimensions or not row.get("dimensions")) and isinstance(row.get("value"), (int, float)) and float(row["value"]) == value]
    if not rows:
        raise ValueError(f"{name}={value} absent")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "period_start": start, "period_end": end, "concept": row.get("qname"), "unit": row.get("unit"), "value": value, "dimensions": row.get("dimensions", []), "reported_vs_estimated": "reported"}


EVENT_SPECS = {
    "PANW": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 4_563_000_000., "2025-08-01", "2026-04-30", False), ("BusinessCombinationConsiderationTransferredEquityInterestsIssuedAndIssuable", 18_862_000_000., "2025-08-01", "2026-04-30", False), ("ShareBasedCompensation", 1_314_000_000., "2025-08-01", "2026-04-30", False), ("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 8_529_000_000., None, "2026-04-30", False), ("DebtSecuritiesAvailableForSaleExcludingAccruedInterest", 4_956_000_000., None, "2026-04-30", False)),
    "WDAY": (("ShareBasedCompensation", 409_000_000., "2026-02-01", "2026-04-30", False), ("PaymentsForRepurchaseOfCommonStock", 1_587_000_000., "2026-02-01", "2026-04-30", False)),
    "ORCL": (("ShareBasedCompensation", 4_811_000_000., "2025-06-01", "2026-05-31", False), ("LesseeOperatingLeaseLeaseNotYetCommencedLeaseCommitments", 260_000_000_000., None, "2026-05-31", False), ("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 13_309_000_000., None, "2026-05-31", False), ("RestructuringReserve", 653_000_000., None, "2026-05-31", False), ("UnrecognizedTaxBenefits", 10_126_000_000., None, "2026-05-31", False)),
    "NOW": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 8_776_000_000., "2026-01-01", "2026-06-30", False), ("ShareBasedCompensation", 1_199_000_000., "2026-01-01", "2026-06-30", False), ("OtherLongTermInvestments", 2_073_000_000., None, "2026-06-30", False), ("PurchaseObligationFutureMinimumPaymentsRemainderOfFiscalYear", 324_000_000., None, "2026-06-30", True), ("PurchaseObligationDueInNextTwelveMonths", 401_000_000., None, "2026-06-30", True), ("PurchaseObligationDueInSecondYear", 573_000_000., None, "2026-06-30", True), ("PurchaseObligationDueInThirdYear", 704_000_000., None, "2026-06-30", True), ("PurchaseObligationDueInFourthYear", 2_900_000_000., None, "2026-06-30", True), ("PurchaseObligationDueInSecondYear", 1_400_000_000., None, "2026-06-30", True), ("SupplierFinanceProgramObligation", 28_000_000., None, "2026-06-30", True)),
    "SMCI": (("ShareBasedCompensation", 305_558_000., "2025-07-01", "2026-03-31", False), ("PurchaseObligation", 10_100_000_000., None, "2026-03-31", False), ("StandardProductWarrantyAccrual", 23_767_000., None, "2026-03-31", False), ("AssetImpairmentCharges", 13_747_000., "2025-07-01", "2026-03-31", False), ("ConvertibleLongTermNotesPayable", 4_659_357_000., None, "2026-03-31", False)),
    "CDW": (("AllocatedShareBasedCompensationExpense", 50_200_000., "2026-01-01", "2026-06-30", False), ("PaymentsToAcquireBusinessesNetOfCashAcquired", 300_000., "2026-01-01", "2026-06-30", False)),
    "NXPI": (("ShareBasedCompensation", 214_000_000., "2026-01-01", "2026-06-28", False), ("PurchaseObligation", 2_908_000_000., None, "2026-06-28", False), ("ProceedsFromDivestitureOfBusinessesNetOfCashDivested", 878_000_000., "2026-01-01", "2026-06-28", False), ("GainLossOnDispositionOfAssets", 627_000_000., "2026-01-01", "2026-06-28", False), ("RestructuringReserve", 176_000_000., None, "2026-06-28", False)),
    "VRSK": (("ShareBasedCompensation", 33_100_000., "2026-01-01", "2026-06-30", False), ("PaymentsToAcquireBusinessesAndInterestInAffiliates", 0., "2026-01-01", "2026-06-30", False)),
    "ACN": (("PaymentsToAcquireBusinessesAndInterestInAffiliates", 3_004_003_000., "2025-09-01", "2026-05-31", False), ("ShareBasedCompensation", 1_644_518_000., "2025-09-01", "2026-05-31", False), ("RestructuringSettlementAndImpairmentProvisions", 307_541_000., "2025-09-01", "2026-05-31", False)),
    "CRWD": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 881_376_000., "2026-02-01", "2026-04-30", False), ("ShareBasedCompensation", 297_703_000., "2026-02-01", "2026-04-30", False), ("RecordedUnconditionalPurchaseObligation", 2_618_759_000., None, "2026-04-30", False), ("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 103_700_000., None, "2026-04-30", False)),
}


def _events(ticker: str, structural: dict, policy: Policy) -> list[dict]:
    rows = [{"source_kind": "finsight_model_policy", "period_end": policy.period, "matter": policy.warning, "reported_vs_estimated": "finsight_assumption"}]
    rows.extend(_fact(structural, name, value, start, end, allow_dimensions) for name, value, start, end, allow_dimensions in EVENT_SPECS[ticker])
    return rows


def _structural_ttm_flows(ticker: str, normalizer, structural: dict) -> dict:
    specs_by_ticker = {
        "NXPI": {
            "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", 6_677_000_000., 5_761_000_000.),
            "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities", 1_653_000_000., 1_344_000_000.),
            "capital_expenditures": ("PaymentsToAcquirePropertyPlantAndEquipment", 148_000_000., 222_000_000.),
            "interest_expense": ("InterestExpense", 226_000_000., 221_000_000.),
        },
        "VRSK": {
            "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", 1_588_900_000., 1_525_600_000.),
            "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities", 756_400_000., 689_200_000.),
            "capital_expenditures": ("PaymentsToAcquirePropertyPlantAndEquipment", 132_100_000., 109_500_000.),
            "interest_expense": ("InterestExpenseNonoperating", 96_000_000., 71_800_000.),
        },
    }
    specs = specs_by_ticker[ticker]
    current_start, prior_start = ("2026-01-01", "2025-01-01")
    current_end, prior_end = ("2026-06-28", "2025-06-29") if ticker == "NXPI" else ("2026-06-30", "2025-06-30")
    result = {}
    for field, (concept, current, prior) in specs.items():
        annual_source = dict(normalizer.ttm_flow(field)["sources"][0])
        current_source = _structural_flow(structural, name=concept, start=current_start, end=current_end, expected=current)
        prior_source = _structural_flow(structural, name=concept, start=prior_start, end=prior_end, expected=prior)
        result[field] = {"field": field, "value": annual_source["value"] + current - prior, "period_end": current_end, "method": "latest_fy_plus_structural_current_ytd_minus_prior_ytd", "sources": [annual_source, current_source, prior_source]}
    return result


def _annual_without_interest(normalizer) -> tuple[dict, ...]:
    rows = []
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        capex = normalizer.annual_at_end("capital_expenditures", operating.end)
        revenue = normalizer.annual_at_end("revenue", operating.end)
        if capex is None or revenue is None or revenue.value <= 0:
            continue
        rows.append({"period_end": operating.end, "operating_cash_flow": operating.as_dict(), "capital_expenditures": capex.as_dict(), "interest_expense": None, "pretax_income": None, "income_tax": None, "revenue": revenue.as_dict(), "cash_fcff": operating.value - capex.value, "formula": "OCF - capex; conservative history proxy because comparable annual interest facts are absent"})
    return tuple(rows)


def _issuer_normalizer(ticker: str, submissions: dict, facts: dict):
    if ticker != "CDW":
        return _normalizer(submissions, facts)
    config = copy.deepcopy(load_concept_config())
    config["fields"]["interest_expense"]["concepts"] = ["InterestPaidNet"]
    return _normalizer(submissions, facts, concept_config=config)


def build_batch_31_history_result(*, ticker: str, source_root: Path, structural_root: Path) -> dict:
    if ticker not in BATCH_31_TICKERS:
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
    normalizer = _issuer_normalizer(ticker, submissions, facts)
    flows = _structural_ttm_flows(ticker, normalizer, structural) if ticker in {"NXPI", "VRSK"} else {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    try:
        tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    except ValueError:
        tax_rate, tax_sources = .21, ()
    tax_fallback = not .05 <= tax_rate <= .30
    if tax_fallback:
        tax_rate = .21
    current_cash = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0., interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
    annual = _annual_without_interest(normalizer) if ticker == "NOW" else _annual_cash_with_losses(normalizer)[2]
    sources = [dict(source) for flow in flows.values() for source in flow.get("sources", [])]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=current_cash, ttm_period_end=policy.period, ttm_sources=sources, valuation_date=BATCH_31_VALUATION_DATE)
    cash_metric, growth_metric = profile.metric("cash_conversion_margin"), profile.metric("revenue_growth")

    if ticker == "ORCL":
        baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_31_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(policy.warning, policy.invalidation))
        return {"ticker": ticker, "method": policy.method, "model_version": BATCH_31_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {"ttm_revenue": revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "tax_rate": tax_rate, "ttm_cash_fcff": current_cash}, "governed_assumptions": {"history_policy_version": profile.policy_version, "history_years_used": profile.history_years_used, "normalization_basis": "cloud_software_infrastructure_schedule_required", "assumption_source_mix": "reported_history_with_unbounded_infrastructure_timing", "invalidation": policy.invalidation}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge(ticker, structural, policy, facts), "event_sources": _events(ticker, structural, policy), "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "other_equity_claim_formula": policy.bridge_formula, "shares": policy.shares}, "model_gap": {"required_route": "segmented_cloud_software_infrastructure_fcff", "missing_bounded_schedules": ["capex commissioning and depreciation", "not-yet-commenced lease start and duration", "purchase-obligation timing", "debt refinancing", "preferred conversion", "supported incremental cash flow"], "zero_substitution": False}, "package_provenance": {"package_manifest_sha256": source_receipt["package_manifest_sha256"], "primary_document": package.get("primary_document")}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}

    if cash_metric is None or growth_metric is None or not profile.full_history:
        raise ValueError(f"{ticker}: history unavailable")
    margins = tuple(max(.001, float(value)) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    if ticker == "SMCI":
        margins = (.005, .025, .07)
    growth = (max(-.10, min(policy.growth[0], growth_metric.low)), max(-.08, min(policy.growth[1], growth_metric.base)), max(0., min(policy.growth[2], growth_metric.high)))
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(revenue * margins[index], growth[index], policy.terminal[index], policy.wacc[index], policy.cash, policy.debt, 0., policy.claims, policy.shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "conditional_value_per_share": max(0., raw), "raw_value_per_share": raw, "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": policy.wacc[index], "terminal_growth": policy.terminal[index], "cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "shares": policy.shares[index], "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: invalid range")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons)
    public_history = profile.public_metadata()
    if not is_pass:
        public_history.update({"normalization_basis": "company_history_with_named_material_dependency", "assumption_source_mix": "reported_history_and_finsight_policy"})
    assumptions = {**public_history, "forecast_years": FORECAST_YEARS, "cash_conversion_margin": margins, "growth": growth, "wacc": policy.wacc, "terminal_growth": policy.terminal, "cash_and_investments": (policy.cash,) * 3, "claims": (policy.claims,) * 3, "shares": policy.shares, "assumption_classification": {"cash_conversion_margin": "finsight_assumption" if ticker == "SMCI" else "historically_derived", "growth": "history_bounded_finsight_assumption", "wacc": "finsight_assumption", "terminal_growth": "finsight_assumption", "cash_debt_claims_and_shares": "reported_or_governed_range"}, "tax_rate_basis": "governed 21% fallback" if tax_fallback else "normalized filing history", "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator is calibrated to the exact faded-cash base.", "invalidation": policy.invalidation}
    if ticker in {"PANW", "WDAY", "NOW", "SMCI", "NXPI", "ACN", "CRWD"}:
        assumptions["named_dependency_treatment"] = {"treatment": policy.warning, "release_condition": policy.invalidation}
    if ticker == "CDW":
        assumptions["interest_basis"] = {"concept": "InterestPaidNet", "ttm_value": flows["interest_expense"]["value"], "treatment": "Cash interest paid is the issuer-consistent addback lineage for the cash-FCFF history; no mixed-sign net-interest concept is used."}
    commitment = {
        "PANW": {"reported_total": 8_529_000_000.},
        "NOW": {"reported_cloud_and_it_schedule_total": 6_302_000_000., "supplier_finance_obligation": 28_000_000.},
        "SMCI": {"reported_total": 10_100_000_000.},
        "NXPI": {"reported_purchase_obligations": 2_908_000_000., "separately_deducted_infrastructure_obligation": 1_200_000_000.},
        "CRWD": {"reported_recorded": 2_618_759_000., "reported_unrecorded": 103_700_000., "reported_total": 2_722_459_000.},
    }.get(ticker)
    if commitment:
        assumptions["commitment_coverage"] = {**commitment, "current_cash_and_investments": policy.cash, "ttm_cash_fcff": current_cash, "treatment": "Operating purchase commitments remain inside post-cost cash conversion and are not deducted again as financing debt; separately identified investment obligations are deducted once."}
    if ticker == "PANW":
        assumptions["investment_coverage"] = {"used_components": {"short_term_investments": 747_000_000., "long_term_investments": 3_881_000_000.}, "used_total": 4_628_000_000., "afs_aggregate_diagnostic": 4_956_000_000., "excluded_residual": 328_000_000., "treatment": "Use the non-overlapping balance-sheet captions and exclude the unexplained aggregate residual conservatively."}
    if ticker == "NOW":
        assumptions["investment_coverage"] = {"used_afs_total": 4_204_000_000., "other_long_term_investments_diagnostic": 2_073_000_000., "treatment": "The other-long-term caption substantially matches the $2.043B AFS noncurrent component and is excluded to avoid double counting."}
    if ticker == "SMCI":
        assumptions["debt_scope_diagnostic"] = {"used_combined_carrying_amount": 4_113_744_000., "convertible_note_caption": 4_659_357_000., "treatment": "The combined debt carrying amount controls arithmetic; the larger convertible-note caption is retained as a scope diagnostic pending note-by-note reconciliation."}
    if ticker in {"PANW", "WDAY", "NOW", "SMCI", "NXPI", "ACN", "CRWD"}:
        sbc = {"PANW": 1_314_000_000., "WDAY": 409_000_000., "NOW": 1_199_000_000., "SMCI": 305_558_000., "NXPI": 214_000_000., "ACN": 1_644_518_000., "CRWD": 297_703_000.}[ticker]
        assumptions["stock_compensation_treatment"] = {"reported_current_stock_compensation": sbc, "cash_flow_treatment": "Retained in reported operating cash flow.", "dilution_treatment": "Current weighted/share facts bound the present denominator; unsupported future issuance is not invented.", "release_condition": "Conditional until recurring SBC is normalized against forward net dilution or offsetting buybacks."}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_31_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and current cash conversion anchors the range."),), warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    bridge_reconciliation = {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "other_equity_claim_formula": policy.bridge_formula, "shares": policy.shares, "operating_liability_treatment": "Operating leases, supplier obligations, deferred revenue, warranties, purchase commitments, SBC, and ordinary working capital remain inside operating cash conversion unless explicitly reserved once."}
    if commitment:
        bridge_reconciliation["commitment_coverage"] = assumptions["commitment_coverage"]
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_31_HISTORY_VERSION, "availability_type": "available" if is_pass else "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "tax_rate": tax_rate, "ttm_cash_fcff": current_cash}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge(ticker, structural, policy, facts), "event_sources": _events(ticker, structural, policy), "bridge_reconciliation": bridge_reconciliation, "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces}, "package_provenance": {"package_manifest_sha256": source_receipt["package_manifest_sha256"], "primary_document": package.get("primary_document")}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False, "selection_basis": "source receipt report date plus exact fact periods"}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


if set(P) != set(BATCH_31_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_31_TICKERS):
    raise RuntimeError("Batch 31 policy mismatch")
