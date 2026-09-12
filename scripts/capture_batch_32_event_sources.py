#!/usr/bin/env python3
"""Capture the cutoff-safe GoDaddy financing event used by Batch 32."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.sec_client import SecClient, sec_archive_url
from capture_batch_15_recovery_sources import _immutable


CIK = "0001609711"
ACCESSION = "0001609711-26-000092"
FILENAME = "gddy-20260731.htm"
FILED = "2026-08-04"
REPORT_DATE = "2026-07-31"


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _validate(raw: bytes) -> None:
    parser = _Text()
    parser.feed(raw.decode("utf-8", errors="replace"))
    text = " ".join(parser.parts)
    required = (
        "GoDaddy Inc.", "July 31, 2026", "new revolving credit facility of $1,200 million",
        "existing $1,000 million revolving credit facility", "maturity date of July 31, 2031",
        "at least 40%", "not greater than 5.75:1.00",
    )
    if any(value not in text for value in required):
        raise RuntimeError("GoDaddy 8-K identity or financing terms changed")


def _text(raw: bytes) -> str:
    parser = _Text()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return " ".join(parser.parts)


def _capture_document(client: SecClient, output_root: Path, *, ticker: str, cik: str, accession: str, filename: str) -> tuple[bytes, str]:
    path = output_root / ticker / filename
    raw = path.read_bytes() if path.exists() else client.filing_attachment(cik, accession, filename, max_bytes=8 * 1024 * 1024)
    digest = hashlib.sha256(raw).hexdigest()
    _immutable(path, raw)
    return raw, digest


def _capture_release_events(output_root: Path, client: SecClient) -> list[dict]:
    cases = []
    definitions = {
        "LITE": {"cik": "0001633978", "accession": "0001628280-26-055726", "filed": "2026-08-11", "report_date": "2026-06-27", "primary": "lite-20260811.htm", "exhibit": "lite_ex991xq4fy26.htm", "required": ("LUMENTUM ANNOUNCES FOURTH QUARTER AND FULL FISCAL YEAR 2026 RESULTS", "Net revenue of $1.01 billion", "3,014.0", "2,043.5", "694.9", "1,596.9", "40.5", "88.6", "101.1", "90.2", "7,756.6"), "terms": {"revenue": 3_014_000_000, "cash": 2_043_500_000, "short_term_investments": 694_900_000, "debt_current": 1_596_900_000, "debt_noncurrent": 40_500_000, "common_shares": 88_600_000, "preferred_one_for_one_shares": 2_900_000, "q4_non_gaap_diluted_shares": 101_100_000, "fy_non_gaap_diluted_shares": 90_200_000, "noncash_debt_extinguishment_loss": 7_756_600_000}},
        "SNDK": {"cik": "0002023554", "accession": "0001628280-26-053346", "filed": "2026-08-05", "report_date": "2026-07-03", "primary": "sndk-20260805.htm", "exhibit": "sndkq4-26ex991xpressrelease.htm", "required": ("Sandisk Reports Fiscal Fourth Quarter 2026 Financial Results", "20,248", "11,671", "4,762", "1,777", "155", "$14 billion"), "terms": {"revenue": 20_248_000_000, "operating_cash_flow": 11_671_000_000, "capital_expenditures": 177_000_000, "interest_expense": 73_000_000, "pretax_income": 13_017_000_000, "income_tax": 1_584_000_000, "cash": 4_762_000_000, "marketable_equity_securities": 1_777_000_000, "debt": 0, "common_shares": 149_000_000, "diluted_shares": 155_000_000, "q4_diluted_shares": 157_000_000, "new_repurchase_authorization": 14_000_000_000, "repurchase_obligation": False}},
    }
    for ticker, definition in definitions.items():
        primary, primary_hash = _capture_document(client, output_root, ticker=ticker, cik=definition["cik"], accession=definition["accession"], filename=definition["primary"])
        exhibit, exhibit_hash = _capture_document(client, output_root, ticker=ticker, cik=definition["cik"], accession=definition["accession"], filename=definition["exhibit"])
        combined = _text(primary) + " " + _text(exhibit)
        if any(value not in combined for value in definition["required"]):
            raise RuntimeError(f"{ticker} event source identity or terms changed")
        receipt = {"schema_version": "FINSIGHT-BATCH-32-EVENT-SOURCE-1", "valuation_date": "2026-08-14", "ticker": ticker, "accession": definition["accession"], "filed": definition["filed"], "report_date": definition["report_date"], "form": "8-K", "primary": {"document": definition["primary"], "url": sec_archive_url(definition["cik"], definition["accession"], definition["primary"]), "sha256": primary_hash}, "exhibit": {"document": definition["exhibit"], "url": sec_archive_url(definition["cik"], definition["accession"], definition["exhibit"]), "sha256": exhibit_hash}, "reported_terms": definition["terms"], "treatment": "Latest cutoff-safe earnings release supersedes the older quarterly operating/bridge snapshot; unaudited release status remains explicit."}
        _immutable(output_root / ticker / "source-receipt.json", (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        cases.append({"ticker": ticker, "accession": definition["accession"], "primary_sha256": primary_hash, "exhibit_sha256": exhibit_hash})
    return cases


def _capture_hpe_dividend(output_root: Path, client: SecClient) -> dict:
    ticker, cik, accession, filename = "HPE", "0001645590", "0001645590-26-000074", "hpe-20260804.htm"
    raw, digest = _capture_document(client, output_root, ticker=ticker, cik=cik, accession=accession, filename=filename)
    text = _text(raw)
    required = ("Hewlett Packard Enterprise Company", "$0.953125 per share", "September 1, 2026", "August 15, 2026")
    if any(value not in text for value in required):
        raise RuntimeError("HPE preferred-dividend event changed")
    terms_root = ROOT / "output/official-evidence-difficult-106-part-3/packages/HPE/CIK0001645590-000164559025000130"
    terms_document = next(terms_root.rglob("hpe-20251031.htm"))
    terms_raw = terms_document.read_bytes()
    terms_text = _text(terms_raw)
    if any(value not in terms_text for value in ("September 1, 2027", "2.5352", "3.1056")):
        raise RuntimeError("HPE mandatory-conversion terms changed")
    terms_manifest = json.loads((terms_document.parent / "package-manifest.json").read_text())
    terms_name = "hpe-20251031.htm"
    _immutable(output_root / ticker / terms_name, terms_raw)
    terms_url = next(item["source_url"] for item in terms_manifest["files"] if item.get("local_path") == terms_manifest["primary_document"])
    receipt = {"schema_version": "FINSIGHT-BATCH-32-EVENT-SOURCE-1", "valuation_date": "2026-08-14", "ticker": ticker, "accession": accession, "filed": "2026-08-04", "report_date": "2026-08-04", "form": "8-K", "document": filename, "url": sec_archive_url(cik, accession, filename), "document_sha256": digest, "terms_source": {"accession": "0001645590-25-000130", "filed": "2025-12-18", "report_date": "2025-10-31", "document": terms_name, "url": terms_url, "document_sha256": hashlib.sha256(terms_raw).hexdigest()}, "reported_terms": {"preferred_dividend_per_share": .953125, "preferred_shares": 30_000_000, "payment_date": "2026-09-01", "record_date": "2026-08-15", "quarterly_dividend_total": 28_593_750, "mandatory_conversion_date": "2027-09-01", "minimum_conversion_rate": 2.5352, "maximum_conversion_rate": 3.1056, "minimum_common_conversion_shares": 76_056_000, "maximum_common_conversion_shares": 93_168_000}, "treatment": "The 10-K bounds mandatory conversion and the 8-K confirms the next preferred dividend; both enter the share/dividend schedule."}
    _immutable(output_root / ticker / "source-receipt.json", (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    return {"ticker": ticker, "accession": accession, "document_sha256": digest}


def _capture_avgo_events(output_root: Path, client: SecClient) -> dict:
    ticker, cik = "AVGO", "0001730168"
    tender_accession, tender_primary_name, tender_exhibit_name = "0001193125-26-275077", "d149683d8k.htm", "d149683dex992.htm"
    tender_primary, tender_primary_hash = _capture_document(client, output_root, ticker=ticker, cik=cik, accession=tender_accession, filename=tender_primary_name)
    tender_exhibit, tender_exhibit_hash = _capture_document(client, output_root, ticker=ticker, cik=cik, accession=tender_accession, filename=tender_exhibit_name)
    apple_accession, apple_name = "0001193125-26-295589", "d84378d8k.htm"
    apple, apple_hash = _capture_document(client, output_root, ticker=ticker, cik=cik, accession=apple_accession, filename=apple_name)
    tender_text, apple_text = _text(tender_primary) + " " + _text(tender_exhibit), _text(apple)
    if any(value not in tender_text for value in ("Broadcom Inc.", "June 17, 2026", "$1,843,836,000", "$1,050,537,000", "$982.01", "$970.29")):
        raise RuntimeError("AVGO debt-tender terms changed")
    if any(value not in apple_text for value in ("Broadcom Inc.", "July 6, 2026", "through 2031", "custom ASIC silicon products")):
        raise RuntimeError("AVGO Apple agreement terms changed")
    receipt = {"schema_version": "FINSIGHT-BATCH-32-EVENT-SOURCE-1", "valuation_date": "2026-08-14", "ticker": ticker, "events": [{"accession": tender_accession, "filed": "2026-06-18", "report_date": "2026-06-17", "form": "8-K", "primary": {"document": tender_primary_name, "url": sec_archive_url(cik, tender_accession, tender_primary_name), "sha256": tender_primary_hash}, "exhibit": {"document": tender_exhibit_name, "url": sec_archive_url(cik, tender_accession, tender_exhibit_name), "sha256": tender_exhibit_hash}, "reported_terms": {"accepted_principal": 2_894_373_000, "stated_tender_consideration_before_accrued_coupon": 2_829_990_936.09, "accrued_coupon_separately_payable": True}, "treatment": "The post-quarter tender reduces cash and debt by approximately offsetting amounts; the pre-event net bridge is retained conservatively because accrued coupons are not quantified in the release."}, {"accession": apple_accession, "filed": "2026-07-06", "report_date": "2026-07-06", "form": "8-K", "document": apple_name, "url": sec_archive_url(cik, apple_accession, apple_name), "document_sha256": apple_hash, "reported_terms": {"counterparty": "Apple Inc.", "agreement_end_year": 2031, "products": "custom ASIC silicon products", "contract_value_reported": False}, "treatment": "The agreement supports revenue visibility but is not added to cash or value without reported economics."}]}
    _immutable(output_root / ticker / "source-receipt.json", (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    return {"ticker": ticker, "tender_accession": tender_accession, "apple_accession": apple_accession, "tender_exhibit_sha256": tender_exhibit_hash, "apple_sha256": apple_hash}


def capture(*, output_root: Path, user_agent: str) -> dict:
    output_root = Path(output_root)
    if any(part in {"backend", "frontend"} for part in output_root.parts):
        raise ValueError("event evidence must remain outside serving roots")
    document = output_root / "GDDY" / FILENAME
    receipt_path = output_root / "GDDY" / "source-receipt.json"
    reused = document.exists() and receipt_path.exists()
    client = SecClient(user_agent=user_agent, cache_dir=output_root / ".sec-cache")
    if reused:
        raw = document.read_bytes()
    else:
        raw = client.filing_attachment(CIK, ACCESSION, FILENAME, max_bytes=5 * 1024 * 1024)
    _validate(raw)
    digest = hashlib.sha256(raw).hexdigest()
    receipt = {
        "schema_version": "FINSIGHT-BATCH-32-EVENT-SOURCE-1", "valuation_date": "2026-08-14",
        "ticker": "GDDY", "accession": ACCESSION, "filed": FILED, "report_date": REPORT_DATE, "form": "8-K",
        "url": sec_archive_url(CIK, ACCESSION, FILENAME), "document": FILENAME, "document_sha256": digest,
        "reported_terms": {"new_revolver_commitment": 1_200_000_000, "replaced_revolver_commitment": 1_000_000_000, "maturity": "2031-07-31", "utilization_covenant_trigger": .40, "maximum_first_lien_net_leverage_ratio": 5.75, "new_borrowing_reported": False},
        "treatment": "This changes available revolving capacity and maturity, not reported drawn debt; the June 30 debt carrying amount remains the valuation bridge until a draw is reported.",
    }
    _immutable(document, raw)
    _immutable(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    cases = [{"ticker": "GDDY", "accession": ACCESSION, "document_sha256": digest}, *_capture_release_events(output_root, client), _capture_hpe_dividend(output_root, client), _capture_avgo_events(output_root, client)]
    return {"attempted": 5, "captured": len(cases), "reused_gddy": reused, "cases": cases, "serving_artifacts_changed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--user-agent", required=True)
    print(json.dumps(capture(**vars(parser.parse_args())), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
