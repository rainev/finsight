from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_preferred_conversion import (
    PreferredConversionRefreshError,
    bind_preferred_conversion_sources,
)


ROOT = Path(__file__).resolve().parents[2]
STRUCTURAL = ROOT / "output/batch-10-structural-sources-final-a/PG/structural-filing.json"


@pytest.fixture()
def pg_structural() -> dict:
    return json.loads(STRUCTURAL.read_text())


def _fact(packet: dict, qname: str, *, end: str = "2026-06-30") -> dict:
    return next(
        row for row in packet["facts"]
        if row.get("qname") == qname and row.get("period_end") == end
        and row.get("period_start") == "2025-07-01"
    )


def test_real_pg_fy_conversion_reconciles_and_does_not_deduct_preferred_again(pg_structural: dict) -> None:
    result = bind_preferred_conversion_sources(pg_structural)
    assert result["cik"] == "0000080424"
    assert result["period_start"] == "2025-07-01"
    assert result["period_end"] == "2026-06-30"
    shares = result["share_denominator"]
    assert shares == {
        "basic_weighted_average": 2_333_700_000.0,
        "preferred_conversion_increment": 68_300_000.0,
        "other_dilutive_awards_increment": 20_500_000.0,
        "pre_conversion_diluted": 2_354_200_000.0,
        "converted_diluted": 2_422_500_000.0,
    }
    claim = result["preferred_claim"]
    assert claim["class_a_carrying_value"] == 756_000_000.0
    assert claim["class_b_carrying_value"] == 0.0
    assert claim["additional_preferred_deduction"] == 0.0


def test_conversion_projection_preserves_other_blockers_and_reported_claim(pg_structural):
    from app.us_valuation.bridge_policy import BridgeRange, BridgeResolution
    from app.us_valuation.refresh_preferred_conversion import project_converted_bridge
    proof = bind_preferred_conversion_sources(pg_structural,period_end='2026-06-30')
    raw = BridgeResolution(complete=False,can_value=False,
        missing_fields=('finance_lease_current','preferred_equity'),
        blocking_fields=('finance_lease_current','preferred_equity'),bounded_fields=(),
        cash_and_investments=BridgeRange(1000.,1000.,1000.),total_debt=BridgeRange(100.,100.,100.),
        preferred_equity=BridgeRange(756.,756.,756.),noncontrolling_interests=BridgeRange(230.,230.,230.),
        bridge_adjustment=BridgeRange(-86.,-86.,-86.),fully_diluted_shares=100.,reason_codes=())
    projected = project_converted_bridge(raw,proof)
    assert projected.preferred_equity.midpoint == 0
    assert projected.bridge_adjustment.midpoint == 670
    assert projected.fully_diluted_shares == 2422500000
    assert projected.blocking_fields == ('finance_lease_current',)
    assert not projected.can_value
    assert proof['preferred_claim']['reported_preferred_carrying_value'] == 756000000
    assert raw.preferred_equity.midpoint == 756  # No mutation of reported inputs.


def test_wrong_scheme_and_changed_class_b_are_not_conversion_proofs(pg_structural):
    bad = copy.deepcopy(pg_structural)
    _fact(bad,'us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding')['entity_scheme']='wrong'
    with pytest.raises(PreferredConversionRefreshError,match='scheme'):
        bind_preferred_conversion_sources(bad)
    bad = copy.deepcopy(pg_structural)
    for row in bad['facts']:
        if row.get('qname') == 'us-gaap:PreferredStockValue' and row.get('period_end') == '2026-06-30' and row.get('dimensions') == [['us-gaap:StatementClassOfStockAxis','us-gaap:PreferredClassBMember']]:
            row['value'] = 1
    with pytest.raises(PreferredConversionRefreshError,match='changed preferred class'):
        bind_preferred_conversion_sources(bad)


def test_rejects_double_conversion(pg_structural: dict) -> None:
    mutated = copy.deepcopy(pg_structural)
    diluted = _fact(mutated, "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding")
    diluted["value"] += 68_300_000
    with pytest.raises(PreferredConversionRefreshError, match="double conversion|reconcile"):
        bind_preferred_conversion_sources(mutated)


def test_rejects_missing_or_nonconversion_fact(pg_structural: dict) -> None:
    mutated = copy.deepcopy(pg_structural)
    mutated["facts"] = [
        row for row in mutated["facts"]
        if row.get("qname") != "us-gaap:IncrementalCommonSharesAttributableToConversionOfPreferredStock"
        or row.get("period_end") != "2026-06-30"
    ]
    with pytest.raises(PreferredConversionRefreshError, match="conversion"):
        bind_preferred_conversion_sources(mutated)


def test_rejects_missing_class_b_and_unknown_nonzero_class(pg_structural: dict) -> None:
    missing_b = copy.deepcopy(pg_structural)
    missing_b["facts"] = [
        row for row in missing_b["facts"]
        if not (
            row.get("qname") == "us-gaap:PreferredStockValue"
            and row.get("period_end") == "2026-06-30"
            and row.get("dimensions") == [["us-gaap:StatementClassOfStockAxis", "us-gaap:PreferredClassBMember"]]
        )
    ]
    with pytest.raises(PreferredConversionRefreshError, match="PreferredClassBMember"):
        bind_preferred_conversion_sources(missing_b)

    unknown = copy.deepcopy(pg_structural)
    unknown["facts"].append({
        "qname": "us-gaap:PreferredStockValue",
        "namespace": "http://fasb.org/us-gaap/2026",
        "unit": "USD",
        "value": 1.0,
        "entity_identifier": "0000080424",
        "entity_scheme": "http://www.sec.gov/CIK",
        "source_accession": unknown["source_accession"],
        "period_start": None,
        "period_end": "2026-06-30",
        "dimensions": [["us-gaap:StatementClassOfStockAxis", "us-gaap:PreferredClassUnknownMember"]],
    })
    with pytest.raises(PreferredConversionRefreshError, match="unknown nonzero preferred class"):
        bind_preferred_conversion_sources(unknown)


def test_selects_latest_common_current_period_not_fact_order(pg_structural: dict) -> None:
    mutated = copy.deepcopy(pg_structural)
    mutated["facts"] = list(reversed(mutated["facts"]))
    result = bind_preferred_conversion_sources(mutated)
    assert (result["period_start"], result["period_end"]) == ("2025-07-01", "2026-06-30")


def test_rejects_identity_unit_and_context_scope_conflicts(pg_structural: dict) -> None:
    for field, value, message in (
        ("entity_identifier", "0000000000", "CIK"),
        ("unit", "USD", "unit"),
    ):
        mutated = copy.deepcopy(pg_structural)
        row = _fact(mutated, "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic")
        row[field] = value
        with pytest.raises(PreferredConversionRefreshError, match=message):
            bind_preferred_conversion_sources(mutated)
