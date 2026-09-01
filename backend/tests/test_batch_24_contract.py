import hashlib
from importlib.resources import files
from app.us_valuation.batch_24 import BATCH_24_MANIFEST,BATCH_24_TICKERS,BATCH_24_VALUATION_DATE
def test_batch_24_contract():
 assert BATCH_24_VALUATION_DATE=='2026-08-14' and BATCH_24_TICKERS==('NOC','TDG','BLDR','TT','GNRC','HII','XYL','UBER','ETN','ALLE');assert len(BATCH_24_MANIFEST)==10 and len({r.cik for r in BATCH_24_MANIFEST})==10 and sum(r.role=='core' for r in BATCH_24_MANIFEST)==8;assert [(r.ticker,r.role) for r in BATCH_24_MANIFEST if r.role=='boundary']==[('GNRC','boundary'),('UBER','boundary')]
def test_batch_24_hash():
 p=files('app.us_valuation').joinpath('config/reset_batches_2026_08_14/batch_24.json');assert hashlib.sha256(p.read_bytes()).hexdigest()=='5e91acf91a147facfa50ed3fc2691eab4e7e3a3d10a7dc37477a4b4d7cb95dc2'
