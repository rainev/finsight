import json,math,shutil,sys
from functools import lru_cache
from pathlib import Path
import pytest
from app.us_valuation.batch_45 import BATCH_45_MANIFEST
from app.us_valuation.batch_45_history import RESIDUAL_TICKERS,build_batch_45_history_result
from app.us_valuation.practical_models import EquityCashFlowState,mixed_utility_fcfe,practical_equity_cash_flow_range

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"))
KW={"source_root":ROOT/"output/batch-45-sec-source-packets-20260907","structural_root":ROOT/"output/batch-45-structural-sources-20260907","event_root":ROOT/"output/batch-45-event-review-20260907","structural_cache_root":ROOT/"output/batch-45-structural-cache-20260907","special_annual_root":ROOT/"output/batch-45-special-annual-sources-20260908"}
EXPECTED={"AEP":(62.44810733596384,72.29218811129995,85.72613306234724),"ETR":(42.942822628690955,49.7179580894959,58.96403988704425),"ES":(28.379355561789573,40.65006218619693,45.32770160666248),"XEL":(37.82812789514866,43.780228454180154,51.90243684969919),"SO":(28.663644678528215,41.964173903057315,50.17638289188946),"LNT":(33.27809166711696,38.509312325953104,45.64754411713015),"D":(29.366921125708558,33.98062254756495,40.27616173866987),"PNW":(54.81910086601474,63.43614778780974,75.19457268250751),"WEC":(47.10354927423115,49.69471929449417,65.57712598462646),"PEG":(43.648639644616516,44.89633125143623,50.27404343319912)}
@lru_cache(None)
def result(ticker):return build_batch_45_history_result(ticker=ticker,**KW)

def test_all_ten_are_numeric_conditional_low_with_exact_ranges():
    rows=[result(i.ticker) for i in BATCH_45_MANIFEST];assert len(rows)==10;assert all(r["availability_type"]=="conditional_estimate" and r["history_reliability"]["label"]=="Low" for r in rows)
    for r in rows:
        observed=tuple(r["scenario_range"][k] for k in ("low","base","high"));assert observed==pytest.approx(EXPECTED[r["ticker"]]);assert 0<observed[0]<=observed[1]<=observed[2] and all(math.isfinite(v) for v in observed)
    assert {r["ticker"] for r in rows if r["method"]=="regulated_utility_residual_income"}==RESIDUAL_TICKERS

def test_aep_raw_ticker_override_and_source_receipts_are_explicit():
    manifest=json.loads((KW["source_root"]/"AEP/source-manifest.json").read_text());sub=json.loads((KW["source_root"]/"AEP/submissions.json").read_text());assert sub["tickers"]==[];assert manifest["ticker_identity_override"]["accepted"] is True;assert manifest["issuer"]["cik"]=="0000004904";assert result("AEP")["source_ledger"]["runtime_source_verification"]["verified"]

def test_complete_capex_and_ttm_lineages_are_exact():
    aep=result("AEP")["source_ledger"];assert aep["annual_utility_cash_history"][1]["capital_expenditures"]["value"]==12_036_000_000;assert aep["ttm_utility_cash_state"]["capital_expenditures"]["value"]==13_584_000_000
    etr=result("ETR")["source_ledger"];assert etr["ttm_utility_cash_state"]["capital_expenditures"]["value"]==9_373_143_000
    lnt=result("LNT")["source_ledger"];assert lnt["annual_utility_cash_history"][1]["capital_expenditures"]["value"]==2_483_000_000;assert lnt["ttm_utility_cash_state"]["capital_expenditures"]["value"]==2_440_000_000
    wec=result("WEC")["source_ledger"];assert wec["annual_utility_cash_history"][1]["capital_expenditures"]["value"]==4_398_100_000;assert wec["ttm_utility_cash_state"]["capital_expenditures"]["value"]==4_947_500_000

def test_fcfe_routes_replay_and_only_funding_varies():
    for ticker in {i.ticker for i in BATCH_45_MANIFEST}-RESIDUAL_TICKERS:
        r=result(ticker);reported=r["reported_inputs"];rows=r["scenario_rows"];assert len({x["growth_rate"] for x in rows})==len({x["terminal_growth"] for x in rows})==len({x["cost_of_equity"] for x in rows})==len({x["shares"] for x in rows})==1
        states={x["name"]:EquityCashFlowState(x["cash_flow"],x["growth_rate"],x["terminal_growth"],x["cost_of_equity"]) for x in rows};replay,_=practical_equity_cash_flow_range(states=states,diluted_shares=rows[0]["shares"],forecast_years=10,maximum_terminal_share=.90);assert replay.as_dict()==pytest.approx(r["scenario_range"])
        for x in rows:assert x["cash_flow"]==pytest.approx(mixed_utility_fcfe(operating_cash_flow=reported["ttm_operating_cash_flow"],capital_expenditures=reported["ttm_capital_expenditures"],net_income=reported["model_income_before_parent_allocation"],debt_funding_share=x["debt_funding_share"],parent_cash_flow_share=reported["parent_cash_flow_share"]))
        assert r["source_ledger"]["funding_clipping"]["raw"]

def test_residual_fallbacks_use_common_equity_without_ev_debt_bridge():
    for ticker in RESIDUAL_TICKERS:
        r=result(ticker);assert r["governed_assumptions"]["ev_debt_bridge_applied"] is False;assert r["reported_inputs"]["ending_common_equity"]>0;assert r["reported_inputs"]["ttm_common_earnings"]>0;assert r["source_ledger"]["fcfe_route_rejected"]["raw_debt_funding_share"];assert r["governed_assumptions"]["scenario_calibration"].startswith("cost_of_equity_only");assert len({row["current_roe"] for row in r["scenario_rows"]})==1
    d=result("D");assert d["reported_inputs"]["ending_common_equity"]==27_931_000_000;assert d["source_ledger"]["equity_allocation"]["current"]["preferred_equity"]["value"]==991_000_000
    assert result("PNW")["source_ledger"]["fcfe_route_rejected"]["observed_error"].endswith("degenerate")
    assert result("PEG")["source_ledger"]["equity_allocation"]["parent_common_equity"]["claim_absence_check"]["reported_vs_estimated"]=="source_bounded_absence"

def test_public_model_identity_availability_reliability_and_calculator_match():
    from app.us_valuation.calculator import calculate,calculator_view
    from run_batch_45_history import _public
    for issuer in BATCH_45_MANIFEST:
        private=result(issuer.ticker);public=_public(issuer,private);expected="residual_income" if issuer.ticker in RESIDUAL_TICKERS else "fcfe_dcf";assert public["model_policy"]["primary"]==expected;assert public["availability_type"]=="conditional_estimate";assert "RELIABILITY_PAYLOAD_INVALID" not in public["reliability"]["reasons"];view=calculator_view(public);assert view["can_calculate"];assert calculate(public,overrides={},manual_price=None)["result"]==pytest.approx(private["scenario_range"]);encoded=json.dumps(public)
        assert set(public["scenarios"])=={"bear","base","bull"}
        if expected=="fcfe_dcf":
            assert view["model_family"]=="utility_fcfe"
            funding=view["defaults"]["debt_funding_share"]
            if funding<1:assert calculate(public,overrides={"debt_funding_share":min(1.,funding+.01)},manual_price=None)["result"]["base"]>private["scenario_range"]["base"]
        for key in ("source_ledger","reported_inputs","governed_assumptions","annual_utility_cash_history","raw_debt_funding_share"):assert key not in encoded

def test_source_tampering_fails_closed(tmp_path):
    source=tmp_path/"sources";shutil.copytree(KW["source_root"]/"ES",source/"ES");(source/"ES/companyfacts.json").write_text("{}")
    with pytest.raises(ValueError,match="hash mismatch"):build_batch_45_history_result(ticker="ES",**{**KW,"source_root":source})

def test_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_45_history import run
    report=run(output_root=tmp_path/"candidate",**KW);assert (report["attempted_count"],report["pass_count"],report["conditional_count"],report["withheld_count"],report["numeric_count"])==(10,0,10,0,10);assert report["denominator_tickers"]==[i.ticker for i in BATCH_45_MANIFEST];assert report["batch_44_dependency_status"]=="confirmed_batch_44_recovery_catalog_and_bookkeeping_bound";assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
