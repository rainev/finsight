"""Source-bound MRNA asset-runway refresh tests."""

import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_runway_policy import (
    RunwayRefreshError,
    bind_and_evaluate_mrna_runway_recipe,
    compile_mrna_runway_policy,
)


ROOT = Path(__file__).parents[2]
OUTPUT = ROOT / "output"


def _cached_mrna():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/MRNA.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "MRNA")
    source = OUTPUT / "batch-17-sec-source-packets-20260830/MRNA"
    packet = {
        "submissions": json.loads((source / "submissions.json").read_text()),
        "companyfacts": json.loads((source / "companyfacts.json").read_text()),
    }
    structural = json.loads(
        (OUTPUT / "batch-17-structural-sources-20260830/MRNA/structural-filing.json").read_text()
    )
    return recipe, entry, packet, structural


def test_compile_policy_contains_horizons_not_frozen_source_amounts():
    recipe, entry, _, _ = _cached_mrna()
    policy = compile_mrna_runway_policy(recipe, entry)
    encoded = json.dumps(policy, sort_keys=True)

    assert policy["version"].endswith("MRNA")
    assert policy["burn_policy"]["bear_reserve_multiplier"] == 3.0
    assert policy["burn_policy"]["base_reserve_multiplier"] == 2.0
    assert policy["burn_policy"]["bull_reserve_multiplier"] == 1.0
    assert "6910000000" not in encoded
    assert "0001682852-26-000150" not in encoded
    assert '2023-12-31' not in encoded
    assert policy['burn_policy']['annual_periods'] == 3


def test_cached_mrna_recomputes_runway_inputs_and_replays_asset_engine():
    recipe, entry, packet, structural = _cached_mrna()
    policy = compile_mrna_runway_policy(recipe, entry)
    result = bind_and_evaluate_mrna_runway_recipe(
        policy,
        recipe,
        packet,
        structural_packet=structural,
        cutoff="2026-08-14",
    )
    ledger = result["source_ledger"]

    assert ledger["controlling_filing"]["accessionNumber"] == "0001682852-26-000150"
    assert ledger["period_end"] == "2026-06-30"
    assert ledger["values"] == {
        "liquid_assets": 6_910_000_000.0,
        "debt_and_finance_leases": 628_000_000.0,
        "cash_burn_reserve": {
            "bear": 11_475_000_000.0,
            "base": 2_488_000_000.0,
            "bull": 1_244_000_000.0,
        },
        "shares": {"bear": 399235889., "base": 397617944.5, "bull": 396000000.},
        "pipeline_terminal_value": 0.0,
    }
    assert result["refreshed_replay"] == {
        "low": pytest.approx(0.0),
        "base": pytest.approx(9.541822879173402),
        "high": pytest.approx(12.722222222222221),
    }
    assert result["refreshed_recipe"]["scenarios"]["base"]["inputs"]["pipeline_terminal_value"] == 0.0
    assert ledger["pipeline_review"]["status"] == "explicit_model_scope_zero"
    assert result["refreshed_replay"] == recipe["replay"]
    assert ledger['sources']['weighted_shares']['start'] == '2026-01-01'
    assert ledger['sources']['weighted_shares']['value'] == 396000000.
    assert ledger['sources']['cover_shares']['period_end'] == '2026-07-24'


def test_mrna_rejects_wrong_fact_identity_and_lookalike_concept():
    from copy import deepcopy
    recipe,entry,packet,structural = _cached_mrna()
    policy = compile_mrna_runway_policy(recipe,entry)
    wrong = deepcopy(structural)
    wrong['facts'][0]['entity_identifier'] = '0000000001'
    with pytest.raises(RunwayRefreshError,match='identity'):
        bind_and_evaluate_mrna_runway_recipe(policy,recipe,packet,structural_packet=wrong,cutoff='2026-08-14')
    wrong = deepcopy(structural)
    for row in wrong['facts']:
        if row.get('qname') == 'us-gaap:CashAndCashEquivalentsAtCarryingValue':
            row['qname'] = 'issuer:CashAndCashEquivalentsAtCarryingValue'
    with pytest.raises(RunwayRefreshError,match='CashAndCashEquivalents'):
        bind_and_evaluate_mrna_runway_recipe(policy,recipe,packet,structural_packet=wrong,cutoff='2026-08-14')


def test_mrna_nonroutine_event_blocks_runway_refresh():
    recipe, entry, packet, structural = _cached_mrna()
    policy = compile_mrna_runway_policy(recipe, entry)
    tampered = json.loads(json.dumps(packet))
    recent = tampered["submissions"]["filings"]["recent"]
    recent["accessionNumber"].append("0001682852-26-999999")
    recent["form"].append("8-K")
    recent["filingDate"].append("2026-08-15")
    recent["reportDate"].append("2026-08-15")
    recent["items"].append("1.01")
    recent["primaryDocument"].append("mrna-event.htm")
    with pytest.raises(RunwayRefreshError, match="clinical/corporate event"):
        bind_and_evaluate_mrna_runway_recipe(
            policy,
            recipe,
            tampered,
            structural_packet=structural,
            cutoff="2026-08-15",
        )
