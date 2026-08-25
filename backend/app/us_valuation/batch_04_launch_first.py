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


BATCH_04_LAUNCH_FIRST_VERSION = "BATCH-04-LAUNCH-FIRST-1.0"


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
        "MCD": [("CashAndCashEquivalentsAtCarryingValue",822_000_000.),("DebtInstrumentCarryingAmount",39_900_000_000.),("OperatingLeaseLiabilityCurrent",690_000_000.),("OperatingLeaseLiabilityNoncurrent",14_039_000_000.)],
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


def _standard_result(ticker: str, *, source_root: Path, structural_root: Path) -> dict[str, Any]:
    policy = _POLICIES[ticker]
    packet = Path(source_root)/ticker
    submissions=json.loads((packet/"submissions.json").read_text()); facts=json.loads((packet/"companyfacts.json").read_text()); manifest=json.loads((packet/"source-manifest.json").read_text())
    structural=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text()); filing=_controlling(manifest,submissions)
    if structural["source_accession"] != filing["accession"] or filing["period_end"] != policy.period_end:
        raise ValueError(f"{ticker}: controlling source mismatch")
    normalizer=_normalizer(submissions,facts)
    flows={field:normalizer.ttm_flow(field) for field in ("revenue","operating_cash_flow","capital_expenditures","interest_expense")}
    tax,_tax_sources=_normalized_tax_rate(normalizer)
    current_cash=cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]),capital_expenditures=float(flows["capital_expenditures"]["value"]),spectrum_investment=0,interest_expense=abs(float(flows["interest_expense"]["value"])),tax_rate=tax)
    current_margin=current_cash/float(flows["revenue"]["value"])
    try:
        annual_cash,annual_revenue,annual_sources=_annual_cash_fcff(normalizer,spectrum_required=False,spectrum_floor=0,spectrum_source={},scope_adjustment=0)
        history=[cash/revenue for cash,revenue in zip(annual_cash,annual_revenue) if revenue>0]
    except ValueError:
        annual_cash=annual_revenue=annual_sources=()
        history=[]
    pool=history[-3:]+[current_margin]
    margins=(max(.005,min(pool)*.75),median(pool),max(pool)*1.15) if len(pool)>1 else (max(.005,current_margin*.65),current_margin,current_margin*1.25)
    reported_sources=[_point(structural,name="Assets",expected=policy.assets,period_end=policy.period_end),*_bridge_sources(ticker,structural,policy)]
    nci_is_reported=ticker in {"GPC","HAS","MGM"}
    if not nci_is_reported:
        reported_sources.append({"source_kind":"governed_policy","field":"unresolved_nci_and_other_claims","period_end":policy.period_end,"reported_vs_estimated":"estimated_range","value_range":{"bear":policy.assets*.02,"base":policy.assets*.01,"bull":0.0},"basis":"No current reported NCI point is asserted; the asset-based unresolved-claims reserve covers the uncertainty."})
    scenario_rows=[]
    for index,name in enumerate(("bear","base","bull")):
        claims=policy.nci+policy.assets*(.02,.01,0)[index]
        raw=five_year_fcff_dcf(revenue=float(flows["revenue"]["value"]),fcff_margin=margins[index],growth=policy.growth[index],wacc=policy.wacc[index],terminal_growth=policy.terminal_growth[index],cash_and_investments=policy.cash,debt=policy.debt,noncontrolling_interests=claims,shares=policy.shares[index])
        value=max(0.0,float(raw["value_per_share"]))
        scenario_rows.append({"name":name,"conditional_value_per_share":value,"raw_value_per_share":raw["value_per_share"],"cash_conversion_margin":margins[index],"growth":policy.growth[index],"wacc":policy.wacc[index],"terminal_growth":policy.terminal_growth[index],"limited_liability_floor_applied":value==0 and raw["value_per_share"]<0})
    lease_treatment=("Operating lease expense is already reflected in operating cash flow and is not subtracted again as debt." if ticker in {"MCD","MGM"} else "No separate operating-lease bridge subtraction is applied; operating lease cash remains in operating cash flow.")
    return {"ticker":ticker,"method":policy.method,"scenario_rows":scenario_rows,"scenario_range":{"low":scenario_rows[0]["conditional_value_per_share"],"base":scenario_rows[1]["conditional_value_per_share"],"high":scenario_rows[2]["conditional_value_per_share"]},"reported_inputs":{"ttm_revenue":flows["revenue"]["value"],"ttm_operating_cash_flow":flows["operating_cash_flow"]["value"],"ttm_capex":flows["capital_expenditures"]["value"]},"governed_assumptions":{"cash_conversion_margin":margins,"growth":policy.growth,"wacc":policy.wacc,"terminal_growth":policy.terminal_growth,"shares":policy.shares,"unresolved_claims_reserve_rates":(.02,.01,0),"equity_floor_basis":"limited-liability floor after a negative bear residual" if scenario_rows[0]["limited_liability_floor_applied"] else "not applied","calculator_calibration":"Calculator is calibrated to the published baseline and does not rerun this issuer-specific source model.","invalidation":policy.invalidation},"source_ledger":{"controlling_filing":filing,"flow_sources":flows,"bridge_sources":reported_sources,"annual_sources":annual_sources,"bridge_reconciliation":{"cash_and_investments":policy.cash,"interest_bearing_debt":policy.debt,"reported_nci":policy.nci if nci_is_reported else None,"nci_status":"reported" if nci_is_reported else "unresolved_covered_by_asset_reserve","unresolved_claims_reserve_rates":(.02,.01,0)},"operating_lease_treatment":lease_treatment,"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False,"basis":"Controlling submissions report date and fact-row periods govern; malformed parser summary period is diagnostic only."}},"warning":policy.warning}


def _ford_result(*, source_root: Path, structural_root: Path) -> dict[str, Any]:
    ticker="F";packet=Path(source_root)/ticker
    submissions=json.loads((packet/"submissions.json").read_text());facts=json.loads((packet/"companyfacts.json").read_text());manifest=json.loads((packet/"source-manifest.json").read_text());structural=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text());filing=_controlling(manifest,submissions)
    normalizer=_normalizer(submissions,facts)
    pretax=normalizer.ttm_flow("pretax_income");tax=normalizer.ttm_flow("income_tax");revenue=normalizer.ttm_flow("revenue");current_net=float(pretax["value"])-float(tax["value"])
    annual=[]
    for row in normalizer.annual_series("pretax_income",5):
        tax_row=normalizer.annual_at_end("income_tax",row.end);annual.append(float(row.value)-(float(tax_row.value) if tax_row else 0.0))
    positive=sorted(value for value in annual if value>0)
    earnings=(1_000_000_000.,median(positive),max(positive)*.75)
    multiples=(5.,8.,11.);shares=(4_300_000_000.,4_069_000_000.,3_987_000_000.)
    rows=[{"name":name,"conditional_value_per_share":earnings[i]*multiples[i]/shares[i],"normalized_common_earnings":earnings[i],"earnings_multiple":multiples[i],"shares":shares[i],"limited_liability_floor_applied":False} for i,name in enumerate(("bear","base","bull"))]
    margins=tuple(value/float(revenue["value"]) for value in earnings)
    ford_sources=[_point(structural,name="StockholdersEquity",expected=35_719_000_000.,period_end="2026-06-30"),_member_point(structural,name="NotesReceivableNet",expected=104_869_000_000.,period_end="2026-06-30",member="FordCreditMember"),_member_point(structural,name="DebtLongtermAndShorttermCombinedAmount",expected=137_348_000_000.,period_end="2026-06-30",member="FordCreditMember"),_member_point(structural,name="DebtLongtermAndShorttermCombinedAmount",expected=23_619_000_000.,period_end="2026-06-30",member="CompanyExcludingFordCreditMember")]
    return {"ticker":"F","method":"ford_normalized_equity_earnings_baseline","scenario_rows":rows,"scenario_range":{"low":rows[0]["conditional_value_per_share"],"base":rows[1]["conditional_value_per_share"],"high":rows[2]["conditional_value_per_share"]},"reported_inputs":{"ttm_revenue":revenue["value"],"ttm_pretax_income":pretax["value"],"ttm_income_tax":tax["value"],"ttm_common_earnings_proxy":current_net},"governed_assumptions":{"cash_conversion_margin":margins,"normalized_common_earnings":earnings,"earnings_multiples":multiples,"shares":shares,"route_is_captive_finance_sotp":False,"ev_debt_bridge_applied":False,"calculator_calibration":"Calculator is calibrated to the published baseline and does not rerun the normalized-equity-earnings model.","invalidation":"Invalidate when Ford Credit equity/funding, warranty/pension claims, or normalized common earnings leave the governed range."},"source_ledger":{"controlling_filing":filing,"revenue_source":revenue,"pretax_source":pretax,"tax_source":tax,"annual_common_earnings":annual,"ford_credit_context_sources":ford_sources,"ford_credit_treatment":"Conditional normalized consolidated equity-earnings baseline, not a Ford Credit SOTP. The EV debt bridge is deliberately not used because finance funding and receivables remain inside the consolidated equity object.","structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":"Conditional Low normalized-equity-earnings estimate. It is not a Ford Credit SOTP; auto-cycle/EV transition, warranty, pension, and finance economics can move value materially."}


def build_batch_04_launch_first_result(*,ticker:str,source_root:Path,structural_root:Path) -> dict[str,Any]:
    if ticker not in BATCH_04_TICKERS: raise KeyError(ticker)
    result=_ford_result(source_root=source_root,structural_root=structural_root) if ticker=="F" else _standard_result(ticker,source_root=source_root,structural_root=structural_root)
    scenario=result["scenario_range"]
    assumptions=(BaselineAssumption("reported operating anchor",str(result["reported_inputs"]),AssumptionClassification.REPORTED,"Controlling SEC filing and cutoff-safe history."),BaselineAssumption("governed scenario policy",str(result["governed_assumptions"]),AssumptionClassification.FINSIGHT_ASSUMPTION,"Launch-first broad bear/base/bull decision baseline."))
    def primary(): raise FallbackRejected("Primary source-bounded route requires model-specific refinements; launch-first conditional route selected.")
    def conditional(): return BaselineValuation(ticker=ticker,method=result["method"],method_version=BATCH_04_LAUNCH_FIRST_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence="Low",availability_type=AvailabilityType.CONDITIONAL,key_assumptions=assumptions,warnings=(result["warning"],result["governed_assumptions"]["invalidation"]),confidence_reasons=("CONDITIONAL_EVENT_MODEL","SPECIALIST_MODEL_UNCERTAINTY"),calculator_link=f"/api/us-valuations/{ticker}/calculator")
    baseline=run_fallback_ladder(ticker=ticker,strategies=((FallbackStage.PRIMARY_INTRINSIC,"primary_source_bounded",primary),(FallbackStage.CONDITIONAL,result["method"],conditional)))
    return {**result,"model_version":BATCH_04_LAUNCH_FIRST_VERSION,"availability_type":"conditional_estimate","baseline":baseline.as_private_dict()}
