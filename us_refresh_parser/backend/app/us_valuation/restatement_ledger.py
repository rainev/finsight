"""Point-in-time restatement and supersession ledger for official facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from numbers import Real
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


def _iso(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error
    return value


@dataclass(frozen=True)
class RestatementFact:
    value: float
    tag: str
    unit: str
    period_start: str | None
    period_end: str
    dimensions: tuple[tuple[str, str], ...]
    accession: str
    filed_date: str
    source_url: str
    entity_identifier: str | None = None
    form: str | None = None
    report_date: str | None = None
    dimensions_known: bool = True

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RestatementFact:
        raw_value = value.get("value")
        if isinstance(raw_value, bool) or not isinstance(raw_value, Real) or not isfinite(float(raw_value)):
            raise ValueError("restatement fact value must be finite")
        raw_dimensions = value.get("dimensions")
        dimensions_known = raw_dimensions is not None
        dimensions = tuple(sorted(tuple(item) for item in (raw_dimensions or ())))
        if any(len(item) != 2 or any(not isinstance(part, str) for part in item) for item in dimensions):
            raise ValueError("restatement dimensions must be string pairs")
        period_start = value.get("period_start")
        if period_start is not None:
            period_start = _iso(period_start, "period_start")
        for field in ("tag", "unit", "accession", "source_url"):
            if not isinstance(value.get(field), str) or not str(value[field]).strip():
                raise ValueError(f"restatement {field} must be nonempty text")
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(value["accession"])):
            raise ValueError("restatement accession must use SEC 10-2-6 format")
        source = urlparse(str(value["source_url"]))
        if source.scheme != "https" or source.hostname not in {
            "www.sec.gov", "sec.gov", "data.sec.gov"
        }:
            raise ValueError("restatement source_url must be an official SEC HTTPS URL")
        report_date = value.get("report_date")
        if report_date is not None:
            report_date = _iso(report_date, "report_date")
        form = value.get("form")
        if form is not None and (not isinstance(form, str) or not form.strip()):
            raise ValueError("restatement form must be nonempty text")
        return cls(
            value=float(raw_value),
            tag=str(value["tag"]),
            unit=str(value["unit"]),
            period_start=period_start,
            period_end=_iso(value["period_end"], "period_end"),
            dimensions=dimensions,
            accession=str(value["accession"]),
            filed_date=_iso(value["filed_date"], "filed_date"),
            source_url=str(value["source_url"]),
            entity_identifier=(
                str(value["entity_identifier"])
                if value.get("entity_identifier") is not None
                else None
            ),
            form=form,
            report_date=report_date,
            dimensions_known=dimensions_known,
        )

    @property
    def semantic_key(self) -> tuple[object, ...]:
        return (
            self.tag,
            self.unit,
            self.period_start,
            self.period_end,
            self.dimensions,
            self.entity_identifier,
            self.dimensions_known,
        )


@dataclass(frozen=True)
class RestatementLink:
    original_accession: str
    corrected_accession: str
    original_value: float
    corrected_value: float
    original_filed_date: str
    corrected_filed_date: str
    semantic_context: dict[str, Any]
    link_type: str
    confirmed_restatement: bool


@dataclass(frozen=True)
class RestatementLedger:
    valuation_date: str
    selected: tuple[RestatementFact, ...]
    links: tuple[RestatementLink, ...]
    future_candidates: tuple[RestatementFact, ...]


def _semantic_context(fact: RestatementFact) -> dict[str, Any]:
    return {
        "tag": fact.tag,
        "unit": fact.unit,
        "period_start": fact.period_start,
        "period_end": fact.period_end,
        "dimensions": [list(item) for item in fact.dimensions],
        "entity_identifier": fact.entity_identifier,
        "dimensions_known": fact.dimensions_known,
        "form": fact.form,
        "report_date": fact.report_date,
    }


def build_restatement_ledger(
    candidates: Sequence[Mapping[str, Any]], *, valuation_date: str
) -> RestatementLedger:
    cutoff = _iso(valuation_date, "valuation_date")
    facts = tuple(RestatementFact.from_dict(item) for item in candidates)
    eligible = tuple(fact for fact in facts if fact.filed_date <= cutoff)
    future = tuple(sorted((fact for fact in facts if fact.filed_date > cutoff), key=lambda item: (item.filed_date, item.accession)))
    groups: dict[tuple[object, ...], list[RestatementFact]] = {}
    for fact in facts:
        groups.setdefault(fact.semantic_key, []).append(fact)

    selected: list[RestatementFact] = []
    links: list[RestatementLink] = []
    for semantic_key, group in sorted(groups.items(), key=lambda item: repr(item[0])):
        ordered = sorted(group, key=lambda item: (item.filed_date, item.accession))
        seen_filing: dict[tuple[str, str], RestatementFact] = {}
        for fact in ordered:
            filing_key = (fact.filed_date, fact.accession)
            prior_same = seen_filing.get(filing_key)
            if prior_same is not None and prior_same.value != fact.value:
                raise ValueError("conflicting values within one accession semantic context")
            seen_filing[filing_key] = fact
        for original, corrected in zip(ordered, ordered[1:]):
            if original.value == corrected.value:
                continue
            if not original.dimensions_known or not corrected.dimensions_known:
                link_type = "unresolved_dimension_context"
            elif (
                corrected.form is not None
                and corrected.form.endswith("/A")
                and corrected.report_date == original.report_date
            ):
                link_type = "amendment"
            elif corrected.report_date == original.report_date:
                link_type = "comparative_value_change_candidate"
            else:
                link_type = "unresolved_value_change"
            links.append(
                RestatementLink(
                    original_accession=original.accession,
                    corrected_accession=corrected.accession,
                    original_value=original.value,
                    corrected_value=corrected.value,
                    original_filed_date=original.filed_date,
                    corrected_filed_date=corrected.filed_date,
                    semantic_context=_semantic_context(original),
                    link_type=link_type,
                    confirmed_restatement=link_type == "amendment",
                )
            )
        eligible_group = [fact for fact in ordered if fact.filed_date <= cutoff]
        if eligible_group:
            selected.append(eligible_group[-1])
    return RestatementLedger(
        valuation_date=cutoff,
        selected=tuple(sorted(selected, key=lambda item: repr(item.semantic_key))),
        links=tuple(links),
        future_candidates=future,
    )
