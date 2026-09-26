"""Batch 28 four-company source claims, finite NXGEN screen and staged catalog."""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_28 import FROZEN_BATCH_TICKERS, SCALES, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts import build_pse_v2_phase_b_batch_28 as builder
from scripts.activate_pse_v2_phase_b_batch_28 import (
    CONFIRMED_ACTIVE_POINTER_SHA256, CONFIRMED_MANIFEST_SHA256,
    activate, preflight, write_pointer,
)


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"
REVIEWED = {
    "AAA": (-20011318, 799999981, "2014-06-30", "not_available"),
    "EG": (2658824951, 30000000000, "2019-09-30", "not_available"),
    "NXGEN": (669333909, 1490000003, "2026-06-30", "market_relative_only"),
    "PTT": (173718, 1500000000, "2026-06-30", "not_available"),
}


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_four_reviewed_common_lines_one_relative_screen_three_null():
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS == tuple(REVIEWED)
    for ticker, (equity, shares, period, availability) in REVIEWED.items():
        issuer = config["issuers"][ticker]
        artifact = artifacts[ticker]
        assert (issuer["equity_value"], issuer["shares_outstanding"], issuer["period_end"], issuer["availability"]) == (equity, shares, period, availability)
        assert artifact.price is None and artifact.verify_artifact_hash()
        assert all(value is None for value in artifact.scenarios.values()) and artifact.blocking_reasons
        references, raw = source_receipt(ticker, config)
        receipt = json.loads(raw)
        assert len(references) >= 2 and hashlib.sha256(raw).hexdigest() == references[0]["sha256"]
        assert receipt["facts"]["reported_equity"]["value"] == equity
        assert receipt["facts"]["reported_equity"]["unit_scale"] == issuer["equity_unit_scale"]
        assert receipt["facts"]["reported_share_classes"][0]["shares"] == shares
        if issuer["share_bridge_type"] == "unresolved_claims":
            assert receipt["facts"]["reviewed_common_denominator"] is None
        if availability == "not_available":
            assert artifact.publication_state == "blocked" and artifact.market_relative is None
            assert artifact.numerical_range == {"low": None, "high": None}
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is False
        else:
            assert ticker == "NXGEN" and artifact.publication_state == "provisional"
            assert artifact.public_assumptions["reliability"] == "Low"
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is True
            book = Decimal(equity) * Decimal(SCALES[issuer["equity_unit_scale"]]) / Decimal(shares)
            policy = config["policies"][issuer["policy"]]
            for case in ("low", "base", "high"):
                assert artifact.market_relative["estimates"][case] == round(float(book * Decimal(str(policy["assumptions"][case]))), 9)
            assert receipt["facts"]["derived_php_parent_equity_per_common_share"] == pytest.approx(float(book))
    assert config["issuers"]["PTT"]["source_currency_label"] == "In thousand pesos"
    assert config["issuers"]["PTT"]["equity_basis"] == "total"
    assert config["issuers"]["NXGEN"]["reported_bvps"] == 0.51
    assert set(t for t, a in artifacts.items() if a.publication_state == "blocked") == {"AAA", "EG", "PTT"}


def test_unsupported_relative_claims_and_dates_fail(tmp_path):
    config = load_batch_config()
    path = tmp_path / "bad.json"
    for ticker, field, value, message in (
        ("NXGEN", "equity_basis", "total", "dated parent/common bridge"),
        ("NXGEN", "share_bridge_type", "unresolved_claims", "dated parent/common bridge"),
        ("NXGEN", "shares_outstanding", 0, "positive sourced common-share line"),
        ("AAA", "availability", "market_relative_only", "dated parent/common bridge"),
        ("PTT", "currency", "USD", "source currency"),
        ("EG", "share_as_of", "2026-09-27", "dated facts exceed"),
    ):
        bad = json.loads(json.dumps(config))
        bad["issuers"][ticker][field] = value
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match=message):
            load_batch_config(path)


def test_282_deterministic_twins_exact_parent_and_staged_router(tmp_path, monkeypatch):
    active_before = (ACTIVE / "active.json").read_bytes()
    parent_before = (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    catalog_root = builder.build(first)
    builder.build(second)
    assert tree(first) == tree(second)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
    catalog = load_pointer(first)
    assert catalog.version == builder.CATALOG_VERSION and catalog.status == "staged" and len(catalog.entries) == 282
    assert sum(e.availability_type == "intrinsic_valuation" for e in catalog.entries) == 34
    assert sum(e.availability_type == "market_relative_only" for e in catalog.entries) == 205
    assert sum(e.availability_type == "not_available" for e in catalog.entries) == 43
    parent = json.loads(parent_before)
    for entry in parent["entries"]:
        ticker = entry["ticker"]
        assert (catalog_root / "artifacts" / f"{ticker}.json").read_bytes() == (ACTIVE / builder.PARENT_CATALOG_VERSION / "artifacts" / f"{ticker}.json").read_bytes()
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", first)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    listing = pse_valuations.list_pse_valuations({"sub": 1, "role": "user"})
    assert listing["count"] == 282 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, {"sub": 1, "role": "user"})
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, {"sub": 1, "role": "user"})["can_calculate"] is (ticker == "NXGEN")


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
    assert checks["active_before"] == builder.CATALOG_VERSION
    assert checks["ready_for_separate_activation"] is True
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
    assert result["active"] == builder.CATALOG_VERSION and result["count"] == 282
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
    artifact = catalog_root / "artifacts" / "NXGEN.json"
    artifact.write_bytes(artifact.read_bytes() + b" ")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        preflight(candidate_root)
