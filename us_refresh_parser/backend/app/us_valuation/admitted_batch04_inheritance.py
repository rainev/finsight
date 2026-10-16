"""Closed future B04 local-admission proof; validation never grants release."""

from pathlib import Path

from .staged_batch04_inheritance import (
    IDENTITIES,
    NULLS,
    PARENT_REGISTRY_SHA,
    PARENT_SHA,
    PARENT_VERSION,
    ROOT_FILES,
    TARGETS,
    validate as validate_stage,
)


SCHEMA = "US-B04-LOCAL-ADMISSION-INHERITANCE-1"
STAGE_SHA = "7e2a54aea529e3617e77c520c86ff14f01a8621966a580006a1bf07ea854fa9b"
CONFIRMATION_SHA = "0419c797064c2c00cf7a22b255b46a8bcdfe8407ee1d36e088b0db7d25d09989"
PREPARATION_SHA = "b67d1bade798dff82035178c08005b87459873d98c3178a305fbf5cf1d7b86e1"
STAGE_REGISTRY_SHA = "e535546fb4244e00c757cb422b32ad600c63ec215f84ee218de2181f39ea6872"
POLICIES_SHA = "bc98af7595f96ee7956d2335d9b9d6359abf816d682dcad75980b8889c3e2075"
CUTOFF = "2026-10-06"
REVIEW_SCHEMA = "US-B04-READ-ONLY-STAGED-REVIEW-1"
AUTH_SCHEMA = "US-B04-EXPLICIT-LOCAL-RELEASE-AUTHORIZATION-1"
READINESS_SCHEMA = "US-B04-ADMISSION-READINESS-HANDOFF-1"
PREPARATION_SCHEMA = "US-B04-ADMISSION-READINESS-PREPARATION-AUTHORIZATION-1"
CONFIRMATION_SCHEMA = "US-B04-STAGED-CANDIDATE-CONFIRMATION-1"
EXTRA_FILES = {
    "local-admission-stage.json",
    "local-admission-confirmation.json",
    "local-admission-preparation.json",
    "local-admission-authorization.json",
    "local-admission-readiness.json",
}
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


def require(value, why):
    if not value:
        raise ValueError("Batch04 local admission rejected: " + why)


def _rows(manifest):
    return {
        entry["ticker"]: (
            entry["cik"],
            entry["batch"],
            entry["availability_type"],
            entry["artifact_sha256"],
        )
        for entry in manifest["entries"]
    }


def validate(root, manifest, *, deep=False, proof_reader=None):
    """Validate an immutable B04 successor without changing any live state."""
    require(callable(proof_reader), "verified proof reader missing")
    grant = manifest.get("local_admission")
    proof = manifest.get("approved_base_inheritance")
    require(
        isinstance(grant, dict)
        and set(grant) == {"schema_version", "authorization_sha256", "readiness_sha256"}
        and grant.get("schema_version") == "US-B04-LOCAL-ADMISSION-1",
        "separate B04 local grant required",
    )
    require(
        isinstance(proof, dict)
        and proof == {
            "schema_version": SCHEMA,
            "confirmed_stage_manifest_sha256": STAGE_SHA,
            "stage_confirmation_sha256": CONFIRMATION_SHA,
            "readiness_preparation_sha256": PREPARATION_SHA,
        },
        "exact B04 stage/confirmation/preparation pins",
    )

    stage = proof_reader(root, "local-admission-stage.json", STAGE_SHA)
    confirmation = proof_reader(root, "local-admission-confirmation.json", CONFIRMATION_SHA)
    preparation = proof_reader(root, "local-admission-preparation.json", PREPARATION_SHA)
    authorization = proof_reader(root, "local-admission-authorization.json", grant["authorization_sha256"])
    readiness = proof_reader(root, "local-admission-readiness.json", grant["readiness_sha256"])

    require(
        confirmation.get("schema_version") == CONFIRMATION_SCHEMA
        and confirmation.get("manifest_sha256") == STAGE_SHA
        and confirmation.get("confirmed_scope") == "sealed_staged_public_candidate_only"
        and confirmation.get("all_values_holds_and_BSET_source_gate_preserved") is True
        and all(confirmation.get(key) is False for key in ("admission", "activation", "publication")),
        "staged confirmation is not read-only",
    )
    require(
        preparation.get("schema_version") == PREPARATION_SCHEMA
        and preparation.get("readiness_preparation_authorized") is True
        and preparation.get("stage_confirmation_sha256") == CONFIRMATION_SHA
        and preparation.get("confirmed_staged_manifest_sha256") == STAGE_SHA
        and preparation.get("candidate_count") == 540
        and preparation.get("baseline_count") == 530
        and preparation.get("evidence_cutoff") == CUTOFF
        and all(preparation.get(key) is False for key in ("admission", "activation", "publication"))
        and all(preparation.get(key) is False for key in PREPARATION_DENIED),
        "readiness preparation scope widened",
    )
    require(
        set(authorization) == AUTH_FIELDS
        and authorization.get("schema_version") == AUTH_SCHEMA
        and authorization.get("authorization_source") == "direct_human_user"
        and isinstance(authorization.get("user_request"), str)
        and authorization["user_request"].strip()
        and all(
            authorization.get(key) is True
            for key in (
                "admission_authorized",
                "local_activation_authorized",
                "local_public_visibility_authorized",
            )
        )
        and all(authorization.get(key) is False for key in FALSE_AUTH),
        "future local authority is not exact or contains prohibited permission",
    )
    require(
        authorization.get("confirmed_stage_manifest_sha256") == STAGE_SHA
        and authorization.get("readiness_sha256") == grant["readiness_sha256"]
        and authorization.get("readiness_preparation_sha256") == PREPARATION_SHA
        and authorization.get("stage_confirmation_sha256") == CONFIRMATION_SHA
        and authorization.get("active_parent_manifest_sha256") == PARENT_SHA
        and set(authorization.get("public_numeric_additions", [])) == TARGETS
        and set(authorization.get("public_null_additions", [])) == NULLS
        and authorization.get("new_filing_holds") == 10
        and authorization.get("evidence_cutoff") == CUTOFF
        and authorization.get("staged_registry_sha256") == STAGE_REGISTRY_SHA
        and authorization.get("refresh_policy_sha256") == POLICIES_SHA,
        "future local authority does not bind exact B04 scope",
    )
    require(
        readiness.get("schema_version") == READINESS_SCHEMA
        and readiness.get("status") == "verified_pending_single_admission_local_activation_decision"
        and readiness.get("manifest_sha256") == STAGE_SHA
        and readiness.get("live_count") == 530
        and readiness.get("candidate_count") == 540
        and readiness.get("public_numeric_count") == 498
        and readiness.get("public_null_count") == 42
        and readiness.get("new_declared_filing_holds") == 10
        and readiness.get("new_auto_revaluation_ready") == 0
        and readiness.get("approved_values_and_holds_preserved") is True
        and all(readiness.get(key) is False for key in ("admission", "activation", "publication"))
        and all(readiness.get(key) is False for key in READINESS_DENIED),
        "readiness handoff is not verified/read-only",
    )
    require(
        readiness.get("confirmation_sha256") == CONFIRMATION_SHA
        and readiness.get("preparation_sha256") == PREPARATION_SHA
        and readiness.get("staged_registry_sha256") == STAGE_REGISTRY_SHA
        and readiness.get("refresh_policy_sha256") == POLICIES_SHA,
        "readiness handoff proof pins changed",
    )

    originals = validate_stage(root, stage, deep=False, proof_reader=proof_reader)
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
    require(set(manifest) == set(stage) | {"local_admission"}, "future admitted metadata membership changed")
    require(
        all(manifest[key] == value for key, value in stage.items() if key not in changed),
        "stage economics/metadata changed",
    )
    require(
        str(manifest.get("catalog_version", "")).startswith("US-ADMITTED-B04-540-")
        and manifest.get("catalog_kind") == "admitted_local_expansion"
        and manifest.get("staged_release_only") is False
        and manifest.get("admission_prepared_only") is False
        and manifest.get("staged_read_only_review_ready") is False
        and manifest.get("admission") is True
        and manifest.get("activation") is False
        and manifest.get("publication") is False,
        "future admitted baseline scope is not local-only",
    )
    require(
        manifest.get("base_manifest_sha256") == PARENT_SHA
        and manifest.get("base_catalog_version") == PARENT_VERSION,
        "future parent changed",
    )
    preserved = {
        **stage["preserved_prior_estimate_sha256"],
        "local-admission-stage.json": STAGE_SHA,
        "local-admission-confirmation.json": CONFIRMATION_SHA,
        "local-admission-preparation.json": PREPARATION_SHA,
        "local-admission-authorization.json": grant["authorization_sha256"],
        "local-admission-readiness.json": grant["readiness_sha256"],
    }
    require(manifest.get("preserved_prior_estimate_sha256") == preserved, "future proof index changed")
    if deep:
        require(
            {path.name for path in Path(root).iterdir()}
            == ROOT_FILES | EXTRA_FILES | {"artifacts", "recipes"},
            "future admitted root allowlist changed",
        )
        for name, digest in preserved.items():
            proof_reader(root, name, digest)
        require(
            {path.name for path in (Path(root) / "artifacts").iterdir()}
            == {entry["ticker"] + ".json" for entry in stage["entries"]},
            "future artifact membership changed",
        )
        for entry in stage["entries"]:
            proof_reader(root, "artifacts/" + entry["ticker"] + ".json", entry["artifact_sha256"])
        require(
            {path.name for path in (Path(root) / "recipes").iterdir()}
            == {ticker + ".json" for ticker in stage["private_recipe_sha256"]},
            "future recipe membership changed",
        )
        for ticker, digest in stage["private_recipe_sha256"].items():
            proof_reader(root, "recipes/" + ticker + ".json", digest)
    return originals


def validate_registry(root, manifest, registry, *, proof_reader=None):
    require(callable(proof_reader), "verified proof reader missing")
    parent = proof_reader(root, "approved-parent-registry.json", PARENT_REGISTRY_SHA)
    require(
        registry.get("schema_version") == parent.get("schema_version")
        and len(registry.get("entries", [])) == 540,
        "future registry540 schema",
    )
    require(all(row in registry["entries"] for row in parent["entries"]), "future old530 registry records changed")
    actual = {
        (entry["ticker"], entry["cik"], entry["batch"], entry["availability_type"])
        for entry in registry["entries"]
    }
    wanted = {
        (entry["ticker"], entry["cik"], entry["batch"], entry["availability_type"])
        for entry in manifest["entries"]
    }
    require(len(actual) == 540 and actual == wanted, "future registry identities/statuses")
