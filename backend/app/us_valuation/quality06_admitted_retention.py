"""Future-only retention child for a real Q06 local admission.

The child keeps the actual admitted parent byte-authenticated and records only
status/hold outcomes. It never grants admission, activates a pointer, captures
SEC data, recalculates a valuation, or publishes a result.
"""
from collections import Counter
from pathlib import Path
import shutil

from . import quality06_admission as admission
from . import quality06_staged as stage

SCHEMA = "US-QUALITY06-ADMITTED-RETENTION-CHILD-1"
ROOT_FILES = {
    "manifest.json", "artifacts", "recipes", "refresh-policies.json",
    "admission-parent", "quality06-admitted-parent.json",
    "quality06-admitted-status.json",
}
ALLOWED = {"checked_unchanged", "prior_unavailable", "held_new_filing"}
require, canonical, sha = stage.require, stage.canonical, stage.sha


def _source_epoch_contract(root, *, proof_reader):
    anchors = stage.anchors()
    binding = stage.proof(root, "quality-source-binding.json",
                          anchors["binding_sha256"], proof_reader)
    policies = stage.proof(root, "refresh-policies.json",
                           anchors["policies_sha256"], proof_reader)
    prior = stage.proof(root, "approved-parent-policies.json",
                        anchors["parent_policies_sha256"], proof_reader)
    require(set(binding["records"]) == stage.TARGETS | stage.CARRY_FORWARD,
            "Q06 binding scope")
    epochs = {}
    for ticker in stage.TARGETS:
        record = binding["records"][ticker]
        epoch = record.get("proposed_review_hold_epoch")
        require(
            isinstance(epoch, str)
            and epoch == record.get("proposed_evidence_cutoff")
            and epoch == record.get("proposed_public_valuation_date"),
            ticker + " mixed source/valuation epoch",
        )
        require(policies[ticker].get("source_epoch") == epoch,
                ticker + " admitted policy source epoch")
        old = prior.get(ticker, {})
        if old.get("source_epoch") is not None:
            require(old["source_epoch"] == epoch,
                    ticker + " inherited source epoch changed")
        epochs[ticker] = epoch
    return epochs


def _validate_scope(root, *, proof_reader):
    anchors = stage.anchors()
    binding = stage.proof(root, "quality-source-binding.json",
                          anchors["binding_sha256"], proof_reader)
    confirmation = stage.proof(root, "quality-private-confirmation.json",
                               anchors["confirmation_sha256"], proof_reader)
    require(set(binding["carry_forward"]) == stage.CARRY_FORWARD
            and set(binding["private_held_updates"]) == stage.HELD
            and set(binding["private_only_diagnostics"]) == stage.PRIVATE_ONLY
            and set(binding["unchanged_controls"]) == stage.CONTROLS,
            "Q06 carry/held/private-only/control scope")
    require(len(stage.TARGETS) == 25 and len(stage.CARRY_FORWARD) == 25
            and len(stage.HELD) == 23 and len(stage.PRIVATE_ONLY) == 1
            and len(stage.CONTROLS) == 1,
            "Q06 25/25/23/1/1 scope")
    require(set(confirmation["preserved_held_updates"]) == stage.HELD
            and set(confirmation["preserved_unchanged_ranges"])
            == stage.CONTROLS,
            "Q06 private hold/control confirmation")
    return _source_epoch_contract(root, proof_reader=proof_reader)


def validate(root, manifest, *, deep=False, proof_reader=None):
    require(callable(proof_reader), "verified admitted-child proof reader")
    anchors = stage.anchors()
    lineage = manifest.get("approved_base_inheritance")
    require(
        isinstance(lineage, dict)
        and set(lineage) == {
            "schema_version", "admitted_parent_manifest_sha256",
            "quality_stage_manifest_sha256", "authorization_sha256",
            "readiness_sha256",
        }
        and lineage["schema_version"] == SCHEMA
        and lineage["quality_stage_manifest_sha256"]
        == anchors["manifest_sha256"],
        "exact Q06 admitted-child ancestry",
    )
    parent = stage.proof(root, "quality06-admitted-parent.json",
                        lineage["admitted_parent_manifest_sha256"],
                        proof_reader)
    nested = Path(root) / "admission-parent"
    require(stage.proof(nested, "manifest.json",
                         lineage["admitted_parent_manifest_sha256"],
                         proof_reader) == parent,
            "exact retained actual Q06 admitted parent")
    require(parent.get("approved_base_inheritance", {}).get("schema_version")
            == admission.SCHEMA,
            "real admitted Q06 parent required")
    _validate_scope(nested, proof_reader=proof_reader)
    require(
        manifest.get("refresh_parent_manifest_sha256")
        == lineage["admitted_parent_manifest_sha256"]
        and manifest.get("refresh_parent_catalog_version")
        == parent["catalog_version"],
        "immediate actual Q06 refresh parent",
    )
    require(
        manifest.get("base_manifest_sha256") == parent["base_manifest_sha256"]
        and manifest.get("base_catalog_version") == parent["base_catalog_version"],
        "approved old Q06 parent distinct from refresh parent",
    )
    require(
        manifest.get("staged_release_only") is True
        and manifest.get("admission_prepared_only") is True
        and manifest.get("staged_read_only_review_ready") is False
        and manifest.get("catalog_kind")
        == "unadmitted_quality06_admitted_retention_child",
        "inactive Q06 admitted-child metadata",
    )
    require(all(manifest.get(key) is False for key in
                ("admission", "activation", "publication"))
            and "local_admission" not in manifest,
            "Q06 parent release grant leaked to child")
    mutable = {
        "catalog_version", "valuation_date", "publication_counts",
        "refresh_status", "refresh_cutoff", "input_fingerprints",
        "preserved_prior_estimate_sha256", "refresh_parent_catalog_version",
        "refresh_parent_manifest_sha256", "approved_base_inheritance",
        "catalog_kind", "staged_release_only",
        "staged_read_only_review_ready", "admission_prepared_only",
        "admission", "local_admission",
        "quality06_admitted_retention_receipt_sha256",
    }
    require(
        set(manifest) == (set(parent) - {"local_admission"}) | {
            "refresh_parent_catalog_version", "refresh_parent_manifest_sha256",
            "refresh_cutoff", "refresh_status", "input_fingerprints",
            "preserved_prior_estimate_sha256",
            "quality06_admitted_retention_receipt_sha256",
        },
        "exact Q06 admitted-child manifest fields",
    )
    require(all(manifest[key] == value for key, value in parent.items()
                if key not in mutable),
            "Q06 child economics/source/recipe/policy/identity changed")
    receipt = stage.proof(
        root, "quality06-admitted-status.json",
        manifest["quality06_admitted_retention_receipt_sha256"],
        proof_reader,
    )
    epochs = _source_epoch_contract(nested, proof_reader=proof_reader)
    require(
        receipt.get("schema_version")
        == "US-QUALITY06-ADMITTED-RETENTION-STATUS-1"
        and receipt.get("parent_manifest_sha256")
        == lineage["admitted_parent_manifest_sha256"]
        and receipt.get("cutoff") == manifest.get("refresh_cutoff")
        and receipt.get("active_changed") is False
        and receipt.get("source_bound_recalculations") == 0
        and receipt.get("source_epoch_by_target") == epochs,
        "Q06 admitted status parent/no-recalculation authority",
    )
    require(
        receipt.get("revised_target_count") == 25
        and receipt.get("carried_forward_count") == 25
        and receipt.get("held_update_count") == 23
        and receipt.get("private_only_diagnostic_count") == 1
        and receipt.get("unchanged_control_count") == 1
        and receipt.get("unchanged_controls_preserved") is True,
        "Q06 admitted status lane counts",
    )
    rows = receipt["rows"]
    require(len(rows) == len({row["ticker"] for row in rows}) == 650
            and {row["ticker"] for row in rows}
            == {entry["ticker"] for entry in parent["entries"]},
            "all650 Q06 issuer outcomes")
    require(set(row["outcome"] for row in rows) <= ALLOWED
            and dict(Counter(row["outcome"] for row in rows))
            == receipt["counts"], "Q06 retention-only outcomes")
    require(set(manifest["refresh_status"]) ==
            {row["ticker"] for row in rows},
            "exact Q06 issuer status membership")
    for row in rows:
        ticker = row["ticker"]
        status = manifest["refresh_status"][ticker]
        require(status["outcome"] == row["outcome"]
                and status["checked_as_of"] == receipt["cutoff"],
                ticker + " status accounting")
        if ticker in stage.HELD:
            require(status.get("private_quality_hold") is True
                    and status.get("private_quality_hold_preserved") is True
                    and row.get("private_quality_hold") is True,
                    ticker + " private quality hold lost")
        if ticker in stage.TARGETS:
            if row.get("latest_accession") != row.get("prior_accession"):
                require(row["outcome"] == "held_new_filing",
                        ticker + " changed filing escaped Q06 hold")
    if deep:
        require({path.name for path in Path(root).iterdir()} == ROOT_FILES,
                "exact Q06 admitted-child root files")
        require({path.name for path in (Path(root) / "artifacts").iterdir()}
                == {entry["ticker"] + ".json" for entry in parent["entries"]},
                "Q06 child artifact membership")
        require({path.name for path in (Path(root) / "recipes").iterdir()}
                == {ticker + ".json"
                    for ticker in parent["private_recipe_sha256"]},
                "Q06 child recipe membership")
        require((Path(root) / "refresh-policies.json").read_bytes()
                == (nested / "refresh-policies.json").read_bytes(),
                "Q06 child exact policy bytes")
    return parent


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader):
    validate(root, manifest, proof_reader=proof_reader)
    parent = stage.proof(
        root, "quality06-admitted-parent.json",
        manifest["approved_base_inheritance"]
        ["admitted_parent_manifest_sha256"], proof_reader,
    )
    return admission.preserved_parent_artifact(
        Path(root) / "admission-parent", parent, ticker, raw,
        proof_reader=proof_reader,
    )


def consumer_disclosures(root, manifest, artifact, payload, *, proof_reader):
    validate(root, manifest, proof_reader=proof_reader)
    parent = stage.proof(
        root, "quality06-admitted-parent.json",
        manifest["approved_base_inheritance"]
        ["admitted_parent_manifest_sha256"], proof_reader,
    )
    return admission.consumer_disclosures(
        Path(root) / "admission-parent", parent, artifact, payload,
        proof_reader=proof_reader,
    )


def assemble(active, manifest, destination, rows, cutoff, *, copy_function=None):
    require(
        active.manifest.get("approved_base_inheritance", {})
        .get("schema_version") == admission.SCHEMA,
        "real admitted Quality06 parent required",
    )
    require(not any(row["outcome"] == "source_bound" for row in rows),
            "source-bound changes need separate Q06 source authority")
    destination = Path(destination)
    copier = copy_function or shutil.copy2
    shutil.copytree(active.root, destination / "admission-parent",
                    copy_function=copier)
    (destination / "quality06-admitted-parent.json").write_bytes(
        (active.root / "manifest.json").read_bytes())
    anchors = stage.anchors()
    from .approved_inheritance import _proof
    source_epochs = _source_epoch_contract(active.root, proof_reader=_proof)
    receipt = {
        "schema_version": "US-QUALITY06-ADMITTED-RETENTION-STATUS-1",
        "parent_manifest_sha256": active.manifest_sha256,
        "cutoff": cutoff, "rows": rows,
        "counts": dict(Counter(row["outcome"] for row in rows)),
        "active_changed": False, "source_bound_recalculations": 0,
        "source_epoch_by_target": source_epochs,
        "revised_target_count": 25, "carried_forward_count": 25,
        "held_update_count": 23, "private_only_diagnostic_count": 1,
        "unchanged_control_count": 1, "unchanged_controls_preserved": True,
    }
    raw = canonical(receipt)
    (destination / "quality06-admitted-status.json").write_bytes(raw)
    manifest.pop("local_admission", None)
    manifest.update(
        approved_base_inheritance={
            "schema_version": SCHEMA,
            "admitted_parent_manifest_sha256": active.manifest_sha256,
            "quality_stage_manifest_sha256": anchors["manifest_sha256"],
            "authorization_sha256":
                active.manifest["local_admission"]["authorization_sha256"],
            "readiness_sha256":
                active.manifest["local_admission"]["readiness_sha256"],
        },
        base_catalog_version=active.manifest["base_catalog_version"],
        base_manifest_sha256=active.manifest["base_manifest_sha256"],
        refresh_parent_catalog_version=active.catalog_version,
        refresh_parent_manifest_sha256=active.manifest_sha256,
        staged_release_only=True, staged_read_only_review_ready=False,
        admission_prepared_only=True, admission=False, activation=False,
        publication=False,
        catalog_kind="unadmitted_quality06_admitted_retention_child",
        quality06_admitted_retention_receipt_sha256=sha(raw),
    )
    manifest["preserved_prior_estimate_sha256"] = {
        str(path.relative_to(destination)): sha(path.read_bytes())
        for path in destination.rglob("*") if path.is_file()
        and not str(path.relative_to(destination)).startswith(
            ("artifacts/", "recipes/"))
    }
