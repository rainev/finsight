"""Cumulative companies still withheld after one controlled recovery attempt."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
import re
from typing import Any, Mapping


VERSION = "US-UNIVERSE-RESET-WITHHELD-1.0"
_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_CIK = re.compile(r"^\d{10}$")


def _strings(value: object, field: str) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(f"{field} must be unique nonempty strings")
    return tuple(value)


@dataclass(frozen=True)
class UniverseResetWithheldEntry:
    batch: int
    ticker: str
    cik: str
    issuer_name: str
    model_version: str
    recovery_attempts: int
    final_outcome: str
    reason_codes: tuple[str, ...]
    hard_blockers: tuple[str, ...]
    evidence_report: str
    pipeline_revision_retries: int
    revision_retry_report: str | None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UniverseResetWithheldEntry":
        if not isinstance(value, Mapping):
            raise ValueError("withheld entry must be an object")
        batch = value.get("batch")
        attempts = value.get("recovery_attempts")
        revision_retries = value.get("pipeline_revision_retries", 0)
        ticker = value.get("ticker")
        cik = value.get("cik")
        if not isinstance(batch, int) or batch < 1:
            raise ValueError("batch must be a positive integer")
        if attempts != 1:
            raise ValueError("universe reset permits exactly one recovery attempt")
        if revision_retries not in (0, 1):
            raise ValueError("pipeline revision retry count must be zero or one")
        if not isinstance(ticker, str) or not _TICKER.fullmatch(ticker):
            raise ValueError("ticker is invalid")
        if not isinstance(cik, str) or not _CIK.fullmatch(cik):
            raise ValueError("CIK is invalid")
        if value.get("final_outcome") != "withheld":
            raise ValueError("register entries must remain withheld")
        text_fields = {
            field: value.get(field)
            for field in ("issuer_name", "model_version", "evidence_report")
        }
        if any(not isinstance(item, str) or not item.strip() for item in text_fields.values()):
            raise ValueError("withheld entry text fields must be nonempty")
        revision_report = value.get("revision_retry_report")
        if (revision_retries == 1) != (
            isinstance(revision_report, str) and bool(revision_report.strip())
        ):
            raise ValueError("pipeline revision retry report must match retry count")
        return cls(
            batch=batch,
            ticker=ticker,
            cik=cik,
            issuer_name=text_fields["issuer_name"],
            model_version=text_fields["model_version"],
            recovery_attempts=attempts,
            final_outcome="withheld",
            reason_codes=_strings(value.get("reason_codes"), "reason_codes"),
            hard_blockers=_strings(value.get("hard_blockers"), "hard_blockers"),
            evidence_report=text_fields["evidence_report"],
            pipeline_revision_retries=revision_retries,
            revision_retry_report=revision_report if revision_retries else None,
        )


def load_universe_reset_withheld() -> tuple[UniverseResetWithheldEntry, ...]:
    path = files(__package__).joinpath("config/universe_reset_withheld.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("version") != VERSION
        or value.get("valuation_date") != "2026-08-14"
        or not isinstance(value.get("entries"), list)
    ):
        raise ValueError("universe reset withheld register is invalid")
    entries = tuple(
        UniverseResetWithheldEntry.from_dict(row) for row in value["entries"]
    )
    if len({row.ticker for row in entries}) != len(entries):
        raise ValueError("withheld register contains duplicate tickers")
    if len({row.cik for row in entries}) != len(entries):
        raise ValueError("withheld register contains duplicate CIKs")
    if entries != tuple(sorted(entries, key=lambda row: (row.batch, row.cik))):
        raise ValueError("withheld register must be sorted by batch then CIK")
    return entries
