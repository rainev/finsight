import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_msft_model import MSFTRefreshError, build_msft_forecast, compile_msft_approved_policy, _select_msft_shares


ROOT = Path(__file__).parents[2]
WRAPPER = ROOT / "output/us-refresh-runtime/acquisitions/0a0a47feb71d0ecdf4f4f1cc82bbbab937dc31f55876e119a3a97feb4d7e3c3d/packets/MSFT.json"


def _live():
    wrapper = json.loads(WRAPPER.read_text())
    recipe = json.loads((ROOT / "output/us-refresh-runtime/recipes/MSFT.json").read_text())
    return recipe, wrapper["packet"]


def _live_interim():
    wrapper = json.loads((ROOT / "output/us-refresh-runtime/acquisitions/ff62e1c19a9cc3b94f7a27214d6e20bf8dd7d16d35b4c08f413303e06b38363b/packets/MSFT.json").read_text())
    recipe = json.loads((ROOT / "output/us-refresh-runtime/recipes/MSFT.json").read_text())
    return recipe, wrapper["packet"]


def _approved_policy():
    recipe = json.loads((ROOT / "output/us-refresh-runtime/recipes/MSFT.json").read_text())
    return compile_msft_approved_policy(recipe)


def test_msft_policy_compiles_without_period_key_or_source_amount_arrays():
    recipe, _ = _live()
    policy = compile_msft_approved_policy(recipe)
    encoded = json.dumps(policy, sort_keys=True)
    assert "2026-06-30" not in encoded
    assert "139996000000" not in encoded
    assert policy["input_hashes"]["private_provenance_sha256"]
    assert policy["segment_axis_qname"] == "us-gaap:StatementBusinessSegmentsAxis"


def test_msft_policy_uses_retained_approval_weights_and_rejects_unequal_segments(tmp_path):
    recipe, _ = _live()
    private = json.loads(Path(recipe['provenance']['source_path']).read_text())
    segments = private['practical_private']['forecast_assumptions']['segment_forecast']['segments']
    weights = {'archetype_anchor':.1, 'company_history':.5, 'recent_ytd':.4}
    for segment in segments.values():
        segment['evidence']['growth_weights'] = weights.copy()
    retained = tmp_path/'synthetic-private.json'
    retained.write_text(json.dumps(private))
    recipe['provenance']['source_path'] = str(retained)
    assert compile_msft_approved_policy(recipe)['growth_weights'] == weights
    segments['intelligent_cloud']['evidence']['growth_weights']['company_history'] = .6
    retained.write_text(json.dumps(private))
    with pytest.raises(MSFTRefreshError, match='per-segment policy'):
        compile_msft_approved_policy(recipe)


def test_live_msft_builds_segment_model_trace_without_bridge_fabrication():
    recipe, packet = _live()
    result = build_msft_forecast(packet, recipe, cutoff="2026-09-08", approved_policy=_approved_policy())
    assert result["status"] == "forecast_bound_unbridged"
    assert result["bridge_deferred"] is True
    assert set(result["source_ledger"]["segment_evidence"]["segments"]) == {
        "productivity_and_business_processes",
        "intelligent_cloud",
        "more_personal_computing",
    }
    assert result["source_ledger"]["segment_evidence"]["consolidated_ttm"] == {
        "revenue": 331_839_000_000.0,
        "operating_income": 155_237_000_000.0,
    }
    assert result["source_ledger"]["segment_evidence"]["rd_intangible_sources"]
    assert result["source_ledger"]["tax_rate"] == pytest.approx(0.18604975925577727)
    from statistics import median
    annual = json.loads(Path(recipe['provenance']['source_path']).read_text())['practical_private']['financials']['annual']
    assert result["normalized_assumptions"]["normalized_operating_margin"] == pytest.approx(median(row['values']['operating_income']/row['values']['revenue'] for row in annual))
    capital = result['source_ledger']['segment_evidence']['capital_intensity']
    assert capital['unadjusted_sales_to_capital'] == 3.0
    historical = median(row['values']['capital_expenditures']/row['values']['revenue'] for row in annual)
    expected_base = min(1.25, max(.50, historical/(115948000000/331839000000)))
    assert capital['scenario_multipliers'] == pytest.approx({'bear':max(.35,expected_base*.75),'base':expected_base,'bull':min(1.25,expected_base*1.10)})
    for name in result['scenarios']:
        assert result['scenarios'][name]['assumptions']['sales_to_capital'] == pytest.approx(3*capital['scenario_multipliers'][name])
    assert len(result["source_ledger"]["tax_normalization"]["annual"]) == 3
    assert result["source_ledger"]["tax_normalization"]["current_ttm"]["period_end"] == "2026-06-30"
    assert set(result["scenarios"]) == {"bear", "base", "bull"}
    assert all(row["model"]["errors"] == [] for row in result["scenarios"].values())
    assert all(row["model"]["detail"]["forecast_schedule"] for row in result["scenarios"].values())


def test_msft_segment_source_tamper_is_rejected_before_model_trace():
    recipe, packet = _live()
    tampered = copy.deepcopy(packet)
    for row in tampered["structural_filing"]["facts"]:
        if row.get("local_name") == "OperatingIncomeLoss" and row.get("period_end") == "2026-06-30" and row.get("dimensions") and any(str(pair[1]).endswith("IntelligentCloudMember") for pair in row["dimensions"]):
            row["value"] += 1_000_000_000
    with pytest.raises(MSFTRefreshError, match="reconcile"):
        build_msft_forecast(tampered, recipe, cutoff="2026-09-08", approved_policy=_approved_policy())


def test_msft_r_and_d_is_ledgered_as_reported_diagnostic_not_capitalized_guess():
    recipe, packet = _live()
    result = build_msft_forecast(packet, recipe, cutoff="2026-09-08", approved_policy=_approved_policy())
    assert "diagnostic" in result["source_ledger"]["r_and_d_treatment"]
    assert "asset-life" in result["source_ledger"]["r_and_d_treatment"]


def test_msft_share_selector_rejects_conflicting_current_facts():
    recipe, packet = _live()
    structural = copy.deepcopy(packet["structural_filing"])
    row = next(row for row in structural["facts"] if row.get("local_name") == "WeightedAverageNumberOfDilutedSharesOutstanding" and row.get("period_end") == "2026-06-30" and row.get("period_start") == "2025-07-01" and not row.get("dimensions"))
    conflict = copy.deepcopy(row); conflict["value"] += 1; conflict["context_id"] = "conflict-share-context"; structural["facts"].append(conflict)
    with pytest.raises(MSFTRefreshError, match="conflict"):
        _select_msft_shares(structural, accession="0001193125-26-323660", period_end="2026-06-30")


def test_msft_share_selector_rejects_wrong_qname():
    recipe, packet = _live()
    structural = copy.deepcopy(packet["structural_filing"])
    for row in structural["facts"]:
        if row.get("local_name") == "WeightedAverageNumberOfDilutedSharesOutstanding" and row.get("period_end") == "2026-06-30" and row.get("source_accession") == "0001193125-26-323660":
            row["qname"] = "custom:WrongSharesTag"
    with pytest.raises(MSFTRefreshError, match="wrong QName|missing"):
        _select_msft_shares(structural, accession="0001193125-26-323660", period_end="2026-06-30")


def test_msft_share_selector_accepts_official_taxonomy_year_change_not_lookalike():
    _, packet = _live()
    structural = copy.deepcopy(packet['structural_filing'])
    for row in structural['facts']:
        if row.get('local_name') == 'WeightedAverageNumberOfDilutedSharesOutstanding':
            row['namespace'] = 'http://fasb.org/us-gaap/2027'
    selected = _select_msft_shares(structural, accession='0001193125-26-323660', period_end='2026-06-30')
    assert selected['value'] > 0
    for row in structural['facts']:
        if row.get('local_name') == 'WeightedAverageNumberOfDilutedSharesOutstanding':
            row['namespace'] = 'http://fasb.org.attacker.invalid/us-gaap/2027'
    with pytest.raises(MSFTRefreshError, match='wrong QName|missing'):
        _select_msft_shares(structural, accession='0001193125-26-323660', period_end='2026-06-30')


def test_msft_capital_intensity_recomputes_for_changed_current_capex(monkeypatch):
    # Synthetic stress of the operating calculation, not a source certification.
    import app.us_valuation.refresh_msft_model as module
    recipe, packet = _live()
    original = module._financials
    baseline = build_msft_forecast(packet, recipe, cutoff='2026-09-08', approved_policy=_approved_policy())
    def stressed(*args, **kwargs):
        normalizer, financials, tax = original(*args, **kwargs)
        financials['ttm']['values']['capital_expenditures'] *= 2
        return normalizer, financials, tax
    monkeypatch.setattr(module, '_financials', stressed)
    changed = build_msft_forecast(packet, recipe, cutoff='2026-09-08', approved_policy=_approved_policy())
    assert changed['source_ledger']['segment_evidence']['capital_intensity']['scenario_multipliers']['base'] == .5
    for name in ('bear','base','bull'):
        assert changed['scenarios'][name]['assumptions']['sales_to_capital'] < baseline['scenarios'][name]['assumptions']['sales_to_capital']
        assert changed['scenarios'][name]['model']['intrinsic_value_per_share'] < baseline['scenarios'][name]['model']['intrinsic_value_per_share']


def test_msft_forecast_replays_under_alternate_frozen_cutoff_without_date_keyed_policy():
    recipe, packet = _live()
    policy = _approved_policy()
    current = build_msft_forecast(packet, recipe, cutoff="2026-09-08", approved_policy=policy)
    alternate = build_msft_forecast(packet, recipe, cutoff="2026-08-14", approved_policy=policy)
    assert current["source_ledger"]["controlling_filing"]["accessionNumber"] == alternate["source_ledger"]["controlling_filing"]["accessionNumber"]
    assert current["scenarios"]["base"]["model"]["intrinsic_value_per_share"] == alternate["scenarios"]["base"]["model"]["intrinsic_value_per_share"]


def test_msft_interim_request_reports_missing_distinct_comparable_ytd_capture():
    recipe, packet = _live()
    interim = copy.deepcopy(packet)
    interim["_selected_controlling_filing"] = {**packet["controlling_filing"], "form": "10-Q", "reportDate": "2026-03-31", "accessionNumber": "missing-interim-accession"}
    with pytest.raises(MSFTRefreshError, match="distinct captured annual structural package|comparable-YTD"):
        build_msft_forecast(interim, recipe, cutoff="2026-09-08", approved_policy=_approved_policy())


def test_live_msft_interim_builds_fy_plus_current_ytd_minus_comparable_ytd_trace():
    recipe, packet = _live_interim()
    result = build_msft_forecast(packet, recipe, cutoff="2026-05-01", approved_policy=_approved_policy())
    assert result["status"] == "forecast_bound_unbridged"
    evidence = result["source_ledger"]["segment_evidence"]
    assert evidence["status"] == "annual_plus_comparable_ytd_reconciled"
    assert evidence["period_comparison_basis"] == "ytd"
    assert evidence["interim_source"]["prior_period_end"] < evidence["interim_source"]["period_end"]
    assert evidence["interim_source"]["current_segment_totals"] == evidence["interim_source"]["consolidated_ytd"]
    assert evidence["interim_source"]["prior_segment_totals"] == evidence["interim_source"]["prior_consolidated"]
    ledger = result["source_ledger"]["input_ledger"]
    assert ledger["annual_source_accession"] == "0000950170-25-100235"
    assert ledger["interim_source_accession"] == "0001193125-26-191507"
    assert all(row["accession"] == "0001193125-26-191507" for row in ledger["interim_segment_rows"])
    assert all(row["model"]["errors"] == [] for row in result["scenarios"].values())
    assert result["source_ledger"]["controlling_filing"]["accessionNumber"] == "0001193125-26-191507"


def test_msft_missing_immediately_prior_fy_cannot_use_older_annual_in_ttm():
    recipe, packet = _live_interim()
    damaged = copy.deepcopy(packet)
    for concepts in damaged['companyfacts']['facts'].values():
        for concept in concepts.values():
            for unit, rows in concept.get('units', {}).items():
                concept['units'][unit] = [row for row in rows if row.get('end') != '2025-06-30']
    with pytest.raises(MSFTRefreshError, match='not contiguous'):
        build_msft_forecast(damaged, recipe, cutoff='2026-05-01', approved_policy=_approved_policy())
