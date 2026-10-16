"""Statement-table checks shared by every issuer in the staged refresh.

This module selects reported facts and identifies concrete exceptions. It does
not choose new valuation assumptions or infer missing facts as zero.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
import re

from .catalog import canonical_json_bytes, sha256_bytes
from .xbrl import load_concept_config

VERSION = "US-TABLE-FIRST-1"
# Screening thresholds trigger review, not automatic financial adjustments.
BALANCE_TOLERANCE = .005
MATERIAL_CHANGE = .20
EXTRA_FIELDS = {
    "liabilities": ("instant", "USD", ["Liabilities"]),
    "group_equity": ("instant", "USD", ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]),
    "parent_equity": ("instant", "USD", ["StockholdersEquity"]),
    "balance_total": ("instant", "USD", ["LiabilitiesAndStockholdersEquity"]),
    "temporary_equity_total": ("instant", "USD", ["TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests"]),
    "redeemable_nci": ("instant", "USD", ["RedeemableNoncontrollingInterestEquityCarryingAmount"]),
    "temporary_parent_equity": ("instant", "USD", ["TemporaryEquityCarryingAmountAttributableToParent"]),
    "parent_earnings": ("flow", "USD", ["NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"]),
    "acquisition_cash": ("flow", "USD", ["PaymentsToAcquireBusinessesNetOfCashAcquired"]),
    "discontinued_cash": ("flow", "USD", ["NetCashProvidedByUsedInOperatingActivitiesDiscontinuedOperations"]),
}


def _issue(code, field, detail):
    return {"code": code, "field": field, "detail": detail}


def inspect_tables(packet: dict, *, cik: str, cutoff: str, recipe: dict | None = None) -> dict:
    """Read the controlling filing's consolidated tables before model readiness.

    Values from the structural parser are already scaled. Stock/flow periods,
    entity, dimensions, units and accession are checked before selection.
    """
    date.fromisoformat(cutoff)
    filing = packet.get("controlling_filing", {})
    accession = filing.get("accessionNumber") or filing.get("accession")
    period = filing.get("reportDate") or filing.get("report_date")
    filed = filing.get("filingDate") or filing.get("filed")
    structure = packet.get("structural_packets", {}).get(accession) or packet.get("structural_filing")
    issues, facts, missing, diagnostics = [], {}, [], []
    result = {"version": VERSION, "cik": str(cik).zfill(10), "accession": accession,
              "period": period, "facts": facts, "missing_fields": missing, "exceptions": issues,
              "diagnostics": diagnostics}
    engine = (recipe or {}).get('scenarios', {}).get('base', {}).get('engine')
    required = {'total_assets', 'liabilities', 'group_equity', 'balance_total', 'diluted_weighted_average_shares'}
    required |= {'residual_income': {'parent_equity', 'parent_earnings'},
                 'enterprise_cash_fcff': {'cash', 'operating_cash_flow', 'capital_expenditures'},
                 'cash_schedule': {'cash', 'revenue', 'operating_income'},
                 'constant_growth_fcff': {'cash', 'revenue'}}.get(engine, set())
    profile=(recipe or {}).get('source_refresh_profile')
    if profile=='parent_common_ri' and engine=='residual_income':
        required={'total_assets','liabilities','balance_total','parent_equity','parent_earnings'}
    elif profile=='owner_cash_ait' and engine=='cash_schedule':
        required={'total_assets','liabilities','balance_total','parent_equity','revenue','operating_cash_flow','capital_expenditures'}
    if not accession or not period or not filed or not period <= filed <= cutoff:
        issues.append(_issue("invalid_filing_period", "filing", "A cutoff-eligible controlling financial filing is required."))
        return result
    if str(packet.get("submissions", {}).get("cik", "")).zfill(10) != str(cik).zfill(10):
        issues.append(_issue("identity_mismatch", "cik", "Submission identity differs from the frozen issuer."))
        return result
    if not isinstance(structure, dict) or structure.get("source_accession") != accession:
        issues.append(_issue("missing_statement_tables", "structural_filing", "Current filing tables have not been extracted."))
        return result
    result["structural_sha256"] = sha256_bytes(canonical_json_bytes(structure))
    definitions = deepcopy(load_concept_config()["fields"])
    definitions.update({name: {"kind": kind, "unit": unit, "concepts": concepts}
                        for name, (kind, unit, concepts) in EXTRA_FIELDS.items()})
    rows = structure.get("facts", [])
    for field, definition in definitions.items():
        field_issues = issues if field in required else diagnostics
        selected = []
        for concept in definition["concepts"]:
            namespace, local = concept.split(":", 1) if ":" in concept else ("us-gaap", concept)
            # No issuer-name aliases are added to this shared selector.
            if namespace not in {"us-gaap", "dei"}:
                continue
            candidates = [row for row in rows if row.get("qname") == f"{namespace}:{local}"
                          and row.get("period_end") == period and not row.get("dimensions")
                          and row.get("source_accession") == accession
                          and bool(row.get("period_start")) == (definition["kind"] == "flow")]
            if not candidates:
                continue
            matching_entity = [r for r in candidates if str(r.get('entity_identifier', '')).zfill(10) == str(cik).zfill(10)]
            if matching_entity:
                # Combined registrant filings legitimately contain several CIKs.
                candidates = matching_entity
            bad = [row for row in candidates if
                   str(row.get("entity_identifier", "")).zfill(10) != str(cik).zfill(10)
                   or row.get("entity_scheme") != "http://www.sec.gov/CIK"
                   or str(row.get("unit", "")).removeprefix("xbrli:") != definition["unit"]
                   or not isinstance(row.get("value"), (float, int)) or isinstance(row.get("value"), bool)
                   or not isfinite(row["value"])
                   or (namespace == "us-gaap" and not re.fullmatch(r"https?://fasb.org/us-gaap/20\d{2}", str(row.get("namespace", ""))))]
            if bad:
                field_issues.append(_issue("invalid_fact_scope", field, "Reported fact has conflicting entity, namespace, units or value."))
                break
            if definition["kind"] == "flow":
                # Longest current fiscal duration, never a quarter substituted for YTD.
                start = min(row["period_start"] for row in candidates)
                candidates = [row for row in candidates if row["period_start"] == start]
                duration = (date.fromisoformat(period) - date.fromisoformat(start)).days + 1
                if not 60 <= duration <= 385:
                    field_issues.append(_issue("invalid_flow_period", field, "Current flow duration is outside quarterly/annual periods."))
                    break
            if len({row["value"] for row in candidates}) != 1:
                def precision(row):
                    decimals = str(row.get('decimals', 'INF'))
                    return float('inf') if decimals == 'INF' else int(decimals)
                def radius(row):
                    return 0 if precision(row) == float('inf') else .5 * 10 ** -precision(row)
                if max(r['value']-radius(r) for r in candidates) > min(r['value']+radius(r) for r in candidates):
                    field_issues.append(_issue("conflicting_facts", field, "Same-concept consolidated facts disagree beyond their reported precision."))
                    break
                # Rounded cover/table duplicates corroborate, not contradict,
                # a more precise reported value. Do not average them.
                candidates.sort(key=precision, reverse=True)
            selected = candidates
            break
        if not selected:
            missing.append(field)
            continue
        row = selected[0]
        facts[field] = {key: row.get(key) for key in
                        ("value", "qname", "unit", "period_start", "period_end", "source_accession", "context_id", "decimals")}
        facts[field]["filed_date"] = filed
    value = lambda name: facts[name]["value"] if name in facts else None
    assets = value("total_assets")
    if assets is None:
        issues.append(_issue("missing_essential_input", "total_assets", "A current consolidated balance sheet is required."))
    elif assets <= 0:
        issues.append(_issue("invalid_balance", "total_assets", "Reported assets must be positive."))
    else:
        totals = [("balance_total", value("balance_total"))]
        if value("liabilities") is not None and value("group_equity") is not None:
            temporary = value('temporary_equity_total')
            if temporary is None:
                temporary = sum(value(name) for name in ('redeemable_nci', 'temporary_parent_equity') if value(name) is not None)
            totals.append(("liabilities_plus_equity", value("liabilities") + value("group_equity") + temporary))
        for name, total in totals:
            if total is not None and abs(total-assets) > BALANCE_TOLERANCE*assets:
                issues.append(_issue("balance_sheet_inconsistent", name, "Assets differ materially from liabilities and consolidated equity."))
        acquisition = value("acquisition_cash")
        if acquisition is not None and abs(acquisition) > MATERIAL_CHANGE*assets:
            issues.append(_issue("material_business_change", "acquisition_cash", "Acquisition cash exceeds 20% of current assets; check forecast comparability."))
    if value("cash") is not None and value("cash") < 0:
        issues.append(_issue("invalid_balance", "cash", "Cash cannot be negative."))
    shares = value("diluted_weighted_average_shares")
    if shares is not None and shares <= 0:
        issues.append(_issue("invalid_share_count", "diluted_weighted_average_shares", "Share denominator must be positive."))
    if recipe and shares is not None:
        prior = recipe.get("scenarios", {}).get("base", {}).get("inputs", {})
        denominator = prior.get("diluted_shares", prior.get("shares"))
        if denominator and abs(shares/denominator - 1) > MATERIAL_CHANGE:
            diagnostics.append(_issue("material_share_change", "diluted_weighted_average_shares", "Share denominator changed more than 20%; the model binding must reconcile current shares before recalculation."))
    if value("discontinued_cash") not in (None, 0) and "operating_cash_flow" in facts:
        if facts["operating_cash_flow"]["qname"] != "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations":
            issues.append(_issue("continuing_scope_required", "operating_cash_flow", "Discontinued-operation cash is reported; reconcile the continuing model scope."))
    return result


def require_table_inputs(packet: dict, *, cik: str, cutoff: str, recipe: dict) -> dict:
    audit = inspect_tables(packet, cik=cik, cutoff=cutoff, recipe=recipe)
    if audit["exceptions"]:
        raise ValueError("; ".join(f"{r['code']}:{r['field']}: {r['detail']}" for r in audit["exceptions"]))
    return audit


def project_table_facts(companyfacts: dict, audit: dict, filing: dict) -> dict:
    """Feed selected table amounts into the existing normalizer's source format.

    Prior-year evidence remains intact. Only the exact current accession,
    concept and period are replaced; filing facts never overwrite assumptions.
    """
    projected = deepcopy(companyfacts)
    definitions = load_concept_config()['fields']
    # An optional conflict is harmless only while the model does not use it.
    # Remove that current operand so an actual binding request fails explicitly
    # rather than silently falling back to the conflicting aggregate feed.
    for problem in audit.get('diagnostics', []):
        if problem['code'] not in {'invalid_fact_scope', 'invalid_flow_period', 'conflicting_facts'}:
            continue
        for reference in definitions.get(problem['field'], {}).get('concepts', []):
            namespace, concept = reference.split(':', 1) if ':' in reference else ('us-gaap', reference)
            for rows in projected.get('facts', {}).get(namespace, {}).get(concept, {}).get('units', {}).values():
                rows[:] = [r for r in rows if not (r.get('accn') == audit['accession'] and r.get('end') == audit['period'])]
    for fact in audit['facts'].values():
        namespace, concept = fact['qname'].split(':', 1)
        unit = fact['unit'].removeprefix('xbrli:')
        units = projected.setdefault('facts', {}).setdefault(namespace, {}).setdefault(concept, {}).setdefault('units', {})
        rows = units.setdefault(unit, [])
        rows[:] = [r for r in rows if not (r.get('accn') == fact['source_accession']
                  and r.get('end') == fact['period_end'] and r.get('start') == fact['period_start'])]
        row = {'accn': fact['source_accession'], 'end': fact['period_end'], 'val': fact['value'],
               'filed': filing['filingDate'], 'form': filing['form'],
               'fy': int(fact['period_end'][:4]), 'fp': 'FY' if filing['form'].startswith('10-K') else 'Q'}
        if fact['period_start']:
            row['start'] = fact['period_start']
        rows.append(row)
    return projected


def metadata_exceptions(rows: list[dict], *, since: str) -> list[dict]:
    """Only explicit financial non-reliance triggers a metadata hold.

    Routine 8-K presence is not an exception. Financial amendments are parsed
    as statement inputs by the capture/binding path.
    """
    return [_issue("financial_nonreliance", "filing", "Filed Item 4.02 says prior statements should not be relied upon.")
            for row in rows if row.get("filingDate", "") > since
            and row.get("form") in {"8-K", "8-K/A"}
            and "4.02" in {v.strip() for v in str(row.get("items", "")).split(",")}]
