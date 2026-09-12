import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_42 import BATCH_42_MANIFEST
from app.us_valuation.batch_42_history import build_batch_42_history_result
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {
    "source_root": ROOT / "output/batch-42-sec-source-packets-b-20260907",
    "structural_root": ROOT / "output/batch-42-structural-sources-20260907",
    "event_root": ROOT / "output/batch-42-event-review-20260907",
    "structural_cache_root": ROOT / "output/batch-42-structural-cache-20260907",
}
EXPECTED = {
    "PPG": (7.144690314373073, 48.47101559927543, 92.60033872564556),
    "SLB": (17.439590850521764, 35.603899340859414, 56.40297746351421),
    "SHW": (41.862117597498454, 114.38588234438251, 193.01249023085938),
    "CVX": (44.187112296249516, 119.70200924378297, 216.0995354167879),
    "OXY": (0.6585526241123432, 33.387252822779864, 88.1923930267511),
    "EOG": (63.282493839769735, 132.99942018932535, 202.03854577934104),
    "FCX": (0.0, 3.4377546338092677, 15.595719494054677),
    "CRH": (10.626194087059302, 37.79268828856319, 66.47125216926902),
    "EXE": (None, None, None),
    "ALB": (None, None, None),
}


@lru_cache(None)
def result(ticker):
    return build_batch_42_history_result(ticker=ticker, **KW)


def test_denominator_sources_values_and_initial_outcomes():
    rows = [result(issuer.ticker) for issuer in BATCH_42_MANIFEST]
    assert len(rows) == 10
    assert [row["ticker"] for row in rows if row["availability_type"] == "not_available"] == ["EXE", "ALB"]
    assert all(row["availability_type"] == "conditional_estimate" for row in rows if row["ticker"] not in {"EXE", "ALB"})
    for row in rows:
        assert row["source_ledger"]["runtime_source_verification"]["verified"]
        assert row["source_ledger"]["event_sources"]["screened_filings"]
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        if row["ticker"] in {"EXE", "ALB"}:
            assert observed == EXPECTED[row["ticker"]]
            assert row["history_reliability"] is None
        else:
            assert observed == pytest.approx(EXPECTED[row["ticker"]])
            assert all(math.isfinite(value) for value in observed)
            assert row["history_reliability"]["label"] == "Low"


def test_numeric_scenarios_replay_exactly_and_preserve_raw_bear():
    for issuer in BATCH_42_MANIFEST:
        row = result(issuer.ticker)
        for scenario in row["scenario_rows"]:
            state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0., scenario["other_equity_claims"], scenario["shares"])
            replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
            assert replay == pytest.approx(scenario["raw_value_per_share"])
            assert scenario["conditional_value_per_share"] == pytest.approx(max(0., replay))
    assert result("FCX")["scenario_rows"][0]["raw_value_per_share"] < 0
    assert result("FCX")["scenario_range"]["low"] == 0


def test_structural_ttm_repairs_and_custom_concepts_are_exact():
    ppg = result("PPG")["source_ledger"]["flow_sources"]
    assert ppg["revenue"]["period_end"] == "2026-06-30"
    assert ppg["revenue"]["value"] == 16_421_000_000
    exe = result("EXE")["source_ledger"]["flow_sources"]
    assert exe["revenue"]["period_end"] == "2026-06-30"
    assert exe["revenue"]["value"] == 13_595_000_000
    eog = result("EOG")["source_ledger"]["flow_sources"]["capital_expenditures"]
    assert eog["current_h1"]["value"] == 3_426_000_000
    assert len(eog["current_h1"]["components"]) == 2
    eog_interest = result("EOG")["source_ledger"]["flow_sources"]["interest_expense"]
    assert eog_interest["current_h1"]["value"] == 133_000_000
    assert eog_interest["current_h1"]["concept"].endswith("InterestExpense")
    assert eog_interest["latest_fy"]["concept"] == "InterestExpense"
    exe_interest = result("EXE")["source_ledger"]["flow_sources"]["interest_expense"]
    assert exe_interest["current_h1"]["value"] == 102_000_000
    assert exe_interest["current_h1"]["concept"].endswith("InterestExpenseNonoperating")
    assert exe_interest["latest_fy"]["concept"] == "InterestExpenseNonoperating"
    fcx = result("FCX")["source_ledger"]["flow_sources"]
    assert fcx["capital_expenditures"]["current_h1"]["value"] == 2_077_000_000
    assert fcx["interest_expense"]["current_h1"]["concept"].endswith("InterestIncomeExpenseNet")
    alb = result("ALB")["source_ledger"]["flow_sources"]
    assert alb["interest_expense"]["current_h1"]["concept"].endswith("InterestAndDebtExpense")


def test_bridge_claims_and_pending_events_are_bound_once():
    oxy = result("OXY")["source_ledger"]["bridge_context"]
    assert oxy["debt"] == 13_743_000_000
    assert oxy["claims"][0] - oxy["claims"][1] == 7_809_000_000
    fcx = result("FCX")["source_ledger"]["bridge_context"]
    assert fcx["claims"] == pytest.approx((18_056_000_000, 12_113_000_000, 12_113_000_000))
    assert fcx["excluded_or_separately_treated"]["closure_obligation_sensitivity"] == pytest.approx((5_943_000_000, 0., 0.))
    assert result("EOG")["source_ledger"]["bridge_context"]["claims"] == pytest.approx((1_607_000_000, 0., 0.))
    assert result("CRH")["source_ledger"]["bridge_context"]["claims"] == pytest.approx((2_060_000_000, 1_500_000_000, 1_500_000_000))
    assert result("EXE")["source_ledger"]["bridge_context"]["claims"] == pytest.approx((723_000_000, 0., 0.))
    alb = result("ALB")["source_ledger"]["bridge_context"]
    assert alb["base_share_count"] == 118_005_057
    assert alb["excluded_or_separately_treated"]["preferred_stock_requires_conversion_reconciliation"] == 2_235_105_000
    assert "pending" in result("CRH")["source_ledger"]["event_sources"]["treatment"].lower()
    assert result("EXE")["source_ledger"]["twin_eagle_purchase_price_included"] is False


def test_exe_and_alb_hard_gates_remain_withheld():
    exe = result("EXE")
    assert exe["governed_assumptions"]["history_years_used"] == 1
    assert exe["source_ledger"]["current_ttm_is_diagnostic_only"] is True
    assert exe["scenario_range"] == {"low": None, "base": None, "high": None}
    alb = result("ALB")
    margins = alb["governed_assumptions"]["cash_conversion_margin"]
    assert len(margins) == 5
    assert sorted(margins)[2] < 0
    assert alb["source_ledger"]["current_ttm_is_diagnostic_only"] is True
    assert alb["scenario_range"] == {"low": None, "base": None, "high": None}


def test_public_contract_calculator_and_private_boundary_are_exact():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_42_history import _public

    for issuer in BATCH_42_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        assert public["model_policy"]["primary"] == "fcff_dcf"
        assert "latest reported common shares" in public["public_assumptions"]["share_count_basis"]
        view = calculator_view(public)
        if issuer.ticker in {"EXE", "ALB"}:
            assert not view["can_calculate"]
            assert public["scenario_range"]["base"] is None
        else:
            assert view["can_calculate"]
            assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
            higher = calculate(public, overrides={"discount_rate": view["defaults"]["discount_rate"] + .01}, manual_price=None)
            assert higher["result"]["base"] < private["scenario_range"]["base"]
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "runtime_source_verification", "raw_scenario_rows"):
            assert key not in encoded


def test_source_tampering_fails_closed(tmp_path):
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "EOG", source / "EOG")
    (source / "EOG" / "companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_42_history_result(ticker="EOG", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_42_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 8, 2, 8)
    assert report["denominator_tickers"] == [issuer.ticker for issuer in BATCH_42_MANIFEST]
    assert report["batch_41_dependency_status"] == "confirmed_batch_41_recovery_catalog_and_bookkeeping_bound"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
