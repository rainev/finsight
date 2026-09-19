#!/usr/bin/env python3
"""Build private deterministic HON separation event evidence."""
import argparse,json
from pathlib import Path
from capture_batch_02_structural_sources import _immutable_json
from app.us_valuation.refresh_separation_event_evidence import extract_separation_event_evidence

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ticker',required=True);p.add_argument('--capture-report',required=True)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--cutoff',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=extract_separation_event_evidence(a.ticker,a.capture_report,source_root=a.source_root,cutoff=a.cutoff)
    _immutable_json(a.output,value);print(json.dumps({'output':str(a.output),'receipt_sha256':value['receipt_sha256'],'status':value['status']}))
