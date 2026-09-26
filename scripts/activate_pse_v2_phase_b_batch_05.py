#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,shutil
from pathlib import Path
from app.pse_valuation.catalog import POINTER_SCHEMA,load_pointer
ROOT=Path(__file__).resolve().parents[1];SERVING_ROOT=ROOT/"backend/app/data/pse_valuation_catalogs";DEFAULT_CANDIDATE_ROOT=ROOT/"output/pse-valuation-candidates/phase-b-batch-05-candidate-a";CATALOG_VERSION="PSE-V2-PHASE-B-B05-2026-09-23-1.0";CONFIRMED_MANIFEST_SHA256="b6dc2ae35ad13e0ee2f40c11e0b7190441da651acf914e90fea3334302ece95b";PREVIOUS_CATALOG_VERSION="PSE-V2-PHASE-B-B04-2026-09-22-1.0"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(root):return {p.relative_to(root):sha(p) for p in root.rglob("*") if p.is_file()}
def write_pointer(path,value):
 raw=json.dumps(value,indent=2,sort_keys=True).encode()+b"\n";tmp=path.with_suffix(path.suffix+".tmp");tmp.write_bytes(raw);tmp.replace(path)
def activate(candidate_root:Path=DEFAULT_CANDIDATE_ROOT):
 candidate_root=candidate_root.resolve();catalog=candidate_root/CATALOG_VERSION;manifest=catalog/"manifest.json"
 if sha(manifest)!=CONFIRMED_MANIFEST_SHA256:raise RuntimeError("candidate manifest does not match confirmed Batch 5")
 staged=json.loads((candidate_root/"staged.json").read_text())
 if staged.get("schema_version")!=POINTER_SCHEMA or staged.get("catalog_version")!=CATALOG_VERSION or staged.get("manifest_sha256")!=CONFIRMED_MANIFEST_SHA256:raise RuntimeError("invalid staged pointer")
 before=json.loads((SERVING_ROOT/"active.json").read_text())
 if before.get("catalog_version") not in {PREVIOUS_CATALOG_VERSION,CATALOG_VERSION}:raise RuntimeError("unexpected active catalog")
 if not (SERVING_ROOT/PREVIOUS_CATALOG_VERSION/"manifest.json").is_file():raise RuntimeError("rollback catalog missing")
 destination=SERVING_ROOT/CATALOG_VERSION
 if destination.exists():
  if tree(destination)!=tree(catalog):raise RuntimeError("existing Batch 5 differs")
 else:shutil.copytree(catalog,destination)
 write_pointer(SERVING_ROOT/"staged.json",{**staged,"status":"staged"});write_pointer(SERVING_ROOT/"active.json",{**staged,"status":"active"});active=load_pointer(SERVING_ROOT,"active.json")
 if active.version!=CATALOG_VERSION or active.status!="active" or len(active.entries)!=58:raise RuntimeError("activation validation failed")
 return {"previous_catalog_version":before["catalog_version"],"active_catalog_version":active.version,"artifact_count":len(active.entries),"manifest_sha256":active.manifest_sha256,"rollback_catalog_preserved":True}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--candidate-root",type=Path,default=DEFAULT_CANDIDATE_ROOT);a=p.parse_args();print(activate(a.candidate_root))
