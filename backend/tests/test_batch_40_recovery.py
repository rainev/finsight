from functools import lru_cache
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

from app.us_valuation.batch_40 import BATCH_40_MANIFEST
from app.us_valuation.batch_40_recovery import build_batch_40_recovery_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-40-sec-source-packets-20260907"
STRUCTURAL = ROOT / "output/batch-40-structural-sources-20260907"
EVENTS = ROOT / "output/batch-40-event-review-20260907"
RECOVERY_SOURCES = ROOT / "output/batch-40-recovery-event-sources-20260907"
CACHE = ROOT / "output/batch-40-structural-cache-20260907"
INITIAL = ROOT / "output/batch-40-history-run-g-20260907"
KW = {
    "source_root": SOURCE,
    "structural_root": STRUCTURAL,
    "event_root": EVENTS,
    "recovery_source_root": RECOVERY_SOURCES,
    "structural_cache_root": CACHE,
}


@lru_cache(None)
def result(ticker):
    return build_batch_40_recovery_result(ticker=ticker, **KW)


def test_recovery_attempt_keeps_coin_withheld_and_denominator_exact():
    rows = {issuer.ticker: result(issuer.ticker) for issuer in BATCH_40_MANIFEST}
    assert len(rows) == 10
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "not_available"} == {"COIN"}
    assert all(row["availability_type"] == "conditional_estimate" for ticker, row in rows.items() if ticker != "COIN")
    coin = rows["COIN"]
    assert coin["scenario_range"] == {"low": None, "base": None, "high": None}
    assert coin["source_ledger"]["recovery_attempt"]["attempted"] is True
    assert coin["source_ledger"]["recovery_attempt"]["missing_earnings_exhibit_recovered"] is True
    assert coin["source_ledger"]["recovery_attempt"]["final_availability_type"] == "not_available"


def test_missing_q2_earnings_exhibit_is_hash_verified_and_not_misused():
    from capture_batch_40_events import _is_relevant_attachment

    assert _is_relevant_attachment("q226earningsdeck_sec.htm")
    coin = result("COIN")
    source = coin["source_ledger"]["completed_earnings_exhibit"]
    assert source["verified"] is True
    assert source["accession"] == "0001679788-26-000087"
    assert source["document"]["filename"] == "q226earningsdeck_sec.htm"
    path = ROOT / source["document"]["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source["document"]["sha256"]
    metrics = source["reported_metrics"]
    assert metrics["q2_total_revenue"] == 1_220_068_000
    assert metrics["q2_adjusted_ebitda_non_gaap"] == 207_800_000
    assert metrics["used_as_valuation_input"] is False


def test_history_preserves_losses_and_rejects_positive_bear_invention():
    coin = result("COIN")
    earnings = coin["source_ledger"]["common_earnings_reconstruction"]
    assert [row["value"] for row in earnings["annual_history"]] == [3_096_958_000, -2_624_949_000, 94_752_000, 2_577_755_000, 1_260_327_000]
    assert earnings["ttm"] == -987_766_000
    diagnostic = coin["source_ledger"]["rejected_through_cycle_diagnostic"]
    assert diagnostic["reported_earnings_percentiles"] == pytest.approx({"low": -717_136_500, "base": 677_539_500, "high": 2_248_398_000})
    assert diagnostic["reported_bear_roe"] < 0
    assert diagnostic["publication_allowed"] is False
    rows = diagnostic["scenario_rows"]
    assert [row["value_per_share"] for row in rows] == pytest.approx((10.645841192086817, 37.63579498574516, 74.37156421773588))
    assert all(row["publication_allowed"] is False for row in rows)
    assert "manufacture" in diagnostic["why_rejected"]


def test_customer_crypto_cash_boundaries_reconcile_without_free_cash():
    coin = result("COIN")
    boundary = coin["source_ledger"]["customer_crypto_funding_reconciliation"]
    cash = boundary["aggregate_cash_reconciliation"]
    assert cash["aggregate_cash_and_restricted"]["value"] == 13_152_428_000
    assert cash["corporate_cash"]["value"] == 8_614_065_000
    assert cash["restricted_cash"]["value"] == 275_815_000
    assert cash["client_custodial_cash"]["value"] == 4_262_548_000
    assert cash["difference"] == 0
    assert boundary["client_custodial_funds"]["value"] == boundary["custodial_cash_liability"]["value"] == 4_299_190_000
    assert boundary["safeguarding_asset_off_balance_sheet"]["value"] == boundary["safeguarding_liability_off_balance_sheet"]["value"] == 245_900_000_000
    assert boundary["all_customer_or_financing_balances_used_as_issuer_cash"] is False


def test_tax_regulatory_claim_and_dilution_gates_are_explicit():
    coin = result("COIN")
    claim = coin["source_ledger"]["tax_legal_regulatory_claim_boundary"]
    assert claim["possible_loss_range"] is None
    assert claim["loss_range_estimable"] is False
    assert claim["established_accruals_complete_bound"] is False
    capital = coin["source_ledger"]["capital_and_dilution_context"]
    assert capital["temporary_equity"]["value"] == 0
    assert capital["current_class_a_plus_b_shares"]["value"] == 263_836_923
    assert capital["option_shares_outstanding"]["value"] == 18_617_000
    assert capital["nonvested_rsu_shares"]["value"] == 5_197_000
    assert capital["nonvested_prsu_shares"]["value"] == 426_000
    assert capital["undiscounted_full_share_stress"] == 288_076_923


def test_recovery_public_contract_is_safe_and_calculator_behavior_is_exact():
    from run_batch_40_recovery import _public

    for issuer in BATCH_40_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "rejected_through_cycle_diagnostic", "tax_legal_regulatory_claim_boundary"):
            assert key not in encoded
        view = calculator_view(public)
        if issuer.ticker == "COIN":
            assert public["availability_type"] == "not_available"
            assert public["model_policy"]["primary"] == "residual_income"
            assert set(public["models"]) == {"residual_income"}
            assert public["bridge_quality"]["blocking_fields"] == ["other_equity_claims"]
            assert public["bridge_quality"]["bounded_fields"] == ["cash"]
            assert public["bridge_quality"]["reason_codes"] == ["BRIDGE_POLICY_WITHHELD", "MAJOR_EVENT_UNBOUNDED"]
            assert not view["can_calculate"]
            assert "conditional_estimate" not in encoded
        else:
            assert view["can_calculate"]
            assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])


def test_recovery_source_tampering_fails_closed(tmp_path):
    bad = tmp_path / "recovery-sources"
    shutil.copytree(RECOVERY_SOURCES, bad)
    exhibit = bad / "COIN/0001679788-26-000087/q226earningsdeck_sec.htm"
    exhibit.write_bytes(exhibit.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="exhibit hash mismatch"):
        build_batch_40_recovery_result(ticker="COIN", **{**KW, "recovery_source_root": bad})


def test_recovery_runner_pins_initial_and_preserves_protected_state(tmp_path):
    from run_batch_40_recovery import run

    output = tmp_path / "candidate"
    report = run(initial_root=INITIAL, output_root=output, **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (1, 0, 9, 1, 9)
    assert report["attempted_tickers"] == ["COIN"]
    assert report["recovered_to_conditional_tickers"] == []
    assert report["still_withheld_tickers"] == ["COIN"]
    assert not report["serving_artifacts_changed"]
    assert not report["watchlist_changed"]
    assert not report["withheld_register_changed"]
    for issuer in BATCH_40_MANIFEST:
        if issuer.ticker == "COIN":
            continue
        assert (output / "generated" / issuer.ticker / "valuation-private.json").read_bytes() == (INITIAL / "generated" / issuer.ticker / "valuation-private.json").read_bytes()
        assert (output / "staged-public" / f"{issuer.ticker}.json").read_bytes() == (INITIAL / "staged-public" / f"{issuer.ticker}.json").read_bytes()
        assert next(row for row in report["cases"] if row["ticker"] == issuer.ticker) == next(row for row in json.loads((INITIAL / "batch-40-report.json").read_text())["cases"] if row["ticker"] == issuer.ticker)
