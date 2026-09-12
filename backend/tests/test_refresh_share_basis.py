from __future__ import annotations

import copy
import json
import hashlib
from pathlib import Path

import pytest

from app.us_valuation.refresh_share_basis import (
    ShareBasisReviewRequired,
    resolve_class_equivalent_share_basis,
)


ROOT = Path(__file__).resolve().parents[2]
STRUCTURAL = ROOT / "output/batch-37-structural-sources-20260906/BRK.B/structural-filing.json"
PRIVATE = ROOT / "output/batch-37-history-run-a-20260906/generated/BRK.B/valuation-private.json"


def _brk_structural() -> dict:
    return json.loads(STRUCTURAL.read_text())


def test_namespace_versions_are_not_embedded_filing_dates():
    structural = _brk_structural()
    # Synthetic namespace-version drift only; not a successive real filing claim.
    for row in structural['facts']:
        ns = row.get('namespace', '')
        if ns == 'http://www.berkshirehathaway.com/20260630':
            row['namespace'] = 'http://www.berkshirehathaway.com/20260930'
        elif ns == 'http://xbrl.sec.gov/dei/2026':
            row['namespace'] = 'http://xbrl.sec.gov/dei/2027'
        else:
            continue
        row['qname'] = 'ns_' + hashlib.sha1(row['namespace'].encode()).hexdigest()[:10] + ':' + row['local_name']
    result = resolve_class_equivalent_share_basis(structural, ticker='BRK.B', selected_class='B',
        cik='1067983', accession='0001193125-26-341032', report_period_end='2026-06-30',
        filing_date='2026-08-10', cutoff='2026-08-14')
    assert result['value'] == 2140710161.0


def test_brk_b_basis_uses_reported_class_facts_and_filing_ratio() -> None:
    structural = _brk_structural()
    private = json.loads(PRIVATE.read_text())
    base_row = private["history_backed"]["scenario_rows"][1]

    result = resolve_class_equivalent_share_basis(
        structural,
        ticker="BRK.B",
        selected_class="B",
        cik="1067983",
        accession="0001193125-26-341032",
        report_period_end="2026-06-30",
        filing_date="2026-08-10",
        cutoff="2026-08-14",
        expected_equivalent_shares=base_row["shares"],
    )

    assert result["status"] == "verified"
    assert result["class_a_shares"] == 488450.0
    assert result["class_b_shares"] == 1408035161.0
    assert result["conversion_ratio"] == 1500.0
    assert result["value"] == 2140710161.0
    assert result["formula"] == "Class A shares * 1500 + Class B shares"
    assert result["source_kind"] == "derived_class_b_equivalent_shares"
    assert result["share_observation_period_end"] == "2026-07-29"
    assert {row["source_accession"] for row in result["sources"]} == {"0001193125-26-341032"}


def test_brk_b_missing_or_classless_source_requires_review() -> None:
    structural = _brk_structural()
    structural["facts"] = [
        row
        for row in structural["facts"]
        if not (
            row.get("local_name") == "EntityCommonStockSharesOutstanding"
            and any("CommonClassBMember" in member for dimension in row.get("dimensions", []) for member in dimension)
        )
    ]
    with pytest.raises(ShareBasisReviewRequired, match="Class B outstanding source fact is missing"):
        resolve_class_equivalent_share_basis(
            structural,
            ticker="BRK.B",
            selected_class="B",
            cik="0001067983",
            accession="0001193125-26-341032",
            report_period_end="2026-06-30",
            filing_date="2026-08-10",
            cutoff="2026-08-14",
        )


def test_brk_b_conflicting_ratio_or_identity_requires_review() -> None:
    structural = _brk_structural()
    conflicting = copy.deepcopy(next(
        row
        for row in structural["facts"]
        if row.get("local_name") == "NumberOfSharesObtainableFromConvertingOneShareFromOneClassToAnotherClass"
    ))
    conflicting["value"] = 1.0
    structural["facts"].append(conflicting)
    with pytest.raises(ShareBasisReviewRequired, match="Class conversion ratio source facts conflict"):
        resolve_class_equivalent_share_basis(
            structural,
            ticker="BRK.B",
            selected_class="B",
            cik="0001067983",
            accession="0001193125-26-341032",
            report_period_end="2026-06-30",
            filing_date="2026-08-10",
            cutoff="2026-08-14",
        )

    structural = _brk_structural()
    with pytest.raises(ShareBasisReviewRequired, match="structural packet accession mismatch"):
        resolve_class_equivalent_share_basis(
            structural,
            ticker="BRK.B",
            selected_class="B",
            cik="0001067983",
            accession="000000000-00-000000",
            report_period_end="2026-06-30",
            filing_date="2026-08-10",
            cutoff="2026-08-14",
        )


def test_brk_b_rejects_spoof_qname_future_cover_and_wrong_identity() -> None:
    structural = _brk_structural()
    spoofed = copy.deepcopy(structural)
    row = next(
        row
        for row in spoofed["facts"]
        if row.get("local_name") == "EntityCommonStockSharesOutstanding"
    )
    row["qname"] = "spoof:EntityCommonStockSharesOutstanding"
    with pytest.raises(ShareBasisReviewRequired, match="Class A outstanding source fact is missing"):
        resolve_class_equivalent_share_basis(
            spoofed,
            ticker="BRK.B",
            selected_class="B",
            cik="0001067983",
            accession="0001193125-26-341032",
            report_period_end="2026-06-30",
            filing_date="2026-08-10",
            cutoff="2026-08-14",
        )

    future = _brk_structural()
    for row in future["facts"]:
        if row.get("local_name") == "EntityCommonStockSharesOutstanding":
            row["period_end"] = "2026-08-15"
    with pytest.raises(ShareBasisReviewRequired, match="share observation period is outside report/filing window"):
        resolve_class_equivalent_share_basis(
            future,
            ticker="BRK.B",
            selected_class="B",
            cik="0001067983",
            accession="0001193125-26-341032",
            report_period_end="2026-06-30",
            filing_date="2026-08-10",
            cutoff="2026-08-20",
        )

    with pytest.raises(ShareBasisReviewRequired, match="ticker and selected class do not match"):
        resolve_class_equivalent_share_basis(
            structural,
            ticker="BRK.A",
            selected_class="B",
            cik="0001067983",
            accession="0001193125-26-341032",
            report_period_end="2026-06-30",
            filing_date="2026-08-10",
            cutoff="2026-08-14",
        )
    with pytest.raises(ShareBasisReviewRequired, match="CIK is not the governed"):
        resolve_class_equivalent_share_basis(
            structural,
            ticker="BRK.B",
            selected_class="B",
            cik="0000320193",
            accession="0001193125-26-341032",
            report_period_end="2026-06-30",
            filing_date="2026-08-10",
            cutoff="2026-08-14",
        )
