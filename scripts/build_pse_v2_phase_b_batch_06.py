#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from app.pse_valuation.catalog import CATALOG_SCHEMA,POINTER_SCHEMA,load_pointer
from app.pse_valuation.phase_b_batch_06 import FROZEN_BATCH_TICKERS,build_batch_artifacts,load_batch_config,source_receipt
ROOT=Path(__file__).resolve().parents[1];SERVING_ROOT=ROOT/"backend/app/data/pse_valuation_catalogs";ACTIVE_POINTER=SERVING_ROOT/"active.json";DEFAULT_OUTPUT_ROOT=ROOT/"output/pse-valuation-candidates/phase-b-batch-06-candidate-a";PARENT_CATALOG_VERSION="PSE-V2-PHASE-B-B05-2026-09-23-1.0";PARENT_MANIFEST_SHA256="b6dc2ae35ad13e0ee2f40c11e0b7190441da651acf914e90fea3334302ece95b";CATALOG_VERSION="PSE-V2-PHASE-B-B06-2026-09-23-1.0"
def h(b):return hashlib.sha256(b).hexdigest()
def write(p,v):b=json.dumps(v,indent=2,sort_keys=True).encode()+b"\n";p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);return b
def snap():
 pr=ACTIVE_POINTER.read_bytes();p=json.loads(pr)
 if p.get("status")!="active" or p.get("catalog_version") not in {PARENT_CATALOG_VERSION,CATALOG_VERSION,"PSE-V2-PHASE-B-B07-2026-09-23-1.0","PSE-V2-PHASE-B-B08-2026-09-23-1.0","PSE-V2-PHASE-B-B09-2026-09-23-1.0","PSE-V2-PHASE-B-B10-2026-09-23-1.0","PSE-V2-PHASE-B-B11-2026-09-23-1.0","PSE-V2-PHASE-B-B12-2026-09-23-1.0","PSE-V2-PHASE-B-B13-2026-09-23-1.0","PSE-V2-PHASE-B-B14-2026-09-23-1.0","PSE-V2-PHASE-B-B15-2026-09-23-1.0", "PSE-V2-PHASE-B-B16-2026-09-25-1.0", "PSE-V2-PHASE-B-B17-2026-09-25-1.0", "PSE-V2-PHASE-B-B18-2026-09-25-1.0", "PSE-V2-PHASE-B-B19-2026-09-25-1.0", "PSE-V2-PHASE-B-B20-2026-09-25-1.0", "PSE-V2-PHASE-B-B21-2026-09-25-1.0", "PSE-V2-PHASE-B-B22-2026-09-25-1.0", "PSE-V2-PHASE-B-B23-2026-09-25-1.0", "PSE-V2-PHASE-B-B24-2026-09-25-1.0", "PSE-V2-PHASE-B-B25-2026-09-25-1.0", "PSE-V2-PHASE-B-B26-2026-09-25-1.0", "PSE-V2-PHASE-B-B27-2026-09-25-1.0", "PSE-V2-PHASE-B-B28-2026-09-26-1.0"}:raise RuntimeError("unexpected active catalog")
 ar=SERVING_ROOT/p["catalog_path"];mr=(ar/"manifest.json").read_bytes();parent=SERVING_ROOT/PARENT_CATALOG_VERSION;pmr=(parent/"manifest.json").read_bytes()
 if h(pmr)!=PARENT_MANIFEST_SHA256:raise RuntimeError("parent hash differs")
 pm=json.loads(pmr)
 if pm["artifact_count"]!=58:raise RuntimeError("parent count differs")
 return pr,mr,parent,pm
def build(output_root=DEFAULT_OUTPUT_ROOT):
 output_root=Path(output_root).resolve()
 if SERVING_ROOT.resolve() in output_root.parents:raise RuntimeError("candidate in serving root")
 pb,mb,parent,pm=snap();c=load_batch_config();batch=build_batch_artifacts(c);cr=output_root/c["catalog_version"];entries=[];pe={r["ticker"]:r for r in pm["entries"]}
 for t in sorted(pe):raw=(parent/"artifacts"/f"{t}.json").read_bytes();target=cr/"artifacts"/f"{t}.json";target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);entries.append(dict(pe[t]))
 for t in FROZEN_BATCH_TICKERS:
  a=batch[t];ref,rr=source_receipt(t,c);ep=cr/"evidence"/f"{t}.json";ep.parent.mkdir(parents=True,exist_ok=True);ep.write_bytes(rr);raw=write(cr/"artifacts"/f"{t}.json",a.model_dump(mode="json"));entries.append({"ticker":t,"availability_type":a.availability_type,"publication_state":a.publication_state,"primary_model":a.primary_model,"artifact_sha256":h(raw),"source_audit":f"PSE-V2-PHASE-B-B06-{t}-SOURCE-1.0"})
 entries.sort(key=lambda x:x["ticker"]);av={k:0 for k in ("intrinsic_valuation","market_relative_only","not_available")};pub={k:0 for k in ("approved","provisional","blocked")}
 for e in entries:av[e["availability_type"]]+=1;pub[e["publication_state"]]+=1
 if len(entries)!=68:raise RuntimeError("count mismatch")
 manifest={"schema_version":CATALOG_SCHEMA,"catalog_version":c["catalog_version"],"universe_version":c["universe_version"],"valuation_date":c["valuation_date"],"catalog_status":"staged","artifact_count":68,"availability_counts":av,"publication_counts":pub,"batch":{"batch_version":c["batch_version"],"frozen_tickers":list(FROZEN_BATCH_TICKERS),"active_parent_catalog":pm["catalog_version"],"active_parent_manifest_sha256":PARENT_MANIFEST_SHA256},"entries":entries};raw=write(cr/"manifest.json",manifest);write(output_root/"staged.json",{"schema_version":POINTER_SCHEMA,"status":"staged","catalog_version":c["catalog_version"],"catalog_path":c["catalog_version"],"manifest_sha256":h(raw)});assert len(load_pointer(output_root).entries)==68;pa,ma,_,_=snap();assert pa==pb and ma==mb;return cr
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=DEFAULT_OUTPUT_ROOT);a=p.parse_args();print(build(a.output))
