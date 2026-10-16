"""Source-linked recorded debt rows, ownership reconciliation and cash-only scope."""
from pathlib import Path
import re
from math import isclose
from bs4 import BeautifulSoup
from datetime import date
from decimal import Decimal
from .family_forecast import fact,common_class_par
from .bridge_policy import BridgeResolution,BridgeRange
from .catalog import sha256_bytes

VERSION='US-SHARED-STATEMENT-BRIDGE-1'
RECONCILED_VERSION='US-SHARED-STATEMENT-BRIDGE-2'
SEPARATE_ROWS_VERSION='US-SHARED-STATEMENT-BRIDGE-3'


def source_radius(packet, source):
    """Use the filing's reported rounding, not a fixed dollar tolerance."""
    if 'operands' in source:
        return sum(source_radius(packet, s) for s in source['operands'])
    acc=packet['controlling_filing']['accessionNumber']
    structure=packet.get('structural_packets',{}).get(acc) or packet['structural_filing']
    rows=[r for r in structure['facts'] if r.get('qname')==source.get('qname')
          and r.get('context_id')==source.get('context_id') and r.get('value')==source.get('value')
          and r.get('source_accession')==acc]
    if not rows:raise ValueError('rounding provenance unavailable')
    def radius(row):
        precision=str(row.get('decimals'))
        if precision=='INF':return 0.
        if not re.fullmatch(r'-?\d{1,2}',precision) or not -9<=int(precision)<=6:
            raise ValueError('explicit supported reported precision is required')
        return .5*10**-int(precision)
    return min(radius(r) for r in rows)


def derived_liability_components(packet,table,selected):
    """Sum disclosed rows; the equity identity checks rather than creates total."""
    after_current=False;finished=False;rows=[]
    current=fact(packet,['LiabilitiesCurrent']);assets=fact(packet,['Assets']);parent=fact(packet,['StockholdersEquity'])
    for tr in table.find_all('tr'):
        cells=tr.find_all(['td','th'],recursive=False)
        label=next((' '.join(c.stripped_strings) for c in cells if ' '.join(c.stripped_strings)),'')
        sources=list({s['qname']:s for _,s in selected(tr)}.values())
        if any(s['qname']=='us-gaap:LiabilitiesCurrent' for s in sources):after_current=True;continue
        if not after_current:continue
        if re.match(r'^(?:stockholders|shareholders|stockholder|shareholder)[’\x27s ]*\s*(?:equity|deficit|investment)',label,re.I):
            finished=True;break
        sources=[s for s in sources if s['qname']!='us-gaap:CommitmentsAndContingencies']
        if not sources:
            tags=tr.find_all(lambda t:t.name and t.name.lower().endswith('nonfraction'))
            if any(t.get('name') and t.get('name','').split(':')[-1]!='CommitmentsAndContingencies'
                   and str(t.get('xsi:nil','false')).lower() not in ('true','1') for t in tags):
                raise ValueError('unselected noncurrent liability row: '+label[:80])
            continue
        if len(sources)!=1:raise ValueError('ambiguous liability row: '+label[:80])
        source=sources[0]
        if source['value']<0:raise ValueError('negative liability component needs separate classification')
        if any(r['source']['qname']==source['qname'] for r in rows):raise ValueError('duplicate or nested liability component')
        rows.append({'label':label,'source':source})
    if not finished or not rows:raise ValueError('complete noncurrent liability section not proven')
    components=[current,*[r['source'] for r in rows]]
    total=float(sum(Decimal(str(s['value'])) for s in components))
    equity=fact(packet,['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],optional=True) or parent
    residual=assets['value']-total-equity['value']
    tolerance=sum(source_radius(packet,s) for s in [assets,equity,*components])
    if abs(residual)>tolerance:raise ValueError('independent liability component sum does not close the balance sheet')
    return {'value':total,'qname':'derived:liability_component_sum','unit':'USD',
        'period_end':packet['controlling_filing']['reportDate'],'operands':components,
        'classification':'derived_not_reported_total','noncurrent_rows':rows,
        'balance_sheet_residual':residual,'reported_rounding_tolerance':tolerance}


def statement_rows(packet,*,reconciled=False):
    filing=packet['controlling_filing'];acc=filing['accessionNumber'];period=filing['reportDate']
    receipts=[r for r in packet.get('structural_receipts',[]) if r['accession']==acc]
    if len(receipts)!=1:raise ValueError('current statement document provenance incomplete')
    receipt=receipts[0];raw=Path(receipt['path']).read_bytes()
    if sha256_bytes(raw)!=receipt['raw_payload_sha256']:raise ValueError('current statement source bytes changed')
    structure=packet.get('structural_packets',{}).get(acc) or packet['structural_filing']
    usable={}
    for f in structure['facts']:
        if (f.get('period_end')!=period or f.get('period_start') or f.get('dimensions')
            or f.get('unit')!='USD' or f.get('source_accession')!=acc
            or not re.fullmatch(r'https?://fasb.org/us-gaap/20\d{2}',str(f.get('namespace','')))):continue
        try:s=fact(packet,[f['local_name']],optional=True)
        except ValueError:continue
        if s:usable[(f['local_name'],f['context_id'])]=s
    soup=BeautifulSoup(raw,'html.parser');tables=[]
    def selected(table):
        found=[]
        for tag in table.find_all(lambda t:t.name and t.name.lower().endswith('nonfraction')):
            name=tag.get('name','').split(':')[-1];context=tag.get('contextref');s=usable.get((name,context))
            if s:found.append((tag,s))
        return found
    for table in soup.find_all('table'):
        sources=selected(table);names={s['qname'].split(':')[-1] for _,s in sources}
        if 'Assets' in names and 'LiabilitiesAndStockholdersEquity' in names and names.intersection({'StockholdersEquity','RetainedEarningsAccumulatedDeficit','LiabilitiesCurrent'}):
            tables.append((len(table.get_text()),table))
    if tables:table=min(tables,key=lambda x:x[0])[1]
    else:
        # Some filings split assets and liabilities across adjacent page tables.
        candidates=[]
        for t in soup.find_all('table'):
            names={s['qname'].split(':')[-1] for _,s in selected(t)}
            if 'LiabilitiesAndStockholdersEquity' in names and 'LiabilitiesCurrent' in names:candidates.append((len(t.get_text()),t))
        if not candidates:raise ValueError('complete current financial-position table unavailable')
        table=min(candidates,key=lambda x:x[0])[1]
    rows=[];in_liabilities=False
    for tr in table.find_all('tr'):
        cells=tr.find_all(['td','th'],recursive=False)
        label=next((' '.join(c.stripped_strings) for c in cells if ' '.join(c.stripped_strings)), '')
        if re.match(r'^(?:current )?liabilities\b',label,re.I):in_liabilities=True
        if re.match(r'^(?:stockholders|shareholders|stockholder|shareholder)[’\x27s ]* (?:equity|investment)',label,re.I):in_liabilities=False
        if not in_liabilities:continue
        sources=[s for _,s in selected(tr)]
        debt_sources=[s for s in sources if re.search(r'Debt|Borrow|CommercialPaper|FinanceLeaseLiability|CapitalLeaseObligation|NotesPayable',s['qname'])]
        if not debt_sources and not re.search(r'debt|borrowings|commercial paper|(?:finance|capital) lease|notes payable',label,re.I):continue
        if not debt_sources:raise ValueError('recorded borrowing row has no selectable current source: '+label[:90])
        values={s['value'] for s in debt_sources}
        if len(values)!=1:raise ValueError('recorded borrowing row has ambiguous amounts')
        source=debt_sources[0]
        if source['value']<0:raise ValueError('negative recorded borrowing liability')
        rows.append({'label':label,'value':source['value'],'source':source,
                     'includes_finance_leases':bool(re.search(r'(?:finance|capital) lease',label,re.I)
                          or 'FinanceLease' in source['qname'] or 'CapitalLease' in source['qname'])})
    # A recorded liability must appear only once; note references and repeated
    # table wrappers cannot make it a second debt deduction.
    distinct={}
    for r in rows:
        key=(r['source']['qname'],r['source']['context_id'])
        distinct[key]=r
    rows=list(distinct.values())
    for subtotal in list(rows):
        name=subtotal['source']['qname'].split(':')[-1]
        if name!='DebtCurrent':continue
        components=[r for r in rows if r is not subtotal and r['source']['qname'].split(':')[-1]
                    in {'LongTermDebtCurrent','LongTermDebtAndCapitalLeaseObligationsCurrent','ShortTermBorrowings','CommercialPaper','FinanceLeaseLiabilityCurrent'}]
        if components:
            if not isclose(subtotal['value'],sum(r['value'] for r in components),rel_tol=1e-10,
                           abs_tol=sum(source_radius(packet,r['source']) for r in [subtotal,*components])):
                raise ValueError('current debt subtotal and component coverage does not reconcile')
            subtotal['includes_finance_leases']=all(r['includes_finance_leases'] for r in components)
            rows=[r for r in rows if r not in components]
    totals=[r for r in rows if re.match(r'^total\s+(?:interest[- ]bearing\s+)?debt\b',r['label'],re.I)]
    if totals and len(rows)>1:
        if len(totals)!=1 or not isclose(totals[0]['value'],sum(r['value'] for r in rows if r is not totals[0]),rel_tol=1e-10,abs_tol=sum(source_radius(packet,r['source']) for r in rows)):
            raise ValueError('debt total and component rows have ambiguous coverage')
        totals[0]['includes_finance_leases']=all(r['includes_finance_leases'] for r in rows if r is not totals[0])
        rows=totals
    text=' '.join(soup.stripped_strings)
    derived=None
    if reconciled and fact(packet,['Liabilities'],optional=True) is None and fact(packet,['LiabilitiesNoncurrent'],optional=True) is None:
        derived=derived_liability_components(packet,table,selected)
    operating_sentence=None
    if reconciled:
        candidate=re.search(r'\bAll leases are classified as operating leases\b[^.;]*[.;]',text,re.I)
        if candidate and not re.search(r'\bexcept\b|excluding|other than|unless|(?:finance|capital) leases',candidate.group(),re.I):
            operating_sentence=candidate.group()
            # Even a dimensioned positive claim contradicts an all-operating
            # statement. Do not let a wording match erase reported debt.
            if any(f.get('period_end')==period and not f.get('period_start')
                   and re.search(r'FinanceLeaseLiability|CapitalLeaseObligations',f.get('local_name',''))
                   and isinstance(f.get('value'),(int,float)) and f['value']>0 for f in structure['facts']):
                raise ValueError('operating-only disclosure conflicts with finance-lease balances')
    cash_rows=[]
    for t in soup.find_all('table'):
        names={s['qname'].split(':')[-1] for _,s in selected(t)}
        if 'Assets' not in names:continue
        for tr in t.find_all('tr'):
            cells=tr.find_all(['td','th'],recursive=False)
            label=next((' '.join(c.stripped_strings) for c in cells if ' '.join(c.stripped_strings)), '')
            if not re.match(r'^cash and cash equivalents\b',label,re.I) or re.search(r'restricted|investments',label,re.I):continue
            candidates=[s for _,s in selected(tr) if s['qname'].split(':')[-1] in {
                'CashAndCashEquivalentsAtCarryingValue','CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents','CashCashEquivalentsAndShortTermInvestments'}]
            if len({s['value'] for s in candidates})==1:cash_rows.append({'label':label,'source':candidates[0]})
    cash_row=cash_rows[0] if cash_rows and len({r['source']['value'] for r in cash_rows})==1 else None
    d=date.fromisoformat(period);dated=re.escape(d.strftime('%B')+f' {d.day}, {d.year}')
    result={'debt_rows':rows,'document_sha256':receipt['raw_payload_sha256'],
        'cash_balance_row':cash_row,
        'all_leases_operating':bool(operating_sentence or re.search(r'(?:all (?:of )?(?:our|the company[’\x27]s) leases (?:are|were) (?:classified as )?operating leases|(?:we|the company) (?:have|has|had) no finance leases)\s*[.;]',text,re.I)),
        'explicit_no_debt':bool(re.search(r'(?:we|the company) (?:have|has|had) no (?:outstanding )?debt(?: outstanding)? (?:as of|at)\s+'+dated,text,re.I)
            or re.search(r'(?:we|the company) (?:have|has) no (?:outstanding )?debt(?: outstanding)?\s*[.;]',text,re.I))}
    if reconciled:result.update(derived_liabilities=derived,operating_only_sentence=operating_sentence)
    return result


def shared_bridge(packet,scope):
    version=scope.get('version')
    from .staged_lease_fallback import VERSION as STAGED_VERSION, claim_envelope
    if version not in (VERSION,RECONCILED_VERSION,SEPARATE_ROWS_VERSION,STAGED_VERSION) or scope.get('cash_scope')!='reported_cash_only':raise ValueError('unsupported shared bridge scope')
    disclosure=statement_rows(packet,reconciled=True) if version!=VERSION else statement_rows(packet)
    sources={}
    def reconciles(left,right,*operands):
        return isclose(left,right,rel_tol=1e-10,abs_tol=sum(source_radius(packet,s) for s in operands)+1e-8)
    def get(key,names,optional=False):
        r=fact(packet,names,optional=optional)
        if r:sources[key]=r
        return r
    cash=get('cash',['CashAndCashEquivalentsAtCarryingValue'],True)
    if cash is None:
        if disclosure['cash_balance_row'] is None:raise ValueError('cash-only financial-position row scope incomplete')
        cash=disclosure['cash_balance_row']['source'];sources['cash_row_scope']=disclosure['cash_balance_row']
    assets=get('assets',['Assets']);parent=get('parent_equity',['StockholdersEquity'])
    liab=get('liabilities',['Liabilities'],True)
    if liab is None:
        current=get('current_liabilities',['LiabilitiesCurrent'],True);noncurrent=get('noncurrent_liabilities',['LiabilitiesNoncurrent'],True)
        if current is not None and noncurrent is not None:
            liab={'value':current['value']+noncurrent['value'],'operands':[current,noncurrent]}
        elif disclosure.get('derived_liabilities') is not None:liab=disclosure['derived_liabilities']
        else:raise ValueError('shared ownership bridge requires a reported total liability scope')
        sources['liabilities']=liab
    group=get('group_equity',['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],True)
    outside=assets['value']-liab['value']-parent['value']
    nci=get('minority',['MinorityInterest'],True)
    if group:
        if not reconciles(assets['value']-liab['value'],group['value'],assets,liab,group):
            raise ValueError('shared consolidated equity scope does not reconcile to assets less liabilities')
        difference=group['value']-parent['value']
        if nci is not None and not reconciles(difference,nci['value'],group,parent,nci):raise ValueError('reported minority claim differs from group/parent reconciliation')
        if not reconciles(difference,outside,group,parent,assets,liab):raise ValueError('outside-equity allocation remains incomplete')
        minority=max(difference,0.)
    elif nci is not None:
        if not reconciles(outside,nci['value'],assets,liab,parent,nci):raise ValueError('outside parent equity does not reconcile to reported minority')
        minority=max(nci['value'],0.)
    elif reconciles(outside,0.,assets,liab,parent):
        minority=0.;sources['minority_zero_reconciliation']={'assets':assets,'liabilities':liab,'parent':parent}
    else:raise ValueError('outside parent equity claims require an allocation')
    pref=get('preferred',['PreferredStockValue'],True)
    issued=get('preferred_shares',['PreferredStockSharesIssued','PreferredStockSharesOutstanding'],True)
    if issued is not None and issued['value']>0 and (pref is None or pref['value']<=0):
        raise ValueError('issued preferred shares have an unresolved claim')
    if pref is None:
        if issued is not None and issued['value']==0:preferred=0.
        else:
            combined=get('common_paid_capital',['CommonStocksIncludingAdditionalPaidInCapital'],True)
            if combined is None:
                par=get('common_par',['CommonStockValue'],True);apic=get('common_apic',['AdditionalPaidInCapitalCommonStock','AdditionalPaidInCapital'],True)
                if par is None:par=common_class_par(packet)
                if par is None or apic is None:raise ValueError('preferred/common paid capital scope incomplete')
                combined={'value':par['value']+apic['value'],'operands':[par,apic]}
            retained=get('retained',['RetainedEarningsAccumulatedDeficit'])
            aoci=get('aoci',['AccumulatedOtherComprehensiveIncomeLossNetOfTax'],True);treasury=get('treasury',['TreasuryStockValue','TreasuryStockCommonValue'],True)
            common=combined['value']+retained['value']+(aoci['value'] if aoci else 0)-(treasury['value'] if treasury else 0)
            if not reconciles(common,parent['value'],combined,retained,parent,*[s for s in (aoci,treasury) if s]):raise ValueError('common equity components do not exhaust parent equity')
            preferred=0.;sources['preferred_zero_reconciliation']={'common_component_total':common,'parent':parent,'sources':list(sources)}
    else:preferred=pref['value']
    if min(cash['value'],preferred)<0:raise ValueError('negative cash/preferred bridge amount')
    rows=disclosure['debt_rows']
    if not rows:
        if not disclosure['explicit_no_debt']:raise ValueError('recorded debt scope empty without a no-debt disclosure')
        ordinary=0.;includes_lease=False
    else:
        ordinary=sum(r['value'] for r in rows);includes_lease=all(r['includes_finance_leases'] for r in rows)
        if version not in (SEPARATE_ROWS_VERSION,STAGED_VERSION) and any(r['includes_finance_leases'] for r in rows) and not includes_lease:
            raise ValueError('partially embedded finance leases require disjoint claim coverage')
    lease_total=get('finance_lease_total',['FinanceLeaseLiability','FinanceLeaseLiabilityPaymentsDuePresentValue','CapitalLeaseObligations'],True)
    lease_current=get('finance_lease_current',['FinanceLeaseLiabilityCurrent','CapitalLeaseObligationsCurrent'],True)
    lease_noncurrent=get('finance_lease_noncurrent',['FinanceLeaseLiabilityNoncurrent','CapitalLeaseObligationsNoncurrent'],True)
    separate_proof=None
    if version==SEPARATE_ROWS_VERSION:
        names={'FinanceLeaseLiabilityCurrent','FinanceLeaseLiabilityNoncurrent','CapitalLeaseObligationsCurrent','CapitalLeaseObligationsNoncurrent'}
        dedicated=[r for r in rows if r['source']['qname'].split(':')[-1] in names]
        combined=[r for r in rows if r['includes_finance_leases'] and r not in dedicated]
        if dedicated:
            if combined:raise ValueError('combined and separate lease rows have unresolved overlapping coverage')
            if lease_current is None or lease_noncurrent is None:raise ValueError('separate lease rows require both reported maturity scopes')
            expected={lease_current['qname']:lease_current,lease_noncurrent['qname']:lease_noncurrent}
            if len(dedicated)!=2 or {r['source']['qname'] for r in dedicated}!=set(expected):
                raise ValueError('separate lease rows do not exhaust both maturity scopes')
            for r in dedicated:
                selected=expected[r['source']['qname']]
                if r['source']['context_id']!=selected['context_id'] or not reconciles(r['value'],selected['value'],r['source'],selected):
                    raise ValueError('separate lease row differs from selected maturity source')
            total=lease_current['value']+lease_noncurrent['value']
            if lease_total is not None and not reconciles(total,lease_total['value'],lease_current,lease_noncurrent,lease_total):
                raise ValueError('separate lease rows conflict with reported lease aggregate')
            separate_proof={'current':lease_current,'noncurrent':lease_noncurrent,'already_counted_finance_leases':total,
                'additional_deduction':0.,'basis':'Disjoint current/noncurrent finance-lease rows already included once in statement debt.'}
        elif any(r['includes_finance_leases'] for r in rows) and not includes_lease:
            raise ValueError('partially embedded finance leases require disjoint claim coverage')
    staged_proof=None
    if version==STAGED_VERSION:
        staged_proof=claim_envelope(packet,disclosure,liab,lease_current,lease_noncurrent,lease_total)
        staged_proof['authorization']=scope['authorization']
        lease_extra=staged_proof['additional_minimum']
    elif separate_proof is not None or includes_lease:lease_extra=0.
    elif lease_total is not None:lease_extra=lease_total['value']
    elif lease_current is not None and lease_noncurrent is not None:lease_extra=lease_current['value']+lease_noncurrent['value']
    elif disclosure['all_leases_operating']:
        if any(r is not None and r['value']>0 for r in (lease_total,lease_current,lease_noncurrent)):raise ValueError('operating-only disclosure conflicts with finance-lease balances')
        lease_extra=0.
    else:raise ValueError('finance-lease scope is incomplete; absence is not an explicit zero')
    if lease_extra<0:raise ValueError('negative finance-lease claim')
    debt=ordinary+lease_extra
    shares=fact(packet,['WeightedAverageNumberOfDilutedSharesOutstanding'],flow=True)
    if shares['value']<=0:raise ValueError('share denominator invalid')
    point=lambda v:BridgeRange(v,v,v)
    unresolved=('finance_lease_current','finance_lease_noncurrent') if staged_proof else ()
    resolution=BridgeResolution(complete=not unresolved,can_value=True,missing_fields=unresolved,blocking_fields=(),bounded_fields=unresolved,
        cash_and_investments=point(cash['value']),total_debt=point(debt),preferred_equity=point(preferred),
        noncontrolling_interests=point(minority),bridge_adjustment=point(cash['value']-debt-preferred-minority),
        fully_diluted_shares=shares['value'],reason_codes=('SHARED_RECORDED_STATEMENT_SCOPE','CASH_ONLY_INVESTMENTS_EXCLUDED','BOOK_OWNERSHIP_CLAIM_PROXY'),policy_version=version)
    result={'balance_sheet':{'period_end':packet['controlling_filing']['reportDate'],'fully_diluted_shares_proxy':shares['value']},
        'resolution':resolution.as_dict(),'warnings':[],'shared_statement_bridge':{'version':version,'sources':sources,
        'statement':disclosure,'ordinary_debt':ordinary,'additional_finance_lease':lease_extra,
        'excluded_investments':'not modeled; not asserted zero','ownership_basis':'reported book claims, not independent fair values'},
        'approved_cash_only_scope':None,'approved_share_basis':None,'capital_structure_projection':None,
        'reported_claim_scope':None,'structural_recovery':{'scope':version}}
    if version==SEPARATE_ROWS_VERSION:result['shared_statement_bridge']['separate_lease_row_reconciliation']=separate_proof
    if staged_proof:result['shared_statement_bridge']['staged_lease_fallback']=staged_proof
    return result
