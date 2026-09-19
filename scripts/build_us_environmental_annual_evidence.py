#!/usr/bin/env python3
"""Compile private deterministic annual environmental evidence from captured sources."""
import argparse
import json
from pathlib import Path
from capture_batch_02_structural_sources import _immutable_json
from app.us_valuation.refresh_environmental_annual_evidence import extract_annual_environmental_evidence

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--ticker',required=True);p.add_argument('--cutoff',required=True)
    p.add_argument('--package-manifest',action='append',required=True)
    p.add_argument('--structural',action='append',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if len(a.package_manifest)!=len(a.structural):raise ValueError('one structural per manifest required')
    sources=[{'package_manifest_path':m,'structural_path':s} for m,s in zip(a.package_manifest,a.structural)]
    receipt=extract_annual_environmental_evidence(a.ticker,sources,source_root=a.source_root,cutoff=a.cutoff)
    _immutable_json(a.output,receipt)
    print(json.dumps({'receipt_sha256':receipt['receipt_sha256'],'output':str(a.output),'status':receipt['status']}))
