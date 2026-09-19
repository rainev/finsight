from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_acquisition_funding_overlays import (
    acquisition_funding_overlay_policy,
    select_acquisition_funding_overlay,
)
from app.us_valuation.refresh_narrative_evidence import (
    _VisibleText,
    extract_narrative_evidence,
    narrative_policy,
    terms_by_name,
    validate_narrative_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"
ECL_STRUCTURAL = OUTPUT / "batch-41-structural-sources-20260907/ECL/structural-filing.json"
ECL_PACKAGE = OUTPUT / "official-evidence-difficult-106-part-2/packages/ECL/CIK0000031462-000162828026053886/f2b0cf2a97c69dbc50d7ba2220dd6696aec7bd0fcbe14b674d72af8aca2316a7/package-manifest.json"
PH_STRUCTURAL = OUTPUT / "batch-19-structural-sources-20260830/PH/structural-filing.json"
PH_EVENT = OUTPUT / "batch-19-event-sources-20260830-v2/PH/0001193125-26-349148/narrative-source-manifest.json"
ECL_EVENT_INVENTORY = OUTPUT / "batch-41-event-review-c-20260907/ECL/inventory.json"


def _case(ticker: str):
    path = ECL_STRUCTURAL if ticker == "ECL" else PH_STRUCTURAL
    manifest = ECL_PACKAGE if ticker == "ECL" else PH_EVENT
    structural = json.loads(path.read_bytes())
    structural["narrative_evidence"] = extract_narrative_evidence(
        narrative_policy(ticker), manifest, source_root=OUTPUT
    )
    filing = {
        "accessionNumber": structural["source_accession"],
        "reportDate": structural.get("report_date") or structural["period_end"],
        "filingDate": structural["filed_date"],
        "form": structural["form"],
    }
    return acquisition_funding_overlay_policy(ticker), structural, filing


def test_ecl_narrative_receipt_has_exact_source_and_term_provenance():
    receipt = extract_narrative_evidence(narrative_policy("ECL"), ECL_PACKAGE, source_root=OUTPUT)
    terms = terms_by_name(receipt)
    assert receipt["source"]["document_sha256"] == "e7f4323d48165a47f7c7ab2b70ae495d9399c43a1315be65c0917e91bdc39266"
    assert receipt["filing"] == {
        "accession": "0001628280-26-053886", "form": "10-Q",
        "report_date": "2026-06-30", "filed_date": "2026-08-06",
    }
    assert terms["acquisition_price"]["value"] == 4_750_000_000
    assert terms["close_date"]["value"] == "2026-07-02"
    assert terms["issued_note_principal"]["value"] == 5_000_000_000
    assert terms["delayed_draw_facility_status"]["value"] == "terminated_undrawn"
    assert all(row["section"] in receipt["sections"] for row in terms.values())
    assert validate_narrative_evidence(receipt, narrative_policy("ECL"), source_root=OUTPUT) == receipt


def test_ecl_reconciles_current_financing_and_bounded_cost_proxy_once():
    policy, structural, filing = _case("ECL")
    result = select_acquisition_funding_overlay(
        policy, structural, filing, policy["cik"], "2026-08-14"
    )
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 334_400_000
    assert result["scenario_adjustments"] == {
        "bear_cash_adjustment": -1_425_000_000,
        "base_cash_adjustment": 0,
        "bull_cash_adjustment": 1_425_000_000,
    }
    assert result["components"]["period_end_debt"] == 13_170_800_000
    assert result["components"]["terminated_delayed_draw_facility"] is True
    assert result["components"]["transaction_price_is_intrinsic_value"] is False
    assert result["components"]["benefit_contributions_already_in_cash_flow"] == 32_800_000


def test_ecl_real_event_exhibit_is_hash_bound_context_not_acquired_fcff():
    inventory = json.loads(ECL_EVENT_INVENTORY.read_bytes())
    assert len(inventory) == 1 and inventory[0]["accession"] == "0001628280-26-049933"
    documents = {Path(row["path"]).name: row for row in inventory[0]["documents"]}
    exhibit = OUTPUT.parent / documents["ecl_ex99x1.htm"]["path"]
    raw = exhibit.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == documents["ecl_ex99x1.htm"]["sha256"]
    parser = _VisibleText(); parser.feed(raw.decode("utf-8")); parser.close()
    assert "Global High-Tech platform is now approaching $1.5 billion in annualized sales" in parser.text
    assert "we expect it to grow to $4 billion in sales by 2030" in parser.text
    policy = acquisition_funding_overlay_policy("ECL")
    assert "acquired_fcff" not in policy and "synergies" not in policy


def test_ph_preserves_unreported_residual_funding_as_review_not_claim():
    policy, structural, filing = _case("PH")
    result = select_acquisition_funding_overlay(
        policy, structural, filing, policy["cik"], "2026-08-14"
    )
    assert result["status"] == "review_required"
    assert result["claim_adjustment"] is None
    assert result["review_reasons"] == [
        "residual_purchase_funding_source_is_not_reported",
        "post_close_cash_debt_share_and_acquired_operating_scope_are_not_source_bound",
    ]
    assert result["components"]["event_term_loans"] == 7_750_000_000
    assert result["components"]["arithmetic_funding_gap_not_a_reported_liability"] == 1_500_000_000
    assert result["components"]["period_end_debt"] == 11_682_000_000
    assert result["components"]["period_end_nci"] == 8_000_000
    assert result["components"]["period_end_preferred_equity"] == 0


def test_overlay_narrative_tampering_fails_closed():
    policy, structural, filing = _case("ECL")
    changed = copy.deepcopy(structural)
    changed["narrative_evidence"]["terms"][0]["value"] = 0
    with pytest.raises(ValueError, match="narrative term set|price is not|missing or mismatched"):
        select_acquisition_funding_overlay(policy, changed, filing, policy["cik"], "2026-08-14")
