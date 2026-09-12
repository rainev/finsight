from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_operating_claims import operating_claim_policy, select_operating_claim


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "AVY": ROOT / "output/batch-41-structural-sources-20260907/AVY/structural-filing.json",
    "BALL": ROOT / "output/batch-41-structural-sources-20260907/BALL/structural-filing.json",
    "MPC": ROOT / "output/batch-44-structural-sources-20260907/MPC/structural-filing.json",
}


def _source(ticker):
    structural = json.loads(SOURCES[ticker].read_text())
    filing = {
        "accessionNumber": structural["source_accession"],
        "reportDate": structural["report_date"],
        "filingDate": structural["filed_date"],
        "form": structural["form"],
    }
    policy = operating_claim_policy(ticker)
    return policy, structural, filing


def test_avy_keeps_three_balance_mechanisms_and_flows_disjoint_but_requires_review():
    policy, structural, filing = _source("AVY")
    result = select_operating_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "review_required" and result["claim_adjustment"] is None
    assert result["review_reasons"] == [
        "operating_reserves_and_acquisition_claim_lack_one_forward_cash_overlap_rule"
    ]
    assert result["components"] == {
        "restructuring_reserve": 19_400_000,
        "restructuring_charges": 34_400_000,
        "restructuring_cash_payments": 26_000_000,
        "restructuring_noncash_settlements": 3_100_000,
        "environmental_reserve": 9_400_000,
        "environmental_current_portion": 2_000_000,
        "environmental_cash_payments": 1_200_000,
        "environmental_charges": 600_000,
        "acquisition_contingent_consideration": 2_200_000,
    }


def test_ball_reconciles_benefit_aggregate_and_deducts_only_approved_components():
    policy, structural, filing = _source("BALL")
    result = select_operating_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 251_000_000
    assert result["components"]["nci_separate_bridge_claim"] == 20_000_000
    assert result["components"]["benefit_noncurrent_aggregate"] == 468_000_000
    assert result["components"]["pension_current"] + result["components"]["pension_noncurrent"] == 176_000_000
    assert (
        result["components"]["pension_noncurrent"]
        + result["components"]["postemployment_liability"]
        + result["components"]["deferred_compensation_operating"]
        + result["components"]["other_employee_liabilities_operating"]
        == result["components"]["benefit_noncurrent_aggregate"]
    )
    assert result["components"]["operating_restructuring_flow"] == 33_000_000
    assert result["components"]["pension_noncash_ocf_adjustment"] == -15_000_000
    assert result["components"]["pension_cash_contribution"] == 15_000_000


def test_mpc_preserves_gross_reserves_as_bear_stress_without_netting_recovery():
    policy, structural, filing = _source("MPC")
    result = select_operating_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["scenario_adjustments"] == {"bear": 1_656_000_000, "base": 0.0, "bull": 0.0}
    assert result["components"]["environmental_reserve_gross"] == 368_000_000
    assert result["components"]["environmental_recovery_not_netted"] == 4_000_000
    assert result["components"]["pension_benefits_paid"] == 8_000_000
    assert result["components"]["postretirement_benefits_paid"] == 28_000_000
    assert result["components"]["pension_postretirement_noncash_ocf_adjustment"] == 108_000_000
    assert result["components"]["equity_method_investment_not_surplus_cash"] == 7_197_000_000


@pytest.mark.parametrize("ticker", ["AVY", "BALL", "MPC"])
def test_operating_claim_rules_have_no_filing_amount_or_date_constants_and_reject_tampering(ticker):
    policy, structural, filing = _source(ticker)
    assert not {"accession", "filed_date", "period_end", "amount"} & set(policy)
    changed = copy.deepcopy(policy)
    changed["version"] = "tampered"
    with pytest.raises(RuntimeError, match="identity/version mismatch"):
        select_operating_claim(changed, structural, filing, policy["cik"], "2026-08-14")


def test_ball_aggregate_component_drift_fails_closed():
    policy, structural, filing = _source("BALL")
    changed = copy.deepcopy(structural)
    row = next(
        item for item in changed["facts"]
        if item.get("qname") == policy["deferred_compensation_qname"]
        and item.get("period_end") == filing["reportDate"]
        and item.get("period_start") is None
        and not item.get("dimensions")
    )
    row["value"] += 1
    with pytest.raises(ValueError, match="aggregate does not reconcile"):
        select_operating_claim(policy, changed, filing, policy["cik"], "2026-08-14")


def test_mpc_recovery_cannot_silently_reduce_bear_stress():
    policy, structural, filing = _source("MPC")
    changed = copy.deepcopy(structural)
    row = next(
        item for item in changed["facts"]
        if item.get("qname") == policy["environmental_recovery_qname"]
        and item.get("period_end") == filing["reportDate"]
    )
    row["value"] = 200_000_000
    result = select_operating_claim(policy, changed, filing, policy["cik"], "2026-08-14")
    assert result["scenario_adjustments"]["bear"] == 1_656_000_000
    assert result["components"]["environmental_recovery_not_netted"] == 200_000_000
