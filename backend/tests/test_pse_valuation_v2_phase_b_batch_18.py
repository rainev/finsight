import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_18 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_18 import CONFIRMED_MANIFEST_SHA256, activate, preflight, write_pointer
from scripts.build_pse_v2_phase_b_batch_18 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_exact_relative_values_status_and_claim_warnings():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    expected = {
        "PBC": (26.844, 35.792, 44.74), "PTC": (13.932, 18.576, 23.22),
        "V": (0.6175, 0.988, 1.3585), "BKR": (0.24, 0.384, 0.528),
        "APC": (0.005, 0.008, 0.011), "IPM": (0.307254447, 0.491607115, 0.675959783),
        "SGI": (1.79, 2.864, 3.938), "CTS": (0.0725, 0.116, 0.1595),
        "REG": (0.898460091, 1.437536146, 1.976612201),
        "ECP": (0.49437118, 0.823951967, 1.153532753),
    }
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        assert artifact.availability_type == "market_relative_only" and artifact.publication_state == "provisional"
        assert artifact.currency == "PHP" and all(value is None for value in artifact.scenarios.values())
        assert tuple(artifact.market_relative["estimates"][key] for key in ("low", "base", "high")) == pytest.approx(values)
        assert artifact.public_assumptions["reliability"] == "Low" and artifact.verify_artifact_hash()
        view = calculator_view(artifact.model_dump(mode="json"))
        assert view["can_calculate"] is True and view["baseline_result"]["base"] == pytest.approx(values[1])
    assert artifacts["PBC"].primary_model == artifacts["PTC"].primary_model == "residual_income"
    assert "zero parent" in artifacts["PTC"].warnings[-1]
    assert "zero gross revenue" in artifacts["APC"].warnings[-1]
    for ticker in ("IPM", "REG", "ECP"):
        assert "parent equity per common share" in artifacts[ticker].warnings[-1]


def test_independent_parent_equity_arithmetic_and_fact_gates(tmp_path):
    config = load_batch_config()
    expected = {
        "IPM": Decimal(848022273) / Decimal(690000000),
        "REG": Decimal(2451235) * 1000 / Decimal(682065632),
        "ECP": Decimal(247185590) / Decimal(150000000),
    }
    for ticker, value in expected.items():
        assert float(value) == pytest.approx(config["issuers"][ticker]["metric_value_per_share"])
        assert float(value) < config["issuers"][ticker]["reported_total_bvps"]["value"]
    for ticker in FROZEN_BATCH_TICKERS:
        references, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == references[0]["sha256"]
        assert all(reference["sha256"] == references[0]["sha256"] for reference in references)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["IPM"]["reported_shares"]["value"] = 0
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="parent capital"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["REG"]["reported_parent_equity"]["unit_scale"] = "millions"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="parent capital"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["PTC"]["reported_bvps"]["period_end"] = "2025-12-31"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="BVPS source"):
        load_batch_config(path)
    result = calculate(build_batch_artifacts()["ECP"].model_dump(mode="json"), overrides={"valuation_multiple": 0.6}, scenario="base", manual_price=None)
    assert result["result"]["base"] == pytest.approx(float(expected["ECP"]) * 0.6)


def test_deterministic_twins_parent_preservation_and_confirmed_preflight(tmp_path):
    before = tree(ACTIVE)
    first, second = tmp_path / "first", tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second) and tree(ACTIVE) == before
    catalog = load_pointer(first)
    assert len(catalog.entries) == 188
    assert sum(entry.availability_type == "intrinsic_valuation" for entry in catalog.entries) == 34
    assert sum(entry.availability_type == "market_relative_only" for entry in catalog.entries) == 152
    assert {entry.ticker for entry in catalog.entries if entry.publication_state == "blocked"} == {"CDC", "HOUSE"}
    parent = ACTIVE / PARENT_CATALOG_VERSION
    for entry in json.loads((parent / "manifest.json").read_text())["entries"]:
        ticker = entry["ticker"]
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (parent / "artifacts" / f"{ticker}.json").read_bytes()
    assert catalog.manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    isolated_serving = tmp_path / "isolated-serving"
    isolated_serving.mkdir()
    shutil.copytree(parent, isolated_serving / PARENT_CATALOG_VERSION)
    write_pointer(isolated_serving / "active.json", {"schema_version": "FINSIGHT-PSE-VALUATION-POINTER-1.0", "status": "active", "catalog_version": PARENT_CATALOG_VERSION, "catalog_path": PARENT_CATALOG_VERSION, "manifest_sha256": hashlib.sha256((parent / "manifest.json").read_bytes()).hexdigest()})
    checks = preflight(first, isolated_serving)
    assert checks["active_before"] == PARENT_CATALOG_VERSION
    assert checks["ready_for_separate_activation"] is True
    activated = activate(first, isolated_serving)
    assert activated["active"] == CATALOG_VERSION and activated["count"] == 188
    assert load_pointer(isolated_serving, "active.json").manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert tree(parent) == tree(isolated_serving / PARENT_CATALOG_VERSION)
    assert tree(ACTIVE) == before
    assert load_pointer(ACTIVE, "active.json").version == "PSE-V2-PHASE-B-B28-2026-09-26-1.0"
    assert tree(ACTIVE / CATALOG_VERSION) == tree(first_catalog)


def test_staged_router_parity(tmp_path, monkeypatch):
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["count"] == 188 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
    assert pse_valuations.get_pse_valuation_calculator("HOUSE", user)["can_calculate"] is False
