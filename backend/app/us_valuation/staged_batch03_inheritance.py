"""Closed Batch03 staged public-preparation authority; no admission or activation."""

import hashlib
import json
from pathlib import Path


PARENT_SHA = "a0c1fe6caba7c0d9eb0880494e8581c657f39bd52ebdf53cf28a431673a7affe"
PARENT_VERSION = "US-ADMITTED-B02-520-a42d5320e9a7d88a9269522f"
PARENT_REGISTRY_SHA = "9a5ec15115bdaa627990da7d430d7d504f6106c13d416bd36f19ebba19d6b3b6"
APPROVAL_SHA = "0d92c48993cb278e0a1f41becb00d2abbc4cea78874caf4f823db182f015456c"
PROPOSAL_SHA = "42fc85e224c77e607eae4daf909a6280019aa4901145839ce985e6e61b644dff"
RANGES_SHA = "d6684c624688e82783e9563198abc2ac5b77db7ec8efede7c36ea15673093aae"
SCHEMA = "US-B03-APPROVED-PARENT-INHERITANCE-1"
REVIEW_SCHEMA = "US-B03-READ-ONLY-STAGED-REVIEW-1"
CUTOFF = "2026-10-06"

IDENTITIES = {
    "IOSP": "0001054905",
    "ALG": "0000897077",
    "AIN": "0000819793",
    "MTRN": "0001104657",
    "DORM": "0000868780",
    "ENS": "0001289308",
    "KWR": "0000081362",
    "IPAR": "0000822663",
    "UFPI": "0000912767",
    "SMID": "0000924719",
}
TARGETS = {"IOSP", "MTRN", "IPAR", "UFPI", "SMID"}
NULLS = {"ALG", "AIN", "DORM", "ENS", "KWR"}
ROOT_FILES = {
    "manifest.json",
    "refresh-policies.json",
    "approved-base-manifest.json",
    "approved-parent-manifest.json",
    "approved-parent-registry.json",
    "approved-parent-policies.json",
    "public-scope-authorization.json",
}
ECONOMIC_HASHES = {
    "IOSP": "e4859ac8d91ea0dd0fcbda78f50c9af1daca3d9a7e5762548dd15c15f9ac4649",
    "IPAR": "fb3792331e56a71f8dbee63ee830f98fdc31e83f79e46508e80fb8392647866c",
    "MTRN": "ff8e63e1d0769fe685d4c47befd8aed47bdcba702b9ecb2a73406d380db1dfc5",
    "SMID": "dbd782c8c13112d8983848a0945dad3332c903beb4149cef39f329716dd10b56",
    "UFPI": "e8f9dd1658bbbae96ac018e36299809650f9d5db752b296073c0a87fe598e604",
}
SOURCE_HEADER_SHA256 = {
    "IOSP": "19edc34c48fb33f1bd9d4080ac4c644e47cf1142ae56ae9004139aba93f2e8fe",
    "ALG": "5f596f3d34bc7d30b52571fdd0c94c593049507c1d8fbc1b296d3e04d6ae95ca",
    "AIN": "c5c92b20d5df5f679994cb7cdbe06c697eaf735b02d16a244f59494a941ee818",
    "MTRN": "8622af787a8b1f9abb53dc8f641d9a259cf061d9199dfecd4ee598714b2af32d",
    "DORM": "8dd1bf60db665edeb5d97c984e3a491056c96293e48c8046638f80cdce44edac",
    "ENS": "3d432b9e76e444adc7df68a429bcb58112e6c18633aa0c12e194503d18bdb25c",
    "KWR": "f151599244b2badd900964ee72dff9caaebc47e3c2305f12206469bf56b17032",
    "IPAR": "f14ca77c62340ffea171c1d3e0c03f9809920087992c6a5dbf3e46f8ee74d910",
    "UFPI": "6119d83129247114442b04e72fb461040fbbb1a6099366a868f03e0f8a3e1b24",
    "SMID": "67a87f6af76881794e96e49478600b41485bb8415bbb9aaeb9210886518455ae",
}
TARGET_CONFIDENCE = {"IOSP": 0.55, "MTRN": 0.60, "IPAR": 0.55, "UFPI": 0.0, "SMID": 0.0}
NATIVE_ARCHETYPES = {
    "IOSP": "b03_common_ri__specialty_chemicals",
    "MTRN": "b03_common_ri__capital_goods_machinery",
    "IPAR": "b03_common_ri__specialty_chemicals",
}
MANUAL_ARCHETYPE = "b03_common_ri__diversified_industrials"
MANUAL_REASON = "Unrated manual issuer mapping: classification_confidence 0.0 is a conservative guard sentinel, not measured confidence or calibration."
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


def require(value, why):
    if not value:
        raise ValueError("Batch03 staged review rejected: " + why)


def _canonical_sha(value):
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def _rows(manifest):
    return {
        entry["ticker"]: (
            entry["cik"],
            entry["batch"],
            entry["availability_type"],
            entry["artifact_sha256"],
        )
        for entry in manifest["entries"]
    }


def _target_classification(artifact, ticker):
    issuer = artifact.get("issuer", {})
    require(issuer.get("override_applied") is True, ticker + " classification override is not explicit")
    require(issuer.get("classification_confidence") == TARGET_CONFIDENCE[ticker], ticker + " classification confidence changed")
    require(issuer.get("classification_reason"), ticker + " classification reason is missing")
    reason = str(issuer.get("classification_reason", ""))
    require("reported parent-common GAAP book/earnings residual-income override" in reason, ticker + " common-RI override reason is missing")
    if ticker in NATIVE_ARCHETYPES:
        require(issuer.get("primary_archetype") == NATIVE_ARCHETYPES[ticker], ticker + " native archetype changed")
        require("Native SEC-SIC routing score retained" in reason, ticker + " native routing provenance is missing")
    else:
        require(issuer.get("primary_archetype") == MANUAL_ARCHETYPE, ticker + " manual diversified-industrials route changed")
        require(MANUAL_REASON in reason, ticker + " manual sentinel meaning is missing")


def _validate_public_artifact(proof_reader, root, ticker, row, ranges):
    artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
    issuer = artifact.get("issuer", {})
    require(issuer.get("ticker") == ticker and str(issuer.get("cik")).zfill(10) == IDENTITIES[ticker], ticker + " public identity changed")
    require("private_review_only" not in artifact and "source_ledger" not in artifact, ticker + " private payload leaked")
    require(_canonical_sha(artifact.get("source_financial_statement", {})) == SOURCE_HEADER_SHA256[ticker], ticker + " frozen source header changed")
    require(artifact.get("valuation_date") == CUTOFF and artifact.get("assumption_date") == CUTOFF, ticker + " public dates changed")
    require(artifact.get("availability_type") == "conditional_estimate", ticker + " target availability changed")
    require(artifact.get("primary_valuation_method") == "residual_income", ticker + " public model changed")
    require(artifact.get("model_policy", {}).get("primary") == "residual_income", ticker + " public model policy changed")
    require(artifact.get("public_assumptions", {}).get("forecast_policy_version") == "US-B03-PUBLIC-COMMON-RI-1", ticker + " public policy version changed")
    reliability = artifact.get("reliability", {})
    require(reliability.get("label") == "Low", ticker + " reliability is not Low")
    if "source_cap" in reliability:
        require(reliability.get("source_cap") == "Low" and reliability.get("model_cap") == "Low", ticker + " reliability caps changed")
    _target_classification(artifact, ticker)
    require(artifact.get("review", {}).get("publication_state") == "review_required", ticker + " review state changed")
    require(set(artifact.get("review", {}).get("warnings", [])) >= set(artifact.get("reliability", {}).get("warnings", [])), ticker + " warning contract changed")
    warning_text = " ".join(str(value) for value in artifact.get("review", {}).get("warnings", [])).lower()
    if ticker == "MTRN":
        require("371" in warning_text and "common eps" in warning_text and "no365-day annualization" in warning_text, "MTRN period/owner warning gate missing")
    if ticker == "SMID":
        require("future40% payout" in warning_text and "rental/royalty" in warning_text and "nasdaq" in warning_text, "SMID payout/operating/filing warning gate missing")
    ranges[ticker] = {key: artifact["scenario_range"][key] for key in ("low", "base", "high")}
    return artifact


def validate(root, manifest, *, deep=False, proof_reader=None):
    require(callable(proof_reader), "verified proof reader missing")
    proof = manifest.get("approved_base_inheritance")
    require(isinstance(proof, dict) and set(proof) == {"schema_version", "parent_manifest_sha256", "parent_catalog_version", "scope_approval_sha256", "proposal_sha256"}, "inheritance exact schema")
    require(proof == {"schema_version": SCHEMA, "parent_manifest_sha256": PARENT_SHA, "parent_catalog_version": PARENT_VERSION, "scope_approval_sha256": APPROVAL_SHA, "proposal_sha256": PROPOSAL_SHA}, "parent/scope pins")
    require(manifest.get("approved_base_manifest_sha256") == PARENT_SHA and manifest.get("release_scope_approval_sha256") == APPROVAL_SHA, "consistent approved base/scope metadata")
    require(str(manifest.get("catalog_version", "")).startswith("US-STAGED-EXPANSION-B03-530-"), "approved staged version namespace")
    require(manifest.get("base_catalog_version") == PARENT_VERSION and manifest.get("base_manifest_sha256") == PARENT_SHA, "consistent staged parent")
    require(manifest.get("staged_release_only") is True and manifest.get("catalog_kind") == "unadmitted_public_contract_candidate", "staged scope")
    require(not manifest.get("private_integration_only") and "private_review" not in manifest, "no private projection privilege")
    require("local_admission" not in manifest and "supported_refresh_integration" not in manifest, "no inherited release grants")
    require(all(manifest.get(key) is False for key in ("admission", "activation", "publication")), "release remains unauthorized")
    require(manifest.get("staged_read_only_review_ready") is True, "read-only review marker")

    parent = proof_reader(root, "approved-parent-manifest.json", PARENT_SHA)
    require(parent.get("catalog_version") == PARENT_VERSION and len(parent.get("entries", [])) == 520, "authentic520 parent")
    approval = proof_reader(root, "public-scope-authorization.json", APPROVAL_SHA)
    require(approval.get("schema_version") == "US-B03-PUBLIC-STAGED-PREPARATION-AUTHORIZATION-1" and approval.get("policy_scope_approved") is True and approval.get("staged_candidate_only") is True, "approved preparation only")
    require(set(approval.get("public_preparation_targets", [])) == TARGETS and set(approval.get("public_unavailable_additions", [])) == NULLS, "approved5/5 scope")
    require(approval.get("evidence_cutoff") == CUTOFF and approval.get("approved_proposal_sha256") == PROPOSAL_SHA, "cutoff/proposal scope")
    for key in ("admission", "activation", "publication", "automatic_new_source_revaluation", "new_recovery", "new_source_capture", "next_batch", "valuation_recalculation", "live_runtime_promotion", "new_live_refresh_job", "push", "cloud_deployment"):
        require(approval.get(key) is False, "broader authority: " + key)

    old = _rows(parent)
    current = _rows(manifest)
    require(len(manifest["entries"]) == len(current) == 530 and set(current) == set(old) | set(IDENTITIES), "exact530 identities")
    require(all(current[t] == row for t, row in old.items()), "old520 identity/status/artifact drift")
    require(all(current[t][0] == cik and current[t][1] == 53 and current[t][2] == ("conditional_estimate" if t in TARGETS else "not_available") for t, cik in IDENTITIES.items()), "new5/5 identity/status drift")
    index = manifest.get("private_recipe_sha256")
    require(isinstance(index, dict) and set(index) == set(parent["private_recipe_sha256"]) | TARGETS, "public recipe membership")
    require(all(index.get(t) == digest for t, digest in parent["private_recipe_sha256"].items()), "old520 recipe drift")
    require(not (set(index) & NULLS), "public-null recipes absent")

    policies = proof_reader(root, "refresh-policies.json", manifest["private_refresh_policy_sha256"])
    parent_policies = proof_reader(root, "approved-parent-policies.json", parent["private_refresh_policy_sha256"])
    require(set(policies) == set(parent_policies) | set(IDENTITIES) and all(policies[t] == p for t, p in parent_policies.items()), "old policy drift")
    for ticker in IDENTITIES:
        policy = policies[ticker]
        require(policy.get("schema_version") == "FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1" and policy.get("ticker") == ticker and policy.get("cik") == IDENTITIES[ticker] and policy.get("private_only") is False and policy.get("staged_public_candidate_authorized") is True and policy.get("new_filing_hold_before_capture") is True and policy.get("direct_binding_rejected") is True and policy.get("source_epoch") == CUTOFF, ticker + " new-filing hold contract")
        for key in ("public_release_authorized", "auto_revaluation", "admission_authorized", "activation_authorized", "publication_authorized"):
            require(policy.get(key) is False, ticker + " release authority")

    ranges = {}
    for ticker in IDENTITIES:
        row = current[ticker]
        if ticker in TARGETS:
            _validate_public_artifact(proof_reader, root, ticker, row, ranges)
        else:
            artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
            require(artifact.get("availability_type") == "not_available" and "private_review_only" not in artifact, ticker + " public-null privacy")
            require(_canonical_sha(artifact.get("source_financial_statement", {})) == SOURCE_HEADER_SHA256[ticker], ticker + " frozen source header changed")
            require(all(artifact.get("scenario_range", {}).get(key) is None for key in ("low", "base", "high")), ticker + " public-null range")
            require(artifact.get("review", {}).get("publication_state") == "withheld" and artifact.get("confidence", {}).get("label") is None, ticker + " public-null state")
            if ticker == "KWR":
                require(artifact.get("valuation_date") == "2026-06-30" and artifact.get("assumption_date") == CUTOFF, "KWR dated null scope changed")

    require(_canonical_sha(ranges) == RANGES_SHA, "accepted five-target range anchor")
    if deep:
        from .artifacts import sanitize_public_artifact
        from .calculation_recipe import evaluate_recipe
        require({path.name for path in Path(root).iterdir()} == ROOT_FILES | {"artifacts", "recipes"}, "exact staged root allowlist; no historical release grants")
        expected = {"approved-base-manifest.json": PARENT_SHA, "approved-parent-manifest.json": PARENT_SHA, "approved-parent-registry.json": PARENT_REGISTRY_SHA, "approved-parent-policies.json": parent["private_refresh_policy_sha256"], "public-scope-authorization.json": APPROVAL_SHA}
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
                    if exc.name != __package__ + '.latest_calculator':
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
    require(registry.get("schema_version") == parent.get("schema_version") and len(registry.get("entries", [])) == 530, "registry530 schema")
    require(all(row in registry["entries"] for row in parent["entries"]), "old520 registry records changed")
    actual = {(entry["ticker"], entry["cik"], entry["batch"], entry["availability_type"]) for entry in registry["entries"]}
    wanted = {(entry["ticker"], entry["cik"], entry["batch"], entry["availability_type"]) for entry in manifest["entries"]}
    require(len(actual) == 530 and actual == wanted, "registry identities/statuses")
