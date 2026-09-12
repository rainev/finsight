"""One Batch 44 withheld recovery plus whole-batch non-stacked recalibration."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_44 import BATCH_44_TICKERS
from .batch_44_history import build_batch_44_history_result
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_44_RECOVERY_VERSION="BATCH-44-RECOVERY-RECALIBRATION-1.0"
ATTEMPTED=frozenset({"BKR","AMCR","SW"})
RECOVERED_PASS_TICKERS=frozenset()
RECOVERED_CONDITIONAL_TICKERS=frozenset(set(BATCH_44_TICKERS)-{"BKR"})
RECOVERED_WITHHELD_TICKERS=frozenset({"BKR"})


def _reliability(scenario:dict[str,float])->dict[str,Any]:
    return assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="Low",source_cap="High",reasons=("NORMALIZED_CYCLICAL_RANGE","SPECIALIST_MODEL_UNCERTAINTY")).as_dict()


def _scenario_rows(*,revenue:float,bridge:dict[str,Any],margins:tuple[float,float,float],growth:tuple[float,float,float],wacc:tuple[float,float,float],terminal:tuple[float,float,float],claims:tuple[float,float,float]|None=None)->tuple[list[dict[str,Any]],dict[str,Any]]:
    claims=claims or tuple(bridge["claims"]); base_shares=bridge["base_share_count"]; shares=(base_shares*1.0075,base_shares,base_shares*.9925); rows=[]; traces={}
    for i,name in enumerate(("bear","base","bull")):
        starting=revenue*margins[i]; state=EnterpriseCashFlowState(starting,growth[i],terminal[i],wacc[i],bridge["cash"],bridge["debt"],0.,claims[i],shares[i]); trace=enterprise_cash_flow_dcf(state,forecast_years=8,allow_nonpositive_equity_trace=True); raw=float(trace["intrinsic_value_per_share"]); rows.append({"name":name,"raw_value_per_share":raw,"conditional_value_per_share":max(0.,raw),"starting_cash_fcff":starting,"cash_conversion_margin":margins[i],"growth":growth[i],"wacc":wacc[i],"terminal_growth":terminal[i],"cash_and_investments":bridge["cash"],"debt_and_finance_leases":bridge["debt"],"other_equity_claims":claims[i],"shares":shares[i],"limited_liability_floor_applied":raw<0}); traces[name]=trace
    return rows,traces


def _non_stacked(initial:dict[str,Any])->dict[str,Any]:
    value=deepcopy(initial); old=initial["scenario_rows"]; base=old[1]
    margins=((old[0]["cash_conversion_margin"]+base["cash_conversion_margin"])/2,base["cash_conversion_margin"],(base["cash_conversion_margin"]+old[2]["cash_conversion_margin"])/2)
    growth=((old[0]["growth"]+base["growth"])/2,base["growth"],(base["growth"]+old[2]["growth"])/2)
    wacc=((old[0]["wacc"]+base["wacc"])/2,base["wacc"],(base["wacc"]+old[2]["wacc"])/2)
    terminal=((old[0]["terminal_growth"]+base["terminal_growth"])/2,base["terminal_growth"],(base["terminal_growth"]+old[2]["terminal_growth"])/2)
    bridge=initial["source_ledger"]["bridge_context"]; rows,traces=_scenario_rows(revenue=initial["reported_inputs"]["ttm_revenue"],bridge=bridge,margins=margins,growth=growth,wacc=wacc,terminal=terminal); scenario=dict(zip(("low","base","high"),(row["conditional_value_per_share"] for row in rows)))
    if abs(scenario["base"]-initial["scenario_range"]["base"])>1e-10 or not 0<=scenario["low"]<=scenario["base"]<=scenario["high"]: raise ValueError(f"{initial['ticker']}: recalibration invariant failed")
    warning=initial["warning"]+" The displayed band uses moderate history-to-base scenario midpoints rather than stacking every independent tail at once."
    value.update({"model_version":BATCH_44_RECOVERY_VERSION,"scenario_rows":rows,"scenario_range":scenario,"warning":warning,"history_reliability":_reliability(scenario)})
    value["governed_assumptions"]={**initial["governed_assumptions"],"cash_conversion_margin":margins,"growth":growth,"wacc":wacc,"terminal_growth":terminal,"shares":tuple(row["shares"] for row in rows),"scenario_calibration":"moderated_multi_factor_midpoints_between_full_tails_and_unchanged_base","scenario_calibration_reason":"The range still moves cash margin, growth, WACC, terminal growth, dilution and recorded bear claims together, but uses midpoint stresses rather than stacking every full historical/policy tail; base economics and reported bridge claims remain unchanged.","share_sensitivity_basis":"latest cutoff-safe common shares are the base; governed +/-0.75% stress represents unresolved dilution","reason_codes":["MODERATED_MULTI_FACTOR_SCENARIO_BAND","NORMALIZED_CYCLICAL_RANGE","SPECIALIST_MODEL_UNCERTAINTY"]}
    value["source_ledger"]={**initial["source_ledger"],"pre_recalibration_scenario_rows":old,"model_trace":{"states":traces},"raw_scenario_rows":rows,"recalibration":{"whole_batch_reviewed":True,"base_value_unchanged":True,"reported_bridge_unchanged":True,"market_price_used":False,"analyst_target_used":False,"competitor_value_used":False}}
    value["baseline"]={**value["baseline"],"method_version":BATCH_44_RECOVERY_VERSION,"low":scenario["low"],"base":scenario["base"],"high":scenario["high"],"warnings":[warning,value["governed_assumptions"]["invalidation"]]}
    return value


def _recover(initial:dict[str,Any])->dict[str,Any]:
    ticker=initial["ticker"]; value=deepcopy(initial); bridge=initial["source_ledger"]["bridge_context"]; revenue=initial["reported_inputs"]["ttm_revenue"]
    if ticker=="AMCR":
        current=initial["reported_inputs"]["ttm_cash_fcff"]/revenue; margins=(current*.85,current,current*1.15); growth=(-.01,.01,.025); wacc=(.105,.095,.0875); terminal=(.005,.01,.015); claims=tuple(bridge["claims"]); current_periods=1
        warning="Recovered Conditional Low post-Berry packaging baseline. It uses the first full combined FY2026 cash conversion with a transparent +/-15% margin band; older Amcor history is context only. Integration, restructuring, debt and one-year predictability remain material."
        basis="one full post-Berry annual cash period anchored to current consolidated revenue, OCF, capex, interest, debt and shares"
        release="Revalue when additional post-Berry annual periods establish a combined-company cycle or if integration, restructuring, debt, shares or cash conversion leave the range."
    elif ticker=="SW":
        annual=initial["source_ledger"]["annual_cash_sources"]; fy=annual[-1]["cash_fcff"]/annual[-1]["revenue"]["value"]; ttm=initial["reported_inputs"]["ttm_cash_fcff"]/revenue; margins=(min(fy,ttm)*.85,(fy+ttm)/2,max(fy,ttm)*1.15); growth=(-.015,.005,.02); wacc=(.11,.10,.09); terminal=(0.,.005,.0125); claims=(bridge["claims"][0]+10_000_000.,bridge["claims"][1]+5_000_000.,bridge["claims"][2]); current_periods=2
        warning="Recovered Conditional Low combined Smurfit Westrock packaging baseline. It uses FY2025 plus current TTM cash conversion, excludes predecessor years from calibration, and carries a governed preferred-claim stress. Exact preferred rights are not filed; closures, restructuring, leverage and short combined history remain material."
        basis="two current-company observations: full FY2025 and June-2026 TTM; predecessor and partial-combination years excluded from calibration"
        release="Revalue with additional combined-company annual history, exact preferred rights and quantified mill/converting-facility closure cash schedules."
    else: raise ValueError(ticker)
    rows,traces=_scenario_rows(revenue=revenue,bridge=bridge,margins=margins,growth=growth,wacc=wacc,terminal=terminal,claims=claims); scenario=dict(zip(("low","base","high"),(row["conditional_value_per_share"] for row in rows)))
    if not 0<=scenario["low"]<=scenario["base"]<=scenario["high"] or scenario["base"]<=0: raise ValueError(f"{ticker}: recovery range invalid")
    reliability=_reliability(scenario); baseline=BaselineValuation(ticker=ticker,method="resource_cycle_enterprise_fcff",method_version=BATCH_44_RECOVERY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence="Low",availability_type=AvailabilityType.CONDITIONAL,warnings=(warning,release))
    value.update({"model_version":BATCH_44_RECOVERY_VERSION,"availability_type":"conditional_estimate","scenario_rows":rows,"scenario_range":scenario,"warning":warning,"history_reliability":reliability,"baseline":baseline.as_private_dict()})
    value["governed_assumptions"]={**initial["governed_assumptions"],"history_years_used":current_periods,"normalization_basis":basis,"cash_conversion_margin":margins,"growth":growth,"wacc":wacc,"terminal_growth":terminal,"shares":tuple(row["shares"] for row in rows),"scenario_calibration":"current_company_observations_with_non_stacked_moderate_band","share_sensitivity_basis":"latest cutoff-safe common shares are the base; governed +/-0.75% stress represents unresolved dilution","equity_floor_basis":"bear-only limited-liability floor; raw negative residual retained privately" if ticker=="SW" else "not applied","reason_codes":["CURRENT_COMPANY_SHORT_HISTORY","CONSOLIDATED_MODEL_FALLBACK","SPECIALIST_MODEL_UNCERTAINTY"],"invalidation":release}
    value["source_ledger"]={**initial["source_ledger"],"current_company_recovery_calibration":{"basis":basis,"cash_conversion_margin":margins,"preferred_claim_sensitivity":claims if ticker=="SW" else None,"reported_vs_estimated":"reported_current_company_cash_history_with_governed_low_reliability_band"},"model_trace":{"states":traces},"raw_scenario_rows":rows,"recovery_attempt":{"attempted":True,"initial_availability_type":"not_available","final_availability_type":"conditional_estimate","market_price_used":False,"analyst_target_used":False,"competitor_value_used":False}}
    return value


def _bkr(initial:dict[str,Any])->dict[str,Any]:
    value=deepcopy(initial); reason="Recovery attempted; BKR remains withheld. Chart holders receive $210 cash per share and $2B of term loans are known, but exact total cash consideration, assumed debt/claims, post-close cash/debt and combined operating cash flow are absent. Modeling only the known loans would materially understate the completed transaction."
    release="Revalue with acquisition accounting, exact total cash and assumed-claim bridge, post-close balance sheet and issuer-filed Chart combined or pro-forma OCF/capex history."; baseline=BaselineValuation(ticker="BKR",method="resource_cycle_enterprise_fcff",method_version=BATCH_44_RECOVERY_VERSION,low=None,base=None,high=None,confidence=None,availability_type=AvailabilityType.NOT_AVAILABLE,warnings=(reason,release)); value.update({"model_version":BATCH_44_RECOVERY_VERSION,"warning":reason,"baseline":baseline.as_private_dict()}); value["governed_assumptions"]={**initial["governed_assumptions"],"reason_codes":["POST_ACQUISITION_CASH_STATE_UNAVAILABLE","ASSUMED_CLAIMS_UNBOUNDED","PRO_FORMA_CASH_FLOW_NOT_DISCLOSED","VALUATION_WITHHELD"],"invalidation":release}; value["source_ledger"]={**initial["source_ledger"],"recovery_attempt":{"attempted":True,"initial_availability_type":"not_available","final_availability_type":"not_available","known_chart_cash_per_share":210.,"known_term_loans":2_000_000_000.,"total_cash_consideration":None,"assumed_debt_and_claims":None,"post_close_cash_and_debt":None,"combined_operating_cash_flow":None,"market_price_used":False,"analyst_target_used":False,"competitor_value_used":False}}; return value


def build_batch_44_recovery_result(*,ticker:str,source_root:Path,structural_root:Path,event_root:Path,structural_cache_root:Path,special_annual_root:Path,xom_annual_root:Path)->dict[str,Any]:
    initial=build_batch_44_history_result(ticker=ticker,source_root=source_root,structural_root=structural_root,event_root=event_root,structural_cache_root=structural_cache_root,special_annual_root=special_annual_root,xom_annual_root=xom_annual_root)
    if ticker=="BKR": return _bkr(initial)
    if ticker in {"AMCR","SW"}: return _recover(initial)
    return _non_stacked(initial)


if RECOVERED_PASS_TICKERS|RECOVERED_CONDITIONAL_TICKERS|RECOVERED_WITHHELD_TICKERS!=set(BATCH_44_TICKERS): raise RuntimeError("Batch 44 recovery classification mismatch")
