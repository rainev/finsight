"""FOD2 contracts for free XBRL-US DQC diagnostics."""

from __future__ import annotations

from app.us_valuation.dqc_diagnostics import evaluate_dqc


def test_dqc_rejects_a_taxonomy_year_mismatch_fail_closed() -> None:
    result = evaluate_dqc(
        diagnostics=[{"code": "DQC.US.001", "severity": "error", "message": "fixture"}],
        taxonomy_year=2025,
        ruleset_metadata={"taxonomy_year": 2024, "ruleset": "xbrl-us-dqc"},
    )

    assert result.status == "unavailable"
    assert result.reason_codes == ("DQC_TAXONOMY_YEAR_MISMATCH",)
    assert result.value is None


def test_dqc_diagnostics_can_lower_confidence_but_never_create_a_fact_value() -> None:
    result = evaluate_dqc(
        diagnostics=[{"code": "DQC.US.001", "severity": "error", "message": "fixture"}],
        taxonomy_year=2025,
        ruleset_metadata={"taxonomy_year": 2025, "ruleset": "xbrl-us-dqc"},
    )

    assert result.status == "diagnostic_error"
    assert result.reason_codes == ("DQC.US.001",)
    assert result.value is None
    assert result.can_create_value is False
