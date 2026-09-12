"""Declarative refresh policies for specialized equity-earnings/runway families."""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping
from copy import deepcopy

from .calculation_recipe import evaluate_recipe
from .xbrl import CompanyFactsNormalizer, load_concept_config


SCHEMA = "FINSIGHT-SPECIAL-REFRESH-POLICY-1"

EQUITY_EARNINGS = {"APTV", "CVNA", "DHI", "F", "GM", "HONA", "LEN", "NVR", "PHM"}
OWNER_CASH = {"META", "OMC", "TTWO"}
ASSET_RUNWAY = {"MRNA"}
EVENT_ENVELOPE = {"WBD"}


def _lineage(kind: str, selector: str, meaning: str) -> dict[str, Any]:
    return {"kind": kind, "selector": selector, "meaning": meaning, "source_selector_required": True}


def compile_special_refresh_policy(recipe: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    ticker = str(recipe.get("ticker"))
    if ticker == "APTV":
        base_earnings = recipe["scenarios"]["base"]["inputs"]["earnings"]
        base_shares = recipe["scenarios"]["base"]["inputs"]["shares"]
        family = "post_spin_parent_attributable_continuing_equity_earnings"
        inputs = {
            "parent_continuing_earnings": _lineage("reported_parent_attributable", "current_and_comparative_ytd_parent_earnings", "Use continuing parent-attributable income; NCI is diagnostic only and is not subtracted again."),
            "shares": _lineage("reported", "current_weighted_average_diluted_shares", "Use the current continuing-period reported weighted average; scenario dilution is an approved fixed sensitivity."),
            "multiple": _lineage("approved_fixed_policy", "fixed_earnings_multiple_policy", "6x/8x/10x are approved policy states, not refreshed market data."),
        }
        # Main refresh dispatcher must supply the selected filing; the field
        # concepts are constrained to the continuing parent-attributable line.
        approved = {"earnings_multipliers": [recipe["scenarios"][name]["inputs"]["earnings"] / base_earnings for name in ("bear", "base", "bull")], "share_multipliers": [recipe["scenarios"][name]["inputs"]["shares"] / base_shares for name in ("bear", "base", "bull")], "multiples": [recipe["scenarios"][name]["inputs"]["multiple"] for name in ("bear", "base", "bull")]}
        unresolved = []
    elif ticker in EQUITY_EARNINGS:
        family = "normalized_parent_or_consolidated_equity_earnings"
        inputs = {
            "normalized_earnings": _lineage("reported_or_history_normalized_earnings", "parent_attributable_earnings_history", "Use issuer-specific parent/common earnings when available; do not substitute generic net income."),
            "multiple": _lineage("approved_fixed_policy", "fixed_multiple_policy", "Refresh only through explicit issuer/model policy review."),
            "shares": _lineage("reported", "current_reported_weighted_average_or_cover_plus_awards", "Use current reported denominator; never additive TTM share arithmetic."),
        }
        unresolved = ["preferred/NCI and specialty finance scope require issuer-specific review before policy promotion"]
    elif ticker in OWNER_CASH:
        family = "owner_cash_multiple_with_explicit_bridge"
        inputs = {
            "owner_cash": _lineage("reported_or_governed_owner_cash", "issuer_specific_cash_conversion_or_normalized_fcff", "Owner cash is not consolidated net income; preserve issuer formula."),
            "multiple": _lineage("approved_fixed_policy", "fixed_cash_multiple_policy", "Refresh only through explicit model policy review."),
            "cash_claim": _lineage("reported", "current_cash_and_securities", "Use current issuer cash/securities bridge."),
            "debt_claim": _lineage("reported", "current_debt_and_finance_leases", "Use current issuer debt/lease bridge."),
            "other_claims": _lineage("reported_or_governed", "NCI_lease_reserve_commitment_claims", "Keep issuer-specific claims separate and visible."),
            "shares": _lineage("reported", "current_reported_weighted_average_or_cover_plus_awards", "Use current reported denominator."),
        }
        unresolved = ["owner-cash history and event/commitment claim scope require issuer-specific review before policy promotion"]
    elif ticker in ASSET_RUNWAY:
        family = "liquid_assets_less_burn_and_debt_plus_pipeline"
        inputs = {
            "liquid_assets": _lineage("reported", "current_liquid_assets", "Use issuer cash/securities and exclude customer-restricted assets."),
            "cash_burn_reserve": _lineage("history_or_governed", "reported_cash_burn_history_and_policy_reserve", "Recompute burn range from comparable history."),
            "debt_and_finance_leases": _lineage("reported", "current_debt_and_finance_leases", "Use current issuer debt/lease bridge."),
            "pipeline_terminal_value": _lineage("event_or_specialist", "approved_pipeline_value", "No pipeline value is a valid zero by default; unresolved clinical pipeline remains a review blocker."),
            "shares": _lineage("reported", "current_reported_weighted_average_or_cover_plus_awards", "Use current reported denominator."),
        }
        unresolved = ["clinical pipeline events, legal/regulatory claims and burn normalization require specialist review"]
    elif ticker in EVENT_ENVELOPE:
        family = "standalone_cash_flow_plus_separate_contract_event"
        inputs = {
            "standalone_cash_flow": _lineage("reported_or_history_normalized", "standalone_fcff_history", "Rebuild standalone value from current issuer cash flow."),
            "contract_consideration": _lineage("event", "filed_merger_consideration_and_ticking_cash", "Keep contractual cash separate; never probability-weight into intrinsic value."),
            "shares": _lineage("reported", "current_reported_weighted_average_or_cover_plus_awards", "Use current reported denominator."),
        }
        unresolved = ["merger close/termination/amendment and standalone/separation state require explicit event review"]
    else:
        raise ValueError(f"unsupported special policy ticker: {ticker}")
    return {
        "schema_version": SCHEMA,
        "version": f"{SCHEMA}-{ticker}",
        "ticker": ticker,
        "cik": registry_entry.get("cik"),
        "family": family,
        "policy_status": "mapped_requires_source_reselection",
        "baseline_binding": {
            "baseline_version": recipe.get("baseline_version"),
            "baseline_sha256": registry_entry.get("baseline_sha256"),
            "evidence_cutoff": recipe.get("evidence_cutoff"),
            "source_accession": recipe.get("source_accession") or (registry_entry.get("controlling_filing") or {}).get("accession"),
        },
        "inputs": inputs,
        **({"statement_required_fields": {"parent_continuing_earnings": "flow", "diluted_shares": "flow", "period_end_equity": "instant"}, "concept_config": {"fields": {"parent_continuing_earnings": {"concepts": ["IncomeLossFromContinuingOperations"], "unit": "USD", "kind": "flow"}, "diluted_shares": {"concepts": ["WeightedAverageNumberOfDilutedSharesOutstanding"], "unit": "shares", "kind": "flow"}, "period_end_equity": {"concepts": ["StockholdersEquity"], "unit": "USD", "kind": "instant"}}}} if ticker == "APTV" else {}),
        "approved_sensitivities": locals().get("approved", {}),
        "source_requirements": {"structural":True,"event_exhibits":True},
        "unresolved_economic_rules": unresolved,
        "consumer_integration": "not_claimed",
    }


def bind_aptv_special_recipe(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, cutoff: str) -> dict[str, Any]:
    """Bind APTV's post-spin parent-attributable recipe from selected SEC facts.

    The controlling filing is selected by the refresh dispatcher.  This binder
    deliberately does not rediscover a period from a cached packet: doing that
    would make a changed quarter silently replay the old H1 recipe.  The
    current and comparative observations must be from the selected accession,
    with matching fiscal starts/ends, and the annualization factor is derived
    from those dates rather than stored as an APTV-specific constant.
    """
    if policy.get("ticker") != "APTV" or policy.get("family") != "post_spin_parent_attributable_continuing_equity_earnings":
        raise ValueError("policy is not APTV post-spin family")
    submissions, companyfacts = packet["submissions"], packet["companyfacts"]
    policy_cik = str(policy.get("cik", "")).zfill(10)
    if str(companyfacts.get("cik", "")).zfill(10) != policy_cik or str(submissions.get("cik", "")).zfill(10) != policy_cik:
        raise ValueError("APTV packet CIK mismatch")
    try:
        cutoff_date = date.fromisoformat(cutoff)
    except (TypeError, ValueError) as exc:
        raise ValueError("APTV cutoff must be an ISO date") from exc
    recent = submissions.get("filings", {}).get("recent", {})
    rows = [{key: values[i] for key, values in recent.items() if isinstance(values, list) and i < len(values)} for i in range(len(recent.get("accessionNumber", [])))]
    selected = packet.get("_selected_controlling_filing")
    if not isinstance(selected, Mapping):
        raise ValueError("APTV dispatcher must provide _selected_controlling_filing")
    accession = str(selected.get("accession", ""))
    period_end = str(selected.get("period_end", ""))
    period_start = selected.get("period_start")
    if period_start is None:
        # Submissions contain report dates, not duration starts. Derive the
        # start from the issuer's actual cumulative fact, never the batch date.
        fact_rows = companyfacts.get('facts', {}).get('us-gaap', {}).get('IncomeLossFromContinuingOperations', {}).get('units', {}).get('USD', [])
        starts = {row['start'] for row in fact_rows if row.get('accn') == accession and row.get('end') == period_end
                  and row.get('filed', '') <= cutoff and isinstance(row.get('start'), str) and row['start'].endswith('-01-01')}
        if len(starts) == 1:
            period_start = starts.pop()
    if not accession or not period_end or not period_start:
        raise ValueError("APTV selected filing requires accession, period_start, and period_end")
    try:
        selected_end = date.fromisoformat(period_end)
        selected_start = date.fromisoformat(str(period_start))
    except (TypeError, ValueError) as exc:
        raise ValueError("APTV selected filing has invalid period dates") from exc
    if selected_end > cutoff_date or selected_start >= selected_end:
        raise ValueError("APTV selected filing is outside cutoff or has invalid period")
    selected_rows = [
        row for row in rows
        if row.get("accessionNumber") == accession
        and row.get("filingDate", "") <= cutoff
        and row.get("reportDate") == period_end
        and row.get("form") in {"10-Q", "10-Q/A", "10-K", "10-K/A"}
    ]
    if len(selected_rows) != 1:
        raise ValueError("APTV selected accession is not one unique eligible SEC filing")
    selected_row = selected_rows[0]
    config = load_concept_config()
    config.setdefault("fields", {}).update({
        "parent_continuing_earnings": {"unit": "USD", "kind": "flow", "concepts": ["IncomeLossFromContinuingOperations"]},
        "diluted_shares": {"unit": "shares", "kind": "flow", "concepts": ["WeightedAverageNumberOfDilutedSharesOutstanding"]},
    })
    normalizer = CompanyFactsNormalizer(companyfacts, concept_config=config, fiscal_year_end=submissions.get("fiscalYearEnd"), as_of_date=cutoff, filing_records=rows)

    def _period_months(start: date, end: date) -> tuple[int, float]:
        days = (end - start).days + 1
        if start.month != 1 or start.day != 1:
            raise ValueError("APTV refresh supports calendar-year periods only")
        if 330 <= days <= 385 and end.month == 12 and end.day == 31:
            return 12, 1.0
        if not 70 <= days <= 310:
            raise ValueError("APTV selected period is not a supported annual or calendar YTD period")
        months = end.month
        expected_end = date(end.year, end.month, end.day)
        quarter_ends = {3: 31, 6: 30, 9: 30}
        if end.month not in quarter_ends or end.day != quarter_ends[end.month] or expected_end < date(end.year, 3, 31):
            raise ValueError("APTV selected YTD period must end at a calendar quarter")
        return months, 12.0 / months

    selected_start = date.fromisoformat(str(period_start))
    selected_end = date.fromisoformat(period_end)
    months, annualization_factor = _period_months(selected_start, selected_end)
    annual = normalizer.annual_series("parent_continuing_earnings", 20)
    if annualization_factor == 1.0:
        current_parent = normalizer.annual_at_end("parent_continuing_earnings", period_end)
        prior_end = date(selected_end.year - 1, selected_end.month, selected_end.day).isoformat()
        prior_parent = normalizer.annual_at_end("parent_continuing_earnings", prior_end)
        current_share = normalizer.annual_at_end("diluted_shares", period_end)
        if current_parent is None or prior_parent is None or current_share is None:
            raise ValueError("APTV annual selector did not resolve current and comparative periods")
        prior_start = date(selected_start.year - 1, selected_start.month, selected_start.day).isoformat()
        prior_end = date(selected_end.year - 1, selected_end.month, selected_end.day).isoformat()
        if (
            current_parent.accession != accession
            or prior_parent.accession != accession
            or current_share.accession != accession
            or current_parent.start != str(period_start)
            or current_parent.end != period_end
            or current_share.start != str(period_start)
            or current_share.end != period_end
            or prior_parent.accession != accession
            or prior_parent.start != prior_start
            or prior_parent.end != prior_end
        ):
            raise ValueError("APTV annual facts do not match selected controlling filing")
    else:
        pair = normalizer.latest_ytd_pair("parent_continuing_earnings", after_end=annual[-1].end) if annual else None
        share_pair = normalizer.latest_ytd_pair("diluted_shares", after_end=annual[-1].end) if annual else None
        if pair is None or share_pair is None:
            raise ValueError("APTV current/prior YTD selector did not resolve to controlling filing")
        current_parent, prior_parent = pair
        current_share = share_pair[0]
        prior_start = date(selected_start.year - 1, selected_start.month, selected_start.day).isoformat()
        prior_end = date(selected_end.year - 1, selected_end.month, selected_end.day).isoformat()
        if (
            current_parent.accession != accession
            or current_share.accession != accession
            or current_parent.start != str(period_start)
            or current_parent.end != period_end
            or current_share.start != str(period_start)
            or current_share.end != period_end
            or prior_parent.start != prior_start
            or prior_parent.end != prior_end
            or share_pair[1].start != prior_start
            or share_pair[1].end != prior_end
        ):
            raise ValueError("APTV current/prior YTD periods do not match selected controlling filing")
    if current_parent.concept != "IncomeLossFromContinuingOperations":
        raise ValueError("APTV earnings selector did not resolve the parent continuing-operations concept")
    if current_share.concept != "WeightedAverageNumberOfDilutedSharesOutstanding":
        raise ValueError("APTV share selector did not resolve current reported diluted shares")
    current_shares = current_share.value
    approved = policy["approved_sensitivities"]
    scenarios = {}
    for name, multiple, earn_mult, share_mult in zip(("bear", "base", "bull"), approved["multiples"], approved["earnings_multipliers"], approved["share_multipliers"]):
        scenarios[name] = {"engine": "earnings_multiple", "inputs": {"earnings": current_parent.value * annualization_factor * earn_mult, "multiple": multiple, "shares": current_shares * share_mult, "net_bridge": 0.0}}
    bound = dict(recipe)
    bound["scenarios"] = scenarios
    bound['evidence_cutoff'] = cutoff
    bound['source_accession'] = accession
    replay = evaluate_recipe(bound)["range"]
    return {"status": "bound_successor_candidate", "recipe": bound, "replay": replay, "source_ledger": {"controlling_accession": accession, "selected_filing": {"accession": accession, "filing_date": selected_row.get("filingDate"), "form": selected_row.get("form"), "period_start": str(period_start), "period_end": period_end}, "current_parent_earnings": current_parent.as_dict(), "prior_parent_earnings": prior_parent.as_dict(), "annualization_factor": annualization_factor, "fiscal_months": months, "nci_subtracted_again": False, "current_shares": current_share.as_dict()}}


def compile_special_inventory(recipes: Mapping[str, Mapping[str, Any]], registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    policies = []
    gaps = []
    for ticker, recipe in sorted(recipes.items()):
        if ticker not in EQUITY_EARNINGS | OWNER_CASH | ASSET_RUNWAY | EVENT_ENVELOPE:
            continue
        entry = registry.get(ticker)
        if entry is None:
            gaps.append({"ticker": ticker, "reason": "registry_entry_missing"})
            continue
        try:
            policies.append(compile_special_refresh_policy(recipe, entry))
        except ValueError as exc:
            gaps.append({"ticker": ticker, "reason": str(exc)})
    return {"schema_version": SCHEMA, "policy_count": len(policies), "policies": policies, "gaps": gaps}


def evaluate_bound_special_recipe(recipe: Mapping[str, Any], bound_scenarios: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Apply caller-selected source inputs and evaluate the new recipe.

    The caller is responsible for obtaining ``bound_scenarios`` from the main
    filing/structural selector.  This function deliberately does not accept or
    derive target values.
    """
    bound = deepcopy(recipe)
    for name, source_inputs in bound_scenarios.items():
        if name not in bound["scenarios"] or not isinstance(source_inputs, Mapping):
            raise ValueError(f"unsupported special scenario: {name}")
        bound["scenarios"][name]["inputs"].update(source_inputs)
    result = evaluate_recipe(bound)
    return {"recipe": bound, "replay": result["range"], "source_binding": "caller_selected"}
