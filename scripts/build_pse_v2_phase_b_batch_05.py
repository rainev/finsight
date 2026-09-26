#!/usr/bin/env python3
"""Build a staged cumulative 58-issuer Batch 5 candidate without activation."""

from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from app.pse_valuation.catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from app.pse_valuation.phase_b_batch_05 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt

ROOT=Path(__file__).resolve().parents[1]
SERVING_ROOT=ROOT/"backend/app/data/pse_valuation_catalogs"
ACTIVE_POINTER=SERVING_ROOT/"active.json"
DEFAULT_OUTPUT_ROOT=ROOT/"output/pse-valuation-candidates/phase-b-batch-05-candidate-a"
PARENT_CATALOG_VERSION="PSE-V2-PHASE-B-B04-2026-09-22-1.0"
PARENT_MANIFEST_SHA256="29673524d381211947d1518cc31720320fcbbe60d0a88f5b005040808f248588"
CATALOG_VERSION="PSE-V2-PHASE-B-B05-2026-09-23-1.0"

def _sha256(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def _write_json(path:Path,value:dict)->bytes:
 raw=json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False).encode()+b"\n";path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);return raw
def _active_snapshot():
 pointer_raw=ACTIVE_POINTER.read_bytes();pointer=json.loads(pointer_raw)
 if pointer.get("status")!="active" or pointer.get("catalog_version") not in {PARENT_CATALOG_VERSION,CATALOG_VERSION,"PSE-V2-PHASE-B-B06-2026-09-23-1.0","PSE-V2-PHASE-B-B07-2026-09-23-1.0","PSE-V2-PHASE-B-B08-2026-09-23-1.0","PSE-V2-PHASE-B-B09-2026-09-23-1.0","PSE-V2-PHASE-B-B10-2026-09-23-1.0","PSE-V2-PHASE-B-B11-2026-09-23-1.0","PSE-V2-PHASE-B-B12-2026-09-23-1.0","PSE-V2-PHASE-B-B13-2026-09-23-1.0","PSE-V2-PHASE-B-B14-2026-09-23-1.0","PSE-V2-PHASE-B-B15-2026-09-23-1.0", "PSE-V2-PHASE-B-B16-2026-09-25-1.0", "PSE-V2-PHASE-B-B17-2026-09-25-1.0", "PSE-V2-PHASE-B-B18-2026-09-25-1.0", "PSE-V2-PHASE-B-B19-2026-09-25-1.0", "PSE-V2-PHASE-B-B20-2026-09-25-1.0", "PSE-V2-PHASE-B-B21-2026-09-25-1.0", "PSE-V2-PHASE-B-B22-2026-09-25-1.0", "PSE-V2-PHASE-B-B23-2026-09-25-1.0", "PSE-V2-PHASE-B-B24-2026-09-25-1.0", "PSE-V2-PHASE-B-B25-2026-09-25-1.0", "PSE-V2-PHASE-B-B26-2026-09-25-1.0", "PSE-V2-PHASE-B-B27-2026-09-25-1.0", "PSE-V2-PHASE-B-B28-2026-09-26-1.0"}:raise RuntimeError("unexpected active catalog while reproducing Phase B Batch 5")
 active_root=SERVING_ROOT/pointer["catalog_path"];manifest_raw=(active_root/"manifest.json").read_bytes();parent_root=SERVING_ROOT/PARENT_CATALOG_VERSION;parent_raw=(parent_root/"manifest.json").read_bytes()
 if _sha256(parent_raw)!=PARENT_MANIFEST_SHA256:raise RuntimeError("confirmed Batch 4 parent manifest hash differs")
 parent=json.loads(parent_raw)
 if parent.get("artifact_count")!=48:raise RuntimeError("confirmed Batch 4 parent catalog must contain 48 artifacts")
 return pointer_raw,manifest_raw,parent_root,parent
def build(output_root:Path=DEFAULT_OUTPUT_ROOT)->Path:
 output_root=output_root.resolve()
 if output_root==SERVING_ROOT.resolve() or SERVING_ROOT.resolve() in output_root.parents:raise RuntimeError("Phase B candidates must remain outside serving root")
 pointer_before,manifest_before,parent_root,parent_manifest=_active_snapshot();config=load_batch_config();batch=build_batch_artifacts(config);catalog_root=output_root/config["catalog_version"];artifacts_root=catalog_root/"artifacts";evidence_root=catalog_root/"evidence";entries=[]
 parent_entries={r["ticker"]:r for r in parent_manifest["entries"]}
 if set(parent_entries)&set(FROZEN_BATCH_TICKERS):raise RuntimeError("Batch 5 overlaps parent catalog")
 for ticker in sorted(parent_entries):
  raw=(parent_root/"artifacts"/f"{ticker}.json").read_bytes()
  if _sha256(raw)!=parent_entries[ticker]["artifact_sha256"]:raise RuntimeError(f"{ticker}: parent digest mismatch")
  target=artifacts_root/f"{ticker}.json";target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);entries.append(dict(parent_entries[ticker]))
 for ticker in FROZEN_BATCH_TICKERS:
  artifact=batch[ticker];reference,receipt_raw=source_receipt(ticker,config);receipt=evidence_root/f"{ticker}.json";receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_bytes(receipt_raw)
  if _sha256(receipt_raw)!=reference["sha256"]:raise RuntimeError(f"{ticker}: receipt digest mismatch")
  raw=_write_json(artifacts_root/f"{ticker}.json",artifact.model_dump(mode="json"));entries.append({"ticker":ticker,"availability_type":artifact.availability_type,"publication_state":artifact.publication_state,"primary_model":artifact.primary_model,"artifact_sha256":_sha256(raw),"source_audit":f"PSE-V2-PHASE-B-B05-{ticker}-SOURCE-1.0"})
 entries.sort(key=lambda r:r["ticker"]);expected=sorted([*parent_entries,*FROZEN_BATCH_TICKERS])
 if len(entries)!=58 or [r["ticker"] for r in entries]!=expected:raise RuntimeError("candidate must contain exact active-48 plus frozen-10")
 availability={k:0 for k in ("intrinsic_valuation","market_relative_only","not_available")};publication={k:0 for k in ("approved","provisional","blocked")}
 for e in entries:availability[e["availability_type"]]+=1;publication[e["publication_state"]]+=1
 manifest={"schema_version":CATALOG_SCHEMA,"catalog_version":config["catalog_version"],"universe_version":config["universe_version"],"valuation_date":config["valuation_date"],"catalog_status":"staged","artifact_count":len(entries),"availability_counts":availability,"publication_counts":publication,"batch":{"batch_version":config["batch_version"],"frozen_tickers":list(FROZEN_BATCH_TICKERS),"active_parent_catalog":parent_manifest["catalog_version"],"active_parent_manifest_sha256":PARENT_MANIFEST_SHA256},"entries":entries}
 manifest_raw=_write_json(catalog_root/"manifest.json",manifest);_write_json(output_root/"staged.json",{"schema_version":POINTER_SCHEMA,"status":"staged","catalog_version":config["catalog_version"],"catalog_path":config["catalog_version"],"manifest_sha256":_sha256(manifest_raw)})
 candidate=load_pointer(output_root)
 if candidate.status!="staged" or len(candidate.entries)!=58:raise RuntimeError("candidate validation failed")
 pointer_after,manifest_after,_,_=_active_snapshot()
 if pointer_after!=pointer_before or manifest_after!=manifest_before:raise RuntimeError("active catalog changed during build")
 return catalog_root
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=DEFAULT_OUTPUT_ROOT);args=p.parse_args();print(build(args.output))
if __name__=="__main__":main()
