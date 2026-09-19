#!/usr/bin/env python3
"""Build a bounded, metadata-only register for the latest 500-company refresh.

This is a reporting command.  It does not acquire filings, run valuation
calculations, update recipes, or infer that an approved value changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.refresh_work_register import (  # noqa: E402
    canonical_json_bytes,
    implementation_fingerprint,
)


SCHEMA_VERSION = "FINSIGHT-LATEST-500-WORK-REGISTER-1"
EXPECTED_COUNT = 500
TARGET_REVIEW_TICKERS = frozenset({"BIIB", "HON", "INTC", "JBL", "MCK", "LHX", "GILD", "INCY"})


def _read(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_range(value: Any) -> bool:
    return isinstance(value, Mapping) and all(
        isinstance(value.get(key), (int, float))
        and not isinstance(value.get(key), bool)
        and math.isfinite(float(value[key]))
        for key in ("low", "base", "high")
    )


def _index_rows(value: Any, *, path: Path, key: str = "ticker") -> dict[str, dict[str, Any]]:
    if isinstance(value, Mapping):
        rows = next(
            (value[name] for name in ("rows", "companies", "entries") if isinstance(value.get(name), list)),
            value,
        )
    else:
        rows = value
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise ValueError(f"{path}: expected a row list")
    result: dict[str, dict[str, Any]] = {}
    for raw in rows:
        ticker = str(raw.get(key) or "").strip()
        if not ticker or ticker in result:
            raise ValueError(f"{path}: duplicate or missing ticker")
        result[ticker] = dict(raw)
    return result


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _capture_rows(capture_report: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = capture_report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("capture report rows are missing")
    result: dict[str, dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, Mapping) or not raw.get("ticker"):
            raise ValueError("capture report contains an invalid row")
        ticker = str(raw["ticker"])
        if ticker in result:
            raise ValueError("capture report contains duplicate tickers")
        result[ticker] = dict(raw)
    return result


def _source_reports(runtime_root: Path) -> list[tuple[Path, Mapping[str, Any]]]:
    result: list[tuple[Path, Mapping[str, Any]]] = []
    for path in sorted((runtime_root / "source-validation").glob("*/report.json")):
        report = _read(path)
        if isinstance(report, Mapping):
            result.append((path, report))
    return result


def _source_diagnostics(
    ticker: str,
    *,
    reports: list[tuple[Path, Mapping[str, Any]]],
    capture_receipt_sha: str | None,
    policy_sha: str | None,
    implementation_sha: str,
) -> dict[str, Any]:
    candidates: list[tuple[bool, str, Path, dict[str, Any]]] = []
    for path, report in reports:
        report_impl = report.get("implementation_sha256")
        report_policy = report.get("policy_sha256")
        rows = report.get("rows")
        if not isinstance(rows, list):
            continue
        for raw in rows:
            if not isinstance(raw, Mapping) or str(raw.get("ticker")) != ticker:
                continue
            row = dict(raw)
            source_capture = row.get("source_capture")
            wrapper = source_capture.get("wrapper_sha256") if isinstance(source_capture, Mapping) else None
            fingerprint_match = (
                report_impl == implementation_sha
                and report_policy == policy_sha
                and bool(capture_receipt_sha)
                and wrapper == capture_receipt_sha
            )
            candidates.append((fingerprint_match, str(path), path, row))
    if not candidates:
        return {"status": "unavailable", "current": False, "reason": "no source-validation diagnostic"}
    candidates.sort(key=lambda item: (item[0], item[1]))
    current, _, path, row = candidates[-1]
    if not current:
        return {
            "status": "stale_or_earlier_snapshot",
            "current": False,
            "report_path": str(path),
            "reason": "implementation, policy, or capture receipt fingerprint does not match the latest snapshot",
            "historical_status": row.get("status"),
        }
    return {
        "status": "current",
        "current": True,
        "report_path": str(path),
        "row_status": row.get("status"),
        "reason": row.get("reason"),
        "current_range": row.get("current_range"),
        "reliability": row.get("reliability"),
        "source_cutoff": row.get("source_cutoff"),
        "controlling_accession": row.get("controlling_accession"),
    }


def _next_action(
    *,
    acquisition: str,
    prior_unavailable: bool,
    changed_regular: bool,
    migration_ready: bool,
    policy_ready: bool,
    target_review: bool,
    event_flag: bool,
    source_validation: Mapping[str, Any],
) -> str:
    if acquisition == "failed":
        return "Resolve the captured-source failure, then rerun bounded acquisition."
    if acquisition == "pending":
        return "Acquire the selected latest source packet before any refresh decision."
    if prior_unavailable:
        return "Use the separately authorized recovery path; do not infer a numeric value."
    if not migration_ready:
        return "Restore or validate the numeric baseline recipe before refresh work."
    if changed_regular and not policy_ready:
        return "Implement or repair the applicable refresh mapping before binding the changed filing."
    if target_review:
        return "Complete the named targeted review and record its source-bound result."
    if source_validation.get("status") == "current" and source_validation.get("row_status") not in {"cached_source_bound", "source_bound"}:
        return "Resolve the current source/economic review before considering any update."
    if event_flag:
        return "Review the post-baseline event filings under the approved event policy."
    if changed_regular:
        return "Bind and verify the changed regular filing; the approved baseline remains unchanged until then."
    return "Retain the approved baseline pending a material source or policy change."


def build_register(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    runtime = root / "runtime"
    discovery_root = root / "final-discovery"
    registry = _read(runtime / "registry.json")
    registry_rows = _index_rows(registry.get("entries"), path=runtime / "registry.json")
    if len(registry_rows) != EXPECTED_COUNT:
        raise ValueError(f"runtime registry must contain exactly {EXPECTED_COUNT} companies")
    if len({str(row.get('cik','')).zfill(10) for row in registry_rows.values()})!=EXPECTED_COUNT:
        raise ValueError('runtime registry contains duplicate company identities')
    discovery = _read(discovery_root / "discovery-report.json")
    discovery_rows = _index_rows(discovery, path=discovery_root / "discovery-report.json")
    if len(discovery_rows) != EXPECTED_COUNT or set(discovery_rows) != set(registry_rows):
        raise ValueError("discovery must contain the exact original 500 tickers")
    for ticker, row in discovery_rows.items():
        if str(row.get("cik", "")).zfill(10) != str(registry_rows[ticker].get("cik", "")).zfill(10):
            raise ValueError(f"discovery CIK mismatch for {ticker}")
    capture_report_path = discovery_root / "capture-report.json"
    capture_report = _read(capture_report_path)
    capture_rows = _capture_rows(capture_report)
    capture_by_ticker = {ticker: capture_rows.get(ticker) for ticker in registry_rows}
    policy_report_path = runtime / "policy-compilation-report.json"
    policy_report = _read(policy_report_path)
    policy_rows = _index_rows(policy_report, path=policy_report_path)
    migration_rows = _index_rows(_read(runtime / "migration-company-report.json"), path=runtime / "migration-company-report.json", key="ticker")
    policies = _read(runtime / "refresh-policies.json")
    recipes_root = runtime / "recipes"
    extra_review_path=runtime/'targeted-reviews.json'
    extra_reviews=_read(extra_review_path).get('companies',{}) if extra_review_path.is_file() else {}
    if not isinstance(extra_reviews,dict) or set(extra_reviews)-set(registry_rows):raise ValueError('invalid additional targeted-review registry')
    reports = _source_reports(runtime)
    policy_sha = policy_report.get("policy_sha256")
    if policy_sha!=_sha(runtime/'refresh-policies.json'):
        raise ValueError('policy compilation fingerprint mismatch')
    implementation_sha = implementation_fingerprint()
    companies: list[dict[str, Any]] = []
    for ticker in sorted(registry_rows):
        reg = registry_rows[ticker]
        discovery_row = discovery_rows[ticker]
        migration = migration_rows.get(ticker, {})
        policy_row = policy_rows.get(ticker, {})
        recipe_path = recipes_root / f"{ticker}.json"
        recipe = _read(recipe_path) if recipe_path.is_file() else None
        migration_ready = bool(recipe and _finite_range(recipe.get("replay")))
        policy_ready = policy_row.get("status") == "contract_compiled"
        prior_unavailable = (
            reg.get("availability_type") == "not_available"
            or migration.get("migration_status") == "prior_unavailable"
            or policy_row.get("status") == "prior_unavailable"
        )
        capture = capture_by_ticker[ticker]
        acquisition = "pending" if capture is None else "captured" if capture.get("status") == "captured" else "failed"
        capture_receipt_sha = capture.get("receipt_sha256") if capture else None
        source_validation = _source_diagnostics(
            ticker,
            reports=reports,
            capture_receipt_sha=capture_receipt_sha,
            policy_sha=policy_sha,
            implementation_sha=implementation_sha,
        )
        event_filings = discovery_row.get("event_filings")
        event_flag = bool(event_filings)
        changed_regular = bool(discovery_row.get("changed_regular"))
        target_review = ticker in TARGET_REVIEW_TICKERS or ticker in extra_reviews
        baseline_range = migration.get("baseline_range")
        reliability = migration.get("reliability") or migration.get("confidence")
        filing = migration.get("filing") if isinstance(migration.get("filing"), Mapping) else {}
        companies.append({
            "ticker": ticker,
            "cik": str(reg.get("cik", "")).zfill(10),
            "baseline": {
                "exact_range": baseline_range,
                "reliability": reliability,
                "filed_date": filing.get("filed_date"),
                "accession": filing.get("accession"),
            },
            "discovery": {
                "changed_regular": changed_regular,
                "event_flag": event_flag,
                "event_count": len(event_filings) if isinstance(event_filings, list) else 0,
                "latest_regular": discovery_row.get("latest_regular"),
                "latest_annual": discovery_row.get("latest_annual"),
            },
            "acquisition": {
                "status": acquisition,
                "receipt_sha256": capture_receipt_sha,
                "error": capture.get("error") if capture else None,
            },
            "migration_ready": migration_ready,
            "prior_unavailable": prior_unavailable,
            "policy_ready": policy_ready,
            "target_review": {"flag": target_review, "reason": extra_reviews.get(ticker,{}).get('reason') or ("named target review" if target_review else None),
                "detail":extra_reviews.get(ticker)},
            "source_validation": source_validation,
            "next_action": _next_action(
                acquisition=acquisition,
                prior_unavailable=prior_unavailable,
                changed_regular=changed_regular,
                migration_ready=migration_ready,
                policy_ready=policy_ready,
                target_review=target_review,
                event_flag=event_flag,
                source_validation=source_validation,
            ),
        })
    counts = {
        "evidence_acquired": sum(row["acquisition"]["status"] == "captured" for row in companies),
        "current_source_bound_diagnostics": sum(
            row["source_validation"].get("status") == "current"
            and row["source_validation"].get("row_status") in {"cached_source_bound", "source_bound"}
            for row in companies
        ),
        "pending_acquisition": sum(row["acquisition"]["status"] == "pending" for row in companies),
        "failed_capture": sum(row["acquisition"]["status"] == "failed" for row in companies),
        "remaining_mapping_changed_regular": sum(
            row["discovery"]["changed_regular"] and not row["policy_ready"] and not row['prior_unavailable'] for row in companies
        ),
        "changed_regular_recovery_reviews":sum(row['discovery']['changed_regular'] and row['prior_unavailable'] for row in companies),
        "prior_unavailable": sum(
            not row["migration_ready"] and registry_rows[row["ticker"]].get("availability_type") == "not_available"
            for row in companies
        ),
        "changed_regular": sum(row["discovery"]["changed_regular"] for row in companies),
        "event_flagged": sum(row["discovery"]["event_flag"] for row in companies),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "expected_count": EXPECTED_COUNT,
            "registry_count": len(registry_rows),
            "discovery_count": len(discovery_rows),
            "exact_original_universe": True,
            "discovery_cutoff": discovery.get("cutoff"),
        },
        "fingerprints": {
            "discovery_sha256": _sha(discovery_root / "discovery-report.json"),
            "capture_report_sha256": _sha(capture_report_path),
            "policy_sha256": policy_sha,
            "implementation_sha256": implementation_sha,
        },
        "counts": counts,
        "companies": companies,
        "reporting_limits": [
            "Baseline ranges and reliability are retained metadata; no current source diagnostic updates an approved value.",
            "Only diagnostics matching implementation, policy, and capture receipt fingerprints count as current.",
            "Stale or earlier source-validation receipts remain visible but do not count as current evidence.",
        ],
    }


def render_markdown(register: Mapping[str, Any]) -> str:
    counts = register["counts"]
    lines = [
        "# Latest 500-company refresh work register",
        "",
        "Reporting-only snapshot. Approved baseline values are not updated by this register.",
        "",
        f"- Universe: {register['scope']['registry_count']} exact original companies",
        f"- Evidence acquired: {counts['evidence_acquired']}",
        f"- Current source-bound diagnostics: {counts['current_source_bound_diagnostics']}",
        f"- Pending acquisition: {counts['pending_acquisition']}",
        f"- Failed capture: {counts['failed_capture']}",
        f"- Remaining mapping for changed regular filings: {counts['remaining_mapping_changed_regular']}",
        "",
        "| Ticker | Changed regular | Events | Acquisition | Migration | Policy | Source diagnostic | Next action |",
        "|---|---:|---:|---|---:|---:|---|---|",
    ]
    for row in register["companies"]:
        lines.append(
            f"| {row['ticker']} | {str(row['discovery']['changed_regular']).lower()} | "
            f"{row['discovery']['event_count']} | {row['acquisition']['status']} | "
            f"{str(row['migration_ready']).lower()} | {str(row['policy_ready']).lower()} | "
            f"{row['source_validation']['status']} | {row['next_action']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "output" / "latest-universe-20260919")
    args = parser.parse_args()
    register = build_register(args.root)
    _atomic_write(args.root / "work-register.json", canonical_json_bytes(register))
    _atomic_write(args.root / "work-register.md", render_markdown(register).encode("utf-8"))
    print(json.dumps({"json": str(args.root / "work-register.json"), "markdown": str(args.root / "work-register.md"), "counts": register["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
