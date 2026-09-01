import hashlib
from importlib.resources import files
from app.us_valuation.batch_25 import BATCH_25_MANIFEST,BATCH_25_TICKERS,BATCH_25_VALUATION_DATE
def test_batch_25_contract():
 assert BATCH_25_VALUATION_DATE=='2026-08-14' and BATCH_25_TICKERS==('FTV','DD','IR','OTIS','CARR','VLTO','GEV','FERG','FDXF','HONA');assert len(BATCH_25_MANIFEST)==10 and len({r.cik for r in BATCH_25_MANIFEST})==10 and sum(r.role=='core' for r in BATCH_25_MANIFEST)==8;assert [(r.ticker,r.role) for r in BATCH_25_MANIFEST if r.role=='boundary']==[('GEV','boundary'),('FDXF','boundary')]
def test_batch_25_hash():
 p=files('app.us_valuation').joinpath('config/reset_batches_2026_08_14/batch_25.json');assert hashlib.sha256(p.read_bytes()).hexdigest()=='747d46a64f74129ff544ded7d23f89d1720a7b4bb679ff44ce65f4f4bf59d99d'
