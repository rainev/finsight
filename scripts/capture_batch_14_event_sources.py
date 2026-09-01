#!/usr/bin/env python3
"""Capture the cutoff-eligible non-10-K/Q event filing needed by Batch 14."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.sec_client import SecClient,sec_archive_url
from capture_batch_02_sources import PROTECTED_ROOTS,_assert_non_serving,_tree_hash
from capture_batch_02_structural_sources import _immutable_json
SOURCES=({"ticker":"TECH","cik":"0000842023","accession":"0001140361-26-032037","form":"PREM14A","filed":"2026-08-10","report_date":"2026-08-10","primary_document":"ny20078105x1_prem14a.htm","role":"pending_merger_terms"},)
def run(*,output_root:Path,user_agent:str|None=None,refresh:bool=False):
 output_root=Path(output_root);roots=tuple(Path(r) for r in PROTECTED_ROOTS);_assert_non_serving(output_root,roots);before={str(r):_tree_hash(r) for r in roots};client=SecClient(user_agent=user_agent,cache_dir=output_root.parent/'.sec-cache');cases=[]
 for source in SOURCES:
  raw=client.filing_attachment(source['cik'],source['accession'],source['primary_document'],refresh=refresh,max_bytes=24*1024*1024);digest=hashlib.sha256(raw).hexdigest();target=output_root/source['ticker'];target.mkdir(parents=True,exist_ok=True);document=target/source['primary_document']
  if document.exists() and document.read_bytes()!=raw:raise FileExistsError(f"immutable event document differs: {document}")
  if not document.exists():document.write_bytes(raw)
  receipt={"schema_version":"FINSIGHT-BATCH-14-EVENT-SOURCE-1","valuation_date":"2026-08-14",**source,"url":sec_archive_url(source['cik'],source['accession'],source['primary_document']),"document_sha256":digest,"document_bytes":len(raw),"reported_terms":{"agreement_date":"2026-06-25","cash_consideration_per_share":73.0,"status":"pending_shareholder_and_other_closing_conditions"}};_immutable_json(target/'source-receipt.json',receipt);cases.append({"ticker":source['ticker'],"accession":source['accession'],"filed":source['filed'],"form":source['form'],"document_sha256":digest})
 after={str(r):_tree_hash(r) for r in roots}
 if before!=after:raise RuntimeError('serving changed')
 summary={"attempted":len(SOURCES),"captured":len(cases),"failed":0,"cases":cases,"serving_hash_before":before,"serving_hash_after":after,"serving_artifacts_changed":False};_immutable_json(output_root/'summary.json',summary);return summary
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',required=True,type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));p.add_argument('--refresh',action='store_true');print(json.dumps(run(**vars(p.parse_args())),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
