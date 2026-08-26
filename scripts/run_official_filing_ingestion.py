#!/usr/bin/env python3
"""Replay manifest-driven official filing ingestion from frozen source packets."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.filing_package import FilingPackageIncomplete
from app.us_valuation.official_filing_ingestion import (
    SCHEMA_VERSION,
    ingest_manifest,
    select_filing_pair,
)
from app.us_valuation.sec_client import normalize_cik


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _filing_rows(source_manifest: Mapping[str, Any], submissions: Mapping[str, Any]) -> list[dict[str, str]]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    by_accession: dict[str, dict[str, Any]] = {}
    if isinstance(accessions, list):
        for index, accession in enumerate(accessions):
            if not isinstance(accession, str):
                continue
            by_accession[accession] = {
                key: values[index]
                for key, values in recent.items()
                if isinstance(values, list) and index < len(values)
            }
    rows: list[dict[str, str]] = []
    for item in source_manifest.get("eligible_filings", []):
        if not isinstance(item, Mapping):
            continue
        accession = str(item.get("accession") or "")
        source = by_accession.get(accession, {})
        expected = {
            "form": item.get("form"),
            "filed": item.get("filed"),
            "primary_document": item.get("primary_document"),
        }
        actual = {
            "form": source.get("form"),
            "filed": source.get("filingDate"),
            "primary_document": source.get("primaryDocument"),
        }
        if actual != expected:
            raise ValueError(f"{accession}: source manifest conflicts with frozen submissions")
        report_date = source.get("reportDate")
        if not isinstance(report_date, str) or not report_date:
            raise ValueError(f"{accession}: report date absent from frozen submissions")
        rows.append(
            {
                "accession": accession,
                "form": str(item.get("form") or ""),
                "filed": str(item.get("filed") or ""),
                "report_date": report_date,
                "primary_document": str(item.get("primary_document") or ""),
            }
        )
    return rows


def _private_payload(path: Path) -> Mapping[str, Any]:
    raw = _json(path)
    if not isinstance(raw, Mapping):
        return {}
    diagnostic = raw.get("diagnostic_private")
    if isinstance(diagnostic, Mapping):
        return diagnostic
    practical = raw.get("practical_private")
    if isinstance(practical, Mapping):
        return practical
    strict = raw.get("strict_diagnostic")
    return strict if isinstance(strict, Mapping) else raw


def _availability(valuation_root: Path | None, ticker: str) -> Mapping[str, Any]:
    if valuation_root is None:
        return {}
    path = valuation_root / ticker / "valuation-private.json"
    if not path.is_file():
        return {}
    payload = _private_payload(path)
    availability = (
        payload.get("financials", {}).get("balance_sheet", {}).get("availability", {})
    )
    return availability if isinstance(availability, Mapping) else {}


def _model(valuation_root: Path | None, ticker: str) -> str:
    if valuation_root is None:
        return "official_evidence_only"
    path = valuation_root / ticker / "valuation-private.json"
    if not path.is_file():
        return "official_evidence_only"
    payload = _private_payload(path)
    primary = payload.get("model_policy", {}).get("primary")
    return str(primary or "official_evidence_only")


def _companyfacts_has_accession(companyfacts: Mapping[str, Any], accession: str) -> bool:
    facts = companyfacts.get("facts", {})
    if not isinstance(facts, Mapping):
        return False
    for namespace in facts.values():
        if not isinstance(namespace, Mapping):
            continue
        for concept in namespace.values():
            if not isinstance(concept, Mapping):
                continue
            for rows in concept.get("units", {}).values():
                if isinstance(rows, list) and any(
                    isinstance(row, Mapping) and row.get("accn") == accession for row in rows
                ):
                    return True
    return False


def build_manifest(
    *,
    source_root: Path,
    valuation_date: str,
    valuation_root: Path | None = None,
    partition_index: int = 0,
    partition_count: int = 1,
    tickers: tuple[str, ...] = (),
) -> dict[str, Any]:
    if partition_count <= 0 or not 0 <= partition_index < partition_count:
        raise ValueError("partition index/count are invalid")
    issuers: list[dict[str, Any]] = []
    for packet in sorted(path for path in source_root.iterdir() if path.is_dir()):
        manifest_path = packet / "source-manifest.json"
        submissions_path = packet / "submissions.json"
        companyfacts_path = packet / "companyfacts.json"
        if not all(path.is_file() for path in (manifest_path, submissions_path, companyfacts_path)):
            continue
        source_manifest = _json(manifest_path)
        submissions = _json(submissions_path)
        companyfacts = _json(companyfacts_path)
        cik = normalize_cik(submissions.get("cik", ""))
        ticker = packet.name.upper()
        if ticker not in (submissions.get("tickers") or []):
            raise ValueError(f"{ticker}: frozen submissions identity mismatch")
        filings = _filing_rows(source_manifest, submissions)
        controlling = select_filing_pair(
            filings, valuation_date=valuation_date
        ).controlling
        availability = _availability(valuation_root, ticker)
        model = _model(valuation_root, ticker)
        specialist_fields = {
            "residual_income": [
                "common_equity", "preferred_equity", "cet1_capital",
                "total_regulatory_capital", "risk_weighted_assets", "cet1_ratio",
                "loan_loss_allowance", "diluted_weighted_average_shares",
            ],
            "ddm": [
                "rate_base", "allowed_return", "utility_debt",
                "ownership_interest", "dividend_per_share",
                "diluted_weighted_average_shares",
            ],
            "ffo": [
                "ffo", "affo", "straight_line_rent_adjustment",
                "recurring_maintenance_capex", "occupancy", "preferred_equity",
                "diluted_weighted_average_shares",
            ],
        }
        fields = sorted(availability) if availability else specialist_fields.get(model, ["cash"])
        coverage: dict[str, dict[str, Any]] = {}
        for field in fields:
            record = availability.get(field, {}) if isinstance(availability, Mapping) else {}
            if (
                isinstance(record, Mapping)
                and record.get("source_accession") == controlling["accession"]
                and record.get("fallback_level") == "current_reported"
                and record.get("value") is not None
            ):
                coverage[field] = {
                    "value": record["value"],
                    "source_accession": record.get("source_accession"),
                    "period_end": record.get("period_end"),
                    "filed_date": controlling["filed"],
                }
        issuers.append(
            {
                "ticker": ticker,
                "cik": cik,
                "companyfacts": {
                    "accession": (
                        controlling["accession"]
                        if _companyfacts_has_accession(companyfacts, controlling["accession"])
                        else None
                    ),
                    "fields": coverage,
                },
                "filings": filings,
                "material_requests": [
                    {
                        "required_field": field,
                        "model": model,
                        "period_role": (
                            "regulatory_snapshot"
                            if model in {"residual_income", "ddm"}
                            and field not in {"dividend_per_share", "diluted_weighted_average_shares"}
                            else "operating_ttm"
                            if model == "ffo" and field not in {"preferred_equity", "diluted_weighted_average_shares"}
                            else "balance_sheet_snapshot"
                        ),
                        "materiality": "material",
                    }
                    for field in fields
                ],
            }
        )
    if not issuers:
        raise ValueError("no complete frozen issuer packets found")
    requested = {ticker.upper() for ticker in tickers}
    if requested:
        available = {issuer["ticker"] for issuer in issuers}
        unknown = requested - available
        if unknown:
            raise ValueError(f"requested ingestion tickers are unavailable: {sorted(unknown)}")
        issuers = [issuer for issuer in issuers if issuer["ticker"] in requested]
    return {
        "schema_version": SCHEMA_VERSION,
        "valuation_date": valuation_date,
        "issuers": issuers[partition_index::partition_count],
    }


class ExistingPackageCapture:
    def __init__(self, roots: Iterable[Path]) -> None:
        self.by_identity: dict[tuple[str, str], Path] = {}
        for root in roots:
            for manifest_path in Path(root).rglob("package-manifest.json"):
                manifest = _json(manifest_path)
                key = (normalize_cik(manifest.get("cik", "")), str(manifest.get("accession") or ""))
                entrypoint = manifest_path.parent / str(manifest.get("entrypoint_local_path") or "")
                if entrypoint.is_file():
                    self.by_identity.setdefault(key, entrypoint)

    def __call__(self, *, cik: str, accession: str, **_: Any) -> Path:
        entrypoint = self.by_identity.get((normalize_cik(cik), accession))
        if entrypoint is None:
            raise FilingPackageIncomplete(
                "OFFICIAL_PACKAGE_NOT_IN_FROZEN_CACHE",
                f"{normalize_cik(cik)} {accession}",
            )
        return entrypoint


class ExistingParsedParse:
    def __init__(self, roots: Iterable[Path]) -> None:
        self.by_accession: dict[str, dict[str, Any]] = {}
        for root in roots:
            for path in Path(root).glob("parsed/*/*.json"):
                raw = _json(path)
                payload = raw.get("parsed") if isinstance(raw, Mapping) else None
                if not isinstance(payload, Mapping):
                    payload = raw if isinstance(raw, Mapping) else None
                if isinstance(payload, Mapping):
                    self.by_accession.setdefault(path.stem, dict(payload))

    def __call__(self, entrypoint: Path, *, accession: str, **_: Any) -> dict[str, Any]:
        payload = self.by_accession.get(accession)
        if payload is None:
            raise ValueError(f"no immutable parsed cache for {accession}")
        return dict(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--valuation-root", type=Path)
    parser.add_argument("--valuation-date", required=True)
    parser.add_argument("--partition-index", type=int, default=0)
    parser.add_argument("--partition-count", type=int, default=1)
    parser.add_argument("--ticker", action="append", default=[])
    parser.add_argument("--existing-package-root", type=Path, action="append")
    parser.add_argument("--existing-parsed-root", type=Path, action="append")
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--sec-cache-root", type=Path)
    parser.add_argument("--requests-per-second", type=float, default=2.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    from app.us_valuation.arelle_adapter import parse_structural_filing

    manifest = build_manifest(
        source_root=args.source_root,
        valuation_date=args.valuation_date,
        valuation_root=args.valuation_root,
        partition_index=args.partition_index,
        partition_count=args.partition_count,
        tickers=tuple(args.ticker),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "input-manifest.json"
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != encoded:
        raise FileExistsError("refusing to overwrite another immutable input manifest")
    manifest_path.write_text(encoded, encoding="utf-8")
    ingest_args: dict[str, Any] = {
        "output_dir": args.output_dir,
        "parse": (
            ExistingParsedParse(args.existing_parsed_root)
            if args.existing_parsed_root
            else parse_structural_filing
        ),
        "protected_serving_roots": (
            ROOT / "backend/app/data/us_valuation_catalogs",
            ROOT / "frontend/public/data",
            ROOT / "frontend/src/research/generated",
        ),
    }
    if args.existing_package_root:
        ingest_args["package_capture"] = ExistingPackageCapture(args.existing_package_root)
    else:
        from app.us_valuation.sec_client import SecClient

        cache_root = args.sec_cache_root or args.output_dir.parent / ".official-evidence-sec-cache"
        ingest_args["client"] = SecClient(
            user_agent=args.user_agent,
            cache_dir=cache_root,
            requests_per_second=args.requests_per_second,
        )
    result = ingest_manifest(manifest, **ingest_args)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
