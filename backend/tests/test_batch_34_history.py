from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_34 import BATCH_34_MANIFEST, BATCH_34_TICKERS
from app.us_valuation.batch_34_history import PASS_TICKERS, CONDITIONAL_TICKERS, WITHHELD_TICKERS, build_batch_34_history_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-34-sec-source-packets-20260903"
STRUCTURAL = ROOT / "output/batch-34-structural-sources-20260903"
EVENTS = ROOT / "output/batch-34-event-sources-20260903"


def result(ticker):
    return build_batch_34_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS)


def test_all_ten_are_numeric_and_finite_ordered():
    rows = {ticker: result(ticker) for ticker in BATCH_34_TICKERS}
    assert len(rows) == 10
    assert not PASS_TICKERS
    assert CONDITIONAL_TICKERS == set(BATCH_34_TICKERS)
    assert not WITHHELD_TICKERS
    for row in rows.values():
        low, base, high = (row["scenario_range"][key] for key in ("low", "base", "high"))
        assert 0 < low <= base <= high
        assert row["history_reliability"]["label"] in {"High", "Medium", "Low"}


def test_exact_period_and_source_provenance_are_private():
    for ticker in BATCH_34_TICKERS:
        row = result(ticker)
        filing = row["source_ledger"]["controlling_filing"]
        assert filing["period_end"] == "2026-06-30"
        assert filing["accession"]
        history = row["source_ledger"]["company_history_profile"]
        assert history["full_history"] and len(history["annual_periods"]) == 5
        reconstruction = row["source_ledger"]["common_earnings_reconstruction"]
        assert reconstruction["current_ytd"]["filed"]
        assert reconstruction["prior_ytd"]["filed"]
        assert row["governed_assumptions"]["route_is_equity_level"] is True
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
        if ticker in {"L", "SPGI"}:
            assert reconstruction["current_ytd"]["unit"] == "USD"
            assert reconstruction["prior_ytd"]["unit"] == "USD"


def test_parent_earnings_and_preferred_event_claims_are_explicit():
    for ticker, expected_current, expected_prior in (("L", 737_000_000., 714_000_000.), ("SPGI", 2_398_000_000., 1_991_000_000.)):
        row = result(ticker)
        reconstruction = row["source_ledger"]["common_earnings_reconstruction"]
        assert reconstruction["current_ytd"]["value"] == expected_current
        assert reconstruction["prior_ytd"]["value"] == expected_prior
        assert reconstruction["current_ytd"]["method"] == "consolidated_earnings_less_reported_nci"
        assert len(reconstruction["current_ytd"]["sources"]) == 2
    stt = result("STT")
    assert any(item.get("accession") == "0001193125-26-346938" for item in stt["source_ledger"]["event_sources"])
    assert stt["governed_assumptions"]["preferred_claim_range"][1] >= 500_000_000.
    assert all(row["preferred_claim"] == claim for row, claim in zip(stt["scenario_rows"], stt["governed_assumptions"]["preferred_claim_range"]))
    tfc = result("TFC")
    prior_preferred = tfc["source_ledger"]["beginning_preferred_context"]
    assert len(prior_preferred) == 1
    assert prior_preferred[0]["value"] == 4_916_000_000.0
    assert prior_preferred[0]["period_end"] == "2025-12-31"


def test_roe_is_capped_to_history_and_unreported_claims_are_bounded():
    bro = result("BRO")
    assert bro["availability_type"] == "conditional_estimate"
    bridge = bro["governed_assumptions"]["roe_scenario_bridge"]
    assert bridge["modeled_roe"][2] <= bridge["reported_history_roe_range"][2]
    for ticker in {"L", "SPGI", "BRO", "PGR", "TRV"}:
        row = result(ticker)
        assert row["governed_assumptions"]["preferred_claim_status"] == "preferred_claim_bounded_from_no_reported_claim_row"
        low, base, high = row["governed_assumptions"]["preferred_claim_range"]
        assert low == 0 and base > 0 and high > base


def test_residual_income_replay_and_sensitivity_direction():
    from app.valuation.bank import residual_income_valuation
    for ticker in BATCH_34_TICKERS:
        row = result(ticker)
        for scenario in row["scenario_rows"]:
            trace = residual_income_valuation(book_value_per_share=scenario["book_value_per_share"], current_roe=scenario["current_roe"], cost_of_equity=scenario["cost_of_equity"], current_payout_ratio=scenario["current_payout_ratio"], terminal_roe=scenario["terminal_roe"], terminal_growth=scenario["terminal_growth"], years=5)
            assert trace["intrinsic_value"] == pytest.approx(scenario["raw_value_per_share"])
        assert row["scenario_rows"][0]["cost_of_equity"] > row["scenario_rows"][2]["cost_of_equity"]
        assert row["scenario_rows"][0]["current_roe"] <= row["scenario_rows"][2]["current_roe"]


def test_public_payload_and_calculator_do_not_leak_private_evidence():
    from run_batch_34_history import _public
    for issuer in BATCH_34_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        for key in ("source_ledger", "reported_inputs", "residual_income_trace", "equity_model_context", "ttm_"):
            assert key not in encoded
        assert calculator_view(public)["can_calculate"]
        assert calculate(public, overrides={}, manual_price=None)["result"] == private["scenario_range"]


def test_batch_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_34_history import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, event_root=None, output_root=tmp_path / "candidate")
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 10, 0, 10)
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]


def test_arelle_stays_outside_serving_process():
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
