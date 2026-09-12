import json, math, sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_39 import BATCH_39_MANIFEST
from app.us_valuation.batch_39_history import build_batch_39_history_result
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from app.valuation.bank import residual_income_valuation


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {"source_root": ROOT / "output/batch-39-sec-source-packets-20260907", "structural_root": ROOT / "output/batch-39-structural-sources-20260907", "structural_cache_root": ROOT / "output/batch-39-structural-cache-20260907", "event_root": ROOT / "output/batch-39-event-review-20260907"}
EXPECTED = {
    "ARES": (7.5009712961046615, 12.518844692911918, 17.787468563059363),
    "RF": (13.166011411505744, 21.309338652768535, 29.53298912173637),
    "CBOE": (82.52698381312132, 185.25601329677832, 313.5824693012958),
    "IBKR": (9.260992215293587, 15.291802562890975, 21.4680792029658),
    "TRGP": (0.0, 73.40857708609367, 207.21891242872445),
    "BNY": (43.78099920339457, 68.85452553608589, 96.6438262534545),
    "BX": (8.515650442345999, 14.085664559150201, 19.912841939711313),
    "V": (155.05120152180547, 229.12545553810705, 376.79112579242224),
    "KKR": (21.550674926898868, 35.49410604697175, 49.98667171252024),
    "KMI": (4.524392329711989, 15.48158919730078, 30.03515557993387),
}


@lru_cache(None)
def result(ticker):
    return build_batch_39_history_result(ticker=ticker, **KW)


def test_denominator_values_sources_and_initial_outcomes():
    rows = [result(issuer.ticker) for issuer in BATCH_39_MANIFEST]
    assert len(rows) == 10
    assert all(row["availability_type"] == "conditional_estimate" for row in rows)
    for row in rows:
        assert row["source_ledger"]["runtime_source_verification"]["verified"]
        assert row["source_ledger"]["event_sources"]["screened_filings"]
        assert tuple(row["scenario_range"][key] for key in ("low", "base", "high")) == pytest.approx(EXPECTED[row["ticker"]])
        assert all(math.isfinite(value) for value in EXPECTED[row["ticker"]])
        assert row["history_reliability"]["label"] == "Low"


def test_all_scenarios_replay_canonical_models_exactly():
    for issuer in BATCH_39_MANIFEST:
        row = result(issuer.ticker)
        for scenario in row["scenario_rows"]:
            if "book_value_per_share" in scenario:
                replay = residual_income_valuation(book_value_per_share=scenario["book_value_per_share"], current_roe=scenario["current_roe"], cost_of_equity=scenario["cost_of_equity"], current_payout_ratio=scenario["current_payout_ratio"], terminal_roe=scenario["terminal_roe"], terminal_growth=scenario["terminal_growth"], years=5)["intrinsic_value"]
            else:
                state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0.0, scenario["other_equity_claims"], scenario["shares"])
                replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
            assert replay == pytest.approx(scenario["raw_value_per_share"])


def test_financial_parent_equity_preferred_and_share_controls():
    ares, rf, ibkr, bny, bx, kkr = (result(ticker) for ticker in ("ARES", "RF", "IBKR", "BNY", "BX", "KKR"))
    assert ares["reported_inputs"]["preferred_claim"] == 1_460_030_000
    assert ares["reported_inputs"]["share_count"] == 227_447_653
    conversion = ares["source_ledger"]["equity_model_context"]["ares_mandatory_conversion"]
    assert conversion["minimum_future_class_a_shares"] == 8_151_000
    assert conversion["maximum_future_class_a_shares"] == 9_780_000
    assert rf["reported_inputs"]["preferred_claim"] == 1_400_000_000
    assert bny["reported_inputs"]["preferred_claim"] == 5_254_000_000
    assert bny["governed_assumptions"]["event_preferred_claim_and_proceeds"] == 500_000_000
    assert bny["governed_assumptions"]["event_debt_principal"] == 2_500_000_000
    assert bny["source_ledger"]["bny_note_event"]["fixed_note_interest"] == 108_880_000
    assert ibkr["scenario_rows"][0]["shares"] - ibkr["reported_inputs"]["share_count"] == 3_419_567
    assert bx["source_ledger"]["common_earnings_reconstruction"]["ttm"] == 3_473_481_000
    assert kkr["reported_inputs"]["preferred_claim"] == 2_543_404_000
    assert all(row["governed_assumptions"]["ev_debt_bridge_applied"] is False for row in (ares, rf, ibkr, bny, bx, kkr))


def test_cboe_visa_and_midstream_boundaries_are_reconciled():
    cboe, visa, trgp, kmi = (result(ticker) for ticker in ("CBOE", "V", "TRGP", "KMI"))
    assert cboe["source_ledger"]["bridge_context"]["clearing_assets"] == cboe["source_ledger"]["bridge_context"]["clearing_liabilities"] == 2_542_300_000
    assert visa["source_ledger"]["flow_sources"]["period_end"] == "2026-06-30"
    assert visa["source_ledger"]["flow_sources"]["values"] == {"revenue": 44_488_000_000, "operating_cash_flow": 22_580_000_000, "capital_expenditures": 1_567_000_000, "interest_expense": 776_000_000}
    assert visa["source_ledger"]["bridge_context"]["matched_customer_collateral"] == 4_310_000_000
    assert trgp["source_ledger"]["special_reinvestment"]["formula"].startswith("2 x (reported OCF + after-tax interest")
    assert trgp["source_ledger"]["bridge_context"]["finance_lease_liability"]["value"] == 794_100_000
    assert kmi["source_ledger"]["bridge_context"]["cutoff_refinancing"]["net_debt_change"] == 0
    assert "not added as surplus cash" in kmi["source_ledger"]["bridge_context"]["treatment"]


def test_public_contract_and_calculator_defaults_are_exact_and_safe():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_39_history import _public
    for issuer in BATCH_39_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        assert public["availability_type"] == "conditional_estimate"
        assert calculator_view(public)["can_calculate"]
        assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "runtime_source_verification", "raw_scenario_rows"):
            assert key not in encoded


def test_higher_discount_rate_lowers_every_numeric_base():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_39_history import _public
    for issuer in BATCH_39_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        view = calculator_view(public)
        higher = calculate(public, overrides={"discount_rate": view["defaults"]["discount_rate"] + .01}, manual_price=None)
        assert higher["result"]["base"] < private["scenario_range"]["base"]


def test_source_tampering_fails_closed(tmp_path):
    import shutil
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "V", source / "V")
    (source / "V" / "companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_39_history_result(ticker="V", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_39_history import run
    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 10, 0, 10)
    assert report["denominator_tickers"] == [issuer.ticker for issuer in BATCH_39_MANIFEST]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
