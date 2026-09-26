"""Internal-only refresh tests; all new source data here is synthetic test input."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pse_valuation.calculator import calculate, calculator_view
from app.pse_valuation.catalog import load_pointer
from app.pse_valuation.contract import PseValuationArtifact
from app.pse_valuation.internal_refresh import (
    BUNDLE_SCHEMA, FACT_SCOPES, RECEIPT_SCHEMA, RefreshHold, build_refresh_artifact,
    stage_internal_refresh,
)
from app.routers import pse_valuations
from app.security.jwt import sign_access_token


ROOT = Path(__file__).resolve().parents[2]
CATALOGS = ROOT / "backend/app/data/pse_valuation_catalogs"
USER = {"sub": 1, "role": "user"}


def _parent(ticker: str) -> PseValuationArtifact:
    catalog = load_pointer(CATALOGS, "active.json")
    return PseValuationArtifact.model_validate_json(catalog.verify_artifact(ticker).read_bytes())


def _receipt(ticker: str) -> dict:
    parent = _parent(ticker)
    model = parent.primary_model
    facts = {
        "AP": {
            "starting_fcff_php_millions": 38000.0,
            "cash_php_millions": 10000.0,
            "nonoperating_assets_php_millions": 500.0,
            "debt_php_millions": 100000.0,
            "preferred_claims_php_millions": 0.0,
            "minority_value_php_millions": 1000.0,
            "other_claims_php_millions": 0.0,
            "shares_millions": 7203.750741,
        },
        "BPI": {
            "parent_common_equity_php_millions": 476553.0,
            "prior_parent_common_equity_php_millions": 430469.0,
            "net_income_to_parent_php_millions": 66615.0,
            "shares_millions": 5283.794223,
        },
        "RCR": {
            "current_distribution_per_share": 0.4268,
            "shares_millions": 19548.803008,
            "quarterly_distributions_per_share": {"2025Q1": 0.1047, "2025Q2": 0.1049, "2025Q3": 0.1060, "2025Q4": 0.1112},
        },
        "RLC": {
            "parent_equity_php_millions": 175531.939468,
            "preferred_claims_php_millions": 0.0,
            "shares_millions": 4805.105288,
            "investment_property_carrying_value_php_millions": 100.0,
            "investment_property_fair_value_php_millions": 200.0,
            "property_by_owner": [
                {"name": "synthetic_part_owned", "carrying_value_php_millions": 40.0, "fair_value_php_millions": 90.0, "ownership": 0.6, "source_page": 1},
                {"name": "synthetic_wholly_owned", "carrying_value_php_millions": 60.0, "fair_value_php_millions": 110.0, "ownership": 1.0, "source_page": 1},
            ],
        },
    }[ticker]
    macro = {
        "version": "SYNTHETIC-TEST-MACRO",
        "benchmark_kind": "ten_year_government_bond",
        "benchmark_source": "synthetic unit-test observation",
        "benchmark_yield": 0.07,
        "observed_at": "2026-09-01",
        "reviewed_at": "2026-09-02",
        "reviewer": "synthetic-test",
    }
    return {
        "schema_version": RECEIPT_SCHEMA,
        "ticker": ticker,
        "trigger": "new_filing",
        "reviewer": "synthetic-test",
        "reviewed_at": "2026-09-03",
        "filing_period": "Synthetic 1H2026 test",
        "period_end": "2026-06-30",
        "filing_published_at": "2026-08-11",
        "source": {"label": "Synthetic test fact receipt", "identifier": "synthetic-test-only", "form": "17-Q", "source_page": 1},
        "facts": facts,
        "fact_provenance": {
            key: {
                "unit": "shares_millions" if key == "shares_millions" else "PHP_per_share" if key in {"current_distribution_per_share", "quarterly_distributions_per_share"} else "PHP_millions",
                "scope": FACT_SCOPES[key], "period_end": "2026-06-30", "source_page": 1,
            }
            for key in facts
        },
        "assumptions": {
            "policy_version": f"SYNTHETIC-{model}-1",
            "reviewer": "synthetic-test",
            "reviewed_at": "2026-09-03",
            "forecast_years": 5,
            "scenario_assumptions": parent.public_assumptions["scenario_assumptions"],
            **({"macro_snapshot": macro} if ticker != "RLC" else {}),
        },
    }


def _bundle(tmp_path: Path, ready: set[str], receipts: dict[str, dict] | None = None) -> Path:
    receipts = receipts or {}
    cases = {}
    for ticker in ("AP", "BPI", "RCR", "RLC"):
        if ticker not in ready:
            cases[ticker] = {"status": "hold", "reason": "No reviewed new-filing bridge supplied"}
            continue
        raw = (json.dumps(receipts.get(ticker, _receipt(ticker)), sort_keys=True) + "\n").encode()
        path = tmp_path / "receipts" / f"{ticker}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        cases[ticker] = {"status": "ready", "receipt_path": f"receipts/{ticker}.json", "receipt_sha256": hashlib.sha256(raw).hexdigest()}
    payload = {
        "schema_version": BUNDLE_SCHEMA,
        "catalog_version": "PSE-V2-REFRESH-SYNTHETIC-TEST-1.0",
        "valuation_date": "2026-09-26",
        "active_manifest_sha256": load_pointer(CATALOGS, "active.json").manifest_sha256,
        "cases": cases,
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("ticker", ["AP", "BPI", "RCR", "RLC"])
def test_four_models_rerun_from_reviewed_shape(ticker: str) -> None:
    receipt = _receipt(ticker)
    artifact = build_refresh_artifact(_parent(ticker), receipt, "a" * 64, date(2026, 9, 26))
    assert artifact.primary_model == _parent(ticker).primary_model
    assert artifact.publication_state == "provisional"
    assert artifact.verify_artifact_hash()
    assert artifact.scenarios["base"].value_per_share > 0
    view = calculator_view(artifact.model_dump(mode="json"))
    calculated = calculate(artifact.model_dump(mode="json"), overrides=view["scenario_presets"]["base"], scenario="base", manual_price=None)
    assert calculated["result"]["base"] == pytest.approx(artifact.scenarios["base"].value_per_share)


def test_stage_exact_catalog_and_real_staged_api_without_active_change(tmp_path: Path, monkeypatch) -> None:
    pointer_before = (CATALOGS / "active.json").read_bytes()
    bundle = _bundle(tmp_path, {"BPI"})
    output = tmp_path / "candidate-a"
    stage_internal_refresh(bundle, output, CATALOGS)
    staged = load_pointer(output)
    active = load_pointer(CATALOGS, "active.json")
    assert staged.status == "staged"
    assert len(staged.entries) == len(active.entries) == 282
    assert staged.entry_by_ticker["BPI"].artifact_sha256 != active.entry_by_ticker["BPI"].artifact_sha256
    for ticker in active.entry_by_ticker.keys() - {"BPI"}:
        assert staged.verify_artifact(ticker).read_bytes() == active.verify_artifact(ticker).read_bytes()
    report = json.loads((output / "refresh_report.json").read_text())
    assert report["activation_ready"] is False
    assert set(report["changed"]) == {"BPI"}
    assert set(report["holds"]) == {"AP", "RCR", "RLC"}
    monkeypatch.setattr(pse_valuations, "CATALOGS_ROOT", output)
    monkeypatch.setattr(pse_valuations, "POINTER_NAME", "staged.json")
    # Other API tests override auth globally; this request must exercise real auth.
    monkeypatch.setattr(app, "dependency_overrides", {})
    token = sign_access_token(1, "synthetic-test@example.invalid", "user")
    client = TestClient(app)
    assert client.get("/api/pse-valuations").status_code == 401
    response = client.get("/api/pse-valuations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200 and response.json()["count"] == 282
    response = client.get("/api/pse-valuations/BPI", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    detail = response.json()
    assert detail["catalog"]["catalog_status"] == "staged"
    assert detail["input_hash"] == PseValuationArtifact.model_validate_json(staged.verify_artifact("BPI").read_bytes()).input_hash
    assert (CATALOGS / "active.json").read_bytes() == pointer_before


def test_dependency_hold_and_deterministic_twins(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, {"RCR"})
    first = tmp_path / "candidate-a"
    second = tmp_path / "candidate-b"
    stage_internal_refresh(bundle, first, CATALOGS)
    stage_internal_refresh(bundle, second, CATALOGS)
    first_tree = {path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()}
    second_tree = {path.relative_to(second): path.read_bytes() for path in second.rglob("*") if path.is_file()}
    assert first_tree == second_tree
    report = json.loads((first / "refresh_report.json").read_text())
    assert report["dependency_holds"] == ["RLC"]


def test_missing_rcr_payout_or_stale_macro_holds_without_stage(tmp_path: Path) -> None:
    invalid = _receipt("RCR")
    invalid["facts"].pop("quarterly_distributions_per_share")
    bundle = _bundle(tmp_path, {"RCR"}, {"RCR": invalid})
    with pytest.raises(RefreshHold, match="no pilot issuer"):
        stage_internal_refresh(bundle, tmp_path / "candidate-a", CATALOGS)
    assert not (tmp_path / "candidate-a").exists()


def test_receipt_hash_tamper_fails_closed(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, {"AP"})
    path = tmp_path / "receipts/AP.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        stage_internal_refresh(bundle, tmp_path / "candidate-a", CATALOGS)
    assert not (tmp_path / "candidate-a").exists()


def test_all_four_stage_with_owned_property_bridge(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, {"AP", "BPI", "RCR", "RLC"})
    stage_internal_refresh(bundle, tmp_path / "candidate", CATALOGS)
    report = json.loads((tmp_path / "candidate/refresh_report.json").read_text())
    assert set(report["changed"]) == {"AP", "BPI", "RCR", "RLC"}
    assert report["dependency_holds"] == []
    assert report["holds"] == {}
    assert load_pointer(tmp_path / "candidate").entry_by_ticker["RLC"].availability_type == "intrinsic_valuation"


def test_material_change_is_flagged_not_approved(tmp_path: Path) -> None:
    receipt = _receipt("BPI")
    receipt["facts"]["shares_millions"] /= 2
    bundle = _bundle(tmp_path, {"BPI"}, {"BPI": receipt})
    output = tmp_path / "candidate"
    stage_internal_refresh(bundle, output, CATALOGS)
    report = json.loads((output / "refresh_report.json").read_text())
    assert report["changed"]["BPI"]["attribution_required"] is True
    assert report["activation_ready"] is False
    artifact = PseValuationArtifact.model_validate_json(load_pointer(output).verify_artifact("BPI").read_bytes())
    assert artifact.publication_state == "provisional"


def test_ap_old_period_cannot_claim_new_filing(tmp_path: Path) -> None:
    receipt = _receipt("AP")
    receipt["period_end"] = "2025-12-31"
    bundle = _bundle(tmp_path, {"AP", "BPI"}, {"AP": receipt})
    output = tmp_path / "candidate"
    stage_internal_refresh(bundle, output, CATALOGS)
    report = json.loads((output / "refresh_report.json").read_text())
    assert "not newer" in report["holds"]["AP"]
    assert set(report["changed"]) == {"BPI"}


@pytest.mark.parametrize("ticker,mutation,message", [
    ("BPI", "wrong_unit", "expected normalized unit"),
    ("RCR", "wrong_quarterly_unit", "expected normalized unit"),
    ("BPI", "wrong_scope", "expected consolidation scope"),
    ("BPI", "policy_rate", "ten-year benchmark"),
    ("RLC", "missing_owner", "does not reconcile"),
    ("RCR", "stale_macro", "stale benchmark"),
])
def test_critical_input_errors_hold_one_issuer(tmp_path: Path, ticker: str, mutation: str, message: str) -> None:
    receipt = _receipt(ticker)
    if mutation == "wrong_unit":
        receipt["fact_provenance"]["shares_millions"]["unit"] = "raw_shares"
    elif mutation == "wrong_quarterly_unit":
        receipt["fact_provenance"]["quarterly_distributions_per_share"]["unit"] = "PHP_millions"
    elif mutation == "wrong_scope":
        receipt["fact_provenance"]["parent_common_equity_php_millions"]["scope"] = "total"
    elif mutation == "policy_rate":
        receipt["assumptions"]["macro_snapshot"]["benchmark_kind"] = "policy_rate"
    elif mutation == "missing_owner":
        receipt["facts"]["property_by_owner"].pop()
    else:
        receipt["assumptions"]["macro_snapshot"]["observed_at"] = "2026-01-01"
    other = "AP" if ticker != "AP" else "BPI"
    bundle = _bundle(tmp_path, {ticker, other}, {ticker: receipt})
    output = tmp_path / "candidate"
    stage_internal_refresh(bundle, output, CATALOGS)
    report = json.loads((output / "refresh_report.json").read_text())
    assert message in report["holds"][ticker]
    assert (output / report["catalog_version"] / "artifacts" / f"{ticker}.json").read_bytes() == load_pointer(CATALOGS, "active.json").verify_artifact(ticker).read_bytes()


def test_cli_stages_isolated_catalog(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, {"BPI"})
    output = tmp_path / "cli-candidate"
    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts/stage_pse_intrinsic_refresh.py"), "--bundle", str(bundle), "--output", str(output)],
        env={**os.environ, "PYTHONPATH": str(ROOT / "backend")},
        capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, run.stderr
    assert str(output) in run.stdout
    assert load_pointer(output).status == "staged"
