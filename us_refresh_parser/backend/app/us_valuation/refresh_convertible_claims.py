"""Source-bound mandatory-convertible claim diagnostics for WG10."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from math import isclose,isfinite
import re
from types import MappingProxyType
from typing import Any,Mapping


SCHEMA="FINSIGHT-CONVERTIBLE-CLAIM-1"
VERSION="FINSIGHT-CONVERTIBLE-CLAIM-WG11-1"
_GAAP=re.compile(r"^https?://(?:fasb\.org|xbrl\.us-gaap)/us-gaap/20\d{2}$")

RULES:Mapping[str,Mapping[str,Any]]=MappingProxyType({
    "MCHP":MappingProxyType({
        "schema_version":SCHEMA,"version":VERSION,"ticker":"MCHP","cik":"0000827054",
        "mode":"mandatory_conversion_terms",
        "preferred_shares_qname":"us-gaap:PreferredStockSharesOutstanding",
        "liquidation_total_qname":"us-gaap:PreferredStockLiquidationPreferenceValue",
        "liquidation_per_share_qname":"us-gaap:PreferredStockLiquidationPreference",
        "preferred_zero_qname":"us-gaap:PreferredStockValue",
        "quarter_dividend_qname":"us-gaap:PreferredStockDividendsIncomeStatementImpact",
        "declared_dividend_per_share_qname":"us-gaap:PreferredStockDividendsPerShareDeclared",
        "current_conversion_increment_qname":"us-gaap:IncrementalCommonSharesAttributableToConversionOfPreferredStock",
        "treatment":"deduct source-scheduled future dividend PV and add mandatory-conversion shares once; do not also deduct liquidation preference; exclude capped-call benefit until its realized offset is source-bound",
    }),
})


def convertible_claim_policy(ticker:str, scenario_discount_rates:Mapping[str,Any]|None=None)->dict[str,Any]:
    rule=RULES.get(ticker)
    if rule is None:raise ValueError(f"no convertible claim rule for {ticker!r}")
    policy=deepcopy(dict(rule))
    from .refresh_narrative_evidence import narrative_policy
    policy['narrative_evidence_policy']=narrative_policy(ticker)
    if scenario_discount_rates is not None:
        rates={case:float(scenario_discount_rates[case]) for case in ('bear','base','bull')}
        if any(not isfinite(value) or not 0<value<1 for value in rates.values()):
            raise ValueError('convertible scenario discount rates are invalid')
        policy['scenario_discount_rates']=rates
    return policy


def _same(a,b):return json.dumps(dict(a),sort_keys=True,separators=(",",":"))==json.dumps(dict(b),sort_keys=True,separators=(",",":"))


def _valid(row,*,policy,accession,unit):
    if (row.get("source_accession")!=accession or row.get("unit")!=unit
        or str(row.get("entity_identifier","")).zfill(10)!=policy["cik"]
        or row.get("entity_scheme")!="http://www.sec.gov/CIK"
        or not _GAAP.fullmatch(str(row.get("namespace","")))
        or isinstance(row.get("value"),bool) or not isinstance(row.get("value"),(int,float))
        or not isfinite(float(row["value"]))):raise ValueError("convertible claim source identity, unit or amount invalid")


def _one(facts,*,policy,accession,qname,unit,period=None,duration=False,latest_before=None,undimensioned=True):
    rows=[]
    for row in facts:
        if row.get("qname")!=qname or (undimensioned and row.get("dimensions") not in (None,[])):continue
        if period is not None and row.get("period_end")!=period:continue
        if duration and not isinstance(row.get("period_start"),str):continue
        if not duration and latest_before is None and row.get("period_start") is not None:continue
        if latest_before is not None:
            if row.get("period_start")!=row.get("period_end") or not isinstance(row.get("period_end"),str) or row["period_end"]>latest_before:continue
        _valid(row,policy=policy,accession=accession,unit=unit);rows.append(row)
    if latest_before is not None and rows:
        end=max(row["period_end"] for row in rows);rows=[row for row in rows if row["period_end"]==end]
    if duration and rows:
        start=max(row["period_start"] for row in rows);rows=[row for row in rows if row["period_start"]==start]
    if not rows or len({float(row["value"]) for row in rows})!=1:raise ValueError(f"convertible claim fact missing or conflicting: {qname}")
    return dict(rows[0]),float(rows[0]["value"])


def select_convertible_claim(policy:Mapping[str,Any],structural:Mapping[str,Any],controlling:Mapping[str,Any],cik:str,cutoff:str)->dict[str,Any]:
    expected=RULES.get(policy.get("ticker"))
    static={key:value for key,value in policy.items() if key not in {'narrative_evidence_policy','scenario_discount_rates'}}
    if expected is None or not _same(static,expected) or str(cik).zfill(10)!=expected["cik"]:raise RuntimeError("convertible claim policy identity/version mismatch")
    from .refresh_narrative_evidence import narrative_policy,terms_by_name
    if policy.get('narrative_evidence_policy')!=narrative_policy(str(policy['ticker'])):
        raise RuntimeError('convertible narrative policy identity/version mismatch')
    rates=policy.get('scenario_discount_rates')
    if not isinstance(rates,Mapping) or set(rates)!={'bear','base','bull'} or any(
        isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(float(value)) or not 0<float(value)<1
        for value in rates.values()
    ):raise RuntimeError('convertible scenario discount rates are missing or invalid')
    accession=controlling.get("accessionNumber") or controlling.get("accession");period=controlling.get("reportDate") or controlling.get("period_end")
    filed=controlling.get("filingDate") or structural.get("filed_date")
    if structural.get("source_accession")!=accession or not isinstance(period,str) or not isinstance(filed,str) or not period<=filed<=cutoff:raise ValueError("convertible claim source period/accession/cutoff mismatch")
    date.fromisoformat(period);date.fromisoformat(filed);date.fromisoformat(cutoff)
    facts=structural.get("facts")
    if not isinstance(facts,list):raise ValueError("convertible claim facts missing")
    shares_row,shares=_one(facts,policy=policy,accession=accession,qname=policy["preferred_shares_qname"],unit="xbrli:shares",period=period)
    liquidation_row,liquidation=_one(facts,policy=policy,accession=accession,qname=policy["liquidation_total_qname"],unit="USD",period=period)
    per_share_row,per_share=_one(facts,policy=policy,accession=accession,qname=policy["liquidation_per_share_qname"],unit="USD",period=period)
    preferred_row,preferred=_one(facts,policy=policy,accession=accession,qname=policy["preferred_zero_qname"],unit="USD",period=period)
    dividend_row,dividend=_one(facts,policy=policy,accession=accession,qname=policy["quarter_dividend_qname"],unit="USD",period=period,duration=True)
    declared_row,declared=_one(facts,policy=policy,accession=accession,qname=policy["declared_dividend_per_share_qname"],unit="USD",latest_before=cutoff,undimensioned=False)
    conversion_row,conversion=_one(facts,policy=policy,accession=accession,qname=policy["current_conversion_increment_qname"],unit="xbrli:shares",period=period,duration=True)
    if min(shares,liquidation,per_share,preferred,dividend,declared,conversion)<0:raise ValueError("convertible claim sign requires review")
    if preferred!=0 or conversion!=0:raise ValueError("current preferred carrying/conversion state changed")
    if not isclose(shares*per_share,liquidation,rel_tol=0,abs_tol=.01):raise ValueError("preferred shares and per-share preference do not reconcile")
    receipt=structural.get('narrative_evidence')
    if not isinstance(receipt,Mapping):raise ValueError('mandatory-convertible narrative evidence is missing')
    if (receipt.get('ticker')!=policy['ticker'] or receipt.get('cik')!=policy['cik']
        or receipt.get('policy')!=policy['narrative_evidence_policy']
        or receipt.get('extraction_version')!=policy['narrative_evidence_policy']['version']):
        raise ValueError('mandatory-convertible narrative evidence identity/version mismatch')
    filing=receipt.get('filing') or {}
    if (filing.get('accession'),filing.get('form'),filing.get('report_date'),filing.get('filed_date'))!=(accession,controlling.get('form'),period,filed):
        raise ValueError('mandatory-convertible narrative filing identity mismatch')
    narrative=terms_by_name(receipt)
    required={'annual_dividend_rate','liquidation_preference_per_share','dividend_payment_day','dividend_payment_months',
        'declared_quarterly_dividend_per_share','dividend_declaration_date','next_dividend_payment_date',
        'mandatory_conversion_date','minimum_conversion_rate','maximum_conversion_rate','vwap_trading_days',
        'vwap_start_trading_day_offset','capped_call_cap_price','capped_call_treatment'}
    if set(narrative)!=required:raise ValueError('mandatory-convertible narrative term set changed')
    nv={name:row['value'] for name,row in narrative.items()}
    if not isclose(float(nv['liquidation_preference_per_share']),per_share,rel_tol=0,abs_tol=.0001):
        raise ValueError('narrative and structured liquidation preference conflict')
    if not isclose(shares*float(nv['declared_quarterly_dividend_per_share']),dividend,rel_tol=0,abs_tol=50_000):
        raise ValueError('narrative and structured quarterly dividend conflict')
    if not isclose(float(nv['annual_dividend_rate'])*per_share/4,float(nv['declared_quarterly_dividend_per_share']),rel_tol=0,abs_tol=.0001):
        raise ValueError('narrative annual and quarterly dividend terms conflict')
    cutoff_date=date.fromisoformat(cutoff);conversion_date=date.fromisoformat(str(nv['mandatory_conversion_date']))
    if conversion_date<=cutoff_date:raise ValueError('mandatory conversion is no longer a future event')
    month_numbers={name:index for index,name in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'),1)}
    months=nv['dividend_payment_months'];day=int(nv['dividend_payment_day'])
    if not isinstance(months,list) or not months or any(month not in month_numbers for month in months):
        raise ValueError('preferred dividend payment calendar is invalid')
    payment_dates=[]
    for year in range(cutoff_date.year,conversion_date.year+1):
        for month in months:
            payment=date(year,month_numbers[month],day)
            if cutoff_date<payment<=conversion_date:payment_dates.append(payment)
    payment_dates=sorted(set(payment_dates))
    if not payment_dates or payment_dates[0].isoformat()!=nv['next_dividend_payment_date'] or payment_dates[-1]!=conversion_date:
        raise ValueError('preferred dividend schedule does not reconcile to filed dates')
    quarterly=shares*float(nv['declared_quarterly_dividend_per_share'])
    dividend_pv={case:sum(quarterly/((1+float(rates[case]))**((payment-cutoff_date).days/365.25)) for payment in payment_dates)
        for case in ('bear','base','bull')}
    minimum=float(nv['minimum_conversion_rate']);maximum=float(nv['maximum_conversion_rate'])
    if not 0<minimum<maximum:raise ValueError('mandatory conversion rate range is invalid')
    conversion_rates={'bear':maximum,'base':(minimum+maximum)/2,'bull':minimum}
    conversion_shares={case:shares*rate for case,rate in conversion_rates.items()}
    result={"status":"source_bound","claim_adjustment":dividend_pv['base'],"review_reasons":[],
        "policy":dict(policy),"period_end":period,"controlling_accession":accession,
        "components":{"preferred_shares":shares,"liquidation_preference":liquidation,
            "liquidation_preference_per_share":per_share,"quarter_dividend_cash":dividend,
            "declared_quarterly_dividend_per_share":declared,"current_conversion_increment":conversion,
            "liquidation_preference_deducted":False,"future_dividend_pv":dividend_pv,
            "future_conversion_shares":conversion_shares,"conversion_rates":conversion_rates,
            "payment_dates":[item.isoformat() for item in payment_dates],
            "capped_call_cap_price":nv['capped_call_cap_price'],"capped_call_treatment":nv['capped_call_treatment']},
        "source_rows":[shares_row,liquidation_row,per_share_row,dividend_row,declared_row,conversion_row],
        "narrative_evidence":dict(receipt),"excluded_rows":[preferred_row],
        "formula":"sum(source scheduled quarterly dividend / (1 + scenario WACC) ^ exact year fraction); add preferred shares times scenario conversion rate to source shares; do not deduct liquidation preference or uncertain capped-call benefit"}
    for case in ('bear','base','bull'):
        result[f'{case}_adjustment']=dividend_pv[case]
        result[f'{case}_conversion_shares']=conversion_shares[case]
    return result


__all__=["RULES","SCHEMA","VERSION","convertible_claim_policy","select_convertible_claim"]
