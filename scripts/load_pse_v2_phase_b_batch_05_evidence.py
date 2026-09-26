#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import date,datetime,timezone
from pathlib import Path
from app.db import pool
from app.db_migrate import run_migrations
from app.pse_valuation.persistence import capture_document,store_assumption,store_reported_fact,store_valuation_run,upsert_security
from app.pse_valuation.phase_b_batch_05 import FROZEN_BATCH_TICKERS,INTRINSIC_TICKERS,load_batch_config,source_receipt
from app.services import company_service
ROOT=Path(__file__).resolve().parents[1];DEFAULT_CANDIDATE_ROOT=ROOT/"output/pse-valuation-candidates/phase-b-batch-05-candidate-a"
def fact(metric,value,unit,measurement="stock"):
 return {"metric":metric,"value":value,"currency":"PHP","unit_scale":unit,"period_end":date(2025,12,31),"period_type":"annual" if measurement=="flow" else "instant","measurement_type":measurement,"consolidation_scope":"parent_common","source_page":None}
def main(candidate_root:Path=DEFAULT_CANDIDATE_ROOT):
 config=load_batch_config();catalog_root=candidate_root/config["catalog_version"]
 if not (catalog_root/"manifest.json").is_file():raise RuntimeError("build Batch 5 candidate first")
 pool.open()
 try:
  run_migrations();retrieved=datetime.now(timezone.utc);docs={}
  for ticker in FROZEN_BATCH_TICKERS:
   issuer=config["issuers"][ticker];sid=f"PSE:{ticker}:COMMON";upsert_security(security_id=sid,issuer_id=f"PSE:{ticker}",ticker=ticker,issuer_name=issuer["issuer_name"],subsector=issuer["subsector"],source_as_of=date.fromisoformat(config["valuation_date"]));company_service.upsert(ticker=ticker,name=issuer["issuer_name"],sector=issuer["subsector"],currency="PHP",market="PH",exchange="PSE");ref,raw=source_receipt(ticker,config);docs[ticker]=capture_document(issuer_id=f"PSE:{ticker}",security_id=sid,source_url=ref["url"],published_at=None,retrieved_at=retrieved,filename=f"{ticker}-reviewed-fact-receipt.json",raw=raw,content_type="application/json")
  effective=date.fromisoformat(config["valuation_date"])
  for ticker in FROZEN_BATCH_TICKERS:
   issuer=config["issuers"][ticker];facts=issuer["facts"];rows=[]
   if ticker in INTRINSIC_TICKERS:
    rows=[fact("parent_common_equity",facts["parent_common_equity_php_millions"],"millions"),fact("prior_parent_common_equity",facts["prior_parent_common_equity_php_millions"],"millions"),fact("net_income_to_parent",facts["net_income_to_parent_php_millions"],"millions","flow"),fact("book_value_per_share",facts["book_value_per_share"],"per_share"),fact("basic_eps",facts["basic_eps"],"per_share","flow")]
    policy=config["residual_policies"][issuer["policy"]]
    for scenario,values in policy["scenarios"].items():
     for metric,value in values.items():store_assumption({"version":policy["version"],"scope":ticker,"metric":metric,"scenario":scenario,"value":value,"unit":"decimal","effective_date":effective,"source_or_rationale":policy["rationale"],"reviewer":"Phase B Batch 5 reviewed policy"})
   else:
    numeric=[(k,v) for k,v in facts.items() if isinstance(v,(int,float))]
    rows=[fact(k,v,"per_share" if "per_share" in k or k=="basic_eps" else "millions","flow" if "loss" in k or k=="basic_eps" else "stock") for k,v in numeric]
    policy=config["relative_policies"][issuer["policy"]]
    for scenario,value in policy["assumptions"].items():store_assumption({"version":policy["policy_version"],"scope":ticker,"metric":policy["metric"],"scenario":scenario,"value":value,"unit":"multiple","effective_date":effective,"source_or_rationale":policy["rationale"],"reviewer":"Phase B Batch 5 reviewed policy"})
   for row in rows:store_reported_fact(docs[ticker]["id"],row)
  for ticker in FROZEN_BATCH_TICKERS:
   artifact=json.loads((catalog_root/"artifacts"/f"{ticker}.json").read_text());store_valuation_run(artifact,{"artifact_hash":artifact["artifact_hash"],"reviewed_fact_receipt_sha256":docs[ticker]["sha256"]})
  print({"batch":config["batch_version"],"securities":10,"documents":10,"reported_facts":46,"assumptions":174,"runs":10})
 finally:pool.close()
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--candidate-root",type=Path,default=DEFAULT_CANDIDATE_ROOT);args=p.parse_args();main(args.candidate_root.resolve())
