import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_40 import BATCH_40_MANIFEST
from app.us_valuation.batch_40_history import build_batch_40_history_result
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from app.valuation.bank import residual_income_valuation


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {
    "source_root": ROOT / "output/batch-40-sec-source-packets-20260907",
    "structural_root": ROOT / "output/batch-40-structural-sources-20260907",
    "structural_cache_root": ROOT / "output/batch-40-structural-cache-20260907",
    "event_root": ROOT / "output/batch-40-event-review-20260907",
}
EXPECTED = {
    "MSCI": (130.0741537164008, 265.46018394493495, 404.37721726992066),
    "XYZ": (20.73791089470268, 33.15663715362076, 43.99942798842173),
    "ICE": (38.95027916345947, 85.92002066234853, 134.26299655765646),
    "SYF": (31.312707521452637, 51.082571093152886, 71.28091192910878),
    "PYPL": (16.42860549515635, 27.17441582954794, 38.41635195453094),
    "COIN": (None, None, None),
    "HOOD": (7.155897547606039, 11.983401311204473, 17.075647533130464),
    "TPL": (5.293472432910433, 53.30718459975814, 150.42208741925873),
    "APO": (21.59895771023219, 36.49572409242654, 52.26731753562608),
    "BLK": (279.985496220747, 464.4576093201319, 631.3780969168668),
}


@lru_cache(None)
def result(ticker):
    return build_batch_40_history_result(ticker=ticker, **KW)


def test_denominator_values_sources_and_initial_outcomes():
    rows = [result(issuer.ticker) for issuer in BATCH_40_MANIFEST]
    assert len(rows) == 10
    assert [row["ticker"] for row in rows if row["availability_type"] == "not_available"] == ["COIN"]
    assert all(row["availability_type"] == "conditional_estimate" for row in rows if row["ticker"] != "COIN")
    for row in rows:
        assert row["source_ledger"]["runtime_source_verification"]["verified"]
        assert row["source_ledger"]["event_sources"]["screened_filings"]
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        if row["ticker"] == "COIN":
            assert observed == EXPECTED[row["ticker"]]
            assert row["history_reliability"] is None
        else:
            assert observed == pytest.approx(EXPECTED[row["ticker"]])
            assert all(math.isfinite(value) for value in observed)
            assert row["history_reliability"]["label"] == "Low"


def test_all_numeric_scenarios_replay_canonical_models_exactly():
    for issuer in BATCH_40_MANIFEST:
        row = result(issuer.ticker)
        for scenario in row["scenario_rows"]:
            if "book_value_per_share" in scenario:
                replay = residual_income_valuation(
                    book_value_per_share=scenario["book_value_per_share"],
                    current_roe=scenario["current_roe"],
                    cost_of_equity=scenario["cost_of_equity"],
                    current_payout_ratio=scenario["current_payout_ratio"],
                    terminal_roe=scenario["terminal_roe"],
                    terminal_growth=scenario["terminal_growth"],
                    years=5,
                )["intrinsic_value"]
            else:
                state = EnterpriseCashFlowState(
                    scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"],
                    scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"],
                    0.0, scenario["other_equity_claims"], scenario["shares"],
                )
                replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
            assert replay == pytest.approx(scenario["raw_value_per_share"])


def test_financial_and_customer_asset_boundaries_are_explicit():
    for ticker in ("XYZ", "SYF", "PYPL", "HOOD", "APO", "BLK"):
        row = result(ticker)
        assert row["governed_assumptions"]["route_is_equity_level"] is True
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
        assert "remain inside" in row["source_ledger"]["bridge_treatment"]
    blk = result("BLK")
    assert blk["reported_inputs"]["ending_common_equity"] == 60_441_000_000
    assert blk["reported_inputs"]["share_count"] == 162_476_186
    assert blk["source_ledger"]["common_earnings_reconstruction"]["ttm"] == 6_904_000_000
    coin = result("COIN")
    assert coin["source_ledger"]["common_earnings_reconstruction"]["ttm"] < 0
    boundary = coin["source_ledger"]["customer_boundary"]
    assert boundary["client_custodial_funds"]["value"] == boundary["custodial_cash_liability"]["value"]
    assert boundary["used_as_issuer_cash"] is False


def test_operating_reinvestment_clearing_and_event_bridges_are_bound_once():
    msci, ice, tpl = (result(ticker) for ticker in ("MSCI", "ICE", "TPL"))
    assert msci["source_ledger"]["bridge_context"]["first_street_fixed_cash_sensitivity"] == (120_000_000, 60_000_000, 0.0)
    assert ice["source_ledger"]["bridge_context"]["matched_margin_and_guaranty_funds"] == 114_599_000_000
    assert ice["source_ledger"]["bridge_context"]["transaction_overlay_included"] is False
    components = tpl["source_ledger"]["flow_sources"]["capital_expenditures"]
    assert components["value"] > 0
    assert any(row["concept"] == "tpl:PaymentsToAcquireEquipmentAndOtherAcquisitionOfRealEstate" and row["value"] == 59_531_000 for row in components["latest_fy"]["components"])
    assert components["current_h1"][0]["value"] == 29_201_000
    assert components["prior_h1"][0]["value"] == 12_277_000
    assert any(row["concept"] == "us-gaap:PaymentsToAcquireRoyaltyInterestsInMiningProperties" for row in components["latest_fy"]["components"])


def test_public_contract_calculator_defaults_and_model_identity_are_exact_and_safe():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_40_history import _public

    for issuer in BATCH_40_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        expected_model = "fcff_dcf" if "fcff" in private["method"] else "residual_income"
        assert public["model_policy"]["primary"] == expected_model
        view = calculator_view(public)
        if issuer.ticker == "COIN":
            assert not view["can_calculate"]
            assert public["availability_type"] == "not_available"
        else:
            assert view["can_calculate"]
            assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "runtime_source_verification", "raw_scenario_rows"):
            assert key not in encoded


def test_higher_discount_rate_lowers_every_numeric_base():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_40_history import _public

    for issuer in BATCH_40_MANIFEST:
        private = result(issuer.ticker)
        if private["availability_type"] == "not_available":
            continue
        public = _public(issuer, private)
        view = calculator_view(public)
        higher = calculate(public, overrides={"discount_rate": view["defaults"]["discount_rate"] + 0.01}, manual_price=None)
        assert higher["result"]["base"] < private["scenario_range"]["base"]


def test_source_tampering_fails_closed(tmp_path):
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "PYPL", source / "PYPL")
    (source / "PYPL" / "companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_40_history_result(ticker="PYPL", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_40_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 9, 1, 9)
    assert report["denominator_tickers"] == [issuer.ticker for issuer in BATCH_40_MANIFEST]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
