"""Cheap source/model preflight controls proven by controlled Batch 01."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class FutureBatchPreflight:
    current_accession_fact_count: int
    direct_filing_required: bool
    equity_level_model_required: bool
    cycle_history_reset_required: bool
    complete_borrowing_required: bool
    required_actions: tuple[str, ...]


def _accession_fact_count(
    companyfacts: Mapping[str, Any], accession: str, *, cutoff: str
) -> int:
    count = 0
    for namespace in companyfacts.get("facts", {}).values():
        if not isinstance(namespace, Mapping):
            continue
        for concept in namespace.values():
            units = concept.get("units", {}) if isinstance(concept, Mapping) else {}
            for rows in units.values():
                if not isinstance(rows, list):
                    continue
                count += sum(
                    1
                    for row in rows
                    if isinstance(row, Mapping)
                    and row.get("accn") == accession
                    and row.get("filed", "") <= cutoff
                )
    return count


def assess_future_batch_preflight(
    *,
    companyfacts: Mapping[str, Any],
    latest_eligible_accession: str,
    valuation_date: str,
    captive_finance_activity: bool,
    cyclical_exposure: bool,
    major_business_change: bool,
    capital_intensive_equity_route: bool,
) -> FutureBatchPreflight:
    """Identify the minimum recovery work before a future valuation is built."""

    if any(
        not isinstance(value, bool)
        for value in (
            captive_finance_activity,
            cyclical_exposure,
            major_business_change,
            capital_intensive_equity_route,
        )
    ):
        raise ValueError("preflight economic flags must be booleans")
    fact_count = _accession_fact_count(
        companyfacts, latest_eligible_accession, cutoff=valuation_date
    )
    direct = fact_count == 0
    equity = captive_finance_activity
    reset_cycle = cyclical_exposure and major_business_change
    actions = []
    if direct:
        actions.append("CAPTURE_EXACT_FILING_PACKAGE")
    if equity:
        actions.append("USE_EQUITY_LEVEL_CAPTIVE_FINANCE_ROUTE")
    if reset_cycle:
        actions.append("RESET_CYCLE_HISTORY_AND_REQUIRE_COMPARABLE_RANGE")
    if capital_intensive_equity_route:
        actions.append("RECONCILE_ALL_INTEREST_BEARING_BORROWING")
    return FutureBatchPreflight(
        current_accession_fact_count=fact_count,
        direct_filing_required=direct,
        equity_level_model_required=equity,
        cycle_history_reset_required=reset_cycle,
        complete_borrowing_required=capital_intensive_equity_route,
        required_actions=tuple(actions),
    )
