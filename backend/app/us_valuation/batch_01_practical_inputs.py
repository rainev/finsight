"""Source-linked practical policy inputs for controlled Batch 01."""

from __future__ import annotations

from typing import Any, Mapping

from .field_availability import FieldAvailability
from .practical_bridge import bounded_claim, reported_aggregate


def _instant(
    companyfacts: Mapping[str, Any],
    *,
    concept: str,
    period_end: str,
    accession: str,
) -> tuple[float, str]:
    payload = (
        companyfacts.get("facts", {})
        .get("us-gaap", {})
        .get(concept, {})
    )
    matches = []
    for row in payload.get("units", {}).get("USD", []):
        if (
            row.get("end") == period_end
            and row.get("accn") == accession
            and row.get("filed", "") <= "2026-08-14"
            and row.get("form") in {"10-K", "10-K/A", "10-Q", "10-Q/A"}
            and isinstance(row.get("val"), (int, float))
            and not isinstance(row.get("val"), bool)
        ):
            matches.append(row)
    values = {float(row["val"]) for row in matches}
    if len(values) != 1:
        raise ValueError(
            f"{concept} must have one exact same-accession instant value"
        )
    frame = next(
        (row.get("frame") for row in matches if row.get("frame")),
        "undimensioned",
    )
    return values.pop(), str(frame)


def practical_bridge_evidence(
    *,
    ticker: str,
    companyfacts: Mapping[str, Any],
) -> tuple[FieldAvailability, ...]:
    """Build only the two approved source-derived practical bridge packets."""

    if ticker == "AAPL":
        accession = "0000320193-26-000020"
        period = "2026-06-27"
        equity, frame = _instant(
            companyfacts,
            concept="StockholdersEquity",
            period_end=period,
            accession=accession,
        )
        # The two fields are an arithmetic representation of one joint maximum.
        # Their combined high endpoint equals reported total equity, never 2x it.
        per_field_upper = equity / 2.0
        basis = (
            "Joint preferred-equity plus NCI maximum is capped by same-filing "
            f"reported stockholders' equity of {equity:.0f}; equal field "
            "allocation is presentation-only and the combined bound is controlling."
        )
        return tuple(
            bounded_claim(
                field=field,
                upper_bound=per_field_upper,
                source_accession=accession,
                period_end=period,
                source_concept="us-gaap:StockholdersEquity",
                context_id=frame,
                basis=basis,
            )
            for field in ("preferred_equity", "noncontrolling_interests")
        )
    if ticker == "ANET":
        accession = "0001596532-26-000175"
        period = "2026-06-30"
        securities, securities_frame = _instant(
            companyfacts,
            concept="AvailableForSaleSecuritiesDebtSecurities",
            period_end=period,
            accession=accession,
        )
        current_securities, _ = _instant(
            companyfacts,
            concept="AvailableForSaleSecuritiesDebtSecuritiesCurrent",
            period_end=period,
            accession=accession,
        )
        if securities != current_securities:
            raise ValueError("ANET current securities do not reconcile to reported total")
        liabilities, liabilities_frame = _instant(
            companyfacts,
            concept="Liabilities",
            period_end=period,
            accession=accession,
        )
        equity, equity_frame = _instant(
            companyfacts,
            concept="StockholdersEquity",
            period_end=period,
            accession=accession,
        )
        return (
            reported_aggregate(
                field="marketable_securities_total",
                low=securities,
                high=securities,
                source_accession=accession,
                period_end=period,
                source_concept="us-gaap:AvailableForSaleSecuritiesDebtSecurities",
                context_id=securities_frame,
                covered_fields=(
                    "marketable_securities_current",
                    "marketable_securities_noncurrent",
                ),
                economic_scope="marketable_securities_current_and_noncurrent",
                basis="Reported total equals the same-filing current classification.",
            ),
            reported_aggregate(
                field="total_interest_bearing_debt",
                low=0.0,
                high=liabilities,
                source_accession=accession,
                period_end=period,
                source_concept="us-gaap:Liabilities",
                context_id=liabilities_frame,
                covered_fields=(
                    "commercial_paper",
                    "current_debt",
                    "noncurrent_debt",
                    "finance_lease_current",
                    "finance_lease_noncurrent",
                ),
                economic_scope="all_interest_bearing_debt_and_finance_leases",
                basis=(
                    "Missing financing claims are bounded between zero and "
                    "same-filing total liabilities; operating liabilities make "
                    "the high endpoint deliberately conservative."
                ),
            ),
            bounded_claim(
                field="noncontrolling_interests",
                upper_bound=equity,
                source_accession=accession,
                period_end=period,
                source_concept="us-gaap:StockholdersEquity",
                context_id=equity_frame,
                basis=(
                    "NCI is bounded between zero and same-filing stockholders' "
                    "equity; the upper endpoint is deliberately conservative."
                ),
            ),
        )
    return ()
