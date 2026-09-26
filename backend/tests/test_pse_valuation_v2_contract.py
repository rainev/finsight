from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.pse_valuation import CATALOG_VERSION
from app.pse_valuation.catalog import CatalogIntegrityError, load_pointer
from app.pse_valuation.contract import PseValuationArtifact, ScenarioValue, blocked_artifact
from app.pse_valuation.pipeline import PILOT_TICKERS, build_pilot_artifacts
from scripts.build_pse_v2_pilot import build
from scripts.load_pse_v2_pilot_evidence import _corpus_documents, _legacy_document


ROOT = Path(__file__).parents[2]


def source() -> dict:
    return {
        "document_id": "source-1",
        "label": "Reviewed filing",
        "sha256": "a" * 64,
    }


def test_blocked_contract_has_null_values_and_reason() -> None:
    artifact = blocked_artifact(
        ticker="TEST",
        issuer_name="Test Issuer",
        subsector="Test",
        primary_model="sotp",
        valuation_date=date(2026, 9, 21),
        sources=[source()],
        blocking_reasons=["Missing attributable component values."],
        input_snapshot={"ticker": "TEST"},
    )
    assert artifact.availability_type == "not_available"
    assert artifact.publication_state == "blocked"
    assert all(value is None for value in artifact.scenarios.values())
    assert artifact.verify_artifact_hash()


def test_blocked_contract_rejects_numeric_scenario() -> None:
    with pytest.raises(ValidationError):
        PseValuationArtifact(
            ticker="TEST",
            issuer={"issuer_id": "TEST", "name": "Test"},
            security={"security_id": "PSE:TEST:COMMON", "type": "ordinary_common"},
            subsector="Test",
            primary_model="sotp",
            valuation_date=date(2026, 9, 21),
            availability_type="not_available",
            publication_state="blocked",
            scenarios={
                "bear": ScenarioValue(value_per_share=1, common_equity_value=10),
                "base": None,
                "bull": None,
            },
            numerical_range={"low": None, "high": None},
            sources=[source()],
            blocking_reasons=["blocked"],
            input_hash="b" * 64,
        )


def test_phase_a_builder_preserves_intrinsic_and_market_relative_boundaries() -> None:
    artifacts = build_pilot_artifacts(ROOT)
    assert tuple(artifacts) == PILOT_TICKERS
    assert artifacts["AP"].availability_type == "intrinsic_valuation"
    assert artifacts["AP"].publication_state == "provisional"
    assert artifacts["AP"].scenarios["bear"].value_per_share < artifacts["AP"].scenarios["base"].value_per_share
    assert artifacts["AP"].scenarios["base"].value_per_share < artifacts["AP"].scenarios["bull"].value_per_share
    for ticker in set(PILOT_TICKERS) - {"AP"}:
        assert artifacts[ticker].availability_type == "market_relative_only"
        assert artifacts[ticker].publication_state == "provisional"
        assert artifacts[ticker].blocking_reasons
        assert all(value is None for value in artifacts[ticker].scenarios.values())
        assert artifacts[ticker].market_relative["estimates"]["base"] > 0


def test_market_relative_pilot_values_are_exact() -> None:
    artifacts = build_pilot_artifacts(ROOT)
    expected = {
        "AC": (518.16, 647.7, 777.24),
        "ACR": (1.071, 1.26, 1.449),
        "ALI": (32.4, 40.5, 48.6),
        "AREIT": (28.0, 32.0, 37.333333333333336),
        "BDO": (130.24, 162.8, 195.36),
        "PERC": (4.675, 5.5, 6.325),
        "SCC": (23.4855, 27.63, 31.7745),
    }
    for ticker, values in expected.items():
        estimates = artifacts[ticker].market_relative["estimates"]
        assert (estimates["low"], estimates["base"], estimates["high"]) == pytest.approx(values)


def test_ap_base_case_reconciles_with_independent_fcff_calculation() -> None:
    artifact = build_pilot_artifacts(ROOT)["AP"]
    assumptions = {
        "growth_rate": 0.035,
        "roic": 0.12,
        "wacc": 0.115,
        "terminal_growth": 0.03,
        "terminal_roic": 0.11,
    }
    normalized_fcff = 38_000.0
    nopat = normalized_fcff / (1 - assumptions["growth_rate"] / assumptions["roic"])
    present_value = 0.0
    for year in range(1, 6):
        nopat *= 1 + assumptions["growth_rate"]
        fcff = nopat * (1 - assumptions["growth_rate"] / assumptions["roic"])
        present_value += fcff / (1 + assumptions["wacc"]) ** year
    terminal_nopat = nopat * (1 + assumptions["terminal_growth"])
    terminal_fcff = terminal_nopat * (
        1 - assumptions["terminal_growth"] / assumptions["terminal_roic"]
    )
    terminal_value = terminal_fcff / (
        assumptions["wacc"] - assumptions["terminal_growth"]
    )
    enterprise = present_value + terminal_value / (1 + assumptions["wacc"]) ** 5
    equity = enterprise + 58_932.061 - 327_548.364
    expected_per_share = equity / 7_203.750741
    assert artifact.scenarios["base"].value_per_share == pytest.approx(expected_per_share)


def test_public_artifacts_exclude_private_fact_payloads() -> None:
    forbidden = {"raw_text", "reported_value", "financials", "private_result"}

    def visit(value):
        if isinstance(value, dict):
            assert not (forbidden & set(value))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str):
            assert "/Users/" not in value

    for path in (ROOT / "backend/app/data/pse_valuation_catalogs" / CATALOG_VERSION / "artifacts").glob("*.json"):
        visit(json.loads(path.read_text()))


def test_catalog_twins_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    build(first)
    build(second)
    first_files = {path.relative_to(first): path.read_bytes() for path in first.rglob("*.json")}
    second_files = {path.relative_to(second): path.read_bytes() for path in second.rglob("*.json")}
    assert first_files == second_files
    catalog = load_pointer(first)
    assert len(catalog.entries) == 8
    assert catalog.status == "staged"


def test_confirmed_catalog_can_be_selected_by_active_pointer(tmp_path: Path) -> None:
    build(tmp_path)
    pointer = json.loads((tmp_path / "staged.json").read_text())
    pointer["status"] = "active"
    (tmp_path / "active.json").write_text(json.dumps(pointer))
    catalog = load_pointer(tmp_path, "active.json")
    assert catalog.status == "active"
    assert len(catalog.entries) == 8


def test_catalog_detects_artifact_tampering(tmp_path: Path) -> None:
    build(tmp_path)
    pointer = json.loads((tmp_path / "staged.json").read_text())
    artifact = tmp_path / pointer["catalog_path"] / "artifacts" / "AP.json"
    artifact.write_text(artifact.read_text() + " ")
    with pytest.raises(CatalogIntegrityError, match="artifact hash mismatch"):
        load_pointer(tmp_path)


def test_all_local_pilot_sources_resolve_and_match_recorded_hashes() -> None:
    for ticker in ("AP", "SCC", "BDO", "AREIT", "ALI", "AC"):
        documents = _corpus_documents(ticker)
        assert documents
        assert all(path.is_file() and len(digest) == 64 for path, digest in documents)
    for ticker in ("ACR", "PERC"):
        path, digest = _legacy_document(ticker)
        assert path.is_file()
        assert len(digest) == 64
