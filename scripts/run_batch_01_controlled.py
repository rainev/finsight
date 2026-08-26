#!/usr/bin/env python3
"""Generate controlled, non-serving Batch 01 outcomes from frozen source packets."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
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

from app.us_valuation.artifacts import public_result, sanitize_public_artifact
from app.us_valuation.batch_01 import (
    BATCH_01_MANIFEST,
    BATCH_01_TICKERS,
    BATCH_01_VALUATION_DATE,
)
from app.us_valuation.economic_routing import load_batch_01_routing_records
from app.us_valuation.batch_01_practical_inputs import practical_bridge_evidence
from app.us_valuation.batch_01_practical_models import build_practical_result
from app.us_valuation.batch_01_recovery_inputs import (
    load_batch_01_recovery_evidence,
)
from app.us_valuation.pipeline import build_us_valuation
from app.us_valuation.structural_promotion import (
    StructuralPromotionError,
    promote_structural_decision,
    resolution_decision_from_dict,
)


PROTECTED_ROOTS = (
    ROOT / "backend/app/data/us_valuation_catalogs",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)


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
    ).encode("utf-8")


def _immutable_bytes(path: Path, raw: bytes) -> None:
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"refusing to overwrite immutable output: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{path.stem}-", dir=path.parent))
    try:
        staging = staging_dir / path.name
        staging.write_bytes(raw)
        staging.replace(path)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def _immutable_json(path: Path, value: object) -> None:
    _immutable_bytes(path, _json_bytes(value))


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
            digest.update(b"\n")
    return digest.hexdigest()


def _validate_paths(source_root: Path, output_root: Path) -> None:
    source = source_root.resolve(strict=True)
    target = output_root.resolve(strict=False)
    if not source.is_dir():
        raise ValueError("source root must be a directory")
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("source and output roots must be separate")
    if any(target.is_relative_to(root.resolve()) for root in PROTECTED_ROOTS):
        raise ValueError("output root must be outside protected serving roots")


def _load_packet(source_root: Path, issuer: Any) -> tuple[dict, dict, dict]:
    packet = source_root / issuer.ticker
    manifest = json.loads((packet / "source-manifest.json").read_text())
    if manifest.get("valuation_date") != BATCH_01_VALUATION_DATE:
        raise ValueError(f"{issuer.ticker}: packet valuation date mismatch")
    identity = manifest.get("issuer", {})
    if identity.get("ticker") != issuer.ticker or identity.get("cik") != issuer.cik:
        raise ValueError(f"{issuer.ticker}: packet identity mismatch")
    for filename, expected in manifest.get("packet_payload_sha256", {}).items():
        path = packet / filename
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError(f"{issuer.ticker}: packet hash mismatch for {filename}")
    submissions = json.loads((packet / "submissions.json").read_text())
    companyfacts = json.loads((packet / "companyfacts.json").read_text())
    return manifest, submissions, companyfacts


def _load_blockers() -> dict[str, list[str]]:
    path = BACKEND / "app/us_valuation/config/batch_01_model_blockers.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("version") != "BATCH-01-MODEL-BLOCKERS-1.0":
        raise ValueError("Batch 01 blocker policy version is invalid")
    blockers = raw.get("blockers")
    if not isinstance(blockers, dict) or tuple(blockers) != BATCH_01_TICKERS:
        raise ValueError("Batch 01 blocker policy does not match the manifest")
    if any(
        not isinstance(rows, list)
        or not rows
        or any(not isinstance(row, str) or not row.strip() for row in rows)
        for rows in blockers.values()
    ):
        raise ValueError("Batch 01 blocker policy contains invalid rows")
    return blockers


def _structural_evidence(
    structural_root: Path | None,
    *,
    ticker: str,
    cik: str,
    valuation_date: str,
) -> tuple[object, ...]:
    if structural_root is None:
        return ()
    report_path = structural_root / ticker / "structural-report.json"
    if not report_path.is_file():
        return ()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    filing = report.get("controlling_filing") or {}
    filing_date = filing.get("filing_date")
    if not isinstance(filing_date, str):
        diagnostic_path = structural_root / ticker / "diagnostic-private.json"
        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
        filing_date = (
            diagnostic.get("financials", {})
            .get("ttm", {})
            .get("controlling_filing", {})
            .get("filing_date")
        )
    promoted = []
    for raw_decision in report.get("decisions", []):
        if raw_decision.get("status") != "accepted":
            continue
        try:
            promoted.append(
                promote_structural_decision(
                    resolution_decision_from_dict(raw_decision),
                    ticker=ticker,
                    cik=cik,
                    filing_date=filing_date,
                    valuation_date=valuation_date,
                )
            )
        except StructuralPromotionError:
            continue
    return tuple(promoted)


def _force_withheld_public(
    public: dict[str, Any],
    *,
    target_model: str,
    blockers: Sequence[str],
) -> dict[str, Any]:
    result = json.loads(json.dumps(public))
    review = result.setdefault("review", {})
    review["publication_state"] = "withheld"
    errors = list(review.get("errors") or [])
    errors.extend(
        [
            f"CONTROLLED_RESET_TARGET_MODEL: {target_model}",
            "CONTROLLED_RESET_MODEL_NOT_VALIDATED",
            *blockers,
        ]
    )
    review["errors"] = list(dict.fromkeys(errors))
    for model in (result.get("models") or {}).values():
        model["intrinsic_value_per_share"] = None
        model["publication_state"] = "withheld"
    for scenario in (result.get("scenarios") or {}).values():
        for model in scenario.values():
            model["intrinsic_value_per_share"] = None
            model["publication_state"] = "withheld"
    result["scenario_range"] = {
        "low": None,
        "base": None,
        "high": None,
        "label": "assumption range, not a statistical confidence interval",
    }
    result.pop("reliability", None)
    return sanitize_public_artifact(result)


def render_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Controlled Batch 01 outcome report",
        "",
        f"Policy: `{summary['policy']}`",
        "",
        f"Valuation date: `{summary['valuation_date']}`",
        "",
        f"- Attempted: {summary['attempted_count']}/10",
        f"- Publishable numeric: {summary['numeric_count']}/10",
        f"- Withheld: {summary['withheld_count']}/10",
        f"- Invalid input: {summary['invalid_input_count']}/10",
        f"- Cumulative processing: {summary['cumulative_processing']}",
        f"- Cumulative publishable numeric: {summary['cumulative_publishable_numeric']}",
        f"- Serving artifacts changed: {str(summary['serving_artifacts_changed']).lower()}",
        "",
        "Old pipeline numbers are diagnostic comparison evidence only. They are not controlled-reset values.",
        "",
        "| Ticker | Target lane | Maturity | Outcome | Low | Base | High |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for case in summary["cases"]:
        values = tuple(
            "—" if case[key] is None else f"{case[key]:.6f}"
            for key in ("low", "base", "high")
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    case["ticker"],
                    case["target_model"],
                    case["model_maturity"],
                    case["outcome"],
                    *values,
                )
            )
            + " |"
        )
    lines.extend(("", "## Exact blockers", ""))
    for case in summary["cases"]:
        lines.append(f"### {case['ticker']} — {case['economic_lane']}")
        lines.append("")
        for blocker in case["blockers"]:
            lines.append(f"- {blocker}")
        comparison = case["diagnostic_comparison"]
        lines.extend(
            (
                "",
                "Diagnostic comparison: "
                f"configured `{comparison['configured_model']}`, "
                f"base `{comparison['base']}`, state "
                f"`{comparison['publication_state']}`. Not a controlled-reset value.",
                "",
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def run_batch(
    *,
    source_root: Path,
    output_root: Path,
    structural_root: Path | None = None,
    recovery_root: Path | None = None,
    manifest: Sequence[Any] = BATCH_01_MANIFEST,
    routing_records: Sequence[Any] | None = None,
    blocker_policy: Mapping[str, Sequence[str]] | None = None,
    policy: str = "strict",
    build: Callable[..., dict] = build_us_valuation,
    serialize: Callable[..., dict] = public_result,
) -> dict[str, Any]:
    """Generate exactly one safe explicit outcome for every frozen Batch 01 issuer."""

    source_root = Path(source_root)
    output_root = Path(output_root)
    structural_root = Path(structural_root) if structural_root is not None else None
    recovery_root = Path(recovery_root) if recovery_root is not None else None
    if policy not in {"strict", "practical"}:
        raise ValueError("policy must be strict or practical")
    _validate_paths(source_root, output_root)
    recovery_evidence = None
    if recovery_root is not None:
        if policy != "practical" or structural_root is None:
            raise ValueError("recovery evidence requires practical policy and structural root")
        resolved_recovery = recovery_root.resolve(strict=True)
        if not resolved_recovery.is_dir():
            raise ValueError("recovery root must be a directory")
        if output_root.resolve(strict=False).is_relative_to(resolved_recovery):
            raise ValueError("output root must be separate from recovery evidence")
        recovery_evidence = load_batch_01_recovery_evidence(
            recovery_root=recovery_root,
            structural_root=structural_root,
        )
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    routes = tuple(routing_records or load_batch_01_routing_records())
    blockers = dict(blocker_policy or _load_blockers())
    if tuple(issuer.ticker for issuer in manifest) != tuple(
        route.ticker for route in routes
    ):
        raise ValueError("routing records do not match the Batch 01 manifest")
    if tuple(blockers) != tuple(issuer.ticker for issuer in manifest):
        raise ValueError("blocker policy does not match the Batch 01 manifest")

    cases: list[dict[str, Any]] = []
    for issuer, route in zip(manifest, routes):
        source_manifest, submissions, companyfacts = _load_packet(
            source_root, issuer
        )
        structural_evidence = _structural_evidence(
            structural_root,
            ticker=issuer.ticker,
            cik=issuer.cik,
            valuation_date=BATCH_01_VALUATION_DATE,
        )
        strict_diagnostic = build(
            submissions=submissions,
            companyfacts=companyfacts,
            valuation_date=BATCH_01_VALUATION_DATE,
            source_manifest=source_manifest,
            bridge_evidence=structural_evidence,
        )
        decision = route.model_decision
        primary = (strict_diagnostic.get("model_policy") or {}).get("primary")
        strict_range = strict_diagnostic.get("scenario_range") or {}
        practical_private = None
        if policy == "practical":
            combined_evidence = (
                *structural_evidence,
                *practical_bridge_evidence(
                    ticker=issuer.ticker,
                    companyfacts=companyfacts,
                ),
            )
            practical_diagnostic = build(
                submissions=submissions,
                companyfacts=companyfacts,
                valuation_date=BATCH_01_VALUATION_DATE,
                source_manifest=source_manifest,
                bridge_evidence=combined_evidence,
            )
            practical_private, practical_outcome = build_practical_result(
                ticker=issuer.ticker,
                diagnostic=practical_diagnostic,
                companyfacts=companyfacts,
                recovery_evidence=recovery_evidence,
            )
            public = serialize(
                practical_private,
                submissions if primary == "fcff_dcf" else None,
            )
            if practical_outcome.is_numeric:
                staged = public
                ticker_blockers = []
                outcome_name = "numeric"
                low = practical_outcome.value_range.low
                base = practical_outcome.value_range.base
                high = practical_outcome.value_range.high
                reliability = practical_outcome.reliability
                fallback_levels = sorted(
                    {
                        assumption.fallback_level
                        for assumption in practical_outcome.assumptions
                    }
                )
                reason_codes = list(practical_outcome.reason_codes)
                model_version = practical_outcome.model_version
            else:
                ticker_blockers = list(practical_outcome.hard_block_reasons)
                practical_target_model = (
                    (practical_private.get("model_policy") or {}).get("primary")
                    or decision.model_family
                )
                staged = _force_withheld_public(
                    public,
                    target_model=practical_target_model,
                    blockers=ticker_blockers,
                )
                outcome_name = "withheld"
                low = base = high = reliability = None
                fallback_levels = []
                reason_codes = list(practical_outcome.reason_codes)
                model_version = practical_outcome.model_version
        else:
            public = serialize(
                strict_diagnostic,
                submissions if primary == "fcff_dcf" else None,
            )
            ticker_blockers = [
                "MODEL_ROUTING_HYPOTHESIS_NOT_CONFIRMED",
                (
                    "MODEL_LANE_EXPERIMENTAL"
                    if decision.maturity == "experimental"
                    else "MODEL_LANE_PROVISIONAL_EVIDENCE_INCOMPLETE"
                ),
                *blockers[issuer.ticker],
            ]
            staged = _force_withheld_public(
                public,
                target_model=decision.model_family,
                blockers=ticker_blockers,
            )
            outcome_name = "withheld"
            low = base = high = reliability = None
            fallback_levels = []
            reason_codes = []
            model_version = decision.model_version
        case = {
            "ticker": issuer.ticker,
            "cik": issuer.cik,
            "issuer_name": issuer.issuer_name,
            "outcome": outcome_name,
            "economic_lane": decision.economic_lane,
            "target_model": decision.model_family,
            "model_version": model_version,
            "model_maturity": decision.maturity,
            "reliability_cap": (
                reliability
                if policy == "practical" and reliability is not None
                else "Withhold"
                if policy == "practical"
                else decision.reliability_cap
            ),
            "low": low,
            "base": base,
            "high": high,
            "reliability": reliability,
            "reason_codes": reason_codes,
            "fallback_levels": fallback_levels,
            "blockers": ticker_blockers,
            "diagnostic_comparison": {
                "configured_model": primary,
                "low": strict_range.get("low"),
                "base": strict_range.get("base"),
                "high": strict_range.get("high"),
                "publication_state": (strict_diagnostic.get("review") or {}).get(
                    "publication_state"
                ),
                "strict_controlled_outcome": "withheld",
                "not_a_controlled_reset_value": True,
            },
            "structural_promotions": [
                evidence.field for evidence in structural_evidence
            ],
        }
        private = {
            "schema_version": "FINSIGHT-CONTROLLED-BATCH-OUTCOME-1",
            "valuation_date": BATCH_01_VALUATION_DATE,
            "issuer": {
                "ticker": issuer.ticker,
                "cik": issuer.cik,
                "issuer_name": issuer.issuer_name,
            },
            "economic_profile": (
                asdict(route.economic_profile)
                if is_dataclass(route.economic_profile)
                else route.economic_profile
            ),
            "model_decision": (
                asdict(decision) if is_dataclass(decision) else decision
            ),
            "controlled_outcome": case,
            "diagnostic_private": strict_diagnostic,
            "practical_private": practical_private,
        }
        _immutable_json(
            output_root / "generated" / issuer.ticker / "valuation-private.json",
            private,
        )
        _immutable_json(output_root / "staged-public" / f"{issuer.ticker}.json", staged)
        cases.append(case)

    numeric_count = sum(case["outcome"] == "numeric" for case in cases)
    withheld_count = sum(case["outcome"] == "withheld" for case in cases)
    reliability_counts = {
        label: sum(case.get("reliability") == label for case in cases)
        for label in ("High", "Medium", "Low")
    }
    summary = {
        "schema_version": "FINSIGHT-CONTROLLED-BATCH-REPORT-1",
        "policy": policy,
        "valuation_date": BATCH_01_VALUATION_DATE,
        "attempted_count": len(cases),
        "numeric_count": numeric_count,
        "withheld_count": withheld_count,
        "invalid_input_count": 0,
        "reliability_counts": reliability_counts,
        "cumulative_processing": "10/500",
        "cumulative_publishable_numeric": f"{numeric_count}/500",
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
    _immutable_json(output_root / "batch-report.json", summary)
    _immutable_bytes(
        output_root / "batch-report.md",
        render_markdown(summary).encode("utf-8"),
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path)
    parser.add_argument("--recovery-root", type=Path)
    parser.add_argument("--policy", choices=("strict", "practical"), default="strict")
    args = parser.parse_args()
    summary = run_batch(
        source_root=args.source_root,
        output_root=args.output_root,
        structural_root=args.structural_root,
        recovery_root=args.recovery_root,
        policy=args.policy,
    )
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
