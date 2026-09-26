"""Holdings persistence — a user's watchlist of owned companies. Raw SQL over the
shared pool. Every query is scoped by user_id so one user can never touch
another's holdings.
"""

import json
from pathlib import Path
from typing import Any

from ..db import query, query_one
from ..errors import AppError
from ..us_valuation.catalog import CatalogIntegrityError, load_active_catalog
from . import company_service


_CATALOG = load_active_catalog(
    Path(__file__).resolve().parents[1] / "data" / "us_valuation_catalogs"
)

# The client-facing shape: the holding joined to its company.
_SELECT = """
  SELECT h.id, h.company_id, c.ticker, c.name, c.sector,
         c.currency, c.market, c.exchange
  FROM holdings h
  JOIN companies c ON c.id = h.company_id
"""


def list_for_user(user_id: int) -> list[dict[str, Any]]:
    return query(_SELECT + " WHERE h.user_id = %s ORDER BY c.ticker", (user_id,))


def _get(user_id: int, holding_id: int) -> dict[str, Any] | None:
    return query_one(_SELECT + " WHERE h.id = %s AND h.user_id = %s", (holding_id, user_id))


def _ensure_us_company(ticker: str) -> dict[str, Any]:
    try:
        path = _CATALOG.verify_artifact(ticker)
    except KeyError as exc:
        raise AppError(f"No confirmed batch valuation found for ticker '{ticker}'.", 404) from exc
    except CatalogIntegrityError as exc:
        raise AppError("U.S. valuation catalog is invalid", 500) from exc
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AppError("U.S. valuation artifact is invalid", 500) from exc
    issuer = artifact.get("issuer", {})
    return company_service.upsert(
        ticker=ticker,
        name=issuer.get("issuer_name") or ticker,
        sector=issuer.get("finsight_sector"),
        currency="USD",
        market="US",
        exchange="US",
        cik=str(issuer.get("cik") or "").zfill(10) or None,
    )


def add(user_id: int, ticker: str, market: str = "PH") -> dict[str, Any]:
    normalized_market = market.upper()
    normalized_ticker = ticker.upper()
    company = company_service.get_by_ticker(normalized_ticker, normalized_market)
    if not company and normalized_market == "US":
        company = _ensure_us_company(normalized_ticker)
    if not company:
        raise AppError(f"No {normalized_market} company found for ticker '{ticker}'.", 404)

    # Idempotent per (user, company): re-adding a held ticker is a no-op.
    query(
        "INSERT INTO holdings (user_id, company_id) VALUES (%s, %s) "
        "ON CONFLICT (user_id, company_id) DO NOTHING",
        (user_id, company["id"]),
    )
    return query_one(
        _SELECT + " WHERE h.user_id = %s AND h.company_id = %s", (user_id, company["id"])
    )


def remove(user_id: int, holding_id: int) -> None:
    if not _get(user_id, holding_id):
        raise AppError("Holding not found", 404)
    query("DELETE FROM holdings WHERE id = %s AND user_id = %s", (holding_id, user_id))
