import json
from pathlib import Path

from app.us_valuation.refresh_special_policies import bind_aptv_special_recipe, compile_special_inventory, compile_special_refresh_policy, evaluate_bound_special_recipe
from app.us_valuation.refresh_bindings import _select_complete_filings


ROOT = Path(__file__).parents[2]
OUTPUT = ROOT / "output"


def test_special_inventory_covers_recorded_special_recipe_families():
    recipes_root = OUTPUT / "us-refresh-runtime" / "recipes"
    recipes = {path.stem: json.loads(path.read_text()) for path in recipes_root.glob("*.json")}
    registry_doc = json.loads((OUTPUT / "us-refresh-runtime" / "registry.json").read_text())
    registry = {row["ticker"]: row for row in registry_doc["entries"]}
    inventory = compile_special_inventory(recipes, registry)
    assert inventory["policy_count"] == 14
    assert not inventory["gaps"]
    assert {row["ticker"] for row in inventory["policies"]} >= {"META", "OMC", "TTWO", "MRNA", "WBD"}
    assert all(row["consumer_integration"] == "not_claimed" for row in inventory["policies"])


def test_owner_cash_policy_keeps_bridge_fields_explicit():
    recipe = json.loads((OUTPUT / "us-refresh-runtime" / "recipes" / "META.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime" / "registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "META")
    policy = compile_special_refresh_policy(recipe, entry)
    assert policy["family"] == "owner_cash_multiple_with_explicit_bridge"
    assert policy["inputs"]["owner_cash"]["meaning"].startswith("Owner cash")
    assert policy["inputs"]["cash_claim"]["source_selector_required"] is True
    assert policy["inputs"]["debt_claim"]["source_selector_required"] is True


def test_asset_runway_policy_keeps_clinical_review_exception():
    recipe = json.loads((OUTPUT / "us-refresh-runtime" / "recipes" / "MRNA.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime" / "registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "MRNA")
    policy = compile_special_refresh_policy(recipe, entry)
    assert policy["family"] == "liquid_assets_less_burn_and_debt_plus_pipeline"
    assert any("clinical" in item for item in policy["unresolved_economic_rules"])


def test_bound_special_inputs_are_evaluated_not_target_fitted():
    recipe = json.loads((OUTPUT / "us-refresh-runtime" / "recipes" / "MRNA.json").read_text())
    bound = {name: dict(spec["inputs"]) for name, spec in recipe["scenarios"].items()}
    before = evaluate_bound_special_recipe(recipe, bound)["replay"]
    bound["base"]["liquid_assets"] += 100_000_000.0
    after = evaluate_bound_special_recipe(recipe, bound)["replay"]
    assert after["base"] > before["base"]


def test_aptv_binds_real_post_spin_parent_earnings_and_shares():
    recipe = json.loads((OUTPUT / "us-refresh-runtime" / "recipes" / "APTV.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime" / "registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "APTV")
    policy = compile_special_refresh_policy(recipe, entry)
    assert policy["statement_required_fields"] == {"parent_continuing_earnings": "flow", "diluted_shares": "flow", "period_end_equity": "instant"}
    assert policy["concept_config"]["fields"]["period_end_equity"]["concepts"] == ["StockholdersEquity"]
    source = OUTPUT / "batch-08-sec-source-packets-20260826" / "APTV"
    packet = {"submissions": json.loads((source / "submissions.json").read_text()), "companyfacts": json.loads((source / "companyfacts.json").read_text()), "_selected_controlling_filing": {"accession": "0001521332-26-000061", "period_start": "2026-01-01", "period_end": "2026-06-30"}}
    result = bind_aptv_special_recipe(policy, recipe, packet, cutoff="2026-08-14")
    assert result["status"] == "bound_successor_candidate"
    assert result["source_ledger"]["controlling_accession"] == "0001521332-26-000061"
    assert result["source_ledger"]["nci_subtracted_again"] is False
    assert result["source_ledger"]["annualization_factor"] == 2.0
    assert result["replay"] == recipe["replay"]


def test_aptv_policy_fields_select_real_controlling_filing():
    recipe = json.loads((OUTPUT / "us-refresh-runtime" / "recipes" / "APTV.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime" / "registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "APTV")
    policy = compile_special_refresh_policy(recipe, entry)
    source = OUTPUT / "batch-08-sec-source-packets-20260826" / "APTV"
    submissions = json.loads((source / "submissions.json").read_text())
    companyfacts = json.loads((source / "companyfacts.json").read_text())
    recent = submissions["filings"]["recent"]
    rows = [{key: values[i] for key, values in recent.items() if isinstance(values, list) and i < len(values)} for i in range(len(recent["accessionNumber"]))]
    selected, _ = _select_complete_filings(rows, companyfacts, None, cutoff="2026-08-14", required_fields=policy["statement_required_fields"], concept_config=policy["concept_config"])
    assert selected["accessionNumber"] == "0001521332-26-000061"
    assert selected["reportDate"] == "2026-06-30"


def test_aptv_rejects_synthetic_changed_quarter_without_aligned_cached_facts():
    """Synthetic boundary: a dispatcher-selected quarter must not reuse cached H1."""
    recipe = json.loads((OUTPUT / "us-refresh-runtime" / "recipes" / "APTV.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime" / "registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "APTV")
    policy = compile_special_refresh_policy(recipe, entry)
    source = OUTPUT / "batch-08-sec-source-packets-20260826" / "APTV"
    packet = {"submissions": json.loads((source / "submissions.json").read_text()), "companyfacts": json.loads((source / "companyfacts.json").read_text()), "_selected_controlling_filing": {"accession": "0001521332-26-000061", "period_start": "2026-01-01", "period_end": "2026-03-31"}}
    import pytest
    with pytest.raises(ValueError, match="selected|period|YTD|selector"):
        bind_aptv_special_recipe(policy, recipe, packet, cutoff="2026-08-14")
