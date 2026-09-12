#!/usr/bin/env python3
"""Capture Batch 45 cutoff-event filings and exhibits."""
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/"backend") not in sys.path:sys.path.insert(0,str(ROOT/"backend"))
from app.us_valuation.batch_45 import BATCH_45_MANIFEST,BATCH_45_VALUATION_DATE
from app.us_valuation.sec_client import SecClient
from capture_batch_37_event_sources import _immutable,_json
EVENT_FORMS={"8-K","8-K/A","424B5"}
def capture_events(*,source_root:Path,output_root:Path,user_agent:str|None=None)->dict:
    source_root,output_root=Path(source_root).resolve(),Path(output_root).resolve();client=SecClient(user_agent=user_agent,cache_dir=output_root/".cache");cases=[]
    for i in BATCH_45_MANIFEST:
        recent=json.loads((source_root/i.ticker/"submissions.json").read_text())["filings"]["recent"];entries=[]
        for idx,filed in enumerate(recent["filingDate"]):
            form=recent["form"][idx]
            if not("2026-06-30"<=filed<=BATCH_45_VALUATION_DATE and form in EVENT_FORMS):continue
            accession=recent["accessionNumber"][idx];primary=recent["primaryDocument"][idx];raw=client.filing_attachment(i.cik,accession,primary);docs=[(primary,raw)]
            for link in sorted(set(re.findall(r'href=["\x27]([^"\x27]+)',raw.decode(errors="ignore"),re.I))):
                low=link.lower()
                if "/" in link or not low.endswith((".htm",".html")) or not any(x in low for x in ("99","exhibit","release","earnings","ex10","ex4","presentation","livemaster")):continue
                docs.append((link,client.filing_attachment(i.cik,accession,link)))
            captured=[]
            for name,data in docs[:20]:target=output_root/i.ticker/accession/name;_immutable(target,data);captured.append({"path":str(target.relative_to(ROOT)),"sha256":hashlib.sha256(data).hexdigest()})
            entries.append({"accession":accession,"filed":filed,"report_date":recent["reportDate"][idx],"form":form,"items":recent["items"][idx],"primary_document":primary,"documents":captured})
        inventory=_json(entries);_immutable(output_root/i.ticker/"inventory.json",inventory);cases.append({"ticker":i.ticker,"filing_count":len(entries),"document_count":sum(len(r["documents"]) for r in entries),"inventory_sha256":hashlib.sha256(inventory).hexdigest()})
    summary={"schema_version":"FINSIGHT-BATCH-45-EVENT-SCREEN-1","valuation_date":BATCH_45_VALUATION_DATE,"attempted":10,"cases":cases,"serving_artifacts_changed":False};_immutable(output_root/"summary.json",_json(summary));return summary
def main():
    p=argparse.ArgumentParser();p.add_argument("--source-root",type=Path,required=True);p.add_argument("--output-root",type=Path,required=True);p.add_argument("--user-agent",default=os.environ.get("SEC_USER_AGENT"));print(json.dumps(capture_events(**vars(p.parse_args())),sort_keys=True))
if __name__=="__main__":main()
