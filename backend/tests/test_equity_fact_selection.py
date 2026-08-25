import pytest

from app.us_valuation.equity_fact_selection import annual_facts, latest_instant, source_statement


def test_selector_is_point_in_time_and_exactly_attributable() -> None:
    gaap = {"NetIncomeLoss": {"units": {"USD": [
        {"val": 2.0, "start": "2025-01-01", "end": "2026-03-31", "filed": "2026-08-15", "accn": "0000000001-26-000002", "form": "10-K", "fy": 2026, "fp": "FY"},
        {"val": 1.0, "start": "2025-01-01", "end": "2025-12-31", "filed": "2026-02-20", "accn": "0000000001-26-000001", "form": "10-K", "fy": 2025, "fp": "FY"},
    ]}}}
    selected = annual_facts(gaap, concepts=("NetIncomeLoss",), unit="USD", valuation_date="2026-08-14")[2025]
    assert selected.value == 1.0
    statement = source_statement(
        selected,
        submissions={
            "filings": {
                "recent": {
                    "accessionNumber": [selected.accession],
                    "primaryDocument": ["annual.htm"],
                    "form": [selected.form],
                    "filingDate": [selected.filed_date],
                }
            }
        },
        cik="0000320193",
    )
    assert statement["url"] == "https://www.sec.gov/Archives/edgar/data/320193/000000000126000001/annual.htm"


def test_selector_rejects_missing_provenance_and_conflicts() -> None:
    gaap = {"X": {"units": {"USD": [{"val": 1.0, "end": "2026-01-01"}]}}}
    assert latest_instant(gaap, concepts=("X",), unit="USD", valuation_date="2026-08-14") is None


def test_annual_selector_excludes_same_filing_fourth_quarter_duration() -> None:
    gaap = {
        "NetIncomeLoss": {
            "units": {
                "USD": [
                    {
                        "val": 100.0,
                        "start": "2025-01-01",
                        "end": "2025-12-31",
                        "filed": "2026-02-20",
                        "accn": "0000000001-26-000001",
                        "form": "10-K",
                        "fy": 2025,
                        "fp": "FY",
                    },
                    {
                        "val": 25.0,
                        "start": "2025-10-01",
                        "end": "2025-12-31",
                        "filed": "2026-02-20",
                        "accn": "0000000001-26-000001",
                        "form": "10-K",
                        "fy": 2025,
                        "fp": "FY",
                    },
                ]
            }
        }
    }

    selected = annual_facts(
        gaap,
        concepts=("NetIncomeLoss",),
        unit="USD",
        valuation_date="2026-08-14",
    )
    assert selected[2025].value == 100.0
    assert selected[2025].period_start == "2025-01-01"


@pytest.mark.parametrize(
    "change",
    [
        {"filed": "not-a-date"},
        {"end": "not-a-date"},
        {"accn": "invalid"},
        {"form": "8-K"},
    ],
)
def test_selector_rejects_malformed_or_ineligible_provenance(change: dict) -> None:
    raw = {
        "val": 1.0,
        "end": "2025-12-31",
        "filed": "2026-02-20",
        "accn": "0000000001-26-000001",
        "form": "10-K",
    }
    raw.update(change)
    gaap = {"X": {"units": {"USD": [raw]}}}
    assert latest_instant(
        gaap,
        concepts=("X",),
        unit="USD",
        valuation_date="2026-08-14",
    ) is None


def test_source_statement_rejects_filing_metadata_mismatch() -> None:
    fact = latest_instant(
        {
            "X": {
                "units": {
                    "USD": [
                        {
                            "val": 1.0,
                            "end": "2025-12-31",
                            "filed": "2026-02-20",
                            "accn": "0000000001-26-000001",
                            "form": "10-K",
                        }
                    ]
                }
            }
        },
        concepts=("X",),
        unit="USD",
        valuation_date="2026-08-14",
    )
    assert fact is not None
    with pytest.raises(ValueError, match="conflicts"):
        source_statement(
            fact,
            submissions={
                "filings": {
                    "recent": {
                        "accessionNumber": [fact.accession],
                        "primaryDocument": ["annual.htm"],
                        "form": ["10-Q"],
                        "filingDate": [fact.filed_date],
                    }
                }
            },
            cik="0000000001",
        )
