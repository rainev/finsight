from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_pharma_claims import pharma_claim_policy, select_pharma_claim


ROOT = Path(__file__).resolve().parents[2]
STRUCTURAL = ROOT / "output" / "batch-14-structural-sources-20260829"
CONTROL = {
    "BIIB": ("0000875045", "0000875045-26-000075", "2026-07-29"),
    "GILD": ("0000882095", "0000882095-26-000031", "2026-08-06"),
    "INCY": ("0000879169", "0000879169-26-000056", "2026-07-28"),
}


def _run(ticker: str, structural: dict | None = None) -> dict:
    cik, accession, filed = CONTROL[ticker]
    packet = structural or json.loads((STRUCTURAL / ticker / "structural-filing.json").read_text())
    return select_pharma_claim(
        pharma_claim_policy(ticker), packet,
        {"accessionNumber": accession, "reportDate": "2026-06-30", "filingDate": filed},
        cik, "2026-08-14",
    )


def test_biib_reconciles_acquisition_claim_and_keeps_legal_amount_nonadditive():
    result = _run("BIIB")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 273_500_000
    assert result["current_carrying_liability"] == 273_500_000
    assert result["components"] == {
        "aggregate_carrying_liability": 273_500_000,
        "narrower_existing_claim": 269_400_000,
        "acquisition_purchase_added_within_aggregate": 4_100_000,
        "legal_judgment_not_added": 124_300_000,
    }
    assert result["review_reasons"] == []


def test_gild_counts_current_carrying_claims_once_and_excludes_maxima_cvr_and_cash():
    result = _run("GILD")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 337_000_000
    assert result["current_carrying_liability"] == 337_000_000
    assert result["review_reasons"] == []
    assert result["components"]["typed_location_total"] == 276_000_000
    assert result["components"]["typed_location_rounding_difference"] == 1_000_000
    assert result["components"]["contractual_maxima_not_added"] == [500_000_000, 1_900_000_000]
    assert result["components"]["cvr_ceiling_not_added"] == [300_000_000]
    assert result["components"]["settlement_cash_not_added"] == [288_000_000]
    assert result["components"]["future_royalty_carrying_not_added"] == 1_100_000_000
    assert result["components"]["future_royalty_fair_value_not_added"] == 700_000_000
    assert result["components"]["future_royalty_debt_component"] == 1_077_000_000
    assert result["components"]["total_debt_containing_future_royalty"] == 26_246_000_000


def test_incy_counts_components_once_and_adjusts_completed_vega_cash_once():
    result = _run("INCY")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 102_000_000
    assert result["cash_adjustment"] == -1_250_000_000
    assert result["components"]["contingent_cash_paid_not_added"] == 9_565_000
    assert result["components"]["post_period_contingent_ceiling_not_added"] == 750_000_000


def test_gild_does_not_accept_a_maximum_as_a_carrying_claim():
    packet = json.loads((STRUCTURAL / "GILD" / "structural-filing.json").read_text())
    packet = deepcopy(packet)
    packet["facts"] = [
        row for row in packet["facts"]
        if not (row.get("qname") == "us-gaap:AssetAcquisitionContingentConsiderationLiability"
                and row.get("period_end") == "2026-06-30")
    ]
    with pytest.raises(ValueError, match="Ouro carrying liability"):
        _run("GILD", packet)


def test_incy_rejects_stale_or_conflicting_current_components():
    packet = json.loads((STRUCTURAL / "INCY" / "structural-filing.json").read_text())
    packet = deepcopy(packet)
    for row in packet["facts"]:
        if (row.get("qname") == "us-gaap:BusinessCombinationContingentConsiderationLiabilityCurrent"
                and row.get("period_end") == "2026-06-30"):
            row["value"] += 1_000_000
    with pytest.raises(ValueError, match="do not reconcile"):
        _run("INCY", packet)


@pytest.mark.parametrize("ticker,qname,match", [
    ("BIIB", "us-gaap:BusinessCombinationContingentConsiderationLiabilityNoncurrent", "unsupported nonzero carrying-liability"),
    ("GILD", "us-gaap:BusinessCombinationContingentConsiderationLiability", "unsupported nonzero MYR"),
    ("INCY", "us-gaap:BusinessCombinationContingentConsiderationLiabilityCurrent", "unsupported nonzero carrying-liability"),
])
def test_unknown_nonzero_claim_dimensions_fail_closed(ticker: str, qname: str, match: str):
    packet = json.loads((STRUCTURAL / ticker / "structural-filing.json").read_text())
    packet = deepcopy(packet)
    row = next(row for row in packet["facts"] if row.get("qname") == qname
               and row.get("period_end") == "2026-06-30" and row.get("period_start") is None
               and float(row.get("value", 0)) > 0)
    injected = deepcopy(row)
    injected["dimensions"] = list(injected.get("dimensions") or []) + [["us-gaap:StatementScenarioAxis", "us-gaap:ScenarioForecastMember"]]
    packet["facts"].append(injected)
    with pytest.raises(ValueError, match=match):
        _run(ticker, packet)
