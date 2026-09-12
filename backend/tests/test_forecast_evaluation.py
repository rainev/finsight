import json

import pytest

from app.us_valuation.forecast_evaluation import (
    ForecastDatum,
    compare_forecast_to_actuals,
    evaluate_forecast,
)
from app.us_valuation.sustainable_inputs import SourceEvidence


def _source(value: float, period_end: str = "2026-12-31", filing_date: str = "2026-08-01", *, estimated: bool = False) -> SourceEvidence:
    return SourceEvidence(
        source_id="sec:0000000001-26-000001",
        cik="0000000001",
        field="metric",
        unit="USD",
        reported_value=value,
        period_end=period_end,
        filing_date=filing_date,
        reported_vs_estimated="estimated" if estimated else "reported",
    )


def test_exact_period_match_returns_signed_and_absolute_errors() -> None:
    result = evaluate_forecast(
        (ForecastDatum("revenue", "FY2026", 100.0, _source(100.0, estimated=True)),),
        (ForecastDatum("revenue", "FY2026", 110.0, _source(110.0, filing_date="2027-02-15")),),
        frozen_cutoff="2027-03-01",
    )

    row = result.comparisons[0]
    assert row.status == "comparable"
    assert row.signed_error == 10.0  # actual minus forecast: actual beat forecast
    assert row.absolute_error == 10.0
    assert row.signed_error_ratio == pytest.approx(10.0 / 110.0)
    assert row.absolute_error_pct == pytest.approx(100.0 * 10.0 / 110.0)
    assert result.compared_count == 1
    assert result.incomparable_count == 0


def test_missing_fiscal_period_is_explicitly_incomparable_not_zero_actual() -> None:
    result = compare_forecast_to_actuals(
        ({"metric": "cash_fcff", "fiscal_period": "FY2026", "forecast_value": 20.0, "source": _source(20.0, estimated=True)},),
        ({"metric": "cash_fcff", "fiscal_period": "FY2025", "actual_value": 10.0, "source": _source(10.0, period_end="2025-12-31", filing_date="2027-02-15")},),
        frozen_cutoff="2027-03-01",
    )

    row = result.comparisons[0]
    assert row.status == "incomparable"
    assert row.actual_value is None
    assert row.absolute_error is None
    assert result.incomparable_count == 1


def test_zero_actual_is_finite_when_equal_and_undefined_when_nonzero_error() -> None:
    equal = evaluate_forecast(
        (ForecastDatum("earnings", "FY2026", 0.0, _source(0.0, estimated=True)),),
        (ForecastDatum("earnings", "FY2026", 0.0, _source(0.0, filing_date="2027-02-15")),),
        frozen_cutoff="2027-03-01",
    ).comparisons[0]
    nonzero = evaluate_forecast(
        (ForecastDatum("earnings", "FY2026", 5.0, _source(5.0, estimated=True)),),
        (ForecastDatum("earnings", "FY2026", 0.0, _source(0.0, filing_date="2027-02-15")),),
        frozen_cutoff="2027-03-01",
    ).comparisons[0]

    assert equal.signed_error_pct == 0.0
    assert equal.percentage_status == "zero_actual_equal"
    assert nonzero.absolute_error == 5.0
    assert nonzero.signed_error_pct is None
    assert nonzero.percentage_status == "zero_actual_nonzero_error"


def test_forecast_snapshot_is_immutable_and_evaluation_never_tunes() -> None:
    forecast = [ForecastDatum("margin", "FY2026", 0.2, _source(0.2, estimated=True))]
    result = evaluate_forecast(
        forecast,
        [ForecastDatum("margin", "FY2026", 0.25, _source(0.25, filing_date="2027-02-15"))],
        frozen_cutoff="2027-03-01",
    )
    forecast.append(ForecastDatum("margin", "FY2027", 0.3, _source(0.3, estimated=True)))

    assert len(result.forecast_snapshot) == 1
    assert result.tuning_applied is False
    assert result.status == "evaluated"
    json.dumps(result.as_dict())


def test_duplicate_period_keys_are_rejected_instead_of_silently_choosing_one() -> None:
    with pytest.raises(ValueError, match="forecast metric/fiscal_period keys"):
        evaluate_forecast(
            (
                ForecastDatum("revenue", "FY2026", 100.0, _source(100.0, estimated=True)),
                ForecastDatum("revenue", "FY2026", 101.0, _source(101.0, estimated=True)),
            ),
            (),
            frozen_cutoff="2027-03-01",
        )


def test_same_fiscal_label_with_different_source_period_is_incomparable() -> None:
    result = evaluate_forecast(
        (ForecastDatum("revenue", "FY2026", 100.0, _source(100.0, estimated=True)),),
        (ForecastDatum("revenue", "FY2026", 110.0, _source(110.0, period_end="2026-09-30", filing_date="2027-02-15")),),
        frozen_cutoff="2027-03-01",
    )
    assert result.comparisons[0].status == "incomparable"
    assert result.comparisons[0].reason == "source_period_mismatch"


def test_actual_must_be_filed_after_forecast_and_before_frozen_cutoff() -> None:
    before = evaluate_forecast(
        (ForecastDatum("revenue", "FY2026", 100.0, _source(100.0, filing_date="2027-02-15", estimated=True)),),
        (ForecastDatum("revenue", "FY2026", 110.0, _source(110.0, filing_date="2027-02-15")),),
        frozen_cutoff="2027-03-01",
    )
    assert before.comparisons[0].reason == "actual_not_subsequent"

    with pytest.raises(ValueError, match="after the frozen cutoff"):
        evaluate_forecast(
            (ForecastDatum("revenue", "FY2026", 100.0, _source(100.0, estimated=True)),),
            (ForecastDatum("revenue", "FY2026", 110.0, _source(110.0, filing_date="2027-04-01")),),
            frozen_cutoff="2027-03-01",
        )
