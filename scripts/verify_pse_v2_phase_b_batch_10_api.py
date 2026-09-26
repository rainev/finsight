import argparse,json,time,urllib.error,urllib.request
from pathlib import Path
TICKERS=("BLOOM","BEL","WEB","SUN","PHR","WPI","ACE","BHI","GPH","MJC")
def req(base,path,token=None,body=None):
 h={"Content-Type":"application/json"};
 if token:h["Authorization"]=f"Bearer {token}"
 r=urllib.request.Request(f"{base}/api{path}",data=json.dumps(body).encode() if body is not None else None,headers=h,method="POST" if body is not None else "GET")
 try:
  with urllib.request.urlopen(r) as x:return x.status,json.loads(x.read())
 except urllib.error.HTTPError as e:return e.code,json.loads(e.read() or b"{}")
def main(base,root,expected_status="staged"):
 assert req(base,"/pse-valuations")[0]==401;cred={"email":"pse-b10-verifier@example.com","password":"PseB10!Verify2026"};s,p=req(base,"/auth/register",body=cred)
 if s==409:s,p=req(base,"/auth/login",body=cred)
 token=p["access_token"];s,l=req(base,"/pse-valuations",token);assert s==200 and l["count"]==108 and l["catalog_status"]==expected_status;details=calc=0;baselines={};batch_artifacts={}
 for path in sorted((root/"artifacts").glob("*.json")):
  t=path.stem;stored=json.loads(path.read_text());s,d=req(base,f"/pse-valuations/{t}",token);assert s==200 and {k:d[k] for k in stored}==stored;details+=1
  if t in TICKERS:batch_artifacts[t]=stored
 if expected_status=="active":time.sleep(58)
 for t in TICKERS:
  s,v=req(base,f"/pse-valuations/{t}/calculator",token);e=batch_artifacts[t]["market_relative"]["estimates"]["base"];assert s==200 and abs(v["baseline_result"]["base"]-e)<1e-9;baselines[t]=v;calc+=1
 v=baselines["BEL"];_,e=req(base,"/pse-valuations/BEL/calculator",token,body={"overrides":{"valuation_multiple":0.7},"scenario":"base","save":True});assert e["result"]["base"]>v["baseline_result"]["base"] and e["saved_id"]
 print({"catalog_status":l["catalog_status"],"count":108,"detail_parity":details,"calculator_parity":calc,"bel_base":v["baseline_result"]["base"],"bel_edited":e["result"]["base"],"saved_id":e["saved_id"],"unauth":401})
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--base",default="http://localhost:4021");p.add_argument("--catalog-root",type=Path,required=True);p.add_argument("--expected-status",choices=("staged","active"),default="staged");a=p.parse_args();main(a.base,a.catalog_root,a.expected_status)
