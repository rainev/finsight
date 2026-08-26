"""Durable not-fully-recovered watchlist contracts."""

import pytest

from app.us_valuation.universe_reset_recovery_learning_watchlist import (
    CALL_NAME,
    TITLE,
    RecoveryLearningEntry,
    load_recovery_learning_watchlist,
)
from app.us_valuation.universe_reset_withheld import load_universe_reset_withheld


def test_recovery_learning_watchlist_has_a_stable_name_and_exact_current_set() -> None:
    assert TITLE == "Universe Reset Recovery Learning Watchlist"
    assert CALL_NAME == "Recovery Learning Watchlist"
    entries = load_recovery_learning_watchlist()
    assert tuple(row.ticker for row in entries) == (
        "NEE",
        "OMC",
        "TTWO",
        "CHTR",
        "CMCSA",
        "META",
        "WBD",
        "LYV",
        "ECHO",
        "GOOGL",
        "APP",
        "FOXA",
        "TKO",
        "PSKY",
        "F",
        "GPC",
        "HAS",
        "LOW",
        "NKE",
        "MGM",
        "CCL",
        "PHM",
        "SBUX",
        "DHI",
        "RCL",
        "NVR",
        "LEN",
        "AMZN",
        "YUM",
        "EL",
        "BKNG",
        "WYNN",
        "LVS",
        "TSLA",
        "EXPE",
        "LULU",
        "KDP",
        "GM",
        "NCLH",
        "APTV",
        "ABNB",
        "CVNA",
        "DASH",
        "ADM",
        "STZ",
        "CLX",
        "KO",
        "TAP",
        "TGT",
        "DG",
        "GIS",
        "KMB",
        "MKC",
        "SJM",
        "TSN",
    )
    assert entries[0].current_status == "withheld_after_recovery"
    assert all(row.initial_outcome == "withheld" for row in entries if row.batch <= 6)
    assert all(row.initial_outcome == "conditional_numeric_low" for row in entries if row.batch == 7)
    assert all(row.initial_outcome == "conditional_numeric_low" for row in entries if row.batch == 9 and row.ticker != "CLX")
    assert all(row.initial_outcome == "conditional_numeric_low" for row in entries if row.batch == 10 and row.ticker != "KMB")
    assert all(
        row.recovery_outcome in {"withheld", "conditional_numeric_low", "not_applicable"}
        for row in entries
    )
    assert all(
        row.current_status.startswith("conditional_numeric_low")
        for row in entries[1:7]
    )
    batch_03 = entries[7:]
    assert sum(row.current_status.startswith("conditional_numeric_low") for row in batch_03[:7]) == 5
    assert sum(row.current_status == "withheld_after_recovery" for row in batch_03[:7]) == 2
    assert all(row.current_status in {"withheld_after_recovery","conditional_numeric_low","conditional_numeric_low_equity_at_risk"} for row in entries[14:])
    batch_04=[row for row in entries if row.batch==4]
    assert tuple(row.ticker for row in batch_04)==("F","GPC","HAS","LOW","NKE","MGM")
    batch_05=[row for row in entries if row.batch==5]
    assert sum(row.current_status=="conditional_numeric_low_equity_at_risk" for row in batch_05)==2
    batch_06=[row for row in entries if row.batch==6]
    assert sum(row.current_status=="conditional_numeric_low_equity_at_risk" for row in batch_06)==1
    batch_07=[row for row in entries if row.batch==7]
    assert tuple(row.ticker for row in batch_07)==("EL","BKNG","WYNN","LVS","TSLA","EXPE")
    assert all(row.recovery_outcome=="not_applicable" for row in batch_07)
    assert sum(row.current_status=="conditional_numeric_low_equity_at_risk" for row in batch_07)==2
    batch_08=[row for row in entries if row.batch==8]
    assert tuple(row.ticker for row in batch_08)==("LULU","KDP","GM","NCLH","APTV","ABNB","CVNA","DASH")
    assert all(row.recovery_outcome=="not_applicable" for row in batch_08 if row.ticker in {"LULU","KDP","GM","ABNB","CVNA","DASH"})
    assert next(row for row in batch_08 if row.ticker=="NCLH").recovery_outcome=="withheld"
    assert next(row for row in batch_08 if row.ticker=="APTV").recovery_outcome=="conditional_numeric_low"
    assert sum(row.current_status=="conditional_numeric_low_equity_at_risk" for row in batch_08)==2
    batch_09=[row for row in entries if row.batch==9]
    assert tuple(row.ticker for row in batch_09)==("ADM","STZ","CLX","KO","TAP","TGT","DG","GIS")
    assert all(row.recovery_outcome=="not_applicable" for row in batch_09 if row.ticker!="CLX")
    assert next(row for row in batch_09 if row.ticker=="CLX").recovery_outcome=="conditional_numeric_low"
    batch_10=[row for row in entries if row.batch==10]
    assert tuple(row.ticker for row in batch_10)==("KMB","MKC","SJM","TSN")
    assert all(row.recovery_outcome=="not_applicable" for row in batch_10 if row.ticker!="KMB")
    assert next(row for row in batch_10 if row.ticker=="KMB").recovery_outcome=="conditional_numeric_low"
    assert all(row.learning_themes for row in entries)
    assert all(row.revisit_triggers for row in entries)
    assert all(row.evidence_reports for row in entries)


def test_current_withheld_register_is_fully_bookmarked_without_changing_semantics() -> None:
    withheld = load_universe_reset_withheld()
    watchlist = load_recovery_learning_watchlist()
    assert {(row.ticker,row.cik) for row in withheld}.issubset({(row.ticker,row.cik) for row in watchlist})
    assert sum(row.current_status == "withheld_after_recovery" for row in watchlist) == 4
    assert sum(row.current_status.startswith("conditional_numeric_low") for row in watchlist) == 51


def test_watchlist_rejects_a_fully_recovered_or_unclassified_status() -> None:
    value = {
        "batch": 3,
        "ticker": "TEST",
        "cik": "0000000001",
        "issuer_name": "Test",
        "initial_outcome": "withheld",
        "recovery_outcome": "withheld",
        "current_status": "fully_recovered",
        "provisional_model": "test",
        "why_not_fully_recovered": "test",
        "learning_themes": ["test"],
        "revisit_triggers": ["test"],
        "evidence_reports": ["docs/test.md"],
    }
    with pytest.raises(ValueError, match="status"):
        RecoveryLearningEntry.from_dict(value)

    value["current_status"] = "withheld_after_recovery"
    value["initial_outcome"] = "numeric"
    with pytest.raises(ValueError, match="initial pass"):
        RecoveryLearningEntry.from_dict(value)

    value["initial_outcome"] = "conditional_numeric_low"
    value["recovery_outcome"] = "conditional_numeric_low"
    with pytest.raises(ValueError, match="do not receive"):
        RecoveryLearningEntry.from_dict(value)
