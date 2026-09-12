import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_claim_policies import ADP_CLAIM_POLICY, build_adp_claim_policy, capex_alias_spec, select_current_claims


ROOT = Path(__file__).parents[2]
STRUCTURAL = ROOT / "output" / "batch-18-structural-replay-a" / "ADP" / "structural-filing.json"
ACCESSION = "0000008670-26-000030"
CONTROLLING = {"accession": ACCESSION, "period_end": "2026-06-30"}


def _structural() -> dict:
    return json.loads(STRUCTURAL.read_text())


def test_adp_current_claims_replay_source_bound_475_7m_overlay() -> None:
    result = select_current_claims(ADP_CLAIM_POLICY, _structural(), CONTROLLING, "0000008670", "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["preferred_equity"] == 475_700_000.0
    assert result["reported_preferred_equity"] == 0.0
    assert result["raw_components"] == {
        "funds_held": 43_957_800_000.0,
        "client_obligations": 44_415_500_000.0,
        "legal_accrual": 48_000_000.0,
        "legal_receivable": 30_000_000.0,
    }
    assert result["derived_components"] == {"client_funds_shortfall": 457_700_000.0, "net_legal_claim": 18_000_000.0}
    assert result["sources"]["funds_held"]["namespace"] == "http://www.adp.com/20260630"
    assert result["sources"]["funds_held"]["source_accession"] == ACCESSION
    assert "not issuer-owned surplus cash" in result["scope_narrative"]


def test_adp_capex_alias_is_current_config_plus_issuer_concept() -> None:
    alias = capex_alias_spec()
    assert alias["field"] == "capital_expenditures"
    assert alias["unit"] == "USD"
    assert alias["kind"] == "flow"
    assert "PaymentsToAcquireOtherPropertyPlantAndEquipment" in alias["concepts"]
    assert alias["amount_fit_forbidden"] is True
    assert build_adp_claim_policy()["capex_alias"] == alias


@pytest.mark.parametrize("field,new_value,reason", [
    ("ClientFundsObligations", 43_000_000_000.0, "client_funds_shortfall_negative"),
    ("LossContingencyReceivable", 60_000_000.0, "net_legal_claim_negative"),
])
def test_adp_negative_derived_claim_is_reviewed_not_clamped(field: str, new_value: float, reason: str) -> None:
    structural = _structural()
    for row in structural["facts"]:
        if row.get("local_name") == field and row.get("period_end") == "2026-06-30":
            row["value"] = new_value
    result = select_current_claims(ADP_CLAIM_POLICY, structural, CONTROLLING, "0000008670", "2026-08-14")
    assert result["status"] == "review_required"
    assert reason in result["review_reasons"]
    assert result["preferred_equity"] is None
    assert result["claim_adjustment"] is None


def test_adp_identity_and_namespace_mismatches_block_binding() -> None:
    with pytest.raises(ValueError, match="accession"):
        select_current_claims(ADP_CLAIM_POLICY, _structural(), {**CONTROLLING, "accession": "0000008670-26-999999"}, "0000008670", "2026-08-14")
    with pytest.raises(ValueError, match="CIK"):
        select_current_claims(ADP_CLAIM_POLICY, _structural(), CONTROLLING, "0000008671", "2026-08-14")
    structural = _structural()
    for row in structural["facts"]:
        if row.get("local_name") == "FundsHeldClients" and row.get("period_end") == "2026-06-30":
            row["namespace"] = "http://www.adp.com/oldprefix"
    with pytest.raises(ValueError, match="FundsHeldClients"):
        select_current_claims(ADP_CLAIM_POLICY, structural, CONTROLLING, "0000008670", "2026-08-14")


def test_adp_duplicate_conflicting_source_values_are_not_silently_deduped() -> None:
    structural = _structural()
    source = next(row for row in structural["facts"] if row.get("local_name") == "FundsHeldClients" and row.get("period_end") == "2026-06-30")
    conflicting = copy.deepcopy(source)
    conflicting["value"] = source["value"] + 1.0
    structural["facts"].append(conflicting)
    with pytest.raises(ValueError, match="ambiguous"):
        select_current_claims(ADP_CLAIM_POLICY, structural, CONTROLLING, "0000008670", "2026-08-14")
