"""Exact-fingerprint tests for Batch 01 structural promotion."""

from dataclasses import replace

import pytest

from app.us_valuation.structural_promotion import (
    StructuralPromotionError,
    promote_structural_decision,
    resolution_decision_from_dict,
)
from app.us_valuation.structural_xbrl import (
    ResolutionDecision,
    ResolutionEvidence,
    StructuralFact,
    StructuralRelationship,
)


def _decision() -> ResolutionDecision:
    fact = StructuralFact(
        qname="us-gaap:FinanceLeaseLiability",
        namespace="http://fasb.org/us-gaap/2025",
        local_name="FinanceLeaseLiability",
        labels=(("standard", "Finance Lease, Liability"),),
        documentation=None,
        value=664_000_000,
        unit="USD",
        period_start=None,
        period_end="2026-04-30",
        context_id="c-3",
        dimensions=(),
        statement_roles=(),
        presentation_parents=("us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",),
        calculation_parents=(),
        calculation_children=(),
        definition_parents=(),
        definition_children=(),
        source_accession="0001108524-26-000127",
        decimals="-6",
        scale="6",
        sign=None,
        filing_form="10-Q",
        filing_metadata=(
            ("primary_document", "crm-20260430.htm"),
            ("filed", "2026-05-28"),
        ),
        presentation_ancestry=(
            "us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",
        ),
        relationships=(
            StructuralRelationship(
                arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                linkrole="http://salesforce.com/role/Leases",
                from_concept="us-gaap:FinanceLeaseLiabilitiesPaymentsDueAbstract",
                to_concept="us-gaap:FinanceLeaseLiability",
                order=1.0,
                preferred_label=None,
                calculation_weight=None,
            ),
        ),
    )
    evidence = ResolutionEvidence.from_fact(
        fact,
        mapping_version="US-XBRL-RESOLVER-1.1",
        confidence=1.0,
        reason_codes=(
            "EXACT_CONFIGURED_CONCEPT",
            "STRUCTURAL_STATEMENT_SUPPORT",
        ),
    )
    return ResolutionDecision(
        status="accepted",
        normalized_concept="finance_lease_total",
        source_concept=fact.qname,
        value=fact.value,
        unit=fact.unit,
        period=fact.period_end,
        source_accession=fact.source_accession,
        confidence=1.0,
        mapping_method="exact_configured_concept",
        reason_codes=evidence.reason_codes,
        form="10-Q",
        evidence=evidence,
    )


def _promote(decision: ResolutionDecision, **overrides: str):
    arguments = {
        "ticker": "CRM",
        "cik": "0001108524",
        "filing_date": "2026-05-28",
        "valuation_date": "2026-08-14",
    }
    arguments.update(overrides)
    return promote_structural_decision(decision, **arguments)


def test_exact_reviewed_structural_decision_promotes_to_production() -> None:
    promoted = _promote(_decision())

    assert promoted.field == "finance_lease_total"
    assert promoted.value == 664_000_000
    assert promoted.authority == "production"
    assert promoted.fallback_level == "current_structural"
    assert promoted.source_accession == "0001108524-26-000127"
    assert promoted.covered_fields == (
        "finance_lease_current",
        "finance_lease_noncurrent",
    )
    assert promoted.coverage_basis == "direct_issuer_total"
    assert promoted.economic_scope == "finance_lease_current_and_noncurrent"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ticker", "OTHER"),
        ("cik", "0000000001"),
        ("filing_date", "2026-05-29"),
    ],
)
def test_promotion_rejects_context_fingerprint_drift(field: str, value: str) -> None:
    with pytest.raises(StructuralPromotionError, match="exact reviewed fingerprint"):
        _promote(_decision(), **{field: value})


def test_promotion_rejects_decision_drift_nonaccepted_and_future_filing() -> None:
    decision = _decision()
    changed_evidence = replace(decision.evidence, confidence=0.99)
    with pytest.raises(StructuralPromotionError, match="exact reviewed fingerprint"):
        _promote(
            replace(
                decision,
                confidence=0.99,
                evidence=changed_evidence,
            )
        )
    with pytest.raises(StructuralPromotionError, match="only accepted"):
        _promote(replace(_decision(), status="review"))
    with pytest.raises(StructuralPromotionError, match="future-filed"):
        _promote(_decision(), filing_date="2026-08-15")


def test_private_report_decision_round_trips_before_promotion() -> None:
    decision = _decision()
    restored = resolution_decision_from_dict(decision.as_dict())

    assert restored == decision
    assert _promote(restored).value == 664_000_000
