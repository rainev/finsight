# FinSight Evidence-Aware Reliability Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate FinSight's existing Arelle/evidence-aware bridge foundation, replace its all-or-nothing 1% gate with the approved fallback and `High`/`Medium`/`Low` reliability policy, and prove the behavior on the existing difficult-company replay corpus.

**Architecture:** Reuse the immutable source-evidence records, structural-XBRL resolver, and economic bridge reconciliation from `feat/evidence-aware-bridge-policy`. Add one pure reliability module, make annual company facts within 365 days explicitly carried forward, and let finite bridge ranges lower reliability instead of erasing values. Keep Arelle offline; generated JSON remains the only API input.

**Tech Stack:** Python 3.11, frozen dataclasses, FastAPI, SEC Companyfacts, Arelle offline worker, JSON artifacts, pytest 8.3.4, existing replay scripts.

## Scope boundary

This is Phase 1 of `docs/superpowers/specs/2026-08-14-whole-universe-valuation-reliability-design.md`. It implements the shared accounting and reliability pipeline used by every later company.

It does not claim 500/500 completion. Later gated plans must freeze the 500-company manifest, add missing specialist model lanes, supply current-price comparisons, run the complete-universe replay, and complete the point-in-time backtest. This phase must not invent those inputs merely to inflate coverage.

## Global Constraints

- Work only on `feat/whole-universe-greenlight` in `.worktrees/whole-universe-greenlight`.
- Preserve the user's dirty root checkout and never stage generated `output/` evidence.
- Keep Arelle in offline ingestion; the FastAPI process reads prepared JSON and never imports Arelle.
- Never treat missing, stale, conflicting, wrong-unit, wrong-currency, or wrong-share-denominator evidence as zero.
- Never switch a company to an economically unrelated valuation model to produce a number.
- A trustworthy annual company fact no more than 365 days old is `carried_forward`, not missing, and age alone creates no reliability cap.
- Accounting impact `0%–5%` has no automatic cap; `>5%–20%` caps at `Medium`; `>20%` is `Low`.
- Total scenario movement up to `20%` permits `High`; `>20%–40%` caps at `Medium`; `>40%` is `Low`.
- Do not silently tune thresholds. Replay evidence suggesting unfair grading must be reported to the user with affected counts and examples.
- Use test-driven development for every behavior change: observe RED, implement the minimum, then observe GREEN.
- A task is not complete from tests alone. Run the cached real-data replay or API consumer flow named in its gate.

---

### Task 1: Integrate and verify the existing evidence-aware foundation

**Files:**

- Merge source: `feat/evidence-aware-bridge-policy` at `e1cd1e2`
- Preserve: `docs/superpowers/specs/2026-08-14-whole-universe-valuation-reliability-design.md`
- Resolve: `docs/learnings/INDEX.md`
- Create: `docs/audit/03-evidence-foundation-integration.md`

**Interfaces:**

- Consumes: branch `feat/whole-universe-greenlight` at or after `81b9ee8`; branch `feat/evidence-aware-bridge-policy` at `e1cd1e2`.
- Produces: one branch containing `FieldAvailability`, `BridgeResolution`, structural-XBRL/Arelle support, pipeline integration, public-sanitizer protections, and all existing tests.

- [ ] **Step 1: Verify the isolated branch is clean**

Run:

```bash
git branch --show-current
git status --short
git rev-parse feat/evidence-aware-bridge-policy
```

Expected: branch is `feat/whole-universe-greenlight`, status is empty, and the source branch resolves to `e1cd1e2`.

- [ ] **Step 2: Merge without committing**

Run:

```bash
git merge --no-commit --no-ff feat/evidence-aware-bridge-policy
```

Expected: only `docs/learnings/INDEX.md` conflicts. If any implementation file conflicts, stop and record the unexpected conflict before choosing a side.

- [ ] **Step 3: Resolve the learning index additively**

The resolved `docs/learnings/INDEX.md` must retain the whole-universe threshold pointer and every evidence-branch pointer. Remove conflict markers, sort neither history nor content mechanically, and verify:

```bash
rg -n "^(<<<<<<<|=======|>>>>>>>)" docs/learnings/INDEX.md
rg -n "Reliability thresholds are provisional|Companyfacts|bridge|structural" docs/learnings/INDEX.md
```

Expected: the first command finds nothing; the second finds both bodies of learning pointers.

Stage the resolved conflict:

```bash
git add docs/learnings/INDEX.md
```

- [ ] **Step 4: Run the focused foundation suite**

Run:

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_field_availability.py \
  backend/tests/test_field_availability_normalizer.py \
  backend/tests/test_bridge_policy.py \
  backend/tests/test_bridge_policy_pipeline.py \
  backend/tests/test_structural_xbrl_schema.py \
  backend/tests/test_structural_xbrl_integration.py \
  backend/tests/test_structural_shadow.py
```

Expected: all focused tests pass.

- [ ] **Step 5: Run the full backend suite**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests
```

Expected baseline from `e1cd1e2`: `811 passed, 3 skipped`. Any different result must be explained in the audit before proceeding.

- [ ] **Step 6: Re-run the immutable bridge baseline**

Run with a new empty output directory:

```bash
python3 scripts/run_bridge_policy_shadow.py \
  --input-root /Users/carlosconda/Desktop/Investing\ Application/output/legacy-fcff-bridge-recovery \
  --output-dir output/bridge-policy-integration-baseline
```

Expected: 104 valid private company artifacts plus the two known invalid public-shaped cases; no serving artifact changes. A non-zero exit caused solely by the known zero-publication evidence gate is recorded as baseline evidence, not described as a passing gate.

- [ ] **Step 7: Record verified integration evidence**

Create `docs/audit/03-evidence-foundation-integration.md` with the exact branch SHAs, merge result, focused/full test outputs, replay command, input denominator, decision counts, and any differences from the expected baseline. Label every statement `Verified` or `Unverified`.

- [ ] **Step 8: Commit the integration**

```bash
git add docs/audit/03-evidence-foundation-integration.md
git diff --cached --check
git commit -m "merge: integrate evidence-aware valuation foundation"
```

**Gate:** The evidence/Arelle foundation is present on the feature branch, the full backend baseline is known, and the replay is reproducible without changing served artifacts.

---

### Task 2: Add the pure three-level reliability engine

**Files:**

- Create: `backend/app/us_valuation/reliability.py`
- Create: `backend/tests/test_us_valuation_reliability.py`

**Interfaces:**

- Produces: `ReliabilityLabel`, `ReliabilityAssessment`, `relative_movement()`, `accounting_label()`, `scenario_label()`, `lowest_label()`, and `assess_reliability()`.
- Consumed by: bridge assessment, pipeline results, artifacts, API summaries, and replay reporting.

- [ ] **Step 1: Write failing boundary and validation tests**

Add tests with this public API:

```python
from app.us_valuation.reliability import (
    assess_reliability,
    relative_movement,
)


def test_relative_movement_uses_largest_distance_from_base() -> None:
    assert relative_movement(low=94.0, base=100.0, high=105.0) == 0.06


@pytest.mark.parametrize(
    ("low", "base", "high", "expected"),
    [
        (95.0, 100.0, 105.0, "High"),
        (94.99, 100.0, 105.0, "Medium"),
        (80.0, 100.0, 120.0, "Medium"),
        (79.99, 100.0, 120.0, "Low"),
    ],
)
def test_accounting_boundaries(low, base, high, expected) -> None:
    result = assess_reliability(
        accounting_low=low,
        accounting_base=base,
        accounting_high=high,
        scenario_low=80.0,
        scenario_base=100.0,
        scenario_high=120.0,
    )
    assert result.accounting_label == expected


@pytest.mark.parametrize(
    ("low", "base", "high", "expected"),
    [
        (80.0, 100.0, 120.0, "High"),
        (79.99, 100.0, 120.0, "Medium"),
        (60.0, 100.0, 140.0, "Medium"),
        (59.99, 100.0, 140.0, "Low"),
    ],
)
def test_scenario_boundaries(low, base, high, expected) -> None:
    result = assess_reliability(
        accounting_low=100.0,
        accounting_base=100.0,
        accounting_high=100.0,
        scenario_low=low,
        scenario_base=base,
        scenario_high=high,
    )
    assert result.scenario_label == expected


def test_sector_or_unproven_model_cap_forces_low() -> None:
    result = assess_reliability(
        accounting_low=100.0,
        accounting_base=100.0,
        accounting_high=100.0,
        scenario_low=90.0,
        scenario_base=100.0,
        scenario_high=110.0,
        model_cap="Low",
        source_cap="High",
        reasons=("UNPROVEN_SPECIALIST_LANE",),
    )
    assert result.label == "Low"
```

Also test booleans, non-finite values, unordered ranges, zero base, unknown labels, and duplicate reason removal.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/test_us_valuation_reliability.py
```

Expected: collection fails because `app.us_valuation.reliability` does not exist.

- [ ] **Step 3: Implement the minimal pure module**

Use this implementation contract:

```python
from dataclasses import dataclass
from math import isclose, isfinite
from numbers import Real
from typing import Literal


ReliabilityLabel = Literal["High", "Medium", "Low"]
_LABEL_RANK: dict[ReliabilityLabel, int] = {
    "High": 0,
    "Medium": 1,
    "Low": 2,
}
_BOUNDARY_RELATIVE_TOLERANCE = 1e-12
_BOUNDARY_ABSOLUTE_TOLERANCE = 1e-15


@dataclass(frozen=True)
class ReliabilityAssessment:
    label: ReliabilityLabel
    accounting_label: ReliabilityLabel
    scenario_label: ReliabilityLabel
    model_cap: ReliabilityLabel
    source_cap: ReliabilityLabel
    accounting_impact_ratio: float
    scenario_movement_ratio: float
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "accounting_label": self.accounting_label,
            "scenario_label": self.scenario_label,
            "model_cap": self.model_cap,
            "source_cap": self.source_cap,
            "accounting_impact_ratio": self.accounting_impact_ratio,
            "scenario_movement_ratio": self.scenario_movement_ratio,
            "reasons": list(self.reasons),
        }


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    normalized = float(value)
    if not isfinite(normalized):
        raise ValueError(f"{name} must be a finite number")
    return normalized


def relative_movement(*, low: float, base: float, high: float) -> float:
    low_value = _finite_number(low, "low")
    base_value = _finite_number(base, "base")
    high_value = _finite_number(high, "high")
    if not low_value <= base_value <= high_value:
        raise ValueError("range must satisfy low <= base <= high")
    if base_value == 0:
        raise ValueError("base must be non-zero")
    return max(
        abs(low_value - base_value),
        abs(high_value - base_value),
    ) / abs(base_value)


def _nonnegative_ratio(value: float) -> float:
    normalized = _finite_number(value, "ratio")
    if normalized < 0:
        raise ValueError("ratio must be nonnegative")
    return normalized


def _at_or_below(value: float, boundary: float) -> bool:
    return value < boundary or isclose(
        value,
        boundary,
        rel_tol=_BOUNDARY_RELATIVE_TOLERANCE,
        abs_tol=_BOUNDARY_ABSOLUTE_TOLERANCE,
    )


def accounting_label(impact: float) -> ReliabilityLabel:
    impact = _nonnegative_ratio(impact)
    if _at_or_below(impact, 0.05):
        return "High"
    if _at_or_below(impact, 0.20):
        return "Medium"
    return "Low"


def scenario_label(movement: float) -> ReliabilityLabel:
    movement = _nonnegative_ratio(movement)
    if _at_or_below(movement, 0.20):
        return "High"
    if _at_or_below(movement, 0.40):
        return "Medium"
    return "Low"


def lowest_label(*labels: ReliabilityLabel) -> ReliabilityLabel:
    if not labels or any(label not in _LABEL_RANK for label in labels):
        raise ValueError("labels must contain only High, Medium, or Low")
    return max(labels, key=_LABEL_RANK.__getitem__)


def assess_reliability(
    *,
    accounting_low: float,
    accounting_base: float,
    accounting_high: float,
    scenario_low: float,
    scenario_base: float,
    scenario_high: float,
    model_cap: ReliabilityLabel = "High",
    source_cap: ReliabilityLabel = "High",
    reasons: tuple[str, ...] = (),
) -> ReliabilityAssessment:
    accounting_impact = relative_movement(
        low=accounting_low,
        base=accounting_base,
        high=accounting_high,
    )
    scenario_movement = relative_movement(
        low=scenario_low,
        base=scenario_base,
        high=scenario_high,
    )
    data_label = accounting_label(accounting_impact)
    forecast_label = scenario_label(scenario_movement)
    label = lowest_label(data_label, forecast_label, model_cap, source_cap)
    if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
        raise ValueError("reasons must contain nonempty strings")
    return ReliabilityAssessment(
        label=label,
        accounting_label=data_label,
        scenario_label=forecast_label,
        model_cap=model_cap,
        source_cap=source_cap,
        accounting_impact_ratio=accounting_impact,
        scenario_movement_ratio=scenario_movement,
        reasons=tuple(dict.fromkeys(reasons)),
    )
```

`lowest_label()` must use the strictness order `High < Medium < Low`. Ratios are unrounded floats; rounding is presentation-only.

- [ ] **Step 4: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_us_valuation_reliability.py
PYTHONPATH=backend pytest -q backend/tests
```

Expected: all tests pass with no warnings introduced.

- [ ] **Step 5: Commit**

```bash
git add backend/app/us_valuation/reliability.py backend/tests/test_us_valuation_reliability.py
git diff --cached --check
git commit -m "feat: add valuation reliability thresholds"
```

**Gate:** Exact 5%, 20%, and 40% boundaries and qualitative caps are proven by direct tests.

---

### Task 3: Treat trustworthy annual facts within 365 days as carried forward

**Files:**

- Modify: `backend/app/us_valuation/field_availability.py`
- Modify: `backend/app/us_valuation/xbrl.py`
- Modify: `backend/app/us_valuation/bridge_policy.py`
- Modify: `backend/tests/test_field_availability.py`
- Modify: `backend/tests/test_field_availability_normalizer.py`
- Modify: `backend/tests/test_bridge_policy.py`

**Interfaces:**

- Extends `Freshness` with `carried_forward`.
- Extends `FieldAvailability` with `fallback_level` and `source_age_days`.
- Extends `availability_from_normalized_field(*, field, value, source, legacy_state, period_end, covered_fields=(), reference_date: str)` to recover a source-linked prior company fact when it is no more than 365 days old.

- [ ] **Step 1: Write failing carried-forward contract tests**

Add round-trip tests proving this record is valid:

```python
FieldAvailability(
    field="finance_lease_noncurrent",
    value=25.0,
    state="reported",
    reason_code="ANNUAL_COMPANY_FACT_CARRIED_FORWARD",
    period_end="2025-12-31",
    source_accession="0000000000-26-000001",
    source_kind="companyfacts",
    evidence_class="reported",
    freshness="carried_forward",
    fallback_level="annual_carried_forward",
    source_age_days=181,
)
```

Add invalid tests for missing age, negative age, age `366`, missing accession, and shadow authority. Add bridge tests proving valid carried-forward company evidence is usable and that a `366`-day source remains unusable.

- [ ] **Step 2: Write failing normalizer boundary tests**

Use a reduced Companyfacts fixture whose current quarter omits an instant field but whose controlling `10-K` reports it. Assert:

```python
assert availability["finance_lease_noncurrent"]["value"] == 25.0
assert availability["finance_lease_noncurrent"]["freshness"] == "carried_forward"
assert availability["finance_lease_noncurrent"]["fallback_level"] == "annual_carried_forward"
assert availability["finance_lease_noncurrent"]["source_age_days"] == 365
```

Move the reference date one day later and assert the same source remains `stale` with no usable point value.

- [ ] **Step 3: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_field_availability.py \
  backend/tests/test_field_availability_normalizer.py \
  backend/tests/test_bridge_policy.py \
  -k 'carried_forward or 365 or 366'
```

Expected: failures because `carried_forward`, fallback metadata, and `reference_date` are unsupported.

- [ ] **Step 4: Extend the immutable availability contract**

Add:

```python
FallbackLevel = Literal[
    "current_reported",
    "current_structural",
    "reported_aggregate",
    "annual_carried_forward",
    "company_history",
    "sector_estimate",
]
Freshness = Literal["current", "carried_forward", "stale", "unknown"]
```

Add to `FieldAvailability`:

```python
fallback_level: FallbackLevel = "current_reported"
source_age_days: int | None = None
```

Require `annual_carried_forward` to use production authority, `freshness="carried_forward"`, a source accession, and integer age `0 <= source_age_days <= 365`. Preserve these fields through `as_dict()` and `from_dict()`.

- [ ] **Step 5: Recover eligible annual company facts in the normalizer**

Change `availability_from_normalized_field()` to accept `reference_date`. For legacy `verification_stale`, inspect the source's `value`, `end`, `form`, and accession. If the form is `10-K` or `10-K/A`, the value is finite and nonnegative, source end is not after the reference date, and age is at most 365 days, return a production `reported` record with `freshness="carried_forward"`, `fallback_level="annual_carried_forward"`, and exact age. Otherwise preserve the existing unusable `stale` record.

Pass `reference_date=self.as_of_date or ttm_end` from `CompanyFactsNormalizer.normalize()`.

- [ ] **Step 6: Permit carried-forward evidence without an age-only cap**

In `bridge_policy._record_unusable_reason()`, accept `freshness` in `{"current", "carried_forward"}`. Do not classify carried-forward as bounded solely because of age. Preserve `fallback_level` in private availability output so later replay reporting can count it.

- [ ] **Step 7: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_field_availability.py \
  backend/tests/test_field_availability_normalizer.py \
  backend/tests/test_bridge_policy.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 8: Commit**

```bash
git add \
  backend/app/us_valuation/field_availability.py \
  backend/app/us_valuation/xbrl.py \
  backend/app/us_valuation/bridge_policy.py \
  backend/tests/test_field_availability.py \
  backend/tests/test_field_availability_normalizer.py \
  backend/tests/test_bridge_policy.py
git diff --cached --check
git commit -m "feat: carry recent annual accounting facts forward"
```

**Gate:** A trustworthy company fact at 365 days is usable and traceable; at 366 days it is not. No current or conflicting evidence is weakened.

---

### Task 4: Replace the 1% bridge cutoff with accounting-impact reliability

**Files:**

- Modify: `backend/app/us_valuation/bridge_policy.py`
- Modify: `backend/app/us_valuation/pipeline.py`
- Modify: `backend/app/us_valuation/equity_models.py`
- Modify: `backend/tests/test_bridge_policy.py`
- Modify: `backend/tests/test_bridge_policy_pipeline.py`
- Modify: `backend/tests/test_us_valuation.py`
- Modify: `backend/tests/test_us_valuation_v2_routing.py`

**Interfaces:**

- `BridgeAssessment` adds `accounting_impact_ratio` and `reliability_cap`.
- `assess_bridge_materiality(resolution, enterprise_value)` returns usable finite bounded ranges at every size.
- `build_us_valuation()` and `build_equity_level_result()` attach one `ReliabilityAssessment` dictionary to every newly generated finite private valuation result. A true withheld result has no fabricated impact ratios.

- [ ] **Step 1: Replace old cutoff tests with failing impact tests**

Keep tests that withhold real blockers, invalid shares, non-finite outputs, and non-positive midpoints. Replace tests asserting `>1%` withholding with these behaviors:

```python
assert assess_bridge_materiality(five_percent, enterprise_value).reliability_cap == "High"
assert assess_bridge_materiality(just_over_five, enterprise_value).reliability_cap == "Medium"
assert assess_bridge_materiality(twenty_percent, enterprise_value).reliability_cap == "Medium"
assert assess_bridge_materiality(just_over_twenty, enterprise_value).reliability_cap == "Low"
assert assess_bridge_materiality(just_over_twenty, enterprise_value).usable is True
```

In the pipeline test, assert a `Low` bridge assessment preserves finite FCFF, EPV, scenario, sensitivity, and scenario-range values while the review remains `review_required`.

Add routing tests asserting residual-income and DDM results derive reliability from their scenario ranges. Add an FFO test asserting its explicitly limited interim route uses `model_cap="Low"`.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_bridge_policy.py \
  backend/tests/test_bridge_policy_pipeline.py \
  backend/tests/test_us_valuation.py \
  backend/tests/test_us_valuation_v2_routing.py \
  -k 'materiality or bridge or reliability'
```

Expected: old `1%` withholding behavior contradicts the new assertions.

- [ ] **Step 3: Change bridge assessment without weakening evidence validation**

For a finite range, calculate:

```python
accounting_impact_ratio = max(
    abs(intrinsic_value_range.low - intrinsic_value_range.midpoint),
    abs(intrinsic_value_range.high - intrinsic_value_range.midpoint),
) / abs(intrinsic_value_range.midpoint)
```

Use `accounting_label(accounting_impact_ratio)` for `reliability_cap`. Return `decision="bounded_review"` and `usable=True` for every finite positive midpoint, including impact above 20%. Retain `decision="withheld"` only for unresolved blockers, invalid shares, non-finite results, or non-positive midpoint.

- [ ] **Step 4: Make the pipeline preserve bounded values**

Change `_apply_bridge_publication_ceiling()` so `bounded_review` adds a warning and sets model publication states no stricter than `review_required`; it must not null any value. Only an unusable assessment may invoke the existing withheld scrub path.

After low/base/high scenarios exist, call:

```python
reliability = assess_reliability(
    accounting_low=bridge_low,
    accounting_base=bridge_midpoint,
    accounting_high=bridge_high,
    scenario_low=scenario_range["low"],
    scenario_base=scenario_range["base"],
    scenario_high=scenario_range["high"],
    source_cap=bridge_assessment.reliability_cap,
    reasons=bridge_assessment.reason_codes,
)
```

For a complete bridge, set all three accounting values to the base intrinsic value. Save `reliability.as_dict()` at top level in the private result.

- [ ] **Step 5: Apply the same contract to governed equity-level lanes**

In `build_equity_level_result()`, calculate reliability after low/base/high values exist. Use the base value for all three accounting values because this phase has no separate bounded bridge for equity-level models. Use the result's low/base/high scenario range for scenario movement. Set `model_cap="Low"` and add `INTERIM_FFO_ROUTE` for the existing FFO route; use `model_cap="High"` for governed residual-income and DDM routes. Save the same top-level `reliability` dictionary used by FCFF results.

- [ ] **Step 6: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_bridge_policy.py \
  backend/tests/test_bridge_policy_pipeline.py \
  backend/tests/test_us_valuation.py \
  backend/tests/test_us_valuation_v2_routing.py \
  backend/tests/test_us_valuation_reliability.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 7: Commit**

```bash
git add \
  backend/app/us_valuation/bridge_policy.py \
  backend/app/us_valuation/pipeline.py \
  backend/app/us_valuation/equity_models.py \
  backend/tests/test_bridge_policy.py \
  backend/tests/test_bridge_policy_pipeline.py \
  backend/tests/test_us_valuation.py \
  backend/tests/test_us_valuation_v2_routing.py
git diff --cached --check
git commit -m "feat: grade bounded bridge uncertainty by impact"
```

**Gate:** Finite uncertainty changes reliability instead of erasing values; true source-integrity blockers still fail closed.

---

### Task 5: Add reliability to artifacts and API without leaking unsafe data

**Files:**

- Modify: `backend/app/us_valuation/artifacts.py`
- Modify: `backend/app/us_valuation/automated_review.py`
- Modify: `backend/app/routers/us_valuations.py`
- Modify: `backend/tests/test_bridge_policy_artifacts.py`
- Modify: `backend/tests/test_automated_review.py`
- Modify: `backend/tests/test_us_valuation.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**

- `public_result(result, submissions=None)` becomes the canonical serializer for FCFF, residual-income, DDM, and FFO results. It reuses `public_equity_artifact()` for equity-level lanes before applying the same sanitizer and reliability contract.
- Newly generated public artifacts use `schema_version="US-PUBLIC-VALUATION-1.1"`; a 1.1 artifact missing reliability is invalid rather than being mislabeled as legacy.
- Public detail adds an allowlisted `reliability` DTO with `label`, accounting impact, scenario movement, caps, and reason codes.
- Public list adds `reliability` as `High`, `Medium`, or `Low`.
- Old finite 1.0 artifacts without reliability receive `Low` plus `LEGACY_ARTIFACT_NOT_REGENERATED`; they do not pretend to be high confidence.
- Withheld artifacts receive a canonical `Low` reliability DTO with null impact metrics and only `VALUATION_WITHHELD`; no private withholding text is echoed.
- `FINSIGHT_US_VALUATION_DATA_ROOT` may point a local verification server at regenerated public artifacts; when unset, the production data root remains `backend/app/data/us_valuations`.

- [ ] **Step 1: Write failing public-contract tests**

Assert a newly generated detail artifact contains:

```python
assert public["reliability"] == {
    "label": "Medium",
    "accounting_label": "High",
    "scenario_label": "Medium",
    "model_cap": "High",
    "source_cap": "High",
    "accounting_impact_ratio": pytest.approx(0.05),
    "scenario_movement_ratio": pytest.approx(0.25),
    "reasons": [],
}
```

Add adversarial tests for unknown labels, booleans/non-finite ratios, duplicate reasons, extra keys, and malformed dictionaries. Assert malformed reliability becomes `Low` with `RELIABILITY_PAYLOAD_INVALID`, while pre-existing finite model/range values remain visible unless another genuine publication blocker requires scrubbing.

Add tests proving:

- a finite `bounded_review` artifact above the historical 1% spread is preserved and graded instead of scrubbed;
- FCFF, residual-income, DDM, and FFO all pass through canonical `public_result()` and expose safe reliability;
- a `review_required` supporting EPV model is a caveat and does not hide a finite primary FCFF value;
- a withheld primary model, non-finite primary value, source-integrity blocker, hard warning, or malformed public contract still withholds;
- every list item and detail response has reliability, and the list/detail labels match;
- finite legacy and malformed-reliability fallbacks use numeric derived ratios, while a withheld artifact uses this non-fabricated shape:

```python
{
    "label": "Low",
    "accounting_label": "Low",
    "scenario_label": "Low",
    "model_cap": "Low",
    "source_cap": "Low",
    "accounting_impact_ratio": None,
    "scenario_movement_ratio": None,
    "reasons": ["VALUATION_WITHHELD"],
}
```

Unknown reason strings and private warning/error text must never be echoed. Only explicitly allowlisted public reason codes may survive.

Add a configuration test that reloads or invokes the router with `FINSIGHT_US_VALUATION_DATA_ROOT` set to a temporary directory and proves both endpoints read that directory. Also prove the unset default still resolves to `backend/app/data/us_valuations`.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_bridge_policy_artifacts.py \
  backend/tests/test_automated_review.py \
  backend/tests/test_us_valuation.py \
  backend/tests/test_api.py \
  -k 'reliability or artifact or us_valuation'
```

- [ ] **Step 3: Add an allowlisted public reliability DTO**

In `artifacts.py`, validate exactly the fields produced by `ReliabilityAssessment.as_dict()`. Copy only those keys into the canonical `public_result()`. Do not expose raw statement values or private field-by-field evidence. Dispatch equity-level results through the existing `public_equity_artifact()` first, then apply the same schema, automated review, sanitizer, and reliability DTO used by FCFF.

For a finite legacy 1.0 artifact with no reliability object, derive its scenario movement from `scenario_range`, set accounting impact to `0.0`, set all qualitative fields and the overall label to `Low`, and include `LEGACY_ARTIFACT_NOT_REGENERATED`. For a finite 1.1 artifact with malformed or missing reliability, use the same conservative numeric fallback with `RELIABILITY_PAYLOAD_INVALID`. A withheld artifact remains scrubbed and receives only the canonical null-ratio `VALUATION_WITHHELD` DTO.

Validate bridge arithmetic and canonical FCFF agreement, but remove the historical 1% public rejection for regenerated 1.1 `bounded_review` artifacts. Preserve the existing fail-closed handling of historical 1.0 artifacts that were already marked withheld, and preserve all genuine source-integrity, identity, non-finite, and model-policy blockers.

Allow only the bridge-policy reason codes, `INTERIM_FFO_ROUTE`, `LEGACY_ARTIFACT_NOT_REGENERATED`, `RELIABILITY_PAYLOAD_INVALID`, and `VALUATION_WITHHELD`. Any unknown or private reason makes the incoming reliability payload invalid and is replaced by the generic fallback; it is never echoed.

- [ ] **Step 4: Correct primary-versus-supporting model review semantics**

In `automated_review.py`, use `model_policy.primary` to distinguish the main valuation from supporting checks. A finite supporting model in `review_required` state, including EPV, adds a public caveat but is not a blocking reason. A finite primary model in `review_required` state also remains visible as a caveated valuation when the artifact has no errors, hard warning, source-integrity failure, or malformed contract. A withheld primary model, a missing/non-finite primary value, an unknown model state, or a genuine hard warning remains blocking. Scenario checks continue to validate every scenario and never weaken a withheld or malformed scenario.

Do not special-case a ticker or EPV by name: the rule is based on declared primary/supporting role. Preserve deterministic reason ordering and add focused tests in `test_automated_review.py`.

- [ ] **Step 5: Expose the same label from list and detail APIs**

Make `list_us_valuations()` sanitize each artifact before reading its summary. Add:

```python
"reliability": sanitized["reliability"]["label"]
```

Do not read raw, unsanitized reliability fields into the list response.

Resolve `DATA_ROOT` from `FINSIGHT_US_VALUATION_DATA_ROOT` at process startup, falling back to the existing package-relative directory. This override changes only which already-generated JSON files a deliberately configured local process reads; it must not write, download, or mutate artifacts.

- [ ] **Step 6: Run focused, full, and direct API checks**

```bash
PYTHONPATH=backend pytest -q \
  backend/tests/test_bridge_policy_artifacts.py \
  backend/tests/test_automated_review.py \
  backend/tests/test_us_valuation.py \
  backend/tests/test_api.py
PYTHONPATH=backend pytest -q backend/tests
```

Then use FastAPI's existing test client or app runner to request:

```text
GET /api/us-valuations
GET /api/us-valuations/MSFT
```

Capture one list item and one detail response showing the same reliability label and finite value.

- [ ] **Step 7: Commit**

```bash
git add \
  backend/app/us_valuation/artifacts.py \
  backend/app/us_valuation/automated_review.py \
  backend/app/routers/us_valuations.py \
  backend/tests/test_bridge_policy_artifacts.py \
  backend/tests/test_automated_review.py \
  backend/tests/test_us_valuation.py \
  backend/tests/test_api.py
git diff --cached --check
git commit -m "feat: expose valuation reliability safely"
```

**Gate:** The real API exposes one safe three-level reliability label consistently, and low reliability does not erase an otherwise finite value.

---

### Task 6: Replay the difficult corpus and audit threshold fairness

**Files:**

- Create: `scripts/run_reliability_pipeline_replay.py`
- Create: `backend/tests/test_reliability_pipeline_replay.py`
- Create: `docs/audit/04-reliability-policy-replay.md`

**Interfaces:**

- Consumes the preserved private artifacts and matching `sec-cache/CIK*-companyfacts.json`, `CIK*-submissions.json`, metadata files, and optional `filing-evidence-used.json` under the immutable corpus.
- Rebuilds each valid company through `build_us_valuation()` using the artifact's original valuation date and source manifest, with network access disabled.
- Produces a non-serving JSON report, per-company private artifacts, and flat `public/{TICKER}.json` artifacts under a fresh `output/` directory so a local API process can consume them without copying into the serving tree.
- Reports source-integrity failures, valid/invalid input counts, before/after numeric counts, reliability/fallback counts, impact buckets, near-boundary cases, remaining blockers, and serving-tree hashes.

- [ ] **Step 1: Write failing replay-schema tests**

Build a tiny corpus from the existing reduced SEC fixtures and require these summary keys:

```python
{
    "input_candidate_count",
    "valid_private_count",
    "invalid_input_count",
    "numeric_before_count",
    "numeric_after_count",
    "reliability_counts",
    "fallback_level_counts",
    "accounting_impact_buckets",
    "near_boundary_cases",
    "remaining_blocker_counts",
    "source_integrity_failure_count",
    "build_error_count",
    "unsafe_promotion_count",
    "serving_artifacts_changed",
}
```

Assert the test calls the real `build_us_valuation()` path rather than mocking it. Define accounting near-boundary as within `0.005` absolute ratio of `0.05` or `0.20`, and scenario near-boundary as within `0.005` of `0.20` or `0.40`. Require explicit accounting and scenario bucket counts on both sides of every boundary. Require every count to name its denominator in the Markdown output. Add negative tests proving the runner rejects an output directory inside `backend/app/data/us_valuations`, rejects a source whose SHA-256 does not match the private artifact's source manifest, rejects mismatched optional filing-evidence, reports a public-shaped input as invalid rather than building it, and cannot enter a network path.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_reliability_pipeline_replay.py
```

Expected: collection fails because `scripts/run_reliability_pipeline_replay.py` does not exist.

- [ ] **Step 3: Implement an offline regeneration runner**

The runner must:

1. discover exactly one `valuation-private.json` in each candidate directory while excluding `sec-cache/`;
2. validate private schema shape, canonical ticker/CIK, valuation date, and source manifest before using a candidate;
3. resolve its CIK to the cached Companyfacts and submissions files and, when declared, the exact `filing-evidence-used.json`;
4. recompute SHA-256 for every declared source file and refuse that company if any hash differs from the artifact's manifest;
5. call the real `build_us_valuation()` with the cached JSON, original valuation date, and source manifest, with no download or network fallback;
6. call `public_result()` on the rebuilt private result and fail that company if public sanitization rejects it;
7. write per-company regenerated output only beneath the requested fresh non-serving output directory;
8. hash `backend/app/data/us_valuations` before and after the run and set `serving_artifacts_changed` from the comparison; and
9. make network access structurally unavailable and prove that guard in tests; and
10. exit non-zero for source-integrity failures, build errors, unsafe promotions, or serving-tree changes, while still writing the report.

`numeric_before_count` and `numeric_after_count` mean companies with a finite public intrinsic value, not merely a directory or a parsed filing. Count reliability only among after-run numeric companies. Count annual carried-forward use from private availability metadata. Count unresolved withholding reasons separately. Report accounting impact buckets around 5% and 20%, scenario movement buckets around 20% and 40%, and literal near-boundary company examples. The runner must be deterministic for the same immutable inputs and must not alter 5%, 20%, or 40%, promote Arelle shadow candidates to production authority, or convert unresolved conflicts to estimates.

- [ ] **Step 4: Run focused and full tests**

```bash
PYTHONPATH=backend pytest -q backend/tests/test_reliability_pipeline_replay.py
PYTHONPATH=backend pytest -q backend/tests
```

- [ ] **Step 5: Reconfirm the Arelle/bridge baseline, then rebuild from cached SEC evidence**

First rerun the evidence-only baseline in a new directory:

```bash
python3 scripts/run_bridge_policy_shadow.py \
  --input-root /Users/carlosconda/Desktop/Investing\ Application/output/legacy-fcff-bridge-recovery \
  --output-dir output/bridge-policy-replay-20260814
```

Then run the actual valuation regeneration in a different new directory:

```bash
python3 scripts/run_reliability_pipeline_replay.py \
  --input-root /Users/carlosconda/Desktop/Investing\ Application/output/legacy-fcff-bridge-recovery \
  --output-dir output/reliability-pipeline-replay-20260814
```

Expected input denominator: 106 candidate directories, consisting of 104 valid private artifacts and two known invalid public-shaped cases. This is an expected input shape, not a required success count; record any observed difference. Record the exact number attempted, valid, invalid, source-verified, numeric before/after, `High`/`Medium`/`Low`, carried-forward usage, remaining blockers, near-boundary companies, source-integrity failures, build errors, unsafe promotions, and serving-artifact changes.

- [ ] **Step 6: Write the replay audit**

Create `docs/audit/04-reliability-policy-replay.md`. Explain results simply using `X out of Y, selected because Z`. Separate:

- verified improvement;
- remaining blockers;
- evidence that thresholds appear fair;
- evidence that a threshold may be unfair; and
- unverified claims requiring the 500-company replay or backtest.

If a threshold appears unfair, stop before changing it and present the evidence to the user.

- [ ] **Step 7: Commit**

```bash
git add \
  scripts/run_reliability_pipeline_replay.py \
  backend/tests/test_reliability_pipeline_replay.py \
  docs/audit/04-reliability-policy-replay.md
git diff --cached --check
git commit -m "test: replay reliability policy on difficult filings"
```

**Gate:** The replay truthfully shows what improved, what remains blocked, and whether the V1 thresholds—not merely extraction—are producing questionable grades.

---

### Task 7: Phase-level real verification and handoff

**Files:**

- Create: `docs/audit/05-reliability-pipeline-phase-verification.md`
- Modify: `docs/plans/ROADMAP.md`
- Modify: `docs/plans/PRODUCTION-BACKLOG.md`
- Modify: `docs/learnings/INDEX.md` only if a non-obvious learning was recorded

**Interfaces:**

- Consumes: Tasks 1–6 and their commits/evidence.
- Produces: one reproducible phase-verification record and an honest next-phase status.

- [ ] **Step 1: Run final automated verification**

```bash
PYTHONPATH=backend pytest -q backend/tests
git diff --check
git status --short
```

- [ ] **Step 2: Exercise the real consumer path**

Start the backend in one terminal with the same hermetic environment used by the test suite:

```bash
APP_ENV=test \
JWT_ACCESS_SECRET=test-access-secret \
JWT_REFRESH_SECRET=test-refresh-secret \
PGHOST=localhost \
PGPORT=5432 \
PGUSER=test \
PGPASSWORD=test \
PGDATABASE=test \
MINIO_ENDPOINT=http://localhost:9000 \
MINIO_ROOT_USER=test \
MINIO_ROOT_PASSWORD=test \
MINIO_BUCKET=test \
FINSIGHT_US_VALUATION_DATA_ROOT=output/reliability-pipeline-replay-20260814/public \
PYTHONPATH=backend \
uvicorn app.main:app --host 127.0.0.1 --port 8011
```

In another terminal, request the list and three details selected from the replay report:

```bash
curl --fail --silent http://127.0.0.1:8011/api/us-valuations
curl --fail --silent http://127.0.0.1:8011/api/us-valuations/AMZN
```

`AMZN` is the known corpus identity check. Repeat the detail request using the exact tickers recorded in `docs/audit/04-reliability-policy-replay.md` for up to three category details: the first finite numeric company, one annual-carried-forward company, and one `Low` company. Record those literal curl commands in the phase audit. Confirm list/detail labels match and that the numeric selection is finite. If any requested category has no member, do not invent one: mark that gate `partial` and record `0 out of Y`. Do not substitute direct function calls for this HTTP check.

- [ ] **Step 3: Re-check serving boundaries**

Hash or compare `backend/app/data/us_valuations` before and after the replay. Confirm the replay changed zero serving artifacts. Confirm Arelle is absent from FastAPI imports:

```bash
rg -n "arelle" backend/app/main.py backend/app/routers backend/app/deps.py
```

Expected: no live-serving import.

- [ ] **Step 4: Record phase evidence**

Write `docs/audit/05-reliability-pipeline-phase-verification.md` with commands, outputs, API samples, replay paths, failures, skipped checks, and exact remaining gaps. Status must be `verified — user confirmation needed`, `partial`, or `blocked`; never self-declare done.

- [ ] **Step 5: Update roadmap and backlog honestly**

Mark Phase 1 complete only if every gate has evidence. Keep the canonical 500 manifest, specialist lanes, current-price comparisons, full-universe replay, and point-in-time backtest in their next phases. Park incidental defects with why and an unblock condition.

- [ ] **Step 6: Commit and push the verified phase**

```bash
git add docs/audit/05-reliability-pipeline-phase-verification.md docs/plans docs/learnings
git diff --cached --check
git commit -m "docs: verify reliability pipeline phase"
git push origin feat/whole-universe-greenlight
```

**Gate:** The backend behavior is exercised through the real API, evidence is durable, remaining work is explicit, and the user receives a simple confirmation request.
