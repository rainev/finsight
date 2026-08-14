from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from app.us_valuation.artifacts import (
    frontend_company,
    public_result,
    sanitize_public_artifact,
)
from app.us_valuation.pipeline import build_us_valuation


FIXTURES = Path(__file__).parent / "fixtures" / "us"
BRIDGE_FIELD = "marketable_securities_noncurrent"
BRIDGE_WARNING = (
    "Enterprise-to-equity bridge uses source-bounded uncertainty; "
    "the joint intrinsic-value spread is 1.00% and requires review."
)
QUALITY_KEYS = {
    "decision",
    "complete",
    "usable",
    "bounded_fields",
    "blocking_fields",
    "reason_codes",
    "intrinsic_value_range",
}
RANGE_KEYS = {
    "low",
    "midpoint",
    "high",
    "spread_ratio",
    "spread_limit",
}
RELIABILITY_KEYS = {
    "label",
    "accounting_label",
    "scenario_label",
    "model_cap",
    "source_cap",
    "accounting_impact_ratio",
    "scenario_movement_ratio",
    "reasons",
}


def load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def submissions() -> dict[str, Any]:
    return load_json("aapl-submissions.json")


@pytest.fixture(scope="module")
def private_aapl() -> dict[str, Any]:
    return build_us_valuation(
        submissions=load_json("aapl-submissions.json"),
        companyfacts=load_json("aapl-companyfacts.json"),
        valuation_date="2026-08-01",
    )


def _make_native_pass(result: dict[str, Any]) -> None:
    result["review"]["publication_state"] = "pass"
    result["review"]["errors"] = []
    result["review"]["warnings"] = []
    for model in result["models"].values():
        model["publication_state"] = "pass"
        model["errors"] = []
        model["warnings"] = []
    for scenario in result["scenarios"].values():
        for model in scenario.values():
            model["publication_state"] = "pass"
            model["errors"] = []
            model["warnings"] = []


def _install_private_assessment(
    result: dict[str, Any],
    *,
    decision: str,
    usable: bool,
    low: float | None,
    midpoint: float | None,
    high: float | None,
    spread_ratio: float | None,
    blocking_fields: list[str],
    bounded_fields: list[str],
    reason_codes: list[str],
    warning: str | None,
) -> None:
    balance = result["financials"]["balance_sheet"]
    balance.update(
        {
            "bridge_complete": decision == "complete",
            "bridge_can_value": not blocking_fields,
            "bridge_usable": usable,
            "bridge_decision": decision,
            "bridge_missing_fields": sorted(
                set(blocking_fields) | set(bounded_fields)
            ),
            "bridge_blocking_fields": blocking_fields,
            "bridge_bounded_fields": bounded_fields,
            "bridge_uncertainty": {
                "decision": decision,
                "usable": usable,
                "intrinsic_value_range": (
                    None
                    if low is None and midpoint is None and high is None
                    else {"low": low, "midpoint": midpoint, "high": high}
                ),
                "spread_ratio": spread_ratio,
                "spread_limit": 0.01,
                "blocking_fields": blocking_fields,
                "bounded_fields": bounded_fields,
                "reason_codes": reason_codes,
                "warning": warning,
                "policy_version": "US-BRIDGE-POLICY-1.0",
            },
        }
    )


def _bounded_private(private_aapl: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(private_aapl)
    _make_native_pass(result)
    result["models"]["fcff_dcf"]["intrinsic_value_per_share"] = 100.0
    _install_private_assessment(
        result,
        decision="bounded_review",
        usable=True,
        low=99.5,
        midpoint=100.0,
        high=100.5,
        spread_ratio=0.01,
        blocking_fields=[],
        bounded_fields=[BRIDGE_FIELD],
        reason_codes=["CURRENT_NOTE_SUPPLIES_FINITE_RANGE"],
        warning=BRIDGE_WARNING,
    )
    return result


def _approved_review() -> dict[str, Any]:
    return {
        "review_version": "US-AUTO-REVIEW-1.0",
        "decision": "approved",
        "publication_state": "pass",
        "evidence_status": "complete",
        "blocking_reasons": [],
        "repair_actions": [],
        "warnings": [],
    }


def _blocked_review() -> dict[str, Any]:
    return {
        "review_version": "US-AUTO-REVIEW-1.0",
        "decision": "blocked",
        "publication_state": "withheld",
        "evidence_status": "complete",
        "blocking_reasons": ["model_not_pass:epv"],
        "repair_actions": ["rebuild_valuation_models"],
        "warnings": [],
    }


def _range(
    low: float | None,
    midpoint: float | None,
    high: float | None,
    spread_ratio: float | None,
) -> dict[str, Any]:
    return {
        "low": low,
        "midpoint": midpoint,
        "high": high,
        "spread_ratio": spread_ratio,
        "spread_limit": 0.01,
    }


def complete_quality(value: float | None = 100.0) -> dict[str, Any]:
    return {
        "decision": "complete",
        "complete": True,
        "usable": True,
        "bounded_fields": [],
        "blocking_fields": [],
        "reason_codes": [],
        "intrinsic_value_range": _range(value, value, value, 0.0),
    }


def bounded_quality() -> dict[str, Any]:
    return {
        "decision": "bounded_review",
        "complete": False,
        "usable": True,
        "bounded_fields": [BRIDGE_FIELD],
        "blocking_fields": [],
        "reason_codes": ["CURRENT_NOTE_SUPPLIES_FINITE_RANGE"],
        "intrinsic_value_range": _range(99.5, 100.0, 100.5, 0.01),
    }


def wide_bounded_quality() -> dict[str, Any]:
    return {
        "decision": "bounded_review",
        "complete": False,
        "usable": True,
        "bounded_fields": [BRIDGE_FIELD],
        "blocking_fields": [],
        "reason_codes": ["CURRENT_NOTE_SUPPLIES_FINITE_RANGE"],
        "intrinsic_value_range": _range(95.0, 100.0, 105.0, 0.10),
    }


def reliability_dto(
    *,
    label: str = "High",
    accounting_label: str = "High",
    scenario_label: str = "High",
    model_cap: str = "High",
    source_cap: str = "High",
    accounting_impact_ratio: float = 0.0,
    scenario_movement_ratio: float = 0.20,
    reasons: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "label": label,
        "accounting_label": accounting_label,
        "scenario_label": scenario_label,
        "model_cap": model_cap,
        "source_cap": source_cap,
        "accounting_impact_ratio": accounting_impact_ratio,
        "scenario_movement_ratio": scenario_movement_ratio,
        "reasons": [] if reasons is None else reasons,
    }


def over_limit_quality() -> dict[str, Any]:
    low = 99.4999995
    midpoint = 100.0
    high = 100.5000005
    ratio = (high - low) / midpoint
    return {
        "decision": "withheld",
        "complete": False,
        "usable": False,
        "bounded_fields": [BRIDGE_FIELD],
        "blocking_fields": [],
        "reason_codes": [
            "CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
            "JOINT_INTRINSIC_VALUE_SPREAD_EXCEEDS_LIMIT",
        ],
        "intrinsic_value_range": _range(low, midpoint, high, ratio),
    }


def blocked_quality() -> dict[str, Any]:
    return {
        "decision": "withheld",
        "complete": False,
        "usable": False,
        "bounded_fields": [],
        "blocking_fields": ["cash"],
        "reason_codes": ["BRIDGE_FIELD_MISSING_OR_INVALID"],
        "intrinsic_value_range": _range(None, None, None, None),
    }


def no_base_quality() -> dict[str, Any]:
    return {
        "decision": "withheld",
        "complete": False,
        "usable": False,
        "bounded_fields": [BRIDGE_FIELD],
        "blocking_fields": [],
        "reason_codes": ["BASE_ENTERPRISE_VALUE_UNAVAILABLE"],
        "intrinsic_value_range": _range(None, None, None, None),
    }


def public_artifact(
    *,
    quality: dict[str, Any] | None = None,
    review_state: str = "pass",
    automated_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = {
        "schema_version": "US-PUBLIC-VALUATION-1.0",
        "issuer": {
            "ticker": "TEST",
            "classification_confidence": 0.98,
        },
        "source_financial_statement": {
            "form": "10-Q",
            "period_end": "2026-03-31",
            "filed_date": "2026-05-01",
            "accession": "0000000001-26-000001",
            "url": (
                "https://www.sec.gov/Archives/edgar/data/1/"
                "000000000126000001/test.htm"
            ),
        },
        "model_policy": {
            "primary": "fcff_dcf",
            "supporting": ["arbitrary_top_model"],
            "reason": "test",
        },
        "review": {
            "publication_state": review_state,
            "errors": [],
            "warnings": [],
        },
        "automated_review": deepcopy(automated_review or _approved_review()),
        "models": {
            "fcff_dcf": {
                "publication_state": "pass",
                "intrinsic_value_per_share": 100.0,
            },
            "arbitrary_top_model": {
                "publication_state": "pass",
                "intrinsic_value_per_share": 95.0,
            },
        },
        "scenarios": {
            "stress": {
                "arbitrary_scenario_model": {
                    "publication_state": "pass",
                    "intrinsic_value_per_share": 80.0,
                },
                "second_scenario_model": {
                    "publication_state": "pass",
                    "intrinsic_value_per_share": 82.0,
                },
            },
            "base": {
                "fcff_dcf": {
                    "publication_state": "pass",
                    "intrinsic_value_per_share": 100.0,
                }
            },
        },
        "scenario_range": {
            "low": 80.0,
            "base": 100.0,
            "high": 120.0,
            "label": "assumption range, not a statistical confidence interval",
            "injected": 999.0,
        },
        "sensitivities": [
            {
                "field": "wacc",
                "publication_state": "pass",
                "intrinsic_value_per_share": 90.0,
            },
            {
                "field": "growth",
                "publication_state": "pass",
                "intrinsic_value_per_share": 110.0,
            },
        ],
    }
    if quality is not None:
        artifact["bridge_quality"] = deepcopy(quality)
    return artifact


def current_public_artifact(
    *, quality: dict[str, Any] | None = None
) -> dict[str, Any]:
    artifact = public_artifact(quality=quality or complete_quality())
    artifact["schema_version"] = "US-PUBLIC-VALUATION-1.1"
    artifact["reliability"] = reliability_dto()
    return artifact


def _all_value_sinks(artifact: dict[str, Any]) -> list[Any]:
    return [
        *(model["intrinsic_value_per_share"] for model in artifact["models"].values()),
        *(
            model["intrinsic_value_per_share"]
            for scenario in artifact["scenarios"].values()
            for model in scenario.values()
        ),
        *(row["intrinsic_value_per_share"] for row in artifact.get("sensitivities", [])),
        artifact["scenario_range"]["low"],
        artifact["scenario_range"]["base"],
        artifact["scenario_range"]["high"],
    ]


def test_public_result_signature_has_no_sanitizer_bypass(
    private_aapl: dict[str, Any], submissions: dict[str, Any]
) -> None:
    signature = inspect.signature(public_result)
    assert list(signature.parameters) == [
        "result",
        "submissions",
    ]
    assert signature.parameters["submissions"].default is None
    public = public_result(private_aapl, submissions)
    assert public["review"]["publication_state"] == "review_required"
    assert public["models"]["fcff_dcf"]["intrinsic_value_per_share"] is not None


def test_complete_public_result_exposes_exact_allowlisted_quality(
    private_aapl: dict[str, Any], submissions: dict[str, Any]
) -> None:
    private = deepcopy(private_aapl)
    _make_native_pass(private)

    public = public_result(private, submissions)

    quality = public["bridge_quality"]
    assert set(quality) == QUALITY_KEYS
    assert set(quality["intrinsic_value_range"]) == RANGE_KEYS
    assert quality["decision"] == "complete"
    assert quality["complete"] is True
    assert quality["usable"] is True
    assert quality["bounded_fields"] == []
    assert quality["blocking_fields"] == []
    assert quality["reason_codes"] == []
    assert quality["intrinsic_value_range"] == {
        "low": 130.59749600881733,
        "midpoint": 130.59749600881733,
        "high": 130.59749600881733,
        "spread_ratio": 0.0,
        "spread_limit": 0.01,
    }


def test_exact_one_percent_bounded_result_is_review_required_and_public_safe(
    private_aapl: dict[str, Any], submissions: dict[str, Any]
) -> None:
    private = _bounded_private(private_aapl)
    original = deepcopy(private)

    public = public_result(private, submissions)

    assert private == original
    assert public["review"]["publication_state"] == "review_required"
    assert public["bridge_quality"] == {
        "decision": "bounded_review",
        "complete": False,
        "usable": True,
        "bounded_fields": [BRIDGE_FIELD],
        "blocking_fields": [],
        "reason_codes": ["CURRENT_NOTE_SUPPLIES_FINITE_RANGE"],
        "intrinsic_value_range": {
            "low": 99.5,
            "midpoint": 100.0,
            "high": 100.5,
            "spread_ratio": 0.01,
            "spread_limit": 0.01,
        },
    }
    assert all(
        model["publication_state"] == "review_required"
        for model in public["models"].values()
    )
    assert all(
        model["publication_state"] == "review_required"
        for scenario in public["scenarios"].values()
        for model in scenario.values()
    )
    serialized = json.dumps(public)
    for private_token in (
        '"availability"',
        '"bridge_precheck"',
        '"bridge_uncertainty"',
        '"cash_and_nonoperating_investments"',
        '"fully_diluted_shares"',
        '"enterprise_value"',
    ):
        assert private_token not in serialized


def test_new_public_result_exposes_exact_allowlisted_reliability(
    private_aapl: dict[str, Any], submissions: dict[str, Any]
) -> None:
    private = deepcopy(private_aapl)
    _make_native_pass(private)
    private["models"]["fcff_dcf"]["intrinsic_value_per_share"] = 100.0
    private["scenario_range"].update(
        {"low": 75.0, "base": 100.0, "high": 125.0}
    )
    _install_private_assessment(
        private,
        decision="bounded_review",
        usable=True,
        low=95.0,
        midpoint=100.0,
        high=105.0,
        spread_ratio=0.10,
        blocking_fields=[],
        bounded_fields=[BRIDGE_FIELD],
        reason_codes=[],
        warning=(
            "Enterprise-to-equity bridge uses source-bounded uncertainty; "
            "the joint intrinsic-value spread is 10.00% and requires review."
        ),
    )
    private["reliability"] = reliability_dto(
        label="Medium",
        accounting_label="High",
        scenario_label="Medium",
        accounting_impact_ratio=0.05,
        scenario_movement_ratio=0.25,
    )

    public = public_result(private, submissions)

    assert public["schema_version"] == "US-PUBLIC-VALUATION-1.1"
    assert set(public["reliability"]) == RELIABILITY_KEYS
    assert public["reliability"] == {
        "label": "Medium",
        "accounting_label": "High",
        "scenario_label": "Medium",
        "model_cap": "High",
        "source_cap": "High",
        "accounting_impact_ratio": pytest.approx(0.05),
        "scenario_movement_ratio": pytest.approx(0.25),
        "reasons": [],
    }
    assert public["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0


def test_regenerated_wide_bounded_review_is_graded_instead_of_scrubbed() -> None:
    artifact = public_artifact(quality=wide_bounded_quality())
    artifact["schema_version"] = "US-PUBLIC-VALUATION-1.1"
    artifact["reliability"] = reliability_dto(
        accounting_impact_ratio=0.05,
        reasons=["CURRENT_NOTE_SUPPLIES_FINITE_RANGE"],
    )

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "review_required"
    assert sanitized["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0
    assert sanitized["bridge_quality"]["intrinsic_value_range"] == _range(
        95.0, 100.0, 105.0, 0.10
    )
    assert sanitized["reliability"]["label"] == "High"


def test_historical_one_zero_wide_bounded_review_remains_fail_closed() -> None:
    artifact = public_artifact(quality=wide_bounded_quality())
    artifact["reliability"] = reliability_dto(
        accounting_impact_ratio=0.05,
        reasons=["CURRENT_NOTE_SUPPLIES_FINITE_RANGE"],
    )

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert sanitized["models"]["fcff_dcf"]["intrinsic_value_per_share"] is None
    assert sanitized["reliability"] == {
        "label": "Low",
        "accounting_label": "Low",
        "scenario_label": "Low",
        "model_cap": "Low",
        "source_cap": "Low",
        "accounting_impact_ratio": None,
        "scenario_movement_ratio": None,
        "reasons": ["VALUATION_WITHHELD"],
    }


def _reliability_unknown_label(artifact: dict[str, Any]) -> None:
    artifact["reliability"]["label"] = "Certain"


def _reliability_boolean_ratio(artifact: dict[str, Any]) -> None:
    artifact["reliability"]["accounting_impact_ratio"] = True


def _reliability_nonfinite_ratio(artifact: dict[str, Any]) -> None:
    artifact["reliability"]["scenario_movement_ratio"] = float("nan")


def _reliability_duplicate_reasons(artifact: dict[str, Any]) -> None:
    artifact["reliability"]["reasons"] = [
        "CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
        "CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
    ]


def _reliability_unknown_reason(artifact: dict[str, Any]) -> None:
    artifact["reliability"]["reasons"] = ["ATTACKER_PRIVATE_REASON"]


def _reliability_extra_private_key(artifact: dict[str, Any]) -> None:
    artifact["reliability"]["private_warning"] = "ATTACKER_PRIVATE_WARNING"


def _reliability_missing_key(artifact: dict[str, Any]) -> None:
    del artifact["reliability"]["source_cap"]


def _reliability_nonmapping(artifact: dict[str, Any]) -> None:
    artifact["reliability"] = ["ATTACKER_PRIVATE_ERROR"]


@pytest.mark.parametrize(
    "mutation",
    [
        _reliability_unknown_label,
        _reliability_boolean_ratio,
        _reliability_nonfinite_ratio,
        _reliability_duplicate_reasons,
        _reliability_unknown_reason,
        _reliability_extra_private_key,
        _reliability_missing_key,
        _reliability_nonmapping,
    ],
)
def test_malformed_reliability_uses_generic_numeric_fallback_without_scrubbing(
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    artifact = public_artifact(quality=complete_quality())
    artifact["schema_version"] = "US-PUBLIC-VALUATION-1.1"
    artifact["reliability"] = reliability_dto()
    mutation(artifact)

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "pass"
    assert sanitized["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0
    assert sanitized["scenario_range"] == {
        "low": 80.0,
        "base": 100.0,
        "high": 120.0,
        "label": "assumption range, not a statistical confidence interval",
    }
    assert sanitized["reliability"] == {
        "label": "Low",
        "accounting_label": "Low",
        "scenario_label": "Low",
        "model_cap": "Low",
        "source_cap": "Low",
        "accounting_impact_ratio": 0.0,
        "scenario_movement_ratio": pytest.approx(0.20),
        "reasons": ["RELIABILITY_PAYLOAD_INVALID"],
    }
    serialized = json.dumps(sanitized)
    assert "ATTACKER_PRIVATE" not in serialized
    assert "Certain" not in serialized


def test_self_consistent_reliability_must_match_current_scenario_range() -> None:
    artifact = current_public_artifact()
    artifact["reliability"] = reliability_dto(
        label="Medium",
        scenario_label="Medium",
        scenario_movement_ratio=0.25,
    )
    before = deepcopy(artifact)

    once = sanitize_public_artifact(artifact)
    twice = sanitize_public_artifact(once)

    assert artifact == before
    assert twice == once
    assert once["review"]["publication_state"] == "pass"
    assert once["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0
    assert once["scenario_range"]["base"] == 100.0
    assert once["reliability"] == {
        "label": "Low",
        "accounting_label": "Low",
        "scenario_label": "Low",
        "model_cap": "Low",
        "source_cap": "Low",
        "accounting_impact_ratio": 0.0,
        "scenario_movement_ratio": pytest.approx(0.20),
        "reasons": ["RELIABILITY_PAYLOAD_INVALID"],
    }


@pytest.mark.parametrize(
    "reliability",
    [
        reliability_dto(accounting_impact_ratio=0.05),
        reliability_dto(label="Medium", source_cap="Medium"),
    ],
)
def test_fcff_reliability_must_match_bridge_arithmetic_and_source_cap(
    reliability: dict[str, Any],
) -> None:
    artifact = current_public_artifact()
    artifact["reliability"] = reliability

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "pass"
    assert sanitized["bridge_quality"]["decision"] == "complete"
    assert sanitized["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0
    assert sanitized["reliability"]["label"] == "Low"
    assert sanitized["reliability"]["accounting_impact_ratio"] == 0.0
    assert sanitized["reliability"]["scenario_movement_ratio"] == pytest.approx(
        0.20
    )
    assert sanitized["reliability"]["reasons"] == [
        "RELIABILITY_PAYLOAD_INVALID"
    ]


def _weaken_current_provenance(artifact: dict[str, Any]) -> None:
    artifact["source_financial_statement"].update(
        {
            "filed_date": None,
            "url": "https://www.sec.gov/cgi-bin/browse-edgar?CIK=1",
        }
    )


def _malform_current_model_policy(artifact: dict[str, Any]) -> None:
    artifact["model_policy"]["supporting"] = "arbitrary_top_model"


def _add_current_review_error(artifact: dict[str, Any]) -> None:
    artifact["review"]["errors"] = ["ATTACKER_PRIVATE_REVIEW_ERROR"]


@pytest.mark.parametrize(
    ("mutation", "blocking_reason"),
    [
        (_weaken_current_provenance, "weak_sec_provenance"),
        (_malform_current_model_policy, "invalid_model_policy"),
        (_add_current_review_error, "review_errors_present"),
    ],
)
def test_current_sanitizer_recomputes_stale_shape_valid_automated_review(
    mutation: Callable[[dict[str, Any]], None], blocking_reason: str
) -> None:
    artifact = current_public_artifact()
    artifact["automated_review"] = _approved_review()
    mutation(artifact)

    once = sanitize_public_artifact(artifact)
    twice = sanitize_public_artifact(once)

    assert twice == once
    assert once["automated_review"]["publication_state"] == "withheld"
    assert blocking_reason in once["automated_review"]["blocking_reasons"]
    assert once["review"]["publication_state"] == "withheld"
    assert once["models"]["fcff_dcf"]["intrinsic_value_per_share"] is None
    assert once["scenario_range"]["base"] is None
    assert once["reliability"] == _withheld_reliability_for_test()


def _withheld_reliability_for_test() -> dict[str, Any]:
    return {
        "label": "Low",
        "accounting_label": "Low",
        "scenario_label": "Low",
        "model_cap": "Low",
        "source_cap": "Low",
        "accounting_impact_ratio": None,
        "scenario_movement_ratio": None,
        "reasons": ["VALUATION_WITHHELD"],
    }


@pytest.mark.parametrize(
    ("location", "field", "message", "blocking_reason"),
    [
        (
            "model",
            "errors",
            "ATTACKER_PRIVATE_MODEL_ERROR",
            "model_errors:fcff_dcf",
        ),
        (
            "scenario",
            "warnings",
            "ATTACKER_PRIVATE fallback warning",
            "scenario_model_hard_warning:base:fcff_dcf",
        ),
    ],
)
def test_current_sanitizer_blocks_local_errors_and_hard_warnings(
    location: str,
    field: str,
    message: str,
    blocking_reason: str,
) -> None:
    artifact = current_public_artifact()
    target = (
        artifact["models"]["fcff_dcf"]
        if location == "model"
        else artifact["scenarios"]["base"]["fcff_dcf"]
    )
    target[field] = [message]
    artifact["automated_review"] = _approved_review()

    once = sanitize_public_artifact(artifact)
    twice = sanitize_public_artifact(once)

    assert twice == once
    assert once["review"]["publication_state"] == "withheld"
    assert blocking_reason in once["automated_review"]["blocking_reasons"]
    assert message not in json.dumps(once["automated_review"]["blocking_reasons"])
    assert message not in json.dumps(once["reliability"])
    assert once["reliability"] == _withheld_reliability_for_test()


@pytest.mark.parametrize(
    ("schema_version", "reason"),
    [
        (
            "US-PUBLIC-VALUATION-1.0",
            "LEGACY_ARTIFACT_NOT_REGENERATED",
        ),
        (
            "US-PUBLIC-VALUATION-1.1",
            "RELIABILITY_PAYLOAD_INVALID",
        ),
    ],
)
def test_missing_reliability_uses_versioned_numeric_fallback(
    schema_version: str, reason: str
) -> None:
    artifact = public_artifact(quality=complete_quality())
    artifact["schema_version"] = schema_version

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "pass"
    assert sanitized["scenario_range"]["base"] == 100.0
    assert sanitized["reliability"] == {
        "label": "Low",
        "accounting_label": "Low",
        "scenario_label": "Low",
        "model_cap": "Low",
        "source_cap": "Low",
        "accounting_impact_ratio": 0.0,
        "scenario_movement_ratio": pytest.approx(0.20),
        "reasons": [reason],
    }


def test_overflowing_derived_reliability_ratio_withholds_malformed_contract() -> None:
    artifact = public_artifact(quality=complete_quality())
    artifact["scenario_range"].update(
        {"low": -1.7e308, "base": 1e-308, "high": 1.7e308}
    )

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert sanitized["scenario_range"]["base"] is None
    assert sanitized["reliability"] == {
        "label": "Low",
        "accounting_label": "Low",
        "scenario_label": "Low",
        "model_cap": "Low",
        "source_cap": "Low",
        "accounting_impact_ratio": None,
        "scenario_movement_ratio": None,
        "reasons": ["VALUATION_WITHHELD"],
    }


def test_withheld_artifact_uses_nonfabricated_reliability_without_private_text() -> None:
    artifact = public_artifact(quality=blocked_quality())
    artifact["schema_version"] = "US-PUBLIC-VALUATION-1.1"
    artifact["reliability"] = {
        **reliability_dto(),
        "reasons": ["ATTACKER_PRIVATE_WITHHOLDING_REASON"],
        "private_error": "ATTACKER_PRIVATE_ERROR",
    }

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert sanitized["reliability"] == {
        "label": "Low",
        "accounting_label": "Low",
        "scenario_label": "Low",
        "model_cap": "Low",
        "source_cap": "Low",
        "accounting_impact_ratio": None,
        "scenario_movement_ratio": None,
        "reasons": ["VALUATION_WITHHELD"],
    }
    assert "ATTACKER_PRIVATE" not in json.dumps(sanitized)


@pytest.mark.parametrize(
    ("quality", "expected_decision", "expected_ratio", "expected_reasons"),
    [
        (
            over_limit_quality(),
            "withheld",
            over_limit_quality()["intrinsic_value_range"]["spread_ratio"],
            [
                "CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
                "JOINT_INTRINSIC_VALUE_SPREAD_EXCEEDS_LIMIT",
            ],
        ),
        (
            blocked_quality(),
            "withheld",
            None,
            ["BRIDGE_FIELD_MISSING_OR_INVALID"],
        ),
        (
            no_base_quality(),
            "withheld",
            None,
            ["BASE_ENTERPRISE_VALUE_UNAVAILABLE"],
        ),
    ],
)
def test_withheld_quality_shapes_retain_metadata_but_scrub_absolute_range(
    quality: dict[str, Any],
    expected_decision: str,
    expected_ratio: float | None,
    expected_reasons: list[str],
) -> None:
    artifact = public_artifact(quality=quality)

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert sanitized["bridge_quality"]["decision"] == expected_decision
    assert sanitized["bridge_quality"]["reason_codes"] == expected_reasons
    assert sanitized["bridge_quality"]["intrinsic_value_range"] == {
        "low": None,
        "midpoint": None,
        "high": None,
        "spread_ratio": expected_ratio,
        "spread_limit": 0.01,
    }
    assert set(_all_value_sinks(sanitized)) == {None}


@pytest.mark.parametrize(
    ("quality", "ceiling"),
    [
        (complete_quality(), "pass"),
        (bounded_quality(), "review_required"),
        (blocked_quality(), "withheld"),
    ],
)
def test_publication_lattice_is_monotonic_across_every_sink(
    quality: dict[str, Any], ceiling: str
) -> None:
    strictness = {"pass": 0, "review_required": 1, "withheld": 2}
    states = ("pass", "review_required", "withheld")

    for existing_state in states:
        artifact = public_artifact(quality=quality)
        artifact["review"]["publication_state"] = existing_state
        for model in artifact["models"].values():
            model["publication_state"] = existing_state
        for scenario in artifact["scenarios"].values():
            for model in scenario.values():
                model["publication_state"] = existing_state
        for row in artifact["sensitivities"]:
            row["publication_state"] = existing_state

        sanitized = sanitize_public_artifact(artifact)
        expected = max(
            (existing_state, ceiling), key=lambda state: strictness[state]
        )

        assert sanitized["review"]["publication_state"] == expected
        assert {
            model["publication_state"]
            for model in sanitized["models"].values()
        } == {expected}
        assert {
            model["publication_state"]
            for scenario in sanitized["scenarios"].values()
            for model in scenario.values()
        } == {expected}
        assert {
            row["publication_state"]
            for row in sanitized["sensitivities"]
        } == {expected}
        if expected == "withheld":
            assert set(_all_value_sinks(sanitized)) == {None}


def test_individually_withheld_sinks_are_scrubbed_without_global_promotion() -> None:
    artifact = public_artifact(quality=complete_quality())
    artifact["models"]["arbitrary_top_model"]["publication_state"] = "withheld"
    artifact["scenarios"]["stress"]["arbitrary_scenario_model"][
        "publication_state"
    ] = "withheld"
    artifact["sensitivities"][0]["publication_state"] = "withheld"

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "pass"
    assert sanitized["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0
    assert sanitized["models"]["arbitrary_top_model"] == {
        "publication_state": "withheld",
        "intrinsic_value_per_share": None,
    }
    assert sanitized["scenarios"]["stress"]["arbitrary_scenario_model"][
        "intrinsic_value_per_share"
    ] is None
    assert sanitized["scenarios"]["stress"]["second_scenario_model"][
        "intrinsic_value_per_share"
    ] == 82.0
    assert sanitized["sensitivities"][0]["intrinsic_value_per_share"] is None
    assert sanitized["sensitivities"][1]["intrinsic_value_per_share"] == 110.0
    assert sanitized["scenario_range"] == {
        "low": None,
        "base": None,
        "high": None,
        "label": "assumption range, not a statistical confidence interval",
    }


def test_unrelated_global_withholding_keeps_bridge_truth_but_scrubs_range() -> None:
    artifact = public_artifact(
        quality=complete_quality(), automated_review=_blocked_review()
    )
    snapshot = deepcopy(artifact["automated_review"])

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["automated_review"] == snapshot
    assert sanitized["bridge_quality"]["decision"] == "complete"
    assert sanitized["bridge_quality"]["complete"] is True
    assert sanitized["bridge_quality"]["intrinsic_value_range"] == {
        "low": None,
        "midpoint": None,
        "high": None,
        "spread_ratio": 0.0,
        "spread_limit": 0.01,
    }
    assert set(_all_value_sinks(sanitized)) == {None}


@pytest.mark.parametrize(
    "quality",
    [complete_quality(), bounded_quality(), blocked_quality()],
)
def test_valid_automated_review_is_byte_for_byte_unchanged_across_bridge_decisions(
    quality: dict[str, Any],
) -> None:
    artifact = public_artifact(
        quality=quality, automated_review=_blocked_review()
    )
    before = json.dumps(artifact["automated_review"], separators=(",", ":"))

    sanitized = sanitize_public_artifact(artifact)

    after = json.dumps(sanitized["automated_review"], separators=(",", ":"))
    assert after == before
    assert sanitized["review"]["publication_state"] == "withheld"


def test_unsanitized_bounded_review_requires_finite_absolute_range() -> None:
    quality = bounded_quality()
    quality["intrinsic_value_range"] = _range(None, None, None, 0.005)
    artifact = public_artifact(quality=quality)

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert sanitized["bridge_quality"] == {
        "decision": "withheld",
        "complete": False,
        "usable": False,
        "bounded_fields": [],
        "blocking_fields": [],
        "reason_codes": ["BRIDGE_QUALITY_INVALID_OR_MISSING"],
        "intrinsic_value_range": _range(None, None, None, None),
    }
    assert set(_all_value_sinks(sanitized)) == {None}


def test_unsanitized_complete_bridge_requires_a_finite_point_range() -> None:
    artifact = public_artifact(quality=complete_quality(None))
    assert artifact["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["bridge_quality"]["reason_codes"] == [
        "BRIDGE_QUALITY_INVALID_OR_MISSING"
    ]
    assert sanitized["review"]["publication_state"] == "withheld"
    assert set(_all_value_sinks(sanitized)) == {None}


def test_fully_scrubbed_bounded_review_is_idempotent() -> None:
    artifact = public_artifact(
        quality=bounded_quality(), automated_review=_blocked_review()
    )

    once = sanitize_public_artifact(artifact)
    twice = sanitize_public_artifact(once)

    assert twice == once
    assert once["bridge_quality"]["decision"] == "bounded_review"
    assert once["bridge_quality"]["intrinsic_value_range"] == _range(
        None, None, None, 0.01
    )
    assert set(_all_value_sinks(once)) == {None}


def test_fully_scrubbed_complete_bridge_is_idempotent() -> None:
    artifact = public_artifact(
        quality=complete_quality(), automated_review=_blocked_review()
    )

    once = sanitize_public_artifact(artifact)
    twice = sanitize_public_artifact(once)

    assert twice == once
    assert once["bridge_quality"]["decision"] == "complete"
    assert once["bridge_quality"]["intrinsic_value_range"] == _range(
        None, None, None, 0.0
    )
    assert set(_all_value_sinks(once)) == {None}


def test_withheld_label_does_not_bypass_null_bounded_range_validation() -> None:
    quality = bounded_quality()
    quality["intrinsic_value_range"] = _range(None, None, None, 0.005)
    artifact = public_artifact(quality=quality, review_state="withheld")
    assert artifact["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["bridge_quality"]["reason_codes"] == [
        "BRIDGE_QUALITY_INVALID_OR_MISSING"
    ]
    assert sanitized["review"]["publication_state"] == "withheld"


def test_fcff_missing_automated_review_fails_closed_even_with_valid_bridge() -> None:
    artifact = public_artifact(quality=complete_quality())
    del artifact["automated_review"]

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["automated_review"]["decision"] == "blocked"
    assert sanitized["automated_review"]["blocking_reasons"] == [
        "invalid_automated_review_payload"
    ]
    assert sanitized["review"]["publication_state"] == "withheld"
    assert set(_all_value_sinks(sanitized)) == {None}


@pytest.mark.parametrize("fcff_surface", ["model", "scenario", "bridge"])
def test_fcff_surface_cannot_spoof_equity_policy_to_omit_automated_review(
    fcff_surface: str,
) -> None:
    artifact = public_artifact(quality=complete_quality())
    del artifact["automated_review"]
    artifact["model_policy"]["primary"] = "residual_income"
    if fcff_surface != "model":
        artifact["models"] = {
            "residual_income": {
                "publication_state": "pass",
                "intrinsic_value_per_share": 42.0,
            }
        }
    if fcff_surface != "scenario":
        artifact["scenarios"] = {}
    if fcff_surface != "bridge":
        del artifact["bridge_quality"]

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["automated_review"]["decision"] == "blocked"
    assert sanitized["review"]["publication_state"] == "withheld"
    assert set(_all_value_sinks(sanitized)) == {None}


def test_fcff_surface_must_agree_with_model_policy_even_with_valid_review() -> None:
    artifact = public_artifact(quality=complete_quality())
    artifact["model_policy"]["primary"] = "residual_income"

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert any("model policy" in error.lower() for error in sanitized["review"]["errors"])
    assert set(_all_value_sinks(sanitized)) == {None}


@pytest.mark.parametrize("fcff_surface", ["model", "scenario"])
def test_fcff_model_discriminator_cannot_hide_behind_renamed_key(
    fcff_surface: str,
) -> None:
    artifact = public_artifact(quality=complete_quality())
    del artifact["automated_review"]
    del artifact["bridge_quality"]
    artifact["model_policy"]["primary"] = "residual_income"
    if fcff_surface == "model":
        artifact["models"] = {
            "renamed_equity_model": {
                "model": "fcff_dcf",
                "publication_state": "pass",
                "intrinsic_value_per_share": 100.0,
            }
        }
        artifact["scenarios"] = {}
    else:
        artifact["models"] = {
            "residual_income": {
                "model": "residual_income",
                "publication_state": "pass",
                "intrinsic_value_per_share": 42.0,
            }
        }
        artifact["scenarios"] = {
            "base": {
                "renamed_equity_model": {
                    "model": "fcff_dcf",
                    "publication_state": "pass",
                    "intrinsic_value_per_share": 100.0,
                }
            }
        }

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["automated_review"]["decision"] == "blocked"
    assert sanitized["review"]["publication_state"] == "withheld"
    assert set(_all_value_sinks(sanitized)) == {None}


@pytest.mark.parametrize("location", ["model", "scenario"])
def test_model_key_and_discriminator_must_agree(location: str) -> None:
    artifact = public_artifact(quality=complete_quality())
    if location == "model":
        artifact["models"]["fcff_dcf"]["model"] = "residual_income"
    else:
        artifact["scenarios"]["stress"]["fcff_dcf"] = {
            "model": "residual_income",
            "publication_state": "pass",
            "intrinsic_value_per_share": 100.0,
        }

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert any("model" in error.lower() for error in sanitized["review"]["errors"])
    assert set(_all_value_sinks(sanitized)) == {None}


def test_bridge_midpoint_must_match_canonical_fcff_value() -> None:
    artifact = public_artifact(quality=complete_quality(331_839_000_000.0))
    assert artifact["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100.0

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["bridge_quality"]["reason_codes"] == [
        "BRIDGE_QUALITY_INVALID_OR_MISSING"
    ]
    assert sanitized["review"]["publication_state"] == "withheld"
    assert set(_all_value_sinks(sanitized)) == {None}


@pytest.mark.parametrize(
    "canonical_value",
    [None, True, float("nan"), float("inf"), float("-inf")],
)
def test_bridge_absolutes_require_finite_canonical_fcff_value(
    canonical_value: object,
) -> None:
    artifact = public_artifact(quality=bounded_quality())
    artifact["models"]["fcff_dcf"][
        "intrinsic_value_per_share"
    ] = canonical_value

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["bridge_quality"]["reason_codes"] == [
        "BRIDGE_QUALITY_INVALID_OR_MISSING"
    ]
    assert sanitized["review"]["publication_state"] == "withheld"


def test_bridge_absolutes_require_canonical_fcff_model() -> None:
    artifact = public_artifact(quality=bounded_quality())
    del artifact["models"]["fcff_dcf"]

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["bridge_quality"]["reason_codes"] == [
        "BRIDGE_QUALITY_INVALID_OR_MISSING"
    ]
    assert sanitized["review"]["publication_state"] == "withheld"


@pytest.mark.parametrize(
    ("model_state", "expected_review_state", "expected_midpoint"),
    [
        ("review_required", "review_required", 100.0),
        ("withheld", "withheld", None),
    ],
)
def test_canonical_fcff_state_constrains_review_and_bridge_range(
    model_state: str,
    expected_review_state: str,
    expected_midpoint: float | None,
) -> None:
    artifact = public_artifact(quality=complete_quality())
    artifact["models"]["fcff_dcf"]["publication_state"] = model_state

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == expected_review_state
    assert sanitized["bridge_quality"]["intrinsic_value_range"][
        "midpoint"
    ] == expected_midpoint


def _delete_decision(quality: dict[str, Any]) -> None:
    del quality["decision"]


def _set_unknown_decision(quality: dict[str, Any]) -> None:
    quality["decision"] = "attacker-decision"


def _set_string_usable(quality: dict[str, Any]) -> None:
    quality["usable"] = "true"


def _set_nonmapping_range(quality: dict[str, Any]) -> None:
    quality["intrinsic_value_range"] = [99.5, 100.0, 100.5]


def _set_nan_range(quality: dict[str, Any]) -> None:
    quality["intrinsic_value_range"]["low"] = float("nan")


def _set_infinite_ratio(quality: dict[str, Any]) -> None:
    quality["intrinsic_value_range"]["spread_ratio"] = float("inf")


def _reverse_range(quality: dict[str, Any]) -> None:
    quality["intrinsic_value_range"].update(
        {"low": 101.0, "midpoint": 100.0, "high": 99.0}
    )


def _set_nonpositive_midpoint(quality: dict[str, Any]) -> None:
    quality["intrinsic_value_range"].update(
        {"low": -1.0, "midpoint": 0.0, "high": 1.0}
    )


def _set_wrong_ratio(quality: dict[str, Any]) -> None:
    quality["intrinsic_value_range"]["spread_ratio"] = 0.009


def _set_wrong_limit(quality: dict[str, Any]) -> None:
    quality["intrinsic_value_range"]["spread_limit"] = 0.02


def _set_unknown_field(quality: dict[str, Any]) -> None:
    quality["bounded_fields"] = ["ATTACKER_PRIVATE_ACCOUNT"]


def _set_unknown_reason(quality: dict[str, Any]) -> None:
    quality["reason_codes"] = ["ATTACKER_PRIVATE_REASON"]


def _set_duplicate_field(quality: dict[str, Any]) -> None:
    quality["bounded_fields"] = [BRIDGE_FIELD, BRIDGE_FIELD]


def _set_duplicate_reason(quality: dict[str, Any]) -> None:
    quality["reason_codes"] = [
        "CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
        "CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
    ]


def _add_unknown_public_key(quality: dict[str, Any]) -> None:
    quality["raw_account_range"] = {"low": 1_000_000_000.0}


@pytest.mark.parametrize(
    "mutation",
    [
        _delete_decision,
        _set_unknown_decision,
        _set_string_usable,
        _set_nonmapping_range,
        _set_nan_range,
        _set_infinite_ratio,
        _reverse_range,
        _set_nonpositive_midpoint,
        _set_wrong_ratio,
        _set_wrong_limit,
        _set_unknown_field,
        _set_unknown_reason,
        _set_duplicate_field,
        _set_duplicate_reason,
        _add_unknown_public_key,
    ],
)
def test_malformed_public_bridge_quality_fails_closed_without_echo_or_raise(
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    quality = bounded_quality()
    mutation(quality)
    artifact = public_artifact(quality=quality)

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert sanitized["bridge_quality"] == {
        "decision": "withheld",
        "complete": False,
        "usable": False,
        "bounded_fields": [],
        "blocking_fields": [],
        "reason_codes": ["BRIDGE_QUALITY_INVALID_OR_MISSING"],
        "intrinsic_value_range": {
            "low": None,
            "midpoint": None,
            "high": None,
            "spread_ratio": None,
            "spread_limit": 0.01,
        },
    }
    serialized = json.dumps(sanitized)
    assert "ATTACKER_PRIVATE" not in serialized
    assert set(_all_value_sinks(sanitized)) == {None}


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("bridge_decision",), "attacker-decision"),
        (("bridge_complete",), "true"),
        (("bridge_can_value",), False),
        (("bridge_missing_fields",), [BRIDGE_FIELD, BRIDGE_FIELD]),
        (("bridge_bounded_fields",), ["ATTACKER_PRIVATE_ACCOUNT"]),
        (("bridge_uncertainty", "policy_version"), "ATTACKER-VERSION"),
        (("bridge_uncertainty", "spread_limit"), 0.005),
        (("bridge_uncertainty", "reason_codes"), ["ATTACKER_PRIVATE_REASON"]),
        (("bridge_uncertainty", "intrinsic_value_range", "low"), float("nan")),
    ],
)
def test_private_alias_and_assessment_mismatches_emit_only_generic_public_reason(
    private_aapl: dict[str, Any],
    submissions: dict[str, Any],
    path: tuple[str, ...],
    value: Any,
) -> None:
    private = _bounded_private(private_aapl)
    target = private["financials"]["balance_sheet"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    public = public_result(private, submissions)

    assert public["bridge_quality"]["reason_codes"] == [
        "BRIDGE_QUALITY_INVALID_OR_MISSING"
    ]
    assert public["review"]["publication_state"] == "withheld"
    assert "ATTACKER" not in json.dumps(public)


def test_private_bridge_unknown_keys_and_provenance_are_never_copied(
    private_aapl: dict[str, Any], submissions: dict[str, Any]
) -> None:
    private = _bounded_private(private_aapl)
    balance = private["financials"]["balance_sheet"]
    balance["bridge_uncertainty"]["future_private_key"] = {
        "availability": {"source_accession": "ATTACKER_ACCESSION"},
        "concept": "ATTACKER_CONCEPT",
        "account_range": {"low": 1_000_000_000.0, "high": 2_000_000_000.0},
        "shares": 3_000_000_000.0,
        "enterprise_value": 4_000_000_000.0,
    }

    public = public_result(private, submissions)

    assert public["bridge_quality"]["reason_codes"] == [
        "BRIDGE_QUALITY_INVALID_OR_MISSING"
    ]
    serialized = json.dumps(public)
    for token in (
        "future_private_key",
        "ATTACKER_ACCESSION",
        "ATTACKER_CONCEPT",
        "account_range",
        '"shares"',
        '"enterprise_value"',
    ):
        assert token not in serialized


def test_private_over_limit_reason_is_deduplicated_before_publication(
    private_aapl: dict[str, Any], submissions: dict[str, Any]
) -> None:
    private = deepcopy(private_aapl)
    _make_native_pass(private)
    low = 99.4999995
    midpoint = 100.0
    high = 100.5000005
    private["models"]["fcff_dcf"]["intrinsic_value_per_share"] = midpoint
    _install_private_assessment(
        private,
        decision="withheld",
        usable=False,
        low=low,
        midpoint=midpoint,
        high=high,
        spread_ratio=(high - low) / midpoint,
        blocking_fields=[],
        bounded_fields=[BRIDGE_FIELD],
        reason_codes=[
            "CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
            "JOINT_INTRINSIC_VALUE_SPREAD_EXCEEDS_LIMIT",
        ],
        warning=None,
    )

    public = public_result(private, submissions)

    assert public["bridge_quality"]["reason_codes"] == [
        "CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
        "JOINT_INTRINSIC_VALUE_SPREAD_EXCEEDS_LIMIT",
    ]
    assert public["bridge_quality"]["intrinsic_value_range"][
        "spread_ratio"
    ] == (high - low) / midpoint


def test_sanitizer_is_idempotent_immutable_and_deduplicates_messages() -> None:
    artifact = public_artifact(quality={"decision": "bad"})
    artifact["review"]["errors"] = [
        "Public bridge quality is invalid or missing; valuation was withheld.",
        "Public bridge quality is invalid or missing; valuation was withheld.",
    ]
    before = deepcopy(artifact)

    once = sanitize_public_artifact(artifact)
    twice = sanitize_public_artifact(once)

    assert artifact == before
    assert twice == once
    assert once["review"]["errors"].count(
        "Public bridge quality is invalid or missing; valuation was withheld."
    ) == 1


@pytest.mark.parametrize(
    "malformed",
    [
        {"models": []},
        {"models": {"fcff_dcf": "bad"}},
        {"scenarios": []},
        {"scenarios": {"base": []}},
        {"sensitivities": {}},
        {"sensitivities": ["bad"]},
        {"scenario_range": []},
    ],
)
def test_malformed_sink_containers_fail_closed_without_type_error(
    malformed: dict[str, Any],
) -> None:
    artifact = public_artifact(quality=complete_quality())
    artifact.update(malformed)

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"


def test_legacy_fcff_missing_quality_fails_closed_but_equity_is_not_applicable() -> None:
    fcff = public_artifact(quality=None)
    del fcff["automated_review"]

    equity = public_artifact(quality=None, review_state="review_required")
    del equity["automated_review"]
    equity["model_policy"] = {
        "primary": "residual_income",
        "reason": "intentional equity-level route",
    }
    equity["models"] = {
        "residual_income": {
            "publication_state": "review_required",
            "intrinsic_value_per_share": 42.0,
        }
    }
    equity["scenarios"] = {}

    fcff_public = sanitize_public_artifact(fcff)
    equity_public = sanitize_public_artifact(equity)

    assert fcff_public["review"]["publication_state"] == "withheld"
    assert fcff_public["bridge_quality"]["reason_codes"] == [
        "BRIDGE_QUALITY_INVALID_OR_MISSING"
    ]
    assert equity_public["review"]["publication_state"] == "review_required"
    assert "bridge_quality" not in equity_public
    assert equity_public["models"]["residual_income"][
        "intrinsic_value_per_share"
    ] == 42.0


def test_legacy_fcff_fallback_reason_remains_authoritative() -> None:
    artifact = public_artifact(quality=None, review_state="review_required")
    del artifact["automated_review"]
    artifact["model_policy"] = {
        "primary": "ddm",
        "fallback_from": "fcff_dcf",
        "reason": "legacy FCFF bridge fallback",
    }
    artifact["models"] = {
        "ddm": {
            "publication_state": "review_required",
            "intrinsic_value_per_share": 30.0,
        }
    }
    artifact["scenarios"] = {}

    sanitized = sanitize_public_artifact(artifact)

    assert sanitized["review"]["publication_state"] == "withheld"
    assert sanitized["models"]["ddm"]["intrinsic_value_per_share"] is None
    assert any(
        "legacy fcff fallback" in error.lower()
        for error in sanitized["review"]["errors"]
    )


def test_frontend_copy_uses_sanitized_bridge_quality_and_review_eligibility(
    private_aapl: dict[str, Any], submissions: dict[str, Any]
) -> None:
    private = _bounded_private(private_aapl)
    public = public_result(private, submissions)

    frontend = frontend_company(
        private,
        public,
        {
            "ticker": "AAPL",
            "short_name": "Apple",
            "subsector": "Hardware & electronic equipment",
            "insight": "test",
        },
    )

    assert frontend["valuation"]["us"]["bridge_quality"] == public[
        "bridge_quality"
    ]
    assert frontend["valuation"]["modelPolicy"]["publishable"] is True
    assert public["review"]["publication_state"] == "review_required"


def test_frontend_replay_recomputes_current_automated_review_and_is_idempotent(
    private_aapl: dict[str, Any], submissions: dict[str, Any]
) -> None:
    private = _bounded_private(private_aapl)
    public = public_result(private, submissions)
    public["bridge_quality"] = blocked_quality()
    public["review"]["publication_state"] = "pass"
    for model in public["models"].values():
        model["publication_state"] = "pass"
        model["intrinsic_value_per_share"] = 999.0
    automated_before = deepcopy(public["automated_review"])

    frontend = frontend_company(
        private,
        public,
        {
            "ticker": "AAPL",
            "short_name": "Apple",
            "subsector": "Hardware & electronic equipment",
            "insight": "test",
        },
    )
    replayed = frontend["valuation"]["us"]

    assert replayed["automated_review"] != automated_before
    assert replayed["automated_review"]["publication_state"] == "review_required"
    assert replayed["automated_review"]["blocking_reasons"] == []
    assert all(
        warning.startswith("Scenario ")
        for warning in replayed["automated_review"]["warnings"]
    )
    assert replayed["review"]["publication_state"] == "withheld"
    assert replayed["bridge_quality"]["intrinsic_value_range"]["low"] is None
    assert all(
        model["intrinsic_value_per_share"] is None
        for model in replayed["models"].values()
    )
    assert sanitize_public_artifact(replayed) == replayed
