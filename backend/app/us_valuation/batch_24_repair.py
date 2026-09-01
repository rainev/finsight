"""User-authorized whole-Conditional repair for controlled Batch 24."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from .baseline import AvailabilityType
from .batch_24 import BATCH_24_TICKERS
from .batch_24_history import CONDITIONAL_TICKERS,build_batch_24_history_result
BATCH_24_REPAIR_VERSION='BATCH-24-WHOLE-CONDITIONAL-REPAIR-1.0'
ATTEMPTED_TICKERS=CONDITIONAL_TICKERS;REPAIRED_PASS_TICKERS=frozenset({'BLDR','TT','XYL','ALLE'});REPAIRED_CONDITIONAL_TICKERS=frozenset({'NOC','TDG','GNRC','HII','UBER','ETN'});REPAIRED_WITHHELD_TICKERS=frozenset()
RELEASE={'NOC':'Stable B-21/program cash, completed capacity investment, and resolved environmental tail.','TDG':'Stable acquired cash conversion, final subsequent acquisitions, and materially reduced leverage.','GNRC':'Full-year or pro-forma acquired cash conversion plus bounded warranty, tariff, and channel exposure.','HII':'Positive stable shipbuilding post-capex cash and source-bounded delivery/program conversion.','UBER':'Stable marketplace cash and bounded restricted funds, driver/merchant balances, acquisitions, investments, and claims.','ETN':'Complete post-acquisition operating cash, final accounting/funding, and normalized integration/supplier-finance state.'}
def _versioned(r,t):
 v=deepcopy(r);v['model_version']=BATCH_24_REPAIR_VERSION;v['baseline']={**v['baseline'],'method_version':BATCH_24_REPAIR_VERSION};v['source_ledger']={**v['source_ledger'],'whole_conditional_repair':{'repair_scope':'user_authorized_batch_24_conditional_revisit','repair_attempted':t in ATTEMPTED_TICKERS,'initial_availability_type':r['availability_type'],'release_condition':RELEASE.get(t),'market_price_used':False,'analyst_target_used':False}};return v
def build_batch_24_repair_result(*,ticker:str,source_root:Path,structural_root:Path):
 if ticker not in BATCH_24_TICKERS:raise ValueError(ticker)
 r=build_batch_24_history_result(ticker=ticker,source_root=source_root,structural_root=structural_root);return _versioned(r,ticker)
if REPAIRED_PASS_TICKERS|REPAIRED_CONDITIONAL_TICKERS|REPAIRED_WITHHELD_TICKERS!=set(BATCH_24_TICKERS):raise RuntimeError('Batch24 repair mismatch')
