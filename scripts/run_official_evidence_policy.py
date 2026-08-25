#!/usr/bin/env python3
"""Resolve official evidence order against staged private valuation artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.evidence_policy import (
    SourceAttempt,
    project_decision_to_availability,
    resolve_evidence_order,
    source_attempt_from_decision,
)
from app.us_valuation.evidence_field_registry import load_field_registry
from app.us_valuation.evidence_router import route_evidence_model
from app.us_valuation.official_evidence import EvidenceDecision
from app.us_valuation.sec_client import sec_archive_url


SERVING_ROOTS = (
    ROOT / "backend/app/data/us_valuations",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _private(path: Path) -> Mapping[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    for key in ("diagnostic_private", "practical_private", "strict_diagnostic"):
        value = raw.get(key)
        if isinstance(value, Mapping):
            return value
    return raw


def _existing_attempt(
    record: Mapping[str, Any],
    *,
    filing_metadata: Mapping[str, Mapping[str, str]],
    controlling_filing: Mapping[str, str],
    cik: str,
    registry: Mapping[str, Any],
) -> SourceAttempt | None:
    accession = record.get("source_accession")
    period_end = record.get("period_end")
    if not isinstance(accession, str) or not accession or not isinstance(period_end, str) or not period_end:
        return None
    fallback = record.get("fallback_level")
    source = {
        "current_reported": "companyfacts_current",
        "current_structural": "exact_sec_filing",
        "reported_aggregate": "current_aggregate",
        "annual_carried_forward": "annual_carry_forward",
        "company_history": "company_history",
        "sector_estimate": "sector_range",
    }.get(fallback)
    if source is None:
        return None
    filing = filing_metadata.get(accession, {})
    field_name = str(record.get("field") or "")
    governed = registry.get(field_name)
    unit = governed.units[0] if governed is not None and governed.units else None
    state = record.get("state")
    uncertainty = record.get("uncertainty")
    if isinstance(uncertainty, Mapping) and uncertainty.get("low") is not None and uncertainty.get("high") is not None:
        status, value, low, high = "bounded_estimate", None, uncertainty["low"], uncertainty["high"]
    elif state in {"explicit_zero", "evidence_backed_zero", "not_applicable"}:
        status, value, low, high = "explicit_zero", 0.0, None, None
    elif state == "reported":
        status, value, low, high = (
            "reported_aggregate" if fallback == "reported_aggregate" else "reported",
            record.get("value"), None, None,
        )
    elif state == "stale":
        status, value, low, high = "stale", record.get("value") or 0.0, None, None
    else:
        status, value, low, high = "conflicting" if state == "conflict" else "unresolved", None, None, None
    lineage_complete = bool(
        filing.get("filed") and filing.get("primary_document") and unit
    )
    current_lineage = (
        accession == controlling_filing.get("accession")
        and period_end == controlling_filing.get("report_date")
    )
    fallback_eligible = True
    if source == "sector_range":
        fallback_eligible = (
            record.get("source_kind") == "sector_range"
            and record.get("evidence_class") == "bounded_estimate"
        )
    elif source == "company_history":
        fallback_eligible = record.get("source_kind") in {
            "company_history", "companyfacts", "practical_policy"
        }
    return SourceAttempt(
        source=source,
        status=status,
        value=value,
        low=low,
        high=high,
        eligible=(
            record.get("authority") == "production"
            and status not in {"stale", "unresolved", "conflicting"}
            and fallback_eligible
            and (
                source not in {"companyfacts_current", "exact_sec_filing", "current_aggregate"}
                or current_lineage
            )
            and (lineage_complete or source not in {"companyfacts_current", "exact_sec_filing", "current_aggregate"})
        ),
        accession=accession,
        period_end=period_end,
        reason_codes=(str(record.get("reason_code") or "EXISTING_AVAILABILITY_CHECKED"),),
        source_kind=str(record.get("source_kind") or "companyfacts"),
        filed_date=filing.get("filed"),
        source_age_days=record.get("source_age_days"),
        covered_fields=tuple(record.get("covered_fields") or ()),
        coverage_basis=record.get("coverage_basis"),
        coverage_source_facts=tuple(record.get("coverage_source_facts") or ()),
        economic_scope=record.get("economic_scope"),
        source_url=(
            sec_archive_url(cik, accession, filing["primary_document"])
            if filing.get("primary_document")
            else None
        ),
        unit=unit,
        entity_identifier=cik,
        consolidation_scope="consolidated_parent" if lineage_complete else None,
        candidate_id=f"existing:{accession}:{field_name}" if lineage_complete else None,
    )


def _table_index(payload: Mapping[str, Any]) -> dict[tuple[str, str], tuple[Mapping[str, Any], ...]]:
    staged: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for issuer in payload.get("issuers", []):
        for evidence in issuer.get("evidence", []):
            if evidence.get("status") == "reported":
                staged.setdefault((issuer["ticker"], evidence["required_field"]), []).append(evidence)
    return {
        key: tuple(sorted(values, key=lambda item: (
            str(item.get("source_accession") or ""),
            str(item.get("table_title") or ""),
            str(item.get("row_label") or ""),
            str(item.get("column_label") or ""),
        )))
        for key, values in staged.items()
    }


def run(
    *,
    ingestion_receipt: Path,
    table_receipt: Path,
    specialist_receipt: Path,
    valuation_root: Path,
) -> dict[str, Any]:
    ingestion = json.loads(ingestion_receipt.read_text(encoding="utf-8"))
    tables = _table_index(json.loads(table_receipt.read_text(encoding="utf-8")))
    specialist = json.loads(specialist_receipt.read_text(encoding="utf-8"))
    specialist_tickers = {
        item["ticker"] for item in specialist.get("banks", [])
    } | {specialist.get("utility", {}).get("ticker"), specialist.get("reit", {}).get("ticker")}
    registry = load_field_registry()
    specialist_fields = {
        "JPM": {
            "common_equity", "preferred_equity", "cet1_capital",
            "total_regulatory_capital", "risk_weighted_assets", "cet1_ratio",
            "loan_loss_allowance",
        },
        "BAC": {
            "common_equity", "preferred_equity", "cet1_capital",
            "total_regulatory_capital", "risk_weighted_assets", "cet1_ratio",
            "loan_loss_allowance",
        },
        "NEE": {"rate_base", "allowed_return", "utility_debt", "ownership_interest"},
        "O": {
            "ffo", "affo", "straight_line_rent_adjustment",
            "recurring_maintenance_capex", "occupancy", "preferred_equity",
            "diluted_weighted_average_shares",
        },
    }
    specialist_routes = {
        "JPM": ("bank_residual_income", "fr_y9c"),
        "BAC": ("bank_residual_income", "fr_y9c"),
        "NEE": ("regulated_utility", "ferc_form_1"),
        "O": ("reit", "sec_filed_exhibit_99_2"),
    }
    before = {str(root.resolve()): _tree_hash(root) for root in SERVING_ROOTS}
    cases: list[dict[str, Any]] = []
    statuses: Counter[str] = Counter()
    tiers: Counter[str] = Counter()
    projection_failures: Counter[str] = Counter()
    for issuer in ingestion["issuers"]:
        ticker = issuer["ticker"]
        private_path = valuation_root / ticker / "valuation-private.json"
        private = _private(private_path) if private_path.is_file() else {}
        availability = private.get("financials", {}).get("balance_sheet", {}).get("availability", {})
        model_policy = private.get("model_policy", {})
        filing_metadata = {
            item["accession"]: item
            for item in (issuer["controlling_filing"], issuer["latest_annual_filing"])
        }
        issuer_cases: list[dict[str, Any]] = []
        for raw_decision in issuer["decisions"]:
            evidence_decision = EvidenceDecision.from_dict(raw_decision)
            request = evidence_decision.request.as_dict()
            request["model_suitable"] = model_policy.get("primary", request["model"]) == request["model"]
            applicable_sources = {
                "companyfacts_current", "exact_sec_filing", "filing_table",
                "current_aggregate", "annual_carry_forward",
                "company_history", "sector_range",
            }
            attempts: list[SourceAttempt] = [
                source_attempt_from_decision(
                    evidence_decision,
                    source="exact_sec_filing",
                    eligible=evidence_decision.selected is not None,
                )
            ]
            for table in tables.get((ticker, evidence_decision.request.required_field), ()):
                table_eligible = table.get("consolidation_scope") == "consolidated_parent"
                attempts.append(
                    SourceAttempt(
                        source="filing_table",
                        status="explicit_zero" if table["value"] == 0 else "reported",
                        value=float(table["value"]) * float(table["scale"]),
                        low=None,
                        high=None,
                        eligible=table_eligible,
                        accession=table["source_accession"],
                        period_end=table["period_end"],
                        reason_codes=tuple(table["reason_codes"]) + (
                            () if table_eligible else ("TABLE_CONSOLIDATION_SCOPE_UNPROVEN",)
                        ),
                        source_kind="filing_table",
                        filed_date=table["filed_date"],
                        source_url=table["source_url"],
                        unit="USD",
                        entity_identifier=table["entity_identifier"],
                        consolidation_scope=table["consolidation_scope"],
                        candidate_id=(
                            f"table:{table['source_accession']}:{evidence_decision.request.required_field}:"
                            f"{table['search_scope_hash']}:{table.get('table_title')}:{table.get('row_label')}"
                        ),
                        package_sha256=table["package_sha256"],
                    )
                )
            existing = availability.get(evidence_decision.request.required_field) if isinstance(availability, Mapping) else None
            if isinstance(existing, Mapping):
                existing_attempt = _existing_attempt(
                    existing,
                    filing_metadata=filing_metadata,
                    controlling_filing=issuer["controlling_filing"],
                    cik=issuer["cik"],
                    registry=registry,
                )
                if existing_attempt is not None:
                    attempts.append(existing_attempt)
            if (
                ticker in specialist_tickers
                and evidence_decision.request.required_field in specialist_fields.get(ticker, set())
            ):
                family, source_kind = specialist_routes[ticker]
                route_evidence_model(
                    {"family": family, "model": request["model"]},
                    source_kind=source_kind,
                )
                applicable_sources.add("regulator_or_sec_supplement")
                attempts.append(
                    SourceAttempt(
                        source="regulator_or_sec_supplement",
                        status="unresolved",
                        value=None,
                        low=None,
                        high=None,
                        eligible=False,
                        accession=f"SPECIALIST-{ticker}-BLOCKER",
                        period_end=ingestion["valuation_date"],
                        reason_codes=("SPECIALIST_IDENTITY_OR_CONSOLIDATION_UNPROVEN",),
                        source_kind="specialist_blocker",
                    )
                )
            request["applicable_sources"] = sorted(applicable_sources)
            attempted_sources = {attempt.source for attempt in attempts}
            for missing_source in sorted(applicable_sources - attempted_sources, key=lambda item: {
                "companyfacts_current": 1, "exact_sec_filing": 2, "filing_table": 3,
                "regulator_or_sec_supplement": 4, "current_aggregate": 5,
                "annual_carry_forward": 6, "company_history": 7, "sector_range": 8,
            }[item]):
                attempts.append(
                    SourceAttempt(
                        source=missing_source,
                        status="unresolved",
                        value=None,
                        low=None,
                        high=None,
                        eligible=False,
                        accession=f"NO-{missing_source.upper()}-CANDIDATE",
                        period_end=ingestion["valuation_date"],
                        reason_codes=(f"NO_{missing_source.upper()}_CANDIDATE",),
                    )
                )
            policy = resolve_evidence_order(request, attempts)
            projection = None
            if policy.selected is not None:
                fallback = {
                    "companyfacts_current": "current_reported",
                    "exact_sec_filing": "current_structural",
                    "filing_table": "current_reported",
                    "regulator_or_sec_supplement": "current_reported",
                    "current_aggregate": "reported_aggregate",
                    "annual_carry_forward": "annual_carried_forward",
                    "company_history": "company_history",
                    "sector_range": "sector_estimate",
                }[policy.selected.source]
                try:
                    projection = project_decision_to_availability(
                        policy,
                        fallback_level=fallback,
                        source_attempt=policy.selected,
                    ).as_dict()
                except ValueError as error:
                    projection_failures[str(error)] += 1
            statuses[policy.status] += 1
            if policy.selected is not None:
                tiers[policy.selected.source] += 1
            issuer_cases.append(
                {
                    "request": request,
                    "attempts": [attempt.__dict__ for attempt in attempts],
                    "status": policy.status,
                    "selected_source": policy.selected.source if policy.selected else None,
                    "selected_value": policy.selected.value if policy.selected else None,
                    "selected_range": policy.selected_range,
                    "reason_codes": policy.reason_codes,
                    "exhausted": policy.exhaustion_receipt.exhausted,
                    "reliability_cap": policy.reliability_cap,
                    "availability_projection": projection,
                }
            )
        cases.append({"ticker": ticker, "cik": issuer["cik"], "decisions": issuer_cases})
    after = {str(root.resolve()): _tree_hash(root) for root in SERVING_ROOTS}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    return {
        "schema_version": "FINSIGHT-EVIDENCE-POLICY-1",
        "valuation_date": ingestion["valuation_date"],
        "issuer_count": len(cases),
        "request_count": sum(len(item["decisions"]) for item in cases),
        "status_counts": dict(sorted(statuses.items())),
        "selected_tier_counts": dict(sorted(tiers.items())),
        "projection_count": sum(
            decision["availability_projection"] is not None
            for item in cases for decision in item["decisions"]
        ),
        "projection_failure_counts": dict(sorted(projection_failures.items())),
        "serving_hash_before": before,
        "serving_hash_after": after,
        "serving_artifacts_changed": False,
        "issuers": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ingestion-receipt", required=True, type=Path)
    parser.add_argument("--table-receipt", required=True, type=Path)
    parser.add_argument("--specialist-receipt", required=True, type=Path)
    parser.add_argument("--valuation-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(
        ingestion_receipt=args.ingestion_receipt,
        table_receipt=args.table_receipt,
        specialist_receipt=args.specialist_receipt,
        valuation_root=args.valuation_root,
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output.exists() and args.output.read_text(encoding="utf-8") != encoded:
        raise FileExistsError("refusing to overwrite another evidence-policy receipt")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
