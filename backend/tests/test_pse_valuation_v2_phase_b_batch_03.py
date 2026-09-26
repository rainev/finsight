from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import CatalogIntegrityError, load_catalog, load_pointer
from app.pse_valuation.models.sotp import sotp_valuation
from app.pse_valuation.phase_b_batch_03 import (
    FROZEN_BATCH_TICKERS,
    INTRINSIC_TICKERS,
    RELATIVE_TICKERS,
    build_batch_artifacts,
    load_batch_config,
    source_receipt,
)
from app.routers import pse_valuations
from scripts.build_pse_v2_phase_b_batch_03 import PARENT_CATALOG_VERSION, build
from scripts import activate_pse_v2_phase_b_batch_03 as activation


ROOT = Path(__file__).parents[2]
ACTIVE_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_batch_03_membership_and_routes_are_exact() -> None:
    assert FROZEN_BATCH_TICKERS == (
        "SM", "AEV", "JGS", "GTCAP", "DMC", "SMPH", "RLC", "MEG", "FLI", "CLI"
    )
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    assert all(row.primary_model == "sotp" for row in artifacts.values())
    assert {ticker for ticker, row in artifacts.items() if row.availability_type == "intrinsic_valuation"} == set(INTRINSIC_TICKERS)
    assert {ticker for ticker, row in artifacts.items() if row.availability_type == "market_relative_only"} == set(RELATIVE_TICKERS)
    assert all(row.publication_state == "provisional" for row in artifacts.values())


def test_batch_03_rejects_membership_and_route_drift(tmp_path: Path) -> None:
    config = load_batch_config()
    config["frozen_tickers"] = [*config["frozen_tickers"], "EXTRA"]
    path = tmp_path / "membership.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="confirmed frozen set"):
        load_batch_config(path)

    config = load_batch_config()
    config["issuers"]["SM"]["availability"] = "intrinsic_valuation"
    path = tmp_path / "route.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="route classification drift"):
        load_batch_config(path)


def test_reported_nav_facts_and_receipts_are_hash_bound() -> None:
    config = load_batch_config()
    for ticker in FROZEN_BATCH_TICKERS:
        facts = config["issuers"][ticker]["facts"]
        assert facts["book_value_per_share"] > 0
        assert facts["parent_equity_php_millions"] > 0
        if ticker in RELATIVE_TICKERS:
            assert facts["intrinsic_blocker"]
        reference, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == reference["sha256"]
        assert reference["url"].startswith("https://")
        assert b"not a redistributed copy" in raw


def test_batch_03_values_are_exact_and_keep_relative_results_separate() -> None:
    artifacts = build_batch_artifacts()
    expected = {
        "SM": (515.07, 629.53, 743.99),
        "AEV": (23.5395, 31.386, 39.2325),
        "JGS": (16.7895, 22.386, 27.9825),
        "GTCAP": (609.4305, 812.574, 1015.7175),
        "DMC": (9.07, 11.3375, 13.605),
        "SMPH": (30.51643446938899, 41.68760898486752, 54.13548915925787),
        "RLC": (50.753333811152906, 61.81569315623288, 74.14232214075057),
        "MEG": (2.469, 3.7035, 4.938),
        "FLI": (5.4664039229961165, 6.527948871181909, 7.710813242017505),
        "CLI": (2.092, 2.8765, 3.661),
    }
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        if ticker in INTRINSIC_TICKERS:
            estimates = tuple(artifact.scenarios[name].value_per_share for name in ("bear", "base", "bull"))
            assert estimates == pytest.approx(values)
            assert artifact.market_relative is None
            assert not artifact.blocking_reasons
        else:
            estimates = artifact.market_relative["estimates"]
            assert (estimates["low"], estimates["base"], estimates["high"]) == pytest.approx(values)
            assert all(value is None for value in artifact.scenarios.values())
            assert artifact.blocking_reasons
        assert artifact.public_assumptions["reliability"] == "Low"


def test_rlc_base_reconciles_with_independent_rnav_call() -> None:
    artifact = build_batch_artifacts()["RLC"]
    bridge = artifact.public_assumptions["nav_bridge"]
    assumptions = artifact.public_assumptions["scenario_assumptions"]["base"]
    uplift = (
        bridge["investment_property_fair_value_php_millions"]
        - bridge["investment_property_carrying_value_php_millions"]
    ) * assumptions["uplift_realization"] * (1 - assumptions["tax_leakage"])
    result = sotp_valuation(
        components=[
            {"name": "reported_parent_equity", "equity_value": bridge["parent_equity_php_millions"], "ownership": 1.0},
            {"name": "after_tax_property_fair_value_uplift", "equity_value": uplift, "ownership": 1.0},
        ],
        shares_outstanding=bridge["shares_millions"],
        other_parent_claims=bridge["preferred_claims_php_millions"],
    )
    assert artifact.scenarios["base"].value_per_share == pytest.approx(result["value_per_share"])


def test_batch_03_calculators_reproduce_and_move_with_pb_multiple() -> None:
    artifacts = build_batch_artifacts()
    for ticker, artifact_model in artifacts.items():
        artifact = artifact_model.model_dump(mode="json")
        view = calculator_view(artifact)
        result = calculate(artifact, overrides={}, scenario="base", manual_price=None)
        expected = (
            artifact["scenarios"]["base"]["value_per_share"]
            if ticker in INTRINSIC_TICKERS
            else artifact["market_relative"]["estimates"]["base"]
        )
        assert view["baseline_result"]["base"] == pytest.approx(expected)
        assert result["result"]["base"] == pytest.approx(expected)
        if ticker in INTRINSIC_TICKERS:
            assert [row["key"] for row in view["editable_assumptions"]] == ["uplift_realization", "tax_leakage"]
            overrides = {"uplift_realization": view["defaults"]["uplift_realization"] + 0.1}
        else:
            assert [row["key"] for row in view["editable_assumptions"]] == ["valuation_multiple"]
            overrides = {"valuation_multiple": view["defaults"]["valuation_multiple"] + 0.1}
        edited = calculate(artifact, overrides=overrides, scenario="base", manual_price=None)
        assert edited["result"]["base"] > expected, ticker


def test_cumulative_38_candidate_twins_preserve_active_28(tmp_path: Path) -> None:
    active_before = tree(ACTIVE_ROOT)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second)
    assert tree(ACTIVE_ROOT) == active_before
    candidate = load_pointer(first)
    assert candidate.status == "staged"
    assert len(candidate.entries) == 38

    parent_catalog = ACTIVE_ROOT / PARENT_CATALOG_VERSION
    parent_manifest = json.loads((parent_catalog / "manifest.json").read_text())
    for row in parent_manifest["entries"]:
        ticker = row["ticker"]
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (
            parent_catalog / "artifacts" / f"{ticker}.json"
        ).read_bytes()


def test_staged_candidate_router_has_exact_38_record_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["catalog_status"] == "staged"
    assert listing["count"] == 38
    assert [row["ticker"] for row in listing["items"]] == sorted(
        [row.stem for row in (catalog_root / "artifacts").glob("*.json")]
    )
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
        view = pse_valuations.get_pse_valuation_calculator(ticker, user)
        assert view["can_calculate"] is True


def test_catalog_rejects_manifest_artifact_metadata_drift(tmp_path: Path) -> None:
    catalog_root = build(tmp_path)
    manifest_path = catalog_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    row = next(item for item in manifest["entries"] if item["ticker"] == "SM")
    row["primary_model"] = "fcff_dcf"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with pytest.raises(CatalogIntegrityError, match="metadata differs"):
        load_catalog(catalog_root)


def test_confirmed_batch_03_activation_preserves_batch_02_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_root = tmp_path / "candidate"
    build(candidate_root)
    serving_root = tmp_path / "serving"
    previous_version = activation.PREVIOUS_CATALOG_VERSION
    shutil.copytree(ACTIVE_ROOT / previous_version, serving_root / previous_version)
    previous_manifest = serving_root / previous_version / "manifest.json"
    previous_pointer = {
        "schema_version": "FINSIGHT-PSE-VALUATION-POINTER-1.0",
        "status": "active",
        "catalog_version": previous_version,
        "catalog_path": previous_version,
        "manifest_sha256": hashlib.sha256(previous_manifest.read_bytes()).hexdigest(),
    }
    (serving_root / "active.json").write_text(json.dumps(previous_pointer))
    (serving_root / "staged.json").write_text(json.dumps({**previous_pointer, "status": "staged"}))
    monkeypatch.setattr(activation, "SERVING_ROOT", serving_root)

    result = activation.activate(candidate_root)

    assert result["previous_catalog_version"] == previous_version
    assert result["active_catalog_version"] == activation.CATALOG_VERSION
    assert result["artifact_count"] == 38
    assert previous_manifest.is_file()
    assert load_pointer(serving_root, "active.json").status == "active"
