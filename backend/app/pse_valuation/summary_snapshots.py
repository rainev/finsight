"""Compare locally supplied PSE EDGE financial-summary observations.

These summary figures are change signals, not reviewed valuation facts. This
module performs no network requests and does not persist the observed figures.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from .contract import PseValuationArtifact


SUMMARY_SCHEMA = "PSE-V2-FINANCIAL-SUMMARY-SNAPSHOT-1.0"
PSE_SUMMARY_URLS = {
    "AP": "https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=609",
    "BPI": "https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=234",
    "RCR": "https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=684",
    "RLC": "https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id=195",
}


@dataclass(frozen=True)
class SummaryObservation:
    ticker: str
    period_end: date
    digest: str


def _date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date") from exc


def read_snapshot(path: Path, ticker: str) -> SummaryObservation:
    """Validate a manually saved, structured snapshot and hash only economics."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
        raise ValueError(f"{ticker}: snapshot is missing, linked, or too large")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{ticker}: snapshot is not valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SUMMARY_SCHEMA:
        raise ValueError(f"{ticker}: unsupported summary snapshot")
    if payload.get("ticker") != ticker or payload.get("source_url") != PSE_SUMMARY_URLS[ticker]:
        raise ValueError(f"{ticker}: summary identity or source URL differs")
    observed = _date(payload.get("observed_at"), f"{ticker} observed_at")
    period = _date(payload.get("period_end"), f"{ticker} period_end")
    if observed > date.today():
        raise ValueError(f"{ticker}: summary observation date is in the future")
    if period > observed:
        raise ValueError(f"{ticker}: summary period follows observation date")
    if payload.get("period_type") not in {"annual", "quarterly"}:
        raise ValueError(f"{ticker}: annual or quarterly period_type is required")
    if payload.get("currency") != "PHP" or payload.get("unit") not in {"PHP", "PHP_thousands", "PHP_millions"}:
        raise ValueError(f"{ticker}: explicit PHP currency and unit are required")
    if payload.get("scope") not in {"consolidated", "parent"}:
        raise ValueError(f"{ticker}: explicit consolidation scope is required")
    facts = payload.get("facts")
    if not isinstance(facts, dict) or not facts:
        raise ValueError(f"{ticker}: summary facts must be a nonempty object")
    for name, value in facts.items():
        if not isinstance(name, str) or not name.strip() or isinstance(value, bool) or (
            value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value))
        ):
            raise ValueError(f"{ticker}: summary facts need named finite numbers or null")
    normalized_facts = {name: None if value is None else str(Decimal(str(value)).normalize()) for name, value in facts.items()}
    normalized = {
        "period_end": period.isoformat(), "period_type": payload["period_type"],
        "currency": payload["currency"], "unit": payload["unit"],
        "scope": payload["scope"], "facts": normalized_facts,
    }
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return SummaryObservation(ticker, period, hashlib.sha256(raw).hexdigest())


def active_period(parent: PseValuationArtifact) -> date | None:
    periods = [_date(source.period_end, "active source period") for source in parent.sources if source.period_end]
    if periods:
        return max(periods)
    filing = parent.filing_period or ""
    if filing.startswith("FY ") and filing[3:].isdigit() and len(filing) == 7:
        return date(int(filing[3:]), 12, 31)
    return None


def compare_snapshot(
    observed: SummaryObservation, previous: dict[str, str] | None, active_source_period: date | None,
) -> str:
    """Return the signal; first same-period observation is only a baseline."""
    if previous:
        prior_period = _date(previous.get("period_end"), "prior summary period")
        if observed.period_end < prior_period:
            return "stale_period_held"
        if observed.period_end > prior_period:
            return "new_period"
        return "unchanged" if observed.digest == previous.get("snapshot_sha256") else "restated_summary"
    if active_source_period is None:
        return "baseline_no_active_period"
    if observed.period_end < active_source_period:
        return "stale_period_held"
    if observed.period_end > active_source_period:
        return "new_period"
    return "baseline_recorded"
