#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend')) if str(ROOT/'backend') not in sys.path else None
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_25 import BATCH_25_MANIFEST,BATCH_25_TICKERS,BATCH_25_VALUATION_DATE
from app.us_valuation.batch_25_recovery import BATCH_25_RECOVERY_VERSION,build_batch_25_recovery_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_25_history import _public as _initial_public
APPROVED='af01d74c0c6edc8f5ed57971d56eb14152181b3c88513741ae41a5c0b218acd9'
def _sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _public(i,r):
 v=_initial_public(i,r);v['public_assumptions']['forecast_policy_version']=BATCH_25_RECOVERY_VERSION;v['forecast_quality']['policy_version']=BATCH_25_RECOVERY_VERSION;v['methodology']['forecast_policy']=BATCH_25_RECOVERY_VERSION;v['model_policy']['reason']=r['warning'];
 if i.ticker=='HONA':v['public_assumptions']['forecast_mode']='normalized_equity_earnings';v['public_assumptions']['valuation_basis']='newly_separated_aerospace_equity_earnings'
 return sanitize_public_artifact(v)
def run(*,initial_root:Path,source_root:Path,structural_root:Path,output_root:Path):
 ir=json.loads((Path(initial_root)/'batch-25-report.json').read_text());
 if _sha(Path(initial_root)/'batch-25-report.json')!=APPROVED or (ir['pass_count'],ir['conditional_count'],ir['withheld_count'])!=(2,7,1):raise ValueError('confirmed initial required')
 before={str(x):_tree(x) for x in PROTECTED};watch=_sha(WATCHLIST);withheld=_sha(WITHHELD_REGISTER);cases=[]
 for i in BATCH_25_MANIFEST:
  r=build_batch_25_recovery_result(ticker=i.ticker,source_root=source_root,structural_root=structural_root);p=_public(i,r);out='pass' if r['availability_type']=='available' else 'conditional' if r['availability_type']=='conditional_estimate' else 'withheld';case={'ticker':i.ticker,'outcome':out,'availability_type':r['availability_type'],'reliability':r['history_reliability']['label'] if r['history_reliability'] else None,'method':r['method'],**r['scenario_range'],'warning':r['warning']};_immutable(output_root/'generated'/i.ticker/'valuation-private.json',_json({'batch':25,'issuer':{'ticker':i.ticker,'cik':i.cik},'recovery':r,'controlled_outcome':case}));_immutable(output_root/'staged-public'/f'{i.ticker}.json',_json(p));cases.append(case)
 if before!={str(x):_tree(x) for x in PROTECTED} or watch!=_sha(WATCHLIST) or withheld!=_sha(WITHHELD_REGISTER):raise RuntimeError('protected change')
 report={'schema_version':'FINSIGHT-BATCH-25-RECOVERY-REPORT-1','batch':25,'attempted_count':1,'recovered_to_conditional_tickers':['HONA'],'pass_count':sum(x['outcome']=='pass' for x in cases),'conditional_count':sum(x['outcome']=='conditional' for x in cases),'withheld_count':sum(x['outcome']=='withheld' for x in cases),'numeric_count':sum(x['outcome']!='withheld' for x in cases),'cases':cases,'serving_artifacts_changed':False,'watchlist_changed':False,'withheld_register_changed':False};_immutable(output_root/'batch-25-recovery-report.json',_json(report));return report
def main():
 p=argparse.ArgumentParser();p.add_argument('--initial-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--structural-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);r=run(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('attempted_count','pass_count','conditional_count','withheld_count','numeric_count','recovered_to_conditional_tickers')},sort_keys=True))
if __name__=='__main__':main()
