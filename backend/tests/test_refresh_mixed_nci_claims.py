from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.us_valuation.bridge_policy import BridgeRange, BridgeResolution
from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_acquisition_claims import mixed_claim_policy, select_acquisition_claim
from app.us_valuation.refresh_bridge_scope_policies import (
    AGGREGATE_DEBT_SCOPE_RULES,
    aggregate_debt_field_availability,
    nonmarketable_investment_zero_availabilities,
)
from app.us_valuation.refresh_litigation_claims import litigation_claim_policy, select_litigation_claim
from app.us_valuation.refresh_preferred_lifecycle import bind_preferred_lifecycle, preferred_lifecycle_policy
from app.us_valuation.refresh_reported_claim_scope import (
    ClaimScopeReviewRequired,
    REPORTED_NCI_SCOPE_RULES,
    project_reported_nci_scope,
    reported_nci_field_availability,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "ABT": ROOT / "output/batch-12-structural-sources-20260828/ABT/structural-filing.json",
    "BAX": ROOT / "output/batch-12-structural-sources-20260828/BAX/structural-filing.json",
    "BA": ROOT / "output/batch-18-structural-sources-20260830/BA/structural-filing.json",
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


def _bridge(nci: float) -> BridgeResolution:
    cash = BridgeRange(10.0, 10.0, 10.0)
    debt = BridgeRange(2.0, 2.0, 2.0)
    preferred = BridgeRange(0.0, 0.0, 0.0)
    outside = BridgeRange(nci, nci, nci)
    adjustment = BridgeRange(8.0 - nci, 8.0 - nci, 8.0 - nci)
    return BridgeResolution(
        complete=True,
        can_value=True,
        missing_fields=(),
        blocking_fields=(),
        bounded_fields=(),
        cash_and_investments=cash,
        total_debt=debt,
        preferred_equity=preferred,
        noncontrolling_interests=outside,
        bridge_adjustment=adjustment,
        fully_diluted_shares=1.0,
        reason_codes=(),
    )


def _forbidden_policy_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"amount", "accession", "filed_date", "period_end"}:
                return True
            if _forbidden_policy_keys(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_forbidden_policy_keys(item) for item in value)
    return False


def test_abt_counts_duplicate_contingent_consideration_once():
    structural, filing = _source("ABT")
    policy = mixed_claim_policy("ABT")
    result = select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 263_000_000
    assert result["pro_forma_revenue"] == 24_500_000_000
    assert result["pro_forma_months"] == 6
    assert result["annualized_pro_forma_revenue"] == 49_000_000_000
    assert [row["value"] for row in result["source_rows"]].count(263_000_000) == 2
    assert [row["value"] for row in result["source_rows"]].count(0) == 2


def test_abt_uses_carrying_accrual_and_not_possible_loss_or_historical_maxima():
    structural, filing = _source("ABT")
    policy = litigation_claim_policy("ABT")
    result = select_litigation_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 510_000_000
    assert result["components"]["possible_loss_range"] == [120_000_000, 530_000_000]
    assert result["components"]["site_maxima"] == [10_000_000, 4_000_000]
    assert any(row["qname"] == "us-gaap:LossContingencyDamagesAwardedValue" for row in result["excluded_rows"])


def test_abt_rejects_unexpected_positive_claim_dimensions():
    structural, filing = _source("ABT")
    acquisition = mixed_claim_policy("ABT")
    extra = deepcopy(next(row for row in structural["facts"]
                          if row.get("qname") == acquisition["qname"]
                          and row.get("period_end") == filing["reportDate"]
                          and not row.get("dimensions")))
    extra["dimensions"] = [["us-gaap:BusinessAcquisitionAxis", "us-gaap:OtherMember"]]
    extra["context_id"] = "unexpected-acquisition-scope"
    structural["facts"].append(extra)
    with pytest.raises(ValueError, match="unexpected current acquisition claim dimension"):
        select_acquisition_claim(acquisition, structural, filing, acquisition["cik"], "2026-08-14")

    structural, filing = _source("ABT")
    litigation = litigation_claim_policy("ABT")
    extra = deepcopy(next(row for row in structural["facts"]
                          if row.get("qname") == litigation["reserve_qname"]
                          and row.get("period_end") == filing["reportDate"]))
    extra["dimensions"] = [[litigation["reserve_axis"], "us-gaap:OtherMember"]]
    extra["context_id"] = "unexpected-litigation-scope"
    structural["facts"].append(extra)
    with pytest.raises(ValueError, match="unexpected positive current litigation"):
        select_litigation_claim(litigation, structural, filing, litigation["cik"], "2026-08-14")


def test_bax_separates_three_current_claims_from_duplicates_maxima_reserves_and_paid_cash():
    structural, filing = _source("BAX")
    policy = mixed_claim_policy("BAX")
    result = select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 105_000_000
    assert result["components"] == {
        "contingent_consideration": 10_000_000,
        "separation_indemnification": 43_000_000,
        "disposal_group_claim": 52_000_000,
    }
    excluded = {row["local_name"]: row["value"] for row in result["excluded_rows"]}
    assert excluded["DisposalGroupIncludingDiscontinuedOperationContingentLiabilityHeld"] == 133_000_000
    assert excluded["BusinessGuaranteesRetainedValue"] == 28_000_000
    assert excluded["LitigationReserve"] == 39_000_000
    assert excluded["AccrualForEnvironmentalLossContingencies"] == 25_000_000
    assert excluded["PaymentForContingentConsiderationLiabilityFinancingActivities"] == 31_000_000


def test_bax_environmental_reserve_is_a_subset_and_the_maximum_is_non_additive():
    structural, filing = _source("BAX")
    policy = mixed_claim_policy("BAX")
    for row in structural["facts"]:
        if row.get("qname") == policy["environmental_accrual_qname"] and row.get("period_end") == filing["reportDate"]:
            row["value"] = 40_000_000
    with pytest.raises(ValueError, match="environmental reserve exceeds"):
        select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")

    structural, filing = _source("BAX")
    for row in structural["facts"]:
        if row.get("local_name") == policy["aggregate_maximum_local_name"] and row.get("period_end") == filing["reportDate"]:
            row["value"] += 1
    assert select_acquisition_claim(
        policy, structural, filing, policy["cik"], "2026-08-14")["claim_adjustment"] == 105_000_000


def test_abt_and_bax_nci_are_source_bound_without_inverting_negative_bax_balance():
    for ticker, reported in (("ABT", 652_000_000), ("BAX", -27_000_000)):
        structural, filing = _source(ticker)
        rule = REPORTED_NCI_SCOPE_RULES[ticker]
        availability, proof = reported_nci_field_availability(
            ticker=ticker,
            policy=asdict(rule),
            structural_packet=structural,
            accession=filing["accessionNumber"],
            period_end=filing["reportDate"],
        )
        assert availability.value == reported
        projected = project_reported_nci_scope(
            ticker=ticker,
            policy=asdict(rule),
            normalized_bridge=_bridge(reported),
            proof=proof,
        )
        assert projected.noncontrolling_interests.midpoint == (reported if ticker == "ABT" else 0.0)
    changed = deepcopy(structural)
    for row in changed["facts"]:
        if row.get("qname") == "us-gaap:MinorityInterest" and row.get("period_end") == filing["reportDate"] and not row.get("dimensions"):
            row["value"] = 1.0
    rule = REPORTED_NCI_SCOPE_RULES["BAX"]
    availability, proof = reported_nci_field_availability(
        ticker="BAX", policy=asdict(rule), structural_packet=changed,
        accession=filing["accessionNumber"], period_end=filing["reportDate"])
    with pytest.raises(ClaimScopeReviewRequired, match="became a positive"):
        project_reported_nci_scope(
            ticker="BAX", policy=asdict(rule), normalized_bridge=_bridge(availability.value), proof=proof)


def test_abt_debt_investment_and_preferred_scopes_close_without_missing_fact_zeros():
    structural, filing = _source("ABT")
    debt_rule = AGGREGATE_DEBT_SCOPE_RULES["ABT"]
    debt, debt_proof = aggregate_debt_field_availability(
        ticker="ABT", policy=asdict(debt_rule), structural_packet=structural,
        accession=filing["accessionNumber"], period_end=filing["reportDate"])
    assert debt.value == debt_proof["total"] == 32_608_000_000
    investments, investment_proof = nonmarketable_investment_zero_availabilities(
        ticker="ABT", policy=asdict(debt_rule), structural_packet=structural,
        accession=filing["accessionNumber"], period_end=filing["reportDate"])
    assert [(row.field, row.value) for row in investments] == [("marketable_securities_noncurrent", 0.0)]
    assert investment_proof["excluded_total"] == 1_111_000_000
    preferred_rule = preferred_lifecycle_policy("ABT")
    preferred, preferred_proof = bind_preferred_lifecycle(
        ticker="ABT", policy=preferred_rule, structural=structural,
        accession=filing["accessionNumber"], period=filing["reportDate"])
    assert preferred.value == preferred_proof["preferred_equity"] == 0.0
    assert preferred_proof["components"]["current_shares_issued"] == 0.0


def test_ba_nci_is_separate_but_does_not_clear_its_convertible_and_legal_claim_gap():
    structural, filing = _source("BA")
    rule = REPORTED_NCI_SCOPE_RULES["BA"]
    availability, proof = reported_nci_field_availability(
        ticker="BA", policy=asdict(rule), structural_packet=structural,
        accession=filing["accessionNumber"], period_end=filing["reportDate"])
    assert availability.value == proof["source_total"] == 15_000_000
    assert rule.clears_legacy_claim_scope is False
    assert any(row.get("qname") == "us-gaap:PreferredStockValue" and row.get("value") == 6_000_000
               for row in structural["facts"])


def test_wg15_policies_contain_no_filing_amounts_or_dates_and_reclassification_is_exact():
    for ticker in ("ABT", "BAX"):
        acquisition = mixed_claim_policy(ticker)
        assert not _forbidden_policy_keys(acquisition)
        if ticker == "ABT":
            assert not _forbidden_policy_keys(litigation_claim_policy(ticker))
        recipe = json.loads((ROOT / f"output/us-refresh-runtime/recipes/{ticker}.json").read_bytes())
        original = evaluate_recipe(recipe)
        structural, filing = _source(ticker)
        acquisition_amount = select_acquisition_claim(
            acquisition, structural, filing, acquisition["cik"], "2026-08-14")["claim_adjustment"]
        legal_amount = 0.0
        nci = 0.0
        if ticker == "ABT":
            legal = litigation_claim_policy(ticker)
            legal_amount = select_litigation_claim(
                legal, structural, filing, legal["cik"], "2026-08-14")["claim_adjustment"]
            nci = 652_000_000
        mapped = deepcopy(recipe)
        for scenario in mapped["scenarios"].values():
            scenario["inputs"]["preferred_equity"] = 0.0
            scenario["inputs"]["noncontrolling_interests"] = nci
            scenario["inputs"]["nonoperating_adjustment"] = -(acquisition_amount + legal_amount)
        assert evaluate_recipe(mapped)["range"] == original["range"]
