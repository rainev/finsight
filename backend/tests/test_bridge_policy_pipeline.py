from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

import app.us_valuation.pipeline as valuation_pipeline
from app.us_valuation.bridge_policy import (
    BridgeResolution,
    assess_bridge_materiality,
    reconcile_bridge,
)
from app.us_valuation.field_availability import (
    FieldAvailability,
    UncertaintyRange,
)
from app.us_valuation.pipeline import build_us_valuation
from app.us_valuation.xbrl import CompanyFactsNormalizer


FIXTURES = Path(__file__).parent / "fixtures" / "us"
ORIGINAL_NORMALIZE = CompanyFactsNormalizer.normalize
ORIGINAL_DERIVE_FORECAST_ASSUMPTIONS = (
    valuation_pipeline.derive_forecast_assumptions
)
ORIGINAL_FCFF_DCF = valuation_pipeline.fcff_dcf
ORIGINAL_SCENARIO_SET = valuation_pipeline.scenario_set

AAPL_CASH_AND_INVESTMENTS = 146_595_000_000.0
AAPL_DEBT = 84_711_000_000.0
AAPL_SHARES = 14_744_753_000.0
AAPL_BASE_ENTERPRISE_VALUE = 1_863_743_821_068.4976
AAPL_BASE_EQUITY_VALUE = 1_925_627_821_068.4976
AAPL_BASE_INTRINSIC_VALUE = 130.59749600881733
AAPL_EPV_ENTERPRISE_VALUE = 1_286_498_182_222.9802
AAPL_EPV_EQUITY_VALUE = 1_348_382_182_222.9802
AAPL_EPV_INTRINSIC_VALUE = 91.44827195294354
AAPL_SCENARIO_VALUES = {
    "bear": 104.7201491751573,
    "base": 130.59749600881733,
    "bull": 166.40499480949893,
}
AAPL_SENSITIVITY_VALUES = [
    ("wacc", -0.01, 147.94065930200173),
    ("wacc", 0.01, 116.79105260002564),
    ("terminal_growth", -0.005, 128.7052924216841),
    ("terminal_growth", 0.005, 132.52824922873808),
    ("initial_revenue_growth", -0.02, 124.27430067346455),
    ("initial_revenue_growth", 0.02, 137.2140780143736),
    ("target_operating_margin", -0.02, 124.14850867657972),
    ("target_operating_margin", 0.02, 137.02712998362094),
]
TINY_BRIDGE_WARNING = (
    "Enterprise-to-equity bridge uses source-bounded uncertainty; "
    "the joint intrinsic-value spread is 0.00% and requires review."
)


def load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build_aapl() -> dict[str, Any]:
    return build_us_valuation(
        submissions=load_json("aapl-submissions.json"),
        companyfacts=load_json("aapl-companyfacts.json"),
        valuation_date="2026-08-01",
    )


def _availability(balance: dict[str, Any]) -> dict[str, FieldAvailability]:
    return {
        field: FieldAvailability.from_dict(payload)
        for field, payload in balance["availability"].items()
    }


def _replace_availability_record(
    financials: dict[str, Any],
    *,
    field: str,
    replacement: FieldAvailability,
) -> None:
    balance = financials["balance_sheet"]
    availability = _availability(balance)
    availability[field] = replacement
    balance["values"][field] = None
    balance["sources"][field] = {
        "value_status": replacement.state,
        "source_accession": replacement.source_accession,
        "source_kind": replacement.source_kind,
        "evidence_class": replacement.evidence_class,
        "reason_code": replacement.reason_code,
    }
    balance["field_states"][field] = replacement.state
    resolution = reconcile_bridge(
        availability,
        fully_diluted_shares=balance["fully_diluted_shares_proxy"],
    )
    balance["availability"] = {
        name: item.as_dict() for name, item in availability.items()
    }
    balance.update(resolution.as_balance_sheet_fields())


def _install_aapl_record(
    monkeypatch: pytest.MonkeyPatch,
    *,
    field: str,
    replacement: Callable[[dict[str, Any], FieldAvailability], FieldAvailability],
) -> None:
    def normalize_with_record(
        self: CompanyFactsNormalizer,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        financials = ORIGINAL_NORMALIZE(self, *args, **kwargs)
        balance = financials["balance_sheet"]
        original = _availability(balance)[field]
        _replace_availability_record(
            financials,
            field=field,
            replacement=replacement(balance, original),
        )
        return financials

    monkeypatch.setattr(CompanyFactsNormalizer, "normalize", normalize_with_record)


def install_bounded_aapl_normalizer(
    monkeypatch: pytest.MonkeyPatch,
    *,
    field: str,
    low: float,
    high: float,
) -> None:
    def bounded_record(
        balance: dict[str, Any],
        original: FieldAvailability,
    ) -> FieldAvailability:
        assert original.source_accession is not None
        return FieldAvailability(
            field=field,
            value=None,
            state="bounded_unresolved",
            reason_code="TEST_CURRENT_NOTE_RANGE",
            period_end=balance["period_end"],
            source_accession=original.source_accession,
            source_kind="test_current_filing_note",
            evidence_class="reported_range",
            freshness="current",
            uncertainty=UncertaintyRange(
                low=low,
                high=high,
                basis="Hand-checked integration-test filing range.",
                source_accessions=(original.source_accession,),
            ),
        )

    _install_aapl_record(
        monkeypatch,
        field=field,
        replacement=bounded_record,
    )


def install_unavailable_aapl_normalizer(
    monkeypatch: pytest.MonkeyPatch,
    *,
    field: str,
    state: str,
    reason_code: str,
) -> None:
    def unavailable_record(
        balance: dict[str, Any],
        original: FieldAvailability,
    ) -> FieldAvailability:
        keep_source = state in {"stale", "conflict", "not_disclosed"}
        return FieldAvailability(
            field=field,
            value=None,
            state=state,
            reason_code=reason_code,
            period_end=balance["period_end"],
            source_accession=(
                original.source_accession if keep_source else None
            ),
            source_kind=original.source_kind if keep_source else None,
            evidence_class=state if keep_source else None,
            freshness="stale" if state == "stale" else "unknown",
        )

    _install_aapl_record(
        monkeypatch,
        field=field,
        replacement=unavailable_record,
    )


def install_tampered_blocked_aapl_normalizer(
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    field = "marketable_securities_noncurrent"

    def normalize_with_tampered_aliases(
        self: CompanyFactsNormalizer,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        financials = ORIGINAL_NORMALIZE(self, *args, **kwargs)
        balance = financials["balance_sheet"]
        original = _availability(balance)[field]
        _replace_availability_record(
            financials,
            field=field,
            replacement=FieldAvailability(
                field=field,
                value=None,
                state="conflict",
                reason_code="TEST_AUTHORITATIVE_CONFLICT",
                period_end=balance["period_end"],
                source_accession=original.source_accession,
                source_kind=original.source_kind,
                evidence_class="conflict",
                freshness="unknown",
            ),
        )
        balance.update(
            {
                "bridge_complete": True,
                "bridge_can_value": True,
                "bridge_usable": True,
                "bridge_decision": "complete",
                "bridge_missing_fields": [],
                "bridge_blocking_fields": [],
                "bridge_bounded_fields": [],
            }
        )
        return financials

    monkeypatch.setattr(
        CompanyFactsNormalizer,
        "normalize",
        normalize_with_tampered_aliases,
    )
    return field


def install_tampered_bounded_aapl_normalizer(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[str, dict[str, Any]]:
    field = "marketable_securities_noncurrent"
    canonical_precheck: dict[str, Any] = {}

    def normalize_with_tampered_aliases(
        self: CompanyFactsNormalizer,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        financials = ORIGINAL_NORMALIZE(self, *args, **kwargs)
        balance = financials["balance_sheet"]
        availability = _availability(balance)
        original = availability[field]
        assert original.source_accession is not None
        _replace_availability_record(
            financials,
            field=field,
            replacement=FieldAvailability(
                field=field,
                value=None,
                state="bounded_unresolved",
                reason_code="TEST_CURRENT_NOTE_RANGE",
                period_end=balance["period_end"],
                source_accession=original.source_accession,
                source_kind="test_current_filing_note",
                evidence_class="reported_range",
                freshness="current",
                uncertainty=UncertaintyRange(
                    low=78_087_500_000.0,
                    high=78_088_500_000.0,
                    basis="Hand-checked integration-test filing range.",
                    source_accessions=(original.source_accession,),
                ),
            ),
        )
        canonical_precheck.update(balance["bridge_precheck"])
        balance["bridge_precheck"]["missing_fields"] = [field, field]
        balance["bridge_precheck"]["bounded_fields"] = [field, field]
        balance.update(
            {
                "cash_and_nonoperating_investments": 1_146_595_000_000.0,
                "total_interest_bearing_debt": 1.0,
                "preferred_equity": 250_000_000_000.0,
                "noncontrolling_interests": 125_000_000_000.0,
                "fully_diluted_shares_proxy": 1.0,
                "bridge_complete": True,
                "bridge_can_value": False,
                "bridge_usable": True,
                "bridge_decision": "complete",
                "bridge_missing_fields": [],
                "bridge_blocking_fields": ["cash"],
                "bridge_bounded_fields": [],
            }
        )
        return financials

    monkeypatch.setattr(
        CompanyFactsNormalizer,
        "normalize",
        normalize_with_tampered_aliases,
    )
    return field, canonical_precheck


def publication_states(result: dict[str, Any]) -> list[str]:
    return [
        *(model["publication_state"] for model in result["models"].values()),
        *(
            scenario["fcff_dcf"]["publication_state"]
            for scenario in result["scenarios"].values()
        ),
        *(row["publication_state"] for row in result["sensitivities"]),
        result["review"]["publication_state"],
    ]


def assert_bridge_warning_placement(
    result: dict[str, Any],
    warning: str,
) -> None:
    assert result["review"]["warnings"].count(warning) == 1
    for model in result["models"].values():
        assert model["warnings"].count(warning) == 1
    for scenario in result["scenarios"].values():
        assert scenario["fcff_dcf"]["warnings"].count(warning) == 1
    assert all("warnings" not in row for row in result["sensitivities"])


def install_invalid_base_assumptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def assumptions_with_invalid_base_roic(
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        assumptions = ORIGINAL_DERIVE_FORECAST_ASSUMPTIONS(*args, **kwargs)
        assumptions["initial_marginal_roic"] = 0.0
        return assumptions

    monkeypatch.setattr(
        valuation_pipeline,
        "derive_forecast_assumptions",
        assumptions_with_invalid_base_roic,
    )


def test_complete_real_fixture_preserves_exact_native_values_and_states() -> None:
    result = build_aapl()
    balance = result["financials"]["balance_sheet"]

    assert balance["bridge_complete"] is True
    assert balance["bridge_can_value"] is True
    assert balance["bridge_usable"] is True
    assert balance["bridge_decision"] == "complete"
    assert balance["bridge_missing_fields"] == []
    assert balance["bridge_blocking_fields"] == []
    assert balance["bridge_bounded_fields"] == []
    assert balance["cash_and_nonoperating_investments"] == AAPL_CASH_AND_INVESTMENTS
    assert balance["total_interest_bearing_debt"] == AAPL_DEBT
    assert balance["preferred_equity"] == 0.0
    assert balance["noncontrolling_interests"] == 0.0
    assert balance["fully_diluted_shares_proxy"] == AAPL_SHARES
    assert "total_interest_bearing_debt" not in balance["availability"]

    base = result["models"]["fcff_dcf"]
    assert base["enterprise_value"] == AAPL_BASE_ENTERPRISE_VALUE
    assert base["equity_value"] == AAPL_BASE_EQUITY_VALUE
    assert base["intrinsic_value_per_share"] == AAPL_BASE_INTRINSIC_VALUE
    assert base["publication_state"] == "pass"
    assert base["errors"] == []
    assert base["warnings"] == []

    epv = result["models"]["epv"]
    assert epv["enterprise_value"] == AAPL_EPV_ENTERPRISE_VALUE
    assert epv["equity_value"] == AAPL_EPV_EQUITY_VALUE
    assert epv["intrinsic_value_per_share"] == AAPL_EPV_INTRINSIC_VALUE
    assert epv["publication_state"] == "review_required"

    assert {
        name: scenario["fcff_dcf"]["intrinsic_value_per_share"]
        for name, scenario in result["scenarios"].items()
    } == AAPL_SCENARIO_VALUES
    assert all(
        scenario["fcff_dcf"]["publication_state"] == "pass"
        for scenario in result["scenarios"].values()
    )
    assert result["scenario_range"] == {
        "low": AAPL_SCENARIO_VALUES["bear"],
        "base": AAPL_SCENARIO_VALUES["base"],
        "high": AAPL_SCENARIO_VALUES["bull"],
        "label": "assumption range, not a statistical confidence interval",
    }
    assert [
        (row["field"], row["delta"], row["intrinsic_value_per_share"])
        for row in result["sensitivities"]
    ] == AAPL_SENSITIVITY_VALUES
    assert all(
        row["publication_state"] == "pass"
        for row in result["sensitivities"]
    )
    assert result["review"]["publication_state"] == "review_required"
    assert result["review"]["errors"] == []
    assert not any(
        "bridge" in message.lower()
        for message in [
            *result["review"]["warnings"],
            *result["review"]["errors"],
            *base["warnings"],
            *base["errors"],
        ]
    )
    assert balance["bridge_uncertainty"]["decision"] == "complete"
    assert balance["bridge_uncertainty"]["warning"] is None


def test_complete_bridge_stays_complete_when_native_base_is_withheld(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_invalid_base_assumptions(monkeypatch)

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]

    assert result["models"]["fcff_dcf"]["publication_state"] == "withheld"
    assert "enterprise_value" not in result["models"]["fcff_dcf"]
    assert balance["bridge_complete"] is True
    assert balance["bridge_can_value"] is True
    assert balance["bridge_usable"] is True
    assert balance["bridge_decision"] == "complete"
    assert balance["bridge_uncertainty"]["decision"] == "complete"
    assert balance["bridge_uncertainty"]["spread_ratio"] == 0.0
    assert result["review"]["publication_state"] == "withheld"
    assert not any(
        "Enterprise-to-equity bridge is withheld" in error
        for error in result["review"]["errors"]
    )


@pytest.mark.parametrize(
    ("state", "reason_code"),
    [
        ("unresolved", "TEST_MISSING_CURRENT_FACT"),
        ("stale", "TEST_STALE_CURRENT_FACT"),
        ("conflict", "TEST_CONFLICTING_CURRENT_FACTS"),
        ("not_disclosed", "TEST_UNBOUNDED_CURRENT_NOTE"),
    ],
)
def test_precheck_blockers_stop_before_forecast_and_models(
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    reason_code: str,
) -> None:
    field = "marketable_securities_noncurrent"
    install_unavailable_aapl_normalizer(
        monkeypatch,
        field=field,
        state=state,
        reason_code=reason_code,
    )

    def unexpected(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("forecast or valuation model executed after bridge blocker")

    for name in (
        "load_issuer_forecast_evidence",
        "derive_forecast_assumptions",
        "fcff_dcf",
        "earnings_power_value",
        "scenario_set",
        "one_way_sensitivities",
    ):
        monkeypatch.setattr(valuation_pipeline, name, unexpected)

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]

    assert balance["bridge_complete"] is False
    assert balance["bridge_can_value"] is False
    assert balance["bridge_usable"] is False
    assert balance["bridge_decision"] == "withheld"
    assert balance["bridge_missing_fields"] == [field]
    assert balance["bridge_blocking_fields"] == [field]
    assert balance["bridge_bounded_fields"] == []
    assert balance["bridge_precheck"]["reason_codes"] == [reason_code]
    assert result["models"]["fcff_dcf"]["publication_state"] == "withheld"
    assert result["models"]["fcff_dcf"]["intrinsic_value_per_share"] is None
    assert result["models"]["epv"]["publication_state"] == "withheld"
    assert result["models"]["epv"]["intrinsic_value_per_share"] is None
    assert result["scenarios"] == {}
    assert result["sensitivities"] == []
    assert result["review"]["publication_state"] == "withheld"
    assert field in " ".join(result["review"]["errors"])


def test_blocked_precheck_ignores_permissive_aliases_and_restores_canonical_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    field = install_tampered_blocked_aapl_normalizer(monkeypatch)

    def unexpected(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("forecast executed despite authoritative blocked precheck")

    monkeypatch.setattr(
        valuation_pipeline,
        "load_issuer_forecast_evidence",
        unexpected,
    )
    monkeypatch.setattr(
        valuation_pipeline,
        "derive_forecast_assumptions",
        unexpected,
    )

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]

    assert balance["bridge_precheck"]["can_value"] is False
    assert balance["bridge_complete"] is False
    assert balance["bridge_can_value"] is False
    assert balance["bridge_usable"] is False
    assert balance["bridge_decision"] == "withheld"
    assert balance["bridge_missing_fields"] == [field]
    assert balance["bridge_blocking_fields"] == [field]
    assert balance["bridge_bounded_fields"] == []
    assert result["review"]["publication_state"] == "withheld"
    assert field in " ".join(result["review"]["errors"])


def test_validated_precheck_canonicalizes_all_model_and_compatibility_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    field, canonical_precheck = install_tampered_bounded_aapl_normalizer(
        monkeypatch
    )

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]
    base = result["models"]["fcff_dcf"]

    assert balance["bridge_precheck"] == canonical_precheck
    assert balance["cash_and_nonoperating_investments"] == AAPL_CASH_AND_INVESTMENTS
    assert balance["total_interest_bearing_debt"] == AAPL_DEBT
    assert balance["preferred_equity"] == 0.0
    assert balance["noncontrolling_interests"] == 0.0
    assert balance["fully_diluted_shares_proxy"] == AAPL_SHARES
    assert balance["bridge_complete"] is False
    assert balance["bridge_can_value"] is True
    assert balance["bridge_usable"] is True
    assert balance["bridge_decision"] == "bounded_review"
    assert balance["bridge_missing_fields"] == [field]
    assert balance["bridge_blocking_fields"] == []
    assert balance["bridge_bounded_fields"] == [field]
    assert base["enterprise_value"] == AAPL_BASE_ENTERPRISE_VALUE
    assert base["equity_value"] == AAPL_BASE_EQUITY_VALUE
    assert base["intrinsic_value_per_share"] == AAPL_BASE_INTRINSIC_VALUE
    assert balance["bridge_uncertainty"]["intrinsic_value_range"][
        "midpoint"
    ] == pytest.approx(AAPL_BASE_INTRINSIC_VALUE)
    assert publication_states(result) == ["review_required"] * 14


def test_bounded_asset_midpoint_runs_and_caps_every_publication_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    field = "marketable_securities_noncurrent"
    install_bounded_aapl_normalizer(
        monkeypatch,
        field=field,
        low=78_087_500_000.0,
        high=78_088_500_000.0,
    )

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]
    assessment = balance["bridge_uncertainty"]

    assert balance["values"][field] is None
    assert balance["availability"][field]["value"] is None
    assert balance["availability"][field]["uncertainty"] == {
        "low": 78_087_500_000.0,
        "high": 78_088_500_000.0,
        "basis": "Hand-checked integration-test filing range.",
        "source_accessions": [
            balance["availability"][field]["source_accession"]
        ],
    }
    assert balance["cash_and_nonoperating_investments"] == AAPL_CASH_AND_INVESTMENTS
    assert balance["total_interest_bearing_debt"] == AAPL_DEBT
    assert balance["bridge_complete"] is False
    assert balance["bridge_can_value"] is True
    assert balance["bridge_usable"] is True
    assert balance["bridge_decision"] == "bounded_review"
    assert balance["bridge_missing_fields"] == [field]
    assert balance["bridge_blocking_fields"] == []
    assert balance["bridge_bounded_fields"] == [field]
    assert assessment["spread_ratio"] <= 0.01
    assert result["models"]["fcff_dcf"]["enterprise_value"] == (
        AAPL_BASE_ENTERPRISE_VALUE
    )
    assert result["models"]["fcff_dcf"]["equity_value"] == (
        AAPL_BASE_EQUITY_VALUE
    )
    assert result["models"]["fcff_dcf"]["intrinsic_value_per_share"] == (
        AAPL_BASE_INTRINSIC_VALUE
    )
    assert publication_states(result) == ["review_required"] * 14
    assert TINY_BRIDGE_WARNING == assessment["warning"]
    assert_bridge_warning_placement(result, TINY_BRIDGE_WARNING)


def test_bounded_liability_midpoint_reduces_equity_not_enterprise_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    field = "noncurrent_debt"
    install_bounded_aapl_normalizer(
        monkeypatch,
        field=field,
        low=74_405_000_000.0,
        high=74_407_000_000.0,
    )

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]
    base = result["models"]["fcff_dcf"]
    expected_debt_increase = 2_000_000.0

    assert balance["values"][field] is None
    assert balance["availability"][field]["value"] is None
    assert balance["total_interest_bearing_debt"] == (
        AAPL_DEBT + expected_debt_increase
    )
    assert "total_interest_bearing_debt" not in balance["availability"]
    assert base["enterprise_value"] == AAPL_BASE_ENTERPRISE_VALUE
    assert base["equity_value"] == (
        AAPL_BASE_EQUITY_VALUE - expected_debt_increase
    )
    assert base["intrinsic_value_per_share"] == (
        (AAPL_BASE_EQUITY_VALUE - expected_debt_increase) / AAPL_SHARES
    )
    assert balance["bridge_decision"] == "bounded_review"
    assert publication_states(result) == ["review_required"] * 14


def test_bounded_over_limit_withholds_all_states_but_keeps_private_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    field = "marketable_securities_noncurrent"
    install_bounded_aapl_normalizer(
        monkeypatch,
        field=field,
        low=0.0,
        high=1_000_000_000_000.0,
    )

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]
    assessment = balance["bridge_uncertainty"]

    assert balance["values"][field] is None
    assert balance["bridge_usable"] is False
    assert balance["bridge_decision"] == "withheld"
    assert assessment["spread_ratio"] > 0.01
    assert assessment["spread_limit"] == 0.01
    assert assessment["bounded_fields"] == [field]
    assert set(publication_states(result)) == {"withheld"}
    assert result["models"]["fcff_dcf"]["enterprise_value"] == (
        AAPL_BASE_ENTERPRISE_VALUE
    )
    assert result["models"]["fcff_dcf"]["intrinsic_value_per_share"] is not None
    assert result["models"]["epv"]["intrinsic_value_per_share"] is not None
    assert result["scenario_range"]["low"] is not None
    review_error = " ".join(result["review"]["errors"])
    assert "Enterprise-to-equity bridge is withheld" in review_error
    assert "spread_ratio=" in review_error
    assert "spread_limit=0.01" in review_error
    assert field in review_error


def test_bounded_review_never_promotes_a_native_withheld_scenario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_bounded_aapl_normalizer(
        monkeypatch,
        field="marketable_securities_noncurrent",
        low=78_087_500_000.0,
        high=78_088_500_000.0,
    )

    def scenario_with_native_withholding(*args: Any, **kwargs: Any) -> dict[str, Any]:
        scenarios = ORIGINAL_SCENARIO_SET(*args, **kwargs)
        scenarios["bear"]["fcff_dcf"]["publication_state"] = "withheld"
        scenarios["bear"]["fcff_dcf"]["errors"].append(
            "TEST_NATIVE_SCENARIO_WITHHELD"
        )
        return scenarios

    monkeypatch.setattr(
        valuation_pipeline,
        "scenario_set",
        scenario_with_native_withholding,
    )

    result = build_aapl()

    assert result["financials"]["balance_sheet"]["bridge_decision"] == (
        "bounded_review"
    )
    assert result["scenarios"]["bear"]["fcff_dcf"]["publication_state"] == (
        "withheld"
    )
    assert "TEST_NATIVE_SCENARIO_WITHHELD" in result["scenarios"]["bear"][
        "fcff_dcf"
    ]["errors"]
    assert all(state != "pass" for state in publication_states(result))
    assert_bridge_warning_placement(result, TINY_BRIDGE_WARNING)


def test_bounded_bridge_without_base_enterprise_value_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_bounded_aapl_normalizer(
        monkeypatch,
        field="marketable_securities_noncurrent",
        low=78_087_500_000.0,
        high=78_088_500_000.0,
    )

    install_invalid_base_assumptions(monkeypatch)

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]
    assessment = balance["bridge_uncertainty"]

    assert "enterprise_value" not in result["models"]["fcff_dcf"]
    assert assessment["decision"] == "withheld"
    assert assessment["usable"] is False
    assert assessment["intrinsic_value_range"] is None
    assert assessment["spread_ratio"] is None
    assert "BASE_ENTERPRISE_VALUE_UNAVAILABLE" in assessment["reason_codes"]
    assert set(publication_states(result)) == {"withheld"}
    assert result["models"]["epv"]["intrinsic_value_per_share"] is not None
    review_error = " ".join(result["review"]["errors"])
    assert "BASE_ENTERPRISE_VALUE_UNAVAILABLE" in review_error
    assert "spread_ratio=None" in review_error
    assert "spread_limit=0.01" in review_error


@pytest.mark.parametrize(
    "enterprise_value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_bounded_bridge_with_nonfinite_base_enterprise_value_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    enterprise_value: float,
) -> None:
    install_bounded_aapl_normalizer(
        monkeypatch,
        field="marketable_securities_noncurrent",
        low=78_087_500_000.0,
        high=78_088_500_000.0,
    )

    def fcff_with_nonfinite_enterprise_value(
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        base = ORIGINAL_FCFF_DCF(*args, **kwargs)
        base["enterprise_value"] = enterprise_value
        return base

    monkeypatch.setattr(
        valuation_pipeline,
        "fcff_dcf",
        fcff_with_nonfinite_enterprise_value,
    )

    result = build_aapl()
    assessment = result["financials"]["balance_sheet"]["bridge_uncertainty"]

    assert assessment["decision"] == "withheld"
    assert assessment["usable"] is False
    assert assessment["intrinsic_value_range"] is None
    assert assessment["spread_ratio"] is None
    assert "BASE_ENTERPRISE_VALUE_UNAVAILABLE" in assessment["reason_codes"]
    assert publication_states(result) == ["withheld"] * 14


def test_base_fcff_is_the_single_run_level_materiality_discriminator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_bounded_aapl_normalizer(
        monkeypatch,
        field="marketable_securities_noncurrent",
        low=70_000_000_000.0,
        high=85_000_000_000.0,
    )

    result = build_aapl()
    balance = result["financials"]["balance_sheet"]
    resolution = BridgeResolution.from_dict(balance["bridge_precheck"])
    independent_epv_assessment = assess_bridge_materiality(
        resolution,
        enterprise_value=result["models"]["epv"]["enterprise_value"],
    )

    assert balance["bridge_uncertainty"]["spread_ratio"] <= 0.01
    assert balance["bridge_decision"] == "bounded_review"
    assert independent_epv_assessment.spread_ratio is not None
    assert independent_epv_assessment.spread_ratio > 0.01
    assert independent_epv_assessment.decision == "withheld"
    assert result["models"]["epv"]["publication_state"] == "review_required"
    assert all(state != "pass" for state in publication_states(result))
