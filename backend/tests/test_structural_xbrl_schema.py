from __future__ import annotations

import pytest

from app.us_valuation.structural_xbrl import (
    ResolutionDecision,
    ResolutionRequest,
    StructuralFact,
    StructuralFiling,
)


def test_structural_fact_round_trip_preserves_provenance() -> None:
    fact = StructuralFact(
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
