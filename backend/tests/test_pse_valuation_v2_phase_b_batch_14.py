import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_14 import FROZEN_BATCH_TICKERS, build_batch_artifacts, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_14 import CONFIRMED_MANIFEST_SHA256, activate, preflight
from scripts.build_pse_v2_phase_b_batch_14 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build
from scripts.build_pse_v2_phase_b_batch_28 import CATALOG_VERSION as ACTIVE_CATALOG_VERSION


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_exact_set_values_source_periods_and_separation():
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    expected = {"STI": (1.76, 2.2, 2.64), "CEU": (11.92, 14.9, 17.88), "FEU": (643.44, 804.3, 965.16), "IPO": (7.44, 9.3, 11.16), "MEDIC": (0.255, 0.425, 0.595), "EURO": (0.88, 1.1, 1.32), "MRSGI": (1.92, 2.4, 2.88), "UPSON": (1.2, 1.5, 1.8), "FRUIT": (0.4, 0.5, 0.6), "KEEPR": (2.08, 2.6, 3.12)}
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        assert artifact.availability_type == "market_relative_only" and artifact.publication_state == "provisional"
        assert artifact.currency == "PHP" and all(value is None for value in artifact.scenarios.values())
        assert tuple(artifact.market_relative["estimates"][key] for key in ("low", "base", "high")) == pytest.approx(values)
        assert artifact.public_assumptions["reliability"] == "Low" and artifact.verify_artifact_hash()
        assert calculate(artifact.model_dump(mode="json"), overrides={}, scenario="base", manual_price=None)["result"]["base"] == pytest.approx(values[1])
    assert artifacts["STI"].filing_period == "2026-03-31"
    assert artifacts["CEU"].filing_period == "2026-02-28"
    assert artifacts["FEU"].filing_period == "2026-05-31"
    assert artifacts["MEDIC"].market_relative["metric"] == "price_to_book"
    assert artifacts["STI"].market_relative["metric"] == "price_to_earnings"
    assert "COSCO" in artifacts["KEEPR"].warnings[-1]


def test_receipts_and_invalid_eps_bridge(tmp_path):
    config = load_batch_config()
    for ticker in FROZEN_BATCH_TICKERS:
        refs, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == refs[0]["sha256"]
        assert all(ref["sha256"] == refs[0]["sha256"] for ref in refs)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["CEU"]["reported_eps"]["prior_ytd"]["value"] = 1.25
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="reconcile"):
        load_batch_config(path)


def test_deterministic_twins_parent_preservation_and_confirmed_activation_preflight(tmp_path):
    before = tree(ACTIVE)
    first, second = tmp_path / "first", tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second) and tree(ACTIVE) == before
    assert len(load_pointer(first).entries) == 148
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
    assert activate(first, isolated_serving)["count"] == 148
    assert load_pointer(isolated_serving, "active.json").version == CATALOG_VERSION
    assert (isolated_serving / PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == (parent / "manifest.json").read_bytes()
    assert load_pointer(ACTIVE, "active.json").version == ACTIVE_CATALOG_VERSION
    assert tree(ACTIVE / CATALOG_VERSION) == tree(first_catalog)


def test_staged_router_parity(tmp_path, monkeypatch):
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["count"] == 148 and listing["catalog_status"] == "staged"
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
