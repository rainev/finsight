from __future__ import annotations

import json
from pathlib import Path
import shutil
import threading

import pytest

from app.us_valuation.refresh_group_verification import (
    DependencyClosureError,
    VerificationIntegrityError,
    dependency_closure,
    freeze_manifest,
    make_worker_specs,
    materialize_implementation_snapshot,
    partition_tickers,
    partition_dependency_components,
    reduce_worker_results,
    run_worker,
    run_workers,
)


def _runtime(tmp_path: Path, *, unknown_peer: bool = False) -> tuple[Path, list[Path]]:
    runtime = tmp_path / "runtime"
    (runtime / "baseline").mkdir(parents=True)
    (runtime / "baseline" / "manifest.json").write_text('{"baseline": true}\n')
    registry = {
        "schema_version": "test-registry",
        "baseline_manifest_sha256": "baseline",
        "entries": [
            {"ticker": ticker, "cik": f"000000000{index}", "batch": index}
            for index, ticker in enumerate(("AAA", "BBB", "CCC", "DDD"), start=1)
        ],
    }
    policies = {
        "AAA": {"source_peers": [{"ticker": "MISSING", "cik": "0000000999"}]} if unknown_peer else {"source_peers": [{"ticker": "BBB", "cik": "0000000002"}]},
        "BBB": {"source_peers": []},
        "CCC": {"source_peers": []},
        "DDD": {"source_peers": []},
    }
    (runtime / "registry.json").write_text(json.dumps(registry, sort_keys=True) + "\n")
    (runtime / "refresh-policies.json").write_text(json.dumps(policies, sort_keys=True) + "\n")
    (runtime / "recipes").mkdir()
    for ticker in ("AAA", "BBB", "CCC", "DDD"):
        (runtime / "recipes" / f"{ticker}.json").write_text(json.dumps({"ticker": ticker}) + "\n")
    implementation = tmp_path / "implementation.py"
    implementation.write_text("# uncommitted implementation bytes\n")
    return runtime, [implementation]


def _manifest(tmp_path: Path, tickers=("AAA", "CCC", "DDD")):
    runtime, implementation = _runtime(tmp_path)
    return runtime, implementation, freeze_manifest(runtime, tickers, implementation_paths=implementation)


def _verifier(runtime: Path, tickers, manifest):
    return {
        "rows": [{"ticker": ticker, "status": "cached_source_bound", "reason": "fixture"} for ticker in tickers],
        "timings": {"prepare": 0.01, "source": 0.02, "calc": 0.03, "verify": 0.04},
    }


def test_partition_is_deterministic_and_never_exceeds_two_workers():
    assert partition_tickers(["DDD", "AAA", "CCC", "BBB", "AAA"]) == [("AAA", "BBB"), ("CCC", "DDD")]
    assert partition_tickers(["BBB", "AAA"], max_workers=2) == [("AAA",), ("BBB",)]
    assert partition_tickers(["AAA"], max_workers=2) == [("AAA",)]
    with pytest.raises(ValueError, match="1 or 2"):
        partition_tickers(["AAA"], max_workers=3)


def test_dependency_closure_adds_declared_peer_and_fails_unknown_dependency(tmp_path: Path):
    runtime, implementation = _runtime(tmp_path)
    registry = json.loads((runtime / "registry.json").read_text())
    policies = json.loads((runtime / "refresh-policies.json").read_text())
    closure = dependency_closure(["AAA"], registry, policies)
    assert closure["tickers"] == ["AAA", "BBB"]
    assert closure["source_peers"] == {"AAA": ["BBB"], "BBB": []}
    manifest=freeze_manifest(runtime,['AAA','CCC','DDD'],implementation_paths=implementation)
    groups=partition_dependency_components(manifest)
    assert any({'AAA','BBB'}<=set(group) for group in groups)

    unknown_runtime, _ = _runtime(tmp_path / "unknown", unknown_peer=True)
    with pytest.raises(DependencyClosureError, match="broader recheck"):
        freeze_manifest(unknown_runtime, ["AAA"], implementation_paths=implementation)
    unknown_registry = json.loads((unknown_runtime / "registry.json").read_text())
    unknown_policies = json.loads((unknown_runtime / "refresh-policies.json").read_text())
    marked = dependency_closure(["AAA"], unknown_registry, unknown_policies, allow_broader_recheck=True)
    assert marked["broader_recheck"][0]["peer_ticker"] == "MISSING"


def test_workers_reduce_once_per_company_and_preserve_timing(tmp_path: Path):
    runtime, implementation, manifest = _manifest(tmp_path)
    output = tmp_path / "workers"
    specs = make_worker_specs(manifest, output)
    reports = [run_worker(spec, manifest, runtime, verifier=_verifier) for spec in specs]
    report = reduce_worker_results(
        manifest,
        reports,
        tmp_path / "reports",
        runtime_root=runtime,
        implementation_paths=implementation,
    )
    assert report["expected_tickers"] == ["AAA", "BBB", "CCC", "DDD"]
    assert report["counts"] == {"cached_source_bound": 4}
    assert report['registry_sha256']==manifest['registry_sha256']
    assert report['policy_sha256']==manifest['policy_sha256']
    assert report["timings"]["source"] == pytest.approx(0.04)
    assert [row["ticker"] for row in report["rows"]] == report["expected_tickers"]
    # The reducer's logical output is stable regardless of worker completion
    # order because workers and rows are sorted by their identifiers/tickers.
    reverse = reduce_worker_results(
        manifest,
        list(reversed(reports)),
        tmp_path / "reports-reverse",
        runtime_root=runtime,
        implementation_paths=implementation,
    )
    assert reverse["expected_tickers"] == report["expected_tickers"]
    assert reverse["rows"] == report["rows"]
    assert reverse["counts"] == report["counts"]
    assert reverse['report_sha256']==report['report_sha256']


def test_manifest_is_deterministic_for_identical_bytes(tmp_path: Path):
    runtime,implementation=_runtime(tmp_path)
    first=freeze_manifest(runtime,['AAA','CCC'],implementation_paths=implementation)
    second=freeze_manifest(runtime,['CCC','AAA'],implementation_paths=implementation)
    assert first==second


def test_manifest_freezes_complete_catalog_membership(tmp_path: Path):
    runtime,implementation=_runtime(tmp_path)
    artifacts=runtime/'baseline'/'artifacts';artifacts.mkdir()
    for ticker in ('AAA','BBB','CCC','DDD'):(artifacts/f'{ticker}.json').write_text(ticker)
    manifest=freeze_manifest(runtime,['CCC'],implementation_paths=implementation)
    keys=set(manifest['input_files'])
    assert 'baseline/artifacts/CCC.json' in keys
    assert {'baseline/artifacts/AAA.json','baseline/artifacts/CCC.json','baseline/artifacts/DDD.json'} <= keys


def test_uncommitted_implementation_is_materialized_and_reused(tmp_path: Path):
    runtime,implementation=_runtime(tmp_path);project=tmp_path/'project';source=project/'backend/app/us_valuation/example.py';source.parent.mkdir(parents=True);source.write_text('# uncommitted\n')
    manifest=freeze_manifest(runtime,['AAA'],implementation_paths=[source]);manifest['implementation_root']=str(project.resolve());manifest['manifest_sha256']=__import__('app.us_valuation.refresh_group_verification',fromlist=['manifest_sha256']).manifest_sha256(manifest)
    snapshot=materialize_implementation_snapshot(manifest,tmp_path/'output')
    assert (snapshot/'backend/app/us_valuation/example.py').read_text()=='# uncommitted\n'
    source.write_text('# later unrelated working copy edit\n')
    assert materialize_implementation_snapshot(manifest,tmp_path/'output')==snapshot


def test_run_workers_overlaps_two_isolated_workers(tmp_path: Path):
    runtime, implementation, manifest = _manifest(tmp_path)
    specs = make_worker_specs(manifest, tmp_path / "parallel")
    barrier = threading.Barrier(2)

    def concurrent_verifier(staged_root, tickers, frozen_manifest):
        barrier.wait(timeout=2)
        return {"rows": [{"ticker": ticker, "status": "ok"} for ticker in tickers]}

    reports = run_workers(specs, manifest, runtime, verifier=concurrent_verifier)
    assert [path.parent.name for path in reports] == ["worker-01", "worker-02"]


def test_reducer_rejects_duplicate_missing_and_tampered_workers(tmp_path: Path):
    runtime, implementation, manifest = _manifest(tmp_path)
    specs = make_worker_specs(manifest, tmp_path / "workers")
    reports = [run_worker(spec, manifest, runtime, verifier=_verifier) for spec in specs]
    kwargs = {"runtime_root": runtime, "implementation_paths": implementation}
    with pytest.raises(VerificationIntegrityError, match="duplicate worker"):
        reduce_worker_results(manifest, [reports[0], reports[0]], tmp_path / "duplicate", **kwargs)
    with pytest.raises(VerificationIntegrityError, match="coverage mismatch"):
        reduce_worker_results(manifest, [reports[0]], tmp_path / "missing", **kwargs)

    result_path = reports[0].parent / "results" / "AAA.json"
    result_path.write_bytes(result_path.read_bytes() + b"tampered")
    with pytest.raises(VerificationIntegrityError, match="result hash mismatch"):
        reduce_worker_results(manifest, reports, tmp_path / "tampered", **kwargs)


def test_manifest_rejects_input_or_implementation_drift(tmp_path: Path):
    runtime, implementation, manifest = _manifest(tmp_path, tickers=("AAA",))
    specs = make_worker_specs(manifest, tmp_path / "workers", max_workers=1)
    reports = [run_worker(specs[0], manifest, runtime, verifier=_verifier)]
    recipe_path = runtime / "recipes" / "AAA.json"
    original_recipe = recipe_path.read_bytes()
    recipe_path.write_text('{"ticker":"AAA","changed":true}\n')
    with pytest.raises(VerificationIntegrityError, match="input hash mismatch"):
        reduce_worker_results(manifest, reports, tmp_path / "drift", runtime_root=runtime, implementation_paths=implementation)

    # Restore the input and tamper the uncommitted implementation bytes; the
    # reducer still refuses the old worker result.
    recipe_path.write_bytes(original_recipe)
    implementation[0].write_text("# changed bytes\n")
    with pytest.raises(VerificationIntegrityError, match="implementation hash mismatch"):
        reduce_worker_results(manifest, reports, tmp_path / "drift-code", runtime_root=runtime, implementation_paths=implementation)
