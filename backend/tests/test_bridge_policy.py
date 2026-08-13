from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

import pytest

from app.us_valuation.bridge_policy import (
    BridgeRange,
    BridgeResolution,
    reconcile_bridge,
)
from app.us_valuation.classification import classify_issuer
from app.us_valuation.field_availability import (
    FieldAvailability,
    UncertaintyRange,
)
from app.us_valuation.xbrl import CompanyFactsNormalizer


ACCESSION = "0000000000-26-000001"
PERIOD_END = "2026-06-30"
FIXTURES = Path(__file__).parent / "fixtures" / "us"
DEBT_COMPONENTS = (
    "commercial_paper",
    "current_debt",
    "finance_lease_current",
    "finance_lease_noncurrent",
    "noncurrent_debt",
)
LEASE_COMPONENTS = ("finance_lease_current", "finance_lease_noncurrent")


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


def point(
    field: str,
    value: float,
    *,
    authority: str = "production",
    covered_fields: tuple[str, ...] = (),
) -> FieldAvailability:
    zero_state = "explicit_zero" if value == 0 else "reported"
    return FieldAvailability(
        field=field,
        value=value,
        state=zero_state,
        reason_code="TEST_REPORTED_ZERO" if value == 0 else "TEST_REPORTED",
        period_end=PERIOD_END,
        source_accession=ACCESSION,
        source_kind="test_filing",
        evidence_class="reported_zero" if value == 0 else "reported",
        freshness="current",
        covered_fields=covered_fields,
        authority=authority,
    )


def unresolved(field: str) -> FieldAvailability:
    return FieldAvailability(
        field=field,
        value=None,
        state="unresolved",
        reason_code="NO_CURRENT_CANDIDATE",
        period_end=PERIOD_END,
        source_accession=None,
        source_kind=None,
        evidence_class=None,
        freshness="unknown",
    )


def unavailable(field: str, state: str) -> FieldAvailability:
    return FieldAvailability(
        field=field,
        value=None,
        state=state,
        reason_code=f"TEST_{state.upper()}",
        period_end=PERIOD_END,
        source_accession=ACCESSION if state in {"stale", "conflict"} else None,
        source_kind="test_filing" if state in {"stale", "conflict"} else None,
        evidence_class=state if state in {"stale", "conflict"} else None,
        freshness="stale" if state == "stale" else "unknown",
    )


def bounded(
    field: str,
    low: float,
    high: float,
    *,
    covered_fields: tuple[str, ...] = (),
) -> FieldAvailability:
    return FieldAvailability(
        field=field,
        value=None,
        state="bounded_unresolved",
        reason_code="CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
        period_end=PERIOD_END,
        source_accession=ACCESSION,
        source_kind="test_filing_note",
        evidence_class="reported_range",
        freshness="current",
        uncertainty=UncertaintyRange(
            low=low,
            high=high,
            basis="Hand-checked current filing range.",
            source_accessions=(ACCESSION,),
        ),
        covered_fields=covered_fields,
    )


def complete_availability(
    **overrides: float | None,
) -> dict[str, FieldAvailability]:
    values: dict[str, float | None] = {
        "cash": 100.0,
        "marketable_securities_current": 20.0,
        "marketable_securities_noncurrent": 5.0,
        "commercial_paper": 0.0,
        "current_debt": 10.0,
        "noncurrent_debt": 40.0,
        "finance_lease_current": 2.0,
        "finance_lease_noncurrent": 8.0,
        "finance_lease_total": None,
        "preferred_equity": 0.0,
        "noncontrolling_interests": 1.0,
    }
    values.update(overrides)
    return {
        field: point(
            field,
            value,
            covered_fields=LEASE_COMPONENTS if field == "finance_lease_total" else (),
        )
        if value is not None
        else unresolved(field)
        for field, value in values.items()
    }


def with_total_debt(
    availability: dict[str, FieldAvailability],
    value: float,
    *,
    covered_fields: tuple[str, ...] = DEBT_COMPONENTS,
) -> dict[str, FieldAvailability]:
    availability["total_interest_bearing_debt"] = point(
        "total_interest_bearing_debt",
        value,
        covered_fields=covered_fields,
    )
    return availability


def test_complete_bridge_reconciles_point_values() -> None:
    resolution = reconcile_bridge(
        complete_availability(
            cash=100.0,
            marketable_securities_current=20.0,
            marketable_securities_noncurrent=5.0,
            commercial_paper=0.0,
            current_debt=10.0,
            noncurrent_debt=40.0,
            finance_lease_current=2.0,
            finance_lease_noncurrent=8.0,
            preferred_equity=0.0,
            noncontrolling_interests=1.0,
        ),
        fully_diluted_shares=10.0,
    )

    assert resolution.complete is True
    assert resolution.can_value is True
    assert resolution.cash_and_investments.midpoint == 125.0
    assert resolution.total_debt.midpoint == 60.0
    assert resolution.bridge_adjustment.midpoint == 64.0


def test_real_msft_normalizer_availability_reconciles_complete_bridge() -> None:
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
    availability = {
        field: FieldAvailability.from_dict(payload)
        for field, payload in balance["availability"].items()
    }

    resolution = reconcile_bridge(
        availability,
        fully_diluted_shares=balance["fully_diluted_shares_proxy"],
    )

    assert balance["bridge_complete"] is True
    assert balance["bridge_missing_fields"] == []
    assert resolution.complete is True
    assert resolution.can_value is True
    assert resolution.blocking_fields == ()
    assert resolution.cash_and_investments == BridgeRange(
        low=95_653_000_000.0,
        midpoint=95_653_000_000.0,
        high=95_653_000_000.0,
    )
    assert resolution.total_debt == BridgeRange(
        low=42_881_000_000.0,
        midpoint=42_881_000_000.0,
        high=42_881_000_000.0,
    )
    assert resolution.bridge_adjustment.midpoint == 52_772_000_000.0


def test_aggregate_finance_lease_replaces_missing_splits_once() -> None:
    availability = complete_availability(
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=10.0,
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.total_debt.midpoint == 60.0
    assert "finance_lease_current" not in resolution.blocking_fields
    assert "finance_lease_noncurrent" not in resolution.blocking_fields


def test_matching_lease_total_and_splits_are_counted_once() -> None:
    availability = complete_availability(
        finance_lease_current=2.0,
        finance_lease_noncurrent=8.0,
        finance_lease_total=10.0,
    )

    assert reconcile_bridge(
        availability,
        fully_diluted_shares=10.0,
    ).total_debt.midpoint == 60.0


def test_one_split_plus_lease_total_counts_only_the_total() -> None:
    availability = complete_availability(
        finance_lease_current=3.0,
        finance_lease_noncurrent=None,
        finance_lease_total=10.0,
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.total_debt == BridgeRange(low=60.0, midpoint=60.0, high=60.0)
    assert resolution.complete is True
    assert resolution.blocking_fields == ()


def test_one_split_above_lease_total_high_endpoint_conflicts() -> None:
    availability = complete_availability(
        finance_lease_current=11.0,
        finance_lease_noncurrent=None,
        finance_lease_total=None,
    )
    availability["finance_lease_total"] = bounded(
        "finance_lease_total",
        8.0,
        9.0,
        covered_fields=LEASE_COMPONENTS,
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert "FINANCE_LEASE_AGGREGATE_CONFLICT" in resolution.reason_codes


def test_bounded_split_low_above_lease_total_high_endpoint_conflicts() -> None:
    availability = complete_availability(
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=9.0,
    )
    availability["finance_lease_current"] = bounded(
        "finance_lease_current",
        11.0,
        12.0,
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert "FINANCE_LEASE_AGGREGATE_CONFLICT" in resolution.reason_codes


def test_lease_total_corroboration_uses_the_inclusive_one_dollar_tolerance() -> None:
    availability = complete_availability(
        finance_lease_current=2.0,
        finance_lease_noncurrent=8.0,
        finance_lease_total=11.0,
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is True
    assert resolution.total_debt.midpoint == 61.0


def test_governed_total_debt_aggregate_covers_missing_components() -> None:
    availability = complete_availability(
        commercial_paper=None,
        current_debt=None,
        noncurrent_debt=None,
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=None,
    )
    with_total_debt(availability, 60.0)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.total_debt.midpoint == 60.0
    assert resolution.blocking_fields == ()


def test_total_debt_plus_lease_total_are_not_double_counted() -> None:
    availability = complete_availability(
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=10.0,
    )
    with_total_debt(availability, 60.0)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.total_debt.midpoint == 60.0
    assert resolution.blocking_fields == ()


def test_total_debt_aggregate_corroboration_uses_the_inclusive_tolerance() -> None:
    availability = with_total_debt(complete_availability(), 61.0)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is True
    assert resolution.total_debt.midpoint == 61.0


def test_unresolved_commercial_paper_blocks_when_no_aggregate_covers_it() -> None:
    availability = complete_availability(commercial_paper=None)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.complete is False
    assert resolution.can_value is False
    assert resolution.blocking_fields == ("commercial_paper",)


def test_conflicting_lease_total_and_splits_fail_closed() -> None:
    availability = complete_availability(
        finance_lease_current=2.0,
        finance_lease_noncurrent=8.0,
        finance_lease_total=25.0,
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert "FINANCE_LEASE_AGGREGATE_CONFLICT" in resolution.reason_codes


def test_lease_total_does_not_cover_a_conflicting_split() -> None:
    availability = complete_availability(
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=10.0,
    )
    availability["finance_lease_current"] = unavailable(
        "finance_lease_current",
        "conflict",
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert resolution.blocking_fields == ("finance_lease_current",)
    assert "TEST_CONFLICT" in resolution.reason_codes


def test_conflicting_total_debt_aggregate_and_components_fail_closed() -> None:
    availability = with_total_debt(complete_availability(), 75.0)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert "TOTAL_DEBT_AGGREGATE_CONFLICT" in resolution.reason_codes


def test_total_debt_aggregate_does_not_cover_a_conflicting_component() -> None:
    availability = with_total_debt(complete_availability(), 60.0)
    availability["current_debt"] = unavailable("current_debt", "conflict")

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert resolution.blocking_fields == ("current_debt",)
    assert "TEST_CONFLICT" in resolution.reason_codes


def test_total_debt_aggregate_requires_explicit_complete_component_coverage() -> None:
    availability = with_total_debt(
        complete_availability(),
        60.0,
        covered_fields=("current_debt", "noncurrent_debt"),
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert resolution.blocking_fields == ("total_interest_bearing_debt",)
    assert "TOTAL_DEBT_AGGREGATE_INCOMPLETE_COVERAGE" in resolution.reason_codes


def test_lease_aggregate_requires_explicit_split_coverage() -> None:
    availability = complete_availability(
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=None,
    )
    availability["finance_lease_total"] = point("finance_lease_total", 10.0)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert "finance_lease_total" in resolution.blocking_fields
    assert "FINANCE_LEASE_AGGREGATE_INCOMPLETE_COVERAGE" in resolution.reason_codes


def test_shadow_fact_is_not_usable_bridge_evidence() -> None:
    availability = complete_availability()
    availability["marketable_securities_noncurrent"] = point(
        "marketable_securities_noncurrent",
        5.0,
        authority="shadow",
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert resolution.blocking_fields == ("marketable_securities_noncurrent",)


@pytest.mark.parametrize("freshness", ["stale", "unknown"])
@pytest.mark.parametrize("state", ["reported", "proxy"])
def test_stale_or_unknown_point_and_proxy_records_are_blockers(
    state: str,
    freshness: str,
) -> None:
    availability = complete_availability()
    availability["current_debt"] = replace(
        point("current_debt", 10.0),
        state=state,
        reason_code=f"TEST_{state.upper()}",
        evidence_class=state,
        freshness=freshness,
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert resolution.blocking_fields == ("current_debt",)


@pytest.mark.parametrize("optional_source_field", ["source_kind", "evidence_class"])
def test_ordinary_bridge_records_allow_optional_source_metadata(
    optional_source_field: str,
) -> None:
    availability = complete_availability()
    availability["current_debt"] = replace(
        point("current_debt", 10.0),
        **{optional_source_field: None},
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.complete is True
    assert resolution.can_value is True
    assert resolution.blocking_fields == ()


def test_finance_lease_total_allows_optional_source_metadata() -> None:
    availability = complete_availability(
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=10.0,
    )
    availability["finance_lease_total"] = replace(
        availability["finance_lease_total"],
        source_kind=None,
        evidence_class=None,
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.complete is True
    assert resolution.can_value is True
    assert resolution.total_debt.midpoint == 60.0


@pytest.mark.parametrize("required_source_field", ["source_kind", "evidence_class"])
def test_total_debt_aggregate_requires_extended_source_metadata(
    required_source_field: str,
) -> None:
    availability = complete_availability(
        commercial_paper=None,
        current_debt=None,
        noncurrent_debt=None,
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=None,
    )
    with_total_debt(availability, 60.0)
    availability["total_interest_bearing_debt"] = replace(
        availability["total_interest_bearing_debt"],
        **{required_source_field: None},
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert "total_interest_bearing_debt" in resolution.blocking_fields
    assert "BRIDGE_EVIDENCE_SOURCE_INCOMPLETE" in resolution.reason_codes


@pytest.mark.parametrize("field", ["cash", "current_debt"])
def test_not_applicable_is_not_usable_for_cash_or_debt(field: str) -> None:
    availability = complete_availability()
    availability[field] = replace(
        point(field, 0.0),
        state="not_applicable",
        reason_code="TEST_NOT_APPLICABLE",
        evidence_class="not_applicable",
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert resolution.blocking_fields == (field,)


@pytest.mark.parametrize(
    "field",
    [
        "cash",
        "marketable_securities_current",
        "marketable_securities_noncurrent",
        "commercial_paper",
        "current_debt",
        "noncurrent_debt",
        "finance_lease_current",
        "finance_lease_noncurrent",
        "preferred_equity",
        "noncontrolling_interests",
    ],
)
def test_current_proxy_is_not_usable_for_bridge_components(field: str) -> None:
    availability = complete_availability()
    availability[field] = replace(
        availability[field],
        state="proxy",
        reason_code="TEST_PROXY",
        evidence_class="proxy",
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert resolution.blocking_fields == (field,)


def test_current_proxy_is_not_usable_for_finance_lease_total() -> None:
    availability = complete_availability(
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=10.0,
    )
    availability["finance_lease_total"] = replace(
        availability["finance_lease_total"],
        state="proxy",
        reason_code="TEST_PROXY",
        evidence_class="proxy",
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert "finance_lease_total" in resolution.blocking_fields


def test_current_proxy_is_not_usable_for_total_debt_aggregate() -> None:
    availability = complete_availability(
        commercial_paper=None,
        current_debt=None,
        noncurrent_debt=None,
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=None,
    )
    with_total_debt(availability, 60.0)
    availability["total_interest_bearing_debt"] = replace(
        availability["total_interest_bearing_debt"],
        state="proxy",
        reason_code="TEST_PROXY",
        evidence_class="proxy",
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert "total_interest_bearing_debt" in resolution.blocking_fields


@pytest.mark.parametrize(
    "state",
    ["not_disclosed", "unresolved", "stale", "conflict"],
)
def test_unavailable_current_debt_states_block(state: str) -> None:
    availability = complete_availability()
    availability["current_debt"] = unavailable("current_debt", state)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.can_value is False
    assert resolution.blocking_fields == ("current_debt",)


@pytest.mark.parametrize("field", ["preferred_equity", "noncontrolling_interests"])
def test_current_not_applicable_claim_is_a_point_zero(field: str) -> None:
    availability = complete_availability()
    availability[field] = FieldAvailability(
        field=field,
        value=0.0,
        state="not_applicable",
        reason_code="CURRENT_EQUITY_PRESENTATION_HAS_NO_CLAIM",
        period_end=PERIOD_END,
        source_accession=ACCESSION,
        source_kind="filing_equity_presentation",
        evidence_class="not_applicable",
        freshness="current",
    )

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.complete is True
    assert getattr(resolution, field).midpoint == 0.0


def test_bounded_debt_endpoint_signs_reduce_the_equity_bridge() -> None:
    availability = complete_availability()
    availability["current_debt"] = bounded("current_debt", 10.0, 20.0)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.total_debt == BridgeRange(low=60.0, midpoint=65.0, high=70.0)
    assert resolution.bridge_adjustment == BridgeRange(
        low=54.0,
        midpoint=59.0,
        high=64.0,
    )


def test_bounded_bridge_remains_a_strict_withheld_precheck() -> None:
    availability = complete_availability()
    availability["current_debt"] = bounded("current_debt", 10.0, 20.0)

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)
    fields = resolution.as_balance_sheet_fields()

    assert resolution.complete is False
    assert resolution.can_value is True
    assert resolution.blocking_fields == ()
    assert resolution.bounded_fields == ("current_debt",)
    assert resolution.missing_fields == ("current_debt",)
    assert fields["bridge_complete"] is False
    assert fields["bridge_can_value"] is True
    assert fields["bridge_usable"] is False
    assert fields["bridge_decision"] == "withheld"
    assert fields["bridge_missing_fields"] == ["current_debt"]
    assert fields["bridge_bounded_fields"] == ["current_debt"]


def test_missing_blocking_and_bounded_fields_are_sorted_deterministically() -> None:
    availability = complete_availability()
    availability["cash"] = unresolved("cash")
    availability["current_debt"] = bounded("current_debt", 10.0, 20.0)
    availability["preferred_equity"] = unresolved("preferred_equity")

    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)

    assert resolution.blocking_fields == ("cash", "preferred_equity")
    assert resolution.bounded_fields == ("current_debt",)
    assert resolution.missing_fields == (
        "cash",
        "current_debt",
        "preferred_equity",
    )
    assert resolution.reason_codes == tuple(sorted(resolution.reason_codes))


def test_bridge_range_and_resolution_round_trip_through_json() -> None:
    range_value = BridgeRange(low=1.0, midpoint=2.0, high=3.0)
    resolution = reconcile_bridge(
        complete_availability(),
        fully_diluted_shares=10.0,
    )

    serialized_range = json.loads(json.dumps(range_value.as_dict()))
    serialized_resolution = json.loads(json.dumps(resolution.as_dict()))

    assert BridgeRange.from_dict(serialized_range) == range_value
    assert BridgeResolution.from_dict(serialized_resolution) == resolution
    assert serialized_resolution["blocking_fields"] == []
    assert serialized_resolution["cash_and_investments"] == {
        "low": 125.0,
        "midpoint": 125.0,
        "high": 125.0,
    }
    assert (
        resolution.as_balance_sheet_fields()["bridge_precheck"]
        == resolution.as_dict()
    )


def test_resolution_constructor_rejects_inconsistent_bridge_adjustment() -> None:
    resolution = reconcile_bridge(
        complete_availability(),
        fully_diluted_shares=10.0,
    )

    with pytest.raises(ValueError, match="bridge_adjustment"):
        replace(
            resolution,
            bridge_adjustment=BridgeRange(low=0.0, midpoint=0.0, high=0.0),
        )


def test_resolution_from_dict_rejects_inconsistent_bridge_adjustment() -> None:
    resolution = reconcile_bridge(
        complete_availability(),
        fully_diluted_shares=10.0,
    )
    serialized = resolution.as_dict()
    serialized["bridge_adjustment"] = {
        "low": 0.0,
        "midpoint": 0.0,
        "high": 0.0,
    }

    with pytest.raises(ValueError, match="bridge_adjustment"):
        BridgeResolution.from_dict(serialized)


@pytest.mark.parametrize(
    "low,midpoint,high",
    [
        (True, 1.0, 1.0),
        (0.0, float("nan"), 1.0),
        (0.0, 1.0, float("inf")),
        (1.0, 0.0, 2.0),
        (0.0, 2.0, 1.0),
    ],
)
def test_bridge_range_rejects_nonfinite_or_unordered_endpoints(
    low: float,
    midpoint: float,
    high: float,
) -> None:
    with pytest.raises(ValueError):
        BridgeRange(low=low, midpoint=midpoint, high=high)


@pytest.mark.parametrize(
    "fully_diluted_shares",
    [True, 0.0, -1.0, float("nan"), float("inf")],
)
def test_reconcile_bridge_rejects_invalid_fully_diluted_shares(
    fully_diluted_shares: float,
) -> None:
    with pytest.raises(ValueError, match="fully_diluted_shares"):
        reconcile_bridge(
            complete_availability(),
            fully_diluted_shares=fully_diluted_shares,
        )


def test_resolution_from_dict_revalidates_invalid_shares() -> None:
    resolution = reconcile_bridge(
        complete_availability(),
        fully_diluted_shares=10.0,
    )
    serialized = resolution.as_dict()
    serialized["fully_diluted_shares"] = float("nan")

    with pytest.raises(ValueError, match="fully_diluted_shares"):
        BridgeResolution.from_dict(serialized)


def test_bridge_records_are_frozen() -> None:
    range_value = BridgeRange(low=1.0, midpoint=2.0, high=3.0)
    resolution = reconcile_bridge(
        complete_availability(),
        fully_diluted_shares=10.0,
    )

    with pytest.raises(FrozenInstanceError):
        range_value.low = 0.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        resolution.complete = False  # type: ignore[misc]
