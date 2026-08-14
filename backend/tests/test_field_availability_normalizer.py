import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

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
        reference_date="2026-06-30",
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
        reference_date="2026-06-30",
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
        reference_date="2026-06-30",
    )
    assert item.state == "stale"
    assert item.value is None
    assert item.freshness == "stale"


def _reduced_annual_bridge_fixture(
    *, form: str = "10-K"
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    submission = load_json("msft-submissions.json")
    companyfacts = deepcopy(load_json("msft-companyfacts.json"))
    companyfacts["facts"]["us-gaap"]["FinanceLeaseLiabilityNoncurrent"] = {
        "label": "Finance lease liability, noncurrent",
        "description": "Noncurrent finance lease liability.",
        "units": {
            "USD": [
                {
                    "val": 25,
                    "accn": "0000000000-24-000001",
                    "fy": 2024,
                    "fp": "FY",
                    "form": form,
                    "filed": "2024-08-01",
                    "frame": "CY2024I",
                    "end": "2024-06-30",
                }
            ]
        },
    }
    return companyfacts, filing_records(submission)


def test_normalizer_carries_forward_annual_fact_at_exact_365_day_boundary() -> None:
    companyfacts, submissions = _reduced_annual_bridge_fixture()
    financials = CompanyFactsNormalizer(
        companyfacts,
        fiscal_year_end="0630",
        as_of_date="2025-06-30",
        filing_records=submissions,
    ).normalize()

    availability = financials["balance_sheet"]["availability"]

    assert availability["finance_lease_noncurrent"]["value"] == 25.0
    assert availability["finance_lease_noncurrent"]["freshness"] == (
        "carried_forward"
    )
    assert availability["finance_lease_noncurrent"]["fallback_level"] == (
        "annual_carried_forward"
    )
    assert availability["finance_lease_noncurrent"]["source_age_days"] == 365
    assert availability["finance_lease_noncurrent"]["source_accession"] == (
        "0000000000-24-000001"
    )
    assert availability["finance_lease_noncurrent"]["source_kind"] == "companyfacts"
    assert availability["finance_lease_noncurrent"]["authority"] == "production"
    assert availability["finance_lease_noncurrent"]["evidence_class"] == "reported"
    assert financials["balance_sheet"]["sources"]["finance_lease_noncurrent"][
        "form"
    ] == "10-K"
    assert financials["balance_sheet"]["sources"]["finance_lease_noncurrent"][
        "end"
    ] == "2024-06-30"
    assert financials["balance_sheet"]["sources"]["finance_lease_noncurrent"][
        "filed"
    ] == "2024-08-01"


@pytest.mark.parametrize(
    "form,expected_freshness",
    [("10-K/A", "carried_forward"), ("10-Q", "stale")],
)
def test_normalizer_requires_annual_companyfacts_form(
    form: str, expected_freshness: str
) -> None:
    companyfacts, submissions = _reduced_annual_bridge_fixture(form=form)
    financials = CompanyFactsNormalizer(
        companyfacts,
        fiscal_year_end="0630",
        as_of_date="2025-06-30",
        filing_records=submissions,
    ).normalize()

    item = financials["balance_sheet"]["availability"]["finance_lease_noncurrent"]

    assert item["freshness"] == expected_freshness


def test_normalizer_rejects_annual_fact_one_day_beyond_365_day_boundary() -> None:
    companyfacts, submissions = _reduced_annual_bridge_fixture()
    financials = CompanyFactsNormalizer(
        companyfacts,
        fiscal_year_end="0630",
        as_of_date="2025-07-01",
        filing_records=submissions,
    ).normalize()

    item = financials["balance_sheet"]["availability"]["finance_lease_noncurrent"]

    assert item["state"] == "stale"
    assert item["value"] is None
    assert item["freshness"] == "stale"
    assert item["source_accession"] == "0000000000-24-000001"


def _stale_companyfacts_source(**overrides: object) -> dict[str, object]:
    source: dict[str, object] = {
        "value": 25.0,
        "end": "2025-06-30",
        "form": "10-K",
        "accession": "0000000000-25-000001",
        "source_kind": "companyfacts",
        "authority": "production",
        "evidence_class": "reported",
    }
    source.update(overrides)
    return source


@pytest.mark.parametrize(
    "overrides,expected_freshness",
    [
        ({"form": "10-K/A"}, "carried_forward"),
        ({"form": "10-Q"}, "stale"),
        ({"evidence_class": "conflict"}, "stale"),
        ({"end": "2026-07-01"}, "stale"),
        ({"authority": "shadow"}, "stale"),
        ({"authority": None}, "stale"),
    ],
)
def test_companyfacts_annual_recovery_requires_explicit_trustworthy_metadata(
    overrides: dict[str, object], expected_freshness: str
) -> None:
    item = availability_from_normalized_field(
        field="finance_lease_noncurrent",
        value=None,
        source=_stale_companyfacts_source(**overrides),
        legacy_state="verification_stale",
        period_end="2026-06-30",
        reference_date="2026-06-30",
    )

    assert item.freshness == expected_freshness
    if expected_freshness == "carried_forward":
        assert item.authority == "production"
        assert item.evidence_class == "reported"
    else:
        assert item.value is None


def test_companyfacts_annual_recovery_rejects_missing_authority() -> None:
    source = _stale_companyfacts_source()
    del source["authority"]

    item = availability_from_normalized_field(
        field="finance_lease_noncurrent",
        value=None,
        source=source,
        legacy_state="verification_stale",
        period_end="2026-06-30",
        reference_date="2026-06-30",
    )

    assert item.freshness == "stale"
    assert item.value is None


def test_missing_fact_stays_unresolved_without_a_source() -> None:
    item = availability_from_normalized_field(
        field="noncontrolling_interests",
        value=None,
        source=None,
        legacy_state="missing",
        period_end="2026-06-30",
        reference_date="2026-06-30",
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
        reference_date="2026-06-30",
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
        reference_date="2026-06-30",
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
        reference_date="2026-06-30",
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
