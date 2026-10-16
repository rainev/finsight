"""Deterministic terms from official public documents; not contract valuation."""
from __future__ import annotations
from hashlib import sha256
import json,re
from pathlib import Path
from .catalog import canonical_json_bytes,sha256_bytes
from .refresh_narrative_evidence import _VisibleText,_number,_money

VERSION='FINSIGHT-PUBLIC-CONTRACT-EVIDENCE-WG32-1'
REQUIRED_LABELS=('core-q1-2025','core-q3-2025','mck-annual-2026','mms-deck-2026','mms-proxy-cover-2026','mms-official-announcement')
SOURCE_IDENTITIES={
 'core-q1-2025':('2025-08-06','https://www.sec.gov/Archives/edgar/data/927653/000092765325000107/mck-20250630.htm','text/html'),
 'core-q3-2025':('2026-02-04','https://www.sec.gov/Archives/edgar/data/927653/000092765326000017/mck-20251231.htm','text/html'),
 'mck-annual-2026':('2026-05-08','https://www.sec.gov/Archives/edgar/data/927653/000092765326000069/mck-20260331.htm','text/html'),
 'mms-deck-2026':('2026-06-30','https://www.sec.gov/Archives/edgar/data/927653/000092765326000182/a260604_mckinvestordeck202.pdf','application/pdf'),
 'mms-proxy-cover-2026':('2026-06-30','https://www.sec.gov/Archives/edgar/data/927653/000092765326000182/mck-20260630.htm','text/html'),
 'mms-official-announcement':('2026-04-20','https://investor.mckesson.com/news/financial-news/2026/McKesson-Signs-Agreement-with-Apollo-Funds-for-Strategic-Minority-Interest-in-Medical-Surgical-Solutions/default.aspx','text/html')}

def _source(root,row):
    path=(root/row['document_path']).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ValueError('public contract source unavailable or outside root')
    raw=path.read_bytes()
    if len(raw)!=row['byte_count'] or sha256_bytes(raw)!=row['sha256']:raise ValueError('public contract source hash/size mismatch')
    return path,raw
def _text(raw):
    p=_VisibleText();p.feed(raw.decode('utf-8'));p.close();return p.text
def _matches(text,pattern,name,values):
    found=list(re.finditer(pattern,text,re.I))
    if not found:raise ValueError('public contract term missing: '+name)
    rows=[]
    for match in found:
        value=values(match)
        excerpt=match.group(0)
        rows.append({'name':name,'value':value,'locator':{'normalized_text_start':match.start(),'normalized_text_end':match.end()},'excerpt_sha256':sha256(excerpt.encode()).hexdigest()})
    if len({json.dumps(row['value'],sort_keys=True) for row in rows})!=1:raise ValueError('public contract duplicate term conflicts: '+name)
    return rows

def extract_public_contract_evidence(capture_report, *,source_root):
    root=Path(source_root).resolve();report=Path(capture_report).resolve()
    if not report.is_file() or not report.is_relative_to(root):raise ValueError('public capture report outside source root')
    report_raw=report.read_bytes();cap=json.loads(report_raw)
    if cap.get('schema_version')!='FINSIGHT-PUBLIC-CONTRACT-EVIDENCE-CAPTURE-1' or cap.get('cutoff')!='2026-08-14' or cap.get('economic_validation') is not False:
        raise ValueError('public contract capture contract mismatch')
    indexed={row['label']:row for row in cap['rows']}
    if tuple(indexed)!=REQUIRED_LABELS or cap.get('attempted')!=6 or cap.get('captured')!=6:raise ValueError('public contract source inventory mismatch')
    texts={};sources=[]
    for label in REQUIRED_LABELS:
        row=indexed[label];path,raw=_source(root,row)
        source_date,url,content_type=SOURCE_IDENTITIES[label]
        if (row.get('source_date')!=source_date or row.get('url')!=url or row.get('final_url')!=url
            or row.get('content_type')!=content_type or row.get('cutoff')!='2026-08-14'):
            raise ValueError('public contract source identity/date/type mismatch: '+label)
        sources.append({**row,'document_path':path.relative_to(root).as_posix()})
        if row['content_type']=='text/html':texts[label]=_text(raw)
    put=r'The (?P<pct>[0-9,.]+) % minority interest is classified as redeemable noncontrolling interest, with a put option exercisable every (?P<years>five|[0-9]+) years subject to a floor of (?P<floor>[0-9,.]+) % of initial fair value'
    vintages=[]
    for label in ('core-q1-2025','core-q3-2025'):
        rows=_matches(texts[label],put,'core_put_floor',lambda m:{'retained_percent':_number(m['pct']),'cadence_years':5 if m['years'].lower()=='five' else int(m['years']),'floor_percent_of_initial_fair_value':_number(m['floor'])})
        vintages.append({'label':label,'terms':rows})
    values={json.dumps(v['terms'][0]['value'],sort_keys=True) for v in vintages}
    if len(values)!=1:raise ValueError('Core put terms disagree across filing vintages')
    recognized=r'recognized redeemable noncontrolling interests of \$\s*(?P<prism>[0-9,.]+) million related to (?:the |its )?acquisition of PRISM Vision and \$\s*(?P<core>[0-9,.]+) million related to (?:the |its )?acquisition of Core Ventures'
    recognized_rows=_matches(texts['core-q1-2025'],recognized,'initial_acquisition_rni',lambda m:{'prism':_number(m['prism'])*1_000_000,'core':_number(m['core'])*1_000_000})
    initial_core=recognized_rows[0]['value']['core'];floor_pct=vintages[0]['terms'][0]['value']['floor_percent_of_initial_fair_value']
    annual_fair=_matches(texts['mck-annual-2026'],r'recorded a fair value adjustment of \$\s*(?P<n>[0-9,.]+) million, which was recorded as a decrease in the Company’s additional paid-in capital',
        'annual_fair_value_adjustment',lambda m:_number(m['n'])*1_000_000)
    annual_redemption=_matches(texts['mck-annual-2026'],r'recognized a redemption value adjustment to the Core Ventures redeemable noncontrolling interest of \$\s*(?P<n>[0-9,.]+) million',
        'annual_core_redemption_adjustment',lambda m:_number(m['n'])*1_000_000)
    event=r'Apollo Funds will invest \$(?P<investment>[0-9,.]+) (?P<scale>billion|million) in convertible preferred equity of MMS to acquire an approximately (?P<pct>[0-9,.]+)% minority interest in MMS\. The transaction values MMS at approximately \$(?P<ev>[0-9,.]+) (?P<evscale>billion|million) total enterprise valuation'
    event_rows=_matches(texts['mms-official-announcement'],event,'apollo_announcement',lambda m:{'investment':_money(m['investment'],m['scale']),'subsidiary_interest_percent':_number(m['pct']),'transaction_enterprise_valuation':_money(m['ev'],m['evscale'])})
    result={'schema_version':'FINSIGHT-PUBLIC-CONTRACT-EVIDENCE-1','version':VERSION,'ticker':'MCK','cutoff':'2026-08-14',
        'capture_report_path':report.relative_to(root).as_posix(),'capture_report_sha256':sha256_bytes(report_raw),'sources':sources,
        'core_put':{'vintages':vintages,'initial_core_fair_value':initial_core,'floor_percent':floor_pct,
            'source_arithmetic_floor':initial_core*floor_pct/100,'first_exercise_date':None,'valuation_formula':None,
            'latest_annual_and_current_omission':'not_source_proven_revocation'},
        'historical_component_evidence':{'initial':recognized_rows,'annual_fair_value_adjustment':annual_fair,'annual_core_redemption_adjustment':annual_redemption,
            'current_per_instrument_reconciliation':None,'monte_carlo_inputs':None},
        'apollo_announcement':{'terms':event_rows,'treatment':'transaction descriptor only; not intrinsic value, current claim, conversion ratio, parent dilution or cash addback'},
        'not_economic_inputs':[{'label':'mms-deck-2026','reason':'visually reviewed strategy deck; no identified contract terms'},
            {'label':'mms-proxy-cover-2026','reason':'cover/attachment relationship only; not executed agreement'}],
        'executed_agreements_captured':False,'numeric_successor_issued':False,'claim_adjustment':None,
        'review_reasons':['apollo_mms_executed_preferred_and_governing_terms_not_captured','prism_put_terms_not_captured',
            'core_exact_exercise_windows_and_valuation_formula_not_captured','current_per_instrument_reconciliation_and_monte_carlo_inputs_not_captured']}
    result['receipt_sha256']=sha256_bytes(canonical_json_bytes(result));return result

def validate_public_contract_evidence(receipt, *,source_root):
    rebuilt=extract_public_contract_evidence(Path(source_root)/receipt['capture_report_path'],source_root=source_root)
    if canonical_json_bytes(rebuilt)!=canonical_json_bytes(receipt):raise ValueError('public contract evidence receipt/source drift')
    return rebuilt
