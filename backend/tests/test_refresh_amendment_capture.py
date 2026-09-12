from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.us_valuation import refresh_source_ingestion as ingestion


def _records() -> dict:
    regular = {
        "accessionNumber": "0000000000-26-000001",
        "form": "10-K",
        "filingDate": "2026-08-01",
        "reportDate": "2026-06-30",
        "primaryDocument": "annual.htm",
    }
    amendment = {
        "accessionNumber": "0000000000-26-000002",
        "form": "10-K/A",
        "filingDate": "2026-08-10",
        "reportDate": "2026-06-30",
        "primaryDocument": "amendment.htm",
    }
    return {
        "cik": "0000000000",
        "filings": {"recent": {
            "accessionNumber": [regular["accessionNumber"], amendment["accessionNumber"]],
            "form": [regular["form"], amendment["form"]],
            "filingDate": [regular["filingDate"], amendment["filingDate"]],
            "reportDate": [regular["reportDate"], amendment["reportDate"]],
            "primaryDocument": [regular["primaryDocument"], amendment["primaryDocument"]],
            "items": ["", ""],
        }},
    }


def _capture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, paths: dict[str, Path] | None) -> dict:
    submissions = _records()
    monkeypatch.setattr(
        ingestion,
        "_cached_packet",
        lambda *_args, **_kwargs: (submissions, {"cik": "0000000000"}, {}),
    )
    monkeypatch.setattr(
        ingestion,
        "_cache_structural_payload",
        lambda **_kwargs: ({"source_accession": _kwargs["accession"], "form": _kwargs["filing"]["form"], "report_date": _kwargs["filing"]["report_date"], "facts": []}, "f" * 64, False),
    )
    return ingestion.capture_company_source(
        ticker="TEST",
        cik="0000000000",
        cutoff="2026-08-14",
        offline_packet_dir=tmp_path / "offline",
        structural_paths=paths,
        require_structural=False,
        parsed_cache_dir=tmp_path / "parsed",
    )


def test_same_period_financial_amendment_structural_capture_is_indexed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    regular = tmp_path / "regular.json"
    amendment = tmp_path / "amendment.json"
    regular.write_text("{}")
    amendment.write_text("{}")
    result = _capture(
        monkeypatch,
        tmp_path,
        {
            "0000000000-26-000001": regular,
            "0000000000-26-000002": amendment,
        },
    )
    assert result["controlling_filing"]["accessionNumber"] == "0000000000-26-000001"
    assert result["amendment_filings"][0]["amendment_kind"] == "financial_amendment"
    assert result["amendment_structural_receipts"][0]["accession"] == "0000000000-26-000002"
    assert result["structural_packets"]["0000000000-26-000002"]["source_accession"] == "0000000000-26-000002"


def test_missing_financial_amendment_body_is_explicit_acquisition_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    regular = tmp_path / "regular.json"
    regular.write_text("{}")
    result = _capture(monkeypatch, tmp_path, {"0000000000-26-000001": regular})
    failure = result["amendment_acquisition_failures"][0]
    assert failure["accession"] == "0000000000-26-000002"
    assert failure["status"] == "acquisition_failed"
    assert result["amendment_filings"][0]["review_status"] == "financial_amendment_requires_structural_proof"


def test_regular_fallback_retains_amendment_metadata_and_review_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result = _capture(monkeypatch, tmp_path, None)
    amendment = result["amendment_filings"][0]
    assert result["controlling_filing"]["form"] == "10-K"
    assert amendment["form"] == "10-K/A"
    assert amendment["review_status"] == "financial_amendment_requires_structural_proof"
    assert result["amendment_acquisition_failures"]
    assert json.dumps(result["amendment_filings"])
