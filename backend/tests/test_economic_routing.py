"""Private economic-routing and model-governance contract tests."""

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from app.us_valuation.batch_01 import BATCH_01_TICKERS
from app.us_valuation.economic_routing import (
    EconomicRoutingRecord,
    load_batch_01_routing_records,
)


def _record_dict() -> dict:
    return {
        "ticker": "TEST",
        "economic_profile": {
            "business_type": "operating",
            "material_segments": ["Core"],
            "lifecycle": "mature",
            "cyclical_exposure": False,
            "commodity_exposure": False,
            "regulatory_capital_dependence": False,
            "captive_finance_activity": False,
            "property_or_reserve_assets": False,
            "primary_model_candidate": "fcff",
            "secondary_model_candidates": ["epv"],
            "routing_explanation": "Source-backed operating-company route hypothesis.",
            "source_accessions": ["0000000001-26-000001"],
        },
        "model_decision": {
            "economic_lane": "mature_operating",
            "model_family": "fcff",
            "model_version": "FCFF-1.0",
            "required_inputs": ["ttm_operating_income", "reinvestment"],
            "rejected_models": [
                {"model_family": "ddm", "reason": "Payout is not the full claim."}
            ],
            "maturity": "provisional",
            "reliability_cap": "Withhold",
            "source_accessions": ["0000000001-26-000001"],
            "routing_status": "hypothesis",
            "decision_reason": "Awaiting controlled source and model validation.",
        },
    }


def test_batch_01_routing_records_match_manifest_and_recovery_governance() -> None:
    records = load_batch_01_routing_records()

    assert tuple(record.ticker for record in records) == BATCH_01_TICKERS
    assert len(records) == len({record.ticker for record in records}) == 10
    recovered = {
        record.ticker: record
        for record in records
        if record.ticker in {"WDC", "DELL", "NEE"}
    }
    assert {
        ticker: row.model_decision.model_family
        for ticker, row in recovered.items()
    } == {
        "WDC": "normalized_cyclical_fcff",
        "DELL": "captive_finance_fcfe",
        "NEE": "mixed_utility_fcfe",
    }
    assert all(
        row.model_decision.routing_status == "selected"
        for row in recovered.values()
    )
    assert all(
        row.model_decision.maturity == "provisional"
        for row in recovered.values()
    )
    assert all(
        row.model_decision.reliability_cap == "Low"
        for row in recovered.values()
    )
    untouched = [record for record in records if record.ticker not in recovered]
    assert all(
        record.model_decision.routing_status == "hypothesis"
        for record in untouched
    )
    assert all(
        record.model_decision.reliability_cap == "Withhold"
        for record in untouched
    )
    assert all(record.economic_profile.source_accessions for record in records)
    assert all(record.model_decision.rejected_models for record in records)

    with pytest.raises(FrozenInstanceError):
        records[0].ticker = "OTHER"  # type: ignore[misc]


def test_governance_rejects_unconfirmed_or_immature_publication_caps() -> None:
    raw = _record_dict()
    raw["model_decision"]["reliability_cap"] = "Low"
    with pytest.raises(ValueError, match="hypotheses must be withheld"):
        EconomicRoutingRecord.from_dict(raw)

    raw = _record_dict()
    raw["model_decision"]["maturity"] = "experimental"
    raw["model_decision"]["routing_status"] = "selected"
    raw["model_decision"]["reliability_cap"] = "Withhold"
    with pytest.raises(ValueError, match="experimental models cannot be selected"):
        EconomicRoutingRecord.from_dict(raw)


def test_governance_rejects_wrong_model_and_unlinked_accession() -> None:
    raw = _record_dict()
    raw["model_decision"]["model_family"] = "ddm"
    with pytest.raises(ValueError, match="cannot also be rejected"):
        EconomicRoutingRecord.from_dict(raw)

    raw = deepcopy(_record_dict())
    raw["model_decision"]["source_accessions"] = ["0000000002-26-000002"]
    with pytest.raises(ValueError, match="must be present in the economic profile"):
        EconomicRoutingRecord.from_dict(raw)


def test_governance_rejects_invalid_accession_and_missing_economics() -> None:
    raw = _record_dict()
    raw["economic_profile"]["source_accessions"] = ["invalid"]
    with pytest.raises(ValueError, match="invalid SEC accession"):
        EconomicRoutingRecord.from_dict(raw)

    raw = _record_dict()
    raw["economic_profile"]["material_segments"] = []
    with pytest.raises(ValueError, match="must not be empty"):
        EconomicRoutingRecord.from_dict(raw)
