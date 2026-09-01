import hashlib
from importlib.resources import files
from app.us_valuation.batch_18 import BATCH_18_MANIFEST,BATCH_18_TICKERS,BATCH_18_VALUATION_DATE

def test_batch_18_contract_is_exact_and_frozen():
 assert BATCH_18_VALUATION_DATE=="2026-08-14"
 assert BATCH_18_TICKERS==("HWM","ADP","BA","CAT","CMI","DAL","DOV","EMR","EFX","GD")
 assert len(BATCH_18_MANIFEST)==10 and len({r.cik for r in BATCH_18_MANIFEST})==10
 assert sum(r.role=="core" for r in BATCH_18_MANIFEST)==8
 assert [(r.ticker,r.role) for r in BATCH_18_MANIFEST if r.role=="boundary"]==[("ADP","boundary"),("EFX","boundary")]
 assert all(r.partition_family_id=="operating_fcff" for r in BATCH_18_MANIFEST)

def test_batch_18_manifest_hash_matches_partition_receipt():
 path=files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_18.json")
 assert hashlib.sha256(path.read_bytes()).hexdigest()=="c2574b73d31c4581d84087b6f4ee5d624831adc9daf59a3fb26b5fb07b413a38"
