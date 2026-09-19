"""Source-bound share-class reconciliation for residual-income refreshes.

Some issuers report more than one common-stock class.  A generic CompanyFacts
weighted-average-share selector is not a safe replacement for an issuer's
class conversion rule: for Berkshire Hathaway, the BRK.B denominator is
reported Class A shares multiplied by the filing's reported conversion ratio,
plus reported Class B shares.

This module deliberately does not infer a ratio from prices or from a value
fit.  Missing, conflicting, or misidentified structural facts are explicit
review failures so a caller can withhold the refresh.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import re
from math import isfinite
from numbers import Real
from typing import Any, Mapping

from .approved_cash_only_scope import _private_packet
from .concept_resolver import load_structural_rules


class ShareBasisReviewRequired(ValueError):
    """Raised when source facts cannot prove the requested share basis."""

    def __init__(self, *reasons: str) -> None:
        self.reasons = tuple(str(reason) for reason in reasons if str(reason))
        super().__init__("share basis requires review: " + "; ".join(self.reasons))


_BRK_CIK = "0001067983"
_BRK_CLASS_BY_TICKER = {"BRK.A": "A", "BRK.B": "B"}
_CLASS_AXIS = "us-gaap:StatementClassOfStockAxis"


def _iso_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(_text(value, field))
    except ValueError as exc:
        raise ShareBasisReviewRequired(f"{field} must be an ISO date") from exc


def _canonical_qname(namespace: str, local_name: str) -> str:
    """Match the Arelle worker's deterministic namespace canonicalizer."""
    return f"ns_{hashlib.sha1(namespace.encode('utf-8')).hexdigest()[:10]}:{local_name}"


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShareBasisReviewRequired(f"{field} is missing")
    return value.strip()


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ShareBasisReviewRequired(f"{field} is not numeric")
    result = float(value)
    if not isfinite(result) or result <= 0:
        raise ShareBasisReviewRequired(f"{field} must be positive and finite")
    return result


def _cik(value: Any) -> str:
    raw = _text(str(value) if isinstance(value,int) and not isinstance(value,bool) else value, "CIK")
    if not raw.isdigit() or len(raw) > 10:
        raise ShareBasisReviewRequired("CIK is invalid")
    return raw.zfill(10)


def _local_name(row: Mapping[str, Any]) -> str:
    local = row.get("local_name")
    if isinstance(local, str) and local:
        return local
    qname = row.get("qname")
    return str(qname).rsplit(":", 1)[-1] if isinstance(qname, str) else ""


def _dimensions(row: Mapping[str, Any]) -> tuple[str, str] | None:
    dimensions = row.get("dimensions")
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 1:
        return None
    pair = dimensions[0]
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        return None
    return str(pair[0]), str(pair[1])


def _member_class(row: Mapping[str, Any]) -> str | None:
    pair = _dimensions(row)
    if pair is None or pair[0] != _CLASS_AXIS:
        return None
    member = pair[1].rsplit(":", 1)[-1]
    if pair[1] == "us-gaap:CommonClassAMember":
        return "A"
    if pair[1] == "us-gaap:CommonClassBMember":
        return "B"
    return None


def _identity_matches(
    row: Mapping[str, Any],
    *,
    local_name: str,
    unit: str,
    cik: str,
    accession: str,
    namespace_pattern: str,
) -> bool:
    entity = str(row.get("entity_identifier", ""))
    return (
        _local_name(row) == local_name
        and isinstance(row.get("namespace"), str)
        and re.fullmatch(namespace_pattern, row["namespace"]) is not None
        and row.get("qname") == _canonical_qname(row["namespace"], local_name)
        and row.get("unit") == unit
        and str(row.get("source_accession", "")) == accession
        and entity.zfill(10) == cik
        and row.get("entity_scheme") == "http://www.sec.gov/CIK"
        and row.get("period_start") is None
    )


def _unique_fact(
    rows: list[Mapping[str, Any]],
    *,
    label: str,
) -> dict[str, Any]:
    if not rows:
        raise ShareBasisReviewRequired(f"{label} source fact is missing")
    values = {_number(row.get("value"), f"{label} value") for row in rows}
    if len(values) != 1:
        raise ShareBasisReviewRequired(f"{label} source facts conflict")
    # Identical parser duplicates are harmless; retain one complete source row.
    return deepcopy(rows[0])


def resolve_class_equivalent_share_basis(
    structural_packet: Mapping[str, Any],
    *,
    ticker: str,
    selected_class: str,
    cik: str,
    accession: str,
    report_period_end: str,
    filing_date: str,
    cutoff: str,
    expected_equivalent_shares: float | None = None,
) -> dict[str, Any]:
    """Resolve a class-equivalent share denominator from one filing.

    ``report_period_end`` is the controlling filing's reporting period.  The
    class outstanding facts may have a later observation date (as BRK.B's
    2026-07-29 cover-page counts do), but must share one exact date with each
    other and the same accession/issuer.  The conversion ratio must be an
    explicit structural fact from that filing.

    The result's ``value`` and ``equivalent_shares`` are the only derived
    denominator values.  Every source component and the formula are retained
    for auditability.  No market price is accepted or consulted.
    """
    if not isinstance(structural_packet, Mapping):
        raise ShareBasisReviewRequired("structural packet is missing")
    ticker = _text(ticker, "ticker")
    selected_class = _text(selected_class, "selected class").upper()
    if selected_class not in {"A", "B"}:
        raise ShareBasisReviewRequired("selected class must be A or B")
    cik = _cik(cik)
    governed_class = _BRK_CLASS_BY_TICKER.get(ticker)
    if governed_class is None:
        raise ShareBasisReviewRequired("ticker is outside the governed BRK.A/BRK.B share basis")
    if cik != _BRK_CIK:
        raise ShareBasisReviewRequired("CIK is not the governed Berkshire Hathaway CIK")
    if selected_class != governed_class:
        raise ShareBasisReviewRequired("ticker and selected class do not match")
    accession = _text(accession, "accession")
    report_period_end = _text(report_period_end, "report period end")
    filing_date_value = _iso_date(filing_date, "filing date")
    cutoff_value = _iso_date(cutoff, "cutoff")
    report_period_value = _iso_date(report_period_end, "report period end")
    if filing_date_value > cutoff_value:
        raise ShareBasisReviewRequired("filing date is after cutoff")
    if structural_packet.get("source_accession") != accession:
        raise ShareBasisReviewRequired("structural packet accession mismatch")
    if structural_packet.get("filed_date") != filing_date:
        raise ShareBasisReviewRequired("structural packet filing date mismatch")
    packet_report_period = structural_packet.get("report_date") or structural_packet.get("period_end")
    if packet_report_period is not None and str(packet_report_period) != report_period_end:
        raise ShareBasisReviewRequired("structural packet report period mismatch")
    facts = structural_packet.get("facts")
    if not isinstance(facts, list):
        raise ShareBasisReviewRequired("structural packet has no fact rows")

    class_rows: dict[str, list[Mapping[str, Any]]] = {"A": [], "B": []}
    ratio_rows: list[Mapping[str, Any]] = []
    for row in facts:
        if not isinstance(row, Mapping) or not _identity_matches(
            row,
            local_name="EntityCommonStockSharesOutstanding",
            unit="xbrli:shares",
            cik=cik,
            accession=accession,
            namespace_pattern=r"http://xbrl\.sec\.gov/dei/\d{4}",
        ):
            if isinstance(row, Mapping) and _identity_matches(
                row,
                local_name="NumberOfSharesObtainableFromConvertingOneShareFromOneClassToAnotherClass",
                unit="xbrli:shares",
                cik=cik,
                accession=accession,
                namespace_pattern=r"http://www\.berkshirehathaway\.com/\d{8}",
            ):
                if _member_class(row) == "B":
                    ratio_rows.append(row)
            continue
        klass = _member_class(row)
        if klass is not None:
            class_rows[klass].append(row)

    selected: dict[str, dict[str, Any]] = {}
    for klass in ("A", "B"):
        row = _unique_fact(class_rows[klass], label=f"Class {klass} outstanding")
        if not row.get("period_end"):
            raise ShareBasisReviewRequired(f"Class {klass} outstanding period is missing")
        selected[klass] = row
    share_periods = {str(row.get("period_end")) for row in selected.values()}
    if len(share_periods) != 1:
        raise ShareBasisReviewRequired("Class A and Class B outstanding periods conflict")
    share_period_value = _iso_date(next(iter(share_periods)), "share observation period")
    if not report_period_value <= share_period_value <= filing_date_value:
        raise ShareBasisReviewRequired("share observation period is outside report/filing window")
    for row in (*selected.values(), *ratio_rows):
        if row.get("filed_date") != filing_date or row.get("report_date") != report_period_end:
            raise ShareBasisReviewRequired("source fact filing identity or report period mismatch")

    ratio = _unique_fact(ratio_rows, label="Class conversion ratio")
    ratio_period = str(ratio.get("period_end", ""))
    if ratio_period != report_period_end:
        raise ShareBasisReviewRequired("Class conversion ratio period mismatch")
    conversion_ratio = _number(ratio.get("value"), "Class conversion ratio")
    class_a = _number(selected["A"].get("value"), "Class A shares")
    class_b = _number(selected["B"].get("value"), "Class B shares")
    if selected_class == "B":
        value = class_a * conversion_ratio + class_b
        formula = f"Class A shares * {conversion_ratio:g} + Class B shares"
        source_kind = "derived_class_b_equivalent_shares"
    else:
        value = class_a + class_b / conversion_ratio
        formula = f"Class A shares + Class B shares / {conversion_ratio:g}"
        source_kind = "derived_class_a_equivalent_shares"
    if not isfinite(value) or value <= 0:
        raise ShareBasisReviewRequired("derived equivalent share count is invalid")
    if expected_equivalent_shares is not None:
        expected = _number(expected_equivalent_shares, "expected equivalent shares")
        if value != expected:
            raise ShareBasisReviewRequired(
                f"derived equivalent shares {value:g} do not match expected {expected:g}"
            )
    return {
        "status": "verified",
        "ticker": ticker,
        "selected_class": selected_class,
        "unit": "xbrli:shares",
        "value": value,
        "equivalent_shares": value,
        "class_a_shares": class_a,
        "class_b_shares": class_b,
        "conversion_ratio": conversion_ratio,
        "formula": formula,
        "source_kind": source_kind,
        "reported_vs_estimated": "reported_components_with_derived_conversion",
        "source_accession": accession,
        "report_period_end": report_period_end,
        "share_observation_period_end": next(iter(share_periods)),
        "sources": [deepcopy(selected["A"]), deepcopy(selected["B"]), deepcopy(ratio)],
    }


SHARE_PROFILE_BBY = "one_reported_ytd_with_fixed_sensitivity"
SHARE_PROFILE_REPORTED_YTD_AND_COVER = "reported_ytd_and_cover"
_SHARE_PROFILE_CIKS = {
    "BBY": "0000764478",
    "GILD": "0000882095",
    "INCY": "0000879169",
}
_SHARE_PROFILE_BY_TICKER = {
    "BBY": SHARE_PROFILE_BBY,
    "GILD": SHARE_PROFILE_REPORTED_YTD_AND_COVER,
    "INCY": SHARE_PROFILE_REPORTED_YTD_AND_COVER,
}
_SHARE_SCENARIOS = ("bear", "base", "bull")
_APPROVED_US_GAAP_NAMESPACES = frozenset(load_structural_rules()['official_us_gaap_namespaces'])


def _same_number(left: Any, right: Any, field: str) -> bool:
    return abs(_number(left, field) - _number(right, field)) == 0.0


def _share_recipe_value(recipe: Mapping[str, Any], scenario: str) -> float:
    scenarios = recipe.get("scenarios")
    if not isinstance(scenarios, Mapping) or scenario not in scenarios:
        raise ShareBasisReviewRequired(f"recipe {scenario} scenario is missing")
    inputs = scenarios[scenario].get("inputs") if isinstance(scenarios[scenario], Mapping) else None
    if not isinstance(inputs, Mapping):
        raise ShareBasisReviewRequired(f"recipe {scenario} inputs are missing")
    key = "shares" if scenarios[scenario].get("engine") == "constant_growth_fcff" else "diluted_shares"
    value = inputs.get(key)
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)) or float(value) <= 0:
        raise ShareBasisReviewRequired(f"recipe {scenario} {key} is invalid")
    return float(value)


def _private_share_rows(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    history = packet.get("history_backed")
    ledger = history.get("source_ledger") if isinstance(history, Mapping) else None
    rows = ledger.get("bridge_sources") if isinstance(ledger, Mapping) else None
    if not isinstance(rows, list):
        raise ShareBasisReviewRequired("private bridge share source rows are missing")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _private_share_value(packet: Mapping[str, Any]) -> tuple[float, list[float]]:
    history = packet.get("history_backed")
    assumptions = history.get("governed_assumptions") if isinstance(history, Mapping) else None
    ledger = history.get("source_ledger") if isinstance(history, Mapping) else None
    reconciliation = ledger.get("bridge_reconciliation") if isinstance(ledger, Mapping) else None
    values = assumptions.get("shares") if isinstance(assumptions, Mapping) else None
    if not isinstance(values, list):
        values = reconciliation.get("shares") if isinstance(reconciliation, Mapping) else None
    if not isinstance(values, list) or len(values) != 3:
        raise ShareBasisReviewRequired("private governed share scenarios are missing")
    values = [_number(value, "private governed share scenario") for value in values]
    return values[1], values


def _share_source_kind(row: Mapping[str, Any], *, unit: str, concept_suffix: str) -> bool:
    concept = str(row.get("concept", ""))
    return (
        row.get("unit") == unit
        and row.get("reported_vs_estimated") == "reported"
        and row.get("source_kind") == "structural_xbrl"
        and str(row.get("dimensions") or "") in {"", "[]"}
        and concept.rsplit(":", 1)[-1] == concept_suffix
    )


def _unique_private_source(rows: list[dict[str, Any]], *, unit: str, concept_suffix: str, label: str) -> dict[str, Any]:
    matches = [row for row in rows if _share_source_kind(row, unit=unit, concept_suffix=concept_suffix)]
    if not matches:
        raise ShareBasisReviewRequired(f"private {label} share source is missing")
    values = {_number(row.get("value"), f"private {label} share source") for row in matches}
    if len(values) != 1:
        raise ShareBasisReviewRequired(f"private {label} share sources conflict")
    return deepcopy(matches[0])


def compile_share_basis_profile(
    recipe: Mapping[str, Any],
    *,
    profile: str | None = None,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Compile a share-basis contract from hash-verified private lineage."""

    ticker = recipe.get("ticker")
    if not isinstance(ticker, str) or ticker not in _SHARE_PROFILE_CIKS:
        raise ShareBasisReviewRequired("ticker is outside the governed share-basis profiles")
    selected_profile = profile or _SHARE_PROFILE_BY_TICKER[ticker]
    if selected_profile != _SHARE_PROFILE_BY_TICKER[ticker]:
        raise ShareBasisReviewRequired("requested share-basis profile does not match ticker")
    packet, provenance = _private_packet(recipe, project_root=project_root)
    issuer = packet.get("issuer")
    if not isinstance(issuer, Mapping) or issuer.get("ticker") != ticker or _cik(issuer.get("cik")) != _SHARE_PROFILE_CIKS[ticker]:
        raise ShareBasisReviewRequired("private share-basis issuer identity mismatch")
    recipe_values = [_share_recipe_value(recipe, scenario) for scenario in _SHARE_SCENARIOS]
    _, private_values = _private_share_value(packet)
    if recipe_values != private_values:
        raise ShareBasisReviewRequired("recipe share scenarios do not match private governed share scenarios")
    rows = _private_share_rows(packet)
    if selected_profile == SHARE_PROFILE_BBY:
        weighted = _unique_private_source(
            rows,
            unit="shares",
            concept_suffix="WeightedAverageNumberOfDilutedSharesOutstanding",
            label="reported YTD weighted-diluted",
        )
        if not _same_number(weighted.get("value"), private_values[1], "BBY private base share"):
            raise ShareBasisReviewRequired("BBY private base share does not match reported YTD source")
        factors = [private_values[index] / private_values[1] for index in range(3)]
        return {
            "schema_version": "FINSIGHT-SHARE-BASIS-1",
            "profile": selected_profile,
            "ticker": ticker,
            "cik": _SHARE_PROFILE_CIKS[ticker],
            "private_provenance": provenance,
            "stored_scenario_shares": dict(zip(_SHARE_SCENARIOS, private_values)),
            "sensitivity_factors": dict(zip(_SHARE_SCENARIOS, factors)),
            "private_sources": {"reported_ytd_weighted_diluted": weighted},
            "limitations": [
                "Current reported YTD weighted-diluted shares are the refreshed base; approved BBY scenario factors remain governed sensitivities.",
                "No cover/share-additive or conversion policy is applied.",
            ],
        }
    weighted = _unique_private_source(
        rows,
        unit="shares",
        concept_suffix="WeightedAverageNumberOfDilutedSharesOutstanding",
        label="reported YTD weighted-diluted",
    )
    cover = _unique_private_source(
        rows,
        unit="xbrli:shares",
        concept_suffix="EntityCommonStockSharesOutstanding",
        label="reported cover",
    )
    if not _same_number(weighted.get("value"), private_values[0], "private weighted share"):
        raise ShareBasisReviewRequired("private bear share does not match reported YTD source")
    if not _same_number(cover.get("value"), private_values[2], "private cover share"):
        raise ShareBasisReviewRequired("private bull share does not match reported cover source")
    if not _same_number((private_values[0] + private_values[2]) / 2.0, private_values[1], "private midpoint share"):
        raise ShareBasisReviewRequired("private base share is not the source-range midpoint")
    return {
        "schema_version": "FINSIGHT-SHARE-BASIS-1",
        "profile": selected_profile,
        "ticker": ticker,
        "cik": _SHARE_PROFILE_CIKS[ticker],
        "private_provenance": provenance,
        "stored_scenario_shares": dict(zip(_SHARE_SCENARIOS, private_values)),
        "private_sources": {"reported_ytd_weighted_diluted": weighted, "reported_cover": cover},
        "limitations": [
            "Bear and bull are reselected reported source observations; the base is their arithmetic midpoint.",
            "No fixed multiplicative factor, conversion share, or additive share policy is applied.",
        ],
    }


def _current_structural(packet: Mapping[str, Any]) -> dict[str, Any]:
    candidate = packet.get("structural_filing") or packet.get("structural") or packet
    if isinstance(candidate, Mapping) and isinstance(candidate.get("parsed"), Mapping):
        candidate = candidate["parsed"]
    if not isinstance(candidate, Mapping):
        raise ShareBasisReviewRequired("current complete packet has no structural filing")
    result = dict(candidate)
    if not isinstance(result.get("facts"), list):
        raise ShareBasisReviewRequired("current structural filing has no facts")
    return result


def _packet_cik(packet: Mapping[str, Any]) -> str | None:
    issuer = packet.get("issuer")
    if isinstance(issuer, Mapping) and issuer.get("cik") is not None:
        return _cik(issuer.get("cik"))
    return None


def _fact_identity(row: Mapping[str, Any], *, cik: str, accession: str) -> None:
    if str(row.get("entity_identifier", "")).zfill(10) != cik or row.get("entity_scheme") != "http://www.sec.gov/CIK":
        raise ShareBasisReviewRequired("share fact entity identity does not match issuer")
    if row.get("source_accession") != accession:
        raise ShareBasisReviewRequired("share fact accession does not match controlling filing")
    if row.get("dimensions") not in (None, [], ()) or row.get("typed_dimensions") not in (None, [], ()):
        raise ShareBasisReviewRequired("share fact dimensions are not undimensioned")
    if row.get("filed_date") is not None and str(row.get("filed_date")) != str(row.get("expected_filed_date")):
        raise ShareBasisReviewRequired("share fact filing date does not match controlling filing")


def _current_rows(structural: Mapping[str, Any], *, local_name: str, unit: str | tuple[str, ...], cik: str, accession: str, report_period_end: str, filed_date: str | None) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for raw in structural.get("facts", []):
        if not isinstance(raw, Mapping) or raw.get("local_name") != local_name:
            continue
        allowed_units = (unit,) if isinstance(unit, str) else unit
        if raw.get("unit") not in allowed_units:
            continue
        row = dict(raw)
        if local_name == "WeightedAverageNumberOfDilutedSharesOutstanding":
            if (
                row.get("qname") != f"us-gaap:{local_name}"
                or row.get("namespace") not in _APPROVED_US_GAAP_NAMESPACES
            ):
                raise ShareBasisReviewRequired("weighted-diluted share fact QName or taxonomy identity is invalid")
        if not isinstance(row.get("filed_date"), str) or not isinstance(row.get("report_date"), str):
            raise ShareBasisReviewRequired("share fact filed_date and report_date are required")
        row["expected_filed_date"] = filed_date
        _fact_identity(row, cik=cik, accession=accession)
        if row.get("report_date") is not None and row.get("report_date") != report_period_end:
            raise ShareBasisReviewRequired("share fact report period does not match controlling filing")
        if filed_date is not None and row.get("filed_date") not in (None, filed_date):
            raise ShareBasisReviewRequired("share fact filing date does not match controlling filing")
        matches.append(row)
    return matches


def _unique_current(rows: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    if not rows:
        raise ShareBasisReviewRequired(f"current {label} source fact is missing")
    values = {_number(row.get("value"), f"current {label} value") for row in rows}
    if len(values) != 1:
        raise ShareBasisReviewRequired(f"current {label} source facts are ambiguous")
    if len({(row.get('period_start'),row.get('period_end')) for row in rows})!=1:
        raise ShareBasisReviewRequired(f"current {label} periods are ambiguous")
    return deepcopy(rows[0])


def _current_report_fields(packet: Mapping[str, Any], *, report_period_end: str, cutoff: str) -> tuple[str, str, str, str | None]:
    controlling = packet.get("controlling_filing")
    if not isinstance(controlling, Mapping):
        raise ShareBasisReviewRequired("current controlling filing metadata is missing")
    accession = str(controlling.get("accessionNumber") or controlling.get("accession") or "")
    form = str(controlling.get("form") or "")
    filing_date = controlling.get("filingDate") or controlling.get("filed")
    if not accession or not form or not isinstance(filing_date, str) or not filing_date:
        raise ShareBasisReviewRequired("current controlling filing identity is incomplete")
    if form not in {'10-K','10-K/A','10-Q','10-Q/A'} or controlling.get('reportDate')!=report_period_end:
        raise ShareBasisReviewRequired('unsupported share filing form or report period mismatch')
    _iso_date(report_period_end, "current report period")
    cutoff_date = _iso_date(cutoff, "cutoff")
    if filing_date is not None and _iso_date(str(filing_date), "filing date") > cutoff_date:
        raise ShareBasisReviewRequired("current filing is after cutoff")
    return accession, form, report_period_end, str(filing_date) if filing_date is not None else None


def bind_current_share_basis(
    profile: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    ticker: str,
    cik: str,
    accession: str,
    report_period_end: str,
    cutoff: str,
) -> dict[str, Any]:
    """Bind a compiled share profile to one complete, identity-checked packet."""

    if profile.get("schema_version") != "FINSIGHT-SHARE-BASIS-1" or profile.get("ticker") != ticker:
        raise ShareBasisReviewRequired("share profile identity or schema mismatch")
    expected_cik = _cik(cik)
    if profile.get("cik") != expected_cik or _SHARE_PROFILE_CIKS.get(ticker) != expected_cik:
        raise ShareBasisReviewRequired("share profile CIK does not match issuer")
    if _packet_cik(packet) not in (None, expected_cik):
        raise ShareBasisReviewRequired("current packet CIK does not match issuer")
    for packet_field in ("submissions", "companyfacts"):
        source = packet.get(packet_field)
        if isinstance(source, Mapping) and source.get("cik") is not None and _cik(source.get("cik")) != expected_cik:
            raise ShareBasisReviewRequired(f"current {packet_field} CIK does not match issuer")
    accession_meta, form, period, filing_date = _current_report_fields(packet, report_period_end=report_period_end, cutoff=cutoff)
    if accession_meta != accession:
        raise ShareBasisReviewRequired("current controlling accession mismatch")
    structural = _current_structural(packet)
    metadata=dict(structural.get('filing_metadata',()))
    if metadata.get('manifest_version')!='FINSIGHT-XBRL-PACKAGE-1' or not metadata.get('package_generation'):
        raise ShareBasisReviewRequired('complete structural package is required for share selection')
    if structural.get("source_accession") != accession:
        raise ShareBasisReviewRequired("current structural accession mismatch")
    if structural.get("report_date") != period or structural.get('form')!=form:
        raise ShareBasisReviewRequired("current structural period mismatch")
    facts = structural.get("facts", [])
    fact_ciks = {str(row.get("entity_identifier", "")).zfill(10) for row in facts if isinstance(row, Mapping) and row.get("entity_identifier") is not None}
    if fact_ciks != {expected_cik}:
        raise ShareBasisReviewRequired("current structural facts do not have complete issuer identity")
    weighted = _current_rows(
        structural,
        local_name="WeightedAverageNumberOfDilutedSharesOutstanding",
        unit=("shares", "xbrli:shares"),
        cik=expected_cik,
        accession=accession,
        report_period_end=period,
        filed_date=filing_date,
    )
    weighted = [row for row in weighted if row.get("period_start") and row.get("period_end") == period]
    if form.upper() in {"10-Q", "10-Q/A"}:
        annual = packet.get("latest_annual_filing")
        annual_end = annual.get("reportDate") if isinstance(annual, Mapping) else None
        if not isinstance(annual_end, str):
            raise ShareBasisReviewRequired("latest annual period is required for interim YTD share selection")
        expected_start = _iso_date(annual_end, "latest annual period") + timedelta(days=1)
        weighted = [row for row in weighted if row.get("period_start") == expected_start.isoformat()]
    else:
        current_end = _iso_date(period, "current report period")
        annual_rows = []
        for row in weighted:
            start = row.get("period_start")
            if not isinstance(start, str):
                continue
            days = (current_end - _iso_date(start, "weighted share period start")).days + 1
            if 350 <= days <= 380:
                annual_rows.append(row)
        weighted = annual_rows
    weighted_row = _unique_current(weighted, label="YTD weighted-diluted shares")
    weighted_value = _number(weighted_row.get("value"), "current weighted-diluted shares")
    if profile.get("profile") == SHARE_PROFILE_BBY:
        factors = profile.get("sensitivity_factors")
        if not isinstance(factors, Mapping):
            raise ShareBasisReviewRequired("BBY share sensitivity factors are missing")
        scenario_shares = {name: weighted_value * _number(factors.get(name), f"{name} share factor") for name in _SHARE_SCENARIOS}
        return {
            "status": "verified",
            "profile": profile["profile"],
            "ticker": ticker,
            "cik": expected_cik,
            "base_shares": weighted_value,
            "scenario_shares": scenario_shares,
            "sources": {"reported_ytd_weighted_diluted": weighted_row},
            "limitations": list(profile.get("limitations", ())),
        }
    cover = _current_rows(
        structural,
        local_name="EntityCommonStockSharesOutstanding",
        unit="xbrli:shares",
        cik=expected_cik,
        accession=accession,
        report_period_end=period,
        filed_date=filing_date,
    )
    cover = [
        row for row in cover
        if row.get("period_start") is None
        and re.fullmatch(r"http://xbrl\.sec\.gov/dei/\d{4}", str(row.get("namespace", "")))
        and row.get("qname") == _canonical_qname(str(row.get("namespace")), "EntityCommonStockSharesOutstanding")
        and isinstance(row.get("period_end"), str)
        and _iso_date(row["period_end"], "cover share period") >= _iso_date(period, "current report period")
        and _iso_date(row["period_end"], "cover share period") <= _iso_date(cutoff, "cutoff")
        and _iso_date(row["period_end"], "cover share period") <= _iso_date(filing_date, "filing date")
    ]
    if not cover:
        raise ShareBasisReviewRequired("current cover common-share source fact is missing")
    latest_period = max(_iso_date(row["period_end"], "cover share period") for row in cover)
    cover = [row for row in cover if _iso_date(row["period_end"], "cover share period") == latest_period]
    cover_row = _unique_current(cover, label="cover common shares")
    cover_value = _number(cover_row.get("value"), "current cover common shares")
    if weighted_value < cover_value:
        raise ShareBasisReviewRequired("current weighted-diluted and cover share order reversed")
    base_value = (weighted_value + cover_value) / 2.0
    return {
        "status": "verified",
        "profile": profile["profile"],
        "ticker": ticker,
        "cik": expected_cik,
        "base_shares": base_value,
        "scenario_shares": {"bear": weighted_value, "base": base_value, "bull": cover_value},
        "sources": {"reported_ytd_weighted_diluted": weighted_row, "reported_cover": cover_row},
        "limitations": list(profile.get("limitations", ())),
    }


def bind_share_basis(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility alias for the explicit current share-basis binder."""

    return bind_current_share_basis(*args, **kwargs)


__all__ = [
    "ShareBasisReviewRequired",
    "resolve_class_equivalent_share_basis",
    "SHARE_PROFILE_BBY",
    "SHARE_PROFILE_REPORTED_YTD_AND_COVER",
    "compile_share_basis_profile",
    "bind_current_share_basis",
    "bind_share_basis",
]
