#!/usr/bin/env python3
"""Stage history-backed Batch 10 outcomes without serving or watchlist writes."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_10 import BATCH_10_MANIFEST,BATCH_10_TICKERS,BATCH_10_VALUATION_DATE
from app.us_valuation.batch_10_history import BATCH_10_HISTORY_VERSION,build_batch_10_history_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_08_history import _public as _prior_public
def _public(issuer,result):
 policy_version=result.get('model_version') or BATCH_10_HISTORY_VERSION;value=_prior_public(issuer,result);value['issuer']['classification_reason']='Frozen Batch 10 lane plus issuer-specific history and event review.';value['public_assumptions']['forecast_policy_version']=policy_version;value['forecast_quality']['policy_version']=policy_version;value['methodology']['forecast_policy']=policy_version
 if issuer.ticker=='KMB' and result['availability_type']=='not_available':value['public_assumptions']['forecast_mode']='unavailable_transaction_state'
 if issuer.ticker=='KMB' and result['availability_type']=='conditional_estimate':
  value['public_assumptions']['forecast_mode']='current_state_post_ifp_pre_kenvue';value['model_policy']['reason']='Conditional Low current-state estimate using reported continuing operations and completed IFP transaction terms.'
 value=sanitize_public_artifact(value)
 if value['availability_type']!=result['availability_type'] or value['scenario_range']['base']!=result['scenario_range']['base']:raise RuntimeError(f'{issuer.ticker}: public mismatch')
 return value
def run(*,source_root:Path,structural_root:Path,output_root:Path):
 source_root,structural_root,output_root=map(Path,(source_root,structural_root,output_root));before={str(root):_tree(root) for root in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();cases=[];reliability={'High':0,'Medium':0,'Low':0}
 for issuer in BATCH_10_MANIFEST:
  result=build_batch_10_history_result(ticker=issuer.ticker,source_root=source_root,structural_root=structural_root);public=_public(issuer,result);availability=result['availability_type'];outcome='pass' if availability=='available' else 'conditional' if availability=='conditional_estimate' else 'withheld';label=None if result['history_reliability'] is None else result['history_reliability']['label'];
  if label:reliability[label]+=1
  case={'ticker':issuer.ticker,'outcome':outcome,'availability_type':availability,'reliability':label,'method':result['method'],**result['scenario_range'],'history_years_used':result['governed_assumptions']['history_years_used'],'warning':result['warning']};private={'schema_version':'FINSIGHT-BATCH-10-HISTORY-1','batch':10,'valuation_date':BATCH_10_VALUATION_DATE,'issuer':{'ticker':issuer.ticker,'cik':issuer.cik,'issuer_name':issuer.issuer_name},'history_backed':result,'controlled_outcome':case};_immutable(output_root/'generated'/issuer.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{issuer.ticker}.json',_json(public));cases.append(case)
 after={str(root):_tree(root) for root in PROTECTED};watch_after=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
 if before!=after or watch!=watch_after:raise RuntimeError('Batch 10 changed protected state')
 report={'schema_version':'FINSIGHT-BATCH-10-HISTORY-REPORT-1','batch':10,'valuation_date':BATCH_10_VALUATION_DATE,'policy_version':BATCH_10_HISTORY_VERSION,'denominator_tickers':list(BATCH_10_TICKERS),'attempted_count':10,'pass_count':sum(r['outcome']=='pass' for r in cases),'conditional_count':sum(r['outcome']=='conditional' for r in cases),'withheld_count':sum(r['outcome']=='withheld' for r in cases),'numeric_count':sum(r['outcome']!='withheld' for r in cases),'pass_tickers':[r['ticker'] for r in cases if r['outcome']=='pass'],'conditional_tickers':[r['ticker'] for r in cases if r['outcome']=='conditional'],'withheld_tickers':[r['ticker'] for r in cases if r['outcome']=='withheld'],'reliability_counts':reliability,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'watchlist_changed':False,'watchlist_sha256':watch,'cases':cases};_immutable(output_root/'batch-10-report.json',_json(report));return report
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--structural-root',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('attempted_count','pass_count','conditional_count','withheld_count','numeric_count','reliability_counts','serving_artifacts_changed','watchlist_changed')},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
