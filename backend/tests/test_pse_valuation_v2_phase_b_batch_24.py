"""Batch 24 currency/common-claim boundaries and deterministic staged catalog."""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_24 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts import build_pse_v2_phase_b_batch_24 as builder
from scripts.activate_pse_v2_phase_b_batch_24 import (
    CONFIRMED_ACTIVE_POINTER_SHA256, CONFIRMED_MANIFEST_SHA256,
    activate, preflight, write_pointer,
)


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"
REVIEWED_BRIDGES = {
    "AB": (-390230168, 2545000000, "PHP", "not_available"),
    "FPI": (261653330, 1838943246, "PHP", "market_relative_only"),
    "FAF": (-684615700, 1193200000, "PHP", "not_available"),
    "BH": (87100779, 499987, "PHP", "market_relative_only"),
    "GEO": (325798, 3500000000, "PHP", "not_available"),
    "UPM": (-336437679, 273836982480, "PHP", "not_available"),
    "MA": (3360556712, 311504146443, "PHP", "market_relative_only"),
    "X": (-213213964, 2713603812, "PHP", "not_available"),
    "MFC": (52324, 1656816042, "CAD", "not_available"),
    "SLF": (25765, 556714560, "CAD", "not_available"),
}


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_reviewed_claims_and_only_three_finite_php_screens():
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS == tuple(REVIEWED_BRIDGES)
    for ticker, (equity, shares, currency, availability) in REVIEWED_BRIDGES.items():
        issuer = config["issuers"][ticker]
        artifact = artifacts[ticker]
        assert (issuer["equity_value"], issuer["shares_outstanding"], issuer["currency"], issuer["availability"]) == (equity, shares, currency, availability)
        assert artifact.verify_artifact_hash() and artifact.price is None
        assert all(value is None for value in artifact.scenarios.values()) and artifact.blocking_reasons
        references, receipt = source_receipt(ticker, config)
        assert len(references) >= 2 and hashlib.sha256(receipt).hexdigest() == references[0]["sha256"]
        if issuer["share_bridge_type"] == "class_sum":
            assert sum(row["shares"] for row in issuer["share_classes"]) == shares
        if availability == "not_available":
            assert artifact.publication_state == "blocked"
            assert artifact.market_relative is None and artifact.numerical_range == {"low": None, "high": None}
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is False
        else:
            assert currency == "PHP" and equity > 0
            assert artifact.publication_state == "provisional" and artifact.public_assumptions["reliability"] == "Low"
            policy = config["policies"][issuer["policy"]]
            book = Decimal(equity) / Decimal(shares)
            for scenario in ("low", "base", "high"):
                expected = round(float(book * Decimal(str(policy["assumptions"][scenario]))), 9)
                assert artifact.market_relative["estimates"][scenario] == expected
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is True
    assert {t for t, a in artifacts.items() if a.publication_state == "blocked"} == {"AB", "FAF", "GEO", "UPM", "X", "MFC", "SLF"}
    assert config["issuers"]["MA"]["share_bridge_type"] == "class_sum"
    assert "C$ millions" in artifacts["MFC"].warnings[-1]


def test_bad_class_sum_currency_and_dates_fail(tmp_path):
    config = load_batch_config()
    path = tmp_path / "bad.json"
    for ticker, field, value, message in (
        ("MA", "shares_outstanding", 186955303646, "pooled common shares"),
        ("MFC", "availability", "market_relative_only", "PHP common book bridge"),
        ("FPI", "shares_outstanding", 0, "nonzero reported equity"),
        ("BH", "share_as_of", "2026-09-26", "dated facts"),
    ):
        bad = json.loads(json.dumps(config))
        bad["issuers"][ticker][field] = value
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match=message):
            load_batch_config(path)


def test_248_deterministic_twins_exact_parent_and_staged_router(tmp_path, monkeypatch):
    active_before = (ACTIVE / "active.json").read_bytes()
    parent_before = (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    catalog_root = builder.build(first)
    builder.build(second)
    assert tree(first) == tree(second)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
    catalog = load_pointer(first)
    assert catalog.version == builder.CATALOG_VERSION and catalog.status == "staged" and len(catalog.entries) == 248
    assert sum(e.availability_type == "intrinsic_valuation" for e in catalog.entries) == 34
    assert sum(e.availability_type == "market_relative_only" for e in catalog.entries) == 200
    assert {e.ticker for e in catalog.entries if e.publication_state == "blocked"} == {"AB", "FAF", "GEO", "UPM", "X", "MFC", "SLF", "BC", "OPM", "CDC", "HOUSE", "IS", "PAX", "PRIM"}
    parent = json.loads(parent_before)
    for entry in parent["entries"]:
        ticker = entry["ticker"]
        assert (catalog_root / "artifacts" / f"{ticker}.json").read_bytes() == (ACTIVE / builder.PARENT_CATALOG_VERSION / "artifacts" / f"{ticker}.json").read_bytes()
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", first)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    listing = pse_valuations.list_pse_valuations({"sub": 1, "role": "user"})
    assert listing["count"] == 248 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, {"sub": 1, "role": "user"})
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, {"sub": 1, "role": "user"})["can_calculate"] is (ticker in {"FPI", "BH", "MA"})


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
    assert result["active"] == builder.CATALOG_VERSION and result["count"] == 248
    assert load_pointer(isolated, "active.json").manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert hashlib.sha256((isolated / "active.json").read_bytes()).hexdigest() == CONFIRMED_ACTIVE_POINTER_SHA256
    assert tree(isolated / builder.PARENT_CATALOG_VERSION) == tree(ACTIVE / builder.PARENT_CATALOG_VERSION)
    assert tree(isolated / builder.CATALOG_VERSION) == tree(candidate_catalog)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
