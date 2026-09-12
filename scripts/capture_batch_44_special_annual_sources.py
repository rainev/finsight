#!/usr/bin/env python3
"""Capture PSX and APA FY2025 filings for extension-concept annual lineage."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/"backend") not in sys.path: sys.path.insert(0,str(ROOT/"backend"))
from capture_batch_02_structural_sources import _dependencies,_immutable_json

SOURCES={
    "PSX":{"cik":"0001534701","accession":"0001534701-26-000006","primary":"psx-20251231.htm","filed":"2026-02-20"},
    "APA":{"cik":"0001841666","accession":"0001841666-26-000015","primary":"apa-20251231.htm","filed":"2026-02-26"},
}


def run(*,output_root:Path,cache_root:Path,user_agent:str|None=None)->dict:
    output_root,cache_root=Path(output_root),Path(cache_root); sec,package_capture,parse=_dependencies(); client=sec(user_agent=user_agent,cache_dir=cache_root/".sec-cache"); receipts=[]
    for ticker,source in SOURCES.items():
        entry=package_capture(client,cik=source["cik"],accession=source["accession"],primary_document=source["primary"],form="10-K",output_dir=cache_root/f"filings/{ticker}",refresh=False,filed_date=source["filed"],report_date="2025-12-31"); parsed=parse(entry,accession=source["accession"],form="10-K",timeout_seconds=300); structural=parsed.as_dict() if hasattr(parsed,"as_dict") else parsed; package=json.loads((entry.parent/"package-manifest.json").read_text())
        receipt={"schema_version":"FINSIGHT-BATCH-44-SPECIAL-ANNUAL-SOURCE-1","valuation_date":"2026-08-14","ticker":ticker,"cik":source["cik"],"filing":{"accession":source["accession"],"filed":source["filed"],"form":"10-K","report_date":"2025-12-31","primary_document":source["primary"]},"package_manifest_sha256":hashlib.sha256((json.dumps(package,indent=2,sort_keys=True)+"\n").encode()).hexdigest(),"structural_filing_sha256":hashlib.sha256((json.dumps(structural,indent=2,sort_keys=True)+"\n").encode()).hexdigest()}
        target=output_root/ticker; _immutable_json(target/"package-manifest.json",package); _immutable_json(target/"structural-filing.json",structural); _immutable_json(target/"source-receipt.json",receipt); receipts.append(receipt)
    return {"schema_version":"FINSIGHT-BATCH-44-SPECIAL-ANNUAL-SOURCE-1","receipts":receipts}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output-root",type=Path,required=True); parser.add_argument("--cache-root",type=Path,required=True); parser.add_argument("--user-agent",default=os.environ.get("SEC_USER_AGENT")); print(json.dumps(run(**vars(parser.parse_args())),sort_keys=True))


if __name__=="__main__": main()
