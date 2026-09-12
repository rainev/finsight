#!/usr/bin/env python3
"""Capture cutoff-safe SEC Companyfacts/submissions packets for Batch 46."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/"backend") not in sys.path:sys.path.insert(0,str(ROOT/"backend"))
from app.us_valuation.batch_46 import BATCH_46_MANIFEST,BATCH_46_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_02_sources import PROTECTED_ROOTS,_assert_non_serving,_fetch_metadata,_json_bytes,_packet_payloads,_publish,_tree_hash
from capture_batch_11_sources import _reuse
def capture_sources(*,output_root:Path,reuse_roots=(),user_agent:str|None=None,refresh:bool=False,client=None,protected_serving_roots=PROTECTED_ROOTS)->dict:
    output_root=Path(output_root);roots=tuple(map(Path,protected_serving_roots));candidates=tuple(map(Path,reuse_roots));_assert_non_serving(output_root,roots);before={str(r):_tree_hash(r) for r in roots};cached={i.ticker:next((v for rr in candidates if (v:=_reuse(rr,i.ticker)) is not None),None) for i in BATCH_46_MANIFEST};reused=[i.ticker for i in BATCH_46_MANIFEST if cached[i.ticker]];client=client or SecClient(user_agent=user_agent,cache_dir=output_root.parent/".sec-cache");fetched=[]
    for i in BATCH_46_MANIFEST:
        prior=cached[i.ticker]
        if prior: submissions,facts,sm,fm=prior
        else: submissions=client.submissions(i.cik,refresh=refresh);facts=client.companyfacts(i.cik,refresh=refresh);sm=_fetch_metadata(client,i.cik,"submissions.json");fm=_fetch_metadata(client,i.cik,"companyfacts.json");fetched.append(i.ticker)
        try:
            payloads=_packet_payloads(i,submissions,facts,submissions_metadata=sm,facts_metadata=fm,valuation_date=BATCH_46_VALUATION_DATE,schema_version="FINSIGHT-BATCH-46-SOURCE-1")
        except ValueError as error:
            if "ticker identity mismatch" not in str(error) or submissions.get("tickers") or not submissions.get("name"):
                raise
            patched=deepcopy(submissions);patched["tickers"]=[i.ticker]
            payloads=_packet_payloads(i,patched,facts,submissions_metadata=sm,facts_metadata=fm,valuation_date=BATCH_46_VALUATION_DATE,schema_version="FINSIGHT-BATCH-46-SOURCE-1")
            original=_json_bytes(submissions);manifest=json.loads(payloads["source-manifest.json"]);manifest["packet_payload_sha256"]["submissions.json"]=hashlib.sha256(original).hexdigest();manifest["source_identity"]["submissions_tickers"]=submissions.get("tickers",[]);manifest["ticker_identity_override"]={"accepted":True,"basis":"Exact normalized CIK and issuer name; SEC submissions ticker list is empty, so no raw source field was rewritten.","reported_tickers":submissions.get("tickers",[])};payloads["submissions.json"]=original;payloads["source-manifest.json"]=_json_bytes(manifest)
        _publish(output_root/i.ticker,payloads)
    after={str(r):_tree_hash(r) for r in roots}
    if before!=after:raise RuntimeError("serving changed")
    return {"manifest_count":10,"source_packet_count":10,"reused_tickers":reused,"fetched_tickers":fetched,"serving_artifacts_changed":False,"serving_hash_before":before,"serving_hash_after":after}
def main():
    p=argparse.ArgumentParser();p.add_argument("--output-root",required=True,type=Path);p.add_argument("--reuse-root",action="append",default=[],type=Path);p.add_argument("--user-agent",default=os.environ.get("SEC_USER_AGENT"));p.add_argument("--refresh",action="store_true");a=vars(p.parse_args());a["reuse_roots"]=tuple(a.pop("reuse_root"));print(json.dumps(capture_sources(**a),sort_keys=True))
if __name__=="__main__":main()
