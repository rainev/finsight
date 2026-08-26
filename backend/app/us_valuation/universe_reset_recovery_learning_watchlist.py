"""Machine-readable bookmark for not-fully-recovered universe-reset issuers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
import re
from typing import Any, Mapping


VERSION = "US-UNIVERSE-RESET-RECOVERY-LEARNING-1.0"
TITLE = "Universe Reset Recovery Learning Watchlist"
CALL_NAME = "Recovery Learning Watchlist"
_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
_CIK = re.compile(r"^\d{10}$")
_STATUSES = {
    "withheld_after_recovery",
    "conditional_numeric_low",
    "conditional_numeric_low_equity_at_risk",
}
_INITIAL_OUTCOMES = {"withheld", "conditional_numeric_low"}
_RECOVERY_OUTCOMES = {"withheld", "conditional_numeric_low", "not_applicable"}


def _strings(value: object, field: str) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(f"{field} must contain unique nonempty strings")
    return tuple(value)


@dataclass(frozen=True)
class RecoveryLearningEntry:
    batch: int
    ticker: str
    cik: str
    issuer_name: str
    initial_outcome: str
    recovery_outcome: str
    current_status: str
    provisional_model: str
    why_not_fully_recovered: str
    learning_themes: tuple[str, ...]
    revisit_triggers: tuple[str, ...]
    evidence_reports: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RecoveryLearningEntry":
        if not isinstance(value, Mapping):
            raise ValueError("learning-watchlist entry must be an object")
        batch = value.get("batch")
        ticker = value.get("ticker")
        cik = value.get("cik")
        status = value.get("current_status")
        initial_outcome = value.get("initial_outcome")
        recovery_outcome = value.get("recovery_outcome")
        if not isinstance(batch, int) or batch < 1 or batch > 50:
            raise ValueError("watchlist batch must be between 1 and 50")
        if not isinstance(ticker, str) or not _TICKER.fullmatch(ticker):
            raise ValueError("watchlist ticker is invalid")
        if not isinstance(cik, str) or not _CIK.fullmatch(cik):
            raise ValueError("watchlist CIK is invalid")
        if status not in _STATUSES:
            raise ValueError("watchlist status is invalid")
        if initial_outcome not in _INITIAL_OUTCOMES:
            raise ValueError("watchlist companies must have failed the initial pass")
        if recovery_outcome not in _RECOVERY_OUTCOMES:
            raise ValueError("watchlist recovery outcome is invalid")
        if initial_outcome == "conditional_numeric_low" and recovery_outcome != "not_applicable":
            raise ValueError("direct conditional entries do not receive a withheld recovery attempt")
        if initial_outcome == "withheld" and recovery_outcome == "not_applicable":
            raise ValueError("withheld entries require a recovery outcome")
        text = {
            field: value.get(field)
            for field in (
                "issuer_name",
                "provisional_model",
                "why_not_fully_recovered",
            )
        }
        if any(not isinstance(item, str) or not item.strip() for item in text.values()):
            raise ValueError("watchlist explanations must be nonempty")
        return cls(
            batch=batch,
            ticker=ticker,
            cik=cik,
            initial_outcome=initial_outcome,
            recovery_outcome=recovery_outcome,
            current_status=status,
            issuer_name=text["issuer_name"],
            provisional_model=text["provisional_model"],
            why_not_fully_recovered=text["why_not_fully_recovered"],
            learning_themes=_strings(value.get("learning_themes"), "learning_themes"),
            revisit_triggers=_strings(value.get("revisit_triggers"), "revisit_triggers"),
            evidence_reports=_strings(value.get("evidence_reports"), "evidence_reports"),
        )


def load_recovery_learning_watchlist() -> tuple[RecoveryLearningEntry, ...]:
    path = files(__package__).joinpath(
        "config/universe_reset_recovery_learning_watchlist.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("version") != VERSION
        or value.get("title") != TITLE
        or value.get("call_name") != CALL_NAME
        or value.get("valuation_date") != "2026-08-14"
        or value.get("review_after_batch") != 50
        or not isinstance(value.get("entries"), list)
    ):
        raise ValueError("recovery learning watchlist is invalid")
    entries = tuple(RecoveryLearningEntry.from_dict(row) for row in value["entries"])
    if len({row.ticker for row in entries}) != len(entries):
        raise ValueError("recovery learning watchlist contains duplicate tickers")
    if len({row.cik for row in entries}) != len(entries):
        raise ValueError("recovery learning watchlist contains duplicate CIKs")
    if entries != tuple(sorted(entries, key=lambda row: (row.batch, row.cik))):
        raise ValueError("recovery learning watchlist must be sorted by batch then CIK")
    return entries
