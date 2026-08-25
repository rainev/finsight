"""Hermetic source-contract tests for practical AAPL and ANET bridge inputs."""

from app.us_valuation.batch_01_practical_inputs import practical_bridge_evidence


def _fact(value: float, *, end: str, accn: str, frame: str) -> dict:
    return {
        "units": {
            "USD": [
                {
                    "val": value,
                    "end": end,
                    "filed": "2026-08-01",
                    "accn": accn,
                    "form": "10-Q",
                    "frame": frame,
                }
            ]
        }
    }


def test_aapl_joint_claim_high_equals_reported_equity_not_double() -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "StockholdersEquity": _fact(
                    107_520_000_000,
                    end="2026-06-27",
                    accn="0000320193-26-000020",
                    frame="CY2026Q2I",
                )
            }
        }
    }
    records = practical_bridge_evidence(ticker="AAPL", companyfacts=facts)
    assert {record.field for record in records} == {
        "preferred_equity",
        "noncontrolling_interests",
    }
    assert sum(record.uncertainty.high for record in records) == 107_520_000_000
    assert all(record.value is None for record in records)


def test_anet_uses_reported_total_and_liability_claim_ceiling() -> None:
    accession = "0001596532-26-000175"
    period = "2026-06-30"
    facts = {
        "facts": {
            "us-gaap": {
                "AvailableForSaleSecuritiesDebtSecurities": _fact(
                    11_053_100_000,
                    end=period,
                    accn=accession,
                    frame="CY2026Q2I",
                ),
                "AvailableForSaleSecuritiesDebtSecuritiesCurrent": _fact(
                    11_053_100_000,
                    end=period,
                    accn=accession,
                    frame="CY2026Q2I",
                ),
                "Liabilities": _fact(
                    8_922_400_000,
                    end=period,
                    accn=accession,
                    frame="CY2026Q2I",
                ),
                "StockholdersEquity": _fact(
                    14_797_700_000,
                    end=period,
                    accn=accession,
                    frame="CY2026Q2I",
                ),
            }
        }
    }
    records = {
        record.field: record
        for record in practical_bridge_evidence(ticker="ANET", companyfacts=facts)
    }
    assert records["marketable_securities_total"].value == 11_053_100_000
    assert records["total_interest_bearing_debt"].uncertainty.high == 8_922_400_000
    assert records["total_interest_bearing_debt"].value is None
    assert records["noncontrolling_interests"].uncertainty.high == 14_797_700_000
