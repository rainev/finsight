#!/usr/bin/env python3
"""Capture cutoff-safe SEC Companyfacts/submissions packets for Batch 38."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/'backend') not in sys.path:sys.path.insert(0,str(ROOT/'backend'))
from app.us_valuation.batch_38 import BATCH_38_MANIFEST,BATCH_38_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import PROTECTED_ROOTS,_assert_non_serving,_fetch_metadata,_packet_payloads,_publish,_tree_hash
from capture_batch_11_sources import _reuse
def capture_sources(*,output_root:Path,reuse_root:Path|None=None,user_agent:str|None=None,refresh:bool=False,client=None,protected_serving_roots=PROTECTED_ROOTS)->dict:
 output_root=Path(output_root);roots=tuple(map(Path,protected_serving_roots));_assert_non_serving(output_root,roots);before={str(r):_tree_hash(r) for r in roots};cached={i.ticker:_reuse(reuse_root,i.ticker) for i in BATCH_38_MANIFEST};reused=[i.ticker for i in BATCH_38_MANIFEST if cached[i.ticker]];client=client or SecClient(user_agent=user_agent,cache_dir=output_root.parent/'.sec-cache');fetched=[]
 for i in BATCH_38_MANIFEST:
  prior=cached[i.ticker]
  if prior:sub,facts,sub_meta,facts_meta=prior
  else:sub=client.submissions(i.cik,refresh=refresh);facts=client.companyfacts(i.cik,refresh=refresh);sub_meta=_fetch_metadata(client,i.cik,'submissions.json');facts_meta=_fetch_metadata(client,i.cik,'companyfacts.json');fetched.append(i.ticker)
  _publish(output_root/i.ticker,_packet_payloads(i,sub,facts,submissions_metadata=sub_meta,facts_metadata=facts_meta,valuation_date=BATCH_38_VALUATION_DATE,schema_version='FINSIGHT-BATCH-38-SOURCE-1'))
 after={str(r):_tree_hash(r) for r in roots}
 if before!=after:raise RuntimeError('serving changed')
 return {'manifest_count':10,'source_packet_count':10,'reused_tickers':reused,'fetched_tickers':fetched,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output-root',required=True,type=Path);p.add_argument('--reuse-root',type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));p.add_argument('--refresh',action='store_true');print(json.dumps(capture_sources(**vars(p.parse_args())),sort_keys=True))
if __name__=='__main__':main()
