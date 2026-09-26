from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.models.distributions import distribution_valuation
from app.pse_valuation.phase_b_batch_04 import (
    FROZEN_BATCH_TICKERS,
    INTRINSIC_TICKERS,
    RELATIVE_TICKERS,
    build_batch_artifacts,
    load_batch_config,
    source_receipts,
)
from app.routers import pse_valuations
from scripts.build_pse_v2_phase_b_batch_04 import PARENT_CATALOG_VERSION, build
from scripts import activate_pse_v2_phase_b_batch_04 as activation


ROOT = Path(__file__).parents[2]
ACTIVE_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_batch_04_membership_and_routes_are_exact() -> None:
    assert FROZEN_BATCH_TICKERS == ("MER", "FGEN", "ACEN", "MWC", "SPC", "CREC", "ALTER", "ASLAG", "SPNEC", "MYNLD")
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    assert {ticker for ticker, row in artifacts.items() if row.availability_type == "intrinsic_valuation"} == set(INTRINSIC_TICKERS)
    assert {ticker for ticker, row in artifacts.items() if row.availability_type == "market_relative_only"} == set(RELATIVE_TICKERS)
    assert all(row.publication_state == "provisional" for row in artifacts.values())


def test_batch_04_rejects_membership_and_route_drift(tmp_path: Path) -> None:
    config = load_batch_config()
    config["frozen_tickers"] = [*config["frozen_tickers"], "EXTRA"]
    path = tmp_path / "membership.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="confirmed frozen set"):
        load_batch_config(path)

    config = load_batch_config()
    config["issuers"]["MER"]["availability"] = "market_relative_only"
    path = tmp_path / "route.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="route classification drift"):
        load_batch_config(path)


def test_batch_04_receipts_are_hash_bound_and_complete() -> None:
    config = load_batch_config()
    receipt_count = 0
    for ticker in FROZEN_BATCH_TICKERS:
        receipts = source_receipts(ticker, config)
        receipt_count += len(receipts)
        for reference, raw in receipts:
            assert hashlib.sha256(raw).hexdigest() == reference["sha256"]
            assert reference["url"].startswith("https://")
            assert b"not a redistributed copy" in raw
    assert receipt_count == 16


def test_batch_04_values_are_exact_and_relative_results_stay_separate() -> None:
    artifacts = build_batch_artifacts()
    expected = {
        "MER": (200.61637189455172, 298.3566172850372, 441.9236919232287),
        "FGEN": (15.678, 23.517, 31.356),
        "ACEN": (2.552, 3.509, 4.466),
        "MWC": (12.083097841919663, 17.025269694732497, 23.44202931005598),
        "SPC": (7.923421795810739, 10.907882969149753, 16.05410204439587),
        "CREC": (1.736, 2.387, 3.038),
        "ALTER": (0.46, 0.69, 0.92),
        "ASLAG": (1.54, 1.98, 2.42),
        "SPNEC": (0.97, 1.455, 1.94),
        "MYNLD": (6.347356681557339, 8.024114199072182, 9.824019273537669),
    }
    for ticker, values in expected.items():
        artifact = artifacts[ticker]
        if ticker in INTRINSIC_TICKERS:
            observed = tuple(artifact.scenarios[name].value_per_share for name in ("bear", "base", "bull"))
            assert observed == pytest.approx(values)
            assert artifact.market_relative is None
            assert not artifact.blocking_reasons
        else:
            estimates = artifact.market_relative["estimates"]
            assert (estimates["low"], estimates["base"], estimates["high"]) == pytest.approx(values)
            assert all(value is None for value in artifact.scenarios.values())
            assert artifact.blocking_reasons
        assert artifact.public_assumptions["reliability"] == "Low"


def test_mwc_base_reconciles_to_independent_finite_distribution_call() -> None:
    artifact = build_batch_artifacts()["MWC"]
    assumptions = artifact.public_assumptions["scenario_assumptions"]["base"]
    expected = distribution_valuation(
        current_distribution_per_share=artifact.public_assumptions["current_distribution_per_share"],
        forecast_years=20,
        finite_life_years=20,
        **assumptions,
    )
    assert expected["terminal_value"] == 0
    assert artifact.scenarios["base"].value_per_share == pytest.approx(expected["value_per_share"])


def test_batch_04_calculators_reproduce_and_move_in_expected_direction() -> None:
    artifacts = build_batch_artifacts()
    for ticker, artifact_model in artifacts.items():
        artifact = artifact_model.model_dump(mode="json")
        view = calculator_view(artifact)
        result = calculate(artifact, overrides={}, scenario="base", manual_price=None)
        expected = artifact["scenarios"]["base"]["value_per_share"] if ticker in INTRINSIC_TICKERS else artifact["market_relative"]["estimates"]["base"]
        assert view["baseline_result"]["base"] == pytest.approx(expected)
        assert result["result"]["base"] == pytest.approx(expected)
        if ticker in INTRINSIC_TICKERS:
            keys = [row["key"] for row in view["editable_assumptions"]]
            if ticker == "SPC":
                assert keys == ["explicit_growth", "cost_of_equity", "terminal_growth"]
            else:
                assert keys == ["explicit_growth", "cost_of_equity"]
            edited = calculate(artifact, overrides={"explicit_growth": view["defaults"]["explicit_growth"] + 0.01}, scenario="base", manual_price=None)
        else:
            assert [row["key"] for row in view["editable_assumptions"]] == ["valuation_multiple"]
            edited = calculate(artifact, overrides={"valuation_multiple": view["defaults"]["valuation_multiple"] + 0.1}, scenario="base", manual_price=None)
        assert edited["result"]["base"] > expected, ticker


def test_cumulative_48_candidate_twins_preserve_active_38(tmp_path: Path) -> None:
    active_before = tree(ACTIVE_ROOT)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_catalog = build(first)
    build(second)
    assert tree(first) == tree(second)
    assert tree(ACTIVE_ROOT) == active_before
    candidate = load_pointer(first)
    assert candidate.status == "staged"
    assert len(candidate.entries) == 48

    parent_catalog = ACTIVE_ROOT / PARENT_CATALOG_VERSION
    parent_manifest = json.loads((parent_catalog / "manifest.json").read_text())
    for row in parent_manifest["entries"]:
        ticker = row["ticker"]
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (parent_catalog / "artifacts" / f"{ticker}.json").read_bytes()


def test_staged_candidate_router_has_exact_48_record_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["catalog_status"] == "staged"
    assert listing["count"] == 48
    assert [row["ticker"] for row in listing["items"]] == sorted(row.stem for row in (catalog_root / "artifacts").glob("*.json"))
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
        assert pse_valuations.get_pse_valuation_calculator(ticker, user)["can_calculate"] is True


def test_confirmed_batch_04_activation_preserves_batch_03_rollback(
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
    assert result["artifact_count"] == 48
    assert previous_manifest.is_file()
    assert load_pointer(serving_root, "active.json").status == "active"
