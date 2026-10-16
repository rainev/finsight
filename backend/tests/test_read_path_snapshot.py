"""Adversarial coverage for request-scoped read-path proof caching."""

import hashlib
import json
from pathlib import Path

import pytest

from app.us_valuation import quality03_admission
from app.us_valuation import quality04_admission
from app.us_valuation.read_path_snapshot import ProofSnapshot, SnapshotProofReader


def _raw(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _write(root, name, value):
    raw = _raw(value)
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_cached_manifest_proofs_are_fresh_objects_and_mutation_isolated(tmp_path):
    manifest = {"catalog_version": "test", "entries": [{"ticker": "AAA"}]}
    digest = _write(tmp_path, "manifest.json", manifest)
    snapshot = ProofSnapshot()

    value = snapshot.proof(tmp_path, "manifest.json", digest)
    value["entries"][0]["ticker"] = "POISON"
    fresh = snapshot.proof(tmp_path, "manifest.json", digest)
    assert fresh == manifest
    assert fresh is not value
    assert fresh["entries"] is not value["entries"]


def test_context_and_metadata_recheck_the_caller_manifest(tmp_path):
    manifest = {"catalog_version": "test", "entries": []}
    _write(tmp_path, "manifest.json", manifest)
    snapshot = ProofSnapshot(tmp_path, manifest)
    calls = []
    assert snapshot.context_for(tmp_path, manifest, lambda: calls.append(1) or {"ok": True}) == {"ok": True}
    assert calls == [1]

    manifest["catalog_version"] = "forged"
    with pytest.raises(ValueError, match="caller manifest"):
        snapshot.context_for(tmp_path, manifest, lambda: {"ok": "poison"})
    with pytest.raises(ValueError, match="caller manifest"):
        snapshot.metadata_for(tmp_path, manifest, lambda: {"ok": "poison"})


def test_disk_edit_is_not_trusted_by_a_new_request_snapshot(tmp_path):
    manifest = {"catalog_version": "test", "entries": []}
    digest = _write(tmp_path, "manifest.json", manifest)
    first = ProofSnapshot()
    assert first.proof(tmp_path, "manifest.json", digest)["catalog_version"] == "test"

    changed = {"catalog_version": "edited", "entries": []}
    _write(tmp_path, "manifest.json", changed)
    with pytest.raises(ValueError, match="hash mismatch"):
        ProofSnapshot().proof(tmp_path, "manifest.json", digest)


def test_raw_authenticated_but_noncanonical_proof_fails_closed(tmp_path):
    raw = b'{"entries": [], "catalog_version": "test"}\n'
    (tmp_path / "manifest.json").write_bytes(raw)
    with pytest.raises(ValueError, match="parsed proof hash mismatch"):
        ProofSnapshot().proof(tmp_path, "manifest.json", hashlib.sha256(raw).hexdigest())


def test_snapshot_reader_is_immutable_and_fake_hooks_do_not_bypass_validation(monkeypatch, tmp_path):
    reader = SnapshotProofReader(ProofSnapshot())
    with pytest.raises(TypeError, match="immutable"):
        reader._snapshot = None

    calls = []

    class FakeReader:
        def __call__(self, *_args):
            return {}

        def metadata_for(self, *_args):
            return {"poison": True}

    monkeypatch.setattr(
        quality04_admission,
        "_metadata_uncached",
        lambda *args, **kwargs: calls.append(True) or {"validated": True},
    )
    assert quality04_admission.metadata(tmp_path, {}, proof_reader=FakeReader()) == {"validated": True}
    assert calls == [True]


def test_symlinked_proof_is_rejected(tmp_path):
    target = tmp_path / "outside.json"
    target.write_text("{}")
    link = tmp_path / "manifest.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="regular in-root file"):
        ProofSnapshot().proof(tmp_path, "manifest.json", hashlib.sha256(b"{}").hexdigest())


def test_quality04_inherited_consumer_uses_q03_parent_scope(monkeypatch, tmp_path):
    """Q04's 600 inherited records are Q03-parent records, never Q02 records."""
    parent_calls = []
    parent_manifest = {"catalog_version": "q03-parent"}
    monkeypatch.setattr(quality04_admission, "metadata", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        quality04_admission.stage,
        "proof",
        lambda root, name, expected, proof_reader: parent_manifest,
    )

    def q03_parent(root, manifest, artifact, payload, *, proof_reader):
        parent_calls.append((Path(root), manifest, artifact["issuer"]["ticker"]))
        return {**payload, "parent": "q03"}

    monkeypatch.setattr(quality03_admission, "consumer_disclosures", q03_parent)
    artifact = {"issuer": {"ticker": "ZZZ"}}
    result = quality04_admission.consumer_disclosures(
        tmp_path,
        {"catalog_version": "q04"},
        artifact,
        {"base": 1},
        proof_reader=lambda *_args: {},
    )
    assert result == {"base": 1, "parent": "q03"}
    assert parent_calls == [(tmp_path / "prior-catalog", parent_manifest, "ZZZ")]


def test_quality04_stage_does_not_trust_forged_digest_attribute():
    class Forged(dict):
        _read_path_digest = "f" * 64

    with pytest.raises(ValueError, match="parsed proof changed"):
        quality04_admission.stage.proof(
            Path("/unused"), "manifest.json", "f" * 64, lambda *_args: Forged(poison=True)
        )
