from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from app.us_valuation.approved_cash_only_scope import (
    CashOnlyScopeError,
    bind_current_cash_only_scope,
    compile_approved_cash_only_scope,
)


ROOT = Path(__file__).parents[2]
RECIPE = ROOT / "output/us-refresh-operational-uat-20260909-wg6-nue-a/catalogs/snapshots/REFRESH-OPERATIONAL-UAT-a/recipes/BBY.json"
CURRENT_PACKAGE = ROOT / "output/latest-universe-20260919/final-discovery/parsed/parsed-structural/0000764478-26-000042-afe0f63c3987eb87-22e48483c36e5cf0.json.gz"


def _recipe() -> dict:
    return json.loads(RECIPE.read_text())


def _package() -> dict:
    return json.loads(gzip.open(CURRENT_PACKAGE, "rt").read())


def _scope() -> dict:
    return compile_approved_cash_only_scope(
        _recipe(),
        requested_profile={
            "name": "cash_only",
            "cash_qname": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            "unit": "USD",
        },
    )


def test_real_bby_cash_only_scope_compiles_and_binds_current_cash():
    scope = _scope()
    assert scope["ticker"] == "BBY"
    assert scope["cik"] == "0000764478"
    assert scope["private_cash"]["value"] == 1_749_000_000.0
    assert scope["excluded"] == {
        "other_investments": "unknown_outside_scope_not_zero",
        "restricted_cash": "unknown_outside_scope_not_zero",
    }

    bound = bind_current_cash_only_scope(
        scope,
        _package(),
        current_accession="0000764478-26-000042",
        cik="0000764478",
        period_end="2026-08-01",
    )
    assert bound["cash_and_cash_equivalents"] == 2_255_000_000.0
    assert bound["source"]["qname"] == "us-gaap:CashAndCashEquivalentsAtCarryingValue"
    assert bound["source"]["dimensions"] == []
    assert bound["excluded"]["other_investments"] == "unknown_outside_scope_not_zero"
    assert "Debt and noncontrolling interests" in " ".join(bound["limitations"])


def test_scope_requires_explicit_profile():
    with pytest.raises(CashOnlyScopeError, match="explicit cash_only profile"):
        compile_approved_cash_only_scope(_recipe(), requested_profile=None)


def test_scope_rejects_private_hash_mismatch():
    recipe = _recipe()
    recipe["provenance"]["private_sha256"] = "0" * 64
    with pytest.raises(CashOnlyScopeError, match="private provenance hash mismatch"):
        compile_approved_cash_only_scope(recipe, requested_profile="cash_only")


def test_scope_rejects_private_cash_source_not_reported():
    recipe = _recipe()
    private = json.loads(Path(recipe["provenance"]["source_path"]).read_text())
    rows = private["history_backed"]["source_ledger"]["bridge_sources"]
    cash_row = next(row for row in rows if row.get("concept") == "us-gaap:CashAndCashEquivalentsAtCarryingValue")
    cash_row["reported_vs_estimated"] = "estimated"
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        output = root / "output"
        output.mkdir()
        path = output / "private.json"
        raw = (json.dumps(private, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        recipe["provenance"]["source_path"] = "output/private.json"
        import hashlib
        recipe["provenance"]["private_sha256"] = hashlib.sha256(raw).hexdigest()
        with pytest.raises(CashOnlyScopeError, match="not reported"):
            compile_approved_cash_only_scope(recipe, requested_profile="cash_only", project_root=root)


def test_scope_rejects_private_issuer_mismatch():
    recipe = _recipe()
    private = json.loads(Path(recipe["provenance"]["source_path"]).read_text())
    private["issuer"]["ticker"] = "NOT_BBY"
    # Keep the source immutable; replace the in-memory loader path with a
    # temporary serialized packet and its matching hash.
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        output = root / "output"
        output.mkdir()
        path = output / "private.json"
        raw = (json.dumps(private, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        recipe["provenance"]["source_path"] = "output/private.json"
        import hashlib
        recipe["provenance"]["private_sha256"] = hashlib.sha256(raw).hexdigest()
        with pytest.raises(CashOnlyScopeError, match="ticker conflict"):
            compile_approved_cash_only_scope(recipe, requested_profile="cash_only", project_root=root)


def test_scope_resolves_relative_private_path_against_project_root():
    recipe = _recipe()
    source = Path(recipe["provenance"]["source_path"])
    root = ROOT
    recipe["provenance"]["source_path"] = str(source.relative_to(root))
    scope = compile_approved_cash_only_scope(recipe, requested_profile="cash_only", project_root=root)
    assert scope["private_cash"]["value"] == 1_749_000_000.0


def test_scope_rejects_missing_exact_current_cash_fact():
    scope = _scope()
    package = _package()
    package["parsed"]["facts"] = [
        fact for fact in package["parsed"]["facts"]
        if fact.get("qname") != "us-gaap:CashAndCashEquivalentsAtCarryingValue"
    ]
    with pytest.raises(CashOnlyScopeError, match="no exact undimensioned cash fact"):
        bind_current_cash_only_scope(
            scope,
            package,
            current_accession="0000764478-26-000042",
            cik="0000764478",
            period_end="2026-08-01",
        )


def test_parsed_only_real_bby_package_derives_identity_from_facts():
    scope = _scope()
    parsed_only = _package()["parsed"]
    bound = bind_current_cash_only_scope(
        scope,
        parsed_only,
        current_accession="0000764478-26-000042",
        cik="0000764478",
        period_end="2026-08-01",
    )
    assert bound["cash_and_cash_equivalents"] == 2_255_000_000.0


@pytest.mark.parametrize("mutation, message", [
    ("missing_entity", "entity identity"),
    ("typed_dimensions", "dimensions"),
    ("duration", "duration-based"),
    ("negative", "cannot be negative"),
])
def test_current_cash_fact_identity_and_period_contract_is_strict(mutation, message):
    scope = _scope()
    package = _package()
    matches = [
        fact for fact in package["parsed"]["facts"]
        if fact.get("qname") == scope["cash_qname"] and fact.get("period_end") == "2026-08-01"
    ]
    assert matches
    for fact in matches:
        if mutation == "missing_entity":
            fact.pop("entity_identifier", None)
        elif mutation == "typed_dimensions":
            fact["typed_dimensions"] = [["example", "member"]]
        elif mutation == "duration":
            fact["period_start"] = "2026-02-01"
        elif mutation == "negative":
            fact["value"] = -1
    with pytest.raises(CashOnlyScopeError, match=message):
        bind_current_cash_only_scope(
            scope,
            package,
            current_accession="0000764478-26-000042",
            cik="0000764478",
            period_end="2026-08-01",
        )


def test_current_package_requires_complete_filing_metadata():
    scope = _scope()
    package = _package()
    package["parsed"].pop("filing_metadata")
    with pytest.raises(CashOnlyScopeError, match="filing metadata is missing"):
        bind_current_cash_only_scope(
            scope,
            package,
            current_accession="0000764478-26-000042",
            cik="0000764478",
            period_end="2026-08-01",
        )


def test_scope_rejects_current_identity_mismatch():
    with pytest.raises(CashOnlyScopeError, match="CIK does not match"):
        bind_current_cash_only_scope(
            _scope(),
            _package(),
            current_accession="0000764478-26-000042",
            cik="0000006281",
            period_end="2026-08-01",
        )
