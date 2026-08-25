"""Read-only access to reviewed, precomputed filing-only U.S. valuations."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from fastapi import APIRouter

from ..deps import CurrentUser
from ..errors import AppError
from ..models.valuation import UsCalculatorInput
from ..services import valuation_service
from ..us_valuation.artifacts import sanitize_public_artifact
from ..us_valuation.baseline import apply_public_baseline_contract
from ..us_valuation.calculator import calculate, calculator_view
from ..us_valuation.market_comparison import (
    load_private_eod_record,
    load_private_security_record,
    public_market_comparison,
    validate_eod_for_valuation,
)


router = APIRouter(prefix="/us-valuations", tags=["us-valuations"])
DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "us_valuations"
DATA_ROOT = Path(
    os.environ.get("FINSIGHT_US_VALUATION_DATA_ROOT") or DEFAULT_DATA_ROOT
)
EOD_DATA_ROOT = (
    Path(os.environ["FINSIGHT_US_EOD_DATA_ROOT"])
    if os.environ.get("FINSIGHT_US_EOD_DATA_ROOT")
    else None
)
SECURITY_MASTER_ROOT = (
    Path(os.environ["FINSIGHT_US_SECURITY_MASTER_ROOT"])
    if os.environ.get("FINSIGHT_US_SECURITY_MASTER_ROOT")
    else None
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
    result = sanitize_public_artifact(_read_artifact_object(path))
    base = result.get("scenario_range", {}).get("base")
    if (
        isinstance(base, (int, float))
        and EOD_DATA_ROOT is not None
        and SECURITY_MASTER_ROOT is not None
    ):
        try:
            security = load_private_security_record(SECURITY_MASTER_ROOT, normalized)
            record = load_private_eod_record(EOD_DATA_ROOT, normalized)
            if security is not None and record is not None:
                if security.canonical_security != normalized:
                    raise ValueError("security-master identity mismatch")
                validate_eod_for_valuation(
                    record,
                    ticker=normalized,
                    primary_listing=security.primary_listing,
                    valuation_date=result["valuation_date"],
                )
                result["market_comparison"] = public_market_comparison(
                    base_value=float(base), record=record
                )
            else:
                result["market_comparison"] = {
                    "status": "unavailable",
                    "reason": "approved_eod_record_unavailable",
                }
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            result["market_comparison"] = {
                "status": "unavailable",
                "reason": "approved_eod_record_invalid",
            }
        result = apply_public_baseline_contract(result)
    return result


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
            "availability_type": data["availability_type"],
            "confidence": data["confidence"],
        })
    return {"count": len(items), "items": items}


@router.get("/{ticker}/calculator")
def get_us_valuation_calculator(ticker: str) -> dict:
    return calculator_view(load_generated_result(ticker))


@router.post("/{ticker}/calculator")
def post_us_valuation_calculator(
    ticker: str, body: UsCalculatorInput, user: CurrentUser
) -> dict:
    artifact = load_generated_result(ticker)
    try:
        result = calculate(
            artifact,
            overrides=body.overrides,
            manual_price=body.manual_price,
        )
    except ValueError as error:
        raise AppError(str(error), 400) from error
    if body.save:
        saved = valuation_service.save_us(
            user_id=user["sub"],
            ticker=result["ticker"],
            model=str(result["assigned_model"]),
            model_version=str(result["model_version"]),
            assumptions=result["assumptions"],
            user_price=body.manual_price,
            result={
                "low": result["result"]["low"],
                "base": result["result"]["base"],
                "high": result["result"]["high"],
                "comparison": result["comparison"],
                "availability_type": result["availability_type"],
            },
        )
        result["saved_id"] = saved["id"]
    return result


@router.get("/{ticker}")
def get_us_valuation(ticker: str) -> dict:
    return load_generated_result(ticker)
