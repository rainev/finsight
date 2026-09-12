"""Focused correctness tests for deterministic EOD/scenario comparisons."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json

import pytest

from app.us_valuation.market_comparison import (
    PrivateEodRecord,
    public_market_comparison,
    public_scenario_market_comparison,
    validate_current_eod_for_valuation,
    validate_eod_for_valuation,
)


def _eod(**changes: object) -> PrivateEodRecord:
    values: dict[str, object] = {
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


def test_historical_validation_defaults_are_unchanged() -> None:
    # Existing historical callers continue to use valuation_date and the
    # seven-day default without a mode or injected clock.
    validate_eod_for_valuation(
        _eod(),
        ticker="AAPL",
        primary_listing="NASDAQ",
        valuation_date="2026-08-14",
    )
    with pytest.raises(ValueError, match="later than the valuation date"):
        validate_eod_for_valuation(
            _eod(price_date="2026-08-15"),
            ticker="AAPL",
            primary_listing="NASDAQ",
            valuation_date="2026-08-14",
        )


def test_current_validation_uses_explicit_injected_utc_reference() -> None:
    validate_current_eod_for_valuation(
        _eod(),
        ticker="AAPL",
        primary_listing="NASDAQ",
        reference_date=datetime(2026, 8, 15, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(ValueError, match="explicit UTC reference date"):
        validate_eod_for_valuation(
            _eod(),
            ticker="AAPL",
            primary_listing="NASDAQ",
            mode="current",
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_current_eod_for_valuation(
            _eod(),
            ticker="AAPL",
            primary_listing="NASDAQ",
            reference_date=datetime(2026, 8, 15),
        )


@pytest.mark.parametrize(
    ("record", "listing", "reference", "message"),
    [
        (_eod(primary_listing="NYSE"), "NASDAQ", "2026-08-14", "listing"),
        (_eod(price_date="2026-08-15"), "NASDAQ", "2026-08-14", "later"),
        (
            _eod(price_date=(date(2026, 8, 14) - timedelta(days=8)).isoformat()),
            "NASDAQ",
            "2026-08-14",
            "stale",
        ),
    ],
)
def test_current_validation_rejects_listing_future_and_stale(
    record: PrivateEodRecord, listing: str, reference: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_current_eod_for_valuation(
            record,
            ticker="AAPL",
            primary_listing=listing,
            reference_date=reference,
        )


def test_currency_is_rejected_at_private_record_boundary() -> None:
    with pytest.raises(ValueError, match="USD"):
        _eod(currency="EUR")


def test_scenario_comparison_recomputes_all_cases_from_one_private_price() -> None:
    result = public_scenario_market_comparison(
        scenario_range={"low": 100.0, "base": 200.0, "high": 400.0},
        record=_eod(split_adjusted_close=80.0),
    )

    assert result["status"] == "available"
    assert result["price_date"] == "2026-08-14"
    assert result["denominator"] == "finsight_scenario_value"
    assert result["low"]["gap_pct"] == pytest.approx(0.20)
    assert result["base"]["gap_pct"] == pytest.approx(0.60)
    assert result["high"]["gap_pct"] == pytest.approx(0.80)
    encoded = json.dumps(result)
    # The exact close is absent as a field; a derived 80.0% label is allowed.
    assert '"split_adjusted_close"' not in encoded
    assert "approved-private-vendor" not in encoded
    assert "payload_hash" not in encoded
    assert "aaaaaaaa" not in encoded


def test_nonpositive_scenario_has_unavailable_percentage_without_clipping() -> None:
    result = public_scenario_market_comparison(
        scenario_values={"low": 0.0, "base": -10.0, "high": 100.0},
        manual_price=80.0,
    )

    assert result["status"] == "partial"
    assert result["low"] == {
        "status": "unavailable",
        "gap_pct": None,
        "label": "Unavailable: FinSight scenario value is not positive and finite",
    }
    assert result["base"]["gap_pct"] is None
    assert result["high"]["gap_pct"] == pytest.approx(0.20)
    assert result["price_date"] is None


def test_manual_and_eod_comparisons_use_the_same_derived_shape() -> None:
    automatic = public_scenario_market_comparison(
        scenario_range={"low": 100.0, "base": 200.0, "high": 400.0},
        record=_eod(split_adjusted_close=80.0),
    )
    manual = public_scenario_market_comparison(
        scenario_range={"low": 100.0, "base": 200.0, "high": 400.0},
        price=80.0,
    )
    assert {key: manual[key]["gap_pct"] for key in ("low", "base", "high")} == pytest.approx(
        {key: automatic[key]["gap_pct"] for key in ("low", "base", "high")}
    )
    assert '"manual_price"' not in json.dumps(manual)
    assert '"provider"' not in json.dumps(manual)


def test_legacy_base_comparison_keeps_its_public_shape() -> None:
    assert public_market_comparison(base_value=100.0, record=_eod()) == {
        "status": "available",
        "gap_pct": pytest.approx(0.20),
        "label": "Undervalued by 20.0% versus FinSight value",
        "price_date": "2026-08-14",
        "denominator": "finsight_base_value",
    }
