"""Offline verification-only status children of the frozen Quality04 stage."""

from collections import Counter
from pathlib import Path
import shutil

from . import quality04_staged as stage


SCHEMA = "US-QUALITY04-OFFLINE-RETENTION-CHILD-1"
EXTRA = {
    "quality04-refresh-stage.json",
    "quality04-refresh-authorization.json",
    "quality04-refresh-status.json",
}
ALLOWED = {"checked_unchanged", "prior_unavailable", "held_new_filing"}
require, canonical, sha = stage.require, stage.canonical, stage.sha


def reader(proof_reader):
    """Translate the retained parent manifest proof to its child filename."""

    def wrapped(root, name, digest):
        return proof_reader(
            root,
            "quality04-refresh-stage.json" if name == "manifest.json" else name,
            digest,
        )

    return wrapped


def validate(root, manifest, *, deep=False, proof_reader=None):
    """Validate a Q04 child without granting source, admission, or release authority."""

    anchors = stage.anchors()
    parent = stage.proof(
        root,
        "quality04-refresh-stage.json",
        anchors["manifest_sha256"],
        proof_reader,
    )
    grant = stage.proof(
        root,
        "quality04-refresh-authorization.json",
        anchors["approval_sha256"],
        proof_reader,
    )
    require(
        grant["staged_candidate_only"] is True
        and all(grant[key] is False for key in stage.DENIED),
        "offline child authority is not release",
    )
    require(
        manifest["approved_base_inheritance"]
        == {
            "schema_version": SCHEMA,
            "quality_stage_manifest_sha256": anchors["manifest_sha256"],
            "authorization_sha256": anchors["approval_sha256"],
        },
        "exact child ancestry",
    )
    require(
        manifest["catalog_kind"] == "quality04_offline_verification_retention_child"
        and manifest["staged_release_only"] is True
        and manifest["staged_read_only_review_ready"] is False
        and manifest["admission_prepared_only"] is False,
        "offline-only child",
    )
    require(
        all(manifest[key] is False for key in ("admission", "activation", "publication"))
        and "local_admission" not in manifest,
        "child release flags",
    )
    require(
        manifest["refresh_parent_catalog_version"] == parent["catalog_version"]
        and manifest["refresh_parent_manifest_sha256"] == anchors["manifest_sha256"],
        "immediate refresh parent",
    )
    require(
        manifest["base_catalog_version"] == parent["base_catalog_version"]
        and manifest["base_manifest_sha256"] == parent["base_manifest_sha256"],
        "approved parent distinct from refresh parent",
    )
    mutable = {
        "catalog_version",
        "valuation_date",
        "base_catalog_version",
        "base_manifest_sha256",
        "publication_counts",
        "refresh_status",
        "refresh_cutoff",
        "input_fingerprints",
        "preserved_prior_estimate_sha256",
        "refresh_parent_catalog_version",
        "refresh_parent_manifest_sha256",
        "approved_base_inheritance",
        "catalog_kind",
        "staged_release_only",
        "staged_read_only_review_ready",
        "admission_prepared_only",
        "quality04_retention_receipt_sha256",
    }
    require(
        set(manifest) <= set(parent) | mutable
        and all(manifest[key] == value for key, value in parent.items() if key not in mutable),
        "child economic/policy/source mutation",
    )
    original = stage.validate(
        root, parent, deep=False, proof_reader=reader(proof_reader)
    )
    receipt = stage.proof(
        root,
        "quality04-refresh-status.json",
        manifest["quality04_retention_receipt_sha256"],
        proof_reader,
    )
    require(
        receipt["base_manifest_sha256"] == anchors["manifest_sha256"]
        and receipt["active_changed"] is False
        and receipt["source_bound_recalculations"] == 0
        and receipt["offline_verification_only"] is True,
        "status receipt",
    )
    rows = receipt["rows"]
    require(
        len(rows) == len({row["ticker"] for row in rows}) == 650
        and {row["ticker"] for row in rows}
        == {entry["ticker"] for entry in parent["entries"]},
        "all650 outcomes",
    )
    require(
        set(row["outcome"] for row in rows) <= ALLOWED
        and dict(Counter(row["outcome"] for row in rows)) == receipt["counts"],
        "no recalculations",
    )
    require(
        set(manifest["refresh_status"]) == {row["ticker"] for row in rows},
        "complete status mapping",
    )
    for row in rows:
        status = manifest["refresh_status"][row["ticker"]]
        require(
            status["outcome"] == row["outcome"]
            and status["checked_as_of"] == receipt["cutoff"],
            "status accounting",
        )
        if row["ticker"] in stage.TARGETS and row.get("latest_accession") != row.get(
            "prior_accession"
        ):
            require(
                row["outcome"] == "held_new_filing",
                "changed target outside its hold",
            )
    if deep:
        require(
            {path.name for path in Path(root).iterdir()} == stage.ROOT_FILES | EXTRA,
            "child proof filenames",
        )
        expected = {
            str(path.relative_to(root)): sha(path.read_bytes())
            for path in Path(root).rglob("*")
            if path.is_file()
            and path != Path(root) / "manifest.json"
            and not str(path.relative_to(root)).startswith(("artifacts/", "recipes/"))
        }
        require(
            manifest["preserved_prior_estimate_sha256"] == expected,
            "actual child proof index",
        )
        for entry in parent["entries"]:
            stage.proof(
                root,
                "artifacts/" + entry["ticker"] + ".json",
                entry["artifact_sha256"],
                proof_reader,
            )
        for ticker, digest in parent["private_recipe_sha256"].items():
            stage.proof(root, "recipes/" + ticker + ".json", digest, proof_reader)
        for ticker in stage.TARGETS:
            binding = stage.proof(
                root,
                "quality-source-binding.json",
                anchors["binding_sha256"],
                proof_reader,
            )
            stage.target(
                root,
                parent,
                ticker,
                binding["records"][ticker],
                next(entry for entry in parent["entries"] if entry["ticker"] == ticker),
                reader(proof_reader),
            )
        from .approved_inheritance import validate_inheritance

        old = stage.proof(
            root,
            "approved-parent-manifest.json",
            anchors["parent_manifest_sha256"],
            proof_reader,
        )
        validate_inheritance(Path(root) / "prior-catalog", old, deep=True)
    return original


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader):
    validate(root, manifest, deep=False, proof_reader=proof_reader)
    parent = stage.proof(
        root,
        "quality04-refresh-stage.json",
        stage.anchors()["manifest_sha256"],
        proof_reader,
    )
    return stage.preserved_parent_artifact(
        root, parent, ticker, raw, proof_reader=reader(proof_reader)
    )


def assemble(active, manifest, destination, rows, cutoff, *, copy_function=None):
    """Build a retention-only child in an isolated test/offline environment."""

    import os

    require(os.environ.get("APP_ENV") == "test", "offline verification environment")
    anchors = stage.anchors()
    require(
        active.manifest_sha256 == anchors["manifest_sha256"]
        and not any(row["outcome"] == "source_bound" for row in rows),
        "compiled baseline and no new valuations",
    )
    copier = copy_function or shutil.copy2
    destination = Path(destination)
    for name in stage.ROOT_FILES - {
        "manifest.json",
        "artifacts",
        "recipes",
        "refresh-policies.json",
    }:
        source, target = active.root / name, destination / name
        if source.is_dir():
            shutil.copytree(source, target, copy_function=copier)
        else:
            copier(source, target)
    for name, source, pin in (
        (
            "quality04-refresh-stage.json",
            active.root / "manifest.json",
            anchors["manifest_sha256"],
        ),
        (
            "quality04-refresh-authorization.json",
            active.root / "quality-scope-authorization.json",
            anchors["approval_sha256"],
        ),
    ):
        raw = source.read_bytes()
        require(sha(raw) == pin, "offline child authority bytes")
        (destination / name).write_bytes(raw)
    receipt = {
        "schema_version": "US-QUALITY04-OFFLINE-RETENTION-STATUS-1",
        "base_manifest_sha256": active.manifest_sha256,
        "cutoff": cutoff,
        "rows": rows,
        "counts": dict(Counter(row["outcome"] for row in rows)),
        "active_changed": False,
        "source_bound_recalculations": 0,
        "offline_verification_only": True,
    }
    raw = canonical(receipt)
    (destination / "quality04-refresh-status.json").write_bytes(raw)
    manifest.update(
        approved_base_inheritance={
            "schema_version": SCHEMA,
            "quality_stage_manifest_sha256": anchors["manifest_sha256"],
            "authorization_sha256": anchors["approval_sha256"],
        },
        base_catalog_version=active.manifest["base_catalog_version"],
        base_manifest_sha256=active.manifest["base_manifest_sha256"],
        refresh_parent_catalog_version=active.catalog_version,
        refresh_parent_manifest_sha256=active.manifest_sha256,
        staged_release_only=True,
        staged_read_only_review_ready=False,
        admission_prepared_only=False,
        admission=False,
        activation=False,
        publication=False,
        catalog_kind="quality04_offline_verification_retention_child",
        quality04_retention_receipt_sha256=sha(raw),
    )
    manifest["preserved_prior_estimate_sha256"] = {
        str(path.relative_to(destination)): sha(path.read_bytes())
        for path in destination.rglob("*")
        if path.is_file()
        and not str(path.relative_to(destination)).startswith(("artifacts/", "recipes/"))
    }
