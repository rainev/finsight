from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_acquisition_claims import nci_acquisition_special_claim_policy, select_acquisition_claim
from app.us_valuation.refresh_bridge_scope_policies import (
    AGGREGATE_DEBT_SCOPE_RULES,PREFERRED_EQUITY_ZERO_RULES,
    aggregate_debt_field_availability,preferred_equity_zero_availability,
)
from app.us_valuation.refresh_commitment_claims import commitment_claim_policy,select_commitment_claim
from app.us_valuation.refresh_operating_claims import operating_claim_policy,select_operating_claim
from app.us_valuation.refresh_operating_policies import _policy_for_entry
from app.us_valuation.refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES,reported_nci_field_availability
from app.us_valuation.xbrl import load_concept_config


ROOT=Path(__file__).resolve().parents[2]
SOURCES={
    "TEL":ROOT/"output/batch-30-structural-sources-20260901/TEL/structural-filing.json",
    "CRWD":ROOT/"output/batch-31-structural-sources-20260902/CRWD/structural-filing.json",
    "PH":ROOT/"output/batch-19-structural-sources-20260830/PH/structural-filing.json",
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
    if isinstance(value,(list,tuple)): return any(_forbidden(item) for item in value)
    return False


@pytest.mark.parametrize(("ticker","expected"),(("TEL",147_000_000),("CRWD",41_455_000)))
def test_wg20_binds_redeemable_or_ordinary_nci_and_keeps_flows_separate(ticker,expected):
    structural,filing=_source(ticker);rule=REPORTED_NCI_SCOPE_RULES[ticker]
    availability,proof=reported_nci_field_availability(
        ticker=ticker,policy=asdict(rule),structural_packet=structural,
        accession=filing["accessionNumber"],period_end=filing["reportDate"])
    assert availability.value==proof["source_total"]==expected
    assert proof["duration_diagnostics"]
    assert all(row["period_start"]<row["period_end"] for row in proof["duration_diagnostics"])


def test_tel_separates_current_claim_paid_cash_costs_and_pending_astrodyne_event():
    structural,filing=_source("TEL");policy=nci_acquisition_special_claim_policy("TEL")
    result=select_acquisition_claim(policy,structural,filing,policy["cik"],"2026-08-14")
    assert result["status"]=="source_bound" and result["claim_adjustment"]==150_000_000
    assert result["components"]=={
        "noncurrent_acquisition_carrying_liability":150_000_000,
        "acquisition_cash_is_not_added":200_000_000,
        "pending_forecast_acquisition_payment_is_not_current_claim":1_400_000_000,
        "acquisition_and_integration_cost_flows":[9_000_000,20_000_000],
    }
    operating=operating_claim_policy("TEL")
    reserve=select_operating_claim(operating,structural,filing,operating["cik"],"2026-08-14")
    assert reserve["status"]=="source_bound" and reserve["claim_adjustment"]==27_000_000
    assert reserve["components"]=={
        "operating_environmental_reserve":27_000_000,
        "environmental_range":[20_000_000,53_000_000],
        "legal_settlement_cash_flows":[14_000_000],
        "additional_equity_bridge_claim":27_000_000,
    }


def test_crwd_separates_acquisition_operating_reserve_and_purchase_schedule():
    structural,filing=_source("CRWD");policy=nci_acquisition_special_claim_policy("CRWD")
    result=select_acquisition_claim(policy,structural,filing,policy["cik"],"2026-08-14")
    assert result["status"]=="source_bound" and result["claim_adjustment"]==43_800_000
    assert result["components"]=={
        "acquisition_carrying_liability":43_800_000,
        "acquisition_cash_is_not_added":881_376_000,
    }
    operating=operating_claim_policy("CRWD")
    reserve=select_operating_claim(operating,structural,filing,operating["cik"],"2026-08-14")
    assert reserve["status"]=="source_bound" and reserve["claim_adjustment"]==17_103_000
    assert reserve["components"]=={
        "operating_loss_contingency_reserve":17_103_000,
        "loss_contingency_provision":18_128_000,
        "loss_contingency_cash_payments":16_523_000,
        "additional_equity_bridge_claim":17_103_000,
    }
    commitment=commitment_claim_policy("CRWD")
    schedule=select_commitment_claim(commitment,structural,filing,commitment["cik"],"2026-08-14")
    assert schedule["status"]=="source_bound" and schedule["claim_adjustment"]==0
    assert schedule["components"]=={
        "recorded_operating_purchase_obligations":2_618_759_000,
        "recorded_payment_schedule":[369_516_000,678_758_000,680_755_000,520_424_000,209_224_000,160_082_000],
        "unrecorded_operating_purchase_obligations":103_700_000,
        "post_period_operating_purchase_obligation":1_700_000_000,
        "additional_equity_bridge_claim":0.0,
    }


def test_ph_is_excluded_because_purchase_funding_and_transaction_overlay_are_not_current_claims():
    structural,filing=_source("PH")
    current=[row for row in structural["facts"] if row.get("period_end")==filing["reportDate"]
             and row.get("period_start") is None]
    assert any(row.get("qname")=="us-gaap:MinorityInterest" and row.get("value")==8_000_000 for row in current)
    assert not any("ContingentConsiderationLiability" in str(row.get("qname")) for row in current)
    with pytest.raises(ValueError,match="no WG20"):
        nci_acquisition_special_claim_policy("PH")


@pytest.mark.parametrize(("ticker","debt"),(("TEL",5_632_000_000),("CRWD",745_843_000)))
def test_wg20_bridge_scopes_reconcile_debt_and_zero_preferred(ticker,debt):
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


@pytest.mark.parametrize("ticker",["TEL","CRWD"])
def test_wg20_policies_are_versioned_without_filing_amounts_or_dates(ticker):
    assert not _forbidden(nci_acquisition_special_claim_policy(ticker))
    assert not _forbidden(operating_claim_policy(ticker))
    if ticker=="CRWD": assert not _forbidden(commitment_claim_policy(ticker))


def test_wg20_reclassification_preserves_each_explicit_current_reserve_once():
    expected={
        "TEL":(147_000_000,150_000_000,27_000_000,{"low":0.0,"base":0.0,"high":0.0}),
        "CRWD":(41_455_000,43_800_000,17_103_000,{"low":0.0,"base":0.0,"high":0.0}),
    }
    for ticker,(nci,acquisition,reserve,change) in expected.items():
        recipe=json.loads((ROOT/f"output/us-refresh-runtime/recipes/{ticker}.json").read_bytes())
        old=evaluate_recipe(recipe)["range"];corrected=deepcopy(recipe)
        for scenario in corrected["scenarios"].values():
            scenario["inputs"]["preferred_equity"]=0.0
            scenario["inputs"]["noncontrolling_interests"]=nci
            scenario["inputs"]["nonoperating_adjustment"]=-(acquisition+reserve)
        new=evaluate_recipe(corrected)["range"]
        assert {key:new[key]-old[key] for key in ("low","base","high")}==change


def test_wg20_maps_tel_crwd_and_wg21_routes_ph_to_event_overlay_review():
    runtime=ROOT/"output/us-refresh-runtime"
    registry={row["ticker"]:row for row in json.loads((runtime/"registry.json").read_bytes())["entries"]}
    for ticker in ("TEL","CRWD","PH"):
        recipe=json.loads((runtime/"recipes"/f"{ticker}.json").read_bytes())
        artifact=json.loads((runtime/"baseline/artifacts"/f"{ticker}.json").read_bytes())
        compiled=_policy_for_entry(registry[ticker],artifact=artifact,recipe=recipe,
                                   source_evidence=None,concept_config=load_concept_config())
        if ticker=="PH":
            assert compiled.reason_codes == ()
            assert "WG21-ACQUISITION-FUNDING-OVERLAY" in compiled.policy["version"]
            assert compiled.policy["inputs"]["acquisition_funding_review"]["selector"] == "special_claim"
            assert compiled.policy["narrative_evidence_policy"]["source_role"] == "event_filing"
        else:
            assert "baseline_non_debt_claim_scope_requires_source_rule" not in compiled.reason_codes
