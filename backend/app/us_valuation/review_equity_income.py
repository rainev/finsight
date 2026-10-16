"""Private capital-intensive common-equity review, with explicit forecast choices.

This is an earnings/book alternative when equity cash allocation is unresolved;
it never pretends to reconcile CFO, leases or minority cash distributions.
"""
from copy import deepcopy
from math import isfinite
from statistics import median
from .calculation_recipe import SCHEMA,evaluate_recipe

VERSION='US-COMMON-EQUITY-INCOME-REVIEW-2'
CAPITAL_CASES=frozenset('AGCO ALSN AWI FSS GBX GATX TRN RUSHA DXPE ITRI ITT ASTE AZZ CTS OSIS ACLS VECO MLR HAYW FORM MTSI POWI LMAT SAIA'.split())

def prepare(ledger,policy):
    ticker=ledger['ticker']
    if ticker not in CAPITAL_CASES:raise ValueError('cash/ownership review required; no book-model fallback for this business')
    book=ledger['current_common_capital']['reported_parent_common_book']['value']
    ni=ledger['current_income_ttm']['value'];shares=ledger['balance_point_common_shares']['value']
    source=ledger['current_common_capital']['reported_parent_common_book']
    if source.get('unit') is None and source.get('operands'):
        operands=source['operands']
        if not all(r.get('unit')=='USD' for r in operands):raise ValueError('common book component currency mismatch')
        ends={r['period_end'] for r in operands};accessions={r['source_accession'] for r in operands}
        if len(ends)!=1 or len(accessions)!=1:raise ValueError('common book component period/source mismatch')
        source={**source,'unit':'USD','period_end':ends.pop(),'source_accession':accessions.pop()}
    income=ledger['current_income_ttm']
    if income.get('mode')=='reported_annual':
        operand=income['operands'][0]
        income={**operand,**income}
    units=[r.get('unit',r.get('currency')) for r in income.get('operands',[])]
    income_unit=income.get('unit') or income.get('currency')
    if income_unit is None and units and all(u=='USD' for u in units):income_unit='USD'
    if source.get('unit')!='USD' or income_unit!='USD':raise ValueError('common source currency mismatch')
    if not income.get('period_end') and len(income.get('operands',[]))==3:
        annual,current_operand,prior_operand=income['operands']
        if current_operand['source_accession']!=prior_operand['source_accession']:raise ValueError('same-filing comparison required')
        if abs(annual['value']+current_operand['value']-prior_operand['value']-ni)>max(.01,abs(ni)*1e-10):raise ValueError('TTM source arithmetic mismatch')
        income={**income,'period_end':current_operand['period_end']}
    if source['period_end']!=income['period_end'] or not 330<=income['duration_days']<=385:raise ValueError('common fiscal-TTM/book period mismatch')
    if source['period_end']>ledger['cutoff']:raise ValueError('common source period after cutoff')
    if ledger.get('no_market_price_or_target_fitting') is not True:raise ValueError('source ledger must prohibit target fitting')
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v) and v>0 for v in [book,ni,shares]):raise ValueError('positive common-owner source basis required')
    observed=ledger['annual_reported_ROE'];historical=median(observed)
    if historical<=0:raise ValueError('positive historical return evidence missing')
    current=ni/book
    # Terminal persistence is an explicit scenario assumption using the
    # reported historical return range, capped at twice current return. This
    # permits a bounded cycle recovery but no unconstrained industry turnaround.
    terminal_base=min(historical,current*2.)
    payout=ledger['assumptions']['future_payout_ratio']
    ke=policy['risk_free_rate']+policy['sector_beta_prior']*policy['equity_risk_premium']+policy['uncertainty_premium']
    years=8;specs={};policies={}
    for name,first_multiplier,terminal_multiplier,rate_delta,g in [
        ('bear',.75,.75,.02,0.),('base',1.,1.,0.,.01),('bull',1.2,1.2,-.0075,.02)]:
        first=current*first_multiplier;terminal=min(terminal_base*terminal_multiplier,current*2.)
        growth=min(g,terminal*.20);rate=ke+rate_delta
        if rate-growth<.03:raise ValueError('rate-growth spread below3%')
        # Existing RI engine fades in year one. Algebraically map its input
        # so the first projected common income is the explicitly chosen
        # reported-TTM scenario amount, not a hidden preforecast haircut.
        initial=(first-terminal/years)/(1-1/years)
        if initial<=0:raise ValueError('terminal return unsupported by starting earnings')
        specs[name]={'engine':'residual_income','inputs':{'book_value_per_share':book/shares,'current_roe':initial,
            'cost_of_equity':rate,'current_payout_ratio':payout,'terminal_roe':terminal,'terminal_growth':growth,'years':years}}
        policies[name]={'first_forecast_common_income':ni*first_multiplier,'terminal_ROE_assumption':terminal,
            'source_historical_median_ROE':historical,'current_TTM_common_income_to_current_book':current,
            'no_historical_ROE_cap_on_initial_income':True,'synthetic_engine_initial_ROE':initial}
    recipe={'schema_version':SCHEMA,'recipe_version':VERSION,'ticker':ticker,'valuation_date':ledger['cutoff'],
        'evidence_cutoff':ledger['cutoff'],'private_only':True,'reliability':'Low','scenarios':specs,
        'editable':{'discount_rate':{'field':'cost_of_equity','label':'Cost of equity','operation':'delta','min':.06,'max':.25,'step':.0025}},
        'warnings':[
            'Private common-equity earnings/book scenario, not a reconciled common-cash DCF.',
            'First-year earnings start from reported fiscal TTM; historical ROE is not multiplied into changed book to normalize income.',
            'Terminal return uses observed historical median with a2x current-return cap; cycle recovery and persistence are assumptions.',
            'Potential payout and future clean surplus remain assumptions; actual buyback/SBC/OCI/financing cash budgets are not reconciled.',
            'Sector-beta/risk-premium discount inputs are broad priors and explicit uncertainty assumptions, not issuer calibration.',
            'Common-owner income/book already reflect reported liabilities and minority attribution; no duplicate enterprise debt bridge.',
            'Cash-model rejection and existing filing/event/public holds remain disclosed; this is not a public eligibility upgrade.',
        ]}
    evaluated=evaluate_recipe(recipe)
    for name,m in policies.items():
        first=evaluated['scenarios'][name]['trace']['detail']['schedule'][0]['earnings_per_share']*shares
        if abs(first-m['first_forecast_common_income'])>max(1.,abs(first)*1e-10):raise ValueError('first-year common income mapping mismatch')
    return recipe,{'version':VERSION,'policy':deepcopy(policy),'source_current_common_income':ni,'source_book':book,
        'scenarios':policies,'ranges':evaluated['range'],'cash_budget_reconciled':False,'economic_calibration':'analyst_review_required'}
