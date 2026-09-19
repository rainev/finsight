#!/usr/bin/env python3
"""Narrow real-source ownership proof and legacy replay; no numeric successor."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from verify_us_refresh_sources import indexed_paths,_packet,implementation_fingerprint
from app.us_valuation.refresh_reported_claim_scope import REPORTED_NCI_SCOPE_RULES,reported_nci_field_availability
from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.catalog import canonical_json_bytes,sha256_bytes
from app.us_valuation.refresh_job import atomic

def proof(root,index):
    registry=json.loads((root/'registry.json').read_bytes());policies=json.loads((root/'refresh-policies.json').read_bytes())
    paths,structures,indexed=indexed_paths(ROOT/'output',registry,index,['LHX','MCK']);rows=[]
    for ticker in ('LHX','MCK'):
        entry=next(r for r in registry['entries'] if r['ticker']==ticker)
        recipe=json.loads((root/'recipes'/f'{ticker}.json').read_bytes())
        packet,provenance=_packet(entry,recipe,paths,structures,root/'source-validation-cache',recipe['evidence_cutoff'],indexed)
        st=packet['structural_filing'];rule=asdict(REPORTED_NCI_SCOPE_RULES[ticker])
        _,ownership=reported_nci_field_availability(ticker=ticker,policy=rule,structural_packet=st,
            accession=st['source_accession'],period_end=st['report_date'])
        # Classification arithmetic only: preserve EVERY legacy deduction.
        # The residual is not certified as the correct current legal/event claim.
        reconstructed=deepcopy(recipe);remaining={}
        for name,spec in reconstructed['scenarios'].items():
            fields=spec['inputs'];remaining[name]=fields['preferred_equity']+fields['noncontrolling_interests']-ownership['source_total']
            fields.update(preferred_equity=0.,noncontrolling_interests=ownership['source_total'],
                nonoperating_adjustment=fields['nonoperating_adjustment']-remaining[name])
        previous=evaluate_recipe(recipe)['range'];replayed=evaluate_recipe(reconstructed)['range']
        rows.append({'ticker':ticker,'source_ownership_proof':ownership,'source_capture':provenance,
            'legacy_remaining_deduction_not_current_validated_claim':remaining,
            'previous_range':previous,'classification_replay_range':replayed,
            'numeric_successor_issued':False,'official_value_changes':{'low':0.,'base':0.,'high':0.}})
    return {'scope':'ownership source binding and value-neutral legacy classification only; full stacks remain implementation gaps',
        'implementation_sha256':implementation_fingerprint(),'policy_sha256':sha256_bytes(canonical_json_bytes(policies)),
        'rows':rows,'numeric_successor_issued':False}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-index',type=Path,required=True)
    p.add_argument('--runtime-root',type=Path,default=ROOT/'output/us-refresh-runtime');args=p.parse_args()
    result=proof(args.runtime_root,args.source_index);path=args.runtime_root/'wg26-redeemable-ownership-source-proof.json'
    atomic(path,canonical_json_bytes(result),immutable=False)
    print(json.dumps({'proof_path':str(path),'rows':[{k:v for k,v in r.items() if k not in {'source_capture','source_ownership_proof'}} for r in result['rows']]},sort_keys=True))
