from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_work_register import (
    build_work_register,
    canonical_json_bytes,
    render_markdown,
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _fixture(tmp_path: Path, *, source_reports: list[dict] | None = None) -> Path:
    root = tmp_path / "runtime"
    registry_entries = [
        {
            "ticker": "AAA",
            "batch": 1,
            "cik": "1",
            "availability_type": "available",
            "source_audit": "docs/audit/aaa.md",
            "primary_model": "fcff_dcf",
        },
        {
            "ticker": "BBB",
            "batch": 1,
            "cik": "2",
            "availability_type": "not_available",
            "source_audit": "docs/audit/bbb.md",
            "primary_model": "conditional_estimate",
        },
    ]
    _write(root / "registry.json", {"schema_version": "registry", "entries": registry_entries})
    _write(
        root / "baseline" / "manifest.json",
        {"schema_version": "manifest", "entries": [{"ticker": "AAA", "artifact_sha256": "a"}, {"ticker": "BBB", "artifact_sha256": "b"}]},
    )
    _write(
        root / "policy-compilation-report.json",
        {
            "policy_sha256": "policy-current",
            "rows": [
                {"ticker": "AAA", "status": "contract_compiled", "reason": None},
                {"ticker": "BBB", "status": "prior_unavailable", "reason": "No numeric baseline recipe; recovery is separate."},
            ],
        },
    )
    _write(
        root / "refresh-policies.json",
        {
            "AAA": {"family": "enterprise_cash_fcff", "version": "v1", "inputs": {"cash": {}}},
            "BBB": {"family": "enterprise_cash_fcff", "version": "v1", "inputs": {"cash": {}}},
        },
    )
    _write(
        root / "recipes" / "AAA.json",
        {"ticker": "AAA", "replay": {"low": 1.0, "base": 2.0, "high": 3.0}, "scenarios": {"base": {"engine": "enterprise_cash_fcff"}}},
    )
    for index, report in enumerate(source_reports or []):
        _write(root / "source-validation" / f"r{index}" / "report.json", report)
    return root


def test_real_runtime_has_exact_denominator_and_separate_states():
    root = Path(__file__).parents[2] / "output" / "us-refresh-runtime"
    register = build_work_register(root)
    assert register["scope"]["registry_count"] == 440
    assert len(register["companies"]) == 440
    assert len({row["ticker"] for row in register["companies"]}) == 440
    assert register["scope"]["recipe_count"] == 419
    compiled=json.loads((root/'policy-compilation-report.json').read_text())['contract_compiled']
    assert register["counts"]["instruction_compiled"] == compiled
    assert register["counts"]["implementation_gap"] == 419-compiled
    assert register["counts"]["prior_unavailable"] == 21
    assert register["implementation_queue"]["family_adapter_count"] == 17
    assert register["counts"].get("successive_period_verified", 0) == 0
    assert register["source_reports"]["composable"] is False
    assert any(
        phrase in register["source_reports"]["composability_reason"]
        for phrase in ("different", "omits")
    )


def test_conflicting_source_receipts_are_preserved_and_not_composable(tmp_path: Path):
    reports = [
        {
            "scope": "focused A",
            "registry_sha256": "registry",
            "policy_sha256": "old-policy",
            "implementation_sha256": "old-implementation",
            "rows": [
                {"ticker": "AAA", "status": "cached_source_bound", "source_capture": {"path": "packet/a"}},
                {"ticker": "BBB", "status": "cached_source_gap", "reason": "missing source"},
            ],
        },
        {
            "scope": "focused B",
            "registry_sha256": "registry",
            "policy_sha256": "different-policy",
            "implementation_sha256": "different-implementation",
            "rows": [
                {"ticker": "AAA", "status": "source_or_economic_review", "reason": "bridge review"},
            ],
        },
    ]
    register = build_work_register(_fixture(tmp_path, source_reports=reports), expected_count=2)
    assert register["source_reports"]["composable"] is False
    aaa = next(row for row in register["companies"] if row["ticker"] == "AAA")
    assert aaa["evidence"]["source_report"]
    assert aaa["states"]["source_bound_current_version"] is False
    bbb = next(row for row in register["companies"] if row["ticker"] == "BBB")
    assert bbb["states"]["source_gap"] is True
    assert bbb["states"]["prior_unavailable"] is True


def test_claim_classification_requires_supported_text_and_keeps_unclassified_flag(tmp_path: Path):
    reports = [
        {
            "scope": "claims",
            "registry_sha256": "registry",
            "policy_sha256": "policy-current",
            "rows": [
                {"ticker": "AAA", "status": "source_or_economic_review", "special_claim_flag": True, "reason": "broad claim review"},
                {"ticker": "BBB", "status": "prior_unavailable", "special_claim_flag": True, "reason": "claim review"},
            ],
        }
    ]
    register = build_work_register(_fixture(tmp_path, source_reports=reports), expected_count=2)
    aaa = next(row for row in register["companies"] if row["ticker"] == "AAA")
    assert aaa["special_claims"]["mechanisms"] == ["unclassified_review"]
    assert aaa["special_claims"]["flagged"] is True
    report = render_markdown(register)
    assert "What works" in report and "What is blocked" in report and "Next working group" in report


def test_duplicate_registry_rows_fail_closed(tmp_path: Path):
    root = _fixture(tmp_path)
    registry = json.loads((root / "registry.json").read_text())
    registry["entries"].append(dict(registry["entries"][0]))
    _write(root / "registry.json", registry)
    with pytest.raises(ValueError, match="duplicate ticker"):
        build_work_register(root, expected_count=2)


def test_missing_recipe_for_numeric_baseline_is_implementation_gap(tmp_path: Path):
    root = _fixture(tmp_path)
    registry = json.loads((root / "registry.json").read_text())
    registry["entries"][1]["availability_type"] = "available"
    _write(root / "registry.json", registry)
    register = build_work_register(root, expected_count=2)
    bbb = next(row for row in register["companies"] if row["ticker"] == "BBB")
    assert bbb["prior_unavailable"] is False
    assert bbb["implementation_gap"] is True
    assert "recipe" in bbb["next_action"]


def test_numeric_recipe_slot_does_not_prove_claim_mechanism(tmp_path: Path):
    root = _fixture(tmp_path)
    policies = json.loads((root / "refresh-policies.json").read_text())
    policies["AAA"]["baseline_non_debt_claims"] = {"base": {"preferred_equity": 100.0}}
    _write(root / "refresh-policies.json", policies)
    register = build_work_register(root, expected_count=2)
    aaa = next(row for row in register["companies"] if row["ticker"] == "AAA")
    assert "preferred_stock" not in aaa["special_claims"]["mechanisms"]


def test_explicit_nested_source_policy_classifies_claim_mechanism(tmp_path: Path):
    root = _fixture(tmp_path)
    policies = json.loads((root / "refresh-policies.json").read_text())
    policies["AAA"]["inputs"] = {
        "legal_claim": {
            "selector": "special_claim",
            "policy": {"schema_version": "FINSIGHT-LITIGATION-CLAIM-1"},
        }
    }
    policies["AAA"]["reason_codes"] = ["baseline_non_debt_claim_scope_requires_source_rule"]
    _write(root / "refresh-policies.json", policies)
    register = build_work_register(root, expected_count=2)
    aaa = next(row for row in register["companies"] if row["ticker"] == "AAA")
    assert aaa["special_claims"]["mechanisms"] == ["litigation"]


def test_reported_claim_scope_classifies_nci_without_numeric_slot_inference(tmp_path: Path):
    root = _fixture(tmp_path)
    _write(
        root / "source-validation" / "claims" / "report.json",
        {
            "scope": "claims",
            "registry_sha256": "registry",
            "policy_sha256": "policy-current",
            "rows": [{"ticker": "AAA", "special_claim_flag": True}],
        },
    )
    policies = json.loads((root / "refresh-policies.json").read_text())
    policies["AAA"]["reported_claim_scope"] = {
        "version": "FINSIGHT-REPORTED-NCI-SCOPE-2",
        "ticker": "AAA",
    }
    _write(root / "refresh-policies.json", policies)
    register = build_work_register(root, expected_count=2)
    aaa = next(row for row in register["companies"] if row["ticker"] == "AAA")
    assert aaa["special_claims"]["mechanisms"] == ["minority_interests"]


def test_explicit_operating_claim_policy_remains_classified_after_gap_is_closed(tmp_path: Path):
    root = _fixture(tmp_path)
    policies = json.loads((root / "refresh-policies.json").read_text())
    policies["AAA"]["inputs"] = {
        "benefit_claim": {
            "selector": "special_claim",
            "policy": {
                "schema_version": "FINSIGHT-OPERATING-CLAIM-1",
                "treatment": "pension liability and environmental reserve stay separate from NCI",
            },
        }
    }
    _write(root / "refresh-policies.json", policies)
    register = build_work_register(root, expected_count=2)
    aaa = next(row for row in register["companies"] if row["ticker"] == "AAA")
    assert aaa["special_claims"]["flagged"] is False
    assert aaa["special_claims"]["mechanisms"] == ["minority_interests", "operating_reserves"]


def test_customer_funds_schema_and_classification_only_contract_are_machine_readable(tmp_path: Path):
    root=_fixture(tmp_path)
    policies=json.loads((root/'refresh-policies.json').read_text())
    policies['AAA']['inputs']={'funds':{'selector':'special_claim','policy':{
        'schema_version':'FINSIGHT-CUSTOMER-FUNDS-1',
        'treatment':'matched customer funds and guaranty funds remain operating'}}}
    policies['BBB']['claim_classification']={
        'version':'FINSIGHT-CLAIM-CLASSIFICATION-WG8-1',
        'mechanisms':['acquisition payments','preferred stock'],
        'status':'implementation_required'}
    _write(root/'refresh-policies.json',policies)
    register=build_work_register(root,expected_count=2)
    aaa=next(row for row in register['companies'] if row['ticker']=='AAA')
    bbb=next(row for row in register['companies'] if row['ticker']=='BBB')
    assert 'customer_funds' in aaa['special_claims']['mechanisms']
    assert bbb['special_claims']['mechanisms']==['preferred_stock','acquisition_payments']


def test_acquisition_financing_schema_classifies_only_explicit_mechanisms(tmp_path: Path):
    root=_fixture(tmp_path)
    policies=json.loads((root/'refresh-policies.json').read_text())
    policies['AAA']['inputs']={'claim':{'selector':'special_claim','policy':{
        'schema_version':'FINSIGHT-ACQUISITION-FINANCING-CLAIMS-1',
        'mode':'complex_financing_review',
        'treatment':'acquisition payments preferred stock minority interests financing claims'}}}
    _write(root/'refresh-policies.json',policies)
    row=next(item for item in build_work_register(root,expected_count=2)['companies'] if item['ticker']=='AAA')
    assert row['special_claims']['mechanisms']==[
        'minority_interests','preferred_stock','acquisition_payments']


def test_hash_verified_private_claim_formula_classifies_mechanism(tmp_path: Path):
    import hashlib
    root=_fixture(tmp_path)
    private=root/'private.json';_write(private,{'source_ledger':{'bridge_reconciliation':{
        'other_equity_claim_formula':'Reported NCI plus litigation reserve and timed purchase commitment.'}}})
    raw=private.read_bytes();recipe=json.loads((root/'recipes/AAA.json').read_text())
    recipe['provenance']={'source_path':str(private),'private_sha256':hashlib.sha256(raw).hexdigest()}
    _write(root/'recipes/AAA.json',recipe)
    policies=json.loads((root/'refresh-policies.json').read_text());policies['AAA']['reason_codes']=['baseline_non_debt_claim_scope_requires_source_rule'];_write(root/'refresh-policies.json',policies)
    value=build_work_register(root,expected_count=2)
    claim=next(row for row in value['companies'] if row['ticker']=='AAA')['special_claims']
    assert claim['mechanisms']==['minority_interests','litigation','timed_commitments']
    private.write_text('{}')
    claim=next(row for row in build_work_register(root,expected_count=2)['companies'] if row['ticker']=='AAA')['special_claims']
    assert claim['mechanisms']==['unclassified_review']


def test_generic_source_missing_nci_does_not_classify_legacy_claim_slot(tmp_path: Path):
    reports=[{'scope':'source','registry_sha256':'x','policy_sha256':'y','implementation_sha256':'z',
        'rows':[{'ticker':'AAA','status':'source_or_economic_review','reason':'unresolved source fields: noncontrolling_interests, preferred_equity'}]}]
    value=build_work_register(_fixture(tmp_path,source_reports=reports),expected_count=2)
    claim=next(row for row in value['companies'] if row['ticker']=='AAA')['special_claims']
    assert claim['flagged'] is False and claim['mechanisms']==[]


def test_source_failures_are_separate_from_missing_financial_evidence(tmp_path: Path):
    reports=[{'scope':'source','registry_sha256':'x','policy_sha256':'y','implementation_sha256':'z','rows':[
        {'ticker':'AAA','status':'cached_source_gap','reason':'cached source packet is missing'},
        {'ticker':'BBB','status':'source_or_economic_review','reason':'current bridge has unresolved source fields: debt'}]}]
    value=build_work_register(_fixture(tmp_path,source_reports=reports),expected_count=2)
    by={row['ticker']:row for row in value['companies']}
    assert by['AAA']['source_issue']['category']=='acquisition_or_cache_failure'
    assert by['BBB']['source_issue']['category']=='missing_financial_evidence'


def test_canonical_json_is_byte_stable(tmp_path: Path):
    register = build_work_register(_fixture(tmp_path), expected_count=2)
    assert canonical_json_bytes(register) == canonical_json_bytes(json.loads(canonical_json_bytes(register)))
