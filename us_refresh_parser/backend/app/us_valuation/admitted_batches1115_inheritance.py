"""Future-only local admission proof for the B11--B15 public stage.

The validator is intentionally inert until a separately authorized admission
package supplies all proof receipts.  It validates the frozen staged manifest
first and then checks that an admitted manifest changes metadata only.  It
does not create a grant, snapshot, active pointer, source binding, or refresh.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from types import MappingProxyType

from .catalog import canonical_json_bytes, sha256_bytes
from .staged_batches1115_inheritance import (
    ANCHORS as STAGED_ANCHORS,
    EXPECTED_PUBLIC_COUNTS,
    IDENTITIES,
    NULLS,
    TARGETS,
    validate as validate_stage,
    preserved_parent_artifact as validate_stage_leaf,
)


ANCHORS = MappingProxyType({
    "baseline_count": 600,
    "catalog_count": 650,
    "new_filing_holds": 50,
    "parent_manifest_sha256": "5543a20376f0921887a75de00c8a9883e33aeb0bb5ba56628529d678c37f6b27",
    "public_null_count": 78,
    "public_numeric_count": 572,
    "readiness_preparation_sha256": "9b550604ad67d9ff5434c6df54b199829ec0d6d67c141e1b1acd2ea806e25bf9",
    "refresh_policy_sha256": "c189835804d1855094f0b60ceda60dbe504a185d12cc9fad0a60c426463eb7e7",
    "source_cutoff": "2026-10-08",
    "stage_confirmation_sha256": "9f0089cd10df7b06628e0e62c2ac42d79825a1377c40154ebf68dde3c4a87a73",
    "stage_manifest_sha256": "1597c19677457d6d8428f9393b959e3cf7e76f161071db74a9d98e558ebd21c2",
    "stage_version": "US-STAGED-EXPANSION-B11-B15-650-f4b48e827d20830005af6e60",
    "staged_registry_sha256": "9e59dc68924b89979c83ab5574daf1d76613a987ec50d422e25fdac905752eac"
})


SCHEMA = "US-B11-B15-LOCAL-ADMISSION-INHERITANCE-1"
REVIEW_SCHEMA = "US-B11-B15-READ-ONLY-STAGED-REVIEW-1"
AUTH_SCHEMA = "US-B11-B15-EXPLICIT-LOCAL-RELEASE-AUTHORIZATION-1"
READINESS_SCHEMA = "US-B11-B15-ADMISSION-READINESS-HANDOFF-1"
PREPARATION_SCHEMA = "US-B11-B15-ADMISSION-READINESS-PREPARATION-AUTHORIZATION-1"
CONFIRMATION_SCHEMA = "US-B11-B15-STAGED-CANDIDATE-CONFIRMATION-1"
CUTOFF = str(ANCHORS["source_cutoff"])
PARENT_SHA = str(STAGED_ANCHORS["parent_manifest_sha256"])
PARENT_VERSION = str(STAGED_ANCHORS["parent_version"])
STAGE_SHA = str(ANCHORS["stage_manifest_sha256"])
CONFIRMATION_SHA = str(ANCHORS["stage_confirmation_sha256"])
PREPARATION_SHA = str(ANCHORS["readiness_preparation_sha256"])
STAGE_REGISTRY_SHA = str(ANCHORS["staged_registry_sha256"])
POLICIES_SHA = str(ANCHORS["refresh_policy_sha256"])
PUBLIC_NUMERIC_COUNT = 572
PUBLIC_NULL_COUNT = 78
NEW_FILING_HOLDS = 50

FALSE_AUTH = (
    "automatic_new_source_revaluation",
    "new_source_capture",
    "new_recovery",
    "next_batch",
    "cloud_deployment",
    "push",
    "publication",
    "save",
    "source_adapter_integration",
    "DB_job_write",
    "live_SEC_refresh",
    "new_live_refresh_job",
    "new_valuation_inputs",
    "valuation_recalculation",
)
PREPARATION_DENIED = (
    "admission",
    "activation",
    "publication",
    "automatic_new_source_revaluation",
    "new_source_capture",
    "new_recovery",
    "new_valuation_inputs",
    "live_runtime_promotion",
    "new_live_refresh_job",
    "next_batch",
    "cloud_deployment",
    "push",
)
READINESS_DENIED = PREPARATION_DENIED + (
    "save",
    "source_adapter_integration",
    "DB_job_write",
    "live_SEC_refresh",
    "valuation_recalculation",
)
AUTH_FIELDS = set(FALSE_AUTH) | {
    "schema_version",
    "authorization_source",
    "user_request",
    "admission_authorized",
    "local_activation_authorized",
    "local_public_visibility_authorized",
    "confirmed_stage_manifest_sha256",
    "readiness_sha256",
    "readiness_preparation_sha256",
    "stage_confirmation_sha256",
    "active_parent_manifest_sha256",
    "public_numeric_additions",
    "public_null_additions",
    "new_filing_holds",
    "evidence_cutoff",
    "staged_registry_sha256",
    "refresh_policy_sha256",
}
ROOT_FILES = {
    "manifest.json",
    "refresh-policies.json",
    "approved-base-manifest.json",
    "approved-parent-manifest.json",
    "approved-parent-registry.json",
    "approved-parent-policies.json",
    "public-scope-authorization.json",
    "source-disclosure-binding.json",
}
ADMISSION_FILES = {
    "local-admission-stage.json",
    "local-admission-confirmation.json",
    "local-admission-preparation.json",
    "local-admission-authorization.json",
    "local-admission-readiness.json",
}


def require(value: object, why: str) -> None:
    if not value:
        raise ValueError("B11-B15 local admission rejected: " + why)


def _read_anchor(name: str) -> object:
    if name not in ANCHORS:
        raise ValueError("B11-B15 admission anchor missing: " + name)
    return ANCHORS[name]


def _proof(proof_reader, root, name: str, digest: str):
    return proof_reader(root, name, digest)


def _rows(manifest: dict) -> dict[str, dict]:
    return {entry["ticker"]: entry for entry in manifest["entries"]}


def _stage_proof(root, proof_reader) -> dict:
    stage = _proof(proof_reader, root, "local-admission-stage.json", STAGE_SHA)
    require(isinstance(stage, dict), "stage proof is not an object")
    require(stage.get("catalog_version") == ANCHORS["stage_version"], "stage version changed")
    require(sha256_bytes(canonical_json_bytes(stage)) == STAGE_SHA,
            "stage proof canonical hash mismatch")
    return stage


def _validate_confirmation(value: dict) -> None:
    require(value.get("schema_version") == CONFIRMATION_SCHEMA, "stage confirmation schema changed")
    require(value.get("manifest_sha256") == STAGE_SHA
            and value.get("confirmed_scope") == "sealed_staged_public_candidate_only",
            "stage confirmation scope changed")
    require(value.get("all_values_Low_warnings_and_holds_preserved") is True,
            "stage confirmation preservation flag changed")
    require(all(value.get(key) is False for key in ("admission", "activation", "publication")),
            "stage confirmation grants release")


def _validate_preparation(value: dict) -> None:
    require(value.get("schema_version") == PREPARATION_SCHEMA
            and value.get("readiness_preparation_authorized") is True,
            "readiness preparation authorization changed")
    require(value.get("confirmed_staged_manifest_sha256") == STAGE_SHA
            and value.get("stage_confirmation_sha256") == CONFIRMATION_SHA
            and value.get("baseline_count") == 600
            and value.get("candidate_count") == 650
            and value.get("evidence_cutoff") == CUTOFF,
            "readiness preparation pins/counts changed")
    require(all(value.get(key) is False for key in PREPARATION_DENIED),
            "readiness preparation grants prohibited work")


def _validate_readiness(value: dict) -> None:
    require(value.get("schema_version") == READINESS_SCHEMA
            and value.get("status") == "verified_pending_single_admission_local_activation_decision",
            "readiness handoff status/schema changed")
    require(value.get("manifest_sha256") == STAGE_SHA
            and value.get("live_count") == 600
            and value.get("candidate_count") == 650
            and value.get("public_numeric_count") == PUBLIC_NUMERIC_COUNT
            and value.get("public_null_count") == PUBLIC_NULL_COUNT
            and value.get("new_declared_filing_holds") == NEW_FILING_HOLDS
            and value.get("new_auto_revaluation_ready") == 0
            and value.get("approved_values_and_holds_preserved") is True,
            "readiness handoff counts/status changed")
    require(value.get("confirmation_sha256") == CONFIRMATION_SHA
            and value.get("preparation_sha256") == PREPARATION_SHA
            and value.get("staged_registry_sha256") == STAGE_REGISTRY_SHA
            and value.get("refresh_policy_sha256") == POLICIES_SHA,
            "readiness handoff proof pins changed")
    require(all(value.get(key) is False for key in READINESS_DENIED),
            "readiness handoff grants prohibited work")


def _validate_authorization(value: dict, *, readiness_sha: str) -> None:
    require(set(value) == AUTH_FIELDS, "local authorization exact fields changed")
    require(value.get("schema_version") == AUTH_SCHEMA
            and value.get("authorization_source") == "direct_human_user"
            and isinstance(value.get("user_request"), str)
            and value["user_request"].strip(),
            "local authorization source/schema/user request changed")
    require(all(value.get(key) is True for key in (
        "admission_authorized",
        "local_activation_authorized",
        "local_public_visibility_authorized",
    )), "local admission authority is not explicit")
    require(all(value.get(key) is False for key in FALSE_AUTH),
            "local admission authority widened")
    require(value.get("confirmed_stage_manifest_sha256") == STAGE_SHA
            and value.get("readiness_preparation_sha256") == PREPARATION_SHA
            and value.get("stage_confirmation_sha256") == CONFIRMATION_SHA
            and value.get("readiness_sha256") == readiness_sha
            and value.get("active_parent_manifest_sha256") == PARENT_SHA
            and set(value.get("public_numeric_additions", [])) == set(TARGETS)
            and set(value.get("public_null_additions", [])) == set(NULLS)
            and value.get("new_filing_holds") == NEW_FILING_HOLDS
            and value.get("evidence_cutoff") == CUTOFF
            and value.get("staged_registry_sha256") == STAGE_REGISTRY_SHA
            and value.get("refresh_policy_sha256") == POLICIES_SHA,
            "local admission authority does not bind exact B11-B15 scope")


def _validate_metadata_only(stage: dict, manifest: dict) -> None:
    changed = {
        "catalog_version",
        "catalog_kind",
        "staged_release_only",
        "admission_prepared_only",
        "staged_read_only_review_ready",
        "admission",
        "approved_base_inheritance",
        "local_admission",
        "preserved_prior_estimate_sha256",
    }
    require(set(manifest) == set(stage) | {"local_admission"},
            "admitted manifest membership changed")
    require(all(manifest[key] == value for key, value in stage.items() if key not in changed),
            "stage economics/source/rows changed")
    require(str(manifest.get("catalog_version", "")).startswith("US-ADMITTED-B11-B15-650-"),
            "admitted catalog namespace changed")
    require(manifest.get("catalog_kind") == "admitted_local_expansion"
            and manifest.get("staged_release_only") is False
            and manifest.get("admission_prepared_only") is False
            and manifest.get("staged_read_only_review_ready") is False
            and manifest.get("admission") is True
            and manifest.get("activation") is False
            and manifest.get("publication") is False,
            "admitted local-only metadata changed")
    require(manifest.get("private_integration_only") is not True
            and "private_review" not in manifest,
            "private admission privilege leaked")
    stage_rows, current_rows = _rows(stage), _rows(manifest)
    require(len(current_rows) == 650 and current_rows == stage_rows,
            "admitted entries changed")
    require(manifest.get("availability_counts") == EXPECTED_PUBLIC_COUNTS
            and len(manifest.get("private_recipe_sha256", {})) == 572
            and manifest.get("private_recipe_sha256") == stage.get("private_recipe_sha256"),
            "admitted counts/recipes changed")
    require(manifest.get("private_refresh_policy_sha256") == stage.get("private_refresh_policy_sha256"),
            "admitted refresh policy changed")
    expected_preserved = dict(stage.get("preserved_prior_estimate_sha256", {}))
    expected_preserved.update({
        "local-admission-stage.json": STAGE_SHA,
        "local-admission-confirmation.json": CONFIRMATION_SHA,
        "local-admission-preparation.json": PREPARATION_SHA,
        "local-admission-authorization.json": manifest["local_admission"]["authorization_sha256"],
        "local-admission-readiness.json": manifest["local_admission"]["readiness_sha256"],
    })
    require(manifest.get("preserved_prior_estimate_sha256") == expected_preserved,
            "admitted preservation proof index changed")


_VALIDATED: dict[tuple[str, str, tuple[str, ...]], tuple[dict, dict]] = {}


def _validate_admission_metadata(root, manifest: dict, *, proof_reader=None, use_cache=True) -> tuple[dict, dict]:
    require(callable(proof_reader), "verified proof reader missing")
    manifest_sha = sha256_bytes(canonical_json_bytes(manifest))
    grant = manifest.get("local_admission")
    proof = manifest.get("approved_base_inheritance")
    require(isinstance(grant, dict)
            and set(grant) == {"schema_version", "authorization_sha256", "readiness_sha256"}
            and grant.get("schema_version") == "US-B11-B15-LOCAL-ADMISSION-1",
            "separate B11-B15 local grant required")
    require(isinstance(proof, dict)
            and proof == {
                "schema_version": SCHEMA,
                "confirmed_stage_manifest_sha256": STAGE_SHA,
                "stage_confirmation_sha256": CONFIRMATION_SHA,
                "readiness_preparation_sha256": PREPARATION_SHA,
            }, "exact B11-B15 admission proof pins changed")
    stage = _stage_proof(root, proof_reader)
    confirmation = _proof(proof_reader, root, "local-admission-confirmation.json", CONFIRMATION_SHA)
    preparation = _proof(proof_reader, root, "local-admission-preparation.json", PREPARATION_SHA)
    authorization = _proof(proof_reader, root, "local-admission-authorization.json", grant["authorization_sha256"])
    readiness = _proof(proof_reader, root, "local-admission-readiness.json", grant["readiness_sha256"])
    _validate_confirmation(confirmation)
    _validate_preparation(preparation)
    _validate_authorization(authorization, readiness_sha=grant["readiness_sha256"])
    _validate_readiness(readiness)
    # The production reader has just reread and SHA-256 checked each receipt's
    # exact bytes. Re-encoding megabytes of decoded proof for every leaf adds
    # no integrity guarantee. Custom readers retain the content-derived key.
    from .approved_inheritance import _proof as verified_reader
    if proof_reader is verified_reader:
        receipt_digests = (STAGE_SHA, CONFIRMATION_SHA, PREPARATION_SHA,
                           grant["authorization_sha256"], grant["readiness_sha256"])
    else:
        receipt_digests = tuple(
            sha256_bytes(canonical_json_bytes(value))
            for value in (stage, confirmation, preparation, authorization, readiness)
        )
    key = (str(Path(root).resolve()), manifest_sha, receipt_digests)
    if use_cache and key in _VALIDATED:
        cached_stage, cached_originals = _VALIDATED[key]
        return deepcopy(cached_stage), deepcopy(cached_originals)
    # Stage authority remains the leaf authority. Never pass the admitted
    # manifest to the staged validator.
    originals = validate_stage(root, stage, deep=False, proof_reader=proof_reader)
    _validate_metadata_only(stage, manifest)
    if use_cache:
        _VALIDATED[key] = (deepcopy(stage), deepcopy(originals))
    return stage, originals


def validate(root, manifest, *, deep=False, proof_reader=None):
    """Validate a future admitted650 package without creating or activating it."""
    stage, originals = _validate_admission_metadata(root, manifest, proof_reader=proof_reader, use_cache=False)
    if deep:
        require({path.name for path in Path(root).iterdir()}
                == ROOT_FILES | ADMISSION_FILES | {"artifacts", "recipes"},
                "admitted650 root allowlist changed")
        for name, digest in manifest["preserved_prior_estimate_sha256"].items():
            proof_reader(root, name, digest)
        require({path.stem for path in (Path(root) / "artifacts").glob("*.json")}
                == set(_rows(manifest)), "admitted artifact membership changed")
        require({path.stem for path in (Path(root) / "recipes").glob("*.json")}
                == set(manifest["private_recipe_sha256"]), "admitted recipe membership changed")
        for entry in stage["entries"]:
            path = Path(root) / "artifacts" / f"{entry['ticker']}.json"
            require(sha256_bytes(path.read_bytes()) == entry["artifact_sha256"],
                    entry["ticker"] + " admitted artifact bytes changed")
        for ticker, digest in stage["private_recipe_sha256"].items():
            path = Path(root) / "recipes" / f"{ticker}.json"
            require(sha256_bytes(path.read_bytes()) == digest, ticker + " admitted recipe bytes changed")
    return originals


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader=None):
    """Fast leaf check: cache admission metadata, then use staged leaf authority."""
    stage, originals = _validate_admission_metadata(root, manifest, proof_reader=proof_reader)
    require(ticker in _rows(stage), "unknown admitted ticker")
    # This call receives the authenticated frozen stage manifest, never the
    # admitted manifest. It performs the old-parent byte check or new50 leaf.
    result = validate_stage_leaf(root, stage, ticker, raw, proof_reader=proof_reader)
    if ticker in originals:
        require(result is True, "authenticated old parent leaf changed")
        return True
    return False


def consumer_disclosures(root, manifest, artifact, payload, *, proof_reader=None):
    """Future granted readers keep frozen warnings without calling them staged."""
    ticker = artifact.get('ticker', artifact.get('issuer', {}).get('ticker'))
    if ticker not in IDENTITIES:
        return payload  # No B11--B15 disclosure; normal parent leaf checks still apply.
    _validate_admission_metadata(root, manifest, proof_reader=proof_reader)
    from .staged_batches1115_inheritance import consumer_disclosures as staged_disclosures
    result = staged_disclosures(artifact,payload)
    if result is payload:
        return payload
    scope = result.pop('staged_scope')
    scope.pop('admission',None)
    scope.pop('activation',None)
    scope.pop('publication',None)
    scope.update(local_admission_authorized=True,local_public_visibility_authorized=True,
                 cloud_publication_authorized=False)
    result['admitted_scope'] = scope
    return result


def validate_registry(root, manifest, registry, *, proof_reader=None):
    require(callable(proof_reader), "verified proof reader missing")
    parent = proof_reader(root, "approved-parent-registry.json", STAGED_ANCHORS["parent_registry_sha256"])
    require(isinstance(parent, dict) and len(parent.get("entries", [])) == 600,
            "admitted parent registry550 schema")
    rows = registry.get("entries") if isinstance(registry, dict) else None
    require(registry.get("schema_version") == parent.get("schema_version")
            and isinstance(rows, list) and len(rows) == 650,
            "admitted registry600 schema")
    require(all(row in rows for row in parent["entries"]), "admitted old600 registry rows changed")
    actual = {(_row.get("ticker"), _row.get("cik"), _row.get("batch"), _row.get("availability_type")) for _row in rows}
    wanted = {(row["ticker"], row["cik"], row["batch"], row["availability_type"]) for row in manifest["entries"]}
    require(len(actual) == 650 and actual == wanted, "admitted registry identities/statuses changed")
    return registry
