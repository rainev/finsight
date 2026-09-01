from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_20 import BATCH_20_MANIFEST, BATCH_20_TICKERS
from app.us_valuation.batch_20_history import CONDITIONAL_TICKERS, EQUITY_EARNINGS_TICKERS, PASS_TICKERS, P, build_batch_20_history_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-20-sec-source-packets-20260830"
STRUCTURAL = ROOT / "output/batch-20-structural-sources-20260830"
EVENT = ROOT / "output/batch-20-event-sources-20260830"


def _result(ticker: str):
    return build_batch_20_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT)


EXPECTED = {
    "PNR": (22.219910091817944, 44.02102254181184, 74.35337016717862),
    "ROL": (12.899346533023857, 20.83936746966346, 33.682168798992876),
    "AOS": (30.082417499499776, 53.90931573480934, 83.83956195239817),
    "SNA": (121.88617613167021, 272.5405720233845, 529.4306816780638),
    "LUV": (7.3364448831580145, 13.796474255490876, 28.26566496690149),
    "SWK": (32.67476908075391, 58.256170022650714, 101.19235037220955),
    "UAL": (58.82569240067848, 106.23404575729593, 168.04607848194132),
    "UNP": (59.38493919279397, 110.26465081186957, 199.31367706337517),
    "CTAS": (45.81947013305615, 74.2186489721215, 114.55198826181042),
    "PAYX": (50.56830362801552, 83.96631361672581, 137.04997233440002),
}


def test_batch_20_exact_outcomes_ranges_and_reliability() -> None:
    rows = {ticker: _result(ticker) for ticker in BATCH_20_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS) == {"ROL", "SWK", "PAYX"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == {"PNR", "AOS", "SNA", "LUV", "UAL", "UNP", "CTAS"}
    for ticker, row in rows.items():
        values = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        assert values == pytest.approx(EXPECTED[ticker])
        assert 0.0 <= values[0] <= values[1] <= values[2] and values[1] > 0.0
        assert row["history_reliability"]["label"] == "Low"


def test_operating_directions_and_no_missing_zero_substitution() -> None:
    for ticker in P:
        row = _result(ticker)
        states = row["scenario_rows"]
        assert states[0]["wacc"] > states[1]["wacc"] > states[2]["wacc"]
        assert states[0]["growth"] <= states[1]["growth"] <= states[2]["growth"]
        assert states[0]["conditional_value_per_share"] <= states[1]["conditional_value_per_share"] <= states[2]["conditional_value_per_share"]
        assert all(state["raw_value_per_share"] > 0.0 for state in states)


def test_events_client_funds_and_divestiture_are_bound_once() -> None:
    pnr = _result("PNR")
    assert pnr["source_ledger"]["event_sources"][0]["reported_terms"]["purchase_price_usd"] == 1_425_000_000.0
    assert all(row["interest_expense"]["reported_vs_estimated"] == "estimated_from_current_interest_revenue_ratio" for row in pnr["source_ledger"]["annual_cash_sources"])
    aos = _result("AOS")
    assert aos["reported_inputs"]["valuation_revenue"] == aos["reported_inputs"]["ttm_revenue"] + 31_800_000.0
    assert aos["source_ledger"]["bridge_sources"][-2]["value"] == 135_908_573.0
    swk = _result("SWK")
    assert swk["scenario_rows"][1]["other_equity_claims"] == 351_200_000.0
    assert swk["source_ledger"]["event_sources"][1]["value"] == 1_814_700_000.0
    assert swk["scenario_rows"][1]["cash_and_investments"] == 592_400_000.0
    payx = _result("PAYX")
    assert payx["scenario_rows"][1]["other_equity_claims"] == 52_400_000.0
    assert payx["scenario_rows"][1]["cash_and_investments"] == 1_124_500_000.0
    assert "not treated as issuer-owned surplus" in payx["source_ledger"]["bridge_reconciliation"]["other_equity_claim_formula"]


def test_equity_airline_and_pending_deal_routes_are_honest() -> None:
    for ticker in EQUITY_EARNINGS_TICKERS:
        row = _result(ticker)
        assert row["governed_assumptions"]["route_is_equity_level"] is True
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
    luv = _result("LUV")
    assert luv["source_ledger"]["event_sources"][2]["reported_terms"]["amount_outstanding_usd"] == 0.0
    assert luv["source_ledger"]["event_sources"][0]["reported_terms"]["aircraft_purchase_commitments_usd"] == 14_800_000_000.0
    assert _result("UAL")["source_ledger"]["event_sources"][1]["value"] == 19_000_000_000.0
    assert _result("UNP")["source_ledger"]["event_sources"][0]["reported_terms"]["expected_cash_consideration_usd"] == 20_000_000_000.0
    assert _result("CTAS")["source_ledger"]["event_sources"][0]["reported_terms"]["transaction_value_usd"] == 5_500_000_000.0


def test_public_contract_safe_and_calculator_family() -> None:
    from run_batch_20_history import _public

    for issuer in BATCH_20_MANIFEST:
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
    from run_batch_20_history import run

    report = run(source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT, output_root=tmp_path / "b20")
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (3, 7, 0, 10)
    assert report["serving_artifacts_changed"] is False and report["watchlist_changed"] is False and report["withheld_register_changed"] is False


def test_arelle_outside_serving_imports() -> None:
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
