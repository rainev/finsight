from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from app.us_valuation.field_availability import (
    FieldAvailability,
    UncertaintyRange,
)


def test_explicit_zero_preserves_current_source_evidence() -> None:
    item = FieldAvailability(
        field="commercial_paper",
        value=0.0,
        state="explicit_zero",
        reason_code="CURRENT_DEBT_NOTE_REPORTS_NONE_OUTSTANDING",
        period_end="2026-06-30",
        source_accession="0000000000-26-000001",
        source_kind="filing_debt_note",
        evidence_class="reported_zero",
        freshness="current",
    )
    assert FieldAvailability.from_dict(item.as_dict()) == item
    assert item.as_dict()["mapping_version"] == "US-FIELD-AVAILABILITY-1.0"


def test_bounded_field_requires_null_point_value_and_current_sources() -> None:
    item = FieldAvailability(
        field="marketable_securities_noncurrent",
        value=None,
        state="bounded_unresolved",
        reason_code="CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
        period_end="2026-06-30",
        source_accession="0000000000-26-000001",
        source_kind="filing_investments_note",
        evidence_class="reported_range",
        freshness="current",
        uncertainty=UncertaintyRange(
            low=0.0,
            high=10_000_000.0,
            basis="Current investment note bounds the undisclosed noncurrent portion.",
            source_accessions=("0000000000-26-000001",),
        ),
    )
    assert FieldAvailability.from_dict(item.as_dict()) == item


@pytest.mark.parametrize(
    "state,value",
    [
        ("explicit_zero", 1.0),
        ("not_applicable", None),
        ("unresolved", 1.0),
        ("stale", 0.0),
        ("conflict", 2.0),
    ],
)
def test_invalid_state_value_pairs_fail_closed(state: str, value: float | None) -> None:
    with pytest.raises(ValueError):
        FieldAvailability(
            field="preferred_equity",
            value=value,
            state=state,
            reason_code="TEST",
            period_end="2026-06-30",
            source_accession="0000000000-26-000001",
            source_kind="test",
            evidence_class="test",
            freshness="current",
        )


def test_shadow_authority_cannot_be_marked_as_production() -> None:
    item = FieldAvailability(
        field="marketable_securities_current",
        value=10.0,
        state="reported",
        reason_code="STRUCTURAL_EXTENSION_MATCH",
        period_end="2026-06-30",
        source_accession="0000000000-26-000001",
        source_kind="structural_xbrl",
        evidence_class="extension_structural_match",
        freshness="current",
        authority="shadow",
    )
    assert item.authority == "shadow"


def _reported(**overrides: object) -> FieldAvailability:
    values: dict[str, object] = {
        "field": "cash",
        "value": 100.0,
        "state": "reported",
        "reason_code": "CURRENT_FILING_FACT",
        "period_end": "2026-06-30",
        "source_accession": "0000000000-26-000001",
        "source_kind": "companyfacts",
        "evidence_class": "reported_fact",
        "freshness": "current",
    }
    values.update(overrides)
    return FieldAvailability(**values)  # type: ignore[arg-type]


def _uncertainty() -> UncertaintyRange:
    return UncertaintyRange(
        low=0.0,
        high=10.0,
        basis="Current filing supplies a finite range.",
        source_accessions=("0000000000-26-000001",),
    )


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), float("-inf")])
def test_point_values_reject_bools_and_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValueError, match="value"):
        _reported(value=value)


@pytest.mark.parametrize(
    "low,high",
    [
        (True, 1.0),
        (0.0, False),
        (float("nan"), 1.0),
        (0.0, float("inf")),
        (-1.0, 1.0),
        (2.0, 1.0),
    ],
)
def test_uncertainty_range_requires_finite_ordered_nonnegative_bounds(
    low: float, high: float
) -> None:
    with pytest.raises(ValueError):
        UncertaintyRange(
            low=low,
            high=high,
            basis="Current filing supplies a finite range.",
            source_accessions=("0000000000-26-000001",),
        )


@pytest.mark.parametrize(
    "basis,source_accessions",
    [
        ("", ("0000000000-26-000001",)),
        ("   ", ("0000000000-26-000001",)),
        ("Current filing range.", ()),
        ("Current filing range.", ("",)),
    ],
)
def test_uncertainty_range_requires_basis_and_source_accessions(
    basis: str, source_accessions: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError):
        UncertaintyRange(
            low=0.0,
            high=1.0,
            basis=basis,
            source_accessions=source_accessions,
        )


@pytest.mark.parametrize("state", ["reported", "proxy"])
def test_point_states_require_a_value(state: str) -> None:
    with pytest.raises(ValueError, match="value"):
        _reported(state=state, value=None)


@pytest.mark.parametrize(
    "state",
    ["explicit_zero", "evidence_backed_zero", "not_applicable"],
)
def test_zero_states_require_zero_and_current_freshness(state: str) -> None:
    with pytest.raises(ValueError):
        _reported(state=state, value=1.0)
    with pytest.raises(ValueError, match="freshness"):
        _reported(state=state, value=0.0, freshness="unknown")


def test_bounded_state_requires_null_value_current_freshness_and_range() -> None:
    with pytest.raises(ValueError, match="value"):
        _reported(state="bounded_unresolved", value=1.0, uncertainty=_uncertainty())
    with pytest.raises(ValueError, match="freshness"):
        _reported(
            state="bounded_unresolved",
            value=None,
            freshness="unknown",
            uncertainty=_uncertainty(),
        )
    with pytest.raises(ValueError, match="uncertainty"):
        _reported(state="bounded_unresolved", value=None)


@pytest.mark.parametrize(
    "state,freshness",
    [
        ("not_disclosed", "unknown"),
        ("unresolved", "unknown"),
        ("stale", "stale"),
        ("conflict", "unknown"),
    ],
)
def test_nonpoint_states_reject_uncertainty(state: str, freshness: str) -> None:
    with pytest.raises(ValueError, match="uncertainty"):
        _reported(
            state=state,
            value=None,
            freshness=freshness,
            source_accession=None,
            uncertainty=_uncertainty(),
        )


def test_stale_state_requires_stale_freshness() -> None:
    with pytest.raises(ValueError, match="freshness"):
        _reported(state="stale", value=None, freshness="current")


@pytest.mark.parametrize(
    "state,value,uncertainty",
    [
        ("reported", 1.0, None),
        ("proxy", 1.0, None),
        ("explicit_zero", 0.0, None),
        ("evidence_backed_zero", 0.0, None),
        ("not_applicable", 0.0, None),
        ("bounded_unresolved", None, _uncertainty()),
    ],
)
def test_production_resolving_states_require_source_accession(
    state: str,
    value: float | None,
    uncertainty: UncertaintyRange | None,
) -> None:
    with pytest.raises(ValueError, match="source_accession"):
        _reported(
            state=state,
            value=value,
            source_accession=None,
            uncertainty=uncertainty,
        )


def test_covered_fields_are_sorted_unique_and_default_empty() -> None:
    ordinary = _reported()
    aggregate = _reported(
        field="total_interest_bearing_debt",
        covered_fields=("noncurrent_debt", "current_debt", "noncurrent_debt"),
    )

    assert ordinary.covered_fields == ()
    assert aggregate.covered_fields == ("current_debt", "noncurrent_debt")


def test_serialization_emits_json_arrays_and_restores_tuples() -> None:
    item = _reported(
        field="total_interest_bearing_debt",
        value=None,
        state="bounded_unresolved",
        uncertainty=_uncertainty(),
        covered_fields=("noncurrent_debt", "current_debt"),
    )

    serialized = item.as_dict()

    assert serialized["covered_fields"] == ["current_debt", "noncurrent_debt"]
    assert serialized["uncertainty"]["source_accessions"] == [
        "0000000000-26-000001"
    ]
    assert json.loads(json.dumps(serialized)) == serialized
    restored = FieldAvailability.from_dict(serialized)
    assert restored == item
    assert isinstance(restored.covered_fields, tuple)
    assert isinstance(restored.uncertainty.source_accessions, tuple)


def test_from_dict_revalidates_mutated_payload() -> None:
    serialized = _reported().as_dict()
    serialized["value"] = float("nan")

    with pytest.raises(ValueError, match="value"):
        FieldAvailability.from_dict(serialized)


@pytest.mark.parametrize(
    "overrides",
    [
        {"state": "guessed"},
        {"authority": "advisory"},
        {"freshness": "future"},
    ],
)
def test_runtime_literal_values_fail_closed(overrides: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        _reported(**overrides)


def test_schema_records_are_frozen_and_hashable() -> None:
    item = _reported()
    uncertainty = _uncertainty()

    assert isinstance(hash(item), int)
    assert isinstance(hash(uncertainty), int)
    with pytest.raises(FrozenInstanceError):
        item.value = 1.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        uncertainty.low = 1.0  # type: ignore[misc]
