#!/usr/bin/env python3
"""Build the complete cutoff-event screening ledger for Batch 36."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.us_valuation.batch_36 import BATCH_36_MANIFEST, BATCH_36_VALUATION_DATE


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
    "FISV": {"decision": "accepted", "filings": (("0000798354-26-000028", "2026-08-06", "8-K"), ("0001193125-26-297448", "2026-07-07", "8-K")), "documents": (("d110419d8k.htm", "1314b10f850ae796acea50201dfa841c7fd693ea173ef39d615021ba9e221f76"),), "reported_terms": {"president_resignation_effective": "2026-07-07", "financial_solutions_interim_leadership_effective": "2026-07-07"}, "treatment": "The August earnings release is superseded by the controlling 10-Q. The July President resignation and interim Financial Solutions leadership are accepted as a qualitative execution warning; no unsupported cash adjustment is invented."},
    "AMP": {"decision": "rejected", "filings": (("0000820027-26-000038", "2026-07-23", "8-K"),), "treatment": "Duplicate earnings release superseded by the August 4 controlling 10-Q; June note issuance is already inside the current balance sheet."},
    "C": {"decision": "rejected", "filings": (("0001104659-26-083383", "2026-07-14", "8-K"),), "treatment": "Duplicate earnings release superseded by the August 6 controlling 10-Q. The July common-dividend declaration and Banamex pending 1.4% sale remain controlling-filing event context."},
    "HIG": {"decision": "rejected", "filings": (("0000874766-26-000062", "2026-08-11", "8-K"),), "documents": (("hig-20260811.htm", "41337eaea5edd0fb580d021fb6763dde06c4533577bf0ecd27692e1cd45469fd"),), "treatment": "Post-quarter independent-director appointment; no operating disagreement, related-party transaction, or material valuation input."},
    "GS": {"decision": "accepted", "filings": (("0001193125-26-310408", "2026-07-21", "8-K"), ("0001193125-26-318147", "2026-07-27", "8-K"), ("0001193125-26-344912", "2026-08-11", "8-K")), "documents": (("d102046d8k.htm", "e3b82663942aad6c1529be8c24c68585984558ac7460b0dbd4a4aac7d018e5d6"), ("d113214d8k.htm", "ebe313af74d9c38df2bb14fa6019624ace42eb04c34a5d1cc1f36592ef82337b"), ("d179572d8k.htm", "ebdfae9ecb30a7b11ace2f787a210c07f5d7e49d81f9f1ca32d60bf8a84130b3")), "reported_terms": {"debt_tranches": ({"principal": 3_500_000_000, "coupon": .05240}, {"principal": 3_500_000_000, "coupon": .05655}, {"principal": 3_000_000_000, "coupon": .06215}), "debt_principal": 10_000_000_000, "annualized_gross_interest": 567_775_000, "governed_interest_tax_rate": .21, "annualized_after_tax_interest": 448_542_250, "series_aa_shares": 100_000, "series_aa_liquidation_per_share": 25_000, "series_aa_claim": 2_500_000_000, "series_aa_coupon": .065, "series_u_redemption": 750_000_000, "series_u_coupon": .0365, "net_preferred_claim_and_proceeds": 1_750_000_000, "net_annual_preferred_dividend_increase": 135_125_000}, "treatment": "The July $10B note issuance is accepted as equity-model operating funding; it is not EV-bridged, but its $567.775M gross coupon is scenario-adjusted for tax and proceeds income. Series AA issuance and completed Series U redemption add net $1.75B proceeds and preferred claim once, leaving current common book equity unchanged; the $135.125M net preferred dividend also reduces forward common earnings."},
    "MS": {"decision": "rejected", "filings": (("0000895421-26-000207", "2026-07-15", "8-K"),), "treatment": "Duplicate earnings release superseded by the August 4 controlling 10-Q."},
    "CB": {"decision": "accepted", "filings": (("0001193125-26-310312", "2026-07-21", "8-K"),), "reported_terms": {"buyback_authorization": 7_500_000_000, "july_repurchase_shares": 40_000, "july_repurchase_cash": 14_000_000, "cutoff_share_observation": 385_799_859}, "treatment": "The earnings release is superseded by the controlling 10-Q, but the filing's July buyback authorization and executed 40,000-share repurchase are accepted as cutoff event context. Use the latest cutoff share denominator; do not deduct authorization as a claim."},
    "ALL": {"decision": "accepted", "filings": (("0000899051-26-000117", "2026-08-05", "8-K"),), "reported_terms": {"oklahoma_litigation_loss_probable": False, "management_expects_material_financial_position_loss": False, "july_common_dividend_per_share": 1.08, "december_debt_maturity": 550_000_000}, "treatment": "The earnings release is superseded by the controlling 10-Q, while the July Oklahoma litigation, paid common dividend, and December maturity are accepted as current warning/liquidity context. No unreported litigation reserve is invented."},
    "COF": {"decision": "rejected", "filings": (("0000927628-26-000083", "2026-07-21", "8-K"), ("0000927628-26-000084", "2026-07-21", "8-K")), "treatment": "Earnings release and June monthly credit metrics are superseded by the July 28 combined-company 10-Q. Discover/Brex integration and provisional purchase accounting remain controlling-filing event context."},
    "VLO": {"decision": "accepted", "filings": (("0001628280-26-048495", "2026-07-16", "8-K"), ("0001628280-26-050937", "2026-07-30", "10-Q")), "documents": (("vlo-20260716.htm", "bfd829a559bcf1a65d25f144d61717b273b50d9dd01398323cc0fbf03ac8f3e0"),), "reported_terms": {"additional_buyback_authorization": 5_000_000_000, "july_debt_repayment": 100_000_000, "port_arthur_insurance_receivable": 78_000_000, "port_arthur_repair_costs": 15_000_000, "port_arthur_planned_incident_capital": 250_000_000, "port_arthur_claims_estimable": False}, "treatment": "The July 16 8-K proves only the additional buyback authorization; no authorized amount is deducted. The July 30 controlling 10-Q separately proves the July debt repayment and Port Arthur fire/claim state. Port Arthur claims cannot be reasonably estimated, so the initial intrinsic result remains withheld pending one recovery attempt."},
}


def _submission_filing(source_root: Path, ticker: str, accession: str) -> dict:
    recent = json.loads((Path(source_root) / ticker / "submissions.json").read_text())["filings"]["recent"]
    index = recent["accessionNumber"].index(accession)
    return {key: recent[key][index] for key in ("accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument")}


def capture(*, source_root: Path, output_root: Path, reuse_root: Path) -> dict:
    source_root, output_root, reuse_root = map(Path, (source_root, output_root, reuse_root))
    cases = []
    for issuer in BATCH_36_MANIFEST:
        definition = EVENTS[issuer.ticker]
        filings = []
        for accession, filed, form in definition["filings"]:
            row = _submission_filing(source_root, issuer.ticker, accession)
            if row["filingDate"] != filed or row["form"] != form or filed > BATCH_36_VALUATION_DATE:
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
        receipt = {"schema_version": "FINSIGHT-BATCH-36-EVENT-LEDGER-1", "valuation_date": BATCH_36_VALUATION_DATE, "ticker": issuer.ticker, "cik": issuer.cik, "decision": definition["decision"], "screened_filings": filings, "documents": documents, "reported_terms": definition.get("reported_terms", {}), "treatment": definition["treatment"], "source_manifest_sha256": _sha(source_manifest.read_bytes())}
        raw = _json(receipt)
        _immutable(output_root / issuer.ticker / "source-receipt.json", raw)
        cases.append({"ticker": issuer.ticker, "decision": definition["decision"], "source_receipt_sha256": _sha(raw)})
    summary = {"schema_version": "FINSIGHT-BATCH-36-EVENT-LEDGER-1", "valuation_date": BATCH_36_VALUATION_DATE, "attempted": 10, "accepted": sum(row["decision"] == "accepted" for row in cases), "rejected": sum(row["decision"] == "rejected" for row in cases), "cases": cases, "serving_artifacts_changed": False}
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
