from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil

import pytest

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.calculator import baseline_version
from app.us_valuation.catalog import CatalogIntegrityError, canonical_json_bytes, load_catalog_version, load_active_catalog, sha256_bytes
from app.us_valuation.refresh_catalog_store import (
    REFRESH_REGISTRY_SCHEMA,
    RefreshCatalogStore,
    load_frozen_registry,
)


ROOT = Path(__file__).resolve().parents[2]
RESET = ROOT / "backend/app/data/us_valuation_catalogs/US-RESET-2026-08-14-B01-B10-1.0"


def _registry_for(
    catalog_root: Path, *, numeric_ticker: str | None = None, numeric_tickers: set[str] | None = None
) -> dict:
    catalog = load_catalog_version(catalog_root)
    return {
        "schema_version": REFRESH_REGISTRY_SCHEMA,
        "baseline_catalog_version": catalog.catalog_version,
        "baseline_manifest_sha256": catalog.manifest_sha256,
        "entries": [
                {
                    "ticker": entry.ticker,
                    "cik": entry.cik,
                    "batch": entry.batch,
                    "recipe_status": (
                        "migration_pending"
                        if entry.ticker == numeric_ticker or entry.ticker in (numeric_tickers or set())
                        else "prior_unavailable"
                    ),
                }
            for entry in catalog.entries
        ],
    }


def _store(tmp_path: Path, source: Path = RESET) -> RefreshCatalogStore:
    registry = _registry_for(source)
    registry_path = tmp_path / "frozen-registry.json"
    registry_path.write_bytes(canonical_json_bytes(registry))
    return RefreshCatalogStore(
        tmp_path / "runtime",
        frozen_registry=registry_path,
        expected_registry_count=len(registry["entries"]),
    )


def _refresh_source_and_store(tmp_path: Path) -> tuple[Path, RefreshCatalogStore]:
    source = _versioned_source(tmp_path, "REFRESH-TEST")
    recipe_hashes: dict[str, str] = {}
    recipes_root = source / "recipes"
    recipes_root.mkdir()
    numeric_tickers: set[str] = set()
    for artifact_path in sorted((source / "artifacts").glob("*.json")):
        public = sanitize_public_artifact(json.loads(artifact_path.read_text(encoding="utf-8")))
        if public["availability_type"] == "not_available":
            continue
        ticker = artifact_path.stem
        numeric_tickers.add(ticker)
        target = public["scenario_range"]
        recipe = {
            "schema_version": "FINSIGHT-CALCULATION-RECIPE-1",
            "ticker": ticker,
            "baseline_version": baseline_version(public),
            "recipe_version": "TEST-1",
            "editable": {},
            "scenarios": {
                name: {
                    "engine": "earnings_multiple",
                    "inputs": {
                        "earnings": 1.0,
                        "multiple": float(target[target_name]),
                        "shares": 1.0,
                        "net_bridge": 0.0,
                    },
                }
                for name, target_name in (
                    ("bear", "low"),
                    ("base", "base"),
                    ("bull", "high"),
                )
            },
        }
        recipe_path = recipes_root / f"{ticker}.json"
        recipe_path.write_bytes(canonical_json_bytes(recipe))
        recipe_hashes[ticker] = sha256_bytes(recipe_path.read_bytes())
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["private_recipe_sha256"] = recipe_hashes
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    registry = _registry_for(
        RESET,
        numeric_tickers=numeric_tickers,
    )
    registry_path = tmp_path / "frozen-registry.json"
    registry_path.write_bytes(canonical_json_bytes(registry))
    store = RefreshCatalogStore(
        tmp_path / "runtime",
        frozen_registry=registry_path,
        expected_registry_count=len(registry["entries"]),
    )
    return source, store


def _versioned_source(tmp_path: Path, version: str) -> Path:
    source = tmp_path / f"source-{version}"
    shutil.copytree(RESET, source)
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["catalog_version"] = version
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return source


def _approve(store: RefreshCatalogStore, fingerprint: str = "policy-v1") -> None:
    store.approved_policy_path.parent.mkdir(parents=True, exist_ok=True)
    store.approved_policy_path.write_bytes(
        canonical_json_bytes(
            {
                "status": "approved",
                "policy_fingerprint": fingerprint,
                "registry_sha256": store.registry.registry_sha256,
            }
        )
    )


def test_stage_validates_complete_catalog_and_keeps_runtime_snapshot_immutable(tmp_path: Path) -> None:
    store = _store(tmp_path)

    staged = store.stage_catalog(RESET)

    assert staged.catalog_version == "US-RESET-2026-08-14-B01-B10-1.0"
    assert staged.root == store.snapshots_root / staged.catalog_version
    assert staged.manifest_sha256 == load_catalog_version(staged.root).manifest_sha256
    assert not store.active_pointer_path.exists()

    # Re-staging identical bytes is idempotent; replacing the same version with
    # different bytes is refused rather than mutating an immutable snapshot.
    assert store.stage_catalog(RESET).manifest_sha256 == staged.manifest_sha256
    changed = tmp_path / "changed"
    shutil.copytree(RESET, changed)
    artifact = changed / "artifacts" / "AAPL.json"
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    with pytest.raises(CatalogIntegrityError, match="hash mismatch"):
        store.stage_catalog(changed)


def test_refresh_snapshot_requires_and_copies_private_recipe_index(tmp_path: Path) -> None:
    source, store = _refresh_source_and_store(tmp_path)

    staged = store.stage_catalog(source)

    assert staged.root.joinpath("recipes", "AAPL.json").is_file()
    assert staged.manifest["private_recipe_sha256"]["AAPL"] == sha256_bytes(
        staged.root.joinpath("recipes", "AAPL.json").read_bytes()
    )


def test_refresh_snapshot_rejects_missing_or_drifted_private_recipe_pin(tmp_path: Path) -> None:
    source, store = _refresh_source_and_store(tmp_path)
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("private_recipe_sha256")
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(CatalogIntegrityError, match="index is required"):
        store.stage_catalog(source)

    source, store = _refresh_source_and_store(tmp_path / "drift")
    recipe_path = source / "recipes" / "AAPL.json"
    recipe_path.write_bytes(recipe_path.read_bytes() + b"\n")
    with pytest.raises(CatalogIntegrityError, match="hash mismatch"):
        store.stage_catalog(source)


def test_refresh_snapshot_rejects_recipe_symlink_escape_and_membership_drift(tmp_path: Path) -> None:
    source, store = _refresh_source_and_store(tmp_path)
    recipe_path = source / "recipes" / "AAPL.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(recipe_path.read_bytes())
    recipe_path.unlink()
    recipe_path.symlink_to(outside)
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["private_recipe_sha256"]["AAPL"] = sha256_bytes(outside.read_bytes())
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(CatalogIntegrityError, match="escapes"):
        store.stage_catalog(source)

    source, store = _refresh_source_and_store(tmp_path / "membership")
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["private_recipe_sha256"]["NOPE"] = manifest["private_recipe_sha256"]["AAPL"]
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(CatalogIntegrityError, match="membership"):
        store.stage_catalog(source)


def test_active_reader_rechecks_private_recipe_pin_on_first_load(tmp_path: Path) -> None:
    source, store = _refresh_source_and_store(tmp_path)
    staged = store.stage_catalog(source)
    _approve(store)
    store.activate(
        staged,
        policy_fingerprint="policy-v1",
        activated_at="one",
        expected_active_manifest_sha256=None,
    )
    recipe_path = staged.root / "recipes" / "AAPL.json"
    recipe_path.write_bytes(recipe_path.read_bytes() + b"\n")

    with pytest.raises(CatalogIntegrityError, match="hash mismatch"):
        store.reader().get_snapshot()


def test_activation_requires_preexisting_policy_and_writes_atomic_pointer_receipt(tmp_path: Path) -> None:
    store = _store(tmp_path)
    staged = store.stage_catalog(RESET)

    with pytest.raises(CatalogIntegrityError, match="preexisting approved policy"):
        store.activate(staged, policy_fingerprint="policy-v1", activated_at="2026-09-08T00:00:00Z")
    assert not store.active_pointer_path.exists()
    assert not store.approved_policy_path.exists()

    store.approved_policy_path.write_bytes(
        canonical_json_bytes(
            {
                "policy_fingerprint": "policy-v1",
                "registry_sha256": store.registry.registry_sha256,
            }
        )
    )
    with pytest.raises(CatalogIntegrityError, match="not approved"):
        store.activate(staged, policy_fingerprint="policy-v1", activated_at="missing-approval")

    store.approved_policy_path.write_bytes(
        canonical_json_bytes(
            {
                "approved": True,
                "policy_fingerprint": "policy-v1",
                "registry_sha256": "0" * 64,
            }
        )
    )
    with pytest.raises(CatalogIntegrityError, match="registry hash"):
        store.activate(staged, policy_fingerprint="policy-v1", activated_at="wrong-registry")

    _approve(store)
    result = store.activate(
        staged,
        policy_fingerprint="policy-v1",
        activated_at="2026-09-08T00:00:00Z",
    )
    pointer = load_active_catalog(store.runtime_root)
    assert pointer.catalog_version == staged.catalog_version
    assert result["rollback_pointer"] is None
    assert result["receipt"]["previous_pointer"] is None
    assert Path(result["receipt_path"]).is_file()
    assert result["pointer"]["policy_fingerprint"] == "policy-v1"


def test_refresh_activation_requires_explicit_compare_and_swap_precondition(tmp_path: Path) -> None:
    source, store = _refresh_source_and_store(tmp_path)
    staged = store.stage_catalog(source)
    _approve(store)

    with pytest.raises(CatalogIntegrityError, match="explicit active-manifest precondition"):
        store.activate(staged, policy_fingerprint="policy-v1", activated_at="one")
    assert not store.active_pointer_path.exists()
    assert not list(store.history_root.glob("*.json"))

    activated = store.activate(
        staged,
        policy_fingerprint="policy-v1",
        activated_at="one",
        expected_active_manifest_sha256=None,
    )
    assert activated["pointer"]["manifest_sha256"] == staged.manifest_sha256


def test_compare_and_swap_rejects_stale_candidate_and_initial_race(tmp_path: Path) -> None:
    source_a, store = _refresh_source_and_store(tmp_path)
    source_b = _versioned_source(tmp_path, "REFRESH-TEST-B")
    # Reuse the valid private recipe index generated for the first source.
    first_manifest = json.loads((source_a / "manifest.json").read_text(encoding="utf-8"))
    second_manifest_path = source_b / "manifest.json"
    second_manifest = json.loads(second_manifest_path.read_text(encoding="utf-8"))
    shutil.copytree(source_a / "recipes", source_b / "recipes")
    second_manifest["private_recipe_sha256"] = first_manifest["private_recipe_sha256"]
    second_manifest_path.write_bytes(canonical_json_bytes(second_manifest))
    first = store.stage_catalog(source_a)
    second = store.stage_catalog(source_b)
    _approve(store)
    activated_first = store.activate(
        first,
        policy_fingerprint="policy-v1",
        activated_at="one",
        expected_active_manifest_sha256=None,
    )
    activated_second = store.activate(
        second,
        policy_fingerprint="policy-v1",
        activated_at="two",
        expected_active_manifest_sha256=activated_first["pointer"]["manifest_sha256"],
    )
    before = store.active_pointer_path.read_bytes()
    receipts_before = sorted(store.history_root.glob("*.json"))

    with pytest.raises(CatalogIntegrityError, match="precondition mismatch"):
        store.activate(
            first,
            policy_fingerprint="policy-v1",
            activated_at="stale",
            expected_active_manifest_sha256=activated_first["pointer"]["manifest_sha256"],
        )
    assert store.active_pointer_path.read_bytes() == before
    assert sorted(store.history_root.glob("*.json")) == receipts_before
    assert load_active_catalog(store.runtime_root).catalog_version == activated_second["pointer"]["catalog_version"]

    # A second writer that still expects an empty active slot cannot win after
    # the first writer has installed its pointer.
    with pytest.raises(CatalogIntegrityError, match="expected no active pointer"):
        store.activate(
            first,
            policy_fingerprint="policy-v1",
            activated_at="initial-race",
            expected_active_manifest_sha256=None,
        )


def test_policy_mismatch_and_registry_mismatch_leave_last_active_pointer_unchanged(tmp_path: Path) -> None:
    store = _store(tmp_path)
    staged = store.stage_catalog(RESET)
    _approve(store)
    store.activate(staged, policy_fingerprint="policy-v1", activated_at="one")
    before = store.active_pointer_path.read_bytes()

    with pytest.raises(CatalogIntegrityError, match="not pre-approved"):
        store.activate(staged, policy_fingerprint="policy-v2", activated_at="two")
    assert store.active_pointer_path.read_bytes() == before

    wrong_registry = _registry_for(RESET)
    wrong_registry["entries"] = wrong_registry["entries"][:-1]
    bad_store = RefreshCatalogStore(
        tmp_path / "bad-runtime",
        frozen_registry=wrong_registry,
        expected_registry_count=len(wrong_registry["entries"]),
    )
    with pytest.raises(CatalogIntegrityError, match="membership"):
        bad_store.stage_catalog(RESET)


def test_activation_failure_on_corrupt_staged_snapshot_preserves_active_pointer(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.stage_catalog(RESET)
    _approve(store)
    store.activate(first, policy_fingerprint="policy-v1", activated_at="one")
    before = store.active_pointer_path.read_bytes()

    second_source = _versioned_source(tmp_path, "TEST-V2")
    second = store.stage_catalog(second_source)
    artifact = second.root / "artifacts" / "AAPL.json"
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    with pytest.raises(CatalogIntegrityError, match="hash mismatch"):
        store.activate(second, policy_fingerprint="policy-v1", activated_at="two")
    assert store.active_pointer_path.read_bytes() == before
    assert load_active_catalog(store.runtime_root).catalog_version == first.catalog_version


def test_reader_pins_one_loaded_snapshot_then_reloads_after_pointer_hash_changes(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.stage_catalog(RESET)
    second = store.stage_catalog(_versioned_source(tmp_path, "TEST-V2"))
    _approve(store)
    store.activate(first, policy_fingerprint="policy-v1", activated_at="one")

    reader = store.reader()
    pinned = reader.get_snapshot()
    store.activate(second, policy_fingerprint="policy-v1", activated_at="two")
    assert pinned.catalog_version == first.catalog_version
    assert reader.get_snapshot().catalog_version == "TEST-V2"


def test_rollback_restores_previous_pointer_and_records_receipt(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.stage_catalog(RESET)
    second = store.stage_catalog(_versioned_source(tmp_path, "TEST-V2"))
    _approve(store)
    store.activate(first, policy_fingerprint="policy-v1", activated_at="one")
    activated = store.activate(second, policy_fingerprint="policy-v1", activated_at="two")

    rollback = store.rollback(activated["receipt_path"], rolled_back_at="three", reason="test")

    assert rollback["pointer"]["catalog_version"] == first.catalog_version
    assert rollback["pointer"]["rollback_of"] == second.catalog_version
    assert load_active_catalog(store.runtime_root).catalog_version == first.catalog_version
    assert rollback["receipt"]["to_pointer"]["catalog_version"] == first.catalog_version
    assert Path(rollback["receipt_path"]).is_file()


def test_rollback_rejects_stale_receipt_without_replacing_newer_activation(tmp_path):
    store = _store(tmp_path)
    first = store.stage_catalog(RESET)
    second = store.stage_catalog(_versioned_source(tmp_path,'ROLLBACK-V2'))
    third = store.stage_catalog(_versioned_source(tmp_path,'ROLLBACK-V3'))
    _approve(store)
    store.activate(first,policy_fingerprint='policy-v1',activated_at='one')
    stale = store.activate(second,policy_fingerprint='policy-v1',activated_at='two')
    store.activate(third,policy_fingerprint='policy-v1',activated_at='three')
    before = store.active_pointer_path.read_bytes()
    with pytest.raises(CatalogIntegrityError,match='currently active'):
        store.rollback(stale['receipt_path'],rolled_back_at='four')
    assert store.active_pointer_path.read_bytes() == before


def test_rollback_revalidates_prior_private_recipe_files(tmp_path):
    source,store = _refresh_source_and_store(tmp_path)
    first = store.stage_catalog(source)
    second_source = _versioned_source(tmp_path,'ROLLBACK-AFTER-PRIVATE')
    second = store.stage_catalog(second_source)
    _approve(store)
    store.activate(first,policy_fingerprint='policy-v1',activated_at='one',expected_active_manifest_sha256=None)
    activated = store.activate(second,policy_fingerprint='policy-v1',activated_at='two')
    recipe_path = first.root/'recipes/AAPL.json'
    recipe_path.write_bytes(recipe_path.read_bytes()+b' ')
    before = store.active_pointer_path.read_bytes()
    with pytest.raises(CatalogIntegrityError,match='recipe'):
        store.rollback(activated['receipt_path'],rolled_back_at='three')
    assert store.active_pointer_path.read_bytes() == before


def test_reader_is_safe_for_concurrent_reads_during_atomic_activation(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.stage_catalog(RESET)
    second = store.stage_catalog(_versioned_source(tmp_path, "TEST-V2"))
    _approve(store)
    store.activate(first, policy_fingerprint="policy-v1", activated_at="one")
    reader = store.reader()

    with ThreadPoolExecutor(max_workers=8) as pool:
        before = list(pool.map(lambda _: reader.get_snapshot().catalog_version, range(32)))
        store.activate(second, policy_fingerprint="policy-v1", activated_at="two")
        after = list(pool.map(lambda _: reader.get_snapshot().catalog_version, range(32)))

    assert set(before) == {first.catalog_version}
    assert set(after) == {second.catalog_version}


def test_reader_rejects_runtime_path_escape_and_symlink_escape(tmp_path: Path) -> None:
    store = _store(tmp_path)
    staged = store.stage_catalog(RESET)
    _approve(store)
    store.activate(staged, policy_fingerprint="policy-v1", activated_at="one")
    pointer = json.loads(store.active_pointer_path.read_text(encoding="utf-8"))
    outside = tmp_path / "outside"
    outside.mkdir()
    (store.snapshots_root / "escape").symlink_to(outside, target_is_directory=True)

    pointer["catalog_path"] = "snapshots/escape"
    store.active_pointer_path.write_bytes(canonical_json_bytes(pointer))
    with pytest.raises(CatalogIntegrityError, match="escapes"):
        store.reader().get_snapshot()

    pointer["catalog_path"] = "snapshots/../outside"
    store.active_pointer_path.write_bytes(canonical_json_bytes(pointer))
    with pytest.raises(CatalogIntegrityError, match="unsafe"):
        store.reader().get_snapshot()


def test_supported_unavailable_keeps_integrity_checked_retry_template(tmp_path):
    from collections import Counter
    from app.us_valuation.catalog import artifact_tree_sha256
    from app.us_valuation.refresh_catalog_store import load_retry_states
    from app.us_valuation.refresh_job import _unavailable
    source,_ = _refresh_source_and_store(tmp_path)
    original = load_catalog_version(source)
    registry = _registry_for(source)
    by_ticker = {entry.ticker:entry for entry in original.entries}
    for entry in registry['entries']:
        entry['availability_type'] = by_ticker[entry['ticker']].availability_type
    store = RefreshCatalogStore(tmp_path/'retry-runtime',frozen_registry=registry,expected_registry_count=len(registry['entries']))
    public = sanitize_public_artifact(json.loads((source/'artifacts/AAPL.json').read_bytes()))
    recipe = json.loads((source/'recipes/AAPL.json').read_bytes())
    unavailable = _unavailable(public,'simulated source-insufficient fixture',cutoff='2026-09-08')
    payload = canonical_json_bytes(unavailable)
    (source/'artifacts/AAPL.json').write_bytes(payload)
    (source/'recipes/AAPL.json').unlink()
    state = {'schema_version':'FINSIGHT-RETRY-STATE-1','recipe':recipe,'public_template':public}
    retry = canonical_json_bytes(state)
    (source/'retry-state').mkdir()
    (source/'retry-state/AAPL.json').write_bytes(retry)
    manifest = json.loads((source/'manifest.json').read_bytes())
    for entry in manifest['entries']:
        if entry['ticker'] == 'AAPL':
            entry.update(availability_type='not_available',artifact_sha256=sha256_bytes(payload))
    manifest['private_recipe_sha256'].pop('AAPL')
    manifest['retry_state_sha256'] = {'AAPL':sha256_bytes(retry)}
    manifest['artifact_tree_sha256'] = artifact_tree_sha256(manifest['entries'])
    counts = Counter(entry['availability_type'] for entry in manifest['entries'])
    manifest['availability_counts'] = {key:counts[key] for key in manifest['availability_counts']}
    (source/'manifest.json').write_bytes(canonical_json_bytes(manifest))
    staged = store.stage_catalog(source)
    assert load_retry_states(staged,store.registry)['AAPL']['recipe'] == recipe
    assert staged.entry_by_ticker['AAPL'].availability_type == 'not_available'
    (staged.root/'retry-state/AAPL.json').write_text('{}')
    with pytest.raises(CatalogIntegrityError,match='retry state hash'):
        load_retry_states(staged,store.registry)
    manifest.pop('retry_state_sha256')
    (source/'manifest.json').write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(CatalogIntegrityError,match='missing its retry state'):
        store.stage_catalog(source)
