#!/usr/bin/env python3
"""Read-only source audit for possible Batch 34 conditional-to-pass recovery."""
from __future__ import annotations

import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.parts: list[str] = []
    def handle_data(self, data: str) -> None: self.parts.append(data)


def text(path: Path) -> str:
    p = _Text(); p.feed(path.read_text(errors="replace")); return " ".join(p.parts)


def tree_hash(root: Path) -> str:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and ".sec-cache" not in p.parts):
        rel = path.relative_to(root).as_posix()
        rows.append(rel.encode() + b"\0" + hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
    return hashlib.sha256(b"".join(rows)).hexdigest()


def run(*, root: Path, output_root: Path) -> dict:
    packet_root = root / "output/batch-34-sec-source-packets-20260903"
    structural_root = root / "output/batch-34-structural-sources-20260903"
    event_root = root / "output/batch-34-event-sources-20260903"
    controls = []
    for path in sorted(p for p in packet_root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        manifest = json.loads((path / "source-manifest.json").read_text())
        rows = [r for r in manifest["eligible_filings"] if r["form"] in {"10-Q", "10-K"}]
        row = max(rows, key=lambda r: (r["filed"], r["accession"]))
        recent = json.loads((path / "submissions.json").read_text())["filings"]["recent"]
        i = recent["accessionNumber"].index(row["accession"])
        controls.append({"ticker": path.name, "accession": row["accession"], "filed": row["filed"], "report_date": recent["reportDate"][i], "form": row["form"]})
    capital_terms = {
        "USB": ["common equity tier 1 capital 10.8", "tier 1 capital 12.2", "total risk-based capital 14.4", "leverage 8.9", "well-capitalized"],
        "KEY": ["common equity tier 1 11.17", "tier 1 risk-based capital 12.78", "total capital 8.00", "10.32", "parent company generally maintains cash"],
        "NTRS": ["common equity tier 1 capital 12.2", "tier 1 capital 13.1", "total capital 15.5", "tier 1 leverage 7.6"],
        "STT": ["standardized cet1 capital ratio decreased to 10.8%", "tier 1 leverage ratio was 5.3%", "common equity tier 1 capital"],
        "TFC": ["capital ratios, which include cet1 capital, tier 1 capital, and total capital", "above the regulatory", "stress testing on its capital levels"],
    }
    capital_evidence = {}
    for ticker, terms in capital_terms.items():
        html = next(structural_root.parent.joinpath("batch-34-structural-cache-20260903/filings").glob(ticker + "/**/" + ticker.lower() + "-20260630.htm"))
        body = text(html).lower()
        capital_evidence[ticker] = {"document": str(html.relative_to(root)), "sha256": hashlib.sha256(html.read_bytes()).hexdigest(), "terms_found": {term: term in body for term in terms}}
    matrix = [
        {"ticker":"BRO","decision":"CONDITIONAL AFTER MODEL CHALLENGE","evidence":"Preferred absence and $25M NCI are repaired, but 2025 acquisition cash was $7.854B across 43 acquisitions; TTM acquisition cash is $7.723B and pro-forma revenue was $6.947B versus $5.902B reported.","remaining_work":"Bound acquisition/reinvestment economics before restoring Pass; retain residual income rather than an acquisition-blind FCFF shortcut."},
        {"ticker":"USB","decision":"PASS REPAIR COMPLETE","evidence":"5 annual common-earnings periods; $60.624B parent equity; $6.808B preferred claim; 10-Q capital ratios 10.8% CET1, 12.2% Tier 1, 14.4% total, 8.9% leverage and well-capitalized statement.","remaining_work":"None for current Pass gate; ordinary credit/capital uncertainty remains in the scenario range."},
        {"ticker":"KEY","decision":"PASS CANDIDATE AFTER REPAIR","evidence":"5 annual periods; $17.298B common equity after reported $2.5B preferred; parent liquidity disclosure ($5.3B cash/short-term investments); 10-Q estimated CET1 11.17%, Tier 1 12.78%, total 14.82%, leverage 10.32%.","remaining_work":"Record that capital ratios are estimates and preserve Sep-15 preferred redemption as post-cutoff/not completed."},
        {"ticker":"TFC","decision":"PASS CANDIDATE AFTER REPAIR","evidence":"5 annual common-earnings periods; $58.684B common equity after $5.411B preferred; 10-Q explicitly reports CET1/Tier 1/total capital framework and stress testing; note offering is separately captured.","remaining_work":"Extract exact ratio table values and record $1.25B July note issuance as a post-quarter debt event; keep risk caveat."},
        {"ticker":"L","decision":"CONDITIONAL PENDING REPAIR","evidence":"5 annual periods; $19.115B parent equity; $917M NCI separately reported; parent-attributable earnings are repaired; detailed reserve and liquidity disclosures exist.","remaining_work":"Add bounded reserve/catastrophe/subsidiary-dividend and parent-liquidity treatment."},
        {"ticker":"SPGI","decision":"CONDITIONAL PENDING REPAIR","evidence":"5 annual periods; $31.501B parent equity; NCI-attributable earnings are removed; 294.8M xbrli:shares.","remaining_work":"Build a ratings/data history route that bounds acquisition integration and recurring content/software investment."},
        {"ticker":"PGR","decision":"CONDITIONAL PENDING REPAIR","evidence":"5 annual periods; $34.333B equity; 581.4M shares; insurance investment, claims, reserve and underwriting evidence.","remaining_work":"Add explicit catastrophe/reserve/investment sensitivity and source-bound statutory capital/preferred absence."},
        {"ticker":"TRV","decision":"CONDITIONAL PENDING REPAIR","evidence":"5 annual common-earnings periods; $33.121B equity; reserve/reinsurance evidence; $750M note event is finite.","remaining_work":"Bound statutory capital, catastrophe/reserve sensitivity, preferred absence, July notes and $1.55B unfunded commitment."},
        {"ticker":"NTRS","decision":"CONDITIONAL AFTER CLAIM REPAIR","evidence":"Exact Series D/E carrying values total $884.9M; capital ratios are 12.2% CET1, 13.1% Tier 1, 15.5% total and 7.6% leverage.","remaining_work":"Retain the post-cutoff redemption state and bound remaining custody/capital economics before Pass."},
        {"ticker":"STT","decision":"CONDITIONAL AFTER CLAIM REPAIR","evidence":"Exact June preferred values total $3.559B; Series L adds a $500M claim and approximately $495M proceeds before cutoff; 10-Q reports 10.8% CET1 and 5.3% leverage.","remaining_work":"Bind the broader capital and custody-fee gate before Pass."},
    ]
    result = {"schema_version":"FINSIGHT-BATCH-34-RECOVERY-SOURCE-AUDIT-2","audit_stage":"post_sol_repair","valuation_date":"2026-08-14","controls":controls,"capital_evidence":capital_evidence,"matrix":matrix,"source_tree_hash":tree_hash(packet_root),"structural_tree_hash":tree_hash(structural_root),"event_tree_hash":tree_hash(event_root),"serving_artifacts_changed":False}
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "recovery-source-audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); parser.add_argument("--output-root",type=Path,required=True); print(json.dumps(run(**vars(parser.parse_args())),sort_keys=True))


if __name__ == "__main__": main()
