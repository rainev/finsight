"""Immutable contract for controlled universe-reset Batch 22."""
from __future__ import annotations
from dataclasses import dataclass
from importlib.resources import files
import json
from .sec_client import normalize_cik
BATCH_22_VALUATION_DATE='2026-08-14';BATCH_22_TICKERS=('HON','WM','IEX','JCI','ODFL','CPRT','LMT','WAB','ROK','FIX')
@dataclass(frozen=True)
class Batch22Issuer:
 ticker:str;cik:str;issuer_name:str;role:str;boundary_reason:str|None;primary_lane_id:str;partition_family_id:str;gics_sector:str;gics_sub_industry:str
def _load():
 v=json.loads(files(__package__).joinpath('config/reset_batches_2026_08_14/batch_22.json').read_text());rows=tuple(Batch22Issuer(str(r['ticker']),normalize_cik(r['cik']),str(r['issuer_name']),str(r['role']),r.get('boundary_reason'),str(r['primary_lane_id']),str(r['partition_family_id']),str(r['gics_sector']),str(r['gics_sub_industry'])) for r in v['members'])
 if v.get('batch')!=22 or v.get('valuation_date')!=BATCH_22_VALUATION_DATE or v.get('core_count')!=8 or v.get('boundary_count')!=2 or tuple(r.ticker for r in rows)!=BATCH_22_TICKERS or len({r.cik for r in rows})!=10:raise ValueError('Batch 22 contract invalid')
 return rows
BATCH_22_MANIFEST=_load()
