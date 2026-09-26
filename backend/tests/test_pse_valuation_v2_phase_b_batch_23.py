"""Batch 23 class/claim boundaries and deterministic staged catalog."""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_23 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts import build_pse_v2_phase_b_batch_23 as builder
from scripts.activate_pse_v2_phase_b_batch_23 import (
    CONFIRMED_ACTIVE_POINTER_SHA256, CONFIRMED_MANIFEST_SHA256,
    activate, preflight, write_pointer,
)


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"
REVIEWED_BRIDGES = {
    "BC": (10982048, 715861854, "thousands", "not_available"),
    "CA": (313390546, 27466449, "pesos", "market_relative_only"),
    "LC": (7634806, 66375758097, "thousands", "market_relative_only"),
    "ATN": (2568247205, 6825055429, "pesos", "market_relative_only"),
    "OPM": (84487332, 192063300000, "dollars", "not_available"),
    "FJP": (2089516655, 481827653, "pesos", "market_relative_only"),
    "DIZ": (25892569, 79087487, "pesos", "market_relative_only"),
    "IMP": (989306677, 652500000, "pesos", "market_relative_only"),
    "FERRO": (157514702, 341824002, "pesos", "market_relative_only"),
    "ABG": (246342895, 300000000, "pesos", "market_relative_only"),
}


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_reviewed_class_bridges_relative_screens_and_null_blocks():
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS == tuple(REVIEWED_BRIDGES)
    for ticker, (equity, shares, units, availability) in REVIEWED_BRIDGES.items():
        issuer = config["issuers"][ticker]
        artifact = artifacts[ticker]
        assert (issuer["equity_value"], issuer["shares_outstanding"], issuer["equity_unit_scale"], issuer["availability"]) == (equity, shares, units, availability)
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
            assert issuer["currency"] == "PHP" and artifact.publication_state == "provisional"
            assert artifact.public_assumptions["reliability"] == "Low"
            policy = config["policies"][issuer["policy"]]
            book = Decimal(equity) * (1000 if units == "thousands" else 1) / Decimal(shares)
            for scenario in ("low", "base", "high"):
                expected = round(float(book * Decimal(str(policy["assumptions"][scenario]))), 9)
                assert artifact.market_relative["estimates"][scenario] == expected
            assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is True
    assert artifacts["CA"].public_assumptions["share_bridge_type"] == "reported_total_declassification"
    assert artifacts["ATN"].filing_period == "2026-06-30"
    assert "March 31" in artifacts["ATN"].warnings[-1]
    assert "USD" in artifacts["OPM"].warnings[-1]


def test_bad_class_sum_currency_and_denominator_are_rejected(tmp_path):
    config = load_batch_config()
    path = tmp_path / "bad.json"
    for ticker, field, value, message in (
        ("LC", "shares_outstanding", 39822869196, "pooled common shares"),
        ("DIZ", "currency", "USD", "equity units"),
        ("CA", "shares_outstanding", 0, "positive reported equity and shares"),
        ("FJP", "share_as_of", "2026-09-26", "dated facts"),
    ):
        bad = json.loads(json.dumps(config))
        bad["issuers"][ticker][field] = value
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match=message):
            load_batch_config(path)


def test_238_deterministic_twins_exact_parent_and_staged_router(tmp_path, monkeypatch):
    active_before = (ACTIVE / "active.json").read_bytes()
    parent_before = (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    catalog_root = builder.build(first)
    builder.build(second)
    assert tree(first) == tree(second)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
    catalog = load_pointer(first)
    assert catalog.version == builder.CATALOG_VERSION and catalog.status == "staged" and len(catalog.entries) == 238
    assert sum(e.availability_type == "intrinsic_valuation" for e in catalog.entries) == 34
    assert sum(e.availability_type == "market_relative_only" for e in catalog.entries) == 197
    assert {e.ticker for e in catalog.entries if e.publication_state == "blocked"} == {"CDC", "HOUSE", "IS", "PAX", "PRIM", "BC", "OPM"}
    parent = json.loads(parent_before)
    for entry in parent["entries"]:
        ticker = entry["ticker"]
        assert (catalog_root / "artifacts" / f"{ticker}.json").read_bytes() == (ACTIVE / builder.PARENT_CATALOG_VERSION / "artifacts" / f"{ticker}.json").read_bytes()
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", first)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    listing = pse_valuations.list_pse_valuations({"sub": 1, "role": "user"})
    assert listing["count"] == 238 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, {"sub": 1, "role": "user"})
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, {"sub": 1, "role": "user"})["can_calculate"] is (ticker not in {"BC", "OPM"})


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
        "schema_version": "FINSIGHT-PSE-VALUATION-POINTER-1.0", "status": "active",
        "catalog_version": builder.PARENT_CATALOG_VERSION,
        "catalog_path": builder.PARENT_CATALOG_VERSION,
        "manifest_sha256": hashlib.sha256(parent_before).hexdigest(),
    })
    checks = preflight(candidate_root, isolated)
    assert checks["active_before"] == builder.PARENT_CATALOG_VERSION
    assert checks["ready_for_separate_activation"] is True
    result = activate(candidate_root, isolated)
    assert result["active"] == builder.CATALOG_VERSION and result["count"] == 238
    assert load_pointer(isolated, "active.json").manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert hashlib.sha256((isolated / "active.json").read_bytes()).hexdigest() == CONFIRMED_ACTIVE_POINTER_SHA256
    assert tree(isolated / builder.PARENT_CATALOG_VERSION) == tree(ACTIVE / builder.PARENT_CATALOG_VERSION)
    assert tree(isolated / builder.CATALOG_VERSION) == tree(candidate_catalog)
    assert (ACTIVE / "active.json").read_bytes() == active_before
    assert (ACTIVE / builder.PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_before
