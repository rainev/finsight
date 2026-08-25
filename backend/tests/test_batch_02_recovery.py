from dataclasses import asdict
import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.batch_02_recovery import (
    PUBLIC_METHOD_REFERENCES,
    RECOVERY_DECISIONS,
    RECOVERY_TICKERS,
    conditional_wbd_merger_consideration,
)
from app.us_valuation.batch_02 import BATCH_02_MANIFEST

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_batch_02_recovery import _recovery_source_identity


def test_recovery_attempt_is_exactly_six_source_blocked_issuers() -> None:
    assert tuple(decision.ticker for decision in RECOVERY_DECISIONS) == RECOVERY_TICKERS
    assert len(RECOVERY_DECISIONS) == 6
    assert all(decision.final_outcome == "withheld" for decision in RECOVERY_DECISIONS)
    assert all(decision.hard_blockers for decision in RECOVERY_DECISIONS)
    assert all(decision.missing_evidence for decision in RECOVERY_DECISIONS)
    assert all(decision.next_eligible_trigger for decision in RECOVERY_DECISIONS)
    assert all(reference["proprietary_formula_used"] is False for reference in PUBLIC_METHOD_REFERENCES)


def test_wbd_contractual_quote_is_labeled_non_intrinsic_and_not_probability_weighted() -> None:
    wbd = next(decision for decision in RECOVERY_DECISIONS if decision.ticker == "WBD")
    diagnostic = wbd.conditional_event_diagnostic
    assert diagnostic is not None
    assert diagnostic["published_as_intrinsic_value"] is False
    assert diagnostic["probability_weighted"] is False
    assert conditional_wbd_merger_consideration("2026-09-30") == 31.0
    assert conditional_wbd_merger_consideration("2026-10-01") == pytest.approx(
        31.00277778
    )
    assert conditional_wbd_merger_consideration("2026-12-29") == pytest.approx(31.25)


def test_recovery_decisions_are_serializable_without_private_formula_claims() -> None:
    payload = [asdict(decision) for decision in RECOVERY_DECISIONS]
    assert len(payload) == 6
    assert all(item["model_version"] for item in payload)
    assert all("proprietary" not in item["recovery_model"] for item in payload)


def test_all_six_recovery_periods_come_from_matching_submissions_rows(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "sources"
    structural_root = tmp_path / "structural"
    issuers = [
        issuer for issuer in BATCH_02_MANIFEST if issuer.ticker in RECOVERY_TICKERS
    ]
    for issuer in issuers:
        accession = f"{issuer.cik}-26-000001"
        packet = source_root / issuer.ticker
        packet.mkdir(parents=True)
        manifest = {
            "valuation_date": "2026-08-14",
            "issuer": {
                "ticker": issuer.ticker,
                "cik": issuer.cik,
                "issuer_name": issuer.issuer_name,
            },
            "eligible_filings": [
                {
                    "accession": accession,
                    "filed": "2026-08-07",
                    "form": "10-Q",
                    "primary_document": "quarter.htm",
                }
            ],
            "future_filings": [
                {
                    "accession": f"{issuer.cik}-26-000002",
                    "filed": "2026-08-15",
                    "form": "10-Q",
                    "primary_document": "future.htm",
                }
            ],
        }
        submissions = {
            "cik": issuer.cik,
            "filings": {
                "recent": {
                    "accessionNumber": [accession],
                    "filingDate": ["2026-08-07"],
                    "reportDate": ["2026-06-30"],
                    "form": ["10-Q"],
                    "primaryDocument": ["quarter.htm"],
                }
            },
        }
        (packet / "source-manifest.json").write_text(json.dumps(manifest))
        (packet / "submissions.json").write_text(json.dumps(submissions))
        structural = structural_root / issuer.ticker
        structural.mkdir(parents=True)
        (structural / "structural-filing.json").write_text(
            json.dumps(
                {
                    "source_accession": accession,
                    "period_end": "2026-12-30",
                    "facts": [],
                }
            )
        )

    for issuer in issuers:
        latest, report_date, structural = _recovery_source_identity(
            source_root, structural_root, issuer
        )
        assert latest["filed"] == "2026-08-07"
        assert report_date == "2026-06-30"
        assert structural["period_end"] == "2026-12-30"
