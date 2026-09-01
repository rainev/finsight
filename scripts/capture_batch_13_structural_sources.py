#!/usr/bin/env python3
"""Capture parsed controlling filings for Batch 13 with cache-first reuse."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from typing import Any,Callable
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.batch_13 import BATCH_13_MANIFEST,BATCH_13_VALUATION_DATE
from app.us_valuation.sec_client import normalize_cik
from capture_batch_02_structural_sources import ELIGIBLE_FORMS,PROTECTED_ROOTS,_dependencies,_immutable_json,_json_bytes,_sha256,_tree_hash,_validate_paths
from capture_batch_12_structural_sources import _reuse_any_structural
def _control(root,issuer):
 packet=Path(root)/issuer.ticker;manifest=json.loads((packet/'source-manifest.json').read_text())
 if manifest.get('schema_version')!='FINSIGHT-BATCH-13-SOURCE-1' or manifest.get('issuer')!={'ticker':issuer.ticker,'cik':issuer.cik,'issuer_name':issuer.issuer_name}:raise ValueError(issuer.ticker)
 rows=[r for r in manifest['eligible_filings'] if r['form'] in ELIGIBLE_FORMS];filing=dict(max(rows,key=lambda r:(r['filed'],r['accession'])));sub=json.loads((packet/'submissions.json').read_text());recent=sub['filings']['recent'];indexes=[i for i,a in enumerate(recent['accessionNumber']) if a==filing['accession']]
 if len(indexes)!=1:raise ValueError(f'{issuer.ticker}: controlling report date unresolved')
 i=indexes[0]
 if recent['filingDate'][i]!=filing['filed'] or recent['form'][i]!=filing['form'] or recent['primaryDocument'][i]!=filing['primary_document']:raise ValueError(f'{issuer.ticker}: controlling metadata mismatch')
 filing['report_date']=recent['reportDate'][i];return filing,manifest
def capture_structural_sources(*,source_root:Path,output_root:Path,cache_root:Path,user_agent:str|None=None,refresh:bool=False,client:Any=None,package_capture:Callable[...,Path]|None=None,parse:Callable[...,Any]|None=None,reuse_roots:tuple[Path,...]=(),protected_serving_roots=PROTECTED_ROOTS):
 source_root,output_root,cache_root=map(Path,(source_root,output_root,cache_root));_validate_paths(source_root,output_root,cache_root,protected_serving_roots);before={str(r):_tree_hash(r) for r in protected_serving_roots};reuse_roots=tuple(Path(r) for r in reuse_roots);controls={i.ticker:_control(source_root,i) for i in BATCH_13_MANIFEST};cached={i.ticker:_reuse_any_structural(reuse_roots,i,controls[i.ticker][0]) for i in BATCH_13_MANIFEST}
 if any(v is None for v in cached.values()) and (client is None or package_capture is None or parse is None):sec,capture_default,parse_default=_dependencies();client=client or sec(user_agent=user_agent,cache_dir=cache_root/'.sec-cache');package_capture=package_capture or capture_default;parse=parse or parse_default
 cases=[];reused=[];captured=[]
 for issuer in BATCH_13_MANIFEST:
  filing,source_manifest=controls[issuer.ticker];prior=cached[issuer.ticker]
  if prior:value,package,reuse_source=prior;reused.append(issuer.ticker)
  else:
   entry=package_capture(client,cik=issuer.cik,accession=filing['accession'],primary_document=filing['primary_document'],form=filing['form'],output_dir=cache_root/'filings'/issuer.ticker,refresh=refresh,filed_date=filing['filed'],report_date=filing['report_date']);parsed=parse(entry,accession=filing['accession'],form=filing['form']);value=parsed.as_dict() if hasattr(parsed,'as_dict') else parsed;package=json.loads((entry.parent/'package-manifest.json').read_text());reuse_source=None;captured.append(issuer.ticker)
  if normalize_cik(package.get('cik',''))!=issuer.cik:raise ValueError(issuer.ticker)
  receipt={'schema_version':'FINSIGHT-BATCH-13-STRUCTURAL-SOURCE-1','valuation_date':BATCH_13_VALUATION_DATE,'ticker':issuer.ticker,'cik':issuer.cik,'filing':filing,'source_packet_manifest_sha256':_sha256(_json_bytes(source_manifest)),'package_manifest_sha256':_sha256(_json_bytes(package)),'structural_filing_sha256':_sha256(_json_bytes(value)),'capture_mode':'reused' if prior else 'captured','reuse_source':reuse_source};target=output_root/issuer.ticker;_immutable_json(target/'package-manifest.json',package);_immutable_json(target/'structural-filing.json',value);_immutable_json(target/'source-receipt.json',receipt);cases.append({'ticker':issuer.ticker,'accession':filing['accession'],'filed':filing['filed'],'form':filing['form'],'result':'parsed','capture_mode':'reused' if prior else 'captured'})
 after={str(r):_tree_hash(r) for r in protected_serving_roots}
 if before!=after:raise RuntimeError('serving changed')
 summary={'valuation_date':BATCH_13_VALUATION_DATE,'attempted':10,'parsed':10,'failed':0,'reused_tickers':reused,'captured_tickers':captured,'cases':cases,'serving_hash_before':before,'serving_hash_after':after,'serving_artifacts_changed':False};_immutable_json(output_root/'summary.json',summary);return summary
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);p.add_argument('--cache-root',required=True,type=Path);p.add_argument('--reuse-root',action='append',default=[],type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));p.add_argument('--refresh',action='store_true');args=vars(p.parse_args());args['reuse_roots']=tuple(args.pop('reuse_root'));print(json.dumps(capture_structural_sources(**args),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
