#!/usr/bin/env python3
"""Capture immutable SEC packets for frozen Batch 05."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.batch_05 import BATCH_05_MANIFEST,BATCH_05_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import PROTECTED_ROOTS,_assert_non_serving,_fetch_metadata,_packet_payloads,_publish,_tree_hash
def _reuse(root,t):
 p=Path(root)/t if root else None;names=('submissions.json','companyfacts.json','submissions.meta.json','companyfacts.meta.json')
 return tuple(json.loads((p/n).read_text()) for n in names) if p and all((p/n).is_file() for n in names) else None
def capture_sources(*,output_root:Path,reuse_root:Path|None=None,user_agent:str|None=None,refresh:bool=False,client:Any=None,protected_serving_roots=PROTECTED_ROOTS):
 output_root=Path(output_root);roots=tuple(Path(r) for r in protected_serving_roots);_assert_non_serving(output_root,roots);before={str(r):_tree_hash(r) for r in roots};client=client or SecClient(user_agent=user_agent,cache_dir=output_root.parent/'.sec-cache');packets={};reused=[];fetched=[]
 for issuer in BATCH_05_MANIFEST:
  cached=_reuse(reuse_root,issuer.ticker)
  if cached:sub,facts,sm,fm=cached;reused.append(issuer.ticker)
  else:sub=client.submissions(issuer.cik,refresh=refresh);facts=client.companyfacts(issuer.cik,refresh=refresh);sm=_fetch_metadata(client,issuer.cik,'submissions.json');fm=_fetch_metadata(client,issuer.cik,'companyfacts.json');fetched.append(issuer.ticker)
  packets[issuer.ticker]=_packet_payloads(issuer,sub,facts,submissions_metadata=sm,facts_metadata=fm,valuation_date=BATCH_05_VALUATION_DATE,schema_version='FINSIGHT-BATCH-05-SOURCE-1')
 for t,p in packets.items():_publish(output_root/t,p)
 after={str(r):_tree_hash(r) for r in roots}
 if before!=after:raise RuntimeError('serving changed')
 return {'manifest_count':10,'source_packet_count':10,'reused_tickers':reused,'fetched_tickers':fetched,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',required=True,type=Path);p.add_argument('--reuse-root',type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));p.add_argument('--refresh',action='store_true');print(json.dumps(capture_sources(**vars(p.parse_args())),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())

