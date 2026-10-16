"""Build a deterministic, evidence-preserving work register for U.S. refreshes.

The register is deliberately a reporting layer.  It does not compile policies,
fetch filings, or change a serving catalog.  It joins the frozen registry,
baseline/recipe inventory, policy compilation receipt, and cached source
validation receipts while keeping the claims made by each receipt separate.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "FINSIGHT-US-REFRESH-WORK-REGISTER-1"
DEFAULT_EXPECTED_COUNT = 440
CLAIM_MECHANISMS = (
    "minority_interests",
    "preferred_stock",
    "acquisition_payments",
    "litigation",
    "timed_commitments",
    "post_filing_events",
    "operating_reserves",
    "customer_funds",
    "unclassified_review",
)


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable, human-readable canonical JSON bytes."""

    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def implementation_fingerprint(repo_root: Path | None = None) -> str:
    """Match ``scripts/verify_us_refresh_sources.py``'s code fingerprint."""

    root = Path(repo_root or Path(__file__).resolve().parents[3]).resolve()
    report_only = {'refresh_work_register.py','refresh_group_verification.py'}
    paths = [
        root / "scripts" / "verify_us_refresh_sources.py",
        *(path for path in sorted((root / "backend" / "app" / "us_valuation").rglob("*.py")) if path.name not in report_only),
        *sorted((root / "backend" / "app" / "us_valuation" / "config").rglob("*.json")),
    ]
    payload = {
        str(path.relative_to(root)): sha256_file(path)
        for path in paths
        if path.is_file()
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _as_rows(value: Any, *, path: Path, keys: Sequence[str] = ()) -> list[dict[str, Any]]:
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict):
        rows = next((value[key] for key in keys if isinstance(value.get(key), list)), None)
        if rows is None:
            for candidate in ("rows", "companies", "entries", "issuers"):
                if isinstance(value.get(candidate), list):
                    rows = value[candidate]
                    break
        if rows is None:
            raise ValueError(f"{path}: expected a row list")
    else:
        raise ValueError(f"{path}: expected a JSON object or row list")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: every row must be an object")
    return list(rows)


def _ticker(row: Mapping[str, Any], *, path: Path) -> str | None:
    for key in ("ticker", "symbol", "issuer_ticker"):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _short_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(f"{key} {_short_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_short_text(item) for item in value)
    return str(value)


def _extract_paths(value: Any) -> list[str]:
    """Keep evidence paths but do not treat arbitrary URLs as local paths."""

    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"path", "source_path", "packet_directory", "report_path", "evidence_path"}:
                if isinstance(item, str) and item:
                    found.append(item)
            found.extend(_extract_paths(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_extract_paths(item))
    return sorted(set(found))


def _finite_replay(recipe: Mapping[str, Any]) -> bool:
    replay = recipe.get("replay")
    if not isinstance(replay, Mapping):
        return False
    return all(
        isinstance(replay.get(key), (int, float))
        and math.isfinite(float(replay[key]))
        for key in ("low", "base", "high")
    )


def _date_key(report: Mapping[str, Any], path: Path) -> tuple[str, str, str]:
    """Prefer explicit report dates; use path only as a stable fallback.

    File mtimes are intentionally not used: touching a receipt must not change
    a canonical register.  A caller can pass reports in an explicit order when
    two receipts have no date metadata.
    """

    date = report.get("generated_at") or report.get("created_at") or report.get("valuation_date")
    return (str(date or ""), str(report.get("scope") or ""), str(path))


def discover_source_reports(runtime_root: Path, explicit: Iterable[Path] | None = None) -> list[Path]:
    """Discover source reports deterministically, without reading network data."""

    paths = sorted(runtime_root.joinpath("source-validation").glob("*/report.json"))
    paths.extend(sorted(runtime_root.parent.joinpath('us-refresh-group-verification').glob('*/report.json')))
    if explicit is not None: paths.extend(explicit)
    unique = {Path(path).resolve() for path in paths}
    return sorted(unique, key=str)


def _report_metadata(path: Path, report: Mapping[str, Any]) -> dict[str, Any]:
    counts = report.get("counts")
    if not isinstance(counts, Mapping):
        counts = {}
    rows = report.get("rows")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "scope": report.get("scope"),
        "row_count": len(rows) if isinstance(rows, list) else 0,
        "counts": dict(counts),
        "registry_sha256": report.get("registry_sha256"),
        "policy_sha256": report.get("policy_sha256"),
        "implementation_sha256": report.get("implementation_sha256"),
    }


def _row_status(row: Mapping[str, Any]) -> str:
    status = row.get("status") or row.get("migration_status") or row.get("state")
    return str(status or "").strip().lower()


def _explicit_bool(values: Iterable[Any], names: Sequence[str]) -> bool:
    for value in values:
        if isinstance(value, Mapping):
            for name in names:
                if value.get(name) is True:
                    return True
        elif value is True:
            return True
    return False


def _claim_mechanisms(text: str, *, special_claim_flag: bool) -> list[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    patterns = {
        "minority_interests": (
            r"\bminority interest(?:s)?\b",
            r"\bnoncontrolling interest(?:s)?\b",
            r"\bnci\b",
        ),
        "preferred_stock": (
            r"\bpreferred stock\b",
            r"\bpreferred equity\b",
            r"\bpreferred share(?:s)?\b",
            r"\bpreferred dividend(?:s)?\b",
            r"\bseries [a-z0-9]+ preferred\b",
        ),
        "acquisition_payments": (
            r"\bacquisition(?:s)?\b",
            r"\bacquired\b",
            r"\bpurchase consideration\b",
            r"\bmerger consideration\b",
            r"\bcontingent consideration\b",
        ),
        "litigation": (
            r"\blitigation\b",
            r"\blegal exposure\b",
            r"\blegal outcome\b",
            r"\blegal settlement\b",
            r"\blitigation settlement\b",
            r"\bsettlement reserve\b",
            r"\bcontingent legal\b",
        ),
        "timed_commitments": (
            r"\bcommitment(?:s)?\b",
            r"\bpurchase obligation(?:s)?\b",
            r"\bcontractual obligation(?:s)?\b",
            r"\btimed cash\b",
            r"\blease obligation(?:s)?\b",
        ),
        "post_filing_events": (
            r"\bpost filing\b",
            r"\bpost cutoff\b",
            r"\bpost period\b",
            r"\bsubsequent event\b",
            r"\bafter the quarter\b",
            r"\bafter cutoff\b",
        ),
        "operating_reserves": (
            r"\bpension\b",
            r"\bpostretirement\b",
            r"\bpostemployment\b",
            r"\brestructuring reserve\b",
            r"\benvironmental reserve\b",
            r"\boperating liability stress\b",
        ),
        "customer_funds": (
            r"\bcustomer funds source policy\b",
        ),
    }
    mechanisms = [
        mechanism
        for mechanism in CLAIM_MECHANISMS[:-1]
        if any(re.search(pattern, normalized) for pattern in patterns[mechanism])
    ]
    # A broad flag is not evidence of a mechanism.  Keep an explicit review
    # bucket when the source/private text does not identify one.
    if special_claim_flag and not mechanisms:
        mechanisms.append("unclassified_review")
    return mechanisms


def _special_claim_flag(values: Iterable[Any]) -> bool:
    for value in values:
        if isinstance(value, Mapping):
            for key in ("special_claim_flag", "special_claims", "has_special_claims", "claim_flag"):
                if value.get(key) is True:
                    return True
            # Some source receipts use an explicit categorical flag.
            for key in ("special_claim_status", "claim_status"):
                if str(value.get(key, "")).lower() in {"flagged", "review", "special"}:
                    return True
            reason_codes=value.get('reason_codes')
            if isinstance(reason_codes,(list,tuple)) and 'baseline_non_debt_claim_scope_requires_source_rule' in reason_codes:
                return True
        elif isinstance(value, str) and "special claim" in value.lower():
            return True
    return False


def _non_debt_claim_evidence(policy: Mapping[str, Any] | None, recipe: Mapping[str, Any] | None) -> str:
    """Extract explicit policy semantics only; numeric recipe slots are not evidence.

    Compiled source policies are stronger evidence than their legacy numeric
    field names.  Keep this deliberately schema-based so a generic selector or
    ticker flag cannot manufacture a financial classification.
    """

    parts: list[str] = []
    if isinstance(policy, Mapping):
        parts.extend(
            str(policy.get(key, ""))
            for key in ("explanation", "claim_explanation", "unresolved_economic_rules", "special_claim_flag", "special_claims", "claim_status")
            if policy.get(key)
        )
        reported_scope = policy.get("reported_claim_scope")
        if isinstance(reported_scope, Mapping) and reported_scope.get("version"):
            parts.append("reported noncontrolling interest NCI")
        schema_terms = {
            "FINSIGHT-ACQUISITION-CLAIM-1": "acquisition contingent consideration",
            "FINSIGHT-LITIGATION-CLAIM-1": "litigation legal settlement insurance recovery",
            "FINSIGHT-COMMITMENT-CLAIM-1": "timed contractual purchase commitment",
            "FINSIGHT-POST-FILING-EVENT-1": "post period subsequent event",
            "FINSIGHT-OPERATING-CLAIM-1": "pension postretirement postemployment restructuring reserve environmental reserve operating liability stress",
            "FINSIGHT-CUSTOMER-FUNDS-1": "customer funds source policy",
            "FINSIGHT-ACQUISITION-FINANCING-CLAIMS-1": "acquisition payments",
            "FINSIGHT-CONVERTIBLE-CLAIM-1": "preferred stock conversion shares",
        }
        inputs = policy.get("inputs")
        if isinstance(inputs, Mapping):
            for binding in inputs.values():
                if not isinstance(binding, Mapping) or binding.get("selector") != "special_claim":
                    continue
                claim_policy = binding.get("policy")
                if not isinstance(claim_policy, Mapping):
                    continue
                schema = claim_policy.get("schema_version")
                if schema in schema_terms:
                    parts.append(schema_terms[schema])
                if (schema=="FINSIGHT-ACQUISITION-FINANCING-CLAIMS-1"
                    and claim_policy.get("mode")=="complex_financing_review"):
                    parts.append("minority interests preferred stock financing claims")
                narrative = (claim_policy.get("scope_narrative")
                             or claim_policy.get("economic_treatment")
                             or claim_policy.get("treatment"))
                if isinstance(narrative, str):
                    parts.append(narrative)
        classification=policy.get('claim_classification')
        if isinstance(classification,Mapping) and classification.get('version'):
            parts.append(_short_text(classification.get('mechanisms')))
            parts.append(str(classification.get('reason') or ''))
    return " ".join(parts)


_PRIVATE_TEXT_KEYS = {
    'other_equity_claim_formula','claim_formula','bridge_formula',
    'treatment','operating_liability_treatment','nonrecurring_cash_adjustment',
}


def _verified_private_claim_evidence(recipe: Mapping[str, Any] | None) -> dict[str, Any]:
    """Read only hash-bound explanatory text; legacy numeric slot names prove nothing."""
    provenance=recipe.get('provenance') if isinstance(recipe,Mapping) else None
    if not isinstance(provenance,Mapping):
        return {'status':'missing','text':'','path':None,'sha256':None}
    source_path=provenance.get('source_path');expected=provenance.get('private_sha256')
    if not isinstance(source_path,str) or not isinstance(expected,str) or not re.fullmatch(r'[0-9a-f]{64}',expected):
        return {'status':'missing','text':'','path':source_path,'sha256':expected}
    path=Path(source_path)
    try: raw=path.read_bytes()
    except OSError:
        return {'status':'missing','text':'','path':source_path,'sha256':expected}
    actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected:
        return {'status':'hash_mismatch','text':'','path':source_path,'sha256':actual,'expected_sha256':expected}
    try: private=json.loads(raw)
    except json.JSONDecodeError:
        return {'status':'invalid_json','text':'','path':source_path,'sha256':actual}
    found=[]
    def walk(value):
        if isinstance(value,Mapping):
            for key,item in value.items():
                if key in _PRIVATE_TEXT_KEYS and isinstance(item,str) and item.strip(): found.append(item.strip())
                walk(item)
        elif isinstance(value,(list,tuple)):
            for item in value: walk(item)
    walk(private)
    return {'status':'verified','text':' '.join(dict.fromkeys(found)),'path':source_path,'sha256':actual}


def _claim_text(value: Any) -> str:
    """Text eligible for mechanism classification from a receipt/private row.

    Transport metadata such as ``acquisition_id``, packet paths, hashes and
    generic limitations are deliberately excluded: they describe how evidence
    was captured, not an issuer claim.
    """

    excluded = {
        "acquisition_id",
        "activated",
        "current_range",
        "previous_range",
        "limitations",
        "network_accessed",
        "path",
        "packet_directory",
        "raw_hashes",
        "source_capture",
        "source_ledger",
        "wrapper_sha256",
    }
    if isinstance(value, Mapping):
        parts: list[str] = []
        for key, item in value.items():
            if key in excluded or key.endswith("_sha256"):
                continue
            parts.append(str(key))
            parts.append(_claim_text(item))
        return " ".join(parts)
    if isinstance(value, (list, tuple, set)):
        return " ".join(_claim_text(item) for item in value)
    return str(value) if isinstance(value, str) else ""


def _blockers(
    *,
    status: str,
    reason: str | None,
    source_row: Mapping[str, Any] | None,
    policy_row: Mapping[str, Any] | None,
    prior_unavailable: bool,
) -> list[dict[str, str]]:
    source_status = _row_status(source_row or {})
    policy_status = _row_status(policy_row or {})
    text = " ".join(
        part for part in (status, source_status, policy_status, reason or "", _short_text(source_row)) if part
    ).lower()
    blockers: list[dict[str, str]] = []
    if prior_unavailable:
        blockers.append({"category": "prior_unavailable", "detail": reason or "No numeric baseline recipe."})
    if policy_status in {"implementation_required", "implementation_gap"} or "implementation" in text:
        blockers.append({"category": "implementation_gap", "detail": reason or "Refresh implementation is incomplete."})
    if source_status in {"cached_source_gap", "source_gap"} or any(
        phrase in text for phrase in ("source gap", "source selection failed", "missing source", "unresolved source", "retrieval failed")
    ):
        blockers.append({"category": "source_gap", "detail": reason or "Required source evidence is missing or unresolved."})
    if source_status in {"source_or_economic_review", "financial_review", "economic_review"} or any(
        phrase in text for phrase in ("financial review", "bridge review", "economic review", "financial judgment")
    ):
        blockers.append({"category": "financial_review", "detail": reason or "Financial interpretation still requires review."})
    return blockers


def _source_issue(source_row: Mapping[str,Any] | None, *, current: bool=False) -> dict[str,Any] | None:
    if not isinstance(source_row,Mapping): return None
    status=_row_status(source_row);reason=str(source_row.get('reason') or '')
    text=reason.lower()
    if status in {'cached_source_bound','source_bound'}:
        return {'category':'source_bound_current' if current else 'historical_source_bound_needs_recheck','detail':None}
    if status in {'implementation_gap','prior_unavailable'}: return None
    if any(phrase in text for phrase in ('no local companyfacts','download','retrieval','cached source packet','structural body is missing','package is missing')):
        category='acquisition_or_cache_failure'
    elif any(phrase in text for phrase in ('amount conflict','identity conflict','ambiguous','periods do not align','source selection failed')) and 'unresolved source fields' not in text:
        category='source_selector_conflict'
    elif any(phrase in text for phrase in ('unresolved source fields','no complete eligible filing evidence','is unavailable','is not evidenced','evidence is incomplete')):
        category='missing_financial_evidence'
    elif status in {'source_or_economic_review','financial_review','economic_review'}:
        category='financial_interpretation_review'
    elif status in {'cached_source_gap','source_gap'}:
        category='acquisition_or_cache_failure'
    else: category='unclassified_source_review'
    return {'category':category,'detail':reason or None}


def _choose_source_rows(
    report_items: Sequence[tuple[Path, Mapping[str, Any]]],
    *,
    registry_sha256: str | None,
    policy_sha256: str | None,
    implementation_sha256: str | None,
) -> dict[str, tuple[Mapping[str, Any], Path, bool]]:
    candidates: dict[str, list[tuple[tuple[Any, ...], Mapping[str, Any], Path, bool]]] = defaultdict(list)
    for path, report in report_items:
        rows = report.get("rows")
        if not isinstance(rows, list):
            continue
        current = (
            report.get("registry_sha256") == registry_sha256
            and report.get("policy_sha256") == policy_sha256
            and (
                report.get("implementation_sha256") == implementation_sha256
                if implementation_sha256 is not None
                else report.get("implementation_sha256") is None
            )
        )
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            ticker = _ticker(row, path=path)
            if not ticker:
                continue
            # Current-version evidence outranks historical evidence.  Within
            # a version, explicit source-bound rows outrank reviews/gaps, then
            # explicit date/scope/path order gives stable deterministic choice.
            source_status = _row_status(row)
            evidence_rank = {
                "cached_source_bound": 3,
                "source_bound": 3,
                "source_or_economic_review": 2,
                "financial_review": 2,
                "cached_source_gap": 1,
                "source_gap": 1,
            }.get(source_status, 0)
            report_rank = (1 if current else 0, evidence_rank, _date_key(report, path))
            candidates[ticker].append((report_rank, row, path, current))
    chosen: dict[str, tuple[Mapping[str, Any], Path, bool]] = {}
    for ticker, rows in candidates.items():
        rows.sort(key=lambda item: item[0], reverse=True)
        _, row, path, current = rows[0]
        chosen[ticker] = (row, path, current)
    return chosen


def _model_family(policy: Mapping[str, Any] | None, recipe: Mapping[str, Any] | None) -> str | None:
    for source in (policy or {}, recipe or {}):
        if not isinstance(source, Mapping):
            continue
        for key in ("family", "engine", "primary_model"):
            if source.get(key):
                return str(source[key])
    if recipe:
        engines = sorted({str(item.get("engine")) for item in recipe.get("scenarios", {}).values() if isinstance(item, Mapping) and item.get("engine")})
        if engines:
            return "+".join(engines)
    return None


def build_work_register(
    runtime_root: Path,
    *,
    source_reports: Iterable[Path] | None = None,
    expected_count: int = DEFAULT_EXPECTED_COUNT,
) -> dict[str, Any]:
    """Build the register from one frozen runtime root.

    ``expected_count`` is configurable solely for small synthetic tests; the
    production CLI defaults to the approved 440-company denominator.
    """

    runtime_root = Path(runtime_root)
    registry_path = runtime_root / "registry.json"
    baseline_manifest_path = runtime_root / "baseline" / "manifest.json"
    policy_report_path = runtime_root / "policy-compilation-report.json"
    migration_path = runtime_root / "migration-company-report.json"
    policies_path = runtime_root / "refresh-policies.json"
    required = [registry_path, baseline_manifest_path, policy_report_path]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    registry = _read_json(registry_path)
    baseline = _read_json(baseline_manifest_path)
    policy_report = _read_json(policy_report_path)
    migration = _read_json(migration_path) if migration_path.is_file() else {}
    policies = _read_json(policies_path) if policies_path.is_file() else {}
    registry_rows = _as_rows(registry.get("entries"), path=registry_path)
    baseline_rows = _as_rows(baseline.get("entries"), path=baseline_manifest_path)
    policy_rows = _as_rows(policy_report.get("rows"), path=policy_report_path)
    migration_rows = _as_rows(migration, path=migration_path) if migration else []

    def index(rows: Iterable[Mapping[str, Any]], *, path: Path) -> dict[str, Mapping[str, Any]]:
        result: dict[str, Mapping[str, Any]] = {}
        duplicates: list[str] = []
        for row in rows:
            ticker = _ticker(row, path=path)
            if not ticker:
                raise ValueError(f"{path}: row without ticker")
            if ticker in result:
                duplicates.append(ticker)
            result[ticker] = row
        if duplicates:
            raise ValueError(f"{path}: duplicate ticker(s): {sorted(set(duplicates))}")
        return result

    reg = index(registry_rows, path=registry_path)
    base = index(baseline_rows, path=baseline_manifest_path)
    compiled = index(policy_rows, path=policy_report_path)
    migration_index = index(migration_rows, path=migration_path) if migration_rows else {}
    tickers = sorted(reg)
    if len(tickers) != expected_count:
        raise ValueError(f"{registry_path}: expected exactly {expected_count} unique companies, found {len(tickers)}")
    if set(base) != set(tickers):
        raise ValueError("registry and baseline do not cover the same companies")
    if set(compiled) - set(tickers):
        raise ValueError("policy compilation report contains issuers outside the registry")

    # Source receipts pin the registry JSON itself (not the baseline catalog
    # manifest referenced by the registry).  Keep both identities visible in
    # the output and compare the right one for current-version evidence.
    registry_sha = sha256_file(registry_path)
    policy_sha = policy_report.get("policy_sha256")
    implementation_sha = implementation_fingerprint()
    report_paths = discover_source_reports(runtime_root, source_reports)
    report_items: list[tuple[Path, Mapping[str, Any]]] = []
    report_metadata: list[dict[str, Any]] = []
    for path in report_paths:
        report = _read_json(path)
        if not isinstance(report, Mapping):
            raise ValueError(f"{path}: expected an object")
        report_items.append((path, report))
        report_metadata.append(_report_metadata(path, report))
    chosen_source = _choose_source_rows(
        report_items,
        registry_sha256=registry_sha,
        policy_sha256=policy_sha,
        implementation_sha256=implementation_sha,
    )

    version_fingerprints = {
        tuple(str(report.get(key) or "") for key in ("registry_sha256", "policy_sha256", "implementation_sha256"))
        for _, report in report_items
        if any(report.get(key) for key in ("registry_sha256", "policy_sha256", "implementation_sha256"))
    }
    incomplete_fingerprints = any(
        not all(report.get(key) for key in ("registry_sha256", "policy_sha256", "implementation_sha256"))
        for _, report in report_items
    )
    source_composable = bool(report_items) and not incomplete_fingerprints and len(version_fingerprints) == 1
    if incomplete_fingerprints:
        source_composability_reason = "At least one source receipt omits a version hash; unknown dependencies require rechecking and receipts are not composable as one run."
    elif source_composable:
        source_composability_reason = "All considered source receipts share one version fingerprint."
    else:
        source_composability_reason = "Source receipts carry different registry/policy/implementation hashes; they are evidence only and are not composable as one run."

    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        registry_row = reg[ticker]
        baseline_row = base[ticker]
        policy_row = compiled.get(ticker, {})
        migration_row = migration_index.get(ticker, {})
        recipe_path = runtime_root / "recipes" / f"{ticker}.json"
        recipe = _read_json(recipe_path) if recipe_path.is_file() else None
        source_entry = chosen_source.get(ticker)
        source_row, source_path, source_current = source_entry if source_entry else (None, None, False)
        source_status = _row_status(source_row or {})
        source_issue=_source_issue(source_row,current=source_current)
        policy_status = _row_status(policy_row)
        recipe_ready = bool(recipe is not None and _finite_replay(recipe))
        instruction_compiled = policy_status == "contract_compiled"
        source_bound_current = bool(source_current and source_status in {"cached_source_bound", "source_bound"})
        source_needs_recheck = bool(source_path and not source_current)
        successive = _explicit_bool(
            (registry_row, baseline_row, policy_row, migration_row, source_row or {}),
            ("successive_period_verified", "successive_filing_verified", "successive_real_filing_verified"),
        )
        baseline_unavailable = bool(
            registry_row.get("availability_type") == "not_available"
            or baseline_row.get("availability_type") == "not_available"
        )
        # Missing/invalid replay for an otherwise numeric baseline is an
        # implementation gap.  Only an explicitly unavailable baseline is a
        # prior-unavailable state.
        recipe_implementation_gap = bool(not recipe_ready and not baseline_unavailable)
        prior_unavailable = bool(
            baseline_unavailable
            or (policy_status == "prior_unavailable" and not recipe_implementation_gap)
            or (str(migration_row.get("migration_status", "")).lower() == "prior_unavailable" and not recipe_implementation_gap)
        )
        reasons = list(dict.fromkeys(
            value
            for value in (
                policy_row.get("reason"),
                source_row.get("reason") if source_row else None,
                migration_row.get("reason"),
            )
            if value
        ))
        policy = policies.get(ticker) if isinstance(policies, Mapping) else None
        private_claim_evidence=_verified_private_claim_evidence(recipe)
        # Generic concept configuration is not claim evidence.  Mechanisms are
        # classified from source receipt/private migration text plus explicit
        # non-debt values only, so every broad flag remains reviewable.
        explicit_flag = _special_claim_flag((registry_row, baseline_row, policy_row, migration_row, source_row or {}, policy or {}))
        # Classify the broad claim-migration flag from claim-specific text.
        # Generic source fields such as "noncontrolling_interests missing" and
        # unrelated invalidation warnings are not proof of the old slot's
        # economic mechanism.
        claim_text = " ".join(_claim_text(value) for value in (
            migration_row,_non_debt_claim_evidence(policy,recipe),private_claim_evidence['text']))
        mechanisms = _claim_mechanisms(claim_text, special_claim_flag=explicit_flag)
        special_flag = explicit_flag
        blocker_reason = "; ".join(str(item) for item in reasons) or None
        if recipe_implementation_gap:
            blocker_reason = "; ".join(
                item
                for item in (blocker_reason, "Numeric baseline exists but its replay recipe is missing or invalid.")
                if item
            )
        blockers = _blockers(
            status="implementation_gap" if recipe_implementation_gap else policy_status,
            reason=blocker_reason,
            source_row=source_row,
            policy_row=policy_row,
            prior_unavailable=prior_unavailable,
        )
        status_labels = []
        if recipe_ready:
            status_labels.append("recipe_ready")
        if instruction_compiled:
            status_labels.append("instruction_compiled")
        if source_bound_current:
            status_labels.append("source_bound_current_version")
        if successive:
            status_labels.append("successive_period_verified")
        if any(item["category"] == "source_gap" for item in blockers):
            status_labels.append("source_gap")
        if any(item["category"] == "financial_review" for item in blockers):
            status_labels.append("financial_review")
        if any(item["category"] == "implementation_gap" for item in blockers):
            status_labels.append("implementation_gap")
        if prior_unavailable:
            status_labels.append("prior_unavailable")
        dependencies = {
            "policy_sha256": policy_sha,
            "implementation_sha256": implementation_sha,
            "registry_sha256": registry_sha,
            "policy_version": policy.get("version") if isinstance(policy, Mapping) else None,
            "family": _model_family(policy, recipe),
            "source_requirements": policy.get("source_requirements", {}) if isinstance(policy, Mapping) else {},
            "required_fields": sorted(
                (policy.get("inputs") or {}).keys()
                if isinstance(policy, Mapping) and isinstance(policy.get("inputs"), Mapping)
                else (policy.get("concept_config", {}).get("fields", {}) or {}).keys()
                if isinstance(policy, Mapping) and isinstance(policy.get("concept_config"), Mapping)
                else []
            ),
        }
        rows.append(
            {
                "ticker": ticker,
                "batch": registry_row.get("batch"),
                "cik": registry_row.get("cik"),
                # Keep the gate fields flat for simple consumers; the nested
                # ``states`` object is the canonical grouped view.
                "recipe_ready": recipe_ready,
                "instruction_compiled": instruction_compiled,
                "source_bound_current_version": source_bound_current,
                "successive_period_verified": successive,
                "source_gap": any(item["category"] == "source_gap" for item in blockers),
                "financial_review": any(item["category"] == "financial_review" for item in blockers),
                "implementation_gap": any(item["category"] == "implementation_gap" for item in blockers),
                "prior_unavailable": prior_unavailable,
                "needs_recheck": source_needs_recheck,
                "baseline": {
                    "availability_type": baseline_row.get("availability_type", registry_row.get("availability_type")),
                    "artifact_sha256": baseline_row.get("artifact_sha256", registry_row.get("baseline_sha256")),
                    "source_audit": baseline_row.get("source_audit", registry_row.get("source_audit")),
                },
                "states": {
                    "recipe_ready": recipe_ready,
                    "instruction_compiled": instruction_compiled,
                    "source_bound_current_version": source_bound_current,
                    "successive_period_verified": successive,
                    "source_gap": any(item["category"] == "source_gap" for item in blockers),
                    "financial_review": any(item["category"] == "financial_review" for item in blockers),
                    "implementation_gap": any(item["category"] == "implementation_gap" for item in blockers),
                    "prior_unavailable": prior_unavailable,
                    "needs_recheck": source_needs_recheck,
                },
                "status_labels": status_labels,
                "policy_dependencies": dependencies,
                "blockers": blockers,
                "special_claims": {
                    "flagged": special_flag,
                    "mechanisms": mechanisms,
                    "classification_basis": "explicit source/private text" if mechanisms and mechanisms != ["unclassified_review"] else "explicit broad flag without a supported mechanism; review required" if special_flag else None,
                    "evidence_basis": {
                        "kind": "source_or_private_text" if mechanisms and mechanisms != ["unclassified_review"] else "unknown" if special_flag else None,
                        "source_report": str(source_path) if source_path and mechanisms else None,
                        "private_source": private_claim_evidence,
                        "note": "Mechanism labels are a review aid grounded in retained text; an explicit broad flag without text remains unclassified."
                        if special_flag
                        else None,
                    },
                },
                "evidence": {
                    "registry_source_audit": registry_row.get("source_audit"),
                    "migration_status": migration_row.get("migration_status"),
                    "migration_report": str(migration_path) if migration_rows else None,
                    "recipe_path": str(recipe_path) if recipe_ready else None,
                    "policy_report": str(policy_report_path),
                    "source_report": str(source_path) if source_path else None,
                    "source_report_current_version": source_current,
                    "source_report_version": {
                        "registry_sha256": (
                            next(
                                (metadata.get("registry_sha256") for metadata in report_metadata if metadata.get("path") == str(source_path)),
                                None,
                            )
                            if source_path
                            else None
                        ),
                        "policy_sha256": (
                            next(
                                (metadata.get("policy_sha256") for metadata in report_metadata if metadata.get("path") == str(source_path)),
                                None,
                            )
                            if source_path
                            else None
                        ),
                        "implementation_sha256": (
                            next(
                                (metadata.get("implementation_sha256") for metadata in report_metadata if metadata.get("path") == str(source_path)),
                                None,
                            )
                            if source_path
                            else None
                        ),
                    },
                    "historical_source_evidence": {
                        "report": str(source_path),
                        "status": source_status,
                        "needs_recheck": source_needs_recheck,
                    }
                    if source_path and source_needs_recheck
                    else None,
                    "needs_recheck": source_needs_recheck,
                    "source_paths": _extract_paths(source_row or {}),
                },
                "source_report_status": source_status or None,
                "source_issue":source_issue,
                "primary_model": registry_row.get("primary_model"),
                "model_family": _model_family(policy, recipe),
                "controlling_filing": registry_row.get("controlling_filing"),
                "next_action": (
                    "Resolve prior unavailable input and run the separately authorized recovery."
                    if prior_unavailable
                    else "Restore or validate the numeric replay recipe, then rerun compilation."
                    if recipe_implementation_gap
                    else "Implement the missing family/issuer rule, then rerun source validation."
                    if any(item["category"] == "implementation_gap" for item in blockers)
                    else "Resolve the named source gap, then rerun the bounded source check."
                    if any(item["category"] == "source_gap" for item in blockers)
                    else "Complete financial bridge review and independently verify the source-bound calculation."
                    if any(item["category"] == "financial_review" for item in blockers)
                    else "Run the next filing through the current policy and verify a successive period."
                ),
            }
        )

    counts = Counter()
    for row in rows:
        for key, value in row["states"].items():
            if value:
                counts[key] += 1
    for key in (
        "recipe_ready",
        "instruction_compiled",
        "source_bound_current_version",
        "successive_period_verified",
        "source_gap",
        "financial_review",
        "implementation_gap",
        "prior_unavailable",
        "needs_recheck",
    ):
        counts.setdefault(key, 0)
    claim_counts = Counter(
        mechanism
        for row in rows
        for mechanism in row["special_claims"]["mechanisms"]
    )
    source_issue_counts=Counter(row['source_issue']['category'] for row in rows if row.get('source_issue'))
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        for mechanism in row["special_claims"]["mechanisms"]:
            group = groups.setdefault(
                mechanism,
                {"mechanism": mechanism, "company_count": 0, "tickers": [], "source_supported_count": 0,
                 "planning_evidence_count":0},
            )
            group["company_count"] += 1
            group["tickers"].append(row["ticker"])
            # A stale receipt or a source-gap report is not source-supported
            # current evidence.  Only a current-version bound row contributes
            # to working-group reuse.
            if row["states"]["source_bound_current_version"]:
                group["source_supported_count"] += 1
            evidence=row['special_claims']['evidence_basis']
            if evidence.get('source_report') or evidence.get('private_source',{}).get('status')=='verified':
                group['planning_evidence_count'] += 1
    for group in groups.values():
        group["tickers"] = sorted(group["tickers"])
        group["acceptance_test"] = "Prove the mechanism on one representative and one difficult source-bound case, then validate every listed ticker."
    working_groups = sorted(
        groups.values(),
        key=lambda group: (-group["source_supported_count"],-group['planning_evidence_count'], -group["company_count"], group["mechanism"]),
    )
    eligible_groups = [group for group in working_groups if group["planning_evidence_count"] > 0 and group['mechanism']!='unclassified_review']
    next_group = eligible_groups[0] if eligible_groups else None
    adapter_rows = []
    for row in rows:
        policy_row = compiled.get(row["ticker"], {})
        reason = str(policy_row.get("reason") or "")
        if reason.lower().startswith("family adapter required"):
            adapter_rows.append(
                {
                    "ticker": row["ticker"],
                    "reason": reason,
                    "model_family": row.get("model_family"),
                }
            )
    implementation_queue = {
        "family_adapter_count": len(adapter_rows),
        "family_adapters": sorted(adapter_rows, key=lambda item: item["ticker"]),
        "other_implementation_gap_count": counts["implementation_gap"] - len(adapter_rows),
    }
    summary = {
        "what_works": [
            f"{counts['recipe_ready']} companies have finite replayable numeric recipes.",
            f"{counts['instruction_compiled']} companies have compiled refresh contracts.",
            f"{counts['source_bound_current_version']} companies have source-bound evidence on the current version.",
            f"{counts['successive_period_verified']} companies have explicit successive-period evidence (never inferred).",
        ],
        "what_was_fixed": "The register separates replay, compilation, current source binding, and successive-period verification so historical counts cannot be added into release readiness.",
        "what_is_blocked": {
            "implementation_gap": counts["implementation_gap"],
            "source_gap": counts["source_gap"],
            "financial_review": counts["financial_review"],
            "prior_unavailable": counts["prior_unavailable"],
        },
        "what_needs_rechecking": sorted(
            row["ticker"]
            for row in rows
            if row["evidence"]["source_report"] and not row["evidence"]["source_report_current_version"]
        ),
        "next": {
            "working_group": next_group,
            "acceptance_test": next_group["acceptance_test"] if next_group else "Select the highest-reuse source-supported group after the first source run.",
        },
    }

    input_hashes = {str(path): sha256_file(path) for path in required}
    input_hashes.update({str(path): sha256_file(path) for path in (migration_path, policies_path) if path.is_file()})
    result = {
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "universe": "US-RESET-2026-08-14-B01-B44",
            "batches": list(range(1, 45)),
            "denominator": expected_count,
            "registry_count": len(rows),
            "recipe_count": sum(row["states"]["recipe_ready"] for row in rows),
        },
        "inputs": {
            "sha256": input_hashes,
            "registry": str(registry_path),
            "baseline_manifest": str(baseline_manifest_path),
            "policy_compilation_report": str(policy_report_path),
            "migration_report": str(migration_path) if migration_path.is_file() else None,
            "policies": str(policies_path) if policies_path.is_file() else None,
        },
        "source_reports": {
            "considered": report_metadata,
            "composable": source_composable,
            "composability_reason": source_composability_reason,
            "version_fingerprints": [list(item) for item in sorted(version_fingerprints)],
        },
        "counts": dict(sorted(counts.items())),
        "claim_mechanism_counts": dict(sorted(claim_counts.items())),
        "source_issue_counts":dict(sorted(source_issue_counts.items())),
        "working_groups": working_groups,
        "implementation_queue": implementation_queue,
        "summary": summary,
        "companies": rows,
    }
    return result


def render_markdown(register: Mapping[str, Any]) -> str:
    """Render the concise plain-language companion report."""

    scope = register["scope"]
    counts = register.get("counts", {})
    summary = register.get("summary", {})
    lines = [
        "# FinSight refresh work register",
        "",
        f"Scope: **{scope['registry_count']}/{scope['denominator']} companies** in Batches 01–44. This is a work register, not a release-readiness percentage.",
        "",
        "## What works",
        "",
    ]
    lines.extend(f"- {item}" for item in summary.get("what_works", []))
    lines.extend(["", "## What changed", "", f"- {summary.get('what_was_fixed', '')}", "", "## What is blocked", ""])
    for key in ("implementation_gap", "source_gap", "financial_review", "prior_unavailable"):
        lines.append(f"- {key.replace('_', ' ').title()}: **{counts.get(key, 0)}**")
    lines.extend(["", "## What needs rechecking", ""])
    recheck = summary.get("what_needs_rechecking", [])
    lines.append(
        f"- **{len(recheck)}** source result(s) come from a different version fingerprint and must be rechecked before reuse."
    )
    if recheck:
        preview=recheck[:20]
        lines.append(f"- Examples: {', '.join(preview)}" + (f"; full list of {len(recheck)} is in work-register.json." if len(recheck)>len(preview) else "."))
    lines.extend(["", "## Next working group", ""])
    group = (summary.get("next") or {}).get("working_group")
    if group:
        lines.append(
            f"- **{group['mechanism'].replace('_', ' ').title()}**: {group['company_count']} company(ies), {group['planning_evidence_count']} with hash-verified planning evidence, {group['source_supported_count']} source-bound on the current version."
        )
        lines.append(f"- Acceptance test: {group['acceptance_test']}")
    else:
        lines.append("- Select the highest-reuse source-supported group after the first source run.")
    lines.extend(["", "## Source problem types", ""])
    for key,value in register.get('source_issue_counts',{}).items(): lines.append(f"- {key.replace('_',' ').title()}: **{value}**")
    lines.extend(["", "## Integrity notes", "", f"- Source receipts composable as one run: **{str(register['source_reports']['composable']).lower()}**.", f"- Claim mechanism counts: {json.dumps(register.get('claim_mechanism_counts', {}), sort_keys=True)}", "- Blocker counts overlap: one company can have implementation, source, and financial-review work at the same time.", "- Instructions written, real filing verified, and successive quarterly verification remain separate fields.", ""])
    return "\n".join(lines)


__all__ = [
    "CLAIM_MECHANISMS",
    "DEFAULT_EXPECTED_COUNT",
    "SCHEMA_VERSION",
    "build_work_register",
    "canonical_json_bytes",
    "discover_source_reports",
    "render_markdown",
]
