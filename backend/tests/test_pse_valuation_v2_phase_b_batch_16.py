import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_16 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_16 import CONFIRMED_MANIFEST_SHA256, activate, preflight
from scripts.build_pse_v2_phase_b_batch_16 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_exact_status_values_and_source_periods():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    expected = {"AXLM": (2.16, 2.7, 3.24), "BALAI": (0.126, 0.21, 0.294), "FCG": (0.96, 1.2, 1.44), "FOOD": (0.16573964, 0.24860946, 0.33147928), "SFI": (0.001514377, 0.002271566, 0.003028755), "BCOR": (0.6825, 1.092, 1.5015), "BNCOM": (13.248, 17.664, 22.08), "BSC": (0.07, 0.112, 0.154), "PMPC": (6.34, 8.876, 11.412), "PPC": (15.6, 19.5, 23.4)}
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        assert artifact.availability_type == "market_relative_only" and artifact.publication_state == "provisional"
        assert artifact.currency == "PHP" and all(value is None for value in artifact.scenarios.values())
        assert tuple(artifact.market_relative["estimates"][key] for key in ("low", "base", "high")) == pytest.approx(values)
        assert artifact.public_assumptions["reliability"] == "Low" and artifact.verify_artifact_hash()
        view = calculator_view(artifact.model_dump(mode="json"))
        assert view["can_calculate"] is True and view["baseline_result"]["base"] == pytest.approx(values[1])
    assert artifacts["FCG"].filing_period == "2026-03-31" and artifacts["BCOR"].filing_period == "2026-03-31"
    assert artifacts["PMPC"].filing_period == "2026-06-30"
    assert artifacts["BNCOM"].primary_model == "residual_income"
    assert artifacts["FOOD"].public_assumptions["fx_rate_php_per_usd"] == 62.698
    assert artifacts["FOOD"].public_assumptions["fx_observed_at"] == "2026-09-23"
    assert any(source.url and source.url.startswith("https://www.bsp.gov.ph/") for source in artifacts["FOOD"].sources)
    assert "convertible preferred" in artifacts["SFI"].warnings[-1]
    assert "parent equity" in artifacts["BALAI"].warnings[-1]


def test_independent_fact_arithmetic_and_gate_failures(tmp_path):
    config = load_batch_config()
    assert Decimal("0.22") + Decimal("0.11") - Decimal("0.06") == Decimal("0.27")
    assert Decimal("0.12") + Decimal("0.08") - Decimal("0.08") == Decimal("0.12")
    assert Decimal("1.97") + Decimal("0.93") - Decimal("0.95") == Decimal("1.95")
    food = (Decimal(78817556) + Decimal(22813840) - Decimal(35552503)) * Decimal("62.698") / Decimal(2499712463)
    sfi = (Decimal(33489) + Decimal(10290) - Decimal(16241)) * Decimal(1000) / Decimal(1818436953)
    assert float(food) == pytest.approx(config["issuers"]["FOOD"]["metric_value_per_share"])
    assert float(sfi) == pytest.approx(config["issuers"]["SFI"]["metric_value_per_share"])
    for ticker in FROZEN_BATCH_TICKERS:
        references, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == references[0]["sha256"]
        assert all(reference["sha256"] == references[0]["sha256"] for reference in references)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["FCG"]["reported_eps"]["prior_ytd"]["period_end"] = "2025-06-30"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="aligned"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["fx_snapshot"]["rate_php_per_usd"] = 62.799
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="USD/PHP"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["SFI"]["reported_shares"]["value"] = 0
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="share count"):
        load_batch_config(path)
    assert calculate(build_batch_artifacts()["AXLM"].model_dump(mode="json"), overrides={"valuation_multiple": 11}, scenario="base", manual_price=None)["result"]["base"] == pytest.approx(2.97)
    assert calculate(build_batch_artifacts()["SFI"].model_dump(mode="json"), overrides={"valuation_multiple": 0.2}, scenario="base", manual_price=None)["result"]["base"] == pytest.approx(0.003028755)


def test_deterministic_twins_parent_preservation_and_activation_lock(tmp_path):
    before = tree(ACTIVE)
    first, second = tmp_path / "first", tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second) and tree(ACTIVE) == before
    catalog = load_pointer(first)
    assert len(catalog.entries) == 168
    assert sum(entry.availability_type == "not_available" for entry in catalog.entries) == 2
    parent = ACTIVE / PARENT_CATALOG_VERSION
    for entry in json.loads((parent / "manifest.json").read_text())["entries"]:
        ticker = entry["ticker"]
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (parent / "artifacts" / f"{ticker}.json").read_bytes()
    assert catalog.manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    isolated_serving = tmp_path / "isolated-serving"
    isolated_serving.mkdir()
    shutil.copytree(parent, isolated_serving / PARENT_CATALOG_VERSION)
    (isolated_serving / "active.json").write_text(json.dumps({"schema_version": "FINSIGHT-PSE-VALUATION-POINTER-1.0", "status": "active", "catalog_version": PARENT_CATALOG_VERSION, "catalog_path": PARENT_CATALOG_VERSION, "manifest_sha256": hashlib.sha256((parent / "manifest.json").read_bytes()).hexdigest()}))
    checks = preflight(first, isolated_serving)
    assert checks["active_before"] == PARENT_CATALOG_VERSION
    assert checks["ready_for_separate_activation"] is True
    activated = activate(first, isolated_serving)
    assert activated["active"] == CATALOG_VERSION and activated["count"] == 168
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
    assert listing["count"] == 168 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
    assert pse_valuations.get_pse_valuation_calculator("HOUSE", user)["can_calculate"] is False
