"""Immutable contract for controlled universe-reset Batch 49."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .sec_client import normalize_cik

BATCH_49_VALUATION_DATE = "2026-08-14"
BATCH_49_TICKERS = ("REG", "MAA", "AVB", "ESS", "SBAC", "ARE", "BXP", "PLD", "CCI", "EQIX")


@dataclass(frozen=True)
class Batch49Issuer:
    ticker: str
    cik: str
    issuer_name: str
    role: str
    boundary_reason: str | None
    primary_lane_id: str
    partition_family_id: str
    gics_sector: str
    gics_sub_industry: str


def _load() -> tuple[Batch49Issuer, ...]:
    value = json.loads(files(__package__).joinpath("config/reset_batches_2026_08_14/batch_49.json").read_text())
    rows = tuple(Batch49Issuer(ticker=str(row["ticker"]), cik=normalize_cik(row["cik"]), issuer_name=str(row["issuer_name"]), role=str(row["role"]), boundary_reason=row.get("boundary_reason"), primary_lane_id=str(row["primary_lane_id"]), partition_family_id=str(row["partition_family_id"]), gics_sector=str(row["gics_sector"]), gics_sub_industry=str(row["gics_sub_industry"])) for row in value["members"])
    if value.get("batch") != 49 or value.get("valuation_date") != BATCH_49_VALUATION_DATE or value.get("core_count") != 8 or value.get("boundary_count") != 2 or tuple(row.ticker for row in rows) != BATCH_49_TICKERS or len({row.cik for row in rows}) != 10 or {row.partition_family_id for row in rows} != {"reit_affo"}:
        raise ValueError("Batch 49 contract invalid")
    return rows


BATCH_49_MANIFEST = _load()
