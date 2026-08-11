from __future__ import annotations

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
    "qname,documentation",
    [
        ("us-gaap:DebtMaturitySchedule", "Debt maturity repayments."),
        ("us-gaap:DebtInstrumentFaceAmount", "Debt instrument face amount."),
        ("us-gaap:DebtInstrumentFairValue", "Debt instrument fair value."),
        (
            "us-gaap:ProceedsFromIssuanceOfLongTermDebt",
            "Proceeds from debt issuance cash flows.",
        ),
        (
            "us-gaap:RepaymentsOfLongTermDebt",
            "Repayments of long-term debt cash flows.",
        ),
    ],
)
def test_debt_schedule_valuation_and_cash_flow_facts_are_rejected(
    qname: str, documentation: str
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

    assert decision.status == "rejected"
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


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
    overrides: dict[str, object], reason: str
) -> None:
    parent = "us-gaap:FinanceLeaseLiabilitiesCurrentAbstract"
    fact_values: dict[str, object] = {
        "value": 220_000_000,
        "statement_roles": (),
        "presentation_parents": (parent,),
        "calculation_parents": (parent,),
    }
    fact_values.update(overrides)

    decision = resolve_concept(
        metric_request("finance_lease_current"),
        [account_fact("us-gaap:FinanceLeaseLiabilityCurrent", **fact_values)],
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
    "qname,documentation",
    [
        (
            "us-gaap:OperatingLeaseLiabilityCurrent",
            "Operating lease liability current carrying value.",
        ),
        ("us-gaap:RightOfUseAsset", "Right of use asset."),
        ("us-gaap:LeaseCost", "Lease cost."),
        (
            "us-gaap:PaymentsForOperatingLeases",
            "Cash payments for operating leases.",
        ),
        ("issuer:LeaseCommitments", "Generic lease commitments."),
    ],
)
def test_non_finance_lease_economics_are_rejected_from_carrying_value(
    qname: str, documentation: str
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

    assert decision.status == "rejected"
    assert decision.reason_codes == ("EXCLUDED_ECONOMIC_CLASS",)


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
    }
    required_policy_fields = {
        "orientation",
        "statement_support_parents",
        "direct_statement_parents",
        "structural_parents",
        "extension_terms",
        "required_definition_phrases",
        "excluded_economic_phrases",
        "component_only_concepts",
        "review_only_phrases",
        "direct_statement_concepts",
        "concept_reason_codes",
        "allowed_dimensions",
        "contextual_concepts",
    }
    assert all(required_policy_fields <= set(policy) for policy in metric_rules.values())
    assert {policy["orientation"] for policy in metric_rules.values()} == {
        "current",
        "noncurrent",
        "none",
    }
    assert all(policy["excluded_economic_phrases"] for policy in metric_rules.values())
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


def test_gate_failure_order_is_stable_for_same_qname_and_accession() -> None:
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
    assert forward.reason_codes == reverse.reason_codes == ("PERIOD_MISMATCH",)
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


def test_equal_strength_same_value_facts_are_not_treated_as_conflicting() -> None:
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

    assert decision.status == "accepted"
    assert decision.value == 100.0
    assert decision.source_concept == "us-gaap:AvailableForSaleSecuritiesCurrent"


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
