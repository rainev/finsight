"""Practical-materiality Pass repairs for confirmed Batch 14 HCA and REGN."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from typing import Any
from .batch_04_launch_first import _point
from .batch_07_history import _structural_flow
from .batch_11_history import _dimension_fact
from .batch_14 import BATCH_14_TICKERS
from .batch_14_history import build_batch_14_history_result
from .reliability import assess_reliability

BATCH_14_REPAIR_VERSION="BATCH-14-PASS-REPAIR-1.0"
REPAIRED_PASS_TICKERS=frozenset({"HCA","REGN"})
FINAL_PASS_TICKERS=frozenset({"HCA","REGN","IDXX"})

def _hca_sources(st:dict[str,Any],structural_root:Path)->list[dict[str,Any]]:
 package=json.loads((Path(structural_root)/"HCA/package-manifest.json").read_text());primary=next(row for row in package["files"] if row["local_path"]==package["primary_document"])
 return [_point(st,name="ProfessionalLiabilityRisks",expected=1_466_000_000.,period_end="2025-12-31"),{"source_kind":"sec_filing_text","accession":st["source_accession"],"filed":package.get("filed_date"),"form":package.get("form"),"period_end":package.get("report_date"),"primary_document":package["primary_document"],"document_sha256":primary["sha256"],"url":primary["source_url"],"reported_terms":{"insurance_subsidiary_reserve_current":104_000_000.,"insurance_subsidiary_reserve_prior":91_000_000.,"self_insured_reserve_current":1_892_000_000.,"self_insured_reserve_prior":1_906_000_000.,"expected_next_twelve_month_claim_payments":573_000_000.,"expected_self_insured_claim_payments":532_000_000.},"reported_vs_estimated":"reported"}]

def _regn_sources(st:dict[str,Any])->list[dict[str,Any]]:
 return [_dimension_fact(st,name="RevenueFromContractWithCustomerExcludingAssessedTax",expected=4_354_700_000.,start="2026-01-01",end="2026-06-30",member="CollaborationRevenueMember"),_dimension_fact(st,name="RevenueFromContractWithCustomerExcludingAssessedTax",expected=3_391_900_000.,start="2025-01-01",end="2025-06-30",member="CollaborationRevenueMember"),_structural_flow(st,name="RevenueFromContractWithCustomerExcludingAssessedTax",start="2026-01-01",end="2026-06-30",expected=7_896_100_000.),_structural_flow(st,name="RevenueFromContractWithCustomerExcludingAssessedTax",start="2025-01-01",end="2025-06-30",expected=6_704_300_000.),_structural_flow(st,name="AcquiredInProcessResearchAndDevelopment",start="2026-01-01",end="2026-06-30",expected=228_900_000.),_structural_flow(st,name="PaymentsToAcquireIntangibleAssets1",start="2026-01-01",end="2026-06-30",expected=99_900_000.)]

def build_batch_14_repair_result(*,ticker:str,source_root:Path,structural_root:Path,event_root:Path)->dict[str,Any]:
 initial=build_batch_14_history_result(ticker=ticker,source_root=source_root,structural_root=structural_root,event_root=event_root)
 if ticker not in REPAIRED_PASS_TICKERS:return initial
 result=deepcopy(initial);scenario=result["scenario_range"];shares=result["governed_assumptions"]["shares"];st=json.loads((Path(structural_root)/ticker/"structural-filing.json").read_text())
 if ticker=="HCA":
  reserve=1_464_000_000.;base_reserve=732_000_000.;no_reserve_base=scenario["base"]+base_reserve/shares[1];base_equity=no_reserve_base*shares[1];impact=reserve/base_equity;sources=_hca_sources(st,Path(structural_root));warning="Source-bounded hospital-operations baseline. The complete professional-liability reserve sensitivity is 1.92% of base common equity, below the governed 5% materiality threshold; the 100%/50%/0% range remains visible.";basis={"maximum_bounded_amount":reserve,"no_reserve_base_value_per_share":no_reserve_base,"base_common_equity":base_equity,"impact_ratio":impact,"threshold":.05,"decision":"ordinary_bounded_sensitivity"}
 else:
  base_equity=scenario["base"]*shares[1];ipr=228_900_000.;cash=99_900_000.;claim=67_200_000.;sources=_regn_sources(st);warning="Source-bounded consolidated biotechnology baseline. Collaboration revenue is recurring in comparative periods; acquired IPR&D, acquisition cash, and contingent consideration are each below 1% of base common equity.";basis={"base_common_equity":base_equity,"acquired_iprd":ipr,"acquired_iprd_impact_ratio":ipr/base_equity,"intangible_acquisition_cash":cash,"intangible_acquisition_cash_impact_ratio":cash/base_equity,"contingent_consideration":claim,"contingent_consideration_impact_ratio":claim/base_equity,"collaboration_revenue_current_h1":4_354_700_000.,"collaboration_revenue_prior_h1":3_391_900_000.,"threshold":.05,"decision":"recurring_consolidated_and_immaterial_bounded_sensitivities"}
 if not all(float(value)<.05 for key,value in basis.items() if key.endswith("impact_ratio")):raise ValueError(f"{ticker}: repair exceeds materiality threshold")
 reliability=assess_reliability(accounting_low=scenario["base"],accounting_base=scenario["base"],accounting_high=scenario["base"],scenario_low=scenario["low"],scenario_base=scenario["base"],scenario_high=scenario["high"],model_cap="High",source_cap="High",reasons=())
 result["model_version"]=BATCH_14_REPAIR_VERSION;result["availability_type"]="available";result["warning"]=warning;result["history_reliability"]=reliability.as_dict();result["governed_assumptions"]["materiality_assessment"]=basis;result["governed_assumptions"]["assumption_source_mix"]="reported_and_company_history";result["source_ledger"]["pass_repair"]={"policy_version":BATCH_14_REPAIR_VERSION,"materiality_assessment":basis,"sources":sources,"reason":"Existing source-bounded sensitivity retained; classification repaired from material Conditional to ordinary Pass."};baseline=result["baseline"];baseline["method_version"]=BATCH_14_REPAIR_VERSION;baseline["availability_type"]="available";baseline["warnings"]=[warning,result["governed_assumptions"]["invalidation"]];baseline["confidence"]=reliability.label;baseline["confidence_reasons"]=list(reliability.reasons)
 return result

if not REPAIRED_PASS_TICKERS<set(BATCH_14_TICKERS):raise RuntimeError("Batch 14 repair denominator mismatch")
