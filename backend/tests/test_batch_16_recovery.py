from __future__ import annotations

import json
from pathlib import Path
import sys

from app.us_valuation.batch_16 import BATCH_16_MANIFEST
from app.us_valuation.batch_16_recovery import BATCH_16_RECOVERY_TICKERS, build_batch_16_recovery_result

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-16-sec-source-packets-20260830"
STRUCTURAL = ROOT / "output/batch-16-structural-sources-20260830"
EVENT = ROOT / "output/batch-16-event-sources-20260830"
CONFIRMED_PUBLIC = ROOT / "output/batch-16-history/final-c/staged-public"


def _result(ticker):
    return build_batch_16_recovery_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT)


def test_batch_16_recovery_exact_denominator_and_outcomes():
    assert BATCH_16_RECOVERY_TICKERS == ("DXCM", "EW", "CRL", "ZBH", "COR", "ELV")
    rows = {ticker: _result(ticker) for ticker in BATCH_16_RECOVERY_TICKERS}
    assert all(row["availability_type"] == "not_available" for row in rows.values())
    assert all(row["scenario_range"] == {"low": None, "base": None, "high": None} for row in rows.values())
    assert all(row["source_ledger"]["recovery_source_exhaustion"]["recovery_outcome"] == "withheld" for row in rows.values())


def test_finite_subclaims_do_not_hide_unbounded_total_claim_sets():
    ew = _result("EW")["source_ledger"]["recovery_source_exhaustion"]
    assert ew["litigation_reserve"]["value"] == 56_900_000.
    assert ew["combined_litigation_and_insurance_reserve"]["value"] == 72_400_000.
    assert ew["remaining_valtech_balance"] is None
    cor = _result("COR")["source_ledger"]["recovery_source_exhaustion"]
    assert cor["total_recorded_opioid_accrual"]["value"] == 4_200_000_000.
    assert cor["current_recorded_opioid_accrual"]["value"] == 396_200_000.
    assert cor["loss_range_outside_accrual"] is None
    elv = _result("ELV")["source_ledger"]["recovery_source_exhaustion"]
    assert elv["cms_remaining_accrual"]["value"] == 593_000_000.
    assert elv["cms_adjustment_range_plus_minus_usd"] == 320_000_000.
    assert elv["doj_total_loss_range"] is None


def test_unbounded_recovery_fields_are_not_replaced_with_zero():
    dxcm = _result("DXCM")["source_ledger"]["recovery_source_exhaustion"]
    assert dxcm["current_claim_insurance_limit"] is None and dxcm["insurance_receivable"] is None
    crl = _result("CRL")["source_ledger"]["recovery_source_exhaustion"]
    assert crl["maximum_securities_exposure"] is None and crl["current_d_and_o_insurance_limit"] is None
    zbh = _result("ZBH")["source_ledger"]["recovery_source_exhaustion"]
    assert zbh["china_excess_loss_range"] is None and zbh["current_irs_proposed_adjustment_range"] is None


def test_batch_16_recovery_public_artifacts_are_safe_and_withheld():
    from run_batch_16_history import _public
    issuers = {issuer.ticker: issuer for issuer in BATCH_16_MANIFEST}
    for ticker in BATCH_16_RECOVERY_TICKERS:
        row = _result(ticker)
        public = _public(issuers[ticker], row)
        raw = json.dumps(public)
        assert public["availability_type"] == "not_available"
        assert public["review"]["publication_state"] == "withheld"
        assert "source_ledger" not in raw and "recovery_source_exhaustion" not in raw


def test_batch_16_recovery_runner_preserves_pre_bookkeeping_state(tmp_path):
    from run_batch_16_recovery import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, event_root=EVENT, confirmed_public_root=CONFIRMED_PUBLIC, output_root=tmp_path / "recovery")
    assert report["attempted_count"] == 6 and report["remaining_withheld_count"] == 6
    assert report["final_batch_counts"] == {"pass": 2, "conditional": 2, "withheld": 6, "numeric": 4}
    assert report["final_public_count"] == 10
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed_before_bookkeeping"] is False
    assert report["withheld_register_changed_before_bookkeeping"] is False
