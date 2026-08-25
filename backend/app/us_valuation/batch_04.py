"""Immutable contract for controlled universe-reset Batch 04."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .sec_client import normalize_cik


BATCH_04_VALUATION_DATE = "2026-08-14"
BATCH_04_TICKERS = ("F", "GPC", "HAS", "LOW", "MCD", "TJX", "NKE", "HD", "ROST", "MGM")


@dataclass(frozen=True)
class Batch04Issuer:
    ticker: str
    cik: str
    issuer_name: str
    role: str
    boundary_reason: str | None
    primary_lane_id: str
    partition_family_id: str
    gics_sector: str
    gics_sub_industry: str


def _load() -> tuple[Batch04Issuer, ...]:
    path = files(__package__).joinpath("config/reset_batches_2026_08_14/batch_04.json")
    value = json.loads(path.read_text())
    if (
        value.get("batch") != 4
        or value.get("valuation_date") != BATCH_04_VALUATION_DATE
        or value.get("core_count") != 8
        or value.get("boundary_count") != 2
        or value.get("partition_families") != ["operating_fcff"]
    ):
        raise ValueError("Batch 04 frozen manifest contract is invalid")
    rows = tuple(
        Batch04Issuer(
            ticker=str(row["ticker"]),
            cik=normalize_cik(row["cik"]),
            issuer_name=str(row["issuer_name"]),
            role=str(row["role"]),
            boundary_reason=row.get("boundary_reason"),
            primary_lane_id=str(row["primary_lane_id"]),
            partition_family_id=str(row["partition_family_id"]),
            gics_sector=str(row["gics_sector"]),
            gics_sub_industry=str(row["gics_sub_industry"]),
        )
        for row in value.get("members", [])
    )
    if tuple(row.ticker for row in rows) != BATCH_04_TICKERS:
        raise ValueError("Batch 04 ticker order changed")
    if len(rows) != 10 or len({row.cik for row in rows}) != 10:
        raise ValueError("Batch 04 must contain ten unique issuer CIKs")
    return rows


BATCH_04_MANIFEST = _load()

