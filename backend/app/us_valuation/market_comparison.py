"""Private EOD validation and public-safe FinSight-value comparison."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
from typing import Any

from collections.abc import Mapping


_SCENARIO_KEYS = ("low", "base", "high")


@dataclass(frozen=True)
class PrivateEodRecord:
    canonical_security: str
    primary_listing: str
    currency: str
    split_adjusted_close: float
    price_date: str
    provider: str
    payload_hash: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", self.canonical_security):
            raise ValueError("EOD canonical security is invalid")
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{1,15}", self.primary_listing):
            raise ValueError("EOD primary listing is invalid")
        if self.currency != "USD":
            raise ValueError("U.S. EOD comparison requires USD")
        if not isfinite(self.split_adjusted_close) or self.split_adjusted_close <= 0:
            raise ValueError("EOD split-adjusted close must be positive and finite")
        try:
            date.fromisoformat(self.price_date)
        except ValueError as error:
            raise ValueError("EOD price date is invalid") from error
        if not self.provider.strip():
            raise ValueError("EOD provider is required")
        if not re.fullmatch(r"[0-9a-f]{64}", self.payload_hash):
            raise ValueError("EOD payload hash must be lowercase SHA-256")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PrivateEodRecord":
        return cls(
            canonical_security=str(value["canonical_security"]),
            primary_listing=str(value["primary_listing"]),
            currency=str(value["currency"]),
            split_adjusted_close=float(value["split_adjusted_close"]),
            price_date=str(value["price_date"]),
            provider=str(value["provider"]),
            payload_hash=str(value["payload_hash"]),
        )


@dataclass(frozen=True)
class PrivateSecurityRecord:
    canonical_security: str
    primary_listing: str
    currency: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", self.canonical_security):
            raise ValueError("security-master ticker is invalid")
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{1,15}", self.primary_listing):
            raise ValueError("security-master listing is invalid")
        if self.currency != "USD":
            raise ValueError("U.S. security master requires USD")


def validate_eod_for_valuation(
    record: PrivateEodRecord,
    *,
    ticker: str,
    primary_listing: str,
    valuation_date: str | None = None,
    max_age_days: int = 7,
    mode: str = "historical",
    reference_date: str | date | datetime | None = None,
    reference_datetime: datetime | None = None,
) -> None:
    """Validate an EOD record for a historical or current valuation.

    Historical callers retain the original contract: ``valuation_date`` is the
    reference date and the default mode is ``historical``.  Current callers
    must inject ``reference_date`` (or its explicitly named datetime form), so
    validation never consults the wall clock and remains reproducible in tests
    and in a frozen serving run.
    """
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in {"historical", "current"}:
        raise ValueError("EOD validation mode must be historical or current")
    if record.canonical_security != ticker.strip().upper():
        raise ValueError("EOD security does not match valuation ticker")
    if record.primary_listing != primary_listing.strip().upper():
        raise ValueError("EOD listing does not match primary listing")
    # Keep this guard in the validator as well as the record constructor.  It
    # protects the boundary if a record is deserialized by a future adapter or
    # supplied by a test double rather than constructed directly.
    if record.currency != "USD":
        raise ValueError("U.S. EOD comparison requires USD")
    if max_age_days < 0:
        raise ValueError("EOD maximum age must be nonnegative")
    if reference_date is not None and reference_datetime is not None:
        raise ValueError("provide only one UTC EOD reference date")
    if normalized_mode == "current":
        if reference_datetime is not None:
            effective_reference = _utc_reference_date(reference_datetime)
        elif reference_date is not None:
            effective_reference = _utc_reference_date(reference_date)
        else:
            raise ValueError("current EOD validation requires an explicit UTC reference date")
    else:
        # Do not change the historical behavior or its error surface: callers
        # have always supplied valuation_date and it is parsed as an ISO date.
        if valuation_date is None:
            raise ValueError("historical EOD validation requires valuation_date")
        effective_reference = date.fromisoformat(valuation_date)
        if reference_date is not None or reference_datetime is not None:
            raise ValueError("reference_date is only supported in current EOD validation mode")
    price_day = date.fromisoformat(record.price_date)
    age = (effective_reference - price_day).days
    if age < 0:
        raise ValueError("EOD price is later than the valuation date")
    if age > max_age_days:
        raise ValueError("EOD price is stale for this valuation")


def _utc_reference_date(value: str | date | datetime) -> date:
    """Normalize an injected date/datetime to its UTC calendar date."""
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("UTC EOD reference datetime must be timezone-aware")
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("UTC EOD reference date is required")
    try:
        return date.fromisoformat(text)
    except ValueError:
        # Accept an ISO UTC datetime string for callers that inject a frozen
        # clock directly.  A timezone is mandatory for datetime strings.
        normalized = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as error:
            raise ValueError("UTC EOD reference date is invalid") from error
        return _utc_reference_date(parsed)


def validate_current_eod_for_valuation(
    record: PrivateEodRecord,
    *,
    ticker: str,
    primary_listing: str,
    reference_date: str | date | datetime,
    max_age_days: int = 7,
) -> None:
    """Explicit deterministic current-mode EOD validation helper."""
    validate_eod_for_valuation(
        record,
        ticker=ticker,
        primary_listing=primary_listing,
        max_age_days=max_age_days,
        mode="current",
        reference_date=reference_date,
    )


def public_market_comparison(
    *, base_value: float, record: PrivateEodRecord
) -> dict[str, Any]:
    if not isfinite(base_value) or base_value <= 0:
        raise ValueError("FinSight base value must be positive and finite")
    gap = (base_value - record.split_adjusted_close) / base_value
    if abs(gap) <= 0.05:
        label = "Near FinSight's base value"
    elif gap > 0:
        label = f"Undervalued by {abs(gap):.1%} versus FinSight value"
    else:
        label = f"Overvalued by {abs(gap):.1%} versus FinSight value"
    return {
        "status": "available",
        "gap_pct": gap,
        "label": label,
        "price_date": record.price_date,
        "denominator": "finsight_base_value",
    }


def _comparison_for_value(*, value: object, market_price: float) -> dict[str, Any]:
    """Return only the public-safe derived comparison for one scenario."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or float(value) <= 0
    ):
        return {
            "status": "unavailable",
            "gap_pct": None,
            "label": "Unavailable: FinSight scenario value is not positive and finite",
        }
    scenario_value = float(value)
    gap = (scenario_value - market_price) / scenario_value
    if abs(gap) <= 0.05:
        label = "Near FinSight's scenario value"
    elif gap > 0:
        label = f"Undervalued by {abs(gap):.1%} versus FinSight value"
    else:
        label = f"Overvalued by {abs(gap):.1%} versus FinSight value"
    return {"status": "available", "gap_pct": gap, "label": label}


def public_scenario_market_comparison(
    *,
    scenario_range: Mapping[str, Any] | None = None,
    scenario_values: Mapping[str, Any] | None = None,
    record: PrivateEodRecord | None = None,
    manual_price: float | None = None,
    price: float | None = None,
) -> dict[str, Any]:
    """Derive low/base/high comparisons from one EOD or manual price.

    ``record`` and ``manual_price`` are mutually exclusive inputs.  The
    private price is used for arithmetic only; it is never included in the
    returned object, nor are provider or payload-hash fields.  Every scenario
    is recomputed independently from that same price.  A nonpositive or
    otherwise unusable scenario returns ``gap_pct=None`` and status
    ``unavailable`` for that scenario instead of silently clipping it.

    ``scenario_values`` is an alias retained for callers that use the shorter
    name.  ``price`` is an alias for ``manual_price`` for integration with
    calculator callers that already use that vocabulary.
    """
    if scenario_range is not None and scenario_values is not None:
        raise ValueError("provide only one scenario range")
    values = scenario_range if scenario_range is not None else scenario_values
    if not isinstance(values, Mapping):
        raise ValueError("scenario_range must be an object")
    if record is not None and manual_price is not None:
        raise ValueError("provide either an EOD record or a manual price")
    if manual_price is not None and price is not None:
        raise ValueError("provide only one manual market price")
    if price is not None:
        manual_price = price
    if record is not None:
        if record.currency != "USD":
            raise ValueError("U.S. EOD comparison requires USD")
        if (
            not isinstance(record.split_adjusted_close, (int, float))
            or not isfinite(float(record.split_adjusted_close))
            or float(record.split_adjusted_close) <= 0
        ):
            raise ValueError("EOD split-adjusted close must be positive and finite")
        # Preserve the private record's date as a derived public field only
        # after confirming it is a valid ISO calendar date.
        date.fromisoformat(record.price_date)
        market_price = record.split_adjusted_close
        price_date: str | None = record.price_date
    elif manual_price is not None:
        if (
            isinstance(manual_price, bool)
            or not isinstance(manual_price, (int, float))
            or not isfinite(float(manual_price))
            or float(manual_price) <= 0
        ):
            raise ValueError("manual_price must be positive and finite")
        market_price = float(manual_price)
        price_date = None
    else:
        raise ValueError("an EOD record or manual price is required")

    comparisons = {
        key: _comparison_for_value(value=values.get(key), market_price=market_price)
        for key in _SCENARIO_KEYS
    }
    statuses = [row["status"] for row in comparisons.values()]
    overall_status = (
        "available"
        if all(status == "available" for status in statuses)
        else "unavailable"
        if all(status == "unavailable" for status in statuses)
        else "partial"
    )
    result: dict[str, Any] = {
        "status": overall_status,
        "price_date": price_date,
        "denominator": "finsight_scenario_value",
    }
    result.update(comparisons)
    return result


# Integration-friendly alias: the operation is deliberately public-safe and
# derived, while the record/price inputs remain private to the caller.
derived_market_comparison = public_scenario_market_comparison
public_market_comparison_for_scenarios = public_scenario_market_comparison
public_market_comparison_scenarios = public_scenario_market_comparison


def load_private_eod_record(root: Path, ticker: str) -> PrivateEodRecord | None:
    path = Path(root) / f"{ticker.strip().upper()}.json"
    if not path.exists():
        return None
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("private EOD record must be an object")
    record = PrivateEodRecord.from_dict(value)
    # The payload hash identifies the vendor payload, not this normalized wrapper. A
    # wrapper hash is still checked when supplied so accidental edits fail loudly.
    wrapper_hash = value.get("normalized_record_sha256")
    if wrapper_hash is not None:
        canonical = dict(value)
        canonical.pop("normalized_record_sha256", None)
        expected = hashlib.sha256(
            (json.dumps(canonical, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest()
        if wrapper_hash != expected:
            raise ValueError("private EOD normalized-record hash mismatch")
    return record


def load_private_security_record(root: Path, ticker: str) -> PrivateSecurityRecord | None:
    path = Path(root) / f"{ticker.strip().upper()}.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("private security-master record must be an object")
    return PrivateSecurityRecord(
        canonical_security=str(value["canonical_security"]),
        primary_listing=str(value["primary_listing"]),
        currency=str(value["currency"]),
    )
