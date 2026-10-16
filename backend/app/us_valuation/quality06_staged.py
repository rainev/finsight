"""Fail-closed native guards for the Quality06 staged public candidate.

Quality06 is an unbound, read-only preparation scope.  This module deliberately
keeps the Q05 admission/activation chain intact while authenticating the Q06
25-target overlay and its 25 carried rows.  The compiled anchor and artifact
pin values are placeholders until the root builder supplies the exact bytes;
selection therefore fails closed in this copy.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import hashlib
import json

SCHEMA = "US-QUALITY06-STAGED-INHERITANCE-1"
REVIEW_SCHEMA = "US-QUALITY06-STAGED-READ-ONLY-1"
MODEL_VERSION = "US-QUALITY06-PUBLIC-DATED-LOW-1"
OFFLINE_RETENTION_SCHEMA = "US-QUALITY06-OFFLINE-RETENTION-CHILD-1"

# Root replaces these only after compiling and hashing the exact prepared
# catalog.  Empty values are intentional fail-closed sentinels.
ANCHOR_SHA = "219e37acfebbf6f11a4499adae53d978de684a099f1cb3a8a0a82bd321e84db8"
PUBLIC_OVERRIDE_PINS_SHA = "ddd44338d4b6ae5e047427c845bf09fb4aa3c5e6f64ba861a41ab8196a0e81a7"
PUBLIC_OVERRIDE_MANIFEST_SHA = "c044cf6139adffc28712b6ad0e6e56f38b46750f16f9d6027ca8692e0fe78f82"
PUBLIC_OVERRIDE_CATALOG_VERSION = "US-STAGED-QUALITY06-650-b2477566e1082578658ba281"

RI_TARGETS = frozenset("AEE AWK CMS CNP DTE EVRG GL WRB".split())
CASH_TARGETS = frozenset("EQT FDS FICO FIX HWM MSI MTD MU STX SYK VMC XYL".split())
REIT_TARGETS = frozenset("ARE DLR EQIX PLD WELL".split())
TARGETS = RI_TARGETS | CASH_TARGETS | REIT_TARGETS
HELD = frozenset("APD AVY BSX CNC DE ELV ETR EXPE GE GWW HUM JBL KKR LII LNT ODFL PH PNW PSX SPGI SWK UBER XYZ".split())
PRIVATE_ONLY = frozenset({"APO"})
CONTROLS = frozenset({"BEN"})
CARRY_FORWARD = HELD | PRIVATE_ONLY | CONTROLS

PREPARATION_AUTHORITY_FIELDS = frozenset({
    "Docker_operation", "HWM_source_role_unit_and_unchanged_value_gate_approved",
    "activation", "admission", "carry_forward_prior_active_artifact_and_recipe",
    "cloud_deployment", "confirmed_private_values_and_Low_warnings_preserved",
    "data_deletion", "eligibility_verification_sha256",
    "existing_refresh_support_and_hold_epochs_preserved", "existing_runtime_service_operation",
    "issuer_specific_frozen_cutoffs_retained", "new_SEC_capture_or_job", "next_batch",
    "policy_economics_change", "private_confirmation_sha256", "private_held_update_tickers",
    "private_only_diagnostic_tickers", "proposal_sha256", "public_preparation_scope_approved",
    "publication", "recorded_at_UTC", "revision_specific_new_filing_holds_required",
    "schema_version", "second_recovery_pass", "source", "staged_candidate_only", "targets",
    "unchanged_control_tickers", "user_request",
})
# The native read-only review authority is intentionally smaller than the
# direct preparation grant.  Keeping the two schemas separate prevents a
# preparation receipt from becoming release authority by field reuse.
AUTHORITY_FIELDS = frozenset({
    "schema_version", "read_only", "manifest_sha256", "catalog_version", "registry_sha256",
    "admission", "activation", "publication", "save", "automatic_new_source_revaluation",
})
DENIED = (
    "admission", "activation", "publication", "policy_economics_change",
    "new_SEC_capture_or_job", "existing_runtime_service_operation", "Docker_operation",
    "data_deletion", "cloud_deployment", "second_recovery_pass", "next_batch",
)
APPROVAL_SCHEMA = "US-QUALITY06-PUBLIC-PREPARATION-AUTHORIZATION-1"
PROPOSAL_SCHEMA = "US-QUALITY06-UNBOUND-PUBLIC-POLICY-PROPOSAL-1"
ELIGIBILITY_SCHEMA = "US-QUALITY06-UNBOUND-PUBLIC-ELIGIBILITY-HANDOFF-1"
CONFIRMATION_SCHEMA = "US-QUALITY06-PRIVATE-RECOVERY-CONFIRMATION-1"
BINDING_SCHEMA = "US-QUALITY06-PUBLIC-SOURCE-POLICY-BINDING-1"
ROOT_FILES = frozenset({
    "manifest.json", "artifacts", "recipes", "refresh-policies.json", "prior-catalog",
    "approved-parent-manifest.json", "approved-parent-registry.json", "approved-parent-policies.json",
    "quality-scope-authorization.json", "quality-source-binding.json", "quality-private-confirmation.json",
    "quality-eligibility-proposal.json", "quality-eligibility-verification.json",
})
RAW_FORBIDDEN_KEYS = frozenset({
    "source_ledger", "source_ledgers", "source_packet", "source_receipt", "companyfacts", "recipe",
    "raw_value", "raw_range", "raw_financials", "eod_price", "market_price", "forecast_assumptions",
    "private_quality_review", "private_review_only",
})


def require(value, reason):
    if not value:
        raise ValueError("Quality06 stage rejected: " + reason)


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def replay_matches(actual, expected):
    # Reuse the reviewed four-ULP cross-runtime arithmetic check. Exact
    # source/recipe/artifact/value pins above remain mandatory and unchanged.
    from .quality_batches1115_staged import replay_matches as bounded_replay
    return bounded_replay(actual, expected)


def is_exact_calculator_baseline(artifact):
    # The native router adds only catalog context/evidence-health after
    # authenticating the immutable public leaf. Do not discard any source,
    # model, warning, value, date or other unrecognised field here.
    leaf = deepcopy(artifact)
    for field in ("catalog", "catalog_version", "evidence_health", "dates", "freshness"):
        leaf.pop(field, None)
    # Runtime price comparisons are not intrinsic calculation inputs. Restore
    # only this generation's exact placeholder before authenticating every
    # source, model, financial, date, warning and intrinsic-value field.
    leaf["market_comparison"] = {"status": "unavailable", "reason": "approved_eod_record_unavailable"}
    return is_exact_public_override(leaf)


def _assert_raw_free(value):
    if isinstance(value, dict):
        require(not RAW_FORBIDDEN_KEYS.intersection(value), "raw/private field in public artifact")
        for child in value.values():
            _assert_raw_free(child)
    elif isinstance(value, list):
        for child in value:
            _assert_raw_free(child)


def is_exact_public_override(artifact):
    """Authenticate only a pinned Q06 public leaf; never authorize release."""
    try:
        if not all(isinstance(v, str) and v for v in (
            PUBLIC_OVERRIDE_PINS_SHA, PUBLIC_OVERRIDE_MANIFEST_SHA, PUBLIC_OVERRIDE_CATALOG_VERSION
        )):
            return False
        path = Path(__file__).with_name("config") / "quality06_public_artifact_override_pins_v2.json"
        if path.is_symlink() or not path.is_file():
            return False
        raw = path.read_bytes()
        if sha(raw) != PUBLIC_OVERRIDE_PINS_SHA:
            return False
        pins = json.loads(raw)
        if pins.get("schema_version") != "US-QUALITY06-PUBLIC-ARTIFACT-OVERRIDE-PINS-1":
            return False
        if pins.get("manifest_sha256") != PUBLIC_OVERRIDE_MANIFEST_SHA or pins.get("catalog_version") != PUBLIC_OVERRIDE_CATALOG_VERSION:
            return False
        if set(pins.get("artifacts", {})) != TARGETS or not isinstance(artifact, dict):
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
    require(isinstance(ANCHOR_SHA, str) and len(ANCHOR_SHA) == 64, "compiled anchor pin placeholder")
    path = Path(__file__).with_name("config") / "quality06_staged_anchors_v2.json"
    require(path.is_file() and not path.is_symlink(), "compiled anchor file")
    raw = path.read_bytes()
    require(sha(raw) == ANCHOR_SHA, "compiled anchor bytes")
    value = json.loads(raw)
    require(value.get("schema_version") == SCHEMA, "compiled schema")
    require(set(value.get("targets", ())) == TARGETS, "compiled target scope")
    require(set(value.get("carry_forward", ())) == CARRY_FORWARD and set(value.get("held_updates", ())) == HELD, "compiled carry/held scope")
    require(set(value.get("private_only_diagnostics", ())) == PRIVATE_ONLY and set(value.get("unchanged_controls", ())) == CONTROLS, "compiled diagnostic/control scope")
    require(set(value.get("expected_issuer_mapping", ())) == TARGETS, "compiled issuer mapping")
    require(set(value.get("root_files", ())) == ROOT_FILES, "compiled root contract")
    return deepcopy(value)


def proof(root, name, expected, proof_reader):
    require(callable(proof_reader), "authenticated proof reader")
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader(root, name, expected)
    value = deepcopy(proof_reader(root, name, expected))
    require(digest(value) == expected, "parsed proof changed: " + name)
    return value


def _names(a):
    configured = a.get("proof_files", {})
    return {
        "parent_manifest": configured.get("parent_manifest", "approved-parent-manifest.json"),
        "grant": configured.get("grant", "quality-scope-authorization.json"),
        "binding": configured.get("binding", "quality-source-binding.json"),
        "confirmation": configured.get("confirmation", "quality-private-confirmation.json"),
        "proposal": configured.get("proposal", "quality-eligibility-proposal.json"),
        "eligibility": configured.get("eligibility", "quality-eligibility-verification.json"),
    }


def _context_uncached(root, manifest, proof_reader):
    a = anchors()
    names = _names(a)
    bound = proof(root, "manifest.json", a["manifest_sha256"], proof_reader)
    require(manifest == bound, "compiled manifest")
    require(manifest.get("staged_release_only") is True and manifest.get("staged_read_only_review_ready") is True, "read-only stage")
    require(all(manifest.get(k) is False for k in ("admission", "activation", "publication")), "no release")
    require("local_admission" not in manifest and "private_review" not in manifest and not manifest.get("private_integration_only"), "foreign permission lineage")
    require(manifest.get("catalog_kind") == "unadmitted_quality06_public_candidate" and str(manifest.get("catalog_version", "")).startswith("US-STAGED-QUALITY06-650-"), "namespace")
    parent = proof(root, names["parent_manifest"], a["parent_manifest_sha256"], proof_reader)
    grant = proof(root, names["grant"], a["approval_sha256"], proof_reader)
    binding = proof(root, names["binding"], a["binding_sha256"], proof_reader)
    confirmation = proof(root, names["confirmation"], a["confirmation_sha256"], proof_reader)
    proposal = proof(root, names["proposal"], a["proposal_sha256"], proof_reader)
    eligibility = proof(root, names["eligibility"], a["eligibility_sha256"], proof_reader)
    require(set(grant) == PREPARATION_AUTHORITY_FIELDS and grant.get("schema_version") == APPROVAL_SCHEMA, "exact approval fields")
    require(grant.get("source") == "direct_human_user" and isinstance(grant.get("user_request"), str) and grant["user_request"].strip(), "direct human scope")
    require(grant.get("issuer_specific_frozen_cutoffs_retained") is True and grant.get("public_preparation_scope_approved") is True and grant.get("staged_candidate_only") is True, "approved preparation")
    require(all(grant.get(k) is False for k in DENIED), "prep only")
    require(set(grant.get("targets", ())) == TARGETS and set(grant.get("carry_forward_prior_active_artifact_and_recipe", ())) == CARRY_FORWARD, "exact25/25 scope")
    require(set(grant.get("private_only_diagnostic_tickers", ())) == PRIVATE_ONLY and set(grant.get("private_held_update_tickers", ())) == HELD and set(grant.get("unchanged_control_tickers", ())) == CONTROLS, "private/held/control scope")
    require(grant.get("revision_specific_new_filing_holds_required") is True and grant.get("existing_refresh_support_and_hold_epochs_preserved") is True, "filing/support guard")
    require(grant.get("HWM_source_role_unit_and_unchanged_value_gate_approved") is True, "HWM source-role gate")
    require(grant.get("proposal_sha256") == a["proposal_sha256"] and grant.get("eligibility_verification_sha256") == a["eligibility_sha256"] and grant.get("private_confirmation_sha256") == a["confirmation_sha256"], "approval ancestry")
    require(proposal.get("schema_version") == PROPOSAL_SCHEMA and set(proposal.get("proposed_preparation_tickers", ())) == TARGETS and proposal.get("public_preparation_permission_issued") is False, "unbound proposal")
    require(eligibility.get("schema_version") == ELIGIBILITY_SCHEMA and str(eligibility.get("status", "")).startswith("unbound25_"), "unbound eligibility handoff")
    require(set(eligibility.get("proposed_preparation_tickers", ())) == TARGETS and eligibility.get("binding_candidate_admission_activation_publication") is False, "unbound eligibility scope")
    require(confirmation.get("schema_version") == CONFIRMATION_SCHEMA and confirmation.get("status") == "private_recovery_results_user_confirmed", "confirmed private scope")
    require(confirmation.get("confirmed_private_Low_count") == 26 and set(confirmation.get("confirmed_private_Low_ranges", ())) == TARGETS | PRIVATE_ONLY and confirmation.get("unchanged_count") == 1 and set(confirmation.get("preserved_unchanged_ranges", ())) == CONTROLS and confirmation.get("held_count") == 23 and set(confirmation.get("preserved_held_updates", ())) == HELD, "confirmed private26/control1/held23")
    require(binding.get("schema_version") == BINDING_SCHEMA and binding.get("model_policy_version") == MODEL_VERSION and binding.get("issuer_specific_frozen_cutoffs_retained") is True, "source/model binding")
    for field, key in (("approval_sha256", "approval_sha256"), ("private_confirmation_sha256", "confirmation_sha256"), ("proposal_sha256", "proposal_sha256"), ("eligibility_sha256", "eligibility_sha256")):
        require(binding.get(field) == a[key], "binding ancestry " + field)
    require(set(binding.get("targets", ())) == TARGETS and set(binding.get("carry_forward", ())) == CARRY_FORWARD and set(binding.get("private_only_diagnostics", ())) == PRIVATE_ONLY and set(binding.get("private_held_updates", ())) == HELD and set(binding.get("unchanged_controls", ())) == CONTROLS, "binding scope")
    require(binding.get("all25_revision_specific_new_filing_holds") is True and all(binding.get(k) is False for k in ("admission", "activation", "publication", "new_capture_or_refresh", "economic_values_changed")), "binding permission")
    current = {e["ticker"]: e for e in manifest["entries"]}; old = {e["ticker"]: e for e in parent["entries"]}
    require(len(current) == len(manifest["entries"]) == len(parent["entries"]) == len(old) == 650 and set(current) == set(old), "650 identity membership")
    require(set(manifest.get("private_recipe_sha256", {})) == set(parent.get("private_recipe_sha256", {})), "recipe membership")
    require(manifest.get("base_manifest_sha256") == manifest.get("approved_base_manifest_sha256") == a["parent_manifest_sha256"] and manifest.get("base_catalog_version") == parent.get("catalog_version"), "parent identity")
    records = binding.get("records", {}); originals = {r["ticker"]: r for r in proposal.get("rows", [])}
    require(set(records) == TARGETS | CARRY_FORWARD and len(records) == 50 and {t for t, r in records.items() if r.get("updated_value_prepared")} == TARGETS, "50 reviewed records")
    require(set(originals) == TARGETS | CARRY_FORWARD, "proposal 50-row scope")
    for t in set(old) - TARGETS:
        require(current[t] == old[t] and manifest["private_recipe_sha256"].get(t) == parent["private_recipe_sha256"].get(t), t + " unchanged625 artifact/recipe")
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


def context(root, manifest, proof_reader):
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader.context_for(root, manifest, lambda: _context_uncached(root, manifest, proof_reader))
    return _context_uncached(root, manifest, proof_reader)


def target(root, manifest, ticker, record, entry, proof_reader):
    from .artifacts import sanitize_public_artifact
    from .automated_review import assess_artifact
    try:
        from .latest_calculator import baseline_version
    except ImportError:
        from .calculator import baseline_version
    from .calculation_recipe import evaluate_recipe
    a = anchors()
    artifact = proof(root, "artifacts/" + ticker + ".json", entry["artifact_sha256"], proof_reader)
    recipe = proof(root, "recipes/" + ticker + ".json", manifest["private_recipe_sha256"][ticker], proof_reader)
    _assert_raw_free(artifact)
    require(artifact.get("issuer") == a["expected_issuer_mapping"][ticker] and artifact["issuer"].get("ticker") == ticker and artifact["issuer"].get("cik") == record["cik"], ticker + " mapping")
    require(artifact.get("source_financial_statement") == record["exact_source_header"] == record["source_to_recipe_review"]["canonical_source_header"], ticker + " canonical source header")
    cutoff = record["proposed_evidence_cutoff"]
    require(artifact.get("valuation_date") == recipe.get("valuation_date") == recipe.get("evidence_cutoff") == cutoff, ticker + " preserved issuer date")
    require(all(artifact["source_financial_statement"][k] <= cutoff for k in ("filed_date", "period_end")), ticker + " financial cutoff")
    expected = record["confirmed_private_range"]
    expected_model = record["expected_model"]
    require(artifact.get("model_version") == MODEL_VERSION and artifact.get("model_policy", {}).get("primary") == expected_model, ticker + " exact model")
    require(artifact.get("public_assumptions", {}).get("source_policy_binding_sha256") == manifest.get("quality_source_binding_sha256") == a["binding_sha256"], ticker + " public binding")
    require(artifact.get("reliability", {}).get("label") == "Low" and artifact.get("availability_type") == "conditional_estimate" and artifact.get("review", {}).get("publication_state") == "review_required" and not artifact.get("review", {}).get("errors"), ticker + " Conditional/Low")
    require(not assess_artifact(artifact).get("blocking_reasons") and sanitize_public_artifact(artifact) == artifact, ticker + " ordinary public gate")
    dto = record.get("forecast_assumptions")
    require(dto is not None, ticker + " reviewed forecast DTO")
    from .quality06_disclosures import public_forecast_assumptions
    require(public_forecast_assumptions(dto, issuer=ticker) == dto, ticker + " reviewed semantic DTO")
    require(dto.get("forecast_mode") == recipe.get("scenarios", {}).get("base", {}).get("engine", "") + "_exact" or (ticker in REIT_TARGETS and dto.get("forecast_mode") == "reit_affo_exact"), ticker + " reviewed engine mode")
    recipe_inputs = recipe.get("scenarios", {}).get("base", {}).get("inputs", {})
    if ticker in REIT_TARGETS:
        require(expected_model == "affo_dcf" and recipe.get("scenarios", {}).get("base", {}).get("engine") == "cash_schedule", ticker + " REIT model/engine")
        require(dto.get("server_engine") == "cash_schedule" and dto.get("forecast_years") == 8, ticker + " REIT cash schedule")
        require(len(recipe_inputs.get("cash_flows", [])) == 8, ticker + " REIT cash-flow horizon")
        require(all(recipe.get("scenarios", {}).get(s, {}).get("inputs", {}).get("shares") == 1.0 and recipe.get("scenarios", {}).get(s, {}).get("inputs", {}).get("net_bridge") == 0.0 for s in ("bear", "base", "bull")), ticker + " REIT per-common-share bridge")
        require(record.get("REIT_base_exactly_unchanged") is True and record.get("REIT_no_second_recurring_capital_or_EV_bridge") is True, ticker + " REIT base/source preservation")
        require(dto.get("reit_base_unchanged") is True and dto.get("per_common_share_no_EV_bridge") is True, ticker + " REIT DTO preservation")
    else:
        recipe_horizon = recipe_inputs.get("forecast_years", recipe_inputs.get("years"))
        expected_horizon = 5 if recipe.get("scenarios", {}).get("base", {}).get("engine") == "constant_growth_fcff" else recipe_horizon
        require(dto.get("forecast_years") == expected_horizon, ticker + " reviewed horizon")
    require({k: artifact["scenario_range"][k] for k in ("low", "base", "high")} == expected, ticker + " values")
    require(set(artifact.get("models", {})) == {expected_model} and artifact["models"][expected_model]["intrinsic_value_per_share"] == expected["base"], ticker + " base model")
    require(set(artifact.get("scenarios", {})) == {"bear", "base", "bull"}, ticker + " scenarios")
    for name, key in (("bear", "low"), ("base", "base"), ("bull", "high")):
        require(set(artifact["scenarios"][name]) == {expected_model} and artifact["scenarios"][name][expected_model]["intrinsic_value_per_share"] == expected[key], ticker + " scenario value")
    require(recipe.get("ticker") == ticker and str(recipe.get("cik")).zfill(10) == str(record["cik"]).zfill(10) and recipe.get("private_only") is True and recipe.get("baseline_version") == baseline_version(artifact), ticker + " recipe identity")
    require(digest({k: recipe[k] for k in ("scenarios", "editable", "warnings")}) == record["bound_recipe_economic_sha256"], ticker + " economics")
    require(replay_matches(evaluate_recipe(recipe)["range"], expected), ticker + " bounded runtime replay")
    require(set(record.get("required_public_disclosures", ())) <= set(artifact.get("review", {}).get("warnings", ())) and set(recipe.get("warnings", ())) <= set(artifact.get("review", {}).get("warnings", ())), ticker + " warnings")
    if ticker == "HWM":
        gate = record.get("HWM_source_role_gate")
        require(isinstance(gate, dict), "HWM named source-role gate")
        require(gate.get("unit") == "shares" and gate.get("value") == 0, "HWM preferred shares unit/value")
        require(gate.get("ticker") == "HWM" and str(gate.get("cik")).zfill(10) == str(record["cik"]).zfill(10), "HWM gate issuer")
        require(gate.get("concept") == "us-gaap:PreferredStockSharesOutstanding", "HWM gate concept")
        require(isinstance(gate.get("accession"), str) and gate.get("accession"), "HWM gate accession")
        require(isinstance(gate.get("period_end"), str) and gate.get("period_end"), "HWM gate period")
        require(isinstance(gate.get("source_document_sha256"), str) and len(gate.get("source_document_sha256")) == 64, "HWM gate source hash")
        require(isinstance(gate.get("root_source_receipt_sha256"), str) and len(gate.get("root_source_receipt_sha256")) == 64, "HWM gate root receipt hash")
        require(gate.get("explicit_fixed_zero_verified") is True and gate.get("original_USD_label_not_propagated") is True, "HWM gate metadata semantics")
        require(gate.get("financial_amounts_claims_shares_and_all_values_unchanged") is True, "HWM gate unchanged values")
        require(gate.get("preferred_capital_inferred_from_zero_share_count") is False and gate.get("legal_absence_inferred") is False, "HWM no waiver/inference")
        require(gate.get("future_changed_filing_adapter_approved") is False, "HWM future-filing adapter hold")
        require(dto.get("source_role_gate_verified") is True and dto.get("preferred_share_source_unit") == "shares" and dto.get("preferred_shares_outstanding_source") == 0, "HWM DTO gate")
    return artifact


def expected_policy(ticker, record, artifact_sha, old, approval_sha, binding_sha):
    old = old or {}
    proposed_epoch = record.get("proposed_review_hold_epoch")
    require(
        proposed_epoch == record.get("proposed_evidence_cutoff")
        == record.get("proposed_public_valuation_date"),
        ticker + " exact source/valuation epoch",
    )
    if old.get("source_epoch") is not None:
        require(old["source_epoch"] == proposed_epoch,
                ticker + " inherited source epoch changed")
    return {
        "schema_version": "FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1", "version": "US-QUALITY06-REVISION-FILING-HOLD-1",
        "ticker": ticker, "cik": record["cik"], "private_only": False, "public_release_authorized": False,
        "staged_public_candidate_authorized": True, "admission_authorized": False, "activation_authorized": False,
        "publication_authorized": False, "new_filing_hold_before_capture": True, "direct_binding_rejected": True,
        "auto_revaluation": False, "source_epoch": record.get("proposed_review_hold_epoch"),
        "reasons": ["Revised Quality06 dated baseline requires new source/model/assumption review before any new financial filing or amendment can be recalculated."],
        "pins": {"public_baseline": artifact_sha, "private_economic_payload": record["bound_recipe_economic_sha256"], "quality_source_policy_binding": binding_sha, "release_scope_approval": approval_sha, "predecessor_policy": digest(old)},
        "predecessor_policy_retained_for_existing_active_baseline": True, "revised_baseline_adapter_readiness_not_inherited": True,
    }


def validate(root, manifest, *, deep=False, proof_reader=None):
    a, parent, binding, current = context(root, manifest, proof_reader)
    policies = proof(root, "refresh-policies.json", a["policies_sha256"], proof_reader)
    oldpolicies = proof(root, "approved-parent-policies.json", a["parent_policies_sha256"], proof_reader)
    require(set(oldpolicies).isdisjoint(REIT_TARGETS), "REIT predecessor policies must be absent")
    require(set(policies) == (set(oldpolicies) | REIT_TARGETS) and len(policies) == 581, "exact 581 policy membership")
    require(set(policies) <= set(current), "policy rows must be catalog rows")
    for ticker in set(oldpolicies) - TARGETS:
        require(policies[ticker] == oldpolicies[ticker], ticker + " untouched predecessor policy")
    for ticker in policies:
        old = oldpolicies.get(ticker, {})
        expected = expected_policy(ticker, binding["records"][ticker], current[ticker]["artifact_sha256"], old, a["approval_sha256"], a["binding_sha256"]) if ticker in TARGETS else old
        require(policies[ticker] == expected, ticker + " exact policy/support guard")
    if deep:
        require({p.name for p in Path(root).iterdir()} == ROOT_FILES, "root filenames")
        require({p.name for p in (Path(root) / "artifacts").iterdir()} == {t + ".json" for t in current}, "artifact files")
        require({p.name for p in (Path(root) / "recipes").iterdir()} == {t + ".json" for t in manifest["private_recipe_sha256"]}, "recipe files")
        for ticker in TARGETS:
            target(root, manifest, ticker, binding["records"][ticker], current[ticker], proof_reader)
    return {t: (e["cik"], e["batch"], e["availability_type"], e["artifact_sha256"]) for t, e in current.items() if t not in TARGETS}


def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader):
    _, _, binding, current = context(root, manifest, proof_reader)
    require(ticker in current and sha(raw) == current[ticker]["artifact_sha256"], "leaf bytes")
    if ticker in TARGETS:
        target(root, manifest, ticker, binding["records"][ticker], current[ticker], proof_reader)
        return False
    return True


def validate_registry(root, manifest, registry, *, proof_reader):
    a, parent, _, current = context(root, manifest, proof_reader)
    require(digest(registry) == a["registry_sha256"], "registry anchor")
    rows = {r["ticker"]: r for r in registry["entries"]}
    predecessor_registry = proof(root, "approved-parent-registry.json", a["parent_registry_sha256"], proof_reader)
    oldrows = {r["ticker"]: r for r in predecessor_registry["entries"]}
    require(len(rows) == len(registry["entries"]) == 650 and set(rows) == set(current), "registry650")
    require(registry.get("baseline_manifest_sha256") == a["manifest_sha256"] and registry.get("baseline_catalog_version") == manifest.get("catalog_version"), "registry lineage")
    for ticker in rows:
        expected = deepcopy(oldrows[ticker])
        if ticker in TARGETS:
            binding = proof(root, "quality-source-binding.json", a["binding_sha256"], proof_reader)
            expected.update(baseline_sha256=current[ticker]["artifact_sha256"], availability_type="conditional_estimate", primary_model=binding["records"][ticker]["expected_model"], forecast_mode=binding["records"][ticker]["forecast_assumptions"]["forecast_mode"], controlling_filing=binding["records"][ticker]["exact_source_header"], source_audit="docs/audit/us-quality06-public-staged.md", recipe_status="quality06_recipe_revision_new_filing_held")
        require(rows[ticker] == expected, ticker + " exact registry row")
    return registry


def review_selection(root, authority_file, authority, manifest, manifest_sha, *, proof_reader):
    a = anchors()
    require(set(authority) == AUTHORITY_FIELDS and authority.get("schema_version") == REVIEW_SCHEMA and authority.get("read_only") is True, "review fields")
    require(all(authority.get(k) is False for k in ("admission", "activation", "publication", "save", "automatic_new_source_revaluation")), "review permission")
    require(authority.get("manifest_sha256") == manifest_sha == a["manifest_sha256"] and authority.get("catalog_version") == manifest.get("catalog_version") and authority.get("registry_sha256") == a["registry_sha256"], "review ancestry")
    validate(root, manifest, deep=True, proof_reader=proof_reader)
    registry = proof(authority_file.parent, "runtime/registry.json", a["registry_sha256"], proof_reader)
    validate_registry(root, manifest, registry, proof_reader=proof_reader)
    return root, manifest_sha
