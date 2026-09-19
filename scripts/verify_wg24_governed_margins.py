#!/usr/bin/env python3
"""Narrow real-source governed-margin proof; never publishes a successor."""
import json
from pathlib import Path
import sys
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from verify_us_refresh_sources import indexed_paths, _packet, implementation_fingerprint
from app.us_valuation.xbrl import CompanyFactsNormalizer
from app.us_valuation.refresh_financials import cash_history
from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_job import atomic
from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes

def proof(root, index):
    registry=json.loads((root/'registry.json').read_bytes())
    entry=next(r for r in registry['entries'] if r['ticker']=='INTC')
    recipe=json.loads((root/'recipes/INTC.json').read_bytes())
    policies=json.loads((root/'refresh-policies.json').read_bytes())
    policy=policies['INTC']
    cutoff=registry.get('evidence_cutoff') or recipe['evidence_cutoff']
    paths,structures,indexed=indexed_paths(ROOT/'output',registry,index,['INTC'])
    packet,provenance=_packet(entry,recipe,paths,structures,root/'parsed-source-cache',cutoff,indexed)
    st=packet['structural_filing']
    recent=packet['submissions']['filings']['recent']
    records=[{key:vals[i] for key,vals in recent.items() if isinstance(vals,list) and i<len(vals)}
             for i in range(len(recent['accessionNumber']))]
    rule=next(r for r in policy['inputs'].values() if r['field']=='governed_cash_conversion_margin')
    normalizer=CompanyFactsNormalizer(packet['companyfacts'],concept_config=policy['concept_config'],
        fiscal_year_end=packet['submissions'].get('fiscalYearEnd'),as_of_date=cutoff,
        filing_records=records)
    history=cash_history(normalizer,period=st['report_date'],cutoff=cutoff,rule=rule,structural_packet=st)
    reconstructed=deepcopy(recipe)
    for case,stat in (('bear','low'),('base','base'),('bull','high')):
        reconstructed['scenarios'][case]['inputs']['cash_fcff']=history['reported']['revenue']*history['governed_cash_conversion_margin'][stat]
    return {'status':'narrow_governed_margin_proof','numeric_successor_issued':False,
        'scope':'margin migration and exact historical replay only; unreconciled bridge remains retained, not validated',
        'implementation_sha256':implementation_fingerprint(),'policy_sha256':sha256_bytes(canonical_json_bytes(policies)),
        'source_provenance':provenance,'normalization':history,
        'reconstructed_starting_cash':{c:s['inputs']['cash_fcff'] for c,s in reconstructed['scenarios'].items()},
        'previous_range':evaluate_recipe(recipe)['range'],'narrow_replayed_range':evaluate_recipe(reconstructed)['range'],
        'official_value_changes':{'low':0.,'base':0.,'high':0.}}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-index',type=Path,required=True)
    p.add_argument('--runtime-root',type=Path,default=ROOT/'output/us-refresh-runtime')
    args=p.parse_args()
    result=proof(args.runtime_root,args.source_index)
    destination=args.runtime_root/'wg24-governed-margin-source-proof.json'
    atomic(destination,canonical_json_bytes(result),immutable=False)
    print(json.dumps({'proof_path':str(destination),'validity':result['normalization']['governed_validity'],
        'previous_range':result['previous_range'],'narrow_replayed_range':result['narrow_replayed_range']},sort_keys=True))
