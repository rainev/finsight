"""Opt-in, source-bounded financing series. No issuer-specific calculation code."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import json
import math
from .catalog import sha256_bytes,canonical_json_bytes
from .family_forecast import fact
from .xbrl import CompanyFactsNormalizer

VERSION='US-FINANCING-INPUT-ALIGNMENT-1'
NET_ALIASES=('InterestIncomeExpenseNet','InterestRevenueExpenseNet')


def aligned_view(n,concept):
    from .refresh_financials import _validate_ttm_alignment
    config=deepcopy(n.config);config['fields']['interest_expense']={'unit':'USD','kind':'flow','concepts':['us-gaap:'+concept]}
    selected=CompanyFactsNormalizer(n.companyfacts,concept_config=config,fiscal_year_end=n.fiscal_year_end,
        as_of_date=n.as_of_date,filing_records=n.filing_records)
    flow=selected.ttm_flow('interest_expense');_validate_ttm_alignment(flow)
    operating=n.annual_series('operating_cash_flow',5)
    annual=[a for a in selected.annual_series('interest_expense',5)
        if any((a.start,a.end,a.unit)==(b.start,b.end,b.unit) for b in operating)]
    if len(annual)<3:raise ValueError('aligned financing needs three recent matching annual cash periods')
    return selected,flow,annual


def net_role(packet,n,concept):
    net=fact(packet,[concept],flow=True);pretax=fact(packet,['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'],flow=True)
    operating=fact(packet,['OperatingIncomeLoss'],flow=True,optional=True)
    if operating is None:
        revenue=fact(packet,[s.split(':')[-1] for s in n.config['fields']['revenue']['concepts']],flow=True)
        cost=fact(packet,['CostOfGoodsAndServicesSold','CostOfRevenue'],flow=True);admin=fact(packet,['SellingGeneralAndAdministrativeExpense'],flow=True)
        operating={'value':revenue['value']-cost['value']-admin['value'],'period_start':revenue['period_start'],
            'period_end':revenue['period_end'],'operands':[revenue,cost,admin],'value_status':'derived'}
    for source in (pretax,operating):
        if (source['period_start'],source['period_end'])!=(net['period_start'],net['period_end']):
            raise ValueError('net-interest and operating/pretax periods differ')
    if not math.isclose(operating['value']+net['value'],pretax['value'],abs_tol=1.):
        raise ValueError('net-interest nonoperating scope/sign does not reconcile')
    return {'net':net,'operating':operating,'pretax':pretax,'income_positive':True}


@dataclass(frozen=True)
class DerivedFinancingFact:
    value: float
    start: str
    end: str
    sources: tuple
    unit: str='USD'

    def as_dict(self):
        return {'field':'interest_expense','namespace':'derived','concept':'interest_income_less_accrual_expense',
            'value':self.value,'start':self.start,'end':self.end,'unit':self.unit,'value_status':'derived',
            'sources':list(self.sources),'selection_reason':'Disjoint reported income less reported accrual expense, identical annual window.'}


class FinancingAnnualView:
    """Preserve the normalizer interface without inventing reported XBRL facts."""
    def __init__(self,base,annual):self.base=base;self.annual=annual
    def __getattr__(self,name):return getattr(self.base,name)
    def annual_series(self,field,count=5):
        return self.annual[-count:] if field=='interest_expense' else self.base.annual_series(field,count)
    def annual_at_end(self,field,end):
        if field!='interest_expense':return self.base.annual_at_end(field,end)
        return next((a for a in self.annual if a.end==end),None)


def reviewed_record(packet,policy):
    raw=Path(policy['review_path']).read_bytes()
    if sha256_bytes(raw)!=policy['review_sha256']:raise ValueError('reviewed financing record hash changed')
    review=json.loads(raw);acc=packet['controlling_filing']['accessionNumber']
    rows=[r for r in review['rows'] if r['filing']['accessionNumber']==acc]
    if len(rows)!=1:raise ValueError('reviewed financing record does not match current filing')
    record=rows[0]
    original={k:v for k,v in packet.items() if k not in ('event_review','_selected_controlling_filing')}
    if sha256_bytes(canonical_json_bytes(original))!=record['source_packet_sha256']:
        raise ValueError('reviewed financing source packet changed')
    for acc,h in record['source_documents'].items():
        docs=[d for d in packet['structural_receipts'] if d['accession']==acc]
        if len(docs)!=1 or sha256_bytes(Path(docs[0]['path']).read_bytes())!=h:
            raise ValueError('reviewed financing source document changed')
    return record


def align_financing_inputs(n,packet,policy):
    from .refresh_financials import _validate_ttm_alignment
    if policy.get('version')!=VERSION:raise ValueError('unsupported financing-alignment version')
    if str(n.companyfacts['cik']).zfill(10)!=str(packet['submissions']['cik']).zfill(10):
        raise ValueError('financing normalizer/source issuer mismatch')
    period=packet['controlling_filing']['reportDate'];mode=policy.get('mode')
    if not n.as_of_date or packet['controlling_filing']['filingDate']>n.as_of_date:
        raise ValueError('financing source is not eligible at the dated cutoff')
    if mode=='tagged_net':
        failures=[];eligible=[]
        for concept in NET_ALIASES:
            try:
                role=net_role(packet,n,concept);view,flow,annual=aligned_view(n,concept)
                if flow['period_end']!=period:raise ValueError('tagged net-interest series is not current')
                current=flow.get('current_ytd',flow['sources'][-1]);selected=role['net']
                if (current.get('accession')!=selected['source_accession'] or current.get('start')!=selected['period_start']
                    or current.get('end')!=selected['period_end'] or not math.isclose(current['value'],selected['value'],rel_tol=1e-12,abs_tol=.01)):
                    raise ValueError('net-interest aggregate feed differs from current structural source')
                flow={**flow,'financing_alignment':{'version':VERSION,'mode':mode,'role_proof':role,
                    'annual_periods':len(annual),'value_status':'derived_from_reported_components','basis':'net_nonoperating_interest'}}
                eligible.append((view,flow,'net_nonoperating_interest'))
            except ValueError as exc:failures.append(str(exc))
        if eligible:
            if any(not math.isclose(r[1]['value'],eligible[0][1]['value'],rel_tol=1e-12,abs_tol=.01) for r in eligible[1:]):
                raise ValueError('current role-qualified net-interest aliases conflict')
            return eligible[0]
        raise ValueError('no current role-qualified net-interest alias: '+'; '.join(failures))
    record=reviewed_record(packet,policy)
    if mode=='cash_paid_proxy':
        view,flow,annual=aligned_view(n,'InterestPaidNet')
        if flow['period_end']!=period or any(s['value']<0 for s in flow['sources']):raise ValueError('cash-paid proxy period/sign invalid')
        flow={**flow,'financing_alignment':{'version':VERSION,'mode':mode,'basis':'cash_interest_paid_proxy',
            'annual_periods':len(annual),'review_sha256':policy['review_sha256'],
            'warning':'Cash paid is not accrual expense; explicit basis selection is required before valuation use.'}}
        return view,flow,'cash_interest_paid_proxy'
    if mode not in ('reviewed_net_components','reviewed_gross_components'):raise ValueError('unsupported financing-alignment mode')
    tables=record.get('reviewed_interest_tables');corroboration=record.get('table_corroboration')
    if not tables or not corroboration:raise ValueError('reviewed disjoint interest-table evidence missing')
    for table in tables.values():
        if 'million' not in table['unit_caption'].lower():raise ValueError('reviewed table units unavailable')
        data={r['label']:r['signed_displayed_millions'] for r in table['rows']}
        total=data.get('Total',data.get('Total other (expense) income, net'))
        for i in (0,1):
            if data['Interest income'][i]+data['Interest expense'][i]+data['Other, net'][i]!=total[i]:
                raise ValueError('reviewed financing subtotal does not reconcile')
    expense_concept=corroboration['annual_tagged_interest_expense']['qname'].split(':')[-1]
    income_concept=corroboration['annual_tagged_interest_income']['qname'].split(':')[-1]
    config=deepcopy(n.config);config['fields']['interest_expense']={'kind':'flow','unit':'USD','concepts':['us-gaap:'+expense_concept]}
    config['fields']['reviewed_interest_income']={'kind':'flow','unit':'USD','concepts':['us-gaap:'+income_concept]}
    history=CompanyFactsNormalizer(n.companyfacts,concept_config=config,fiscal_year_end=n.fiscal_year_end,
        as_of_date=n.as_of_date,filing_records=n.filing_records)
    annual=[]
    for operating in n.annual_series('operating_cash_flow',5):
        expense=history.annual_at_end('interest_expense',operating.end)
        income=history.annual_at_end('reviewed_interest_income',operating.end)
        if expense is None or income is None:continue
        if any((s.start,s.end,s.unit)!=(operating.start,operating.end,operating.unit) for s in (income,expense)):
            raise ValueError('reviewed financing annual component periods differ')
        annual.append(DerivedFinancingFact(income.value-expense.value,operating.start,operating.end,
            (income.as_dict(),expense.as_dict())) if mode=='reviewed_net_components' else expense)
    if len(annual)<3:raise ValueError('reviewed financing needs three matched annual periods')
    cash_dates=record['candidates'][0]['flow'];reference_annual,current,prior=cash_dates['sources']
    if annual[-1].end!=reference_annual['end']:raise ValueError('reviewed annual/current transition differs')
    days=[(date.fromisoformat(s['end'])-date.fromisoformat(s['start'])).days+1 for s in (current,prior)]
    if 'Three Months' not in tables['current']['period_header'] or any(not 75<=d<=105 for d in days):
        raise ValueError('quarter-only reviewed note cannot replace a cumulative YTD series')
    values={r['label']:r['displayed_millions'] for r in tables['current']['rows']}
    current_value=(values['Interest income'][0]-values['Interest expense'][0]) if mode=='reviewed_net_components' else values['Interest expense'][0]
    prior_value=(values['Interest income'][1]-values['Interest expense'][1]) if mode=='reviewed_net_components' else values['Interest expense'][1]
    def observed(value,source,column):
        return {'field':'interest_expense','value':value*1e6,'start':source['start'],'end':source['end'],'unit':'USD',
            'accession':packet['controlling_filing']['accessionNumber'],'value_status':'reviewed_table_observation',
            'review_sha256':policy['review_sha256'],'table_index':tables['current']['table_index'],'column':column}
    sources=[annual[-1].as_dict(),observed(current_value,current,'current'),observed(prior_value,prior,'comparative')]
    value=sources[0]['value']+sources[1]['value']-sources[2]['value'];radius=3e6 if mode=='reviewed_net_components' else 1.5e6
    flow={'value':value,'period_end':period,'method':'latest_fy_plus_current_ytd_minus_prior_ytd','sources':sources,
        'current_ytd':sources[1],'prior_ytd':sources[2],'financing_alignment':{'version':VERSION,'mode':mode,
            'income_or_expense_uncertainty':{'low':value-radius,'midpoint':value,'high':value+radius},
            'annual_periods':len(annual),'review_sha256':policy['review_sha256'],'value_status':'derived',
            'calendar_warning':'Keep actual fiscal quarter durations; current/prior are '+str(days)+' days.'}}
    flow['financing_alignment']['before_tax_adjustment_uncertainty']=(
        {'low':-(value+radius),'midpoint':-value,'high':-(value-radius)} if mode=='reviewed_net_components'
        else {'low':value-radius,'midpoint':value,'high':value+radius})
    _validate_ttm_alignment(flow)
    return FinancingAnnualView(n,annual),flow,'net_nonoperating_interest' if mode=='reviewed_net_components' else 'gross_expense_proxy'
