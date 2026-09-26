#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,shutil
from pathlib import Path
from app.pse_valuation.catalog import POINTER_SCHEMA,load_pointer
ROOT=Path(__file__).resolve().parents[1];SERVING_ROOT=ROOT/"backend/app/data/pse_valuation_catalogs";DEFAULT_CANDIDATE_ROOT=ROOT/"output/pse-valuation-candidates/phase-b-batch-10-candidate-a";CATALOG_VERSION="PSE-V2-PHASE-B-B10-2026-09-23-1.0";CONFIRMED_MANIFEST_SHA256="d835ccf5a75b9728a76e7a01f89a7fcc1054e06cf7564070f3f9c1973dbd5018";PREVIOUS_CATALOG_VERSION="PSE-V2-PHASE-B-B09-2026-09-23-1.0"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(r):return {p.relative_to(r):sha(p) for p in r.rglob("*") if p.is_file()}
def wp(p,v):raw=json.dumps(v,indent=2,sort_keys=True).encode()+b"\n";t=p.with_suffix(p.suffix+".tmp");t.write_bytes(raw);t.replace(p)
def activate(root=DEFAULT_CANDIDATE_ROOT):
 root=Path(root).resolve();catalog=root/CATALOG_VERSION;manifest=catalog/"manifest.json"
 if sha(manifest)!=CONFIRMED_MANIFEST_SHA256:raise RuntimeError("unconfirmed candidate")
 staged=json.loads((root/"staged.json").read_text())
 if staged.get("schema_version")!=POINTER_SCHEMA or staged.get("catalog_version")!=CATALOG_VERSION or staged.get("manifest_sha256")!=CONFIRMED_MANIFEST_SHA256:raise RuntimeError("invalid pointer")
 before=json.loads((SERVING_ROOT/"active.json").read_text())
 if before.get("catalog_version") not in {PREVIOUS_CATALOG_VERSION,CATALOG_VERSION}:raise RuntimeError("unexpected active")
 prev=SERVING_ROOT/PREVIOUS_CATALOG_VERSION
 if not (prev/"manifest.json").is_file():raise RuntimeError("rollback missing")
 dest=SERVING_ROOT/CATALOG_VERSION
 if dest.exists():
  if tree(dest)!=tree(catalog):raise RuntimeError("existing catalog differs")
 else:shutil.copytree(catalog,dest)
 wp(SERVING_ROOT/"staged.json",{**staged,"status":"staged"});wp(SERVING_ROOT/"active.json",{**staged,"status":"active"});active=load_pointer(SERVING_ROOT,"active.json")
 if active.version!=CATALOG_VERSION or len(active.entries)!=108:raise RuntimeError("activation failed")
 return {"previous":before["catalog_version"],"active":active.version,"count":108,"manifest_sha256":active.manifest_sha256,"rollback_preserved":True}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--candidate-root",type=Path,default=DEFAULT_CANDIDATE_ROOT);a=p.parse_args();print(activate(a.candidate_root))
