#!/usr/bin/env python3
"""Stage launch-first Batch 04 baselines without serving writes."""

from __future__ import annotations

import argparse,hashlib,json,shutil,sys,tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/"backend"
if str(BACKEND) not in sys.path:sys.path.insert(0,str(BACKEND))
from app.us_valuation.artifacts import PUBLIC_SCHEMA_VERSION,sanitize_public_artifact
from app.us_valuation.batch_04 import BATCH_04_MANIFEST,BATCH_04_TICKERS,BATCH_04_VALUATION_DATE
from app.us_valuation.batch_04_launch_first import BATCH_04_LAUNCH_FIRST_VERSION,build_batch_04_launch_first_result
from app.us_valuation.reliability import relative_movement

PROTECTED=(ROOT/"backend/app/data/us_valuation_catalogs",ROOT/"frontend/public/data",ROOT/"frontend/src/research/generated")
WATCHLIST=ROOT/"backend/app/us_valuation/config/universe_reset_recovery_learning_watchlist.json"
def _json(v):return (json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n").encode()
def _tree(root):
 h=hashlib.sha256();
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file()):h.update(p.relative_to(root).as_posix().encode());h.update(b'\0');h.update(hashlib.sha256(p.read_bytes()).digest());h.update(b'\n')
 return h.hexdigest()
def _immutable(path,raw):
 if path.exists():
  if path.read_bytes()!=raw:raise FileExistsError(path)
  return
 path.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix=f'.{path.stem}-',dir=path.parent))/path.name
 try:stage.write_bytes(raw);stage.replace(path)
 finally:shutil.rmtree(stage.parent,ignore_errors=True)
def _public(issuer,result):
 s=result['scenario_range'];base=s['base'];movement=relative_movement(low=s['low'],base=s['base'],high=s['high'])
 source=result['source_ledger']['controlling_filing'];url=f"https://www.sec.gov/Archives/edgar/data/{int(issuer.cik)}/{source['accession'].replace('-','')}/{source['primary_document']}"
 assumptions=result['governed_assumptions'];cash=assumptions.get('cash_conversion_margin',(0,0,0));shares=assumptions['shares']
 public={"schema_version":PUBLIC_SCHEMA_VERSION,"valuation_date":BATCH_04_VALUATION_DATE,"market":"US","currency":"USD","ticker":issuer.ticker,"issuer":{"cik":issuer.cik,"ticker":issuer.ticker,"issuer_name":issuer.issuer_name,"filing_regime":"10-K_10-Q","accounting_standard":"US-GAAP","sec_sic_code":None,"sec_sic_label":issuer.gics_sub_industry,"finsight_sector":issuer.gics_sector,"primary_archetype":issuer.primary_lane_id,"secondary_archetypes":[],"classification_confidence":.75,"mapping_version":"US-RESET-PARTITION-2026-08-14-2.0","classification_reason":"Frozen Batch 04 lane with launch-first issuer review.","override_applied":True,"source_accessions":[source['accession']]},"source_financial_statement":{"form":source['form'],"period_end":source['period_end'],"filed_date":source['filed'],"accession":source['accession'],"url":url,"note":"Controlling cutoff-eligible filing anchors reported inputs; forecast states are FinSight assumptions."},"primary_valuation_method":result['method'],"model_policy":{"primary":"conditional_estimate","supporting":[],"blend_models":False,"reason":"Launch-first Conditional Low baseline after the primary source-bounded route required refinements.","fallback_from":"fcff_dcf"},"public_assumptions":{"forecast_policy_version":BATCH_04_LAUNCH_FIRST_VERSION,"forecast_years":5,"forecast_mode":"normalized_cash_conversion","cash_conversion_margin_low":cash[0] if cash else 0,"cash_conversion_margin":cash[1] if cash else 0,"cash_conversion_margin_high":cash[2] if cash else 0,"diluted_shares":shares[1],"diluted_shares_low":shares[2],"diluted_shares_high":shares[0],"equity_floor_applied":s['low']==0,"equity_floor_basis":assumptions.get('equity_floor_basis','not applied'),"source_policy":"Reported SEC facts plus governed launch-first assumptions; no stock price or analyst target."},"models":{"conditional_estimate":{"model":"conditional_estimate","output_type":"conditional_value_per_share","currency":"USD","conditional_value_per_share":base,"publication_state":"review_required","errors":[],"warnings":[result['warning']]}},"scenarios":{},"scenario_range":{**s,"label":"conditional decision range; not a probability-weighted forecast or recommendation"},"sensitivities":[],"forecast_quality":{"policy_version":BATCH_04_LAUNCH_FIRST_VERSION,"status":"review_required","errors":[],"warnings":[result['warning']],"checks":{}},"review":{"publication_state":"review_required","confidence_grade":"conditional_low","errors":[],"warnings":[result['warning'],assumptions['invalidation'],assumptions['calculator_calibration']],"price_dependent_inputs_used":False,"prohibited_output_check":{"buy_hold_sell":False,"current_price":False,"trading_multiples":False,"upside_downside":False}},"reliability":{"label":"Low","accounting_label":"High","scenario_label":"Low","model_cap":"Low","source_cap":"Low","accounting_impact_ratio":0.0,"scenario_movement_ratio":movement,"reasons":["CONDITIONAL_EVENT_MODEL","SPECIALIST_MODEL_UNCERTAINTY"]},"methodology":{"forecast_policy":BATCH_04_LAUNCH_FIRST_VERSION,"sector_framework":result['method'],"source_policy":"Reported facts remain private and separate from governed assumptions."},"data_boundary":{"raw_financial_statement_values_included":False,"stock_prices_used":False,"public_payload_contains":"conditional range, confidence reasons, warnings, assumptions, and filing attribution"}}
 value=sanitize_public_artifact(public)
 if value['availability_type']!='conditional_estimate' or value['scenario_range']['base']!=base:raise RuntimeError(issuer.ticker)
 return value
def run(*,source_root:Path,structural_root:Path,output_root:Path):
 source_root,structural_root,output_root=map(Path,(source_root,structural_root,output_root));before={str(r):_tree(r) for r in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();cases=[]
 for issuer in BATCH_04_MANIFEST:
  result=build_batch_04_launch_first_result(ticker=issuer.ticker,source_root=source_root,structural_root=structural_root);public=_public(issuer,result);private={"schema_version":"FINSIGHT-CONTROLLED-BATCH-OUTCOME-1","batch":4,"valuation_date":BATCH_04_VALUATION_DATE,"issuer":{"ticker":issuer.ticker,"cik":issuer.cik,"issuer_name":issuer.issuer_name},"launch_first":result,"controlled_outcome":{"ticker":issuer.ticker,"outcome":"conditional_numeric","availability_type":"conditional_estimate","reliability":"Low",**result['scenario_range']}}
  _immutable(output_root/'generated'/issuer.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{issuer.ticker}.json',_json(public));cases.append({"ticker":issuer.ticker,"outcome":"conditional_numeric","availability_type":"conditional_estimate","reliability":"Low","method":result['method'],**result['scenario_range'],"warning":result['warning']})
 after={str(r):_tree(r) for r in PROTECTED};watch_after=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
 if before!=after or watch!=watch_after:raise RuntimeError('protected state changed')
 report={"schema_version":"FINSIGHT-BATCH-04-LAUNCH-FIRST-REPORT-1","batch":4,"valuation_date":BATCH_04_VALUATION_DATE,"policy_version":BATCH_04_LAUNCH_FIRST_VERSION,"denominator_tickers":list(BATCH_04_TICKERS),"attempted_count":10,"numeric_count":10,"conditional_numeric_count":10,"not_available_count":0,"reliability_counts":{"High":0,"Medium":0,"Low":10},"watchlist_changed":False,"watchlist_sha256":watch,"serving_artifacts_changed":False,"serving_hash_before":before,"serving_hash_after":after,"cases":cases};_immutable(output_root/'launch-first-report.json',_json(report));return report
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--structural-root',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('attempted_count','numeric_count','conditional_numeric_count','not_available_count','serving_artifacts_changed','watchlist_changed')},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
