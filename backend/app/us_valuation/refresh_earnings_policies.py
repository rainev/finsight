"""Source-bound refresh policies for ordinary equity earnings multiples.

This family deliberately stays at the equity-earnings level.  Ford Credit,
GM Financial, mortgage operations, land deposits, and other issuer-specific
businesses remain inside consolidated earnings; no EV/debt bridge is added.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Mapping

from .calculation_recipe import evaluate_recipe
from .history import HistoryObservation, summarize_history_metric
from .xbrl import CompanyFactsNormalizer, SelectedFact, load_concept_config
from .sec_client import normalize_cik


SCHEMA = "FINSIGHT-EARNINGS-REFRESH-POLICY-1"
SUPPORTED_TICKERS = frozenset({"F", "GM", "DHI", "LEN", "NVR", "PHM"})


RULES: dict[str, dict[str, Any]] = {
    "F": {
        "earnings_concepts": ["NetIncomeLossAvailableToCommonStockholdersBasic"],
        "history_formula": "reported annual earnings available to common shareholders, not consolidated pretax less tax",
        "current_formula": "FY common earnings + current selected YTD common earnings - prior comparable YTD common earnings",
        "positive_history_only": False,
        "family": "ford_consolidated_common_earnings",
        "scope": "Ford Credit remains consolidated; no captive-finance SOTP or EV debt bridge.",
    },
    "GM": {
        "earnings_concepts": ["NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"],
        "history_formula": "reported consolidated annual common-stockholder earnings",
        "current_formula": "FY + current selected YTD - prior comparable YTD",
        "positive_history_only": False,
        "family": "gm_consolidated_common_earnings",
        "scope": "GM Financial and floorplan funding remain consolidated; no EV debt bridge.",
    },
    "DHI": {
        "earnings_concepts": ["NetIncomeLoss"],
        "history_formula": "reported annual consolidated net income",
        "current_formula": "FY + current selected YTD - prior comparable YTD",
        "positive_history_only": True,
        "family": "homebuilder_consolidated_earnings",
        "scope": "Homebuilding and mortgage activity remain consolidated; no mortgage-separated FCFF or EV debt bridge.",
    },
    "LEN": {
        "earnings_concepts": ["NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"],
        "history_formula": "reported annual common-stockholder earnings",
        "current_formula": "FY + current selected YTD - prior comparable YTD",
        "positive_history_only": True,
        "family": "homebuilder_consolidated_common_earnings",
        "scope": "Mortgage activity, land deposits, and financing remain consolidated; no mortgage-separated FCFF or EV debt bridge.",
    },
    "NVR": {
        "earnings_concepts": ["NetIncomeLoss"],
        "history_formula": "reported annual consolidated net income",
        "current_formula": "FY + current selected YTD - prior comparable YTD",
        "positive_history_only": True,
        "family": "homebuilder_consolidated_earnings",
        "scope": "Mortgage banking and lot-option economics remain consolidated; no EV debt bridge.",
    },
    "PHM": {
        "earnings_concepts": ["NetIncomeLoss"],
        "history_formula": "reported annual consolidated net income",
        "current_formula": "FY + current selected YTD - prior comparable YTD",
        "positive_history_only": True,
        "family": "homebuilder_consolidated_earnings",
        "scope": "Mortgage activity and land exposure remain consolidated; no EV debt bridge.",
    },
}


def _config(rule: Mapping[str, Any]) -> dict[str, Any]:
    config = load_concept_config()
    config.setdefault("fields", {})["earnings_refresh"] = {
        "concepts": list(rule["earnings_concepts"]),
        "unit": "USD",
        "kind": "flow",
    }
    config["fields"]["diluted_shares_refresh"] = {
        "concepts": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
        "unit": "shares",
        "kind": "flow",
    }
    config["fields"]["income_tax_refresh"] = {
        "concepts": ["IncomeTaxExpenseBenefit"],
        "unit": "USD",
        "kind": "flow",
    }
    return config


def _records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    return [
        {key: values[i] for key, values in recent.items() if isinstance(values, list) and i < len(values)}
        for i in range(len(accessions))
    ]


def _selected_filing(policy: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    submissions = packet.get("submissions")
    companyfacts = packet.get("companyfacts")
    selected = packet.get("_selected_controlling_filing")
    if not isinstance(submissions, Mapping) or not isinstance(companyfacts, Mapping) or not isinstance(selected, Mapping):
        raise ValueError("earnings refresh requires submissions, companyfacts, and dispatcher-selected filing")
    expected_cik = normalize_cik(policy.get('cik',''))
    if normalize_cik(submissions.get('cik','')) != expected_cik or normalize_cik(companyfacts.get('cik','')) != expected_cik:
        raise ValueError("earnings refresh issuer identity conflict")
    accession = str(selected.get("accession", ""))
    period_end = str(selected.get("period_end", ""))
    period_start = str(selected.get("period_start", ""))
    if not period_start:
        starts = []
        for reference in policy['earnings_concepts']:
            namespace,concept = reference.split(':',1) if ':' in reference else ('us-gaap',reference)
            for row in companyfacts.get('facts', {}).get(namespace, {}).get(concept, {}).get('units', {}).get('USD', []):
                if row.get('accn') == accession and row.get('end') == period_end and row.get('filed','') <= cutoff and isinstance(row.get('start'),str):
                    if 65 <= (date.fromisoformat(period_end)-date.fromisoformat(row['start'])).days + 1 <= 385:
                        starts.append(row['start'])
        if starts: period_start = min(starts)
        if not starts:
            structural = packet.get('structural_filing') or packet.get('structural') or {}
            concepts = {reference if ':' in reference else f'us-gaap:{reference}' for reference in policy['earnings_concepts']}
            for row in structural.get('facts', []):
                if (row.get('source_accession') == accession and row.get('period_end') == period_end and row.get('qname') in concepts
                    and row.get('unit') == 'USD' and not row.get('dimensions') and isinstance(row.get('period_start'),str)):
                    if 65 <= (date.fromisoformat(period_end)-date.fromisoformat(row['period_start'])).days + 1 <= 385:
                        starts.append(row['period_start'])
            if starts: period_start = min(starts)
    if not accession or not period_end or not period_start:
        raise ValueError("selected controlling filing requires accession, period_start, and period_end")
    try:
        cutoff_date = date.fromisoformat(cutoff)
        end = date.fromisoformat(period_end)
        start = date.fromisoformat(period_start)
    except ValueError as exc:
        raise ValueError("selected filing dates are invalid") from exc
    if start >= end or end > cutoff_date:
        raise ValueError("selected filing period is invalid or outside cutoff")
    rows = _records(submissions)
    matches = [
        row for row in rows
        if row.get("accessionNumber") == accession
        and row.get("reportDate") == period_end
        and row.get("filingDate", "") <= cutoff
        and row.get("form") in {"10-Q", "10-Q/A", "10-K", "10-K/A"}
    ]
    if len(matches) != 1:
        raise ValueError("selected controlling filing is not one eligible SEC filing")
    return {**selected, 'period_start':period_start, "filing_date": matches[0].get("filingDate"), "form": matches[0].get("form")}, rows


def compile_earnings_refresh_policy(recipe: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    ticker = str(recipe.get("ticker", ""))
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"unsupported ordinary earnings ticker: {ticker}")
    if any(spec.get("engine") != "earnings_multiple" for spec in recipe.get("scenarios", {}).values()):
        raise ValueError("recipe is not earnings-multiple family")
    if any(float(spec.get("inputs", {}).get("net_bridge", 0.0)) != 0.0 for spec in recipe.get("scenarios", {}).values()):
        raise ValueError(f"{ticker} has a nonzero bridge and is outside ordinary earnings policy")
    base_shares = float(recipe["scenarios"]["base"]["inputs"]["shares"])
    rule = RULES[ticker]
    return {
        "schema_version": SCHEMA,
        "version": f"{SCHEMA}-{ticker}",
        "ticker": ticker,
        "cik": str(registry_entry.get("cik", "")).zfill(10),
        "family": rule["family"],
        "policy_status": "source_validation_pending",
        "source_formula": rule["current_formula"],
        "history_formula": rule["history_formula"],
        "history_positive_only": rule["positive_history_only"],
        "earnings_concepts": list(rule["earnings_concepts"]),
        "share_source": "current reported weighted-average diluted shares; scenario sensitivity is an approved fixed ratio; no additive TTM shares",
        "approved_sensitivities": {
            "multiples": [float(recipe["scenarios"][name]["inputs"]["multiple"]) for name in ("bear", "base", "bull")],
            "share_multipliers": [float(recipe["scenarios"][name]["inputs"]["shares"]) / base_shares for name in ("bear", "base", "bull")],
        },
        "baseline_binding": {
            "baseline_version": recipe.get("baseline_version"),
            "baseline_sha256": registry_entry.get("baseline_sha256"),
            "evidence_cutoff": recipe.get("evidence_cutoff"),
            "source_accession": recipe.get("source_accession"),
            "source_path": (recipe.get("provenance") or {}).get("source_path"),
        },
        "concept_config": {
            "fields": {
                "earnings_refresh": {"concepts": list(rule["earnings_concepts"]), "unit": "USD", "kind": "flow"},
                "diluted_shares_refresh": {"concepts": ["WeightedAverageNumberOfDilutedSharesOutstanding"], "unit": "shares", "kind": "flow"},
                'period_end_equity':{'concepts':['StockholdersEquity'],'unit':'USD','kind':'instant'},
                **({"income_tax_refresh": {"concepts": ["IncomeTaxExpenseBenefit"], "unit": "USD", "kind": "flow"}} if ticker == "F" else {}),
            }
        },
        "statement_required_fields": {"earnings_refresh": "flow", "diluted_shares_refresh": "flow",'period_end_equity':'instant'},
        'source_requirements':{'structural':True,'event_exhibits':True},
        'correctness_repair': 'Use reported common earnings rather than consolidated pretax less tax, which includes minority earnings.' if ticker == 'F' else None,
        "scope": rule["scope"],
        "ev_debt_bridge": False,
        "normalization_policy": "US-COMPANY-HISTORY-1.0 median with historical 25th/75th percentiles; no target fitting",
        "normalization_intentional_change": "Refresh current/prior periods and current weighted-average shares from the selected filing while preserving approved multiples and scenario share ratios.",
    }


def _structural_rows(structural: Mapping[str, Any], *, local_name: str, period_start: str, period_end: str, accession: str, unit: str) -> list[dict[str, Any]]:
    facts = structural.get("facts") if isinstance(structural, Mapping) else None
    if not isinstance(facts, list):
        return []
    rows = [
        row for row in facts
        if isinstance(row, Mapping)
        and row.get("local_name") == local_name
        and row.get('qname') == f'us-gaap:{local_name}'
        and row.get("period_start") == period_start
        and row.get("period_end") == period_end
        and row.get("source_accession") == accession
        and row.get("unit") == unit
        and row.get("dimensions") in ([], None)
        and isinstance(row.get("value"), (int, float))
    ]
    unique: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for row in rows:
        unique[(row.get("value"), row.get("qname"), row.get("context_id"))] = row
    return [deepcopy(row) for row in unique.values()]


def _structural_one(structural: Mapping[str, Any] | None, *, local_name: str, period_start: str, period_end: str, accession: str, unit: str) -> dict[str, Any] | None:
    rows = _structural_rows(structural or {}, local_name=local_name, period_start=period_start, period_end=period_end, accession=accession, unit=unit)
    if not rows:
        return None
    if len(rows) != 1:
        raise ValueError(f"ambiguous structural fact: {local_name} {period_start}/{period_end}")
    return rows[0]


def _validate_structural_identity(structural: Mapping[str, Any], *, cik: str, accession: str) -> None:
    facts = structural.get("facts")
    if not isinstance(facts, list):
        raise ValueError("structural packet has no facts")
    relevant = [row for row in facts if isinstance(row, Mapping) and row.get("source_accession") == accession]
    if not relevant:
        raise ValueError("structural packet has no facts for selected accession")
    expected = str(cik).zfill(10)
    for row in relevant:
        if str(row.get("entity_identifier", "")).zfill(10) != expected or row.get("entity_scheme") != "http://www.sec.gov/CIK":
            raise ValueError("structural fact issuer identity does not match selected policy")


def _fact_source(fact: SelectedFact | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(fact, SelectedFact):
        source = fact.as_dict()
        # Keep both normalizer-native and structural-style period keys so the
        # ledger can be consumed uniformly by the refresh dispatcher.
        source["period_start"] = source.get("start")
        source["period_end"] = source.get("end")
        return source
    return {
        "concept": fact.get("qname") or fact.get("local_name"),
        "value": fact.get("value"),
        "unit": fact.get("unit"),
        "period_start": fact.get("period_start"),
        "period_end": fact.get("period_end"),
        "accession": fact.get("source_accession"),
        "form": fact.get("filing_form"),
        "filed_date": fact.get("filed_date"),
        "dimensions": fact.get("dimensions", []),
        "reported_vs_estimated": "reported",
    }


def _aligned_pair(normalizer: CompanyFactsNormalizer, field: str, annual_end: str, selected: Mapping[str, Any], structural: Mapping[str, Any] | None, *, structural_name: str, unit: str) -> tuple[SelectedFact | Mapping[str, Any], SelectedFact | Mapping[str, Any]]:
    pair = normalizer.latest_ytd_pair(field, after_end=annual_end)
    selected_start = str(selected["period_start"])
    selected_end = str(selected["period_end"])
    accession = str(selected["accession"])
    if pair is not None and pair[0].accession == accession and pair[1].accession == accession and pair[0].start == selected_start and pair[0].end == selected_end:
        return pair
    current = _structural_one(structural, local_name=structural_name, period_start=selected_start, period_end=selected_end, accession=accession, unit=unit)
    prior_start = date.fromisoformat(selected_start).replace(year=date.fromisoformat(selected_start).year - 1).isoformat()
    prior_end = date.fromisoformat(selected_end).replace(year=date.fromisoformat(selected_end).year - 1).isoformat()
    prior = _structural_one(structural, local_name=structural_name, period_start=prior_start, period_end=prior_end, accession=accession, unit=unit)
    if current is None or prior is None:
        raise ValueError(f"{field} current/prior selected-period facts do not match controlling filing")
    return current, prior


def _history_metric(normalizer: CompanyFactsNormalizer, ticker: str, rule: Mapping[str, Any]) -> tuple[Any, list[dict[str, Any]]]:
    # The recorded generators use the latest five annual observations for the
    # history quantile; older observations are retained in Companyfacts but do
    # not belong to this approved normalization window.
    annual = normalizer.annual_series("earnings_refresh", 5)
    observations: list[HistoryObservation] = []
    sources: list[dict[str, Any]] = []
    for fact in annual:
        if rule.get('net_income_from_pretax'):
            tax = normalizer.annual_at_end("income_tax_refresh", fact.end)
            if tax is None:
                continue
            value = float(fact.value) - float(tax.value)
            source = [_fact_source(fact), _fact_source(tax)]
            formula = rule["history_formula"]
        else:
            value = float(fact.value)
            source = [_fact_source(fact)]
            formula = rule["history_formula"]
        if rule["positive_history_only"] and value <= 0:
            continue
        observations.append(HistoryObservation(period_role="annual", period_end=fact.end, fiscal_year=fact.fiscal_year, value=value, unit="USD", formula=formula, sources=tuple(source)))
        sources.append({"period_end": fact.end, "value": value, "formula": formula, "sources": source})
    if len(observations) < 3:
        raise ValueError(f"{ticker} has fewer than three eligible annual earnings observations")
    return summarize_history_metric(f"{ticker.lower()}_normalized_earnings", observations), sources


def _current_reconstruction(normalizer: CompanyFactsNormalizer, ticker: str, rule: Mapping[str, Any], selected: Mapping[str, Any], structural: Mapping[str, Any] | None) -> tuple[float, dict[str, Any]]:
    annual = normalizer.annual_series("earnings_refresh", 20)
    if not annual:
        raise ValueError(f"{ticker} has no annual earnings anchor")
    fy = annual[-1]
    if fy.end == selected['period_end']:
        if fy.accession != selected['accession'] or fy.start != selected['period_start']:
            raise ValueError('current annual earnings do not match selected filing')
        return float(fy.value), {'formula':'reported current fiscal-year common earnings','fy':_fact_source(fy),'value':float(fy.value)}
    if fy.end > selected['period_end']:
        raise ValueError('annual earnings anchor follows selected current period')
    if not 1 <= (date.fromisoformat(selected['period_start']) - date.fromisoformat(fy.end)).days <= 8:
        raise ValueError('annual earnings and current YTD periods are not contiguous')
    current, prior = _aligned_pair(normalizer, "earnings_refresh", fy.end, selected, structural, structural_name=rule["earnings_concepts"][0], unit="USD")
    prior_source = _fact_source(prior)
    if abs((date.fromisoformat(prior_source['period_start']) - date.fromisoformat(fy.start)).days) > 8 or prior_source['period_end'] > fy.end:
        raise ValueError('comparative earnings YTD does not belong to the annual anchor')
    if rule.get('net_income_from_pretax'):
        tax_annual = normalizer.annual_at_end("income_tax_refresh", fy.end)
        if tax_annual is None:
            raise ValueError("F annual tax fact missing")
        tax_current, tax_prior = _aligned_pair(normalizer, "income_tax_refresh", fy.end, selected, structural, structural_name="IncomeTaxExpenseBenefit", unit="USD")
        fy_net = float(fy.value) - float(tax_annual.value)
        current_net = float(current["value"] if isinstance(current, Mapping) else current.value) - float(tax_current["value"] if isinstance(tax_current, Mapping) else tax_current.value)
        prior_net = float(prior["value"] if isinstance(prior, Mapping) else prior.value) - float(tax_prior["value"] if isinstance(tax_prior, Mapping) else tax_prior.value)
    else:
        fy_net = float(fy.value)
        current_net = float(current["value"] if isinstance(current, Mapping) else current.value)
        prior_net = float(prior["value"] if isinstance(prior, Mapping) else prior.value)
    value = fy_net + current_net - prior_net
    reconstruction = {"formula": rule["current_formula"], "fy": _fact_source(fy), "current_ytd": _fact_source(current), "prior_ytd": _fact_source(prior), "value": value}
    if rule.get('net_income_from_pretax'):
        reconstruction.update({"fy_tax": _fact_source(tax_annual), "current_ytd_tax": _fact_source(tax_current), "prior_ytd_tax": _fact_source(tax_prior)})
    return value, reconstruction


def _current_shares(normalizer: CompanyFactsNormalizer, selected: Mapping[str, Any], structural: Mapping[str, Any] | None) -> tuple[float, dict[str, Any]]:
    annual = normalizer.annual_series("diluted_shares_refresh", 20)
    if not annual:
        raise ValueError("current weighted-average diluted shares have no annual anchor")
    if annual[-1].end == selected['period_end']:
        current = annual[-1]
        if current.accession != selected['accession'] or current.start != selected['period_start']:
            raise ValueError('current annual diluted shares do not match selected filing')
        return float(current.value), {'formula':'current reported fiscal-year weighted-average diluted shares','current':_fact_source(current),'prior_comparable':None}
    current, prior = _aligned_pair(normalizer, "diluted_shares_refresh", annual[-1].end, selected, structural, structural_name="WeightedAverageNumberOfDilutedSharesOutstanding", unit="xbrli:shares")
    value = float(current["value"] if isinstance(current, Mapping) else current.value)
    return value, {"formula": "current selected-period reported weighted-average diluted shares; no additive TTM shares", "current": _fact_source(current), "prior_comparable": _fact_source(prior)}


def bind_earnings_recipe(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, cutoff: str) -> dict[str, Any]:
    ticker = str(policy.get("ticker", ""))
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError("policy is not an ordinary earnings policy")
    if recipe.get('ticker') != ticker or recipe.get('evidence_cutoff','') > cutoff:
        raise ValueError('earnings recipe identity or evidence cutoff mismatch')
    selected, records = _selected_filing(policy, packet, cutoff)
    companyfacts = packet["companyfacts"]
    structural = packet.get("structural_filing") or packet.get("structural")
    if isinstance(structural, Mapping) and structural.get("source_accession") != selected["accession"]:
        raise ValueError("structural source does not match selected controlling filing")
    if isinstance(structural, Mapping):
        _validate_structural_identity(structural, cik=str(policy["cik"]), accession=str(selected["accession"]))
    normalizer = CompanyFactsNormalizer(companyfacts, concept_config=_config(RULES[ticker]), fiscal_year_end=packet["submissions"].get("fiscalYearEnd"), as_of_date=cutoff, filing_records=records)
    metric, history_sources = _history_metric(normalizer, ticker, RULES[ticker])
    current_value, current_reconstruction = _current_reconstruction(normalizer, ticker, RULES[ticker], selected, structural)
    source_shares, share_source = _current_shares(normalizer, selected, structural)
    approved = policy["approved_sensitivities"]
    normalized_earnings = [float(metric.low), float(metric.base), float(metric.high)]
    scenarios: dict[str, dict[str, Any]] = {}
    for name, earnings, multiple, share_multiplier in zip(("bear", "base", "bull"), normalized_earnings, approved["multiples"], approved["share_multipliers"]):
        original = recipe["scenarios"][name]
        inputs = deepcopy(original["inputs"])
        inputs.update({"earnings": earnings, "multiple": float(multiple), "shares": source_shares * float(share_multiplier), "net_bridge": 0.0})
        scenarios[name] = {"engine": "earnings_multiple", **({"equity_floor": original["equity_floor"]} if original.get("equity_floor") else {}), "inputs": inputs}
    bound = deepcopy(recipe)
    bound["scenarios"] = scenarios
    bound['source_accession'] = selected['accession']
    bound['evidence_cutoff'] = cutoff
    replay = evaluate_recipe(bound)["range"]
    return {
        "status": "bound_successor_candidate",
        "recipe": bound,
        "replay": replay,
        "source_ledger": {
            "controlling_filing": selected,
            "current_earnings_reconstruction": current_reconstruction,
            "normalized_history": history_sources,
            "current_shares": share_source,
            "history_normalization": {"low": metric.low, "base": metric.base, "high": metric.high, "positive_history_only": RULES[ticker]["positive_history_only"]},
            "scope": RULES[ticker]["scope"],
            "ev_debt_bridge_applied": False,
        },
    }


__all__ = ["RULES", "SCHEMA", "SUPPORTED_TICKERS", "bind_earnings_recipe", "compile_earnings_refresh_policy"]
