"""History-backed practical baselines for controlled Universe Reset Batch 30."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point, _source_proven_no_other_equity_claims
from .batch_05_launch_first import _source_proven_no_debt
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _no_preferred
from .batch_16_history import _share_point
from .batch_30 import BATCH_30_TICKERS, BATCH_30_VALUATION_DATE
from .history import build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_30_HISTORY_VERSION = "BATCH-30-TECHNOLOGY-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"TDY", "BR"})
CONDITIONAL_TICKERS = frozenset({"CTSH", "ON", "STX", "FTNT", "FSLR", "MPWR", "PLTR", "TEL"})
WITHHELD_TICKERS = frozenset()


def _shares(weighted: float, current: float) -> tuple[float, float, float]:
    high, low = max(weighted, current), min(weighted, current)
    return high, (high + low) / 2, low


def _cash(value: float) -> tuple[float, float, float]:
    return value, value, value


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


P = {
    "CTSH": Policy("post_acquisition_it_services_faded_fcff", "2026-06-30", _cash(1_157_000_000.), 1_560_000_000., (25_000_000.,) * 3, _shares(472_000_000., 450_444_209.), (0., .04, .07), (.11, .095, .085), (.01, .02, .025), "Conditional Low post-acquisition IT-services baseline. Current H1 facts are structurally repaired, while $1.334B acquisition cash, acquired goodwill/intangibles, contingent consideration, restructuring, and the new debt/share state remain material.", "Invalidate if acquired cash conversion, restructuring, contingent consideration, litigation settlement state, debt, investments, or diluted shares changes materially.", "$1.038B cash plus $13M short- and $106M long-term investments; $1.527B long-term plus $33M short-term debt; $25M reported contingent consideration deducted once."),
    "TDY": Policy("instrumentation_aerospace_cash_faded_fcff", "2026-06-28", _cash(340_100_000.), 2_027_000_000., (5_700_000.,) * 3, _shares(46_900_000., 46_355_673.), (.01, .05, .09), (.105, .09, .08), (.01, .02, .025), "Source-bounded instrumentation/aerospace baseline. Five-year cash history, current acquisition scale, debt, environmental accrual, preferred/NCI absence, warranty cash, and shares reconcile.", "Invalidate if aerospace/instrument demand, acquisition conversion, debt, environmental/warranty claims, or diluted shares changes materially.", "$340.1M cash less $2.027B current/noncurrent debt and $5.7M environmental accrual. Current acquisition cash is consolidated and not deducted again."),
    "ON": Policy("pre_synaptics_semiconductor_cycle_faded_fcff", "2026-07-03", _cash(3_864_500_000.), 4_459_400_000., (132_900_000.,) * 3, (404_400_000., 396_855_860.5, 389_311_721.), (-.05, .03, .08), (.12, .105, .095), (0., .01, .02), "Conditional Low pre-Synaptics semiconductor baseline. The pending stock-and-cash merger remains separate, while restructuring/impairment, debt, NCI, contingent consideration, manufacturing actions, and cycle recovery remain material.", "Invalidate if the Synaptics transaction closes, terminates, or changes; or if cycle cash, restructuring, debt/leases, NCI, contingent consideration, or diluted shares changes materially.", "$3.5145B cash plus $350M short-term investments; $4.4594B debt/capital-lease total; $19.8M NCI plus $113.1M contingent consideration. Pending merger consideration/termination fees are not probability-weighted."),
    "STX": Policy("storage_hardware_cycle_faded_fcff", "2026-07-03", _cash(1_704_000_000.), 3_565_000_000., (120_000_000.,) * 3, _shares(229_000_000., 226_644_518.), (-.05, .08, .15), (.12, .105, .095), (0., .01, .02), "Conditional Low storage-cycle baseline. Five-year history contains the downturn and recovery; current cash, debt, purchase commitments, preferred absence, and shares reconcile. Two separately typed $45M and $75M legal-claim contexts are summed conservatively, but their overlap cannot yet be disproven. The wrapper's impossible future diagnostic date is never used.", "Invalidate if the legal-claim contexts prove overlapping, or if storage demand/pricing, cash conversion, debt, loss contingencies, purchase commitments, or diluted shares changes materially.", "$1.704B cash less $185M current and $3.380B noncurrent debt, plus $45M and $75M source-reported loss-contingency contexts deducted conservatively. Operating purchase commitments remain in forward cash conversion."),
    "FTNT": Policy("network_security_growth_faded_fcff", "2026-06-30", _cash(4_468_700_000.), 496_900_000., (0.,) * 3, _shares(741_300_000., 733_713_653.), (.05, .12, .18), (.105, .09, .08), (.01, .02, .025), "Conditional Low network-security baseline. Cash history is strong, while $1.6671B of inventory commitments, real-estate expansion, high growth, deferred-revenue conversion, and review-grade investment scope remain material.", "Invalidate if security growth/cash conversion, inventory commitments, data-center expansion, investment classification, debt, or diluted shares changes materially.", "$2.9349B cash plus the reported $1.1347B other short-term and $399.1M long-term investment captions; $496.9M noncurrent debt. Investment classification remains review-grade and is a Conditional release condition. The $62.1M real-estate purchase is inside reported capex and is not deducted twice."),
    "FSLR": Policy("governed_solar_manufacturing_cash_range", "2026-06-30", _cash(1_726_964_000.), 74_501_000., (223_700_000., 198_700_000., 158_700_000.), (107_732_000., 107_600_894., 107_469_788.), (0., .08, .15), (.12, .10, .09), (0., .01, .02), "Conditional Low governed solar-manufacturing baseline. Four of five historical cash years were negative; the 0.5%/3%/10% cash-conversion range is a deliberately conservative FinSight policy assumption—not a source-reported contract or capacity model—while tax-credit economics, capacity expansion, unpaid capex, litigation, and government policy remain material.", "Invalidate if contracted bookings, module pricing, Section 45X/government grants, manufacturing ramp, capex/payables, litigation, debt/leases, or diluted shares changes materially.", "$1.688279B cash plus $38.685M unrestricted AFS securities; $37.635M debt plus $36.866M finance leases. Claims include $21.8M litigation reserve, $65M/$40M/$0 possible excess loss, and $136.9M unpaid capex. The operating margin range is a FinSight assumption pending a full capacity/backlog model."),
    "MPWR": Policy("debt_free_power_semiconductor_faded_fcff", "2026-06-30", _cash(1_413_786_000.), 0., (0.,) * 3, (49_260_000., 49_201_500., 49_143_000.), (.05, .15, .22), (.11, .095, .085), (.01, .02, .025), "Conditional Low debt-free power-semiconductor baseline. Five-year owner-cash history, complete cash/investments, debt absence, purchase-obligation coverage, warranties, and current shares reconcile, but $94.282M of H1 stock compensation remains inside operating cash flow and future dilution is only bounded by the current share range.", "Invalidate if semiconductor growth/margins, stock compensation/dilution, purchase obligations, capex, debt absence, investments, warranties, or diluted shares changes materially.", "$1.005587B cash plus $408.174M current and $25K long-term investments; source-proven no debt. Interest income is not treated as an expense addback. Stock compensation remains in historical owner cash and is disclosed as a Conditional dilution dependency."),
    "PLTR": Policy("high_growth_software_commitment_adjusted_faded_fcff", "2026-06-30", _cash(9_409_099_000.), 0., (110_690_000.,) * 3, _shares(2_569_826_000., 2_402_897_000.), (.10, .20, .30), (.12, .10, .09), (0., .015, .025), "Conditional Low high-growth software baseline. Cash generation is strong, while $5.6B of long-term commitments, $466.801M of H1 stock compensation retained in operating cash flow, future dilution, customer concentration, high growth fade, NCI, and marketable-security scope remain material.", "Invalidate if growth/cash conversion, purchase commitments, stock compensation/net dilution, NCI, investments, customer concentration, or debt absence changes materially.", "$2.030047B balance-sheet cash plus $7.379052B balance-sheet marketable securities; source-proven no debt; $110.69M NCI deducted once. The $7.591790B AFS total overlaps $396.828M cash equivalents and $7.194962B marketable debt securities and is diagnostic only. Stock compensation remains in historical owner cash and is a Conditional forward-dilution dependency."),
    "BR": Policy("outsourced_processing_cash_faded_fcff", "2026-06-30", _cash(636_300_000.), 3_254_600_000., (59_900_000.,) * 3, _shares(117_100_000., 114_021_798.), (.02, .06, .08), (.105, .09, .08), (.01, .02, .025), "Source-bounded outsourced-processing baseline. Five-year cash history, investments, debt, acquisition/contingent consideration, operating commitments, preferred/NCI absence, and shares reconcile.", "Invalidate if processing volumes, acquisition conversion, contingent consideration, commitments, debt, investments, or diluted shares changes materially.", "$402.9M cash plus $0.9M current and $232.5M noncurrent marketable securities; $3.2546B debt; $59.9M contingent consideration deducted once. Other long-term investments are conservatively excluded."),
    "TEL": Policy("pre_astrodyne_connectivity_cycle_faded_fcff", "2026-06-26", _cash(1_239_000_000.), 5_632_000_000., (324_000_000.,) * 3, _shares(295_000_000., 289_513_228.), (0., .05, .09), (.105, .09, .08), (.01, .02, .025), "Conditional Low pre-Astrodyne connectivity baseline. The pending approximately $1.4B cash acquisition remains separate, while current acquisitions, restructuring, contingent consideration, debt, redeemable NCI, environmental exposure, and cycle mix remain material.", "Invalidate if Astrodyne closes, terminates, or changes; or if acquisition conversion, restructuring, debt, NCI, environmental/contingent claims, or diluted shares changes materially.", "$1.239B cash less $102M current and $5.530B noncurrent debt; $147M redeemable NCI, $150M contingent consideration, and $27M environmental accrual deducted once. Pending Astrodyne cash is not deducted or probability-weighted."),
}


POINT = {
    "CTSH": (("CashAndCashEquivalentsAtCarryingValue", 1_038_000_000.), ("ShortTermInvestments", 13_000_000.), ("LongTermInvestments", 106_000_000.), ("LongTermDebtNoncurrent", 1_527_000_000.), ("ShortTermBorrowings", 33_000_000.)),
    "TDY": (("CashAndCashEquivalentsAtCarryingValue", 340_100_000.), ("LongTermDebtCurrent", 100_000.), ("LongTermDebtNoncurrent", 2_026_900_000.), ("AccrualForEnvironmentalLossContingencies", 5_700_000.)),
    "ON": (("CashAndCashEquivalentsAtCarryingValue", 3_514_500_000.), ("ShortTermInvestments", 350_000_000.), ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities", 4_459_400_000.), ("MinorityInterest", 19_800_000.), ("BusinessCombinationContingentConsiderationLiability", 113_100_000.)),
    "STX": (("CashAndCashEquivalentsAtCarryingValue", 1_704_000_000.), ("LongTermDebtCurrent", 185_000_000.), ("LongTermDebtNoncurrent", 3_380_000_000.)),
    "FTNT": (("CashAndCashEquivalentsAtCarryingValue", 2_934_900_000.), ("OtherShortTermInvestments", 1_134_700_000.), ("LongTermInvestments", 399_100_000.), ("DebtSecuritiesAvailableForSaleAndEquitySecurities", 1_533_800_000.), ("LongTermDebtNoncurrent", 496_900_000.)),
    "FSLR": (("CashAndCashEquivalentsAtCarryingValue", 1_688_279_000.), ("AvailableForSaleSecuritiesDebtSecuritiesCurrent", 38_685_000.), ("DebtCurrent", 37_635_000.), ("FinanceLeaseLiability", 36_866_000.), ("LitigationReserveCurrent", 21_800_000.)),
    "MPWR": (("CashAndCashEquivalentsAtCarryingValue", 1_005_587_000.), ("ShortTermInvestments", 408_174_000.), ("LongTermInvestments", 25_000.)),
    "PLTR": (("CashAndCashEquivalentsAtCarryingValue", 2_030_047_000.), ("MarketableSecuritiesCurrent", 7_379_052_000.), ("AvailableForSaleSecuritiesDebtSecurities", 7_591_790_000.), ("MinorityInterest", 110_690_000.)),
    "BR": (("CashAndCashEquivalentsAtCarryingValue", 402_900_000.), ("MarketableSecuritiesCurrent", 900_000.), ("MarketableSecuritiesNoncurrent", 232_500_000.), ("LongTermDebt", 3_254_600_000.), ("BusinessCombinationContingentConsiderationLiability", 59_900_000.)),
    "TEL": (("CashAndCashEquivalentsAtCarryingValue", 1_239_000_000.), ("DebtCurrent", 102_000_000.), ("LongTermDebtNoncurrent", 5_530_000_000.), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 147_000_000.), ("AccrualForEnvironmentalLossContingencies", 27_000_000.)),
}

WEIGHTED = {"CTSH": 472_000_000., "TDY": 46_900_000., "ON": 401_500_000., "STX": 229_000_000., "FTNT": 741_300_000., "FSLR": 107_677_000., "MPWR": 49_251_000., "PLTR": 2_569_826_000., "BR": 117_100_000., "TEL": 295_000_000.}
START = {"CTSH": "2026-01-01", "TDY": "2025-12-29", "ON": "2026-01-01", "STX": "2025-06-28", "FTNT": "2026-01-01", "FSLR": "2026-01-01", "MPWR": "2026-01-01", "PLTR": "2026-01-01", "BR": "2025-07-01", "TEL": "2025-09-27"}
CURRENT = {"CTSH": 450_444_209., "TDY": 46_355_673., "ON": 389_311_721., "STX": 226_644_518., "FTNT": 733_713_653., "FSLR": 107_469_788., "MPWR": 49_143_000., "PLTR": 2_402_897_000., "BR": 114_021_798., "TEL": 289_513_228.}
END = {"CTSH": "2026-07-24", "TDY": "2026-07-15", "ON": "2026-07-29", "STX": "2026-07-31", "FTNT": "2026-07-28", "FSLR": "2026-07-24", "MPWR": "2026-07-29", "BR": "2026-07-31", "TEL": "2026-07-20"}
QUARTER_DILUTED = {"ON": (404_400_000., "2026-04-04", "2026-07-03"), "FSLR": (107_732_000., "2026-04-01", "2026-06-30"), "MPWR": (49_260_000., "2026-04-01", "2026-06-30")}


def _fact(structural, name, value, start, end, allow_dimensions=False):
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") == start and row.get("period_end") == end and (allow_dimensions or not row.get("dimensions")) and isinstance(row.get("value"), (int, float)) and float(row["value"]) == value]
    if not rows:
        raise ValueError(f"{name}={value} absent")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "filed": structural.get("filed_date"), "period_start": start, "period_end": end, "concept": row.get("qname"), "unit": row.get("unit"), "value": value, "dimensions": row.get("dimensions", []), "reported_vs_estimated": "reported"}


def _point_unit(structural, name, value, period):
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") is None and row.get("period_end") == period and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and float(row["value"]) == value]
    if not rows:
        raise ValueError(f"{name}={value} absent")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "period_end": period, "concept": row.get("qname"), "unit": row.get("unit"), "value": value, "reported_vs_estimated": "reported"}


def _bridge(ticker, structural, policy):
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT[ticker]]
    rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=WEIGHTED[ticker], period_start=START[ticker], period_end=policy.period))
    if ticker == "PLTR":
        rows.append(_point_unit(structural, "CommonStockSharesOutstanding", CURRENT[ticker], policy.period))
    else:
        rows.append(_share_point(structural, expected=CURRENT[ticker], end=END[ticker]))
    if ticker in QUARTER_DILUTED:
        value, start, end = QUARTER_DILUTED[ticker]
        rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=value, period_start=start, period_end=end))
    rows.append(_no_preferred(structural, policy.period))
    if ticker not in {"ON", "PLTR", "TEL"}:
        rows.append(_source_proven_no_other_equity_claims(structural, period_end=policy.period))
    if ticker in {"MPWR", "PLTR"}:
        rows.append(_source_proven_no_debt(structural, period_end=policy.period))
    diagnostic_concepts = {"FTNT": "DebtSecuritiesAvailableForSaleAndEquitySecurities", "PLTR": "AvailableForSaleSecuritiesDebtSecurities"}
    if ticker in diagnostic_concepts:
        suffix = f":{diagnostic_concepts[ticker]}"
        for row in rows:
            if str(row.get("concept", "")).endswith(suffix):
                row["used_in_arithmetic"] = False
                row["coverage_role"] = "diagnostic_overlap_proof"
            elif row.get("concept") and row.get("unit") == "USD":
                row["used_in_arithmetic"] = True
    return rows


def _events(ticker, filing, structural, policy, package, source_receipt):
    rows = [{"source_kind": "finsight_model_policy", "period_end": filing["period_end"], "matter": policy.warning, "reported_vs_estimated": "finsight_assumption"}]
    specs = {
        "CTSH": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 1_334_000_000., "2026-01-01", "2026-06-30", False), ("BusinessCombinationContingentConsiderationLiability", 25_000_000., None, "2026-06-30", True), ("RestructuringCharges", 84_000_000., "2026-01-01", "2026-06-30", False), ("LitigationSettlementAmountAwardedFromOtherParty", 298_000_000., "2026-03-27", "2026-03-27", True)),
        "TDY": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 53_400_000., "2025-12-29", "2026-06-28", False), ("AccrualForEnvironmentalLossContingencies", 5_700_000., None, "2026-06-28", False)),
        "ON": (("BusinessCombinationContingentConsiderationLiability", 113_100_000., None, "2026-07-03", False), ("RestructuringCostsAndAssetImpairmentCharges", 370_500_000., "2026-01-01", "2026-07-03", False)),
        "STX": (("LossContingencyAccrualAtCarryingValue", 45_000_000., None, "2026-07-03", True), ("LossContingencyAccrualAtCarryingValue", 75_000_000., None, "2026-07-03", True), ("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 547_000_000., None, "2026-07-03", False)),
        "FTNT": (("InventoryPurchaseObligation", 1_667_100_000., None, "2026-06-30", False), ("PaymentsToAcquireProductiveAssets", 62_100_000., "2026-01-01", "2026-06-30", False)),
        "FSLR": (("LitigationReserveCurrent", 21_800_000., None, "2026-06-30", False), ("LossContingencyEstimateOfPossibleLoss", 40_000_000., None, "2026-06-30", True), ("LossContingencyEstimateOfPossibleLoss", 65_000_000., None, "2026-06-30", True)),
        "MPWR": (("PurchaseObligation", 571_036_000., None, "2026-06-30", False), ("PurchaseObligationDueInNextTwelveMonths", 313_075_000., None, "2026-06-30", False), ("ShareBasedCompensation", 94_282_000., "2026-01-01", "2026-06-30", False)),
        "PLTR": (("LongTermPurchaseCommitmentAmount", 5_600_000_000., "2026-01-03", "2026-06-30", True), ("ShareBasedCompensation", 466_801_000., "2026-01-01", "2026-06-30", False)),
        "BR": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 282_700_000., "2025-07-01", "2026-06-30", False), ("BusinessCombinationContingentConsiderationLiability", 59_900_000., None, "2026-06-30", False), ("MinimumCommitmentTotal", 868_500_000., None, "2026-06-30", False), ("MinimumCommitmentYearOne", 238_200_000., None, "2026-06-30", False), ("MinimumCommitmentYearTwo", 207_100_000., None, "2026-06-30", False), ("MinimumCommitmentYearThree", 173_300_000., None, "2026-06-30", False), ("MinimumCommitmentYearFour", 132_700_000., None, "2026-06-30", False), ("MinimumCommitmentYearFive", 81_600_000., None, "2026-06-30", False), ("MinimumCommitmentAfterFifthYear", 35_500_000., None, "2026-06-30", False)),
        "TEL": (("PaymentsToAcquireBusinessesNetOfCashAcquired", 200_000_000., "2025-09-27", "2026-06-26", False), ("BusinessCombinationContingentConsiderationLiabilityNoncurrent", 150_000_000., None, "2026-06-26", True)),
    }
    rows.extend(_fact(structural, name, value, start, end, allow_dimensions) for name, value, start, end, allow_dimensions in specs.get(ticker, ()))
    manual = {
        "CTSH": {"acquisition_cash": 1_334_000_000., "contingent_consideration": 25_000_000., "restructuring_charge": 84_000_000., "litigation_settlement_awarded_from_other_party": 298_000_000., "litigation_treatment": "Under appeal and explicitly not recognized as a gain until realizable; not added to cash/value and not deducted as a liability."},
        "ON": {"economic_state": "pre_synaptics_merger", "expected_close": "mid_2027", "synaptics_termination_fee": 235_000_000., "on_regulatory_termination_fee": 320_000_000.},
        "STX": {"loss_contingency_claims": [45_000_000., 75_000_000.], "wrapper_period_end": structural.get("period_end"), "wrapper_period_used": False},
        "FTNT": {"inventory_commitment": 1_667_100_000., "remainder_of_2026": 1_337_500_000., "thereafter": 329_600_000., "real_estate_purchase_inside_capex": 62_100_000.},
        "FSLR": {"unpaid_capex": 136_900_000., "possible_loss_range": [40_000_000., 65_000_000.], "historical_cash_years_negative": 4},
        "PLTR": {"long_term_purchase_commitment": 5_600_000_000., "debt_state": "source_proven_absent"},
        "TEL": {"economic_state": "pre_astrodyne", "pending_cash_consideration": 1_400_000_000., "signed": "2026-07-22", "expected_close": "calendar_2026_end"},
    }
    if ticker in manual:
        locators = {"CTSH": "Legal Proceedings—Syntel appeal; Business Combinations; Project Leap", "ON": "Note 1—Synaptics Merger Agreement; restructuring and impairment notes", "STX": "Legal, Environmental and Other Contingencies; Purchase Obligations", "FTNT": "Note 5—Property and Equipment; Note 10—Commitments", "FSLR": "Commitments and Contingencies; capex payable and litigation notes", "PLTR": "Note 7—Commitments and Contingencies", "TEL": "Note 17—Subsequent Event (Astrodyne TDI)"}
        rows.append({"source_kind": "controlling_filing_reported_terms", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "source_locator": locators[ticker], "reported_terms": manual[ticker], "reported_vs_estimated": "reported_terms_with_governed_treatment"})
    primary_name = package.get("primary_document")
    primary = next((item for item in package.get("files", []) if item.get("local_path") == primary_name), None)
    if not isinstance(primary, dict) or not primary.get("sha256") or not primary.get("source_url"):
        raise ValueError(f"{ticker}: primary filing provenance unavailable")
    provenance = {"primary_document": primary_name, "source_url": primary["source_url"], "document_sha256": primary["sha256"], "package_manifest_sha256": source_receipt["package_manifest_sha256"]}
    for row in rows:
        if row.get("source_kind") not in {"structural_xbrl", "finsight_model_policy"}:
            row.update(provenance)
    return rows


def _ctsh_flows(normalizer, structural):
    specs = {
        "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", 10_894_000_000., 10_360_000_000.),
        "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities", 832_000_000., 798_000_000.),
        "capital_expenditures": ("PaymentsToAcquirePropertyPlantAndEquipment", 175_000_000., 144_000_000.),
        "interest_expense": ("InterestExpenseNonoperating", 20_000_000., 21_000_000.),
    }
    result = {}
    for field, (concept, current, prior) in specs.items():
        annual_source = dict(normalizer.ttm_flow(field)["sources"][0])
        current_source = _structural_flow(structural, name=concept, start="2026-01-01", end="2026-06-30", expected=current)
        prior_source = _structural_flow(structural, name=concept, start="2025-01-01", end="2025-06-30", expected=prior)
        result[field] = {"field": field, "value": annual_source["value"] + current - prior, "period_end": "2026-06-30", "method": "latest_fy_plus_structural_current_ytd_minus_prior_ytd", "sources": [annual_source, current_source, prior_source], "current_ytd": current_source, "prior_ytd": prior_source}
    return result


def _annual_no_interest(normalizer):
    rows = []
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        capex = normalizer.annual_at_end("capital_expenditures", operating.end)
        revenue = normalizer.annual_at_end("revenue", operating.end)
        if capex is None or revenue is None or revenue.value <= 0:
            continue
        rows.append({"period_end": operating.end, "operating_cash_flow": operating.as_dict(), "capital_expenditures": capex.as_dict(), "interest_expense": None, "pretax_income": None, "income_tax": None, "revenue": revenue.as_dict(), "cash_fcff": operating.value - capex.value, "formula": "OCF - capex; source-proven no debt, so no interest addback"})
    return tuple(rows)


def build_batch_30_history_result(*, ticker: str, source_root: Path, structural_root: Path):
    if ticker not in BATCH_30_TICKERS:
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
    if ticker == "CTSH":
        flows = _ctsh_flows(normalizer, structural)
    else:
        names = ("revenue", "operating_cash_flow", "capital_expenditures") if ticker in {"MPWR", "PLTR"} else ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")
        flows = {name: normalizer.ttm_flow(name) for name in names}
    tax_sources = ()
    tax_fallback = False
    if ticker in {"MPWR", "PLTR"}:
        tax_rate = 0.
        current_cash = float(flows["operating_cash_flow"]["value"]) - float(flows["capital_expenditures"]["value"])
        annual = _annual_no_interest(normalizer)
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
        current_cash = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0., interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
        annual = _annual_cash_with_losses(normalizer)[2]
    sources = [dict(source) for flow in flows.values() for source in flow.get("sources", [])]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=current_cash, ttm_period_end=policy.period, ttm_sources=sources, valuation_date=BATCH_30_VALUATION_DATE)
    cash_metric, growth_metric = profile.metric("cash_conversion_margin"), profile.metric("revenue_growth")
    if cash_metric is None or growth_metric is None or not profile.full_history:
        raise ValueError(f"{ticker}: history unavailable")
    margins = tuple(max(.001, float(value)) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    if ticker == "FSLR":
        margins = (.005, .03, .10)
    growth = (max(-.10, min(policy.growth[0], growth_metric.low)), max(-.08, min(policy.growth[1], growth_metric.base)), max(0., min(policy.growth[2], growth_metric.high)))
    rows, traces = [], {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(revenue * margins[index], growth[index], policy.terminal[index], policy.wacc[index], policy.cash[index], policy.debt, 0., policy.claims[index], policy.shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "conditional_value_per_share": max(0., raw), "raw_value_per_share": raw, "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": policy.wacc[index], "terminal_growth": policy.terminal[index], "cash_and_investments": policy.cash[index], "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims[index], "shares": policy.shares[index], "limited_liability_floor_applied": raw < 0})
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
    assumptions = {**public_history, "forecast_years": FORECAST_YEARS, "cash_conversion_margin": margins, "growth": growth, "wacc": policy.wacc, "terminal_growth": policy.terminal, "cash_and_investments": policy.cash, "claims": policy.claims, "shares": policy.shares, "assumption_classification": {"cash_conversion_margin": "finsight_assumption" if ticker == "FSLR" else "historically_derived", "growth": "history_bounded_finsight_assumption", "wacc": "finsight_assumption", "terminal_growth": "finsight_assumption", "cash_debt_claims_and_shares": "reported_or_governed_range"}, "tax_rate_basis": "source-proven no debt; no interest addback" if ticker in {"MPWR", "PLTR"} else "governed 21% fallback" if tax_fallback else "normalized filing history", "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator is calibrated to the exact faded-cash base.", "invalidation": policy.invalidation}
    if ticker in {"CTSH", "TDY", "ON", "BR", "TEL"}:
        assumptions["acquisition_reinvestment_treatment"] = {"current_state": "Reported acquisitions are consolidated into the current issuer and current cash/debt/share bridge.", "forecast_treatment": "Growth is capped by reported history and the governed issuer range; no additional acquisition-driven growth is invented.", "bridge_treatment": "Acquisition consideration exchanged for acquired operating assets is not deducted again as an equity loss.", "invalidation": "A future material acquisition, changed consideration, or acquired cash-conversion evidence requires a new valuation state."}
    coverage = {
        "STX": {"reported_total": 547_000_000., "current_cash": 1_704_000_000., "ttm_cash_fcff": current_cash},
        "FTNT": {"reported_total": 1_667_100_000., "near_term": 1_337_500_000., "current_cash_and_investments": 4_468_700_000., "ttm_cash_fcff": current_cash},
        "MPWR": {"reported_total": 571_036_000., "next_twelve_months": 313_075_000., "current_cash_and_investments": 1_413_786_000., "ttm_cash_fcff": current_cash},
        "PLTR": {"reported_total": 5_600_000_000., "current_cash_and_investments": 9_409_099_000., "ttm_cash_fcff": current_cash},
        "BR": {"reported_total": 868_500_000., "year_one": 238_200_000., "year_two": 207_100_000., "year_three": 173_300_000., "year_four": 132_700_000., "year_five": 81_600_000., "after_fifth_year": 35_500_000., "schedule_sum": 868_400_000., "rounding_difference": 100_000., "current_cash_and_investments": 636_300_000., "ttm_cash_fcff": current_cash},
    }.get(ticker)
    if coverage:
        assumptions["operating_commitment_coverage"] = {**coverage, "treatment": "Operating commitments remain inside post-cost cash conversion and are not deducted again as financing debt."}
    if ticker == "PLTR":
        assumptions["marketable_securities_coverage"] = {"balance_sheet_cash": 2_030_047_000., "balance_sheet_marketable_securities": 7_379_052_000., "afs_total_diagnostic": 7_591_790_000., "afs_in_cash_equivalents": 396_828_000., "afs_in_marketable_securities": 7_194_962_000., "covered_fields": ["CashAndCashEquivalentsAtCarryingValue", "MarketableSecuritiesCurrent"], "treatment": "Use balance-sheet captions once; retain the overlapping AFS note total only as coverage proof."}
    if ticker == "FTNT":
        assumptions["investment_coverage"] = {"other_short_term_investments": 1_134_700_000., "long_term_investments": 399_100_000., "aggregate_diagnostic": 1_533_800_000., "covered_fields": ["OtherShortTermInvestments", "LongTermInvestments"], "fallback_level": "reported_components_review_grade"}
    if ticker == "STX":
        assumptions["loss_contingency_treatment"] = {"reported_claims": [45_000_000., 75_000_000.], "source_context_ids": ["c-303", "c-304"], "treatment": "The two separately typed filing contexts are summed conservatively because their dimension labels are opaque in the parser.", "invalidation": "If the filing proves the contexts overlap, replace the conservative sum and regenerate the valuation."}
    if ticker == "MPWR":
        assumptions["stock_compensation_treatment"] = {"reported_h1_stock_compensation": 94_282_000., "cash_flow_treatment": "Retained in the reported operating-cash-flow history rather than falsely treated as a cash expense.", "dilution_treatment": "Current weighted and outstanding share facts bound the present denominator; no unsupported future issuance is invented.", "release_condition": "Conditional until recurring stock compensation is normalized against forward net dilution or buybacks."}
    if ticker == "PLTR":
        assumptions["stock_compensation_treatment"] = {"reported_h1_stock_compensation": 466_801_000., "cash_flow_treatment": "Retained in the reported operating-cash-flow history rather than falsely treated as a cash expense.", "dilution_treatment": "Current weighted and outstanding share facts bound the present denominator; no unsupported future issuance is invented.", "release_condition": "Conditional until recurring stock compensation is normalized against forward net dilution or buybacks."}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_30_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and current cash conversion anchors the range."),), warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    bridge_reconciliation = {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "other_equity_claim_formula": policy.bridge_formula, "shares": policy.shares, "operating_liability_treatment": "Operating leases, supplier obligations, deferred revenue, warranties, and ordinary working capital remain inside operating cash conversion and are not deducted twice."}
    if coverage:
        bridge_reconciliation["operating_commitment_coverage"] = assumptions["operating_commitment_coverage"]
    if ticker == "PLTR":
        bridge_reconciliation["marketable_securities_coverage"] = assumptions["marketable_securities_coverage"]
    if ticker == "FTNT":
        bridge_reconciliation["investment_coverage"] = assumptions["investment_coverage"]
    period_diagnostic = {"value": structural.get("period_end"), "used_for_selection": False}
    if ticker == "STX":
        period_diagnostic.update({"rejected_reason": "Wrapper diagnostic conflicts with the source receipt report date and no fact selection uses it.", "selection_basis": "Controlling source-receipt report date plus exact fact periods.", "controlling_report_date": policy.period})
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_30_HISTORY_VERSION, "availability_type": "available" if is_pass else "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "tax_rate": tax_rate, "ttm_cash_fcff": current_cash}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "tax_rate_treatment": {"fallback_applied": tax_fallback, "rate": tax_rate}, "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge(ticker, structural, policy), "event_sources": _events(ticker, filing, structural, policy, package, source_receipt), "bridge_reconciliation": bridge_reconciliation, "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces}, "structural_top_level_period_diagnostic": period_diagnostic}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


if set(P) != set(BATCH_30_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_30_TICKERS):
    raise RuntimeError("Batch 30 policy mismatch")
