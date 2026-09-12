"""Read-only access to reviewed, precomputed filing-only U.S. valuations."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from contextvars import ContextVar

from fastapi import APIRouter, Depends

from ..deps import CurrentUser
from ..errors import AppError
from ..models.valuation import UsCalculatorInput
from ..services import valuation_service
from ..us_valuation.artifacts import sanitize_public_artifact
from ..us_valuation.baseline import apply_public_baseline_contract
from ..us_valuation.calculator import calculate, calculator_view, baseline_version
from ..us_valuation.catalog import (
    CatalogIntegrityError,
    TICKER,
    load_active_catalog,
    load_catalog_version,
    sha256_bytes,
)
from ..us_valuation.refresh_catalog_store import RefreshCatalogStore
from ..us_valuation.market_comparison import (
    load_private_eod_record,
    load_private_security_record,
    public_market_comparison,
    validate_eod_for_valuation,
)


router = APIRouter(prefix="/us-valuations", tags=["us-valuations"])
DEFAULT_CATALOGS_ROOT = (
    Path(__file__).resolve().parents[1] / "data" / "us_valuation_catalogs"
)
CATALOGS_ROOT = Path(
    os.environ.get("FINSIGHT_US_VALUATION_CATALOG_ROOT") or DEFAULT_CATALOGS_ROOT
)
CATALOG = load_active_catalog(CATALOGS_ROOT)
DEFAULT_DATA_ROOT = CATALOG.artifacts_root
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
RECIPE_ROOT = Path(os.environ['FINSIGHT_US_RECIPE_ROOT']) if os.environ.get('FINSIGHT_US_RECIPE_ROOT') else None
RUNTIME_ROOT = Path(os.environ['FINSIGHT_US_REFRESH_ROOT']) if os.environ.get('FINSIGHT_US_REFRESH_ROOT') else None
RUNTIME_STORE = RefreshCatalogStore(RUNTIME_ROOT / 'catalogs', frozen_registry=RUNTIME_ROOT / 'registry.json') if RUNTIME_ROOT else None
RUNTIME_READER = RUNTIME_STORE.reader() if RUNTIME_STORE else None
_REQUEST_CATALOG = ContextVar('us_valuation_request_catalog', default=None)


async def _pin_catalog():
    try:
        snapshot = RUNTIME_READER.get_snapshot() if RUNTIME_READER else CATALOG
    except CatalogIntegrityError as exc:
        raise AppError('U.S. valuation catalog is invalid', 500) from exc
    token = _REQUEST_CATALOG.set(snapshot)
    try:
        yield
    finally:
        _REQUEST_CATALOG.reset(token)


router.dependencies.append(Depends(_pin_catalog))


def _catalog():
    return _REQUEST_CATALOG.get() or (RUNTIME_READER.get_snapshot() if RUNTIME_READER else CATALOG)


def _comparison_now() -> datetime:
    return datetime.now(timezone.utc)


def _load_recipe(ticker: str) -> dict | None:
    ticker = ticker.upper()
    if not TICKER.fullmatch(ticker):
        raise AppError('Invalid ticker', 400)
    catalog = _catalog()
    hashes = catalog.manifest.get('private_recipe_sha256') if _uses_active_catalog() else None
    expected = None
    if hashes is not None:
        expected = hashes.get(ticker)
        if expected is None:
            if ticker in catalog.entry_by_ticker and catalog.entry_by_ticker[ticker].availability_type != 'not_available':
                raise AppError('Calculation recipe is missing', 500)
            return None
        path = catalog.root / 'recipes' / f'{ticker}.json'
    elif RECIPE_ROOT is not None:
        path = RECIPE_ROOT / f'{ticker}.json'
    else:
        return None
    if not path.is_file():
        if expected is not None:
            raise AppError('Calculation recipe is missing', 500)
        return None
    try:
        payload = path.read_bytes()
        if expected is not None and sha256_bytes(payload) != expected:
            raise ValueError('recipe hash mismatch')
        value = json.loads(payload)
        if not isinstance(value, dict) or value.get('ticker') != ticker.upper():
            raise ValueError('identity mismatch')
        return value
    except (OSError, ValueError) as exc:
        raise AppError('Calculation recipe is invalid', 500) from exc


def _uses_active_catalog() -> bool:
    return RUNTIME_READER is not None or DATA_ROOT.resolve() == CATALOG.artifacts_root.resolve()


def _artifact_path(ticker: str) -> Path:
    if not _uses_active_catalog():
        # Hermetic tests may still inject a one-off loose root. Production uses
        # only the manifest-controlled active catalog.
        if os.environ.get("APP_ENV") != "test":
            raise AppError("U.S. valuation catalog is invalid", 500)
        return DATA_ROOT / f"{ticker}.json"
    try:
        return _catalog().verify_artifact(ticker)
    except KeyError as exc:
        raise AppError("U.S. valuation not available", 404) from exc
    except CatalogIntegrityError as exc:
        raise AppError("U.S. valuation catalog is invalid", 500) from exc


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


def load_generated_result(ticker: str, *, comparison_mode: str = 'current') -> dict:
    normalized = ticker.upper()
    if not TICKER.fullmatch(normalized):
        raise AppError("Invalid ticker", 400)
    path = _artifact_path(normalized)
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
                    mode=comparison_mode,
                    reference_datetime=_comparison_now() if comparison_mode == 'current' else None,
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
    if _uses_active_catalog():
        catalog = _catalog()
        result['catalog_version'] = catalog.catalog_version
        entry = catalog.entry_by_ticker.get(normalized)
        result['catalog'] = {
            'catalog_version': catalog.catalog_version,
            'batch': entry.batch if entry is not None else None,
            'universe_version': catalog.universe_version,
            'valuation_date': catalog.valuation_date,
        }
        result['freshness'] = catalog.manifest.get('refresh_status', {}).get(normalized, {'outcome': 'historical_snapshot', 'checked_as_of': result['valuation_date'], 'reason': None})
    result['dates'] = {'filing_period': result['source_financial_statement']['period_end'],
                       'evidence_cutoff': result['valuation_date'],
                       'assumption_date': result.get('assumption_date'),
                       'market_comparison_date': (result.get('market_comparison') or {}).get('price_date')}
    comparison = result.get('market_comparison')
    if isinstance(comparison, dict) and 'verdict' not in comparison:
        gap = comparison.get('gap_pct')
        comparison['verdict'] = (
            'Undervalued' if isinstance(gap, (int, float)) and gap > 0.05
            else 'Overvalued' if isinstance(gap, (int, float)) and gap < -0.05
            else 'Fairly valued' if isinstance(gap, (int, float))
            else None
        )
    return result


@router.get("")
def list_us_valuations() -> dict:
    """Public-safe summary of every available valuation (no raw financials)."""
    items = []
    if _uses_active_catalog():
        paths = []
        for entry in _catalog().entries:
            try:
                paths.append(_catalog().verify_artifact(entry.ticker))
            except CatalogIntegrityError as exc:
                raise AppError("U.S. valuation catalog is invalid", 500) from exc
    else:
        if os.environ.get("APP_ENV") != "test":
            raise AppError("U.S. valuation catalog is invalid", 500)
        paths = sorted(DATA_ROOT.glob("*.json"))
    for path in paths:
        try:
            data = _read_artifact_object(path)
        except AppError:
            if _uses_active_catalog():
                raise
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
    result = {"count": len(items), "items": items}
    if _uses_active_catalog():
        result.update(_catalog().public_metadata())
    return result


@router.get("/{ticker}/calculator")
def get_us_valuation_calculator(ticker: str) -> dict:
    artifact = load_generated_result(ticker)
    return calculator_view(artifact, recipe=_load_recipe(ticker))


@router.post("/{ticker}/calculator")
def post_us_valuation_calculator(
    ticker: str, body: UsCalculatorInput, user: CurrentUser
) -> dict:
    artifact = load_generated_result(ticker)
    recipe = _load_recipe(ticker)
    if (body.baseline_version is not None and body.baseline_version != baseline_version(artifact)) or (recipe is not None and (body.baseline_version is None or body.recipe_version != recipe.get('recipe_version'))):
        raise AppError('Valuation changed; reload the calculator before recalculating or saving', 409)
    if body.scenario is not None and body.selected_scenario is not None and body.scenario != body.selected_scenario:
        raise AppError('scenario and selected_scenario must match', 400)
    selected_scenario = body.scenario if body.scenario is not None else body.selected_scenario
    try:
        result = calculate(
            artifact,
            overrides=body.overrides,
            manual_price=body.manual_price,
            recipe=recipe,
            selected_scenario=selected_scenario,
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
                "baseline_version": result.get('baseline_version'),
                "recipe_version": result.get('recipe_version'),
                "recipe_hash": result.get('recipe_hash'),
                "selected_scenario": result.get('selected_scenario', selected_scenario or 'base'),
                "scenario_presets": result.get('scenario_presets'),
                "user_overrides": body.overrides,
            },
        )
        result["saved_id"] = saved["id"]
    return result


@router.get("/{ticker}")
def get_us_valuation(ticker: str, comparison_mode: Literal['current','historical'] = 'current') -> dict:
    return load_generated_result(ticker, comparison_mode=comparison_mode)


@router.get('/{ticker}/history')
def get_us_valuation_history(ticker: str) -> dict:
    ticker = ticker.upper()
    if not TICKER.fullmatch(ticker):
        raise AppError('Invalid ticker', 400)
    catalog = _catalog()
    if ticker not in catalog.entry_by_ticker:
        raise AppError('U.S. valuation not available', 404)
    catalogs = {catalog.catalog_version: catalog}
    if RUNTIME_STORE:
        # The first refresh has no prior runtime activation receipt. Its dated
        # migration baseline still belongs in history, including repaired rows.
        migration = load_catalog_version(RUNTIME_STORE.runtime_root.parent / 'baseline',
                                        expected_manifest_sha256=RUNTIME_STORE.registry.baseline_manifest_sha256)
        catalogs[migration.catalog_version] = migration
        for path in RUNTIME_STORE.history_root.glob('activation-*.json'):
            receipt = json.loads(path.read_text())
            version = receipt['catalog_version']
            if Path(version).name != version:
                raise AppError('Valuation history is invalid', 500)
            historic = load_catalog_version(RUNTIME_STORE.snapshots_root / version, expected_manifest_sha256=receipt['manifest_sha256'])
            catalogs[version] = historic
    items = []
    for historic in catalogs.values():
        if ticker not in historic.entry_by_ticker:
            continue
        value = sanitize_public_artifact(json.loads(historic.verify_artifact(ticker).read_text()))
        items.append({'catalog_version': historic.catalog_version, 'valuation_date': value['valuation_date'],
                      'availability_type': value['availability_type'], 'scenario_range': value['scenario_range'],
                      'source_financial_statement': value['source_financial_statement']})
    return {'ticker': ticker, 'items': sorted(items, key=lambda row: (row['valuation_date'], row['catalog_version']), reverse=True)}
