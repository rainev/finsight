#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.us_valuation.catalog import canonical_json_bytes
from app.us_valuation.refresh_job import atomic
from app.us_valuation.refresh_public_contract_evidence import extract_public_contract_evidence
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT/'output');p.add_argument('--capture-report',type=Path,required=True);p.add_argument('--runtime-root',type=Path,default=ROOT/'output/us-refresh-runtime');a=p.parse_args()
 r=extract_public_contract_evidence(a.capture_report,source_root=a.source_root);path=a.runtime_root/'public-contract-evidence/MCK.json';atomic(path,canonical_json_bytes(r),immutable=False);print(json.dumps({'path':str(path),'receipt_sha256':r['receipt_sha256'],'status':'source_terms_verified_economic_contract_gap'}))
