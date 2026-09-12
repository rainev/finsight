"""Source-bound normalization shared by declarative refresh family policies."""
from __future__ import annotations

from math import isclose
import re
from statistics import median
from datetime import date, timedelta
from typing import Any
from copy import deepcopy

from .history import build_cash_fcff_history_profile
from .xbrl import CompanyFactsNormalizer
from .calculation_recipe import number
from .bridge_policy import BridgeRange, BridgeResolution, assess_bridge_materiality
from .field_availability import FieldAvailability
from .catalog import canonical_json_bytes, sha256_bytes
from .official_evidence import EvidenceRequest, EvidenceDecision
from .official_filing_ingestion import _structural_evidence_decisions
from .evidence_policy import source_attempt_from_decision, resolve_evidence_order, project_decision_to_availability
from .sustainable_inputs import SourceEvidence

POLICY_VERSION = 'US-REFRESH-CASH-HISTORY-2'
LEGACY_POLICY_VERSION = 'US-REFRESH-CASH-HISTORY-1'
_NET_INTEREST = 'InterestIncomeExpenseNonoperatingNet'
_GROSS_INTEREST = ('InterestExpenseNonoperating','InterestAndDebtExpense','InterestExpenseDebt','InterestExpense')
CDW_CASH_INTEREST_POLICY = 'CDW-CASH-INTEREST-1'
MCO_CASH_INTEREST_POLICY = 'MCO-CASH-INTEREST-1'
CTSH_STRUCTURAL_INTEREST_POLICY = 'CTSH-STRUCTURAL-INTEREST-1'
ABT_STRUCTURAL_INTEREST_POLICY = 'ABT-STRUCTURAL-INTEREST-1'
COHR_OPERATING_INTEREST_POLICY = 'COHR-OPERATING-INTEREST-1'
CMG_OWNER_CASH_POLICY = 'CMG-OWNER-CASH-1'
DASH_OWNER_CASH_POLICY = 'DASH-OWNER-CASH-1'


def financing_adjustment(value: float, *, basis: str) -> float:
    amount = number(value,'reported financing contribution')
    if basis == 'net_nonoperating_interest':
        return -amount
    if basis in {'gross_expense_proxy','cash_interest_paid_proxy'} and amount >= 0:
        return amount
    raise ValueError('unsupported financing sign or economic basis')


def _validate_ttm_alignment(flow: dict) -> None:
    if flow.get('method') != 'latest_fy_plus_current_ytd_minus_prior_ytd':
        return
    annual,current,prior = flow['sources']
    gap = (date.fromisoformat(current['start'])-date.fromisoformat(annual['end'])).days
    prior_start_gap = abs((date.fromisoformat(prior['start'])-date.fromisoformat(annual['start'])).days)
    if not 1 <= gap <= 8 or prior_start_gap > 8 or prior['end'] > annual['end']:
        raise ValueError('TTM annual and comparative YTD periods are not contiguous')


def _structural_financing_normalizer(normalizer: CompanyFactsNormalizer, structural: dict, period: str,
                                     financing_policy: str):
    """Rebuild TTM interest when the current 10-Q fact is structural-only."""
    cik=str(normalizer.companyfacts.get('cik','')).zfill(10)
    scopes={
        CTSH_STRUCTURAL_INTEREST_POLICY:('0001058290',('InterestExpenseNonoperating','InterestExpense')),
        ABT_STRUCTURAL_INTEREST_POLICY:('0000001800',('InterestExpenseNonoperating','InterestExpense')),
    }
    expected=scopes.get(financing_policy)
    if expected is None or cik!=expected[0] or structural.get('report_date')!=period:
        raise ValueError('unsupported structural financing source scope')
    accession=structural.get('source_accession')
    if not isinstance(accession,str):
        raise ValueError('structural financing accession is missing')
    config=deepcopy(normalizer.config)
    concepts=expected[1]
    config['fields']['interest_expense']={'unit':'USD','kind':'flow','concepts':list(concepts)}
    candidate=CompanyFactsNormalizer(normalizer.companyfacts,concept_config=config,
        fiscal_year_end=normalizer.fiscal_year_end,as_of_date=normalizer.as_of_date,
        filing_records=normalizer.filing_records)
    annuals=[row for row in candidate.annual_series('interest_expense',5) if row.end < period]
    if not annuals:
        raise ValueError('structural financing needs a prior annual source')
    annual=annuals[-1]
    rows=[row for row in structural.get('facts',[]) if row.get('qname') in {'us-gaap:'+name for name in concepts}
          and row.get('source_accession')==accession and row.get('unit')=='USD' and not row.get('dimensions')
          and row.get('period_start') and row.get('period_end') and row.get('entity_scheme')=='http://www.sec.gov/CIK'
          and str(row.get('entity_identifier','')).zfill(10)==cik
          and re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(row.get('namespace','')))]
    current=[row for row in rows if row['period_end']==period and row['period_start']>annual.end]
    if not current:
        raise ValueError('structural current YTD financing fact is missing')
    current_start=min(row['period_start'] for row in current)
    current=[row for row in current if row['period_start']==current_start]
    current_values={number(row['value'],'current YTD financing') for row in current}
    if len(current_values)!=1:
        raise ValueError('structural current YTD financing facts conflict')
    duration=(date.fromisoformat(period)-date.fromisoformat(current_start)).days
    prior=[row for row in rows if row['period_end']<=annual.end
           and abs((date.fromisoformat(row['period_end'])-date.fromisoformat(row['period_start'])).days-duration)<=7
           and abs((date.fromisoformat(row['period_start'])-date.fromisoformat(annual.start)).days)<=7]
    if not prior:
        raise ValueError('structural comparative YTD financing fact is missing')
    prior_end=max(row['period_end'] for row in prior)
    prior=[row for row in prior if row['period_end']==prior_end]
    prior_values={number(row['value'],'comparative YTD financing') for row in prior}
    if len(prior_values)!=1:
        raise ValueError('structural comparative YTD financing facts conflict')
    def source(row):
        return {'field':'interest_expense','namespace':'us-gaap','concept':row['qname'].split(':',1)[1],
            'unit':'USD','value':number(row['value'],'structural financing source'),
            'start':row['period_start'],'end':row['period_end'],'accession':accession,
            'form':row.get('filing_form'),'filed':row.get('filed_date'),'dimensions':row.get('dimensions') or [],
            'selection_reason':'Exact current structural YTD financing fact from the controlling filing.'}
    current_source,prior_source=source(current[0]),source(prior[0])
    flow={'value':annual.value+current_values.pop()-prior_values.pop(),'period_end':period,
        'method':'latest_fy_plus_current_ytd_minus_prior_ytd',
        'sources':[annual.as_dict(),current_source,prior_source],
        'current_ytd':current_source,'prior_ytd':prior_source}
    _validate_ttm_alignment(flow)
    return candidate,flow,'gross_expense_proxy'


def _structural_ttm_flow(normalizer: CompanyFactsNormalizer, structural: dict, period: str, field: str) -> dict:
    """Reconstruct a current TTM flow from exact structural YTD comparatives."""
    cik=str(normalizer.companyfacts.get('cik','')).zfill(10)
    if cik not in {'0000001800','0001058290'} or structural.get('report_date')!=period:
        raise ValueError('unsupported structural TTM source scope')
    accession=structural.get('source_accession')
    concepts=normalizer.config.get('fields',{}).get(field,{}).get('concepts',())
    qnames={str(name) if ':' in str(name) else 'us-gaap:'+str(name) for name in concepts}
    annuals=[row for row in normalizer.annual_series(field,5) if row.end < period]
    if not annuals or not qnames or not isinstance(accession,str):
        raise ValueError(f'{field} structural TTM prerequisites are missing')
    annual=annuals[-1]
    rows=[row for row in structural.get('facts',[]) if row.get('qname') in qnames
          and row.get('source_accession')==accession and row.get('unit')==normalizer.config['fields'][field]['unit']
          and not row.get('dimensions') and row.get('period_start') and row.get('period_end')
          and row.get('entity_scheme')=='http://www.sec.gov/CIK'
          and str(row.get('entity_identifier','')).zfill(10)==cik
          and re.fullmatch(r'https?://fasb\.org/us-gaap/20\d{2}',str(row.get('namespace','')))]
    current=[row for row in rows if row['period_end']==period and row['period_start']>annual.end]
    if not current:
        raise ValueError(f'{field} structural current YTD fact is missing')
    current_start=min(row['period_start'] for row in current)
    current=[row for row in current if row['period_start']==current_start]
    current_values={number(row['value'],f'{field} current YTD') for row in current}
    if len(current_values)!=1:
        raise ValueError(f'{field} structural current YTD facts conflict')
    duration=(date.fromisoformat(period)-date.fromisoformat(current_start)).days
    prior=[row for row in rows if row['period_end']<=annual.end
           and abs((date.fromisoformat(row['period_end'])-date.fromisoformat(row['period_start'])).days-duration)<=7
           and abs((date.fromisoformat(row['period_start'])-date.fromisoformat(annual.start)).days)<=7]
    if not prior:
        raise ValueError(f'{field} structural comparative YTD fact is missing')
    prior_end=max(row['period_end'] for row in prior);prior=[row for row in prior if row['period_end']==prior_end]
    prior_values={number(row['value'],f'{field} comparative YTD') for row in prior}
    if len(prior_values)!=1:
        raise ValueError(f'{field} structural comparative YTD facts conflict')
    def source(row):
        return {'field':field,'namespace':'us-gaap','concept':row['qname'].split(':',1)[1],
            'unit':row['unit'],'value':number(row['value'],f'{field} structural source'),
            'start':row['period_start'],'end':row['period_end'],'accession':accession,
            'form':row.get('filing_form'),'filed':row.get('filed_date'),'dimensions':row.get('dimensions') or [],
            'selection_reason':'Exact current structural YTD fact from the controlling filing.'}
    current_source,prior_source=source(current[0]),source(prior[0])
    flow={'value':annual.value+current_values.pop()-prior_values.pop(),'period_end':period,
        'method':'latest_fy_plus_current_ytd_minus_prior_ytd','sources':[annual.as_dict(),current_source,prior_source],
        'current_ytd':current_source,'prior_ytd':prior_source}
    _validate_ttm_alignment(flow)
    return flow


def _financing_normalizer(normalizer: CompanyFactsNormalizer, period: str, financing_policy: str | None = None,
                          structural_packet: dict | None = None):
    """Never combine gross expense and net-income concepts in one TTM sum."""
    if financing_policy in {CTSH_STRUCTURAL_INTEREST_POLICY,ABT_STRUCTURAL_INTEREST_POLICY}:
        if not isinstance(structural_packet,dict):
            raise ValueError('structural financing policy requires the current filing')
        return _structural_financing_normalizer(normalizer,structural_packet,period,financing_policy)
    failures = []
    choices = (('net_nonoperating_interest',(_NET_INTEREST,)),('gross_expense_proxy',_GROSS_INTEREST))
    if financing_policy is not None:
        scopes = {CDW_CASH_INTEREST_POLICY:'0001402057',MCO_CASH_INTEREST_POLICY:'0001059556',
                  COHR_OPERATING_INTEREST_POLICY:'0000820318'}
        if financing_policy not in scopes or str(normalizer.companyfacts.get('cik','')).zfill(10) != scopes[financing_policy]:
            raise ValueError('unsupported issuer-specific cash-interest policy')
        choices = ((('gross_expense_proxy',('InterestExpenseOperating',)),)
                   if financing_policy==COHR_OPERATING_INTEREST_POLICY
                   else (('cash_interest_paid_proxy',('InterestPaidNet',)),))
    for basis,concepts in choices:
        config = deepcopy(normalizer.config)
        config['fields']['interest_expense'] = {'unit':'USD','kind':'flow','concepts':['us-gaap:'+name for name in concepts]}
        candidate = CompanyFactsNormalizer(normalizer.companyfacts,concept_config=config,
            fiscal_year_end=normalizer.fiscal_year_end,as_of_date=normalizer.as_of_date,filing_records=normalizer.filing_records)
        try:
            flow = candidate.ttm_flow('interest_expense')
            _validate_ttm_alignment(flow)
            if flow['period_end'] != period:
                raise ValueError('financing period does not match current filing')
            if basis == 'cash_interest_paid_proxy' and any(number(row['value'],'cash interest component') < 0 for row in flow['sources']):
                raise ValueError('cash interest components require nonnegative reported payments')
            financing_adjustment(flow['value'],basis=basis)
            return candidate,flow,basis
        except ValueError as exc:
            failures.append(str(exc))
    raise ValueError('no complete, consistently scoped current financing series: ' + '; '.join(failures))


def _reconciled_equity_zero(field: str, structural: dict, proof: dict, *, accession: str, period: str) -> FieldAvailability:
    qnames = {'us-gaap:StockholdersEquity','us-gaap:CommonStockValue','us-gaap:AdditionalPaidInCapitalCommonStock',
              'us-gaap:CommonStocksIncludingAdditionalPaidInCapital','us-gaap:RetainedEarningsAccumulatedDeficit',
              'us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax','us-gaap:TreasuryStockValue',
              'us-gaap:TreasuryStockCommonValue'}
    if field == 'noncontrolling_interests':
        qnames.update({'us-gaap:Assets','us-gaap:Liabilities','us-gaap:LiabilitiesAndStockholdersEquity'})
    sources = tuple(sorted({f"{accession}|{period}|{row['qname']}|{row['context_id']}"
        for row in structural['facts'] if row.get('qname') in qnames and row.get('period_end') == period
        and row.get('period_start') is None and row.get('unit') == 'USD' and row.get('context_id')}))
    if not sources:
        raise ValueError('equity reconciliation source contexts are missing')
    return FieldAvailability(field=field,value=0.,state='evidence_backed_zero',
        reason_code='COMMON_EQUITY_COMPONENTS_RECONCILED' if field == 'preferred_equity' else 'COMMON_EQUITY_AND_BALANCE_RECONCILED',
        period_end=period,source_accession=accession,source_kind='practical_policy',
        evidence_class='reported_component_reconciliation',freshness='current',fallback_level='reported_aggregate',
        covered_fields=(field,),coverage_basis='reconciled_disjoint_components',coverage_source_facts=sources,
        economic_scope='common parent equity' if field == 'preferred_equity' else 'consolidated assets less liabilities and common parent equity',
        extraction_complete=True,searched_concepts=tuple(sorted(qnames)))


def structural_bridge_evidence(packet: dict, *, period: str, cutoff: str, cik: str) -> tuple[list[FieldAvailability], dict]:
    """Promote only decisions accepted by the existing official-source policy."""
    structural = packet.get('structural_filing')
    if not isinstance(structural, dict): return [], {'status':'structural_packet_unavailable'}
    raw_filing = packet.get('controlling_filing', {})
    if not raw_filing.get('primaryDocument') and not raw_filing.get('primary_document'):
        recent = packet.get('submissions', {}).get('filings', {}).get('recent', {})
        accessions = recent.get('accessionNumber', [])
        if structural['source_accession'] in accessions:
            index = accessions.index(structural['source_accession'])
            raw_filing = {key:values[index] for key,values in recent.items() if isinstance(values,list) and index<len(values)}
    document = raw_filing.get('primaryDocument') or raw_filing.get('primary_document')
    if not document: raise ValueError('controlling primary document metadata is missing')
    filing = {'accession':structural['source_accession'], 'form':structural['form'], 'report_date':period,
              'filed':structural.get('filed_date') or raw_filing.get('filingDate'),
              'primary_document':document}
    if not filing['filed'] or filing['filed'] > cutoff:
        raise ValueError('structural bridge filing is outside the source cutoff')
    fields = ('cash','marketable_securities_current','marketable_securities_noncurrent','marketable_securities_total',
              'commercial_paper','current_debt','noncurrent_debt','finance_lease_current','finance_lease_noncurrent','finance_lease_total','preferred_equity','noncontrolling_interests')
    requests = [EvidenceRequest(field,'fcff_dcf','balance_sheet_snapshot','material',valuation_date=cutoff,expected_unit='USD') for field in fields]
    digest = sha256_bytes(canonical_json_bytes(structural))
    decisions, _ = _structural_evidence_decisions(requests, parsed=structural, filing=filing, cik=cik,
                     valuation_date=cutoff, proof=(digest,))
    availability, reconciliations = [], {}
    for raw in decisions:
        decision = EvidenceDecision.from_dict(raw)
        if decision.status not in {'reported','explicit_zero'}: continue
        attempt = source_attempt_from_decision(decision, source='exact_sec_filing', eligible=True)
        policy = resolve_evidence_order(decision.request.as_dict(), [attempt])
        if policy.selected is not None:
            availability.append(project_decision_to_availability(policy, fallback_level='current_reported', source_attempt=attempt).availability)
    if not any(row.field == 'preferred_equity' for row in availability):
        from .newrefresh_family_policies import reconcile_common_equity_components
        try:
            common = reconcile_common_equity_components(structural, cik=cik, accession=filing['accession'], period_end=period)
        except ValueError:
            common = None
        if common is not None:
            reconciliations['preferred_equity'] = common
            availability.append(_reconciled_equity_zero('preferred_equity',structural,common,accession=filing['accession'],period=period))
    if not any(row.field == 'noncontrolling_interests' for row in availability):
        from .newrefresh_family_policies import reconcile_no_outside_equity_claim
        try:
            nci = reconcile_no_outside_equity_claim(structural,cik=cik,accession=filing['accession'],period_end=period)
        except ValueError:
            nci = None
        if nci is not None:
            reconciliations['noncontrolling_interests'] = nci
            availability.append(_reconciled_equity_zero('noncontrolling_interests',structural,nci,accession=filing['accession'],period=period))
    return availability, {'decisions':decisions, 'structural_sha256':digest,'reconciliations':reconciliations}


def cash_history(normalizer: CompanyFactsNormalizer, *, period: str, cutoff: str, rule: dict,
                 cash_receipts: list | None = None, structural_packet: dict | None = None) -> dict:
    """Rebuild the established annual-median cash-conversion profile.

    No unusual-item/SBC addbacks or invented maintenance-capex splits occur.
    Negative annual observations stay in the private profile.
    """
    version = rule.get('normalization_version')
    if version not in {POLICY_VERSION,LEGACY_POLICY_VERSION}:
        raise ValueError('explicit supported cash-history policy version required')
    cash_policy=rule.get('cash_policy')
    owner_cash = cash_policy in {CMG_OWNER_CASH_POLICY,DASH_OWNER_CASH_POLICY}
    owner_cash_ciks={CMG_OWNER_CASH_POLICY:'0001058090',DASH_OWNER_CASH_POLICY:'0001792789'}
    if cash_policy is not None and (not owner_cash or version != POLICY_VERSION
        or str(normalizer.companyfacts.get('cik','')).zfill(10) != owner_cash_ciks[cash_policy]
        or rule.get('financing_policy')):
        raise ValueError('unsupported owner-cash policy or issuer')
    cap = number(rule.get('annual_tax_cap', .30), 'annual_tax_cap')
    fallback = number(rule.get('loss_tax_fallback', .21), 'loss_tax_fallback')
    if not 0 <= fallback <= cap <= 1:
        raise ValueError('invalid approved tax normalization policy')
    extra_capex = tuple(rule.get('additional_capex_fields', ()))
    structural_ttm_fields=tuple(rule.get('structural_ttm_fields',()))
    if structural_ttm_fields and (str(normalizer.companyfacts.get('cik','')).zfill(10) not in {'0000001800','0001058290'}
        or structural_ttm_fields!=('revenue','operating_cash_flow','capital_expenditures')
        or not isinstance(structural_packet,dict)):
        raise ValueError('unsupported structural TTM field policy')
    if extra_capex:
        cik=str(normalizer.companyfacts['cik']).zfill(10)
        br_expected = {'capitalized_software': ['us-gaap:PaymentsForSoftware'], 'capital_expenditures':['us-gaap:PaymentsToAcquirePropertyPlantAndEquipment']}
        br_valid=(cik=='0001383312' and extra_capex==('capitalized_software',)
            and all(normalizer.config['fields'][field]['concepts']==concepts for field,concepts in br_expected.items()))
        dash_valid=(cash_policy==DASH_OWNER_CASH_POLICY and cik=='0001792789'
            and extra_capex==('software_development',)
            and 'PaymentsToDevelopSoftware' in normalizer.config['fields']['software_development']['concepts'])
        if version != POLICY_VERSION or not (br_valid or dash_valid):
            raise RuntimeError('additional capex requires an approved disjoint issuer source mapping')
    fields = ('revenue','operating_cash_flow','capital_expenditures', *(() if owner_cash else ('interest_expense',)), *extra_capex)
    interest_normalizer = normalizer
    basis = 'legacy_absolute_interest'
    if owner_cash:
        basis = 'owner_cash_no_financing_adjustment'
        ttm = {field:(_structural_ttm_flow(normalizer,structural_packet,period,field)
                      if field in structural_ttm_fields else normalizer.ttm_flow(field)) for field in fields}
    elif version == POLICY_VERSION:
        interest_normalizer,interest_flow,basis = _financing_normalizer(
            normalizer,period,rule.get('financing_policy'),structural_packet)
        ttm = {field: (_structural_ttm_flow(normalizer,structural_packet,period,field)
                       if field in structural_ttm_fields else normalizer.ttm_flow(field))
               for field in fields if field != 'interest_expense'}
        ttm['interest_expense'] = interest_flow
    else:
        ttm = {field:(_structural_ttm_flow(normalizer,structural_packet,period,field)
                      if field in structural_ttm_fields else normalizer.ttm_flow(field)) for field in fields}
    if any(row['period_end'] != period for row in ttm.values()):
        raise ValueError('cash history TTM periods are not aligned to current filing')
    if version == POLICY_VERSION:
        for flow in ttm.values():
            _validate_ttm_alignment(flow)
    annual, tax_rates, dropped = [], [], []
    for operating in normalizer.annual_series('operating_cash_flow', 5):
        selected = {field: normalizer.annual_at_end(field, operating.end) for field in (*fields, *(() if owner_cash else ('income_tax','pretax_income')))}
        if owner_cash:
            selected.update(interest_expense=None,income_tax=None,pretax_income=None)
        elif version == POLICY_VERSION:
            selected['interest_expense'] = interest_normalizer.annual_at_end('interest_expense',operating.end)
        if any(selected[field] is None for field in fields):
            dropped.append({'period_end': operating.end, 'reason':'incomplete_comparable_cash_history'})
            continue
        if any(selected[field].unit != operating.unit or selected[field].start != operating.start for field in fields):
            raise ValueError('annual cash history units or start dates do not align')
        tax, pretax = selected['income_tax'], selected['pretax_income']
        valid_tax = tax is not None and pretax is not None and pretax.value > 0
        if valid_tax and (tax.start != operating.start or pretax.start != operating.start or tax.unit != operating.unit or pretax.unit != operating.unit):
            raise ValueError('annual tax periods or units do not align')
        rate = min(cap, max(0., tax.value / pretax.value)) if valid_tax else fallback
        if valid_tax: tax_rates.append(rate)
        if any(selected[field].value < 0 for field in ('capital_expenditures', *extra_capex)):
            raise ValueError('reported capex sign requires an explicit mapping rule')
        adjustment = 0. if owner_cash else (abs(selected['interest_expense'].value) if version == LEGACY_POLICY_VERSION
                      else financing_adjustment(selected['interest_expense'].value,basis=basis))
        cash = operating.value - selected['capital_expenditures'].value - sum(selected[field].value for field in extra_capex) + adjustment * (1-rate)
        annual.append({'period_end':operating.end, **{field: fact.as_dict() if fact else None for field,fact in selected.items()},
                       'cash_fcff':cash, 'tax_rate':rate, 'tax_basis':'bounded_reported_effective_rate' if valid_tax else 'approved_loss_tax_fallback'})
        if version == POLICY_VERSION:
            annual[-1].update(financing_adjustment_basis=basis,financing_adjustment_before_tax=adjustment,
                financing_adjustment_after_tax=adjustment*(1-rate))
        if owner_cash:
            annual[-1].update(tax_rate=None,tax_basis='not_used_owner_cash',formula='reported operating cash flow - capital expenditures')
    minimum = rule.get('minimum_annual_periods', 3)
    if isinstance(minimum, bool) or not isinstance(minimum, int) or not 3 <= minimum <= 5:
        raise ValueError('ordinary cash-history policy requires three to five annual periods')
    if len(annual) < minimum or (not owner_cash and len(tax_rates) < minimum):
        raise ValueError('insufficient comparable annual cash or tax history')
    tax_rate = 0. if owner_cash else median(tax_rates)
    reported = {field: number(row['value'], field) for field,row in ttm.items()}
    if any(reported[field] < 0 for field in ('capital_expenditures', *extra_capex)):
        raise ValueError('reported capex sign requires an explicit mapping rule')
    adjustment = 0. if owner_cash else abs(reported['interest_expense']) if version == LEGACY_POLICY_VERSION else financing_adjustment(reported['interest_expense'],basis=basis)
    fcff = reported['operating_cash_flow'] - reported['capital_expenditures'] - sum(reported[field] for field in extra_capex) + adjustment * (1-tax_rate)
    sources = [source for row in ttm.values() for source in row['sources']]
    starts = set()
    for flow in ttm.values():
        if flow['method'] == 'latest_fiscal_year':
            starts.add(flow['sources'][0]['start'])
        elif flow['method'] == 'latest_fy_plus_current_ytd_minus_prior_ytd':
            starts.add((date.fromisoformat(flow['prior_ytd']['end']) + timedelta(days=1)).isoformat())
        else:
            raise ValueError('cash metric needs a verified annual or reconstructed TTM interval')
    if len(starts) != 1:
        raise ValueError('cash metric source intervals are not comparable')
    flow_start = starts.pop()
    receipt_adjustment = None
    if cash_receipts is not None:
        from .refresh_cash_receipts import CF_CIK, sum_cash_receipts
        if str(normalizer.companyfacts['cik']).zfill(10) != CF_CIK or version != POLICY_VERSION or not cash_receipts:
            raise ValueError('unsupported or missing source-backed cash receipt normalization')
        receipt_adjustment = sum_cash_receipts(cash_receipts,window_start=flow_start,window_end=period,cutoff=cutoff)
        receipt_adjustment['cash_fcff_before_adjustment'] = fcff
        fcff -= receipt_adjustment['amount']
        for row in annual:
            adjustment_row = sum_cash_receipts(cash_receipts,window_start=row['operating_cash_flow']['start'],window_end=row['period_end'],cutoff=cutoff)
            row['cash_fcff_before_receipt_adjustment'] = row['cash_fcff']
            row['cash_fcff'] -= adjustment_row['amount']
            row['cash_receipt_adjustment'] = adjustment_row
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=reported['revenue'],
             ttm_cash_fcff=fcff, ttm_period_end=period, ttm_sources=sources, valuation_date=cutoff)
    metric = profile.metric('cash_conversion_margin')
    if metric is None: raise ValueError('cash-conversion history unavailable')
    derivation = {'policy_version':version,'cash_sources':ttm,'annual_tax_sources':annual,'tax_rate':tax_rate,'value':fcff}
    if owner_cash:
        derivation.update(tax_rate=None,cash_policy=cash_policy)
    if receipt_adjustment is not None:
        derivation['cash_receipt_adjustment'] = receipt_adjustment
    if version == POLICY_VERSION:
        derivation['financing_adjustment_basis'] = basis
    derivation_hash = sha256_bytes(canonical_json_bytes(derivation))
    source_dates = [row['filed'] for row in sources]
    source_dates.extend(fact['filed'] for row in annual for field in ('income_tax','pretax_income')
                        if isinstance((fact := row.get(field)), dict))
    if cash_receipts:
        source_dates.extend(row['filing_date'] for row in cash_receipts)
    metric_source = SourceEvidence(
        source_id=f'cash-fcff-{derivation_hash}', cik=str(normalizer.companyfacts['cik']),
        field='cash_fcff',unit='USD',reported_value=fcff,period_start=flow_start,period_end=period,
        filing_date=max(source_dates),reported_vs_estimated='derived_reported',
        locator=f'{version}: ' + ('OCF minus total capex; no financing or tax adjustment' if owner_cash else 'OCF minus total capex plus interest after policy-normalized tax') + (' less source-backed receipts in their cash-date window' if receipt_adjustment is not None else '') + '; full source derivation retained',
    ).as_dict()
    result = {'policy_version':version, 'reported':reported, 'reported_sources':ttm,
            'actual_measure':{'value':fcff,'source':metric_source,'derivation_sha256':derivation_hash},
            'ttm_cash_fcff':fcff, 'tax_rate':tax_rate, 'annual':annual, 'excluded_annual_periods':dropped,
            'profile':profile.as_private_dict(), 'cash_conversion_margin':{'low':metric.low,'base':metric.base,'high':metric.high},
            'formula':'reported OCF - total reported capex + after-tax reported interest',
            'limitations':['Working-capital movements remain in reported OCF unless separately reconciled.',
                          'SBC is not automatically added back; source share and dilution policy remains separate.',
                          'Cash-growth scenarios grow a post-total-capex cash starting point; no maintenance/growth split is inferred.']}
    if version == POLICY_VERSION:
        result.update(financing_adjustment_basis=basis,financing_adjustment_before_tax=adjustment,
            financing_adjustment_after_tax=adjustment*(1-tax_rate),
            formula='reported OCF - total reported capex + signed after-tax financing adjustment')
        if basis == 'cash_interest_paid_proxy':
            result['limitations'].append('Source-linked cash interest paid is the approved issuer-specific financing proxy, not accrued interest expense.')
        elif not owner_cash:
            result['limitations'].append('Reported interest is an accrual-based financing proxy, not a claim that cash interest paid was separately verified.')
        if basis == 'gross_expense_proxy':
            result['limitations'].append('Gross expense is added back; any separately unreported nonoperating interest income remains in reported OCF.')
    if owner_cash:
        result.update(tax_rate=None,tax_basis='not_used_owner_cash',formula='reported OCF - total reported capex')
        result['limitations'].append('Explicit owner-cash lane: no interest or tax adjustment. Financing claims remain separately validated in the current bridge.')
    if receipt_adjustment is not None:
        result['cash_receipt_adjustment'] = receipt_adjustment
        result['formula'] += ' - source-backed nonrecurring cash receipts within each cash-flow window'
        result['limitations'].append('Receipt removal is gross cash only; no separately evidenced tax reversal is applied.')
    if extra_capex:
        result['additional_capex_components'] = {field:reported[field] for field in extra_capex}
        result['total_capital_spending'] = reported['capital_expenditures'] + sum(reported[field] for field in extra_capex)
        result['limitations'].append('Capital spending includes separately reported software investment; operating software-license expenses/liabilities are not capitalized or added back.')
    growth = profile.metric('revenue_growth')
    if growth is not None:
        result['revenue_growth'] = {'low':growth.low,'base':growth.base,'high':growth.high}
        result['revenue_growth_basis'] = growth.normalization_basis
    return result


def normalized_bridge(
    normalizer: CompanyFactsNormalizer,
    packet: dict,
    *,
    period: str,
    capital_structure_policy: dict | None = None,
    reported_claim_scope: dict | None = None,
    aggregate_debt_scope: dict | None = None,
    outside_equity_zero_scope: dict | None = None,
    preferred_equity_zero_scope: dict | None = None,
    preferred_lifecycle_scope: dict | None = None,
    unconsolidated_vie_scope: dict | None = None,
) -> dict:
    """Reuse existing evidence-aware normalization and bridge resolution."""
    evidence = [FieldAvailability.from_dict(row) for row in packet.get('bridge_evidence', [])]
    recovered, recovery_receipt = structural_bridge_evidence(packet, period=period, cutoff=normalizer.as_of_date,
                                  cik=str(normalizer.companyfacts['cik']).zfill(10))
    evidence.extend(recovered)
    unconsolidated_vie_proof=None
    if unconsolidated_vie_scope is not None:
        from .refresh_vie_scope import bind_unconsolidated_vie_scope
        structural=packet.get('structural_filing');controlling=packet.get('controlling_filing',{})
        accession=controlling.get('accessionNumber') or controlling.get('accession')
        if not isinstance(structural,dict) or not isinstance(accession,str):
            raise ValueError('unconsolidated VIE scope requires the current structural filing')
        availability,unconsolidated_vie_proof=bind_unconsolidated_vie_scope(
            ticker=str(unconsolidated_vie_scope.get('ticker','')),policy=unconsolidated_vie_scope,
            structural=structural,accession=accession,period=period)
        evidence.append(availability)
    preferred_lifecycle_proof = None
    if preferred_lifecycle_scope is not None:
        from .refresh_preferred_lifecycle import bind_preferred_lifecycle
        structural = packet.get('structural_filing')
        controlling = packet.get('controlling_filing', {})
        accession = controlling.get('accessionNumber') or controlling.get('accession')
        if not isinstance(structural, dict) or not isinstance(accession, str):
            raise ValueError('preferred lifecycle scope requires the current structural filing')
        availability, preferred_lifecycle_proof = bind_preferred_lifecycle(
            ticker=str(preferred_lifecycle_scope.get('ticker','')), policy=preferred_lifecycle_scope,
            structural=structural, accession=accession, period=period)
        evidence.append(availability)
    aggregate_debt_proof = None
    investment_scope_proof = None
    if aggregate_debt_scope is not None:
        from .refresh_bridge_scope_policies import (
            aggregate_debt_field_availability,
            nonmarketable_investment_zero_availabilities,
        )
        structural = packet.get('structural_filing')
        controlling = packet.get('controlling_filing', {})
        accession = controlling.get('accessionNumber') or controlling.get('accession')
        if not isinstance(structural, dict) or not isinstance(accession, str):
            raise ValueError('aggregate debt scope requires the current structural filing')
        availability, aggregate_debt_proof = aggregate_debt_field_availability(
            ticker=str(aggregate_debt_scope.get('ticker', '')),
            policy=aggregate_debt_scope,
            structural_packet=structural,
            accession=accession,
            period_end=period,
        )
        evidence.append(availability)
        if (aggregate_debt_scope.get('excluded_investment_total_qname')
            or aggregate_debt_scope.get('direct_marketable_qnames')
            or aggregate_debt_scope.get('zero_marketable_fields')):
            investment_records, investment_scope_proof = nonmarketable_investment_zero_availabilities(
                ticker=str(aggregate_debt_scope.get('ticker', '')),
                policy=aggregate_debt_scope,
                structural_packet=structural,
                accession=accession,
                period_end=period,
            )
            # The versioned investment-scope rule has just proved that a
            # generically named structural investment is not cash-like. Drop
            # only the generic recovery for those exact fields so it cannot
            # conflict with the narrower, source-reconciled classification.
            replaced_fields = {record.field for record in investment_records}
            evidence = [record for record in evidence if record.field not in replaced_fields]
            evidence.extend(investment_records)
    outside_equity_proof = None
    if outside_equity_zero_scope is not None:
        from .refresh_bridge_scope_policies import outside_equity_zero_availability
        structural = packet.get('structural_filing')
        controlling = packet.get('controlling_filing', {})
        accession = controlling.get('accessionNumber') or controlling.get('accession')
        if not isinstance(structural,dict) or not isinstance(accession,str):
            raise ValueError('outside-equity scope requires the current structural filing')
        availability,outside_equity_proof = outside_equity_zero_availability(
            ticker=str(outside_equity_zero_scope.get('ticker','')),
            policy=outside_equity_zero_scope,structural_packet=structural,
            accession=accession,period_end=period)
        evidence.append(availability)
    preferred_zero_proof=None
    if preferred_equity_zero_scope is not None:
        from .refresh_bridge_scope_policies import preferred_equity_zero_availability
        structural=packet.get('structural_filing');controlling=packet.get('controlling_filing',{})
        accession=controlling.get('accessionNumber') or controlling.get('accession')
        if not isinstance(structural,dict) or not isinstance(accession,str):
            raise ValueError('preferred-equity zero scope requires the current structural filing')
        availability,preferred_zero_proof=preferred_equity_zero_availability(
            ticker=str(preferred_equity_zero_scope.get('ticker','')),policy=preferred_equity_zero_scope,
            structural_packet=structural,accession=accession,period_end=period)
        evidence.append(availability)
    claim_scope_proof = None
    if reported_claim_scope is not None:
        from .refresh_reported_claim_scope import reported_nci_field_availability
        structural = packet.get('structural_filing')
        controlling = packet.get('controlling_filing', {})
        accession = controlling.get('accessionNumber') or controlling.get('accession')
        if not isinstance(structural, dict) or not isinstance(accession, str):
            raise ValueError('reported NCI scope requires the current structural filing')
        availability, claim_scope_proof = reported_nci_field_availability(
            ticker=str(reported_claim_scope.get('ticker', '')),
            policy=reported_claim_scope,
            structural_packet=structural,
            accession=accession,
            period_end=period,
        )
        evidence.append(availability)
    normalized = normalizer.normalize_balance_sheet(period_end=period, filing_evidence=packet.get('filing_evidence', ()), bridge_evidence=evidence)
    balance = normalized['balance_sheet']
    if balance['period_end'] != period:
        raise ValueError('normalized bridge is not anchored to current financial period')
    resolution = BridgeResolution.from_dict(balance['bridge_precheck'])
    if preferred_lifecycle_proof is not None:
        preferred=resolution.preferred_equity
        expected=float(preferred_lifecycle_proof['preferred_equity'])
        if not (preferred.low==preferred.midpoint==preferred.high==expected):
            raise ValueError('preferred lifecycle claim does not reconcile to normalized bridge')
    projection = None
    if capital_structure_policy is not None:
        from .refresh_preferred_conversion import CONVERSION_POLICY, bind_preferred_conversion_sources, project_converted_bridge
        if capital_structure_policy != CONVERSION_POLICY or str(normalizer.companyfacts['cik']).zfill(10) != CONVERSION_POLICY['cik']:
            raise RuntimeError('capital structure policy identity/version mismatch')
        projection = bind_preferred_conversion_sources(packet['structural_filing'],period_end=period)
        projection['reported_bridge'] = resolution.as_dict()
        resolution = project_converted_bridge(resolution, projection)
        balance = {**balance, 'preferred_equity':0.,
            'fully_diluted_shares_proxy':resolution.fully_diluted_shares,
            'bridge_precheck':resolution.as_dict(),
            'preferred_equity_basis':'no additional deduction under source-proven assumed conversion; not reported absence'}
    if not resolution.can_value:
        raise ValueError('current bridge has unresolved source fields: ' + ', '.join(resolution.blocking_fields))
    if reported_claim_scope is not None:
        from .refresh_reported_claim_scope import (
            project_reported_nci_scope,
            validate_reported_nci_scope,
        )
        claim_scope_proof = validate_reported_nci_scope(
            ticker=str(reported_claim_scope.get('ticker', '')),
            structural_packet=packet['structural_filing'],
            normalized_bridge=resolution,
            accession=claim_scope_proof['accession'],
            period_end=period,
        )
        projected = project_reported_nci_scope(
            ticker=str(reported_claim_scope.get('ticker', '')),
            policy=reported_claim_scope,
            normalized_bridge=resolution,
            proof=claim_scope_proof,
        )
        if projected != resolution:
            claim_scope_proof['reported_bridge_nci'] = resolution.noncontrolling_interests.midpoint
            claim_scope_proof['valuation_nci'] = projected.noncontrolling_interests.midpoint
            claim_scope_proof['negative_balance_treatment'] = reported_claim_scope.get('negative_balance_treatment')
            resolution = projected
            balance = {
                **balance,
                'noncontrolling_interests':resolution.noncontrolling_interests.midpoint,
                'bridge_precheck':resolution.as_dict(),
                'noncontrolling_interests_basis':'reported negative NCI retained diagnostically and not inverted into common-shareholder value',
            }
    return {'balance_sheet':balance, 'resolution':resolution.as_dict(), 'warnings':normalized.get('warnings', []),
            'structural_recovery':recovery_receipt,'capital_structure_projection':projection,
            'reported_claim_scope':claim_scope_proof,'aggregate_debt_scope':aggregate_debt_proof,
            'investment_scope':investment_scope_proof,'outside_equity_scope':outside_equity_proof,
            'preferred_equity_zero_scope':preferred_zero_proof,
            'preferred_lifecycle_scope':preferred_lifecycle_proof,
            'unconsolidated_vie_scope':unconsolidated_vie_proof}


def bridge_assessment(bridge: dict, recipe: dict, valued: dict,
                      cash_reserve_range: tuple[float,float,float] | None = None,
                      additional_claim_adjustment: float = 0.0,
                      share_adjustment: float = 0.0,
                      preferred_adjustment: float = 0.0) -> dict:
    resolution = BridgeResolution.from_dict(bridge['resolution'])
    if cash_reserve_range is not None:
        bear_reserve,base_reserve,bull_reserve=(number(value,'customer cash reserve') for value in cash_reserve_range)
        if not 0 <= bull_reserve <= base_reserve <= bear_reserve:
            raise ValueError('customer cash reserve must narrow from bear to bull')
        original=resolution.cash_and_investments
        cash=BridgeRange(original.low-bear_reserve,original.midpoint-base_reserve,original.high-bull_reserve)
        adjustment=BridgeRange(
            cash.low-resolution.total_debt.high-resolution.preferred_equity.high-resolution.noncontrolling_interests.high,
            cash.midpoint-resolution.total_debt.midpoint-resolution.preferred_equity.midpoint-resolution.noncontrolling_interests.midpoint,
            cash.high-resolution.total_debt.low-resolution.preferred_equity.low-resolution.noncontrolling_interests.low)
        reserve_is_range=not (bear_reserve==base_reserve==bull_reserve)
        bounded=(tuple(sorted(set((*resolution.bounded_fields,'cash'))))
                 if reserve_is_range else resolution.bounded_fields)
        blocking=resolution.blocking_fields
        resolution=BridgeResolution(
            complete=not blocking and not bounded,can_value=not blocking,
            missing_fields=tuple(sorted(set((*blocking,*bounded)))),
            blocking_fields=blocking,bounded_fields=bounded,cash_and_investments=cash,
            total_debt=resolution.total_debt,preferred_equity=resolution.preferred_equity,
            noncontrolling_interests=resolution.noncontrolling_interests,bridge_adjustment=adjustment,
            fully_diluted_shares=resolution.fully_diluted_shares,
            reason_codes=(tuple((*resolution.reason_codes,'CURRENT_NOTE_SUPPLIES_FINITE_RANGE'))
                          if reserve_is_range else resolution.reason_codes),
            policy_version=resolution.policy_version+'-CASH-RESERVE-1')
    spec = recipe['scenarios']['base']
    inputs = spec['inputs']
    if spec['engine'] == 'enterprise_cash_fcff':
        shares, cash, debt, preferred, nci = (inputs[key] for key in ('diluted_shares','cash_and_investments','interest_bearing_debt','preferred_equity','noncontrolling_interests'))
        model_shares,model_preferred=shares,preferred
        shares-=number(share_adjustment,'additional share adjustment')
        preferred-=number(preferred_adjustment,'additional preferred adjustment')
    elif spec['engine'] == 'constant_growth_fcff':
        shares, cash, debt, nci = (inputs[key] for key in ('shares','cash_and_investments','debt','noncontrolling_interests'))
        # This engine has one combined non-debt claim input. The binder adds
        # preferred and NCI there; split it only for source reconciliation.
        preferred = resolution.preferred_equity.midpoint
        nci -= preferred
        nci -= number(additional_claim_adjustment,'additional bridge claim adjustment')
    else:
        raise ValueError('enterprise bridge assessment requires an enterprise model')
    expected = (resolution.fully_diluted_shares, resolution.cash_and_investments.midpoint, resolution.total_debt.midpoint, resolution.preferred_equity.midpoint, resolution.noncontrolling_interests.midpoint)
    if any(not isclose(a,b,rel_tol=1e-9,abs_tol=1e-6) for a,b in zip((shares,cash,debt,preferred,nci),expected)):
        raise ValueError('recipe bridge does not reconcile to the normalized source bridge')
    # Keep separately fixed adjustments in the value available to this bridge;
    # otherwise its implied equity range would silently omit those claims.
    enterprise = valued['scenarios']['base']['raw_value'] * (model_shares if spec['engine']=='enterprise_cash_fcff' else shares) - cash + debt + (model_preferred if spec['engine']=='enterprise_cash_fcff' else preferred) + nci
    assessment = assess_bridge_materiality(resolution, enterprise_value=enterprise).as_dict()
    return {**assessment, 'complete':resolution.complete}
