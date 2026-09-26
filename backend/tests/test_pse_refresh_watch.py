"""Internal filing-watch scheduler tests; no external source request is made."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.refresh_watch import WATCH_SCHEMA, parse_index_links, run_once


ROOT = Path(__file__).resolve().parents[2]
CATALOGS = ROOT / "backend/app/data/pse_valuation_catalogs"
CONFIG = ROOT / "backend/app/pse_valuation/config/internal_filing_watch.json"
RCR_INPUT = ROOT / "docs/audit/evidence/pse-rcr-internal-source-refresh-2026-09-26"


def _paths(tmp_path: Path) -> dict:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    return {
        "config_path": CONFIG,
        "bundle_inbox": inbox,
        "stage_root": tmp_path / "staged",
        "state_dir": tmp_path / "state",
        "catalogs_root": CATALOGS,
    }


def _copy_rcr_bundle(inbox: Path) -> Path:
    target = inbox / "rcr-reviewed"
    target.mkdir()
    for name in ("bundle.json", "receipt.json"):
        shutil.copy2(RCR_INPUT / name, target / name)
    return target


def test_no_cleared_rights_means_no_external_poll(tmp_path: Path) -> None:
    args = _paths(tmp_path)
    active_before = (CATALOGS / "active.json").read_bytes()

    def forbidden_fetch(_url: str) -> bytes:
        raise AssertionError("external source must not be fetched")

    report = run_once(**args, fetch_index=forbidden_fetch)
    assert report["new_filing_links"] == []
    assert report["staged"] == []
    assert set(report["source_checks"].values()) == {"disabled_pending_source_rights"}
    assert (CATALOGS / "active.json").read_bytes() == active_before
    assert (args["state_dir"] / "state.json").exists()


def test_cleared_index_records_baseline_then_new_pdf_link(tmp_path: Path) -> None:
    args = _paths(tmp_path)
    config = {
        "schema_version": WATCH_SCHEMA,
        "sources": [{
            "id": "RCR-test-index", "ticker": "RCR",
            "index_url": "https://issuer.example.com/disclosures",
            "pdf_path_pattern": r"\.pdf$",
            "automated_metadata_access_allowed": True,
            "rights_record": "TEST-ONLY-METADATA-ACCESS",
        }],
    }
    config_path = tmp_path / "sources.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    args["config_path"] = config_path
    responses = iter([
        b'<a href="/files/2025-17a.pdf">old</a>',
        b'<a href="/files/2025-17a.pdf">old</a><a href="/files/2026-17q.pdf">new</a><a href="https://other.example.com/foreign.pdf">ignore</a>',
    ])

    def fake_index(url: str) -> bytes:
        assert url == "https://issuer.example.com/disclosures"
        return next(responses)

    first = run_once(**args, fetch_index=fake_index)
    second = run_once(**args, fetch_index=fake_index)
    assert first["source_checks"]["RCR-test-index"] == "baseline_recorded"
    assert first["new_filing_links"] == []
    assert second["new_filing_links"] == [{
        "ticker": "RCR", "source_id": "RCR-test-index",
        "url": "https://issuer.example.com/files/2026-17q.pdf",
        "status": "needs_fact_and_rights_review",
    }]
    assert not args["stage_root"].exists()


def test_real_rcr_reviewed_bundle_stages_once_and_keeps_rlc_hold(tmp_path: Path) -> None:
    args = _paths(tmp_path)
    _copy_rcr_bundle(args["bundle_inbox"])
    active_before = (CATALOGS / "active.json").read_bytes()
    first = run_once(**args, fetch_index=lambda _url: (_ for _ in ()).throw(AssertionError("unexpected fetch")))
    assert len(first["staged"]) == 1 and first["holds"] == []
    output_root = args["stage_root"] / "PSE-V2-REFRESH-RCR-2026-09-26-1.0"
    catalog = load_pointer(output_root)
    assert catalog.status == "staged" and len(catalog.entries) == 282
    candidate = json.loads(catalog.verify_artifact("RCR").read_bytes())
    assert candidate["scenarios"]["base"]["value_per_share"] == pytest.approx(5.310705882352938)
    assert candidate["publication_state"] == "provisional"
    active = load_pointer(CATALOGS, "active.json")
    assert catalog.verify_artifact("RLC").read_bytes() == active.verify_artifact("RLC").read_bytes()
    refresh_report = json.loads((output_root / "refresh_report.json").read_text())
    assert refresh_report["dependency_holds"] == ["RLC"]
    assert refresh_report["activation_ready"] is False
    second = run_once(**args, fetch_index=lambda _url: (_ for _ in ()).throw(AssertionError("unexpected fetch")))
    assert second["staged"] == []
    assert second["skipped"][0]["reason"] == "already_staged"
    assert (CATALOGS / "active.json").read_bytes() == active_before


def test_rlc_ready_bundle_is_held_without_staging(tmp_path: Path) -> None:
    args = _paths(tmp_path)
    target = _copy_rcr_bundle(args["bundle_inbox"])
    bundle = json.loads((target / "bundle.json").read_text())
    bundle["cases"]["RLC"] = {"status": "ready", "receipt_path": "missing.json", "receipt_sha256": "0" * 64}
    (target / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    report = run_once(**args)
    assert report["staged"] == []
    assert "RLC stays on hold" in report["holds"][0]["reason"]
    assert not args["stage_root"].exists()


def test_rights_record_is_required_before_metadata_access(tmp_path: Path) -> None:
    args = _paths(tmp_path)
    config = {
        "schema_version": WATCH_SCHEMA,
        "sources": [{"id": "unsafe", "ticker": "RCR", "index_url": "https://issuer.example.com/", "pdf_path_pattern": r"\.pdf$", "automated_metadata_access_allowed": True, "rights_record": None}],
    }
    path = tmp_path / "bad-sources.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    args["config_path"] = path
    with pytest.raises(ValueError, match="rights record"):
        run_once(**args)


def test_private_index_address_is_rejected_before_fetch(tmp_path: Path) -> None:
    args = _paths(tmp_path)
    config = {
        "schema_version": WATCH_SCHEMA,
        "sources": [{"id": "unsafe", "ticker": "RCR", "index_url": "https://127.0.0.1/", "pdf_path_pattern": r"\.pdf$", "automated_metadata_access_allowed": True, "rights_record": "TEST-ONLY"}],
    }
    path = tmp_path / "bad-host.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    args["config_path"] = path
    with pytest.raises(ValueError, match="local addresses"):
        run_once(**args, fetch_index=lambda _url: (_ for _ in ()).throw(AssertionError("unexpected fetch")))


def test_index_change_without_new_pdf_link_needs_review(tmp_path: Path) -> None:
    args = _paths(tmp_path)
    config = {
        "schema_version": WATCH_SCHEMA,
        "sources": [{"id": "RCR-test-index", "ticker": "RCR", "index_url": "https://issuer.example.com/disclosures", "pdf_path_pattern": r"\.pdf$", "automated_metadata_access_allowed": True, "rights_record": "TEST-ONLY"}],
    }
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    args["config_path"] = path
    responses = iter([b'<a href="/files/old.pdf">old</a>', b'<a href="/files/old.pdf">amended label</a>'])
    run_once(**args, fetch_index=lambda _url: next(responses))
    second = run_once(**args, fetch_index=lambda _url: next(responses))
    assert second["source_checks"]["RCR-test-index"] == "index_changed_review_needed"
    assert second["new_filing_links"] == []


def test_parser_rejects_cross_host_and_query_links() -> None:
    html = b'<a href="/files/ok.pdf">ok</a><a href="https://elsewhere.example.org/bad.pdf">bad</a><a href="/files/token.pdf?key=secret">token</a>'
    assert parse_index_links(html, "https://issuer.example.com/disclosures", r"\.pdf$") == ["https://issuer.example.com/files/ok.pdf"]
