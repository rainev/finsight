"""Compiler for declarative operating-company refresh policies.

The compiler emits executable-shaped policy contracts and an honest gap
registry. It never fits concepts to amounts, tunes growth/discount inputs, or
claims production readiness.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from .xbrl import load_concept_config
from .refresh_financials import POLICY_VERSION as CASH_HISTORY_VERSION
from .refresh_growth_policies import AUDITED_GROWTH_TICKERS, compile_history_growth_policy


COMPILER_SCHEMA = "FINSIGHT-REFRESH-OPERATING-POLICIES-1"
SUPPORTED_MODES = frozenset({
    "history_backed_normalized_cash_conversion",
    "history_backed_bounded_uncertainty",
    "enterprise_cash_fcff_exact",
    "faded_cash_fcff",
    "faded_cash_fcff_recovery",
    "normalized_cash_conversion",
    "consolidated_cash_fcff",
    "consolidated",
    "company_history_cash_conversion",
    "normalized_owner_cash",
    "normalized_cycle",
})


@dataclass(frozen=True)
class PolicyCompileResult:
    ticker: str
    cik: str
    status: str
    reason_codes: tuple[str, ...]
    policy: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "cik": self.cik,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "policy": self.policy,
        }


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _concept_candidates(concept_config: Mapping[str, Any], field: str) -> tuple[str, ...]:
    definition = concept_config.get("fields", {}).get(field, {})
    concepts = definition.get("concepts", ()) if isinstance(definition, Mapping) else ()
    return tuple(str(item) for item in concepts if isinstance(item, str))


def _collect_concepts(value: object) -> tuple[str, ...]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"concept", "source_concept", "field"} and isinstance(item, str):
                found.add(item)
            found.update(_collect_concepts(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_concepts(item))
    return tuple(sorted(found))


def _source_rows(evidence: object) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(evidence, Mapping):
        return ()
    rows = evidence.get("rows")
    if isinstance(rows, list):
        return tuple(row for row in rows if isinstance(row, Mapping))
    return (evidence,)


def _policy_for_entry(
    entry: Mapping[str, Any],
    *,
    artifact: Mapping[str, Any] | None,
    recipe: Mapping[str, Any] | None,
    source_evidence: Mapping[str, Any] | None,
    concept_config: Mapping[str, Any],
) -> PolicyCompileResult:
    ticker = str(entry.get("ticker", ""))
    cik = str(entry.get("cik", ""))
    mode = entry.get("forecast_mode")
    reasons: list[str] = []
    if mode not in SUPPORTED_MODES:
        reasons.append('issuer_state_scope_requires_explicit_refresh_rule')
    if artifact is None:
        reasons.append("baseline_artifact_missing")
    public = artifact.get("public_assumptions", {}) if isinstance(artifact, Mapping) else {}
    if not isinstance(public, Mapping):
        public = {}
    if any(key in public for key in ("nonoperating_adjustment", "equity_overlay", "other_equity_claims")):
        reasons.append("nonzero_or_explicit_equity_overlay_requires_explicit_rule")
    if entry.get("primary_model") not in {"fcff_dcf", "conditional_estimate"}:
        reasons.append("primary_model_not_supported_by_operating_fcff_compiler")
    engines: set[str] = set()
    baseline_claims = {}
    if recipe is None:
        reasons.append("approved_recipe_missing")
    else:
        engines = {
            scenario.get("engine")
            for scenario in recipe.get("scenarios", {}).values()
            if isinstance(scenario, Mapping)
        }
        engines.discard(None)
        if engines != {"enterprise_cash_fcff"} and engines != {"constant_growth_fcff"}:
            reasons.append("recipe_engine_not_supported_by_operating_compiler")
        for scenario in recipe.get("scenarios", {}).values() if isinstance(recipe.get("scenarios"), Mapping) else ():
            inputs = scenario.get("inputs", {}) if isinstance(scenario, Mapping) else {}
            for field in ("nonoperating_adjustment", "equity_overlay"):
                value = inputs.get(field)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value != 0:
                    reasons.append(f"nonzero_{field}_requires_explicit_rule")
        for case, scenario in recipe.get('scenarios', {}).items():
            inputs = scenario.get('inputs', {})
            baseline_claims[case] = {key: inputs[key] for key in ('preferred_equity', 'noncontrolling_interests', 'nonoperating_adjustment') if key in inputs}
        # Historical batches also put litigation/commitment reserves into the
        # preferred-equity slot. A same-named current preferred-stock tag does
        # not establish that those economic claims have disappeared.
        if any(value != 0 for claims in baseline_claims.values() for value in claims.values()):
            reasons.append('baseline_non_debt_claim_scope_requires_source_rule')
    evidence_rows = _source_rows(source_evidence)
    fixed = {
        key: public[key]
        for key in ("forecast_years", "initial_growth", "policy_wacc", "wacc", "terminal_growth", "cost_of_equity", "terminal_roe")
        if key in public
    }
    base_inputs = recipe.get("scenarios", {}).get("base", {}).get("inputs", {}) if isinstance(recipe, Mapping) else {}
    if isinstance(base_inputs, Mapping):
        for source, target in (("initial_growth", "initial_growth"), ("growth", "initial_growth"), ("wacc", "wacc"), ("terminal_growth", "terminal_growth"), ("forecast_years", "forecast_years")):
            if target not in fixed and source in base_inputs:
                fixed[target] = base_inputs[source]
    policy = {
        "version": "US-REFRESH-OPERATING-POLICY-1",
        "supported_engine": "constant_growth_fcff" if recipe and engines == {"constant_growth_fcff"} else "enterprise_cash_fcff",
        "execution_state": "compiled_source_validation_pending",
        "auto_tune": False,
        "inputs": {
            "ttm_revenue": {
                "selector": "ttm",
                "field": "revenue",
                "concept_candidates": list(_concept_candidates(concept_config, "revenue")),
            },
            "source_shares": {"selector":"normalized_bridge", "field":"fully_diluted_shares_proxy"},
        },
        "scenario_bindings": {},
        "concept_config": deepcopy(concept_config),
        "source_requirements": {"structural": True, "event_exhibits": True},
        "normalization_version": CASH_HISTORY_VERSION,
        "intentional_migration_changes": [
            "Rebuild sustainable cash conversion from aligned annual history and current TTM data.",
            "Use contemporaneous source bridge uncertainty and a locked reported diluted-share proxy; do not carry stale share counts.",
        ],
        "fixed_assumptions": fixed,
        "source_contract": {
            "source_rows_required": True,
            "amount_fit_forbidden": True,
            "required_lineage": ["accession", "filed_date", "period_end", "unit", "concept"],
        },
        "baseline_non_debt_claims": baseline_claims,
    }
    for case, statistic in (('bear','low'),('base','base'),('bull','high')):
        margin_key = f'{case}_cash_margin'
        policy['inputs'][margin_key] = {'selector':'cash_fcff_history', 'field':'cash_conversion_margin',
            'statistic':statistic, 'normalization_version':CASH_HISTORY_VERSION}
        cash_stat = {'bear':'low','base':'midpoint','bull':'high'}[case]
        claim_stat = {'bear':'high','base':'midpoint','bull':'low'}[case]
        for field in ('cash_and_investments','debt','preferred_equity','noncontrolling_interests'):
            policy['inputs'][f'{case}_{field}'] = {'selector':'normalized_bridge','field':field,
                'statistic':cash_stat if field=='cash_and_investments' else claim_stat}
        bound = {'cash_and_investments':f'{case}_cash_and_investments'}
        if policy['supported_engine']=='enterprise_cash_fcff':
            bound.update({'cash_fcff':{'multiply':['ttm_revenue',margin_key]},
                'interest_bearing_debt':f'{case}_debt','preferred_equity':f'{case}_preferred_equity',
                'noncontrolling_interests':f'{case}_noncontrolling_interests','diluted_shares':'source_shares'})
        else:
            bound.update({'revenue':'ttm_revenue','fcff_margin':margin_key,'debt':f'{case}_debt',
                'noncontrolling_interests':{'add':[f'{case}_preferred_equity',f'{case}_noncontrolling_interests']},'shares':'source_shares'})
        policy['scenario_bindings'][case] = bound
    if (ticker,str(cik).zfill(10)) in {('CDW','0001402057'),('MCO','0001059556')}:
        from .refresh_financials import CDW_CASH_INTEREST_POLICY,MCO_CASH_INTEREST_POLICY
        policy['version'] += '-CASH-INTEREST-1'
        for case in ('bear','base','bull'):
            policy['inputs'][f'{case}_cash_margin']['financing_policy'] = CDW_CASH_INTEREST_POLICY if ticker=='CDW' else MCO_CASH_INTEREST_POLICY
        policy['intentional_migration_changes'].append(f'Preserve {ticker} cash-interest-paid lineage for current and annual cash FCFF; never fall back to a mixed-sign income/expense series.')
    if (ticker,str(cik).zfill(10))==('COHR','0000820318'):
        from .refresh_financials import COHR_OPERATING_INTEREST_POLICY
        policy['version']+='-OPERATING-INTEREST-1'
        for case in ('bear','base','bull'):
            policy['inputs'][f'{case}_cash_margin']['financing_policy']=COHR_OPERATING_INTEREST_POLICY
        policy['intentional_migration_changes'].append('Preserve COHR current and annual operating-interest lineage as the filing-specific gross financing proxy; never mix it with net-interest concepts.')
    if ticker=='CTSH' and str(cik).zfill(10)=='0001058290':
        from .refresh_financials import CTSH_STRUCTURAL_INTEREST_POLICY
        policy['version'] += '-STRUCTURAL-INTEREST-1'
        policy['inputs']['ttm_revenue']['selector']='structural_ttm'
        for case in ('bear','base','bull'):
            policy['inputs'][f'{case}_cash_margin']['financing_policy']=CTSH_STRUCTURAL_INTEREST_POLICY
            policy['inputs'][f'{case}_cash_margin']['structural_ttm_fields']=[
                'revenue','operating_cash_flow','capital_expenditures']
        policy['intentional_migration_changes'].append('Reconstruct CTSH current interest from the exact controlling-filing YTD and comparative YTD structural facts plus the prior annual fact; do not carry the annual amount into TTM.')
    if ticker == 'CMG' and str(cik).zfill(10) == '0001058090':
        from .refresh_financials import CMG_OWNER_CASH_POLICY
        policy['version'] += '-OWNER-CASH-1'
        policy['cash_policy'] = CMG_OWNER_CASH_POLICY
        for case in ('bear','base','bull'):
            policy['inputs'][f'{case}_cash_margin']['cash_policy'] = CMG_OWNER_CASH_POLICY
        policy['intentional_migration_changes'].append('Preserve CMG owner cash as reported OCF minus capex without interest/tax adjustment; require the supported debt-free bridge before valuation.')
    if ticker == 'DASH' and str(cik).zfill(10) == '0001792789':
        from .refresh_financials import DASH_OWNER_CASH_POLICY
        policy['cash_policy']=DASH_OWNER_CASH_POLICY
        for case in ('bear','base','bull'):
            policy['inputs'][f'{case}_cash_margin']['cash_policy']=DASH_OWNER_CASH_POLICY
            policy['inputs'][f'{case}_cash_margin']['additional_capex_fields']=['software_development']
        policy['version']+='-DASH-OWNER-CASH-1'
        policy['intentional_migration_changes'].append('Preserve DASH owner cash as reported OCF minus PP&E and separately reported capitalized software; do not invent an interest addback for the zero-coupon convertible note.')
    if ticker == 'ADP' and policy['supported_engine'] == 'enterprise_cash_fcff':
        from .refresh_claim_policies import build_adp_claim_policy
        claims = build_adp_claim_policy()
        alias = claims['capex_alias']
        policy['concept_config']['fields']['capital_expenditures'] = {key:alias[key] for key in ('unit','kind','concepts')}
        policy['inputs']['adp_claim_reserve'] = {'selector':'special_claim','field':'claim_adjustment','policy':claims}
        for fields in policy['scenario_bindings'].values():
            fields['nonoperating_adjustment'] = {'subtract':[0.,'adp_claim_reserve']}
        policy['intentional_migration_changes'].append('Separate ADP client-funds and net litigation reserves from reported preferred stock; deduct them once as a nonoperating adjustment.')
        reasons = [reason for reason in reasons if reason != 'baseline_non_debt_claim_scope_requires_source_rule']
    if ticker == 'BR' and str(cik).zfill(10) == '0001383312' and engines == {'enterprise_cash_fcff'}:
        from .refresh_acquisition_claims import broadridge_claim_policy
        policy['inputs']['acquisition_liability'] = {'selector': 'special_claim', 'field': 'claim_adjustment', 'policy': broadridge_claim_policy()}
        for fields in policy['scenario_bindings'].values():
            fields['nonoperating_adjustment'] = {'subtract': [0., 'acquisition_liability']}
        policy['intentional_migration_changes'].append('Separate reported acquisition contingent consideration from preferred stock and deduct its current carrying liability once.')
        policy['version'] = 'US-REFRESH-OPERATING-POLICY-1-BR-CAPEX-1'
        policy['concept_config']['fields']['capital_expenditures'] = {'unit':'USD','kind':'flow','concepts':['us-gaap:PaymentsToAcquirePropertyPlantAndEquipment']}
        policy['concept_config']['fields']['capitalized_software'] = {'unit':'USD','kind':'flow','concepts':['us-gaap:PaymentsForSoftware']}
        for case in ('bear','base','bull'):
            policy['inputs'][f'{case}_cash_margin']['additional_capex_fields'] = ['capitalized_software']
        policy['intentional_migration_changes'].append('Deduct separately reported software investment alongside PP&E; preserve the reported components and do not substitute operating software-license liabilities for investment cash.')
        reasons = [reason for reason in reasons if reason != 'baseline_non_debt_claim_scope_requires_source_rule']
    if ticker == 'IDXX' and str(cik).zfill(10) == '0000874716' and engines == {'enterprise_cash_fcff'}:
        from .refresh_acquisition_claims import idexx_claim_policy
        policy['inputs'] = {'acquisition_liability':{'selector':'special_claim','field':'claim_adjustment','policy':idexx_claim_policy()}, **policy['inputs']}
        for fields in policy['scenario_bindings'].values():
            fields['nonoperating_adjustment'] = {'subtract':[0.,'acquisition_liability']}
        policy['intentional_migration_changes'].append('Correct the prior estimated acquisition payment mislabelled as an upper bound; require current liability evidence or explicitly report the unsupported current estimate.')
        reasons = [reason for reason in reasons if reason != 'baseline_non_debt_claim_scope_requires_source_rule']
    if ticker in {'VRTX','LLY','CTSH','VRT','REGN'} and engines == {'enterprise_cash_fcff'}:
        from .refresh_acquisition_claims import wg2_claim_policy
        claim_policy = wg2_claim_policy(ticker)
        if str(cik).zfill(10) != claim_policy['cik']:
            raise RuntimeError('WG2 acquisition claim registry identity mismatch')
        policy['inputs']['acquisition_liability'] = {
            'selector':'special_claim','field':'claim_adjustment','policy':claim_policy,
        }
        for fields in policy['scenario_bindings'].values():
            fields['nonoperating_adjustment'] = {'subtract':[0.,'acquisition_liability']}
        policy['version'] += '-WG2-ACQUISITION-CLAIM-1'
        policy['intentional_migration_changes'].append('Separate the current acquisition carrying liability from preferred equity and deduct it once; transaction prices, maxima, paid cash, duration accruals and post-period events remain separately classified.')
        reasons = [reason for reason in reasons if reason != 'baseline_non_debt_claim_scope_requires_source_rule']
    if ticker in {'ABT','BAX'} and engines == {'enterprise_cash_fcff'}:
        from .refresh_acquisition_claims import mixed_claim_policy
        mixed_policy=mixed_claim_policy(ticker)
        if str(cik).zfill(10)!=mixed_policy['cik']:
            raise RuntimeError('WG15 mixed-claim registry identity mismatch')
        policy['inputs']['mixed_acquisition_claim']={
            'selector':'special_claim','field':'claim_adjustment','policy':mixed_policy}
        claim_expression='mixed_acquisition_claim'
        if ticker=='ABT':
            from .refresh_financials import ABT_STRUCTURAL_INTEREST_POLICY
            from .refresh_litigation_claims import litigation_claim_policy
            legal_policy=litigation_claim_policy(ticker)
            if str(cik).zfill(10)!=legal_policy['cik']:
                raise RuntimeError('WG15 litigation registry identity mismatch')
            policy['inputs']['mixed_litigation_claim']={
                'selector':'special_claim','field':'claim_adjustment','policy':legal_policy}
            policy['inputs']['abt_pro_forma_revenue']={
                'selector':'special_claim','field':'annualized_pro_forma_revenue','policy':mixed_policy}
            claim_expression={'add':['mixed_acquisition_claim','mixed_litigation_claim']}
            policy['inputs']['ttm_revenue']['selector']='structural_ttm'
            for case in ('bear','base','bull'):
                policy['inputs'][f'{case}_cash_margin']['financing_policy']=ABT_STRUCTURAL_INTEREST_POLICY
                policy['inputs'][f'{case}_cash_margin']['structural_ttm_fields']=[
                    'revenue','operating_cash_flow','capital_expenditures']
            policy['version']+='-STRUCTURAL-INTEREST-1'
        for fields in policy['scenario_bindings'].values():
            fields['nonoperating_adjustment']={'subtract':[0.,claim_expression]}
        if ticker=='ABT':
            for case in ('bear','base','bull'):
                policy['scenario_bindings'][case]['cash_fcff']={
                    'multiply':['abt_pro_forma_revenue',f'{case}_cash_margin']}
        policy['version']+='-WG15-MIXED-NCI-CLAIMS-1'
        policy['intentional_migration_changes'].append('Separate current NCI from acquisition, legal, environmental, disposal and indemnification claims; count matching aggregate/Level-3 views once and keep paid cash, possible-loss ranges and historical maxima non-additive.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker in {'ABBV','STE','CAH','COO','FIS','V','DASH'} and engines in ({'enterprise_cash_fcff'},{'constant_growth_fcff'}):
        from .refresh_litigation_claims import litigation_claim_policy
        litigation_policy=litigation_claim_policy(ticker)
        if str(cik).zfill(10)!=litigation_policy['cik']:
            raise RuntimeError('litigation claim registry identity mismatch')
        policy['inputs']['litigation_claim']={
            'selector':'special_claim','field':'claim_adjustment','policy':litigation_policy}
        for case,fields in policy['scenario_bindings'].items():
            if policy['supported_engine']=='enterprise_cash_fcff':
                fields['nonoperating_adjustment']={'subtract':[0.,'litigation_claim']}
            else:
                fields['noncontrolling_interests']={'add':[
                    {'add':[f'{case}_preferred_equity',f'{case}_noncontrolling_interests']},
                    'litigation_claim']}
        policy['version']+='-WG3-LITIGATION-CLAIM-1'
        policy['intentional_migration_changes'].append('Separate current litigation accruals, recognized recoveries, operating settlement balances, paid cash and unaccrued exposure; deduct only a source-bound current net claim once.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker in {'MU','KLAC','NXPI','AVGO','SNDK'} and engines == {'enterprise_cash_fcff'}:
        from .refresh_commitment_claims import commitment_claim_policy
        commitment_policy=commitment_claim_policy(ticker)
        if str(cik).zfill(10)!=commitment_policy['cik']:raise RuntimeError('commitment registry identity mismatch')
        policy['inputs']['commitment_claim']={'selector':'special_claim','field':'claim_adjustment','policy':commitment_policy}
        for fields in policy['scenario_bindings'].values():fields['nonoperating_adjustment']={'subtract':[0.,'commitment_claim']}
        policy['version']+='-WG4-COMMITMENT-CLAIM-1'
        policy['intentional_migration_changes'].append('Separate current payables, paid cash, future commitments, contingent maxima, authorizations and timing-incomplete schedules; deduct only a source-bound current claim once.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker=='MRK' and engines=={'enterprise_cash_fcff'}:
        from .refresh_post_filing_events import post_filing_event_policy
        event_policy=post_filing_event_policy()
        if str(cik).zfill(10)!=event_policy['cik']:raise RuntimeError('MRK event registry identity mismatch')
        policy['inputs']['post_filing_event_claim']={'selector':'special_claim','field':'claim_adjustment','policy':event_policy}
        for fields in policy['scenario_bindings'].values():fields['nonoperating_adjustment']={'subtract':[0.,'post_filing_event_claim']}
        policy['version']+='-POST-FILING-EVENT-1';policy['intentional_migration_changes'].append('Reconcile current claims and completed post-period acquisition cash once; pending consideration and transaction price never become intrinsic value.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker in {'AVY','BALL','MPC'} and engines=={'enterprise_cash_fcff'}:
        from .refresh_operating_claims import operating_claim_policy
        operating_claim = operating_claim_policy(ticker)
        if str(cik).zfill(10) != operating_claim['cik']:
            raise RuntimeError('operating claim registry identity mismatch')
        if ticker == 'MPC':
            for case in ('bear','base','bull'):
                key = f'{case}_operating_claim'
                policy['inputs'][key] = {
                    'selector':'special_claim','field':f'{case}_adjustment','policy':operating_claim,
                }
                policy['scenario_bindings'][case]['nonoperating_adjustment'] = {'subtract':[0.,key]}
        else:
            policy['inputs'] = {'operating_claim': {
                'selector':'special_claim','field':'claim_adjustment','policy':operating_claim,
            }, **policy['inputs']}
            for fields in policy['scenario_bindings'].values():
                fields['nonoperating_adjustment'] = {'subtract':[0.,'operating_claim']}
        policy['version'] += '-WG7-OPERATING-CLAIM-1'
        policy['intentional_migration_changes'].append('Separate ownership claims, benefit liabilities, operating reserves, recoveries, paid cash and noncash OCF movements; bind only the declared nonoverlapping scenario treatment.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker in {'DASH','ICE'} and engines in ({'enterprise_cash_fcff'},{'constant_growth_fcff'}):
        from .refresh_customer_funds import customer_funds_policy
        customer_policy=customer_funds_policy(ticker)
        if str(cik).zfill(10)!=customer_policy['cik']:
            raise RuntimeError('customer-funds registry identity mismatch')
        if ticker=='DASH':
            for case in ('bear','base','bull'):
                key=f'{case}_customer_cash_reserve'
                policy['inputs'][key]={'selector':'special_claim','field':f'{case}_cash_reserve','policy':customer_policy}
                policy['scenario_bindings'][case]['cash_and_investments']={
                    'subtract':[f'{case}_cash_and_investments',key]}
        else:
            policy['inputs']['matched_customer_funds']={
                'selector':'special_claim','field':'claim_adjustment','policy':customer_policy}
            for fields in policy['scenario_bindings'].values():
                fields['nonoperating_adjustment']={'subtract':[0.,'matched_customer_funds']}
        policy['version']+='-WG8-CUSTOMER-FUNDS-1'
        policy['intentional_migration_changes'].append('Separate issuer cash from restricted and customer/clearing funds, matched operating liabilities, gross pledged collateral and guaranty diagnostics; bind only the approved cash reserve or exact net-zero treatment.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker in {'KDP','MSCI'} and engines in ({'enterprise_cash_fcff'},{'constant_growth_fcff'}):
        from .refresh_acquisition_financing_claims import acquisition_financing_policy
        claim_policy=acquisition_financing_policy(ticker)
        if str(cik).zfill(10)!=claim_policy['cik']:
            raise RuntimeError('acquisition-financing registry identity mismatch')
        if ticker=='MSCI':
            policy['inputs']['restricted_cash']={
                'selector':'special_claim','field':'restricted_cash_adjustment','policy':claim_policy}
            for case in ('bear','base','bull'):
                key=f'{case}_acquisition_claim'
                policy['inputs'][key]={
                    'selector':'special_claim','field':f'{case}_adjustment','policy':claim_policy}
                policy['scenario_bindings'][case]['cash_and_investments']={
                    'subtract':[f'{case}_cash_and_investments','restricted_cash']}
                policy['scenario_bindings'][case]['nonoperating_adjustment']={'subtract':[0.,key]}
        else:
            claim_inputs={}
            for case in ('bear','base','bull'):
                key=f'{case}_acquisition_financing_claim'
                claim_inputs[key]={'selector':'special_claim','field':f'{case}_adjustment','policy':claim_policy}
                policy['scenario_bindings'][case]['noncontrolling_interests']={
                    'add':[{'add':[f'{case}_preferred_equity',f'{case}_noncontrolling_interests']},key]}
                policy['scenario_bindings'][case]['revenue']='kdp_pro_forma_revenue'
            claim_inputs['kdp_pro_forma_revenue']={
                'selector':'special_claim','field':'annualized_revenue','policy':claim_policy}
            policy['inputs']={**claim_inputs,**policy['inputs']}
        policy['version']+='-WG9-ACQUISITION-FINANCING-1'
        policy['intentional_migration_changes'].append('Separate current acquisition liabilities, ownership claims, mandatory redemption, supplier financing, paid cash, integration stresses and pending transaction consideration; never fit ambiguous typed locations to prior amounts.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker=='MCHP' and engines=={'enterprise_cash_fcff'}:
        from .refresh_convertible_claims import convertible_claim_policy
        convertible_policy=convertible_claim_policy(ticker,{
            case:recipe['scenarios'][case]['inputs']['wacc'] for case in ('bear','base','bull')
        })
        if str(cik).zfill(10)!=convertible_policy['cik']:
            raise RuntimeError('convertible claim registry identity mismatch')
        policy['narrative_evidence_policy']=deepcopy(convertible_policy['narrative_evidence_policy'])
        claim_inputs={}
        for case in ('bear','base','bull'):
            dividend=f'{case}_convertible_dividend_pv';conversion=f'{case}_convertible_conversion_shares'
            claim_inputs[dividend]={'selector':'special_claim','field':f'{case}_adjustment','policy':convertible_policy}
            claim_inputs[conversion]={'selector':'special_claim','field':f'{case}_conversion_shares','policy':convertible_policy}
            policy['scenario_bindings'][case]['preferred_equity']={'add':[f'{case}_preferred_equity',dividend]}
            policy['scenario_bindings'][case]['diluted_shares']={'add':['source_shares',conversion]}
        policy['inputs']={**claim_inputs,**policy['inputs']}
        policy['version']+='-WG11-CONVERTIBLE-NARRATIVE-1'
        policy['intentional_migration_changes'].append('Extract mandatory-convertible dates, rates, dividends and capped-call limitations deterministically from hashed filing narrative; deduct exact-date dividend PV and add conversion dilution once, never liquidation preference too.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker=='BMY' and engines=={'enterprise_cash_fcff'}:
        from .refresh_transaction_claims import transaction_claim_policy
        transaction_policy=transaction_claim_policy(ticker)
        if str(cik).zfill(10)!=transaction_policy['cik']:
            raise RuntimeError('transaction claim registry identity mismatch')
        policy['narrative_evidence_policy']=deepcopy(transaction_policy['narrative_evidence_policy'])
        policy['inputs']={'transaction_claim':{
            'selector':'special_claim','field':'claim_adjustment','policy':transaction_policy},**policy['inputs']}
        policy['version']+='-WG11-TRANSACTION-NARRATIVE-1'
        policy['intentional_migration_changes'].append('Keep recognized CVR, dated Hengrui payments, paid BioNTech cash, fixed BioNTech timing envelope and both contingent maxima separate; incomplete fixed-payment timing remains review-only.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    if ticker == 'PG' and str(cik).zfill(10) == '0000080424' and engines == {'constant_growth_fcff'}:
        from .refresh_preferred_conversion import CONVERSION_POLICY
        policy['capital_structure_policy'] = deepcopy(CONVERSION_POLICY)
        policy['intentional_migration_changes'].append('Validate PG assumed preferred conversion in current diluted shares; retain reported preferred value diagnostically without a second deduction.')
    if ticker == 'CF' and str(cik).zfill(10) == '0001324404' and engines == {'enterprise_cash_fcff'}:
        policy['cash_receipt_policy'] = 'CF_ORICA_LITIGATION_SETTLEMENT'
        policy['intentional_migration_changes'].append('Remove the source-backed Orica receipt from the actual cash-date window, retaining evidence across future fiscal periods; do not use gain recognition as the cash date.')
    from .refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES
    claim_rule = REPORTED_NCI_SCOPE_RULES.get(ticker)
    if claim_rule is not None and str(cik).zfill(10) == claim_rule.cik and engines in ({'enterprise_cash_fcff'}, {'constant_growth_fcff'}):
        # Audited historical formulas establish that these legacy preferred
        # slots contained reported NCI, not contingent or finite reserves.
        # Current amounts still must reconcile to the official source bridge.
        policy['reported_claim_scope'] = asdict(claim_rule)
        policy['intentional_migration_changes'].append('Keep documented reported NCI separate from preferred equity, reclassifying legacy preferred slots where necessary; validate every current component against the normalized NCI bridge.')
        if claim_rule.clears_legacy_claim_scope:
            reasons = [reason for reason in reasons if reason != 'baseline_non_debt_claim_scope_requires_source_rule']
        if ticker=='COHR':
            policy['inputs']['ttm_cash_fcff']={
                'selector':'cash_fcff_history','field':'ttm_cash_fcff',
                'normalization_version':policy['normalization_version']}
            bear_gap={'max':[0.,{'subtract':[{'multiply':['ttm_revenue','bear_cash_margin']},'ttm_cash_fcff']} ]}
            policy['scenario_bindings']['bear']['nonoperating_adjustment']={'subtract':[0.,bear_gap]}
            policy['scenario_bindings']['base']['nonoperating_adjustment']=0.
            policy['scenario_bindings']['bull']['nonoperating_adjustment']=0.
            policy['version']+='-CASH-DOWNSIDE-GAP-1'
            policy['intentional_migration_changes'].append('Keep COHR current NCI in the ownership bridge and preserve the separate bear-only gap between normalized cash and current reported cash as a signed scenario stress; do not label that stress preferred equity.')
        if ticker=='CMI':
            from .refresh_nci_ownership_claims import nci_ownership_claim_policy
            guarantee_policy=nci_ownership_claim_policy(ticker)
            policy['inputs']={'guarantee_scope_review':{
                'selector':'special_claim','field':'claim_adjustment','policy':guarantee_policy},**policy['inputs']}
            for fields in policy['scenario_bindings'].values():
                fields['nonoperating_adjustment']={'subtract':[0.,'guarantee_scope_review']}
            policy['version']+='-NCI-GUARANTEE-SCOPE-1'
            policy['intentional_migration_changes'].append('Keep CMI current NCI separate from the recognized guarantee carrying value and maximum exposure; block until the guarantee scopes reconcile instead of adding the maximum to NCI.')
    if ticker=='A' and str(cik).zfill(10)=='0001090872' and engines=={'enterprise_cash_fcff'}:
        from .refresh_vie_scope import unconsolidated_vie_scope_policy
        policy['unconsolidated_vie_scope']=unconsolidated_vie_scope_policy(ticker)
        policy['concept_config']['fields']['marketable_securities_noncurrent']['concepts']=[
            concept for concept in policy['concept_config']['fields']['marketable_securities_noncurrent']['concepts']
            if concept!='LongTermInvestments']
        policy['version']+='-UNCONSOLIDATED-VIE-SCOPE-1'
        policy['intentional_migration_changes'].append('Keep Agilent not-primary-beneficiary VIE investments and loans as an investment exposure diagnostic, not issuer NCI or an additive cash-like asset.')
        reasons=[reason for reason in reasons if reason!='baseline_non_debt_claim_scope_requires_source_rule']
    from .refresh_bridge_scope_policies import AGGREGATE_DEBT_SCOPE_RULES
    debt_rule = AGGREGATE_DEBT_SCOPE_RULES.get(ticker)
    if debt_rule is not None and str(cik).zfill(10) == debt_rule.cik and engines in ({'enterprise_cash_fcff'}, {'constant_growth_fcff'}):
        policy['aggregate_debt_scope'] = asdict(debt_rule)
        policy['version'] += '-DEBT-SCOPE-1'
        policy['intentional_migration_changes'].append('Use the current filing aggregate debt presentation once, with complete component coverage and reconciliation; never add overlapping debt or lease detail twice.')
        if ticker in {'ABT','MCO','ROK'}:
            concepts = policy['concept_config']['fields']['marketable_securities_noncurrent']['concepts']
            policy['concept_config']['fields']['marketable_securities_noncurrent']['concepts'] = [
                concept for concept in concepts if concept != 'LongTermInvestments'
            ]
            policy['intentional_migration_changes'].append(f'Exclude {ticker} generic LongTermInvestments from cash-like securities under its approved other-asset scope; retain only directly classified cash-like instruments.')
        if ticker == 'VRT':
            concepts = policy['concept_config']['fields']['marketable_securities_current']['concepts']
            held_to_maturity = 'DebtSecuritiesHeldToMaturityAmortizedCostAfterAllowanceForCreditLossCurrent'
            if held_to_maturity not in concepts:
                concepts.append(held_to_maturity)
            policy['intentional_migration_changes'].append('Bind VRT current held-to-maturity debt securities as cash-like investments; require complete current evidence before treating the noncurrent counterpart as zero.')
        if ticker == 'AVY':
            current = policy['concept_config']['fields']['marketable_securities_current']['concepts']
            noncurrent = policy['concept_config']['fields']['marketable_securities_noncurrent']['concepts']
            for concepts, name in ((current,'DebtSecuritiesAvailableForSaleExcludingAccruedInterest'),
                                   (noncurrent,'DebtSecuritiesAvailableForSaleExcludingAccruedInterestNoncurrent')):
                if name not in concepts:
                    concepts.append(name)
            policy['intentional_migration_changes'].append('Classify AVY current and noncurrent available-for-sale debt securities directly from their current filing facts; do not infer them from the prior cash total.')
    from .refresh_bridge_scope_policies import OUTSIDE_EQUITY_ZERO_RULES
    outside_equity_rule = OUTSIDE_EQUITY_ZERO_RULES.get(ticker)
    if outside_equity_rule is not None and str(cik).zfill(10) == outside_equity_rule['cik'] and engines in ({'enterprise_cash_fcff'}, {'constant_growth_fcff'}):
        policy['outside_equity_zero_scope'] = dict(outside_equity_rule)
        policy['version'] += '-OUTSIDE-EQUITY-SCOPE-1'
        policy['intentional_migration_changes'].append('Accept zero NCI only when current consolidated assets, liabilities and parent stockholders equity close exactly and no nonzero NCI concept or member conflicts.')
    from .refresh_bridge_scope_policies import PREFERRED_EQUITY_ZERO_RULES
    preferred_zero_rule=PREFERRED_EQUITY_ZERO_RULES.get(ticker)
    if preferred_zero_rule is not None and str(cik).zfill(10)==preferred_zero_rule['cik'] and engines in ({'enterprise_cash_fcff'},{'constant_growth_fcff'}):
        policy['preferred_equity_zero_scope']=dict(preferred_zero_rule)
        policy['version']+='-PREFERRED-ZERO-SCOPE-1'
        policy['intentional_migration_changes'].append('Accept zero preferred equity only when current reported common components fully reconcile to parent equity and no nonzero preferred or temporary-equity evidence conflicts.')
    if ticker in {'ABT','COHR','WMB'} and engines=={'enterprise_cash_fcff'}:
        from .refresh_preferred_lifecycle import preferred_lifecycle_policy
        lifecycle=preferred_lifecycle_policy(ticker)
        if str(cik).zfill(10)!=lifecycle['cik']:
            raise RuntimeError('preferred lifecycle registry identity mismatch')
        policy['preferred_lifecycle_scope']=lifecycle
        policy['version']+='-PREFERRED-LIFECYCLE-1'
        policy['intentional_migration_changes'].append('Separate current issuer preferred or temporary equity from NCI and par-only disclosures; preserve settled conversion history without carrying a redeemed claim or adding conversion dilution twice.')
    if ticker in AUDITED_GROWTH_TICKERS and recipe is not None:
        growth_policy = compile_history_growth_policy(entry, recipe)
        if growth_policy['status'] != 'compiled':
            reasons.append('historical_growth_rule_not_reconciled_to_retained_generator')
            policy['history_growth_review'] = growth_policy
        else:
            policy['history_growth_policy'] = growth_policy
            policy['version'] += '-GROWTH-1'
            policy['fixed_assumptions'].pop('initial_growth', None)
            policy['fixed_assumptions'].pop('growth', None)
            field = 'initial_growth' if policy['supported_engine'] == 'enterprise_cash_fcff' else 'growth'
            for index, (case, statistic) in enumerate((('bear','low'),('base','base'),('bull','high'))):
                key = f'{case}_historical_growth'
                # Append after cash inputs, so the common history calculation
                # includes any issuer-specific total-investment adjustments.
                policy['inputs'][key] = {'selector':'cash_fcff_history','field':'revenue_growth',
                    'statistic':statistic,'normalization_version':CASH_HISTORY_VERSION}
                policy['scenario_bindings'][case][field] = {'max':[growth_policy['rule']['floors'][index],
                    {'min':[growth_policy['rule']['caps'][index], key]}]}
            policy['intentional_migration_changes'].append('Recompute history-derived revenue growth from each frozen source snapshot under the retained generator floors and caps; do not freeze the previous derived growth rate.')
    if ticker in {'BBY','DECK','DRI'} and recipe is not None:
        from .refresh_margin_stress import compile_margin_stress_policy
        stress = compile_margin_stress_policy(entry,recipe)
        if stress['status']!='compiled':
            reasons.append('governed_margin_stress_not_reconciled')
            policy['margin_stress_review'] = stress
        else:
            policy['margin_stress_policy'] = stress
            policy['version'] += '-MARGIN-STRESS-1'
            for index,case in enumerate(('bear','base','bull')):
                policy['scenario_bindings'][case]['fcff_margin'] = {'max':[stress['rule']['floor'],
                    {'subtract':[f'{case}_cash_margin',stress['rule']['scenario_rates'][index]]}]}
            policy['intentional_migration_changes'].append('Preserve the source-versioned scenario margin haircuts after cash history normalization; these are governed stresses, not reported working-capital adjustments.')
    status = "compiled_with_gaps" if reasons else "compiled_source_validation_pending"
    return PolicyCompileResult(ticker, cik, status, tuple(dict.fromkeys(reasons)), policy)


def compile_operating_policy_registry(
    *,
    registry_path: Path,
    artifacts_dir: Path,
    recipes_dir: Path,
    evidence_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Compile every frozen registry entry into proposal-only policy records."""

    registry = _json(registry_path)
    concept_config = load_concept_config()
    evidence = _json(evidence_path) if evidence_path else {}
    evidence_by_ticker = evidence.get("by_ticker", {}) if isinstance(evidence, Mapping) else {}
    if not isinstance(evidence_by_ticker, Mapping):
        evidence_by_ticker = {}
    results: list[dict[str, Any]] = []
    for entry in registry.get("entries", []):
        ticker = entry.get("ticker")
        artifact_path = Path(artifacts_dir) / f"{ticker}.json"
        recipe_path = Path(recipes_dir) / f"{ticker}.json"
        result = _policy_for_entry(
            entry,
            artifact=_json(artifact_path) if artifact_path.is_file() else None,
            recipe=_json(recipe_path) if recipe_path.is_file() else None,
            source_evidence=evidence_by_ticker.get(ticker),
            concept_config=concept_config,
        )
        results.append(result.as_dict())
    output = {
        "schema_version": COMPILER_SCHEMA,
        "production_ready": False,
        "auto_tune": False,
        "entry_count": len(results),
        "results": results,
    }
    if output_path is not None:
        Path(output_path).write_bytes((json.dumps(output, indent=2, sort_keys=True) + "\n").encode())
    return output


__all__ = ["COMPILER_SCHEMA", "PolicyCompileResult", "compile_operating_policy_registry"]
