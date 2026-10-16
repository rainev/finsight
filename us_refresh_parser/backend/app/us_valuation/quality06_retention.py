"""Offline, status-only retention child for the approved Quality06 stage.

This module intentionally has no source capture, valuation, activation, or
publication path.  It retains the complete 650-entry parent and records only
the frozen filing-hold outcomes for the 25 target issuers.
"""

from collections import Counter
import ctypes
import errno
from pathlib import Path
import os
import shutil
import sys

from . import quality06_staged as stage


SCHEMA = "US-QUALITY06-OFFLINE-RETENTION-CHILD-1"
ALLOWED = {"checked_unchanged", "prior_unavailable", "held_new_filing"}
REIT_POLICY_TARGETS = frozenset("ARE DLR EQIX PLD WELL".split())
require, canonical, sha = stage.require, stage.canonical, stage.sha


def _name(suffix: str) -> str:
    return f"quality06-refresh-{suffix}.json"


def _clone_copy(source, destination):
    """Copy one retained file with APFS clonefile; never fall back to a full copy."""
    if sys.platform != "darwin":
        raise OSError(errno.EXDEV, "Quality06 retention requires same-volume clonefile support")
    library = ctypes.CDLL(None, use_errno=True)
    clonefile = library.clonefile
    clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    clonefile.restype = ctypes.c_int
    if clonefile(os.fsencode(source), os.fsencode(destination), 0):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(destination))
    return str(destination)


def reader(proof_reader):
    def wrapped(root, name, digest):
        return proof_reader(root, _name("stage") if name == "manifest.json" else name, digest)
    return wrapped


def _scope_guard():
    require(len(stage.TARGETS) == 25, "exact Quality06 target scope")
    require(len(stage.CARRY_FORWARD) == 25, "exact Quality06 carry-forward scope")
    require(len(stage.HELD) == 23 and len(stage.PRIVATE_ONLY) == 1 and len(stage.CONTROLS) == 1,
            "exact Quality06 carry/held/private/control lanes")
    require(stage.PRIVATE_ONLY == {"APO"} and stage.CONTROLS == {"BEN"},
            "Quality06 APO/BEN lanes")


def _policy_overlay(root, anchors, proof_reader):
    """Allow only the five new target REIT filing-hold policy records."""
    policies = stage.proof(root, "refresh-policies.json", anchors["policies_sha256"], proof_reader)
    prior = stage.proof(root, "approved-parent-policies.json", anchors["parent_policies_sha256"], proof_reader)
    require(set(prior) <= set(policies), "Quality06 policy membership shrank")
    added = set(policies) - set(prior)
    require(added == REIT_POLICY_TARGETS, "only five target REIT policies may be added")
    for ticker in added:
        policy = policies[ticker]
        require(policy.get("schema_version") == "FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1",
                ticker + " explicit REIT hold schema")
        require(policy.get("ticker") == ticker
                and policy.get("new_filing_hold_before_capture") is True
                and policy.get("auto_revaluation") is False
                and policy.get("public_release_authorized") is False
                and policy.get("admission_authorized") is False
                and policy.get("activation_authorized") is False
                and policy.get("publication_authorized") is False,
                ticker + " source-hold policy")
    for ticker in set(prior) & set(policies):
        # Stage validation authenticates the exact revised policy for all 25
        # target issuers.  Only non-target policy bytes must carry forward
        # unchanged; the five newly added policies remain REIT-only above.
        if ticker not in stage.TARGETS:
            require(policies[ticker] == prior[ticker], ticker + " non-target policy changed")


def validate(root, manifest, *, deep=False, proof_reader=None):
    """Validate a Q06 child without granting a new source cycle or release."""
    _scope_guard()
    anchors = stage.anchors()
    parent = stage.proof(root, _name("stage"), anchors["manifest_sha256"], proof_reader)
    grant = stage.proof(root, _name("authorization"), anchors["approval_sha256"], proof_reader)
    require(grant.get("staged_candidate_only") is True
            and all(grant.get(key) is False for key in stage.DENIED),
            "offline child authority is not release")
    require(manifest["approved_base_inheritance"] == {
        "schema_version": SCHEMA,
        "quality_stage_manifest_sha256": anchors["manifest_sha256"],
        "authorization_sha256": anchors["approval_sha256"],
    }, "exact child ancestry")
    require(manifest["catalog_kind"] == "quality06_offline_verification_retention_child"
            and manifest["staged_release_only"] is True
            and manifest["staged_read_only_review_ready"] is False
            and manifest["admission_prepared_only"] is False,
            "offline-only child")
    require(all(manifest[key] is False for key in ("admission", "activation", "publication")),
            "child release flags")
    require(manifest["refresh_parent_catalog_version"] == parent["catalog_version"]
            and manifest["refresh_parent_manifest_sha256"] == anchors["manifest_sha256"],
            "immediate refresh parent")
    require(manifest["base_catalog_version"] == parent["base_catalog_version"]
            and manifest["base_manifest_sha256"] == parent["base_manifest_sha256"],
            "approved parent distinct from refresh parent")
    mutable = {
        "catalog_version", "valuation_date", "publication_counts", "refresh_status",
        "refresh_cutoff", "input_fingerprints", "preserved_prior_estimate_sha256",
        "refresh_parent_catalog_version", "refresh_parent_manifest_sha256",
        "approved_base_inheritance", "catalog_kind", "staged_release_only",
        "staged_read_only_review_ready", "admission_prepared_only",
        "quality06_retention_receipt_sha256",
    }
    require(set(manifest) <= set(parent) | mutable
            and all(manifest[key] == value for key, value in parent.items() if key not in mutable),
            "child economic/policy/source mutation")
    original = stage.validate(root, parent, deep=False, proof_reader=reader(proof_reader))
    _policy_overlay(root, anchors, proof_reader)
    receipt = stage.proof(root, _name("status"), manifest["quality06_retention_receipt_sha256"], proof_reader)
    require(receipt["schema_version"] == "US-QUALITY06-OFFLINE-RETENTION-STATUS-1"
            and receipt["base_manifest_sha256"] == anchors["manifest_sha256"]
            and receipt["active_changed"] is False
            and receipt["source_bound_recalculations"] == 0
            and receipt["offline_verification_only"] is True
            and receipt["auto_revaluation"] is False
            and receipt["new_filing_policy"] == "hold_before_capture",
            "status receipt")
    rows = receipt["rows"]
    tickers = {row["ticker"] for row in rows}
    require(len(rows) == len(tickers) == 650 and tickers == {entry["ticker"] for entry in parent["entries"]},
            "all650 outcomes")
    require(set(row["outcome"] for row in rows) <= ALLOWED
            and dict(Counter(row["outcome"] for row in rows)) == receipt["counts"],
            "no recalculations")
    require(set(manifest["refresh_status"]) == tickers, "complete status mapping")
    for row in rows:
        status = manifest["refresh_status"][row["ticker"]]
        require(status["outcome"] == row["outcome"]
                and status["checked_as_of"] == receipt["cutoff"], "status accounting")
        if row["ticker"] in stage.HELD:
            require(status.get("private_quality_hold") is True
                    and status.get("private_quality_hold_preserved") is True
                    and row.get("private_quality_hold") is True,
                    row["ticker"] + " private quality hold preservation")
        if row["ticker"] in stage.TARGETS and row.get("latest_accession") != row.get("prior_accession"):
            require(row["outcome"] == "held_new_filing", "changed target outside filing hold")
        if row["ticker"] in stage.CARRY_FORWARD:
            require(row.get("outcome") in {"checked_unchanged", "prior_unavailable", "held_new_filing"},
                    "carry-forward status")
    # The retention child intentionally adds its three status/authority files;
    # the staged validator's deep root-filename check is for the parent only.
    # Child leaf bytes and inherited recipes are already authenticated above.
    return original


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader):
    validate(root, manifest, deep=False, proof_reader=proof_reader)
    parent = stage.proof(root, _name("stage"), stage.anchors()["manifest_sha256"], proof_reader)
    return stage.preserved_parent_artifact(root, parent, ticker, raw, proof_reader=reader(proof_reader))


def consumer_disclosures(root, manifest, artifact, payload, *, proof_reader):
    """Route inherited out-of-scope rows through the Q05 admission chain."""
    ticker = artifact["issuer"]["ticker"]
    if ticker not in stage.TARGETS | stage.CARRY_FORWARD:
        from .quality05_admission import consumer_disclosures as q05_consumer
        parent = stage.proof(root, "approved-parent-manifest.json",
                             stage.anchors()["parent_manifest_sha256"], proof_reader)
        return q05_consumer(Path(root) / "prior-catalog", parent, artifact, payload,
                            proof_reader=proof_reader)
    from .quality06_disclosures import consumer_disclosures as q06_consumer
    return q06_consumer(root, manifest, artifact, payload, proof_reader=proof_reader)


def assemble(active, manifest, destination, rows, cutoff, *, copy_function=None):
    """Build the status-only child in an isolated offline test environment."""
    require(os.environ.get("APP_ENV") == "test", "offline verification environment")
    _scope_guard()
    anchors = stage.anchors()
    require(active.manifest_sha256 == anchors["manifest_sha256"]
            and not any(row["outcome"] == "source_bound" for row in rows),
            "compiled baseline and no new valuations")
    copier = copy_function or _clone_copy
    destination = Path(destination)
    for name in stage.ROOT_FILES - {"manifest.json", "artifacts", "recipes", "refresh-policies.json"}:
        source, target = active.root / name, destination / name
        if source.is_dir():
            shutil.copytree(source, target, copy_function=copier)
        else:
            copier(source, target)
    for name, source, pin in (
        (_name("stage"), active.root / "manifest.json", anchors["manifest_sha256"]),
        (_name("authorization"), active.root / "quality-scope-authorization.json", anchors["approval_sha256"]),
    ):
        raw = source.read_bytes()
        require(sha(raw) == pin, "offline child authority bytes")
        (destination / name).write_bytes(raw)
    receipt = {
        "schema_version": "US-QUALITY06-OFFLINE-RETENTION-STATUS-1",
        "base_manifest_sha256": active.manifest_sha256,
        "cutoff": cutoff,
        "rows": rows,
        "counts": dict(Counter(row["outcome"] for row in rows)),
        "active_changed": False,
        "source_bound_recalculations": 0,
        "offline_verification_only": True,
        "auto_revaluation": False,
        "new_filing_policy": "hold_before_capture",
        "new_SEC_capture_or_job": False,
    }
    raw = canonical(receipt)
    (destination / _name("status")).write_bytes(raw)
    manifest.update(
        approved_base_inheritance={"schema_version": SCHEMA,
            "quality_stage_manifest_sha256": anchors["manifest_sha256"],
            "authorization_sha256": anchors["approval_sha256"]},
        base_catalog_version=active.manifest["base_catalog_version"],
        base_manifest_sha256=active.manifest["base_manifest_sha256"],
        refresh_parent_catalog_version=active.catalog_version,
        refresh_parent_manifest_sha256=active.manifest_sha256,
        staged_release_only=True, staged_read_only_review_ready=False,
        admission_prepared_only=False, admission=False, activation=False, publication=False,
        catalog_kind="quality06_offline_verification_retention_child",
        quality06_retention_receipt_sha256=sha(raw),
    )
    manifest["preserved_prior_estimate_sha256"] = {
        str(path.relative_to(destination)): sha(path.read_bytes())
        for path in destination.rglob("*") if path.is_file()
        and not str(path.relative_to(destination)).startswith(("artifacts/", "recipes/"))
    }
