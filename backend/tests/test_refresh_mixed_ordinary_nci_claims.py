from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_acquisition_claims import mixed_ordinary_nci_claim_policy, select_acquisition_claim
from app.us_valuation.refresh_bridge_scope_policies import (
    AGGREGATE_DEBT_SCOPE_RULES,
    PREFERRED_EQUITY_ZERO_RULES,
    aggregate_debt_field_availability,
    preferred_equity_zero_availability,
)
from app.us_valuation.refresh_litigation_claims import litigation_claim_policy, select_litigation_claim
from app.us_valuation.refresh_operating_claims import operating_claim_policy, select_operating_claim
from app.us_valuation.refresh_operating_policies import _policy_for_entry
from app.us_valuation.refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES, reported_nci_field_availability
from app.us_valuation.xbrl import load_concept_config


ROOT=Path(__file__).resolve().parents[2]
SOURCES={
    "HSIC":ROOT/"output/batch-15-structural-sources-20260830/HSIC/structural-filing.json",
    "ON":ROOT/"output/batch-30-structural-sources-20260901/ON/structural-filing.json",
    "TEL":ROOT/"output/batch-30-structural-sources-20260901/TEL/structural-filing.json",
    "ZBH":ROOT/"output/batch-16-structural-sources-20260830/ZBH/structural-filing.json",
}


def _source(ticker):
    structural=json.loads(SOURCES[ticker].read_bytes())
    filing={"accessionNumber":structural["source_accession"],"reportDate":structural["report_date"],
            "filingDate":structural["filed_date"],"form":structural["form"]}
    return structural,filing


def _forbidden(value):
    if isinstance(value,dict):
        return any(key in {"amount","accession","filed_date","period_end"} or _forbidden(item)
                   for key,item in value.items())
    if isinstance(value,(list,tuple)):
        return any(_forbidden(item) for item in value)
    return False


@pytest.mark.parametrize(("ticker","expected"),(("HSIC",1_566_000_000),("ON",19_800_000),("ZBH",8_700_000)))
def test_wg19_binds_current_ownership_claims_and_keeps_flows_separate(ticker,expected):
    structural,filing=_source(ticker);rule=REPORTED_NCI_SCOPE_RULES[ticker]
    availability,proof=reported_nci_field_availability(
        ticker=ticker,policy=asdict(rule),structural_packet=structural,
        accession=filing["accessionNumber"],period_end=filing["reportDate"])
    assert availability.value==proof["source_total"]==expected
    assert proof["duration_diagnostics"]
    assert all(row["period_start"]<row["period_end"] for row in proof["duration_diagnostics"])


def test_hsic_reconciles_ordinary_redeemable_and_recurring_acquisition_claims():
    structural,filing=_source("HSIC");policy=mixed_ordinary_nci_claim_policy("HSIC")
    result=select_acquisition_claim(policy,structural,filing,policy["cik"],"2026-08-14")
    assert result["status"]=="source_bound" and result["claim_adjustment"]==58_000_000
    assert result["components"]=={
        "aggregate_carrying_liability":58_000_000,
        "recurring_view_is_not_additive":58_000_000,
        "level3_view_is_not_additive":58_000_000,
        "paid_cash_is_not_added":[4_000_000],
        "measurement_changes_are_not_claims":[-2_000_000,-1_000_000],
        "deferred_consideration_duration_disclosures_are_not_current_claims":[3_000_000,5_000_000],
        "acquisition_cash_is_not_added":[26_000_000,194_000_000],
    }
    operating=operating_claim_policy("HSIC")
    reserve=select_operating_claim(operating,structural,filing,operating["cik"],"2026-08-14")
    assert reserve["status"]=="source_bound" and reserve["claim_adjustment"]==0
    assert reserve["components"]=={
        "operating_restructuring_reserve":43_000_000,
        "restructuring_charges":41_000_000,
        "restructuring_cash_payments":43_000_000,
        "additional_equity_bridge_claim":0.0,
    }


def test_on_reconciles_current_noncurrent_claim_and_operating_reserve():
    structural,filing=_source("ON");policy=mixed_ordinary_nci_claim_policy("ON")
    result=select_acquisition_claim(policy,structural,filing,policy["cik"],"2026-08-14")
    assert result["status"]=="source_bound" and result["claim_adjustment"]==113_100_000
    assert result["components"]=={
        "aggregate_carrying_liability":113_100_000,
        "current_carrying_portion":58_600_000,
        "noncurrent_carrying_portion":54_500_000,
        "acquisition_cash_is_not_added":[13_000_000],
    }
    operating=operating_claim_policy("ON")
    reserve=select_operating_claim(operating,structural,filing,operating["cik"],"2026-08-14")
    assert reserve["status"]=="source_bound" and reserve["claim_adjustment"]==0
    assert reserve["components"]=={
        "operating_restructuring_reserve":6_800_000,
        "restructuring_charges":22_700_000,
        "restructuring_cash_payments":21_900_000,
        "additional_equity_bridge_claim":0.0,
    }


def test_zbh_counts_recurring_acquisition_once_but_preserves_unbounded_legal_review():
    structural,filing=_source("ZBH");policy=mixed_ordinary_nci_claim_policy("ZBH")
    result=select_acquisition_claim(policy,structural,filing,policy["cik"],"2026-08-14")
    assert result["status"]=="source_bound" and result["claim_adjustment"]==244_600_000
    assert result["components"]=={
        "aggregate_carrying_liability":244_600_000,
        "level3_view_is_not_additive":244_600_000,
        "acquisition_member_values_are_not_additive":[35_000_000,201_600_000,211_300_000],
        "maximum_is_not_current_claim":720_000_000,
        "paid_cash_is_not_added":[69_200_000],
        "acquisition_cash_is_not_added":[175_900_000,1_241_500_000],
    }
    legal=litigation_claim_policy("ZBH")
    review=select_litigation_claim(legal,structural,filing,legal["cik"],"2026-08-14")
    assert review["status"]=="review_required" and review["claim_adjustment"] is None
    assert review["review_reasons"]==["china_distributor_and_tax_exposure_not_finitely_bounded"]
    assert review["components"]=={
        "operating_litigation_reserve":137_900_000,
        "possible_loss_portion_not_accrued":465_000_000,
        "additional_equity_bridge_claim":0.0,
        "settlement_expense_flows":[17_800_000,22_800_000],
    }


def test_tel_is_excluded_without_current_ordinary_nci():
    structural,filing=_source("TEL")
    current=[row for row in structural["facts"] if row.get("period_end")==filing["reportDate"]
             and row.get("period_start") is None]
    assert not any(row.get("qname")=="us-gaap:MinorityInterest" for row in current)
    assert any(row.get("qname")=="us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount"
               and row.get("value")==147_000_000 for row in current)
    with pytest.raises(ValueError,match="no WG19"):
        mixed_ordinary_nci_claim_policy("TEL")


@pytest.mark.parametrize(("ticker","debt"),(("HSIC",3_462_000_000),("ON",4_459_400_000),("ZBH",7_479_000_000)))
def test_wg19_bridge_scopes_reconcile_debt_and_zero_preferred(ticker,debt):
    structural,filing=_source(ticker);rule=AGGREGATE_DEBT_SCOPE_RULES[ticker]
    availability,proof=aggregate_debt_field_availability(
        ticker=ticker,policy=asdict(rule),structural_packet=structural,
        accession=filing["accessionNumber"],period_end=filing["reportDate"])
    assert availability.value==proof["total"]==debt
    preferred=PREFERRED_EQUITY_ZERO_RULES[ticker]
    zero,zero_proof=preferred_equity_zero_availability(
        ticker=ticker,policy=preferred,structural_packet=structural,
        accession=filing["accessionNumber"],period_end=filing["reportDate"])
    assert zero.value==zero_proof["value"]==0


@pytest.mark.parametrize("ticker",["HSIC","ON","ZBH"])
def test_wg19_policies_are_versioned_without_filing_amounts_or_dates(ticker):
    assert not _forbidden(mixed_ordinary_nci_claim_policy(ticker))
    if ticker in {"HSIC","ON"}: assert not _forbidden(operating_claim_policy(ticker))
    if ticker=="ZBH": assert not _forbidden(litigation_claim_policy(ticker))


def test_wg19_claim_reclassification_and_zbh_operating_reserve_correction():
    expected={
        "HSIC":(1_566_000_000,58_000_000,{"low":0.0,"base":0.0,"high":0.0}),
        "ON":(19_800_000,113_100_000,{"low":0.0,"base":0.0,"high":0.0}),
        "ZBH":(8_700_000,244_600_000,{"low":0.7097272259392682,"base":0.7162935158796842,"high":0.7229824410843122}),
    }
    for ticker,(nci,acquisition,change) in expected.items():
        recipe=json.loads((ROOT/f"output/us-refresh-runtime/recipes/{ticker}.json").read_bytes())
        old=evaluate_recipe(recipe)["range"];corrected=deepcopy(recipe)
        for scenario in corrected["scenarios"].values():
            scenario["inputs"]["preferred_equity"]=0.0
            scenario["inputs"]["noncontrolling_interests"]=nci
            scenario["inputs"]["nonoperating_adjustment"]=-acquisition
        new=evaluate_recipe(corrected)["range"]
        assert {key:new[key]-old[key] for key in ("low","base","high")}==change


def test_wg19_maps_its_tranche_and_wg20_now_routes_tel_special_situation():
    runtime=ROOT/"output/us-refresh-runtime"
    registry={row["ticker"]:row for row in json.loads((runtime/"registry.json").read_bytes())["entries"]}
    for ticker in ("HSIC","ON","TEL","ZBH"):
        recipe=json.loads((runtime/"recipes"/f"{ticker}.json").read_bytes())
        artifact=json.loads((runtime/"baseline/artifacts"/f"{ticker}.json").read_bytes())
        compiled=_policy_for_entry(registry[ticker],artifact=artifact,recipe=recipe,
                                   source_evidence=None,concept_config=load_concept_config())
        assert "baseline_non_debt_claim_scope_requires_source_rule" not in compiled.reason_codes
        if ticker=="TEL":
            assert "WG20-NCI-ACQUISITION-SPECIAL-1" in compiled.policy["version"]
