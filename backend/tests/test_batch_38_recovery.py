from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_38 import BATCH_38_MANIFEST
from app.us_valuation.batch_38_recovery import build_batch_38_recovery_result
from app.us_valuation.calculator import calculate, calculator_view
from app.valuation.bank import residual_income_valuation


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-38-sec-source-packets-20260907"
STRUCTURAL = ROOT / "output/batch-38-structural-sources-20260907"
EVENTS = ROOT / "output/batch-38-event-review-20260907"
CACHE = ROOT / "output/batch-38-structural-cache-20260907"
INITIAL = ROOT / "output/batch-38-history-run-i-20260907"
KW = {"source_root": SOURCE, "structural_root": STRUCTURAL, "event_root": EVENTS, "structural_cache_root": CACHE}


def result(ticker):
    return build_batch_38_recovery_result(ticker=ticker, **KW)


def test_recovery_outcomes_are_exact():
    rows = {issuer.ticker: result(issuer.ticker) for issuer in BATCH_38_MANIFEST}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "not_available"} == {"GPN"}
    assert rows["CPAY"]["availability_type"] == "conditional_estimate"
    assert rows["CPAY"]["scenario_range"] == pytest.approx({"low": 40.11750250791505, "base": 65.42223238466619, "high": 90.9507793503895})


def test_gpn_favorable_bridge_still_fails_positive_base_gate():
    row = result("GPN")
    assert row["scenario_range"] == {"low": None, "base": None, "high": None}
    assert row["source_ledger"]["settlement_line_matching"]["settlement_line_of_credit"]["value"] == 1_136_764_000
    challenge = row["source_ledger"]["favorable_bridge_challenge"]
    assert challenge["base_still_negative"] is True
    assert [item["raw_value_per_share"] for item in challenge["scenario_rows"]] == pytest.approx((-50.4930416158, -37.8388599360, -21.9784832981))
    assert all(item["raw_value_per_share"] < 0 for item in challenge["scenario_rows"])
    q2 = row["source_ledger"]["q2_cash_earnings_diagnostic"]
    assert q2["publication_allowed"] is False
    assert q2["estimated_q2_capex"] == 248_500_000
    assert q2["annualized_cash_earnings"] == pytest.approx(3_621_686_734.0370235)
    assert [item["raw_value_per_share"] for item in q2["scenario_rows"]] == pytest.approx((-3.4163310848, 82.5058019442, 139.4982561754))
    assert "not publishable" in q2["why_rejected"]


def test_cpay_customer_funding_reconciles_without_becoming_free_cash():
    row = result("CPAY")
    funding = row["source_ledger"]["customer_funding_reconciliation"]
    assert funding["customer_deposits_current"]["value"] == 8_915_786_000
    assert funding["restricted_cash"]["value"] == 7_004_803_000
    assert funding["balance_sheet_movements"] == {"accounts_payable": 711_251_000, "accrued_expenses": -38_174_000, "customer_deposits": 797_220_000}
    assert funding["movement_total"] == 1_470_297_000
    assert funding["pooled_cash_flow_line"]["value"] == 1_570_343_000
    assert funding["residual"] == 100_046_000
    assert funding["recorded_ftc_charge"]["value"] == 100_000_000
    assert funding["used_as_free_cash"] is False


def test_cpay_parent_equity_history_and_scenarios_replay():
    row = result("CPAY")
    earnings = row["source_ledger"]["common_earnings_reconstruction"]
    assert [item["value"] for item in earnings["annual_history"]] == [981_890_000, 1_003_746_000, 1_068_346_000]
    assert earnings["ttm"] == 1_133_503_000
    assert row["reported_inputs"]["ending_common_equity"] == 3_541_884_000
    assert row["reported_inputs"]["share_count"] == 65_659_599
    assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
    for scenario in row["scenario_rows"]:
        replay = residual_income_valuation(book_value_per_share=scenario["book_value_per_share"], current_roe=scenario["current_roe"], cost_of_equity=scenario["cost_of_equity"], current_payout_ratio=scenario["current_payout_ratio"], terminal_roe=scenario["terminal_roe"], terminal_growth=scenario["terminal_growth"], years=5)
        assert replay["intrinsic_value"] == pytest.approx(scenario["raw_value_per_share"])


def test_cpay_events_are_bounded_and_not_double_counted():
    row = result("CPAY")
    maintenance = row["source_ledger"]["pending_maintenance_disposition"]
    assert maintenance["status"] == "signed_pending_regulatory_approval_at_cutoff"
    assert maintenance["expected_gross_proceeds"] == 800_000_000
    assert maintenance["proceeds_or_gain_included_in_value"] is False
    grant = row["source_ledger"]["post_cutoff_share_event"]
    assert grant["maximum_psus"] == 328_213
    assert row["scenario_rows"][0]["shares"] == row["reported_inputs"]["share_count"] + 328_213
    assert row["scenario_rows"][1]["shares"] == row["reported_inputs"]["share_count"]
    assert "$100M FTC charge is already included" in row["warning"]


def test_recovery_public_contract_and_calculator_are_safe():
    from run_batch_38_recovery import _public
    for issuer in BATCH_38_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "customer_funding_reconciliation", "favorable_bridge_challenge"):
            assert key not in encoded
        view = calculator_view(public)
        if issuer.ticker == "GPN":
            assert public["availability_type"] == "not_available"
            assert public["model_policy"]["primary"] == "fcff_dcf"
            assert not view["can_calculate"]
        else:
            assert view["can_calculate"]
            assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
    cpay = _public(next(row for row in BATCH_38_MANIFEST if row.ticker == "CPAY"), result("CPAY"))
    assert cpay["model_policy"]["primary"] == "residual_income"
    assert set(cpay["models"]) == {"residual_income"}


def test_recovery_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_38_recovery import run
    report = run(initial_root=INITIAL, output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (2, 0, 9, 1, 9)
    assert report["attempted_tickers"] == ["GPN", "CPAY"]
    assert report["recovered_to_conditional_tickers"] == ["CPAY"]
    assert report["still_withheld_tickers"] == ["GPN"]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
