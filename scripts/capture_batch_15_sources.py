#!/usr/bin/env python3
"""Capture immutable SEC packets for frozen Batch 15, reusing cached packets first."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.batch_15 import BATCH_15_MANIFEST,BATCH_15_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import PROTECTED_ROOTS,_assert_non_serving,_fetch_metadata,_packet_payloads,_publish,_tree_hash
from capture_batch_11_sources import _reuse
def capture_sources(*,output_root:Path,reuse_root:Path|None=None,user_agent:str|None=None,refresh:bool=False,client:Any=None,protected_serving_roots=PROTECTED_ROOTS):
 output_root=Path(output_root);roots=tuple(Path(r) for r in protected_serving_roots);_assert_non_serving(output_root,roots);before={str(r):_tree_hash(r) for r in roots};cached={i.ticker:_reuse(reuse_root,i.ticker) for i in BATCH_15_MANIFEST};reused=[i.ticker for i in BATCH_15_MANIFEST if cached[i.ticker]];missing=[i.ticker for i in BATCH_15_MANIFEST if not cached[i.ticker]];client=client or SecClient(user_agent=user_agent,cache_dir=output_root.parent/'.sec-cache');packets={};fetched=[]
 for issuer in BATCH_15_MANIFEST:
  packet=cached[issuer.ticker]
  if packet:sub,facts,sub_meta,fact_meta=packet
  else:sub=client.submissions(issuer.cik,refresh=refresh);facts=client.companyfacts(issuer.cik,refresh=refresh);sub_meta=_fetch_metadata(client,issuer.cik,'submissions.json');fact_meta=_fetch_metadata(client,issuer.cik,'companyfacts.json');fetched.append(issuer.ticker)
  packets[issuer.ticker]=_packet_payloads(issuer,sub,facts,submissions_metadata=sub_meta,facts_metadata=fact_meta,valuation_date=BATCH_15_VALUATION_DATE,schema_version='FINSIGHT-BATCH-15-SOURCE-1')
 for ticker,payload in packets.items():_publish(output_root/ticker,payload)
 after={str(r):_tree_hash(r) for r in roots}
 if before!=after:raise RuntimeError('serving changed')
 return {'manifest_count':10,'source_packet_count':10,'cache_preflight_reused_tickers':reused,'cache_preflight_missing_tickers':missing,'reused_tickers':reused,'fetched_tickers':fetched,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',required=True,type=Path);p.add_argument('--reuse-root',type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));p.add_argument('--refresh',action='store_true');print(json.dumps(capture_sources(**vars(p.parse_args())),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
