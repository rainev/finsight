"""Immutable contract for controlled universe-reset Batch 13."""
from __future__ import annotations
from dataclasses import dataclass
from importlib.resources import files
import json
from .sec_client import normalize_cik
BATCH_13_VALUATION_DATE="2026-08-14"
BATCH_13_TICKERS=("PFE","TMO","JNJ","MRK","SYK","DHR","AMGN","COO","CAH","UNH")
@dataclass(frozen=True)
class Batch13Issuer:
 ticker:str;cik:str;issuer_name:str;role:str;boundary_reason:str|None;primary_lane_id:str;partition_family_id:str;gics_sector:str;gics_sub_industry:str
def _load():
 value=json.loads(files(__package__).joinpath('config/reset_batches_2026_08_14/batch_13.json').read_text())
 if value.get('batch')!=13 or value.get('valuation_date')!=BATCH_13_VALUATION_DATE or value.get('core_count')!=8 or value.get('boundary_count')!=2:raise ValueError('Batch 13 contract invalid')
 rows=tuple(Batch13Issuer(str(r['ticker']),normalize_cik(r['cik']),str(r['issuer_name']),str(r['role']),r.get('boundary_reason'),str(r['primary_lane_id']),str(r['partition_family_id']),str(r['gics_sector']),str(r['gics_sub_industry'])) for r in value['members'])
 if tuple(r.ticker for r in rows)!=BATCH_13_TICKERS or len({r.cik for r in rows})!=10:raise ValueError('Batch 13 denominator changed')
 return rows
BATCH_13_MANIFEST=_load()
