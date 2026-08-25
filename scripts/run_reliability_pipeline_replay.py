#!/usr/bin/env python3
"""Regenerate the difficult U.S. valuation corpus without network or serving writes."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date
from html.parser import HTMLParser
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any, Mapping
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SERVING_ROOTS = (
    BACKEND / "app" / "data" / "us_valuations",
    ROOT / "frontend" / "public" / "data",
)
FORBIDDEN_PUBLIC_KEYS = {
    "financials",
    "forecast_assumptions",
    "discount_rate",
    "bridge_uncertainty",
    "source_manifest",
}
EVIDENCE_KEYS = {
    "ticker",
    "cik",
    "field",
    "value",
    "raw_value",
    "unit",
    "period_end",
    "filing_date",
    "source_accession",
    "source_url",
    "form",
    "source_kind",
    "status",
    "confidence",
    "locator",
    "excerpt",
    "rationale",
    "evidence_class",
    "parser_version",
}
SECTOR_FALLBACK_FIELDS = (
    "cash",
    "marketable_securities_current",
    "marketable_securities_noncurrent",
    "marketable_securities_total",
    "commercial_paper",
    "current_debt",
    "noncurrent_debt",
    "finance_lease_current",
    "finance_lease_noncurrent",
    "finance_lease_total",
    "preferred_equity",
    "noncontrolling_interests",
)


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


class PublicContractError(ValueError):
    """The rebuilt private result could not cross the public artifact boundary."""


def _visible_text(raw: bytes) -> str:
    parser = _VisibleTextParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return " ".join(" ".join(parser.parts).split())


def _compact_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("“", '"').replace("”", '"').replace("’", "'")
    return re.sub(r"\s+", "", normalized)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_paths(input_root: str | Path, output_dir: str | Path) -> tuple[Path, Path]:
    source = Path(input_root).resolve(strict=True)
    if not source.is_dir():
        raise ValueError("input root must resolve to a directory")
    target = Path(output_dir).resolve(strict=False)
    for serving_root in SERVING_ROOTS:
        if _is_within(target, serving_root.resolve(strict=False)):
            raise ValueError("output directory must not be inside a serving root")
    if _is_within(target, source):
        raise ValueError("output directory must not be inside the input root")
    return source, target


def _tree_hash() -> str:
    digest = hashlib.sha256()
    for root in SERVING_ROOTS:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
            digest.update(b"\n")
    return digest.hexdigest()


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _normal_cik(value: object) -> str:
    digits = "".join(character for character in str(value) if character.isdigit())
    if not digits:
        raise ValueError("CIK must contain digits")
    return digits.zfill(10)


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _require_private(candidate: Path) -> dict[str, Any]:
    raw = _json(candidate)
    if not isinstance(raw, dict):
        raise ValueError("private artifact must be an object")
    required = {"schema_version", "valuation_date", "issuer", "source_manifest", "model_policy", "financials"}
    if not required.issubset(raw):
        raise ValueError("public-shaped or incomplete private artifact")
    if not isinstance(raw["financials"], dict) or not isinstance(raw["issuer"], dict):
        raise ValueError("private artifact has invalid financials or issuer")
    ticker = str(raw["issuer"].get("ticker", "")).upper()
    if not ticker or not candidate.parent.name == ticker:
        raise ValueError("private artifact ticker does not match candidate directory")
    if _normal_cik(raw["issuer"].get("cik")) != _normal_cik(raw["financials"].get("cik")):
        raise ValueError("private artifact CIK identity mismatch")
    if not isinstance(raw["source_manifest"], dict):
        raise ValueError("source manifest must be an object")
    return raw


def _load_sources(private: Mapping[str, Any], input_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    records = private["source_manifest"].get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("source manifest records are missing")
    loaded: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("source manifest record is invalid")
        name = record.get("cache_file")
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("source manifest cache file is unsafe")
        path = input_root / "sec-cache" / name
        if not path.is_file():
            raise ValueError(f"source cache file is missing: {name}")
        expected = record.get("sha256")
        if not isinstance(expected, str) or _sha256(path) != expected:
            raise ValueError(f"source cache hash mismatch: {name}")
        loaded[name] = _json(path)
    cik = _normal_cik(private["issuer"].get("cik"))
    submissions_name = f"CIK{cik}-submissions.json"
    companyfacts_name = f"CIK{cik}-companyfacts.json"
    if submissions_name not in loaded or companyfacts_name not in loaded:
        raise ValueError("source manifest must include submissions and companyfacts")
    return loaded[submissions_name], loaded[companyfacts_name]


def _validate_evidence(candidate_dir: Path, private: Mapping[str, Any], input_root: Path) -> list[dict[str, Any]]:
    used_path = candidate_dir / "filing-evidence-used.json"
    if not used_path.exists():
        return []
    used = _json(used_path)
    if not isinstance(used, list):
        raise ValueError("used filing evidence must be a list")
    if not used:
        return []
    all_path = candidate_dir / "filing-evidence.json"
    if not all_path.is_file():
        raise ValueError("used filing evidence has no sibling evidence set")
    available = _json(all_path)
    if not isinstance(available, list):
        raise ValueError("filing evidence must be a list")
    available_keys = {_canonical(record) for record in available if isinstance(record, dict)}
    cik = _normal_cik(private["issuer"].get("cik"))
    ticker = str(private["issuer"].get("ticker", "")).upper()
    validated: list[dict[str, Any]] = []
    for record in used:
        if not isinstance(record, dict) or _canonical(record) not in available_keys:
            raise ValueError("used filing evidence is not an exact sibling record")
        if set(record) != EVIDENCE_KEYS:
            raise ValueError("filing evidence schema is not exact")
        if str(record["ticker"]).upper() != ticker or _normal_cik(record["cik"]) != cik:
            raise ValueError("filing evidence identity mismatch")
        if record["evidence_class"] not in {"reported", "reported_zero", "inferred_zero"}:
            raise ValueError("filing evidence class is invalid")
        if record["parser_version"] != "US-FILING-EVIDENCE-1.0":
            raise ValueError("filing evidence parser version is invalid")
        if not _finite(record["value"]):
            raise ValueError("filing evidence value is not finite")
        parsed = urlparse(str(record["source_url"]))
        filename = Path(parsed.path).name
        accession = str(record["source_accession"]).replace("-", "")
        if parsed.scheme != "https" or parsed.hostname not in {"www.sec.gov", "sec.gov"} or not filename:
            raise ValueError("filing evidence source URL is not a governed SEC archive URL")
        prefix = f"CIK{cik}-{accession}-"
        matches = list((input_root / "sec-cache" / "filings").glob(prefix + filename))
        if len(matches) != 1:
            raise ValueError(f"cached filing HTML is missing or ambiguous: {filename}")
        filing_path = matches[0]
        expected_hash = record.get("sha256")
        if expected_hash is not None and (_sha256(filing_path) != expected_hash):
            raise ValueError("cached filing HTML hash mismatch")
        excerpt = " ".join(str(record["excerpt"]).split())
        if excerpt and _compact_text(excerpt) not in _compact_text(
            _visible_text(filing_path.read_bytes())
        ):
            raise ValueError("filing evidence excerpt is absent from cached filing HTML")
        validated.append(deepcopy(record))
    return validated


def _before_base(candidate_dir: Path) -> float | None:
    path = candidate_dir / "valuation-public-candidate.json"
    if not path.is_file():
        return None
    try:
        value = _json(path).get("scenario_range", {}).get("base")
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return float(value) if _finite(value) else None


def _primary_value(result: Mapping[str, Any]) -> float | None:
    primary = result.get("model_policy", {}).get("primary")
    value = result.get("models", {}).get(primary, {}).get("intrinsic_value_per_share")
    return float(value) if _finite(value) else None


def _fallback_levels(result: Mapping[str, Any]) -> Counter[str]:
    availability = result.get("financials", {}).get("balance_sheet", {}).get("availability", {})
    counter: Counter[str] = Counter()
    if isinstance(availability, Mapping):
        for record in availability.values():
            if isinstance(record, Mapping) and isinstance(record.get("fallback_level"), str):
                counter[record["fallback_level"]] += 1
    return counter


def _unsafe_promotion(result: Mapping[str, Any], public: Mapping[str, Any], source_verified: bool) -> bool:
    if not source_verified:
        return True
    review = result.get("review", {})
    private_withheld = review.get("publication_state") == "withheld"
    public_withheld = public.get("review", {}).get("publication_state") == "withheld"
    if public_withheld:
        return not private_withheld
    if private_withheld:
        return True
    primary = result.get("model_policy", {}).get("primary")
    private_value = _primary_value(result)
    public_value = public.get("models", {}).get(primary, {}).get("intrinsic_value_per_share")
    if private_value is None or not _finite(public_value) or float(public_value) != private_value:
        return True
    if any(key in public for key in FORBIDDEN_PUBLIC_KEYS):
        return True
    return False


def _filing_records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    return [
        {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(len(accessions))
    ]


def _build_sector_cohorts(
    candidates: list[Path],
    input_root: Path,
) -> dict[tuple[str, str, str], list[tuple[float, str, str]]]:
    from app.us_valuation.xbrl import CompanyFactsNormalizer

    cohorts: dict[tuple[str, str, str], list[tuple[float, str, str]]] = {}
    for candidate in candidates:
        try:
            private = _require_private(candidate / "valuation-private.json")
            submissions, companyfacts = _load_sources(private, input_root)
            normalizer = CompanyFactsNormalizer(
                companyfacts,
                fiscal_year_end=submissions.get("fiscalYearEnd"),
                as_of_date=private["valuation_date"],
                filing_records=_filing_records(submissions),
            )
            assets_by_end = {
                fact.end: fact
                for fact in normalizer.annual_instant_series("total_assets", 3)
            }
            ticker = str(private["issuer"]["ticker"]).upper()
            dimensions = (
                ("archetype", str(private["issuer"]["primary_archetype"])),
                ("sector", str(private["issuer"]["finsight_sector"])),
            )
            for field in SECTOR_FALLBACK_FIELDS:
                history = normalizer.annual_instant_series(field, 3)
                matched = [fact for fact in history if fact.end in assets_by_end]
                if not matched:
                    continue
                fact = matched[-1]
                total_assets = assets_by_end[fact.end]
                if total_assets.value <= 0 or fact.value < 0:
                    continue
                ratio = fact.value / total_assets.value
                for dimension, group in dimensions:
                    cohorts.setdefault((dimension, group, field), []).append(
                        (ratio, fact.accession, ticker)
                    )
        except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
            continue
    return cohorts


def _sector_estimates_for_candidate(
    *,
    private: Mapping[str, Any],
    submissions: Mapping[str, Any],
    companyfacts: Mapping[str, Any],
    cohorts: Mapping[tuple[str, str, str], list[tuple[float, str, str]]],
) -> dict[str, Any]:
    from app.us_valuation.period_fallbacks import sector_estimate_decision
    from app.us_valuation.xbrl import CompanyFactsNormalizer

    normalizer = CompanyFactsNormalizer(
        dict(companyfacts),
        fiscal_year_end=submissions.get("fiscalYearEnd"),
        as_of_date=str(private["valuation_date"]),
        filing_records=_filing_records(submissions),
    )
    assets = normalizer.instant(
        "total_assets",
        at_or_before=str(private["valuation_date"]),
    )
    if assets is None or assets.value <= 0:
        return {}
    age = (
        date.fromisoformat(str(private["valuation_date"]))
        - date.fromisoformat(assets.end)
    ).days
    if age < 0 or age > 365:
        return {}
    ticker = str(private["issuer"]["ticker"]).upper()
    archetype = str(private["issuer"]["primary_archetype"])
    sector = str(private["issuer"]["finsight_sector"])
    decisions: dict[str, Any] = {}
    for field in SECTOR_FALLBACK_FIELDS:
        peers = [
            (ratio, accession)
            for ratio, accession, peer_ticker in cohorts.get(
                ("archetype", archetype, field), []
            )
            if peer_ticker != ticker
        ]
        if len(peers) < 5:
            peers = [
                (ratio, accession)
                for ratio, accession, peer_ticker in cohorts.get(
                    ("sector", sector, field), []
                )
                if peer_ticker != ticker
            ]
        if len(peers) < 5:
            continue
        decisions[field] = sector_estimate_decision(
            field=field,
            peer_ratios=peers,
            current_total_assets=assets.value,
        )
    return decisions


def _case_result(
    candidate_dir: Path,
    input_root: Path,
    output_dir: Path,
    cohorts: Mapping[tuple[str, str, str], list[tuple[float, str, str]]],
) -> dict[str, Any]:
    from app.us_valuation import build_us_valuation
    from app.us_valuation.artifacts import public_result

    private = _require_private(candidate_dir / "valuation-private.json")
    submissions, companyfacts = _load_sources(private, input_root)
    evidence = _validate_evidence(candidate_dir, private, input_root)
    sector_estimates = _sector_estimates_for_candidate(
        private=private,
        submissions=submissions,
        companyfacts=companyfacts,
        cohorts=cohorts,
    )
    result = build_us_valuation(
        submissions=submissions,
        companyfacts=companyfacts,
        valuation_date=private["valuation_date"],
        source_manifest=private["source_manifest"],
        filing_evidence=evidence,
        sector_estimates=sector_estimates,
    )
    try:
        public = public_result(result, submissions)
    except (TypeError, ValueError, KeyError) as error:
        raise PublicContractError(str(error)) from error
    ticker = str(private["issuer"]["ticker"]).upper()
    _write_json(output_dir / "generated" / ticker / "valuation-private.json", result)
    _write_json(output_dir / "public" / f"{ticker}.json", public)
    return {"private": result, "public": public, "ticker": ticker}


def _bucket(value: object, boundaries: tuple[float, float]) -> str:
    if not _finite(value):
        return "unavailable"
    number = float(value)
    if number <= boundaries[0]:
        return f"0_to_{boundaries[0]:.2f}"
    if number <= boundaries[1]:
        return f"over_{boundaries[0]:.2f}_to_{boundaries[1]:.2f}"
    return f"over_{boundaries[1]:.2f}"


def _near(value: object, boundaries: tuple[float, float]) -> bool:
    return _finite(value) and any(abs(float(value) - boundary) <= 0.005 for boundary in boundaries)


def render_markdown(summary: Mapping[str, Any]) -> str:
    den = summary["denominators"]
    lines = [
        "# FinSight reliability-policy replay",
        "",
        "Every count below names its denominator; this replay is evidence, not a publication approval.",
        "",
        f"- Input candidates: {summary['input_candidate_count']} immediate candidate directories.",
        f"- Valid private artifacts: {summary['valid_private_count']} of {den['input_candidate_count']} input candidates.",
        f"- Source-verified candidates: {summary['source_verified_count']} of {den['valid_private_count']} valid private artifacts.",
        f"- Numeric before: {summary['numeric_before_count']} of {den['input_candidate_count']} candidates.",
        f"- Numeric after: {summary['numeric_after_count']} of {den['source_verified_count']} source-verified candidates.",
        f"- Reliability counts: {dict(summary['reliability_counts'])} of {den['numeric_after_count']} numeric-after results.",
        f"- Fallback field counts: {dict(summary['fallback_level_counts'])} accepted fields.",
        f"- Fallback company counts: {dict(summary['fallback_level_company_counts'])} distinct companies.",
        f"- Source-integrity failures: {summary['source_integrity_failure_count']} of {den['input_candidate_count']} candidates.",
        f"- Build errors: {summary['build_error_count']} of {den['source_verified_count']} source-verified candidates.",
        f"- Public-contract failures: {summary['public_contract_failure_count']} of {den['source_verified_count']} source-verified candidates.",
        f"- Unsafe promotions: {summary['unsafe_promotion_count']} of {den['numeric_after_count']} numeric-after results.",
        f"- Serving artifacts changed: {summary['serving_artifacts_changed']}",
        f"- Serving hash before: `{summary['serving_hash_before']}`",
        f"- Serving hash after: `{summary['serving_hash_after']}`",
        "",
        "## Policy buckets",
        "",
        f"- Accounting impact (0.05 / 0.20 boundaries): `{summary['accounting_impact_buckets']}` of {den['numeric_after_count']} numeric-after results.",
        f"- Scenario movement (0.20 / 0.40 boundaries): `{summary['scenario_movement_buckets']}` of {den['numeric_after_count']} numeric-after results.",
        f"- Near-boundary cases: `{summary['near_boundary_cases']}` of {den['numeric_after_count']} numeric-after results.",
        "",
        "## Remaining blockers",
        "",
        f"`{summary['remaining_blocker_counts']}` of {den['source_verified_count']} source-verified candidates.",
        "",
        "## Company cases",
        "",
        "| Ticker | Result | Base | Reliability | Fallback levels | Blockers | Error |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for case in summary["cases"]:
        lines.append(
            "| " + " | ".join(
                str(case.get(key, "—")).replace("|", "\\|").replace("\n", " ")
                for key in ("ticker", "result", "base", "reliability", "fallback_levels", "blockers", "error")
            ) + " |"
        )
    return "\n".join(lines) + "\n"


def run_replay(input_root: str | Path, output_dir: str | Path) -> dict[str, Any]:
    source, target = validate_paths(input_root, output_dir)
    target.mkdir(parents=True, exist_ok=True)
    before_hash = _tree_hash()
    candidates = sorted(path for path in source.iterdir() if path.is_dir() and path.name != "sec-cache")
    cohorts = _build_sector_cohorts(candidates, source)
    summary: dict[str, Any] = {
        "schema_version": "US-RELIABILITY-REPLAY-1.0",
        "input_candidate_count": len(candidates),
        "valid_private_count": 0,
        "invalid_input_count": 0,
        "source_verified_count": 0,
        "numeric_before_count": 0,
        "numeric_after_count": 0,
        "reliability_counts": Counter(),
        "fallback_level_counts": Counter(),
        "fallback_level_company_counts": Counter(),
        "accounting_impact_buckets": Counter(),
        "scenario_movement_buckets": Counter(),
        "near_boundary_cases": [],
        "remaining_blocker_counts": Counter(),
        "source_integrity_failure_count": 0,
        "build_error_count": 0,
        "public_contract_failure_count": 0,
        "unsafe_promotion_count": 0,
        "serving_hash_before": before_hash,
        "serving_hash_after": None,
        "serving_artifacts_changed": None,
        "denominators": {
            "input_candidate_count": len(candidates),
            "valid_private_count": 0,
            "source_verified_count": 0,
            "numeric_after_count": 0,
        },
        "cases": [],
    }
    fallback_companies: Counter[str] = Counter()
    for candidate in candidates:
        case: dict[str, Any] = {"ticker": candidate.name, "result": "invalid", "base": None}
        before = _before_base(candidate)
        if before is not None:
            summary["numeric_before_count"] += 1
        try:
            private = _require_private(candidate / "valuation-private.json")
            summary["valid_private_count"] += 1
            summary["denominators"]["valid_private_count"] = summary["valid_private_count"]
            case["ticker"] = str(private["issuer"]["ticker"]).upper()
            replayed = _case_result(candidate, source, target, cohorts)
            summary["source_verified_count"] += 1
            summary["denominators"]["source_verified_count"] = summary["source_verified_count"]
            result = replayed["private"]
            public = replayed["public"]
            fallback = _fallback_levels(result)
            for level, count in fallback.items():
                summary["fallback_level_counts"][level] += count
                fallback_companies[level] += 1
            case["fallback_levels"] = dict(fallback)
            case["base"] = public.get("scenario_range", {}).get("base")
            case["reliability"] = public.get("reliability", {}).get("label")
            case["blockers"] = public.get("review", {}).get("errors", [])
            case["result"] = "numeric" if _finite(case["base"]) else "withheld"
            if _finite(case["base"]):
                summary["numeric_after_count"] += 1
                summary["denominators"]["numeric_after_count"] = summary["numeric_after_count"]
                summary["reliability_counts"][case["reliability"]] += 1
                reliability = public.get("reliability", {})
                accounting = _bucket(reliability.get("accounting_impact_ratio"), (0.05, 0.20))
                scenario = _bucket(reliability.get("scenario_movement_ratio"), (0.20, 0.40))
                summary["accounting_impact_buckets"][accounting] += 1
                summary["scenario_movement_buckets"][scenario] += 1
                if _near(reliability.get("accounting_impact_ratio"), (0.05, 0.20)) or _near(reliability.get("scenario_movement_ratio"), (0.20, 0.40)):
                    summary["near_boundary_cases"].append(case["ticker"])
            for blocker in case["blockers"]:
                summary["remaining_blocker_counts"][str(blocker)] += 1
            if _unsafe_promotion(result, public, True):
                summary["unsafe_promotion_count"] += 1
                case["result"] = "unsafe_promotion_blocked"
        except PublicContractError as error:
            summary["public_contract_failure_count"] += 1
            case["error"] = f"{type(error).__name__}: {error}"
        except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
            message = f"{type(error).__name__}: {error}"
            case["error"] = message
            if "source" in message or "evidence" in message or "hash" in message or "cache" in message:
                summary["source_integrity_failure_count"] += 1
            elif "private artifact" in message or "public-shaped" in message or "ticker" in message:
                summary["invalid_input_count"] += 1
            else:
                summary["build_error_count"] += 1
        summary["cases"].append(case)
    summary["fallback_level_company_counts"] = fallback_companies
    after_hash = _tree_hash()
    summary["serving_hash_after"] = after_hash
    summary["serving_artifacts_changed"] = before_hash != after_hash
    for key, value in list(summary.items()):
        if isinstance(value, Counter):
            summary[key] = dict(sorted(value.items()))
    _write_json(target / "replay-report.json", summary)
    (target / "replay-report.md").write_text(render_markdown(summary), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        sys.path.insert(0, str(BACKEND))
        summary = run_replay(args.input_root, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({key: summary[key] for key in (
        "input_candidate_count", "valid_private_count", "source_verified_count",
        "numeric_before_count", "numeric_after_count", "reliability_counts",
        "source_integrity_failure_count", "build_error_count", "public_contract_failure_count",
        "unsafe_promotion_count", "serving_artifacts_changed",
    )}, sort_keys=True))
    if summary["serving_artifacts_changed"] or summary["unsafe_promotion_count"]:
        return 2
    if summary["source_integrity_failure_count"] or summary["build_error_count"] or summary["public_contract_failure_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
