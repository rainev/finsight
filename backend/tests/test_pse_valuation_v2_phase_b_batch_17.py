import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_17 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_17 import CONFIRMED_MANIFEST_SHA256, activate, preflight, write_pointer
from scripts.build_pse_v2_phase_b_batch_17 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_exact_relative_values_status_and_source_periods():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    expected = {
        "SGP": (13.795, 19.313, 24.831), "VVT": (10.905, 15.267, 19.629),
        "PREIT": (0.475, 0.76, 1.045), "SHLPH": (5.874, 9.79, 13.706),
        "CHP": (0.285, 0.475, 0.665), "PHN": (7.015, 11.224, 15.433),
        "RCI": (2.295, 3.672, 5.049), "TFC": (30.0, 37.5, 45.0),
        "LBC": (5.003205016, 7.004487022, 9.005769028), "MRC": (0.2925, 0.468, 0.6435),
    }
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        assert artifact.availability_type == "market_relative_only" and artifact.publication_state == "provisional"
        assert artifact.currency == "PHP" and all(value is None for value in artifact.scenarios.values())
        assert tuple(artifact.market_relative["estimates"][key] for key in ("low", "base", "high")) == pytest.approx(values)
        assert artifact.public_assumptions["reliability"] == "Low" and artifact.verify_artifact_hash()
        view = calculator_view(artifact.model_dump(mode="json"))
        assert view["can_calculate"] is True and view["baseline_result"]["base"] == pytest.approx(values[1])
    assert artifacts["TFC"].filing_period == "2026-05-31"
    assert artifacts["PREIT"].primary_model == "sustainable_distributions"
    assert any("lease" in text.lower() for text in artifacts["PREIT"].warnings)
    assert any("listed shares" in text for text in artifacts["LBC"].warnings)


def test_independent_arithmetic_receipts_and_period_gates(tmp_path):
    config = load_batch_config()
    assert Decimal("3.52") + Decimal("2.81") - Decimal("2.58") == Decimal("3.75")
    lbc = (Decimal(14025956097) + Decimal(7220274354) - Decimal(6978435899)) / Decimal(1425865471)
    assert float(lbc) == pytest.approx(config["issuers"]["LBC"]["metric_value_per_share"])
    for ticker in FROZEN_BATCH_TICKERS:
        references, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == references[0]["sha256"]
        assert all(reference["sha256"] == references[0]["sha256"] for reference in references)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["TFC"]["reported_eps"]["prior_ytd"]["period_end"] = "2025-06-30"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="aligned"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["LBC"]["reported_shares"]["value"] = 0
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="share count"):
        load_batch_config(path)
    assert calculate(build_batch_artifacts()["TFC"].model_dump(mode="json"), overrides={"valuation_multiple": 11}, scenario="base", manual_price=None)["result"]["base"] == pytest.approx(41.25)


def test_deterministic_twins_parent_preservation_and_confirmed_preflight(tmp_path):
    before = tree(ACTIVE)
    first, second = tmp_path / "first", tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second) and tree(ACTIVE) == before
    catalog = load_pointer(first)
    assert len(catalog.entries) == 178
    assert sum(entry.availability_type == "intrinsic_valuation" for entry in catalog.entries) == 34
    assert sum(entry.availability_type == "market_relative_only" for entry in catalog.entries) == 142
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
    assert activated["active"] == CATALOG_VERSION and activated["count"] == 178
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
    assert listing["count"] == 178 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
    assert pse_valuations.get_pse_valuation_calculator("HOUSE", user)["can_calculate"] is False
