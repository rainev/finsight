"""Immutable contract for controlled universe-reset Batch 40."""
from __future__ import annotations
from dataclasses import dataclass
from importlib.resources import files
import json
from .sec_client import normalize_cik

BATCH_40_VALUATION_DATE = "2026-08-14"
BATCH_40_TICKERS = ("MSCI", "XYZ", "ICE", "SYF", "PYPL", "COIN", "HOOD", "TPL", "APO", "BLK")

@dataclass(frozen=True)
class Batch40Issuer:
    ticker: str
    cik: str
    issuer_name: str
    role: str
    boundary_reason: str | None
    primary_lane_id: str
    partition_family_id: str
    gics_sector: str
    gics_sub_industry: str

def _load() -> tuple[Batch40Issuer, ...]:
    value = json.loads(files(__package__).joinpath("config/reset_batches_2026_08_14/batch_40.json").read_text())
    rows = tuple(Batch40Issuer(str(row["ticker"]), normalize_cik(row["cik"]), str(row["issuer_name"]), str(row["role"]), row.get("boundary_reason"), str(row["primary_lane_id"]), str(row["partition_family_id"]), str(row["gics_sector"]), str(row["gics_sub_industry"])) for row in value["members"])
    if value.get("batch") != 40 or value.get("valuation_date") != BATCH_40_VALUATION_DATE or value.get("core_count") != 8 or value.get("boundary_count") != 2 or tuple(row.ticker for row in rows) != BATCH_40_TICKERS or len({row.cik for row in rows}) != 10:
        raise ValueError("Batch 40 contract invalid")
    return rows

BATCH_40_MANIFEST = _load()
