from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from statistics import median

import pytest

from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.models.fcff import fcff_valuation
from app.pse_valuation.phase_b_batch_02 import (
    FROZEN_BATCH_TICKERS,
    INTRINSIC_TICKERS,
    RELATIVE_TICKERS,
    build_batch_artifacts,
    load_batch_config,
    source_receipt,
)
from app.routers import pse_valuations
from scripts.build_pse_v2_phase_b_batch_02 import PARENT_CATALOG_VERSION, build
from scripts import activate_pse_v2_phase_b_batch_02 as activation


ROOT = Path(__file__).parents[2]
ACTIVE_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_batch_02_membership_and_routes_are_exact() -> None:
    assert FROZEN_BATCH_TICKERS == (
        "URC", "CNPF", "MONDE", "JFC", "DNL", "PGOLD", "RRHI", "WLCON", "SEVN", "SSI"
    )
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    assert {ticker for ticker, row in artifacts.items() if row.availability_type == "intrinsic_valuation"} == set(INTRINSIC_TICKERS)
    assert {ticker for ticker, row in artifacts.items() if row.availability_type == "market_relative_only"} == set(RELATIVE_TICKERS)
    assert all(row.publication_state == "provisional" for row in artifacts.values())


def test_batch_02_rejects_membership_drift(tmp_path: Path) -> None:
    config = load_batch_config()
    config["frozen_tickers"] = [*config["frozen_tickers"], "EXTRA"]
    path = tmp_path / "drifted.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="confirmed frozen set"):
        load_batch_config(path)


def test_intrinsic_normalization_and_lease_bridges_reconcile() -> None:
    config = load_batch_config()
    for ticker in INTRINSIC_TICKERS:
        facts = config["issuers"][ticker]["facts"]
        observations = [
            facts["operating_cash_flow_php_millions"][year]
            - facts["capital_expenditures_php_millions"][year]
            for year in ("2023", "2024", "2025")
        ]
        assert facts["normalized_fcff_proxy_php_millions"] == pytest.approx(median(observations))
        assert facts["debt_includes_lease_liabilities"] is True
        assert facts["shares_millions"] > 0


def test_reviewed_fact_receipts_are_hash_bound() -> None:
    config = load_batch_config()
    for ticker in FROZEN_BATCH_TICKERS:
        reference, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == reference["sha256"]
        assert reference["url"].startswith("https://")
        assert b"not a redistributed copy" in raw


def test_urc_base_reconciles_with_independent_fcff_call() -> None:
    config = load_batch_config()
    artifact = build_batch_artifacts(config)["URC"]
    assumptions = artifact.public_assumptions["scenario_assumptions"]["base"]
    bridge = artifact.public_assumptions["capital_bridge"]
    normalized = artifact.public_assumptions["normalized_fcff_proxy_php_millions"]
    starting_nopat = normalized / (1 - assumptions["growth_rate"] / assumptions["roic"])
    result = fcff_valuation(
        starting_nopat=starting_nopat,
        forecast_years=5,
        cash=bridge["cash_php_millions"],
        debt=bridge["debt_php_millions"],
        preferred_claims=bridge["preferred_claims_php_millions"],
        minority_value=bridge["minority_value_php_millions"],
        other_claims=bridge["other_claims_php_millions"],
        nonoperating_assets=bridge["nonoperating_assets_php_millions"],
        shares_outstanding=bridge["shares_millions"],
        **assumptions,
    )
    assert artifact.scenarios["base"].value_per_share == pytest.approx(result["value_per_share"])


def test_batch_02_values_are_exact_and_relative_results_remain_separate() -> None:
    artifacts = build_batch_artifacts()
    expected_base = {
        "URC": 21.556249836915885,
        "CNPF": 18.54319014508341,
        "MONDE": 6.454718620301496,
        "JFC": 157.42876710686852,
        "DNL": 3.5999999999999996,
        "PGOLD": 33.51729421683522,
        "RRHI": 42.24903793403655,
        "WLCON": 7.808708650465419,
        "SEVN": 54.12015904970705,
        "SSI": 3.2,
    }
    for ticker, expected in expected_base.items():
        artifact = artifacts[ticker]
        if ticker in INTRINSIC_TICKERS:
            assert artifact.scenarios["base"].value_per_share == pytest.approx(expected)
            assert artifact.market_relative is None
        else:
            assert artifact.market_relative["estimates"]["base"] == pytest.approx(expected)
            assert all(value is None for value in artifact.scenarios.values())
            assert artifact.blocking_reasons


def test_batch_02_calculators_use_each_issuers_own_bridge() -> None:
    artifacts = build_batch_artifacts()
    for ticker in FROZEN_BATCH_TICKERS:
        artifact = artifacts[ticker].model_dump(mode="json")
        view = calculator_view(artifact)
        result = calculate(artifact, overrides={}, scenario="base", manual_price=None)
        expected = (
            artifact["scenarios"]["base"]["value_per_share"]
            if ticker in INTRINSIC_TICKERS
            else artifact["market_relative"]["estimates"]["base"]
        )
        assert view["baseline_result"]["base"] == pytest.approx(expected)
        assert result["result"]["base"] == pytest.approx(expected)
    urc_bridge = artifacts["URC"].public_assumptions["capital_bridge"]
    cnpf_bridge = artifacts["CNPF"].public_assumptions["capital_bridge"]
    assert urc_bridge["shares_millions"] != cnpf_bridge["shares_millions"]
    assert urc_bridge["debt_php_millions"] != cnpf_bridge["debt_php_millions"]


def test_cumulative_28_candidate_twins_preserve_active_18(tmp_path: Path) -> None:
    active_before = tree(ACTIVE_ROOT)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_catalog = build(first)
    second_catalog = build(second)
    assert tree(first) == tree(second)
    assert tree(ACTIVE_ROOT) == active_before
    candidate = load_pointer(first)
    assert candidate.status == "staged"
    assert len(candidate.entries) == 28

    parent_catalog = ACTIVE_ROOT / PARENT_CATALOG_VERSION
    parent_manifest = json.loads((parent_catalog / "manifest.json").read_text())
    for row in parent_manifest["entries"]:
        ticker = row["ticker"]
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (
            parent_catalog / "artifacts" / f"{ticker}.json"
        ).read_bytes()


def test_staged_candidate_router_has_exact_28_record_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["catalog_status"] == "staged"
    assert listing["count"] == 28
    assert [row["ticker"] for row in listing["items"]] == sorted(
        [row.stem for row in (catalog_root / "artifacts").glob("*.json")]
    )
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
        view = pse_valuations.get_pse_valuation_calculator(ticker, user)
        assert view["can_calculate"] is True


def test_confirmed_batch_02_activation_preserves_batch_01_rollback(
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
    assert result["artifact_count"] == 28
    assert previous_manifest.is_file()
    assert load_pointer(serving_root, "active.json").status == "active"
