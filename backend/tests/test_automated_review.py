from __future__ import annotations

from copy import deepcopy
import json
import math

import pytest

from app.us_valuation.automated_review import REVIEW_VERSION, assess_artifact


DTO_KEYS = {
    "review_version",
    "decision",
    "publication_state",
    "evidence_status",
    "blocking_reasons",
    "repair_actions",
    "warnings",
}


def clean_artifact() -> dict:
    return {
        "schema_version": "US-PUBLIC-VALUATION-1.0",
        "valuation_date": "2026-08-01",
        "issuer": {
            "ticker": "AAPL",
            "classification_confidence": 0.98,
        },
        "source_financial_statement": {
            "form": "10-Q",
            "period_end": "2026-03-28",
            "filed_date": "2026-05-01",
            "accession": "0000320193-26-000013",
            "url": (
                "https://www.sec.gov/Archives/edgar/data/320193/"
                "000032019326000013/aapl-20260328.htm"
            ),
        },
        "model_policy": {"primary": "fcff_dcf", "supporting": ["epv"]},
        "review": {
            "publication_state": "pass",
            "errors": [],
            "warnings": [],
        },
        "models": {
            "fcff_dcf": {
                "publication_state": "pass",
                "intrinsic_value_per_share": 100.0,
            },
            "epv": {
                "publication_state": "pass",
                "intrinsic_value_per_share": 95.0,
            },
        },
        "scenarios": {
            "low": {
                "fcff_dcf": {
                    "publication_state": "pass",
                    "intrinsic_value_per_share": 90.0,
                }
            },
            "base": {
                "fcff_dcf": {
                    "publication_state": "pass",
                    "intrinsic_value_per_share": 100.0,
                }
            },
            "high": {
                "fcff_dcf": {
                    "publication_state": "pass",
                    "intrinsic_value_per_share": 110.0,
                }
            },
        },
    }


def test_clean_artifact_is_approved_with_exact_versioned_dto() -> None:
    artifact = clean_artifact()
    before = deepcopy(artifact)

    result = assess_artifact(artifact)

    assert artifact == before
    assert set(result) == DTO_KEYS
    assert result == {
        "review_version": REVIEW_VERSION,
        "decision": "approved",
        "publication_state": "pass",
        "evidence_status": "complete",
        "blocking_reasons": [],
        "repair_actions": [],
        "warnings": [],
    }


def test_unknown_model_state_is_blocked_deterministically() -> None:
    artifact = clean_artifact()
    artifact["models"]["fcff_dcf"]["publication_state"] = "unknown"

    first = assess_artifact(artifact)
    second = assess_artifact(deepcopy(artifact))

    assert first == second
    assert first["decision"] == "blocked"
    assert first["publication_state"] == "withheld"
    assert first["blocking_reasons"] == ["invalid_model_state:fcff_dcf"]


def test_weak_sec_provenance_is_blocked_with_repair_action() -> None:
    artifact = clean_artifact()
    artifact["source_financial_statement"].update(
        {
            "filed_date": None,
            "url": (
                "https://www.sec.gov/cgi-bin/browse-edgar?"
                "action=getcompany&CIK=320193"
            ),
        }
    )

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["evidence_status"] == "incomplete"
    assert result["blocking_reasons"] == ["weak_sec_provenance"]
    assert result["repair_actions"] == ["refresh_sec_provenance"]


def test_low_classification_confidence_is_review_grade_not_hard_failure() -> None:
    artifact = clean_artifact()
    artifact["issuer"]["classification_confidence"] = 0.7

    result = assess_artifact(artifact)

    assert result["decision"] == "approved_with_caveat"
    assert result["publication_state"] == "review_required"
    assert result["blocking_reasons"] == []
    assert result["repair_actions"] == [
        "reclassify_issuer_or_switch_model"
    ]
    assert result["warnings"] == [
        "Classification confidence is below the 0.80 review threshold."
    ]


def test_structural_model_warning_is_a_hard_failure() -> None:
    artifact = clean_artifact()
    warning = "Terminal value exceeds 85% of enterprise value."
    artifact["review"]["warnings"] = [warning]

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["publication_state"] == "withheld"
    assert result["blocking_reasons"] == ["review_hard_warning"]
    assert warning not in json.dumps(result["blocking_reasons"])
    assert result["repair_actions"] == ["resolve_model_warnings"]


def test_bounded_bridge_review_states_are_not_misclassified_as_model_failures() -> None:
    artifact = clean_artifact()
    artifact["bridge_quality"] = {"decision": "bounded_review"}
    artifact["review"]["publication_state"] = "review_required"
    artifact["models"]["fcff_dcf"]["publication_state"] = "review_required"
    artifact["models"]["epv"]["publication_state"] = "review_required"
    for scenario in artifact["scenarios"].values():
        scenario["fcff_dcf"]["publication_state"] = "review_required"
    artifact["review"]["warnings"] = ["Bounded bridge requires review."]

    result = assess_artifact(artifact)

    assert result["decision"] == "approved_with_caveat"
    assert result["publication_state"] == "review_required"
    assert result["blocking_reasons"] == []


def test_declared_supporting_review_grade_model_is_a_public_caveat() -> None:
    artifact = clean_artifact()
    artifact["bridge_quality"] = {"decision": "complete"}
    artifact["models"]["epv"]["publication_state"] = "review_required"

    result = assess_artifact(artifact)

    assert result["decision"] == "approved_with_caveat"
    assert result["publication_state"] == "review_required"
    assert result["blocking_reasons"] == []
    assert result["repair_actions"] == []
    assert result["warnings"] == [
        "Supporting model 'epv' is review_required."
    ]


def test_finite_primary_review_grade_model_remains_visible_with_caveat() -> None:
    artifact = clean_artifact()
    artifact["review"]["publication_state"] = "review_required"
    artifact["models"]["fcff_dcf"]["publication_state"] = "review_required"

    result = assess_artifact(artifact)

    assert result["decision"] == "approved_with_caveat"
    assert result["publication_state"] == "review_required"
    assert result["blocking_reasons"] == []
    assert result["warnings"] == [
        "Primary model 'fcff_dcf' is review_required."
    ]


def test_withheld_primary_model_remains_blocking() -> None:
    artifact = clean_artifact()
    artifact["models"]["fcff_dcf"].update(
        {
            "publication_state": "withheld",
            "intrinsic_value_per_share": None,
        }
    )

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["publication_state"] == "withheld"
    assert result["blocking_reasons"] == [
        "model_not_pass:fcff_dcf",
        "missing_model_value:fcff_dcf",
    ]


@pytest.mark.parametrize("value", [True, math.inf, -math.inf, math.nan])
def test_nonfinite_primary_model_value_remains_blocking(value: object) -> None:
    artifact = clean_artifact()
    artifact["models"]["fcff_dcf"]["intrinsic_value_per_share"] = value

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["publication_state"] == "withheld"
    assert result["blocking_reasons"] == [
        "nonfinite_model_value:fcff_dcf"
    ]


def test_finite_review_grade_scenario_is_a_caveat_not_a_bypass() -> None:
    artifact = clean_artifact()
    artifact["scenarios"]["base"]["fcff_dcf"][
        "publication_state"
    ] = "review_required"

    result = assess_artifact(artifact)

    assert result["decision"] == "approved_with_caveat"
    assert result["blocking_reasons"] == []
    assert result["warnings"] == [
        "Scenario 'base' model 'fcff_dcf' is review_required."
    ]


def test_arbitrary_scenario_model_withheld_is_blocked_once() -> None:
    artifact = clean_artifact()
    artifact["scenarios"]["stress"] = {
        "custom_model": {
            "publication_state": "withheld",
            "intrinsic_value_per_share": None,
        }
    }

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["blocking_reasons"] == [
        "scenario_not_pass:stress:custom_model"
    ]


@pytest.mark.parametrize("value", [True, math.inf, math.nan])
def test_malformed_scenario_value_remains_blocking(value: object) -> None:
    artifact = clean_artifact()
    artifact["scenarios"]["base"]["fcff_dcf"][
        "intrinsic_value_per_share"
    ] = value

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["publication_state"] == "withheld"
    assert result["blocking_reasons"] == [
        "nonfinite_scenario_value:base:fcff_dcf"
    ]


def test_duplicate_review_messages_are_deduplicated_in_source_order() -> None:
    artifact = clean_artifact()
    artifact["review"]["errors"] = ["same", "same"]
    artifact["review"]["warnings"] = ["soft", "soft"]

    result = assess_artifact(artifact)

    assert result["blocking_reasons"] == ["review_errors_present"]
    assert result["warnings"] == ["soft"]


@pytest.mark.parametrize(
    ("location", "field", "message", "expected_reason"),
    [
        (
            "model",
            "errors",
            "ATTACKER_PRIVATE_MODEL_ERROR",
            "model_errors:fcff_dcf",
        ),
        (
            "model",
            "warnings",
            "ATTACKER_PRIVATE fallback warning",
            "model_hard_warning:fcff_dcf",
        ),
        (
            "scenario",
            "errors",
            "ATTACKER_PRIVATE_SCENARIO_ERROR",
            "scenario_model_errors:base:fcff_dcf",
        ),
        (
            "scenario",
            "warnings",
            "ATTACKER_PRIVATE bridge incomplete warning",
            "scenario_model_hard_warning:base:fcff_dcf",
        ),
    ],
)
def test_model_and_scenario_local_failures_block_with_generic_reasons(
    location: str,
    field: str,
    message: str,
    expected_reason: str,
) -> None:
    artifact = clean_artifact()
    target = (
        artifact["models"]["fcff_dcf"]
        if location == "model"
        else artifact["scenarios"]["base"]["fcff_dcf"]
    )
    target[field] = [message]

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["publication_state"] == "withheld"
    assert result["blocking_reasons"] == [expected_reason]
    assert message not in json.dumps(result["blocking_reasons"])


@pytest.mark.parametrize(
    ("location", "field", "expected_reason"),
    [
        ("model", "errors", "invalid_model_errors:fcff_dcf"),
        (
            "scenario",
            "warnings",
            "invalid_scenario_model_warnings:base:fcff_dcf",
        ),
    ],
)
def test_model_and_scenario_message_lists_are_validated(
    location: str, field: str, expected_reason: str
) -> None:
    artifact = clean_artifact()
    target = (
        artifact["models"]["fcff_dcf"]
        if location == "model"
        else artifact["scenarios"]["base"]["fcff_dcf"]
    )
    target[field] = "ATTACKER_PRIVATE_NOT_A_LIST"

    result = assess_artifact(artifact)

    assert result["publication_state"] == "withheld"
    assert result["blocking_reasons"] == [expected_reason]
    assert "ATTACKER_PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("location", ["model", "scenario"])
def test_ordinary_model_and_scenario_warnings_are_public_caveats(
    location: str,
) -> None:
    artifact = clean_artifact()
    message = "Sensitivity should be reviewed before publication."
    target = (
        artifact["models"]["fcff_dcf"]
        if location == "model"
        else artifact["scenarios"]["base"]["fcff_dcf"]
    )
    target["warnings"] = [message]

    result = assess_artifact(artifact)

    assert result["decision"] == "approved_with_caveat"
    assert result["publication_state"] == "review_required"
    assert result["blocking_reasons"] == []
    assert any(message in warning for warning in result["warnings"])
