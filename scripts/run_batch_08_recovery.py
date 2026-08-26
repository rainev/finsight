#!/usr/bin/env python3
"""Run the single Batch 08 recovery attempt without serving/register writes."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.batch_08 import BATCH_08_MANIFEST,BATCH_08_TICKERS,BATCH_08_VALUATION_DATE
from app.us_valuation.batch_08_recovery import BATCH_08_RECOVERY_VERSION,evaluate_nclh,recover_aptv
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_08_history import _public

def run(*,source_root:Path,structural_root:Path,initial_root:Path,output_root:Path):
 source_root,structural_root,initial_root,output_root=map(Path,(source_root,structural_root,initial_root,output_root));before={str(root):_tree(root) for root in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
 aptv=recover_aptv(source_root=source_root,structural_root=structural_root);nclh=evaluate_nclh(source_root=source_root,structural_root=structural_root);results={'APTV':aptv,'NCLH':nclh};cases=[]
 for issuer in BATCH_08_MANIFEST:
  if issuer.ticker=='APTV':public=_public(issuer,aptv)
  else:public_raw=(initial_root/'staged-public'/f'{issuer.ticker}.json').read_bytes();_immutable(output_root/'staged-public'/f'{issuer.ticker}.json',public_raw);continue
  _immutable(output_root/'staged-public'/f'{issuer.ticker}.json',_json(public))
 for ticker,result in results.items():
  outcome='conditional_recovery' if ticker=='APTV' else 'withheld_after_recovery';case={'ticker':ticker,'attempt_number':1,'outcome':outcome,'availability_type':result['availability_type'],'method':result['method'],**result['scenario_range']};private={'schema_version':'FINSIGHT-BATCH-08-RECOVERY-1','batch':8,'valuation_date':BATCH_08_VALUATION_DATE,'ticker':ticker,'recovery':result,'recovery_outcome':case};_immutable(output_root/'generated'/ticker/'recovery-private.json',_json(private));cases.append(case)
 after={str(root):_tree(root) for root in PROTECTED};watch_after=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
 if before!=after or watch!=watch_after:raise RuntimeError('Batch 08 recovery changed protected state')
 report={'schema_version':'FINSIGHT-BATCH-08-RECOVERY-REPORT-1','batch':8,'valuation_date':BATCH_08_VALUATION_DATE,'policy_version':BATCH_08_RECOVERY_VERSION,'initial_denominator_tickers':list(BATCH_08_TICKERS),'attempted_tickers':['NCLH','APTV'],'attempted_count':2,'recovered_conditional_count':1,'remaining_withheld_count':1,'recovered_tickers':['APTV'],'remaining_withheld_tickers':['NCLH'],'final_pass_count':2,'final_conditional_count':7,'final_withheld_count':1,'final_numeric_count':9,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'watchlist_changed':False,'watchlist_sha256':watch,'cases':cases};_immutable(output_root/'batch-08-recovery-report.json',_json(report));return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--structural-root',required=True,type=Path);p.add_argument('--initial-root',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('attempted_count','recovered_conditional_count','remaining_withheld_count','final_pass_count','final_conditional_count','final_withheld_count','final_numeric_count','serving_artifacts_changed','watchlist_changed')},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
