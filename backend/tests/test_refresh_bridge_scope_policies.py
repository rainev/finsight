from __future__ import annotations

import copy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_bridge_scope_policies import (
    AGGREGATE_DEBT_SCOPE_RULES,
    OUTSIDE_EQUITY_ZERO_RULES,
    PREFERRED_EQUITY_ZERO_RULES,
    BridgeScopeReviewRequired,
    aggregate_debt_field_availability,
    nonmarketable_investment_zero_availabilities,
    outside_equity_zero_availability,
    preferred_equity_zero_availability,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "ABBV": ROOT / "output/batch-17-structural-sources-20260830/ABBV/structural-filing.json",
    "AVY": ROOT / "output/batch-41-structural-sources-20260907/AVY/structural-filing.json",
    "BALL": ROOT / "output/batch-41-structural-sources-20260907/BALL/structural-filing.json",
    "COO": ROOT / "output/batch-13-structural-sources-20260829/COO/structural-filing.json",
    "CTSH": ROOT / "output/batch-30-structural-sources-20260901/CTSH/structural-filing.json",
    "DASH": ROOT / "output/batch-08-structural-sources-20260826/DASH/structural-filing.json",
    "ICE": ROOT / "output/batch-40-structural-sources-20260907/ICE/structural-filing.json",
    "KDP": ROOT / "output/batch-08-structural-sources-20260826/KDP/structural-filing.json",
    "ROK": ROOT / "output/batch-22-structural-sources-20260831/ROK/structural-filing.json",
    "MCO": ROOT / "output/batch-37-structural-sources-20260906/MCO/structural-filing.json",
    "MPC": ROOT / "output/batch-44-structural-sources-20260907/MPC/structural-filing.json",
    "MSCI": ROOT / "output/batch-40-structural-sources-20260907/MSCI/structural-filing.json",
    "MU": ROOT / "output/batch-27-structural-sources-20260831/MU/structural-filing.json",
    "MRK": ROOT / "output/batch-13-structural-sources-20260829/MRK/structural-filing.json",
    "NUE": ROOT / "output/batch-41-structural-sources-20260907/NUE/structural-filing.json",
    "STLD": ROOT / "output/batch-43-structural-sources-20260907/STLD/structural-filing.json",
    "VRTX": ROOT / "output/batch-14-structural-sources-20260829/VRTX/structural-filing.json",
    "VRT": ROOT / "output/batch-32-structural-sources-20260903/VRT/structural-filing.json",
}


def _bind(ticker: str, structural: dict | None = None):
    rule = AGGREGATE_DEBT_SCOPE_RULES[ticker]
    structural = structural or json.loads(SOURCES[ticker].read_text())
    if ticker == "DASH" and structural.get("report_date") is None:
        structural = {**structural, "report_date": "2026-06-30"}
    return aggregate_debt_field_availability(
        ticker=ticker, policy=asdict(rule), structural_packet=structural,
        accession=structural["source_accession"], period_end=structural["report_date"],
    )


@pytest.mark.parametrize("ticker,total", [("MCO", 6_946_000_000), ("ROK", 3_258_000_000)])
def test_current_real_debt_scope_is_source_bound_without_filing_constants(ticker,total):
    availability, proof = _bind(ticker)
    assert availability.value == total
    assert availability.field == "total_interest_bearing_debt"
    assert availability.fallback_level == "reported_aggregate"
    assert set(availability.covered_fields) == {
        "commercial_paper", "current_debt", "noncurrent_debt",
        "finance_lease_current", "finance_lease_noncurrent",
    }
    assert availability.coverage_source_facts
    assert proof["status"] == "source_bound"
    assert proof["total"] == total


@pytest.mark.parametrize("ticker,total", [("ABBV",70_822_000_000),("COO",2_460_200_000),("MRK",53_906_000_000),("MU",5_722_000_000),
    ("CTSH",1_560_000_000),("VRTX",0),("VRT",2_939_800_000)])
def test_wg2_current_debt_scope_is_source_bound(ticker,total):
    availability,proof=_bind(ticker)
    assert availability.value==total
    assert set(availability.covered_fields)=={
        "commercial_paper","current_debt","noncurrent_debt",
        "finance_lease_current","finance_lease_noncurrent"}
    assert proof["total"]==total


@pytest.mark.parametrize("ticker,total", [("NUE", 7_099_000_000), ("STLD", 4_182_142_000)])
def test_unclassified_nci_group_reconciles_complete_debt_scope(ticker, total):
    availability, proof = _bind(ticker)
    assert availability.value == total
    assert availability.extraction_complete
    assert proof["total"] == total


@pytest.mark.parametrize("ticker,total", [
    ("AVY", 3_678_200_000), ("BALL", 7_177_000_000), ("MPC", 33_255_000_000),
])
def test_operating_reserve_group_reconciles_complete_debt_scope(ticker, total):
    availability, proof = _bind(ticker)
    assert availability.value == total
    assert availability.extraction_complete
    assert proof["total"] == total


@pytest.mark.parametrize("ticker,total", [("DASH", 2_727_000_000), ("ICE", 19_846_000_000)])
def test_customer_funds_group_reconciles_complete_debt_scope(ticker, total):
    availability, proof = _bind(ticker)
    assert availability.value == total
    assert availability.extraction_complete
    assert proof["total"] == total


def test_msci_acquisition_group_reconciles_carrying_debt_scope():
    availability,proof=_bind("MSCI")
    assert availability.value==6_380_400_000
    assert availability.extraction_complete and proof["total"]==6_380_400_000


def test_kdp_typed_financing_group_reconciles_debt_and_lease_scope():
    structural=json.loads(SOURCES['KDP'].read_text());structural={**structural,'report_date':'2026-06-30'}
    availability,proof=_bind('KDP',structural)
    assert availability.value==31_006_000_000
    assert availability.extraction_complete and proof['total']==31_006_000_000


def test_msci_zero_outside_equity_requires_parent_balance_sheet_close():
    structural=json.loads(SOURCES["MSCI"].read_text());policy=dict(OUTSIDE_EQUITY_ZERO_RULES["MSCI"])
    availability,proof=outside_equity_zero_availability(
        ticker="MSCI",policy=policy,structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert availability.state=="evidence_backed_zero" and availability.value==0


def test_msci_preferred_zero_reconciles_negative_common_equity():
    structural=json.loads(SOURCES["MSCI"].read_text());policy=dict(PREFERRED_EQUITY_ZERO_RULES["MSCI"])
    availability,proof=preferred_equity_zero_availability(
        ticker="MSCI",policy=policy,structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert availability.state=="evidence_backed_zero" and availability.value==0
    assert proof["component_sum"]==proof["parent_equity"]==-2_689_500_000


def test_kdp_common_equity_zero_preferred_keeps_temporary_claim_separate():
    structural=json.loads(SOURCES['KDP'].read_text());structural={**structural,'report_date':'2026-06-30'}
    policy=dict(PREFERRED_EQUITY_ZERO_RULES['KDP'])
    availability,proof=preferred_equity_zero_availability(
        ticker='KDP',policy=policy,structural_packet=structural,
        accession=structural['source_accession'],period_end=structural['report_date'])
    assert availability.state=='evidence_backed_zero' and availability.value==0
    assert proof['component_sum']==proof['parent_equity']==25_032_000_000
    assert {row['qname'] for row in proof['outside_equity_components']}=={
        'us-gaap:TemporaryEquityCarryingAmountAttributableToParent',
        'us-gaap:TemporaryEquityLiquidationPreference'}


def test_ice_complete_issuer_scope_has_no_marketable_securities():
    structural=json.loads(SOURCES["ICE"].read_text());rule=AGGREGATE_DEBT_SCOPE_RULES["ICE"]
    records,proof=nonmarketable_investment_zero_availabilities(
        ticker="ICE",policy=asdict(rule),structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert {row.field for row in records}=={"marketable_securities_current","marketable_securities_noncurrent"}
    assert all(row.state=="evidence_backed_zero" for row in records)


@pytest.mark.parametrize("ticker", ["NUE", "STLD"])
def test_unclassified_nci_group_proves_noncurrent_marketable_absence(ticker):
    structural = json.loads(SOURCES[ticker].read_text())
    rule = AGGREGATE_DEBT_SCOPE_RULES[ticker]
    records, proof = nonmarketable_investment_zero_availabilities(
        ticker=ticker,
        policy=asdict(rule),
        structural_packet=structural,
        accession=structural["source_accession"],
        period_end=structural["report_date"],
    )
    assert {row.field for row in records} == {"marketable_securities_noncurrent"}
    assert all(row.state == "evidence_backed_zero" and row.extraction_complete for row in records)
    assert proof["marketable_securities"] == 0.0


@pytest.mark.parametrize("ticker", ["CTSH","VRTX","VRT"])
def test_wg2_zero_nci_requires_exact_parent_only_balance_sheet(ticker):
    structural=json.loads(SOURCES[ticker].read_text()); policy=dict(OUTSIDE_EQUITY_ZERO_RULES[ticker])
    availability,proof=outside_equity_zero_availability(
        ticker=ticker,policy=policy,structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert availability.state=="evidence_backed_zero"
    assert availability.value==0
    assert proof["totals"]["us-gaap:Assets"]==proof["totals"]["us-gaap:LiabilitiesAndStockholdersEquity"]


def test_wg2_zero_nci_rejects_balance_sheet_residual():
    structural=json.loads(SOURCES["CTSH"].read_text());tampered=copy.deepcopy(structural)
    for row in tampered["facts"]:
        if row.get("qname")=="us-gaap:Liabilities" and row.get("period_end")==tampered["report_date"] and not row.get("dimensions"):
            row["value"]+=1
    with pytest.raises(BridgeScopeReviewRequired,match="does not close"):
        outside_equity_zero_availability(ticker="CTSH",policy=dict(OUTSIDE_EQUITY_ZERO_RULES["CTSH"]),
            structural_packet=tampered,accession=tampered["source_accession"],period_end=tampered["report_date"])


def test_mco_total_must_reconcile_to_disjoint_components():
    structural = json.loads(SOURCES["MCO"].read_text())
    tampered = copy.deepcopy(structural)
    for row in tampered["facts"]:
        if row.get("qname") == "us-gaap:LongTermDebt" and row.get("period_end") == tampered["report_date"] and not row.get("dimensions"):
            row["value"] += 1
    with pytest.raises(BridgeScopeReviewRequired, match="does not reconcile"):
        _bind("MCO", tampered)


def test_rok_dimensioned_commercial_paper_is_required_as_containment_proof():
    structural = json.loads(SOURCES["ROK"].read_text())
    tampered = copy.deepcopy(structural)
    for row in tampered["facts"]:
        if row.get("qname") == "us-gaap:ShortTermBorrowings" and row.get("dimensions"):
            row["dimensions"] = [["us-gaap:OtherAxis", "us-gaap:CommercialPaperMember"]]
    with pytest.raises(BridgeScopeReviewRequired, match="commercial paper"):
        _bind("ROK", tampered)


def test_policy_identity_is_immutable_but_does_not_contain_filing_date_or_amount():
    rule = AGGREGATE_DEBT_SCOPE_RULES["ROK"]
    policy = asdict(rule)
    assert "accession" not in policy and "period_end" not in policy and "amount" not in policy
    policy["version"] = "tampered"
    structural = json.loads(SOURCES["ROK"].read_text())
    with pytest.raises(BridgeScopeReviewRequired, match="identity/version mismatch"):
        aggregate_debt_field_availability(ticker="ROK", policy=policy,
            structural_packet=structural, accession=structural["source_accession"],
            period_end=structural["report_date"])


@pytest.mark.parametrize("ticker", ["MCO", "ROK"])
def test_compiled_policy_excludes_generic_nonmarketable_long_term_investments(ticker):
    from app.us_valuation.refresh_operating_policies import _policy_for_entry
    from app.us_valuation.xbrl import load_concept_config
    runtime = ROOT / "output/us-refresh-runtime"
    registry = json.loads((runtime / "registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == ticker)
    recipe = json.loads((runtime / f"recipes/{ticker}.json").read_text())
    artifact = json.loads((runtime / f"baseline/artifacts/{ticker}.json").read_text())
    compiled = _policy_for_entry(entry, artifact=artifact, recipe=recipe,
                                 source_evidence=None, concept_config=load_concept_config())
    concepts = compiled.policy["concept_config"]["fields"]["marketable_securities_noncurrent"]["concepts"]
    assert "LongTermInvestments" not in concepts
    assert compiled.policy["aggregate_debt_scope"]["ticker"] == ticker


def test_rok_nonmarketable_investment_scope_is_reconciled_not_missing_as_zero():
    structural = json.loads(SOURCES["ROK"].read_text())
    rule = AGGREGATE_DEBT_SCOPE_RULES["ROK"]
    records, proof = nonmarketable_investment_zero_availabilities(
        ticker="ROK", policy=asdict(rule), structural_packet=structural,
        accession=structural["source_accession"], period_end=structural["report_date"])
    assert {row.field for row in records} == {
        "marketable_securities_current", "marketable_securities_noncurrent"}
    assert all(row.state == "evidence_backed_zero" and row.extraction_complete for row in records)
    assert proof["excluded_total"] == 187_000_000
    assert sum(row["value"] for row in proof["components"][1:]) == proof["excluded_total"]


def test_mco_other_asset_placement_excludes_generic_long_term_investment():
    structural = json.loads(SOURCES["MCO"].read_text())
    rule = AGGREGATE_DEBT_SCOPE_RULES["MCO"]
    records, proof = nonmarketable_investment_zero_availabilities(
        ticker="MCO", policy=asdict(rule), structural_packet=structural,
        accession=structural["source_accession"], period_end=structural["report_date"])
    assert {row.field for row in records} == {"marketable_securities_noncurrent"}
    assert all(row.state == "evidence_backed_zero" for row in records)
    assert proof["excluded_total"] == 103_000_000


def test_vrt_current_security_and_noncurrent_absence_are_separate():
    structural=json.loads(SOURCES["VRT"].read_text());rule=AGGREGATE_DEBT_SCOPE_RULES["VRT"]
    records,proof=nonmarketable_investment_zero_availabilities(
        ticker="VRT",policy=asdict(rule),structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert {row.field for row in records}=={"marketable_securities_noncurrent"}
    assert proof["excluded_total"] is None
    assert proof["components"][0]["value"]==300_000_000


def test_coo_complete_current_scope_has_no_marketable_securities():
    structural=json.loads(SOURCES["COO"].read_text());rule=AGGREGATE_DEBT_SCOPE_RULES["COO"]
    records,proof=nonmarketable_investment_zero_availabilities(
        ticker="COO",policy=asdict(rule),structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert {row.field for row in records}=={"marketable_securities_current","marketable_securities_noncurrent"}
    assert all(row.state=="evidence_backed_zero" for row in records)
    assert proof["components"][0]["qname"]=="us-gaap:CashAndCashEquivalentsAtCarryingValue"


def test_abbv_preferred_zero_uses_complete_reported_common_components():
    structural=json.loads(SOURCES["ABBV"].read_text());policy=dict(PREFERRED_EQUITY_ZERO_RULES["ABBV"])
    availability,proof=preferred_equity_zero_availability(
        ticker="ABBV",policy=policy,structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert availability.state=="evidence_backed_zero" and availability.value==0
    assert proof["component_sum"]==proof["parent_equity"]==-5_935_000_000


def test_ball_preferred_zero_uses_complete_reported_common_components():
    structural=json.loads(SOURCES["BALL"].read_text());policy=dict(PREFERRED_EQUITY_ZERO_RULES["BALL"])
    availability,proof=preferred_equity_zero_availability(
        ticker="BALL",policy=policy,structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert availability.state=="evidence_backed_zero" and availability.value==0
    assert proof["component_sum"]==proof["parent_equity"]==5_746_000_000


def test_dash_preferred_zero_keeps_temporary_equity_in_separate_outside_owner_scope():
    structural=json.loads(SOURCES["DASH"].read_text())
    structural={**structural,"report_date":"2026-06-30"}
    policy=dict(PREFERRED_EQUITY_ZERO_RULES["DASH"])
    availability,proof=preferred_equity_zero_availability(
        ticker="DASH",policy=policy,structural_packet=structural,
        accession=structural["source_accession"],period_end=structural["report_date"])
    assert availability.state=="evidence_backed_zero" and availability.value==0
    assert proof["component_sum"]==proof["parent_equity"]==9_921_000_000
    assert proof["outside_equity_components"]==[{
        "qname":"us-gaap:TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
        "value":11_000_000.0}]


def test_rok_nonmarketable_investment_scope_rejects_new_marketable_fact():
    structural = json.loads(SOURCES["ROK"].read_text())
    tampered = copy.deepcopy(structural)
    exemplar = next(row for row in tampered["facts"] if row.get("qname") == "us-gaap:LongTermInvestments" and row.get("period_end") == tampered["report_date"] and not row.get("dimensions"))
    injected = copy.deepcopy(exemplar)
    injected["qname"] = "us-gaap:MarketableSecuritiesNoncurrent"
    injected["local_name"] = "MarketableSecuritiesNoncurrent"
    tampered["facts"].append(injected)
    rule = AGGREGATE_DEBT_SCOPE_RULES["ROK"]
    with pytest.raises(BridgeScopeReviewRequired, match="requires direct classification"):
        nonmarketable_investment_zero_availabilities(ticker="ROK", policy=asdict(rule),
            structural_packet=tampered, accession=tampered["source_accession"],
            period_end=tampered["report_date"])
