import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_bindings import EconomicException, AcquisitionIncomplete, bind_current_recipe


PACKET_ROOT = Path("output/batch-32-sec-source-packets-20260903/SNDK")
REFRESH_CUTOFF = "2026-08-20"


def test_real_filing_selection_does_not_require_a_particular_cash_tag():
    from app.us_valuation.refresh_bindings import _required_statement_fields, _select_complete_filings
    root = Path('output/us-refresh-runtime')
    packet = json.loads((root/'acquisitions/506c1ecff5edd36238a72e9a6ebe30be11e2679946d4c9342e329b811cd466bc/packets/CSX.json').read_text())['packet']
    policy = json.loads((root/'refresh-policies.json').read_text())['CSX']
    recent = packet['submissions']['filings']['recent']
    records = [{key:values[index] for key,values in recent.items() if isinstance(values,list) and index<len(values)} for index in range(len(recent['accessionNumber']))]
    required = _required_statement_fields(policy,policy['concept_config'])
    assert required == {'revenue':'flow','total_assets':'instant'}
    controlling, annual = _select_complete_filings(records,packet['companyfacts'],packet['structural_filing'],
        cutoff='2026-08-14',required_fields=required,concept_config=policy['concept_config'],
        structural_packets=packet['structural_packets'])
    assert controlling['accessionNumber'] == '0000277948-26-000032'
    assert annual['form'] in {'10-K','10-K/A'}
    # This test establishes filing selection only, never cash bridge validity.


def _packet() -> dict:
    return {
        "submissions": json.loads((PACKET_ROOT / "submissions.json").read_text()),
        "companyfacts": json.loads((PACKET_ROOT / "companyfacts.json").read_text()),
    }


def _packet_with_structural() -> dict:
    packet = _packet()
    structural_path = Path("output/batch-32-structural-sources-20260903/SNDK/structural-filing.json")
    packet["structural_filing"] = json.loads(structural_path.read_text())
    return packet


def _recipe() -> dict:
    scenarios = {
        name: {
            "engine": "enterprise_cash_fcff",
            "inputs": {
                "cash_fcff": 100.0,
                "initial_growth": 0.02,
                "terminal_growth": 0.01,
                "wacc": 0.10,
                "cash_and_investments": 1.0,
                "interest_bearing_debt": 1.0,
                "preferred_equity": 0.0,
                "noncontrolling_interests": 0.0,
                "diluted_shares": 10.0,
                "forecast_years": 8,
            },
        }
        for name in ("bear", "base", "bull")
    }
    return {
        "schema_version": "FINSIGHT-CALCULATION-RECIPE-1",
        "ticker": "SNDK",
        "recipe_version": "test-refresh",
        "evidence_cutoff": "2026-07-29",
        "scenarios": scenarios,
        "editable": {},
    }


def _policy() -> dict:
    return {
        "version": "test-policy-1",
        "supported_engine": "enterprise_cash_fcff",
        "routine_8k_items": ["2.02", "8.01", "9.01"],
        "inputs": {
            "operating_cash_flow": {"field": "operating_cash_flow", "selector": "ttm"},
            "capex": {"field": "capital_expenditures", "selector": "total_capex"},
            "interest": {"field": "interest_expense", "selector": "ttm"},
            "tax_rate": {"field": "tax_rate", "selector": "tax_rate"},
            "cash": {"field": "cash", "selector": "instant"},
            "shares": {"field": "common_shares_outstanding", "selector": "instant"},
            "history_revenue": {"field": "revenue", "selector": "history_median"},
        },
        "scenario_bindings": {
            name: {
                "cash_fcff": {
                    "subtract": [
                        {"add": ["operating_cash_flow", {"multiply": ["interest", {"subtract": [1.0, "tax_rate"]}]}]},
                        "capex",
                    ]
                },
                "cash_and_investments": "cash",
                "diluted_shares": "shares",
            }
            for name in ("bear", "base", "bull")
        },
    }


def test_cached_real_sndk_successor_packet_binds_cash_fcff_history_and_enterprise_recipe() -> None:
    bound, ledger = bind_current_recipe(
        {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": _policy()},
        _recipe(),
        _packet(),
        REFRESH_CUTOFF,
    )

    assert bound["source_accession"] == "0001628280-26-057406"
    assert ledger["period_end"] == "2026-07-03"
    assert ledger["sources"]["operating_cash_flow"]["source"]["cik"] == "0002023554"
    assert ledger["sources"]["operating_cash_flow"]["source"]["period_end"] <= REFRESH_CUTOFF
    assert ledger["sources"]["capex"]["resolution"]["basis"] == "reported_total_capex"
    assert len(ledger["sources"]["history_revenue"]["selected"]) >= 3
    assert all(row["end"] <= REFRESH_CUTOFF for row in ledger["sources"]["history_revenue"]["selected"])
    expected_cash_fcff = ledger["values"]["operating_cash_flow"] - ledger["values"]["capex"] + ledger["values"]["interest"] * (1.0 - ledger["values"]["tax_rate"])
    assert bound["scenarios"]["base"]["inputs"]["cash_fcff"] == pytest.approx(expected_cash_fcff)


def test_same_issuer_cutoffs_select_prior_then_successor_complete_filings() -> None:
    prior, prior_ledger = bind_current_recipe(
        {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": _policy()},
        _recipe(),
        _packet(),
        "2026-07-30",
    )
    later, later_ledger = bind_current_recipe(
        {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": _policy()},
        _recipe(),
        _packet(),
        "2026-08-20",
    )
    assert prior_ledger["controlling_filing"]["accessionNumber"] == "0001628280-26-029401"
    assert later_ledger["controlling_filing"]["accessionNumber"] == "0001628280-26-057406"
    assert prior["source_accession"] != later["source_accession"]
    assert prior_ledger["period_end"] != later_ledger["period_end"]


def test_normalized_selector_keeps_reported_value_and_source_backed_adjustment() -> None:
    policy = _policy()
    policy["inputs"] = {
        "normalized_cash": {
            "field": "cash_fcff",
            "selector": "normalized",
            "base": {"field": "revenue", "selector": "ttm"},
            "adjustments": [
                {"name": "reported_capex", "field": "capital_expenditures", "selector": "ttm", "sign": -1},
            ],
        }
    }
    policy["scenario_bindings"] = {
        name: {"cash_fcff": "normalized_cash"}
        for name in ("bear", "base", "bull")
    }
    _, ledger = bind_current_recipe(
        {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": policy},
        _recipe(),
        _packet(),
        REFRESH_CUTOFF,
    )
    normalized = ledger["sources"]["normalized_cash"]
    assert normalized["reported_preserved"] is True
    assert normalized["adjustment_total"] < 0
    assert normalized["normalized_value"] == pytest.approx(
        normalized["reported_value"] + normalized["adjustment_total"]
    )


def test_frozen_cutoff_and_unapproved_events_fail_closed() -> None:
    with pytest.raises(EconomicException, match="evidence cutoff"):
        bind_current_recipe(
            {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": _policy()},
            _recipe(),
            _packet(),
            "2026-07-20",
        )

    packet = _packet()
    recent = packet["submissions"]["filings"]["recent"]
    for key, value in (
        ("accessionNumber", "0002023554-26-000099"),
        ("filingDate", "2026-07-30"),
        ("reportDate", "2026-07-25"),
        ("form", "8-K"),
        ("items", "1.01"),
        ("primaryDocument", "event.htm"),
    ):
        recent.setdefault(key, []).append(value)
    packet["companyfacts"]["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"].append(
        {
            "val": 1000000,
            "end": "2026-07-03",
            "filed": "2026-07-29",
            "accn": "0002023554-26-099999",
            "form": "10-Q/A",
        }
    )
    with pytest.raises(EconomicException, match="corporate-event filing"):
        bind_current_recipe(
            {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": _policy()},
            _recipe(),
            packet,
            REFRESH_CUTOFF,
        )


def test_declared_non_enterprise_recipe_is_rejected_by_enterprise_binding() -> None:
    recipe = _recipe()
    recipe["scenarios"]["bull"]["engine"] = "residual_income"
    with pytest.raises(RuntimeError, match="supported declared recipe engine"):
        bind_current_recipe(
            {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": _policy()},
            recipe,
            _packet(),
            REFRESH_CUTOFF,
        )


def test_optional_structural_packet_is_accession_and_period_bound() -> None:
    policy = _policy()
    policy["inputs"] = {"cash": {"field": "us-gaap:CashAndCashEquivalentsAtCarryingValue", "selector": "structural", "expected_unit": "USD", "period_kind": "instant"}}
    policy["scenario_bindings"] = {
        name: {"cash_and_investments": "cash"}
        for name in ("bear", "base", "bull")
    }
    bound, ledger = bind_current_recipe(
        {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": policy},
        _recipe(),
        _packet_with_structural(),
        "2026-07-30",
    )
    assert ledger["sources"]["cash"]["selected"]["source_kind"] == "structural_xbrl"
    assert bound["scenarios"]["base"]["inputs"]["cash_and_investments"] == 3_735_000_000

    missing_contract = _policy()
    missing_contract["inputs"] = {"cash": {"field": "us-gaap:CashAndCashEquivalentsAtCarryingValue", "selector": "structural"}}
    missing_contract["scenario_bindings"] = {name: {"cash_and_investments": "cash"} for name in ("bear", "base", "bull")}
    with pytest.raises(EconomicException, match="expected unit"):
        bind_current_recipe(
            {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": missing_contract},
            _recipe(),
            _packet_with_structural(),
            "2026-07-30",
        )

    mismatched = _packet_with_structural()
    mismatched["structural_filing"]["source_accession"] = "0001628280-26-999999"
    # A corrupted/wrong filing packet is acquisition failure, not new economic
    # invalidity. The job must retain the previous dated estimate in this case.
    with pytest.raises(AcquisitionIncomplete, match="structural packet accession"):
        bind_current_recipe(
            {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": policy},
            _recipe(),
            mismatched,
            "2026-07-30",
        )

    wrong_entity = _packet_with_structural()
    wrong_entity["structural_filing"]["facts"] = [
        {**wrong_entity["structural_filing"]["facts"][0], "qname": "us-gaap:CashAndCashEquivalentsAtCarryingValue", "local_name": "CashAndCashEquivalentsAtCarryingValue", "value": 3_735_000_000, "period_end": "2026-04-03", "unit": "USD", "dimensions": [], "entity_identifier": "0000000002"}
    ]
    with pytest.raises(EconomicException, match="entity identifier"):
        bind_current_recipe(
            {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": policy},
            _recipe(),
            wrong_entity,
            "2026-07-30",
        )


def test_metadata_only_amendment_does_not_replace_complete_current_filing() -> None:
    packet = _packet()
    recent = packet["submissions"]["filings"]["recent"]
    for key, value in (
        ("accessionNumber", "0002023554-26-099999"),
        ("filingDate", "2026-07-29"),
        ("reportDate", "2026-07-03"),
        ("form", "10-Q/A"),
        ("items", ""),
        ("primaryDocument", "cover-only-amendment.htm"),
    ):
        recent.setdefault(key, []).append(value)
    _, ledger = bind_current_recipe(
        {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": _policy()},
        _recipe(),
        packet,
        "2026-07-30",
    )
    assert ledger["controlling_filing"]["accessionNumber"] == "0001628280-26-029401"

    missing = _packet()
    recent = missing["submissions"]["filings"]["recent"]
    for key, value in (
        ("accessionNumber", "0002023554-26-099998"),
        ("filingDate", "2026-07-30"),
        ("reportDate", "2026-07-03"),
        ("form", "10-Q"),
        ("items", ""),
        ("primaryDocument", "missing-source.htm"),
    ):
        recent.setdefault(key, []).append(value)
    with pytest.raises(AcquisitionIncomplete, match="latest eligible regular filing"):
        bind_current_recipe(
            {"ticker": "SNDK", "cik": "0002023554", "refresh_policy": _policy()},
            _recipe(),
            missing,
            "2026-07-30",
        )
