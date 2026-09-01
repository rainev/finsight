#!/usr/bin/env python3
"""Capture the exact URI FY2025 10-K needed for the Batch 23 repair attempt."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend')) if str(ROOT/'backend') not in sys.path else None
from app.us_valuation.batch_23 import BATCH_23_VALUATION_DATE
from app.us_valuation.sec_client import normalize_cik
from capture_batch_02_structural_sources import PROTECTED_ROOTS,_dependencies,_immutable_json,_json_bytes,_sha256,_tree_hash,_validate_paths
URI_CIK='0001067701';URI_ACCESSION='0001067701-26-000007'
def capture(*,source_root:Path,output_root:Path,cache_root:Path,user_agent=None,refresh=False,client=None,package_capture=None,parse=None,protected_serving_roots=PROTECTED_ROOTS):
 source_root,output_root,cache_root=map(Path,(source_root,output_root,cache_root));_validate_paths(source_root,output_root,cache_root,protected_serving_roots);before={str(r):_tree_hash(r) for r in protected_serving_roots};p=source_root/'URI';m=json.loads((p/'source-manifest.json').read_text());eligible=[dict(x) for x in m['eligible_filings'] if x['accession']==URI_ACCESSION]
 if len(eligible)!=1:raise ValueError('URI repair 10-K absent from cutoff manifest')
 f=eligible[0];sub=json.loads((p/'submissions.json').read_text())['filings']['recent'];i=sub['accessionNumber'].index(URI_ACCESSION);f['report_date']=sub['reportDate'][i]
 if f['form']!='10-K' or f['filed']>'2026-08-14' or f['report_date']!='2025-12-31':raise ValueError('URI repair filing identity invalid')
 if client is None or package_capture is None or parse is None:sec,pc,pa=_dependencies();client=client or sec(user_agent=user_agent,cache_dir=cache_root/'.sec-cache');package_capture=package_capture or pc;parse=parse or pa
 e=package_capture(client,cik=URI_CIK,accession=f['accession'],primary_document=f['primary_document'],form=f['form'],output_dir=cache_root/'filings'/'URI',refresh=refresh,filed_date=f['filed'],report_date=f['report_date']);z=parse(e,accession=f['accession'],form=f['form']);value=z.as_dict() if hasattr(z,'as_dict') else z;package=json.loads((e.parent/'package-manifest.json').read_text())
 if normalize_cik(package.get('cik',''))!=URI_CIK:raise ValueError('URI repair package CIK mismatch')
 receipt={'schema_version':'FINSIGHT-BATCH-23-REPAIR-SOURCE-1','valuation_date':BATCH_23_VALUATION_DATE,'ticker':'URI','cik':URI_CIK,'filing':f,'source_packet_manifest_sha256':_sha256(_json_bytes(m)),'package_manifest_sha256':_sha256(_json_bytes(package)),'structural_filing_sha256':_sha256(_json_bytes(value)),'purpose':'exact_fy2025_fleet_and_other_capex'};target=output_root/'URI';_immutable_json(target/'package-manifest.json',package);_immutable_json(target/'structural-filing.json',value);_immutable_json(target/'source-receipt.json',receipt);after={str(r):_tree_hash(r) for r in protected_serving_roots}
 if before!=after:raise RuntimeError('serving changed')
 return {'ticker':'URI','accession':f['accession'],'form':f['form'],'filed':f['filed'],'report_date':f['report_date'],'parsed_fact_count':len(value.get('facts',[])),'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--cache-root',type=Path,required=True);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));print(json.dumps(capture(**vars(p.parse_args())),sort_keys=True))
if __name__=='__main__':main()
