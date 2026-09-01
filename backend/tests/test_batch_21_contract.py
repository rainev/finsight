import hashlib
from importlib.resources import files
from app.us_valuation.batch_21 import BATCH_21_MANIFEST,BATCH_21_TICKERS,BATCH_21_VALUATION_DATE
def test_batch_21_contract_is_exact_and_frozen():
 assert BATCH_21_VALUATION_DATE=="2026-08-14" and BATCH_21_TICKERS==("RTX","EME","LHX","TXT","GWW","CSX","NSC","JBHT","EXPD","FAST")
 assert len(BATCH_21_MANIFEST)==10 and len({r.cik for r in BATCH_21_MANIFEST})==10 and sum(r.role=="core" for r in BATCH_21_MANIFEST)==8
 assert [(r.ticker,r.role) for r in BATCH_21_MANIFEST if r.role=="boundary"]==[("JBHT","boundary"),("FAST","boundary")]
 assert all(r.partition_family_id=="operating_fcff" for r in BATCH_21_MANIFEST)
def test_batch_21_manifest_hash_matches_partition_receipt():
 path=files("app.us_valuation").joinpath("config/reset_batches_2026_08_14/batch_21.json");assert hashlib.sha256(path.read_bytes()).hexdigest()=="b4cd7b3c64c5de53dce64017108a2cdfe12faf63865044088d89df231b9a3a5b"
