import json
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_47 import BATCH_47_MANIFEST
from app.us_valuation.batch_47_recovery import ATTEMPTED_TICKERS, RECOVERY_VERSION, recover_batch_47_withheld

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
INITIAL = ROOT / "output/batch-47-history-run-b-20260908"
SOURCES = ROOT / "output/batch-47-sec-source-packets-20260908"
STRUCTURAL = ROOT / "output/batch-47-structural-sources-run-b-20260908"
EXPECTED_DIAGNOSTIC = {
    "NRG": (29.954968639776617, 34.03576496630482, 39.5757088228311),
    "VST": (21.30379535026372, 23.669713249602278, 26.851710920910353),
    "CEG": (109.81558070257338, 126.50729448105105, 149.25836854186022),
}


@lru_cache(None)
def recovered(ticker: str):
    initial = json.loads((INITIAL / "generated" / ticker / "valuation-private.json").read_text())["history_backed"]
    facts = json.loads((SOURCES / ticker / "companyfacts.json").read_text())
    structural = json.loads((STRUCTURAL / ticker / "structural-filing.json").read_text())
    return recover_batch_47_withheld(initial=initial, facts=facts, structural=structural)


def test_all_three_consume_one_attempt_and_remain_withheld() -> None:
    assert ATTEMPTED_TICKERS == ("NRG", "VST", "CEG")
    for ticker in ATTEMPTED_TICKERS:
        row = recovered(ticker)
        attempt = row["source_ledger"]["recovery_attempt"]
        assert row["model_version"] == RECOVERY_VERSION
        assert row["availability_type"] == "not_available"
        assert row["scenario_range"] == {"low": None, "base": None, "high": None}
        assert attempt["attempt_number"] == 1 and attempt["decision"] == "withheld"
        assert attempt["final_availability_type"] == "not_available"
        assert attempt["zero_substitution_used"] is False
        assert attempt["hard_blockers"] == ("MODEL_UNSUPPORTED",)


def test_private_diagnostics_are_exact_but_never_publishable() -> None:
    for ticker in ATTEMPTED_TICKERS:
        diagnostic = recovered(ticker)["source_ledger"]["recovery_attempt"]["private_residual_income_diagnostic"]
        assert tuple(row["value_per_share"] for row in diagnostic["scenario_rows"]) == pytest.approx(EXPECTED_DIAGNOSTIC[ticker])
        assert diagnostic["diagnostic_only"] is True and diagnostic["publication_eligible"] is False


def test_nrg_vst_and_ceg_recovery_evidence_is_source_linked() -> None:
    nrg = recovered("NRG")["source_ledger"]["recovery_attempt"]["reported_recovery_evidence"]
    assert nrg["earnings_event"]["reported_facts"]["post_balance_common_repurchases_through_2026_07_31"] == 932_000_000
    assert nrg["earnings_event"]["reported_facts"]["post_balance_common_dividends_through_2026_07_31"] == 202_000_000
    assert nrg["pjm_capacity_event"]["reported_facts"]["cleared_capacity_mw"] == 6_839
    vst = recovered("VST")["source_ledger"]["recovery_attempt"]["reported_recovery_evidence"]
    assert vst["earnings_event"]["reported_facts"]["q2_2026_unrealized_hedge_loss"] == 472_000_000
    assert vst["current_equity_and_claims"]["preferred_equity"]["value"] == 2_476_000_000
    ceg = recovered("CEG")["source_ledger"]["recovery_attempt"]["reported_recovery_evidence"]
    assert ceg["ttm_unrealized_derivative_gain"]["value"] == 132_000_000
    assert ceg["h1_acquisition_cash"]["value"] == 2_537_000_000
    assert ceg["h1_long_term_debt_issuance"]["value"] == 5_001_000_000
    assert ceg["h1_short_term_debt_issuance"]["value"] == 4_500_000_000


def test_recovered_public_artifacts_remain_withheld_and_private_safe() -> None:
    from app.us_valuation.calculator import calculator_view
    from run_batch_47_history import _public

    issuers = {row.ticker: row for row in BATCH_47_MANIFEST}
    for ticker in ATTEMPTED_TICKERS:
        public = _public(issuers[ticker], recovered(ticker))
        assert public["availability_type"] == "not_available"
        assert public["scenario_range"]["base"] is None
        assert public["model_policy"]["primary"] == "residual_income"
        assert not calculator_view(public)["can_calculate"]
        encoded = json.dumps(public)
        for key in ("recovery_attempt", "private_residual_income_diagnostic", "reported_recovery_evidence", "reported_inputs", "source_ledger"):
            assert key not in encoded


def test_recovery_runner_is_scoped_and_preserves_protected_state(tmp_path: Path) -> None:
    from run_batch_47_recovery import run

    report = run(initial_root=INITIAL, source_root=SOURCES, structural_root=STRUCTURAL, output_root=tmp_path / "recovery")
    assert (report["recovery_attempt_count"], report["recovered_to_conditional_count"], report["still_withheld_count"]) == (3, 0, 3)
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (0, 7, 3, 7)
    assert report["attempted_recovery_tickers"] == list(ATTEMPTED_TICKERS)
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
    assert (tmp_path / "recovery/staged-public/ED.json").read_bytes() == (INITIAL / "staged-public/ED.json").read_bytes()


def test_recovery_source_drift_fails_closed(tmp_path: Path) -> None:
    from run_batch_47_recovery import run

    source = tmp_path / "sources"
    shutil.copytree(SOURCES, source)
    (source / "NRG/companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="source drifted"):
        run(initial_root=INITIAL, source_root=source, structural_root=STRUCTURAL, output_root=tmp_path / "recovery")
