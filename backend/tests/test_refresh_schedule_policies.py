"""Source-bound AAPL cash-schedule refresh adapter contract."""

import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_schedule_policies import (
    CashScheduleRefreshError,
    bind_and_evaluate_cash_schedule_recipe,
    compile_cash_schedule_policy,
)


ROOT = Path(__file__).parents[2]
OUTPUT = ROOT / "output"


def _cached_aapl():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/AAPL.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "AAPL")
    source = OUTPUT / "batch-01-controlled/sources/AAPL"
    packet = {
        "submissions": json.loads((source / "submissions.json").read_text()),
        "companyfacts": json.loads((source / "companyfacts.json").read_text()),
    }
    structural = json.loads(
        (OUTPUT / "batch-01-controlled/structural-shadow-run-b/AAPL/structural-filing.json").read_text()
    )
    return recipe, entry, packet, structural


def _cached_msft():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/MSFT.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "MSFT")
    source = OUTPUT / "batch-01-controlled/sources/MSFT"
    packet = {
        "submissions": json.loads((source / "submissions.json").read_text()),
        "companyfacts": json.loads((source / "companyfacts.json").read_text()),
    }
    return recipe, entry, packet


def test_compile_cash_schedule_policy_has_no_frozen_source_facts():
    recipe, entry, _, _ = _cached_aapl()
    policy = compile_cash_schedule_policy(recipe, entry)

    assert policy["version"].endswith("AAPL")
    assert policy["supported_engine"] == "cash_schedule"
    encoded = json.dumps(policy, sort_keys=True)
    assert "0000320193-26-000020" not in encoded
    assert "2026-06-27" not in encoded
    assert "122619614048" not in encoded


def test_cached_aapl_returns_exact_source_ledger_and_withholds_unresolved_bridge():
    recipe, entry, packet, structural = _cached_aapl()
    policy = compile_cash_schedule_policy(recipe, entry)
    with pytest.raises(CashScheduleRefreshError, match="preferred_equity|noncontrolling_interests") as raised:
        bind_and_evaluate_cash_schedule_recipe(
            policy,
            recipe,
            packet,
            structural_packet=structural,
            cutoff="2026-08-14",
        )
    ledger = raised.value.ledger
    assert ledger["controlling_filing"]["accessionNumber"] == "0000320193-26-000020"
    assert ledger["period_end"] == "2026-06-27"
    assert ledger["values"]["cash_and_investments"] == 146_517_000_000.0
    assert ledger["values"]["shares"] == 14_651_967_000.0
    assert ledger["values"]["total_reported_capex"] == 10_041_000_000.0
    assert set(ledger["bridge_quality"]["blocking_fields"]) == {
        "preferred_equity",
        "noncontrolling_interests",
    }
    assert "finance_lease_total" in ledger["bridge_quality"]["bounded_fields"]
    assert "scenario_results" not in ledger


def test_aapl_adapter_rejects_unresolved_structural_claims():
    recipe, entry, packet, structural = _cached_aapl()
    policy = compile_cash_schedule_policy(recipe, entry)
    tampered = json.loads(json.dumps(structural))
    tampered["facts"].append(
        {
            "local_name": "PreferredStockValue",
            "period_end": "2026-06-27",
            "dimensions": [],
            "value": 1.0,
        }
    )
    with pytest.raises(CashScheduleRefreshError, match="preferred_equity|noncontrolling_interests"):
        bind_and_evaluate_cash_schedule_recipe(
            policy,
            recipe,
            packet,
            structural_packet=tampered,
            cutoff="2026-08-14",
        )


def test_aapl_policy_declares_remaining_unsupported_cases():
    recipe, entry, _, _ = _cached_aapl()
    policy = compile_cash_schedule_policy(recipe, entry)
    assert any("non-routine 8-K" in row for row in policy["unsupported_cases"])
    assert any("finance-lease" in row for row in policy["unsupported_cases"])


def test_msft_compiles_segment_policy_and_blocks_without_current_segment_package():
    recipe, entry, packet = _cached_msft()
    policy = compile_cash_schedule_policy(recipe, entry)

    assert policy["ticker"] == "MSFT"
    assert policy["model_profile"] == "segment_operating_income_intangible_investment"
    assert policy["policy_assumptions"]["segment_mode"] == "segment_operating_income"
    assert policy["source_requirements"]["segment_filing_table"] is True
    encoded = json.dumps(policy, sort_keys=True)
    assert "106203930751" not in encoded
    assert "0001193125-26-323660" not in encoded

    with pytest.raises(CashScheduleRefreshError, match="segment-table structural package") as raised:
        bind_and_evaluate_cash_schedule_recipe(
            policy,
            recipe,
            packet,
            structural_packet=None,
            cutoff="2026-08-14",
        )
    assert raised.value.source_gate["controlling_filing"]["accessionNumber"] == "0001193125-26-323660"
    assert raised.value.source_gate["period_end"] == "2026-06-30"
    assert raised.value.source_gate["source_packet_has_structural_filing"] is False


def test_reparsed_aapl_shared_dispatch_reconciles_sources_models_and_public_result():
    from app.us_valuation.refresh_bindings import bind_current_recipe
    from app.us_valuation.calculation_recipe import evaluate_recipe
    from app.us_valuation.refresh_job import refreshed_public
    recipe,entry,packet,_ = _cached_aapl()
    packet['structural_filing'] = json.loads((OUTPUT/'us-refresh-aapl-source-verification/structural-filing.json').read_text())
    policy = compile_cash_schedule_policy(recipe,entry)
    bound,ledger = bind_current_recipe({**entry,'refresh_policy':policy},recipe,packet,'2026-08-14')
    valued = evaluate_recipe(bound)
    assert valued['range']['base'] == pytest.approx(107.3745809737621)
    assert ledger['bridge_quality']['bounded_fields'] == ['finance_lease_total']
    proof = ledger['sources']['normalized_bridge']['structural_receipt']['reconciliations']
    assert proof['preferred_equity']['value'] == 107520000000.
    assert proof['noncontrolling_interests']['value'] == 0.
    for case in ('bear','base','bull'):
        direct_model = ledger['scenario_results'][case]['model_trace']
        assert valued['scenarios'][case]['value'] == pytest.approx(direct_model['intrinsic_value_per_share'])
        assert bound['scenarios'][case]['inputs']['discount_rate'] == recipe['scenarios'][case]['inputs']['discount_rate']
    assert bound['scenarios']['bear']['inputs']['net_bridge'] < bound['scenarios']['bull']['inputs']['net_bridge']
    public = json.loads((OUTPUT/'us-refresh-runtime/baseline/artifacts/AAPL.json').read_text())
    updated = refreshed_public(public,bound,valued,ledger,'2026-08-14')
    assert updated['scenario_range']['base'] == pytest.approx(107.3745809737621)
    assert 'reinvestment' in updated['normalization_explanation']
    assert 'forecast_quality' not in updated
