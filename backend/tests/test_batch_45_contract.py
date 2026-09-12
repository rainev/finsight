from app.us_valuation.batch_45 import BATCH_45_MANIFEST,BATCH_45_TICKERS,BATCH_45_VALUATION_DATE
def test_batch_45_manifest_is_exact_and_frozen():
    assert BATCH_45_VALUATION_DATE=="2026-08-14"; assert BATCH_45_TICKERS==("AEP","ETR","ES","XEL","SO","LNT","D","PNW","WEC","PEG"); assert len(BATCH_45_MANIFEST)==10; assert len({r.cik for r in BATCH_45_MANIFEST})==10; assert sum(r.role=="core" for r in BATCH_45_MANIFEST)==8; assert sum(r.role=="boundary" for r in BATCH_45_MANIFEST)==2; assert {r.partition_family_id for r in BATCH_45_MANIFEST}=={"utility_fcfe"}
