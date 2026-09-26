"""Market-aware company persistence."""

from typing import Any

from ..db import query, query_one


_FIELDS = "id, ticker, name, sector, currency, market, exchange, cik"


def list_all(
    sector: str | None = None,
    market: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[str] = []
    if sector:
        clauses.append("sector = %s")
        values.append(sector)
    if market:
        clauses.append("market = %s")
        values.append(market.upper())
    if search:
        clauses.append("(ticker ILIKE %s OR name ILIKE %s)")
        term = f"%{search.strip()}%"
        values.extend((term, term))
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return query(
        f"SELECT {_FIELDS} FROM companies{where} ORDER BY market, ticker",
        tuple(values),
    )


def get(company_id: int) -> dict[str, Any] | None:
    return query_one(f"SELECT {_FIELDS} FROM companies WHERE id = %s", (company_id,))


def get_by_ticker(ticker: str, market: str = "PH") -> dict[str, Any] | None:
    return query_one(
        f"SELECT {_FIELDS} FROM companies WHERE ticker = %s AND market = %s",
        (ticker.upper(), market.upper()),
    )


def upsert(
    ticker: str,
    name: str,
    sector: str | None,
    currency: str = "PHP",
    market: str = "PH",
    exchange: str | None = None,
    cik: str | None = None,
) -> dict[str, Any]:
    """Insert or update one market-qualified security."""
    return query_one(
        f"""
        INSERT INTO companies (ticker, name, sector, currency, market, exchange, cik)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (market, ticker) DO UPDATE
          SET name = EXCLUDED.name,
              sector = EXCLUDED.sector,
              currency = EXCLUDED.currency,
              exchange = EXCLUDED.exchange,
              cik = EXCLUDED.cik
        RETURNING {_FIELDS}
        """,
        (ticker.upper(), name, sector, currency, market.upper(), exchange, cik),
    )
