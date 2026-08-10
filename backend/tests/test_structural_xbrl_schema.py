from __future__ import annotations

import pytest

from app.us_valuation.structural_xbrl import (
    ParseDiagnostic,
    ResolutionDecision,
    ResolutionRequest,
    StructuralFact,
    StructuralFiling,
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
    }
    values.update(overrides)
    return StructuralFact(**values)  # type: ignore[arg-type]


def _decision(**overrides: object) -> ResolutionDecision:
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


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), float("-inf")])
def test_resolution_decision_rejects_non_finite_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        _decision(confidence=confidence)


def test_structural_fact_rejects_non_string_documentation() -> None:
    with pytest.raises(ValueError, match="documentation"):
        _fact(documentation=42)
