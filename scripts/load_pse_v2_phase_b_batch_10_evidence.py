#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import date,datetime,timezone
from pathlib import Path
from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation.persistence import capture_document,store_assumption,store_reported_fact,store_valuation_run,upsert_security
from app.pse_valuation.phase_b_batch_10 import FROZEN_BATCH_TICKERS,load_batch_config,source_receipt
from app.services import company_service
ROOT=Path(__file__).resolve().parents[1];DEFAULT_CANDIDATE_ROOT=ROOT/"output/pse-valuation-candidates/phase-b-batch-10-candidate-a"
def main(candidate_root=DEFAULT_CANDIDATE_ROOT):
 c=load_batch_config();cr=Path(candidate_root)/c["catalog_version"];pool.open()
 try:
  run_migrations();docs={};now=datetime.now(timezone.utc)
  for t in FROZEN_BATCH_TICKERS:
   i=c["issuers"][t];sid=f"PSE:{t}:COMMON";upsert_security(security_id=sid,issuer_id=f"PSE:{t}",ticker=t,issuer_name=i["issuer_name"],subsector=i["subsector"],source_as_of=date.fromisoformat(c["valuation_date"]));company_service.upsert(ticker=t,name=i["issuer_name"],sector=i["subsector"],currency="PHP",market="PH",exchange="PSE");ref,raw=source_receipt(t,c);docs[t]=capture_document(issuer_id=f"PSE:{t}",security_id=sid,source_url=ref["url"],published_at=None,retrieved_at=now,filename=f"{t}-receipt.json",raw=raw,content_type="application/json");p=c["policies"][i["policy"]];store_reported_fact(docs[t]["id"],{"metric":"screening_metric_per_share","value":i["metric_value_per_share"],"currency":"PHP","unit_scale":"per_share","period_end":date.fromisoformat(i["source"]["period_end"]),"period_type":"interim_or_ttm","measurement_type":"flow" if p["metric"]=="price_to_sales" else "stock","consolidation_scope":"consolidated_common","source_page":None})
   for s,v in p["assumptions"].items():store_assumption({"version":p["version"],"scope":t,"metric":p["metric"],"scenario":s,"value":v,"unit":"multiple","effective_date":date.fromisoformat(c["valuation_date"]),"source_or_rationale":i["route_reason"],"reviewer":"Phase B Batch 10 reviewed policy"})
  for t in FROZEN_BATCH_TICKERS:a=json.loads((cr/"artifacts"/f"{t}.json").read_text());store_valuation_run(a,{"artifact_hash":a["artifact_hash"],"receipt_sha256":docs[t]["sha256"]})
  print({"batch":c["batch_version"],"securities":10,"documents":10,"reported_facts":10,"assumptions":30,"runs":10})
 finally:pool.close()
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--candidate-root",type=Path,default=DEFAULT_CANDIDATE_ROOT);a=p.parse_args();main(a.candidate_root)
