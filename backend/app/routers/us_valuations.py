"""Catalog-bound access to the confirmed Universe Reset Batches 01–10."""

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
from ..us_valuation.calculator import calculate, calculator_view
from ..us_valuation.catalog import CatalogIntegrityError, load_active_catalog


router = APIRouter(prefix="/us-valuations", tags=["us-valuations"])
DEFAULT_CATALOGS_ROOT = Path(__file__).resolve().parents[1] / "data" / "us_valuation_catalogs"
CATALOGS_ROOT = Path(
    os.environ.get("FINSIGHT_US_VALUATION_CATALOG_ROOT") or DEFAULT_CATALOGS_ROOT
)
CATALOG = load_active_catalog(CATALOGS_ROOT)
DEFAULT_DATA_ROOT = CATALOG.artifacts_root
DATA_ROOT = DEFAULT_DATA_ROOT
TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


def _artifact_path(ticker: str) -> Path:
    if DATA_ROOT.resolve() != DEFAULT_DATA_ROOT.resolve():
        if os.environ.get("APP_ENV") != "test":
            raise AppError("U.S. valuation catalog is invalid", 500)
        return DATA_ROOT / f"{ticker}.json"
    try:
        return CATALOG.verify_artifact(ticker)
    except KeyError as exc:
        raise AppError("U.S. valuation not available", 404) from exc
    except CatalogIntegrityError as exc:
        raise AppError("U.S. valuation catalog is invalid", 500) from exc


def _read_artifact(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AppError("U.S. valuation artifact is invalid", 500) from exc
    if not isinstance(result, dict):
        raise AppError("U.S. valuation artifact is invalid", 500)
    issuer = result.get("issuer")
    if (
        not isinstance(issuer, dict)
        or issuer.get("ticker") != path.stem
        or result.get("ticker", path.stem) != path.stem
    ):
        raise AppError("U.S. valuation artifact identity mismatch", 500)
    return result


def _evidence_health(result: dict) -> list[dict]:
    """Expose honest model-evidence quality without inventing company ratios."""
    reliability = result.get("reliability")
    reliability = reliability if isinstance(reliability, dict) else {}
    scores = {"High": 90, "Medium": 74, "Low": 54}
    rows = (
        ("source_strength", "Source strength", reliability.get("source_cap")),
        ("accounting_quality", "Accounting quality", reliability.get("accounting_label")),
        ("scenario_resilience", "Scenario resilience", reliability.get("scenario_label")),
        ("model_confidence", "Model confidence", reliability.get("label")),
    )
    return [
        {
            "key": key,
            "label": label,
            "score": scores.get(value),
            "band": value or "Not scored",
            "methodology_version": "US-VALUATION-EVIDENCE-1.0",
        }
        for key, label, value in rows
    ]


def load_generated_result(ticker: str) -> dict:
    normalized = ticker.upper()
    if not TICKER.fullmatch(normalized):
        raise AppError("Invalid ticker", 400)
    result = sanitize_public_artifact(_read_artifact(_artifact_path(normalized)))
    if DATA_ROOT.resolve() == DEFAULT_DATA_ROOT.resolve():
        result["evidence_health"] = _evidence_health(result)
        entry = CATALOG.entry_by_ticker[normalized]
        result["catalog"] = {
            **CATALOG.public_metadata(),
            "batch": entry.batch,
            "source_audit": entry.source_audit,
        }
    return result


@router.get("")
def list_us_valuations() -> dict:
    """List exactly the 100 companies confirmed in batches 01–10."""
    items = []
    using_catalog = DATA_ROOT.resolve() == DEFAULT_DATA_ROOT.resolve()
    sources = (
        [(entry, CATALOG.verify_artifact(entry.ticker)) for entry in CATALOG.entries]
        if using_catalog
        else [(None, path) for path in sorted(DATA_ROOT.glob("*.json"))]
    )
    for entry, path in sources:
        try:
            data = sanitize_public_artifact(_read_artifact(path))
        except (AppError, CatalogIntegrityError) as exc:
            if using_catalog:
                raise AppError("U.S. valuation catalog is invalid", 500) from exc
            continue
        issuer = data.get("issuer", {})
        summary = {
            "ticker": issuer.get("ticker", path.stem),
            "name": issuer.get("issuer_name"),
            "sector": issuer.get("finsight_sector"),
            "model": data.get("primary_valuation_method")
            or data.get("model_policy", {}).get("primary"),
            "base": data.get("scenario_range", {}).get("base"),
            "publication_state": data.get("review", {}).get("publication_state"),
        }
        if entry is not None:
            summary.update({
                "availability_type": entry.availability_type,
                "reliability": data.get("reliability", {}).get("label"),
                "batch": entry.batch,
            })
        items.append(summary)
    result = {"count": len(items), "items": items}
    if using_catalog:
        result.update(CATALOG.public_metadata())
    return result


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
            scenario=body.scenario,
        )
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    if body.save:
        saved = valuation_service.save_us(
            user_id=user["sub"],
            ticker=result["ticker"],
            model=str(result["assigned_model"]),
            model_version=str(result["model_version"]),
            assumptions=result["assumptions"],
            user_price=body.manual_price,
            result={
                **result["result"],
                "comparison": result["comparison"],
                "availability_type": result["availability_type"],
                "selected_scenario": result["selected_scenario"],
            },
        )
        result["saved_id"] = saved["id"]
    return result


@router.get("/{ticker}")
def get_us_valuation(ticker: str) -> dict:
    return load_generated_result(ticker)
