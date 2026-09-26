import hashlib
import json
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_13 import FROZEN_BATCH_TICKERS, USD_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_13 import CONFIRMED_MANIFEST_SHA256
from scripts.build_pse_v2_phase_b_batch_13 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build
from scripts.build_pse_v2_phase_b_batch_28 import CATALOG_VERSION as ACTIVE_CATALOG_VERSION


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_exact_membership_values_and_source_units():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    expected = {
        "IMI": (2.257128, 3.76188, 5.266632),
        "TECH": (5.830914, 9.71819, 13.605466),
        "ION": (1.504752, 2.50792, 3.511088),
        "CIC": (7.05, 9.87, 12.69),
        "MVC": (3.415, 4.781, 6.147),
        "CROWN": (1.99, 2.786, 3.582),
        "STN": (0.45, 0.63, 0.81),
        "LFM": (7.325, 10.255, 13.185),
        "VMC": (1.3, 1.82, 2.34),
        "SBS": (1.555, 2.177, 2.799),
    }
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        assert artifact.availability_type == "market_relative_only"
        assert artifact.publication_state == "provisional"
        assert artifact.currency == "PHP"
        assert all(value is None for value in artifact.scenarios.values())
        assert tuple(artifact.market_relative["estimates"][key] for key in ("low", "base", "high")) == pytest.approx(values)
        assert artifact.verify_artifact_hash()
    assert artifacts["VMC"].filing_period == "2026-05-31"
    assert all(artifacts[ticker].public_assumptions["fx_rate_php_per_usd"] == 62.698 for ticker in USD_TICKERS)
    assert all(any(source.url and source.url.startswith("https://www.bsp.gov.ph/") for source in artifacts[ticker].sources) for ticker in USD_TICKERS)
    assert any("preferred" in warning for warning in artifacts["TECH"].warnings)
    assert any("direct distribution" in warning for warning in artifacts["LFM"].warnings)


def test_fx_snapshot_receipts_and_calculators(tmp_path):
    config = load_batch_config()
    for ticker, artifact in build_batch_artifacts(config).items():
        references, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == references[0]["sha256"]
        assert all(reference["sha256"] == references[0]["sha256"] for reference in references)
        payload = artifact.model_dump(mode="json")
        calculated = calculate(payload, overrides={}, scenario="base", manual_price=None)
        assert calculated["result"]["base"] == pytest.approx(payload["market_relative"]["estimates"]["base"])
    assert calculate(build_batch_artifacts()["TECH"].model_dump(mode="json"), overrides={"valuation_multiple": 0.6}, scenario="base", manual_price=None)["result"]["base"] == pytest.approx(11.661828)
    bad = json.loads(json.dumps(config))
    bad["fx_snapshot"]["rate_php_per_usd"] = 62.799
    path = tmp_path / "bad-fx.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="reconcile|differs"):
        load_batch_config(path)


def test_deterministic_twins_and_parent_preservation(tmp_path):
    before = tree(ACTIVE)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second)
    assert tree(ACTIVE) == before
    catalog = load_pointer(first)
    assert len(catalog.entries) == 138
    parent = ACTIVE / PARENT_CATALOG_VERSION
    parent_manifest = json.loads((parent / "manifest.json").read_text())
    for entry in parent_manifest["entries"]:
        ticker = entry["ticker"]
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (parent / "artifacts" / f"{ticker}.json").read_bytes()


def test_staged_router_parity_and_confirmed_result_hash(tmp_path, monkeypatch):
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["count"] == 138 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
    assert load_pointer(tmp_path).manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert load_pointer(ACTIVE, "active.json").version == ACTIVE_CATALOG_VERSION
    assert (ACTIVE / PARENT_CATALOG_VERSION / "manifest.json").is_file()
