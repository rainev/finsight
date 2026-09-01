from __future__ import annotations

import json
from pathlib import Path
import sys

from app.us_valuation.batch_15 import BATCH_15_MANIFEST, BATCH_15_TICKERS
from app.us_valuation.batch_15_history import PASS_TICKERS, CONDITIONAL_TICKERS, WITHHELD_TICKERS, build_batch_15_history_result
from app.us_valuation.calculator import calculate, calculator_view

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-15-sec-source-packets-20260830"
STRUCTURAL = ROOT / "output/batch-15-structural-sources-20260830"


def _result(ticker):
    return build_batch_15_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL)


def test_batch_15_exact_outcomes_and_numeric_contract():
    rows = {ticker: _result(ticker) for ticker in BATCH_15_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS)
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS)
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "not_available"} == set(WITHHELD_TICKERS)
    for ticker, row in rows.items():
        if ticker in WITHHELD_TICKERS:
            assert row["scenario_range"] == {"low": None, "base": None, "high": None}
            assert row["history_reliability"] is None
        else:
            low, base, high = row["scenario_range"].values()
            assert 0 <= low <= base <= high and base > 0
            assert row["history_reliability"]["label"] in {"High", "Medium", "Low"}


def test_batch_15_model_routes_directions_and_no_fabricated_zero():
    for ticker in set(BATCH_15_TICKERS) - WITHHELD_TICKERS - {"CNC"}:
        row = _result(ticker)
        scenarios = row["scenario_rows"]
        assert scenarios[0]["wacc"] > scenarios[1]["wacc"] > scenarios[2]["wacc"]
        assert scenarios[0]["growth"] <= scenarios[1]["growth"] <= scenarios[2]["growth"]
        assert scenarios[0]["debt_and_finance_leases"] >= scenarios[1]["debt_and_finance_leases"] >= scenarios[2]["debt_and_finance_leases"]
        assert scenarios[0]["other_equity_claims"] >= scenarios[1]["other_equity_claims"] >= scenarios[2]["other_equity_claims"]
        assert scenarios[0]["conditional_value_per_share"] <= scenarios[1]["conditional_value_per_share"] <= scenarios[2]["conditional_value_per_share"]
    assert _result("ISRG")["source_ledger"]["bridge_sources"][-1]["reported_vs_estimated"] == "source_proven_absent"
    assert "cannot be ranged" in _result("ALGN")["source_ledger"]["bridge_reconciliation"]["unbounded_claim"]
    assert _result("WAT")["scenario_rows"][0]["limited_liability_floor_applied"] is True
    assert _result("LH")["source_ledger"]["bridge_reconciliation"]["unbounded_claim"].startswith("DOJ settlement")


def test_batch_15_managed_care_is_equity_level_and_history_backed():
    row = _result("CNC")
    assumptions = row["governed_assumptions"]
    assert assumptions["route_is_equity_level"] is True
    assert assumptions["ev_debt_bridge_applied"] is False
    assert assumptions["history_years_used"] >= 4
    assert row["reported_inputs"]["reported_2025_net_loss"] < 0
    assert row["reported_inputs"]["normalized_2025_parent_earnings"] == 52_000_000.
    assert row["reported_inputs"]["h1_risk_adjustment_pre_tax_benefit"] == 481_000_000.
    assert row["scenario_rows"][0]["cost_of_equity"] > row["scenario_rows"][1]["cost_of_equity"] > row["scenario_rows"][2]["cost_of_equity"]


def test_batch_15_public_contract_is_safe_and_calculable():
    from run_batch_15_history import _public
    for issuer in BATCH_15_MANIFEST:
        row = _result(issuer.ticker)
        public = _public(issuer, row)
        raw = json.dumps(public)
        assert public["availability_type"] == row["availability_type"]
        assert public["scenario_range"]["base"] == row["scenario_range"]["base"]
        assert "source_ledger" not in raw and "model_trace" not in raw and "reported_inputs" not in raw
        if issuer.ticker not in WITHHELD_TICKERS:
            assert calculator_view(public)["model_family"] == ("equity_earnings" if issuer.ticker == "CNC" else "operating")
            assert calculate(public, overrides={}, manual_price=None)["result"] == row["scenario_range"]
