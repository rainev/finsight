"""Versioned common-owner cash DCF for private economic review.

This module does not replace approved catalogs. It consumes verified statement
observations and explicit policy assumptions; it cannot read vendor prices.
"""
from copy import deepcopy
from math import isfinite
from statistics import median

from .calculation_recipe import SCHEMA,evaluate_recipe

VERSION='US-COMMON-CASH-DCF-REVIEW-2'

class CashReviewGap(ValueError):pass

def need(ok,message):
    if not ok:raise CashReviewGap(message)

def finite(value,name):
    need(isinstance(value,(int,float)) and not isinstance(value,bool) and isfinite(value),name+' must be finite')
    return float(value)

def prepare(facts,policy):
    """Build an after-interest common-cash forecast with an explicit cash budget.

    Reported cash interest and operating rent stay inside CFO. Future debt
    rollover is an assumption; no borrowing proceeds, cash balances or debt
    bridge is added to this equity cash flow. SBC is expensed once, with the
    reported physical denominator held fixed. No buyback benefit is invented.
    """
    need(facts['source_verified'] is True,'source rows must be verified first')
    need(facts['common_owner_accounting_bound_verified'] is True,'common cash ownership needs a reconciled accounting bound')
    need(facts.get('existing_hold') is None,'existing source/transaction hold: '+str(facts.get('existing_hold')))
    need(facts['cutoff']=='2026-10-08','review cutoff mismatch')
    for forbidden in ['alpha_value','competitor_value','market_price','price_target','target_value']:
        need(forbidden not in facts and forbidden not in policy,'vendor/market target is not a valuation input')
    shares=finite(facts['common_shares'],'common shares')
    ni=finite(facts['common_income_ttm'],'common income')
    revenue=finite(facts['revenue_ttm'],'revenue')
    cfo=finite(facts['cfo_ttm'],'CFO');capex=finite(facts['capex_ttm'],'capex');sbc=finite(facts['sbc_ttm'],'SBC')
    need(shares>0 and ni>0 and revenue>0 and cfo>0 and capex>=0 and sbc>=0,'positive owner/cash basis and nonnegative economic costs required')
    history=facts['history']
    need(len(history)>=3,'three recent aligned annual cash/income observations required')
    ratios=[];cash_margins=[];revenue_history=[];income_history=[]
    for row in history:
        need(row['role_verified'] and row['period_aligned'],'historical statement role or fiscal period unresolved')
        income=finite(row['common_income'],'annual income')
        cash=finite(row['cfo'],'annual CFO')-finite(row['capex'],'annual capex')-finite(row['sbc'],'annual SBC')
        # A cash trough is a real observation, not a row to discard. Retain
        # signed conversion; only a nonpositive median fails the cash lane.
        rev=finite(row['revenue'],'annual revenue');need(rev>0,'annual revenue must be positive')
        ratios.append(cash/income if income>0 else None)
        cash_margins.append(cash/rev);revenue_history.append(rev);income_history.append(income)
    raw_cash=cfo-capex-sbc
    need(raw_cash>0,'cash after reinvestment and SBC is nonpositive')
    # Normalize conversion, not historical ROE times today's changed book.
    mode=policy.get('cash_anchor_mode','signed_historical_conversion')
    if mode=='reported_TTM_cash':
        # In particular, intangible amortization and tax items can depress
        # GAAP NI without consuming cash. Do not introduce a second one-sided
        # NI cap after removing the book/ROE cap. Retain source history as
        # volatility evidence and stress the observed cash forecast explicitly.
        conversion=None;normalized_cash=raw_cash
        normalization_basis='reported fiscal-TTM cash after full productive/SBC costs; no assumed NI cap or unsourced addback'
    elif all(r is not None for r in ratios):
        conversion=median(ratios)
        need(conversion>0,'median common cash conversion is nonpositive')
        normalized_cash=min(raw_cash,ni*conversion)
        normalization_basis='signed recent cash/common-income conversion; no period discarded'
    else:
        conversion=median(cash_margins)
        need(conversion>0,'median cash/revenue margin is nonpositive')
        normalized_cash=min(raw_cash,revenue*conversion)
        normalization_basis='signed cash/revenue margins for ALL recent periods; nonpositive historical NI does not erase positive source cash'
    normalized_cfo=normalized_cash+capex+sbc
    observed_growth=(revenue_history[-1]/revenue_history[0])**(1/(len(revenue_history)-1))-1
    need(observed_growth>-.15,'severe historical contraction requires an issuer forecast')
    policy=deepcopy(policy)
    rf=finite(policy['risk_free_rate'],'risk-free rate');erp=finite(policy['equity_risk_premium'],'ERP');beta=finite(policy['sector_beta_prior'],'beta')
    need(rf>0 and erp>0 and beta>0,'risk benchmark inputs must be positive')
    premium=finite(policy['uncertainty_premium'],'uncertainty premium')
    need(premium>=0,'uncertainty premium must be nonnegative')
    ke=rf+beta*erp+premium
    need(policy['rate_kind']=='cost_of_equity','after-interest cash cannot use WACC')
    need(policy['debt_net_borrowing_assumption']==0,'this lane gives no incremental borrowing-funded cash')
    need(policy['cash_debt_bridge']==0,'equity cash must not receive a duplicate cash/debt bridge')
    years=policy['forecast_years'];need(isinstance(years,int) and 5<=years<=15,'unsupported forecast horizon')
    reserve=finite(policy['future_acquisition_cash_budget_fraction'],'acquisition cash budget')
    need(0<=reserve<=.50,'invalid acquisition cash budget')
    principal=finite(facts['annual_finance_lease_principal_budget'],'finance lease principal budget')
    need(principal>=0,'negative finance-lease principal budget')
    need(facts['finance_lease_budget_reviewed'] is True,'finance lease principal cash coverage unresolved')
    scenarios={};budgets={}
    base_growth=max(-.03,min(policy['initial_growth_cap'],observed_growth))
    # Source CFO/capex/SBC intensities are scaled together with future revenue.
    # Existing growth expenditure is retained, never called maintenance capex.
    # Additional growth above the observed source rate gets an extra funding cost.
    for name,g_delta,r_delta,haircut,capex_stress,reserve_stress,terminal in [
        ('bear',-.03,.02,.80,1.20,.05,0.),
        ('base',0.,0.,1.,1.,0.,.02),
        ('bull',.02,-.0075,1.,1.,0.,.025),
    ]:
        initial=max(-.05,min(policy['initial_growth_cap']+.02,base_growth+g_delta))
        discount=ke+r_delta
        need(discount-terminal>=.03,'rate-growth spread too small')
        sales=revenue;cash_flows=[];schedule=[]
        for year in range(1,years+2):
            weight=max(0.,(years-year)/(years-1))
            growth=terminal+(initial-terminal)*weight
            sales*=1+growth
            scale=sales/revenue
            # Stress cash generation after the existing productive/SBC budget,
            # then separately stress productive-asset cash. This avoids treating
            # an FCF haircut as the same percentage haircut to gross CFO.
            operating=(capex+sbc+normalized_cash*haircut)*scale
            investment=capex*scale*capex_stress
            compensation=sbc*scale
            acquisition=max(0.,operating-investment-compensation)*(reserve+reserve_stress)
            funding=sales*max(0.,growth-max(0.,observed_growth))*policy['incremental_growth_cash_intensity']
            cash=operating-investment-compensation-acquisition-principal*scale-funding
            need(cash>0,name+' cash budget is nonpositive; no automatic floor')
            schedule.append({'year':year,'revenue':sales,'growth':growth,'operating_cash':operating,
                'productive_asset_cash':investment,'SBC_economic_cost':compensation,
                'future_acquisition_cash_budget':acquisition,'finance_lease_principal':principal*scale,
                'additional_growth_funding':funding,'common_cash':cash})
            if year<=years:cash_flows.append(cash)
        scenarios[name]={'engine':'cash_schedule','inputs':{'cash_flows':cash_flows,
            'terminal_cash_flow':schedule[-1]['common_cash'],'terminal_growth':terminal,
            'discount_rate':discount,'shares':shares,'net_bridge':0.}}
        budgets[name]=schedule
    recipe={'schema_version':SCHEMA,'recipe_version':VERSION,'ticker':facts['ticker'],
        'valuation_date':facts['cutoff'],'evidence_cutoff':facts['cutoff'],'private_only':True,
        'reliability':'Low','scenarios':scenarios,'editable':{
            'discount_rate':{'field':'discount_rate','label':'Cost of equity','operation':'delta',
                'min':.06,'max':.25,'step':.0025}},'warnings':[
            'Private common-cash DCF using reported after-interest CFO and full reported capex/SBC costs.',
            'Broad sector beta and uncertainty premiums are analyst assumptions, not measured issuer beta or WACC.',
            'Future financing assumes stable debt rollover with zero net borrowing; no cash/debt bridge or buyback benefit.',
            ('Reported TTM cash is the forecast anchor; historical income/cash ratios are not used as a one-sided cap.' if mode=='reported_TTM_cash'
                else 'Cash conversion is normalized against recent reported common income, not historical ROE multiplied by changed book.'),
            'Working-capital cycles, acquisitions, taxes and unreported claims can invalidate these Low forecasts.',
            'Future acquisition/reinvestment cash budgets are explicit assumptions; missing historical tags are not filled with zero.',
            'Source accounting claims are bounded to dated statements, not a claim of universal legal absence.',
        ]}
    evaluated=evaluate_recipe(recipe)
    diagnostics={'version':VERSION,'reported_core_cash':raw_cash,'historical_cash_to_common_income_ratios':ratios,
        'median_conversion':conversion,'normalization_basis':normalization_basis,'historical_cash_margins':cash_margins,
        'normalized_common_cash_before_future_budgets':normalized_cash,
        'normalized_CFO':normalized_cfo,'reported_revenue_growth':observed_growth,
        'base_initial_growth_assumption':base_growth,'cost_of_equity':ke,'policy':policy,
        'forecast_budgets':budgets,'ranges':evaluated['range'],'vendor_targets_used':False,
        'economic_calibration':'analyst_review_required','existing_cash_interest_and_operating_rent_subtracted_again':False}
    return recipe,diagnostics
