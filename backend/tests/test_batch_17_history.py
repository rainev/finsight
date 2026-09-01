from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_17 import BATCH_17_MANIFEST, BATCH_17_TICKERS
from app.us_valuation.batch_17_history import CONDITIONAL_TICKERS, PASS_TICKERS, P, build_batch_17_history_result
from app.us_valuation.calculator import calculate, calculator_view

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-17-sec-source-packets-20260830"
STRUCTURAL = ROOT / "output/batch-17-structural-sources-20260830"
EVENT = ROOT / "output/batch-17-event-sources-20260830"


def _result(ticker: str) -> dict:
    return build_batch_17_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT)


EXPECTED = {
    "ABBV": (83.12948904671562, 172.7466150580554, 261.85421361578307),
    "ZTS": (35.4124526481204, 75.03281039834815, 110.96312303849146),
    "MDT": (30.522535700217027, 55.40862094808861, 79.209828771173),
    "MRNA": (0.0, 9.541822879173402, 12.722222222222221),
    "CI": (94.02430288374907, 191.14887489926159, 363.9692966170845),
    "STE": (65.13865858336227, 143.0612560383287, 222.40745398877885),
    "VTRS": (1.0515694574818177, 6.460233384435179, 16.714823257209577),
    "GEHC": (22.056504895440654, 42.634377717899056, 65.41411173940185),
    "KVUE": (3.5872062710860786, 8.77745252652278, 13.554543101274122),
    "SOLV": (0.0, 36.03575304491704, 76.33517623288786),
}


def test_batch_17_exact_outcomes_and_ranges() -> None:
    rows = {ticker: _result(ticker) for ticker in BATCH_17_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS) == {"ZTS", "STE"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == {"ABBV", "MDT", "MRNA", "CI", "VTRS", "GEHC", "KVUE", "SOLV"}
    assert all(row["availability_type"] != "not_available" for row in rows.values())
    for ticker, row in rows.items():
        values = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        assert values == pytest.approx(EXPECTED[ticker])
        assert 0.0 <= values[0] <= values[1] <= values[2] and values[1] > 0.0
        assert row["history_reliability"]["label"] == "Low"


def test_batch_17_operating_sensitivity_and_claim_directions() -> None:
    for ticker in P:
        row = _result(ticker)
        states = row["scenario_rows"]
        assert states[0]["wacc"] > states[1]["wacc"] > states[2]["wacc"]
        assert states[0]["growth"] <= states[1]["growth"] <= states[2]["growth"]
        assert states[0]["other_equity_claims"] >= states[1]["other_equity_claims"] >= states[2]["other_equity_claims"]
        assert states[0]["conditional_value_per_share"] <= states[1]["conditional_value_per_share"] <= states[2]["conditional_value_per_share"]


def test_batch_17_specialist_and_event_treatments_are_explicit() -> None:
    mrna = _result("MRNA")
    assert mrna["scenario_rows"][0]["raw_value_per_share"] < 0.0
    assert mrna["scenario_rows"][0]["conditional_value_per_share"] == 0.0
    assert mrna["governed_assumptions"]["pipeline_terminal_value"] == 0.0
    assert mrna["governed_assumptions"]["pipeline_terminal_value_status"] == "not_modeled_not_missing_value_substitution"
    assert mrna["reported_inputs"]["liquid_assets"] == 6_910_000_000.0
    ci = _result("CI")
    assert ci["governed_assumptions"]["route_is_equity_level"] is True
    assert ci["governed_assumptions"]["ev_debt_bridge_applied"] is False
    assert ci["source_ledger"]["event_sources"][0]["reported_terms"]["ifp_exit_effective"] == "2027-01-01"
    mdt = _result("MDT")
    assert mdt["source_ledger"]["event_sources"][0]["reported_terms"]["ownership_ratio"] == 0.9003
    assert mdt["source_ledger"]["event_sources"][0]["reported_terms"]["accounting_state"] == "consolidated"
    abbv = _result("ABBV")
    assert abbv["source_ledger"]["event_sources"][1]["reported_terms"]["aggregate_principal_usd"] == 10_000_000_000.0
    assert abbv["source_ledger"]["event_sources"][1]["reported_terms"]["cutoff_status"] == "signed_not_closed_not_issued"
    assert abbv["source_ledger"]["bridge_sources"][-1]["value"] == 27_495_000_000.0
    assert "not bridge-deducted again" in abbv["source_ledger"]["bridge_sources"][-1]["treatment"]
    gehc = _result("GEHC")
    assert gehc["reported_inputs"]["ttm_interest"] == 426_000_000.0
    assert {row["concept"] for row in gehc["source_ledger"]["flow_sources"]["interest_expense"]["sources"]} == {"InterestAndDebtExpense"}


def test_batch_17_recorded_claims_and_debt_are_counted_once() -> None:
    assert _result("ABBV")["scenario_rows"][1]["other_equity_claims"] == 1_747_000_000.0
    assert _result("MDT")["scenario_rows"][1]["other_equity_claims"] == 972_000_000.0
    assert _result("VTRS")["scenario_rows"][1]["other_equity_claims"] == 766_600_000.0
    assert "inside that $303M balance" in _result("VTRS")["source_ledger"]["bridge_reconciliation"]["other_equity_claim_formula"]
    assert _result("GEHC")["scenario_rows"][1]["debt_and_finance_leases"] == 10_217_000_000.0
    assert _result("KVUE")["scenario_rows"][1]["debt_and_finance_leases"] == 8_483_000_000.0
    assert _result("SOLV")["scenario_rows"][1]["debt_and_finance_leases"] == 5_292_000_000.0
    for ticker in ("ABBV", "VTRS", "GEHC", "KVUE", "SOLV"):
        assert _result(ticker)["governed_assumptions"]["unquantified_legal_loss_amount"] is None
        assert _result(ticker)["governed_assumptions"]["unquantified_legal_loss_assumed_zero"] is False


def test_batch_17_public_contract_is_safe_and_uses_correct_calculator_family() -> None:
    from run_batch_17_history import _public

    for issuer in BATCH_17_MANIFEST:
        row = _result(issuer.ticker)
        public = _public(issuer, row)
        raw = json.dumps(public)
        assert public["availability_type"] == row["availability_type"]
        assert public["scenario_range"]["base"] == row["scenario_range"]["base"]
        assert all(key not in raw for key in ("source_ledger", "model_trace", "reported_inputs", "unquantified_legal_loss_amount"))
        view = calculator_view(public)
        expected_family = "asset_runway" if issuer.ticker == "MRNA" else "equity_earnings" if issuer.ticker == "CI" else "operating"
        assert view["model_family"] == expected_family
        assert calculate(public, overrides={}, manual_price=None)["result"] == row["scenario_range"]
    mrna_public = _public(next(row for row in BATCH_17_MANIFEST if row.ticker == "MRNA"), _result("MRNA"))
    assert calculator_view(mrna_public)["editable_assumptions"][0]["label"] == "Cash-runway value factor"


def test_batch_17_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_17_history import run

    report = run(source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT, output_root=tmp_path / "batch17")
    assert report["attempted_count"] == 10
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (2, 8, 0, 10)
    assert report["pass_tickers"] == ["ZTS", "STE"]
    assert report["conditional_tickers"] == ["ABBV", "MDT", "MRNA", "CI", "VTRS", "GEHC", "KVUE", "SOLV"]
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed"] is False
    assert report["withheld_register_changed"] is False


def test_arelle_remains_outside_serving_imports() -> None:
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
