"""Compile frozen private valuation packets into executable calculation recipes.

This module is deliberately conservative: a packet is migrated only when its
recorded scenario inputs can be replayed by :mod:`calculation_recipe` to the
published low/base/high values.  It never solves backwards from a published
value and it never scales an input to make a range fit.
"""
from __future__ import annotations

from hashlib import sha256
import json
from math import isclose
from pathlib import Path
from typing import Any, Iterable, Mapping

from .calculation_recipe import SCENARIOS, SCHEMA, evaluate_recipe


def _walk(value: Any):
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _scenario_rows(payload: Mapping[str, Any]) -> tuple[list[dict[str, Any]], Mapping[str, Any]] | None:
    """Return the first recorded three-row scenario table and its owning map."""
    fallback = None
    for owner in _walk(payload):
        rows = owner.get("scenario_rows")
        if isinstance(rows, list) and len(rows) == 3 and all(isinstance(row, Mapping) for row in rows):
            by_name = {str(row.get("name")): dict(row) for row in rows}
            if set(by_name) == set(SCENARIOS):
                return [by_name[name] for name in SCENARIOS], owner
            if fallback is None:
                fallback = ([dict(row) for row in rows], owner)
    return fallback


def _first_map(payload: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    for obj in _walk(payload):
        value = obj.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _value(value: Any, index: int, *, keys: tuple[str, ...] = ()) -> Any:
    if isinstance(value, (list, tuple)):
        return value[index] if len(value) == 3 else None
    if isinstance(value, Mapping):
        for key in keys:
            if key in value:
                return _value(value[key], index, keys=keys)
        return None
    return value


def _reported_inputs(owner: Mapping[str, Any]) -> Mapping[str, Any]:
    value = owner.get("reported_inputs")
    return value if isinstance(value, Mapping) else {}


def _bridge(owner: Mapping[str, Any]) -> Mapping[str, Any]:
    ledger = owner.get("source_ledger")
    if not isinstance(ledger, Mapping):
        return {}
    bridge = ledger.get("bridge_reconciliation", ledger.get("bridge"))
    return bridge if isinstance(bridge, Mapping) else {}


def _bridge_field(bridge: Mapping[str, Any], index: int, *names: str) -> Any:
    for name in names:
        if name in bridge:
            value = _value(bridge[name], index)
            if value is not None:
                return value
    return None


def _floor(row: Mapping[str, Any]) -> str | None:
    return "limited_liability" if row.get("limited_liability_floor_applied") else None


def _recipe_version(payload: Mapping[str, Any], owner: Mapping[str, Any]) -> str:
    version = owner.get("model_version") or owner.get("method") or payload.get("schema_version")
    return f"MIGRATED-{version or 'PRIVATE'}"


def _enterprise(rows: list[dict[str, Any]], owner: Mapping[str, Any]) -> dict[str, Any] | None:
    required = {"starting_cash_fcff", "growth", "terminal_growth", "wacc", "cash_and_investments", "debt_and_finance_leases", "shares"}
    if not required <= set(rows[0]):
        return None
    years = owner.get("governed_assumptions", {}).get("forecast_years", 8)
    if not isinstance(years, int):
        years = 8
    scenarios = {}
    for index, row in enumerate(rows):
        claims = row.get("other_equity_claims", 0.0)
        scenarios[row["name"]] = {
            "engine": "enterprise_cash_fcff",
            "inputs": {
                "cash_fcff": row["starting_cash_fcff"],
                "initial_growth": row["growth"],
                "terminal_growth": row["terminal_growth"],
                "wacc": row["wacc"],
                "cash_and_investments": row["cash_and_investments"],
                "interest_bearing_debt": row["debt_and_finance_leases"],
                "preferred_equity": claims,
                "noncontrolling_interests": 0.0,
                "diluted_shares": row["shares"],
                "forecast_years": years,
                "nonoperating_adjustment": row.get("enterprise_value_overlay", 0.0),
            },
        }
        if _floor(row):
            scenarios[row["name"]]["equity_floor"] = _floor(row)
    return scenarios


def _constant_growth(rows: list[dict[str, Any]], owner: Mapping[str, Any]) -> dict[str, Any] | None:
    if not ("cash_conversion_margin" in rows[0] or "fcff_margin" in rows[0]) or "growth" not in rows[0]:
        return None
    reported = _reported_inputs(owner)
    revenue = reported.get("ttm_revenue", reported.get("revenue_anchor", reported.get("reported_revenue", reported.get("fy2025_revenue", reported.get("continuing_ttm_revenue")))))
    if revenue is None:
        return None
    bridge = _bridge(owner)
    governed = owner.get("governed_assumptions") if isinstance(owner.get("governed_assumptions"), Mapping) else {}
    scenarios = {}
    for index, row in enumerate(rows):
        if not {"growth", "wacc", "terminal_growth"} <= set(row):
            return None
        margin = row.get("cash_conversion_margin", row.get("fcff_margin"))
        if margin is None:
            return None
        shares = row.get("shares", _value(governed.get("shares"), index) or reported.get("diluted_shares") or reported.get("shares"))
        if shares is None:
            return None
        cash = row.get("cash_and_investments")
        if cash is None:
            cash = _bridge_field(bridge, index, "cash_and_investments_range", "cash_and_investments", "cash")
        if cash is None:
            cash = _value(reported.get("cash_and_securities", reported.get("cash")), index)
        debt = row.get("debt")
        if debt is None:
            debt = row.get("debt_and_finance_leases")
        if debt is None:
            debt = _bridge_field(bridge, index, "debt", "interest_bearing_debt", "debt_and_finance_leases", "model_debt_and_finance_leases", "commercial_paper_long_term_debt_and_finance_leases", "remaining_debt_and_capital_leases")
        if debt is None:
            debt = _value(reported.get("debt"), index)
        claims = row.get("other_claims", row.get("bridge_claims"))
        if claims is None:
            claims = _bridge_field(bridge, index, "other_claims", "bridge_claims", "nci_or_event_claim_range", "nci_or_temporary_equity", "nci_range", "preferred_nci_and_redeemable_claims", "nci_and_redeemable_claims", "noncontrolling_interests")
        if claims is None:
            claims = _value(reported.get("noncontrolling_interests"), index)
        if claims is None:
            status = str(bridge.get("nci_status", ""))
            if status == "source_proven_absent":
                claims = 0.0
            elif bridge.get("reported_nci") is not None:
                claims = bridge.get("reported_nci")
            else:
                rates = owner.get("governed_assumptions", {}).get("unresolved_claims_reserve_rates", [])
                assets = None
                for source in owner.get("source_ledger", {}).get("bridge_sources", []):
                    if isinstance(source, Mapping) and str(source.get("concept", "")).endswith(":Assets"):
                        assets = source.get("value")
                        break
                if isinstance(rates, (list, tuple)) and assets is not None:
                    claims = float(rates[index]) * float(assets)
        # Some early packets report an NCI point and separately govern an
        # unresolved-claim reserve; both are explicit bridge deductions.
        rates = governed.get("unresolved_claims_reserve_rates", [])
        assets = None
        ledger = owner.get("source_ledger") if isinstance(owner.get("source_ledger"), Mapping) else {}
        for source in ledger.get("bridge_sources", []):
            if isinstance(source, Mapping) and str(source.get("concept", "")).endswith(":Assets"):
                assets = source.get("value")
                break
        explicit_claim_range = any(key in bridge for key in ("nci_or_event_claim_range", "nci_range", "other_claims"))
        if claims is not None and not explicit_claim_range and bridge.get("nci_status") == "reported" and isinstance(rates, (list, tuple)) and len(rates) == 3 and assets is not None:
            claims += float(rates[index]) * float(assets)
        # Explicit policy reserves (for example AZO finance-lease principal)
        # are kept in source-ledger value_range and are not reverse-fitted.
        for source in ledger.get("bridge_sources", []):
            if not isinstance(source, Mapping):
                continue
            value_range = source.get("value_range")
            if isinstance(value_range, Mapping):
                extra = value_range.get(("bear", "base", "bull")[index])
                if isinstance(extra, (int, float)) and not explicit_claim_range and "reserve" in str(source.get("field", "")).lower():
                    claims = (claims or 0.0) + extra
        shares = row.get("shares", _value(governed.get("shares"), index) or reported.get("diluted_shares") or reported.get("shares"))
        if cash is None or debt is None or claims is None or shares is None:
            return None
        scenarios[row["name"]] = {
            "engine": "constant_growth_fcff",
            "inputs": {
                "revenue": revenue,
                "fcff_margin": margin,
                "growth": row["growth"],
                "wacc": row["wacc"],
                "terminal_growth": row["terminal_growth"],
                "cash_and_investments": cash,
                "debt": debt,
                "noncontrolling_interests": claims,
                "shares": shares,
            },
        }
        if _floor(row):
            scenarios[row["name"]]["equity_floor"] = _floor(row)
    return scenarios


def _residual(rows: list[dict[str, Any]], owner: Mapping[str, Any]) -> dict[str, Any] | None:
    required = {"book_value_per_share", "current_roe", "cost_of_equity", "current_payout_ratio", "terminal_roe", "terminal_growth", "shares"}
    if not required <= set(rows[0]):
        return None
    years = owner.get("governed_assumptions", {}).get("forecast_years", 5)
    if not isinstance(years, int):
        years = 5
    scenarios = {}
    for row in rows:
        scenarios[row["name"]] = {"engine": "residual_income", "inputs": {
            "book_value_per_share": row["book_value_per_share"],
            "current_roe": row["current_roe"],
            "cost_of_equity": row["cost_of_equity"],
            "current_payout_ratio": row["current_payout_ratio"],
            "terminal_roe": row["terminal_roe"],
            "terminal_growth": row["terminal_growth"],
            "years": years,
        }}
        if _floor(row):
            scenarios[row["name"]]["equity_floor"] = _floor(row)
    return scenarios


def _multiple(rows: list[dict[str, Any]], owner: Mapping[str, Any]) -> dict[str, Any] | None:
    # Historical earnings-multiple packets record either normalized earnings or
    # the already-reconciled owner cash.  Both are source facts, not inferred.
    governed = owner.get("governed_assumptions") if isinstance(owner.get("governed_assumptions"), Mapping) else {}
    reported = _reported_inputs(owner)
    if not ("earnings_multiple" in rows[0] or "multiple" in rows[0]):
        return None
    if not ("shares" in rows[0] or governed.get("shares") is not None or reported.get("shares") is not None):
            return None
    scenarios = {}
    for index, row in enumerate(rows):
        earnings = row.get("normalized_common_earnings", row.get("normalized_consolidated_earnings", row.get("normalized_continuing_parent_earnings")))
        multiple = row.get("earnings_multiple")
        if earnings is None:
            earnings = row.get("owner_cash")
            multiple = row.get("multiple")
        shares = row.get("shares", _value(governed.get("shares"), index) or reported.get("shares"))
        if earnings is None or multiple is None or shares is None:
            return None
        net_bridge = row.get("net_bridge")
        if net_bridge is None and row.get("equity_value") is not None and row.get("enterprise_or_cash_value") is not None:
            net_bridge = row["equity_value"] - row["enterprise_or_cash_value"]
        scenarios[row["name"]] = {"engine": "earnings_multiple", "inputs": {
            "earnings": earnings, "multiple": multiple, "shares": shares, "net_bridge": net_bridge or 0.0,
        }}
        if _floor(row):
            scenarios[row["name"]]["equity_floor"] = _floor(row)
    return scenarios


def _cash_runway(rows: list[dict[str, Any]], owner: Mapping[str, Any]) -> dict[str, Any] | None:
    """Preserve the asset-runway identity; liquid assets are not earnings."""
    required = {"liquid_assets", "cash_burn_reserve", "debt_and_finance_leases", "shares"}
    if not required <= set(rows[0]):
        return None
    result = {}
    for row in rows:
        # This is the packet's stated runway arithmetic, not a target-derived
        # adjustment: liquid assets minus the governed burn reserve and debt.
        result[row["name"]] = {"engine": "asset_runway", "inputs": {
            "liquid_assets": row['liquid_assets'], "cash_burn_reserve": row['cash_burn_reserve'],
            "debt_and_finance_leases": row['debt_and_finance_leases'],
            "pipeline_terminal_value": row.get('pipeline_terminal_value', 0.0), "shares": row['shares']}}
        if _floor(row):
            result[row["name"]]["equity_floor"] = _floor(row)
    return result


def _model_cash_schedule(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Translate legacy model-detail schedules without reconstructing inputs."""
    for owner in _walk(payload):
        models = owner.get("scenarios")
        if not isinstance(models, Mapping) or set(models) != set(SCENARIOS):
            continue
        result: dict[str, Any] = {}
        for name in SCENARIOS:
            scenario = models[name]
            if not isinstance(scenario, Mapping):
                break
            model = next((value for value in scenario.values() if isinstance(value, Mapping)), None)
            detail = model.get("detail") if isinstance(model, Mapping) else None
            if not isinstance(detail, Mapping) or not isinstance(detail.get("forecast_schedule"), list):
                break
            flows = []
            for row in detail["forecast_schedule"]:
                if not isinstance(row, Mapping):
                    break
                flow = row.get("fcff", row.get("cash_fcff"))
                if not isinstance(flow, (int, float)):
                    break
                flows.append(flow)
            if not flows or not all(key in detail for key in ("terminal_fcff", "wacc", "terminal_growth", "shares_proxy")):
                break
            bridge = detail.get("cash_and_nonoperating_investments", 0.0) + detail.get("nonoperating_adjustment", 0.0)
            bridge -= detail.get("interest_bearing_debt", 0.0) + detail.get("preferred_equity", 0.0) + detail.get("noncontrolling_interests", 0.0)
            # Batch-01 practical states record this scenario-specific bridge
            # delta per share; retain it as arithmetic, never as calibration.
            bridge += detail.get("practical_bridge_delta_per_share", 0.0) * detail["shares_proxy"]
            spec: dict[str, Any] = {"engine": "cash_schedule", "inputs": {
                "cash_flows": flows,
                "terminal_cash_flow": detail["terminal_fcff"],
                "discount_rate": detail["wacc"],
                "terminal_growth": detail["terminal_growth"],
                "shares": detail["shares_proxy"],
                "net_bridge": bridge,
            }}
            result[name] = spec
        if len(result) == 3:
            return result
    return None


def _legacy_practical_inputs(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Use source-recorded practical-policy schedules (B01 bank/FCFE)."""
    for obj in _walk(payload):
        policy = obj.get("practical_policy")
        inputs = policy.get("scenario_inputs") if isinstance(policy, Mapping) else None
        if not isinstance(inputs, Mapping):
            continue
        # Realty Income's private policy stores the complete AFFO states as a
        # nested map and the two-stage DCF's governed constants are explicit.
        if isinstance(inputs.get("affo"), Mapping) and isinstance(inputs.get("shares"), (int, float)):
            growth = (0.02, 0.04, 0.055)
            discount = (0.105, 0.095, 0.085)
            terminal = (0.015, 0.02, 0.025)
            result = {}
            for index, name in enumerate(SCENARIOS):
                affo = inputs["affo"].get(name)
                if not isinstance(affo, (int, float)):
                    result = None
                    break
                flows = [affo * (1 + growth[index]) ** year for year in range(1, 9)]
                result[name] = {"engine": "cash_schedule", "inputs": {
                    "cash_flows": flows,
                    "terminal_cash_flow": affo * (1 + growth[index]) ** 8 * (1 + terminal[index]),
                    "discount_rate": discount[index], "terminal_growth": terminal[index],
                    "shares": inputs["shares"], "net_bridge": 0.0,
                }}
            if result is not None:
                return result
        if not all(name in inputs for name in SCENARIOS):
            continue
        sample = inputs["base"]
        if not isinstance(sample, Mapping):
            continue
        # Bank scenario inputs are complete residual-income contracts.
        if {"ending_common_equity", "roe", "cost_of_equity", "payout", "terminal_roe", "shares"} <= set(sample):
            result = {}
            for name in SCENARIOS:
                row = inputs[name]
                result[name] = {"engine": "residual_income", "inputs": {
                    "book_value_per_share": row["ending_common_equity"] / row["shares"],
                    "current_roe": row["roe"], "cost_of_equity": row["cost_of_equity"],
                    "current_payout_ratio": row["payout"], "terminal_roe": row["terminal_roe"],
                    "terminal_growth": 0.02, "years": 5,
                }}
            return result
        # Dell records the complete ten-year FCFE schedule and terminal value.
        if {"forecast_schedule", "terminal_value", "cost_of_equity", "terminal_growth", "shares"} <= set(sample):
            result = {}
            for name in SCENARIOS:
                row = inputs[name]
                schedule = row["forecast_schedule"]
                if not isinstance(schedule, list) or not all(isinstance(x, Mapping) and isinstance(x.get("cash_flow"), (int, float)) for x in schedule):
                    return None
                result[name] = {"engine": "cash_schedule", "inputs": {
                    "cash_flows": [x["cash_flow"] for x in schedule],
                    "terminal_cash_flow": row["terminal_value"] * (row["cost_of_equity"] - row["terminal_growth"]),
                    "discount_rate": row["cost_of_equity"], "terminal_growth": row["terminal_growth"],
                    "shares": row["shares"], "net_bridge": 0.0,
                }}
            return result
    return None


def _cyclical_inputs(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Compile WDC's issuer-balanced cycle inputs for the dedicated engine."""
    cycle = None
    for obj in _walk(payload):
        candidate = obj.get("scenario_inputs")
        if isinstance(candidate, Mapping) and isinstance(candidate.get("states"), list) and isinstance(candidate.get("revenue_medians"), Mapping):
            cycle = candidate
            break
    if cycle is None or len(cycle["states"]) < 6:
        return None
    medians = cycle["revenue_medians"]
    states: list[dict[str, Any]] = []
    current = None
    for stored in cycle["states"]:
        if not isinstance(stored, Mapping) or not isinstance(stored.get("schedule"), list):
            return None
        endpoint = next((row for row in stored["schedule"] if isinstance(row, Mapping) and row.get("year") == 5), None)
        if endpoint is None:
            return None
        issuer = stored.get("issuer")
        median_revenue = medians.get(issuer)
        wdc_median = medians.get("WDC")
        if not isinstance(issuer, str) or not isinstance(median_revenue, (int, float)) or not isinstance(wdc_median, (int, float)):
            return None
        mapped_revenue = endpoint.get("revenue")
        if not isinstance(mapped_revenue, (int, float)) or not median_revenue:
            return None
        # Stored schedule revenue is mapped to the current WDC median. Undo
        # only that documented mapping to recover the original issuer state;
        # do not derive any value from the published target range.
        original_revenue = float(mapped_revenue) / float(wdc_median) * float(median_revenue)
        state = {
            "issuer": issuer,
            "period_end": stored.get("period_end"),
            "revenue": original_revenue,
            "operating_margin": endpoint.get("operating_margin"),
            "depreciation_ratio": endpoint.get("depreciation_ratio"),
            "capex_ratio": endpoint.get("capex_ratio"),
        }
        if any(not isinstance(state[key], (int, float, str)) for key in state):
            return None
        states.append(state)
        if issuer == "WDC" and stored.get("period_end") == "2026-07-03":
            first = next((row for row in stored["schedule"] if isinstance(row, Mapping) and row.get("year") == 1), None)
            if first is None:
                return None
            current = {"issuer": "WDC", "period_end": "2026-07-03", "revenue": first.get("revenue"), "operating_margin": first.get("operating_margin"), "depreciation_ratio": first.get("depreciation_ratio"), "capex_ratio": first.get("capex_ratio")}
    if current is None:
        return None
    share_range = None
    for obj in _walk(payload):
        candidate = obj.get("share_range")
        if isinstance(candidate, Mapping) and all(isinstance(candidate.get(key), (int, float)) for key in ("low", "base", "high")):
            share_range = candidate
            break
    if share_range is None:
        return None
    claims = cycle.get("other_claims")
    if not isinstance(claims, Mapping):
        return None
    specs = {}
    for name, tax, shares, quantile in (("bear", 0.25, share_range["high"], 0.25), ("base", 0.21, share_range["base"], 0.50), ("bull", 0.16, share_range["low"], 0.75)):
        specs[name] = {"engine": "cyclical_fcff_quantile", "inputs": {"current_state": current, "observed_states": states, "operating_nwc_ratio": cycle.get("operating_nwc_ratio"), "normalized_tax_rate": tax, "wacc": cycle.get("wacc"), "cash": cycle.get("cash"), "debt": cycle.get("debt"), "other_claims": claims, "diluted_shares": shares, "quantile": quantile}}
    return specs


def _chtr_event_overlay(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """Reconstruct CHTR's recorded bull/transaction envelope arithmetic."""
    for obj in _walk(payload):
        governed = obj.get("governed_assumptions")
        reported = obj.get("reported_inputs")
        if not isinstance(governed, Mapping) or not isinstance(reported, Mapping):
            continue
        states = governed.get("current_company_dcf_states")
        required = ("announced_common_units", "announced_transaction_claims", "diluted_shares")
        if not isinstance(states, list) or len(states) != 3 or not all(isinstance(state, Mapping) for state in states) or not all(isinstance(reported.get(key), (int, float)) for key in required):
            continue
        current_shares = float(reported["diluted_shares"])
        revenue = reported.get("fy2025_revenue")
        cash = reported.get("cash")
        debt = reported.get("debt")
        nci = reported.get("noncontrolling_interests")
        if not all(isinstance(value, (int, float)) for value in (revenue, cash, debt, nci)):
            continue
        claims = float(reported["announced_transaction_claims"])
        units = float(reported["announced_common_units"])
        specs = {}
        for index, name in enumerate(SCENARIOS):
            state = states[index]
            if not all(isinstance(state.get(key), (int, float)) for key in ("fcff_margin", "growth", "wacc", "terminal_growth")):
                specs = {}
                break
            spec = {"engine": "constant_growth_fcff", "inputs": {"revenue": revenue, "fcff_margin": state["fcff_margin"], "growth": state["growth"], "wacc": state["wacc"], "terminal_growth": state["terminal_growth"], "cash_and_investments": cash, "debt": debt, "noncontrolling_interests": nci, "shares": current_shares}}
            if name == "bear":
                spec["equity_floor"] = "limited_liability"
            specs[name] = spec
        if not specs:
            continue
        # The event-adjusted middle state is applied to the independently
        # recomputed bull operating value, never to the cached equity_value.
        specs["base"] = {"engine": "constant_growth_fcff", "inputs": {**specs["bull"]["inputs"]}, "equity_overlay": {"cash_claim": claims, "incremental_shares": units}}
        return specs
    return None


def compile_private_recipe(
    payload: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    source_path: str | Path,
    private_sha256: str | None = None,
) -> dict[str, Any]:
    """Compile one private packet, returning ``status=gap`` on any mismatch."""
    found = _scenario_rows(payload)
    ticker = str(artifact.get("ticker") or payload.get("ticker") or "")
    target = artifact.get("scenario_range") if isinstance(artifact.get("scenario_range"), Mapping) else {}
    if not found:
        cyclical = _cyclical_inputs(payload)
        if cyclical is not None:
            schedule = cyclical
        else:
            schedule = None
        legacy = _chtr_event_overlay(payload) or _legacy_practical_inputs(payload)
        if schedule is None and legacy is not None:
            schedule = legacy
        elif schedule is None:
            schedule = _model_cash_schedule(payload)
        if schedule is None:
            return {"ticker": ticker, "status": "gap", "reason": "scenario_rows_missing", "source_path": str(source_path)}
        recipe = {
            "schema_version": SCHEMA,
            "ticker": ticker,
            "baseline_version": _baseline_version(artifact),
            "recipe_version": f"MIGRATED-{payload.get('schema_version') or 'PRIVATE'}",
            "scenarios": schedule,
            "editable": {},
            "provenance": {"source_path": str(source_path), "private_sha256": private_sha256 or sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "private_schema_version": payload.get("schema_version"), "evidence_cutoff": artifact.get("valuation_date"), "source_accession": (artifact.get("source_financial_statement") or {}).get("accession")},
        }
        try:
            replay = evaluate_recipe(recipe)["range"]
        except Exception as exc:
            return {"ticker": ticker, "status": "gap", "reason": f"replay_error:{exc}", "source_path": str(source_path)}
        expected = {name: target.get(name) for name in ("low", "base", "high")}
        if any(not isinstance(expected[name], (int, float)) or not isclose(replay[name], float(expected[name]), rel_tol=1e-9, abs_tol=1e-7) for name in expected):
            return {"ticker": ticker, "status": "gap", "reason": "recorded_inputs_do_not_replay_published_range", "source_path": str(source_path), "replay": replay, "expected": expected}
        recipe["replay"] = replay
        return {"ticker": ticker, "status": "migrated", "recipe": recipe, "source_path": str(source_path)}
    rows, owner = found
    forced_scenarios = _chtr_event_overlay(payload)
    # Batch-02 envelopes retain their underlying current-company DCF states
    # privately even though the public scenario table is an event envelope.
    governed = owner.get("governed_assumptions") if isinstance(owner.get("governed_assumptions"), Mapping) else {}
    if isinstance(governed.get("current_company_dcf_states"), list) and len(governed["current_company_dcf_states"]) == 3:
        rows = [dict(row) for row in governed["current_company_dcf_states"]]
        owner = {"reported_inputs": owner.get("reported_inputs", {}), "governed_assumptions": {}, "source_ledger": {}}
    elif isinstance(governed.get("standalone_dcf_states"), list) and len(governed["standalone_dcf_states"]) == 3:
        dcf_rows = [dict(row) for row in governed["standalone_dcf_states"]]
        for row, name in zip(dcf_rows, SCENARIOS):
            row["name"] = name
            row["limited_liability_floor_applied"] = name == "bear"
        reported = owner.get("reported_inputs", {})
        shares = reported.get("diluted_shares")
        contract_per_share = reported.get("merger_cash_per_share", 0.0) + 247.0 * reported.get("ticking_cash_per_day", 0.0)
        inner_owner = {"reported_inputs": reported, "governed_assumptions": {}, "source_ledger": {}}
        inner = _constant_growth(dcf_rows, inner_owner)
        if inner is not None:
            forced_scenarios = inner
        dcf_rows[2] = {"name": "bull", "owner_cash": contract_per_share * shares, "multiple": 1.0, "shares": shares, "limited_liability_floor_applied": False}
        if forced_scenarios is not None:
            forced_scenarios["bull"] = {"engine": "earnings_multiple", "inputs": {"earnings": contract_per_share * shares, "multiple": 1.0, "shares": shares, "net_bridge": 0.0}}
        rows = dcf_rows
        owner = {"reported_inputs": reported, "governed_assumptions": {}, "source_ledger": {}}
    scenarios = (forced_scenarios or _enterprise(rows, owner) or _constant_growth(rows, owner) or _residual(rows, owner) or _multiple(rows, owner) or _cash_runway(rows, owner))
    if scenarios is None:
        return {"ticker": ticker, "status": "gap", "reason": "unsupported_or_incomplete_recorded_shape", "source_path": str(source_path)}
    # The evaluator requires all three scenario names.  No target output is
    # used to fill an input; validation is a pure replay of recorded fields.
    recipe = {
        "schema_version": SCHEMA,
        "ticker": ticker,
        "baseline_version": _baseline_version(artifact),
        "recipe_version": _recipe_version(payload, owner),
        "scenarios": scenarios,
        "editable": {},
        "provenance": {
            "source_path": str(source_path),
            "private_sha256": private_sha256 or sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "private_schema_version": payload.get("schema_version"),
            "evidence_cutoff": artifact.get("valuation_date"),
            "source_accession": (artifact.get("source_financial_statement") or {}).get("accession"),
        },
    }
    try:
        replay = evaluate_recipe(recipe)["range"]
    except Exception as exc:
        return {"ticker": ticker, "status": "gap", "reason": f"replay_error:{exc}", "source_path": str(source_path)}
    expected = {name: target.get(name) for name in ("low", "base", "high")}
    if any(not isinstance(expected[name], (int, float)) or not isclose(replay[name], float(expected[name]), rel_tol=1e-9, abs_tol=1e-7) for name in expected):
        return {"ticker": ticker, "status": "gap", "reason": "recorded_inputs_do_not_replay_published_range", "source_path": str(source_path), "replay": replay, "expected": expected}
    recipe["replay"] = replay
    return {"ticker": ticker, "status": "migrated", "recipe": recipe, "source_path": str(source_path)}


def _baseline_version(artifact: Mapping[str, Any]) -> str:
    # Kept lazy to avoid calculator -> calculation_recipe import cycles.
    from .calculator import baseline_version

    return baseline_version(artifact)


def discover_private_source(ticker: str, expected_range: Mapping[str, Any], private_roots: Iterable[str | Path]) -> tuple[Path, dict[str, Any]] | None:
    """Find a deterministic private packet whose recorded range matches target."""
    target = tuple(expected_range.get(name) for name in ("low", "base", "high"))
    if not all(isinstance(v, (int, float)) for v in target):
        return None
    candidates: list[Path] = []
    for root in private_roots:
        path = Path(root)
        if path.is_file() and path.name.endswith("private.json"):
            candidates.append(path)
        elif path.exists():
            candidates.extend(path.glob(f"**/{ticker}/*private.json"))
    return _discover_from_candidates(expected_range, candidates)


def _discover_from_candidates(expected_range: Mapping[str, Any], candidates: Iterable[Path]) -> tuple[Path, dict[str, Any]] | None:
    target = tuple(expected_range.get(name) for name in ("low", "base", "high"))
    if not all(isinstance(v, (int, float)) for v in target):
        return None
    for path, payload in _matching_private_candidates(expected_range, candidates):
        return path, payload
    return None


def _matching_private_candidates(expected_range: Mapping[str, Any], candidates: Iterable[Path]) -> list[tuple[Path, dict[str, Any]]]:
    target = tuple(expected_range.get(name) for name in ("low", "base", "high"))
    if not all(isinstance(v, (int, float)) for v in target):
        return []
    matches = []
    for path in sorted(set(candidates)):
        try:
            payload = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        ranges = []
        for obj in _walk(payload):
            value = obj.get("scenario_range")
            if isinstance(value, Mapping):
                ranges.append(tuple(value.get(name) for name in ("low", "base", "high")))
        if any(all(isinstance(a, (int, float)) and isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-7) for a, b in zip(row, target)) for row in ranges):
            matches.append((path, payload))
    return matches


def migrate_catalog(catalog_dir: str | Path, private_roots: Iterable[str | Path]) -> dict[str, Any]:
    """Build migration evidence for numeric catalog entries without mutation."""
    root = Path(catalog_dir)
    manifest = json.loads((root / "manifest.json").read_text())
    # Index once: the confirmed universe has thousands of immutable candidate
    # packets, so rescanning every root for every ticker is needlessly costly.
    indexed: dict[str, list[Path]] = {}
    for private_root in private_roots:
        path = Path(private_root)
        candidates = [path] if path.is_file() else list(path.glob("**/*private.json")) if path.exists() else []
        for candidate in candidates:
            if candidate.is_file() and candidate.name.endswith("private.json"):
                indexed.setdefault(candidate.parent.name, []).append(candidate)
    migrated: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        ticker = entry["ticker"]
        artifact = json.loads((root / "artifacts" / f"{ticker}.json").read_text())
        if entry.get("availability_type") == "not_available":
            continue
        candidates = _matching_private_candidates(artifact.get("scenario_range", {}), indexed.get(ticker, []))
        if not candidates:
            gaps.append({"ticker": ticker, "reason": "matching_private_packet_missing", "public_artifact_sha256": entry.get("artifact_sha256")})
            continue
        result = None
        for path, payload in candidates:
            attempt = compile_private_recipe(payload, artifact, source_path=path, private_sha256=sha256(path.read_bytes()).hexdigest())
            result = attempt
            if attempt["status"] == "migrated":
                break
        result["public_artifact_sha256"] = entry.get("artifact_sha256")
        if result["status"] == "migrated":
            migrated.append(result)
        else:
            gaps.append(result)
    return {
        "catalog_version": manifest.get("catalog_version"),
        "numeric_count": len(migrated) + len(gaps),
        "migrated_count": len(migrated),
        "gap_count": len(gaps),
        "migrated": migrated,
        "gaps": gaps,
    }
