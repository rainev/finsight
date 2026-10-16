"""Fail-closed, point-in-time Companyfacts selection for equity model inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
import re
from typing import Any, Mapping


_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_ELIGIBLE_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})


@dataclass(frozen=True)
class SelectedFact:
    concept: str
    value: float
    unit: str
    period_start: str | None
    period_end: str
    filed_date: str
    accession: str
    form: str
    fiscal_year: int | None


def _iso(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error


def _candidate(
    concept: str,
    unit: str,
    raw: Mapping[str, Any],
    valuation_date: str,
) -> SelectedFact | None:
    value = raw.get("val")
    start, end, filed, accession, form = (
        raw.get(key) for key in ("start", "end", "filed", "accn", "form")
    )
    cutoff = _iso(valuation_date, "valuation_date")
    try:
        normalized_end = _iso(end, "period_end")
        normalized_filed = _iso(filed, "filed_date")
    except ValueError:
        return None
    normalized_start = None
    if start is not None:
        try:
            normalized_start = _iso(start, "period_start")
        except ValueError:
            return None
        if normalized_start > normalized_end:
            return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or not isinstance(accession, str)
        or not _ACCESSION.fullmatch(accession)
        or form not in _ELIGIBLE_FORMS
        or normalized_end > cutoff
        or normalized_filed > cutoff
    ):
        return None
    fiscal_year = raw.get("fy")
    if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int): fiscal_year = None
    return SelectedFact(
        concept,
        float(value),
        unit,
        normalized_start,
        normalized_end,
        normalized_filed,
        accession,
        form,
        fiscal_year,
    )


def _select(gaap: Mapping[str, Any], *, concepts: tuple[str, ...], unit: str, valuation_date: str, annual: bool) -> list[SelectedFact]:
    rows: list[SelectedFact] = []
    for concept in concepts:
        payload = gaap.get(concept, {})
        for raw in payload.get("units", {}).get(unit, []) if isinstance(payload, Mapping) else []:
            if not isinstance(raw, Mapping): continue
            selected = _candidate(concept, unit, raw, valuation_date)
            annual_duration = None
            if selected and selected.period_start is not None:
                annual_duration = (
                    date.fromisoformat(selected.period_end)
                    - date.fromisoformat(selected.period_start)
                ).days
            if selected and (
                not annual
                or (
                    raw.get("fp") == "FY"
                    and selected.form in {"10-K", "10-K/A"}
                    and annual_duration is not None
                    and 300 <= annual_duration <= 380
                )
            ):
                rows.append(selected)
    by_key: dict[tuple[str, str | None, str, str], SelectedFact] = {}
    for row in rows:
        key = (row.concept, row.period_start, row.period_end, row.accession)
        if key in by_key and by_key[key].value != row.value:
            raise ValueError(f"conflicting duplicate Companyfacts value for {row.concept}")
        by_key[key] = row
    return list(by_key.values())


def annual_facts(gaap: Mapping[str, Any], *, concepts: tuple[str, ...], unit: str, valuation_date: str) -> dict[int, SelectedFact]:
    choices: dict[int, SelectedFact] = {}
    for fact in _select(gaap, concepts=concepts, unit=unit, valuation_date=valuation_date, annual=True):
        if fact.fiscal_year is None: continue
        prior = choices.get(fact.fiscal_year)
        if prior is None or (fact.period_end, fact.filed_date, fact.accession) > (prior.period_end, prior.filed_date, prior.accession): choices[fact.fiscal_year] = fact
    return choices


def latest_instant(gaap: Mapping[str, Any], *, concepts: tuple[str, ...], unit: str, valuation_date: str) -> SelectedFact | None:
    rows = _select(gaap, concepts=concepts, unit=unit, valuation_date=valuation_date, annual=False)
    return max(rows, key=lambda item: (item.period_end, item.filed_date, item.accession), default=None)


def source_statement(fact: SelectedFact, *, submissions: Mapping[str, Any], cik: str) -> dict[str, object]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = list(recent.get("accessionNumber", []))
    try:
        index = accessions.index(fact.accession)
    except ValueError as exc:
        raise ValueError(
            "selected fact accession is absent from cutoff submissions"
        ) from exc
    fields = {
        "primary_document": recent.get("primaryDocument", []),
        "form": recent.get("form", []),
        "filed_date": recent.get("filingDate", []),
    }
    if any(not isinstance(values, list) or index >= len(values) for values in fields.values()):
        raise ValueError("selected filing metadata is incomplete")
    primary = fields["primary_document"][index]
    if not isinstance(primary, str) or not primary:
        raise ValueError("selected fact primary document is missing")
    if fields["form"][index] != fact.form or fields["filed_date"][index] != fact.filed_date:
        raise ValueError("selected fact conflicts with cutoff submissions metadata")
    cik_digits = "".join(character for character in str(cik) if character.isdigit())
    if not cik_digits:
        raise ValueError("CIK must contain digits")
    digits = "".join(char for char in fact.accession if char.isdigit())
    return {
        "form": fact.form,
        "period_end": fact.period_end,
        "filed_date": fact.filed_date,
        "accession": fact.accession,
        "url": (
            "https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik_digits)}/{digits}/{primary}"
        ),
    }
