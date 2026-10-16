"""Future-only quality admission contract; no real grant or admitted package here."""
from copy import deepcopy
from pathlib import Path
from . import quality_batches1115_staged as stage
from .quality_batches1115_retention import anchors,canonical,sha,require

SCHEMA="US-B1115-QUALITY-LOCAL-ADMISSION-INHERITANCE-1"
AUTH_SCHEMA="US-B1115-QUALITY-EXPLICIT-LOCAL-RELEASE-1"
FALSE_AUTH=("publication","cloud_deployment","push","new_live_refresh_job","new_source_capture","automatic_new_source_revaluation",
    "source_adapter_integration","DB_job_write","valuation_recalculation","new_valuation_inputs","next_batch","data_deletion")
AUTH_FIELDS=set(FALSE_AUTH)|{"schema_version","authorization_source","user_request","admission_authorized","local_activation_authorized",
    "local_public_visibility_authorized","confirmed_stage_manifest_sha256","readiness_sha256","preparation_sha256","confirmation_sha256",
    "active_parent_manifest_sha256","revised_targets","new_filing_holds","registry_sha256","policies_sha256","evidence_cutoff",
    "data_preserving_runtime_recreation_authorized"}
FILES={"quality-admission-stage.json","quality-admission-confirmation.json","quality-admission-preparation.json",
    "quality-admission-authorization.json","quality-admission-readiness.json"}

def check_authorization(value,*,readiness_sha):
    a=anchors();require(set(value)==AUTH_FIELDS,"quality admission exact authorization fields")
    require(value["schema_version"]==AUTH_SCHEMA and value["authorization_source"]=="direct_human_user"
        and isinstance(value["user_request"],str) and value["user_request"].strip(),"explicit human release authority")
    require(all(value[k] is True for k in ("admission_authorized","local_activation_authorized","local_public_visibility_authorized")),"release not expressly authorized")
    require(type(value["data_preserving_runtime_recreation_authorized"]) is bool,"runtime authority must be separate explicit boolean")
    require(all(value[k] is False for k in FALSE_AUTH),"quality grant widens scope")
    require(value["confirmed_stage_manifest_sha256"]==a["stage_manifest_sha256"] and value["confirmation_sha256"]==a["confirmation_sha256"]
        and value["preparation_sha256"]==a["preparation_sha256"] and value["readiness_sha256"]==readiness_sha
        and value["active_parent_manifest_sha256"]==a["parent_manifest_sha256"],"quality grant ancestry")
    require(set(value["revised_targets"])==stage.TARGETS and len(value["revised_targets"])==25
        and value["new_filing_holds"]==50 and value["registry_sha256"]==a["registry_sha256"]
        and value["policies_sha256"]==a["policies_sha256"] and value["evidence_cutoff"]==a["cutoff"],"quality grant scope/source/runtime pins")

def reader(proof_reader):
    def read(root,name,digest):
        return proof_reader(root,"quality-admission-stage.json" if name=="manifest.json" else name,digest)
    if hasattr(proof_reader, "context_for"):
        read.context_for = proof_reader.context_for
    if hasattr(proof_reader, "metadata_for"):
        read.metadata_for = proof_reader.metadata_for
    return read

def _metadata_uncached(root,manifest,*,proof_reader):
    a=anchors();grant=manifest.get("local_admission")
    require(isinstance(grant,dict) and set(grant)=={"schema_version","authorization_sha256","readiness_sha256"}
        and grant["schema_version"]==AUTH_SCHEMA,"separate quality release grant required")
    frozen=proof_reader(root,"quality-admission-stage.json",a["stage_manifest_sha256"])
    confirmation=proof_reader(root,"quality-admission-confirmation.json",a["confirmation_sha256"])
    preparation=proof_reader(root,"quality-admission-preparation.json",a["preparation_sha256"])
    authorization=proof_reader(root,"quality-admission-authorization.json",grant["authorization_sha256"])
    readiness=proof_reader(root,"quality-admission-readiness.json",grant["readiness_sha256"])
    check_authorization(authorization,readiness_sha=grant["readiness_sha256"])
    require(confirmation["confirmed_scope"]=="sealed_quality_staged_candidate_only" and all(confirmation[k] is False for k in ("admission","activation","publication")),"confirmation is not release")
    require(preparation["readiness_preparation_authorized"] is True and all(preparation[k] is False for k in ("admission","activation","publication","new_source_capture","new_live_refresh_job")),"preparation is not release")
    require(readiness["schema_version"]=="US-B1115-QUALITY-READINESS-HANDOFF-1" and readiness["status"]=="verified_pending_single_quality_admission_local_activation_decision" and readiness["manifest_sha256"]==a["stage_manifest_sha256"]
        and readiness["confirmation_sha256"]==a["confirmation_sha256"] and readiness["preparation_sha256"]==a["preparation_sha256"]
        and readiness["registry_sha256"]==a["registry_sha256"] and readiness["policies_sha256"]==a["policies_sha256"]
        and readiness["updated_count"]==25 and readiness["carried_forward_count"]==625
        and readiness["new_filing_holds"]==50 and all(readiness[k] is False for k in ("admission","activation","publication")),"readiness receipt scope")
    mutable={"catalog_version","catalog_kind","staged_release_only","staged_read_only_review_ready","admission_prepared_only","admission","approved_base_inheritance","local_admission"}
    require(set(manifest)==set(frozen)|{"local_admission"} and all(manifest[k]==v for k,v in frozen.items() if k not in mutable),"admission changed source/economics/holds")
    require(manifest["approved_base_inheritance"]=={"schema_version":SCHEMA,"confirmed_stage_manifest_sha256":a["stage_manifest_sha256"],
        "confirmation_sha256":a["confirmation_sha256"],"preparation_sha256":a["preparation_sha256"]},"admitted proof pins")
    require(manifest["catalog_version"].startswith("US-ADMITTED-B1115-QUALITY-650-") and manifest["catalog_kind"]=="admitted_local_quality_revision"
        and manifest["admission"] is True and manifest["staged_release_only"] is False
        and manifest["staged_read_only_review_ready"] is False and manifest["admission_prepared_only"] is False
        and manifest["activation"] is False and manifest["publication"] is False,"local-only admission metadata")
    stage.validate(root,frozen,deep=False,proof_reader=reader(proof_reader))
    return frozen


def metadata(root,manifest,*,proof_reader):
    if hasattr(proof_reader, "metadata_for"):
        return proof_reader.metadata_for(root, manifest, lambda: _metadata_uncached(root, manifest, proof_reader=proof_reader))
    return _metadata_uncached(root, manifest, proof_reader=proof_reader)

def validate(root,manifest,*,deep=False,proof_reader=None):
    require(callable(proof_reader),"verified proof reader required")
    frozen=metadata(root,manifest,proof_reader=proof_reader)
    if deep:
        require({p.name for p in Path(root).iterdir()}==stage.ROOT_FILES|FILES,"quality admitted root files")
        for e in frozen["entries"]:proof_reader(root,"artifacts/"+e["ticker"]+".json",e["artifact_sha256"])
        for t,d in frozen["private_recipe_sha256"].items():proof_reader(root,"recipes/"+t+".json",d)
        binding=proof_reader(root,"quality-source-binding.json",anchors()["quality_binding_sha256"])
        for t in stage.TARGETS:stage.target(root,frozen,t,binding["records"][t],next(e for e in frozen["entries"] if e["ticker"]==t),reader(proof_reader))
    return {e["ticker"]:e for e in frozen["entries"] if e["ticker"] not in stage.TARGETS}

def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader):
    frozen=metadata(root,manifest,proof_reader=proof_reader)
    return stage.preserved_parent_artifact(root,frozen,ticker,raw,proof_reader=reader(proof_reader))

def consumer_disclosures(root,manifest,artifact,payload,*,proof_reader):
    if artifact["issuer"]["ticker"] not in anchors()["scope_tickers"]:return payload
    frozen=metadata(root,manifest,proof_reader=proof_reader)
    result=stage.consumer_disclosures(root,frozen,artifact,payload,proof_reader=reader(proof_reader))
    scope=result.pop("staged_scope")
    for k in ("admission","activation","publication"):scope.pop(k,None)
    scope.update(local_admission_authorized=True,local_public_visibility_authorized=True,cloud_publication_authorized=False)
    result["admitted_scope"]=scope
    result["warnings"].append("Frozen stage-origin disclaimers remain historical provenance; explicit local admission permits this dated estimate, not cloud publication, new-filing revaluation or market calibration.")
    return result
