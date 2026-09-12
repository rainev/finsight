import json
from pathlib import Path

from app.us_valuation.refresh_policy_migration import (
    SCHEMA,
    compile_refresh_inventory,
    compile_refresh_policy,
    verify_successor_filing,
)


def test_policy_compiler_binds_provenance_and_never_claims_ready():
    recipe = {
        "schema_version": "FINSIGHT-CALCULATION-RECIPE-1",
        "ticker": "X",
        "baseline_version": "baseline",
        "evidence_cutoff": "2026-08-14",
        "source_accession": "acc",
        "provenance": {"source_path": "/private/X.json"},
        "scenarios": {name: {"engine": "constant_growth_fcff", "inputs": {
            "revenue": 100., "fcff_margin": .1, "growth": .02,
            "wacc": .1, "terminal_growth": .02, "cash_and_investments": 1.,
            "debt": 2., "noncontrolling_interests": 0., "shares": 10.,
        }} for name in ("bear", "base", "bull")},
    }
    policy = compile_refresh_policy(recipe, {"baseline_sha256": "hash", "controlling_filing": {"accession": "fresh"}})
    assert policy["schema_version"] == SCHEMA
    assert policy["policy_status"] == "migration_evidence_only"
    assert policy["refresh_status"] == "requires_source_reselection"
    assert policy["baseline_binding"]["source_accession"] == "acc"
    assert policy["source_field_lineage"]["revenue"]["source_selector_required"] is True
    assert verify_successor_filing(policy, {"ticker": "X", "accession": "new", "filed_date": "2026-09-01"})["status"] == "candidate_metadata_only"


def test_frozen_inventory_has_exact_numeric_coverage():
    root = Path(__file__).parents[2] / "output" / "us-refresh-runtime"
    inventory = compile_refresh_inventory(root / "recipes", root / "registry.json")
    assert inventory["recipe_count"] == 419
    assert inventory["expected_numeric_count"] == 419
    assert inventory["coverage_exact"] is True
    assert inventory["policy_status_counts"] == {"migration_evidence_only": 419}
    assert set(inventory["engine_coverage"]) >= {"enterprise_cash_fcff", "constant_growth_fcff", "residual_income"}
