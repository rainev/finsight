from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from app.us_valuation.bridge_policy import BridgeRange, BridgeResolution
from app.us_valuation.refresh_reported_claim_scope import (
    ClaimScopeReviewRequired,
    REPORTED_NCI_SCOPE_RULES,
    reported_nci_field_availability,
    validate_reported_nci_scope,
)


ROOT = Path(__file__).resolve().parents[2]


def _source(ticker: str, qnames: tuple[str, ...]) -> tuple[dict, str, str]:
    recipe = json.loads((ROOT / "output/us-refresh-runtime/recipes" / f"{ticker}.json").read_text())
    private = json.loads(Path(recipe["provenance"]["source_path"]).read_text())
    value = private.get("history_backed") or private.get("recovery") or private
    filing = value["source_ledger"]["controlling_filing"]
    accession, period = filing["accession"], filing["period_end"]
    for path in sorted((ROOT / "output").glob(f"**/{ticker}/structural-filing.json")):
        structural = json.loads(path.read_text())
        if structural.get("source_accession") != accession:
            continue
        from app.us_valuation.refresh_source_ingestion import _validate_structural_payload
        structural = _validate_structural_payload(structural, cik=REPORTED_NCI_SCOPE_RULES[ticker].cik,
            filing={'accession':accession,'report_date':period,'form':filing['form']})
        current = {
            row.get("qname")
            for row in structural.get("facts", [])
            if row.get("qname") in qnames
            and row.get("period_end") == period
            and row.get("period_start") is None
            and row.get("unit") == "USD"
        }
        if current >= set(qnames):
            return structural, accession, period
    raise AssertionError(f"no cached structural source for {ticker}")


def _bridge(nci: float) -> BridgeResolution:
    cash = BridgeRange(100.0, 100.0, 100.0)
    debt = BridgeRange(10.0, 10.0, 10.0)
    preferred = BridgeRange(0.0, 0.0, 0.0)
    nci_range = BridgeRange(nci, nci, nci)
    adjustment = BridgeRange(90.0 - nci, 90.0 - nci, 90.0 - nci)
    return BridgeResolution(
        complete=True,
        can_value=True,
        missing_fields=(),
        blocking_fields=(),
        bounded_fields=(),
        cash_and_investments=cash,
        total_debt=debt,
        preferred_equity=preferred,
        noncontrolling_interests=nci_range,
        bridge_adjustment=adjustment,
        fully_diluted_shares=10.0,
        reason_codes=(),
    )


def test_all_remaining_mappings_reconcile_real_current_structural_sources() -> None:
    for ticker, rule in REPORTED_NCI_SCOPE_RULES.items():
        structural, accession, period = _source(ticker, rule.required_qnames)
        total = sum(
            next(
                float(row["value"])
                for row in structural["facts"]
                if row.get("qname") == qname
                and row.get("period_end") == period
                and row.get("period_start") is None
                and row.get("unit") == "USD"
                and row.get("dimensions") in (None, [])
            )
            for qname in rule.required_qnames
        )
        result = validate_reported_nci_scope(
            ticker=ticker,
            structural_packet=structural,
            normalized_bridge=_bridge(total),
            accession=accession,
            period_end=period,
        )
        assert result["status"] == "verified"
        assert result["source_total"] == result["normalized_bridge_nci"]
        assert tuple(result["required_qnames"]) == rule.required_qnames


@pytest.mark.parametrize("ticker,total", [("NUE", 1_157_000_000.0), ("STLD", 143_259_000.0)])
def test_unclassified_nci_group_binds_only_positive_outside_owner_claims(ticker, total):
    from app.us_valuation.refresh_operating_policies import _policy_for_entry
    from app.us_valuation.xbrl import load_concept_config

    root = ROOT / "output/us-refresh-runtime"
    recipe = json.loads((root / "recipes" / f"{ticker}.json").read_text())
    entry = next(
        row for row in json.loads((root / "registry.json").read_text())["entries"]
        if row["ticker"] == ticker
    )
    artifact = json.loads((root / "baseline/artifacts" / f"{ticker}.json").read_text())
    compiled = _policy_for_entry(
        entry,
        artifact=artifact,
        recipe=recipe,
        source_evidence=None,
        concept_config=load_concept_config(),
    )
    assert "baseline_non_debt_claim_scope_requires_source_rule" not in compiled.reason_codes
    rule = REPORTED_NCI_SCOPE_RULES[ticker]
    structural, accession, period = _source(ticker, rule.required_qnames)
    result = validate_reported_nci_scope(
        ticker=ticker,
        structural_packet=structural,
        normalized_bridge=_bridge(total),
        accession=accession,
        period_end=period,
    )
    assert result["source_total"] == total
    if ticker == "STLD":
        assert any(
            row["qname"] == "us-gaap:MinorityInterest" and row["value"] < 0
            for row in result["alias_components"]
        )


def test_stld_negative_nci_is_diagnostic_but_positive_value_fails_closed():
    rule = REPORTED_NCI_SCOPE_RULES["STLD"]
    structural, accession, period = _source("STLD", rule.required_qnames)
    total = next(
        float(row["value"])
        for row in structural["facts"]
        if row.get("qname") == rule.required_qnames[0]
        and row.get("period_end") == period
        and row.get("period_start") is None
        and row.get("dimensions") in (None, [])
    )
    changed = copy.deepcopy(structural)
    row = next(
        item for item in changed["facts"]
        if item.get("qname") == "us-gaap:MinorityInterest"
        and item.get("period_end") == period
        and item.get("period_start") is None
        and item.get("dimensions") in (None, [])
    )
    row["value"] = abs(float(row["value"]))
    with pytest.raises(ClaimScopeReviewRequired, match="became a positive outside-owner claim"):
        validate_reported_nci_scope(
            ticker="STLD",
            structural_packet=changed,
            normalized_bridge=_bridge(total),
            accession=accession,
            period_end=period,
        )


@pytest.mark.parametrize("ticker,total", [("DASH", 11_000_000.0), ("ICE", 101_000_000.0)])
def test_customer_funds_group_keeps_outside_owner_claims_separate(ticker,total):
    rule=REPORTED_NCI_SCOPE_RULES[ticker]
    structural,accession,period=_source(ticker,rule.required_qnames)
    result=validate_reported_nci_scope(
        ticker=ticker,structural_packet=structural,normalized_bridge=_bridge(total),
        accession=accession,period_end=period)
    assert result["source_total"]==total


@pytest.mark.parametrize('ticker,total',[('MAS',247000000),('MSI',16000000),('MCO',141000000)])
def test_new_nci_only_mappings_match_current_sources_not_generic_preferred_claims(ticker,total):
    from app.us_valuation.refresh_operating_policies import _policy_for_entry
    from app.us_valuation.xbrl import load_concept_config
    root=ROOT/'output/us-refresh-runtime'
    recipe=json.loads((root/'recipes'/f'{ticker}.json').read_text())
    entry=next(row for row in json.loads((root/'registry.json').read_text())['entries'] if row['ticker']==ticker)
    artifact=json.loads((root/'baseline/artifacts'/f'{ticker}.json').read_text())
    compiled=_policy_for_entry(entry,artifact=artifact,recipe=recipe,source_evidence=None,concept_config=load_concept_config())
    assert 'baseline_non_debt_claim_scope_requires_source_rule' not in compiled.reason_codes
    assert compiled.policy['history_growth_policy']['verification']['matches_frozen_recipe']
    structural,accession,period=_source(ticker,('us-gaap:MinorityInterest',))
    assert validate_reported_nci_scope(ticker=ticker,structural_packet=structural,normalized_bridge=_bridge(total),accession=accession,period_end=period)['source_total']==total
    assert all(spec['inputs']['preferred_equity']==total for spec in recipe['scenarios'].values())
    assert any(row.get('qname')=='us-gaap:PreferredStockValue' and row.get('period_end')==period and not row.get('dimensions') and row.get('value')==0 for row in structural['facts'])


@pytest.mark.parametrize('ticker,total',[('COHR',334_705_000),('WMB',2_178_000_000)])
def test_preferred_lifecycle_group_keeps_nci_in_its_own_bridge_field(ticker,total):
    rule=REPORTED_NCI_SCOPE_RULES[ticker]
    structural,accession,period=_source(ticker,rule.required_qnames)
    availability,proof=reported_nci_field_availability(
        ticker=ticker,policy=asdict(rule),structural_packet=structural,
        accession=accession,period_end=period)
    assert availability.value==total and proof['source_total']==total
    preferred=[row for row in structural['facts'] if row.get('period_end')==period and row.get('period_start') is None
               and row.get('qname') in {'us-gaap:PreferredStockValue','us-gaap:TemporaryEquityCarryingAmountAttributableToParent'}
               and row.get('dimensions') in (None,[])]
    assert preferred and all(float(row['value'])==(35_000_000 if ticker=='WMB' else 0) for row in preferred)


@pytest.mark.parametrize('ticker,total',[
    ('FTV',8800000),('GEV',1158000000),('HUBB',11100000),('JCI',33000000),('LDOS',52000000),
    ('OTIS',294000000),('PWR',104001000),('ROK',2000000),('VLTO',1000000),('WAB',30000000),('WM',1000000)])
def test_clean_nci_working_group_reclassifies_only_current_reported_nci(ticker,total):
    from app.us_valuation.refresh_operating_policies import _policy_for_entry
    from app.us_valuation.xbrl import load_concept_config
    root=ROOT/'output/us-refresh-runtime';recipe=json.loads((root/'recipes'/f'{ticker}.json').read_text())
    entry=next(row for row in json.loads((root/'registry.json').read_text())['entries'] if row['ticker']==ticker)
    artifact=json.loads((root/'baseline/artifacts'/f'{ticker}.json').read_text())
    compiled=_policy_for_entry(entry,artifact=artifact,recipe=recipe,source_evidence=None,concept_config=load_concept_config())
    assert compiled.reason_codes==()
    assert compiled.policy['history_growth_policy']['verification']['matches_frozen_recipe']
    rule=REPORTED_NCI_SCOPE_RULES[ticker];structural,accession,period=_source(ticker,rule.required_qnames)
    result=validate_reported_nci_scope(ticker=ticker,structural_packet=structural,normalized_bridge=_bridge(total),accession=accession,period_end=period)
    assert result['source_total']==total
    assert all(spec['inputs']['preferred_equity']==total and spec['inputs']['noncontrolling_interests']==0 for spec in recipe['scenarios'].values())


@pytest.mark.parametrize('ticker,total',[('ROK',2000000),('LDOS',52000000)])
def test_reported_nci_is_bound_before_bridge_resolution_from_real_sources(ticker,total):
    from dataclasses import asdict
    rule=REPORTED_NCI_SCOPE_RULES[ticker]
    structural,accession,period=_source(ticker,rule.required_qnames)
    availability,proof=reported_nci_field_availability(
        ticker=ticker,policy=asdict(rule),structural_packet=structural,
        accession=accession,period_end=period)
    assert availability.field=='noncontrolling_interests'
    assert availability.state=='reported'
    assert availability.value==total
    assert availability.source_accession==accession
    assert availability.extraction_complete
    assert proof['status']=='source_bound'
    assert proof['source_total']==total


def test_cmi_current_nci_is_a_balance_and_distribution_flows_are_not_added():
    from dataclasses import asdict
    ticker='CMI';rule=REPORTED_NCI_SCOPE_RULES[ticker]
    structural,accession,period=_source(ticker,rule.required_qnames)
    availability,proof=reported_nci_field_availability(
        ticker=ticker,policy=asdict(rule),structural_packet=structural,
        accession=accession,period_end=period)
    assert availability.value==1_059_000_000
    assert proof['source_total']==1_059_000_000
    assert any(row.get('qname')=='us-gaap:MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders'
               and row.get('period_start') is not None for row in structural['facts'])
    assert all(row['qname']!='us-gaap:MinorityInterestDecreaseFromDistributionsToNoncontrollingInterestHolders'
               for row in proof['components'])


def test_reported_nci_prebridge_binding_rejects_policy_tampering():
    from dataclasses import asdict
    ticker='ROK';rule=REPORTED_NCI_SCOPE_RULES[ticker]
    structural,accession,period=_source(ticker,rule.required_qnames)
    policy=asdict(rule);policy['version']='tampered'
    with pytest.raises(ClaimScopeReviewRequired,match='identity/version mismatch'):
        reported_nci_field_availability(ticker=ticker,policy=policy,
            structural_packet=structural,accession=accession,period_end=period)


def test_missing_required_component_requires_review() -> None:
    rule = REPORTED_NCI_SCOPE_RULES["ACN"]
    structural, accession, period = _source("ACN", rule.required_qnames)
    structural["facts"] = [
        row
        for row in structural["facts"]
        if not (row.get("qname") == "us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount" and row.get("period_end") == period)
    ]
    with pytest.raises(ClaimScopeReviewRequired, match="required current NCI component is missing"):
        validate_reported_nci_scope(
            ticker="ACN",
            structural_packet=structural,
            normalized_bridge=_bridge(1.0),
            accession=accession,
            period_end=period,
        )


def test_unknown_nonzero_component_and_conflict_require_review() -> None:
    rule = REPORTED_NCI_SCOPE_RULES["ACN"]
    structural, accession, period = _source("ACN", rule.required_qnames)
    extra = copy.deepcopy(next(row for row in structural["facts"] if row.get("qname") == rule.required_qnames[0] and row.get("period_end") == period))
    extra["qname"] = "us-gaap:NonredeemableNoncontrollingInterest"
    extra["local_name"] = "NonredeemableNoncontrollingInterest"
    extra["value"] = 1.0
    structural["facts"].append(extra)
    with pytest.raises(ClaimScopeReviewRequired, match="unknown nonzero current NCI component"):
        validate_reported_nci_scope(
            ticker="ACN",
            structural_packet=structural,
            normalized_bridge=_bridge(1.0),
            accession=accession,
            period_end=period,
        )

    structural, accession, period = _source("ACN", rule.required_qnames)
    duplicate = copy.deepcopy(next(row for row in structural["facts"] if row.get("qname") == rule.required_qnames[0] and row.get("period_end") == period))
    duplicate["value"] = float(duplicate["value"]) + 1.0
    structural["facts"].append(duplicate)
    with pytest.raises(ClaimScopeReviewRequired, match="required current NCI component conflicts"):
        validate_reported_nci_scope(
            ticker="ACN",
            structural_packet=structural,
            normalized_bridge=_bridge(1.0),
            accession=accession,
            period_end=period,
        )


def test_bridge_mismatch_and_identity_require_review() -> None:
    rule = REPORTED_NCI_SCOPE_RULES["CPRT"]
    structural, accession, period = _source("CPRT", rule.required_qnames)
    actual = float(next(row["value"] for row in structural["facts"] if row.get("qname") == rule.required_qnames[0] and row.get("period_end") == period))
    with pytest.raises(ClaimScopeReviewRequired, match="does not reconcile"):
        validate_reported_nci_scope(
            ticker="CPRT",
            structural_packet=structural,
            normalized_bridge=_bridge(actual + 1.0),
            accession=accession,
            period_end=period,
        )
    tampered = copy.deepcopy(structural)
    for row in tampered["facts"]:
        if row.get("qname") == rule.required_qnames[0] and row.get("period_end") == period:
            row["entity_identifier"] = "0000000001"
    with pytest.raises(ClaimScopeReviewRequired, match="required current NCI component is missing"):
        validate_reported_nci_scope(
            ticker="CPRT",
            structural_packet=tampered,
            normalized_bridge=_bridge(actual),
            accession=accession,
            period_end=period,
        )
