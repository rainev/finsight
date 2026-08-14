from __future__ import annotations

import json

import pytest

import app.us_valuation.concept_resolver as concept_resolver_module
from app.us_valuation.concept_resolver import load_structural_rules, resolve_concept
from app.us_valuation.structural_xbrl import (
    ResolutionRequest,
    StructuralFact,
    StructuralRelationship,
)


ACCESSION = "0000000000-26-000001"
PERIOD = "2025-12-31"
OFFICIAL_NAMESPACES = (
    "http://xbrl.us/us-gaap/2008-01-31",
    "http://xbrl.us/us-gaap/2009-01-31",
    "http://fasb.org/us-gaap/2011-01-31",
    "http://fasb.org/us-gaap/2012-01-31",
    "http://fasb.org/us-gaap/2013-01-31",
    "http://fasb.org/us-gaap/2014-01-31",
    "http://fasb.org/us-gaap/2015-01-31",
    "http://fasb.org/us-gaap/2016-01-31",
    "http://fasb.org/us-gaap/2017-01-31",
    "http://fasb.org/us-gaap/2018-01-31",
    "http://fasb.org/us-gaap/2019-01-31",
    "http://fasb.org/us-gaap/2020-01-31",
    "http://fasb.org/us-gaap/2021-01-31",
    "http://fasb.org/us-gaap/2022",
    "http://fasb.org/us-gaap/2023",
    "http://fasb.org/us-gaap/2024",
    "http://fasb.org/us-gaap/2025",
    "http://fasb.org/us-gaap/2026",
)


def make_fact(**overrides: object) -> StructuralFact:
    qname = str(overrides.get("qname", "fsi:LiquidInvestmentSecuritiesCurrent"))
    values: dict[str, object] = {
        "qname": qname,
        "namespace": (
            "http://fasb.org/us-gaap/2025"
            if qname.startswith("us-gaap:")
            else "https://example.test/fsi/2025"
        ),
        "local_name": qname.split(":", 1)[-1],
        "labels": (("standard", "Liquid investment securities"),),
        "documentation": "Available-for-sale debt securities classified as current.",
        "value": 100.0,
        "unit": "USD",
        "period_start": None,
        "period_end": PERIOD,
        "context_id": "CurrentYearInstant",
        "dimensions": (),
        "statement_roles": ("balance_sheet",),
        "presentation_parents": ("us-gaap:AssetsCurrent",),
        "calculation_parents": ("us-gaap:AssetsCurrent",),
        "calculation_children": (),
        "definition_parents": (),
        "definition_children": (),
        "source_accession": ACCESSION,
        "decimals": "0",
        "scale": None,
        "sign": None,
        "filing_form": "10-K",
        "filing_metadata": (("primary_document", "fsi-20251231.htm"),),
        "presentation_ancestry": ("us-gaap:AssetsCurrent",),
        "relationships": (
            StructuralRelationship(
                arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                linkrole="https://example.test/role/BalanceSheet",
                from_concept="us-gaap:AssetsCurrent",
                to_concept=qname,
                order=1.0,
                preferred_label=None,
                calculation_weight=None,
            ),
        ),
    }
    values.update(overrides)
    return StructuralFact(**values)  # type: ignore[arg-type]


def metric_request(metric: str, **overrides: object) -> ResolutionRequest:
    values: dict[str, object] = {
        "normalized_concept": metric,
        "period_end": PERIOD,
        "source_accession": ACCESSION,
        "unit": "USD",
        "statement_role": "balance_sheet",
        "form": "10-K",
    }
    values.update(overrides)
    return ResolutionRequest(**values)  # type: ignore[arg-type]


def account_fact(qname: str, **overrides: object) -> StructuralFact:
    local_name = qname.split(":", 1)[-1]
    presentation_parents = tuple(overrides.get("presentation_parents", ()))
    values: dict[str, object] = {
        "qname": qname,
        "local_name": local_name,
        "labels": (("standard", local_name),),
        "documentation": local_name,
        "presentation_ancestry": presentation_parents,
    }
    if "presentation_parents" in overrides and "calculation_parents" not in overrides:
        values["calculation_parents"] = presentation_parents
    values.update(overrides)
    return make_fact(**values)


def current_request(**overrides: object) -> ResolutionRequest:
    return metric_request("marketable_securities_current", **overrides)


def noncurrent_request(**overrides: object) -> ResolutionRequest:
    return metric_request("marketable_securities_noncurrent", **overrides)


@pytest.mark.parametrize(
    "qname,reason_code",
    [
        ("us-gaap:PreferredStockValue", "PREFERRED_EQUITY_CARRYING_AMOUNT"),
        (
            "us-gaap:TemporaryEquityCarryingAmountAttributableToParent",
            "TEMPORARY_EQUITY_CARRYING_AMOUNT",
        ),
    ],
)
def test_direct_preferred_or_temporary_carrying_amount_zero_is_accepted(
    qname: str, reason_code: str
) -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                qname,
                value=0,
                statement_roles=(),
                presentation_parents=("us-gaap:TemporaryEquity",),
                calculation_parents=("us-gaap:TemporaryEquity",),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 0
    assert reason_code in decision.reason_codes


def test_preferred_stock_value_alias_outranks_descriptive_share_wording() -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                "us-gaap:PreferredStockValue",
                value=0,
                labels=(
                    ("standard", "Preferred Stock, Value, Issued"),
                    (
                        "terse",
                        "Preferred stock authorized and no shares issued or outstanding",
                    ),
                ),
                documentation=None,
                statement_roles=(),
                presentation_parents=("us-gaap:EquityAbstract",),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 0
    assert "PREFERRED_EQUITY_CARRYING_AMOUNT" in decision.reason_codes


def test_negative_phrase_alone_does_not_admit_candidate() -> None:
    fact = account_fact(
        "issuer:OtherCurrentAsset",
        labels=(("standard", "Strategic asset"),),
        documentation="Strategic asset.",
        statement_roles=(),
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "unresolved"
    assert decision.reason_codes == ("NO_CANDIDATE",)


def test_review_phrase_alone_does_not_admit_candidate() -> None:
    fact = account_fact(
        "issuer:OtherLiability",
        labels=(("standard", "Year two through thereafter"),),
        documentation="Year two through thereafter.",
        statement_roles=(),
        presentation_parents=(
            "us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",
        ),
        calculation_parents=(
            "us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",
        ),
    )

    decision = resolve_concept(metric_request("finance_lease_total"), [fact])

    assert decision.status == "unresolved"
    assert decision.reason_codes == ("NO_CANDIDATE",)


def test_preferred_stock_value_outstanding_is_a_governed_preferred_equity_alias() -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                "us-gaap:PreferredStockValueOutstanding",
                value=0,
                labels=(("standard", "Preferred Stock Value Outstanding"),),
                documentation="Preferred stock value outstanding.",
                statement_roles=(),
                presentation_parents=("us-gaap:StockholdersEquity",),
                calculation_parents=("us-gaap:StockholdersEquity",),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 0
    assert decision.mapping_method == "known_taxonomy_alias"
    assert "PREFERRED_EQUITY_CARRYING_AMOUNT" in decision.reason_codes


def test_hpe_like_zero_preferred_value_is_rejected_by_companion_instrument_evidence() -> None:
    preferred_value = account_fact(
        "us-gaap:PreferredStockValueOutstanding",
        value=0,
        labels=(
            (
                "terse",
                "7.625% Series C mandatory convertible preferred stock, $0.01 par value",
            ),
        ),
        documentation="Preferred stock value outstanding.",
        statement_roles=(),
        presentation_parents=("us-gaap:StockholdersEquity",),
        calculation_parents=("us-gaap:StockholdersEquity",),
    )
    preferred_shares = account_fact(
        "us-gaap:PreferredStockSharesOutstanding",
        value=30_000_000,
        unit="shares",
        labels=(("standard", "Preferred Stock, Shares Outstanding"),),
        documentation="Preferred stock shares outstanding.",
        statement_roles=(),
        presentation_parents=("us-gaap:StockholdersEquity",),
        calculation_parents=("us-gaap:StockholdersEquity",),
    )

    decision = resolve_concept(
        metric_request("preferred_equity"), [preferred_value, preferred_shares]
    )

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == (
        "PREFERRED_ZERO_CONTRADICTED_BY_INSTRUMENT_EVIDENCE",
    )


def test_preferred_zero_value_is_rejected_by_configured_preferred_dividend_evidence() -> None:
    preferred_value = account_fact(
        "us-gaap:PreferredStockValueOutstanding",
        value=0,
        statement_roles=(),
        presentation_parents=("us-gaap:StockholdersEquity",),
        calculation_parents=("us-gaap:StockholdersEquity",),
    )
    preferred_dividends = account_fact(
        "us-gaap:DividendsPreferredStockCash",
        value=1_000_000,
        labels=(("standard", "Dividends Preferred Stock Cash"),),
        documentation="Dividends preferred stock cash.",
        statement_roles=(),
        presentation_parents=("us-gaap:StockholdersEquity",),
        calculation_parents=("us-gaap:StockholdersEquity",),
    )

    decision = resolve_concept(
        metric_request("preferred_equity"), [preferred_value, preferred_dividends]
    )

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == (
        "PREFERRED_ZERO_CONTRADICTED_BY_INSTRUMENT_EVIDENCE",
    )


def test_preferred_zero_conflict_requires_same_accession_and_period() -> None:
    preferred_value = account_fact(
        "us-gaap:PreferredStockValueOutstanding",
        value=0,
        statement_roles=(),
        presentation_parents=("us-gaap:StockholdersEquity",),
        calculation_parents=("us-gaap:StockholdersEquity",),
    )
    preferred_shares = account_fact(
        "us-gaap:PreferredStockSharesOutstanding",
        value=30_000_000,
        unit="shares",
    )

    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            preferred_value,
            preferred_shares,
        ],
    )

    assert decision.status == "rejected"
    assert decision.reason_codes == (
        "PREFERRED_ZERO_CONTRADICTED_BY_INSTRUMENT_EVIDENCE",
    )

    mismatched_decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            preferred_value,
            account_fact(
                "us-gaap:PreferredStockSharesOutstanding",
                value=30_000_000,
                unit="shares",
                source_accession="0000000000-26-000002",
                period_end="2024-12-31",
            ),
        ],
    )

    assert mismatched_decision.status == "accepted"
    assert mismatched_decision.value == 0


def test_preferred_zero_conflict_cannot_be_bypassed_by_higher_ranked_alias() -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                "us-gaap:PreferredStocksIncludingAdditionalPaidInCapitalParOrStatedValue",
                value=0,
                statement_roles=(),
                presentation_parents=("us-gaap:StockholdersEquity",),
            ),
            account_fact(
                "us-gaap:PreferredStockValueOutstanding",
                value=0,
                statement_roles=(),
                presentation_parents=("us-gaap:StockholdersEquity",),
            ),
            account_fact(
                "us-gaap:PreferredStockSharesOutstanding",
                value=30_000_000,
                unit="shares",
            ),
        ],
    )

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == (
        "PREFERRED_ZERO_CONTRADICTED_BY_INSTRUMENT_EVIDENCE",
    )


def test_nvda_like_zero_preferred_value_remains_accepted_without_companion_evidence() -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                "us-gaap:PreferredStockValueOutstanding",
                value=0,
                labels=(("terse", "Preferred stock"),),
                documentation="Preferred Stock, Value, Outstanding.",
                statement_roles=("balance_sheet",),
                presentation_parents=(
                    "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterestAbstract",
                ),
                calculation_parents=(),
                relationships=(
                    StructuralRelationship(
                        arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                        linkrole="https://example.test/role/BalanceSheet",
                        from_concept=(
                            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterestAbstract"
                        ),
                        to_concept="us-gaap:PreferredStockValueOutstanding",
                        order=1.0,
                        preferred_label=None,
                        calculation_weight=None,
                        statement_role="balance_sheet",
                    ),
                ),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 0
    assert decision.confidence == 0.98


def test_rtx_like_redeemable_nci_temporary_equity_is_not_preferred_equity() -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
                value=28_000_000,
                labels=(("terse", "Redeemable noncontrolling interest"),),
                documentation="Temporary Equity, Including Noncontrolling Interest.",
                statement_roles=(),
                presentation_parents=(
                    "us-gaap:LiabilitiesAndStockholdersEquityAbstract",
                ),
                calculation_parents=(),
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_parent_only_nci_wording_rejects_preferred_equity_extension() -> None:
    fact = account_fact(
        "issuer:TemporaryPreferredEquityCarryingAmount",
        value=100,
        labels=(("standard", "Temporary equity carrying amount"),),
        documentation="Temporary preferred equity carrying amount.",
        statement_roles=("balance_sheet",),
        presentation_parents=(
            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterestAbstract",
        ),
        calculation_parents=(
            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterestAbstract",
        ),
        relationships=(
            StructuralRelationship(
                arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                linkrole="https://example.test/role/BalanceSheet",
                from_concept=(
                    "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterestAbstract"
                ),
                to_concept="issuer:TemporaryPreferredEquityCarryingAmount",
                order=1.0,
                preferred_label=None,
                calculation_weight=None,
                statement_role="balance_sheet",
            ),
        ),
    )

    decision = resolve_concept(metric_request("preferred_equity"), [fact])

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_wdc_like_parent_attributable_temporary_equity_remains_preferred_equity() -> None:
    carrying_amount = account_fact(
        "us-gaap:TemporaryEquityCarryingAmountAttributableToParent",
        value=0,
        labels=(
            (
                "standard",
                "Temporary Equity, Carrying Amount, Attributable to Parent",
            ),
        ),
        documentation="Temporary equity carrying amount attributable to parent.",
        statement_roles=(),
        presentation_parents=("us-gaap:TemporaryEquity",),
        calculation_parents=("us-gaap:TemporaryEquity",),
    )
    liquidation_preference = account_fact(
        "wdc:TemporaryEquityLiquidationPreference",
        value=265_000_000,
        documentation="Temporary equity liquidation preference.",
        statement_roles=(),
        presentation_parents=("us-gaap:TemporaryEquity",),
        calculation_parents=("us-gaap:TemporaryEquity",),
    )

    decision = resolve_concept(
        metric_request("preferred_equity"),
        [liquidation_preference, carrying_amount],
    )

    assert decision.status == "accepted"
    assert decision.source_concept == carrying_amount.qname
    assert decision.value == 0
    assert "TEMPORARY_EQUITY_CARRYING_AMOUNT" in decision.reason_codes


def test_expe_like_governed_dimensional_nci_remains_accepted() -> None:
    fact = account_fact(
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        value=1_260_000_000,
        dimensions=(
            (
                "us-gaap:StatementEquityComponentsAxis",
                "us-gaap:NoncontrollingInterestMember",
            ),
        ),
        statement_roles=(),
        presentation_parents=(
            "us-gaap:IncreaseDecreaseInStockholdersEquityRollForward",
        ),
        calculation_parents=(),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "accepted"
    assert decision.value == 1_260_000_000
    assert decision.confidence == 0.96
    assert "GOVERNED_DIMENSIONAL_CONTEXT" in decision.reason_codes


def test_temporary_equity_alias_ignores_unrelated_fair_value_ancestry() -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                "us-gaap:TemporaryEquityCarryingAmountAttributableToParent",
                value=0,
                labels=(
                    (
                        "standard",
                        "Temporary Equity, Carrying Amount, Attributable to Parent",
                    ),
                ),
                documentation=None,
                statement_roles=(),
                presentation_parents=("us-gaap:LiabilitiesAbstract",),
                presentation_ancestry=(
                    "us-gaap:FairValueDisclosuresAbstract",
                    "us-gaap:LiabilitiesAbstract",
                ),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 0
    assert "TEMPORARY_EQUITY_CARRYING_AMOUNT" in decision.reason_codes


def test_balance_sheet_restricted_parent_excludes_marketable_extension() -> None:
    qname = "issuer:InvestmentSecuritiesCurrent"
    decision = resolve_concept(
        metric_request("marketable_securities_current"),
        [
            account_fact(
                qname,
                value=42_500_000,
                labels=(("standard", "Investment securities"),),
                documentation="Available-for-sale debt securities classified as current.",
                statement_roles=("balance_sheet",),
                presentation_parents=("us-gaap:AssetsCurrent",),
                presentation_ancestry=(
                    "us-gaap:AssetsCurrent",
                    "us-gaap:RestrictedAssetsAbstract",
                ),
                calculation_parents=("us-gaap:AssetsCurrent",),
                relationships=(
                    StructuralRelationship(
                        arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                        linkrole="https://issuer.test/role/custom-1001",
                        statement_role="balance_sheet",
                        from_concept="us-gaap:RestrictedAssetsAbstract",
                        to_concept="us-gaap:AssetsCurrent",
                        order=1.0,
                        preferred_label=None,
                        calculation_weight=None,
                    ),
                    StructuralRelationship(
                        arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                        linkrole="https://issuer.test/role/custom-1001",
                        statement_role="balance_sheet",
                        from_concept="us-gaap:AssetsCurrent",
                        to_concept=qname,
                        order=2.0,
                        preferred_label=None,
                        calculation_weight=None,
                    ),
                ),
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_unrelated_disclosure_parent_does_not_exclude_marketable_extension() -> None:
    qname = "issuer:InvestmentSecuritiesCurrent"
    decision = resolve_concept(
        metric_request("marketable_securities_current"),
        [
            account_fact(
                qname,
                value=42_500_000,
                labels=(("standard", "Investment securities"),),
                documentation="Available-for-sale debt securities classified as current.",
                statement_roles=("balance_sheet",),
                presentation_parents=("us-gaap:AssetsCurrent",),
                presentation_ancestry=(
                    "us-gaap:AssetsCurrent",
                    "us-gaap:RestrictedAssetsAbstract",
                ),
                calculation_parents=("us-gaap:AssetsCurrent",),
                relationships=(
                    StructuralRelationship(
                        arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                        linkrole="https://issuer.test/role/custom-1001",
                        statement_role="balance_sheet",
                        from_concept="us-gaap:AssetsCurrent",
                        to_concept=qname,
                        order=1.0,
                        preferred_label=None,
                        calculation_weight=None,
                    ),
                    StructuralRelationship(
                        arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                        linkrole="https://issuer.test/role/RestrictedAssetsDisclosure",
                        statement_role=None,
                        from_concept="us-gaap:RestrictedAssetsAbstract",
                        to_concept="us-gaap:AssetsCurrent",
                        order=1.0,
                        preferred_label=None,
                        calculation_weight=None,
                    ),
                ),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 42_500_000


def test_preferred_equity_alias_still_requires_usd_unit() -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                "us-gaap:PreferredStockValue",
                value=0,
                unit="shares",
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("UNIT_MISMATCH",)


@pytest.mark.parametrize(
    "fact_overrides,request_overrides,reason_code",
    [
        ({"source_accession": "0000000000-26-999999"}, {}, "ACCESSION_MISMATCH"),
        ({"period_end": "2024-12-31"}, {}, "PERIOD_MISMATCH"),
        (
            {
                "statement_roles": ("income_statement",),
                "presentation_parents": ("us-gaap:NetIncomeLoss",),
                "calculation_parents": ("us-gaap:NetIncomeLoss",),
            },
            {},
            "STATEMENT_ROLE_MISMATCH",
        ),
        (
            {
                "dimensions": (
                    ("us-gaap:StatementBusinessSegmentsAxis", "issuer:CloudMember"),
                ),
                "presentation_parents": ("us-gaap:TemporaryEquity",),
                "calculation_parents": ("us-gaap:TemporaryEquity",),
            },
            {},
            "DIMENSIONED_NONCONSOLIDATED_FACT",
        ),
        ({"filing_form": "10-Q"}, {}, "FILING_FORM_MISMATCH"),
    ],
)
def test_preferred_direct_alias_obeys_every_non_unit_accounting_gate(
    fact_overrides: dict[str, object],
    request_overrides: dict[str, object],
    reason_code: str,
) -> None:
    decision = resolve_concept(
        metric_request("preferred_equity", **request_overrides),
        [
            account_fact(
                "us-gaap:PreferredStockValue",
                value=0,
                **fact_overrides,
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == (reason_code,)


@pytest.mark.parametrize(
    "qname,value,documentation",
    [
        (
            "wdc:TemporaryEquityLiquidationPreference",
            265_000_000,
            "Temporary equity liquidation preference.",
        ),
        (
            "wdc:PreferredStockDividends",
            10_000_000,
            "Preferred dividends.",
        ),
        (
            "wdc:PreferredStockConversionValue",
            265_000_000,
            "Preferred stock conversion value.",
        ),
        (
            "wdc:PreferredStockProceeds",
            265_000_000,
            "Preferred stock proceeds.",
        ),
        (
            "wdc:PreferredEquityEPS",
            1.25,
            "Preferred-equity EPS.",
        ),
        (
            "wdc:PreferredSharesIssued",
            1_000_000,
            "Preferred share counts.",
        ),
    ],
)
def test_preferred_non_carrying_facts_are_review_only(
    qname: str, value: float, documentation: str
) -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                qname,
                value=value,
                documentation=documentation,
                statement_roles=(),
                presentation_parents=("us-gaap:TemporaryEquity",),
                calculation_parents=("us-gaap:TemporaryEquity",),
            )
        ],
    )

    assert decision.status == "review"
    assert decision.value == value
    assert decision.status != "accepted"


@pytest.mark.parametrize(
    "qname,documentation",
    [
        (
            "issuer:PreferredStockRedemptionAmount",
            "Preferred stock redemption amount.",
        ),
        ("issuer:PreferredStockShares", "Preferred stock shares."),
        (
            "issuer:PreferredStockNumberOfShares",
            "Preferred stock number of shares.",
        ),
    ],
)
def test_synthetic_preferred_non_carrying_extensions_are_review_only(
    qname: str, documentation: str
) -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                qname,
                value=100,
                documentation=documentation,
                statement_roles=(),
                presentation_parents=("us-gaap:TemporaryEquity",),
                calculation_parents=("us-gaap:TemporaryEquity",),
            )
        ],
    )

    assert decision.status == "review"
    assert "REVIEW_ONLY_ACCOUNTING_CONTEXT" in decision.reason_codes


def test_preferred_carrying_amount_wins_over_liquidation_preference() -> None:
    carrying_amount = account_fact(
        "us-gaap:TemporaryEquityCarryingAmountAttributableToParent",
        value=0,
        statement_roles=(),
        presentation_parents=("us-gaap:TemporaryEquity",),
        calculation_parents=("us-gaap:TemporaryEquity",),
    )
    liquidation_preference = account_fact(
        "wdc:TemporaryEquityLiquidationPreference",
        value=265_000_000,
        documentation="Temporary equity liquidation preference.",
        statement_roles=(),
        presentation_parents=("us-gaap:TemporaryEquity",),
        calculation_parents=("us-gaap:TemporaryEquity",),
    )

    decision = resolve_concept(
        metric_request("preferred_equity"),
        [liquidation_preference, carrying_amount],
    )

    assert decision.status == "accepted"
    assert decision.source_concept == carrying_amount.qname
    assert decision.value == 0


def test_preferred_shares_issued_zero_is_not_a_usd_preferred_equity_value() -> None:
    decision = resolve_concept(
        metric_request("preferred_equity"),
        [
            account_fact(
                "us-gaap:PreferredStockSharesIssued",
                value=0,
                unit="shares",
                documentation="Preferred share counts.",
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("UNIT_MISMATCH",)


def test_governed_nci_equity_member_is_accepted() -> None:
    fact = account_fact(
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        value=0,
        dimensions=(
            (
                "us-gaap:StatementEquityComponentsAxis",
                "us-gaap:NoncontrollingInterestMember",
            ),
        ),
        statement_roles=(),
        presentation_parents=(
            "us-gaap:IncreaseDecreaseInStockholdersEquityRollForward",
        ),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "accepted"
    assert decision.value == 0
    assert decision.confidence == 0.96
    assert decision.mapping_method == "taxonomy_and_context"
    assert "GOVERNED_DIMENSIONAL_CONTEXT" in decision.reason_codes


def test_governed_nci_member_ignores_unrelated_income_statement_ancestry() -> None:
    fact = account_fact(
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        value=0,
        dimensions=(
            (
                "us-gaap:StatementEquityComponentsAxis",
                "us-gaap:NoncontrollingInterestMember",
            ),
        ),
        labels=(
            (
                "standard",
                "Equity, Including Portion Attributable to Noncontrolling Interest",
            ),
        ),
        documentation=None,
        statement_roles=(),
        presentation_parents=(
            "us-gaap:IncreaseDecreaseInStockholdersEquityRollForward",
        ),
        presentation_ancestry=(
            "us-gaap:IncomeStatementAbstract",
            "us-gaap:IncreaseDecreaseInStockholdersEquityRollForward",
            "us-gaap:StatementOfStockholdersEquityAbstract",
        ),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "accepted"
    assert decision.value == 0
    assert decision.reason_codes[0] == "GOVERNED_DIMENSIONAL_CONTEXT"


@pytest.mark.parametrize(
    "qname",
    [
        "us-gaap:MinorityInterest",
        "us-gaap:NoncontrollingInterestInConsolidatedEntity",
    ],
)
def test_legacy_direct_nci_aliases_cannot_bypass_governed_dimension(
    qname: str,
) -> None:
    fact = account_fact(
        qname,
        value=0,
        statement_roles=(),
        presentation_parents=(
            "us-gaap:IncreaseDecreaseInStockholdersEquityRollForward",
        ),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "review"
    assert decision.status != "accepted"


@pytest.mark.parametrize(
    "dimensions",
    [
        ((
            "us-gaap:StatementEquityComponentsAxis",
            "us-gaap:ParentMember",
        ),),
        ((
            "us-gaap:StatementEquityComponentsAxis",
            "us-gaap:RetainedEarningsMember",
        ),),
        (),
    ],
)
def test_nci_total_equity_other_members_and_unsegmented_facts_are_rejected(
    dimensions: tuple[tuple[str, str], ...]
) -> None:
    fact = account_fact(
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        value=0,
        dimensions=dimensions,
        statement_roles=(),
        presentation_parents=(
            "us-gaap:IncreaseDecreaseInStockholdersEquityRollForward",
        ),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("DIMENSIONED_NONCONSOLIDATED_FACT",)


def test_nci_exact_member_rejects_an_extra_dimension() -> None:
    fact = account_fact(
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        value=0,
        dimensions=(
            (
                "us-gaap:StatementEquityComponentsAxis",
                "us-gaap:NoncontrollingInterestMember",
            ),
            ("us-gaap:StatementBusinessSegmentsAxis", "issuer:CloudMember"),
        ),
        statement_roles=(),
        presentation_parents=(
            "us-gaap:IncreaseDecreaseInStockholdersEquityRollForward",
        ),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("DIMENSIONED_NONCONSOLIDATED_FACT",)


def test_nci_exact_member_requires_rollforward_parent_even_with_statement_role() -> None:
    fact = account_fact(
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        value=0,
        dimensions=(
            (
                "us-gaap:StatementEquityComponentsAxis",
                "us-gaap:NoncontrollingInterestMember",
            ),
        ),
        statement_roles=("balance_sheet",),
        presentation_parents=("us-gaap:StockholdersEquity",),
        calculation_parents=("us-gaap:StockholdersEquity",),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("STATEMENT_ROLE_MISMATCH",)


def test_income_statement_nci_cannot_satisfy_equity_nci() -> None:
    fact = account_fact(
        "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
        value=0,
        statement_roles=("income_statement",),
        presentation_parents=("us-gaap:NetIncomeLoss",),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("STATEMENT_ROLE_MISMATCH",)


def test_narrative_only_ftnt_ownership_is_not_structural_nci_zero() -> None:
    fact = account_fact(
        "ftnt:OwnershipNarrative",
        value=None,
        documentation="100% ownership is maintained.",
        presentation_parents=("us-gaap:StockholdersEquity",),
    )

    decision = resolve_concept(metric_request("noncontrolling_interests"), [fact])

    assert decision.status == "rejected"
    assert decision.value is None
    assert decision.reason_codes == ("STATEMENT_ROLE_MISMATCH",)


@pytest.mark.parametrize("metric", ["preferred_equity", "noncontrolling_interests"])
def test_task_4_account_absence_is_unresolved_not_zero(metric: str) -> None:
    decision = resolve_concept(metric_request(metric), [])

    assert decision.status == "unresolved"
    assert decision.value is None
    assert decision.reason_codes == ("NO_CANDIDATE",)


@pytest.mark.parametrize(
    "metric,qname,value,parents,roles",
    [
        (
            "current_debt",
            "us-gaap:DebtCurrent",
            7_550_000_000,
            ("us-gaap:DebtInstrumentLineItems",),
            (),
        ),
        (
            "current_debt",
            "us-gaap:LongTermDebtCurrent",
            0,
            ("us-gaap:LiabilitiesCurrentAbstract",),
            ("balance_sheet",),
        ),
        (
            "noncurrent_debt",
            "us-gaap:LongTermDebtNoncurrent",
            23_611_000_000,
            ("us-gaap:DebtInstrumentLineItems",),
            (),
        ),
        (
            "noncurrent_debt",
            "us-gaap:LongTermDebtNoncurrent",
            0,
            ("us-gaap:LiabilitiesNoncurrentAbstract",),
            ("balance_sheet",),
        ),
    ],
)
def test_direct_debt_carrying_amounts_are_accepted(
    metric: str,
    qname: str,
    value: float,
    parents: tuple[str, ...],
    roles: tuple[str, ...],
) -> None:
    decision = resolve_concept(
        metric_request(metric),
        [account_fact(qname, value=value, presentation_parents=parents, statement_roles=roles)],
    )

    assert decision.status == "accepted"
    assert decision.value == value


@pytest.mark.parametrize(
    "metric,qname,value,valid_parent,unrelated_parent,unrelated_ancestor",
    [
        (
            "current_debt",
            "us-gaap:DebtCurrent",
            7_550_000_000,
            "us-gaap:LiabilitiesCurrentAbstract",
            "us-gaap:AccountsNotesAndLoansReceivableLineItems",
            "us-gaap:ReceivablesAbstract",
        ),
        (
            "noncurrent_debt",
            "us-gaap:LongTermDebtNoncurrent",
            23_611_000_000,
            "us-gaap:DebtInstrumentLineItems",
            "us-gaap:AccountsNotesAndLoansReceivableLineItems",
            "us-gaap:ReceivablesAbstract",
        ),
        (
            "current_debt",
            "us-gaap:LongTermDebtCurrent",
            1_581_000_000,
            "us-gaap:LiabilitiesCurrentAbstract",
            "us-gaap:DebtInstrumentLineItems",
            "us-gaap:FairValueDisclosuresAbstract",
        ),
    ],
)
def test_exact_debt_alias_ignores_unrelated_disclosure_relationships(
    metric: str,
    qname: str,
    value: float,
    valid_parent: str,
    unrelated_parent: str,
    unrelated_ancestor: str,
) -> None:
    decision = resolve_concept(
        metric_request(metric),
        [
            account_fact(
                qname,
                value=value,
                labels=(("standard", qname.split(":", 1)[-1]),),
                documentation=None,
                statement_roles=(),
                presentation_parents=(valid_parent, unrelated_parent),
                presentation_ancestry=(valid_parent, unrelated_ancestor),
                calculation_parents=(),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == value


def test_noncurrent_debt_label_excluding_current_maturities_is_not_a_conflict() -> None:
    decision = resolve_concept(
        metric_request("noncurrent_debt"),
        [
            account_fact(
                "us-gaap:LongTermDebtNoncurrent",
                value=496_900_000,
                labels=(
                    (
                        "standard",
                        "Long-Term Debt, Excluding Current Maturities",
                    ),
                    ("terse", "LONG-TERM DEBT"),
                ),
                documentation=None,
                statement_roles=(),
                presentation_parents=("us-gaap:DebtInstrumentLineItems",),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 496_900_000


def test_convertible_current_debt_is_review_only_component() -> None:
    decision = resolve_concept(
        metric_request("current_debt"),
        [account_fact("us-gaap:ConvertibleDebtCurrent", value=125.0)],
    )

    assert decision.status == "review"
    assert decision.confidence == 0.75
    assert "COMPONENT_ONLY_CONCEPT" in decision.reason_codes


def test_unqualified_long_term_debt_is_review_only_for_noncurrent_debt() -> None:
    decision = resolve_concept(
        metric_request("noncurrent_debt"),
        [
            account_fact(
                "us-gaap:LongTermDebt",
                value=23_611_000_000,
                presentation_parents=("us-gaap:LiabilitiesNoncurrentAbstract",),
                calculation_parents=("us-gaap:LiabilitiesNoncurrentAbstract",),
            )
        ],
    )

    assert decision.status == "review"
    assert decision.confidence == 0.75
    assert "COMPONENT_ONLY_CONCEPT" in decision.reason_codes


def test_current_debt_subtype_with_only_generic_debt_note_support_is_rejected() -> None:
    decision = resolve_concept(
        metric_request("current_debt"),
        [
            account_fact(
                "us-gaap:LongTermDebtCurrent",
                statement_roles=(),
                presentation_parents=("us-gaap:DebtInstrumentLineItems",),
                calculation_parents=("us-gaap:DebtInstrumentLineItems",),
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.reason_codes == ("STATEMENT_ROLE_MISMATCH",)


@pytest.mark.parametrize(
    "qname,documentation,expected_status,expected_reason",
    [
        (
            "us-gaap:DebtMaturitySchedule",
            "Debt maturity repayments.",
            "unresolved",
            "NO_CANDIDATE",
        ),
        (
            "us-gaap:DebtInstrumentFaceAmount",
            "Debt instrument face amount.",
            "unresolved",
            "NO_CANDIDATE",
        ),
        (
            "us-gaap:DebtInstrumentFairValue",
            "Debt instrument fair value.",
            "unresolved",
            "NO_CANDIDATE",
        ),
        (
            "us-gaap:ProceedsFromIssuanceOfLongTermDebt",
            "Proceeds from debt issuance cash flows.",
            "rejected",
            "EXCLUDED_ECONOMIC_CLASS",
        ),
        (
            "us-gaap:RepaymentsOfLongTermDebt",
            "Repayments of long-term debt cash flows.",
            "rejected",
            "EXCLUDED_ECONOMIC_CLASS",
        ),
    ],
)
def test_debt_schedule_valuation_and_cash_flow_facts_are_not_candidates(
    qname: str,
    documentation: str,
    expected_status: str,
    expected_reason: str,
) -> None:
    decision = resolve_concept(
        metric_request("noncurrent_debt"),
        [
            account_fact(
                qname,
                documentation=documentation,
                presentation_parents=("us-gaap:DebtInstrumentLineItems",),
                calculation_parents=("us-gaap:DebtInstrumentLineItems",),
            )
        ],
    )

    assert decision.status == expected_status
    assert decision.reason_codes == (expected_reason,)


def test_debt_maturity_schedule_is_excluded_with_carrying_amount_wording() -> None:
    decision = resolve_concept(
        metric_request("noncurrent_debt"),
        [
            account_fact(
                "issuer:LongTermDebtMaturitySchedule",
                documentation="Noncurrent debt carrying amount maturity schedule.",
                presentation_parents=("us-gaap:DebtInstrumentLineItems",),
                calculation_parents=("us-gaap:DebtInstrumentLineItems",),
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_crm_commercial_paper_investment_component_is_excluded() -> None:
    decision = resolve_concept(
        metric_request("commercial_paper"),
        [
            account_fact(
                "us-gaap:AvailableForSaleSecuritiesDebtSecurities",
                value=94_000_000,
                documentation="Available-for-sale debt securities reported at assets fair value.",
                dimensions=(
                    (
                        "us-gaap:FinancialInstrumentAxis",
                        "us-gaap:CommercialPaperMember",
                    ),
                ),
                presentation_parents=("us-gaap:AssetsCurrent",),
                calculation_parents=("us-gaap:AssetsCurrent",),
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_dimensional_commercial_paper_liability_is_not_treated_as_investment() -> None:
    decision = resolve_concept(
        metric_request("commercial_paper"),
        [
            account_fact(
                "us-gaap:CommercialPaper",
                value=250_000_000,
                labels=(("standard", "Commercial paper borrowings"),),
                documentation="Commercial paper liability carrying amount.",
                dimensions=(
                    (
                        "us-gaap:FinancialInstrumentAxis",
                        "us-gaap:CommercialPaperMember",
                    ),
                ),
                statement_roles=("balance_sheet",),
                presentation_parents=("us-gaap:LiabilitiesCurrent",),
                calculation_parents=("us-gaap:LiabilitiesCurrent",),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 250_000_000
    assert decision.reason_codes[0] == "EXACT_CONFIGURED_CONCEPT"


def test_dimensional_commercial_paper_extension_uses_governed_context() -> None:
    decision = resolve_concept(
        metric_request("commercial_paper"),
        [
            account_fact(
                "issuer:CommercialPaperBorrowings",
                value=250_000_000,
                labels=(("standard", "Commercial paper borrowings"),),
                documentation="Commercial paper liability carrying amount.",
                dimensions=(
                    (
                        "us-gaap:FinancialInstrumentAxis",
                        "us-gaap:CommercialPaperMember",
                    ),
                ),
                statement_roles=("balance_sheet",),
                presentation_parents=("us-gaap:LiabilitiesCurrent",),
                calculation_parents=("us-gaap:LiabilitiesCurrent",),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == 250_000_000
    assert decision.mapping_method == "extension_structural_match"


def test_crm_commercial_paper_asset_is_not_obscured_by_unrelated_current_debt() -> None:
    investment_asset = account_fact(
        "us-gaap:AvailableForSaleSecuritiesDebtSecurities",
        value=94_000_000,
        labels=(
            ("standard", "Debt Securities, Available-for-Sale"),
            ("verbose", "Marketable securities"),
        ),
        documentation=None,
        dimensions=(
            (
                "us-gaap:FinancialInstrumentAxis",
                "us-gaap:CommercialPaperMember",
            ),
        ),
        statement_roles=(),
        presentation_parents=(
            "us-gaap:ScheduleOfAvailableForSaleSecuritiesLineItems",
        ),
        calculation_parents=(),
    )
    unrelated_debt = account_fact(
        "us-gaap:LongTermDebtCurrent",
        value=0,
        labels=(("standard", "Long-Term Debt, Current Maturities"),),
        documentation=None,
        statement_roles=(),
        presentation_parents=("us-gaap:DebtInstrumentLineItems",),
        calculation_parents=(),
    )

    decision = resolve_concept(
        metric_request("commercial_paper"),
        [investment_asset, unrelated_debt],
    )

    assert decision.status == "rejected"
    assert decision.source_concept == investment_asset.qname
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_crm_commercial_paper_asset_outranks_duration_gain_component() -> None:
    current_asset = account_fact(
        "us-gaap:AvailableForSaleSecuritiesDebtSecurities",
        value=94_000_000,
        labels=(
            ("standard", "Debt Securities, Available-for-Sale"),
            ("verbose", "Marketable securities"),
        ),
        documentation=None,
        dimensions=(
            (
                "us-gaap:FinancialInstrumentAxis",
                "us-gaap:CommercialPaperMember",
            ),
        ),
        statement_roles=(),
        presentation_parents=(
            "us-gaap:ScheduleOfAvailableForSaleSecuritiesLineItems",
        ),
        calculation_parents=(),
    )
    duration_gain = account_fact(
        "us-gaap:AvailableForSaleDebtSecuritiesAccumulatedGrossUnrealizedGainBeforeTax",
        value=0,
        period_start="2025-01-01",
        labels=(("standard", "Unrealized Gains"),),
        documentation=None,
        dimensions=(
            (
                "us-gaap:FinancialInstrumentAxis",
                "us-gaap:CommercialPaperMember",
            ),
        ),
        statement_roles=(),
        presentation_parents=(),
        calculation_parents=(),
    )
    stale_amortized_cost = account_fact(
        "us-gaap:AvailableForSaleDebtSecuritiesAmortizedCostBasis",
        value=30_000_000,
        period_end="2024-12-31",
        labels=(("standard", "Debt Securities, Available-for-Sale, Amortized Cost"),),
        documentation=None,
        dimensions=(
            (
                "us-gaap:FinancialInstrumentAxis",
                "us-gaap:CommercialPaperMember",
            ),
        ),
        statement_roles=(),
        presentation_parents=(),
        calculation_parents=(),
    )
    current_amortized_cost = account_fact(
        "us-gaap:AvailableForSaleDebtSecuritiesAmortizedCostBasis",
        value=94_000_000,
        labels=(("standard", "Debt Securities, Available-for-Sale, Amortized Cost"),),
        documentation=None,
        dimensions=(
            (
                "us-gaap:FinancialInstrumentAxis",
                "us-gaap:CommercialPaperMember",
            ),
        ),
        statement_roles=(),
        presentation_parents=(),
        calculation_parents=(),
    )
    generic_fair_value_disclosure = account_fact(
        "us-gaap:AssetsFairValueDisclosure",
        value=94_000_000,
        labels=(("standard", "Assets, Fair Value Disclosure"),),
        documentation=None,
        dimensions=(
            (
                "us-gaap:FinancialInstrumentAxis",
                "us-gaap:CommercialPaperMember",
            ),
        ),
        statement_roles=(),
        presentation_parents=(),
        calculation_parents=(),
    )

    decision = resolve_concept(
        metric_request("commercial_paper"),
        [
            duration_gain,
            stale_amortized_cost,
            generic_fair_value_disclosure,
            current_asset,
            current_amortized_cost,
        ],
    )

    assert decision.status == "rejected"
    assert decision.source_concept == current_amortized_cost.qname
    assert decision.period == PERIOD
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


@pytest.mark.parametrize(
    "metric,qname",
    [
        ("current_debt", "us-gaap:AccountsPayableCurrent"),
        ("noncurrent_debt", "us-gaap:ContractWithCustomerLiabilityNoncurrent"),
        ("finance_lease_current", "us-gaap:AssetsCurrent"),
        ("finance_lease_noncurrent", "us-gaap:AssetsNoncurrent"),
    ],
)
def test_generic_orientation_words_do_not_create_structural_candidates(
    metric: str, qname: str
) -> None:
    decision = resolve_concept(
        metric_request(metric),
        [
            account_fact(
                qname,
                labels=(("standard", qname.split(":", 1)[-1]),),
                documentation=None,
            )
        ],
    )

    assert decision.status == "unresolved"
    assert decision.value is None
    assert decision.reason_codes == ("NO_CANDIDATE",)


def test_missing_commercial_paper_borrowing_is_unresolved_not_zero() -> None:
    decision = resolve_concept(metric_request("commercial_paper"), [])

    assert decision.status == "unresolved"
    assert decision.value is None
    assert decision.reason_codes == ("NO_CANDIDATE",)


def _issuer_current_borrowings_fact(
    *, presentation_parents: tuple[str, ...], calculation_parents: tuple[str, ...]
) -> StructuralFact:
    return account_fact(
        "issuer:CurrentBorrowingsAndMaturities",
        labels=(("standard", "Current borrowings and maturities"),),
        documentation="Aggregate current debt carrying amount.",
        statement_roles=(),
        presentation_parents=presentation_parents,
        calculation_parents=calculation_parents,
        relationships=(
            StructuralRelationship(
                arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                linkrole="https://example.test/role/BalanceSheet",
                from_concept="us-gaap:LiabilitiesCurrentAbstract",
                to_concept="issuer:CurrentBorrowingsAndMaturities",
                order=1.0,
                preferred_label=None,
                calculation_weight=None,
            ),
        ),
    )


def test_issuer_current_borrowings_extension_is_accepted_with_two_structural_signals() -> None:
    fact = _issuer_current_borrowings_fact(
        presentation_parents=("us-gaap:LiabilitiesCurrentAbstract",),
        calculation_parents=("us-gaap:LiabilitiesCurrentAbstract",),
    )

    decision = resolve_concept(metric_request("current_debt"), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert decision.value == 100.0
    assert set(decision.reason_codes) >= {
        "CURRENT_LIABILITY_PRESENTATION_PARENT",
        "CURRENT_LIABILITY_CALCULATION_PARENT",
        "DEFINITION_IDENTIFIES_DEBT",
    }
    assert "DEFINITION_IDENTIFIES_MARKETABLE_SECURITIES" not in decision.reason_codes


@pytest.mark.parametrize("missing", ["presentation_parents", "calculation_parents"])
def test_issuer_current_borrowings_missing_one_structural_signal_is_review(
    missing: str,
) -> None:
    parents = ("us-gaap:LiabilitiesCurrentAbstract",)
    overrides = {
        "presentation_parents": parents if missing != "presentation_parents" else (),
        "calculation_parents": parents if missing != "calculation_parents" else (),
    }
    fact = _issuer_current_borrowings_fact(**overrides)

    decision = resolve_concept(metric_request("current_debt"), [fact])

    assert decision.status == "review"
    assert decision.confidence == 0.75


def test_long_term_debt_current_rejects_noncurrent_parent_conflict() -> None:
    parents = ("us-gaap:LiabilitiesNoncurrentAbstract",)
    decision = resolve_concept(
        metric_request("current_debt"),
        [
            account_fact(
                "us-gaap:LongTermDebtCurrent",
                value=0,
                statement_roles=("balance_sheet",),
                presentation_parents=parents,
                calculation_parents=parents,
            )
        ],
    )

    assert decision.status == "rejected"
    assert decision.reason_codes == ("CURRENT_NONCURRENT_CONFLICT",)


@pytest.mark.parametrize(
    "metric,qname,value,parent",
    [
        (
            "finance_lease_current",
            "us-gaap:FinanceLeaseLiabilityCurrent",
            220_000_000,
            "us-gaap:FinanceLeaseLiabilitiesCurrentAbstract",
        ),
        (
            "finance_lease_noncurrent",
            "us-gaap:FinanceLeaseLiabilityNoncurrent",
            444_000_000,
            "us-gaap:FinanceLeaseLiabilitiesNoncurrentAbstract",
        ),
    ],
)
def test_direct_finance_lease_liability_aliases_are_accepted(
    metric: str, qname: str, value: float, parent: str
) -> None:
    decision = resolve_concept(
        metric_request(metric),
        [
            account_fact(
                qname,
                value=value,
                statement_roles=(),
                presentation_parents=(parent,),
            )
        ],
    )

    assert decision.status == "accepted"
    assert decision.value == value
    assert decision.source_concept == qname


@pytest.mark.parametrize(
    "metric",
    ["finance_lease_current", "finance_lease_noncurrent"],
)
def test_finance_lease_split_extension_under_payment_schedule_parent_is_not_accepted(
    metric: str,
) -> None:
    parent = "us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract"
    fact = account_fact(
        "issuer:FinanceLeaseLiabilityCarryingValue",
        documentation="Finance lease liability carrying value.",
        statement_roles=(),
        presentation_parents=(parent,),
        calculation_parents=(parent,),
    )

    decision = resolve_concept(metric_request(metric), [fact])

    assert decision.status != "accepted"


@pytest.mark.parametrize(
    "metric,qname,parent",
    [
        (
            "finance_lease_current",
            "us-gaap:FinanceLeaseLiabilityCurrent",
            "us-gaap:FinanceLeaseLiabilitiesCurrentAbstract",
        ),
        (
            "finance_lease_noncurrent",
            "us-gaap:FinanceLeaseLiabilityNoncurrent",
            "us-gaap:FinanceLeaseLiabilitiesNoncurrentAbstract",
        ),
    ],
)
@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"unit": "shares"}, "UNIT_MISMATCH"),
        ({"period_end": "2024-12-31"}, "PERIOD_MISMATCH"),
        ({"source_accession": "other-accession"}, "ACCESSION_MISMATCH"),
        ({"statement_roles": ("income_statement",)}, "STATEMENT_ROLE_MISMATCH"),
        (
            {
                "dimensions": (
                    ("us-gaap:ProductOrServiceAxis", "us-gaap:FinanceLeaseMember"),
                )
            },
            "DIMENSIONED_NONCONSOLIDATED_FACT",
        ),
    ],
)
def test_finance_lease_direct_alias_enforces_accounting_gates(
    metric: str,
    qname: str,
    parent: str,
    overrides: dict[str, object],
    reason: str,
) -> None:
    fact_values: dict[str, object] = {
        "value": 220_000_000,
        "statement_roles": (),
        "presentation_parents": (parent,),
        "calculation_parents": (parent,),
    }
    fact_values.update(overrides)

    decision = resolve_concept(
        metric_request(metric),
        [account_fact(qname, **fact_values)],
    )

    assert decision.status == "rejected"
    assert decision.reason_codes == (reason,)


@pytest.mark.parametrize(
    "metric",
    [
        "finance_lease_current",
        "finance_lease_noncurrent",
        "finance_lease_total",
    ],
)
def test_finance_lease_absence_is_unresolved_not_zero(metric: str) -> None:
    decision = resolve_concept(metric_request(metric), [])

    assert decision.status == "unresolved"
    assert decision.value is None
    assert decision.reason_codes == ("NO_CANDIDATE",)


def test_finance_lease_total_accepts_net_carrying_value_not_gross_payments() -> None:
    carrying_value = account_fact(
        "us-gaap:FinanceLeaseLiability",
        value=664_000_000,
        statement_roles=(),
        presentation_parents=("us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",),
    )
    gross_payments = account_fact(
        "us-gaap:FinanceLeaseLiabilityPaymentsDue",
        value=718_000_000,
        statement_roles=(),
        presentation_parents=("us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",),
    )

    decision = resolve_concept(
        metric_request("finance_lease_total"), [carrying_value, gross_payments]
    )

    assert decision.status == "accepted"
    assert decision.value == 664_000_000
    assert decision.source_concept == "us-gaap:FinanceLeaseLiability"


def test_finance_lease_total_gross_payments_alone_are_not_accepted() -> None:
    gross_payments = account_fact(
        "us-gaap:FinanceLeaseLiabilityPaymentsDue",
        value=718_000_000,
        statement_roles=(),
        presentation_parents=("us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",),
    )

    decision = resolve_concept(metric_request("finance_lease_total"), [gross_payments])

    assert decision.status == "review"
    assert decision.status != "accepted"


@pytest.mark.parametrize(
    "metric,qname,documentation",
    [
        (
            "finance_lease_current",
            "us-gaap:FinanceLeaseLiabilityPaymentsDueNextTwelveMonths",
            "Finance lease payments due in the next twelve months.",
        ),
        (
            "finance_lease_noncurrent",
            "us-gaap:FinanceLeaseLiabilityPaymentsDueYearTwoThroughThereafter",
            "Finance lease payments due in year two through thereafter.",
        ),
    ],
)
def test_finance_lease_payment_schedule_facts_cannot_satisfy_carrying_value_requests(
    metric: str, qname: str, documentation: str
) -> None:
    decision = resolve_concept(
        metric_request(metric),
        [
            account_fact(
                qname,
                documentation=documentation,
                presentation_parents=(
                    "us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",
                ),
                calculation_parents=(
                    "us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",
                ),
            )
        ],
    )

    assert decision.status in {"review", "rejected"}
    assert decision.status != "accepted"


@pytest.mark.parametrize(
    "qname,documentation,expected_status,expected_reason",
    [
        (
            "us-gaap:OperatingLeaseLiabilityCurrent",
            "Operating lease liability current carrying value.",
            "rejected",
            "EXCLUDED_ECONOMIC_CLASS",
        ),
        (
            "us-gaap:RightOfUseAsset",
            "Right of use asset.",
            "rejected",
            "EXCLUDED_ECONOMIC_CLASS",
        ),
        ("us-gaap:LeaseCost", "Lease cost.", "unresolved", "NO_CANDIDATE"),
        (
            "us-gaap:PaymentsForOperatingLeases",
            "Cash payments for operating leases.",
            "unresolved",
            "NO_CANDIDATE",
        ),
        (
            "issuer:LeaseCommitments",
            "Generic lease commitments.",
            "unresolved",
            "NO_CANDIDATE",
        ),
    ],
)
def test_non_finance_lease_economics_are_rejected_from_carrying_value(
    qname: str,
    documentation: str,
    expected_status: str,
    expected_reason: str,
) -> None:
    decision = resolve_concept(
        metric_request("finance_lease_total"),
        [
            account_fact(
                qname,
                documentation=documentation,
                presentation_parents=("us-gaap:LiabilitiesCurrentAbstract",),
                calculation_parents=("us-gaap:LiabilitiesCurrentAbstract",),
            )
        ],
    )

    assert decision.status == expected_status
    assert decision.reason_codes == (expected_reason,)


def test_load_structural_rules_is_versioned_and_has_both_marketable_metrics() -> None:
    rules = load_structural_rules()

    assert rules["version"] == "US-XBRL-RESOLVER-1.1"
    assert set(rules) >= {
        "version",
        "marketable_securities_current",
        "marketable_securities_noncurrent",
    }
    metric_rules = {
        key: value
        for key, value in rules.items()
        if isinstance(value, dict) and "statement_role" in value
    }
    assert set(metric_rules) == {
        "marketable_securities_current",
        "marketable_securities_noncurrent",
        "current_debt",
        "noncurrent_debt",
        "commercial_paper",
        "finance_lease_current",
        "finance_lease_noncurrent",
        "finance_lease_total",
        "preferred_equity",
        "noncontrolling_interests",
    }
    required_policy_fields = {
        "orientation",
        "statement_support_parents",
        "direct_statement_parents",
        "structural_parents",
        "extension_terms",
        "required_definition_phrases",
        "excluded_economic_phrases",
        "preferred_exclusion_evidence_phrases",
        "component_only_concepts",
        "review_only_phrases",
        "direct_statement_concepts",
        "concept_reason_codes",
        "allowed_dimensions",
        "allowed_extension_dimensions",
        "contextual_concepts",
    }
    assert all(required_policy_fields <= set(policy) for policy in metric_rules.values())
    assert {policy["orientation"] for policy in metric_rules.values()} == {
        "current",
        "noncurrent",
        "none",
    }
    assert all(policy["excluded_economic_phrases"] for policy in metric_rules.values())
    assert all(
        isinstance(policy["preferred_exclusion_evidence_phrases"], list)
        for policy in metric_rules.values()
    )
    assert rules["commercial_paper"]["preferred_exclusion_evidence_phrases"] == [
        "amortized cost",
        "marketable securities",
        "fair value",
    ]


def test_preferred_zero_conflict_companions_must_be_nonempty_strings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    rules = load_structural_rules()
    rules["preferred_equity"]["preferred_zero_value_conflict_companion_concepts"] = [
        "us-gaap:PreferredStockSharesOutstanding",
        "",
    ]
    rules_path = tmp_path / "structural_concept_rules.json"  # type: ignore[operator]
    rules_path.write_text(json.dumps(rules), encoding="utf-8")
    monkeypatch.setattr(concept_resolver_module, "_RULES_PATH", rules_path)

    with pytest.raises(ValueError, match="preferred_zero_value_conflict_companion_concepts"):
        concept_resolver_module.load_structural_rules()


def test_preferred_zero_conflict_reason_must_be_nonempty_string(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    rules = load_structural_rules()
    rules["preferred_equity"]["preferred_zero_value_conflict_reason"] = ""
    rules_path = tmp_path / "structural_concept_rules.json"  # type: ignore[operator]
    rules_path.write_text(json.dumps(rules), encoding="utf-8")
    monkeypatch.setattr(concept_resolver_module, "_RULES_PATH", rules_path)

    with pytest.raises(ValueError, match="preferred_zero_value_conflict_reason"):
        concept_resolver_module.load_structural_rules()
    assert {rules["version"]} == {"US-XBRL-RESOLVER-1.1"}
    assert "excluded_economic_phrases" not in rules
    assert tuple(rules["official_us_gaap_namespaces"]) == OFFICIAL_NAMESPACES


@pytest.mark.parametrize("namespace", OFFICIAL_NAMESPACES)
def test_every_governed_official_namespace_accepts_exact_standard_identity(
    namespace: str,
) -> None:
    fact = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        namespace=namespace,
        value=100.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.98
    assert decision.mapping_method == "known_taxonomy_alias"


@pytest.mark.parametrize(
    "namespace",
    [
        "http://xbrl.us/us-gaap/2008-02-01",
        "http://xbrl.us/us-gaap/2009-13-01",
        "http://xbrl.us/us-gaap/2024-01-31",
        "http://fasb.org/us-gaap/2021-02-01",
        "http://fasb.org/us-gaap/2024-01-31",
        "http://fasb.org/us-gaap/2027",
        "http://fasb.org/us-gaap/2026-01-31",
    ],
)
def test_unknown_or_malformed_namespace_is_not_standard_identity(namespace: str) -> None:
    fact = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        namespace=namespace,
        value=100.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert decision.mapping_method == "extension_structural_match"


def test_known_standard_alias_is_accepted() -> None:
    fact = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        value=100.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.98
    assert decision.mapping_method == "known_taxonomy_alias"
    assert decision.source_concept == "us-gaap:ShortTermInvestments"
    assert decision.source_accession == ACCESSION
    assert decision.value == 100.0


@pytest.mark.parametrize(
    "qname,namespace",
    [
        (
            "ShortTermInvestments",
            "https://issuer.example/us-gaap/2025",
        ),
        (
            "fsi:ShortTermInvestments",
            "https://issuer.example/us-gaap/2025",
        ),
        (
            "us-gaap:ShortTermInvestments",
            "https://fasb.org/us-gaap/2025",
        ),
        (
            "us-gaap:ShortTermInvestments",
            "http://fasb.org.evil/us-gaap/2025",
        ),
        (
            "us-gaap:ShortTermInvestments",
            "http://fasb.org/US-GAAP/2025",
        ),
        (
            "us-gaap:ShortTermInvestments",
            "http://xbrl.us.evil/us-gaap/2024-01-31",
        ),
        (
            "us-gaap:ShortTermInvestments",
            "https://xbrl.us/us-gaap/2024-01-31",
        ),
    ],
)
def test_issuer_namespace_cannot_spoof_standard_alias(
    qname: str, namespace: str
) -> None:
    fact = make_fact(
        qname=qname,
        local_name="ShortTermInvestments",
        namespace=namespace,
        value=100.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert decision.mapping_method == "extension_structural_match"
    assert decision.source_concept == qname


def test_unqualified_qname_cannot_be_standard_identity() -> None:
    fact = make_fact(
        qname="ShortTermInvestments",
        local_name="ShortTermInvestments",
        namespace="http://fasb.org/us-gaap/2025",
        value=100.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert decision.mapping_method == "extension_structural_match"


def test_exact_official_namespace_and_prefixed_qname_are_standard_identity() -> None:
    fact = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        namespace="http://fasb.org/us-gaap/2025",
        value=100.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.98
    assert decision.mapping_method == "known_taxonomy_alias"


@pytest.mark.parametrize("namespace", ["http://xbrl.us/us-gaap/2008-01-31", "http://xbrl.us/us-gaap/2009-01-31"])
def test_legacy_xbrl_us_dated_namespace_is_standard_identity(namespace: str) -> None:
    fact = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        namespace=namespace,
        value=100.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.98
    assert decision.mapping_method == "known_taxonomy_alias"


def test_qname_and_local_name_must_both_match_standard_concept() -> None:
    qname_only = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="OtherInvestmentConcept",
        namespace="http://fasb.org/us-gaap/2025",
        value=100.0,
    )
    local_name_only = make_fact(
        qname="fsi:OtherInvestmentConcept",
        local_name="ShortTermInvestments",
        namespace="http://fasb.org/us-gaap/2025",
        value=100.0,
    )

    qname_decision = resolve_concept(current_request(), [qname_only])
    local_name_decision = resolve_concept(current_request(), [local_name_only])

    assert qname_decision.mapping_method == "extension_structural_match"
    assert local_name_decision.mapping_method == "extension_structural_match"
    assert qname_decision.confidence == local_name_decision.confidence == 0.96


def test_first_configured_standard_concept_is_exactly_accepted() -> None:
    fact = make_fact(
        qname="us-gaap:MarketableSecuritiesCurrent",
        local_name="MarketableSecuritiesCurrent",
        value=101.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 1.00
    assert decision.mapping_method == "exact_configured_concept"
    assert decision.source_concept == "us-gaap:MarketableSecuritiesCurrent"


def test_extension_requires_two_independent_structural_signals() -> None:
    fact = make_fact(
        qname="fsi:LiquidInvestmentSecuritiesCurrent",
        local_name="LiquidInvestmentSecuritiesCurrent",
        documentation="Available-for-sale debt securities classified as current.",
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
        value=125.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert decision.mapping_method == "extension_structural_match"
    assert decision.value == 125.0
    assert decision.reason_codes[-1] == "DEFINITION_IDENTIFIES_MARKETABLE_SECURITIES"
    assert set(decision.reason_codes) >= {
        "CURRENT_ASSET_PRESENTATION_PARENT",
        "CURRENT_ASSET_CALCULATION_PARENT",
        "DEFINITION_IDENTIFIES_MARKETABLE_SECURITIES",
    }
    assert decision.source_concept == "fsi:LiquidInvestmentSecuritiesCurrent"


@pytest.mark.parametrize("missing", ["presentation_parents", "calculation_parents"])
def test_extension_missing_one_structural_signal_is_review(missing: str) -> None:
    overrides: dict[str, object] = {missing: ()}
    decision = resolve_concept(current_request(), [make_fact(**overrides)])

    assert decision.status == "review"
    assert decision.confidence == 0.75
    assert decision.mapping_method == "insufficient_structural_support"
    assert decision.source_concept == "fsi:LiquidInvestmentSecuritiesCurrent"
    assert decision.source_accession == ACCESSION


def test_label_only_extension_is_review_not_accepted() -> None:
    fact = make_fact(
        qname="fsi:MarketableInvestments",
        local_name="MarketableInvestments",
        labels=(("standard", "Marketable investments"),),
        documentation="",
        presentation_parents=(),
        calculation_parents=(),
        value=90.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "review"
    assert decision.confidence == 0.75
    assert decision.mapping_method == "insufficient_structural_support"
    assert decision.source_concept == "fsi:MarketableInvestments"


@pytest.mark.parametrize(
    "qname,documentation",
    [
        ("fsi:StrategicEquityInvestments", "Strategic nonmarketable equity investments."),
        ("fsi:EquityMethodInvestments", "Investments accounted for under the equity method."),
        ("fsi:RestrictedTrustAssets", "Restricted assets held in trust as collateral."),
        ("fsi:CustomerFinancingReceivables", "Customer financing receivables."),
    ],
)
def test_false_friends_are_rejected(qname: str, documentation: str) -> None:
    fact = make_fact(qname=qname, documentation=documentation)

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)
    assert decision.source_concept == qname
    assert decision.source_accession == ACCESSION


def test_excluded_economic_class_cannot_be_overridden_by_structural_support() -> None:
    fact = make_fact(
        qname="fsi:StrategicMarketableInvestments",
        documentation="Strategic investments in available-for-sale debt securities.",
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"source_accession": "other-accession"}, "ACCESSION_MISMATCH"),
        ({"period_end": "2024-12-31"}, "PERIOD_MISMATCH"),
        ({"unit": "shares"}, "UNIT_MISMATCH"),
        ({"statement_roles": ("income_statement",)}, "STATEMENT_ROLE_MISMATCH"),
        ({"dimensions": (("consolidation", "subsidiary"),)}, "DIMENSIONED_NONCONSOLIDATED_FACT"),
    ],
)
def test_accounting_hard_gate_rejects_candidate(
    overrides: dict[str, object], reason: str
) -> None:
    fact = make_fact(**overrides)

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.reason_codes == (reason,)
    assert decision.source_concept == fact.qname
    assert decision.source_accession == fact.source_accession


def test_failed_accounting_gate_is_not_overridden_by_extension_wording_or_confidence() -> None:
    fact = make_fact(
        unit="shares",
        documentation="Available-for-sale debt securities classified as current.",
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.mapping_method == "hard_gate_rejection"
    assert decision.reason_codes == ("UNIT_MISMATCH",)


@pytest.mark.parametrize(
    "qname,local_name",
    [
        ("us-gaap:ShortTermInvestments", "ShortTermInvestments"),
        ("fsi:LiquidInvestmentSecuritiesCurrent", "LiquidInvestmentSecuritiesCurrent"),
    ],
)
def test_missing_numeric_value_is_a_schema_valid_hard_gate(
    qname: str, local_name: str
) -> None:
    fact = make_fact(qname=qname, local_name=local_name, value=None)

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.mapping_method == "hard_gate_rejection"
    assert decision.reason_codes == ("MISSING_NUMERIC_VALUE",)
    assert decision.source_concept == qname
    assert decision.value is None


def test_current_request_rejects_noncurrent_fact() -> None:
    fact = make_fact(
        qname="us-gaap:LongTermInvestments",
        local_name="LongTermInvestments",
        presentation_parents=("us-gaap:AssetsNoncurrent",),
        calculation_parents=("us-gaap:AssetsNoncurrent",),
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("CURRENT_NONCURRENT_CONFLICT",)
    assert decision.source_concept == fact.qname


def test_noncurrent_request_rejects_current_fact() -> None:
    fact = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
    )

    decision = resolve_concept(noncurrent_request(), [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("CURRENT_NONCURRENT_CONFLICT",)
    assert decision.source_concept == fact.qname


def test_noncurrent_extension_uses_noncurrent_structural_signals() -> None:
    fact = make_fact(
        qname="fsi:LiquidInvestmentSecuritiesNoncurrent",
        local_name="LiquidInvestmentSecuritiesNoncurrent",
        documentation="Available-for-sale debt securities classified as noncurrent.",
        presentation_parents=("us-gaap:AssetsNoncurrent",),
        calculation_parents=("us-gaap:AssetsNoncurrent",),
        value=130.0,
    )

    decision = resolve_concept(noncurrent_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert decision.mapping_method == "extension_structural_match"
    assert set(decision.reason_codes) >= {
        "NONCURRENT_ASSET_PRESENTATION_PARENT",
        "NONCURRENT_ASSET_CALCULATION_PARENT",
        "DEFINITION_IDENTIFIES_MARKETABLE_SECURITIES",
    }


@pytest.mark.parametrize(
    "metric_request,parents",
    [
        (current_request(), ("us-gaap:AssetsNoncurrent",)),
        (noncurrent_request(), ("us-gaap:AssetsCurrent",)),
        (
            current_request(),
            ("us-gaap:AssetsCurrent", "us-gaap:AssetsNoncurrent"),
        ),
        (
            noncurrent_request(),
            ("us-gaap:AssetsCurrent", "us-gaap:AssetsNoncurrent"),
        ),
    ],
)
def test_structural_parent_orientation_rejects_generic_or_contradictory_facts(
    metric_request: ResolutionRequest, parents: tuple[str, ...]
) -> None:
    fact = make_fact(
        qname="fsi:InvestmentSecurities",
        local_name="InvestmentSecurities",
        documentation="Available-for-sale debt securities.",
        presentation_parents=parents,
        calculation_parents=parents,
    )

    decision = resolve_concept(metric_request, [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("CURRENT_NONCURRENT_CONFLICT",)


@pytest.mark.parametrize(
    "metric_request,qname,parents",
    [
        (
            current_request(),
            "fsi:InvestmentSecuritiesNoncurrent",
            ("us-gaap:AssetsCurrent",),
        ),
        (
            noncurrent_request(),
            "fsi:InvestmentSecuritiesCurrent",
            ("us-gaap:AssetsNoncurrent",),
        ),
    ],
)
def test_explicit_noncurrent_or_current_name_conflicts_with_parent_orientation(
    metric_request: ResolutionRequest, qname: str, parents: tuple[str, ...]
) -> None:
    fact = make_fact(
        qname=qname,
        local_name=qname.split(":", 1)[-1],
        documentation="Available-for-sale debt securities.",
        presentation_parents=parents,
        calculation_parents=parents,
    )

    decision = resolve_concept(metric_request, [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("CURRENT_NONCURRENT_CONFLICT",)


def test_camel_case_exclusion_is_visible_to_economic_gate() -> None:
    fact = make_fact(
        qname="fsi:RestrictedMarketableSecuritiesCurrent",
        local_name="RestrictedMarketableSecuritiesCurrent",
        documentation="Available-for-sale debt securities classified as current.",
        value=135.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_underscore_is_a_token_separator_for_exclusions() -> None:
    fact = make_fact(
        qname="fsi:Restricted_MarketableSecuritiesCurrent",
        local_name="Restricted_MarketableSecuritiesCurrent",
        documentation="Available-for-sale debt securities classified as current.",
        value=135.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_unrestricted_does_not_match_restricted_exclusion() -> None:
    fact = make_fact(
        qname="fsi:UnrestrictedInvestmentSecuritiesCurrent",
        local_name="UnrestrictedInvestmentSecuritiesCurrent",
        documentation="Unrestricted available-for-sale debt securities classified as current.",
        labels=(("standard", "Unrestricted investment securities"),),
        value=135.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert decision.reason_codes[-1] == "DEFINITION_IDENTIFIES_MARKETABLE_SECURITIES"


@pytest.mark.parametrize(
    "qname,documentation",
    [
        (
            "fsi:InvestmentSecuritiesNonCurrent",
            "Available-for-sale debt securities.",
        ),
        (
            "fsi:InvestmentSecurities",
            "Non-current available-for-sale debt securities.",
        ),
    ],
)
def test_noncurrent_evidence_does_not_create_current_contradiction(
    qname: str, documentation: str
) -> None:
    fact = make_fact(
        qname=qname,
        local_name=qname.split(":", 1)[-1],
        documentation=documentation,
        presentation_parents=("us-gaap:AssetsNoncurrent",),
        calculation_parents=("us-gaap:AssetsNoncurrent",),
        value=135.0,
    )

    decision = resolve_concept(noncurrent_request(), [fact])

    assert decision.status == "accepted"
    assert decision.confidence == 0.96
    assert decision.mapping_method == "extension_structural_match"


def test_independent_current_and_noncurrent_text_is_contradictory() -> None:
    fact = make_fact(
        qname="fsi:InvestmentSecuritiesNonCurrent",
        local_name="InvestmentSecuritiesNonCurrent",
        documentation="Current and non-current available-for-sale debt securities.",
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
        value=135.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("CURRENT_NONCURRENT_CONFLICT",)


def test_plural_single_word_exclusion_remains_true() -> None:
    fact = make_fact(
        qname="fsi:CustomerFinancingReceivables",
        local_name="CustomerFinancingReceivables",
        documentation="Customer financing receivables.",
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


def test_malformed_multiword_phrase_does_not_satisfy_definition() -> None:
    fact = make_fact(
        qname="fsi:MarketableInvestmentSecuritiesCurrent",
        local_name="MarketableInvestmentSecuritiesCurrent",
        documentation="Available-for-sales instruments classified as current.",
        value=135.0,
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "review"
    assert decision.mapping_method == "insufficient_structural_support"


def test_gate_failure_order_prefers_fact_that_passed_more_hard_gates() -> None:
    period_failure = make_fact(
        period_end="2024-12-31",
        source_accession=ACCESSION,
    )
    unit_failure = make_fact(
        unit="shares",
        source_accession=ACCESSION,
    )

    forward = resolve_concept(current_request(), [period_failure, unit_failure])
    reverse = resolve_concept(current_request(), [unit_failure, period_failure])

    assert forward.status == reverse.status == "rejected"
    assert forward.reason_codes == reverse.reason_codes == ("UNIT_MISMATCH",)
    assert forward.source_concept == reverse.source_concept
    assert forward.source_accession == reverse.source_accession == ACCESSION


def test_equal_strength_conflicting_facts_are_ambiguous() -> None:
    first = make_fact(
        qname="us-gaap:AvailableForSaleSecuritiesCurrent",
        local_name="AvailableForSaleSecuritiesCurrent",
        value=100.0,
    )
    second = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        value=110.0,
    )

    decision = resolve_concept(current_request(), [first, second])

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.mapping_method == "hard_gate_rejection"
    assert decision.reason_codes == ("AMBIGUOUS_FACTS",)


def test_equal_strength_same_value_distinct_candidates_are_ambiguous() -> None:
    first = make_fact(
        qname="us-gaap:AvailableForSaleSecuritiesCurrent",
        local_name="AvailableForSaleSecuritiesCurrent",
        value=100.0,
    )
    second = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        value=100.0,
    )

    decision = resolve_concept(current_request(), [first, second])

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.mapping_method == "hard_gate_rejection"
    assert decision.reason_codes == ("AMBIGUOUS_FACTS",)


def test_canonical_candidate_outranks_conflicting_alias_before_ambiguity() -> None:
    canonical = make_fact(
        qname="us-gaap:MarketableSecuritiesCurrent",
        local_name="MarketableSecuritiesCurrent",
        value=100.0,
    )
    alias = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        value=110.0,
    )

    decision = resolve_concept(current_request(), [canonical, alias])

    assert decision.status == "accepted"
    assert decision.confidence == 1.0
    assert decision.source_concept == "us-gaap:MarketableSecuritiesCurrent"


def test_exact_duplicate_facts_are_deduplicated_before_ambiguity() -> None:
    duplicate = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        value=100.0,
    )

    decision = resolve_concept(current_request(), [duplicate, duplicate])

    assert decision.status == "accepted"
    assert decision.source_concept == "us-gaap:ShortTermInvestments"


@pytest.mark.parametrize("form", ["10-K", "10-K/A", "10-Q", "10-Q/A"])
def test_all_governed_forms_can_resolve(form: str) -> None:
    fact = make_fact(
        qname="us-gaap:ShortTermInvestments",
        local_name="ShortTermInvestments",
        filing_form=form,
    )

    assert resolve_concept(current_request(form=form), [fact]).status == "accepted"


@pytest.mark.parametrize("form", ["8-K", "20-F", "S-1", ""])
def test_unsupported_forms_are_stably_unresolved(form: str) -> None:
    decision = resolve_concept(current_request(form=form), [make_fact()])

    assert decision.status == "unresolved"
    assert decision.reason_codes == ("INELIGIBLE_FILING_FORM",)


def test_calculation_linked_component_and_total_candidates_are_rejected() -> None:
    total = make_fact(
        qname="fsi:MarketableSecuritiesCurrentTotal",
        local_name="MarketableSecuritiesCurrentTotal",
        calculation_children=("fsi:ShortTermInvestmentComponent",),
        value=150.0,
    )
    component = make_fact(
        qname="fsi:ShortTermInvestmentComponent",
        local_name="ShortTermInvestmentComponent",
        calculation_parents=("fsi:MarketableSecuritiesCurrentTotal",),
        value=75.0,
    )

    decision = resolve_concept(current_request(), [total, component])

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.mapping_method == "hard_gate_rejection"
    assert decision.reason_codes == ("COMPONENT_TOTAL_CONFLICT",)


def test_no_candidate_is_unresolved() -> None:
    fact = make_fact(
        qname="us-gaap:CashAndCashEquivalentsAtCarryingValue",
        local_name="CashAndCashEquivalentsAtCarryingValue",
        labels=(),
        documentation="Cash and cash equivalents.",
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
    )

    decision = resolve_concept(current_request(), [fact])

    assert decision.status == "unresolved"
    assert decision.confidence == 0.0
    assert decision.source_concept is None
    assert decision.source_accession == ACCESSION
    assert decision.reason_codes == ("NO_CANDIDATE",)


def _install_contextual_dimension_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    rules = load_structural_rules()
    rules["contextual_metric"] = {
        "statement_role": "balance_sheet",
        "unit": "USD",
        "orientation": "none",
        "statement_support_parents": ["us-gaap:EquityRollForward"],
        "direct_statement_parents": [],
        "structural_parents": ["us-gaap:EquityRollForward"],
        "extension_terms": ["contextual equity"],
        "required_definition_phrases": [],
        "excluded_economic_phrases": [],
        "component_only_concepts": [],
        "review_only_phrases": [],
        "direct_statement_concepts": [],
        "concept_reason_codes": {},
        "allowed_dimensions": {
            "us-gaap:ContextualEquity": [
                [
                    "us-gaap:StatementEquityComponentsAxis",
                    "us-gaap:NoncontrollingInterestMember",
                ]
            ]
        },
        "contextual_concepts": ["us-gaap:ContextualEquity"],
    }
    monkeypatch.setattr(concept_resolver_module, "load_structural_rules", lambda: rules)
    monkeypatch.setattr(
        concept_resolver_module,
        "_load_aliases",
        lambda: {"fields": {"contextual_metric": {"concepts": []}}},
    )


def test_unsegmented_contextual_concept_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_contextual_dimension_policy(monkeypatch)
    fact = account_fact(
        "us-gaap:ContextualEquity",
        statement_roles=(),
        presentation_parents=("us-gaap:EquityRollForward",),
        calculation_parents=(),
        dimensions=(),
        value=100.0,
    )

    decision = resolve_concept(metric_request("contextual_metric"), [fact])

    assert decision.status == "rejected"
    assert decision.reason_codes == ("DIMENSIONED_NONCONSOLIDATED_FACT",)


def test_contextual_concept_accepts_exact_configured_dimension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_contextual_dimension_policy(monkeypatch)
    fact = account_fact(
        "us-gaap:ContextualEquity",
        statement_roles=(),
        presentation_parents=("us-gaap:EquityRollForward",),
        calculation_parents=(),
        dimensions=(
            (
                "us-gaap:StatementEquityComponentsAxis",
                "us-gaap:NoncontrollingInterestMember",
            ),
        ),
        value=100.0,
    )

    decision = resolve_concept(metric_request("contextual_metric"), [fact])

    assert decision.status == "accepted"
    assert decision.value == 100.0
    assert decision.mapping_method == "taxonomy_and_context"
    assert "GOVERNED_DIMENSIONAL_CONTEXT" in decision.reason_codes
