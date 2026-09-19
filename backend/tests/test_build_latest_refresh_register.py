from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.build_latest_refresh_register import build_register
from app.us_valuation.refresh_work_register import canonical_json_bytes, implementation_fingerprint


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "latest"
    runtime = root / "runtime"
    discovery_root = root / "final-discovery"
    rows = []
    registry_entries = []
    migration_rows = []
    policy_rows = []
    for index in range(500):
        ticker = "A" if index == 0 else "B" if index == 1 else "C" if index == 2 else f"T{index:03d}"
        cik = str(index + 1).zfill(10)
        changed = ticker in {"A", "B"}
        registry_entries.append({"ticker": ticker, "cik": cik, "availability_type": "not_available" if ticker == "C" else "available"})
        rows.append({
            "ticker": ticker,
            "cik": cik,
            "changed_regular": changed,
            "event_filings": [{"form": "8-K"}] if ticker == "A" else [],
            "latest_regular": {"accessionNumber": f"{cik}-26-000001"},
            "latest_annual": {"accessionNumber": f"{cik}-25-000001"},
        })
        migration_rows.append({
            "ticker": ticker,
            "migration_status": "prior_unavailable" if ticker == "C" else "exact_replay",
            "baseline_range": {"low": 1.0, "base": 2.0, "high": 3.0},
            "confidence": {"label": "Low"},
            "filing": {"filed_date": "2026-08-14", "accession": "old"},
        })
        policy_rows.append({"ticker": ticker, "status": "implementation_required" if ticker == "B" else "prior_unavailable" if ticker == "C" else "contract_compiled"})
    _write(runtime / "registry.json", {"entries": registry_entries})
    _write(runtime / "migration-company-report.json", {"companies": migration_rows})
    policy_sha=hashlib.sha256(canonical_json_bytes({})).hexdigest()
    _write(runtime / "policy-compilation-report.json", {"policy_sha256": policy_sha, "rows": policy_rows})
    _write(runtime / "refresh-policies.json", {})
    _write(discovery_root / "discovery-report.json", {"cutoff": "2026-09-19", "rows": rows})
    _write(discovery_root / "capture-report.json", {
        "rows": [
            {"ticker": "A", "status": "captured", "receipt_sha256": "receipt-a"},
            {"ticker": "C", "status": "capture_failed", "error": "bad source"},
        ]
    })
    _write(runtime / "recipes" / "A.json", {"replay": {"low": 1.0, "base": 2.0, "high": 3.0}})
    _write(runtime / "recipes" / "B.json", {"replay": {"low": 1.0, "base": 2.0, "high": 3.0}})
    _write(runtime / "source-validation" / "current" / "report.json", {
        "implementation_sha256": implementation_fingerprint(),
        "policy_sha256": policy_sha,
        "rows": [{"ticker": "A", "status": "cached_source_bound", "source_capture": {"wrapper_sha256": "receipt-a"}}],
    })
    _write(runtime / "source-validation" / "stale" / "report.json", {
        "implementation_sha256": "old-implementation",
        "policy_sha256": "old-policy",
        "rows": [{"ticker": "B", "status": "cached_source_bound", "source_capture": {"wrapper_sha256": "old-receipt"}}],
    })
    return root


def test_register_requires_exact_universe_and_separates_current_diagnostics(tmp_path: Path) -> None:
    register = build_register(_fixture(tmp_path))

    assert register["scope"]["exact_original_universe"] is True
    assert register["scope"]["registry_count"] == 500
    assert register["counts"]["evidence_acquired"] == 1
    assert register["counts"]["current_source_bound_diagnostics"] == 1
    assert register["counts"]["pending_acquisition"] == 498
    assert register["counts"]["failed_capture"] == 1
    assert register["counts"]["remaining_mapping_changed_regular"] == 1
    by_ticker = {row["ticker"]: row for row in register["companies"]}
    assert by_ticker["A"]["source_validation"]["status"] == "current"
    assert by_ticker["B"]["source_validation"]["status"] == "stale_or_earlier_snapshot"
    assert by_ticker["B"]["policy_ready"] is False
    assert by_ticker["C"]["acquisition"]["status"] == "failed"
    assert by_ticker["C"]["next_action"].startswith("Resolve the captured-source failure")


def test_register_does_not_count_stale_source_diagnostics_as_current(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    report = json.loads((root / "runtime/source-validation/current/report.json").read_text())
    report["policy_sha256"] = "stale-policy"
    _write(root / "runtime/source-validation/current/report.json", report)

    register = build_register(root)

    assert register["counts"]["current_source_bound_diagnostics"] == 0
    row = next(item for item in register["companies"] if item["ticker"] == "A")
    assert row["source_validation"]["status"] == "stale_or_earlier_snapshot"
