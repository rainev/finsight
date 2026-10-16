"""Closed B11--B15 staged public inheritance for the admitted600 parent.

This module is deliberately separate from the closed Batch05 validator.  It
only validates an unadmitted, read-only 650-company public candidate.  The
immutable issuer, source, classification, warning, recipe and economic pins
are supplied by ``config/staged_b1115_anchors.json`` and are checked before
any candidate is accepted.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from .artifacts import sanitize_public_artifact
from .calculation_recipe import evaluate_recipe


SCHEMA = "US-B11-B15-APPROVED-PARENT-INHERITANCE-1"
REVIEW_SCHEMA = "US-B11-B15-READ-ONLY-STAGED-REVIEW-1"
SOURCE_DISCLOSURE_SCHEMA = "US-B11-B15-APPROVED-PUBLIC-SOURCE-DISCLOSURE-BINDING-1"
CUTOFF = "2026-10-08"
PUBLIC_POLICY_VERSION = "US-B11-B15-PUBLIC-COMMON-RI-1"
ANCHORS_SHA = "3fed1617954de7e16bbab7cab38d4150c698808fcc6597eccd148e89e1569201"
_ANCHOR_FILE = "staged_b1115_anchors.json"
_PENDING = "PENDING_ROOT_ANCHORS_SHA"

NEGATED_OWNER_WARNING = (
    "NetIncomeLoss follows the primary FASB parent-attribution tag semantics; "
    "ProfitLoss is not used as a common-owner fallback and no NCI is subtracted again."
)

AUTHORITY_FIELDS = {
    "schema_version",
    "read_only",
    "manifest_sha256",
    "catalog_version",
    "registry_sha256",
    "admission",
    "activation",
    "publication",
    "save",
    "automatic_new_source_revaluation",
}

ROOT_FILES = {
    "manifest.json",
    "refresh-policies.json",
    "approved-base-manifest.json",
    "approved-parent-manifest.json",
    "approved-parent-registry.json",
    "approved-parent-policies.json",
    "public-scope-authorization.json",
    "source-disclosure-binding.json",
}
EXPECTED_PUBLIC_COUNTS = {
    "available": 116,
    "conditional_estimate": 456,
    "not_available": 78,
}


def _canonical_sha(value: object) -> str:
    raw = (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _load_anchor_config(*, verify: bool = True) -> dict:
    path = Path(__file__).with_name("config") / _ANCHOR_FILE
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("B11-B15 staged anchor configuration is missing or invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("B11-B15 staged anchor configuration must be an object")
    if verify:
        if ANCHORS_SHA == _PENDING:
            raise ValueError("B11-B15 staged anchor SHA is not root-bound")
        if _canonical_sha(value) != ANCHORS_SHA:
            raise ValueError("B11-B15 staged anchor configuration hash mismatch")
    return value


# Root binds ANCHORS_SHA after installing the immutable config.  Importing the
# module before that handoff is intentionally fail-closed.
ANCHORS = _load_anchor_config(verify=True)


def _anchor_value(*names: str, default: object = None) -> object:
    nested = ANCHORS.get("accepted_anchors")
    sources = [ANCHORS]
    if isinstance(nested, dict):
        sources.append(nested)
    for source in sources:
        for name in names:
            if name in source:
                return source[name]
    return default


def _required_anchor(*names: str) -> object:
    value = _anchor_value(*names)
    if value is None:
        raise ValueError("B11-B15 staged anchor is missing: " + "/".join(names))
    return value


def _verified_anchors() -> dict:
    # Reload on every validation.  This prevents an in-process config mutation
    # from being hidden by the import-time object.
    if ANCHORS_SHA == _PENDING or _canonical_sha(ANCHORS) != ANCHORS_SHA:
        raise ValueError("B11-B15 in-memory anchor configuration hash mismatch")
    fresh = _load_anchor_config(verify=True)
    if _canonical_sha(fresh) != _canonical_sha(ANCHORS):
        raise ValueError("B11-B15 anchor configuration changed in process")
    return fresh


def _as_cik(value: object) -> str:
    return str(value).zfill(10)


def _as_map(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError("B11-B15 staged anchor map is invalid: " + label)
    return value


def _string_set(value: object, label: str) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError("B11-B15 staged anchor ticker set is invalid: " + label)
    return frozenset(value)


_IDENTITIES = _as_map(_required_anchor("identities", "new_identities"), "identities")
IDENTITIES = {ticker: _as_cik(cik) for ticker, cik in _IDENTITIES.items()}
TARGETS = _string_set(
    _required_anchor("targets", "numeric_tickers", "public_targets"), "targets"
)
NULLS = _string_set(
    _required_anchor("public_nulls", "null_tickers", "withheld_tickers"), "public_nulls"
)
if (
    len(IDENTITIES) != 50
    or len(TARGETS) != 29
    or len(NULLS) != 21
    or TARGETS | NULLS != frozenset(IDENTITIES)
    or TARGETS & NULLS
):
    raise ValueError("B11-B15 staged anchor scope must contain exactly 29/21 of 50 issuers")

BATCHES = {ticker: int(batch) for ticker, batch in _as_map(
    _required_anchor("catalog_batches", "batches"), "catalog_batches"
).items()}
if (
    set(BATCHES) != set(IDENTITIES)
    or Counter(BATCHES.values()) != Counter({61: 10, 62: 10, 63: 10, 64: 10, 65: 10})
):
    raise ValueError("B11-B15 staged batches must cover only batches 61 through 65")


def require(value: object, why: str) -> None:
    if not value:
        raise ValueError("B11-B15 staged review rejected: " + why)


def _rows(manifest: dict) -> dict[str, tuple]:
    return {
        entry["ticker"]: (
            _as_cik(entry["cik"]),
            entry["batch"],
            entry["availability_type"],
            entry["artifact_sha256"],
        )
        for entry in manifest["entries"]
    }


def _private_pin(ticker: str, key: str) -> object:
    pins = _as_map(_required_anchor("private_pins", "confirmed_private650_pins"), "private_pins")
    record = pins.get(ticker)
    require(isinstance(record, dict), ticker + " private650 pin is missing")
    aliases = {
        "artifact": (
            "confirmed_private650_artifact_sha256",
            "private650_artifact_sha256",
            "artifact",
            "artifact_sha256",
        ),
        "recipe": (
            "confirmed_private650_recipe_sha256",
            "private650_recipe_sha256",
            "recipe",
            "recipe_sha256",
        ),
        "source_ledger": (
            "confirmed_private650_source_ledger_sha256",
            "private650_source_ledger_sha256",
            "source_ledger",
            "source_ledger_sha256",
        ),
    }
    for name in aliases[key]:
        if name in record:
            return record[name]
    return None


def _source_header_expected(ticker: str) -> object:
    values = _as_map(
        _required_anchor("source_header_values", "source_headers"),
        "source_header_values",
    )
    require(ticker in values, ticker + " source header value is missing")
    return values[ticker]


def _source_header_matches(actual: object, expected: object) -> bool:
    if isinstance(expected, dict):
        if "value" in expected and not _source_header_matches(actual, expected["value"]):
            return False
        digest = expected.get("sha256")
        if digest is not None and _canonical_sha(actual) != digest:
            return False
        if "value" in expected or digest is not None:
            return True
    return actual == expected


def _normalized_header(value: object) -> bool:
    return isinstance(value, dict) and isinstance(value.get("url"), str) and bool(value["url"])


def _classification_expected(ticker: str) -> dict:
    values = _as_map(
        _required_anchor("target_classification", "classifications"),
        "target_classification",
    )
    expected = values.get(ticker)
    require(isinstance(expected, dict), ticker + " target classification is missing")
    return expected


def _check_classification(artifact: dict, ticker: str) -> None:
    expected = _classification_expected(ticker)
    issuer = artifact.get("issuer", {})
    require(issuer.get("ticker") == ticker, ticker + " classification identity changed")
    require(issuer.get("override_applied") is True, ticker + " classification override is not explicit")
    aliases = {
        "archetype": ("primary_archetype", "archetype"),
        "primary_archetype": ("primary_archetype", "archetype"),
        "confidence": ("classification_confidence", "confidence"),
        "classification_confidence": ("classification_confidence", "confidence"),
        "reason": ("classification_reason", "reason"),
        "classification_reason": ("classification_reason", "reason"),
        "mapping": ("classification_mapping", "mapping"),
        "classification_mapping": ("classification_mapping", "mapping"),
    }
    for key, expected_value in expected.items():
        if key == "override_applied":
            require(issuer.get(key) is expected_value, ticker + " classification override changed")
            continue
        actual = None
        for alias in aliases.get(key, (key,)):
            if alias in issuer:
                actual = issuer[alias]
                break
        require(actual == expected_value, ticker + " classification " + key + " changed")


def _warning_view(artifact: dict) -> dict:
    review = artifact.get("review", {})
    models = artifact.get("models", {})
    scenarios = artifact.get("scenarios", {})
    return {
        "review": review.get("warnings", []) if isinstance(review, dict) else None,
        "models": {
            name: model.get("warnings", [])
            for name, model in models.items()
            if isinstance(model, dict)
        }
        if isinstance(models, dict)
        else None,
        "scenarios": {
            scenario_name: {
                model_name: model.get("warnings", [])
                for model_name, model in scenario.items()
                if isinstance(model, dict)
            }
            for scenario_name, scenario in scenarios.items()
            if isinstance(scenario, dict)
        }
        if isinstance(scenarios, dict)
        else None,
    }


def _warnings_match(artifact: dict, ticker: str) -> bool:
    expected_map = _as_map(
        _required_anchor("retained_warnings", "warnings"), "retained_warnings"
    )
    expected = expected_map.get(ticker)
    require(expected is not None, ticker + " retained warnings are missing")
    actual = _warning_view(artifact)
    if isinstance(expected, list):
        return set(expected) <= set(actual["review"] or [])
    if not isinstance(expected, dict):
        return False
    origin = expected.get(
        "origin_review_warnings",
        expected.get("origin", expected.get("review_warnings", expected.get("review", []))),
    )
    if not isinstance(origin, list) or not set(origin) <= set(actual["review"] or []):
        return False
    public = expected.get(
        "public_warnings",
        expected.get(
            "public_warning_view",
            expected.get("public_review_warnings", expected.get("expected_public_warnings")),
        ),
    )
    if public is not None and actual["review"] != public:
        return False
    aliases = {"model_warnings": "models", "scenario_warnings": "scenarios"}
    for key, value in expected.items():
        actual_key = aliases.get(key)
        if actual_key is not None and actual[actual_key] != value:
            return False
    return True


def source_bound_negated_owner_warning(artifact: dict, warning: str) -> bool:
    """Return true only for the exact source-bound owner warning exception.

    This is intentionally a predicate, not a sanitizer bypass.  Callers must
    still reject every other unsupported or hard warning.
    """
    if warning != NEGATED_OWNER_WARNING or not isinstance(artifact, dict):
        return False
    try:
        _verified_anchors()
    except (KeyError, TypeError, ValueError):
        return False
    ticker = artifact.get("ticker")
    issuer = artifact.get("issuer", {})
    if ticker not in TARGETS or not isinstance(issuer, dict):
        return False
    if ticker != issuer.get("ticker") or _as_cik(issuer.get("cik")) != IDENTITIES[ticker]:
        return False
    if artifact.get("model_version") != PUBLIC_POLICY_VERSION:
        return False
    assumptions = artifact.get("public_assumptions", {})
    policy = artifact.get("model_policy", {})
    if not isinstance(assumptions, dict) or not isinstance(policy, dict):
        return False
    source_sha = _required_anchor("source_disclosure_sha256")
    if (
        assumptions.get("forecast_policy_version") != PUBLIC_POLICY_VERSION
        or assumptions.get("source_policy_binding_sha256") != source_sha
        or policy.get("primary") != "residual_income"
        or artifact.get("availability_type") != "conditional_estimate"
        or artifact.get("reliability", {}).get("label") != "Low"
        or artifact.get("valuation_date") != CUTOFF
        or artifact.get("assumption_date") != CUTOFF
    ):
        return False
    try:
        if not _normalized_header(artifact.get("source_financial_statement")):
            return False
        if not _source_header_matches(
            artifact.get("source_financial_statement"), _source_header_expected(ticker)
        ):
            return False
        if not _warnings_match(artifact, ticker):
            return False
        if warning not in (_warning_view(artifact).get("review") or []):
            return False
        _check_classification(artifact, ticker)
    except (KeyError, TypeError, ValueError):
        return False
    return True


def _gate_flag(gate: dict, *names: str) -> object:
    for name in names:
        if name in gate:
            return gate[name]
    return None


def validate_source_disclosure(proof_reader, root):
    """Validate the immutable V2 source-binding record without release authority."""
    expected_sha = _required_anchor("source_disclosure_sha256")
    proof = proof_reader(root, "source-disclosure-binding.json", expected_sha)
    require(isinstance(proof, dict), "source disclosure binding is not an object")
    require(proof.get("schema_version") == SOURCE_DISCLOSURE_SCHEMA, "source disclosure schema changed")
    require(proof.get("cutoff") == CUTOFF, "source disclosure cutoff changed")
    require(set(proof.get("targets", [])) == set(TARGETS), "source disclosure targets changed")
    require(set(proof.get("public_nulls", [])) == set(NULLS), "source disclosure null scope changed")
    require(proof.get("approved_scope_sha256", proof.get("scope_approval_sha256"))
            == _required_anchor("scope_approval_sha256", "approval_sha256"),
            "source disclosure scope pin changed")
    require(proof.get("approved_proposal_sha256", proof.get("proposal_sha256"))
            == _required_anchor("proposal_sha256", "proposed_scope_sha256"),
            "source disclosure proposal pin changed")
    require(proof.get("acceptance_cutoff_UTC", proof.get("acceptance"))
            == _required_anchor("acceptance_cutoff_UTC", "acceptance"),
            "source disclosure acceptance pin changed")
    for key in ("admission", "activation", "publication", "automatic_new_source_revaluation"):
        require(proof.get(key) is False, "source disclosure grants " + key)
    for key in (
        "facts_and_forecast_assumptions_separate",
        "no_new_source_capture_or_economic_normalization",
        "no_new_valuation_inputs_or_floor",
        "all_private_values_and_filing_holds_unchanged",
        "no_new_inputs",
        "no_floor",
        "no_source_capture",
        "no_normalization",
    ):
        require(proof.get(key) is True, "source disclosure preservation gate missing: " + key)
    records = proof.get("records")
    require(isinstance(records, dict) and set(records) == set(IDENTITIES),
            "source disclosure record membership changed")
    for ticker, record in records.items():
        require(isinstance(record, dict), ticker + " source disclosure record malformed")
        identity = record.get("identity", {})
        require(identity.get("ticker") == ticker and _as_cik(identity.get("cik")) == IDENTITIES[ticker],
                ticker + " source identity changed")
        gate = record.get("gate")
        require(isinstance(gate, dict), ticker + " source gate is missing")
        if ticker in TARGETS:
            require(gate.get("ready") is True, ticker + " source gate is not ready")
            for key in ("unchanged_value_gate","source_scope_checked","periods_units_contexts_checked",
                        "owner_common_scope_checked","point_shares_checked","facts_forecast_separated","anchor_input_checked"):
                require(gate.get(key) is True, ticker + " " + key + " is not ready")
        else:
            require(gate.get("ready") is False, ticker + " null source gate became ready")
        require(
            record.get("confirmed_private650_artifact_sha256") == _private_pin(ticker, "artifact"),
            ticker + " confirmed private650 artifact pin changed",
        )
        if ticker in {'CBT','UTMD'}:
            require(record.get('dated_only') == {'financial_reference_date':'2026-06-30','current_post_event_value_held':True}, ticker + ' source dated-only scope changed')
        expected_recipe = _private_pin(ticker, "recipe")
        require(record.get("confirmed_private650_recipe_sha256") == expected_recipe,
                ticker + " confirmed private650 recipe pin changed")
        require(record.get("source_ledger_sha256")
                == _private_pin(ticker, "source_ledger"),
                ticker + " confirmed private650 source-ledger pin changed")
        header = record.get("source_header")
        require(isinstance(header, dict) and header.get("url"), ticker + " normalized source header/url missing")
        require(_source_header_matches(header, _source_header_expected(ticker)),
                ticker + " normalized source header changed")
        proofs = record.get("primary_proofs")
        require(isinstance(proofs, list), ticker + " primary proof list malformed")
        for source in proofs:
            require(isinstance(source, dict), ticker + " primary proof malformed")
            for date_key in ("filed_date", "report_date"):
                if date_key in source:
                    require(isinstance(source[date_key], str) and source[date_key] <= CUTOFF,
                            ticker + " post-cutoff source proof")
    return proof


def _validate_public_artifact(proof_reader, root, ticker: str, row: tuple, ranges: dict) -> None:
    artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
    require(isinstance(artifact, dict), ticker + " artifact is not an object")
    issuer = artifact.get("issuer", {})
    require(_as_cik(issuer.get("cik")) == IDENTITIES[ticker] and issuer.get("ticker") == ticker,
            ticker + " public identity changed")
    require("private_review_only" not in artifact and "source_ledger" not in artifact,
            ticker + " private payload leaked")
    require(_normalized_header(artifact.get("source_financial_statement"))
            and _source_header_matches(artifact.get("source_financial_statement"), _source_header_expected(ticker)),
            ticker + " frozen source header changed")
    require(artifact.get("valuation_date") == CUTOFF and artifact.get("assumption_date") == CUTOFF,
            ticker + " public dates changed")
    require(artifact.get("availability_type") == "conditional_estimate"
            and artifact.get("primary_valuation_method") == "residual_income",
            ticker + " public model/status changed")
    require(artifact.get("model_version") == PUBLIC_POLICY_VERSION,
            ticker + " public model profile changed")
    require(artifact.get("model_policy", {}).get("primary") == "residual_income",
            ticker + " public model policy changed")
    require(artifact.get("public_assumptions", {}).get("forecast_policy_version") == PUBLIC_POLICY_VERSION
            and artifact.get("public_assumptions", {}).get("source_policy_binding_sha256")
            == _required_anchor("source_disclosure_sha256"),
            ticker + " public policy version changed")
    require(artifact.get("reliability", {}).get("label") == "Low", ticker + " reliability is not Low")
    require(artifact.get("review", {}).get("publication_state") == "review_required",
            ticker + " review state changed")
    require(_warnings_match(artifact, ticker), ticker + " retained warning contract changed")
    for warning in artifact.get("review", {}).get("warnings", []):
        if warning == NEGATED_OWNER_WARNING:
            require(source_bound_negated_owner_warning(artifact, warning),
                    ticker + " negated owner warning is not source-bound")
    expected_ranges = _as_map(_required_anchor("frozen_ranges", "ranges"), "frozen_ranges")
    expected = expected_ranges.get(ticker)
    require(isinstance(expected, dict) and set(expected) == {"low", "base", "high"},
            ticker + " frozen range is missing")
    ranges[ticker] = {key: artifact["scenario_range"][key] for key in ("low", "base", "high")}
    require(ranges[ticker] == expected, ticker + " public range changed")
    economic_hashes = _as_map(_required_anchor("economic_hashes", "economic_recipe_hashes"), "economic_hashes")
    if ticker in economic_hashes:
        # The recipe is checked in deep mode; this marker only ensures the
        # accepted anchor is present for every public target.
        require(isinstance(economic_hashes[ticker], str) and len(economic_hashes[ticker]) == 64,
                ticker + " economic hash anchor malformed")
    _check_classification(artifact, ticker)


def _validate_null_artifact(proof_reader, root, ticker: str, row: tuple) -> None:
    artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
    issuer = artifact.get("issuer", {})
    require(_as_cik(issuer.get("cik")) == IDENTITIES[ticker] and issuer.get("ticker") == ticker,
            ticker + " null identity changed")
    require("private_review_only" not in artifact and "source_ledger" not in artifact,
            ticker + " null private payload leaked")
    require(_normalized_header(artifact.get("source_financial_statement"))
            and _source_header_matches(artifact.get("source_financial_statement"), _source_header_expected(ticker)),
            ticker + " null source header changed")
    require(artifact.get("availability_type") == "not_available", ticker + " null status changed")
    require(all(artifact.get("scenario_range", {}).get(key) is None for key in ("low", "base", "high")),
            ticker + " null range became numeric")
    require(artifact.get("review", {}).get("publication_state") == "withheld",
            ticker + " null review state changed")
    require(artifact.get("valuation_date") == CUTOFF and artifact.get("assumption_date") == CUTOFF,
            ticker + " null dates changed")
    require(_warnings_match(artifact, ticker), ticker + " null retained warning contract changed")
    if ticker in {'CBT','UTMD'}:
        require(artifact['source_financial_statement']['period_end'] == '2026-06-30'
                and any('DATED_FINANCIAL_REFERENCE_ONLY' in w and 'current post-event valuation held' in w for w in artifact['review']['warnings']),
                ticker + ' dated-only/current hold disclosure changed')


def consumer_disclosures(artifact: dict, payload: dict) -> dict:
    """Keep source/Low and public-null limits on every staged value surface."""
    ticker = artifact.get('ticker', artifact.get('issuer', {}).get('ticker'))
    if ticker not in IDENTITIES:
        return payload
    _verified_anchors()
    require(_warnings_match(artifact,ticker), ticker + ' consumer warning scope changed')
    result = deepcopy(payload)
    result['warnings'] = list(dict.fromkeys([*result.get('warnings',[]), *artifact['review']['warnings']]))
    result['staged_scope'] = {'admission':False,'activation':False,'publication':False,
        'evidence_cutoff':CUTOFF,'financial_reference_date':artifact['source_financial_statement']['period_end'],
        'reliability':artifact['reliability']['label'],'new_filing_review_required':True}
    if ticker in {'CBT','UTMD'}:
        result['staged_scope'].update(current_post_event_value_held=True,
            valuation_scope='dated_private_reference_publicly_unavailable')
    return result


def _approved_parent(manifest: dict) -> dict:
    proof = manifest.get("approved_base_inheritance")
    require(isinstance(proof, dict), "inheritance proof missing")
    expected = {
        "schema_version": SCHEMA,
        "parent_manifest_sha256": _required_anchor("base_manifest_sha256", "parent_manifest_sha256"),
        "parent_catalog_version": _required_anchor("base_catalog_version", "parent_catalog_version", "parent_version"),
        "scope_approval_sha256": _required_anchor("scope_approval_sha256", "approval_sha256"),
        "proposal_sha256": _required_anchor("proposal_sha256", "proposed_scope_sha256"),
    }
    require(proof == expected, "parent/scope/proposal pins changed")
    return proof


def validate(root, manifest, *, deep: bool = False, proof_reader=None):
    require(callable(proof_reader), "verified proof reader missing")
    _verified_anchors()
    proof = _approved_parent(manifest)
    require(manifest.get("approved_base_manifest_sha256") == proof["parent_manifest_sha256"],
            "approved base manifest pin changed")
    require(manifest.get("release_scope_approval_sha256") == proof["scope_approval_sha256"],
            "scope approval pin changed")
    version = str(manifest.get("catalog_version"))
    require(
        version.startswith("US-STAGED-EXPANSION-B11-B15-650-")
        or version.startswith("US-REFRESH-650-2026-10-08-"),
        "staged650 version namespace changed",
    )
    for manifest_key, anchor_names in (
        ("refresh_parent_catalog_version", ("refresh_parent_catalog_version",)),
        ("refresh_parent_manifest_sha256", ("refresh_parent_manifest_sha256",)),
    ):
        if manifest_key in manifest and _anchor_value(*anchor_names) is not None:
            require(manifest[manifest_key] == _anchor_value(*anchor_names),
                    manifest_key + " changed")
    if "refresh_parent" in manifest:
        expected_refresh_parent = _anchor_value("refresh_parent")
        require(isinstance(expected_refresh_parent, dict)
                and manifest["refresh_parent"] == expected_refresh_parent,
                "refresh parent lineage changed")
        require(manifest["refresh_parent"] != {
            "catalog_version": proof["parent_catalog_version"],
            "manifest_sha256": proof["parent_manifest_sha256"],
        }, "refresh parent collapsed into the admitted600 parent")
    require(manifest.get("base_catalog_version") == proof["parent_catalog_version"]
            and manifest.get("base_manifest_sha256") == proof["parent_manifest_sha256"],
            "staged650 parent changed")
    require(manifest.get("staged_release_only") is True
            and manifest.get("catalog_kind") == "unadmitted_public_contract_candidate",
            "staged650 scope changed")
    require(not manifest.get("private_integration_only") and "private_review" not in manifest,
            "private projection privilege inherited")
    require("local_admission" not in manifest and "supported_refresh_integration" not in manifest,
            "release grant inherited")
    require(all(manifest.get(key) is False for key in ("admission", "activation", "publication")),
            "release remains unauthorized")
    require(manifest.get("staged_read_only_review_ready") is True, "read-only review marker missing")

    parent = proof_reader(root, "approved-parent-manifest.json", proof["parent_manifest_sha256"])
    require(parent.get("catalog_version") == proof["parent_catalog_version"]
            and len(parent.get("entries", [])) == 600, "authentic550 parent")
    approval = proof_reader(root, "public-scope-authorization.json", proof["scope_approval_sha256"])
    require(approval.get("staged_candidate_only") is True, "approved preparation-only scope missing")
    require(set(approval.get("public_preparation_targets", [])) == set(TARGETS)
            and set(approval.get("public_unavailable_additions", [])) == set(NULLS),
            "approved29/21 scope changed")
    require(approval.get("evidence_cutoff") == CUTOFF
            and approval.get("approved_proposal_sha256") == proof["proposal_sha256"],
            "cutoff/proposal scope changed")
    for key in (
        "admission",
        "activation",
        "publication",
        "automatic_new_source_revaluation",
        "new_recovery",
        "new_source_capture",
        "next_batch",
        "valuation_recalculation",
        "live_runtime_promotion",
        "new_live_refresh_job",
        "push",
        "cloud_deployment",
    ):
        require(approval.get(key) is False, "broader authority: " + key)
    validate_source_disclosure(proof_reader, root)
    require(set(_as_map(_required_anchor("target_classification", "classifications"), "target_classification"))
            == set(TARGETS), "target classification scope changed")
    require(set(_as_map(_required_anchor("source_header_values", "source_headers"), "source_header_values"))
            == set(IDENTITIES), "source header scope changed")
    require(set(_as_map(_required_anchor("retained_warnings", "warnings"), "retained_warnings"))
            == set(IDENTITIES), "retained warning scope changed")
    require(set(_as_map(_required_anchor("private_pins", "confirmed_private650_pins"), "private_pins"))
            == set(IDENTITIES), "private650 pin scope changed")
    require(set(_as_map(_required_anchor("economic_hashes", "economic_recipe_hashes"), "economic_hashes"))
            == set(TARGETS), "economic hash scope changed")

    old, current = _rows(parent), _rows(manifest)
    parent_entries = {entry["ticker"]: entry for entry in parent["entries"]}
    current_entries = {entry["ticker"]: entry for entry in manifest["entries"]}
    require(len(current) == 650 and set(current) == set(old) | set(IDENTITIES),
            "exact600 identities")
    require(manifest.get("artifact_count") == 650
            and manifest.get("availability_counts") == EXPECTED_PUBLIC_COUNTS,
            "exact600 availability counts")
    require(all(current_entries[ticker] == parent_entries[ticker] for ticker in old),
            "old600 identity/status/artifact drift")
    for ticker, cik in IDENTITIES.items():
        expected_status = "conditional_estimate" if ticker in TARGETS else "not_available"
        require(current[ticker][:3] == (cik, BATCHES[ticker], expected_status),
                ticker + " new identity/status drift")

    index = manifest.get("private_recipe_sha256")
    require(isinstance(index, dict) and len(index) == 572
            and set(index) == set(parent["private_recipe_sha256"]) | set(TARGETS),
            "public recipe membership changed")
    require(all(index.get(ticker) == digest for ticker, digest in parent["private_recipe_sha256"].items()),
            "old600 recipe drift")
    require(not (set(index) & set(NULLS)), "public-null recipes leaked")
    policies = proof_reader(root, "refresh-policies.json", manifest["private_refresh_policy_sha256"])
    parent_policies = proof_reader(root, "approved-parent-policies.json", parent["private_refresh_policy_sha256"])
    require(set(policies) == set(parent_policies) | set(IDENTITIES)
            and all(policies[ticker] == value for ticker, value in parent_policies.items()),
            "old600 policy drift")
    for ticker in IDENTITIES:
        policy = policies[ticker]
        require(
            policy.get("schema_version") == "FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1"
            and policy.get("ticker") == ticker
            and _as_cik(policy.get("cik")) == IDENTITIES[ticker]
            and policy.get("private_only") is False
            and policy.get("staged_public_candidate_authorized") is True
            and policy.get("new_filing_hold_before_capture") is True
            and policy.get("direct_binding_rejected") is True
            and policy.get("source_epoch") == CUTOFF,
            ticker + " new-filing hold contract",
        )
        if ticker in {'CBT','UTMD'}:
            require(policy.get('dated_only') == {'financial_reference_date':'2026-06-30','current_post_event_value_held':True}, ticker + ' dated-only policy changed')
        for key in (
            "public_release_authorized",
            "auto_revaluation",
            "admission_authorized",
            "activation_authorized",
            "publication_authorized",
        ):
            require(policy.get(key) is False, ticker + " release authority")

    ranges = {}
    for ticker in IDENTITIES:
        row = current[ticker]
        if ticker in TARGETS:
            _validate_public_artifact(proof_reader, root, ticker, row, ranges)
        else:
            _validate_null_artifact(proof_reader, root, ticker, row)
    require(_canonical_sha(ranges) == _required_anchor("ranges_sha256", "frozen_ranges_sha256"),
            "accepted29 range anchor changed")

    if deep:
        require({path.name for path in Path(root).iterdir()} == ROOT_FILES | {"artifacts", "recipes"},
                "exact staged650 root allowlist")
        expected = {
            "approved-base-manifest.json": proof["parent_manifest_sha256"],
            "approved-parent-manifest.json": proof["parent_manifest_sha256"],
            "approved-parent-registry.json": _required_anchor("parent_registry_sha256", "approved_parent_registry_sha256"),
            "approved-parent-policies.json": parent["private_refresh_policy_sha256"],
            "public-scope-authorization.json": proof["scope_approval_sha256"],
            "source-disclosure-binding.json": _required_anchor("source_disclosure_sha256"),
        }
        require(manifest.get("preserved_prior_estimate_sha256") == expected,
                "exact staged650 preservation index")
        for name, digest in expected.items():
            proof_reader(root, name, digest)
        require({path.stem for path in (Path(root) / "artifacts").glob("*.json")} == set(current),
                "artifact files exact")
        require({path.stem for path in (Path(root) / "recipes").glob("*.json")} == set(index),
                "recipe files exact")
        economic_hashes = _as_map(_required_anchor("economic_hashes", "economic_recipe_hashes"), "economic_hashes")
        for ticker, row in current.items():
            artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
            if ticker in IDENTITIES:
                require(sanitize_public_artifact(artifact) == artifact,
                        ticker + " ordinary public projection/idempotence")
            if ticker in TARGETS:
                recipe = proof_reader(root, "recipes/" + ticker + ".json", index[ticker])
                require(recipe.get("ticker") == ticker and _as_cik(recipe.get("cik")) == IDENTITIES[ticker],
                        ticker + " recipe identity")
                require(recipe.get("valuation_date") == CUTOFF and recipe.get("evidence_cutoff") == CUTOFF,
                        ticker + " recipe dates")
                try:
                    from .latest_calculator import baseline_version
                except ModuleNotFoundError as exc:
                    if exc.name != __package__ + ".latest_calculator":
                        raise
                    from .calculator import baseline_version
                require(recipe.get("baseline_version") == baseline_version(artifact),
                        ticker + " recipe baseline")
                require(evaluate_recipe(recipe)["range"] == ranges[ticker],
                        ticker + " public recipe replay")
                economic = {key: recipe[key] for key in ("scenarios", "warnings", "editable")}
                require(_canonical_sha(economic) == economic_hashes[ticker],
                        ticker + " accepted economic recipe/warning anchor")
            elif ticker in NULLS:
                require(not (Path(root) / "recipes" / (ticker + ".json")).exists(),
                        ticker + " null recipe leaked")
    return old


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader=None):
    """Recheck frozen authority and this record, not all fifty records per leaf.

    Full deep validation still runs at native review selection and strict-store
    admission to the inactive store. Every leaf rereads the pinned source and
    parent proofs and verifies its own current bytes against the frozen scope.
    """
    require(callable(proof_reader), "verified proof reader missing")
    _verified_anchors()
    proof = _approved_parent(manifest)
    require(manifest.get("staged_release_only") is True
            and manifest.get("catalog_kind") == "unadmitted_public_contract_candidate"
            and manifest.get("staged_read_only_review_ready") is True,
            "leaf must remain a staged read-only candidate")
    require(all(manifest.get(key) is False for key in ("admission","activation","publication"))
            and "local_admission" not in manifest and "private_review" not in manifest
            and "supported_refresh_integration" not in manifest,
            "leaf acquired release/private privilege")
    require(manifest.get("base_catalog_version") == proof["parent_catalog_version"]
            and manifest.get("base_manifest_sha256") == proof["parent_manifest_sha256"]
            and manifest.get("approved_base_manifest_sha256") == proof["parent_manifest_sha256"]
            and manifest.get("release_scope_approval_sha256") == proof["scope_approval_sha256"],
            "leaf parent/scope changed")
    parent = proof_reader(root,"approved-parent-manifest.json",proof["parent_manifest_sha256"])
    proof_reader(root,"public-scope-authorization.json",proof["scope_approval_sha256"])
    validate_source_disclosure(proof_reader,root)
    old = {entry["ticker"]:entry for entry in parent["entries"]}
    current = {entry["ticker"]:entry for entry in manifest["entries"]}
    require(len(parent["entries"]) == 600 and len(manifest["entries"]) == len(current) == manifest.get("artifact_count") == 650
            and set(current) == set(old) | set(IDENTITIES)
            and manifest.get("availability_counts") == EXPECTED_PUBLIC_COUNTS,
            "leaf exact600 membership/counts changed")
    require(all(current[t] == entry for t,entry in old.items()),"leaf inherited row changed")
    require(all((current[t]["cik"],current[t]["batch"],current[t]["availability_type"])
                == (IDENTITIES[t],BATCHES[t],"conditional_estimate" if t in TARGETS else "not_available")
                for t in IDENTITIES),"leaf new issuer/batch/status changed")
    index = manifest.get("private_recipe_sha256",{})
    require(len(index) == 572 and set(index) == set(parent["private_recipe_sha256"]) | set(TARGETS)
            and all(index[t] == digest for t,digest in parent["private_recipe_sha256"].items()),
            "leaf recipe membership or parent changed")
    require(hashlib.sha256(raw).hexdigest() == current[ticker]["artifact_sha256"],
            "leaf current artifact bytes changed")
    if ticker in old:
        require(manifest["private_recipe_sha256"].get(ticker)
                == parent["private_recipe_sha256"].get(ticker),"leaf inherited recipe changed")
        return True
    row = _rows(manifest)[ticker]
    if ticker in TARGETS:
        ranges = {}
        _validate_public_artifact(proof_reader,root,ticker,row,ranges)
    else:
        _validate_null_artifact(proof_reader,root,ticker,row)
    return False


def validate_registry(root, manifest, registry, *, proof_reader=None):
    require(callable(proof_reader), "verified proof reader missing")
    parent = proof_reader(
        root,
        "approved-parent-registry.json",
        _required_anchor("parent_registry_sha256", "approved_parent_registry_sha256"),
    )
    require(isinstance(parent, dict) and len(parent.get("entries", [])) == 600,
            "registry550 parent")
    rows = registry.get("entries") if isinstance(registry, dict) else None
    require(registry.get("schema_version") == parent.get("schema_version")
            and isinstance(rows, list) and len(rows) == 650,
            "registry600 schema")
    require(all(row in rows for row in parent["entries"]), "old600 registry records changed")
    actual = {
        (_as_cik(entry["cik"]), entry["ticker"], entry["batch"], entry["availability_type"])
        for entry in rows
    }
    wanted = {
        (_as_cik(entry["cik"]), entry["ticker"], entry["batch"], entry["availability_type"])
        for entry in manifest["entries"]
    }
    require(len(actual) == 650 and actual == wanted, "registry identities/statuses")
    current = {r['ticker']:r for r in manifest['entries']}
    for record in rows:
        ticker = record['ticker']
        if ticker in IDENTITIES:
            require(record.get('baseline_sha256') == current[ticker]['artifact_sha256']
                    and record.get('controlling_filing') == _source_header_expected(ticker),
                    ticker + ' registry source/artifact binding changed')
    return registry
