# Evidence-Aware Bridge Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add source-linked field availability, economic bridge reconciliation, bounded materiality, and fail-closed publication behavior to FinSight's US FCFF valuation pipeline.

**Architecture:** Existing Companyfacts and governed filing evidence are normalized into immutable field-availability records. A pure bridge-policy module reconciles non-overlapping economic groups, supplies midpoint inputs only for source-bounded uncertainty, and calculates a joint low-to-high per-share spread after enterprise value is known. The serving pipeline remains independent of Arelle; structural candidates enter through the existing shadow plan and cannot clear a gate until promoted.

**Tech Stack:** Python 3.11, frozen dataclasses, JSON, pytest 8.3.4, existing FinSight Companyfacts normalizer, FCFF models, artifact sanitizer, and structural-XBRL interfaces.

## Global Constraints

- Execute docs/superpowers/plans/2026-08-10-structural-xbrl-concept-resolution.md first; its first release remains shadow-only.
- A blank fact never becomes zero by itself.
- Stale facts never satisfy a current-period requirement.
- Conflicting applicable facts block the affected bridge group.
- The application-serving process must not import Arelle.
- Shadow structural candidates cannot clear publication gates.
- Unbounded bridge uncertainty remains withheld.
- A bounded bridge is usable only when the joint low-to-high intrinsic-value spread is no more than 1% of its positive midpoint.
- A bounded bridge can produce at most review_required, never pass.
- Existing bridge_complete and bridge_missing_fields meanings remain stable.
- Existing point-in-time controls and public-value scrubbing remain authoritative.
- Preserve all unrelated changes in the dirty worktree.
- Every production behavior is introduced test-first and watched failing before implementation.

---

## Execution order

This is the second implementation plan in the approved sequence:

1. Execute all six tasks in docs/superpowers/plans/2026-08-10-structural-xbrl-concept-resolution.md.
2. Verify the Arelle path is shadow-only and produces no serving-artifact changes.
3. Execute Tasks 1-8 in this plan.
4. Use the resulting live evidence before writing the separate sector-NWC and frontend-presentation designs.

## File structure

- Create backend/app/us_valuation/field_availability.py: immutable availability and uncertainty types, validation, legacy-source conversion, and structural-shadow conversion.
- Create backend/app/us_valuation/bridge_policy.py: bridge ranges, group reconciliation, overlap protection, materiality assessment, and deterministic serialization.
- Modify backend/app/us_valuation/xbrl.py: emit availability records and bridge precheck output while preserving legacy fields.
- Modify backend/app/us_valuation/pipeline.py: allow provisional valuation only for complete or fully bounded bridges, apply the 1% joint-spread gate, and cap bounded outputs at review_required.
- Modify backend/app/us_valuation/artifacts.py: expose a derived bridge-quality summary and preserve scrubbing for withheld ranges.
- Modify backend/app/us_valuation/structural_shadow.py: attach shadow-authority availability candidates without changing production normalization.
- Create backend/app/us_valuation/bridge_policy_shadow.py: read private artifacts, evaluate legacy and new bridge policy side by side, and produce bounded diagnostics.
- Create scripts/run_bridge_policy_shadow.py: corpus CLI that writes JSON diagnostics and a Markdown audit summary without modifying valuation artifacts.
- Create focused test modules under backend/tests instead of growing test_us_valuation.py.

---

### Task 1: Define immutable field availability and uncertainty

**Files:**
- Create: backend/app/us_valuation/field_availability.py
- Test: backend/tests/test_field_availability.py

**Interfaces:**
- Produces: AvailabilityState and AvailabilityAuthority literal types.
- Produces: UncertaintyRange and FieldAvailability frozen dataclasses.
- Produces: FieldAvailability.as_dict() and FieldAvailability.from_dict().
- Consumers: Tasks 2, 3, and 6.

- [ ] **Step 1: Write failing schema tests**

~~~python
from __future__ import annotations

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
~~~

- [ ] **Step 2: Run the tests and verify RED**

Run: cd backend && pytest -q tests/test_field_availability.py

Expected: collection fails with ModuleNotFoundError for app.us_valuation.field_availability.

- [ ] **Step 3: Implement the immutable schema**

Define these exact types and invariants:

~~~python
AvailabilityState = Literal[
    "reported",
    "explicit_zero",
    "evidence_backed_zero",
    "not_applicable",
    "proxy",
    "bounded_unresolved",
    "not_disclosed",
    "unresolved",
    "stale",
    "conflict",
]
AvailabilityAuthority = Literal["production", "shadow"]
Freshness = Literal["current", "stale", "unknown"]


@dataclass(frozen=True)
class UncertaintyRange:
    low: float
    high: float
    basis: str
    source_accessions: tuple[str, ...]


@dataclass(frozen=True)
class FieldAvailability:
    field: str
    value: float | None
    state: AvailabilityState
    reason_code: str
    period_end: str
    source_accession: str | None
    source_kind: str | None
    evidence_class: str | None
    freshness: Freshness
    uncertainty: UncertaintyRange | None = None
    covered_fields: tuple[str, ...] = ()
    authority: AvailabilityAuthority = "production"
    mapping_version: str = "US-FIELD-AVAILABILITY-1.0"
~~~

Validation rules:

- Reject bool values and non-finite numbers.
- Require 0 <= low <= high for every uncertainty range.
- Require a nonempty basis and at least one source accession for a range.
- reported and proxy require a finite point value.
- explicit_zero, evidence_backed_zero, and not_applicable require value == 0 and current freshness.
- bounded_unresolved requires value is None, current freshness, and an uncertainty range.
- not_disclosed, unresolved, stale, and conflict require value is None and no uncertainty range.
- stale requires freshness == stale.
- Any production point, zero, not-applicable, proxy, or bounded state requires source_accession.
- covered_fields is sorted and unique during construction; it is empty for ordinary component facts.
- as_dict() emits tuples as JSON arrays; from_dict() restores tuples and re-runs validation.

- [ ] **Step 4: Run the schema tests and verify GREEN**

Run: cd backend && pytest -q tests/test_field_availability.py

Expected: all tests pass.

- [ ] **Step 5: Commit the schema**

~~~bash
git add backend/app/us_valuation/field_availability.py backend/tests/test_field_availability.py
git commit -m "feat: define bridge field availability"
~~~

---

### Task 2: Convert existing normalized facts into availability records

**Files:**
- Modify: backend/app/us_valuation/field_availability.py
- Modify: backend/app/us_valuation/xbrl.py:11-13, 911-1011, 1153-1182
- Create: backend/tests/test_field_availability_normalizer.py

**Interfaces:**
- Consumes: FieldAvailability from Task 1 and the existing value/source/state triples in CompanyFactsNormalizer.
- Produces: availability_from_normalized_field(field, value, source, legacy_state, period_end, covered_fields=()) -> FieldAvailability.
- Produces: balance_sheet.availability keyed by normalized field.
- Consumers: Task 3 and all private-artifact diagnostics.

- [ ] **Step 1: Write failing legacy-mapping tests**

~~~python
from app.us_valuation.field_availability import availability_from_normalized_field


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
~~~

- [ ] **Step 2: Run the mapper tests and verify RED**

Run: cd backend && pytest -q tests/test_field_availability_normalizer.py

Expected: import fails because availability_from_normalized_field is absent.

- [ ] **Step 3: Implement the exact legacy mapping**

Use this mapping table:

~~~python
LEGACY_STATE_MAP = {
    "reported": "reported",
    "governed_filing_fact": "reported",
    "policy_verified_zero": "evidence_backed_zero",
    "weighted_average_diluted_proxy": "proxy",
    "verification_stale": "stale",
    "missing": "unresolved",
}
~~~

For governed_filing_fact with value == 0, map evidence_class == reported_zero to explicit_zero; map all other governed zero evidence to evidence_backed_zero. Read accession from source_accession first, then accession. Generate stable reason codes from state and evidence class; do not copy free-form rationale into reason_code.

- [ ] **Step 4: Add fixture helpers and a failing real-normalizer availability test**

Use the existing Microsoft fixtures and filing-record conversion:

~~~python
import json
from pathlib import Path
from typing import Any

from app.us_valuation.classification import classify_issuer
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
~~~

- [ ] **Step 5: Run the integration test and verify RED**

Run: cd backend && pytest -q tests/test_field_availability_normalizer.py::test_normalizer_emits_availability_without_changing_legacy_bridge_fields

Expected: KeyError for balance_sheet.availability.

- [ ] **Step 6: Emit availability from CompanyFactsNormalizer**

After balance_fields is complete and the share fallback has run, build:

~~~python
availability = {
    field: availability_from_normalized_field(
        field=field,
        value=item["value"],
        source=item["source"],
        legacy_state=item["state"],
        period_end=ttm_end,
        covered_fields=(
            ("finance_lease_current", "finance_lease_noncurrent")
            if field == "finance_lease_total"
            else ()
        ),
    )
    for field, item in balance_fields.items()
}
~~~

Serialize under balance_sheet.availability. Do not change bridge arithmetic or publication behavior in this task.

- [ ] **Step 7: Run focused and existing normalizer tests**

Run: cd backend && pytest -q tests/test_field_availability.py tests/test_field_availability_normalizer.py tests/test_filing_evidence.py tests/test_us_valuation.py

Expected: all tests pass with existing publication outcomes unchanged.

- [ ] **Step 8: Commit the compatibility layer**

~~~bash
git add backend/app/us_valuation/field_availability.py backend/app/us_valuation/xbrl.py backend/tests/test_field_availability_normalizer.py
git commit -m "feat: emit source-linked bridge availability"
~~~

---

### Task 3: Reconcile economic bridge groups without double counting

**Files:**
- Create: backend/app/us_valuation/bridge_policy.py
- Create: backend/tests/test_bridge_policy.py

**Interfaces:**
- Consumes: Mapping[str, FieldAvailability].
- Produces: BridgeRange, BridgeResolution, and BridgeAssessment frozen dataclasses with as_dict()/from_dict().
- Produces: reconcile_bridge(availability, fully_diluted_shares) -> BridgeResolution.
- Produces: BridgeResolution.as_balance_sheet_fields() -> dict[str, Any].
- Consumers: Tasks 4 and 5.

- [ ] **Step 1: Add explicit bridge test builders**

Place these builders in test_bridge_policy.py:

~~~python
import pytest


ACCESSION = "0000000000-26-000001"
PERIOD_END = "2026-06-30"


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


def bounded(field: str, low: float, high: float) -> FieldAvailability:
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
    )


def complete_availability(**overrides: float | None) -> dict[str, FieldAvailability]:
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
    result = {
        field: point(
            field,
            value,
            covered_fields=(
                ("finance_lease_current", "finance_lease_noncurrent")
                if field == "finance_lease_total"
                else ()
            ),
        )
        if value is not None
        else unresolved(field)
        for field, value in values.items()
    }
    return result
~~~

- [ ] **Step 2: Write failing complete-bridge and aggregate-lease tests**

~~~python
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


def test_aggregate_finance_lease_replaces_missing_split_without_double_counting() -> None:
    availability = complete_availability(
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=10.0,
    )
    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)
    assert resolution.total_debt.midpoint == 60.0
    assert "finance_lease_current" not in resolution.blocking_fields
    assert "finance_lease_noncurrent" not in resolution.blocking_fields


def test_matching_lease_total_and_split_are_counted_once() -> None:
    availability = complete_availability(
        finance_lease_current=2.0,
        finance_lease_noncurrent=8.0,
        finance_lease_total=10.0,
    )
    assert reconcile_bridge(
        availability,
        fully_diluted_shares=10.0,
    ).total_debt.midpoint == 60.0


def test_governed_total_debt_aggregate_covers_missing_components() -> None:
    availability = complete_availability(
        commercial_paper=None,
        current_debt=None,
        noncurrent_debt=None,
        finance_lease_current=None,
        finance_lease_noncurrent=None,
        finance_lease_total=None,
    )
    availability["total_interest_bearing_debt"] = point(
        "total_interest_bearing_debt",
        60.0,
        covered_fields=(
            "commercial_paper",
            "current_debt",
            "noncurrent_debt",
            "finance_lease_current",
            "finance_lease_noncurrent",
        ),
    )
    resolution = reconcile_bridge(
        availability,
        fully_diluted_shares=10.0,
    )
    assert resolution.total_debt.midpoint == 60.0
    assert resolution.blocking_fields == ()
~~~

- [ ] **Step 3: Write failing blocker and overlap tests**

~~~python
def test_unresolved_commercial_paper_blocks_when_no_aggregate_covers_it() -> None:
    availability = complete_availability(commercial_paper=None)
    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)
    assert resolution.complete is False
    assert resolution.can_value is False
    assert resolution.blocking_fields == ("commercial_paper",)


def test_conflicting_lease_total_and_split_fail_closed() -> None:
    availability = complete_availability(
        finance_lease_current=2.0,
        finance_lease_noncurrent=8.0,
        finance_lease_total=25.0,
    )
    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)
    assert resolution.can_value is False
    assert "FINANCE_LEASE_AGGREGATE_CONFLICT" in resolution.reason_codes


def test_conflicting_total_debt_aggregate_and_components_fail_closed() -> None:
    availability = complete_availability()
    availability["total_interest_bearing_debt"] = point(
        "total_interest_bearing_debt",
        75.0,
        covered_fields=(
            "commercial_paper",
            "current_debt",
            "noncurrent_debt",
            "finance_lease_current",
            "finance_lease_noncurrent",
        ),
    )
    resolution = reconcile_bridge(
        availability,
        fully_diluted_shares=10.0,
    )
    assert resolution.can_value is False
    assert "TOTAL_DEBT_AGGREGATE_CONFLICT" in resolution.reason_codes


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


@pytest.mark.parametrize(
    "state",
    ["not_disclosed", "unresolved", "stale", "conflict"],
)
def test_unavailable_current_debt_states_block(state: str) -> None:
    availability = complete_availability()
    availability["current_debt"] = unavailable("current_debt", state)
    resolution = reconcile_bridge(
        availability,
        fully_diluted_shares=10.0,
    )
    assert resolution.can_value is False
    assert resolution.blocking_fields == ("current_debt",)


def test_current_not_applicable_preferred_equity_is_a_point_zero() -> None:
    availability = complete_availability()
    availability["preferred_equity"] = FieldAvailability(
        field="preferred_equity",
        value=0.0,
        state="not_applicable",
        reason_code="CURRENT_EQUITY_PRESENTATION_HAS_NO_PREFERRED_CLAIM",
        period_end=PERIOD_END,
        source_accession=ACCESSION,
        source_kind="filing_equity_presentation",
        evidence_class="not_applicable",
        freshness="current",
    )
    resolution = reconcile_bridge(
        availability,
        fully_diluted_shares=10.0,
    )
    assert resolution.complete is True
    assert resolution.preferred_equity.midpoint == 0.0
~~~

- [ ] **Step 4: Run bridge-policy tests and verify RED**

Run: cd backend && pytest -q tests/test_bridge_policy.py

Expected: collection fails with ModuleNotFoundError for app.us_valuation.bridge_policy.

- [ ] **Step 5: Implement range and result types**

Define:

~~~python
@dataclass(frozen=True)
class BridgeRange:
    low: float
    midpoint: float
    high: float


@dataclass(frozen=True)
class BridgeResolution:
    complete: bool
    can_value: bool
    missing_fields: tuple[str, ...]
    blocking_fields: tuple[str, ...]
    bounded_fields: tuple[str, ...]
    cash_and_investments: BridgeRange
    total_debt: BridgeRange
    preferred_equity: BridgeRange
    noncontrolling_interests: BridgeRange
    bridge_adjustment: BridgeRange
    fully_diluted_shares: float
    reason_codes: tuple[str, ...]
    policy_version: str = "US-BRIDGE-POLICY-1.0"
~~~

Reject non-positive or non-finite shares. BridgeRange validates low <= midpoint <= high and finite numbers.

BridgeResolution.as_balance_sheet_fields() returns the legacy strict fields plus the new precheck:

~~~python
{
    "bridge_complete": resolution.complete,
    "bridge_can_value": resolution.can_value,
    "bridge_usable": resolution.complete,
    "bridge_decision": "complete" if resolution.complete else "withheld",
    "bridge_missing_fields": list(resolution.missing_fields),
    "bridge_blocking_fields": list(resolution.blocking_fields),
    "bridge_bounded_fields": list(resolution.bounded_fields),
    "bridge_precheck": resolution.as_dict(),
    "cash_and_nonoperating_investments": resolution.cash_and_investments.midpoint,
    "total_interest_bearing_debt": resolution.total_debt.midpoint,
    "preferred_equity": resolution.preferred_equity.midpoint,
    "noncontrolling_interests": resolution.noncontrolling_interests.midpoint,
}
~~~

- [ ] **Step 6: Implement deterministic group reconciliation**

Use exact economic signs:

~~~python
bridge_adjustment = (
    cash_and_investments
    - total_debt
    - preferred_equity
    - noncontrolling_interests
)
~~~

Rules:

- Cash must be a production point state.
- Current and noncurrent securities may be production point states or bounded_unresolved.
- Commercial paper, current debt, and noncurrent debt require production point or bounded states unless a governed aggregate explicitly covers the missing component.
- total_interest_bearing_debt is optional. When present, it must list every covered debt component. It may replace missing covered detail, or corroborate complete detail within max(1 USD, 1e-9 times the larger absolute value); a mismatch blocks with TOTAL_DEBT_AGGREGATE_CONFLICT.
- Finance-lease total covers both lease split fields. If a current total exists, use the total once; when current split values also exist, require their sum to match the total within max(1 USD, 1e-9 times the larger absolute value).
- Preferred equity and NCI accept production point/zero/not-applicable or bounded states.
- Shadow, stale, unresolved, not_disclosed, and conflict states become blockers.
- missing_fields equals sorted(blocking_fields + bounded_fields).
- complete is true only with no blocking or bounded fields.
- can_value is true when there are no blockers, including when bounded fields remain.
- For a bounded field, midpoint is (low + high) / 2.
- For multiple ranges, add worst-case endpoints using the account's bridge sign.

- [ ] **Step 7: Run bridge-policy tests and verify GREEN**

Run: cd backend && pytest -q tests/test_field_availability.py tests/test_bridge_policy.py

Expected: all tests pass.

- [ ] **Step 8: Commit the bridge reconciler**

~~~bash
git add backend/app/us_valuation/bridge_policy.py backend/tests/test_bridge_policy.py
git commit -m "feat: reconcile economic bridge groups"
~~~

---

### Task 4: Assess combined bridge materiality at the 1% boundary

**Files:**
- Modify: backend/app/us_valuation/bridge_policy.py
- Modify: backend/tests/test_bridge_policy.py

**Interfaces:**
- Consumes: BridgeResolution, which already carries fully diluted shares, plus enterprise value.
- Produces: assess_bridge_materiality(resolution, enterprise_value, spread_limit=0.01) -> BridgeAssessment.
- BridgeAssessment fields: decision, usable, intrinsic_value_range, spread_ratio, spread_limit, blocking_fields, bounded_fields, reason_codes, warning, policy_version.
- Consumer: Task 5.

- [ ] **Step 1: Add an explicit bounded-resolution builder**

Pytest is already imported from Task 3. Place these helpers in test_bridge_policy.py:

~~~python
def bounded_resolution(
    *,
    securities: tuple[float, float] | None = None,
    preferred: tuple[float, float] | None = None,
    debt: tuple[float, float] | None = None,
    shares: float,
) -> BridgeResolution:
    availability = complete_availability()
    if securities is not None:
        availability["marketable_securities_noncurrent"] = bounded(
            "marketable_securities_noncurrent",
            *securities,
        )
    if preferred is not None:
        availability["preferred_equity"] = bounded(
            "preferred_equity",
            *preferred,
        )
    if debt is not None:
        availability["noncurrent_debt"] = bounded(
            "noncurrent_debt",
            *debt,
        )
    return reconcile_bridge(
        availability,
        fully_diluted_shares=shares,
    )


def exact_one_percent_resolution() -> BridgeResolution:
    zero = BridgeRange(low=0.0, midpoint=0.0, high=0.0)
    adjustment = BridgeRange(low=0.0, midpoint=0.5, high=1.0)
    return BridgeResolution(
        complete=False,
        can_value=True,
        missing_fields=("marketable_securities_noncurrent",),
        blocking_fields=(),
        bounded_fields=("marketable_securities_noncurrent",),
        cash_and_investments=adjustment,
        total_debt=zero,
        preferred_equity=zero,
        noncontrolling_interests=zero,
        bridge_adjustment=adjustment,
        fully_diluted_shares=1.0,
        reason_codes=(),
    )
~~~

- [ ] **Step 2: Write failing complete and bounded-review tests**

~~~python
def test_complete_bridge_has_zero_spread_and_complete_decision() -> None:
    resolution = reconcile_bridge(
        complete_availability(),
        fully_diluted_shares=10.0,
    )
    assessment = assess_bridge_materiality(
        resolution,
        enterprise_value=1_000.0,
    )
    assert assessment.decision == "complete"
    assert assessment.usable is True
    assert assessment.spread_ratio == 0.0


def test_joint_spread_below_one_percent_is_bounded_review() -> None:
    resolution = bounded_resolution(
        securities=(0.0, 0.8),
        preferred=(0.0, 0.1),
        shares=10.0,
    )
    assessment = assess_bridge_materiality(
        resolution,
        enterprise_value=1_000.0,
    )
    assert assessment.decision == "bounded_review"
    assert assessment.usable is True
    assert assessment.spread_ratio < 0.01


def test_exact_one_percent_joint_spread_is_bounded_review() -> None:
    assessment = assess_bridge_materiality(
        exact_one_percent_resolution(),
        enterprise_value=99.5,
    )
    assert assessment.intrinsic_value_range == BridgeRange(
        low=99.5,
        midpoint=100.0,
        high=100.5,
    )
    assert assessment.spread_ratio == pytest.approx(0.01)
    assert assessment.decision == "bounded_review"
~~~

- [ ] **Step 3: Write failing boundary and joint-risk tests**

~~~python
def test_joint_spread_above_one_percent_is_withheld() -> None:
    resolution = bounded_resolution(
        securities=(0.0, 6.0),
        preferred=(0.0, 6.0),
        shares=10.0,
    )
    assessment = assess_bridge_materiality(
        resolution,
        enterprise_value=1_000.0,
    )
    assert assessment.decision == "withheld"
    assert assessment.usable is False
    assert assessment.spread_ratio > 0.01


def test_individually_small_fields_are_assessed_jointly() -> None:
    resolution = bounded_resolution(
        securities=(0.0, 6.0),
        preferred=(0.0, 6.0),
        shares=10.0,
    )
    assessment = assess_bridge_materiality(
        resolution,
        enterprise_value=1_000.0,
    )
    assert set(assessment.bounded_fields) == {
        "marketable_securities_noncurrent",
        "preferred_equity",
    }
    assert assessment.decision == "withheld"


def test_nonpositive_midpoint_is_withheld() -> None:
    resolution = bounded_resolution(
        debt=(0.0, 10.0),
        shares=10.0,
    )
    assessment = assess_bridge_materiality(
        resolution,
        enterprise_value=-100.0,
    )
    assert assessment.decision == "withheld"
    assert "NONPOSITIVE_INTRINSIC_VALUE_MIDPOINT" in assessment.reason_codes
~~~

- [ ] **Step 4: Run the materiality tests and verify RED**

Run: cd backend && pytest -q tests/test_bridge_policy.py

Expected: import or attribute failure because assess_bridge_materiality and BridgeAssessment do not exist.

- [ ] **Step 5: Implement the joint per-share calculation**

Add the immutable assessment type:

~~~python
@dataclass(frozen=True)
class BridgeAssessment:
    decision: Literal["complete", "bounded_review", "withheld"]
    usable: bool
    intrinsic_value_range: BridgeRange | None
    spread_ratio: float | None
    spread_limit: float
    blocking_fields: tuple[str, ...]
    bounded_fields: tuple[str, ...]
    reason_codes: tuple[str, ...]
    warning: str | None
    policy_version: str = "US-BRIDGE-POLICY-1.0"
~~~

Implement as_dict()/from_dict() with the same validation discipline as BridgeResolution. Use:

~~~python
shares = resolution.fully_diluted_shares
low = (enterprise_value + resolution.bridge_adjustment.low) / shares
high = (enterprise_value + resolution.bridge_adjustment.high) / shares
midpoint = (low + high) / 2
spread_ratio = (high - low) / midpoint
~~~

Calculate high before midpoint. Decision rules:

- Existing blockers: withheld without evaluating a provisional spread.
- No bounded fields: complete and usable.
- Midpoint <= 0 or any non-finite result: withheld.
- spread_ratio <= 0.01: bounded_review and usable.
- spread_ratio > 0.01: withheld.

The warning for bounded_review is exactly:

~~~text
Enterprise-to-equity bridge uses source-bounded uncertainty; the joint intrinsic-value spread is {spread_percent:.2f}% and requires review.
~~~

- [ ] **Step 6: Run all bridge tests and verify GREEN**

Run: cd backend && pytest -q tests/test_bridge_policy.py

Expected: all tests pass, including the exact 1% boundary.

- [ ] **Step 7: Commit materiality assessment**

~~~bash
git add backend/app/us_valuation/bridge_policy.py backend/tests/test_bridge_policy.py
git commit -m "feat: gate bridge uncertainty by materiality"
~~~

---

### Task 5: Integrate bridge precheck and final assessment into FCFF valuation

**Files:**
- Modify: backend/app/us_valuation/xbrl.py:1030-1182
- Modify: backend/app/us_valuation/pipeline.py:168-227, 477-645
- Create: backend/tests/test_bridge_policy_pipeline.py
- Test: backend/tests/test_us_valuation_v2_routing.py

**Interfaces:**
- Consumes: availability_from_normalized_field(), reconcile_bridge(), and assess_bridge_materiality().
- Produces: balance_sheet.bridge_precheck, bridge_can_value, bridge_complete, bridge_usable, bridge_decision, bridge_blocking_fields, bridge_bounded_fields, and bridge_uncertainty.
- Production pipeline uses midpoint aggregate bridge values only when BridgeResolution.can_value is true.

- [ ] **Step 1: Add real-fixture helpers and write a failing complete-bridge regression test**

~~~python
import json
from pathlib import Path
from typing import Any

import pytest

from app.us_valuation.bridge_policy import reconcile_bridge
from app.us_valuation.field_availability import (
    FieldAvailability,
    UncertaintyRange,
)
from app.us_valuation.pipeline import build_us_valuation
from app.us_valuation.xbrl import CompanyFactsNormalizer


FIXTURES = Path(__file__).parent / "fixtures" / "us"
ORIGINAL_NORMALIZE = CompanyFactsNormalizer.normalize


def load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build_aapl() -> dict[str, Any]:
    return build_us_valuation(
        submissions=load_json("aapl-submissions.json"),
        companyfacts=load_json("aapl-companyfacts.json"),
        valuation_date="2026-08-01",
    )


def test_complete_real_fixture_keeps_current_value_and_review_state() -> None:
    result = build_aapl()
    balance = result["financials"]["balance_sheet"]
    assert balance["bridge_decision"] == "complete"
    assert balance["bridge_usable"] is True
    assert balance["bridge_complete"] is True
    assert result["review"]["publication_state"] == "review_required"
~~~

- [ ] **Step 2: Run the complete-bridge test and verify RED**

Run: cd backend && pytest -q tests/test_bridge_policy_pipeline.py::test_complete_real_fixture_keeps_current_value_and_review_state

Expected: KeyError for bridge_decision or bridge_usable.

- [ ] **Step 3: Replace local tuple arithmetic with BridgeResolution**

In CompanyFactsNormalizer.normalize():

1. Build and serialize balance_sheet.availability.
2. Call reconcile_bridge() with FieldAvailability objects and diluted_proxy.
3. Set aggregate model inputs to the resolution midpoints.
4. Preserve bridge_complete as resolution.complete.
5. Preserve bridge_missing_fields as resolution.missing_fields.
6. Add bridge_precheck from resolution.as_dict().
7. Set bridge_can_value to resolution.can_value.
8. Set bridge_usable to resolution.complete.
9. Set bridge_decision to complete when complete, otherwise withheld until the pipeline finishes materiality assessment.

Do not store midpoint values in balance_sheet.values for bounded fields; those point values remain null.

- [ ] **Step 4: Change the early pipeline gate**

Replace the bridge_complete check with bridge_can_value. If false, use the existing withheld result with bridge_blocking_fields in the error. If true, run forecast assumptions and the valuation models using the aggregate midpoint fields. A bounded precheck therefore permits calculation but does not claim bridge_usable until the final assessment passes.

- [ ] **Step 5: Add a bounded-source wrapper and failing integration tests**

Use the real AAPL normalizer, then wrap its output in the test to replace one current securities availability record with a bounded source record and rerun the pure reconciliation helper. This preserves real forecast/model behavior and alters only the source condition under test.

~~~python
def install_bounded_aapl_normalizer(
    monkeypatch: pytest.MonkeyPatch,
    *,
    field: str,
    low: float,
    high: float,
) -> None:
    def normalize_with_bound(
        self: CompanyFactsNormalizer,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        financials = ORIGINAL_NORMALIZE(self, *args, **kwargs)
        balance = financials["balance_sheet"]
        availability = {
            name: FieldAvailability.from_dict(item)
            for name, item in balance["availability"].items()
        }
        source_accession = availability["cash"].source_accession
        assert source_accession is not None
        availability[field] = FieldAvailability(
            field=field,
            value=None,
            state="bounded_unresolved",
            reason_code="TEST_CURRENT_NOTE_RANGE",
            period_end=balance["period_end"],
            source_accession=source_accession,
            source_kind="test_current_filing_note",
            evidence_class="reported_range",
            freshness="current",
            uncertainty=UncertaintyRange(
                low=low,
                high=high,
                basis="Hand-checked integration-test filing range.",
                source_accessions=(source_accession,),
            ),
        )
        resolution = reconcile_bridge(
            availability,
            fully_diluted_shares=balance["fully_diluted_shares_proxy"],
        )
        balance["availability"] = {
            name: item.as_dict()
            for name, item in availability.items()
        }
        balance.update(resolution.as_balance_sheet_fields())
        return financials

    monkeypatch.setattr(
        CompanyFactsNormalizer,
        "normalize",
        normalize_with_bound,
    )


def test_bounded_bridge_under_limit_runs_but_cannot_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_bounded_aapl_normalizer(
        monkeypatch,
        field="marketable_securities_noncurrent",
        low=0.0,
        high=1_000_000.0,
    )
    result = build_aapl()
    assert result["financials"]["balance_sheet"]["bridge_decision"] == "bounded_review"
    assert result["review"]["publication_state"] == "review_required"
    assert all(
        model["publication_state"] == "review_required"
        for model in result["models"].values()
    )
    assert result["financials"]["balance_sheet"]["bridge_uncertainty"][
        "spread_ratio"
    ] <= 0.01


def test_bounded_bridge_over_limit_is_withheld(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_bounded_aapl_normalizer(
        monkeypatch,
        field="marketable_securities_noncurrent",
        low=0.0,
        high=1_000_000_000_000.0,
    )
    result = build_aapl()
    assert result["financials"]["balance_sheet"]["bridge_decision"] == "withheld"
    assert result["review"]["publication_state"] == "withheld"
    assert all(
        model["publication_state"] == "withheld"
        for model in result["models"].values()
    )
~~~

- [ ] **Step 6: Run the bounded tests and verify RED**

Run: cd backend && pytest -q tests/test_bridge_policy_pipeline.py -k bounded

Expected: bounded cases retain withheld legacy behavior or lack final assessment fields.

- [ ] **Step 7: Finalize bridge materiality after FCFF enterprise value**

Immediately after base = fcff_dcf(...):

~~~python
bridge_assessment = assess_bridge_materiality(
    BridgeResolution.from_dict(
        financials["balance_sheet"]["bridge_precheck"]
    ),
    enterprise_value=float(base["enterprise_value"]),
)
~~~

Write the assessment to balance_sheet.bridge_uncertainty and set final bridge_usable/bridge_decision. Pass bridge_assessment into _publication_review().

For bounded_review:

- Set fcff_dcf, epv, every FCFF scenario, and every sensitivity row to review_required unless already withheld.
- Append the bridge warning to result.review.warnings and each affected model's warnings.

For withheld:

- Set every model, scenario, and sensitivity publication_state to withheld.
- Add a review error containing spread ratio, 1% limit, and bounded fields.
- Leave private calculated values available for diagnosis; rely on public sanitizer to scrub them.

For complete:

- Preserve existing model and review behavior.

- [ ] **Step 8: Run focused pipeline tests and verify GREEN**

Run: cd backend && pytest -q tests/test_bridge_policy_pipeline.py tests/test_us_valuation_v2_routing.py

Expected: all tests pass; the existing incomplete-FCFF test remains withheld.

- [ ] **Step 9: Run full US valuation regressions**

Run: cd backend && pytest -q tests/test_us_valuation.py tests/test_filing_evidence.py tests/test_us_valuation_v2_fcff.py tests/test_us_valuation_v2_routing.py

Expected: all tests pass with no complete-bridge value regressions.

- [ ] **Step 10: Commit pipeline integration**

~~~bash
git add backend/app/us_valuation/xbrl.py backend/app/us_valuation/pipeline.py backend/tests/test_bridge_policy_pipeline.py backend/tests/test_us_valuation_v2_routing.py
git commit -m "feat: apply evidence-aware bridge policy"
~~~

---

### Task 6: Connect structural-XBRL shadow decisions without granting authority

**Files:**
- Modify: backend/app/us_valuation/field_availability.py
- Modify: backend/app/us_valuation/structural_shadow.py
- Modify: backend/tests/test_structural_shadow.py
- Modify: backend/tests/test_field_availability.py

**Interfaces:**
- Consumes: ResolutionDecision from app.us_valuation.structural_xbrl.
- Produces: availability_from_resolution_decision(decision) -> FieldAvailability with authority fixed to shadow.
- structural_shadow diagnostics include availability_candidate; production normalizer inputs remain unchanged.

- [ ] **Step 1: Write failing structural conversion tests**

~~~python
def test_accepted_structural_decision_is_still_shadow_authority() -> None:
    availability = availability_from_resolution_decision(
        ResolutionDecision(
            status="accepted",
            normalized_concept="marketable_securities_current",
            source_concept="issuer:LiquidInvestmentSecuritiesCurrent",
            value=42_500_000.0,
            unit="USD",
            period="2026-06-30",
            source_accession="0000000000-26-000001",
            confidence=0.96,
            mapping_method="extension_structural_match",
            reason_codes=("CURRENT_ASSET_PRESENTATION_PARENT",),
        )
    )
    assert availability.state == "reported"
    assert availability.authority == "shadow"


def test_review_structural_decision_cannot_carry_a_bridge_point() -> None:
    availability = availability_from_resolution_decision(
        ResolutionDecision(
            status="review",
            normalized_concept="marketable_securities_current",
            source_concept="issuer:MarketableInvestments",
            value=42_500_000.0,
            unit="USD",
            period="2026-06-30",
            source_accession="0000000000-26-000001",
            confidence=0.75,
            mapping_method="insufficient_structural_support",
            reason_codes=("LABEL_ONLY",),
        )
    )
    assert availability.state == "unresolved"
    assert availability.value is None
    assert availability.authority == "shadow"
~~~

- [ ] **Step 2: Run conversion tests and verify RED**

Run: cd backend && pytest -q tests/test_field_availability.py -k structural

Expected: import or attribute failure for availability_from_resolution_decision.

- [ ] **Step 3: Implement conversion with shadow as the default**

Accepted decisions map to reported only when value is numeric and the decision carries period, accession, source concept, mapping method, and reason codes. Review, rejected, and unresolved decisions map to unresolved with a null point. This function always emits shadow authority. A production promotion requires a separate governed interface and is outside this plan.

- [ ] **Step 4: Write a failing shadow diagnostic test**

~~~python
def test_shadow_case_emits_non_authoritative_availability_candidate() -> None:
    diagnostic = evaluate_shadow_case(
        withheld_artifact(missing=["marketable_securities_current"]),
        structural_filing_with_current_extension(),
    )
    candidate = diagnostic["decisions"][0]["availability_candidate"]
    assert candidate["authority"] == "shadow"
    assert candidate["field"] == "marketable_securities_current"
    assert diagnostic["publication_effect"] == "none_shadow_only"
~~~

- [ ] **Step 5: Run the shadow test and verify RED**

Run: cd backend && pytest -q tests/test_structural_shadow.py::test_shadow_case_emits_non_authoritative_availability_candidate

Expected: availability_candidate is absent.

- [ ] **Step 6: Attach candidates to shadow output only**

In evaluate_shadow_case(), serialize availability_from_resolution_decision() beside each resolution decision. Keep publication_effect equal to none_shadow_only and do not import structural_shadow from pipeline.py or xbrl.py.

- [ ] **Step 7: Verify serving imports remain Arelle-free**

Run: cd backend && python -c "import app.us_valuation.pipeline; assert 'arelle' not in __import__('sys').modules"

Run: cd backend && pytest -q tests/test_structural_shadow.py tests/test_field_availability.py tests/test_bridge_policy.py

Expected: import assertion and all tests pass.

- [ ] **Step 8: Commit the shadow mesh**

~~~bash
git add backend/app/us_valuation/field_availability.py backend/app/us_valuation/structural_shadow.py backend/tests/test_structural_shadow.py backend/tests/test_field_availability.py
git commit -m "feat: map structural shadow evidence to field states"
~~~

---

### Task 7: Preserve public safety and expose derived bridge quality

**Files:**
- Modify: backend/app/us_valuation/artifacts.py:145-157, 182-276, 328-421
- Create: backend/tests/test_bridge_policy_artifacts.py
- Test: backend/tests/test_automated_review.py

**Interfaces:**
- Consumes: private balance_sheet bridge decision and uncertainty.
- Produces: public bridge_quality containing decision, complete, usable, bounded_fields, blocking_fields, reason_codes, and derived per-share range.
- Withheld public artifacts retain reasons but null all intrinsic-value range numbers.

- [ ] **Step 1: Add real-result public artifact builders**

~~~python
import json
from pathlib import Path
from typing import Any

from app.us_valuation.artifacts import public_result, sanitize_public_artifact
from app.us_valuation.pipeline import build_us_valuation


FIXTURES = Path(__file__).parent / "fixtures" / "us"
BRIDGE_WARNING = (
    "Enterprise-to-equity bridge uses source-bounded uncertainty; "
    "the joint intrinsic-value spread is 1.00% and requires review."
)


def load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def submissions() -> dict[str, Any]:
    return load_json("aapl-submissions.json")


def bounded_private_result() -> dict[str, Any]:
    result = build_us_valuation(
        submissions=submissions(),
        companyfacts=load_json("aapl-companyfacts.json"),
        valuation_date="2026-08-01",
    )
    balance = result["financials"]["balance_sheet"]
    balance.update(
        {
            "bridge_complete": False,
            "bridge_usable": True,
            "bridge_decision": "bounded_review",
            "bridge_missing_fields": [
                "marketable_securities_noncurrent"
            ],
            "bridge_bounded_fields": [
                "marketable_securities_noncurrent"
            ],
            "bridge_blocking_fields": [],
            "bridge_uncertainty": {
                "decision": "bounded_review",
                "usable": True,
                "intrinsic_value_range": {
                    "low": 99.5,
                    "midpoint": 100.0,
                    "high": 100.5,
                },
                "spread_ratio": 0.01,
                "spread_limit": 0.01,
                "blocking_fields": [],
                "bounded_fields": [
                    "marketable_securities_noncurrent"
                ],
                "reason_codes": [],
                "warning": BRIDGE_WARNING,
                "policy_version": "US-BRIDGE-POLICY-1.0",
            },
        }
    )
    result["review"]["publication_state"] = "review_required"
    result["review"]["warnings"] = list(
        dict.fromkeys([*result["review"]["warnings"], BRIDGE_WARNING])
    )
    for model in result["models"].values():
        model["publication_state"] = "review_required"
    for scenario in result["scenarios"].values():
        scenario["fcff_dcf"]["publication_state"] = "review_required"
    return result


def bounded_public_artifact_with_pass_states() -> dict[str, Any]:
    artifact = public_result(
        bounded_private_result(),
        submissions(),
        sanitize=False,
    )
    artifact["review"]["publication_state"] = "pass"
    for model in artifact["models"].values():
        model["publication_state"] = "pass"
    for scenario in artifact["scenarios"].values():
        scenario["fcff_dcf"]["publication_state"] = "pass"
    return artifact


def adversarial_withheld_bridge_public() -> dict[str, Any]:
    artifact = bounded_public_artifact_with_pass_states()
    quality = artifact["bridge_quality"]
    quality["decision"] = "withheld"
    quality["usable"] = False
    quality["intrinsic_value_range"] = {
        "low": 80.0,
        "midpoint": 100.0,
        "high": 105.0,
        "spread_ratio": 0.25,
        "spread_limit": 0.01,
    }
    return artifact
~~~

- [ ] **Step 2: Write a failing bounded public-summary test**

~~~python
def test_bounded_public_artifact_exposes_only_derived_bridge_quality() -> None:
    private = bounded_private_result()
    public = public_result(private, submissions(), sanitize=True)
    assert public["review"]["publication_state"] == "review_required"
    assert public["bridge_quality"] == {
        "decision": "bounded_review",
        "complete": False,
        "usable": True,
        "bounded_fields": ["marketable_securities_noncurrent"],
        "blocking_fields": [],
        "reason_codes": [],
        "intrinsic_value_range": {
            "low": 99.5,
            "midpoint": 100.0,
            "high": 100.5,
            "spread_ratio": 0.01,
            "spread_limit": 0.01,
        },
    }
    serialized = json.dumps(public)
    assert '"availability"' not in serialized
    assert '"source_accession"' not in serialized
    assert '"cash_and_nonoperating_investments"' not in serialized
~~~

- [ ] **Step 3: Write a failing withheld-range scrubbing test**

~~~python
def test_withheld_bridge_range_is_scrubbed_but_reason_is_retained() -> None:
    public = sanitize_public_artifact(adversarial_withheld_bridge_public())
    assert public["review"]["publication_state"] == "withheld"
    assert public["bridge_quality"]["decision"] == "withheld"
    assert public["bridge_quality"]["bounded_fields"] == [
        "marketable_securities_noncurrent"
    ]
    assert public["bridge_quality"]["intrinsic_value_range"] == {
        "low": None,
        "midpoint": None,
        "high": None,
        "spread_ratio": 0.25,
        "spread_limit": 0.01,
    }
    assert public["models"]["fcff_dcf"]["intrinsic_value_per_share"] is None
~~~

- [ ] **Step 4: Write a failing publication-ceiling test**

~~~python
def test_bounded_bridge_cannot_be_promoted_to_pass_by_automated_review() -> None:
    artifact = bounded_public_artifact_with_pass_states()
    sanitized = sanitize_public_artifact(artifact)
    assert sanitized["review"]["publication_state"] == "review_required"
    assert sanitized["models"]["fcff_dcf"]["publication_state"] == "review_required"
~~~

- [ ] **Step 5: Run artifact tests and verify RED**

Run: cd backend && pytest -q tests/test_bridge_policy_artifacts.py

Expected: bridge_quality is absent or bounded pass is not downgraded.

- [ ] **Step 6: Implement derived public serialization**

Add _public_bridge_quality(result) that reads only the final bridge decision and per-share assessment. Do not serialize raw field values, availability records, sources, account ranges, or accessions.

In sanitize_public_artifact():

- bounded_review forces top-level and nested non-withheld models/scenarios to review_required;
- withheld bridge decision forces top-level and nested states to withheld;
- withheld scrubbing nulls low, midpoint, and high but retains spread_ratio, spread_limit, fields, and reason codes;
- unsupported bridge decisions fail closed as withheld.

- [ ] **Step 7: Run artifact, automated-review, and public-safety tests**

Run: cd backend && pytest -q tests/test_bridge_policy_artifacts.py tests/test_automated_review.py tests/test_us_valuation.py -k "public or withheld or bridge or automated"

Expected: all selected tests pass.

- [ ] **Step 8: Commit public safety behavior**

~~~bash
git add backend/app/us_valuation/artifacts.py backend/tests/test_bridge_policy_artifacts.py backend/tests/test_automated_review.py
git commit -m "feat: expose safe bridge quality"
~~~

---

### Task 8: Replay real issuer artifacts and gate activation with evidence

**Files:**
- Create: backend/app/us_valuation/bridge_policy_shadow.py
- Create: backend/tests/test_bridge_policy_shadow.py
- Create: scripts/run_bridge_policy_shadow.py
- Create from verified command output: docs/audit/02-evidence-aware-bridge-replay.md
- Modify after verification: docs/plans/ROADMAP.md
- Modify only if a blocker is deferred: docs/plans/PRODUCTION-BACKLOG.md

**Interfaces:**
- Produces: evaluate_private_artifact(artifact) -> dict[str, Any].
- Produces: evaluate_corpus(input_root, tickers=()) -> dict[str, Any].
- CLI writes bridge-policy-shadow.json and a Markdown summary; it never writes under backend/app/data/us_valuations or frontend/public/data.

- [ ] **Step 1: Add explicit private-artifact builders and failing corpus tests**

~~~python
from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.us_valuation.bridge_policy_shadow import (
    evaluate_corpus,
    evaluate_private_artifact,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PERIOD_END = "2026-06-30"
ACCESSION = "0000000000-26-000001"


def private_artifact_fixture(ticker: str = "TEST") -> dict[str, Any]:
    values = {
        "cash": 100.0,
        "marketable_securities_current": 20.0,
        "marketable_securities_noncurrent": 0.0,
        "commercial_paper": None,
        "current_debt": 10.0,
        "noncurrent_debt": 40.0,
        "finance_lease_current": 2.0,
        "finance_lease_noncurrent": 8.0,
        "finance_lease_total": 10.0,
        "preferred_equity": 0.0,
        "noncontrolling_interests": 0.0,
        "common_shares_outstanding": 10.0,
        "diluted_weighted_average_shares": 10.0,
        "incremental_dilutive_shares": 0.0,
    }
    states = {
        field: "missing" if value is None else "reported"
        for field, value in values.items()
    }
    sources = {
        field: None
        if value is None
        else {
            "accession": ACCESSION,
            "value_status": "reported",
            "value": value,
        }
        for field, value in values.items()
    }
    return {
        "issuer": {"ticker": ticker, "cik": "0000000000"},
        "financial_period_end": PERIOD_END,
        "financials": {
            "balance_sheet": {
                "period_end": PERIOD_END,
                "values": values,
                "sources": sources,
                "field_states": states,
                "fully_diluted_shares_proxy": 10.0,
                "bridge_complete": False,
                "bridge_missing_fields": ["commercial_paper"],
            }
        },
        "review": {"publication_state": "withheld"},
    }


def write_private(path: Path, *, ticker: str) -> None:
    artifact = deepcopy(private_artifact_fixture(ticker))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, indent=2) + "\n",
        encoding="utf-8",
    )


def test_shadow_evaluator_reports_old_and_new_bridge_states() -> None:
    report = evaluate_private_artifact(private_artifact_fixture())
    assert report["ticker"] == "TEST"
    assert report["legacy"]["bridge_complete"] is False
    assert report["evidence_aware"]["decision"] == "withheld"
    assert report["evidence_aware"]["blocking_fields"] == [
        "commercial_paper"
    ]
    assert report["serving_artifact_changed"] is False


def test_corpus_summary_counts_every_input_once(tmp_path: Path) -> None:
    write_private(tmp_path / "A" / "valuation-private.json", ticker="A")
    write_private(tmp_path / "B" / "valuation-private.json", ticker="B")
    summary = evaluate_corpus(tmp_path)
    assert summary["artifact_count"] == 2
    assert sum(summary["decision_counts"].values()) == 2
    assert summary["serving_artifacts_changed"] == 0
~~~

- [ ] **Step 2: Run shadow tests and verify RED**

Run: cd backend && pytest -q tests/test_bridge_policy_shadow.py

Expected: collection fails with ModuleNotFoundError for bridge_policy_shadow.

- [ ] **Step 3: Implement read-only artifact evaluation**

For artifacts with balance_sheet.availability, deserialize it. For legacy artifacts, reconstruct availability through availability_from_normalized_field() using values, sources, and field_states. Evaluate the bridge without changing the input mapping. Emit:

- ticker and financial period;
- legacy complete/missing fields;
- evidence-aware complete/can-value/decision;
- bounded and blocking fields;
- reason codes;
- field-state counts;
- whether a structural shadow candidate exists;
- serving_artifact_changed, always false.

The read-only precheck decision is complete when every field has a point, bounded_candidate when the bridge has only bounded fields, and withheld when any blocker remains. This diagnostic state is not a serving publication state. The corpus summary includes artifact count, decision counts, blocker frequencies, bounded-field frequencies, state counts, and a deterministic ticker-sorted case list.

- [ ] **Step 4: Write the failing CLI test**

~~~python
def test_cli_writes_diagnostics_outside_serving_roots(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    write_private(
        input_root / "TEST" / "valuation-private.json",
        ticker="TEST",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_bridge_policy_shadow.py",
            "--input-root",
            str(input_root),
            "--output-dir",
            str(output_root),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert (output_root / "bridge-policy-shadow.json").exists()
    assert (output_root / "bridge-policy-shadow.md").exists()
    assert not list((REPO_ROOT / "backend/app/data/us_valuations").glob("*.tmp"))
~~~

- [ ] **Step 5: Implement the bounded CLI**

Arguments:

~~~text
--input-root PATH
--output-dir PATH
--tickers AMZN,CAT,RCL,PEP,WMT,AAPL,MSFT,ANET,CRM,WDC
~~~

Require output-dir not to resolve inside backend/app/data/us_valuations or frontend/public/data. Write files atomically. Markdown contains the exact JSON summary counts plus one ticker-sorted table of legacy missing fields, evidence-aware blockers, bounded fields, and decision.

- [ ] **Step 6: Run CLI tests and verify GREEN**

Run: cd backend && pytest -q tests/test_bridge_policy_shadow.py

Run: python3 scripts/run_bridge_policy_shadow.py --help

Expected: tests pass and help exits zero.

- [ ] **Step 7: Run the complete focused suite**

Run: cd backend && pytest -q tests/test_structural_xbrl_schema.py tests/test_concept_resolver.py tests/test_arelle_adapter.py tests/test_filing_package.py tests/test_structural_shadow.py tests/test_field_availability.py tests/test_field_availability_normalizer.py tests/test_bridge_policy.py tests/test_bridge_policy_pipeline.py tests/test_bridge_policy_artifacts.py tests/test_bridge_policy_shadow.py

Expected: all tests pass.

- [ ] **Step 8: Run the full backend regression suite**

Run: cd backend && pytest -q

Expected: zero failures. Record the exact pass count and elapsed time.

- [ ] **Step 9: Replay the current private recovery corpus**

Run:

~~~bash
python3 scripts/run_bridge_policy_shadow.py \
  --input-root output/legacy-fcff-bridge-recovery \
  --output-dir output/bridge-policy-shadow
~~~

Validate:

~~~bash
jq '{artifact_count, decision_counts, blocker_frequencies, bounded_field_frequencies, serving_artifacts_changed}' output/bridge-policy-shadow/bridge-policy-shadow.json
~~~

Expected:

- artifact_count equals the number of valuation-private.json inputs;
- decision counts sum to artifact_count;
- serving_artifacts_changed equals 0;
- every changed eligibility case has field-level reason codes.

- [ ] **Step 10: Replay representative issuers and reconcile source lineage**

Run:

~~~bash
python3 scripts/run_bridge_policy_shadow.py \
  --input-root output/legacy-fcff-bridge-recovery \
  --output-dir output/bridge-policy-shadow-representative \
  --tickers AMZN,CAT,RCL,PEP,WMT,AAPL,MSFT,ANET,CRM,WDC
~~~

For every available ticker, compare period_end and source_accession to its controlling filing in the private artifact. Confirm:

- AMZN's explicit commercial-paper zero remains zero with current evidence;
- CAT and WMT stale observations remain stale and blocking unless current evidence resolves them;
- aggregate finance leases are counted once;
- no absent preferred equity, NCI, securities, or lease field becomes zero without a governed reason;
- shadow structural candidates do not change serving eligibility.

- [ ] **Step 11: Produce the durable audit report**

Use apply_patch to create docs/audit/02-evidence-aware-bridge-replay.md from the generated Markdown summary, then add:

- focused and full pytest command outputs;
- representative issuer reconciliation results, each labeled firsthand pass/fail;
- every publication-state delta and reason;
- unresolved cases and whether they remain withheld;
- the statement “verified — user confirmation needed.”

Do not mark the phase complete if any case lacks source accession reconciliation.

- [ ] **Step 12: Update the GoodBehavior roadmap gate**

Add stable roadmap IDs for:

- structural shadow verified;
- availability schema verified;
- bridge policy shadow verified;
- bounded-review activation verified or withheld pending evidence.

Mark an item with a firsthand check only when its command and real-artifact evidence are in the audit report. Move any failed promotion class to PRODUCTION-BACKLOG.md with the exact failing case and condition required to reconsider it.

- [ ] **Step 13: Commit the replay tooling and verified evidence**

~~~bash
git add backend/app/us_valuation/bridge_policy_shadow.py backend/tests/test_bridge_policy_shadow.py scripts/run_bridge_policy_shadow.py docs/audit/02-evidence-aware-bridge-replay.md docs/plans/ROADMAP.md docs/plans/PRODUCTION-BACKLOG.md
git commit -m "test: verify evidence-aware bridge policy"
~~~

---

## Plan self-check targets

- Structural parsing remains isolated in the pre-existing Arelle plan.
- Task 1 defines every type consumed later.
- Task 2 maps current production sources without changing publication.
- Tasks 3-4 implement economic reconciliation and joint materiality as pure functions.
- Task 5 changes FCFF behavior only after the pure policy passes.
- Task 6 proves Arelle shadow output meshes without receiving authority.
- Task 7 protects public output and the review ceiling.
- Task 8 verifies the real corpus and records the GoodBehavior gate.
- Sector-NWC rules and frontend layout remain outside this plan as required by the confirmed scope decomposition.
