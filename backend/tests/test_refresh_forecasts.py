from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.us_valuation.forecast_evaluation import ForecastDatum
from app.us_valuation.forecast_vintage_store import ForecastVintageStore
from app.us_valuation.forecast_vintage_store import ForecastVintage
from app.us_valuation.refresh_forecasts import issue_recipe_vintage, refresh_forecast_tracking, track_company_refresh
from app.us_valuation.sustainable_inputs import SourceEvidence


def _recipe_file(tmp_path: Path) -> tuple[dict, dict[str, SourceEvidence]]:
    evidence: dict[str, SourceEvidence] = {}
    schedule: dict[str, list[dict]] = {}
    for scenario, value in (("bear", 80.0), ("base", 100.0), ("bull", 120.0)):
        source_id = f"forecast-{scenario}"
        evidence[source_id] = SourceEvidence(
            source_id=source_id,
            cik="0000000001",
            field="cash_fcff",
            unit="USD",
            reported_value=value,
            period_end="2027-03-31",
            filing_date="2026-08-01",
            reported_vs_estimated="estimated",
        )
        schedule[scenario] = [{
            "metric": "cash_fcff",
            "fiscal_period": "2027Q1",
            "value": value,
            "source_id": source_id,
        }]
    recipe = {
        "recipe_version": "cached-recipe-1",
        "model_version": "cash-model-1",
        "policy_version": "cash-policy-1",
        "forecast_schedule": schedule,
        "provenance": {"source_hashes": {key: "a" * 64 for key in evidence}},
    }
    path = tmp_path / "cached-recipe.json"
    path.write_text(json.dumps(recipe), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8")), evidence


def _actual(value: float, source_id: str, filing_date: str) -> ForecastDatum:
    return ForecastDatum(
        "cash_fcff",
        "2027Q1",
        value,
        SourceEvidence(
            source_id=source_id,
            cik="0000000001",
            field="cash_fcff",
            unit="USD",
            reported_value=value,
            period_end="2027-03-31",
            filing_date=filing_date,
        ),
    )


def test_issue_recipe_vintage_uses_explicit_cutoff_and_cached_schedule(tmp_path: Path) -> None:
    recipe, evidence = _recipe_file(tmp_path)
    store = ForecastVintageStore(tmp_path / "forecast-store")

    result = issue_recipe_vintage(
        store=store,
        recipe=recipe,
        vintage_id="ACME-2026-08-01",
        company_id="ACME",
        company_cik="0000000001",
        company_family="industrial",
        model_version=recipe["model_version"],
        policy_version=recipe["policy_version"],
        issued_at="2026-08-01",
        source_cutoff="2026-08-01",
        source_evidence=evidence,
    )

    vintage = store.read_vintage("ACME-2026-08-01")
    assert result["review_only"] is True
    assert vintage.model_version == "cash-model-1"
    assert vintage.policy_version == "cash-policy-1"
    assert vintage.fiscal_periods == ("2027Q1",)
    assert all(row.metric == "cash_fcff" for row in vintage.scenarios["base"])
    assert result["vintage"]["frozen_cutoff"] == "2026-08-01"


def test_tracking_without_later_actual_is_explicit_historical_limitation(tmp_path: Path) -> None:
    recipe, evidence = _recipe_file(tmp_path)
    result = refresh_forecast_tracking(
        store=ForecastVintageStore(tmp_path / "store"),
        recipe=recipe,
        vintage_id="ACME-2026-08-01",
        company_id="ACME",
        company_cik="0000000001",
        company_family="industrial",
        model_version="cash-model-1",
        policy_version="cash-policy-1",
        issued_at="2026-08-01",
        source_cutoff="2026-08-01",
        source_evidence=evidence,
    )
    assert result["evaluation"]["status"] == "prospective_tracking"
    assert result["evaluation"]["historical_comparison_claim"] is False
    assert result["policy_change_applied"] is False
    assert result["recommendations"]


def test_actual_evaluation_cutoff_must_reach_issued_vintage(tmp_path: Path) -> None:
    recipe, evidence = _recipe_file(tmp_path)
    store = ForecastVintageStore(tmp_path / "store")
    issue_recipe_vintage(
        store=store,
        recipe=recipe,
        vintage_id="ACME-2026-09-08",
        company_id="ACME",
        company_cik="0000000001",
        company_family="industrial",
        model_version="cash-model-1",
        policy_version="cash-policy-1",
        issued_at="2026-09-08",
        source_cutoff="2026-08-14",
        source_evidence=evidence,
    )
    with pytest.raises(ValueError, match="issuance"):
        from app.us_valuation.forecast_vintage_store import evaluate_vintage
        evaluate_vintage(store.read_vintage("ACME-2026-09-08"), (), frozen_cutoff="2026-08-14")


def test_tracking_distinguishes_first_reported_restated_and_corporate_event(tmp_path: Path) -> None:
    recipe, evidence = _recipe_file(tmp_path)
    store = ForecastVintageStore(tmp_path / "store")
    first = refresh_forecast_tracking(
        store=store,
        recipe=recipe,
        vintage_id="ACME-2026-08-01",
        company_id="ACME",
        company_cik="0000000001",
        company_family="industrial",
        model_version="cash-model-1",
        policy_version="cash-policy-1",
        issued_at="2026-08-01",
        source_cutoff="2026-08-01",
        actuals=(_actual(105.0, "actual-1", "2027-05-01"),),
        actual_source_hashes={"actual-1": "b" * 64},
        actual_captured_at="2027-05-02",
        actual_cutoff="2027-05-02",
        source_evidence=evidence,
    )
    assert first["actual_capture"]["rows"][0]["status"] == "first_reported"
    assert first["evaluation"]["status"] == "historically_comparable"

    restated = refresh_forecast_tracking(
        store=store,
        recipe=recipe,
        vintage_id="ACME-2026-08-01",
        company_id="ACME",
        company_cik="0000000001",
        company_family="industrial",
        model_version="cash-model-1",
        policy_version="cash-policy-1",
        issued_at="2026-08-01",
        source_cutoff="2026-08-01",
        actuals=(_actual(120.0, "actual-2", "2027-06-01"),),
        actual_source_hashes={"actual-2": "c" * 64},
        actual_captured_at="2027-06-02",
        actual_cutoff="2027-06-02",
        corporate_event_periods=("2027Q1",),
        source_evidence=evidence,
    )
    assert restated["actual_capture"]["rows"][0]["status"] == "restated"
    assert restated["corporate_event_incomparability"] == ["2027Q1"]
    assert restated["evaluation"]["status"] == "historical_data_limitation"
    assert restated["policy_change_applied"] is False


def test_issue_rejects_missing_source_backing_or_implicit_dates(tmp_path: Path) -> None:
    recipe, evidence = _recipe_file(tmp_path)
    recipe["forecast_schedule"]["base"][0].pop("source_id")
    with pytest.raises(ValueError, match="source_id"):
        issue_recipe_vintage(
            store=ForecastVintageStore(tmp_path / "store"),
            recipe=recipe,
            vintage_id="ACME-2026-08-01",
            company_id="ACME",
            company_cik="0000000001",
            company_family="industrial",
            model_version="cash-model-1",
            policy_version="cash-policy-1",
            issued_at="2026-08-01",
            source_cutoff="2026-08-01",
            source_evidence=evidence,
        )


@pytest.mark.parametrize(
    ("ticker", "cik", "period_end"),
    [("ACN", "0001467373", "2026-05-31")],
)
def test_real_cached_recipe_is_enriched_into_forward_dated_vintage(
    tmp_path: Path, ticker: str, cik: str, period_end: str
) -> None:
    recipe = json.loads((Path("output/us-refresh-runtime/recipes") / f"{ticker}.json").read_text())
    store = ForecastVintageStore(tmp_path / ticker)
    ledger = {"period_end": period_end, "source_filing_date": "2026-08-14"}
    result = issue_recipe_vintage(
        store=store,
        recipe=recipe,
        vintage_id=f"{ticker}-2026-09-08",
        company_id=ticker,
        company_cik=cik,
        company_family="public_company",
        issued_at="2026-09-08",
        source_cutoff="2026-08-14",
        ledger=ledger,
    )
    vintage = store.read_vintage(f"{ticker}-2026-09-08")
    assert result["vintage"]["frozen_cutoff"] == "2026-08-14"
    assert vintage.issued_at == "2026-09-08"
    assert vintage.fiscal_periods[0] == "TTM:2027-05-31"
    assert all(row.source.filing_date == "2026-09-08" for row in vintage.scenarios["base"])
    assert vintage.scenarios["base"][0].source.period_start == "2026-06-01"
    assert result["limitations"] == []


def test_cash_schedule_requires_explicit_metric_policy(tmp_path: Path) -> None:
    recipe = json.loads((Path("output/us-refresh-runtime/recipes") / "AAPL.json").read_text())
    with pytest.raises(ValueError, match="forecast_metric"):
        issue_recipe_vintage(
            store=ForecastVintageStore(tmp_path / "AAPL"),
            recipe=recipe,
            vintage_id="AAPL-2026-09-08",
            company_id="AAPL",
            company_cik="0000320193",
            company_family="public_company",
            issued_at="2026-09-08",
            source_cutoff="2026-08-14",
            ledger={"period_end": "2026-06-27", "source_filing_date": "2026-08-14"},
        )


def test_company_coordinator_with_synthetic_future_actual_evaluates_prior_before_issuing_next(tmp_path: Path) -> None:
    # Real cached recipe, deliberately synthetic 2027 actual. This is an
    # ordering regression test, not evidence of a historical track record.
    recipe = json.loads((Path("output/us-refresh-runtime/recipes") / "ACN.json").read_text())
    store = ForecastVintageStore(tmp_path / "ACN")
    initial_ledger = {"period_end": "2026-05-31", "source_filing_date": "2026-08-14"}
    issue_recipe_vintage(
        store=store,
        recipe=recipe,
        ledger=initial_ledger,
        vintage_id="ACN-2026-09-08",
        company_id="ACN",
        company_cik="0001467373",
        company_family="public_company",
        issued_at="2026-09-08",
        source_cutoff="2026-08-14",
    )
    current_ledger = {
        "period_end": "2027-05-31",
        "filing_date": "2027-06-15",
        "ttm_cash_fcff": 13_000_000_000.0,
        "reported_sources": {
            "cash_fcff": {
                "source_id": "acn-current-cash",
                "cik": "0001467373",
                "field": "cash_fcff",
                "unit": "USD",
                "reported_value": 13_000_000_000.0,
                "period_end": "2027-05-31",
                "period_start": "2026-06-01",
                "filing_date": "2027-06-15",
            }
        },
    }
    report = track_company_refresh(
        store=store,
        recipe=recipe,
        ledger=current_ledger,
        issued_at="2027-06-20",
        source_cutoff="2027-06-15",
        company_id="ACN",
        company_cik="0001467373",
        company_family="public_company",
        vintage_id="ACN-2027-06-20",
    )
    assert report["prior_vintage_id"] == "ACN-2026-09-08"
    assert report["prior_evaluation"]["status"] == "historically_comparable"
    assert report["new_vintage"]["vintage"]["vintage_id"] == "ACN-2027-06-20"
    assert report["prior_evaluation"]["scenario_evaluations"][0]["comparisons"][0]["fiscal_period"].startswith("TTM:2027-05-31")
    assert report["new_vintage"]["vintage"]["fiscal_periods"][0].startswith("TTM:2028-05-31")
    assert list((store.root / "tracking").glob("ACN-2027-06-20-*.json"))
