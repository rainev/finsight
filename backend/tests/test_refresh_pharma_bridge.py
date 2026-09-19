from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_pharma_bridge import bind_pharma_bridge, pharma_bridge_policy


ROOT = Path(__file__).resolve().parents[2]
STRUCTURAL = ROOT / "output" / "batch-14-structural-sources-20260829"
CONTROL = {
    "BIIB": ("0000875045-26-000075", "2026-06-30"),
    "GILD": ("0000882095-26-000031", "2026-06-30"),
    "INCY": ("0000879169-26-000056", "2026-06-30"),
}


def _packet(ticker: str) -> dict:
    return json.loads((STRUCTURAL / ticker / "structural-filing.json").read_text())


def _run(ticker: str, packet: dict | None = None):
    accession, period = CONTROL[ticker]
    return bind_pharma_bridge(pharma_bridge_policy(ticker), packet or _packet(ticker),
                              accession=accession, period=period)


def test_gild_cash_debt_and_royalty_component_are_counted_once():
    records, proof = _run("GILD")
    assert {row.field: row.value for row in records} == {
        "cash": 3_179_000_000,
        "marketable_securities_current": 0,
        "marketable_securities_noncurrent": 0,
        "total_interest_bearing_debt": 26_246_000_000,
    }
    assert proof["current_debt"] == 2_414_000_000
    assert proof["noncurrent_debt"] == 23_832_000_000
    assert proof["royalty_debt_component"] == 1_077_000_000
    assert proof["royalty_carrying_disclosure"] == 1_100_000_000
    assert proof["royalty_fair_value_diagnostic"] == 700_000_000
    assert proof["royalty_principal_financing_reduction"] == 33_000_000
    assert proof["matured_note_financing_reduction"] == 2_750_000_000
    assert proof["reported_financing_repayments"] == 2_783_000_000
    assert "included once" in proof["royalty_treatment"]


def test_incy_marketables_finance_leases_and_strategic_investments_are_separate():
    records, proof = _run("INCY")
    assert {row.field: row.value for row in records} == {
        "marketable_securities_current": 553_365_000,
        "marketable_securities_noncurrent": 0,
        "total_interest_bearing_debt": 32_679_000,
    }
    assert proof["strategic_equity_investments_excluded_from_cash"] == 104_387_000
    assert proof["revolving_credit_borrowing"] == 0
    assert sum(proof["strategic_investment_hierarchy"].values()) == 104_387_000


def test_gild_rejects_debt_total_that_no_longer_reconciles():
    packet = deepcopy(_packet("GILD"))
    for row in packet["facts"]:
        if (row.get("qname") == "us-gaap:LongTermDebt" and row.get("period_end") == "2026-06-30"
                and row.get("period_start") is None and not row.get("dimensions")):
            row["value"] += 100_000_000
    with pytest.raises(ValueError, match="do not reconcile to total"):
        _run("GILD", packet)


def test_gild_rejects_missing_royalty_debt_component():
    packet = deepcopy(_packet("GILD"))
    packet["facts"] = [row for row in packet["facts"] if not (
        row.get("qname") == "us-gaap:LongTermDebt"
        and dict(row.get("dimensions") or []).get("us-gaap:LongtermDebtTypeAxis")
        == "us-gaap:NotesPayableOtherPayablesMember"
        and row.get("period_end") == "2026-06-30")]
    with pytest.raises(ValueError, match="required fact is missing"):
        _run("GILD", packet)


def test_incy_rejects_new_noncurrent_marketable_debt_security():
    packet = deepcopy(_packet("INCY"))
    source = next(row for row in packet["facts"] if row.get("qname")
                  == "us-gaap:DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent"
                  and row.get("period_end") == "2026-06-30" and not row.get("dimensions"))
    added = deepcopy(source)
    added["qname"] = "us-gaap:DebtSecuritiesAvailableForSaleExcludingAccruedInterestNoncurrent"
    added["local_name"] = "DebtSecuritiesAvailableForSaleExcludingAccruedInterestNoncurrent"
    packet["facts"].append(added)
    with pytest.raises(ValueError, match="separate noncurrent marketable debt security"):
        _run("INCY", packet)


def test_incy_rejects_strategic_investment_hierarchy_conflict():
    packet = deepcopy(_packet("INCY"))
    for row in packet["facts"]:
        if (row.get("qname") == "us-gaap:EquitySecuritiesFVNINoncurrent"
                and dict(row.get("dimensions") or []).get("us-gaap:FairValueByFairValueHierarchyLevelAxis")
                == "us-gaap:FairValueInputsLevel3Member" and row.get("period_end") == "2026-06-30"):
            row["value"] += 1_000_000
    with pytest.raises(ValueError, match="hierarchy does not reconcile"):
        _run("INCY", packet)


@pytest.mark.parametrize("ticker", ["BIIB", "GILD", "INCY"])
def test_policy_contains_no_filing_amounts_or_dates(ticker: str):
    encoded = json.dumps(pharma_bridge_policy(ticker), sort_keys=True)
    assert "2026-" not in encoded
    assert not any(amount in encoded for amount in (
        "1285000000", "8090300000", "3179000000", "26246000000", "553365000", "32679000"))


def test_biib_period_end_cash_and_split_debt_are_complete_without_double_counting():
    records, proof = _run("BIIB")
    assert {row.field: row.value for row in records} == {
        "cash": 1_285_000_000,
        "marketable_securities_current": 0,
        "marketable_securities_noncurrent": 0,
        "total_interest_bearing_debt": 8_090_300_000,
    }
    assert proof["current_debt"] == 800_000_000
    assert proof["noncurrent_debt"] == 7_290_300_000
