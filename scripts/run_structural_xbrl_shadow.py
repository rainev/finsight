#!/usr/bin/env python3
"""Run non-publishing structural XBRL diagnostics for withheld valuation artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping


_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_DIR = _REPO_ROOT / "backend"
_DEFAULT_DATA_ROOT = _BACKEND_DIR / "app" / "data" / "us_valuations"
_DEFAULT_OUTPUT_ROOT = _REPO_ROOT / "output" / "structural-xbrl-shadow"
_PROTECTED_OUTPUT_ROOTS = (
    _DEFAULT_DATA_ROOT,
    _REPO_ROOT / "frontend" / "public" / "data",
)
_MARKETABLE_SECURITIES_FIELDS = frozenset(
    {"marketable_securities_current", "marketable_securities_noncurrent"}
)
_CANONICAL_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")
_COUNTER_NAMES = (
    "discovered",
    "eligible",
    "parsed",
    "accepted_shadow",
    "review",
    "rejected",
    "unresolved",
    "parser_failed",
    "skipped",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=_DEFAULT_DATA_ROOT)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=_DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--ticker", action="append", default=[], help="repeatable optional filter")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--user-agent")
    return parser


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _artifact_ticker(artifact: Mapping[str, Any], path: Path) -> str:
    ticker = artifact.get("ticker")
    if isinstance(ticker, str) and ticker:
        return _validate_ticker(ticker)
    issuer_ticker = _mapping(artifact.get("issuer")).get("ticker")
    if isinstance(issuer_ticker, str) and issuer_ticker:
        return _validate_ticker(issuer_ticker)
    return _validate_ticker(path.stem)


def _validate_ticker(value: str) -> str:
    if not _CANONICAL_TICKER.fullmatch(value):
        raise ValueError("ticker must be a canonical uppercase symbol")
    return value


def _is_withheld(artifact: Mapping[str, Any]) -> bool:
    return _mapping(artifact.get("review")).get("publication_state") == "withheld"


def _controlling_filing(artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    financials = _mapping(artifact.get("financials"))
    return _mapping(_mapping(financials.get("ttm")).get("controlling_filing"))


def _marketable_securities_gaps(artifact: Mapping[str, Any]) -> tuple[str, ...]:
    financials = _mapping(artifact.get("financials"))
    balance_sheet = _mapping(financials.get("balance_sheet"))
    missing = balance_sheet.get("bridge_missing_fields")
    if not isinstance(missing, (list, tuple)):
        return ()
    return tuple(
        field
        for field in missing
        if isinstance(field, str) and field in _MARKETABLE_SECURITIES_FIELDS
    )


def _write_immutable_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != encoded:
            raise RuntimeError(f"Refusing to overwrite immutable shadow report: {path}")


def _ensure_separate_output(data_root: Path, output_root: Path) -> None:
    resolved_output = output_root.resolve()
    protected_roots = (data_root, *_PROTECTED_OUTPUT_ROOTS)
    if any(
        resolved_output.is_relative_to(protected_root.resolve())
        for protected_root in protected_roots
    ):
        raise ValueError("output-root must not be inside protected project data")


def _iter_withheld_artifacts(
    data_root: Path, ticker_filter: set[str]
) -> Iterable[tuple[Path, dict[str, Any]]]:
    for path in sorted(data_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or not _is_withheld(payload):
            continue
        ticker = _artifact_ticker(payload, path)
        if ticker_filter and ticker.upper() not in ticker_filter:
            continue
        yield path, payload


def _failure_report(
    artifact: Mapping[str, Any], *, ticker: str, error: Exception
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "cik": _mapping(artifact.get("issuer")).get("cik"),
        "valuation_date": artifact.get("valuation_date"),
        "controlling_filing": dict(_controlling_filing(artifact)),
        "existing_field_state": {
            field: _mapping(
                _mapping(_mapping(artifact.get("financials")).get("balance_sheet")).get(
                    "field_states"
                )
            ).get(field)
            for field in _marketable_securities_gaps(artifact)
        },
        "parser_diagnostics": [],
        "decisions": [],
        "skipped_fields": [],
        "parser_failure": str(error),
        "publication_effect": "none_shadow_only",
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _ensure_separate_output(args.data_root, args.output_root)

    # Imports below this line deliberately keep --help independent of Arelle.
    sys.path.insert(0, str(_BACKEND_DIR))
    from app.us_valuation.arelle_adapter import parse_structural_filing
    from app.us_valuation.filing_package import cache_structural_filing_package
    from app.us_valuation.sec_client import SecClient
    from app.us_valuation.structural_shadow import (
        evaluate_shadow_case,
        shadow_requests_from_artifact,
    )

    summary = {counter: 0 for counter in _COUNTER_NAMES}
    ticker_filter = {ticker.upper() for ticker in args.ticker}
    client = SecClient(user_agent=args.user_agent, cache_dir=args.cache_dir)
    for path, artifact in _iter_withheld_artifacts(args.data_root, ticker_filter):
        summary["discovered"] += 1
        ticker = _artifact_ticker(artifact, path)
        if not _marketable_securities_gaps(artifact):
            summary["skipped"] += 1
            continue
        summary["eligible"] += 1
        controlling_filing = _controlling_filing(artifact)
        try:
            requests = shadow_requests_from_artifact(artifact)
            cik = _mapping(artifact.get("issuer")).get("cik")
            accession = controlling_filing.get("accession")
            primary_document = controlling_filing.get("primary_document")
            if not isinstance(cik, str) or not cik:
                raise ValueError("artifact CIK is required")
            if not isinstance(accession, str) or not accession:
                raise ValueError("controlling accession is required")
            if not isinstance(primary_document, str) or not primary_document:
                raise ValueError("controlling primary document is required")
            entrypoint = cache_structural_filing_package(
                client,
                cik=cik,
                accession=accession,
                primary_document=primary_document,
                output_dir=args.cache_dir / "structural-filings",
                refresh=args.refresh,
            )
            filing = parse_structural_filing(entrypoint, accession=accession)
            report = evaluate_shadow_case(artifact, filing)
            summary["parsed"] += 1
        except (OSError, RuntimeError, ValueError) as error:
            report = _failure_report(artifact, ticker=ticker, error=error)
            summary["parser_failed"] += 1
        else:
            for decision in report["decisions"]:
                status = decision["status"]
                if status == "accepted":
                    summary["accepted_shadow"] += 1
                elif status in {"review", "rejected", "unresolved"}:
                    summary[status] += 1
        _write_immutable_json(args.output_root / f"{ticker}.json", report)

    _write_immutable_json(args.output_root / "summary.json", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
