"""History-backed practical baselines for controlled Universe Reset Batch 26."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _companyfacts_duration, _controlling, _duration, _point
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _no_preferred
from .batch_16_history import _history_source, _share_point
from .batch_26 import BATCH_26_TICKERS, BATCH_26_VALUATION_DATE
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_26_HISTORY_VERSION = "BATCH-26-TECHNOLOGY-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"SWKS", "ADI", "AMAT", "GLW", "HPQ", "MSI"})
CONDITIONAL_TICKERS = frozenset({"AMD", "INTC", "IBM", "APH"})
WITHHELD_TICKERS = frozenset()
EQUITY_EARNINGS_TICKERS = frozenset({"IBM"})


def _shares(weighted: float, current: float) -> tuple[float, float, float]:
    high = max(weighted, current)
    low = min(weighted, current)
    return high, (high + low) / 2.0, low


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: float
    claims: float
    shares: tuple[float, float, float]
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str
    claim_formula: str


P = {
    "AMD": Policy("post_zt_ai_semiconductor_faded_fcff", "2026-06-27", 16_512_000_000.0, 3_226_000_000.0, 0.0, _shares(1_655_000_000.0, 1_632_475_042.0), (-.05, .03, .08), (.11, .095, .085), (0.0, .015, .025), "Conditional Low post-ZT AI-semiconductor baseline. Five-year cash history is finite, while ZT integration, the manufacturing divestiture, acquired AI-system cash conversion, and R&D intensity remain material.", "Invalidate if ZT/divestiture scope, AI revenue or cash conversion, R&D/capex, securities, debt, or diluted shares changes materially.", "$5.086B cash plus $11.426B complete current/noncurrent AFS debt securities; $3.226B total debt. The $361M ZT contingent consideration was source-proven settled in October 2025, so the current claim is zero rather than missing. R&D remains expensed inside operating cash and is not added back."),
    "SWKS": Policy("rf_semiconductor_cycle_faded_fcff", "2026-07-03", 813_800_000.0, 496_900_000.0, 0.0, _shares(150_800_000.0, 150_472_782.0), (-.06, -.01, .04), (.11, .095, .085), (0.0, .01, .02), "Source-bounded RF-semiconductor cycle baseline. Five-year cash history, current cash/securities, debt, preferred absence, restructuring, and shares reconcile; weaker demand is handled through the range.", "Invalidate if customer concentration, RF demand, cash conversion, restructuring, debt, securities, or diluted shares changes materially.", "$790M cash plus $23.8M current/noncurrent marketable securities; $496.9M long-term debt."),
    "ADI": Policy("analog_semiconductor_cycle_faded_fcff", "2026-05-02", 3_439_308_000.0, 8_134_651_000.0, 0.0, _shares(491_057_000.0, 487_087_040.0), (-.04, .02, .06), (.105, .09, .08), (.005, .015, .025), "Source-bounded analog-semiconductor baseline. Five-year post-Maxim cash history and current securities, debt, preferred absence, restructuring, and shares reconcile.", "Invalidate if analog demand, cash conversion, R&D/capex, debt, securities, restructuring, or diluted shares changes materially.", "$2.436916B cash plus $1.002392B current AFS securities; $899.227M current and $7.235424B noncurrent debt."),
    "AMAT": Policy("semiconductor_equipment_cycle_faded_fcff", "2026-04-26", 13_383_000_000.0, 6_455_000_000.0, 0.0, _shares(799_000_000.0, 793_959_430.0), (-.05, .02, .06), (.105, .09, .08), (.005, .015, .025), "Source-bounded semiconductor-equipment baseline. Five-year cash history and the complete cash/investment total, debt, warranty reserve, capex, and shares reconcile; equipment-cycle and export demand are ranged.", "Invalidate if equipment demand, export restrictions, capex/R&D, investments, debt, warranties, or diluted shares changes materially.", "$13.383B reported cash/cash-equivalents/investments fair value counted once; $1.199B current and $5.256B noncurrent debt."),
    "GLW": Policy("components_cycle_faded_fcff", "2026-06-30", 2_504_000_000.0, 8_424_000_000.0, 723_000_000.0, (879_388_331.0, 878_194_165.5, 877_000_000.0), (-.04, .03, .07), (.11, .095, .085), (0.0, .01, .02), "Source-bounded components-cycle baseline. Four-year cash history, structurally repaired current Q2 capex, debt/NCI/contingent consideration, and a complete 0–18M NVIDIA warrant dilution sensitivity reconcile; the warrant ceiling is about 2.1% of current shares.", "Invalidate if the NVIDIA agreement/warrants, Springboard capex, segment cash conversion, contingent consideration, debt/NCI, or diluted shares changes materially.", "$668M current debt + $7.756B precise noncurrent debt/lease fact; $567M NCI + $156M contingent consideration. The share range includes up to 18M reported warrants; $500M proceeds are already in current cash and are not added again."),
    "HPQ": Policy("mature_hardware_print_cycle_faded_fcff", "2026-04-30", 3_828_000_000.0, 9_700_000_000.0, 0.0, _shares(928_000_000.0, 914_522_690.0), (-.05, -.01, .03), (.11, .095, .085), (0.0, .01, .02), "Source-bounded mature hardware and print baseline. Five-year cash history, current cash/securities, debt, restructuring cash, warranties, supplier-finance operating treatment, and shares reconcile; negative book equity is not substituted for operating value.", "Invalidate if PC/print demand, cash conversion, restructuring, supplier-finance scope, debt, warranties, or diluted shares changes materially.", "$3.703B cash plus $125M AFS/equity securities; $9.7B debt/capital leases. Supplier finance remains in operating working capital and is not deducted twice."),
    "INTC": Policy("foundry_transformation_cash_conversion_faded_fcff", "2026-06-27", 35_037_000_000.0, 50_537_000_000.0, 15_601_000_000.0, _shares(5_108_000_000.0, 5_044_000_000.0), (-.03, .02, .06), (.115, .10, .09), (0.0, .01, .02), "Conditional Low foundry-transformation baseline. Current revenue and post-capex cash are finite, while four prior annual cash periods were negative and fab capex, foundry execution, impairments, government support, and large NCI remain load-bearing.", "Invalidate if foundry/fab capex, government support, restructuring/impairment, debt, securities, NCI, or diluted shares changes materially.", "$12.874B cash plus $22.163B complete AFS debt securities; $50.537B current/noncurrent debt; $15.601B NCI. Raw negative bear equity is retained before a limited-liability floor."),
    "MSI": Policy("public_safety_communications_faded_fcff", "2026-07-04", 1_010_000_000.0, 9_033_000_000.0, 16_000_000.0, _shares(167_600_000.0, 165_493_788.0), (-.02, .04, .07), (.105, .09, .08), (.005, .015, .025), "Source-bounded public-safety communications baseline. Five-year cash history, current cash/investments, debt, NCI, ordinary acquisitions, supplier finance, operating leases, and shares reconcile.", "Invalidate if recurring public-safety/service cash, acquisitions, debt, NCI, supplier finance, leases, or diluted shares changes materially.", "$710M cash plus $300M long-term investments; $9.033B debt; $16M NCI. Operating leases remain inside cash conversion."),
    "APH": Policy("post_ccs_acquisition_components_faded_fcff", "2026-06-30", 5_419_100_000.0, 18_811_300_000.0, 130_500_000.0, _shares(1_289_400_000.0, 1_232_983_457.0), (-.04, .04, .08), (.11, .095, .085), (0.0, .01, .02), "Conditional Low post-CCS electronic-components baseline. Current cash is finite, while $10.684B of first-half acquisition cash, $7.008B acquired goodwill, debt funding, integration, acquired conversion, NCI, and dilution remain material.", "Invalidate if CCS integration/acquired cash conversion, purchase accounting, debt, securities, NCI, or diluted shares changes materially.", "$5.4191B cash plus short-term investments counted once; $18.8113B debt/capital leases; $121.5M NCI + $9M redeemable NCI."),
}


POINT_SPECS = {
    "AMD": (("CashAndCashEquivalentsAtCarryingValue", 5_086_000_000.0), ("AvailableForSaleSecuritiesDebtSecurities", 11_426_000_000.0), ("DebtLongtermAndShorttermCombinedAmount", 3_226_000_000.0)),
    "SWKS": (("CashAndCashEquivalentsAtCarryingValue", 790_000_000.0), ("MarketableSecuritiesCurrent", 9_200_000.0), ("MarketableSecuritiesNoncurrent", 14_600_000.0), ("LongTermDebt", 496_900_000.0), ("PreferredStockValue", 0.0)),
    "ADI": (("CashAndCashEquivalentsAtCarryingValue", 2_436_916_000.0), ("AvailableForSaleSecuritiesDebtSecuritiesCurrent", 1_002_392_000.0), ("LongTermDebtCurrent", 899_227_000.0), ("LongTermDebtNoncurrent", 7_235_424_000.0), ("PreferredStockValue", 0.0)),
    "AMAT": (("CashCashEquivalentsAndInvestmentsEstimatedFairValue", 13_383_000_000.0), ("LongTermDebtCurrent", 1_199_000_000.0), ("LongTermDebtNoncurrent", 5_256_000_000.0)),
    "GLW": (("CashAndCashEquivalentsAtCarryingValue", 2_504_000_000.0), ("DebtCurrent", 668_000_000.0), ("LongTermDebtAndCapitalLeaseObligations", 7_756_000_000.0), ("MinorityInterest", 567_000_000.0), ("BusinessCombinationContingentConsiderationLiabilityNoncurrent", 156_000_000.0)),
    "HPQ": (("CashAndCashEquivalentsAtCarryingValue", 3_703_000_000.0), ("DebtSecuritiesAvailableForSaleExcludingAccruedInterestAndEquitySecuritiesFVNI", 125_000_000.0), ("DebtAndCapitalLeaseObligations", 9_700_000_000.0), ("PreferredStockValue", 0.0)),
    "INTC": (("CashAndCashEquivalentsAtCarryingValue", 12_874_000_000.0), ("AvailableForSaleSecuritiesDebtSecurities", 22_163_000_000.0), ("DebtCurrent", 1_988_000_000.0), ("LongTermDebtNoncurrent", 48_549_000_000.0), ("MinorityInterest", 15_601_000_000.0)),
    "MSI": (("CashAndCashEquivalentsAtCarryingValue", 710_000_000.0), ("LongTermInvestments", 300_000_000.0), ("DebtInstrumentCarryingAmount", 9_033_000_000.0), ("MinorityInterest", 16_000_000.0), ("PreferredStockValue", 0.0)),
    "APH": (("CashCashEquivalentsAndShortTermInvestments", 5_419_100_000.0), ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities", 18_811_300_000.0), ("MinorityInterest", 121_500_000.0), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 9_000_000.0)),
}

SHARE_STARTS = {"AMD":"2025-12-28","SWKS":"2025-10-04","ADI":"2025-11-02","AMAT":"2025-10-27","GLW":"2026-01-01","HPQ":"2025-11-01","INTC":"2025-12-28","MSI":"2026-01-01","APH":"2026-01-01"}
WEIGHTED_SHARES = {"AMD":1_655_000_000.0,"SWKS":150_800_000.0,"ADI":491_057_000.0,"AMAT":799_000_000.0,"GLW":877_000_000.0,"HPQ":928_000_000.0,"INTC":5_108_000_000.0,"MSI":167_600_000.0,"APH":1_289_400_000.0}
CURRENT_SHARES = {"AMD":1_632_475_042.0,"SWKS":150_472_782.0,"ADI":487_087_040.0,"AMAT":793_959_430.0,"GLW":861_388_331.0,"HPQ":914_522_690.0,"INTC":5_044_000_000.0,"MSI":165_493_788.0,"APH":1_232_983_457.0}
SHARE_ENDS = {"AMD":"2026-07-29","SWKS":"2026-07-23","ADI":"2026-05-02","AMAT":"2026-04-26","GLW":"2026-07-24","HPQ":"2026-05-20","INTC":"2026-07-17","MSI":"2026-07-31","APH":"2026-07-28"}
MARGIN_OVERRIDES = {"INTC": (.03, .07, .12)}
GROWTH_OVERRIDES = {"INTC": P["INTC"].growth}


def _fact(structural: dict[str, Any], *, name: str, expected: float, start: str | None, end: str) -> dict[str, Any]:
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") == start and row.get("period_end") == end and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and float(row["value"]) == expected]
    if not rows:
        raise ValueError(f"{name}: expected {expected} absent for {start}/{end}")
    row = rows[0]
    return {"source_kind":"structural_xbrl","accession":structural["source_accession"],"filed":structural.get("filed_date"),"period_start":start,"period_end":end,"concept":row.get("qname"),"unit":row.get("unit"),"value":expected,"reported_vs_estimated":"reported"}


def _fact_with_dimensions(structural: dict[str, Any], *, name: str, expected: float, start: str | None, end: str) -> dict[str, Any]:
    rows = [row for row in structural["facts"] if row.get("local_name") == name and row.get("period_start") == start and row.get("period_end") == end and isinstance(row.get("value"), (int, float)) and float(row["value"]) == expected]
    if not rows:
        raise ValueError(f"{name}: expected dimensional {expected} absent for {start}/{end}")
    row = rows[0]
    return {"source_kind":"structural_xbrl","accession":structural["source_accession"],"filed":structural.get("filed_date"),"period_start":start,"period_end":end,"concept":row.get("qname"),"unit":row.get("unit"),"value":expected,"dimensions":row.get("dimensions",[]),"reported_vs_estimated":"reported"}


def _no_preferred_excluding_redeemable_nci(structural: dict[str, Any], period: str) -> dict[str, Any]:
    names = ("PreferredStockValue", "PreferredStockValueOutstanding", "PreferredStockNoParValue", "PreferredStockSharesIssued")
    rows = [row for row in structural["facts"] if row.get("local_name") in names and row.get("period_start") is None and row.get("period_end") == period and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and float(row["value"]) != 0.0]
    if rows:
        raise ValueError("unreconciled preferred equity")
    return {"source_kind":"controlling_filing_structure","accession":structural["source_accession"],"period_end":period,"field":"preferred_equity","reported_vs_estimated":"source_proven_absent_or_zero","checked_concepts":list(names),"separate_temporary_equity_treatment":"Redeemable NCI is recorded separately in the common-equity claim bridge."}


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [_point(structural, name=name, expected=value, period_end=policy.period) for name, value in POINT_SPECS[ticker]]
    rows.extend((_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=WEIGHTED_SHARES[ticker], period_start=SHARE_STARTS[ticker], period_end=policy.period), _share_point(structural, expected=CURRENT_SHARES[ticker], end=SHARE_ENDS[ticker])))
    rows.append(_no_preferred_excluding_redeemable_nci(structural, policy.period) if ticker == "APH" else _no_preferred(structural, policy.period))
    if ticker == "GLW":
        rows.append({"source_kind":"governed_dilution_sensitivity","accession":structural["source_accession"],"period_end":"2026-05-06","reported_warrant_shares":18_000_000.0,"shares":policy.shares,"reported_vs_estimated":"reported_warrants_plus_governed_sensitivity"})
    return rows


def _glw_normalizer(submissions: dict[str, Any], facts: dict[str, Any]):
    config = copy.deepcopy(load_concept_config())
    config["fields"]["capital_expenditures"]["concepts"] = ["PaymentsForCapitalImprovements"]
    return _normalizer(submissions, facts, concept_config=config)


def _glw_flows(normalizer, structural: dict[str, Any]) -> dict[str, Any]:
    values = {"revenue":("Revenues",8_649_000_000.0,7_314_000_000.0),"operating_cash_flow":("NetCashProvidedByUsedInOperatingActivities",2_079_000_000.0,859_000_000.0),"capital_expenditures":("PaymentsForCapitalImprovements",754_000_000.0,516_000_000.0),"interest_expense":("InterestExpenseNonoperating",186_000_000.0,165_000_000.0)}
    flows = {}
    for field, (concept, current_value, prior_value) in values.items():
        base = normalizer.ttm_flow(field)
        annual = dict(base["sources"][0])
        current = _structural_flow(structural, name=concept, start="2026-01-01", end="2026-06-30", expected=current_value)
        prior = _structural_flow(structural, name=concept, start="2025-01-01", end="2025-06-30", expected=prior_value)
        flows[field] = {"field":field,"value":float(annual["value"]) + current_value - prior_value,"period_end":"2026-06-30","method":"latest_fy_plus_structural_current_ytd_minus_prior_ytd","sources":[annual,current,prior],"current_ytd":current,"prior_ytd":prior}
    return flows


def _events(ticker: str, filing: dict[str, Any], structural: dict[str, Any], policy: Policy) -> list[dict[str, Any]]:
    rows = [{"source_kind":"controlling_filing_narrative","accession":filing["accession"],"filed":filing["filed"],"period_end":filing["period_end"],"matter":policy.warning,"reported_vs_estimated":"reported_narrative"}]
    specs = {
        "AMD": (("PaymentsToAcquireBusinessesNetOfCashAcquired",129_000_000.0,"2025-12-28","2026-06-27"),("ProceedsFromDivestitureOfBusinessesNetOfCashDivested",1_400_000_000.0,"2025-12-28","2026-06-27"),("ResearchAndDevelopmentExpense",4_925_000_000.0,"2025-12-28","2026-06-27")),
        "GLW": (("ProceedsFromIssuanceOfWarrants",500_000_000.0,"2026-01-01","2026-06-30"),("ClassOfWarrantOrRightNumberOfSecuritiesCalledByWarrantsOrRights",18_000_000.0,None,"2026-05-06")),
        "HPQ": (("SupplierFinanceProgramObligation",9_100_000_000.0,None,"2026-04-30"),("RestructuringCosts",491_000_000.0,"2025-11-01","2026-04-30")),
        "INTC": (("AssetImpairmentCharges",3_967_000_000.0,"2025-12-28","2026-06-27"),),
        "IBM": (("PaymentsToAcquireBusinessesNetOfCashAcquired",10_480_000_000.0,"2026-01-01","2026-06-30"),("FinancingReceivableAndNetInvestmentInLeaseBeforeAllowanceForCreditLossAndFee",14_526_000_000.0,None,"2026-06-30")),
        "APH": (("PaymentsToAcquireBusinessesNetOfCashAcquired",10_684_000_000.0,"2026-01-01","2026-06-30"),("GoodwillAcquiredDuringPeriod",7_007_700_000.0,"2026-01-01","2026-06-30")),
    }
    rows.extend(_fact(structural, name=name, expected=value, start=start, end=end) for name, value, start, end in specs.get(ticker, ()))
    if ticker == "AMD":
        rows.extend((_fact_with_dimensions(structural,name="BusinessCombinationConsiderationTransferred1",expected=4_409_000_000.0,start="2025-12-28",end="2026-06-27"),_fact_with_dimensions(structural,name="BusinessCombinationConsiderationTransferredEquityInterestsIssuedAndIssuable",expected=860_000_000.0,start="2025-03-31",end="2025-03-31"),_fact_with_dimensions(structural,name="BusinessCombinationContingentConsiderationLiability",expected=361_000_000.0,start=None,end="2025-03-31"),_fact_with_dimensions(structural,name="DisposalGroupIncludingDiscontinuedOperationConsideration",expected=2_400_000_000.0,start=None,end="2026-06-27"),_fact(structural,name="DisposalGroupIncludingDiscontinuedOperationConsiderationShares",expected=1_151_052.0,start=None,end="2026-06-27"),{"source_kind":"controlling_filing_narrative","accession":filing["accession"],"filed":filing["filed"],"period_end":filing["period_end"],"matter":"ZT contingent consideration settlement","reported_terms":{"historical_contingent_consideration_usd":361_000_000.0,"settled":"2025-10","current_claim_usd":0.0},"reported_vs_estimated":"source_proven_settled_not_missing_zero"}))
    if ticker == "GLW":
        rows.extend((_fact(structural,name="AdjustmentsToAdditionalPaidInCapitalWarrantIssued",expected=796_000_000.0,start="2026-04-01",end="2026-06-30"),_fact_with_dimensions(structural,name="ClassOfWarrantOrRightExercisePriceOfWarrantsOrRights1",expected=180.0,start=None,end="2026-05-06")))
    return rows


def _operating_result(ticker: str, filing: dict[str, Any], structural: dict[str, Any], submissions: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    policy = P[ticker]
    normalizer = _glw_normalizer(submissions, facts) if ticker == "GLW" else _normalizer(submissions, facts)
    flows = _glw_flows(normalizer, structural) if ticker == "GLW" else {name: normalizer.ttm_flow(name) for name in ("revenue","operating_cash_flow","capital_expenditures","interest_expense")}
    tax_fallback=False
    try:
        tax_rate, tax_sources = _normalized_tax_rate(normalizer)
    except ValueError:
        tax_rate, tax_sources, tax_fallback = .21, (), True
    if not .05 <= tax_rate <= .30:
        tax_rate, tax_fallback = .21, True
    current = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0.0, interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
    annual = _annual_cash_with_losses(normalizer)[2]
    sources = [dict(row) for flow in flows.values() for row in flow.get("sources", [])]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=current, ttm_period_end=policy.period, ttm_sources=sources, valuation_date=BATCH_26_VALUATION_DATE)
    cash_metric, growth_metric = profile.metric("cash_conversion_margin"), profile.metric("revenue_growth")
    if cash_metric is None or growth_metric is None or not profile.full_history:
        raise ValueError(f"{ticker}: history unavailable")
    margins = MARGIN_OVERRIDES.get(ticker, (cash_metric.low, cash_metric.base, cash_metric.high))
    margins = tuple(max(.001, float(value)) for value in margins)
    growth = GROWTH_OVERRIDES.get(ticker, (max(-.10,min(policy.growth[0],growth_metric.low)),max(-.08,min(policy.growth[1],growth_metric.base)),max(0.0,min(policy.growth[2],growth_metric.high))))
    rows=[];traces={}
    for index, name in enumerate(("bear","base","bull")):
        state=EnterpriseCashFlowState(revenue*margins[index],growth[index],policy.terminal[index],policy.wacc[index],policy.cash,policy.debt,0.0,policy.claims,policy.shares[index])
        trace=enterprise_cash_flow_dcf(state,forecast_years=FORECAST_YEARS,allow_nonpositive_equity_trace=True);raw=float(trace["intrinsic_value_per_share"])
        rows.append({"name":name,"conditional_value_per_share":max(0.0,raw),"raw_value_per_share":raw,"starting_cash_fcff":state.cash_fcff,"cash_conversion_margin":margins[index],"growth":growth[index],"wacc":policy.wacc[index],"terminal_growth":policy.terminal[index],"cash_and_investments":policy.cash,"debt_and_finance_leases":policy.debt,"other_equity_claims":policy.claims,"shares":policy.shares[index],"limited_liability_floor_applied":raw<0.0});traces[name]=trace
    scenario={"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]}
    if not 0.0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0.0:
        raise ValueError(f"{ticker}: invalid range")
    is_pass=ticker in PASS_TICKERS;reasons=() if is_pass else ("CONDITIONAL_EVENT_MODEL","SPECIALIST_MODEL_UNCERTAINTY")
    reliability=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="High" if is_pass else "Low",source_cap="High",reasons=reasons)
    public=profile.public_metadata()
    if not is_pass:public.update({"normalization_basis":"company_history_with_named_material_technology_dependency","assumption_source_mix":"reported_history_and_finsight_policy"})
    assumptions={**public,"forecast_years":FORECAST_YEARS,"cash_conversion_margin":margins,"growth":growth,"wacc":policy.wacc,"terminal_growth":policy.terminal,"shares":policy.shares,"tax_rate_basis":"governed 21% fallback because normalized filing history was outside 5%-30%" if tax_fallback else "normalized filing history","equity_floor_basis":"limited-liability bear floor with raw residual retained" if scenario["low"]==0.0 else "not applied","calculator_calibration":"Calculator is calibrated to the exact faded-cash base.","invalidation":policy.invalidation}
    baseline=BaselineValuation(ticker=ticker,method=policy.method,method_version=BATCH_26_HISTORY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence=reliability.label,availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL,key_assumptions=(BaselineAssumption("company history",str(profile.history_years_used),AssumptionClassification.HISTORICALLY_DERIVED,"Source-linked annual and current cash conversion anchors the range."),),warnings=(policy.warning,policy.invalidation),confidence_reasons=tuple(reliability.reasons),calculator_link=f"/api/us-valuations/{ticker}/calculator")
    return {"ticker":ticker,"method":policy.method,"model_version":BATCH_26_HISTORY_VERSION,"availability_type":"available" if is_pass else "conditional_estimate","scenario_rows":rows,"scenario_range":scenario,"reported_inputs":{"ttm_revenue":revenue,"ttm_operating_cash_flow":flows["operating_cash_flow"]["value"],"ttm_reinvestment":flows["capital_expenditures"]["value"],"ttm_interest":flows["interest_expense"]["value"],"tax_rate":tax_rate,"ttm_cash_fcff":current},"governed_assumptions":assumptions,"history_reliability":reliability.as_dict(),"source_ledger":{"controlling_filing":filing,"flow_sources":flows,"annual_cash_sources":list(annual),"tax_rate_sources":list(tax_sources),"tax_rate_treatment":{"fallback_applied":tax_fallback,"rate":tax_rate,"reason":"normalized filing history outside governed 5%-30% band" if tax_fallback else "normalized filing history"},"company_history_profile":profile.as_private_dict(),"bridge_sources":_bridge(ticker,structural,policy),"event_sources":_events(ticker,filing,structural,policy),"bridge_reconciliation":{"cash_and_investments":policy.cash,"debt_and_finance_leases":policy.debt,"other_equity_claims":policy.claims,"other_equity_claim_formula":policy.claim_formula,"shares":policy.shares,"operating_liability_treatment":"Operating leases, supplier finance, R&D, and ordinary working-capital liabilities remain inside operating cash conversion and are not deducted twice."},"model_trace":{"forecast_years":FORECAST_YEARS,"states":traces},"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":policy.warning,"baseline":baseline.as_private_dict()}


def _ibm_result(filing: dict[str, Any], structural: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    specs=((2021,"0001558370-22-001584",5_743_000_000.0),(2022,"0001558370-23-002376",1_639_000_000.0),(2023,"0000051143-26-000010",7_502_000_000.0),(2024,"0000051143-26-000010",6_023_000_000.0),(2025,"0000051143-26-000010",10_593_000_000.0));observations=[]
    for year,accession,value in specs:
        source=_companyfacts_duration(facts,concept="NetIncomeLossAvailableToCommonStockholdersBasic",accession=accession,start=f"{year}-01-01",end=f"{year}-12-31",expected=value);observations.append(HistoryObservation("annual",f"{year}-12-31",year,value,"USD","reported common earnings",(source,)))
    current=_structural_flow(structural,name="NetIncomeLossAvailableToCommonStockholdersBasic",start="2026-01-01",end="2026-06-30",expected=3_381_000_000.0)
    prior=_structural_flow(structural,name="NetIncomeLossAvailableToCommonStockholdersBasic",start="2025-01-01",end="2025-06-30",expected=3_249_000_000.0)
    ttm=float(observations[-1].value)+3_381_000_000.0-3_249_000_000.0
    observations.append(HistoryObservation("operating_ttm","2026-06-30",None,ttm,"USD","latest FY + current H1 - prior H1",(observations[-1].sources[0],current,prior)))
    metric=summarize_history_metric("normalized_common_earnings",observations);profile=CompanyHistoryProfile(HISTORY_POLICY_VERSION,"mixed_technology_finance_residual_income",BATCH_26_VALUATION_DATE,tuple(row.period_end for row in observations if row.period_role=="annual"),(metric,),True,"reported_and_company_history")
    dividend_sources=(_companyfacts_duration(facts,concept="DividendsCommonStockCash",accession="0000051143-26-000010",start="2025-01-01",end="2025-12-31",expected=6_255_000_000.0),_companyfacts_duration(facts,concept="DividendsCommonStockCash",accession="0000051143-26-000078",start="2026-01-01",end="2026-06-30",expected=3_166_000_000.0),_companyfacts_duration(facts,concept="DividendsCommonStockCash",accession="0000051143-26-000078",start="2025-01-01",end="2025-06-30",expected=3_112_000_000.0))
    beginning,ending=32_648_000_000.0,34_452_000_000.0;weighted,current_shares=952_697_295.0,942_134_390.0;shares=_shares(weighted,current_shares);earnings=(metric.low,metric.base,metric.high);average=(beginning+ending)/2.0;ttm_dividends=sum((dividend_sources[0]["value"],dividend_sources[1]["value"],-dividend_sources[2]["value"]));payout=min(1.0,ttm_dividends/ttm);cost=(.12,.10,.085);terminal_roe=(.12,.20,.28);terminal_growth=(.01,.02,.025);rows=[];traces={};multiples=[]
    for index,name in enumerate(("bear","base","bull")):
        trace=residual_income_valuation(book_value_per_share=ending/shares[index],current_roe=earnings[index]/average,cost_of_equity=cost[index],current_payout_ratio=payout,terminal_roe=terminal_roe[index],terminal_growth=terminal_growth[index],years=5);raw=float(trace["intrinsic_value"]);multiple=raw*shares[index]/earnings[index];rows.append({"name":name,"conditional_value_per_share":raw,"raw_value_per_share":raw,"normalized_common_earnings":earnings[index],"book_value_per_share":ending/shares[index],"current_roe":earnings[index]/average,"current_payout_ratio":payout,"cost_of_equity":cost[index],"terminal_roe":terminal_roe[index],"terminal_growth":terminal_growth[index],"earnings_multiple":multiple,"shares":shares[index],"limited_liability_floor_applied":False});traces[name]=trace;multiples.append(multiple)
    scenario={"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]}
    if not 0.0<scenario["low"]<=scenario["base"]<=scenario["high"]:raise ValueError("IBM: invalid equity range")
    reasons=("CONSOLIDATED_MODEL_FALLBACK","SPECIALIST_MODEL_UNCERTAINTY");reliability=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="Low",source_cap="High",reasons=reasons)
    warning="Conditional Low mixed technology/Global Financing residual-income baseline. Parent common earnings and equity avoid double-counting financing receivables and debt, while $10.48B of first-half acquisitions, acquired conversion, financing credit/funding, integration, and capital allocation remain material.";invalid="Invalidate if acquired cash/earnings, Global Financing receivables or credit losses, common equity, payout, debt funding, NCI, or diluted shares changes materially.";assumptions={**profile.public_metadata(),"normalization_basis":"reported_common_equity_and_history_residual_income","assumption_source_mix":"reported_common_equity_earnings_dividends_and_finsight_policy","normalized_common_earnings":earnings,"earnings_multiples":tuple(multiples),"shares":shares,"book_equity":ending,"average_common_equity":average,"current_payout_ratio":payout,"cost_of_equity":cost,"terminal_roe":terminal_roe,"terminal_growth":terminal_growth,"route_is_equity_level":True,"ev_debt_bridge_applied":False,"equity_floor_basis":"not applied","calculator_calibration":"Calculator varies normalized earnings and the residual-income-implied multiple around the base.","invalidation":invalid}
    baseline=BaselineValuation(ticker="IBM",method="mixed_technology_finance_residual_income_equity_earnings",method_version=BATCH_26_HISTORY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence=reliability.label,availability_type=AvailabilityType.CONDITIONAL,key_assumptions=(BaselineAssumption("reported common equity",ending,AssumptionClassification.REPORTED,"Current parent equity anchors residual income."),BaselineAssumption("company earnings history",str(profile.history_years_used),AssumptionClassification.HISTORICALLY_DERIVED,"Common earnings history supplies the ROE range.")),warnings=(warning,invalid),confidence_reasons=reasons,calculator_link="/api/us-valuations/IBM/calculator")
    context=[_point(structural,name="StockholdersEquity",expected=ending,period_end="2026-06-30"),_duration(structural,name="WeightedAverageNumberOfDilutedSharesOutstanding",expected=weighted,period_start="2026-01-01",period_end="2026-06-30"),_share_point(structural,expected=current_shares,end="2026-06-30"),_no_preferred(structural,"2026-06-30"),_structural_flow(structural,name="PaymentsOfDividendsCommonStock",start="2026-01-01",end="2026-06-30",expected=3_166_000_000.0),_point(structural,name="MinorityInterest",expected=89_000_000.0,period_end="2026-06-30")]
    events=[{"source_kind":"controlling_filing_narrative","accession":filing["accession"],"filed":filing["filed"],"period_end":filing["period_end"],"matter":warning,"reported_vs_estimated":"reported_narrative"},_fact(structural,name="PaymentsToAcquireBusinessesNetOfCashAcquired",expected=10_480_000_000.0,start="2026-01-01",end="2026-06-30"),_fact(structural,name="FinancingReceivableAndNetInvestmentInLeaseBeforeAllowanceForCreditLossAndFee",expected=14_526_000_000.0,start=None,end="2026-06-30")]
    return {"ticker":"IBM","method":baseline.method,"model_version":BATCH_26_HISTORY_VERSION,"availability_type":"conditional_estimate","scenario_rows":rows,"scenario_range":scenario,"reported_inputs":{"ttm_common_earnings":ttm,"beginning_common_equity":beginning,"ending_common_equity":ending,"current_period_common_dividends":3_166_000_000.0,"ttm_common_dividends":ttm_dividends},"governed_assumptions":assumptions,"history_reliability":reliability.as_dict(),"source_ledger":{"controlling_filing":filing,"company_history_profile":profile.as_private_dict(),"equity_model_context":context,"ttm_dividend_sources":list(dividend_sources),"event_sources":events,"residual_income_trace":{"states":traces},"bridge_treatment":"Equity-level model; Global Financing receivables/debt, industrial debt, acquisitions, and NCI remain inside common earnings/equity and are not EV-bridged.","structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":warning,"baseline":baseline.as_private_dict()}


def build_batch_26_history_result(*,ticker: str,source_root: Path,structural_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_26_TICKERS:raise ValueError(ticker)
    packet=Path(source_root)/ticker;submissions=json.loads((packet/"submissions.json").read_text());facts=json.loads((packet/"companyfacts.json").read_text());manifest=json.loads((packet/"source-manifest.json").read_text());structural=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text());filing=_controlling(manifest,submissions)
    if structural["source_accession"]!=filing["accession"]:raise ValueError(f"{ticker}: source mismatch")
    if ticker=="IBM":return _ibm_result(filing,structural,facts)
    if filing["period_end"]!=P[ticker].period:raise ValueError(f"{ticker}: period mismatch")
    return _operating_result(ticker,filing,structural,submissions,facts)


if set(P)!=(set(BATCH_26_TICKERS)-EQUITY_EARNINGS_TICKERS) or PASS_TICKERS|CONDITIONAL_TICKERS|WITHHELD_TICKERS!=set(BATCH_26_TICKERS):raise RuntimeError("Batch 26 policy mismatch")
