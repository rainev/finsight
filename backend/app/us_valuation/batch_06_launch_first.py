"""Launch-first Conditional Low baselines for controlled Batch 06."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from statistics import median
from typing import Any

from .baseline import AssumptionClassification,AvailabilityType,BaselineAssumption,BaselineValuation,FallbackRejected,FallbackStage,run_fallback_ladder
from .batch_02_conditional_estimates import five_year_fcff_dcf
from .batch_02_practical_inputs import _annual_cash_fcff,_normalizer,_normalized_tax_rate,cash_fcff_from_reported
from .batch_04_launch_first import _controlling,_duration,_point,_source_proven_no_other_equity_claims
from .batch_05_launch_first import _companyfacts_duration,_structural_duration,_source_proven_no_debt
from .batch_06 import BATCH_06_TICKERS
from .equity_fact_selection import annual_facts
from .history import HISTORY_POLICY_VERSION,CompanyHistoryProfile,HistoryObservation,build_cash_fcff_history_profile,summarize_history_metric
from .reliability import assess_reliability


BATCH_06_LAUNCH_FIRST_VERSION = "BATCH-06-LAUNCH-FIRST-1.0"
BATCH_06_HISTORY_REPAIR_VERSION = "BATCH-06-HISTORY-REPAIR-1.0"
PASS_TICKERS = frozenset({"BBY","DECK","TSCO","DRI","RL","MAR","CMG"})


@dataclass(frozen=True)
class Policy:
    method: str
    growth: tuple[float,float,float]
    wacc: tuple[float,float,float]
    terminal: tuple[float,float,float]
    shares: tuple[float,float,float]
    period: str
    cash: float
    debt: float
    reserve: tuple[float,float,float]
    warning: str
    invalidation: str
    working_capital_adjustment: tuple[float,float,float]=(0,0,0)
    margin_override: tuple[float,float,float]|None=None


P={
 "BBY":Policy("supplier_finance_normalized_retail_fcff",(-.03,0,.03),(.11,.10,.09),(0,.01,.02),(216_582_500.,211_300_000.,206_017_500.),"2026-05-02",1_749_000_000.,1_169_000_000.,(.02,.01,0),"Conditional Low estimate. Inventory, supplier finance, leases, and a mixed annual/TTM source anchor materially widen the range.","Invalidate when aligned revenue, supplier-finance reversal, debt, leases, or shares leave the governed range.",(.015,.005,0)),
 "DECK":Policy("seasonal_footwear_inventory_cash_fcff",(0,.05,.09),(.11,.095,.085),(.01,.02,.025),(142_022_975.,138_559_000.,135_095_025.),"2026-06-30",1_602_589_000.,0.,(.10,.05,0),"Conditional Low estimate. Seasonal inventory, leases, repurchases, and unreported financing claims remain broadly ranged.","Invalidate when inventory seasonality, leases, debt evidence, or diluted shares leave the governed range.",(.02,.005,0)),
 "TSCO":Policy("supplier_finance_inventory_cash_fcff",(0,.04,.07),(.10,.09,.08),(.01,.02,.025),(539_576_400.,526_416_000.,513_255_600.),"2026-06-27",231_588_000.,2_207_074_000.,(.02,.01,0),"Conditional Low estimate. Inventory expansion, supplier finance, leases, and buybacks require normalized cash scenarios.","Invalidate when inventory/AP reversal, supplier finance, debt, leases, or shares leave the governed range.",(.01,.003,0)),
 "LEN":Policy("homebuilder_normalized_equity_earnings_baseline",(-.06,0,.06),(.12,.10,.09),(0,.01,.02),(248_672_175.,242_607_000.,236_541_825.),"2026-05-31",0.,0.,(.02,.01,0),"Conditional Low normalized-equity-earnings estimate. Mortgage activity, land deposits, inventory, and financing remain inside consolidated earnings.","Invalidate when consolidated earnings, mortgage/land exposure, liabilities, or diluted shares leave the governed range."),
 "DRI":Policy("restaurant_finance_lease_cash_fcff",(-.02,.03,.06),(.11,.095,.085),(0,.015,.02),(119_207_500.,116_300_000.,113_392_500.),"2026-05-31",219_500_000.,3_929_500_000.,(.02,.01,0),"Conditional Low estimate. Restaurant reinvestment, finance leases, operating leases, and buybacks drive a broad range.","Invalidate when cash conversion, debt/finance leases, operating leases, or diluted shares leave the range.",(.01,.003,0)),
 "AMZN":Policy("capex_lease_normalized_cash_fcff",(.03,.08,.12),(.105,.09,.08),(.01,.02,.025),(11_161_225_000.,10_889_000_000.,10_616_775_000.),"2026-06-30",122_988_000_000.,146_771_000_000.,(.02,.01,0),"Conditional Low estimate. Current reported post-capex cash is negative; AI/data-center capex, leases, and cash conversion determine the range.","Invalidate when capex commitments, finance debt, operating-lease treatment, or diluted shares leave the range.",margin_override=(-.0114,.034,.06)),
 "RL":Policy("apparel_inventory_fx_cash_fcff",(-.02,.03,.06),(.11,.095,.085),(0,.015,.02),(62_832_500.,61_300_000.,59_767_500.),"2026-06-27",1_941_600_000.,1_467_200_000.,(.02,.01,0),"Conditional Low estimate. Inventory, FX, brand mix, leases, and repurchases require normalized states.","Invalidate when inventory/FX conversion, debt, leases, or diluted shares leave the range.",(.02,.005,0)),
 "YUM":Policy("franchise_disposal_lease_cash_fcff",(0,.04,.07),(.10,.09,.08),(.01,.02,.025),(284_950_000.,278_000_000.,271_050_000.),"2026-06-30",674_000_000.,9_462_000_000.,(.02,.01,0),"Conditional Low estimate. Franchise economics, disposal-group scope, leases, negative equity, and an annual interest carry-forward remain provisional.","Invalidate when continuing operations, disposal-group claims, debt/capital leases, or shares leave the range.",(.01,.003,0)),
 "MAR":Policy("asset_light_franchise_lease_cash_fcff",(0,.04,.07),(.10,.09,.08),(.01,.02,.025),(272_342_500.,265_700_000.,259_057_500.),"2026-06-30",462_000_000.,16_915_000_000.,(.02,.01,0),"Conditional Low estimate. Asset-light franchise cash, reimbursed revenue, leases, debt, negative equity, and buybacks widen the range.","Invalidate when franchise cash scope, debt/capital leases, or diluted shares leave the range.",(.01,.003,0)),
 "CMG":Policy("restaurant_lease_owner_cash_proxy",(0,.06,.10),(.11,.095,.085),(.01,.02,.025),(1_322_723_550.,1_290_462_000.,1_258_200_450.),"2026-06-30",697_357_000.,0.,(.10,.05,0),"Conditional Low owner-cash estimate. No interest addback or verified debt-zero assumption is used; leases, reinvestment, and buybacks remain provisional.","Invalidate when debt/interest evidence, lease cash, restaurant capex, or diluted shares leave the range.",margin_override=(.08,.1263,.158)),
}


def _bridge_sources(ticker,structural,policy,assets):
    point=lambda name,value:_point(structural,name=name,expected=value,period_end=policy.period)
    specs={
      "BBY":[("CashAndCashEquivalentsAtCarryingValue",1_749_000_000.),("DebtAndCapitalLeaseObligations",1_169_000_000.),("InventoryNet",5_598_000_000.),("SupplierFinanceProgramObligation",861_000_000.)],
      "DECK":[("CashAndCashEquivalentsAtCarryingValue",1_602_589_000.),("InventoryNet",807_580_000.)],
      "TSCO":[("CashAndCashEquivalentsAtCarryingValue",231_588_000.),("LongTermDebtNoncurrent",2_153_826_000.),("FinanceLeaseLiabilityCurrent",10_315_000.),("FinanceLeaseLiabilityNoncurrent",42_933_000.),("InventoryNet",3_518_451_000.),("SupplierFinanceProgramObligation",179_000_000.)],
      "DRI":[("CashAndCashEquivalentsAtCarryingValue",219_500_000.),("DebtInstrumentCarryingAmount",2_189_100_000.),("FinanceLeaseLiability",1_740_400_000.),("InventoryNet",326_300_000.)],
      "AMZN":[("CashCashEquivalentsAndMarketableSecuritiesExcludingRestrictedCashAndInvestments",122_988_000_000.),("LongTermDebt",132_995_000_000.),("ShortTermBorrowings",325_000_000.),("FinanceLeaseLiability",13_451_000_000.),("InventoryNet",38_184_000_000.)],
      "RL":[("CashAndCashEquivalentsAtCarryingValue",1_719_000_000.),("ShortTermInvestments",222_600_000.),("LongTermDebtNoncurrent",1_239_400_000.),("FinanceLeaseLiabilityCurrent",20_300_000.),("FinanceLeaseLiabilityNoncurrent",207_500_000.),("InventoryNet",1_163_700_000.)],
      "YUM":[("CashAndCashEquivalentsAtCarryingValue",674_000_000.),("LongTermDebtAndCapitalLeaseObligations",9_462_000_000.)],
      "MAR":[("CashAndCashEquivalentsAtCarryingValue",462_000_000.),("DebtAndCapitalLeaseObligations",16_915_000_000.)],
      "CMG":[("CashAndCashEquivalentsAtCarryingValueAndDebtSecuritiesHeldToMaturityFairValue",697_357_000.),("InventoryNet",46_622_000.)],
    }
    starts={"BBY":"2026-02-01","DECK":"2026-04-01","TSCO":"2025-12-28","DRI":"2025-05-26","AMZN":"2026-01-01","RL":"2026-03-29","YUM":"2026-01-01","MAR":"2026-01-01","CMG":"2026-01-01"}
    rows=[point("Assets",assets),*[point(name,value) for name,value in specs[ticker]]]
    rows.append(_duration(structural,name="WeightedAverageNumberOfDilutedSharesOutstanding",expected=policy.shares[1],period_start=starts[ticker],period_end=policy.period))
    return rows


def _reconstructed_flow(*, field, components):
    fiscal_year,current,prior=components
    return {"value":fiscal_year["value"]+current["value"]-prior["value"],"period_end":current["period_end"],"method":"latest_fy_plus_current_ytd_minus_prior_ytd","sources":list(components),"field":field}


def _bby_revenue(facts):
    concept="RevenueFromContractWithCustomerIncludingAssessedTax"
    components=(
        _companyfacts_duration(facts,concept=concept,accession="0000764478-26-000009",start="2025-02-02",end="2026-01-31",expected=41_691_000_000.),
        _companyfacts_duration(facts,concept=concept,accession="0000764478-26-000022",start="2026-02-01",end="2026-05-02",expected=8_936_000_000.),
        _companyfacts_duration(facts,concept=concept,accession="0000764478-26-000022",start="2025-02-02",end="2025-05-03",expected=8_767_000_000.),
    )
    return _reconstructed_flow(field="revenue",components=components)


def _annual_owner_cash(normalizer):
    cash=[];revenue=[];rows=[]
    for operating_cash in normalizer.annual_series("operating_cash_flow",5):
        capex=normalizer.annual_at_end("capital_expenditures",operating_cash.end);sales=normalizer.annual_at_end("revenue",operating_cash.end)
        if capex is None or sales is None:continue
        owner_cash=float(operating_cash.value)-float(capex.value)
        if owner_cash>0 and sales.value>0:
            cash.append(owner_cash);revenue.append(float(sales.value));rows.append({"period_end":operating_cash.end,"operating_cash_flow":operating_cash.as_dict(),"capital_expenditures":capex.as_dict(),"interest_expense":None,"income_tax":None,"pretax_income":None,"revenue":sales.as_dict(),"cash_fcff":owner_cash,"formula":"operating cash flow - capital expenditures; no interest addback because current filing has no interest-bearing debt"})
    return tuple(cash),tuple(revenue),tuple(rows)


def _history_source(fact):
    return {"concept":fact.concept,"value":fact.value,"unit":fact.unit,"period_start":fact.period_start,"period_end":fact.period_end,"filed_date":fact.filed_date,"accession":fact.accession,"form":fact.form,"fiscal_year":fact.fiscal_year}


def _len_history(facts):
    gaap=facts.get("facts",{}).get("us-gaap",{});annual=annual_facts(gaap,concepts=("NetIncomeLossAvailableToCommonStockholdersBasic","NetIncomeLoss"),unit="USD",valuation_date="2026-08-14");observations=[]
    for year in sorted(annual)[-5:]:
        fact=annual[year]
        if fact.value>0:observations.append(HistoryObservation(period_role="annual",period_end=fact.period_end,fiscal_year=fact.fiscal_year,value=fact.value,unit="USD",formula="reported annual common-stockholder earnings",sources=(_history_source(fact),)))
    metric=summarize_history_metric("normalized_common_earnings",observations);periods=tuple(row.period_end for row in observations);full=len(set(periods))>=3
    return CompanyHistoryProfile(policy_version=HISTORY_POLICY_VERSION,lane="normalized_equity_earnings",valuation_date="2026-08-14",annual_periods=periods,metrics=(metric,) if metric else (),full_history=full,assumption_source_mix="reported_and_company_history" if full else "reported_history_and_finsight_policy")


LEN_EARNINGS={
 "ttm":1_598_948_000.,
 "fy":(2_058_083_000.,"0001628280-26-003870","2024-12-01","2025-11-30"),
 "current_ytd":(526_751_000.,"0001628280-26-046019","2025-12-01","2026-05-31"),
 "prior_ytd":(985_886_000.,"0001628280-26-046019","2024-12-01","2025-05-31"),
}


def _len_result(policy,filing,structural,facts,assets,flows,history_backed=False):
    earn=(LEN_EARNINGS["ttm"]*.6,LEN_EARNINGS["ttm"],LEN_EARNINGS["ttm"]*1.2);history_profile=_len_history(facts) if history_backed else None
    if history_profile and history_profile.full_history:
        metric=history_profile.metric("normalized_common_earnings")
        if metric is not None:earn=(metric.low,metric.base,metric.high)
    multiples=(5.,8.,11.);rows=[]
    for index,name in enumerate(("bear","base","bull")):
        value=earn[index]*multiples[index]/policy.shares[index]
        rows.append({"name":name,"conditional_value_per_share":value,"normalized_consolidated_earnings":earn[index],"earnings_multiple":multiples[index],"shares":policy.shares[index],"wacc":policy.wacc[index],"cash_conversion_margin":earn[index]/float(flows["revenue"]["value"]),"limited_liability_floor_applied":False})
    scenario_range={"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]}
    components={key:_companyfacts_duration(facts,concept="NetIncomeLossAvailableToCommonStockholdersBasic",accession=value[1],start=value[2],end=value[3],expected=value[0]) for key,value in (("fy",LEN_EARNINGS["fy"]),("current_ytd",LEN_EARNINGS["current_ytd"]),("prior_ytd",LEN_EARNINGS["prior_ytd"]))}
    context=[_point(structural,name="Assets",expected=33_701_455_000.,period_end=policy.period),_point(structural,name="Liabilities",expected=11_935_729_000.,period_end=policy.period),_point(structural,name="CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",expected=2_173_778_000.,period_end=policy.period),_point(structural,name="MinorityInterest",expected=145_088_000.,period_end=policy.period),_point(structural,name="EscrowDeposit",expected=559_800_000.,period_end=policy.period),_structural_duration(structural,name="IncreaseInDepositsAndPreAcquisitionCostsOnRealEstate",expected=554_766_000.,start="2025-12-01",end=policy.period),_structural_duration(structural,name="IncreaseDecreaseInLoansHeldForSale",expected=-246_731_000.,start="2025-12-01",end=policy.period),_structural_duration(structural,name="InventoryWriteDown",expected=36_240_000.,start="2025-12-01",end=policy.period),_duration(structural,name="WeightedAverageNumberOfDilutedSharesOutstanding",expected=policy.shares[1],period_start="2025-12-01",period_end=policy.period)]
    reserve_values=tuple(assets*rate for rate in policy.reserve);impact=max(abs(reserve_values[0]-reserve_values[1]),abs(reserve_values[2]-reserve_values[1]))/max(scenario_range["base"]*policy.shares[1],1.)
    history_public=history_profile.public_metadata() if history_profile else {}
    if history_profile:history_public.update({"normalization_basis":"company_history_with_material_event_override","assumption_source_mix":"reported_history_and_finsight_policy"})
    assumptions={**history_public,"cash_conversion_margin":tuple(row["cash_conversion_margin"] for row in rows),"normalized_consolidated_earnings":earn,"earnings_multiples":multiples,"shares":policy.shares,"route_is_mortgage_separated_fcff":False,"ev_debt_bridge_applied":False,"equity_floor_basis":"not applied","calculator_calibration":"Calculator directly varies normalized earnings and the earnings multiple around the published base.","invalidation":policy.invalidation}
    reliability=assess_reliability(accounting_low=scenario_range["base"]-impact*scenario_range["base"],accounting_base=scenario_range["base"],accounting_high=scenario_range["base"]+impact*scenario_range["base"],scenario_low=scenario_range["low"],scenario_base=scenario_range["base"],scenario_high=scenario_range["high"],model_cap="Low",source_cap="High",reasons=("CONDITIONAL_EVENT_MODEL",)) if history_backed else None;version=BATCH_06_HISTORY_REPAIR_VERSION if history_backed else BATCH_06_LAUNCH_FIRST_VERSION
    def primary():raise FallbackRejected("Mortgage-separated FCFF lacks current point-in-time land/mortgage evidence; consolidated equity-earnings baseline selected.")
    def conditional():return BaselineValuation(ticker="LEN",method=policy.method,method_version=version,low=scenario_range["low"],base=scenario_range["base"],high=scenario_range["high"],confidence=reliability.label if reliability else "Low",availability_type=AvailabilityType.CONDITIONAL,key_assumptions=((BaselineAssumption("company history",str(history_profile.history_years_used),AssumptionClassification.HISTORICALLY_DERIVED,"Source-linked annual common-earnings history supplies the normalized range."),) if history_profile else ())+ (BaselineAssumption("reported consolidated earnings",str(components),AssumptionClassification.REPORTED,"FY plus current YTD less prior YTD net income."),BaselineAssumption("earnings scenarios",str(assumptions),AssumptionClassification.FINSIGHT_ASSUMPTION,"Broad equity-level baseline; mortgage and land activity remain consolidated.")),warnings=(policy.warning,policy.invalidation),confidence_reasons=tuple(reliability.reasons) if reliability else ("CONDITIONAL_EVENT_MODEL","SPECIALIST_MODEL_UNCERTAINTY"),calculator_link="/api/us-valuations/LEN/calculator")
    baseline=run_fallback_ladder(ticker="LEN",strategies=((FallbackStage.PRIMARY_INTRINSIC,"mortgage_separated_fcff",primary),(FallbackStage.CONDITIONAL,policy.method,conditional)))
    return {"ticker":"LEN","method":policy.method,"model_version":version,"availability_type":"conditional_estimate","scenario_rows":rows,"scenario_range":scenario_range,"reported_inputs":{"revenue_anchor":flows["revenue"]["value"],"ttm_common_net_income":LEN_EARNINGS["ttm"]},"governed_assumptions":assumptions,"accounting_impact_ratio":impact,"history_reliability":reliability.as_dict() if reliability else None,"source_ledger":{"controlling_filing":filing,"net_income_reconstruction":{"components":components,"ttm":LEN_EARNINGS["ttm"],"formula":"FY + current YTD - prior YTD"},"company_history_profile":history_profile.as_private_dict() if history_profile else None,"mortgage_and_land_context":context,"accounting_uncertainty":{"source_linked_exposure":assets,"reserve_rates":policy.reserve,"reserve_values":reserve_values,"impact_ratio":impact,"basis":"Current total assets multiplied by governed 2%/1%/0% unresolved mortgage/land reserve rates."},"bridge_treatment":"Equity-level baseline; mortgage, land financing, and liabilities remain inside common earnings. No EV debt bridge is applied.","structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":policy.warning,"baseline":baseline.as_private_dict()}


def build_batch_06_launch_first_result(*,ticker,source_root,structural_root,history_backed=False):
    policy=P[ticker];packet=Path(source_root)/ticker;sub=json.loads((packet/"submissions.json").read_text());facts=json.loads((packet/"companyfacts.json").read_text());manifest=json.loads((packet/"source-manifest.json").read_text());structural=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text());filing=_controlling(manifest,sub)
    if filing["period_end"]!=policy.period or structural["source_accession"]!=filing["accession"]:raise ValueError(f"{ticker}: controlling source mismatch")
    normalizer=_normalizer(sub,facts);flows={field:normalizer.ttm_flow(field) for field in ("revenue","operating_cash_flow","capital_expenditures")};assets=float(normalizer.instant("total_assets").value)
    if ticker=="BBY":flows["revenue"]=_bby_revenue(facts)
    if ticker=="LEN":return _len_result(policy,filing,structural,facts,assets,flows,history_backed=history_backed)
    interest_status="reported_ttm"
    try:interest=normalizer.ttm_flow("interest_expense")
    except ValueError:
        if ticker!="CMG":raise
        interest=None;interest_status="not_used_owner_cash_proxy"
    if interest and interest["period_end"]!=flows["operating_cash_flow"]["period_end"]:
        if ticker!="YUM":raise ValueError(f"{ticker}: interest period mismatch")
        interest_status="latest_fiscal_year_carried_as_estimate"
    tax=.21
    try:tax=_normalized_tax_rate(normalizer)[0]
    except ValueError:pass
    interest_value=abs(float(interest["value"])) if interest else 0.
    current_cash=float(flows["operating_cash_flow"]["value"])-float(flows["capital_expenditures"]["value"]) if ticker=="CMG" else cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]),capital_expenditures=float(flows["capital_expenditures"]["value"]),spectrum_investment=0,interest_expense=interest_value,tax_rate=tax)
    revenue=float(flows["revenue"]["value"]);current_margin=current_cash/revenue
    try:
        annual_cash,annual_revenue,annual_sources=_annual_owner_cash(normalizer) if ticker=="CMG" and history_backed else _annual_cash_fcff(normalizer,spectrum_required=False,spectrum_floor=0,spectrum_source={},scope_adjustment=0)
        history=[cash/rev for cash,rev in zip(annual_cash,annual_revenue) if rev>0]
    except ValueError:annual_cash=annual_revenue=annual_sources=();history=[]
    pool=history[-3:]+[current_margin];margins=policy.margin_override or ((max(.005,min(pool)*.75),median(pool),max(pool)*1.15) if len(pool)>1 else (max(.005,current_margin*.65),current_margin,current_margin*1.25));growth=policy.growth;history_profile=None
    if history_backed:
        ttm_sources=[]
        for flow in (*flows.values(),interest or {}):
            if isinstance(flow,dict):ttm_sources.extend(dict(source) for source in flow.get("sources",[]) if isinstance(source,dict))
        history_profile=build_cash_fcff_history_profile(annual_cash_states=annual_sources,ttm_revenue=revenue,ttm_cash_fcff=current_cash,ttm_period_end=filing["period_end"],ttm_sources=ttm_sources,valuation_date="2026-08-14");cash_metric=history_profile.metric("cash_conversion_margin");growth_metric=history_profile.metric("revenue_growth")
        if history_profile.full_history and cash_metric is not None and ticker!="AMZN":margins=(cash_metric.low,cash_metric.base,cash_metric.high)
        if ticker in PASS_TICKERS and history_profile.full_history and growth_metric is not None:growth=tuple(max(-.10,min(.20,value)) for value in (growth_metric.low,growth_metric.base,growth_metric.high))
    margins=tuple(max(.001,margin-policy.working_capital_adjustment[index]) for index,margin in enumerate(margins));is_pass=ticker in PASS_TICKERS and history_backed and bool(history_profile and history_profile.full_history);reserve_rates=(0.,0.,0.) if is_pass else policy.reserve;rows=[]
    for index,name in enumerate(("bear","base","bull")):
        claims=assets*reserve_rates[index];raw=five_year_fcff_dcf(revenue=revenue,fcff_margin=margins[index],growth=growth[index],wacc=policy.wacc[index],terminal_growth=policy.terminal[index],cash_and_investments=policy.cash,debt=policy.debt,noncontrolling_interests=claims,shares=policy.shares[index]);value=max(0,float(raw["value_per_share"]));rows.append({"name":name,"conditional_value_per_share":value,"raw_value_per_share":raw["value_per_share"],"cash_conversion_margin":margins[index],"growth":growth[index],"wacc":policy.wacc[index],"terminal_growth":policy.terminal[index],"limited_liability_floor_applied":value==0 and raw["value_per_share"]<0})
    sources=_bridge_sources(ticker,structural,policy,assets);debt_unresolved=ticker in {"DECK","CMG"}
    if is_pass:
        sources.append(_source_proven_no_other_equity_claims(structural,period_end=policy.period))
        if debt_unresolved:sources.append(_source_proven_no_debt(structural,period_end=policy.period))
    else:sources.append({"source_kind":"governed_policy","field":"unresolved_debt_nci_and_other_claims" if debt_unresolved else "unresolved_nci_and_other_claims","period_end":policy.period,"reported_vs_estimated":"estimated_range","value_range":{"bear":assets*reserve_rates[0],"base":assets*reserve_rates[1],"bull":assets*reserve_rates[2]},"basis":"No current debt or NCI point is asserted; the 10%/5%/0% asset reserve explicitly covers unreported debt, finance leases, NCI, and other financing claims." if debt_unresolved else "No current reported NCI point is asserted; reserve covers unresolved claims."})
    scenario_range={"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]};history_public=history_profile.public_metadata() if history_profile else {}
    if history_profile and not is_pass:history_public.update({"normalization_basis":"company_history_with_material_event_override","assumption_source_mix":"reported_history_and_finsight_policy"})
    assumptions={**history_public,"cash_conversion_margin":margins,"growth":growth,"wacc":policy.wacc,"terminal_growth":policy.terminal,"shares":policy.shares,"unresolved_claims_reserve_rates":reserve_rates,"working_capital_adjustment_rates":policy.working_capital_adjustment,"equity_floor_basis":"limited-liability floor after negative residual" if scenario_range["low"]==0 else "not applied","calculator_calibration":"Calculator is calibrated to the baseline and does not rerun the private issuer model.","invalidation":policy.invalidation}
    if ticker=="BBY":assumptions["revenue_period_treatment"]="Current TTM revenue is reconstructed from FY plus current Q1 less prior Q1 using the issuer's current revenue concept."
    if ticker=="YUM":assumptions["interest_period_treatment"]="Latest reported FY interest is carried as an estimated TTM addback; it is not labeled current-period reported."
    if ticker=="CMG":assumptions["interest_period_treatment"]="No interest addback is used because the controlling filing contains no nonzero interest-bearing debt fact; owner-cash history uses OCF less capex."
    estimated=[row["value_range"] for row in sources if row.get("reported_vs_estimated")=="estimated_range"];totals={state:sum(float(row[state]) for row in estimated) for state in ("bear","base","bull")};accounting_impact=max(abs(totals["bear"]-totals["base"]),abs(totals["bull"]-totals["base"]))/max(scenario_range["base"]*policy.shares[1],1.) if estimated else 0.;reliability=assess_reliability(accounting_low=scenario_range["base"]-accounting_impact*scenario_range["base"],accounting_base=scenario_range["base"],accounting_high=scenario_range["base"]+accounting_impact*scenario_range["base"],scenario_low=scenario_range["low"],scenario_base=scenario_range["base"],scenario_high=scenario_range["high"],model_cap="Low" if not is_pass or not (history_profile and history_profile.full_history) else "High",source_cap="High",reasons=("CONDITIONAL_EVENT_MODEL",) if not is_pass else ());version=BATCH_06_HISTORY_REPAIR_VERSION if history_backed else BATCH_06_LAUNCH_FIRST_VERSION
    key_assumptions=((BaselineAssumption("company history",str(history_profile.history_years_used),AssumptionClassification.HISTORICALLY_DERIVED,"Source-linked company history supplies ordinary growth and cash-conversion assumptions."),) if history_profile else ())+ (BaselineAssumption("reported anchors",str({key:value["value"] for key,value in flows.items()}),AssumptionClassification.REPORTED,"Cutoff-safe filing facts; period exceptions are separately labeled."),BaselineAssumption("scenario policy",str(assumptions),AssumptionClassification.FINSIGHT_ASSUMPTION,"WACC, terminal growth, shares, and named dependencies remain governed assumptions."))
    def primary():
        if not is_pass:raise FallbackRejected("Primary source-bounded route requires issuer-specific refinements; conditional baseline selected.")
        return BaselineValuation(ticker=ticker,method=policy.method,method_version=version,low=scenario_range["low"],base=scenario_range["base"],high=scenario_range["high"],confidence=reliability.label,availability_type=AvailabilityType.AVAILABLE,key_assumptions=key_assumptions,warnings=(policy.warning,policy.invalidation),confidence_reasons=tuple(reliability.reasons),calculator_link=f"/api/us-valuations/{ticker}/calculator")
    def conditional():return BaselineValuation(ticker=ticker,method=policy.method,method_version=version,low=scenario_range["low"],base=scenario_range["base"],high=scenario_range["high"],confidence=reliability.label,availability_type=AvailabilityType.CONDITIONAL,key_assumptions=key_assumptions,warnings=(policy.warning,policy.invalidation),confidence_reasons=tuple(reliability.reasons),calculator_link=f"/api/us-valuations/{ticker}/calculator")
    strategies=((FallbackStage.NORMALIZED,policy.method,primary),) if is_pass else ((FallbackStage.PRIMARY_INTRINSIC,"primary_source_bounded",primary),(FallbackStage.CONDITIONAL,policy.method,conditional));baseline=run_fallback_ladder(ticker=ticker,strategies=strategies)
    return {"ticker":ticker,"method":policy.method,"model_version":version,"availability_type":baseline.availability_type.value,"scenario_rows":rows,"scenario_range":scenario_range,"reported_inputs":{"revenue_anchor":flows["revenue"]["value"],"revenue_period_end":flows["revenue"]["period_end"],"operating_cash_flow":flows["operating_cash_flow"]["value"],"operating_cash_flow_period_end":flows["operating_cash_flow"]["period_end"],"capital_expenditures":flows["capital_expenditures"]["value"],"interest_expense":None if interest is None else interest["value"],"interest_period_status":interest_status},"governed_assumptions":assumptions,"accounting_impact_ratio":accounting_impact,"history_reliability":reliability.as_dict(),"source_ledger":{"controlling_filing":filing,"flow_sources":flows,"interest_source":interest,"interest_period_status":interest_status,"annual_sources":annual_sources,"company_history_profile":history_profile.as_private_dict() if history_profile else None,"bridge_sources":sources,"bridge_reconciliation":{"cash_and_investments":policy.cash,"reported_debt_and_finance_leases":None if debt_unresolved else policy.debt,"model_debt_and_finance_leases":policy.debt,"debt_status":"source_proven_absent" if is_pass and debt_unresolved else "unresolved_covered_by_reserve" if debt_unresolved else "reported","reported_nci":None,"nci_status":"source_proven_absent" if is_pass else "unresolved_covered_by_reserve","unresolved_claims_reserve_rates":reserve_rates},"operating_lease_treatment":"Operating lease cash remains in OCF and is not subtracted again as debt. Finance leases are included once where reported.","structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":policy.warning,"baseline":baseline.as_private_dict()}


if set(P)!=set(BATCH_06_TICKERS):raise RuntimeError("Batch 06 policy denominator mismatch")
