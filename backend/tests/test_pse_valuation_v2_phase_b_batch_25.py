"""Batch 25 source claims, null gates and deterministic staged catalog."""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_25 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts import build_pse_v2_phase_b_batch_25 as builder
from scripts.activate_pse_v2_phase_b_batch_25 import (
    CONFIRMED_ACTIVE_POINTER_SHA256, CONFIRMED_MANIFEST_SHA256,
    activate, preflight, write_pointer,
)


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"
REVIEWED = {
    "FFI": (233909191, 50167397, "market_relative_only"),
    "FYN": (1034724, 172819683, "not_available"),
    "MAH": (-25605905, 306122449, "not_available"),
    "MED": (36942978, 3159292441, "market_relative_only"),
    "MG": (134915911, 2369684619, "market_relative_only"),
    "ZHI": (710546, 2737044807, "not_available"),
    "LTL": (None, None, "not_available"),
    "VLL": (132676, 12698007676, "not_available"),
    "VREIT": (31082499, 7500000000, "not_available"),
    "ALLDY": (7011208592, 22857145000, "not_available"),
}


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_reviewed_claims_three_finite_and_seven_null():
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS == tuple(REVIEWED)
    for ticker, (equity, shares, availability) in REVIEWED.items():
        issuer = config["issuers"][ticker]
        artifact = artifacts[ticker]
        assert (issuer["equity_value"], issuer["shares_outstanding"], issuer["availability"]) == (equity, shares, availability)
        assert artifact.verify_artifact_hash() and artifact.price is None
        assert all(value is None for value in artifact.scenarios.values()) and artifact.blocking_reasons
        refs, receipt_raw = source_receipt(ticker, config)
        receipt = json.loads(receipt_raw)
        assert refs and hashlib.sha256(receipt_raw).hexdigest() == refs[0]["sha256"]
        if issuer["share_bridge_type"] == "unresolved_claims" or ticker == "LTL":
            assert receipt["facts"]["reviewed_common_denominator"] is None
        if availability == "not_available":
            assert artifact.publication_state == "blocked"
            assert artifact.market_relative is None and artifact.numerical_range == {"low": None, "high": None}
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is False
        else:
            assert artifact.publication_state == "provisional" and artifact.public_assumptions["reliability"] == "Low"
            policy = config["policies"][issuer["policy"]]
            scale = {"pesos": 1, "thousands": 1000, "millions": 1000000}[issuer["equity_unit_scale"]]
            book = Decimal(equity) * Decimal(scale) / Decimal(shares)
            for case in ("low", "base", "high"):
                expected = round(float(book * Decimal(str(policy["assumptions"][case]))), 9)
                assert artifact.market_relative["estimates"][case] == expected
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is True
    assert {t for t, a in artifacts.items() if a.publication_state == "blocked"} == {"FYN", "MAH", "ZHI", "LTL", "VLL", "VREIT", "ALLDY"}
    assert config["issuers"]["FYN"]["equity_unit_scale"] == "thousands"
    assert json.loads(source_receipt("FYN", config)[1])["facts"]["reported_preferred_shares"] == {"value": 33426498, "as_of": "2026-08-19", "claim_value": None}
    assert config["issuers"]["VLL"]["equity_unit_scale"] == "millions"
    assert config["issuers"]["LTL"]["equity_value"] is None


def test_bad_claim_period_and_status_fail(tmp_path):
    config = load_batch_config()
    path = tmp_path / "bad.json"
    for ticker, field, value, message in (
        ("MED", "shares_outstanding", 0, "positive common shares"),
        ("FYN", "availability", "market_relative_only", "current reviewed common bridge"),
        ("MG", "status_as_of", "2026-09-26", "stock status exceeds"),
        ("FFI", "period_end", "2025-09-30", "current reviewed common bridge"),
        ("LTL", "shares_outstanding", 0, "positive common shares"),
        ("VLL", "policy", "layered_book", "blocked issuer"),
    ):
        bad = json.loads(json.dumps(config))
        bad["issuers"][ticker][field] = value
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match=message):
            load_batch_config(path)


def test_258_deterministic_twins_exact_parent_and_staged_router(tmp_path, monkeypatch):
    active_before = (ACTIVE / "active.json").read_bytes()
    parent_before = (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    catalog_root = builder.build(first)
    builder.build(second)
    assert tree(first) == tree(second)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
    catalog = load_pointer(first)
    assert catalog.version == builder.CATALOG_VERSION and catalog.status == "staged" and len(catalog.entries) == 258
    assert sum(e.availability_type == "intrinsic_valuation" for e in catalog.entries) == 34
    assert sum(e.availability_type == "market_relative_only" for e in catalog.entries) == 203
    assert sum(e.availability_type == "not_available" for e in catalog.entries) == 21
    parent = json.loads(parent_before)
    for entry in parent["entries"]:
        ticker = entry["ticker"]
        assert (catalog_root / "artifacts" / f"{ticker}.json").read_bytes() == (ACTIVE / builder.PARENT_CATALOG_VERSION / "artifacts" / f"{ticker}.json").read_bytes()
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", first)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    listing = pse_valuations.list_pse_valuations({"sub": 1, "role": "user"})
    assert listing["count"] == 258 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, {"sub": 1, "role": "user"})
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, {"sub": 1, "role": "user"})["can_calculate"] is (ticker in {"FFI", "MED", "MG"})


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
    assert result["active"] == builder.CATALOG_VERSION and result["count"] == 258
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
    artifact = catalog_root / "artifacts" / "FFI.json"
    artifact.write_bytes(artifact.read_bytes() + b" ")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        preflight(candidate_root)
