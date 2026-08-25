"""FOD3 contracts for SEC-filed REIT Exhibit 99 supplements."""

from __future__ import annotations

import pytest

from app.us_valuation.reit_supplement import discover_filed_exhibit99, parse_reit_reconciliation



def _filings() -> list[dict[str, object]]:
    return [
        {"accession": "0000726728-26-000010", "form": "8-K", "filed": "2026-08-10", "attachments": [{"name": "earnings.htm", "exhibit": "99.1", "url": "https://www.sec.gov/ex99"}]},
        {"accession": "0000726728-26-000011", "form": "8-K", "filed": "2026-08-15", "attachments": [{"name": "future.htm", "exhibit": "99.1", "url": "https://www.sec.gov/future"}]},
    ]


def test_discovery_returns_exact_pre_cutoff_sec_filed_exhibit99_attachment() -> None:
    exhibit = discover_filed_exhibit99(_filings(), valuation_date="2026-08-14")
    assert exhibit.accession == "0000726728-26-000010"
    assert exhibit.exhibit == "99.1"
    assert exhibit.source_url == "https://www.sec.gov/ex99"


def test_reit_reconciliation_preserves_issuer_defined_affo_and_source_identity() -> None:
    packet = parse_reit_reconciliation(
        """<table><caption>Supplemental Information</caption><tr><td>FFO</td><td>100</td></tr><tr><td>Straight-line rent</td><td>5</td></tr><tr><td>Recurring maintenance capital</td><td>7</td></tr><tr><td>AFFO</td><td>88</td></tr><tr><td>Occupancy</td><td>98.2%</td></tr></table>""",
        accession="0000726728-26-000010", source_url="https://www.sec.gov/ex99", period_end="2026-06-30", filed_date="2026-08-10",
        valuation_date="2026-08-14",
    )
    assert packet.affo_definition == "issuer_defined"
    assert packet.accession == "0000726728-26-000010"
    assert {fact.field for fact in packet.facts} >= {"ffo", "affo", "straight_line_rent_adjustment", "recurring_maintenance_capex", "occupancy"}
    assert packet.reconciliation_status == "pass"
    assert packet.unexplained_affo_residual == 0


def test_reit_supplement_rejects_post_cutoff_or_non_sec_attachment() -> None:
    with pytest.raises(ValueError, match="cutoff|SEC"):
        discover_filed_exhibit99([_filings()[1]], valuation_date="2026-08-14")


def test_reit_parser_rejects_future_filing_and_ambiguous_multi_period_columns() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        parse_reit_reconciliation(
            "<table><tr><td>FFO</td><td>100</td></tr></table>",
            accession="0000726728-26-000010", source_url="https://www.sec.gov/ex99",
            period_end="2026-06-30", filed_date="2026-08-15", valuation_date="2026-08-14",
        )
    with pytest.raises(ValueError, match="multiple columns|period column"):
        parse_reit_reconciliation(
            "<table><tr><th>Metric</th><th>2025</th><th>2024</th></tr><tr><td>FFO</td><td>100</td><td>90</td></tr></table>",
            accession="0000726728-26-000010", source_url="https://www.sec.gov/ex99",
            period_end="2026-06-30", filed_date="2026-08-10", valuation_date="2026-08-14",
        )
