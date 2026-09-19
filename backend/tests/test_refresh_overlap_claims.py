from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_acquisition_claims import overlapping_claim_policy, select_acquisition_claim
from app.us_valuation.refresh_litigation_claims import litigation_claim_policy, select_litigation_claim
from app.us_valuation.refresh_operating_policies import _policy_for_entry
from app.us_valuation.refresh_preferred_lifecycle import bind_preferred_lifecycle, preferred_lifecycle_policy
from app.us_valuation.refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES, reported_nci_field_availability
from app.us_valuation.xbrl import load_concept_config


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "BSX": ROOT / "output/batch-14-structural-sources-20260829/BSX/structural-filing.json",
    "DGX": ROOT / "output/batch-15-structural-sources-20260830/DGX/structural-filing.json",
    "EW": ROOT / "output/batch-16-structural-sources-20260830/EW/structural-filing.json",
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


def _result(ticker: str):
    structural, filing = _source(ticker)
    acquisition = overlapping_claim_policy(ticker)
    litigation = litigation_claim_policy(ticker)
    return (
        select_acquisition_claim(acquisition, structural, filing, acquisition["cik"], "2026-08-14"),
        select_litigation_claim(litigation, structural, filing, litigation["cik"], "2026-08-14"),
    )


def _forbidden_policy_keys(value):
    if isinstance(value, dict):
        return any(key in {"amount", "accession", "filed_date", "period_end"}
                   or _forbidden_policy_keys(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_forbidden_policy_keys(item) for item in value)
    return False


def test_bsx_current_claims_reconcile_but_untimed_restructuring_stays_separate():
    acquisition, litigation = _result("BSX")
    assert acquisition["claim_adjustment"] == 257_000_000
    assert acquisition["components"] == {
        "carrying_components": {
            "RevenueBasedPaymentsMember": 76_000_000,
            "RDRegulatoryandCommercializationbasedMilestoneMember": 181_000_000,
        },
        "maximum_is_not_current_claim": 596_000_000,
        "paid_cash_is_not_added": [82_000_000, 78_000_000],
    }
    assert litigation["claim_adjustment"] == 282_000_000
    assert any(row["qname"] == "us-gaap:LitigationSettlementExpense" for row in litigation["excluded_rows"])


def test_dgx_separates_ordinary_and_redeemable_nci_from_acquisition_and_operating_reserves():
    structural, filing = _source("DGX")
    rule = REPORTED_NCI_SCOPE_RULES["DGX"]
    availability, proof = reported_nci_field_availability(
        ticker="DGX", policy=asdict(rule), structural_packet=structural,
        accession=filing["accessionNumber"], period_end=filing["reportDate"])
    assert availability.value == proof["source_total"] == 383_000_000
    assert {row["qname"] for row in proof["alias_components"]} == {
        "us-gaap:RedeemableNoncontrollingInterestEquityFairValue"
    }
    assert {row["value"] for row in proof["alias_components"]} == {0.0, 80_000_000.0}
    assert {row["qname"] for row in proof["duration_diagnostics"]} == {
        *rule.diagnostic_duration_qnames,
        "ns_8314d21e0f:NoncontrollingInterestIncreaseFromContributions",
    }
    acquisition, litigation = _result("DGX")
    assert acquisition["claim_adjustment"] == 100_000_000
    assert sorted(acquisition["components"]["measurement_changes_are_not_claims"]) == [3_000_000, 4_000_000]
    assert acquisition["components"]["acquisition_cash_is_not_contingent_payment"] == [38_000_000]
    assert litigation["claim_adjustment"] == 0
    assert litigation["components"] == {
        "malpractice_operating_reserve": 174_000_000,
        "separate_litigation_operating_reserve": 17_000_000,
        "additional_equity_bridge_claim": 0.0,
    }
    assert all(row.get("period_start") is None for row in proof["components"])


@pytest.mark.parametrize("ticker", ["BSX", "EW"])
def test_nci_earnings_and_owner_flows_remain_duration_diagnostics(ticker):
    structural, filing = _source(ticker)
    rule = REPORTED_NCI_SCOPE_RULES[ticker]
    _, proof = reported_nci_field_availability(
        ticker=ticker, policy=asdict(rule), structural_packet=structural,
        accession=filing["accessionNumber"], period_end=filing["reportDate"])
    assert {row["qname"] for row in proof["duration_diagnostics"]} == set(rule.diagnostic_duration_qnames)
    assert all(row["period_start"] < row["period_end"] for row in proof["duration_diagnostics"])


def test_ew_uses_current_contingent_liability_not_maximum_or_arithmetic_midpoint():
    acquisition, litigation = _result("EW")
    assert acquisition["claim_adjustment"] == 9_900_000
    assert acquisition["components"]["current_carrying_portion"] == 7_500_000
    assert acquisition["components"]["maximum_is_not_current_claim"] == 132_500_000
    assert 70_000_000 in acquisition["components"]["separate_acquisition_equity_not_contingent_claim"]
    assert litigation["status"] == "review_required"
    assert litigation["claim_adjustment"] is None
    assert litigation["current_carrying_claim"] == 56_900_000
    assert litigation["review_reasons"] == [
        "unaccrued_patent_milestone_appeal_and_tax_exposure_has_no_finite_range"
    ]
    assert litigation["components"] == {
        "litigation_reserve": 56_900_000,
        "combined_litigation_and_insurance_reserve": 72_400_000,
        "current_litigation_reserve_subset": 0.0,
        "combined_excess_not_recovery": 15_500_000,
    }


def test_wg16_maxima_duplicates_and_operating_reserves_cannot_change_current_claim():
    structural, filing = _source("EW")
    policy = overlapping_claim_policy("EW")
    for row in structural["facts"]:
        if row.get("qname") == policy["maximum_qname"]:
            row["value"] += 1
    assert select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")["claim_adjustment"] == 9_900_000

    structural, filing = _source("DGX")
    policy = overlapping_claim_policy("DGX")
    duplicate = deepcopy(next(row for row in structural["facts"]
                              if row.get("qname") == policy["qname"]
                              and row.get("period_end") == filing["reportDate"]
                              and not row.get("dimensions")))
    duplicate["value"] += 1
    structural["facts"].append(duplicate)
    with pytest.raises(ValueError, match="presentations conflict"):
        select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")

    structural, filing = _source("DGX")
    policy = litigation_claim_policy("DGX")
    extra = deepcopy(next(row for row in structural["facts"]
                          if row.get("qname") == policy["litigation_qname"]
                          and row.get("period_end") == filing["reportDate"]))
    extra["dimensions"] = [[policy["litigation_axis"], "us-gaap:OtherMember"]]
    extra["context_id"] = "unexpected-legal-scope"
    structural["facts"].append(extra)
    with pytest.raises(ValueError, match="unexpected positive"):
        select_litigation_claim(policy, structural, filing, policy["cik"], "2026-08-14")

    structural, filing = _source("EW")
    policy = litigation_claim_policy("EW")
    for row in structural["facts"]:
        if row.get("local_name") == policy["combined_local_name"] and row.get("period_end") == filing["reportDate"]:
            row["value"] = 1
    with pytest.raises(ValueError, match="scopes do not reconcile"):
        select_litigation_claim(policy, structural, filing, policy["cik"], "2026-08-14")


@pytest.mark.parametrize("ticker", ["BSX", "DGX", "EW"])
def test_wg16_policies_are_versioned_without_filing_amounts_or_dates(ticker):
    assert not _forbidden_policy_keys(overlapping_claim_policy(ticker))
    assert not _forbidden_policy_keys(litigation_claim_policy(ticker))


@pytest.mark.parametrize("ticker", ["BSX", "EW"])
def test_reported_zero_preferred_requires_both_zero_value_and_zero_shares(ticker):
    structural, filing = _source(ticker)
    policy = preferred_lifecycle_policy(ticker)
    availability, proof = bind_preferred_lifecycle(
        ticker=ticker, policy=policy, structural=structural,
        accession=filing["accessionNumber"], period=filing["reportDate"])
    assert availability.value == proof["preferred_equity"] == 0.0


def test_dgx_reclassification_preserves_value_and_ew_drops_maximum_as_current_claim():
    for ticker, nci, acquisition, litigation in (
        ("DGX", 383_000_000, 100_000_000, 0),
        ("EW", 106_900_000, 9_900_000, 56_900_000),
    ):
        recipe = json.loads((ROOT / f"output/us-refresh-runtime/recipes/{ticker}.json").read_bytes())
        original = evaluate_recipe(recipe)["range"]
        mapped = deepcopy(recipe)
        for scenario in mapped["scenarios"].values():
            scenario["inputs"]["preferred_equity"] = 0.0
            scenario["inputs"]["noncontrolling_interests"] = nci
            scenario["inputs"]["nonoperating_adjustment"] = -(acquisition + litigation)
        current = evaluate_recipe(mapped)["range"]
        if ticker == "DGX":
            assert current == original
        else:
            assert current["low"] > original["low"]
            assert current["base"] > original["base"]
            assert current["high"] < original["high"]


def test_compiler_retains_bsx_schedule_blocker_but_compiles_dgx_and_ew_claims():
    runtime = ROOT / "output/us-refresh-runtime"
    registry = {row["ticker"]: row for row in json.loads((runtime / "registry.json").read_bytes())["entries"]}
    for ticker in ("BSX", "DGX", "EW"):
        recipe = json.loads((runtime / "recipes" / f"{ticker}.json").read_bytes())
        artifact = json.loads((runtime / "baseline/artifacts" / f"{ticker}.json").read_bytes())
        compiled = _policy_for_entry(
            registry[ticker], artifact=artifact, recipe=recipe,
            source_evidence=None, concept_config=load_concept_config())
        if ticker == "BSX":
            assert compiled.reason_codes == ("post_period_restructuring_cash_requires_separate_timed_schedule",)
        else:
            assert compiled.reason_codes == ()
