#!/usr/bin/env python3
"""Compile data-only refresh policies outside source; no activation or approval."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from app.us_valuation.refresh_job import atomic, writer, policy_readiness
from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes, load_catalog_version
from app.us_valuation.refresh_operating_policies import _policy_for_entry
from app.us_valuation.newrefresh_family_policies import compile_residual_income_policy
from app.us_valuation.refresh_special_policies import compile_special_refresh_policy
from app.us_valuation.refresh_schedule_policies import compile_cash_schedule_policy
from app.us_valuation.refresh_earnings_policies import compile_earnings_refresh_policy, SUPPORTED_TICKERS as EARNINGS_TICKERS
from app.us_valuation.refresh_runway_policy import compile_mrna_runway_policy
from app.us_valuation.refresh_cyclical_policy import compile_cyclical_policy
from app.us_valuation.xbrl import load_concept_config


def compile_policies(root: Path) -> dict:
    with writer(root):
        registry = json.loads((root/'registry.json').read_text())
        baseline = load_catalog_version(root/'baseline')
        if baseline.manifest_sha256 != registry['baseline_manifest_sha256']:
            raise ValueError('frozen baseline mismatch')
        policies, report = {}, []
        # The concept map is immutable for one compilation. Reusing one
        # validated copy avoids hundreds of identical file reads; individual
        # compilers deep-copy any issuer-specific changes before mutation.
        concept_config = load_concept_config()
        for entry in registry['entries']:
            ticker = entry['ticker']
            path = root/'recipes'/f'{ticker}.json'
            if not path.is_file():
                report.append({'ticker':ticker,'status':'prior_unavailable','reason':'No numeric baseline recipe; recovery is separate.'})
                continue
            recipe = json.loads(path.read_text())
            engines = {spec['engine'] for spec in recipe['scenarios'].values()}
            if ticker == 'WDC':
                policy = compile_cyclical_policy(recipe,entry)
            elif ticker == 'MRNA':
                policy = compile_mrna_runway_policy(recipe,entry)
            elif ticker in {'AAPL','MSFT'}:
                policy = compile_cash_schedule_policy(recipe,entry)
            elif ticker == 'APTV':
                policy = compile_special_refresh_policy(recipe,entry)
            elif ticker in EARNINGS_TICKERS:
                policy = compile_earnings_refresh_policy(recipe,entry)
            elif engines == {'residual_income'}:
                policy = compile_residual_income_policy(recipe, entry)
            elif engines in ({'enterprise_cash_fcff'}, {'constant_growth_fcff'}):
                artifact = json.loads(baseline.verify_artifact(ticker).read_text())
                compiled = _policy_for_entry(entry,artifact=artifact,recipe=recipe,source_evidence=None,concept_config=concept_config)
                policy = compiled.policy
                policy['reason_codes'] = list(compiled.reason_codes)
                if any(spec.get('equity_overlay') for spec in recipe['scenarios'].values()):
                    policy['reason_codes'].append('event_overlay_refresh_rule_required')
            else:
                report.append({'ticker':ticker,'status':'implementation_required','reason':f'Family adapter required: {sorted(engines)}'})
                continue
            policies[ticker] = policy
            ready, reason = policy_readiness(recipe, policy)
            report.append({'ticker':ticker,'status':'contract_compiled' if ready else 'implementation_required','reason':reason,
                           'source_validation':'must_run_before_activation'})
        payload = canonical_json_bytes(policies)
        digest = sha256_bytes(payload)
        atomic(root/'policy-history'/f'{digest}.json',payload)
        atomic(root/'refresh-policies.json',payload,immutable=False)
        receipt = {'policy_sha256':digest,'rows':report,'contract_compiled':sum(r['status']=='contract_compiled' for r in report),
                   'source_validated':False,'activated':False}
        atomic(root/'policy-compilation-report.json',canonical_json_bytes(receipt),immutable=False)
        return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,default=ROOT/'output/us-refresh-runtime')
    args=parser.parse_args()
    report=compile_policies(args.runtime_root)
    print(json.dumps({key:value for key,value in report.items() if key!='rows'},sort_keys=True))
