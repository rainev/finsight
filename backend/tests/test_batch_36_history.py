from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_36 import BATCH_36_MANIFEST, BATCH_36_TICKERS
from app.us_valuation.batch_36_history import CONDITIONAL_TICKERS, PASS_TICKERS, WITHHELD_TICKERS, _verify_source_bundle, build_batch_36_history_result


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-36-sec-source-packets-20260905"
STRUCTURAL = ROOT / "output/batch-36-structural-sources-20260905"
EVENTS = ROOT / "output/batch-36-event-sources-v3-20260905"
CACHE = ROOT / "output/batch-36-structural-cache-20260905"


def result(ticker):
    return build_batch_36_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS, structural_cache_root=CACHE)


def test_contract_and_initial_outcome_partition():
    assert tuple(row.ticker for row in BATCH_36_MANIFEST) == BATCH_36_TICKERS
    assert len(BATCH_36_TICKERS) == 10
    assert not PASS_TICKERS
    assert CONDITIONAL_TICKERS == set(BATCH_36_TICKERS) - {"VLO"}
    assert WITHHELD_TICKERS == {"VLO"}


def test_numeric_results_are_finite_ordered_low_and_withheld_is_empty():
    for ticker in CONDITIONAL_TICKERS:
        row = result(ticker)
        low, base, high = (row["scenario_range"][key] for key in ("low", "base", "high"))
        assert 0 <= low <= base <= high
        assert base > 0
        assert row["history_reliability"]["label"] == "Low"
    vlo = result("VLO")
    assert vlo["availability_type"] == "not_available"
    assert vlo["scenario_range"] == {"low": None, "base": None, "high": None}
    assert vlo["history_reliability"] is None


def test_financial_routes_are_equity_level_and_replay_exactly():
    from app.valuation.bank import residual_income_valuation
    for ticker in set(BATCH_36_TICKERS) - {"FISV", "VLO"}:
        row = result(ticker)
        assert row["governed_assumptions"]["route_is_equity_level"] is True
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
        for scenario in row["scenario_rows"]:
            replay = residual_income_valuation(book_value_per_share=scenario["book_value_per_share"], current_roe=scenario["current_roe"], cost_of_equity=scenario["cost_of_equity"], current_payout_ratio=scenario["current_payout_ratio"], terminal_roe=scenario["terminal_roe"], terminal_growth=scenario["terminal_growth"], years=5)
            assert replay["intrinsic_value"] == pytest.approx(scenario["raw_value_per_share"])


def test_roe_policy_is_conservative_even_when_recent_returns_are_high():
    expected = {"AMP": (.10, .14, .18), "HIG": (.08, .12, .16), "GS": (.08, .12, .16), "MS": (.08, .12, .16), "ALL": (.08, .12, .16)}
    for ticker, policy in expected.items():
        actual = tuple(row["current_roe"] + (row["event_forward_common_earnings_drag"] / max(row["ending_common_equity"], 1)) for row in result(ticker)["scenario_rows"])
        assert actual == pytest.approx(policy)
    assert result("AMP")["scenario_rows"][1]["current_roe"] == pytest.approx(.14)


def test_fisv_is_operating_fcff_with_settlement_and_finance_assets_separated():
    from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
    row = result("FISV")
    assert row["method"] == "payments_processor_operating_fcff"
    bridge = row["source_ledger"]["bridge_reconciliation"]
    assert bridge["unrestricted_cash"] == 627_000_000
    assert bridge["settlement_assets_excluded"] == bridge["settlement_liabilities_excluded"] == 17_561_000_000
    assert row["governed_assumptions"]["captive_finance_reinvestment_burden"] == (300_000_000., 150_000_000., 0.)
    reconciliation = row["source_ledger"]["captive_finance_reinvestment_reconciliation"]
    assert reconciliation["reported_current_net_collection"] == 300_000_000
    assert reconciliation["governed_future_burden_range"] == (300_000_000., 150_000_000., 0.)
    assert reconciliation["merchant_originations"]["value"] == 566_000_000
    assert reconciliation["merchant_repayments_and_sales"]["value"] == -678_000_000
    assert reconciliation["settlement_anticipation_net_collection"]["value"] == -188_000_000
    assert row["reported_inputs"]["ttm_interest"] == 1_552_000_000
    for scenario in row["scenario_rows"]:
        state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0., scenario["other_equity_claims"], scenario["shares"])
        replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
        assert max(0., replay["intrinsic_value_per_share"]) == pytest.approx(scenario["conditional_value_per_share"])


def test_preferred_claim_aliases_and_cutoff_events_are_not_zero_or_double_counted():
    cof = result("COF")
    assert cof["reported_inputs"]["reported_preferred_equity"] == 5_407_000_000
    assert cof["reported_inputs"]["preferred_claim_midpoint"] == 5_407_000_000
    assert cof["source_ledger"]["preferred_context"]["current"][0]["concept"].endswith("PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount")
    assert cof["source_ledger"]["predecessor_history_treatment"] == "rejected_from_model_due_post_discover_scope"
    assert cof["governed_assumptions"]["history_years_used"] == 1
    gs = result("GS")
    assert gs["reported_inputs"]["reported_preferred_equity"] == 13_028_000_000
    assert gs["governed_assumptions"]["event_preferred_claim_and_proceeds"] == 1_750_000_000
    assert gs["governed_assumptions"]["event_forward_common_earnings_drag"] == pytest.approx((583_667_250, 359_396_125, 135_125_000))
    assert gs["governed_assumptions"]["event_debt_principal"] == 10_000_000_000
    assert gs["governed_assumptions"]["event_annualized_gross_interest"] == 567_775_000
    assert gs["reported_inputs"]["post_event_total_equity"] - gs["reported_inputs"]["ending_common_equity"] == 14_778_000_000
    cb = result("CB")
    assert cb["reported_inputs"]["reported_preferred_equity"] is None
    assert cb["reported_inputs"]["preferred_claim_midpoint"] == 753_720_000
    claims = [row["preferred_claim"] for row in cb["scenario_rows"]]
    assert claims[0] > claims[1] > claims[2] == 0
    assert cb["reported_inputs"]["ttm_common_earnings"] == 11_185_000_000
    attribution = cb["source_ledger"]["earnings_attribution_context"]
    assert len(attribution) == 2
    assert attribution[0]["consolidated"]["value"] - attribution[0]["nci"]["value"] == attribution[0]["parent_attributable"]["value"]


def test_vlo_withholding_preserves_capex_debt_and_event_provenance():
    row = result("VLO")
    bridge = row["source_ledger"]["bridge_reconciliation"]
    assert bridge["debt_and_finance_leases_at_2026_06_30"] == 11_349_000_000
    assert bridge["restricted_cash_excluded"] == 180_000_000
    assert bridge["custom_capex_current_h1"] == 798_000_000
    assert bridge["custom_capex_prior_h1"] == 1_066_000_000
    filings = row["source_ledger"]["event_sources"][0]["screened_filings"]
    assert {item["accession"] for item in filings} == {"0001628280-26-048495", "0001628280-26-050937"}
    assert "cannot reasonably be estimated" in row["warning"]


def test_public_artifacts_are_safe_and_calculators_replay_defaults():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_36_history import _public
    for issuer in BATCH_36_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        for key in ("source_ledger", "reported_inputs", "runtime_source_verification", "event_sources", "residual_income_trace", "model_trace"):
            assert key not in encoded
        view = calculator_view(public)
        if issuer.ticker == "VLO":
            assert public["availability_type"] == "not_available"
            assert public["model_policy"]["primary"] == "fcff_dcf"
            assert set(public["models"]) == {"fcff_dcf"}
            assert public["bridge_quality"]["blocking_fields"] == ["other_equity_claims"]
            assert view["can_calculate"] is False
        else:
            assert public["availability_type"] == "conditional_estimate"
            if issuer.ticker == "FISV":
                assert public["bridge_quality"]["intrinsic_value_range"]["low"] == pytest.approx(private["scenario_range"]["low"])
                assert public["bridge_quality"]["intrinsic_value_range"]["high"] == pytest.approx(private["scenario_range"]["high"])
            assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
            assert calculate(public, overrides=view["defaults"], manual_price=None)["result"] == pytest.approx(private["scenario_range"])


def test_source_bundle_hashes_fail_closed(tmp_path):
    control = result("FISV")["source_ledger"]["controlling_filing"]
    packet = tmp_path / "packet" / "FISV"
    structural = tmp_path / "structural" / "FISV"
    cache = tmp_path / "cache" / "filings"
    packet.mkdir(parents=True)
    structural.mkdir(parents=True)
    cache.mkdir(parents=True)
    for path in (SOURCE / "FISV").iterdir():
        (packet / path.name).symlink_to(path)
    for path in (STRUCTURAL / "FISV").iterdir():
        (structural / path.name).symlink_to(path)
    (cache / "FISV").symlink_to(CACHE / "filings/FISV", target_is_directory=True)
    (packet / "companyfacts.json").unlink()
    (packet / "companyfacts.json").write_text("{}\n")
    with pytest.raises(ValueError, match="source packet hash mismatch"):
        _verify_source_bundle(ticker="FISV", packet=packet, structural_packet=structural, structural_cache_root=tmp_path / "cache", filing=control)
