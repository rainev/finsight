#!/usr/bin/env python3
"""Exercise one immutable 500-company candidate in an isolated real API runtime."""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.us_valuation.catalog import canonical_json_bytes,load_catalog_version
from app.us_valuation.refresh_catalog_store import RefreshCatalogStore,load_frozen_registry

def call(port,path,body=None,token=None):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    with urlopen(Request(f'http://127.0.0.1:{port}/api'+path,headers=headers,
        data=None if body is None else json.dumps(body).encode()),timeout=30) as response:return json.load(response)

def worker(root,port):
    from verify_refresh_persistence import configure_database
    configure_database();os.environ['FINSIGHT_US_REFRESH_ROOT']=str(root)
    os.environ.setdefault('CLIENT_URL','http://localhost:4178')
    from app.main import app
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=port)

def run(runtime,candidate,port):
    runtime=runtime.resolve();candidate=candidate.resolve()
    catalog=load_catalog_version(candidate);registry=load_frozen_registry(runtime/'registry.json',expected_count=500)
    if len(catalog.entries)!=500 or catalog.manifest.get('private_recipe_sha256') is None:raise ValueError('candidate is not an exact 500-company recipe catalog')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root=ROOT/'output'/f'latest-500-candidate-uat-{stamp}-{uuid.uuid4().hex[:8]}'
    root.mkdir();shutil.copy2(runtime/'registry.json',root/'registry.json');shutil.copytree(runtime/'baseline',root/'baseline')
    (root/'uat-fixture.json').write_bytes(canonical_json_bytes({'scope':'isolated latest candidate UAT','candidate':str(candidate),'production':False}))
    store=RefreshCatalogStore(root/'catalogs',frozen_registry=root/'registry.json',expected_registry_count=500)
    store.runtime_root.mkdir()
    policy='latest-candidate-uat-policy'
    from app.us_valuation.catalog import sha256_bytes
    fingerprint=sha256_bytes(policy.encode())
    store.approved_policy_path.write_bytes(canonical_json_bytes({'approved':True,'status':'approved','policy_fingerprint':fingerprint,
        'registry_sha256':registry.registry_sha256,'scope':'isolated latest candidate UAT'}))
    predecessor=store.stage_catalog(runtime/'baseline')
    first=store.activate(predecessor,policy_fingerprint=fingerprint,activated_at=datetime.now(timezone.utc).isoformat(),reason='isolated predecessor')
    reader=store.reader();pinned=reader.get_snapshot()
    successor=store.stage_catalog(candidate)
    second=store.activate(successor,policy_fingerprint=fingerprint,activated_at=datetime.now(timezone.utc).isoformat(),
        expected_active_manifest_sha256=first['pointer']['manifest_sha256'],reason='isolated latest successor')
    reloaded=reader.get_snapshot()
    if pinned.catalog_version!=predecessor.catalog_version or reloaded.catalog_version!=successor.catalog_version:raise AssertionError('reader pin/reload failed')
    log=(root/'api.log').open('wb')
    process=subprocess.Popen([sys.executable,__file__,'--worker-root',str(root),'--port',str(port)],stdout=log,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+45
        while True:
            if process.poll() is not None:raise RuntimeError('isolated API exited')
            try: auth=call(port,'/auth/login',{'email':'refresh-uat@example.com','password':'Local-UAT-only-20260908!'});break
            except OSError:
                if time.monotonic()>deadline:raise
                time.sleep(.2)
        token=auth['access_token'];listed=call(port,'/us-valuations',token=token)
        if listed['count']!=500:raise AssertionError('isolated candidate list count differs')
        rows=[]
        report=json.loads((candidate/'assembly-report.json').read_bytes())
        promoted=[row['ticker'] for row in report['rows'] if row['outcome']=='source_bound']
        for ticker in promoted:
            detail=call(port,f'/us-valuations/{ticker}',token=token);view=call(port,f'/us-valuations/{ticker}/calculator',token=token)
            calculated=call(port,f'/us-valuations/{ticker}/calculator',{'overrides':{},'baseline_version':view['baseline_version'],'recipe_version':view['recipe_version']},token=token)
            expected=detail['scenario_range']
            if any(calculated['result'][key]!=expected[key] for key in ('low','base','high')):raise AssertionError(ticker+' calculator parity failed')
            rows.append({'ticker':ticker,'range':{key:expected[key] for key in ('low','base','high')},'catalog_version':detail['catalog_version'],'calculator_parity':True})
        rollback=store.rollback(second['receipt_path'],rolled_back_at=datetime.now(timezone.utc).isoformat(),reason='isolated latest candidate rollback')
        after=reader.get_snapshot()
        if after.catalog_version!=predecessor.catalog_version:raise AssertionError('reader rollback reload failed')
        rollback_detail=call(port,'/us-valuations/BBY',token=token)
        if rollback_detail['catalog_version']!=predecessor.catalog_version:raise AssertionError('worker rollback reload failed')
        result={'status':'verified','scope':'isolated real API; production untouched','runtime_root':str(root),'candidate':str(candidate),
            'registry_count':500,'promoted':rows,'reader_pin_reload':True,'worker_reload':True,'rollback':True,
            'activation_receipt':str(second['receipt_path']),'rollback_receipt':str(rollback['receipt_path']),'production_runtime_touched':False}
        (root/'verification.json').write_bytes(canonical_json_bytes(result));return result
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path);p.add_argument('--candidate',type=Path)
    p.add_argument('--port',type=int,default=4193);p.add_argument('--worker-root',type=Path)
    a=p.parse_args()
    if a.worker_root:worker(a.worker_root.resolve(),a.port);return
    if not a.runtime_root or not a.candidate:p.error('runtime and candidate required')
    print(json.dumps(run(a.runtime_root,a.candidate,a.port),sort_keys=True))
if __name__=='__main__':main()
