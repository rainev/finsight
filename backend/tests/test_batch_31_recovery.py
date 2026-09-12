from dataclasses import replace
from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_31 import BATCH_31_MANIFEST
from app.us_valuation.batch_31_recovery import SCENARIOS, build_batch_31_recovery_result, value_oracle_infrastructure_scenario
from app.us_valuation.calculator import calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-31-sec-source-packets-20260902"
STRUCTURAL = ROOT / "output/batch-31-structural-sources-20260902"
INITIAL = ROOT / "output/batch-31-history-run-e-20260902"


def result(ticker="ORCL"):
    return build_batch_31_recovery_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL)


def test_orcl_recovery_attempt_remains_withheld():
    value = result()
    assert value["availability_type"] == "not_available"
    assert value["scenario_range"] == {"low": None, "base": None, "high": None}
    assert value["source_ledger"]["recovery_attempt"]["attempted"] is True
    traces = value["source_ledger"]["infrastructure_recovery_attempt"]["scenario_traces"]
    assert traces[0]["raw_value_per_share"] < traces[1]["raw_value_per_share"] < traces[2]["raw_value_per_share"]
    assert traces[1]["raw_value_per_share"] < 0
    assert value["governed_assumptions"]["reason_codes"] == ["MODEL_UNSUPPORTED", "NONFINITE_OR_NONPOSITIVE_VALUE", "CAPEX_CASH_CONVERSION_SENSITIVITY"]


def test_orcl_recovery_schedules_and_double_count_controls():
    value = result()
    attempt = value["source_ledger"]["infrastructure_recovery_attempt"]
    assert value["governed_assumptions"]["excluded_optimistic_costs"]["purchase_obligations_after_year_five"] == 7_533_000_000.
    assert value["governed_assumptions"]["excluded_optimistic_costs"]["post_balance_infrastructure_commitment"] == 19_000_000_000.
    assert attempt["purchase_obligations_after_year_five_included"] is False
    assert attempt["post_balance_19b_included"] is False
    assert attempt["rpo_added_as_cash"] is False
    assert all(len(row["forecast_rows"]) == 10 for row in attempt["scenario_traces"])
    assert [row["new_lease_term_years"] for row in attempt["scenario_traces"]] == [15, 17, 19]
    assert value["governed_assumptions"]["lease_schedule_treatment"]["reported_vs_estimated"] == "reported_bounds_with_optimistic_finsight_timing"
    assert all(row["reported_vs_estimated"] == "finsight_assumption" for row in value["governed_assumptions"]["scenario_parameters"].values())


def test_orcl_recovery_exact_replay_and_sensitivity():
    rows = [value_oracle_infrastructure_scenario(scenario) for scenario in SCENARIOS]
    assert [row["raw_value_per_share"] for row in rows] == pytest.approx((-144.1482, -6.0580, 177.7963), abs=.01)
    assert [row["preferred_conversion_shares"] for row in rows] == pytest.approx((31_238_285., 28_114_457.5, 24_990_630.))
    assert rows[1]["preferred_conversion_alternative_per_share"] < 0
    base = SCENARIOS[1]
    original = value_oracle_infrastructure_scenario(base)["raw_value_per_share"]
    assert value_oracle_infrastructure_scenario(replace(base, pre_capex_cash_margin=base.pre_capex_cash_margin + .01))["raw_value_per_share"] > original
    assert value_oracle_infrastructure_scenario(replace(base, terminal_capex_ratio=base.terminal_capex_ratio - .01))["raw_value_per_share"] > original
    assert value_oracle_infrastructure_scenario(replace(base, wacc=base.wacc + .01))["raw_value_per_share"] < original
    bull = SCENARIOS[2]
    bull_value = value_oracle_infrastructure_scenario(bull)["raw_value_per_share"]
    assert value_oracle_infrastructure_scenario(replace(bull, shares=bull.shares * 1.01))["raw_value_per_share"] < bull_value


def test_orcl_public_remains_safe_and_unavailable():
    from run_batch_31_recovery import _public
    issuer = next(row for row in BATCH_31_MANIFEST if row.ticker == "ORCL")
    private = result()
    public = _public(issuer, private)
    raw = json.dumps(public)
    assert "source_ledger" not in raw and "scenario_traces" not in raw and "reported_inputs" not in raw
    view = calculator_view(public)
    assert not view["can_calculate"] and public["availability_type"] == "not_available"
    assert public["public_assumptions"]["forecast_years"] == 10
    assert public["public_assumptions"]["history_years_used"] == 5


def test_recovery_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_31_recovery import run
    report = run(initial_root=INITIAL, source_root=SOURCE, structural_root=STRUCTURAL, output_root=tmp_path / "candidate")
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (1, 2, 7, 1, 9)
    assert report["attempted_tickers"] == ["ORCL"] and report["still_withheld_tickers"] == ["ORCL"]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
