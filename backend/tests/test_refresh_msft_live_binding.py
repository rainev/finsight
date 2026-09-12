import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_schedule_policies import CashScheduleRefreshError, bind_and_evaluate_cash_schedule_recipe, compile_cash_schedule_policy, _records, _msft_segment_source_gate, _select_filing


ROOT = Path(__file__).parents[2]
WRAPPER = ROOT / "output/us-refresh-runtime/acquisitions/0a0a47feb71d0ecdf4f4f1cc82bbbab937dc31f55876e119a3a97feb4d7e3c3d/packets/MSFT.json"


def _live_msft():
    wrapper = json.loads(WRAPPER.read_text())
    packet = wrapper["packet"]
    recipe = json.loads((ROOT / "output/us-refresh-runtime/recipes/MSFT.json").read_text())
    registry = json.loads((ROOT / "output/us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "MSFT")
    return recipe, entry, packet, packet["structural_filing"]


def test_live_msft_segment_extraction_is_not_an_executable_forecast():
    recipe, entry, packet, structural = _live_msft()
    policy = compile_cash_schedule_policy(recipe, entry)
    # Isolate extraction without treating the captured event inventory as reviewed.
    gate = {"segment_evidence": _msft_segment_source_gate(
        policy=policy, packet=packet, structural_packet=structural,
        controlling=_select_filing(_records(packet["submissions"]), "2026-09-08"), cutoff="2026-09-08",
    )}
    assert gate["segment_evidence"]["status"] == "segment_evidence_reconciled"
    assert gate["segment_evidence"]["annual_periods"][-1] == "2026-06-30"
    assert set(gate["segment_evidence"]["segments"]) == {
        "productivity_and_business_processes",
        "intelligent_cloud",
        "more_personal_computing",
    }
    assert gate["segment_evidence"]["consolidated_reported"] == {
        "revenue": 331_839_000_000.0,
        "operating_income": 155_237_000_000.0,
    }
    assert gate["segment_evidence"]["rd_intangible_sources"]
    assert gate["segment_evidence"]["rd_policy_status"].startswith("source_amounts_present")


def test_msft_segment_tamper_fails_reconciliation_before_bridge_claims():
    recipe, entry, packet, structural = _live_msft()
    tampered = copy.deepcopy(structural)
    for row in tampered["facts"]:
        if row.get("local_name") == "OperatingIncomeLoss" and row.get("period_end") == "2026-06-30" and row.get("dimensions") and any(str(pair[1]).endswith("IntelligentCloudMember") for pair in row["dimensions"]):
            row["value"] += 1_000_000_000
    policy = compile_cash_schedule_policy(recipe, entry)
    with pytest.raises(CashScheduleRefreshError, match="reconcile"):
        _msft_segment_source_gate(policy=policy, packet=packet, structural_packet=tampered,
            controlling=_select_filing(_records(packet["submissions"]), "2026-09-08"), cutoff="2026-09-08")


def test_msft_does_not_bypass_unknown_corporate_events():
    recipe, entry, packet, structural = _live_msft()
    packet = copy.deepcopy(packet)
    recent = packet["submissions"]["filings"]["recent"]
    injected = {"accessionNumber": "0000789019-26-999999", "form": "8-K", "filingDate": "2026-09-08", "items": "1.01"}
    for key, values in recent.items():
        if isinstance(values, list):
            values.append(injected.get(key, ""))
    with pytest.raises(CashScheduleRefreshError, match="corporate-event"):
        bind_and_evaluate_cash_schedule_recipe(compile_cash_schedule_policy(recipe, entry), recipe, packet,
            structural_packet=structural, cutoff="2026-09-08")


def test_real_msft_shared_binding_and_public_output_reconcile_all_cases():
    from app.us_valuation.refresh_bindings import bind_current_recipe
    from app.us_valuation.calculation_recipe import evaluate_recipe
    from app.us_valuation.refresh_job import refreshed_public
    recipe, entry, _, _ = _live_msft()
    wrapper = ROOT/'output/us-refresh-runtime/acquisitions/46b4aef07dddcaef6c42a278c4942007d5154e3dd16d9327f6be2f36f1866752/packets/MSFT.json'
    packet = json.loads(wrapper.read_text())['packet']
    policy = compile_cash_schedule_policy(recipe,entry)
    bound, ledger = bind_current_recipe({**entry,'refresh_policy':policy},recipe,packet,'2026-08-14')
    result = evaluate_recipe(bound)
    original = json.loads((ROOT/'output/us-refresh-runtime/baseline/artifacts/MSFT.json').read_text())
    public = refreshed_public(original,bound,result,ledger,'2026-08-14')
    assert public['scenario_range']['base'] == pytest.approx(result['scenarios']['base']['raw_value'])
    assert ledger['normalization']['assumptions']['normalized_tax_rate'] == pytest.approx(0.18604975925577727)
    assert ledger['normalization']['assumptions']['normalized_operating_margin'] == pytest.approx(0.44644299573273716)
    assert public['model_version'] == policy['version']
    assert ledger['values']['preferred_equity'] == 0
    assert ledger['values']['noncontrolling_interests'] == 0
    assert ledger['sources']['normalized_bridge']['structural_receipt']
    for name,spec in bound['scenarios'].items():
        inputs = spec['inputs']
        rate,growth = inputs['discount_rate'],inputs['terminal_growth']
        cashflows = inputs['cash_flows']
        pv = sum(cash/(1+rate)**year for year,cash in enumerate(cashflows,1))
        pv += inputs['terminal_cash_flow']/(rate-growth)/(1+rate)**len(cashflows)
        expected = (pv+inputs['net_bridge'])/inputs['shares']
        assert result['scenarios'][name]['raw_value'] == pytest.approx(expected)
        # Separate the intentional bridge repair from legacy operating replay.
        legacy = recipe['scenarios'][name]['inputs']
        assert inputs['cash_flows'] == pytest.approx(legacy['cash_flows'])
        assert inputs['terminal_cash_flow'] == pytest.approx(legacy['terminal_cash_flow'])
        assert inputs['shares'] == legacy['shares']
        old_value = evaluate_recipe(recipe)['scenarios'][name]['raw_value']
        assert result['scenarios'][name]['raw_value'] - old_value == pytest.approx(
            (inputs['net_bridge'] - legacy['net_bridge']) / inputs['shares'], abs=1e-10)
