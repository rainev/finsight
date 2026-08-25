import json
from pathlib import Path
import sys

import pytest

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_02_conditional_estimates import (
    COMMON_WARNING,
    CONDITIONAL_TICKERS,
    build_conditional_estimates,
    five_year_fcff_dcf,
    multiple_equity_value,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_batch_02_conditional_estimates import _conditional_public


def test_exact_six_conditional_values_are_finite_ordered_and_low() -> None:
    results = build_conditional_estimates()
    assert tuple(results) == CONDITIONAL_TICKERS
    expected = {
        "OMC": (40.52672670947796, 70.01240523776706, 100.97236769247061),
        "TTWO": (12.325304572579865, 79.69468560435286, 193.17795711929082),
        "CHTR": (0.0, 0.0, 246.27531646327975),
        "CMCSA": (1.3213582473062397, 28.73961001144733, 55.781326316322165),
        "META": (164.50742673562138, 411.98800467653933, 710.2490698199643),
        "WBD": (0.0, 0.3187229936930318, 14.703888165106772),
    }
    for ticker, result in results.items():
        values = result["scenario_range"]
        assert 0 <= values["low"] <= values["base"] <= values["high"]
        assert values["base"] > 0 or (ticker == "CHTR" and values["high"] > 0)
        assert result["reliability"] == "Low"
        assert result["model"] == "conditional_estimate"
        assert result["source"]["filed_date"] <= "2026-08-14"
        assert result["input_source_ledger"]
        assert "assumption_governance" in result["governed_assumptions"]
        assert result["reason_codes"] == [
            "CONDITIONAL_EVENT_MODEL",
            "SPECIALIST_MODEL_UNCERTAINTY",
        ]
        assert tuple(values.values()) == pytest.approx(expected[ticker])


def test_missing_values_are_not_zero_and_equity_floors_are_explicit() -> None:
    results = build_conditional_estimates()
    for ticker in ("CHTR", "WBD"):
        low = results[ticker]["scenario_rows"][0]
        assert low["value_per_share"] == 0.0
        assert "limited_liability_floor" in low["basis"]
    for result in results.values():
        assert all(value is not None for value in result["reported_inputs"].values())


def test_cash_margin_multiple_and_dcf_directions_are_economic() -> None:
    common = dict(
        revenue=10_000.0,
        cash_and_investments=1_000.0,
        debt=2_000.0,
        other_claims=100.0,
        shares=100.0,
    )
    low = multiple_equity_value(cash_margin=0.10, multiple=10.0, **common)
    high_margin = multiple_equity_value(cash_margin=0.20, multiple=10.0, **common)
    high_claim = multiple_equity_value(cash_margin=0.10, multiple=10.0, **{**common, "other_claims": 500.0})
    assert high_margin["value_per_share"] > low["value_per_share"]
    assert high_claim["value_per_share"] < low["value_per_share"]

    dcf = dict(
        revenue=10_000.0, fcff_margin=0.20, growth=0.02,
        terminal_growth=0.01, cash_and_investments=1_000.0,
        debt=2_000.0, noncontrolling_interests=100.0, shares=100.0,
    )
    lower_rate = five_year_fcff_dcf(wacc=0.08, **dcf)
    higher_rate = five_year_fcff_dcf(wacc=0.10, **dcf)
    assert higher_rate["value_per_share"] < lower_rate["value_per_share"]


def test_wbd_contract_is_separate_and_never_probability_weighted() -> None:
    wbd = build_conditional_estimates()["WBD"]
    assumptions = wbd["governed_assumptions"]
    assert assumptions["merger_consideration_is_intrinsic_value"] is False
    assert assumptions["probability_weighted"] is False
    assert assumptions["contract_cash_if_closed_by_2026_09_30"] == 31.0
    assert assumptions["contract_calendar_illustration_2027_06_04"] == pytest.approx(31.68611166)


def test_conditional_public_surface_is_low_warned_and_private_safe() -> None:
    prior = json.loads(
        (Path("output/batch-02-revision-retry/verified-run-a/staged-public/OMC.json")).read_text()
    )
    result = build_conditional_estimates()["OMC"]
    public = _conditional_public(prior, result)
    assert sanitize_public_artifact(public) == public
    assert public["model_policy"]["primary"] == "conditional_estimate"
    assert public["review"]["publication_state"] == "review_required"
    assert public["reliability"]["label"] == "Low"
    assert COMMON_WARNING in public["review"]["warnings"]
    model = public["models"]["conditional_estimate"]
    assert "intrinsic_value_per_share" not in model
    assert model["conditional_value_per_share"] == pytest.approx(
        result["scenario_range"]["base"]
    )
    serialized = json.dumps(public)
    assert "reported_inputs" not in serialized
    assert "governed_assumptions" not in serialized
    assert "scenario_rows" not in serialized


def test_chtr_and_wbd_keep_standalone_ranges_coherent_and_contract_separate() -> None:
    results = build_conditional_estimates()
    chtr = results["CHTR"]
    assert [row["name"] for row in chtr["scenario_rows"]] == [
        "standalone_bear",
        "standalone_base",
        "standalone_bull",
    ]
    assert chtr["scenario_range"]["base"] == 0.0
    assert "transaction_overlay_diagnostic_only" not in chtr["governed_assumptions"]
    assert chtr["governed_assumptions"]["current_h1_cash_after_capex_margin"] == pytest.approx(
        (8.229 - 5.726) / 27.123
    )

    prior = json.loads(
        Path("output/batch-02-revision-retry/verified-run-a/staged-public/WBD.json").read_text()
    )
    wbd = results["WBD"]
    public = _conditional_public(prior, wbd)
    assert public["scenario_range"]["high"] == pytest.approx(14.703888165106772)
    contract = public["contractual_consideration"]
    assert contract["amount_per_share"] == 31.0
    assert contract["illustration_amount_per_share"] == pytest.approx(31.68611166)
    assert "not_intrinsic_value" in contract["status"]
    assert wbd["input_source_ledger"]["contractual_consideration"]["as_of_date"] == "2026-02-27"


def test_fact_level_source_periods_are_not_overstated() -> None:
    results = build_conditional_estimates()
    omc_shares = results["OMC"]["input_source_ledger"]["h1_diluted_weighted_shares"]
    assert (omc_shares["period_start"], omc_shares["period_end"]) == (
        "2026-01-01",
        "2026-06-30",
    )
    ttwo_shares = results["TTWO"]["input_source_ledger"]["common_shares_outstanding"]
    assert ttwo_shares["as_of_date"] == "2026-07-27"


def test_conditional_value_is_scrubbed_if_public_review_fails_closed() -> None:
    prior = json.loads(
        Path("output/batch-02-revision-retry/verified-run-a/staged-public/OMC.json").read_text()
    )
    public = _conditional_public(prior, build_conditional_estimates()["OMC"])
    public["review"]["publication_state"] = "withheld"
    scrubbed = sanitize_public_artifact(public)
    model = scrubbed["models"]["conditional_estimate"]
    assert model["publication_state"] == "withheld"
    assert model["conditional_value_per_share"] is None
