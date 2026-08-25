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
        "MCD",
        "TJX",
        "NKE",
        "HD",
        "ROST",
        "MGM",
        "WSM",
        "CASY",
        "CCL",
        "PHM",
        "SBUX",
        "AZO",
        "DHI",
        "RCL",
        "ORLY",
        "NVR",
    )
    assert entries[0].current_status == "withheld_after_recovery"
    assert all(row.initial_outcome == "withheld" for row in entries)
    assert all(
        row.recovery_outcome in {"withheld", "conditional_numeric_low"}
        for row in entries
    )
    assert all(
        row.current_status.startswith("conditional_numeric_low")
        for row in entries[1:7]
    )
    batch_03 = entries[7:]
    assert sum(row.current_status.startswith("conditional_numeric_low") for row in batch_03[:7]) == 5
    assert sum(row.current_status == "withheld_after_recovery" for row in batch_03[:7]) == 2
    assert all(row.current_status.startswith("conditional_numeric_low") for row in entries[14:])
    assert tuple(row.current_status for row in entries[24:]) == (
        "conditional_numeric_low",
        "conditional_numeric_low",
        "conditional_numeric_low_equity_at_risk",
        "conditional_numeric_low",
        "conditional_numeric_low",
        "conditional_numeric_low",
        "conditional_numeric_low",
        "conditional_numeric_low_equity_at_risk",
        "conditional_numeric_low",
        "conditional_numeric_low",
    )
    assert all(row.learning_themes for row in entries)
    assert all(row.revisit_triggers for row in entries)
    assert all(row.evidence_reports for row in entries)


def test_current_withheld_register_is_fully_bookmarked_without_changing_semantics() -> None:
    withheld = load_universe_reset_withheld()
    watchlist = load_recovery_learning_watchlist()
    assert {(row.ticker, row.cik) for row in watchlist if row.batch <= 2} == {
        (row.ticker, row.cik) for row in withheld
    }
    assert sum(row.current_status == "withheld_after_recovery" for row in watchlist) == 3
    assert sum(row.current_status.startswith("conditional_numeric_low") for row in watchlist) == 31


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
