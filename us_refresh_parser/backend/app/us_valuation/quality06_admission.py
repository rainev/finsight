"""Future-only Quality06 readiness and local-release contract.

This module validates an unsigned readiness handoff and a separately scoped
future grant. It never creates a grant, admitted catalog, active pointer, or
runtime job. Q06 remains a staged read-only candidate until a later authority
validates a real grant.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import json
import re

from . import quality06_staged as stage

SCHEMA = "US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1"
AUTH_SCHEMA = "US-QUALITY06-EXPLICIT-LOCAL-RELEASE-1"
ANCHOR_SHA = "fbd7602ab1b11f59d4b8b3dd5e3260b3ac5e87d6c8deca22288eb37f33123404"

# These are copied from the readiness-preparation authority. They are
# preparation denials, not a release grant.
PREPARATION_DENIED = (
    "admission", "activation", "publication",
    "existing_runtime_service_operation",
    "Docker_startup_recreation_build_or_pull",
    "new_SEC_capture_or_job", "new_valuation",
    "policy_economics_change", "new_source_adapter_approval",
    "DB_job_write", "data_deletion", "cloud_deployment", "push",
    "next_batch", "second_recovery_pass", "live_source_integration",
)

# Future authorization remains deliberately explicit about the boundaries
# that a local release must not widen.
FALSE_AUTH = (
    "publication", "cloud_deployment", "push", "new_SEC_capture_or_job",
    "automatic_new_source_revaluation", "source_adapter_integration",
    "new_source_adapter_approval", "new_financial_adapter_approval",
    "source_economics_approval", "DB_job_write", "new_valuation",
    "new_live_refresh_job", "valuation_recalculation", "new_valuation_inputs",
    "policy_economics_change", "second_recovery_pass", "next_batch",
    "data_deletion", "new_financial_data_capture",
    "existing_runtime_service_operation", "Docker_operation",
    "Docker_startup_recreation_build_or_pull", "live_source_integration",
)

AUTH_FIELDS = set(FALSE_AUTH) | {
    "schema_version", "authorization_source", "user_request",
    "admission_authorized", "local_activation_authorized",
    "local_public_visibility_authorized",
    "data_preserving_runtime_recreation_authorized", "runtime_scope",
    "live_source_integration_authorized",
    "source_integration_plan_sha256",
    "prepared_runtime_implementation_sha256",
    "confirmed_stage_manifest_sha256", "stage_handoff_sha256",
    "readiness_sha256", "preparation_sha256", "confirmation_sha256",
    "active_parent_manifest_sha256", "revised_targets",
    "held_updates_carry_prior", "registry_sha256", "policies_sha256",
    "source_binding_sha256", "issuer_cutoffs", "carry_forward_prior_active",
    "private_only_diagnostics", "unchanged_control_tickers",
}
FILES = {
    "quality06-admission-stage.json",
    "quality06-admission-confirmation.json",
    "quality06-admission-preparation.json",
    "quality06-admission-authorization.json",
    "quality06-admission-readiness.json",
}
require, canonical, sha = stage.require, stage.canonical, stage.sha


def _hex(value, label):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
            label + " must be a SHA-256 pin")


def anchors():
    path = Path(__file__).with_name("config") / "quality06_readiness_anchors.json"
    require(path.is_file() and not path.is_symlink(), "readiness compiled anchor")
    raw = path.read_bytes()
    require(sha(raw) == ANCHOR_SHA, "readiness anchor changed")
    value = json.loads(raw)
    require(
        value.get("schema_version") == "US-QUALITY06-ACCEPTED-READINESS-ANCHORS-1"
        and set(value.get("targets", ())) == stage.TARGETS
        and len(value.get("targets", ())) == 25
        and set(value.get("carry_forward", ())) == stage.CARRY_FORWARD
        and len(value.get("carry_forward", ())) == 25
        and set(value.get("held_updates", ())) == stage.HELD
        and len(value.get("held_updates", ())) == 23
        and set(value.get("private_only_diagnostics", ())) == stage.PRIVATE_ONLY
        and set(value.get("unchanged_controls", ())) == stage.CONTROLS
        and value.get("candidate_count") == 650,
        "readiness exact 25/25/23/APO/BEN/650 scope",
    )
    require(set(value.get("issuer_cutoffs", ())) == stage.TARGETS,
            "exact per-issuer cutoffs")
    return deepcopy(value)


def _scope(value, *, grant=False):
    a = anchors()
    require(set(value.get("revised_targets", ())) == stage.TARGETS,
            "exact revised target scope")
    require(set(value.get("held_updates_carry_prior", ())) == stage.HELD,
            "exact held-update scope")
    require(set(value.get("carry_forward_prior_active", ())) == stage.CARRY_FORWARD,
            "exact carry-forward scope")
    require(set(value.get("private_only_diagnostics", ())) == stage.PRIVATE_ONLY,
            "exact private-only scope")
    require(set(value.get("unchanged_control_tickers", ())) == stage.CONTROLS,
            "exact unchanged-control scope")
    require(set(value.get("issuer_cutoffs", ())) == stage.TARGETS,
            "exact cutoff scope")
    require(len(value.get("revised_targets", ())) == 25
            and len(value.get("held_updates_carry_prior", ())) == 23
            and len(value.get("carry_forward_prior_active", ())) == 25
            and len(value.get("private_only_diagnostics", ())) == 1
            and len(value.get("unchanged_control_tickers", ())) == 1,
            "exact Q06 lane counts")
    if grant:
        require(value.get("confirmed_stage_manifest_sha256") == a["stage_manifest_sha256"]
                and value.get("stage_handoff_sha256") == a["stage_handoff_sha256"]
                and value.get("preparation_sha256") == a["preparation_sha256"]
                and value.get("confirmation_sha256") == a["confirmation_sha256"]
                and value.get("active_parent_manifest_sha256") == a["active_parent_manifest_sha256"]
                and value.get("registry_sha256") == a["registry_sha256"]
                and value.get("policies_sha256") == a["policies_sha256"]
                and value.get("source_binding_sha256") == a["binding_sha256"],
                "future grant exact evidence ancestry")


def check_authorization(value, *, readiness_sha, readiness=None):
    """Validate a future grant in memory; this does not issue or persist it."""
    a = anchors()
    require(set(value) == AUTH_FIELDS, "exact future grant fields")
    require(
        value.get("schema_version") == AUTH_SCHEMA
        and value.get("authorization_source") == "direct_human_user"
        and isinstance(value.get("user_request"), str)
        and value["user_request"].strip(),
        "explicit future human release authority",
    )
    require(all(value.get(key) is True for key in (
        "admission_authorized", "local_activation_authorized",
        "local_public_visibility_authorized",
    )), "release not expressly authorized")
    runtime = value.get("data_preserving_runtime_recreation_authorized")
    require(type(runtime) is bool, "explicit separate runtime authority")
    require(value.get("runtime_scope") == (
        "data_preserving_backend_worker_recreation_only" if runtime else "none"
    ), "runtime authority is narrowly scoped")
    require(value.get("live_source_integration_authorized") is True,
            "future source integration must be separately authorized")
    for key in FALSE_AUTH:
        require(value.get(key) is False, "future grant widens scope: " + key)
    _hex(readiness_sha, "readiness_sha256")
    require(value.get("readiness_sha256") == readiness_sha,
            "readiness receipt hash")
    _hex(value.get("source_integration_plan_sha256"), "source_integration_plan_sha256")
    _hex(value.get("prepared_runtime_implementation_sha256"),
         "prepared_runtime_implementation_sha256")
    if readiness is not None:
        require(value["source_integration_plan_sha256"]
                == readiness.get("source_integration_plan_sha256")
                and value["prepared_runtime_implementation_sha256"]
                == readiness.get("prepared_runtime_implementation_sha256"),
                "future grant integration pins differ from readiness")
    _scope(value, grant=True)
    return True


def validate_confirmation(value):
    a = anchors()
    require(value.get("schema_version")
            == "US-QUALITY06-STAGED-RESULT-CONFIRMATION-1"
            and value.get("confirmed_scope")
            == "sealed_quality06_staged_candidate_only"
            and value.get("manifest_sha256") == a["stage_manifest_sha256"]
            and value.get("handoff_sha256") == a["stage_handoff_sha256"]
            and all(value.get(key) is False for key in
                    ("admission", "activation", "publication")),
            "stage confirmation is not release authority")
    return True


def validate_preparation(value):
    a = anchors()
    require(value.get("schema_version")
            == "US-QUALITY06-READINESS-PREPARATION-1"
            and value.get("readiness_preparation_authorized") is True
            and value.get("confirmed_stage_manifest_sha256")
            == a["stage_manifest_sha256"],
            "readiness preparation ancestry")
    require(all(value.get(key) is False for key in PREPARATION_DENIED),
            "readiness preparation widened scope")
    require(value.get("prepared_code_integration_plan_review_authorized") is True,
            "prepared integration plan was not authorized")
    return True


def validate_readiness_receipt(value):
    """Validate a verified, unsigned readiness handoff only."""
    a = anchors()
    require(value.get("schema_version") == "US-QUALITY06-READINESS-HANDOFF-1"
            and value.get("status")
            == "verified_pending_single_local_admission_activation_decision",
            "verified Q06 readiness status")
    expected = {
        "manifest_sha256": a["stage_manifest_sha256"],
        "stage_handoff_sha256": a["stage_handoff_sha256"],
        "confirmation_sha256": a["confirmation_sha256"],
        "preparation_sha256": a["preparation_sha256"],
        "active_parent_manifest_sha256": a["active_parent_manifest_sha256"],
        "registry_sha256": a["registry_sha256"],
        "policies_sha256": a["policies_sha256"],
        "source_binding_sha256": a["binding_sha256"],
    }
    require(all(value.get(key) == pin for key, pin in expected.items()),
            "readiness evidence ancestry")
    require(
        value.get("candidate_count") == 650
        and value.get("numeric_count") == 572
        and value.get("unavailable_count") == 78
        and value.get("revised_count") == 25
        and value.get("reviewed_carry_forward_count") == 25
        and value.get("held_update_carry_forward_count") == 23
        and value.get("private_only_diagnostic_count") == 1
        and value.get("unchanged_control_count") == 1,
        "readiness exact counts",
    )
    require(value.get("existing_refresh_support_and_policy_epochs_preserved") is True
            and value.get("fresh_successful_post_authorization_precommit_required") is True
            and value.get("real_admitted_ACTIVE_and_child_verification_pending_separate_authority") is True
            and value.get("no_real_grant_or_admitted_snapshot_created") is True,
            "readiness safety gates")
    require(all(value.get(key) is False for key in (
        "admission", "activation", "publication",
        "live_source_integration_authorized",
    )), "readiness permission flags")
    require(set(value.get("issuer_cutoffs", ())) == stage.TARGETS,
            "readiness issuer cutoffs")
    _hex(value.get("source_integration_plan_sha256"),
         "source_integration_plan_sha256")
    _hex(value.get("prepared_runtime_implementation_sha256"),
         "prepared_runtime_implementation_sha256")
    receipts = value.get("verification_receipts")
    require(isinstance(receipts, dict), "readiness proof receipts")
    base = {"http_main", "http_worktree", "offline_workers",
            "entrypoint_refusals"}
    require(base <= set(receipts), "four required readiness proof pins")
    require(any("consumer" in key for key in receipts)
            and any("runtime" in key for key in receipts),
            "consumer/runtime readiness proof pins")
    require(all(isinstance(pin, str) and re.fullmatch(r"[0-9a-f]{64}", pin)
                for pin in receipts.values()), "readiness proof pin format")
    return True


def validate_readiness(*, manifest, readiness, confirmation=None,
                       preparation=None):
    """Validate staged metadata and readiness; never creates an admitted tree."""
    require(isinstance(manifest, dict) and "local_admission" not in manifest,
            "readiness cannot contain a local grant")
    require(manifest.get("approved_base_inheritance", {}).get("schema_version")
            == stage.SCHEMA
            and manifest.get("catalog_kind")
            == "unadmitted_quality06_public_candidate"
            and manifest.get("admission") is False
            and manifest.get("activation") is False
            and manifest.get("publication") is False,
            "readiness must remain a staged candidate")
    if confirmation is not None:
        validate_confirmation(confirmation)
    if preparation is not None:
        validate_preparation(preparation)
    validate_readiness_receipt(readiness)
    _scope(readiness)
    return deepcopy(manifest)


def reader(proof_reader):
    """Remap the admitted proof reader to the frozen Q06 stage manifest."""
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader.remap_manifest("quality06-admission-stage.json")

    def wrapped(root, name, digest):
        return proof_reader(
            root,
            "quality06-admission-stage.json"
            if name == "manifest.json" else name,
            digest,
        )
    return wrapped


def validate_frozen_semantics(root, frozen, proof_reader):
    require(callable(proof_reader), "verified frozen-stage proof reader required")
    # The stage validator authenticates the exact immutable stage manifest and
    # all Q06 ancestry through the remapped reader. It does not read an
    # arbitrary path or trust a caller-supplied parsed object.
    stage.validate(root, frozen, deep=False, proof_reader=reader(proof_reader))


def _metadata_uncached(root, manifest, *, proof_reader):
    require(callable(proof_reader), "verified future-admission proof reader")
    a = anchors()
    grant = manifest.get("local_admission")
    require(
        isinstance(grant, dict)
        and set(grant) == {
            "schema_version", "authorization_sha256", "readiness_sha256",
        }
        and grant.get("schema_version") == AUTH_SCHEMA,
        "separate exact Quality06 grant required",
    )
    _hex(grant["authorization_sha256"], "authorization_sha256")
    _hex(grant["readiness_sha256"], "readiness_sha256")

    frozen = stage.proof(
        root, "quality06-admission-stage.json",
        a["stage_manifest_sha256"], proof_reader,
    )
    confirmation = stage.proof(
        root, "quality06-admission-confirmation.json",
        a["confirmation_sha256"], proof_reader,
    )
    preparation = stage.proof(
        root, "quality06-admission-preparation.json",
        a["preparation_sha256"], proof_reader,
    )
    authorization = stage.proof(
        root, "quality06-admission-authorization.json",
        grant["authorization_sha256"], proof_reader,
    )
    readiness = stage.proof(
        root, "quality06-admission-readiness.json",
        grant["readiness_sha256"], proof_reader,
    )
    check_authorization(
        authorization,
        readiness_sha=grant["readiness_sha256"],
        readiness=readiness,
    )
    validate_confirmation(confirmation)
    validate_preparation(preparation)
    validate_readiness_receipt(readiness)
    _scope(readiness)

    require(
        confirmation.get("manifest_sha256") == a["stage_manifest_sha256"]
        and confirmation.get("handoff_sha256") == a["stage_handoff_sha256"]
        and all(confirmation.get(key) is False for key in
                ("admission", "activation", "publication")),
        "confirmation is not release authority",
    )
    require(
        preparation.get("confirmed_stage_manifest_sha256")
        == a["stage_manifest_sha256"]
        and preparation.get("stage_confirmation_sha256")
        == a["confirmation_sha256"]
        and all(preparation.get(key) is False
                for key in PREPARATION_DENIED),
        "readiness preparation widened scope",
    )
    require(
        readiness.get("source_integration_plan_sha256")
        == authorization.get("source_integration_plan_sha256")
        and readiness.get("prepared_runtime_implementation_sha256")
        == authorization.get("prepared_runtime_implementation_sha256"),
        "future integration pins differ from readiness",
    )
    validate_frozen_semantics(root, frozen, proof_reader)

    mutable = {
        "catalog_version", "catalog_kind", "staged_release_only",
        "staged_read_only_review_ready", "admission_prepared_only",
        "admission", "activation", "publication",
        "approved_base_inheritance", "local_admission",
    }
    require(
        set(manifest) == set(frozen) | {"local_admission"}
        and all(manifest[key] == value
                for key, value in frozen.items() if key not in mutable),
        "admission changed frozen economics/source/holds",
    )
    require(
        manifest.get("approved_base_inheritance") == {
            "schema_version": SCHEMA,
            "confirmed_stage_manifest_sha256": a["stage_manifest_sha256"],
            "confirmation_sha256": a["confirmation_sha256"],
            "preparation_sha256": a["preparation_sha256"],
        },
        "exact Q06 admitted lineage",
    )
    require(
        str(manifest.get("catalog_version", "")).startswith(
            "US-ADMITTED-QUALITY06-650-"
        )
        and manifest.get("catalog_kind") == "admitted_local_quality06_revision"
        and manifest.get("admission") is True
        and all(manifest.get(key) is False for key in (
            "staged_release_only", "staged_read_only_review_ready",
            "admission_prepared_only", "activation", "publication",
        )),
        "local-only Q06 admission metadata",
    )

    binding = stage.proof(
        root, "quality-source-binding.json", a["binding_sha256"], proof_reader,
    )
    policies = stage.proof(
        root, "refresh-policies.json", a["policies_sha256"], proof_reader,
    )
    old_policies = stage.proof(
        root, "approved-parent-policies.json",
        stage.anchors()["parent_policies_sha256"], proof_reader,
    )
    for ticker in stage.TARGETS:
        record = binding["records"][ticker]
        epoch = a["issuer_cutoffs"][ticker]
        require(
            epoch == record.get("proposed_evidence_cutoff")
            == record.get("proposed_public_valuation_date")
            == record.get("proposed_review_hold_epoch")
            == policies[ticker].get("source_epoch"),
            ticker + " exact issuer epoch",
        )
        old = old_policies.get(ticker, {})
        if old.get("source_epoch") is not None:
            require(old["source_epoch"] == epoch,
                    ticker + " inherited epoch changed",
            )

    return frozen


@lru_cache(maxsize=4)
def _metadata_bytes(files, manifest_bytes):
    # Semantic results depend only on freshly authenticated immutable bytes.
    # Never retain mutable decoded authority or cache by path/mtime.
    indexed = {name: (pin, raw) for name, pin, raw in files}

    def memory(root, name, pin):
        expected, raw = indexed[name]
        require(expected == pin, "immutable admission proof pin")
        return json.loads(raw)

    frozen = _metadata_uncached(
        Path("."), json.loads(manifest_bytes), proof_reader=memory,
    )
    return canonical(frozen)


def metadata(root, manifest, *, proof_reader):
    from .approved_inheritance import _proof as authenticated_reader
    from .read_path_snapshot import SnapshotProofReader
    require(callable(proof_reader), "authenticated proof reader required")
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader.metadata_for(
            root, manifest,
            lambda: metadata(
                root, manifest, proof_reader=authenticated_reader,
            ),
        )
    from .approved_inheritance import _file
    if proof_reader is not authenticated_reader:
        return _metadata_uncached(root, manifest, proof_reader=proof_reader)
    a, sa = anchors(), stage.anchors()
    grant = manifest.get("local_admission")
    require(isinstance(grant, dict)
            and set(grant) == {"schema_version", "authorization_sha256", "readiness_sha256"}
            and grant["schema_version"] == AUTH_SCHEMA,
            "separate exact Quality06 grant required")
    _hex(grant["authorization_sha256"], "authorization_sha256")
    _hex(grant["readiness_sha256"], "readiness_sha256")
    pins = {
        "quality06-admission-stage.json": a["stage_manifest_sha256"],
        "quality06-admission-confirmation.json": a["confirmation_sha256"],
        "quality06-admission-preparation.json": a["preparation_sha256"],
        "quality06-admission-authorization.json": grant["authorization_sha256"],
        "quality06-admission-readiness.json": grant["readiness_sha256"],
        "approved-parent-manifest.json": sa["parent_manifest_sha256"],
        "quality-scope-authorization.json": sa["approval_sha256"],
        "quality-source-binding.json": sa["binding_sha256"],
        "quality-private-confirmation.json": sa["confirmation_sha256"],
        "quality-eligibility-proposal.json": sa["proposal_sha256"],
        "quality-eligibility-verification.json": sa["eligibility_sha256"],
        "refresh-policies.json": sa["policies_sha256"],
        "approved-parent-policies.json": sa["parent_policies_sha256"],
    }
    files = []
    for name, pin in sorted(pins.items()):
        raw = _file(root, name)
        require(sha(raw) == pin, "current admission proof bytes: " + name)
        files.append((name, pin, raw))
    require(json.loads(_file(root, "manifest.json")) == manifest,
            "current admitted manifest object changed")
    return json.loads(_metadata_bytes(tuple(files), canonical(manifest)))


def validate(root, manifest, *, deep=False, proof_reader=None,
             readiness=None, confirmation=None, preparation=None):
    # Readiness-only callers must use validate_readiness directly. The native
    # metadata/validate path is intentionally reserved for an actual grant.
    require(callable(proof_reader), "authenticated proof reader required")
    frozen = metadata(root, manifest, proof_reader=proof_reader)
    if deep:
        require(
            {path.name for path in Path(root).iterdir()}
            == stage.ROOT_FILES | FILES,
            "exact Q06 admitted root filenames",
        )
        require(
            {path.name for path in (Path(root) / "artifacts").iterdir()}
            == {entry["ticker"] + ".json" for entry in frozen["entries"]},
            "Q06 admitted artifact membership",
        )
        require(
            {path.name for path in (Path(root) / "recipes").iterdir()}
            == {ticker + ".json"
                for ticker in frozen["private_recipe_sha256"]},
            "Q06 admitted recipe membership",
        )
        for entry in frozen["entries"]:
            stage.proof(
                root, "artifacts/" + entry["ticker"] + ".json",
                entry["artifact_sha256"], proof_reader,
            )
        for ticker, digest in frozen["private_recipe_sha256"].items():
            stage.proof(root, "recipes/" + ticker + ".json",
                        digest, proof_reader)
        binding = stage.proof(
            root, "quality-source-binding.json", anchors()["binding_sha256"],
            proof_reader,
        )
        for ticker in stage.TARGETS:
            entry = next(entry for entry in frozen["entries"]
                         if entry["ticker"] == ticker)
            stage.target(
                root, frozen, ticker, binding["records"][ticker], entry,
                reader(proof_reader),
            )
        parent = stage.proof(
            root, "approved-parent-manifest.json",
            stage.anchors()["parent_manifest_sha256"], proof_reader,
        )
        from .approved_inheritance import validate_inheritance
        validate_inheritance(
            Path(root) / "prior-catalog", parent, deep=True,
        )
    return {
        entry["ticker"]: entry for entry in frozen["entries"]
        if entry["ticker"] not in stage.TARGETS
    }


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader):
    frozen = metadata(root, manifest, proof_reader=proof_reader)
    entry = next(
        (row for row in frozen["entries"] if row.get("ticker") == ticker),
        None,
    )
    require(entry is not None and sha(raw) == entry["artifact_sha256"],
            "admitted parent artifact identity")
    if ticker in stage.TARGETS:
        binding = stage.proof(
            root, "quality-source-binding.json",
            anchors()["binding_sha256"], proof_reader,
        )
        stage.target(
            root, frozen, ticker, binding["records"][ticker], entry,
            reader(proof_reader),
        )
        return False
    return True


def consumer_disclosures(root, manifest, artifact, payload, *, proof_reader):
    frozen = metadata(root, manifest, proof_reader=proof_reader)
    ticker = artifact["issuer"]["ticker"]
    if ticker not in stage.TARGETS | stage.CARRY_FORWARD:
        from .quality05_admission import consumer_disclosures
        parent = stage.proof(
            root, "approved-parent-manifest.json",
            stage.anchors()["parent_manifest_sha256"], proof_reader,
        )
        return consumer_disclosures(
            Path(root) / "prior-catalog", parent, artifact, payload,
            proof_reader=proof_reader,
        )
    from .quality06_disclosures import consumer_disclosures
    result = consumer_disclosures(
        root, frozen, artifact, payload, proof_reader=reader(proof_reader),
    )
    scope = result.pop("staged_scope")
    for key in ("admission", "activation", "publication", "read_only"):
        scope.pop(key, None)
    scope.update(
        schema_version=SCHEMA,
        local_admission_authorized=True,
        local_public_visibility_authorized=True,
        cloud_publication_authorized=False,
    )
    result["admitted_scope"] = scope
    result.setdefault("warnings", []).append(
        "Inactive stage-origin wording remains historical provenance; "
        "explicit local admission permits only this dated estimate, not "
        "cloud publication, new-filing support, or economic calibration."
    )
    return result
