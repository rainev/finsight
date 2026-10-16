"""Source-bounded lease/capital cash ledger; payment schedules are not debt."""
from copy import deepcopy
from datetime import date
import json
from math import isfinite
from pathlib import Path
import re
from types import MappingProxyType

from .catalog import canonical_json_bytes
from .refresh_narrative_evidence import narrative_policy,validate_narrative_evidence,terms_by_name

VERSION='FINSIGHT-LEASE-CAPITAL-SCOPE-WG25-1'
RULES=MappingProxyType({
    'INTC':{'version':VERSION,'ticker':'INTC','cik':'0000050863',
        'variant':'extended_term_financing_cash','issuer_namespace_pattern':r'https?://(?:www\.)?intel\.com/\d{8}',
        'debt_qnames':('us-gaap:DebtCurrent','us-gaap:LongTermDebtNoncurrent'),
        'capital_payment_local_name':'PaymentsToAcquirePropertyPlantAndEquipmentFinancingActivities',
        'noncash_purchase_local_name':'CapitalExpendituresIncurredButNotYetPaidExtendedPaymentTerms'},
    'JBL':{'version':VERSION,'ticker':'JBL','cik':'0000898293',
        'variant':'new_only_lease_schedule','issuer_namespace_pattern':r'https?://(?:www\.)?jabil\.com/\d{8}',
        'debt_qnames':('us-gaap:LongTermDebtCurrent','us-gaap:LongTermDebtNoncurrent')},
})

def lease_capital_policy(ticker):
    if ticker not in RULES:raise ValueError('no approved lease/capital scope rule')
    return deepcopy(RULES[ticker])

def _valid(row,policy,accession,period, *, flow=False, parent=None, role=None, issuer=False):
    if (row.get('source_accession')!=accession or row.get('period_end')!=period
        or bool(row.get('period_start'))!=flow or row.get('unit')!='USD'
        or str(row.get('entity_identifier','')).zfill(10)!=policy['cik']
        or row.get('entity_scheme')!='http://www.sec.gov/CIK' or row.get('dimensions')
        or isinstance(row.get('value'),bool) or not isinstance(row.get('value'),(int,float))
        or not isfinite(row['value']) or row['value']<0
        or (role and role not in row.get('statement_roles',[]))
        or (parent and parent not in row.get('presentation_parents',[]))
        or not re.fullmatch(policy['issuer_namespace_pattern'] if issuer else r'https?://fasb\.org/us-gaap/20\d{2}',str(row.get('namespace','')))):
        raise ValueError('lease/capital source identity, period, unit or economic presentation invalid')

def _one(rows,label, *, required=True):
    if not rows:
        if required:raise ValueError(label+' missing; absence is not zero')
        return None,[]
    identities={(r.get('context_id'),r.get('period_start'),r['value']) for r in rows}
    if len(identities)!=1:raise ValueError(label+' has conflicting or ambiguous contexts')
    return float(rows[0]['value']),[rows[0]]

def assess_lease_capital_scope(policy,structural,controlling,cik,cutoff,narrative, *, source_root=None):
    expected=RULES.get(policy.get('ticker'))
    if expected is None or canonical_json_bytes(policy)!=canonical_json_bytes(expected) or str(cik).zfill(10)!=expected['cik']:
        raise ValueError('lease/capital policy identity/version mismatch')
    acc,period,filed=(controlling[k] for k in ('accessionNumber','reportDate','filingDate'))
    for value in (period,filed,cutoff):date.fromisoformat(value)
    if not period<=filed<=cutoff or structural.get('source_accession')!=acc or structural.get('report_date')!=period or structural.get('filed_date')!=filed:
        raise ValueError('lease/capital controlling source/cutoff mismatch')
    source_root=Path(source_root or Path(__file__).resolve().parents[3]/'output')
    receipt=validate_narrative_evidence(narrative,narrative_policy(policy['ticker']),source_root=source_root)
    f=receipt['filing'];metadata=dict(structural.get('filing_metadata',()))
    manifest=json.loads((source_root/receipt['source']['package_manifest_path']).read_bytes())
    if (f!={'accession':acc,'form':controlling['form'],'report_date':period,'filed_date':filed}
        or metadata.get('primary_document')!=receipt['source']['document_name']
        or metadata.get('package_generation')!=manifest.get('generation')):
        raise ValueError('lease/capital narrative and structural package disagree')
    terms=terms_by_name(receipt);facts=structural['facts'];sources=[]
    def instant(qname, *, required=True, role=None, parent=None):
        rows=[r for r in facts if r.get('qname')==qname and r.get('period_end')==period and not r.get('period_start') and not r.get('dimensions')]
        for r in rows:_valid(r,policy,acc,period,role=role,parent=parent)
        value,src=_one(rows,qname,required=required);sources.extend(src);return value
    debt={q:instant(q,role='balance_sheet',parent=('us-gaap:LiabilitiesCurrentAbstract'
        if q.endswith('Current') else 'us-gaap:LiabilitiesAndStockholdersEquityAbstract')) for q in policy['debt_qnames']}
    carrying={q:instant(q,required=False,role='balance_sheet') for q in (
        'us-gaap:FinanceLeaseLiability','us-gaap:FinanceLeaseLiabilityCurrent','us-gaap:FinanceLeaseLiabilityNoncurrent')}
    if all(carrying[q] is not None for q in ('us-gaap:FinanceLeaseLiabilityCurrent','us-gaap:FinanceLeaseLiabilityNoncurrent')):
        component_total=carrying['us-gaap:FinanceLeaseLiabilityCurrent']+carrying['us-gaap:FinanceLeaseLiabilityNoncurrent']
        if carrying['us-gaap:FinanceLeaseLiability'] is not None and component_total!=carrying['us-gaap:FinanceLeaseLiability']:
            raise ValueError('finance-lease total and components do not reconcile')
    review=['complete_current_finance_lease_carrying_and_aggregate_debt_overlap_unbound']
    result={'status':'review_required','policy_version':VERSION,'ticker':policy['ticker'],
        'accession':acc,'period_end':period,'claim_adjustment':None,
        'reported_balance_sheet_debt_carrying_components':debt,'reported_balance_sheet_debt_carrying_subtotal':sum(debt.values()),
        'current_finance_lease_carrying_facts':carrying,'aggregate_debt_lease_overlap':'unresolved',
        'narrative_receipt_sha256':receipt['receipt_sha256'],'document_sha256':receipt['source']['document_sha256'],
        'reported_investing_capex_cash':None,'finance_lease_principal_cash':None,
        'financing_extended_term_capital_cash':None,'reported_noncash_extended_term_capital_amount':None,
        'reported_noncash_capital_amount':None,'noncash_capital_economic_scope':'ending_obligation_and_stock_vs_flow_scope_unbound',
        'source_rows':sources,'review_reasons':review,'numeric_successor_issued':False}
    def flow(local, *, issuer=False,parent):
        rows=[r for r in facts if r.get('local_name')==local and r.get('period_end')==period and r.get('period_start') and not r.get('dimensions')]
        for r in rows:_valid(r,policy,acc,period,flow=True,role='cash_flow',parent=parent,issuer=issuer)
        if rows:
            if len({r['period_start'] for r in rows})!=1:
                raise ValueError('lease/capital current source has multiple distinct duration windows')
        value,src=_one(rows,local);sources.extend(src);return value,rows[0]['period_start']
    investing,istart=flow('PaymentsToAcquirePropertyPlantAndEquipment',parent='us-gaap:NetCashProvidedByUsedInInvestingActivitiesAbstract')
    result.update(reported_investing_capex_cash=investing,current_ytd_start=istart)
    if policy['variant']=='extended_term_financing_cash':
        if terms['capital_payment_economic_scope']['value']!=policy['variant']:
            raise ValueError('extended-term capital financing classification not source bound')
        financing='us-gaap:NetCashProvidedByUsedInFinancingActivitiesAbstract'
        cap,start=flow(policy['capital_payment_local_name'],issuer=True,parent=financing)
        principal,pstart=flow('FinanceLeasePrincipalPayments',parent=financing)
        noncash,nstart=flow(policy['noncash_purchase_local_name'],issuer=True,parent='us-gaap:StatementOfCashFlowsAbstract')
        noncash_total,ntstart=flow('CapitalExpendituresIncurredButNotYetPaid',parent='us-gaap:SupplementalCashFlowInformationAbstract')
        if len({start,pstart,nstart,ntstart,istart})!=1:raise ValueError('lease/capital current YTD cash and noncash windows disagree')
        if noncash>noncash_total:raise ValueError('extended-term noncash inclusion exceeds reported supplemental total')
        result.update(current_ytd_start=start,reported_investing_capex_cash=investing,
            finance_lease_principal_cash=principal,financing_extended_term_capital_cash=cap,
            reported_noncash_extended_term_capital_amount=noncash,reported_noncash_capital_amount=noncash_total)
        review.append('extended_term_capital_financing_ending_liability_and_cash_debt_overlap_unbound')
        review.append('noncash_capital_supplemental_disclosure_ending_obligation_scope_unbound')
    else:
        from .refresh_commitment_claims import select_commitment_claim,commitment_claim_policy
        schedule=select_commitment_claim(commitment_claim_policy(policy['ticker']),structural,controlling,cik,cutoff)
        if terms['lease_schedule_economic_scope']['value']!='new_only_operating_and_finance_leases':
            raise ValueError('new-only lease schedule classification not source bound')
        result.update(new_only_lease_schedule=schedule['components'],
            excluded_combined_lease_guarantee_disclosure=terms['residual_guarantee_excluded_disclosure']['value'],
            excluded_combined_uncommenced_payments=terms['uncommenced_combined_lease_payments']['value'],
            guarantee_recognition_scope=terms['guarantee_recognition_scope']['value'])
        sources.extend(schedule['source_rows'] if 'source_rows' in schedule else schedule.get('source_facts',[]))
        review.extend(schedule['review_reasons'])
    return result
