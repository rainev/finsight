import json

from scripts.rebuild_us_model_routes import (
    evaluate_route_candidate,
    quarantine_route_technical_failure,
)


def test_route_rebuild_accepts_only_an_actual_governed_model_change() -> None:
    old = {
        "issuer": {"ticker": "TEST", "primary_archetype": "us_utility"},
        "model_policy": {"primary": "ddm"},
    }
    private = {
        "issuer": {"ticker": "TEST", "primary_archetype": "energy_infrastructure"},
        "model_policy": {"primary": "fcff_dcf"},
    }
    public = {
        "issuer": {"ticker": "TEST", "primary_archetype": "energy_infrastructure"},
        "model_policy": {"primary": "fcff_dcf"},
        "models": {"fcff_dcf": {"intrinsic_value_per_share": None}},
    }

    accepted, reasons = evaluate_route_candidate(old, private, public)

    assert accepted is True
    assert reasons == ()


def test_route_rebuild_rejects_unchanged_or_fallback_candidate() -> None:
    old = {
        "issuer": {"ticker": "TEST", "primary_archetype": "us_utility"},
        "model_policy": {"primary": "ddm"},
    }
    private = {
        "issuer": {"ticker": "TEST", "primary_archetype": "us_utility"},
        "model_policy": {"primary": "ddm", "fallback_from": "fcff_dcf"},
    }
    public = {
        "issuer": {"ticker": "TEST", "primary_archetype": "us_utility"},
        "model_policy": {"primary": "ddm", "fallback_from": "fcff_dcf"},
        "models": {"ddm": {"intrinsic_value_per_share": None}},
    }

    accepted, reasons = evaluate_route_candidate(old, private, public)

    assert accepted is False
    assert "route_unchanged" in reasons
    assert "legacy_fallback" in reasons


def test_route_technical_failure_replaces_wrong_model_with_value_free_lane(tmp_path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    old = {
        "currency": "USD",
        "issuer": {"ticker": "TEST", "primary_archetype": "us_insurance"},
        "model_policy": {"primary": "residual_income"},
        "models": {"residual_income": {"intrinsic_value_per_share": 42.0}},
        "scenarios": {},
        "review": {"publication_state": "review_required"},
    }
    (data / "TEST.json").write_text(json.dumps(old))
    classification = {
        "ticker": "TEST",
        "finsight_sector": "Financials",
        "primary_archetype": "insurance_brokerage",
        "secondary_archetypes": [],
        "classification_confidence": 0.95,
        "mapping_version": "US-ARCHETYPE-1.1",
        "classification_reason": "issuer reviewed",
        "model_route_eligible": True,
        "model_route_reason": "issuer reviewed",
        "valuation_policy": {
            "primary_model": "fcff_dcf",
            "supporting_models": ["epv"],
            "model_policy_reason": "broker FCFF",
        },
    }

    quarantine_route_technical_failure(
        "TEST",
        reason="technical_error:ValueError:Missing annual fact for operating_income",
        classification=classification,
        data_root=data,
    )

    result = json.loads((data / "TEST.json").read_text())
    assert result["issuer"]["primary_archetype"] == "insurance_brokerage"
    assert result["model_policy"]["primary"] == "fcff_dcf"
    assert result["models"]["fcff_dcf"]["intrinsic_value_per_share"] is None
    assert result["review"]["publication_state"] == "withheld"
