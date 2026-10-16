"""Closed Batch05 staged public-preparation authority; no admission or activation."""

import hashlib
import json
from pathlib import Path


PARENT_SHA = "98609f24350af2118db0c6f3f4a9ea57ee50e1e029def0637e7f6748e411b6f5"
PARENT_VERSION = "US-ADMITTED-B04-540-868c81efc1d6625a07c4a086"
PARENT_REGISTRY_SHA = "fe355f8303c05277e908211f2e2435f36361fbd86c775c2349a5124c4502f141"
APPROVAL_SHA = "1fb5db518c8c79ef04d7d466e9c17cf70d15af815c43111f3366f140952489ce"
PROPOSAL_SHA = "4872eba06c16fdc4210a05e5566a0d715f7d515d209a5edd50eb35fbb344a4cc"
RANGES_SHA = "181273de37bd6cf6b6b2daff5ada9340dd512d47d7f001defae1e7a00fb20aaf"
SOURCE_DISCLOSURE_SHA = "188635e7ed78c5341e77ff3dc8fce2f5391390f83ab2b72b301098e3ce6c2be4"
SCHEMA = "US-B05-APPROVED-PARENT-INHERITANCE-1"
REVIEW_SCHEMA = "US-B05-READ-ONLY-STAGED-REVIEW-1"
CUTOFF = "2026-10-07"

IDENTITIES = {
    "USLM": "0000082020", "IIIN": "0000764401", "POWL": "0000080420",
    "PLPC": "0000080035", "HWKN": "0000046250", "AVNT": "0001122976",
    "EBF": "0000033002", "ACU": "0000002098", "TILE": "0000715787",
    "NWPX": "0001001385",
}
TARGETS = {"USLM", "IIIN", "POWL", "PLPC", "HWKN", "EBF", "ACU", "TILE", "NWPX"}
NULLS = {"AVNT"}
ROOT_FILES = {
    "manifest.json", "refresh-policies.json", "approved-base-manifest.json",
    "approved-parent-manifest.json", "approved-parent-registry.json",
    "approved-parent-policies.json", "public-scope-authorization.json",
    "source-disclosure-binding.json",
}
ECONOMIC_HASHES = {
    "ACU": "09ea58b1fc503bd38cfaf855db695fffb86ca76a548a2679a3f026026e39967c",
    "EBF": "0dfa42b2d32db0211e1bd8f96af4a800a6062d99f906a4794a95626b97ae363e",
    "HWKN": "4c1d9f260ee02154566821d3f0af300f9ebed95e49656793ef09ccadc26c04d7",
    "IIIN": "9e25dc07956a13f27d1b124e14e0ff6d8680f20ac8bfa575d30a61eaff2233d8",
    "NWPX": "3b2b098a6fd85c6c380507219938d557d7b108c647f952762d613fd1b5f9ef67",
    "PLPC": "c4b2f18ccd23d4af3a08dc21ae80cc3316483a7ab119fac2badba55d52ae15ff",
    "POWL": "5d26cec0de4afffc94b10282a916c49d58b48b34a180f085c4f71ea185d2816a",
    "TILE": "d8ef12cf9a402a37c535cb38a71d1559a1276415a3f883d1c93da5c7fde4f387",
    "USLM": "a2650f5d93a4b143c65591cec471205cee2a7194e5dc3497d6fb376f85241577",
}
SOURCE_HEADER_SHA256 = {
    "ACU": "6e095191aee5e4b7c19b2c81e98e52b930f44a4068bb96f11c20ea0c9865ca80",
    "AVNT": "cf4627f3bf377731d569baa964112faeb303727b35051c0c0face55bfbcc047b",
    "EBF": "1d0c6d0c56474602ec90d790fde8cf15b32862008bc98620daac09ce3d06f614",
    "HWKN": "1da88c92813a95b43833751e79c030783dcdd4a8e89bae562ba64e6215e7d7dc",
    "IIIN": "a87c72950fdedc37f3b16ef3ad4d52d45628ee94169cdad40b751f9d8c47f8d4",
    "NWPX": "d031939c42d389ae164e86a9c96d46a3a0a21ea74fd5f9394f3e23addc86904d",
    "PLPC": "1f207307b96ba1a89201dd6f6466e1920ed7435a9f615bfa9086d57237e89a61",
    "POWL": "20648786e03a04054e6f5fd146cafa8eb7726157f1bcb83fefb3c8e7ad0f92d7",
    "TILE": "430777b5447a2cf65da3b5e30827732cbfa51c6ea5865f88c0d4712ea9fe2195",
    "USLM": "1310f5c1e161eaa447bd8056ef89bdda26ff9d2a2f4eb307b8d10be8ecf34063",
}
NATIVE_ARCHETYPES = {"ACU": "b05_common_ri__capital_goods_machinery"}
MANUAL_ARCHETYPES = {
    "USLM": "b05_common_ri__industrial", "IIIN": "b05_common_ri__industrial",
    "POWL": "b05_common_ri__capital_goods_machinery", "PLPC": "b05_common_ri__industrial",
    "HWKN": "b05_common_ri__specialty_chemicals", "EBF": "b05_common_ri__industrial",
    "TILE": "b05_common_ri__consumer_operating", "NWPX": "b05_common_ri__industrial",
}
TARGET_CONFIDENCE = {ticker: 0.6 if ticker == "ACU" else 0.0 for ticker in TARGETS}
MANUAL_REASON = "Unrated manual issuer mapping: classification_confidence 0.0 is a conservative guard sentinel, not measured confidence or calibration."
PUBLIC_POLICY_VERSION = "US-B05-PUBLIC-COMMON-RI-1"
SOURCE_DISCLOSURE_SCHEMA = "US-B05-APPROVED-PUBLIC-SOURCE-DISCLOSURE-BINDING-1"
AUTHORITY_FIELDS = {"schema_version", "read_only", "manifest_sha256", "catalog_version", "registry_sha256", "admission", "activation", "publication", "save", "automatic_new_source_revaluation"}


def require(value, why):
    if not value:
        raise ValueError("Batch05 staged review rejected: " + why)


def _canonical_sha(value):
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def _rows(manifest):
    return {entry["ticker"]: (entry["cik"], entry["batch"], entry["availability_type"], entry["artifact_sha256"]) for entry in manifest["entries"]}


def _target_classification(artifact, ticker):
    issuer = artifact.get("issuer", {})
    require(issuer.get("ticker") == ticker, ticker + " classification identity changed")
    require(issuer.get("override_applied") is True, ticker + " classification override is not explicit")
    require(issuer.get("classification_confidence") == TARGET_CONFIDENCE[ticker], ticker + " classification confidence changed")
    reason = str(issuer.get("classification_reason", ""))
    require("reported parent-common GAAP book/earnings residual-income override" in reason, ticker + " common-RI override reason is missing")
    if ticker in NATIVE_ARCHETYPES:
        require(issuer.get("primary_archetype") == NATIVE_ARCHETYPES[ticker], ticker + " native archetype changed")
        require("Native SEC-SIC routing score retained" in reason, ticker + " native routing provenance is missing")
    else:
        require(issuer.get("primary_archetype") == MANUAL_ARCHETYPES[ticker], ticker + " manual archetype changed")
        require(MANUAL_REASON in reason, ticker + " manual sentinel meaning is missing")


def _proof_value(proof, *paths):
    for path in paths:
        value = proof
        for key in path.split("."):
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value is not None:
            return value
    return None


def validate_source_disclosure(proof_reader, root, *, expected_sha256=None):
    """Authenticate source/disclosure scope without authorizing release."""
    expected = SOURCE_DISCLOSURE_SHA if expected_sha256 is None else expected_sha256
    require(isinstance(expected, str) and len(expected) == 64 and set(expected) != {"0"}, "source disclosure hash anchor is pending")
    proof = proof_reader(root, "source-disclosure-binding.json", expected)
    required = {
        "AVNT_private_numeric_unchanged", "AVNT_public_null_anchor_tax_gate_preserved", "activation",
        "admission", "all_private_values_and_filing_holds_unchanged", "approved_proposal_sha256",
        "automatic_new_source_revaluation", "cutoff", "facts_and_forecast_assumptions_separate",
        "no_new_source_capture_or_economic_normalization", "no_new_valuation_inputs_or_floor",
        "policy_binding_scope", "public_nulls", "publication", "records", "schema_version",
        "scope_approval_sha256", "targets",
    }
    require(set(proof) == required, "source disclosure exact fields")
    require(proof.get("schema_version") == SOURCE_DISCLOSURE_SCHEMA, "source disclosure schema changed")
    require(proof.get("cutoff") == CUTOFF and proof.get("approved_proposal_sha256") == PROPOSAL_SHA and proof.get("scope_approval_sha256") == APPROVAL_SHA, "source disclosure pins changed")
    require(set(proof.get("targets", [])) == TARGETS and set(proof.get("public_nulls", [])) == NULLS, "source disclosure target/null scope changed")
    for key in ("activation", "admission", "automatic_new_source_revaluation", "publication"):
        require(proof.get(key) is False, "source disclosure grants " + key)
    for key in ("AVNT_private_numeric_unchanged", "AVNT_public_null_anchor_tax_gate_preserved", "all_private_values_and_filing_holds_unchanged", "facts_and_forecast_assumptions_separate", "no_new_source_capture_or_economic_normalization", "no_new_valuation_inputs_or_floor"):
        require(proof.get(key) is True, "source disclosure preservation gate missing: " + key)
    require(set(proof["records"]) == set(IDENTITIES), "source disclosure record membership changed")
    for ticker, record in proof["records"].items():
        require(record.get("identity", {}).get("ticker") == ticker and str(record.get("identity", {}).get("cik")).zfill(10) == IDENTITIES[ticker], ticker + " source identity changed")
        require(all(isinstance(record.get(key), str) and len(record[key]) == 64 for key in ("original_artifact_sha256", "original_recipe_sha256", "source_ledger_sha256", "confirmed_private550_artifact_sha256", "confirmed_private550_recipe_sha256")), ticker + " source/private preservation hash missing")
        header = record.get("source_header", {})
        require(_canonical_sha(header) == SOURCE_HEADER_SHA256[ticker], ticker + " source header changed")
        require(isinstance(record.get("primary_proofs"), dict) and "primary" in record["primary_proofs"] and "annual" in record["primary_proofs"], ticker + " primary proof missing")
        for name, source in record["primary_proofs"].items():
            require(isinstance(source, dict) and isinstance(source.get("document_sha256"), str) and len(source["document_sha256"]) == 64, ticker + " " + name + " document proof missing")
            require(source.get("filed_date", "") <= CUTOFF and source.get("report_date", "") <= CUTOFF, ticker + " post-cutoff source proof")
    ebf = proof["records"]["EBF"]["selected_anchor"]
    require(ebf.get("FY2025_special_cash_dividend_USD") == 65000000 and ebf.get("FY2025_special_dividend_per_share_USD") == 2.5 and ebf.get("future_payout_ratio_is_assumption") == 0.4, "EBF special distribution/payout scope changed")
    require("actual special-containing distributions remain history" in ebf.get("future_payout_policy", ""), "EBF special distribution policy is missing")
    return proof


def _allowed_catalog_namespace(version):
    return str(version).startswith("US-STAGED-EXPANSION-B05-550-") or str(version).startswith("US-REFRESH-550-2026-10-07-")


def _validate_public_artifact(proof_reader, root, ticker, row, ranges):
    artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
    issuer = artifact.get("issuer", {})
    require(str(issuer.get("cik")).zfill(10) == IDENTITIES[ticker], ticker + " public identity changed")
    require("private_review_only" not in artifact and "source_ledger" not in artifact, ticker + " private payload leaked")
    require(_canonical_sha(artifact.get("source_financial_statement", {})) == SOURCE_HEADER_SHA256[ticker], ticker + " frozen source header changed")
    require(artifact.get("valuation_date") == CUTOFF and artifact.get("assumption_date") == CUTOFF, ticker + " public dates changed")
    require(artifact.get("availability_type") == "conditional_estimate" and artifact.get("primary_valuation_method") == "residual_income", ticker + " public model/status changed")
    require(artifact.get("model_policy", {}).get("primary") == "residual_income", ticker + " public model policy changed")
    require(artifact.get("public_assumptions", {}).get("forecast_policy_version") == PUBLIC_POLICY_VERSION, ticker + " public policy version changed")
    require(artifact.get("reliability", {}).get("label") == "Low", ticker + " reliability is not Low")
    _target_classification(artifact, ticker)
    require(artifact.get("review", {}).get("publication_state") == "review_required", ticker + " review state changed")
    require(set(artifact.get("review", {}).get("warnings", [])) >= set(artifact.get("reliability", {}).get("warnings", [])), ticker + " warning contract changed")
    ranges[ticker] = {key: artifact["scenario_range"][key] for key in ("low", "base", "high")}


def validate(root, manifest, *, deep=False, proof_reader=None):
    require(callable(proof_reader), "verified proof reader missing")
    proof = manifest.get("approved_base_inheritance")
    require(isinstance(proof, dict) and set(proof) == {"schema_version", "parent_manifest_sha256", "parent_catalog_version", "scope_approval_sha256", "proposal_sha256"}, "inheritance exact schema")
    require(proof == {"schema_version": SCHEMA, "parent_manifest_sha256": PARENT_SHA, "parent_catalog_version": PARENT_VERSION, "scope_approval_sha256": APPROVAL_SHA, "proposal_sha256": PROPOSAL_SHA}, "parent/scope pins")
    require(manifest.get("approved_base_manifest_sha256") == PARENT_SHA and manifest.get("release_scope_approval_sha256") == APPROVAL_SHA, "consistent approved base/scope metadata")
    require(_allowed_catalog_namespace(manifest.get("catalog_version")), "approved staged version namespace")
    require(manifest.get("base_catalog_version") == PARENT_VERSION and manifest.get("base_manifest_sha256") == PARENT_SHA, "consistent staged parent")
    require(manifest.get("staged_release_only") is True and manifest.get("catalog_kind") == "unadmitted_public_contract_candidate", "staged scope")
    require(not manifest.get("private_integration_only") and "private_review" not in manifest, "no private projection privilege")
    require("local_admission" not in manifest and "supported_refresh_integration" not in manifest, "no inherited release grants")
    require(all(manifest.get(key) is False for key in ("admission", "activation", "publication")), "release remains unauthorized")
    require(manifest.get("staged_read_only_review_ready") is True, "read-only review marker")

    parent = proof_reader(root, "approved-parent-manifest.json", PARENT_SHA)
    require(parent.get("catalog_version") == PARENT_VERSION and len(parent.get("entries", [])) == 540, "authentic540 parent")
    approval = proof_reader(root, "public-scope-authorization.json", APPROVAL_SHA)
    require(approval.get("schema_version") == "US-B05-PUBLIC-STAGED-PREPARATION-AUTHORIZATION-1" and approval.get("policy_scope_approved") is True and approval.get("staged_candidate_only") is True, "approved preparation only")
    require(set(approval.get("public_preparation_targets", [])) == TARGETS and set(approval.get("public_unavailable_additions", [])) == NULLS, "approved9/1 scope")
    require(approval.get("evidence_cutoff") == CUTOFF and approval.get("approved_proposal_sha256") == PROPOSAL_SHA and approval.get("AVNT_public_null_and_private_value_preservation_gate") is True, "cutoff/proposal/AVNT scope")
    for key in ("admission", "activation", "publication", "automatic_new_source_revaluation", "new_recovery", "new_source_capture", "next_batch", "valuation_recalculation", "live_runtime_promotion", "new_live_refresh_job", "push", "cloud_deployment"):
        require(approval.get(key) is False, "broader authority: " + key)
    validate_source_disclosure(proof_reader, root)

    old, current = _rows(parent), _rows(manifest)
    require(len(manifest["entries"]) == len(current) == 550 and set(current) == set(old) | set(IDENTITIES), "exact550 identities")
    require(manifest.get("artifact_count") == 550 and manifest.get("availability_counts") == {"available": 116, "conditional_estimate": 391, "not_available": 43}, "exact550 availability counts")
    require(all(current[t] == row for t, row in old.items()), "old540 identity/status/artifact drift")
    require(all(current[t][0] == cik and current[t][1] == 55 and current[t][2] == ("conditional_estimate" if t in TARGETS else "not_available") for t, cik in IDENTITIES.items()), "new9/1 identity/status drift")
    index = manifest.get("private_recipe_sha256")
    require(isinstance(index, dict) and len(index) == 507 and set(index) == set(parent["private_recipe_sha256"]) | TARGETS, "public recipe membership")
    require(all(index.get(t) == digest for t, digest in parent["private_recipe_sha256"].items()), "old540 recipe drift")
    require(not (set(index) & NULLS), "public-null recipes absent")
    policies = proof_reader(root, "refresh-policies.json", manifest["private_refresh_policy_sha256"])
    parent_policies = proof_reader(root, "approved-parent-policies.json", parent["private_refresh_policy_sha256"])
    require(set(policies) == set(parent_policies) | set(IDENTITIES) and all(policies[t] == p for t, p in parent_policies.items()), "old policy drift")
    for ticker in IDENTITIES:
        policy = policies[ticker]
        require(policy.get("schema_version") == "FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1" and policy.get("ticker") == ticker and str(policy.get("cik")).zfill(10) == IDENTITIES[ticker] and policy.get("private_only") is False and policy.get("staged_public_candidate_authorized") is True and policy.get("new_filing_hold_before_capture") is True and policy.get("direct_binding_rejected") is True and policy.get("source_epoch") == CUTOFF, ticker + " new-filing hold contract")
        for key in ("public_release_authorized", "auto_revaluation", "admission_authorized", "activation_authorized", "publication_authorized"):
            require(policy.get(key) is False, ticker + " release authority")
    ranges = {}
    for ticker in IDENTITIES:
        row = current[ticker]
        if ticker in TARGETS:
            _validate_public_artifact(proof_reader, root, ticker, row, ranges)
        else:
            artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
            require(str(artifact.get("issuer", {}).get("cik")).zfill(10) == IDENTITIES[ticker] and artifact.get("availability_type") == "not_available" and "private_review_only" not in artifact, ticker + " public-null privacy/status")
            require(_canonical_sha(artifact.get("source_financial_statement", {})) == SOURCE_HEADER_SHA256[ticker], ticker + " frozen source header changed")
            require(all(artifact.get("scenario_range", {}).get(key) is None for key in ("low", "base", "high")), ticker + " public-null range")
            require(artifact.get("review", {}).get("publication_state") == "withheld" and artifact.get("confidence", {}).get("label") is None, ticker + " public-null state")
            require(artifact.get("valuation_date") == CUTOFF and artifact.get("assumption_date") == CUTOFF, ticker + " public-null dates")
    require(_canonical_sha(ranges) == RANGES_SHA, "accepted nine-target range anchor")
    if deep:
        from .artifacts import sanitize_public_artifact
        from .calculation_recipe import evaluate_recipe
        require({path.name for path in Path(root).iterdir()} == ROOT_FILES | {"artifacts", "recipes"}, "exact staged root allowlist; no historical release grants")
        expected = {"approved-base-manifest.json": PARENT_SHA, "approved-parent-manifest.json": PARENT_SHA, "approved-parent-registry.json": PARENT_REGISTRY_SHA, "approved-parent-policies.json": parent["private_refresh_policy_sha256"], "public-scope-authorization.json": APPROVAL_SHA, "source-disclosure-binding.json": SOURCE_DISCLOSURE_SHA}
        require(manifest.get("preserved_prior_estimate_sha256") == expected, "exact preparation proof index")
        for name, digest in expected.items():
            proof_reader(root, name, digest)
        require({path.stem for path in (Path(root) / "artifacts").glob("*.json")} == set(current), "artifact files exact")
        require({path.stem for path in (Path(root) / "recipes").glob("*.json")} == set(index), "recipe files exact")
        for ticker, row in current.items():
            artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
            if ticker in IDENTITIES:
                require(sanitize_public_artifact(artifact) == artifact, ticker + " ordinary public projection/idempotence")
            if ticker in TARGETS:
                recipe = proof_reader(root, "recipes/" + ticker + ".json", index[ticker])
                economic = {key: recipe[key] for key in ("scenarios", "warnings", "editable")}
                require(_canonical_sha(economic) == ECONOMIC_HASHES[ticker], ticker + " accepted economic recipe/warning anchor")
                require(set(recipe.get("warnings", [])) <= set(artifact.get("review", {}).get("warnings", [])), ticker + " source warnings retained")
                try:
                    from .latest_calculator import baseline_version
                except ModuleNotFoundError as exc:
                    if exc.name != __package__ + ".latest_calculator":
                        raise
                    from .calculator import baseline_version
                require(recipe.get("ticker") == ticker and str(recipe.get("cik")).zfill(10) == IDENTITIES[ticker], ticker + " recipe identity")
                require(recipe.get("valuation_date") == artifact.get("valuation_date") and recipe.get("evidence_cutoff") == CUTOFF, ticker + " recipe dates")
                require(recipe.get("baseline_version") == baseline_version(artifact), ticker + " recipe baseline")
                require(evaluate_recipe(recipe)["range"] == ranges[ticker], ticker + " public recipe replay")
            elif ticker in NULLS:
                require(not (Path(root) / "recipes" / (ticker + ".json")).exists(), ticker + " null recipe leaked")
    return old


def validate_registry(root, manifest, registry, *, proof_reader=None):
    require(callable(proof_reader), "verified proof reader missing")
    parent = proof_reader(root, "approved-parent-registry.json", PARENT_REGISTRY_SHA)
    require(registry.get("schema_version") == parent.get("schema_version") and len(registry.get("entries", [])) == 550, "registry550 schema")
    require(all(row in registry["entries"] for row in parent["entries"]), "old540 registry records changed")
    actual = {(entry["ticker"], entry["cik"], entry["batch"], entry["availability_type"]) for entry in registry["entries"]}
    wanted = {(entry["ticker"], entry["cik"], entry["batch"], entry["availability_type"]) for entry in manifest["entries"]}
    require(len(actual) == 550 and actual == wanted, "registry identities/statuses")
