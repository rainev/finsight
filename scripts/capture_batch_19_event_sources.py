#!/usr/bin/env python3
"""Capture cutoff-eligible Batch 19 financing and acquisition events."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.sec_client import SecClient, sec_archive_url
from capture_batch_02_sources import PROTECTED_ROOTS, _assert_non_serving, _tree_hash
from capture_batch_02_structural_sources import _immutable_json


SOURCES = (
    {
        "ticker": "ITW",
        "cik": "0000049826",
        "accession": "0001193125-26-349149",
        "form": "8-K",
        "filed": "2026-08-13",
        "report_date": "2026-08-11",
        "primary_document": "d23818d8k.htm",
        "required_tokens": ("1.5 billion", "4.650%", "August 13, 2026", "commercial paper"),
        "reported_terms": {
            "aggregate_principal_usd": 1_500_000_000.0,
            "issue_date": "2026-08-13",
            "stated_use": "repay a portion of commercial paper; any remainder for general corporate purposes",
        },
        "treatment": "Add issued principal at the cutoff; bind exact proceeds from the companion 424B5 and do not assume the intended commercial-paper repayment occurred.",
    },
    {
        "ticker": "ITW",
        "cik": "0000049826",
        "accession": "0001193125-26-346824",
        "form": "424B5",
        "filed": "2026-08-12",
        "report_date": "2026-08-11",
        "primary_document": "d171544d424b5.htm",
        "required_tokens": ("$1,500,000,000", "1,492,470,000", "1.489"),
        "reported_terms": {
            "proceeds_before_expenses_usd": 1_492_470_000.0,
            "estimated_net_proceeds_usd": 1_489_000_000.0,
        },
        "treatment": "Add estimated net proceeds once at the cutoff and retain the issuance-cost difference conservatively.",
    },
    {
        "ticker": "NDSN",
        "cik": "0000072331",
        "accession": "0000072331-26-000034",
        "form": "8-K",
        "filed": "2026-06-03",
        "report_date": "2026-06-02",
        "primary_document": "ndsn-20260602.htm",
        "required_tokens": ("1.2 billion", "commercial paper program", "may issue"),
        "reported_terms": {
            "maximum_program_capacity_usd": 1_200_000_000.0,
            "reported_issuance_usd": None,
        },
        "treatment": "A borrowing authorization is not issued debt or available cash; add nothing without cutoff-eligible issuance evidence.",
    },
    {
        "ticker": "PH",
        "cik": "0000076334",
        "accession": "0001193125-26-349148",
        "form": "8-K",
        "filed": "2026-08-13",
        "report_date": "2026-08-13",
        "primary_document": "d105152d8k.htm",
        "required_tokens": ("9.25", "5.25", "2.50", "completed the Merger"),
        "reported_terms": {
            "filtration_group_purchase_price_usd": 9_250_000_000.0,
            "new_364_day_term_loan_usd": 5_250_000_000.0,
            "new_three_year_term_loan_usd": 2_500_000_000.0,
            "aggregate_new_term_loans_usd": 7_750_000_000.0,
            "unallocated_purchase_funding_usd": 1_500_000_000.0,
            "close_date": "2026-08-13",
        },
        "treatment": "Use a Conditional post-close cost overlay: add acquired enterprise value at reported purchase price, add the reported term loans, and reserve the remaining purchase funding; do not invent acquired cash flow or synergies.",
    },
    {
        "ticker": "DE",
        "cik": "0000315189",
        "accession": "0001104659-26-083910",
        "form": "8-K",
        "filed": "2026-07-15",
        "report_date": "2026-07-10",
        "primary_document": "de-20260710x8k.htm",
        "required_tokens": ("300,000,000", "4.850%", "July 15, 2031"),
        "reported_terms": {
            "aggregate_principal_usd": 300_000_000.0,
            "issuer": "Deere Funding Canada Corporation",
        },
        "treatment": "Record the finance-subsidiary issuance inside the equity-level model and do not apply a second enterprise-value debt bridge.",
    },
    {
        "ticker": "DE",
        "cik": "0000315189",
        "accession": "0001104659-26-083165",
        "form": "424B2",
        "filed": "2026-07-13",
        "report_date": "2026-07-10",
        "primary_document": "tm2619892-2_424b2.htm",
        "required_tokens": ("298,267,000", "300,000,000", "July 15, 2026"),
        "reported_terms": {
            "aggregate_principal_usd": 300_000_000.0,
            "estimated_net_proceeds_usd": 298_267_000.0,
            "issuance_cost_equity_effect_usd": 1_733_000.0,
        },
        "treatment": "Reduce cutoff common equity by the bounded issuance-cost difference; debt and proceeds otherwise remain inside finance earnings and common equity.",
    },
)


def run(*, output_root: Path, user_agent: str | None = None, refresh: bool = False):
    output_root = Path(output_root)
    roots = tuple(Path(root) for root in PROTECTED_ROOTS)
    _assert_non_serving(output_root, roots)
    before = {str(root): _tree_hash(root) for root in roots}
    client = SecClient(user_agent=user_agent, cache_dir=output_root.parent / ".sec-cache")
    cases = []
    for source in SOURCES:
        raw = client.filing_attachment(
            source["cik"],
            source["accession"],
            source["primary_document"],
            refresh=refresh,
            max_bytes=12 * 1024 * 1024,
        )
        text = raw.decode("utf-8", errors="replace")
        for token in source["required_tokens"]:
            if token not in text:
                raise RuntimeError(f"{source['ticker']} event term changed: {token}")
        digest = hashlib.sha256(raw).hexdigest()
        target = output_root / source["ticker"] / source["accession"]
        target.mkdir(parents=True, exist_ok=True)
        document = target / source["primary_document"]
        if document.exists() and document.read_bytes() != raw:
            raise FileExistsError(f"immutable event document differs: {document}")
        if not document.exists():
            document.write_bytes(raw)
        receipt = {
            "schema_version": "FINSIGHT-BATCH-19-EVENT-SOURCE-1",
            "valuation_date": "2026-08-14",
            **{key: value for key, value in source.items() if key != "required_tokens"},
            "url": sec_archive_url(source["cik"], source["accession"], source["primary_document"]),
            "document_sha256": digest,
            "document_bytes": len(raw),
        }
        _immutable_json(target / "source-receipt.json", receipt)
        cases.append(
            {
                "ticker": source["ticker"],
                "accession": source["accession"],
                "filed": source["filed"],
                "form": source["form"],
                "document_sha256": digest,
            }
        )
    after = {str(root): _tree_hash(root) for root in roots}
    if before != after:
        raise RuntimeError("serving changed")
    summary = {
        "attempted": len(SOURCES),
        "captured": len(cases),
        "failed": 0,
        "cases": cases,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "serving_artifacts_changed": False,
    }
    _immutable_json(output_root / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument("--refresh", action="store_true")
    print(json.dumps(run(**vars(parser.parse_args())), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
