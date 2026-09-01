from __future__ import annotations

import json
from pathlib import Path
import sys

from app.us_valuation.batch_12 import BATCH_12_MANIFEST,BATCH_12_TICKERS
from app.us_valuation.batch_12_history import PASS_TICKERS,build_batch_12_history_result

ROOT=Path(__file__).resolve().parents[2]; SOURCE=ROOT/"output/batch-12-sec-source-packets-20260828"; STRUCTURAL=ROOT/"output/batch-12-structural-sources-20260828"; sys.path.insert(0,str(ROOT/"scripts"))

def _result(ticker): return build_batch_12_history_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)

def test_batch_12_exact_initial_outcomes_and_ranges():
    rows={ticker:_result(ticker) for ticker in BATCH_12_TICKERS}; assert {ticker for ticker,row in rows.items() if row["availability_type"]=="available"}==set(PASS_TICKERS)==set(); assert {ticker for ticker,row in rows.items() if row["availability_type"]=="conditional_estimate"}==set(BATCH_12_TICKERS)-{"UHS"}; assert {ticker for ticker,row in rows.items() if row["availability_type"]=="not_available"}=={"UHS"}
    for row in rows.values():
        scenario=row["scenario_range"]
        if row["availability_type"]=="not_available": assert scenario=={"low":None,"base":None,"high":None}; continue
        assert 0<=scenario["low"]<=scenario["base"]<=scenario["high"] and scenario["base"]>0; assert row["governed_assumptions"]["history_years_used"]>=3

def test_batch_12_operating_sources_periods_shares_and_bridges():
    expected={"ABT":("2026-06-30",5_603_000_000.,32_608_000_000.,915_000_000.,1_745_014_000.),"BAX":("2026-06-30",2_151_000_000.,9_459_000_000.,10_000_000.,517_000_000.),"BDX":("2026-06-30",708_000_000.,16_808_000_000.,0.,281_603_000.),"BMY":("2026-06-30",11_464_000_000.,43_888_000_000.,607_000_000.,2_048_000_000.),"RVTY":("2026-07-05",1_022_943_000.,3_222_200_000.,8_000_000.,111_746_000.),"LLY":("2026-06-30",8_950_000_000.,54_908_000_000.,2_518_000_000.,894_800_000.),"WST":("2026-06-30",571_800_000.,207_300_000.,3_300_000.,71_900_000.)}
    for ticker,(period,cash,debt,claims,shares) in expected.items():
        row=_result(ticker); assert row["source_ledger"]["controlling_filing"]["period_end"]==period; bridge=row["source_ledger"]["bridge_reconciliation"]; assert bridge["cash_and_investments"]==cash; assert bridge["debt_and_finance_leases"]==debt; assert bridge["preferred_nci_and_other_claims"]==claims; assert bridge["shares"][1]==shares
        assert all(source.get("unit") in {None,"USD","shares","xbrli:shares"} for source in row["source_ledger"]["bridge_sources"])

def test_batch_12_special_flow_and_equity_routes():
    abt=_result("ABT"); assert abt["reported_inputs"]["ttm_revenue"]==46_585_000_000.; assert all(flow["period_end"]=="2026-06-30" for flow in abt["source_ledger"]["flow_sources"].values())
    bax=_result("BAX"); assert bax["reported_inputs"]["ttm_interest"]==246_000_000.; assert bax["source_ledger"]["flow_sources"]["interest_expense"]["method"]=="latest_fy_net_interest_magnitude_plus_current_h1_magnitude_minus_prior_h1_magnitude"; assert bax["source_ledger"]["tax_rate_treatment"]["method"]=="governed_practical_fallback_when_three_positive_annual_effective_tax_observations_are_unavailable"
    lly=_result("LLY"); assert lly["reported_inputs"]["ttm_capex"]==9_893_000_000.; assert lly["reported_inputs"]["ttm_interest"]==1_079_000_000.; assert lly["source_ledger"]["flow_sources"]["capital_expenditures"]["method"]=="latest_fy_plus_current_h1_minus_prior_h1_custom_capex"
    hum=_result("HUM"); cvs=_result("CVS"); assert hum["reported_inputs"]["ttm_common_earnings"]==1_263_000_000.; assert cvs["reported_inputs"]["ttm_common_earnings"]==4_890_000_000.; assert hum["governed_assumptions"]["ev_debt_bridge_applied"] is False; assert cvs["governed_assumptions"]["route_is_equity_level"] is True
    rvty=_result("RVTY"); assert "$32.818M restructuring reserve is an operating liability" in rvty["source_ledger"]["bridge_reconciliation"]["treatment"]
    bdx=_result("BDX"); assert "$181M supplier-finance obligation remains in accounts payable" in bdx["source_ledger"]["bridge_reconciliation"]["treatment"]
    uhs=_result("UHS"); assert uhs["availability_type"]=="not_available"; assert "post-Ireland" in uhs["source_ledger"]["release_condition"]

def test_batch_12_sensitivity_directions():
    for ticker in set(BATCH_12_TICKERS)-{"HUM","CVS","UHS"}:
        scenarios=_result(ticker)["scenario_rows"]; assert scenarios[0]["wacc"]>scenarios[1]["wacc"]>scenarios[2]["wacc"]; assert scenarios[0]["cash_conversion_margin"]<=scenarios[1]["cash_conversion_margin"]<=scenarios[2]["cash_conversion_margin"]; assert scenarios[0]["conditional_value_per_share"]<=scenarios[1]["conditional_value_per_share"]<=scenarios[2]["conditional_value_per_share"]; assert scenarios[0]["shares"]>scenarios[1]["shares"]>scenarios[2]["shares"]
    for ticker in ("HUM","CVS"):
        scenarios=_result(ticker)["scenario_rows"]; assert scenarios[0]["normalized_consolidated_earnings"]<=scenarios[1]["normalized_consolidated_earnings"]<=scenarios[2]["normalized_consolidated_earnings"]; assert scenarios[0]["earnings_multiple"]<scenarios[1]["earnings_multiple"]<scenarios[2]["earnings_multiple"]; assert scenarios[0]["conditional_value_per_share"]<scenarios[1]["conditional_value_per_share"]<scenarios[2]["conditional_value_per_share"]

def test_batch_12_public_contract_and_structural_receipts():
    from run_batch_12_history import _public
    for issuer in BATCH_12_MANIFEST:
        result=_result(issuer.ticker); public=_public(issuer,result); raw=json.dumps(public); assert public["availability_type"]==result["availability_type"]; assert public["scenario_range"]["base"]==result["scenario_range"]["base"]; assert "source_ledger" not in raw and "company_history_profile" not in raw
    summary=json.loads((STRUCTURAL/"summary.json").read_text()); assert summary["attempted"]==summary["parsed"]==10 and summary["failed"]==0; assert summary["reused_tickers"]==["BDX"]; assert summary["captured_tickers"]==["ABT","BAX","BMY","RVTY","HUM","LLY","CVS","WST","UHS"]

def test_batch_12_cutoff_excludes_later_filings_from_selected_sources():
    for ticker in BATCH_12_TICKERS:
        result=_result(ticker); assert result["source_ledger"]["controlling_filing"]["filed"]<="2026-08-14"
        for flow in result["source_ledger"].get("flow_sources",{}).values():
            for source in flow.get("sources",[]):
                filed=source.get("filed") or source.get("filed_date")
                if filed: assert filed<="2026-08-14"
        reconstruction=result["source_ledger"].get("common_earnings_reconstruction",{})
        for source in reconstruction.get("sources",[]):
            filed=source.get("filed") or source.get("filed_date")
            if filed: assert filed<="2026-08-14"

def test_batch_12_structural_wrapper_is_a_reusable_offline_cache():
    from capture_batch_12_structural_sources import _control,_reuse_any_structural
    for issuer in BATCH_12_MANIFEST:
        filing,_manifest=_control(SOURCE,issuer); reused=_reuse_any_structural((STRUCTURAL,),issuer,filing); assert reused is not None
        value,package,reuse_source=reused; assert value["source_accession"]==filing["accession"]; assert package["accession"]==filing["accession"]; assert reuse_source==str(STRUCTURAL)
