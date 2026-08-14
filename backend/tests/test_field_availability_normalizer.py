import json
from pathlib import Path
from typing import Any

from app.us_valuation.classification import classify_issuer
from app.us_valuation.field_availability import availability_from_normalized_field
from app.us_valuation.xbrl import CompanyFactsNormalizer


FIXTURES = Path(__file__).parent / "fixtures" / "us"


def load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def filing_records(submission: dict[str, Any]) -> list[dict[str, Any]]:
    recent = submission["filings"]["recent"]
    return [
        {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(len(recent["accessionNumber"]))
    ]


def test_reported_fact_maps_to_current_reported_availability() -> None:
    item = availability_from_normalized_field(
        field="cash",
        value=125.0,
        source={
            "accession": "0000000000-26-000001",
            "value_status": "reported",
        },
        legacy_state="reported",
        period_end="2026-06-30",
    )
    assert item.state == "reported"
    assert item.value == 125.0
    assert item.source_accession == "0000000000-26-000001"


def test_policy_verified_zero_maps_to_evidence_backed_zero() -> None:
    item = availability_from_normalized_field(
        field="preferred_equity",
        value=0.0,
        source={
            "source_accession": "0000000000-26-000001",
            "value_status": "policy_verified_zero",
            "verification_version": "US-BRIDGE-FILING-1.0",
        },
        legacy_state="policy_verified_zero",
        period_end="2026-06-30",
    )
    assert item.state == "evidence_backed_zero"
    assert item.value == 0.0


def test_stale_fact_keeps_diagnostic_source_but_nulls_point_value() -> None:
    item = availability_from_normalized_field(
        field="commercial_paper",
        value=None,
        source={
            "accession": "0000000000-25-000001",
            "value_status": "stale_reported_fact",
            "value": 500.0,
        },
        legacy_state="verification_stale",
        period_end="2026-06-30",
    )
    assert item.state == "stale"
    assert item.value is None
    assert item.freshness == "stale"


def test_missing_fact_stays_unresolved_without_a_source() -> None:
    item = availability_from_normalized_field(
        field="noncontrolling_interests",
        value=None,
        source=None,
        legacy_state="missing",
        period_end="2026-06-30",
    )
    assert item.state == "unresolved"
    assert item.value is None


def test_governed_reported_zero_maps_to_explicit_zero_with_preferred_accession() -> None:
    item = availability_from_normalized_field(
        field="commercial_paper",
        value=0.0,
        source={
            "source_accession": "0000000000-26-000001",
            "accession": "0000000000-25-000001",
            "source_kind": "filing_note",
            "evidence_class": "reported_zero",
            "value_status": "governed_filing_fact",
            "rationale": "This free-form explanation must not become a reason code.",
        },
        legacy_state="governed_filing_fact",
        period_end="2026-06-30",
    )
    assert item.state == "explicit_zero"
    assert item.source_accession == "0000000000-26-000001"
    assert item.source_kind == "filing_note"
    assert item.evidence_class == "reported_zero"
    assert item.reason_code == "EXPLICIT_ZERO_REPORTED_ZERO"


def test_other_governed_zero_maps_to_evidence_backed_zero() -> None:
    item = availability_from_normalized_field(
        field="preferred_equity",
        value=0.0,
        source={
            "source_accession": "0000000000-26-000001",
            "evidence_class": "complete_presentation_zero",
            "value_status": "governed_filing_fact",
        },
        legacy_state="governed_filing_fact",
        period_end="2026-06-30",
    )
    assert item.state == "evidence_backed_zero"


def test_weighted_average_diluted_fallback_maps_to_proxy() -> None:
    item = availability_from_normalized_field(
        field="common_shares_outstanding",
        value=1_000.0,
        source={
            "accession": "0000000000-26-000001",
            "value_status": "weighted_average_diluted_proxy",
        },
        legacy_state="weighted_average_diluted_proxy",
        period_end="2026-06-30",
    )
    assert item.state == "proxy"
    assert item.value == 1_000.0


def test_normalizer_emits_availability_without_changing_legacy_bridge_fields() -> None:
    submission = load_json("msft-submissions.json")
    classification = classify_issuer(submission)
    financials = CompanyFactsNormalizer(
        load_json("msft-companyfacts.json"),
        fiscal_year_end=submission["fiscalYearEnd"],
        filing_records=filing_records(submission),
    ).normalize(
        annual_count=5,
        verified_zero_bridge_fields=classification["verified_zero_bridge_fields"],
        governed_bridge_fields=classification["governed_bridge_fields"],
    )
    balance = financials["balance_sheet"]
    assert balance["availability"]["cash"]["state"] == "reported"
    assert balance["availability"]["preferred_equity"]["value"] == 0.0
    assert balance["values"]["cash"] == balance["availability"]["cash"]["value"]
    assert "bridge_complete" in balance
    assert "bridge_missing_fields" in balance
