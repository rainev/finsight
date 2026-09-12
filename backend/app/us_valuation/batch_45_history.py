"""History-backed utility equity baselines for controlled Universe Reset Batch 45."""
from __future__ import annotations
from datetime import date
import hashlib,json
from pathlib import Path
from statistics import median
from typing import Any

from app.valuation.bank import residual_income_valuation
from .baseline import AvailabilityType,BaselineValuation
from .batch_04_launch_first import _controlling
from .batch_35_history import _instant,_period_flow
from .batch_40_history import _latest_shares
from .batch_45 import BATCH_45_MANIFEST,BATCH_45_TICKERS,BATCH_45_VALUATION_DATE
from .batch_45_sources import verify_source_bundle
from .practical_models import EquityCashFlowState,mixed_utility_fcfe,practical_equity_cash_flow_range
from .reliability import assess_reliability

BATCH_45_HISTORY_VERSION="BATCH-45-UTILITY-EQUITY-1.0"
PERIOD="2026-06-30"
PASS_TICKERS=frozenset()
CONDITIONAL_TICKERS=frozenset(BATCH_45_TICKERS)
WITHHELD_TICKERS=frozenset()
RESIDUAL_TICKERS=frozenset({"AEP","ETR","XEL","LNT","D","PNW"})

SPEC={
"AEP":{"capex":(("PaymentsForConstructionInProcess",1),("PaymentsForNuclearFuel",1),("PaymentsToAcquireProductiveAssets",1)),"income":("NetIncomeLossAvailableToCommonStockholdersBasic",),"issued":(("ProceedsFromIssuanceOfLongTermDebt",1),),"repaid":(("RepaymentsOfLongTermDebt",1),),"short":(("ProceedsFromRepaymentsOfShortTermDebtMaturingInThreeMonthsOrLess",1),)},
"ETR":{"capex":(("PaymentsToAcquirePropertyPlantAndEquipment",1),("PaymentsForNuclearFuel",1),("PaymentsToAcquireOtherProductiveAssets",1)),"income":("NetIncomeLossAvailableToCommonStockholdersBasic",),"issued":(("ProceedsFromIssuanceOfLongTermDebt",1),),"repaid":(("RepaymentsOfLongTermDebt",1),),"short":(("ProceedsFromRepaymentsOfShortTermDebt",1),)},
"ES":{"capex":(("PaymentsToAcquirePropertyPlantAndEquipment",1),),"income":("NetIncomeLossAvailableToCommonStockholdersBasic",),"issued":(("ProceedsFromIssuanceOfLongTermDebt",1),),"repaid":(("RepaymentsOfLongTermDebt",1),),"short":(("ProceedsFromRepaymentsOfShortTermDebt",1),)},
"XEL":{"capex":(("PaymentsToAcquireProductiveAssets",1),),"income":("NetIncomeLoss",),"issued":(("ProceedsFromIssuanceOfLongTermDebt",1),),"repaid":(("RepaymentsOfLongTermDebt",1),),"short":(("ProceedsFromRepaymentsOfShortTermDebt",1),)},
"SO":{"capex":(("PaymentsToAcquirePropertyPlantAndEquipment",1),),"income":("NetIncomeLoss",),"issued":(("ProceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet",1),),"repaid":(("RepaymentsOfLongTermDebtAndCapitalSecurities",1),),"short":(("RepaymentsOfOtherShortTermDebt",-1),)},
"LNT":{"capex":(("PaymentsToAcquireOtherPropertyPlantAndEquipment",1),("PaymentsToAcquireOtherProductiveAssets",1)),"current_capex":(("PaymentsToAcquirePropertyPlantAndEquipment",1),("PaymentsToAcquireOtherProductiveAssets",1)),"income":("NetIncomeLossAvailableToCommonStockholdersBasic","NetIncomeLoss"),"issued":(("ProceedsFromIssuanceOfLongTermDebt",1),),"repaid":(("RepaymentsOfLongTermDebt",1),),"short":(("ProceedsFromRepaymentsOfShortTermDebt",1),),"current_short":(("ProceedsFromRepaymentsOfCommercialPaper",1),),"special_annual":True},
"D":{"capex":(("PaymentsForProceedsFromProductiveAssets",1),),"income":("NetIncomeLossAvailableToCommonStockholdersBasic",),"issued":(("ProceedsFromIssuanceOfLongTermDebt",1),),"repaid":(("RepaymentsOfLongTermDebt",1),),"short":()},
"PNW":{"capex":(("PaymentsToAcquireProductiveAssets",1),),"income":("NetIncomeLossAvailableToCommonStockholdersBasic",),"issued":(("ProceedsFromIssuanceOfOtherLongTermDebt",1),("ProceedsFromIssuanceOfSecuredDebt",1)),"repaid":(("RepaymentsOfOtherLongTermDebt",1),),"short":()},
"WEC":{"capex":(("PaymentsToAcquireOtherPropertyPlantAndEquipment",1),),"current_capex":(("PaymentsToAcquirePropertyPlantAndEquipment",1),),"income":("NetIncomeLossAvailableToCommonStockholdersBasic",),"issued":(("ProceedsFromIssuanceOfLongTermDebt",1),),"repaid":(("RepaymentsOfLongTermDebt",1),),"short":(("ProceedsFromRepaymentsOfShortTermDebtMaturingInThreeMonthsOrLess",1),),"special_annual":True},
"PEG":{"capex":(("PaymentsToAcquirePropertyPlantAndEquipment",1),),"income":("NetIncomeLoss",),"issued":(("ProceedsFromIssuanceOfOtherLongTermDebt",1),),"repaid":(("RepaymentsOfLongTermDebt",1),),"short":(("ProceedsFromRepaymentsOfCommercialPaper",1),)}}

WARNINGS={
"AEP":"Conditional Low regulated-utility residual-income baseline. Common book equity and earnings represent the current construction/acquisition cycle; DOE financing, transmission minority interests, capex and rate recovery remain material.",
"ETR":"Conditional Low regulated-utility residual-income baseline. Common book equity and earnings represent the current nuclear/project investment cycle; excess historical financing is not treated as recurring owner cash, while August junior subordinated issuance, temporary equity, subsidiary preferred/NCI and equity forwards remain material.",
"ES":"Conditional Low utility FCFE baseline. Aquarion disposal scope, offshore-wind liability, rate recovery, debt funding and redeemable preferred/NCI remain material.",
"XEL":"Conditional Low regulated-utility residual-income baseline. Common book equity and earnings represent the current construction phase; rate recovery, capex, financing, regulatory outcomes and common equity remain material.",
"SO":"Conditional Low utility FCFE baseline anchored to the June 30 balance-sheet boundary. August convertible financing is a revaluation trigger; multi-registrant parent allocation, project capex, NCI, debt retirement and dilution remain material.",
"LNT":"Conditional Low regulated-utility residual-income baseline. Common book equity and earnings represent the current construction phase; data-center load, capex, debt funding, rate recovery and approvals remain material.",
"D":"Pre-merger baseline only. Conditional Low utility residual-income value uses current Dominion common equity and earnings; the pending NextEra transaction, preferred/NCI, capex, nuclear obligations and approvals remain material and no post-merger value is implied.",
"PNW":"Conditional Low regulated-utility residual-income baseline. Reported 2025/TTM financing exceeds measured reinvestment and makes the FCFE funding range degenerate; common book equity and earnings represent capex recovery, while Palo Verde, wildfire/weather, leases and NCI remain material.",
"WEC":"Conditional Low utility FCFE baseline. Capex, parent/common allocation, preferred/NCI, financing, rate recovery and project execution remain material.",
"PEG":"Conditional Low mixed regulated/merchant utility FCFE baseline. The funding-only range is narrower than full economic uncertainty; PSE&G versus merchant nuclear cash, capex, financing, NDT/hedging and parent equity remain material."}

EVENT_TREATMENTS={
"AEP":"DOE financing and the five-year capital plan remain funding/rate context; future opportunity value is excluded and the transmission minority transaction remains in parent allocation.",
"ETR":"The pre-cutoff $1.5B junior subordinated issuance is hybrid funding context. It is not added as an EV claim; temporary equity and subsidiary preferred/NCI stay in the parent allocation.",
"ES":"Aquarion closed at quarter-end and is inside reported cash/equity. The sale and offshore-wind charge remain comparability warnings; no proceeds are added twice.",
"XEL":"Earnings/governance filings add no separate transaction value. Parent facts are used instead of subsidiary registrant facts.",
"SO":"August convertible issuance, debt repurchase and intended short-term repayment are treated as a net funding/dilution warning, never as three independent value additions or deductions.",
"LNT":"The earnings release supplies rate-base/load context only; unexecuted capital projects and approvals are not added as value.",
"D":"The NextEra merger is pending. This is a current pre-merger common-equity baseline; merger consideration, synergies and post-close financing are excluded.",
"PNW":"Captured earnings and securities filings are current funding/rate context; Palo Verde, wildfire and future construction remain scenario risks, not bridge assets.",
"WEC":"Earnings and controller filings add no transaction value. Project and rate-base forecasts remain scenario context.",
"PEG":"The current consolidated model includes regulated and merchant operations. Non-GAAP operating earnings, NDT marks and hedging forecasts are diagnostics, not substituted for GAAP owner cash."}

def _rows(facts:dict[str,Any],concept:str)->list[dict[str,Any]]:return [r for r in facts.get("facts",{}).get("us-gaap",{}).get(concept,{}).get("units",{}).get("USD",[]) if isinstance(r.get("val"),(int,float)) and not isinstance(r.get("val"),bool)]
def _source(row:dict[str,Any],concept:str)->dict[str,Any]:return {"source_kind":"companyfacts","concept":f"us-gaap:{concept}","value":float(row["val"]),"unit":"USD","period_start":row.get("start"),"period_end":row.get("end"),"filed":row.get("filed"),"accession":row.get("accn"),"form":row.get("form"),"reported_vs_estimated":"reported"}
def _annual_one(facts:dict[str,Any],concepts:tuple[str,...],year:int)->dict[str,Any]:
    for concept in concepts:
        candidates=[r for r in _rows(facts,concept) if r.get("form") in {"10-K","10-K/A"} and r.get("start")==f"{year}-01-01" and r.get("end")==f"{year}-12-31" and r.get("filed","")<=BATCH_45_VALUATION_DATE]
        if candidates:return _source(max(candidates,key=lambda r:(r.get("filed",""),r.get("accn",""))),concept)
    raise ValueError(f"annual {concepts}/{year} absent")
def _sum_sources(sources:list[dict[str,Any]],label:str)->dict[str,Any]:return {"source_kind":"reported_component_sum","concept":label,"value":sum(r["value"] for r in sources),"unit":"USD","period_start":sources[0].get("period_start"),"period_end":sources[0].get("period_end"),"components":sources,"reported_vs_estimated":"reported_components"}
def _annual_components(facts:dict[str,Any],items:tuple[tuple[str,int],...],year:int)->dict[str,Any]|None:
    if not items:return None
    sources=[]
    for concept,sign in items:
        row=_annual_one(facts,(concept,),year);sources.append({**row,"value":row["value"]*sign,"sign":sign})
    return _sum_sources(sources,"+".join(f"{sign:+d}*{concept}" for concept,sign in items))
def _period_components(structural:dict[str,Any],items:tuple[tuple[str,int],...],end:str)->dict[str,Any]|None:
    if not items:return None
    sources=[]
    for concept,sign in items:
        row=_period_flow(structural,(concept,),end,target_days=180);sources.append({**row,"value":row["value"]*sign,"sign":sign})
    return _sum_sources(sources,"+".join(f"{sign:+d}*{concept}" for concept,sign in items))
def _special_capex(root:Path,ticker:str,year:int)->dict[str,Any]:
    packet=root/ticker;receipt=json.loads((packet/"source-receipt.json").read_text());sp=packet/"structural-filing.json";pp=packet/"package-manifest.json"
    if hashlib.sha256(sp.read_bytes()).hexdigest()!=receipt["structural_filing_sha256"] or hashlib.sha256(pp.read_bytes()).hexdigest()!=receipt["package_manifest_sha256"]:raise ValueError(f"{ticker}: special annual hash mismatch")
    structural=json.loads(sp.read_text());sources=[]
    for concept,sign in SPEC[ticker]["capex"]:
        rows=[r for r in structural["facts"] if r.get("local_name")==concept and r.get("period_start")==f"{year}-01-01" and r.get("period_end")==f"{year}-12-31" and not r.get("dimensions") and isinstance(r.get("value"),(int,float))]
        values={float(r["value"]) for r in rows}
        if len(values)!=1:raise ValueError(f"{ticker}: {concept}/{year} unresolved")
        r=rows[-1];sources.append({"source_kind":"structural_xbrl","accession":structural.get("source_accession"),"filed":structural.get("filed_date"),"form":structural.get("form"),"period_start":r["period_start"],"period_end":r["period_end"],"concept":r.get("qname"),"unit":r.get("unit"),"value":float(r["value"])*sign,"sign":sign,"reported_vs_estimated":"reported"})
    return {**_sum_sources(sources,"special annual capex components"),"annual_source_receipt":receipt}
def _history(ticker:str,facts:dict[str,Any],structural:dict[str,Any],special_root:Path)->tuple[list[dict[str,Any]],dict[str,Any]]:
    spec=SPEC[ticker];annual=[]
    for year in (2024,2025):
        cfo=_annual_one(facts,("NetCashProvidedByUsedInOperatingActivities",),year);capex=_special_capex(special_root,ticker,year) if spec.get("special_annual") else _annual_components(facts,spec["capex"],year);income=_annual_one(facts,spec["income"],year);issued=_annual_components(facts,spec["issued"],year);repaid=_annual_components(facts,spec["repaid"],year);short=_annual_components(facts,spec["short"],year)
        if ticker=="SO":
            nci_income=_annual_one(facts,("NetIncomeLossAttributableToNoncontrollingInterest",),year);income={"source_kind":"derived_parent_common_income","concept":"NetIncomeLoss-NetIncomeLossAttributableToNoncontrollingInterest","value":income["value"]-nci_income["value"],"unit":"USD","period_start":income["period_start"],"period_end":income["period_end"],"components":[income,nci_income],"reported_vs_estimated":"derived_reported_components"}
        reinvestment=capex["value"]+income["value"]-cfo["value"];net=issued["value"]-repaid["value"]+(short["value"] if short else 0.);raw=net/reinvestment
        annual.append({"period_end":f"{year}-12-31","operating_cash_flow":cfo,"capital_expenditures":capex,"common_net_income":income,"debt_issued":issued,"debt_repaid":repaid,"short_term_net":short,"reinvestment":reinvestment,"net_borrowing":net,"raw_debt_funding_share":raw,"short_term_funding_included":short is not None})
    current={}
    for field,annual_key,current_items in (("operating_cash_flow","operating_cash_flow",(("NetCashProvidedByUsedInOperatingActivities",1),)),("capital_expenditures","capital_expenditures",spec.get("current_capex",spec["capex"])),("common_net_income","common_net_income",tuple((c,1) for c in spec["income"])),("debt_issued","debt_issued",spec["issued"]),("debt_repaid","debt_repaid",spec["repaid"]),("short_term_net","short_term_net",spec.get("current_short",spec["short"]))):
        latest=annual[-1][annual_key];cur=_period_components(structural,current_items,PERIOD);prior=_period_components(structural,current_items,"2025-06-30")
        if cur is None or prior is None:current[field]=None;continue
        current[field]={"value":latest["value"]+cur["value"]-prior["value"],"method":"latest_fy_plus_current_h1_minus_prior_h1","period_end":PERIOD,"sources":[latest,cur,prior]}
    latest=annual[-1]["common_net_income"];cur=_period_flow(structural,spec["income"],PERIOD,target_days=180);prior=_period_flow(structural,spec["income"],"2025-06-30",target_days=180)
    if ticker=="SO":
        current_nci=_period_flow(structural,("NetIncomeLossAttributableToNoncontrollingInterest",),PERIOD,target_days=180);prior_nci=_period_flow(structural,("NetIncomeLossAttributableToNoncontrollingInterest",),"2025-06-30",target_days=180);annual_nci=_annual_one(facts,("NetIncomeLossAttributableToNoncontrollingInterest",),2025);nci_ttm=annual_nci["value"]+current_nci["value"]-prior_nci["value"];current_income=annual[-1]["common_net_income"]["components"][0]["value"]+cur["value"]-prior["value"]-nci_ttm;current["common_net_income"]={"value":current_income,"method":"consolidated_ttm_less_nci_attributable_ttm","period_end":PERIOD,"sources":[annual[-1]["common_net_income"]["components"][0],cur,prior,annual_nci,current_nci,prior_nci],"nci_ttm":nci_ttm}
    else:current["common_net_income"]={"value":latest["value"]+cur["value"]-prior["value"],"method":"latest_fy_plus_current_h1_minus_prior_h1","period_end":PERIOD,"sources":[latest,cur,prior]}
    reinvestment=current["capital_expenditures"]["value"]+current["common_net_income"]["value"]-current["operating_cash_flow"]["value"];net=current["debt_issued"]["value"]-current["debt_repaid"]["value"]+(current["short_term_net"]["value"] if current["short_term_net"] else 0.);current.update({"reinvestment":reinvestment,"net_borrowing":net,"raw_debt_funding_share":net/reinvestment,"short_term_funding_included":current["short_term_net"] is not None});return annual,current

def _equity(structural:dict[str,Any],ticker:str,period:str)->dict[str,Any]:
    def maybe(names):
        try:return _instant(structural,names,period)
        except ValueError:return None
    if ticker=="AEP":parent=maybe(("StockholdersEquity",));total=maybe(("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",));temp=maybe(("RedeemableNoncontrollingInterestEquityPerformanceSharesCarryingAmount",));preferred=None
    elif ticker=="ETR":parent=maybe(("StockholdersEquity",));total=maybe(("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",));temp=maybe(("TemporaryEquityCarryingAmountAttributableToParent",));preferred=None
    elif ticker=="ES":parent=maybe(("StockholdersEquity",));temp=maybe(("RedeemableNoncontrollingInterestEquityPreferredCarryingAmount",));total={**parent,"value":parent["value"]+(temp["value"] if temp else 0.),"source_kind":"derived_parent_plus_redeemable_equity"};preferred=None
    elif ticker in {"XEL","LNT"}:parent=maybe(("StockholdersEquity",));total=maybe(("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest","StockholdersEquity"));temp=preferred=None
    elif ticker=="SO":
        total=maybe(("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",));rows=[r for r in structural["facts"] if r.get("local_name")=="StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest" and r.get("period_start") is None and r.get("period_end")==period and r.get("value") is not None and any(pair[1].endswith("NoncontrollingInterestMember") for pair in r.get("dimensions",[]))];vals={float(r["value"]) for r in rows}
        if len(vals)!=1:raise ValueError("SO: NCI equity component unresolved")
        nci=vals.pop();parent={"source_kind":"derived_total_less_nci_component","accession":structural.get("source_accession"),"period_end":period,"value":total["value"]-nci,"unit":"USD","components":{"total_equity":total["value"],"nci":nci},"reported_vs_estimated":"derived_reported_components"};temp=preferred=None
    elif ticker=="D":total=maybe(("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",));nci=maybe(("MinorityInterest",));preferred=maybe(("PreferredStockValue",));parent={"source_kind":"derived_total_less_nci_and_preferred","accession":structural.get("source_accession"),"period_end":period,"value":total["value"]-nci["value"]-preferred["value"],"unit":"USD","components":{"total_equity":total["value"],"nci":nci["value"],"preferred":preferred["value"]},"reported_vs_estimated":"derived_reported_components"};temp=None
    elif ticker=="PNW":parent=maybe(("StockholdersEquity",));total=maybe(("StockholdersEquityIncludingPortionAttributToNoncontrollingInterest","StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"));temp=preferred=None
    elif ticker=="WEC":
        total=maybe(("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",));nci=maybe(("OtherMinorityInterests",));preferred=maybe(("PreferredStockValue",));parent={"source_kind":"derived_total_less_nci_and_preferred","accession":structural.get("source_accession"),"period_end":period,"value":total["value"]-nci["value"]-preferred["value"],"unit":"USD","components":{"total_equity":total["value"],"nci":nci["value"],"preferred":preferred["value"]},"reported_vs_estimated":"derived_reported_components"};temp=None
    elif ticker=="PEG":
        total=maybe(("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",));parent={**total,"source_kind":"source_bounded_parent_equity_after_component_check","claim_absence_check":{"searched_concepts":["MinorityInterest","NoncontrollingInterestInConsolidatedEntity","PreferredStockValue","TemporaryEquityCarryingAmount"],"reported_equity_components":["CommonStockMember","TreasuryStockCommonMember","RetainedEarningsMember","AccumulatedOtherComprehensiveIncomeMember"],"result":"No parent-level NCI, preferred or temporary-equity component is present; reported components reconcile to total parent equity.","reported_vs_estimated":"source_bounded_absence"}};temp=preferred=None
    else:raise ValueError(ticker)
    denominator=total["value"]+(temp["value"] if temp and ticker!="ES" else 0.);share=parent["value"]/denominator
    if not 0<share<=1:raise ValueError(f"{ticker}: parent equity share invalid")
    return {"parent_common_equity":parent,"total_equity":total,"temporary_or_redeemable_equity":temp,"preferred_equity":preferred,"parent_cash_flow_share":share}

def _events(ticker:str,root:Path,manifest_hash:str)->dict[str,Any]:
    path=root/ticker/"inventory.json";rows=json.loads(path.read_text());docs=[]
    if not rows or any(r.get("filed","")>BATCH_45_VALUATION_DATE for r in rows):raise ValueError(f"{ticker}: invalid event inventory")
    for r in rows:
        for doc in r.get("documents",[]):
            p=Path(doc["path"]);p=p if p.is_absolute() else root.parent.parent/p
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=doc["sha256"]:raise ValueError(f"{ticker}: event hash mismatch")
            docs.append(doc)
    return {"source_kind":"sec_event_screening","screened_filings":rows,"documents":docs,"inventory_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"source_manifest_sha256":manifest_hash,"treatment":EVENT_TREATMENTS[ticker],"reported_vs_estimated":"reported_and_screened"}

def _fcfe_result(ticker:str,filing,annual,current,equity,shares,event,verification,structural)->dict[str,Any]:
    raw=tuple(r["raw_debt_funding_share"] for r in (*annual,current));bounded=sorted(max(0.,min(1.,x)) for x in raw);funding=((bounded[0]+bounded[1])/2,bounded[1],(bounded[1]+bounded[2])/2);model_income=current["common_net_income"]["value"]/equity["parent_cash_flow_share"];cash=tuple(mixed_utility_fcfe(operating_cash_flow=current["operating_cash_flow"]["value"],capital_expenditures=current["capital_expenditures"]["value"],net_income=model_income,debt_funding_share=f,parent_cash_flow_share=equity["parent_cash_flow_share"]) for f in funding)
    if min(cash)<=0:raise ValueError(f"{ticker}: utility FCFE route not positive")
    states={name:EquityCashFlowState(cash[i],.02,.02,.085) for i,name in enumerate(("bear","base","bull"))};vr,traces=practical_equity_cash_flow_range(states=states,diluted_shares=shares["value"],forecast_years=10,maximum_terminal_share=.90);scenario=vr.as_dict()
    if abs(scenario["high"]-scenario["base"])<1e-12:raise ValueError(f"{ticker}: utility FCFE route degenerate")
    reasons=("CONSOLIDATED_MIXED_UTILITY_FALLBACK","CAPEX_CASH_CONVERSION_SENSITIVITY","SPECIALIST_MODEL_UNCERTAINTY");rel=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="Low",source_cap="High",reasons=reasons);warning=WARNINGS[ticker];invalidate="Revalue if regulated/merchant scope, capex, debt funding, parent/common allocation, hybrid claims, shares, rate recovery or cutoff events leave the recorded range.";baseline=BaselineValuation(ticker=ticker,method="regulated_utility_fcfe",method_version=BATCH_45_HISTORY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence="Low",availability_type=AvailabilityType.CONDITIONAL,warnings=(warning,invalidate))
    rows=[{"name":n,"value_per_share":scenario[k],"cash_flow":cash[i],"debt_funding_share":funding[i],"growth_rate":.02,"terminal_growth":.02,"cost_of_equity":.085,"shares":shares["value"]} for i,(n,k) in enumerate(zip(("bear","base","bull"),("low","base","high")))]
    assumptions={"history_policy_version":"US-COMPANY-HISTORY-1.0","history_years_used":3,"forecast_years":10,"normalization_basis":"reported_2024_2025_and_ttm_debt_funded_reinvestment_with_clipped_raw_outliers_and_moderated_funding_midpoints","assumption_source_mix":"reported_utility_cash_equity_and_financing_history_plus_governed_clipping","debt_funding_share":funding,"raw_debt_funding_share":raw,"growth_rate":.02,"terminal_growth":.02,"cost_of_equity":.085,"current_payout_ratio":1.,"shares":(shares["value"],)*3,"route_is_equity_level":True,"ev_debt_bridge_applied":False,"equity_floor_basis":"not applied","calculator_calibration":"Exact FCFE range is baseline-calibrated; public edits vary owner-cash growth, payout, cost of equity and terminal growth without changing locked source facts.","funding_clipping_policy":"Raw funding is retained privately; ratios outside 0%-100% are capped only for the published sustainable funding share. Excess financing is excluded from recurring FCFE, not treated as zero or value.","invalidation":invalidate}
    return {"ticker":ticker,"method":"regulated_utility_fcfe","model_version":BATCH_45_HISTORY_VERSION,"availability_type":"conditional_estimate","scenario_rows":rows,"scenario_range":scenario,"reported_inputs":{"ttm_operating_cash_flow":current["operating_cash_flow"]["value"],"ttm_capital_expenditures":current["capital_expenditures"]["value"],"ttm_common_net_income":current["common_net_income"]["value"],"model_income_before_parent_allocation":model_income,"parent_cash_flow_share":equity["parent_cash_flow_share"],"share_count":shares["value"]},"governed_assumptions":assumptions,"history_reliability":rel.as_dict(),"source_ledger":{"controlling_filing":filing,"annual_utility_cash_history":annual,"ttm_utility_cash_state":current,"equity_allocation":equity,"share_source":shares,"event_sources":event,"model_trace":{"states":traces},"funding_clipping":{"raw":raw,"bounded":tuple(max(0.,min(1.,x)) for x in raw),"excess_amounts":tuple(max(0.,x-1.)*r["reinvestment"] for x,r in zip(raw,(*annual,current))),"treatment":"Excess financing is nonrecurring/unallocated until source-decomposed; it is not added to FCFE or silently erased from evidence."},"runtime_source_verification":verification,"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":warning,"baseline":baseline.as_private_dict()}

def _residual_result(ticker:str,filing,annual,current,equity,prior_equity,shares,event,verification,structural,fcfe_error:str)->dict[str,Any]:
    begin=prior_equity["parent_common_equity"]["value"];end=equity["parent_common_equity"]["value"];income=current["common_net_income"]["value"];base_roe=income/((begin+end)/2);roes=(base_roe,base_roe,base_roe);payout=(.65,.65,.65);coe=(.095,.085,.075);terminal_base=min(.105,max(.085,base_roe));terminal_roe=(terminal_base,terminal_base,terminal_base);tg=(.02,.02,.02);rows=[];traces={}
    for i,(name,key) in enumerate(zip(("bear","base","bull"),("low","base","high"))):
        trace=residual_income_valuation(book_value_per_share=end/shares["value"],current_roe=roes[i],cost_of_equity=coe[i],current_payout_ratio=payout[i],terminal_roe=terminal_roe[i],terminal_growth=tg[i],years=5);rows.append({"name":name,"raw_value_per_share":trace["intrinsic_value"],"conditional_value_per_share":trace["intrinsic_value"],"book_value_per_share":end/shares["value"],"current_roe":roes[i],"current_payout_ratio":payout[i],"cost_of_equity":coe[i],"terminal_roe":terminal_roe[i],"terminal_growth":tg[i],"shares":shares["value"]});traces[name]=trace
    scenario=dict(zip(("low","base","high"),(r["conditional_value_per_share"] for r in rows)))
    if not 0<scenario["low"]<=scenario["base"]<=scenario["high"]:raise ValueError(f"{ticker}: residual range invalid")
    reasons=("CONSOLIDATED_MIXED_UTILITY_FALLBACK","SPECIALIST_MODEL_UNCERTAINTY");rel=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="Low",source_cap="High",reasons=reasons);warning=WARNINGS[ticker];invalidate="Revalue if common equity, normalized earnings/ROE, payout, regulatory recovery, preferred/NCI, shares or pending events leave the recorded range.";baseline=BaselineValuation(ticker=ticker,method="regulated_utility_residual_income",method_version=BATCH_45_HISTORY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence="Low",availability_type=AvailabilityType.CONDITIONAL,warnings=(warning,invalidate));assumptions={"history_policy_version":"US-COMPANY-HISTORY-1.0","history_years_used":3,"forecast_years":5,"normalization_basis":"regulated_utility_common_equity_and_ttm_earnings_fallback_after_executed_fcfe_gate","assumption_source_mix":"reported_common_equity_and_earnings_plus_governed_cost_of_equity_range","current_roe":roes,"current_payout_ratio":payout,"cost_of_equity":coe,"terminal_roe":terminal_roe,"terminal_growth":tg,"shares":(shares["value"],)*3,"scenario_calibration":"cost_of_equity_only; sustainable ROE, payout, terminal ROE, terminal growth and shares held at base","route_is_equity_level":True,"ev_debt_bridge_applied":False,"equity_floor_basis":"not applied","calculator_calibration":"Exact residual-income base assumptions replay through the public calculator.","invalidation":invalidate}
    raw=tuple(r["raw_debt_funding_share"] for r in (*annual,current));bounded=sorted(max(0.,min(1.,x)) for x in raw);funding=((bounded[0]+bounded[1])/2,bounded[1],(bounded[1]+bounded[2])/2);model_income=current["common_net_income"]["value"]/equity["parent_cash_flow_share"];fcfe_cash=tuple(mixed_utility_fcfe(operating_cash_flow=current["operating_cash_flow"]["value"],capital_expenditures=current["capital_expenditures"]["value"],net_income=model_income,debt_funding_share=f,parent_cash_flow_share=equity["parent_cash_flow_share"]) for f in funding)
    return {"ticker":ticker,"method":"regulated_utility_residual_income","model_version":BATCH_45_HISTORY_VERSION,"availability_type":"conditional_estimate","scenario_rows":rows,"scenario_range":scenario,"reported_inputs":{"ttm_common_earnings":income,"beginning_common_equity":begin,"ending_common_equity":end,"share_count":shares["value"]},"governed_assumptions":assumptions,"history_reliability":rel.as_dict(),"source_ledger":{"controlling_filing":filing,"annual_utility_cash_history":annual,"ttm_utility_cash_state":current,"equity_allocation":{"current":equity,"prior":prior_equity},"share_source":shares,"event_sources":event,"residual_income_trace":{"states":traces},"fcfe_route_rejected":{"raw_debt_funding_share":raw,"moderated_debt_funding_share":funding,"candidate_parent_fcfe":fcfe_cash,"observed_error":fcfe_error,"reason":"The source-derived FCFE route was executed first and failed its positive, non-degenerate range gate; regulated common-equity residual income is used without an EV debt bridge."},"runtime_source_verification":verification,"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":warning,"baseline":baseline.as_private_dict()}

def build_batch_45_history_result(*,ticker:str,source_root:Path,structural_root:Path,event_root:Path,structural_cache_root:Path,special_annual_root:Path)->dict[str,Any]:
    if ticker not in BATCH_45_TICKERS:raise ValueError(ticker)
    packet=Path(source_root)/ticker;sp=Path(structural_root)/ticker;sub=json.loads((packet/"submissions.json").read_text());facts=json.loads((packet/"companyfacts.json").read_text());manifest=json.loads((packet/"source-manifest.json").read_text());structural=json.loads((sp/"structural-filing.json").read_text());filing=_controlling(manifest,sub)
    if structural.get("source_accession")!=filing["accession"] or structural.get("report_date")!=PERIOD:raise ValueError(f"{ticker}: controlling mismatch")
    verification=verify_source_bundle(ticker=ticker,packet=packet,structural_packet=sp,structural_cache_root=Path(structural_cache_root),filing=filing);annual,current=_history(ticker,facts,structural,Path(special_annual_root));equity=_equity(structural,ticker,PERIOD);prior_equity=_equity(structural,ticker,"2025-12-31");shares=_latest_shares(ticker,structural);event=_events(ticker,Path(event_root),verification["source_manifest_sha256"])
    try:return _fcfe_result(ticker,filing,annual,current,equity,shares,event,verification,structural)
    except ValueError as error:
        if "utility FCFE route" not in str(error) or ticker not in RESIDUAL_TICKERS:raise
        return _residual_result(ticker,filing,annual,current,equity,prior_equity,shares,event,verification,structural,str(error))

if PASS_TICKERS|CONDITIONAL_TICKERS|WITHHELD_TICKERS!=set(BATCH_45_TICKERS):raise RuntimeError("Batch 45 classification mismatch")
