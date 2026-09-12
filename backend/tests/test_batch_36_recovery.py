from dataclasses import replace
from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_36 import BATCH_36_MANIFEST
from app.us_valuation.batch_36_recovery import build_batch_36_recovery_result
from app.us_valuation.calculator import calculator_view
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-36-sec-source-packets-20260905"
STRUCTURAL = ROOT / "output/batch-36-structural-sources-20260905"
EVENTS = ROOT / "output/batch-36-event-sources-v3-20260905"
CACHE = ROOT / "output/batch-36-structural-cache-20260905"
INITIAL = ROOT / "output/batch-36-history-run-i-20260905"


def result(ticker="VLO"):
    return build_batch_36_recovery_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS, structural_cache_root=CACHE)


def test_vlo_recovery_attempt_closes_capex_but_remains_withheld():
    row = result()
    attempt = row["source_ledger"]["recovery_attempt"]
    assert row["availability_type"] == "not_available"
    assert row["scenario_range"] == {"low": None, "base": None, "high": None}
    assert attempt["attempted"] and attempt["capex_gate_closed"]
    assert not attempt["port_arthur_claim_gate_closed"]
    assert row["source_ledger"]["port_arthur_claim_gate"]["third_party_claim_base"] is None


def test_custom_capex_lineage_and_ttm_are_exact():
    row = result()
    capex = row["source_ledger"]["capex_recovery"]
    assert [item["capital_expenditures"]["value"] for item in capex["annual_same_concept_history"]] == [1_916_000_000, 2_057_000_000, 1_885_000_000]
    assert capex["ttm"]["value"] == 1_617_000_000
    assert capex["ttm"]["stale_standard_capex_rejected"] is True
    assert row["source_ledger"]["reported_ttm_reconstruction"]["cash_fcff"] == pytest.approx(9_728_702_838.205303)


def test_private_preclaim_diagnostic_replays_and_is_not_published():
    row = result()
    diagnostic = row["source_ledger"]["pre_claim_diagnostic"]
    assert diagnostic["publication_allowed"] is False
    assert diagnostic["scenario_values"] == pytest.approx((110.3533238151, 171.1824447510, 316.8335533614))
    assert row["governed_assumptions"]["ttm_cash_fcff_not_used_as_scenario_floor"] is True
    for item in diagnostic["scenario_traces"]:
        state = item["state"]
        replay = enterprise_cash_flow_dcf(EnterpriseCashFlowState(state["starting_cash_fcff"], state["growth"], state["terminal_growth"], state["wacc"], state["cash"], state["debt_and_finance_leases"], state["preferred"], state["nci"], state["shares"]), forecast_years=8, allow_nonpositive_equity_trace=True)
        assert replay["intrinsic_value_per_share"] == pytest.approx(item["raw_pre_port_arthur_claim_value_per_share"])


def test_bridge_repayment_and_sensitivities_are_directionally_sound():
    diagnostic = result()["source_ledger"]["pre_claim_diagnostic"]
    bridge = diagnostic["bridge"]
    assert bridge["reported_cash_2026_06_30"]["value"] == 7_874_000_000
    assert bridge["reported_debt_current"]["value"] + bridge["reported_debt_noncurrent"]["value"] == 11_349_000_000
    assert bridge["post_repayment_cash"] == 7_774_000_000
    assert bridge["post_repayment_debt_and_finance_leases"] == 11_249_000_000
    assert bridge["net_debt_change"] == 0
    base = diagnostic["scenario_traces"][1]["state"]
    state = EnterpriseCashFlowState(base["starting_cash_fcff"], base["growth"], base["terminal_growth"], base["wacc"], base["cash"], base["debt_and_finance_leases"], base["preferred"], base["nci"], base["shares"])
    original = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
    assert enterprise_cash_flow_dcf(replace(state, cash_fcff=state.cash_fcff * 1.05), forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"] > original
    assert enterprise_cash_flow_dcf(replace(state, wacc=state.wacc + .01), forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"] < original
    assert enterprise_cash_flow_dcf(replace(state, noncontrolling_interests=state.noncontrolling_interests + 1_000_000_000), forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"] < original


def test_public_result_remains_safe_fcff_and_uncalculable():
    from run_batch_36_recovery import _public
    issuer = next(item for item in BATCH_36_MANIFEST if item.ticker == "VLO")
    private = result()
    public = _public(issuer, private)
    encoded = json.dumps(public)
    assert public["availability_type"] == "not_available"
    assert public["model_policy"]["primary"] == "fcff_dcf"
    assert set(public["models"]) == {"fcff_dcf"}
    assert "conditional_estimate" not in encoded
    assert all("fcff_dcf" in reason for reason in public["automated_review"]["blocking_reasons"] if reason.startswith("model_"))
    assert calculator_view(public)["can_calculate"] is False
    for private_key in ("source_ledger", "pre_claim_diagnostic", "scenario_traces", "reported_inputs"):
        assert private_key not in encoded


def test_recovery_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_36_recovery import run
    report = run(initial_root=INITIAL, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS, structural_cache_root=CACHE, output_root=tmp_path / "candidate")
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (1, 0, 9, 1, 9)
    assert report["attempted_tickers"] == ["VLO"]
    assert report["recovered_to_conditional_tickers"] == []
    assert report["still_withheld_tickers"] == ["VLO"]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
