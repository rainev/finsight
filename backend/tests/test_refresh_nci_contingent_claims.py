from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_acquisition_claims import nci_contingent_claim_policy, select_acquisition_claim
from app.us_valuation.refresh_litigation_claims import litigation_claim_policy, select_litigation_claim
from app.us_valuation.refresh_operating_policies import _policy_for_entry
from app.us_valuation.refresh_preferred_lifecycle import bind_preferred_lifecycle, preferred_lifecycle_policy
from app.us_valuation.refresh_reported_claim_scope import (
    ClaimScopeReviewRequired,
    REPORTED_NCI_SCOPE_RULES,
    reported_nci_field_availability,
)
from app.us_valuation.xbrl import load_concept_config


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "DVA": ROOT / "output/batch-15-structural-sources-20260830/DVA/structural-filing.json",
    "CRL": ROOT / "output/batch-16-structural-sources-20260830/CRL/structural-filing.json",
    "ZBH": ROOT / "output/batch-16-structural-sources-20260830/ZBH/structural-filing.json",
}


def _source(ticker: str):
    structural = json.loads(SOURCES[ticker].read_bytes())
    filing = {
        "accessionNumber": structural["source_accession"],
        "reportDate": structural["report_date"],
        "filingDate": structural["filed_date"],
        "form": structural["form"],
    }
    return structural, filing


def _forbidden_policy_keys(value):
    if isinstance(value, dict):
        return any(key in {"amount", "accession", "filed_date", "period_end"}
                   or _forbidden_policy_keys(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_forbidden_policy_keys(item) for item in value)
    return False


def test_dva_separates_ordinary_and_redeemable_nci_and_validates_aliases_and_flows():
    structural, filing = _source("DVA")
    rule = REPORTED_NCI_SCOPE_RULES["DVA"]
    availability, proof = reported_nci_field_availability(
        ticker="DVA", policy=asdict(rule), structural_packet=structural,
        accession=filing["accessionNumber"], period_end=filing["reportDate"])
    assert availability.value == proof["source_total"] == 1_844_534_000
    aliases = {row["qname"] for row in proof["alias_components"]}
    assert aliases == {
        "us-gaap:RedeemableNoncontrollingInterestEquityFairValue",
        "us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        "ns_c6a75dc24f:PotentialIncreaseDecreaseInFairValueOfNoncontrollingInterestsDueToChangeInWeightedAverageEBITDAMultiple",
    }
    assert {row["qname"] for row in proof["duration_diagnostics"]} >= {
        "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest",
        "us-gaap:MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders",
    }


def test_dva_acquisition_obligation_stays_inside_debt_and_post_period_event_blocks_use():
    structural, filing = _source("DVA")
    policy = nci_contingent_claim_policy("DVA")
    result = select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "review_required"
    assert result["claim_adjustment"] is None
    assert result["current_carrying_liability"] == 39_463_000
    assert result["review_reasons"] == [
        "acquisition_obligation_already_in_aggregate_debt",
        "post_period_investment_cash_lacks_cash_debt_share_and_operating_rollforward",
    ]
    assert result["components"] == {
        "acquisition_obligation_carrying_value": 39_463_000,
        "fair_value_alias_is_not_additive": 39_463_000,
        "acquisition_obligation_in_aggregate_debt": True,
        "nci_fair_value_sensitivity_is_not_claim": [225_000_000],
        "acquisition_cash_is_not_added": [38_540_000],
        "post_period_investment_cash_requires_rollforward": [200_000_000],
    }


def test_dva_corrected_nonoverlap_removes_the_legacy_double_deduction():
    recipe = json.loads((ROOT / "output/us-refresh-runtime/recipes/DVA.json").read_bytes())
    old = evaluate_recipe(recipe)["range"]
    corrected = deepcopy(recipe)
    for scenario in corrected["scenarios"].values():
        scenario["inputs"]["preferred_equity"] = 0.0
        scenario["inputs"]["noncontrolling_interests"] = 1_844_534_000
        scenario["inputs"]["nonoperating_adjustment"] = 0.0
    new = evaluate_recipe(corrected)["range"]
    assert {key:new[key]-old[key] for key in ("low","base","high")} == {
        "low": 0.5848449819194883,
        "base": 0.6012218531948008,
        "high": 0.6185423197492241,
    }


def test_dva_dimensioned_alias_and_unlisted_contingent_claim_changes_fail_closed():
    structural, filing = _source("DVA")
    rule = REPORTED_NCI_SCOPE_RULES["DVA"]
    for row in structural["facts"]:
        if row.get("qname") == "us-gaap:RedeemableNoncontrollingInterestEquityFairValue" and row.get("period_end") == filing["reportDate"]:
            row["value"] += 1
    with pytest.raises(ClaimScopeReviewRequired, match="alias does not match"):
        reported_nci_field_availability(
            ticker="DVA", policy=asdict(rule), structural_packet=structural,
            accession=filing["accessionNumber"], period_end=filing["reportDate"])

    structural, filing = _source("DVA")
    policy = nci_contingent_claim_policy("DVA")
    extra = deepcopy(next(row for row in structural["facts"]
                          if row.get("local_name") == policy["carrying_local_name"]
                          and row.get("period_end") == filing["reportDate"]))
    extra.update(qname="us-gaap:BusinessCombinationContingentConsiderationLiability",
                 local_name="BusinessCombinationContingentConsiderationLiability",context_id="unexpected")
    structural["facts"].append(extra)
    with pytest.raises(ValueError, match="unlisted current"):
        select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")


def test_crl_reconciles_nci_and_current_acquisition_surfaces_but_fails_legal_and_cash_overlap():
    structural, filing = _source("CRL")
    rule = REPORTED_NCI_SCOPE_RULES["CRL"]
    availability, proof = reported_nci_field_availability(
        ticker="CRL", policy=asdict(rule), structural_packet=structural,
        accession=filing["accessionNumber"], period_end=filing["reportDate"])
    assert availability.value == proof["source_total"] == 48_891_000
    assert {row["value"] for row in proof["alias_components"]} == {42_500_000, 47_000_000, 54_000_000}

    acquisition = nci_contingent_claim_policy("CRL")
    claim = select_acquisition_claim(acquisition, structural, filing, acquisition["cik"], "2026-08-14")
    assert claim["status"] == "review_required" and claim["claim_adjustment"] is None
    assert claim["current_carrying_liability"] == 150_000_000
    assert claim["components"] == {
        "current_and_noncurrent_contingent_consideration": 45_000_000,
        "deferred_acquisition_consideration": 105_000_000,
        "current_claim_stack_pending_overlap_review": 150_000_000,
        "paid_contingent_cash_is_not_added": [11_400_000],
        "acquisition_cash_is_not_added": [467_254_000],
    }
    legal = litigation_claim_policy("CRL")
    review = select_litigation_claim(legal, structural, filing, legal["cik"], "2026-08-14")
    assert review["status"] == "review_required" and review["claim_adjustment"] is None
    assert review["review_reasons"] == [
        "securities_and_derivative_claims_have_no_finite_loss_or_insurance_range"
    ]


@pytest.mark.parametrize("ticker", ["DVA", "CRL"])
def test_wg17_preferred_zero_and_policies_have_no_filing_amounts_or_dates(ticker):
    structural, filing = _source(ticker)
    preferred = preferred_lifecycle_policy(ticker)
    availability, proof = bind_preferred_lifecycle(
        ticker=ticker, policy=preferred, structural=structural,
        accession=filing["accessionNumber"], period=filing["reportDate"])
    assert availability.value == proof["preferred_equity"] == 0.0
    assert not _forbidden_policy_keys(nci_contingent_claim_policy(ticker))
    if ticker == "CRL":
        assert not _forbidden_policy_keys(litigation_claim_policy(ticker))


def test_zbh_does_not_qualify_without_redeemable_nci():
    structural, filing = _source("ZBH")
    current = [row for row in structural["facts"] if row.get("period_end") == filing["reportDate"]
               and row.get("period_start") is None]
    assert any(row.get("qname") == "us-gaap:MinorityInterest" and row.get("value") == 8_700_000 for row in current)
    assert not any("RedeemableNoncontrollingInterest" in str(row.get("qname")) for row in current)
    with pytest.raises(ValueError, match="no WG17"):
        nci_contingent_claim_policy("ZBH")


def test_wg17_maps_dva_and_crl_and_wg19_now_routes_zbh_to_financial_review():
    runtime = ROOT / "output/us-refresh-runtime"
    registry = {row["ticker"]:row for row in json.loads((runtime / "registry.json").read_bytes())["entries"]}
    for ticker in ("DVA","CRL","ZBH"):
        recipe = json.loads((runtime / "recipes" / f"{ticker}.json").read_bytes())
        artifact = json.loads((runtime / "baseline/artifacts" / f"{ticker}.json").read_bytes())
        compiled = _policy_for_entry(
            registry[ticker], artifact=artifact, recipe=recipe,
            source_evidence=None, concept_config=load_concept_config())
        assert compiled.reason_codes == ()
        if ticker == "ZBH":
            assert "WG19-MIXED-ORDINARY-NCI-CLAIMS-1" in compiled.policy["version"]
