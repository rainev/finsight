"""Capture immutable, non-serving SEC source packets for controlled Batch 01."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Protocol

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_ROOT = _PROJECT_ROOT / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.us_valuation.batch_01 import BATCH_01_MANIFEST, BATCH_01_VALUATION_DATE, BatchIssuer
from app.us_valuation.sec_client import SecClient, normalize_cik


class _SecClient(Protocol):
    def submissions(self, cik: str, *, refresh: bool = False) -> dict[str, Any]: ...

    def companyfacts(self, cik: str, *, refresh: bool = False) -> dict[str, Any]: ...


_ELIGIBLE_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})
_DEFAULT_PROTECTED_ROOTS = (
    _PROJECT_ROOT / "backend/app/data/us_valuations",
    _PROJECT_ROOT / "frontend/public/data",
    _PROJECT_ROOT / "frontend/src/research/generated",
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for item in sorted(path for path in root.rglob("*") if path.is_file()):
        digest.update(item.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _assert_non_serving(output_root: Path, protected_roots: tuple[Path, ...]) -> None:
    if any(_is_within(output_root, root) for root in protected_roots):
        raise ValueError("output root must be outside every protected serving root")


def _identity(issuer: BatchIssuer, submissions: Mapping[str, Any], facts: Mapping[str, Any]) -> None:
    if normalize_cik(submissions.get("cik", "")) != issuer.cik:
        raise ValueError(f"{issuer.ticker}: submissions CIK identity mismatch")
    if normalize_cik(facts.get("cik", "")) != issuer.cik:
        raise ValueError(f"{issuer.ticker}: companyfacts CIK identity mismatch")
    if issuer.ticker not in submissions.get("tickers", []):
        raise ValueError(f"{issuer.ticker}: submissions ticker identity mismatch")
    source_name = submissions.get("name")
    facts_name = facts.get("entityName")
    if not isinstance(source_name, str) or not source_name:
        raise ValueError(f"{issuer.ticker}: submissions issuer name is missing")
    if not isinstance(facts_name, str) or not facts_name:
        raise ValueError(f"{issuer.ticker}: companyfacts issuer name is missing")


def _filing_ledger(submissions: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    recent = submissions.get("filings", {}).get("recent", {})
    fields = ("accessionNumber", "filingDate", "form", "primaryDocument")
    lengths = {field: len(recent.get(field, [])) for field in fields}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"recent filing arrays have uneven lengths: {lengths}")
    rows = zip(*(recent.get(field, []) for field in fields))
    eligible: list[dict[str, str]] = []
    future: list[dict[str, str]] = []
    ineligible: list[dict[str, str]] = []
    as_of = date.fromisoformat(BATCH_01_VALUATION_DATE)
    for accession, filed, form, primary_document in rows:
        row = {
            "accession": str(accession), "filed": str(filed),
            "form": str(form), "primary_document": str(primary_document),
        }
        try:
            filing_date = date.fromisoformat(row["filed"])
        except ValueError:
            ineligible.append({**row, "reason": "invalid_filing_date"})
            continue
        if filing_date > as_of:
            future.append(row)
        elif row["form"] in _ELIGIBLE_FORMS:
            eligible.append(row)
        else:
            ineligible.append({**row, "reason": "ineligible_form"})
    return eligible, future, ineligible


def _packet_payloads(
    issuer: BatchIssuer,
    submissions: dict[str, Any],
    facts: dict[str, Any],
    *,
    submissions_fetch_metadata: Mapping[str, object],
    companyfacts_fetch_metadata: Mapping[str, object],
) -> dict[str, bytes]:
    _identity(issuer, submissions, facts)
    submissions_raw = _json_bytes(submissions)
    facts_raw = _json_bytes(facts)
    submissions_url = f"https://data.sec.gov/submissions/CIK{issuer.cik}.json"
    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{issuer.cik}.json"
    eligible, future, ineligible = _filing_ledger(submissions)
    files = {
        "submissions.json": {"source_url": submissions_url, "sha256": _sha256(submissions_raw), "fetch_metadata": _provenance(submissions_url, submissions_raw, submissions_fetch_metadata)},
        "companyfacts.json": {"source_url": facts_url, "sha256": _sha256(facts_raw), "fetch_metadata": _provenance(facts_url, facts_raw, companyfacts_fetch_metadata)},
    }
    submissions_meta_raw = _json_bytes(files["submissions.json"])
    facts_meta_raw = _json_bytes(files["companyfacts.json"])
    source_manifest = {
        "schema_version": "FINSIGHT-BATCH-01-SOURCE-1",
        "valuation_date": BATCH_01_VALUATION_DATE,
        "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name},
        "source_identity": {"submissions_name": submissions["name"], "companyfacts_name": facts["entityName"]},
        "files": files,
        "eligible_filings": eligible,
        "future_filings": future,
        "ineligible_filings": ineligible,
        "evidence": {"accepted": [], "rejected": [], "missing": [], "conflicting": []},
        "packet_payload_sha256": {
            "submissions.json": _sha256(submissions_raw),
            "submissions.meta.json": _sha256(submissions_meta_raw),
            "companyfacts.json": _sha256(facts_raw),
            "companyfacts.meta.json": _sha256(facts_meta_raw),
        },
    }
    return {
        "submissions.json": submissions_raw,
        "submissions.meta.json": submissions_meta_raw,
        "companyfacts.json": facts_raw,
        "companyfacts.meta.json": facts_meta_raw,
        "source-manifest.json": _json_bytes(source_manifest),
    }


def _provenance(
    source_url: str,
    raw: bytes,
    cache_metadata: Mapping[str, object],
) -> dict[str, object]:
    """Retain SEC cache provenance or state precisely why it is unavailable."""
    metadata = dict(cache_metadata)
    return {
        "source_url": metadata.get("source_url", source_url),
        "sha256": metadata.get("sha256", _sha256(raw)),
        "fetched_at_epoch": metadata.get("fetched_at_epoch"),
        "cache_file_mtime_epoch": metadata.get("cache_file_mtime_epoch"),
        "provenance_status": metadata.get("provenance_status", "unavailable_from_client"),
    }


def _fetch_metadata(client: _SecClient, cik: str, filename: str) -> Mapping[str, object]:
    """Copy SecClient's recorded cache provenance when available."""
    cache_dir = getattr(client, "cache_dir", None)
    if not isinstance(cache_dir, Path):
        return {}
    metadata_path = cache_dir / f"CIK{cik}-{filename}.meta.json"
    if not metadata_path.exists():
        return {}
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise RuntimeError(f"invalid SEC cache metadata: {metadata_path.name}")
    return metadata


def _publish_packet(destination: Path, payloads: Mapping[str, bytes]) -> None:
    if destination.exists():
        existing = {path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()}
        if existing == dict(payloads):
            return
        raise FileExistsError(f"refusing to overwrite differing source packet: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        for filename, raw in payloads.items():
            (staging / filename).write_bytes(raw)
        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def capture_sources(
    *,
    output_root: Path,
    user_agent: str | None = None,
    refresh: bool = False,
    client: _SecClient | None = None,
    protected_serving_roots: tuple[Path, ...] = _DEFAULT_PROTECTED_ROOTS,
) -> dict[str, object]:
    """Write one deterministic SEC packet per frozen issuer, outside serving data."""
    output_root = Path(output_root)
    protected_roots = tuple(Path(root) for root in protected_serving_roots)
    _assert_non_serving(output_root, protected_roots)
    before = {str(root): _tree_hash(root) for root in protected_roots}
    if client is None:
        client = SecClient(
            user_agent=user_agent,
            cache_dir=output_root.parent / ".sec-cache",
        )
    payloads: dict[str, dict[str, bytes]] = {}
    for issuer in BATCH_01_MANIFEST:
        submissions = client.submissions(issuer.cik, refresh=refresh)
        facts = client.companyfacts(issuer.cik, refresh=refresh)
        payloads[issuer.ticker] = _packet_payloads(
            issuer,
            submissions,
            facts,
            submissions_fetch_metadata=_fetch_metadata(client, issuer.cik, "submissions.json"),
            companyfacts_fetch_metadata=_fetch_metadata(client, issuer.cik, "companyfacts.json"),
        )
    if output_root.exists():
        present = {path.name for path in output_root.iterdir() if path.is_dir()}
        unexpected = present - set(payloads)
        if unexpected:
            raise FileExistsError(f"unexpected packet directories: {sorted(unexpected)}")
    for ticker, packet in payloads.items():
        _publish_packet(output_root / ticker, packet)
    after = {str(root): _tree_hash(root) for root in protected_roots}
    return {
        "manifest_count": len(BATCH_01_MANIFEST),
        "source_packet_count": len(payloads),
        "serving_artifacts_changed": before != after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(capture_sources(output_root=args.output_root, user_agent=args.user_agent, refresh=args.refresh), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
