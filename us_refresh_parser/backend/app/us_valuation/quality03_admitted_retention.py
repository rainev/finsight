"""Inactive byte-retaining children of a real human-admitted Quality03 parent.

This module is future-only.  It deliberately requires the Q03 admission
contract to have validated a real parent, but it never grants admission,
activation, publication, source capture, or source-bound recalculation.
"""
from collections import Counter
from pathlib import Path
import shutil

from . import quality03_admission as admission
from . import quality03_staged as stage


SCHEMA = "US-QUALITY03-ADMITTED-RETENTION-CHILD-1"
ROOT_FILES = {
    "manifest.json",
    "artifacts",
    "recipes",
    "refresh-policies.json",
    "admission-parent",
    "quality03-admitted-parent.json",
    "quality03-admitted-status.json",
}
ALLOWED = {"checked_unchanged", "prior_unavailable", "held_new_filing"}
LEGACY_NULL_SOURCE_EPOCH = frozenset({"HOOD", "IBKR", "MS", "URI"})
require, canonical, sha = stage.require, stage.canonical, stage.sha


def _source_epoch_contract(root, *, proof_reader):
    """Return and authenticate Q03's mixed per-issuer source epochs."""
    anchors = stage.anchors()
    binding = stage.proof(root, "quality-source-binding.json", anchors["binding_sha256"], proof_reader)
    policies = stage.proof(root, "refresh-policies.json", anchors["policies_sha256"], proof_reader)
    prior_policies = stage.proof(root, "approved-parent-policies.json", anchors["parent_policies_sha256"], proof_reader)
    require(set(binding["records"]) == stage.TARGETS | stage.CARRY_FORWARD, "Q03 binding scope")
    epochs, legacy = {}, set()
    for ticker in stage.TARGETS:
        record = binding["records"][ticker]
        epoch = record["proposed_review_hold_epoch"]
        require(isinstance(epoch, str) and epoch == record["proposed_evidence_cutoff"]
                and epoch == record["proposed_public_valuation_date"], ticker + " mixed source/valuation epoch")
        require(policies[ticker]["source_epoch"] == epoch, ticker + " admitted policy source epoch")
        if prior_policies[ticker].get("source_epoch") is None:
            legacy.add(ticker)
            require(record["source_epoch_is_new_proposal_for_legacy_without_epoch"] is True,
                    ticker + " missing legacy source-epoch witness")
        else:
            require(record["source_epoch_is_new_proposal_for_legacy_without_epoch"] is False,
                    ticker + " incorrectly marked as legacy source-epoch proposal")
            require(prior_policies[ticker]["source_epoch"] == epoch, ticker + " inherited source epoch changed")
        epochs[ticker] = epoch
    require(legacy == set(LEGACY_NULL_SOURCE_EPOCH), "exact four legacy source-epoch proposals")
    return epochs


def _validate_scope(root, *, proof_reader):
    anchors = stage.anchors()
    binding = stage.proof(root, "quality-source-binding.json", anchors["binding_sha256"], proof_reader)
    confirmation = stage.proof(root, "quality-private-confirmation.json", anchors["confirmation_sha256"], proof_reader)
    require(set(binding["carry_forward"]) == stage.CARRY_FORWARD
            and set(binding["private_held_updates"]) == stage.HELD
            and set(binding["private_only_diagnostics"]) == stage.PRIVATE_ONLY, "Q03 carry/held/private-only scope")
    require(len(stage.CARRY_FORWARD) == 42 and len(stage.HELD) == 36
            and len(stage.PRIVATE_ONLY) == 5 and "FAST" in stage.CARRY_FORWARD, "Q03 42/36/5/FAST scope")
    require(set(confirmation["preserved_private_held_updates"]) == stage.HELD
            and confirmation["FAST_unchanged_control_preserved"] is True, "Q03 private hold/FAST confirmation")
    return _source_epoch_contract(root, proof_reader=proof_reader)


def validate(root, manifest, *, deep=False, proof_reader=None):
    require(callable(proof_reader), "verified admitted-child proof reader")
    anchors = stage.anchors()
    lineage = manifest.get("approved_base_inheritance")
    require(isinstance(lineage, dict) and set(lineage) == {
        "schema_version", "admitted_parent_manifest_sha256", "quality_stage_manifest_sha256",
        "authorization_sha256", "readiness_sha256",
    } and lineage["schema_version"] == SCHEMA
        and lineage["quality_stage_manifest_sha256"] == anchors["manifest_sha256"], "exact Q03 admitted-child ancestry")
    parent = stage.proof(root, "quality03-admitted-parent.json", lineage["admitted_parent_manifest_sha256"], proof_reader)
    nested = Path(root) / "admission-parent"
    require(stage.proof(nested, "manifest.json", lineage["admitted_parent_manifest_sha256"], proof_reader) == parent,
            "exact retained actual Q03 admitted parent")
    originals = admission.validate(nested, parent, deep=deep, proof_reader=proof_reader)
    require(parent["local_admission"]["authorization_sha256"] == lineage["authorization_sha256"]
            and parent["local_admission"]["readiness_sha256"] == lineage["readiness_sha256"], "actual human Q03 grant/readiness ancestry")
    require(manifest["refresh_parent_manifest_sha256"] == lineage["admitted_parent_manifest_sha256"]
            and manifest["refresh_parent_catalog_version"] == parent["catalog_version"], "immediate actual Q03 refresh parent")
    require(manifest["base_manifest_sha256"] == parent["base_manifest_sha256"]
            and manifest["base_catalog_version"] == parent["base_catalog_version"], "approved old Q03 parent distinct from refresh parent")
    require(manifest["staged_release_only"] is True and manifest["admission_prepared_only"] is True
            and manifest["staged_read_only_review_ready"] is False
            and manifest["catalog_kind"] == "unadmitted_quality03_admitted_retention_child", "inactive Q03 admitted-child metadata")
    require(all(manifest[key] is False for key in ("admission", "activation", "publication"))
            and "local_admission" not in manifest, "Q03 parent release grant leaked to child")
    mutable = {"catalog_version", "valuation_date", "publication_counts", "refresh_status", "refresh_cutoff",
               "input_fingerprints", "preserved_prior_estimate_sha256", "refresh_parent_catalog_version",
               "refresh_parent_manifest_sha256", "approved_base_inheritance", "catalog_kind", "staged_release_only",
               "staged_read_only_review_ready", "admission_prepared_only", "admission", "local_admission",
               "quality03_admitted_retention_receipt_sha256"}
    require(set(manifest) == (set(parent) - {"local_admission"}) | {
        "refresh_parent_catalog_version", "refresh_parent_manifest_sha256", "refresh_cutoff", "refresh_status",
        "input_fingerprints", "preserved_prior_estimate_sha256", "quality03_admitted_retention_receipt_sha256",
    }, "exact Q03 admitted-child manifest fields")
    require(all(manifest[key] == value for key, value in parent.items() if key not in mutable),
            "Q03 child economics/source/recipe/policy/identity changed")
    epochs = _validate_scope(nested, proof_reader=proof_reader)
    receipt = stage.proof(root, "quality03-admitted-status.json", manifest["quality03_admitted_retention_receipt_sha256"], proof_reader)
    require(receipt["schema_version"] == "US-QUALITY03-ADMITTED-RETENTION-STATUS-1"
            and receipt["parent_manifest_sha256"] == lineage["admitted_parent_manifest_sha256"]
            and receipt["cutoff"] == manifest["refresh_cutoff"] and receipt["active_changed"] is False
            and receipt["source_bound_recalculations"] == 0, "Q03 admitted status parent/no-recalculation authority")
    require(receipt["source_epoch_by_target"] == epochs, "Q03 admitted status source epochs")
    require(receipt["revised_target_count"] == 8 and receipt["carried_forward_count"] == 42
            and receipt["held_update_count"] == 36 and receipt["private_only_diagnostic_count"] == 5
            and receipt["FAST_unchanged"] is True, "Q03 admitted status lane counts")
    rows = receipt["rows"]
    require(len(rows) == len({row["ticker"] for row in rows}) == 650
            and {row["ticker"] for row in rows} == {entry["ticker"] for entry in parent["entries"]}, "all650 Q03 issuer outcomes")
    require(set(row["outcome"] for row in rows) <= ALLOWED
            and dict(Counter(row["outcome"] for row in rows)) == receipt["counts"], "Q03 retention-only outcomes")
    require(set(manifest["refresh_status"]) == {row["ticker"] for row in rows}, "exact Q03 issuer status membership")
    for row in rows:
        ticker, status = row["ticker"], manifest["refresh_status"][row["ticker"]]
        require(status["outcome"] == row["outcome"] and status["checked_as_of"] == receipt["cutoff"], ticker + " status accounting")
        if ticker in stage.TARGETS and row.get("latest_accession") != row.get("prior_accession"):
            require(row["outcome"] == "held_new_filing", ticker + " changed filing escaped its Q03 hold")
        if ticker in {"CBT", "UTMD"}:
            require(status["financial_reference_date"] == "2026-06-30" and status["current_post_event_value_held"] is True,
                    "older dated/current hold lost: " + ticker)
    if deep:
        require({path.name for path in Path(root).iterdir()} == ROOT_FILES, "exact Q03 admitted-child root files")
        require({path.name for path in (Path(root) / "artifacts").iterdir()} == {entry["ticker"] + ".json" for entry in parent["entries"]}, "Q03 child artifact membership")
        require({path.name for path in (Path(root) / "recipes").iterdir()} == {ticker + ".json" for ticker in parent["private_recipe_sha256"]}, "Q03 child recipe membership")
        require((Path(root) / "refresh-policies.json").read_bytes() == (nested / "refresh-policies.json").read_bytes(), "Q03 child exact policy bytes")
        expected = {str(path.relative_to(root)): sha(path.read_bytes()) for path in Path(root).rglob("*") if path.is_file() and path != Path(root) / "manifest.json" and not str(path.relative_to(root)).startswith(("artifacts/", "recipes/"))}
        require(manifest["preserved_prior_estimate_sha256"] == expected, "actual copied Q03 admitted-proof index")
        for entry in parent["entries"]:
            stage.proof(root, "artifacts/" + entry["ticker"] + ".json", entry["artifact_sha256"], proof_reader)
        for ticker, digest in parent["private_recipe_sha256"].items():
            stage.proof(root, "recipes/" + ticker + ".json", digest, proof_reader)
        for ticker in stage.CARRY_FORWARD:
            require((Path(root) / "artifacts" / (ticker + ".json")).read_bytes() == (nested / "artifacts" / (ticker + ".json")).read_bytes(), ticker + " carry-forward artifact changed")
            if ticker in parent["private_recipe_sha256"]:
                require((Path(root) / "recipes" / (ticker + ".json")).read_bytes() == (nested / "recipes" / (ticker + ".json")).read_bytes(), ticker + " carry-forward recipe changed")
        require((Path(root) / "artifacts" / "FAST.json").read_bytes() == (nested / "artifacts" / "FAST.json").read_bytes(), "FAST unchanged artifact")
    return originals


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader):
    validate(root, manifest, proof_reader=proof_reader)
    parent = stage.proof(root, "quality03-admitted-parent.json", manifest["approved_base_inheritance"]["admitted_parent_manifest_sha256"], proof_reader)
    return admission.preserved_parent_artifact(Path(root) / "admission-parent", parent, ticker, raw, proof_reader=proof_reader)


def assemble(active, manifest, destination, rows, cutoff, *, copy_function=None):
    require(active.manifest.get("approved_base_inheritance", {}).get("schema_version") == admission.SCHEMA, "real admitted Quality03 parent required")
    require(not any(row["outcome"] == "source_bound" for row in rows), "source-bound changes need separate Q03 source authority")
    from .approved_inheritance import _proof
    admission.validate(active.root, active.manifest, deep=True, proof_reader=_proof)
    destination = Path(destination)
    copier = copy_function or shutil.copy2
    shutil.copytree(active.root, destination / "admission-parent", copy_function=copier)
    (destination / "quality03-admitted-parent.json").write_bytes((active.root / "manifest.json").read_bytes())
    anchors = stage.anchors()
    source_epochs = _source_epoch_contract(active.root, proof_reader=_proof)
    receipt = {"schema_version": "US-QUALITY03-ADMITTED-RETENTION-STATUS-1", "parent_manifest_sha256": active.manifest_sha256,
               "cutoff": cutoff, "rows": rows, "counts": dict(Counter(row["outcome"] for row in rows)),
               "active_changed": False, "source_bound_recalculations": 0, "source_epoch_by_target": source_epochs,
               "revised_target_count": 8, "carried_forward_count": 42, "held_update_count": 36,
               "private_only_diagnostic_count": 5, "FAST_unchanged": True}
    raw = canonical(receipt)
    (destination / "quality03-admitted-status.json").write_bytes(raw)
    manifest.pop("local_admission", None)
    manifest.update(approved_base_inheritance={"schema_version": SCHEMA, "admitted_parent_manifest_sha256": active.manifest_sha256,
        "quality_stage_manifest_sha256": anchors["manifest_sha256"], "authorization_sha256": active.manifest["local_admission"]["authorization_sha256"],
        "readiness_sha256": active.manifest["local_admission"]["readiness_sha256"]}, base_catalog_version=active.manifest["base_catalog_version"],
        base_manifest_sha256=active.manifest["base_manifest_sha256"], refresh_parent_catalog_version=active.catalog_version,
        refresh_parent_manifest_sha256=active.manifest_sha256, staged_release_only=True, staged_read_only_review_ready=False,
        admission_prepared_only=True, admission=False, activation=False, publication=False,
        catalog_kind="unadmitted_quality03_admitted_retention_child", quality03_admitted_retention_receipt_sha256=sha(raw))
    manifest["preserved_prior_estimate_sha256"] = {str(path.relative_to(destination)): sha(path.read_bytes()) for path in destination.rglob("*") if path.is_file() and not str(path.relative_to(destination)).startswith(("artifacts/", "recipes/"))}
