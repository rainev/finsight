#!/usr/bin/env python3
"""Capture cutoff-eligible EFX financing and GD rescission events for Batch 18."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BACKEND=ROOT/'backend';sys.path.insert(0,str(BACKEND)) if str(BACKEND) not in sys.path else None
from app.us_valuation.sec_client import SecClient,sec_archive_url
from capture_batch_02_sources import PROTECTED_ROOTS,_assert_non_serving,_tree_hash
from capture_batch_02_structural_sources import _immutable_json
SOURCES=(
 {'ticker':'EFX','cik':'0000033185','accession':'0001193125-26-323760','form':'8-K','filed':'2026-07-29','report_date':'2026-07-22','primary_document':'d125882d8k.htm','role':'post_balance_sheet_notes_issuance'},
 {'ticker':'GD','cik':'0000040533','accession':'0001193125-26-332899','form':'8-K','filed':'2026-08-04','report_date':'2026-07-30','primary_document':'d122083d8k.htm','role':'share_rescission_offer'},)
def run(*,output_root:Path,user_agent:str|None=None,refresh:bool=False):
 output_root=Path(output_root);roots=tuple(Path(r) for r in PROTECTED_ROOTS);_assert_non_serving(output_root,roots);before={str(r):_tree_hash(r) for r in roots};client=SecClient(user_agent=user_agent,cache_dir=output_root.parent/'.sec-cache');cases=[]
 for src in SOURCES:
  raw=client.filing_attachment(src['cik'],src['accession'],src['primary_document'],refresh=refresh,max_bytes=8*1024*1024);text=raw.decode('utf-8',errors='replace')
  tokens=(('$500,000,000','$990.5','July','29, 2026') if src['ticker']=='EFX' else ('1,010,925','rescission','August','4, 2026'))
  if any(token.lower() not in text.lower() for token in tokens):raise RuntimeError(f"{src['ticker']}: event terms changed")
  digest=hashlib.sha256(raw).hexdigest();target=output_root/src['ticker'];target.mkdir(parents=True,exist_ok=True);document=target/src['primary_document']
  if document.exists() and document.read_bytes()!=raw:raise FileExistsError(document)
  if not document.exists():document.write_bytes(raw)
  terms=({'aggregate_principal_usd':1_000_000_000.0,'net_proceeds_usd':990_500_000.0,'issue_date':'2026-07-29','intended_use':'repay commercial paper borrowings','cutoff_status':'issued'} if src['ticker']=='EFX' else {'maximum_rescission_shares':1_010_925.0,'offer_date':'2026-08-04','management_materiality_assessment':'not expected to materially affect financial condition results or liquidity','cutoff_status':'offer_open'})
  treatment=('Add $1B issued notes and $990.5M proceeds at cutoff; do not assume intended commercial-paper repayment occurred without a source.' if src['ticker']=='EFX' else 'Keep the offer within the governed diluted-share range; do not add or remove shares before election and settlement evidence.')
  receipt={'schema_version':'FINSIGHT-BATCH-18-EVENT-SOURCE-1','valuation_date':'2026-08-14',**src,'url':sec_archive_url(src['cik'],src['accession'],src['primary_document']),'document_sha256':digest,'document_bytes':len(raw),'reported_terms':terms,'treatment':treatment};_immutable_json(target/'source-receipt.json',receipt);cases.append({'ticker':src['ticker'],'accession':src['accession'],'filed':src['filed'],'document_sha256':digest})
 after={str(r):_tree_hash(r) for r in roots}
 if before!=after:raise RuntimeError('serving changed')
 summary={'attempted':2,'captured':2,'failed':0,'cases':cases,'serving_hash_before':before,'serving_hash_after':after,'serving_artifacts_changed':False};_immutable_json(output_root/'summary.json',summary);return summary
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',required=True,type=Path);p.add_argument('--user-agent',default=os.environ.get('SEC_USER_AGENT'));p.add_argument('--refresh',action='store_true');print(json.dumps(run(**vars(p.parse_args())),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
