#!/usr/bin/env python3
"""Replace only CLX in a controlled Batch 09 candidate with its recovery result."""
from __future__ import annotations
import argparse,hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.batch_09 import BATCH_09_MANIFEST,BATCH_09_TICKERS,BATCH_09_VALUATION_DATE
from app.us_valuation.batch_09_recovery import BATCH_09_RECOVERY_VERSION,build_clx_recovery_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_09_history import _public
def run(*,initial_root:Path,source_root:Path,recovered_structural:Path,output_root:Path):
 initial_root,output_root=Path(initial_root),Path(output_root);before={str(root):_tree(root) for root in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();result=build_clx_recovery_result(source_root=Path(source_root),recovered_structural=Path(recovered_structural));cases=[]
 for issuer in BATCH_09_MANIFEST:
  if issuer.ticker=='CLX':
   case={'ticker':'CLX','outcome':'conditional','availability_type':result['availability_type'],'reliability':result['history_reliability']['label'],'method':result['method'],**result['scenario_range'],'history_years_used':result['governed_assumptions']['history_years_used'],'warning':result['warning']};private={'schema_version':'FINSIGHT-BATCH-09-RECOVERY-1','batch':9,'valuation_date':BATCH_09_VALUATION_DATE,'issuer':{'ticker':issuer.ticker,'cik':issuer.cik,'issuer_name':issuer.issuer_name},'recovery':result,'controlled_outcome':case};public=_public(issuer,result);_immutable(output_root/'generated'/'CLX'/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/'CLX.json',_json(public))
  else:
   private=json.loads((initial_root/'generated'/issuer.ticker/'valuation-private.json').read_text());public=json.loads((initial_root/'staged-public'/f'{issuer.ticker}.json').read_text());case=private['controlled_outcome'];_immutable(output_root/'generated'/issuer.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{issuer.ticker}.json',_json(public))
  cases.append(case)
 after={str(root):_tree(root) for root in PROTECTED};watch_after=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
 if before!=after or watch!=watch_after:raise RuntimeError('Batch 09 recovery changed protected state')
 report={'schema_version':'FINSIGHT-BATCH-09-RECOVERY-REPORT-1','batch':9,'valuation_date':BATCH_09_VALUATION_DATE,'policy_version':BATCH_09_RECOVERY_VERSION,'denominator_tickers':list(BATCH_09_TICKERS),'attempted_count':10,'recovery_attempted_tickers':['CLX'],'recovered_tickers':['CLX'],'pass_count':sum(r['outcome']=='pass' for r in cases),'conditional_count':sum(r['outcome']=='conditional' for r in cases),'withheld_count':sum(r['outcome']=='withheld' for r in cases),'numeric_count':sum(r['outcome']!='withheld' for r in cases),'pass_tickers':[r['ticker'] for r in cases if r['outcome']=='pass'],'conditional_tickers':[r['ticker'] for r in cases if r['outcome']=='conditional'],'withheld_tickers':[r['ticker'] for r in cases if r['outcome']=='withheld'],'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'watchlist_changed':False,'watchlist_sha256':watch,'cases':cases};_immutable(output_root/'batch-09-recovery-report.json',_json(report));return report
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--initial-root',required=True,type=Path);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--recovered-structural',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('pass_count','conditional_count','withheld_count','numeric_count','recovered_tickers','serving_artifacts_changed','watchlist_changed')},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
