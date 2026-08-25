"""Governed release-condition decisions for the Batch 02 pipeline-revision retry."""

from __future__ import annotations

from dataclasses import dataclass

from .batch_02_recovery import RECOVERY_TICKERS


REVISION_RETRY_VERSION = "BATCH-02-PIPELINE-REVISION-RETRY-1.0"


@dataclass(frozen=True)
class RevisionRetryDecision:
    ticker: str
    prior_blocker_cleared: bool
    evidence_improvement: str
    remaining_release_condition: str
    decision_reason: str

    def __post_init__(self) -> None:
        if self.prior_blocker_cleared:
            raise ValueError("no Batch 02 release condition is cleared by this revision")
        if not all(
            text.strip()
            for text in (
                self.evidence_improvement,
                self.remaining_release_condition,
                self.decision_reason,
            )
        ):
            raise ValueError("revision-retry explanations must be explicit")


REVISION_RETRY_DECISIONS = (
    RevisionRetryDecision(
        ticker="OMC",
        prior_blocker_cleared=False,
        evidence_improvement="Current cash, debt, noncontrolling interest, and a bounded finance-lease aggregate are now governed evidence.",
        remaining_release_condition="Comparable combined OMC-plus-IPG owner-cash history or issuer-filed combined pro forma cash flow.",
        decision_reason="Balance-sheet extraction does not create a normalized post-merger cash-flow history.",
    ),
    RevisionRetryDecision(
        ticker="TTWO",
        prior_blocker_cleared=False,
        evidence_improvement="Current cash, debt, and marketable securities are now governed evidence.",
        remaining_release_condition="A source-backed release-period conversion range and at least one post-GTA-VI cash observation.",
        decision_reason="The revised evidence does not bound release success or turn nonpositive normalized cash flow into a defensible owner-cash range.",
    ),
    RevisionRetryDecision(
        ticker="CHTR",
        prior_blocker_cleared=False,
        evidence_improvement="Current cash, debt, noncontrolling interest, and reported preferred-equity zero are now governed evidence.",
        remaining_release_condition="Combined Cox/Liberty operating cash, final leverage, conversion dilution, and a complete claims state.",
        decision_reason="Current standalone claims do not bound the pending combined-company economics and dilution.",
    ),
    RevisionRetryDecision(
        ticker="CMCSA",
        prior_blocker_cleared=False,
        evidence_improvement="Current cash, current debt, securities, noncontrolling interest, and reported preferred-equity zero are now governed evidence.",
        remaining_release_condition="Standalone post-separation cash flows, corporate-cost allocation, and final debt/cash/financing allocation.",
        decision_reason="Consolidated balance-sheet facts cannot determine the two future companies' owner cash and capital allocation.",
    ),
    RevisionRetryDecision(
        ticker="META",
        prior_blocker_cleared=False,
        evidence_improvement="Cash, securities, debt, and bounded finance-lease ranges are now governed evidence.",
        remaining_release_condition="A mutually exclusive cash waterfall for commitments, uncommenced leases, and capital spending.",
        decision_reason="Lease bounds do not resolve overlap among the much larger commitment and capex schedules, so a valuation could omit or double-count cash outflows.",
    ),
    RevisionRetryDecision(
        ticker="WBD",
        prior_blocker_cleared=False,
        evidence_improvement="Current cash, debt, noncontrolling interest, reported preferred-equity zero, and bounded finance-lease ranges are now governed evidence.",
        remaining_release_condition="A finite standalone/separation terminal state or a completed/terminated transaction state.",
        decision_reason="Conditional merger consideration remains a contract payoff, not a source-backed intrinsic value, and no transaction probability may be invented.",
    ),
)

if tuple(row.ticker for row in REVISION_RETRY_DECISIONS) != RECOVERY_TICKERS:
    raise ValueError("revision retry decisions must match the exact Batch 02 recovery set")

