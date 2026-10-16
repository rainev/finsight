"""Inactive, byte-retaining refresh children of a real quality-admitted baseline."""
from collections import Counter
from pathlib import Path
import shutil
from . import quality_batches1115_admission as admission
from .quality_batches1115_retention import anchors,require,sha,canonical
from .quality_batches1115_staged import TARGETS

SCHEMA="US-B1115-QUALITY-ADMITTED-RETENTION-CHILD-1"
ROOT_FILES={"manifest.json","artifacts","recipes","refresh-policies.json","admission-parent","quality-admitted-refresh-parent.json","quality-admitted-refresh-status.json"}

def validate(root,manifest,*,deep=False,proof_reader=None):
    require(callable(proof_reader),"verified proof reader required");a=anchors();proof=manifest.get("approved_base_inheritance",{})
    require(set(proof)=={"schema_version","admitted_parent_manifest_sha256","quality_stage_manifest_sha256","authorization_sha256","readiness_sha256"} and proof["schema_version"]==SCHEMA,"admitted child exact proof")
    require(proof["quality_stage_manifest_sha256"]==a["stage_manifest_sha256"],"quality stage ancestry")
    parent=proof_reader(root,"quality-admitted-refresh-parent.json",proof["admitted_parent_manifest_sha256"])
    nested=Path(root)/"admission-parent"
    require(proof_reader(nested,"manifest.json",proof["admitted_parent_manifest_sha256"])==parent,"retained admitted parent")
    originals=admission.validate(nested,parent,deep=deep,proof_reader=proof_reader)
    require(parent["local_admission"]["authorization_sha256"]==proof["authorization_sha256"]
        and parent["local_admission"]["readiness_sha256"]==proof["readiness_sha256"],"real admission grant ancestry")
    require(manifest["refresh_parent_catalog_version"]==parent["catalog_version"]
        and manifest["refresh_parent_manifest_sha256"]==proof["admitted_parent_manifest_sha256"],"immediate admitted refresh parent")
    require(manifest["base_catalog_version"]==parent["base_catalog_version"] and manifest["base_manifest_sha256"]==parent["base_manifest_sha256"],"original approval parent")
    require(manifest["staged_release_only"] is True and manifest["admission_prepared_only"] is True
        and manifest["staged_read_only_review_ready"] is False and manifest["catalog_kind"]=="unadmitted_quality_admitted_retention_child","child not inactive")
    require(all(manifest[k] is False for k in ("admission","activation","publication")) and "local_admission" not in manifest,"baseline grant leaked into child")
    mutable={"catalog_version","valuation_date","base_catalog_version","base_manifest_sha256","publication_counts","refresh_status","refresh_cutoff","input_fingerprints",
        "preserved_prior_estimate_sha256","refresh_parent_catalog_version","refresh_parent_manifest_sha256","approved_base_inheritance",
        "catalog_kind","staged_release_only","staged_read_only_review_ready","admission_prepared_only","admission","local_admission","quality_retention_receipt_sha256"}
    require(set(manifest)==(set(parent)-{"local_admission"})|{"refresh_parent_catalog_version","refresh_parent_manifest_sha256","refresh_cutoff","quality_retention_receipt_sha256"},"child fields")
    require(all(manifest[k]==v for k,v in parent.items() if k not in mutable),"admitted child source/value/policy/membership changed")
    receipt=proof_reader(root,"quality-admitted-refresh-status.json",manifest["quality_retention_receipt_sha256"])
    rows=receipt["rows"];require(receipt["parent_manifest_sha256"]==proof["admitted_parent_manifest_sha256"] and receipt["active_changed"] is False,"status ancestry")
    require(receipt["cutoff"]==manifest["refresh_cutoff"] and len(rows)==650 and len({r["ticker"] for r in rows})==650
        and {r["ticker"] for r in rows}=={e["ticker"] for e in parent["entries"]},"status exact650")
    require(dict(Counter(r["outcome"] for r in rows))==receipt["counts"] and set(r["outcome"] for r in rows)<={"checked_unchanged","prior_unavailable","held_new_filing"},"retention outcomes")
    for r in rows:
        t=r["ticker"];s=manifest["refresh_status"][t]
        require(s["outcome"]==r["outcome"] and s["checked_as_of"]==receipt["cutoff"],"status mismatch")
        if t in a["scope_tickers"] and r.get("latest_accession")!=r.get("prior_accession"):require(r["outcome"]=="held_new_filing","issuer filing hold moved")
        if t in {"CBT","UTMD"}:require(s["financial_reference_date"]=="2026-06-30" and s["current_post_event_value_held"],"dated/current hold lost")
    if deep:
        require({p.name for p in Path(root).iterdir()}==ROOT_FILES,"child root membership")
        expected={str(p.relative_to(root)):sha(p.read_bytes()) for p in Path(root).rglob("*") if p.is_file()
            and p!=Path(root)/"manifest.json" and not str(p.relative_to(root)).startswith(("artifacts/","recipes/"))}
        require(manifest["preserved_prior_estimate_sha256"]==expected,"child proof index")
        for e in parent["entries"]:proof_reader(root,"artifacts/"+e["ticker"]+".json",e["artifact_sha256"])
        for t,d in parent["private_recipe_sha256"].items():proof_reader(root,"recipes/"+t+".json",d)
    return originals

def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader):
    validate(root,manifest,proof_reader=proof_reader)
    proof=manifest["approved_base_inheritance"]
    parent=proof_reader(root,"quality-admitted-refresh-parent.json",proof["admitted_parent_manifest_sha256"])
    return admission.preserved_parent_artifact(Path(root)/"admission-parent",parent,ticker,raw,proof_reader=proof_reader)

def assemble(active,manifest,destination,rows,cutoff,*,copy_function=None):
    require(active.manifest["approved_base_inheritance"]["schema_version"]==admission.SCHEMA,"quality-admitted baseline required")
    from .approved_inheritance import _proof
    admission.validate(active.root,active.manifest,deep=True,proof_reader=_proof)
    require(not any(r["outcome"]=="source_bound" for r in rows),"source-bound updates require separately reviewed changed-child contract")
    copier=copy_function or shutil.copy2;destination=Path(destination)
    shutil.copytree(active.root,destination/"admission-parent",copy_function=copier)
    (destination/"quality-admitted-refresh-parent.json").write_bytes((active.root/"manifest.json").read_bytes())
    receipt={"schema_version":"US-B1115-QUALITY-ADMITTED-RETENTION-STATUS-1","parent_manifest_sha256":active.manifest_sha256,
        "cutoff":cutoff,"counts":dict(sorted(Counter(r["outcome"] for r in rows).items())),"rows":rows,"active_changed":False}
    raw=canonical(receipt);(destination/"quality-admitted-refresh-status.json").write_bytes(raw)
    manifest.pop("local_admission",None)
    manifest.update(approved_base_inheritance={"schema_version":SCHEMA,"admitted_parent_manifest_sha256":active.manifest_sha256,
        "quality_stage_manifest_sha256":anchors()["stage_manifest_sha256"],
        "authorization_sha256":active.manifest["local_admission"]["authorization_sha256"],"readiness_sha256":active.manifest["local_admission"]["readiness_sha256"]},
        base_catalog_version=active.manifest["base_catalog_version"],base_manifest_sha256=active.manifest["base_manifest_sha256"],
        refresh_parent_catalog_version=active.catalog_version,refresh_parent_manifest_sha256=active.manifest_sha256,
        staged_release_only=True,staged_read_only_review_ready=False,admission_prepared_only=True,admission=False,
        catalog_kind="unadmitted_quality_admitted_retention_child",quality_retention_receipt_sha256=sha(raw))
    manifest["preserved_prior_estimate_sha256"]={str(p.relative_to(destination)):sha(p.read_bytes()) for p in destination.rglob("*")
        if p.is_file() and not str(p.relative_to(destination)).startswith(("artifacts/","recipes/"))}
