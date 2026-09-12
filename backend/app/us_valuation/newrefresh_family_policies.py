"""Executable residual-income refresh family policies.

This module binds cached SEC packets to source-derived current inputs while
keeping approved scenario rates/payout/horizon assumptions fixed.  It does not
mutate the public catalog or silently turn missing preferred/NCI evidence into
zero; absence is accepted only with an explicit structural absence proof.
"""
from __future__ import annotations

from datetime import date, timedelta
from copy import deepcopy
import json
import hashlib
import re
from pathlib import Path
from typing import Any, Mapping

from .calculation_recipe import evaluate_recipe
from .calculation_recipe import number
from .refresh_policy_migration import SCHEMA as POLICY_SCHEMA
from .equity_fact_selection import annual_facts
from .xbrl import CompanyFactsNormalizer, SelectedFact, load_concept_config
from .history import HistoryObservation, summarize_history_metric
from .sec_client import normalize_cik
from .share_presentation_precision import SHARE_PRECISION_POLICY


RESIDUAL_POLICY_SCHEMA = "FINSIGHT-RESIDUAL-REFRESH-POLICY-1"
FLOW_CONCEPTS = ("NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss")
EQUITY_CONCEPTS = ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")
PREFERRED_CONCEPTS = ("PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount", "PreferredStockValue", "PreferredStocksIncludingAdditionalPaidInCapitalParOrStatedValue", "TemporaryEquityCarryingAmountAttributableToParent")
NCI_CONCEPTS = ("MinorityInterest", "NonredeemableNoncontrollingInterest", "NoncontrollingInterestInVariableInterestEntity")
SHARE_CONCEPTS = ("WeightedAverageNumberOfDilutedSharesOutstanding",)


def _is_preferred_investment_asset(row: Mapping[str, Any]) -> bool:
    """An investee's preferred security is not this issuer's preferred claim.

    Require explicit investment semantics plus structural investment-table
    ancestry. A merely preferred-labelled item still blocks reconciliation.
    """
    return (row.get('local_name') == 'PreferredStockInvestmentLiquidationValue'
            and 'us-gaap:SummaryOfInvestmentHoldingsTable' in row.get('presentation_ancestry', ())
            and 'balance_sheet' not in row.get('statement_roles', ()))


def _has_outstanding_preferred(structural, *, cik, accession, period):
    found = False
    for row in structural.get('facts', []):
        if (row.get('qname') != 'us-gaap:PreferredStockSharesOutstanding'
            or row.get('period_end') != period or row.get('period_start') is not None
            or row.get('unit') not in {'shares','xbrli:shares'}):
            continue
        if (str(row.get('entity_identifier','')).zfill(10) != normalize_cik(cik)
            or row.get('source_accession') != accession
            or row.get('entity_scheme') != 'http://www.sec.gov/CIK'):
            raise ValueError('preferred-share source identity mismatch')
        found = found or number(row['value'],'preferred shares outstanding') != 0
    return found


def reconcile_separate_common_equity(structural: Mapping[str, Any], *, cik: str, accession: str, period: str) -> dict:
    """Reconcile separately reported common stock and common APIC.

    The five explicit primary-statement components must explain all parent
    equity. Investments in another issuer's preferred shares are assets.
    No missing component or residual is filled with zero.
    """
    if not isinstance(structural, Mapping) or structural.get('source_accession') != accession:
        raise ValueError('common-equity structural packet is missing or mismatched')
    expected_cik = normalize_cik(cik)
    if expected_cik == '0000000000':
        raise ValueError('common-equity issuer identity is missing')
    rows = [row for row in structural.get('facts', []) if row.get('period_end') == period
            and row.get('period_start') is None and row.get('unit') == 'USD']
    if any(str(row.get('entity_identifier','')).zfill(10) != expected_cik
           or row.get('source_accession') != accession for row in rows):
        raise ValueError('common-equity source identity mismatch')
    if _has_outstanding_preferred(structural,cik=expected_cik,accession=accession,period=period):
        raise ValueError('outstanding preferred shares require economic claim reconciliation')
    for row in rows:
        if (any(token in str(row.get('local_name','')).lower() for token in ('preferredstock','preferredequity','temporaryequity'))
            and not _is_preferred_investment_asset(row) and number(row['value'],'preferred claim') != 0):
            raise ValueError('BRK nonzero preferred claim needs separate treatment')
    components = {}
    weights = {'CommonStockValue':1, 'AdditionalPaidInCapitalCommonStock':1,
               'RetainedEarningsAccumulatedDeficit':1, 'AccumulatedOtherComprehensiveIncomeLossNetOfTax':1,
               'TreasuryStockValue':-1, 'StockholdersEquity':0}
    aliases = {'TreasuryStockValue': ('TreasuryStockValue', 'TreasuryStockCommonValue')}
    for field in weights:
        accepted = aliases.get(field, (field,))
        facts = [row for row in rows if row.get('qname') in {'us-gaap:'+name for name in accepted}
                 and not row.get('dimensions') and 'balance_sheet' in row.get('statement_roles', [])]
        amounts = {number(row['value'],field) for row in facts}
        if len(amounts) != 1:
            raise ValueError('primary common-equity component missing or conflicting: '+field)
        components[field] = deepcopy(facts[0])
    total = components['StockholdersEquity']['value']
    if components['TreasuryStockValue']['value'] < 0 or abs(sum(components[k]['value']*w for k,w in weights.items())-total) > .01:
        raise ValueError('common-equity components do not reconcile to parent equity')
    return {'value':total, 'components':components, 'source_accession':accession,
            'period_end':period, 'preferred_status':'primary_common_components_reconciled'}


def reconcile_brk_common_equity(structural: Mapping[str, Any], *, accession: str, period: str) -> dict:
    return reconcile_separate_common_equity(structural, cik='0001067983', accession=accession, period=period)


def compile_residual_income_policy(recipe: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one existing residual recipe into a declarative refresh policy."""
    if not any(spec.get("engine") == "residual_income" for spec in recipe.get("scenarios", {}).values() if isinstance(spec, Mapping)):
        raise ValueError("recipe is not residual-income family")
    base = recipe["scenarios"]["base"]["inputs"]
    scenarios = {name: recipe["scenarios"][name]["inputs"] for name in ("bear", "base", "bull")}
    policy = {
        "schema_version": RESIDUAL_POLICY_SCHEMA,
        "version": f"{RESIDUAL_POLICY_SCHEMA}-{recipe.get('ticker')}" + ('-CLASS-BASIS-1' if recipe.get('ticker') in {'BRK.A','BRK.B'} else '') + '-SHARE-PRECISION-1',
        'share_precision_policy': SHARE_PRECISION_POLICY,
        "ticker": recipe.get("ticker"),
        "cik": registry_entry.get("cik"),
        "policy_status": "mapped_requires_source_reselection",
        "roe_history_basis": 'approved_post_combination_policy' if recipe.get('ticker') in {'FITB','HBAN'} else 'average_beginning_ending_common_equity',
        "engine": "residual_income",
        "baseline_binding": {
            "baseline_version": recipe.get("baseline_version"),
            "baseline_sha256": registry_entry.get("baseline_sha256"),
            "evidence_cutoff": recipe.get("evidence_cutoff"),
            "source_accession": recipe.get("source_accession") or (registry_entry.get("controlling_filing") or {}).get("accession"),
        },
        "inputs": {
            "common_equity": {"field": "common_equity", "selector": "instant", "required": True, "concepts": ("StockholdersEquity",)},
            "preferred_equity": {"field": "preferred_equity", "selector": "instant_reported_claim", "required": True, "concepts": PREFERRED_CONCEPTS},
            "noncontrolling_interests": {"field": "noncontrolling_interests", "selector": "instant_or_structural_absence", "required": True, "concepts": NCI_CONCEPTS},
            "common_earnings": {"field": "common_earnings", "selector": "ttm", "required": True, "concepts": FLOW_CONCEPTS},
            "diluted_shares": {"field": "diluted_shares", "selector": "current_reported_weighted_average", "required": True, "concepts": SHARE_CONCEPTS},
            "history_common_equity": {"field": "common_equity", "selector": "history_median", "required": True, "concepts": EQUITY_CONCEPTS},
            "history_common_earnings": {"field": "common_earnings", "selector": "history_median", "required": True, "concepts": FLOW_CONCEPTS},
        },
        # BRK's share classes are resolved together from the controlling
        # structural filing after financial selection, never classless shares.
        "statement_required_fields": {"common_equity": "instant", "common_earnings": "flow", **({} if recipe.get('ticker') in {'BRK.A','BRK.B'} else {"diluted_shares": "flow"})},
        "concept_config": {"fields": {
            "common_equity": {"concepts": ["StockholdersEquity"], "unit": "USD", "kind": "instant"},
            "common_earnings": {"concepts": list(FLOW_CONCEPTS), "unit": "USD", "kind": "flow"},
            "diluted_shares": {"concepts": list(SHARE_CONCEPTS), "unit": "shares", "kind": "flow"},
            "preferred_equity": {"concepts": list(PREFERRED_CONCEPTS), "unit": "USD", "kind": "instant"},
        }},
        "source_requirements": {"structural": True, "event_exhibits": True},
        "policy_assumptions": {
            "share_count_sensitivity": {'bear':1.015,'base':1.,'bull':.985} if recipe.get('ticker') in {'BRK.A','BRK.B'} else {'bear':1.,'base':1.,'bull':1.},
            "share_count_sensitivity_basis": 'Batch 37 approved +/-1.5 percent dilution sensitivity; source class-equivalent count stays locked' if recipe.get('ticker') in {'BRK.A','BRK.B'} else 'locked reported denominator',
            "cost_of_equity": {"classification": "approved_fixed_policy", "scenario_values": {name: scenarios[name]["cost_of_equity"] for name in scenarios}},
            "current_payout_ratio": {"classification": "approved_fixed_policy", "scenario_values": {name: scenarios[name]["current_payout_ratio"] for name in scenarios}},
            "terminal_roe": {"classification": "approved_fixed_policy", "scenario_values": {name: scenarios[name]["terminal_roe"] for name in scenarios}},
            "terminal_growth": {"classification": "approved_fixed_policy", "scenario_values": {name: scenarios[name]["terminal_growth"] for name in scenarios}},
            "forecast_years": {"classification": "approved_fixed_policy", "value": base.get("years", 5)},
            "current_roe": {"classification": "approved_fixed_policy_roe", "approved_fixed_policy_roe": base.get("current_roe"), "scenario_values": {name:scenarios[name]['current_roe'] for name in scenarios}, "formula": "source history median when 3-5 common-equity observations exist; otherwise retain approved case-specific ROE policy"},
            "book_value_per_share": {"classification": "source_bound", "formula": "common_equity / diluted_shares"},
        },
        "preferred_claim_rule": "reported preferred/temporary/redeemable claims are required; missing claims block binding",
        "source_lineage": {
            "batch": registry_entry.get("batch"),
            "source_audit": registry_entry.get("source_audit"),
            "controlling_filing": registry_entry.get("controlling_filing"),
        },
        "unresolved_economic_rules": [
            "refresh common-equity and earnings history before recomputing ROE",
            "revalidate preferred/NCI claims and capital/regulatory specialist overlays",
        ],
    }
    if recipe.get('ticker')=='APD' and str(registry_entry.get('cik','')).zfill(10)=='0000002969':
        from .refresh_nci_ownership_claims import nci_ownership_claim_policy
        policy['nci_ownership_policy']=nci_ownership_claim_policy('APD')
        policy['version']+='-NCI-OWNERSHIP-1'
    return policy


def reconcile_common_equity_components(structural_packet: Mapping[str, Any], *, cik: str, accession: str, period_end: str) -> dict[str, Any]:
    """Reconcile parent equity from dimensioned components with hard identity checks."""
    if structural_packet.get("source_accession") != accession:
        raise ValueError("structural equity packet accession mismatch")
    if isinstance(cik, bool) or not str(cik).isdigit() or len(str(cik)) > 10:
        raise ValueError('invalid issuer CIK')
    digits = str(cik).zfill(10)
    facts = structural_packet.get("facts")
    if not digits or not isinstance(facts, list) or not facts:
        raise ValueError("structural equity packet identity/facts are incomplete")
    if _has_outstanding_preferred(structural_packet,cik=digits,accession=accession,period=period_end):
        raise ValueError('outstanding preferred shares block a zero common-equity claim proof')
    relevant = [row for row in facts if isinstance(row, Mapping) and row.get("source_accession", accession) == accession and row.get("period_end") == period_end and row.get("period_start") is None and row.get("unit") == "USD" and row.get("dimensions") is not None]
    if any(not str(row.get('entity_identifier', '')).isdigit() or str(row['entity_identifier']).zfill(10) != digits for row in relevant):
        raise ValueError("structural equity packet CIK identity mismatch")
    members = {
        "CommonStockMember": "common_stock",
        "AdditionalPaidInCapitalMember": "additional_paid_in_capital",
        "RetainedEarningsMember": "retained_earnings",
        "AccumulatedOtherComprehensiveIncomeMember": "accumulated_other_comprehensive_income",
        "TreasuryStockCommonMember": "treasury_stock",
    }
    selected: dict[str, Mapping[str, Any]] = {}
    unknown_components = []
    aoci_detail_values = {}
    aoci_detail_members = {'us-gaap:AccumulatedTranslationAdjustmentMember',
        'us-gaap:AccumulatedNetUnrealizedInvestmentGainLossMember',
        'us-gaap:AccumulatedGainLossNetCashFlowHedgeParentMember',
        'us-gaap:AociLiabilityForFuturePolicyBenefitParentMember',
        'us-gaap:AccumulatedDefinedBenefitPlansAdjustmentMember'}
    for row in relevant:
        if row.get("qname") != "us-gaap:StockholdersEquity":
            continue
        dimensions = row.get("dimensions") or []
        if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 1:
            continue
        dimension = dimensions[0]
        if not isinstance(dimension, (list, tuple)) or len(dimension) != 2 or dimension[0] != 'us-gaap:StatementEquityComponentsAxis':
            continue
        member = dimension[1].removeprefix('us-gaap:') if isinstance(dimension[1], str) and dimension[1].startswith('us-gaap:') else None
        key = members.get(member or "")
        if key is None:
            if dimension[1] in aoci_detail_members:
                value = number(row['value'],'AOCI detail')
                if dimension[1] in aoci_detail_values and aoci_detail_values[dimension[1]] != value:
                    raise ValueError('conflicting AOCI subcomponent values')
                aoci_detail_values[dimension[1]] = value
                continue
            unknown_components.append(dimension[1])
            continue
        prior = selected.get(key)
        if prior is not None and prior.get("value") != row.get("value"):
            raise ValueError(f"conflicting equity component {key}")
        selected[key] = row
    if set(selected) != set(members.values()):
        # Some primary statements report common stock and common-only APIC
        # separately without a full dimensional component roll-forward.
        try:
            return reconcile_separate_common_equity(structural_packet, cik=digits, accession=accession, period=period_end)
        except ValueError:
            pass
        return reconcile_common_equity_statement(structural_packet, cik=cik, accession=accession, period_end=period_end)
    if unknown_components:
        raise ValueError('unknown equity component prevents complete common-equity proof: ' + ', '.join(sorted(set(unknown_components))))
    if aoci_detail_values and abs(sum(aoci_detail_values.values()) - number(selected['accumulated_other_comprehensive_income']['value'],'AOCI total')) > .01:
        raise ValueError('AOCI subcomponents do not reconcile to common-equity AOCI')
    total_rows = [row for row in relevant if row.get('qname') == 'us-gaap:StockholdersEquity' and not row.get('dimensions')]
    if not total_rows:
        raise ValueError("undimensioned stockholders equity total is missing")
    totals = {number(row['value'], 'parent equity') for row in total_rows}
    if len(totals) != 1: raise ValueError('conflicting parent equity totals')
    total = totals.pop()
    component_sum = sum(number(row['value'], 'common equity component') for row in selected.values())
    rounding = None
    if digits == '0001383312':
        from .reported_precision import reconcile_reported_sum
        rounding = reconcile_reported_sum(total_rows[0], list(selected.values()), cik=digits, accession=accession, period=period_end)
    elif abs(component_sum - total) > 0.01:
        raise ValueError("common-equity component sum does not reconcile to parent total")
    apic = [row for row in relevant if row.get('qname') == 'us-gaap:AdditionalPaidInCapitalCommonStock' and not row.get('dimensions')]
    if digits == '0001383312' and not apic:
        # BR reports a complete common-only component table plus explicit zero
        # preferred carrying value; corroborate its generic APIC tag only here.
        preferred = [row for row in relevant if row.get('qname') == 'us-gaap:PreferredStockValue' and not row.get('dimensions')]
        if not preferred or {number(row['value'],'preferred') for row in preferred} != {0.}:
            raise ValueError('BR generic APIC requires reported zero preferred carrying value')
        apic = [row for row in relevant if row.get('qname') == 'us-gaap:AdditionalPaidInCapital' and not row.get('dimensions')]
    if not apic or {number(row['value'], 'common APIC') for row in apic} != {number(selected['additional_paid_in_capital']['value'], 'APIC')}:
        raise ValueError("common-only APIC corroboration is missing or inconsistent")
    preferred_nonzero = [row for row in relevant if not _is_preferred_investment_asset(row) and any(token.lower() in str(row.get("local_name", "")).lower() for token in ("preferredstock", "preferredequity", "temporaryequity")) and isinstance(row.get("value"), (int, float)) and float(row["value"]) != 0]
    if preferred_nonzero:
        raise ValueError("reported nonzero preferred claim blocks component-only common equity")
    return {"value": total, "components": {key: {"value": float(row["value"]), "local_name": row["local_name"], "dimensions": row.get("dimensions")} for key, row in selected.items()}, "rounding_reconciliation":rounding, "validated_aoci_subcomponents": aoci_detail_values, "source_accession": accession, "period_end": period_end, "preferred_status": "component_reconciliation_proved_absent"}


def reconcile_common_equity_statement(structural_packet: Mapping[str, Any], *, cik: str, accession: str, period_end: str) -> dict[str, Any]:
    """Reconcile a common-only primary statement to reported parent equity.

    Some issuers combine common stock and APIC instead of publishing the five
    dimensioned members. Every component used here must be actually reported;
    an absent preferred-stock tag is never itself the proof.
    """
    if structural_packet.get('source_accession') != accession:
        raise ValueError('structural equity packet accession mismatch')
    metadata = dict(structural_packet.get('filing_metadata', ()))
    if metadata.get('manifest_version') != 'FINSIGHT-XBRL-PACKAGE-1' or not metadata.get('package_generation'):
        raise ValueError('complete structural filing package receipt is required')
    expected_cik = normalize_cik(cik)
    rows = [row for row in structural_packet.get('facts', []) if isinstance(row, Mapping)
            and row.get('period_end') == period_end and row.get('period_start') is None]
    for row in rows:
        if normalize_cik(row.get('entity_identifier', '')) != expected_cik or row.get('source_accession', accession) != accession:
            raise ValueError('structural equity packet CIK or accession mismatch')
        name = str(row.get('qname') or row.get('local_name', '')).lower()
        if not _is_preferred_investment_asset(row) and any(token in name for token in ('preferredstock', 'preferredequity', 'temporaryequity')):
            monetary_claim = row.get('unit') == 'USD'
            outstanding_shares = row.get('unit') in {'shares','xbrli:shares'} and 'outstanding' in name
            if (monetary_claim or outstanding_shares) and number(row.get('value'), 'preferred claim') != 0:
                raise ValueError('reported nonzero preferred claim blocks common-equity proof')
    selected = {}
    for field in ('StockholdersEquity','CommonStocksIncludingAdditionalPaidInCapital','RetainedEarningsAccumulatedDeficit','AccumulatedOtherComprehensiveIncomeLossNetOfTax'):
        facts = [row for row in rows if row.get('qname') == f'us-gaap:{field}' and row.get('unit') == 'USD'
                 and not row.get('dimensions') and 'balance_sheet' in row.get('statement_roles', [])]
        values = {number(row['value'], field) for row in facts}
        if len(values) != 1:
            raise ValueError('complete common-equity component set is missing or conflicting')
        selected[field] = {'value':values.pop(),'source_accession':accession,'period_end':period_end,'qname':f'us-gaap:{field}'}
    component_fields = {
        'us-gaap:CommonStockIncludingAdditionalPaidInCapitalMember':'CommonStocksIncludingAdditionalPaidInCapital',
        'us-gaap:RetainedEarningsMember':'RetainedEarningsAccumulatedDeficit',
        'us-gaap:AccumulatedOtherComprehensiveIncomeMember':'AccumulatedOtherComprehensiveIncomeLossNetOfTax',
        'us-gaap:TreasuryStockCommonMember':'TreasuryStockValue',
    }
    components = {}
    aoci_details = {}
    aoci_members = {'us-gaap:AccumulatedGainLossNetCashFlowHedgeParentMember',
                    'us-gaap:AccumulatedNetUnrealizedInvestmentGainLossMember'}
    if expected_cik == '0000789019':
        for namespace in {str(row.get('namespace','')) for row in structural_packet.get('facts', [])}:
            if re.fullmatch(r'http://www\.microsoft\.com/\d{8}',namespace):
                prefix = 'ns_' + hashlib.sha1(namespace.encode()).hexdigest()[:10]
                aoci_members.add(prefix + ':AccumulatedTranslationAdjustmentAndOtherMember')
    for row in rows:
        if row.get('qname') != 'us-gaap:StockholdersEquity' or not row.get('dimensions') or row.get('unit') != 'USD':
            continue
        dimensions = row['dimensions']
        if (not isinstance(dimensions, (list,tuple)) or len(dimensions) != 1
            or not isinstance(dimensions[0], (list,tuple)) or len(dimensions[0]) != 2
            or dimensions[0][0] != 'us-gaap:StatementEquityComponentsAxis'):
            raise ValueError('unknown or incomplete common-equity component set is missing a scope rule')
        if dimensions[0][1] in aoci_members:
            member = dimensions[0][1]
            amount = number(row['value'],'AOCI detail')
            if member in aoci_details and aoci_details[member] != amount:
                raise ValueError('conflicting AOCI subcomponent values')
            aoci_details[member] = amount
            continue
        if dimensions[0][1] not in component_fields:
            raise ValueError('unknown or incomplete common-equity component set is missing a scope rule')
        field = component_fields[dimensions[0][1]]
        amount = number(row['value'], field)
        if field in components and components[field] != amount:
            raise ValueError('conflicting common-equity component values')
        components[field] = amount
    for field in tuple(component_fields.values())[:3]:
        if components.get(field) != selected[field]['value']:
            raise ValueError('complete common-equity component set is missing or does not match the balance sheet')
    if aoci_details and abs(sum(aoci_details.values()) - selected['AccumulatedOtherComprehensiveIncomeLossNetOfTax']['value']) > .01:
        raise ValueError('AOCI subcomponents do not reconcile to the parent AOCI amount')
    treasury = [row for row in rows if row.get('qname') == 'us-gaap:TreasuryStockValue' and row.get('unit') == 'USD'
                and not row.get('dimensions') and 'balance_sheet' in row.get('statement_roles', [])]
    if treasury:
        amounts = {number(row['value'], 'treasury stock') for row in treasury}
        if len(amounts) != 1 or min(amounts) < 0:
            raise ValueError('treasury-stock carrying value is inconsistent')
        selected['TreasuryStockValue'] = {'value':amounts.pop(),'source_accession':accession,'period_end':period_end,'qname':'us-gaap:TreasuryStockValue'}
        if components.get('TreasuryStockValue') != -selected['TreasuryStockValue']['value']:
            raise ValueError('signed treasury-stock component does not reconcile')
    elif components.get('TreasuryStockValue', 0.) != 0.:
        raise ValueError('treasury-stock component has no matching balance-sheet claim')
    total = selected['StockholdersEquity']['value']
    common = sum(selected[field]['value'] for field in ('CommonStocksIncludingAdditionalPaidInCapital','RetainedEarningsAccumulatedDeficit','AccumulatedOtherComprehensiveIncomeLossNetOfTax'))
    if treasury:
        common -= selected['TreasuryStockValue']['value']
    if abs(common - total) > .01:
        raise ValueError('common-equity statement components do not reconcile to parent equity')
    return {'value':total,'components':selected,'source_accession':accession,'period_end':period_end,
            'validated_aoci_subcomponents':aoci_details,
            'preferred_status':'component_reconciliation_proved_absent',
            'method':'reported common stock plus APIC, retained earnings and AOCI, less separately reported treasury stock, reconcile to parent equity'}


def reconcile_no_outside_equity_claim(structural_packet: Mapping[str, Any], *, cik: str, accession: str, period_end: str) -> dict[str, Any]:
    """Prove the consolidated balance sheet closes with common parent equity.

    Use the exhaustive common-equity table as a prerequisite and reject any
    disclosed offsetting NCI/temporary/preferred claim, including negative NCI.
    """
    metadata = dict(structural_packet.get('filing_metadata', ()))
    if metadata.get('manifest_version') != 'FINSIGHT-XBRL-PACKAGE-1' or not metadata.get('package_generation'):
        raise ValueError('complete structural filing package receipt is required')
    common = reconcile_common_equity_components(structural_packet,cik=cik,accession=accession,period_end=period_end)
    rows = [row for row in structural_packet['facts'] if row.get('period_end') == period_end and row.get('period_start') is None and row.get('unit') == 'USD']
    for row in rows:
        name = str(row.get('qname', '')).lower()
        if any(token in name for token in ('noncontrollinginterest','minorityinterest','temporaryequity','preferredstock','preferredequity')) and number(row['value'],'outside equity claim') != 0:
            raise ValueError('nonzero outside equity claim prevents a zero-NCI reconciliation')
        dimensions = row.get('dimensions') or []
        allowed_members = {'CommonStockMember','CommonStockIncludingAdditionalPaidInCapitalMember','AdditionalPaidInCapitalMember',
            'RetainedEarningsMember','AccumulatedOtherComprehensiveIncomeMember','TreasuryStockCommonMember',
            'AccumulatedTranslationAdjustmentMember','AccumulatedNetUnrealizedInvestmentGainLossMember',
            'AccumulatedGainLossNetCashFlowHedgeParentMember','AccumulatedDefinedBenefitPlansAdjustmentMember'}
        if row.get('qname') == 'us-gaap:StockholdersEquity' and dimensions:
            if (len(dimensions) == 1 and isinstance(dimensions[0],(list,tuple)) and len(dimensions[0]) == 2
                and dimensions[0][0] == 'us-gaap:StatementEquityComponentsAxis'
                and dimensions[0][1] in common.get('validated_aoci_subcomponents', {})):
                continue
            if (len(dimensions) != 1 or not isinstance(dimensions[0], (list,tuple)) or len(dimensions[0]) != 2
                or dimensions[0][0] != 'us-gaap:StatementEquityComponentsAxis'
                or dimensions[0][1] not in {f'us-gaap:{member}' for member in allowed_members}):
                raise ValueError('unknown equity component prevents a zero-NCI reconciliation')
    totals = {}
    total_sources = {}
    for field in ('Assets','Liabilities','LiabilitiesAndStockholdersEquity'):
        matches = [row for row in rows if row.get('qname') == f'us-gaap:{field}' and not row.get('dimensions') and 'balance_sheet' in row.get('statement_roles', [])]
        amounts = {number(row['value'],field) for row in matches}
        if len(amounts) != 1:
            raise ValueError('complete consolidated balance-sheet totals are missing or conflicting')
        totals[field] = amounts.pop()
        total_sources[field] = matches[0]
    rounding = None
    if normalize_cik(cik) == '0001383312':
        from .reported_precision import reconcile_reported_sum
        equity_rows = [row for row in rows if row.get('qname') == 'us-gaap:StockholdersEquity' and not row.get('dimensions') and 'balance_sheet' in row.get('statement_roles', [])]
        rounding = reconcile_reported_sum(total_sources['Assets'], [total_sources['Liabilities'], equity_rows[0]], cik=normalize_cik(cik), accession=accession, period=period_end)
    if abs(totals['Assets']-totals['LiabilitiesAndStockholdersEquity']) > .01 or (rounding is None and abs(totals['Assets']-totals['Liabilities']-common['value']) > .01):
        raise ValueError('consolidated balance sheet does not close with common parent equity')
    return {'value':0.,'source_accession':accession,'period_end':period_end,'common_equity':common,'balance_totals':totals,'rounding_reconciliation':rounding,
            'method':'component-and-balance reconciliation; no missing-tag zero inference'}


def bind_residual_income_sources(policy: Mapping[str, Any], packet: Mapping[str, Any], *, structural_packet: Mapping[str, Any] | None, cutoff: str) -> dict[str, Any]:
    """Bind using the shared period-aware CompanyFactsNormalizer selectors."""
    submissions, companyfacts = packet["submissions"], packet["companyfacts"]
    policy_cik = normalize_cik(policy.get('cik', ''))
    submission_cik = normalize_cik(submissions.get('cik', ''))
    facts_cik = normalize_cik(companyfacts.get('cik', ''))
    if policy_cik == '0000000000' or submission_cik != policy_cik or facts_cik != policy_cik:
        raise ValueError("residual refresh packet CIK identity mismatch")
    recent = submissions.get("filings", {}).get("recent", {})
    filing_rows = [{key: values[i] for key, values in recent.items() if isinstance(values, list) and i < len(values)} for i in range(len(recent.get("accessionNumber", [])))]
    eligible = [row for row in filing_rows if row.get("form") in {"10-K", "10-K/A", "10-Q", "10-Q/A"} and row.get("filingDate", "") <= cutoff and row.get("reportDate")]
    if not eligible:
        raise ValueError("no eligible residual-income filing")
    selected_filing = packet.get("_selected_controlling_filing")
    if not isinstance(selected_filing, Mapping):
        raise ValueError("main filing selector must provide _selected_controlling_filing")
    filing = next((row for row in eligible if row.get("accessionNumber") == selected_filing.get("accession") and row.get("reportDate") == selected_filing.get("period_end")), None)
    if filing is None:
        raise ValueError("selected controlling filing is not an eligible cached submission")
    period = filing["reportDate"]
    config = load_concept_config()
    config.setdefault("fields", {}).update({
        "common_equity": {"unit": "USD", "kind": "instant", "concepts": ["StockholdersEquity"]},
        "common_earnings": {"unit": "USD", "kind": "flow", "concepts": list(FLOW_CONCEPTS)},
        "diluted_shares": {"unit": "shares", "kind": "flow", "concepts": list(SHARE_CONCEPTS)},
        "preferred_equity": {"unit": "USD", "kind": "instant", "concepts": list(PREFERRED_CONCEPTS)},
    })
    config['fields'].update(policy.get('concept_config', {}).get('fields', {}))
    structural_supplements = {}
    from .concept_resolver import load_structural_rules
    official_namespaces = set(load_structural_rules()['official_us_gaap_namespaces'])
    normalized_facts = deepcopy(companyfacts)
    supplement_trace = []
    share_precision_trace = {}
    if isinstance(structural_packet,Mapping) and structural_packet.get('source_accession') == filing['accessionNumber']:
        allowed_concepts = {name.split(':',1)[-1] for field in ('common_equity','common_earnings','preferred_equity','diluted_shares')
            for name in config['fields'][field]['concepts'] if ':' not in name or name.startswith('us-gaap:')}
        for row in structural_packet.get('facts',[]):
            local = row.get('local_name')
            if (local not in allowed_concepts or row.get('qname') != 'us-gaap:'+str(local)
                or row.get('namespace') not in official_namespaces or row.get('source_accession') != filing['accessionNumber']
                or str(row.get('entity_identifier','')).zfill(10) != policy_cik or row.get('entity_scheme') != 'http://www.sec.gov/CIK'
                or row.get('dimensions') != [] or row.get('unit') not in {'USD','shares','xbrli:shares'}
                or not row.get('period_end') or row['period_end'] > period):
                continue
            amount = number(row['value'],'current structural supplement')
            unit = 'shares' if row['unit'] == 'xbrli:shares' else row['unit']
            rows = normalized_facts.setdefault('facts',{}).setdefault('us-gaap',{}).setdefault(local,{}).setdefault('units',{}).setdefault(unit,[])
            existing = [item for item in rows if item.get('accn') == filing['accessionNumber']
                and item.get('start') == row.get('period_start') and item.get('end') == row['period_end']]
            if existing:
                if any(number(item['val'],'CompanyFacts supplement corroboration') != amount for item in existing):
                    if local not in SHARE_CONCEPTS or unit != 'shares' or policy.get('share_precision_policy') != SHARE_PRECISION_POLICY:
                        raise ValueError('CompanyFacts/structural amount conflict for '+local)
                    from .share_presentation_precision import reconcile_share_presentations
                    siblings = [item for item in structural_packet['facts']
                        if item.get('qname') == row['qname'] and item.get('dimensions') == []
                        and item.get('period_start') == row.get('period_start') and item.get('period_end') == row['period_end']]
                    try:
                        proof = reconcile_share_presentations(siblings,existing,cik=policy_cik,
                            accession=filing['accessionNumber'],start=row.get('period_start'),end=row['period_end'],concept=row['qname'])
                    except ValueError as exc:
                        raise ValueError('CompanyFacts/structural amount conflict for '+local+': '+str(exc)) from exc
                    # Mutate only the private normalized copy. Preserve every
                    # original presentation in the corroboration evidence.
                    rows[:] = [item for item in rows if item not in existing or number(item['val'],'corroborated shares')==proof['value']]
                    key = (row['qname'],row.get('period_start'),row['period_end'])
                    share_precision_trace.setdefault(key,proof)
                continue
            item = {'val':amount,'end':row['period_end'],'accn':filing['accessionNumber'],
                'form':filing['form'],'filed':filing['filingDate']}
            if row.get('period_start') is not None:
                item['start'] = row['period_start']
            rows.append(item)
            supplement_trace.append({'concept':row['qname'],'namespace':row['namespace'],'cik':policy_cik,
                'source_accession':filing['accessionNumber'],'period_start':row.get('period_start'),
                'period_end':row['period_end'],'unit':unit,'value':amount,'context_id':row.get('context_id'),
                'source_kind':'structural_xbrl','labels':row.get('labels',[])})
    structural_supplements['added_facts'] = supplement_trace
    structural_supplements['corroborated_share_precision'] = list(share_precision_trace.values())
    nci_ownership=None
    if policy.get('nci_ownership_policy'):
        if not isinstance(structural_packet,Mapping):
            raise ValueError('NCI ownership policy requires the current structural filing')
        from .refresh_nci_ownership_claims import select_nci_ownership_claim
        nci_ownership=select_nci_ownership_claim(
            policy['nci_ownership_policy'],structural_packet,filing,policy_cik,cutoff)
        if nci_ownership['status']!='source_bound':
            raise ValueError('residual-income NCI ownership scope requires review: '+', '.join(nci_ownership['review_reasons']))
    normalizer = CompanyFactsNormalizer(normalized_facts, concept_config=config, fiscal_year_end=submissions.get("fiscalYearEnd"), as_of_date=cutoff, filing_records=filing_rows)
    def current_instant(field):
        selected = normalizer.instant(field,end=period)
        if selected is not None and selected.accession == filing['accessionNumber']:
            return selected
        if not isinstance(structural_packet,Mapping) or structural_packet.get('source_accession') != filing['accessionNumber']:
            return selected
        for concept in config['fields'][field]['concepts']:
            qname = concept if ':' in concept else 'us-gaap:'+concept
            if not qname.startswith('us-gaap:'):
                continue
            rows = [row for row in structural_packet.get('facts',[]) if row.get('qname') == qname
                and row.get('namespace') in official_namespaces
                and row.get('source_accession') == filing['accessionNumber'] and row.get('period_end') == period
                and row.get('period_start') is None and row.get('unit') == 'USD' and row.get('dimensions') == []
                and row.get('entity_scheme') == 'http://www.sec.gov/CIK'
                and str(row.get('entity_identifier','')).zfill(10) == policy_cik]
            if not rows:
                continue
            values = {number(row['value'],field) for row in rows}
            if len(values) != 1:
                raise ValueError(f'conflicting current structural {field} facts')
            row = rows[0]
            structural_supplements[field] = {'source_accession':filing['accessionNumber'],'qname':qname,
                'period_end':period,'unit':'USD','value':values.copy().pop(),'context_ids':sorted({r.get('context_id','') for r in rows}),
                'cik':policy_cik,'source_kind':'structural_xbrl'}
            return SelectedFact(field=field,namespace='us-gaap',concept=qname.split(':',1)[1],unit='USD',value=values.pop(),
                start=None,end=period,accession=filing['accessionNumber'],form=filing['form'],filed=filing['filingDate'],
                fiscal_year=None,fiscal_period=None,frame=None,selection_reason='Exact current structural fact supplements missing CompanyFacts coverage.')
        return selected
    equity = current_instant("common_equity")
    if equity is None:
        raise ValueError("common equity is missing from selected controlling filing")
    if equity.accession != filing['accessionNumber']:
        raise ValueError('current equity source is not the controlling filing')
    if equity.concept != 'StockholdersEquity' or equity.namespace != 'us-gaap':
        raise ValueError('residual-income book value requires explicitly parent-scoped equity')
    earnings = normalizer.ttm_flow("common_earnings")
    if any(row.get('namespace') != 'us-gaap' or row.get('concept') not in FLOW_CONCEPTS for row in earnings.get('sources', [])):
        raise ValueError('residual-income earnings must be explicitly parent or common attributable')
    if policy.get('ticker') in {'BRK.A', 'BRK.B'} or policy_cik == '0001067983':
        from .refresh_share_basis import resolve_class_equivalent_share_basis
        basis = resolve_class_equivalent_share_basis(
            structural_packet, ticker=policy.get('ticker'),
            selected_class=str(policy.get('ticker')).split('.')[-1], cik=policy_cik,
            accession=filing['accessionNumber'], report_period_end=period,
            filing_date=filing['filingDate'], cutoff=cutoff,
        )
        shares = {'value': basis['value'], 'source': basis, 'method': basis['source_kind']}
    else:
        candidates = [item for item in normalizer._candidates('diluted_shares')
            if item[0] == 'us-gaap' and item[1] in SHARE_CONCEPTS and item[2] == 'shares'
            and item[3].get('accn') == filing['accessionNumber'] and item[3].get('end') == period
            and item[3].get('start') and 1 <= (date.fromisoformat(period)-date.fromisoformat(item[3]['start'])).days+1 <= 385]
        if candidates:
            start = min(item[3]['start'] for item in candidates)
            candidates = [item for item in candidates if item[3]['start'] == start]
            if len({number(item[3]['val'],'reported shares') for item in candidates}) != 1:
                raise ValueError('conflicting current reported diluted shares')
            selected = normalizer._selected('diluted_shares',candidates[0],'Longest current reported FY/YTD duration; no prior-year share pair is required.')
            shares = {'value':selected.value,'source':selected.as_dict(),'method':'current_reported_weighted_average'}
        elif isinstance(structural_packet,Mapping):
            rows = [row for row in structural_packet.get('facts',[]) if row.get('qname') == 'us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding'
                and row.get('namespace') in official_namespaces and row.get('source_accession') == filing['accessionNumber']
                and str(row.get('entity_identifier','')).zfill(10) == policy_cik and row.get('entity_scheme') == 'http://www.sec.gov/CIK'
                and row.get('period_end') == period and row.get('unit') in {'shares','xbrli:shares'} and row.get('dimensions') == []
                and row.get('period_start') and 1 <= (date.fromisoformat(period)-date.fromisoformat(row['period_start'])).days+1 <= 385]
            if not rows:
                raise ValueError('current diluted shares missing from CompanyFacts and structural filing')
            start = min(row['period_start'] for row in rows)
            rows = [row for row in rows if row['period_start'] == start]
            values = {number(row['value'],'structural diluted shares') for row in rows}
            if len(values) != 1:
                raise ValueError('conflicting current structural diluted shares')
            shares = {'value':values.pop(),'source':{'end':period,'start':start,'accession':filing['accessionNumber'],
                'qname':'us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding','unit':'shares','cik':policy_cik,
                'context_ids':sorted({row.get('context_id','') for row in rows})},'method':'current_structural_weighted_average'}
        else:
            raise ValueError('current reported diluted shares are missing')
        if shares['source']['end'] != period or shares['source']['accession'] != filing['accessionNumber']:
            raise ValueError('current reported share period/accession is inconsistent')
    if earnings['period_end'] != period:
        raise ValueError('current earnings or reported share period/accession is inconsistent')
    continuity = None
    pref = current_instant("preferred_equity")
    if pref is None:
        if structural_packet is None:
            raise ValueError("preferred claim is unresolved; reported claim or component reconciliation is required")
        if policy_cik == '0001067983':
            equity_components = reconcile_brk_common_equity(structural_packet, accession=filing['accessionNumber'], period=period)
        else:
            equity_components = reconcile_common_equity_components(structural_packet, cik=str(companyfacts.get("cik", "")), accession=filing["accessionNumber"], period_end=period)
        preferred_value, preferred_status = 0.0, equity_components["preferred_status"]
    else:
        if pref.accession != filing['accessionNumber']:
            raise ValueError('current preferred claim is not from controlling filing')
        preferred_value, preferred_status = float(pref.value), "reported"
        if preferred_value == 0 and isinstance(structural_packet, Mapping):
            # A zero par-value tag does not prove the economic preferred
            # claim is zero. MET reports outstanding preferred series this way.
            outstanding = [row for row in structural_packet.get('facts', [])
                if row.get('qname') == 'us-gaap:PreferredStockSharesOutstanding'
                and row.get('source_accession') == filing['accessionNumber']
                and str(row.get('entity_identifier','')).zfill(10) == policy_cik
                and row.get('period_end') == period and row.get('period_start') is None
                and row.get('unit') in {'shares','xbrli:shares'}
                and number(row.get('value'),'preferred shares outstanding') > 0]
            if outstanding:
                if policy.get('ticker') == 'MET' and policy_cik == '0001099219':
                    from .refresh_preferred_claims import met_preferred_claim
                    continuity = met_preferred_claim(structural_packet, accession=filing['accessionNumber'], period=period, cutoff=cutoff)
                    preferred_value, preferred_status = continuity['value'], continuity['status']
                else:
                    raise ValueError('zero preferred carrying/par value conflicts with outstanding preferred shares; economic claim reconciliation required')
    common_equity = float(equity.value) - preferred_value
    if pref is None:
        common_equity = equity_components["value"]
    if common_equity <= 0 or number(shares['value'], 'reported diluted shares') <= 0:
        raise ValueError('residual-income model needs positive common equity and shares')
    if preferred_value != 0 and any(row.get('concept') != 'NetIncomeLossAvailableToCommonStockholdersBasic' for row in earnings.get('sources', [])):
        raise ValueError('preferred claims require earnings explicitly attributable to common shareholders')
    earnings_history = normalizer.annual_series("common_earnings", 5)
    roe_history = []
    for fact in earnings_history:
        equity_history_fact = normalizer.instant('common_equity', end=fact.end)
        preferred_history_fact = normalizer.instant('preferred_equity', end=fact.end)
        beginning_end = (date.fromisoformat(fact.start) - timedelta(days=1)).isoformat()
        beginning_equity_fact = normalizer.instant('common_equity', end=beginning_end)
        beginning_preferred_fact = normalizer.instant('preferred_equity', end=beginning_end)
        # Historical parent equity is not automatically common equity. Missing
        # preferred history cannot be filled from today's zero or current amount.
        if any(item is None for item in (equity_history_fact,preferred_history_fact,beginning_equity_fact,beginning_preferred_fact)):
            continue
        historical_common = equity_history_fact.value - preferred_history_fact.value
        beginning_common = beginning_equity_fact.value - beginning_preferred_fact.value
        if min(historical_common,beginning_common) <= 0: continue
        if (preferred_history_fact.value != 0 or beginning_preferred_fact.value != 0) and fact.concept != 'NetIncomeLossAvailableToCommonStockholdersBasic':
            continue
        average_common = (beginning_common + historical_common) / 2
        roe_history.append({'fiscal_year':fact.fiscal_year, 'period_end':fact.end, 'earnings':fact.value,
            'common_equity':historical_common,'beginning_common_equity':beginning_common,'average_common_equity':average_common,
            'roe':fact.value/average_common,'roe_denominator_basis':'average_beginning_ending_common_equity',
            'earnings_source':fact.as_dict(),'equity_source':equity_history_fact.as_dict(),'preferred_source':preferred_history_fact.as_dict(),
            'beginning_equity_source':beginning_equity_fact.as_dict(),'beginning_preferred_source':beginning_preferred_fact.as_dict()})
    roe_range = None
    if len(roe_history) < 3 or continuity is not None or policy.get('roe_history_basis') == 'approved_post_combination_policy':
        fixed_roe = policy.get("policy_assumptions", {}).get("current_roe", {}).get("approved_fixed_policy_roe")
        if not isinstance(fixed_roe, (int, float)):
            raise ValueError("fewer than three aligned annual parent-common ROE observations and no approved fixed ROE policy")
        current_roe = float(fixed_roe)
        roe_status = "approved_fixed_policy"
    else:
        observations = tuple(HistoryObservation(period_role='annual',period_end=row['period_end'],fiscal_year=row['fiscal_year'],
            value=row['roe'],unit='ratio',formula='annual common earnings / average beginning and ending common equity',
            sources=(row['earnings_source'],row['equity_source'],row['preferred_source'],row['beginning_equity_source'],row['beginning_preferred_source'])) for row in roe_history[-5:])
        metric = summarize_history_metric('common_roe',observations)
        if metric is None: raise ValueError('common ROE history did not produce a metric')
        roe_range = {'bear':metric.low,'base':metric.base,'bull':metric.high}
        current_roe = metric.base
        roe_status = "annual_parent_common_history_median"
    return {
        "status": "bound_successor_candidate",
        "ticker": policy.get("ticker"),
        "controlling_filing": {"accession": filing["accessionNumber"], "filed_date": filing.get("filingDate"), "period_end": period, "form": filing.get("form")},
        "inputs": {"common_equity": common_equity, "preferred_equity": preferred_value, "common_earnings_ttm": earnings["value"], "diluted_shares": shares["value"], "book_value_per_share": common_equity / shares["value"], "current_roe": current_roe},
        "claim_status": {"preferred_equity": preferred_status, "noncontrolling_interests": "parent_scoped_equity_and_parent_or_common_earnings_no_second_deduction",
            "nci_ownership_scope":nci_ownership},
        "roe_range": roe_range,
        "source_rows": {"equity": equity.as_dict(), "equity_components": equity_components if pref is None else None, "earnings": earnings, "shares": shares, "roe_history": roe_history, "preferred_continuity": continuity, "structural_supplements":structural_supplements,"nci_ownership_scope":nci_ownership},
        "source_ledger": {"selected_controlling_filing": dict(selected_filing), "common_equity": equity.as_dict(), "preferred_equity": pref.as_dict() if pref is not None else (equity_components if pref is None else None), "effective_preferred_claim": {'value':preferred_value, 'status':preferred_status, 'continuity':continuity}, "common_earnings_ttm": earnings, "diluted_shares": shares, "roe_status": roe_status},
    }


def bind_and_evaluate_existing_recipe(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, structural_packet: Mapping[str, Any] | None, cutoff: str) -> dict[str, Any]:
    bound = bind_residual_income_sources(policy, packet, structural_packet=structural_packet, cutoff=cutoff)
    baseline_replay = evaluate_recipe(recipe)["range"]
    refreshed = deepcopy(recipe)
    factors = policy.get('policy_assumptions',{}).get('share_count_sensitivity', {'bear':1.,'base':1.,'bull':1.})
    bound['scenario_share_counts'] = {}
    for name,spec in refreshed["scenarios"].items():
        factor = number(factors[name], 'approved share sensitivity')
        if factor <= 0:
            raise ValueError('share sensitivity must be positive')
        bound['scenario_share_counts'][name] = bound['inputs']['diluted_shares'] * factor
        spec["inputs"]["book_value_per_share"] = bound["inputs"]["common_equity"] / bound['scenario_share_counts'][name]
        if bound['roe_range'] is not None:
            spec["inputs"]["current_roe"] = bound['roe_range'][name]
    return {"bound": bound, "baseline_replay": baseline_replay, "refreshed_recipe": refreshed, "refreshed_replay": evaluate_recipe(refreshed)["range"]}
