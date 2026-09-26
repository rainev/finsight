"""Authenticated, staged read API for the governed PSE valuation V2 pilot."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from fastapi import APIRouter

from ..deps import CurrentUser
from ..errors import AppError
from ..models.valuation import UsCalculatorInput
from ..pse_valuation.calculator import calculate, calculator_view
from ..pse_valuation.catalog import CatalogIntegrityError, PseValuationCatalog, load_catalog, load_pointer
from ..pse_valuation.contract import PseValuationArtifact
from ..services import valuation_service


router = APIRouter(prefix="/pse-valuations", tags=["pse-valuations"])
DEFAULT_CATALOGS_ROOT = Path(__file__).resolve().parents[1] / "data" / "pse_valuation_catalogs"
CATALOGS_ROOT = Path(
    os.environ.get("FINSIGHT_PSE_VALUATION_CATALOG_ROOT") or DEFAULT_CATALOGS_ROOT
)
POINTER_NAME = os.environ.get("FINSIGHT_PSE_VALUATION_CATALOG_POINTER") or "active.json"
TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")


def _catalog():
    try:
        return load_pointer(CATALOGS_ROOT, POINTER_NAME)
    except CatalogIntegrityError as exc:
        raise AppError("PSE V2 valuation catalog is invalid", 500) from exc


def _load_artifact(ticker: str, catalog: PseValuationCatalog | None = None) -> dict:
    normalized = ticker.upper()
    if not TICKER.fullmatch(normalized):
        raise AppError("Invalid ticker", 400)
    catalog = catalog if catalog is not None else _catalog()
    try:
        path = catalog.verify_artifact(normalized)
    except KeyError as exc:
        raise AppError("PSE V2 valuation not available", 404) from exc
    except CatalogIntegrityError as exc:
        raise AppError("PSE V2 valuation catalog is invalid", 500) from exc
    try:
        artifact = PseValuationArtifact.model_validate_json(path.read_bytes())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise AppError("PSE V2 valuation artifact is invalid", 500) from exc
    result = artifact.model_dump(mode="json")
    entry = catalog.entry_by_ticker[normalized]
    result["catalog"] = {
        **catalog.public_metadata(),
        "source_audit": entry.source_audit,
    }
    return result


@router.get("")
def list_pse_valuations(_user: CurrentUser) -> dict:
    catalog = _catalog()
    items = []
    for entry in catalog.entries:
        artifact = _load_artifact(entry.ticker, catalog)
        base = artifact["scenarios"].get("base")
        relative = artifact.get("market_relative") or {}
        relative_base = (relative.get("estimates") or {}).get("base")
        items.append(
            {
                "ticker": entry.ticker,
                "name": artifact["issuer"].get("name"),
                "subsector": artifact["subsector"],
                "primary_model": entry.primary_model,
                "base": base.get("value_per_share") if base else relative_base,
                "availability_type": entry.availability_type,
                "publication_state": entry.publication_state,
                "valuation_date": artifact["valuation_date"],
            }
        )
    return {"count": len(items), "items": items, **catalog.public_metadata()}


@router.get("/{ticker}/calculator")
def get_pse_valuation_calculator(ticker: str, _user: CurrentUser) -> dict:
    return calculator_view(_load_artifact(ticker))


@router.post("/{ticker}/calculator")
def post_pse_valuation_calculator(
    ticker: str, body: UsCalculatorInput, user: CurrentUser
) -> dict:
    artifact = _load_artifact(ticker)
    try:
        result = calculate(
            artifact,
            overrides=body.overrides,
            scenario=body.scenario,
            manual_price=body.manual_price,
        )
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    if body.save:
        saved = valuation_service.save_pse_v2(
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


@router.get("/{ticker}/history")
def get_pse_valuation_history(ticker: str, _user: CurrentUser) -> dict:
    normalized = ticker.upper()
    if not TICKER.fullmatch(normalized):
        raise AppError("Invalid ticker", 400)
    items = []
    for path in sorted(CATALOGS_ROOT.iterdir() if CATALOGS_ROOT.exists() else [], reverse=True):
        if not path.is_dir() or not (path / "manifest.json").exists():
            continue
        try:
            catalog = load_catalog(path)
            artifact_path = catalog.verify_artifact(normalized)
        except (CatalogIntegrityError, KeyError):
            continue
        artifact = PseValuationArtifact.model_validate_json(artifact_path.read_bytes()).model_dump(mode="json")
        if artifact["availability_type"] == "intrinsic_valuation":
            values = {
                "low": artifact["scenarios"]["bear"]["value_per_share"],
                "base": artifact["scenarios"]["base"]["value_per_share"],
                "high": artifact["scenarios"]["bull"]["value_per_share"],
            }
        elif artifact["availability_type"] == "market_relative_only":
            values = artifact["market_relative"]["estimates"]
        else:
            values = {"low": None, "base": None, "high": None}
        items.append(
            {
                "catalog_version": catalog.version,
                "valuation_date": catalog.valuation_date,
                "availability_type": artifact["availability_type"],
                "publication_state": artifact["publication_state"],
                "range": values,
                "filing_period": artifact.get("filing_period"),
            }
        )
    return {"ticker": normalized, "items": items}


@router.get("/{ticker}")
def get_pse_valuation(ticker: str, _user: CurrentUser) -> dict:
    return _load_artifact(ticker)
