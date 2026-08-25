"""Contracts for private, source-linked official-evidence records."""

from __future__ import annotations

import pytest

from app.us_valuation.official_evidence import (
    EvidenceCandidate,
    EvidenceDecision,
    EvidenceRequest,
)


def _request() -> EvidenceRequest:
    return EvidenceRequest(
        required_field="noncurrent_debt",
        model="fcff_dcf",
        period_role="balance_sheet_snapshot",
        materiality="material",
    )


def _candidate(*, value: float = 125.0, filed_date: str = "2026-08-10") -> EvidenceCandidate:
    return EvidenceCandidate(
        field="noncurrent_debt",
        value=value,
        tag="us-gaap:LongTermDebtNoncurrent",
        dimensions=(),
        unit="USD",
        period_end="2026-06-30",
        accession="0000123456-26-000001",
        filed_date=filed_date,
        source_url="https://www.sec.gov/Archives/edgar/data/123456/filing.htm",
        extraction_method="arelle_inline_xbrl",
        cik="0000123456",
        entity_identifier="0000123456",
        entity_scheme="http://www.sec.gov/CIK",
        consolidation_scope="consolidated_parent",
    )


def test_evidence_records_round_trip_without_losing_private_provenance() -> None:
    request = _request()
    candidate = _candidate()
    decision = EvidenceDecision(
        request=request,
        selected=candidate,
        selected_range=None,
        rejected_candidates=(),
        status="reported",
        completeness_proof=("companyfacts_checked", "controlling_filing_parsed"),
        reason_codes=("EXACT_CONTROLLING_FILING_FACT",),
    )

    assert EvidenceRequest.from_dict(request.as_dict()) == request
    assert EvidenceCandidate.from_dict(candidate.as_dict()) == candidate
    assert EvidenceDecision.from_dict(decision.as_dict()) == decision


def test_evidence_candidate_rejects_bad_cutoff_or_identity() -> None:
    with pytest.raises(ValueError, match="accession"):
        EvidenceCandidate(
            field="cash",
            value=1.0,
            tag="us-gaap:CashAndCashEquivalentsAtCarryingValue",
            dimensions=(),
            unit="USD",
            period_end="2026-06-30",
            accession="not-an-accession",
            filed_date="2026-08-10",
            source_url="https://www.sec.gov/Archives/edgar/data/123456/filing.htm",
            extraction_method="arelle_inline_xbrl",
            cik="0000123456",
            entity_identifier="0000123456",
            entity_scheme="http://www.sec.gov/CIK",
            consolidation_scope="consolidated_parent",
        )


def test_decision_rejects_a_candidate_filed_after_valuation_cutoff() -> None:
    with pytest.raises(ValueError, match="cutoff|filed"):
        EvidenceDecision(
            request=_request(),
            selected=_candidate(filed_date="2026-08-15"),
            selected_range=None,
            rejected_candidates=(),
            status="reported",
            completeness_proof=("controlling_filing_parsed",),
            reason_codes=("EXACT_CONTROLLING_FILING_FACT",),
            valuation_date="2026-08-14",
        )


def test_package_failure_is_an_explicit_decision_not_silent_missingness() -> None:
    decision = EvidenceDecision(
        request=_request(),
        selected=None,
        selected_range=None,
        rejected_candidates=(),
        status="unresolved",
        completeness_proof=("companyfacts_checked", "package_capture_failed"),
        reason_codes=("OFFICIAL_FILING_PACKAGE_FAILURE", "XBRL_PACKAGE_INCOMPLETE"),
        package_failure={
            "code": "XBRL_PACKAGE_INCOMPLETE",
            "accession": "0000123456-26-000001",
            "detail": "locally referenced resource is unavailable: extension.xsd",
        },
    )

    assert decision.package_failure["code"] == "XBRL_PACKAGE_INCOMPLETE"
    assert EvidenceDecision.from_dict(decision.as_dict()) == decision


def test_decision_retains_rejected_candidates_alongside_the_selected_fact() -> None:
    rejected = _candidate(value=100.0)
    selected = _candidate(value=125.0)
    decision = EvidenceDecision(
        request=_request(),
        selected=selected,
        selected_range=None,
        rejected_candidates=(
            {
                "candidate": rejected.as_dict(),
                "reason_codes": ("DIMENSIONED_NONCONSOLIDATED_FACT",),
            },
        ),
        status="reported",
        completeness_proof=("companyfacts_checked", "controlling_filing_parsed"),
        reason_codes=("EXACT_CONTROLLING_FILING_FACT",),
    )

    assert decision.selected == selected
    assert decision.rejected_candidates[0]["candidate"]["value"] == 100.0
    assert decision.rejected_candidates[0]["reason_codes"] == (
        "DIMENSIONED_NONCONSOLIDATED_FACT",
    )


def test_selected_evidence_requires_exact_parent_identity_and_consolidation() -> None:
    payload = _candidate().as_dict()
    payload["consolidation_scope"] = "subsidiary"
    with pytest.raises(ValueError, match="parent identity|consolidation"):
        EvidenceDecision(
            request=_request(),
            selected=EvidenceCandidate.from_dict(payload),
            selected_range=None,
            rejected_candidates=(),
            status="reported",
            completeness_proof=("controlling_filing_parsed",),
            reason_codes=("EXACT_CONTROLLING_FILING_FACT",),
        )


def test_reported_aggregate_requires_explicit_nonoverlap_coverage() -> None:
    with pytest.raises(ValueError, match="aggregate coverage"):
        EvidenceDecision(
            request=_request(),
            selected=_candidate(),
            selected_range=None,
            rejected_candidates=(),
            status="reported_aggregate",
            completeness_proof=("controlling_filing_parsed",),
            reason_codes=("REPORTED_AGGREGATE",),
        )


def test_nonpoint_outcomes_and_bounded_ranges_never_synthesize_a_point_value() -> None:
    for status, proof in (
        ("not_disclosed", ("search_complete",)),
        ("stale", ("companyfacts_checked",)),
        ("conflicting", ("official_sources_checked",)),
        ("unresolved", ("official_sources_checked",)),
    ):
        decision = EvidenceDecision(
            request=_request(),
            selected=None,
            selected_range=None,
            rejected_candidates=(),
            status=status,
            completeness_proof=proof,
            reason_codes=(status.upper(),),
        )
        assert decision.selected_value is None

    bounded = EvidenceDecision(
        request=_request(),
        selected=None,
        selected_range=(100.0, 125.0),
        rejected_candidates=(),
        status="bounded_estimate",
        completeness_proof=("source_range_checked",),
        reason_codes=("SOURCE_BACKED_RANGE",),
        range_provenance=("issuer_history:0000123456",),
    )
    assert bounded.selected_value is None
    assert bounded.selected_range == (100.0, 125.0)
