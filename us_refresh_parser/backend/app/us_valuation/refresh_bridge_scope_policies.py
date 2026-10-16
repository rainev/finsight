"""Versioned current-filing aggregate-debt scope rules for ordinary FCFF.

Rules describe issuer reporting structure, never a filing accession, date, or
amount. Each run derives those from the selected structural filing and fails
closed when the presentation or arithmetic changes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isclose, isfinite
from numbers import Real
import re
from types import MappingProxyType
from typing import Any, Mapping

from .field_availability import FieldAvailability


BRIDGE_SCOPE_POLICY_VERSION = "FINSIGHT-DEBT-SCOPE-1"
_DEBT_COVERAGE = (
    "commercial_paper", "current_debt", "noncurrent_debt",
    "finance_lease_current", "finance_lease_noncurrent",
)


class BridgeScopeReviewRequired(ValueError):
    """Raised when the current filing no longer proves an approved scope."""


@dataclass(frozen=True)
class AggregateDebtScopeRule:
    ticker: str
    cik: str
    total_qname: str | None
    component_qnames: tuple[str, ...]
    component_local_names: tuple[str, ...] = ()
    issuer_namespace_pattern: str | None = None
    combined_cash_qname: str | None = None
    searched_separate_cash_qnames: tuple[str, ...] = ()
    commercial_paper_qname: str | None = None
    commercial_paper_axis: str | None = None
    commercial_paper_member: str | None = None
    excluded_investment_total_qname: str | None = None
    excluded_investment_component_qnames: tuple[str, ...] = ()
    excluded_investment_parent_qname: str | None = None
    searched_marketable_qnames: tuple[str, ...] = ()
    zero_marketable_fields: tuple[str, ...] = ()
    direct_marketable_qnames: tuple[str, ...] = ()
    zero_debt_search_qnames: tuple[str, ...] = ()
    excluded_zero_debt_qnames: tuple[str, ...] = ()
    prefer_most_precise_components: bool = False
    marketable_zero_witness_qnames: tuple[str, ...] = (
        "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets", "us-gaap:Liabilities",
    )
    version: str = BRIDGE_SCOPE_POLICY_VERSION


AGGREGATE_DEBT_SCOPE_RULES: Mapping[str, AggregateDebtScopeRule] = MappingProxyType({
    "BBY": AggregateDebtScopeRule(
        ticker="BBY", cik="0000764478",
        total_qname="us-gaap:DebtAndCapitalLeaseObligations",
        component_qnames=("us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
            "us-gaap:LongTermDebtAndCapitalLeaseObligations"),
        excluded_zero_debt_qnames=("us-gaap:CommercialPaper","us-gaap:CommercialPaperAtCarryingValue",
            "us-gaap:ShortTermBorrowings","us-gaap:DebtCurrent"),
        version="FINSIGHT-DEBT-SCOPE-BBY-COMPONENT-1",
    ),
    "WMT": AggregateDebtScopeRule(
        ticker="WMT", cik="0000104169", total_qname=None,
        component_qnames=(
            "us-gaap:ShortTermBorrowings",
            "us-gaap:LongTermDebtCurrent",
            "us-gaap:LongTermDebtNoncurrent",
            "us-gaap:FinanceLeaseLiabilityCurrent",
            "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent",
            "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities",
            "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments",
            "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            "us-gaap:Assets",
            "us-gaap:LiabilitiesAndStockholdersEquity",
            "us-gaap:StockholdersEquity",
        ),
        version="FINSIGHT-DEBT-SCOPE-WMT-COMPONENT-1",
    ),
    "ABT": AggregateDebtScopeRule(
        ticker="ABT", cik="0000001800", total_qname=None,
        component_qnames=("us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        excluded_zero_debt_qnames=(
            "us-gaap:CommercialPaper", "us-gaap:CommercialPaperAtCarryingValue",
            "us-gaap:ShortTermBorrowings", "us-gaap:DebtCurrent",
            "us-gaap:FinanceLeaseLiability", "us-gaap:FinanceLeaseLiabilityCurrent",
            "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
        excluded_investment_total_qname="us-gaap:LongTermInvestments",
        excluded_investment_parent_qname="us-gaap:AssetsAbstract",
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
    ),
    "ABBV": AggregateDebtScopeRule(
        ticker="ABBV", cik="0001551152", total_qname=None,
        component_qnames=("us-gaap:ShortTermBorrowings",
            "us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
            "us-gaap:LongTermDebtAndCapitalLeaseObligations"),
    ),
    "AVY": AggregateDebtScopeRule(
        ticker="AVY", cik="0000008818", total_qname=None,
        component_qnames=("us-gaap:DebtCurrent", "us-gaap:LongTermDebtAndCapitalLeaseObligations"),
    ),
    "AOS": AggregateDebtScopeRule(
        ticker="AOS", cik="0000091142", total_qname=None,
        component_qnames=("us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesNoncurrent", "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent", "us-gaap:LongTermInvestments",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
    ),
    "BALL": AggregateDebtScopeRule(
        ticker="BALL", cik="0000009389",
        total_qname="us-gaap:LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
        component_qnames=(),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
    ),
    "COO": AggregateDebtScopeRule(
        ticker="COO", cik="0000711404", total_qname="us-gaap:DebtLongtermAndShorttermCombinedAmount",
        component_qnames=("us-gaap:DebtCurrent","us-gaap:LongTermDebtAndCapitalLeaseObligations"),
        direct_marketable_qnames=("us-gaap:CashAndCashEquivalentsAtCarryingValue",),
        searched_marketable_qnames=("us-gaap:MarketableSecuritiesCurrent","us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities","us-gaap:ShortTermInvestments","us-gaap:LongTermInvestments",
            "us-gaap:AvailableForSaleSecuritiesCurrent","us-gaap:AvailableForSaleSecuritiesNoncurrent"),
        zero_marketable_fields=("marketable_securities_current","marketable_securities_noncurrent"),
    ),
    "COHR": AggregateDebtScopeRule(
        ticker="COHR", cik="0000820318", total_qname=None,
        component_qnames=("us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent", "us-gaap:FinanceLeaseLiability"),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesNoncurrent", "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent", "us-gaap:LongTermInvestments",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
    ),
    "CTSH": AggregateDebtScopeRule(
        ticker="CTSH", cik="0001058290", total_qname=None,
        component_qnames=("us-gaap:ShortTermBorrowings", "us-gaap:LongTermDebtNoncurrent"),
    ),
    "CRWD": AggregateDebtScopeRule(
        ticker="CRWD", cik="0001535527", total_qname="us-gaap:LongTermDebtNoncurrent",
        component_qnames=(),
        excluded_zero_debt_qnames=(
            "us-gaap:CommercialPaper", "us-gaap:CommercialPaperAtCarryingValue",
            "us-gaap:ShortTermBorrowings", "us-gaap:DebtCurrent", "us-gaap:LongTermDebtCurrent",
            "us-gaap:FinanceLeaseLiability", "us-gaap:FinanceLeaseLiabilityCurrent",
            "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets",
            "us-gaap:LiabilitiesAndStockholdersEquity", "us-gaap:StockholdersEquity",
        ),
    ),
    "DASH": AggregateDebtScopeRule(
        ticker="DASH", cik="0001792789", total_qname="us-gaap:ConvertibleLongTermNotesPayable",
        component_qnames=(),
    ),
    "DGX": AggregateDebtScopeRule(
        ticker="DGX", cik="0001022079", total_qname="us-gaap:LongTermDebt",
        component_qnames=("us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        excluded_zero_debt_qnames=(
            "us-gaap:CommercialPaper", "us-gaap:CommercialPaperAtCarryingValue",
            "us-gaap:ShortTermBorrowings", "us-gaap:DebtCurrent",
            "us-gaap:FinanceLeaseLiability", "us-gaap:FinanceLeaseLiabilityCurrent",
            "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets",
            "us-gaap:LiabilitiesAndStockholdersEquity", "us-gaap:StockholdersEquity",
        ),
    ),
    "ECL": AggregateDebtScopeRule(
        ticker="ECL", cik="0000031462", total_qname="us-gaap:DebtAndCapitalLeaseObligations",
        component_qnames=("us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
                          "us-gaap:LongTermDebtAndCapitalLeaseObligations"),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
    ),
    "ETN": AggregateDebtScopeRule(
        ticker="ETN",cik="0001551182",total_qname=None,
        component_qnames=("us-gaap:ShortTermBorrowings",
            "us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
            "us-gaap:LongTermDebtAndCapitalLeaseObligations"),
        searched_marketable_qnames=("us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent","us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
            "us-gaap:LongTermInvestments"),
        zero_marketable_fields=("marketable_securities_noncurrent",),
        marketable_zero_witness_qnames=("us-gaap:Assets","us-gaap:LiabilitiesAndStockholdersEquity",
            "us-gaap:StockholdersEquity"),
    ),
    "DVA": AggregateDebtScopeRule(
        ticker="DVA", cik="0000927066",
        total_qname="us-gaap:LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
        component_qnames=(
            "us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
            "us-gaap:LongTermDebtAndCapitalLeaseObligations",
        ),
        excluded_zero_debt_qnames=(
            "us-gaap:CommercialPaper", "us-gaap:CommercialPaperAtCarryingValue",
            "us-gaap:ShortTermBorrowings", "us-gaap:DebtCurrent",
        ),
    ),
    "GLW": AggregateDebtScopeRule(
        ticker="GLW", cik="0000024741", total_qname=None,
        component_qnames=("us-gaap:DebtCurrent", "us-gaap:LongTermDebtAndCapitalLeaseObligations"),
        prefer_most_precise_components=True,
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets",
            "us-gaap:LiabilitiesAndStockholdersEquity", "us-gaap:StockholdersEquity",
        ),
    ),
    "HSIC": AggregateDebtScopeRule(
        ticker="HSIC", cik="0001000228", total_qname=None,
        component_qnames=("us-gaap:ShortTermBorrowings",),
        component_local_names=("LongTermDebtAndFinanceLeaseObligationsIncludingCurrentMaturities",),
        issuer_namespace_pattern=r"https?://(?:www\.)?henryschein\.com/\d{8}",
        combined_cash_qname="us-gaap:CashCashEquivalentsAndShortTermInvestments",
        searched_separate_cash_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:ShortTermInvestments",
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:LongTermInvestments",
        ),
    ),
    "MCO": AggregateDebtScopeRule(
        ticker="MCO", cik="0001059556", total_qname="us-gaap:LongTermDebt",
        component_qnames=("us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        excluded_investment_total_qname="us-gaap:LongTermInvestments",
        excluded_investment_parent_qname="us-gaap:OtherAssetsAbstract",
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
    ),
    "MDT": AggregateDebtScopeRule(
        ticker="MDT", cik="0001613103", total_qname="us-gaap:DebtInstrumentCarryingAmount",
        component_qnames=(),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesNoncurrent", "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent", "us-gaap:LongTermInvestments",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets",
            "us-gaap:Liabilities", "us-gaap:StockholdersEquity",
        ),
    ),
    "MCHP": AggregateDebtScopeRule(
        ticker="MCHP", cik="0000827054", total_qname="us-gaap:DebtInstrumentCarryingAmount",
        component_qnames=(),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments", "us-gaap:LongTermInvestments",
            "us-gaap:AvailableForSaleSecuritiesCurrent", "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets",
            "us-gaap:LiabilitiesAndStockholdersEquity", "us-gaap:StockholdersEquity",
        ),
    ),
    "PH": AggregateDebtScopeRule(
        ticker="PH", cik="0000076334", total_qname=None,
        component_qnames=("us-gaap:CommercialPaper",
                          "us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
                          "us-gaap:LongTermDebtAndCapitalLeaseObligations"),
    ),
    "ICE": AggregateDebtScopeRule(
        ticker="ICE", cik="0001571949", total_qname="us-gaap:DebtLongtermAndShorttermCombinedAmount",
        component_qnames=("us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
    ),
    "KDP": AggregateDebtScopeRule(
        ticker="KDP",cik="0001418135",total_qname=None,
        component_qnames=("us-gaap:DebtCurrent","us-gaap:LongTermDebtNoncurrent","us-gaap:FinanceLeaseLiability"),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent","us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities","us-gaap:ShortTermInvestments","us-gaap:LongTermInvestments",
            "us-gaap:AvailableForSaleSecuritiesCurrent","us-gaap:AvailableForSaleSecuritiesNoncurrent"),
        zero_marketable_fields=("marketable_securities_current","marketable_securities_noncurrent"),
    ),
    "MPC": AggregateDebtScopeRule(
        ticker="MPC", cik="0001510295",
        total_qname="us-gaap:DebtAndCapitalLeaseObligations", component_qnames=(),
        excluded_investment_total_qname="us-gaap:EquityMethodInvestments",
        excluded_investment_parent_qname="us-gaap:AssetsAbstract",
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
    ),
    "PFE": AggregateDebtScopeRule(
        ticker="PFE", cik="0000078003", total_qname=None,
        component_qnames=("us-gaap:DebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        excluded_zero_debt_qnames=(
            "us-gaap:FinanceLeaseLiability", "us-gaap:FinanceLeaseLiabilityCurrent",
            "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
    ),
    "ON": AggregateDebtScopeRule(
        ticker="ON", cik="0001097864",
        total_qname="us-gaap:LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
        component_qnames=(),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesNoncurrent", "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent", "us-gaap:LongTermInvestments",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets",
            "us-gaap:LiabilitiesAndStockholdersEquity", "us-gaap:StockholdersEquity",
        ),
    ),
    "MRK": AggregateDebtScopeRule(
        ticker="MRK",cik="0000310158",total_qname=None,
        component_qnames=("us-gaap:DebtCurrent","us-gaap:LongTermDebtNoncurrent"),
    ),
    "MU": AggregateDebtScopeRule(
        ticker="MU",cik="0000723125",total_qname="us-gaap:DebtAndCapitalLeaseObligations",
        component_qnames=(),
    ),
    "MSCI": AggregateDebtScopeRule(
        ticker="MSCI",cik="0001408198",total_qname="us-gaap:LongTermDebtNoncurrent",
        component_qnames=(),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent","us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities","us-gaap:ShortTermInvestments","us-gaap:LongTermInvestments",
            "us-gaap:AvailableForSaleSecuritiesCurrent","us-gaap:AvailableForSaleSecuritiesNoncurrent"),
        zero_marketable_fields=("marketable_securities_current","marketable_securities_noncurrent"),
    ),
    "NUE": AggregateDebtScopeRule(
        ticker="NUE", cik="0000073309", total_qname=None,
        component_qnames=(
            "us-gaap:ShortTermBorrowings",
            "us-gaap:LongTermDebtAndCapitalLeaseObligationsCurrent",
            "us-gaap:LongTermDebtAndCapitalLeaseObligations",
        ),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
            "us-gaap:LongTermInvestments",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
    ),
    "ROK": AggregateDebtScopeRule(
        ticker="ROK", cik="0001024478", total_qname=None,
        component_qnames=("us-gaap:ShortTermBorrowings", "us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        commercial_paper_qname="us-gaap:ShortTermBorrowings",
        commercial_paper_axis="us-gaap:ShortTermDebtTypeAxis",
        commercial_paper_member="us-gaap:CommercialPaperMember",
        excluded_investment_total_qname="us-gaap:LongTermInvestments",
        excluded_investment_component_qnames=(
            "us-gaap:EquitySecuritiesWithoutReadilyDeterminableFairValueAmount",
            "us-gaap:OtherLongTermInvestments",
        ),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent",
            "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities",
            "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
            "us-gaap:ShortTermInvestments",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
    ),
    "STLD": AggregateDebtScopeRule(
        ticker="STLD", cik="0001022671", total_qname=None,
        component_qnames=("us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
    ),
    "TEL": AggregateDebtScopeRule(
        ticker="TEL", cik="0001385157", total_qname=None,
        component_qnames=("us-gaap:DebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets",
            "us-gaap:LiabilitiesAndStockholdersEquity",
            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ),
    ),
    "VRTX": AggregateDebtScopeRule(
        ticker="VRTX", cik="0000875320", total_qname=None, component_qnames=(),
        zero_debt_search_qnames=(
            "us-gaap:CommercialPaper", "us-gaap:ShortTermBorrowings", "us-gaap:DebtCurrent",
            "us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent", "us-gaap:LongTermDebt",
            "us-gaap:DebtInstrumentCarryingAmount", "us-gaap:DebtLongtermAndShorttermCombinedAmount",
            "us-gaap:DebtAndCapitalLeaseObligations", "us-gaap:FinanceLeaseLiability",
            "us-gaap:FinanceLeaseLiabilityCurrent", "us-gaap:FinanceLeaseLiabilityNoncurrent",
        ),
    ),
    "VRT": AggregateDebtScopeRule(
        ticker="VRT", cik="0001674101", total_qname="us-gaap:LongTermDebt",
        component_qnames=(),
        direct_marketable_qnames=(
            "us-gaap:DebtSecuritiesHeldToMaturityAmortizedCostAfterAllowanceForCreditLossCurrent",
        ),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesNoncurrent", "us-gaap:AvailableForSaleSecuritiesNoncurrent",
            "us-gaap:AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
            "us-gaap:DebtSecuritiesHeldToMaturityAmortizedCostAfterAllowanceForCreditLossNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_noncurrent",),
    ),
    "ZBH": AggregateDebtScopeRule(
        ticker="ZBH", cik="0001136869", total_qname=None,
        component_qnames=("us-gaap:LongTermDebtCurrent", "us-gaap:LongTermDebtNoncurrent"),
        searched_marketable_qnames=(
            "us-gaap:MarketableSecuritiesCurrent", "us-gaap:MarketableSecuritiesNoncurrent",
            "us-gaap:MarketableSecurities", "us-gaap:ShortTermInvestments",
            "us-gaap:LongTermInvestments", "us-gaap:AvailableForSaleSecuritiesCurrent",
            "us-gaap:AvailableForSaleSecuritiesNoncurrent",
        ),
        zero_marketable_fields=("marketable_securities_current", "marketable_securities_noncurrent"),
        marketable_zero_witness_qnames=(
            "us-gaap:CashAndCashEquivalentsAtCarryingValue", "us-gaap:Assets",
            "us-gaap:LiabilitiesAndStockholdersEquity", "us-gaap:StockholdersEquity",
        ),
    ),
})

OUTSIDE_EQUITY_ZERO_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    **{
        ticker: MappingProxyType({"version":"FINSIGHT-OUTSIDE-EQUITY-ZERO-1","ticker":ticker,"cik":cik})
        for ticker,cik in {
            "AOS":"0000091142", "BIIB":"0000875045", "CTSH":"0001058290", "MSCI":"0001408198", "VRTX":"0000875320", "VRT":"0001674101",
            "INCY":"0000879169",
        }.items()
    },
    "MCHP":MappingProxyType({
        "version":"FINSIGHT-OUTSIDE-EQUITY-ZERO-1","ticker":"MCHP","cik":"0000827054",
        "basis":"parent_equity_and_complete_nci_search",
    }),
})

PREFERRED_EQUITY_ZERO_RULES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "WMT":MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-WMT-1","ticker":"WMT","cik":"0000104169",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapital",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1)),
    }),
    "BIIB":MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-WG40-1","ticker":"BIIB","cik":"0000875045",
        "parent_qname":"us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapital",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockValue",-1)),
    }),
    "ETN":MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-WG22-1","ticker":"ETN","cik":"0001551182",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValueOutstanding",1),
            ("us-gaap:AdditionalPaidInCapitalCommonStock",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1)),
        "allow_source_rounding":True,
        "minimum_source_decimals":-6,
    }),
    "ABBV": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"ABBV","cik":"0001551152",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValueOutstanding",1),("us-gaap:AdditionalPaidInCapitalCommonStock",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockValue",-1)),
    }),
    "BALL": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"BALL","cik":"0000009389",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockCommonValue",-1)),
    }),
    "DASH": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"DASH","cik":"0001792789",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),
            ("us-gaap:AdditionalPaidInCapital",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1)),
        "allowed_outside_equity_qnames":(
            "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        ),
    }),
    "ECL": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"ECL","cik":"0000031462",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),
            ("us-gaap:AdditionalPaidInCapitalCommonStock",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockCommonValue",-1)),
    }),
    "CRWD": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"CRWD","cik":"0001535527",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapital",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1)),
    }),
    "GLW": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"GLW","cik":"0000024741",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapitalCommonStock",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockCommonValue",-1)),
    }),
    "HSIC": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"HSIC","cik":"0001000228",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValueOutstanding",1),("us-gaap:AdditionalPaidInCapital",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1)),
        "allowed_outside_equity_qnames":(
            "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        ),
    }),
    "MSCI": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"MSCI","cik":"0001408198",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),
            ("us-gaap:AdditionalPaidInCapitalCommonStock",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockCommonValue",-1)),
    }),
    "KDP": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"KDP","cik":"0001418135",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),
            ("us-gaap:AdditionalPaidInCapitalCommonStock",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1)),
        "allowed_outside_equity_qnames":(
            "us-gaap:TemporaryEquityCarryingAmountAttributableToParent",
            "us-gaap:TemporaryEquityLiquidationPreference",
        ),
    }),
    "MCHP": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"MCHP","cik":"0000827054",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapitalCommonStock",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockValue",-1)),
        "allowed_outside_equity_qnames":(
            "us-gaap:PreferredStockLiquidationPreferenceValue","us-gaap:PreferredStockLiquidationPreference",
        ),
    }),
    "MDT": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"MDT","cik":"0001613103",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapital",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1)),
        "par_only_qnames":("us-gaap:PreferredStockParOrStatedValuePerShare",),
        "zero_preferred_share_qnames":("us-gaap:PreferredStockSharesIssued",),
    }),
    "PFE": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"PFE","cik":"0000078003",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapital",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockCommonValue",-1)),
    }),
    "TEL": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"TEL","cik":"0001385157",
        "parent_qname":"us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:RetainedEarningsAccumulatedDeficit",1),
            ("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),("us-gaap:TreasuryStockCommonValue",-1)),
        "par_only_qnames":("us-gaap:PreferredStockParOrStatedValuePerShare",),
        "zero_preferred_share_qnames":("us-gaap:PreferredStockSharesOutstanding",),
    }),
    "ON": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"ON","cik":"0001097864",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapital",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockCommonValue",-1)),
    }),
    "ZBH": MappingProxyType({
        "version":"FINSIGHT-PREFERRED-EQUITY-ZERO-1","ticker":"ZBH","cik":"0001136869",
        "parent_qname":"us-gaap:StockholdersEquity",
        "components":(("us-gaap:CommonStockValue",1),("us-gaap:AdditionalPaidInCapitalCommonStock",1),
            ("us-gaap:RetainedEarningsAccumulatedDeficit",1),("us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",1),
            ("us-gaap:TreasuryStockValue",-1)),
    }),
})


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise BridgeScopeReviewRequired(f"{label} is not finite numeric evidence")
    result = float(value)
    if not isfinite(result) or result < 0:
        raise BridgeScopeReviewRequired(f"{label} is not finite nonnegative evidence")
    return result


def _finite_signed(value: Any,label: str) -> float:
    if isinstance(value,bool) or not isinstance(value,Real) or not isfinite(float(value)):
        raise BridgeScopeReviewRequired(f"{label} is not finite numeric evidence")
    return float(value)


def _validated_rule(ticker: str, policy: Mapping[str, Any]) -> AggregateDebtScopeRule:
    rule = AGGREGATE_DEBT_SCOPE_RULES.get(ticker)
    if rule is None:
        raise BridgeScopeReviewRequired(f"no aggregate debt scope rule for {ticker!r}")
    expected, actual = asdict(rule), dict(policy)
    for field in ("component_qnames", "component_local_names", "searched_separate_cash_qnames", "excluded_investment_component_qnames", "searched_marketable_qnames", "zero_marketable_fields", "direct_marketable_qnames", "zero_debt_search_qnames", "excluded_zero_debt_qnames", "marketable_zero_witness_qnames"):
        expected[field] = tuple(expected.get(field, ()))
        actual[field] = tuple(actual.get(field, ()))
    if actual != expected:
        raise BridgeScopeReviewRequired("aggregate debt policy identity/version mismatch")
    return rule


def _current_rows(structural_packet: Mapping[str, Any], *, rule: AggregateDebtScopeRule,
                  accession: str, period_end: str) -> list[Mapping[str, Any]]:
    if structural_packet.get("source_accession") != accession:
        raise BridgeScopeReviewRequired("structural packet accession mismatch")
    if (structural_packet.get("report_date") or structural_packet.get("period_end")) != period_end:
        raise BridgeScopeReviewRequired("structural packet report period mismatch")
    facts = structural_packet.get("facts")
    if not isinstance(facts, list):
        raise BridgeScopeReviewRequired("structural packet has no facts")
    rows = [row for row in facts if isinstance(row, Mapping)
            and row.get("source_accession") == accession and row.get("period_end") == period_end
            and row.get("period_start") is None and row.get("unit") == "USD"
            and row.get("entity_scheme") == "http://www.sec.gov/CIK"
            and str(row.get("entity_identifier", "")).zfill(10) == rule.cik]
    if not rows:
        raise BridgeScopeReviewRequired("no current issuer USD facts")
    return rows


def _one_undimensioned(rows: list[Mapping[str, Any]], qname: str) -> Mapping[str, Any]:
    matches = [row for row in rows if row.get("qname") == qname and row.get("dimensions") in (None, [])]
    values = {_finite(row.get("value"), qname) for row in matches}
    if not matches:
        raise BridgeScopeReviewRequired(f"required aggregate debt fact is missing: {qname}")
    if len(values) != 1:
        raise BridgeScopeReviewRequired(f"required aggregate debt fact conflicts: {qname}")
    return matches[0]


def _one_issuer_local(rows: list[Mapping[str, Any]], local_name: str, namespace_pattern: str | None) -> Mapping[str, Any]:
    if namespace_pattern is None:
        raise BridgeScopeReviewRequired(f"issuer debt namespace rule is missing: {local_name}")
    matches=[row for row in rows if row.get("local_name")==local_name
             and row.get("dimensions") in (None,[])
             and re.fullmatch(namespace_pattern,str(row.get("namespace","")))]
    values={_finite(row.get("value"),local_name) for row in matches}
    if not matches:
        raise BridgeScopeReviewRequired(f"required issuer debt fact is missing: {local_name}")
    if len(values)!=1:
        raise BridgeScopeReviewRequired(f"required issuer debt fact conflicts: {local_name}")
    return matches[0]


def _one_most_precise_undimensioned(rows: list[Mapping[str, Any]], qname: str) -> Mapping[str, Any]:
    """Select the most precise compatible duplicate from one source context.

    Inline filings sometimes expose the same balance twice at different
    display precision.  The coarser row may differ numerically after scaling,
    so exact-value deduplication would incorrectly reject the filing.  This
    selector accepts that shape only when every row shares one context and the
    precise value falls inside each row's declared rounding interval.
    """
    matches=[row for row in rows if row.get("qname")==qname and row.get("dimensions") in (None,[])]
    if not matches:
        raise BridgeScopeReviewRequired(f"required aggregate debt fact is missing: {qname}")
    contexts={row.get("context_id") for row in matches}
    if len(contexts)!=1 or None in contexts:
        raise BridgeScopeReviewRequired(f"precision-compatible debt facts have different contexts: {qname}")
    parsed=[]
    for row in matches:
        value=_finite(row.get("value"),qname)
        try: decimals=int(str(row.get("decimals")))
        except (TypeError,ValueError) as exc:
            raise BridgeScopeReviewRequired(f"precision-compatible debt fact has invalid decimals: {qname}") from exc
        parsed.append((decimals,value,row))
    precise_decimals,precise_value,precise_row=max(parsed,key=lambda item:item[0])
    for decimals,value,_row in parsed:
        tolerance=0.5*(10.0**(-decimals))
        if abs(value-precise_value)>tolerance:
            raise BridgeScopeReviewRequired(f"rounded debt presentation conflicts with precise fact: {qname}")
    return precise_row


def _one_undimensioned_signed(rows: list[Mapping[str,Any]],qname: str) -> Mapping[str,Any]:
    matches=[row for row in rows if row.get("qname")==qname and row.get("dimensions") in (None,[])]
    values={_finite_signed(row.get("value"),qname) for row in matches}
    if not matches: raise BridgeScopeReviewRequired(f"required equity fact is missing: {qname}")
    if len(values)!=1: raise BridgeScopeReviewRequired(f"required equity fact conflicts: {qname}")
    return matches[0]


def _source_ref(accession: str, period_end: str, row: Mapping[str, Any]) -> str:
    context = row.get("context_id")
    if not isinstance(context, str) or not context:
        raise BridgeScopeReviewRequired("aggregate debt source context is missing")
    return f"{accession}|{period_end}|{row['qname']}|{context}"


def aggregate_debt_field_availability(*, ticker: str, policy: Mapping[str, Any],
                                      structural_packet: Mapping[str, Any], accession: str,
                                      period_end: str) -> tuple[FieldAvailability, dict[str, Any]]:
    """Return one exact total-debt point with complete overlap coverage."""
    rule = _validated_rule(ticker, policy)
    rows = _current_rows(structural_packet, rule=rule, accession=accession, period_end=period_end)
    if rule.zero_debt_search_qnames:
        metadata = dict(structural_packet.get("filing_metadata", ()))
        if metadata.get("manifest_version") != "FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
            raise BridgeScopeReviewRequired("complete structural filing package receipt is required")
        debt_rows = [row for row in rows if row.get("qname") in set(rule.zero_debt_search_qnames)]
        if any(_finite(row.get("value"), str(row.get("qname"))) != 0 for row in debt_rows):
            raise BridgeScopeReviewRequired("nonzero current debt fact conflicts with zero-debt scope")
        witnesses = [_one_undimensioned(rows,qname) for qname in (
            "us-gaap:Assets","us-gaap:Liabilities","us-gaap:StockholdersEquity")]
        refs = tuple(_source_ref(accession,period_end,row) for row in (*witnesses,*debt_rows))
        availability = FieldAvailability(
            field="total_interest_bearing_debt", value=0.0, state="evidence_backed_zero",
            reason_code="COMPLETE_CURRENT_DEBT_SCOPE_ZERO", period_end=period_end,
            source_accession=accession, source_kind="practical_policy",
            evidence_class="reported_component_reconciliation", freshness="current",
            fallback_level="reported_aggregate", covered_fields=_DEBT_COVERAGE,
            coverage_basis="reconciled_disjoint_components", coverage_source_facts=refs,
            economic_scope="complete current balance-sheet debt and finance-lease concept scope",
            extraction_complete=True, searched_concepts=rule.zero_debt_search_qnames,
            authority="production", mapping_version=rule.version)
        return availability, {"status":"source_bound","policy_version":rule.version,
            "ticker":ticker,"accession":accession,"period_end":period_end,"total":0.0,
            "basis":"complete current structural debt scope contains no nonzero financing fact",
            "components":[{"qname":row["qname"],"value":float(row["value"]),
                           "context_id":row.get("context_id"),"dimensions":row.get("dimensions") or []}
                          for row in debt_rows]}
    component_selector=_one_most_precise_undimensioned if rule.prefer_most_precise_components else _one_undimensioned
    components = [component_selector(rows, qname) for qname in rule.component_qnames]
    components.extend(_one_issuer_local(rows,local_name,rule.issuer_namespace_pattern)
                      for local_name in rule.component_local_names)
    component_total = sum(_finite(row["value"], str(row["qname"])) for row in components)
    sources = list(components)
    if rule.total_qname is not None:
        total_row = _one_undimensioned(rows, rule.total_qname)
        total = _finite(total_row["value"], rule.total_qname)
        if components and not isclose(total, component_total, rel_tol=1e-12, abs_tol=0.01):
            raise BridgeScopeReviewRequired("reported total debt does not reconcile to disjoint components")
        sources.append(total_row)
        basis = ("direct issuer total reconciled to disjoint current and noncurrent components"
                 if components else "direct issuer total with complete debt-component coverage")
    else:
        total, basis = component_total, "calculation relationship over disjoint issuer debt subtotals"

    if rule.excluded_zero_debt_qnames:
        metadata = dict(structural_packet.get("filing_metadata", ()))
        if metadata.get("manifest_version") != "FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
            raise BridgeScopeReviewRequired("complete structural filing package receipt is required")
        excluded_rows = [row for row in rows if row.get("qname") in set(rule.excluded_zero_debt_qnames)]
        if any(_finite(row.get("value"), str(row.get("qname"))) != 0 for row in excluded_rows):
            raise BridgeScopeReviewRequired("additional current financing fact conflicts with component debt scope")
        sources.extend(excluded_rows)

    if rule.commercial_paper_qname is not None:
        expected_dimensions = [[rule.commercial_paper_axis, rule.commercial_paper_member]]
        matches = [row for row in rows if row.get("qname") == rule.commercial_paper_qname
                   and row.get("dimensions") == expected_dimensions]
        values = {_finite(row.get("value"), "commercial paper component") for row in matches}
        if not matches or len(values) != 1:
            raise BridgeScopeReviewRequired("dimensioned commercial paper component is missing or conflicting")
        if values.pop() > _finite(components[0]["value"], "short-term debt total"):
            raise BridgeScopeReviewRequired("commercial paper exceeds its short-term debt aggregate")
        sources.append(matches[0])

    coverage_refs = tuple(_source_ref(accession, period_end, row) for row in sources)
    qnames = tuple(sorted(set(row["qname"] for row in sources)))
    availability = FieldAvailability(
        field="total_interest_bearing_debt", value=total, state="reported",
        reason_code="AGGREGATE_DEBT_SCOPE_VERIFIED", period_end=period_end,
        source_accession=accession, source_kind="practical_policy",
        evidence_class="reported_component_reconciliation", freshness="current",
        fallback_level="reported_aggregate", covered_fields=_DEBT_COVERAGE,
        coverage_basis="calculation_relationship", coverage_source_facts=coverage_refs,
        economic_scope="all current and noncurrent interest-bearing debt and finance-lease obligations, counted once",
        extraction_complete=True, searched_concepts=qnames, authority="production",
        mapping_version=rule.version,
    )
    proof = {
        "status": "source_bound", "policy_version": rule.version, "ticker": ticker,
        "accession": accession, "period_end": period_end, "total": total, "basis": basis,
        "components": [{"qname": row["qname"], "value": float(row["value"]),
                        "context_id": row.get("context_id"), "dimensions": row.get("dimensions") or []}
                       for row in sources],
    }
    return availability, proof


def combined_cash_scope_availabilities(*,ticker: str,policy: Mapping[str,Any],
                                       structural_packet: Mapping[str,Any],accession: str,
                                       period_end: str) -> tuple[tuple[FieldAvailability,...],dict[str,Any]]:
    """Bind one reported cash-plus-short-investments total without duplication."""
    rule=_validated_rule(ticker,policy)
    if not rule.combined_cash_qname or not rule.searched_separate_cash_qnames:
        raise BridgeScopeReviewRequired("combined cash scope rule is incomplete")
    metadata=dict(structural_packet.get("filing_metadata",()))
    if metadata.get("manifest_version")!="FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
        raise BridgeScopeReviewRequired("complete structural filing package receipt is required")
    rows=_current_rows(structural_packet,rule=rule,accession=accession,period_end=period_end)
    total_row=_one_undimensioned(rows,rule.combined_cash_qname)
    total=_finite(total_row["value"],rule.combined_cash_qname)
    conflicts=[row for row in rows if row.get("qname") in set(rule.searched_separate_cash_qnames)
               and _finite(row.get("value"),str(row.get("qname")))!=0]
    if conflicts:
        raise BridgeScopeReviewRequired("separate cash or investment fact conflicts with combined cash scope")
    sources=[total_row,*[row for row in rows if row.get("qname") in set(rule.searched_separate_cash_qnames)]]
    refs=tuple(_source_ref(accession,period_end,row) for row in sources)
    common={"period_end":period_end,"source_accession":accession,"source_kind":"practical_policy",
            "evidence_class":"reported_component_reconciliation","freshness":"current",
            "fallback_level":"reported_aggregate","coverage_basis":"reconciled_disjoint_components",
            "coverage_source_facts":refs,"extraction_complete":True,
            "searched_concepts":tuple((rule.combined_cash_qname,*rule.searched_separate_cash_qnames)),
            "authority":"production","mapping_version":rule.version}
    records=(
        FieldAvailability(field="cash",value=total,state="reported",
            reason_code="COMBINED_CASH_AND_SHORT_INVESTMENTS_REPORTED",covered_fields=("cash",),
            economic_scope="reported cash, cash equivalents and short-term investments counted once",**common),
        FieldAvailability(field="marketable_securities_current",value=0.,state="evidence_backed_zero",
            reason_code="COMBINED_CASH_SCOPE_PREVENTS_DUPLICATE_CURRENT_INVESTMENTS",
            covered_fields=("marketable_securities_current",),
            economic_scope="current marketable investments are contained in the reported combined cash total",**common),
        FieldAvailability(field="marketable_securities_noncurrent",value=0.,state="evidence_backed_zero",
            reason_code="COMPLETE_COMBINED_CASH_SCOPE_HAS_NO_NONCURRENT_INVESTMENTS",
            covered_fields=("marketable_securities_noncurrent",),
            economic_scope="complete current filing reports no separate noncurrent cash-like investment",**common),
    )
    return records,{"status":"source_bound","policy_version":rule.version,"ticker":ticker,
        "accession":accession,"period_end":period_end,"combined_cash_and_short_investments":total,
        "separate_cash_or_investment_rows":[{"qname":row["qname"],"value":float(row["value"])} for row in sources[1:]]}


def nonmarketable_investment_zero_availabilities(*, ticker: str, policy: Mapping[str, Any],
                                                 structural_packet: Mapping[str, Any], accession: str,
                                                 period_end: str) -> tuple[tuple[FieldAvailability, ...], dict[str, Any]]:
    """Prove that a reported investment balance is not cash-like securities.

    This is not a missing-tag zero: it requires a complete structural package,
    a reported investment total, a full component reconciliation, and an
    exhaustive current search for the approved marketable-security concepts.
    """
    rule = _validated_rule(ticker, policy)
    if not ((rule.excluded_investment_total_qname and (
        rule.excluded_investment_component_qnames or rule.excluded_investment_parent_qname
    )) or rule.direct_marketable_qnames or (rule.zero_marketable_fields and rule.searched_marketable_qnames)):
        raise BridgeScopeReviewRequired("no nonmarketable investment scope rule")
    metadata = dict(structural_packet.get("filing_metadata", ()))
    if metadata.get("manifest_version") != "FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
        raise BridgeScopeReviewRequired("complete structural filing package receipt is required")
    rows = _current_rows(structural_packet, rule=rule, accession=accession, period_end=period_end)
    unexpected = [row for row in rows if row.get("qname") in set(rule.searched_marketable_qnames)]
    if unexpected:
        raise BridgeScopeReviewRequired("current marketable-security fact requires direct classification")
    total = None
    if rule.excluded_investment_total_qname:
        total_row = _one_undimensioned(rows, rule.excluded_investment_total_qname)
        component_rows = [_one_undimensioned(rows, qname) for qname in rule.excluded_investment_component_qnames]
        total = _finite(total_row["value"], rule.excluded_investment_total_qname)
        if component_rows:
            component_total = sum(_finite(row["value"], str(row["qname"])) for row in component_rows)
            if not isclose(total, component_total, rel_tol=1e-12, abs_tol=0.01):
                raise BridgeScopeReviewRequired("excluded investment components do not reconcile to reported total")
        elif rule.excluded_investment_parent_qname not in total_row.get("presentation_parents", ()):
            raise BridgeScopeReviewRequired("excluded investment is not classified in the approved other-asset scope")
        sources = [total_row, *component_rows]
    elif rule.direct_marketable_qnames:
        sources = [_one_undimensioned(rows,qname) for qname in rule.direct_marketable_qnames]
    else:
        # A complete structural package plus an exhaustive approved concept
        # search can prove absence, but only with current balance-sheet
        # witnesses.  This is not a generic missing-tag zero.
        sources = [_one_undimensioned(rows, qname) for qname in rule.marketable_zero_witness_qnames]
    refs = tuple(_source_ref(accession, period_end, row) for row in sources)
    searched = tuple(sorted({qname for qname in (
        *rule.searched_marketable_qnames, rule.excluded_investment_total_qname,
        *rule.excluded_investment_component_qnames, *rule.direct_marketable_qnames,
    ) if qname}))
    records = tuple(FieldAvailability(
        field=field, value=0.0, state="evidence_backed_zero",
        reason_code="NONMARKETABLE_INVESTMENT_SCOPE_RECONCILED",
        period_end=period_end, source_accession=accession,
        source_kind="practical_policy", evidence_class="reported_component_reconciliation",
        freshness="current", fallback_level="reported_aggregate", covered_fields=(field,),
        coverage_basis="reconciled_disjoint_components", coverage_source_facts=refs,
        economic_scope="current cash-like investments are directly classified; no approved noncurrent marketable-security fact is present" if rule.direct_marketable_qnames else "reported long-term investments are classified as non-marketable other assets; no approved marketable-security fact is present",
        extraction_complete=True, searched_concepts=searched, authority="production",
        mapping_version=rule.version,
    ) for field in rule.zero_marketable_fields)
    return records, {
        "status": "source_bound", "policy_version": rule.version, "ticker": ticker,
        "accession": accession, "period_end": period_end,
        "excluded_total": total,
        "components": [{"qname": row["qname"], "value": float(row["value"]),
                        "context_id": row.get("context_id")} for row in sources],
        "marketable_securities": 0.0,
    }


def outside_equity_zero_availability(*, ticker: str, policy: Mapping[str, Any],
                                     structural_packet: Mapping[str, Any], accession: str,
                                     period_end: str) -> tuple[FieldAvailability, dict[str, Any]]:
    """Prove zero NCI from the complete consolidated balance-sheet identity."""
    expected = OUTSIDE_EQUITY_ZERO_RULES.get(ticker)
    if expected is None or dict(policy) != dict(expected):
        raise BridgeScopeReviewRequired("outside-equity policy identity/version mismatch")
    metadata = dict(structural_packet.get("filing_metadata", ()))
    if metadata.get("manifest_version") != "FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
        raise BridgeScopeReviewRequired("complete structural filing package receipt is required")
    shell = AggregateDebtScopeRule(ticker=ticker,cik=expected["cik"],total_qname=None,component_qnames=())
    rows = _current_rows(structural_packet, rule=shell, accession=accession, period_end=period_end)
    basis=expected.get("basis")
    total_qnames=("us-gaap:Assets","us-gaap:LiabilitiesAndStockholdersEquity") if basis=="parent_equity_and_complete_nci_search" else (
        "us-gaap:Assets","us-gaap:Liabilities","us-gaap:LiabilitiesAndStockholdersEquity")
    totals = {qname:_one_undimensioned(rows,qname) for qname in total_qnames}
    totals["us-gaap:StockholdersEquity"]=_one_undimensioned_signed(rows,"us-gaap:StockholdersEquity")
    assets=_finite(totals["us-gaap:Assets"]["value"],"assets")
    combined=_finite(totals["us-gaap:LiabilitiesAndStockholdersEquity"]["value"],"liabilities and equity")
    parent=_finite_signed(totals["us-gaap:StockholdersEquity"]["value"],"parent equity")
    if not isclose(assets,combined,rel_tol=1e-12,abs_tol=0.01):
        raise BridgeScopeReviewRequired("balance sheet does not close with parent equity")
    if basis!="parent_equity_and_complete_nci_search":
        liabilities=_finite(totals["us-gaap:Liabilities"]["value"],"liabilities")
        if not isclose(assets,liabilities+parent,rel_tol=1e-12,abs_tol=0.01):
            raise BridgeScopeReviewRequired("balance sheet does not close with parent equity")
    nci_markers=("minorityinterest","noncontrollinginterest")
    claim_rows=[row for row in rows if any(marker in str(row.get("local_name","")).lower() for marker in nci_markers)]
    for row in rows:
        dims=row.get("dimensions") or []
        if any(isinstance(pair,(list,tuple)) and len(pair)==2 and "NoncontrollingInterestMember" in str(pair[1]) for pair in dims):
            claim_rows.append(row)
    if any(_finite(row.get("value"),"outside equity claim")!=0 for row in claim_rows):
        raise BridgeScopeReviewRequired("nonzero NCI evidence conflicts with parent-only balance sheet")
    source_rows=[*totals.values(),*claim_rows]
    refs=tuple(_source_ref(accession,period_end,row) for row in source_rows)
    availability=FieldAvailability(
        field="noncontrolling_interests",value=0.0,state="evidence_backed_zero",
        reason_code="BALANCE_SHEET_CLOSES_WITH_PARENT_EQUITY",period_end=period_end,
        source_accession=accession,source_kind="practical_policy",
        evidence_class="reported_component_reconciliation",freshness="current",
        fallback_level="reported_aggregate",covered_fields=("noncontrolling_interests",),
        coverage_basis="reconciled_disjoint_components",coverage_source_facts=refs,
        economic_scope="consolidated assets less liabilities reconcile exactly to parent stockholders equity",
        extraction_complete=True,searched_concepts=tuple((*totals.keys(),"NCI and minority-interest concepts and members")),
        authority="production",mapping_version=expected["version"])
    return availability,{"status":"source_bound","policy_version":expected["version"],
        "ticker":ticker,"accession":accession,"period_end":period_end,"value":0.0,
        "formula":"assets = liabilities and stockholders equity = liabilities + parent stockholders equity",
        "totals":{key:float(row["value"]) for key,row in totals.items()}}


def preferred_equity_zero_availability(*,ticker: str,policy: Mapping[str,Any],
                                       structural_packet: Mapping[str,Any],accession: str,
                                       period_end: str) -> tuple[FieldAvailability,dict[str,Any]]:
    """Prove parent equity consists entirely of reported common components."""
    expected=PREFERRED_EQUITY_ZERO_RULES.get(ticker)
    actual=dict(policy);actual["components"]=tuple(tuple(item) for item in actual.get("components",()))
    canonical=dict(expected or {});canonical["components"]=tuple(tuple(item) for item in canonical.get("components",()))
    actual["allowed_outside_equity_qnames"]=tuple(actual.get("allowed_outside_equity_qnames",()))
    canonical["allowed_outside_equity_qnames"]=tuple(canonical.get("allowed_outside_equity_qnames",()))
    actual["par_only_qnames"]=tuple(actual.get("par_only_qnames",()))
    canonical["par_only_qnames"]=tuple(canonical.get("par_only_qnames",()))
    actual["zero_preferred_share_qnames"]=tuple(actual.get("zero_preferred_share_qnames",()))
    canonical["zero_preferred_share_qnames"]=tuple(canonical.get("zero_preferred_share_qnames",()))
    if expected is None or actual!=canonical:
        raise BridgeScopeReviewRequired("preferred-equity policy identity/version mismatch")
    metadata=dict(structural_packet.get("filing_metadata",()))
    if metadata.get("manifest_version")!="FINSIGHT-XBRL-PACKAGE-1" or not metadata.get("package_generation"):
        raise BridgeScopeReviewRequired("complete structural filing package receipt is required")
    shell=AggregateDebtScopeRule(ticker=ticker,cik=expected["cik"],total_qname=None,component_qnames=())
    rows=_current_rows(structural_packet,rule=shell,accession=accession,period_end=period_end)
    parent=_one_undimensioned_signed(rows,expected["parent_qname"])
    components=[(_one_undimensioned_signed(rows,qname),weight) for qname,weight in expected["components"]]
    total=sum(_finite_signed(row["value"],str(row["qname"]))*weight for row,weight in components)
    rounding_tolerance=.01
    precision_proof=None
    if expected.get('allow_source_rounding'):
        from .reported_precision import reconcile_reported_sum
        source_rows=[parent,*[row for row,_ in components]]
        for row in source_rows:
            decimals=row.get('decimals')
            if not isinstance(decimals,str) or not re.fullmatch(r'-?\d+',decimals):
                raise BridgeScopeReviewRequired('common equity source precision is missing')
            if int(decimals)<expected['minimum_source_decimals']:
                raise BridgeScopeReviewRequired('common equity source precision became too coarse')
        weighted=[{**row,'value':float(row['value'])*weight} for row,weight in components]
        try:
            precision_proof=reconcile_reported_sum(parent,weighted,cik=expected['cik'],
                accession=accession,period=period_end)
        except ValueError as exc:
            raise BridgeScopeReviewRequired('common equity reported-precision reconciliation failed: '+str(exc)) from exc
        rounding_tolerance=precision_proof['maximum_rounding_difference']
    if not isclose(total,float(parent["value"]),rel_tol=1e-12,abs_tol=rounding_tolerance):
        raise BridgeScopeReviewRequired("reported common components do not reconcile to parent equity")
    preferred=[];outside=[];par_only=[];share_zeros=[]
    allowed_outside=set(expected.get("allowed_outside_equity_qnames",()))
    allowed_par=set(expected.get("par_only_qnames",()))
    share_qnames=set(expected.get("zero_preferred_share_qnames",()))
    for row in rows:
        name=str(row.get("local_name","")).lower()
        if any(token in name for token in ("preferredstock","preferredequity","temporaryequity")):
            if row.get("qname") in allowed_par:
                par_only.append(row)
            elif row.get("qname") in share_qnames:
                share_zeros.append(row)
            elif row.get("qname") in allowed_outside:
                outside.append(row)
            else:
                preferred.append(row)
    if share_qnames:
        facts=structural_packet.get("facts")
        if not isinstance(facts,list):
            raise BridgeScopeReviewRequired("preferred-share facts are unavailable")
        share_zeros=[row for row in facts if isinstance(row,Mapping)
                     and row.get("qname") in share_qnames and row.get("source_accession")==accession
                     and row.get("period_end")==period_end and row.get("period_start") is None
                     and row.get("unit")=="xbrli:shares" and row.get("entity_scheme")=="http://www.sec.gov/CIK"
                     and str(row.get("entity_identifier","")).zfill(10)==expected["cik"]]
    preferred=list({(row.get("qname"),row.get("value"),row.get("context_id"),str(row.get("dimensions"))):row
                    for row in preferred}.values())
    outside=list({(row.get("qname"),row.get("value"),row.get("context_id"),str(row.get("dimensions"))):row
                  for row in outside}.values())
    par_only=list({(row.get("qname"),row.get("value"),row.get("context_id"),str(row.get("dimensions"))):row
                   for row in par_only}.values())
    share_zeros=list({(row.get("qname"),row.get("value"),row.get("context_id"),str(row.get("dimensions"))):row
                      for row in share_zeros}.values())
    if allowed_par and (not share_zeros or any(_finite(row.get("value"),"preferred shares")!=0 for row in share_zeros)):
        raise BridgeScopeReviewRequired("par-only preferred disclosure lacks reported zero issued shares")
    if any(_finite(row.get("value"),"preferred claim")!=0 for row in preferred):
        raise BridgeScopeReviewRequired("nonzero preferred claim conflicts with common-only equity")
    sources=[parent,*[row for row,_ in components],*preferred,*outside,*par_only,*share_zeros]
    refs=tuple(_source_ref(accession,period_end,row) for row in sources)
    availability=FieldAvailability(field="preferred_equity",value=0.,state="evidence_backed_zero",
        reason_code="COMMON_COMPONENTS_RECONCILE_TO_PARENT_EQUITY",period_end=period_end,
        source_accession=accession,source_kind="practical_policy",evidence_class="reported_component_reconciliation",
        freshness="current",fallback_level="reported_aggregate",covered_fields=("preferred_equity",),
        coverage_basis="reconciled_disjoint_components",coverage_source_facts=refs,
        economic_scope="reported common equity components fully reconcile to parent stockholders equity",
        extraction_complete=True,searched_concepts=tuple([expected["parent_qname"],*[qname for qname,_ in expected["components"]],
            *allowed_outside,"preferred, temporary-equity and outstanding-share concepts"]),authority="production",mapping_version=expected["version"])
    return availability,{"status":"source_bound","policy_version":expected["version"],"ticker":ticker,
        "accession":accession,"period_end":period_end,"value":0.,"parent_equity":float(parent["value"]),
        "component_sum":total,"rounding_residual":total-float(parent['value']),
        "source_rounding_tolerance":rounding_tolerance,
        "reported_precision_reconciliation":precision_proof,
        "components":[{"qname":row["qname"],"value":float(row["value"]),"weight":weight}
            for row,weight in components],"outside_equity_components":[{"qname":row["qname"],"value":float(row["value"])} for row in outside],
        "par_only_disclosures":[{"qname":row["qname"],"value":float(row["value"])} for row in par_only],
        "zero_preferred_share_facts":[{"qname":row["qname"],"value":float(row["value"])} for row in share_zeros]}


__all__ = ["AGGREGATE_DEBT_SCOPE_RULES", "AggregateDebtScopeRule",
           "BRIDGE_SCOPE_POLICY_VERSION", "BridgeScopeReviewRequired",
           "OUTSIDE_EQUITY_ZERO_RULES", "PREFERRED_EQUITY_ZERO_RULES", "aggregate_debt_field_availability",
           "combined_cash_scope_availabilities", "nonmarketable_investment_zero_availabilities", "outside_equity_zero_availability",
           "preferred_equity_zero_availability"]
