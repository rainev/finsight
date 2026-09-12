from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_31 import BATCH_31_MANIFEST, BATCH_31_TICKERS
from app.us_valuation.batch_31_history import PASS_TICKERS, CONDITIONAL_TICKERS, WITHHELD_TICKERS, build_batch_31_history_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-31-sec-source-packets-20260902"
STRUCTURAL = ROOT / "output/batch-31-structural-sources-20260902"


def result(ticker):
    return build_batch_31_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL)


def test_outcomes_ranges_and_denominator():
    rows = {ticker: result(ticker) for ticker in BATCH_31_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS) == {"CDW", "VRSK"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == {"PANW", "WDAY", "NOW", "SMCI", "NXPI", "ACN", "CRWD"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "not_available"} == set(WITHHELD_TICKERS) == {"ORCL"}
    assert len(rows) == 10
    for ticker, row in rows.items():
        values = row["scenario_range"]
        if ticker == "ORCL":
            assert values == {"low": None, "base": None, "high": None}
        else:
            assert 0 <= values["low"] <= values["base"] <= values["high"] and values["base"] > 0


def test_exact_controlled_ranges_do_not_drift():
    expected = {
        "PANW": (61.670314579633654, 104.21583953299654, 162.0599718888208),
        "WDAY": (122.21505719490514, 204.528324547263, 331.00582370858416),
        "NOW": (53.74677438270102, 90.98468981004262, 145.7672752376119),
        "SMCI": (0., 9.689932758751715, 57.413215066823575),
        "CDW": (35.30430240259429, 111.36467211210919, 191.7801963283429),
        "NXPI": (50.76396511044564, 90.65982715167796, 168.1073928353864),
        "VRSK": (56.443028729871756, 116.47350817675893, 195.3676822369288),
        "ACN": (186.25721921060943, 316.62860227154255, 492.42899578532194),
        "CRWD": (88.62513654578682, 156.55129256762933, 252.3702679976996),
    }
    for ticker, values in expected.items():
        scenario = result(ticker)["scenario_range"]
        assert (scenario["low"], scenario["base"], scenario["high"]) == pytest.approx(values)
    assert result("ORCL")["scenario_range"] == {"low": None, "base": None, "high": None}


def test_controlling_accessions_and_periods():
    expected = {
        "PANW": ("0001327567-26-000015", "2026-04-30"),
        "WDAY": ("0001327811-26-000026", "2026-04-30"),
        "ORCL": ("0001193125-26-277521", "2026-05-31"),
        "NOW": ("0001373715-26-000076", "2026-06-30"),
        "SMCI": ("0001375365-26-000014", "2026-03-31"),
        "CDW": ("0001402057-26-000065", "2026-06-30"),
        "NXPI": ("0001413447-26-000045", "2026-06-28"),
        "VRSK": ("0001437749-26-024749", "2026-06-30"),
        "ACN": ("0001467373-26-000032", "2026-05-31"),
        "CRWD": ("0001535527-26-000025", "2026-04-30"),
    }
    for ticker, (accession, period) in expected.items():
        filing = result(ticker)["source_ledger"]["controlling_filing"]
        assert (filing["accession"], filing["period_end"]) == (accession, period)
        assert filing["filed"] <= "2026-08-14"


def test_source_lineage_and_special_treatments():
    nxpi = result("NXPI")
    assert all(flow["period_end"] == "2026-06-28" for flow in nxpi["source_ledger"]["flow_sources"].values())
    assert nxpi["source_ledger"]["flow_sources"]["revenue"]["method"] == "latest_fy_plus_structural_current_ytd_minus_prior_ytd"
    assert nxpi["source_ledger"]["bridge_reconciliation"]["other_equity_claims"] == 1_562_000_000.
    vrsk = result("VRSK")
    assert all(flow["period_end"] == "2026-06-30" for flow in vrsk["source_ledger"]["flow_sources"].values())
    assert vrsk["source_ledger"]["flow_sources"]["revenue"]["method"] == "latest_fy_plus_structural_current_ytd_minus_prior_ytd"
    smci = result("SMCI")
    assert smci["governed_assumptions"]["cash_conversion_margin"] == (.005, .025, .07)
    assert smci["reported_inputs"]["ttm_cash_fcff"] < 0
    orcl = result("ORCL")
    assert orcl["availability_type"] == "not_available"
    assert orcl["source_ledger"]["model_gap"]["zero_substitution"] is False
    assert "not-yet-commenced lease start and duration" in orcl["source_ledger"]["model_gap"]["missing_bounded_schedules"]


def test_commitment_and_sbc_controls():
    assert result("PANW")["governed_assumptions"]["commitment_coverage"]["reported_total"] == 8_529_000_000.
    assert result("SMCI")["governed_assumptions"]["commitment_coverage"]["reported_total"] == 10_100_000_000.
    assert result("NOW")["governed_assumptions"]["commitment_coverage"]["reported_cloud_and_it_schedule_total"] == 6_302_000_000.
    assert result("CRWD")["governed_assumptions"]["commitment_coverage"]["reported_total"] == 2_722_459_000.
    assert result("WDAY")["governed_assumptions"]["stock_compensation_treatment"]["reported_current_stock_compensation"] == 409_000_000.
    assert result("ACN")["governed_assumptions"]["stock_compensation_treatment"]["reported_current_stock_compensation"] == 1_644_518_000.
    assert result("PANW")["governed_assumptions"]["investment_coverage"]["excluded_residual"] == 328_000_000.
    assert result("SMCI")["governed_assumptions"]["debt_scope_diagnostic"]["convertible_note_caption"] == 4_659_357_000.
    assert result("CDW")["source_ledger"]["flow_sources"]["interest_expense"]["sources"][0]["concept"] == "InterestPaidNet"
    assert result("CDW")["governed_assumptions"]["interest_basis"]["ttm_value"] == 230_800_000.


def test_share_units_and_dcf_replay():
    from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
    for ticker in BATCH_31_TICKERS:
        row = result(ticker)
        assert len([item for item in row["source_ledger"]["bridge_sources"] if item.get("unit") in {"shares", "xbrli:shares"}]) >= 2
        for scenario in row["scenario_rows"]:
            state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0., scenario["other_equity_claims"], scenario["shares"])
            replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
            assert float(replay["intrinsic_value_per_share"]) == pytest.approx(scenario["raw_value_per_share"])


def test_public_and_calculator_safety():
    from run_batch_31_history import _public
    for issuer in BATCH_31_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        raw = json.dumps(public)
        assert "source_ledger" not in raw and "reported_inputs" not in raw and "model_trace" not in raw and "model_gap" not in raw
        view = calculator_view(public)
        assert view["can_calculate"] == (issuer.ticker != "ORCL")
        if view["can_calculate"]:
            assert view["model_family"] == "operating"
            assert calculate(public, overrides={}, manual_price=None)["result"] == private["scenario_range"]


def test_runner_preserves_protected_and_bookkeeping(tmp_path):
    from run_batch_31_history import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, output_root=tmp_path / "candidate")
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (2, 7, 1, 9)
    assert report["withheld_tickers"] == ["ORCL"]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]


def test_arelle_outside_serving_process():
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
