"""Private, source-bound common-owner initial underwriting; not a refresh grant.

Uses captured fiscal periods and the existing RI kernel. Every forecast policy
is an assumption, not a reported fact, public eligibility or economic calibration.
"""
from copy import deepcopy
from datetime import date
from math import isclose,isfinite
from statistics import median
import re
from lxml import html
from .refresh_expansion_common import _packet_facts
from .expansion_period_inputs import _derived_ttm
from .calculation_recipe import SCHEMA,evaluate_recipe,evaluate_scenario

VERSION='US-EXPANSION-B02-PRIVATE-COMMON-1'
NI=('NetIncomeLossAvailableToCommonStockholdersBasic','NetIncomeLoss')
DIV=('PaymentsOfDividendsCommonStock','DividendsCommonStockCash','PaymentsOfDividends')
CYCLICAL={'TNC','LNN','TKR','KMT','ROG'}

class InitialInputGap(ValueError):pass
def need(value,why):
    if not value:raise InitialInputGap(why)
def days(start,end):return (date.fromisoformat(end)-date.fromisoformat(start)).days+1
def num(row):
    value=row.get('value',row.get('val'))
    need(isinstance(value,(int,float)) and not isinstance(value,bool) and isfinite(value),'reported fact must be a finite numeric value')
    return float(value)
def unit(row):return str(row.get('unit','')).removeprefix('xbrli:')
def unique(rows,name):
    need(rows,'missing exact reported '+name)
    vals={num(r) for r in rows};need(all(isfinite(x) for x in vals),'nonfinite '+name)
    def radius(r):
        try:return .5*10**-int(r.get('decimals','INF'))
        except (ValueError,TypeError):return 0.
    need(max(num(r)-radius(r) for r in rows)<=min(num(r)+radius(r) for r in rows),'conflicting exact '+name)
    return deepcopy(min(rows,key=radius))
def source(row,receipts,name):
    acc=row.get('source_accession') or row.get('accn');need(acc in receipts,'fact has no captured primary document: '+name)
    r=receipts[acc];start=row.get('period_start') or row.get('start');end=row.get('period_end') or row.get('end')
    return {'field':name,'qname':row.get('qname'),'value':num(row),'unit':unit(row),'period_start':start,
        'period_end':end,'duration_days':days(start,end) if start else None,
        'source_accession':acc,'form':row.get('form') or r['filing']['form'],
        'filed_date':row.get('filed_date') or row.get('filed') or r['filing']['filingDate'],
        'dimensions':row.get('dimensions') or [],'context_id':row.get('context_id'),
        'source_kind':row.get('_source_kind'),'document_sha256':r['sha256'],'source_url':r['source_url']}
def select_rows(rows,names,*,end,start=None,flow=False,acc=None,annual=False,structural=False,dims=None):
    for name in names:
        q='us-gaap:'+name if ':' not in name else name
        hits=[r for r in rows if r.get('qname')==q and (r.get('period_end') or r.get('end'))==end
              and bool(r.get('period_start') or r.get('start'))==flow
              and (start is None or (r.get('period_start') or r.get('start'))==start)
              and (acc is None or (r.get('source_accession') or r.get('accn'))==acc)
              and (not annual or r.get('form') in {'10-K','10-K/A'})
              and (not structural or r.get('_source_kind')=='structural_xbrl')
              and (dims is None or (r.get('dimensions') or [])==dims)]
        if hits:return hits
    return []
def flow(rows,names,end,receipts,field,*,acc=None,annual=False,start=None):
    candidates=select_rows(rows,names,end=end,start=start,flow=True,acc=acc,annual=annual,dims=[])
    candidates=[r for r in candidates if unit(r)=='USD' and (not annual or 330<=days(r.get('period_start') or r.get('start'),end)<=385)]
    need(candidates,'missing fiscal '+field+' at '+end)
    if start is None:
        first=min(r.get('period_start') or r.get('start') for r in candidates)
        candidates=[r for r in candidates if (r.get('period_start') or r.get('start'))==first]
    # Prefer the actual structural income/cash statement at this accession.
    structural=[r for r in candidates if r.get('_source_kind')=='structural_xbrl']
    if structural:candidates=structural
    else:
        latest=max(r.get('filed_date') or r.get('filed') for r in candidates)
        candidates=[r for r in candidates if (r.get('filed_date') or r.get('filed'))==latest]
    return source(unique(candidates,field),receipts,field)
def owner_income(rows,end,receipts,*,acc=None,annual=False,start=None):
    result=flow(rows,NI,end,receipts,'parent_common_income',acc=acc,annual=annual,start=start)
    stopped=select_rows(rows,('IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToReportingEntity',
        'IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToParent'),end=end,start=result['period_start'],flow=True,acc=result['source_accession'],dims=[])
    if stopped:
        s=source(unique([r for r in stopped if unit(r)=='USD'],'discontinued income'),receipts,'discontinued_parent_income')
        if s['value']!=0:
            result={**result,'value':result['value']-s['value'],'qname':'derived:continuing_parent_common_income',
                    'classification':'derived_from_aligned_reported_income','operands':[result,s]}
    return result
def fiscal_ttm(rows,names,annual,filing,receipts,field,owner=False):
    choose=owner_income if owner else lambda r,e,c,**kw:flow(r,names,e,c,field,**kw)
    if filing['form'].startswith('10-K'):return {'mode':'reported_annual','value':annual[-1]['value'],'operands':[annual[-1]]}
    acc=filing.get('accessionNumber') or filing.get('accession');end=filing['reportDate']
    current=choose(rows,end,receipts,acc=acc)
    prior_candidates=[r for r in rows if (r.get('source_accession') or r.get('accn'))==acc and r.get('qname') in {'us-gaap:'+n for n in names}
                      and (r.get('period_start') or r.get('start'))==annual[-1]['period_start']
                      and (r.get('period_end') or r.get('end','9999'))<annual[-1]['period_end']
                      and (r.get('period_start') or r.get('start')) and abs(days(r.get('period_start') or r.get('start'),r.get('period_end') or r.get('end'))-current['duration_days'])<=1]
    need(prior_candidates,'same-accession comparable fiscal YTD missing: '+field)
    prior_end=max(r.get('period_end') or r.get('end') for r in prior_candidates)
    prior=choose(rows,prior_end,receipts,acc=acc,start=annual[-1]['period_start'])
    derived=_derived_ttm(annual,current,prior)
    need(derived is not None and 330<=derived['duration_days']<=385,'fiscal TTM alignment unsupported: '+field)
    return {'mode':'FY_plus_current_fiscal_YTD_minus_same_accession_prior_YTD',**derived}
def point(rows,names,end,receipts,field,*,acc=None,structural=False,dims=None,units='USD'):
    hits=select_rows(rows,names,end=end,acc=acc,structural=structural,dims=dims or [])
    hits=[r for r in hits if unit(r)==units]
    structural_rows=[r for r in hits if r.get('_source_kind')=='structural_xbrl']
    if structural_rows:hits=structural_rows
    elif hits:
        newest=max(r.get('filed_date') or r.get('filed') for r in hits)
        hits=[r for r in hits if (r.get('filed_date') or r.get('filed'))==newest]
    return source(unique(hits,field),receipts,field)
def common_capital(rows,end,receipts,acc):
    parent=point(rows,('StockholdersEquity',),end,receipts,'parent_book',acc=acc,structural=True)
    current=[r for r in rows if r.get('_source_kind')=='structural_xbrl' and (r.get('source_accession') or r.get('accn'))==acc and r.get('period_end')==end and not r.get('period_start')]
    outstanding=select_rows(current,('PreferredStockSharesOutstanding',),end=end)
    issued=select_rows(current,('PreferredStockSharesIssued',),end=end)
    pref=[];preferred_outstanding=0.
    if outstanding:
        amounts={num(r) for r in outstanding};need(len(amounts)==1,'conflicting preferred outstanding shares')
        preferred_outstanding=amounts.pop();pref=[source(unique(outstanding,'preferred outstanding'),receipts,'preferred outstanding')]
    elif issued:
        dims_groups={str(r.get('dimensions') or []):[] for r in issued}
        for r in issued:dims_groups[str(r.get('dimensions') or [])].append(r)
        issued_value=sum(num(unique(v,'preferred issued class')) for v in dims_groups.values())
        treasury=select_rows(current,('TreasuryStockPreferredShares',),end=end)
        if issued_value>0:
            need(treasury,'issued preferred has no outstanding/treasury reconciliation')
            treasury_value=num(unique(treasury,'preferred treasury shares'))
            need(issued_value==treasury_value,'outstanding preferred claim requires its own model')
            pref=[source(unique(issued,'preferred issued'),receipts,'preferred issued'),source(unique(treasury,'preferred treasury'),receipts,'preferred treasury')]
    need(preferred_outstanding==0,'outstanding preferred capital is not common')
    def component(names,label):
        hit=select_rows(current,names,end=end,dims=[])
        hit=[r for r in hit if unit(r)=='USD']
        return source(unique(hit,label),receipts,label) if hit else None
    par=component(('CommonStockValue','CommonStockValueOutstanding','CommonStockNoParValue'),'common_par')
    if par is None:
        class_rows=select_rows(current,('CommonStockValue',),end=end)
        groups={}
        for r in class_rows:
            d=r.get('dimensions') or []
            if len(d)==1 and 'ClassOfStock' in d[0][0]:groups.setdefault(str(d),[]).append(r)
        need(groups,'common par/class composition missing')
        operands=[source(unique(v,'common class par'),receipts,'common class par') for v in groups.values()]
        par={'value':sum(r['value'] for r in operands),'classification':'sum_disjoint_reported_common_classes','operands':operands}
    components=[par]
    for names,label in [(('AdditionalPaidInCapitalCommonStock','AdditionalPaidInCapital'),'common_apic'),(('RetainedEarningsAccumulatedDeficit',),'retained_earnings'),(('AccumulatedOtherComprehensiveIncomeLossNetOfTax',),'AOCI')]:
        r=component(names,label)
        if r:components.append(r)
        elif label!='AOCI':raise InitialInputGap('common-capital component missing: '+label)
    treasury=component(('TreasuryStockValue','TreasuryStockCommonValue'),'treasury_common_book')
    pref_par=component(('PreferredStockValue',),'issued_preferred_par')
    pref_treasury=select_rows(current,('TreasuryStockPreferredValue',),end=end)
    total=sum(r['value'] for r in components)-(treasury['value'] if treasury else 0.)
    if pref_par and pref_par['value']!=0:
        need(pref,'preferred accounting amount lacks a zero-outstanding reconciliation')
        pt=source(unique(pref_treasury,'preferred treasury carrying amount'),receipts,'preferred treasury carrying amount')
        total+=pref_par['value']-pt['value'];components += [pref_par,{'value':-pt['value'],'operands':[pt]}]
    need(isclose(total,parent['value'],rel_tol=0,abs_tol=.01),'common-capital components do not exhaust reported parent book')
    need(parent['value']>0,'nonpositive common book')
    return {'reported_parent_common_book':parent,'reported_components':components,'treasury_common':treasury,
        'preferred_issued_treasury_or_outstanding_proof':pref,'derived_unallocated_equity_residual':parent['value']-total,
        'scope':'reported common capital at accounting precision; not a claim of no unrecorded legal obligations'}
def primary_text(receipt):
    doc=html.fromstring(receipt['raw_bytes'])
    for n in doc.xpath('//*[local-name()="hidden"]|//script|//style'):
        if n.getparent() is not None:n.getparent().remove(n)
    return re.sub(r'\s+',' ',doc.text_content())
def current_shares(rows,end,receipts,acc,primary,capital):
    current=[r for r in rows if r.get('_source_kind')=='structural_xbrl' and r.get('source_accession')==acc and r.get('period_end')==end and not r.get('period_start') and unit(r)=='shares']
    direct=select_rows(current,('CommonStockSharesOutstanding',),end=end,dims=[])
    if direct:
        value=num(unique(direct,'balance point common shares'))
        need(value>0,'nonpositive common share denominator')
        return {'value':value,'mode':'reported_balance_point','operands':[source(unique(direct,'balance point common shares'),receipts,'common shares')]}
    issued=select_rows(current,('CommonStockSharesIssued',),end=end)
    need(issued,'reported common share count missing')
    classes={}
    for r in issued:classes.setdefault(str(r.get('dimensions') or []),[]).append(r)
    values=[source(unique(v,'issued common class shares'),receipts,'issued common class shares') for v in classes.values()]
    if len(values)>1:
        need(all(v['dimensions'] and len(v['dimensions'])==1 and 'ClassOfStock' in v['dimensions'][0][0] for v in values),'share classes overlap')
        need('share equally, on a share-for-share basis' in primary and 'one share of Common Stock' in primary,'economic common class rights not reconciled')
    treasury=select_rows(current,('TreasuryStockCommonShares','TreasuryStockShares'),end=end)
    if not treasury:
        treasury=[r for r in current if (r.get('local_name') or '')=='TreasuryStockShare']
    if treasury:
        p=source(unique(treasury,'treasury common shares'),receipts,'treasury common shares');value=sum(v['value'] for v in values)-p['value'];values.append(p)
        mode='reported_issued_minus_reported_treasury'
    else:
        need(len(values)==1 and re.search(r'issued and outstanding',primary,re.I),'issued shares are not proven outstanding')
        value=values[0]['value'];mode='issued_and_outstanding_primary_statement_proof'
    need(value>0,'nonpositive common share denominator')
    return {'value':value,'mode':mode,'operands':values,'no_assumed_buyback_or_dilution_benefit':True}

def prepare(packet,coverage,policy):
    """Build source/assumption records only; calculate() is a separate stage."""
    filing=packet['controlling_filing'];acc=filing.get('accessionNumber') or filing.get('accession');end=filing['reportDate'];cutoff=packet['cutoff'];ticker=packet['issuer']['ticker']
    need(end<=cutoff and filing.get('filingDate',filing.get('filed','9999'))<=cutoff,'controlling filing/financial period after cutoff')
    need(str(packet['companyfacts']['cik']).zfill(10)==packet['issuer']['cik']==str(packet['submissions']['cik']).zfill(10),'SEC packet issuer identity mismatch')
    receipts={r['filing']['accessionNumber']:r for r in coverage['documents'] if r['status']=='captured'}
    allowed=set(receipts)|{r['accession'] for r in packet.get('structural_receipts',[])}
    rows=[]
    for r in _packet_facts(packet,filing):
        if r.get('source_accession') not in allowed or (r.get('filed_date') or '')>cutoff:continue
        if r.get('_source_kind')=='structural_xbrl':
            if str(r.get('entity_identifier','')).zfill(10)!=packet['issuer']['cik'] or r.get('entity_scheme')!='http://www.sec.gov/CIK':continue
            if r.get('qname','').startswith('us-gaap:') and not re.fullmatch(r'https?://fasb.org/us-gaap/20\d{2}',r.get('namespace','')):continue
        rows.append(r)
    current_receipt=receipts[acc]
    from pathlib import Path
    text=primary_text({'raw_bytes':Path(current_receipt['path']).read_bytes()})
    if policy.get('source_bound_hold'):
        marker=policy['source_bound_hold']['required_primary_phrase']
        need(marker in text,'expected source-bound hold disclosure changed')
        raise InitialInputGap(policy['source_bound_hold']['reason'])
    capital=common_capital(rows,end,receipts,acc);shares=current_shares(rows,end,receipts,acc,text,capital)
    annual_ends=sorted({r['filing']['reportDate'] for r in coverage['documents'] if r['filing']['form']=='10-K'})[-5:]
    need(len(annual_ends)==5,'five annual statement periods required')
    annual_income=[owner_income(rows,e,receipts,annual=True) for e in annual_ends]
    ttm=fiscal_ttm(rows,NI,annual_income,filing,receipts,'income',owner=True)
    need(ttm['value']>0,'nonpositive fiscal-TTM common income; no unsupported turnaround or addback')
    roes=[];books=[]
    for income in annual_income:
        closing=point(rows,('StockholdersEquity',),income['period_end'],receipts,'annual parent book')
        prior_day=(date.fromisoformat(income['period_start']).fromordinal(date.fromisoformat(income['period_start']).toordinal()-1)).isoformat()
        opening=point(rows,('StockholdersEquity',),prior_day,receipts,'opening annual parent book')
        need(opening['value']>0 and closing['value']>0,'nonpositive historical parent book; ROE comparability unresolved')
        roes.append(income['value']/((opening['value']+closing['value'])/2));books.append({'opening':opening,'closing':closing})
    anchor=min(ttm['value']/capital['reported_parent_common_book']['value'],median(roes))
    need(anchor>0,'nonpositive historical/current common-return anchor')
    distributions={'status':'not_reconciled','future_payout_is_assumption':True}
    try:
        annual_div=[flow(rows,DIV,e,receipts,'common cash dividends',annual=True) for e in annual_ends]
        div_ttm=fiscal_ttm(rows,DIV,annual_div,filing,receipts,'common cash dividends')
        distributions={'status':'reported_and_fiscal_TTM','annual':annual_div,'current_TTM':div_ttm,
            'raw_TTM_cash_dividend_to_common_income':div_ttm['value']/ttm['value'],
            'five_year_cash_dividend_to_common_income':sum(r['value'] for r in annual_div)/sum(r['value'] for r in annual_income) if sum(r['value'] for r in annual_income)>0 else None,
            'specials_not_silently_repeated_or_clipped':True}
    except InitialInputGap as exc:
        distributions['source_gap']=str(exc)
    policy=deepcopy(policy)
    observed=distributions.get('five_year_cash_dividend_to_common_income')
    if isinstance(observed,(int,float)) and 0<=observed<=1 and distributions.get('raw_TTM_cash_dividend_to_common_income',2)<=1 and not policy.get('special_distribution_normalization_required'):
        policy['future_payout_ratio']=observed
        policy['future_payout_basis']='future assumption using observed five-year aggregate common dividends/common income; not asserted recurring or guaranteed'
    else:
        policy['future_payout_basis']='separately labeled sustainable future payout assumption; actual special distributions/ratios retained, no clipping or automatic repetition'
    payout=policy['future_payout_ratio']
    need(0<=payout<=1,'forecast payout is outside economic funding limits')
    specs={}
    for i,name in enumerate(['bear','base','bull']):
        terminal=anchor*policy['terminal_ROE_fractions'][i]
        growth=min(policy['terminal_growth_caps'][i],terminal*policy['terminal_retention_fractions'][i])
        need(terminal>growth>=0 and policy['cost_of_equity'][i]-growth>=.03,'terminal growth is not source-capital-funded')
        specs[name]={'engine':'residual_income','inputs':{'book_value_per_share':capital['reported_parent_common_book']['value']/shares['value'],
            'current_roe':anchor*policy['initial_ROE_multipliers'][i],'cost_of_equity':policy['cost_of_equity'][i],
            'current_payout_ratio':payout,'terminal_roe':terminal,'terminal_growth':growth,'years':policy['years']}}
    warnings=policy['warnings']+[
        'GAAP reported common-owner RI, not enterprise cash FCFF; cash/debt/leases/NCI are not credited or deducted again.',
        'Historical book includes OCI, SBC and treasury/capital movements; future clean surplus and reinvestment/financing are forecast assumptions, not an exact cash budget.',
        'Balance-date common shares can be rounded and are not fully diluted; no assumed future buyback benefit.',
        'Five annual consolidated observations are not organic/pro-forma forecasts; no unsourced acquisition synergies or turnaround gains.',
        'Discount rates, ROE fade, funded terminal growth and sustainable payout are private scenario assumptions; market/economic calibration unvalidated.',
        'The same-schedule DDM reconciliation is algebraic, not independent economic evidence.']
    recipe={'schema_version':SCHEMA,'recipe_version':VERSION,'ticker':ticker,'valuation_date':cutoff,'evidence_cutoff':cutoff,
            'private_only':True,'reliability':'Low','warnings':warnings,'scenarios':specs,'editable':{}}
    ledger={'classification':'reported_source_facts_and_separate_forecasting_assumptions','ticker':ticker,'cutoff':cutoff,
            'current_common_capital':capital,'balance_point_common_shares':shares,'annual_common_income':annual_income,
            'annual_reported_parent_book':books,'annual_reported_ROE':roes,'current_income_ttm':ttm,'normalized_ROE':anchor,
            'reported_common_distributions':distributions,
            'assumptions':deepcopy(policy),'scenario_arguments':specs,'no_market_price_or_target_fitting':True}
    return recipe,ledger

def calculate(recipe):
    """Preserve raw failed traces; never add a floor to make a range pass."""
    raw={n:evaluate_scenario(recipe['scenarios'][n]) for n in ('bear','base','bull')}
    result=evaluate_recipe(recipe)
    return result,raw
