import gzip
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_nci_equity_difference import (
    ParentNciDifferenceReviewRequired,
    reconcile_parent_nci_difference,
)


ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "output/latest-universe-20260919/final-discovery/captures/BBY.json.gz"
CIK = "0000764478"
ACCESSION = "0000764478-26-000042"
PERIOD = "2026-08-01"


def _bby_packet() -> dict:
    return json.loads(gzip.open(CAPTURE, "rt").read())["packet"]["structural_filing"]


def test_bby_equity_difference_retains_reporting_precision_bound() -> None:
    availability, proof = reconcile_parent_nci_difference(
        _bby_packet(), cik=CIK, accession=ACCESSION, period_end=PERIOD
    )
    assert availability.state == "bounded_unresolved"
    assert availability.value is None
    assert availability.uncertainty is not None
    assert availability.uncertainty.low == 0.0
    assert availability.uncertainty.high == 1_000_000.0
    assert proof["reported_difference"] == 0.0
    assert proof["exact_zero_proven"] is False
    assert proof["approved_basepoint_within_bound"] is True
    assert proof["approved_basepoint_projection_required"] is True
    assert proof["preferred_equity"] == "not assessed by this helper"


def test_exact_precision_equal_equity_facts_can_prove_zero() -> None:
    packet = _bby_packet()
    for row in packet["facts"]:
        if (
            row.get("period_end") == PERIOD
            and row.get("period_start") is None
            and row.get("unit") == "USD"
            and row.get("qname") in {
                "us-gaap:StockholdersEquity",
                "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            }
            and not row.get("dimensions")
        ):
            row["decimals"] = "INF"
    availability, proof = reconcile_parent_nci_difference(
        packet, cik=CIK, accession=ACCESSION, period_end=PERIOD
    )
    assert availability.state == "evidence_backed_zero"
    assert availability.value == 0.0
    assert proof["exact_zero_proven"] is True


@pytest.mark.parametrize(
    "qname,local_name",
    [
        ("us-gaap:MinorityInterest", "MinorityInterest"),
        ("us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount", "RedeemableNoncontrollingInterestEquityCarryingAmount"),
        ("us-gaap:TemporaryEquityCarryingAmount", "TemporaryEquityCarryingAmount"),
        ("bby:UnknownOutsideEquityClaim", "UnknownOutsideEquityClaim"),
    ],
)
def test_nonzero_claim_markers_block_difference_proof(qname: str, local_name: str) -> None:
    packet = _bby_packet()
    packet["facts"].append(
        {
            "qname": qname,
            "local_name": local_name,
            "value": 1_000_000.0,
            "unit": "USD",
            "dimensions": [],
            "period_end": PERIOD,
            "period_start": None,
            "source_accession": ACCESSION,
            "entity_scheme": "http://www.sec.gov/CIK",
            "entity_identifier": CIK,
            "context_id": "synthetic-claim",
        }
    )
    with pytest.raises(ParentNciDifferenceReviewRequired, match="claim"):
        reconcile_parent_nci_difference(packet, cik=CIK, accession=ACCESSION, period_end=PERIOD)


def test_conflicting_parent_fact_is_rejected() -> None:
    packet = _bby_packet()
    duplicate = next(
        row for row in packet["facts"]
        if row.get("qname") == "us-gaap:StockholdersEquity"
        and row.get("period_end") == PERIOD
        and row.get("period_start") is None
        and not row.get("dimensions")
    )
    packet["facts"].append({**duplicate, "value": duplicate["value"] + 1_000_000.0, "context_id": "conflict"})
    with pytest.raises(ParentNciDifferenceReviewRequired, match="conflicting"):
        reconcile_parent_nci_difference(packet, cik=CIK, accession=ACCESSION, period_end=PERIOD)


def test_parent_and_combined_facts_must_share_context() -> None:
    packet = _bby_packet()
    for row in packet["facts"]:
        if (
            row.get("qname") == "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
            and row.get("period_end") == PERIOD
            and row.get("period_start") is None
            and not row.get("dimensions")
        ):
            row["context_id"] = "different-context"
    with pytest.raises(ParentNciDifferenceReviewRequired, match="contexts"):
        reconcile_parent_nci_difference(packet, cik=CIK, accession=ACCESSION, period_end=PERIOD)


def test_nci_member_on_parent_equity_fact_blocks_proof() -> None:
    packet = _bby_packet()
    packet["facts"].append(
        {
            "qname": "us-gaap:StockholdersEquity",
            "local_name": "StockholdersEquity",
            "value": 1_000_000.0,
            "unit": "USD",
            "dimensions": [["us-gaap:StatementEquityComponentsAxis", "us-gaap:NoncontrollingInterestMember"]],
            "period_end": PERIOD,
            "period_start": None,
            "source_accession": ACCESSION,
            "entity_scheme": "http://www.sec.gov/CIK",
            "entity_identifier": CIK,
            "context_id": "nci-member",
        }
    )
    with pytest.raises(ParentNciDifferenceReviewRequired, match="claim"):
        reconcile_parent_nci_difference(packet, cik=CIK, accession=ACCESSION, period_end=PERIOD)


def test_approved_basepoint_below_positive_bound_is_rejected() -> None:
    packet = _bby_packet()
    for row in packet["facts"]:
        if (
            row.get("period_end") == PERIOD
            and row.get("period_start") is None
            and row.get("unit") == "USD"
            and row.get("qname") == "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
            and not row.get("dimensions")
        ):
            row["value"] += 2_000_000.0
    with pytest.raises(ParentNciDifferenceReviewRequired, match="basepoint"):
        reconcile_parent_nci_difference(packet, cik=CIK, accession=ACCESSION, period_end=PERIOD)


def test_missing_or_incompatible_precision_is_rejected() -> None:
    packet = _bby_packet()
    parent = next(
        row for row in packet["facts"]
        if row.get("qname") == "us-gaap:StockholdersEquity"
        and row.get("period_end") == PERIOD
        and row.get("period_start") is None
        and not row.get("dimensions")
    )
    parent.pop("decimals", None)
    with pytest.raises(ParentNciDifferenceReviewRequired, match="precision"):
        reconcile_parent_nci_difference(packet, cik=CIK, accession=ACCESSION, period_end=PERIOD)
