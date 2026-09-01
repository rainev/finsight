from __future__ import annotations

import json
from pathlib import Path
import sys

from app.us_valuation.batch_15 import BATCH_15_MANIFEST
from app.us_valuation.batch_15_recovery import BATCH_15_RECOVERY_TICKERS, build_batch_15_recovery_result

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-15-sec-source-packets-20260830"
STRUCTURAL = ROOT / "output/batch-15-structural-sources-20260830"
RECOVERY_SOURCE = ROOT / "output/batch-15-recovery-sources-20260830"
CONFIRMED_PUBLIC = ROOT / "output/batch-15-history/final-a/staged-public"


def _result(ticker):
    return build_batch_15_recovery_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL, recovery_source_root=RECOVERY_SOURCE)


def test_batch_15_recovery_exact_denominator_and_outcomes():
    assert BATCH_15_RECOVERY_TICKERS == ("LH", "ISRG", "ALGN")
    rows = {ticker: _result(ticker) for ticker in BATCH_15_RECOVERY_TICKERS}
    assert all(row["availability_type"] == "not_available" for row in rows.values())
    assert all(row["scenario_range"] == {"low": None, "base": None, "high": None} for row in rows.values())
    assert all(row["history_reliability"] is None for row in rows.values())


def test_lh_bounded_doj_subclaim_does_not_hide_unbounded_total_claims():
    row = _result("LH")
    evidence = row["source_ledger"]["recovery_source_exhaustion"]
    doj = evidence["doj_subclaim"]
    assert doj["reported_terms"]["principal_usd"] == 14_500_000
    assert doj["reported_terms"]["annual_interest_rate"] == .045
    assert doj["cutoff_principal_plus_interest_usd"] > 15_000_000
    assert [source["value"] for source in evidence["ravgen_award_sources"]] == [272_000_000., 100_000_000., 2_600_000., 100.]
    assert all(item["amount_or_range"] is None for item in evidence["class_settlements_without_amounts"])
    assert {item["matter"] for item in evidence["additional_unbounded_current_matters"]} == {"Davis/Vargas certified ADA class action", "Raymond Eugenio AMCA shareholder-derivative action"}
    assert evidence["management_assessed_other_matters"]["used_to_bound_specifically_described_matters"] is False
    assert evidence["recovery_outcome"] == "withheld"


def test_isrg_and_algn_do_not_invent_claim_bounds():
    isrg = _result("ISRG")["source_ledger"]["recovery_source_exhaustion"]
    assert isrg["allocated_legal_reserve"] is None
    assert isrg["current_insurance_limit"] is None
    assert len(isrg["unbounded_current_matters"]) == 4
    algn = _result("ALGN")["source_ledger"]["recovery_source_exhaustion"]
    assert algn["eu_investigation"]["case_identifier"] == "AT.40900"
    assert algn["eu_investigation"]["opened"] == "2026-06-30"
    assert algn["eu_regulation_1_2003_article_23"]["indicative_turnover_reference_usd"] == 403_496_400.
    assert "not a guaranteed" in algn["eu_regulation_1_2003_article_23"]["scope"]
    assert len(algn["unbounded_outside_eu_fine"]) == 6
    assert algn["unused_revolver_is_not_debt"] is True


def test_batch_15_recovery_public_artifacts_are_safe_and_withheld():
    from run_batch_15_history import _public
    issuers = {issuer.ticker: issuer for issuer in BATCH_15_MANIFEST}
    for ticker in BATCH_15_RECOVERY_TICKERS:
        row = _result(ticker)
        public = _public(issuers[ticker], row)
        raw = json.dumps(public)
        assert public["availability_type"] == "not_available"
        assert public["scenario_range"] == {"low": None, "base": None, "high": None, "label": "assumption range, not a statistical confidence interval or recommendation"}
        assert public["review"]["publication_state"] == "withheld"
        assert "source_ledger" not in raw and "recovery_source_exhaustion" not in raw and "reported_inputs" not in raw


def test_batch_15_recovery_runner_preserves_pre_bookkeeping_state(tmp_path):
    from run_batch_15_recovery import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, recovery_source_root=RECOVERY_SOURCE, confirmed_public_root=CONFIRMED_PUBLIC, output_root=tmp_path / "recovery")
    assert report["attempted_count"] == 3
    assert report["remaining_withheld_count"] == 3
    assert report["final_batch_counts"] == {"pass": 4, "conditional": 3, "withheld": 3, "numeric": 7}
    assert report["final_public_count"] == 10
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed_before_bookkeeping"] is False
    assert report["withheld_register_changed_before_bookkeeping"] is False
