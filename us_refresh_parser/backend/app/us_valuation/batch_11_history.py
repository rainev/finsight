"""History-backed practical baselines for controlled universe-reset Batch 11."""
from __future__ import annotations

from dataclasses import dataclass, replace
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
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11 import BATCH_11_TICKERS, BATCH_11_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION, build_cash_fcff_history_profile
from .reliability import assess_reliability


BATCH_11_HISTORY_VERSION = "BATCH-11-HISTORY-PRACTICAL-1.0"
PASS_TICKERS = frozenset({"MO", "MNST"})


def _shares(base: float) -> tuple[float, float, float]:
    return (base * 1.025, base, base * .975)


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: float
    claims: float
    shares: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str


P = {
    "SYY": Policy(
        "food_distribution_cash_fcff",
        "2026-03-28",
        1_900_000_000.,
        14_008_000_000.,
        0.,
        _shares(480_738_926.),
        (.105, .09, .08),
        (0., .015, .02),
        "Withheld. The signed Jetro Restaurant Depot transaction requires approximately $21.6B cash and 91.5M Sysco shares, but the filing does not provide one post-closing cash-flow, debt, and share object.",
        "Revalue after the Jetro transaction closes or terminates and the resulting cash, debt, shares, and operating cash are filed.",
    ),
    "CHD": Policy(
        "consumer_products_cash_fcff",
        "2026-06-30",
        254_800_000.,
        2_256_200_000.,
        14_600_000.,
        _shares(238_200_000.),
        (.105, .09, .08),
        (0., .015, .02),
        "Conditional Low consumer-products estimate. Touchland and current brand acquisitions, acquisition-liability cash, and contingent consideration are material relative to current cash generation and lack a full comparable operating history.",
        "Invalidate if acquisition integration, acquired-brand cash conversion, debt, contingent consideration, or diluted shares changes.",
    ),
    "MO": Policy(
        "mature_tobacco_cash_fcff",
        "2026-06-30",
        2_367_000_000.,
        24_577_000_000.,
        50_000_000.,
        _shares(1_672_000_000.),
        (.105, .09, .08),
        (0., .01, .02),
        "History-backed mature-tobacco cash-FCFF. The equity-method investment remains inside operating cash conversion and is not added again as excess cash.",
        "Invalidate if tobacco cash conversion, investment distributions, debt, NCI, litigation cash, or diluted shares changes.",
    ),
    "MNST": Policy(
        "debt_free_beverage_owner_cash",
        "2026-06-30",
        4_200_570_000.,
        0.,
        0.,
        _shares(988_456_000.),
        (.10, .085, .075),
        (0., .015, .025),
        "History-backed debt-free beverage owner-cash baseline. Cash and the complete current/noncurrent available-for-sale securities total are counted once.",
        "Invalidate if securities coverage, debt absence, distribution agreements, cash conversion, or diluted shares changes.",
    ),
    "COST": Policy(
        "membership_retail_cash_fcff",
        "2026-05-10",
        19_996_000_000.,
        5_670_000_000.,
        0.,
        _shares(444_455_000.),
        (.10, .085, .075),
        (0., .015, .025),
        "Conditional Low membership-retail cash-FCFF. Current balance-sheet debt is complete, but finance-lease payments and new right-of-use assets prove an untagged liability that requires a bounded reserve.",
        "Invalidate if membership economics, working capital, investments, debt, finance leases, or diluted shares changes.",
    ),
    "DLTR": Policy(
        "post_family_dollar_cash_fcff",
        "2026-05-02",
        1_007_300_000.,
        2_932_600_000.,
        0.,
        _shares(197_400_000.),
        (.115, .10, .09),
        (0., .01, .02),
        "Conditional Low post-Family-Dollar estimate. Continuing cash is reported, but disposal consideration, transition services, guarantees, and the shorter comparable-history window remain material.",
        "Invalidate if disposal adjustments, transition services, guarantees, continuing cash, debt, or diluted shares changes.",
    ),
    "MDLZ": Policy(
        "global_snacks_cycle_cash_fcff",
        "2026-06-30",
        1_716_000_000.,
        21_450_000_000.,
        53_000_000.,
        _shares(1_286_000_000.),
        (.115, .10, .09),
        (0., .01, .02),
        "Conditional Low global-snacks estimate. The current H1 filing is reconstructed directly; cocoa and commodity-driven cash conversion remain material.",
        "Invalidate if the H1 reconstruction, cocoa/commodity cash, debt, NCI, restricted cash, or diluted shares changes.",
    ),
    "PM": Policy(
        "smoke_free_tobacco_cash_fcff",
        "2026-06-30",
        5_999_000_000.,
        49_113_000_000.,
        1_926_000_000.,
        _shares(1_560_000_000.),
        (.105, .09, .08),
        (0., .01, .02),
        "Conditional Low tobacco and smoke-free-products estimate. Debt, leases, and NCI reconcile, but the equity-method stake and its investing-cash distributions are not fully integrated into consolidated FCFF.",
        "Invalidate if smoke-free mix, debt/leases, NCI, affiliate investment/distributions, or diluted shares changes.",
    ),
    "KHC": Policy(
        "post_impairment_packaged_food_cash_fcff",
        "2026-06-27",
        2_681_000_000.,
        19_001_000_000.,
        124_000_000.,
        _shares(1_186_000_000.),
        (.115, .10, .09),
        (0., .01, .02),
        "Conditional Low packaged-food estimate. Repeated brand/reporting-unit impairments, restructuring, portfolio actions, and leverage remain material despite positive reported cash.",
        "Invalidate if impairment/restructuring plans, portfolio scope, debt, NCI, cash conversion, or diluted shares changes.",
    ),
    "BG": Policy(
        "post_viterra_cycle_cash_fcff",
        "2026-06-30",
        788_000_000.,
        15_214_000_000.,
        1_457_000_000.,
        _shares(195_536_176.),
        (.12, .105, .095),
        (0., .01, .02),
        "Withheld. The Viterra combination closed mid-2025, and the filing does not provide three comparable combined annual cash periods or a complete filed pro-forma cash history.",
        "Revalue only after comparable combined history or a filed pro-forma cash-flow bridge exists.",
    ),
}


SHARE_STARTS = {
    "SYY": "2025-06-29",
    "CHD": "2026-01-01",
    "MO": "2026-01-01",
    "MNST": "2026-01-01",
    "COST": "2025-09-01",
    "DLTR": "2026-02-01",
    "MDLZ": "2026-01-01",
    "PM": "2026-01-01",
    "KHC": "2025-12-28",
    "BG": "2026-01-01",
}


POINT_SPECS = {
    "SYY": (
        ("CashAndCashEquivalentsAtCarryingValue", 1_900_000_000.),
        ("AvailableForSaleSecuritiesDebtSecurities", 124_000_000.),
        ("RestrictedCashAndCashEquivalents", 156_000_000.),
        ("LongTermDebtAndCapitalLeaseObligationsCurrent", 1_190_000_000.),
        ("LongTermDebtAndCapitalLeaseObligations", 12_818_000_000.),
        ("PreferredStockValue", 0.),
        ("RedeemableNoncontrollingInterestEquityCarryingAmount", 0.),
    ),
    "CHD": (
        ("CashAndCashEquivalentsAtCarryingValue", 254_800_000.),
        ("ShortTermBorrowings", 49_900_000.),
        ("LongTermDebtNoncurrent", 2_206_300_000.),
        ("BusinessCombinationContingentConsiderationLiabilityCurrent", 14_600_000.),
        ("SupplyChainFinanceProgramOutstandingObligations", 111_900_000.),
        ("PreferredStockValue", 0.),
    ),
    "MO": (
        ("CashAndCashEquivalentsAtCarryingValue", 2_367_000_000.),
        ("LongTermDebt", 24_577_000_000.),
        ("MinorityInterest", 50_000_000.),
        ("Investments", 8_896_000_000.),
        ("SupplierFinanceProgramObligation", 171_000_000.),
    ),
    "MNST": (
        ("CashAndCashEquivalentsAtCarryingValue", 2_192_424_000.),
        ("AvailableForSaleSecuritiesDebtSecurities", 2_008_146_000.),
    ),
    "COST": (
        ("CashAndCashEquivalentsAtCarryingValue", 18_946_000_000.),
        ("ShortTermInvestments", 1_050_000_000.),
        ("LongTermDebtCurrent", 0.),
        ("LongTermDebtNoncurrent", 5_670_000_000.),
        ("PreferredStockValue", 0.),
    ),
    "DLTR": (
        ("CashAndCashEquivalentsAtCarryingValue", 1_007_300_000.),
        ("RestrictedCashNoncurrent", 43_400_000.),
        ("LongTermDebtNoncurrent", 2_932_600_000.),
        ("SupplierFinanceProgramObligation", 298_400_000.),
        ("OperatingLeaseLiabilityCurrent", 1_005_200_000.),
        ("OperatingLeaseLiabilityNoncurrent", 3_655_500_000.),
    ),
    "MDLZ": (
        ("CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations", 1_716_000_000.),
        ("RestrictedCashCurrent", 43_000_000.),
        ("ShortTermBorrowings", 2_327_000_000.),
        ("LongTermDebtAndCapitalLeaseObligationsCurrent", 2_663_000_000.),
        ("LongTermDebtAndCapitalLeaseObligations", 16_460_000_000.),
        ("MinorityInterest", 53_000_000.),
        ("SupplierFinanceProgramObligation", 2_900_000_000.),
    ),
    "PM": (
        ("CashAndCashEquivalentsAtCarryingValue", 5_999_000_000.),
        ("RestrictedCash", 25_000_000.),
        ("ShortTermBorrowings", 3_341_000_000.),
        ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities", 45_772_000_000.),
        ("FinanceLeaseLiability", 99_000_000.),
        ("MinorityInterest", 1_926_000_000.),
        ("EquityMethodInvestments", 1_008_000_000.),
    ),
    "KHC": (
        ("CashAndCashEquivalentsAtCarryingValue", 2_419_000_000.),
        ("MarketableSecuritiesCurrent", 262_000_000.),
        ("RestrictedCashCurrent", 164_000_000.),
        ("RestrictedCashAndCashEquivalentsNoncurrent", 106_000_000.),
        ("LongTermDebtAndCapitalLeaseObligationsCurrent", 1_382_000_000.),
        ("LongTermDebtAndCapitalLeaseObligations", 17_619_000_000.),
        ("MinorityInterest", 111_000_000.),
        ("RedeemableNoncontrollingInterestEquityCarryingAmount", 13_000_000.),
    ),
    "BG": (
        ("CashAndCashEquivalentsAtCarryingValue", 593_000_000.),
        ("MarketableSecuritiesCurrent", 195_000_000.),
        ("RestrictedCashCurrent", 3_000_000.),
        ("DebtLongtermAndShorttermCombinedAmount", 15_214_000_000.),
        ("MinorityInterest", 1_389_000_000.),
        ("RedeemableNoncontrollingInterestEquityCarryingAmount", 68_000_000.),
    ),
}


def _no_preferred(structural: dict[str, Any], period: str) -> dict[str, Any]:
    names = (
        "PreferredStockValue",
        "PreferredStockValueOutstanding",
        "TemporaryEquityCarryingAmount",
        "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
    )
    rows = [
        row
        for row in structural["facts"]
        if row.get("local_name") in names
        and row.get("period_start") is None
        and row.get("period_end") == period
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) != 0
    ]
    if rows:
        raise ValueError("unreconciled preferred or temporary equity")
    return {
        "source_kind": "controlling_filing_structure",
        "accession": structural["source_accession"],
        "period_end": period,
        "field": "preferred_and_temporary_equity",
        "reported_vs_estimated": "source_proven_absent_or_zero",
        "checked_concepts": list(names),
    }


def _source_proven_no_short_term_debt(
    structural: dict[str, Any], period: str
) -> dict[str, Any]:
    names = ("ShortTermBorrowings", "CommercialPaper", "DebtCurrent")
    nonzero = [
        row
        for row in structural["facts"]
        if row.get("local_name") in names
        and row.get("period_start") is None
        and row.get("period_end") == period
        and not row.get("dimensions")
        and isinstance(row.get("value"), (int, float))
        and float(row["value"]) != 0
    ]
    if nonzero:
        raise ValueError("unreconciled short-term debt")
    return {
        "source_kind": "controlling_filing_structure",
        "accession": structural["source_accession"],
        "period_end": period,
        "field": "short_term_borrowings_and_commercial_paper",
        "reported_vs_estimated": "source_proven_absent_or_zero",
        "checked_concepts": list(names),
    }


def _dimension_fact(
    structural: dict[str, Any],
    *,
    name: str,
    expected: float,
    start: str | None,
    end: str,
    member: str,
) -> dict[str, Any]:
    rows = [
        row
        for row in structural["facts"]
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
        "period_start": start,
        "period_end": end,
        "concept": row.get("qname"),
        "dimensions": row.get("dimensions"),
        "unit": row.get("unit"),
        "value": expected,
        "reported_vs_estimated": "reported",
    }


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [
        _point(structural, name=name, expected=value, period_end=policy.period)
        for name, value in POINT_SPECS[ticker]
    ]
    rows.append(
        _duration(
            structural,
            name="WeightedAverageNumberOfDilutedSharesOutstanding",
            expected=policy.shares[1],
            period_start=SHARE_STARTS[ticker],
            period_end=policy.period,
        )
    )
    if ticker in {"SYY", "CHD", "MNST", "COST", "DLTR"}:
        rows.append(
            _source_proven_no_other_equity_claims(
                structural, period_end=policy.period
            )
        )
    else:
        rows.append(_no_preferred(structural, policy.period))
    if ticker == "MNST":
        rows.append(_source_proven_no_debt(structural, period_end=policy.period))
    if ticker == "COST":
        rows.extend(
            (
                _source_proven_no_short_term_debt(structural, policy.period),
                _structural_flow(
                    structural,
                    name="FinanceLeasePrincipalPayments",
                    start="2025-09-01",
                    end=policy.period,
                    expected=57_000_000.,
                ),
                _structural_flow(
                    structural,
                    name="RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability",
                    start="2025-09-01",
                    end=policy.period,
                    expected=116_000_000.,
                ),
                {
                    "source_kind": "source_bounded_policy",
                    "field": "unreported_finance_lease_liability",
                    "period_end": policy.period,
                    "reported_vs_estimated": "estimated_range",
                    "value_range": {"bear": 57_000_000., "base": 28_500_000., "bull": 0.},
                    "basis": "The current filing reports $57M YTD finance-lease principal payments and $116M of new finance-lease ROU assets but no liability point. One YTD principal-payment amount caps the explicit reserve.",
                },
            )
        )
    if ticker == "SYY":
        for row in rows:
            if row.get("concept") == "us-gaap:AvailableForSaleSecuritiesDebtSecurities":
                row.update(
                    {
                        "included_in_excess_cash": False,
                        "restriction_basis": "The filing identifies the portfolio as restricted investments of the captive insurance subsidiary.",
                    }
                )
        rows.extend(
            (
                {
                    **_dimension_fact(
                        structural,
                        name="DebtAndCapitalLeaseObligations",
                        expected=473_000_000.,
                        start=None,
                        end=policy.period,
                        member="EuropeMember",
                    ),
                    "bridge_treatment": "included_in_reported_long_term_debt_not_added_again",
                },
                _point(
                    structural,
                    name="SupplierFinanceProgramObligationCurrent",
                    expected=85_000_000.,
                    period_end=policy.period,
                ),
                _dimension_fact(
                    structural,
                    name="BusinessCombinationPriceOfAcquisitionExpected",
                    expected=29_100_000_000.,
                    start="2026-03-30",
                    end="2026-03-30",
                    member="JetroRestaurantDepotMember",
                ),
                _dimension_fact(
                    structural,
                    name="PaymentsToAcquireBusinessesExpectedAmount",
                    expected=21_600_000_000.,
                    start="2026-03-30",
                    end="2026-03-30",
                    member="JetroRestaurantDepotMember",
                ),
                _dimension_fact(
                    structural,
                    name="BusinessCombinationConsiderationTransferredEquityInterestShareIssuedExpectedNumberOfShares",
                    expected=91_500_000.,
                    start="2026-03-30",
                    end="2026-03-30",
                    member="JetroRestaurantDepotMember",
                ),
                _dimension_fact(
                    structural,
                    name="LineOfCreditFacilityMaximumBorrowingCapacity",
                    expected=22_000_000_000.,
                    start=None,
                    end="2026-03-30",
                    member="JetroRestaurantDepotMember",
                ),
                _dimension_fact(
                    structural,
                    name="BusinessCombinationTerminationFee",
                    expected=1_164_000_000.,
                    start=None,
                    end="2026-03-30",
                    member="JetroRestaurantDepotMember",
                ),
                _dimension_fact(
                    structural,
                    name="DerivativeNotionalAmount",
                    expected=6_300_000_000.,
                    start=None,
                    end="2026-03-30",
                    member="JetroRestaurantDepotMember",
                ),
                _dimension_fact(
                    structural,
                    name="LineOfCreditFacilityMaximumBorrowingCapacity",
                    expected=3_000_000_000.,
                    start=None,
                    end="2026-04-28",
                    member="JetroRestaurantDepotMember",
                ),
                _dimension_fact(
                    structural,
                    name="LineOfCreditFacilityMaximumBorrowingCapacity",
                    expected=19_000_000_000.,
                    start=None,
                    end="2026-04-28",
                    member="JetroRestaurantDepotMember",
                ),
                _dimension_fact(
                    structural,
                    name="PaymentsOfDebtIssuanceCosts",
                    expected=88_000_000.,
                    start="2026-04-10",
                    end="2026-04-10",
                    member="JetroRestaurantDepotMember",
                ),
            )
        )
        for row in rows:
            if any(
                "JetroRestaurantDepotMember" in str(value)
                for _, value in (row.get("dimensions") or [])
            ):
                row["valuation_treatment"] = (
                    "separate_transaction_surface_not_in_intrinsic_value"
                )
    if ticker == "CHD":
        rows.extend(
            (
                _structural_flow(
                    structural,
                    name="PaymentsToAcquireBusinessesNetOfCashAcquired",
                    start="2026-01-01",
                    end=policy.period,
                    expected=300_000_000.,
                ),
                _structural_flow(
                    structural,
                    name="PaymentOfBusinessAcquisitionLiability",
                    start="2026-01-01",
                    end=policy.period,
                    expected=-180_500_000.,
                ),
                _dimension_fact(
                    structural,
                    name="BusinessCombinationCashPurchasePriceNetOfContingentConsideration",
                    expected=300_000_000.,
                    start=None,
                    end=policy.period,
                    member="MissMouthsMessyEaterBrandMember",
                ),
                _dimension_fact(
                    structural,
                    name="BusinessCombinationCashPurchasePriceNetOfContingentConsideration",
                    expected=656_000_000.,
                    start=None,
                    end=policy.period,
                    member="TouchlandAcquisitionMember",
                ),
            )
        )
    if ticker == "DLTR":
        rows.extend(
            (
                _structural_flow(
                    structural,
                    name="NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
                    start="2026-02-01",
                    end=policy.period,
                    expected=644_000_000.,
                ),
                _dimension_fact(
                    structural,
                    name="DisposalGroupIncludingDiscontinuedOperationConsideration",
                    expected=793_000_000.,
                    start=None,
                    end="2025-07-05",
                    member="FamilyDollarMember",
                ),
            )
        )
    if ticker == "KHC":
        rows.append(
            _structural_flow(
                structural,
                name="AssetImpairmentCharges",
                start="2025-12-28",
                end=policy.period,
                expected=7_365_000_000.,
            )
        )
    if ticker == "MO":
        rows.extend(
            (
                _point(
                    structural,
                    name="AccruedSettlementLiabilityCurrent",
                    expected=1_169_000_000.,
                    period_end=policy.period,
                ),
                _structural_flow(
                    structural,
                    name="IncreaseDecreaseInSettlementPayable",
                    start="2026-01-01",
                    end=policy.period,
                    expected=-1_009_000_000.,
                ),
                _structural_flow(
                    structural,
                    name="EquityMethodInvestmentDividendsOrDistributions",
                    start="2026-01-01",
                    end=policy.period,
                    expected=186_000_000.,
                ),
            )
        )
    if ticker == "PM":
        rows.extend(
            (
                _structural_flow(
                    structural,
                    name="EquityMethodInvestmentDividendsOrDistributions",
                    start="2026-01-01",
                    end=policy.period,
                    expected=17_000_000.,
                ),
                _structural_flow(
                    structural,
                    name="PaymentsForProceedsFromOtherInvestingActivities",
                    start="2026-01-01",
                    end=policy.period,
                    expected=17_000_000.,
                ),
                _dimension_fact(
                    structural,
                    name="SupplierFinanceProgramObligationCurrent",
                    expected=1_000_000_000.,
                    start=None,
                    end=policy.period,
                    member="SuppliersUsingSupplyChainFinancingProgramMember",
                ),
            )
        )
    if ticker == "BG":
        rows.append(
            _dimension_fact(
                structural,
                name="BusinessCombinationConsiderationTransferred1",
                expected=10_617_000_000.,
                start="2025-07-02",
                end="2025-07-02",
                member="ViterraLimitedMember",
            )
        )
    return rows


def _latest_ttm_from_structural(
    structural: dict[str, Any], normalizer: Any
) -> dict[str, dict[str, Any]]:
    specs = {
        "revenue": ("Revenues", 19_435_000_000., 18_297_000_000.),
        "operating_cash_flow": (
            "NetCashProvidedByUsedInOperatingActivities",
            1_322_000_000.,
            1_400_000_000.,
        ),
        "capital_expenditures": (
            "PaymentsToAcquirePropertyPlantAndEquipment",
            654_000_000.,
            582_000_000.,
        ),
        "interest_expense": ("InterestExpenseDebt", 292_000_000., 288_000_000.),
    }
    values = {}
    for field, (name, current, prior) in specs.items():
        annual = normalizer.annual_series(field, 1)[0]
        current_source = _structural_flow(
            structural,
            name=name,
            start="2026-01-01",
            end="2026-06-30",
            expected=current,
        )
        prior_source = _structural_flow(
            structural,
            name=name,
            start="2025-01-01",
            end="2025-06-30",
            expected=prior,
        )
        values[field] = {
            "field": field,
            "value": float(annual.value) + current - prior,
            "period_end": "2026-06-30",
            "method": "latest_fy_plus_current_h1_minus_prior_h1",
            "sources": [annual.as_dict(), current_source, prior_source],
        }
    return values


def _interest_expense_magnitude_ttm(
    ticker: str, structural: dict[str, Any], normalizer: Any
) -> dict[str, Any]:
    expected_annual = {"MO": 1_177_000_000., "PM": 1_587_000_000.}[ticker]
    expected_current = {"MO": -553_000_000., "PM": -480_000_000.}[ticker]
    expected_prior = {"MO": -537_000_000., "PM": -518_000_000.}[ticker]
    annual = normalizer.annual_series("interest_expense", 1)[0]
    if float(annual.value) != expected_annual:
        raise ValueError(f"{ticker}: annual interest source changed")
    current = _structural_flow(
        structural,
        name="InterestIncomeExpenseNonoperatingNet",
        start="2026-01-01",
        end="2026-06-30",
        expected=expected_current,
    )
    prior = _structural_flow(
        structural,
        name="InterestIncomeExpenseNonoperatingNet",
        start="2025-01-01",
        end="2025-06-30",
        expected=expected_prior,
    )
    return {
        "field": "interest_expense",
        "value": abs(float(annual.value)) + abs(expected_current) - abs(expected_prior),
        "period_end": "2026-06-30",
        "method": "latest_fy_expense_magnitude_plus_current_h1_magnitude_minus_prior_h1_magnitude",
        "sources": [annual.as_dict(), current, prior],
        "sign_treatment": "Annual InterestExpense is a positive expense; H1 InterestIncomeExpenseNonoperatingNet is a negative expense. Magnitudes are aligned before TTM arithmetic.",
    }


def _withheld(
    ticker: str,
    filing: dict[str, Any],
    structural: dict[str, Any],
    policy: Policy,
    *,
    method: str,
    normalization_basis: str,
    assumption_source_mix: str,
    release_condition: str,
) -> dict[str, Any]:
    baseline = BaselineValuation(
        ticker=ticker,
        method=method,
        method_version=BATCH_11_HISTORY_VERSION,
        low=None,
        base=None,
        high=None,
        confidence=None,
        availability_type=AvailabilityType.NOT_AVAILABLE,
        warnings=(policy.warning, policy.invalidation),
    )
    return {
        "ticker": ticker,
        "method": method,
        "model_version": BATCH_11_HISTORY_VERSION,
        "availability_type": "not_available",
        "scenario_rows": [],
        "scenario_range": {"low": None, "base": None, "high": None},
        "reported_inputs": {},
        "governed_assumptions": {
            "history_policy_version": HISTORY_POLICY_VERSION,
            "history_years_used": 0,
            "normalization_basis": normalization_basis,
            "assumption_source_mix": assumption_source_mix,
            "invalidation": policy.invalidation,
        },
        "history_reliability": None,
        "source_ledger": {
            "controlling_filing": filing,
            "bridge_sources": _bridge(ticker, structural, policy),
            "bridge_reconciliation": {
                "cash_and_investments": policy.cash,
                "debt_and_finance_leases": policy.debt,
                "preferred_nci_and_redeemable_claims": policy.claims,
                "shares": policy.shares,
            },
            "release_condition": release_condition,
            "structural_top_level_period_diagnostic": {
                "value": structural.get("period_end"),
                "used_for_selection": False,
            },
        },
        "warning": policy.warning,
        "baseline": baseline.as_private_dict(),
    }


def build_batch_11_history_result(
    *,
    ticker: str,
    source_root: Path,
    structural_root: Path,
    allow_syy_current_state_recovery: bool = False,
    model_version: str = BATCH_11_HISTORY_VERSION,
) -> dict[str, Any]:
    policy = P[ticker]
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads(
        (Path(structural_root) / ticker / "structural-filing.json").read_text()
    )
    filing = _controlling(manifest, submissions)
    if (
        structural["source_accession"] != filing["accession"]
        or filing["period_end"] != policy.period
    ):
        raise ValueError(f"{ticker}: controlling source mismatch")
    if ticker == "SYY" and not allow_syy_current_state_recovery:
        return _withheld(
            ticker,
            filing,
            structural,
            policy,
            method="unavailable_pending_jetro_transaction_state",
            normalization_basis="pending_jetro_transaction_state_unavailable",
            assumption_source_mix="reported_pre_transaction_state_and_signed_transaction_terms",
            release_condition="Filed Jetro closing or termination state with one coherent cash-flow, debt, and share object.",
        )
    if ticker == "SYY":
        policy = replace(
            policy,
            method="pre_jetro_current_state_cash_fcff",
            warning="Conditional Low standalone estimate using three source-linked annual periods at the latest reportable pre-Jetro balance-sheet date (2026-03-28; 10-Q filed 2026-04-29). It excludes the signed Jetro transaction (approximately $29.1B consideration: $21.6B cash and 91.5M Sysco shares), undrawn financing commitments, fees, and rate-lock effects; it is not a post-announcement or post-close equity value and no transaction probability is applied.",
            invalidation="Invalidate on Jetro closing, termination, financing issuance, material term change, or a new controlling filing that changes standalone cash, debt, or shares.",
        )
    if ticker == "BG":
        return _withheld(
            ticker,
            filing,
            structural,
            policy,
            method="unavailable_post_viterra_comparable_history",
            normalization_basis="post_viterra_comparable_cash_history_unavailable",
            assumption_source_mix="reported_current_combined_state_without_comparable_history",
            release_condition="Three comparable combined annual cash periods or a complete filed pro-forma cash-flow bridge.",
        )

    normalizer = _normalizer(submissions, facts)
    if ticker == "MDLZ":
        flows = _latest_ttm_from_structural(structural, normalizer)
    else:
        names = ("revenue", "operating_cash_flow", "capital_expenditures")
        flows = {name: normalizer.ttm_flow(name) for name in names}
        if ticker == "MNST":
            debt_absence = _source_proven_no_debt(
                structural, period_end=policy.period
            )
            flows["interest_expense"] = {
                "field": "interest_expense",
                "value": 0.,
                "period_end": policy.period,
                "method": "not_applicable_source_proven_no_debt",
                "sources": [debt_absence],
            }
        else:
            flows["interest_expense"] = normalizer.ttm_flow("interest_expense")
        if ticker in {"MO", "PM"}:
            flows["interest_expense"] = _interest_expense_magnitude_ttm(
                ticker, structural, normalizer
            )
    if any(flow["period_end"] != policy.period for flow in flows.values()):
        raise ValueError(f"{ticker}: TTM period mismatch")

    tax_rate = _normalized_tax_rate(normalizer)[0]
    current_cash = (
        float(flows["operating_cash_flow"]["value"])
        - float(flows["capital_expenditures"]["value"])
        if ticker == "MNST"
        else cash_fcff_from_reported(
            operating_cash_flow=float(flows["operating_cash_flow"]["value"]),
            capital_expenditures=float(flows["capital_expenditures"]["value"]),
            spectrum_investment=0.,
            interest_expense=abs(float(flows["interest_expense"]["value"])),
            tax_rate=tax_rate,
        )
    )
    if ticker == "MNST":
        annual_sources = _annual_owner_cash(normalizer)[2]
    else:
        annual_sources = _annual_cash_with_losses(normalizer)[2]
    if ticker == "DLTR":
        annual_sources = tuple(
            row for row in annual_sources if row["period_end"] >= "2024-02-03"
        )
    ttm_sources = []
    for flow in flows.values():
        ttm_sources.extend(
            dict(row) for row in flow.get("sources", []) if isinstance(row, dict)
        )
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(
        annual_cash_states=annual_sources,
        ttm_revenue=revenue,
        ttm_cash_fcff=current_cash,
        ttm_period_end=policy.period,
        ttm_sources=ttm_sources,
        valuation_date=BATCH_11_VALUATION_DATE,
    )
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None:
        raise ValueError(f"{ticker}: history insufficient")
    margins = tuple(
        max(.001, value)
        for value in (cash_metric.low, cash_metric.base, cash_metric.high)
    )
    growth = (
        max(-.05, min(.03, growth_metric.low)),
        max(-.03, min(.04, growth_metric.base)),
        max(0., min(.05, growth_metric.high)),
    )
    rows = []
    finance_lease_reserve = (57_000_000., 28_500_000., 0.) if ticker == "COST" else (0., 0., 0.)
    for index, name in enumerate(("bear", "base", "bull")):
        raw = five_year_fcff_dcf(
            revenue=revenue,
            fcff_margin=margins[index],
            growth=growth[index],
            wacc=policy.wacc[index],
            terminal_growth=policy.terminal[index],
            cash_and_investments=policy.cash,
            debt=policy.debt,
            noncontrolling_interests=policy.claims + finance_lease_reserve[index],
            shares=policy.shares[index],
        )
        value = max(0., float(raw["value_per_share"]))
        rows.append(
            {
                "name": name,
                "conditional_value_per_share": value,
                "raw_value_per_share": float(raw["value_per_share"]),
                "cash_conversion_margin": margins[index],
                "growth": growth[index],
                "wacc": policy.wacc[index],
                "terminal_growth": policy.terminal[index],
                "shares": policy.shares[index],
                "bridge_claims": policy.claims + finance_lease_reserve[index],
                "limited_liability_floor_applied": value == 0
                and float(raw["value_per_share"]) < 0,
            }
        )
    scenario = {
        "low": rows[0]["conditional_value_per_share"],
        "base": rows[1]["conditional_value_per_share"],
        "high": rows[2]["conditional_value_per_share"],
    }
    if not (0 <= scenario["low"] <= scenario["base"] <= scenario["high"]):
        raise ValueError(f"{ticker}: unordered range")
    if scenario["base"] <= 0:
        raise ValueError(f"{ticker}: nonpositive base")

    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else (
        "CONDITIONAL_EVENT_MODEL",
        "SPECIALIST_MODEL_UNCERTAINTY",
    )
    reliability = assess_reliability(
        accounting_low=scenario["base"],
        accounting_base=scenario["base"],
        accounting_high=scenario["base"],
        scenario_low=scenario["low"],
        scenario_base=scenario["base"],
        scenario_high=scenario["high"],
        model_cap="High" if is_pass else "Low",
        source_cap="High",
        reasons=reasons,
    )
    public_history = profile.public_metadata()
    if not is_pass:
        public_history.update(
            {
                "normalization_basis": "company_history_with_material_event_override",
                "assumption_source_mix": "reported_history_and_finsight_policy",
            }
        )
    assumptions = {
        **public_history,
        "cash_conversion_margin": margins,
        "growth": growth,
        "wacc": policy.wacc,
        "terminal_growth": policy.terminal,
        "shares": policy.shares,
        "equity_floor_basis": "limited-liability floor after negative residual"
        if scenario["low"] == 0
        else "not applied",
        "calculator_calibration": "Calculator is calibrated to the published base; private history and bridge remain fixed.",
        "invalidation": policy.invalidation,
    }
    if ticker == "SYY":
        assumptions.update(
            {
                "economic_state": "pre_jetro_current_state",
                "normalization_basis": "company_history_current_state_with_pending_transaction_invalidation",
                "pending_transaction_treatment": "Signed Jetro consideration, financing, and expected shares are excluded from intrinsic value and retained only as a separate invalidation event.",
            }
        )
    baseline = BaselineValuation(
        ticker=ticker,
        method=policy.method,
        method_version=model_version,
        low=scenario["low"],
        base=scenario["base"],
        high=scenario["high"],
        confidence=reliability.label,
        availability_type=AvailabilityType.AVAILABLE
        if is_pass
        else AvailabilityType.CONDITIONAL,
        key_assumptions=(
            BaselineAssumption(
                "company history",
                str(profile.history_years_used),
                AssumptionClassification.HISTORICALLY_DERIVED,
                "Source-linked annual history supplies cash-conversion and growth states.",
            ),
            BaselineAssumption(
                "reported anchors",
                str({key: value["value"] for key, value in flows.items()}),
                AssumptionClassification.REPORTED,
                "Cutoff-safe filing facts anchor current cash generation.",
            ),
            BaselineAssumption(
                "scenario policy",
                str(assumptions),
                AssumptionClassification.FINSIGHT_ASSUMPTION,
                "Discount rates, terminal growth, shares, and named dependencies remain transparent assumptions.",
            ),
        ),
        warnings=(policy.warning, policy.invalidation),
        confidence_reasons=tuple(reliability.reasons),
        calculator_link=f"/api/us-valuations/{ticker}/calculator",
    )
    bridge_sources = _bridge(ticker, structural, policy)
    debt_scope = {
        "SYY": "$1.190B current plus $12.818B long-term debt/capital leases equal $14.008B. The disclosed $473M European commercial paper is already classified within long-term debt and is not added again; the $85M supplier-finance obligation stays operating.",
        "MO": "$24.577B total long-term debt already equals current plus noncurrent components.",
        "MDLZ": "$2.327B short-term borrowings plus $2.663B current and $16.460B noncurrent debt/capital leases equal the $21.450B carrying total.",
        "PM": "$3.341B short-term borrowings plus $45.772B current/noncurrent debt and capital leases equal $49.113B; the separate $99M finance-lease disclosure is not added again.",
        "KHC": "$1.382B current plus $17.619B noncurrent debt/capital leases reconcile to approximately $19.001B total debt.",
    }.get(ticker, "Current and noncurrent interest-bearing debt are reconciled once; operating leases stay operating.")
    investment_treatment = {
        "PM": "$1.008B equity-method investment is not added as excess cash. The source ledger binds $17M current H1 distributions to investing cash flow, not OCF; excluding the stake is conservative but keeps the result Conditional until affiliate economics are fully integrated.",
        "MO": "$8.896B investments are not added as excess cash; the source ledger binds $186M current H1 affiliate distributions and the $1.009B settlement-payable cash reduction already inside reported OCF.",
        "MNST": "$2.008146B available-for-sale total equals current plus noncurrent securities and is added once.",
        "COST": "$1.050B short-term investments include $818M AFS and $232M held-to-maturity securities and are added once.",
    }.get(ticker, "Only source-proven cash-like investments are added once.")
    settlement_treatment = (
        "The $1.169B accrued settlement current liability remains operating. Current H1 OCF includes a $1.009B decrease in settlement payable and source-linked annual OCF includes recurring settlement payments; subtracting the current liability again would double-count the same operating cash burden."
        if ticker == "MO"
        else "No separate settlement-liability bridge adjustment is applicable."
    )
    supplier_finance_treatment = {
        "SYY": "The reported $85M supplier-finance obligation remains an operating accounts-payable program already inside OCF; it is not subtracted again as financing debt.",
        "CHD": "The reported $111.9M supply-chain-finance obligation remains in accounts payable and operating cash flow; it is not subtracted again as financing debt.",
        "MO": "The reported $171M supplier-finance obligation remains operating working capital already inside OCF; it is not subtracted again as financing debt.",
        "DLTR": "The reported $298.4M supplier-finance obligation remains operating working capital, and $1.0052B current plus $3.6555B noncurrent operating leases remain post-rent operating items already inside OCF; none is subtracted again as financing debt.",
        "MDLZ": "The reported $2.900B supplier-finance obligation remains operating accounts payable already inside OCF; it is not subtracted again as financing debt.",
        "PM": "The reported $1.000B supplier-finance obligation remains operating accounts payable already inside OCF; it is not subtracted again as financing debt.",
    }.get(
        ticker,
        "No separate supplier-finance or operating-lease financing bridge adjustment is applicable.",
    )
    return {
        "ticker": ticker,
        "method": policy.method,
        "model_version": model_version,
        "availability_type": baseline.availability_type.value,
        "scenario_rows": rows,
        "scenario_range": scenario,
        "reported_inputs": {
            "ttm_revenue": revenue,
            "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"],
            "ttm_capex": flows["capital_expenditures"]["value"],
            "ttm_interest": flows["interest_expense"]["value"],
            "tax_rate": tax_rate,
            "ttm_cash_fcff": current_cash,
        },
        "governed_assumptions": assumptions,
        "history_reliability": reliability.as_dict(),
        "source_ledger": {
            "controlling_filing": filing,
            "flow_sources": flows,
            "company_history_profile": profile.as_private_dict(),
            "bridge_sources": bridge_sources,
            "bridge_reconciliation": {
                "cash_and_investments": policy.cash,
                "debt_and_finance_leases": policy.debt,
                "debt_scope": debt_scope,
                "preferred_nci_and_redeemable_claims": policy.claims,
                "shares": policy.shares,
                "investment_treatment": investment_treatment,
                "settlement_liability_treatment": settlement_treatment,
                "finance_lease_liability_reserve": {
                    "bear": finance_lease_reserve[0],
                    "base": finance_lease_reserve[1],
                    "bull": finance_lease_reserve[2],
                },
                "restricted_cash_treatment": "Restricted cash is disclosed in the ledger and excluded from excess cash.",
                "supplier_finance_and_operating_leases": supplier_finance_treatment,
            },
            "structural_top_level_period_diagnostic": {
                "value": structural.get("period_end"),
                "used_for_selection": False,
            },
        },
        "warning": policy.warning,
        "baseline": baseline.as_private_dict(),
    }


if set(P) != set(BATCH_11_TICKERS):
    raise RuntimeError("Batch 11 policy denominator mismatch")
