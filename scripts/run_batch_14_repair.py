#!/usr/bin/env python3
"""Stage the user-authorized Batch 14 HCA/REGN Pass repair without protected writes."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_14 import BATCH_14_MANIFEST,BATCH_14_TICKERS,BATCH_14_VALUATION_DATE
from app.us_valuation.batch_14_repair import BATCH_14_REPAIR_VERSION,REPAIRED_PASS_TICKERS,build_batch_14_repair_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_14_history import _public as _initial_public
WITHHELD_REGISTER=ROOT/'backend/app/us_valuation/config/universe_reset_withheld.json'
def _public(issuer,result):
 value=_initial_public(issuer,result);value['public_assumptions']['forecast_policy_version']=BATCH_14_REPAIR_VERSION if issuer.ticker in REPAIRED_PASS_TICKERS else value['public_assumptions']['forecast_policy_version'];value['forecast_quality']['policy_version']=BATCH_14_REPAIR_VERSION if issuer.ticker in REPAIRED_PASS_TICKERS else value['forecast_quality']['policy_version'];value['methodology']['forecast_policy']=BATCH_14_REPAIR_VERSION if issuer.ticker in REPAIRED_PASS_TICKERS else value['methodology']['forecast_policy']
 if issuer.ticker in REPAIRED_PASS_TICKERS:
  value['model_policy']['reason']=result['warning']
 value=sanitize_public_artifact(value)
 if value['availability_type']!=result['availability_type'] or value['scenario_range']['base']!=result['scenario_range']['base']:raise RuntimeError(f'{issuer.ticker}: repaired public mismatch')
 return value
def run(*,source_root:Path,structural_root:Path,event_root:Path,output_root:Path):
 source_root,structural_root,event_root,output_root=map(Path,(source_root,structural_root,event_root,output_root));before={str(r):_tree(r) for r in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();withheld=hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest();cases=[];reliability={'High':0,'Medium':0,'Low':0}
 for issuer in BATCH_14_MANIFEST:
  result=build_batch_14_repair_result(ticker=issuer.ticker,source_root=source_root,structural_root=structural_root,event_root=event_root);public=_public(issuer,result);availability=result['availability_type'];outcome='pass' if availability=='available' else 'conditional' if availability=='conditional_estimate' else 'withheld';label=result['history_reliability']['label'];reliability[label]+=1;case={'ticker':issuer.ticker,'outcome':outcome,'availability_type':availability,'reliability':label,'method':result['method'],**result['scenario_range'],'history_years_used':result['governed_assumptions']['history_years_used'],'warning':result['warning']};private={'schema_version':'FINSIGHT-BATCH-14-REPAIR-1','batch':14,'valuation_date':BATCH_14_VALUATION_DATE,'issuer':{'ticker':issuer.ticker,'cik':issuer.cik,'issuer_name':issuer.issuer_name},'repaired':result,'controlled_outcome':case};_immutable(output_root/'generated'/issuer.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{issuer.ticker}.json',_json(public));cases.append(case)
 after={str(r):_tree(r) for r in PROTECTED};watch_after=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();withheld_after=hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest()
 if before!=after or watch!=watch_after or withheld!=withheld_after:raise RuntimeError('Batch 14 repair changed protected or cumulative state')
 report={'schema_version':'FINSIGHT-BATCH-14-REPAIR-REPORT-1','batch':14,'valuation_date':BATCH_14_VALUATION_DATE,'policy_version':BATCH_14_REPAIR_VERSION,'denominator_tickers':list(BATCH_14_TICKERS),'repaired_tickers':sorted(REPAIRED_PASS_TICKERS),'attempted_count':9,'final_pass_count':sum(r['outcome']=='pass' for r in cases),'final_conditional_count':sum(r['outcome']=='conditional' for r in cases),'final_withheld_count':sum(r['outcome']=='withheld' for r in cases),'final_numeric_count':sum(r['outcome']!='withheld' for r in cases),'pass_tickers':[r['ticker'] for r in cases if r['outcome']=='pass'],'conditional_tickers':[r['ticker'] for r in cases if r['outcome']=='conditional'],'withheld_tickers':[r['ticker'] for r in cases if r['outcome']=='withheld'],'reliability_counts':reliability,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'watchlist_changed':False,'watchlist_sha256':watch,'withheld_register_changed':False,'withheld_register_sha256':withheld,'cases':cases};_immutable(output_root/'batch-14-repair-report.json',_json(report));return report
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--structural-root',required=True,type=Path);p.add_argument('--event-root',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('attempted_count','repaired_tickers','final_pass_count','final_conditional_count','final_withheld_count','final_numeric_count','reliability_counts','serving_artifacts_changed','watchlist_changed','withheld_register_changed')},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
