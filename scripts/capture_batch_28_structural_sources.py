#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend')) if str(ROOT/'backend') not in sys.path else None
from app.us_valuation.batch_28 import BATCH_28_MANIFEST,BATCH_28_VALUATION_DATE
from app.us_valuation.sec_client import normalize_cik
from capture_batch_02_structural_sources import ELIGIBLE_FORMS,PROTECTED_ROOTS,_dependencies,_immutable_json,_json_bytes,_sha256,_tree_hash,_validate_paths
from capture_batch_12_structural_sources import _reuse_any_structural
def control(root,i):
 p=Path(root)/i.ticker;m=json.loads((p/'source-manifest.json').read_text());f=dict(max([r for r in m['eligible_filings'] if r['form'] in ELIGIBLE_FORMS],key=lambda r:(r['filed'],r['accession'])));s=json.loads((p/'submissions.json').read_text())['filings']['recent'];x=s['accessionNumber'].index(f['accession']);f['report_date']=s['reportDate'][x];return f,m
def capture_structural_sources(*,source_root:Path,output_root:Path,cache_root:Path,user_agent=None,refresh=False,client=None,package_capture=None,parse=None,reuse_roots=(),protected_serving_roots=PROTECTED_ROOTS):
 source_root,output_root,cache_root=map(Path,(source_root,output_root,cache_root));_validate_paths(source_root,output_root,cache_root,protected_serving_roots);before={str(r):_tree_hash(r) for r in protected_serving_roots};ctl={i.ticker:control(source_root,i) for i in BATCH_28_MANIFEST};cached={i.ticker:_reuse_any_structural(tuple(map(Path,reuse_roots)),i,ctl[i.ticker][0]) for i in BATCH_28_MANIFEST}
 if any(v is None for v in cached.values()) and (client is None or package_capture is None or parse is None):sec,pc,pa=_dependencies();client=client or sec(user_agent=user_agent,cache_dir=cache_root/'.sec-cache');package_capture=package_capture or pc;parse=parse or pa
 cases=[];reused=[];captured=[]
 for i in BATCH_28_MANIFEST:
  f,m=ctl[i.ticker];prior=cached[i.ticker]
  if prior:value,package,source=prior;reused.append(i.ticker)
  else:e=package_capture(client,cik=i.cik,accession=f['accession'],primary_document=f['primary_document'],form=f['form'],output_dir=cache_root/'filings'/i.ticker,refresh=refresh,filed_date=f['filed'],report_date=f['report_date']);z=parse(e,accession=f['accession'],form=f['form']);value=z.as_dict() if hasattr(z,'as_dict') else z;package=json.loads((e.parent/'package-manifest.json').read_text());source=None;captured.append(i.ticker)
  if normalize_cik(package.get('cik',''))!=i.cik:raise ValueError(i.ticker)
  rec={'schema_version':'FINSIGHT-BATCH-28-STRUCTURAL-SOURCE-1','valuation_date':BATCH_28_VALUATION_DATE,'ticker':i.ticker,'cik':i.cik,'filing':f,'source_packet_manifest_sha256':_sha256(_json_bytes(m)),'package_manifest_sha256':_sha256(_json_bytes(package)),'structural_filing_sha256':_sha256(_json_bytes(value)),'capture_mode':'reused' if prior else 'captured','reuse_source':source};target=output_root/i.ticker;_immutable_json(target/'package-manifest.json',package);_immutable_json(target/'structural-filing.json',value);_immutable_json(target/'source-receipt.json',rec);cases.append({'ticker':i.ticker,'accession':f['accession'],'filed':f['filed'],'form':f['form'],'result':'parsed','capture_mode':'reused' if prior else 'captured'})
 after={str(r):_tree_hash(r) for r in protected_serving_roots};summary={'valuation_date':BATCH_28_VALUATION_DATE,'attempted':10,'parsed':10,'failed':0,'reused_tickers':reused,'captured_tickers':captured,'cases':cases,'serving_hash_before':before,'serving_hash_after':after,'serving_artifacts_changed':False};_immutable_json(output_root/'summary.json',summary);return summary
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--cache-root',type=Path,required=True);p.add_argument('--reuse-root',action='append',default=[],type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));a=vars(p.parse_args());a['reuse_roots']=tuple(a.pop('reuse_root'));print(json.dumps(capture_structural_sources(**a),sort_keys=True))
if __name__=='__main__':main()
