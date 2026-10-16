"""Immutable contract for controlled universe-reset Batch 45."""
from __future__ import annotations
from dataclasses import dataclass
from importlib.resources import files
import json
from .sec_client import normalize_cik

BATCH_45_VALUATION_DATE="2026-08-14"
BATCH_45_TICKERS=("AEP","ETR","ES","XEL","SO","LNT","D","PNW","WEC","PEG")

@dataclass(frozen=True)
class Batch45Issuer:
    ticker:str;cik:str;issuer_name:str;role:str;boundary_reason:str|None;primary_lane_id:str;partition_family_id:str;gics_sector:str;gics_sub_industry:str

def _load()->tuple[Batch45Issuer,...]:
    value=json.loads(files(__package__).joinpath("config/reset_batches_2026_08_14/batch_45.json").read_text()); rows=tuple(Batch45Issuer(ticker=str(r["ticker"]),cik=normalize_cik(r["cik"]),issuer_name=str(r["issuer_name"]),role=str(r["role"]),boundary_reason=r.get("boundary_reason"),primary_lane_id=str(r["primary_lane_id"]),partition_family_id=str(r["partition_family_id"]),gics_sector=str(r["gics_sector"]),gics_sub_industry=str(r["gics_sub_industry"])) for r in value["members"])
    if value.get("batch")!=45 or value.get("valuation_date")!=BATCH_45_VALUATION_DATE or value.get("core_count")!=8 or value.get("boundary_count")!=2 or tuple(r.ticker for r in rows)!=BATCH_45_TICKERS or len({r.cik for r in rows})!=10 or {r.partition_family_id for r in rows}!={"utility_fcfe"}: raise ValueError("Batch 45 contract invalid")
    return rows
BATCH_45_MANIFEST=_load()
