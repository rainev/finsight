"""Offline PSE summary signals never replace reviewed valuation facts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.refresh_watch import run_once
from app.pse_valuation.summary_snapshots import PSE_SUMMARY_URLS, SUMMARY_SCHEMA, read_snapshot
from app.main import app
from app.routers import pse_valuations
from app.security.jwt import sign_access_token


ROOT = Path(__file__).resolve().parents[2]
CATALOGS = ROOT / "backend/app/data/pse_valuation_catalogs"
CONFIG = ROOT / "backend/app/pse_valuation/config/internal_filing_watch.json"
RCR_INPUT = ROOT / "docs/audit/evidence/pse-rcr-internal-source-refresh-2026-09-26"


def _args(tmp_path: Path) -> dict:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    summary = tmp_path / "summaries"
    summary.mkdir()
    return {
        "config_path": CONFIG, "bundle_inbox": inbox, "stage_root": tmp_path / "candidates",
        "state_dir": tmp_path / "state", "catalogs_root": CATALOGS, "summary_dir": summary,
        "fetch_index": lambda _url: (_ for _ in ()).throw(AssertionError("offline mode fetched the internet")),
    }


def _snapshot(summary: Path, ticker: str, period: str = "2026-06-30", *, revenue: float | None = 100.0, observed: str = "2026-09-26") -> Path:
    path = summary / f"{ticker}.json"
    path.write_text(json.dumps({
        "schema_version": SUMMARY_SCHEMA, "ticker": ticker, "source_url": PSE_SUMMARY_URLS[ticker],
        "observed_at": observed, "period_end": period, "period_type": "quarterly",
        "currency": "PHP", "unit": "PHP_millions", "scope": "consolidated",
        "facts": {"revenue": revenue, "net_income": 25.0},
    }), encoding="utf-8")
    return path


def _bundle(inbox: Path) -> None:
    folder = inbox / "rcr-reviewed"
    folder.mkdir()
    for name in ("bundle.json", "receipt.json"):
        shutil.copy2(RCR_INPUT / name, folder / name)


def test_snapshot_digest_ignores_observation_time_but_detects_fact_change(tmp_path: Path) -> None:
    path = _snapshot(tmp_path, "RCR", observed="2026-09-25")
    first = read_snapshot(path, "RCR")
    _snapshot(tmp_path, "RCR", observed="2026-09-26")
    assert read_snapshot(path, "RCR").digest == first.digest
    _snapshot(tmp_path, "RCR", revenue=100, observed="2026-09-26")
    assert read_snapshot(path, "RCR").digest == first.digest
    _snapshot(tmp_path, "RCR", revenue=101.0)
    assert read_snapshot(path, "RCR").digest != first.digest


def test_new_summary_without_reviewed_facts_is_pending_not_recalculated(tmp_path: Path) -> None:
    args = _args(tmp_path)
    _snapshot(args["summary_dir"], "AP")
    before = (CATALOGS / "active.json").read_bytes()
    report = run_once(**args)
    assert report["summary_checks"]["AP"] == "new_period"
    assert report["summary_checks"]["BPI"] == "not_supplied"
    assert set(report["source_checks"].values()) == {"disabled_offline_snapshot_mode"}
    assert report["pending_summary_changes"]["AP"]["period_end"] == "2026-06-30"
    assert report["staged"] == []
    assert run_once(**args)["summary_checks"]["AP"] == "unchanged"
    assert (CATALOGS / "active.json").read_bytes() == before


def test_real_reviewed_rcr_receipt_stages_only_with_matching_summary_signal(tmp_path: Path, monkeypatch) -> None:
    args = _args(tmp_path)
    _bundle(args["bundle_inbox"])
    before = (CATALOGS / "active.json").read_bytes()
    no_signal = run_once(**args)
    assert no_signal["staged"] == []
    assert "no changed financial-summary" in no_signal["holds"][0]["reason"]
    for ticker in PSE_SUMMARY_URLS:
        _snapshot(args["summary_dir"], ticker)
    report = run_once(**args)
    assert report["summary_checks"]["RCR"] == "new_period"
    assert len(report["staged"]) == 1
    assert set(report["pending_summary_changes"]) == {"AP", "BPI", "RLC"}
    candidate_root = args["stage_root"] / "PSE-V2-REFRESH-RCR-2026-09-26-1.0"
    candidate = load_pointer(candidate_root)
    active = load_pointer(CATALOGS, "active.json")
    assert candidate.status == "staged" and len(candidate.entries) == 282
    result = json.loads(candidate.verify_artifact("RCR").read_bytes())
    assert result["scenarios"]["base"]["value_per_share"] == pytest.approx(5.310705882352938)
    assert result["publication_state"] == "provisional"
    assert candidate.verify_artifact("RLC").read_bytes() == active.verify_artifact("RLC").read_bytes()
    assert (CATALOGS / "active.json").read_bytes() == before
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", candidate_root)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    monkeypatch.setattr(app, "dependency_overrides", {})
    token = sign_access_token(1, "summary-pilot@example.invalid", "user")
    client = TestClient(app)
    assert client.get("/api/pse-valuations").status_code == 401
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.get("/api/pse-valuations", headers=headers)
    assert listing.status_code == 200 and listing.json()["count"] == 282
    for ticker in ("AP", "BPI", "RCR", "RLC"):
        response = client.get(f"/api/pse-valuations/{ticker}", headers=headers)
        assert response.status_code == 200
        assert response.json()["catalog"]["catalog_status"] == "staged"
    assert client.get("/api/pse-valuations/RCR", headers=headers).json()["scenarios"]["base"]["value_per_share"] == pytest.approx(5.310705882352938)
    again = run_once(**args)
    assert again["staged"] == [] and again["skipped"][0]["reason"] == "already_staged"


def test_unmatched_period_does_not_stage_existing_receipt(tmp_path: Path) -> None:
    args = _args(tmp_path)
    _bundle(args["bundle_inbox"])
    _snapshot(args["summary_dir"], "RCR", period="2026-08-31")
    report = run_once(**args)
    assert report["staged"] == []
    assert "predates the changed summary period" in report["holds"][0]["reason"]
    assert "RCR" in report["pending_summary_changes"]


def test_same_period_first_run_is_baseline_then_restatement_requires_review(tmp_path: Path) -> None:
    args = _args(tmp_path)
    _snapshot(args["summary_dir"], "BPI", period="2025-12-31")
    first = run_once(**args)
    assert first["summary_checks"]["BPI"] == "baseline_recorded"
    assert first["pending_summary_changes"] == {}
    _snapshot(args["summary_dir"], "BPI", period="2025-12-31", revenue=101.0)
    second = run_once(**args)
    assert second["summary_checks"]["BPI"] == "restated_summary"
    assert second["staged"] == [] and "BPI" in second["pending_summary_changes"]


def test_invalid_or_stale_snapshot_fails_closed(tmp_path: Path) -> None:
    args = _args(tmp_path)
    path = _snapshot(args["summary_dir"], "RCR", period="2025-09-30")
    assert run_once(**args)["summary_checks"]["RCR"] == "stale_period_held"
    payload = json.loads(path.read_text())
    payload["source_url"] = "https://other.example.com"
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = run_once(**args)
    assert report["summary_checks"]["RCR"].startswith("held:")
    assert report["pending_summary_changes"] == {}


def test_summary_directory_must_be_isolated(tmp_path: Path) -> None:
    args = _args(tmp_path)
    args["summary_dir"] = args["bundle_inbox"]
    with pytest.raises(ValueError, match="separate"):
        run_once(**args)


def test_offline_cli_one_tick_stages_real_reviewed_rcr_bundle(tmp_path: Path) -> None:
    args = _args(tmp_path)
    _bundle(args["bundle_inbox"])
    _snapshot(args["summary_dir"], "RCR")
    command = [
        sys.executable, str(ROOT / "scripts/run_pse_intrinsic_refresh_watch.py"),
        "--bundle-inbox", str(args["bundle_inbox"]), "--stage-root", str(args["stage_root"]),
        "--state-dir", str(args["state_dir"]), "--summary-dir", str(args["summary_dir"]),
    ]
    result = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "backend")}, capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert len(report["staged"]) == 1 and report["summary_checks"]["RCR"] == "new_period"
    assert set(report["source_checks"].values()) == {"disabled_offline_snapshot_mode"}
    assert report["active_changed"] is False
