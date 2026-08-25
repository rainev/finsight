from __future__ import annotations

import pytest

from app.us_valuation.practical_policy import (
    BoundedAssumption,
    HardSafetyInput,
    InputRange,
    PRACTICAL_REASON_CODES,
    SourceTrace,
    ValueRange,
    decide_practical_outcome,
)


def _source(*, status: str = "estimated") -> SourceTrace:
    return SourceTrace(
        source_kind="filing_evidence",
        accession="0000320193-26-000020",
        policy_reference=None,
        period_end="2026-06-27",
        unit="USD",
        reported_vs_estimated=status,  # type: ignore[arg-type]
    )


def _assumption(*, material: bool = True) -> BoundedAssumption:
    return BoundedAssumption(
        name="conservative cash conversion",
        value_range=InputRange(0.80, 0.90, 1.00),
        sources=(_source(),),
        fallback_level="consolidated",
        basis="Reported TTM cash flow plus governed conservative range.",
        accounting_impact_ratio=0.12,
        scenario_impact_ratio=0.20,
        material_provisional=material,
    )


def test_bounded_assumption_produces_low_numeric_private_outcome() -> None:
    outcome = decide_practical_outcome(
        value_range=ValueRange(80.0, 100.0, 120.0),
        model_version="PRACTICAL-FCFF-1.0",
        model_selection_reason="Consolidated operating cash flows are source-linked.",
        assumptions=(_assumption(),),
        reason_codes=("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"),
        safety=HardSafetyInput(),
        reliability="Low",
    )

    assert outcome.publication_state == "review_required"
    assert outcome.value_range == ValueRange(80.0, 100.0, 120.0)
    assert outcome.reliability == "Low"
    assert outcome.assumptions[0].sources[0].accession == "0000320193-26-000020"
    assert outcome.assumptions[0].sources[0].reported_vs_estimated == "estimated"


@pytest.mark.parametrize(
    "safety",
    [
        HardSafetyInput(identity_valid=False),
        HardSafetyInput(claims_bounded=False),
        HardSafetyInput(evidence_consistent=False),
        HardSafetyInput(public_safe=False),
    ],
)
def test_hard_safety_failures_always_withhold(safety: HardSafetyInput) -> None:
    outcome = decide_practical_outcome(
        value_range=ValueRange(80.0, 100.0, 120.0),
        model_version="PRACTICAL-FCFF-1.0",
        model_selection_reason="Test.",
        assumptions=(_assumption(),),
        reason_codes=("CONSOLIDATED_MODEL_FALLBACK",),
        safety=safety,
    )
    assert outcome.publication_state == "withheld"
    assert outcome.value_range is None
    assert outcome.reliability is None
    assert outcome.hard_block_reasons


def test_missing_value_is_withheld_never_changed_to_zero() -> None:
    outcome = decide_practical_outcome(
        value_range=None,
        model_version="PRACTICAL-FCFF-1.0",
        model_selection_reason="Test.",
        assumptions=(),
        reason_codes=(),
        safety=HardSafetyInput(),
    )
    assert outcome.value_range is None
    assert outcome.hard_block_reasons == ("NONFINITE_OR_NONPOSITIVE_VALUE",)


@pytest.mark.parametrize("raw_range", [(0.0, 100.0, 120.0), (80.0, float("nan"), 120.0)])
def test_nonpositive_or_nonfinite_raw_base_is_hard_withheld(
    raw_range: tuple[float, float, float]
) -> None:
    outcome = decide_practical_outcome(
        value_range=raw_range,
        model_version="PRACTICAL-FCFF-1.0",
        model_selection_reason="Test.",
        assumptions=(),
        reason_codes=(),
        safety=HardSafetyInput(),
    )
    assert outcome.publication_state == "withheld"
    assert outcome.hard_block_reasons == ("NONFINITE_OR_NONPOSITIVE_VALUE",)


@pytest.mark.parametrize("values", [(0.0, 1.0, 2.0), (2.0, 1.0, 3.0)])
def test_invalid_value_range_is_rejected(values: tuple[float, float, float]) -> None:
    with pytest.raises(ValueError):
        ValueRange(*values)


def test_duplicate_reasons_and_untraced_assumption_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        decide_practical_outcome(
            value_range=ValueRange(80.0, 100.0, 120.0),
            model_version="PRACTICAL-FCFF-1.0",
            model_selection_reason="Test.",
            assumptions=(_assumption(),),
            reason_codes=("CONSOLIDATED_MODEL_FALLBACK", "CONSOLIDATED_MODEL_FALLBACK"),
            safety=HardSafetyInput(),
        )
    with pytest.raises(ValueError, match="sources"):
        BoundedAssumption(
            name="untraced",
            value_range=InputRange(1.0, 2.0, 3.0),
            sources=(),
            fallback_level="none",
            basis="none",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=0.0,
        )


def test_material_provisional_assumption_cannot_claim_medium_or_high() -> None:
    with pytest.raises(ValueError, match="require Low"):
        decide_practical_outcome(
            value_range=ValueRange(80.0, 100.0, 120.0),
            model_version="PRACTICAL-FCFF-1.0",
            model_selection_reason="Test.",
            assumptions=(_assumption(material=True),),
            reason_codes=("RD_LIFE_SENSITIVITY",),
            safety=HardSafetyInput(),
            reliability="Medium",
        )


def test_reason_code_contract_is_exact_and_public_facing() -> None:
    assert PRACTICAL_REASON_CODES == {
        "CONSOLIDATED_MODEL_FALLBACK",
        "RD_LIFE_SENSITIVITY",
        "CAPEX_CASH_CONVERSION_SENSITIVITY",
        "NORMALIZED_CYCLICAL_RANGE",
        "PROVISIONAL_BANK_CAPITAL_RANGE",
        "CONSOLIDATED_MIXED_UTILITY_FALLBACK",
        "REPORTED_AFFO_FALLBACK",
        "SPECIALIST_MODEL_UNCERTAINTY",
    }


def test_estimated_input_may_start_at_zero_but_not_use_zero_base() -> None:
    assumption = BoundedAssumption(
        name="unknown claim",
        value_range=InputRange(0.0, 50.0, 100.0),
        sources=(_source(status="estimated"),),
        fallback_level="same_filing_upper_bound",
        basis="Zero-to-reported-equity bound.",
        accounting_impact_ratio=0.20,
        scenario_impact_ratio=0.0,
        material_provisional=True,
    )
    assert assumption.value_range.low == 0.0
    assert assumption.value_range.base == 50.0
    with pytest.raises(ValueError, match="base cannot be zero"):
        BoundedAssumption(
            name="bad missing claim",
            value_range=InputRange(0.0, 0.0, 100.0),
            sources=(_source(status="estimated"),),
            fallback_level="bad",
            basis="Would silently substitute zero.",
            accounting_impact_ratio=0.0,
            scenario_impact_ratio=0.0,
        )


def test_governed_policy_source_does_not_claim_filing_provenance() -> None:
    source = SourceTrace(
        source_kind="governed_policy",
        accession=None,
        policy_reference="BATCH-01-PRACTICAL-1.0:bank-capital-sensitivity",
        period_end="2026-08-14",
        unit="ratio",
        reported_vs_estimated="estimated",
    )
    assert source.accession is None
    with pytest.raises(ValueError, match="cannot claim"):
        SourceTrace(
            source_kind="governed_policy",
            accession="0000320193-26-000020",
            policy_reference="policy",
            period_end="2026-08-14",
            unit="ratio",
            reported_vs_estimated="estimated",
        )
