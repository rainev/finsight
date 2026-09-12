from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_acquisition_financing_claims import (
    acquisition_financing_policy,
    select_acquisition_financing_claim,
)


ROOT=Path(__file__).resolve().parents[2]
SOURCES={
    "KDP":ROOT/"output/batch-08-structural-sources-20260826/KDP/structural-filing.json",
    "MSCI":ROOT/"output/batch-40-structural-sources-20260907/MSCI/structural-filing.json",
}


def _source(ticker):
    structural=json.loads(SOURCES[ticker].read_text())
    filing={
        "accessionNumber":structural["source_accession"],
        "reportDate":structural.get("report_date") or "2026-06-30",
        "filingDate":structural.get("filed_date") or "2026-08-10",
        "form":structural["form"],
    }
    policy=acquisition_financing_policy(ticker)
    return policy,structural,filing


def test_msci_reconciles_recognized_liability_and_keeps_paid_and_pending_cash_separate():
    policy,structural,filing=_source("MSCI")
    result=select_acquisition_financing_claim(policy,structural,filing,policy["cik"],"2026-08-14")
    assert result["status"]=="source_bound"
    assert result["claim_adjustment"]==33_900_000
    assert (result["bear_adjustment"],result["base_adjustment"],result["bull_adjustment"])==(
        153_900_000,93_900_000,33_900_000)
    assert result["restricted_cash_adjustment"]==3_700_000
    assert result["components"]["current_component"]+result["components"]["noncurrent_component"]==33_900_000
    assert result["components"]["paid_cash_not_repeated"]==9_500_000
    assert result["components"]["pending_fixed_price_event"]==120_000_000
    assert result["components"]["pending_unquantified_contingent_payments"] is None


def test_kdp_retains_every_component_but_refuses_amount_fitting_typed_supplier_locations():
    policy,structural,filing=_source("KDP")
    result=select_acquisition_financing_claim(policy,structural,filing,policy["cik"],"2026-08-14")
    assert result["status"]=="review_required" and result["claim_adjustment"] is None
    assert result["review_reasons"]==[
        "typed_supplier_finance_location_members_not_preserved",
    ]
    components=result["components"]
    assert components["nci"]==4_196_000_000
    assert components["temporary_equity_carrying"]==4_418_000_000
    assert components["temporary_equity_liquidation_preference"]==4_500_000_000
    assert components["mandatory_redemption_liability"]==898_000_000
    assert components["supplier_finance_total"]==2_099_000_000
    assert components["supplier_finance_unlabeled_location_values"]==[320_000_000,1_779_000_000]
    assert components["deferred_acquisition_consideration"]==402_000_000
    assert components["acquisition_cash_already_paid"]==16_615_000_000
    assert components["inventory_stepup_in_ocf"]==314_000_000
    assert result['annualized_revenue']==28_258_000_000


def test_kdp_preserved_typed_members_bind_operating_and_financing_without_amount_fit():
    policy,structural,filing=_source("KDP")
    changed=copy.deepcopy(structural)
    for row in changed["facts"]:
        if (row.get("qname")==policy["supplier_total_qname"]
            and row.get("period_end")==filing["reportDate"] and row.get("dimensions")):
            member=(policy["supplier_operating_member"] if row["value"]==1_779_000_000
                    else "ns_765b64f84f:"+policy["supplier_financing_member_local_name"])
            row["typed_dimensions"]=[[policy["supplier_location_axis"],policy["supplier_typed_domain"],member]]
    result=select_acquisition_financing_claim(policy,changed,filing,policy["cik"],"2026-08-14")
    assert result["status"]=="source_bound" and result["review_reasons"]==[]
    assert result["components"]["supplier_finance_operating_accounts_payable"]==1_779_000_000
    assert result["components"]["supplier_finance_structured_financing"]==320_000_000
    assert (result["bear_adjustment"],result["base_adjustment"],result["bull_adjustment"])==(
        6_520_000_000,6_363_000_000,6_038_000_000)
    assert result['annualized_revenue']==28_258_000_000


@pytest.mark.parametrize("ticker",["KDP","MSCI"])
def test_wg9_policies_have_no_filing_amount_or_date_constants_and_reject_tampering(ticker):
    policy,structural,filing=_source(ticker)
    assert not {"accession","filed_date","period_end","amount"}&set(policy)
    changed=copy.deepcopy(policy);changed["version"]="tampered"
    with pytest.raises(RuntimeError,match="identity/version mismatch"):
        select_acquisition_financing_claim(changed,structural,filing,policy["cik"],"2026-08-14")


def test_msci_paid_cash_cannot_be_added_to_current_liability():
    policy,structural,filing=_source("MSCI")
    changed=copy.deepcopy(structural)
    row=next(item for item in changed["facts"] if item.get("qname")==policy["paid_cash_qname"]
             and item.get("period_end")==filing["reportDate"] and not item.get("dimensions"))
    row["value"]=500_000_000
    result=select_acquisition_financing_claim(policy,changed,filing,policy["cik"],"2026-08-14")
    assert result["claim_adjustment"]==33_900_000
    assert result["components"]["paid_cash_not_repeated"]==500_000_000


def test_kdp_supplier_component_drift_fails_closed():
    policy,structural,filing=_source("KDP")
    changed=copy.deepcopy(structural)
    row=next(item for item in changed["facts"] if item.get("qname")==policy["supplier_total_qname"]
             and item.get("period_end")==filing["reportDate"] and item.get("dimensions"))
    row["value"]+=1
    with pytest.raises(ValueError,match="do not reconcile"):
        select_acquisition_financing_claim(policy,changed,filing,policy["cik"],"2026-08-14")
