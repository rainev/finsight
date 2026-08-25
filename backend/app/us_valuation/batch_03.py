"""Immutable contract for controlled universe-reset Batch 03."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .sec_client import normalize_cik


BATCH_03_VALUATION_DATE = "2026-08-14"
BATCH_03_TICKERS = (
    "LYV", "ECHO", "NWSA", "GOOGL", "TTD",
    "DIS", "APP", "FOXA", "TKO", "PSKY",
)


@dataclass(frozen=True)
class Batch03Issuer:
    ticker: str
    cik: str
    issuer_name: str
    role: str
    boundary_reason: str | None
    primary_lane_id: str
    partition_family_id: str
    gics_sector: str
    gics_sub_industry: str


def _load_manifest() -> tuple[Batch03Issuer, ...]:
    path = files(__package__).joinpath(
        "config/reset_batches_2026_08_14/batch_03.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("batch") != 3
        or value.get("valuation_date") != BATCH_03_VALUATION_DATE
        or value.get("core_count") != 8
        or value.get("boundary_count") != 2
        or value.get("partition_families") != ["operating_fcff"]
    ):
        raise ValueError("Batch 03 frozen manifest contract is invalid")
    rows = tuple(
        Batch03Issuer(
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
    if tuple(row.ticker for row in rows) != BATCH_03_TICKERS:
        raise ValueError("Batch 03 ticker order changed")
    if len(rows) != 10 or len({row.cik for row in rows}) != 10:
        raise ValueError("Batch 03 must contain ten unique issuer CIKs")
    if sum(row.role == "core" for row in rows) != 8:
        raise ValueError("Batch 03 core count changed")
    if sum(row.role == "boundary" for row in rows) != 2:
        raise ValueError("Batch 03 boundary count changed")
    if any(row.partition_family_id != "operating_fcff" for row in rows):
        raise ValueError("Batch 03 partition family changed")
    return rows


BATCH_03_MANIFEST = _load_manifest()


def batch_03_issuer(ticker: str) -> Batch03Issuer:
    normalized = ticker.strip().upper()
    for issuer in BATCH_03_MANIFEST:
        if issuer.ticker == normalized:
            return issuer
    raise KeyError(f"unknown Batch 03 ticker: {ticker}")

