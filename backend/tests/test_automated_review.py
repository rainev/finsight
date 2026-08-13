from __future__ import annotations

from copy import deepcopy

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
        "model_policy": {"primary": "fcff_dcf"},
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
    assert result["blocking_reasons"] == [f"hard_warning:{warning}"]
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


def test_complete_bridge_review_grade_model_is_blocked_with_concrete_reason() -> None:
    artifact = clean_artifact()
    artifact["bridge_quality"] = {"decision": "complete"}
    artifact["models"]["epv"]["publication_state"] = "review_required"

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["blocking_reasons"] == ["model_not_pass:epv"]
    assert result["repair_actions"] == ["rebuild_valuation_models"]


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


def test_duplicate_review_messages_are_deduplicated_in_source_order() -> None:
    artifact = clean_artifact()
    artifact["review"]["errors"] = ["same", "same"]
    artifact["review"]["warnings"] = ["soft", "soft"]

    result = assess_artifact(artifact)

    assert result["blocking_reasons"] == ["review_error:same"]
    assert result["warnings"] == ["soft"]
