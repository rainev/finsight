#!/usr/bin/env python3
"""Exercise real authenticated US routes using an isolated private snapshot.

No DB/storage startup, live catalog pointer, SEC traffic or saved valuations.
The temporary active pointer exists only in the disposable verification sandbox.
This is US router verification, NOT full application or deployment verification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]


def serve(port):
    sys.path.insert(0,str(ROOT/'backend'))
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from app.errors import AppError
    from app.routers.us_valuations import router
    app=FastAPI()
    @app.exception_handler(AppError)
    async def error(request,exc):
        return JSONResponse({'error':exc.message},status_code=exc.status)
    app.include_router(router,prefix='/api')
    uvicorn.run(app,host='127.0.0.1',port=port,log_level='error')


def verify(private, output):
    receipt=json.loads((ROOT/'docs/handoff/us700-receipt.json').read_bytes())
    expected=json.loads((ROOT/'docs/handoff/us700-companies.json').read_bytes())
    assert hashlib.sha256((ROOT/'docs/handoff/us700-companies.json').read_bytes()).hexdigest()==receipt['public_company_list_sha256']
    for relative,pin in receipt['source_copy_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==pin, relative
    catalog=private/'catalogs'/receipt['catalog_version']
    assert hashlib.sha256((catalog/'manifest.json').read_bytes()).hexdigest()==receipt['manifest_sha256']
    manifest=json.loads((catalog/'manifest.json').read_bytes())
    sys.path.insert(0,str(ROOT/'backend'))
    from app.us_valuation.latest_calculator import baseline_version
    env={k:v for k,v in os.environ.items() if not k.startswith(('FINSIGHT_US_','US_REFRESH_'))}
    # Random ephemeral credentials are only for this no-database localhost server.
    env.update(APP_ENV='production',JWT_ACCESS_SECRET=secrets.token_urlsafe(32),JWT_REFRESH_SECRET=secrets.token_urlsafe(32),
        PGHOST='127.0.0.1',PGPORT='1',PGUSER='isolated',PGPASSWORD='unused',PGDATABASE='unused',
        MINIO_ENDPOINT='http://127.0.0.1:1',MINIO_ROOT_USER='unused',MINIO_ROOT_PASSWORD='unused',MINIO_BUCKET='unused',
        PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT/'backend'))
    with tempfile.TemporaryDirectory(prefix='us700-partner-proof-') as temporary:
        temp=Path(temporary);(temp/'snapshot').symlink_to(catalog,target_is_directory=True)
        (temp/'active.json').write_text(json.dumps({'schema_version':'FINSIGHT-US-VALUATION-ACTIVE-1.0',
            'catalog_version':receipt['catalog_version'],'catalog_path':'snapshot','manifest_sha256':receipt['manifest_sha256']}))
        env['FINSIGHT_US_VALUATION_CATALOG_ROOT']=str(temp)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        with (temp/'server.log').open('w') as log:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
            try:
                code="from app.security.jwt import sign_access_token; print(sign_access_token(1,'verification@example.invalid','user'))"
                token=subprocess.check_output([sys.executable,'-c',code],cwd=ROOT,env=env,text=True).strip()
                def request(path='',body=None,authorized=True):
                    headers={'Authorization':'Bearer '+token} if authorized else {}
                    if body is not None:headers['Content-Type']='application/json'
                    req=Request(f'http://127.0.0.1:{port}/api/us-valuations'+path,
                        data=None if body is None else json.dumps(body).encode(),headers=headers)
                    try:
                        with urlopen(req,timeout=120) as response:return response.status,json.load(response)
                    except HTTPError as exc:return exc.code,json.load(exc)
                for _ in range(600):
                    if process.poll() is not None:raise RuntimeError((temp/'server.log').read_text())
                    try:
                        status,listed=request();break
                    except URLError:time.sleep(.1)
                else:raise RuntimeError('isolated US HTTP server startup timed out')
                assert status==200 and listed['count']==listed['artifact_count']==700
                print('HTTP700 list returned; verifying exact values, details and calculators.',flush=True)
                # Display GETs are public in the actual router; calculator POST
                # is the consumer operation protected by CurrentUser.
                assert request('/MMS/calculator',body={},authorized=False)[0]==401
                rows={row['ticker']:row for row in listed['items']};assert len(rows)==700
                for company in expected['companies']:
                    row=rows[company['ticker']]
                    assert row['availability_type']==company['availability_type']
                    assert row['base']==company['scenario_range']['base']
                details={}
                for t in ('MMS','FCN','LSTR','SNX','ICFI','CBT','UTMD','AAPL','AIT'):
                    status,detail=request('/'+t);assert status==200,(t,status,detail)
                    raw=json.loads((catalog/'artifacts'/f'{t}.json').read_bytes())
                    assert detail['scenario_range']==raw['scenario_range'],t
                    details[t]=detail['scenario_range']
                calculators={}
                for t in ('MMS','FCN','AAPL','LSTR','SNX','ICFI','CBT','UTMD'):
                    status,view=request('/'+t+'/calculator');assert status==200,(t,status,view)
                    artifact=json.loads((catalog/'artifacts'/f'{t}.json').read_bytes())
                    # Unavailable calculator GETs omit this field. Use the real
                    # native baseline function, not a made-up version/409 probe.
                    version=view.get('baseline_version') or baseline_version(artifact)
                    status,result=request('/'+t+'/calculator',{'baseline_version':version,
                        'recipe_version':view.get('recipe_version'),'overrides':{},'save':False})
                    if details[t]['base'] is None:assert status==400,(t,status,result)
                    else:
                        assert status==200,(t,status,result)
                        for k in ('low','base','high'):
                            assert abs(result['result'][k]-details[t][k])<=max(1e-9,abs(details[t][k])*1e-12)
                    calculators[t]=status
                for t in ('MMS','FCN'):
                    assert rows[t]['reliability']=='Low'
                    assert rows[t].get('warnings')
                proof={'catalog_count':700,'numeric_count':sum(r['base'] is not None for r in rows.values()),
                    'unavailable_count':sum(r['base'] is None for r in rows.values()),'all700_list_values_and_availability_match':True,
                    'unauthenticated_calculator_POST_HTTP':401,'detail_ranges':details,'calculator_HTTP':calculators,
                    'ordinary_production_catalog_guards':True,'full_app_DB_rate_limit_browser_verification':False,
                    'live_pointer_changed':False,'SEC_job_started':False,'partner_activated':False}
                output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
            finally:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--serve',type=int);p.add_argument('--private-root',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.serve:serve(a.serve)
    else:verify(a.private_root.resolve(),a.output.resolve())
