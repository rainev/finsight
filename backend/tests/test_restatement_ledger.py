"""FOD2 contracts for point-in-time restatement selection."""

from __future__ import annotations

from app.us_valuation.restatement_ledger import build_restatement_ledger


def _candidates() -> list[dict[str, object]]:
    return [
        {
            "value": 100.0,
            "tag": "us-gaap:LongTermDebtNoncurrent",
            "unit": "USD",
            "period_end": "2025-12-31",
            "dimensions": (),
            "accession": "0000123456-26-000001",
            "filed_date": "2026-02-20",
            "source_url": "https://www.sec.gov/original",
        },
        {
            "value": 120.0,
            "tag": "us-gaap:LongTermDebtNoncurrent",
            "unit": "USD",
            "period_end": "2025-12-31",
            "dimensions": (),
            "accession": "0000123456-26-000099",
            "filed_date": "2026-04-10",
            "source_url": "https://www.sec.gov/amendment",
        },
    ]


def test_restatement_ledger_selects_only_the_fact_public_by_the_valuation_date() -> None:
    before_amendment = build_restatement_ledger(_candidates(), valuation_date="2026-03-01")
    after_amendment = build_restatement_ledger(_candidates(), valuation_date="2026-05-01")

    assert before_amendment.selected[0].accession == "0000123456-26-000001"
    assert before_amendment.selected[0].value == 100.0
    assert after_amendment.selected[0].accession == "0000123456-26-000099"
    assert after_amendment.selected[0].value == 120.0


def test_restatement_ledger_links_original_and_corrected_facts_by_semantic_context() -> None:
    ledger = build_restatement_ledger(_candidates(), valuation_date="2026-05-01")

    assert len(ledger.links) == 1
    link = ledger.links[0]
    assert link.original_accession == "0000123456-26-000001"
    assert link.corrected_accession == "0000123456-26-000099"
    assert link.semantic_context["tag"] == "us-gaap:LongTermDebtNoncurrent"
    assert link.semantic_context["period_end"] == "2025-12-31"
    assert link.semantic_context["unit"] == "USD"


def test_ordinary_comparative_value_change_is_not_confirmed_as_a_restatement() -> None:
    candidates = _candidates()
    candidates[0].update({"form": "10-K", "report_date": "2025-12-31"})
    candidates[1].update({"form": "10-Q", "report_date": "2026-03-31"})

    link = build_restatement_ledger(candidates, valuation_date="2026-05-01").links[0]

    assert link.link_type == "unresolved_value_change"
    assert link.confirmed_restatement is False
