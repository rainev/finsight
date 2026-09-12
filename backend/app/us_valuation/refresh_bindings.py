"""Declarative, fail-closed refresh bindings for approved calculation recipes.

Bindings contain field selectors and arithmetic, never Python or AI instructions.
They are versioned policy inputs; changing them requires policy review.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import hashlib
import json
import re
from math import isfinite, isclose
from statistics import median
from typing import Any, Mapping

from .calculation_recipe import number, evaluate_recipe
from .refresh_financials import cash_history, normalized_bridge, bridge_assessment
from .xbrl import CompanyFactsNormalizer, load_concept_config
from .sec_client import normalize_cik
from .sustainable_inputs import (
    BoundedAdjustment,
    SourceEvidence,
    normalize_reported_value,
    resolve_total_capex,
    validate_source_evidence,
)


class EconomicException(ValueError):
    pass


class AcquisitionIncomplete(RuntimeError):
    """New filing evidence was not retrieved; do not invalidate prior economics."""


def _iso(value: object, field: str) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise EconomicException(f"{field} must be an ISO date") from exc


def _source_evidence(
    selected: Mapping[str, Any], *, cik: str, field: str, cutoff: str, value: float
) -> SourceEvidence:
    """Convert a normalized selected row into the sustainable-input contract."""
    source_rows = _selected_source_rows(selected)
    derived = len(source_rows) > 1
    if not (selected.get("accession") or selected.get("accn")):
        if not source_rows:
            raise EconomicException(f"{field}: selected source lineage is incomplete")
        selected = max(source_rows, key=lambda row: str(row.get("filed") or row.get("filed_date") or ""))
    accession = selected.get("accession") or selected.get("accn")
    filed = selected.get("filed") or selected.get("filed_date")
    period_end = selected.get("end") or selected.get("period_end")
    if not all(isinstance(item, str) and item for item in (accession, filed, period_end)):
        raise EconomicException(f"{field}: selected source lineage is incomplete")
    try:
        source = SourceEvidence(
            source_id=str(accession),
            cik=cik,
            field=field,
            unit=str(selected.get("unit") or "USD"),
            reported_value=value,
            period_end=str(period_end),
            filing_date=str(filed),
            reported_vs_estimated="derived_reported" if derived else "reported",
        )
        validate_source_evidence(source, cutoff)
        return source
    except ValueError as exc:
        raise EconomicException(f"{field}: source evidence failed validation: {exc}") from exc


def _selected_source_rows(selected: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    rows = selected.get("sources")
    if isinstance(rows, list):
        return tuple(row for row in rows if isinstance(row, Mapping))
    return (selected,)


def _check_selected_period(
    name: str, selected: Mapping[str, Any], *, expected_period: str, cutoff: str
) -> None:
    actual_period = selected.get("period_end") or selected.get("end")
    if actual_period != expected_period:
        raise EconomicException(f"{name}: mismatched current flow period")
    for source in _selected_source_rows(selected):
        source_end = source.get("end") or source.get("period_end")
        source_filed = source.get("filed") or source.get("filed_date")
        if isinstance(source_end, str) and _iso(source_end, f"{name} source period") > cutoff:
            raise EconomicException(f"{name}: source period is after frozen cutoff")
        if isinstance(source_filed, str) and _iso(source_filed, f"{name} source filing") > cutoff:
            raise EconomicException(f"{name}: source filing is after frozen cutoff")


def _fact_count(companyfacts: Mapping[str, Any], accession: str) -> int:
    facts = companyfacts.get("facts", {})
    count = 0
    if not isinstance(facts, Mapping):
        return count
    for namespace in facts.values():
        if not isinstance(namespace, Mapping):
            continue
        for concept in namespace.values():
            units = concept.get("units", {}) if isinstance(concept, Mapping) else {}
            if not isinstance(units, Mapping):
                continue
            for rows in units.values():
                if isinstance(rows, list):
                    count += sum(1 for row in rows if isinstance(row, Mapping) and row.get("accn") == accession)
    return count


def _field_has_fact(
    companyfacts: Mapping[str, Any],
    *,
    field: str,
    accession: str,
    period: str,
    kind: str,
    concept_config: Mapping[str, Any],
) -> bool:
    definition = concept_config.get("fields", {}).get(field, {})
    concepts = definition.get("concepts", ()) if isinstance(definition, Mapping) else ()
    expected_unit = definition.get("unit") if isinstance(definition, Mapping) else None
    facts = companyfacts.get("facts", {})
    if not isinstance(facts, Mapping):
        return False
    for reference in concepts:
        if not isinstance(reference, str):
            continue
        namespace, local = reference.split(":", 1) if ":" in reference else ("us-gaap", reference)
        rows = facts.get(namespace, {}).get(local, {}).get("units", {}).get(expected_unit, []) if isinstance(facts.get(namespace), Mapping) else []
        for row in rows if isinstance(rows, list) else ():
            if row.get("accn") != accession or row.get("end") != period:
                continue
            if kind == "flow" and not row.get("start"):
                continue
            if kind == "instant" and row.get("start") is not None:
                continue
            if isinstance(row.get("val"), (int, float)) and not isinstance(row.get("val"), bool) and isfinite(row['val']):
                return True
    return False


def _structural_facts(packet: Mapping[str, Any] | None) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(packet, Mapping):
        return ()
    facts = packet.get("facts")
    return tuple(row for row in facts if isinstance(row, Mapping)) if isinstance(facts, list) else ()


def _select_complete_filings(
    records: list[dict[str, Any]],
    companyfacts: Mapping[str, Any],
    structural_packet: Mapping[str, Any] | None,
    *,
    cutoff: str,
    required_fields: Mapping[str, str],
    concept_config: Mapping[str, Any],
    structural_packets: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select filings with evidence payloads, avoiding metadata-only amendments."""
    eligible = [
        row for row in records
        if row.get("form") in {"10-K", "10-K/A", "10-Q", "10-Q/A"}
        and isinstance(row.get("filingDate"), str)
        and row["filingDate"] <= cutoff
        and isinstance(row.get("reportDate"), str)
        and isinstance(row.get("accessionNumber"), str)
    ]
    scored = []
    for row in eligible:
        accession = row["accessionNumber"]
        period = row["reportDate"]
        filing_structural = (structural_packets or {}).get(accession)
        if filing_structural is None and isinstance(structural_packet, Mapping) and structural_packet.get('source_accession') == accession:
            filing_structural = structural_packet
        structural_count = len(_structural_facts(filing_structural))
        coverage = {
            field: _field_has_fact(companyfacts, field=field, accession=accession, period=period, kind=kind, concept_config=concept_config)
            for field, kind in required_fields.items()
        }
        flow_present = any(coverage.get(field) for field, kind in required_fields.items() if kind == "flow")
        instant_present = any(coverage.get(field) for field, kind in required_fields.items() if kind == "instant")
        score = _fact_count(companyfacts, accession) if all(coverage.values()) and flow_present and instant_present else 0
        if isinstance(filing_structural, Mapping) and filing_structural.get('source_accession') == accession:
            def structural_matches(field, kind):
                definition = concept_config.get('fields', {}).get(field, {})
                concepts = {name if ':' in name else f'us-gaap:{name}' for name in definition.get('concepts', ())}
                units = {definition.get('unit')}
                if definition.get('unit') == 'shares': units.add('xbrli:shares')
                for fact in _structural_facts(filing_structural):
                    if (fact.get('period_end') != period or fact.get('dimensions') or fact.get('qname') not in concepts
                        or fact.get('unit') not in units or fact.get('source_accession',accession) != accession):
                        continue
                    start = fact.get('period_start')
                    if (kind == 'instant' and start is not None) or (kind == 'flow' and (not isinstance(start,str) or start >= period)):
                        continue
                    try:
                        if normalize_cik(fact.get('entity_identifier','')) != normalize_cik(companyfacts['cik']): continue
                    except ValueError:
                        continue
                    value = fact.get('value')
                    if isinstance(value,(int,float)) and not isinstance(value,bool) and isfinite(value): return True
                return False
            structural_coverage = {
                field: structural_matches(field,kind)
                for field,kind in required_fields.items()
            }
            if all(coverage[field] or structural_coverage.get(field, False) for field in required_fields):
                score += structural_count
        if score:
            scored.append((score, row))
    if not scored:
        raise EconomicException("no complete eligible filing evidence")
    regular = [row for row in eligible if row['form'] in {'10-K','10-Q'}]
    latest_eligible = max(regular or eligible, key=lambda row: (row["reportDate"], row["filingDate"], row["accessionNumber"]))
    complete_accessions = {row["accessionNumber"] for _, row in scored}
    complete_replacement = any(row['reportDate'] == latest_eligible['reportDate'] and row['filingDate'] >= latest_eligible['filingDate'] for _, row in scored)
    if latest_eligible["form"] in {"10-K", "10-Q"} and latest_eligible["accessionNumber"] not in complete_accessions and not complete_replacement:
        raise AcquisitionIncomplete("latest eligible regular filing lacks complete source evidence")
    controlling = max((row for _, row in scored), key=lambda row: (row["reportDate"], row["filingDate"], row["accessionNumber"]))
    annual = [row for _, row in scored if row["form"] in {"10-K", "10-K/A"}]
    if not annual:
        raise EconomicException("no complete eligible annual filing evidence")
    latest_annual = max(annual, key=lambda row: (row["reportDate"], row["filingDate"], row["accessionNumber"]))
    return controlling, latest_annual


def _structural_selected(
    packet: Mapping[str, Any] | None,
    *,
    name: str,
    concept: str,
    period: str,
    controlling: Mapping[str, Any],
    cik: str,
    cutoff: str,
    expected_unit: str | None,
    period_kind: str | None,
    period_start: str | None = None,
) -> tuple[float, dict[str, Any]]:
    if not isinstance(packet, Mapping):
        raise AcquisitionIncomplete(f"{name}: structural evidence packet is unavailable")
    if ":" not in concept or not expected_unit or period_kind not in {"instant", "duration"}:
        raise EconomicException(f"{name}: structural selector requires full concept, expected unit, and period kind")
    if period_kind == 'duration' and (period_start is None or _iso(period_start, 'period_start') >= period):
        raise EconomicException(f'{name}: structural duration needs an exact start date')
    if packet.get("source_accession") != controlling.get("accessionNumber"):
        raise EconomicException(f"{name}: structural packet accession does not match controlling filing")
    packet_period = packet.get("report_date") or packet.get("period_end")
    if packet_period != period:
        raise EconomicException(f"{name}: structural packet period does not match controlling filing")
    facts = [
        row for row in _structural_facts(packet)
        if row.get("period_end") == period
        and not row.get("dimensions")
        and row.get("qname") == concept
        and row.get("unit") == expected_unit
        and ((period_kind == "instant" and row.get("period_start") is None) or (period_kind == "duration" and row.get("period_start") == period_start))
        and isinstance(row.get("value"), (int, float))
        and not isinstance(row.get("value"), bool)
    ]
    values = {float(row["value"]) for row in facts}
    if len(values) != 1:
        raise EconomicException(f"{name}: structural concept has no unique exact value")
    row = facts[0]
    entity_identifier = row.get("entity_identifier")
    if not isinstance(entity_identifier, str):
        raise EconomicException(f"{name}: structural fact entity identifier is missing")
    try:
        fact_cik = normalize_cik(entity_identifier)
    except ValueError as exc:
        raise EconomicException(f"{name}: structural fact entity identifier is invalid") from exc
    if fact_cik != normalize_cik(cik):
        raise EconomicException(f"{name}: structural fact entity identifier does not match issuer")
    source = {
        "source_kind": "structural_xbrl",
        "source_accession": controlling["accessionNumber"],
        "cik": fact_cik,
        "concept": row.get("qname", row.get("local_name")),
        "unit": row.get("unit"),
        "value": values.pop(),
        "period_start": row.get("period_start"),
        "period_end": row.get("period_end"),
        "filing_date": controlling.get("filingDate"),
        "packet_sha256": hashlib.sha256(json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    return source["value"], source


def _required_statement_fields(policy: Mapping[str, Any], concept_config: Mapping[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for rule in policy.get("inputs", {}).values():
        if not isinstance(rule, Mapping):
            continue
        selector = rule.get("selector")
        field = rule.get("field")
        if isinstance(field, str) and field in concept_config.get("fields", {}):
            kind = concept_config["fields"][field].get("kind")
            # Bridge components have their own evidence/absence reconciliation.
            # Requiring every preferred/NCI tag here rejects a complete filing
            # before its structural zero or component proof can be evaluated.
            if kind in {"flow", "instant"} and selector in {'ttm', 'instant', 'total_capex'}:
                fields[field] = kind
        if selector == "tax_rate":
            fields["income_tax"] = "flow"
            fields["pretax_income"] = "flow"
    if not any(kind == "flow" for kind in fields.values()):
        fields["operating_cash_flow"] = "flow"
    if not any(kind == "instant" for kind in fields.values()):
        # Filing completeness is not a cash-concept decision. Cash may be
        # reported with an issuer alias or restricted-cash reconciliation;
        # those remain subject to the independent normalized bridge gate.
        fields["total_assets"] = "instant"
    return fields


def _selected_value(
    normalizer: CompanyFactsNormalizer,
    *,
    name: str,
    field: str,
    selector: str,
    period: str,
    cutoff: str,
    cik: str,
    controlling_accession: str | None = None,
    controlling: Mapping[str, Any] | None = None,
    structural_packet: Mapping[str, Any] | None = None,
    expected_unit: str | None = None,
    period_kind: str | None = None,
    period_start: str | None = None,
) -> tuple[float, dict[str, Any]]:
    if selector == "ttm":
        selected = normalizer.ttm_flow(field)
        _check_selected_period(name, selected, expected_period=period, cutoff=cutoff)
        value = number(selected["value"], name)
        source = _source_evidence(selected, cik=cik, field=field, cutoff=cutoff, value=value)
        return value, {"selected": selected, "source": source.as_dict()}
    if selector == "instant":
        selected = normalizer.instant(field, end=period)
        if selected is None or selected.accession == "":
            raise EconomicException(f"{name}: current controlling balance not reported")
        if controlling_accession is not None and selected.accession != controlling_accession:
            raise EconomicException(f"{name}: current balance is not from controlling filing")
        selected_dict = selected.as_dict()
        _check_selected_period(name, selected_dict, expected_period=period, cutoff=cutoff)
        value = number(selected.value, name)
        source = _source_evidence(selected_dict, cik=cik, field=field, cutoff=cutoff, value=value)
        return value, {"selected": selected_dict, "source": source.as_dict()}
    if selector == "history_median":
        selected = normalizer.annual_series(field, 5)
        if len(selected) < 3:
            raise EconomicException(f"{name}: fewer than three comparable annual periods")
        rows = tuple(row.as_dict() for row in selected)
        for row in rows:
            _check_selected_period(name, {"period_end": row["end"], "sources": [row]}, expected_period=row["end"], cutoff=cutoff)
        value = median(row.value for row in selected)
        return value, {"selected": rows, "value": value}
    if selector == "structural":
        value, source = _structural_selected(
            structural_packet,
            name=name,
            concept=field,
            period=period,
            controlling=controlling or {},
            cik=cik,
            cutoff=cutoff,
            expected_unit=expected_unit,
            period_kind=period_kind,
            period_start=period_start,
        )
        return number(value, name), {"selected": source, "source": source}
    raise RuntimeError("unsupported configured source selector")


def arithmetic(node: Any, values: dict[str, float]) -> float:
    if isinstance(node, str):
        if node not in values:
            raise EconomicException(f'missing required input: {node}')
        return values[node]
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return number(node, 'policy constant')
    if not isinstance(node, dict) or len(node) != 1:
        raise EconomicException('invalid binding expression')
    op, args = next(iter(node.items()))
    if not isinstance(args, list) or len(args) != 2:
        raise EconomicException('binding operations require two arguments')
    left, right = (arithmetic(arg, values) for arg in args)
    if op == 'add': result = left + right
    elif op == 'subtract': result = left - right
    elif op == 'multiply': result = left * right
    elif op == 'divide' and right != 0: result = left / right
    elif op == 'min': result = min(left,right)
    elif op == 'max': result = max(left,right)
    else: raise EconomicException('invalid binding operation or zero denominator')
    return number(result, 'binding result')


def bind_current_recipe(entry: dict, recipe: dict, packet: dict, cutoff: str) -> tuple[dict, dict]:
    """Resolve all source-dependent inputs before computing a new recipe.

    Unsupported aliases, periods, claims, and material filing events are explicit
    exceptions. A non-migrated policy is a deployment error, not an issuer failure.
    """
    policy = entry.get('refresh_policy')
    if not isinstance(policy, dict) or not policy.get('version'):
        raise RuntimeError('refresh binding policy has not been migrated')
    if recipe.get('ticker') != entry.get('ticker') or policy.get('ticker',entry.get('ticker')) != entry.get('ticker'):
        raise RuntimeError('refresh recipe/policy ticker does not match the frozen registry')
    if policy.get('cik') is not None and normalize_cik(policy['cik']) != normalize_cik(entry['cik']):
        raise RuntimeError('refresh policy CIK does not match the frozen registry')
    cutoff = _iso(cutoff, "cutoff")
    submissions, companyfacts = packet['submissions'], packet['companyfacts']
    structural_packet = packet.get('structural_filing') or packet.get('structural') or packet.get('structural_packet')
    structural_packets = packet.get('structural_packets', {})
    cik = normalize_cik(entry['cik'])
    if normalize_cik(submissions['cik']) != cik or normalize_cik(companyfacts['cik']) != cik:
        raise EconomicException('issuer identity conflict')
    recent = submissions['filings']['recent']
    records = [{key: vals[i] for key, vals in recent.items() if isinstance(vals, list) and i < len(vals)} for i in range(len(recent['accessionNumber']))]
    concept_config = policy.get('concept_config') if isinstance(policy.get('concept_config'), Mapping) else load_concept_config()
    required_fields = policy.get('statement_required_fields') or _required_statement_fields(policy, concept_config)
    controlling, latest_annual = _select_complete_filings(
        records,
        companyfacts,
        structural_packet,
        cutoff=cutoff,
        required_fields=required_fields,
        concept_config=concept_config,
        structural_packets=structural_packets,
    )
    period = controlling['reportDate']
    prior_cutoff = _iso(recipe['evidence_cutoff'], "recipe evidence_cutoff")
    if prior_cutoff > cutoff:
        raise EconomicException('recipe evidence cutoff is after refresh cutoff')
    if isinstance(structural_packets.get(controlling['accessionNumber']), Mapping):
        structural_packet = structural_packets[controlling['accessionNumber']]
    elif isinstance(structural_packet, Mapping) and structural_packet.get('source_accession') != controlling['accessionNumber']:
        if structural_packet.get('source_accession') not in {row.get('accessionNumber') for row in records}:
            raise AcquisitionIncomplete('structural packet accession does not match an eligible issuer filing')
        structural_packet = None
    if policy.get('source_requirements', {}).get('structural'):
        if structural_packet is None:
            raise AcquisitionIncomplete('selected controlling filing structural body is missing')
        for amendment in records:
            if amendment.get('form') not in {'10-K/A','10-Q/A'} or not prior_cutoff < amendment.get('filingDate','') <= cutoff:
                continue
            same_period = [filing for filing in (controlling,latest_annual) if filing['reportDate'] == amendment.get('reportDate')]
            if not same_period:
                raise EconomicException('new amendment outside supported financial periods requires scope review')
            if amendment['accessionNumber'] not in structural_packets and structural_packet.get('source_accession') != amendment['accessionNumber']:
                raise AcquisitionIncomplete('new amendment structural body is missing')
            if not any(filing['filingDate'] >= amendment['filingDate'] for filing in same_period):
                raise EconomicException('new amendment requires explicit financial-scope review')
    packet = {**packet,'structural_filing':structural_packet,'controlling_filing':controlling,'latest_annual_filing':latest_annual}
    if packet.get('narrative_evidence') is not None:
        if not isinstance(packet['narrative_evidence'],dict) or not isinstance(structural_packet,dict):
            raise AcquisitionIncomplete('narrative evidence requires the current structural filing')
        structural_packet={**structural_packet,'narrative_evidence':packet['narrative_evidence']}
        packet['structural_filing']=structural_packet
    if packet.get('normalization_review_required'):
        raise EconomicException(str(packet['normalization_review_required']))
    allowed_items = set(policy.get('routine_8k_items', ['2.02','9.01']))
    captured_events = {event.get('accession'):event for event in packet.get('events', []) if isinstance(event, dict)}
    for event in records:
        if event.get('form') in {'8-K','8-K/A'} and prior_cutoff < event.get('filingDate','') <= cutoff:
            items = {item.strip() for item in str(event.get('items', '')).split(',') if item.strip()}
            if not items or items - allowed_items:
                raise EconomicException('new corporate-event filing requires an approved event rule')
            if policy.get('source_requirements', {}).get('event_exhibits'):
                captured = captured_events.get(event['accessionNumber'])
                if not captured or captured.get('relationships_status') != 'exhibit_relationships_captured':
                    raise AcquisitionIncomplete('new event filing is missing verified exhibit relationships or attachment bodies')
    if policy.get('schema_version') == 'FINSIGHT-ASSET-RUNWAY-REFRESH-POLICY-1':
        from .refresh_runway_policy import bind_mrna_runway_sources
        try:
            refreshed,ledger = bind_mrna_runway_sources(policy,recipe,{**packet,'_selected_controlling_filing':controlling},
                structural_packet=structural_packet,cutoff=cutoff)
        except ValueError as exc:
            raise EconomicException(f'asset-runway source policy failed: {exc}') from exc
        ledger['latest_annual_filing'] = latest_annual
        return refreshed,ledger
    if policy.get('schema_version') == 'FINSIGHT-CASH-SCHEDULE-REFRESH-POLICY-1':
        from .refresh_schedule_policies import bind_cash_schedule_sources
        try:
            refreshed, ledger = bind_cash_schedule_sources(policy,recipe,{**packet,'_selected_controlling_filing':controlling},
                structural_packet=structural_packet,cutoff=cutoff)
        except ValueError as exc:
            raise EconomicException(f'cash-schedule source policy failed: {exc}') from exc
        ledger['latest_annual_filing'] = latest_annual
        return refreshed, ledger
    if policy.get('schema_version') == 'FINSIGHT-CYCLICAL-FCFF-REFRESH-POLICY-1':
        from dataclasses import replace
        from .refresh_cyclical_policy import bind_and_evaluate_cyclical_recipe
        from .bridge_policy import BridgeResolution, assess_bridge_materiality
        peer = packet.get('source_peers',{}).get(policy.get('peer_ticker'))
        if not isinstance(peer,dict) or peer.get('acquisition_failed'):
            raise AcquisitionIncomplete('required cyclical peer source is unavailable')
        try:
            result = bind_and_evaluate_cyclical_recipe(policy,recipe,{**packet,'_selected_controlling_filing':controlling},
                peer_packet=peer,structural_packet=structural_packet,cutoff=cutoff)
            normalizer = CompanyFactsNormalizer(companyfacts,concept_config=concept_config,
                fiscal_year_end=submissions.get('fiscalYearEnd'),as_of_date=cutoff,filing_records=records)
            bridge = normalized_bridge(normalizer,packet,period=period)
        except ValueError as exc:
            raise EconomicException(f'cyclical source policy failed: {exc}') from exc
        refreshed = result['refreshed_recipe']
        resolution = BridgeResolution.from_dict(bridge['resolution'])
        for name,spec in refreshed['scenarios'].items():
            cash_stat = {'bear':'low','base':'midpoint','bull':'high'}[name]
            debt_stat = {'bear':'high','base':'midpoint','bull':'low'}[name]
            spec['inputs']['cash'] = getattr(resolution.cash_and_investments,cash_stat)
            spec['inputs']['debt'] = getattr(resolution.total_debt,debt_stat)
            spec['inputs']['other_claims'] = {key:getattr(resolution.preferred_equity,stat)+getattr(resolution.noncontrolling_interests,stat)
                for key,stat in (('low','low'),('base','midpoint'),('high','high'))}
        refreshed.update(source_accession=controlling['accessionNumber'],evidence_cutoff=cutoff,model_version=policy['version'])
        valued = evaluate_recipe(refreshed)
        base = refreshed['scenarios']['base']['inputs']
        enterprise = valued['scenarios']['base']['raw_value']*base['diluted_shares']-base['cash']+base['debt']+base['other_claims']['base']
        # Accounting uncertainty uses the family's source-reported base
        # denominator, not the separate generic cover-plus-awards proxy.
        assessment = assess_bridge_materiality(replace(resolution,fully_diluted_shares=base['diluted_shares']),enterprise_value=enterprise)
        return refreshed, {'controlling_filing':controlling,'latest_annual_filing':latest_annual,
            'period_end':period,'frozen_cutoff':cutoff,'cik':cik,'recipe_engine':'cyclical_fcff_quantile',
            'policy_version':policy['version'],'sources':result['source_ledger'],'normalized_bridge':bridge,
            'values':{'shares':base['diluted_shares'],'cash':base['cash'],'debt':base['debt']},
            'normalization':{'method':'issuer-balanced cyclical operating history; complete reported trade working capital',
                'peer_ticker':policy['peer_ticker'],'claim_scope':result['source_ledger']['claim_review'],
                'base_share_basis':'reported diluted shares selected by cyclical policy'},
            'bridge_quality':{**assessment.as_dict(),'complete':resolution.complete}}
    if policy.get('schema_version') == 'FINSIGHT-EARNINGS-REFRESH-POLICY-1':
        from .refresh_earnings_policies import bind_earnings_recipe
        selected_packet = {**packet,'_selected_controlling_filing':{'accession':controlling['accessionNumber'],'period_end':period}}
        try:
            result = bind_earnings_recipe(policy,recipe,selected_packet,cutoff=cutoff)
        except ValueError as exc:
            raise EconomicException(f'equity-earnings source policy failed: {exc}') from exc
        return result['recipe'], {'controlling_filing':controlling,'latest_annual_filing':latest_annual,
            'period_end':period,'frozen_cutoff':cutoff,'cik':cik,'recipe_engine':'earnings_multiple','policy_version':policy['version'],
            'sources':result['source_ledger'],'values':result['recipe']['scenarios']['base']['inputs'],
            'normalization':{'method':'comparable annual common-earnings history quantiles','history':result['source_ledger']['history_normalization'],
                'scope':policy['scope'],'correctness_repair':policy.get('correctness_repair')}}
    if policy.get('schema_version') == 'FINSIGHT-RESIDUAL-REFRESH-POLICY-1':
        from .newrefresh_family_policies import bind_and_evaluate_existing_recipe
        selected_packet = {**packet, '_selected_controlling_filing':{'accession':controlling['accessionNumber'], 'period_end':period}}
        try:
            result = bind_and_evaluate_existing_recipe(policy, recipe, selected_packet, structural_packet=structural_packet, cutoff=cutoff)
        except ValueError as exc:
            raise EconomicException(f'residual-income source policy failed: {exc}') from exc
        refreshed = result['refreshed_recipe']
        refreshed['evidence_cutoff'] = cutoff
        refreshed['source_accession'] = controlling['accessionNumber']
        bound = result['bound']
        return refreshed, {'controlling_filing':controlling, 'latest_annual_filing':latest_annual,
            'period_end':period, 'frozen_cutoff':cutoff, 'cik':cik, 'recipe_engine':'residual_income',
            'sources':bound['source_rows'], 'values':bound['inputs'], 'policy_version':policy['version'],
            'normalization':{'method':bound['source_ledger']['roe_status'],'roe_range':bound['roe_range'],
                'common_equity':bound['inputs']['common_equity'],'preferred_claim_treatment':bound['claim_status']}}
    if policy.get('schema_version') == 'FINSIGHT-SPECIAL-REFRESH-POLICY-1' and policy.get('ticker') == 'APTV':
        from .refresh_special_policies import bind_aptv_special_recipe
        selected_packet = {**packet, '_selected_controlling_filing':{'accession':controlling['accessionNumber'],'period_end':period}}
        try:
            result = bind_aptv_special_recipe(policy,recipe,selected_packet,cutoff=cutoff)
        except ValueError as exc:
            raise EconomicException(f'APTV continuing-equity source policy failed: {exc}') from exc
        return result['recipe'], {'controlling_filing':controlling,'latest_annual_filing':latest_annual,
            'period_end':period,'frozen_cutoff':cutoff,'cik':cik,'recipe_engine':'earnings_multiple',
            'policy_version':policy['version'],'sources':result['source_ledger'],
            'normalization':{'method':'current comparable continuing-parent earnings annualized from reported fiscal YTD',
                'annualization_factor':result['source_ledger']['annualization_factor'], 'nci_subtracted_again':False},
            'values':result['recipe']['scenarios']['base']['inputs']}
    normalizer = CompanyFactsNormalizer(companyfacts, fiscal_year_end=submissions.get('fiscalYearEnd'), as_of_date=cutoff, filing_records=records,
                                       concept_config=dict(concept_config))
    values, sources = {}, {}
    cash_history_cache, bridge_cache = None, None
    if not isinstance(policy.get('inputs'), dict):
        raise RuntimeError('refresh binding inputs are not declarative')
    # Claim policies must run before bridge resolution even though canonical
    # policy JSON sorts object keys.  Otherwise a valid review decision can be
    # hidden behind a generic bridge error and the consumer never sees the
    # actual economic blocker.
    input_items = sorted(
        policy['inputs'].items(),
        key=lambda item: 0 if isinstance(item[1], dict) and item[1].get('selector') == 'special_claim' else 1,
    )
    for name, rule in input_items:
        if not isinstance(rule, dict) or not isinstance(rule.get('field'), str):
            raise RuntimeError('refresh binding input rule is invalid')
        field, selector = rule['field'], rule.get('selector')
        if not isinstance(selector, str):
            raise RuntimeError('refresh binding source selector is invalid')
        try:
            if selector == 'special_claim':
                from .refresh_claim_policies import select_current_claims
                if not isinstance(rule.get('policy'), dict):
                    raise RuntimeError('invalid special-claim binding contract')
                if structural_packet is None:
                    raise AcquisitionIncomplete('special claims need the current structural filing')
                claim = select_current_claims(rule['policy'],structural_packet,controlling,cik,cutoff)
                if claim['status'] != 'source_bound':
                    raise EconomicException('special claims require review: '+', '.join(claim['review_reasons']))
                selected = claim.get(field)
                if selected is None and isinstance(claim.get('scenario_adjustments'), dict):
                    selected = claim['scenario_adjustments'].get(field.removesuffix('_adjustment'))
                if selected is None:
                    raise EconomicException(f'special claim field is unavailable: {field}')
                values[name],sources[name] = number(selected,name),claim
            elif selector == 'structural_ttm':
                if recipe['ticker'] not in {'ABT','CTSH'} or structural_packet is None:
                    raise RuntimeError('unsupported structural TTM binding contract')
                from .refresh_financials import _structural_ttm_flow
                flow=_structural_ttm_flow(normalizer,structural_packet,period,field)
                values[name]=number(flow['value'],name)
                sources[name]={'source':_source_evidence(flow,cik=cik,field=field,
                    cutoff=cutoff,value=values[name]).as_dict(),'selection':flow}
            elif selector == 'cash_fcff_history':
                if cash_history_cache is None:
                    if rule.get('additional_capex_fields'):
                        if recipe['ticker'] not in {'BR','DASH'} or structural_packet is None:
                            raise RuntimeError('unsupported additional capex source scope')
                        source_fields=(
                            (('capitalized_software','us-gaap:PaymentsForSoftware'),
                             ('capital_expenditures','us-gaap:PaymentsToAcquirePropertyPlantAndEquipment'))
                            if recipe['ticker']=='BR' else
                            (('software_development','us-gaap:PaymentsToDevelopSoftware'),
                             ('capital_expenditures','us-gaap:PaymentsToAcquirePropertyPlantAndEquipment'))
                        )
                        for source_field, qname in source_fields:
                            operands = [row for row in normalizer.ttm_flow(source_field)['sources'] if row.get('accession') == controlling['accessionNumber'] and row.get('end') == period]
                            if len(operands) != 1:
                                raise AcquisitionIncomplete('current source investment operands are not available from the selected filing')
                            rows = [row for row in structural_packet.get('facts', []) if row.get('qname') == qname and row.get('period_end') == period and row.get('period_start') == operands[0]['start']
                                and row.get('source_accession') == controlling['accessionNumber'] and row.get('unit') == 'USD'
                                and str(row.get('entity_identifier','')).zfill(10) == cik and row.get('entity_scheme') == 'http://www.sec.gov/CIK'
                                and re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(row.get('namespace','')))
                                and not row.get('dimensions') and 'cash_flow' in row.get('statement_roles', [])
                                and 'us-gaap:NetCashProvidedByUsedInInvestingActivitiesAbstract' in row.get('presentation_parents', [])]
                            if not rows or any(not isclose(number(row['value'],qname),operands[0]['value'],rel_tol=1e-12,abs_tol=.01) for row in rows):
                                raise EconomicException('separate primary PP&E/software investing outflows are not evidenced')
                    cash_receipts = None
                    if policy.get('cash_receipt_policy'):
                        if recipe['ticker'] != 'CF' or policy['cash_receipt_policy'] != 'CF_ORICA_LITIGATION_SETTLEMENT':
                            raise RuntimeError('unsupported cash receipt policy')
                        cash_receipts = packet.get('cash_receipt_evidence')
                        if not cash_receipts:
                            raise AcquisitionIncomplete('required cash receipt history evidence is not captured')
                        from .catalog import canonical_json_bytes, sha256_bytes
                        if packet.get('cash_receipt_evidence_sha256') != sha256_bytes(canonical_json_bytes(cash_receipts)):
                            raise RuntimeError('cash receipt history hash mismatch')
                    cash_history_cache = cash_history(normalizer, period=period, cutoff=cutoff, rule=rule,
                                                      cash_receipts=cash_receipts,structural_packet=structural_packet)
                if field in {'cash_conversion_margin','revenue_growth'}:
                    statistic = rule.get('statistic', 'base')
                    if statistic not in {'low','base','high'}: raise RuntimeError('unsupported cash history statistic')
                    if field not in cash_history_cache:
                        raise EconomicException('comparable revenue-growth history is unavailable')
                    values[name] = cash_history_cache[field][statistic]
                elif field == 'ttm_cash_fcff':
                    values[name] = cash_history_cache[field]
                else:
                    raise RuntimeError(f'unsupported cash history output: {name} requests {field}')
                sources[name] = {'normalization_ref':'normalization','field':field,'statistic':rule.get('statistic','base')}
            elif selector == 'normalized_bridge':
                if bridge_cache is None:
                    bridge_cache = normalized_bridge(
                        normalizer,
                        packet,
                        period=period,
                        capital_structure_policy=policy.get('capital_structure_policy'),
                        reported_claim_scope=policy.get('reported_claim_scope'),
                        aggregate_debt_scope=policy.get('aggregate_debt_scope'),
                        outside_equity_zero_scope=policy.get('outside_equity_zero_scope'),
                        preferred_equity_zero_scope=policy.get('preferred_equity_zero_scope'),
                        preferred_lifecycle_scope=policy.get('preferred_lifecycle_scope'),
                        unconsolidated_vie_scope=policy.get('unconsolidated_vie_scope'),
                    )
                    if policy.get('cash_policy'):
                        from .refresh_financials import CMG_OWNER_CASH_POLICY,DASH_OWNER_CASH_POLICY
                        expected={CMG_OWNER_CASH_POLICY:'CMG',DASH_OWNER_CASH_POLICY:'DASH'}
                        if expected.get(policy['cash_policy']) != recipe['ticker']:
                            raise RuntimeError('unsupported owner-cash bridge policy')
                        if (policy['cash_policy']==CMG_OWNER_CASH_POLICY
                            and bridge_cache['resolution']['total_debt']['high'] != 0):
                            raise EconomicException('owner-cash scope requires a verified debt-free bridge; interest-bearing debt needs model review')
                if field == 'fully_diluted_shares_proxy':
                    values[name] = number(bridge_cache['balance_sheet'][field], name)
                else:
                    range_name = {'cash_and_investments':'cash_and_investments','debt':'total_debt',
                                  'preferred_equity':'preferred_equity','noncontrolling_interests':'noncontrolling_interests'}.get(field)
                    statistic = rule.get('statistic','midpoint')
                    if range_name is None or statistic not in {'low','midpoint','high'}:
                        raise RuntimeError('unsupported normalized bridge selector')
                    values[name] = number(bridge_cache['resolution'][range_name][statistic], name)
                sources[name] = {'bridge_ref':'normalized_bridge','field':field,'statistic':rule.get('statistic','midpoint')}
            elif selector in {'ttm', 'instant', 'history_median', 'structural'}:
                values[name], sources[name] = _selected_value(
                    normalizer,
                    name=name,
                    field=field,
                    selector=selector,
                    period=period,
                    cutoff=cutoff,
                    cik=cik,
                    controlling_accession=controlling['accessionNumber'],
                    controlling=controlling,
                    structural_packet=structural_packet,
                    expected_unit=rule.get('expected_unit'),
                    period_kind=rule.get('period_kind'),
                    period_start=rule.get('period_start'),
                )
            elif selector == 'normalized':
                base_rule = rule.get('base')
                if not isinstance(base_rule, dict):
                    raise RuntimeError(f'{name}: normalized selector requires a base rule')
                reported, base_source = _selected_value(
                    normalizer,
                    name=f'{name}.reported',
                    field=str(base_rule['field']),
                    selector=str(base_rule.get('selector', 'ttm')),
                    period=period,
                    cutoff=cutoff,
                    cik=cik,
                    controlling_accession=controlling['accessionNumber'],
                    controlling=controlling,
                    structural_packet=structural_packet,
                )
                adjustment_rows = []
                for adjustment in rule.get('adjustments', []):
                    if not isinstance(adjustment, dict):
                        raise RuntimeError(f'{name}: invalid normalization adjustment')
                    raw, raw_source = _selected_value(
                        normalizer,
                        name=f'{name}.{adjustment.get("field", "adjustment")}',
                        field=str(adjustment['field']),
                        selector=str(adjustment.get('selector', 'ttm')),
                        period=period,
                        cutoff=cutoff,
                        cik=cik,
                        controlling_accession=controlling['accessionNumber'],
                        controlling=controlling,
                        structural_packet=structural_packet,
                    )
                    sign = adjustment.get('sign', 1)
                    if sign not in {-1, 1}:
                        raise RuntimeError(f'{name}: normalization sign must be 1 or -1')
                    adjustment_rows.append(
                        BoundedAdjustment(
                            name=str(adjustment.get('name', adjustment['field'])),
                            amount=sign * raw,
                            source=SourceEvidence(
                                source_id=raw_source['source']['source_id'],
                                cik=cik,
                                field=str(adjustment['field']),
                                unit=raw_source['source']['unit'],
                                reported_value=raw,
                                period_end=raw_source['source']['period_end'],
                                filing_date=raw_source['source']['filing_date'],
                                reported_vs_estimated=raw_source['source']['reported_vs_estimated'],
                            ),
                            lower_bound=adjustment.get('lower_bound'),
                            upper_bound=adjustment.get('upper_bound'),
                            rationale=str(adjustment.get('rationale', '')),
                        )
                    )
                normalized = normalize_reported_value(
                    reported,
                    adjustment_rows,
                    field=name,
                    frozen_cutoff=cutoff,
                )
                values[name], sources[name] = normalized.normalized_value, normalized.as_dict()
            elif selector == 'total_capex':
                total, total_source = _selected_value(
                    normalizer,
                    name=f'{name}.total',
                    field=field,
                    selector='ttm',
                    period=period,
                    cutoff=cutoff,
                    cik=cik,
                    controlling_accession=controlling['accessionNumber'],
                    controlling=controlling,
                    structural_packet=structural_packet,
                )
                maintenance = growth = None
                maintenance_source = growth_source = None
                if rule.get('maintenance_field'):
                    maintenance, maintenance_source = _selected_value(
                        normalizer, name=f'{name}.maintenance', field=str(rule['maintenance_field']), selector='ttm', period=period, cutoff=cutoff, cik=cik, controlling_accession=controlling['accessionNumber']
                    )
                if rule.get('growth_field'):
                    growth, growth_source = _selected_value(
                        normalizer, name=f'{name}.growth', field=str(rule['growth_field']), selector='ttm', period=period, cutoff=cutoff, cik=cik, controlling_accession=controlling['accessionNumber']
                    )
                resolution = resolve_total_capex(
                    total,
                    maintenance_capex=maintenance,
                    growth_capex=growth,
                    total_source=SourceEvidence(**total_source['source']),
                    maintenance_source=None if maintenance_source is None else SourceEvidence(**maintenance_source['source']),
                    growth_source=None if growth_source is None else SourceEvidence(**growth_source['source']),
                    frozen_cutoff=cutoff,
                )
                values[name], sources[name] = resolution.effective_total_capex, {
                    'resolution': resolution.as_dict(),
                    'total': total_source,
                    'maintenance': maintenance_source,
                    'growth': growth_source,
                }
            elif selector == 'tax_rate':
                tax_amount, tax_source = _selected_value(
                    normalizer, name=f'{name}.tax', field='income_tax', selector='ttm', period=period, cutoff=cutoff, cik=cik, controlling_accession=controlling['accessionNumber'], controlling=controlling, structural_packet=structural_packet
                )
                pretax_amount, pretax_source = _selected_value(
                    normalizer, name=f'{name}.pretax', field='pretax_income', selector='ttm', period=period, cutoff=cutoff, cik=cik, controlling_accession=controlling['accessionNumber'], controlling=controlling, structural_packet=structural_packet
                )
                if pretax_amount <= 0:
                    raise EconomicException(f'{name}: pretax income is not positive for a source-derived tax rate')
                rate = tax_amount / pretax_amount
                if not 0 <= rate <= 1:
                    raise EconomicException(f'{name}: source-derived tax rate is outside 0% to 100%')
                values[name], sources[name] = rate, {'value': rate, 'formula': 'TTM income_tax / TTM pretax_income', 'income_tax': tax_source, 'pretax_income': pretax_source}
            else:
                raise RuntimeError('unsupported configured source selector')
        except (KeyError, ValueError) as exc:
            raise EconomicException(f'{name}: source selection failed: {exc}') from exc
    bound = deepcopy(recipe)
    declared_engine = policy.get('supported_engine')
    engines = {spec.get('engine') for spec in bound.get('scenarios', {}).values() if isinstance(spec, dict)}
    supported = {'enterprise_cash_fcff','constant_growth_fcff','residual_income','earnings_multiple','asset_runway'}
    if declared_engine is not None and (engines != {declared_engine} or declared_engine not in supported):
        raise RuntimeError('refresh policy does not match a supported declared recipe engine')
    for scenario, fields in policy['scenario_bindings'].items():
        if scenario not in bound['scenarios']:
            raise RuntimeError('binding names an unknown scenario')
        for field, expression in fields.items():
            if field not in bound['scenarios'][scenario]['inputs']:
                raise RuntimeError('binding names an unknown model input')
            bound['scenarios'][scenario]['inputs'][field] = arithmetic(expression, values)
    bound['evidence_cutoff'] = cutoff
    bound['source_accession'] = controlling['accessionNumber']
    try:
        evaluated = evaluate_recipe(bound)
    except (KeyError, TypeError, ValueError) as exc:
        raise EconomicException(f'refreshed enterprise recipe failed replay: {exc}') from exc
    recipe_engine = next(iter(engines)) if len(engines) == 1 else sorted(engines)
    ledger = {
        'controlling_filing': controlling,
        'latest_annual_filing': latest_annual,
        'period_end': period,
        'frozen_cutoff': cutoff,
        'cik': cik,
        'recipe_engine': recipe_engine,
        'sources': sources,
        'values': values,
        'policy_version': policy['version'],
    }
    if cash_history_cache is not None:
        ledger['normalization'] = cash_history_cache
        ledger['ttm_cash_fcff'] = cash_history_cache['actual_measure']['value']
        ledger['reported_sources'] = {'cash_fcff':cash_history_cache['actual_measure']['source']}
    if policy.get('history_growth_policy'):
        ledger['history_growth_policy'] = policy['history_growth_policy']
    if policy.get('margin_stress_policy'):
        ledger['margin_stress'] = {'policy':policy['margin_stress_policy'],
            'history_margins':cash_history_cache['cash_conversion_margin'],
            'effective_margins':{case:bound['scenarios'][case]['inputs']['fcff_margin'] for case in ('bear','base','bull')}}
    if bridge_cache is not None:
        ledger['normalized_bridge'] = bridge_cache
        cash_reserve_range=None
        if recipe.get('ticker')=='DASH' and all(f'{case}_customer_cash_reserve' in values for case in ('bear','base','bull')):
            cash_reserve_range=tuple(values[f'{case}_customer_cash_reserve'] for case in ('bear','base','bull'))
        elif recipe.get('ticker')=='MSCI' and 'restricted_cash' in values:
            cash_reserve_range=(values['restricted_cash'],)*3
        ledger['bridge_quality'] = bridge_assessment(
            bridge_cache,bound,evaluated,cash_reserve_range=cash_reserve_range,
            additional_claim_adjustment=(
                values.get('litigation_claim',0.0) if recipe.get('ticker')=='DASH'
                else values.get('base_acquisition_financing_claim',0.0) if recipe.get('ticker')=='KDP'
                else values.get('mixed_acquisition_claim',0.0)+values.get('mixed_litigation_claim',0.0)
                    if recipe.get('ticker') in {'ABT','BAX'}
                else 0.0),
            share_adjustment=(values.get('base_convertible_conversion_shares',0.0) if recipe.get('ticker')=='MCHP' else 0.0),
            preferred_adjustment=(values.get('base_convertible_dividend_pv',0.0) if recipe.get('ticker')=='MCHP' else 0.0))
    return bound, ledger
