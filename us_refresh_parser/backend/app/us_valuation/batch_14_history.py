"""History-backed practical baselines for controlled Universe Reset Batch 14."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .baseline import AssumptionClassification,AvailabilityType,BaselineAssumption,BaselineValuation
from .batch_02_practical_inputs import _normalizer,_normalized_tax_rate,cash_fcff_from_reported
from .batch_04_launch_first import _controlling,_duration,_point,_source_proven_no_other_equity_claims
from .batch_05_launch_first import _source_proven_no_debt
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _dimension_fact,_no_preferred
from .batch_14 import BATCH_14_TICKERS,BATCH_14_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION,CompanyHistoryProfile,build_cash_fcff_history_profile,summarize_history_metric
from .practical_models import EnterpriseCashFlowState,enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_14_HISTORY_VERSION="BATCH-14-HEALTH-CARE-HISTORY-1.0"
FORECAST_YEARS=8
PASS_TICKERS=frozenset({"IDXX"})


def _bounded_shares(weighted:float,current:float)->tuple[float,float,float]:
    return (weighted,(weighted+current)/2.,current)


@dataclass(frozen=True)
class Policy:
    method:str
    period:str
    cash:float
    debt:float
    claims:tuple[float,float,float]
    shares:tuple[float,float,float]
    growth:tuple[float,float,float]
    wacc:tuple[float,float,float]
    terminal:tuple[float,float,float]
    warning:str
    invalidation:str
    claim_formula:str


P={
    "TECH":Policy(
        "wilson_wolf_life_sciences_faded_fcff","2026-03-31",209_819_000.,200_000_000.,
        (1_000_000_000.,500_000_000.,0.),_bounded_shares(156_943_000.,156_568_751.),
        (-.02,.02,.05),(.115,.10,.09),(.01,.02,.025),
        "Conditional Low pre-merger life-sciences estimate. The pending $73-per-share cash merger is separate from intrinsic value; the Wilson Wolf forward contract can require up to $1B additional investment, while restructuring and the post-cutoff fiscal year remain material.",
        "Invalidate if the pending merger closes, terminates, or changes; or if Wilson Wolf milestones, fiscal-year cash, restructuring, debt, or diluted shares changes.",
        "Bear reserves the source-reported $1B Wilson Wolf additional investment, base reserves 50%, and bull reserves zero; acquired economic value is not invented. Contractual $73 merger consideration is reported separately, never probability-weighted into intrinsic value.",
    ),
    "HCA":Policy(
        "hospital_operations_faded_fcff","2026-06-30",1_013_000_000.,49_718_000_000.,
        (4_897_000_000.,4_165_000_000.,3_433_000_000.),_bounded_shares(224_731_000.,216_501_500.),
        (.01,.04,.06),(.105,.09,.08),(.01,.02,.025),
        "Conditional Low hospital-operations estimate. Debt and NCI reconcile, but the $1.464B professional-liability reserve lacks a complete source-linked payment roll-forward and materially changes the bridge.",
        "Invalidate if hospital cash conversion, debt, NCI, professional-liability cash, acquisitions, or diluted shares changes.",
        "$3.433B reported NCI plus 100%/50%/0% of the $1.464B professional-liability reserve in bear/base/bull. Operating leases remain post-rent operating items and are not deducted again.",
    ),
    "REGN":Policy(
        "biotechnology_cash_and_securities_faded_fcff","2026-06-30",17_645_000_000.,2_706_600_000.,
        (67_200_000.,)*3,_bounded_shares(106_800_000.,102_954_988.),
        (0.,.04,.07),(.11,.095,.085),(.01,.02,.025),
        "Conditional Low biotechnology estimate. Cash, complete marketable securities, debt/finance lease, contingent consideration, and dual-class shares reconcile, while collaboration revenue and acquired IPR&D remain material to recurring cash conversion.",
        "Invalidate if product cash, acquired IPR&D, marketable securities, financing, contingent consideration, or diluted shares changes.",
        "$67.2M H1 acquisition contingent consideration accrued but not yet paid is reserved once; collaboration and acquired-IPR&D effects remain in the Conditional cash range.",
    ),
    "IDXX":Policy(
        "veterinary_diagnostics_faded_fcff","2026-06-30",196_933_000.,449_864_000.,
        (2_300_000.,)*3,_bounded_shares(79_742_000.,78_781_116.),
        (.03,.07,.10),(.105,.09,.08),(.015,.0225,.025),
        "Source-bounded veterinary-diagnostics baseline. Current cash, debt, shares, and supplier-finance treatment reconcile across five comparable annual periods.",
        "Invalidate if diagnostics growth, cash conversion, debt, carried contingent consideration, supplier finance, or diluted shares changes.",
        "$2.3M prior asset-acquisition contingent consideration is retained as a conservative upper bound; supplier finance remains accounts payable/operating cash.",
    ),
    "BIIB":Policy(
        "post_apellis_biopharma_faded_fcff","2026-06-30",1_285_000_000.,7_290_300_000.,
        (397_800_000.,335_650_000.,273_500_000.),_bounded_shares(148_600_000.,147_753_998.),
        (-.05,0.,.04),(.12,.105,.095),(.005,.015,.025),
        "Conditional Low post-Apellis estimate. The $5.410B May acquisition, new term/revolver financing, product integration, contingent consideration, and appealed royalty judgment remain material.",
        "Invalidate if Apellis integration, acquired product cash, debt, Genentech judgment, contingent consideration, or diluted shares changes.",
        "$273.5M reported contingent consideration is reserved in all states; the $124.3M appealed Genentech amount is fully reserved in bear and half-reserved in base.",
    ),
    "VRTX":Policy(
        "pre_crinetics_biopharma_faded_fcff","2026-06-30",13_629_600_000.,0.,
        (79_600_000.,)*3,_bounded_shares(255_700_000.,253_460_924.),
        (.03,.07,.10),(.11,.095,.085),(.01,.02,.025),
        "Conditional Low pre-Crinetics standalone estimate. The signed July merger has approximately $10B expected equity consideration and financing that are not part of the June standalone cash-flow object.",
        "Invalidate if the Crinetics merger closes, terminates, or changes; or if standalone product cash, securities, contingent consideration, or shares changes.",
        "$79.6M reported contingent consideration is reserved once. Signed Crinetics consideration remains a separate pending event and is not probability-weighted into intrinsic value.",
    ),
    "INCY":Policy(
        "post_vega_biopharma_faded_fcff","2026-06-30",3_285_740_000.,32_679_000.,
        (852_000_000.,477_000_000.,102_000_000.),_bounded_shares(207_670_000.,202_697_746.),
        (0.,.05,.09),(.12,.105,.095),(.005,.015,.025),
        "Conditional Low post-Vega estimate. July acquisition cash is removed once, while current and post-period contingent consideration, Medicaid-rebate resolution, product concentration, and acquired pipeline cash remain material.",
        "Invalidate if Vega consideration, contingent milestones, rebate/legal treatment, product cash, finance leases, or diluted shares changes.",
        "$102M reported contingent consideration plus $750M Vega contingent consideration in bear; base reserves half the Vega amount; bull retains only the reported $102M. July $1.25B cash paid is removed once.",
    ),
    "GILD":Policy(
        "post_pipeline_acquisition_pharma_faded_fcff","2026-06-30",3_179_000_000.,26_246_000_000.,
        (2_760_000_000.,1_587_000_000.,637_000_000.),_bounded_shares(1_243_000_000.,1_239_955_155.),
        (-.02,.02,.05),(.115,.10,.09),(.005,.015,.025),
        "Conditional Low post-acquisition pharmaceutical estimate. Arcellx, Tubulis, and Ouro produced $12.15B acquired-IPR&D charges and $11.318B business-acquisition cash, making current TTM cash non-comparable.",
        "Invalidate if acquired pipeline outcomes, contingent milestones/CVR, debt, normalized cash conversion, product erosion, or diluted shares changes.",
        "Bear reserves $60M current business contingent consideration + $300M Arcellx CVR + $1.9B Tubulis maximum + $500M Ouro maximum; base halves unrecorded maxima; bull retains current/recorded $637M. Reported negative $84M NCI is not credited as a common-equity asset.",
    ),
    "BSX":Policy(
        "post_penumbra_medtech_faded_fcff","2026-06-30",539_000_000.,12_624_000_000.,
        (1_481_000_000.,1_431_000_000.,1_381_000_000.),_bounded_shares(1_484_900_000.,1_449_229_526.),
        (.03,.07,.10),(.11,.095,.085),(.01,.02,.025),
        "Conditional Low post-Penumbra medical-technology estimate. The January transaction, other 2026 acquisitions, contingent consideration, NCI, and July restructuring cash remain material to combined cash conversion.",
        "Invalidate if Penumbra integration, acquisition consideration, restructuring cash/savings, debt, NCI, contingent consideration, or diluted shares changes.",
        "$242M NCI + $257M contingent consideration + $282M current litigation reserve + $700M/$650M/$600M source-bounded July restructuring cash in bear/base/bull.",
    ),
    "MCK":Policy(
        "opioid_distribution_acquisition_faded_fcff","2026-06-30",4_911_000_000.,9_700_000_000.,
        (8_103_000_000.,)*3,_bounded_shares(119_200_000.,116_590_363.),
        (.03,.07,.10),(.105,.09,.08),(.01,.02,.025),
        "Conditional Low health-care distribution estimate. Opioid liabilities, redeemable/nonredeemable NCI, Core Ventures integration, restructuring, supplier economics, and high distribution growth remain material.",
        "Invalidate if opioid settlement cash, NCI/redemption value, acquisitions, restructuring, supplier economics, debt, securities, or diluted shares changes.",
        "Post-July state: $5.660B June opioid accrual and June cash are each reduced by the source-reported $496M July payment, leaving $5.164B claim; add $2.563B redeemable NCI + $0.376B nonredeemable NCI once. The $7.9B disclosed settlement amount is not added on top of the recorded reserve.",
    ),
}


SHARE_PERIODS={
    "TECH":("2025-07-01","2026-04-29"),"HCA":("2026-01-01","2026-07-24"),
    "REGN":("2026-01-01","2026-07-23"),"IDXX":("2026-01-01","2026-07-31"),
    "BIIB":("2026-01-01","2026-07-27"),"VRTX":("2026-01-01","2026-07-31"),
    "INCY":("2026-01-01","2026-07-21"),"GILD":("2026-01-01","2026-07-31"),
    "BSX":("2026-01-01","2026-07-30"),"MCK":("2026-04-01","2026-07-31"),
}


POINT_SPECS={
    "TECH":(("CashAndCashEquivalentsAtCarryingValue",209_819_000.),("LongTermDebtAndCapitalLeaseObligations",200_000_000.)),
    "HCA":(("CashAndCashEquivalentsAtCarryingValue",1_013_000_000.),("DebtLongtermAndShorttermCombinedAmount",49_718_000_000.),("MinorityInterest",3_433_000_000.),("ProfessionalLiabilityRisks",1_464_000_000.)),
    "REGN":(("CashAndCashEquivalentsAtCarryingValue",2_455_800_000.),("AvailableForSaleSecuritiesDebtSecurities",15_189_200_000.),("LongTermDebtNoncurrent",1_986_600_000.),("FinanceLeaseLiabilityCurrent",720_000_000.),("PreferredStockValue",0.)),
    "IDXX":(("CashAndCashEquivalentsAtCarryingValue",196_933_000.),("LongTermDebtCurrent",149_999_000.),("LongTermDebtNoncurrent",299_865_000.),("SupplierFinanceProgramObligation",7_014_000.)),
    "BIIB":(("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",1_285_000_000.),("LongTermDebt",7_290_300_000.),("SecuredDebtCurrent",800_000_000.),("BusinessCombinationContingentConsiderationLiabilityNoncurrent",273_500_000.),("PreferredStockValue",0.)),
    "VRTX":(("CashAndCashEquivalentsAtCarryingValue",6_143_500_000.),("AvailableForSaleSecuritiesDebtSecurities",7_486_100_000.),("BusinessCombinationContingentConsiderationLiability",79_600_000.),("PreferredStockValue",0.)),
    "INCY":(("CashAndCashEquivalentsAtCarryingValue",3_982_375_000.),("DebtSecuritiesAvailableForSaleExcludingAccruedInterest",553_365_000.),("FinanceLeaseLiabilityCurrent",4_259_000.),("FinanceLeaseLiabilityNoncurrent",28_420_000.),("BusinessCombinationContingentConsiderationLiabilityCurrent",38_811_000.),("BusinessCombinationContingentConsiderationLiabilityNoncurrent",63_189_000.),("PreferredStockValue",0.)),
    "GILD":(("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",3_179_000_000.),("LongTermDebt",26_246_000_000.),("DebtCurrent",2_414_000_000.),("MinorityInterest",-84_000_000.),("PreferredStockValue",0.)),
    "BSX":(("CashAndCashEquivalentsAtCarryingValue",539_000_000.),("DebtCurrent",1_709_000_000.),("LongTermDebtAndCapitalLeaseObligations",10_915_000_000.),("MinorityInterest",242_000_000.),("BusinessCombinationContingentConsiderationLiability",257_000_000.),("LossContingencyAccrualAtCarryingValue",282_000_000.),("PreferredStockValue",0.)),
    "MCK":(("CashAndCashEquivalentsAtCarryingValue",5_164_000_000.),("EquityAndDebtSecurities",243_000_000.),("DebtAndCapitalLeaseObligations",9_700_000_000.),("MinorityInterest",376_000_000.),("RedeemableNoncontrollingInterestEquityCommonCarryingAmount",2_563_000_000.),("LitigationReserveNoncurrent",5_058_000_000.),("PreferredStockValue",0.)),
}


def _share_point(st:dict[str,Any],*,expected:float,end:str,member:str|None=None)->dict[str,Any]:
    rows=[]
    for row in st["facts"]:
        if row.get("local_name")!="EntityCommonStockSharesOutstanding" or row.get("period_start") is not None or row.get("period_end")!=end or row.get("unit")!="xbrli:shares" or not isinstance(row.get("value"),(int,float)) or float(row["value"])!=expected:
            continue
        dimensions=row.get("dimensions") or []
        if member is None and dimensions:continue
        if member is not None and not any(member in str(value) for _,value in dimensions):continue
        rows.append(row)
    if not rows:raise ValueError(f"share fact {expected} absent for {end}/{member}")
    row=rows[0]
    return {"source_kind":"structural_xbrl","accession":st["source_accession"],"period_end":end,"concept":row.get("qname"),"dimensions":row.get("dimensions"),"unit":row.get("unit"),"value":expected,"reported_vs_estimated":"reported"}


def _share_sources(ticker:str,st:dict[str,Any],p:Policy)->list[dict[str,Any]]:
    start,current_end=SHARE_PERIODS[ticker]
    rows=[_duration(st,name="WeightedAverageNumberOfDilutedSharesOutstanding",expected=p.shares[0],period_start=start,period_end=p.period)]
    if ticker=="REGN":
        rows.extend((_share_point(st,expected=1_817_146.,end=current_end,member="CommonClassAMember"),_share_point(st,expected=101_137_842.,end=current_end,member="CommonStockMember")))
    else:rows.append(_share_point(st,expected=p.shares[2],end=current_end))
    return rows


def _tech_merger_source(event_root:Path)->dict[str,Any]:
    receipt=json.loads((Path(event_root)/"TECH/source-receipt.json").read_text());document=Path(event_root)/"TECH"/receipt["primary_document"]
    if receipt.get("schema_version")!="FINSIGHT-BATCH-14-EVENT-SOURCE-1" or receipt.get("accession")!="0001140361-26-032037" or receipt.get("filed")>BATCH_14_VALUATION_DATE or hashlib.sha256(document.read_bytes()).hexdigest()!=receipt.get("document_sha256"):raise ValueError("TECH merger-event source is invalid")
    return {"source_kind":"sec_proxy_filing","accession":receipt["accession"],"filed":receipt["filed"],"form":receipt["form"],"period_end":receipt["report_date"],"url":receipt["url"],"document_sha256":receipt["document_sha256"],"reported_terms":receipt["reported_terms"],"treatment":"Contractual $73 cash consideration remains separate from standalone intrinsic value while closing conditions remain pending.","reported_vs_estimated":"reported"}


def _event_sources(ticker:str,st:dict[str,Any],p:Policy,event_root:Path)->list[dict[str,Any]]:
    if ticker=="TECH":return [_dimension_fact(st,name="ForwardContractAdditionalInvestment",expected=1_000_000_000.,start=None,end=p.period,member="WilsonWolfCorporationMember"),_tech_merger_source(event_root)]
    if ticker=="HCA":return [_dimension_fact(st,name="PaymentsToAcquireBusinessesGross",expected=386_000_000.,start="2026-01-01",end=p.period,member="HealthcareEntityMember")]
    if ticker=="REGN":return [_structural_flow(st,name="AcquiredInProcessResearchAndDevelopment",start="2026-01-01",end=p.period,expected=228_900_000.),_structural_flow(st,name="AcquisitionsContingentConsiderationAccruedButNotYetPaid",start="2026-01-01",end=p.period,expected=67_200_000.)]
    if ticker=="IDXX":return [_dimension_fact(st,name="AssetAcquisitionContingentConsiderationLiability",expected=2_300_000.,start=None,end="2025-09-30",member="PrivatelyOwnedReferenceLaboratoryMember")]
    if ticker=="BIIB":return [_dimension_fact(st,name="BusinessCombinationConsiderationTransferred1",expected=5_410_100_000.,start="2026-05-14",end="2026-05-14",member="ApellisPharmaceuticalsInc.Member"),_dimension_fact(st,name="BusinessCombinationConsiderationTransferredLiabilitiesIncurred",expected=2_000_000_000.,start="2026-05-14",end="2026-05-14",member="ApellisPharmaceuticalsInc.Member"),_dimension_fact(st,name="LossContingencyDamagesSoughtValue",expected=124_300_000.,start="2025-11-01",end="2025-11-30",member="GenentechMember")]
    if ticker=="VRTX":return [_dimension_fact(st,name="BusinessCombinationPriceOfAcquisitionExpected",expected=10_000_000_000.,start="2026-07-06",end="2026-07-06",member="CrineticsMember"),_dimension_fact(st,name="DebtInstrumentFaceAmount",expected=4_500_000_000.,start=None,end="2026-07-30",member="A2026TermLoanMember")]
    if ticker=="INCY":return [_dimension_fact(st,name="PaymentsForAssetAcquisitions",expected=1_250_000_000.,start="2026-07-06",end="2026-07-06",member="VegaTherapeuticsInc.Member"),_dimension_fact(st,name="AssetAcquisitionContingentConsiderationLiability",expected=750_000_000.,start=None,end="2026-07-06",member="VegaTherapeuticsInc.Member"),_dimension_fact(st,name="LossContingencyLossInPeriod",expected=-246_000_000.,start="2026-04-01",end="2026-06-30",member="USCentersForMedicareAndMedicaidServicesMember")]
    if ticker=="GILD":return [_dimension_fact(st,name="AssetAcquisitionConsiderationTransferred",expected=6_400_000_000.,start="2026-04-01",end="2026-04-30",member="ArcellxIncMember"),_dimension_fact(st,name="AssetAcquisitionContingentValueRightAmount",expected=300_000_000.,start=None,end="2026-04-30",member="ArcellxIncMember"),_dimension_fact(st,name="AssetAcquisitionConsiderationTransferredContingentConsiderationRangeOfOutcomesMaximumAmount",expected=1_900_000_000.,start=None,end="2026-05-31",member="TubulisGmbHMember"),_dimension_fact(st,name="AssetAcquisitionConsiderationTransferredContingentConsiderationRangeOfOutcomesMaximumAmount",expected=500_000_000.,start=None,end="2026-06-30",member="OuroMedicinesLLCMember"),_structural_flow(st,name="PaymentsToAcquireBusinessesNetOfCashAcquired",start="2026-01-01",end=p.period,expected=11_318_000_000.),_structural_flow(st,name="ResearchAndDevelopmentAssetAcquiredOtherThanThroughBusinessCombinationWrittenOff",start="2026-01-01",end=p.period,expected=12_150_000_000.)]
    if ticker=="BSX":return [_dimension_fact(st,name="PaymentsToAcquireBusinessesNetOfCashAcquired",expected=14_500_000_000.,start="2026-01-15",end="2026-01-15",member="PenumbraInc.Member"),_dimension_fact(st,name="RestructuringAndRelatedCostExpectedCostCash",expected=600_000_000.,start=None,end="2026-07-21",member="MinimumMember"),_dimension_fact(st,name="RestructuringAndRelatedCostExpectedCostCash",expected=700_000_000.,start=None,end="2026-07-21",member="MaximumMember")]
    return [_dimension_fact(st,name="LossContingencyAccrualCarryingValueCurrent",expected=602_000_000.,start=None,end=p.period,member="NationalPrescriptionOpiateLitigationMember"),_dimension_fact(st,name="LitigationSettlementAmountAwardedToOtherParty",expected=7_900_000_000.,start="2026-04-01",end="2026-06-30",member="NationalPrescriptionOpiateLitigationMember"),_dimension_fact(st,name="PaymentsForLegalSettlements",expected=496_000_000.,start="2026-07-01",end="2026-07-31",member="NationalPrescriptionOpiateLitigationMember")]


def _bridge(ticker:str,st:dict[str,Any],p:Policy,event_root:Path)->list[dict[str,Any]]:
    rows=[_point(st,name=name,expected=value,period_end=p.period) for name,value in POINT_SPECS[ticker]]
    rows.extend(_share_sources(ticker,st,p));rows.extend(_event_sources(ticker,st,p,event_root))
    if ticker=="VRTX":rows.append(_source_proven_no_debt(st,period_end=p.period))
    if ticker in {"REGN","BIIB","VRTX","INCY"}:rows.append(_source_proven_no_other_equity_claims(st,period_end=p.period))
    if ticker=="TECH":rows.append(_source_proven_no_other_equity_claims(st,period_end=p.period))
    elif ticker not in {"REGN","BIIB","VRTX","INCY","GILD","BSX","MCK"}:rows.append(_no_preferred(st,p.period))
    return rows


def _history_profile(ticker:str,annual:list[dict[str,Any]],revenue:float,current:float,period:str,sources:list[dict[str,Any]])->tuple[CompanyHistoryProfile,list[str]]:
    profile=build_cash_fcff_history_profile(annual_cash_states=annual,ttm_revenue=revenue,ttm_cash_fcff=current,ttm_period_end=period,ttm_sources=sources,valuation_date=BATCH_14_VALUATION_DATE);cash=profile.metric("cash_conversion_margin");exclusions=[]
    if cash is not None and ticker in {"BIIB","VRTX","INCY","GILD"}:
        if ticker=="VRTX":
            observations=tuple(row for row in cash.observations if not (row.period_role=="annual" and row.period_end=="2024-12-31"));exclusions.append("2024 annual cash margin excluded because the Alpine asset-acquisition charge made the period non-comparable.")
        elif ticker=="GILD":
            observations=tuple(row for row in cash.observations if row.period_role=="annual");exclusions.append("Current TTM cash margin excluded because 2026 acquired-IPR&D addbacks and acquisition cash made it non-comparable.")
        elif ticker=="INCY":
            observations=tuple(row for row in cash.observations if row.period_role=="annual");exclusions.append("Current TTM cash margin excluded because the one-time $246M CMS/OPZELURA resolution made current revenue and cash non-comparable.")
        else:
            observations=tuple(row for row in cash.observations if row.period_role=="annual");exclusions.append("Current TTM cash margin excluded because the May Apellis acquisition created a partial-period combined cash object without filed pro-forma cash history.")
        adjusted=summarize_history_metric("cash_conversion_margin",observations)
        if adjusted is None:raise ValueError(f"{ticker}: adjusted history unavailable")
        profile=CompanyHistoryProfile(profile.policy_version,profile.lane,profile.valuation_date,profile.annual_periods,tuple(adjusted if metric.name=="cash_conversion_margin" else metric for metric in profile.metrics),profile.full_history,profile.assumption_source_mix)
    return profile,exclusions


def build_batch_14_history_result(*,ticker:str,source_root:Path,structural_root:Path,event_root:Path)->dict[str,Any]:
    if ticker not in P:raise ValueError(f"unexpected Batch 14 ticker {ticker}")
    packet=Path(source_root)/ticker;sub=json.loads((packet/"submissions.json").read_text());facts=json.loads((packet/"companyfacts.json").read_text());manifest=json.loads((packet/"source-manifest.json").read_text());st=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text());filing=_controlling(manifest,sub);p=P[ticker]
    if filing["period_end"]!=p.period or st["source_accession"]!=filing["accession"]:raise ValueError(f"{ticker}: controlling source mismatch")
    n=_normalizer(sub,facts);flows={name:n.ttm_flow(name) for name in ("revenue","operating_cash_flow","capital_expenditures","interest_expense")};tax_sources=[]
    try:tax,tax_rows=_normalized_tax_rate(n);tax_sources=list(tax_rows)
    except ValueError:tax=.21
    if tax<.05:tax=.21
    current=cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]),capital_expenditures=float(flows["capital_expenditures"]["value"]),spectrum_investment=0.,interest_expense=abs(float(flows["interest_expense"]["value"])),tax_rate=tax);annual=_annual_cash_with_losses(n)[2];sources=[dict(row) for flow in flows.values() for row in flow.get("sources",[]) if isinstance(row,dict)];revenue=float(flows["revenue"]["value"]);valuation_revenue=revenue;profile,exclusions=_history_profile(ticker,annual,revenue,current,p.period,sources);cash_metric=profile.metric("cash_conversion_margin")
    if not profile.full_history or cash_metric is None:raise ValueError(f"{ticker}: history insufficient")
    margins=tuple(max(.001,value) for value in (cash_metric.low,cash_metric.base,cash_metric.high));rows=[];traces={}
    for index,state_name in enumerate(("bear","base","bull")):
        state=EnterpriseCashFlowState(cash_fcff=valuation_revenue*margins[index],initial_growth=p.growth[index],terminal_growth=p.terminal[index],wacc=p.wacc[index],cash_and_investments=p.cash,interest_bearing_debt=p.debt,preferred_equity=0.,noncontrolling_interests=p.claims[index],diluted_shares=p.shares[index]);trace=enterprise_cash_flow_dcf(state,forecast_years=FORECAST_YEARS,allow_nonpositive_equity_trace=True);raw=float(trace["intrinsic_value_per_share"]);rows.append({"name":state_name,"conditional_value_per_share":max(0.,raw),"raw_value_per_share":raw,"starting_cash_fcff":state.cash_fcff,"cash_conversion_margin":margins[index],"growth":p.growth[index],"wacc":p.wacc[index],"terminal_growth":p.terminal[index],"cash_and_investments":p.cash,"debt_and_finance_leases":p.debt,"other_equity_claims":p.claims[index],"shares":p.shares[index],"limited_liability_floor_applied":raw<0});traces[state_name]=trace
    scenario={"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]}
    if not 0<=scenario["low"]<=scenario["base"]<=scenario["high"] or scenario["base"]<=0:raise ValueError(f"{ticker}: invalid range")
    is_pass=ticker in PASS_TICKERS;reason_codes=() if is_pass else ("CONDITIONAL_EVENT_MODEL","SPECIALIST_MODEL_UNCERTAINTY");rel=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="High" if is_pass else "Low",source_cap="High",reasons=reason_codes);public_history=profile.public_metadata();public_history.update({"normalization_basis":"company_history_with_material_event_override" if exclusions or not is_pass else profile.normalization_basis,"assumption_source_mix":"reported_history_and_finsight_policy" if exclusions or not is_pass else profile.assumption_source_mix});assumptions={**public_history,"forecast_years":FORECAST_YEARS,"cash_conversion_margin":margins,"growth":p.growth,"wacc":p.wacc,"terminal_growth":p.terminal,"shares":p.shares,"normalization_exclusions":tuple(exclusions),"equity_floor_basis":"limited-liability floor after negative bear residual" if scenario["low"]==0 else "not applied","calculator_calibration":"Calculator is calibrated to the faded-cash base; private bridge and events remain fixed.","invalidation":p.invalidation};availability=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL;baseline=BaselineValuation(ticker=ticker,method=p.method,method_version=BATCH_14_HISTORY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence=rel.label,availability_type=availability,key_assumptions=(BaselineAssumption("company history",str(profile.history_years_used),AssumptionClassification.HISTORICALLY_DERIVED,"Source-linked annual and comparable TTM cash history supplies the cash-conversion range."),BaselineAssumption("faded health-care states",str({"growth":p.growth,"wacc":p.wacc,"terminal":p.terminal}),AssumptionClassification.FINSIGHT_ASSUMPTION,"Growth fades over eight years to a terminal rate no higher than 2.5%.")),warnings=(p.warning,p.invalidation),confidence_reasons=tuple(rel.reasons),calculator_link=f"/api/us-valuations/{ticker}/calculator");bridge=_bridge(ticker,st,p,Path(event_root))
    return {"ticker":ticker,"method":p.method,"model_version":BATCH_14_HISTORY_VERSION,"availability_type":"available" if is_pass else "conditional_estimate","scenario_rows":rows,"scenario_range":scenario,"reported_inputs":{"ttm_revenue":flows["revenue"]["value"],"valuation_revenue":valuation_revenue,"ttm_operating_cash_flow":flows["operating_cash_flow"]["value"],"ttm_capex":flows["capital_expenditures"]["value"],"ttm_interest":flows["interest_expense"]["value"],"tax_rate":tax,"ttm_cash_fcff":current},"governed_assumptions":assumptions,"history_reliability":rel.as_dict(),"source_ledger":{"controlling_filing":filing,"flow_sources":flows,"tax_rate_sources":tax_sources,"company_history_profile":profile.as_private_dict(),"bridge_sources":bridge,"bridge_reconciliation":{"cash_and_investments":p.cash,"debt_and_finance_leases":p.debt,"other_equity_claims":p.claims,"other_equity_claim_formula":p.claim_formula,"shares":p.shares,"history_normalization_exclusions":exclusions,"revenue_adjustment":None,"negative_nci_treatment":"GILD's reported negative $84M NCI is retained as evidence but conservatively not credited to common equity." if ticker=="GILD" else None,"operating_liability_treatment":"Operating leases, supplier finance, ordinary recurring settlement/professional-liability cash, and royalties remain operating when already represented in cash conversion; separately ranged reserves are deducted only where the payment history is incomplete."},"model_trace":{"forecast_years":FORECAST_YEARS,"states":traces},"structural_top_level_period_diagnostic":{"value":st.get("period_end"),"used_for_selection":False}},"warning":p.warning,"baseline":baseline.as_private_dict()}


if set(P)!=set(BATCH_14_TICKERS):raise RuntimeError("Batch 14 denominator mismatch")
