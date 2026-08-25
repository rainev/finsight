from __future__ import annotations

import json
from pathlib import Path

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

    commercial_paper = next(
        record for record in records if record["field"] == "commercial_paper"
    )
    assert commercial_paper["raw_value"] == 94
    assert commercial_paper["value"] == 0
    assert commercial_paper["status"] == "resolved"


def test_generic_note_total_is_not_assumed_current() -> None:
    records = extract_filing_evidence(
        CRM_HTML,
        metadata=_metadata(
            "OTHER",
            "0000000001",
            "2026-04-30",
            "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/other-20260430.htm",
        ),
    )

    totals = [
        record
        for record in records
        if record["field"] == "marketable_securities_total"
    ]
    assert len(totals) == 1
    assert totals[0]["value"] == 2_902
    assert not any(
        record["field"] == "marketable_securities_current"
        for record in records
    )


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
    assert balance_sheet["bridge_blocking_fields"] == []
    assert balance_sheet["bridge_bounded_fields"] == [
        "finance_lease_current",
        "finance_lease_noncurrent",
    ]
    for field, value in {
        "finance_lease_current": 275_000_000.0,
        "finance_lease_noncurrent": 260_000_000.0,
    }.items():
        assert balance_sheet["availability"][field]["value"] == value
        assert balance_sheet["availability"][field]["freshness"] == (
            "carried_forward"
        )
        assert balance_sheet["availability"][field]["fallback_level"] == (
            "annual_carried_forward"
        )
