"""Authenticated exact-16 Quality04 staged candidate guards.

This module is deliberately a validator, not release authority.  It binds one
immutable 650-row candidate to the direct-user preparation receipt, the frozen
private confirmation, and the unbound eligibility handoff.  Admission,
activation, publication and source refresh are rejected by construction.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import hashlib
import json

SCHEMA = "US-QUALITY04-STAGED-INHERITANCE-1"
REVIEW_SCHEMA = "US-QUALITY04-STAGED-READ-ONLY-1"
MODEL_VERSION = "US-QUALITY04-PUBLIC-DATED-LOW-1"
PUBLIC_OVERRIDE_PINS_SHA = "64d781dbec17622cbaeb2359d5a509f547b49382fb42bdab41e52fe742056b60"
PUBLIC_OVERRIDE_MANIFEST_SHA = "a6cd3031ef40fe5534b8d108b670ff16960ab69d5aac7c1fa2fb4f331063b7fe"
PUBLIC_OVERRIDE_CATALOG_VERSION = "US-STAGED-QUALITY04-650-1ef618bfdd7c0b4457c00ea8"
# Deliberately replaced only after the parent assembles and communicates the
# exact compiled-anchor bytes.  A missing/replaced anchor must fail closed.
ANCHOR_SHA = "a1bc7d7caf3726a3e548fd20685f4afc5100418b04031a8f000d23f34bcf7029"
TARGETS = frozenset("AEP AJG AMAT AMD AVGO AXP CFG COST DUK GS IBM INTU NI NVDA PFG PLTR".split())
RI_TARGETS = frozenset("AEP AJG AXP CFG DUK GS IBM NI PFG".split())
CASH_TARGETS = frozenset("AMD AMAT AVGO COST INTU NVDA PLTR".split())
HELD = frozenset("AAPL ABT AMZN CAT CME CRM CVS GOOGL HD ITW JNJ JPM KLAC LOW MCD MDLZ MRK MSFT NUE PFE PNC QCOM SBUX SRE TECH TGT TSLA".split())
PRIVATE_ONLY = frozenset({"AFL"})
CONTROLS = frozenset("DOV HRL PEP PG ROL RSG".split())
CARRY_FORWARD = frozenset(HELD | PRIVATE_ONLY | CONTROLS)
AUTHORITY_FIELDS = frozenset({"schema_version", "read_only", "manifest_sha256", "catalog_version", "registry_sha256", "admission", "activation", "publication", "save", "automatic_new_source_revaluation"})
ROOT_FILES = frozenset({"manifest.json", "artifacts", "recipes", "refresh-policies.json", "prior-catalog", "approved-parent-manifest.json", "approved-parent-registry.json", "approved-parent-policies.json", "quality-scope-authorization.json", "quality-source-binding.json", "quality-private-confirmation.json", "quality-eligibility-proposal.json", "quality-eligibility-verification.json"})
DENIED = ("admission", "activation", "publication", "policy_economics_change", "new_SEC_capture_or_job", "existing_runtime_service_operation", "Docker_operation", "data_deletion", "cloud_deployment", "second_recovery_pass", "next_batch")
APPROVAL_FIELDS = frozenset(set(DENIED) | {"schema_version", "source", "user_request", "recorded_at_UTC", "issuer_specific_frozen_cutoffs_retained", "targets", "public_preparation_scope_approved", "staged_candidate_only", "proposal_sha256", "eligibility_verification_sha256", "private_confirmation_sha256", "confirmed_private_values_and_Low_warnings_preserved", "carry_forward_prior_active_artifact_and_recipe", "private_only_diagnostic_tickers", "private_held_update_tickers", "unchanged_control_tickers", "revision_specific_new_filing_holds_required", "existing_refresh_support_and_hold_epochs_preserved"})
RAW_FORBIDDEN_KEYS = frozenset({"source_ledger", "source_ledgers", "source_packet", "source_receipt", "companyfacts", "recipe", "raw_value", "raw_range", "raw_financials", "eod_price", "market_price", "forecast_assumptions", "private_quality_review", "private_review_only"})


def require(value, reason):
    if not value:
        raise ValueError("Quality04 stage rejected: " + reason)


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def _assert_raw_free(value):
    if isinstance(value, dict):
        require(not RAW_FORBIDDEN_KEYS.intersection(value), "raw/private field in public artifact")
        for item in value.values():
            _assert_raw_free(item)
    elif isinstance(value, list):
        for item in value:
            _assert_raw_free(item)


def is_exact_public_override(artifact):
    """Return true only for the pinned, raw-free Q04 public leaf.

    This narrow predicate is used by the legacy ROOT sanitizer's issuer-route
    compatibility shim.  It does not call sanitization or model calculation,
    and it never authorizes a catalog, source refresh, admission, or release.
    """
    try:
        path = Path(__file__).with_name("config") / "quality04_public_artifact_override_pins_v1.json"
        if path.is_symlink() or not path.is_file():
            return False
        raw = path.read_bytes()
        if sha(raw) != PUBLIC_OVERRIDE_PINS_SHA:
            return False
        pins = json.loads(raw)
        if pins.get("schema_version") != "US-QUALITY04-PUBLIC-ARTIFACT-OVERRIDE-PINS-1":
            return False
        if pins.get("manifest_sha256") != PUBLIC_OVERRIDE_MANIFEST_SHA or pins.get("catalog_version") != PUBLIC_OVERRIDE_CATALOG_VERSION:
            return False
        if set(pins.get("artifacts", {})) != TARGETS:
            return False
        if not isinstance(artifact, dict):
            return False
        ticker = artifact.get("ticker") or artifact.get("issuer", {}).get("ticker")
        if ticker not in TARGETS or artifact.get("issuer", {}).get("ticker") != ticker:
            return False
        if sha(canonical(artifact)) != pins["artifacts"].get(ticker):
            return False
        if artifact.get("model_version") != MODEL_VERSION or artifact.get("availability_type") != "conditional_estimate":
            return False
        if artifact.get("review", {}).get("publication_state") != "review_required" or artifact.get("review", {}).get("errors"):
            return False
        _assert_raw_free(artifact)
        return True
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
        return False
def anchors():
    path = Path(__file__).with_name("config") / "quality04_staged_anchors_v1.json"
    require(path.is_file() and not path.is_symlink(), "compiled anchor file")
    raw = path.read_bytes()
    require(sha(raw) == ANCHOR_SHA, "compiled anchor bytes")
    value = json.loads(raw)
    require(value.get("schema_version") == SCHEMA and set(value.get("targets", ())) == TARGETS, "compiled target scope")
    require(set(value.get("carry_forward", ())) == CARRY_FORWARD and set(value.get("held_updates", ())) == HELD, "compiled carry/held scope")
    require(set(value.get("private_only_diagnostics", ())) == PRIVATE_ONLY and set(value.get("unchanged_controls", ())) == CONTROLS, "compiled diagnostic/control scope")
    require(set(value.get("expected_issuer_mapping", ())) == TARGETS and set(value.get("root_files", ())) == ROOT_FILES, "compiled mapping/root contract")
    return deepcopy(value)


def proof(root, name, expected, proof_reader):
    require(callable(proof_reader), "authenticated proof reader")
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader(root, name, expected)
    value = proof_reader(root, name, expected)
    value = deepcopy(value)
    require(digest(value) == expected, "parsed proof changed: " + name)
    return value


def _context_uncached(root, manifest, proof_reader):
    a = anchors()
    bound = proof(root, "manifest.json", a["manifest_sha256"], proof_reader)
    require(manifest == bound, "compiled manifest")
    require(manifest.get("staged_release_only") is True and manifest.get("staged_read_only_review_ready") is True, "read-only stage")
    require(all(manifest.get(k) is False for k in ("admission", "activation", "publication")), "no release")
    require("local_admission" not in manifest and "private_review" not in manifest and not manifest.get("private_integration_only"), "foreign permission lineage")
    require(manifest.get("catalog_kind") == "unadmitted_quality04_public_candidate" and str(manifest.get("catalog_version", "")).startswith("US-STAGED-QUALITY04-650-"), "namespace")
    parent = proof(root, "approved-parent-manifest.json", a["parent_manifest_sha256"], proof_reader)
    grant = proof(root, "quality-scope-authorization.json", a["approval_sha256"], proof_reader)
    binding = proof(root, "quality-source-binding.json", a["binding_sha256"], proof_reader)
    confirmation = proof(root, "quality-private-confirmation.json", a["confirmation_sha256"], proof_reader)
    proposal = proof(root, "quality-eligibility-proposal.json", a["proposal_sha256"], proof_reader)
    eligibility = proof(root, "quality-eligibility-verification.json", a["eligibility_sha256"], proof_reader)
    require(set(grant) == APPROVAL_FIELDS and grant.get("schema_version") == "US-QUALITY04-PUBLIC-PREPARATION-AUTHORIZATION-1", "exact approval fields")
    require(grant.get("source") == "direct_human_user" and isinstance(grant.get("user_request"), str) and grant["user_request"].strip(), "direct human scope")
    require(grant.get("issuer_specific_frozen_cutoffs_retained") is True and grant.get("public_preparation_scope_approved") is True and grant.get("staged_candidate_only") is True, "approved preparation")
    require(all(grant.get(k) is False for k in DENIED), "prep only")
    require(set(grant.get("targets", ())) == TARGETS and set(grant.get("carry_forward_prior_active_artifact_and_recipe", ())) == CARRY_FORWARD, "exact16/34")
    require(set(grant.get("private_only_diagnostic_tickers", ())) == PRIVATE_ONLY and set(grant.get("private_held_update_tickers", ())) == HELD and set(grant.get("unchanged_control_tickers", ())) == CONTROLS, "AFL/held/control scope")
    require(grant.get("revision_specific_new_filing_holds_required") is True and grant.get("existing_refresh_support_and_hold_epochs_preserved") is True, "filing/support guard")
    require(grant.get("proposal_sha256") == a["proposal_sha256"] and grant.get("eligibility_verification_sha256") == a["eligibility_sha256"] and grant.get("private_confirmation_sha256") == a["confirmation_sha256"], "approval ancestry")
    require(proposal.get("schema_version") == "US-QUALITY04-UNBOUND-PUBLIC-POLICY-PROPOSAL-1" and set(proposal.get("proposed_preparation_tickers", ())) == TARGETS and proposal.get("public_preparation_permission_issued") is False, "unbound proposal")
    require(eligibility.get("schema_version") == "US-QUALITY04-UNBOUND-PUBLIC-ELIGIBILITY-HANDOFF-1" and eligibility.get("status") == "unbound16_proposal_verified_awaiting_user_scope_confirmation", "unbound eligibility handoff")
    require(set(eligibility.get("proposed_preparation_tickers", ())) == TARGETS and eligibility.get("binding_candidate_admission_activation_publication") is False, "unbound eligibility scope")
    require(confirmation.get("schema_version") == "US-QUALITY04-PRIVATE-RECOVERY-CONFIRMATION-1" and confirmation.get("status") == "private_recovery_results_user_confirmed", "confirmed private scope")
    require(confirmation.get("confirmed_private_Low_count") == 17 and set(confirmation.get("confirmed_private_Low_ranges", ())) == TARGETS | PRIVATE_ONLY and confirmation.get("unchanged_count") == 6 and set(confirmation.get("preserved_unchanged_ranges", ())) == CONTROLS and confirmation.get("held_count") == 27 and set(confirmation.get("preserved_held_updates", ())) == HELD, "confirmed private17/controls6/held27")
    require(binding.get("schema_version") == "US-QUALITY04-PUBLIC-SOURCE-POLICY-BINDING-1" and binding.get("model_policy_version") == MODEL_VERSION and binding.get("issuer_specific_frozen_cutoffs_retained") is True, "source/model binding")
    for field, key in (("approval_sha256", "approval_sha256"), ("private_confirmation_sha256", "confirmation_sha256"), ("proposal_sha256", "proposal_sha256"), ("eligibility_sha256", "eligibility_sha256")):
        require(binding.get(field) == a[key], "binding ancestry " + field)
    require(set(binding.get("targets", ())) == TARGETS and set(binding.get("carry_forward", ())) == CARRY_FORWARD and set(binding.get("private_only_diagnostics", ())) == PRIVATE_ONLY and set(binding.get("private_held_updates", ())) == HELD and set(binding.get("unchanged_controls", ())) == CONTROLS, "binding scope")
    require(binding.get("all16_revision_specific_new_filing_holds") is True and all(binding.get(k) is False for k in ("admission", "activation", "publication", "new_capture_or_refresh", "economic_values_changed")), "binding permission")
    current = {e["ticker"]: e for e in manifest["entries"]}; old = {e["ticker"]: e for e in parent["entries"]}
    require(len(current) == len(manifest["entries"]) == len(parent["entries"]) == len(old) == 650 and set(current) == set(old), "650 identity membership")
    require(set(manifest.get("private_recipe_sha256", {})) == set(parent.get("private_recipe_sha256", {})), "recipe membership")
    require(manifest.get("base_manifest_sha256") == manifest.get("approved_base_manifest_sha256") == a["parent_manifest_sha256"] and manifest.get("base_catalog_version") == parent.get("catalog_version"), "parent identity")
    records = binding.get("records", {}); originals = {r["ticker"]: r for r in proposal.get("rows", [])}
    require(set(records) == TARGETS | CARRY_FORWARD and len(records) == 50 and {t for t, r in records.items() if r.get("updated_value_prepared")} == TARGETS, "50 reviewed records")
    for t in set(old) - TARGETS:
        require(current[t] == old[t] and manifest["private_recipe_sha256"].get(t) == parent["private_recipe_sha256"].get(t), t + " unchanged634 artifact/recipe")
    for t in TARGETS:
        require((current[t]["cik"], current[t]["batch"], current[t]["availability_type"]) == (old[t]["cik"], old[t]["batch"], "conditional_estimate"), t + " target identity/status")
        require(records[t]["confirmed_private_range"] == confirmation["confirmed_private_Low_ranges"][t] == originals[t]["confirmed_private_range"], t + " exact confirmed values")
        require(records[t]["source_to_recipe_review"] == originals[t]["source_to_recipe_review"], t + " unchanged source proof")
        require(records[t]["proposed_public_valuation_date"] == originals[t]["proposed_public_valuation_date"], t + " issuer cutoff")
    for t in CARRY_FORWARD:
        require(records[t]["current_public_value_carry_forward"] == originals[t]["prior_active_range_retained"] and all(records[t]["current_public_value_carry_forward"].get(k) is not None for k in ("low", "base", "high")), t + " prior numeric carry")
        if t in HELD:
            require(records[t].get("private_held_update") is True and records[t].get("reason") == confirmation["preserved_held_updates"][t], t + " held update")
        if t in PRIVATE_ONLY:
            require(records[t].get("private_only_diagnostic_retained") is True and records[t]["confirmed_private_range"] == confirmation["confirmed_private_Low_ranges"][t], t + " private diagnostic")
        if t in CONTROLS:
            require(records[t].get("unchanged_control") is True and records[t]["confirmed_private_range"] == confirmation["preserved_unchanged_ranges"][t], t + " unchanged control")
    return a, parent, binding, current


@lru_cache(maxsize=4)
def _context_bytes(files):
    records = {name: (pin, raw) for name, pin, raw in files}
    def verified_memory(root, name, pin):
        wanted, raw = records[name]
        require(wanted == pin, "immutable context proof pin")
        return json.loads(raw)
    result = _context_uncached(Path("."), json.loads(records["manifest.json"][1]), verified_memory)
    return canonical(result)


@lru_cache(maxsize=4)
def _native_context_files(root_name, pins):
    from .approved_inheritance import _file
    root = Path(root_name)
    files = []
    for name, pin in pins:
        raw = _file(root, name)
        require(sha(raw) == pin, "current context proof bytes: " + name)
        files.append((name, pin, raw))
    return tuple(files)


def context(root, manifest, proof_reader):
    from .approved_inheritance import _proof as native_reader, _file
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader.context_for(root, manifest, lambda: _context_uncached(root, manifest, proof_reader))
    if proof_reader is not native_reader:
        return _context_uncached(root, manifest, proof_reader)
    a = anchors()
    pins = {"manifest.json": a["manifest_sha256"], "approved-parent-manifest.json": a["parent_manifest_sha256"], "quality-scope-authorization.json": a["approval_sha256"], "quality-source-binding.json": a["binding_sha256"], "quality-private-confirmation.json": a["confirmation_sha256"], "quality-eligibility-proposal.json": a["proposal_sha256"], "quality-eligibility-verification.json": a["eligibility_sha256"]}
    files = _native_context_files(str(Path(root)), tuple(sorted(pins.items())))
    result = json.loads(_context_bytes(tuple(files)))
    raw_manifest = next(raw for name, pin, raw in files if name == "manifest.json")
    require(manifest == json.loads(raw_manifest), "current manifest object changed")
    return tuple(result)


def target(root, manifest, ticker, record, entry, proof_reader):
    from .artifacts import sanitize_public_artifact
    from .automated_review import assess_artifact
    from .calculation_recipe import evaluate_recipe
    try:
        from .latest_calculator import baseline_version
    except ImportError:
        from .calculator import baseline_version
    a = anchors(); artifact = proof(root, "artifacts/" + ticker + ".json", entry["artifact_sha256"], proof_reader); recipe = proof(root, "recipes/" + ticker + ".json", manifest["private_recipe_sha256"][ticker], proof_reader)
    _assert_raw_free(artifact)
    require(artifact.get("issuer") == a["expected_issuer_mapping"][ticker] and artifact["issuer"].get("ticker") == ticker and artifact["issuer"].get("cik") == record["cik"], ticker + " mapping")
    require(artifact.get("source_financial_statement") == record["exact_source_header"] == record["source_to_recipe_review"]["canonical_source_header"], ticker + " canonical source header")
    cutoff = record["proposed_evidence_cutoff"]
    require(artifact.get("valuation_date") == recipe.get("valuation_date") == recipe.get("evidence_cutoff") == cutoff, ticker + " preserved issuer date")
    require(all(artifact["source_financial_statement"][k] <= cutoff for k in ("filed_date", "period_end")), ticker + " financial cutoff")
    require(artifact.get("model_version") == MODEL_VERSION and artifact.get("model_policy", {}).get("primary") == record["expected_model"] == ("residual_income" if ticker in RI_TARGETS else "fcff_dcf"), ticker + " exact model")
    require(artifact.get("public_assumptions", {}).get("source_policy_binding_sha256") == manifest.get("quality_source_binding_sha256") == a["binding_sha256"], ticker + " public binding")
    require(artifact["issuer"].get("classification_confidence") == 0.0 and "Unrated" in artifact["issuer"].get("classification_reason", ""), ticker + " unrated guard")
    require(artifact.get("reliability", {}).get("label") == "Low" and artifact.get("availability_type") == "conditional_estimate" and artifact.get("review", {}).get("publication_state") == "review_required" and not artifact.get("review", {}).get("errors"), ticker + " Conditional/Low")
    require(not assess_artifact(artifact).get("blocking_reasons") and sanitize_public_artifact(artifact) == artifact, ticker + " ordinary public gate")
    expected = record["confirmed_private_range"]; model = record["expected_model"]
    dto = record.get("forecast_assumptions")
    require(dto is not None, ticker + " reviewed forecast DTO")
    require(dto.get("forecast_mode") == recipe.get("scenarios", {}).get("base", {}).get("engine", "") + "_exact", ticker + " reviewed engine mode")
    recipe_inputs = recipe.get("scenarios", {}).get("base", {}).get("inputs", {})
    recipe_horizon = recipe_inputs.get("forecast_years", recipe_inputs.get("years"))
    expected_horizon = 5 if recipe.get("scenarios", {}).get("base", {}).get("engine") == "constant_growth_fcff" else recipe_horizon
    require(dto.get("forecast_years") == expected_horizon, ticker + " reviewed horizon")
    require({k: artifact["scenario_range"][k] for k in ("low", "base", "high")} == expected, ticker + " values")
    require(set(artifact.get("models", {})) == {model} and artifact["models"][model]["intrinsic_value_per_share"] == expected["base"], ticker + " base model")
    require(set(artifact.get("scenarios", {})) == {"bear", "base", "bull"}, ticker + " scenarios")
    for name, key in (("bear", "low"), ("base", "base"), ("bull", "high")):
        require(set(artifact["scenarios"][name]) == {model} and artifact["scenarios"][name][model]["intrinsic_value_per_share"] == expected[key], ticker + " scenario value")
    require(recipe.get("ticker") == ticker and recipe.get("cik") == record["cik"] and recipe.get("private_only") is True and recipe.get("baseline_version") == baseline_version(artifact), ticker + " recipe identity")
    require(digest({k: recipe[k] for k in ("scenarios", "editable", "warnings")}) == record["bound_recipe_economic_sha256"], ticker + " economics")
    require(evaluate_recipe(recipe)["range"] == expected, ticker + " exact replay")
    require(set(record.get("required_public_disclosures", ())) <= set(artifact.get("review", {}).get("warnings", ())) and set(recipe.get("warnings", ())) <= set(artifact.get("review", {}).get("warnings", ())), ticker + " warnings")
    if ticker == "AJG":
        require(record.get("required_exact_claim_allowance_by_case") == {"bear": 711510000.0, "base": 237170000.0, "bull": 0.0}, "AJG exact claim allowances")
        require(all(str(v) in " ".join(artifact["review"]["warnings"]) for v in (711510000, 237170000, 0)), "AJG claim disclosure")
    if ticker == "NVDA":
        require(record.get("public_preferred_stock_fact_from_legacy_field_forbidden") is True, "NVDA reserve semantics")
        require(record.get("required_exact_legacy_other_claim_aggregate_by_case") == {n: recipe["scenarios"][n]["inputs"]["preferred_equity"] for n in recipe["scenarios"]}, "NVDA exact claim reserve")
    return artifact


def expected_policy(t, record, artifact_sha, old, approval_sha, binding_sha):
    old = old or {}
    require(old.get("source_epoch") is None or old.get("source_epoch") == record.get("proposed_review_hold_epoch"), t + " old epoch")
    return {"schema_version": "FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1", "version": "US-QUALITY04-REVISION-FILING-HOLD-1", "ticker": t, "cik": record["cik"], "private_only": False, "public_release_authorized": False, "staged_public_candidate_authorized": True, "admission_authorized": False, "activation_authorized": False, "publication_authorized": False, "new_filing_hold_before_capture": True, "direct_binding_rejected": True, "auto_revaluation": False, "source_epoch": record.get("proposed_review_hold_epoch"), "reasons": ["Revised Quality04 dated baseline requires new source/model/assumption review before any new financial filing or amendment can be recalculated."], "pins": {"public_baseline": artifact_sha, "private_economic_payload": record["bound_recipe_economic_sha256"], "quality_source_policy_binding": binding_sha, "release_scope_approval": approval_sha, "predecessor_policy": digest(old)}, "predecessor_policy_retained_for_existing_active_baseline": True, "revised_baseline_adapter_readiness_not_inherited": True}


def validate(root, manifest, *, deep=False, proof_reader=None):
    a, parent, binding, current = context(root, manifest, proof_reader)
    policies = proof(root, "refresh-policies.json", a["policies_sha256"], proof_reader); oldpolicies = proof(root, "approved-parent-policies.json", a["parent_policies_sha256"], proof_reader)
    require(set(policies) == set(oldpolicies), "policy membership")
    for t in policies:
        old = oldpolicies.get(t, {})
        expected = expected_policy(t, binding["records"][t], current[t]["artifact_sha256"], old, a["approval_sha256"], a["binding_sha256"]) if t in TARGETS else old
        require(policies[t] == expected, t + " exact policy/support guard")
    if deep:
        require({p.name for p in Path(root).iterdir()} == ROOT_FILES, "root filenames")
        require({p.name for p in (Path(root) / "artifacts").iterdir()} == {t + ".json" for t in current}, "artifact files")
        require({p.name for p in (Path(root) / "recipes").iterdir()} == {t + ".json" for t in manifest["private_recipe_sha256"]}, "recipe files")
        from .approved_inheritance import validate_inheritance
        validate_inheritance(Path(root) / "prior-catalog", parent, deep=True)
        for t, e in current.items(): proof(root, "artifacts/" + t + ".json", e["artifact_sha256"], proof_reader)
        for t, pin in manifest["private_recipe_sha256"].items(): proof(root, "recipes/" + t + ".json", pin, proof_reader)
        for t in TARGETS: target(root, manifest, t, binding["records"][t], current[t], proof_reader)
    return {t: (e["cik"], e["batch"], e["availability_type"], e["artifact_sha256"]) for t, e in current.items() if t not in TARGETS}


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader):
    _, _, binding, current = context(root, manifest, proof_reader)
    require(ticker in current and sha(raw) == current[ticker]["artifact_sha256"], "leaf bytes")
    if ticker in TARGETS:
        target(root, manifest, ticker, binding["records"][ticker], current[ticker], proof_reader)
        return False
    return True


def validate_registry(root, manifest, registry, *, proof_reader):
    a, _, binding, current = context(root, manifest, proof_reader); old = proof(root, "approved-parent-registry.json", a["parent_registry_sha256"], proof_reader)
    require(digest(registry) == a["registry_sha256"], "registry anchor")
    rows = {r["ticker"]: r for r in registry["entries"]}; oldrows = {r["ticker"]: r for r in old["entries"]}
    require(len(rows) == len(registry["entries"]) == 650 and set(rows) == set(current), "registry650")
    require(registry.get("baseline_manifest_sha256") == a["manifest_sha256"] and registry.get("baseline_catalog_version") == manifest.get("catalog_version"), "registry lineage")
    for t in rows:
        expected = deepcopy(oldrows[t])
        if t in TARGETS:
            expected.update(baseline_sha256=current[t]["artifact_sha256"], availability_type="conditional_estimate", primary_model=binding["records"][t]["expected_model"], forecast_mode=binding["records"][t]["forecast_assumptions"]["forecast_mode"], controlling_filing=binding["records"][t]["exact_source_header"], source_audit="docs/audit/us-quality04-public-staged.md", recipe_status="quality04_recipe_revision_new_filing_held")
        require(rows[t] == expected, t + " exact registry row")
    return registry


def review_selection(root, authority_file, authority, manifest, manifest_sha, *, proof_reader):
    a = anchors()
    require(set(authority) == AUTHORITY_FIELDS and authority.get("schema_version") == REVIEW_SCHEMA and authority.get("read_only") is True, "review fields")
    require(all(authority.get(k) is False for k in ("admission", "activation", "publication", "save", "automatic_new_source_revaluation")), "review permission")
    require(authority.get("manifest_sha256") == manifest_sha == a["manifest_sha256"] and authority.get("catalog_version") == manifest.get("catalog_version") and authority.get("registry_sha256") == a["registry_sha256"], "review ancestry")
    validate(root, manifest, deep=True, proof_reader=proof_reader)
    validate_registry(root, manifest, proof(authority_file.parent, "runtime/registry.json", a["registry_sha256"], proof_reader), proof_reader=proof_reader)
    proof(authority_file.parent, "runtime/refresh-policies.json", a["policies_sha256"], proof_reader)
    return root, manifest_sha
