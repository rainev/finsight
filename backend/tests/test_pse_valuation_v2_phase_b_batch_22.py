"""Batch 22: source-scoped book screens and staged-catalog boundaries."""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_22 import (
    FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt,
)
from app.routers import pse_valuations
from scripts import build_pse_v2_phase_b_batch_22 as builder
from scripts.activate_pse_v2_phase_b_batch_22 import (
    CONFIRMED_ACTIVE_POINTER_SHA256, CONFIRMED_MANIFEST_SHA256,
    activate, preflight, write_pointer,
)


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"
REVIEWED_BRIDGES = {
    "CSB": (1466087430, 173865000, "total"),
    "ORE": (7055062031, 2878500005, "parent"),
    "ECVC": (1289748726, 6630000000, "total"),
    "GREEN": (1750986715, 4150778574, "parent"),
    "EGRN": (3567426561, 25000000000, "parent"),
    "ENEX": (23548036, 250000001, "parent"),
    "JAS": (180650832, 250059097, "total"),
    "NI": (239459312, 1010000000, "parent"),
    "WIN": (1382842122, 3276035637, "parent"),
    "PA": (102193148, 325000000, "parent"),
}


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_reviewed_equity_bridges_screens_and_receipts():
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS == tuple(REVIEWED_BRIDGES)
    for ticker, (equity, shares, basis) in REVIEWED_BRIDGES.items():
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        artifact = artifacts[ticker]
        assert (issuer["equity_value"], issuer["shares_outstanding"], issuer["equity_basis"]) == (equity, shares, basis)
        assert issuer["equity_unit_scale"] == "pesos" and issuer["period_end"] == "2026-06-30"
        assert artifact.availability_type == "market_relative_only" and artifact.publication_state == "provisional"
        assert artifact.primary_model == issuer["primary_model"] and artifact.public_assumptions["reliability"] == "Low"
        assert artifact.verify_artifact_hash() and artifact.price is None
        assert all(value is None for value in artifact.scenarios.values()) and artifact.blocking_reasons
        book = Decimal(equity) / Decimal(shares)
        assert artifact.market_relative["metric_value_per_share"] == pytest.approx(float(book))
        for scenario in ("low", "base", "high"):
            expected = round(float(book * Decimal(str(policy["assumptions"][scenario]))), 9)
            assert artifact.market_relative["estimates"][scenario] == expected
        references, receipt = source_receipt(ticker, config)
        assert len(references) == 2 and hashlib.sha256(receipt).hexdigest() == references[0]["sha256"]
        assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is True
    assert {t for t, (_, _, b) in REVIEWED_BRIDGES.items() if b == "total"} == {"CSB", "ECVC", "JAS"}
    result = calculate(artifacts["CSB"].model_dump(mode="json"), overrides={"valuation_multiple": 1.0}, scenario="base", manual_price=None)
    assert result["result"]["base"] == pytest.approx(1466087430 / 173865000)


def test_invalid_scope_shares_and_dates_fail(tmp_path):
    config = load_batch_config()
    path = tmp_path / "invalid.json"
    for ticker, field, value, message in (
        ("CSB", "shares_outstanding", 0, "common-equity bridge"),
        ("JAS", "equity_basis", "unspecified", "equity scope"),
        ("ORE", "equity_unit_scale", "millions", "equity scope"),
        ("WIN", "share_as_of", "2026-09-26", "dated facts"),
    ):
        bad = json.loads(json.dumps(config))
        bad["issuers"][ticker][field] = value
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match=message):
            load_batch_config(path)


def test_exact_228_deterministic_twins_parent_preservation_and_staged_router(tmp_path, monkeypatch):
    active_before = (ACTIVE / "active.json").read_bytes()
    parent_before = (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    catalog_root = builder.build(first)
    builder.build(second)
    assert tree(first) == tree(second)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
    catalog = load_pointer(first)
    assert catalog.version == builder.CATALOG_VERSION and catalog.status == "staged" and len(catalog.entries) == 228
    assert sum(entry.availability_type == "intrinsic_valuation" for entry in catalog.entries) == 34
    assert sum(entry.availability_type == "market_relative_only" for entry in catalog.entries) == 189
    assert {entry.ticker for entry in catalog.entries if entry.publication_state == "blocked"} == {"CDC", "HOUSE", "IS", "PAX", "PRIM"}
    parent = json.loads(parent_before)
    for entry in parent["entries"]:
        ticker = entry["ticker"]
        assert (catalog_root / "artifacts" / f"{ticker}.json").read_bytes() == (ACTIVE / builder.PARENT_CATALOG_VERSION / "artifacts" / f"{ticker}.json").read_bytes()
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", first)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    listing = pse_valuations.list_pse_valuations({"sub": 1, "role": "user"})
    assert listing["count"] == 228 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, {"sub": 1, "role": "user"})
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, {"sub": 1, "role": "user"})["can_calculate"] is True


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
    isolated = tmp_path / "isolated-serving"
    isolated.mkdir()
    shutil.copytree(ACTIVE / builder.PARENT_CATALOG_VERSION, isolated / builder.PARENT_CATALOG_VERSION)
    write_pointer(isolated / "active.json", {
        "schema_version": "FINSIGHT-PSE-VALUATION-POINTER-1.0",
        "status": "active",
        "catalog_version": builder.PARENT_CATALOG_VERSION,
        "catalog_path": builder.PARENT_CATALOG_VERSION,
        "manifest_sha256": hashlib.sha256(parent_before).hexdigest(),
    })
    checks = preflight(candidate_root, isolated)
    assert checks["active_before"] == builder.PARENT_CATALOG_VERSION
    assert checks["ready_for_separate_activation"] is True
    result = activate(candidate_root, isolated)
    assert result["active"] == builder.CATALOG_VERSION and result["count"] == 228
    assert load_pointer(isolated, "active.json").manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert hashlib.sha256((isolated / "active.json").read_bytes()).hexdigest() == CONFIRMED_ACTIVE_POINTER_SHA256
    assert tree(isolated / builder.PARENT_CATALOG_VERSION) == tree(ACTIVE / builder.PARENT_CATALOG_VERSION)
    assert tree(isolated / builder.CATALOG_VERSION) == tree(candidate_catalog)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
