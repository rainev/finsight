"""Capture immutable, non-serving SEC source packets for frozen Batch 02."""

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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.us_valuation.batch_02 import BATCH_02_MANIFEST, BATCH_02_VALUATION_DATE, Batch02Issuer
from app.us_valuation.sec_client import SecClient, normalize_cik

ELIGIBLE_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})
PROTECTED_ROOTS = tuple(PROJECT_ROOT / path for path in (
    "backend/app/data/us_valuations", "frontend/public/data", "frontend/src/research/generated",
))


class _SecClient(Protocol):
    def submissions(self, cik: str, *, refresh: bool = False) -> dict[str, Any]: ...
    def companyfacts(self, cik: str, *, refresh: bool = False) -> dict[str, Any]: ...


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for item in sorted(path for path in root.rglob("*") if path.is_file()):
            digest.update(item.relative_to(root).as_posix().encode()); digest.update(b"\0")
            digest.update(item.read_bytes()); digest.update(b"\0")
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


def _provenance(url: str, raw: bytes, metadata: Mapping[str, object]) -> dict[str, object]:
    return {"source_url": metadata.get("source_url", url), "sha256": metadata.get("sha256", _sha256(raw)),
            "fetched_at_epoch": metadata.get("fetched_at_epoch"), "cache_file_mtime_epoch": metadata.get("cache_file_mtime_epoch"),
            "provenance_status": metadata.get("provenance_status", "unavailable_from_client")}


def _fetch_metadata(client: _SecClient, cik: str, filename: str) -> Mapping[str, object]:
    cache_dir = getattr(client, "cache_dir", None)
    path = cache_dir / f"CIK{cik}-{filename}.meta.json" if isinstance(cache_dir, Path) else None
    if path is None or not path.exists():
        return {}
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError(f"invalid SEC cache metadata: {path.name}")
    return result


def _packet_payloads(
    issuer: Batch02Issuer,
    submissions: dict[str, Any],
    facts: dict[str, Any],
    *,
    submissions_metadata: Mapping[str, object],
    facts_metadata: Mapping[str, object],
    valuation_date: str = BATCH_02_VALUATION_DATE,
    schema_version: str = "FINSIGHT-BATCH-02-SOURCE-1",
) -> dict[str, bytes]:
    if normalize_cik(submissions.get("cik", "")) != issuer.cik or normalize_cik(facts.get("cik", "")) != issuer.cik:
        raise ValueError(f"{issuer.ticker}: SEC CIK identity mismatch")
    if issuer.ticker not in submissions.get("tickers", []):
        raise ValueError(f"{issuer.ticker}: submissions ticker identity mismatch")
    if not submissions.get("name") or not facts.get("entityName"):
        raise ValueError(f"{issuer.ticker}: SEC issuer name is missing")
    recent = submissions.get("filings", {}).get("recent", {})
    fields = ("accessionNumber", "filingDate", "form", "primaryDocument")
    if len({len(recent.get(field, [])) for field in fields}) != 1:
        raise ValueError("recent filing arrays have uneven lengths")
    eligible: list[dict[str, str]] = []; future: list[dict[str, str]] = []; ineligible: list[dict[str, str]] = []
    for values in zip(*(recent.get(field, []) for field in fields)):
        row = dict(zip(("accession", "filed", "form", "primary_document"), map(str, values)))
        try:
            filed = date.fromisoformat(row["filed"])
        except ValueError:
            ineligible.append({**row, "reason": "invalid_filing_date"}); continue
        if filed > date.fromisoformat(valuation_date): future.append(row)
        elif row["form"] in ELIGIBLE_FORMS: eligible.append(row)
        else: ineligible.append({**row, "reason": "ineligible_form"})
    submissions_raw, facts_raw = _json_bytes(submissions), _json_bytes(facts)
    urls = (f"https://data.sec.gov/submissions/CIK{issuer.cik}.json", f"https://data.sec.gov/api/xbrl/companyfacts/CIK{issuer.cik}.json")
    files = {"submissions.json": {"source_url": urls[0], "sha256": _sha256(submissions_raw), "fetch_metadata": _provenance(urls[0], submissions_raw, submissions_metadata)}, "companyfacts.json": {"source_url": urls[1], "sha256": _sha256(facts_raw), "fetch_metadata": _provenance(urls[1], facts_raw, facts_metadata)}}
    metas = {"submissions.meta.json": _json_bytes(files["submissions.json"]), "companyfacts.meta.json": _json_bytes(files["companyfacts.json"])}
    manifest = {"schema_version": schema_version, "valuation_date": valuation_date, "issuer": {"ticker": issuer.ticker, "cik": issuer.cik, "issuer_name": issuer.issuer_name}, "source_identity": {"submissions_name": submissions["name"], "companyfacts_name": facts["entityName"]}, "files": files, "eligible_filings": eligible, "future_filings": future, "ineligible_filings": ineligible, "evidence": {"accepted": [], "rejected": [], "missing": [], "conflicting": []}, "packet_payload_sha256": {"submissions.json": _sha256(submissions_raw), "submissions.meta.json": _sha256(metas["submissions.meta.json"]), "companyfacts.json": _sha256(facts_raw), "companyfacts.meta.json": _sha256(metas["companyfacts.meta.json"])}}
    return {"submissions.json": submissions_raw, **metas, "companyfacts.json": facts_raw, "source-manifest.json": _json_bytes(manifest)}


def _publish(destination: Path, payloads: Mapping[str, bytes]) -> None:
    if destination.exists():
        existing = {path.name: path.read_bytes() for path in destination.iterdir() if path.is_file()}
        if existing == dict(payloads): return
        raise FileExistsError(f"refusing to overwrite differing source packet: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        for filename, raw in payloads.items(): (staging / filename).write_bytes(raw)
        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True); raise


def capture_sources(*, output_root: Path, user_agent: str | None = None, refresh: bool = False, client: _SecClient | None = None, protected_serving_roots: tuple[Path, ...] = PROTECTED_ROOTS) -> dict[str, object]:
    output_root, roots = Path(output_root), tuple(Path(root) for root in protected_serving_roots)
    _assert_non_serving(output_root, roots); before = {str(root): _tree_hash(root) for root in roots}
    client = client or SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    packets = {issuer.ticker: _packet_payloads(issuer, client.submissions(issuer.cik, refresh=refresh), client.companyfacts(issuer.cik, refresh=refresh), submissions_metadata=_fetch_metadata(client, issuer.cik, "submissions.json"), facts_metadata=_fetch_metadata(client, issuer.cik, "companyfacts.json")) for issuer in BATCH_02_MANIFEST}
    if output_root.exists():
        unexpected = {path.name for path in output_root.iterdir() if path.is_dir()} - set(packets)
        if unexpected: raise FileExistsError(f"unexpected packet directories: {sorted(unexpected)}")
    for ticker, packet in packets.items(): _publish(output_root / ticker, packet)
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after: raise RuntimeError("protected serving artifacts changed")
    return {"manifest_count": len(BATCH_02_MANIFEST), "source_packet_count": len(packets), "serving_artifacts_changed": False, "serving_hash_before": before, "serving_hash_after": after}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output-root", type=Path, required=True); parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT")); parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args(); print(json.dumps(capture_sources(output_root=args.output_root, user_agent=args.user_agent, refresh=args.refresh), sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
