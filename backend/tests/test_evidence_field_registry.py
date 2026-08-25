"""FOD2 contract tests for governed field semantics."""

from __future__ import annotations

from app.us_valuation.evidence_field_registry import GovernedField, load_field_registry


def test_registry_contains_governed_standard_and_custom_field_definitions() -> None:
    registry = load_field_registry()

    debt = registry["noncurrent_debt"]
    affo = registry["reit_affo"]

    assert isinstance(debt, GovernedField)
    assert "us-gaap:LongTermDebtNoncurrent" in debt.standard_aliases
    assert debt.statement_roles
    assert debt.allowed_dimensions == ()
    assert debt.consolidation_level == "consolidated_parent"
    assert debt.allowed_units == ("USD",)
    assert debt.period_role == "balance_sheet_snapshot"
    assert debt.accounting_meaning
    assert debt.economic_class == "financing_claim"

    assert isinstance(affo, GovernedField)
    assert "custom" in affo.custom_aliases
    assert affo.statement_roles
    assert affo.period_role == "operating_ttm"
    assert affo.accounting_meaning
    assert affo.economic_class == "reit_non_gaap_cash_flow"


def test_registry_declares_aggregate_coverage_and_double_count_exclusions() -> None:
    registry = load_field_registry()
    lease_total = registry["finance_lease_total"]

    assert lease_total.valid_aggregate_replacements == (
        "finance_lease_current",
        "finance_lease_noncurrent",
    )
    assert "finance_lease_total" in lease_total.double_counting_exclusions
    assert "finance_lease_current" in lease_total.double_counting_exclusions
    assert "finance_lease_noncurrent" in lease_total.double_counting_exclusions


def test_registry_returns_immutable_definitions_and_rejects_unconfigured_fields() -> None:
    registry = load_field_registry()
    debt = registry["noncurrent_debt"]

    assert debt == load_field_registry()["noncurrent_debt"]
    assert "invented_field" not in registry


def test_registry_requires_exact_dimension_set_without_extra_members() -> None:
    nci = load_field_registry()["noncontrolling_interests"]
    assert nci.allows(
        unit="USD",
        period_role="balance_sheet_snapshot",
        statement_role="balance_sheet",
        consolidation_scope="consolidated_parent",
        dimensions=(("us-gaap:StatementEquityComponentsAxis", "us-gaap:NoncontrollingInterestMember"),),
    )
    assert not nci.allows(
        unit="USD",
        period_role="balance_sheet_snapshot",
        statement_role="balance_sheet",
        consolidation_scope="consolidated_parent",
        dimensions=(
            ("us-gaap:StatementEquityComponentsAxis", "us-gaap:NoncontrollingInterestMember"),
            ("fsi:ExtraAxis", "fsi:ExtraMember"),
        ),
    )
