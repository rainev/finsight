"""Cumulative post-recovery withheld-register contracts."""

from app.us_valuation.universe_reset_withheld import (
    UniverseResetWithheldEntry,
    load_universe_reset_withheld,
)
import pytest


def test_register_contains_exact_post_batch_16_recovery_set() -> None:
    entries = load_universe_reset_withheld()
    assert len(entries) == 19
    entry = entries[0]
    assert (entry.batch, entry.ticker, entry.cik) == (1, "NEE", "0000753308")
    assert entry.recovery_attempts == 1
    assert entry.pipeline_revision_retries == 0
    assert entry.revision_retry_report is None
    assert entry.final_outcome == "withheld"
    assert entry.hard_blockers == ("NONFINITE_OR_NONPOSITIVE_VALUE",)
    batch_02 = entries[1:7]
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
    nclh=entries[7]
    assert (nclh.batch,nclh.ticker,nclh.cik)==(8,"NCLH","0001513761")
    assert nclh.recovery_attempts==1
    assert nclh.hard_blockers==("CLAIMS_UNBOUNDED","MODEL_UNSUPPORTED")
    assert nclh.evidence_report=="docs/audit/57-batch-08-recovery-result.md"
    bg=entries[8]
    assert (bg.batch,bg.ticker,bg.cik)==(11,"BG","0001996862")
    assert bg.recovery_attempts==1
    assert bg.model_version=="BATCH-11-SYY-BG-RECOVERY-1.0"
    assert bg.hard_blockers==(
        "PREDECESSOR_HISTORY_NOT_COMPARABLE",
        "PRO_FORMA_CASH_FLOW_NOT_DISCLOSED",
        "NONFINITE_OR_NONPOSITIVE_VALUE",
    )
    assert bg.evidence_report=="docs/audit/66-batch-11-recovery-result.md"
    uhs=entries[9]
    assert (uhs.batch,uhs.ticker,uhs.cik)==(12,"UHS","0000352915")
    assert uhs.recovery_attempts==1
    assert uhs.model_version=="BATCH-12-WHOLE-RECOVERY-1.0"
    assert uhs.hard_blockers==(
        "POST_PERIOD_CASH_DEBT_STATE_UNAVAILABLE",
        "POST_PERIOD_OPERATING_STATE_CHANGED",
        "PENDING_TRANSACTION_FINANCING_UNRESOLVED",
    )
    assert uhs.evidence_report=="docs/audit/69-batch-12-whole-recovery-result.md"
    batch_15=entries[10:13]
    assert tuple(row.ticker for row in batch_15)==("LH","ISRG","ALGN")
    assert all(row.batch==15 for row in batch_15)
    assert all(row.recovery_attempts==1 for row in batch_15)
    assert all(row.model_version=="BATCH-15-WITHHELD-RECOVERY-1.0" for row in batch_15)
    assert all(row.hard_blockers==("CLAIMS_UNBOUNDED",) for row in batch_15)
    assert all(row.evidence_report=="docs/audit/76-batch-15-recovery-result.md" for row in batch_15)
    batch_16=entries[13:]
    assert tuple(row.ticker for row in batch_16)==("DXCM","EW","CRL","ZBH","COR","ELV")
    assert all(row.batch==16 for row in batch_16)
    assert all(row.recovery_attempts==1 for row in batch_16)
    assert all(row.model_version=="BATCH-16-WITHHELD-RECOVERY-1.0" for row in batch_16)
    assert all(row.reason_codes==("SPECIALIST_MODEL_UNCERTAINTY",) for row in batch_16)
    assert all(row.hard_blockers==("CLAIMS_UNBOUNDED",) for row in batch_16)
    assert all(row.evidence_report=="docs/audit/80-batch-16-recovery-result.md" for row in batch_16)


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
