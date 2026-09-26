import argparse,json,urllib.request,urllib.error
from pathlib import Path
T=("TEL","GLO","CNVRG","DITO","NOW","GMA7","ABS","MB","DFNN","PLUS")
def req(base,path,token=None,body=None):
 h={"Content-Type":"application/json"};
 if token:h["Authorization"]=f"Bearer {token}"
 r=urllib.request.Request(f"{base}/api{path}",data=json.dumps(body).encode() if body is not None else None,headers=h,method="POST" if body is not None else "GET")
 try:
  with urllib.request.urlopen(r) as x:return x.status,json.loads(x.read())
 except urllib.error.HTTPError as e:return e.code,json.loads(e.read() or b"{}")
def main(base,root,expected_status="staged"):
 assert req(base,"/pse-valuations")[0]==401;s,p=req(base,"/auth/register",body={"email":"pse-b06-verifier@example.com","password":"PseB06!Verify2026"})
 if s==409:s,p=req(base,"/auth/login",body={"email":"pse-b06-verifier@example.com","password":"PseB06!Verify2026"})
 token=p["access_token"];s,l=req(base,"/pse-valuations",token);assert s==200 and l["count"]==68 and l["catalog_status"]==expected_status;details=calc=0
 for path in sorted((root/"artifacts").glob("*.json")):
  t=path.stem;stored=json.loads(path.read_text());s,d=req(base,f"/pse-valuations/{t}",token);assert s==200 and {k:d[k] for k in stored}==stored;details+=1
  if t in T:
   s,v=req(base,f"/pse-valuations/{t}/calculator",token);sp,c=req(base,f"/pse-valuations/{t}/calculator",token,body={"overrides":{},"scenario":"base"});e=stored["market_relative"]["estimates"]["base"];assert s==sp==200 and abs(v["baseline_result"]["base"]-e)<1e-9 and abs(c["result"]["base"]-e)<1e-9;calc+=1
 _,v=req(base,"/pse-valuations/TEL/calculator",token);_,e=req(base,"/pse-valuations/TEL/calculator",token,body={"overrides":{"valuation_multiple":11},"scenario":"base","save":True});assert e["result"]["base"]>v["baseline_result"]["base"] and e["saved_id"]
 print({"catalog_status":l["catalog_status"],"count":68,"detail_parity":details,"calculator_parity":calc,"tel_base":v["baseline_result"]["base"],"tel_edited":e["result"]["base"],"saved_id":e["saved_id"],"unauth":401})
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--base",default="http://localhost:4021");p.add_argument("--catalog-root",type=Path,required=True);p.add_argument("--expected-status",choices=("staged","active"),default="staged");a=p.parse_args();main(a.base,a.catalog_root,a.expected_status)
