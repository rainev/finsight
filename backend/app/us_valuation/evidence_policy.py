"""Official-source exhaustion order and private availability projection."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any, Mapping, Sequence

from .field_availability import FieldAvailability, UncertaintyRange
from .official_evidence import EvidenceDecision


_ORDER = {
    "companyfacts_current": 1,
    "exact_sec_filing": 2,
    "filing_table": 3,
    "regulator_or_sec_supplement": 4,
    "current_aggregate": 5,
    "annual_carry_forward": 6,
    "company_history": 7,
    "sector_range": 8,
}
_CAP = {
    "companyfacts_current": "High",
    "exact_sec_filing": "High",
    "filing_table": "High",
    "regulator_or_sec_supplement": "High",
    "current_aggregate": "Medium",
    "annual_carry_forward": "Medium",
    "company_history": "Low",
    "sector_range": "Low",
}


@dataclass(frozen=True)
class SourceAttempt:
    source: str
    status: str
    value: float | None
    low: float | None
    high: float | None
    eligible: bool
    accession: str
    period_end: str
    reason_codes: tuple[str, ...]
    source_kind: str | None = None
    filed_date: str | None = None
    source_age_days: int | None = None
    covered_fields: tuple[str, ...] = ()
    coverage_basis: str | None = None
    coverage_source_facts: tuple[str, ...] = ()
    economic_scope: str | None = None
    source_url: str | None = None
    unit: str | None = None
    entity_identifier: str | None = None
    consolidation_scope: str | None = None
    candidate_id: str | None = None
    package_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.source not in _ORDER:
            raise ValueError("unsupported evidence source tier")
        if not isinstance(self.eligible, bool) or not self.accession or not self.period_end:
            raise ValueError("source attempt identity is incomplete")
        if not self.reason_codes:
            raise ValueError("source attempt needs reason codes")
        for value, name in ((self.value, "value"), (self.low, "low"), (self.high, "high")):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value))
            ):
                raise ValueError(f"source attempt {name} must be finite")
        if self.status == "bounded_estimate":
            if self.low is None or self.high is None or self.low > self.high or self.value is not None:
                raise ValueError("bounded source attempt needs an ordered range only")
        elif self.status in {"reported", "reported_aggregate", "explicit_zero"}:
            if self.value is None or self.low is not None or self.high is not None:
                raise ValueError("reported source attempt needs one point value")
            if self.status == "explicit_zero" and self.value != 0:
                raise ValueError("explicit_zero needs zero")
        elif self.status == "stale":
            if self.value is None or self.low is not None or self.high is not None:
                raise ValueError("stale source attempt preserves one diagnostic point")
        elif self.value is not None or self.low is not None or self.high is not None:
            raise ValueError("nonpoint source attempt cannot carry a value")
        if self.eligible and self.source in {
            "companyfacts_current", "exact_sec_filing", "filing_table",
            "regulator_or_sec_supplement", "current_aggregate",
        } and self.source_kind is not None:
            if (
                not self.filed_date
                or not self.source_url
                or not self.unit
                or not self.entity_identifier
                or self.consolidation_scope != "consolidated_parent"
            ):
                raise ValueError("eligible current evidence needs cutoff, source, unit, identity, and consolidation proof")
        if self.eligible and self.source == "filing_table" and not self.package_sha256:
            raise ValueError("eligible filing-table evidence needs an immutable package hash")


@dataclass(frozen=True)
class EvidenceExhaustionReceipt:
    attempts: tuple[SourceAttempt, ...]
    exhausted: bool
    selected_source: str | None
    blocker_reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class PolicyDecision:
    request: dict[str, Any]
    status: str
    selected: SourceAttempt | None
    selected_range: tuple[float, float] | None
    reason_codes: tuple[str, ...]
    exhaustion_receipt: EvidenceExhaustionReceipt
    reliability_cap: str | None


def _request(value: Mapping[str, Any]) -> dict[str, Any]:
    field = value.get("required_field")
    model = value.get("model")
    valuation_date = value.get("valuation_date")
    if not all(isinstance(item, str) and item for item in (field, model, valuation_date)):
        raise ValueError("evidence request needs field, model, and valuation date")
    return dict(value)


def resolve_evidence_order(
    request: Mapping[str, Any], attempts: Sequence[SourceAttempt]
) -> PolicyDecision:
    request_value = _request(request)
    ordered = tuple(sorted(attempts, key=lambda item: (_ORDER[item.source], item.accession)))
    declared_sources = request_value.get("applicable_sources")
    applicable_sources = (
        set(declared_sources)
        if isinstance(declared_sources, (list, tuple))
        else {item.source for item in ordered}
    )
    if not applicable_sources.issubset(_ORDER):
        raise ValueError("request declares unsupported applicable sources")
    exhausted = bool(applicable_sources) and applicable_sources.issubset(
        {item.source for item in ordered}
    )
    blockers = tuple(
        code
        for attempt in ordered
        if not attempt.eligible or attempt.status in {"unresolved", "stale", "conflicting"}
        for code in attempt.reason_codes
    )
    if request_value.get("model_suitable", True) is not True:
        receipt = EvidenceExhaustionReceipt(ordered, exhausted, None, blockers)
        return PolicyDecision(
            request_value, "unresolved", None, None,
            ("UNSUITABLE_MODEL",), receipt, None,
        )

    current_values = tuple(
        item
        for item in ordered
        if item.source in {"companyfacts_current", "exact_sec_filing", "filing_table"}
        and item.eligible
        and item.status in {"reported", "explicit_zero"}
    )
    comparable_groups: dict[tuple[str, str], set[float]] = {}
    for item in current_values:
        comparable_groups.setdefault((item.accession, item.period_end), set()).add(float(item.value))
    if any(len(values) > 1 for values in comparable_groups.values()):
        receipt = EvidenceExhaustionReceipt(ordered, exhausted, None, blockers)
        return PolicyDecision(
            request_value, "conflicting", None, None,
            ("CURRENT_OFFICIAL_VALUES_CONFLICT",), receipt, None,
        )

    for source in sorted(_ORDER, key=_ORDER.get):
        same_tier = tuple(item for item in ordered if item.source == source)
        if any(item.status == "conflicting" for item in same_tier):
            receipt = EvidenceExhaustionReceipt(ordered, exhausted, None, blockers)
            return PolicyDecision(
                request_value, "conflicting", None, None,
                ("OFFICIAL_SOURCE_CONFLICT",), receipt, None,
            )
        eligible = tuple(
            item
            for item in same_tier
            if item.eligible
            and item.status in {"reported", "reported_aggregate", "explicit_zero", "bounded_estimate"}
        )
        if source == "annual_carry_forward":
            expired = tuple(
                item
                for item in eligible
                if item.status == "stale"
                or (item.source_age_days is not None and item.source_age_days > 365)
            )
            if expired:
                eligible = tuple(item for item in eligible if item not in expired)
        identities = {
            (
                "point" if item.status in {"reported", "explicit_zero"} else item.status,
                item.value,
                item.low,
                item.high,
            )
            for item in eligible
        }
        if len(identities) > 1:
            receipt = EvidenceExhaustionReceipt(ordered, exhausted, None, blockers)
            return PolicyDecision(
                request_value, "conflicting", None, None,
                ("SAME_TIER_OFFICIAL_VALUES_CONFLICT",), receipt, None,
            )
        if eligible:
            selected = eligible[0]
            range_value = (
                (float(selected.low), float(selected.high))
                if selected.status == "bounded_estimate"
                else None
            )
            reasons = selected.reason_codes
            if source != "annual_carry_forward" and any(
                item.source == "annual_carry_forward" and item.status == "stale"
                for item in ordered
            ):
                reasons = ("ANNUAL_CARRY_FORWARD_EXPIRED",) + reasons
            receipt = EvidenceExhaustionReceipt(ordered, exhausted, source, blockers)
            return PolicyDecision(
                request_value,
                selected.status,
                selected,
                range_value,
                reasons,
                receipt,
                "Low" if range_value is not None else _CAP[source],
            )

    specialist_unproven = any(
        item.source == "regulator_or_sec_supplement" and not item.eligible
        for item in ordered
    )
    reasons = (
        ("SPECIALIST_IDENTITY_OR_CONSOLIDATION_UNPROVEN",)
        if specialist_unproven
        else ("OFFICIAL_SOURCES_EXHAUSTED_NO_USABLE_VALUE",)
        if exhausted
        else ("APPLICABLE_OFFICIAL_SOURCES_NOT_EXHAUSTED",)
    )
    receipt = EvidenceExhaustionReceipt(ordered, exhausted, None, blockers)
    return PolicyDecision(request_value, "unresolved", None, None, reasons, receipt, None)


@dataclass(frozen=True)
class EvidenceAvailability:
    availability: FieldAvailability
    reliability_cap: str

    @property
    def state(self) -> str:
        return self.availability.state

    @property
    def uncertainty(self) -> UncertaintyRange | None:
        return self.availability.uncertainty

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.availability.as_dict(),
            "reliability_cap": self.reliability_cap,
        }


def project_decision_to_availability(
    decision: PolicyDecision,
    *,
    fallback_level: str,
    source_attempt: SourceAttempt | None,
) -> EvidenceAvailability:
    if source_attempt is None or decision.selected is None:
        raise ValueError("only a selected policy decision can project")
    if source_attempt != decision.selected:
        raise ValueError("source attempt does not match the policy selection")
    field = decision.request["required_field"]
    valuation_date = decision.request["valuation_date"]
    if decision.status == "bounded_estimate" and decision.selected_range is not None:
        low, high = decision.selected_range
        if fallback_level == "annual_carried_forward":
            availability = FieldAvailability(
                field=field,
                value=None,
                state="bounded_unresolved",
                reason_code=decision.reason_codes[0],
                period_end=source_attempt.period_end,
                source_accession=source_attempt.accession,
                source_kind="companyfacts",
                evidence_class="bounded_estimate",
                freshness="carried_forward",
                fallback_level="annual_carried_forward",
                source_age_days=source_attempt.source_age_days,
                uncertainty=UncertaintyRange(
                    low=low,
                    high=high,
                    basis="annual Companyfacts source-backed range",
                    source_accessions=(source_attempt.accession,),
                ),
                authority="production",
            )
            return EvidenceAvailability(availability, "Low")
        availability = FieldAvailability(
            field=field,
            value=None,
            state="bounded_unresolved",
            reason_code=decision.reason_codes[0],
            period_end=source_attempt.period_end,
            source_accession=source_attempt.accession,
            source_kind=source_attempt.source_kind or source_attempt.source,
            evidence_class="bounded_estimate",
            freshness="current",
            fallback_level=fallback_level,  # type: ignore[arg-type]
            uncertainty=UncertaintyRange(
                low=low,
                high=high,
                basis=f"{source_attempt.source} source-backed range",
                source_accessions=(source_attempt.accession,),
            ),
            authority="production",
        )
        return EvidenceAvailability(availability, "Low")
    if decision.status in {"reported", "reported_aggregate", "explicit_zero"}:
        annual = fallback_level == "annual_carried_forward"
        availability = FieldAvailability(
            field=field,
            value=source_attempt.value,
            state="explicit_zero" if decision.status == "explicit_zero" else "reported",
            reason_code=decision.reason_codes[0],
            period_end=source_attempt.period_end,
            source_accession=source_attempt.accession,
            source_kind=("companyfacts" if annual else source_attempt.source_kind or source_attempt.source),
            evidence_class=("reported" if annual else decision.status),
            freshness=("carried_forward" if annual else "current"),
            fallback_level=fallback_level,  # type: ignore[arg-type]
            source_age_days=source_attempt.source_age_days,
            covered_fields=source_attempt.covered_fields,
            coverage_basis=source_attempt.coverage_basis,  # type: ignore[arg-type]
            coverage_source_facts=source_attempt.coverage_source_facts,
            economic_scope=source_attempt.economic_scope,
            authority="production",
        )
        return EvidenceAvailability(availability, decision.reliability_cap or "Low")
    raise ValueError("nonpromotable policy decision cannot project")


def source_attempt_from_decision(
    decision: EvidenceDecision,
    *,
    source: str,
    eligible: bool,
) -> SourceAttempt:
    if source not in _ORDER:
        raise ValueError("unsupported source")
    selected = decision.selected
    return SourceAttempt(
        source=source,
        status=decision.status,
        value=decision.selected_value,
        low=decision.selected_range[0] if decision.selected_range else None,
        high=decision.selected_range[1] if decision.selected_range else None,
        eligible=eligible,
        accession=(selected.accession if selected is not None else "unresolved-source"),
        period_end=(selected.period_end if selected is not None else decision.request.valuation_date or "1970-01-01"),
        reason_codes=decision.reason_codes,
        source_kind=(selected.source_kind if selected is not None else None),
        filed_date=(selected.filed_date if selected is not None else None),
        source_url=(selected.source_url if selected is not None else None),
        unit=(selected.unit if selected is not None else None),
        entity_identifier=(selected.entity_identifier if selected is not None else None),
        consolidation_scope=(selected.consolidation_scope if selected is not None else None),
        candidate_id=(selected.candidate_id if selected is not None else None),
        covered_fields=(selected.covered_fields if selected is not None else ()),
        coverage_basis=(selected.coverage_basis if selected is not None else None),
        economic_scope=(
            "|".join(selected.covered_fields)
            if selected is not None and selected.covered_fields
            else None
        ),
    )
