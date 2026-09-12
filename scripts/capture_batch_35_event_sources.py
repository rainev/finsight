#!/usr/bin/env python3
"""Build a complete cutoff-event ledger for controlled Batch 35."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_35 import BATCH_35_MANIFEST, BATCH_35_VALUATION_DATE
from app.us_valuation.sec_client import SecClient, sec_archive_url


def _json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _immutable(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise RuntimeError(f"immutable event evidence differs: {path}")
    else:
        path.write_bytes(raw)


ACCEPTED = {
    "WMB": {
        "accession": "0001193125-26-301533", "filed": "2026-07-13", "report_date": "2026-07-10", "form": "8-K", "items": "7.01,9.01",
        "documents": (("d152507d8k.htm", "3ce2cfd8cbce675473f5690676303a181643869424107bcaf6d45a5b4da03aba"), ("d152507dex991.htm", "99fa82af5c142a0a061651993a100dcef9d145c4c3ba4f1148635a9350e10130"), ("d152507dex992.htm", "12f0400101bb7e8bee8547c3fa7b07d6c5693f1779a71cba3bfd78d27c188673")),
        "reported_terms": {"committed_capital": 5_340_000_000, "noncontrolling_interest_pct": .49, "expected_growth_capex_funding": 4_400_000_000, "additional_consideration_approx": 900_000_000},
        "treatment": "Accepted material signed Power Innovation JV financing. The capital, 49% NCI, and project funding are event-conditioned and are not retroactively inserted into the June 30 operating bridge; they remain a public warning and invalidation trigger until closing/project cash economics are filed.",
    },
    "SCHW": {
        "accession": "0001193125-26-347083", "filed": "2026-08-12", "report_date": "2026-08-10", "form": "8-K", "items": "8.01,9.01",
        "documents": (("d42452d8k.htm", "b4bd6da9691472112fcafd93cef626ac7ca642430fc6340acbd77a721528c19c"),),
        "reported_terms": {"senior_notes_2032_principal": 1_250_000_000, "senior_notes_2037_principal": 1_350_000_000, "total_principal": 2_600_000_000, "net_proceeds_approx": 2_582_000_000, "coupon_2032": .05108, "coupon_2037": .05655, "annualized_gross_interest": 140_192_500},
        "treatment": "Accepted post-quarter note issuance. Principal and proceeds offset at issuance for equity-book-value purposes; forward common earnings use a governed zero-to-illustrative-after-tax interest sensitivity because use-of-proceeds income is not reported.",
    },
    "PNC": {
        "accession": "0001628280-26-048994", "filed": "2026-07-21", "report_date": "2026-07-16", "form": "8-K", "items": "8.01,9.01",
        "documents": (("pnc-20260716.htm", "4825c925382d6d39fda84fa8d645db98d9fe9744fffdc85b3eb3c081829ce953"),),
        "reported_terms": {"senior_notes_2030_principal": 1_000_000_000, "senior_notes_2037_principal": 1_000_000_000, "total_principal": 2_000_000_000, "coupon_2030": .04831, "coupon_2037": .05463, "annualized_gross_interest": 102_940_000},
        "treatment": "Accepted post-quarter note issuance. Principal and proceeds offset at issuance for equity-book-value purposes; forward common earnings use a governed zero-to-illustrative-after-tax interest sensitivity because use-of-proceeds income is not reported.",
    },
    "CFG": {
        "accession": "0001193125-26-326411", "filed": "2026-07-31", "report_date": "2026-07-27", "form": "8-K", "items": "3.03,5.03,8.01,9.01",
        "documents": (("d144911d8k.htm", "3692e873a08da6c2a2e0d54adafaf171129b9f015c10b18a3808af58c98e6536"),),
        "reported_terms": {"series": "J", "preferred_shares": 400_000, "liquidation_preference_per_share": 1_000, "preferred_claim": 400_000_000, "coupon": .0675, "annual_preferred_dividend": 27_000_000},
        "treatment": "Accepted Series J preferred issuance. The $400M proceeds and $400M preferred claim offset in current common book equity; the $27M annual dividend is a forward common-earnings sensitivity.",
    },
    "JKHY": {
        "accession": "0000779152-26-000052", "filed": "2026-08-11", "report_date": "2026-08-11", "form": "8-K", "items": "2.02,9.01",
        "documents": (("jkhy-20260811.htm", "fb46a1d8dd03bcf12bf86c0ad585f89d4931afd5b658bd4244aab3e39737e8f9"), ("jkhy-prdatedaugust112026xq.htm", "66c95d5c6a5d993e197dc41333a3e165f4c07b5b94f9fb7c4d9e3227be3e7cdc")),
        "reported_terms": {"fiscal_year_end": "2026-06-30", "q4_deconversion_revenue": 9_300_000, "fy_deconversion_revenue": 42_800_000},
        "treatment": "Accepted cutoff disclosure. Deconversion revenue is reported but excluded from normalized recurring earnings because the issuer describes it as non-recurring and outside ongoing operations; the filing does not provide FY GAAP earnings, equity, or shares.",
    },
}


REJECTED = {
    "WFC": {"accession": "0000072971-26-000288", "filed": "2026-07-14", "report_date": "2026-07-14", "form": "8-K", "items": "2.02,7.01,9.01", "reason": "Earnings release superseded by the later controlling 10-Q."},
    "AON": {"accession": "0001628280-26-050367", "filed": "2026-07-29", "report_date": "2026-07-29", "form": "8-K", "items": "2.02,9.01", "reason": "Duplicate earnings release covered by the same-day controlling 10-Q."},
    "GL": {"accession": "0000320335-26-000218", "filed": "2026-08-07", "report_date": "2026-08-07", "form": "8-K", "items": "5.02", "reason": "Director retirement disclosed no operating disagreement or finite valuation input."},
    "AJG": {"accession": "0001628280-26-051070", "filed": "2026-07-30", "report_date": "2026-07-30", "form": "8-K", "items": "2.02,7.01", "reason": "Earnings release superseded by the later controlling 10-Q."},
    "RJF": {"accession": "0000720005-26-000066", "filed": "2026-07-22", "report_date": "2026-07-22", "form": "8-K", "items": "2.02,9.01", "reason": "Earnings release superseded by the later controlling 10-Q."},
}


def _submission_row(source_root: Path, ticker: str, accession: str) -> dict:
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    recent = submissions["filings"]["recent"]
    index = recent["accessionNumber"].index(accession)
    return {name: recent[name][index] for name in ("accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument")}


def _reuse_document(reuse_roots: tuple[Path, ...], ticker: str, name: str) -> bytes | None:
    for root in reuse_roots:
        for path in (root / ticker / name, root / name):
            if path.exists():
                return path.read_bytes()
    return None


def capture(*, source_root: Path, output_root: Path, reuse_roots: tuple[Path, ...] = (), user_agent: str | None = None) -> dict:
    source_root, output_root = Path(source_root), Path(output_root)
    reuse_roots = tuple(map(Path, reuse_roots))
    if any(part in {"backend", "frontend"} for part in output_root.parts):
        raise ValueError("event evidence must remain outside serving roots")
    client: SecClient | None = None
    cases = []
    for issuer in BATCH_35_MANIFEST:
        definition = ACCEPTED.get(issuer.ticker) or REJECTED[issuer.ticker]
        row = _submission_row(source_root, issuer.ticker, definition["accession"])
        if row["filingDate"] != definition["filed"] or row["form"] != definition["form"] or row["filingDate"] > BATCH_35_VALUATION_DATE:
            raise ValueError(f"{issuer.ticker}: cutoff event identity mismatch")
        source_manifest_path = source_root / issuer.ticker / "source-manifest.json"
        common = {"schema_version": "FINSIGHT-BATCH-35-EVENT-LEDGER-1", "valuation_date": BATCH_35_VALUATION_DATE, "ticker": issuer.ticker, "cik": issuer.cik, "decision": "accepted" if issuer.ticker in ACCEPTED else "rejected", "screened_filing": {"accession": definition["accession"], "filed": definition["filed"], "report_date": definition["report_date"], "form": definition["form"], "items": definition["items"], "primary_document": row["primaryDocument"]}, "source_manifest_sha256": _sha(source_manifest_path.read_bytes())}
        if issuer.ticker in ACCEPTED:
            documents = []
            for name, expected_hash in definition["documents"]:
                raw = _reuse_document(reuse_roots, issuer.ticker, name)
                if raw is None:
                    client = client or SecClient(user_agent=user_agent, cache_dir=output_root / ".sec-cache")
                    raw = client.filing_attachment(issuer.cik, definition["accession"], name, max_bytes=12 * 1024 * 1024)
                if _sha(raw) != expected_hash:
                    raise ValueError(f"{issuer.ticker}: event document hash mismatch for {name}")
                _immutable(output_root / issuer.ticker / name, raw)
                documents.append({"document": name, "url": sec_archive_url(issuer.cik, definition["accession"], name), "sha256": expected_hash})
            receipt = {**common, "documents": documents, "reported_terms": definition["reported_terms"], "treatment": definition["treatment"]}
        else:
            receipt = {**common, "documents": [], "reported_terms": {}, "treatment": definition["reason"]}
        _immutable(output_root / issuer.ticker / "source-receipt.json", _json(receipt))
        cases.append({"ticker": issuer.ticker, "accession": definition["accession"], "decision": receipt["decision"], "source_receipt_sha256": _sha(_json(receipt))})
    summary = {"schema_version": "FINSIGHT-BATCH-35-EVENT-LEDGER-1", "valuation_date": BATCH_35_VALUATION_DATE, "attempted": 10, "accepted": sum(row["decision"] == "accepted" for row in cases), "rejected": sum(row["decision"] == "rejected" for row in cases), "cases": cases, "serving_artifacts_changed": False}
    _immutable(output_root / "summary.json", _json(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--reuse-root", action="append", default=[], type=Path)
    parser.add_argument("--user-agent")
    args = vars(parser.parse_args())
    args["reuse_roots"] = tuple(args.pop("reuse_root"))
    print(json.dumps(capture(**args), sort_keys=True))


if __name__ == "__main__":
    main()
