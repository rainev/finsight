"""Immutable input contract for the controlled ten-company Batch 01 run.

The lane field is a hypothesis for the controlled assessment, not an approved
or public valuation-model selection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .sec_client import normalize_cik


BATCH_01_VALUATION_DATE = "2026-08-14"
_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


@dataclass(frozen=True)
class BatchIssuer:
    ticker: str
    cik: str
    issuer_name: str
    lane_hypothesis: str
    filing_regime: str = "10-K_10-Q"
    accounting_standard: str = "US-GAAP"


def _issuer(
    ticker: str,
    cik: str,
    issuer_name: str,
    lane_hypothesis: str,
) -> BatchIssuer:
    if not _TICKER.fullmatch(ticker):
        raise ValueError(f"invalid Batch 01 ticker: {ticker!r}")
    if not issuer_name:
        raise ValueError("Batch 01 issuer name is required")
    if not lane_hypothesis:
        raise ValueError("Batch 01 lane hypothesis is required")
    return BatchIssuer(
        ticker=ticker,
        cik=normalize_cik(cik),
        issuer_name=issuer_name,
        lane_hypothesis=lane_hypothesis,
    )


BATCH_01_MANIFEST = (
    _issuer("AAPL", "0000320193", "Apple Inc.", "mature_operating_fcff"),
    _issuer("MSFT", "0000789019", "Microsoft Corporation", "intangible_investment_fcff"),
    _issuer("CRM", "0001108524", "Salesforce, Inc.", "intangible_investment_fcff"),
    _issuer("ANET", "0001596532", "Arista Networks, Inc.", "growth_operating_fcff"),
    _issuer("WDC", "0000106040", "Western Digital Corporation", "normalized_cyclical_fcff"),
    _issuer("DELL", "0001571996", "Dell Technologies Inc.", "captive_finance_sotp"),
    _issuer("JPM", "0000019617", "JPMorgan Chase & Co.", "bank_residual_income"),
    _issuer("BAC", "0000070858", "Bank of America Corporation", "bank_residual_income"),
    _issuer("NEE", "0000753308", "NextEra Energy, Inc.", "mixed_utility_sotp"),
    _issuer("O", "0000726728", "Realty Income Corporation", "equity_reit_affo_nav"),
)
BATCH_01_TICKERS = tuple(issuer.ticker for issuer in BATCH_01_MANIFEST)

if len(BATCH_01_TICKERS) != len(set(BATCH_01_TICKERS)):
    raise ValueError("Batch 01 tickers must be unique")
if len(BATCH_01_MANIFEST) != len({issuer.cik for issuer in BATCH_01_MANIFEST}):
    raise ValueError("Batch 01 CIKs must be unique")

_ISSUER_BY_TICKER = {issuer.ticker: issuer for issuer in BATCH_01_MANIFEST}


def issuer_for_ticker(ticker: str) -> BatchIssuer:
    """Return a Batch 01 issuer only for an exact manifest ticker."""
    return _ISSUER_BY_TICKER[ticker]
