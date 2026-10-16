"""One-attempt recovery decisions for the six initially withheld Batch 02 issuers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .batch_02 import BATCH_02_MANIFEST
from .practical_policy import HARD_SAFETY_REASONS, PRACTICAL_REASON_CODES


RECOVERY_VERSION = "BATCH-02-RECOVERY-1.0"
RECOVERY_TICKERS = ("OMC", "TTWO", "CHTR", "CMCSA", "META", "WBD")
PUBLIC_METHOD_REFERENCES = (
    {
        "provider": "Alpha Spread",
        "url": "https://kb.alphaspread.com/hc/en-us/articles/18217888896017-What-is-DCF-Value",
        "adopted_public_practice": "Select the cash-flow model from company characteristics and use historical performance with a matching WACC or cost of equity.",
        "proprietary_formula_used": False,
    },
    {
        "provider": "GuruFocus",
        "url": "https://static.gurufocus.com/download/GuruFocus%20User%20Manual%20DCF%202022.pdf",
        "adopted_public_practice": "Keep the selected earnings or cash-flow measure consistent with its growth rate and warn when business predictability is weak.",
        "proprietary_formula_used": False,
    },
)


@dataclass(frozen=True)
class RecoveryDecision:
    ticker: str
    cik: str
    issuer_name: str
    recovery_model: str
    model_version: str
    final_outcome: str
    reason_codes: tuple[str, ...]
    hard_blockers: tuple[str, ...]
    verified_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    next_eligible_trigger: str
    conditional_event_diagnostic: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.final_outcome != "withheld":
            raise ValueError("Batch 02 recovery decisions must remain withheld")
        if not self.verified_evidence or not self.missing_evidence:
            raise ValueError("recovery evidence and missing evidence must be explicit")
        if any(reason not in PRACTICAL_REASON_CODES for reason in self.reason_codes):
            raise ValueError("unsupported practical recovery reason")
        if any(reason not in HARD_SAFETY_REASONS for reason in self.hard_blockers):
            raise ValueError("unsupported recovery hard blocker")


_ISSUER = {issuer.ticker: issuer for issuer in BATCH_02_MANIFEST}


def conditional_wbd_merger_consideration(close_date: str) -> float:
    """Return contractual cash consideration, not an intrinsic value."""

    closing = date.fromisoformat(close_date)
    threshold = date(2026, 9, 30)
    elapsed = max(0, (closing - threshold).days)
    return 31.0 + 0.00277778 * elapsed


def _decision(
    ticker: str,
    *,
    recovery_model: str,
    reason_codes: tuple[str, ...],
    hard_blockers: tuple[str, ...],
    verified_evidence: tuple[str, ...],
    missing_evidence: tuple[str, ...],
    next_eligible_trigger: str,
    conditional_event_diagnostic: dict[str, Any] | None = None,
) -> RecoveryDecision:
    issuer = _ISSUER[ticker]
    return RecoveryDecision(
        ticker=ticker,
        cik=issuer.cik,
        issuer_name=issuer.issuer_name,
        recovery_model=recovery_model,
        model_version=RECOVERY_VERSION,
        final_outcome="withheld",
        reason_codes=reason_codes,
        hard_blockers=hard_blockers,
        verified_evidence=verified_evidence,
        missing_evidence=missing_evidence,
        next_eligible_trigger=next_eligible_trigger,
        conditional_event_diagnostic=conditional_event_diagnostic,
    )


RECOVERY_DECISIONS = (
    _decision(
        "OMC",
        recovery_model="predecessor_combined_cash_fcff",
        reason_codes=("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"),
        hard_blockers=("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"),
        verified_evidence=(
            "The 2026 Q2 filing says IPG results enter only after the 2025-11-26 close.",
            "The issuer says post-close operating, financial-condition, and cash-flow periods are not comparable.",
            "H1 2026 integration/acquisition costs are reported, but no combined pro forma cash-flow history is filed.",
        ),
        missing_evidence=(
            "At least three aligned combined OMC-plus-IPG cash-flow periods or an issuer-filed combined pro forma cash-flow statement.",
        ),
        next_eligible_trigger="OMC files a full post-close annual period or comparable combined pro forma cash-flow history.",
    ),
    _decision(
        "TTWO",
        recovery_model="pipeline_aware_software_cash_fcff",
        reason_codes=("CAPEX_CASH_CONVERSION_SENSITIVITY", "SPECIALIST_MODEL_UNCERTAINTY"),
        hard_blockers=(
            "MAJOR_EVENT_UNBOUNDED",
            "MODEL_UNSUPPORTED",
            "NONFINITE_OR_NONPOSITIVE_VALUE",
        ),
        verified_evidence=(
            "GTA VI is scheduled for 2026-11-19 and pre-orders began in June 2026.",
            "The filing says release timing and commercial success of a few titles materially affect results.",
            "Current development assets, Q1 development cash, amortization, and impairment are reported.",
        ),
        missing_evidence=(
            "Issuer-supported release-period bookings/revenue or conversion range and at least one post-release cash observation.",
        ),
        next_eligible_trigger="TTWO reports a post-GTA-VI quarter plus release-period guidance or realized bookings/cash conversion.",
    ),
    _decision(
        "CHTR",
        recovery_model="transaction_conditioned_cable_fcff",
        reason_codes=("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"),
        hard_blockers=("MAJOR_EVENT_UNBOUNDED", "CLAIMS_UNBOUNDED"),
        verified_evidence=(
            "Cox terms include $4.15bn cash, $6bn convertible preferred, about 33.6m common units, and about $12.4bn assumed net debt/finance leases.",
            "The Liberty Broadband combination is also pending.",
        ),
        missing_evidence=(
            "Filed combined/pro forma Cox operating cash flow, capex, leverage, and final conversion dilution.",
        ),
        next_eligible_trigger="The Cox/Liberty transactions close with filed purchase accounting and pro forma cash information, or terminate.",
    ),
    _decision(
        "CMCSA",
        recovery_model="post_separation_two_company_sotp",
        reason_codes=("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"),
        hard_blockers=("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"),
        verified_evidence=(
            "The NBCUniversal/Sky separation is targeted for mid-2027 but remains conditional.",
            "Comcast may retain up to 19.9% for up to one year.",
            "The current statements do not give effect to the proposed separation.",
        ),
        missing_evidence=(
            "Filed standalone cash flows, debt/cash allocation, corporate-cost allocation, and final distribution/financing terms.",
        ),
        next_eligible_trigger="Comcast files Form 10/pro forma separation financials and the financing/distribution terms.",
    ),
    _decision(
        "META",
        recovery_model="commitment_aware_growth_fcff",
        reason_codes=("CAPEX_CASH_CONVERSION_SENSITIVITY", "SPECIALIST_MODEL_UNCERTAINTY"),
        hard_blockers=("CLAIMS_UNBOUNDED", "MODEL_UNSUPPORTED"),
        verified_evidence=(
            "$349.31bn non-cancelable commitments include $53.52bn due in 2026 and $81.65bn in 2027.",
            "$278.99bn uncommenced leases begin from 2026 through 2036, plus $68bn of July leases.",
            "$10.80bn restricted cash is tied to infrastructure purchase agreements.",
        ),
        missing_evidence=(
            "A mutually exclusive commitment waterfall mapping cloud, equipment, owned infrastructure, and leases to capex/OCF timing.",
        ),
        next_eligible_trigger="Meta files a commitment schedule that reconciles overlap and cash classification without double counting.",
    ),
    _decision(
        "WBD",
        recovery_model="standalone_plus_conditional_transaction_paths",
        reason_codes=("CONSOLIDATED_MODEL_FALLBACK", "SPECIALIST_MODEL_UNCERTAINTY"),
        hard_blockers=("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"),
        verified_evidence=(
            "The signed merger pays $31.00 cash per share plus $0.00277778 per day after 2026-09-30.",
            "Stockholders approved the agreement, but litigation and regulatory clearance can block closing.",
            "The agreement and alternative separation create materially different issuer states.",
        ),
        missing_evidence=(
            "A finite source-backed standalone/separation terminal state; no merger probability may be invented.",
        ),
        next_eligible_trigger="The merger closes, terminates, is amended, or a filed standalone/separation state becomes finite.",
        conditional_event_diagnostic={
            "output_type": "conditional_merger_cash_consideration_not_intrinsic_value",
            "if_closed_by_2026_09_30": 31.0,
            "daily_ticking_consideration_after_2026_09_30": 0.00277778,
            "illustrative_2027_06_04": conditional_wbd_merger_consideration(
                "2027-06-04"
            ),
            "published_as_intrinsic_value": False,
            "probability_weighted": False,
        },
    ),
)

if tuple(decision.ticker for decision in RECOVERY_DECISIONS) != RECOVERY_TICKERS:
    raise ValueError("Batch 02 recovery decisions do not match the fixed withheld set")


def recovery_decision(ticker: str) -> RecoveryDecision:
    return next(decision for decision in RECOVERY_DECISIONS if decision.ticker == ticker)
