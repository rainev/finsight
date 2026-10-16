"""Hash-bound annual environmental observations, not a forward valuation recipe."""
import json
from math import isfinite
from pathlib import Path
import re
from .catalog import canonical_json_bytes, sha256_bytes
from .refresh_narrative_evidence import _VisibleText, _source_document, _section, _term
from .refresh_environmental_forward_scope import environmental_forward_policy

VERSION = 'FINSIGHT-ENVIRONMENTAL-ANNUAL-EVIDENCE-WG29-1'


def _path(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('annual evidence relative locator required')
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('annual evidence path unavailable or outside root')
    return path


def extract_annual_environmental_evidence(ticker, sources, *, source_root, cutoff):
    root = Path(source_root).resolve()
    policy = environmental_forward_policy(ticker)
    if not sources or len({s['structural_path'] for s in sources}) != len(sources):
        raise ValueError('unique annual evidence sources required')
    observations = []; bound_sources = []; dates = []
    for source in sources:
        manifest_path = _path(root, source['package_manifest_path'])
        structural_path = _path(root, source['structural_path'])
        manifest_raw = manifest_path.read_bytes(); m = json.loads(manifest_raw)
        raw = structural_path.read_bytes(); st = json.loads(raw)
        document, resource, filing = _source_document(m, manifest_path)
        if (str(m.get('cik','')).zfill(10) != policy['cik'] or filing['form'] not in ('10-K','10-K/A')
            or not filing['report_date'] <= filing['filed_date'] <= cutoff
            or st.get('source_accession') != filing['accession'] or st.get('form') != filing['form']
            or st.get('report_date') != filing['report_date'] or st.get('filed_date') != filing['filed_date']):
            raise ValueError('annual evidence issuer/filing/period/cutoff mismatch')
        dates.append((filing['filed_date'], filing['accession']))
        primary = (manifest_path.parent / document).resolve()
        if not primary.is_relative_to(manifest_path.parent) or not primary.is_file():
            raise ValueError('annual primary document unsafe or missing')
        document_raw = primary.read_bytes()
        if sha256_bytes(document_raw) != resource['sha256']:
            raise ValueError('annual primary document hash mismatch')
        # Authenticate the complete package used by the offline parser, not only HTML.
        if (not isinstance(m.get('files'),list) or m.get('resource_count')!=len(m['files'])
            or len({row['local_path'] for row in m['files']})!=len(m['files'])
            or m.get('total_bytes')!=sum(row['byte_count'] for row in m['files'])):
            raise ValueError('annual package resource count/bytes/duplicates invalid')
        package_files = []
        for row in m['files']:
            path = (manifest_path.parent / row['local_path']).resolve()
            if (not path.is_relative_to(manifest_path.parent) or not path.is_file()
                or path.stat().st_size!=row['byte_count'] or sha256_bytes(path.read_bytes()) != row['sha256']):
                raise ValueError('annual package resource hash/path mismatch')
            package_files.append({'path': path.relative_to(root).as_posix(), 'sha256': row['sha256']})
        parser = _VisibleText(); parser.feed(document_raw.decode('utf-8')); parser.close(); text = parser.text
        env, start, end = _section(text, r'Environmental Matters We are subject to numerous', 'ITEM 9.')
        terms = [_term(env, r'(?:Certain|Some of these) environmental costs are eligible for future recovery in the pricing of our products and services to the U\.S\. Government',
            offset=start, name='recovery_mechanism', value='future_government_contract_pricing_not_surplus_cash', unit='classification', section_name='Environmental Matters')]
        terms.append(_term(env, r'our liability and proportionate share of costs that may be shared among other PRPs have not been determined',
            offset=start, name='unquantified_site_scope', value='some_prp_cost_shares_undetermined', unit='classification', section_name='Environmental Matters'))
        accounting_terms = []
        # A separately disclosed accounting policy is required in the latest source.
        if source == sources[0]:
            accounting, astart, aend = _section(text, r'Environmental Expenditures —', 'EPS —')
            for name, pattern, value in (
                ('capitalized_environmental_expenditures', r'We generally capitalize environmental expenditures that increase the life or efficiency of property or that reduce or prevent environmental contamination', 'capital_expenditures_not_automatic_ocf_addback'),
                ('conditional_discounting_policy', r'When the timing and amount of future cash payments are fixed or reliably determinable, such cash flows are generally discounted in estimating the accrual', 'may_already_include_discounting_not_proof_all_reserves_are_pv'),
                ('accrual_remeasurement', r'Accruals are reviewed at least annually and updated for progress in investigation and remediation efforts and changes in facts or legal circumstances', 'stock_change_not_cash_payment')):
                accounting_terms.append(_term(accounting, pattern, offset=astart,name=name,value=value,unit='classification',section_name='Environmental Expenditures'))
        prefixes = {r['qname'].split(':',1)[0] for r in st['facts'] if re.fullmatch(policy['issuer_namespace_pattern'], str(r.get('namespace','')))}
        balances = {}
        for kind, local in (('reported_liability','AccrualForEnvironmentalLossContingencies'),('recoverable_asset',policy['recovery_local_name'])):
            rows = [r for r in st['facts'] if r.get('local_name') == local and r.get('period_start') is None]
            if not rows: raise ValueError('annual environmental balance missing, not zero')
            for r in rows:
                dims = dict(r.get('dimensions') or [])
                namespace = r'https?://fasb\.org/us-gaap/20\d{2}' if kind == 'reported_liability' else policy['issuer_namespace_pattern']
                if (r.get('unit') != 'USD' or len(dims)!=1
                    or str(dims.get(policy['axis'],'')).rsplit(':',1)[-1] != policy['member_local_name']
                    or str(dims[policy['axis']]).split(':',1)[0] not in prefixes
                    or not re.fullmatch(namespace,str(r.get('namespace','')))
                    or r.get('entity_scheme') != 'http://www.sec.gov/CIK' or str(r.get('entity_identifier','')).zfill(10)!=policy['cik']
                    or r.get('source_accession')!=filing['accession']
                    or 'us-gaap:OtherCommitmentsLineItems' not in r.get('presentation_parents',[])
                    or isinstance(r['value'],bool) or not isinstance(r['value'],(int,float)) or not isfinite(r['value']) or r['value']<0):
                    raise ValueError('annual environmental fact scope invalid')
                key = (kind,r['period_end'])
                if key in balances and balances[key] != r: raise ValueError('annual environmental fact conflict')
                balances[key]=r
        periods = {end for kind,end in balances}
        if filing['report_date'] not in periods: raise ValueError('annual current balances unavailable')
        pairs=[]
        for period in sorted(periods):
            liability=balances.get(('reported_liability',period)); recovery=balances.get(('recoverable_asset',period))
            if not liability or not recovery or liability['context_id']!=recovery['context_id']:
                raise ValueError('annual liability/recovery paired scope mismatch')
            pairs.append({'period_end':period,'reported_liability':liability,'recoverable_asset':recovery,
                          'book_difference_not_pv_or_claim':liability['value']-recovery['value']})
        observations.append({'filing':filing,'related_balances':pairs,'terms':terms,'accounting_terms':accounting_terms,
            'section':{'name':'Environmental Matters','normalized_text_start':start,'normalized_text_end':end},
            'payment_candidates':[r for r in st['facts'] if r.get('local_name') in policy['payment_concepts']],
            'recovery_cash_candidates':[r for r in st['facts'] if r.get('local_name') in policy['recovery_cash_concepts']],
            'reported_environmental_cash_payments':None,'recovery_cash_timing':None,'payment_schedule':None})
        bound_sources.append({**source,'package_manifest_sha256':sha256_bytes(manifest_raw),'structural_sha256':sha256_bytes(raw),
            'document_path':primary.relative_to(root).as_posix(),'document_sha256':sha256_bytes(document_raw),
            'normalized_text_sha256':sha256_bytes(text.encode()),'package_files':package_files})
    if dates != sorted(dates,reverse=True): raise ValueError('annual evidence order must be latest first')
    seen={}; differences=[]
    for obs in observations:
        for pair in obs['related_balances']:
            values=(pair['reported_liability']['value'],pair['recoverable_asset']['value'])
            period=pair['period_end']
            if period in seen and seen[period]!=values: differences.append({'period':period,'observations':[seen[period],values]})
            seen[period]=values
    result={'version':VERSION,'ticker':ticker,'cutoff':cutoff,'sources':bound_sources,'observations':observations,
        'overlapping_period_differences':differences,'status':'annual_balances_and_accounting_policy_verified_cash_overlap_review',
        'forecast_cash_overlap':'unallocated; reported OCF/revenue/capex retained, no addback or reserve adjustment',
        'reported_environmental_cash_payments':None,'cash_recovery_timing':None,'pv_reserve':None,'claim_adjustment':None,
        'numeric_successor_issued':False,'review_reasons':['environmental_payments_and_recovery_timing_not_quantified',
            'reported_accrual_may_include_discounting_no_second_discount','capitalized_costs_and_forecast_cash_overlap_unallocated']}
    result['receipt_sha256']=sha256_bytes(canonical_json_bytes(result))
    return result


def validate_annual_environmental_evidence(receipt, *, source_root, cutoff):
    if receipt.get('version') != VERSION or receipt.get('cutoff') != cutoff:
        raise ValueError('annual environmental version/cutoff mismatch')
    sources=[{key:row[key] for key in ('package_manifest_path','structural_path')} for row in receipt['sources']]
    rebuilt=extract_annual_environmental_evidence(receipt['ticker'],sources,source_root=source_root,cutoff=cutoff)
    if canonical_json_bytes(receipt)!=canonical_json_bytes(rebuilt):raise ValueError('annual environmental source/receipt drift')
    return rebuilt
