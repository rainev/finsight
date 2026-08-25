from app.us_valuation.batch_05 import BATCH_05_MANIFEST,BATCH_05_TICKERS,BATCH_05_VALUATION_DATE
def test_batch_05_exact_contract():
 assert BATCH_05_VALUATION_DATE=='2026-08-14';assert tuple(r.ticker for r in BATCH_05_MANIFEST)==BATCH_05_TICKERS;assert len({r.cik for r in BATCH_05_MANIFEST})==10;assert tuple(r.ticker for r in BATCH_05_MANIFEST if r.role=='boundary')==('WSM','CASY')
