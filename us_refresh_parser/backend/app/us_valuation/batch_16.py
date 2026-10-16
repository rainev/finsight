"""Immutable contract for controlled universe-reset Batch 16."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .sec_client import normalize_cik


BATCH_16_VALUATION_DATE = "2026-08-14"
BATCH_16_TICKERS = ("A", "DXCM", "EW", "CRL", "ZBH", "COR", "PODD", "ELV", "VEEV", "IQV")


@dataclass(frozen=True)
class Batch16Issuer:
    ticker: str
    cik: str
    issuer_name: str
    role: str
    boundary_reason: str | None
    primary_lane_id: str
    partition_family_id: str
    gics_sector: str
    gics_sub_industry: str


def _load() -> tuple[Batch16Issuer, ...]:
    value = json.loads(files(__package__).joinpath("config/reset_batches_2026_08_14/batch_16.json").read_text())
    if value.get("batch") != 16 or value.get("valuation_date") != BATCH_16_VALUATION_DATE or value.get("core_count") != 8 or value.get("boundary_count") != 2:
        raise ValueError("Batch 16 contract invalid")
    rows = tuple(Batch16Issuer(str(row["ticker"]), normalize_cik(row["cik"]), str(row["issuer_name"]), str(row["role"]), row.get("boundary_reason"), str(row["primary_lane_id"]), str(row["partition_family_id"]), str(row["gics_sector"]), str(row["gics_sub_industry"])) for row in value["members"])
    if tuple(row.ticker for row in rows) != BATCH_16_TICKERS or len({row.cik for row in rows}) != 10:
        raise ValueError("Batch 16 denominator changed")
    return rows


BATCH_16_MANIFEST = _load()
