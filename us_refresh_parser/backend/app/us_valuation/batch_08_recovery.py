"""One-attempt recovery models for Batch 08 withheld issuers."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .baseline import AssumptionClassification,AvailabilityType,BaselineAssumption,BaselineValuation
from .batch_04_launch_first import _controlling,_duration,_point
from .batch_07_history import _structural_flow
from .batch_08 import BATCH_08_VALUATION_DATE
from .batch_08_history import BATCH_08_HISTORY_VERSION,build_batch_08_history_result
from .history import HISTORY_POLICY_VERSION
from .reliability import assess_reliability

BATCH_08_RECOVERY_VERSION="BATCH-08-RECOVERY-1.0"

def _load(ticker,source_root,structural_root):
 packet=Path(source_root)/ticker;sub=json.loads((packet/'submissions.json').read_text());manifest=json.loads((packet/'source-manifest.json').read_text());structural=json.loads((Path(structural_root)/ticker/'structural-filing.json').read_text());filing=_controlling(manifest,sub)
 if structural['source_accession']!=filing['accession']:raise ValueError(f'{ticker}: recovery source mismatch')
 return filing,structural

def recover_aptv(*,source_root:Path,structural_root:Path)->dict[str,Any]:
 filing,structural=_load('APTV',source_root,structural_root)
 if filing['period_end']!='2026-06-30':raise ValueError('APTV recovery period mismatch')
 current_income=_structural_flow(structural,name='IncomeLossFromContinuingOperations',start='2026-01-01',end='2026-06-30',expected=427_000_000.)
 prior_income=_structural_flow(structural,name='IncomeLossFromContinuingOperations',start='2025-01-01',end='2025-06-30',expected=125_000_000.)
 current_nci=_structural_flow(structural,name='IncomeLossFromContinuingOperationsAttributableToNoncontrollingEntity',start='2026-01-01',end='2026-06-30',expected=3_000_000.)
 prior_nci=_structural_flow(structural,name='IncomeLossFromContinuingOperationsAttributableToNoncontrollingEntity',start='2025-01-01',end='2025-06-30',expected=6_000_000.)
 current_parent=current_income['value'];prior_parent=prior_income['value'];annualized=current_parent*2;earnings=(annualized*.75,annualized,annualized*1.25);multiples=(6.,8.,10.);shares=(223_560_000.,212_530_000.,201_000_000.);rows=[]
 for i,name in enumerate(('bear','base','bull')):
  value=earnings[i]*multiples[i]/shares[i];rows.append({'name':name,'conditional_value_per_share':value,'raw_value_per_share':value,'normalized_continuing_parent_earnings':earnings[i],'earnings_multiple':multiples[i],'shares':shares[i],'limited_liability_floor_applied':False})
 scenario={'low':rows[0]['conditional_value_per_share'],'base':rows[1]['conditional_value_per_share'],'high':rows[2]['conditional_value_per_share']}
 assumptions={'history_policy_version':HISTORY_POLICY_VERSION,'history_years_used':2,'normalization_basis':'post_spin_current_and_comparative_h1_equity_earnings','assumption_source_mix':'reported_current_comparative_and_finsight_policy','normalized_consolidated_earnings':earnings,'earnings_multiples':multiples,'shares':shares,'ev_debt_bridge_applied':False,'equity_floor_basis':'not applied','calculator_calibration':'Calculator directly varies normalized earnings and the earnings multiple around the published base.','invalidation':'Invalidate if continuing-operations scope, debt retained after the spin, NCI, diluted shares, or post-spin earnings leaves the recorded evidence.'}
 reliability=assess_reliability(accounting_low=scenario['base'],accounting_base=scenario['base'],accounting_high=scenario['base'],scenario_low=scenario['low'],scenario_base=scenario['base'],scenario_high=scenario['high'],model_cap='Low',source_cap='High',reasons=('CONDITIONAL_EVENT_MODEL','SPECIALIST_MODEL_UNCERTAINTY'))
 warning='Conditional Low post-spin continuing-equity-earnings estimate. It uses only current and comparative continuing H1 evidence; no pre-spin annual cash history is reused.'
 baseline=BaselineValuation(ticker='APTV',method='post_spin_continuing_equity_earnings',method_version=BATCH_08_RECOVERY_VERSION,low=scenario['low'],base=scenario['base'],high=scenario['high'],confidence=reliability.label,availability_type=AvailabilityType.CONDITIONAL,key_assumptions=(BaselineAssumption('current and comparative continuing H1',str({'current_parent':current_parent,'prior_parent':prior_parent}),AssumptionClassification.REPORTED,'The controlling filing reports both periods on the same post-spin continuing basis.'),BaselineAssumption('annualization and earnings multiples',str(assumptions),AssumptionClassification.FINSIGHT_ASSUMPTION,'H1 parent earnings are annualized; broad earnings multiples and share sensitivity remain governed.')),warnings=(warning,assumptions['invalidation']),confidence_reasons=tuple(reliability.reasons),calculator_link='/api/us-valuations/APTV/calculator')
 context=[_point(structural,name='StockholdersEquity',expected=8_753_000_000.,period_end='2026-06-30'),_point(structural,name='DebtAndCapitalLeaseObligations',expected=5_354_000_000.,period_end='2026-06-30'),_duration(structural,name='WeightedAverageNumberOfDilutedSharesOutstanding',expected=212_530_000.,period_start='2026-01-01',period_end='2026-06-30'),_structural_flow(structural,name='CashPaymentsRelatedToSpinOff',start='2026-01-01',end='2026-06-30',expected=282_000_000.)]
 return {'ticker':'APTV','method':'post_spin_continuing_equity_earnings','model_version':BATCH_08_RECOVERY_VERSION,'availability_type':'conditional_estimate','scenario_rows':rows,'scenario_range':scenario,'reported_inputs':{'current_h1_parent_continuing_earnings':current_parent,'prior_h1_parent_continuing_earnings':prior_parent},'governed_assumptions':assumptions,'history_reliability':reliability.as_dict(),'source_ledger':{'controlling_filing':filing,'continuing_earnings':{'current_parent_attributable_income':current_income,'current_nci_presentation_diagnostic':current_nci,'prior_parent_attributable_income':prior_income,'prior_nci_presentation_diagnostic':prior_nci,'nci_subtracted_again':False},'equity_context':context,'bridge_treatment':'Equity-level recovery; the continuing-income facts are already attributable to Aptiv, so NCI is not subtracted again. Retained debt and the spin distribution remain inside continuing earnings/equity. No EV debt bridge is applied.','structural_top_level_period_diagnostic':{'value':structural.get('period_end'),'used_for_selection':False}},'warning':warning,'baseline':baseline.as_private_dict()}

def evaluate_nclh(*,source_root:Path,structural_root:Path)->dict[str,Any]:
 initial=build_batch_08_history_result(ticker='NCLH',source_root=source_root,structural_root=structural_root);filing,structural=_load('NCLH',source_root,structural_root)
 current=_structural_flow(structural,name='NetIncomeLossAttributableToParentDiluted',start='2026-01-01',end='2026-06-30',expected=328_795_000.);prior=_structural_flow(structural,name='NetIncomeLoss',start='2025-01-01',end='2025-06-30',expected=-10_303_000.)
 diagnostic={'ttm_parent_earnings':423_246_000.+current['value']-prior['value'],'post_shutdown_annual_earnings':(166_178_000.,910_257_000.,423_246_000.),'current_h1_parent_earnings':current['value'],'prior_h1_parent_earnings':prior['value'],'why_rejected':'An earnings multiple does not bind the equity funding, interest, or dilution effects of $18.648B newbuild commitments; using it would hide the same load-bearing uncertainty that blocked cash FCFF.'}
 return {**initial,'recovery_attempt':{'attempt_number':1,'candidate_method':'cruise_consolidated_equity_earnings','outcome':'withheld','diagnostic':diagnostic,'hard_stop':'newbuild_funding_and_dilution_unbounded'}}
