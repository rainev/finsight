from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace

import pytest

from app.us_valuation.batch_02_practical_inputs import (
    BridgeInputs,
    CashFcffInputs,
    _complete_extraction_zero,
    _structural_value,
    cash_fcff_from_reported,
)
from app.us_valuation.batch_02_practical_models import build_cash_fcff_result
from app.us_valuation.xbrl import load_concept_config

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_batch_02_controlled import (
    _cutoff_submissions,
    _force_withheld,
    _numeric_public,
    _validate_roots,
)


def _inputs(ticker: str = "VZ") -> CashFcffInputs:
    return CashFcffInputs(
        ticker=ticker,
        accession="0000732712-26-000046",
        filing_date="2026-07-31",
        form="10-Q",
        primary_document="vz-20260630.htm",
        period_end="2026-06-30",
        source_url=(
            "https://www.sec.gov/Archives/edgar/data/732712/"
            "000073271226000046/vz-20260630.htm"
        ),
        ttm_revenue=20_000.0,
        ttm_operating_cash_flow=4_000.0,
        ttm_capex=1_000.0,
        ttm_spectrum_investment=100.0,
        ttm_interest_expense=300.0,
        normalized_tax_rate=0.21,
        reported_cash_fcff=3_137.0,
        one_time_cash_adjustment=0.0,
        normalized_cash_fcff=3_137.0,
        annual_cash_fcff=(2_200.0, 2_400.0, 2_600.0, 2_900.0, 3_100.0),
        annual_revenue=(15_000.0, 16_000.0, 17_000.0, 18_000.0, 19_000.0),
        bridge=BridgeInputs(
            cash_and_investments=2_000.0,
            interest_bearing_debt=3_000.0,
            preferred_equity=0.0,
            noncontrolling_interests=100.0,
            diluted_shares=1_000.0,
            nonoperating_range=(0.0, 0.0, 0.0),
            sources=({"source_kind": "test"},),
        ),
        flow_sources=({"source_kind": "test"},),
        specialist_context={"scope_adjustment_range": (0.0, 0.0, 0.0)},
    )


def _classification() -> dict:
    return {
        "cik": "0000732712",
        "ticker": "VZ",
        "issuer_name": "Verizon",
        "filing_regime": "10-K_10-Q",
        "accounting_standard": "US-GAAP",
        "sec_sic_code": "4813",
        "sec_sic_label": "Telephone Communications",
        "finsight_sector": "Communication Services",
        "primary_archetype": "telecom",
        "secondary_archetypes": [],
        "classification_confidence": 0.85,
        "mapping_version": "US-ARCHETYPE-1.0",
        "classification_reason": "Test classification.",
        "override_applied": False,
        "source_accessions": ["0000732712-26-000046"],
    }


def test_numeric_result_survives_public_safety_and_withheld_scrubs_every_value() -> None:
    inputs = _inputs()
    practical, outcome = build_cash_fcff_result(inputs)
    public = _numeric_public(
        issuer=SimpleNamespace(ticker="VZ"),
        classification=_classification(),
        result=practical,
    )

    assert outcome.is_numeric
    assert public["review"]["publication_state"] == "review_required"
    assert public["reliability"]["label"] == "Low"
    assert public["scenario_range"] == practical["scenario_range"]
    assert "input_provenance" not in public
    assert "practical_policy" not in public
    assert practical["input_provenance"]["flows"] == inputs.flow_sources

    withheld = _force_withheld(
        public,
        source_statement=practical["source_financial_statement"],
        model="transaction_adjusted_fcff",
        blockers=("MAJOR_EVENT_UNBOUNDED",),
    )
    assert withheld["review"]["publication_state"] == "withheld"
    assert all(
        withheld["scenario_range"][key] is None
        for key in ("low", "base", "high")
    )
    assert all(
        model["intrinsic_value_per_share"] is None
        for model in withheld["models"].values()
    )


def test_netflix_numeric_requires_bear_cash_to_cover_content_growth() -> None:
    inputs = replace(
        _inputs("NFLX"),
        one_time_cash_adjustment=100.0,
        specialist_context={
            "scope_adjustment_range": (0.0, 0.0, 0.0),
            "content_commitments": {
                "h1_additions_increase": 100_000.0,
            },
        },
    )
    with pytest.raises(ValueError, match="does not bound"):
        build_cash_fcff_result(inputs)


def test_structural_source_zero_and_member_selection_fail_closed() -> None:
    structural = {
        "source_accession": "0000000000-26-000001",
        "facts": [
            {
                "local_name": "LongTermDebt",
                "period_start": None,
                "period_end": "2026-06-30",
                "value": 84_621.0,
                "qname": "us-gaap:LongTermDebt",
                "unit": "USD",
                "context_id": "c-1",
                "dimensions": [["axis", "issuer:TotalDebtMember"]],
            }
        ],
    }
    debt, _ = _structural_value(
        structural,
        local_name="LongTermDebt",
        period_end="2026-06-30",
        member="TotalDebtMember",
    )
    assert debt == 84_621.0
    zero, source = _complete_extraction_zero(
        structural,
        period_end="2026-06-30",
        field="preferred equity",
        name_fragments=("PreferredStockValue",),
    )
    assert zero == 0.0
    assert source["source_kind"] == "structural_complete_extraction"

    structural["facts"].append(
        {
            "local_name": "PreferredStockValue",
            "period_start": None,
            "period_end": "2026-06-30",
            "value": 1.0,
        }
    )
    with pytest.raises(ValueError, match="not source-proven zero"):
        _complete_extraction_zero(
            structural,
            period_end="2026-06-30",
            field="preferred equity",
            name_fragments=("PreferredStockValue",),
        )


def test_shared_aliases_cover_cash_fcff_and_verizon_capex() -> None:
    fields = load_concept_config()["fields"]
    assert "operating_cash_flow" in fields
    assert "interest_expense" in fields
    assert "intangible_asset_purchases" in fields
    assert (
        "PaymentsToAcquireOtherProductiveAssets"
        in fields["capital_expenditures"]["concepts"]
    )
    assert "OtherReceivablesNetCurrent" in fields["accounts_receivable"]["concepts"]


def test_reported_cash_fcff_subtracts_spectrum_dollar_for_dollar() -> None:
    without_spectrum = cash_fcff_from_reported(
        operating_cash_flow=10_000.0,
        capital_expenditures=3_000.0,
        spectrum_investment=0.0,
        interest_expense=1_000.0,
        tax_rate=0.20,
    )
    with_spectrum = cash_fcff_from_reported(
        operating_cash_flow=10_000.0,
        capital_expenditures=3_000.0,
        spectrum_investment=750.0,
        interest_expense=1_000.0,
        tax_rate=0.20,
    )
    assert without_spectrum - with_spectrum == 750.0


def test_classification_input_excludes_every_post_cutoff_filing() -> None:
    submissions = {
        "filings": {
            "recent": {
                "accessionNumber": ["before", "after"],
                "filingDate": ["2026-08-14", "2026-08-15"],
                "form": ["10-Q", "10-Q"],
                "primaryDocument": ["before.htm", "after.htm"],
            }
        }
    }
    cutoff = _cutoff_submissions(submissions)
    assert cutoff["filings"]["recent"] == {
        "accessionNumber": ["before"],
        "filingDate": ["2026-08-14"],
        "form": ["10-Q"],
        "primaryDocument": ["before.htm"],
    }


def test_runner_rejects_serving_output_root(tmp_path: Path) -> None:
    source = tmp_path / "sources"
    structural = tmp_path / "structural"
    source.mkdir()
    structural.mkdir()
    with pytest.raises(ValueError, match="serving"):
        _validate_roots(
            source,
            structural,
            Path("backend/app/data/us_valuation_catalogs"),
        )
