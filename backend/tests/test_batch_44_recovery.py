import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_44 import BATCH_44_MANIFEST
from app.us_valuation.batch_44_recovery import build_batch_44_recovery_result
from app.us_valuation.calculator import calculator_view
from app.us_valuation.practical_models import EnterpriseCashFlowState,enterprise_cash_flow_dcf


ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
INITIAL=ROOT/"output/batch-44-history-run-b-20260907"
KW={"source_root":ROOT/"output/batch-44-sec-source-packets-20260907","structural_root":ROOT/"output/batch-44-structural-sources-20260907","event_root":ROOT/"output/batch-44-event-review-20260907","structural_cache_root":ROOT/"output/batch-44-structural-cache-20260907","special_annual_root":ROOT/"output/batch-44-special-annual-sources-20260907","xom_annual_root":ROOT/"output/batch-44-xom-annual-source-20260907"}
EXPECTED={"MPC":(114.70110782714586,260.6138117576469,420.161792576826),"PSX":(34.02640004942218,80.01927151589591,129.58153228630067),"FANG":(117.15330606550854,195.3443178630455,249.05699962639358),"BKR":(None,None,None),"AMCR":(2.60542153364047,17.918065224284618,36.641544050931174),"DOW":(0.,14.154069823637862,33.18948270066658),"CTVA":(10.128216276644173,26.36532045697048,38.696284890207814),"APA":(8.702860401280603,33.396689747336815,50.303397993560736),"SW":(0.,8.999378419841726,27.964391646561683),"XOM":(56.17211804489733,83.64033613314334,106.64562057759753)}


def result(ticker):return build_batch_44_recovery_result(ticker=ticker,**KW)


def test_recovery_outcomes_are_nine_conditional_one_withheld():
    rows={issuer.ticker:result(issuer.ticker) for issuer in BATCH_44_MANIFEST}
    assert {ticker for ticker,row in rows.items() if row["availability_type"]=="not_available"}=={"BKR"}
    assert all(row["availability_type"]=="conditional_estimate" for ticker,row in rows.items() if ticker!="BKR")
    for ticker,row in rows.items():
        observed=tuple(row["scenario_range"][key] for key in ("low","base","high"))
        if ticker=="BKR": assert observed==EXPECTED[ticker]
        else: assert observed==pytest.approx(EXPECTED[ticker])


def test_existing_numeric_bases_are_unchanged_and_ranges_are_narrower():
    initial=json.loads((INITIAL/"batch-44-report.json").read_text()); initial_cases={row["ticker"]:row for row in initial["cases"]}
    for ticker in ("MPC","PSX","FANG","DOW","CTVA","APA","XOM"):
        row=result(ticker); old=initial_cases[ticker]; assert row["scenario_range"]["base"]==pytest.approx(old["base"]); assert row["scenario_range"]["high"]-row["scenario_range"]["low"]<old["high"]-old["low"]; assert row["source_ledger"]["recalibration"]["base_value_unchanged"] is True; assert row["source_ledger"]["recalibration"]["reported_bridge_unchanged"] is True; assert row["governed_assumptions"]["scenario_calibration"]=="moderated_multi_factor_midpoints_between_full_tails_and_unchanged_base"


def test_all_numeric_rows_replay_exactly_and_preserve_raw_floor_logic():
    for issuer in BATCH_44_MANIFEST:
        row=result(issuer.ticker)
        for scenario in row["scenario_rows"]:
            state=EnterpriseCashFlowState(scenario["starting_cash_fcff"],scenario["growth"],scenario["terminal_growth"],scenario["wacc"],scenario["cash_and_investments"],scenario["debt_and_finance_leases"],0.,scenario["other_equity_claims"],scenario["shares"]); replay=enterprise_cash_flow_dcf(state,forecast_years=8,allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
            assert replay==pytest.approx(scenario["raw_value_per_share"]); assert scenario["conditional_value_per_share"]==pytest.approx(max(0.,replay))
    assert result("DOW")["scenario_rows"][0]["raw_value_per_share"]<0
    assert result("SW")["scenario_rows"][0]["raw_value_per_share"]<0
    assert result("APA")["scenario_rows"][0]["raw_value_per_share"]>0


def test_amcr_and_sw_recoveries_use_only_current_company_observations():
    amcr=result("AMCR");sw=result("SW")
    assert amcr["governed_assumptions"]["history_years_used"]==1
    assert "first full combined FY2026" in amcr["warning"]
    assert amcr["source_ledger"]["recovery_attempt"]["final_availability_type"]=="conditional_estimate"
    assert sw["governed_assumptions"]["history_years_used"]==2
    assert "FY2025 plus current TTM" in sw["warning"]
    claims=sw["source_ledger"]["current_company_recovery_calibration"]["preferred_claim_sensitivity"]
    bridge=sw["source_ledger"]["bridge_context"]["claims"]
    assert tuple(claims[i]-bridge[i] for i in range(3))==pytest.approx((10_000_000,5_000_000,0.))
    assert sw["governed_assumptions"]["equity_floor_basis"].startswith("bear-only")


def test_bkr_known_terms_do_not_become_incomplete_numeric_bridge():
    bkr=result("BKR");attempt=bkr["source_ledger"]["recovery_attempt"]
    assert bkr["scenario_range"]=={"low":None,"base":None,"high":None}; assert attempt["known_chart_cash_per_share"]==210.; assert attempt["known_term_loans"]==2_000_000_000.; assert attempt["total_cash_consideration"] is None; assert attempt["assumed_debt_and_claims"] is None; assert attempt["combined_operating_cash_flow"] is None


def test_public_contract_and_calculator_are_safe_after_recalibration():
    from app.us_valuation.calculator import calculate
    from run_batch_44_recovery import _public
    for issuer in BATCH_44_MANIFEST:
        private=result(issuer.ticker); public=_public(issuer,private); encoded=json.dumps(public); view=calculator_view(public); assert public["model_policy"]["primary"]=="fcff_dcf"
        assert "+/-0.75%" in public["public_assumptions"]["share_count_basis"]
        if issuer.ticker=="SW": assert public["public_assumptions"]["equity_floor_basis"].startswith("bear-only")
        if issuer.ticker=="BKR": assert not view["can_calculate"]
        else: assert view["can_calculate"] and calculate(public,overrides={},manual_price=None)["result"]==pytest.approx(private["scenario_range"])
        if issuer.ticker!="BKR": assert "RELIABILITY_PAYLOAD_INVALID" not in public["reliability"]["reasons"]
        for key in ("source_ledger","reported_inputs","governed_assumptions","pre_recalibration_scenario_rows","raw_scenario_rows"): assert key not in encoded


def test_runner_pins_initial_and_preserves_bookkeeping(tmp_path):
    from run_batch_44_recovery import run
    report=run(initial_root=INITIAL,output_root=tmp_path/"candidate",**KW)
    assert (report["attempted_count"],report["pass_count"],report["conditional_count"],report["withheld_count"],report["numeric_count"])==(3,0,9,1,9)
    assert report["recovered_to_conditional_tickers"]==["AMCR","SW"] and report["still_withheld_tickers"]==["BKR"]
    assert report["whole_batch_recalibrated_tickers"]==["MPC","PSX","FANG","DOW","CTVA","APA","XOM"]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
