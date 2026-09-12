"""Bounded, frozen-input verification for small U.S. refresh groups.

This module deliberately sits beside (rather than inside) the refresh job.  A
group run is a diagnostic: it reads a frozen snapshot, writes into isolated
worker/report directories, and never activates or publishes a valuation.

The two important integrity properties are:

* the manifest hashes the bytes that workers are allowed to use; and
* the reducer accepts each expected ticker exactly once, after rechecking all
  manifest and worker hashes.

No network client or subprocess is used here.  The default worker adapter
calls the existing cached verifier against a copied runtime directory; tests
and callers may supply a read-only verifier callback.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


SCHEMA_VERSION = "FINSIGHT-US-REFRESH-GROUP-VERIFICATION-1"
WORKER_SCHEMA_VERSION = "FINSIGHT-US-REFRESH-GROUP-WORKER-1"
REPORT_SCHEMA_VERSION = "FINSIGHT-US-REFRESH-GROUP-REPORT-1"
MISSING_FILE = "MISSING"


class VerificationIntegrityError(ValueError):
    """Raised when a frozen group or worker result cannot be trusted."""


class DependencyClosureError(VerificationIntegrityError):
    """Raised when a declared source dependency cannot be frozen safely."""


@dataclass(frozen=True)
class WorkerSpec:
    """Serializable description of one isolated worker."""

    worker_id: str
    tickers: tuple[str, ...]
    manifest_sha256: str
    implementation_sha256: str
    input_sha256: str
    output_dir: str
    snapshot_checkout: str | None = None
    snapshot_source_index: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WORKER_SCHEMA_VERSION,
            "worker_id": self.worker_id,
            "tickers": list(self.tickers),
            "manifest_sha256": self.manifest_sha256,
            "implementation_sha256": self.implementation_sha256,
            "input_sha256": self.input_sha256,
            "output_dir": self.output_dir,
            "snapshot_checkout": self.snapshot_checkout,
            "snapshot_source_index": self.snapshot_source_index,
        }


def _canonical(value: Any) -> bytes:
    # Keep this local so the runner is usable in a minimal diagnostic Python
    # environment and does not widen the refresh job's import surface.
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    try:
        return _sha256(path.read_bytes())
    except OSError as exc:
        raise VerificationIntegrityError(f"required frozen file is unreadable: {path}") from exc


def _files_under(root: Path) -> list[Path]:
    if not root.is_dir():
        raise VerificationIntegrityError(f"required frozen directory is missing: {root}")
    return sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: path.as_posix())


def _runtime_key(root: Path, path: Path) -> str:
    """Use a stable runtime-relative key, retaining outside files explicitly."""
    root = root.resolve()
    path = path.resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return "@absolute:" + path.as_posix()


def _resolve_runtime_key(root: Path, key: str) -> Path:
    if key.startswith("@absolute:"):
        return Path(key[len("@absolute:"):])
    path = (root / key).resolve()
    if not path.is_relative_to(root.resolve()):
        raise VerificationIntegrityError(f"unsafe frozen input path: {key}")
    return path


def _hash_map(paths: Iterable[Path], *, root: Path, include_missing: bool = False) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted((Path(path) for path in paths), key=lambda item: item.as_posix()):
        key = _runtime_key(root, path)
        if not path.is_file():
            if include_missing:
                result[key] = MISSING_FILE
                continue
            raise VerificationIntegrityError(f"required frozen file is missing: {path}")
        result[key] = _file_sha256(path)
    return result


def _implementation_paths_default() -> tuple[Path, ...]:
    project_root = Path(__file__).resolve().parents[3]
    paths = [project_root / "scripts" / "verify_us_refresh_sources.py", Path(__file__)]
    app_root = project_root / "backend" / "app"
    paths.extend(sorted(app_root.rglob("*.py")))
    paths.extend(sorted((app_root/'us_valuation'/'config').rglob("*.json")))
    # Preserve order while avoiding the module being listed twice.
    return tuple(dict.fromkeys(path.resolve() for path in paths))


def _manifest_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "manifest_sha256"}


def manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """Return the digest of a manifest excluding its self-referential field."""
    return _sha256(_canonical(_manifest_payload(manifest)))


def _dependency_closure(
    selected: Iterable[str],
    registry: Mapping[str, Any],
    policies: Mapping[str, Any],
    *,
    allow_broader_recheck: bool = False,
) -> tuple[tuple[str, ...], dict[str, list[str]], list[dict[str, str]]]:
    entries = {str(row.get("ticker")): row for row in registry.get("entries", []) if isinstance(row, Mapping)}
    if not entries:
        raise VerificationIntegrityError("frozen registry has no entries")
    requested = sorted({str(ticker) for ticker in selected})
    unknown_requested = sorted(set(requested) - set(entries))
    if unknown_requested:
        raise VerificationIntegrityError(f"issuers outside frozen registry: {unknown_requested}")

    closure = set(requested)
    peer_map: dict[str, list[str]] = {}
    unknown: list[dict[str, str]] = []
    queue = list(requested)
    while queue:
        ticker = queue.pop(0)
        policy = policies.get(ticker, {})
        peers = policy.get("source_peers", []) if isinstance(policy, Mapping) else []
        if peers is None:
            peers = []
        if not isinstance(peers, list):
            raise DependencyClosureError(f"{ticker}: source_peers must be a list")
        resolved: list[str] = []
        for peer in peers:
            if not isinstance(peer, Mapping) or not isinstance(peer.get("ticker"), str) or not isinstance(peer.get("cik"), str):
                raise DependencyClosureError(f"{ticker}: malformed source peer declaration")
            peer_ticker = peer["ticker"]
            expected_cik = str(entries.get(peer_ticker, {}).get("cik", "")).zfill(10)
            declared_cik = str(peer["cik"]).zfill(10)
            if peer_ticker not in entries or expected_cik != declared_cik:
                unknown.append({"ticker": ticker, "peer_ticker": peer_ticker, "cik": declared_cik})
                continue
            resolved.append(peer_ticker)
            if peer_ticker not in closure:
                closure.add(peer_ticker)
                queue.append(peer_ticker)
        peer_map[ticker] = sorted(set(resolved))

    if unknown and not allow_broader_recheck:
        details = ", ".join(f"{row['ticker']}->{row['peer_ticker']}" for row in unknown)
        raise DependencyClosureError(f"unknown source dependency; broader recheck required: {details}")
    return tuple(sorted(closure)), {key: value for key, value in sorted(peer_map.items())}, unknown


def dependency_closure(
    selected: Iterable[str],
    registry: Mapping[str, Any],
    policies: Mapping[str, Any],
    *,
    allow_broader_recheck: bool = False,
) -> dict[str, Any]:
    """Expose the dependency calculation for planning and focused tests."""
    closure, peers, broader = _dependency_closure(
        selected, registry, policies, allow_broader_recheck=allow_broader_recheck
    )
    return {"tickers": list(closure), "source_peers": peers, "broader_recheck": broader}


def freeze_manifest(
    runtime_root: Path,
    tickers: Iterable[str],
    *,
    implementation_paths: Iterable[Path] | None = None,
    source_index: Path | None = None,
    allow_broader_recheck: bool = False,
) -> dict[str, Any]:
    """Freeze registry/policy/recipe/baseline/code bytes for one group.

    The function only reads inputs.  It records hashes of the bytes currently
    on disk, so uncommitted edits are included just like committed files.
    """
    runtime_root = Path(runtime_root).resolve()
    registry_path = runtime_root / "registry.json"
    policies_path = runtime_root / "refresh-policies.json"
    if not registry_path.is_file() or not policies_path.is_file():
        raise VerificationIntegrityError("registry.json and refresh-policies.json are required")
    try:
        registry = json.loads(registry_path.read_bytes())
        policies = json.loads(policies_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationIntegrityError("frozen registry or policies are invalid JSON") from exc
    if not isinstance(registry, Mapping) or not isinstance(policies, Mapping):
        raise VerificationIntegrityError("frozen registry and policies must be JSON objects")

    selected = tuple(sorted({str(ticker) for ticker in tickers}))
    if not selected:
        raise VerificationIntegrityError("at least one ticker is required")
    closure, peer_map, broader = _dependency_closure(
        selected, registry, policies, allow_broader_recheck=allow_broader_recheck
    )
    baseline_root = runtime_root / "baseline"
    # The catalog loader deliberately requires exact manifest/artifact
    # membership even when selected hashes are checked lazily. The complete
    # 3.7MB baseline is therefore frozen; the 5.3GB parser cache is not.
    baseline_files = _files_under(baseline_root)
    recipe_files = [runtime_root / "recipes" / f"{ticker}.json" for ticker in closure]
    source_index_path = Path(source_index).resolve() if source_index is not None else None
    if source_index_path is not None and not source_index_path.is_file():
        raise VerificationIntegrityError(f"optional source index was specified but is missing: {source_index_path}")

    input_paths = [registry_path, policies_path, *baseline_files, *recipe_files]
    if any(isinstance(policies.get(ticker),Mapping) and policies[ticker].get('cash_receipt_policy') for ticker in closure):
        for directory in (runtime_root/'source-validation-cache'/'cash-receipts',runtime_root/'normalization-events'):
            if directory.is_dir(): input_paths.extend(_files_under(directory))
    narrative_tickers=[ticker for ticker in closure if isinstance(policies.get(ticker),Mapping) and policies[ticker].get('narrative_evidence_policy')]
    if narrative_tickers:
        source_root=Path(__file__).resolve().parents[3]/'output'
        for ticker in narrative_tickers:
            receipt_path=runtime_root/'narrative-evidence'/f'{ticker}.json'
            if not receipt_path.is_file():
                raise VerificationIntegrityError(f'{ticker}: required narrative evidence receipt is missing')
            try: receipt=json.loads(receipt_path.read_bytes())
            except (OSError,json.JSONDecodeError) as exc:
                raise VerificationIntegrityError(f'{ticker}: narrative evidence receipt is invalid') from exc
            source=receipt.get('source') if isinstance(receipt,Mapping) else None
            if not isinstance(source,Mapping):
                raise VerificationIntegrityError(f'{ticker}: narrative evidence source is missing')
            input_paths.extend((receipt_path,source_root/str(source.get('package_manifest_path','')),source_root/str(source.get('document_path',''))))
    if source_index_path is not None:
        input_paths.append(source_index_path)
    input_files = _hash_map(input_paths, root=runtime_root, include_missing=True)
    implementation = tuple(Path(path).resolve() for path in (implementation_paths or _implementation_paths_default()))
    # Implementation paths intentionally remain absolute: unlike runtime
    # inputs they belong to the checkout, and an absolute key prevents a
    # copied worker runtime from accidentally resolving a different file with
    # the same basename.
    implementation_files = {
        str(path): _file_sha256(path)
        for path in sorted(dict.fromkeys(implementation), key=lambda item: item.as_posix())
    }
    input_digest = _sha256(_canonical(input_files))
    implementation_digest = _sha256(_canonical(implementation_files))
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "runtime_root": str(runtime_root),
        "registry_sha256": input_files[_runtime_key(runtime_root, registry_path)],
        "policy_sha256": input_files[_runtime_key(runtime_root, policies_path)],
        "baseline_tree_sha256": _sha256(_canonical({key: value for key, value in input_files.items() if key == "baseline/manifest.json" or key.startswith("baseline/")})),
        "requested_tickers": list(selected),
        "closure_tickers": list(closure),
        "source_peers": peer_map,
        "broader_recheck": broader,
        "input_files": input_files,
        "input_sha256": input_digest,
        "implementation_root": str(Path(__file__).resolve().parents[3]),
        "implementation_files": implementation_files,
        "implementation_sha256": implementation_digest,
        "source_index": _runtime_key(runtime_root, source_index_path) if source_index_path is not None else None,
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def _assert_manifest_self_hash(manifest: Mapping[str, Any]) -> None:
    expected = manifest.get("manifest_sha256")
    if not isinstance(expected, str) or manifest_sha256(manifest) != expected:
        raise VerificationIntegrityError("frozen manifest hash mismatch")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise VerificationIntegrityError("unsupported frozen group manifest schema")


def validate_manifest_inputs(
    manifest: Mapping[str, Any],
    runtime_root: Path | None = None,
    *,
    implementation_paths: Iterable[Path] | None = None,
) -> None:
    """Re-read every frozen byte hash before workers or reducer consume it."""
    _assert_manifest_self_hash(manifest)
    runtime = Path(runtime_root or manifest.get("runtime_root", "")).resolve()
    if not runtime.is_dir():
        raise VerificationIntegrityError(f"frozen runtime root is missing: {runtime}")
    input_files = manifest.get("input_files")
    implementation_files = manifest.get("implementation_files")
    if not isinstance(input_files, Mapping) or not isinstance(implementation_files, Mapping):
        raise VerificationIntegrityError("frozen manifest hash maps are malformed")
    current_inputs: dict[str, str] = {}
    for key, expected in input_files.items():
        path = _resolve_runtime_key(runtime, str(key))
        current_inputs[str(key)] = _file_sha256(path) if path.is_file() else MISSING_FILE
        if current_inputs[str(key)] != expected:
            raise VerificationIntegrityError(f"frozen input hash mismatch: {key}")
    if _sha256(_canonical(current_inputs)) != manifest.get("input_sha256"):
        raise VerificationIntegrityError("frozen input digest mismatch")

    # Explicit paths are useful for test callers and for a copied runtime.  If
    # omitted, the manifest's byte-addressed implementation paths are used.
    if implementation_paths is None:
        implementation_paths = [Path(key) for key in implementation_files]
    current_impl: dict[str, str] = {}
    for path in implementation_paths:
        resolved = Path(path).resolve()
        # A manifest generated by this module stores absolute implementation
        # keys.  Resolve relative test paths against the current directory.
        key = str(resolved)
        if key not in implementation_files:
            key = _runtime_key(runtime, resolved)
        expected = implementation_files.get(key)
        if expected is None:
            raise VerificationIntegrityError(f"implementation file is outside frozen manifest: {resolved}")
        current_impl[key] = _file_sha256(resolved)
        if current_impl[key] != expected:
            raise VerificationIntegrityError(f"implementation hash mismatch: {key}")
    # Ensure no frozen implementation file was silently omitted from the
    # recheck.  This also catches a tampered/short implementation_paths list.
    if set(current_impl) != set(implementation_files):
        for key, expected in implementation_files.items():
            if key in current_impl:
                continue
            path = Path(key) if str(key).startswith("/") else _resolve_runtime_key(runtime, str(key))
            actual = _file_sha256(path)
            if actual != expected:
                raise VerificationIntegrityError(f"implementation hash mismatch: {key}")
            current_impl[key] = actual
    if _sha256(_canonical(current_impl)) != manifest.get("implementation_sha256"):
        raise VerificationIntegrityError("implementation digest mismatch")


def partition_tickers(tickers: Iterable[str], max_workers: int = 2) -> list[tuple[str, ...]]:
    """Deterministically split sorted tickers into at most two balanced groups."""
    if isinstance(max_workers, bool) or max_workers < 1 or max_workers > 2:
        raise ValueError("max_workers must be 1 or 2")
    ordered = sorted({str(ticker) for ticker in tickers})
    if not ordered:
        return []
    count = min(max_workers, len(ordered))
    size, remainder = divmod(len(ordered), count)
    result: list[tuple[str, ...]] = []
    start = 0
    for index in range(count):
        stop = start + size + (1 if index < remainder else 0)
        result.append(tuple(ordered[start:stop]))
        start = stop
    return result


def partition_dependency_components(manifest: Mapping[str,Any],max_workers: int=2) -> list[tuple[str,...]]:
    """Keep each issuer with its source peers, then balance whole components."""
    if isinstance(max_workers,bool) or max_workers<1 or max_workers>2: raise ValueError('max_workers must be 1 or 2')
    tickers=set(manifest.get('closure_tickers',[]));graph={ticker:set() for ticker in tickers}
    for ticker,peers in (manifest.get('source_peers') or {}).items():
        for peer in peers:
            if ticker in graph and peer in graph: graph[ticker].add(peer);graph[peer].add(ticker)
    components=[]
    while graph:
        start=min(graph);stack=[start];component=set()
        while stack:
            node=stack.pop()
            if node in component: continue
            component.add(node);stack.extend(graph[node]-component)
        for node in component: graph.pop(node,None)
        components.append(tuple(sorted(component)))
    buckets=[[] for _ in range(min(max_workers,len(tickers)))]
    for component in sorted(components,key=lambda value:(-len(value),value)):
        target=min(range(len(buckets)),key=lambda index:(len(buckets[index]),index));buckets[target].extend(component)
    return [tuple(sorted(bucket)) for bucket in buckets if bucket]


def make_worker_specs(
    manifest: Mapping[str, Any],
    output_root: Path,
    *,
    max_workers: int = 2,
    snapshot_checkout: Path | None = None,
) -> list[dict[str, Any]]:
    _assert_manifest_self_hash(manifest)
    if manifest.get("broader_recheck"):
        raise DependencyClosureError("manifest requires broader dependency recheck")
    output_root = Path(output_root).resolve()
    specs: list[dict[str, Any]] = []
    run_root=output_root/str(manifest['manifest_sha256'])/'workers'
    for index, tickers in enumerate(partition_dependency_components(manifest,max_workers), start=1):
        spec = WorkerSpec(
            worker_id=f"worker-{index:02d}",
            tickers=tickers,
            manifest_sha256=str(manifest["manifest_sha256"]),
            implementation_sha256=str(manifest["implementation_sha256"]),
            input_sha256=str(manifest["input_sha256"]),
            output_dir=str(run_root / f"worker-{index:02d}"),
            snapshot_checkout=str(Path(snapshot_checkout).resolve()) if snapshot_checkout else None,
            snapshot_source_index=str(Path(snapshot_checkout).resolve().parent/'source-index.json') if snapshot_checkout and manifest.get('source_index') else None,
        )
        specs.append(spec.as_dict())
    return specs


def _copy_worker_runtime(runtime_root: Path, worker_root: Path, manifest: Mapping[str,Any]) -> Path:
    """Copy only inputs needed by a worker into its private runtime root."""
    staged = worker_root / "runtime"
    staged.mkdir(parents=True, exist_ok=False)
    for key,expected in manifest['input_files'].items():
        if str(key).startswith('@absolute:') or key==manifest.get('source_index'): continue
        source=(runtime_root/key).resolve();target=staged/key
        if expected==MISSING_FILE: continue
        if not source.is_file() or _file_sha256(source)!=expected:
            raise VerificationIntegrityError(f'frozen runtime input changed before copy: {key}')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    return staged


def materialize_implementation_snapshot(manifest: Mapping[str,Any],output_root: Path) -> Path:
    """Copy the exact uncommitted implementation bytes into a content-addressed tree."""
    _assert_manifest_self_hash(manifest)
    project=Path(str(manifest['implementation_root'])).resolve()
    root=Path(output_root).resolve()/str(manifest['manifest_sha256'])/'snapshot'/'checkout'
    if root.is_dir():
        validate_implementation_snapshot(manifest,root);validate_source_index_snapshot(manifest,root);return root
    root.mkdir(parents=True,exist_ok=False)
    for source_key,expected in manifest['implementation_files'].items():
        source=Path(source_key).resolve()
        try: relative=source.relative_to(project)
        except ValueError as exc: raise VerificationIntegrityError('implementation input is outside project root') from exc
        if _file_sha256(source)!=expected: raise VerificationIntegrityError(f'implementation changed before snapshot: {source}')
        target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    index_key=manifest.get('source_index')
    if isinstance(index_key,str):
        source=_resolve_runtime_key(Path(str(manifest['runtime_root'])),index_key);expected=manifest['input_files'][index_key]
        if _file_sha256(source)!=expected: raise VerificationIntegrityError('source index changed before snapshot')
        shutil.copy2(source,root.parent/'source-index.json')
    validate_implementation_snapshot(manifest,root)
    validate_source_index_snapshot(manifest,root)
    return root


def validate_implementation_snapshot(manifest: Mapping[str,Any],snapshot_checkout: Path) -> None:
    project=Path(str(manifest['implementation_root'])).resolve();snapshot=Path(snapshot_checkout).resolve();current={}
    for source_key,expected in manifest['implementation_files'].items():
        source=Path(source_key).resolve()
        try: relative=source.relative_to(project)
        except ValueError as exc: raise VerificationIntegrityError('implementation input is outside project root') from exc
        target=snapshot/relative;actual=_file_sha256(target)
        if actual!=expected: raise VerificationIntegrityError(f'frozen implementation snapshot drift: {relative}')
        current[source_key]=actual
    if _sha256(_canonical(current))!=manifest['implementation_sha256']:
        raise VerificationIntegrityError('frozen implementation snapshot digest mismatch')


def validate_runtime_snapshot(manifest: Mapping[str,Any],snapshot_runtime: Path) -> None:
    snapshot=Path(snapshot_runtime).resolve();current={}
    for key,expected in manifest['input_files'].items():
        if str(key).startswith('@absolute:'):
            path=_resolve_runtime_key(snapshot,key);actual=_file_sha256(path) if path.is_file() else MISSING_FILE
            if actual!=expected: raise VerificationIntegrityError(f'frozen external input drift: {key}')
            current[key]=actual;continue
        if key==manifest.get('source_index'):
            current[key]=expected;continue
        path=snapshot/key;actual=_file_sha256(path) if path.is_file() else MISSING_FILE
        if actual!=expected: raise VerificationIntegrityError(f'frozen runtime snapshot drift: {key}')
        current[key]=actual
    if _sha256(_canonical(current))!=manifest['input_sha256']:
        raise VerificationIntegrityError('frozen runtime snapshot digest mismatch')


def validate_source_index_snapshot(manifest: Mapping[str,Any],snapshot_checkout: Path) -> None:
    key=manifest.get('source_index')
    if not isinstance(key,str): return
    expected=manifest['input_files'].get(key);path=Path(snapshot_checkout).resolve().parent/'source-index.json'
    if not isinstance(expected,str) or _file_sha256(path)!=expected:
        raise VerificationIntegrityError('frozen source-index snapshot drift')


def _rows_from_verifier(result: Any, expected: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if isinstance(result, Mapping):
        rows = result.get("rows")
        extra = dict(result)
    else:
        rows = result
        extra = {}
    if not isinstance(rows, list):
        raise VerificationIntegrityError("worker verifier must return a rows list")
    normalised: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("ticker"), str):
            raise VerificationIntegrityError("worker row is malformed")
        normalised.append(dict(row))
    expected_set = set(expected)
    actual = [row["ticker"] for row in normalised]
    if set(actual) != expected_set or len(actual) != len(set(actual)):
        raise VerificationIntegrityError("worker verifier did not return each assigned ticker exactly once")
    return sorted(normalised, key=lambda row: row["ticker"]), extra


def _timings(result: Mapping[str, Any], elapsed: float) -> dict[str, float]:
    supplied = result.get("timings")
    output: dict[str, float] = {}
    if isinstance(supplied, Mapping):
        aliases = {"prepare": "prepare", "source": "source", "calc": "calc", "calculation": "calc", "verify": "verify",'total':'total'}
        for key, value in supplied.items():
            target = aliases.get(str(key))
            if target is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
                output[target] = round(float(value), 9)
    output.setdefault("verify", round(elapsed, 9))
    return output


def _worker_core_hash(payload: Mapping[str, Any]) -> str:
    return _sha256(_canonical({key: value for key, value in payload.items() if key != "report_sha256"}))


def run_worker(
    spec: Mapping[str, Any],
    manifest: Mapping[str, Any],
    runtime_root: Path,
    *,
    verifier: Callable[[Path, Sequence[str], Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> Path:
    """Run one isolated cached verifier and write immutable per-company output."""
    _assert_manifest_self_hash(manifest)
    validate_manifest_inputs(manifest, runtime_root)
    worker_id = spec.get("worker_id")
    tickers = tuple(spec.get("tickers", ()))
    if not isinstance(worker_id, str) or not tickers or list(tickers) != sorted(set(tickers)):
        raise VerificationIntegrityError("worker specification is malformed")
    if spec.get("manifest_sha256") != manifest.get("manifest_sha256") or spec.get("implementation_sha256") != manifest.get("implementation_sha256") or spec.get("input_sha256") != manifest.get("input_sha256"):
        raise VerificationIntegrityError("worker specification does not match frozen manifest")
    if not set(tickers).issubset(set(manifest.get("closure_tickers", []))):
        raise VerificationIntegrityError("worker includes ticker outside frozen closure")

    worker_root = Path(str(spec["output_dir"])).resolve()
    existing=worker_root/'report.json'
    if existing.is_file():
        report=_read_worker_report(existing)
        if (report.get('worker_id')==worker_id and report.get('manifest_sha256')==manifest['manifest_sha256']
            and report.get('implementation_sha256')==manifest['implementation_sha256']
            and report.get('input_sha256')==manifest['input_sha256']
            and report.get('expected_tickers')==list(tickers)):
            result_dir=worker_root/'results'
            if all((result_dir/f'{ticker}.json').is_file() and _file_sha256(result_dir/f'{ticker}.json')==report['company_result_sha256'].get(ticker) for ticker in tickers):
                return existing
        raise VerificationIntegrityError('existing worker output does not match the frozen specification')
    worker_root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    staged_root = runtime_root
    if verifier is None:
        staged_root = _copy_worker_runtime(Path(runtime_root).resolve(), worker_root, manifest)
        validate_runtime_snapshot(manifest,staged_root)
        snapshot_checkout=spec.get('snapshot_checkout')
        if not isinstance(snapshot_checkout,str): raise VerificationIntegrityError('default worker requires frozen implementation snapshot')
        snapshot_checkout=Path(snapshot_checkout).resolve();validate_implementation_snapshot(manifest,snapshot_checkout)
        index_key=manifest.get('source_index')
        if not isinstance(index_key,str):
            raise VerificationIntegrityError('default cached worker requires a frozen source index')
        source_index=spec.get('snapshot_source_index')
        if not isinstance(source_index,str): raise VerificationIntegrityError('worker source-index snapshot is missing')
        validate_source_index_snapshot(manifest,snapshot_checkout)
        command=[sys.executable,str(snapshot_checkout/'scripts'/'verify_us_refresh_sources.py'),'--runtime-root',str(staged_root),
            '--source-index',str(source_index),'--source-root',str(Path(__file__).resolve().parents[3]/'output')]
        for ticker in tickers: command.extend(['--ticker',ticker])
        env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join((str(snapshot_checkout/'backend'),str(snapshot_checkout)))
        completed=subprocess.run(command,cwd=snapshot_checkout,env=env,text=True,capture_output=True)
        if completed.returncode!=0:
            raise VerificationIntegrityError('frozen worker verifier failed: '+(completed.stderr.strip() or completed.stdout.strip()))
        final=next((json.loads(line) for line in reversed(completed.stdout.splitlines()) if line.startswith('{') and 'report_path' in line),None)
        if not isinstance(final,Mapping): raise VerificationIntegrityError('frozen worker verifier did not return a report path')
        verifier_result=json.loads(Path(str(final['report_path'])).read_bytes())
        if isinstance(final.get('timings'),Mapping): verifier_result['timings']=final['timings']
        validate_runtime_snapshot(manifest,staged_root);validate_implementation_snapshot(manifest,snapshot_checkout)
    else:
        verifier_result = verifier(staged_root, tickers, manifest)
    elapsed = time.perf_counter() - started
    rows, extra = _rows_from_verifier(verifier_result, tickers)
    result_dir = worker_root / "results"
    result_dir.mkdir()
    company_hashes: dict[str, str] = {}
    for row in rows:
        ticker = row["ticker"]
        payload = {"schema_version": WORKER_SCHEMA_VERSION, "ticker": ticker, "row": row}
        raw = _canonical(payload)
        (result_dir / f"{ticker}.json").write_bytes(raw)
        company_hashes[ticker] = _sha256(raw)
    core: dict[str, Any] = {
        "schema_version": WORKER_SCHEMA_VERSION,
        "worker_id": worker_id,
        "manifest_sha256": manifest["manifest_sha256"],
        "implementation_sha256": manifest["implementation_sha256"],
        "source_implementation_sha256": extra.get('implementation_sha256') or manifest['implementation_sha256'],
        "registry_sha256": extra.get('registry_sha256') or manifest['registry_sha256'],
        "policy_sha256": extra.get('policy_sha256') or manifest['policy_sha256'],
        "input_sha256": manifest["input_sha256"],
        "expected_tickers": list(tickers),
        "company_result_sha256": {ticker: company_hashes[ticker] for ticker in sorted(company_hashes)},
        "scope": "cached binding verification; no acquisition or publication",
    }
    report = {**core, "report_sha256": _worker_core_hash(core)}
    report_path = worker_root / "report.json"
    report_path.write_bytes(_canonical(report))
    (worker_root/'measurement.json').write_bytes(_canonical({'worker_id':worker_id,'timings':_timings(extra,elapsed)}))
    return report_path


def run_workers(
    specs: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    runtime_root: Path,
    *,
    verifier: Callable[[Path, Sequence[str], Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> list[Path]:
    """Run at most two isolated workers concurrently, returning sorted paths.

    The worker verifier is expected to be cached/read-only.  Each worker owns
    a different runtime/output directory, so this does not parallelize SEC
    acquisition or share the publication writer lock.
    """
    from concurrent.futures import ThreadPoolExecutor

    specs = list(specs)
    if len(specs) > 2:
        raise ValueError("at most two workers are permitted")
    if not specs:
        return []
    with ThreadPoolExecutor(max_workers=len(specs), thread_name_prefix="finsight-refresh-group") as pool:
        futures = [pool.submit(run_worker, spec, manifest, runtime_root, verifier=verifier) for spec in specs]
        paths = [future.result() for future in futures]
    return sorted(paths, key=lambda path: path.parent.name)


def _read_worker_report(path: Path) -> dict[str, Any]:
    report_path = path / "report.json" if path.is_dir() else path
    try:
        report = json.loads(report_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationIntegrityError(f"worker report is missing or invalid: {report_path}") from exc
    if not isinstance(report, dict) or report.get("schema_version") != WORKER_SCHEMA_VERSION:
        raise VerificationIntegrityError(f"unsupported worker report: {report_path}")
    if report.get("report_sha256") != _worker_core_hash(report):
        raise VerificationIntegrityError(f"worker report hash mismatch: {report_path}")
    return report


def _report_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Frozen refresh-group verification",
        "",
        "Diagnostic only: cached/source-bound verification. No acquisition, activation, or publication occurred.",
        "",
        f"Manifest: `{report['manifest_sha256']}`",
        f"Workers: {len(report['workers'])}",
        "",
        "| Company | Status | Reason |",
        "|---|---|---|",
    ]
    for row in report["rows"]:
        reason = str(row.get("reason") or "—").replace("|", "\\|").replace("\n", " ")
        status = str(row.get("status") or "—").replace("|", "\\|")
        lines.append(f"| {row['ticker']} | {status} | {reason} |")
    return "\n".join(lines) + "\n"


def reduce_worker_results(
    manifest: Mapping[str, Any],
    worker_reports: Iterable[Path],
    output_root: Path,
    *,
    runtime_root: Path | None = None,
    implementation_paths: Iterable[Path] | None = None,
    prepare_elapsed_seconds: float | None = None,
    snapshot_checkout: Path | None = None,
) -> dict[str, Any]:
    """Validate all worker output and emit one deterministic JSON/Markdown report."""
    worker_reports = [Path(path) for path in worker_reports]
    _assert_manifest_self_hash(manifest)
    if manifest.get("broader_recheck"):
        raise DependencyClosureError("manifest requires broader dependency recheck")
    if snapshot_checkout is None:
        validate_manifest_inputs(manifest, runtime_root, implementation_paths=implementation_paths)
    else:
        validate_implementation_snapshot(manifest,snapshot_checkout)
        validate_source_index_snapshot(manifest,snapshot_checkout)
    expected = tuple(sorted(manifest.get("closure_tickers", [])))
    if not expected:
        raise VerificationIntegrityError("frozen manifest has no expected tickers")
    report_records=[(path,_read_worker_report(path)) for path in worker_reports]
    if not report_records:
        raise VerificationIntegrityError("no worker reports supplied")
    worker_ids: set[str] = set()
    seen: dict[str, dict[str, Any]] = {}
    workers: list[dict[str, Any]] = []
    source_implementation_hashes:set[str]=set()
    timings: dict[str, float] = {}
    for supplied,report in report_records:
        worker_id = report.get("worker_id")
        if not isinstance(worker_id, str) or worker_id in worker_ids:
            raise VerificationIntegrityError("duplicate worker report")
        worker_ids.add(worker_id)
        for key in ("manifest_sha256", "implementation_sha256", "input_sha256"):
            if report.get(key) != manifest.get(key):
                raise VerificationIntegrityError(f"worker {worker_id} {key} mismatch")
        if report.get('registry_sha256')!=manifest['registry_sha256'] or report.get('policy_sha256')!=manifest['policy_sha256']:
            raise VerificationIntegrityError(f'worker {worker_id} registry/policy hash mismatch')
        source_hash=report.get('source_implementation_sha256')
        if not isinstance(source_hash,str): raise VerificationIntegrityError(f'worker {worker_id} source implementation hash missing')
        source_implementation_hashes.add(source_hash)
        assigned = report.get("expected_tickers")
        if not isinstance(assigned, list) or assigned != sorted(set(assigned)):
            raise VerificationIntegrityError(f"worker {worker_id} ticker assignment is malformed")
        result_hashes = report.get("company_result_sha256")
        if not isinstance(result_hashes, Mapping) or set(result_hashes) != set(assigned):
            raise VerificationIntegrityError(f"worker {worker_id} result index mismatch")
        if snapshot_checkout is not None:
            validate_runtime_snapshot(manifest,(supplied.parent if supplied.is_file() else supplied)/'runtime')
        # The report does not trust an embedded path.  Locate result files next
        # to the report path supplied by the caller below.
        workers.append({"worker_id": worker_id, "tickers": list(assigned)})
        measurement_file=(supplied.parent if supplied.is_file() else supplied)/'measurement.json'
        try: measurement=json.loads(measurement_file.read_bytes()) if measurement_file else {}
        except (OSError,json.JSONDecodeError): measurement={}
        for key, value in (measurement.get("timings") or {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                timings[key] = round(timings.get(key, 0.0) + float(value), 9)

    # Read reports again paired with their original paths; keeping this loop
    # separate makes duplicate/missing assignment checks explicit and avoids
    # trusting worker-provided directory names.
    for supplied,report in report_records:
        report_path = supplied / "report.json" if supplied.is_dir() else supplied
        worker_id = str(report["worker_id"])
        result_dir = report_path.parent / "results"
        actual_files = {path.stem for path in result_dir.glob("*.json")} if result_dir.is_dir() else set()
        if actual_files != set(report["expected_tickers"]):
            raise VerificationIntegrityError(f"worker {worker_id} result files do not match assignment")
        for ticker in report["expected_tickers"]:
            if ticker in seen:
                raise VerificationIntegrityError(f"duplicate worker result for {ticker}")
            result_path = result_dir / f"{ticker}.json"
            if not result_path.is_file() or _file_sha256(result_path) != report["company_result_sha256"].get(ticker):
                raise VerificationIntegrityError(f"worker {worker_id} result hash mismatch: {ticker}")
            try:
                payload = json.loads(result_path.read_bytes())
            except (OSError, json.JSONDecodeError) as exc:
                raise VerificationIntegrityError(f"worker result is invalid: {result_path}") from exc
            if not isinstance(payload, Mapping) or payload.get("ticker") != ticker or not isinstance(payload.get("row"), Mapping):
                raise VerificationIntegrityError(f"worker result identity mismatch: {ticker}")
            seen[ticker] = dict(payload["row"])
    if set(seen) != set(expected):
        missing = sorted(set(expected) - set(seen))
        extra = sorted(set(seen) - set(expected))
        raise VerificationIntegrityError(f"worker coverage mismatch; missing={missing}, extra={extra}")

    rows = [seen[ticker] for ticker in expected]
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    report_core: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "manifest_sha256": manifest["manifest_sha256"],
        "implementation_sha256": next(iter(source_implementation_hashes)) if len(source_implementation_hashes)==1 else None,
        "orchestrator_implementation_sha256":manifest['implementation_sha256'],
        "registry_sha256":manifest['registry_sha256'],
        "policy_sha256":manifest['policy_sha256'],
        "input_sha256": manifest["input_sha256"],
        "expected_tickers": list(expected),
        "counts": {key: counts[key] for key in sorted(counts)},
        "rows": rows,
        "workers": sorted(workers, key=lambda row: row["worker_id"]),
        "scope": "cached binding verification; no acquisition or publication",
        "broader_recheck": list(manifest.get("broader_recheck", [])),
    }
    if report_core['implementation_sha256'] is None:
        raise VerificationIntegrityError('workers disagree on source implementation version')
    final_report = {**report_core, "report_sha256": _sha256(_canonical(report_core))}
    destination = Path(output_root).resolve() / str(manifest["manifest_sha256"])
    destination.mkdir(parents=True, exist_ok=True)
    report_path=destination/'report.json';markdown_path=destination/'report.md'
    for path,payload in ((report_path,_canonical(final_report)),(markdown_path,_report_markdown(final_report).encode())):
        if path.exists() and path.read_bytes()!=payload:
            raise VerificationIntegrityError(f'deterministic reduced output drift: {path.name}')
        path.write_bytes(payload)
    measurement={'freeze_prepare':round(float(prepare_elapsed_seconds),9)} if prepare_elapsed_seconds is not None else {}
    measurement.update({key:round(value,9) for key,value in sorted(timings.items())})
    measurement_path=destination/'measurement.json';measurement_path.write_bytes(_canonical({'timings':measurement}))
    return {**final_report,"report_path":str(report_path),'measurement_path':str(measurement_path),'timings':measurement}
