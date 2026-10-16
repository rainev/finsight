"""Pure, source-aware building blocks for sustainable valuation inputs.

The functions in this module intentionally do not choose an issuer, model, or
market assumption.  They make a small set of mechanical transformations
safe for a future orchestrator:

* a reported value is retained alongside any bounded, source-backed
  adjustment;
* absent values are represented by ``None`` and are never silently changed to
  zero; and
* total reported capex is the default cash-flow input when it is available.

All result objects are frozen and expose JSON-serializable ``as_dict``
contracts.  No function mutates its arguments or performs I/O.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import math
from numbers import Real
import re
from typing import Any, Iterable


SUSTAINABLE_INPUTS_POLICY_VERSION = "US-SUSTAINABLE-INPUTS-1.0"


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{field} must be a finite number")
    return float(value)


def _nonnegative(value: object, field: str) -> float:
    result = _finite(value, field)
    if result < 0:
        raise ValueError(f"{field} must be nonnegative")
    return result


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value.strip()


def _iso_date(value: object, field: str) -> str:
    text = _text(value, field)
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error


def _cik(value: object) -> str:
    text = _text(value, "cik")
    if not re.fullmatch(r"\d{1,10}", text):
        raise ValueError("cik must contain one to ten digits")
    return text.zfill(10)


def validate_source_evidence(source: "SourceEvidence", frozen_cutoff: str) -> None:
    """Validate filing timing against the caller's immutable valuation cutoff."""

    if not isinstance(source, SourceEvidence):
        raise ValueError("source must be SourceEvidence")
    cutoff = _iso_date(frozen_cutoff, "frozen_cutoff")
    if source.filing_date > cutoff:
        raise ValueError("source filing_date is after the frozen cutoff")
    if source.reported_vs_estimated != "estimated" and source.period_end > cutoff:
        raise ValueError("source period_end is after the frozen cutoff")
    if source.period_start is not None and source.period_start > source.period_end:
        raise ValueError("source period_start cannot follow period_end")


def _reconcile_source_amount(source: SourceEvidence, value: float, field: str) -> None:
    if not math.isclose(abs(source.reported_value), abs(value), rel_tol=1e-12, abs_tol=1e-9):
        raise ValueError(f"{field} does not reconcile to source reported value")


@dataclass(frozen=True)
class SourceEvidence:
    """Minimal source lineage for a reported fact or adjustment."""

    source_id: str
    cik: str
    field: str
    unit: str
    reported_value: float
    period_end: str
    filing_date: str
    period_start: str | None = None
    locator: str | None = None
    reported_vs_estimated: str = "reported"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _text(self.source_id, "source_id"))
        object.__setattr__(self, "cik", _cik(self.cik))
        object.__setattr__(self, "field", _text(self.field, "field"))
        object.__setattr__(self, "unit", _text(self.unit, "unit"))
        object.__setattr__(self, "reported_value", _finite(self.reported_value, "reported_value"))
        object.__setattr__(self, "period_end", _iso_date(self.period_end, "period_end"))
        object.__setattr__(self, "filing_date", _iso_date(self.filing_date, "filing_date"))
        if self.period_start is not None:
            period_start = _iso_date(self.period_start, "period_start")
            if period_start > self.period_end:
                raise ValueError("period_start cannot follow period_end")
            object.__setattr__(self, "period_start", period_start)
        if self.filing_date < self.period_end and self.reported_vs_estimated != "estimated":
            raise ValueError("filing_date cannot precede source period_end")
        if self.locator is not None:
            object.__setattr__(self, "locator", _text(self.locator, "locator"))
        if self.reported_vs_estimated not in {"reported", "derived_reported", "estimated"}:
            raise ValueError("reported_vs_estimated is invalid")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BoundedAdjustment:
    """A signed, source-backed adjustment with explicit permitted bounds."""

    name: str
    amount: float
    source: SourceEvidence
    lower_bound: float | None = None
    upper_bound: float | None = None
    rationale: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "adjustment name"))
        amount = _finite(self.amount, "adjustment amount")
        lower = None if self.lower_bound is None else _finite(self.lower_bound, "lower_bound")
        upper = None if self.upper_bound is None else _finite(self.upper_bound, "upper_bound")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("adjustment bounds must be ordered")
        if lower is not None and amount < lower:
            raise ValueError("adjustment amount is below its lower bound")
        if upper is not None and amount > upper:
            raise ValueError("adjustment amount is above its upper bound")
        if not isinstance(self.source, SourceEvidence):
            raise ValueError("adjustment source must be SourceEvidence")
        if not math.isclose(abs(amount), abs(self.source.reported_value), rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("adjustment amount must reconcile to the source reported value")
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "lower_bound", lower)
        object.__setattr__(self, "upper_bound", upper)
        object.__setattr__(self, "rationale", self.rationale.strip() if isinstance(self.rationale, str) else "")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "amount": self.amount,
            "source": self.source.as_dict(),
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class NormalizedInput:
    """Reported input plus explicit adjustments; never just the adjusted value."""

    field: str
    reported_value: float
    adjustment_total: float
    normalized_value: float
    adjustments: tuple[BoundedAdjustment, ...]
    formula: str
    frozen_cutoff: str
    reported_preserved: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "field", _text(self.field, "field"))
        reported = _finite(self.reported_value, "reported_value")
        total = _finite(self.adjustment_total, "adjustment_total")
        normalized = _finite(self.normalized_value, "normalized_value")
        if not math.isclose(normalized, reported + total, rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("normalized value does not reconcile to reported value plus adjustments")
        if not self.adjustments and not math.isclose(total, 0.0, abs_tol=1e-12):
            raise ValueError("adjustment total requires adjustment rows")
        if self.adjustments and not math.isclose(total, sum(item.amount for item in self.adjustments), rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("adjustment total does not reconcile to adjustment rows")
        object.__setattr__(self, "reported_value", reported)
        object.__setattr__(self, "adjustment_total", total)
        object.__setattr__(self, "normalized_value", normalized)
        object.__setattr__(self, "adjustments", tuple(self.adjustments))
        object.__setattr__(self, "formula", _text(self.formula, "formula"))
        cutoff = _iso_date(self.frozen_cutoff, "frozen_cutoff")
        for adjustment in self.adjustments:
            validate_source_evidence(adjustment.source, cutoff)
        object.__setattr__(self, "frozen_cutoff", cutoff)
        if self.reported_preserved is not True:
            raise ValueError("reported_preserved must remain true")

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_version": SUSTAINABLE_INPUTS_POLICY_VERSION,
            "field": self.field,
            "reported_value": self.reported_value,
            "adjustment_total": self.adjustment_total,
            "normalized_value": self.normalized_value,
            "adjustments": [item.as_dict() for item in self.adjustments],
            "formula": self.formula,
            "frozen_cutoff": self.frozen_cutoff,
            "reported_preserved": self.reported_preserved,
        }


def normalize_reported_value(
    reported_value: float,
    adjustments: Iterable[BoundedAdjustment] = (),
    *,
    field: str = "value",
    frozen_cutoff: str,
) -> NormalizedInput:
    """Apply bounded adjustments while preserving the original reported value."""

    reported = _finite(reported_value, "reported_value")
    rows = tuple(adjustments)
    if any(not isinstance(row, BoundedAdjustment) for row in rows):
        raise ValueError("adjustments must contain BoundedAdjustment rows")
    total = sum(row.amount for row in rows)
    return NormalizedInput(
        field=field,
        reported_value=reported,
        adjustment_total=total,
        normalized_value=reported + total,
        adjustments=rows,
        formula="reported_value + sum(source_backed_bounded_adjustments)",
        frozen_cutoff=frozen_cutoff,
    )


# A short name is useful to callers composing an input pipeline.
normalize_value = normalize_reported_value
SourceBackedAdjustment = BoundedAdjustment
NormalizationResult = NormalizedInput


@dataclass(frozen=True)
class CapexResolution:
    """Capex input with an explicit total-first/default treatment."""

    effective_total_capex: float
    reported_total_capex: float | None
    maintenance_capex: float | None
    growth_capex: float | None
    basis: str
    component_difference: float | None
    components_reconciled: bool | None

    def __post_init__(self) -> None:
        total = _nonnegative(self.effective_total_capex, "effective_total_capex")
        reported = None if self.reported_total_capex is None else _nonnegative(self.reported_total_capex, "reported_total_capex")
        maintenance = None if self.maintenance_capex is None else _nonnegative(self.maintenance_capex, "maintenance_capex")
        growth = None if self.growth_capex is None else _nonnegative(self.growth_capex, "growth_capex")
        if self.basis not in {"reported_total_capex", "reported_components"}:
            raise ValueError("capex basis is invalid")
        if reported is not None and self.basis != "reported_total_capex":
            raise ValueError("reported total capex must use total-capex basis")
        if reported is None and self.basis != "reported_components":
            raise ValueError("component fallback requires reported-components basis")
        difference = None if self.component_difference is None else _finite(self.component_difference, "component_difference")
        if self.components_reconciled is not None and not isinstance(self.components_reconciled, bool):
            raise ValueError("components_reconciled must be boolean or None")
        object.__setattr__(self, "effective_total_capex", total)
        object.__setattr__(self, "reported_total_capex", reported)
        object.__setattr__(self, "maintenance_capex", maintenance)
        object.__setattr__(self, "growth_capex", growth)
        object.__setattr__(self, "component_difference", difference)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_total_capex(
    reported_total_capex: float | None,
    *,
    maintenance_capex: float | None = None,
    growth_capex: float | None = None,
    tolerance: float = 1e-9,
    total_source: SourceEvidence | None = None,
    maintenance_source: SourceEvidence | None = None,
    growth_source: SourceEvidence | None = None,
    frozen_cutoff: str,
) -> CapexResolution:
    """Use reported total capex by default; require both components for fallback.

    When a reported total exists, component values are diagnostic only and are
    never added on top of the total.  If the total is absent, treating one
    missing component as zero would manufacture a cash-flow input, so both
    components are required.
    """

    tol = _nonnegative(tolerance, "tolerance")
    cutoff = _iso_date(frozen_cutoff, "frozen_cutoff")
    if reported_total_capex is not None and total_source is None:
        raise ValueError("reported total capex requires source evidence")
    if maintenance_capex is not None and maintenance_source is None:
        raise ValueError("maintenance capex requires source evidence")
    if growth_capex is not None and growth_source is None:
        raise ValueError("growth capex requires source evidence")
    for source in (total_source, maintenance_source, growth_source):
        if source is not None:
            validate_source_evidence(source, cutoff)
    if reported_total_capex is not None:
        _reconcile_source_amount(total_source, reported_total_capex, "reported total capex")
    if maintenance_capex is not None:
        _reconcile_source_amount(maintenance_source, maintenance_capex, "maintenance capex")
    if growth_capex is not None:
        _reconcile_source_amount(growth_source, growth_capex, "growth capex")
    if reported_total_capex is not None:
        total = _nonnegative(reported_total_capex, "reported_total_capex")
        difference = None
        reconciled = None
        if maintenance_capex is not None and growth_capex is not None:
            components = _nonnegative(maintenance_capex, "maintenance_capex") + _nonnegative(growth_capex, "growth_capex")
            difference = components - total
            reconciled = math.isclose(components, total, rel_tol=tol, abs_tol=tol)
        return CapexResolution(
            effective_total_capex=total,
            reported_total_capex=total,
            maintenance_capex=None if maintenance_capex is None else _nonnegative(maintenance_capex, "maintenance_capex"),
            growth_capex=None if growth_capex is None else _nonnegative(growth_capex, "growth_capex"),
            basis="reported_total_capex",
            component_difference=difference,
            components_reconciled=reconciled,
        )
    if maintenance_capex is None or growth_capex is None:
        raise ValueError("reported total capex is absent; both maintenance and growth capex are required")
    maintenance = _nonnegative(maintenance_capex, "maintenance_capex")
    growth = _nonnegative(growth_capex, "growth_capex")
    return CapexResolution(
        effective_total_capex=maintenance + growth,
        reported_total_capex=None,
        maintenance_capex=maintenance,
        growth_capex=growth,
        basis="reported_components",
        component_difference=0.0,
        components_reconciled=True,
    )


resolve_capex = resolve_total_capex
CapitalExpenditureResolution = CapexResolution


@dataclass(frozen=True)
class TimedCommitment:
    """A nonnegative commitment occupying an inclusive fiscal-year interval."""

    commitment_id: str
    amount: float
    start_year: int
    source: SourceEvidence
    end_year: int | None = None
    coverage_key: str = "default"

    def __post_init__(self) -> None:
        object.__setattr__(self, "commitment_id", _text(self.commitment_id, "commitment_id"))
        object.__setattr__(self, "amount", _nonnegative(self.amount, "commitment amount"))
        if isinstance(self.start_year, bool) or not isinstance(self.start_year, int) or self.start_year < 0:
            raise ValueError("start_year must be a nonnegative integer")
        end = self.start_year if self.end_year is None else self.end_year
        if isinstance(end, bool) or not isinstance(end, int):
            raise ValueError("end_year must be an integer")
        if end < self.start_year:
            raise ValueError("commitment end_year must not precede start_year")
        object.__setattr__(self, "end_year", end)
        object.__setattr__(self, "coverage_key", _text(self.coverage_key, "coverage_key"))
        if not isinstance(self.source, SourceEvidence):
            raise ValueError("commitment source must be SourceEvidence")
        _reconcile_source_amount(self.source, self.amount, "commitment amount")

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["source"] = self.source.as_dict()
        return result


@dataclass(frozen=True)
class CommitmentOverlap:
    left_id: str
    right_id: str
    coverage_key: str
    overlap_start_year: int
    overlap_end_year: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommitmentOverlapCheck:
    status: str
    commitments: tuple[TimedCommitment, ...]
    overlaps: tuple[CommitmentOverlap, ...]
    total_by_year: dict[int, float]

    def __post_init__(self) -> None:
        if self.status not in {"pass", "overlap_found"}:
            raise ValueError("commitment overlap status is invalid")
        if self.status == "pass" and self.overlaps:
            raise ValueError("pass cannot contain overlaps")

    @property
    def is_non_overlapping(self) -> bool:
        return self.status == "pass"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "commitments": [row.as_dict() for row in self.commitments],
            "overlaps": [row.as_dict() for row in self.overlaps],
            "total_by_year": {str(year): value for year, value in self.total_by_year.items()},
            "is_non_overlapping": self.is_non_overlapping,
        }


def check_timed_commitment_overlap(
    commitments: Iterable[TimedCommitment],
    *,
    frozen_cutoff: str,
) -> CommitmentOverlapCheck:
    """Find same-coverage commitments whose fiscal-year intervals overlap."""

    rows = tuple(commitments)
    if any(not isinstance(row, TimedCommitment) for row in rows):
        raise ValueError("commitments must contain TimedCommitment rows")
    cutoff = _iso_date(frozen_cutoff, "frozen_cutoff")
    for row in rows:
        validate_source_evidence(row.source, cutoff)
    ids = [row.commitment_id for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("commitment_id values must be unique")
    overlaps: list[CommitmentOverlap] = []
    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            if left.coverage_key != right.coverage_key:
                continue
            start = max(left.start_year, right.start_year)
            end = min(left.end_year, right.end_year)
            if start <= end:
                overlaps.append(
                    CommitmentOverlap(left.commitment_id, right.commitment_id, left.coverage_key, start, end)
                )
    totals: dict[int, float] = {}
    for row in rows:
        for year in range(row.start_year, row.end_year + 1):
            totals[year] = totals.get(year, 0.0) + row.amount / (row.end_year - row.start_year + 1)
    return CommitmentOverlapCheck(
        status="overlap_found" if overlaps else "pass",
        commitments=rows,
        overlaps=tuple(overlaps),
        total_by_year=dict(sorted(totals.items())),
    )


validate_timed_commitments = check_timed_commitment_overlap
check_commitment_overlap = check_timed_commitment_overlap
Commitment = TimedCommitment


def assert_non_overlapping_commitments(
    commitments: Iterable[TimedCommitment],
    *,
    frozen_cutoff: str,
) -> CommitmentOverlapCheck:
    """Return the check or fail closed when a schedule double-counts coverage."""

    result = check_timed_commitment_overlap(commitments, frozen_cutoff=frozen_cutoff)
    if not result.is_non_overlapping:
        pairs = ", ".join(f"{row.left_id}/{row.right_id}" for row in result.overlaps)
        raise ValueError(f"timed commitment schedule contains overlapping coverage: {pairs}")
    return result


@dataclass(frozen=True)
class TimedPayment:
    """One explicit finite future payment used for commitment PV."""

    payment_id: str
    payment_year: int
    amount: float
    coverage_key: str
    source: SourceEvidence

    def __post_init__(self) -> None:
        object.__setattr__(self, "payment_id", _text(self.payment_id, "payment_id"))
        if isinstance(self.payment_year, bool) or not isinstance(self.payment_year, int):
            raise ValueError("payment_year must be an integer")
        object.__setattr__(self, "amount", _nonnegative(self.amount, "payment amount"))
        object.__setattr__(self, "coverage_key", _text(self.coverage_key, "coverage_key"))
        if not isinstance(self.source, SourceEvidence):
            raise ValueError("payment source must be SourceEvidence")
        _reconcile_source_amount(self.source, self.amount, "payment amount")

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "source": self.source.as_dict()}


@dataclass(frozen=True)
class TimedPaymentPv:
    payment_id: str
    payment_year: int
    amount: float
    discount_factor: float
    present_value: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommitmentPvResult:
    status: str
    valuation_year: int
    discount_rate: float
    frozen_cutoff: str
    payments: tuple[TimedPaymentPv, ...]
    present_value: float
    overlap_check: CommitmentOverlapCheck

    def __post_init__(self) -> None:
        if self.status != "pass":
            raise ValueError("commitment PV status must be pass")
        if isinstance(self.valuation_year, bool) or not isinstance(self.valuation_year, int) or self.valuation_year < 0:
            raise ValueError("valuation_year must be a nonnegative integer")
        _finite(self.discount_rate, "discount_rate")
        if self.discount_rate < 0:
            raise ValueError("discount_rate must be nonnegative")
        _finite(self.present_value, "present_value")
        if self.present_value < 0:
            raise ValueError("present_value must be nonnegative")

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_version": SUSTAINABLE_INPUTS_POLICY_VERSION,
            "status": self.status,
            "valuation_year": self.valuation_year,
            "discount_rate": self.discount_rate,
            "frozen_cutoff": self.frozen_cutoff,
            "payments": [row.as_dict() for row in self.payments],
            "present_value": self.present_value,
            "overlap_check": self.overlap_check.as_dict(),
        }


def evaluate_timed_payment_pv(
    payments: Iterable[TimedPayment],
    *,
    valuation_year: int,
    discount_rate: float,
    frozen_cutoff: str,
) -> CommitmentPvResult:
    """Discount a complete finite payment schedule; no perpetual tail is inferred."""

    if isinstance(valuation_year, bool) or not isinstance(valuation_year, int) or valuation_year < 0:
        raise ValueError("valuation_year must be a nonnegative integer")
    rate = _finite(discount_rate, "discount_rate")
    if rate < 0:
        raise ValueError("discount_rate must be nonnegative")
    cutoff = _iso_date(frozen_cutoff, "frozen_cutoff")
    rows = tuple(payments)
    if not rows:
        raise ValueError("complete payment schedule cannot be empty")
    if any(not isinstance(row, TimedPayment) for row in rows):
        raise ValueError("payments must contain TimedPayment rows")
    for row in rows:
        if row.payment_year <= valuation_year:
            raise ValueError("payment schedule must contain only future payment years")
        validate_source_evidence(row.source, cutoff)
    ids = [row.payment_id for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("payment_id values must be unique")
    # Treat each payment as a one-year coverage interval so same-scope
    # duplicate claims cannot be discounted twice.
    overlap_rows = tuple(
        TimedCommitment(
            row.payment_id,
            row.amount,
            row.payment_year,
            row.source,
            row.payment_year,
            row.coverage_key,
        )
        for row in rows
    )
    overlap = check_timed_commitment_overlap(overlap_rows, frozen_cutoff=cutoff)
    if not overlap.is_non_overlapping:
        raise ValueError("timed payment schedule contains overlapping coverage")
    traces = tuple(
        TimedPaymentPv(
            payment_id=row.payment_id,
            payment_year=row.payment_year,
            amount=row.amount,
            discount_factor=(1.0 + rate) ** (row.payment_year - valuation_year),
            present_value=row.amount / (1.0 + rate) ** (row.payment_year - valuation_year),
        )
        for row in rows
    )
    return CommitmentPvResult(
        status="pass",
        valuation_year=valuation_year,
        discount_rate=rate,
        frozen_cutoff=cutoff,
        payments=traces,
        present_value=sum(row.present_value for row in traces),
        overlap_check=overlap,
    )


present_value_timed_commitments = evaluate_timed_payment_pv
evaluate_commitment_pv = evaluate_timed_payment_pv


__all__ = [
    "SUSTAINABLE_INPUTS_POLICY_VERSION",
    "SourceEvidence",
    "validate_source_evidence",
    "BoundedAdjustment",
    "NormalizedInput",
    "NormalizationResult",
    "SourceBackedAdjustment",
    "normalize_reported_value",
    "normalize_value",
    "CapexResolution",
    "CapitalExpenditureResolution",
    "resolve_total_capex",
    "resolve_capex",
    "TimedCommitment",
    "CommitmentOverlap",
    "CommitmentOverlapCheck",
    "check_timed_commitment_overlap",
    "validate_timed_commitments",
    "check_commitment_overlap",
    "Commitment",
    "assert_non_overlapping_commitments",
    "TimedPayment",
    "TimedPaymentPv",
    "CommitmentPvResult",
    "evaluate_timed_payment_pv",
    "present_value_timed_commitments",
    "evaluate_commitment_pv",
]
