from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_16 import BATCH_16_MANIFEST, BATCH_16_TICKERS
from app.us_valuation.batch_16_history import build_batch_16_history_result
from app.us_valuation.batch_16_whole_repair import (
    LEGAL_TAIL_TICKERS,
    REPAIRED_CONDITIONAL_TICKERS,
    REPAIRED_PASS_TICKERS,
    build_batch_16_whole_repair_result,
)
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-16-sec-source-packets-20260830"
STRUCTURAL = ROOT / "output/batch-16-structural-sources-20260830"
EVENT = ROOT / "output/batch-16-event-sources-20260830"
INITIAL = ROOT / "output/batch-16-history/final-c"


def _result(ticker: str) -> dict:
    return build_batch_16_whole_repair_result(
        ticker=ticker,
        source_root=SOURCE,
        structural_root=STRUCTURAL,
        event_root=EVENT,
    )


EXPECTED = {
    "A": (33.36726191087803, 65.7289157327362, 103.86497668215685),
    "DXCM": (16.46926419509219, 34.58806055838042, 69.88926817661473),
    "EW": (22.7162955873064, 42.40480316156332, 58.04798250543981),
    "CRL": (21.24746874359052, 69.79517035219583, 134.8738002012298),
    "ZBH": (36.93181676761808, 77.98514761336149, 123.17264994856492),
    "COR": (110.75812931953558, 205.761402735587, 375.7841075759678),
    "PODD": (20.9540316590138, 68.16473698232774, 133.3411455051541),
    "ELV": (121.67449290870627, 231.1974807113275, 419.5230998294124),
    "VEEV": (139.90063517477455, 202.836551844966, 285.9038118740371),
    "IQV": (58.07390592913907, 153.56041823748694, 230.18099488939302),
}


def test_whole_repair_has_exact_denominator_outcomes_and_ranges() -> None:
    rows = {ticker: _result(ticker) for ticker in BATCH_16_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(REPAIRED_PASS_TICKERS) == {"PODD", "VEEV", "IQV"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(REPAIRED_CONDITIONAL_TICKERS) == {"A", "DXCM", "EW", "CRL", "ZBH", "COR", "ELV"}
    assert all(row["availability_type"] != "not_available" for row in rows.values())
    for ticker, row in rows.items():
        assert tuple(row["scenario_range"][key] for key in ("low", "base", "high")) == pytest.approx(EXPECTED[ticker])
        assert 0 <= row["scenario_range"]["low"] <= row["scenario_range"]["base"] <= row["scenario_range"]["high"]
        assert row["scenario_range"]["base"] > 0
        assert row["history_reliability"]["label"] == "Low"


def test_unquantified_legal_tail_never_becomes_zero_or_a_claim_estimate() -> None:
    for ticker in LEGAL_TAIL_TICKERS:
        row = _result(ticker)
        policy = row["source_ledger"]["unquantified_legal_tail_policy"]
        assumptions = row["governed_assumptions"]
        assert policy["unquantified_loss_amount"] is None
        assert policy["zero_substitution_used"] is False
        assert policy["reported_vs_estimated"] == "unavailable_not_substituted"
        assert assumptions["unquantified_legal_loss_amount"] is None
        assert assumptions["unquantified_legal_loss_assumed_zero"] is False
        assert row["availability_type"] == "conditional_estimate"
        assert row["history_reliability"]["model_cap"] == "Low"
        assert "outside the valuation range" in row["warning"]


def test_recorded_claims_and_zbh_interest_are_included_once() -> None:
    assert _result("DXCM")["scenario_rows"][1]["other_equity_claims"] == 0.0
    assert _result("EW")["scenario_rows"][1]["other_equity_claims"] == 233_800_000.0
    assert _result("CRL")["scenario_rows"][1]["other_equity_claims"] == 93_891_000.0
    assert _result("ZBH")["scenario_rows"][1]["other_equity_claims"] == 391_200_000.0
    assert _result("COR")["scenario_rows"][1]["other_equity_claims"] == 4_388_133_000.0
    zbh = _result("ZBH")
    assert zbh["reported_inputs"]["ttm_interest"] == -289_000_000.0
    assert {source["concept"] for source in zbh["source_ledger"]["flow_sources"]["interest_expense"]["sources"]} == {"InterestIncomeExpenseNet"}
    ew = _result("EW")
    assert ew["reported_inputs"]["ttm_interest"] is None
    assert ew["reported_inputs"]["interest_expense_used"] == 20_400_000.0
    assert ew["reported_inputs"]["interest_period_status"] == "latest_fiscal_year_carried_as_estimate"
    assert ew["governed_assumptions"]["autus_contingent_consideration_range"] == (132_500_000.0, 70_000_000.0, 7_500_000.0)
    assert ew["governed_assumptions"]["autus_contingent_consideration_base_status"] == "finsight_arithmetic_midpoint_estimate"
    assert ew["source_ledger"]["ew_repair_trace"]["medical_device_company_equity_used_as_autus_fact"] is False


def test_podd_pass_uses_reported_assessment_without_zero_substitution() -> None:
    podd = _result("PODD")
    assessment = podd["source_ledger"]["claim_publication_assessment"]
    assert podd["availability_type"] == "available"
    assert assessment["reported_loss_probability"] == "not probable"
    assert assessment["reported_accrual_usd"] == 0.0
    assert assessment["ultimate_loss_estimate"] is None
    assert assessment["zero_substitution_used"] is False
    assert "not expected to have a material adverse effect" in assessment["reported_aggregate_materiality_assessment"]


def test_existing_a_veev_iqv_values_remain_exact() -> None:
    for ticker in ("A", "VEEV", "IQV"):
        initial = build_batch_16_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT)
        repaired = _result(ticker)
        assert repaired["scenario_range"] == initial["scenario_range"]
        assert repaired["availability_type"] == initial["availability_type"]


def test_whole_repair_public_artifacts_are_safe_and_calculable() -> None:
    from run_batch_16_whole_repair import _public

    for issuer in BATCH_16_MANIFEST:
        row = _result(issuer.ticker)
        public = _public(issuer, row)
        raw = json.dumps(public)
        assert public["availability_type"] == row["availability_type"]
        assert public["scenario_range"]["base"] == row["scenario_range"]["base"]
        assert all(key not in raw for key in ("source_ledger", "model_trace", "reported_inputs", "unquantified_loss_amount"))
        view = calculator_view(public)
        assert view["can_calculate"] is True
        assert view["model_family"] == ("equity_earnings" if issuer.ticker == "ELV" else "operating")
        assert calculate(public, overrides={}, manual_price=None)["result"] == row["scenario_range"]


def test_whole_repair_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_16_whole_repair import run

    report = run(initial_root=INITIAL, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT, output_root=tmp_path / "whole")
    assert report["attempted_count"] == 10
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (3, 7, 0, 10)
    assert report["newly_numeric_tickers"] == ["DXCM", "EW", "CRL", "ZBH", "COR", "ELV"]
    assert report["upgraded_to_pass_tickers"] == ["PODD"]
    assert report["automatic_recovery_attempt_reset"] is False
    assert report["prior_recovery_evidence_preserved"] is True
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed_during_staging"] is False
    assert report["withheld_register_changed_during_staging"] is False
