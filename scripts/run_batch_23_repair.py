#!/usr/bin/env python3
"""Stage the authorized Batch 23 whole-Conditional repair without protected writes."""
from __future__ import annotations
from collections import Counter
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend')) if str(ROOT/'backend') not in sys.path else None
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_23 import BATCH_23_MANIFEST,BATCH_23_TICKERS,BATCH_23_VALUATION_DATE
from app.us_valuation.batch_23_repair import ATTEMPTED_TICKERS,BATCH_23_REPAIR_VERSION,build_batch_23_repair_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_23_history import _public as _initial_public
APPROVED_INITIAL_REPORT_SHA256='2e102ab7ca0529ab3fa2c44a78e86d8a1f4842e4418acd2ea9b61b812868933e';APPROVED_INITIAL_TREE_SHA256='1d556f9da256e617a25ca566836579688292e1559e50ecc133354ff293661278'
def _sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _validate(root):
 root=Path(root);p=root/'batch-23-report.json';r=json.loads(p.read_text())
 if r.get('schema_version')!='FINSIGHT-BATCH-23-HISTORY-REPORT-1' or tuple(r.get('denominator_tickers',()))!=BATCH_23_TICKERS or (r.get('pass_count'),r.get('conditional_count'),r.get('withheld_count'))!=(2,8,0) or _sha(p)!=APPROVED_INITIAL_REPORT_SHA256 or _tree(root)!=APPROVED_INITIAL_TREE_SHA256:raise ValueError('approved Batch23 candidate required')
 return r
def _public(i,r):
 v=_initial_public(i,r);v['public_assumptions']['forecast_policy_version']=BATCH_23_REPAIR_VERSION;v['forecast_quality']['policy_version']=BATCH_23_REPAIR_VERSION;v['methodology']['forecast_policy']=BATCH_23_REPAIR_VERSION;v['model_policy']['reason']=r['warning'];v=sanitize_public_artifact(v)
 if v['availability_type']!=r['availability_type'] or any(v['scenario_range'].get(k)!=r['scenario_range'][k] for k in ('low','base','high')):raise RuntimeError(i.ticker)
 return v
def run(*,initial_root:Path,source_root:Path,structural_root:Path,repair_source_root:Path,output_root:Path):
 initial=_validate(initial_root);cases0={x['ticker']:x for x in initial['cases']};before={str(x):_tree(x) for x in PROTECTED};watch=_sha(WATCHLIST);withheld=_sha(WITHHELD_REGISTER);cases=[]
 for i in BATCH_23_MANIFEST:
  r=build_batch_23_repair_result(ticker=i.ticker,initial_source_root=source_root,structural_root=structural_root,repair_source_root=repair_source_root);pub=_public(i,r);a='pass' if r['availability_type']=='available' else 'conditional' if r['availability_type']=='conditional_estimate' else 'withheld';old=cases0[i.ticker];case={'ticker':i.ticker,'repair_attempted':i.ticker in ATTEMPTED_TICKERS,'initial_outcome':old['outcome'],'initial_availability_type':old['availability_type'],'outcome':a,'availability_type':r['availability_type'],'reliability':r['history_reliability']['label'] if r['history_reliability'] else None,'method':r['method'],**r['scenario_range'],'history_years_used':r['governed_assumptions'].get('history_years_used'),'warning':r['warning']};private={'schema_version':'FINSIGHT-BATCH-23-WHOLE-REPAIR-1','batch':23,'valuation_date':BATCH_23_VALUATION_DATE,'issuer':{'ticker':i.ticker,'cik':i.cik,'issuer_name':i.issuer_name},'whole_repair':r,'controlled_outcome':case};_immutable(output_root/'generated'/i.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{i.ticker}.json',_json(pub));cases.append(case)
 after={str(x):_tree(x) for x in PROTECTED}
 if before!=after or watch!=_sha(WATCHLIST) or withheld!=_sha(WITHHELD_REGISTER):raise RuntimeError('protected change')
 c=Counter(x['outcome'] for x in cases);report={'schema_version':'FINSIGHT-BATCH-23-WHOLE-REPAIR-REPORT-1','batch':23,'valuation_date':BATCH_23_VALUATION_DATE,'policy_version':BATCH_23_REPAIR_VERSION,'denominator_tickers':list(BATCH_23_TICKERS),'repair_attempted_tickers':[x.ticker for x in BATCH_23_MANIFEST if x.ticker in ATTEMPTED_TICKERS],'attempted_count':len(ATTEMPTED_TICKERS),'pass_count':c['pass'],'conditional_count':c['conditional'],'withheld_count':c['withheld'],'numeric_count':c['pass']+c['conditional'],'upgraded_to_pass_tickers':[x['ticker'] for x in cases if x['initial_outcome']!='pass' and x['outcome']=='pass'],'still_conditional_tickers':[x['ticker'] for x in cases if x['repair_attempted'] and x['outcome']=='conditional'],'pass_tickers':[x['ticker'] for x in cases if x['outcome']=='pass'],'conditional_tickers':[x['ticker'] for x in cases if x['outcome']=='conditional'],'withheld_tickers':[x['ticker'] for x in cases if x['outcome']=='withheld'],'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'watchlist_changed_during_staging':False,'watchlist_sha256':watch,'withheld_register_changed_during_staging':False,'withheld_register_sha256':withheld,'cases':cases};_immutable(output_root/'batch-23-whole-repair-report.json',_json(report));return report
def main():
 p=argparse.ArgumentParser();p.add_argument('--initial-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--structural-root',type=Path,required=True);p.add_argument('--repair-source-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('attempted_count','pass_count','conditional_count','withheld_count','numeric_count','upgraded_to_pass_tickers','still_conditional_tickers','serving_artifacts_changed')},sort_keys=True))
if __name__=='__main__':main()
