from __future__ import annotations

import json
from pathlib import Path
import sys

from app.us_valuation.batch_16 import BATCH_16_MANIFEST, BATCH_16_TICKERS
from app.us_valuation.batch_16_history import CONDITIONAL_TICKERS, PASS_TICKERS, WITHHELD_TICKERS, build_batch_16_history_result
from app.us_valuation.calculator import calculate, calculator_view

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-16-sec-source-packets-20260830"
STRUCTURAL = ROOT / "output/batch-16-structural-sources-20260830"
EVENT = ROOT / "output/batch-16-event-sources-20260830"


def _result(ticker):
    return build_batch_16_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT)


def test_batch_16_exact_outcomes_and_numeric_contract():
    rows = {ticker: _result(ticker) for ticker in BATCH_16_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS) == {"VEEV", "IQV"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == {"A", "PODD"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "not_available"} == set(WITHHELD_TICKERS) == {"DXCM", "EW", "CRL", "ZBH", "COR", "ELV"}
    for ticker, row in rows.items():
        if ticker in WITHHELD_TICKERS:
            assert row["scenario_range"] == {"low": None, "base": None, "high": None}
            assert row["history_reliability"] is None
        else:
            low, base, high = row["scenario_range"].values()
            assert 0 <= low <= base <= high and base > 0
            assert row["history_reliability"]["label"] in {"High", "Medium", "Low"}


def test_batch_16_operating_directions_and_special_treatments():
    for ticker in set(BATCH_16_TICKERS) - WITHHELD_TICKERS - {"ELV"}:
        row = _result(ticker)
        scenarios = row["scenario_rows"]
        assert scenarios[0]["wacc"] > scenarios[1]["wacc"] > scenarios[2]["wacc"]
        assert scenarios[0]["growth"] <= scenarios[1]["growth"] <= scenarios[2]["growth"]
        assert scenarios[0]["other_equity_claims"] >= scenarios[1]["other_equity_claims"] >= scenarios[2]["other_equity_claims"]
        assert scenarios[0]["conditional_value_per_share"] <= scenarios[1]["conditional_value_per_share"] <= scenarios[2]["conditional_value_per_share"]
    veev = _result("VEEV")
    assert veev["reported_inputs"]["ttm_interest"] is None
    assert veev["reported_inputs"]["ttm_reinvestment"] == 24_972_000.
    assert veev["source_ledger"]["bridge_sources"][-2]["reported_vs_estimated"] == "source_proven_absent"
    agilent = _result("A")
    assert agilent["source_ledger"]["event_sources"][-1]["reported_terms"]["principal_usd"] == 600_000_000
    assert agilent["scenario_rows"][1]["cash_and_investments"] == 2_406_808_000.
    assert agilent["scenario_rows"][1]["debt_and_finance_leases"] == 3_955_000_000.
    assert _result("PODD")["scenario_rows"][0]["conditional_value_per_share"] > 0
    assert _result("PODD")["source_ledger"]["event_sources"][0]["possible_loss_range"] is None
    assert len(_result("IQV")["source_ledger"]["event_sources"]) == 4


def test_batch_16_elv_is_equity_routed_but_hard_withheld_and_claim_gates_are_explicit():
    elv = _result("ELV")
    assert elv["source_ledger"]["economically_suitable_model_if_released"] == "managed_care_residual_income_normalized_equity_earnings"
    assert elv["source_ledger"]["hard_blocker"] == "CLAIMS_UNBOUNDED"
    assert all(_result(ticker)["source_ledger"]["hard_blocker"] == "CLAIMS_UNBOUNDED" for ticker in WITHHELD_TICKERS)


def test_batch_16_public_contract_is_safe_and_calculable():
    from run_batch_16_history import _public
    for issuer in BATCH_16_MANIFEST:
        row = _result(issuer.ticker)
        public = _public(issuer, row)
        raw = json.dumps(public)
        assert public["availability_type"] == row["availability_type"]
        assert public["scenario_range"]["base"] == row["scenario_range"]["base"]
        assert "source_ledger" not in raw and "model_trace" not in raw and "reported_inputs" not in raw
        if issuer.ticker not in WITHHELD_TICKERS:
            assert calculator_view(public)["model_family"] == "operating"
            assert calculate(public, overrides={}, manual_price=None)["result"] == row["scenario_range"]


def test_batch_16_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_16_history import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT, output_root=tmp_path / "batch16")
    assert report["attempted_count"] == 10
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (2, 2, 6, 4)
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed"] is False
    assert report["withheld_register_changed"] is False
