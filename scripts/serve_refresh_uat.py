#!/usr/bin/env python3
"""Serve the staged local UI acceptance API on an isolated test database.

No dependency overrides, production credentials, activation, or SEC retrieval.
The disposable login below is only for this localhost test database.
"""
import os
from pathlib import Path
import sys
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from verify_refresh_persistence import configure_database


if __name__ == '__main__':
    configure_database()
    os.environ['CLIENT_URL'] = 'http://localhost:4178'
    from app.us_valuation.catalog import load_catalog_version, canonical_json_bytes, ACTIVE_SCHEMA
    from app.us_valuation.refresh_job import atomic
    baseline = load_catalog_version(ROOT / 'output/us-refresh-runtime/baseline')
    preview = ROOT / 'output/us-refresh-uat-catalogs'
    destination = preview / baseline.catalog_version
    if not destination.exists(): shutil.copytree(baseline.root, destination)
    copied = load_catalog_version(destination, expected_manifest_sha256=baseline.manifest_sha256)
    atomic(preview / 'active.json', canonical_json_bytes({'schema_version': ACTIVE_SCHEMA,
           'catalog_version': copied.catalog_version, 'catalog_path': copied.catalog_version,
           'manifest_sha256': copied.manifest_sha256}), immutable=False)
    os.environ['FINSIGHT_US_VALUATION_CATALOG_ROOT'] = str(preview)
    os.environ['FINSIGHT_US_RECIPE_ROOT'] = str(ROOT / 'output/us-refresh-runtime/recipes')
    # Deliberately do not set FINSIGHT_US_REFRESH_ROOT: no staged activation.
    from app.db import pool, query_one
    from app.db_migrate import run_migrations
    from app.security.password import hash_password
    from app.main import app
    import uvicorn
    pool.open()
    try:
        run_migrations()
        query_one("INSERT INTO users(email,password_hash,role,is_verified) VALUES (%s,%s,'user',TRUE) ON CONFLICT(email) DO UPDATE SET password_hash=EXCLUDED.password_hash RETURNING id",
                  ('refresh-uat@example.com', hash_password('Local-UAT-only-20260908!')))
        uvicorn.run(app, host='127.0.0.1', port=4179, lifespan='off')
    finally:
        pool.close()
