#!/usr/bin/env python3
"""Operational UAT for an isolated RefreshCatalogStore runtime.

This driver exercises catalog staging, private-recipe integrity, CAS
activation, reader reload, and rollback against the real frozen 440-entry
baseline.  It never touches the production runtime, the tracked serving
catalog, cloud services, or Git state.  Run with ``--execute`` only after
reviewing the command and output root.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import uuid
import os
import subprocess
import time
import socket
from urllib.request import Request, urlopen
from collections import Counter


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.catalog import canonical_json_bytes, load_active_catalog, load_catalog_version, sha256_bytes, artifact_tree_sha256, CatalogIntegrityError
from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.calculator import baseline_version
from app.us_valuation.refresh_job import refreshed_public, refreshed_recipe_version, _unavailable
from app.us_valuation.refresh_bindings import bind_current_recipe
from app.us_valuation.refresh_catalog_store import (  # noqa: E402
    FROZEN_REGISTRY_COUNT,
    RefreshCatalogStore,
    load_frozen_registry,
    load_retry_states,
)


BASELINE = ROOT / "output/us-refresh-runtime/baseline"
REGISTRY = ROOT / "output/us-refresh-runtime/registry.json"
RECIPES = ROOT / "output/us-refresh-runtime/recipes"
FORBIDDEN_ROOT_NAMES = {
    "us-refresh-runtime",
    "us-refresh-uat-catalogs",
    "catalogs",
}


def _fresh_root(requested: Path | None) -> Path:
    if requested is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        requested = ROOT / "output" / f"us-refresh-operational-uat-{stamp}-{uuid.uuid4().hex[:8]}"
    path = requested.resolve()
    if path.parent != (ROOT/'output').resolve() or not path.name.startswith('us-refresh-operational-uat-'):
        raise ValueError('UAT root must be a new direct child of project output with the operational UAT prefix')
    if path.exists():
        raise ValueError(f"refusing to reuse existing UAT root: {path}")
    if path.name in FORBIDDEN_ROOT_NAMES or "us-refresh-runtime" in path.name or "us-refresh-uat-catalogs" in path.name:
        raise ValueError(f"refusing unsafe production-like UAT root: {path}")
    if "operational-uat" not in path.name:
        raise ValueError("UAT root name must contain operational-uat")
    if path == (ROOT / "backend/app/data/us_valuation_catalogs").resolve():
        raise ValueError("refusing tracked serving catalog root")
    return path


def _prepare_candidate(root: Path, proof_path: Path) -> tuple[Path, str, float]:
    ticker = proof_path.stem
    if ticker not in {entry['ticker'] for entry in json.loads(REGISTRY.read_bytes())['entries']}:
        raise ValueError('source proof ticker is outside the frozen registry')
    predecessor = root / "sources" / "predecessor"
    candidate = root / "sources" / "successor"
    shutil.copytree(BASELINE, predecessor)
    shutil.copytree(BASELINE, candidate)
    shutil.copytree(RECIPES, candidate / "recipes")

    if not proof_path.resolve().is_relative_to((ROOT/'output/us-refresh-runtime/source-validation').resolve()) or proof_path.suffix != '.json':
        raise ValueError('proof must be an existing source-validation receipt')
    proof_bytes = proof_path.read_bytes()
    proof_report = json.loads((proof_path.parent/'report.json').read_bytes())
    if proof_report['evidence_sha256'].get(ticker) != sha256_bytes(proof_bytes):
        raise ValueError('AAPL source proof hash mismatch')
    proof = json.loads(proof_bytes)
    recipe = proof['recipe']
    if recipe['ticker'] != ticker:
        raise ValueError('source proof recipe identity mismatch')
    valued = evaluate_recipe(recipe)
    if valued['range'] != proof['result']['range']:
        raise ValueError('AAPL source proof calculation drift')
    original = json.loads((candidate/'artifacts'/f'{ticker}.json').read_bytes())
    public = refreshed_public(original,recipe,valued,proof['ledger'],proof['ledger']['frozen_cutoff'])
    recipe['baseline_version'] = baseline_version(public)
    recipe['recipe_version'] = 'OPERATIONAL-UAT-' + sha256_bytes(proof_bytes)[:24]
    (candidate/'artifacts'/f'{ticker}.json').write_bytes(canonical_json_bytes(public))
    (candidate/'recipes'/f'{ticker}.json').write_bytes(canonical_json_bytes(recipe))

    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    predecessor_version = manifest["catalog_version"]
    manifest["catalog_version"] = f"REFRESH-OPERATIONAL-UAT-{root.name.rsplit('-', 1)[-1]}"
    manifest["base_catalog_version"] = predecessor_version
    for entry in manifest['entries']:
        if entry['ticker'] == ticker:
            entry['artifact_sha256'] = sha256_bytes((candidate/'artifacts'/f'{ticker}.json').read_bytes())
            entry['availability_type'] = public['availability_type']
    manifest['artifact_tree_sha256'] = artifact_tree_sha256(manifest['entries'])
    counts = Counter(entry['availability_type'] for entry in manifest['entries'])
    manifest['availability_counts'] = {key:counts[key] for key in manifest['availability_counts']}
    hashes = {
        path.stem: sha256_bytes(path.read_bytes())
        for path in sorted((candidate / "recipes").glob("*.json"))
    }
    manifest["private_recipe_sha256"] = hashes
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return candidate, hashes[ticker],valued['range']['base']


def _serve_worker(root: Path, port: int) -> None:
    if root.resolve().parent != (ROOT/'output').resolve() or not root.name.startswith('us-refresh-operational-uat-') or not (root/'uat-fixture.json').is_file():
        raise ValueError('worker requires a previously prepared isolated UAT root')
    from verify_refresh_persistence import configure_database
    configure_database()
    os.environ['FINSIGHT_US_REFRESH_ROOT'] = str(root.resolve())
    os.environ['FINSIGHT_US_RECIPE_ROOT'] = str(RECIPES)
    os.environ['CLIENT_URL'] = 'http://localhost:4178'
    from app.main import app
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=port)


def _http(port, path, body=None, token=None):
    headers = {'Content-Type':'application/json'}
    if token: headers['Authorization'] = f'Bearer {token}'
    request = Request(f'http://127.0.0.1:{port}/api'+path,
        data=None if body is None else json.dumps(body).encode(),headers=headers)
    with urlopen(request,timeout=5) as response:
        return json.load(response)


def run(root: Path, proof_path: Path, *, retry_recovery: bool = False) -> dict:
    ticker = proof_path.stem
    if retry_recovery:
        proof = json.loads(proof_path.read_bytes())
        if not proof.get('source_capture', {}).get('acquisition_id'):
            raise ValueError('retry recovery requires a frozen live-acquisition proof, not an offline packet check')
    root = _fresh_root(root)
    if not BASELINE.is_dir() or not REGISTRY.is_file() or not RECIPES.is_dir():
        raise FileNotFoundError("real frozen baseline, registry, or private recipes are unavailable")
    root.mkdir(parents=True)
    (root/'uat-fixture.json').write_bytes(canonical_json_bytes({'scope':'isolated operational UAT fixture only','production_approval':False}))
    shutil.copy2(REGISTRY, root / "registry.json")
    registry_value = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry = load_frozen_registry(root / "registry.json", expected_count=FROZEN_REGISTRY_COUNT)
    candidate_source, aapl_recipe_hash, expected_base = _prepare_candidate(root,proof_path)
    store = RefreshCatalogStore(root/'catalogs', frozen_registry=root / "registry.json", expected_registry_count=FROZEN_REGISTRY_COUNT)
    store.runtime_root.mkdir()
    approval_fingerprint = sha256_bytes(b"operational-uat-policy-v1")
    store.approved_policy_path.write_bytes(
        canonical_json_bytes(
            {
                "approved": True,
                "status": "approved",
                "policy_fingerprint": approval_fingerprint,
                "registry_sha256": registry.registry_sha256,
                "scope": "isolated operational UAT fixture only",
            }
        )
    )
    predecessor_source = root / "sources" / "predecessor"
    predecessor = store.stage_catalog(predecessor_source)
    predecessor_activation = store.activate(
        predecessor,
        policy_fingerprint=approval_fingerprint,
        activated_at=datetime.now(timezone.utc).isoformat(),
        expected_active_manifest_sha256=None,
        reason="operational UAT predecessor activation",
    )
    reader = store.reader()
    pinned = reader.get_snapshot()
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0))
        port = reservation.getsockname()[1]
    log = (root/'http-worker.log').open('wb')
    worker = subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--http-worker-root',str(root),'--port',str(port)],stdout=log,stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic()+30
        while True:
            if worker.poll() is not None:
                raise RuntimeError(f'isolated HTTP worker failed; inspect {root / "http-worker.log"}')
            try:
                auth = _http(port,'/auth/login',{'email':'refresh-uat@example.com','password':'Local-UAT-only-20260908!'})
                break
            except OSError:
                if time.monotonic() >= deadline: raise
                time.sleep(.1)
        token = auth['access_token']
        before_http = _http(port,f'/us-valuations/{ticker}',token=token)
        if before_http.get('catalog_version') != predecessor.catalog_version:
            raise AssertionError('HTTP worker did not load isolated predecessor')
        return _exercise_successor(root,store,reader,pinned,predecessor,candidate_source,approval_fingerprint,
            predecessor_activation,registry,aapl_recipe_hash,expected_base,port,token,before_http,ticker,
            proof_path if retry_recovery else None)
    finally:
        worker.terminate()
        try: worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill(); worker.wait(timeout=5)
        log.close()


def _exercise_successor(root,store,reader,pinned,predecessor,candidate_source,approval_fingerprint,
        predecessor_activation,registry,aapl_recipe_hash,expected_base,port,token,before_http,ticker,retry_proof=None):
    successor = store.stage_catalog(candidate_source)
    successor_activation = store.activate(
        successor,
        policy_fingerprint=approval_fingerprint,
        activated_at=datetime.now(timezone.utc).isoformat(),
        expected_active_manifest_sha256=predecessor_activation["pointer"]["manifest_sha256"],
        reason="operational UAT successor CAS activation",
    )
    reloaded = reader.get_snapshot()
    after_http = _http(port,f'/us-valuations/{ticker}',token=token)
    assert reloaded.catalog_version == successor.catalog_version and pinned.catalog_version == predecessor.catalog_version
    assert after_http['catalog_version'] == successor.catalog_version
    assert after_http['scenario_range']['base'] == expected_base
    # A valid refresh may preserve the base case while independently changing
    # one or both scenario bounds.  Prove the successor artifact changed as a
    # whole instead of requiring a synthetic base-value movement.
    assert after_http['scenario_range'] != before_http['scenario_range']
    pointer_before_stale = store.active_pointer_path.read_bytes()
    try:
        store.activate(predecessor,policy_fingerprint=approval_fingerprint,activated_at=datetime.now(timezone.utc).isoformat(),
                       expected_active_manifest_sha256=predecessor.manifest_sha256)
        raise AssertionError('stale CAS activation was accepted')
    except CatalogIntegrityError:
        assert store.active_pointer_path.read_bytes() == pointer_before_stale
    rollback = store.rollback(
        successor_activation["receipt_path"],
        rolled_back_at=datetime.now(timezone.utc).isoformat(),
        reason="operational UAT rollback proof",
    )
    active_after_rollback = load_active_catalog(store.runtime_root)
    rollback_http = _http(port,f'/us-valuations/{ticker}',token=token)
    assert active_after_rollback.catalog_version == predecessor.catalog_version
    assert rollback_http['catalog_version'] == predecessor.catalog_version
    assert rollback_http['scenario_range'] == before_http['scenario_range']
    report = {
        "status": "operational_uat_verified",
        "scope": "isolated runtime only; not a complete universe financial refresh or production approval",
        "runtime_root": str(root),
        "registry_count": len(registry.entries),
        "private_recipe_count": len(successor.manifest["private_recipe_sha256"]),
        "source_bound_candidate": {"ticker": ticker, "recipe_sha256": aapl_recipe_hash},
        "predecessor_version": predecessor.catalog_version,
        "successor_version": successor.catalog_version,
        "reader_pinned_version": pinned.catalog_version,
        "reader_reloaded_version": reloaded.catalog_version,
        "rollback_version": active_after_rollback.catalog_version,
        "activation_receipt": str(predecessor_activation["receipt_path"]),
        "successor_receipt": str(successor_activation["receipt_path"]),
        "rollback_receipt": str(rollback["receipt_path"]),
        "http_worker": {'before':before_http['scenario_range'],'after':after_http['scenario_range'],'rollback':rollback_http['scenario_range'],
                        'source':'real FastAPI process, isolated existing UAT database','stale_CAS_rejected':True},
        "production_runtime_touched": False,
    }
    if retry_proof is not None:
        report['retry_recovery'] = _exercise_retry_recovery(root,store,successor,approval_fingerprint,port,token,retry_proof)
    (root / "uat-report.json").write_bytes(canonical_json_bytes(report))
    return report


def _write_transition_manifest(source, manifest, ticker, public):
    payload = canonical_json_bytes(public)
    (source/'artifacts'/f'{ticker}.json').write_bytes(payload)
    for row in manifest['entries']:
        if row['ticker'] == ticker:
            row.update(artifact_sha256=sha256_bytes(payload),availability_type=public['availability_type'])
    manifest['artifact_tree_sha256'] = artifact_tree_sha256(manifest['entries'])
    counts = Counter(row['availability_type'] for row in manifest['entries'])
    manifest['availability_counts'] = {key:counts[key] for key in manifest['availability_counts']}
    (source/'manifest.json').write_bytes(canonical_json_bytes(manifest))


def _exercise_retry_recovery(root,store,numeric,approval,port,token,proof_path):
    """Inject an operational unavailable state, then bind real captured evidence."""
    from scripts.verify_us_refresh_sources import acquired_packet
    ticker = proof_path.stem
    proof = json.loads(proof_path.read_bytes())
    report = json.loads((proof_path.parent/'report.json').read_bytes())
    policy_hash = report['policy_sha256']
    if len(policy_hash) != 64 or any(c not in '0123456789abcdef' for c in policy_hash):
        raise ValueError('invalid source proof policy hash')
    runtime = ROOT/'output/us-refresh-runtime'
    policy_raw = (runtime/'policy-history'/f'{policy_hash}.json').read_bytes()
    if sha256_bytes(policy_raw) != policy_hash:
        raise ValueError('source proof policy history drift')
    policy = json.loads(policy_raw)[ticker]
    registry = json.loads(REGISTRY.read_bytes())
    entry = next(row for row in registry['entries'] if row['ticker'] == ticker)
    packet, provenance = acquired_packet(runtime,proof['source_capture']['acquisition_id'],entry,proof['ledger']['frozen_cutoff'])
    if provenance['wrapper_sha256'] != proof['source_capture']['wrapper_sha256']:
        raise ValueError('retry source differs from the validated source proof')
    if policy.get('source_peers'):
        raise ValueError('this bounded retry UAT requires a standalone issuer source')
    active = store.reader().get_snapshot()
    store.activate(numeric,policy_fingerprint=approval,activated_at=datetime.now(timezone.utc).isoformat(),
                   expected_active_manifest_sha256=active.manifest_sha256,reason='isolated retry UAT numeric predecessor')
    original = json.loads(numeric.verify_artifact(ticker).read_bytes())
    recipe = json.loads((numeric.root/'recipes'/f'{ticker}.json').read_bytes())
    source = root/'sources'/'unavailable'
    shutil.copytree(numeric.root,source)
    unavailable = _unavailable(original,'Simulated missing-input condition for operational UAT; not a company event.',cutoff=proof['ledger']['frozen_cutoff'])
    state_raw = canonical_json_bytes({'schema_version':'FINSIGHT-RETRY-STATE-1','recipe':recipe,'public_template':original})
    (source/'retry-state').mkdir(exist_ok=True)
    (source/'retry-state'/f'{ticker}.json').write_bytes(state_raw)
    (source/'recipes'/f'{ticker}.json').unlink()
    manifest = json.loads((source/'manifest.json').read_bytes())
    manifest.update(catalog_version=numeric.catalog_version+'-UNAVAILABLE',base_catalog_version=numeric.catalog_version)
    manifest['private_recipe_sha256'].pop(ticker)
    manifest['retry_state_sha256'] = {ticker:sha256_bytes(state_raw)}
    _write_transition_manifest(source,manifest,ticker,unavailable)
    unavailable_catalog = store.stage_catalog(source)
    store.activate(unavailable_catalog,policy_fingerprint=approval,activated_at=datetime.now(timezone.utc).isoformat(),
        expected_active_manifest_sha256=numeric.manifest_sha256,reason='isolated injected source-insufficient state')
    unavailable_http = _http(port,f'/us-valuations/{ticker}',token=token)
    assert unavailable_http['availability_type'] == 'not_available'
    assert all(unavailable_http['scenario_range'][case] is None for case in ('low','base','high'))
    assert not unavailable_http.get('sensitivities')
    assert not unavailable_http.get('scenarios')
    assert 'Historical last successful reference only' in unavailable_http['source_financial_statement']['note']
    state = load_retry_states(store.reader().get_snapshot(),store.registry)[ticker]
    updated,ledger = bind_current_recipe({**entry,'refresh_policy':policy},state['recipe'],packet,proof['ledger']['frozen_cutoff'])
    updated['recipe_version'] = refreshed_recipe_version(updated,policy)
    valued = evaluate_recipe(updated)
    restored = refreshed_public(state['public_template'],updated,valued,ledger,proof['ledger']['frozen_cutoff'])
    updated['baseline_version'] = baseline_version(restored)
    recovered_source = root/'sources'/'recovered'
    shutil.copytree(source,recovered_source)
    (recovered_source/'retry-state'/f'{ticker}.json').unlink()
    recipe_raw = canonical_json_bytes(updated)
    (recovered_source/'recipes'/f'{ticker}.json').write_bytes(recipe_raw)
    manifest.update(catalog_version=numeric.catalog_version+'-RECOVERED',base_catalog_version=unavailable_catalog.catalog_version)
    manifest['private_recipe_sha256'][ticker] = sha256_bytes(recipe_raw)
    manifest['retry_state_sha256'] = {}
    _write_transition_manifest(recovered_source,manifest,ticker,restored)
    recovered = store.stage_catalog(recovered_source)
    store.activate(recovered,policy_fingerprint=approval,activated_at=datetime.now(timezone.utc).isoformat(),
        expected_active_manifest_sha256=unavailable_catalog.manifest_sha256,reason='isolated recovery from retained template and real evidence')
    recovered_http = _http(port,f'/us-valuations/{ticker}',token=token)
    assert recovered_http['availability_type'] != 'not_available'
    assert recovered_http['scenario_range']['base'] == valued['range']['base']
    assert ticker not in load_retry_states(store.reader().get_snapshot(),store.registry)
    return {'unavailable_state_injected':True,'financial_source':'real captured filing',
        'unavailable_numeric_surfaces_cleared':True,'unavailable_source_label':'historical last successful reference',
        'unavailable_version':unavailable_catalog.catalog_version,'recovered_version':recovered.catalog_version,
        'restored_base':recovered_http['scenario_range']['base'],'private_template_verified':True,
        'production_runtime_touched':False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="new isolated directory; must contain operational-uat in its name")
    parser.add_argument("--execute", action="store_true", help="perform the isolated UAT; otherwise only print the planned scope")
    parser.add_argument('--source-proof','--aapl-proof',dest='aapl_proof',type=Path,help='Existing hashed company source-validation evidence JSON')
    parser.add_argument('--retry-recovery',action='store_true',help='Also exercise injected unavailability and recovery from retained private state')
    parser.add_argument('--http-worker-root',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--port',type=int,help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.http_worker_root:
        _serve_worker(args.http_worker_root,args.port)
        return 0
    root = _fresh_root(args.root)
    if not args.execute:
        print(json.dumps({"status": "not_run", "planned_root": str(root), "requires": "--execute", "scope": "isolated operational UAT only"}, sort_keys=True))
        return 0
    if args.aapl_proof is None:
        parser.error('--execute requires --aapl-proof')
    print(json.dumps(run(root,args.aapl_proof,retry_recovery=args.retry_recovery), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
