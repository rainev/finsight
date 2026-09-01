from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_30 import BATCH_30_MANIFEST, BATCH_30_TICKERS
from app.us_valuation.batch_30_history import PASS_TICKERS, CONDITIONAL_TICKERS, WITHHELD_TICKERS, build_batch_30_history_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-30-sec-source-packets-20260901"
STRUCTURAL = ROOT / "output/batch-30-structural-sources-20260901"


def result(ticker):
    return build_batch_30_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL)


def test_outcomes_ranges_and_denominator():
    rows = {ticker: result(ticker) for ticker in BATCH_30_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS) == {"TDY", "BR"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == {"CTSH", "ON", "STX", "FTNT", "FSLR", "MPWR", "PLTR", "TEL"}
    assert not WITHHELD_TICKERS and len(rows) == 10
    for row in rows.values():
        values = row["scenario_range"]
        assert 0 <= values["low"] <= values["base"] <= values["high"] and values["base"] > 0


def test_exact_controlled_ranges_do_not_drift():
    expected = {
        "CTSH": (47.55004760434793, 78.25181585482817, 109.15870682135167),
        "TDY": (179.79305916170807, 360.28128693395945, 558.935254815855),
        "ON": (15.089330824101653, 23.99223837376987, 56.03012138588236),
        "STX": (30.891740785065696, 84.75968225699708, 148.47279777759277),
        "FTNT": (46.01085720339318, 74.34568675013986, 120.649435511681),
        "FSLR": (15.342231571554102, 34.739845658486686, 126.56346927440947),
        "MPWR": (167.160851326484, 325.16374716424195, 634.1852877769275),
        "PLTR": (10.05423833144733, 22.908610911392124, 48.37695521857637),
        "BR": (81.22492195895147, 162.62217620642315, 238.6468446609589),
        "TEL": (74.96148097373354, 153.98270321922726, 264.0389830275486),
    }
    for ticker, values in expected.items():
        scenario = result(ticker)["scenario_range"]
        assert (scenario["low"], scenario["base"], scenario["high"]) == pytest.approx(values)


def test_narrow_lineage_claims_and_commitment_controls():
    ctsh = result("CTSH")
    assert all(flow["period_end"] == "2026-06-30" for flow in ctsh["source_ledger"]["flow_sources"].values())
    assert ctsh["source_ledger"]["flow_sources"]["revenue"]["method"] == "latest_fy_plus_structural_current_ytd_minus_prior_ytd"
    stx = result("STX")
    diagnostic = stx["source_ledger"]["structural_top_level_period_diagnostic"]
    assert diagnostic["used_for_selection"] is False
    assert diagnostic["controlling_report_date"] == "2026-07-03"
    assert diagnostic["selection_basis"] == "Controlling source-receipt report date plus exact fact periods."
    assert stx["source_ledger"]["bridge_reconciliation"]["other_equity_claims"] == (120_000_000.,) * 3
    assert stx["governed_assumptions"]["loss_contingency_treatment"]["source_context_ids"] == ["c-303", "c-304"]
    fslr = result("FSLR")
    assert fslr["governed_assumptions"]["cash_conversion_margin"] == (.005, .03, .10)
    assert fslr["source_ledger"]["bridge_reconciliation"]["other_equity_claims"] == (223_700_000., 198_700_000., 158_700_000.)
    assert result("MPWR")["source_ledger"]["bridge_reconciliation"]["operating_commitment_coverage"]["reported_total"] == 571_036_000.
    assert result("MPWR")["governed_assumptions"]["stock_compensation_treatment"]["reported_h1_stock_compensation"] == 94_282_000.
    assert result("PLTR")["source_ledger"]["bridge_reconciliation"]["operating_commitment_coverage"]["reported_total"] == 5_600_000_000.
    assert result("PLTR")["governed_assumptions"]["stock_compensation_treatment"]["reported_h1_stock_compensation"] == 466_801_000.
    br = result("BR")
    assert br["governed_assumptions"]["operating_commitment_coverage"]["schedule_sum"] == 868_400_000.
    assert br["governed_assumptions"]["operating_commitment_coverage"]["rounding_difference"] == 100_000.
    br_commitments = {item["concept"].split(":")[-1]: item["value"] for item in br["source_ledger"]["event_sources"] if item.get("concept", "").split(":")[-1].startswith("MinimumCommitment")}
    assert br_commitments == {"MinimumCommitmentTotal": 868_500_000., "MinimumCommitmentYearOne": 238_200_000., "MinimumCommitmentYearTwo": 207_100_000., "MinimumCommitmentYearThree": 173_300_000., "MinimumCommitmentYearFour": 132_700_000., "MinimumCommitmentYearFive": 81_600_000., "MinimumCommitmentAfterFifthYear": 35_500_000.}
    for ticker in {"CTSH", "TDY", "ON", "BR", "TEL"}:
        assert result(ticker)["governed_assumptions"]["acquisition_reinvestment_treatment"]["forecast_treatment"].startswith("Growth is capped")


def test_event_rows_have_document_hash_provenance():
    for ticker in BATCH_30_TICKERS:
        events = result(ticker)["source_ledger"]["event_sources"]
        policy = [item for item in events if item.get("source_kind") == "finsight_model_policy"]
        assert len(policy) == 1 and policy[0]["reported_vs_estimated"] == "finsight_assumption"
        assert "source_url" not in policy[0] and "document_sha256" not in policy[0]
        narrative = [item for item in events if item.get("source_kind") not in {"structural_xbrl", "finsight_model_policy"}]
        assert all(item.get("document_sha256") and item.get("source_url") and item.get("package_manifest_sha256") for item in narrative)
        assert any(item.get("source_kind") == "structural_xbrl" for item in events)


def test_investment_aggregates_are_diagnostic_not_arithmetic():
    checks = {"FTNT": "DebtSecuritiesAvailableForSaleAndEquitySecurities", "PLTR": "AvailableForSaleSecuritiesDebtSecurities"}
    for ticker, concept in checks.items():
        rows = result(ticker)["source_ledger"]["bridge_sources"]
        aggregate = next(row for row in rows if row.get("concept", "").endswith(f":{concept}"))
        assert aggregate["used_in_arithmetic"] is False
        assert aggregate["coverage_role"] == "diagnostic_overlap_proof"
    pltr = result("PLTR")["governed_assumptions"]["marketable_securities_coverage"]
    assert pltr["balance_sheet_cash"] + pltr["balance_sheet_marketable_securities"] == 9_409_099_000.


def test_share_units_and_dcf_replay():
    from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
    for ticker in BATCH_30_TICKERS:
        row = result(ticker)
        assert len([item for item in row["source_ledger"]["bridge_sources"] if item.get("unit") in {"shares", "xbrli:shares"}]) >= 2
        for scenario in row["scenario_rows"]:
            state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0., scenario["other_equity_claims"], scenario["shares"])
            replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
            assert float(replay["intrinsic_value_per_share"]) == pytest.approx(scenario["raw_value_per_share"])


def test_public_and_calculator_safety():
    from run_batch_30_history import _public
    for issuer in BATCH_30_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        raw = json.dumps(public)
        assert "source_ledger" not in raw and "reported_inputs" not in raw and "model_trace" not in raw
        view = calculator_view(public)
        assert view["can_calculate"] and view["model_family"] == "operating"
        assert calculate(public, overrides={}, manual_price=None)["result"] == private["scenario_range"]


def test_runner_preserves_protected_and_bookkeeping(tmp_path):
    from run_batch_30_history import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, output_root=tmp_path / "candidate")
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (2, 8, 0, 10)
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]


def test_arelle_outside_serving_process():
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
