from __future__ import annotations

import pytest

from app.us_valuation.refresh_event_review import (
    EventReviewError,
    EventReviewIncomplete,
    review_event_records,
)


ACCESSION = "0000000000-26-000001"
PRIMARY = "issuer-20260901.htm"
COMPLETE = "0000000000-26-000001.txt"
PRIMARY_HASH = "a" * 64
COMPLETE_HASH = "b" * 64


def _record(*, items="5.02") -> dict:
    return {
        "accessionNumber": ACCESSION,
        "filingDate": "2026-09-01",
        "reportDate": "2026-09-01",
        "form": "8-K",
        "items": items,
        "primaryDocument": PRIMARY,
    }


def _captured(*, attachments=None, relationships_status="review_exception") -> dict:
    return {
        "accession": ACCESSION,
        "filed_date": "2026-09-01",
        "report_date": "2026-09-01",
        "form": "8-K",
        "items": ["5.02"],
        "primary_document": PRIMARY,
        "attachments": [] if attachments is None else attachments,
        "relationships_status": relationships_status,
        "document_sources": [
            {"name": PRIMARY, "role": "primary_filing", "sha256": PRIMARY_HASH},
            {"name": COMPLETE, "role": "complete_submission", "sha256": COMPLETE_HASH},
        ],
    }


def _policy(*, primary_only_allowed=True, cutoff="2026-09-19") -> dict:
    return {
        "routine_8k_items": ["2.02", "9.01"],
        "source_requirements": {"event_exhibits": True},
        "reviewed_events": {
            ACCESSION: {
                "form": "8-K",
                "items": ["5.02"],
                "filed": "2026-09-01",
                "cutoff": cutoff,
                "primary_document": PRIMARY,
                "primary_sha256": PRIMARY_HASH,
                "complete_submission_document": COMPLETE,
                "complete_submission_sha256": COMPLETE_HASH,
                "primary_only_allowed": primary_only_allowed,
                "treatment": "Narrative-only forward watch; no current-period financial input update.",
                "limitations": ["No quantified current-period financial effect disclosed."],
            }
        },
    }


def test_exact_reviewed_primary_only_event_returns_hash_bound_ledger():
    rows = review_event_records(
        [_record()],
        [_captured()],
        _policy(),
        prior_cutoff="2026-08-14",
        cutoff="2026-09-19",
        require_exhibits=True,
    )
    assert rows == [{
        "accession": ACCESSION,
        "form": "8-K",
        "items": ["5.02"],
        "filed": "2026-09-01",
        "cutoff": "2026-09-19",
        "primary_document": PRIMARY,
        "primary_sha256": PRIMARY_HASH,
        "complete_submission_document": COMPLETE,
        "complete_submission_sha256": COMPLETE_HASH,
        "primary_only_allowed": True,
        "treatment": "Narrative-only forward watch; no current-period financial input update.",
        "limitations": ["No quantified current-period financial effect disclosed."],
    }]


def test_earnings_event_is_superseded_only_by_later_controlling_regular_filing():
    record=_record(items='2.02,7.01,9.01')
    captured=_captured(attachments=[{'name':'earnings.htm','sha256':'c'*64}],relationships_status='exhibit_relationships_captured')
    captured['items']=['2.02','7.01','9.01']
    policy={'routine_8k_items':['2.02','9.01'],'supersede_financial_events_by_controlling_filing':True}
    rows=review_event_records([record],[captured],policy,prior_cutoff='2026-08-14',cutoff='2026-09-19',
        require_exhibits=True,controlling_filing={'filingDate':'2026-09-02','reportDate':'2026-09-01'})
    assert rows[0]['treatment'].startswith('Historical earnings inputs superseded')


def test_future_or_non_earnings_event_is_not_auto_superseded():
    policy={'routine_8k_items':['2.02','9.01'],'supersede_financial_events_by_controlling_filing':True}
    with pytest.raises(EventReviewError,match='approved event rule'):
        review_event_records([_record(items='5.02')],[_captured()],policy,
            prior_cutoff='2026-08-14',cutoff='2026-09-19',require_exhibits=True,
            controlling_filing={'filingDate':'2026-09-02','reportDate':'2026-09-01'})


@pytest.mark.parametrize("field", ["primary_sha256", "complete_submission_sha256", "primary_document"])
def test_review_rejects_mismatched_source_identity(field):
    policy = _policy()
    policy["reviewed_events"][ACCESSION][field] = "c" * 64 if "sha256" in field else "different.htm"
    with pytest.raises(EventReviewError, match="does not match"):
        review_event_records(
            [_record()], [_captured()], policy,
            prior_cutoff="2026-08-14", cutoff="2026-09-19", require_exhibits=True,
        )


def test_review_rejects_absent_exhibits_without_explicit_primary_only_rule():
    with pytest.raises(EventReviewIncomplete, match="missing verified exhibit"):
        review_event_records(
            [_record()], [_captured()], _policy(primary_only_allowed=False),
            prior_cutoff="2026-08-14", cutoff="2026-09-19", require_exhibits=True,
        )


def test_review_rejects_nonempty_attachments_under_primary_only_rule():
    with pytest.raises(EventReviewError, match="no attachments"):
        review_event_records(
            [_record()], [_captured(attachments=[{"name": "exhibit.htm"}])], _policy(),
            prior_cutoff="2026-08-14", cutoff="2026-09-19", require_exhibits=True,
        )


def test_review_rejects_unreviewed_nonroutine_event_and_preserves_routine_gate():
    policy = _policy()
    policy["reviewed_events"] = {}
    with pytest.raises(EventReviewError, match="approved event rule"):
        review_event_records(
            [_record()], [_captured()], policy,
            prior_cutoff="2026-08-14", cutoff="2026-09-19", require_exhibits=True,
        )

    routine_record = _record(items="2.02")
    routine_captured = _captured()
    routine_captured["items"] = ["2.02"]
    assert review_event_records(
        [routine_record], [routine_captured], policy,
        prior_cutoff="2026-08-14", cutoff="2026-09-19", require_exhibits=False,
    ) == []


def test_review_cutoff_is_exact_and_rules_cannot_be_reused_at_later_cutoff():
    with pytest.raises(EventReviewError, match="cutoff does not match"):
        review_event_records(
            [_record()], [_captured()], _policy(cutoff="2026-09-18"),
            prior_cutoff="2026-08-14", cutoff="2026-09-19", require_exhibits=True,
        )
