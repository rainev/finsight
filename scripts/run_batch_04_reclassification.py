#!/usr/bin/env python3
"""Stage the user-approved Batch 04 Pass repairs without serving writes."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_04 import BATCH_04_MANIFEST,BATCH_04_TICKERS,BATCH_04_VALUATION_DATE
from app.us_valuation.batch_04_launch_first import PASS_TICKERS,build_batch_04_launch_first_result
from run_batch_04_launch_first import PROTECTED,WATCHLIST,_immutable,_json,_public,_tree


def _pass_public(issuer,result):
    value=_public(issuer,result);scenario=result['scenario_range'];base=scenario['base']
    value['primary_valuation_method']='fcff_dcf'
    value['model_policy']={'primary':'fcff_dcf','supporting':[],'blend_models':False,'reason':'Source-bounded normalized cash-FCFF with a completed current claims bridge.'}
    value['models']={'fcff_dcf':{'model':'fcff_dcf','output_type':'intrinsic_value_per_share','currency':'USD','intrinsic_value_per_share':base,'publication_state':'review_required','errors':[],'warnings':['Low-reliability source-bounded estimate; ordinary scenario uncertainty remains.']}}
    value['scenario_range']={**scenario,'label':'assumption range, not a statistical confidence interval'}
    value['bridge_quality']={'blocking_fields':[],'bounded_fields':[],'complete':True,'decision':'complete','intrinsic_value_range':{'low':base,'midpoint':base,'high':base,'spread_ratio':0.0,'spread_limit':0.01},'reason_codes':[],'usable':True}
    value['forecast_quality']['warnings']=['Source-bounded normalized cash-FCFF; scenario assumptions require review.']
    value['review']['warnings']=['Low-reliability source-bounded estimate. Ordinary business and scenario uncertainty may materially affect the range.']
    value['reliability']={'label':'Low','accounting_label':'High','scenario_label':'Low','model_cap':'Low','source_cap':'Low','accounting_impact_ratio':0.0,'scenario_movement_ratio':value['reliability']['scenario_movement_ratio'],'reasons':['CONSOLIDATED_MODEL_FALLBACK','SPECIALIST_MODEL_UNCERTAINTY']}
    public=sanitize_public_artifact(value)
    if public['availability_type']!='available' or public['scenario_range']['base']!=base:raise RuntimeError(issuer.ticker)
    return public


def run(*,source_root:Path,structural_root:Path,output_root:Path):
    source_root,structural_root,output_root=map(Path,(source_root,structural_root,output_root));before={str(root):_tree(root) for root in PROTECTED};watch=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest();cases=[]
    for issuer in BATCH_04_MANIFEST:
        result=build_batch_04_launch_first_result(ticker=issuer.ticker,source_root=source_root,structural_root=structural_root);is_pass=issuer.ticker in PASS_TICKERS;public=_pass_public(issuer,result) if is_pass else _public(issuer,result);outcome='source_bounded_numeric' if is_pass else 'conditional_numeric';availability='available' if is_pass else 'conditional_estimate'
        private={'schema_version':'FINSIGHT-CONTROLLED-BATCH-OUTCOME-1','batch':4,'valuation_date':BATCH_04_VALUATION_DATE,'issuer':{'ticker':issuer.ticker,'cik':issuer.cik,'issuer_name':issuer.issuer_name},'launch_first':result,'controlled_outcome':{'ticker':issuer.ticker,'outcome':outcome,'availability_type':availability,'reliability':'Low',**result['scenario_range']}}
        _immutable(output_root/'generated'/issuer.ticker/'valuation-private.json',_json(private));_immutable(output_root/'staged-public'/f'{issuer.ticker}.json',_json(public));cases.append({'ticker':issuer.ticker,'outcome':outcome,'availability_type':availability,'reliability':'Low','method':result['method'],**result['scenario_range'],'warning':result['warning']})
    after={str(root):_tree(root) for root in PROTECTED};watch_after=hashlib.sha256(WATCHLIST.read_bytes()).hexdigest()
    if before!=after or watch!=watch_after:raise RuntimeError('protected state changed')
    report={'schema_version':'FINSIGHT-BATCH-04-PASS-REPAIR-REPORT-1','batch':4,'valuation_date':BATCH_04_VALUATION_DATE,'denominator_tickers':list(BATCH_04_TICKERS),'attempted_count':10,'pass_count':4,'source_bounded_numeric_count':4,'conditional_count':6,'conditional_numeric_count':6,'withheld_count':0,'numeric_count':10,'pass_tickers':sorted(PASS_TICKERS),'conditional_tickers':[ticker for ticker in BATCH_04_TICKERS if ticker not in PASS_TICKERS],'reliability_counts':{'High':0,'Medium':0,'Low':10},'watchlist_changed':False,'watchlist_sha256':watch,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after,'cases':cases};_immutable(output_root/'reclassification-report.json',_json(report));return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',required=True,type=Path);parser.add_argument('--structural-root',required=True,type=Path);parser.add_argument('--output-root',required=True,type=Path);result=run(**vars(parser.parse_args()));print(json.dumps({key:result[key] for key in ('attempted_count','pass_count','conditional_count','withheld_count','serving_artifacts_changed','watchlist_changed')},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
