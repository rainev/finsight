"""Read-only access to reviewed, precomputed filing-only U.S. valuations."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from fastapi import APIRouter

from ..errors import AppError
from ..us_valuation.artifacts import sanitize_public_artifact


router = APIRouter(prefix="/us-valuations", tags=["us-valuations"])
DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "us_valuations"
DATA_ROOT = Path(
    os.environ.get("FINSIGHT_US_VALUATION_DATA_ROOT") or DEFAULT_DATA_ROOT
)
TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


def _read_artifact_object(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AppError("U.S. valuation artifact is invalid", 500) from exc
    if not isinstance(result, dict):
        raise AppError("U.S. valuation artifact is invalid", 500)

    filename_ticker = path.stem
    issuer = result.get("issuer")
    top_level_ticker = result.get("ticker")
    if (
        not TICKER.fullmatch(filename_ticker)
        or not isinstance(issuer, dict)
        or issuer.get("ticker") != filename_ticker
        or (
            top_level_ticker is not None
            and top_level_ticker != filename_ticker
        )
    ):
        raise AppError("U.S. valuation artifact identity mismatch", 500)
    return result


def load_generated_result(ticker: str) -> dict:
    normalized = ticker.upper()
    if not TICKER.fullmatch(normalized):
        raise AppError("Invalid ticker", 400)
    path = DATA_ROOT / f"{normalized}.json"
    if not path.exists():
        raise AppError("U.S. valuation not available", 404)
    result = _read_artifact_object(path)
    return sanitize_public_artifact(result)


@router.get("")
def list_us_valuations() -> dict:
    """Public-safe summary of every available valuation (no raw financials)."""
    items = []
    for path in sorted(DATA_ROOT.glob("*.json")):
        try:
            data = _read_artifact_object(path)
        except AppError:
            continue
        data = sanitize_public_artifact(data)
        issuer = data.get("issuer", {})
        items.append({
            "ticker": issuer.get("ticker", path.stem),
            "name": issuer.get("issuer_name"),
            "sector": issuer.get("finsight_sector"),
            "model": data.get("model_policy", {}).get("primary"),
            "base": data.get("scenario_range", {}).get("base"),
            "publication_state": data.get("review", {}).get("publication_state"),
            "reliability": data["reliability"]["label"],
        })
    return {"count": len(items), "items": items}


@router.get("/{ticker}")
def get_us_valuation(ticker: str) -> dict:
    return load_generated_result(ticker)
