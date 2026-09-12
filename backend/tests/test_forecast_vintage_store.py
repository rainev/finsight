import json
from pathlib import Path

import pytest

from app.us_valuation.forecast_evaluation import ForecastDatum
from app.us_valuation.forecast_vintage_store import (
    ForecastVintage,
    ForecastVintageStore,
    evaluate_vintage,
    summarize_coverage,
)
from app.us_valuation.sustainable_inputs import SourceEvidence


def _source(value: float, source_id: str, filing_date: str, *, estimated: bool = False) -> SourceEvidence:
    return SourceEvidence(
        source_id=source_id,
        cik="0000000001",
        field="revenue",
        unit="USD",
        reported_value=value,
        period_end="2026-12-31",
        filing_date=filing_date,
        reported_vs_estimated="estimated" if estimated else "reported",
    )


def _vintage() -> ForecastVintage:
    scenarios = {
        name: (ForecastDatum("revenue", "FY2026", value, _source(value, f"forecast-{name}", "2026-08-01", estimated=True)),)
        for name, value in (("bear", 90.0), ("base", 100.0), ("bull", 110.0))
    }
    return ForecastVintage(
        vintage_id="vintage-2026-08-01",
        company_id="ACME",
        company_cik="0000000001",
        company_family="software",
        model_version="model-1",
        policy_version="policy-1",
        issued_at="2026-08-01",
        frozen_cutoff="2026-08-01",
        scenarios=scenarios,
        source_hashes={f"forecast-{name}": "a" * 64 for name in ("bear", "base", "bull")},
    )


def test_vintage_is_immutable_on_disk_and_round_trips(tmp_path: Path) -> None:
    store = ForecastVintageStore(tmp_path)
    vintage = _vintage()
    receipt = store.write_vintage(vintage)
    assert Path(receipt.path).exists()
    assert store.read_vintage(vintage.vintage_id).as_dict() == vintage.as_dict()
    assert store.write_vintage(vintage).sha256 == receipt.sha256

    path = Path(receipt.path)
    path.write_text(path.read_text().replace("model-1", "tampered"))
    with pytest.raises(ValueError, match="digest mismatch"):
        store.read_vintage(vintage.vintage_id)
    with pytest.raises(ValueError, match="immutable forecast vintage drift"):
        store.write_vintage(vintage)


def test_actual_capture_preserves_first_reported_and_restated_evidence(tmp_path: Path) -> None:
    store = ForecastVintageStore(tmp_path)
    store.write_vintage(_vintage())
    first = ForecastDatum("revenue", "FY2026", 110.0, _source(110.0, "actual-1", "2027-02-15"))
    restated = ForecastDatum("revenue", "FY2026", 120.0, _source(120.0, "actual-2", "2027-03-01"))
    captured = store.capture_actuals("vintage-2026-08-01", (first,), {"actual-1": "b" * 64}, captured_at="2027-02-16", frozen_cutoff="2027-02-16")
    assert captured.rows[0].status == "first_reported"
    redisclosed = ForecastDatum("revenue", "FY2026", 110.0, _source(110.0, "actual-redisclosed", "2027-02-20"))
    repeated = store.capture_actuals("vintage-2026-08-01", (redisclosed,), {"actual-redisclosed": "d" * 64}, captured_at="2027-02-21", frozen_cutoff="2027-02-21")
    assert repeated.rows[0].status == "repeat"
    second = store.capture_actuals("vintage-2026-08-01", (restated,), {"actual-2": "c" * 64}, captured_at="2027-03-02", frozen_cutoff="2027-03-02")
    assert second.rows[0].status == "restated"
    assert store.select_actuals("vintage-2026-08-01", basis="first_reported")[0].value == 110.0
    assert store.select_actuals("vintage-2026-08-01", basis="latest")[0].value == 120.0

    earlier = ForecastDatum("revenue", "FY2026", 108.0, _source(108.0, "actual-earlier", "2027-01-15"))
    store.capture_actuals("vintage-2026-08-01", (earlier,), {"actual-earlier": "e" * 64}, captured_at="2027-03-03", frozen_cutoff="2027-03-03")
    assert store.select_actuals("vintage-2026-08-01", basis="first_reported")[0].value == 108.0


def test_evaluation_without_actual_evidence_is_prospective_only() -> None:
    evaluation = evaluate_vintage(_vintage(), (), frozen_cutoff="2026-08-01")
    assert evaluation.status == "prospective_tracking"
    assert evaluation.historical_comparison_claim is False
    assert evaluation.policy_change_applied is False
    assert "Capture subsequent" in evaluation.recommendations[0]


def test_evaluation_and_coverage_are_grouped_and_review_only() -> None:
    actual = ForecastDatum("revenue", "FY2026", 105.0, _source(105.0, "actual-1", "2027-02-15"))
    evaluation = evaluate_vintage(_vintage(), (actual,), frozen_cutoff="2027-02-15")
    assert evaluation.status == "historically_comparable"
    assert evaluation.historical_comparison_claim is True
    assert all(row.compared_count == 1 for row in evaluation.scenario_evaluations)
    assert all(row.comparisons[0].absolute_error is not None for row in evaluation.scenario_evaluations)
    assert evaluation.policy_change_applied is False

    report = summarize_coverage((evaluation,))
    assert report.company["ACME"]["vintage_count"] == 1
    assert report.family["software"]["historical_comparison_count"] == 1
    assert report.company["ACME"]["errors_by_metric_unit"]["revenue|USD"]["signed_error_total"] == pytest.approx(15.0)
    assert report.company["ACME"]["errors_by_metric_unit"]["revenue|USD"]["absolute_error_total"] == pytest.approx(25.0)
    assert report.company["ACME"]["interval_coverage"]["revenue|USD"]["coverage_ratio"] == 1.0
    assert report.company["ACME"]["scenarios"]["base"]["coverage_ratio"] == 1.0
    json.dumps(report.as_dict())


def test_vintage_rejects_forecast_source_after_issuance() -> None:
    with pytest.raises(ValueError, match="not available at issuance"):
        ForecastVintage(
            vintage_id="late-vintage",
            company_id="ACME",
            company_cik="0000000001",
            company_family="software",
            model_version="model-1",
            policy_version="policy-1",
            issued_at="2026-08-01",
            frozen_cutoff="2026-08-05",
            scenarios={"base": (ForecastDatum("revenue", "FY2026", 100.0, _source(100.0, "late", "2026-08-02", estimated=True)),)},
            source_hashes={"late": "a" * 64},
        )


def test_capture_rejects_source_identity_or_value_mismatch(tmp_path: Path) -> None:
    store = ForecastVintageStore(tmp_path)
    store.write_vintage(_vintage())
    bad_cik = ForecastDatum(
        "revenue", "FY2026", 110.0,
        SourceEvidence("actual-bad-cik", "0000000002", "revenue", "USD", 110.0, "2026-12-31", "2027-02-15"),
    )
    with pytest.raises(ValueError, match="CIK"):
        store.capture_actuals("vintage-2026-08-01", (bad_cik,), {"actual-bad-cik": "b" * 64}, captured_at="2027-02-16", frozen_cutoff="2027-02-16")

    bad_value = ForecastDatum("revenue", "FY2026", 111.0, _source(110.0, "actual-bad-value", "2027-02-15"))
    with pytest.raises(ValueError, match="reconcile"):
        store.capture_actuals("vintage-2026-08-01", (bad_value,), {"actual-bad-value": "c" * 64}, captured_at="2027-02-16", frozen_cutoff="2027-02-16")


def test_evaluation_requires_explicit_cutoff_and_exact_actual_source_period() -> None:
    actual = ForecastDatum("revenue", "FY2026", 105.0, _source(105.0, "actual", "2027-02-15"))
    with pytest.raises(TypeError):
        evaluate_vintage(_vintage(), (actual,))  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="source unit or period"):
        evaluate_vintage(
            _vintage(),
            (ForecastDatum("revenue", "FY2026", 105.0, SourceEvidence(
                source_id="actual",
                cik="0000000001",
                field="revenue",
                unit="shares",
                reported_value=105.0,
                period_end="2026-12-31",
                filing_date="2027-02-15",
            )),),
            frozen_cutoff="2027-02-15",
        )
