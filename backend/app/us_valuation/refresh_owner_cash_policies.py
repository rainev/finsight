"""Source-bound owner-cash policies for META, OMC, and TTWO.

These issuers use the earnings-multiple calculator as an owner-cash proxy.
Their operating cash states, bridge facts, and timing/commitment overlays remain
distinct issuer rules; consolidated net income is never substituted.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import math
from typing import Any, Mapping

from .calculation_recipe import evaluate_recipe
from .sec_client import normalize_cik


SCHEMA = "FINSIGHT-OWNER-CASH-REFRESH-POLICY-1"
SUPPORTED_TICKERS = frozenset({"META", "OMC", "TTWO"})


RULES: dict[str, dict[str, Any]] = {
    "META": {
        "family": "ai_capex_cash_conversion_equity_multiple",
        "flow_period": "interim_longest_duration",
        "annualization": "12_months_over_selected_fiscal_months",
        "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",),
        "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
        "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
        "cash": ("CashAndCashEquivalentsAtCarryingValue", "MarketableSecuritiesCurrent"),
        "debt": ("LongTermDebt",),
        "claims": (),
        "shares": "weighted_average_diluted_duration",
        "cash_states": (0.13, 0.25, 0.35),
        "reserve_binding": None,
        "scope": "AI infrastructure commitments are captured in governed cash-conversion states and are not deducted again as a second claim.",
        "exception": "The positive 25%/35% cash states and original timing-claim overlay remain approved hypothetical policy states, not reported guidance.",
    },
    "OMC": {
        "family": "post_combination_normalized_fcff_multiple",
        "flow_period": "interim_longest_duration",
        "annualization": "12_months_over_selected_fiscal_months",
        "operating_income": ("OperatingIncomeLoss",),
        "depreciation": ("DepreciationAndAmortization", "DepreciationDepletionAndAmortization"),
        "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
        "cash": ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",),
        "debt": ("DebtInstrumentCarryingAmount",),
        "claims": ("MinorityInterest",),
        "shares": "entity_common_stock_shares_outstanding",
        "tax_rate": 0.24,
        "reserve_binding": None,
        "scope": "Post-combination owner cash is normalized from reported operating income, D&A, and capex; NCI and debt remain separate bridge claims.",
        "exception": "Comparable combined history is short; the 24% tax rate, multiple band, and timing lease reserve remain approved policy assumptions.",
    },
    "TTWO": {
        "family": "major_release_outcome_equity_cash_multiple",
        "flow_period": "interim_latest_quarter",
        "annualization": "12_months_over_selected_fiscal_months",
        "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",),
        "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
        "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
        "cash": ("CashAndCashEquivalentsAtCarryingValue", "ShortTermInvestments"),
        "debt": ("DebtLongtermAndShorttermCombinedAmount",),
        "claims": (),
        "shares": "entity_common_stock_shares_outstanding",
        "cash_states": (0.05, 0.15, 0.25),
        "claim_rates": (0.05, 0.025, 0.0),
        "total_assets": ("Assets",),
        "scope": "Quarter owner-cash states are hypothetical major-release outcomes; negative current quarter OCF is retained as a diagnostic and not converted to reported owner cash.",
        "exception": "GTA VI/release timing, margins, and unresolved-claim reserves remain specialist policy assumptions pending post-release cash evidence.",
    },
}


def _records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    return [{key: values[i] for key, values in recent.items() if isinstance(values, list) and i < len(values)} for i in range(len(recent.get("accessionNumber", [])))]


def _selected(policy: Mapping[str, Any], packet: Mapping[str, Any], cutoff: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    submissions, companyfacts, selected = packet.get("submissions"), packet.get("companyfacts"), packet.get("_selected_controlling_filing")
    if not isinstance(submissions, Mapping) or not isinstance(companyfacts, Mapping) or not isinstance(selected, Mapping):
        raise ValueError("owner-cash refresh requires source packets and dispatcher-selected filing")
    cik = normalize_cik(policy.get('cik',''))
    if normalize_cik(submissions.get('cik','')) != cik or normalize_cik(companyfacts.get('cik','')) != cik:
        raise ValueError("owner-cash issuer identity conflict")
    accession, period_end = str(selected.get("accession", "")), str(selected.get("period_end", ""))
    if not accession or not period_end:
        raise ValueError("selected owner-cash filing requires accession and period_end")
    try:
        cutoff_date = date.fromisoformat(cutoff)
        date.fromisoformat(period_end)
    except ValueError as exc:
        raise ValueError("invalid owner-cash cutoff or period_end") from exc
    if date.fromisoformat(period_end) > cutoff_date:
        raise ValueError('owner-cash financial period is after cutoff')
    records = _records(submissions)
    matches = [row for row in records if row.get("accessionNumber") == accession and row.get("reportDate") == period_end and row.get("filingDate", "") <= cutoff and row.get("form") in {"10-Q", "10-Q/A", "10-K", "10-K/A"}]
    if len(matches) != 1:
        raise ValueError("selected owner-cash filing is not one eligible filing")
    if date.fromisoformat(matches[0]["filingDate"]) > cutoff_date:
        raise ValueError("selected owner-cash filing is outside cutoff")
    return {**selected, "filing_date": matches[0].get("filingDate"), "form": matches[0].get("form")}, records


def compile_owner_cash_policy(recipe: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    ticker = str(recipe.get("ticker", ""))
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"unsupported owner-cash ticker: {ticker}")
    if any(spec.get("engine") != "earnings_multiple" for spec in recipe.get("scenarios", {}).values()):
        raise ValueError("owner-cash recipe must use earnings_multiple")
    rule = RULES[ticker]
    return {
        "schema_version": SCHEMA,
        "version": f"{SCHEMA}-{ticker}",
        "ticker": ticker,
        "cik": str(registry_entry.get("cik", "")).zfill(10),
        "family": rule["family"],
        "policy_status": "source_validation_pending" if rule.get("reserve_binding") is not None or ticker == "TTWO" else "blocked_source_reserve_rule",
        "flow_period_rule": rule["flow_period"],
        "annualization_rule": rule["annualization"],
        "approved_multiples": [float(recipe["scenarios"][name]["inputs"]["multiple"]) for name in ("bear", "base", "bull")],
        "approved_share_multipliers": [float(recipe["scenarios"][name]["inputs"]["shares"]) / float(recipe["scenarios"]["base"]["inputs"]["shares"]) for name in ("bear", "base", "bull")],
        "source_selectors": {key: list(value) if isinstance(value, tuple) else value for key, value in rule.items() if key in {"revenue", "operating_cash_flow", "capex", "operating_income", "depreciation", "cash", "debt", "claims", "shares", "total_assets"}},
        "fixed_assumptions": {key: value for key, value in rule.items() if key in {"cash_states", "tax_rate", "claim_rates"}},
        "bridge_rule": "current source cash/debt/claims; TTWO claims are current Assets times the recorded reserve-rate policy. META/OMC require an explicit source-backed timing waterfall before numeric binding.",
        "scope": rule["scope"],
        "economic_exception": rule["exception"],
        "baseline_binding": {"baseline_version": recipe.get("baseline_version"), "baseline_sha256": registry_entry.get("baseline_sha256"), "evidence_cutoff": recipe.get("evidence_cutoff"), "source_accession": recipe.get("source_accession"), "source_path": (recipe.get("provenance") or {}).get("source_path")},
    }


def _rows(structural: Mapping[str, Any], *, names: tuple[str, ...], period_end: str, accession: str, period_start: str | None, unit: str) -> list[dict[str, Any]]:
    facts = structural.get("facts") if isinstance(structural, Mapping) else None
    if not isinstance(facts, list):
        return []
    out = []
    for row in facts:
        if not isinstance(row, Mapping) or row.get("local_name") not in names or row.get("period_end") != period_end or row.get("source_accession") != accession or row.get("unit") != unit or row.get("dimensions") not in ([], None):
            continue
        qname = str(row.get("qname", ""))
        if qname != f"us-gaap:{row.get('local_name')}" or not str(row.get('namespace','')).startswith(('http://fasb.org/us-gaap/','https://fasb.org/us-gaap/')):
            continue
        if period_start not in (None, "*") and row.get("period_start") != period_start:
            continue
        if period_start is None and row.get("period_start") is not None:
            continue
        if isinstance(row.get('value'),bool) or not isinstance(row.get("value"), (int, float)) or not math.isfinite(float(row["value"])):
            continue
        out.append(dict(row))
    unique = {(row.get("local_name"), row.get("value"), row.get("period_start"), row.get("context_id")): row for row in out}
    return list(unique.values())


def _one(structural: Mapping[str, Any], *, names: tuple[str, ...], period_end: str, accession: str, period_start: str | None, unit: str) -> dict[str, Any]:
    rows = _rows(structural, names=names, period_end=period_end, accession=accession, period_start=period_start, unit=unit)
    if not rows:
        raise ValueError(f"required owner-cash fact missing: {names}")
    if len(rows) != 1:
        raise ValueError(f"ambiguous owner-cash fact: {names}")
    return rows[0]


def _latest_instant(structural: Mapping[str, Any], *, names: tuple[str, ...], accession: str, cutoff: str, unit: str) -> dict[str, Any]:
    facts = structural.get("facts") if isinstance(structural, Mapping) else None
    if not isinstance(facts, list):
        raise ValueError("owner-cash structural facts missing")
    cutoff_date = date.fromisoformat(cutoff)
    rows = [
        row for row in facts
        if isinstance(row, Mapping)
        and row.get("local_name") in names
        and row.get("source_accession") == accession
        and row.get("period_start") is None
        and row.get("unit") == unit
        and row.get("dimensions") in ([], None)
        and isinstance(row.get("period_end"), str)
        and date.fromisoformat(row["period_end"]) <= cutoff_date
        and isinstance(row.get("value"), (int, float))
        and math.isfinite(float(row["value"]))
        and row.get("namespace")
        and str(row.get("qname", "")).endswith(f":{row.get('local_name')}" )
    ]
    unique = {(row.get("value"), row.get("period_end"), row.get("context_id")): row for row in rows}
    rows = list(unique.values())
    if not rows:
        raise ValueError(f"owner-cash instant share fact missing: {names}")
    latest_end = max(date.fromisoformat(row["period_end"]) for row in rows)
    latest = [row for row in rows if date.fromisoformat(row["period_end"]) == latest_end]
    if len(latest) != 1:
        raise ValueError(f"owner-cash instant share fact ambiguous: {names}")
    return latest[0]


def _source(row: Mapping[str, Any]) -> dict[str, Any]:
    return {"concept": row.get("qname") or row.get("local_name"), "value": float(row["value"]), "unit": row.get("unit"), "period_start": row.get("period_start"), "period_end": row.get("period_end"), "accession": row.get("source_accession"), "reported_vs_estimated": "reported"}


def _flow_period(structural: Mapping[str, Any], rule: Mapping[str, Any], *, period_end: str, accession: str) -> tuple[str, int]:
    seed_names = tuple(rule.get("revenue") or rule.get("operating_income") or ())
    candidates = _rows(structural, names=seed_names, period_end=period_end, accession=accession, period_start="*", unit="USD")
    if not candidates:
        raise ValueError("owner-cash flow period seed missing")
    starts = sorted({row.get("period_start") for row in candidates if row.get("period_start")})
    if not starts:
        raise ValueError("owner-cash flow period has no duration start")
    durations = [(start, (date.fromisoformat(period_end) - date.fromisoformat(start)).days + 1) for start in starts]
    if rule["flow_period"] == "interim_latest_quarter":
        start, days = min(durations, key=lambda item: item[1])
    else:
        start, days = max(durations, key=lambda item: item[1])
    start_date, end_date = date.fromisoformat(str(start)), date.fromisoformat(period_end)
    if start_date.day != 1:
        raise ValueError("owner-cash duration does not start on a fiscal month boundary")
    expected_month_end = date(end_date.year, end_date.month + 1, 1) if end_date.month < 12 else date(end_date.year + 1, 1, 1)
    if (expected_month_end - end_date).days != 1:
        raise ValueError("owner-cash duration does not end on a fiscal month boundary")
    months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    if months not in {3, 6, 9, 12}:
        raise ValueError("unsupported owner-cash fiscal duration")
    return str(start), months


def _validate_structural(structural: Mapping[str, Any], receipt: Mapping[str, Any], *, accession: str, cik: str) -> None:
    if structural.get("source_accession") != accession:
        raise ValueError("owner-cash structural accession mismatch")
    if receipt and (str(receipt.get("cik", "")).zfill(10) != str(cik).zfill(10) or receipt.get("filing", {}).get("accession") != accession):
        raise ValueError("owner-cash structural receipt identity mismatch")
    facts = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("source_accession") == accession]
    if not facts:
        raise ValueError("owner-cash structural facts missing selected accession")
    for row in facts:
        if normalize_cik(row.get('entity_identifier','')) != normalize_cik(cik) or row.get('entity_scheme') != 'http://www.sec.gov/CIK':
            raise ValueError("owner-cash structural issuer identity mismatch")


def bind_owner_cash_recipe(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, cutoff: str) -> dict[str, Any]:
    ticker = str(policy.get("ticker", ""))
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError("policy is not owner-cash family")
    selected, records = _selected(policy, packet, cutoff)
    if ticker != 'TTWO':
        raise RuntimeError(f'{ticker}: source-backed timing/commitment reserve waterfall is not implemented')
    if recipe.get('ticker') != ticker or recipe.get('evidence_cutoff','') > cutoff:
        raise ValueError('owner-cash recipe identity or cutoff mismatch')
    structural = packet.get("structural_filing") or packet.get("structural")
    if not isinstance(structural, Mapping):
        raise ValueError("owner-cash structural source is required")
    receipt = packet.get('structural_receipt', {})
    if not isinstance(receipt, Mapping):
        raise ValueError('invalid structural source receipt')
    _validate_structural(structural, receipt, accession=selected["accession"], cik=str(policy["cik"]))
    rule = RULES[ticker]
    if ticker != "TTWO":
        raise RuntimeError(f"{ticker}: source-backed timing/commitment reserve waterfall is not implemented")
    start, months = _flow_period(structural, rule, period_end=selected["period_end"], accession=selected["accession"])
    factor = 12.0 / months
    flows: dict[str, dict[str, Any]] = {}
    for field in ("revenue", "operating_cash_flow", "capex", "operating_income", "depreciation"):
        names = rule.get(field)
        if names:
            flows[field] = _source(_one(structural, names=tuple(names), period_end=selected["period_end"], accession=selected["accession"], period_start=start, unit="USD"))
    bridge: dict[str, dict[str, Any]] = {}
    for field in ("cash", "debt", "claims"):
        names = tuple(rule.get(field) or ())
        if not names:
            continue
        for name in names:
            row = _one(structural, names=(name,), period_end=selected["period_end"], accession=selected["accession"], period_start=None, unit="USD")
            bridge[name] = _source(row)
    source_cash = sum(float(bridge[name]["value"]) for name in rule.get("cash", ()))
    source_debt = sum(float(bridge[name]["value"]) for name in rule.get("debt", ()))
    source_claims = sum(float(bridge[name]["value"]) for name in rule.get("claims", ()))
    if ticker in {"META", "TTWO"}:
        owner_cash_base = float(flows["revenue"]["value"]) * factor
        cash_states = tuple(policy["fixed_assumptions"]["cash_states"])
        owner_cash = [owner_cash_base * float(margin) for margin in cash_states]
    else:
        tax = float(policy["fixed_assumptions"]["tax_rate"])
        owner_cash_base = (float(flows["operating_income"]["value"]) * factor * (1.0 - tax) + float(flows["depreciation"]["value"]) * factor - float(flows["capex"]["value"]) * factor)
        owner_cash = [owner_cash_base] * 3
    if policy["source_selectors"]["shares"] == "weighted_average_diluted_duration":
        share_row = _one(structural, names=("WeightedAverageNumberOfDilutedSharesOutstanding",), period_end=selected["period_end"], accession=selected["accession"], period_start=start, unit="xbrli:shares")
    else:
        share_row = _latest_instant(structural, names=("EntityCommonStockSharesOutstanding",), accession=selected["accession"], cutoff=cutoff, unit="xbrli:shares")
    source_shares = float(share_row["value"])
    approved_multiples = policy["approved_multiples"]
    share_multipliers = policy["approved_share_multipliers"]
    scenarios: dict[str, dict[str, Any]] = {}
    source_bridge_before_overlay = source_cash - source_debt - source_claims
    assets_row = _one(structural, names=tuple(rule["total_assets"]), period_end=selected["period_end"], accession=selected["accession"], period_start=None, unit="USD")
    source_assets = float(assets_row["value"])
    claim_rates = tuple(policy["fixed_assumptions"]["claim_rates"])
    bridge_sources = {"cash": source_cash, "debt": source_debt, "other_reported_claims": source_claims, "assets": _source(assets_row), "components": bridge, "source_bridge_before_reserve": source_bridge_before_overlay, "reserve_formula": "selected current Assets times approved TTWO reserve rate"}
    for index, (name, earnings, multiple, share_multiplier) in enumerate(zip(("bear", "base", "bull"), owner_cash, approved_multiples, share_multipliers)):
        original = recipe["scenarios"][name]
        inputs = deepcopy(original["inputs"])
        reserve = source_assets * float(claim_rates[index])
        inputs.update({"earnings": float(earnings), "multiple": float(multiple), "shares": source_shares * float(share_multiplier), "net_bridge": source_bridge_before_overlay - reserve})
        scenarios[name] = {"engine": "earnings_multiple", "inputs": inputs}
    bound = deepcopy(recipe)
    bound["scenarios"] = scenarios
    bound['source_accession'] = selected['accession']
    bound['evidence_cutoff'] = cutoff
    replay = evaluate_recipe(bound)["range"]
    return {"status": "bound_successor_candidate", "recipe": bound, "replay": replay, "source_ledger": {"controlling_filing": selected, "flow_period": {"period_start": start, "period_end": selected["period_end"], "fiscal_months": months, "annualization_factor": factor}, "flows": flows, "bridge": bridge_sources, "shares": _source(share_row), "owner_cash_formula": "TTWO: selected revenue times annualization factor times approved cash margin", "scope": rule["scope"], "economic_exception": rule["exception"]}}


__all__ = ["RULES", "SCHEMA", "SUPPORTED_TICKERS", "bind_owner_cash_recipe", "compile_owner_cash_policy"]
