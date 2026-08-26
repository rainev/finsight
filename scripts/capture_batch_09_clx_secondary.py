#!/usr/bin/env python3
"""Capture and parse CLX's linked financial-statements document for recovery."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.arelle_adapter import parse_structural_filing
from capture_batch_02_sources import PROTECTED_ROOTS,_tree_hash
from capture_batch_02_structural_sources import _immutable_json
CIK='0000021076';ACCESSION='0000021076-26-000034';SECONDARY='clx-20260630_d2.htm';COMBINED='clx-20260630-combined.htm'
def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _combine_ixds(primary:bytes,secondary:bytes)->bytes:
 primary_lower=primary.lower();secondary_lower=secondary.lower();primary_close=primary_lower.rfind(b'</body>');secondary_open=secondary_lower.find(b'<body');secondary_start=secondary_lower.find(b'>',secondary_open)+1;secondary_close=secondary_lower.rfind(b'</body>')
 if min(primary_close,secondary_open,secondary_start,secondary_close)<0:raise ValueError('split Inline XBRL body boundary missing')
 return primary[:primary_close]+b'\n<!-- FinSight deterministic split-IXDS composition -->\n'+secondary[secondary_start:secondary_close]+b'\n'+primary[primary_close:]
def run(*,existing_package:Path,archive:Path,output_root:Path):
 existing_package,output_root=Path(existing_package),Path(output_root);before={str(p):_tree_hash(p) for p in PROTECTED_ROOTS};package=output_root/'package'
 if not package.exists():shutil.copytree(existing_package,package)
 archive=Path(archive);raw=zipfile.ZipFile(archive).read(SECONDARY);target=package/SECONDARY
 if target.exists() and target.read_bytes()!=raw:raise FileExistsError(target)
 if not target.exists():
  stage=Path(tempfile.mkdtemp(prefix='.clx-secondary-',dir=package))/SECONDARY
  try:stage.write_bytes(raw);stage.replace(target)
  finally:shutil.rmtree(stage.parent,ignore_errors=True)
 manifest_path=package/'package-manifest.json';manifest=json.loads(manifest_path.read_text());source_url=f'https://www.sec.gov/Archives/edgar/data/21076/000002107626000034/{SECONDARY}';stable_epoch=float(manifest['cached_at_epoch']);primary_name='clx-20260630.htm';combined_raw=_combine_ixds((package/primary_name).read_bytes(),raw);combined_target=package/COMBINED;combined_target.write_bytes(combined_raw);composed_url=f'urn:finsight:split-ixds:{CIK}:{ACCESSION}'
 manifest['files']=[row for row in manifest['files'] if row.get('local_path') not in {SECONDARY,COMBINED}];manifest['files'].extend([{'byte_count':len(raw),'dependency_depth':0,'local_path':SECONDARY,'logical_url':source_url,'retrieved_at_epoch':stable_epoch,'sha256':_sha(raw),'source_url':source_url,'taxonomy_namespace':'','taxonomy_version':'unknown'},{'byte_count':len(combined_raw),'dependency_depth':0,'local_path':COMBINED,'logical_url':composed_url,'retrieved_at_epoch':stable_epoch,'sha256':_sha(combined_raw),'source_url':composed_url,'taxonomy_namespace':'','taxonomy_version':'unknown'}]);manifest['files']=sorted(manifest['files'],key=lambda row:row['local_path']);manifest['entrypoint_local_path']=COMBINED;manifest['primary_document']=COMBINED;manifest['primary_source_url']=composed_url;manifest['resource_count']=len(manifest['files']);manifest['total_bytes']=sum(int(row['byte_count']) for row in manifest['files']);manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 parsed=parse_structural_filing(combined_target,accession=ACCESSION,form='10-K').as_dict();_immutable_json(output_root/'structural-filing.json',parsed)
 receipt={'schema_version':'FINSIGHT-BATCH-09-CLX-SECONDARY-1','valuation_date':'2026-08-14','ticker':'CLX','cik':CIK,'accession':ACCESSION,'archive':str(archive),'archive_sha256':_sha(archive.read_bytes()),'primary_document':primary_name,'primary_sha256':_sha((package/primary_name).read_bytes()),'secondary_document':SECONDARY,'source_url':source_url,'secondary_sha256':_sha(raw),'composition':'primary IXBRL resources plus secondary IXBRL body','combined_document':COMBINED,'combined_sha256':_sha(combined_raw),'structural_sha256':_sha((json.dumps(parsed,indent=2,sort_keys=True)+'\n').encode()),'fact_count':len(parsed.get('facts',[]))};_immutable_json(output_root/'source-receipt.json',receipt);after={str(p):_tree_hash(p) for p in PROTECTED_ROOTS}
 if before!=after:raise RuntimeError('serving changed')
 return {**receipt,'serving_artifacts_changed':False,'serving_hash_before':before,'serving_hash_after':after}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--existing-package',required=True,type=Path);p.add_argument('--archive',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path);print(json.dumps(run(**vars(p.parse_args())),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
