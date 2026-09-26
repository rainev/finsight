"""Stage a four-route PSE intrinsic refresh from reviewed local fact receipts.

This module never fetches sources, writes to Postgres/MinIO, or activates a catalog.
Receipt hashes attest to the reviewed JSON bytes, not to original filing bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from .catalog import CATALOG_SCHEMA, POINTER_SCHEMA, load_pointer
from .contract import PseValuationArtifact, ScenarioValue, sha256_object
from .models import distribution_valuation, fcff_valuation, residual_income_valuation, sotp_valuation


BUNDLE_SCHEMA = "PSE-V2-INTERNAL-REFRESH-BUNDLE-1.0"
RECEIPT_SCHEMA = "PSE-V2-INTERNAL-REVIEWED-FACTS-1.0"
MODEL_VERSION = "PSE-V2-INTERNAL-REFRESH-1.0"
PILOT_ROUTES = {
    "AP": "fcff_dcf",
    "BPI": "residual_income",
    "RCR": "sustainable_distributions",
    "RLC": "sotp",
}
SCENARIOS = ("bear", "base", "bull")
DEPENDENTS = {"RCR": ("RLC",)}
FACT_SCOPES = {
    "starting_fcff_php_millions": "consolidated",
    "cash_php_millions": "consolidated",
    "nonoperating_assets_php_millions": "parent_common_bridge",
    "debt_php_millions": "consolidated",
    "preferred_claims_php_millions": "parent_common_bridge",
    "minority_value_php_millions": "parent_common_bridge",
    "other_claims_php_millions": "parent_common_bridge",
    "shares_millions": "ordinary_common",
    "parent_common_equity_php_millions": "parent_common",
    "prior_parent_common_equity_php_millions": "parent_common",
    "net_income_to_parent_php_millions": "parent",
    "current_distribution_per_share": "ordinary_common",
    "quarterly_distributions_per_share": "ordinary_common",
    "parent_equity_php_millions": "parent",
    "investment_property_carrying_value_php_millions": "consolidated",
    "investment_property_fair_value_php_millions": "consolidated",
    "property_by_owner": "consolidated",
}


class RefreshHold(ValueError):
    """A single issuer lacks reviewed inputs; preserve its active artifact."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _number(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise RefreshHold(f"{label} must be a finite number")
    result = float(value)
    if positive and result <= 0 or nonnegative and result < 0:
        raise RefreshHold(f"{label} has an invalid sign")
    return result


def _required(mapping: dict[str, Any], keys: set[str], label: str) -> None:
    missing = sorted(keys - set(mapping))
    if missing:
        raise RefreshHold(f"{label} missing: {', '.join(missing)}")


def _iso_date(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise RefreshHold(f"{label} must be an ISO date") from exc


def _reviewed_receipt(raw: bytes, ticker: str, valuation_date: date) -> dict[str, Any]:
    try:
        receipt = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{ticker}: reviewed receipt is invalid JSON") from exc
    if not isinstance(receipt, dict) or receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise ValueError(f"{ticker}: unsupported reviewed receipt")
    if receipt.get("ticker") != ticker:
        raise ValueError(f"{ticker}: receipt ticker differs")
    if receipt.get("trigger") not in {"new_filing", "amended_filing", "approved_assumptions"}:
        raise RefreshHold(f"{ticker}: a reviewed refresh trigger is required")
    for key in ("reviewer", "filing_period"):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            raise RefreshHold(f"{ticker}: {key} is required")
    period_end = _iso_date(receipt.get("period_end"), f"{ticker} period_end")
    published = _iso_date(receipt.get("filing_published_at"), f"{ticker} filing_published_at")
    reviewed = _iso_date(receipt.get("reviewed_at"), f"{ticker} reviewed_at")
    if period_end > published or published > valuation_date or reviewed > valuation_date:
        raise RefreshHold(f"{ticker}: filing/review dates are inconsistent with valuation date")
    source = receipt.get("source")
    facts = receipt.get("facts")
    provenance = receipt.get("fact_provenance")
    assumptions = receipt.get("assumptions")
    if not all(isinstance(item, dict) for item in (source, facts, provenance, assumptions)):
        raise RefreshHold(f"{ticker}: source, facts, provenance, and assumptions are required")
    if not isinstance(source.get("label"), str) or not source["label"].strip():
        raise RefreshHold(f"{ticker}: source label is required")
    for key in ("identifier", "form"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise RefreshHold(f"{ticker}: source {key} is required")
    source_documents = receipt.get("source_documents")
    if source_documents is not None:
        if not isinstance(source_documents, list) or not source_documents:
            raise RefreshHold(f"{ticker}: source_documents must list reviewed sources")
        identifiers = set()
        for document in source_documents:
            if not isinstance(document, dict) or not all(
                isinstance(document.get(key), str) and document[key].strip()
                for key in ("identifier", "label", "url")
            ):
                raise RefreshHold(f"{ticker}: each reviewed source needs an identifier, label, and URL")
            if document["identifier"] in identifiers:
                raise RefreshHold(f"{ticker}: duplicate source identifier")
            identifiers.add(document["identifier"])
    return receipt


def _fact_provenance(receipt: dict[str, Any], names: set[str]) -> None:
    facts = receipt["facts"]
    provenance = receipt["fact_provenance"]
    _required(facts, names, "reviewed facts")
    _required(provenance, names, "fact provenance")
    source_documents = receipt.get("source_documents")
    known_sources = {row["identifier"] for row in source_documents} if source_documents else None
    for name in names:
        row = provenance[name]
        if not isinstance(row, dict) or not all(
            isinstance(row.get(field), str) and row[field].strip()
            for field in ("unit", "scope")
        ):
            raise RefreshHold(f"{name}: unit and scope provenance are required")
        if _iso_date(row.get("period_end"), f"{name} period_end") > _iso_date(receipt["filing_published_at"], "filing_published_at"):
            raise RefreshHold(f"{name}: fact date follows the filing publication date")
        expected_unit = (
            "shares_millions" if name == "shares_millions" else
            "PHP_per_share" if name in {"current_distribution_per_share", "quarterly_distributions_per_share"} else
            "PHP_millions"
        )
        if row["unit"] != expected_unit:
            raise RefreshHold(f"{name}: expected normalized unit {expected_unit}")
        if row["scope"] != FACT_SCOPES[name]:
            raise RefreshHold(f"{name}: expected consolidation scope {FACT_SCOPES[name]}")
        page = row.get("source_page")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise RefreshHold(f"{name}: reviewed source_page is required")
        if known_sources is not None:
            identifiers = row.get("source_identifiers")
            if not isinstance(identifiers, list) or not identifiers or any(
                not isinstance(identifier, str) or identifier not in known_sources for identifier in identifiers
            ):
                raise RefreshHold(f"{name}: fact sources must match the reviewed source set")


def _assumptions(receipt: dict[str, Any], model: str, valuation_date: date) -> tuple[dict, dict]:
    block = receipt["assumptions"]
    if not isinstance(block.get("policy_version"), str) or not block["policy_version"]:
        raise RefreshHold("versioned model policy is required")
    if not isinstance(block.get("reviewer"), str) or not block["reviewer"].strip():
        raise RefreshHold("model assumptions need a reviewer")
    if _iso_date(block.get("reviewed_at"), "assumptions reviewed_at") > valuation_date:
        raise RefreshHold("model assumption review follows valuation date")
    scenarios = block.get("scenario_assumptions")
    if not isinstance(scenarios, dict) or set(scenarios) != set(SCENARIOS):
        raise RefreshHold("bear/base/bull assumption records are required")
    expected = {
        "fcff_dcf": {"growth_rate", "roic", "wacc", "terminal_growth", "terminal_roic"},
        "residual_income": {"current_roe", "terminal_roe", "cost_of_equity", "payout_ratio", "terminal_growth"},
        "sustainable_distributions": {"explicit_growth", "cost_of_equity", "terminal_growth"},
        "sotp": {"uplift_realization", "tax_leakage"},
    }[model]
    parsed: dict[str, dict[str, float]] = {}
    for name in SCENARIOS:
        row = scenarios[name]
        if not isinstance(row, dict) or set(row) != expected:
            raise RefreshHold(f"{name}: expected {model} assumptions are incomplete")
        parsed[name] = {key: _number(value, f"{name}.{key}") for key, value in row.items()}
    if model != "sotp":
        macro = block.get("macro_snapshot")
        if not isinstance(macro, dict) or not all(
            isinstance(macro.get(key), str) and macro[key].strip()
            for key in ("version", "reviewer", "benchmark_source")
        ):
            raise RefreshHold("reviewed dated macro snapshot is required")
        if macro.get("benchmark_kind") != "ten_year_government_bond":
            raise RefreshHold("the ten-year benchmark cannot be replaced by another series")
        observed = _iso_date(macro.get("observed_at"), "macro observed_at")
        reviewed = _iso_date(macro.get("reviewed_at"), "macro reviewed_at")
        if observed > reviewed or reviewed > valuation_date:
            raise RefreshHold("macro observation/review dates are inconsistent")
        if (valuation_date - observed).days > 90 and not macro.get("carry_forward_reason"):
            raise RefreshHold("stale benchmark requires an explicit carry-forward decision")
        _number(macro.get("benchmark_yield"), "benchmark_yield", positive=True)
    else:
        macro = {}
    return parsed, macro


def _model_result(model: str, receipt: dict, scenario: dict[str, float]) -> dict[str, Any]:
    facts = receipt["facts"]
    years = receipt["assumptions"].get("forecast_years", 5)
    if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 30:
        raise RefreshHold("forecast_years must be between 1 and 30")
    if model == "fcff_dcf":
        required = {
            "starting_fcff_php_millions", "cash_php_millions", "nonoperating_assets_php_millions",
            "debt_php_millions", "preferred_claims_php_millions", "minority_value_php_millions",
            "other_claims_php_millions", "shares_millions",
        }
        _fact_provenance(receipt, required)
        inputs = {key: _number(facts[key], key, positive=key in {"starting_fcff_php_millions", "shares_millions"}, nonnegative=key not in {"starting_fcff_php_millions", "shares_millions"}) for key in required}
        reinvestment = scenario["growth_rate"] / scenario["roic"]
        if not 0 <= reinvestment < 1:
            raise RefreshHold("FCFF growth/ROIC implies invalid starting reinvestment")
        return fcff_valuation(
            starting_nopat=inputs["starting_fcff_php_millions"] / (1 - reinvestment),
            shares_outstanding=inputs["shares_millions"], forecast_years=years,
            cash=inputs["cash_php_millions"], nonoperating_assets=inputs["nonoperating_assets_php_millions"],
            debt=inputs["debt_php_millions"], preferred_claims=inputs["preferred_claims_php_millions"],
            minority_value=inputs["minority_value_php_millions"], other_claims=inputs["other_claims_php_millions"],
            **scenario,
        )
    if model == "residual_income":
        required = {"parent_common_equity_php_millions", "prior_parent_common_equity_php_millions", "net_income_to_parent_php_millions", "shares_millions"}
        _fact_provenance(receipt, required)
        inputs = {key: _number(facts[key], key, positive=key != "net_income_to_parent_php_millions") for key in required}
        return residual_income_valuation(
            opening_common_equity=inputs["parent_common_equity_php_millions"],
            shares_outstanding=inputs["shares_millions"], forecast_years=years, **scenario,
        )
    if model == "sustainable_distributions":
        required = {"current_distribution_per_share", "shares_millions", "quarterly_distributions_per_share"}
        _fact_provenance(receipt, required)
        payout = _number(facts["current_distribution_per_share"], "current_distribution_per_share", positive=True)
        _number(facts["shares_millions"], "shares_millions", positive=True)
        quarters = facts["quarterly_distributions_per_share"]
        if not isinstance(quarters, dict) or len(quarters) != 4:
            raise RefreshHold("four dated quarterly distributions are required")
        quarterly_sum = sum(_number(value, f"quarterly {name}", nonnegative=True) for name, value in quarters.items())
        if abs(quarterly_sum - payout) > 1e-8:
            raise RefreshHold("current payout does not reconcile to the four quarters")
        return distribution_valuation(
            current_distribution_per_share=payout, forecast_years=years, **scenario,
        )
    required = {
        "parent_equity_php_millions", "preferred_claims_php_millions", "shares_millions",
        "investment_property_carrying_value_php_millions", "investment_property_fair_value_php_millions",
        "property_by_owner",
    }
    _fact_provenance(receipt, required)
    parent = _number(facts["parent_equity_php_millions"], "parent_equity", positive=True)
    shares = _number(facts["shares_millions"], "shares_millions", positive=True)
    claims = _number(facts["preferred_claims_php_millions"], "preferred_claims", nonnegative=True)
    carrying = _number(facts["investment_property_carrying_value_php_millions"], "property carrying", positive=True)
    fair = _number(facts["investment_property_fair_value_php_millions"], "property fair value", positive=True)
    rows = facts["property_by_owner"]
    if not isinstance(rows, list) or not rows:
        raise RefreshHold("property-by-owner bridge is required")
    components = [{"name": "reported_parent_equity", "equity_value": parent, "ownership": 1.0}]
    sum_carrying = sum_fair = 0.0
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"]:
            raise RefreshHold("each property owner needs a name")
        if isinstance(row.get("source_page"), bool) or not isinstance(row.get("source_page"), int) or row["source_page"] < 1:
            raise RefreshHold("each property owner needs a source page")
        owned_carrying = _number(row.get("carrying_value_php_millions"), "owner carrying", nonnegative=True)
        owned_fair = _number(row.get("fair_value_php_millions"), "owner fair value", nonnegative=True)
        ownership = _number(row.get("ownership"), "ownership", nonnegative=True)
        if ownership > 1:
            raise RefreshHold("ownership exceeds 100%")
        sum_carrying += owned_carrying
        sum_fair += owned_fair
        components.append({
            "name": row["name"], "equity_value": (owned_fair - owned_carrying) * scenario["uplift_realization"] * (1 - scenario["tax_leakage"]),
            "ownership": ownership,
        })
    if abs(sum_carrying - carrying) > 0.01 or abs(sum_fair - fair) > 0.01:
        raise RefreshHold("property-by-owner bridge does not reconcile to consolidated carrying/fair values")
    return sotp_valuation(components=components, shares_outstanding=shares, other_parent_claims=claims)


def build_refresh_artifact(parent: PseValuationArtifact, receipt: dict, receipt_sha256: str, valuation_date: date) -> PseValuationArtifact:
    ticker = parent.ticker
    model = PILOT_ROUTES[ticker]
    if parent.primary_model != model or parent.availability_type != "intrinsic_valuation":
        raise ValueError(f"{ticker}: active model route is not the pilot intrinsic route")
    scenarios, macro = _assumptions(receipt, model, valuation_date)
    results: dict[str, ScenarioValue] = {}
    for name in SCENARIOS:
        try:
            valued = _model_result(model, receipt, scenarios[name])
        except (KeyError, TypeError, ZeroDivisionError, ValueError) as exc:
            raise RefreshHold(f"{ticker} {name}: {exc}") from exc
        value = _number(valued["value_per_share"], f"{ticker} {name} value", positive=True)
        equity = value * _number(receipt["facts"]["shares_millions"], "shares_millions", positive=True)
        results[name] = ScenarioValue(
            value_per_share=value,
            common_equity_value=equity,
            enterprise_value=valued.get("enterprise_value"),
        )
    facts = receipt["facts"]
    public_assumptions: dict[str, Any] = {
        "policy_version": receipt["assumptions"]["policy_version"],
        "forecast_years": receipt["assumptions"].get("forecast_years", 5),
        "scenario_assumptions": scenarios,
        "reliability": "Pending refreshed-filing review",
        "refresh_receipt_sha256": receipt_sha256,
    }
    if macro:
        public_assumptions["macro_snapshot_version"] = macro["version"]
        public_assumptions["macro_observed_at"] = macro["observed_at"]
    if model == "fcff_dcf":
        public_assumptions["normalized_fcff_proxy_php_millions"] = facts["starting_fcff_php_millions"]
        public_assumptions["capital_bridge"] = {key: facts[key] for key in (
            "cash_php_millions", "nonoperating_assets_php_millions", "debt_php_millions",
            "preferred_claims_php_millions", "minority_value_php_millions", "other_claims_php_millions", "shares_millions",
        )}
    elif model == "residual_income":
        public_assumptions["book_value_per_share"] = facts["parent_common_equity_php_millions"] / facts["shares_millions"]
        public_assumptions["normalized_roe"] = facts["net_income_to_parent_php_millions"] / (
            (facts["parent_common_equity_php_millions"] + facts["prior_parent_common_equity_php_millions"]) / 2
        )
    elif model == "sustainable_distributions":
        public_assumptions["current_distribution_per_share"] = facts["current_distribution_per_share"]
        public_assumptions["shares_millions"] = facts["shares_millions"]
    else:
        public_assumptions["nav_bridge"] = {key: facts[key] for key in (
            "parent_equity_php_millions", "preferred_claims_php_millions", "shares_millions",
            "investment_property_carrying_value_php_millions", "investment_property_fair_value_php_millions",
            "property_by_owner",
        )}
    source = receipt["source"]
    source_ref = {
        "document_id": receipt_sha256[:16],
        "label": f"{source['label']} (reviewed fact receipt; original filing not captured)",
        "form": source.get("form"),
        "period_end": receipt["period_end"],
        "published_at": receipt["filing_published_at"],
        "url": None,
        "source_page": source.get("source_page"),
        "sha256": receipt_sha256,
    }
    payload = parent.model_dump(mode="json")
    payload.update({
        "model_version": MODEL_VERSION,
        "valuation_date": valuation_date.isoformat(),
        "filing_period": receipt["filing_period"],
        "filing_published_at": receipt["filing_published_at"],
        "price": None,
        "publication_state": "provisional",
        "scenarios": {key: value.model_dump() for key, value in results.items()},
        "numerical_range": {"low": min(value.value_per_share for value in results.values()), "high": max(value.value_per_share for value in results.values())},
        "market_relative": None,
        "public_assumptions": public_assumptions,
        "sources": [source_ref],
        "warnings": [
            "Staged internal refresh candidate; requires separate source, accounting, assumption, and activation review.",
            "Source hash binds a reviewer-supplied fact receipt, not original filing bytes; original-file rights and capture are unresolved.",
        ],
        "blocking_reasons": [],
        "input_hash": sha256_object({
            "receipt_sha256": receipt_sha256, "model_version": MODEL_VERSION,
            "ticker": ticker, "parent_artifact_hash": parent.artifact_hash,
        }),
        "artifact_hash": None,
    })
    return PseValuationArtifact.model_validate(payload).with_artifact_hash()


def _write_json(path: Path, value: dict) -> bytes:
    raw = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def stage_internal_refresh(bundle_path: Path, output_root: Path, catalogs_root: Path) -> Path:
    """Stage a complete candidate outside serving, retaining all unrefreshed bytes."""
    catalogs_root = catalogs_root.resolve()
    output_root = output_root.resolve()
    if output_root == catalogs_root or catalogs_root in output_root.parents or output_root in catalogs_root.parents:
        raise ValueError("output must not overlap the serving catalog root")
    if output_root.exists():
        raise FileExistsError(f"stage output already exists: {output_root}")
    bundle_path = bundle_path.resolve()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict) or bundle.get("schema_version") != BUNDLE_SCHEMA:
        raise ValueError("unsupported internal refresh bundle")
    version = bundle.get("catalog_version")
    if not isinstance(version, str) or not re.fullmatch(r"PSE-V2-REFRESH-[A-Za-z0-9._-]+", version):
        raise ValueError("invalid refresh catalog version")
    valuation_date = _iso_date(bundle.get("valuation_date"), "valuation_date")
    cases = bundle.get("cases")
    if not isinstance(cases, dict) or set(cases) != set(PILOT_ROUTES):
        raise ValueError("pilot bundle must state AP, BPI, RCR, and RLC exactly")
    active_pointer_raw = (catalogs_root / "active.json").read_bytes()
    active = load_pointer(catalogs_root, "active.json")
    if active.manifest_sha256 != bundle.get("active_manifest_sha256"):
        raise ValueError("active catalog differs from the reviewed parent")
    parent_manifest_raw = (active.root / "manifest.json").read_bytes()
    if active.status != "active" or len(active.entries) != 282 or _sha256(parent_manifest_raw) != active.manifest_sha256:
        raise ValueError("expected the confirmed 282-entry active catalog")
    catalog_root = output_root / version
    changes: dict[str, PseValuationArtifact] = {}
    holds: dict[str, str] = {}
    receipts: dict[str, bytes] = {}
    for ticker in PILOT_ROUTES:
        case = cases[ticker]
        if not isinstance(case, dict) or case.get("status") not in {"ready", "hold"}:
            raise ValueError(f"{ticker}: case must be ready or hold")
        if case["status"] == "hold":
            reason = case.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"{ticker}: hold requires a reason")
            holds[ticker] = reason
            continue
        relative = case.get("receipt_path")
        digest = case.get("receipt_sha256")
        if not isinstance(relative, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{ticker}: pinned local receipt path and SHA-256 are required")
        safe = PurePosixPath(relative)
        if safe.is_absolute() or not safe.parts or any(part in {".", ".."} for part in safe.parts):
            raise ValueError(f"{ticker}: receipt path is unsafe")
        path = (bundle_path.parent / Path(*safe.parts)).resolve()
        if bundle_path.parent not in path.parents:
            raise ValueError(f"{ticker}: receipt must be inside the bundle directory")
        raw = path.read_bytes()
        if _sha256(raw) != digest:
            raise ValueError(f"{ticker}: reviewed receipt hash mismatch")
        receipt = _reviewed_receipt(raw, ticker, valuation_date)
        parent_path = active.verify_artifact(ticker)
        parent = PseValuationArtifact.model_validate_json(parent_path.read_bytes())
        try:
            if receipt["trigger"] == "new_filing":
                prior_periods = [source.period_end for source in parent.sources if source.period_end]
                if not prior_periods and isinstance(parent.filing_period, str):
                    prior_fy = re.fullmatch(r"FY (\d{4})", parent.filing_period)
                    if prior_fy:
                        prior_periods = [f"{prior_fy.group(1)}-12-31"]
                if prior_periods and receipt["period_end"] <= max(prior_periods):
                    raise RefreshHold(f"{ticker}: new filing period is not newer than the active source")
            if parent.model_version == MODEL_VERSION and parent.public_assumptions.get("refresh_receipt_sha256") == digest:
                raise RefreshHold(f"{ticker}: reviewed input is already active")
            changes[ticker] = build_refresh_artifact(parent, receipt, digest, valuation_date)
            receipts[ticker] = raw
        except RefreshHold as exc:
            holds[ticker] = str(exc)
    if not changes:
        raise RefreshHold(f"no pilot issuer has a complete reviewed rerun; no candidate was written; holds: {holds}")
    dependency_holds = sorted(
        parent for child, parents in DEPENDENTS.items() if child in changes
        for parent in parents if parent not in changes
    )
    parent_entries = {entry.ticker: entry for entry in active.entries}
    manifest_entries = []
    report_changes = {}
    for ticker in sorted(parent_entries):
        old_entry = parent_entries[ticker]
        old_raw = active.verify_artifact(ticker).read_bytes()
        target = catalog_root / "artifacts" / f"{ticker}.json"
        if ticker in changes:
            artifact = changes[ticker]
            raw = _write_json(target, artifact.model_dump(mode="json"))
            old = PseValuationArtifact.model_validate_json(old_raw)
            old_base = old.scenarios["base"].value_per_share
            new_base = artifact.scenarios["base"].value_per_share
            movement = new_base / old_base - 1
            report_changes[ticker] = {
                "old_base_php_per_share": old_base,
                "new_base_php_per_share": new_base,
                "change_pct": movement,
                "attribution_required": abs(movement) > 0.2,
                "filing_period": artifact.filing_period,
                "filing_published_at": artifact.filing_published_at,
                "policy_version": artifact.public_assumptions["policy_version"],
                "old_artifact_sha256": old_entry.artifact_sha256,
                "new_artifact_sha256": _sha256(raw),
                "reviewed_receipt_sha256": _sha256(receipts[ticker]),
            }
            (catalog_root / "receipts").mkdir(parents=True, exist_ok=True)
            (catalog_root / "receipts" / f"{ticker}.json").write_bytes(receipts[ticker])
            entry = {
                "ticker": ticker, "availability_type": artifact.availability_type,
                "publication_state": artifact.publication_state, "primary_model": artifact.primary_model,
                "artifact_sha256": _sha256(raw), "source_audit": "internal_reviewed_fact_receipt",
            }
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(old_raw)
            entry = {
                "ticker": ticker, "availability_type": old_entry.availability_type,
                "publication_state": old_entry.publication_state, "primary_model": old_entry.primary_model,
                "artifact_sha256": old_entry.artifact_sha256, "source_audit": old_entry.source_audit,
            }
        manifest_entries.append(entry)
    inherited_evidence = active.root / "evidence"
    if inherited_evidence.exists():
        for path in sorted(inherited_evidence.rglob("*")):
            if path.is_symlink():
                raise ValueError("active evidence contains an unsafe symlink")
            if path.is_file():
                target = catalog_root / "evidence" / path.relative_to(inherited_evidence)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
    availability = {key: sum(row["availability_type"] == key for row in manifest_entries) for key in ("intrinsic_valuation", "market_relative_only", "not_available")}
    publication = {key: sum(row["publication_state"] == key for row in manifest_entries) for key in ("approved", "provisional", "blocked")}
    manifest = {
        "schema_version": CATALOG_SCHEMA, "catalog_version": version,
        "universe_version": active.universe_version, "valuation_date": valuation_date.isoformat(),
        "catalog_status": "staged", "artifact_count": len(manifest_entries),
        "availability_counts": availability, "publication_counts": publication,
        "refresh_parent": {"catalog_version": active.version, "manifest_sha256": active.manifest_sha256},
        "entries": manifest_entries,
    }
    manifest_raw = _write_json(catalog_root / "manifest.json", manifest)
    _write_json(output_root / "staged.json", {
        "schema_version": POINTER_SCHEMA, "status": "staged", "catalog_version": version,
        "catalog_path": version, "manifest_sha256": _sha256(manifest_raw),
    })
    _write_json(output_root / "refresh_report.json", {
        "schema_version": BUNDLE_SCHEMA, "catalog_version": version,
        "active_parent_catalog": active.version, "active_parent_manifest_sha256": active.manifest_sha256,
        "changed": report_changes, "holds": holds, "dependency_holds": dependency_holds,
        "activation_ready": False,
        "note": "Calculation-only staged candidate. No source rights, accounting approval, or activation is inferred.",
    })
    staged = load_pointer(output_root)
    if staged.status != "staged" or len(staged.entries) != len(active.entries):
        raise ValueError("staged catalog failed exact round-trip")
    if (catalogs_root / "active.json").read_bytes() != active_pointer_raw or (active.root / "manifest.json").read_bytes() != parent_manifest_raw:
        raise ValueError("active serving changed during staging")
    return catalog_root
