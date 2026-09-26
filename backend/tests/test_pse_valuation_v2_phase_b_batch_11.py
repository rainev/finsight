import hashlib
import json
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_11 import (
    FROZEN_BATCH_TICKERS,
    build_batch_artifacts,
    load_batch_config,
    source_receipt,
)
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_11 import CONFIRMED_MANIFEST_SHA256
from scripts.build_pse_v2_phase_b_batch_11 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build
from scripts.build_pse_v2_phase_b_batch_28 import CATALOG_VERSION as ACTIVE_CATALOG_VERSION


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_membership_values_and_status():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    expected = {
        "SMC": 35.24,
        "LTG": 14.4,
        "AGI": 24.198,
        "COSCO": 14.778,
        "FDC": 15.042,
        "FPH": 190.816,
        "ANS": 18.786,
        "LPZ": 10.268,
        "APO": 1.83,
        "TFHI": 175.028,
    }
    for ticker, base in expected.items():
        artifact = artifacts[ticker]
        assert artifact.availability_type == "market_relative_only"
        assert artifact.publication_state == "provisional"
        assert artifact.currency == "PHP" and artifact.primary_model == "sotp"
        assert all(value is None for value in artifact.scenarios.values())
        assert artifact.market_relative["estimates"]["base"] == pytest.approx(base)
    assert any("must not be added" in warning for warning in artifacts["TFHI"].warnings)
    assert any("not additive" in warning for warning in artifacts["FPH"].warnings)


def test_receipts_and_calculators():
    config = load_batch_config()
    for ticker, artifact in build_batch_artifacts(config).items():
        reference, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == reference["sha256"]
        payload = artifact.model_dump(mode="json")
        calculated = calculate(payload, overrides={}, scenario="base", manual_price=None)
        assert calculated["result"]["base"] == pytest.approx(payload["market_relative"]["estimates"]["base"])


def test_deterministic_twins_and_parent_preservation(tmp_path):
    before = tree(ACTIVE)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second)
    assert tree(ACTIVE) == before
    assert len(load_pointer(first).entries) == 118
    parent = ACTIVE / PARENT_CATALOG_VERSION
    parent_manifest = json.loads((parent / "manifest.json").read_text())
    for entry in parent_manifest["entries"]:
        ticker = entry["ticker"]
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (parent / "artifacts" / f"{ticker}.json").read_bytes()


def test_router_parity_and_confirmed_result_hash(tmp_path, monkeypatch):
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["count"] == 118 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
        assert served["publication_state"] == "provisional"
        assert served["availability_type"] == "market_relative_only"
    assert load_pointer(tmp_path).manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert load_pointer(ACTIVE, "active.json").version == ACTIVE_CATALOG_VERSION
    assert (ACTIVE / CATALOG_VERSION / "manifest.json").is_file()
    assert (ACTIVE / PARENT_CATALOG_VERSION / "manifest.json").is_file()
