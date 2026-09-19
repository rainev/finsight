from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_acquisition_claims import (
    ordinary_nci_acquisition_claim_policy,
    select_acquisition_claim,
)
from app.us_valuation.refresh_bridge_scope_policies import (
    AGGREGATE_DEBT_SCOPE_RULES,
    PREFERRED_EQUITY_ZERO_RULES,
    BridgeScopeReviewRequired,
    aggregate_debt_field_availability,
    preferred_equity_zero_availability,
)
from app.us_valuation.refresh_litigation_claims import litigation_claim_policy, select_litigation_claim
from app.us_valuation.refresh_operating_policies import _policy_for_entry
from app.us_valuation.refresh_reported_claim_scope import (
    REPORTED_NCI_SCOPE_RULES,
    reported_nci_field_availability,
)
from app.us_valuation.xbrl import load_concept_config


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    ticker: ROOT / f"output/us-refresh-runtime/wg18-current-parser/{ticker}/structural-filing.json"
    for ticker in ("GLW", "MDT", "PFE")
}


def _source(ticker: str):
    structural = json.loads(SOURCES[ticker].read_bytes())
    filing = {
        "accessionNumber": structural["source_accession"],
        "reportDate": structural["report_date"],
        "filingDate": structural["filed_date"],
        "form": structural["form"],
    }
    return structural, filing


def _forbidden_policy_keys(value):
    if isinstance(value, dict):
        return any(
            key in {"amount", "accession", "filed_date", "period_end"}
            or _forbidden_policy_keys(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_forbidden_policy_keys(item) for item in value)
    return False


@pytest.mark.parametrize(
    ("ticker", "expected"),
    (("GLW", 567_000_000), ("MDT", 609_000_000), ("PFE", 302_000_000)),
)
def test_wg18_binds_ordinary_nci_and_keeps_earnings_as_duration_diagnostics(ticker, expected):
    structural, filing = _source(ticker)
    rule = REPORTED_NCI_SCOPE_RULES[ticker]
    availability, proof = reported_nci_field_availability(
        ticker=ticker,
        policy=asdict(rule),
        structural_packet=structural,
        accession=filing["accessionNumber"],
        period_end=filing["reportDate"],
    )
    assert availability.value == proof["source_total"] == expected
    assert {row["qname"] for row in proof["duration_diagnostics"]} == {
        "us-gaap:NetIncomeLossAttributableToNoncontrollingInterest"
    }
    assert all(row["period_start"] < row["period_end"] for row in proof["duration_diagnostics"])


def test_glw_single_noncurrent_claim_stays_separate_from_nci_and_environmental_reserve():
    structural, filing = _source("GLW")
    policy = ordinary_nci_acquisition_claim_policy("GLW")
    result = select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 156_000_000
    assert result["components"] == {
        "acquisition_carrying_liability": 156_000_000,
        "ordinary_nci_is_separate": 567_000_000,
        "operating_reserves_not_added": [85_000_000],
    }


def test_mdt_reconciles_aggregate_typed_locations_and_level3_components_once():
    structural, filing = _source("MDT")
    policy = ordinary_nci_acquisition_claim_policy("MDT")
    result = select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 163_000_000
    assert result["components"] == {
        "aggregate_carrying_liability": 163_000_000,
        "current_portion": 32_000_000,
        "noncurrent_portion": 131_000_000,
        "level3_components": {
            "RevenueMilestoneMember": 141_000_000,
            "ProductDevelopmentMilestoneMember": 22_000_000,
        },
        "acquisition_cash_is_not_added": [406_000_000],
        "measurement_changes_are_not_claims": [-5_000_000],
    }


def test_mdt_operating_legal_accrual_is_not_deducted_twice():
    structural, filing = _source("MDT")
    policy = litigation_claim_policy("MDT")
    result = select_litigation_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 0
    assert result["components"] == {
        "operating_loss_contingency_accrual": 200_000_000,
        "additional_equity_bridge_claim": 0.0,
    }


def test_pfe_sums_current_and_noncurrent_and_never_adds_level3_duplicates():
    structural, filing = _source("PFE")
    policy = ordinary_nci_acquisition_claim_policy("PFE")
    result = select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")
    assert result["status"] == "source_bound"
    assert result["claim_adjustment"] == 2_259_000_000
    assert result["components"] == {
        "current_carrying_portion": 96_000_000,
        "noncurrent_carrying_portion": 2_163_000_000,
        "aggregate_carrying_liability": 2_259_000_000,
        "measurement_changes_are_not_claims": [255_000_000, 550_000_000],
    }


def test_wg18_debt_and_preferred_scopes_reconcile_current_real_facts():
    expected_debt = {"GLW": 8_424_000_000, "MDT": 28_131_000_000, "PFE": 63_194_000_000}
    for ticker, debt in expected_debt.items():
        structural, filing = _source(ticker)
        rule = AGGREGATE_DEBT_SCOPE_RULES[ticker]
        availability, proof = aggregate_debt_field_availability(
            ticker=ticker, policy=asdict(rule), structural_packet=structural,
            accession=filing["accessionNumber"], period_end=filing["reportDate"],
        )
        assert availability.value == proof["total"] == debt
        preferred = PREFERRED_EQUITY_ZERO_RULES[ticker]
        zero, zero_proof = preferred_equity_zero_availability(
            ticker=ticker, policy=preferred, structural_packet=structural,
            accession=filing["accessionNumber"], period_end=filing["reportDate"],
        )
        assert zero.value == zero_proof["value"] == 0


def test_glw_precision_reconciliation_and_mdt_par_only_preferred_are_fail_closed():
    structural, filing = _source("GLW")
    rule = AGGREGATE_DEBT_SCOPE_RULES["GLW"]
    coarse = next(
        row for row in structural["facts"]
        if row.get("qname") == "us-gaap:LongTermDebtAndCapitalLeaseObligations"
        and row.get("period_end") == filing["reportDate"] and row.get("decimals") == "-8"
        and not row.get("dimensions")
    )
    coarse["value"] += 100_000_000
    with pytest.raises(BridgeScopeReviewRequired, match="rounded debt presentation conflicts"):
        aggregate_debt_field_availability(
            ticker="GLW", policy=asdict(rule), structural_packet=structural,
            accession=filing["accessionNumber"], period_end=filing["reportDate"],
        )

    structural, filing = _source("MDT")
    preferred = PREFERRED_EQUITY_ZERO_RULES["MDT"]
    share = next(
        row for row in structural["facts"]
        if row.get("qname") == "us-gaap:PreferredStockSharesIssued"
        and row.get("period_end") == filing["reportDate"] and not row.get("dimensions")
    )
    share["value"] = 1
    with pytest.raises(BridgeScopeReviewRequired, match="reported zero issued shares"):
        preferred_equity_zero_availability(
            ticker="MDT", policy=preferred, structural_packet=structural,
            accession=filing["accessionNumber"], period_end=filing["reportDate"],
        )


@pytest.mark.parametrize("ticker", ["GLW", "MDT", "PFE"])
def test_wg18_policies_have_no_filing_amounts_or_dates_and_reject_tampering(ticker):
    structural, filing = _source(ticker)
    policy = ordinary_nci_acquisition_claim_policy(ticker)
    assert not _forbidden_policy_keys(policy)
    tampered = deepcopy(policy)
    tampered["version"] = "tampered"
    with pytest.raises(RuntimeError, match="identity/version mismatch"):
        select_acquisition_claim(tampered, structural, filing, policy["cik"], "2026-08-14")


def test_mdt_missing_typed_member_and_duplicate_drift_fail_closed():
    structural, filing = _source("MDT")
    policy = ordinary_nci_acquisition_claim_policy("MDT")
    location = next(
        row for row in structural["facts"]
        if row.get("qname") == policy["qname"]
        and row.get("period_end") == filing["reportDate"]
        and row.get("dimensions") == [[policy["location_axis"], "typed"]]
    )
    location.pop("typed_dimensions")
    with pytest.raises(ValueError, match="typed current/noncurrent"):
        select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")

    structural, filing = _source("PFE")
    policy = ordinary_nci_acquisition_claim_policy("PFE")
    duplicate = deepcopy(next(
        row for row in structural["facts"]
        if row.get("qname") == policy["component_qnames"][0]
        and row.get("period_end") == filing["reportDate"]
        and not row.get("dimensions")
    ))
    duplicate["value"] += 1
    structural["facts"].append(duplicate)
    with pytest.raises(ValueError, match="presentations do not reconcile"):
        select_acquisition_claim(policy, structural, filing, policy["cik"], "2026-08-14")


def test_wg18_reclassification_preserves_glw_and_pfe_but_removes_mdt_double_deduction():
    expected = {
        "GLW": (567_000_000, 156_000_000, {"low": 0.0, "base": 0.0, "high": 0.0}),
        "MDT": (609_000_000, 163_000_000, {
            "low": 0.15526744817949023,
            "base": 0.1557544338059813,
            "high": 0.1562444838373267,
        }),
        "PFE": (302_000_000, 2_259_000_000, {"low": 0.0, "base": 0.0, "high": 0.0}),
    }
    for ticker, (nci, acquisition, change) in expected.items():
        recipe = json.loads((ROOT / f"output/us-refresh-runtime/recipes/{ticker}.json").read_bytes())
        old = evaluate_recipe(recipe)["range"]
        corrected = deepcopy(recipe)
        for scenario in corrected["scenarios"].values():
            scenario["inputs"]["preferred_equity"] = 0.0
            scenario["inputs"]["noncontrolling_interests"] = nci
            scenario["inputs"]["nonoperating_adjustment"] = -acquisition
        new = evaluate_recipe(corrected)["range"]
        assert {key: new[key] - old[key] for key in ("low", "base", "high")} == change


def test_wg18_compiler_maps_all_three_without_claim_scope_gap():
    runtime = ROOT / "output/us-refresh-runtime"
    registry = {row["ticker"]: row for row in json.loads((runtime / "registry.json").read_bytes())["entries"]}
    for ticker in ("GLW", "MDT", "PFE"):
        recipe = json.loads((runtime / "recipes" / f"{ticker}.json").read_bytes())
        artifact = json.loads((runtime / "baseline/artifacts" / f"{ticker}.json").read_bytes())
        compiled = _policy_for_entry(
            registry[ticker], artifact=artifact, recipe=recipe,
            source_evidence=None, concept_config=load_concept_config(),
        )
        assert "baseline_non_debt_claim_scope_requires_source_rule" not in compiled.reason_codes
