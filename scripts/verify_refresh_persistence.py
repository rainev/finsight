#!/usr/bin/env python3
"""Verify saved valuation SQL on an isolated local PostgreSQL database.

Docker credentials are read into process memory and never printed. No existing
application database is modified. The small test database is retained for review.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
DB_NAME = 'finsight_refresh_uat_20260908'


def configure_database():
    metadata = json.loads(subprocess.check_output(['docker','inspect','valuation-db-1']))[0]
    config = dict(item.split('=',1) for item in metadata['Config']['Env'] if '=' in item)
    port = metadata['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']
    import psycopg
    from psycopg import sql
    connection = {'host':'127.0.0.1','port':port,'user':config['POSTGRES_USER'],'password':config['POSTGRES_PASSWORD']}
    with psycopg.connect(dbname='postgres', autocommit=True, **connection) as admin:
        if not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DB_NAME,)).fetchone():
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB_NAME)))
    for name,value in {'APP_ENV':'test','PGHOST':'127.0.0.1','PGPORT':port,'PGUSER':config['POSTGRES_USER'],'PGPASSWORD':config['POSTGRES_PASSWORD'],
                       'PGDATABASE':DB_NAME,'JWT_ACCESS_SECRET':'isolated-uat-access','JWT_REFRESH_SECRET':'isolated-uat-refresh',
                       'MINIO_ENDPOINT':'http://127.0.0.1:9000','MINIO_ROOT_USER':'unused','MINIO_ROOT_PASSWORD':'unused','MINIO_BUCKET':'unused'}.items():
        os.environ[name]=value
    return connection


def main():
    configure_database()
    from app.db import pool, query_one
    from app.db_migrate import run_migrations
    from app.services import valuation_service
    pool.open()
    try:
        run_migrations()
        user=query_one("INSERT INTO users(email,role,is_verified) VALUES (%s,'user',TRUE) ON CONFLICT(email) DO UPDATE SET is_verified=TRUE RETURNING id",('refresh-uat@example.invalid',))
        row=valuation_service.save_us(user_id=user['id'],ticker='XOM',model='fcff_dcf',model_version='recipe-uat1',
               assumptions={'cash_conversion':1.2},user_price=75.,result={'base':102.24,'low':70.,'high':125.,'recipe_version':'uat1','recipe_hash':'a'*64,'baseline_version':'b'*64})
        retrieved=valuation_service.get(user['id'],row['id'])
        assert retrieved['result']['recipe_version']=='uat1'
        assert retrieved['assumptions']=={'cash_conversion':1.2}
        assert float(retrieved['user_price'])==75.
        assert valuation_service.get(user['id']+999999,row['id']) is None
        assert valuation_service.delete(user['id'],row['id']) is True
        print(json.dumps({'database':DB_NAME,'migrations':'passed','save_readback':'passed','user_scoping':'passed','test_valuation_row_removed':True,'application_database_changed':False}))
    finally:
        pool.close()


if __name__=='__main__':main()
