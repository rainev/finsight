import hashlib
import json
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_09 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.build_pse_v2_phase_b_batch_09 import PARENT_CATALOG_VERSION, build


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_membership_values_and_normalization():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    assert all(artifact.availability_type == "market_relative_only" for artifact in artifacts.values())
    expected = {"FB": 50.4, "EMI": 14.08, "GSMI": 307.7, "RFM": 4.9, "MAXS": 3.6, "PIZZA": 5.33, "DELM": 3.825463275961893, "VITA": 0.462, "ANI": 1.64, "CAT": 13.048}
    for ticker, value in expected.items():
        assert artifacts[ticker].market_relative["estimates"]["base"] == pytest.approx(value)
        assert artifacts[ticker].currency == "PHP"
    config = load_batch_config()
    assert config["issuers"]["DELM"]["normalization"]["fx_rate"] == 62.799
    assert config["issuers"]["CAT"]["source"]["period_end"] == "2026-03-31"


def test_receipts_and_calculators():
    config = load_batch_config()
    for ticker, artifact in build_batch_artifacts(config).items():
        reference, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == reference["sha256"]
        payload = artifact.model_dump(mode="json")
        result = calculate(payload, overrides={}, scenario="base", manual_price=None)
        assert result["result"]["base"] == pytest.approx(payload["market_relative"]["estimates"]["base"])


def test_twins_and_active_preserved(tmp_path):
    before = tree(ACTIVE)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second)
    assert tree(ACTIVE) == before
    assert len(load_pointer(first).entries) == 98
    parent = ACTIVE / PARENT_CATALOG_VERSION
    parent_manifest = json.loads((parent / "manifest.json").read_text())
    for row in parent_manifest["entries"]:
        assert (first_catalog / "artifacts" / f"{row['ticker']}.json").read_bytes() == (parent / "artifacts" / f"{row['ticker']}.json").read_bytes()


def test_router_parity(tmp_path, monkeypatch):
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    assert pse_valuations.list_pse_valuations(user)["count"] == 98
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
        assert served["availability_type"] == "market_relative_only"
        assert served["publication_state"] == "provisional"
    delm = pse_valuations.get_pse_valuation("DELM", user)
    ani = pse_valuations.get_pse_valuation("ANI", user)
    assert any("last clearly labeled annual PSE summary" in warning for warning in delm["warnings"])
    assert any("FY2025 annual report remains unfiled" in warning for warning in ani["warnings"])
