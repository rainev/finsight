from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.models.distributions import distribution_valuation
from app.pse_valuation.models.residual_income import residual_income_valuation
from app.pse_valuation.phase_b_batch_01 import (
    FROZEN_BATCH_TICKERS,
    build_batch_artifacts,
    load_batch_config,
    source_receipt,
)
from app.routers import pse_valuations
from scripts.build_pse_v2_phase_b_batch_01 import build
from scripts import activate_pse_v2_phase_b_batch_01 as activation


ROOT = Path(__file__).parents[2]
ACTIVE_ROOT = ROOT / "backend/app/data/pse_valuation_catalogs"


def tree(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_batch_01_membership_is_exactly_the_confirmed_ten() -> None:
    assert FROZEN_BATCH_TICKERS == (
        "BPI",
        "MBT",
        "SECB",
        "CBC",
        "EW",
        "RCR",
        "MREIT",
        "CREIT",
        "FILRT",
        "DDMPR",
    )
    artifacts = build_batch_artifacts()
    assert tuple(artifacts) == FROZEN_BATCH_TICKERS
    assert sum(row.primary_model == "residual_income" for row in artifacts.values()) == 5
    assert sum(row.primary_model == "sustainable_distributions" for row in artifacts.values()) == 5
    assert all(row.availability_type == "intrinsic_valuation" for row in artifacts.values())
    assert all(row.publication_state == "provisional" for row in artifacts.values())


def test_batch_01_rejects_membership_drift(tmp_path: Path) -> None:
    config = load_batch_config()
    config["frozen_tickers"] = [*config["frozen_tickers"], "EXTRA"]
    path = tmp_path / "drifted.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="confirmed frozen set"):
        load_batch_config(path)


def test_reviewed_fact_receipts_are_hash_bound() -> None:
    config = load_batch_config()
    for ticker in FROZEN_BATCH_TICKERS:
        reference, raw = source_receipt(ticker, config)
        assert hashlib.sha256(raw).hexdigest() == reference["sha256"]
        assert reference["url"].startswith("https://")
        assert b"not a redistributed copy" in raw


def test_bpi_base_reconciles_to_independent_residual_income_call() -> None:
    config = load_batch_config()
    artifact = build_batch_artifacts(config)["BPI"]
    facts = config["issuers"]["BPI"]["facts"]
    assumptions = artifact.public_assumptions["scenario_assumptions"]["base"]
    equity = facts["parent_common_equity_php_millions"]
    shares = equity / facts["book_value_per_share"]
    independently_valued = residual_income_valuation(
        opening_common_equity=equity,
        shares_outstanding=shares,
        forecast_years=5,
        **assumptions,
    )
    assert artifact.scenarios["base"].value_per_share == pytest.approx(
        independently_valued["value_per_share"]
    )


def test_mreit_base_reconciles_to_independent_distribution_call() -> None:
    config = load_batch_config()
    artifact = build_batch_artifacts(config)["MREIT"]
    facts = config["issuers"]["MREIT"]["facts"]
    assumptions = artifact.public_assumptions["scenario_assumptions"]["base"]
    independently_valued = distribution_valuation(
        current_distribution_per_share=facts["distribution_per_share"],
        forecast_years=5,
        **assumptions,
    )
    assert artifact.scenarios["base"].value_per_share == pytest.approx(
        independently_valued["value_per_share"]
    )


def test_phase_b_intrinsic_calculators_reproduce_and_edit_selected_case() -> None:
    artifacts = build_batch_artifacts()
    for ticker in ("BPI", "MREIT"):
        artifact = artifacts[ticker].model_dump(mode="json")
        view = calculator_view(artifact)
        baseline = artifact["scenarios"]["base"]["value_per_share"]
        assert view["baseline_result"]["base"] == pytest.approx(baseline)
        result = calculate(
            artifact,
            overrides={},
            scenario="base",
            manual_price=None,
        )
        assert result["result"]["base"] == pytest.approx(baseline)

    bpi = artifacts["BPI"].model_dump(mode="json")
    bpi_edit = calculate(
        bpi,
        overrides={"cost_of_equity": 0.13},
        scenario="base",
        manual_price=None,
    )
    assert bpi_edit["result"]["base"] < bpi["scenarios"]["base"]["value_per_share"]

    mreit = artifacts["MREIT"].model_dump(mode="json")
    mreit_edit = calculate(
        mreit,
        overrides={"cost_of_equity": 0.12},
        scenario="base",
        manual_price=None,
    )
    assert mreit_edit["result"]["base"] < mreit["scenarios"]["base"]["value_per_share"]


def test_cumulative_candidate_twins_are_identical_and_active_is_unchanged(tmp_path: Path) -> None:
    active_before = tree(ACTIVE_ROOT)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_catalog = build(first)
    second_catalog = build(second)
    assert tree(first) == tree(second)
    assert tree(ACTIVE_ROOT) == active_before

    candidate = load_pointer(first)
    assert candidate.status == "staged"
    assert len(candidate.entries) == 18
    assert [entry.ticker for entry in candidate.entries] == sorted(
        ["AC", "ACR", "ALI", "AP", "AREIT", "BDO", "PERC", "SCC", *FROZEN_BATCH_TICKERS]
    )

    active_pointer = json.loads((ACTIVE_ROOT / "active.json").read_text())
    active_catalog = ACTIVE_ROOT / active_pointer["catalog_path"]
    for ticker in ("AC", "ACR", "ALI", "AP", "AREIT", "BDO", "PERC", "SCC"):
        assert (first_catalog / "artifacts" / f"{ticker}.json").read_bytes() == (
            active_catalog / "artifacts" / f"{ticker}.json"
        ).read_bytes()


def test_candidate_router_has_exact_18_record_parity_and_ten_calculators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog_root = build(tmp_path)
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", tmp_path)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    user = {"sub": 1, "role": "user"}
    listing = pse_valuations.list_pse_valuations(user)
    assert listing["catalog_status"] == "staged"
    assert listing["count"] == 18
    assert [row["ticker"] for row in listing["items"]] == sorted(
        ["AC", "ACR", "ALI", "AP", "AREIT", "BDO", "PERC", "SCC", *FROZEN_BATCH_TICKERS]
    )
    for ticker in FROZEN_BATCH_TICKERS:
        stored = json.loads((catalog_root / "artifacts" / f"{ticker}.json").read_text())
        served = pse_valuations.get_pse_valuation(ticker, user)
        assert {key: served[key] for key in stored} == stored
        view = pse_valuations.get_pse_valuation_calculator(ticker, user)
        assert view["baseline_result"]["base"] == pytest.approx(
            stored["scenarios"]["base"]["value_per_share"]
        )


def test_confirmed_candidate_activation_preserves_rollback_catalog(
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
    serving_root.mkdir(parents=True, exist_ok=True)
    (serving_root / "active.json").write_text(json.dumps(previous_pointer))
    (serving_root / "staged.json").write_text(json.dumps({**previous_pointer, "status": "staged"}))
    monkeypatch.setattr(activation, "SERVING_ROOT", serving_root)

    result = activation.activate(candidate_root)

    assert result["previous_catalog_version"] == previous_version
    assert result["active_catalog_version"] == activation.CATALOG_VERSION
    assert result["artifact_count"] == 18
    assert previous_manifest.is_file()
    assert load_pointer(serving_root, "active.json").status == "active"
