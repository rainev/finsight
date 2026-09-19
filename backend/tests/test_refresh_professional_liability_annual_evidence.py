from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from app.us_valuation.refresh_professional_liability_annual_evidence import (
    bind_annual_professional_liability_cash,
    extract_annual_professional_liability_evidence,
    professional_liability_annual_policy,
    validate_annual_professional_liability_evidence,
)
from app.us_valuation.refresh_professional_liability_scope import (
    bind_professional_liability_scope,
    professional_liability_policy,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "output"


def sources():
    return [
        {
            "package_manifest_path": "wg35-hca-annual-cache-20260917/filings/HCA/CIK0000860730-000119312526044769/9d8a6a90629ea5fdfd8022595a878f686cf079d5ff70d88cb401d3f546573f8a/package-manifest.json",
            "structural_path": "wg35-hca-annual-evidence-network-20260917/HCA/0001193125-26-044769/structural-filing.json",
        },
        {
            "package_manifest_path": "wg35-hca-annual-cache-20260917/filings/HCA/CIK0000860730-000095017025020134/0be1d8d58d9fc848f16693671345b8ef7a2d19e6fbb6b31b29a89b4f261ffddd/package-manifest.json",
            "structural_path": "wg35-hca-annual-evidence-network-20260917/HCA/0000950170-25-020134/structural-filing.json",
        },
    ]


def receipt():
    return json.loads((SOURCE_ROOT / "us-refresh-runtime/professional-liability-annual-evidence/HCA.json").read_bytes())


def current_inputs():
    structural = json.loads((SOURCE_ROOT / "batch-14-structural-sources-20260829/HCA/structural-filing.json").read_bytes())
    narrative = json.loads((SOURCE_ROOT / "us-refresh-runtime/narrative-evidence/HCA.json").read_bytes())
    packet = SOURCE_ROOT / "batch-14-sec-source-packets-20260829/HCA"
    companyfacts = json.loads((packet / "companyfacts.json").read_bytes())
    submissions = json.loads((packet / "submissions.json").read_bytes())
    recipe = json.loads((SOURCE_ROOT / "us-refresh-runtime/recipes/HCA.json").read_bytes())
    current = bind_professional_liability_scope(professional_liability_policy("HCA"), structural, narrative,
        companyfacts, submissions, recipe, cutoff="2026-08-14", source_root=SOURCE_ROOT)
    return current, recipe


def test_real_annual_packages_reconcile_reserves_reinsurance_investments_and_cash():
    value = validate_annual_professional_liability_evidence(receipt(), source_root=SOURCE_ROOT, cutoff="2026-08-14")
    latest = value["observations"][0]
    balance = latest["reconciled_balance_periods"]["2025-12-31"]
    assert balance["gross_reserve"] == 2_044_000_000
    assert balance["current_reserve"] == 578_000_000
    assert balance["noncurrent_reserve"] == 1_466_000_000
    assert balance["recognized_reinsurance_receivable"] == 47_000_000
    assert balance["net_reserve"] == 1_997_000_000
    assert balance["insurance_investments_total"] == 588_000_000
    assert balance["insurance_investments_current"] == 103_000_000
    assert balance["insurance_investments_noncurrent"] == 485_000_000
    assert balance["ordinary_nci"] == 3_256_000_000
    assert latest["professional_liability_premiums"] is None


def test_real_rollforward_and_ocf_overlap_is_exact_and_not_a_second_cash_adjustment():
    value = receipt(); latest = value["observations"][0]; rows = latest["rollforward"]
    assert rows["2025"] == {
        "opening_net_reserve": 2_051_000_000, "current_year_provision": 525_000_000,
        "prior_year_development": 126_000_000, "total_provision": 651_000_000,
        "current_year_claim_payments": 12_000_000, "prior_year_claim_payments": 690_000_000,
        "total_claim_payments": 702_000_000, "retroactive_reinsurance_effect": -3_000_000,
        "ending_net_reserve": 1_997_000_000,
    }
    assert [rows[y]["total_claim_payments"] for y in ("2023", "2024", "2025")] == [550_000_000, 600_000_000, 702_000_000]
    assert [latest["operating_cash_flow"][y]["value"] for y in ("2023", "2024", "2025")] == [9_431_000_000, 10_514_000_000, 12_636_000_000]
    assert [latest["ordinary_nci_owner_flows_nonadditive"]["nci_income"][y]["value"] for y in ("2023", "2024", "2025")] == [849_000_000, 897_000_000, 998_000_000]
    assert [latest["ordinary_nci_owner_flows_nonadditive"]["nci_distributions"][y]["value"] for y in ("2023", "2024", "2025")] == [640_000_000, 711_000_000, 827_000_000]
    older = value["observations"][1]
    assert older["rollforward"]["2024"] == rows["2024"] and older["rollforward"]["2023"] == rows["2023"]


def test_current_overlap_preserves_bounded_reserve_sensitivity_until_runoff_is_reconciled():
    current, recipe = current_inputs()
    value = bind_annual_professional_liability_cash(professional_liability_annual_policy("HCA"), receipt(), current,
        recipe, source_root=SOURCE_ROOT, cutoff="2026-08-14")
    assert value["historical_net_claim_payments"] == [550_000_000, 600_000_000, 702_000_000]
    assert value["current_next_12_month_expected_net_payments"] == 573_000_000
    assert value["latest_annual_recognized_reinsurance_receivable"] == 47_000_000
    assert value["latest_annual_ordinary_nci"] == 3_256_000_000 and value["current_ordinary_nci"] == 3_433_000_000
    assert value["claim_adjustment"] is None and value["professional_liability_premiums"] is None
    assert not value["numeric_successor_issued"]
    assert not value["candidate_eligible_for_remaining_bridge_checks"]
    assert value["scenario_diagnostics"]["bear"]["retained_noncurrent_reserve_sensitivity"] == 1_464_000_000
    assert value["scenario_diagnostics"]["base"]["retained_noncurrent_reserve_sensitivity"] == 732_000_000
    assert all(row["value_change"] == 0 and row["old_value"] == row["retained_value"] for row in value["scenario_diagnostics"].values())


def test_sources_must_be_latest_first_and_cutoff_safe():
    with pytest.raises(ValueError, match="latest first"):
        extract_annual_professional_liability_evidence("HCA", list(reversed(sources())), source_root=SOURCE_ROOT, cutoff="2026-08-14")
    with pytest.raises(ValueError, match="cutoff"):
        extract_annual_professional_liability_evidence("HCA", sources(), source_root=SOURCE_ROOT, cutoff="2025-12-31")


def test_structural_reserve_or_reinsurance_mutation_fails_closed(tmp_path):
    copied = []
    for index, source in enumerate(sources()):
        package_source = (SOURCE_ROOT / source["package_manifest_path"]).parent
        package_target = tmp_path / f"package-{index}"
        shutil.copytree(package_source, package_target)
        structural_target = tmp_path / f"structural-{index}.json"
        shutil.copy2(SOURCE_ROOT / source["structural_path"], structural_target)
        copied.append({"package_manifest_path": f"package-{index}/package-manifest.json", "structural_path": structural_target.name})
    structural = json.loads((tmp_path / copied[0]["structural_path"]).read_bytes())
    row = next(row for row in structural["facts"] if row["local_name"] == "CurrentProfessionalLiabilityRisks" and row["period_end"] == "2025-12-31")
    row["value"] += 1
    (tmp_path / copied[0]["structural_path"]).write_text(json.dumps(structural))
    with pytest.raises(ValueError, match="fact conflicts|reserve does not reconcile"):
        extract_annual_professional_liability_evidence("HCA", copied, source_root=tmp_path, cutoff="2026-08-14")


def test_policy_has_semantic_names_not_filing_amounts_or_dates():
    policy = professional_liability_annual_policy("HCA")
    encoded = json.dumps(policy, sort_keys=True)
    assert "0001193125-26-044769" not in encoded and "2025-12-31" not in encoded
    assert "2044000000" not in encoded and "702000000" not in encoded
    policy["gross_reserve_local"] = "wrong"
    assert professional_liability_annual_policy("HCA")["gross_reserve_local"] == "ProfessionalLiabilityRisksReserves"


def test_receipt_or_policy_drift_fails_closed():
    annual = receipt(); annual["observations"][0]["professional_liability_premiums"] = 0
    with pytest.raises(ValueError, match="drift"):
        validate_annual_professional_liability_evidence(annual, source_root=SOURCE_ROOT, cutoff="2026-08-14")
    current, recipe = current_inputs(); policy = professional_liability_annual_policy("HCA"); policy["history_payment_rule"] = "always"
    with pytest.raises(ValueError, match="identity"):
        bind_annual_professional_liability_cash(policy, receipt(), current, recipe, source_root=SOURCE_ROOT, cutoff="2026-08-14")
