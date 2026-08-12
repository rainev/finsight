from __future__ import annotations

import sys

import pytest

from app.us_valuation.structural_xbrl import (
    ParseDiagnostic,
    ResolutionDecision,
    ResolutionEvidence,
    ResolutionRequest,
    StructuralFact,
    StructuralFiling,
    StructuralRelationship,
)


def _fact(**overrides: object) -> StructuralFact:
    values: dict[str, object] = {
        "qname": "fsi:LiquidInvestmentSecuritiesCurrent",
        "namespace": "https://example.test/fsi/2025",
        "local_name": "LiquidInvestmentSecuritiesCurrent",
        "labels": (("standard", "Liquid investment securities"),),
        "documentation": "Available-for-sale debt securities classified as current.",
        "value": 42_500_000.0,
        "unit": "USD",
        "period_start": None,
        "period_end": "2025-12-31",
        "context_id": "CurrentYearInstant",
        "dimensions": (),
        "statement_roles": ("balance_sheet",),
        "presentation_parents": ("us-gaap:AssetsCurrent",),
        "calculation_parents": ("us-gaap:AssetsCurrent",),
        "calculation_children": (),
        "definition_parents": (),
        "definition_children": (),
        "source_accession": "0000000000-26-000001",
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
                to_concept="fsi:LiquidInvestmentSecuritiesCurrent",
                order=1.0,
                preferred_label=None,
                calculation_weight=None,
            ),
        ),
    }
    values.update(overrides)
    return StructuralFact(**values)  # type: ignore[arg-type]


def _decision(**overrides: object) -> ResolutionDecision:
    fact = _fact()
    evidence = ResolutionEvidence.from_fact(
        fact,
        mapping_version="US-XBRL-RESOLVER-1.1",
        confidence=0.95,
        reason_codes=("balance_sheet_role",),
    )
    values: dict[str, object] = {
        "status": "accepted",
        "normalized_concept": "marketable_securities_current",
        "source_concept": "fsi:LiquidInvestmentSecuritiesCurrent",
        "value": 42_500_000.0,
        "unit": "USD",
        "period": "2025-12-31",
        "source_accession": "0000000000-26-000001",
        "confidence": 0.95,
        "mapping_method": "presentation",
        "reason_codes": ("balance_sheet_role",),
        "form": "10-K",
        "evidence": evidence,
    }
    values.update(overrides)
    return ResolutionDecision(**values)  # type: ignore[arg-type]


def test_structural_fact_round_trip_preserves_provenance() -> None:
    fact = _fact(
        qname="fsi:LiquidInvestmentSecuritiesCurrent",
        namespace="https://example.test/fsi/2025",
        local_name="LiquidInvestmentSecuritiesCurrent",
        labels=(("standard", "Liquid investment securities"),),
        documentation="Available-for-sale debt securities classified as current.",
        value=42_500_000.0,
        unit="USD",
        period_start=None,
        period_end="2025-12-31",
        context_id="CurrentYearInstant",
        dimensions=(),
        statement_roles=("balance_sheet",),
        presentation_parents=("us-gaap:AssetsCurrent",),
        calculation_parents=("us-gaap:AssetsCurrent",),
        calculation_children=(),
        definition_parents=(),
        definition_children=(),
        source_accession="0000000000-26-000001",
    )
    assert StructuralFact.from_dict(fact.as_dict()) == fact


def test_resolution_request_rejects_empty_accession() -> None:
    with pytest.raises(ValueError, match="accession"):
        ResolutionRequest(
            normalized_concept="marketable_securities_current",
            period_end="2025-12-31",
            source_accession="",
            unit="USD",
            statement_role="balance_sheet",
            form="10-K",
        )


@pytest.mark.parametrize("field", ["labels", "dimensions"])
def test_structural_fact_rejects_nested_mutable_pairs(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        _fact(**{field: (["axis", "member"],)})


def test_parse_diagnostic_rejects_nested_mutable_context() -> None:
    with pytest.raises(ValueError, match="context"):
        ParseDiagnostic(
            code="missing_context",
            message="Context could not be resolved.",
            severity="warning",
            context=(["context_id", "CurrentYearInstant"],),  # type: ignore[arg-type]
        )


def test_structural_fact_and_diagnostic_are_hashable() -> None:
    fact = _fact()
    diagnostic = ParseDiagnostic(
        code="missing_context",
        message="Context could not be resolved.",
        severity="warning",
        context=(("context_id", "CurrentYearInstant"),),
    )

    assert isinstance(hash(fact), int)
    assert isinstance(hash(diagnostic), int)


def test_required_dates_reject_none() -> None:
    with pytest.raises(ValueError, match="period_end"):
        _fact(period_end=None)
    with pytest.raises(ValueError, match="period_end"):
        StructuralFiling(
            source_accession="0000000000-26-000001",
            period_end=None,  # type: ignore[arg-type]
            facts=(),
            diagnostics=(),
        )
    with pytest.raises(ValueError, match="period_end"):
        ResolutionRequest(
            normalized_concept="marketable_securities_current",
            period_end=None,  # type: ignore[arg-type]
            source_accession="0000000000-26-000001",
            unit="USD",
            statement_role="balance_sheet",
            form="10-K",
        )
    with pytest.raises(ValueError, match="period"):
        _decision(period=None)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_structural_fact_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="value"):
        _fact(value=value)


def test_structural_fact_rejects_integer_beyond_numeric_boundary() -> None:
    with pytest.raises(ValueError, match="value"):
        _fact(value=10**309)


def test_structural_fact_accepts_numeric_boundary_and_rejects_boundary_plus_one() -> None:
    maximum = int(sys.float_info.max)
    assert _fact(value=maximum).value == maximum
    with pytest.raises(ValueError, match="value"):
        _fact(value=maximum + 1)


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), float("-inf")])
def test_resolution_decision_rejects_non_finite_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        _decision(confidence=confidence)


def test_structural_fact_rejects_non_string_documentation() -> None:
    with pytest.raises(ValueError, match="documentation"):
        _fact(documentation=42)


def test_relationship_round_trip_preserves_governed_arc_evidence() -> None:
    fact = _fact()

    restored = StructuralFact.from_dict(fact.as_dict())

    assert restored.relationships == fact.relationships
    assert restored.relationships[0].as_dict() == {
        "arcrole": "http://www.xbrl.org/2003/arcrole/parent-child",
        "linkrole": "https://example.test/role/BalanceSheet",
        "from_concept": "us-gaap:AssetsCurrent",
        "to_concept": "fsi:LiquidInvestmentSecuritiesCurrent",
        "order": 1.0,
        "preferred_label": None,
        "calculation_weight": None,
        "statement_role": None,
    }


def test_relationship_round_trip_preserves_classified_statement_role() -> None:
    relationship = StructuralRelationship(
        arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
        linkrole="https://example.test/role/custom-1001",
        from_concept="us-gaap:RestrictedAssetsAbstract",
        to_concept="us-gaap:AssetsCurrent",
        order=1.0,
        preferred_label=None,
        calculation_weight=None,
        statement_role="balance_sheet",
    )

    assert StructuralRelationship.from_dict(relationship.as_dict()) == relationship
    assert relationship.as_dict()["statement_role"] == "balance_sheet"


@pytest.mark.parametrize("status", ["accepted", "review"])
def test_usable_decisions_require_complete_immutable_evidence(status: str) -> None:
    with pytest.raises(ValueError, match="evidence"):
        _decision(status=status, evidence=None)


def test_evidence_accepts_structural_statement_support_without_classified_role() -> None:
    fact = _fact(
        statement_roles=(),
        presentation_parents=("us-gaap:DebtInstrumentLineItems",),
    )
    evidence = ResolutionEvidence.from_fact(
        fact,
        mapping_version="US-XBRL-RESOLVER-1.1",
        confidence=1.0,
        reason_codes=("EXACT_CONFIGURED_CONCEPT", "STRUCTURAL_STATEMENT_SUPPORT"),
    )

    evidence.validate_complete()


def test_evidence_without_roles_or_structural_statement_support_is_incomplete() -> None:
    fact = _fact(
        statement_roles=(),
        presentation_parents=(),
        calculation_parents=(),
        presentation_ancestry=(),
        relationships=(),
    )
    evidence = ResolutionEvidence.from_fact(
        fact,
        mapping_version="US-XBRL-RESOLVER-1.1",
        confidence=1.0,
        reason_codes=("EXACT_CONFIGURED_CONCEPT",),
    )

    with pytest.raises(
        ValueError, match="accepted/review decisions require complete evidence"
    ):
        evidence.validate_complete()


def test_decision_snapshot_contains_full_accounting_provenance() -> None:
    payload = _decision().as_dict()

    assert payload["form"] == "10-K"
    assert payload["evidence"] == {
        **_fact().as_dict(),
        "mapping_version": "US-XBRL-RESOLVER-1.1",
        "confidence": 0.95,
        "reason_codes": ["balance_sheet_role"],
    }


@pytest.mark.parametrize("form", ["10-K", "10-K/A", "10-Q", "10-Q/A"])
def test_resolution_request_accepts_only_governed_filing_forms(form: str) -> None:
    request = ResolutionRequest(
        normalized_concept="marketable_securities_current",
        period_end="2025-12-31",
        source_accession="0000000000-26-000001",
        unit="USD",
        statement_role="balance_sheet",
        form=form,
    )

    assert request.form == form
