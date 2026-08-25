"""Cumulative post-recovery withheld-register contracts."""

from app.us_valuation.universe_reset_withheld import (
    UniverseResetWithheldEntry,
    load_universe_reset_withheld,
)
import pytest


def test_register_contains_nee_then_exact_batch_02_post_recovery_set() -> None:
    entries = load_universe_reset_withheld()
    assert len(entries) == 7
    entry = entries[0]
    assert (entry.batch, entry.ticker, entry.cik) == (1, "NEE", "0000753308")
    assert entry.recovery_attempts == 1
    assert entry.pipeline_revision_retries == 0
    assert entry.revision_retry_report is None
    assert entry.final_outcome == "withheld"
    assert entry.hard_blockers == ("NONFINITE_OR_NONPOSITIVE_VALUE",)
    batch_02 = entries[1:]
    assert tuple(row.ticker for row in batch_02) == (
        "OMC",
        "TTWO",
        "CHTR",
        "CMCSA",
        "META",
        "WBD",
    )
    assert all(row.batch == 2 for row in batch_02)
    assert all(row.recovery_attempts == 1 for row in batch_02)
    assert all(row.pipeline_revision_retries == 1 for row in batch_02)
    assert all(
        row.revision_retry_report
        == "docs/audit/31-batch-02-revised-pipeline-retry-result.md"
        for row in batch_02
    )
    assert all(row.final_outcome == "withheld" for row in batch_02)
    assert all(
        row.evidence_report == "docs/audit/18-batch-02-recovery-result.md"
        for row in batch_02
    )


def test_register_contract_rejects_more_than_one_recovery() -> None:
    value = {
        "batch": 2,
        "ticker": "TEST",
        "cik": "0000000001",
        "issuer_name": "Test",
        "model_version": "TEST-1",
        "recovery_attempts": 2,
        "final_outcome": "withheld",
        "reason_codes": ["TEST_REASON"],
        "hard_blockers": ["TEST_BLOCKER"],
        "evidence_report": "docs/test.md",
    }
    try:
        UniverseResetWithheldEntry.from_dict(value)
    except ValueError as error:
        assert "exactly one" in str(error)
    else:
        raise AssertionError("more than one recovery attempt must be rejected")


def test_register_contract_keeps_explicit_revision_retry_separate() -> None:
    value = {
        "batch": 2,
        "ticker": "TEST",
        "cik": "0000000001",
        "issuer_name": "Test",
        "model_version": "TEST-1",
        "recovery_attempts": 1,
        "pipeline_revision_retries": 1,
        "revision_retry_report": "docs/retry.md",
        "final_outcome": "withheld",
        "reason_codes": ["TEST_REASON"],
        "hard_blockers": ["TEST_BLOCKER"],
        "evidence_report": "docs/test.md",
    }
    entry = UniverseResetWithheldEntry.from_dict(value)
    assert entry.recovery_attempts == 1
    assert entry.pipeline_revision_retries == 1
    assert entry.revision_retry_report == "docs/retry.md"

    value["pipeline_revision_retries"] = 2
    with pytest.raises(ValueError, match="zero or one"):
        UniverseResetWithheldEntry.from_dict(value)
