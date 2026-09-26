from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.us_valuation.filing_evidence import (
    EVIDENCE_SCHEMA_VERSION,
    extract_filing_evidence,
    governed_bridge_fields_from_evidence,
    reconcile_total,
)
from app.us_valuation.classification import classify_issuer
from app.us_valuation.xbrl import CompanyFactsNormalizer


FIXTURES = Path(__file__).parent / "fixtures" / "us"


CRM_HTML = """
<html><body>
<p>Marketable securities consisted of the following (in millions):</p>
<table>
<tr><td>Corporate notes and obligations</td><td>1,467</td></tr>
<tr><td>U.S. treasury securities</td><td>673</td></tr>
<tr><td>Mortgage-backed obligations</td><td>32</td></tr>
<tr><td>Asset-backed securities</td><td>551</td></tr>
<tr><td>Municipal securities</td><td>29</td></tr>
<tr><td>Commercial paper</td><td>94</td></tr>
<tr><td>Covered bonds</td><td>1</td></tr>
<tr><td>Other</td><td>55</td></tr>
<tr><td>Total marketable securities</td><td>2,902</td></tr>
</table>
<p>As of April 30, 2026, the maturities of lease liabilities under
noncancellable operating and finance leases were as follows (in millions).</p>
<table>
<tr><th>Fiscal Period</th><th>Operating Leases</th><th>Finance Leases</th></tr>
<tr><td>Total minimum lease payments</td><td>2,948</td><td>718</td></tr>
<tr><td>Less: Imputed interest</td><td>(344)</td><td>(54)</td></tr>
<tr><td>Total</td><td>2,604</td><td>664</td></tr>
</table>
</body></html>
"""


WDC_HTML = """
<html><body>
<p>Balance at April 3, 2026</p>
<table><tr><th>Convertible Preferred Stock</th><th>Common Stock</th></tr>
<tr><td>—</td><td>349</td></tr></table>
<p>On February 17, 2026, the Company converted all remaining outstanding
Preferred Shares into 7 million shares of the Company’s common stock.
On February 24, 2026, the Preferred Shares were eliminated.</p>
</body></html>
"""


def _metadata(ticker: str, cik: str, period_end: str, url: str) -> dict[str, str]:
    return {
        "ticker": ticker,
        "cik": cik,
        "form": "10-Q",
        "period_end": period_end,
        "filing_date": "2026-05-28" if ticker == "CRM" else "2026-05-01",
        "source_accession": (
            "0001108524-26-000127"
            if ticker == "CRM"
            else "0001628280-26-029054"
        ),
        "source_url": url,
    }


def test_crm_parser_keeps_finance_lease_split_unresolved() -> None:
    records = extract_filing_evidence(
        CRM_HTML,
        metadata=_metadata(
            "CRM",
            "0001108524",
            "2026-04-30",
            "https://www.sec.gov/Archives/edgar/data/1108524/000110852426000127/crm-20260430.htm",
        ),
    )

    lease_records = {
        record["field"]: record
        for record in records
        if record["field"] in {"finance_lease_current", "finance_lease_noncurrent"}
    }
    assert lease_records["finance_lease_current"]["status"] == "unresolved"
    assert lease_records["finance_lease_current"]["value"] is None
    assert lease_records["finance_lease_noncurrent"]["value"] is None
    assert any(
        record["field"] == "finance_lease_total_commitments"
        and record["value"] == 664
        and record["status"] == "context_only"
        for record in records
    )
    assert any(
        record["field"] == "finance_lease_total"
        and record["value"] == 664
        and record["status"] == "resolved"
        and record["evidence_class"] == "aggregate_reported"
        for record in records
    )

    commercial_paper = next(
        record for record in records if record["field"] == "commercial_paper"
    )
    assert commercial_paper["raw_value"] == 94
    assert commercial_paper["value"] == 0
    assert commercial_paper["status"] == "resolved"


def test_wdc_parser_resolves_converted_preferred_equity() -> None:
    records = extract_filing_evidence(
        WDC_HTML,
        metadata=_metadata(
            "WDC",
            "0000106040",
            "2026-04-03",
            "https://www.sec.gov/Archives/edgar/data/106040/000162828026029054/wdc-20260403.htm",
        ),
    )

    preferred = next(record for record in records if record["field"] == "preferred_equity")
    assert preferred["value"] == 0
    assert preferred["status"] == "resolved"
    assert preferred["confidence"] == "high"
    assert preferred["source_kind"] == "filing_note"
    assert preferred["parser_version"] == EVIDENCE_SCHEMA_VERSION

    governed = governed_bridge_fields_from_evidence(records, as_of_date="2026-07-31")
    assert governed["preferred_equity"]["value"] == 0
    assert governed["preferred_equity"]["source_accession"] == "0001628280-26-029054"


def test_governed_filing_evidence_converts_usd_millions_to_raw_dollars() -> None:
    records = [{
        **_metadata(
            "TEST", "0000000001", "2026-04-30", "https://example.test/test.htm"
        ),
        "field": "finance_lease_total",
        "value": 664,
        "status": "resolved",
        "confidence": "high",
        "unit": "USD millions",
        "source_kind": "filing_balance_sheet",
        "source_accession": "0001628280-26-000001",
        "locator": "balance sheet/finance lease liabilities",
        "excerpt": "Finance lease liabilities 664",
        "rationale": "Directly reported aggregate finance-lease liability.",
    }]

    governed = governed_bridge_fields_from_evidence(records, as_of_date="2026-07-31")

    assert governed["finance_lease_total"]["value"] == 664_000_000
    assert governed["finance_lease_total"]["reported_value"] == 664
    assert governed["finance_lease_total"]["reported_unit"] == "USD millions"


def test_reconciliation_reports_exact_component_match() -> None:
    result = reconcile_total(
        total=2902,
        components={
            "corporate_notes": 1467,
            "treasuries": 673,
            "mortgage_backed": 32,
            "asset_backed": 551,
            "municipal": 29,
            "commercial_paper": 94,
            "covered_bonds": 1,
            "other": 55,
        },
    )

    assert result == {
        "status": "pass",
        "reported_total": 2902.0,
        "component_total": 2902.0,
        "difference": 0.0,
        "tolerance": 0.01,
    }


def test_explicit_period_end_commercial_paper_zero_is_recovered() -> None:
    html = """
    <html><body><p>Commercial Paper</p>
    <p>As of March 28, 2026, the Company had no commercial paper outstanding.</p>
    </body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "AMD",
            "0000002488",
            "2026-03-28",
            "https://www.sec.gov/Archives/edgar/data/2488/example/amd.htm",
        ),
    )

    commercial = [record for record in records if record["field"] == "commercial_paper"]
    assert len(commercial) == 1
    assert commercial[0]["value"] == 0
    assert commercial[0]["source_kind"] == "filing_debt_note"
    assert commercial[0]["evidence_class"] == "reported_zero"
    assert "March 28, 2026" in commercial[0]["excerpt"]


def test_reported_commercial_paper_borrowing_is_recovered_in_reported_units() -> None:
    html = """
    <html><body><p>As of March 31, 2026, we had $349.0 million outstanding
    principal amount under our Commercial Paper program.</p></body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "MCHP",
            "0000827054",
            "2026-03-31",
            "https://www.sec.gov/Archives/edgar/data/827054/example/mchp.htm",
        ),
    )

    commercial = next(record for record in records if record["field"] == "commercial_paper")
    assert commercial["value"] == 349.0
    governed = governed_bridge_fields_from_evidence(records, as_of_date="2026-07-31")
    assert governed["commercial_paper"]["value"] == 349_000_000


def test_commercial_paper_section_no_outstanding_balance_resolves_zero() -> None:
    html = """
    <html><body><h3>Commercial Paper Program</h3>
    <p>The program permits short-term unsecured notes.</p>
    <p>It is supported by the revolving credit facility.</p>
    <p>As of June 30, 2026, there was no outstanding balance under this program.</p>
    </body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    commercial = next(record for record in records if record["field"] == "commercial_paper")
    assert commercial["value"] == 0
    assert commercial["evidence_class"] == "reported_zero"


@pytest.mark.parametrize(
    "sentence",
    [
        "As of June 30, 2026, our commercial paper program had a capacity of $25 billion, with no amounts outstanding.",
        "At June 30, 2026, the Company had no debt outstanding under the commercial paper program.",
        "As of June 30, 2026, we had no outstanding commercial paper.",
        "As of June 30, 2026, there were no short-term bank borrowings or commercial paper outstanding.",
        "As of June 30, 2026, we had no outstanding borrowings under the Credit Facility or issuances under the commercial paper program.",
    ],
)
def test_commercial_paper_zero_wording_variants_are_recovered(sentence: str) -> None:
    records = extract_filing_evidence(
        f"<html><body><p>{sentence}</p></body></html>",
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    commercial = next(record for record in records if record["field"] == "commercial_paper")
    assert commercial["value"] == 0
    assert commercial["evidence_class"] == "reported_zero"


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("We had $8.4 billion in commercial paper notes outstanding as of June 30, 2026.", 8_400),
        ("Commercial paper outstanding totaled $441 million as of June 30, 2026.", 441),
        ("At June 30, 2026, we had $2.7 billion of commercial paper outstanding.", 2_700),
        ("Outstanding borrowings under our commercial paper program were $380 million as of June 30, 2026.", 380),
        ("We had $8.4 billion and $3.5 billion in commercial paper notes outstanding as of June 30, 2026 and June 30, 2025, respectively.", 8_400),
    ],
)
def test_commercial_paper_amount_wording_variants_are_recovered(
    sentence: str, expected: float
) -> None:
    records = extract_filing_evidence(
        f"<html><body><p>{sentence}</p></body></html>",
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    commercial = next(record for record in records if record["field"] == "commercial_paper")
    assert commercial["value"] == expected
    assert commercial["evidence_class"] == "reported"


def test_commercial_paper_parser_does_not_mix_adjacent_debt_paragraphs() -> None:
    html = """
    <html><body>
    <p>As of June 30, 2026, short-term debt included commercial paper borrowings of $1,025 million.</p>
    <p>As of June 30, 2026, no amounts were outstanding under our revolving credit facility.</p>
    </body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    commercial = next(record for record in records if record["field"] == "commercial_paper")
    assert commercial["value"] == 1_025
    assert commercial["evidence_class"] == "reported"


@pytest.mark.parametrize(
    "line",
    [
        "Preferred stock, $5 par value: Authorized – 5 million shares; Issued and outstanding – none",
        "We have 7.5 million authorized preferred shares, none of which was outstanding as of June 30, 2026.",
        "There was no preferred stock outstanding as of June 30, 2026.",
        "As of June 30, 2026, no preferred shares had been issued.",
        "No shares of Preferred Stock are currently issued and outstanding.",
        "Preferred Stock Authorized 5,000,000 shares; no shares were issued or outstanding during any period presented.",
    ],
)
def test_explicit_preferred_zero_wording_variants_are_recovered(line: str) -> None:
    records = extract_filing_evidence(
        f"<html><body><p>{line}</p></body></html>",
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    preferred = next(record for record in records if record["field"] == "preferred_equity")
    assert preferred["value"] == 0
    assert preferred["evidence_class"] == "reported_zero"


def test_preferred_liquidation_preference_balance_is_recovered() -> None:
    html = """
    <html><body><h2>Condensed Consolidated Balance Sheets</h2><p>(In millions)</p>
    <p>ASSETS</p><p>Cash and cash equivalents 100 90</p><p>Total assets 6,000 5,900</p>
    <p>LIABILITIES AND STOCKHOLDERS' EQUITY</p><p>Total liabilities 200 190</p>
    <p>Mandatory convertible preferred stock, 6.00% Series A, par value $1.00 –
    20,000,000 shares authorized; 5,750,000 shares issued; aggregate liquidation preference $5,750</p>
    <p>Total stockholders' equity 5,800 5,710</p>
    </body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "BA", "0000000001", "2026-06-30", "https://example.test/ba.htm"
        ),
    )

    preferred = next(record for record in records if record["field"] == "preferred_equity")
    assert preferred["value"] == 5_750
    assert preferred["evidence_class"] == "reported"


def test_direct_period_end_nci_amount_in_equity_is_recovered() -> None:
    html = """
    <html><body><p>The noncontrolling interest attributed to these consolidated
    investments was $271 million and $162 million as of June 30, 2026 and
    June 30, 2025, respectively, and is included in the equity section of the
    Consolidated Balance Sheets.</p></body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    nci = next(record for record in records if record["field"] == "noncontrolling_interests")
    assert nci["value"] == 271
    assert nci["evidence_class"] == "reported"


def test_reconciled_current_portfolio_resolves_noncurrent_securities_zero() -> None:
    html = """
    <html><body>
    <h2>Condensed Consolidated Balance Sheets</h2><p>(In millions)</p>
    <p>Assets</p><table>
    <tr><td>Marketable securities</td><td>100</td><td>90</td></tr>
    <tr><td>Total assets</td><td>500</td><td>450</td></tr>
    <tr><td>Total liabilities</td><td>200</td><td>180</td></tr>
    </table><p>See accompanying notes.</p>
    <h3>Marketable securities</h3><table>
    <tr><td>Total marketable securities</td><td>95</td><td>5</td><td>100</td></tr>
    </table></body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST",
            "0000123456",
            "2026-03-31",
            "https://www.sec.gov/Archives/edgar/data/123456/example/test.htm",
        ),
    )

    noncurrent = next(
        record for record in records if record["field"] == "marketable_securities_noncurrent"
    )
    assert noncurrent["value"] == 0
    assert noncurrent["source_kind"] == "filing_table_reconciled_classification"
    assert noncurrent["evidence_class"] == "inferred_zero"


def test_unreconciled_current_portfolio_does_not_infer_noncurrent_zero() -> None:
    html = """
    <html><body>
    <h2>Condensed Consolidated Balance Sheets</h2><p>Assets</p><table>
    <tr><td>Marketable securities</td><td>100</td></tr>
    <tr><td>Total assets</td><td>500</td></tr>
    <tr><td>Total liabilities</td><td>200</td></tr>
    </table><p>See accompanying notes.</p>
    <h3>Marketable securities</h3><table>
    <tr><td>Total marketable securities</td><td>75</td></tr>
    </table></body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST",
            "0000123456",
            "2026-03-31",
            "https://www.sec.gov/Archives/edgar/data/123456/example/test.htm",
        ),
    )

    assert not any(
        record["field"] == "marketable_securities_noncurrent" for record in records
    )


def test_short_term_investment_table_alone_does_not_resolve_noncurrent_zero() -> None:
    html = """
    <html><body><h2>Condensed Consolidated Balance Sheets</h2>
    <p>(In thousands)</p><p>Assets</p>
    <p>Short-term investments 71,966 72,929</p><p>Total assets 500,000</p>
    <p>Total liabilities 200,000</p><p>See accompanying notes.</p>
    <h3>Cash Equivalents and Short-term Investments</h3>
    <p>As of April 30, 2026, the balances are as follows:</p>
    <p>Short-term investments:</p><p>U.S. Treasury securities 5,661</p>
    <p>Municipal bonds 23,414</p><p>Corporate debt securities 42,714</p>
    <p>Other 177</p><p>Total: 71,966</p>
    </body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-04-30", "https://example.test/test.htm"
        ),
    )

    assert not any(
        record["field"] == "marketable_securities_noncurrent" for record in records
    )


def test_explicit_all_current_securities_policy_resolves_noncurrent_zero() -> None:
    html = """
    <html><body><p>At each balance sheet date presented, we classify all of our
    investments in debt securities as available-for-sale and as current assets
    because they represent funds available for current operations.</p></body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    noncurrent = next(
        record for record in records if record["field"] == "marketable_securities_noncurrent"
    )
    assert noncurrent["value"] == 0
    assert noncurrent["evidence_class"] == "inferred_zero"
    assert "current assets" in noncurrent["excerpt"]


def test_balance_sheet_unit_is_detected_and_converted_to_raw_dollars() -> None:
    html = """
    <html><body><h2>Condensed Consolidated Balance Sheets</h2>
    <p>(In thousands)</p><p>Assets</p>
    <p>Short-term investments 100 90</p><p>Total assets 500 450</p>
    <p>Long-term debt 300 250</p><p>Total liabilities 400 350</p>
    <p>See accompanying notes.</p></body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-03-31", "https://example.test/test.htm"
        ),
    )

    debt = next(record for record in records if record["field"] == "noncurrent_debt")
    assert debt["unit"] == "USD thousands"
    governed = governed_bridge_fields_from_evidence(records, as_of_date="2026-07-31")
    assert governed["noncurrent_debt"]["value"] == 300_000


def test_balance_sheet_locator_skips_toc_and_accepts_unaudited_heading() -> None:
    html = """
    <html><body>
    <p>Condensed Consolidated Balance Sheets</p><p>Assets and liabilities overview</p>
    <p>Contents 1</p><p>Contents 2</p><p>Contents 3</p><p>Contents 4</p>
    <p>Contents 5</p><p>Contents 6</p><p>Contents 7</p><p>Contents 8</p>
    <p>Long-term debt 999</p><p>Contents 10</p><p>Contents 11</p><p>Contents 12</p>
    <h2>UNAUDITED CONDENSED CONSOLIDATED BALANCE SHEETS AS OF JUNE 30, 2026</h2>
    <p>(In millions)</p><p>Assets</p><p>Current assets:</p>
    <p>Short-term investments 300 100</p><p>Total assets 1,000 900</p>
    <p>Long-term debt 300 250</p>
    <p>Total liabilities 500 450</p><p>Total stockholders' equity 500 450</p>
    <p>Total liabilities and stockholders' equity 1,000 900</p>
    <p>See accompanying notes.</p></body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    current = next(
        record for record in records if record["field"] == "marketable_securities_current"
    )
    assert current["value"] == 300
    assert [
        record["value"] for record in records if record["field"] == "noncurrent_debt"
    ] == [300]


def test_currently_due_debt_is_current_and_related_party_row_does_not_conflict() -> None:
    html = """
    <html><body><h2>Condensed Consolidated Balance Sheets</h2>
    <p>(In millions)</p><p>Assets</p><p>Total assets 50,000</p>
    <p>Long-term debt currently due 5,296 3,412</p>
    <p>Long-term debt 31,858 34,288</p>
    <p>Long-term debt – related party 186 177</p>
    <p>Total liabilities 40,000</p><p>See accompanying notes.</p></body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-03-31", "https://example.test/test.htm"
        ),
    )

    current = [record for record in records if record["field"] == "current_debt"]
    noncurrent = [record for record in records if record["field"] == "noncurrent_debt"]
    assert [record["value"] for record in current] == [5296]
    assert [record["value"] for record in noncurrent] == [31858]


def test_balance_sheet_rows_and_hidden_inline_xbrl_are_parsed_conservatively() -> None:
    html = """
    <html><head><script>Short-term investments 999999</script></head><body>
    <h2>CONDENSED CONSOLIDATED BALANCE SHEETS</h2>
    <p>(in millions)</p>
        <p>ASSETS</p>
        <p>Short-term investments 100 90</p>
        <p>Total assets 400 410</p>
    <p>LIABILITIES AND STOCKHOLDERS' EQUITY</p>
    <p>Current portion of long-term debt — 20</p>
    <p>Long-term debt 300 400</p>
    <p>Preferred stock, no shares issued and outstanding — —</p>
    <p>Total liabilities and stockholders' equity 400 410</p>
    <p>See notes to consolidated financial statements.</p>
    </body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST",
            "0000000001",
            "2026-06-30",
            "https://example.test/filing.htm",
        ),
    )
    resolved = {record["field"]: record for record in records}
    assert resolved["marketable_securities_current"]["value"] == 100
    assert resolved["current_debt"]["value"] == 0
    assert resolved["noncurrent_debt"]["value"] == 300
    assert resolved["preferred_equity"]["value"] == 0
    assert all("999999" not in record["excerpt"] for record in records)


def test_commercial_paper_borrowing_narrative_is_not_investment_evidence() -> None:
    html = """
    <html><body>
    <p>Commercial Paper Program — No commercial paper notes were outstanding.</p>
    </body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST",
            "0000000001",
            "2026-06-30",
            "https://example.test/filing.htm",
        ),
    )
    assert not any(record["field"] == "commercial_paper" for record in records)


def test_complete_equity_section_does_not_resolve_absent_preferred_equity() -> None:
    html = """
    <html><body>
    <h2>CONDENSED CONSOLIDATED BALANCE SHEETS</h2>
    <p>ASSETS</p><p>Cash and cash equivalents 100 90</p><p>Total assets 100 90</p>
    <p>LIABILITIES AND STOCKHOLDERS’ EQUITY</p>
    <p>Total liabilities 20 30</p>
    <p>Stockholders’ equity:</p>
    <p>Common stock and additional paid-in capital 120 110</p>
    <p>Accumulated deficit (40) (50)</p>
    <p>Total stockholders’ equity 80 60</p>
    <p>Total liabilities and stockholders’ equity 100 90</p>
    <p>See notes to consolidated financial statements.</p>
    </body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "ADSK", "0000769397", "2026-04-30", "https://example.test/adsk.htm"
        ),
    )

    assert not any(record["field"] == "preferred_equity" for record in records)


def test_explicit_full_ownership_resolves_noncontrolling_interests() -> None:
    html = """
    <html><body>
    <h2>CONDENSED CONSOLIDATED BALANCE SHEETS</h2>
    <p>ASSETS</p><p>Total assets 100 90</p>
    <p>LIABILITIES AND STOCKHOLDERS’ EQUITY</p>
    <p>Total liabilities 20 30</p>
    <p>Stockholders’ equity:</p><p>Common stock 80 60</p>
    <p>Total stockholders’ equity 80 60</p>
    <p>Total liabilities and stockholders’ equity 100 90</p>
    <p>See notes to consolidated financial statements.</p>
    <p>We acquired all of the remaining outstanding shares and now own 100% of the outstanding equity.</p>
    </body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "FTNT", "0001262039", "2026-06-30", "https://example.test/ftnt.htm"
        ),
    )

    nci = next(record for record in records if record["field"] == "noncontrolling_interests")
    assert nci["value"] == 0
    assert nci["status"] == "resolved"
    assert nci["source_kind"] == "filing_note"


def test_none_issued_preferred_stock_statement_resolves_reported_zero() -> None:
    html = """
    <html><body><p>Preferred stock, $0.01 par value, 2,000,000 shares
    authorized; none issued and outstanding as of June 30, 2026.</p></body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    preferred = next(record for record in records if record["field"] == "preferred_equity")
    assert preferred["value"] == 0
    assert preferred["evidence_class"] == "reported_zero"


def test_direct_balance_sheet_nci_row_is_recovered() -> None:
    html = """
    <html><body><h2>Condensed Consolidated Balance Sheets</h2>
    <p>(In millions)</p><p>Assets</p><p>Total assets 10,000</p>
    <p>Noncontrolling interests 125 120</p><p>Total liabilities 6,000</p>
    <p>Total stockholders' equity 4,000</p>
    <p>Total liabilities and stockholders' equity 10,000</p>
    <p>See accompanying notes.</p></body></html>
    """
    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "TEST", "0000000001", "2026-06-30", "https://example.test/test.htm"
        ),
    )

    nci = next(record for record in records if record["field"] == "noncontrolling_interests")
    assert nci["value"] == 125
    assert nci["evidence_class"] == "reported"


def test_current_only_investment_classification_resolves_noncurrent_zero() -> None:
    html = """
    <html><body>
    <h2>CONSOLIDATED BALANCE SHEETS</h2>
    <p>ASSETS</p><p>Short-term investments 1,514 1,104</p>
    <p>Other non-current assets 1,582 1,643</p><p>Total assets 3,096 2,747</p>
    <p>LIABILITIES AND STOCKHOLDERS' EQUITY</p><p>Total liabilities 2,000 1,900</p>
    <p>Total stockholders' equity 1,096 847</p>
    <p>Total liabilities and stockholders' equity 3,096 2,747</p>
    <p>See notes to consolidated financial statements.</p>
    <p>Our fixed income debt investments are classified as available-for-sale investments.</p>
    </body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "NTAP", "0001002047", "2026-04-24", "https://example.test/ntap.htm"
        ),
    )

    noncurrent = next(
        record for record in records if record["field"] == "marketable_securities_noncurrent"
    )
    assert noncurrent["value"] == 0
    assert noncurrent["status"] == "resolved"
    assert noncurrent["source_kind"] == "filing_balance_sheet_inferred_zero"


def test_cash_equivalent_only_policy_resolves_separate_marketable_securities_zero() -> None:
    html = """
    <html><body>
    <h2>CONDENSED CONSOLIDATED BALANCE SHEETS</h2>
    <p>ASSETS</p><p>Cash and cash equivalents 1,146 891</p>
    <p>Other current assets 426 363</p><p>Other assets, net 421 426</p>
    <p>Total assets 1,993 1,680</p>
    <p>LIABILITIES AND SHAREHOLDERS’ EQUITY</p><p>Total liabilities 1,000 900</p>
    <p>Total shareholders’ equity 993 780</p>
    <p>Total liabilities and shareholders’ equity 1,993 1,680</p>
    <p>See notes to consolidated financial statements.</p>
    <p>Our cash and cash equivalents are maintained in investments with remaining maturities of 90 days or less at the time of purchase.</p>
    </body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "STX", "0001137789", "2026-04-03", "https://example.test/stx.htm"
        ),
    )

    resolved = {record["field"]: record for record in records}
    assert resolved["marketable_securities_current"]["value"] == 0
    assert resolved["marketable_securities_noncurrent"]["value"] == 0
    assert resolved["marketable_securities_current"]["source_kind"] == (
        "filing_balance_sheet_inferred_zero"
    )


def test_complete_debt_free_liability_section_resolves_anet_financing_zeros() -> None:
    html = """
    <html><body>
    <h2>CONDENSED CONSOLIDATED BALANCE SHEETS</h2>
    <p>ASSETS</p><p>Total assets 200 180</p>
    <p>LIABILITIES AND STOCKHOLDERS’ EQUITY</p>
    <p>Current liabilities:</p><p>Accounts payable 20 18</p>
    <p>Accrued liabilities 10 9</p><p>Deferred revenue 30 28</p>
    <p>Other current liabilities 5 4</p><p>Total current liabilities 65 59</p>
    <p>Deferred revenue, non-current 20 19</p>
    <p>Other long-term liabilities 15 14</p><p>Total liabilities 100 92</p>
    <p>Stockholders’ equity:</p><p>Total stockholders’ equity 100 88</p>
    <p>Total liabilities and stockholders’ equity 200 180</p>
    <p>See notes to consolidated financial statements.</p>
    </body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "ANET", "0001596532", "2026-03-31", "https://example.test/anet.htm"
        ),
    )

    resolved = {record["field"]: record for record in records}
    for field in (
        "current_debt",
        "noncurrent_debt",
        "finance_lease_current",
        "finance_lease_noncurrent",
    ):
        assert resolved[field]["value"] == 0
        assert resolved[field]["status"] == "resolved"
        assert resolved[field]["source_kind"] == "filing_balance_sheet_inferred_zero"


def test_majority_owned_subsidiaries_do_not_imply_zero_nci() -> None:
    html = """
    <html><body>
    <h2>CONDENSED CONSOLIDATED BALANCE SHEETS</h2>
    <p>ASSETS</p><p>Total assets 200 180</p>
    <p>LIABILITIES AND SHAREHOLDERS’ EQUITY</p><p>Total liabilities 100 92</p>
    <p>Shareholders’ equity:</p><p>Ordinary shares and additional paid-in capital 150 140</p>
    <p>Accumulated deficit (50) (52)</p><p>Total shareholders’ equity 100 88</p>
    <p>Total liabilities and shareholders’ equity 200 180</p>
    <p>See notes to consolidated financial statements.</p>
    <p>The consolidated financial statements include the accounts of the Company and all its wholly-owned and majority-owned subsidiaries, after elimination of intercompany balances.</p>
    </body></html>
    """

    records = extract_filing_evidence(
        html,
        metadata=_metadata(
            "STX", "0001137789", "2026-04-03", "https://example.test/stx.htm"
        ),
    )

    assert not any(record["field"] == "noncontrolling_interests" for record in records)


def test_recovered_evidence_enters_normalizer_as_governed_bridge_fact() -> None:
    submission = json.loads(
        (FIXTURES / "crm-submissions.json").read_text(encoding="utf-8")
    )
    recent = submission["filings"]["recent"]
    filing_records = [
        {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(len(recent["accessionNumber"]))
    ]
    classification = classify_issuer(submission)
    records = extract_filing_evidence(
        CRM_HTML,
        metadata=_metadata(
            "CRM",
            "0001108524",
            "2026-04-30",
            "https://www.sec.gov/Archives/edgar/data/1108524/000110852426000127/crm-20260430.htm",
        ),
    )

    financials = CompanyFactsNormalizer(
        json.loads((FIXTURES / "crm-companyfacts.json").read_text(encoding="utf-8")),
        fiscal_year_end=submission["fiscalYearEnd"],
        as_of_date="2026-07-31",
        filing_records=filing_records,
    ).normalize(
        annual_count=5,
        verified_zero_bridge_fields=classification["verified_zero_bridge_fields"],
        governed_bridge_fields=classification["governed_bridge_fields"],
        filing_evidence=records,
    )

    balance_sheet = financials["balance_sheet"]
    assert balance_sheet["field_states"]["commercial_paper"] == "governed_filing_fact"
    assert balance_sheet["values"]["commercial_paper"] == 0
    assert "investment asset" in balance_sheet["sources"]["commercial_paper"]["rationale"]
    assert balance_sheet["field_states"]["finance_lease_total"] == "governed_filing_fact"
    assert balance_sheet["values"]["finance_lease_total"] == 664_000_000
    assert balance_sheet["sources"]["finance_lease_total"]["evidence_class"] == "aggregate_reported"
    assert balance_sheet["bridge_missing_fields"] == []
    assert balance_sheet["bridge_complete"] is True
