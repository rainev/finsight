import hashlib
from importlib.resources import files
from app.us_valuation.batch_23 import BATCH_23_MANIFEST,BATCH_23_TICKERS,BATCH_23_VALUATION_DATE
def test_batch_23_contract():
 assert BATCH_23_VALUATION_DATE=='2026-08-14' and BATCH_23_TICKERS==('AME','CHRW','FDX','PWR','RSG','URI','AXON','LII','UPS','LDOS');assert len(BATCH_23_MANIFEST)==10 and len({r.cik for r in BATCH_23_MANIFEST})==10 and sum(r.role=='core' for r in BATCH_23_MANIFEST)==8;assert [(r.ticker,r.role) for r in BATCH_23_MANIFEST if r.role=='boundary']==[('URI','boundary'),('LDOS','boundary')]
def test_batch_23_hash():
 p=files('app.us_valuation').joinpath('config/reset_batches_2026_08_14/batch_23.json');assert hashlib.sha256(p.read_bytes()).hexdigest()=='ac3a445e1cbfdc1d21a2c089e2eac95bc5fac8a9d9c24fd664e27fc5a5d29209'
