"""Deterministic private evidence extraction from hashed filing narrative.

This module is deliberately small and non-generative.  It reads only the
primary document declared by an immutable filing-package manifest, normalizes
visible HTML text, applies a versioned semantic contract, and returns exact
locators and hashes.  A missing, duplicate, or conflicting term fails closed.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

from .catalog import canonical_json_bytes, sha256_bytes


SCHEMA = "FINSIGHT-NARRATIVE-EVIDENCE-1"
VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG11-1"
WG21_VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG21-1"
WG25_VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG25-1"
WG27_VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG27-1"
WG28_VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG28-1"
WG30_VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG30-1"
WG31_VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG31-1"
WG34_VERSION = "FINSIGHT-NARRATIVE-EVIDENCE-WG34-1"


POLICIES: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    'HON':MappingProxyType({'schema_version':SCHEMA,'version':'FINSIGHT-NARRATIVE-EVIDENCE-WG36-1','ticker':'HON','cik':'0000773840','mechanism':'separation_scope'}),
    'HCA':MappingProxyType({'schema_version':SCHEMA,'version':WG34_VERSION,'ticker':'HCA','cik':'0000860730',
        'mechanism':'professional_liability_forward_scope','section_anchor':r'Investments of our insurance subsidiaries, held to maintain statutory equity levels and to provide liquidity to pay claims, totaled',
        'section_end':'Market Risk'}),
    'MCK':MappingProxyType({'schema_version':SCHEMA,'version':WG31_VERSION,
        'ticker':'MCK','cik':'0000927653','mechanism':'settlement_payment_bridge',
        'section_anchor':r'The Company’s estimated accrued liability for the above-described opioid-related claims',
        'section_end':'Canadian Plaintiff Claims','ownership_section_anchor':r'5\. Redeemable Noncontrolling Interests and Noncontrolling Interests',
        'ownership_section_end':'6. Earnings Per Common Share'}),
    "LHX":MappingProxyType({'schema_version':SCHEMA,'version':WG28_VERSION,
        'ticker':'LHX','cik':'0000202058','mechanism':'subsidiary_preferred_bridge',
        'section_anchor':r'NOTE B: STRATEGIC INVESTMENT IN SUBSIDIARY Overview On',
        'section_end':'NOTE C:','environmental_section_anchor':r'Environmental Matters We are subject to numerous',
        'environmental_section_end':'REPORT OF INDEPENDENT REGISTERED PUBLIC ACCOUNTING FIRM'}),
    "INTC": MappingProxyType({
        "schema_version":SCHEMA,"version":WG25_VERSION,"ticker":"INTC","cik":"0000050863",
        "mechanism":"lease_capital_payment_scope","scope_variant":"extended_term_financing_cash",
        "section_anchor":r"Financing Activities Financing cash flows consist primarily of",
        "section_end":"Risk Factors and Other Key Information",
    }),
    "JBL": MappingProxyType({
        "schema_version":SCHEMA,"version":WG25_VERSION,"ticker":"JBL","cik":"0000898293",
        "mechanism":"lease_capital_payment_scope","scope_variant":"new_only_lease_schedule",
        "section_anchor":r"4\. Leases During fiscal year [0-9]{4}, the Company entered into new operating and finance leases\.",
        "section_end":"5. Goodwill and Other Intangible Assets",
    }),
    "MCHP": MappingProxyType({
        "schema_version": SCHEMA,
        "version": VERSION,
        "ticker": "MCHP",
        "cik": "0000827054",
        "mechanism": "mandatory_convertible_preferred",
        "section_anchor": r"Series A Mandatory Convertible Preferred Stock In [A-Z][a-z]+ [0-9]{4}, the Company issued",
        "section_end": "Common Stock Dividends",
    }),
    "BMY": MappingProxyType({
        "schema_version": SCHEMA,
        "version": VERSION,
        "ticker": "BMY",
        "cik": "0000014272",
        "mechanism": "acquisition_and_license_payments",
        "section_anchor": r"Hengrui License Agreements In [A-Z][a-z]+ [0-9]{4}, BMS and Hengrui entered",
        "section_end": "Priority Review Voucher",
        "related_section_anchor": r"BioNTech In [A-Z][a-z]+ [0-9]{4}, BMS and BioNTech entered",
        "related_section_end": "Note 4.",
    }),
    "ECL": MappingProxyType({
        "schema_version": SCHEMA,
        "version": WG21_VERSION,
        "ticker": "ECL",
        "cik": "0000031462",
        "mechanism": "completed_acquisition_funding_overlay",
        "source_role": "controlling_filing",
        "section_anchor": r"CoolIT Systems Acquisition On [A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}, Ecolab entered",
        "section_end": "4. BALANCE SHEETS INFORMATION",
        "related_section_anchor": r"In [A-Z][a-z]+ [0-9]{4}, the Company issued",
        "related_section_end": "The Company’s public notes may be redeemed",
    }),
    "PH": MappingProxyType({
        "schema_version": SCHEMA,
        "version": WG21_VERSION,
        "ticker": "PH",
        "cik": "0000076334",
        "mechanism": "completed_acquisition_funding_overlay",
        "source_role": "event_filing",
        "section_anchor": r"Pursuant to the Merger Agreement, Parker agreed to acquire Filtration Group",
        "section_end": "Item 9.01. Financial Statements and Exhibits.",
    }),
})


class NarrativeEvidenceError(ValueError):
    """The filing bytes do not satisfy the declared narrative contract."""


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"head", "script", "style", "ix:hidden"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"head", "script", "style", "ix:hidden"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored:
            value = " ".join(data.replace("\xa0", " ").split())
            if value:
                self.parts.append(value)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


def narrative_policy(ticker: str) -> dict[str, Any]:
    policy = POLICIES.get(ticker.upper())
    if policy is None:
        raise ValueError(f"no narrative evidence policy for {ticker!r}")
    return deepcopy(dict(policy))


def _same_policy(policy: Mapping[str, Any]) -> bool:
    expected = POLICIES.get(str(policy.get("ticker", "")).upper())
    return expected is not None and canonical_json_bytes(dict(policy)) == canonical_json_bytes(dict(expected))


def _section(text: str, anchor: str, end: str) -> tuple[str, int, int]:
    starts = list(re.finditer(anchor, text))
    candidates: list[tuple[str, int, int]] = []
    for match in starts:
        finish = text.find(end, match.end())
        if finish >= 0:
            candidates.append((text[match.start():finish], match.start(), finish))
    if len(candidates) != 1:
        raise NarrativeEvidenceError(f"narrative section is missing or ambiguous: {anchor}")
    return candidates[0]


def _one(section: str, pattern: str, *, offset: int, name: str) -> re.Match[str]:
    matches = list(re.finditer(pattern, section, re.IGNORECASE))
    if len(matches) != 1:
        raise NarrativeEvidenceError(f"narrative term is missing or ambiguous: {name}")
    return matches[0]


def _term(section: str, pattern: str, *, offset: int, name: str, value: Any, unit: str,
          section_name: str | None = None) -> dict[str, Any]:
    match = _one(section, pattern, offset=offset, name=name)
    start, end = offset + match.start(), offset + match.end()
    excerpt = section[match.start():match.end()]
    result = {
        "name": name,
        "value": value,
        "unit": unit,
        "locator": {"normalized_text_start": start, "normalized_text_end": end},
        "excerpt_sha256": sha256(excerpt.encode("utf-8")).hexdigest(),
    }
    if section_name is not None:
        result["section"] = section_name
    return result


def _number(raw: str) -> float:
    return float(raw.replace(",", ""))


def _lease_capital_payment_scope(text,policy):
    section,start,end=_section(text,policy['section_anchor'],policy['section_end'])
    terms=[]
    if policy['scope_variant']=='extended_term_financing_cash':
        terms.append(_term(section,r'Financing cash flows consist primarily of borrowings and repayments of term debt and commercial paper, financing payments for capital expenditures with extended payment terms',
            offset=start,name='capital_payment_economic_scope',value='extended_term_financing_cash',unit='economic_scope',section_name='MD&A Financing Activities'))
    elif policy['scope_variant']=='new_only_lease_schedule':
        terms.append(_term(section,r'The future minimum lease payments under these new leases',offset=start,
            name='lease_schedule_economic_scope',value='new_only_operating_and_finance_leases',unit='economic_scope',section_name='Note 4 Leases'))
        for name,pattern in (
            ('residual_guarantee_excluded_disclosure',r'Excludes \$\s*(?P<amount>[0-9,]+) million of residual value guarantees'),
            ('uncommenced_combined_lease_payments',r'Excludes \$\s*(?P<amount>[0-9,]+) million of payments related to leases signed but not yet commenced')):
            match=_one(section,pattern,offset=start,name=name)
            terms.append(_term(section,pattern,offset=start,name=name,value=_number(match['amount'])*1_000_000,unit='USD',section_name='Note 4 Leases'))
        pattern=r'The Company does not believe it is probable that any amounts will be owed under these guarantees\.'
        terms.append(_term(section,pattern,offset=start,name='guarantee_recognition_scope',
            value='not_probable_excluded_from_lease_measurement',unit='economic_scope',section_name='Note 4 Leases'))
    else:raise NarrativeEvidenceError('unsupported lease/capital scope variant')
    return terms,[{'name':'lease_capital_scope','normalized_text_start':start,'normalized_text_end':end}]


def _settlement_payment_bridge(text,policy):
    section,start,end=_section(text,policy['section_anchor'],policy['section_end'])
    pattern=r'In (?P<month>[A-Z][a-z]+) (?P<year>[0-9]{4}), the Company made payments totaling \$\s*(?P<n>[0-9,.]+) million associated with the Settlement and the separate settlement agreements for opioid-related claims of participating states, subdivisions, and Native American tribes'
    m=_one(section,pattern,offset=start,name='subsequent_settlement_payment')
    terms=[_term(section,pattern,offset=start,name='subsequent_settlement_payment',value=_number(m['n'])*1_000_000,unit='USD',section_name='Opioid settlement accrual and payments'),
        _term(section,pattern,offset=start,name='payment_month',value=m['month']+' '+m['year'],unit='calendar_month_not_payment_day',section_name='Opioid settlement accrual and payments')]
    zero=r'During the three months ended (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}), the Company made no payments associated with the Settlement and the separate settlement agreements for opioid-related claims of participating states, subdivisions, and Native American tribes'
    z=_one(section,zero,offset=start,name='reported_period_payments')
    terms.extend([_term(section,zero,offset=start,name='reported_period_payments',value=0.,unit='USD',section_name='Opioid settlement accrual and payments'),
        _term(section,zero,offset=start,name='reported_zero_period_end',value=_date(z['date']),unit='date',section_name='Opioid settlement accrual and payments')])
    sections=[{'name':'Opioid settlement accrual and payments','normalized_text_start':start,'normalized_text_end':end}]
    if policy.get('ownership_section_anchor'):
        own,records=_subsidiary_ownership_terms(text,policy);terms.extend(own);sections.extend(records)
    return terms,sections

def _professional_liability_forward_scope(text,policy):
    section,start,end=_section(text,policy['section_anchor'],policy['section_end']);terms=[]
    def add(name,pattern,value,unit):terms.append(_term(section,pattern,offset=start,name=name,value=value,unit=unit,section_name='Professional liability liquidity and reserves'))
    specs=(
      ('insurance_investments',r'Investments of our insurance subsidiaries, held to maintain statutory equity levels and to provide liquidity to pay claims, totaled \$\s*(?P<a>[0-9,.]+) million and \$\s*(?P<b>[0-9,.]+) million',('a','b'),'USD'),
      ('insurance_subsidiary_reserve',r'An insurance subsidiary maintained net reserves for professional liability risks of \$\s*(?P<a>[0-9,.]+) million and \$\s*(?P<b>[0-9,.]+) million',('a','b'),'USD'),
      ('self_insured_reserve',r'Net reserves for the self-insured professional liability risks retained were \$\s*(?P<a>[0-9,.]+) billion and \$\s*(?P<b>[0-9,.]+) billion',('a','b'),'USD'),
      ('next_12_month_payments',r'Claims payments, net of reinsurance recoveries, during the next 12 months are expected to approximate \$\s*(?P<a>[0-9,.]+) million',('a',),'USD_expected_aggregate_not_timed_schedule'),
      ('next_12_month_retained_payments',r'approximately \$\s*(?P<a>[0-9,.]+) million of the expected net claim payments during the next 12 months will relate to claims subject to the self-insured retention',('a',),'USD_expected_aggregate_not_timed_schedule'))
    for name,pattern,keys,unit in specs:
        match=_one(section,pattern,offset=start,name=name);values=[_money(match[key],'billion' if 'billion' in pattern else 'million') for key in keys]
        add(name,pattern,values[0] if len(values)==1 else {'current':values[0],'comparative':values[1]},unit)
    pattern=r'insured by our insurance subsidiary for losses up to \$\s*(?P<a>[0-9,.]+) million per occurrence; however, this coverage is subject, in most cases, to a \$\s*(?P<b>[0-9,.]+) million per occurrence self-insured retention'
    match=_one(section,pattern,offset=start,name='coverage_and_retention')
    add('coverage_limit_per_occurrence',pattern,_money(match['a'],'million'),'USD_per_occurrence_not_liability')
    add('self_insured_retention_per_occurrence',pattern,_money(match['b'],'million'),'USD_per_occurrence_not_liability')
    pattern=r'the insurance subsidiary has entered into reinsurance contracts providing reimbursement for a certain portion of losses in excess of self-insured retentions'
    add('reinsurance_scope',pattern,'contract_exists_recovery_amount_not_disclosed','classification')
    pattern=r'cash flows from operations, amounts available under our senior unsecured credit facility and our anticipated access to public and private debt markets will be sufficient to meet expected liquidity needs'
    add('funding_scope',pattern,'operating_cash_credit_and_debt_not_allocated','classification')
    return terms,[{'name':'Professional liability liquidity and reserves','normalized_text_start':start,'normalized_text_end':end}]

def _subsidiary_ownership_terms(text,policy):
    section,start,end=_section(text,policy['ownership_section_anchor'],policy['ownership_section_end']);terms=[]
    rows=(
        (r'Beginning balance \$ (?P<ordinary_begin>[0-9,]+) \$ (?P<redeemable_begin>[0-9,]+) \$ [0-9,]+ \$ —',('ordinary_begin','redeemable_begin')),
        (r'Net income attributable to noncontrolling interests \(1\) (?P<ordinary_income>[0-9,]+) (?P<redeemable_income>[0-9,]+) [0-9,]+ —',('ordinary_income','redeemable_income')),
        (r'Adjustment to fair value \(2\) — (?P<redeemable_fair>[0-9,]+) — —',('redeemable_fair',)),
        (r'Adjustment to redemption value in net income attributable to noncontrolling interests \(3\) — (?P<redeemable_redemption>[0-9,]+) — —',('redeemable_redemption',)),
        (r'Sale of noncontrolling interest in Medical-Surgical Solutions, net — (?P<net_sale>[0-9,]+) — —',('net_sale',)),
        (r'Payments to noncontrolling interests \( (?P<ordinary_distribution>[0-9,]+) \) — \( [0-9,]+ \) —',('ordinary_distribution',)),
        (r'Other \( (?P<ordinary_other>[0-9,]+) \) \( (?P<redeemable_other>[0-9,]+) \) \( [0-9,]+ \) —',('ordinary_other','redeemable_other')),
        (r'Ending balance \$ (?P<ordinary_end>[0-9,]+) \$ (?P<redeemable_end>[0-9,]+) \$ [0-9,]+ \$ [0-9,]+',('ordinary_end','redeemable_end')),
        (r'Includes redemption value adjustments of \$ (?P<mms_redemption>[0-9,]+) million and \$ (?P<core_redemption>[0-9,]+) million related to the Medical-Surgical Solutions business and Core Ventures, respectively',('mms_redemption','core_redemption')))
    for pattern,names in rows:
        match=_one(section,pattern,offset=start,name=names[0])
        for name in names:terms.append(_term(section,pattern,offset=start,name=name,value=_number(match[name])*1_000_000,unit='USD_reported_rollforward_movement_or_balance',section_name='Note 5 Ownership rollforward'))
    event=r'On (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}), the Company completed a transaction under which funds managed by affiliates of Apollo Funds acquired an approximately (?P<pct>[0-9,.]+) % minority ownership interest in the Company’s Medical‑Surgical Solutions business through an investment of approximately \$ (?P<n>[0-9,.]+) (?P<scale>billion|million) in the business’s convertible preferred equity'
    match=_one(section,event,offset=start,name='apollo_event')
    for name,value,unit in (('apollo_event_date',_date(match['date']),'date'),('apollo_approximate_investment',_money(match['n'],match['scale']),'USD_approximate_event_not_current_claim'),('apollo_subsidiary_ownership_percent',_number(match['pct']),'percent_subsidiary_not_parent')):
        terms.append(_term(section,event,offset=start,name=name,value=value,unit=unit,section_name='Note 5 Apollo event'))
    pattern=r'The Company utilized a Monte Carlo simulation model for its periodic valuation of the redeemable noncontrolling interests for both acquisitions'
    terms.append(_term(section,pattern,offset=start,name='issuer_put_valuation_method',value='issuer_monte_carlo_inputs_not_disclosed_not_replicated',unit='classification',section_name='Note 5'))
    put=r'The (?P<pct>[0-9,.]+) % minority interest is classified as redeemable noncontrolling interest, with a put option exercisable every (?P<years>five|[0-9]+) years'
    core,cs,ce=_section(text,r'Community Oncology Revitalization Enterprise Ventures, LLC On','Divestitures Medical-Surgical Solutions')
    match=_one(core,put,offset=cs,name='core_put_cadence')
    terms.append(_term(core,put,offset=cs,name='core_put_cadence_years',value=5 if match['years']=='five' else int(match['years']),unit='years_cadence_not_exercise_date',section_name='Note 2 Core Ventures'))
    terms.append(_term(core,put,offset=cs,name='core_retained_minority_percent',value=_number(match['pct']),unit='percent_subsidiary_not_parent',section_name='Note 2 Core Ventures'))
    historical=r'During the three months ended (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}), the Company recognized redeemable noncontrolling interests of \$ (?P<prism>[0-9,]+) million related to its acquisition of PRISM Vision and \$ (?P<core>[0-9,]+) million related to its acquisition of Core Ventures'
    match=_one(section,historical,offset=start,name='historical_acquisition_rni')
    for name,value,unit in (('historical_prism_rni',_number(match['prism'])*1_000_000,'USD_historical_acquisition_not_current_claim'),('historical_core_rni',_number(match['core'])*1_000_000,'USD_historical_acquisition_not_current_claim'),('historical_rni_period_end',_date(match['date']),'date')):
        terms.append(_term(section,historical,offset=start,name=name,value=value,unit=unit,section_name='Note 5 Historical acquisition recognition'))
    return terms,[{'name':'Note 5 Ownership','normalized_text_start':start,'normalized_text_end':end},{'name':'Note 2 Core Ventures','normalized_text_start':cs,'normalized_text_end':ce}]

def _subsidiary_preferred_bridge(text,policy):
    section,start,end=_section(text,policy['section_anchor'],policy['section_end']);terms=[]
    def add(name,pattern,value,unit):
        terms.append(_term(section,pattern,offset=start,name=name,value=value,unit=unit,section_name='Note B Strategic Investment in Subsidiary'))
    for name,pattern,value in (
        ('exclusive_outcomes',r'The options are mutually exclusive and are dependent on achieving those milestones\.',True),
        ('bifurcated_features',r'These features of the Subsidiary Series A Preferred Stock were bifurcated from the host instrument and recorded as a derivative liability','conversion_and_redemption_features_bifurcated'),
        ('program_asset_noncash',r'is recognized as a non-cash financing activity and excluded from our Condensed Consolidated Statement of Cash Flows','noncash_operating_program_asset_not_surplus_cash'),
        ('not_currently_redeemable',r'While the Subsidiary Series A Preferred Stock is not currently redeemable',True)):
        add(name,pattern,value,'economic_scope')
    money=(
        ('gross_cash',r'for an aggregate purchase price of \$\s*(?P<n>[0-9,.]+) (?P<scale>billion|million)'),
        ('net_cash',r'Net proceeds of \$\s*(?P<n>[0-9,.]+) (?P<scale>billion|million) are to be used'),
        ('program_asset',r'We recognized a program investment intangible asset of \$\s*(?P<n>[0-9,.]+) (?P<scale>billion|million)'),
        ('deferred_tax',r'we recorded a deferred tax liability of \$\s*(?P<n>[0-9,.]+) (?P<scale>billion|million)'),
        ('transaction_costs',r'We incurred transaction costs of \$\s*(?P<n>[0-9,.]+) (?P<scale>billion|million)'),
        ('highest_redemption',r'current highest redemption value of \$\s*(?P<n>[0-9,.]+) (?P<scale>billion|million)'))
    for name,pattern in money:
        m=_one(section,pattern,offset=start,name=name);add(name,pattern,_money(m['n'],m['scale']),'USD')
    amort=r'This asset will be amortized as a reduction to revenue on a straight-line basis over its estimated useful life of (?P<n>[0-9]+) years, commencing upon achievement of a milestone'
    m=_one(section,amort,offset=start,name='amortization_years');add('amortization_years',amort,int(m['n']),'years')
    allocation=r'Subsidiary Series A preferred stock conversion feature \$\s*(?P<f>[0-9,]+) Subsidiary warrants (?P<w>[0-9,]+) Redeemable subsidiary Series A convertible preferred stock (?P<h>[0-9,]+) Program Investment Asset\.'
    m=_one(section,allocation,offset=start,name='initial_allocation')
    for name,key in (('initial_feature','f'),('initial_warrant','w'),('initial_host','h')):
        add(name,allocation,_number(m[key])*1_000_000,'USD')
    roll=r'Deferred tax liability \( (?P<t>[0-9,]+) \) Transaction costs \( (?P<c>[0-9,]+) \) Subsidiary preferred stock deemed dividend (?P<d>[0-9,]+) Balance as of (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}) \$\s*(?P<h>[0-9,]+)'
    m=_one(section,roll,offset=start,name='host_rollforward')
    for name,key in (('roll_tax','t'),('roll_costs','c'),('deemed_dividend','d'),('current_host','h')):
        add(name,roll,_number(m[key])*1_000_000,'USD')
    add('host_balance_date',roll,_date(m['date']),'date')
    for name,pattern in (
        ('qipo_deadline',r'Qualified Initial Public Offering of AR on or before (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})'),
        ('nonipo_reference_date',r'fair value of the Missile Solutions segment on (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}) if a QIPO does not occur'),
        ('valuation_not_before',r'redemption price would be calculated on or after (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})')):
        m=_one(section,pattern,offset=start,name=name);add(name,pattern,_date(m['date']),'date')
    for name,pattern in (
        ('dividend_rate',r'plus (?P<n>[0-9.]+) % cumulative annual dividends, compounded quarterly'),
        ('conversion_discount',r'at a (?P<n>[0-9.]+) % discount \(the “Conversion Price”\)'),
        ('nonipo_premium',r'contractual premium of (?P<n>[0-9.]+) % to the Liquidation Preference'),
        ('warrant_fraction',r'shares representing (?P<n>[0-9.]+) % of the AXYV Common Stock, on a fully diluted basis')):
        m=_one(section,pattern,offset=start,name=name);add(name,pattern,_number(m['n'])/100,'fraction')
    sections=[{'name':'subsidiary_preferred_bridge','normalized_text_start':start,'normalized_text_end':end}]
    if policy.get('environmental_section_anchor'):
        env,es,ee=_section(text,policy['environmental_section_anchor'],policy['environmental_section_end'])
        pattern=r'Certain environmental costs are eligible for future recovery in the pricing of our products and services to the U\.S\. Government'
        terms.append(_term(env,pattern,offset=es,name='environmental_recovery_mechanism',
            value='future_government_contract_pricing_not_surplus_cash',unit='economic_scope',section_name='Note R Environmental Matters'))
        pattern=r'our liability and proportionate share of costs that may be shared among other PRPs have not been determined'
        terms.append(_term(env,pattern,offset=es,name='environmental_unquantified_scope',
            value='some_site_cost_shares_undetermined',unit='economic_scope',section_name='Note R Environmental Matters'))
        pattern=r'The current and non-current portions of our estimated environmental liability are included in the “Other current liabilities” and “Other non-current liabilities” line items'
        terms.append(_term(env,pattern,offset=es,name='environmental_liability_presentation',
            value='current_and_noncurrent_portions_not_quantified_here',unit='economic_scope',section_name='Note R Environmental Matters'))
        sections.append({'name':'environmental_forward_scope','normalized_text_start':es,'normalized_text_end':ee})
    return terms,sections


def _money(raw: str, scale: str) -> float:
    factor = {"million": 1_000_000.0, "billion": 1_000_000_000.0}.get(scale.lower())
    if factor is None:
        raise NarrativeEvidenceError(f"unsupported narrative money scale: {scale}")
    return _number(raw) * factor


def _date(raw: str) -> str:
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise NarrativeEvidenceError(f"unsupported narrative date: {raw}")


def _section_record(section: str, start: int, end: int, anchor: str) -> dict[str, Any]:
    return {
        "anchor": anchor,
        "locator": {"normalized_text_start": start, "normalized_text_end": end},
        "text_sha256": sha256(section.encode("utf-8")).hexdigest(),
    }


def _mchp(text: str, policy: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    section, start, end = _section(text, str(policy["section_anchor"]), str(policy["section_end"]))
    patterns = {
        "dividend": r"Dividends are cumulative at an annual rate of (?P<rate>[0-9]+(?:\.[0-9]+)?)\s*% on the liquidation preference of \$\s*(?P<preference>[0-9,.]+) per share",
        "schedule": r"payable on the (?P<day>[0-9]+)(?:st|nd|rd|th) of (?P<months>[A-Za-z]+, [A-Za-z]+, [A-Za-z]+ and [A-Za-z]+)",
        "declared": r"quarterly cash dividend of \$\s*(?P<amount>[0-9,.]+) per share of Series A Preferred Stock was declared on (?P<declared>[A-Z][a-z]+ [0-9]+, [0-9]{4}) and will be paid on (?P<payment>[A-Z][a-z]+ [0-9]+, [0-9]{4})",
        "conversion": r"automatically convert on (?P<date>[A-Z][a-z]+ [0-9]+, [0-9]{4}), into between (?P<minimum>[0-9,.]+) shares and (?P<maximum>[0-9,.]+) shares",
        "vwap": r"average volume-weighted average price per share.+?over the (?P<days>[0-9]+) consecutive trading day period.+?the (?P<offset>[0-9]+)(?:st|nd|rd|th) scheduled trading day immediately prior",
        "capped_call": r"capped call options subject to a cap price of \$\s*(?P<price>[0-9,.]+) per share.+?generally expected to reduce the potential dilution.+?and/or offset any cash payments",
    }
    matches = {name: _one(section, pattern, offset=start, name=name) for name, pattern in patterns.items()}
    dividend_rate = _number(matches["dividend"].group("rate")) / 100.0
    preference = _number(matches["dividend"].group("preference"))
    day = int(matches["schedule"].group("day"))
    months = [part.strip() for part in re.split(r",| and ", matches["schedule"].group("months"))]
    declared_amount = _number(matches["declared"].group("amount"))
    declared_date = _date(matches["declared"].group("declared"))
    payment_date = _date(matches["declared"].group("payment"))
    conversion_date = _date(matches["conversion"].group("date"))
    minimum = _number(matches["conversion"].group("minimum"))
    maximum = _number(matches["conversion"].group("maximum"))
    if minimum <= 0 or maximum <= minimum or not (0 < dividend_rate < 1) or preference <= 0:
        raise NarrativeEvidenceError("mandatory-convertible narrative terms are economically invalid")
    values = {
        "annual_dividend_rate": dividend_rate,
        "liquidation_preference_per_share": preference,
        "dividend_payment_day": day,
        "dividend_payment_months": months,
        "declared_quarterly_dividend_per_share": declared_amount,
        "dividend_declaration_date": declared_date,
        "next_dividend_payment_date": payment_date,
        "mandatory_conversion_date": conversion_date,
        "minimum_conversion_rate": minimum,
        "maximum_conversion_rate": maximum,
        "vwap_trading_days": int(matches["vwap"].group("days")),
        "vwap_start_trading_day_offset": int(matches["vwap"].group("offset")),
        "capped_call_cap_price": _number(matches["capped_call"].group("price")),
        "capped_call_treatment": "excluded_unless_realized_offset_is_source_bound",
    }
    units = {
        "annual_dividend_rate": "ratio", "liquidation_preference_per_share": "USD/share",
        "dividend_payment_day": "day_of_month", "dividend_payment_months": "month_names",
        "declared_quarterly_dividend_per_share": "USD/share", "dividend_declaration_date": "date",
        "next_dividend_payment_date": "date", "mandatory_conversion_date": "date",
        "minimum_conversion_rate": "common_shares/preferred_share", "maximum_conversion_rate": "common_shares/preferred_share",
        "vwap_trading_days": "trading_days", "vwap_start_trading_day_offset": "trading_days",
        "capped_call_cap_price": "USD/share", "capped_call_treatment": "classification",
    }
    term_to_pattern = {
        "annual_dividend_rate": "dividend", "liquidation_preference_per_share": "dividend",
        "dividend_payment_day": "schedule", "dividend_payment_months": "schedule",
        "declared_quarterly_dividend_per_share": "declared", "dividend_declaration_date": "declared",
        "next_dividend_payment_date": "declared", "mandatory_conversion_date": "conversion",
        "minimum_conversion_rate": "conversion", "maximum_conversion_rate": "conversion",
        "vwap_trading_days": "vwap", "vwap_start_trading_day_offset": "vwap",
        "capped_call_cap_price": "capped_call", "capped_call_treatment": "capped_call",
    }
    terms = []
    for name, value in values.items():
        key = term_to_pattern[name]
        terms.append(_term(section, patterns[key], offset=start, name=name, value=value, unit=units[name]))
    return terms, {"preferred_stock": _section_record(section, start, end, str(policy["section_anchor"]))}


def _bmy(text: str, policy: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    hengrui, hs, he = _section(text, str(policy["section_anchor"]), str(policy["section_end"]))
    biontech, bs, be = _section(text, str(policy["related_section_anchor"]), str(policy["related_section_end"]))
    specs = [
        (hengrui, hs, "hengrui_upfront_payment", r"upfront payment to Hengrui of \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) in the (?P<quarter>(?:first|second|third|fourth) quarter) of (?P<year>[0-9]{4})", "USD", lambda m: _money(m.group("amount"), m.group("scale"))),
        (hengrui, hs, "hengrui_first_anniversary_payment", r"a \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) anniversary payment, payable in (?P<year>[0-9]{4})", "USD", lambda m: _money(m.group("amount"), m.group("scale"))),
        (hengrui, hs, "hengrui_second_anniversary_payment", r"second \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) anniversary payment.+?payable in (?P<year>[0-9]{4}) provided that there is no prior termination", "USD", lambda m: _money(m.group("amount"), m.group("scale"))),
        (hengrui, hs, "hengrui_contingent_milestone_maximum", r"up to \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) of contingent development, regulatory and sales-based milestones", "USD maximum exposure", lambda m: _money(m.group("amount"), m.group("scale"))),
        (biontech, bs, "biontech_paid_upfront_payment", r"made an upfront payment to BioNTech of \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) during the (?P<quarter>(?:first|second|third|fourth) quarter) of (?P<year>[0-9]{4})", "USD paid cash", lambda m: _money(m.group("amount"), m.group("scale"))),
        (biontech, bs, "biontech_future_anniversary_payments", r"receive \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) in aggregate of anniversary payments.+?beginning in the (?P<quarter>(?:first|second|third|fourth) quarter) of (?P<start_year>[0-9]{4}) through (?P<end_year>[0-9]{4})", "USD timing envelope", lambda m: _money(m.group("amount"), m.group("scale"))),
        (biontech, bs, "biontech_contingent_milestone_maximum", r"up to \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) of contingent development, regulatory and sales-based milestones", "USD maximum exposure", lambda m: _money(m.group("amount"), m.group("scale"))),
    ]
    terms: list[dict[str, Any]] = []
    for section, offset, name, pattern, unit, parser in specs:
        match = _one(section, pattern, offset=offset, name=name)
        row = _term(section, pattern, offset=offset, name=name, value=parser(match), unit=unit)
        for key in ("year", "start_year", "end_year", "quarter"):
            if key in match.groupdict() and match.group(key) is not None:
                row[key] = int(match.group(key)) if "year" in key else match.group(key).lower()
        terms.append(row)
    return terms, {
        "hengrui": _section_record(hengrui, hs, he, str(policy["section_anchor"])),
        "biontech": _section_record(biontech, bs, be, str(policy["related_section_anchor"])),
    }


def _completed_acquisition_overlay(
    text: str, policy: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    acquisition, start, end = _section(text, str(policy["section_anchor"]), str(policy["section_end"]))
    ticker = str(policy["ticker"])
    if ticker == "ECL":
        financing, fs, fe = _section(
            text, str(policy["related_section_anchor"]), str(policy["related_section_end"])
        )
        specs = [
            (acquisition, start, "acquisition_price",
             r"agreement to acquire CoolIT Systems for \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion), subject to certain adjustments",
             "USD agreement price subject to adjustments", lambda m: _money(m.group("amount"), m.group("scale")), "acquisition"),
            (acquisition, start, "close_date",
             r"The acquisition was completed on (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})",
             "date", lambda m: _date(m.group("date")), "acquisition"),
            (acquisition, start, "acquired_operating_scope",
             r"Beginning in the third quarter [0-9]{4}, the business will become part of the Company’s Global Water reportable segment",
             "classification", lambda _m: "Global Water reportable segment beginning in the third quarter", "acquisition"),
            (acquisition, start, "purchase_price_allocation_status",
             r"it is impractical to include a preliminary purchase price allocation",
             "classification", lambda _m: "not_available_at_filing", "acquisition"),
            (acquisition, start, "pro_forma_status",
             r"The pro forma financial information is not material to the Company's consolidated financial statements; therefore, this is not presented",
             "classification", lambda _m: "not_presented_as_immaterial", "acquisition"),
            (acquisition, start, "integration_cost_treatment",
             r"transaction and integration costs.+?were expensed and are reflected in the Consolidated Statements of Income",
             "classification", lambda _m: "expensed_in_operating_results", "acquisition"),
            (financing, fs, "issued_note_principal",
             r"The total proceeds of \$\s*(?P<amount>[0-9,.]+) (?P<scale>million|billion) were used to fund the CoolIT Systems acquisition and for general corporate purposes",
             "USD debt proceeds", lambda m: _money(m.group("amount"), m.group("scale")), "financing"),
            (financing, fs, "issued_note_use",
             r"The total proceeds of \$\s*[0-9,.]+ (?:million|billion) were used to fund the CoolIT Systems acquisition and for general corporate purposes",
             "classification", lambda _m: "acquisition_and_general_corporate_purposes", "financing"),
            (financing, fs, "delayed_draw_facility_status",
             r"terminated its unsecured committed delayed draw term loan credit facility.+?No amounts were drawn under the facility and no borrowings were outstanding at the time of termination",
             "classification", lambda _m: "terminated_undrawn", "financing"),
        ]
        sections = {
            "acquisition": _section_record(acquisition, start, end, str(policy["section_anchor"])),
            "financing": _section_record(financing, fs, fe, str(policy["related_section_anchor"])),
        }
    elif ticker == "PH":
        specs = [
            (acquisition, start, "acquisition_price",
             r"cash-free, debt-free basis for a cash purchase price of \$(?P<amount>[0-9,.]+) (?P<scale>million|billion), subject to a net working capital adjustment",
             "USD cash purchase price subject to working-capital adjustment", lambda m: _money(m.group("amount"), m.group("scale")), "acquisition_and_financing"),
            (acquisition, start, "close_date",
             r"On (?P<date>[A-Z][a-z]+ [0-9]{1,2}, [0-9]{4}), Parker completed the Merger",
             "date", lambda m: _date(m.group("date")), "acquisition_and_financing"),
            (acquisition, start, "short_term_loan_principal",
             r"borrowed \$(?P<amount>[0-9,.]+) (?P<scale>million|billion) under the 364-Day Credit Facility",
             "USD debt principal", lambda m: _money(m.group("amount"), m.group("scale")), "acquisition_and_financing"),
            (acquisition, start, "three_year_loan_principal",
             r"and \$(?P<amount>[0-9,.]+) (?P<scale>million|billion) under the Three-Year Credit Facility",
             "USD debt principal", lambda m: _money(m.group("amount"), m.group("scale")), "acquisition_and_financing"),
            (acquisition, start, "loan_use",
             r"to pay a portion of the Purchase Price and other fees and expenses related thereto",
             "classification", lambda _m: "portion_of_purchase_price_and_related_fees", "acquisition_and_financing"),
        ]
        sections = {
            "acquisition_and_financing": _section_record(
                acquisition, start, end, str(policy["section_anchor"])
            )
        }
    else:
        raise NarrativeEvidenceError("unsupported completed-acquisition issuer")
    terms: list[dict[str, Any]] = []
    for section, offset, name, pattern, unit, parser, section_name in specs:
        match = _one(section, pattern, offset=offset, name=name)
        terms.append(_term(section, pattern, offset=offset, name=name,
                           value=parser(match), unit=unit, section_name=section_name))
    return terms, sections


def _source_document(manifest: Mapping[str, Any], manifest_path: Path) -> tuple[str, Mapping[str, Any], dict[str, Any]]:
    """Normalize an XBRL package or an immutable event-source receipt."""
    entrypoint_name = manifest.get("entrypoint_local_path")
    resources = manifest.get("files")
    filing = {key: manifest.get(key) for key in ("accession", "form", "report_date", "filed_date")}
    if isinstance(entrypoint_name, str) and isinstance(resources, list):
        matching = [row for row in resources if isinstance(row, Mapping) and row.get("local_path") == entrypoint_name]
        if len(matching) != 1:
            raise NarrativeEvidenceError("narrative package primary resource is missing or ambiguous")
        return entrypoint_name, matching[0], filing
    if (manifest.get("schema_version") == "FINSIGHT-BATCH-19-EVENT-SOURCE-1"
            and isinstance(manifest.get("primary_document"), str)):
        entrypoint_name = str(manifest["primary_document"])
        resource = {"local_path": entrypoint_name, "sha256": manifest.get("document_sha256")}
        return entrypoint_name, resource, {
            "accession": manifest.get("accession"), "form": manifest.get("form"),
            "report_date": manifest.get("report_date"), "filed_date": manifest.get("filed"),
        }
    raise NarrativeEvidenceError("narrative source has no supported primary entrypoint")


def extract_narrative_evidence(policy: Mapping[str, Any], package_manifest_path: Path, *, source_root: Path) -> dict[str, Any]:
    """Extract and hash one filing's narrative evidence under a declared rule."""
    if not _same_policy(policy):
        raise NarrativeEvidenceError("narrative evidence policy identity/version mismatch")
    source_root = Path(source_root).resolve()
    manifest_path = Path(package_manifest_path).resolve()
    if not manifest_path.is_file() or not manifest_path.is_relative_to(source_root):
        raise NarrativeEvidenceError("package manifest is outside the allowed source root")
    manifest_raw = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_raw)
    except json.JSONDecodeError as exc:
        raise NarrativeEvidenceError("package manifest is invalid JSON") from exc
    if str(manifest.get("cik", "")).zfill(10) != policy["cik"]:
        raise NarrativeEvidenceError("narrative package CIK mismatch")
    entrypoint_name, resource, filing = _source_document(manifest, manifest_path)
    entrypoint = (manifest_path.parent / entrypoint_name).resolve()
    if not entrypoint.is_file() or not entrypoint.is_relative_to(manifest_path.parent):
        raise NarrativeEvidenceError("narrative primary document is unavailable or unsafe")
    if not isinstance(resource.get("sha256"), str):
        raise NarrativeEvidenceError("narrative package primary resource is missing or ambiguous")
    document_raw = entrypoint.read_bytes()
    document_hash = sha256_bytes(document_raw)
    if document_hash != resource["sha256"]:
        raise NarrativeEvidenceError("narrative primary document hash mismatch")
    parser = _VisibleText()
    try:
        parser.feed(document_raw.decode("utf-8"))
        parser.close()
    except (UnicodeDecodeError, ValueError) as exc:
        raise NarrativeEvidenceError("narrative primary document is not valid supported HTML") from exc
    text = parser.text
    if policy['mechanism']=='separation_scope':
        from .refresh_separation_scope import extract_separation_terms
        terms,sections=extract_separation_terms(text,policy)
    elif policy["mechanism"] == "mandatory_convertible_preferred":
        terms, sections = _mchp(text, policy)
    elif policy["mechanism"] == "acquisition_and_license_payments":
        terms, sections = _bmy(text, policy)
    elif policy["mechanism"] == "completed_acquisition_funding_overlay":
        terms, sections = _completed_acquisition_overlay(text, policy)
    elif policy['mechanism']=='lease_capital_payment_scope':
        terms,sections=_lease_capital_payment_scope(text,policy)
    elif policy['mechanism']=='subsidiary_preferred_bridge':
        terms,sections=_subsidiary_preferred_bridge(text,policy)
    elif policy['mechanism']=='settlement_payment_bridge':
        terms,sections=_settlement_payment_bridge(text,policy)
    elif policy['mechanism']=='professional_liability_forward_scope':
        terms,sections=_professional_liability_forward_scope(text,policy)
    else:
        raise NarrativeEvidenceError("unsupported narrative mechanism")
    receipt = {
        "schema_version": SCHEMA,
        "extraction_version": policy["version"],
        "policy": dict(policy),
        "ticker": policy["ticker"],
        "cik": policy["cik"],
        "filing": filing,
        "source": {
            "source_manifest_path": manifest_path.relative_to(source_root).as_posix(),
            "source_manifest_sha256": sha256_bytes(manifest_raw),
            "package_manifest_path": manifest_path.relative_to(source_root).as_posix(),
            "package_manifest_sha256": sha256_bytes(manifest_raw),
            "document_path": entrypoint.relative_to(source_root).as_posix(),
            "document_name": entrypoint.name,
            "document_sha256": document_hash,
            "document_byte_count": len(document_raw),
            "normalized_text_sha256": sha256(text.encode("utf-8")).hexdigest(),
        },
        "sections": sections,
        "terms": terms,
        "method": "stdlib_html_visible_text_plus_versioned_exact_regex; no AI; no OCR",
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json_bytes(receipt))
    return receipt


def validate_narrative_evidence(receipt: Mapping[str, Any], policy: Mapping[str, Any], *, source_root: Path) -> dict[str, Any]:
    """Re-extract a receipt from current bytes and require exact equality."""
    stored = dict(receipt)
    digest = stored.pop("receipt_sha256", None)
    if not isinstance(digest, str) or sha256_bytes(canonical_json_bytes(stored)) != digest:
        raise NarrativeEvidenceError("narrative receipt hash mismatch")
    source = receipt.get("source")
    manifest_key = source.get("source_manifest_path") if isinstance(source, Mapping) else None
    if not isinstance(manifest_key, str) and isinstance(source, Mapping):
        manifest_key = source.get("package_manifest_path")
    if not isinstance(source, Mapping) or not isinstance(manifest_key, str):
        raise NarrativeEvidenceError("narrative receipt source locator is invalid")
    rebuilt = extract_narrative_evidence(policy, Path(source_root) / manifest_key, source_root=source_root)
    if canonical_json_bytes(rebuilt) != canonical_json_bytes(dict(receipt)):
        raise NarrativeEvidenceError("narrative receipt no longer matches extracted source bytes")
    return rebuilt


def terms_by_name(receipt: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = receipt.get("terms")
    if not isinstance(rows, list):
        raise NarrativeEvidenceError("narrative receipt has no terms")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("name"), str) or row["name"] in result:
            raise NarrativeEvidenceError("narrative receipt term index is malformed")
        result[row["name"]] = dict(row)
    return result


__all__ = [
    "NarrativeEvidenceError", "POLICIES", "SCHEMA", "VERSION", "WG21_VERSION",
    "extract_narrative_evidence", "narrative_policy", "terms_by_name",
    "validate_narrative_evidence",
]
