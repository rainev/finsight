#!/usr/bin/env python3
"""Stage initial Batch 24 historical/practical outcomes without protected-state writes."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend')) if str(ROOT/'backend') not in sys.path else None
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_24 import BATCH_24_MANIFEST,BATCH_24_TICKERS,BATCH_24_VALUATION_DATE
from app.us_valuation.batch_24_history import BATCH_24_HISTORY_VERSION,FORECAST_YEARS,build_batch_24_history_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_08_history import _public as _prior_public
from run_batch_15_history import WITHHELD_REGISTER
def _public(i,r):
 v=_prior_public(i,r);v['issuer']['classification_reason']='Frozen Batch 24 Industrials lane plus issuer-specific source, history, bridge, program, marketplace, and acquisition review.';v['public_assumptions']['forecast_policy_version']=BATCH_24_HISTORY_VERSION;v['public_assumptions']['forecast_mode']='history_backed_normalized_cash_conversion';v['public_assumptions']['forecast_years']=FORECAST_YEARS;v['forecast_quality']['policy_version']=BATCH_24_HISTORY_VERSION;v['methodology']['forecast_policy']=BATCH_24_HISTORY_VERSION;v['model_policy']['reason']=r['warning'];v=sanitize_public_artifact(v)
 if v['availability_type']!=r['availability_type'] or v['scenario_range']['base']!=r['scenario_range']['base']:raise RuntimeError(i.ticker)
 return v
def run(*,source_root:Path,structural_root:Path,output_root:Path):
 before={str(x):_tree(x) for x in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();withheld=hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest();cases=[];rel={'High':0,'Medium':0,'Low':0}
 for i in BATCH_24_MANIFEST:
  r=build_batch_24_history_result(ticker=i.ticker,source_root=source_root,structural_root=structural_root);pub=_public(i,r);out='pass' if r['availability_type']=='available' else 'conditional' if r['availability_type']=='conditional_estimate' else 'withheld';label=r['history_reliability']['label'] if r['history_reliability'] else None
  if label:rel[label]+=1
  case={'ticker':i.ticker,'outcome':out,'availability_type':r['availability_type'],'reliability':label,'method':r['method'],**r['scenario_range'],'history_years_used':r['governed_assumptions'].get('history_years_used'),'warning':r['warning']};private={'schema_version':'FINSIGHT-BATCH-24-HISTORY-1','batch':24,'valuation_date':BATCH_24_VALUATION_DATE,'issuer':{'ticker':i.ticker,'cik':i.cik,'issuer_name':i.issuer_name},'history_backed':r,'controlled_outcome':case};_immutable(output_root/'generated'/i.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{i.ticker}.json',_json(pub));cases.append(case)
 after={str(x):_tree(x) for x in PROTECTED}
 if before!=after or watch!=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld!=hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():raise RuntimeError('protected change')
 report={'schema_version':'FINSIGHT-BATCH-24-HISTORY-REPORT-1','batch':24,'valuation_date':BATCH_24_VALUATION_DATE,'policy_version':BATCH_24_HISTORY_VERSION,'denominator_tickers':list(BATCH_24_TICKERS),'attempted_count':10,'pass_count':sum(x['outcome']=='pass' for x in cases),'conditional_count':sum(x['outcome']=='conditional' for x in cases),'withheld_count':sum(x['outcome']=='withheld' for x in cases),'numeric_count':sum(x['outcome']!='withheld' for x in cases),'pass_tickers':[x['ticker'] for x in cases if x['outcome']=='pass'],'conditional_tickers':[x['ticker'] for x in cases if x['outcome']=='conditional'],'withheld_tickers':[x['ticker'] for x in cases if x['outcome']=='withheld'],'reliability_counts':rel,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'watchlist_changed':False,'watchlist_sha256':watch,'withheld_register_changed':False,'withheld_register_sha256':withheld,'cases':cases};_immutable(output_root/'batch-24-report.json',_json(report));return report
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--structural-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('attempted_count','pass_count','conditional_count','withheld_count','numeric_count','reliability_counts','serving_artifacts_changed','watchlist_changed','withheld_register_changed')},sort_keys=True))
if __name__=='__main__':main()
