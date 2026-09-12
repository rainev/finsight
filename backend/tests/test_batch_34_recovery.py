from pathlib import Path
import json
import sys

from app.us_valuation.batch_34 import BATCH_34_TICKERS
from app.us_valuation.batch_34_recovery import BRO_PREFERRED_ABSENCE, CAPITAL_EVIDENCE, IMPLEMENTED_REPAIRS, RECOVERED_PASS_TICKERS, RECOVERY_ATTEMPT, RECOVERY_PLAN, build_batch_34_recovery_result


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-34-sec-source-packets-20260903"
STRUCTURAL = ROOT / "output/batch-34-structural-sources-20260903"
EVENTS = ROOT / "output/batch-34-event-sources-20260903"
INITIAL = ROOT / "output/batch-34-history-run-i-20260903"


def result(ticker):
    return build_batch_34_recovery_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS)


def test_single_attempt_processes_all_ten_with_only_source_bounded_promotions():
    rows = {ticker: result(ticker) for ticker in BATCH_34_TICKERS}
    assert len(rows) == 10
    assert rows["USB"]["availability_type"] == "available"
    assert rows["BRO"]["availability_type"] == "conditional_estimate"
    assert RECOVERED_PASS_TICKERS == {"USB"}
    assert all(row["availability_type"] == "conditional_estimate" for ticker, row in rows.items() if ticker != "USB")
    assert all(row["source_ledger"]["recovery_attempt"]["attempt_number"] == RECOVERY_ATTEMPT == 1 for row in rows.values())
    assert set(RECOVERY_PLAN) == set(BATCH_34_TICKERS)


def test_recovery_keeps_values_and_adds_release_conditions():
    for ticker in BATCH_34_TICKERS:
        row = result(ticker)
        attempt = row["source_ledger"]["recovery_attempt"]
        assert attempt["recovery_outcome"] == ("pass" if ticker in RECOVERED_PASS_TICKERS else "conditional_numeric_low")
        assert attempt["repair_tested"] == RECOVERY_PLAN[ticker][0]
        assert attempt["repair_status"] == ("implemented" if ticker in IMPLEMENTED_REPAIRS else "assessed_pending")
        assert attempt["release_condition"] == RECOVERY_PLAN[ticker][1]
        assert row["governed_assumptions"]["recovery_release_condition"] == RECOVERY_PLAN[ticker][1]
        assert 0 < row["scenario_range"]["low"] <= row["scenario_range"]["base"] <= row["scenario_range"]["high"]


def test_exact_dimensional_preferred_claims_replace_estimates():
    ntrs = result("NTRS")
    stt = result("STT")
    assert ntrs["governed_assumptions"]["preferred_claim_range"] == (884_900_000.0,) * 3
    assert stt["governed_assumptions"]["preferred_claim_range"] == (4_059_000_000.0,) * 3
    assert stt["reported_inputs"]["ending_total_equity"] == 28_763_000_000.0
    assert ntrs["governed_assumptions"]["beginning_preferred_claim_range"] == (884_900_000.0,) * 3
    assert stt["governed_assumptions"]["beginning_preferred_claim_range"] == (3_559_000_000.0,) * 3
    assert any(row.get("value") == 493_500_000.0 for row in ntrs["source_ledger"]["preferred_context"])
    assert any(row.get("value") == 1_481_000_000.0 for row in stt["source_ledger"]["preferred_context"])
    assert any(row.get("accession") == "0001193125-26-346938" for row in stt["source_ledger"]["preferred_context"])
    assert sum(row.get("accession") == "0001193125-26-346938" for row in stt["source_ledger"]["preferred_context"]) == 1


def test_recovery_recomputes_reliability_and_roe_after_repricing():
    from app.us_valuation.reliability import relative_movement
    for ticker in ("BRO", "NTRS", "STT"):
        row = result(ticker)
        low, base, high = (row["scenario_range"][key] for key in ("low", "base", "high"))
        assert row["history_reliability"]["scenario_movement_ratio"] == relative_movement(low=low, base=base, high=high)
        bridge = row["governed_assumptions"]["roe_scenario_bridge"]
        begin = row["governed_assumptions"]["beginning_common_equity"]
        end = row["governed_assumptions"]["ending_common_equity"]
        assert bridge["reported_ttm_roe"] == row["reported_inputs"]["ttm_common_earnings"] / ((begin + end) / 2)
    usb = result("USB")
    assert usb["history_reliability"]["model_cap"] == "High"
    assert usb["history_reliability"]["reasons"] == []
    assert usb["governed_assumptions"]["recovery_reason_codes"] == ()


def test_bro_acquisition_reinvestment_trace_keeps_it_conditional():
    row = result("BRO")
    trace = row["governed_assumptions"]["acquisition_reinvestment_evidence"]
    assert trace["acquisition_count_2025"] == 43
    assert trace["payments_to_acquire_businesses_2025"] == 7_854_000_000.0
    assert trace["payments_to_acquire_businesses_ttm"] == 7_723_000_000.0
    assert trace["reported_revenue_2025"] == 5_902_000_000.0
    assert trace["pro_forma_revenue_2025"] == 6_947_000_000.0
    assert row["availability_type"] == "conditional_estimate"
    assert "acquisition/reinvestment" in row["warning"]


def test_pass_source_receipt_is_runtime_verified():
    for ticker, document in (("USB", "usb-20260630.htm"), ("BRO", "bro-20260630.htm")):
        row = result(ticker)
        verification = row["source_ledger"]["recovery_attempt"]["runtime_source_verification"]
        cited = CAPITAL_EVIDENCE.get(ticker) or BRO_PREFERRED_ABSENCE
        assert verification["verified"] is True
        assert verification["primary_document"] == document
        assert verification["primary_document_sha256"] == cited["document_sha256"]


def test_public_recovery_artifacts_are_safe_and_calculator_matches():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_34_recovery import _public
    from app.us_valuation.batch_34 import BATCH_34_MANIFEST
    for issuer in BATCH_34_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        assert all(key not in encoded for key in ("source_ledger", "reported_inputs", "recovery_attempt", "residual_income_trace"))
        if issuer.ticker == "USB":
            assert public["model_policy"]["primary"] == "residual_income"
            assert set(public["models"]) == {"residual_income"}
            assert "bridge_quality" not in public
        if issuer.ticker == "BRO":
            assert public["model_policy"]["primary"] == "conditional_estimate"
            assert set(public["models"]) == {"conditional_estimate"}
        assert calculator_view(public)["can_calculate"]
        assert calculate(public, overrides={}, manual_price=None)["result"] == private["scenario_range"]


def test_recovery_runner_requires_initial_batch_and_preserves_bookkeeping(tmp_path):
    from run_batch_34_recovery import run
    report = run(initial_root=INITIAL, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS, output_root=tmp_path / "recovery")
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 1, 9, 0, 10)
    assert report["initial_report_sha256"] == "920a679e0ce7c6f30dbb3246afff29da1ad1008507b494cb1935a7fcdf1ae995"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
