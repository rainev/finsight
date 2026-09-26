"""Batch 27 null-only source claims and deterministic staged catalog."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_27 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts import build_pse_v2_phase_b_batch_27 as builder
from scripts.activate_pse_v2_phase_b_batch_27 import (
    CONFIRMED_ACTIVE_POINTER_SHA256, CONFIRMED_MANIFEST_SHA256,
    activate, preflight, write_pointer,
)


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"
REVIEWED = {
    "AR": (1715850145.74, 199294584200, "2020-09-30"),
    "BMM": (177753, 6000000, "2022-06-30"),
    "CYBR": (-1520397, 6806878853, "2026-06-30"),
    "MGH": (3518441949, 2750000000, "2025-09-30"),
    "MJIC": (-1530001417, 3174405821, "2022-09-30"),
    "PNC": (None, 174444759, None),
    "PORT": (150092077, 2335134100, "2020-06-30"),
    "SOC": (1882304137, 901920568, "2026-06-30"),
    "T": (857375017, 1690000000, "2025-09-30"),
    "TUBIG": (3358533, 40000000040, "2026-03-31"),
}


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_all_ten_source_bounded_null_and_missing_facts_not_zero():
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS == tuple(REVIEWED)
    for ticker, (equity, shares, period) in REVIEWED.items():
        issuer = config["issuers"][ticker]
        artifact = artifacts[ticker]
        assert (issuer["equity_value"], issuer["shares_outstanding"], issuer["period_end"]) == (equity, shares, period)
        assert issuer["trading_status"] == "suspended" and artifact.price is None and artifact.verify_artifact_hash()
        assert artifact.availability_type == "not_available" and artifact.publication_state == "blocked"
        assert all(value is None for value in artifact.scenarios.values()) and artifact.numerical_range == {"low": None, "high": None}
        assert artifact.market_relative is None and artifact.blocking_reasons
        assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is False
        references, receipt_raw = source_receipt(ticker, config)
        receipt = json.loads(receipt_raw)
        assert len(references) >= 2 and hashlib.sha256(receipt_raw).hexdigest() == references[0]["sha256"]
        assert receipt["facts"]["reported_share_classes"][0]["shares"] == shares
        if issuer["share_bridge_type"] == "unresolved_claims":
            assert receipt["facts"]["reviewed_common_denominator"] is None
    assert json.loads(source_receipt("PNC", config)[1])["facts"]["reported_equity"] is None
    assert json.loads(source_receipt("PNC", config)[1])["facts"]["reported_bvps"] is None
    assert json.loads(source_receipt("AR", config)[1])["facts"]["reported_equity"]["source_currency_label"] == "PES0"
    assert config["issuers"]["BMM"]["equity_unit_scale"] == "thousands"
    assert config["issuers"]["CYBR"]["equity_value"] < 0


def test_bad_missing_facts_claims_and_dates_fail(tmp_path):
    config = load_batch_config()
    path = tmp_path / "bad.json"
    for ticker, field, value, message in (
        ("PNC", "equity_value", 0, "missing financial facts must remain null"),
        ("AR", "source_currency_label", None, "dated reported equity"),
        ("BMM", "shares_outstanding", 0, "positive sourced common-share line"),
        ("T", "trading_status", "open", "currency or suspended status"),
        ("SOC", "availability", "market_relative_only", "null-only publication boundary"),
        ("TUBIG", "share_as_of", "2026-09-26", "stock status or share date exceeds"),
    ):
        bad = json.loads(json.dumps(config))
        bad["issuers"][ticker][field] = value
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match=message):
            load_batch_config(path)


def test_278_deterministic_twins_exact_parent_and_staged_router(tmp_path, monkeypatch):
    active_before = (ACTIVE / "active.json").read_bytes()
    parent_before = (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    catalog_root = builder.build(first)
    builder.build(second)
    assert tree(first) == tree(second)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
    catalog = load_pointer(first)
    assert catalog.version == builder.CATALOG_VERSION and catalog.status == "staged" and len(catalog.entries) == 278
    assert sum(e.availability_type == "intrinsic_valuation" for e in catalog.entries) == 34
    assert sum(e.availability_type == "market_relative_only" for e in catalog.entries) == 204
    assert sum(e.availability_type == "not_available" for e in catalog.entries) == 40
    parent = json.loads(parent_before)
    for entry in parent["entries"]:
        ticker = entry["ticker"]
        assert (catalog_root / "artifacts" / f"{ticker}.json").read_bytes() == (ACTIVE / builder.PARENT_CATALOG_VERSION / "artifacts" / f"{ticker}.json").read_bytes()
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", first)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    listing = pse_valuations.list_pse_valuations({"sub": 1, "role": "user"})
    assert listing["count"] == 278 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, {"sub": 1, "role": "user"})
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, {"sub": 1, "role": "user"})["can_calculate"] is False


def test_parent_pointer_guard_rejects_drift(tmp_path, monkeypatch):
    pointer = json.loads((ACTIVE / "active.json").read_text())
    pointer["manifest_sha256"] = "0" * 64
    changed = tmp_path / "active.json"
    changed.write_text(json.dumps(pointer))
    monkeypatch.setattr(builder, "ACTIVE_POINTER", changed)
    with pytest.raises(RuntimeError, match="pointer differs"):
        builder.snapshot_parent()


def test_confirmed_preflight_and_isolated_activation_only(tmp_path):
    active_before = (ACTIVE / "active.json").read_bytes()
    parent_before = (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    candidate_root = tmp_path / "candidate"
    candidate_catalog = builder.build(candidate_root)
    assert hashlib.sha256((candidate_catalog / "manifest.json").read_bytes()).hexdigest() == CONFIRMED_MANIFEST_SHA256
    checks = preflight(candidate_root)
    assert checks["active_before"] == "PSE-V2-PHASE-B-B28-2026-09-26-1.0"
    assert checks["ready_for_separate_activation"] is False
    with pytest.raises(RuntimeError, match="cannot roll back"):
        activate(candidate_root)
    isolated = tmp_path / "isolated-serving"
    isolated.mkdir()
    shutil.copytree(ACTIVE / builder.PARENT_CATALOG_VERSION, isolated / builder.PARENT_CATALOG_VERSION)
    write_pointer(isolated / "active.json", {
        "schema_version": "FINSIGHT-PSE-VALUATION-POINTER-1.0", "status": "active",
        "catalog_version": builder.PARENT_CATALOG_VERSION,
        "catalog_path": builder.PARENT_CATALOG_VERSION,
        "manifest_sha256": hashlib.sha256(parent_before).hexdigest(),
    })
    result = activate(candidate_root, isolated)
    assert result["active"] == builder.CATALOG_VERSION and result["count"] == 278
    assert load_pointer(isolated, "active.json").manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert hashlib.sha256((isolated / "active.json").read_bytes()).hexdigest() == CONFIRMED_ACTIVE_POINTER_SHA256
    assert tree(isolated / builder.PARENT_CATALOG_VERSION) == tree(ACTIVE / builder.PARENT_CATALOG_VERSION)
    assert tree(isolated / builder.CATALOG_VERSION) == tree(candidate_catalog)
    assert preflight(candidate_root, isolated)["active_before"] == builder.CATALOG_VERSION
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before


def test_confirmed_guard_rejects_candidate_artifact_drift(tmp_path):
    candidate_root = tmp_path / "candidate"
    catalog_root = builder.build(candidate_root)
    artifact = catalog_root / "artifacts" / "PNC.json"
    artifact.write_bytes(artifact.read_bytes() + b" ")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        preflight(candidate_root)
