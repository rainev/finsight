"""Compile declarative refresh-policy evidence from frozen calculation recipes.

The output is a refresh contract, not a serving artifact and not a claim that a
recipe is production-ready.  Baseline values remain bound to the frozen
evidence cutoff; a future run must reselect filing facts/history/events and
revalidate every policy assumption before it can supersede the baseline.
"""
from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = "FINSIGHT-REFRESH-POLICY-1"
NUMERIC_RECIPE_COUNT = 419


ENGINE_FIELDS: dict[str, dict[str, str]] = {
    "enterprise_cash_fcff": {
        "cash_fcff": "source-derived operating cash-FCFF anchor; rebuild from cutoff filing/history",
        "initial_growth": "governed current-state growth; recompute from approved history policy",
        "terminal_growth": "governed terminal policy; validate against current policy version",
        "wacc": "governed discount policy; refresh rates and issuer risk inputs",
        "cash_and_investments": "cutoff balance-sheet cash/securities bridge; reselect source facts",
        "interest_bearing_debt": "cutoff debt/finance-lease bridge; reselect source facts",
        "preferred_equity": "preferred/other equity claim bridge; reselect or prove absent",
        "noncontrolling_interests": "NCI bridge; reselect or preserve explicit unresolved reserve",
        "diluted_shares": "cutoff-safe diluted share denominator; reselect cover/award facts",
        "forecast_years": "approved model horizon; locked model policy unless explicitly revised",
        "nonoperating_adjustment": "named non-operating bridge adjustment; revalidate event/claim source",
    },
    "constant_growth_fcff": {
        "revenue": "controlling filing TTM/FY revenue anchor; rebuild period-aware history",
        "fcff_margin": "history-derived cash-FCFF margin; recompute from OCF, capex, interest and tax",
        "growth": "history-bounded governed growth state; recompute from source history",
        "wacc": "governed discount policy; refresh rates and issuer risk inputs",
        "terminal_growth": "governed terminal policy; validate against current policy version",
        "cash_and_investments": "cutoff balance-sheet cash/securities bridge; reselect source facts",
        "debt": "cutoff debt/finance-lease bridge; reselect source facts",
        "noncontrolling_interests": "NCI/other-claim bridge; reselect or preserve explicit reserve",
        "shares": "cutoff-safe diluted share denominator; reselect cover/award facts",
    },
    "residual_income": {
        "book_value_per_share": "reported common-equity anchor divided by cutoff-safe shares",
        "current_roe": "reported/history-bounded current ROE; recompute from current equity and earnings",
        "cost_of_equity": "governed equity discount policy; refresh rates and risk inputs",
        "current_payout_ratio": "reported dividend/earnings payout; reselect current source facts",
        "terminal_roe": "governed terminal ROE policy bounded by history",
        "terminal_growth": "governed terminal policy; validate against current policy version",
        "years": "approved model horizon; locked model policy unless explicitly revised",
    },
    "cash_schedule": {
        "cash_flows": "explicit source-derived forecast schedule; rebuild from filing/history/event inputs",
        "terminal_cash_flow": "terminal cash-flow state; recompute from refreshed schedule and policy",
        "discount_rate": "governed discount policy; refresh rates and issuer risk inputs",
        "terminal_growth": "governed terminal policy; validate against current policy version",
        "shares": "cutoff-safe diluted share denominator; reselect cover/award facts",
        "net_bridge": "named bridge adjustment; reselect current cash/debt/claim/event sources",
    },
    "earnings_multiple": {
        "earnings": "source-derived normalized earnings or owner cash; rebuild history/current period",
        "multiple": "governed issuer/model multiple; requires current policy and specialist review",
        "shares": "cutoff-safe diluted share denominator; reselect cover/award facts",
        "net_bridge": "named bridge adjustment; reselect current cash/debt/claim/event sources",
    },
    "asset_runway": {
        "liquid_assets": "cutoff liquid-assets balance; reselect balance-sheet facts",
        "cash_burn_reserve": "source/history-bounded burn reserve; recompute current burn history",
        "debt_and_finance_leases": "cutoff debt/lease bridge; reselect source facts",
        "pipeline_terminal_value": "explicit approved pipeline/event value; revalidate source and specialist scope",
        "shares": "cutoff-safe diluted share denominator; reselect cover/award facts",
    },
    "cyclical_fcff_quantile": {
        "current_state": "current issuer operating state; rebuild from latest filing facts",
        "observed_states": "period-aligned issuer cycle history; rebuild from source facts",
        "operating_nwc_ratio": "period-aware operating NWC investment ratio; recompute from source facts",
        "normalized_tax_rate": "normalized tax policy; refresh filing reconciliation",
        "wacc": "governed discount policy; refresh rates and issuer risk inputs",
        "cash": "cutoff cash bridge; reselect source facts",
        "debt": "cutoff debt bridge; reselect source facts",
        "other_claims": "claim range; reselect or preserve explicit unresolved reserve",
        "diluted_shares": "cutoff-safe share state; reselect cover/award facts",
        "quantile": "approved cycle quantile selector; locked model policy",
    },
}


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _recipe_fields(recipe: Mapping[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for name, spec in recipe.get("scenarios", {}).items():
        if not isinstance(spec, Mapping):
            continue
        engine = str(spec.get("engine"))
        fields = sorted((spec.get("inputs") or {}).keys())
        result.setdefault(engine, [])
        result[engine] = sorted(set(result[engine]).union(fields))
    return result


def _unresolved_rules(engines: Mapping[str, list[str]], recipe: Mapping[str, Any]) -> list[str]:
    rules: list[str] = []
    if "cyclical_fcff_quantile" in engines:
        rules.append("rebuild period-aligned issuer cycle states and weighted quantiles before refresh")
    if "cash_schedule" in engines:
        rules.append("rebuild explicit schedule and terminal cash flow from refreshed filings; do not carry schedule values")
    if "asset_runway" in engines:
        rules.append("revalidate runway burn, liquid assets, debt and pipeline claims with specialist evidence")
    if any("equity_overlay" in spec for spec in recipe.get("scenarios", {}).values() if isinstance(spec, Mapping)):
        rules.append("revalidate event cash claim and incremental share overlay from a fresh filing/event package")
    if any(engine == "earnings_multiple" for engine in engines):
        rules.append("refresh issuer-specific multiple policy; a stored multiple is not a market-data refresh")
    return rules


def compile_refresh_policy(recipe: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one recipe into a non-ready refresh policy contract."""
    engines = _recipe_fields(recipe)
    fields: dict[str, dict[str, Any]] = {}
    for engine, names in engines.items():
        semantics = ENGINE_FIELDS.get(engine, {})
        for field in names:
            fields[field] = {
                "engine": engine,
                "baseline_value_locked": True,
                "refresh_semantics": semantics.get(field, "source-dependent field requires explicit selector and review"),
                "source_selector_required": True,
            }
    return {
        "schema_version": SCHEMA,
        "ticker": recipe.get("ticker"),
        "policy_status": "migration_evidence_only",
        "refresh_status": "requires_source_reselection",
        "baseline_binding": {
            "baseline_version": recipe.get("baseline_version"),
            "baseline_sha256": registry_entry.get("baseline_sha256"),
            "evidence_cutoff": recipe.get("evidence_cutoff"),
            "source_accession": recipe.get("source_accession") or (registry_entry.get("controlling_filing") or {}).get("accession"),
            "source_filed_date": (registry_entry.get("controlling_filing") or {}).get("filed_date"),
            "source_period_end": (registry_entry.get("controlling_filing") or {}).get("period_end"),
        },
        "model_engines": engines,
        "source_field_lineage": fields,
        "unresolved_economic_rules": _unresolved_rules(engines, recipe),
        "successor_filing_verification": {
            "required": True,
            "checks": [
                "ticker identity and CIK match registry",
                "filing accession differs from baseline and filed date is after evidence cutoff",
                "period/form are eligible under the batch source policy",
                "all source-dependent fields are reselected and replayed before promotion",
            ],
            "status": "metadata_check_only",
        },
        "recipe_provenance": recipe.get("provenance", {}),
    }


def verify_successor_filing(policy: Mapping[str, Any], successor: Mapping[str, Any]) -> dict[str, Any]:
    """Validate cached successor metadata; this does not ingest or promote it."""
    baseline = policy.get("baseline_binding", {})
    expected_ticker = policy.get("ticker")
    errors: list[str] = []
    if successor.get("ticker") != expected_ticker:
        errors.append("ticker_mismatch")
    if not successor.get("accession") or successor.get("accession") == baseline.get("source_accession"):
        errors.append("accession_not_successor")
    if not successor.get("filed_date") or successor.get("filed_date") <= (baseline.get("evidence_cutoff") or ""):
        errors.append("filed_date_not_after_cutoff")
    return {"status": "candidate_metadata_only" if not errors else "rejected_metadata", "verified": not errors, "errors": errors}


def compile_refresh_inventory(recipes_root: str | Path, registry_path: str | Path) -> dict[str, Any]:
    """Compile a complete numeric recipe policy inventory."""
    recipes_root = Path(recipes_root)
    registry = _json(Path(registry_path))
    by_ticker = {row["ticker"]: row for row in registry.get("entries", [])}
    policies: list[dict[str, Any]] = []
    missing_registry: list[str] = []
    for path in sorted(recipes_root.glob("*.json")):
        recipe = _json(path)
        ticker = recipe.get("ticker", path.stem)
        entry = by_ticker.get(ticker)
        if entry is None:
            missing_registry.append(str(ticker))
            continue
        policies.append(compile_refresh_policy(recipe, entry))
    engines = Counter(engine for policy in policies for engine in policy["model_engines"])
    return {
        "schema_version": SCHEMA,
        "baseline_catalog_version": registry.get("baseline_catalog_version"),
        "recipe_count": len(policies),
        "expected_numeric_count": NUMERIC_RECIPE_COUNT,
        "coverage_exact": len(policies) == NUMERIC_RECIPE_COUNT and not missing_registry,
        "engine_coverage": dict(sorted(engines.items())),
        "policy_status_counts": dict(Counter(policy["policy_status"] for policy in policies)),
        "missing_registry": missing_registry,
        "policies": policies,
    }


def write_refresh_inventory(recipes_root: str | Path, registry_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Compile and write policy evidence outside serving/catalog roots."""
    inventory = compile_refresh_inventory(recipes_root, registry_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile non-ready FinSight refresh policy evidence")
    parser.add_argument("--recipes", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    inventory = write_refresh_inventory(args.recipes, args.registry, args.output)
    print(json.dumps({key: inventory[key] for key in ("recipe_count", "expected_numeric_count", "coverage_exact", "engine_coverage")}, sort_keys=True))
    return 0 if inventory["coverage_exact"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
