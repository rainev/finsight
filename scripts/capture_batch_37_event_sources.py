#!/usr/bin/env python3
"""Build the complete cutoff-event screening ledger for Batch 37."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_37 import BATCH_37_MANIFEST, BATCH_37_VALUATION_DATE


def _json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _immutable(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(path)
    else:
        path.write_bytes(raw)


EVENTS = {
    "IVZ": {"decision": "accepted", "filings": (("0000914208-26-000252", "2026-08-11", "8-K"), ("0000914208-26-000229", "2026-07-28", "8-K"), ("0000914208-26-000207", "2026-07-10", "8-K")), "documents": (("ivz-20260811.htm", "9d9da99a9cb2f8a2b2fddb6c45f23f265d97aac8ddb251d9ccdb89329d345f94"), ("ivzaumexhibit991-0726.htm", "7956ddb89feafc5901cc3198459fde9b1dd919d0dc9bcf4b88a127a61345b2d0")), "reported_terms": {"july_aum": 2_447_100_000_000, "june_aum": 2_470_300_000_000, "month_change": -.009, "july_long_term_net_inflows": 8_600_000_000, "july_money_market_net_inflows": 22_800_000_000, "july_market_return_effect": -59_000_000_000, "july_fx_effect": 4_600_000_000, "quarter_to_july_average_aum": 2_453_000_000_000}, "treatment": "The July AUM release is accepted as a current fee-scale diagnostic. It does not replace reported earnings or common equity and is not added as issuer cash. The July earnings and June AUM releases are superseded by the controlling 10-Q and later July AUM observation."},
    "ERIE": {"decision": "rejected", "filings": (("0001628280-26-051071", "2026-07-30", "8-K"),), "treatment": "Same-day earnings and reciprocal-insurance update is superseded by the controlling 10-Q; no distinct post-balance financing or claim event is identified."},
    "ACGL": {"decision": "rejected", "filings": (("0000947484-26-000118", "2026-07-28", "8-K"),), "treatment": "Q2 earnings release is superseded by the August 4 controlling 10-Q; no separate cutoff financing event is identified."},
    "FDS": {"decision": "rejected", "filings": (("0001628280-26-046338", "2026-07-01", "8-K"),), "treatment": "Same-day fiscal-Q3 earnings release is superseded by the controlling 10-Q; no separate cutoff financing event is identified."},
    "OKE": {"decision": "accepted", "filings": (("0001039684-26-000027", "2026-08-03", "8-K"), ("0001193125-26-332962", "2026-08-04", "424B5")), "documents": (("oke-20260803.htm", "0fdb785b9248db15ce02c606dd63f02c67cea377d6ca9bedfa6385cc3cfc74cd"), ("d132069d424b5.htm", "ad6faa56904587b7b7e0cbcedb018c6f0c4b631448def5bd11c3466fa5ce5516")), "reported_terms": {"atm_common_stock_capacity": 1_000_000_000, "sales_completed_by_cutoff_documented": False, "maximum_agent_commission_rate": .02}, "treatment": "The earnings/guidance release is superseded by the next-day controlling 10-Q. The SEC submissions item string says 2.01, while the primary document itself says 2.02; the document controls and no acquisition-close overlay is inferred. The August 4 prospectus creates up to $1B of ATM common-stock capacity but reports no completed sale, so no proceeds or dilution enter the cutoff bridge."},
    "MCO": {"decision": "rejected", "filings": (("0001059556-26-000038", "2026-08-12", "8-K"), ("0001628280-26-049104", "2026-07-22", "8-K")), "documents": (("mco-20260811.htm", "2cff06fb37fe5c5d8b0ac95e6e42592bf5b768fa7535edfd4d5378277e812697"),), "treatment": "The July earnings release is superseded by the controlling 10-Q. The August filing elects a nonemployee director effective November 1, after the valuation cutoff; it is rejected as a nonvaluation governance event."},
    "BRK.B": {"decision": "rejected", "filings": (("0001193125-26-344495", "2026-08-11", "8-K"),), "documents": (("d159922d8k.htm", "cb62a99ad3f80b47e73ee4a46c38b81632d224e3622a22b41ddb587a59129ee0"),), "treatment": "The earnings release repeats the Q2/H1 period already reported in the August 10 controlling 10-Q; no separate post-balance transaction is identified."},
    "MET": {"decision": "rejected", "filings": (("0001099219-26-000048", "2026-08-05", "8-K"),), "treatment": "Q2 earnings and operating release is superseded by the next-day controlling 10-Q; no separate cutoff financing event is identified."},
    "TROW": {"decision": "rejected", "filings": (("0001628280-26-051211", "2026-07-31", "8-K"),), "treatment": "Same-day Q2 earnings release is superseded by the controlling 10-Q; no separate cutoff financing event is identified."},
    "NDAQ": {"decision": "accepted", "filings": (("0001193125-26-292723", "2026-07-01", "8-K"), ("0001120193-26-000011", "2026-07-23", "8-K")), "documents": (("d146997d8k.htm", "c5857f51c693e9ffa66cfe9437b132f91e72e9667a2fcd025cd4ffa66af49822"),), "reported_terms": {"revolving_credit_capacity": 1_500_000_000, "term_years": 5, "benchmark_margin_low": .00875, "benchmark_margin_high": .015, "base_rate_margin_low": 0., "base_rate_margin_high": .005}, "treatment": "The June 30 amended $1.5B five-year revolving facility replaces the prior facility. It is accepted as liquidity context but not added as debt without a reported draw; the same-day earnings release is superseded by the controlling 10-Q."},
}


def _submission_filing(source_root: Path, ticker: str, accession: str) -> dict:
    recent = json.loads((Path(source_root) / ticker / "submissions.json").read_text())["filings"]["recent"]
    index = recent["accessionNumber"].index(accession)
    return {key: recent[key][index] for key in ("accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument")}


def capture(*, source_root: Path, output_root: Path, reuse_root: Path) -> dict:
    source_root, output_root, reuse_root = map(Path, (source_root, output_root, reuse_root))
    cases = []
    for issuer in BATCH_37_MANIFEST:
        definition = EVENTS[issuer.ticker]
        filings = []
        for accession, filed, form in definition["filings"]:
            row = _submission_filing(source_root, issuer.ticker, accession)
            if row["filingDate"] != filed or row["form"] != form or filed > BATCH_37_VALUATION_DATE:
                raise ValueError(f"{issuer.ticker}: event identity mismatch")
            filings.append({"accession": accession, "filed": filed, "report_date": row["reportDate"], "form": form, "items": row["items"], "primary_document": row["primaryDocument"]})
        documents = []
        for name, expected_hash in definition.get("documents", ()):
            source = reuse_root / issuer.ticker / name
            raw = source.read_bytes()
            if _sha(raw) != expected_hash:
                raise ValueError(f"{issuer.ticker}: event document hash mismatch")
            _immutable(output_root / issuer.ticker / name, raw)
            documents.append({"document": name, "sha256": expected_hash})
        source_manifest = source_root / issuer.ticker / "source-manifest.json"
        receipt = {"schema_version": "FINSIGHT-BATCH-37-EVENT-LEDGER-1", "valuation_date": BATCH_37_VALUATION_DATE, "ticker": issuer.ticker, "cik": issuer.cik, "decision": definition["decision"], "screened_filings": filings, "documents": documents, "reported_terms": definition.get("reported_terms", {}), "treatment": definition["treatment"], "source_manifest_sha256": _sha(source_manifest.read_bytes())}
        raw = _json(receipt)
        _immutable(output_root / issuer.ticker / "source-receipt.json", raw)
        cases.append({"ticker": issuer.ticker, "decision": definition["decision"], "source_receipt_sha256": _sha(raw)})
    summary = {"schema_version": "FINSIGHT-BATCH-37-EVENT-LEDGER-1", "valuation_date": BATCH_37_VALUATION_DATE, "attempted": 10, "accepted": sum(row["decision"] == "accepted" for row in cases), "rejected": sum(row["decision"] == "rejected" for row in cases), "cases": cases, "serving_artifacts_changed": False}
    _immutable(output_root / "summary.json", _json(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--reuse-root", required=True, type=Path)
    print(json.dumps(capture(**vars(parser.parse_args())), sort_keys=True))


if __name__ == "__main__":
    main()
