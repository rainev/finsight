"""Private EOD validation and public-safe FinSight-value comparison."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
from typing import Any


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
    valuation_date: str,
    max_age_days: int = 7,
) -> None:
    if record.canonical_security != ticker.strip().upper():
        raise ValueError("EOD security does not match valuation ticker")
    if record.primary_listing != primary_listing.strip().upper():
        raise ValueError("EOD listing does not match primary listing")
    if max_age_days < 0:
        raise ValueError("EOD maximum age must be nonnegative")
    valuation_day = date.fromisoformat(valuation_date)
    price_day = date.fromisoformat(record.price_date)
    age = (valuation_day - price_day).days
    if age < 0:
        raise ValueError("EOD price is later than the valuation date")
    if age > max_age_days:
        raise ValueError("EOD price is stale for this valuation")


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
