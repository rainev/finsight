#!/usr/bin/env python3
"""Capture immutable SEC packets for frozen Batch 09."""
from __future__ import annotations
import argparse,json,os,sys
from dataclasses import replace
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.batch_09 import BATCH_09_MANIFEST,BATCH_09_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import PROTECTED_ROOTS,_assert_non_serving,_fetch_metadata,_json_bytes,_packet_payloads,_publish,_tree_hash
def _reuse(root,ticker):
 path=Path(root)/ticker if root else None;names=('submissions.json','companyfacts.json','submissions.meta.json','companyfacts.meta.json')
 return tuple(json.loads((path/name).read_text()) for name in names) if path and all((path/name).is_file() for name in names) else None
def capture_sources(*,output_root:Path,reuse_root:Path|None=None,user_agent:str|None=None,refresh:bool=False,client:Any=None,protected_serving_roots=PROTECTED_ROOTS):
 output_root=Path(output_root);roots=tuple(Path(root) for root in protected_serving_roots);_assert_non_serving(output_root,roots);before={str(root):_tree_hash(root) for root in roots};client=client or SecClient(user_agent=user_agent,cache_dir=output_root.parent/'.sec-cache');packets={};reused=[];fetched=[]
 for issuer in BATCH_09_MANIFEST:
  cached=_reuse(reuse_root,issuer.ticker)
  if cached:sub,facts,sub_meta,fact_meta=cached;reused.append(issuer.ticker)
  else:sub=client.submissions(issuer.cik,refresh=refresh);facts=client.companyfacts(issuer.cik,refresh=refresh);sub_meta=_fetch_metadata(client,issuer.cik,'submissions.json');fact_meta=_fetch_metadata(client,issuer.cik,'companyfacts.json');fetched.append(issuer.ticker)
  sec_issuer=replace(issuer,ticker='BF-B') if issuer.ticker=='BF.B' else issuer
  payload=_packet_payloads(sec_issuer,sub,facts,submissions_metadata=sub_meta,facts_metadata=fact_meta,valuation_date=BATCH_09_VALUATION_DATE,schema_version='FINSIGHT-BATCH-09-SOURCE-1')
  if issuer.ticker=='BF.B':
   manifest=json.loads(payload['source-manifest.json']);manifest['issuer']['ticker']='BF.B';manifest['ticker_alias_evidence']={'frozen_ticker':'BF.B','sec_ticker':'BF-B','cik':issuer.cik,'basis':'SEC submissions uses dash notation for the same Brown-Forman Class B security; no issuer or share class substitution.'};payload['source-manifest.json']=_json_bytes(manifest)
  packets[issuer.ticker]=payload
 for ticker,payload in packets.items():_publish(output_root/ticker,payload)
 after={str(root):_tree_hash(root) for root in roots}
 if before!=after:raise RuntimeError('serving changed')
 return {'manifest_count':10,'source_packet_count':10,'reused_tickers':reused,'fetched_tickers':fetched,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',required=True,type=Path);p.add_argument('--reuse-root',type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));p.add_argument('--refresh',action='store_true');print(json.dumps(capture_sources(**vars(p.parse_args())),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
