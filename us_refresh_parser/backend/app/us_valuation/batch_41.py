"""Immutable contract for controlled universe-reset Batch 41."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json

from .sec_client import normalize_cik


BATCH_41_VALUATION_DATE = "2026-08-14"
BATCH_41_TICKERS = ("APD", "AVY", "BALL", "ECL", "EQT", "HAL", "IFF", "IP", "NUE", "PKG")


@dataclass(frozen=True)
class Batch41Issuer:
    ticker: str
    cik: str
    issuer_name: str
    role: str
    boundary_reason: str | None
    primary_lane_id: str
    partition_family_id: str
    gics_sector: str
    gics_sub_industry: str


def _load() -> tuple[Batch41Issuer, ...]:
    value = json.loads(files(__package__).joinpath("config/reset_batches_2026_08_14/batch_41.json").read_text())
    rows = tuple(
        Batch41Issuer(
            str(row["ticker"]),
            normalize_cik(row["cik"]),
            str(row["issuer_name"]),
            str(row["role"]),
            row.get("boundary_reason"),
            str(row["primary_lane_id"]),
            str(row["partition_family_id"]),
            str(row["gics_sector"]),
            str(row["gics_sub_industry"]),
        )
        for row in value["members"]
    )
    if (
        value.get("batch") != 41
        or value.get("valuation_date") != BATCH_41_VALUATION_DATE
        or value.get("core_count") != 8
        or value.get("boundary_count") != 2
        or tuple(row.ticker for row in rows) != BATCH_41_TICKERS
        or len({row.cik for row in rows}) != 10
        or {row.partition_family_id for row in rows} != {"resource_cycle_fcff"}
    ):
        raise ValueError("Batch 41 contract invalid")
    return rows


BATCH_41_MANIFEST = _load()
