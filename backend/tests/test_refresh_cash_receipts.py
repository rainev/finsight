"""Focused source and timing tests for the CF/Orica cash receipt boundary."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_cash_receipts import (
    CashReceiptReviewRequired,
    canonical_structural_sha256,
    extract_cash_receipt_evidence,
    sum_cash_receipts,
)


ROOT = Path(__file__).parents[2]
HTML_PATH = ROOT / "output/batch-43-structural-cache-20260907/filings/CF/CIK0001324404-000132440426000019/8f6d751e84ee94c8bd02391a88c254b8e48499a20370dd721eadc0a076496034/cf-20260630.htm"
STRUCTURAL_PATH = ROOT / "output/batch-43-structural-sources-20260907/CF/structural-filing.json"
ACCESSION = "0001324404-26-000019"
CIK = "0001324404"
FILING_DATE = "2026-08-06"


def _evidence():
    html = HTML_PATH.read_bytes()
    structural = json.loads(STRUCTURAL_PATH.read_text())
    return extract_cash_receipt_evidence(
        html,
        expected_sha256=hashlib.sha256(html).hexdigest(),
        structural_packet=structural,
        expected_structural_sha256=canonical_structural_sha256(structural),
        cik=CIK,
        accession=ACCESSION,
        filing_date=FILING_DATE,
        cutoff="2026-08-14",
    )


def test_actual_filing_proves_cash_amount_date_and_distinct_recognition_period():
    evidence = _evidence()
    event = evidence.event
    assert event.amount == 170_000_000.0
    assert event.cash_received_date == "2026-04-30"
    assert (event.recognized_period_start, event.recognized_period_end) == ("2026-03-01", "2026-03-31")
    assert event.standard_gain_qname == "us-gaap:GainLossRelatedToLitigationSettlement"
    assert event.event_gain_qname == "us-gaap:LitigationSettlementGain"
    assert event.ocf_narrative_amount == event.amount
    assert event.tax_adjustment_supported is False
    json.dumps(evidence.as_dict(), allow_nan=False)


def test_cash_windows_use_receipt_date_not_march_gain_recognition_date():
    evidence = _evidence()
    q1 = sum_cash_receipts([evidence], window_start="2026-01-01", window_end="2026-03-31", cutoff="2026-08-14")
    q2 = sum_cash_receipts([evidence], window_start="2026-04-01", window_end="2026-06-30", cutoff="2026-08-14")
    rolling_ttm = sum_cash_receipts([evidence], window_start="2025-07-01", window_end="2026-06-30", cutoff="2026-08-14")
    assert q1["amount"] == 0.0
    assert q2["amount"] == 170_000_000.0
    assert rolling_ttm["amount"] == 170_000_000.0


def test_duplicate_corrobating_event_is_counted_once():
    evidence = _evidence()
    result = sum_cash_receipts([evidence, evidence, evidence.event], window_start="2026-04-01", window_end="2026-06-30", cutoff="2026-08-14")
    assert result["amount"] == 170_000_000.0
    assert len(result["included_event_ids"]) == 1


def test_wrong_primary_hash_is_rejected():
    html = HTML_PATH.read_bytes()
    structural = json.loads(STRUCTURAL_PATH.read_text())
    with pytest.raises(CashReceiptReviewRequired, match="SHA-256 mismatch"):
        extract_cash_receipt_evidence(
            html,
            expected_sha256="0" * 64,
            structural_packet=structural,
            expected_structural_sha256=canonical_structural_sha256(structural),
            cik=CIK,
            accession=ACCESSION,
            filing_date=FILING_DATE,
            cutoff="2026-08-14",
        )


def test_wrong_canonical_structural_hash_is_rejected():
    html = HTML_PATH.read_bytes()
    structural = json.loads(STRUCTURAL_PATH.read_text())
    with pytest.raises(CashReceiptReviewRequired, match="canonical structural SHA-256 mismatch"):
        extract_cash_receipt_evidence(
            html,
            expected_sha256=hashlib.sha256(html).hexdigest(),
            structural_packet=structural,
            expected_structural_sha256="0" * 64,
            cik=CIK,
            accession=ACCESSION,
            filing_date=FILING_DATE,
            cutoff="2026-08-14",
        )


def test_governed_cf_identity_and_cutoff_are_required():
    html = HTML_PATH.read_bytes()
    structural = json.loads(STRUCTURAL_PATH.read_text())
    kwargs = {
        "expected_sha256": hashlib.sha256(html).hexdigest(),
        "structural_packet": structural,
        "expected_structural_sha256": canonical_structural_sha256(structural),
        "cik": CIK,
        "accession": ACCESSION,
        "filing_date": FILING_DATE,
    }
    with pytest.raises(CashReceiptReviewRequired, match="governed only for ticker CF"):
        extract_cash_receipt_evidence(html, ticker="XOM", cutoff="2026-08-14", **kwargs)
    with pytest.raises(CashReceiptReviewRequired, match="after cutoff"):
        extract_cash_receipt_evidence(html, ticker="CF", cutoff="2026-08-05", **kwargs)


def test_structural_identity_mismatch_is_rejected():
    html = HTML_PATH.read_bytes()
    structural = json.loads(STRUCTURAL_PATH.read_text())
    structural["source_accession"] = "0001324404-26-999999"
    with pytest.raises(CashReceiptReviewRequired, match="structural accession mismatch"):
        extract_cash_receipt_evidence(
            html,
            expected_sha256=hashlib.sha256(html).hexdigest(),
            structural_packet=structural,
            expected_structural_sha256=canonical_structural_sha256(structural),
            cik=CIK,
            accession=ACCESSION,
            filing_date=FILING_DATE,
            cutoff="2026-08-14",
        )


def test_non_official_us_gaap_namespace_is_rejected():
    html = HTML_PATH.read_bytes()
    structural = json.loads(STRUCTURAL_PATH.read_text())
    for row in structural["facts"]:
        if row.get("qname") == "us-gaap:GainLossRelatedToLitigationSettlement":
            row["namespace"] = "https://example.invalid/us-gaap/2026"
    with pytest.raises(CashReceiptReviewRequired, match="standard litigation gain source is missing"):
        extract_cash_receipt_evidence(
            html,
            expected_sha256=hashlib.sha256(html).hexdigest(),
            structural_packet=structural,
            expected_structural_sha256=canonical_structural_sha256(structural),
            cik=CIK,
            accession=ACCESSION,
            filing_date=FILING_DATE,
            cutoff="2026-08-14",
        )


def test_conflicting_structural_gain_amount_is_rejected():
    html = HTML_PATH.read_bytes()
    structural = json.loads(STRUCTURAL_PATH.read_text())
    original = next(
        row
        for row in structural["facts"]
        if row.get("qname") == "us-gaap:GainLossRelatedToLitigationSettlement"
        and row.get("period_start") == "2026-01-01"
        and row.get("period_end") == "2026-06-30"
        and row.get("value") == 170_000_000
    )
    conflict = deepcopy(original)
    conflict["value"] = 175_000_000
    conflict["context_id"] = "synthetic-conflicting-context"
    structural["facts"].append(conflict)
    with pytest.raises(CashReceiptReviewRequired, match="standard litigation gain facts conflict"):
        extract_cash_receipt_evidence(
            html,
            expected_sha256=hashlib.sha256(html).hexdigest(),
            structural_packet=structural,
            expected_structural_sha256=canonical_structural_sha256(structural),
            cik=CIK,
            accession=ACCESSION,
            filing_date=FILING_DATE,
            cutoff="2026-08-14",
        )


def test_conflicting_duplicate_event_values_are_rejected():
    evidence = _evidence()
    conflicting = evidence.event.as_dict()
    conflicting["amount"] = 175_000_000.0
    conflicting['ocf_narrative_amount'] = 175_000_000.0
    with pytest.raises(CashReceiptReviewRequired, match="conflicting receipt evidence"):
        sum_cash_receipts([evidence, conflicting], window_start="2026-04-01", window_end="2026-06-30", cutoff="2026-08-14")


def test_conflicting_duplicate_event_dates_are_rejected():
    evidence = _evidence()
    conflicting = evidence.event.as_dict()
    conflicting["cash_received_date"] = "2026-05-01"
    with pytest.raises(CashReceiptReviewRequired, match="conflicting receipt evidence"):
        sum_cash_receipts([evidence, conflicting], window_start="2026-04-01", window_end="2026-06-30", cutoff="2026-08-14")


def test_serialized_event_validates_hash_identity_amount_and_date_ordering():
    evidence = _evidence()
    raw = evidence.event.as_dict()
    raw["source_sha256"] = "not-a-hash"
    with pytest.raises(CashReceiptReviewRequired, match="serialized cash receipt hash is invalid"):
        sum_cash_receipts([raw], window_start="2026-04-01", window_end="2026-06-30", cutoff="2026-08-14")

    raw = evidence.event.as_dict()
    raw["ocf_narrative_amount"] = raw["amount"] + 1.0
    with pytest.raises(CashReceiptReviewRequired, match="does not match OCF"):
        sum_cash_receipts([raw], window_start="2026-04-01", window_end="2026-06-30", cutoff="2026-08-14")

    raw = evidence.event.as_dict()
    raw["cash_received_date"] = "2026-08-07"
    with pytest.raises(CashReceiptReviewRequired, match="date ordering"):
        sum_cash_receipts([raw], window_start="2026-04-01", window_end="2026-12-31", cutoff="2026-08-14")

    raw = evidence.event.as_dict()
    raw["recognized_period_start"] = "2026-04-01"
    raw["recognized_period_end"] = "2026-03-31"
    with pytest.raises(CashReceiptReviewRequired, match="recognition period is invalid"):
        sum_cash_receipts([raw], window_start="2026-04-01", window_end="2026-06-30", cutoff="2026-08-14")
