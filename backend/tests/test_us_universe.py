"""Frozen replacement-universe contracts."""

from app.us_valuation.batch_01 import BATCH_01_MANIFEST
from app.us_valuation.universe import load_universe


def test_universe_is_exactly_500_unique_cutoff_issuers() -> None:
    records = load_universe()
    assert len(records) == len({row.cik for row in records}) == 500
    assert len({row.ticker for row in records}) == 500
    assert records == tuple(sorted(records, key=lambda row: row.cik))
    assert "AVB" in {row.ticker for row in records}
    assert "RDDT" not in {row.ticker for row in records}


def test_universe_contains_locked_batch_01_by_cik() -> None:
    by_cik = {row.cik: row for row in load_universe()}
    assert all(
        issuer.cik in by_cik and by_cik[issuer.cik].ticker == issuer.ticker
        for issuer in BATCH_01_MANIFEST
    )


def test_multi_class_issuers_use_explicit_class_a_policy() -> None:
    multi = {
        row.cik: (row.ticker, row.all_index_tickers, row.share_class_policy)
        for row in load_universe()
        if len(row.all_index_tickers) > 1
    }
    assert multi == {
        "0001564708": ("NWSA", ("NWS", "NWSA"), "explicit_class_a_primary"),
        "0001652044": ("GOOGL", ("GOOG", "GOOGL"), "explicit_class_a_primary"),
        "0001754301": ("FOXA", ("FOX", "FOXA"), "explicit_class_a_primary"),
    }
