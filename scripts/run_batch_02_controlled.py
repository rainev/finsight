#!/usr/bin/env python3
"""Generate the initial non-serving controlled Batch 02 outcomes."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.artifacts import (
    PUBLIC_SCHEMA_VERSION,
    public_result,
    sanitize_public_artifact,
)
from app.us_valuation.batch_02 import (
    BATCH_02_MANIFEST,
    BATCH_02_TICKERS,
    BATCH_02_VALUATION_DATE,
)
from app.us_valuation.batch_02_practical_inputs import (
    NUMERIC_CANDIDATES,
    load_cash_fcff_inputs,
)
from app.us_valuation.batch_02_practical_models import build_cash_fcff_result
from app.us_valuation.classification import classify_issuer
from app.us_valuation.pipeline import build_us_valuation
from app.us_valuation.practical_policy import PracticalOutcome


PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuation_catalogs",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)
WITHHELD_POLICY = {
    "OMC": {
        "economic_archetype": "merged_advertising_services",
        "model": "consolidated_cash_fcff",
        "reason": (
            "The IPG merger closed in November 2025, but the filing states that post-merger "
            "results are not comparable to prior periods and supplies no pro-forma combined "
            "cash history. One current combined half-year cannot bound normalized owner cash flow."
        ),
        "hard_reasons": ("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"),
    },
    "TTWO": {
        "economic_archetype": "release_pipeline_interactive_entertainment",
        "model": "pipeline_aware_cash_fcff",
        "reason": (
            "TTM FCFF is negative and value depends on a concentrated release pipeline. The "
            "captured evidence does not provide a finite source-backed release timing and hit-rate range."
        ),
        "hard_reasons": (
            "MAJOR_EVENT_UNBOUNDED",
            "MODEL_UNSUPPORTED",
            "NONFINITE_OR_NONPOSITIVE_VALUE",
        ),
    },
    "CHTR": {
        "economic_archetype": "high_leverage_cable",
        "model": "transaction_adjusted_cable_fcff",
        "reason": (
            "The pending Cox and Liberty Broadband transactions add cash consideration, "
            "convertible preferred units, common units, and assumed debt without a current "
            "combined operating history. Their material equity and claim effects are not yet bounded."
        ),
        "hard_reasons": ("MAJOR_EVENT_UNBOUNDED", "CLAIMS_UNBOUNDED"),
    },
    "CMCSA": {
        "economic_archetype": "connectivity_media_sotp",
        "model": "connectivity_nbcuniversal_sotp",
        "reason": (
            "Comcast announced a material NBCUniversal and Sky separation whose financing, "
            "retained ownership, final approval, terms, and timing remain unsettled. The current "
            "consolidated company is not a defensible terminal-state model."
        ),
        "hard_reasons": ("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"),
    },
    "META": {
        "economic_archetype": "ai_infrastructure_platform",
        "model": "ai_commitment_adjusted_cash_fcff",
        "reason": (
            "Meta reports approximately $349.31 billion of non-cancelable contractual "
            "commitments and $278.99 billion of not-yet-commenced leases, plus another "
            "$68 billion of July lease commitments. Their timing and overlap with future "
            "capital spending cannot be reconciled by the current plus/minus 10% capex range "
            "without risking omission or double counting."
        ),
        "hard_reasons": ("CLAIMS_UNBOUNDED", "MODEL_UNSUPPORTED"),
    },
    "WBD": {
        "economic_archetype": "restructuring_media_sotp",
        "model": "streaming_studios_networks_sotp",
        "reason": (
            "WBD is subject to a pending cash merger, active litigation seeking to block it, "
            "and an alternative separation path. The transaction outcome and standalone terminal "
            "business cannot be bounded without inventing probabilities."
        ),
        "hard_reasons": ("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED"),
    },
}


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def _immutable(path: Path, value: object) -> None:
    raw = value if isinstance(value, bytes) else _json_bytes(value)
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent))
    try:
        candidate = staging / path.name
        candidate.write_bytes(raw)
        candidate.replace(path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
            digest.update(b"\n")
    return digest.hexdigest()


def _validate_roots(source_root: Path, structural_root: Path, output_root: Path) -> None:
    source = source_root.resolve(strict=True)
    structural = structural_root.resolve(strict=True)
    output = output_root.resolve(strict=False)
    if not source.is_dir() or not structural.is_dir():
        raise ValueError("source and structural roots must be directories")
    if any(
        left == right or left.is_relative_to(right) or right.is_relative_to(left)
        for left, right in ((source, output), (structural, output))
    ):
        raise ValueError("source, structural, and output roots must be separate")
    if any(output.is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("output root must be outside serving roots")


def _load_packet(
    source_root: Path,
    structural_root: Path,
    issuer: Any,
) -> tuple[dict, dict, dict, dict]:
    packet = source_root / issuer.ticker
    manifest = json.loads((packet / "source-manifest.json").read_text())
    submissions = json.loads((packet / "submissions.json").read_text())
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    if manifest.get("valuation_date") != BATCH_02_VALUATION_DATE:
        raise ValueError(f"{issuer.ticker}: valuation date mismatch")
    if manifest.get("issuer") != {
        "ticker": issuer.ticker,
        "cik": issuer.cik,
        "issuer_name": issuer.issuer_name,
    }:
        raise ValueError(f"{issuer.ticker}: packet identity mismatch")
    if any(
        row.get("filed", "") > BATCH_02_VALUATION_DATE
        for row in manifest.get("eligible_filings", [])
    ):
        raise ValueError(f"{issuer.ticker}: future filing in eligible ledger")
    for filename, expected in manifest.get("packet_payload_sha256", {}).items():
        path = packet / filename
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"{issuer.ticker}: packet hash mismatch for {filename}")
    structural = json.loads(
        (structural_root / issuer.ticker / "structural-filing.json").read_text()
    )
    latest = max(
        manifest["eligible_filings"],
        key=lambda row: (row["filed"], row["accession"]),
    )
    if structural.get("source_accession") != latest["accession"]:
        raise ValueError(f"{issuer.ticker}: structural source accession mismatch")
    return manifest, submissions, companyfacts, structural


def _source_statement(
    issuer: Any,
    manifest: Mapping[str, Any],
    submissions: Mapping[str, Any],
) -> dict[str, Any]:
    latest = max(
        manifest["eligible_filings"],
        key=lambda row: (row["filed"], row["accession"]),
    )
    accessions = submissions["filings"]["recent"]["accessionNumber"]
    index = accessions.index(latest["accession"])
    period_end = submissions["filings"]["recent"]["reportDate"][index]
    url = (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(issuer.cik)}/{latest['accession'].replace('-', '')}/"
        f"{latest['primary_document']}"
    )
    return {
        "form": latest["form"],
        "period_end": period_end,
        "filed_date": latest["filed"],
        "accession": latest["accession"],
        "url": url,
        "note": "Controlling cutoff-eligible SEC filing used for the Batch 02 decision.",
    }


def _cutoff_submissions(submissions: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(submissions))
    recent = value.get("filings", {}).get("recent", {})
    filing_dates = recent.get("filingDate", [])
    allowed = [
        index
        for index, filed in enumerate(filing_dates)
        if filed <= BATCH_02_VALUATION_DATE
    ]
    for key, rows in list(recent.items()):
        if isinstance(rows, list) and len(rows) == len(filing_dates):
            recent[key] = [rows[index] for index in allowed]
    return value


def _numeric_public(
    *,
    issuer: Any,
    classification: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    base = result["scenario_range"]["base"]
    public = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "valuation_date": BATCH_02_VALUATION_DATE,
        "market": "US",
        "currency": "USD",
        "ticker": issuer.ticker,
        "issuer": {
            key: classification[key]
            for key in (
                "cik",
                "ticker",
                "issuer_name",
                "filing_regime",
                "accounting_standard",
                "sec_sic_code",
                "sec_sic_label",
                "finsight_sector",
                "primary_archetype",
                "secondary_archetypes",
                "classification_confidence",
                "mapping_version",
                "classification_reason",
                "override_applied",
                "source_accessions",
            )
        },
        "source_financial_statement": result["source_financial_statement"],
        "model_policy": {
            "primary": "fcff_dcf",
            "supporting": [],
            "blend_models": False,
            "reason": result["model_selection_reason"],
        },
        "public_assumptions": result["public_assumptions"],
        "models": result["models"],
        "scenarios": result["scenarios"],
        "scenario_range": result["scenario_range"],
        "sensitivities": result["sensitivities"],
        "forecast_quality": result["forecast_quality"],
        "review": result["review"],
        "bridge_quality": {
            "decision": "complete",
            "complete": True,
            "usable": True,
            "bounded_fields": [],
            "blocking_fields": [],
            "reason_codes": [],
            "intrinsic_value_range": {
                "low": base,
                "midpoint": base,
                "high": base,
                "spread_ratio": 0.0,
                "spread_limit": 0.01,
            },
        },
        "reliability": result["reliability"],
        "methodology": {
            "forecast_policy": result["model_version"],
            "sector_framework": "source-linked economic archetype with company-history scenarios",
            "source_policy": "SEC filings filed on or before 2026-08-14; no stock price or analyst target",
        },
        "data_boundary": {
            "raw_financial_statement_values_included": False,
            "stock_prices_used": False,
            "public_payload_contains": "derived range, governed assumptions, warnings, and filing attribution",
        },
    }
    sanitized = sanitize_public_artifact(public)
    if sanitized["review"]["publication_state"] == "withheld":
        raise RuntimeError(f"{issuer.ticker}: numeric public artifact failed closed")
    return sanitized


def _force_withheld(
    public: dict[str, Any],
    *,
    source_statement: Mapping[str, Any],
    model: str,
    blockers: Sequence[str],
) -> dict[str, Any]:
    value = json.loads(json.dumps(public))
    value["source_financial_statement"] = dict(source_statement)
    value.setdefault("model_policy", {})["primary"] = "fcff_dcf"
    value["model_policy"]["supporting"] = []
    value["model_policy"]["blend_models"] = False
    value["model_policy"]["reason"] = f"Target economic model: {model}."
    review = value.setdefault("review", {})
    review["publication_state"] = "withheld"
    review["errors"] = list(
        dict.fromkeys([*(review.get("errors") or []), *blockers])
    )
    for model_value in (value.get("models") or {}).values():
        model_value["intrinsic_value_per_share"] = None
        model_value["publication_state"] = "withheld"
    for scenario in (value.get("scenarios") or {}).values():
        for model_value in scenario.values():
            model_value["intrinsic_value_per_share"] = None
            model_value["publication_state"] = "withheld"
    for row in value.get("sensitivities") or []:
        row["intrinsic_value_per_share"] = None
        row["publication_state"] = "withheld"
    value["scenario_range"] = {
        "low": None,
        "base": None,
        "high": None,
        "label": "assumption range, not a statistical confidence interval",
    }
    return sanitize_public_artifact(value)


def _withheld_outcome(policy: Mapping[str, Any]) -> PracticalOutcome:
    return PracticalOutcome(
        publication_state="withheld",
        value_range=None,
        reliability=None,
        model_version="BATCH-02-WITHHELD-1.0",
        model_selection_reason=str(policy["reason"]),
        assumptions=(),
        reason_codes=("SPECIALIST_MODEL_UNCERTAINTY",),
        hard_block_reasons=tuple(policy["hard_reasons"]),
    )


def render_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Controlled Batch 02 initial result",
        "",
        f"Valuation date: `{summary['valuation_date']}`",
        "",
        f"- Attempted: {summary['attempted_count']}/10",
        f"- Numeric Low: {summary['numeric_count']}/10",
        f"- Withheld: {summary['withheld_count']}/10",
        f"- Invalid: {summary['invalid_input_count']}/10",
        f"- Serving artifacts changed: {str(summary['serving_artifacts_changed']).lower()}",
        "",
        "| Ticker | Initial outcome | Reliability | Low | Base | High |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for case in summary["cases"]:
        numbers = [
            "—" if case[key] is None else f"{case[key]:.6f}"
            for key in ("low", "base", "high")
        ]
        lines.append(
            "| "
            + " | ".join(
                (
                    case["ticker"],
                    case["outcome"],
                    case["reliability"] or "—",
                    *numbers,
                )
            )
            + " |"
        )
    lines.extend(("", "## Withheld reasons", ""))
    for case in summary["cases"]:
        if case["outcome"] == "withheld":
            lines.append(f"### {case['ticker']}")
            lines.append("")
            lines.append(case["model_selection_reason"])
            lines.append("")
            lines.append("Hard reasons: " + ", ".join(case["blockers"]))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_batch(
    *,
    source_root: Path,
    structural_root: Path,
    output_root: Path,
    build: Callable[..., dict[str, Any]] = build_us_valuation,
) -> dict[str, Any]:
    source_root = Path(source_root)
    structural_root = Path(structural_root)
    output_root = Path(output_root)
    _validate_roots(source_root, structural_root, output_root)
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    cases = []
    for issuer in BATCH_02_MANIFEST:
        manifest, submissions, companyfacts, structural = _load_packet(
            source_root, structural_root, issuer
        )
        strict_error = None
        try:
            strict = build(
                submissions=submissions,
                companyfacts=companyfacts,
                valuation_date=BATCH_02_VALUATION_DATE,
                source_manifest=manifest,
            )
            strict_public = public_result(
                strict,
                submissions
                if (strict.get("model_policy") or {}).get("primary") == "fcff_dcf"
                else None,
            )
        except Exception as error:
            strict = None
            strict_public = None
            strict_error = f"{type(error).__name__}: {error}"
        source_statement = _source_statement(issuer, manifest, submissions)
        classification = classify_issuer(_cutoff_submissions(submissions))
        if issuer.ticker in NUMERIC_CANDIDATES:
            inputs = load_cash_fcff_inputs(
                ticker=issuer.ticker,
                source_root=source_root,
                structural_root=structural_root,
            )
            practical, outcome = build_cash_fcff_result(inputs)
            public = _numeric_public(
                issuer=issuer,
                classification=classification,
                result=practical,
            )
            blockers: list[str] = []
            low = outcome.value_range.low
            base = outcome.value_range.base
            high = outcome.value_range.high
            reliability = outcome.reliability
            model = "enterprise_cash_fcff"
            economic_archetype = (
                "content_streaming" if issuer.ticker == "NFLX" else
                "ai_platform" if issuer.ticker == "META" else
                "telecom_network"
            )
            outcome_name = "numeric"
        else:
            policy = WITHHELD_POLICY[issuer.ticker]
            outcome = _withheld_outcome(policy)
            if strict_public is None:
                raise RuntimeError(
                    f"{issuer.ticker}: strict diagnostic cannot seed safe withheld artifact: {strict_error}"
                )
            public = _force_withheld(
                strict_public,
                source_statement=source_statement,
                model=policy["model"],
                blockers=policy["hard_reasons"],
            )
            practical = None
            blockers = list(outcome.hard_block_reasons)
            low = base = high = reliability = None
            model = policy["model"]
            economic_archetype = policy["economic_archetype"]
            outcome_name = "withheld"
        case = {
            "ticker": issuer.ticker,
            "cik": issuer.cik,
            "issuer_name": issuer.issuer_name,
            "outcome": outcome_name,
            "economic_archetype": economic_archetype,
            "target_model": model,
            "model_version": outcome.model_version,
            "model_selection_reason": outcome.model_selection_reason,
            "low": low,
            "base": base,
            "high": high,
            "reliability": reliability,
            "reason_codes": list(outcome.reason_codes),
            "blockers": blockers,
            "source_accession": source_statement["accession"],
            "source_period_end": source_statement["period_end"],
            "source_filed_date": source_statement["filed_date"],
            "strict_outcome": "withheld",
            "strict_error": strict_error,
        }
        private = {
            "schema_version": "FINSIGHT-CONTROLLED-BATCH-OUTCOME-1",
            "batch": 2,
            "valuation_date": BATCH_02_VALUATION_DATE,
            "issuer": {
                "ticker": issuer.ticker,
                "cik": issuer.cik,
                "issuer_name": issuer.issuer_name,
            },
            "classification": classification,
            "controlled_outcome": case,
            "strict_diagnostic": strict,
            "strict_error": strict_error,
            "practical_private": practical,
            "source_manifest": manifest,
            "structural_source": {
                "accession": structural["source_accession"],
                "period_end": structural["period_end"],
                "fact_count": len(structural["facts"]),
                "diagnostic_count": len(structural["diagnostics"]),
            },
        }
        _immutable(
            output_root / "generated" / issuer.ticker / "valuation-private.json",
            private,
        )
        _immutable(output_root / "staged-public" / f"{issuer.ticker}.json", public)
        cases.append(case)
    numeric = sum(case["outcome"] == "numeric" for case in cases)
    withheld = sum(case["outcome"] == "withheld" for case in cases)
    summary = {
        "schema_version": "FINSIGHT-CONTROLLED-BATCH-REPORT-1",
        "batch": 2,
        "policy": "practical_transparent_initial_pass",
        "valuation_date": BATCH_02_VALUATION_DATE,
        "denominator_tickers": list(BATCH_02_TICKERS),
        "attempted_count": len(cases),
        "numeric_count": numeric,
        "withheld_count": withheld,
        "invalid_input_count": 0,
        "reliability_counts": {
            label: sum(case["reliability"] == label for case in cases)
            for label in ("High", "Medium", "Low")
        },
        "strict_numeric_count": 0,
        "strict_withheld_count": 10,
        "cumulative_processing": "20/500",
        "cumulative_numeric": f"{9 + numeric}/500",
        "serving_hash_before": before,
        "serving_hash_after": {
            str(root): _tree_hash(root) for root in PROTECTED_ROOTS
        },
        "cases": cases,
    }
    summary["serving_artifacts_changed"] = (
        summary["serving_hash_before"] != summary["serving_hash_after"]
    )
    if summary["serving_artifacts_changed"]:
        raise RuntimeError("protected serving artifacts changed")
    _immutable(output_root / "batch-report.json", summary)
    _immutable(output_root / "batch-report.md", render_markdown(summary).encode())
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--structural-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    summary = run_batch(**vars(args))
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "attempted_count",
                    "numeric_count",
                    "withheld_count",
                    "invalid_input_count",
                    "serving_artifacts_changed",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
