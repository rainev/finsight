"""History-backed resource-cycle baselines for controlled Universe Reset Batch 44."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from .baseline import AvailabilityType, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling
from .batch_08_history import _annual_cash_with_losses
from .batch_35_history import _instant, _period_flow
from .batch_40_history import _latest_shares
from .batch_44 import BATCH_44_MANIFEST, BATCH_44_TICKERS, BATCH_44_VALUATION_DATE
from .batch_44_sources import verify_source_bundle
from .history import build_cash_fcff_history_profile
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability
from .xbrl import load_concept_config


BATCH_44_HISTORY_VERSION = "BATCH-44-HISTORY-1.0"
PERIOD = "2026-06-30"
PASS_TICKERS = frozenset()
WITHHELD_TICKERS = frozenset({"BKR", "AMCR", "SW"})
CONDITIONAL_TICKERS = frozenset(set(BATCH_44_TICKERS) - WITHHELD_TICKERS)

FLOW_SPEC = {
    "MPC": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpenseDebt",)},
    "PSX": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("CapitalExpendituresAndInvestments",), "interest": ("InterestAndDebtExpense",), "special_annual": True},
    "FANG": {"revenue": ("Revenues",), "ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PaymentsToExploreAndDevelopOilAndGasProperties",), "interest": ("InterestPaidNet",)},
    "BKR": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestPaidNet",)},
    "AMCR": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestExpense",), "fiscal_year_ttm": True},
    "DOW": {"revenue": ("Revenues",), "ocf": ("NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",), "capex": ("PaymentsToAcquireMachineryAndEquipment",), "interest": ("InterestExpenseDebt",)},
    "CTVA": {"revenue": ("Revenues",), "ocf": ("NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestAndDebtExpense",)},
    "APA": {"revenue": ("RevenuesAndOther",), "ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PaymentsToExploreAndDevelopOilAndGasProperties",), "interest": ("InterestExpenseDebt",), "special_annual": True},
    "SW": {"revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",), "ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PaymentsToAcquireProductiveAssets",), "interest": ("InterestExpenseNonoperating",)},
    "XOM": {"revenue": ("Revenues",), "ocf": ("NetCashProvidedByUsedInOperatingActivities",), "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",), "interest": ("InterestExpense",), "special_annual": True},
}

POLICY = {
    "MPC": {"growth": (-.08, -.005, .04), "wacc": (.12, .10, .085), "terminal": (-.02, .0025, .015), "warning": "Conditional Low refining/midstream-cycle FCFF baseline. Refining margins, MPLX/NCI, turnaround and growth capex, debt, projects and working-capital timing remain material."},
    "PSX": {"growth": (-.08, -.005, .04), "wacc": (.12, .10, .085), "terminal": (-.02, .0025, .015), "warning": "Conditional Low refining/chemicals-cycle FCFF baseline. WRB consolidation, refining margins, JV cash, capex/investments, debt and NCI remain material."},
    "FANG": {"growth": (-.08, 0., .04), "wacc": (.115, .095, .085), "terminal": (-.015, .005, .015), "warning": "Conditional Low E&P-cycle FCFF baseline. Commodity prices, decline, development capex, Endeavor integration, debt, NCI and ARO remain material."},
    "DOW": {"growth": (-.07, -.01, .035), "wacc": (.12, .105, .09), "terminal": (-.015, 0., .0125), "warning": "Conditional Low commodity-chemicals-cycle FCFF baseline. Recent negative cash history, restructuring, InfraCo, environmental/asbestos claims, debt, NCI and dilution remain material."},
    "CTVA": {"growth": (-.06, .01, .04), "wacc": (.11, .095, .085), "terminal": (-.01, .01, .018), "warning": "Conditional Low current consolidated agricultural-cycle FCFF baseline—not a post-separation value. Seasonality, pending Vylor separation, future debt allocation, environmental/product claims and pensions remain material."},
    "APA": {"growth": (-.08, 0., .04), "wacc": (.12, .10, .0875), "terminal": (-.02, .0025, .0125), "warning": "Conditional Low E&P-cycle FCFF baseline. Commodity prices, decline, development capex, Egypt NCI, debt, ARO and pending Savant/Uruguay activity remain material."},
    "XOM": {"growth": (-.07, 0., .04), "wacc": (.105, .09, .08), "terminal": (-.01, .0075, .0175), "warning": "Conditional Low integrated-energy-cycle FCFF baseline. Commodity/refining/chemicals cycles, holding-company continuity, capex, debt, NCI, pensions and project timing remain material."},
}

EVENT_TREATMENTS = {
    "MPC": "The earnings filing is reconciled to the controlling 10-Q. Future MPLX/refinery projects and repurchase authorization are not added as value or present claims.",
    "PSX": "WRB became fully consolidated on October 1, 2025. The three-year annual capex-and-investment lineage is retained with an explicit scope warning; announced future projects are excluded.",
    "FANG": "Current debt, shares and repurchases already reflect the filing state. Property acquisitions and repurchase authorization are excluded from recurring development capex and intrinsic value.",
    "BKR": "Chart closed July 16 after the balance date. The $2B funded term loans alone do not capture cash consideration, assumed claims or combined operations; no transaction value or synergy is invented.",
    "AMCR": "FY2026 contains only the first partial/full-year Berry combination period. Acquired sales/EBIT and stated integration costs are retained as diagnostics, not converted into a synthetic multi-year cash history.",
    "DOW": "The restructuring/InfraCo/environmental disclosures remain scenario context. The 5.41M registered incentive-plan shares are covered by the governed dilution stress and are not assumed fully issued twice.",
    "CTVA": "Vylor remains unseparated at cutoff. This is a current consolidated CTVA baseline; projected post-separation cash, debt and value are excluded and the result invalidates at separation.",
    "APA": "Near-term debt repayment is reflected only when present in the cutoff balance; pending Savant and Uruguay activity, contingent payments and guidance are excluded from current intrinsic value.",
    "SW": "The Smurfit/WestRock combination has only one complete combined year. Integration targets and predecessor histories remain diagnostics and are not spliced into a current-company cycle.",
    "XOM": "The July holding-company succession is treated as legal continuity of the same consolidated operations. Predecessor annual facts are separately hashed; no reorganization value is added.",
}


def _config(ticker: str) -> dict[str, Any]:
    config = deepcopy(load_concept_config()); spec = FLOW_SPEC[ticker]
    config["fields"]["revenue"]["concepts"] = list(spec["revenue"])
    config["fields"]["operating_cash_flow"]["concepts"] = list(spec["ocf"])
    config["fields"]["capital_expenditures"]["concepts"] = list(spec["capex"])
    config["fields"]["interest_expense"]["concepts"] = list(spec["interest"])
    return config


def _source(row: dict[str, Any], field: str) -> dict[str, Any]:
    return {"field": field, "namespace": row.get("namespace", "reported"), "concept": row.get("local_name"), "unit": row.get("unit"), "value": float(row["value"]), "start": row.get("period_start"), "end": row.get("period_end"), "accession": row.get("accession"), "form": row.get("form"), "filed": row.get("filed"), "fiscal_year": int(str(row.get("period_end"))[:4]), "fiscal_period": "FY", "dimensions": row.get("dimensions", []), "taxonomy_type": "reported_structural", "value_status": "reported", "selection_reason": "Exact no-dimension annual context from the cutoff-safe FY2025 filing."}


def _annual_fact(structural: dict[str, Any], name: str, end: str) -> dict[str, Any]:
    rows = [row for row in structural.get("facts", []) if row.get("local_name") == name and row.get("period_end") == end and row.get("period_start") == f"{end[:4]}-01-01" and not row.get("dimensions") and isinstance(row.get("value"), (int, float))]
    values = {float(row["value"]) for row in rows}
    if len(values) != 1: raise ValueError(f"annual {name} {end} unresolved")
    return rows[-1]


def _special_annual(ticker: str, root: Path, fallback_tax: float) -> tuple[dict[str, Any], ...]:
    packet = Path(root) / ticker; receipt = json.loads((packet / "source-receipt.json").read_text()); structural_path = packet / "structural-filing.json"; package_path = packet / "package-manifest.json"
    if hashlib.sha256(structural_path.read_bytes()).hexdigest() != receipt.get("structural_filing_sha256") or hashlib.sha256(package_path.read_bytes()).hexdigest() != receipt.get("package_manifest_sha256"): raise ValueError(f"{ticker}: annual receipt mismatch")
    structural = json.loads(structural_path.read_text()); spec = FLOW_SPEC[ticker]; rows=[]
    for end in ("2023-12-31", "2024-12-31", "2025-12-31"):
        raw={"revenue":_annual_fact(structural,spec["revenue"][0],end),"operating_cash_flow":_annual_fact(structural,spec["ocf"][0],end),"capital_expenditures":_annual_fact(structural,spec["capex"][0],end),"interest_expense":_annual_fact(structural,spec["interest"][0],end),"income_tax":_annual_fact(structural,"IncomeTaxExpenseBenefit",end)}
        try: raw["pretax_income"]=_annual_fact(structural,"IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",end)
        except ValueError: raw["pretax_income"]=None
        raw={field:({**value,"accession":structural.get("source_accession"),"filed":structural.get("filed_date"),"form":structural.get("form")} if value is not None else None) for field,value in raw.items()}
        fields={field:(_source(value,field) if value is not None else None) for field,value in raw.items()}
        tax_rate=fallback_tax if fields["pretax_income"] is None or fields["pretax_income"]["value"]<=0 else max(0.,min(.30,fields["income_tax"]["value"]/fields["pretax_income"]["value"]))
        rows.append({"period_end":end,**fields,"cash_fcff":cash_fcff_from_reported(operating_cash_flow=fields["operating_cash_flow"]["value"],capital_expenditures=fields["capital_expenditures"]["value"],spectrum_investment=0.,interest_expense=abs(fields["interest_expense"]["value"]),tax_rate=tax_rate),"formula":"OCF - capex + after-tax interest; exact structural annual lineage","annual_source_receipt":receipt})
    return tuple(rows)


def _flow(structural: dict[str, Any], names: tuple[str, ...], end: str) -> dict[str, Any]:
    return _period_flow(structural, names, end, target_days=180)


def _ttm(ticker: str, normalizer, structural: dict[str, Any], tax_rate: float, annual: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    spec=FLOW_SPEC[ticker]; fields={}
    if spec.get("fiscal_year_ttm"):
        latest=annual[-1]
        for field in ("revenue","operating_cash_flow","capital_expenditures","interest_expense"):
            fields[field]={"value":latest[field]["value"],"period_end":PERIOD,"method":"controlling_fy_is_ttm","sources":[latest[field]],"latest_fy":latest[field]}
    else:
        for field,names in (("revenue",spec["revenue"]),("operating_cash_flow",spec["ocf"]),("capital_expenditures",spec["capex"]),("interest_expense",spec["interest"])):
            if spec.get("special_annual"): latest=annual[-1][field]; annual_value=latest["value"]
            else:
                selected=normalizer.annual_series(field,1)
                if not selected: raise ValueError(f"{ticker}: annual {field} unavailable")
                latest=selected[-1].as_dict(); annual_value=selected[-1].value
            current=_flow(structural,names,PERIOD); prior=_flow(structural,names,"2025-06-30")
            fields[field]={"value":annual_value+current["value"]-prior["value"],"period_end":PERIOD,"method":"latest_fy_plus_current_h1_minus_prior_h1","sources":[latest,current,prior],"latest_fy":latest,"current_h1":current,"prior_h1":prior}
    fields["cash_fcff"]=cash_fcff_from_reported(operating_cash_flow=fields["operating_cash_flow"]["value"],capital_expenditures=fields["capital_expenditures"]["value"],spectrum_investment=0.,interest_expense=abs(fields["interest_expense"]["value"]),tax_rate=tax_rate)
    return fields


def _point(structural: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]: return _instant(structural,names,PERIOD)


def _bridge(ticker: str, structural: dict[str, Any]) -> dict[str, Any]:
    latest=_latest_shares(ticker,structural); cash=debt=fixed=stress=0.; excluded={}
    if ticker=="MPC": cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("DebtAndCapitalLeaseObligations",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]+_point(structural,("AccrualForEnvironmentalLossContingencies",))["value"]; excluded["equity_method_investments"]=_point(structural,("EquityMethodInvestments",))["value"]
    elif ticker=="PSX": cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("DebtCurrent",))["value"]+_point(structural,("LongTermDebtAndCapitalLeaseObligations",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("AssetRetirementObligationsAndAccruedEnvironmentalCost",))["value"]+_point(structural,("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]; excluded["equity_method_investments"]=_point(structural,("InvestmentsInAffiliatesSubsidiariesAssociatesAndJointVentures",))["value"]
    elif ticker=="FANG": cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("DebtLongtermAndShorttermCombinedAmount",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("AssetRetirementObligation",))["value"]; excluded["restricted_cash"]=_point(structural,("RestrictedCashAndCashEquivalentsAtCarryingValue",))["value"]
    elif ticker=="BKR": cash=_point(structural,("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",))["value"]; debt=_point(structural,("DebtLongtermAndShorttermCombinedAmount",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]; excluded["cash_availability_unresolved_post_chart"]="aggregate only; diagnostic while withheld"
    elif ticker=="AMCR": cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",))["value"]+_point(structural,("ShortTermBorrowings",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("DefinedBenefitPensionPlanLiabilitiesNoncurrent",))["value"]+_point(structural,("AccrualForEnvironmentalLossContingenciesComponentAmount",))["value"]
    elif ticker=="DOW": cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("LongTermDebtAndCapitalLeaseObligations",))["value"]+_point(structural,("LongTermDebtAndCapitalLeaseObligationsCurrent",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("AccrualForEnvironmentalLossContingencies",))["value"]; excluded["restricted_cash"]=_point(structural,("RestrictedCashAndCashEquivalents",))["value"]; excluded["asbestos_environmental_gross_overlap_not_added"]=_point(structural,("LiabilityForAsbestosAndEnvironmentalClaimsGross",))["value"]
    elif ticker=="CTVA": cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("DebtCurrent",))["value"]+_point(structural,("LongTermDebtAndCapitalLeaseObligations",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("AccrualForEnvironmentalLossContingencies",))["value"]+_point(structural,("AccrualforEnvironmentalLossContingenciesPotentialExposureinExcessofAccrual",))["value"]+_point(structural,("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]; excluded["restricted_cash"]=_point(structural,("RestrictedCash",))["value"]
    elif ticker=="APA":
        cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",))["value"]; parent=_point(structural,("StockholdersEquity",))["value"]; consolidated=_point(structural,("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",))["value"]; fixed=consolidated-parent; stress=_point(structural,("AssetRetirementObligation",))["value"]+_point(structural,("AccrualForEnvironmentalLossContingenciesGross",))["value"]; excluded["nci_derivation"]={"consolidated_equity":consolidated,"parent_equity":parent,"difference":fixed}
    elif ticker=="SW": cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("DebtAndCapitalLeaseObligations",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]
    elif ticker=="XOM": cash=_point(structural,("CashAndCashEquivalentsAtCarryingValue",))["value"]; debt=_point(structural,("DebtCurrent",))["value"]+_point(structural,("LongTermDebtAndCapitalLeaseObligations",))["value"]; fixed=_point(structural,("MinorityInterest",))["value"]; stress=_point(structural,("PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",))["value"]; excluded["equity_method_investments"]=_point(structural,("EquityMethodInvestments",))["value"]
    else: raise ValueError(ticker)
    return {"cash":float(cash),"debt":float(debt),"claims":(float(fixed+stress),float(fixed),float(fixed)),"latest_common_shares":latest,"base_share_count":float(latest["value"]),"excluded_or_separately_treated":{**excluded,"operating_claim_stress":(float(stress),0.,0.),"operating_claim_policy":"Operating cash effects remain in OCF; closing pension/ARO/environmental balances are bear-only stresses. Fixed NCI is deducted in every scenario."},"reported_vs_estimated":"reported_bridge_with_named_scope_controls"}


def _events(ticker: str, root: Path, source_manifest_sha256: str) -> dict[str, Any]:
    path=root/ticker/"inventory.json"; rows=json.loads(path.read_text())
    if not rows or any(row.get("filed","")>BATCH_44_VALUATION_DATE for row in rows): raise ValueError(f"{ticker}: invalid event inventory")
    documents=[]
    for row in rows:
        for document in row.get("documents",[]):
            document_path=Path(document["path"])
            if not document_path.is_absolute(): document_path=root.parent.parent/document_path
            if not document_path.exists() or hashlib.sha256(document_path.read_bytes()).hexdigest()!=document.get("sha256"): raise ValueError(f"{ticker}: event hash mismatch")
            documents.append(document)
    return {"source_kind":"sec_event_screening","decision":"accepted_context","screened_filings":rows,"documents":documents,"inventory_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"source_manifest_sha256":source_manifest_sha256,"treatment":EVENT_TREATMENTS[ticker],"reported_vs_estimated":"reported_and_screened"}


def _withheld(ticker: str, *, filing, flows, annual, profile, bridge, event, verification, structural, tax_rate, tax_sources) -> dict[str, Any]:
    reasons={
        "BKR":("Withheld: Baker Hughes closed the Chart acquisition after the June balance date. The $2B term loans are known, but exact cash consideration, assumed claims, post-close cash/debt and combined operating cash flow are not in the controlling 10-Q.","Revalue with acquisition accounting, exact cash/assumed-claim bridge and issuer-filed Chart combined or pro-forma cash-flow history."),
        "AMCR":("Withheld: FY2026 is the first full post-Berry annual period; older annual cash periods are legacy or partial-combination Amcor. Acquired sales and EBIT do not supply a comparable multi-year combined OCF/capex cycle.","Revalue with issuer-filed combined pro-forma cash flows or at least three comparable post-Berry annual cash periods on the current debt/share base."),
        "SW":("Withheld: Smurfit Westrock has only one complete combined-company annual cash period. FY2022-2023 are predecessor Smurfit and FY2024 is partial, so the historical cycle cannot be applied to the current company without splicing unlike perimeters.","Revalue after at least three comparable combined-company annual periods or issuer-filed pro-forma OCF, capex and interest history."),
    }
    reason,invalidation=reasons[ticker]; baseline=BaselineValuation(ticker=ticker,method="resource_cycle_enterprise_fcff",method_version=BATCH_44_HISTORY_VERSION,low=None,base=None,high=None,confidence=None,availability_type=AvailabilityType.NOT_AVAILABLE,warnings=(reason,invalidation))
    return {"ticker":ticker,"method":baseline.method,"model_version":BATCH_44_HISTORY_VERSION,"availability_type":"not_available","scenario_rows":[],"scenario_range":{"low":None,"base":None,"high":None},"reported_inputs":{"ttm_revenue":flows["revenue"]["value"],"ttm_cash_fcff":flows["cash_fcff"]},"governed_assumptions":{**profile.public_metadata(),"forecast_years":8,"normalization_basis":"current-company scope hard gate; history retained as diagnostic only","assumption_source_mix":"reported_history_current_ttm_and_event_context","equity_floor_basis":"not applied","invalidation":invalidation},"history_reliability":None,"source_ledger":{"controlling_filing":filing,"flow_sources":flows,"annual_cash_sources":annual,"tax_rate":tax_rate,"tax_rate_sources":list(tax_sources),"company_history_profile":profile.as_private_dict(),"bridge_context":bridge,"event_sources":event,"runtime_source_verification":verification,"current_ttm_is_diagnostic_only":True,"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":reason,"baseline":baseline.as_private_dict()}


def build_batch_44_history_result(*,ticker:str,source_root:Path,structural_root:Path,event_root:Path,structural_cache_root:Path,special_annual_root:Path,xom_annual_root:Path)->dict[str,Any]:
    if ticker not in BATCH_44_TICKERS: raise ValueError(ticker)
    packet=Path(source_root)/ticker; structural_packet=Path(structural_root)/ticker; submissions=json.loads((packet/"submissions.json").read_text()); facts=json.loads((packet/"companyfacts.json").read_text()); manifest=json.loads((packet/"source-manifest.json").read_text()); structural=json.loads((structural_packet/"structural-filing.json").read_text()); filing=_controlling(manifest,submissions)
    if structural.get("source_accession")!=filing["accession"] or structural.get("report_date")!=PERIOD: raise ValueError(f"{ticker}: controlling mismatch")
    verification=verify_source_bundle(ticker=ticker,packet=packet,structural_packet=structural_packet,structural_cache_root=Path(structural_cache_root),filing=filing); event=_events(ticker,Path(event_root),verification["source_manifest_sha256"]); normalizer=_normalizer(submissions,facts,concept_config=_config(ticker))
    if ticker=="XOM":
        annual=_special_annual(ticker,Path(xom_annual_root),.283); tax_rates=[row["income_tax"]["value"]/row["pretax_income"]["value"] for row in annual]; tax_rate=sorted(tax_rates)[1]; tax_sources=tuple(row["income_tax"] for row in annual)
    else:
        tax_rate,tax_sources=_normalized_tax_rate(normalizer)
        if FLOW_SPEC[ticker].get("special_annual"): annual=_special_annual(ticker,Path(special_annual_root),tax_rate)
        else: _,_,annual=_annual_cash_with_losses(normalizer)
    flows=_ttm(ticker,normalizer,structural,tax_rate,annual); ttm_sources=[source for field in ("revenue","operating_cash_flow","capital_expenditures","interest_expense") for source in flows[field]["sources"]]; profile=build_cash_fcff_history_profile(annual_cash_states=annual,ttm_revenue=flows["revenue"]["value"],ttm_cash_fcff=flows["cash_fcff"],ttm_period_end=PERIOD,ttm_sources=ttm_sources,valuation_date=BATCH_44_VALUATION_DATE); metric=profile.metric("cash_conversion_margin")
    if metric is None: raise ValueError(f"{ticker}: cash history unavailable")
    bridge=_bridge(ticker,structural)
    if ticker in WITHHELD_TICKERS: return _withheld(ticker,filing=filing,flows=flows,annual=annual,profile=profile,bridge=bridge,event=event,verification=verification,structural=structural,tax_rate=tax_rate,tax_sources=tax_sources)
    policy=POLICY[ticker]; margins=(metric.low,metric.base,metric.high); share_base=bridge["base_share_count"]; shares=(share_base*1.015,share_base,share_base*.985); rows=[]; traces={}
    for index,name in enumerate(("bear","base","bull")):
        starting=flows["revenue"]["value"]*max(.0025,margins[index]); state=EnterpriseCashFlowState(starting,policy["growth"][index],policy["terminal"][index],policy["wacc"][index],bridge["cash"],bridge["debt"],0.,bridge["claims"][index],shares[index]); trace=enterprise_cash_flow_dcf(state,forecast_years=8,allow_nonpositive_equity_trace=True); raw=float(trace["intrinsic_value_per_share"]); rows.append({"name":name,"raw_value_per_share":raw,"conditional_value_per_share":max(0.,raw),"starting_cash_fcff":starting,"cash_conversion_margin":max(.0025,margins[index]),"growth":policy["growth"][index],"wacc":policy["wacc"][index],"terminal_growth":policy["terminal"][index],"cash_and_investments":bridge["cash"],"debt_and_finance_leases":bridge["debt"],"other_equity_claims":bridge["claims"][index],"shares":shares[index],"limited_liability_floor_applied":raw<0}); traces[name]=trace
    scenario=dict(zip(("low","base","high"),(row["conditional_value_per_share"] for row in rows)))
    if not 0<=scenario["low"]<=scenario["base"]<=scenario["high"] or scenario["base"]<=0: raise ValueError(f"{ticker}: nonpositive or unordered scenario")
    reliability=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="Low",source_cap="High",reasons=("NORMALIZED_CYCLICAL_RANGE","SPECIALIST_MODEL_UNCERTAINTY")); invalidation="Revalue if current-company scope, resource/input prices, cash conversion, capex, debt/leases, NCI, operating claims, shares or cutoff events leave the recorded range."
    if ticker=="PSX": invalidation="Revalue when WRB has comparable fully consolidated cash history or an issuer-filed scope bridge; also revalue if refining/chemicals margins, capex/investments, debt, NCI or cutoff events leave the range."
    assumptions={**profile.public_metadata(),"forecast_years":8,"normalization_basis":"source-linked cash-FCFF history with issuer-specific cycle and event treatment","assumption_source_mix":"reported_history_and_governed_cycle_scenarios","cash_conversion_margin":tuple(max(.0025,x) for x in margins),"growth":policy["growth"],"wacc":policy["wacc"],"terminal_growth":policy["terminal"],"shares":shares,"share_sensitivity_basis":"latest cutoff-safe common shares are the base; governed +/-1.5% stress represents unresolved dilution","equity_floor_basis":"bear-only limited-liability floor; raw residual retained privately","calculator_calibration":"Exact enterprise cash-FCFF default replay.","invalidation":invalidation}
    baseline=BaselineValuation(ticker=ticker,method="resource_cycle_enterprise_fcff",method_version=BATCH_44_HISTORY_VERSION,low=scenario["low"],base=scenario["base"],high=scenario["high"],confidence="Low",availability_type=AvailabilityType.CONDITIONAL,warnings=(policy["warning"],invalidation))
    return {"ticker":ticker,"method":baseline.method,"model_version":BATCH_44_HISTORY_VERSION,"availability_type":"conditional_estimate","scenario_rows":rows,"scenario_range":scenario,"reported_inputs":{"ttm_revenue":flows["revenue"]["value"],"ttm_cash_fcff":flows["cash_fcff"],"share_count":share_base},"governed_assumptions":assumptions,"history_reliability":reliability.as_dict(),"source_ledger":{"controlling_filing":filing,"flow_sources":flows,"annual_cash_sources":annual,"tax_rate":tax_rate,"tax_rate_sources":list(tax_sources),"company_history_profile":profile.as_private_dict(),"bridge_context":bridge,"event_sources":event,"model_trace":{"states":traces},"raw_scenario_rows":rows,"runtime_source_verification":verification,"structural_top_level_period_diagnostic":{"value":structural.get("period_end"),"used_for_selection":False}},"warning":policy["warning"],"baseline":baseline.as_private_dict()}


if PASS_TICKERS|CONDITIONAL_TICKERS|WITHHELD_TICKERS!=set(BATCH_44_TICKERS): raise RuntimeError("Batch 44 policy mismatch")
