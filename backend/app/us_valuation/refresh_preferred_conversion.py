"""Source-bound preferred-conversion proof for PG.

This module only proves the share denominator/claim basis used by the retained
PG model.  It deliberately does not bind or evaluate a valuation recipe.
"""

from __future__ import annotations

from datetime import date
import math
import re
from typing import Any, Mapping


class PreferredConversionRefreshError(ValueError):
    """Raised when the controlling filing cannot prove the conversion basis."""


PG_CIK = "0000080424"
CONVERSION_POLICY = {'version':'PG-IF-CONVERTED-1','ticker':'PG','cik':PG_CIK}
_US_GAAP_NAMESPACE_PREFIX = "http://fasb.org/us-gaap/"

_BASIC = "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic"
_PREFERRED_CONVERSION = "us-gaap:IncrementalCommonSharesAttributableToConversionOfPreferredStock"
_AWARD_DILUTION = "us-gaap:IncrementalCommonSharesAttributableToShareBasedPaymentArrangements"
_DILUTED = "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"
_PREFERRED_VALUE = "us-gaap:PreferredStockValue"

_SHARE_FACTS = {
    _BASIC: "xbrli:shares",
    _PREFERRED_CONVERSION: "xbrli:shares",
    _AWARD_DILUTION: "xbrli:shares",
    _DILUTED: "xbrli:shares",
}

_CLASS_AXIS = "us-gaap:StatementClassOfStockAxis"
_CLASS_A = "us-gaap:PreferredClassAMember"
_CLASS_B = "us-gaap:PreferredClassBMember"


def _fail(message: str) -> None:
    raise PreferredConversionRefreshError(message)


def _parse_day(value: Any, field: str) -> date:
    if not isinstance(value, str):
        _fail(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        _fail(f"{field} must be an ISO date")
        raise AssertionError from exc


def _standard_fact(fact: Mapping[str, Any], qname: str, unit: str) -> bool:
    return (
        fact.get("qname") == qname
        and isinstance(fact.get("namespace"), str)
        and re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}', fact['namespace'])
        and fact.get("unit") == unit
    )


def _finite_number(fact: Mapping[str, Any], qname: str) -> float:
    value = fact.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        _fail(f"{qname} value is missing or non-finite")
    return float(value)


def _entity_and_accession(fact: Mapping[str, Any], source_accession: str) -> None:
    if fact.get("entity_identifier") != PG_CIK:
        _fail(f"{fact.get('qname', 'fact')} CIK identity is not {PG_CIK}")
    if fact.get('entity_scheme') != 'http://www.sec.gov/CIK':
        _fail('share/claim entity scheme is not SEC CIK')
    if fact.get("source_accession") != source_accession:
        _fail(f"{fact.get('qname', 'fact')} source accession conflicts with controlling filing")


def _duration_candidates(
    facts: list[Mapping[str, Any]], qname: str, source_accession: str
) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for fact in facts:
        if not _standard_fact(fact, qname, _SHARE_FACTS[qname]):
            continue
        _entity_and_accession(fact, source_accession)
        if fact.get("dimensions"):
            _fail(f"{qname} has an unexpected dimension")
        start, end = fact.get("period_start"), fact.get("period_end")
        if not isinstance(start, str) or not isinstance(end, str):
            continue
        if _parse_day(start, f"{qname} period_start") >= _parse_day(end, f"{qname} period_end"):
            _fail(f"{qname} has an invalid duration")
        if not 65 <= (_parse_day(end,'end') - _parse_day(start,'start')).days + 1 <= 385:
            continue
        rows.append(fact)
    if not rows:
        _fail(f"missing current-period {qname}")
    return rows


def _select_duration(
    facts: list[Mapping[str, Any]], qname: str, source_accession: str,
    period_start: str | None, period_end: str | None,
) -> Mapping[str, Any]:
    rows = _duration_candidates(facts, qname, source_accession)
    if period_start is not None:
        rows = [
            row for row in rows
            if row.get("period_start") == period_start and row.get("period_end") == period_end
        ]
        if not rows:
            if any(
                row.get("qname") == qname
                and row.get("period_start") == period_start
                and row.get("period_end") == period_end
                for row in facts
            ):
                _fail(f"{qname} has a conflicting unit or namespace in the current period")
            if qname == _PREFERRED_CONVERSION:
                _fail("preferred conversion fact does not have the requested current period")
            _fail(f"{qname} does not have the requested current period")
    else:
        latest_end = max(_parse_day(row["period_end"], f"{qname} period_end") for row in rows)
        rows = [row for row in rows if _parse_day(row["period_end"], f"{qname} period_end") == latest_end]
        # Prefer the longest same-end duration (normally the controlling FY).
        earliest_start = min(_parse_day(row["period_start"], f"{qname} period_start") for row in rows)
        rows = [row for row in rows if _parse_day(row["period_start"], f"{qname} period_start") == earliest_start]
    values = {_finite_number(row, qname) for row in rows}
    if len(rows) != 1 or len(values) != 1:
        _fail(f"ambiguous current-period {qname}")
    return rows[0]


def _derive_current_period(
    facts: list[Mapping[str, Any]], source_accession: str,
    period_start: str | None, period_end: str | None,
) -> tuple[str, str]:
    if period_start is not None:
        if not isinstance(period_start, str) or not isinstance(period_end, str):
            _fail("period_start and period_end must be supplied together")
        return period_start, period_end
    periods: set[tuple[str, str]] = set()
    for fact in facts:
        if fact.get("qname") not in _SHARE_FACTS:
            continue
        if fact.get("source_accession") != source_accession or fact.get("entity_identifier") != PG_CIK:
            continue
        start, end = fact.get("period_start"), fact.get("period_end")
        if isinstance(start, str) and isinstance(end, str) and _parse_day(start, "period_start") < _parse_day(end, "period_end"):
            if (period_end is None or end == period_end) and 65 <= (_parse_day(end,'end')-_parse_day(start,'start')).days+1 <= 385:
                periods.add((start, end))
    if not periods:
        _fail("missing current-period share facts")
    latest_end = max(_parse_day(end, "period_end") for _, end in periods)
    same_end = [(start, end) for start, end in periods if _parse_day(end, "period_end") == latest_end]
    return min(same_end, key=lambda item: _parse_day(item[0], "period_start"))


def _dimensions(fact: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    dimensions = fact.get("dimensions")
    if not isinstance(dimensions, list):
        return ()
    pairs: list[tuple[str, str]] = []
    for item in dimensions:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            _fail(f"{fact.get('qname', 'fact')} has malformed dimensions")
        pairs.append((str(item[0]), str(item[1])))
    return tuple(pairs)


def _preferred_classes(
    facts: list[Mapping[str, Any]], source_accession: str, period_end: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    for fact in facts:
        if not _standard_fact(fact, _PREFERRED_VALUE, "USD"):
            continue
        _entity_and_accession(fact, source_accession)
        if fact.get("period_end") != period_end or fact.get("period_start") is not None:
            continue
        candidates.append(fact)
    by_class: dict[str, list[Mapping[str, Any]]] = {_CLASS_A: [], _CLASS_B: []}
    for fact in candidates:
        dimensions = _dimensions(fact)
        if len(dimensions) != 1 or dimensions[0][0] != _CLASS_AXIS:
            if _finite_number(fact, _PREFERRED_VALUE) != 0:
                _fail("unknown nonzero preferred class")
            continue
        member = dimensions[0][1]
        if member not in by_class:
            if _finite_number(fact, _PREFERRED_VALUE) != 0:
                _fail(f"unknown nonzero preferred class {member}")
            continue
        by_class[member].append(fact)
    selected: list[Mapping[str, Any]] = []
    for member in (_CLASS_A, _CLASS_B):
        rows = by_class[member]
        if not rows:
            _fail(f"missing preferred class scope {member}")
        values = {_finite_number(row, _PREFERRED_VALUE) for row in rows}
        if len(rows) != 1 or len(values) != 1:
            _fail(f"ambiguous preferred class scope {member}")
        selected.append(rows[0])
    return selected[0], selected[1]


def bind_preferred_conversion_sources(
    structural_filing: Mapping[str, Any],
    *,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Bind PG's same-filing preferred conversion and diluted share proof."""

    if not isinstance(structural_filing, Mapping):
        _fail("structural filing must be a mapping")
    source_accession = structural_filing.get("source_accession")
    facts = structural_filing.get("facts")
    if not isinstance(source_accession, str) or not source_accession:
        _fail("missing controlling source accession")
    if not isinstance(facts, list):
        _fail("structural filing facts are missing")
    current_start, current_end = _derive_current_period(facts, source_accession, period_start, period_end)
    selected: dict[str, Mapping[str, Any]] = {}
    for qname in _SHARE_FACTS:
        selected[qname] = _select_duration(facts, qname, source_accession, current_start, current_end)
    starts = {row.get("period_start") for row in selected.values()}
    ends = {row.get("period_end") for row in selected.values()}
    if len(starts) != 1 or len(ends) != 1:
        _fail("share facts do not share one current period")
    selected_start, selected_end = next(iter(starts)), next(iter(ends))
    assert isinstance(selected_start, str) and isinstance(selected_end, str)
    preferred_a, preferred_b = _preferred_classes(facts, source_accession, selected_end)
    if _finite_number(preferred_a, _PREFERRED_VALUE) <= 0 or _finite_number(preferred_b, _PREFERRED_VALUE) != 0:
        _fail('changed preferred class capital structure requires review')
    for fact in facts:
        name = str(fact.get('qname','')).lower()
        if (fact.get('period_end') == selected_end and fact.get('period_start') is None
            and fact.get('unit') == 'USD' and ('preferred' in name or 'temporaryequity' in name)
            and fact.get('qname') not in (_PREFERRED_VALUE, 'us-gaap:PreferredStockParOrStatedValuePerShare')
            and _finite_number(fact,name) != 0):
            _fail('new preferred or temporary claim structure requires review')

    basic = _finite_number(selected[_BASIC], _BASIC)
    conversion = _finite_number(selected[_PREFERRED_CONVERSION], _PREFERRED_CONVERSION)
    award_dilution = _finite_number(selected[_AWARD_DILUTION], _AWARD_DILUTION)
    diluted = _finite_number(selected[_DILUTED], _DILUTED)
    if conversion <= 0:
        _fail("preferred conversion is unsupported without a positive conversion share fact")
    if basic <= 0 or award_dilution < 0 or diluted <= 0:
        _fail("share denominator facts must be positive/nonnegative")
    pre_conversion_diluted = basic + award_dilution
    if not math.isclose(diluted, pre_conversion_diluted + conversion, rel_tol=0.0, abs_tol=1e-6):
        _fail("diluted shares do not reconcile without double conversion")

    def source_row(fact: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "qname": fact["qname"],
            "namespace": fact["namespace"],
            "unit": fact["unit"],
            "value": fact["value"],
            "entity_identifier": fact["entity_identifier"],
            "source_accession": fact["source_accession"],
            "period_start": fact.get("period_start"),
            "period_end": fact.get("period_end"),
            "context_id": fact.get("context_id"),
            "dimensions": fact.get("dimensions", []),
        }

    preferred_value = _finite_number(preferred_a, _PREFERRED_VALUE) + _finite_number(preferred_b, _PREFERRED_VALUE)
    return {
        "status": "bound_success",
        "ticker": "PG",
        "cik": PG_CIK,
        "controlling_accession": source_accession,
        "period_start": selected_start,
        "period_end": selected_end,
        "share_denominator": {
            "basic_weighted_average": basic,
            "preferred_conversion_increment": conversion,
            "other_dilutive_awards_increment": award_dilution,
            "pre_conversion_diluted": pre_conversion_diluted,
            "converted_diluted": diluted,
        },
        "preferred_claim": {
            "class_a_carrying_value": _finite_number(preferred_a, _PREFERRED_VALUE),
            "class_b_carrying_value": _finite_number(preferred_b, _PREFERRED_VALUE),
            "reported_preferred_carrying_value": preferred_value,
            "additional_preferred_deduction": 0.0,
            "basis": "assumed_conversion_is_included_in_the_diluted_share_denominator",
        },
        "source_ledger": {
            "share_facts": {name: source_row(row) for name, row in selected.items()},
            "preferred_class_a": source_row(preferred_a),
            "preferred_class_b": source_row(preferred_b),
            "reconciliation": "diluted = basic + preferred conversion + other dilutive awards",
        },
    }


def project_converted_bridge(resolution, proof):
    """Project the reported bridge into the expressly assumed-conversion basis.

    This is not an absence proof. The reported preferred value remains in the
    conversion evidence; only its additional model deduction is zero.
    """
    from dataclasses import replace
    from .bridge_policy import BridgeRange, _bridge_adjustment_range
    if proof.get('ticker') != 'PG' or proof.get('status') != 'bound_success':
        _fail('validated PG conversion proof required')
    preferred = BridgeRange(0.,0.,0.)
    blocked = tuple(field for field in resolution.blocking_fields if field != 'preferred_equity')
    bounded = tuple(field for field in resolution.bounded_fields if field != 'preferred_equity')
    return replace(resolution, preferred_equity=preferred,
        fully_diluted_shares=proof['share_denominator']['converted_diluted'],
        blocking_fields=blocked,bounded_fields=bounded,
        missing_fields=tuple(sorted(set(blocked)|set(bounded))),
        complete=not blocked and not bounded,can_value=not blocked,
        bridge_adjustment=_bridge_adjustment_range(resolution.cash_and_investments,resolution.total_debt,preferred,resolution.noncontrolling_interests))
