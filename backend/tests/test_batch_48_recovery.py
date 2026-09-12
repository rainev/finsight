import json
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_48 import BATCH_48_MANIFEST
from app.us_valuation.batch_48_recovery import ATTEMPTED_TICKERS, RECOVERY_VERSION, recover_batch_48_withheld

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
INITIAL = ROOT / "output/batch-48-history-run-p-20260911"
SOURCES = ROOT / "output/batch-48-sec-source-packets-20260911"


@lru_cache(None)
def recovered(ticker: str):
    initial = json.loads((INITIAL / "generated" / ticker / "valuation-private.json").read_text())["history_backed"]
    facts = json.loads((SOURCES / ticker / "companyfacts.json").read_text())
    return recover_batch_48_withheld(initial=initial, facts=facts)


def test_recovery_scope_and_exact_outcomes() -> None:
    assert ATTEMPTED_TICKERS == ("WY", "EQR")
    wy, eqr = recovered("WY"), recovered("EQR")
    assert wy["model_version"] == eqr["model_version"] == RECOVERY_VERSION
    assert wy["availability_type"] == "conditional_estimate"
    assert wy["scenario_range"] == pytest.approx({"low": 5.507164856114062, "base": 8.4, "high": 11.8})
    assert wy["history_reliability"]["label"] == "Low"
    assert eqr["availability_type"] == "not_available"
    assert eqr["scenario_range"] == {"low": None, "base": None, "high": None}


def test_wy_cash_return_evidence_and_ddm_replay() -> None:
    wy = recovered("WY")
    evidence = wy["source_ledger"]["cash_return_evidence"]
    assert evidence["h1_adjusted_fad"]["value"] == 265_000_000
    assert evidence["cash_return_target"]["low"] == 0.75 and evidence["cash_return_target"]["high"] == 0.80
    assert [row["value"] for row in evidence["annual_dividend_history"]] == [1.18, 2.17, 1.66, 0.94, 0.84]
    assert evidence["h1_diluted_weighted_shares"]["value"] == 721_787_000
    for scenario in wy["scenario_rows"]:
        assert scenario["conditional_value_per_share"] == pytest.approx(scenario["owner_distribution_per_share"] / 0.10)
        assert scenario["raw_value_per_share"] > 0
    attempt = wy["source_ledger"]["recovery_attempt"]
    assert attempt["attempt_number"] == 1 and attempt["zero_substitution_used"] is False
    assert wy["source_ledger"]["rejected_initial_fcff_diagnostic"]["published"] is False


def test_eqr_recovery_keeps_both_diagnostics_private_and_withholds() -> None:
    eqr = recovered("EQR")
    attempt = eqr["source_ledger"]["recovery_attempt"]
    assert attempt["attempt_number"] == 1 and attempt["decision"] == "withheld"
    assert attempt["hard_blockers"] == ("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED")
    standalone = eqr["source_ledger"]["standalone_preclose_diagnostic"]
    combined = eqr["source_ledger"]["combined_proforma_diagnostic"]
    assert not standalone["publication_eligible"] and not combined["publication_eligible"]
    assert standalone["scenario_values"] == pytest.approx({"bear": 46.43493950921436, "base": 49.63734913053946, "bull": 53.31418980687576})
    assert combined["fixed_exchange_ratio"] == 2.793
    assert combined["h1_2026_diluted_shares"] == 779_245_000


def test_recovered_public_contract_and_exact_calculator() -> None:
    from app.us_valuation.artifacts import sanitize_public_artifact
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_48_history import _public as initial_public
    from run_batch_48_recovery import _wy_public

    issuers = {row.ticker: row for row in BATCH_48_MANIFEST}
    wy_public = _wy_public(issuers["WY"], recovered("WY"))
    assert wy_public["model_policy"]["primary"] == "total_payout_ddm"
    assert wy_public["primary_valuation_method"] == "timber_total_payout_ddm"
    assert wy_public["availability_type"] == "conditional_estimate"
    assert sanitize_public_artifact(wy_public) == wy_public
    view = calculator_view(wy_public)
    assert view["model_family"] == "distribution_ddm" and view["can_calculate"]
    assert calculate(wy_public, overrides={}, manual_price=None)["result"] == pytest.approx({key: wy_public["scenario_range"][key] for key in ("low", "base", "high")})
    with pytest.raises(ValueError, match="locked source-derived input"):
        calculate(wy_public, overrides={"owner_distribution_per_share": 1.0}, manual_price=None)
    assert calculate(wy_public, overrides={"discount_rate": 0.11}, manual_price=None)["result"]["base"] < wy_public["scenario_range"]["base"]
    eqr_public = initial_public(issuers["EQR"], recovered("EQR"))
    assert eqr_public["availability_type"] == "not_available" and eqr_public["scenario_range"]["base"] is None
    assert not calculator_view(eqr_public)["can_calculate"]
    encoded = json.dumps({"WY": wy_public, "EQR": eqr_public})
    for key in ("recovery_attempt", "cash_return_evidence", "standalone_preclose_diagnostic", "combined_proforma_diagnostic", "reported_inputs", "source_ledger"):
        assert key not in encoded


def test_recovery_runner_is_scoped_and_preserves_protected_state(tmp_path: Path) -> None:
    from run_batch_48_recovery import run

    report = run(initial_root=INITIAL, source_root=SOURCES, output_root=tmp_path / "recovery")
    assert (report["recovery_attempt_count"], report["recovered_to_conditional_count"], report["still_withheld_count"]) == (2, 1, 1)
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (0, 9, 1, 9)
    assert report["attempted_recovery_tickers"] == ["WY", "EQR"] and report["still_withheld_tickers"] == ["EQR"]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
    assert (tmp_path / "recovery/staged-public/FRT.json").read_bytes() == (INITIAL / "staged-public/FRT.json").read_bytes()
    eqr_public = json.loads((tmp_path / "recovery/staged-public/EQR.json").read_text())
    assert eqr_public["review"]["confidence_grade"] == "withheld"
    assert eqr_public["public_assumptions"]["forecast_policy_version"] == RECOVERY_VERSION


def test_recovery_source_drift_fails_closed(tmp_path: Path) -> None:
    from run_batch_48_recovery import run

    source = tmp_path / "sources"
    shutil.copytree(SOURCES, source)
    (source / "WY/companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="source drifted"):
        run(initial_root=INITIAL, source_root=source, output_root=tmp_path / "recovery")
