import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_43 import BATCH_43_MANIFEST
from app.us_valuation.batch_43_history import build_batch_43_history_result
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {
    "source_root": ROOT / "output/batch-43-sec-source-packets-b-20260907",
    "structural_root": ROOT / "output/batch-43-structural-sources-20260907",
    "event_root": ROOT / "output/batch-43-event-review-20260907",
    "structural_cache_root": ROOT / "output/batch-43-structural-cache-20260907",
    "cop_annual_root": ROOT / "output/batch-43-cop-annual-source-20260907",
}
EXPECTED = {
    "MLM": (16.953588063597977, 106.46410754818967, 218.16355471458706),
    "STLD": (0.5751620187990207, 49.46559171931485, 208.35899065262876),
    "DVN": (None, None, None),
    "COP": (27.377548309324208, 79.99326056311911, 126.98633713971223),
    "NEM": (None, None, None),
    "MOS": (0.0, 11.758146259939611, 58.9516492286897),
    "CF": (52.635941721530564, 141.90394441109885, 244.90114284327666),
    "VMC": (15.436407074592978, 70.67958592097881, 136.64939901704753),
    "LYB": (None, None, None),
    "LIN": (51.760600300444224, 122.98931701930243, 217.5846964717504),
}


@lru_cache(None)
def result(ticker):
    return build_batch_43_history_result(ticker=ticker, **KW)


def test_denominator_sources_values_and_initial_outcomes():
    rows = [result(issuer.ticker) for issuer in BATCH_43_MANIFEST]
    assert len(rows) == 10
    assert [row["ticker"] for row in rows if row["availability_type"] == "not_available"] == ["DVN", "NEM", "LYB"]
    assert all(row["availability_type"] == "conditional_estimate" for row in rows if row["ticker"] not in {"DVN", "NEM", "LYB"})
    for row in rows:
        assert row["source_ledger"]["runtime_source_verification"]["verified"]
        assert row["source_ledger"]["event_sources"]["screened_filings"]
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        if row["availability_type"] == "not_available":
            assert observed == EXPECTED[row["ticker"]]
            assert row["history_reliability"] is None
        else:
            assert observed == pytest.approx(EXPECTED[row["ticker"]])
            assert all(math.isfinite(value) for value in observed)
            assert row["history_reliability"]["label"] == "Low"


def test_numeric_scenarios_replay_exactly_and_floor_only_raw_bear():
    for issuer in BATCH_43_MANIFEST:
        row = result(issuer.ticker)
        for scenario in row["scenario_rows"]:
            state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0., scenario["other_equity_claims"], scenario["shares"])
            replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)["intrinsic_value_per_share"]
            assert replay == pytest.approx(scenario["raw_value_per_share"])
            assert scenario["conditional_value_per_share"] == pytest.approx(max(0., replay))
    assert result("MOS")["scenario_rows"][0]["raw_value_per_share"] < 0
    assert result("MOS")["scenario_range"]["low"] == 0


def test_source_lineage_and_cycle_normalization_are_exact():
    cop = result("COP")["source_ledger"]
    assert [row["period_end"] for row in cop["annual_cash_sources"]] == ["2023-12-31", "2024-12-31", "2025-12-31"]
    assert cop["annual_cash_sources"][-1]["capital_expenditures"]["value"] == 12_553_000_000
    assert cop["flow_sources"]["capital_expenditures"]["value"] == 11_861_000_000
    assert cop["flow_sources"]["capital_expenditures"]["current_h1"]["concept"].endswith("PaymentToAcquireProductiveAssetsAndInvestments")
    vmc = result("VMC")["source_ledger"]["flow_sources"]
    assert vmc["operating_cash_flow"]["current_h1"]["value"] == 584_600_000
    assert vmc["capital_expenditures"]["current_h1"]["value"] == 370_400_000
    cf = result("CF")["source_ledger"]["flow_sources"]
    assert cf["reported_cash_fcff_before_event_normalization"] - cf["cash_fcff"] == 170_000_000
    assert result("MOS")["governed_assumptions"]["cash_conversion_margin"][1] > 0


def test_claim_bridges_and_cutoff_events_are_applied_once():
    mlm = result("MLM")["source_ledger"]["bridge_context"]
    assert mlm["cash"] == 5_612_000_000 and mlm["debt"] == 11_451_000_000
    assert mlm["excluded_or_separately_treated"]["august_note_overlay"]["cash"] == 5_500_000_000
    assert mlm["claims"] == pytest.approx((57_000_000, 2_000_000, 2_000_000))
    stld = result("STLD")["source_ledger"]["bridge_context"]
    assert stld["claims"] == pytest.approx((143_259_000, 143_259_000, 143_259_000))
    assert stld["excluded_or_separately_treated"]["negative_nonredeemable_nci_not_inverted"] == -199_720_000
    assert result("CF")["source_ledger"]["bridge_context"]["claims"] == pytest.approx((3_172_000_000,) * 3)
    assert result("MOS")["source_ledger"]["bridge_context"]["debt"] == 5_855_700_000
    assert result("LIN")["source_ledger"]["bridge_context"]["claims"] == pytest.approx((1_549_000_000,) * 3)
    assert "priced but settle after" in result("MOS")["source_ledger"]["event_sources"]["treatment"]


def test_scope_changers_fail_closed_without_zero_imputation():
    for ticker in ("DVN", "NEM", "LYB"):
        row = result(ticker)
        assert row["scenario_range"] == {"low": None, "base": None, "high": None}
        assert row["source_ledger"]["current_ttm_is_diagnostic_only"] is True
        assert "Revalue" in row["governed_assumptions"]["invalidation"]
    assert "Coterra" in result("DVN")["warning"]
    assert "$1.95B" in result("NEM")["warning"]
    assert "consolidated" in result("LYB")["warning"]


def test_public_contract_calculator_and_private_boundary_are_exact():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_43_history import _public

    for issuer in BATCH_43_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        assert public["model_policy"]["primary"] == "fcff_dcf"
        view = calculator_view(public)
        if private["availability_type"] == "not_available":
            assert not view["can_calculate"]
        else:
            assert view["can_calculate"]
            assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
            higher = calculate(public, overrides={"discount_rate": view["defaults"]["discount_rate"] + .01}, manual_price=None)
            assert higher["result"]["base"] < private["scenario_range"]["base"]
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "runtime_source_verification", "raw_scenario_rows"):
            assert key not in encoded


def test_source_tampering_fails_closed(tmp_path):
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "CF", source / "CF")
    (source / "CF" / "companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_43_history_result(ticker="CF", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path):
    from run_batch_43_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 7, 3, 7)
    assert report["denominator_tickers"] == [issuer.ticker for issuer in BATCH_43_MANIFEST]
    assert report["batch_42_dependency_status"] == "confirmed_batch_42_recovery_catalog_and_bookkeeping_bound"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
