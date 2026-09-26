import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_15 import BLOCKED_TICKERS, FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_15 import CONFIRMED_MANIFEST_SHA256, activate, preflight
from scripts.build_pse_v2_phase_b_batch_15 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_exact_membership_values_and_delisted_null_contract():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS and BLOCKED_TICKERS == ("HOUSE",)
    expected = {"ALCO": (0.363, 0.5445, 0.726), "ALHI": (3.444, 5.166, 6.888), "APVI": (3.486, 5.229, 6.972), "CEI": (0.045, 0.0675, 0.09), "ELI": (0.606, 0.909, 1.212), "GERI": (1.194, 1.791, 2.388), "KPPI": (1.278, 1.917, 2.556), "PRMX": (0.258, 0.387, 0.516), "SLI": (1.2, 1.8, 2.4)}
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        assert artifact.availability_type == "market_relative_only" and artifact.publication_state == "provisional"
        assert artifact.primary_model == "sotp" and artifact.currency == "PHP"
        assert tuple(artifact.market_relative["estimates"][key] for key in ("low", "base", "high")) == pytest.approx(values)
        assert all(value is None for value in artifact.scenarios.values()) and artifact.verify_artifact_hash()
        view = calculator_view(artifact.model_dump(mode="json"))
        assert view["can_calculate"] is True and view["baseline_result"]["base"] == pytest.approx(values[1])
    house = artifacts["HOUSE"]
    assert house.availability_type == "not_available" and house.publication_state == "blocked"
    assert house.market_relative is None and house.numerical_range == {"low": None, "high": None}
    assert all(value is None for value in house.scenarios.values()) and house.verify_artifact_hash()
    assert house.public_assumptions["listing_status"] == "delisted"
    assert any("delisted" in reason.lower() for reason in house.blocking_reasons)
    assert calculator_view(house.model_dump(mode="json"))["can_calculate"] is False
    with pytest.raises(ValueError, match="unavailable"):
        calculate(house.model_dump(mode="json"), overrides={}, scenario="base", manual_price=None)
    assert artifacts["ALCO"].filing_period == "2026-03-31" and house.filing_period == "2025-06-30"
    assert all("MEG" in artifacts[ticker].warnings[-1] for ticker in ("ELI", "GERI"))


def test_source_receipts_and_config_gates(tmp_path):
    config = load_batch_config()
    for ticker in FROZEN_BATCH_TICKERS:
        references, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == references[0]["sha256"]
        assert all(reference["sha256"] == references[0]["sha256"] for reference in references)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["ALCO"]["source"]["period_end"] = "2026-06-30"
    path = tmp_path / "bad-period.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="period"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["HOUSE"]["availability"] = "market_relative_only"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="availability"):
        load_batch_config(path)


def test_deterministic_twins_parent_preservation_and_confirmed_preflight(tmp_path):
    before = tree(ACTIVE)
    first, second = tmp_path / "first", tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second) and tree(ACTIVE) == before
    catalog = load_pointer(first)
    assert len(catalog.entries) == 158
    assert sum(entry.availability_type == "not_available" for entry in catalog.entries) == 2
    parent = ACTIVE / PARENT_CATALOG_VERSION
    for entry in json.loads((parent / "manifest.json").read_text())["entries"]:
        ticker = entry["ticker"]
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (parent / "artifacts" / f"{ticker}.json").read_bytes()
    assert load_pointer(first).manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    isolated_serving = tmp_path / "isolated-serving"
    isolated_serving.mkdir()
    shutil.copytree(parent, isolated_serving / PARENT_CATALOG_VERSION)
    (isolated_serving / "active.json").write_text(json.dumps({"schema_version": "FINSIGHT-PSE-VALUATION-POINTER-1.0", "status": "active", "catalog_version": PARENT_CATALOG_VERSION, "catalog_path": PARENT_CATALOG_VERSION, "manifest_sha256": hashlib.sha256((parent / "manifest.json").read_bytes()).hexdigest()}))
    assert preflight(first, isolated_serving)["active_before"] == PARENT_CATALOG_VERSION
    assert activate(first, isolated_serving)["count"] == 158
    assert load_pointer(isolated_serving, "active.json").version == CATALOG_VERSION
    assert (isolated_serving / PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == (parent / "manifest.json").read_bytes()
    assert load_pointer(ACTIVE, "active.json").version == "PSE-V2-PHASE-B-B28-2026-09-26-1.0"
    assert tree(ACTIVE / CATALOG_VERSION) == tree(first_catalog)


def test_staged_router_parity(tmp_path, monkeypatch):
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["count"] == 158 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
    assert pse_valuations.get_pse_valuation_calculator("HOUSE", user)["can_calculate"] is False
