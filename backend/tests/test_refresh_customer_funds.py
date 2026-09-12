from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_customer_funds import customer_funds_policy, select_customer_funds


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "DASH": ROOT / "output/batch-08-structural-sources-20260826/DASH/structural-filing.json",
    "ICE": ROOT / "output/batch-40-structural-sources-20260907/ICE/structural-filing.json",
}


def _source(ticker):
    structural = json.loads(SOURCES[ticker].read_text())
    if ticker == "DASH":
        filing = {
            "accessionNumber": "0001792789-26-000050",
            "reportDate": "2026-06-30",
            "filingDate": "2026-08-05",
            "form": "10-Q",
        }
    else:
        filing = {
            "accessionNumber": structural["source_accession"],
            "reportDate": structural["report_date"],
            "filingDate": structural["filed_date"],
            "form": structural["form"],
        }
    policy = customer_funds_policy(ticker)
    return policy, structural, filing


def test_dash_reserves_customer_prepayments_from_cash_without_netting_operating_balances():
    policy, structural, filing = _source("DASH")
    result = select_customer_funds(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert (result["bear_cash_reserve"], result["base_cash_reserve"], result["bull_cash_reserve"]) == (
        554_000_000, 277_000_000, 0,
    )
    components = result["components"]
    assert components["unreserved_cash_and_investments"] == 6_216_000_000
    assert components["restricted_cash_current"] + components["restricted_cash_noncurrent"] == 422_000_000
    assert components["processor_held_funds_operating"] == 513_000_000
    assert components["merchant_payable_operating"] == 1_714_000_000
    assert components["temporary_equity_separate_claim"] == 11_000_000
    assert components["customer_contract_liability"] == 554_000_000


def test_ice_reconciles_issuer_restricted_and_member_cash_without_creating_a_claim():
    policy, structural, filing = _source("ICE")
    result = select_customer_funds(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound" and result["claim_adjustment"] == 0
    components = result["components"]
    assert components["issuer_cash"] == 1_067_000_000
    assert components["matched_member_margin_asset"] == components["matched_member_margin_liability"] == 114_599_000_000
    assert components["matched_settlement_receivable"] == components["matched_settlement_payable"] == 2_313_000_000
    assert components["clearing_assets_total"] == 116_912_000_000
    assert components["restricted_cash_current"] == 627_000_000
    assert components["restricted_cash_noncurrent"] == 260_000_000
    assert components["gross_pledged_collateral_not_additive"] == 235_300_000_000
    assert components["net_customer_fund_claim"] == 0


@pytest.mark.parametrize("ticker", ["DASH", "ICE"])
def test_customer_fund_policies_have_no_filing_amount_or_date_constants_and_reject_tampering(ticker):
    policy, structural, filing = _source(ticker)
    assert not {"accession", "filed_date", "period_end", "amount"} & set(policy)
    changed = copy.deepcopy(policy)
    changed["version"] = "tampered"
    with pytest.raises(RuntimeError, match="identity/version mismatch"):
        select_customer_funds(changed, structural, filing, policy["cik"], "2026-08-14")


def test_ice_unmatched_member_liability_fails_closed():
    policy, structural, filing = _source("ICE")
    changed = copy.deepcopy(structural)
    row = next(
        item for item in changed["facts"]
        if item.get("local_name") == policy["margin_liability_local_name"]
        and item.get("period_end") == filing["reportDate"]
        and item.get("period_start") is None
        and not item.get("dimensions")
    )
    row["value"] += 1
    with pytest.raises(ValueError, match="do not match"):
        select_customer_funds(policy, changed, filing, policy["cik"], "2026-08-14")


def test_dash_restricted_cash_reconciliation_fails_closed():
    policy, structural, filing = _source("DASH")
    changed = copy.deepcopy(structural)
    row = next(
        item for item in changed["facts"]
        if item.get("qname") == policy["restricted_current_qname"]
        and item.get("period_end") == filing["reportDate"]
        and item.get("period_start") is None
        and not item.get("dimensions")
    )
    row["value"] += 1
    with pytest.raises(ValueError, match="conflicts|cash-flow total"):
        select_customer_funds(policy, changed, filing, policy["cik"], "2026-08-14")
