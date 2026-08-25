"""Hermetic contracts for manifest-driven official SEC filing ingestion."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.us_valuation.official_filing_ingestion import (
    ingest_manifest,
    material_gap_requires_filing,
    select_filing_pair,
)


def _filings() -> list[dict[str, str]]:
    return [
        {
            "accession": "0000123456-26-000010",
            "form": "10-Q",
            "filed": "2026-08-10",
            "report_date": "2026-06-30",
            "primary_document": "q2.htm",
        },
        {
            "accession": "0000123456-26-000005",
            "form": "10-K",
            "filed": "2026-02-20",
            "report_date": "2025-12-31",
            "primary_document": "annual.htm",
        },
        {
            "accession": "0000123456-26-000011",
            "form": "10-Q",
            "filed": "2026-08-16",
            "report_date": "2026-06-30",
            "primary_document": "future.htm",
        },
    ]


def _manifest() -> dict[str, object]:
    return {
        "schema_version": "FINSIGHT-OFFICIAL-FILING-INGESTION-1",
        "valuation_date": "2026-08-14",
        "issuers": [
            {
                "ticker": "TEST",
                "cik": "0000123456",
                "companyfacts": {"accession": "0000123456-26-000005"},
                "filings": _filings(),
                "material_requests": [
                    {
                        "required_field": "noncurrent_debt",
                        "model": "fcff_dcf",
                        "period_role": "balance_sheet_snapshot",
                        "materiality": "material",
                    }
                ],
            }
        ],
    }


def test_selects_controlling_filing_and_latest_eligible_annual_before_cutoff() -> None:
    pair = select_filing_pair(_filings(), valuation_date="2026-08-14")

    assert pair.controlling["accession"] == "0000123456-26-000010"
    assert pair.latest_annual["accession"] == "0000123456-26-000005"
    assert pair.controlling["filed"] <= "2026-08-14"
    assert pair.latest_annual["form"] == "10-K"


def test_same_day_amendment_uses_report_date_then_accession_deterministically() -> None:
    filings = _filings() + [
        {
            "accession": "0000123456-26-000009",
            "form": "10-Q/A",
            "filed": "2026-08-10",
            "report_date": "2026-06-29",
            "primary_document": "q2-amendment.htm",
        }
    ]

    assert select_filing_pair(filings, valuation_date="2026-08-14").controlling[
        "accession"
    ] == "0000123456-26-000010"


def test_filing_selection_rejects_malformed_dates_before_cutoff_comparison() -> None:
    filings = _filings()
    filings[0] = {**filings[0], "filed": "2026-8-1"}
    with pytest.raises(ValueError, match="ISO date"):
        select_filing_pair(filings, valuation_date="2026-08-14")


def test_material_gap_trigger_covers_missing_controlling_accession_and_material_field() -> None:
    assert material_gap_requires_filing(
        companyfacts={"accession": "0000123456-26-000005", "fields": {}},
        controlling_accession="0000123456-26-000010",
        material_fields=("noncurrent_debt",),
    ) is True
    assert material_gap_requires_filing(
        companyfacts={
            "accession": "0000123456-26-000010",
            "fields": {"noncurrent_debt": {"value": 125.0}},
        },
        controlling_accession="0000123456-26-000010",
        material_fields=("noncurrent_debt",),
    ) is False


def test_ingestion_uses_arbitrary_manifest_identity_and_parses_each_accession_once(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str, str]] = []

    def capture(*, cik: str, accession: str, primary_document: str, output_dir: Path, **_: object) -> Path:
        calls.append((cik, accession, primary_document))
        entrypoint = output_dir / accession / primary_document
        entrypoint.parent.mkdir(parents=True, exist_ok=True)
        entrypoint.write_text("fixture", encoding="utf-8")
        return entrypoint

    def parse(entrypoint: Path, *, accession: str, **_: object) -> dict[str, object]:
        calls.append(("parse", accession, entrypoint.name))
        return {"accession": accession, "facts": [{"tag": "test:Debt", "value": 125.0}]}

    result_a = ingest_manifest(
        _manifest(),
        output_dir=tmp_path / "a",
        package_capture=capture,
        parse=parse,
        protected_serving_roots=(),
    )
    result_b = ingest_manifest(
        _manifest(),
        output_dir=tmp_path / "a",
        package_capture=capture,
        parse=parse,
        protected_serving_roots=(),
    )

    issuer_a = result_a["issuers"][0]
    assert issuer_a["ticker"] == "TEST"
    assert issuer_a["cik"] == "0000123456"
    assert [item["accession"] for item in issuer_a["packages"]] == [
        "0000123456-26-000005",
        "0000123456-26-000010",
    ]
    assert result_a == result_b
    assert calls.count(("parse", "0000123456-26-000005", "annual.htm")) == 1
    assert calls.count(("parse", "0000123456-26-000010", "q2.htm")) == 1


def test_ingestion_rejects_output_under_a_protected_serving_root(tmp_path: Path) -> None:
    serving_root = tmp_path / "backend" / "app" / "data" / "us_valuations"
    serving_root.mkdir(parents=True)

    with pytest.raises(ValueError, match="protected|serving"):
        ingest_manifest(
            _manifest(),
            output_dir=serving_root / "official-evidence",
            package_capture=lambda **_: pytest.fail("must fail before capture"),
            parse=lambda **_: pytest.fail("must fail before parse"),
            protected_serving_roots=(serving_root,),
        )


def test_ingestion_fails_closed_on_an_active_or_stale_writer_lock(tmp_path: Path) -> None:
    output = tmp_path / "official-evidence"
    output.mkdir()
    (output / ".official-ingestion.lock").mkdir()

    with pytest.raises(RuntimeError, match="writer lock"):
        ingest_manifest(
            _manifest(),
            output_dir=output,
            package_capture=lambda **_: pytest.fail("must not capture under another writer"),
            parse=lambda **_: pytest.fail("must not parse under another writer"),
            protected_serving_roots=(),
        )


def test_annual_failure_does_not_mask_a_successful_controlling_package(
    tmp_path: Path,
) -> None:
    def capture(*, accession: str, primary_document: str, output_dir: Path, **_: object) -> Path:
        if primary_document == "annual.htm":
            raise RuntimeError("annual unavailable")
        entrypoint = output_dir / accession / primary_document
        entrypoint.parent.mkdir(parents=True, exist_ok=True)
        entrypoint.write_text("fixture", encoding="utf-8")
        return entrypoint

    result = ingest_manifest(
        _manifest(),
        output_dir=tmp_path / "mixed",
        package_capture=capture,
        parse=lambda _entrypoint, *, accession, **_: {
            "accession": accession,
            "facts": [{"tag": "test:Debt", "value": 125.0}],
        },
        protected_serving_roots=(),
    )

    issuer = result["issuers"][0]
    assert result["request_count"] == result["decision_count"] == 1
    assert issuer["decisions"][0]["package_failure"] is None
    assert issuer["decisions"][0]["completeness_proof"] == [
        "companyfacts_checked",
        "controlling_filing_parsed",
        "latest_annual_package_failed",
    ]
    assert issuer["package_failures"][0]["accession"] == "0000123456-26-000005"


def test_cached_parse_must_match_the_selected_package_generation(tmp_path: Path) -> None:
    output = tmp_path / "tampered"

    def capture(*, accession: str, primary_document: str, output_dir: Path, **_: object) -> Path:
        entrypoint = output_dir / accession / primary_document
        entrypoint.parent.mkdir(parents=True, exist_ok=True)
        entrypoint.write_text("fixture", encoding="utf-8")
        return entrypoint

    ingest_manifest(
        _manifest(),
        output_dir=output,
        package_capture=capture,
        parse=lambda _entrypoint, *, accession, **_: {
            "accession": accession,
            "facts": [{"tag": "test:Debt", "value": 125.0}],
        },
        protected_serving_roots=(),
    )
    (output / "official-filing-ingestion.json").unlink()
    parsed_path = output / "parsed/TEST/0000123456-26-000010.json"
    cached = __import__("json").loads(parsed_path.read_text())
    cached["package"]["package_generation"] = "tampered"
    parsed_path.write_text(__import__("json").dumps(cached), encoding="utf-8")

    result = ingest_manifest(
        _manifest(),
        output_dir=output,
        package_capture=capture,
        parse=lambda *_args, **_kwargs: pytest.fail("tampered cache must not parse or promote"),
        protected_serving_roots=(),
    )
    controlling = result["issuers"][0]["decisions"][0]
    assert controlling["status"] == "unresolved"
    assert controlling["package_failure"]["code"] == "OFFICIAL_PACKAGE_FAILURE"
