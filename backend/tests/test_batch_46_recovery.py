import json
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_46 import BATCH_46_MANIFEST
from app.us_valuation.batch_46_recovery import ATTEMPTED_TICKERS, RECOVERY_VERSION, recover_batch_46_withheld

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
INITIAL = ROOT / "output/batch-46-history-run-b-20260908"
SOURCES = ROOT / "output/batch-46-sec-source-packets-20260908"
STRUCTURAL = ROOT / "output/batch-46-structural-sources-20260908"
EXPECTED_DIAGNOSTIC = {
    "EIX": (60.839790067937344, 69.6095225107413, 81.54048939375323),
    "AES": (11.973136931375038, 13.49518441635956, 15.555565715921787),
    "PCG": (12.32038092738213, 14.260813695313198, 16.908797468915388),
    "SRE": (36.15136589181951, 41.82857628336423, 49.57526420367392),
}
EXPECTED_PUBLISHED = {
    "EIX": (29.722566995886645, 52.859390122095874, 77.26517939093048),
    "AES": (10.58466094385518, 12.012177285883622, 13.949350043758681),
    "PCG": (8.938569331952573, 15.036381569753571, 22.09041086238211),
    "SRE": (36.15136589181951, 41.82857628336423, 49.57526420367392),
}


@lru_cache(None)
def recovered(ticker: str):
    initial = json.loads((INITIAL / "generated" / ticker / "valuation-private.json").read_text())["history_backed"]
    facts = json.loads((SOURCES / ticker / "companyfacts.json").read_text())
    structural = json.loads((STRUCTURAL / ticker / "structural-filing.json").read_text())
    return recover_batch_46_withheld(initial=initial, facts=facts, structural=structural)


def test_all_four_consume_one_attempt_and_publish_conditional_low() -> None:
    assert ATTEMPTED_TICKERS == ("EIX", "AES", "PCG", "SRE")
    for ticker in ATTEMPTED_TICKERS:
        row = recovered(ticker)
        attempt = row["source_ledger"]["recovery_attempt"]
        assert row["model_version"] == RECOVERY_VERSION
        assert row["availability_type"] == "conditional_estimate"
        assert tuple(row["scenario_range"][key] for key in ("low", "base", "high")) == pytest.approx(EXPECTED_PUBLISHED[ticker])
        assert row["history_reliability"]["label"] == "Low"
        assert attempt["attempt_number"] == 1 and attempt["decision"] == "conditional_numeric_low"
        assert attempt["final_availability_type"] == "conditional_estimate"
        assert attempt["zero_substitution_used"] is False
        assert attempt["former_hard_blockers"] and attempt["release_condition"]


def test_private_residual_diagnostics_replay_but_are_not_publishable() -> None:
    for ticker in ATTEMPTED_TICKERS:
        diagnostic = recovered(ticker)["source_ledger"]["recovery_attempt"]["private_pre_authorized_diagnostic"]
        observed = tuple(row["value_per_share"] for row in diagnostic["scenario_rows"])
        assert observed == pytest.approx(EXPECTED_DIAGNOSTIC[ticker])
        assert diagnostic["diagnostic_only"] is True and diagnostic["publication_eligible"] is False


def test_eix_and_pcg_claim_evidence_is_exact_and_not_misread_as_a_cap() -> None:
    eix = recovered("EIX")["source_ledger"]["recovery_attempt"]["reported_recovery_evidence"]
    assert eix["wildfire_accrual"]["value"] == 1_434_000_000
    assert eix["wildfire_loss_h1"]["value"] == 512_000_000
    assert eix["expected_wildfire_fund_recovery_h1"]["value"] == 511_000_000
    assert eix["wildfire_fund_maximum_liability_context"]["value"] == 4_300_000_000
    assert eix["wildfire_fund_claim_paying_capacity_context"]["value"] == 21_000_000_000
    assert "not a complete ceiling" in eix["non_overlap_conclusion"]
    pcg = recovered("PCG")["source_ledger"]["recovery_attempt"]["reported_recovery_evidence"]
    assert pcg["wildfire_related_claims"]["value"] == 309_000_000
    assert pcg["dixie_possible_loss"]["value"] == 2_250_000_000
    assert pcg["dixie_settlement"]["value"] == 2_049_000_000
    assert pcg["dixie_wildfire_fund_receivable"]["value"] == 244_000_000
    assert pcg["regulatory_disallowance_cap_context"]["value"] == 5_100_000_000
    assert "do not form a mutually exclusive ceiling" in pcg["non_overlap_conclusion"]


def test_aes_and_sre_scope_evidence_is_source_linked() -> None:
    aes = recovered("AES")["source_ledger"]["recovery_attempt"]["reported_recovery_evidence"]
    assert aes["ttm_gain_on_sale_of_business"]["value"] == 198_000_000
    assert aes["ttm_asset_impairment_charges"]["value"] == 474_000_000
    assert aes["reported_nci"]["value"] == 4_830_000_000
    assert aes["reported_temporary_or_redeemable_equity"]["value"] == 3_052_000_000
    sre = recovered("SRE")["source_ledger"]["recovery_attempt"]["reported_recovery_evidence"]
    assert sre["si_partners_held_for_sale_assets"]["value"] == 32_939_000_000
    assert sre["si_partners_held_for_sale_liabilities"]["value"] == 12_992_000_000
    assert sre["si_partners_noncurrent_debt"]["value"] == 9_027_000_000
    assert (sre["ecogas_expected_gain_low"]["value"], sre["ecogas_expected_gain_high"]["value"]) == (165_000_000, 205_000_000)
    assert (sre["ecogas_parent_after_tax_gain_low"]["value"], sre["ecogas_parent_after_tax_gain_high"]["value"]) == (57_000_000, 77_000_000)


def test_recovered_public_artifacts_are_conditional_low_and_private_safe() -> None:
    from app.us_valuation.calculator import calculate, calculator_view
    from run_batch_46_history import _public

    issuers = {row.ticker: row for row in BATCH_46_MANIFEST}
    for ticker in ATTEMPTED_TICKERS:
        public = _public(issuers[ticker], recovered(ticker))
        assert public["availability_type"] == "conditional_estimate"
        assert public["scenario_range"]["base"] == pytest.approx(EXPECTED_PUBLISHED[ticker][1])
        assert public["reliability"]["label"] == "Low"
        assert public["model_policy"]["primary"] == "residual_income"
        assert calculator_view(public)["can_calculate"]
        calculated = calculate(public, overrides={}, manual_price=None)["result"]
        assert tuple(calculated[key] for key in ("low", "base", "high")) == pytest.approx(tuple(public["scenario_range"][key] for key in ("low", "base", "high")))
        encoded = json.dumps(public)
        for key in ("recovery_attempt", "private_pre_authorized_diagnostic", "reported_recovery_evidence", "reported_inputs", "source_ledger"):
            assert key not in encoded


def test_recovery_runner_is_scoped_and_preserves_protected_state(tmp_path: Path) -> None:
    from run_batch_46_recovery import run

    report = run(initial_root=INITIAL, source_root=SOURCES, structural_root=STRUCTURAL, output_root=tmp_path / "recovery")
    assert (report["recovery_attempt_count"], report["recovered_to_conditional_count"], report["still_withheld_count"]) == (4, 4, 0)
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (0, 10, 0, 10)
    assert report["attempted_recovery_tickers"] == list(ATTEMPTED_TICKERS)
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
    assert (tmp_path / "recovery/staged-public/ATO.json").read_bytes() == (INITIAL / "staged-public/ATO.json").read_bytes()


def test_recovery_source_drift_fails_closed(tmp_path: Path) -> None:
    from run_batch_46_recovery import run

    source = tmp_path / "sources"
    shutil.copytree(SOURCES, source)
    (source / "EIX/companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="source drifted"):
        run(initial_root=INITIAL, source_root=source, structural_root=STRUCTURAL, output_root=tmp_path / "recovery")
