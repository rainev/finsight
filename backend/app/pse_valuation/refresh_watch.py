"""One internal filing-watch tick and stage-only reviewed-bundle scheduler.

External metadata polling is disabled unless a versioned source record explicitly
allows it. This module never downloads filings, extracts financial facts from
PDFs, changes the active pointer, or approves a valuation.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import tempfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .catalog import load_pointer
from .contract import PseValuationArtifact
from .internal_refresh import BUNDLE_SCHEMA, PILOT_ROUTES, stage_internal_refresh
from .summary_snapshots import PSE_SUMMARY_URLS, active_period, compare_snapshot, read_snapshot


WATCH_SCHEMA = "PSE-V2-INTERNAL-FILING-WATCH-1.0"
TICKERS = frozenset(PILOT_ROUTES)
FetchIndex = Callable[[str], bytes]


class _PdfLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if isinstance(href, str):
                self.hrefs.append(href)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    temporary = path.with_name(path.name + ".new")
    temporary.write_bytes(raw)
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: expected a JSON object")
    return payload


def _source_url(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("source index URL is missing")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("source index must be a plain HTTPS URL")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"} or parsed.hostname.endswith(".local"):
        raise ValueError("local addresses are not external issuer sources")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("private IP addresses are not issuer sources")
    return value


def parse_index_links(raw: bytes, index_url: str, path_pattern: str) -> list[str]:
    """Find same-host PDF links; discovery is metadata, not a filing review."""
    if len(raw) > 2_000_000:
        raise ValueError("source index exceeds the 2 MB metadata limit")
    parser = _PdfLinks()
    parser.feed(raw.decode("utf-8", errors="replace"))
    host = urlsplit(index_url).hostname
    pattern = re.compile(path_pattern, re.IGNORECASE)
    links: set[str] = set()
    for href in parser.hrefs:
        url = urljoin(index_url, href)
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname != host or parts.username or parts.password or parts.query:
            continue
        if not parts.path.lower().endswith(".pdf") or not pattern.search(parts.path):
            continue
        links.add(urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")))
    return sorted(links)


def _fetch_index(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "FinSight-internal-filing-watch/1.0"})
    with urlopen(request, timeout=15) as response:
        if response.url and urlsplit(response.url).hostname != urlsplit(url).hostname:
            raise ValueError("source index redirected to another host")
        if "text/html" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("source index did not return HTML metadata")
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("source index exceeds the 2 MB metadata limit")
    return raw


def _config(path: Path) -> dict[str, Any]:
    config = _read_json(path)
    if config.get("schema_version") != WATCH_SCHEMA or not isinstance(config.get("sources"), list):
        raise ValueError("unsupported PSE filing-watch source registry")
    ids: set[str] = set()
    for row in config["sources"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] or row["id"] in ids:
            raise ValueError("filing-watch source IDs must be unique")
        if row.get("ticker") not in TICKERS:
            raise ValueError("filing-watch source is outside the pilot")
        ids.add(row["id"])
        if row.get("automated_metadata_access_allowed") is True:
            if not isinstance(row.get("rights_record"), str) or not row["rights_record"].strip():
                raise ValueError(f"{row['id']}: cleared metadata access needs a rights record")
            _source_url(row.get("index_url"))
            if not isinstance(row.get("pdf_path_pattern"), str) or not row["pdf_path_pattern"]:
                raise ValueError(f"{row['id']}: reviewed PDF path pattern is required")
            re.compile(row["pdf_path_pattern"])
    return config


def _state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": WATCH_SCHEMA, "source_snapshots": {}, "processed_bundles": {}, "summary_snapshots": {}, "pending_summary_changes": {}}
    state = _read_json(path)
    if state.get("schema_version") != WATCH_SCHEMA or not isinstance(state.get("source_snapshots"), dict) or not isinstance(state.get("processed_bundles"), dict):
        raise ValueError("filing-watch state is invalid")
    for key in ("summary_snapshots", "pending_summary_changes"):
        if not isinstance(state.setdefault(key, {}), dict):
            raise ValueError("filing-watch summary state is invalid")
    return state


def _bundle_covers_summary(bundle_path: Path, cases: dict, pending: dict[str, dict]) -> list[str]:
    """Require a pinned reviewed receipt for each changed issuer before staging."""
    ready = [ticker for ticker, case in cases.items() if case.get("status") == "ready"]
    if not ready:
        raise ValueError("reviewed bundle has no ready issuer")
    for ticker in ready:
        change = pending.get(ticker)
        if change is None:
            raise ValueError(f"{ticker}: no changed financial-summary snapshot is pending")
        relative = cases[ticker].get("receipt_path")
        expected = cases[ticker].get("receipt_sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError(f"{ticker}: pinned reviewed receipt is required")
        safe = PurePosixPath(relative)
        if safe.is_absolute() or not safe.parts or any(part in {".", ".."} for part in safe.parts):
            raise ValueError(f"{ticker}: receipt path is unsafe")
        unresolved = bundle_path.parent / Path(*safe.parts)
        path = unresolved.resolve()
        if bundle_path.parent not in path.parents or unresolved.is_symlink():
            raise ValueError(f"{ticker}: receipt must stay in the reviewed bundle")
        raw = path.read_bytes()
        if _sha256(raw) != expected:
            raise ValueError(f"{ticker}: reviewed receipt hash mismatch")
        receipt = json.loads(raw)
        if not isinstance(receipt, dict) or receipt.get("ticker") != ticker:
            raise ValueError(f"{ticker}: reviewed receipt identity differs")
        receipt_period = date.fromisoformat(receipt["period_end"])
        changed_period = date.fromisoformat(change["period_end"])
        if receipt_period < changed_period:
            raise ValueError(f"{ticker}: reviewed receipt predates the changed summary period")
        if change["reason"] == "restated_summary" and receipt.get("trigger") != "amended_filing":
            raise ValueError(f"{ticker}: a restated summary needs a reviewed amended-filing receipt")
    return ready


def run_once(
    *, config_path: Path, bundle_inbox: Path, stage_root: Path, state_dir: Path,
    catalogs_root: Path, fetch_index: FetchIndex = _fetch_index, summary_dir: Path | None = None,
) -> dict[str, Any]:
    """Run one tick; summary_dir selects offline snapshot comparison only."""
    config = _config(config_path)
    bundle_inbox = bundle_inbox.resolve()
    stage_root = stage_root.resolve()
    state_dir = state_dir.resolve()
    catalogs_root = catalogs_root.resolve()
    if summary_dir is not None:
        summary_dir = summary_dir.resolve()
        if not summary_dir.is_dir():
            raise FileNotFoundError(f"saved summary snapshot directory is missing: {summary_dir}")
        if any(summary_dir == root or summary_dir in root.parents or root in summary_dir.parents for root in (stage_root, state_dir, catalogs_root, bundle_inbox)):
            raise ValueError("summary snapshots must be separate from inbox, state, candidates, and serving catalogs")
    if any(root == catalogs_root or catalogs_root in root.parents or root in catalogs_root.parents for root in (stage_root, state_dir)):
        raise ValueError("scheduler state and candidates must stay outside serving catalogs")
    if stage_root == state_dir or stage_root in state_dir.parents or state_dir in stage_root.parents:
        raise ValueError("scheduler state and candidate roots must be separate")
    if bundle_inbox == stage_root or bundle_inbox in stage_root.parents or stage_root in bundle_inbox.parents:
        raise ValueError("reviewed bundle inbox and candidate root must be separate")
    if not bundle_inbox.is_dir():
        raise FileNotFoundError(f"reviewed bundle inbox is missing: {bundle_inbox}")
    state = _state(state_dir / "state.json")
    pointer_before = (catalogs_root / "active.json").read_bytes()
    active = load_pointer(catalogs_root, "active.json")
    report: dict[str, Any] = {
        "schema_version": WATCH_SCHEMA,
        "active_parent_catalog": active.version,
        "active_parent_manifest_sha256": active.manifest_sha256,
        "source_checks": {}, "new_filing_links": [], "summary_checks": {}, "pending_summary_changes": {},
        "staged": [], "skipped": [], "holds": [],
        "active_changed": False,
    }
    if summary_dir is not None:
        for ticker in sorted(PSE_SUMMARY_URLS):
            path = summary_dir / f"{ticker}.json"
            if not path.exists() and not path.is_symlink():
                report["summary_checks"][ticker] = "not_supplied"
                continue
            try:
                observation = read_snapshot(path, ticker)
                previous = state["summary_snapshots"].get(ticker)
                parent = PseValuationArtifact.model_validate_json(active.verify_artifact(ticker).read_bytes())
                outcome = compare_snapshot(observation, previous, active_period(parent))
                report["summary_checks"][ticker] = outcome
                if outcome == "stale_period_held":
                    continue
                state["summary_snapshots"][ticker] = {
                    "period_end": observation.period_end.isoformat(), "snapshot_sha256": observation.digest,
                }
                if outcome in {"new_period", "restated_summary"}:
                    state["pending_summary_changes"][ticker] = {
                        "period_end": observation.period_end.isoformat(),
                        "snapshot_sha256": observation.digest, "reason": outcome,
                    }
            except (OSError, ValueError, TypeError, KeyError) as exc:
                report["summary_checks"][ticker] = f"held: {exc}"
        report["pending_summary_changes"] = dict(state["pending_summary_changes"])
    for source in config["sources"]:
        source_id = source["id"]
        if summary_dir is not None:
            report["source_checks"][source_id] = "disabled_offline_snapshot_mode"
            continue
        if source.get("automated_metadata_access_allowed") is not True:
            report["source_checks"][source_id] = "disabled_pending_source_rights"
            continue
        try:
            index_url = _source_url(source["index_url"])
            raw = fetch_index(index_url)
            links = parse_index_links(raw, index_url, source["pdf_path_pattern"])
            previous = state["source_snapshots"].get(source_id)
            new_links: list[str] = []
            if previous is not None:
                new_links = sorted(set(links) - set(previous["links"]))
                for url in new_links:
                    report["new_filing_links"].append({
                        "ticker": source["ticker"], "source_id": source_id, "url": url,
                        "status": "needs_fact_and_rights_review",
                    })
            state["source_snapshots"][source_id] = {"index_sha256": _sha256(raw), "links": links}
            report["source_checks"][source_id] = (
                "baseline_recorded" if previous is None else
                "index_changed_review_needed" if previous["index_sha256"] != _sha256(raw) and not new_links else
                "checked"
            )
        except (OSError, UnicodeError, ValueError) as exc:
            report["source_checks"][source_id] = f"held: {exc}"
    for bundle_path in sorted(bundle_inbox.glob("*/bundle.json")):
        if bundle_path.is_symlink() or bundle_path.parent.is_symlink():
            report["holds"].append({"bundle": bundle_path.parent.name, "reason": "unsafe bundle symlink"})
            continue
        try:
            raw = bundle_path.read_bytes()
            bundle = json.loads(raw)
            if not isinstance(bundle, dict) or bundle.get("schema_version") != BUNDLE_SCHEMA:
                raise ValueError("unsupported reviewed bundle")
            version = bundle.get("catalog_version")
            if not isinstance(version, str) or not re.fullmatch(r"PSE-V2-REFRESH-[A-Za-z0-9._-]+", version):
                raise ValueError("invalid reviewed catalog version")
            cases = bundle.get("cases")
            if not isinstance(cases, dict) or set(cases) != TICKERS:
                raise ValueError("reviewed bundle must state the four pilot issuers")
            if not isinstance(cases["RLC"], dict) or cases["RLC"].get("status") != "hold":
                raise ValueError("RLC stays on hold until a separate ownership-bridge decision")
            digest = _sha256(raw)
            output_root = stage_root / version
            processed = state["processed_bundles"].get(digest)
            if processed:
                catalog = load_pointer(output_root)
                if catalog.manifest_sha256 != processed["manifest_sha256"]:
                    raise ValueError("previously staged candidate changed")
                report["skipped"].append({"bundle": bundle_path.parent.name, "reason": "already_staged", "catalog_version": version})
                continue
            if output_root.exists():
                raise ValueError("candidate path already exists for a different reviewed bundle")
            ready = []
            if summary_dir is not None:
                ready = _bundle_covers_summary(bundle_path, cases, state["pending_summary_changes"])
                for ticker in ready:
                    if report["summary_checks"].get(ticker) in {"not_supplied", "stale_period_held"} or str(report["summary_checks"].get(ticker, "")).startswith("held:"):
                        raise ValueError(f"{ticker}: a valid current summary snapshot is required")
            stage_root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="pse-refresh-", dir=stage_root) as temporary:
                temporary_output = Path(temporary) / "candidate"
                stage_internal_refresh(bundle_path, temporary_output, catalogs_root)
                load_pointer(temporary_output)
                refresh_details = _read_json(temporary_output / "refresh_report.json")
                changed = refresh_details.get("changed")
                if not isinstance(changed, dict) or not changed or not set(changed) <= set(cases):
                    raise ValueError("staged refresh report has invalid changed issuers")
                temporary_output.rename(output_root)
            catalog = load_pointer(output_root)
            state["processed_bundles"][digest] = {"catalog_version": version, "manifest_sha256": catalog.manifest_sha256}
            report["staged"].append({"bundle": bundle_path.parent.name, "catalog_version": version, "catalog_root": str(output_root / version), "manifest_sha256": catalog.manifest_sha256, "changed_tickers": sorted(changed), "model_holds": refresh_details.get("holds", {})})
            for ticker in ready:
                if ticker in changed:
                    state["pending_summary_changes"].pop(ticker, None)
            report["pending_summary_changes"] = dict(state["pending_summary_changes"])
        except (OSError, TypeError, KeyError, ValueError, json.JSONDecodeError) as exc:
            report["holds"].append({"bundle": bundle_path.parent.name, "reason": str(exc)})
    if (catalogs_root / "active.json").read_bytes() != pointer_before:
        raise ValueError("active catalog changed during filing-watch tick")
    state_dir.mkdir(parents=True, exist_ok=True)
    _write_json(state_dir / "state.json", state)
    _write_json(state_dir / "last_report.json", report)
    return report
