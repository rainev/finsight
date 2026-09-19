from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_biib_scope import assess_biib_scope, biib_scope_policy
from app.us_valuation.refresh_bridge_scope_policies import (
    PREFERRED_EQUITY_ZERO_RULES,
    preferred_equity_zero_availability,
)


ROOT = Path(__file__).resolve().parents[2]
STRUCTURAL = ROOT / "output/batch-14-structural-sources-20260829/BIIB/structural-filing.json"
CONTROLLING = {
    "accessionNumber": "0000875045-26-000075",
    "reportDate": "2026-06-30",
    "filingDate": "2026-07-29",
}


def _packet() -> dict:
    return json.loads(STRUCTURAL.read_text())


def _run(packet: dict | None = None) -> dict:
    return assess_biib_scope(biib_scope_policy(), packet or _packet(), CONTROLLING,
                             "0000875045", "2026-08-14")


def test_biib_legal_and_apellis_scope_is_bound_without_numeric_successor():
    result = _run()
    assert result["status"] == "review_required"
    assert result["claim_adjustment"] is None
    assert result["numeric_successor_issued"] is False
    assert result["review_reasons"] == [
        "genentech_judgment_current_carrying_scope_unresolved",
        "genentech_judgment_payment_interest_and_recovery_scope_unresolved",
        "apellis_comparable_post_acquisition_cash_flow_not_reported",
        "apellis_integration_payment_scope_not_exclusive",
        "pending_raythera_transaction_cutoff_status_not_captured",
    ]
    legal = result["legal_scope"]
    assert legal["judgment_amount"] == 124_300_000
    assert legal["current_carrying_rows"] == []
    assert legal["current_legal_payment_rows"] == []
    assert legal["current_unscoped_litigation_expense"] == 4_300_000
    assert legal["insurance_or_indemnification_recovery"] is None
    assert legal["judgment_interest"] is None

    acquisition = result["acquisition_scope"]
    assert acquisition["total_consideration"] == 5_410_100_000
    assert acquisition["cash_consideration_paid_or_payable"] == 5_406_000_000
    assert acquisition["acquired_cash"] == 310_700_000
    assert acquisition["reported_net_acquisition_cash"] == 5_065_100_000
    assert acquisition["cash_consideration_timing_difference"] == 30_200_000
    assert acquisition["term_loan_funding"] == 2_000_000_000
    assert acquisition["revolver_funding"] == 400_000_000
    assert acquisition["period_end_cash"] == 1_285_000_000
    assert acquisition["period_end_current_debt"] == 800_000_000
    assert acquisition["period_end_noncurrent_debt"] == 7_290_300_000
    assert acquisition["period_end_total_debt"] == 8_090_300_000
    assert acquisition["integration_charge"] == 153_200_000
    assert acquisition["current_workforce_restructuring_payments"] == 153_500_000
    assert acquisition["pending_transaction"] == {
        "status": "narrative_only_not_machine_bound",
        "upfront_upon_closing": None,
        "contingent_maximum": None,
        "current_claim": None,
    }
    assert acquisition["reported_product_revenue"] == {
        "SYFOVREMember": 97_400_000,
        "EMPAVELIMember": 30_400_000,
    }
    assert acquisition["pro_forma_rows"] == []
    assert acquisition["acquired_operating_cash_rows"] == []
    assert acquisition["acquired_fcff"] is None and acquisition["synergies"] is None


def test_biib_missing_judgment_does_not_become_zero():
    packet = deepcopy(_packet())
    packet["facts"] = [row for row in packet["facts"] if not (
        row.get("qname") == "us-gaap:LossContingencyDamagesSoughtValue"
        and "GenentechMember" in json.dumps(row.get("dimensions") or []))]
    with pytest.raises(ValueError, match="Genentech judgment"):
        _run(packet)


def test_biib_missing_acquired_cash_or_funding_fails_closed():
    packet = deepcopy(_packet())
    packet["facts"] = [row for row in packet["facts"] if not (
        row.get("qname") == "us-gaap:BusinessCombinationRecognizedIdentifiableAssetsAcquiredAndLiabilitiesAssumedCashAndEquivalents"
        and "ApellisPharmaceuticalsInc.Member" in json.dumps(row.get("dimensions") or []))]
    with pytest.raises(ValueError, match="Apellis acquired cash"):
        _run(packet)


def test_biib_policy_contains_no_amounts_or_filing_dates():
    encoded = json.dumps(biib_scope_policy(), sort_keys=True)
    assert "2026-" not in encoded and "2025-" not in encoded
    assert "124300000" not in encoded and "5410100000" not in encoded


def test_compiled_biib_policy_migrates_legacy_preferred_claims_exactly_once():
    policy = json.loads((ROOT / "output/us-refresh-runtime/refresh-policies.json").read_text())["BIIB"]
    assert json.dumps(policy["inputs"]["biib_legal_operating_scope_review"]["policy"], sort_keys=True) == json.dumps(biib_scope_policy(), sort_keys=True)
    for case in ("bear", "base", "bull"):
        bindings = policy["scenario_bindings"][case]
        assert bindings["preferred_equity"] == f"{case}_preferred_equity"
        assert bindings["nonoperating_adjustment"] == {"subtract": [0.0, "pharma_acquisition_claim"]}
    assert policy["baseline_non_debt_claims"] == {
        "bear": {"preferred_equity": 397_800_000.0, "noncontrolling_interests": 0.0, "nonoperating_adjustment": 0.0},
        "base": {"preferred_equity": 335_650_000.0, "noncontrolling_interests": 0.0, "nonoperating_adjustment": 0.0},
        "bull": {"preferred_equity": 273_500_000.0, "noncontrolling_interests": 0.0, "nonoperating_adjustment": 0.0},
    }


def test_biib_preferred_zero_is_reconciled_from_current_common_equity():
    availability, proof = preferred_equity_zero_availability(
        ticker="BIIB", policy=dict(PREFERRED_EQUITY_ZERO_RULES["BIIB"]),
        structural_packet=_packet(), accession=CONTROLLING["accessionNumber"],
        period_end=CONTROLLING["reportDate"])
    assert availability.value == 0
    assert proof["parent_equity"] == 18_848_000_000
    assert proof["component_sum"] == 18_848_000_000
    assert proof["rounding_residual"] == 0
