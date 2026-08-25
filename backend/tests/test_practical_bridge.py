"""Contract tests for source-derived practical bridge ranges."""

import pytest

from app.us_valuation.bridge_evidence_merge import merge_bridge_evidence
from app.us_valuation.field_availability import FieldAvailability
from app.us_valuation.practical_bridge import bounded_claim, reported_aggregate


def _unresolved(field: str) -> FieldAvailability:
    return FieldAvailability(
        field=field,
        value=None,
        state="unresolved",
        reason_code="NO_CURRENT_CANDIDATE",
        period_end="2026-06-30",
        source_accession=None,
        source_kind=None,
        evidence_class=None,
        freshness="unknown",
    )


def test_missing_claim_becomes_range_not_zero() -> None:
    claim = bounded_claim(
        field="noncontrolling_interests",
        upper_bound=100.0,
        source_accession="0000000001-26-000001",
        period_end="2026-06-30",
        source_concept="us-gaap:StockholdersEquity",
        context_id="current",
        basis="Joint same-filing equity upper bound.",
    )
    merged = merge_bridge_evidence(
        {"noncontrolling_interests": _unresolved("noncontrolling_interests")},
        (claim,),
    )

    result = merged.availability["noncontrolling_interests"]
    assert result.value is None
    assert result.state == "bounded_unresolved"
    assert result.uncertainty.low == 0.0
    assert result.uncertainty.high == 100.0


def test_reported_total_has_exact_coverage_and_cannot_hide_bad_range() -> None:
    total = reported_aggregate(
        field="marketable_securities_total",
        low=11.0,
        high=11.0,
        source_accession="0000000001-26-000001",
        period_end="2026-06-30",
        source_concept="us-gaap:AvailableForSaleSecuritiesDebtSecurities",
        context_id="current",
        covered_fields=(
            "marketable_securities_current",
            "marketable_securities_noncurrent",
        ),
        economic_scope="marketable_securities_current_and_noncurrent",
        basis="Direct same-filing total.",
    )
    assert total.value == 11.0
    assert total.coverage_basis == "direct_issuer_total"
    assert total.covered_fields == (
        "marketable_securities_current",
        "marketable_securities_noncurrent",
    )
    with pytest.raises(ValueError, match="aggregate range"):
        reported_aggregate(
            field="total_interest_bearing_debt",
            low=12.0,
            high=11.0,
            source_accession="0000000001-26-000001",
            period_end="2026-06-30",
            source_concept="us-gaap:Liabilities",
            context_id="current",
            covered_fields=("current_debt", "noncurrent_debt"),
            economic_scope="debt",
            basis="Invalid.",
        )
