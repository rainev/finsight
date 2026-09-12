#!/usr/bin/env python3
"""Capture LNT and WEC FY2025 filings for complete utility-capex lineage."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/"backend") not in sys.path:sys.path.insert(0,str(ROOT/"backend"))
from capture_batch_02_structural_sources import _dependencies,_immutable_json
SOURCES={"LNT":{"cik":"0000352541","accession":"0000352541-26-000007","primary":"lnt-20251231.htm","filed":"2026-02-20"},"WEC":{"cik":"0000783325","accession":"0000783325-26-000018","primary":"wec-20251231.htm","filed":"2026-02-20"}}
def run(*,output_root:Path,cache_root:Path,user_agent:str|None=None)->dict:
    output_root,cache_root=Path(output_root),Path(cache_root);sec,pack,parse=_dependencies();client=sec(user_agent=user_agent,cache_dir=cache_root/".sec-cache");receipts=[]
    for ticker,s in SOURCES.items():
        entry=pack(client,cik=s["cik"],accession=s["accession"],primary_document=s["primary"],form="10-K",output_dir=cache_root/f"filings/{ticker}",refresh=False,filed_date=s["filed"],report_date="2025-12-31");parsed=parse(entry,accession=s["accession"],form="10-K",timeout_seconds=300);structural=parsed.as_dict() if hasattr(parsed,"as_dict") else parsed;package=json.loads((entry.parent/"package-manifest.json").read_text());receipt={"schema_version":"FINSIGHT-BATCH-45-SPECIAL-ANNUAL-SOURCE-1","valuation_date":"2026-08-14","ticker":ticker,"cik":s["cik"],"filing":{"accession":s["accession"],"filed":s["filed"],"form":"10-K","report_date":"2025-12-31","primary_document":s["primary"]},"package_manifest_sha256":hashlib.sha256((json.dumps(package,indent=2,sort_keys=True)+"\n").encode()).hexdigest(),"structural_filing_sha256":hashlib.sha256((json.dumps(structural,indent=2,sort_keys=True)+"\n").encode()).hexdigest()};target=output_root/ticker;_immutable_json(target/"package-manifest.json",package);_immutable_json(target/"structural-filing.json",structural);_immutable_json(target/"source-receipt.json",receipt);receipts.append(receipt)
    return {"schema_version":"FINSIGHT-BATCH-45-SPECIAL-ANNUAL-SOURCE-1","receipts":receipts}
def main():
    p=argparse.ArgumentParser();p.add_argument("--output-root",type=Path,required=True);p.add_argument("--cache-root",type=Path,required=True);p.add_argument("--user-agent",default=os.environ.get("SEC_USER_AGENT"));print(json.dumps(run(**vars(p.parse_args())),sort_keys=True))
if __name__=="__main__":main()
