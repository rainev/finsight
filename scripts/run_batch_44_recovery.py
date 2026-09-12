#!/usr/bin/env python3
"""Stage Batch 44 recovery and whole-batch range recalibration without bookkeeping writes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT/"backend") not in sys.path: sys.path.insert(0,str(ROOT/"backend"))
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_44 import BATCH_44_MANIFEST
from app.us_valuation.batch_44_recovery import ATTEMPTED,BATCH_44_RECOVERY_VERSION,build_batch_44_recovery_result
from run_batch_07_history import PROTECTED,WATCHLIST,_immutable,_json,_tree
from run_batch_15_history import WITHHELD_REGISTER
from run_batch_44_history import _public as _initial_public

APPROVED_INITIAL_REPORT_SHA256="af8530bf8b549a4ef460315cbbd92d36f852eaa10b86c18860dda37ea7fd1ed8"


def _sha(path:Path)->str:return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _public(issuer,result):
    value=_initial_public(issuer,result); value["public_assumptions"]["forecast_policy_version"]=BATCH_44_RECOVERY_VERSION; value["forecast_quality"]["policy_version"]=BATCH_44_RECOVERY_VERSION; value["methodology"]["forecast_policy"]=BATCH_44_RECOVERY_VERSION; value["issuer"]["classification_reason"]="Frozen Batch 44 sources plus one controlled withheld recovery and whole-batch moderated multi-factor range review."; value["model_policy"]["reason"]=result["warning"]
    value["public_assumptions"]["share_count_basis"]="The calculator's share fields are governed scenario denominators anchored to the latest reported common shares; the +/-0.75% range is a disclosed dilution stress."
    if issuer.ticker=="BKR": value["public_assumptions"]["forecast_mode"]="withheld_after_post_chart_recovery_attempt"
    if result.get("history_reliability") is not None: value["reliability"]=result["history_reliability"]
    value.pop("automated_review",None); value=sanitize_public_artifact(value)
    if value["availability_type"]!=result["availability_type"] or value["scenario_range"]["base"]!=result["scenario_range"]["base"] or value["model_policy"]["primary"]!="fcff_dcf": raise RuntimeError(issuer.ticker)
    return value


def run(*,initial_root:Path,source_root:Path,structural_root:Path,event_root:Path,output_root:Path,structural_cache_root:Path,special_annual_root:Path,xom_annual_root:Path):
    initial_report_path=Path(initial_root)/"batch-44-report.json"; initial_report=json.loads(initial_report_path.read_text())
    if _sha(initial_report_path)!=APPROVED_INITIAL_REPORT_SHA256 or (initial_report["pass_count"],initial_report["conditional_count"],initial_report["withheld_count"])!=(0,7,3): raise ValueError("confirmed Batch 44 initial result required")
    before={str(path):_tree(path) for path in PROTECTED}; watchlist_hash=_sha(WATCHLIST); withheld_hash=_sha(WITHHELD_REGISTER); cases=[]
    for issuer in BATCH_44_MANIFEST:
        result=build_batch_44_recovery_result(ticker=issuer.ticker,source_root=source_root,structural_root=structural_root,event_root=event_root,structural_cache_root=structural_cache_root,special_annual_root=special_annual_root,xom_annual_root=xom_annual_root); public=_public(issuer,result); outcome="conditional" if result["availability_type"]=="conditional_estimate" else "withheld"; label=result["history_reliability"]["label"] if result["history_reliability"] else None; case={"ticker":issuer.ticker,"outcome":outcome,"availability_type":result["availability_type"],"reliability":label,"method":result["method"],**result["scenario_range"],"warning":result["warning"]}; private={"schema_version":"FINSIGHT-BATCH-44-RECOVERY-1","batch":44,"issuer":{"ticker":issuer.ticker,"cik":issuer.cik},"recovery":result,"controlled_outcome":case}; _immutable(output_root/"generated"/issuer.ticker/"valuation-private.json",_json(private)); _immutable(output_root/"staged-public"/f"{issuer.ticker}.json",_json(public)); cases.append(case)
    if before!={str(path):_tree(path) for path in PROTECTED} or watchlist_hash!=_sha(WATCHLIST) or withheld_hash!=_sha(WITHHELD_REGISTER): raise RuntimeError("protected or bookkeeping state changed")
    report={"schema_version":"FINSIGHT-BATCH-44-RECOVERY-REPORT-1","batch":44,"attempted_count":3,"attempted_tickers":[issuer.ticker for issuer in BATCH_44_MANIFEST if issuer.ticker in ATTEMPTED],"recovered_to_conditional_tickers":["AMCR","SW"],"still_withheld_tickers":["BKR"],"whole_batch_recalibrated_tickers":[issuer.ticker for issuer in BATCH_44_MANIFEST if issuer.ticker not in ATTEMPTED],"pass_count":0,"conditional_count":sum(row["outcome"]=="conditional" for row in cases),"withheld_count":sum(row["outcome"]=="withheld" for row in cases),"numeric_count":sum(row["outcome"]!="withheld" for row in cases),"serving_artifacts_changed":False,"watchlist_changed":False,"withheld_register_changed":False,"watchlist_sha256":watchlist_hash,"withheld_register_sha256":withheld_hash,"cases":cases}; _immutable(output_root/"batch-44-recovery-report.json",_json(report)); return report


def main():
    p=argparse.ArgumentParser(); p.add_argument("--initial-root",type=Path,required=True); p.add_argument("--source-root",type=Path,required=True); p.add_argument("--structural-root",type=Path,required=True); p.add_argument("--event-root",type=Path,required=True); p.add_argument("--structural-cache-root",type=Path,required=True); p.add_argument("--special-annual-root",type=Path,required=True); p.add_argument("--xom-annual-root",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); report=run(**vars(p.parse_args())); print(json.dumps({key:report[key] for key in ("attempted_count","attempted_tickers","recovered_to_conditional_tickers","still_withheld_tickers","whole_batch_recalibrated_tickers","pass_count","conditional_count","withheld_count","numeric_count")},sort_keys=True))


if __name__=="__main__":main()
