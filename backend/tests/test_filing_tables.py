"""FOD2 contracts for deterministic SEC filing-table extraction."""

from __future__ import annotations

from app.us_valuation.filing_tables import (
    TableExtractionResult,
    extract_numeric_table_evidence,
)


def _metadata() -> dict[str, str]:
    return {
        "ticker": "TEST",
        "cik": "0000123456",
        "source_accession": "0000123456-26-000001",
        "source_url": "https://www.sec.gov/Archives/edgar/data/123456/filing.htm",
        "filed_date": "2026-08-10",
        "period_end": "2026-06-30",
        "form": "10-Q",
        "unit": "USD millions",
        "entity_identifier": "0000123456",
        "consolidation_scope": "consolidated_parent",
        "package_sha256": "a" * 64,
    }


def _requests() -> list[dict[str, str]]:
    return [
        {
            "required_field": "marketable_securities_current",
            "statement_role": "balance_sheet",
            "period_role": "balance_sheet_snapshot",
        }
    ]


def test_extracts_current_dated_column_and_preserves_full_table_locator() -> None:
    html = """
    <table>
      <caption>Consolidated Marketable Securities</caption>
      <tr><th>June 30, 2026</th><th>June 30, 2025</th></tr>
      <tr><td>Current marketable securities</td><td>$1,234</td><td>$987</td></tr>
      <tr><td>Total marketable securities</td><td>$1,456</td><td>$1,111</td></tr>
    </table>
    """

    result = extract_numeric_table_evidence(html, _requests(), _metadata())

    assert isinstance(result, TableExtractionResult)
    assert result.complete_search is True
    assert len(result.evidence) == 1
    evidence = result.evidence[0]
    assert evidence.status == "reported"
    assert evidence.value == 1234.0
    assert evidence.table_title == "Consolidated Marketable Securities"
    assert evidence.row_label == "Current marketable securities"
    assert evidence.column_label == "June 30, 2026"
    assert evidence.period_end == "2026-06-30"
    assert evidence.unit == "USD millions"
    assert evidence.source_accession == _metadata()["source_accession"]
    assert evidence.filed_date == "2026-08-10"
    assert evidence.entity_identifier == "0000123456"
    assert evidence.consolidation_scope == "consolidated_parent"
    assert evidence.package_sha256 == "a" * 64
    assert "Current marketable securities" in evidence.excerpt


def test_table_without_consolidated_title_does_not_claim_parent_scope() -> None:
    html = """
    <table><caption>Marketable Securities</caption>
      <tr><th>June 30, 2026</th></tr>
      <tr><td>Current marketable securities</td><td>$1,234</td></tr>
    </table>
    """
    evidence = extract_numeric_table_evidence(html, _requests(), _metadata()).evidence[0]

    assert evidence.status == "reported"
    assert evidence.consolidation_scope == "unknown"


def test_rejects_table_evidence_without_complete_cutoff_and_package_lineage() -> None:
    metadata = _metadata()
    metadata.pop("filed_date")
    html = """
    <table><caption>Marketable Securities</caption>
      <tr><th>June 30, 2026</th></tr>
      <tr><td>Current marketable securities</td><td>$1,234</td></tr>
    </table>
    """

    try:
        extract_numeric_table_evidence(html, _requests(), metadata)
    except ValueError as error:
        assert "complete filing" in str(error)
    else:
        raise AssertionError("missing filed date must fail closed")


def test_rejects_duplicate_or_ambiguous_numeric_tables_instead_of_choosing_one() -> None:
    html = """
    <table><caption>Marketable Securities</caption>
      <tr><th>June 30, 2026</th></tr>
      <tr><td>Current marketable securities</td><td>$1,234</td></tr>
    </table>
    <table><caption>Marketable Securities</caption>
      <tr><th>June 30, 2026</th></tr>
      <tr><td>Current marketable securities</td><td>$2,345</td></tr>
    </table>
    """

    result = extract_numeric_table_evidence(html, _requests(), _metadata())

    assert result.complete_search is True
    evidence = result.evidence[0]
    assert evidence.status == "unresolved"
    assert evidence.value is None
    assert "AMBIGUOUS" in evidence.reason_codes
    assert len(evidence.candidate_locators) == 2


def test_not_disclosed_requires_a_complete_search_proof() -> None:
    html = "<table><caption>Unrelated Table</caption><tr><td>Revenue</td><td>$12</td></tr></table>"

    result = extract_numeric_table_evidence(html, _requests(), _metadata())

    evidence = result.evidence[0]
    assert result.complete_search is True
    assert evidence.status == "not_disclosed"
    assert evidence.value is None
    assert evidence.searched_table_count == 1
    assert evidence.search_scope_hash


def test_unknown_scale_and_incomplete_scope_remain_unresolved() -> None:
    html = """
    <table><caption>Marketable Securities</caption>
      <tr><th>June 30, 2026</th></tr>
      <tr><td>Current marketable securities</td><td>$1,234</td></tr>
    </table>
    """
    metadata = {key: value for key, value in _metadata().items() if key != "unit"}
    metadata["search_scope_complete"] = False
    metadata["search_scope_kind"] = "primary_document_only"

    result = extract_numeric_table_evidence(html, _requests(), metadata)

    assert result.complete_search is False
    assert result.scope_kind == "primary_document_only"
    assert result.evidence[0].status == "unresolved"
    assert result.evidence[0].reason_codes == ("TABLE_UNIT_SCALE_UNRESOLVED",)


def test_detects_millions_scale_and_rejects_maturity_schedule_role() -> None:
    statement = """
    <div>(dollars in millions)</div>
    <table><caption>Balance Sheet</caption>
      <tr><th>June 30, 2026</th></tr>
      <tr><td>Current marketable securities</td><td>$1,234</td></tr>
    </table>
    """
    metadata = {key: value for key, value in _metadata().items() if key != "unit"}
    evidence = extract_numeric_table_evidence(statement, _requests(), metadata).evidence[0]
    assert evidence.status == "reported"
    assert evidence.unit == "USD millions"
    assert evidence.scale == 1_000_000.0

    maturity = """
    <div>Debt maturities (dollars in millions)</div>
    <table><caption>Contractual maturities</caption>
      <tr><th>June 30, 2026</th></tr>
      <tr><td>Long-term debt</td><td>$1,234</td></tr>
    </table>
    """
    request = [{"required_field": "noncurrent_debt", "statement_role": "balance_sheet", "period_role": "balance_sheet_snapshot"}]
    rejected = extract_numeric_table_evidence(maturity, request, metadata).evidence[0]
    assert rejected.status == "not_disclosed"
    assert rejected.value is None
