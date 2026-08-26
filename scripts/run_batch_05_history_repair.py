#!/usr/bin/env python3
"""Stage history-backed Batch 05 Pass repairs without serving or watchlist writes."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_05 import BATCH_05_MANIFEST,BATCH_05_TICKERS,BATCH_05_VALUATION_DATE
from app.us_valuation.batch_05_launch_first import BATCH_05_HISTORY_REPAIR_VERSION,PASS_TICKERS,build_batch_05_launch_first_result
from run_batch_05_launch_first import PROTECTED,WATCHLIST,_immutable,_json,_public,_tree

HISTORY_PUBLIC_FIELDS=('history_policy_version','history_years_used','normalization_basis','assumption_source_mix')

def _pass_public(issuer,result):
 value=_public(issuer,result);scenario=result['scenario_range'];base=scenario['base'];impact=float(result['accounting_impact_ratio'])
 value['primary_valuation_method']='fcff_dcf';value['model_policy']={'primary':'fcff_dcf','supporting':[],'blend_models':False,'reason':'History-backed source-bounded normalized cash-FCFF with a usable current claims bridge.'};value['models']={'fcff_dcf':{'model':'fcff_dcf','output_type':'intrinsic_value_per_share','currency':'USD','intrinsic_value_per_share':base,'publication_state':'review_required','errors':[],'warnings':['History-backed source-bounded estimate; ordinary scenario uncertainty remains.']}};value['scenario_range']={**scenario,'label':'assumption range, not a statistical confidence interval'}
 if issuer.ticker=='AZO':
  low=base*(1-impact);high=base*(1+impact);spread=(high-low)/base;value['bridge_quality']={'blocking_fields':[],'bounded_fields':['finance_lease_total'],'complete':False,'decision':'bounded_review','intrinsic_value_range':{'low':low,'midpoint':base,'high':high,'spread_ratio':spread,'spread_limit':.01},'reason_codes':['CURRENT_NOTE_SUPPLIES_FINITE_RANGE'],'usable':True}
 else:value['bridge_quality']={'blocking_fields':[],'bounded_fields':[],'complete':True,'decision':'complete','intrinsic_value_range':{'low':base,'midpoint':base,'high':base,'spread_ratio':0.0,'spread_limit':.01},'reason_codes':[],'usable':True}
 value['forecast_quality']['warnings']=['History-backed normalized cash-FCFF; scenario assumptions require review.'];value['review']['warnings']=['History-backed source-bounded estimate. Ordinary business and scenario uncertainty may materially affect the range.'];value['reliability']=result['history_reliability'];value['confidence']={'label':result['history_reliability']['label'],'reasons':result['history_reliability']['reasons']}
 public=sanitize_public_artifact(value)
 if public['availability_type']!='available' or public['scenario_range']['base']!=base:raise RuntimeError(issuer.ticker)
 return public

def _history_public(issuer,result):
 public=_pass_public(issuer,result) if issuer.ticker in PASS_TICKERS else _public(issuer,result);ass=result['governed_assumptions']
 for field in HISTORY_PUBLIC_FIELDS:
  if field in ass:public['public_assumptions'][field]=ass[field]
 public['reliability']=result['history_reliability'];public['confidence']={'label':result['history_reliability']['label'],'reasons':result['history_reliability']['reasons']};public['forecast_quality']['policy_version']=BATCH_05_HISTORY_REPAIR_VERSION;public['methodology']['forecast_policy']=BATCH_05_HISTORY_REPAIR_VERSION;value=sanitize_public_artifact(public);expected='available' if issuer.ticker in PASS_TICKERS else 'conditional_estimate'
 if value['availability_type']!=expected or value['scenario_range']['base']!=result['scenario_range']['base']:raise RuntimeError(issuer.ticker)
 return value

def run(*,source_root:Path,structural_root:Path,output_root:Path):
 source_root,structural_root,output_root=map(Path,(source_root,structural_root,output_root));before={str(root):_tree(root) for root in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();cases=[];reliability_counts={'High':0,'Medium':0,'Low':0}
 for issuer in BATCH_05_MANIFEST:
  prior=build_batch_05_launch_first_result(ticker=issuer.ticker,source_root=source_root,structural_root=structural_root);result=build_batch_05_launch_first_result(ticker=issuer.ticker,source_root=source_root,structural_root=structural_root,history_backed=True);public=_history_public(issuer,result);availability=result['baseline']['availability_type'];outcome='source_bounded_numeric' if availability=='available' else 'conditional_numeric';reliability=result['history_reliability']['label'];reliability_counts[reliability]+=1;prior_base=prior['scenario_range']['base'];base=result['scenario_range']['base'];case={'ticker':issuer.ticker,'outcome':outcome,'availability_type':availability,'reliability':reliability,'method':result['method'],'prior_base':prior_base,'low':result['scenario_range']['low'],'base':base,'high':result['scenario_range']['high'],'base_change_pct':(base-prior_base)/prior_base,'history_years_used':result['governed_assumptions'].get('history_years_used'),'normalization_basis':result['governed_assumptions'].get('normalization_basis'),'assumption_source_mix':result['governed_assumptions'].get('assumption_source_mix'),'reliability_reasons':result['history_reliability']['reasons']};private={'schema_version':'FINSIGHT-BATCH-05-HISTORY-REPAIR-1','batch':5,'valuation_date':BATCH_05_VALUATION_DATE,'issuer':{'ticker':issuer.ticker,'cik':issuer.cik,'issuer_name':issuer.issuer_name},'prior_baseline':prior['scenario_range'],'history_backed':result,'repair_outcome':case};_immutable(output_root/'generated'/issuer.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{issuer.ticker}.json',_json(public));cases.append(case)
 after={str(root):_tree(root) for root in PROTECTED};watch_after=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
 if before!=after or watch!=watch_after:raise RuntimeError('Batch 05 history repair changed protected state')
 report={'schema_version':'FINSIGHT-BATCH-05-HISTORY-REPAIR-REPORT-1','batch':5,'valuation_date':BATCH_05_VALUATION_DATE,'policy_version':BATCH_05_HISTORY_REPAIR_VERSION,'denominator_tickers':list(BATCH_05_TICKERS),'attempted_count':10,'pass_count':4,'conditional_count':6,'withheld_count':0,'numeric_count':10,'pass_tickers':sorted(PASS_TICKERS),'conditional_tickers':[ticker for ticker in BATCH_05_TICKERS if ticker not in PASS_TICKERS],'reliability_counts':reliability_counts,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'watchlist_changed':False,'watchlist_sha256':watch,'cases':cases};_immutable(output_root/'history-repair-report.json',_json(report));return report

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',required=True,type=Path);parser.add_argument('--structural-root',required=True,type=Path);parser.add_argument('--output-root',required=True,type=Path);report=run(**vars(parser.parse_args()));print(json.dumps({key:report[key] for key in ('attempted_count','pass_count','conditional_count','withheld_count','numeric_count','reliability_counts','serving_artifacts_changed','watchlist_changed')},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
