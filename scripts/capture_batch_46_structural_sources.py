#!/usr/bin/env python3
"""Capture and parse controlling SEC XBRL filings for Batch 46."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/"backend") not in sys.path:sys.path.insert(0,str(ROOT/"backend"))
from app.us_valuation.batch_46 import BATCH_46_MANIFEST,BATCH_46_VALUATION_DATE
from app.us_valuation.sec_client import normalize_cik
from capture_batch_02_structural_sources import ELIGIBLE_FORMS,PROTECTED_ROOTS,_dependencies,_immutable_json,_json_bytes,_sha256,_tree_hash,_validate_paths
from capture_batch_12_structural_sources import _reuse_any_structural
def control(root,issuer):
    path=Path(root)/issuer.ticker;packet=json.loads((path/"source-manifest.json").read_text());rows=[r for r in packet["eligible_filings"] if r["form"] in ELIGIBLE_FORMS];filing=dict(max(rows,key=lambda r:(r["filed"],r["accession"])));recent=json.loads((path/"submissions.json").read_text())["filings"]["recent"];idx=recent["accessionNumber"].index(filing["accession"]);filing["report_date"]=recent["reportDate"][idx];return filing,packet
def capture_structural_sources(*,source_root:Path,output_root:Path,cache_root:Path,user_agent:str|None=None,refresh:bool=False,client=None,package_capture=None,parse=None,reuse_roots=(),protected_serving_roots=PROTECTED_ROOTS):
    source_root,output_root,cache_root=map(Path,(source_root,output_root,cache_root));_validate_paths(source_root,output_root,cache_root,protected_serving_roots);before={str(r):_tree_hash(r) for r in protected_serving_roots};controls={i.ticker:control(source_root,i) for i in BATCH_46_MANIFEST};cached={i.ticker:_reuse_any_structural(tuple(map(Path,reuse_roots)),i,controls[i.ticker][0]) for i in BATCH_46_MANIFEST}
    if any(v is None for v in cached.values()) and (client is None or package_capture is None or parse is None):sec,pack,parser=_dependencies();client=client or sec(user_agent=user_agent,cache_dir=cache_root/".sec-cache");package_capture=package_capture or pack;parse=parse or parser
    cases=[];reused=[];captured=[]
    for i in BATCH_46_MANIFEST:
        filing,packet=controls[i.ticker];prior=cached[i.ticker]
        if prior:value,package,source=prior;reused.append(i.ticker)
        else:entry=package_capture(client,cik=i.cik,accession=filing["accession"],primary_document=filing["primary_document"],form=filing["form"],output_dir=cache_root/"filings"/i.ticker,refresh=refresh,filed_date=filing["filed"],report_date=filing["report_date"]);parsed=parse(entry,accession=filing["accession"],form=filing["form"],timeout_seconds=300);value=parsed.as_dict() if hasattr(parsed,"as_dict") else parsed;package=json.loads((entry.parent/"package-manifest.json").read_text());source=None;captured.append(i.ticker)
        if normalize_cik(package.get("cik",""))!=i.cik:raise ValueError(i.ticker)
        receipt={"schema_version":"FINSIGHT-BATCH-46-STRUCTURAL-SOURCE-1","valuation_date":BATCH_46_VALUATION_DATE,"ticker":i.ticker,"cik":i.cik,"filing":filing,"source_packet_manifest_sha256":_sha256(_json_bytes(packet)),"package_manifest_sha256":_sha256(_json_bytes(package)),"structural_filing_sha256":_sha256(_json_bytes(value)),"capture_mode":"reused" if prior else "captured","reuse_source":source};target=output_root/i.ticker;_immutable_json(target/"package-manifest.json",package);_immutable_json(target/"structural-filing.json",value);_immutable_json(target/"source-receipt.json",receipt);cases.append({"ticker":i.ticker,"accession":filing["accession"],"filed":filing["filed"],"report_date":filing["report_date"],"form":filing["form"],"result":"parsed","capture_mode":"reused" if prior else "captured"})
    after={str(r):_tree_hash(r) for r in protected_serving_roots}
    if before!=after:raise RuntimeError("serving changed")
    summary={"schema_version":"FINSIGHT-BATCH-46-STRUCTURAL-SOURCE-1","valuation_date":BATCH_46_VALUATION_DATE,"attempted":10,"parsed":10,"failed":0,"reused_tickers":reused,"captured_tickers":captured,"cases":cases,"serving_hash_before":before,"serving_hash_after":after,"serving_artifacts_changed":False};_immutable_json(output_root/"summary.json",summary);return summary
def main():
    p=argparse.ArgumentParser();p.add_argument("--source-root",required=True,type=Path);p.add_argument("--output-root",required=True,type=Path);p.add_argument("--cache-root",required=True,type=Path);p.add_argument("--reuse-root",action="append",default=[],type=Path);p.add_argument("--user-agent",default=os.environ.get("SEC_USER_AGENT"));a=vars(p.parse_args());a["reuse_roots"]=tuple(a.pop("reuse_root"));print(json.dumps(capture_structural_sources(**a),sort_keys=True))
if __name__=="__main__":main()
