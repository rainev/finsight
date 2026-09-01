import hashlib
from importlib.resources import files
from app.us_valuation.batch_26 import BATCH_26_MANIFEST,BATCH_26_TICKERS,BATCH_26_VALUATION_DATE
def test_batch_26_contract():
 assert BATCH_26_VALUATION_DATE=='2026-08-14' and BATCH_26_TICKERS==('AMD','SWKS','ADI','AMAT','GLW','HPQ','INTC','IBM','MSI','APH');assert len(BATCH_26_MANIFEST)==10 and len({r.cik for r in BATCH_26_MANIFEST})==10 and sum(r.role=='core' for r in BATCH_26_MANIFEST)==8;assert [(r.ticker,r.role) for r in BATCH_26_MANIFEST if r.role=='boundary']==[('GLW','boundary'),('APH','boundary')];assert all(r.partition_family_id=='operating_fcff' for r in BATCH_26_MANIFEST)
def test_batch_26_hash():
 p=files('app.us_valuation').joinpath('config/reset_batches_2026_08_14/batch_26.json');assert hashlib.sha256(p.read_bytes()).hexdigest()=='0c767cc411938e49e1e2d731470c158c76de6e16ff0cd8c518293c482651964a'
