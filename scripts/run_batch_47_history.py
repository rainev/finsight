#!/usr/bin/env python3
"""Stage Batch 47 utility-equity candidates without confirmation-state writes."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/"backend") not in sys.path:sys.path.insert(0,str(ROOT/"backend"))
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_47 import BATCH_47_MANIFEST,BATCH_47_TICKERS,BATCH_47_VALUATION_DATE
from app.us_valuation.batch_47_history import BATCH_47_HISTORY_VERSION,build_batch_47_history_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_08_history import _base
from run_batch_15_history import WITHHELD_REGISTER

def _public(issuer,result):
    a=result["governed_assumptions"];scenario=result["scenario_range"]
    common={"forecast_policy_version":BATCH_47_HISTORY_VERSION,"forecast_years":a["forecast_years"],"history_policy_version":a["history_policy_version"],"history_years_used":a["history_years_used"],"normalization_basis":a["normalization_basis"],"assumption_source_mix":a["assumption_source_mix"],"equity_floor_applied":False,"equity_floor_basis":a["equity_floor_basis"],"source_policy":"Reported SEC utility cash, financing, equity and share facts plus transparent governed assumptions; no stock price or analyst target."}
    if result["availability_type"]=="not_available":
        primary="residual_income";model={"model":primary,"output_type":"intrinsic_value_per_share","currency":"USD","intrinsic_value_per_share":None,"publication_state":"withheld","errors":[result["warning"]],"warnings":[a["invalidation"]]};assumptions={**common,"forecast_mode":"unavailable_merchant_normalization_scope"}
    elif result["method"]=="regulated_utility_fcfe":
        primary="fcfe_dcf";model={"model":primary,"output_type":"intrinsic_value_per_share","currency":"USD","intrinsic_value_per_share":scenario["base"],"publication_state":"review_required","errors":[],"warnings":[result["warning"]]};reported=result["reported_inputs"];share=reported["share_count"];assumptions={**common,"forecast_mode":"utility_fcfe_exact","initial_revenue_growth":a["growth_rate"],"cost_of_equity":a["cost_of_equity"],"terminal_growth":a["terminal_growth"],"operating_cash_flow_per_share":reported["ttm_operating_cash_flow"]/share,"capital_expenditures_per_share":reported["ttm_capital_expenditures"]/share,"model_income_before_parent_allocation_per_share":reported["model_income_before_parent_allocation"]/share,"parent_cash_flow_share":reported["parent_cash_flow_share"],"debt_funding_share_low":a["debt_funding_share"][0],"debt_funding_share":a["debt_funding_share"][1],"debt_funding_share_high":a["debt_funding_share"][2]}
    else:
        base=result["scenario_rows"][1]
        primary="residual_income";model={"model":primary,"output_type":"intrinsic_value_per_share","currency":"USD","intrinsic_value_per_share":scenario["base"],"publication_state":"review_required","errors":[],"warnings":[result["warning"]]};assumptions={**common,"forecast_mode":"residual_income_exact","book_value_per_share":base["book_value_per_share"],"current_roe":base["current_roe"],"current_payout_ratio":base["current_payout_ratio"],"cost_of_equity":base["cost_of_equity"],"terminal_roe":base["terminal_roe"],"terminal_growth":base["terminal_growth"]}
    conditional_model={"model":"conditional_estimate","output_type":"conditional_value_per_share","currency":"USD","conditional_value_per_share":scenario["base"],"publication_state":"review_required","errors":[],"warnings":[result["warning"]]}
    value=sanitize_public_artifact(_base(issuer,result,primary="conditional_estimate" if result["availability_type"]!="not_available" else primary,model=conditional_model if result["availability_type"]!="not_available" else model,assumptions=assumptions));public_method=result["method"];value["primary_valuation_method"]=public_method;value["model_policy"]["primary"]=primary;value["model_policy"].pop("fallback_from",None);value["model_policy"]["reason"]=result["warning"];value["models"]={primary:model};value["scenarios"]={} if result["availability_type"]=="not_available" else {name:{primary:{"model":primary,"intrinsic_value_per_share":scenario[key],"publication_state":"review_required"}} for name,key in zip(("bear","base","bull"),("low","base","high"))};value["issuer"]["classification_reason"]="Frozen Batch 47 utility source, financing, equity and model review.";value["methodology"]["forecast_policy"]=BATCH_47_HISTORY_VERSION;value["methodology"]["sector_framework"]=public_method;value["forecast_quality"]["policy_version"]=BATCH_47_HISTORY_VERSION
    if result["history_reliability"] is not None:value["reliability"]=result["history_reliability"]
    value.pop("automated_review",None);value=sanitize_public_artifact(value)
    if value["availability_type"]!=result["availability_type"] or value["scenario_range"]["base"]!=scenario["base"] or value["model_policy"]["primary"]!=primary:raise RuntimeError(issuer.ticker)
    return value

def run(*,source_root:Path,structural_root:Path,event_root:Path,output_root:Path,structural_cache_root:Path):
    before={str(p):_tree(p) for p in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();withheld=hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest();cases=[];reliability={"High":0,"Medium":0,"Low":0}
    for issuer in BATCH_47_MANIFEST:
        result=build_batch_47_history_result(ticker=issuer.ticker,source_root=source_root,structural_root=structural_root,event_root=event_root,structural_cache_root=structural_cache_root);public=_public(issuer,result);label=result["history_reliability"]["label"] if result["history_reliability"] else None
        if label:reliability[label]+=1
        outcome="conditional" if result["availability_type"]=="conditional_estimate" else "withheld";case={"ticker":issuer.ticker,"outcome":outcome,"availability_type":result["availability_type"],"reliability":label,"method":result["method"],**result["scenario_range"],"history_years_used":a if (a:=result["governed_assumptions"].get("history_years_used")) is not None else 0,"warning":result["warning"]};private={"schema_version":"FINSIGHT-BATCH-47-HISTORY-1","batch":47,"valuation_date":BATCH_47_VALUATION_DATE,"issuer":{"ticker":issuer.ticker,"cik":issuer.cik,"issuer_name":issuer.issuer_name},"history_backed":result,"controlled_outcome":case};_immutable(output_root/"generated"/issuer.ticker/"valuation-private.json",_json(private));_immutable(output_root/"staged-public"/f"{issuer.ticker}.json",_json(public));cases.append(case)
    after={str(p):_tree(p) for p in PROTECTED}
    if before!=after or watch!=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld!=hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():raise RuntimeError("protected state changed")
    report={"schema_version":"FINSIGHT-BATCH-47-HISTORY-REPORT-1","batch":47,"valuation_date":BATCH_47_VALUATION_DATE,"policy_version":BATCH_47_HISTORY_VERSION,"denominator_tickers":list(BATCH_47_TICKERS),"attempted_count":10,"pass_count":0,"conditional_count":sum(r["outcome"]=="conditional" for r in cases),"withheld_count":sum(r["outcome"]=="withheld" for r in cases),"numeric_count":sum(r["outcome"]!="withheld" for r in cases),"pass_tickers":[],"conditional_tickers":[r["ticker"] for r in cases if r["outcome"]=="conditional"],"withheld_tickers":[r["ticker"] for r in cases if r["outcome"]=="withheld"],"reliability_counts":reliability,"serving_artifacts_changed":False,"serving_hash_before":before,"serving_hash_after":after,"watchlist_changed":False,"watchlist_sha256":watch,"withheld_register_changed":False,"withheld_register_sha256":withheld,"batch_46_dependency_status":"confirmed_batch_46_recovery_catalog_and_bookkeeping_bound","cases":cases};_immutable(output_root/"batch-47-report.json",_json(report));return report
def main():
    p=argparse.ArgumentParser();p.add_argument("--source-root",type=Path,required=True);p.add_argument("--structural-root",type=Path,required=True);p.add_argument("--event-root",type=Path,required=True);p.add_argument("--structural-cache-root",type=Path,required=True);p.add_argument("--output-root",type=Path,required=True);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ("attempted_count","pass_count","conditional_count","withheld_count","numeric_count","reliability_counts","batch_46_dependency_status")},sort_keys=True))
if __name__=="__main__":main()
