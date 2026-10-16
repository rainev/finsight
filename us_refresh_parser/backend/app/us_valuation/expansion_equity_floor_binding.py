"""Explicit private SITE output-floor overlay; never alters economic inputs."""
from copy import deepcopy

from .calculation_recipe import evaluate_recipe, recipe_hash
from .expansion_policy_binding import content_hash, require

VERSION = "US-EXPANSION-PRIVATE-SITE-FLOOR-1"
RECIPE_VERSION = "US-EXPANSION-B01-SITE-PRIVATE-FLOOR-1"
FLOOR_WARNING = "Explicitly approved private bear-only zero floor; raw negative residual retained. This is an output convention, not a market-price forecast or source-gate clearance."


def bind_floor(policy, prior_recipe, prior_result, approval, *, authority):
    require(approval["schema_version"] == "US-SITE-PRIVATE-FLOOR-APPROVAL-1", "invalid floor approval")
    require(approval["ticker"] == "SITE" and approval["cutoff"] == "2026-10-03"
            and approval["scenario"] == "bear" and type(approval["floor_value_USD_per_share"]) in {int,float}
            and approval["floor_value_USD_per_share"] == 0
            and approval["floor_authorized"] is True, "floor scope changed")
    require(all(approval[key] is False for key in ("catalog_admission_authorized", "activation_authorized", "publication_authorized", "live_refresh_promotion_authorized")), "wider authority forbidden")
    require(approval["preserve_raw_negative_residual"] is True and approval["preserve_low_claim_warnings"] is True
            and approval["leave_AIT_unchanged"] is True and approval["keep_other_eight_held"] is True, "preservation authority missing")
    require(approval["pins"] == authority, "prior authority pins changed")
    require(policy["ticker"] == prior_recipe["ticker"] == prior_result["ticker"] == "SITE", "only SITE floor authorized")
    require(policy["valuation_date"] == policy["evidence_cutoff"] == prior_recipe["evidence_cutoff"] == "2026-10-03", "cutoff changed")
    require(policy["policy_ready_for_private_low_analysis"] is True and policy["public_or_source_complete_release_ready"] is False
            and policy["remaining_exact_source_gates"] == ["acquisition_perimeter"], "claim scope changed")
    require(prior_recipe["private_only"] is True and prior_recipe["reliability"] == prior_result["reliability"] == "Low", "prior private reliability changed")
    require(not any("equity_floor" in spec for spec in prior_recipe["scenarios"].values()), "floor reapplication forbidden")
    require(prior_result["raw_scenario_range"]["low"] < 0 and prior_result["limited_liability_floor_applied"] is False, "negative prior diagnostic missing")
    # Sealed files use catalog.canonical_json_bytes (pretty JSON + newline).
    # This is distinct from calculation_recipe.recipe_hash (compact JSON).
    require(content_hash(policy) == authority["policy_sha256"]
            and content_hash(prior_recipe) == authority["prior_recipe_sha256"]
            and content_hash(prior_result) == authority["prior_result_sha256"], "supplied records differ from pinned authority")
    recipe = deepcopy(prior_recipe)
    recipe["recipe_version"] = RECIPE_VERSION
    recipe["scenarios"]["bear"]["equity_floor"] = "limited_liability"
    # Retain every claim/denominator limitation; supersede only the old no-approval statement.
    historical_warning = recipe["warnings"][-1]
    require(historical_warning == "Raw negative residual equity, if produced, is a private diagnostic; no limited-liability floor is approved.", "prior warning contract changed")
    recipe["warnings"][-1] = FLOOR_WARNING
    recipe["floor_approval"] = {"classification":"FINSIGHT_ASSUMPTION_output_convention", "scenario":"bear",
        "value_USD_per_share":0., "raw_negative_retained":True, "approval_canonical_sha256":content_hash(approval), **authority}
    bound = {"schema_version":VERSION,"ticker":"SITE","cutoff":"2026-10-03","private_only":True,
        "reliability":"Low","recipe":recipe,"recipe_sha256":recipe_hash(recipe),
        "source_policy_sha256":authority["policy_sha256"],"approval_canonical_sha256":content_hash(approval),
        "prior_raw_scenario_range":deepcopy(prior_result["raw_scenario_range"]),
        "superseded_historical_no_floor_warning":historical_warning,
        "remaining_exact_source_gates":deepcopy(policy["remaining_exact_source_gates"]),
        "exact_claim_reconciliation":False,"public_or_source_complete_release_ready":False,
        "catalog_admission_authorized":False,"activation_authorized":False,"publication_authorized":False,
        "live_refresh_promotion_authorized":False,"changes_active_catalog":False,"economic_calibration":"unvalidated"}
    bound["integrity_sha256"] = content_hash(bound)
    return bound


def validate_binding(bound, policy, prior_recipe, prior_result, approval, *, authority):
    expected = bind_floor(policy,prior_recipe,prior_result,approval,authority=authority)
    require(bound == expected, "floor binding does not reconstruct from approved frozen authority")
    return bound


def consume_binding(bound, policy, prior_recipe, prior_result, approval, *, authority):
    validate_binding(bound,policy,prior_recipe,prior_result,approval,authority=authority)
    checked = evaluate_recipe(bound["recipe"])
    raw = {label:checked["scenarios"][name]["raw_value"] for label,name in (("low","bear"),("base","base"),("high","bull"))}
    require(raw == prior_result["raw_scenario_range"], "underlying residual changed")
    require(checked["range"] == {**raw,"low":0.}, "floor affected more than bear output")
    for name in ("bear","base","bull"):
        require(checked["scenarios"][name]["trace"] == prior_result["scenarios"][name]["trace"], "raw economic trace changed")
    return {"schema_version":VERSION,"ticker":"SITE","currency":"USD","unit":"per_point_common_share",
        "cutoff":"2026-10-03","private_only":True,"reliability":"Low","publication_state":"not_authorized",
        "scenario_range":checked["range"],"raw_scenario_range":raw,"scenarios":checked["scenarios"],
        "raw_value_decimal_strings":deepcopy(prior_result["raw_value_decimal_strings"]),
        "historical_raw_diagnostic_warnings":deepcopy(prior_result["warnings"]),
        "recipe_sha256":checked["recipe_hash"],"binding_integrity_sha256":bound["integrity_sha256"],
        "warnings":deepcopy(bound["recipe"]["warnings"]),"bear_output_type":"explicit_private_zero_floor",
        "raw_bear_status":"negative_residual_private_diagnostic_retained",
        "floor_applied_to":["bear"],"limited_liability_floor_applied":True,
        "numeric_range_gate":"nonnegative_ordered_range_verified_not_release_approval",
        "remaining_exact_source_gates":bound["remaining_exact_source_gates"],"exact_claim_reconciliation":False,
        "public_or_source_complete_release_ready":False,"catalog_admission_authorized":False,
        "activation_authorized":False,"publication_authorized":False,"live_refresh_promotion_authorized":False,
        "changes_active_catalog":False,"economic_calibration":"unvalidated"}
