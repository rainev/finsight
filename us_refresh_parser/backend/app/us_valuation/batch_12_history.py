"""History-backed practical baselines for controlled universe-reset Batch 12."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_conditional_estimates import five_year_fcff_dcf
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point, _source_proven_no_other_equity_claims
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _dimension_fact, _no_preferred
from .batch_12 import BATCH_12_TICKERS, BATCH_12_VALUATION_DATE
from .equity_fact_selection import annual_facts
from .history import HISTORY_POLICY_VERSION, HistoryObservation, CompanyHistoryProfile, build_cash_fcff_history_profile, summarize_history_metric
from .reliability import assess_reliability


BATCH_12_HISTORY_VERSION = "BATCH-12-HEALTH-CARE-HISTORY-1.0"
PASS_TICKERS = frozenset()
EQUITY_EARNINGS_TICKERS = frozenset({"HUM", "CVS"})


def _shares(base: float) -> tuple[float, float, float]:
    return (base * 1.025, base, base * .975)


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: float
    claims: float
    shares: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str


P = {
    "ABT": Policy("post_exact_sciences_medical_device_fcff", "2026-06-30", 5_603_000_000., 32_608_000_000., 915_000_000., _shares(1_745_014_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low post-Exact-Sciences estimate. The $20.6B acquisition, new debt, contingent consideration, and only partial acquired-business cash history remain material.", "Invalidate if Exact Sciences integration, acquisition debt/claims, diagnostic cash conversion, R&D, capex, or diluted shares changes."),
    "BAX": Policy("post_disposition_medical_products_fcff", "2026-06-30", 2_151_000_000., 9_459_000_000., 10_000_000., _shares(517_000_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low medical-products estimate. Discontinued-operation scope, separation costs, debt, contingent consideration, and uneven cash history remain material.", "Invalidate if continuing-business scope, separation cash, debt/leases, contingent consideration, or shares changes."),
    "BDX": Policy("post_spin_medical_technology_fcff", "2026-06-30", 708_000_000., 16_808_000_000., 0., _shares(281_603_000.), (.12, .105, .095), (0., .01, .02), "Conditional Low post-spin estimate. The $4B spin transaction, discontinued R&D, impairment, portfolio scope, and debt remain material.", "Invalidate if spin accounting, continuing cash, debt/leases, impairment, R&D, or shares changes."),
    "BMY": Policy("patent_pipeline_pharma_fcff", "2026-06-30", 11_464_000_000., 43_888_000_000., 607_000_000., _shares(2_048_000_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low pharmaceutical estimate. Patent loss, pipeline probability, pricing, acquired milestones, contingent value rights, litigation, R&D, and leverage remain material.", "Invalidate if patent/pipeline cash, pricing, contingent value rights, acquired obligations, debt, litigation, R&D, capex, or shares changes."),
    "RVTY": Policy("acquisition_restructuring_life_sciences_fcff", "2026-07-05", 1_022_943_000., 3_222_200_000., 8_000_000., _shares(111_746_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low life-sciences and diagnostics estimate. Advanced Chemistry Development acquisition cash, contingent consideration, and current restructuring remain material.", "Invalidate if acquisition integration, contingent consideration, restructuring, diagnostics/life-sciences cash, debt, capex, or shares changes."),
    "LLY": Policy("pipeline_manufacturing_pharma_fcff", "2026-06-30", 8_950_000_000., 54_908_000_000., 2_518_000_000., _shares(894_800_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low pharmaceutical estimate. Large current and subsequent acquisitions, contingent consideration, pipeline probability, patent/pricing risk, and exceptional manufacturing capex remain material.", "Invalidate if acquired pipeline probability, contingent consideration, manufacturing capex, patent/pricing cash, debt, or shares changes."),
    "WST": Policy("post_divestiture_health_care_supplies_fcff", "2026-06-30", 571_800_000., 207_300_000., 3_300_000., _shares(71_900_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low post-divestiture supplies estimate. The July SmartDose sale cash is included, while disposed-business cash history, quality/regulatory risk, capacity capex, and contingent consideration remain material.", "Invalidate if SmartDose adjustments, quality events, capacity capex, debt/leases, contingent consideration, or shares changes."),
    "UHS": Policy("pre_talkspace_hospital_fcff", "2026-06-30", 138_800_000., 4_851_847_000., 141_823_000., _shares(60_789_000.), (.115, .10, .09), (0., .01, .02), "Conditional Low standalone pre-Talkspace hospital estimate. The pending $835M debt-financed acquisition, reimbursement, labor, self-insurance, leases, and facility capex remain material.", "Invalidate on Talkspace closing/termination/financing, reimbursement or labor shifts, self-insurance claims, debt/leases, capex, or shares."),
}


SHARE_STARTS = {"ABT":"2026-01-01","BAX":"2026-01-01","BDX":"2025-10-01","BMY":"2026-01-01","RVTY":"2025-12-29","LLY":"2026-01-01","WST":"2026-01-01","UHS":"2026-01-01"}


POINT_SPECS = {
    "ABT": (("CashAndCashEquivalentsAtCarryingValue",5_104_000_000.),("ShortTermInvestments",499_000_000.),("LongTermInvestments",1_111_000_000.),("LongTermDebtCurrent",3_005_000_000.),("LongTermDebtNoncurrent",29_603_000_000.),("MinorityInterest",652_000_000.),("BusinessCombinationContingentConsiderationLiability",263_000_000.),("PreferredStockValue",0.)),
    "BAX": (("CashAndCashEquivalentsAtCarryingValue",2_150_000_000.),("AvailableForSaleSecuritiesDebtSecurities",1_000_000.),("RestrictedCash",6_000_000.),("LongTermDebtAndCapitalLeaseObligationsCurrent",844_000_000.),("LongTermDebtAndLeaseObligationExcludingCurrentMaturities",8_615_000_000.),("MinorityInterest",-27_000_000.),("BusinessCombinationContingentConsiderationLiability",10_000_000.)),
    "BDX": (("CashAndCashEquivalentsAtCarryingValue",708_000_000.),("RestrictedCashAndInvestmentsCurrent",155_000_000.),("DebtCurrent",3_297_000_000.),("LongTermDebtNoncurrent",13_511_000_000.),("SupplierFinanceProgramObligation",181_000_000.)),
    "BMY": (("CashAndCashEquivalentsAtCarryingValue",8_722_000_000.),("AvailableForSaleSecuritiesDebtSecuritiesCurrent",2_345_000_000.),("AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",397_000_000.),("ShortTermBorrowings",1_027_000_000.),("LongTermDebt",42_861_000_000.),("MinorityInterest",0.),("ContingentValueRightsNoncurrent",607_000_000.),("PreferredStockValue",0.)),
    "RVTY": (("CashAndCashEquivalentsAtCarryingValue",1_022_943_000.),("RestrictedCashCurrent",713_000.),("RestrictedCashNoncurrent",525_000.),("DebtLongtermAndShorttermCombinedAmount",3_222_200_000.),("RestructuringReserve",32_818_000.),("PreferredStockValue",0.)),
    "LLY": (("CashAndCashEquivalentsAtCarryingValue",8_950_000_000.),("LongTermInvestments",3_856_000_000.),("DebtCurrent",7_050_000_000.),("LongTermDebtNoncurrent",47_858_000_000.)),
    "WST": (("CashAndCashEquivalentsAtCarryingValue",435_800_000.),("LongTermDebt",202_900_000.),("FinanceLeaseLiability",4_400_000.),("BusinessCombinationContingentConsiderationLiability",3_300_000.),("PreferredStockValue",0.)),
    "UHS": (("CashAndCashEquivalentsAtCarryingValue",138_800_000.),("RestrictedCash",133_583_000.),("LongTermDebtCurrent",771_910_000.),("LongTermDebtNoncurrent",4_079_937_000.),("MinorityInterest",67_823_000.),("RedeemableNoncontrollingInterestEquityCarryingAmount",74_000_000.),("TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",73_603_000.)),
}


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows=[_point(structural,name=name,expected=value,period_end=policy.period) for name,value in POINT_SPECS[ticker]]
    rows.append(_duration(structural,name="WeightedAverageNumberOfDilutedSharesOutstanding",expected=policy.shares[1],period_start=SHARE_STARTS[ticker],period_end=policy.period))
    if ticker in {"BDX","WST"}: rows.append(_source_proven_no_other_equity_claims(structural,period_end=policy.period))
    elif ticker=="UHS":
        preferred=[row for row in structural["facts"] if row.get("local_name") in {"PreferredStockValue","PreferredStockValueOutstanding"} and row.get("period_start") is None and row.get("period_end")==policy.period and not row.get("dimensions") and isinstance(row.get("value"),(int,float)) and float(row["value"])!=0]
        if preferred: raise ValueError("UHS preferred claim unresolved")
        rows.append({"source_kind":"controlling_filing_structure","accession":structural["source_accession"],"period_end":policy.period,"field":"preferred_equity","reported_vs_estimated":"source_proven_absent_or_zero","redeemable_nci_temporary_equity_treatment":"$73.603M temporary equity is the same approximate $74M redeemable NCI claim and is not added twice."})
    else: rows.append(_no_preferred(structural,policy.period))
    if ticker=="ABT": rows.extend((_structural_flow(structural,name="PaymentsToAcquireBusinessesNetOfCashAcquiredAndResearchAndDevelopmentInProcess",start="2026-01-01",end=policy.period,expected=19_962_000_000.),_dimension_fact(structural,name="BusinessCombinationConsiderationTransferred1",expected=20_600_000_000.,start="2026-03-23",end="2026-03-23",member="ExactSciencesCorporationMember")))
    if ticker=="BDX": rows.extend((_dimension_fact(structural,name="DisposalGroupIncludingDiscontinuedOperationConsideration",expected=4_000_000_000.,start=None,end="2026-02-09",member="SpinOffEntityMember"),_structural_flow(structural,name="AssetImpairmentCharges",start="2025-10-01",end=policy.period,expected=450_000_000.)))
    if ticker=="RVTY": rows.extend((_dimension_fact(structural,name="BusinessCombinationContingentConsiderationLiability",expected=8_000_000.,start=None,end=policy.period,member="AdvancedChemistryDevelopmentInc.Member"),_dimension_fact(structural,name="BusinessAcquisitionCostOfAcquiredEntityCashPaidIncludingWorkingCapitalAndOtherAdjustments",expected=72_000_000.,start="2025-12-29",end="2026-04-05",member="AdvancedChemistryDevelopmentInc.Member"),_structural_flow(structural,name="NetRestructuringChargesIncurred",start="2025-12-29",end=policy.period,expected=41_311_000.)))
    if ticker=="LLY": rows.extend((_dimension_fact(structural,name="BusinessCombinationContingentConsiderationLiabilityCurrent",expected=814_000_000.,start=None,end=policy.period,member="FairValueInputsLevel3Member"),_dimension_fact(structural,name="BusinessCombinationContingentConsiderationLiabilityNoncurrent",expected=1_704_000_000.,start=None,end=policy.period,member="FairValueInputsLevel3Member"),_structural_flow(structural,name="OtherPaymentsToAcquireBusinesses",start="2026-01-01",end=policy.period,expected=9_805_000_000.),_structural_flow(structural,name="PaymentsToAcquireInProcessResearchAndDevelopment",start="2026-01-01",end=policy.period,expected=3_486_000_000.)))
    if ticker=="WST": rows.extend((_dimension_fact(structural,name="ProceedsFromDivestitureOfBusinesses",expected=136_000_000.,start="2026-07-01",end="2026-07-01",member="SmartDose3.5mLOnBodyDeliverySystemAndAssociatedFacilitiesMember"),_dimension_fact(structural,name="DisposalGroupIncludingDiscontinuedOperationConsideration",expected=112_500_000.,start=None,end="2025-12-31",member="SmartDose3.5mLOnBodyDeliverySystemAndAssociatedFacilitiesMember")))
    if ticker=="UHS": rows.extend(({"source_kind":"controlling_filing_text","accession":structural["source_accession"],"period_end":policy.period,"field":"pending_talkspace_consideration","reported_value_millions":835.,"scale":1_000_000.,"value":835_000_000.,"unit":"USD","reported_vs_estimated":"reported_scaled","valuation_treatment":"separate_pending_transaction_surface"},{"source_kind":"controlling_filing_text_subsequent_event","accession":structural["source_accession"],"event_period":"2026-07","field":"completed_ireland_facilities_acquisition","reported_value_millions":188.,"scale":1_000_000.,"value":188_000_000.,"unit":"USD","reported_vs_estimated":"reported_scaled","valuation_treatment":"post_period_state_change_requires_new_cash_and_debt_object"}))
    return rows


def _reconstruct_ttm(structural: dict[str,Any], normalizer: Any, specs: dict[str,tuple[str,float,float]], period: str) -> dict[str,dict[str,Any]]:
    out={}
    for field,(name,current,prior) in specs.items():
        annual=normalizer.annual_series(field,1)[0]
        cs=_structural_flow(structural,name=name,start="2026-01-01",end=period,expected=current)
        ps=_structural_flow(structural,name=name,start="2025-01-01",end="2025-06-30",expected=prior)
        out[field]={"field":field,"value":float(annual.value)+current-prior,"period_end":period,"method":"latest_fy_plus_current_h1_minus_prior_h1","sources":[annual.as_dict(),cs,ps]}
    return out


def _companyfact_custom_annual(facts: dict, concept: str, end: str, *, field: str = "capital_expenditures") -> dict:
    rows=facts["facts"]["us-gaap"][concept]["units"]["USD"]
    eligible=[row for row in rows if row.get("end")==end and row.get("form") in {"10-K","10-K/A"} and row.get("filed","")<=BATCH_12_VALUATION_DATE and isinstance(row.get("val"),(int,float)) and row.get("start")]
    if not eligible: raise ValueError(f"{concept}/{end}: annual source absent")
    row=max(eligible,key=lambda value:(value.get("filed",""),value.get("accn","")))
    return {"field":field,"concept":f"us-gaap:{concept}","accession":row.get("accn"),"filed":row.get("filed"),"form":row.get("form"),"start":row.get("start"),"end":row.get("end"),"period_end":row.get("end"),"unit":"USD","value":float(row["val"]),"fiscal_year":row.get("fy"),"reported_vs_estimated":"reported"}


def _lly_annual_states(normalizer: Any, facts: dict) -> tuple[dict,...]:
    states=[]
    for ocf in normalizer.annual_series("operating_cash_flow",5):
        try: capex=_companyfact_custom_annual(facts,"PaymentsToAcquireOtherPropertyPlantAndEquipment",ocf.end)
        except ValueError: continue
        revenue=normalizer.annual_at_end("revenue",ocf.end); interest=normalizer.annual_at_end("interest_expense",ocf.end); pretax=normalizer.annual_at_end("pretax_income",ocf.end); tax=normalizer.annual_at_end("income_tax",ocf.end)
        if not all((revenue,interest,pretax,tax)): continue
        rate=max(0.,min(.35,float(tax.value)/float(pretax.value))) if pretax.value>0 else .21
        cash=cash_fcff_from_reported(operating_cash_flow=float(ocf.value),capital_expenditures=capex["value"],spectrum_investment=0.,interest_expense=abs(float(interest.value)),tax_rate=rate)
        states.append({"period_end":ocf.end,"operating_cash_flow":ocf.as_dict(),"capital_expenditures":capex,"interest_expense":interest.as_dict(),"pretax_income":pretax.as_dict(),"income_tax":tax.as_dict(),"revenue":revenue.as_dict(),"cash_fcff":cash})
    return tuple(states)


def _equity_history(ticker: str, facts: dict, structural: dict, filing: dict, shares: tuple[float,float,float]) -> dict:
    gaap=facts.get("facts",{}).get("us-gaap",{})
    annual=annual_facts(gaap,concepts=("NetIncomeLossAvailableToCommonStockholdersBasic","NetIncomeLoss"),unit="USD",valuation_date=BATCH_12_VALUATION_DATE)
    observations=[]; annual_common={}; annual_sources={}
    for year,fact in sorted(annual.items())[-5:]:
        fact_source={"concept":fact.concept,"value":fact.value,"unit":fact.unit,"period_start":fact.period_start,"period_end":fact.period_end,"filed_date":fact.filed_date,"accession":fact.accession,"form":fact.form}; value=float(fact.value); sources=[fact_source]
        if fact.concept=="NetIncomeLoss":
            try:
                nci=_companyfact_custom_annual(facts,"NetIncomeLossAttributableToNoncontrollingInterest",fact.period_end,field="noncontrolling_interest_earnings"); value-=float(nci["value"]); sources.append(nci)
            except ValueError: pass
        annual_common[year]=value; annual_sources[year]=tuple(sources); observations.append(HistoryObservation(period_role="annual",period_end=fact.period_end,fiscal_year=fact.fiscal_year,value=value,unit="USD",formula="reported annual parent-attributable common-equity earnings",sources=tuple(sources)))
    latest_year=max(annual_common); latest_value=annual_common[latest_year]
    if ticker=="HUM":
        current_net=_structural_flow(structural,name="NetIncomeLoss",start="2026-01-01",end="2026-06-30",expected=1_880_000_000.); current_nci=_structural_flow(structural,name="NetIncomeLossAttributableToNoncontrollingInterest",start="2026-01-01",end="2026-06-30",expected=-3_000_000.); prior_net=_structural_flow(structural,name="NetIncomeLoss",start="2025-01-01",end="2025-06-30",expected=1_789_000_000.); prior_nci=_structural_flow(structural,name="NetIncomeLossAttributableToNoncontrollingInterest",start="2025-01-01",end="2025-06-30",expected=-4_000_000.); current_value=current_net["value"]-current_nci["value"]; prior_value=prior_net["value"]-prior_nci["value"]; current={"value":current_value,"formula":"net income less reported NCI line","sources":[current_net,current_nci]}; prior={"value":prior_value,"formula":"net income less reported NCI line","sources":[prior_net,prior_nci]}
    else:
        current_source=_structural_flow(structural,name="NetIncomeLossAvailableToCommonStockholdersBasic",start="2026-01-01",end="2026-06-30",expected=5_922_000_000.); prior_source=_structural_flow(structural,name="NetIncomeLossAvailableToCommonStockholdersBasic",start="2025-01-01",end="2025-06-30",expected=2_800_000_000.); current_value=current_source["value"]; prior_value=prior_source["value"]; current={"value":current_value,"formula":"reported available-to-common earnings","sources":[current_source]}; prior={"value":prior_value,"formula":"reported available-to-common earnings","sources":[prior_source]}
    ttm=latest_value+current_value-prior_value
    observations.append(HistoryObservation(period_role="operating_ttm",period_end="2026-06-30",fiscal_year=None,value=ttm,unit="USD",formula="latest FY plus current H1 less prior H1 parent-attributable common earnings",sources=annual_sources[latest_year]+tuple(current["sources"])+tuple(prior["sources"])))
    metric=summarize_history_metric("normalized_common_earnings",observations); periods=tuple(row.period_end for row in observations if row.period_role=="annual"); full_history=len(set(periods))>=3
    if not full_history or metric is None: raise ValueError(f"{ticker}: equity earnings history insufficient")
    profile=CompanyHistoryProfile(policy_version=HISTORY_POLICY_VERSION,lane="normalized_equity_earnings",valuation_date=BATCH_12_VALUATION_DATE,annual_periods=periods,metrics=(metric,),full_history=full_history,assumption_source_mix="reported_and_company_history")
    multiples=(5.,8.,11.) if ticker=="HUM" else (4.,7.,10.); rows=[]
    for i,state in enumerate(("bear","base","bull")):
        value=(metric.low,metric.base,metric.high)[i]; per_share=value*multiples[i]/shares[i]; rows.append({"name":state,"conditional_value_per_share":per_share,"normalized_consolidated_earnings":value,"earnings_multiple":multiples[i],"shares":shares[i],"cash_conversion_margin":0.,"wacc":0.,"limited_liability_floor_applied":False})
    scenario={"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]}; reliability=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="Low",source_cap="High",reasons=("CONDITIONAL_EVENT_MODEL","SPECIALIST_MODEL_UNCERTAINTY")); warning=("Conditional Low managed-care equity-earnings estimate. Medical claims, capital requirements, member funds, acquisition integration, and underwriting normalization remain material." if ticker=="HUM" else "Conditional Low mixed insurance/PBM/retail equity-earnings estimate. Medical claims, customer/member funds, segment mix, reimbursement, and debt remain material."); invalidation="Invalidate if underwriting/medical claims, regulated capital, member funds, acquisitions, debt, or diluted shares changes." if ticker=="HUM" else "Invalidate if insurance/PBM/retail mix, medical claims, member funds, reimbursement, debt, or diluted shares changes."
    assumptions={**profile.public_metadata(),"normalization_basis":"company_history_with_material_event_override","assumption_source_mix":"reported_history_and_finsight_policy","normalized_consolidated_earnings":(metric.low,metric.base,metric.high),"earnings_multiples":multiples,"shares":shares,"route_is_equity_level":True,"ev_debt_bridge_applied":False,"equity_floor_basis":"not applied","calculator_calibration":"Calculator varies normalized earnings and the earnings multiple around the published base.","invalidation":invalidation}
    baseline=BaselineValuation(ticker=ticker,method="managed_care_normalized_equity_earnings" if ticker=="HUM" else "mixed_health_services_normalized_equity_earnings",method_version=BATCH_12_HISTORY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence=reliability.label,availability_type=AvailabilityType.CONDITIONAL,key_assumptions=(BaselineAssumption("company earnings history",str(profile.history_years_used),AssumptionClassification.HISTORICALLY_DERIVED,"Source-linked parent-attributable common-equity earnings history supplies the normalized range."),BaselineAssumption("equity-level model",str(assumptions),AssumptionClassification.FINSIGHT_ASSUMPTION,"Regulated insurance and financing claims remain inside common earnings; no EV debt bridge is applied.")),warnings=(warning,invalidation),confidence_reasons=tuple(reliability.reasons),calculator_link=f"/api/us-valuations/{ticker}/calculator")
    equity_expected=19_213_000_000. if ticker=="HUM" else 79_702_000_000.; context=[_point(structural,name="StockholdersEquity",expected=equity_expected,period_end="2026-06-30"),_duration(structural,name="WeightedAverageNumberOfDilutedSharesOutstanding",expected=shares[1],period_start="2026-01-01",period_end="2026-06-30")]
    return {"ticker":ticker,"method":baseline.method,"model_version":BATCH_12_HISTORY_VERSION,"availability_type":"conditional_estimate","scenario_rows":rows,"scenario_range":scenario,"reported_inputs":{"ttm_common_earnings":ttm},"governed_assumptions":assumptions,"history_reliability":reliability.as_dict(),"source_ledger":{"controlling_filing":filing,"common_earnings_reconstruction":{"latest_fy":latest_value,"current_h1":current_value,"prior_h1":prior_value,"ttm":ttm,"sources":list(annual_sources[latest_year])+current["sources"]+prior["sources"]},"company_history_profile":profile.as_private_dict(),"equity_model_context":context,"bridge_treatment":"Equity-level model; medical claims, member funds, regulated capital, operating liabilities, NCI, and debt remain inside parent-attributable common earnings. No enterprise-value bridge is applied.","structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":warning,"baseline":baseline.as_private_dict()}


def _withheld_uhs(filing: dict, structural: dict, policy: Policy) -> dict:
    reason="Withheld. UHS completed a $188M post-period Ireland facilities acquisition before the valuation date while the $835M debt-financed Talkspace acquisition remained pending; the filing does not provide one post-Ireland cash, debt, and operating-cash object."
    invalidation="Revalue after filed post-Ireland cash/debt and Talkspace closing or termination state."
    baseline=BaselineValuation(ticker="UHS",method="unavailable_post_period_acquisition_state",method_version=BATCH_12_HISTORY_VERSION,low=None,base=None,high=None,confidence=None,availability_type=AvailabilityType.NOT_AVAILABLE,warnings=(reason,invalidation))
    return {"ticker":"UHS","method":"unavailable_post_period_acquisition_state","model_version":BATCH_12_HISTORY_VERSION,"availability_type":"not_available","scenario_rows":[],"scenario_range":{"low":None,"base":None,"high":None},"reported_inputs":{},"governed_assumptions":{"history_policy_version":HISTORY_POLICY_VERSION,"history_years_used":0,"normalization_basis":"post_period_acquisition_cash_and_debt_state_unavailable","assumption_source_mix":"reported_pre_acquisition_state_and_subsequent_event_terms","invalidation":invalidation},"history_reliability":None,"source_ledger":{"controlling_filing":filing,"bridge_sources":_bridge("UHS",structural,policy),"bridge_reconciliation":{"reported_period_cash":policy.cash,"reported_period_debt":policy.debt,"reported_period_claims":policy.claims,"shares":policy.shares},"release_condition":"Filed post-Ireland cash/debt plus final Talkspace closing or termination state.","structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":reason,"baseline":baseline.as_private_dict()}


def build_batch_12_history_result(*, ticker: str, source_root: Path, structural_root: Path) -> dict:
    packet=Path(source_root)/ticker; submissions=json.loads((packet/"submissions.json").read_text()); facts=json.loads((packet/"companyfacts.json").read_text()); manifest=json.loads((packet/"source-manifest.json").read_text()); structural=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text()); filing=_controlling(manifest,submissions)
    if structural["source_accession"]!=filing["accession"]: raise ValueError(f"{ticker}: controlling source mismatch")
    if ticker in EQUITY_EARNINGS_TICKERS:
        shares=_shares(120_893_000. if ticker=="HUM" else 1_283_000_000.); return _equity_history(ticker,facts,structural,filing,shares)
    policy=P[ticker]
    if filing["period_end"]!=policy.period: raise ValueError(f"{ticker}: period mismatch")
    if ticker=="UHS": return _withheld_uhs(filing,structural,policy)
    normalizer=_normalizer(submissions,facts)
    if ticker=="ABT": flows=_reconstruct_ttm(structural,normalizer,{"revenue":("RevenueFromContractWithCustomerExcludingAssessedTax",23_757_000_000.,21_500_000_000.),"operating_cash_flow":("NetCashProvidedByUsedInOperatingActivities",3_803_000_000.,3_464_000_000.),"capital_expenditures":("PaymentsToAcquirePropertyPlantAndEquipment",896_000_000.,986_000_000.),"interest_expense":("InterestExpenseNonoperating",525_000_000.,252_000_000.)},policy.period)
    else:
        flows={field:normalizer.ttm_flow(field) for field in ("revenue","operating_cash_flow","capital_expenditures","interest_expense")} if ticker!="LLY" else {field:normalizer.ttm_flow(field) for field in ("revenue","operating_cash_flow")}
    if ticker=="BAX":
        annual_interest=_companyfact_custom_annual(facts,"InterestIncomeExpenseNonoperatingNet","2025-12-31",field="interest_expense"); current_interest=_structural_flow(structural,name="InterestIncomeExpenseNonoperatingNet",start="2026-01-01",end=policy.period,expected=-130_000_000.); prior_interest=_structural_flow(structural,name="InterestIncomeExpenseNonoperatingNet",start="2025-01-01",end="2025-06-30",expected=-122_000_000.); flows["interest_expense"]={"field":"interest_expense","value":abs(annual_interest["value"])+abs(current_interest["value"])-abs(prior_interest["value"]),"period_end":policy.period,"method":"latest_fy_net_interest_magnitude_plus_current_h1_magnitude_minus_prior_h1_magnitude","sources":[annual_interest,current_interest,prior_interest],"sign_treatment":"Negative net-interest facts are aligned to expense magnitudes before TTM arithmetic."}
    if ticker=="LLY":
        annual_capex=_companyfact_custom_annual(facts,"PaymentsToAcquireOtherPropertyPlantAndEquipment","2025-12-31"); current=_structural_flow(structural,name="PaymentsToAcquireOtherPropertyPlantAndEquipment",start="2026-01-01",end=policy.period,expected=5_259_000_000.); prior=_structural_flow(structural,name="PaymentsToAcquireOtherPropertyPlantAndEquipment",start="2025-01-01",end="2025-06-30",expected=3_207_000_000.); flows["capital_expenditures"]={"field":"capital_expenditures","value":annual_capex["value"]+current["value"]-prior["value"],"period_end":policy.period,"method":"latest_fy_plus_current_h1_minus_prior_h1_custom_capex","sources":[annual_capex,current,prior]}; interest=normalizer.annual_series("interest_expense",1)[0]; current_interest=_dimension_fact(structural,name="InterestExpenseNonoperating",expected=677_000_000.,start="2026-01-01",end=policy.period,member="ReportableSegmentMember"); prior_interest=_dimension_fact(structural,name="InterestExpenseNonoperating",expected=493_000_000.,start="2025-01-01",end="2025-06-30",member="ReportableSegmentMember"); flows["interest_expense"]={"field":"interest_expense","value":abs(float(interest.value))+current_interest["value"]-prior_interest["value"],"period_end":policy.period,"method":"latest_fy_plus_current_h1_minus_prior_h1_aggregate_interest","sources":[interest.as_dict(),current_interest,prior_interest]}
    if any(flow["period_end"]!=policy.period for flow in flows.values()): raise ValueError(f"{ticker}: TTM period mismatch")
    try:
        tax_rate,tax_sources=_normalized_tax_rate(normalizer); tax_rate_treatment={"value":tax_rate,"method":"median_of_at_least_three_positive_annual_effective_tax_rates","sources":list(tax_sources)}
    except ValueError:
        tax_rate=.21; tax_rate_treatment={"value":tax_rate,"method":"governed_practical_fallback_when_three_positive_annual_effective_tax_observations_are_unavailable","sources":[],"reason":"insufficient_positive_annual_pretax_periods"}
    current_cash=cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]),capital_expenditures=float(flows["capital_expenditures"]["value"]),spectrum_investment=0.,interest_expense=abs(float(flows["interest_expense"]["value"])),tax_rate=tax_rate)
    annual_sources=_lly_annual_states(normalizer,facts) if ticker=="LLY" else _annual_cash_with_losses(normalizer)[2]; ttm_sources=[dict(row) for flow in flows.values() for row in flow.get("sources",[]) if isinstance(row,dict)]; revenue=float(flows["revenue"]["value"]); profile=build_cash_fcff_history_profile(annual_cash_states=annual_sources,ttm_revenue=revenue,ttm_cash_fcff=current_cash,ttm_period_end=policy.period,ttm_sources=ttm_sources,valuation_date=BATCH_12_VALUATION_DATE); cash=profile.metric("cash_conversion_margin"); growth_metric=profile.metric("revenue_growth")
    if not profile.full_history or cash is None or growth_metric is None: raise ValueError(f"{ticker}: history insufficient")
    margins=tuple(max(.001,value) for value in (cash.low,cash.base,cash.high)); growth=(max(-.05,min(.03,growth_metric.low)),max(-.03,min(.04,growth_metric.base)),max(0.,min(.05,growth_metric.high))); rows=[]
    for i,state in enumerate(("bear","base","bull")):
        raw=five_year_fcff_dcf(revenue=revenue,fcff_margin=margins[i],growth=growth[i],wacc=policy.wacc[i],terminal_growth=policy.terminal[i],cash_and_investments=policy.cash,debt=policy.debt,noncontrolling_interests=policy.claims,shares=policy.shares[i]); value=max(0.,float(raw["value_per_share"])); rows.append({"name":state,"conditional_value_per_share":value,"raw_value_per_share":float(raw["value_per_share"]),"cash_conversion_margin":margins[i],"growth":growth[i],"wacc":policy.wacc[i],"terminal_growth":policy.terminal[i],"shares":policy.shares[i],"limited_liability_floor_applied":value==0 and float(raw["value_per_share"])<0})
    scenario={"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]}
    if not 0<=scenario["low"]<=scenario["base"]<=scenario["high"] or scenario["base"]<=0: raise ValueError(f"{ticker}: invalid range")
    is_pass=ticker in PASS_TICKERS; reasons=() if is_pass else ("CONDITIONAL_EVENT_MODEL","SPECIALIST_MODEL_UNCERTAINTY"); reliability=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="High" if is_pass else "Low",source_cap="High",reasons=reasons); public=profile.public_metadata()
    if not is_pass: public.update({"normalization_basis":"company_history_with_material_event_override","assumption_source_mix":"reported_history_and_finsight_policy"})
    assumptions={**public,"cash_conversion_margin":margins,"growth":growth,"wacc":policy.wacc,"terminal_growth":policy.terminal,"shares":policy.shares,"equity_floor_basis":"limited-liability floor after negative residual" if scenario["low"]==0 else "not applied","calculator_calibration":"Calculator is calibrated to the published base; private history and bridge remain fixed.","invalidation":policy.invalidation}; baseline=BaselineValuation(ticker=ticker,method=policy.method,method_version=BATCH_12_HISTORY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence=reliability.label,availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL,key_assumptions=(BaselineAssumption("company history",str(profile.history_years_used),AssumptionClassification.HISTORICALLY_DERIVED,"Source-linked history supplies cash-conversion and growth states."),BaselineAssumption("reported anchors",str({key:value["value"] for key,value in flows.items()}),AssumptionClassification.REPORTED,"Cutoff-safe filing facts anchor current cash generation."),BaselineAssumption("scenario policy",str(assumptions),AssumptionClassification.FINSIGHT_ASSUMPTION,"Rates, growth, shares, and named health-care dependencies remain transparent assumptions.")),warnings=(policy.warning,policy.invalidation),confidence_reasons=tuple(reliability.reasons),calculator_link=f"/api/us-valuations/{ticker}/calculator"); bridge=_bridge(ticker,structural,policy)
    treatments={"ABT":"$1.111B long-term investments are excluded from excess cash; $263M contingent consideration is added to $652M NCI once.","BAX":"Negative $27M book NCI is diagnostic and not treated as an equity asset; $10M contingent consideration is subtracted.","BDX":"$155M restricted cash/investments are excluded; the $4B spin consideration is event evidence, not added to intrinsic value. The $181M supplier-finance obligation remains in accounts payable and operating cash flow and is not subtracted again as debt.","BMY":"$1.027B short-term borrowings plus $42.861B total long-term debt are included once; the separate $607M contingent-value-rights liability is subtracted once as an additional common-equity claim.","RVTY":"$1.238M restricted cash is excluded. The $3.2222B combined-debt fact is gross principal and is used once as a conservative equity claim; the $16.95M of unamortized discounts and issuance costs embedded in the $3.20525B net carrying amount are not treated as excess value. The $32.818M restructuring reserve is an operating liability represented in operating cash flow and history, so it is retained as a diagnostic and not subtracted again as an equity-bridge claim.","LLY":"$3.856B long-term investments are excluded; $2.518B current/noncurrent contingent consideration is subtracted.","WST":"$136M completed divestiture proceeds are added to reported cash; $3.3M contingent consideration and $4.4M finance leases are claims.","UHS":"$133.583M restricted cash is excluded; $73.603M temporary equity is the same approximate redeemable NCI claim and is not added twice."}[ticker]
    return {"ticker":ticker,"method":policy.method,"model_version":BATCH_12_HISTORY_VERSION,"availability_type":baseline.availability_type.value,"scenario_rows":rows,"scenario_range":scenario,"reported_inputs":{"ttm_revenue":revenue,"ttm_operating_cash_flow":flows["operating_cash_flow"]["value"],"ttm_capex":flows["capital_expenditures"]["value"],"ttm_interest":flows["interest_expense"]["value"],"tax_rate":tax_rate,"ttm_cash_fcff":current_cash},"governed_assumptions":assumptions,"history_reliability":reliability.as_dict(),"source_ledger":{"controlling_filing":filing,"flow_sources":flows,"tax_rate_treatment":tax_rate_treatment,"company_history_profile":profile.as_private_dict(),"bridge_sources":bridge,"bridge_reconciliation":{"cash_and_investments":policy.cash,"debt_and_finance_leases":policy.debt,"preferred_nci_and_other_claims":policy.claims,"shares":policy.shares,"treatment":treatments},"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":policy.warning,"baseline":baseline.as_private_dict()}


if set(P)|set(EQUITY_EARNINGS_TICKERS)!=set(BATCH_12_TICKERS): raise RuntimeError("Batch 12 policy denominator mismatch")
