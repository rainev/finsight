"""History-backed practical baselines for controlled Universe Reset Batch 32."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_16_history import _share_point
from .batch_30_history import _fact, _point_unit
from .batch_32 import BATCH_32_TICKERS, BATCH_32_VALUATION_DATE
from .history import build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_32_HISTORY_VERSION = "BATCH-32-TECHNOLOGY-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"GDDY"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_32_TICKERS) - PASS_TICKERS)
WITHHELD_TICKERS = frozenset()


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: tuple[float, float, float]
    debt: float
    claims: tuple[float, float, float]
    shares: tuple[float, float, float]
    margin: tuple[float, float, float] | None
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str
    bridge_formula: str


def _same(value: float) -> tuple[float, float, float]:
    return (value, value, value)


P = {
    "DDOG": Policy(
        "convertible_debt_cloud_observability_faded_fcff", "2026-06-30", _same(4_985_438_000.),
        985_545_000., _same(0.), (371_023_000., 368_271_000., 359_075_024.), None,
        (.05, .12, .18), (.11, .095, .085), (.01, .02, .025),
        "Conditional Low cloud-observability baseline. Five-year cash history is strong, while current stock compensation, convertible-note/capped-call economics, multi-class shares, and high growth fade remain material.",
        "Invalidate if recurring stock compensation/net dilution, convertible settlement, capped-call coverage, cash/securities, debt, or cash conversion leaves the stated range.",
        "$434.957M cash plus $4.550481B current AFS securities, less $985.545M convertible-note carrying value; capped calls are not valued separately.",
    ),
    "KEYS": Policy(
        "post_acquisition_electronic_measurement_faded_fcff", "2026-04-30", _same(2_581_000_000.),
        2_531_000_000., _same(39_000_000.), (173_000_000., 172_000_000., 170_895_368.), None,
        (-.016, .044, .084), (.11, .095, .085), (.01, .02, .025),
        "Conditional Low electronic-measurement baseline. Five-year history is source-backed, while recent acquired/divested businesses, integration costs, stock compensation, purchase obligations, and the current debt bridge remain material.",
        "Invalidate if acquisition/divestiture scope, acquired cash conversion, integration costs, purchase obligations, debt, or diluted shares changes materially.",
        "$2.412B cash plus $169M long-term investments, less $699M current and $1.832B noncurrent debt and the $39M deferred-compensation liability tied to the investment program; restricted cash is excluded.",
    ),
    "GDDY": Policy(
        "domain_and_hosting_subscription_faded_fcff", "2026-06-30", _same(1_155_500_000.),
        3_774_400_000., _same(0.), (132_766_000., 129_800_000., 126_834_000.), None,
        (.04, .07, .077), (.11, .095, .085), (.01, .02, .025),
        "Source-bounded Low domain-and-hosting baseline. Five-year cash conversion, reported cash, debt, preferred absence, and shrinking share count reconcile. A cutoff-safe post-period amendment replaced the $1.0B revolver with a $1.2B facility but reported no new borrowing; leverage and registry cash reserves remain ordinary scenario risks.",
        "Invalidate if subscription retention, cash conversion, debt, cash restriction, stock compensation/net dilution, or diluted shares changes materially.",
        "$1.1555B cash and cash equivalents less $15M current and $3.7594B noncurrent net debt. The $3.8169B gross debt principal is diagnostic, not a second claim; the new revolver was undrawn.",
    ),
    "LITE": Policy(
        "post_equitization_optical_cycle_faded_fcff", "2026-03-28", _same(2_738_400_000.),
        1_637_400_000., _same(0.), (101_100_000., 95_200_000., 91_500_000.), (.005, .0454, .12),
        (.05, .20, .35), (.12, .105, .095), (0., .01, .02),
        "Conditional Low optical-cycle baseline updated through the August 11 earnings release. Negative cycle years remain in the governed cash range; the latest bridge captures the completed note equitization, current common/preferred shares, and debt, while customer concentration, purchase commitments, acquired operations, and remaining conversion dilution remain material.",
        "Invalidate if note conversion/settlement, preferred conversion, purchase commitments, customer concentration, acquired cash conversion, cash, debt, or shares changes materially.",
        "August 11 release: $2.0435B cash plus $694.9M short-term investments, less $1.5969B current and $40.5M noncurrent debt. Every scenario exceeds the latest 88.6M common plus 2.9M one-for-one preferred shares; the $7.7566B debt-extinguishment loss is noncash and not subtracted again.",
    ),
    "HPE": Policy(
        "mixed_enterprise_technology_finance_conservative_fcff", "2026-04-30", _same(6_123_000_000.),
        20_496_000_000., (195_760_161.03343195, 196_744_325.67042312, 197_413_737.82283366), (1_447_371_521., 1_429_815_521., 1_400_259_521.), None,
        (0., .03, .06), (.115, .10, .09), (0., .01, .02),
        "Conditional Low mixed enterprise-technology/finance baseline. All reported debt is deducted conservatively and financing receivables are not added as surplus cash; mandatory-convertible dilution, Financial Services, acquisition integration, inventory conversion, and commitments remain material.",
        "Invalidate if Financial Services funding/receivable scope, preferred conversion, inventory conversion, debt, acquisitions, or diluted shares leaves the stated range.",
        "$5.292B April cash plus $224M AFS securities, plus $1.357B May H3C sale proceeds and less the $750M May term-loan repayment; debt falls from $21.246B to $20.496B. Claims include $61M NCI and the scenario PV of five $28.59375M preferred dividends. The 76.056M–93.168M mandatory-conversion range enters every share denominator; financing receivables stay inside operations.",
    ),
    "VRT": Policy(
        "post_acquisition_data_center_infrastructure_faded_fcff", "2026-06-30", _same(3_110_600_000.),
        2_939_800_000., _same(222_500_000.), (392_746_991., 392_511_287., 384_988_173.), None,
        (.08, .15, .20), (.115, .095, .085), (.01, .02, .025),
        "Conditional Low data-center-infrastructure baseline. History spans a loss year and current acceleration; PurgeRite/other acquisitions, contingent consideration, restructuring, order conversion, and high growth fade remain material.",
        "Invalidate if data-center demand/order conversion, acquired cash conversion, contingent consideration, restructuring, debt, investments, or diluted shares changes materially.",
        "$2.8106B cash plus $300M current held-to-maturity securities, less $2.9398B debt and the full $222.5M current contingent-consideration liability once.",
    ),
    "AVGO": Policy(
        "post_vmware_semiconductor_infrastructure_software_faded_fcff", "2026-05-03", _same(19_628_000_000.),
        64_907_000_000., (29_000_000_000., 0., 0.), (4_882_000_000., 4_879_000_000., 4_757_580_198.), None,
        (.05, .12, .18), (.105, .09, .08), (.01, .02, .025),
        "Conditional Low semiconductor/infrastructure-software baseline. Five-year cash history is strong, while VMware integration, $128.11B of operating purchase obligations, $164.6B RPO, stock compensation, leverage, growth fade, and a customer-lease backstop with $29B maximum exposure remain material. The bear case deducts that maximum; base/bull assume customer performance without probability-weighting it.",
        "Invalidate if integration, recurring stock compensation/net dilution, RPO conversion, purchase obligations, debt, cash, or diluted shares changes materially.",
        "$19.628B cash less $2.252B current and $62.655B noncurrent debt. The bear case deducts the separately reported $29B maximum backstop exposure. Operating purchase obligations remain inside forward cash conversion and are not deducted again as financing debt.",
    ),
    "MRVL": Policy(
        "post_acquisition_ai_connectivity_cycle_faded_fcff", "2026-05-02", _same(3_983_700_000.),
        4_961_300_000., _same(647_600_000.), (907_200_000., 901_900_000., 896_600_000.), None,
        (0., .12, .20), (.115, .10, .09), (0., .01, .02),
        "Conditional Low post-acquisition AI-connectivity baseline. Celestial/XConn consideration, contingent cash and share consideration, NVIDIA preferred conversion, stock compensation, supply capacity, and acquired cash conversion remain material.",
        "Invalidate if acquisition accounting/cash conversion, contingent consideration or shares, preferred conversion, supply commitments, debt, investments, or diluted shares changes materially.",
        "$3.8436B cash plus $140.1M other long-term investments, less $4.9613B debt and the full $647.6M fair-value contingent-consideration liability. The liability already includes cash and share components, so the 22.4M contingent acquisition shares are not added again; only the 21.8M preferred conversion shares plus ordinary award dilution enter the denominator. The $81.1M forward-stock-purchase asset is excluded conservatively.",
    ),
    "SNDK": Policy(
        "post_spin_storage_cycle_governed_fcff", "2026-04-03", (6_183_600_000., 6_539_000_000., 6_539_000_000.),
        0., _same(131_000_000.), (157_000_000., 155_000_000., 149_000_000.), (.01, .08, .16),
        (-.10, .05, .10), (.12, .105, .095), (0., .01, .02),
        "Conditional Low post-spin storage-cycle baseline updated through the August 5 full-year release. Three negative annual cash observations and the current sharp recovery are retained through a governed 1%/8%/16% cash-conversion range; purchase obligations, related-party fab commitments, the tax indemnity, marketable-security volatility, and limited standalone history remain material.",
        "Invalidate if storage pricing/cycle cash, purchase or fab commitments, tax indemnity, debt absence, cash, or diluted shares leaves the stated range.",
        "August 5 release: $4.762B cash plus $1.777B marketable equity securities (20% bear haircut), source-reported zero debt, and a $131M tax-indemnification claim. Flash Ventures assets stay inside operations. The new $14B buyback is an authorization, not an obligation or cash deduction.",
    ),
    "Q": Policy(
        "post_separation_electronics_materials_governed_fcff", "2026-06-30", _same(961_000_000.),
        4_020_000_000., _same(339_000_000.), (210_300_000., 209_750_000., 209_208_543.), (.08, .14, .20),
        (0., .05, .10), (.12, .105, .095), (0., .01, .02),
        "Conditional Low post-separation electronics-materials baseline. Three carve-out annual periods plus current comparative cash anchor a governed range; new debt interest, parent transfers, NCI, environmental claims, preferred stock, and limited standalone history remain material.",
        "Invalidate if standalone cash conversion, separation adjustments, debt/interest, NCI, environmental or preferred claims, investments, or diluted shares changes materially.",
        "$961M cash less $23M current and $3.997B noncurrent debt; $285M NCI, $52M environmental accrual, and $2M preferred value are deducted once. Long-term investments/receivables are conservatively excluded.",
    ),
}


POINTS = {
    "DDOG": (("CashAndCashEquivalentsAtCarryingValue", 434_957_000.), ("AvailableForSaleSecuritiesDebtSecuritiesCurrent", 4_550_481_000.), ("ConvertibleLongTermNotesPayable", 985_545_000.)),
    "KEYS": (("CashAndCashEquivalentsAtCarryingValue", 2_412_000_000.), ("LongTermInvestments", 169_000_000.), ("LongTermDebtCurrent", 699_000_000.), ("LongTermDebtNoncurrent", 1_832_000_000.)),
    "GDDY": (("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 1_155_500_000.), ("LongTermDebtCurrent", 15_000_000.), ("LongTermDebtNoncurrent", 3_759_400_000.), ("DebtInstrumentCarryingAmount", 3_816_900_000.)),
    "LITE": (("CashAndCashEquivalentsAtCarryingValue", 2_617_800_000.), ("AvailableForSaleSecuritiesDebtSecurities", 554_500_000.), ("DebtLongtermAndShorttermCombinedAmount", 3_281_800_000.), ("PreferredStockSharesOutstanding", 2_900_000.)),
    "HPE": (("CashAndCashEquivalentsAtCarryingValue", 5_292_000_000.), ("AvailableForSaleSecuritiesDebtSecurities", 224_000_000.), ("DebtLongtermAndShorttermCombinedAmount", 21_246_000_000.), ("StockholdersEquityAttributableToNoncontrollingInterestContinuingOperations", 61_000_000.), ("PreferredStockSharesOutstanding", 30_000_000.)),
    "VRT": (("CashAndCashEquivalentsAtCarryingValue", 2_810_600_000.), ("DebtSecuritiesHeldToMaturityAmortizedCostAfterAllowanceForCreditLossCurrent", 300_000_000.), ("LongTermDebt", 2_939_800_000.), ("ContingentConsiderationLiabilityCurrent", 222_500_000.)),
    "AVGO": (("CashAndCashEquivalentsAtCarryingValue", 19_628_000_000.), ("LongTermDebt", 64_907_000_000.)),
    "MRVL": (("CashAndCashEquivalentsAtCarryingValue", 3_843_600_000.), ("OtherLongTermInvestments", 140_100_000.), ("LongTermDebt", 4_961_300_000.), ("BusinessCombinationContingentConsiderationLiabilityNoncurrent", 647_600_000.), ("PreferredStockSharesOutstanding", 2_000_000.), ("PreferredStockConvertibleSharesIssuable", 21_800_000.)),
    "SNDK": (("CashAndCashEquivalentsAtCarryingValue", 3_735_000_000.), ("LongTermDebt", 0.), ("TaxLiabilityIndemnification", 131_000_000.)),
    "Q": (("CashAndCashEquivalentsAtCarryingValue", 961_000_000.), ("DebtCurrent", 23_000_000.), ("LongTermDebtAndCapitalLeaseObligations", 3_997_000_000.), ("MinorityInterest", 285_000_000.), ("AccrualForEnvironmentalLossContingencies", 52_000_000.), ("PreferredStockValue", 2_000_000.)),
}


WEIGHTED = {
    "DDOG": (368_271_000., "2026-01-01"), "KEYS": (173_000_000., "2025-11-01"), "GDDY": (132_766_000., "2026-01-01"),
    "LITE": (87_400_000., "2025-06-29"), "HPE": (1_356_000_000., "2025-11-01"), "VRT": (392_511_287., "2026-01-01"),
    "AVGO": (4_882_000_000., "2025-11-03"), "MRVL": (893_300_000., "2026-02-01"), "SNDK": (154_000_000., "2025-06-28"), "Q": (210_300_000., "2026-01-01"),
}


CURRENT = {
    "KEYS": (170_895_368., "2026-05-29"), "GDDY": (126_647_704., "2026-07-24"), "LITE": (77_800_000., "2026-04-30"),
    "HPE": (1_324_203_521., "2026-05-26"), "VRT": (384_988_173., "2026-07-27"), "AVGO": (4_757_580_198., "2026-05-29"),
    "MRVL": (874_800_000., "2026-05-21"), "SNDK": (148_089_758., "2026-04-24"), "Q": (209_208_543., "2026-07-31"),
}


def _normalizer_for(ticker: str, submissions: dict[str, Any], facts: dict[str, Any]):
    if ticker != "Q":
        return _normalizer(submissions, facts)
    config = copy.deepcopy(load_concept_config())
    config["fields"]["interest_expense"]["concepts"] = ["InterestAndDebtExpense"]
    return _normalizer(submissions, facts, concept_config=config)


def _release_flow(event: dict[str, Any], field: str, value: float, concept: str) -> dict[str, Any]:
    source = {"source_kind": "sec_earnings_release", "field": field, "concept": concept, "unit": "USD", "value": value, "accession": event["accession"], "filed": event["filed"], "end": event["period_end"], "source_url": event["source_url"], "document_sha256": event["document_sha256"], "value_status": "reported_unaudited"}
    return {"field": field, "value": value, "period_end": event["period_end"], "method": "latest_cutoff_safe_earnings_release", "sources": [source]}


def _hpe_current_interest(normalizer, structural: dict[str, Any]) -> dict[str, Any]:
    annual_source = dict(normalizer.ttm_flow("interest_expense")["sources"][0])
    current = _structural_flow(structural, name="FinancingInterestExpensesIncludingDivestitures", start="2025-11-01", end="2026-04-30", expected=240_000_000.)
    return {"field": "mixed_finance_interest_proxy", "value": 480_000_000., "period_end": "2026-04-30", "method": "current_h1_financing_cost_annualized_mixed_finance_proxy", "sources": [current], "annual_reference": annual_source, "reported_current_h1": current, "reported_vs_estimated": "finsight_annualization_not_like_for_like_corporate_interest"}


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    share_names = {"PreferredStockSharesOutstanding", "PreferredStockConvertibleSharesIssuable"}
    for name, value in POINTS[ticker]:
        if name in share_names:
            rows.append(_point_unit(structural, name, value, policy.period if name != "PreferredStockConvertibleSharesIssuable" else "2026-03-31"))
        else:
            rows.append(_point(structural, name=name, expected=value, period_end=policy.period))
    weighted, start = WEIGHTED[ticker]
    rows.append(_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=weighted, period_start=start, period_end=policy.period))
    if ticker == "DDOG":
        rows.extend((
            _fact(structural, "CommonStockSharesOutstanding", 334_438_127., None, policy.period, True),
            _fact(structural, "CommonStockSharesOutstanding", 24_518_658., None, policy.period, True),
            _fact(structural, "EntityCommonStockSharesOutstanding", 334_904_614., None, "2026-07-31", True),
            _fact(structural, "EntityCommonStockSharesOutstanding", 24_170_410., None, "2026-07-31", True),
        ))
    else:
        current, end = CURRENT[ticker]
        rows.append(_share_point(structural, expected=current, end=end))
    diagnostic = {"GDDY": {"DebtInstrumentCarryingAmount"}, "LITE": {name for name, _ in POINTS["LITE"]}, "HPE": {"CashAndCashEquivalentsAtCarryingValue", "AvailableForSaleSecuritiesDebtSecurities", "DebtLongtermAndShorttermCombinedAmount"}, "SNDK": {"CashAndCashEquivalentsAtCarryingValue"}}.get(ticker, set())
    for row in rows:
        local_name = str(row.get("concept", "")).split(":")[-1]
        if local_name in diagnostic or ticker in {"LITE", "SNDK"} and row.get("unit") in {"shares", "xbrli:shares"}:
            row["used_in_arithmetic"] = False
            row["coverage_role"] = "prior_or_gross_snapshot_reconciled_by_event_ledger"
    return rows


def _event_fact(structural: dict[str, Any], name: str, value: float, start: str | None, end: str, dimensions: bool = False) -> dict[str, Any]:
    return _fact(structural, name, value, start, end, dimensions)


EVENT_SPECS = {
    "DDOG": (("ShareBasedCompensation", 417_093_000., "2026-01-01", "2026-06-30", False), ("PaymentsToAcquireBusinessesNetOfCashAcquired", 112_310_000., "2026-01-01", "2026-06-30", False), ("RevenueRemainingPerformanceObligation", 3_471_400_000., None, "2026-06-30", False)),
    "KEYS": (("ShareBasedCompensation", 134_000_000., "2025-11-01", "2026-04-30", False), ("PaymentsToAcquireBusinessesNetOfCashAcquired", 17_000_000., "2025-11-01", "2026-04-30", False), ("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 545_000_000., None, "2026-04-30", False), ("DeferredCompensationLiabilityClassifiedNoncurrent", 39_000_000., None, "2026-04-30", True)),
    "GDDY": (("ShareBasedCompensation", 145_500_000., "2026-01-01", "2026-06-30", False), ("RevenueRemainingPerformanceObligation", 3_510_900_000., None, "2026-06-30", False)),
    "LITE": (("ShareBasedCompensation", 129_400_000., "2025-06-29", "2026-03-28", False), ("ProceedsFromIssuanceOfConvertiblePreferredStock", 1_999_700_000., "2025-06-29", "2026-03-28", False), ("DebtConversionConvertedInstrumentAmount1", 474_600_000., "2026-04-07", "2026-04-07", True), ("StockIssuedDuringPeriodSharesConversionOfConvertibleSecurities", 5_700_000., "2026-04-07", "2026-04-07", True)),
    "HPE": (("ShareBasedCompensation", 434_000_000., "2025-11-01", "2026-04-30", False), ("FinancingInterestExpensesIncludingDivestitures", 240_000_000., "2025-11-01", "2026-04-30", False), ("RevenueRemainingPerformanceObligation", 10_800_000_000., None, "2026-04-30", False), ("ConvertiblePreferredDividendsNetOfTax", 58_000_000., "2025-11-01", "2026-04-30", False), ("AntidilutiveSecuritiesExcludedFromComputationOfEarningsPerShareConvertiblePreferredStockAmount", 76_000_000., "2025-11-01", "2026-04-30", False), ("EquityMethodInvestmentPutSharePurchaseAgreementTotalConsideration", 987_000_000., None, "2026-05-13", True), ("EquityMethodInvestmentPutSharePurchaseAgreementTotalConsideration", 370_000_000., None, "2026-05-28", True)),
    "VRT": (("ShareBasedCompensation", 30_800_000., "2026-01-01", "2026-06-30", False), ("PaymentsToAcquireBusinessesNetOfCashAcquired", 278_100_000., "2026-01-01", "2026-06-30", False), ("BusinessCombinationAdditionalCashConsideration", 250_000_000., "2025-12-04", "2025-12-04", True)),
    "AVGO": (("ShareBasedCompensation", 4_268_000_000., "2025-11-03", "2026-05-03", False), ("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", 128_110_000_000., None, "2026-05-03", False), ("RevenueRemainingPerformanceObligation", 164_600_000_000., None, "2026-05-03", False), ("GuaranteeObligationsMaximumExposure", 29_000_000_000., None, "2026-06-03", True)),
    "MRVL": (("ShareBasedCompensation", 207_600_000., "2026-02-01", "2026-05-02", False), ("PaymentsToAcquireBusinessesNetOfCashAcquired", 1_270_900_000., "2026-02-01", "2026-05-02", False), ("BusinessCombinationContingentConsiderationShares", 22_400_000., None, "2026-02-02", True), ("BusinessCombinationConsiderationTransferred1", 3_537_400_000., "2026-02-02", "2026-02-02", True), ("BusinessCombinationConsiderationTransferred1", 469_000_000., "2026-02-10", "2026-02-10", True), ("DerivativeAssets", 81_100_000., None, "2026-05-02", True), ("OtherCommitment", 870_000_000., None, "2026-05-28", True)),
    "SNDK": (("ShareBasedCompensation", 165_000_000., "2025-06-28", "2026-04-03", False), ("PurchaseObligation", 7_107_000_000., None, "2026-04-03", False), ("RevenueRemainingPerformanceObligation", 41_600_000_000., None, "2026-04-03", False), ("SpinOffTransactionProRataDistributionOutstandingShares", 116_035_464., None, "2025-02-21", True)),
    "Q": (("ShareBasedCompensation", 25_000_000., "2026-01-01", "2026-06-30", False), ("InterestAndDebtExpense", 122_000_000., "2026-01-01", "2026-06-30", False), ("CommonStockSharesSeparatedAndDistributedToShareholders", 209_000_000., None, "2025-10-22", False)),
}


def _events(ticker: str, filing: dict[str, Any], structural: dict[str, Any], policy: Policy, package: dict[str, Any], receipt: dict[str, Any], event_root: Path) -> list[dict[str, Any]]:
    rows = [{"source_kind": "finsight_model_policy", "period_end": policy.period, "matter": policy.warning, "reported_vs_estimated": "finsight_assumption"}]
    rows.extend(_event_fact(structural, *spec) for spec in EVENT_SPECS[ticker])
    manual: dict[str, dict[str, Any]] = {
        "GDDY": {"matter": "cash and debt presentation", "reported_terms": {"cash_and_cash_equivalents": 1_155_500_000., "current_debt_net": 15_000_000., "noncurrent_debt_net": 3_759_400_000., "gross_debt_principal_diagnostic": 3_816_900_000.}, "treatment": "Use financial-statement cash and net carrying debt; retain gross principal only as a diagnostic."},
        "KEYS": {"matter": "recent acquisitions and divestiture", "treatment": "Current-state cash/debt includes completed consideration; acquired growth is not invented."},
        "LITE": {"matter": "note equitization and Series A preferred", "reported_terms": {"april_debt_principal_exchanged": 474_600_000., "april_common_shares_issued": 5_700_000., "preferred_shares": 2_900_000., "preferred_conversion": "one_for_one"}, "treatment": "The later August earnings release controls the final cash/debt/share bridge."},
        "HPE": {"matter": "Series C mandatory convertible, H3C sales, May debt repayment, and Financial Services", "reported_terms": {"h3c_may_sale_proceeds": 1_357_000_000., "may_term_loan_repayment": 750_000_000.}, "treatment": "Post-period cash/debt changes are reconciled; conversion and dividends are scheduled; all remaining debt is deducted and finance receivables stay inside operations."},
        "MRVL": {"matter": "Celestial/XConn and NVIDIA preferred", "reported_terms": {"preferred_as_converted_shares": 21_800_000., "contingent_acquisition_shares": 22_400_000.}},
        "SNDK": {"matter": "post-spin storage-cycle normalization", "treatment": "Three negative annual cash years and current recovery are bounded with a governed 1%/8%/16% margin range."},
        "Q": {"matter": "post-separation capital structure", "treatment": "Three carve-out annual periods plus current comparable cash anchor the governed range; current debt and claims are deducted once."},
    }
    if ticker in manual:
        rows.append({"source_kind": "controlling_filing_reported_terms", "accession": filing["accession"], "filed": filing["filed"], "period_end": policy.period, "reported_vs_estimated": "reported_terms_with_governed_treatment", **manual[ticker]})
    rows.extend(_load_event_rows(ticker, event_root))
    primary_name = package.get("primary_document")
    primary = next((item for item in package.get("files", []) if item.get("local_path") == primary_name), None)
    if not isinstance(primary, dict) or not primary.get("sha256") or not primary.get("source_url"):
        raise ValueError(f"{ticker}: primary filing provenance unavailable")
    provenance = {"primary_document": primary_name, "source_url": primary["source_url"], "document_sha256": primary["sha256"], "package_manifest_sha256": receipt["package_manifest_sha256"]}
    for row in rows:
        if row.get("source_kind") == "controlling_filing_reported_terms":
            row.update(provenance)
    return rows


def _verify_document(event_packet: Path, document: str, expected: str) -> None:
    if hashlib.sha256((event_packet / document).read_bytes()).hexdigest() != expected:
        raise ValueError(f"{event_packet.name}: event document hash mismatch")


def _load_event_rows(ticker: str, event_root: Path) -> list[dict[str, Any]]:
    if ticker not in {"GDDY", "LITE", "SNDK", "HPE", "AVGO"}:
        return []
    event_packet = Path(event_root) / ticker
    receipt = json.loads((event_packet / "source-receipt.json").read_text())
    if receipt.get("schema_version") != "FINSIGHT-BATCH-32-EVENT-SOURCE-1" or receipt.get("valuation_date") != BATCH_32_VALUATION_DATE:
        raise ValueError(f"{ticker}: event receipt invalid")
    if receipt.get("filed") and receipt["filed"] > BATCH_32_VALUATION_DATE:
        raise ValueError(f"{ticker}: event is after valuation cutoff")
    if ticker in {"LITE", "SNDK"}:
        for key in ("primary", "exhibit"):
            _verify_document(event_packet, receipt[key]["document"], receipt[key]["sha256"])
        return [{"source_kind": "sec_earnings_release", "accession": receipt["accession"], "filed": receipt["filed"], "period_end": receipt["report_date"], "source_url": receipt["exhibit"]["url"], "document_sha256": receipt["exhibit"]["sha256"], "primary_document_sha256": receipt["primary"]["sha256"], "reported_terms": receipt["reported_terms"], "treatment": receipt["treatment"], "reported_vs_estimated": "reported_unaudited"}]
    if ticker == "AVGO":
        result = []
        for event in receipt["events"]:
            if event["filed"] > BATCH_32_VALUATION_DATE:
                raise ValueError("AVGO event is after valuation cutoff")
            if "primary" in event:
                _verify_document(event_packet, event["primary"]["document"], event["primary"]["sha256"])
                _verify_document(event_packet, event["exhibit"]["document"], event["exhibit"]["sha256"])
                source_url, digest = event["exhibit"]["url"], event["exhibit"]["sha256"]
            else:
                _verify_document(event_packet, event["document"], event["document_sha256"])
                source_url, digest = event["url"], event["document_sha256"]
            result.append({"source_kind": "sec_current_report", "accession": event["accession"], "filed": event["filed"], "period_end": event["report_date"], "source_url": source_url, "document_sha256": digest, "reported_terms": event["reported_terms"], "treatment": event["treatment"], "reported_vs_estimated": "reported"})
        return result
    _verify_document(event_packet, receipt["document"], receipt["document_sha256"])
    row = {"source_kind": "sec_current_report", "accession": receipt["accession"], "filed": receipt["filed"], "period_end": receipt["report_date"], "source_url": receipt["url"], "document_sha256": receipt["document_sha256"], "reported_terms": receipt["reported_terms"], "treatment": receipt["treatment"], "reported_vs_estimated": "reported"}
    if ticker == "HPE":
        terms_source = receipt["terms_source"]
        _verify_document(event_packet, terms_source["document"], terms_source["document_sha256"])
        row["terms_source"] = terms_source
    return [row]


def build_batch_32_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_32_TICKERS:
        raise ValueError(ticker)
    policy = P[ticker]
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural_packet = Path(structural_root) / ticker
    structural = json.loads((structural_packet / "structural-filing.json").read_text())
    package = json.loads((structural_packet / "package-manifest.json").read_text())
    receipt = json.loads((structural_packet / "source-receipt.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural["source_accession"] != filing["accession"] or filing["period_end"] != policy.period:
        raise ValueError(f"{ticker}: controlling source mismatch")

    normalizer = _normalizer_for(ticker, submissions, facts)
    flows = {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow", "capital_expenditures", "interest_expense")}
    if ticker == "HPE":
        flows["interest_expense"] = _hpe_current_interest(normalizer, structural)
    history_anchor_flows = copy.deepcopy(flows)
    release_event = None
    if ticker in {"LITE", "SNDK"}:
        release_event = _load_event_rows(ticker, event_root)[0]
        terms = release_event["reported_terms"]
        flows["revenue"] = _release_flow(release_event, "revenue", float(terms["revenue"]), "earnings_release:Revenue")
        if ticker == "SNDK":
            flows["operating_cash_flow"] = _release_flow(release_event, "operating_cash_flow", float(terms["operating_cash_flow"]), "earnings_release:OperatingCashFlow")
            flows["capital_expenditures"] = _release_flow(release_event, "capital_expenditures", float(terms["capital_expenditures"]), "earnings_release:CapitalExpenditures")
            flows["interest_expense"] = _release_flow(release_event, "interest_expense", float(terms["interest_expense"]), "earnings_release:InterestExpense")
    try:
        tax_rate, tax_sources = _normalized_tax_rate(normalizer)
        tax_fallback = not .05 <= tax_rate <= .30
    except ValueError:
        tax_rate, tax_sources, tax_fallback = .21, (), True
    if tax_fallback:
        tax_rate = .21
    if ticker == "SNDK" and release_event is not None:
        terms = release_event["reported_terms"]
        tax_rate = float(terms["income_tax"]) / float(terms["pretax_income"])
        tax_sources = (dict(flows["revenue"]["sources"][0], field="normalized_tax_rate", concept="earnings_release:IncomeTaxExpenseDividedByPretaxIncome", value=tax_rate, unit="ratio"),)
        tax_fallback = False
    current_cash = cash_fcff_from_reported(
        operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]),
        spectrum_investment=0., interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate,
    )
    annual = _annual_cash_with_losses(normalizer)[2]
    sources = [dict(source) for flow in flows.values() for source in flow.get("sources", [])]
    revenue = float(flows["revenue"]["value"])
    profile_flows = history_anchor_flows if ticker == "LITE" else flows
    profile_sources = [dict(source) for flow in profile_flows.values() for source in flow.get("sources", [])]
    profile_revenue = float(profile_flows["revenue"]["value"])
    profile_period = policy.period if ticker == "LITE" else release_event["period_end"] if release_event else policy.period
    profile = build_cash_fcff_history_profile(
        annual_cash_states=annual, ttm_revenue=profile_revenue, ttm_cash_fcff=current_cash, ttm_period_end=profile_period,
        ttm_sources=profile_sources, valuation_date=BATCH_32_VALUATION_DATE,
    )
    cash_metric, growth_metric = profile.metric("cash_conversion_margin"), profile.metric("revenue_growth")
    if cash_metric is None:
        raise ValueError(f"{ticker}: cash history unavailable")
    margins = policy.margin or tuple(max(.001, float(value)) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    if growth_metric is None:
        growth = policy.growth
    else:
        growth = (
            max(-.10, min(policy.growth[0], growth_metric.low)),
            max(-.08, min(policy.growth[1], growth_metric.base)),
            max(0., min(policy.growth[2], growth_metric.high)),
        )
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
    reliability = assess_reliability(
        accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"],
        scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"],
        model_cap="High" if is_pass else "Low", source_cap="High",
        reasons=() if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"),
    )
    assumptions = {
        **profile.public_metadata(), "forecast_years": FORECAST_YEARS, "cash_conversion_margin": margins, "growth": growth,
        "wacc": policy.wacc, "terminal_growth": policy.terminal, "cash_and_investments": policy.cash, "claims": policy.claims,
        "shares": policy.shares, "assumption_classification": {
            "cash_conversion_margin": "governed_cycle_or_post_separation_range" if policy.margin else "historically_derived",
            "growth": "history_bounded_finsight_assumption", "wacc": "finsight_assumption", "terminal_growth": "finsight_assumption",
            "cash_debt_claims_and_shares": "reported_or_source_bounded_range",
        }, "tax_rate_basis": "governed 21% fallback" if tax_fallback else "normalized filing history",
        "equity_floor_basis": "limited-liability bear floor with raw residual retained" if scenario["low"] == 0 else "not applied",
        "calculator_calibration": "Calculator is calibrated to the exact faded-cash base.", "invalidation": policy.invalidation,
    }
    if ticker in {"DDOG", "GDDY", "LITE", "HPE", "AVGO", "MRVL", "SNDK"}:
        assumptions["stock_compensation_treatment"] = {"cash_flow_treatment": "Retained in reported operating cash flow; it is not subtracted again as cash.", "dilution_treatment": "Current weighted, outstanding, and where applicable conversion-share facts bound the denominator.", "release_condition": "Conditional where recurring future net dilution remains material."}
    if ticker in {"KEYS", "VRT", "MRVL"}:
        assumptions["acquisition_treatment"] = {"current_state": "Completed acquisitions are consolidated in current reported operations and the current balance sheet.", "forecast_treatment": "Growth is capped; no unsupported acquisition growth is invented.", "bridge_treatment": "Acquisition consideration exchanged for operating assets is not deducted twice."}
    if ticker in {"KEYS", "AVGO", "SNDK"}:
        assumptions["operating_commitment_treatment"] = {"treatment": "Reported purchase commitments remain inside post-cost forward cash conversion and are not deducted again as financing debt.", "invalidation": "Revalue if commitments become demonstrably excess, loss-making, or separately financed."}
    if ticker == "LITE":
        assumptions["latest_release_treatment"] = {"release_period": "2026-06-27", "revenue": 3_014_000_000., "cash_and_short_term_investments": 2_738_400_000., "debt": 1_637_400_000., "common_shares": 88_600_000., "preferred_one_for_one_shares": 2_900_000., "q4_non_gaap_diluted_shares": 101_100_000., "noncash_debt_extinguishment_loss": 7_756_600_000., "coherent_history_anchor_period": "2026-03-28", "coherent_history_anchor_revenue": 2_488_400_000., "coherent_history_anchor_cash_fcff": current_cash, "cash_flow_treatment": "The release did not furnish a full cash-flow statement; the history profile keeps the coherent March 28 TTM revenue/cash pair, while only the final valuation state uses the newer release revenue and bridge."}
    if ticker == "MRVL":
        assumptions["conversion_and_contingent_share_treatment"] = {"preferred_as_converted_shares": 21_800_000., "contingent_acquisition_shares_maximum": 22_400_000., "contingent_consideration_fair_value": 647_600_000., "forward_stock_purchase_asset_excluded": 81_100_000., "treatment": "The full fair-value liability is deducted once; contingent shares already represented by that liability are not added again. Preferred conversion and ordinary award dilution remain in the denominator."}
    if ticker == "HPE":
        assumptions["mandatory_convertible_treatment"] = {"conversion_date": "2027-09-01", "preferred_shares": 30_000_000., "minimum_common_conversion_shares": 76_056_000., "maximum_common_conversion_shares": 93_168_000., "reported_h1_preferred_dividends": 58_000_000., "declared_next_dividend_total": 28_593_750., "remaining_quarters_reserved": 5, "dividend_pv": tuple(value - 61_000_000. for value in policy.claims), "nci": 61_000_000., "treatment": "Every scenario includes the source-bounded mandatory conversion; five quarterly dividends are discounted on the scenario WACC schedule before the 2027 conversion date."}
        assumptions["post_period_bridge_treatment"] = {"april_cash_and_afs": 5_516_000_000., "h3c_sale_proceeds": 1_357_000_000., "may_term_loan_repayment": 750_000_000., "post_event_cash_and_afs": 6_123_000_000., "april_debt": 21_246_000_000., "post_event_debt": 20_496_000_000.}
        assumptions["mixed_finance_interest_treatment"] = {"reported_h1_financing_cost": 240_000_000., "annualized_proxy": 480_000_000., "classification": "finsight_assumption", "warning": "This income-statement financing-cost proxy includes Financial Services economics and is not presented as like-for-like corporate debt interest."}
    if ticker == "SNDK":
        assumptions["cycle_normalization"] = {"annual_cash_years": 3, "annual_cash_observations": [row["cash_fcff"] for row in annual], "latest_release_cash_fcff": current_cash, "governed_margin_range": margins, "latest_release_period": "2026-07-03", "treatment": "The 57% release-period cash margin is treated as a cycle outlier, not the base assumption."}
    if ticker == "Q":
        assumptions["post_separation_history_treatment"] = {"annual_history_years": profile.history_years_used, "current_h1_interest": 122_000_000., "ttm_interest": flows["interest_expense"]["value"], "treatment": "Current post-separation debt interest is carried through the issuer-specific concept lineage; no zero substitution."}

    baseline = BaselineValuation(
        ticker=ticker, method=policy.method, method_version=BATCH_32_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"],
        confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL,
        key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual/current cash evidence anchors or bounds the range."),),
        warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator",
    )
    return {
        "ticker": ticker, "method": policy.method, "model_version": BATCH_32_HISTORY_VERSION,
        "availability_type": "available" if is_pass else "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario,
        "reported_inputs": {"ttm_revenue": revenue, "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": flows["interest_expense"]["value"], "ttm_interest_basis": flows["interest_expense"].get("method"), "tax_rate": tax_rate, "ttm_cash_fcff": current_cash},
        "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(),
        "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "annual_cash_sources": list(annual), "tax_rate_sources": list(tax_sources), "tax_rate_treatment": {"fallback_applied": tax_fallback, "rate": tax_rate}, "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge(ticker, structural, policy), "event_sources": _events(ticker, filing, structural, policy, package, receipt, event_root), "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "other_equity_claim_formula": policy.bridge_formula, "shares": policy.shares, "operating_liability_treatment": "Operating leases, supplier obligations, deferred revenue, warranties, and ordinary working capital remain inside operating cash conversion and are not deducted twice."}, "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces}, "package_provenance": {"package_manifest_sha256": receipt["package_manifest_sha256"], "primary_document": package.get("primary_document")}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False, "selection_basis": "controlling source receipt report date plus exact fact periods"}},
        "warning": policy.warning, "baseline": baseline.as_private_dict(),
    }


if set(P) != set(BATCH_32_TICKERS) or PASS_TICKERS | CONDITIONAL_TICKERS | WITHHELD_TICKERS != set(BATCH_32_TICKERS):
    raise RuntimeError("Batch 32 policy mismatch")
