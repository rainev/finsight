from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_22 import BATCH_22_MANIFEST, BATCH_22_TICKERS
from app.us_valuation.batch_22_history import CONDITIONAL_TICKERS, PASS_TICKERS, P, build_batch_22_history_result
from app.us_valuation.calculator import calculate, calculator_view

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-22-sec-source-packets-20260831"
STRUCTURAL = ROOT / "output/batch-22-structural-sources-corrected-20260831"


def _result(ticker: str) -> dict:
    return build_batch_22_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL)


EXPECTED = {
    "HON": (60.78533467481803, 149.61398945604896, 277.0528047042256),
    "WM": (15.865646004518792, 65.5898953632795, 151.14499014377122),
    "IEX": (74.04009126419149, 120.80674026183728, 189.47743706380305),
    "JCI": (0.0, 18.65159591902528, 59.09507195457155),
    "ODFL": (30.55334862201182, 44.74554319109597, 83.24163324007851),
    "CPRT": (15.824519356584405, 24.571527012326726, 40.11767766167956),
    "LMT": (235.7669183234685, 417.6229098429032, 728.1934157008144),
    "WAB": (41.43363384256189, 110.65246913689661, 192.7838276140766),
    "ROK": (55.57737860807108, 158.65917206250896, 276.668917606048),
    "FIX": (282.63743108583225, 550.2236007355106, 841.8013135098261),
}


def test_batch_22_exact_outcomes_and_ranges() -> None:
    rows = {ticker:_result(ticker) for ticker in BATCH_22_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS)
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS)
    assert all(row["availability_type"] != "not_available" for row in rows.values())
    for ticker, row in rows.items():
        values = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        assert values == pytest.approx(EXPECTED[ticker])
        assert 0. <= values[0] <= values[1] <= values[2] and values[1] > 0.
        assert row["history_reliability"]["label"] == "Low"


def test_batch_22_source_and_transition_controls() -> None:
    hon = _result("HON")
    assert hon["source_ledger"]["controlling_filing"]["accession"] == "0000773840-26-000124"
    assert hon["reported_inputs"]["ttm_interest"] == pytest.approx(1_449_000_000.)
    assert {source["concept"] for source in hon["source_ledger"]["flow_sources"]["interest_expense"]["sources"]} == {"InterestAndDebtExpense", "InterestExpenseNonoperating"}
    assert hon["source_ledger"]["event_sources"][1]["value"] == 15_835_000_000.
    assert _result("JCI")["governed_assumptions"]["history_years_used"] == 2
    assert _result("WAB")["source_ledger"]["event_sources"][1]["value"] == 1_062_000_000.
    assert _result("LMT")["source_ledger"]["event_sources"][1]["value"] == 0.


def test_batch_22_bridge_and_sensitivity_directions() -> None:
    assert _result("CPRT")["scenario_rows"][1]["other_equity_claims"] == 17_181_000.
    assert _result("ROK")["scenario_rows"][1]["debt_and_finance_leases"] == 3_258_000_000.
    assert _result("IEX")["scenario_rows"][1]["other_equity_claims"] == 0.
    for ticker in P:
        rows = _result(ticker)["scenario_rows"]
        assert rows[0]["wacc"] > rows[1]["wacc"] > rows[2]["wacc"]
        assert rows[0]["growth"] <= rows[1]["growth"] <= rows[2]["growth"]
        assert rows[0]["conditional_value_per_share"] <= rows[1]["conditional_value_per_share"] <= rows[2]["conditional_value_per_share"]


def test_batch_22_independent_arithmetic_and_source_identity() -> None:
    """Recalculate each DCF without calling the production valuation function."""
    for ticker in BATCH_22_TICKERS:
        result = _result(ticker)
        filing = result["source_ledger"]["controlling_filing"]
        assert filing["filed"] <= "2026-08-14"
        assert filing["period_end"] == P[ticker].period
        for row in result["scenario_rows"]:
            cash = row["starting_cash_fcff"]
            present = 0.
            for year in range(1, 9):
                fade = (8 - year) / 7
                growth = row["terminal_growth"] + (row["growth"] - row["terminal_growth"]) * fade
                cash *= 1 + growth
                present += cash / (1 + row["wacc"]) ** year
            terminal = cash * (1 + row["terminal_growth"]) / (row["wacc"] - row["terminal_growth"])
            enterprise = present + terminal / (1 + row["wacc"]) ** 8
            equity = enterprise + row["cash_and_investments"] - row["debt_and_finance_leases"] - row["other_equity_claims"]
            raw = equity / row["shares"]
            assert raw == pytest.approx(row["raw_value_per_share"])
            assert max(0., raw) == pytest.approx(row["conditional_value_per_share"])


def test_batch_22_public_contract_and_calculator() -> None:
    from run_batch_22_history import _public
    for issuer in BATCH_22_MANIFEST:
        row = _result(issuer.ticker)
        public = _public(issuer, row)
        raw = json.dumps(public)
        assert public["availability_type"] == row["availability_type"]
        assert public["scenario_range"]["base"] == row["scenario_range"]["base"]
        assert all(key not in raw for key in ("source_ledger", "model_trace", "reported_inputs", "annual_cash_sources"))
        assert calculator_view(public)["model_family"] == "operating"
        assert calculate(public, overrides={}, manual_price=None)["result"] == row["scenario_range"]


def test_batch_22_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_22_history import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, output_root=tmp_path / "batch22")
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 7, 3, 0, 10)
    assert report["pass_tickers"] == ["WM", "IEX", "ODFL", "CPRT", "LMT", "ROK", "FIX"]
    assert report["conditional_tickers"] == ["HON", "JCI", "WAB"]
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed"] is False
    assert report["withheld_register_changed"] is False


def test_arelle_remains_outside_serving_imports() -> None:
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
