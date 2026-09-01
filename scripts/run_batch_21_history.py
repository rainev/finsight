#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend')) if str(ROOT/'backend') not in sys.path else None
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_21 import BATCH_21_MANIFEST,BATCH_21_TICKERS,BATCH_21_VALUATION_DATE
from app.us_valuation.batch_21_history import BATCH_21_HISTORY_VERSION,EQUITY_EARNINGS_TICKERS,build_batch_21_history_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_08_history import _public as prior_public
from run_batch_15_history import WITHHELD_REGISTER
def _public(i,r):
 v=prior_public(i,r);v['issuer']['classification_reason']='Frozen Batch 21 Industrials lane with source/history/claim/transaction review.';v['public_assumptions']['forecast_policy_version']=BATCH_21_HISTORY_VERSION;v['forecast_quality']['policy_version']=BATCH_21_HISTORY_VERSION;v['methodology']['forecast_policy']=BATCH_21_HISTORY_VERSION;v['model_policy']['reason']=r['warning'];v['public_assumptions']['forecast_mode']='normalized_equity_earnings' if i.ticker in EQUITY_EARNINGS_TICKERS else 'history_backed_normalized_cash_conversion';
 if i.ticker in EQUITY_EARNINGS_TICKERS:v['public_assumptions']['valuation_basis']='mixed_industrial_finance_residual_income'
 else:v['public_assumptions']['forecast_years']=r['governed_assumptions']['forecast_years']
 return sanitize_public_artifact(v)
def run(*,source_root:Path,structural_root:Path,output_root:Path):
 before={str(r):_tree(r) for r in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();withheld=hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest();cases=[];rel={'High':0,'Medium':0,'Low':0}
 for i in BATCH_21_MANIFEST:
  r=build_batch_21_history_result(ticker=i.ticker,source_root=source_root,structural_root=structural_root);pub=_public(i,r);out='pass' if r['availability_type']=='available' else 'conditional';label=r['history_reliability']['label'];rel[label]+=1;case={'ticker':i.ticker,'outcome':out,'availability_type':r['availability_type'],'reliability':label,'method':r['method'],**r['scenario_range'],'history_years_used':r['governed_assumptions'].get('history_years_used'),'warning':r['warning']};private={'schema_version':'FINSIGHT-BATCH-21-HISTORY-1','batch':21,'valuation_date':BATCH_21_VALUATION_DATE,'issuer':{'ticker':i.ticker,'cik':i.cik,'issuer_name':i.issuer_name},'history_backed':r,'controlled_outcome':case};_immutable(output_root/'generated'/i.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{i.ticker}.json',_json(pub));cases.append(case)
 after={str(r):_tree(r) for r in PROTECTED}
 if before!=after or watch!=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest() or withheld!=hashlib.sha256(WITHHELD_REGISTER.read_bytes()).hexdigest():raise RuntimeError('protected change')
 report={'schema_version':'FINSIGHT-BATCH-21-HISTORY-REPORT-1','batch':21,'valuation_date':BATCH_21_VALUATION_DATE,'policy_version':BATCH_21_HISTORY_VERSION,'denominator_tickers':list(BATCH_21_TICKERS),'attempted_count':10,'pass_count':sum(x['outcome']=='pass' for x in cases),'conditional_count':sum(x['outcome']=='conditional' for x in cases),'withheld_count':0,'numeric_count':10,'pass_tickers':[x['ticker'] for x in cases if x['outcome']=='pass'],'conditional_tickers':[x['ticker'] for x in cases if x['outcome']=='conditional'],'withheld_tickers':[],'reliability_counts':rel,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'watchlist_changed':False,'watchlist_sha256':watch,'withheld_register_changed':False,'withheld_register_sha256':withheld,'cases':cases};_immutable(output_root/'batch-21-report.json',_json(report));return report
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--structural-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('pass_count','conditional_count','withheld_count','numeric_count','reliability_counts')},sort_keys=True))
if __name__=='__main__':main()
