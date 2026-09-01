#!/usr/bin/env python3
"""Capture parsed controlling filings for Batch 21 with cache-first reuse."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend')) if str(ROOT/'backend') not in sys.path else None
from app.us_valuation.batch_21 import BATCH_21_MANIFEST,BATCH_21_VALUATION_DATE
from app.us_valuation.sec_client import normalize_cik
from capture_batch_02_structural_sources import ELIGIBLE_FORMS,PROTECTED_ROOTS,_dependencies,_immutable_json,_json_bytes,_sha256,_tree_hash,_validate_paths
from capture_batch_12_structural_sources import _reuse_any_structural
def _control(root,i):
 p=Path(root)/i.ticker;m=json.loads((p/'source-manifest.json').read_text());
 if m.get('schema_version')!='FINSIGHT-BATCH-21-SOURCE-1' or m.get('issuer')!={'ticker':i.ticker,'cik':i.cik,'issuer_name':i.issuer_name}:raise ValueError(i.ticker)
 f=dict(max([r for r in m['eligible_filings'] if r['form'] in ELIGIBLE_FORMS],key=lambda r:(r['filed'],r['accession'])));s=json.loads((p/'submissions.json').read_text())['filings']['recent'];idx=[x for x,a in enumerate(s['accessionNumber']) if a==f['accession']]
 if len(idx)!=1:raise ValueError(i.ticker)
 x=idx[0];f['report_date']=s['reportDate'][x];return f,m
def capture_structural_sources(*,source_root:Path,output_root:Path,cache_root:Path,user_agent:str|None=None,refresh:bool=False,client=None,package_capture=None,parse=None,reuse_roots=(),protected_serving_roots=PROTECTED_ROOTS):
 source_root,output_root,cache_root=map(Path,(source_root,output_root,cache_root));_validate_paths(source_root,output_root,cache_root,protected_serving_roots);before={str(r):_tree_hash(r) for r in protected_serving_roots};controls={i.ticker:_control(source_root,i) for i in BATCH_21_MANIFEST};cached={i.ticker:_reuse_any_structural(tuple(map(Path,reuse_roots)),i,controls[i.ticker][0]) for i in BATCH_21_MANIFEST}
 if any(v is None for v in cached.values()) and (client is None or package_capture is None or parse is None):sec,pc,pa=_dependencies();client=client or sec(user_agent=user_agent,cache_dir=cache_root/'.sec-cache');package_capture=package_capture or pc;parse=parse or pa
 cases=[];reused=[];captured=[]
 for i in BATCH_21_MANIFEST:
  f,m=controls[i.ticker];prior=cached[i.ticker]
  if prior:value,package,reuse_source=prior;reused.append(i.ticker)
  else:e=package_capture(client,cik=i.cik,accession=f['accession'],primary_document=f['primary_document'],form=f['form'],output_dir=cache_root/'filings'/i.ticker,refresh=refresh,filed_date=f['filed'],report_date=f['report_date']);parsed=parse(e,accession=f['accession'],form=f['form']);value=parsed.as_dict() if hasattr(parsed,'as_dict') else parsed;package=json.loads((e.parent/'package-manifest.json').read_text());reuse_source=None;captured.append(i.ticker)
  if normalize_cik(package.get('cik',''))!=i.cik:raise ValueError(i.ticker)
  rec={'schema_version':'FINSIGHT-BATCH-21-STRUCTURAL-SOURCE-1','valuation_date':BATCH_21_VALUATION_DATE,'ticker':i.ticker,'cik':i.cik,'filing':f,'source_packet_manifest_sha256':_sha256(_json_bytes(m)),'package_manifest_sha256':_sha256(_json_bytes(package)),'structural_filing_sha256':_sha256(_json_bytes(value)),'capture_mode':'reused' if prior else 'captured','reuse_source':reuse_source};target=output_root/i.ticker;_immutable_json(target/'package-manifest.json',package);_immutable_json(target/'structural-filing.json',value);_immutable_json(target/'source-receipt.json',rec);cases.append({'ticker':i.ticker,'accession':f['accession'],'filed':f['filed'],'form':f['form'],'result':'parsed','capture_mode':'reused' if prior else 'captured'})
 after={str(r):_tree_hash(r) for r in protected_serving_roots}
 if before!=after:raise RuntimeError('serving changed')
 summary={'valuation_date':BATCH_21_VALUATION_DATE,'attempted':10,'parsed':10,'failed':0,'reused_tickers':reused,'captured_tickers':captured,'cases':cases,'serving_hash_before':before,'serving_hash_after':after,'serving_artifacts_changed':False};_immutable_json(output_root/'summary.json',summary);return summary
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);p.add_argument('--cache-root',required=True,type=Path);p.add_argument('--reuse-root',action='append',default=[],type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));p.add_argument('--refresh',action='store_true');a=vars(p.parse_args());a['reuse_roots']=tuple(a.pop('reuse_root'));print(json.dumps(capture_structural_sources(**a),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
