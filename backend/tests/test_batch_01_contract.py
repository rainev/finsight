"""Contract tests for the controlled Batch 01 issuer manifest."""

from dataclasses import FrozenInstanceError

import pytest

from app.us_valuation.batch_01 import (
    BATCH_01_MANIFEST,
    BATCH_01_TICKERS,
    BATCH_01_VALUATION_DATE,
    issuer_for_ticker,
)


def test_batch_01_manifest_is_exact_ordered_and_immutable() -> None:
    assert BATCH_01_VALUATION_DATE == "2026-08-14"
    assert tuple(
        (
            issuer.ticker,
            issuer.cik,
            issuer.issuer_name,
            issuer.lane_hypothesis,
            issuer.filing_regime,
            issuer.accounting_standard,
        )
        for issuer in BATCH_01_MANIFEST
    ) == (
        ("AAPL", "0000320193", "Apple Inc.", "mature_operating_fcff", "10-K_10-Q", "US-GAAP"),
        ("MSFT", "0000789019", "Microsoft Corporation", "intangible_investment_fcff", "10-K_10-Q", "US-GAAP"),
        ("CRM", "0001108524", "Salesforce, Inc.", "intangible_investment_fcff", "10-K_10-Q", "US-GAAP"),
        ("ANET", "0001596532", "Arista Networks, Inc.", "growth_operating_fcff", "10-K_10-Q", "US-GAAP"),
        ("WDC", "0000106040", "Western Digital Corporation", "normalized_cyclical_fcff", "10-K_10-Q", "US-GAAP"),
        ("DELL", "0001571996", "Dell Technologies Inc.", "captive_finance_sotp", "10-K_10-Q", "US-GAAP"),
        ("JPM", "0000019617", "JPMorgan Chase & Co.", "bank_residual_income", "10-K_10-Q", "US-GAAP"),
        ("BAC", "0000070858", "Bank of America Corporation", "bank_residual_income", "10-K_10-Q", "US-GAAP"),
        ("NEE", "0000753308", "NextEra Energy, Inc.", "mixed_utility_sotp", "10-K_10-Q", "US-GAAP"),
        ("O", "0000726728", "Realty Income Corporation", "equity_reit_affo_nav", "10-K_10-Q", "US-GAAP"),
    )
    assert BATCH_01_TICKERS == tuple(issuer.ticker for issuer in BATCH_01_MANIFEST)
    assert len(BATCH_01_MANIFEST) == len({issuer.cik for issuer in BATCH_01_MANIFEST}) == 10

    with pytest.raises(FrozenInstanceError):
        BATCH_01_MANIFEST[0].ticker = "OTHER"  # type: ignore[misc]


def test_issuer_lookup_requires_an_exact_manifest_ticker() -> None:
    assert issuer_for_ticker("O") is BATCH_01_MANIFEST[-1]
    with pytest.raises(KeyError):
        issuer_for_ticker("o")
    with pytest.raises(KeyError):
        issuer_for_ticker("UNKNOWN")
