from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from app.us_valuation import refresh_job
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.calculator import baseline_version
from app.us_valuation.catalog import canonical_json_bytes, load_catalog_version
from app.us_valuation.refresh_catalog_store import REFRESH_REGISTRY_SCHEMA, load_frozen_registry


ROOT = Path(__file__).resolve().parents[2]
RESET = ROOT / "backend/app/data/us_valuation_catalogs/US-RESET-2026-08-14-B01-B10-1.0"


def test_recipe_version_tracks_semantics_without_churning_on_cutoff():
    recipe = {'schema_version':'test','ticker':'AAPL','scenarios':{'base':{'value':100}},
              'editable':{'discount_rate':{'min':.04}},'recipe_version':'old','evidence_cutoff':'2026-08-14'}
    policy = {'version':'policy-1'}
    version = refresh_job.refreshed_recipe_version(recipe,policy)
    assert refresh_job.refreshed_recipe_version({**recipe,'recipe_version':version,'evidence_cutoff':'2026-09-08'},policy) == version
    assert refresh_job.refreshed_recipe_version(recipe,{'version':'policy-2'}) != version
    assert refresh_job.refreshed_recipe_version({**recipe,'editable':{'discount_rate':{'min':.05}}},policy) != version


def test_source_peer_is_pinned_to_same_snapshot_and_cannot_override_selection(tmp_path):
    registry = {'entries':[{'ticker':'STX','cik':'0001137789'}]}
    policy = {'source_peers':[{'ticker':'STX','cik':'0001137789'}]}
    peer = {'submissions':{'cik':1137789},'companyfacts':{'cik':1137789},'cutoff':'2026-08-14',
            '_selected_controlling_filing':{'accessionNumber':'untrusted-override'}}
    output = refresh_job.attach_source_peers(tmp_path,{'issuer':'WDC'},policy,{'STX':peer},registry,'2026-08-14')
    assert output['source_peers']['STX']['cutoff'] == '2026-08-14'
    assert '_selected_controlling_filing' not in output['source_peers']['STX']
    assert '_selected_controlling_filing' in peer
    for packets in ({}, {'STX':{**peer,'cutoff':'2026-05-01'}}, {'STX':{**peer,'companyfacts':{'cik':1}}}):
        failed = refresh_job.attach_source_peers(tmp_path,{'issuer':'WDC'},policy,packets,registry,'2026-08-14')
        assert failed['acquisition_failed'] == 'required_peer_source_unavailable'
        assert failed['peer_ticker'] == 'STX'
    with pytest.raises(RuntimeError,match='registry binding'):
        refresh_job.attach_source_peers(tmp_path,{'issuer':'WDC'},policy,{'STX':peer},{'entries':[]},'2026-08-14')


def test_runtime_contact_configuration_and_environment_override(tmp_path,monkeypatch):
    monkeypatch.delenv('SEC_USER_AGENT',raising=False)
    (tmp_path/'runtime-config.json').write_text(json.dumps({'schema_version':'FINSIGHT-US-REFRESH-RUNTIME-1','sec_user_agent':'FinSight contact@example.invalid'}))
    assert refresh_job.configured_sec_user_agent(tmp_path) == 'FinSight contact@example.invalid'
    monkeypatch.setenv('SEC_USER_AGENT','Other approved contact@example.invalid')
    assert refresh_job.configured_sec_user_agent(tmp_path).startswith('Other approved')
    monkeypatch.setenv('SEC_USER_AGENT','FinSight contact@example.invalid\nInjected: header')
    with pytest.raises(ValueError,match='monitored contact'):
        refresh_job.configured_sec_user_agent(tmp_path)


def _tiny_runtime(tmp_path: Path, *, cik: str | None = None) -> tuple[Path, dict]:
    runtime = tmp_path / "refresh-runtime"
    shutil.copytree(RESET, runtime / "baseline")
    baseline = load_catalog_version(runtime / "baseline")
    entry = next(row for row in baseline.entries if row.ticker == "AAPL")
    registry = {
        "schema_version": REFRESH_REGISTRY_SCHEMA,
        "baseline_catalog_version": baseline.catalog_version,
        "baseline_manifest_sha256": baseline.manifest_sha256,
        "entries": [
            {
                "ticker": entry.ticker,
                "cik": cik or entry.cik,
                "batch": entry.batch,
                "availability_type": entry.availability_type,
                "baseline_sha256": entry.artifact_sha256,
                "controlling_filing": {},
                "forecast_mode": "consolidated",
                "primary_model": "fcff_dcf",
                "recipe_status": "not_migrated",
                "source_audit": entry.source_audit,
            }
        ],
    }
    (runtime / "registry.json").write_bytes(canonical_json_bytes(registry))
    (runtime / "refresh-policies.json").write_bytes(canonical_json_bytes({}))
    return runtime, registry


def test_predecessor_artifact_is_retained_on_known_outage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, registry = _tiny_runtime(tmp_path)
    source_file = tmp_path / "evidence.json"
    source_file.write_bytes(
        canonical_json_bytes({"cutoff": "2026-09-08", "packets": {}})
    )
    baseline_public = sanitize_public_artifact(
        json.loads((runtime / "baseline" / "artifacts" / "AAPL.json").read_text())
    )
    target = baseline_public["scenario_range"]
    recipe = {
        "schema_version": "FINSIGHT-CALCULATION-RECIPE-1",
        "ticker": "AAPL",
        "baseline_version": baseline_version(baseline_public),
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
            for name, target_name in (("bear", "low"), ("base", "base"), ("bull", "high"))
        },
    }
    (runtime / "recipes").mkdir()
    (runtime / "recipes" / "AAPL.json").write_bytes(canonical_json_bytes(recipe))

    class Candidate:
        catalog_version = "TEST-CANDIDATE"
        manifest_sha256 = "b" * 64

    real_baseline = load_catalog_version(runtime / "baseline")

    class MiniBaseline:
        root = real_baseline.root
        catalog_version = real_baseline.catalog_version
        manifest_sha256 = real_baseline.manifest_sha256
        manifest = {
            **real_baseline.manifest,
            "entries": [real_baseline.manifest["entries"][0]],
            "artifact_count": 1,
        }
        entries = (real_baseline.entries[0],)

        @staticmethod
        def verify_artifact(ticker: str) -> Path:
            return real_baseline.verify_artifact(ticker)

    class Store:
        def __init__(self, *_: object, **__: object) -> None:
            self.active_pointer_path = tmp_path / "active-pointer"
            self.active_pointer_path.touch()

        def reader(self) -> object:
            return type("Reader", (), {"get_snapshot": lambda _: MiniBaseline()})()

        def stage_catalog(self, _: Path) -> Candidate:
            return Candidate()

        def activate(self, *_: object, **__: object) -> None:
            raise AssertionError("stage mode must not activate")

    monkeypatch.setattr(refresh_job, "RefreshCatalogStore", Store)
    # This small orchestration unit test is not migration acceptance evidence.
    monkeypatch.setattr(refresh_job, 'preflight', lambda root: {'numeric_count': 1, 'recipe_ready_count': 1, 'refresh_ready_count': 1})
    monkeypatch.setattr(
        refresh_job,
        "load_frozen_registry",
        lambda path: load_frozen_registry(path, expected_count=1),
    )
    report = refresh_job.execute(
        runtime,
        mode="stage",
        cutoff="2026-09-08",
        source_file=source_file,
    )

    run_root = runtime / "runs" / report["run_id"]
    previous = (runtime / "baseline" / "artifacts" / "AAPL.json").read_bytes()
    candidate = (run_root / "candidate" / "artifacts" / "AAPL.json").read_bytes()
    assert candidate == previous
    assert report["counts"] == {"acquisition_failed": 1}


def test_atomic_resume_rejects_drift_but_accepts_identical_replay(tmp_path: Path) -> None:
    path = tmp_path / "run" / "input.json"
    payload = b'{"run":"frozen"}\n'
    refresh_job.atomic(path, payload)
    refresh_job.atomic(path, payload)

    with pytest.raises(ValueError, match="immutable output drift"):
        refresh_job.atomic(path, b'{"run":"changed"}\n')


def test_capture_contains_unexpected_provider_corruption_per_issuer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime, registry = _tiny_runtime(tmp_path)

    class CorruptProvider:
        def __init__(self, **_: object) -> None:
            pass

        def submissions(self, _cik: str, *, refresh: bool = False) -> dict:
            raise ValueError("malformed provider payload")

        def companyfacts(self, _cik: str, *, refresh: bool = False) -> dict:
            raise AssertionError("companyfacts should not run after submissions corruption")

    monkeypatch.setattr(refresh_job, "SecClient", CorruptProvider)
    captured = refresh_job.capture(runtime, registry, "2026-09-08", "offline@example.invalid")

    failure = captured['packets']['AAPL']
    assert failure['acquisition_failed'] == 'ValueError'
    assert failure['diagnostic'] == 'malformed provider payload'
    assert failure['cause_type'] == 'ValueError'
    assert failure['http_status'] is None


def test_preflight_requires_exact_frozen_440_registry(tmp_path: Path) -> None:
    runtime, _ = _tiny_runtime(tmp_path)

    with pytest.raises(ValueError, match='440'):
        refresh_job.preflight(runtime)


def test_preflight_reconciles_registry_identity_to_predecessor(tmp_path: Path, monkeypatch) -> None:
    runtime, _ = _tiny_runtime(tmp_path, cik="0000000001")

    monkeypatch.setattr(refresh_job, 'load_frozen_registry', lambda path: load_frozen_registry(path, expected_count=1))
    with pytest.raises(ValueError, match='identity'):
        refresh_job.preflight(runtime)
