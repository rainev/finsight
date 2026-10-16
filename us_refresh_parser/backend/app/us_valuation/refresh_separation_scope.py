"""Source-bound separation classification; incomplete continuing scope stays blocked."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, date
from math import isfinite
import json
from pathlib import Path
import re

from .arelle_worker import _QNameCanonicalizer
from .calculation_recipe import evaluate_recipe

VERSION = 'FINSIGHT-SEPARATION-SCOPE-WG36-1'
POLICIES = {'HON': {'version': VERSION, 'ticker': 'HON', 'cik': '0000773840',
    'distribution_name': 'Aerospace', 'acquisition_name': 'Johnson Matthey',
    'economic_scope': 'continuing_parent_after_distribution_and_acquisition'}}


def separation_policy(ticker):
    return deepcopy(POLICIES[ticker])


def extract_separation_terms(text, policy):
    from .refresh_narrative_evidence import _one, _term, _section
    terms = []
    sections = []
    def add(section, offset, name, pattern, value, unit, title):
        terms.append(_term(section, pattern, offset=offset, name=name, value=value, unit=unit, section_name=title))
    d = r'[A-Z][a-z]+ \d{1,2}, \d{4}'
    def iso(value): return datetime.strptime(value, '%B %d, %Y').date().isoformat()
    basis, start, end = _section(text, r'NOTE 1\. BASIS OF PRESENTATION In the opinion', 'NOTE 2.')
    sections.append({'name':'Basis of presentation', 'normalized_text_start':start, 'normalized_text_end':end})
    pattern = rf'closing dates for the three and six months ended {d} and \d{{4}}, were (?P<current>{d}) and (?P<prior>{d}), respectively'
    m = _one(basis, pattern, offset=start, name='actual_close')
    add(basis,start,'actual_close',pattern,{'current':iso(m['current']),'comparative':iso(m['prior'])},'date','Basis of presentation')
    pattern = rf'In the third quarter on (?P<date>{d}), following the Aerospace Spin-Off.*?the Reverse Stock Split became effective'
    m = _one(basis,pattern,offset=start,name='split_date')
    add(basis,start,'split_date',pattern,iso(m['date']),'date','Basis of presentation')
    pattern = r'every two shares of common stock issued and outstanding or held by Honeywell Technologies as treasury shares were automatically combined into one share of common stock'
    add(basis,start,'split_ratio',pattern,0.5,'ratio','Basis of presentation')
    pattern = r'All share and per share amounts have been retrospectively adjusted to reflect the Reverse Stock Split for all periods presented'
    add(basis,start,'reported_shares_already_adjusted',pattern,True,'classification','Basis of presentation')
    acquisition, astart, aend = _section(text,r'ACQUISITIONS Johnson Matthey[’\']s Catalyst Technologies Business', 'Sundyne')
    sections.append({'name':'Acquisition', 'normalized_text_start':astart,'normalized_text_end':aend})
    pattern = rf'On (?P<date>{d}), the Company acquired (?P<percent>[0-9.]+) % .*?total consideration of \$ (?P<amount>[0-9,]+) million, net of cash acquired'
    m = _one(acquisition,pattern,offset=astart,name='acquisition_close')
    add(acquisition,astart,'acquisition_close',pattern,{'date':iso(m['date']),'ownership_percent':float(m['percent']),'consideration_net_cash_acquired':float(m['amount'].replace(',',''))*1e6},'USD/date/percent','Acquisition')
    pattern = r'preliminary purchase price allocation required by ASC 805, Business Combinations , will be disclosed within the financial statements for the period ending (?P<date>'+d+r')'
    m = _one(acquisition,pattern,offset=astart,name='pending_allocation')
    add(acquisition,astart,'pending_allocation',pattern,iso(m['date']),'date','Acquisition')
    quantinuum, qstart, qend = _section(text,rf'Quantinuum On {d}, the Company[’\']s former consolidated subsidiary', 'Productivity Solutions and Services and Warehouse and Workflow Solutions Businesses')
    sections.append({'name':'Quantinuum deconsolidation','normalized_text_start':qstart,'normalized_text_end':qend})
    pattern=r'No cash contributions were made or cash distributions received by the Company as part of the IPO'
    add(quantinuum,qstart,'ipo_cash_received',pattern,0.0,'USD_reported_zero','Quantinuum deconsolidation')
    quant_values={}
    for name,pattern in (
        ('gain',r'recognized a gain of \$ (?P<amount>[0-9,]+) million'),
        ('retained_investment',r'initial fair value of the retained investment of \$ (?P<amount>[0-9,]+) million'),
        ('removed_nci',r'carrying value of the non-controlling interest in the former subsidiary was \$ (?P<amount>[0-9,]+) million'),
        ('removed_net_assets',r'carrying value of Quantinuum[’\']s net assets was \$ (?P<amount>[0-9,]+) million')):
        m=_one(quantinuum,pattern,offset=qstart,name=name)
        quant_values[name]=float(m['amount'].replace(',',''))*1e6
        add(quantinuum,qstart,'quantinuum_'+name,pattern,quant_values[name],'USD_nonadditive','Quantinuum deconsolidation')
    if quant_values['retained_investment']+quant_values['removed_nci']-quant_values['removed_net_assets']!=quant_values['gain']:
        raise ValueError('Quantinuum accounting rollforward conflicts')
    distribution, sstart, send = _section(text,rf'Aerospace Technologies Business In the third quarter on {d}, the Company completed the previously announced separation', 'NOTE 4.')
    sections.append({'name':'Aerospace distribution','normalized_text_start':sstart,'normalized_text_end':send})
    pattern = rf'on (?P<date>{d}), the Company completed the previously announced separation'
    m = _one(distribution,pattern,offset=sstart,name='distribution_date')
    add(distribution,sstart,'distribution_date',pattern,iso(m['date']),'date','Aerospace distribution')
    pattern = r'one share of Honeywell Aerospace common stock for every two shares of Honeywell Technologies common stock'
    add(distribution,sstart,'distributed_share_ratio',pattern,0.5,'subsidiary_share_per_presplit_parent_share','Aerospace distribution')
    pattern = r'our financial results include the assets, liabilities, and operating results of Honeywell Aerospace as continuing operations'
    add(text,0,'reported_scope_includes_distributed_business',pattern,True,'classification','Reporting perimeter disclosure')
    pattern = r'aggregate amount of \$ (?P<total>[0-9.]+) billion over a period of less than five years , with an initial payment of \$ (?P<initial>[0-9.]+) million due within five days of the distribution date followed by (?P<count>\d+) equal monthly payments of \$ (?P<payment>[0-9.]+) million'
    m = _one(distribution,pattern,offset=sstart,name='trademark_payments')
    terms_value = {'total':float(m['total'])*1e9,'initial':float(m['initial'])*1e6,'initial_due_within_days':5,'monthly_count':int(m['count']),'monthly_payment':float(m['payment'])*1e6,'actual_cash_received':None}
    if terms_value['total'] != terms_value['initial'] + terms_value['monthly_count']*terms_value['monthly_payment']:
        raise ValueError('trademark payment schedule does not reconcile')
    add(distribution,sstart,'trademark_payments',pattern,terms_value,'USD/relative_schedule','Aerospace distribution')
    for name,pattern in (
        ('conditional_nonrenewal_reimbursement',r'If Honeywell Aerospace elects not to renew.*?reimburse Honeywell Aerospace \$ (?P<amount>[0-9.]+) million unless certain exceptions apply'),
        ('conditional_termination_reimbursement',r'on the 6th anniversary of the distribution date, in which case Honeywell Technologies is obligated to reimburse Honeywell Aerospace \$ (?P<amount>[0-9.]+) million')):
        m = _one(distribution,pattern,offset=sstart,name=name)
        add(distribution,sstart,name,pattern,float(m['amount'])*1e6,'USD_conditional_not_current_claim','Aerospace distribution')
    return terms, sections


def bind_separation_scope(policy, structural, narrative, recipe, *, source_root, cutoff):
    from .refresh_narrative_evidence import narrative_policy, validate_narrative_evidence, terms_by_name
    from .refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES, reported_nci_field_availability
    if policy != POLICIES.get(policy.get('ticker')):
        raise ValueError('separation policy identity mismatch')
    cutoff = date.fromisoformat(cutoff).isoformat()
    receipt = validate_narrative_evidence(narrative,narrative_policy(policy['ticker']),source_root=Path(source_root))
    filing = receipt['filing']; acc = filing['accession']; period = filing['report_date']
    if (structural.get('source_accession')!=acc or structural.get('report_date')!=period
        or structural.get('filed_date')!=filing['filed_date'] or structural.get('form')!=filing['form']
        or filing['form'] not in {'10-Q','10-Q/A'} or not period<=filing['filed_date']<=cutoff
        or recipe.get('ticker')!=policy['ticker'] or recipe.get('source_accession')!=acc):
        raise ValueError('separation source/recipe identity or cutoff mismatch')
    manifest=json.loads((Path(source_root)/receipt['source']['package_manifest_path']).read_bytes())
    if dict(structural.get('filing_metadata',())).get('package_generation')!=manifest.get('generation'):
        raise ValueError('separation parser package mismatch')
    t = {k:v['value'] for k,v in terms_by_name(receipt).items()}
    actual_close=t['actual_close']['current']; event=t['distribution_date']
    if not actual_close < event == t['split_date'] <= filing['filed_date'] <= cutoff:
        raise ValueError('separation chronology requires review')
    if not period < t['acquisition_close']['date'] <= filing['filed_date'] <= cutoff:
        raise ValueError('subsequent acquisition chronology requires review')
    if not t['reported_shares_already_adjusted'] or not t['reported_scope_includes_distributed_business']:
        raise ValueError('separation reporting scope changed; rule requires review')
    canon=_QNameCanonicalizer()
    def facts(local,unit,kind):
        rows=[r for r in structural['facts'] if r.get('local_name')==local and not r.get('dimensions') and r.get('period_end')==period
              and ((r.get('period_start') is None) if kind=='instant' else (isinstance(r.get('period_start'),str) and r['period_start']<period))]
        if not rows:raise ValueError('missing separation source fact: '+local)
        for r in rows:
            ns=str(r.get('namespace',''))
            if (r.get('unit') not in unit or r.get('source_accession')!=acc or r.get('entity_scheme')!='http://www.sec.gov/CIK'
                or str(r.get('entity_identifier','')).zfill(10)!=policy['cik']
                or r.get('qname')!=canon.prefix(ns)+':'+local
                or not re.fullmatch(r'https?://(?:fasb\.org/us-gaap|xbrl\.sec\.gov/dei)/20\d{2}',ns)
                or isinstance(r.get('value'),bool) or not isinstance(r.get('value'),(int,float)) or not isfinite(r['value'])):
                raise ValueError('invalid separation fact identity/unit: '+local)
            roles=r.get('statement_roles',[])
            if kind=='duration' and local!='WeightedAverageNumberOfDilutedSharesOutstanding' and 'cash_flow' not in roles:
                raise ValueError('separation cash-flow presentation missing')
            if local in {'CashAndCashEquivalentsAtCarryingValue','MinorityInterest','ShortTermBorrowings'} and 'balance_sheet' not in roles:
                raise ValueError('separation balance-sheet presentation missing')
        by_context={}
        for r in rows:
            key=(r['context_id'],r.get('period_start'),r['period_end'])
            if key in by_context and by_context[key]!=r['value']:
                # Different rounded presentations are retained only as raw debt
                # diagnostics; they are never selected/summed into a new bridge.
                if local!='ShortTermBorrowings':raise ValueError('separation fact conflict')
            by_context[key]=r['value']
        return list({json.dumps(r,sort_keys=True):r for r in rows}.values())
    ledger={}
    for name in ('CashAndCashEquivalentsAtCarryingValue','LongTermDebt','ShortTermBorrowings','MinorityInterest'):
        ledger[name]=facts(name,{'USD'},'instant')
    for name in ('NetCashProvidedByUsedInOperatingActivities','PaymentsToAcquirePropertyPlantAndEquipment','CashDivestedFromDeconsolidation','DeconsolidationGainOrLossAmount'):
        ledger[name]=facts(name,{'USD'},'duration')
    ledger['reported_cover_shares']=facts('EntityCommonStockSharesOutstanding',{'shares','xbrli:shares'},'instant')
    ledger['reported_diluted_shares']=facts('WeightedAverageNumberOfDilutedSharesOutstanding',{'shares','xbrli:shares'},'duration')
    _, ownership=reported_nci_field_availability(ticker=policy['ticker'],policy=asdict(REPORTED_NCI_SCOPE_RULES[policy['ticker']]),structural_packet=structural,accession=acc,period_end=period)
    return {'version':VERSION,'ticker':policy['ticker'],'status':'separation_continuing_scope_requires_reconciliation',
        'filing':filing,'actual_accounting_close':actual_close,'terms':t,'source_receipt_sha256':receipt['receipt_sha256'],
        'reported_pre_distribution_ledger':ledger,'ordinary_nci_proof':ownership,
        'debt_presentation_treatment':'retain rounded and detailed borrowing presentations as alternatives; no new debt total selected',
        'share_treatment':'reported shares already retrospectively adjusted; no second split multiplication',
        'distributed_balances':None,'continuing_parent_fcff':None,'post_acquisition_cash_debt':None,
        'acquired_fcff':None,'synergies':None,'claim_adjustment':None,'numeric_successor_issued':False,
        'historical_range_only':evaluate_recipe(recipe)['range'],
        'review_reasons':['continuing_parent_cash_flow_excluding_aerospace_not_reconciled',
            'distributed_assets_liabilities_cash_debt_nci_not_reconciled',
            'acquisition_paid_cash_financing_and_post_close_balances_not_reconciled',
            'acquired_operating_cash_flow_and_purchase_allocation_unavailable',
            'trademark_receipts_taxes_and_forecast_overlap_unreconciled',
            'quantinuum_deconsolidation_is_separate_from_aerospace_distribution']}
