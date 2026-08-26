from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.us_valuation.artifacts import public_result
from app.us_valuation.xbrl import CompanyFactsNormalizer
from app.us_valuation.history import (
    HISTORY_POLICY_VERSION,
    HistoryObservation,
    build_equity_history_profile,
    build_operating_history_profile,
    material_dependency_requires_conditional,
    summarize_history_metric,
)
from app.us_valuation.pipeline import build_us_valuation


FIXTURES = Path(__file__).parent / "fixtures" / "us"


def _source(year: int, concept: str, value: float, unit: str = "USD") -> dict:
    return {
        "field": concept,
        "concept": concept,
        "unit": unit,
        "value": value,
        "accession": f"0000000001-{year % 100:02d}-000001",
        "form": "10-K",
        "filed": f"{year + 1}-02-15",
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
        "fiscal_year": year,
        "fiscal_period": "FY",
    }


def _annual_row(year: int, revenue: float, margin: float) -> dict:
    operating_income = revenue * margin
    values = {
        "revenue": revenue,
        "operating_income": operating_income,
        "pretax_income": operating_income,
        "income_tax": operating_income * 0.21,
        "depreciation_amortization": revenue * 0.04,
        "capital_expenditures": revenue * 0.05,
    }
    return {
        "period_end": f"{year}-12-31",
        "fiscal_year": year,
        "values": values,
        "sources": {
            name: _source(year, name, value)
            for name, value in values.items()
        },
    }


def _operating_financials(years: range) -> dict:
    annual = [
        _annual_row(year, 100.0 * 1.08 ** index, 0.10 + index * 0.01)
        for index, year in enumerate(years)
    ]
    latest = annual[-1]
    ttm_revenue = latest["values"]["revenue"] * 1.05
    ttm_values = {
        **latest["values"],
        "revenue": ttm_revenue,
        "operating_income": ttm_revenue * 0.15,
    }
    return {
        "annual": annual,
        "ttm": {
            "period_end": "2026-06-30",
            "source_cutoff_date": "2026-08-14",
            "values": ttm_values,
            "sources": {
                name: {
                    "sources": [_source(2025, name, value)],
                    "period_role": "operating_ttm",
                }
                for name, value in ttm_values.items()
                if name in {"revenue", "operating_income", "pretax_income", "income_tax", "depreciation_amortization", "capital_expenditures"}
            },
        },
        "normalized": {
            "revenue_ttm_history": [
                {
                    "period_end": "2025-06-30",
                    "value": latest["values"]["revenue"],
                    "sources": [_source(2024, "revenue", latest["values"]["revenue"])],
                }
            ]
        },
    }


def _duration_fact(year: int, value: float, *, unit: str = "USD") -> dict:
    return {
        "val": value,
        "fy": year,
        "fp": "FY",
        "form": "10-K",
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
        "filed": f"{year + 1}-02-15",
        "accn": f"0000000001-{year % 100:02d}-000001",
        "unit": unit,
    }


def _instant_fact(year: int, value: float) -> dict:
    row = _duration_fact(year, value)
    row.pop("start")
    return row


def _concept(rows: list[dict], unit: str = "USD") -> dict:
    return {"units": {unit: rows}}


def test_current_including_assessed_tax_revenue_beats_stale_legacy_revenue() -> None:
    current = _duration_fact(2025, 120.0)
    current.update({"start": "2025-01-01", "end": "2025-12-31"})
    stale = _duration_fact(2018, 80.0)
    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerIncludingAssessedTax": _concept([current]),
                "Revenues": _concept([stale]),
            }
        }
    }
    normalizer = CompanyFactsNormalizer(facts, fiscal_year_end="1231", as_of_date="2026-08-14")
    selected = normalizer.annual_series("revenue", 1)[0]
    assert selected.value == 120.0
    assert selected.concept == "RevenueFromContractWithCustomerIncludingAssessedTax"


def test_history_metric_uses_percentiles_after_four_observations() -> None:
    rows = tuple(
        HistoryObservation(
            period_role="annual",
            period_end=f"202{index}-12-31",
            fiscal_year=2020 + index,
            value=value,
            unit="ratio",
            formula="fixture",
            sources=(_source(2020 + index, "metric", value),),
        )
        for index, value in enumerate((0.10, 0.20, 0.30, 0.40), start=1)
    )
    metric = summarize_history_metric("metric", rows)
    assert metric is not None
    assert metric.low == pytest.approx(0.175)
    assert metric.base == pytest.approx(0.25)
    assert metric.high == pytest.approx(0.325)


def test_operating_profile_uses_ttm_and_only_latest_five_annual_periods() -> None:
    profile = build_operating_history_profile(
        _operating_financials(range(2019, 2026)),
        valuation_date="2026-08-14",
    )
    assert profile.policy_version == HISTORY_POLICY_VERSION
    assert profile.history_years_used == 5
    assert profile.annual_periods == tuple(f"{year}-12-31" for year in range(2021, 2026))
    assert profile.full_history is True
    growth = profile.metric("revenue_growth")
    margin = profile.metric("operating_margin")
    assert growth is not None and any(row.period_role == "operating_ttm" for row in growth.observations)
    assert margin is not None and margin.base > 0


def test_insufficient_history_is_explicit_policy_fallback() -> None:
    profile = build_operating_history_profile(
        _operating_financials(range(2024, 2026)),
        valuation_date="2026-08-14",
    )
    assert profile.full_history is False
    assert profile.public_metadata() == {
        "history_policy_version": HISTORY_POLICY_VERSION,
        "history_years_used": 2,
        "normalization_basis": "insufficient_company_history_policy_fallback",
        "assumption_source_mix": "reported_history_and_finsight_policy",
    }


def test_cash_history_does_not_count_ttm_twice_when_it_is_the_latest_fy() -> None:
    from app.us_valuation.history import build_cash_fcff_history_profile

    annual=[]
    for year,margin in ((2022,.03),(2023,.04),(2024,.05),(2025,.06)):
        revenue=100.0
        annual.append({
            "period_end": f"{year}-12-31",
            "cash_fcff": revenue*margin,
            "revenue": {"value": revenue, "fiscal_year": year, "sources": [_source(year,"revenue",revenue)]},
            "operating_cash_flow": {"sources": [_source(year,"ocf",revenue*margin)]},
            "capital_expenditures": {"sources": [_source(year,"capex",0.0)]},
            "interest_expense": {"sources": [_source(year,"interest",0.0)]},
            "income_tax": {"sources": [_source(year,"tax",0.0)]},
            "pretax_income": {"sources": [_source(year,"pretax",1.0)]},
        })
    annual.append(dict(annual[-1]))
    profile=build_cash_fcff_history_profile(annual_cash_states=annual,ttm_revenue=100.0,ttm_cash_fcff=99.0,ttm_period_end="2025-12-31",ttm_sources=(_source(2025,"ttm",99.0),),valuation_date="2026-08-14")
    metric=profile.metric("cash_conversion_margin")
    assert metric is not None
    assert len(metric.observations)==4
    assert all(row.period_role=="annual" for row in metric.observations)
    assert metric.base==pytest.approx(.045)


def test_materiality_rule_matches_publication_policy() -> None:
    assert not material_dependency_requires_conditional(impact_ratio=0.05)
    assert material_dependency_requires_conditional(impact_ratio=0.050001)
    assert material_dependency_requires_conditional(
        impact_ratio=0.0, changes_economic_object=True
    )
    assert material_dependency_requires_conditional(
        impact_ratio=0.0, determines_positive_value=True
    )


@pytest.mark.parametrize(
    ("model_name", "expected_metric"),
    [
        ("residual_income", "common_roe"),
        ("ddm", "dividend_growth"),
        ("ffo", "ffo_per_share"),
    ],
)
def test_equity_lanes_build_source_linked_history(
    model_name: str, expected_metric: str
) -> None:
    years = range(2021, 2026)
    gaap = {
        "NetIncomeLoss": _concept([_duration_fact(year, 100 + year) for year in years]),
        "CommonStockholdersEquity": _concept([_instant_fact(year, 1_000 + year) for year in range(2020, 2026)]),
        "PaymentsOfDividendsCommonStock": _concept([_duration_fact(year, 40 + year) for year in years]),
        "CommonStockDividendsPerShareCashPaid": _concept(
            [_duration_fact(year, 1.0 + (year - 2021) * 0.08, unit="USD/shares") for year in years],
            unit="USD/shares",
        ),
        "DepreciationDepletionAndAmortization": _concept([_duration_fact(year, 50 + year) for year in years]),
        "GainLossOnSaleOfProperty": _concept([_duration_fact(year, 5.0) for year in years]),
        "WeightedAverageNumberOfDilutedSharesOutstanding": _concept(
            [_duration_fact(year, 100.0, unit="shares") for year in years],
            unit="shares",
        ),
    }
    profile = build_equity_history_profile(
        {"facts": {"us-gaap": gaap}},
        model_name=model_name,
        valuation_date="2026-08-14",
    )
    assert profile.full_history is True
    assert profile.history_years_used == 5
    assert profile.metric(expected_metric) is not None


def test_real_operating_pipeline_exposes_only_safe_history_metadata() -> None:
    submissions = json.loads((FIXTURES / "aapl-submissions.json").read_text())
    companyfacts = json.loads((FIXTURES / "aapl-companyfacts.json").read_text())
    result = build_us_valuation(
        submissions=submissions,
        companyfacts=companyfacts,
        valuation_date="2026-07-31",
    )
    private_profile = result["forecast_assumptions"]["company_history_profile"]
    assert private_profile["metrics"]
    public = public_result(result, submissions)
    assert public["public_assumptions"]["history_years_used"] == 5
    assert public["public_assumptions"]["assumption_source_mix"] == "reported_and_company_history"
    assert "company_history_profile" not in json.dumps(public)
    assert "observations" not in json.dumps(public)
