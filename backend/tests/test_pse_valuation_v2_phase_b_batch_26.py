"""Batch 26 suspended-line claims, historical MM screen and staged catalog."""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_26 import FROZEN_BATCH_TICKERS, SCALES, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts import build_pse_v2_phase_b_batch_26 as builder
from scripts.activate_pse_v2_phase_b_batch_26 import (
    CONFIRMED_ACTIVE_POINTER_SHA256, CONFIRMED_MANIFEST_SHA256,
    activate, preflight, write_pointer,
)


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"
REVIEWED = {
    "DHI": (3473823424, 2162475312, "not_available"),
    "HOME": (16230243466, 3750000002, "not_available"),
    "MM": (3003150995, 7594936709, "market_relative_only"),
    "STR": (58499, 8425981156, "not_available"),
    "VLC": (13372649, 644117649, "not_available"),
    "UNH": (8987615495, 70765401, "not_available"),
    "PNX": (10083802981, 1442866332, "not_available"),
    "ROX": (2238923, 1547935799, "not_available"),
    "INFRA": (100923208521, 6061560322, "not_available"),
    "I": (-29941687, 611639122, "not_available"),
}


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_reviewed_suspended_claims_one_historical_screen_nine_null():
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS == tuple(REVIEWED)
    for ticker, (equity, shares, availability) in REVIEWED.items():
        issuer = config["issuers"][ticker]
        artifact = artifacts[ticker]
        assert (issuer["equity_value"], issuer["shares_outstanding"], issuer["availability"]) == (equity, shares, availability)
        assert issuer["trading_status"] == "suspended" and artifact.price is None and artifact.verify_artifact_hash()
        assert all(value is None for value in artifact.scenarios.values()) and artifact.blocking_reasons
        references, receipt_raw = source_receipt(ticker, config)
        receipt = json.loads(receipt_raw)
        assert len(references) >= 2 and hashlib.sha256(receipt_raw).hexdigest() == references[0]["sha256"]
        if issuer["share_bridge_type"] == "unresolved_claims":
            assert receipt["facts"]["reviewed_common_denominator"] is None
        if availability == "not_available":
            assert artifact.publication_state == "blocked"
            assert artifact.market_relative is None and artifact.numerical_range == {"low": None, "high": None}
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is False
        else:
            assert ticker == "MM" and artifact.publication_state == "provisional"
            assert artifact.public_assumptions["reliability"] == "Low" and artifact.public_assumptions["screen_time_basis"] == "historical_2026_q1"
            assert "no current quote or upside" in artifact.market_relative["note"]
            policy = config["policies"][issuer["policy"]]
            book = Decimal(equity) * Decimal(SCALES[issuer["equity_unit_scale"]]) / Decimal(shares)
            for case in ("low", "base", "high"):
                expected = round(float(book * Decimal(str(policy["assumptions"][case]))), 9)
                assert artifact.market_relative["estimates"][case] == expected
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is True
    assert {t for t, a in artifacts.items() if a.publication_state == "blocked"} == set(FROZEN_BATCH_TICKERS) - {"MM"}
    assert config["issuers"]["STR"]["equity_unit_scale"] == "millions"
    assert config["issuers"]["VLC"]["equity_unit_scale"] == "thousands"
    assert config["issuers"]["ROX"]["period_end"] == "2024-06-30"


def test_bad_suspended_screen_claims_and_dates_fail(tmp_path):
    config = load_batch_config()
    path = tmp_path / "bad.json"
    for ticker, field, value, message in (
        ("MM", "screen_time_basis", None, "dated historical parent/common bridge"),
        ("MM", "shares_outstanding", 0, "positive shares"),
        ("DHI", "availability", "market_relative_only", "dated historical parent/common bridge"),
        ("HOME", "period_end", "2026-09-26", "dated facts exceed"),
        ("VLC", "currency", "CAD", "currency, units or scope"),
        ("I", "trading_status", "open", "suspension-risk batch"),
    ):
        bad = json.loads(json.dumps(config))
        bad["issuers"][ticker][field] = value
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match=message):
            load_batch_config(path)


def test_268_deterministic_twins_exact_parent_and_staged_router(tmp_path, monkeypatch):
    active_before = (ACTIVE / "active.json").read_bytes()
    parent_before = (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    catalog_root = builder.build(first)
    builder.build(second)
    assert tree(first) == tree(second)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
    catalog = load_pointer(first)
    assert catalog.version == builder.CATALOG_VERSION and catalog.status == "staged" and len(catalog.entries) == 268
    assert sum(e.availability_type == "intrinsic_valuation" for e in catalog.entries) == 34
    assert sum(e.availability_type == "market_relative_only" for e in catalog.entries) == 204
    assert sum(e.availability_type == "not_available" for e in catalog.entries) == 30
    parent = json.loads(parent_before)
    for entry in parent["entries"]:
        ticker = entry["ticker"]
        assert (catalog_root / "artifacts" / f"{ticker}.json").read_bytes() == (ACTIVE / builder.PARENT_CATALOG_VERSION / "artifacts" / f"{ticker}.json").read_bytes()
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", first)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    listing = pse_valuations.list_pse_valuations({"sub": 1, "role": "user"})
    assert listing["count"] == 268 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, {"sub": 1, "role": "user"})
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, {"sub": 1, "role": "user"})["can_calculate"] is (ticker == "MM")


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
    assert result["active"] == builder.CATALOG_VERSION and result["count"] == 268
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
    artifact = catalog_root / "artifacts" / "MM.json"
    artifact.write_bytes(artifact.read_bytes() + b" ")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        preflight(candidate_root)
