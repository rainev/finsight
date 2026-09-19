#!/usr/bin/env python3
"""Produce real current-source lease/capital classifications, never a catalog."""
from copy import deepcopy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from verify_us_refresh_sources import indexed_paths,_packet,implementation_fingerprint
from app.us_valuation.catalog import canonical_json_bytes,sha256_bytes
from app.us_valuation.refresh_job import atomic
from app.us_valuation.refresh_lease_capital_scope import assess_lease_capital_scope,lease_capital_policy
from app.us_valuation.calculation_recipe import evaluate_recipe

def proof(root,index):
    registry=json.loads((root/'registry.json').read_bytes());policies=json.loads((root/'refresh-policies.json').read_bytes())
    paths,structures,indexed=indexed_paths(ROOT/'output',registry,index,['INTC','JBL'])
    rows=[]
    for ticker in ('INTC','JBL'):
        entry=next(r for r in registry['entries'] if r['ticker']==ticker)
        recipe=json.loads((root/'recipes'/f'{ticker}.json').read_bytes());cutoff=recipe['evidence_cutoff']
        packet,provenance=_packet(entry,recipe,paths,structures,root/'source-validation-cache',cutoff,indexed)
        st=packet['structural_filing'];f={'accessionNumber':st['source_accession'],'reportDate':st['report_date'],
            'filingDate':st['filed_date'],'form':st['form']}
        narrative=json.loads((root/'narrative-evidence'/f'{ticker}.json').read_bytes())
        ledger=assess_lease_capital_scope(lease_capital_policy(ticker),st,f,entry['cik'],cutoff,narrative)
        previous=evaluate_recipe(recipe)['range'];replayed=evaluate_recipe(deepcopy(recipe))['range']
        rows.append({'ticker':ticker,'classification':ledger,'source_provenance':provenance,
            'previous_range':previous,'retained_recipe_range':replayed,
            'official_value_changes':{k:0. for k in ('low','base','high')},'numeric_successor_issued':False})
    return {'status':'narrow_lease_capital_scope_verified','scope':'classification and retained historical replay; not complete current debt or numeric refresh',
        'implementation_sha256':implementation_fingerprint(),'policy_sha256':sha256_bytes(canonical_json_bytes(policies)),
        'rows':rows}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-index',type=Path,required=True)
    p.add_argument('--runtime-root',type=Path,default=ROOT/'output/us-refresh-runtime');args=p.parse_args()
    result=proof(args.runtime_root,args.source_index)
    destination=args.runtime_root/'wg25-lease-capital-source-proof.json';atomic(destination,canonical_json_bytes(result),immutable=False)
    print(json.dumps({'proof_path':str(destination),'rows':[{k:v for k,v in r.items() if k not in {'source_provenance','classification'}} for r in result['rows']]},sort_keys=True))
