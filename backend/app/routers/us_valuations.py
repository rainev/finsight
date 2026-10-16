"""Catalog-bound access to the confirmed Universe Reset Batches 01–10."""

from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends

from ..deps import CurrentUser
from ..errors import AppError
from ..models.valuation import UsCalculatorInput
from ..services import valuation_service
from ..us_valuation.artifacts import sanitize_public_artifact
from ..us_valuation.calculator import calculate, calculator_view
from ..us_valuation.catalog import CatalogIntegrityError, load_active_catalog, load_catalog
from ..us_valuation import latest_calculator
from ..us_valuation.approved_inheritance import review_selection, preserved_original
from ..us_valuation.private_integration import project_review_artifact, preserved_b03_public_parent, preserved_b05_public_parent


router = APIRouter(prefix="/us-valuations", tags=["us-valuations"])
DEFAULT_CATALOGS_ROOT = Path(__file__).resolve().parents[1] / "data" / "us_valuation_catalogs"
CATALOGS_ROOT = Path(
    os.environ.get("FINSIGHT_US_VALUATION_CATALOG_ROOT") or DEFAULT_CATALOGS_ROOT
)
REVIEW_SELECTION = review_selection()
REVIEW_ONLY = REVIEW_SELECTION is not None
CATALOG = (load_catalog(REVIEW_SELECTION[0], manifest_sha256=REVIEW_SELECTION[1])
           if REVIEW_ONLY else load_active_catalog(CATALOGS_ROOT))


async def _pin_read_path():
    from ..us_valuation.read_path_snapshot import install
    proof_context = install(CATALOG.root, CATALOG.manifest)
    next(proof_context)
    try:
        yield
    finally:
        proof_context.close()


router.dependencies.append(Depends(_pin_read_path))
if CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-QUALITY06-STAGED-INHERITANCE-1','US-QUALITY06-OFFLINE-RETENTION-CHILD-1','US-QUALITY05-STAGED-INHERITANCE-1','US-QUALITY05-OFFLINE-RETENTION-CHILD-1','US-QUALITY06-ADMITTED-RETENTION-CHILD-1','US-QUALITY05-ADMITTED-RETENTION-CHILD-1','US-QUALITY04-STAGED-INHERITANCE-1','US-QUALITY04-OFFLINE-RETENTION-CHILD-1','US-QUALITY04-ADMITTED-RETENTION-CHILD-1','US-QUALITY03-STAGED-INHERITANCE-1','US-QUALITY03-OFFLINE-RETENTION-CHILD-1','US-QUALITY03-ADMITTED-RETENTION-CHILD-1'} and not REVIEW_ONLY:
    raise RuntimeError('inactive catalog requires its exact authenticated read-only review authority')
if CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-QUALITY02-STAGED-INHERITANCE-1','US-QUALITY02-OFFLINE-RETENTION-CHILD-1','US-QUALITY02-ADMITTED-RETENTION-CHILD-1'} and not REVIEW_ONLY:
    raise RuntimeError('Quality02 inactive catalog requires exact authenticated read-only review authority')
if (CATALOG.manifest.get('private_review', {}).get('profile') == 'B11-B15-FROZEN-PRIVATE-1'
        or CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B11-B15-APPROVED-PARENT-INHERITANCE-1') and not REVIEW_ONLY:
    raise RuntimeError('private650 requires authenticated read-only review authority; staged650 also requires its exact read-only scope')
if CATALOG.manifest.get('private_review', {}).get('profile') == 'B16-B20-FROZEN-PRIVATE-1' and not REVIEW_ONLY:
    raise RuntimeError('private700 requires exact authenticated read-only authority')
if CATALOG.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1' and not REVIEW_ONLY:
    raise RuntimeError('staged700 requires exact authenticated read-only authority')
DEFAULT_DATA_ROOT = CATALOG.artifacts_root
DATA_ROOT = DEFAULT_DATA_ROOT
TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
LATEST_500_MANIFEST_SHA256 = "7f0ec0dc5f9489e9d22054a12b1ba91d553d9b982e8201acd6cf71cdc5d1fbcf"
INITIAL_500_MANIFEST_SHA256 = "c80a26aff4b4760a34c042d13a83ca93dbc096513e9847ebc73a9188a3f2ee8c"


def _using_catalog() -> bool:
    return DATA_ROOT.resolve() == DEFAULT_DATA_ROOT.resolve()


def _request_proof_reader():
    from ..us_valuation.approved_inheritance import _proof
    from ..us_valuation.read_path_snapshot import SnapshotProofReader, current
    snapshot = current()
    if snapshot is None:
        return _proof
    return SnapshotProofReader(snapshot)


def _is_latest_500() -> bool:
    return _using_catalog() and CATALOG.manifest_sha256 == LATEST_500_MANIFEST_SHA256


def _uses_catalog_recipes() -> bool:
    return _using_catalog() and bool(CATALOG.manifest.get("private_recipe_sha256"))


def _public_artifact(path: Path, *, manifest_sha256: str | None = None) -> dict:
    raw = _read_artifact(path)
    if _using_catalog() and CATALOG.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1':
        if not REVIEW_ONLY or os.environ.get('APP_ENV') != 'test':
            raise AppError('Staged700 requires isolated authenticated review', 500)
        from ..us_valuation.staged_batches1620 import project
        return project(raw, CATALOG.manifest, ticker=path.stem, artifact_sha256=CATALOG.entry_by_ticker[path.stem].artifact_sha256)
    if _using_catalog() and CATALOG.manifest.get('private_review', {}).get('profile') == 'B16-B20-FROZEN-PRIVATE-1':
        if not REVIEW_ONLY or os.environ.get('APP_ENV') != 'test':
            raise AppError('Private700 requires isolated authenticated review', 500)
        from ..us_valuation.private_batches1620 import project
        return project(raw, CATALOG.manifest, ticker=path.stem, artifact_sha256=CATALOG.entry_by_ticker[path.stem].artifact_sha256)
    digest = manifest_sha256 or (CATALOG.manifest_sha256 if _using_catalog() else None)
    if (_using_catalog() and CATALOG.manifest.get('private_integration_only') is True
            and CATALOG.manifest.get('private_review', {}).get('profile') in {'B03-FROZEN-PRIVATE-1','B04-FROZEN-PRIVATE-1','B05-FROZEN-PRIVATE-1','B06-B10-FROZEN-PRIVATE-1','B11-B15-FROZEN-PRIVATE-1'}):
        if os.environ.get('APP_ENV') != 'test':
            raise AppError('Private integration is restricted to isolated review', 500)
        try:
            parent_proof = preserved_b03_public_parent
            if CATALOG.manifest['private_review']['profile']=='B04-FROZEN-PRIVATE-1':
                from ..us_valuation.private_integration import preserved_b04_public_parent
                parent_proof = preserved_b04_public_parent
            elif CATALOG.manifest['private_review']['profile']=='B05-FROZEN-PRIVATE-1':
                parent_proof = preserved_b05_public_parent
            elif CATALOG.manifest['private_review']['profile']=='B06-B10-FROZEN-PRIVATE-1':
                from ..us_valuation.private_batches0610 import preserved_public_parent
                parent_proof = preserved_public_parent
            elif CATALOG.manifest['private_review']['profile']=='B11-B15-FROZEN-PRIVATE-1':
                from ..us_valuation.private_batches1115 import preserved_public_parent
                parent_proof = preserved_public_parent
            if parent_proof(CATALOG.root, CATALOG.manifest, path.stem, path.read_bytes()):
                return raw
            return project_review_artifact(raw, CATALOG.manifest, ticker=path.stem,
                artifact_sha256=CATALOG.entry_by_ticker[path.stem].artifact_sha256)
        except (ValueError, KeyError, TypeError) as exc:
            raise AppError('Private integration review proof is invalid', 500) from exc
    if _using_catalog() and 'approved_base_inheritance' in CATALOG.manifest:
        try:
            if preserved_original(CATALOG.root, CATALOG.manifest, path.stem, path.read_bytes(), proof_reader=_request_proof_reader()):
                return raw
            if CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-QUALITY06-STAGED-INHERITANCE-1','US-QUALITY06-OFFLINE-RETENTION-CHILD-1','US-QUALITY05-STAGED-INHERITANCE-1','US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY06-ADMITTED-RETENTION-CHILD-1','US-QUALITY05-ADMITTED-RETENTION-CHILD-1','US-QUALITY04-STAGED-INHERITANCE-1','US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY03-STAGED-INHERITANCE-1','US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY02-STAGED-INHERITANCE-1','US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1'}:
                return sanitize_public_artifact(raw)
            if CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B11-B15-APPROVED-PARENT-INHERITANCE-1':
                # Inheritance already checked this new row against the closed
                # staged scope; both production and test review use the normal
                # public sanitizer, never the legacy private500 fallback.
                return sanitize_public_artifact(raw)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise AppError('Approved original-catalog inheritance is invalid', 500) from exc
    if digest in {LATEST_500_MANIFEST_SHA256, INITIAL_500_MANIFEST_SHA256}:
        # These exact immutable catalogs were independently checked: all 500
        # stored artifacts were byte-identical to the current public sanitizer's
        # output. Hash verification happens before this projection is reached.
        return raw
    if (_using_catalog() and (CATALOG.manifest.get('private_integration_only') is True
                             or CATALOG.manifest.get('staged_release_only') is True)
            and os.environ.get('APP_ENV') == 'test'):
        # The isolated expansion preserves the exact approved 500 byte sets.
        # Require the authentic original manifest, not a self-declared hash map.
        expected_base = CATALOG.manifest.get('approved_base_manifest_sha256')
        if expected_base not in {LATEST_500_MANIFEST_SHA256, INITIAL_500_MANIFEST_SHA256}:
            raise AppError('Private integration base authority is invalid', 500)
        try:
            base_bytes = (CATALOG.root / 'approved-base-manifest.json').read_bytes()
            if hashlib.sha256(base_bytes).hexdigest() != expected_base:
                raise ValueError('original approved manifest hash differs')
            base = json.loads(base_bytes)
            original = next((entry for entry in base['entries'] if entry['ticker'] == path.stem), None)
            if original is not None:
                if hashlib.sha256(path.read_bytes()).hexdigest() != original['artifact_sha256']:
                    raise ValueError('preserved approved artifact changed')
                return raw
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise AppError('Private integration approved base is invalid', 500) from exc
    return sanitize_public_artifact(raw)


def _load_recipe(ticker: str) -> dict | None:
    if not _uses_catalog_recipes():
        return None
    expected = CATALOG.manifest.get("private_recipe_sha256", {}).get(ticker)
    if expected is None:
        if CATALOG.entry_by_ticker[ticker].availability_type != "not_available":
            raise AppError("U.S. calculation recipe is missing", 500)
        return None
    path = CATALOG.root / "recipes" / f"{ticker}.json"
    try:
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError("recipe hash mismatch")
        recipe = json.loads(payload)
        if not isinstance(recipe, dict) or recipe.get("ticker") != ticker:
            raise ValueError("recipe identity mismatch")
        return recipe
    except (OSError, ValueError) as exc:
        raise AppError("U.S. calculation recipe is invalid", 500) from exc


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
    result = _public_artifact(_artifact_path(normalized))
    if _using_catalog():
        result["evidence_health"] = _evidence_health(result)
        entry = CATALOG.entry_by_ticker[normalized]
        result["catalog"] = {
            **CATALOG.public_metadata(),
            "batch": entry.batch,
            "source_audit": entry.source_audit,
        }
        result["catalog_version"] = CATALOG.version
        if normalized in CATALOG.manifest.get("refresh_status", {}):
            result["freshness"] = CATALOG.manifest["refresh_status"][normalized]
            result["dates"] = {
                "filing_period": result["source_financial_statement"]["period_end"],
                "evidence_cutoff": result["valuation_date"],
                "assumption_date": result.get("assumption_date"),
                "market_comparison_date": None,
            }
            if (CATALOG.manifest.get('private_integration_only') is True
                    and CATALOG.manifest.get('private_review', {}).get('profile') == 'B03-FROZEN-PRIVATE-1'
                    and entry.batch == 53):
                result['dates']['evidence_cutoff'] = CATALOG.manifest['private_review']['cutoff']
    return result


def _private_scope(artifact: dict, payload: dict) -> dict:
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-B1620-ADMITTED-RETENTION-CHILD-1'}:
        from ..us_valuation.admitted_batches1620 import consumer_disclosures
        return consumer_disclosures(CATALOG.root, CATALOG.manifest, artifact, payload)
    if _using_catalog() and CATALOG.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1':
        from ..us_valuation.staged_batches1620 import consumer_disclosures
        return consumer_disclosures(CATALOG.manifest, artifact, payload)
    if _using_catalog() and CATALOG.manifest.get('private_review', {}).get('profile') == 'B16-B20-FROZEN-PRIVATE-1':
        from ..us_valuation.private_batches1620 import consumer_disclosures
        return consumer_disclosures(CATALOG.manifest, artifact, payload)
    proof_reader = _request_proof_reader()
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1':
        from ..us_valuation.quality06_admission import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY06-ADMITTED-RETENTION-CHILD-1':
        from ..us_valuation.quality06_admitted_retention import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY06-OFFLINE-RETENTION-CHILD-1':
        from ..us_valuation.quality06_retention import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY06-STAGED-INHERITANCE-1':
        from ..us_valuation.quality06_staged import TARGETS, CARRY_FORWARD, anchors, proof
        if artifact['issuer']['ticker'] not in TARGETS | CARRY_FORWARD:
            from ..us_valuation.quality05_admission import consumer_disclosures
            parent = proof(CATALOG.root,'approved-parent-manifest.json',anchors()['parent_manifest_sha256'],proof_reader)
            return consumer_disclosures(CATALOG.root/'prior-catalog',parent,artifact,payload,proof_reader=proof_reader)
        from ..us_valuation.quality06_disclosures import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1':
        from ..us_valuation.quality05_admission import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY05-ADMITTED-RETENTION-CHILD-1':
        from ..us_valuation.quality05_admitted_retention import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY05-STAGED-INHERITANCE-1':
        from ..us_valuation.quality05_staged import TARGETS, CARRY_FORWARD, anchors, proof
        if artifact['issuer']['ticker'] not in TARGETS | CARRY_FORWARD:
            from ..us_valuation.quality04_admission import consumer_disclosures
            parent = proof(CATALOG.root,'approved-parent-manifest.json',anchors()['parent_manifest_sha256'],proof_reader)
            return consumer_disclosures(CATALOG.root/'prior-catalog',parent,artifact,payload,proof_reader=proof_reader)
        from ..us_valuation.quality05_disclosures import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1':
        from ..us_valuation.quality04_admission import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY04-STAGED-INHERITANCE-1':
        from ..us_valuation.quality04_staged import TARGETS, CARRY_FORWARD, anchors, proof
        if artifact['issuer']['ticker'] not in TARGETS | CARRY_FORWARD:
            from ..us_valuation.quality03_admission import consumer_disclosures
            parent = proof(CATALOG.root,'approved-parent-manifest.json',anchors()['parent_manifest_sha256'],proof_reader)
            return consumer_disclosures(CATALOG.root/'prior-catalog',parent,artifact,payload,proof_reader=proof_reader)
        from ..us_valuation.quality04_disclosures import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1':
        from ..us_valuation.quality03_admission import consumer_disclosures
        from ..us_valuation.approved_inheritance import _proof
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY03-STAGED-INHERITANCE-1':
        from ..us_valuation.quality03_staged import TARGETS, CARRY_FORWARD, anchors, proof
        from ..us_valuation.approved_inheritance import _proof
        if artifact['issuer']['ticker'] not in TARGETS | CARRY_FORWARD:
            from ..us_valuation.quality02_admission import consumer_disclosures
            parent = proof(CATALOG.root,'approved-parent-manifest.json',anchors()['parent_manifest_sha256'],proof_reader)
            return consumer_disclosures(CATALOG.root/'prior-catalog',parent,artifact,payload,proof_reader=proof_reader)
        from ..us_valuation.quality03_disclosures import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1':
        from ..us_valuation.quality02_admission import consumer_disclosures
        from ..us_valuation.approved_inheritance import _proof
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-QUALITY02-STAGED-INHERITANCE-1':
        from ..us_valuation.quality02_staged import TARGETS, CARRY_HELD, anchors, proof
        from ..us_valuation.approved_inheritance import _proof
        if artifact['issuer']['ticker'] not in TARGETS | CARRY_HELD:
            from ..us_valuation.quality_batches1115_admission import consumer_disclosures
            parent = proof(CATALOG.root,'approved-parent-manifest.json',anchors()['parent_manifest_sha256'],proof_reader)
            return consumer_disclosures(CATALOG.root/'prior-catalog',parent,artifact,payload,proof_reader=proof_reader)
        from ..us_valuation.quality02_disclosures import consumer_disclosures
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B1115-QUALITY-LOCAL-ADMISSION-INHERITANCE-1':
        from ..us_valuation.quality_batches1115_admission import consumer_disclosures
        from ..us_valuation.approved_inheritance import _proof
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B1115-QUALITY-STAGED-INHERITANCE-1':
        from ..us_valuation.quality_batches1115_staged import consumer_disclosures
        from ..us_valuation.approved_inheritance import _proof
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B11-B15-LOCAL-ADMISSION-INHERITANCE-1':
        from ..us_valuation.admitted_batches1115_inheritance import consumer_disclosures
        from ..us_valuation.approved_inheritance import _proof
        return consumer_disclosures(CATALOG.root,CATALOG.manifest,artifact,payload,proof_reader=proof_reader)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B11-B15-APPROVED-PARENT-INHERITANCE-1':
        from ..us_valuation.staged_batches1115_inheritance import consumer_disclosures
        return consumer_disclosures(artifact,payload)
    if _using_catalog() and CATALOG.manifest.get('private_review', {}).get('profile') == 'B11-B15-FROZEN-PRIVATE-1':
        from ..us_valuation.private_batches1115 import consumer_disclosures
        return consumer_disclosures(CATALOG.manifest, artifact, payload)
    return payload


@router.get("")
def list_us_valuations() -> dict:
    """List exactly the issuers bound by the selected immutable catalog."""
    items = []
    using_catalog = _using_catalog()
    sources = (
        [(entry, CATALOG.verify_artifact(entry.ticker)) for entry in CATALOG.entries]
        if using_catalog
        else [(None, path) for path in sorted(DATA_ROOT.glob("*.json"))]
    )
    for entry, path in sources:
        try:
            data = _public_artifact(path)
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
        items.append(_private_scope(data, summary))
    result = {"count": len(items), "items": items}
    if using_catalog:
        result.update(CATALOG.public_metadata())
    return result


@router.get("/{ticker}/calculator")
def get_us_valuation_calculator(ticker: str) -> dict:
    artifact = load_generated_result(ticker)
    if _uses_catalog_recipes():
        try:
            return _private_scope(artifact, latest_calculator.calculator_view(artifact, recipe=_load_recipe(ticker.upper())))
        except ValueError as exc:
            raise AppError("U.S. calculation recipe does not match the catalog", 500) from exc
    return _private_scope(artifact, calculator_view(artifact))


@router.post("/{ticker}/calculator")
def post_us_valuation_calculator(
    ticker: str, body: UsCalculatorInput, user: CurrentUser
) -> dict:
    if REVIEW_ONLY and body.save:
        raise AppError('Read-only catalog review cannot save valuations', 403)
    artifact = load_generated_result(ticker)
    try:
        if _uses_catalog_recipes():
            recipe = _load_recipe(ticker.upper())
            if (body.baseline_version != latest_calculator.baseline_version(artifact)
                    or (recipe is not None and body.recipe_version != recipe.get("recipe_version"))):
                raise AppError("Valuation changed; reload the calculator", 409)
            result = latest_calculator.calculate(
                artifact,
                overrides=body.overrides,
                manual_price=body.manual_price,
                recipe=recipe,
                selected_scenario=body.scenario,
            )
        else:
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
                **({
                    "baseline_version": result.get("baseline_version"),
                    "recipe_version": result.get("recipe_version"),
                } if _uses_catalog_recipes() else {}),
            },
        )
        result["saved_id"] = saved["id"]
    return _private_scope(artifact, result)


@router.get("/{ticker}/history")
def get_us_valuation_history(ticker: str) -> dict:
    normalized = ticker.upper()
    if not TICKER.fullmatch(normalized):
        raise AppError("Invalid ticker", 400)
    if normalized not in CATALOG.entry_by_ticker:
        raise AppError("U.S. valuation not available", 404)
    catalogs = [CATALOG]
    if _is_latest_500():
        base_version = CATALOG.manifest.get("base_catalog_version")
        if base_version != "US-RESET-2026-08-14-B01-B50-INITIAL-1.0":
            raise AppError("U.S. valuation history is invalid", 500)
        baseline = load_catalog(
            CATALOGS_ROOT / base_version,
            manifest_sha256=INITIAL_500_MANIFEST_SHA256,
        )
        catalogs.append(baseline)
    items = []
    for catalog in catalogs:
        if normalized not in catalog.entry_by_ticker:
            continue
        data = _public_artifact(
            catalog.verify_artifact(normalized), manifest_sha256=catalog.manifest_sha256
        )
        items.append(_private_scope(data, {
            "catalog_version": catalog.version,
            "valuation_date": data["valuation_date"],
            "availability_type": data["availability_type"],
            "scenario_range": data["scenario_range"],
            "source_financial_statement": data["source_financial_statement"],
        }))
    return {"ticker": normalized, "items": items}


@router.get("/{ticker}")
def get_us_valuation(ticker: str) -> dict:
    artifact = load_generated_result(ticker)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-B1620-ADMITTED-RETENTION-CHILD-1'}:
        return _private_scope(artifact, artifact)
    if _using_catalog() and CATALOG.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1':
        return _private_scope(artifact, artifact)
    if _using_catalog() and CATALOG.manifest.get('private_review', {}).get('profile') == 'B16-B20-FROZEN-PRIVATE-1':
        return _private_scope(artifact, artifact)
    if _using_catalog() and CATALOG.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-QUALITY06-STAGED-INHERITANCE-1','US-QUALITY06-OFFLINE-RETENTION-CHILD-1','US-QUALITY05-STAGED-INHERITANCE-1','US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY06-ADMITTED-RETENTION-CHILD-1','US-QUALITY05-ADMITTED-RETENTION-CHILD-1','US-QUALITY04-STAGED-INHERITANCE-1','US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY03-STAGED-INHERITANCE-1','US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1','US-QUALITY02-STAGED-INHERITANCE-1','US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1','US-B1115-QUALITY-STAGED-INHERITANCE-1','US-B1115-QUALITY-LOCAL-ADMISSION-INHERITANCE-1'}:
        return _private_scope(artifact,artifact)
    return artifact
