import hashlib
import json
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_41_recovery import build_batch_41_recovery_result
from app.valuation.bank import residual_income_valuation


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
INITIAL = ROOT / "output/batch-41-history-run-g-20260907"
KW = {
    "source_root": ROOT / "output/batch-41-sec-source-packets-c-20260907",
    "structural_root": ROOT / "output/batch-41-structural-sources-20260907",
    "structural_cache_root": ROOT / "output/batch-41-structural-cache-20260907",
    "event_root": ROOT / "output/batch-41-event-review-c-20260907",
}
EXPECTED_APD = (40.75099009290014, 68.53961494484994, 103.3782018277093)


@lru_cache(None)
def result(ticker):
    return build_batch_41_recovery_result(ticker=ticker, **KW)


def test_recovery_attempts_exactly_three_initial_withheld_issuers():
    apd, iff, ip = (result(ticker) for ticker in ("APD", "IFF", "IP"))
    assert apd["availability_type"] == "conditional_estimate"
    assert tuple(apd["scenario_range"][key] for key in ("low", "base", "high")) == pytest.approx(EXPECTED_APD)
    assert apd["history_reliability"]["label"] == "Low"
    assert iff["availability_type"] == ip["availability_type"] == "not_available"
    assert iff["source_ledger"]["disposal_group_assets"]["value"] == 4_840_000_000
    assert iff["source_ledger"]["disposal_group_liabilities"]["value"] == 1_170_000_000
    assert iff["source_ledger"]["other_held_for_sale_group"]["assets"]["value"] == 44_000_000
    assert iff["source_ledger"]["other_held_for_sale_group"]["liabilities"]["value"] == 3_000_000
    assert iff["source_ledger"]["other_held_for_sale_group"]["included_in_food_ingredients_scl_discontinued_net_assets"] is False
    assert iff["source_ledger"]["recovery_attempt"]["result"].startswith("The named economic-object")
    assert ip["source_ledger"]["recovery_attempt"]["result"].startswith("The named economic-object")


def test_apd_normalized_earnings_and_exit_cash_do_not_double_count():
    apd = result("APD")
    attempt = apd["source_ledger"]["recovery_attempt"]
    assert attempt["raw_ttm_parent_earnings"] == -47_300_000
    assert attempt["after_tax_project_exit_charge"]["value"] == 2_236_600_000
    assert attempt["normalized_ttm_parent_earnings"] == 2_189_300_000
    assert attempt["recognized_fy2026_project_exit_reserve"]["value"] == 696_800_000
    assert attempt["recognized_fy2025_project_exit_reserve"]["value"] == 89_900_000
    assert attempt["maximum_fy2026_exit_cash"] == 925_000_000
    assert attempt["maximum_unrecognized_fy2026_excess"] == 228_200_000
    assert "already inside reported common equity" in attempt["double_count_prevention"]
    assert apd["governed_assumptions"]["ev_debt_bridge_applied"] is False


def test_apd_residual_income_scenarios_replay_exactly():
    apd = result("APD")
    for row in apd["scenario_rows"]:
        replay = residual_income_valuation(book_value_per_share=row["book_value_per_share"], current_roe=row["current_roe"], cost_of_equity=row["cost_of_equity"], current_payout_ratio=row["current_payout_ratio"], terminal_roe=row["terminal_roe"], terminal_growth=row["terminal_growth"], years=5)["intrinsic_value"]
        assert replay == pytest.approx(row["raw_value_per_share"])


def test_apd_public_contract_and_calculator_are_exact_and_safe():
    from app.us_valuation.calculator import calculate, calculator_view
    from app.us_valuation.batch_41 import BATCH_41_MANIFEST
    from run_batch_41_recovery import _apd_public

    issuer = next(row for row in BATCH_41_MANIFEST if row.ticker == "APD")
    private = result("APD")
    public = _apd_public(issuer, private)
    encoded = json.dumps(public)
    view = calculator_view(public)
    assert public["model_policy"]["primary"] == "residual_income"
    assert view["model_family"] == "residual_income" and view["can_calculate"]
    assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx(private["scenario_range"])
    higher = calculate(public, overrides={"discount_rate": view["defaults"]["discount_rate"] + 0.01}, manual_price=None)
    assert higher["result"]["base"] < private["scenario_range"]["base"]
    for key in ("source_ledger", "reported_inputs", "governed_assumptions", "recovery_attempt"):
        assert key not in encoded


def test_recovery_runner_pins_every_non_apd_artifact(tmp_path):
    from run_batch_41_recovery import run

    output = tmp_path / "recovery"
    report = run(initial_root=INITIAL, output_root=output, **KW)
    assert report["attempted_tickers"] == ["APD", "IFF", "IP"]
    assert report["recovered_to_conditional_tickers"] == ["APD"]
    assert report["still_withheld_tickers"] == ["IFF", "IP"]
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (0, 8, 2, 8)
    for ticker in ("AVY", "BALL", "ECL", "EQT", "HAL", "NUE", "PKG"):
        assert (output / "generated" / ticker / "valuation-private.json").read_bytes() == (INITIAL / "generated" / ticker / "valuation-private.json").read_bytes()
        assert (output / "staged-public" / f"{ticker}.json").read_bytes() == (INITIAL / "staged-public" / f"{ticker}.json").read_bytes()
    for ticker in ("IFF", "IP"):
        assert (output / "staged-public" / f"{ticker}.json").read_bytes() == (INITIAL / "staged-public" / f"{ticker}.json").read_bytes()
        private = json.loads((output / "generated" / ticker / "valuation-private.json").read_text())
        assert private["recovery"]["source_ledger"]["recovery_attempt"]["recovery_outcome"] == "withheld"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]


def test_recovery_runner_rejects_initial_report_drift(tmp_path):
    from run_batch_41_recovery import run

    initial = tmp_path / "initial"
    shutil.copytree(INITIAL, initial)
    report = json.loads((initial / "batch-41-report.json").read_text())
    report["withheld_count"] = 2
    (initial / "batch-41-report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="confirmed Batch 41"):
        run(initial_root=initial, output_root=tmp_path / "recovery", **KW)


def test_recovery_fails_closed_on_source_tampering(tmp_path):
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "APD", source / "APD")
    (source / "APD" / "companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_41_recovery_result(ticker="APD", **{**KW, "source_root": source})


def test_confirmed_initial_report_hash_is_pinned():
    assert hashlib.sha256((INITIAL / "batch-41-report.json").read_bytes()).hexdigest() == "a1d1825266595ac1ef84c75eded8f6c7cf511608703710a158827d4837c483f8"
