"""Launch-first Conditional Low baselines for controlled Batch 04."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from .baseline import (
    AssumptionClassification, AvailabilityType, BaselineAssumption,
    BaselineValuation, FallbackRejected, FallbackStage, run_fallback_ladder,
)
from .batch_02_conditional_estimates import five_year_fcff_dcf
from .batch_02_practical_inputs import (
    _annual_cash_fcff, _normalizer, _normalized_tax_rate,
    cash_fcff_from_reported,
)
from .batch_04 import BATCH_04_MANIFEST, BATCH_04_TICKERS, BATCH_04_VALUATION_DATE
from .history import (
    HISTORY_POLICY_VERSION,
    CompanyHistoryProfile,
    HistoryObservation,
    build_cash_fcff_history_profile,
    summarize_history_metric,
)
from .reliability import assess_reliability


BATCH_04_LAUNCH_FIRST_VERSION = "BATCH-04-LAUNCH-FIRST-1.0"
BATCH_04_HISTORY_SHADOW_VERSION = "BATCH-04-HISTORY-SHADOW-1.0"
PASS_TICKERS = frozenset({"MCD", "TJX", "HD", "ROST"})


@dataclass(frozen=True)
class Policy:
    method: str
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal_growth: tuple[float, float, float]
    shares: tuple[float, float, float]
    period_end: str
    cash: float
    debt: float
    nci: float
    assets: float
    warning: str
    invalidation: str


_POLICIES = {
    "GPC": Policy("working_capital_normalized_cash_fcff", (-.02,.02,.05), (.11,.095,.085), (0,.015,.02), (144_917_850.,141_467_425.,138_017_000.), "2026-06-30", 559_118_000., 4_979_122_000., 17_777_000., 21_058_293_000., "Conditional Low estimate. Acquisition and working-capital normalization, leases, and unresolved claims materially affect the range.", "Invalidate when acquisition claims or normalized working capital leave the governed range."),
    "HAS": Policy("post_impairment_normalized_cash_fcff", (-.03,0,.04), (.12,.105,.095), (0,.01,.02), (150_360_000.,146_780_000.,143_200_000.), "2026-06-28", 880_500_000., 3_556_900_000., 25_100_000., 6_037_200_000., "Conditional Low estimate. Entertainment changes, impairments, restructuring, and licensing cash conversion can move value materially.", "Invalidate when post-divestiture cash or impairment claims leave the governed range."),
    "LOW": Policy("home_retail_normalized_cash_fcff", (-.03,0,.03), (.10,.09,.08), (0,.015,.02), (588_000_000.,574_000_000.,560_000_000.), "2026-05-01", 1_491_000_000., 37_941_000_000., 0., 54_941_000_000., "Conditional Low estimate. Housing-cycle cash conversion and unresolved claims are ranged conservatively.", "Invalidate when current debt, leases, securities, or cash conversion leave the governed range."),
    "MCD": Policy("franchise_lease_normalized_cash_fcff", (0,.04,.07), (.095,.085,.075), (.01,.02,.025), (747_915_000.,730_107_500.,712_300_000.), "2026-06-30", 822_000_000., 39_900_000_000., 0., 59_920_000_000., "Conditional Low estimate. Franchise and lease economics are operating cash items and are not deducted twice as debt.", "Invalidate when franchise, lessor/lessee cash, debt, or share evidence leaves the governed range."),
    "TJX": Policy("off_price_normalized_cash_fcff", (0,.04,.07), (.10,.09,.08), (.01,.02,.025), (1_176_000_000.,1_148_000_000.,1_120_000_000.), "2026-05-02", 5_580_000_000., 2_870_000_000., 0., 36_158_000_000., "Conditional Low estimate. Alternate revenue mapping and off-price inventory normalization create material uncertainty.", "Invalidate when validated TTM revenue, inventory, debt, leases, or shares leave the governed range."),
    "NKE": Policy("transition_normalized_cash_fcff", (-.03,.02,.06), (.11,.095,.085), (0,.015,.02), (1_555_050_000.,1_518_025_000.,1_481_000_000.), "2026-05-31", 7_563_000_000., 7_942_000_000., 0., 38_410_000_000., "Conditional Low estimate. Wholesale/DTC mix, inventory, China, FX, and margin recovery are governed transition assumptions.", "Invalidate when filed transition economics or inventory cash conversion leave the governed range."),
    "HD": Policy("housing_cycle_integration_cash_fcff", (-.02,.02,.05), (.10,.09,.08), (0,.015,.02), (1_045_800_000.,1_020_900_000.,996_000_000.), "2026-05-03", 1_601_000_000., 53_509_000_000., 0., 107_904_000_000., "Conditional Low estimate. SRS integration and the housing/repair cycle are reflected through broad cash states.", "Invalidate when integration claims, debt, leases, or cash conversion leave the governed range."),
    "ROST": Policy("off_price_normalized_cash_fcff", (0,.04,.07), (.10,.09,.08), (.01,.02,.025), (337_292_550.,329_261_775.,321_231_000.), "2026-05-02", 4_130_980_000., 1_018_187_000., 0., 15_554_572_000., "Conditional Low estimate. Off-price inventory, leases, investments, and claim reserves are governed rather than assumed absent.", "Invalidate when debt, leases, investments, shares, or cash conversion leave the governed range."),
    "MGM": Policy("casino_cycle_jv_normalized_cash_fcff", (-.04,.02,.06), (.12,.105,.095), (0,.01,.02), (271_243_350.,264_785_175.,258_327_000.), "2026-06-30", 2_547_380_000., 6_315_842_000., 862_283_000., 39_848_326_000., "Conditional Low estimate. Casino-cycle, property capex, MGM China/JV/NCI, leases, and digital economics can move value materially.", "Invalidate when casino/JV cash, debt, lease, or NCI evidence leaves the governed range."),
}


def _point(structural: Mapping[str, Any], *, name: str, expected: float, period_end: str) -> dict[str, Any]:
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") is None and row.get("period_end") == period_end and not row.get("dimensions") and isinstance(row.get("value"),(int,float)) and float(row["value"]) == expected]
    if not rows:
        raise ValueError(f"{name}: expected {expected} absent for {period_end}")
    row = rows[0]
    return {"source_kind":"structural_xbrl","accession":structural["source_accession"],"period_end":period_end,"concept":row.get("qname"),"unit":"USD","value":expected,"reported_vs_estimated":"reported"}


def _duration(structural: Mapping[str, Any], *, name: str, expected: float, period_start: str, period_end: str) -> dict[str, Any]:
    rows=[row for row in structural["facts"] if row.get("local_name")==name and row.get("period_start")==period_start and row.get("period_end")==period_end and not row.get("dimensions") and isinstance(row.get("value"),(int,float)) and float(row["value"])==expected]
    if not rows: raise ValueError(f"{name}: expected duration {expected} absent")
    row=rows[0]
    return {"source_kind":"structural_xbrl","accession":structural["source_accession"],"period_start":period_start,"period_end":period_end,"concept":row.get("qname"),"unit":"shares","value":expected,"reported_vs_estimated":"reported"}


def _companyfacts_duration(facts: Mapping[str, Any], *, concept: str, accession: str, start: str, end: str, expected: float) -> dict[str, Any]:
    rows=facts["facts"]["us-gaap"][concept]["units"]["USD"]
    matches=[row for row in rows if row.get("accn")==accession and row.get("start")==start and row.get("end")==end and isinstance(row.get("val"),(int,float)) and float(row["val"])==expected]
    if not matches: raise ValueError(f"{concept}: expected {expected} absent for {accession} {start}/{end}")
    row=matches[0]
    return {"source_kind":"companyfacts","concept":f"us-gaap:{concept}","accession":accession,"period_start":start,"period_end":end,"filed":row.get("filed"),"form":row.get("form"),"unit":"USD","value":expected,"reported_vs_estimated":"reported"}


def _reconstructed_flow(*, field: str, components: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    fiscal_year,current,prior=components
    return {"value":fiscal_year["value"]+current["value"]-prior["value"],"period_end":current["period_end"],"method":"latest_fy_plus_current_ytd_minus_prior_ytd","sources":list(components),"field":field}


def _tjx_revenue(facts: Mapping[str, Any]) -> dict[str, Any]:
    concept="RevenueFromContractWithCustomerIncludingAssessedTax"
    components=(
        _companyfacts_duration(facts,concept=concept,accession="0000109198-26-000008",start="2025-02-02",end="2026-01-31",expected=60_372_000_000.),
        _companyfacts_duration(facts,concept=concept,accession="0000109198-26-000034",start="2026-02-01",end="2026-05-02",expected=14_323_000_000.),
        _companyfacts_duration(facts,concept=concept,accession="0000109198-26-000034",start="2025-02-02",end="2025-05-03",expected=13_111_000_000.),
    )
    return _reconstructed_flow(field="revenue",components=components)


def _rost_interest(facts: Mapping[str, Any]) -> dict[str, Any]:
    sources=[];total=0.
    for concept,values in (
        ("InterestExpenseLongTermDebt",(49_136_000.,10_333_000.,17_463_000.)),
        ("InterestExpenseOther",(1_554_000.,346_000.,400_000.)),
    ):
        components=(
            _companyfacts_duration(facts,concept=concept,accession="0000745732-26-000006",start="2025-02-02",end="2026-01-31",expected=values[0]),
            _companyfacts_duration(facts,concept=concept,accession="0000745732-26-000032",start="2026-02-01",end="2026-05-02",expected=values[1]),
            _companyfacts_duration(facts,concept=concept,accession="0000745732-26-000032",start="2025-02-02",end="2025-05-03",expected=values[2]),
        )
        row=_reconstructed_flow(field="interest_expense",components=components);total+=row["value"];sources.extend(row["sources"])
    return {"value":total,"period_end":"2026-05-02","method":"sum_of_reconstructed_interest_components","sources":sources,"field":"interest_expense"}


def _source_proven_no_other_equity_claims(structural: Mapping[str, Any], *, period_end: str) -> dict[str, Any]:
    claim_names=("MinorityInterest","NonredeemableNoncontrollingInterest","RedeemableNoncontrollingInterestEquityCarryingAmount","PreferredStockValue","PreferredStockValueOutstanding")
    nonzero=[row for row in structural["facts"] if row.get("local_name") in claim_names and row.get("period_start") is None and row.get("period_end")==period_end and not row.get("dimensions") and isinstance(row.get("value"),(int,float)) and float(row["value"])!=0]
    if nonzero: raise ValueError("other equity claims are present in the controlling filing")
    return {"source_kind":"controlling_filing_structure","accession":structural["source_accession"],"period_end":period_end,"field":"preferred_equity_and_nci","reported_vs_estimated":"source_proven_absent","checked_concepts":list(claim_names),"basis":"The controlling filing contains no nonzero preferred-equity, redeemable-NCI, or minority-interest point fact for the reported balance sheet."}


def _member_point(structural: Mapping[str, Any], *, name: str, expected: float, period_end: str, member: str) -> dict[str, Any]:
    rows=[row for row in structural["facts"] if row.get("local_name")==name and row.get("period_start") is None and row.get("period_end")==period_end and any(member in str(value) for _,value in (row.get("dimensions") or [])) and isinstance(row.get("value"),(int,float)) and float(row["value"])==expected]
    if not rows: raise ValueError(f"{name}/{member}: expected {expected} absent")
    row=rows[0]
    return {"source_kind":"structural_xbrl","accession":structural["source_accession"],"period_end":period_end,"concept":row.get("qname"),"member":member,"unit":"USD","value":expected,"reported_vs_estimated":"reported"}


def _bridge_sources(ticker: str, structural: Mapping[str, Any], policy: Policy) -> list[dict[str, Any]]:
    p=lambda name,value:_point(structural,name=name,expected=value,period_end=policy.period_end)
    specs={
        "GPC": [("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",559_118_000.),("ShortTermBorrowings",752_474_000.),("LongTermDebtCurrent",250_000_000.),("LongTermDebtNoncurrent",3_976_648_000.),("MinorityInterest",17_777_000.)],
        "HAS": [("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",880_500_000.),("DebtInstrumentCarryingAmount",3_556_900_000.),("MinorityInterest",25_100_000.)],
        "LOW": [("CashAndCashEquivalentsAtCarryingValue",786_000_000.),("ShortTermInvestments",458_000_000.),("LongTermInvestments",247_000_000.),("ShortTermBorrowings",380_000_000.),("LongTermDebtAndCapitalLeaseObligationsCurrent",810_000_000.),("LongTermDebtAndCapitalLeaseObligations",36_751_000_000.)],
        "MCD": [("CashAndCashEquivalentsAtCarryingValue",822_000_000.),("DebtInstrumentCarryingAmount",39_900_000_000.),("OperatingLeaseLiabilityCurrent",690_000_000.),("OperatingLeaseLiabilityNoncurrent",14_039_000_000.),("PreferredStockValue",0.),("InvestmentsInAffiliatesSubsidiariesAssociatesAndJointVentures",2_896_000_000.)],
        "TJX": [("CashAndCashEquivalentsAtCarryingValue",5_580_000_000.),("LongTermDebtCurrent",999_000_000.),("LongTermDebtNoncurrent",1_871_000_000.)],
        "NKE": [("CashAndCashEquivalentsAtCarryingValue",7_563_000_000.),("LongTermDebt",7_942_000_000.)],
        "HD": [("CashAndCashEquivalentsAtCarryingValue",1_601_000_000.),("CommercialPaper",3_503_000_000.),("LongTermDebtAndCapitalLeaseObligationsCurrent",5_178_000_000.),("LongTermDebtAndCapitalLeaseObligations",44_828_000_000.)],
        "ROST": [("CashAndCashEquivalentsAtCarryingValue",4_130_980_000.),("LongTermDebt",1_018_187_000.)],
        "MGM": [("CashAndCashEquivalentsAtCarryingValue",2_547_380_000.),("DebtInstrumentCarryingAmount",6_103_186_000.),("FinanceLeaseLiability",212_656_000.),("MinorityInterest",853_879_000.),("RedeemableNoncontrollingInterestEquityCarryingAmount",8_404_000.),("OperatingLeaseLiability",23_877_591_000.)],
    }
    rows=[p(name,value) for name,value in specs[ticker]]
    starts={"GPC":"2026-01-01","HAS":"2025-12-29","LOW":"2026-01-31","TJX":"2026-02-01","NKE":"2025-06-01","HD":"2026-02-02","ROST":"2026-02-01","MGM":"2026-01-01"}
    if ticker=="MCD":
        rows.append({"source_kind":"companyfacts_scaled_disclosure","accession":structural["source_accession"],"period_start":"2026-01-01","period_end":"2026-06-30","concept":"us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding","reported_value_millions":712.3,"scale":1_000_000,"value":712_300_000.,"unit":"shares","reported_vs_estimated":"reported_scaled"})
    else:
        rows.append(_duration(structural,name="WeightedAverageNumberOfDilutedSharesOutstanding",expected=policy.shares[2],period_start=starts[ticker],period_end=policy.period_end))
    return rows


def _controlling(source_manifest: Mapping[str, Any], submissions: Mapping[str, Any]) -> dict[str, str]:
    filing = max(source_manifest["eligible_filings"], key=lambda row:(row["filed"],row["accession"]))
    index = submissions["filings"]["recent"]["accessionNumber"].index(filing["accession"])
    return {**filing,"period_end":submissions["filings"]["recent"]["reportDate"][index]}


def _direct_annual_rows(
    facts: Mapping[str, Any],
    *,
    concepts: tuple[str, ...],
    period_end: str,
) -> tuple[float, tuple[dict[str, Any], ...]] | None:
    selected=[]
    for concept in concepts:
        rows=facts.get("facts",{}).get("us-gaap",{}).get(concept,{}).get("units",{}).get("USD",[])
        candidates=[row for row in rows if row.get("end")==period_end and row.get("fp")=="FY" and row.get("form") in {"10-K","10-K/A"} and isinstance(row.get("val"),(int,float)) and isinstance(row.get("filed"),str) and row["filed"]<=BATCH_04_VALUATION_DATE]
        if not candidates:return None
        row=max(candidates,key=lambda value:(value.get("filed",""),value.get("form","").endswith("/A"),value.get("accn","")))
        selected.append({"field":concept,"concept":f"us-gaap:{concept}","accession":row.get("accn"),"period_start":row.get("start"),"period_end":row.get("end"),"filed":row.get("filed"),"form":row.get("form"),"unit":"USD","value":float(row["val"]),"reported_vs_estimated":"reported"})
    return sum(row["value"] for row in selected),tuple(selected)


def _batch_04_annual_cash_history(normalizer, facts: Mapping[str, Any], ticker: str):
    standard=_annual_cash_fcff(normalizer,spectrum_required=False,spectrum_floor=0,spectrum_source={},scope_adjustment=0)
    if len(standard[0])>=3:return standard
    cash_rows=[];revenue_rows=[];source_rows=[]
    for operating_cash in normalizer.annual_series("operating_cash_flow",5):
        capex=normalizer.annual_at_end("capital_expenditures",operating_cash.end);pretax=normalizer.annual_at_end("pretax_income",operating_cash.end);tax=normalizer.annual_at_end("income_tax",operating_cash.end)
        if capex is None:continue
        if ticker=="TJX":revenue_direct=_direct_annual_rows(facts,concepts=("RevenueFromContractWithCustomerIncludingAssessedTax",),period_end=operating_cash.end);revenue_value,revenue_sources=revenue_direct if revenue_direct else (None,())
        else:
            revenue=normalizer.annual_at_end("revenue",operating_cash.end);revenue_value=float(revenue.value) if revenue else None;revenue_sources=(revenue.as_dict(),) if revenue else ()
        if ticker=="ROST":interest_direct=_direct_annual_rows(facts,concepts=("InterestExpenseLongTermDebt","InterestExpenseOther"),period_end=operating_cash.end);interest_value,interest_sources=interest_direct if interest_direct else (None,())
        else:
            interest=normalizer.annual_at_end("interest_expense",operating_cash.end);interest_value=abs(float(interest.value)) if interest else None;interest_sources=(interest.as_dict(),) if interest else ()
        if revenue_value is None or revenue_value<=0 or interest_value is None:continue
        tax_rate=max(0.,min(.30,float(tax.value)/float(pretax.value))) if pretax is not None and tax is not None and pretax.value>0 else .21
        cash_fcff=cash_fcff_from_reported(operating_cash_flow=float(operating_cash.value),capital_expenditures=float(capex.value),spectrum_investment=0.,interest_expense=float(interest_value),tax_rate=tax_rate)
        if cash_fcff<=0:continue
        revenue_source={"field":"revenue","value":float(revenue_value),"period_end":operating_cash.end,"fiscal_year":operating_cash.fiscal_year,"sources":list(revenue_sources)}
        interest_source={"field":"interest_expense","value":float(interest_value),"period_end":operating_cash.end,"fiscal_year":operating_cash.fiscal_year,"sources":list(interest_sources)}
        cash_rows.append(cash_fcff);revenue_rows.append(float(revenue_value));source_rows.append({"period_end":operating_cash.end,"operating_cash_flow":operating_cash.as_dict(),"capital_expenditures":capex.as_dict(),"spectrum_investment":{"state":"not_applicable","value":0.},"scope_adjustment":0.,"interest_expense":interest_source,"pretax_income":pretax.as_dict() if pretax else None,"income_tax":tax.as_dict() if tax else None,"revenue":revenue_source,"cash_fcff":cash_fcff})
    return tuple(cash_rows),tuple(revenue_rows),tuple(source_rows)


def _standard_result(
    ticker: str,
    *,
    source_root: Path,
    structural_root: Path,
    history_backed: bool = False,
) -> dict[str, Any]:
    policy = _POLICIES[ticker]
    packet = Path(source_root)/ticker
    submissions=json.loads((packet/"submissions.json").read_text()); facts=json.loads((packet/"companyfacts.json").read_text()); manifest=json.loads((packet/"source-manifest.json").read_text())
    structural=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text()); filing=_controlling(manifest,submissions)
    if structural["source_accession"] != filing["accession"] or filing["period_end"] != policy.period_end:
        raise ValueError(f"{ticker}: controlling source mismatch")
    normalizer=_normalizer(submissions,facts)
    flows={field:normalizer.ttm_flow(field) for field in ("revenue","operating_cash_flow","capital_expenditures","interest_expense")}
    if ticker=="TJX": flows["revenue"]=_tjx_revenue(facts)
    if ticker=="ROST": flows["interest_expense"]=_rost_interest(facts)
    tax,_tax_sources=_normalized_tax_rate(normalizer)
    current_cash=cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]),capital_expenditures=float(flows["capital_expenditures"]["value"]),spectrum_investment=0,interest_expense=abs(float(flows["interest_expense"]["value"])),tax_rate=tax)
    current_margin=current_cash/float(flows["revenue"]["value"])
    try:
        annual_cash,annual_revenue,annual_sources=(_batch_04_annual_cash_history(normalizer,facts,ticker) if history_backed else _annual_cash_fcff(normalizer,spectrum_required=False,spectrum_floor=0,spectrum_source={},scope_adjustment=0))
        history=[cash/revenue for cash,revenue in zip(annual_cash,annual_revenue) if revenue>0]
    except ValueError:
        annual_cash=annual_revenue=annual_sources=()
        history=[]
    pool=history[-3:]+[current_margin]
    margins=(max(.005,min(pool)*.75),median(pool),max(pool)*1.15) if len(pool)>1 else (max(.005,current_margin*.65),current_margin,current_margin*1.25)
    growth=policy.growth
    history_profile=None
    if history_backed:
        ttm_sources=[]
        for flow in flows.values():
            if isinstance(flow, Mapping):
                ttm_sources.extend(
                    dict(source)
                    for source in flow.get("sources", [])
                    if isinstance(source, Mapping)
                )
        history_profile=build_cash_fcff_history_profile(
            annual_cash_states=annual_sources,
            ttm_revenue=float(flows["revenue"]["value"]),
            ttm_cash_fcff=current_cash,
            ttm_period_end=filing["period_end"],
            ttm_sources=ttm_sources,
            valuation_date=BATCH_04_VALUATION_DATE,
        )
        cash_metric=history_profile.metric("cash_conversion_margin")
        growth_metric=history_profile.metric("revenue_growth")
        if history_profile.full_history and cash_metric is not None:
            margins=(cash_metric.low,cash_metric.base,cash_metric.high)
        if (
            ticker in PASS_TICKERS
            and history_profile.full_history
            and growth_metric is not None
        ):
            growth=tuple(max(-.10,min(.20,value)) for value in (growth_metric.low,growth_metric.base,growth_metric.high))
    reported_sources=[_point(structural,name="Assets",expected=policy.assets,period_end=policy.period_end),*_bridge_sources(ticker,structural,policy)]
    nci_is_reported=ticker in {"GPC","HAS","MGM"}
    source_proven_absent=ticker in PASS_TICKERS
    reserve_rates=(0.,0.,0.) if source_proven_absent else (.02,.01,0.)
    if source_proven_absent:
        reported_sources.append(_source_proven_no_other_equity_claims(structural,period_end=policy.period_end))
    elif not nci_is_reported:
        reported_sources.append({"source_kind":"governed_policy","field":"unresolved_nci_and_other_claims","period_end":policy.period_end,"reported_vs_estimated":"estimated_range","value_range":{"bear":policy.assets*.02,"base":policy.assets*.01,"bull":0.0},"basis":"No current reported NCI point is asserted; the asset-based unresolved-claims reserve covers the uncertainty."})
    scenario_rows=[]
    for index,name in enumerate(("bear","base","bull")):
        claims=policy.nci+policy.assets*reserve_rates[index]
        raw=five_year_fcff_dcf(revenue=float(flows["revenue"]["value"]),fcff_margin=margins[index],growth=growth[index],wacc=policy.wacc[index],terminal_growth=policy.terminal_growth[index],cash_and_investments=policy.cash,debt=policy.debt,noncontrolling_interests=claims,shares=policy.shares[index])
        value=max(0.0,float(raw["value_per_share"]))
        scenario_rows.append({"name":name,"conditional_value_per_share":value,"raw_value_per_share":raw["value_per_share"],"cash_conversion_margin":margins[index],"growth":growth[index],"wacc":policy.wacc[index],"terminal_growth":policy.terminal_growth[index],"limited_liability_floor_applied":value==0 and raw["value_per_share"]<0})
    lease_treatment=("Operating lease expense is already reflected in operating cash flow and is not subtracted again as debt." if ticker in {"MCD","MGM"} else "No separate operating-lease bridge subtraction is applied; operating lease cash remains in operating cash flow.")
    treatments={"MCD":"The $2.896B equity-method investment remains inside the consolidated owner-cash object; it is not added again to the bridge, avoiding double counting of affiliate distributions.","HD":"The current TTM cash history includes the controlled SRS operations; no separate pro-forma acquisition adjustment is added.","TJX":"Revenue is reconstructed from current FY/Q1 facts using the issuer's current revenue concept.","ROST":"Interest is reconstructed from current long-term-debt and other-interest facts."}
    history_public=history_profile.public_metadata() if history_profile else {}
    if history_profile and ticker not in PASS_TICKERS:
        history_public.update({"normalization_basis":"company_history_with_material_event_override","assumption_source_mix":"reported_history_and_finsight_policy"})
    return {"ticker":ticker,"method":policy.method,"scenario_rows":scenario_rows,"scenario_range":{"low":scenario_rows[0]["conditional_value_per_share"],"base":scenario_rows[1]["conditional_value_per_share"],"high":scenario_rows[2]["conditional_value_per_share"]},"reported_inputs":{"ttm_revenue":flows["revenue"]["value"],"ttm_operating_cash_flow":flows["operating_cash_flow"]["value"],"ttm_capex":flows["capital_expenditures"]["value"]},"governed_assumptions":{**history_public,"cash_conversion_margin":margins,"growth":growth,"wacc":policy.wacc,"terminal_growth":policy.terminal_growth,"shares":policy.shares,"unresolved_claims_reserve_rates":reserve_rates,"equity_floor_basis":"limited-liability floor after a negative bear residual" if scenario_rows[0]["limited_liability_floor_applied"] else "not applied","calculator_calibration":"Calculator is calibrated to the published baseline and does not rerun this issuer-specific source model.","invalidation":policy.invalidation},"source_ledger":{"controlling_filing":filing,"flow_sources":flows,"bridge_sources":reported_sources,"annual_sources":annual_sources,"company_history_profile":history_profile.as_private_dict() if history_profile else None,"bridge_reconciliation":{"cash_and_investments":policy.cash,"interest_bearing_debt":policy.debt,"reported_nci":policy.nci if nci_is_reported else None,"nci_status":"reported" if nci_is_reported else "source_proven_absent" if source_proven_absent else "unresolved_covered_by_asset_reserve","unresolved_claims_reserve_rates":reserve_rates},"pass_repair_treatment":treatments.get(ticker),"operating_lease_treatment":lease_treatment,"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False,"basis":"Controlling submissions report date and fact-row periods govern; malformed parser summary period is diagnostic only."}},"warning":policy.warning}


def _ford_result(*, source_root: Path, structural_root: Path, history_backed: bool = False) -> dict[str, Any]:
    ticker="F";packet=Path(source_root)/ticker
    submissions=json.loads((packet/"submissions.json").read_text());facts=json.loads((packet/"companyfacts.json").read_text());manifest=json.loads((packet/"source-manifest.json").read_text());structural=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text());filing=_controlling(manifest,submissions)
    normalizer=_normalizer(submissions,facts)
    pretax=normalizer.ttm_flow("pretax_income");tax=normalizer.ttm_flow("income_tax");revenue=normalizer.ttm_flow("revenue");current_net=float(pretax["value"])-float(tax["value"])
    annual=[];annual_observations=[]
    for row in normalizer.annual_series("pretax_income",5):
        tax_row=normalizer.annual_at_end("income_tax",row.end);net=float(row.value)-(float(tax_row.value) if tax_row else 0.0);annual.append(net)
        if tax_row is not None:
            annual_observations.append(HistoryObservation(period_role="annual",period_end=row.end,fiscal_year=row.fiscal_year,value=net,unit="USD",formula="annual pretax income - annual income tax",sources=(row.as_dict(),tax_row.as_dict())))
    positive=sorted(value for value in annual if value>0)
    earnings=(1_000_000_000.,median(positive),max(positive)*.75)
    history_profile=None
    if history_backed:
        metric=summarize_history_metric("normalized_common_earnings",annual_observations)
        periods=tuple(row.period_end for row in annual_observations[-5:])
        full=len(set(periods))>=3
        history_profile=CompanyHistoryProfile(policy_version=HISTORY_POLICY_VERSION,lane="normalized_equity_earnings",valuation_date=BATCH_04_VALUATION_DATE,annual_periods=periods,metrics=(metric,) if metric else (),full_history=full,assumption_source_mix="reported_and_company_history" if full else "reported_history_and_finsight_policy")
        if full and metric is not None:earnings=(metric.low,metric.base,metric.high)
    multiples=(5.,8.,11.);shares=(4_300_000_000.,4_069_000_000.,3_987_000_000.)
    rows=[{"name":name,"conditional_value_per_share":earnings[i]*multiples[i]/shares[i],"normalized_common_earnings":earnings[i],"earnings_multiple":multiples[i],"shares":shares[i],"limited_liability_floor_applied":False} for i,name in enumerate(("bear","base","bull"))]
    for scenario in rows:
        raw_value=scenario["conditional_value_per_share"]
        scenario["raw_value_per_share"]=raw_value
        if raw_value < 0:
            scenario["conditional_value_per_share"]=0.0
            scenario["limited_liability_floor_applied"]=True
    margins=tuple(value/float(revenue["value"]) for value in earnings)
    ford_sources=[_point(structural,name="StockholdersEquity",expected=35_719_000_000.,period_end="2026-06-30"),_member_point(structural,name="NotesReceivableNet",expected=104_869_000_000.,period_end="2026-06-30",member="FordCreditMember"),_member_point(structural,name="DebtLongtermAndShorttermCombinedAmount",expected=137_348_000_000.,period_end="2026-06-30",member="FordCreditMember"),_member_point(structural,name="DebtLongtermAndShorttermCombinedAmount",expected=23_619_000_000.,period_end="2026-06-30",member="CompanyExcludingFordCreditMember")]
    history_public=history_profile.public_metadata() if history_profile else {}
    if history_profile:
        history_public.update({"normalization_basis":"company_history_with_material_event_override","assumption_source_mix":"reported_history_and_finsight_policy"})
    return {"ticker":"F","method":"ford_normalized_equity_earnings_baseline","scenario_rows":rows,"scenario_range":{"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]},"reported_inputs":{"ttm_revenue":revenue["value"],"ttm_pretax_income":pretax["value"],"ttm_income_tax":tax["value"],"ttm_common_earnings_proxy":current_net},"governed_assumptions":{**history_public,"cash_conversion_margin":margins,"normalized_common_earnings":earnings,"earnings_multiples":multiples,"shares":shares,"route_is_captive_finance_sotp":False,"ev_debt_bridge_applied":False,"calculator_calibration":"Calculator is calibrated to the published baseline and does not rerun the normalized-equity-earnings model.","invalidation":"Invalidate when Ford Credit equity/funding, warranty/pension claims, or normalized common earnings leave the governed range."},"source_ledger":{"controlling_filing":filing,"revenue_source":revenue,"pretax_source":pretax,"tax_source":tax,"annual_common_earnings":annual,"company_history_profile":history_profile.as_private_dict() if history_profile else None,"ford_credit_context_sources":ford_sources,"ford_credit_treatment":"Conditional normalized consolidated equity-earnings baseline, not a Ford Credit SOTP. The EV debt bridge is deliberately not used because finance funding and receivables remain inside the consolidated equity object.","structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":"Conditional Low normalized-equity-earnings estimate. It is not a Ford Credit SOTP; auto-cycle/EV transition, warranty, pension, and finance economics can move value materially."}


def build_batch_04_launch_first_result(*,ticker:str,source_root:Path,structural_root:Path,history_backed:bool=False) -> dict[str,Any]:
    if ticker not in BATCH_04_TICKERS: raise KeyError(ticker)
    result=_ford_result(source_root=source_root,structural_root=structural_root,history_backed=history_backed) if ticker=="F" else _standard_result(ticker,source_root=source_root,structural_root=structural_root,history_backed=history_backed)
    scenario=result["scenario_range"]
    assumptions=(BaselineAssumption("reported operating anchor",str(result["reported_inputs"]),AssumptionClassification.REPORTED,"Controlling SEC filing and cutoff-safe history."),BaselineAssumption("company history",str(result["governed_assumptions"].get("history_years_used")),AssumptionClassification.HISTORICALLY_DERIVED,"Source-linked company history supplies ordinary growth and normalized operating assumptions."),BaselineAssumption("governed scenario policy",str(result["governed_assumptions"]),AssumptionClassification.FINSIGHT_ASSUMPTION,"WACC, terminal growth, shares, and named issuer-specific dependencies remain governed assumptions.")) if history_backed else (BaselineAssumption("reported operating anchor",str(result["reported_inputs"]),AssumptionClassification.REPORTED,"Controlling SEC filing and cutoff-safe history."),BaselineAssumption("governed scenario policy",str(result["governed_assumptions"]),AssumptionClassification.FINSIGHT_ASSUMPTION,"Launch-first broad bear/base/bull decision baseline."))
    is_conditional=ticker not in PASS_TICKERS
    profile=result["source_ledger"].get("company_history_profile")
    history_full=bool(profile and profile.get("full_history"))
    if history_backed:
        reliability=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="Low" if is_conditional or not history_full else "High",source_cap="High",reasons=("CONDITIONAL_EVENT_MODEL",) if is_conditional else (("INSUFFICIENT_COMPANY_HISTORY",) if not history_full else ()))
        confidence=reliability.label
        version=BATCH_04_HISTORY_SHADOW_VERSION
    else:
        reliability=None;confidence="Low";version=BATCH_04_LAUNCH_FIRST_VERSION
    def primary():
        if ticker not in PASS_TICKERS: raise FallbackRejected("Primary source-bounded route requires model-specific refinements; launch-first conditional route selected.")
        return BaselineValuation(ticker=ticker,method=result["method"],method_version=version,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence=confidence,availability_type=AvailabilityType.AVAILABLE,key_assumptions=assumptions,warnings=(result["warning"],result["governed_assumptions"]["invalidation"]),confidence_reasons=tuple(reliability.reasons) if reliability else ("CONSOLIDATED_MODEL_FALLBACK","SPECIALIST_MODEL_UNCERTAINTY"),calculator_link=f"/api/us-valuations/{ticker}/calculator")
    def conditional(): return BaselineValuation(ticker=ticker,method=result["method"],method_version=version,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence=confidence,availability_type=AvailabilityType.CONDITIONAL,key_assumptions=assumptions,warnings=(result["warning"],result["governed_assumptions"]["invalidation"]),confidence_reasons=tuple(reliability.reasons) if reliability else ("CONDITIONAL_EVENT_MODEL","SPECIALIST_MODEL_UNCERTAINTY"),calculator_link=f"/api/us-valuations/{ticker}/calculator")
    strategies=((FallbackStage.NORMALIZED,result["method"],primary),) if ticker in PASS_TICKERS else ((FallbackStage.PRIMARY_INTRINSIC,"primary_source_bounded",primary),(FallbackStage.CONDITIONAL,result["method"],conditional))
    baseline=run_fallback_ladder(ticker=ticker,strategies=strategies)
    return {**result,"model_version":version,"availability_type":baseline.availability_type.value,"baseline":baseline.as_private_dict(),"history_reliability":reliability.as_dict() if reliability else None}
