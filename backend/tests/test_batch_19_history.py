from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_19 import BATCH_19_MANIFEST, BATCH_19_TICKERS
from app.us_valuation.batch_19_history import CONDITIONAL_TICKERS, EQUITY_EARNINGS_TICKERS, PASS_TICKERS, P, build_batch_19_history_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-19-sec-source-packets-20260830"
STRUCTURAL = ROOT / "output/batch-19-structural-sources-20260830"
EVENT = ROOT / "output/batch-19-event-sources-20260830-v2"


def _result(ticker: str):
    return build_batch_19_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT)


EXPECTED = {
    "GE": (33.33371787777517, 76.31214123864024, 150.89805259941875),
    "HUBB": (54.92294379145809, 166.6929200270177, 293.91223946790797),
    "ITW": (59.823056905648954, 112.3385864142071, 183.00712178651042),
    "J": (33.738404455018554, 77.92178234754333, 196.80254404986067),
    "MAS": (20.7376835412255, 35.88423877623827, 59.642985813439),
    "MMM": (0.0, 39.460337961525326, 85.13402233956532),
    "NDSN": (64.83778859814856, 131.76634292348268, 224.758239426562),
    "PCAR": (38.62742837945751, 82.67888418022667, 158.6190248806928),
    "PH": (168.4077188615264, 344.41280130660505, 566.2997603380239),
    "DE": (114.64752564894698, 265.4856470382269, 521.7570597554202),
}


def test_batch_19_exact_outcomes_ranges_and_reliability() -> None:
    rows = {ticker: _result(ticker) for ticker in BATCH_19_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS) == {"ITW", "J", "MAS", "NDSN"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == {"GE", "HUBB", "MMM", "PCAR", "PH", "DE"}
    for ticker, row in rows.items():
        values = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        assert values == pytest.approx(EXPECTED[ticker])
        assert 0.0 <= values[0] <= values[1] <= values[2]
        assert values[1] > 0.0
        assert row["history_reliability"]["label"] == "Low"


def test_operating_directions_and_3m_equity_floor() -> None:
    for ticker in P:
        states = _result(ticker)["scenario_rows"]
        assert states[0]["wacc"] > states[1]["wacc"] > states[2]["wacc"]
        assert states[0]["growth"] <= states[1]["growth"] <= states[2]["growth"]
        assert states[0]["conditional_value_per_share"] <= states[1]["conditional_value_per_share"] <= states[2]["conditional_value_per_share"]
    mmm = _result("MMM")
    assert mmm["scenario_rows"][0]["raw_value_per_share"] < 0.0
    assert mmm["scenario_range"]["low"] == 0.0
    assert mmm["scenario_range"]["base"] > 0.0


def test_cutoff_events_and_claims_are_bound_once() -> None:
    hubb = _result("HUBB")
    assert hubb["reported_inputs"]["ttm_revenue"] == 5_996_100_000.0
    assert hubb["reported_inputs"]["valuation_revenue"] == 6_489_300_000.0
    assert [row["value"] for row in hubb["source_ledger"]["event_sources"][-2:]] == [3_228_500_000.0, 3_475_100_000.0]
    itw = _result("ITW")
    assert itw["scenario_rows"][1]["cash_and_investments"] == 2_328_000_000.0
    assert itw["scenario_rows"][1]["debt_and_finance_leases"] == 11_194_000_000.0
    assert [row["reported_terms"] for row in itw["source_ledger"]["event_sources"][1:]][0]["aggregate_principal_usd"] == 1_500_000_000.0
    ndsn = _result("NDSN")
    assert ndsn["source_ledger"]["event_sources"][1]["reported_terms"]["reported_issuance_usd"] is None
    assert ndsn["scenario_rows"][1]["debt_and_finance_leases"] == 1_904_814_000.0
    ph = _result("PH")
    assert ph["scenario_rows"][1]["enterprise_value_overlay"] == 9_250_000_000.0
    assert ph["scenario_rows"][1]["debt_and_finance_leases"] == 16_619_000_000.0
    assert ph["scenario_rows"][1]["other_equity_claims"] == 1_508_000_000.0
    mmm = _result("MMM")
    assert mmm["scenario_rows"][1]["other_equity_claims"] == 9_809_000_000.0


def test_equity_routes_do_not_double_bridge_finance_or_insurance() -> None:
    for ticker in EQUITY_EARNINGS_TICKERS:
        row = _result(ticker)
        assert row["governed_assumptions"]["route_is_equity_level"] is True
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
    de = _result("DE")
    assert de["reported_inputs"]["ending_common_equity"] == 27_404_267_000.0
    assert de["source_ledger"]["event_sources"][2]["reported_terms"]["issuance_cost_equity_effect_usd"] == 1_733_000.0


def test_public_contract_safe_and_calculator_family() -> None:
    from run_batch_19_history import _public

    for issuer in BATCH_19_MANIFEST:
        result = _result(issuer.ticker)
        public = _public(issuer, result)
        raw = json.dumps(public)
        assert public["availability_type"] == result["availability_type"]
        assert public["scenario_range"]["base"] == result["scenario_range"]["base"]
        assert all(key not in raw for key in ("source_ledger", "model_trace", "reported_inputs"))
        view = calculator_view(public)
        assert view["model_family"] == ("equity_earnings" if issuer.ticker in EQUITY_EARNINGS_TICKERS else "operating")
        assert calculate(public, overrides={}, manual_price=None)["result"] == result["scenario_range"]


def test_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_19_history import run

    report = run(source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT, output_root=tmp_path / "b19")
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (4, 6, 0, 10)
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed"] is False
    assert report["withheld_register_changed"] is False


def test_arelle_outside_serving_imports() -> None:
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
