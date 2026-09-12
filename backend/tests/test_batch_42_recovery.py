import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_42 import BATCH_42_MANIFEST
from app.us_valuation.batch_42_recovery import build_batch_42_recovery_result
from app.us_valuation.calculator import calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
INITIAL = ROOT / "output/batch-42-history-run-g-20260907"
KW = {"source_root": ROOT / "output/batch-42-sec-source-packets-b-20260907", "structural_root": ROOT / "output/batch-42-structural-sources-20260907", "event_root": ROOT / "output/batch-42-event-review-20260907", "structural_cache_root": ROOT / "output/batch-42-structural-cache-20260907"}


def result(ticker):
    return build_batch_42_recovery_result(ticker=ticker, **KW)


def test_recovery_outcomes_remain_exactly_two_withheld():
    rows = {issuer.ticker: result(issuer.ticker) for issuer in BATCH_42_MANIFEST}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "not_available"} == {"EXE", "ALB"}
    assert all(row["availability_type"] == "conditional_estimate" for ticker, row in rows.items() if ticker not in {"EXE", "ALB"})
    assert rows["EXE"]["scenario_range"] == rows["ALB"]["scenario_range"] == {"low": None, "base": None, "high": None}


def test_exe_three_nonoverlapping_windows_reconcile_but_remain_diagnostic():
    exe = result("EXE")
    windows = exe["source_ledger"]["post_combination_nonoverlapping_windows"]
    assert [(row["label"], row["revenue"], row["operating_cash_flow"], row["capital_expenditures"], row["interest_expense"]) for row in windows] == [("H1 2025", 5_886_000_000, 2_418_000_000, 1_220_000_000, 119_000_000), ("H2 2025", 6_238_000_000, 2_157_000_000, 1_516_000_000, 116_000_000), ("H1 2026", 7_357_000_000, 3_498_000_000, 1_460_000_000, 102_000_000)]
    assert [row["cash_fcff"] for row in windows] == pytest.approx((1_292_855_828.2208588, 733_464_504.820333, 2_119_304_995.6178792))
    assert all(all(item["difference"] == 0 for item in exe["source_ledger"]["window_reconciliation"].values()) for _ in [0])
    diagnostic = exe["source_ledger"]["rejected_short_history_diagnostic"]
    assert [row["value_per_share"] for row in diagnostic["scenario_rows"]] == pytest.approx((2.1390267825978335, 47.40682432558402, 147.0899048140617))
    assert diagnostic["publication_allowed"] is False
    assert exe["source_ledger"]["recovery_attempt"]["through_cycle_history_gate_closed"] is False


def test_alb_conversion_and_positive_diagnostic_do_not_override_source_gate():
    alb = result("ALB")
    conversion = alb["source_ledger"]["mandatory_convertible_reconciliation"]
    assert conversion["current_common_shares"]["value"] == 118_005_057
    assert conversion["incremental_conversion_shares"]["value"] == 17_521_000
    assert conversion["incremental_share_compensation"]["value"] == 742_000
    assert conversion["fully_diluted_proxy"] == 136_268_057
    assert conversion["reported_h1_diluted_average"]["value"] == 136_170_000
    assert conversion["preferred_claim"]["value"] == 2_235_105_000
    assert conversion["preferred_claim_deducted"] is False
    schedule = alb["source_ledger"]["preferred_dividend_schedule"]
    assert schedule["quarterly_run_rate"] == 41_687_500
    diagnostic = alb["source_ledger"]["rejected_current_recovery_diagnostic"]
    assert [row["conditional_value_per_share"] for row in diagnostic["scenario_rows"]] == pytest.approx((0., 25.638977197429085, 81.14112414641455))
    assert [row["preferred_dividend_reserve"] for row in diagnostic["scenario_rows"]] == pytest.approx((125_062_500, 83_375_000, 41_687_500))
    assert [row["other_equity_claims"] for row in diagnostic["scenario_rows"]] == pytest.approx((510_050_500, 342_060_000, 300_372_500))
    assert all(row["other_equity_claims"] == pytest.approx(row["fixed_nci_and_operating_claims"] + row["preferred_dividend_reserve"]) for row in diagnostic["scenario_rows"])
    assert diagnostic["publication_allowed"] is False
    assert alb["source_ledger"]["recovery_attempt"]["positive_base_diagnostic_found"] is True
    assert alb["source_ledger"]["recovery_attempt"]["point_in_time_conversion_gate_closed"] is False


def test_attempted_public_outputs_remain_safe_and_uncalculable():
    from run_batch_42_recovery import _public

    for issuer in BATCH_42_MANIFEST:
        if issuer.ticker not in {"EXE", "ALB"}:
            continue
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        assert public["availability_type"] == "not_available"
        assert public["model_policy"]["primary"] == "fcff_dcf"
        assert public["scenario_range"]["base"] is None
        assert not calculator_view(public)["can_calculate"]
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "post_combination_nonoverlapping_windows", "mandatory_convertible_reconciliation"):
            assert key not in encoded


def test_recovery_runner_pins_initial_and_preserves_protected_state(tmp_path):
    from run_batch_42_recovery import run

    output = tmp_path / "candidate"
    report = run(initial_root=INITIAL, output_root=output, **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (2, 0, 8, 2, 8)
    assert report["attempted_tickers"] == ["EXE", "ALB"]
    assert report["recovered_to_conditional_tickers"] == []
    assert report["still_withheld_tickers"] == ["EXE", "ALB"]
    initial_report = json.loads((INITIAL / "batch-42-report.json").read_text())
    initial_cases = {row["ticker"]: row for row in initial_report["cases"]}
    for issuer in BATCH_42_MANIFEST:
        if issuer.ticker in {"EXE", "ALB"}:
            continue
        assert (output / "generated" / issuer.ticker / "valuation-private.json").read_bytes() == (INITIAL / "generated" / issuer.ticker / "valuation-private.json").read_bytes()
        assert (output / "staged-public" / f"{issuer.ticker}.json").read_bytes() == (INITIAL / "staged-public" / f"{issuer.ticker}.json").read_bytes()
        assert next(row for row in report["cases"] if row["ticker"] == issuer.ticker) == initial_cases[issuer.ticker]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
