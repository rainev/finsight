from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from app.us_valuation.artifacts import PUBLIC_SCHEMA_VERSION, sanitize_public_artifact
from app.us_valuation.baseline import (
    AvailabilityType,
    BaselineValuation,
    FallbackRejected,
    FallbackStage,
    run_fallback_ladder,
)
from app.us_valuation.market_comparison import (
    PrivateEodRecord,
    public_market_comparison,
    validate_eod_for_valuation,
)


def _baseline(
    *, method: str = "normalized_fcff", availability: AvailabilityType = AvailabilityType.AVAILABLE
) -> BaselineValuation:
    return BaselineValuation(
        ticker="AAPL",
        method=method,
        method_version="TEST-1",
        low=80.0,
        base=100.0,
        high=130.0,
        confidence="Medium",
        availability_type=availability,
    )


def test_fallback_ladder_records_rejection_then_selects_normalized_route() -> None:
    def reject() -> BaselineValuation:
        raise FallbackRejected("primary inputs incomplete")

    result = run_fallback_ladder(
        ticker="aapl",
        strategies=(
            (FallbackStage.PRIMARY_INTRINSIC, "fcff_dcf", reject),
            (FallbackStage.NORMALIZED, "normalized_fcff", _baseline),
        ),
    )

    assert result.availability_type == AvailabilityType.AVAILABLE
    assert [row.outcome.value for row in result.fallback_attempts] == [
        "rejected",
        "selected",
    ]


def test_fallback_ladder_hard_failure_stops_before_models() -> None:
    called = False

    def builder() -> BaselineValuation:
        nonlocal called
        called = True
        return _baseline()

    result = run_fallback_ladder(
        ticker="AAPL",
        hard_failures=("unreliable share denominator",),
        strategies=((FallbackStage.NORMALIZED, "normalized_fcff", builder),),
    )

    assert not called
    assert result.availability_type == AvailabilityType.NOT_AVAILABLE
    assert result.base is None


def test_conditional_stage_requires_conditional_availability() -> None:
    with pytest.raises(ValueError, match="must be labeled conditional"):
        run_fallback_ladder(
            ticker="AAPL",
            strategies=((FallbackStage.CONDITIONAL, "normalized_fcff", _baseline),),
        )


def test_v12_projection_keeps_only_derived_market_comparison() -> None:
    artifact = json.loads(
        Path("backend/app/data/us_valuations/WFC.json").read_text(encoding="utf-8")
    )
    artifact["market_comparison"] = {
        "status": "available",
        "gap_pct": 0.20,
        "label": "Undervalued by 20.0% versus FinSight value",
        "price_date": "2026-08-14",
        "denominator": "finsight_base_value",
        "raw_price": 80.0,
        "provider": "private-vendor",
        "payload_hash": "a" * 64,
    }

    public = sanitize_public_artifact(artifact)

    assert public["schema_version"] == PUBLIC_SCHEMA_VERSION == "US-PUBLIC-VALUATION-1.2"
    assert public["availability_type"] == "available"
    assert public["calculator_link"] == "/api/us-valuations/WFC/calculator"
    assert public["market_comparison"] == {
        "status": "available",
        "gap_pct": 0.20,
        "label": "Undervalued by 20.0% versus FinSight value",
        "price_date": "2026-08-14",
        "denominator": "finsight_base_value",
    }
    encoded = json.dumps(public)
    assert "raw_price" not in encoded
    assert "private-vendor" not in encoded
    assert "payload_hash" not in encoded


def _eod(**changes: object) -> PrivateEodRecord:
    values = {
        "canonical_security": "AAPL",
        "primary_listing": "NASDAQ",
        "currency": "USD",
        "split_adjusted_close": 80.0,
        "price_date": "2026-08-14",
        "provider": "approved-private-vendor",
        "payload_hash": "a" * 64,
    }
    values.update(changes)
    return PrivateEodRecord(**values)  # type: ignore[arg-type]


def test_market_gap_uses_documented_finsight_value_denominator() -> None:
    comparison = public_market_comparison(base_value=100.0, record=_eod())

    assert comparison["gap_pct"] == pytest.approx(0.20)
    assert comparison["denominator"] == "finsight_base_value"
    assert "80" not in json.dumps(comparison)
    assert "approved-private-vendor" not in json.dumps(comparison)


@pytest.mark.parametrize(
    ("record", "listing", "valuation_date", "message"),
    [
        (_eod(canonical_security="MSFT"), "NASDAQ", "2026-08-14", "security"),
        (_eod(primary_listing="NYSE"), "NASDAQ", "2026-08-14", "listing"),
        (
            _eod(price_date=(date(2026, 8, 14) - timedelta(days=8)).isoformat()),
            "NASDAQ",
            "2026-08-14",
            "stale",
        ),
    ],
)
def test_eod_validation_rejects_identity_listing_and_staleness(
    record: PrivateEodRecord, listing: str, valuation_date: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_eod_for_valuation(
            record,
            ticker="AAPL",
            primary_listing=listing,
            valuation_date=valuation_date,
        )


def test_eod_record_rejects_wrong_currency() -> None:
    with pytest.raises(ValueError, match="USD"):
        _eod(currency="PHP")
