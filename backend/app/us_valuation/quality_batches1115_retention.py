"""Closed offline retention children of the confirmed quality-stage baseline.

A status check is not admission or a new valuation/source-binding approval.
Every artifact and recipe remains the exact frozen baseline byte set.
"""
from collections import Counter
from copy import deepcopy
import hashlib,json,shutil
from pathlib import Path
from . import quality_batches1115_staged as stage

SCHEMA="US-B1115-QUALITY-RETENTION-CHILD-1"
ANCHORS_SHA="cad800633c0e123f323fd786d2682f0078ada5f86daf2be530969a26edd1a670"
EXTRA={"quality-refresh-stage.json","quality-refresh-confirmation.json","quality-refresh-preparation.json","quality-refresh-status-receipt.json"}
ALLOWED_OUTCOMES={"checked_unchanged","prior_unavailable","held_new_filing"}

def require(v,why):
    if not v:raise ValueError("quality retention child rejected: "+why)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return (json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n").encode()

def anchors():
    raw=(Path(__file__).with_name("config")/"quality_b1115_readiness_anchors.json").read_bytes()
    require(sha(raw)==ANCHORS_SHA,"compiled preparation anchor drift")
    return json.loads(raw)

def stage_reader(proof_reader):
    def read(root,name,digest):
        return proof_reader(root,"quality-refresh-stage.json" if name=="manifest.json" else name,digest)
    return read

def validate(root,manifest,*,deep=False,proof_reader=None):
    require(callable(proof_reader),"verified proof reader required");a=anchors()
    parent=proof_reader(root,"quality-refresh-stage.json",a["stage_manifest_sha256"])
    confirmation=proof_reader(root,"quality-refresh-confirmation.json",a["confirmation_sha256"])
    preparation=proof_reader(root,"quality-refresh-preparation.json",a["preparation_sha256"])
    require(confirmation["confirmed_scope"]=="sealed_quality_staged_candidate_only" and confirmation["manifest_sha256"]==a["stage_manifest_sha256"],"confirmation scope")
    require(preparation["readiness_preparation_authorized"] is True and preparation["confirmed_stage_manifest_sha256"]==a["stage_manifest_sha256"],"preparation scope")
    require(all(preparation[k] is False for k in ("admission","activation","publication","new_live_refresh_job","new_source_capture","automatic_new_source_revaluation")),"preparation permits release/source")
    proof=manifest.get("approved_base_inheritance")
    require(proof=={"schema_version":SCHEMA,"quality_stage_manifest_sha256":a["stage_manifest_sha256"],"confirmation_sha256":a["confirmation_sha256"],"preparation_sha256":a["preparation_sha256"]},"exact child proof")
    require(manifest.get("refresh_parent_catalog_version")==parent["catalog_version"] and manifest.get("refresh_parent_manifest_sha256")==a["stage_manifest_sha256"],"refresh parent")
    require(manifest.get("base_catalog_version")==parent["base_catalog_version"] and manifest.get("base_manifest_sha256")==parent["base_manifest_sha256"],"approval parent changed")
    require(manifest.get("catalog_kind")=="unadmitted_quality_retention_child" and manifest.get("staged_release_only") is True and manifest.get("staged_read_only_review_ready") is False and manifest.get("admission_prepared_only") is True,"child stage scope")
    require(all(manifest[k] is False for k in ("admission","activation","publication")) and "local_admission" not in manifest,"child release scope")
    require(str(manifest["catalog_version"]).startswith("US-REFRESH-650-"),"child namespace")
    mutable={"catalog_version","valuation_date","base_catalog_version","base_manifest_sha256","publication_counts","refresh_status","refresh_cutoff","input_fingerprints",
        "preserved_prior_estimate_sha256","refresh_parent_catalog_version","refresh_parent_manifest_sha256","approved_base_inheritance",
        "catalog_kind","staged_release_only","staged_read_only_review_ready","admission_prepared_only","quality_retention_receipt_sha256"}
    require(set(manifest)==set(parent)|{"refresh_parent_catalog_version","refresh_parent_manifest_sha256","refresh_cutoff","quality_retention_receipt_sha256"},"child manifest fields")
    require(all(manifest[k]==v for k,v in parent.items() if k not in mutable),"baseline economics/policy/membership changed")
    wrapped=stage_reader(proof_reader)
    originals=stage.validate(root,parent,deep=False,proof_reader=wrapped)
    receipt=proof_reader(root,"quality-refresh-status-receipt.json",manifest["quality_retention_receipt_sha256"])
    require(receipt["base_manifest_sha256"]==a["stage_manifest_sha256"] and receipt["cutoff"]==manifest["refresh_cutoff"] and receipt["active_changed"] is False,"status receipt ancestry")
    rows=receipt["rows"];require(len(rows)==650 and len({r["ticker"] for r in rows})==650 and {r["ticker"] for r in rows}=={e["ticker"] for e in parent["entries"]},"status exact650")
    require(set(r["outcome"] for r in rows)<=ALLOWED_OUTCOMES and dict(Counter(r["outcome"] for r in rows))==receipt["counts"],"status/hold accounting or recalculation")
    require(set(manifest["refresh_status"])=={r["ticker"] for r in rows},"status membership")
    for r in rows:
        t=r["ticker"];status=manifest["refresh_status"][t]
        require(status["outcome"]==r["outcome"] and status["checked_as_of"]==receipt["cutoff"],"status receipt mismatch")
        require(isinstance(r.get("metadata_sha256"),str) and len(r["metadata_sha256"])==64,"metadata evidence hash")
        if t in a['scope_tickers'] and r.get('latest_accession')!=r.get('prior_accession'):
            require(r['outcome']=='held_new_filing','quality financial change moved outside its issuer hold')
        if t in {"CBT","UTMD"}:require(status["current_post_event_value_held"] is True and status["financial_reference_date"]=="2026-06-30","dated/current hold lost")
    if deep:
        require({p.name for p in Path(root).iterdir()}==stage.ROOT_FILES|EXTRA,"root proof membership")
        expected={str(p.relative_to(root)):sha(p.read_bytes()) for p in Path(root).rglob('*')
            if p.is_file() and p.name!='manifest.json' and not str(p.relative_to(root)).startswith(('artifacts/','recipes/'))}
        # Nested prior manifests are proofs too; only the CURRENT manifest is excluded.
        for p in (Path(root)/'prior-catalog').rglob('manifest.json'):expected[str(p.relative_to(root))]=sha(p.read_bytes())
        require(manifest['preserved_prior_estimate_sha256']==expected,'child proof-preservation index changed')
        for e in parent["entries"]:proof_reader(root,"artifacts/"+e["ticker"]+".json",e["artifact_sha256"])
        for t,d in parent["private_recipe_sha256"].items():proof_reader(root,"recipes/"+t+".json",d)
        for t in stage.TARGETS:
            binding=proof_reader(root,"quality-source-binding.json",a["quality_binding_sha256"])
            stage.target(root,parent,t,binding["records"][t],next(e for e in parent["entries"] if e["ticker"]==t),wrapped)
        from .approved_inheritance import validate_inheritance
        old=proof_reader(root,"approved-parent-manifest.json",a["parent_manifest_sha256"])
        validate_inheritance(Path(root)/"prior-catalog",old,deep=True)
    return originals

def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader):
    validate(root,manifest,deep=False,proof_reader=proof_reader)
    parent=proof_reader(root,"quality-refresh-stage.json",anchors()["stage_manifest_sha256"])
    return stage.preserved_parent_artifact(root,parent,ticker,raw,proof_reader=stage_reader(proof_reader))

def assemble_retention_child(active,manifest,destination,rows,cutoff,*,copy_function=None):
    """Called only by the actual runner after its metadata/per-issuer checks."""
    require(active.manifest.get("approved_base_inheritance",{}).get("schema_version")==stage.SCHEMA,"unsupported baseline")
    a=anchors();require(active.manifest_sha256==a["stage_manifest_sha256"],"compiled baseline")
    require(not any(r["outcome"]=="source_bound" for r in rows),"unadmitted quality rehearsal cannot acquire new valuation authority")
    copier=copy_function or shutil.copy2
    for name in stage.ROOT_FILES-{"manifest.json","artifacts","recipes","refresh-policies.json"}:
        source=active.root/name;target=Path(destination)/name
        if source.is_dir():shutil.copytree(source,target,copy_function=copier)
        else:copier(source,target)
    source=Path(__file__).resolve()
    # Preparation receipts live beside the approved local rehearsal, not arbitrary paths.
    workspace=source.parents[3]
    if workspace.name=="whole-universe-greenlight":workspace=workspace.parent.parent
    phase=workspace/"output/us-b1115-valuation-repair-20261009/quality-admission-readiness"
    staged=workspace/"output/us-b1115-valuation-repair-20261009/public-staged-quality"
    for name,path,d in [("quality-refresh-stage.json",active.root/"manifest.json",a["stage_manifest_sha256"]),
        ("quality-refresh-confirmation.json",staged/"confirmation.json",a["confirmation_sha256"]),
        ("quality-refresh-preparation.json",phase/"authorization.json",a["preparation_sha256"])]:
        raw=path.read_bytes();require(sha(raw)==d,"preparation receipt changed");(Path(destination)/name).write_bytes(raw)
    receipt={"schema_version":"US-B1115-QUALITY-RETENTION-STATUS-1","base_manifest_sha256":active.manifest_sha256,"cutoff":cutoff,
        "counts":dict(sorted(Counter(r["outcome"] for r in rows).items())),"rows":rows,"active_changed":False,"source_bound_recalculations":0}
    raw=canonical(receipt);(Path(destination)/"quality-refresh-status-receipt.json").write_bytes(raw)
    manifest.update(approved_base_inheritance={"schema_version":SCHEMA,"quality_stage_manifest_sha256":a["stage_manifest_sha256"],
        "confirmation_sha256":a["confirmation_sha256"],"preparation_sha256":a["preparation_sha256"]},
        base_catalog_version=active.manifest["base_catalog_version"],base_manifest_sha256=active.manifest["base_manifest_sha256"],
        refresh_parent_catalog_version=active.catalog_version,refresh_parent_manifest_sha256=active.manifest_sha256,
        staged_release_only=True,admission_prepared_only=True,staged_read_only_review_ready=False,
        catalog_kind="unadmitted_quality_retention_child",quality_retention_receipt_sha256=sha(raw))
    manifest["preserved_prior_estimate_sha256"]={str(p.relative_to(destination)):sha(p.read_bytes()) for p in Path(destination).rglob("*")
        if p.is_file() and not str(p.relative_to(destination)).startswith(("artifacts/","recipes/"))}
