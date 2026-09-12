"""Runtime catalog refresh, activation, and per-request snapshot handling.

The tracked catalog is a build input.  This module keeps the mutable runtime
state in an explicitly supplied directory: immutable catalog snapshots, an
atomic ``active.json`` pointer, and activation/rollback receipts.  It never
creates an approval record; publishing requires a policy fingerprint that was
already approved by the caller's governance process.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import json
from math import isclose
import os
import fcntl
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from threading import RLock
from typing import Any
from uuid import uuid4

from .catalog import (
    ACTIVE_SCHEMA,
    CatalogIntegrityError,
    TICKER,
    ValuationCatalog,
    canonical_json_bytes,
    load_active_catalog,
    load_catalog_version,
    sha256_bytes,
)
from .artifacts import sanitize_public_artifact
from .calculation_recipe import evaluate_recipe
from .calculator import baseline_version


REFRESH_REGISTRY_SCHEMA = "FINSIGHT-US-REFRESH-REGISTRY-1"
ACTIVATION_RECEIPT_SCHEMA = "FINSIGHT-US-CATALOG-ACTIVATION-1"
ROLLBACK_RECEIPT_SCHEMA = "FINSIGHT-US-CATALOG-ROLLBACK-1"
FROZEN_REGISTRY_COUNT = 440
_UNSET = object()


@dataclass(frozen=True)
class FrozenRegistryEntry:
    ticker: str
    cik: str
    batch: int | None = None
    recipe_status: str | None = None
    availability_type: str | None = None


@dataclass(frozen=True)
class FrozenRegistry:
    """The exact issuer identity set a refresh is allowed to publish."""

    path: Path | None
    registry_sha256: str
    entries: tuple[FrozenRegistryEntry, ...]
    baseline_catalog_version: str | None = None
    baseline_manifest_sha256: str | None = None

    @property
    def identity_set(self) -> frozenset[tuple[str, str]]:
        return frozenset((entry.ticker, entry.cik) for entry in self.entries)

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(entry.ticker for entry in self.entries)


def _registry_from_object(
    value: Mapping[str, Any],
    *,
    path: Path | None,
    registry_sha256: str,
    expected_count: int | None,
) -> FrozenRegistry:
    if value.get("schema_version") != REFRESH_REGISTRY_SCHEMA:
        raise CatalogIntegrityError("refresh registry schema is unsupported")
    raw_entries = value.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise CatalogIntegrityError("refresh registry entries are missing")
    if expected_count is not None and len(raw_entries) != expected_count:
        raise CatalogIntegrityError(
            f"refresh registry expected {expected_count} entries, got {len(raw_entries)}"
        )

    entries: list[FrozenRegistryEntry] = []
    seen_tickers: set[str] = set()
    seen_ciks: set[str] = set()
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise CatalogIntegrityError("refresh registry entry is invalid")
        ticker = raw.get("ticker")
        cik = raw.get("cik")
        batch = raw.get("batch")
        if not isinstance(ticker, str) or not TICKER.fullmatch(ticker):
            raise CatalogIntegrityError("refresh registry ticker is invalid")
        if not isinstance(cik, str) or len(cik) != 10 or not cik.isdigit():
            raise CatalogIntegrityError(f"{ticker}: refresh registry CIK is invalid")
        if batch is not None and (
            not isinstance(batch, int) or isinstance(batch, bool) or batch < 1
        ):
            raise CatalogIntegrityError(f"{ticker}: refresh registry batch is invalid")
        if ticker in seen_tickers:
            raise CatalogIntegrityError(f"{ticker}: duplicate refresh registry ticker")
        if cik in seen_ciks:
            raise CatalogIntegrityError(f"{ticker}: duplicate refresh registry CIK")
        seen_tickers.add(ticker)
        seen_ciks.add(cik)
        recipe_status = raw.get("recipe_status")
        if recipe_status is not None and not isinstance(recipe_status, str):
            raise CatalogIntegrityError(f"{ticker}: refresh registry recipe status is invalid")
        availability_type = raw.get('availability_type')
        if availability_type is not None and availability_type not in {'available','conditional_estimate','not_available','relative_baseline'}:
            raise CatalogIntegrityError(f'{ticker}: invalid original availability type')
        entries.append(
            FrozenRegistryEntry(
                ticker=ticker, cik=cik, batch=batch, recipe_status=recipe_status, availability_type=availability_type
            )
        )
    if raw_entries != sorted(raw_entries, key=lambda row: str(row.get("ticker"))):
        raise CatalogIntegrityError("refresh registry entries are not sorted by ticker")

    return FrozenRegistry(
        path=path,
        registry_sha256=registry_sha256,
        entries=tuple(entries),
        baseline_catalog_version=(
            str(value["baseline_catalog_version"])
            if value.get("baseline_catalog_version") is not None
            else None
        ),
        baseline_manifest_sha256=(
            str(value["baseline_manifest_sha256"])
            if value.get("baseline_manifest_sha256") is not None
            else None
        ),
    )


def load_frozen_registry(
    path: Path, *, expected_count: int | None = FROZEN_REGISTRY_COUNT
) -> FrozenRegistry:
    """Load and validate a frozen registry, preserving its byte hash."""
    path = Path(path).resolve()
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogIntegrityError("refresh registry is missing or invalid") from exc
    if not isinstance(value, dict):
        raise CatalogIntegrityError("refresh registry must be a JSON object")
    return _registry_from_object(
        value,
        path=path,
        registry_sha256=sha256_bytes(raw),
        expected_count=expected_count,
    )


def _coerce_registry(
    registry: FrozenRegistry | Path | Mapping[str, Any],
    *,
    expected_count: int | None = FROZEN_REGISTRY_COUNT,
) -> FrozenRegistry:
    if isinstance(registry, FrozenRegistry):
        if expected_count is not None and len(registry.entries) != expected_count:
            raise CatalogIntegrityError(
                f"refresh registry expected {expected_count} entries, got {len(registry.entries)}"
            )
        return registry
    if isinstance(registry, (str, Path)):
        return load_frozen_registry(Path(registry), expected_count=expected_count)
    if isinstance(registry, Mapping):
        raw = canonical_json_bytes(registry)
        return _registry_from_object(
            registry,
            path=None,
            registry_sha256=sha256_bytes(raw),
            expected_count=expected_count,
        )
    raise TypeError("frozen_registry must be a path, object, or FrozenRegistry")


def _validate_membership(
    catalog: ValuationCatalog, registry: FrozenRegistry
) -> None:
    actual = {(entry.ticker, entry.cik) for entry in catalog.entries}
    expected = registry.identity_set
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise CatalogIntegrityError(
            "catalog membership does not match frozen registry"
            f" (missing={missing[:5]}, extra={extra[:5]})"
        )
    expected_by_ticker = {entry.ticker: entry for entry in registry.entries}
    for entry in catalog.entries:
        frozen = expected_by_ticker[entry.ticker]
        if frozen.batch is not None and entry.batch != frozen.batch:
            raise CatalogIntegrityError(
                f"{entry.ticker}: catalog batch does not match frozen registry"
            )


def _validate_private_recipe_index(
    root: Path, catalog: ValuationCatalog, registry: FrozenRegistry
) -> None:
    """Validate candidate-only private recipe pins against public baselines."""
    index = catalog.manifest.get("private_recipe_sha256")
    required = {
        entry.ticker for entry in catalog.entries if entry.availability_type != "not_available"
    }
    if index is None:
        if catalog.catalog_version.startswith("REFRESH-"):
            raise CatalogIntegrityError("refresh catalog private recipe index is required")
        return
    if not isinstance(index, dict):
        raise CatalogIntegrityError("private recipe index is invalid")
    if set(index) != required:
        raise CatalogIntegrityError(
            f"private recipe index membership mismatch (expected={sorted(required)[:5]})"
        )
    recipes_root = root / "recipes"
    if not recipes_root.is_dir():
        raise CatalogIntegrityError("private recipe directory is missing")
    recipe_files = {path.stem for path in recipes_root.glob("*.json")}
    if recipe_files != required:
        raise CatalogIntegrityError("private recipe files do not match the recipe index")
    root_resolved = root.resolve()
    for ticker in sorted(required):
        digest = index[ticker]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise CatalogIntegrityError(f"{ticker}: private recipe hash is invalid")
        path = recipes_root / f"{ticker}.json"
        resolved = path.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise CatalogIntegrityError(f"{ticker}: private recipe path escapes catalog") from exc
        if not path.is_file() or sha256_bytes(path.read_bytes()) != digest:
            raise CatalogIntegrityError(f"{ticker}: private recipe hash mismatch")
        try:
            recipe = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogIntegrityError(f"{ticker}: private recipe is invalid") from exc
        if not isinstance(recipe, dict) or recipe.get("ticker") != ticker:
            raise CatalogIntegrityError(f"{ticker}: private recipe ticker mismatch")
        public = sanitize_public_artifact(
            json.loads(catalog.verify_artifact(ticker).read_text(encoding="utf-8"))
        )
        if recipe.get("baseline_version") != baseline_version(public):
            raise CatalogIntegrityError(f"{ticker}: private recipe baseline mismatch")
        try:
            actual = evaluate_recipe(recipe)["range"]
        except (KeyError, TypeError, ValueError) as exc:
            raise CatalogIntegrityError(f"{ticker}: private recipe evaluation failed") from exc
        expected = public.get("scenario_range", {})
        if any(
            not isclose(float(actual[key]), float(expected[key]), rel_tol=1e-9, abs_tol=1e-7)
            for key in ("low", "base", "high")
        ):
            raise CatalogIntegrityError(f"{ticker}: private recipe does not reproduce baseline")


def load_retry_states(catalog: ValuationCatalog, registry: FrozenRegistry) -> dict[str, dict]:
    """Validate private last-numeric templates retained for supported unavailable issuers."""
    index = catalog.manifest.get('retry_state_sha256', {})
    if not isinstance(index,dict):
        raise CatalogIntegrityError('retry state index is invalid')
    unavailable = {entry.ticker for entry in catalog.entries if entry.availability_type == 'not_available'}
    original = {entry.ticker:entry for entry in registry.entries}
    expected = {ticker for ticker in unavailable if original[ticker].availability_type in {'available','conditional_estimate','relative_baseline'}}
    if catalog.catalog_version.startswith('REFRESH-') and not expected <= set(index):
        raise CatalogIntegrityError('supported unavailable issuer is missing its retry state')
    if not set(index) <= unavailable or any(original[ticker].availability_type == 'not_available' for ticker in index):
        raise CatalogIntegrityError('retry state membership is outside supported unavailable issuers')
    directory = catalog.root/'retry-state'
    files = {path.stem for path in directory.glob('*.json')} if directory.exists() else set()
    if files != set(index):
        raise CatalogIntegrityError('retry state files do not match the index')
    states = {}
    for ticker,digest in index.items():
        path = directory/f'{ticker}.json'
        if not path.resolve().is_relative_to(catalog.root.resolve()) or not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest):
            raise CatalogIntegrityError('invalid retry state path or digest')
        raw = path.read_bytes()
        if sha256_bytes(raw) != digest:
            raise CatalogIntegrityError(f'{ticker}: retry state hash mismatch')
        try:
            state = json.loads(raw)
            if state.get('schema_version') != 'FINSIGHT-RETRY-STATE-1':
                raise ValueError('unsupported retry state schema')
            recipe = state['recipe']
            public = sanitize_public_artifact(state['public_template'])
            if (recipe.get('ticker') != ticker or public['issuer']['ticker'] != ticker
                or public['issuer']['cik'] != original[ticker].cik or public['availability_type'] == 'not_available'
                or recipe.get('baseline_version') != baseline_version(public)):
                raise ValueError('retry template identity/baseline mismatch')
            actual = evaluate_recipe(recipe)['range']
            if any(not isclose(actual[key],public['scenario_range'][key],rel_tol=1e-9,abs_tol=1e-7) for key in ('low','base','high')):
                raise ValueError('retry recipe does not reproduce last numeric template')
        except (KeyError,ValueError,TypeError) as exc:
            raise CatalogIntegrityError(f'{ticker}: invalid retry state: {exc}') from exc
        states[ticker] = state
    return states


def _safe_relative_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise CatalogIntegrityError("runtime catalog path is missing")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise CatalogIntegrityError("runtime catalog path is unsafe")
    return Path(*pure.parts)


def _is_default_policy_path(path: Path, runtime_root: Path) -> bool:
    return path == runtime_root / "approved-policy.json"


def _contained_runtime_path(runtime_root: Path, relative: Path, *, label: str) -> Path:
    """Resolve a runtime-relative path and reject symlink/path escapes."""
    root = runtime_root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise CatalogIntegrityError(f"runtime {label} escapes runtime root") from exc
    return resolved


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}-", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


class RefreshCatalogStore:
    """Manage immutable runtime snapshots below one explicit root."""

    def __init__(
        self,
        runtime_root: Path,
        *,
        frozen_registry: FrozenRegistry | Path | Mapping[str, Any],
        expected_registry_count: int | None = FROZEN_REGISTRY_COUNT,
        approved_policy_path: Path | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self.snapshots_root = self.runtime_root / "snapshots"
        self.history_root = self.runtime_root / "history"
        self.approved_policy_path = (
            Path(approved_policy_path).resolve()
            if approved_policy_path
            else self.runtime_root / "approved-policy.json"
        )
        self.registry = _coerce_registry(
            frozen_registry, expected_count=expected_registry_count
        )
        self._lock = RLock()
        self._writer_lock_path = self.runtime_root / ".refresh-writers.lock"

    @property
    def active_pointer_path(self) -> Path:
        return self.runtime_root / "active.json"

    @contextmanager
    def _writer_lock(self):
        """Serialize writers across threads and independent processes."""
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        with self._writer_lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_pointer(self) -> tuple[dict[str, Any], bytes]:
        try:
            raw = self.active_pointer_path.read_bytes()
            value = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogIntegrityError("runtime active pointer is missing or invalid") from exc
        if not isinstance(value, dict) or value.get("schema_version") != ACTIVE_SCHEMA:
            raise CatalogIntegrityError("runtime active pointer schema is unsupported")
        if value.get("registry_sha256") != self.registry.registry_sha256:
            raise CatalogIntegrityError("runtime active pointer registry hash mismatch")
        _contained_runtime_path(
            self.runtime_root,
            _safe_relative_path(value.get("catalog_path")),
            label="catalog path",
        )
        return value, raw

    def _validate_candidate(self, root: Path) -> ValuationCatalog:
        candidate = load_catalog_version(root)
        _validate_membership(candidate, self.registry)
        _validate_private_recipe_index(root, candidate, self.registry)
        load_retry_states(candidate,self.registry)
        return candidate

    def stage_catalog(self, source_root: Path) -> ValuationCatalog:
        """Copy and validate a complete catalog into an immutable snapshot."""
        source_root = Path(source_root).resolve()
        candidate = self._validate_candidate(source_root)
        destination = self.snapshots_root / candidate.catalog_version
        with self._writer_lock(), self._lock:
            _contained_runtime_path(
                self.runtime_root, Path("snapshots"), label="snapshots root"
            )
            self.snapshots_root.mkdir(parents=True, exist_ok=True)
            version_path = PurePosixPath(candidate.catalog_version)
            if (
                version_path.is_absolute()
                or len(version_path.parts) != 1
                or version_path.parts[0] in {".", ".."}
            ):
                raise CatalogIntegrityError("catalog version is unsafe for runtime storage")
            if destination.exists():
                existing = self._validate_candidate(destination)
                if existing.manifest_sha256 != candidate.manifest_sha256:
                    raise FileExistsError(
                        f"immutable runtime snapshot differs: {destination}"
                    )
                return existing
            stage = Path(
                tempfile.mkdtemp(prefix=f".{candidate.catalog_version}-", dir=self.snapshots_root)
            )
            try:
                shutil.copytree(source_root, stage, dirs_exist_ok=True)
                staged = self._validate_candidate(stage)
                if staged.manifest_sha256 != candidate.manifest_sha256:
                    raise CatalogIntegrityError("staged catalog manifest hash changed")
                stage.replace(destination)
                _fsync_directory(self.snapshots_root)
            except Exception:
                if stage.exists():
                    shutil.rmtree(stage)
                raise
        return load_catalog_version(destination)

    def _approved_policy_fingerprint(self) -> str:
        policy_path = self.approved_policy_path
        # Accept the underscore spelling as an integration convenience, while
        # keeping one explicit default location and never creating either file.
        if not policy_path.exists() and _is_default_policy_path(policy_path, self.runtime_root):
            alternate = self.runtime_root / "approved_policy.json"
            if alternate.exists():
                policy_path = alternate
        try:
            value = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogIntegrityError(
                "a preexisting approved policy fingerprint is required"
            ) from exc
        if not isinstance(value, dict):
            raise CatalogIntegrityError("approved policy record is invalid")
        approved = value.get("approved") is True or value.get("status") == "approved"
        if not approved or value.get("approved") is False or (
            value.get("status") is not None and value.get("status") != "approved"
        ):
            raise CatalogIntegrityError("approved policy record is not approved")
        registry_sha256 = value.get("registry_sha256", value.get("approved_registry_sha256"))
        if registry_sha256 != self.registry.registry_sha256:
            raise CatalogIntegrityError("approved policy registry hash does not match frozen registry")
        fingerprint = value.get("policy_fingerprint", value.get("fingerprint"))
        if not isinstance(fingerprint, str) or not fingerprint.strip():
            raise CatalogIntegrityError("approved policy fingerprint is missing")
        return fingerprint.strip()

    def _candidate_root(self, catalog: Path | str | ValuationCatalog) -> tuple[Path, ValuationCatalog]:
        if isinstance(catalog, ValuationCatalog):
            root = catalog.root
        else:
            raw = Path(catalog)
            root = raw if raw.is_absolute() else self.runtime_root / raw
        root = root.resolve()
        try:
            root.relative_to(self.runtime_root)
        except ValueError as exc:
            raise CatalogIntegrityError(
                "runtime activation requires a staged catalog under runtime_root"
            ) from exc
        candidate = self._validate_candidate(root)
        return root, candidate

    def _pointer_for(
        self,
        candidate: ValuationCatalog,
        root: Path,
        *,
        activated_at: str,
        policy_fingerprint: str,
    ) -> dict[str, Any]:
        try:
            relative = root.relative_to(self.runtime_root).as_posix()
        except ValueError as exc:
            raise CatalogIntegrityError(
                "runtime activation requires a staged catalog under runtime_root"
            ) from exc
        return {
            "schema_version": ACTIVE_SCHEMA,
            "catalog_version": candidate.catalog_version,
            "catalog_path": relative,
            "manifest_sha256": candidate.manifest_sha256,
            "registry_sha256": self.registry.registry_sha256,
            "policy_fingerprint": policy_fingerprint,
            "activated_at": activated_at,
        }

    def _write_pointer(self, pointer: Mapping[str, Any]) -> None:
        _atomic_json_write(self.active_pointer_path, pointer)

    def _restore_pointer_bytes(self, raw: bytes | None) -> None:
        if raw is None:
            try:
                self.active_pointer_path.unlink()
            except FileNotFoundError:
                pass
            return
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".active-rollback-", suffix=".json", dir=self.runtime_root
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.active_pointer_path)
            _fsync_directory(self.runtime_root)
        finally:
            if temporary.exists():
                temporary.unlink()

    def activate(
        self,
        catalog: Path | str | ValuationCatalog,
        *,
        policy_fingerprint: str,
        activated_at: str,
        reason: str | None = None,
        expected_active_manifest_sha256: str | None | object = _UNSET,
    ) -> dict[str, Any]:
        """Atomically activate a staged catalog after all gates pass."""
        if not isinstance(policy_fingerprint, str) or not policy_fingerprint.strip():
            raise ValueError("explicit policy fingerprint is required")
        policy_fingerprint = policy_fingerprint.strip()
        with self._writer_lock(), self._lock:
            approved = self._approved_policy_fingerprint()
            if policy_fingerprint != approved:
                raise CatalogIntegrityError("policy fingerprint is not pre-approved")
            root, candidate = self._candidate_root(catalog)
            if (
                expected_active_manifest_sha256 is _UNSET
                and candidate.catalog_version.startswith("REFRESH-")
            ):
                raise CatalogIntegrityError(
                    "refresh activation requires an explicit active-manifest precondition"
                )
            if expected_active_manifest_sha256 is not _UNSET and expected_active_manifest_sha256 is not None:
                if not isinstance(expected_active_manifest_sha256, str) or not re.fullmatch(
                    r"[0-9a-f]{64}", expected_active_manifest_sha256
                ):
                    raise ValueError("expected active manifest hash is invalid")
            previous_pointer: dict[str, Any] | None = None
            previous_raw: bytes | None = None
            if self.active_pointer_path.exists():
                previous_pointer, previous_raw = self._read_pointer()
                # Validate the currently active catalog before replacing it.
                load_active_catalog(self.runtime_root)
            actual_active_manifest = (
                previous_pointer.get("manifest_sha256") if previous_pointer else None
            )
            if expected_active_manifest_sha256 is None:
                if actual_active_manifest is not None:
                    raise CatalogIntegrityError(
                        "active catalog precondition expected no active pointer"
                    )
            elif expected_active_manifest_sha256 is not _UNSET:
                if actual_active_manifest != expected_active_manifest_sha256:
                    raise CatalogIntegrityError(
                        "active catalog manifest precondition mismatch"
                    )
            pointer = self._pointer_for(
                candidate,
                root,
                activated_at=activated_at,
                policy_fingerprint=policy_fingerprint,
            )
            receipt = {
                "schema_version": ACTIVATION_RECEIPT_SCHEMA,
                "operation": "activate",
                "catalog_version": candidate.catalog_version,
                "manifest_sha256": candidate.manifest_sha256,
                "registry_sha256": self.registry.registry_sha256,
                "policy_fingerprint": policy_fingerprint,
                "activated_at": activated_at,
                "reason": reason,
                "previous_pointer": previous_pointer,
                "rollback_pointer": previous_pointer,
            }
            self.history_root.mkdir(parents=True, exist_ok=True)
            receipt_path = self.history_root / f"activation-{uuid4().hex}.json"
            self._write_pointer(pointer)
            try:
                _atomic_json_write(receipt_path, receipt)
            except Exception:
                # Keep the last active state if durable history cannot be
                # recorded.  The pointer write itself is still atomic.
                self._restore_pointer_bytes(previous_raw)
                raise
            return {
                "pointer": pointer,
                "receipt": receipt,
                "receipt_path": receipt_path,
                "rollback_pointer": previous_pointer,
            }

    def rollback(
        self,
        receipt_path: Path | str,
        *,
        rolled_back_at: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Restore the previous pointer recorded by an activation receipt."""
        receipt_path = Path(receipt_path)
        if not receipt_path.is_absolute():
            receipt_path = self.runtime_root / receipt_path
        if not receipt_path.resolve().is_relative_to(self.history_root.resolve()):
            raise CatalogIntegrityError('rollback requires an activation receipt from this runtime history')
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogIntegrityError("activation receipt is missing or invalid") from exc
        if not isinstance(receipt, dict) or receipt.get("schema_version") != ACTIVATION_RECEIPT_SCHEMA:
            raise CatalogIntegrityError("activation receipt schema is unsupported")
        previous = receipt.get("rollback_pointer")
        if previous is None:
            raise CatalogIntegrityError("activation has no previous pointer to roll back to")
        if not isinstance(previous, dict):
            raise CatalogIntegrityError("activation rollback pointer is invalid")
        relative = _safe_relative_path(previous.get("catalog_path"))
        previous_root = _contained_runtime_path(self.runtime_root,relative,label='rollback catalog path')
        with self._writer_lock(), self._lock:
            current_pointer, current_raw = self._read_pointer()
            if current_pointer.get('manifest_sha256') != receipt.get('manifest_sha256'):
                raise CatalogIntegrityError('rollback receipt does not describe the currently active catalog')
            candidate = self._validate_candidate(previous_root)
            if candidate.manifest_sha256 != previous.get('manifest_sha256'):
                raise CatalogIntegrityError('rollback catalog manifest hash mismatch')
            rollback_receipt = {
                "schema_version": ROLLBACK_RECEIPT_SCHEMA,
                "operation": "rollback",
                "rolled_back_at": rolled_back_at,
                "reason": reason,
                "from_pointer": current_pointer,
                "to_pointer": previous,
                "activation_receipt": receipt_path.as_posix(),
            }
            pointer = dict(previous)
            pointer["activated_at"] = rolled_back_at
            pointer["rollback_of"] = receipt.get("catalog_version")
            rollback_path = self.history_root / f"rollback-{uuid4().hex}.json"
            self._write_pointer(pointer)
            try:
                _atomic_json_write(rollback_path, rollback_receipt)
            except Exception:
                self._restore_pointer_bytes(current_raw)
                raise
            return {
                "pointer": pointer,
                "receipt": rollback_receipt,
                "receipt_path": rollback_path,
            }

    def reader(self) -> "CatalogSnapshotReader":
        return CatalogSnapshotReader(self)

    def load_active(self) -> ValuationCatalog:
        return self.reader().get_snapshot()


class CatalogSnapshotReader:
    """Per-request catalog reader that pins until active pointer hash changes."""

    def __init__(self, store: RefreshCatalogStore) -> None:
        self.store = store
        self._pointer_hash: str | None = None
        self._snapshot: ValuationCatalog | None = None

    def get_snapshot(self) -> ValuationCatalog:
        with self.store._lock:
            try:
                raw = self.store.active_pointer_path.read_bytes()
            except OSError as exc:
                raise CatalogIntegrityError("runtime active pointer is missing") from exc
            pointer_hash = sha256_bytes(raw)
            if self._snapshot is not None and pointer_hash == self._pointer_hash:
                return self._snapshot
            # Validate the pointer's registry binding and resolved containment
            # before delegating to the generic loader.
            self.store._read_pointer()
            snapshot = load_active_catalog(self.store.runtime_root)
            _validate_membership(snapshot, self.store.registry)
            _validate_private_recipe_index(snapshot.root, snapshot, self.store.registry)
            load_retry_states(snapshot,self.store.registry)
            self._pointer_hash = pointer_hash
            self._snapshot = snapshot
            return snapshot
