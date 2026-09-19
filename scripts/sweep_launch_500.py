"""Read-only launch sweep of the approved staged catalog; writes audit receipts only."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from collections import Counter
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
CAT = ROOT/'output/batch-50-api-runtime-a/catalogs/US-RESET-2026-08-14-B01-B50-INITIAL-1.0'
OUT = ROOT/'output/launch-sweep-20260919'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--serve',action='store_true')
    p.add_argument('--http',action='store_true')
    p.add_argument('--recipe-root',type=Path)
    p.add_argument('--output',type=Path,default=OUT)
    p.add_argument('--port',type=int,default=4189)
    a=p.parse_args()
    os.environ['FINSIGHT_US_VALUATION_CATALOG_ROOT']=str(CAT.parent)
    for key,value in {'APP_ENV':'test','JWT_ACCESS_SECRET':'launch-sweep-isolated-local-access','JWT_REFRESH_SECRET':'launch-sweep-isolated-local-refresh','PGHOST':'127.0.0.1','PGPORT':'5432','PGUSER':'unused','PGPASSWORD':'unused','PGDATABASE':'unused','MINIO_ENDPOINT':'http://127.0.0.1:9000','MINIO_ROOT_USER':'unused','MINIO_ROOT_PASSWORD':'unused','MINIO_BUCKET':'unused'}.items():
        os.environ[key]=value
    for key in ('FINSIGHT_US_REFRESH_ROOT','FINSIGHT_US_RECIPE_ROOT','FINSIGHT_US_VALUATION_DATA_ROOT'):
        os.environ.pop(key,None)
    if a.recipe_root:os.environ['FINSIGHT_US_RECIPE_ROOT']=str(a.recipe_root.resolve())
    if a.serve:
        from app.main import app
        import uvicorn
        uvicorn.run(app,host='127.0.0.1',port=a.port,lifespan='off')
        return
    from app.us_valuation.catalog import load_catalog_version
    from app.us_valuation.calculator import calculator_view, calculate
    from app.security.jwt import sign_access_token
    catalog=load_catalog_version(CAT)
    manifest=json.loads((CAT/'manifest.json').read_text())
    token=sign_access_token(7,'launch-sweep-local@example.invalid','user')
    def call(path,body=None):
        req=Request(f'http://127.0.0.1:{a.port}/api'+path,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},data=None if body is None else json.dumps(body).encode())
        try:
            with urlopen(req,timeout=20) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    private={'official_evidence','reported_inputs','governed_assumptions','input_source_ledger','scenario_rows','pipeline_revision_retry'}
    def leaks(x):
        if isinstance(x,dict):return bool(private.intersection(x)) or any(leaks(v) for v in x.values())
        return isinstance(x,list) and any(leaks(v) for v in x)
    targeted={
        'BIIB':'WG40 current debt is 8.0903B versus retained recipe 7.2903B; legal and acquired-cash scope require correction/review.',
        'HON':'WG36/37 completed separation changes the company being valued; continuing-company cash/debt bridge remains unresolved.',
        'INTC':'WG24/25 identify possible cash/AFS overlap and incomplete financing-capital-payment treatment.',
        'JBL':'WG23/25 identify a new-only lease schedule used without full current carrying/overlap reconciliation.',
        'MCK':'WG30–33 payment-only proxy and ownership reconciliation do not establish full cash/legal overlap.',
        'LHX':'WG27–29 preferred/derivative and environmental recovery/forward-cash overlap remain unresolved.'}
    rows=[]
    for entry in manifest['entries']:
        ticker=entry['ticker']; artifact=json.loads(catalog.verify_artifact(ticker).read_text())
        recipe_path=a.recipe_root/f'{ticker}.json' if a.recipe_root else None
        recipe=json.loads(recipe_path.read_bytes()) if recipe_path and recipe_path.is_file() else None
        errors=[]; notes=[]; r=artifact['scenario_range']; numeric=r.get('base') is not None
        if artifact['issuer']['ticker']!=ticker or str(artifact['issuer']['cik']).zfill(10)!=str(entry['cik']).zfill(10):errors.append('identity mismatch')
        vals=[r.get(k) for k in ('low','base','high')]
        if numeric and (not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in vals) or not vals[0]<=vals[1]<=vals[2] or vals[1]<=0):errors.append('invalid numeric range')
        if not numeric and any(v is not None for v in vals):errors.append('partial unavailable range')
        source=artifact.get('source_financial_statement',{})
        cutoff=artifact.get('valuation_date')
        if source.get('filed_date') and source['filed_date']>cutoff:errors.append('filing after evidence cutoff')
        if source.get('period_end') and source.get('filed_date') and source['period_end']>source['filed_date']:errors.append('report period after filing')
        if not (ROOT/entry['source_audit']).is_file():errors.append('source audit missing')
        if leaks(artifact):errors.append('private keys')
        try:
            view=calculator_view(artifact,recipe=recipe)
            parity=not numeric and not view['can_calculate']
            if numeric:
                computed=calculate(artifact,overrides={},manual_price=None,recipe=recipe)
                parity=all(math.isclose(computed['result'][k],r[k],rel_tol=1e-10,abs_tol=1e-8) for k in ('low','base','high'))
            if not parity:errors.append('offline calculator mismatch')
        except Exception as e:errors.append('calculator: '+str(e));parity=False
        http=None
        if a.http:
            status,detail=call('/us-valuations/'+ticker)
            vs,v=call('/us-valuations/'+ticker+'/calculator')
            cs,c=call('/us-valuations/'+ticker+'/calculator',{'overrides':{},'save':False,
                'baseline_version':v.get('baseline_version'),'recipe_version':v.get('recipe_version')})
            hp=status==200 and vs==200 and detail.get('scenario_range')==r and detail.get('availability_type')==artifact.get('availability_type') and not leaks(detail)
            cp=(cs==400 and not numeric) or (cs==200 and numeric and all(math.isclose(c['result'][k],r[k],rel_tol=1e-10,abs_tol=1e-8) for k in ('low','base','high')))
            http={'detail':hp,'calculator':cp,'post_status':cs}
            if not hp or not cp:errors.append('HTTP parity failure')
        if artifact.get('model_policy',{}).get('primary')=='conditional_estimate':notes.append('primary label describes availability; expose actual calculator model')
        if numeric and (r['high']-r['low'])/r['base']>1.25:notes.append('wide range; approved uncertainty disclosure required')
        if ticker in ('GILD','INCY'):notes.append('retain approved baseline; WG39 replacement normalization requires review')
        if ticker in targeted:notes.append(targeted[ticker])
        classification=('targeted_review' if numeric and (errors or ticker in targeted) else 'unavailable' if not numeric else 'publishable_with_disclosure' if artifact.get('availability_type')=='conditional_estimate' or notes else 'publishable_baseline')
        rows.append({'ticker':ticker,'cik':entry['cik'],'batch':entry['batch'],'classification':classification,'availability':artifact.get('availability_type'),'range':r,'reliability':artifact.get('reliability',{}).get('label'),'source':source,'cutoff':cutoff,'artifact_sha256':entry['artifact_sha256'],'source_audit':entry['source_audit'],'offline_parity':parity,'http':http,'errors':errors,'notes':notes,'existing_warnings':artifact.get('review',{}).get('warnings',[])})
    assert len(rows)==500 and len({x['ticker'] for x in rows})==500 and len({x['cik'] for x in rows})==500
    assert Counter(x['batch'] for x in rows)==Counter({i:10 for i in range(1,51)})
    listing=call('/us-valuations')[1] if a.http else None
    report={'scope':'approved dated baseline publication screening; no fresh SEC acquisition or deployment','catalog':str(CAT),'manifest_sha256':hashlib.sha256((CAT/'manifest.json').read_bytes()).hexdigest(),'count':500,'counts':dict(Counter(x['classification'] for x in rows)),'errors':sum(bool(x['errors']) for x in rows),'http_list_count':listing.get('count') if listing else None,'rows':rows}
    out=a.output;out.mkdir(parents=True,exist_ok=True)
    name='http-sweep' if a.http else 'offline-sweep'
    (out/(name+'.json')).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    (out/(name+'.md')).write_text('# 500-company launch sweep\n\n'+json.dumps(report['counts'])+'\n\n| Company | Disposition | Low / Base / High | Notes |\n|---|---|---|---|\n'+'\n'.join('| '+x['ticker']+' | '+x['classification']+' | '+' / '.join(str(x['range'].get(k)) for k in ('low','base','high'))+' | '+'; '.join(x['errors']+x['notes']).replace('|','/')+' |' for x in rows)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
