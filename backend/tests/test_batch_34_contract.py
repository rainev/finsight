import json

from app.us_valuation.batch_34 import BATCH_34_MANIFEST, BATCH_34_TICKERS, BATCH_34_VALUATION_DATE


def test_batch_34_is_frozen_ten_company_contract():
    assert BATCH_34_TICKERS == ("USB", "L", "SPGI", "NTRS", "BRO", "PGR", "TRV", "KEY", "TFC", "STT")
    assert len(BATCH_34_MANIFEST) == 10
    assert len({issuer.cik for issuer in BATCH_34_MANIFEST}) == 10
    assert all(issuer.partition_family_id == "financial_equity" for issuer in BATCH_34_MANIFEST)
    assert BATCH_34_VALUATION_DATE == "2026-08-14"
