from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_35 import BATCH_35_MANIFEST, BATCH_35_TICKERS
from app.us_valuation.batch_35_history import CONDITIONAL_TICKERS, PASS_TICKERS, WITHHELD_TICKERS, _verify_source_bundle, build_batch_35_history_result


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-35-sec-source-packets-20260904"
STRUCTURAL = ROOT / "output/batch-35-structural-sources-20260904"
EVENTS = ROOT / "output/batch-35-event-sources-repair-20260904"


def result(ticker):
    return build_batch_35_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENTS if EVENTS.exists() else None)


def test_contract_and_outcome_partition():
    assert len(BATCH_35_MANIFEST) == 10
    assert tuple(row.ticker for row in BATCH_35_MANIFEST) == BATCH_35_TICKERS
    assert not PASS_TICKERS
    assert CONDITIONAL_TICKERS == set(BATCH_35_TICKERS)
    assert not WITHHELD_TICKERS


def test_each_result_is_finite_ordered_and_history_backed():
    for ticker in BATCH_35_TICKERS:
        row = result(ticker)
        low, base, high = (row["scenario_range"][key] for key in ("low", "base", "high"))
        assert 0 <= low <= base <= high
        assert base > 0
        assert row["availability_type"] == "conditional_estimate"
        assert row["history_reliability"]["label"] in {"High", "Medium", "Low"}
        assert row["governed_assumptions"]["history_years_used"] >= 5


def test_exact_source_identity_and_period_are_private():
    for ticker in BATCH_35_TICKERS:
        row = result(ticker)
        filing = row["source_ledger"]["controlling_filing"]
        assert filing["accession"]
        assert filing["period_end"] <= "2026-06-30"
        assert row["source_ledger"]["structural_top_level_period_diagnostic"]["used_for_selection"] is False


def test_financial_equity_is_not_ev_bridged_and_wmb_is_fcff():
    for ticker in set(BATCH_35_TICKERS) - {"WMB"}:
        row = result(ticker)
        assert row["governed_assumptions"]["route_is_equity_level"] is True
        assert row["governed_assumptions"]["ev_debt_bridge_applied"] is False
    wmb = result("WMB")
    assert wmb["method"] == "resource_cycle_fcff"
    assert wmb["governed_assumptions"]["cash_conversion_margin"]
    assert all(item["starting_cash_fcff"] > 0 for item in wmb["scenario_rows"])


def test_public_payload_has_no_private_source_ledger():
    from run_batch_35_history import _public
    for issuer in BATCH_35_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        for key in ("source_ledger", "reported_inputs", "residual_income_trace", "equity_model_context", "flow_sources", "model_trace"):
            assert key not in encoded
        for key in ("low", "base", "high"):
            assert public["scenario_range"][key] == private["scenario_range"][key]


def test_residual_income_replay_for_financial_equity():
    from app.valuation.bank import residual_income_valuation
    for ticker in set(BATCH_35_TICKERS) - {"WMB"}:
        row = result(ticker)
        for scenario in row["scenario_rows"]:
            replay = residual_income_valuation(book_value_per_share=scenario["book_value_per_share"], current_roe=scenario["current_roe"], cost_of_equity=scenario["cost_of_equity"], current_payout_ratio=scenario["current_payout_ratio"], terminal_roe=scenario["terminal_roe"], terminal_growth=scenario["terminal_growth"], years=5)
            assert replay["intrinsic_value"] == pytest.approx(scenario["raw_value_per_share"])


def test_preferred_claims_are_period_matched_and_missing_values_are_not_zero_imputed():
    wfc = result("WFC")
    assert wfc["reported_inputs"]["beginning_preferred_equity"] == 17_376_000_000
    assert wfc["reported_inputs"]["preferred_equity"] == 16_116_000_000
    schw = result("SCHW")
    assert schw["reported_inputs"]["beginning_preferred_equity"] == 6_871_000_000
    assert schw["reported_inputs"]["preferred_equity"] == 6_315_000_000
    gl = result("GL")
    assert gl["source_ledger"]["preferred_context"]["current_status"] == "reported_preferred_absence"
    assert gl["governed_assumptions"]["preferred_claim_range"] == (0.0, 0.0, 0.0)
    pnc = result("PNC")
    assert pnc["reported_inputs"]["preferred_equity"] == 5_879_000_000
    assert pnc["reported_inputs"]["beginning_preferred_equity"] == 5_760_000_000
    wmb = result("WMB")
    assert wmb["source_ledger"]["bridge_reconciliation"]["preferred_equity"] == 35_000_000
    assert wmb["governed_assumptions"]["assumption_classification"]["unreported_investments"] == "excluded_not_zero_imputed"


def test_non_calendar_issuers_use_their_latest_audited_fiscal_year_equity_anchor():
    assert result("RJF")["source_ledger"]["preferred_context"]["prior_equity_period"] == "2025-09-30"
    assert result("JKHY")["source_ledger"]["preferred_context"]["prior_equity_period"] == "2025-06-30"


def test_wmb_bridge_includes_every_debt_component_and_bounds_restricted_cash():
    row = result("WMB")
    bridge = row["source_ledger"]["bridge_reconciliation"]
    assert bridge["noncurrent_debt_and_finance_leases"] == 28_121_000_000
    assert bridge["current_debt"] == 2_197_000_000
    assert bridge["commercial_paper"] == 475_000_000
    assert bridge["debt_and_finance_leases"] == 30_793_000_000
    assert bridge["cash_availability_range"] == (0.0, 101_500_000.0, 203_000_000.0)
    assert row["scenario_range"] == pytest.approx({"low": 0.0, "base": 15.439688427767331, "high": 41.84304198875888})


def test_unreported_preferred_claims_are_adverse_in_bear_and_favorable_in_bull():
    for ticker in ("AON", "AJG"):
        row = result(ticker)
        claims = [scenario["preferred_claim"] for scenario in row["scenario_rows"]]
        assert claims[0] > claims[1] > claims[2] == 0
        assert "explicit governed common-equity claim sensitivity" in row["warning"]


def test_complete_cutoff_event_ledger_is_consumed_and_scenario_adjusted():
    rows = {ticker: result(ticker) for ticker in BATCH_35_TICKERS}
    assert all(len(row["source_ledger"]["event_sources"]) == 1 for row in rows.values())
    accepted = {ticker for ticker, row in rows.items() if row["source_ledger"]["event_sources"][0]["decision"] == "accepted"}
    assert accepted == {"WMB", "SCHW", "PNC", "CFG", "JKHY"}
    assert rows["PNC"]["governed_assumptions"]["event_forward_common_earnings_drag"] == pytest.approx((81_322_600, 40_661_300, 0))
    assert rows["SCHW"]["governed_assumptions"]["event_forward_common_earnings_drag"] == pytest.approx((110_752_075, 55_376_037.5, 0))
    for ticker in ("PNC", "SCHW"):
        assert rows[ticker]["governed_assumptions"]["event_interest_tax_rate"] == .21
        assert rows[ticker]["governed_assumptions"]["event_proceeds_income_offset"] == (0.0, 0.5, 1.0)
    assert rows["CFG"]["governed_assumptions"]["event_preferred_claim"] == 400_000_000
    assert rows["CFG"]["governed_assumptions"]["event_forward_common_earnings_drag"] == (27_000_000.0,) * 3
    assert "$42.8M FY2026 deconversion revenue" in rows["JKHY"]["warning"]
    assert "$5.34B of partner capital" in rows["WMB"]["warning"]


def test_public_model_and_calculator_replay_the_actual_formula():
    from app.us_valuation.calculator import calculate, calculator_view
    from app.valuation.bank import residual_income_valuation
    from run_batch_35_history import _public
    for issuer in BATCH_35_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        view = calculator_view(public)
        expected_model = "fcff_dcf" if issuer.ticker == "WMB" else "residual_income"
        expected_family = "enterprise_fcff" if issuer.ticker == "WMB" else "residual_income"
        assert public["availability_type"] == "conditional_estimate"
        assert public["model_policy"]["primary"] == expected_model
        assert set(public["models"]) == {expected_model}
        assert view["model_family"] == expected_family
        assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
        assert calculate(public, overrides=view["defaults"], manual_price=None)["result"] == pytest.approx(private["scenario_range"])
        if issuer.ticker == "WMB":
            assert view["defaults"]["discount_rate"] == private["scenario_rows"][1]["wacc"] == .095
            higher = calculate(public, overrides={"discount_rate": .105}, manual_price=None)
            defaults = view["defaults"]
            cash = defaults["starting_cash_fcff_per_share"] * defaults["cash_conversion"]
            pv = 0.0
            for year in range(1, defaults["forecast_years"] + 1):
                fade = (defaults["forecast_years"] - year) / (defaults["forecast_years"] - 1)
                growth = defaults["terminal_growth"] + (defaults["initial_growth"] - defaults["terminal_growth"]) * fade
                cash *= 1 + growth
                pv += cash / (1 + defaults["discount_rate"]) ** year
            direct = pv + cash * (1 + defaults["terminal_growth"]) / (defaults["discount_rate"] - defaults["terminal_growth"]) / (1 + defaults["discount_rate"]) ** defaults["forecast_years"] + defaults["bridge_adjustment_per_share"]
            assert direct == pytest.approx(private["scenario_range"]["base"])
        else:
            assert view["defaults"]["sustainable_roe"] == private["scenario_rows"][1]["current_roe"]
            higher = calculate(public, overrides={"discount_rate": view["defaults"]["discount_rate"] + .01}, manual_price=None)
            direct = residual_income_valuation(
                book_value_per_share=view["defaults"]["book_value_per_share"],
                current_roe=view["defaults"]["sustainable_roe"],
                cost_of_equity=view["defaults"]["discount_rate"],
                current_payout_ratio=view["defaults"]["payout_ratio"],
                terminal_roe=view["defaults"]["terminal_roe"],
                terminal_growth=view["defaults"]["terminal_growth"],
                years=view["defaults"]["forecast_years"],
            )["intrinsic_value"]
            assert direct == pytest.approx(private["scenario_range"]["base"])
        assert higher["result"]["base"] < private["scenario_range"]["base"]


def test_exact_calculator_lanes_reject_invalid_terminal_spreads():
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_35_history import _public
    wfc_issuer = next(row for row in BATCH_35_MANIFEST if row.ticker == "WFC")
    wmb_issuer = next(row for row in BATCH_35_MANIFEST if row.ticker == "WMB")
    with pytest.raises(ValueError, match="3% below"):
        calculate(_public(wfc_issuer, result("WFC")), overrides={"discount_rate": .065, "terminal_growth": .04}, manual_price=None)
    with pytest.raises(ValueError, match="2.5% below"):
        calculate(_public(wmb_issuer, result("WMB")), overrides={"discount_rate": .062, "terminal_growth": .04}, manual_price=None)
    wfc_public = _public(wfc_issuer, result("WFC"))
    changed_locked = dict(calculator_view(wfc_public)["defaults"])
    changed_locked["book_value_per_share"] += 1
    with pytest.raises(ValueError, match="locked source-derived"):
        calculate(wfc_public, overrides=changed_locked, manual_price=None)


def test_source_bundle_hashes_are_runtime_enforced(tmp_path):
    actual = result("WFC")["source_ledger"]["runtime_source_verification"]
    assert actual["verified"] is True
    assert actual["primary_document_sha256"]

    packet = tmp_path / "packet" / "WFC"
    structural = tmp_path / "structural" / "WFC"
    cache = tmp_path / "cache" / "filings"
    packet.mkdir(parents=True)
    structural.mkdir(parents=True)
    cache.mkdir(parents=True)
    for path in (SOURCE / "WFC").iterdir():
        (packet / path.name).symlink_to(path)
    for path in (STRUCTURAL / "WFC").iterdir():
        (structural / path.name).symlink_to(path)
    (cache / "WFC").symlink_to(ROOT / "output/batch-35-structural-cache-20260904/filings/WFC", target_is_directory=True)
    (packet / "companyfacts.json").unlink()
    (packet / "companyfacts.json").write_text("{}\n")
    control = result("WFC")["source_ledger"]["controlling_filing"]
    with pytest.raises(ValueError, match="source packet hash mismatch"):
        _verify_source_bundle(ticker="WFC", packet=packet, structural_packet=structural, structural_cache_root=tmp_path / "cache", filing=control)


def test_event_capture_replays_all_ten_without_network(tmp_path):
    from capture_batch_35_event_sources import capture
    output = tmp_path / "events"
    reuse = (ROOT / "output/batch-35-event-sources-20260904", ROOT / "output/batch-35-event-repair-20260904")
    first = capture(source_root=SOURCE, output_root=output, reuse_roots=reuse)
    second = capture(source_root=SOURCE, output_root=output, reuse_roots=reuse)
    assert first == second
    assert (first["attempted"], first["accepted"], first["rejected"]) == (10, 5, 5)
    assert {row["ticker"] for row in first["cases"]} == set(BATCH_35_TICKERS)
