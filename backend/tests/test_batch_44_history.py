import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_44 import BATCH_44_MANIFEST
from app.us_valuation.batch_44_history import build_batch_44_history_result
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf


ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
KW={"source_root":ROOT/"output/batch-44-sec-source-packets-20260907","structural_root":ROOT/"output/batch-44-structural-sources-20260907","event_root":ROOT/"output/batch-44-event-review-20260907","structural_cache_root":ROOT/"output/batch-44-structural-cache-20260907","special_annual_root":ROOT/"output/batch-44-special-annual-sources-20260907","xom_annual_root":ROOT/"output/batch-44-xom-annual-source-20260907"}
EXPECTED={
    "MPC":(27.753897350780043,260.6138117576469,658.0283279464621),
    "PSX":(7.689113693919407,80.01927151589591,203.24750514587154),
    "FANG":(68.23467422954272,195.3443178630455,320.3962608731252),
    "BKR":(None,None,None),"AMCR":(None,None,None),
    "DOW":(0.,14.154069823637862,61.211729982981126),
    "CTVA":(2.299428221566588,26.36532045697048,55.29207952226162),
    "APA":(0.,33.396689747336815,73.81186937254579),
    "SW":(None,None,None),
    "XOM":(39.23767756258341,83.64033613314334,138.20400921108578),
}


@lru_cache(None)
def result(ticker): return build_batch_44_history_result(ticker=ticker,**KW)


def test_denominator_sources_values_and_initial_outcomes():
    rows=[result(issuer.ticker) for issuer in BATCH_44_MANIFEST]
    assert len(rows)==10
    assert [row["ticker"] for row in rows if row["availability_type"]=="not_available"]==["BKR","AMCR","SW"]
    assert all(row["availability_type"]=="conditional_estimate" for row in rows if row["ticker"] not in {"BKR","AMCR","SW"})
    for row in rows:
        assert row["source_ledger"]["runtime_source_verification"]["verified"]
        assert row["source_ledger"]["event_sources"]["screened_filings"]
        observed=tuple(row["scenario_range"][key] for key in ("low","base","high"))
        if row["availability_type"]=="not_available": assert observed==EXPECTED[row["ticker"]] and row["history_reliability"] is None
        else: assert observed==pytest.approx(EXPECTED[row["ticker"]]) and all(math.isfinite(value) for value in observed) and row["history_reliability"]["label"]=="Low"


def test_numeric_scenarios_replay_and_floor_only_negative_bears():
    for issuer in BATCH_44_MANIFEST:
        row=result(issuer.ticker)
        for scenario in row["scenario_rows"]:
            state=EnterpriseCashFlowState(scenario["starting_cash_fcff"],scenario["growth"],scenario["terminal_growth"],scenario["wacc"],scenario["cash_and_investments"],scenario["debt_and_finance_leases"],0.,scenario["other_equity_claims"],scenario["shares"])
            replay=enterprise_cash_flow_dcf(state,forecast_years=8,allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
            assert replay==pytest.approx(scenario["raw_value_per_share"])
            assert scenario["conditional_value_per_share"]==pytest.approx(max(0.,replay))
    assert result("DOW")["scenario_rows"][0]["raw_value_per_share"]<0
    assert result("APA")["scenario_rows"][0]["raw_value_per_share"]<0


def test_special_annual_and_current_ttm_lineages_are_exact():
    psx=result("PSX")["source_ledger"]
    assert [row["period_end"] for row in psx["annual_cash_sources"]]==["2023-12-31","2024-12-31","2025-12-31"]
    assert psx["annual_cash_sources"][-1]["capital_expenditures"]["value"]==2_233_000_000
    assert psx["annual_cash_sources"][-1]["capital_expenditures"]["accession"]=="0001534701-26-000006"
    assert psx["flow_sources"]["capital_expenditures"]["value"]==2_531_000_000
    apa=result("APA")["source_ledger"]
    assert apa["flow_sources"]["revenue"]["value"]==8_610_000_000
    assert apa["flow_sources"]["capital_expenditures"]["value"]==2_414_000_000
    xom=result("XOM")["source_ledger"]
    assert xom["annual_cash_sources"][-1]["annual_source_receipt"]["predecessor_cik"]=="0000034088"
    assert xom["annual_cash_sources"][-1]["revenue"]["value"]==332_238_000_000
    assert xom["annual_cash_sources"][-1]["revenue"]["accession"]=="0000034088-26-000045"
    amcr=result("AMCR")["source_ledger"]["flow_sources"]
    assert amcr["revenue"]["method"]=="controlling_fy_is_ttm"
    assert amcr["capital_expenditures"]["value"]==922_000_000
    fang=result("FANG")["source_ledger"]["flow_sources"]
    assert fang["capital_expenditures"]["current_h1"]["concept"].endswith("PaymentsToExploreAndDevelopOilAndGasProperties")
    assert fang["interest_expense"]["current_h1"]["concept"].endswith("InterestPaidNet")


def test_claim_bridges_and_scope_events_are_applied_once():
    expected={"MPC":(33_255_000_000,(8_299_000_000,6_643_000_000,6_643_000_000)),"PSX":(20_565_000_000,(2_871_000_000,1_197_000_000,1_197_000_000)),"FANG":(12_614_000_000,(6_632_000_000,6_085_000_000,6_085_000_000)),"DOW":(17_909_000_000,(2_512_000_000,1_507_000_000,1_507_000_000)),"CTVA":(4_875_000_000,(2_710_000_000,244_000_000,244_000_000)),"APA":(3_743_000_000,(3_855_000_000,923_000_000,923_000_000)),"XOM":(42_368_000_000,(15_799_000_000,6_731_000_000,6_731_000_000))}
    for ticker,(debt,claims) in expected.items():
        bridge=result(ticker)["source_ledger"]["bridge_context"]
        assert bridge["debt"]==debt and bridge["claims"]==pytest.approx(claims)
    assert result("APA")["source_ledger"]["bridge_context"]["excluded_or_separately_treated"]["nci_derivation"]["difference"]==923_000_000
    assert "not a post-separation value" in result("CTVA")["warning"]
    assert "legal continuity" in result("XOM")["source_ledger"]["event_sources"]["treatment"]


def test_three_current_company_history_gates_remain_withheld():
    for ticker in ("BKR","AMCR","SW"):
        row=result(ticker); assert row["scenario_range"]=={"low":None,"base":None,"high":None}; assert row["source_ledger"]["current_ttm_is_diagnostic_only"] is True; assert "Revalue" in row["governed_assumptions"]["invalidation"]
    assert "Chart" in result("BKR")["warning"]
    assert "Berry" in result("AMCR")["warning"]
    assert "one complete" in result("SW")["warning"]


def test_public_contract_calculator_and_private_boundary_are_exact():
    from app.us_valuation.calculator import calculate,calculator_view
    from run_batch_44_history import _public
    for issuer in BATCH_44_MANIFEST:
        private=result(issuer.ticker); public=_public(issuer,private); encoded=json.dumps(public); assert public["model_policy"]["primary"]=="fcff_dcf"; view=calculator_view(public)
        if issuer.ticker=="XOM": assert "/data/34088/" in public["source_financial_statement"]["url"]
        if private["availability_type"]=="not_available": assert not view["can_calculate"]
        else:
            assert view["can_calculate"] and calculate(public,overrides={},manual_price=None)["result"]==pytest.approx(private["scenario_range"])
            assert calculate(public,overrides={"discount_rate":view["defaults"]["discount_rate"]+.01},manual_price=None)["result"]["base"]<private["scenario_range"]["base"]
        for key in ("source_ledger","reported_inputs","governed_assumptions","runtime_source_verification","raw_scenario_rows"): assert key not in encoded


def test_source_tampering_fails_closed(tmp_path):
    source=tmp_path/"sources"; shutil.copytree(KW["source_root"]/"MPC",source/"MPC"); (source/"MPC"/"companyfacts.json").write_text("{}")
    with pytest.raises(ValueError,match="hash mismatch"): build_batch_44_history_result(ticker="MPC",**{**KW,"source_root":source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_44_history import run
    report=run(output_root=tmp_path/"candidate",**KW)
    assert (report["attempted_count"],report["pass_count"],report["conditional_count"],report["withheld_count"],report["numeric_count"])==(10,0,7,3,7)
    assert report["denominator_tickers"]==[issuer.ticker for issuer in BATCH_44_MANIFEST]
    assert report["batch_43_dependency_status"]=="confirmed_batch_43_recovery_catalog_and_bookkeeping_bound"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
