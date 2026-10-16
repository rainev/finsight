"""Request-scoped, content-authenticated proof snapshot for read-only consumers."""
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path

from .approved_inheritance import _file

_CURRENT = ContextVar("us_read_path_snapshot", default=None)


def _canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


class ProofSnapshot:
    """Validate current proof bytes once per request and return fresh objects."""

    def __init__(self, bound_root=None, bound_manifest=None):
        self._proofs = {}
        self._contexts = {}
        self._metadata = {}
        self._bound_root = str(Path(bound_root).resolve()) if bound_root is not None else None
        self._bound_manifest = bound_manifest
        self._bound_manifest_digest = (
            hashlib.sha256(_canonical(bound_manifest)).hexdigest()
            if bound_manifest is not None else None
        )

    def proof(self, root, name, expected):
        key = (str(Path(root).resolve()), name, expected)
        if key not in self._proofs:
            raw = _file(root, name)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("read-path proof hash mismatch: " + name)
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("read-path proof is not an object: " + name)
            # Cache only authenticated bytes.  Every caller receives a fresh
            # decoded object; mutable proof values can never poison this
            # request's cache or a later consumer.
            canonical = _canonical(value)
            if hashlib.sha256(canonical).hexdigest() != expected:
                raise ValueError("read-path parsed proof hash mismatch: " + name)
            self._proofs[key] = canonical
        cached = self._proofs[key]
        return json.loads(cached)

    def assert_manifest(self, root, manifest):
        raw = _file(root, "manifest.json")
        value = json.loads(raw)
        if value != manifest:
            raise ValueError("read-path caller manifest does not match current file")

    def context_for(self, root, manifest, builder):
        # Staged validators may pass an authenticated stage manifest while
        # reading an admitted catalog root, so the root manifest must not be
        # compared here. A request-scoped content key prevents mutated
        # caller objects from reusing a cached semantic result.
        root_key = str(Path(root).resolve())
        manifest_digest = hashlib.sha256(_canonical(manifest)).hexdigest()
        if (root_key == self._bound_root and manifest is self._bound_manifest
                and manifest_digest != self._bound_manifest_digest):
            self.assert_manifest(root, manifest)
        key = (root_key, manifest_digest)
        if key not in self._contexts:
            self._contexts[key] = _canonical(builder())
        value = json.loads(self._contexts[key])
        return tuple(value) if isinstance(value, list) else value

    def metadata_for(self, root, manifest, builder):
        root_key = str(Path(root).resolve())
        manifest_digest = hashlib.sha256(_canonical(manifest)).hexdigest()
        if (root_key == self._bound_root and manifest is self._bound_manifest
                and manifest_digest != self._bound_manifest_digest):
            self.assert_manifest(root, manifest)
        key = (root_key, manifest_digest)
        if key not in self._metadata:
            self._metadata[key] = _canonical(builder())
        return json.loads(self._metadata[key])


class SnapshotProofReader:
    """The only reader allowed to use the request-authenticated fast path."""

    __slots__ = ("_snapshot", "_manifest_name", "_sealed")

    def __init__(self, snapshot, *, manifest_name="manifest.json"):
        if type(snapshot) is not ProofSnapshot:
            raise TypeError("snapshot reader requires the exact ProofSnapshot")
        object.__setattr__(self, "_snapshot", snapshot)
        object.__setattr__(self, "_manifest_name", manifest_name)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name, value):
        raise TypeError("snapshot proof reader is immutable")

    def __call__(self, root, name, expected):
        selected = self._manifest_name if name == "manifest.json" else name
        return self._snapshot.proof(root, selected, expected)

    def context_for(self, root, manifest, builder):
        return self._snapshot.context_for(root, manifest, builder)

    def metadata_for(self, root, manifest, builder):
        return self._snapshot.metadata_for(root, manifest, builder)

    def remap_manifest(self, name):
        return SnapshotProofReader(self._snapshot, manifest_name=name)


def current():
    return _CURRENT.get()


def install(root, manifest):
    snapshot = ProofSnapshot(root, manifest)
    snapshot.assert_manifest(root, manifest)
    token = _CURRENT.set(snapshot)
    try:
        yield snapshot
    finally:
        _CURRENT.reset(token)
