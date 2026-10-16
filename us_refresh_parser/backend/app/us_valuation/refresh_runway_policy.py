"""Source-bound MRNA liquid-asset runway refresh.

This adapter keeps the approved Batch 17 asset-runway identity: current liquid
assets less current debt/finance leases and a source-recomputed cash-burn
reserve.  It assigns no value to the clinical pipeline.  All balances, burn
observations, periods, units, CIKs, and share evidence are selected from the
dispatcher packet and structural filing at bind time.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
from statistics import median
import re
from typing import Any, Mapping

from .calculation_recipe import evaluate_recipe, number
from .xbrl import CompanyFactsNormalizer, load_concept_config
from .sec_client import normalize_cik


SCHEMA = "FINSIGHT-ASSET-RUNWAY-REFRESH-POLICY-1"
POLICY_VERSION = f"{SCHEMA}-MRNA"
TICKER = "MRNA"
ENGINE = "asset_runway"
ROUTINE_EVENT_ITEMS = frozenset({"2.02", "9.01"})


class RunwayRefreshError(ValueError):
    """Source selection or runway scope is not safely refreshable."""


def _iso(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise RunwayRefreshError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise RunwayRefreshError(f"{field} must be an ISO date") from exc


def _records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    if not isinstance(accessions, list):
        raise RunwayRefreshError("SEC submissions recent accession list is missing")
    return [
        {key: values[index] for key, values in recent.items() if isinstance(values, list) and index < len(values)}
        for index in range(len(accessions))
    ]


def _select_filing(records: list[dict[str, Any]], cutoff: str) -> dict[str, Any]:
    eligible = [
        row for row in records
        if row.get("form") in {"10-K", "10-Q"}
        and isinstance(row.get("accessionNumber"), str)
        and isinstance(row.get("reportDate"), str)
        and isinstance(row.get("filingDate"), str)
        and row["filingDate"] <= cutoff
        and row["reportDate"] <= cutoff
    ]
    if not eligible:
        raise RunwayRefreshError("no cutoff-eligible MRNA regular filing")
    return max(eligible, key=lambda row: (row["reportDate"], row["filingDate"], row["accessionNumber"]))


def _finite(value: Any, field: str) -> float:
    result = number(value, field)
    if not isfinite(result):
        raise RunwayRefreshError(f"{field} must be finite")
    return result


def compile_mrna_runway_policy(recipe: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    """Compile policy data only; no baseline amount is copied into the policy."""
    if recipe.get("ticker") != TICKER or set(recipe.get("scenarios", {})) != {"bear", "base", "bull"}:
        raise ValueError("asset-runway compiler supports the MRNA recipe only")
    if {spec.get("engine") for spec in recipe["scenarios"].values()} != {ENGINE}:
        raise ValueError("recipe is not an asset-runway family recipe")
    return {
        "schema_version": SCHEMA,
        "version": POLICY_VERSION,
        "ticker": TICKER,
        "cik": str(registry_entry.get("cik", "")).zfill(10),
        "supported_engine": ENGINE,
        'concept_config':load_concept_config(),
        'statement_required_fields':{'operating_cash_flow':'flow','cash':'instant'},
        "normalization_version": "US-MRNA-RUNWAY-SOURCE-NORMALIZATION-1",
        "source_requirements": {
            "companyfacts": True,
            "regular_filing": True,
            "structural_bridge": True,
            'structural':True,
            'event_exhibits':True,
            "event_review": True,
        },
        "event_rule": {
            "routine_items": sorted(ROUTINE_EVENT_ITEMS),
            "non_routine_action": "block_until_explicit_clinical_or_corporate_event_review",
            "pipeline_value": "zero_only_as_explicit_model_scope; never a missing-data substitution",
        },
        "burn_policy": {
            "annual_periods": 3,
            "burn_formula": "max(0, -(operating_cash_flow - total_capex))",
            "bear_reserve_multiplier": 3.0,
            "base_reserve_multiplier": 2.0,
            "bull_reserve_multiplier": 1.0,
            "share_states": "bear=max(current cover, current diluted weighted average), base=average, bull=min",
        },
        "unsupported_cases": [
            "non-routine 8-K or clinical/corporate event between recipe cutoff and refresh cutoff",
            "missing exact annual burn history or current TTM cash-flow inputs",
            "unresolved cash/securities, debt/finance-lease, or share evidence",
            "pipeline value requests outside the explicit zero-value model scope",
        ],
    }


def _structural_fact(structural: Mapping[str, Any], *, local_name: str, period: str, accession: str, unit: str, period_start: str | None = None) -> dict[str, Any]:
    rows = [
        row for row in structural.get("facts", [])
        if isinstance(row, Mapping)
        and row.get("local_name") == local_name
        and row.get('qname') == f'us-gaap:{local_name}'
        and row.get("source_accession") == accession
        and row.get("period_end") == period
        and row.get("period_start") == period_start
        and row.get("unit") == unit
        and not row.get("dimensions")
    ]
    values = {number(row.get('value'),local_name) for row in rows}
    if len(values) != 1:
        raise RunwayRefreshError(f"{local_name}: exact current structural fact is missing or conflicting")
    row = dict(rows[0])
    row["value"] = values.pop()
    return row


def _share_fact(structural: Mapping[str, Any], *, accession: str, period: str, cutoff: str) -> dict[str, Any]:
    rows = [
        row for row in structural.get("facts", [])
        if isinstance(row, Mapping)
        and (row.get('qname') == 'us-gaap:CommonStockSharesOutstanding' or
             (row.get('local_name') == 'EntityCommonStockSharesOutstanding' and
              re.fullmatch(r'https?://xbrl\.sec\.gov/dei/\d{4}(?:-\d{2}-\d{2})?',str(row.get('namespace','')))))
        and row.get("source_accession") == accession
        and row.get("unit") in {"xbrli:shares", "shares"}
        and not row.get("dimensions")
        and row.get('period_start') is None
        and isinstance(row.get("period_end"), str)
        and row["period_end"] <= cutoff
        and isinstance(row.get("value"), (int, float))
    ]
    if not rows:
        raise RunwayRefreshError("current common-share count is missing")
    latest_end = max(row['period_end'] for row in rows)
    latest = [row for row in rows if row['period_end']==latest_end]
    if len({number(row['value'],'current common shares') for row in latest}) != 1:
        raise RunwayRefreshError('current common-share count conflicts at the same date')
    return latest[0]


def _burn_history(normalizer: CompanyFactsNormalizer, *, current_period: str, policy: Mapping[str, Any]) -> tuple[dict[str, Any], float, list[dict[str, Any]]]:
    annual_rows: list[dict[str, Any]] = []
    annual_ocf = normalizer.annual_series('operating_cash_flow',policy['annual_periods'])
    if len(annual_ocf) != policy['annual_periods']:
        raise RunwayRefreshError('three comparable annual cash-burn periods are required')
    for ocf in annual_ocf:
        end = ocf.end
        capex = normalizer.annual_at_end("capital_expenditures", end)
        if ocf is None or capex is None:
            raise RunwayRefreshError(f"annual burn history is incomplete at {end}")
        if ocf.start != capex.start or ocf.unit != capex.unit or capex.value < 0:
            raise RunwayRefreshError('annual burn units, duration or capex sign do not reconcile')
        burn = max(0.0, -(float(ocf.value) - float(capex.value)))
        annual_rows.append({"period_end": end, "operating_cash_flow": ocf.as_dict(), "capital_expenditures": capex.as_dict(), "cash_burn": burn})
    operating = normalizer.ttm_flow("operating_cash_flow")
    capex = normalizer.ttm_flow("capital_expenditures")
    if operating["period_end"] != current_period or capex["period_end"] != current_period:
        raise RunwayRefreshError("current TTM burn inputs are not aligned to controlling period")
    if capex['value'] < 0:
        raise RunwayRefreshError('current capex sign requires an explicit rule')
    ttm_burn = max(0.0, -(float(operating["value"]) - float(capex["value"])))
    median_recent = float(median(row["cash_burn"] for row in annual_rows))
    return {"annual": annual_rows, "ttm": {"operating_cash_flow": operating, "capital_expenditures": capex, "cash_burn": ttm_burn}, "median_recent_burn": median_recent}, ttm_burn, annual_rows


def bind_mrna_runway_sources(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, structural_packet: Mapping[str, Any] | None, cutoff: str) -> tuple[dict[str, Any], dict[str, Any]]:
    cutoff = _iso(cutoff, "cutoff")
    if policy.get("ticker") != TICKER or recipe.get('ticker') != TICKER:
        raise RunwayRefreshError("MRNA runway policy identity mismatch")
    submissions, companyfacts = packet.get("submissions"), packet.get("companyfacts")
    if not isinstance(submissions, Mapping) or not isinstance(companyfacts, Mapping):
        raise RunwayRefreshError("MRNA source packet is incomplete")
    cik = str(policy.get("cik", "")).zfill(10)
    if str(submissions.get("cik", "")).zfill(10) != cik or str(companyfacts.get("cik", "")).zfill(10) != cik:
        raise RunwayRefreshError("MRNA source packet CIK mismatch")
    records = _records(submissions)
    prior_cutoff = _iso(recipe.get("evidence_cutoff"), "recipe evidence_cutoff")
    if prior_cutoff > cutoff:
        raise RunwayRefreshError('recipe evidence cutoff is after refresh cutoff')
    for event in records:
        if event.get("form") in {"8-K", "8-K/A"} and prior_cutoff < str(event.get("filingDate", "")) <= cutoff:
            items = {item.strip() for item in str(event.get("items", "")).split(",") if item.strip()}
            if not items or items - ROUTINE_EVENT_ITEMS:
                raise RunwayRefreshError("MRNA clinical/corporate event requires explicit review")
    controlling = packet.get("_selected_controlling_filing") or _select_filing(records, cutoff)
    if controlling not in records or controlling.get("filingDate", "") > cutoff:
        raise RunwayRefreshError("selected MRNA controlling filing is not eligible cached evidence")
    period = controlling["reportDate"]
    if structural_packet is None or structural_packet.get("source_accession") != controlling["accessionNumber"]:
        raise RunwayRefreshError("MRNA current structural bridge package is missing or mismatched")
    for row in structural_packet.get('facts', []):
        if normalize_cik(row.get('entity_identifier','')) != normalize_cik(cik):
            raise RunwayRefreshError('MRNA structural fact issuer identity mismatch')
    normalizer = CompanyFactsNormalizer(companyfacts, fiscal_year_end=submissions.get("fiscalYearEnd"), as_of_date=cutoff, filing_records=records, concept_config=load_concept_config())
    burn, _, _ = _burn_history(normalizer, current_period=period, policy=policy["burn_policy"])
    accession = controlling["accessionNumber"]
    liquid_rows = [_structural_fact(structural_packet, local_name=name, period=period, accession=accession, unit="USD") for name in ("CashAndCashEquivalentsAtCarryingValue", "AvailableForSaleSecuritiesDebtSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesNoncurrent")]
    debt_rows = [_structural_fact(structural_packet, local_name="LongTermDebtNoncurrent", period=period, accession=accession, unit="USD"), _structural_fact(structural_packet, local_name="FinanceLeaseLiability", period=period, accession=accession, unit="USD")]
    preferred = _structural_fact(structural_packet,local_name='PreferredStockValue',period=period,accession=accession,unit='USD')
    if preferred['value'] != 0:
        raise RunwayRefreshError('new preferred claim requires a common-equity allocation rule')
    current_debt = normalizer.instant('current_debt',end=period)
    if current_debt is not None:
        if current_debt.accession != accession or current_debt.value < 0:
            raise RunwayRefreshError('current debt does not reconcile to controlling filing')
        if 'Lease' in current_debt.concept:
            raise RunwayRefreshError('current debt aggregate includes leases; its overlap with total finance leases requires a source rule')
        debt_rows.append(current_debt.as_dict())
    annual = normalizer.annual_series('diluted_weighted_average_shares',1)
    pair = normalizer.latest_ytd_pair('diluted_weighted_average_shares',after_end=annual[-1].end) if annual else None
    weighted_fact = pair[0] if pair else (annual[-1] if annual else None)
    if weighted_fact is None or weighted_fact.end != period or weighted_fact.accession != accession:
        raise RunwayRefreshError("current diluted weighted-average shares are not aligned")
    weighted = weighted_fact.as_dict()
    cover = _share_fact(structural_packet, accession=accession, period=period, cutoff=cutoff)
    weighted_shares = float(weighted["value"])
    cover_shares = float(cover["value"])
    high = max(weighted_shares, cover_shares)
    low = min(weighted_shares, cover_shares)
    liquid_assets = sum(float(row["value"]) for row in liquid_rows)
    debt = sum(float(row["value"]) for row in debt_rows)
    reserves = {"bear": burn["median_recent_burn"] * policy["burn_policy"]["bear_reserve_multiplier"], "base": burn["ttm"]["cash_burn"] * policy["burn_policy"]["base_reserve_multiplier"], "bull": burn["ttm"]["cash_burn"] * policy["burn_policy"]["bull_reserve_multiplier"]}
    shares = {"bear": high, "base": (high + low) / 2.0, "bull": low}
    refreshed = deepcopy(recipe)
    refreshed['evidence_cutoff'] = cutoff
    refreshed['source_accession'] = accession
    ledger: dict[str, Any] = {"controlling_filing": controlling, "period_end": period, "frozen_cutoff": cutoff, "cik": cik, "policy_version": policy["version"], "sources": {"burn": burn, "liquid_assets": liquid_rows, "debt_and_finance_leases": debt_rows, "weighted_shares": weighted, "cover_shares": cover}, "values": {"liquid_assets": liquid_assets, "debt_and_finance_leases": debt, "cash_burn_reserve": reserves, "shares": shares, "pipeline_terminal_value": 0.0}, "pipeline_review": {"status": "explicit_model_scope_zero", "value": 0.0, "reason": "No pipeline success value is modeled; this is not a missing-data substitution.", "event_rule": policy["event_rule"]}}
    for name in ("bear", "base", "bull"):
        inputs = refreshed["scenarios"][name]["inputs"]
        inputs.update({"liquid_assets": liquid_assets, "debt_and_finance_leases": debt, "cash_burn_reserve": reserves[name], "shares": shares[name], "pipeline_terminal_value": 0.0})
    evaluated = evaluate_recipe(refreshed)
    ledger["result"] = {"range": evaluated["range"], "recipe_hash": evaluated["recipe_hash"], "effective_recipe_hash": evaluated["effective_recipe_hash"]}
    ledger['sources']['reported_preferred'] = preferred
    ledger['recipe_engine'] = ENGINE
    ledger['normalization'] = {'method':'current liquid assets less reported debt and versioned cash-burn reserves',
        'annual_periods_used':[row['period_end'] for row in burn['annual']],
        'limitations':['Clinical pipeline success has no assigned value in this asset-runway model.',
                      'This is a source-bounded cash-runway scenario, not a liquidation guarantee.']}
    return refreshed, ledger


def bind_and_evaluate_mrna_runway_recipe(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, structural_packet: Mapping[str, Any] | None, cutoff: str) -> dict[str, Any]:
    refreshed, ledger = bind_mrna_runway_sources(policy, recipe, packet, structural_packet=structural_packet, cutoff=cutoff)
    return {"bound": ledger["values"], "baseline_replay": dict(recipe.get("replay", evaluate_recipe(recipe)["range"])), "refreshed_recipe": refreshed, "refreshed_replay": ledger["result"]["range"], "source_ledger": ledger}
