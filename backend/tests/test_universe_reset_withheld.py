"""Cumulative post-recovery withheld-register contracts."""

from app.us_valuation.universe_reset_withheld import (
    UniverseResetWithheldEntry,
    load_universe_reset_withheld,
)
import pytest


def test_register_contains_exact_post_batch_49_confirmation_set() -> None:
    entries = load_universe_reset_withheld()
    assert len(entries) == 36
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
    batch_16=entries[13:19]
    assert tuple(row.ticker for row in batch_16)==("DXCM","EW","CRL","ZBH","COR","ELV")
    assert all(row.batch==16 for row in batch_16)
    assert all(row.recovery_attempts==1 for row in batch_16)
    assert all(row.model_version=="BATCH-16-WITHHELD-RECOVERY-1.0" for row in batch_16)
    assert all(row.reason_codes==("SPECIALIST_MODEL_UNCERTAINTY",) for row in batch_16)
    assert all(row.hard_blockers==("CLAIMS_UNBOUNDED",) for row in batch_16)
    assert all(row.evidence_report=="docs/audit/80-batch-16-recovery-result.md" for row in batch_16)
    orcl=entries[19]
    assert (orcl.batch,orcl.ticker,orcl.cik)==(31,"ORCL","0001341439")
    assert orcl.recovery_attempts==1
    assert orcl.model_version=="BATCH-31-ORCL-INFRASTRUCTURE-RECOVERY-1.0"
    assert orcl.reason_codes==("SPECIALIST_MODEL_UNCERTAINTY","CAPEX_CASH_CONVERSION_SENSITIVITY")
    assert orcl.hard_blockers==("MODEL_UNSUPPORTED","NONFINITE_OR_NONPOSITIVE_VALUE")
    assert orcl.evidence_report=="docs/audit/118-batch-31-orcl-recovery-result.md"
    vlo=entries[20]
    assert (vlo.batch,vlo.ticker,vlo.cik)==(36,"VLO","0001035002")
    assert vlo.recovery_attempts==1
    assert vlo.model_version=="BATCH-36-VLO-RECOVERY-1.0"
    assert vlo.reason_codes==("NORMALIZED_CYCLICAL_RANGE","SPECIALIST_MODEL_UNCERTAINTY")
    assert vlo.hard_blockers==("CLAIMS_UNBOUNDED",)
    assert vlo.evidence_report=="docs/audit/135-batch-36-vlo-recovery-result.md"
    gpn=entries[21]
    assert (gpn.batch,gpn.ticker,gpn.cik)==(38,"GPN","0001123360")
    assert gpn.recovery_attempts==1
    assert gpn.model_version=="BATCH-38-GPN-CPAY-RECOVERY-1.0"
    assert gpn.reason_codes==("POST_COMBINATION_HISTORY_INCOMPLETE","NONFINITE_OR_NONPOSITIVE_VALUE")
    assert gpn.hard_blockers==("MODEL_UNSUPPORTED","NONFINITE_OR_NONPOSITIVE_VALUE")
    assert gpn.evidence_report=="docs/audit/140-batch-38-gpn-cpay-recovery-result.md"
    coin=entries[22]
    assert (coin.batch,coin.ticker,coin.cik)==(40,"COIN","0001679788")
    assert coin.recovery_attempts==1
    assert coin.model_version=="BATCH-40-COIN-RECOVERY-1.0"
    assert coin.reason_codes==("NEGATIVE_THROUGH_CYCLE_BEAR","UNBOUNDED_TAX_REGULATORY_CLAIMS","SPECIALIST_MODEL_REQUIRED","VALUATION_WITHHELD")
    assert coin.hard_blockers==("CLAIMS_UNBOUNDED","NONFINITE_OR_NONPOSITIVE_VALUE")
    assert coin.evidence_report=="docs/audit/146-batch-40-coin-recovery-result.md"
    iff,ip=entries[23:25]
    assert (iff.batch,iff.ticker,iff.cik)==(41,"IFF","0000051253")
    assert iff.recovery_attempts==1
    assert iff.model_version=="BATCH-41-RECOVERY-1.0"
    assert iff.reason_codes==("CONTINUING_DISCONTINUED_CASH_PERIMETER_UNRESOLVED","NEGATIVE_PARENT_EARNINGS_HISTORY")
    assert iff.hard_blockers==("MODEL_UNSUPPORTED",)
    assert iff.evidence_report=="docs/audit/148-batch-41-recovery-result.md"
    assert (ip.batch,ip.ticker,ip.cik)==(41,"IP","0000051434")
    assert ip.recovery_attempts==1
    assert ip.model_version=="BATCH-41-RECOVERY-1.0"
    assert ip.reason_codes==("POST_COMBINATION_HISTORY_INCOMPLETE","CONTINUING_DISCONTINUED_CAPEX_PERIMETER_UNRESOLVED")
    assert ip.hard_blockers==("MODEL_UNSUPPORTED","NONFINITE_OR_NONPOSITIVE_VALUE")
    assert ip.evidence_report=="docs/audit/148-batch-41-recovery-result.md"
    exe,alb=entries[25:27]
    assert (exe.batch,exe.ticker,exe.cik)==(42,"EXE","0000895126")
    assert exe.recovery_attempts==1 and exe.model_version=="BATCH-42-EXE-ALB-RECOVERY-1.0"
    assert exe.reason_codes==("POST_COMBINATION_HISTORY_INCOMPLETE","SPECIALIST_MODEL_REQUIRED","VALUATION_WITHHELD")
    assert exe.hard_blockers==("MODEL_UNSUPPORTED",)
    assert exe.evidence_report=="docs/audit/150-batch-42-exe-alb-recovery-result.md"
    assert (alb.batch,alb.ticker,alb.cik)==(42,"ALB","0000915913")
    assert alb.recovery_attempts==1 and alb.model_version=="BATCH-42-EXE-ALB-RECOVERY-1.0"
    assert alb.reason_codes==("NEGATIVE_THROUGH_CYCLE_BASE","CURRENT_OBJECT_HISTORY_INCOMPLETE","PREFERRED_CONVERSION_SCOPE_UNRESOLVED","VALUATION_WITHHELD")
    assert alb.hard_blockers==("MODEL_UNSUPPORTED","NONFINITE_OR_NONPOSITIVE_VALUE")
    assert alb.evidence_report=="docs/audit/150-batch-42-exe-alb-recovery-result.md"
    dvn,nem,lyb=entries[27:30]
    assert (dvn.batch,dvn.ticker,dvn.cik)==(43,"DVN","0001090012")
    assert dvn.recovery_attempts==1 and dvn.model_version=="BATCH-43-DVN-NEM-LYB-RECOVERY-1.0"
    assert dvn.reason_codes==("POST_COMBINATION_CASH_HISTORY_INCOMPLETE","PRO_FORMA_EARNINGS_NOT_CASH_FLOW","VALUATION_WITHHELD")
    assert dvn.hard_blockers==("MODEL_UNSUPPORTED",)
    assert dvn.evidence_report=="docs/audit/152-batch-43-recovery-result.md"
    assert (nem.batch,nem.ticker,nem.cik)==(43,"NEM","0001164727")
    assert nem.recovery_attempts==1 and nem.model_version=="BATCH-43-DVN-NEM-LYB-RECOVERY-1.0"
    assert nem.hard_blockers==("CLAIMS_UNBOUNDED","MODEL_UNSUPPORTED")
    assert nem.evidence_report=="docs/audit/152-batch-43-recovery-result.md"
    assert (lyb.batch,lyb.ticker,lyb.cik)==(43,"LYB","0001489393")
    assert lyb.recovery_attempts==1 and lyb.model_version=="BATCH-43-DVN-NEM-LYB-RECOVERY-1.0"
    assert lyb.hard_blockers==("MODEL_UNSUPPORTED",)
    assert lyb.evidence_report=="docs/audit/152-batch-43-recovery-result.md"
    bkr=entries[30]
    assert (bkr.batch,bkr.ticker,bkr.cik)==(44,"BKR","0001701605")
    assert bkr.recovery_attempts==1 and bkr.model_version=="BATCH-44-RECOVERY-RECALIBRATION-1.0"
    assert bkr.reason_codes==("POST_ACQUISITION_CASH_STATE_UNAVAILABLE","ASSUMED_CLAIMS_UNBOUNDED","PRO_FORMA_CASH_FLOW_NOT_DISCLOSED","VALUATION_WITHHELD")
    assert bkr.hard_blockers==("CLAIMS_UNBOUNDED","MODEL_UNSUPPORTED")
    assert bkr.evidence_report=="docs/audit/154-batch-44-recovery-and-range-recalibration-result.md"
    nrg,vst,ceg=entries[31:34]
    assert (nrg.batch,nrg.ticker,nrg.cik)==(47,"NRG","0001013871")
    assert (vst.batch,vst.ticker,vst.cik)==(47,"VST","0001692819")
    assert (ceg.batch,ceg.ticker,ceg.cik)==(47,"CEG","0001868275")
    assert all(row.recovery_attempts==1 and row.model_version=="BATCH-47-MERCHANT-RECOVERY-1.0" for row in (nrg,vst,ceg))
    assert all(row.hard_blockers==("MODEL_UNSUPPORTED",) for row in (nrg,vst,ceg))
    assert all(row.evidence_report=="docs/audit/159-batch-47-recovery-result.md" for row in (nrg,vst,ceg))
    eqr=entries[34]
    assert (eqr.batch,eqr.ticker,eqr.cik)==(48,"EQR","0000906107")
    assert eqr.recovery_attempts==1 and eqr.model_version=="BATCH-48-REIT-RECOVERY-1.0"
    assert eqr.reason_codes==("MAJOR_EVENT_UNBOUNDED","POST_COMBINATION_HISTORY_INCOMPLETE","VALUATION_WITHHELD")
    assert eqr.hard_blockers==("MAJOR_EVENT_UNBOUNDED","MODEL_UNSUPPORTED")
    assert eqr.evidence_report=="docs/audit/162-batch-48-recovery-result.md"
    avb=entries[35]
    assert (avb.batch,avb.ticker,avb.cik)==(49,"AVB","0000915912")
    assert avb.recovery_attempts==1 and avb.model_version=="BATCH-49-AVB-RECOVERY-1.0"
    assert avb.reason_codes==("MAJOR_EVENT_UNBOUNDED","AFFO_RECONCILIATION_UNAVAILABLE","POST_COMBINATION_HISTORY_INCOMPLETE","VALUATION_WITHHELD")
    assert avb.hard_blockers==("MAJOR_EVENT_UNBOUNDED","MODEL_UNSUPPORTED")
    assert avb.evidence_report=="docs/audit/165-batch-49-avb-recovery-result.md"


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
