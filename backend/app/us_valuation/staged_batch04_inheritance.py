"""Closed Batch04 staged public-preparation authority; no admission or activation."""

import hashlib
import json
from pathlib import Path


PARENT_SHA = "368db44036f2f340b116faa3d8c79d03957efaf52a5d51acfa3f381ee8c7ff24"
PARENT_VERSION = "US-ADMITTED-B03-530-87c22806696587f23d529649"
PARENT_REGISTRY_SHA = "5121bf6e36704b7f0ab81268e50ec1299de5fe724ab09f427598bcc39e4426cb"
APPROVAL_SHA = "f36ec0cbf86a7af6d273a96be98262cf0f939f788d2f63d5510748fae9eaa02d"
PROPOSAL_SHA = "6a3df0fd703f77160eb1162301948dcdf80c21fb27c42aa5e0a1a3dbbd943899"
RANGES_SHA = "4d2f4a23f13d0a47d9c1292a222e7c070628cc8176dd1ad85f71c62b22b73502"
SCHEMA = "US-B04-APPROVED-PARENT-INHERITANCE-1"
REVIEW_SCHEMA = "US-B04-READ-ONLY-STAGED-REVIEW-1"
CUTOFF = "2026-10-06"

IDENTITIES = {
    "ETD": "0000896156", "LZB": "0000057131", "BSET": "0000010329",
    "FLXS": "0000037472", "PLOW": "0001287213", "PATK": "0000076605",
    "UFPT": "0000914156", "IBP": "0001580905", "NPK": "0000080172",
    "MTW": "0000061986",
}
TARGETS = {"ETD", "LZB", "BSET", "PLOW", "PATK", "UFPT", "IBP", "NPK"}
NULLS = {"FLXS", "MTW"}
ROOT_FILES = {
    "manifest.json", "refresh-policies.json", "approved-base-manifest.json",
    "approved-parent-manifest.json", "approved-parent-registry.json",
    "approved-parent-policies.json", "public-scope-authorization.json",
    "bset-source-correction.json",
}
ECONOMIC_HASHES = {
    "ETD": "2ed0970d702b75205812c21448a9a8303011273f0de286dfc92ac24c3f79cb5e",
    "LZB": "fc1a58aa7f6c444062c4c061d56d175ce0b63bf70ca06e3b5e5bd162ac2fb683",
    "BSET": "9a2c5b2d6c68bc61988f493fc45845ab441faeba3c3d82f7276ebb89d610c93b",
    "PLOW": "e8dc6d291988b0000ae82d3a7e5c0d7a7be4bb1fba469edab51afe3b0a9da54e",
    "PATK": "a7e46b3aca970b52576512c47361a2cb1ba786b7663bf4a8edbf1e57f6ec53f5",
    "UFPT": "1685accb0392cb5b5db0aac3048a667c08894c78bd19126b018fcaa5d520e8e9",
    "IBP": "36d84b474084d836af5a50a7b95f0f8b230430ead429da9ee19511d747637b64",
    "NPK": "896d7c0cee683dbe84b6c8e0473683c83d73a6a1d324f4ad11f237f6ad0f4575",
}
SOURCE_HEADER_SHA256 = {
    "ETD": "cb612da181283e2ba2bc16085dfcd07c12111950136217f80630c4940108c579",
    "LZB": "9b3e832cc9d4dc2153bcbfc6924c9ecef0f7b3d33e18ef6e7910ffcd58f97eb9",
    "BSET": "87919c4886498e22808707b771f233dc6be9e66e1c505eadd1bc804bf43b2fcf",
    "FLXS": "129e2e47ef6f8dbf59651f8bdf1e6eb12563389ac2a7d20a43d6c99474d6e0e3",
    "PLOW": "86ea2b0c608f6c1039f0b5adaa331aa0006d26bda65440d6be3daadaca00648f",
    "PATK": "6c5a0c654ee312a1d5882534fa6a68fcfb8e9bb822204f28a84b624ae1d830c7",
    "UFPT": "274e8ae5b1489a5310a3b34eb1e7e16a2b8cda53c232bb6c036c7c824d7ad176",
    "IBP": "2cb0b77eeedf1846ca860256f40dbf6e2b426da6974569115bb75d77006193b9",
    "NPK": "b8e2c577dd542bce5b3e00af9765ea100a24016f57117a6c3331c6050ac70972",
    "MTW": "83a8410f4e9395814ff5b75b7085f57fc2cd03faa58bc7882221ad20bb3330c8",
}
TARGET_CONFIDENCE = {"ETD": 0.0, "LZB": 0.0, "BSET": 0.0, "PLOW": 0.60, "PATK": 0.0, "UFPT": 0.65, "IBP": 0.0, "NPK": 0.60}
NATIVE_ARCHETYPES = {"PLOW": "b04_common_ri__capital_goods_machinery", "NPK": "b04_common_ri__capital_goods_machinery", "UFPT": "b04_common_ri__medical_devices_instruments"}
MANUAL_ARCHETYPES = {"ETD": "b04_common_ri__consumer_operating", "LZB": "b04_common_ri__consumer_operating", "BSET": "b04_common_ri__consumer_operating", "PATK": "b04_common_ri__diversified_industrials", "IBP": "b04_common_ri__diversified_industrials"}
MANUAL_REASON = "Unrated manual issuer mapping: classification_confidence 0.0 is a conservative guard sentinel, not measured confidence or calibration."
PUBLIC_POLICY_VERSION = "US-B04-PUBLIC-COMMON-RI-1"
BSET_PROOF_SCHEMA = "US-B04-BSET-PUBLIC-SOURCE-CORRECTION-1"
# Authenticated by the frozen public-staged BSET source-correction proof.
BSET_PROOF_SHA256 = "279b8f74c1edf67ae4f39fd1aa9b00bd9862cc45074693a1f716d8a7e68f2318"
BSET_SOURCE_PROOF_SHA = BSET_PROOF_SHA256
AUTHORITY_FIELDS = {"schema_version", "read_only", "manifest_sha256", "catalog_version", "registry_sha256", "admission", "activation", "publication", "save", "automatic_new_source_revaluation"}


def require(value, why):
    if not value:
        raise ValueError("Batch04 staged review rejected: " + why)


def _canonical_sha(value):
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def _rows(manifest):
    return {entry["ticker"]: (entry["cik"], entry["batch"], entry["availability_type"], entry["artifact_sha256"]) for entry in manifest["entries"]}


def _target_classification(artifact, ticker):
    issuer = artifact.get("issuer", {})
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
    require(artifact.get("public_assumptions", {}).get("forecast_policy_version") == PUBLIC_POLICY_VERSION, ticker + " public policy version changed")
    require(artifact.get("reliability", {}).get("label") == "Low", ticker + " reliability is not Low")
    _target_classification(artifact, ticker)
    require(artifact.get("review", {}).get("publication_state") == "review_required", ticker + " review state changed")
    require(set(artifact.get("review", {}).get("warnings", [])) >= set(artifact.get("reliability", {}).get("warnings", [])), ticker + " warning contract changed")
    ranges[ticker] = {key: artifact["scenario_range"][key] for key in ("low", "base", "high")}
    return artifact


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


def validate_bset_proof(proof_reader, root, *, expected_sha256=None):
    """Authenticate the later BSET source correction without changing values."""
    expected = BSET_PROOF_SHA256 if expected_sha256 is None else expected_sha256
    require(isinstance(expected, str) and len(expected) == 64 and set(expected) != {"0"}, "BSET source proof hash anchor is pending")
    proof = proof_reader(root, "bset-source-correction.json", expected)
    require(proof.get("schema_version") == BSET_PROOF_SCHEMA, "BSET source proof schema changed")
    require(proof.get("ticker") == "BSET" and str(proof.get("cik")).zfill(10) == IDENTITIES["BSET"], "BSET source proof identity changed")
    require(_proof_value(proof, "source_accession", "primary_accession", "primary.source_accession", "document.accession") == "0001437749-23-001642", "BSET primary source accession changed")
    continuing = proof.get("FY2022_continuing_income", {})
    discontinued = proof.get("FY2022_discontinued_income", {})
    total = proof.get("FY2022_total_income", {})
    require(continuing.get("period_start") == "2021-11-28" and continuing.get("period_end") == "2022-11-26", "BSET continuing-income period changed")
    require(continuing.get("value") == 25360000 and discontinued.get("value") == 39985000 and total.get("value") == 65345000, "BSET income identity changed")
    require(discontinued.get("period_start") == continuing.get("period_start") and discontinued.get("period_end") == continuing.get("period_end"), "BSET discontinued period changed")
    books = proof.get("corrected_annual_parent_books", [])
    corrected_book = next((row for row in books if row.get("opening", {}).get("period_end") == "2021-11-27" and row.get("closing", {}).get("period_end") == "2022-11-26"), {})
    require(corrected_book.get("opening", {}).get("value") == 162732000 and corrected_book.get("closing", {}).get("value") == 195609000, "BSET book values changed")
    require(proof.get("corrected_opening_book_date") == "2021-11-27" and proof.get("corrected_closing_book_date") == "2022-11-26", "BSET book dates changed")
    require(proof.get("corrected_median_period") == "2025-11-29" and proof.get("corrected_median_ROE") == 0.03669901393960907, "BSET selected median changed")
    require(proof.get("common_book_and_balance_share_arguments_unchanged") is True and proof.get("private_ledger_recipe_artifact_unchanged") is True, "BSET selected model/value preservation is missing")
    require(proof.get("future_payout_ratio_unchanged") == 0.4 and proof.get("no_new_valuation_or_normalization_or_floor") is True, "BSET economic arguments changed")
    require(proof.get("accepted_recipe_economic_sha256") == ECONOMIC_HASHES["BSET"], "BSET accepted economic arguments changed")
    document_sha = _proof_value(proof, "primary_document_sha256", "document_sha256", "source_document_sha256", "document.sha256")
    require(isinstance(document_sha, str) and len(document_sha) == 64, "BSET authenticated document hash is missing")
    return proof


def _allowed_catalog_namespace(version):
    return str(version).startswith("US-STAGED-EXPANSION-B04-540-") or str(version).startswith("US-REFRESH-540-2026-10-06-")


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
    require(parent.get("catalog_version") == PARENT_VERSION and len(parent.get("entries", [])) == 530, "authentic530 parent")
    approval = proof_reader(root, "public-scope-authorization.json", APPROVAL_SHA)
    require(approval.get("schema_version") == "US-B04-PUBLIC-STAGED-PREPARATION-AUTHORIZATION-1" and approval.get("policy_scope_approved") is True and approval.get("staged_candidate_only") is True, "approved preparation only")
    require(set(approval.get("public_preparation_targets", [])) == TARGETS and set(approval.get("public_unavailable_additions", [])) == NULLS, "approved8/2 scope")
    require(approval.get("evidence_cutoff") == CUTOFF and approval.get("approved_proposal_sha256") == PROPOSAL_SHA and approval.get("BSET_source_correction_and_unchanged_value_gate") is True, "cutoff/proposal/BSET scope")
    for key in ("admission", "activation", "publication", "automatic_new_source_revaluation", "new_recovery", "new_source_capture", "next_batch", "valuation_recalculation", "live_runtime_promotion", "new_live_refresh_job", "push", "cloud_deployment"):
        require(approval.get(key) is False, "broader authority: " + key)

    old = _rows(parent)
    current = _rows(manifest)
    require(len(manifest["entries"]) == len(current) == 540 and set(current) == set(old) | set(IDENTITIES), "exact540 identities")
    require(all(current[t] == row for t, row in old.items()), "old530 identity/status/artifact drift")
    require(all(current[t][0] == cik and current[t][1] == 54 and current[t][2] == ("conditional_estimate" if t in TARGETS else "not_available") for t, cik in IDENTITIES.items()), "new8/2 identity/status drift")
    index = manifest.get("private_recipe_sha256")
    require(isinstance(index, dict) and set(index) == set(parent["private_recipe_sha256"]) | TARGETS, "public recipe membership")
    require(all(index.get(t) == digest for t, digest in parent["private_recipe_sha256"].items()), "old530 recipe drift")
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
            if ticker == "BSET":
                validate_bset_proof(proof_reader, root)
        else:
            artifact = proof_reader(root, "artifacts/" + ticker + ".json", row[3])
            require(artifact.get("availability_type") == "not_available" and "private_review_only" not in artifact, ticker + " public-null privacy")
            require(_canonical_sha(artifact.get("source_financial_statement", {})) == SOURCE_HEADER_SHA256[ticker], ticker + " frozen source header changed")
            require(all(artifact.get("scenario_range", {}).get(key) is None for key in ("low", "base", "high")), ticker + " public-null range")
            require(artifact.get("review", {}).get("publication_state") == "withheld" and artifact.get("confidence", {}).get("label") is None, ticker + " public-null state")
            require(artifact.get("valuation_date") == CUTOFF and artifact.get("assumption_date") == CUTOFF, ticker + " public-null dates")

    require(_canonical_sha(ranges) == RANGES_SHA, "accepted eight-target range anchor")
    if deep:
        from .artifacts import sanitize_public_artifact
        from .calculation_recipe import evaluate_recipe
        require({path.name for path in Path(root).iterdir()} == ROOT_FILES | {"artifacts", "recipes"}, "exact staged root allowlist; no historical release grants")
        expected = {"approved-base-manifest.json": PARENT_SHA, "approved-parent-manifest.json": PARENT_SHA, "approved-parent-registry.json": PARENT_REGISTRY_SHA, "approved-parent-policies.json": parent["private_refresh_policy_sha256"], "public-scope-authorization.json": APPROVAL_SHA}
        require(manifest.get("preserved_prior_estimate_sha256") == expected | {"bset-source-correction.json": BSET_PROOF_SHA256}, "exact preparation proof index")
        for name, digest in expected.items():
            proof_reader(root, name, digest)
        if BSET_PROOF_SHA256 != "0" * 64:
            validate_bset_proof(proof_reader, root)
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
    require(registry.get("schema_version") == parent.get("schema_version") and len(registry.get("entries", [])) == 540, "registry540 schema")
    require(all(row in registry["entries"] for row in parent["entries"]), "old530 registry records changed")
    actual = {(entry["ticker"], entry["cik"], entry["batch"], entry["availability_type"]) for entry in registry["entries"]}
    wanted = {(entry["ticker"], entry["cik"], entry["batch"], entry["availability_type"]) for entry in manifest["entries"]}
    require(len(actual) == 540 and actual == wanted, "registry identities/statuses")
