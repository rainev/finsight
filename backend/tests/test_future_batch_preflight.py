"""Batch 01 lessons become deterministic future-batch preflight controls."""

from app.us_valuation.future_batch_preflight import assess_future_batch_preflight


def _facts(accession: str | None) -> dict:
    rows = [] if accession is None else [{"accn": accession, "filed": "2026-07-01", "val": 1}]
    return {"facts": {"us-gaap": {"Revenue": {"units": {"USD": rows}}}}}


def test_empty_current_accession_triggers_direct_filing_and_complete_borrowing() -> None:
    result = assess_future_batch_preflight(
        companyfacts=_facts(None),
        latest_eligible_accession="0000753308-26-000060",
        valuation_date="2026-08-14",
        captive_finance_activity=False,
        cyclical_exposure=False,
        major_business_change=False,
        capital_intensive_equity_route=True,
    )
    assert result.direct_filing_required is True
    assert result.required_actions == (
        "CAPTURE_EXACT_FILING_PACKAGE",
        "RECONCILE_ALL_INTEREST_BEARING_BORROWING",
    )


def test_captive_finance_and_post_event_cycle_route_before_modeling() -> None:
    dell = assess_future_batch_preflight(
        companyfacts=_facts("0001571996-26-000030"),
        latest_eligible_accession="0001571996-26-000030",
        valuation_date="2026-08-14",
        captive_finance_activity=True,
        cyclical_exposure=True,
        major_business_change=False,
        capital_intensive_equity_route=False,
    )
    assert dell.required_actions == ("USE_EQUITY_LEVEL_CAPTIVE_FINANCE_ROUTE",)

    wdc = assess_future_batch_preflight(
        companyfacts=_facts("0001628280-26-057139"),
        latest_eligible_accession="0001628280-26-057139",
        valuation_date="2026-08-14",
        captive_finance_activity=False,
        cyclical_exposure=True,
        major_business_change=True,
        capital_intensive_equity_route=False,
    )
    assert wdc.cycle_history_reset_required is True
    assert wdc.required_actions == (
        "RESET_CYCLE_HISTORY_AND_REQUIRE_COMPARABLE_RANGE",
    )
