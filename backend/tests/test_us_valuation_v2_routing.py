"""Routing-safety tests for the U.S. valuation V2 lane."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

import app.us_valuation.pipeline as valuation_pipeline
from app.us_valuation.classification import classify_issuer, load_archetype_config
from app.us_valuation.eligibility import model_eligibility
from app.us_valuation.artifacts import public_result, sanitize_public_artifact


FIXTURES = Path(__file__).parent / "fixtures" / "us"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def classification_for(archetype: str, model: str) -> dict:
    return {
        "primary_archetype": archetype,
        "valuation_policy": {"primary_model": model},
    }


def submissions_for(*, cik: str, ticker: str, sic: int, description: str) -> dict:
    return {
        "cik": cik,
        "tickers": [ticker],
        "name": ticker,
        "sic": sic,
        "sicDescription": description,
        "filings": {"recent": {}},
    }


@pytest.mark.parametrize(
    ("cik", "ticker", "sic", "archetype", "model"),
    [
        ("0001506307", "KMI", 4922, "energy_infrastructure", "fcff_dcf"),
        ("0001060391", "RSG", 4953, "environmental_services", "fcff_dcf"),
        ("0001692819", "VST", 4911, "independent_power_producer", "fcff_dcf"),
        ("0001138118", "CBRE", 6500, "real_estate_services", "fcff_dcf"),
        ("0000004904", "AEP", 4911, "us_utility", "ddm"),
        ("0001053507", "AMT", 6798, "us_reit", "ffo"),
    ],
)
def test_issuer_level_routes_override_broad_utility_and_real_estate_sic_bands(
    cik: str, ticker: str, sic: int, archetype: str, model: str
) -> None:
    classification = classify_issuer(
        submissions_for(cik=cik, ticker=ticker, sic=sic, description="fixture")
    )

    assert classification["primary_archetype"] == archetype
    assert classification["valuation_policy"]["primary_model"] == model
    assert classification["model_route_eligible"] is True
    assert classification["override_applied"] is True
    assert model_eligibility(classification)["eligible"] is True


@pytest.mark.parametrize("sic", [4911, 4924, 6500])
def test_unreviewed_broad_utility_and_real_estate_routes_fail_closed(sic: int) -> None:
    classification = classify_issuer(
        submissions_for(
            cik="0000123456", ticker="TEST", sic=sic, description="broad band"
        )
    )

    result = model_eligibility(classification)

    assert classification["model_route_eligible"] is False
    assert result["eligible"] is False
    assert "issuer-level" in result["reason"].lower()


def test_stale_broad_sic_artifact_is_withheld_when_current_route_changed() -> None:
    rebuilt = json.loads(
        (Path(__file__).parents[1] / "app/data/us_valuations/KMI.json").read_text()
    )

    public = sanitize_public_artifact(rebuilt)

    assert public["issuer"]["primary_archetype"] == "energy_infrastructure"
    assert public["model_policy"]["primary"] == "fcff_dcf"
    assert public["review"]["publication_state"] == "withheld"
    assert public["scenario_range"]["base"] is None
    assert public["models"]["fcff_dcf"]["intrinsic_value_per_share"] is None


def test_every_checked_in_broad_band_issuer_has_one_explicit_route_decision() -> None:
    config = load_archetype_config()
    grouped_ciks = [
        cik
        for group in config["model_routing_groups"]
        for cik in group["issuers"]
    ]
    assert len(grouped_ciks) == len(set(grouped_ciks))

    data_root = Path(__file__).parents[1] / "app/data/us_valuations"
    for path in data_root.glob("*.json"):
        issuer = json.loads(path.read_text())["issuer"]
        raw_sic = issuer.get("sec_sic_code")
        if raw_sic is None:
            continue
        sic = int(raw_sic)
        if not (4900 <= sic <= 4991 or 6500 <= sic <= 6799):
            continue
        classification = classify_issuer(
            submissions_for(
                cik=issuer["cik"],
                ticker=issuer["ticker"],
                sic=sic,
                description=issuer["sec_sic_label"],
            )
        )
        assert classification["override_applied"] is True, issuer["ticker"]
        assert classification["model_route_eligible"] is True, issuer["ticker"]


@pytest.mark.parametrize(
    ("archetype", "model", "expected"),
    [
        ("us_bank", "residual_income", True),
        ("us_utility", "ddm", True),
        ("us_reit", "ffo", True),
        ("enterprise_software_cloud", "fcff_dcf", True),
        ("enterprise_software_cloud", "residual_income", False),
        ("enterprise_software_cloud", "ddm", False),
    ],
)
def test_model_eligibility_matches_archetype_model_pair(
    archetype: str, model: str, expected: bool
) -> None:
    result = model_eligibility(classification_for(archetype, model))

    assert result["eligible"] is expected
    assert result["model"] == model
    assert result["reason"]


def test_every_configured_archetype_has_one_governed_primary_model() -> None:
    policies = load_archetype_config()["valuation_policies"]

    assert policies
    for archetype, policy in policies.items():
        model = policy["primary_model"]
        result = model_eligibility(classification_for(archetype, model))
        assert result["eligible"] is True


@pytest.mark.parametrize(
    ("archetype", "model"),
    [
        ("enterprise_software_cloud", "fcff_dcf"),
        ("semiconductors_and_components", "fcff_dcf"),
        ("us_bank", "residual_income"),
        ("us_insurance", "residual_income"),
        ("us_reit", "ffo"),
        ("us_utility", "ddm"),
        ("diversified_industrials", "fcff_dcf"),
        ("capital_goods_machinery", "fcff_dcf"),
    ],
)
def test_requested_company_types_use_governed_models(
    archetype: str, model: str
) -> None:
    result = model_eligibility(classification_for(archetype, model))

    assert result["eligible"] is True


@pytest.mark.parametrize(
    ("cik", "ticker", "sic", "archetype", "model"),
    [
        ("0001024478", "ROK", 3829, "capital_goods_machinery", "fcff_dcf"),
        ("0000874716", "IDXX", 2835, "medical_devices_instruments", "fcff_dcf"),
        ("0000089800", "SHW", 5231, "specialty_chemicals", "fcff_dcf"),
        ("0000315293", "AON", 6411, "insurance_brokerage", "fcff_dcf"),
        ("0000354190", "AJG", 6411, "insurance_brokerage", "fcff_dcf"),
    ],
)
def test_issuer_reviewed_business_models_override_misleading_sic_routes(
    cik: str, ticker: str, sic: int, archetype: str, model: str
) -> None:
    classification = classify_issuer(
        submissions_for(cik=cik, ticker=ticker, sic=sic, description="fixture")
    )

    assert classification["primary_archetype"] == archetype
    assert classification["valuation_policy"]["primary_model"] == model
    assert model_eligibility(classification)["eligible"] is True


def test_coinbase_is_routed_to_a_dedicated_withheld_model_lane() -> None:
    classification = classify_issuer(
        submissions_for(
            cik="0001679788", ticker="COIN", sic=6199, description="Finance Services"
        )
    )

    assert classification["primary_archetype"] == "digital_asset_marketplace"
    assert classification["valuation_policy"]["primary_model"] == "fcff_dcf"
    assert model_eligibility(classification)["eligible"] is False
    assert "dedicated" in classification["model_route_reason"].lower()


@pytest.mark.parametrize(
    "classification",
    [
        classification_for("unknown_archetype", "fcff_dcf"),
        {"valuation_policy": {"primary_model": "fcff_dcf"}},
        classification_for(["enterprise_software_cloud"], "fcff_dcf"),
    ],
)
def test_model_eligibility_rejects_unknown_missing_and_malformed_archetypes(
    classification: dict,
) -> None:
    result = model_eligibility(classification)

    assert result["eligible"] is False
    assert result["reason"]


def test_model_eligibility_rejects_configured_but_unimplemented_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.us_valuation.eligibility.load_archetype_config",
        lambda: {
            "valuation_policies": {
                "enterprise_software_cloud": {"primary_model": "magic_model"}
            }
        },
    )

    result = model_eligibility(
        classification_for("enterprise_software_cloud", "magic_model")
    )

    assert result["eligible"] is False
    assert result["model"] == "magic_model"
    assert "implemented" in result["reason"].lower()


def test_ineligible_model_pair_returns_withheld_artifact(monkeypatch) -> None:
    submissions = load_fixture("msft-submissions.json")
    classification = {
        **valuation_pipeline.classify_issuer(submissions),
        "valuation_policy": {
            **valuation_pipeline.classify_issuer(submissions)["valuation_policy"],
            "primary_model": "residual_income",
        },
    }
    monkeypatch.setattr(valuation_pipeline, "classify_issuer", lambda _: classification)

    result = valuation_pipeline.build_us_valuation(
        submissions=submissions,
        companyfacts={"cik": submissions["cik"]},
        valuation_date="2026-08-01",
    )

    assert result["model_policy"]["primary"] == "residual_income"
    assert result["models"]["residual_income"]["intrinsic_value_per_share"] is None
    assert result["models"]["residual_income"]["publication_state"] == "withheld"
    assert result["review"]["publication_state"] == "withheld"
    assert "eligibility" in " ".join(result["review"]["errors"]).lower()

    public = public_result(result, submissions)
    assert public["review"]["publication_state"] == "withheld"
    assert public["models"]["residual_income"]["intrinsic_value_per_share"] is None
    assert public["scenario_range"]["base"] is None


def test_incomplete_fcff_bridge_is_withheld_without_model_fallback(monkeypatch) -> None:
    submissions = load_fixture("msft-submissions.json")
    companyfacts = {
        "cik": submissions["cik"],
        "facts": {
            "us-gaap": {
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "fy": 2025,
                                "fp": "FY",
                                "form": "10-K",
                                "end": "2025-06-30",
                                "val": 100_000_000,
                            }
                        ]
                    }
                },
                "StockholdersEquity": {
                    "units": {
                        "USD": [
                            {"end": "2025-06-30", "val": 1_000_000_000}
                        ]
                    }
                },
                "CommonStockSharesOutstanding": {
                    "units": {"shares": [{"end": "2025-06-30", "val": 100_000_000}]}
                },
            }
        },
    }
    normalized = {
        "normalized": {"tax_rate": 0.21},
        "balance_sheet": {
            "bridge_complete": False,
            "bridge_missing_fields": [
                "preferred_equity",
                "noncontrolling_interests",
            ],
        },
        "ttm": {"period_end": "2025-06-30"},
    }
    monkeypatch.setattr(
        valuation_pipeline.CompanyFactsNormalizer,
        "normalize",
        lambda self, **kwargs: deepcopy(normalized),
    )

    result = valuation_pipeline.build_us_valuation(
        submissions=submissions,
        companyfacts=companyfacts,
        valuation_date="2026-08-01",
    )

    assert result["model_policy"]["primary"] == "fcff_dcf"
    assert result["review"]["publication_state"] == "withheld"
    assert result["models"]["fcff_dcf"]["intrinsic_value_per_share"] is None
    errors = " ".join(result["review"]["errors"])
    assert "preferred_equity" in errors
    assert "noncontrolling_interests" in errors
