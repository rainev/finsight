import hashlib
import json
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_12 import BLOCKED_TICKERS, FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_12 import CONFIRMED_MANIFEST_SHA256
from scripts.build_pse_v2_phase_b_batch_12 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build
from scripts.build_pse_v2_phase_b_batch_28 import CATALOG_VERSION as ACTIVE_CATALOG_VERSION


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_exact_membership_values_and_blocked_status():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    assert BLOCKED_TICKERS == ("CDC",)
    expected = {
        "CPG": (0.648, 0.972, 1.296),
        "ROCK": (2.451, 3.6765, 4.902),
        "SHNG": (3.48, 5.22, 6.96),
        "DD": (4.86, 7.776, 10.692),
        "ALLHC": (0.72, 1.08, 1.44),
        "ARA": (0.351, 0.5265, 0.702),
        "PHES": (0.303, 0.4545, 0.606),
        "RLT": (0.216, 0.324, 0.432),
        "BRN": (0.6975, 1.116, 1.5345),
    }
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        assert artifact.availability_type == "market_relative_only"
        assert artifact.publication_state == "provisional"
        assert artifact.primary_model == "sotp" and artifact.currency == "PHP"
        assert all(value is None for value in artifact.scenarios.values())
        assert tuple(artifact.market_relative["estimates"][key] for key in ("low", "base", "high")) == pytest.approx(values)
        assert artifact.verify_artifact_hash()
    blocked = artifacts["CDC"]
    assert blocked.availability_type == "not_available" and blocked.publication_state == "blocked"
    assert blocked.market_relative is None and blocked.numerical_range == {"low": None, "high": None}
    assert all(value is None for value in blocked.scenarios.values())
    assert blocked.blocking_reasons and len(blocked.sources) == 2
    assert any("must not be added" in warning for warning in artifacts["DD"].warnings)
    assert any("not additive" in warning for warning in artifacts["ALLHC"].warnings)


def test_source_receipts_and_calculator_states():
    config = load_batch_config()
    for ticker, artifact in build_batch_artifacts(config).items():
        references, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == references[0]["sha256"]
        assert all(reference["sha256"] == references[0]["sha256"] for reference in references)
        payload = artifact.model_dump(mode="json")
        view = calculator_view(payload)
        if ticker == "CDC":
            assert view["can_calculate"] is False and view["baseline_result"] is None
            with pytest.raises(ValueError, match="unavailable"):
                calculate(payload, overrides={}, scenario="base", manual_price=None)
        else:
            assert view["can_calculate"] is True
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
    catalog = load_pointer(first)
    assert len(catalog.entries) == 128
    assert sum(entry.availability_type == "not_available" for entry in catalog.entries) == 1
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
    assert listing["count"] == 128 and listing["catalog_status"] == "staged"
    assert next(row for row in listing["items"] if row["ticker"] == "CDC")["base"] is None
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
    cdc_view = pse_valuations.get_pse_valuation_calculator("CDC", user)
    assert cdc_view["can_calculate"] is False and cdc_view["baseline_result"] is None
    assert load_pointer(tmp_path).manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert load_pointer(ACTIVE, "active.json").version == ACTIVE_CATALOG_VERSION
    assert (ACTIVE / CATALOG_VERSION / "manifest.json").is_file()
    assert (ACTIVE / PARENT_CATALOG_VERSION / "manifest.json").is_file()
