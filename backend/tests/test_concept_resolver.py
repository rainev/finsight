from __future__ import annotations

import pytest

from app.us_valuation.concept_resolver import load_structural_rules, resolve_concept
from app.us_valuation.structural_xbrl import ResolutionRequest, StructuralFact


ACCESSION = "0000000000-26-000001"
PERIOD = "2025-12-31"


def make_fact(**overrides: object) -> StructuralFact:
    qname = str(overrides.get("qname", "fsi:LiquidInvestmentSecuritiesCurrent"))
    values: dict[str, object] = {
        "qname": qname,
        "namespace": "https://example.test/fsi/2025",
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
    }
    values.update(overrides)
    return StructuralFact(**values)  # type: ignore[arg-type]


def current_request(**overrides: object) -> ResolutionRequest:
    values: dict[str, object] = {
        "normalized_concept": "marketable_securities_current",
        "period_end": PERIOD,
        "source_accession": ACCESSION,
        "unit": "USD",
        "statement_role": "balance_sheet",
    }
    values.update(overrides)
    return ResolutionRequest(**values)  # type: ignore[arg-type]


def noncurrent_request(**overrides: object) -> ResolutionRequest:
    values: dict[str, object] = {
        "normalized_concept": "marketable_securities_noncurrent",
        "period_end": PERIOD,
        "source_accession": ACCESSION,
        "unit": "USD",
        "statement_role": "balance_sheet",
    }
    values.update(overrides)
    return ResolutionRequest(**values)  # type: ignore[arg-type]


def test_load_structural_rules_is_versioned_and_has_both_marketable_metrics() -> None:
    rules = load_structural_rules()

    assert rules["version"] == "US-XBRL-RESOLVER-1.0"
    assert set(rules) >= {
        "version",
        "marketable_securities_current",
        "marketable_securities_noncurrent",
        "excluded_economic_phrases",
    }
    assert rules["marketable_securities_current"]["statement_role"] == (
        "balance_sheet"
    )
    assert rules["marketable_securities_current"]["unit"] == "USD"
    assert rules["marketable_securities_current"]["known_current_parents"] == [
        "us-gaap:AssetsCurrent",
        "us-gaap:ShortTermInvestments",
        "us-gaap:MarketableSecuritiesCurrent",
    ]
    assert rules["marketable_securities_noncurrent"][
        "known_noncurrent_parents"
    ] == [
        "us-gaap:AssetsNoncurrent",
        "us-gaap:LongTermInvestments",
        "us-gaap:MarketableSecuritiesNoncurrent",
    ]
    assert set(rules["excluded_economic_phrases"]) >= {
        "strategic",
        "equity method",
        "restricted",
        "trust",
        "collateral",
        "receivable",
        "financial-institution trading assets",
    }


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


def test_canonical_and_alias_duplicates_are_ambiguous_before_confidence_selection() -> None:
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

    assert decision.status == "rejected"
    assert decision.confidence == 0.0
    assert decision.reason_codes == ("AMBIGUOUS_FACTS",)


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
    assert decision.reason_codes == ("AMBIGUOUS_FACTS",)


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
