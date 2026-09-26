import pytest

from app.errors import AppError
from app.services import holdings_service


def test_add_us_holding_resolves_identity_from_confirmed_catalog(monkeypatch):
    captured = {}

    monkeypatch.setattr(holdings_service.company_service, "get_by_ticker", lambda ticker, market: None)

    def upsert(**kwargs):
        captured.update(kwargs)
        return {"id": 42, **kwargs}

    monkeypatch.setattr(holdings_service.company_service, "upsert", upsert)
    monkeypatch.setattr(holdings_service, "query", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        holdings_service,
        "query_one",
        lambda *args, **kwargs: {
            "id": 7,
            "company_id": 42,
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
            "currency": "USD",
            "market": "US",
            "exchange": "US",
        },
    )

    result = holdings_service.add(1, "aapl", "us")
    assert result["ticker"] == "AAPL"
    assert captured["market"] == "US"
    assert captured["currency"] == "USD"
    assert captured["cik"] == "0000320193"


def test_non_catalog_us_holding_is_rejected(monkeypatch):
    monkeypatch.setattr(holdings_service.company_service, "get_by_ticker", lambda ticker, market: None)
    with pytest.raises(AppError, match="No confirmed batch valuation"):
        holdings_service.add(1, "NVDA", "US")
