from __future__ import annotations
import hashlib,json
from datetime import date
from pathlib import Path
from .contract import PseValuationArtifact,canonical_json,sha256_object
from .models.comparables import market_relative_range
CONFIG_PATH=Path(__file__).with_name("config")/"phase_b_batch_10.json";MODEL_VERSION="PSE-V2-PHASE-B-B10-1.0";FROZEN_BATCH_TICKERS=("BLOOM","BEL","WEB","SUN","PHR","WPI","ACE","BHI","GPH","MJC")
def load_batch_config(path:Path=CONFIG_PATH):
 p=json.loads(path.read_text())
 if p.get("schema_version")!="PSE-V2-PHASE-B-BATCH-10.0" or tuple(p.get("frozen_tickers",()))!=FROZEN_BATCH_TICKERS:raise ValueError("Batch 10 confirmed frozen set mismatch")
 if set(p.get("issuers",{}))!=set(FROZEN_BATCH_TICKERS):raise ValueError("Batch 10 must contain exact ten")
 return p
def source_receipt(ticker,config):
 i=config["issuers"][ticker];r={"schema_version":"PSE-V2-REVIEWED-FACT-RECEIPT-1.0","batch_version":config["batch_version"],"review_status":config["review_status"],"retrieval_date":config["valuation_date"],"ticker":ticker,"issuer_name":i["issuer_name"],"source":i["source"],"facts":{"metric_value_per_share":i["metric_value_per_share"],"metric_label":i["metric_label"],"normalization":i["normalization"],"intrinsic_blocker":i["intrinsic_blocker"]},"note":"This deterministic receipt binds reviewed public facts, normalization, and official source links. It is not a redistributed filing copy."};raw=canonical_json(r)+b"\n";d=hashlib.sha256(raw).hexdigest();s=i["source"];return ({"document_id":d[:16],"label":s["label"],"form":s.get("form"),"period_end":s.get("period_end"),"published_at":s.get("published_at"),"url":s["url"],"source_page":None,"sha256":d},raw)
def build_batch_artifacts(config=None):
 c=config or load_batch_config();out={}
 for t in FROZEN_BATCH_TICKERS:
  i=c["issuers"][t];p=c["policies"][i["policy"]];s,_=source_receipt(t,c);r=market_relative_range(metric=p["metric"],metric_value_per_share=float(i["metric_value_per_share"]),assumptions=p["assumptions"],relation=p["relation"]);r.update({"policy_version":p["version"],"metric_label":i["metric_label"],"source_status":"reviewed_public_fact","source_document_sha256":s["sha256"],"source_page":None,"note":"Transparent screening fallback while the specialist intrinsic bridge remains incomplete."});e=r["estimates"];w=["Screening-grade market-relative estimate; this is not the unresolved specialist intrinsic valuation.","Gaming regulation, property values, ramp economics, debt, and capital claims can materially change value and are not replaced by this screening band."]
  if i.get("source_warning"):w.append(i["source_warning"])
  out[t]=PseValuationArtifact(model_version=MODEL_VERSION,ticker=t,issuer={"issuer_id":f"PSE:{t}","name":i["issuer_name"]},security={"security_id":f"PSE:{t}:COMMON","type":"ordinary_common"},subsector=i["subsector"],primary_model=i["primary_model"],valuation_date=date.fromisoformat(c["valuation_date"]),filing_period=s["period_end"],availability_type="market_relative_only",publication_state="provisional",scenarios={"bear":None,"base":None,"bull":None},numerical_range={"low":min(e.values()),"high":max(e.values())},market_relative=r,public_assumptions={"route_reason":i["route_reason"],"intrinsic_blocker":i["intrinsic_blocker"],"metric_basis":i["normalization"]["formula"],"reliability":"Low"},sources=[s],warnings=w,blocking_reasons=[i["intrinsic_blocker"]],input_hash=sha256_object({"ticker":t,"issuer":i,"policy":p,"source":s["sha256"],"model_version":MODEL_VERSION})).with_artifact_hash()
 return out
