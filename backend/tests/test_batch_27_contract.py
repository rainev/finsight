import hashlib
from importlib.resources import files
from app.us_valuation.batch_27 import BATCH_27_MANIFEST,BATCH_27_TICKERS,BATCH_27_VALUATION_DATE
def test_batch_27_contract():
 assert BATCH_27_VALUATION_DATE=='2026-08-14' and BATCH_27_TICKERS==('TER','TXN','KLAC','LRCX','MU','IT','ADSK','ADBE','COHR','FLEX');assert len(BATCH_27_MANIFEST)==10 and len({r.cik for r in BATCH_27_MANIFEST})==10 and sum(r.role=='core' for r in BATCH_27_MANIFEST)==8;assert [(r.ticker,r.role) for r in BATCH_27_MANIFEST if r.role=='boundary']==[('COHR','boundary'),('FLEX','boundary')];assert all(r.partition_family_id=='operating_fcff' for r in BATCH_27_MANIFEST)
def test_batch_27_hash():
 p=files('app.us_valuation').joinpath('config/reset_batches_2026_08_14/batch_27.json');assert hashlib.sha256(p.read_bytes()).hexdigest()=='89c54b31e9a24afe2166164bebe39bf3bfae254413c50eb59eabdb79574c2974'
