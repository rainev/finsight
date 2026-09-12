#!/usr/bin/env python3
"""Capture Batch 40 cutoff-event filings for later source review."""
import sys,json,hashlib,os,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.us_valuation.batch_40 import BATCH_40_MANIFEST
from app.us_valuation.sec_client import SecClient
from capture_batch_37_event_sources import _immutable,_json


def _is_relevant_attachment(link):
 lower=link.lower()
 return '/' not in link and link.endswith(('.htm','.html')) and any(x in lower for x in ('99','exhibit','release','earnings'))


def run():
 out=ROOT/'output/batch-40-event-review-20260907';client=SecClient(user_agent=os.environ.get('SEC_USER_AGENT'),cache_dir=out/'.cache')
 for issuer in BATCH_40_MANIFEST:
  rec=json.loads((ROOT/'output/batch-40-sec-source-packets-20260907'/issuer.ticker/'submissions.json').read_text())['filings']['recent'];entries=[]
  for i,d in enumerate(rec['filingDate']):
   if not ('2026-06-30'<=d<='2026-08-14' and rec['form'][i] in ('8-K','8-K/A','424B5')):continue
   acc=rec['accessionNumber'][i];name=rec['primaryDocument'][i];raw=client.filing_attachment(issuer.cik,acc,name);documents=[(name,raw)]
   for link in sorted(set(re.findall(r'href=["\x27]([^"\x27]+)',raw.decode(errors='ignore'),re.I))):
    if _is_relevant_attachment(link):documents.append((link,client.filing_attachment(issuer.cik,acc,link)))
   ds=[]
   for filename,data in documents:
    _immutable(out/issuer.ticker/acc/filename,data);ds.append({'path':str((out/issuer.ticker/acc/filename).relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest()})
   entries.append({'accession':acc,'filed':d,'form':rec['form'][i],'items':rec['items'][i],'documents':ds})
  _immutable(out/issuer.ticker/'inventory.json',_json(entries));print(issuer.ticker,len(entries),flush=True)
if __name__=='__main__':run()
