import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.phase_b_batch_20 import FROZEN_BATCH_TICKERS, build_batch_artifacts, equity_per_share, load_batch_config, source_receipt
from app.routers import pse_valuations
from scripts.activate_pse_v2_phase_b_batch_20 import CONFIRMED_MANIFEST_SHA256, activate, preflight, write_pointer
from scripts.build_pse_v2_phase_b_batch_20 import CATALOG_VERSION, PARENT_CATALOG_VERSION, build


ROOT = Path(__file__).parents[2]
ACTIVE = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_parent_common_screens_reconcile_independently_and_preserve_limits():
    config = load_batch_config()
    artifacts = build_batch_artifacts(config)
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    for ticker in FROZEN_BATCH_TICKERS:
        issuer = config["issuers"][ticker]
        policy = config["policies"][issuer["policy"]]
        artifact = artifacts[ticker]
        parent_equity = Decimal(str(issuer["equity_value"])) * (1000 if issuer["equity_unit_scale"] == "thousands" else 1)
        common_shares = Decimal(str(issuer["shares_outstanding"]))
        independent_book = parent_equity / common_shares
        assert equity_per_share(issuer) == pytest.approx(float(independent_book))
        assert artifact.availability_type == "market_relative_only" and artifact.publication_state == "provisional"
        assert artifact.public_assumptions["reliability"] == "Low" and artifact.verify_artifact_hash()
        assert all(value is None for value in artifact.scenarios.values()) and artifact.price is None
        assert artifact.blocking_reasons and len(artifact.sources) == 2
        for name in ("low", "base", "high"):
            expected = round(float(independent_book * Decimal(str(policy["assumptions"][name]))), 9)
            assert artifact.market_relative["estimates"][name] == expected
        references, receipt = source_receipt(ticker, config)
        assert hashlib.sha256(receipt).hexdigest() == references[0]["sha256"]
        assert all(reference["sha256"] == references[0]["sha256"] for reference in references)
        assert calculator_view(artifact.model_dump(mode="json"))["can_calculate"] is True
    assert equity_per_share(config["issuers"]["HI"]) < config["issuers"]["HI"]["reported_bvps"]
    assert equity_per_share(config["issuers"]["MACAY"]) < config["issuers"]["MACAY"]["reported_bvps"]
    assert equity_per_share(config["issuers"]["TOP"]) < config["issuers"]["TOP"]["reported_bvps"]
    assert "ISIN blank" in artifacts["TOP"].warnings[-1]
    result = calculate(artifacts["TOP"].model_dump(mode="json"), overrides={"valuation_multiple": 0.6}, scenario="base", manual_price=None)
    assert result["result"]["base"] == pytest.approx(float(Decimal(3210994963) / Decimal(10742193000) * Decimal("0.6")))


def test_invalid_facts_and_unreviewed_policy_are_rejected(tmp_path):
    config = load_batch_config()
    path = tmp_path / "invalid.json"
    bad = json.loads(json.dumps(config))
    bad["issuers"]["HI"]["shares_outstanding"] = 0
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="common-equity bridge"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["MACAY"]["equity_basis"] = "total"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="parent-equity scope"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["REDC"]["share_as_of"] = "2026-09-26"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="dated facts"):
        load_batch_config(path)
    bad = json.loads(json.dumps(config))
    bad["issuers"]["MBC"]["policy"] = "unreviewed"
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="unreviewed P/B"):
        load_batch_config(path)


def test_exact_208_deterministic_twins_parent_preservation_and_staged_router(tmp_path, monkeypatch):
    active_pointer_before = (ACTIVE / "active.json").read_bytes()
    parent_manifest_before = (ACTIVE / PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    first, second = tmp_path / "first", tmp_path / "second"
    catalog_root = build(first)
    build(second)
    assert tree(first) == tree(second)
    assert (ACTIVE / "active.json").read_bytes() == active_pointer_before
    assert (ACTIVE / PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_manifest_before
    catalog = load_pointer(first)
    assert catalog.version == CATALOG_VERSION and catalog.status == "staged" and len(catalog.entries) == 208
    assert sum(entry.availability_type == "intrinsic_valuation" for entry in catalog.entries) == 34
    assert sum(entry.availability_type == "market_relative_only" for entry in catalog.entries) == 169
    assert {entry.ticker for entry in catalog.entries if entry.publication_state == "blocked"} == {"CDC", "HOUSE", "IS", "PAX", "PRIM"}
    parent = json.loads(parent_manifest_before)
    for entry in parent["entries"]:
        ticker = entry["ticker"]
        assert (catalog_root / "artifacts" / f"{ticker}.json").read_bytes() == (ACTIVE / PARENT_CATALOG_VERSION / "artifacts" / f"{ticker}.json").read_bytes()
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", first)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["count"] == 208 and listing["catalog_status"] == "staged"
    assert {item["ticker"] for item in listing["items"]} == {entry.ticker for entry in catalog.entries}
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, user)["can_calculate"] is True


def test_confirmed_preflight_and_isolated_activation_only(tmp_path):
    active_pointer_before = (ACTIVE / "active.json").read_bytes()
    parent_manifest_before = (ACTIVE / PARENT_CATALOG_VERSION / "manifest.json").read_bytes()
    candidate_root = tmp_path / "candidate"
    candidate_catalog = build(candidate_root)
    assert hashlib.sha256((candidate_catalog / "manifest.json").read_bytes()).hexdigest() == CONFIRMED_MANIFEST_SHA256
    isolated = tmp_path / "isolated-serving"
    isolated.mkdir()
    shutil.copytree(ACTIVE / PARENT_CATALOG_VERSION, isolated / PARENT_CATALOG_VERSION)
    write_pointer(isolated / "active.json", {
        "schema_version": "FINSIGHT-PSE-VALUATION-POINTER-1.0",
        "status": "active",
        "catalog_version": PARENT_CATALOG_VERSION,
        "catalog_path": PARENT_CATALOG_VERSION,
        "manifest_sha256": hashlib.sha256(parent_manifest_before).hexdigest(),
    })
    checks = preflight(candidate_root, isolated)
    assert checks["active_before"] == PARENT_CATALOG_VERSION
    assert checks["ready_for_separate_activation"] is True
    result = activate(candidate_root, isolated)
    assert result["active"] == CATALOG_VERSION and result["count"] == 208
    assert load_pointer(isolated, "active.json").manifest_sha256 == CONFIRMED_MANIFEST_SHA256
    assert tree(isolated / PARENT_CATALOG_VERSION) == tree(ACTIVE / PARENT_CATALOG_VERSION)
    assert tree(isolated / CATALOG_VERSION) == tree(candidate_catalog)
    assert (ACTIVE / "active.json").read_bytes() == active_pointer_before
    assert (ACTIVE / PARENT_CATALOG_VERSION / "manifest.json").read_bytes() == parent_manifest_before
    assert load_pointer(ACTIVE, "active.json").version == "PSE-V2-PHASE-B-B28-2026-09-26-1.0"
