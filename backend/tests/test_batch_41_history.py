import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_41 import BATCH_41_MANIFEST
from app.us_valuation.batch_41_history import build_batch_41_history_result
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {
    "source_root": ROOT / "output/batch-41-sec-source-packets-c-20260907",
    "structural_root": ROOT / "output/batch-41-structural-sources-20260907",
    "structural_cache_root": ROOT / "output/batch-41-structural-cache-20260907",
    "event_root": ROOT / "output/batch-41-event-review-c-20260907",
}
EXPECTED = {
    "APD": (None, None, None),
    "AVY": (46.46777035487608, 113.022742883164, 184.81468988181297),
    "BALL": (4.782217303771855, 21.26908781162332, 40.347306289310076),
    "ECL": (33.750181163523685, 78.52498381981147, 132.01884520511823),
    "EQT": (2.7145735006986906, 15.017926437315847, 58.87612575936702),
    "HAL": (10.442226010300494, 24.571866084615642, 41.92240225179062),
    "IFF": (None, None, None),
    "IP": (None, None, None),
    "NUE": (10.145541923817701, 121.8011652366488, 338.78105649606704),
    "PKG": (30.023733146314985, 68.28357892599081, 108.59053785102606),
}


@lru_cache(None)
def result(ticker):
    return build_batch_41_history_result(ticker=ticker, **KW)


def test_denominator_sources_values_and_initial_outcomes():
    rows = [result(issuer.ticker) for issuer in BATCH_41_MANIFEST]
    assert len(rows) == 10
    assert [row["ticker"] for row in rows if row["availability_type"] == "not_available"] == ["APD", "IFF", "IP"]
    for row in rows:
        assert row["source_ledger"]["runtime_source_verification"]["verified"]
        assert row["source_ledger"]["event_sources"]["screened_filings"]
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        if row["availability_type"] == "not_available":
            assert observed == EXPECTED[row["ticker"]]
            assert row["history_reliability"] is None
        else:
            assert observed == pytest.approx(EXPECTED[row["ticker"]])
            assert all(math.isfinite(value) for value in observed)
            assert row["history_reliability"]["label"] == "Low"


def test_numeric_scenarios_replay_or_apply_explicit_zero_operating_value():
    for issuer in BATCH_41_MANIFEST:
        row = result(issuer.ticker)
        for scenario in row["scenario_rows"]:
            if scenario["starting_cash_fcff"] <= 0:
                replay = (scenario["cash_and_investments"] - scenario["debt_and_finance_leases"] - scenario["other_equity_claims"]) / scenario["shares"]
            else:
                state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0.0, scenario["other_equity_claims"], scenario["shares"])
                replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
            assert replay == pytest.approx(scenario["raw_value_per_share"])
            assert scenario["conditional_value_per_share"] == pytest.approx(max(0.0, replay))


def test_event_and_bridge_arithmetic_is_bound_once():
    apd = result("APD")
    assert apd["source_ledger"]["project_exit_cash_maximum"] == 925_000_000
    ecl = result("ECL")["source_ledger"]["bridge_context"]
    assert ecl["cash"] == pytest.approx(385_300_000)
    assert ecl["debt"] == 13_170_800_000
    assert ecl["operating_asset_overlay"] == pytest.approx((3_562_500_000, 4_750_000_000, 5_937_500_000))
    eqt = result("EQT")["source_ledger"]["bridge_context"]
    assert eqt["event_reconciliation"] == {"july_15_debt_repayment": 115_000_000.0, "july_21_acquisition_debt": 77_000_000.0, "july_21_acquired_asset_cost": 77_000_000.0, "gross_debt_change": -38_000_000.0, "net_debt_change": 0.0, "base_common_equity_effect": 0.0, "treatment": eqt["event_reconciliation"]["treatment"]}
    assert eqt["operating_asset_overlay"] == (0.0, 0.0, 0.0)
    assert eqt["event_debt"] == 0.0
    assert result("EQT")["scenario_rows"][1]["commitment_present_value"] > 0
    assert result("HAL")["source_ledger"]["bridge_context"]["debt"] == 7_161_000_000
    assert result("NUE")["source_ledger"]["bridge_context"]["capex_coverage"]["ttm_coverage_above_full_year_guidance"] == 341_000_000


def test_share_conflicts_are_reconciled_to_later_cover_counts():
    ball = result("BALL")["source_ledger"]["share_reconciliation"]
    assert ball["selected_cover_dei_shares"]["value"] == 264_703_357
    assert ball["calculated_period_end_outstanding"] == 264_605_826
    ip = result("IP")["source_ledger"]["share_reconciliation"]
    assert ip["selected_cover_dei_shares"]["value"] == 529_569_895
    assert ip["calculated_period_end_outstanding"] == 529_500_000


def test_withheld_economic_objects_remain_null_and_explain_release_conditions():
    iff = result("IFF")
    assert iff["source_ledger"]["pending_sale_proceeds_included"] is False
    assert iff["source_ledger"]["disposal_group_assets"]["value"] == 4_840_000_000
    assert iff["source_ledger"]["disposal_group_liabilities"]["value"] == 1_173_000_000
    assert iff["source_ledger"]["structural_top_level_period_diagnostic"]["used_for_selection"] is False
    ip = result("IP")
    assert ip["source_ledger"]["debt"]["value"] == 9_200_000_000
    assert ip["source_ledger"]["cash_conversion_margin_diagnostic_only"]["base"] > 0
    assert ip["source_ledger"]["gcf_discontinued_cash"]["operating"]["value"] == 68_000_000
    assert ip["source_ledger"]["gcf_discontinued_cash"]["investing"]["value"] == -45_000_000


def test_corrected_halliburton_event_exhibit_is_hash_bound():
    event = result("HAL")["source_ledger"]["event_sources"]
    assert len(event["documents"]) == 2
    assert any(Path(document["path"]).name == "livemastererdocument.htm" for document in event["documents"])


def test_public_contract_calculator_and_private_boundary_are_exact():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_41_history import _public

    for issuer in BATCH_41_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        assert public["model_policy"]["primary"] == "fcff_dcf"
        view = calculator_view(public)
        if private["availability_type"] == "not_available":
            assert not view["can_calculate"]
            assert public["scenario_range"]["base"] is None
        else:
            assert view["can_calculate"]
            assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
            higher = calculate(public, overrides={"discount_rate": view["defaults"]["discount_rate"] + 0.01}, manual_price=None)
            assert higher["result"]["base"] < private["scenario_range"]["base"]
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "runtime_source_verification", "raw_scenario_rows"):
            assert key not in encoded


def test_source_tampering_fails_closed(tmp_path):
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "NUE", source / "NUE")
    (source / "NUE" / "companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_41_history_result(ticker="NUE", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_41_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 7, 3, 7)
    assert report["denominator_tickers"] == [issuer.ticker for issuer in BATCH_41_MANIFEST]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
