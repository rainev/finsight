"""Accession-bound review contracts for non-routine SEC current reports.

Routine current-report items remain governed by the family policy.  A reviewed
event is a narrower exception: the policy must identify the exact accession,
form, item set, filing date, primary document, and captured source hashes.  No
wildcards or item-only approvals are accepted here.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping


class EventReviewError(ValueError):
    """The policy does not match the issuer's captured filing identity."""


class EventReviewIncomplete(RuntimeError):
    """The reviewed filing's captured source provenance is incomplete."""


def _iso(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise EventReviewError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise EventReviewError(f"{field} must be an ISO date") from exc


def _items(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise EventReviewError(f"{field} must be a non-empty exact item list")
    result = tuple(str(item).strip() for item in value)
    if any(not item or item in {"*", "all", "ALL"} for item in result):
        raise EventReviewError(f"{field} cannot contain wildcard items")
    if len(set(result)) != len(result):
        raise EventReviewError(f"{field} cannot contain duplicate items")
    return tuple(sorted(result))


def _record_value(record: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = record.get(name)
        if value is not None:
            return value
    return None


def _sources(event: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = event.get("document_sources")
    if not isinstance(rows, list):
        raise EventReviewIncomplete("reviewed event document provenance is missing")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise EventReviewIncomplete("reviewed event document provenance is invalid")
        role = row.get("role")
        if role in {"primary_filing", "complete_submission"}:
            if role in result:
                raise EventReviewIncomplete(f"reviewed event has duplicate {role} sources")
            result[str(role)] = row
    for role in ("primary_filing", "complete_submission"):
        if role not in result:
            raise EventReviewIncomplete(f"reviewed event {role} source is missing")
    return result


def _source_identity(source: Mapping[str, Any], role: str) -> tuple[str, str]:
    name, digest = source.get("name"), source.get("sha256")
    if not isinstance(name, str) or not name:
        raise EventReviewIncomplete(f"reviewed event {role} source name is missing")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        raise EventReviewIncomplete(f"reviewed event {role} source hash is missing or invalid")
    return name, digest.lower()


def _validate_reviewed_event(
    *,
    record: Mapping[str, Any],
    captured: Mapping[str, Any] | None,
    rule: Mapping[str, Any],
    prior_cutoff: str,
    cutoff: str,
    accession: str,
    require_exhibits: bool,
) -> dict[str, Any]:
    if captured is None:
        raise EventReviewIncomplete(f"reviewed event {accession} capture is missing")
    if not isinstance(rule.get("form"), str) or rule["form"] != record.get("form"):
        raise EventReviewError(f"reviewed event {accession} form does not match")
    rule_items = _items(rule.get("items"), f"reviewed event {accession} items")
    record_items = _items(
        record.get("items") if isinstance(record.get("items"), list) else str(record.get("items", "")).split(","),
        f"captured event {accession} items",
    )
    captured_items = _items(captured.get("items"), f"captured event {accession} items")
    if rule_items != record_items or rule_items != captured_items:
        raise EventReviewError(f"reviewed event {accession} item set does not match")
    filed = _iso(_record_value(record, "filingDate", "filed"), f"event {accession} filing date")
    if _iso(rule.get("filed"), f"reviewed event {accession} filed") != filed:
        raise EventReviewError(f"reviewed event {accession} filing date does not match")
    if not (_iso(prior_cutoff, "prior cutoff") < filed <= _iso(cutoff, "cutoff")):
        raise EventReviewError(f"reviewed event {accession} is outside the refresh window")
    if _iso(rule.get("cutoff"), f"reviewed event {accession} cutoff") != _iso(cutoff, "cutoff"):
        raise EventReviewError(f"reviewed event {accession} cutoff does not match")
    primary_document = _record_value(record, "primaryDocument", "primary_document")
    captured_document = _record_value(captured, "primaryDocument", "primary_document")
    if not isinstance(rule.get("primary_document"), str) or rule["primary_document"] != primary_document or captured_document != primary_document:
        raise EventReviewError(f"reviewed event {accession} primary document does not match")
    if captured.get("accession") != accession:
        raise EventReviewError(f"reviewed event {accession} capture accession does not match")
    record_report_date = _record_value(record, "reportDate", "report_date")
    captured_report_date = _record_value(captured, "report_date", "reportDate")
    if captured.get("form") != record.get("form") or _iso(captured.get("filed_date"), f"captured event {accession} filing date") != filed:
        raise EventReviewError(f"reviewed event {accession} capture identity does not match")
    if isinstance(record_report_date, str) and isinstance(captured_report_date, str) and record_report_date != captured_report_date:
        raise EventReviewError(f"reviewed event {accession} report date does not match")

    sources = _sources(captured)
    primary_name, primary_hash = _source_identity(sources["primary_filing"], "primary filing")
    complete_name, complete_hash = _source_identity(sources["complete_submission"], "complete submission")
    if primary_name != primary_document or primary_hash != str(rule.get("primary_sha256", "")).lower():
        raise EventReviewError(f"reviewed event {accession} primary source hash does not match")
    if complete_name != str(rule.get("complete_submission_document", "")) or complete_hash != str(rule.get("complete_submission_sha256", "")).lower():
        raise EventReviewError(f"reviewed event {accession} complete submission hash does not match")

    primary_only_allowed = rule.get("primary_only_allowed", False)
    if not isinstance(primary_only_allowed, bool):
        raise EventReviewError(f"reviewed event {accession} primary_only_allowed must be boolean")
    attachments = captured.get("attachments")
    if primary_only_allowed:
        if not isinstance(attachments, list) or attachments:
            raise EventReviewError(f"reviewed event {accession} primary-only rule requires no attachments")
    elif captured.get("relationships_status") != "exhibit_relationships_captured":
        if require_exhibits:
            raise EventReviewIncomplete(f"reviewed event {accession} is missing verified exhibit relationships or attachment bodies")
        raise EventReviewIncomplete(f"reviewed event {accession} has absent exhibits without primary-only approval")

    treatment = rule.get("treatment")
    if not isinstance(treatment, str) or not treatment.strip():
        raise EventReviewError(f"reviewed event {accession} treatment is missing")
    limitations = rule.get("limitations", [])
    if not isinstance(limitations, list) or not all(isinstance(item, str) and item.strip() for item in limitations):
        raise EventReviewError(f"reviewed event {accession} limitations must be strings")
    return {
        "accession": accession,
        "form": record.get("form"),
        "items": list(rule_items),
        "filed": filed,
        "cutoff": _iso(cutoff, "cutoff"),
        "primary_document": primary_document,
        "primary_sha256": primary_hash,
        "complete_submission_document": complete_name,
        "complete_submission_sha256": complete_hash,
        "primary_only_allowed": primary_only_allowed,
        "treatment": treatment,
        "limitations": list(limitations),
    }


def review_event_records(
    records: list[Mapping[str, Any]],
    captured_events: list[Mapping[str, Any]],
    policy: Mapping[str, Any],
    *,
    prior_cutoff: str,
    cutoff: str,
    require_exhibits: bool,
    controlling_filing: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate new current reports and return the reviewed-event ledger rows."""
    prior_cutoff = _iso(prior_cutoff, "prior cutoff")
    cutoff = _iso(cutoff, "cutoff")
    routine = set(_items(policy.get("routine_8k_items", ["2.02", "9.01"]), "routine_8k_items"))
    rules = policy.get("reviewed_events", {})
    if rules is None:
        rules = {}
    if not isinstance(rules, Mapping):
        raise EventReviewError("reviewed_events must be an accession-keyed mapping")
    captured_by_accession = {
        str(event.get("accession")): event
        for event in captured_events
        if isinstance(event, Mapping) and isinstance(event.get("accession"), str)
    }
    reviewed: list[dict[str, Any]] = []
    for record in records:
        form = record.get("form")
        filed_value = _record_value(record, "filingDate", "filed")
        if form not in {"8-K", "8-K/A"} or not isinstance(filed_value, str):
            continue
        filed = _iso(filed_value, "event filing date")
        if not prior_cutoff < filed <= cutoff:
            continue
        accession = _record_value(record, "accessionNumber", "accession")
        if not isinstance(accession, str) or not accession:
            raise EventReviewError("new corporate-event filing accession is missing")
        rule = rules.get(accession)
        record_items = _items(
            record.get("items") if isinstance(record.get("items"), list) else str(record.get("items", "")).split(","),
            f"captured event {accession} items",
        )
        if rule is not None:
            if not isinstance(rule, Mapping):
                raise EventReviewError(f"reviewed event {accession} rule is invalid")
            reviewed.append(_validate_reviewed_event(
                record=record,
                captured=captured_by_accession.get(accession),
                rule=rule,
                prior_cutoff=prior_cutoff,
                cutoff=cutoff,
                accession=accession,
                require_exhibits=require_exhibits,
            ))
            continue
        if policy.get('supersede_financial_events_by_controlling_filing') is True:
            control_filed=_record_value(controlling_filing or {},'filingDate','filed')
            control_period=_record_value(controlling_filing or {},'reportDate','report_date')
            financial_items={'2.02','7.01','8.01','9.01'}
            captured=captured_by_accession.get(accession)
            if ('2.02' in record_items and set(record_items)<=financial_items
                and isinstance(control_filed,str) and filed<=_iso(control_filed,'controlling filing date')
                and isinstance(control_period,str) and _iso(control_period,'controlling report period')<=filed):
                if not captured or captured.get('relationships_status')!='exhibit_relationships_captured':
                    raise EventReviewIncomplete('superseded financial event lacks verified primary/exhibit relationships')
                reviewed.append({'accession':accession,'form':form,'items':list(record_items),'filed':filed,
                    'cutoff':cutoff,'primary_document':_record_value(record,'primaryDocument','primary_document'),
                    'primary_sha256':_sources(captured)['primary_filing']['sha256'],
                    'complete_submission_document':_sources(captured)['complete_submission']['name'],
                    'complete_submission_sha256':_sources(captured)['complete_submission']['sha256'],
                    'primary_only_allowed':False,
                    'treatment':'Historical earnings inputs superseded by the later controlling regular filing; forward guidance remains outside reported inputs.',
                    'limitations':['Forward guidance and non-GAAP measures in the event are not inserted into historical source facts. Reassess if the event describes a transaction or balance not reflected in the controlling filing.']})
                continue
        if not record_items or set(record_items) - routine:
            raise EventReviewError("new corporate-event filing requires an approved event rule")
        if require_exhibits:
            captured = captured_by_accession.get(accession)
            if not captured or captured.get("relationships_status") != "exhibit_relationships_captured":
                raise EventReviewIncomplete("new event filing is missing verified exhibit relationships or attachment bodies")
    return reviewed
