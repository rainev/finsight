#!/usr/bin/env python3
"""Build one immutable, manifest-controlled U.S. valuation catalog.

Examples:

  # Initial reset catalog from confirmed batch outputs.
  python scripts/build_us_valuation_catalog.py --catalog-kind reset ...

  # Next catalog version, extending an existing immutable catalog.
  python scripts/build_us_valuation_catalog.py --base-catalog <version-root> \
      --batch-source 11:<public-root>:docs/audit/<report>.md ...

Building never activates a catalog.  Use ``activate_us_valuation_catalog.py``
as a separate, explicit step after verification.
"""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.artifacts import sanitize_public_artifact  # noqa: E402
from app.us_valuation.baseline import apply_public_baseline_contract  # noqa: E402
from app.us_valuation.catalog import (  # noqa: E402
    CATALOG_SCHEMA,
    AVAILABILITY_TYPES,
    artifact_tree_sha256,
    canonical_json_bytes,
    load_catalog_version,
    sha256_bytes,
)


FORBIDDEN_PUBLIC_KEYS = {
    "financials",
    "source_ledger",
    "company_history_profile",
    "flow_sources",
    "bridge_sources",
    "event_and_bridge_sources",
    "input_provenance",
    "source_manifest",
    "reported_inputs",
}


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _private_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_PUBLIC_KEYS:
                found.add(key)
            found.update(_private_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_private_keys(child))
    return found


def _cik(value: object) -> str:
    normalized = str(value or "").strip()
    if not normalized.isdigit() or len(normalized) > 10:
        raise ValueError(f"invalid CIK {value!r}")
    return normalized.zfill(10)


def _availability(artifact: dict[str, Any], *, legacy: bool) -> str:
    if legacy:
        public = apply_public_baseline_contract(sanitize_public_artifact(artifact))
        result = public.get("availability_type")
    else:
        result = artifact.get("availability_type")
    if result not in AVAILABILITY_TYPES:
        raise ValueError(f"invalid availability type {result!r}")
    return str(result)


def _artifact(
    path: Path,
    *,
    expected_ticker: str | None,
    expected_cik: str | None,
    legacy: bool,
) -> tuple[bytes, dict[str, Any], str, str, str]:
    raw = path.read_bytes()
    value = _read_object(path)
    ticker = str(value.get("ticker") or value.get("issuer", {}).get("ticker") or "")
    issuer = value.get("issuer")
    if not ticker or not isinstance(issuer, dict) or issuer.get("ticker") != ticker:
        raise ValueError(f"{path}: public artifact identity is invalid")
    cik = _cik(issuer.get("cik"))
    if path.stem != ticker:
        raise ValueError(f"{path}: filename and ticker differ")
    if expected_ticker is not None and ticker != expected_ticker:
        raise ValueError(f"{path}: expected ticker {expected_ticker}")
    if expected_cik is not None and cik != expected_cik:
        raise ValueError(f"{ticker}: expected CIK {expected_cik}, got {cik}")
    if not legacy:
        forbidden = _private_keys(value)
        if forbidden:
            raise ValueError(f"{ticker}: private keys reached public artifact: {sorted(forbidden)}")
    return raw, value, ticker, cik, _availability(value, legacy=legacy)


def _batch_manifest(batch: int) -> tuple[tuple[str, str], ...]:
    module = importlib.import_module(f"app.us_valuation.batch_{batch:02d}")
    manifest = getattr(module, f"BATCH_{batch:02d}_MANIFEST")
    rows = tuple((str(row.ticker), _cik(row.cik)) for row in manifest)
    if len(rows) != 10 or len({ticker for ticker, _ in rows}) != 10:
        raise ValueError(f"Batch {batch:02d} manifest is not exactly ten unique issuers")
    return rows


def _parse_batch_source(value: str) -> tuple[int, Path, str]:
    try:
        batch_text, root_text, audit = value.split(":", 2)
        batch = int(batch_text)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(
            "batch source must be BATCH:PUBLIC_ROOT:SOURCE_AUDIT"
        ) from exc
    root = Path(root_text)
    if batch < 1 or not root.is_dir() or not audit:
        raise argparse.ArgumentTypeError("batch source is incomplete")
    return batch, root, audit


def _tree_bytes(root: Path) -> bytes:
    ledger = bytearray()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix().encode("utf-8")
            ledger.extend(relative + b"\0" + sha256_bytes(path.read_bytes()).encode() + b"\n")
    return bytes(ledger)


def _publish_immutable(candidate: Path, target: Path) -> None:
    if target.exists():
        if _tree_bytes(candidate) != _tree_bytes(target):
            raise FileExistsError(f"immutable catalog differs: {target}")
        shutil.rmtree(candidate)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    candidate.replace(target)


def build_catalog(
    *,
    catalog_kind: str,
    target_root: Path,
    catalog_version: str,
    universe_version: str,
    valuation_date: str,
    created_at: str,
    batch_sources: Iterable[tuple[int, Path, str]] = (),
    base_catalog: Path | None = None,
    legacy_source_root: Path | None = None,
    legacy_source_commit: str | None = None,
    legacy_source_tree: str | None = None,
    expected_count: int | None = None,
    expected_availability: dict[str, int] | None = None,
    expected_publication: dict[str, int] | None = None,
) -> dict[str, Any]:
    if catalog_kind not in {"reset", "legacy_archive"}:
        raise ValueError("catalog kind must be reset or legacy_archive")
    target_root = Path(target_root).resolve()
    target_root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target_root.name}-", dir=target_root.parent))
    artifacts_root = stage / "artifacts"
    artifacts_root.mkdir()
    entries: dict[str, dict[str, Any]] = {}
    publication_counts: Counter[str] = Counter()
    included_batches: set[int] = set()
    source_batches: dict[str, dict[str, Any]] = {}

    try:
        if base_catalog is not None:
            if catalog_kind != "reset":
                raise ValueError("only reset catalogs can extend a base catalog")
            base = load_catalog_version(base_catalog)
            included_batches.update(base.included_batches)
            for entry in base.entries:
                raw = base.artifact_path(entry.ticker).read_bytes()
                (artifacts_root / f"{entry.ticker}.json").write_bytes(raw)
                base_value = json.loads(raw)
                publication_counts[
                    str(base_value.get("review", {}).get("publication_state", "missing"))
                ] += 1
                entries[entry.ticker] = {
                    "ticker": entry.ticker,
                    "cik": entry.cik,
                    "batch": entry.batch,
                    "availability_type": entry.availability_type,
                    "artifact_sha256": entry.artifact_sha256,
                    "source_audit": entry.source_audit,
                }

        parsed_sources = sorted(batch_sources, key=lambda row: row[0])
        if catalog_kind == "reset" and not parsed_sources and base_catalog is None:
            raise ValueError("a reset catalog needs at least one batch source")
        for batch, source_root, source_audit in parsed_sources:
            if batch in included_batches:
                raise ValueError(f"Batch {batch:02d} is already present in the base catalog")
            expected = _batch_manifest(batch)
            source_files = sorted(source_root.glob("*.json"))
            if {path.stem for path in source_files} != {ticker for ticker, _ in expected}:
                raise ValueError(f"Batch {batch:02d} source does not match its frozen manifest")
            for ticker, cik in expected:
                raw, value, actual_ticker, actual_cik, availability = _artifact(
                    source_root / f"{ticker}.json",
                    expected_ticker=ticker,
                    expected_cik=cik,
                    legacy=False,
                )
                if actual_ticker in entries:
                    raise ValueError(f"{actual_ticker}: duplicate ticker across catalogs")
                (artifacts_root / f"{actual_ticker}.json").write_bytes(raw)
                entries[actual_ticker] = {
                    "ticker": actual_ticker,
                    "cik": actual_cik,
                    "batch": batch,
                    "availability_type": availability,
                    "artifact_sha256": sha256_bytes(raw),
                    "source_audit": source_audit,
                }
                publication_counts[str(value.get("review", {}).get("publication_state", "missing"))] += 1
            included_batches.add(batch)
            source_batches[f"{batch:02d}"] = {
                "source_audit": source_audit,
                "source_root": source_root.as_posix(),
                "artifact_count": 10,
            }

        if catalog_kind == "legacy_archive":
            if base_catalog is not None or parsed_sources or legacy_source_root is None:
                raise ValueError("legacy archive requires only --legacy-source-root")
            source_files = sorted(Path(legacy_source_root).glob("*.json"))
            if not source_files:
                raise ValueError("legacy archive source is empty")
            for path in source_files:
                raw, value, ticker, cik, availability = _artifact(
                    path,
                    expected_ticker=None,
                    expected_cik=None,
                    legacy=True,
                )
                (artifacts_root / path.name).write_bytes(raw)
                entries[ticker] = {
                    "ticker": ticker,
                    "cik": cik,
                    "batch": None,
                    "availability_type": availability,
                    "artifact_sha256": sha256_bytes(raw),
                    "source_audit": f"Legacy serving snapshot from {legacy_source_commit}",
                }
                publication_counts[str(value.get("review", {}).get("publication_state", "missing"))] += 1

        ordered = [entries[ticker] for ticker in sorted(entries)]
        availability_counts = Counter(str(entry["availability_type"]) for entry in ordered)
        normalized_availability = {
            name: availability_counts.get(name, 0) for name in sorted(AVAILABILITY_TYPES)
        }
        if expected_count is not None and len(ordered) != expected_count:
            raise ValueError(f"expected {expected_count} artifacts, got {len(ordered)}")
        if expected_availability is not None and normalized_availability != expected_availability:
            raise ValueError(
                f"availability counts differ: {normalized_availability} != {expected_availability}"
            )
        normalized_publication = dict(sorted(publication_counts.items()))
        if expected_publication is not None and normalized_publication != expected_publication:
            raise ValueError(
                f"publication counts differ: {normalized_publication} != {expected_publication}"
            )

        manifest: dict[str, Any] = {
            "schema_version": CATALOG_SCHEMA,
            "catalog_kind": catalog_kind,
            "catalog_version": catalog_version,
            "universe_version": universe_version,
            "valuation_date": valuation_date,
            "created_at": created_at,
            "included_batches": sorted(included_batches),
            "artifact_count": len(ordered),
            "availability_counts": normalized_availability,
            "publication_counts": normalized_publication,
            "artifact_tree_sha256": artifact_tree_sha256(ordered),
            "entries": ordered,
        }
        if base_catalog is not None:
            manifest["base_catalog_version"] = load_catalog_version(base_catalog).catalog_version
        if source_batches:
            manifest["source_batches"] = source_batches
        if catalog_kind == "legacy_archive":
            manifest["legacy_source"] = {
                "commit": legacy_source_commit,
                "git_tree": legacy_source_tree,
                "rollback": "Activate this catalog only in an isolated rollback configuration, then verify every public boundary before serving it.",
            }
        (stage / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        load_catalog_version(stage)
        _publish_immutable(stage, target_root)
        return manifest
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def _counts(values: list[str]) -> dict[str, int] | None:
    if not values:
        return None
    result: dict[str, int] = {}
    for value in values:
        name, count = value.split("=", 1)
        result[name] = int(count)
    return dict(sorted(result.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-kind", choices=("reset", "legacy_archive"), required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--catalog-version", required=True)
    parser.add_argument("--universe-version", required=True)
    parser.add_argument("--valuation-date", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--batch-source", action="append", default=[], type=_parse_batch_source)
    parser.add_argument("--base-catalog", type=Path)
    parser.add_argument("--legacy-source-root", type=Path)
    parser.add_argument("--legacy-source-commit")
    parser.add_argument("--legacy-source-tree")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--expected-availability", action="append", default=[])
    parser.add_argument("--expected-publication", action="append", default=[])
    args = parser.parse_args()
    manifest = build_catalog(
        catalog_kind=args.catalog_kind,
        target_root=args.target_root,
        catalog_version=args.catalog_version,
        universe_version=args.universe_version,
        valuation_date=args.valuation_date,
        created_at=args.created_at,
        batch_sources=args.batch_source,
        base_catalog=args.base_catalog,
        legacy_source_root=args.legacy_source_root,
        legacy_source_commit=args.legacy_source_commit,
        legacy_source_tree=args.legacy_source_tree,
        expected_count=args.expected_count,
        expected_availability=_counts(args.expected_availability),
        expected_publication=_counts(args.expected_publication),
    )
    print(
        json.dumps(
            {
                "catalog_version": manifest["catalog_version"],
                "artifact_count": manifest["artifact_count"],
                "included_batches": manifest["included_batches"],
                "availability_counts": manifest["availability_counts"],
                "artifact_tree_sha256": manifest["artifact_tree_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
