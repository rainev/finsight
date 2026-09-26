#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,urllib.error,urllib.request
from pathlib import Path
EMAIL="pse-b05-verifier-20260923@example.com";PASSWORD="PseB05!Verify2026"
BATCH_TICKERS=("PNB","RCB","UBP","AUB","PBB","PSB","COL","PSE","NRCP","MFIN");INTRINSIC=set(BATCH_TICKERS)-{"PSE","MFIN"}
def request(base,path,token=None,body=None):
 headers={"Content-Type":"application/json"};
 if token:headers["Authorization"]=f"Bearer {token}"
 req=urllib.request.Request(f"{base}/api{path}",data=json.dumps(body).encode() if body is not None else None,headers=headers,method="POST" if body is not None else "GET")
 try:
  with urllib.request.urlopen(req) as r:return r.status,json.loads(r.read())
 except urllib.error.HTTPError as e:return e.code,json.loads(e.read() or b"{}")
def auth(base):
 s,p=request(base,"/auth/register",body={"email":EMAIL,"password":PASSWORD})
 if s==409:s,p=request(base,"/auth/login",body={"email":EMAIL,"password":PASSWORD})
 if s not in {200,201}:raise RuntimeError(f"auth failed {s} {p}")
 return p["access_token"]
def main(base,catalog_root,expected_status="staged"):
 unauth,_=request(base,"/pse-valuations")
 if unauth!=401:raise RuntimeError("auth boundary failed")
 token=auth(base);status,listing=request(base,"/pse-valuations",token)
 if status!=200 or listing["count"]!=58 or listing["catalog_status"]!=expected_status:raise RuntimeError("list mismatch")
 stored_tickers=sorted(p.stem for p in (catalog_root/"artifacts").glob("*.json"))
 if [r["ticker"] for r in listing["items"]]!=stored_tickers:raise RuntimeError("membership mismatch")
 details=calculators=0
 for ticker in stored_tickers:
  status,detail=request(base,f"/pse-valuations/{ticker}",token);stored=json.loads((catalog_root/"artifacts"/f"{ticker}.json").read_text())
  if status!=200 or {k:detail[k] for k in stored}!=stored:raise RuntimeError(f"{ticker} detail mismatch")
  details+=1
  if ticker in BATCH_TICKERS:
   s,v=request(base,f"/pse-valuations/{ticker}/calculator",token);sp,c=request(base,f"/pse-valuations/{ticker}/calculator",token,body={"overrides":{},"scenario":"base"});expected=stored["scenarios"]["base"]["value_per_share"] if ticker in INTRINSIC else stored["market_relative"]["estimates"]["base"]
   if s!=200 or sp!=200 or abs(v["baseline_result"]["base"]-expected)>1e-9 or abs(c["result"]["base"]-expected)>1e-9:raise RuntimeError(f"{ticker} calculator mismatch")
   calculators+=1
 _,pnb=request(base,"/pse-valuations/PNB/calculator",token);_,pnb_edit=request(base,"/pse-valuations/PNB/calculator",token,body={"overrides":{"cost_of_equity":0.11},"scenario":"base","save":True})
 if pnb_edit["result"]["base"]<=pnb["baseline_result"]["base"] or not pnb_edit.get("saved_id"):raise RuntimeError("PNB edit failed")
 _,pse=request(base,"/pse-valuations/PSE/calculator",token);_,pse_edit=request(base,"/pse-valuations/PSE/calculator",token,body={"overrides":{"valuation_multiple":13.0},"scenario":"base"})
 if pse_edit["result"]["base"]<=pse["baseline_result"]["base"]:raise RuntimeError("PSE edit failed")
 print({"catalog_version":listing["catalog_version"],"catalog_status":listing["catalog_status"],"list_count":58,"detail_parity":details,"calculator_parity":calculators,"pnb_base":pnb["baseline_result"]["base"],"pnb_edited":pnb_edit["result"]["base"],"pse_base":pse["baseline_result"]["base"],"pse_edited":pse_edit["result"]["base"],"saved_scenario_id":pnb_edit["saved_id"],"unauthenticated_status":unauth})
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--base",default="http://localhost:4021");p.add_argument("--catalog-root",type=Path,required=True);p.add_argument("--expected-status",choices=("staged","active"),default="staged");a=p.parse_args();main(a.base.rstrip("/"),a.catalog_root.resolve(),a.expected_status)
