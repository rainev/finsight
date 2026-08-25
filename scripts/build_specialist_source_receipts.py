#!/usr/bin/env python3
"""Build deterministic specialist identity packets and exact source-access receipts."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.bank_regulatory import load_bank_parent_crosswalk
from app.us_valuation.reit_supplement import parse_reit_reconciliation


VALUATION_DATE = "2026-08-14"
SERVING_ROOTS = (
    ROOT / "backend/app/data/us_valuations",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _submissions(ticker: str, root: Path) -> dict[str, Any]:
    return json.loads((root / ticker / "submissions.json").read_text(encoding="utf-8"))


def _filing(submissions: dict[str, Any], accession: str) -> dict[str, Any]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    index = accessions.index(accession)
    return {
        key: values[index]
        for key, values in recent.items()
        if isinstance(values, list) and index < len(values)
    }


def build(*, source_root: Path, identity_root: Path) -> dict[str, Any]:
    before = {str(root.resolve()): _tree_hash(root) for root in SERVING_ROOTS}
    crosswalk = load_bank_parent_crosswalk()
    banks: list[dict[str, Any]] = []
    for ticker in ("JPM", "BAC"):
        identity = crosswalk[ticker]
        submissions = _submissions(ticker, source_root)
        if str(submissions.get("cik")).zfill(10) != identity.cik:
            raise ValueError(f"{ticker}: SEC identity mismatch")
        lei_path = identity_root / f"{ticker}-lei.json"
        lei_payload = json.loads(lei_path.read_text(encoding="utf-8"))["data"]
        legal_name = lei_payload["attributes"]["entity"]["legalName"]["name"]
        if (
            lei_payload["id"] != identity.lei
            or legal_name != identity.legal_name
            or lei_payload["attributes"]["entity"].get("status") != "ACTIVE"
            or lei_payload["attributes"]["registration"].get("status") != "ISSUED"
        ):
            raise ValueError(f"{ticker}: GLEIF identity mismatch")
        banks.append(
            {
                "ticker": ticker,
                "identity": identity.as_dict(),
                "identity_sources": {
                    "sec_submissions_sha256": _sha(source_root / ticker / "submissions.json"),
                    "gleif_sha256": _sha(lei_path),
                    "rssd_profile_url": f"https://www.ffiec.gov/npw/Institution/Profile/{identity.rssd}",
                },
                "source_kind": "fr_y9c",
                "period_end_requested": "2026-06-30",
                "status": "source_access_blocked",
                "reason_codes": ["FFIEC_BULK_HTTP_403", "CURRENT_Y9C_PAYLOAD_UNAVAILABLE"],
                "attempted_source_url": "https://www.ffiec.gov/npw/FinancialReport/ReturnBHCFZipFiles?zipfilename=BHCF20260630.ZIP",
                "primary_form_url": "https://www.federalreserve.gov/apps/reportingforms/Report/Index/FR_Y-9C",
                "distribution_source": "FFIEC_NIC_FEDERAL_RESERVE_COLLECTED_DATA",
                "transport_failure": {"protocol": "HTTPS", "status": 403},
                "parent_promotable": False,
                "facts": [],
            }
        )

    nee_submissions = _submissions("NEE", source_root)
    utility = {
        "ticker": "NEE",
        "public_parent": {
            "cik": str(nee_submissions.get("cik")).zfill(10),
            "legal_name": nee_submissions.get("name"),
        },
        "regulated_entity": {"legal_name": "FLORIDA POWER & LIGHT COMPANY", "ferc_cid": None},
        "source_kind": "ferc_form_1_and_3q",
        "status": "identity_and_payload_unresolved",
        "reason_codes": [
            "FERC_CID_NOT_VERIFIED",
            "FERC_PUBLIC_XBRL_PACKET_NOT_LOCALLY_RETRIEVABLE",
            "PARENT_ALLOCATION_BRIDGE_NOT_PROVEN",
        ],
        "official_source_url": "https://www.ferc.gov/general-information-0/electric-industry-forms",
        "attempted_discovery_urls": [
            "https://ecollection.ferc.gov/",
            "https://elibrary.ferc.gov/eLibrary/search",
        ],
        "transport_failure": {
            "status": "NO_STABLE_PUBLIC_INSTANCE_DOWNLOAD_RESOLVED",
            "note": "Official pages expose viewer/eLibrary workflows but no verified FPL instance endpoint or CID was captured.",
        },
        "parent_promotable": False,
        "facts": [],
    }

    o_submissions = _submissions("O", source_root)
    accession = "0000726728-26-000028"
    filing = _filing(o_submissions, accession)
    if filing.get("form") != "8-K" or filing.get("filingDate") != "2026-05-06":
        raise ValueError("Realty Income Exhibit 99 filing identity mismatch")
    source_url = (
        "https://www.sec.gov/Archives/edgar/data/726728/"
        "000072672826000028/realtyincomeq12026supple.htm"
    )
    verified_excerpt = """
    <table><caption>Issuer-defined Q1 2026 AFFO reconciliation (USD in thousands)</caption>
      <tr><td>FFO available to common stockholders</td><td>993,601</td></tr>
      <tr><td>Straight-line rent and expenses, net</td><td>(39,510)</td></tr>
      <tr><td>Recurring capital expenditures</td><td>(170)</td></tr>
      <tr><td>AFFO available to common stockholders</td><td>1,057,553</td></tr>
      <tr><td>Occupancy</td><td>98.9%</td></tr>
    </table>
    """
    reit_packet = parse_reit_reconciliation(
        verified_excerpt,
        accession=accession,
        source_url=source_url,
        period_end="2026-03-31",
        filed_date="2026-05-06",
        valuation_date=VALUATION_DATE,
        amount_unit="USD thousands",
    )
    reit = {
        "ticker": "O",
        "source_kind": "sec_filed_exhibit_99_2",
        "accession": accession,
        "filed_date": "2026-05-06",
        "period_end": "2026-03-31",
        "source_url": source_url,
        "status": "source_link_verified_payload_not_immutable",
        "reason_codes": [
            "SEC_EXHIBIT_DISCOVERED",
            "WEB_EXTRACTED_VALUES_NOT_SOURCE_PAYLOAD",
            "MONITORED_SEC_CONTACT_NOT_CONFIGURED",
        ]
        + (
            ["AFFO_RECONCILIATION_RESIDUAL_UNEXPLAINED"]
            if reit_packet.reconciliation_status != "pass"
            else []
        ),
        "affo_definition": reit_packet.affo_definition,
        "observations": [fact.as_dict() for fact in reit_packet.facts],
        "observation_fixture_sha256": reit_packet.source_sha256,
        "raw_signed_values": reit_packet.raw_signed_values,
        "reconciliation_status": reit_packet.reconciliation_status,
        "unexplained_affo_residual": reit_packet.unexplained_affo_residual,
        "parent_promotable": False,
    }
    after = {str(root.resolve()): _tree_hash(root) for root in SERVING_ROOTS}
    if before != after:
        raise RuntimeError("protected serving artifacts changed")
    return {
        "schema_version": "FINSIGHT-SPECIALIST-SOURCE-RECEIPT-1",
        "valuation_date": VALUATION_DATE,
        "banks": banks,
        "utility": utility,
        "reit": reit,
        "serving_hash_before": before,
        "serving_hash_after": after,
        "serving_artifacts_changed": False,
        "promotable_packet_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--identity-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(source_root=args.source_root, identity_root=args.identity_root)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output.exists() and args.output.read_text(encoding="utf-8") != encoded:
        raise FileExistsError("refusing to overwrite another specialist receipt")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
