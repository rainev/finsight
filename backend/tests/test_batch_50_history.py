import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_50 import BATCH_50_MANIFEST, BATCH_50_TICKERS
from app.us_valuation.batch_50_history import OPERATING_TICKERS, REIT_INPUTS, build_batch_50_history_result
from app.us_valuation.calculator import calculate, calculator_view
from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf, two_stage_cash_flow_value

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {"source_root": ROOT / "output/batch-50-sec-source-packets-20260912", "structural_root": ROOT / "output/batch-50-structural-sources-20260912", "event_root": ROOT / "output/batch-50-event-review-20260912", "structural_cache_root": ROOT / "output/batch-50-structural-cache-20260912"}
EXPECTED = {
    "AMT": (145.89290322580655, 155.9544827586207, 167.5066666666668),
    "CSGP": (15.713934792456987, 17.769077508236997, 20.45847402335817),
    "SPG": (153.19597707668686, 163.76121687507896, 175.89167738434418),
    "HST": (17.151649817769588, 18.334522218995065, 19.692634975957674),
    "CBRE": (54.322588756264736, 64.5370588067213, 77.67641083122435),
    "EXR": (97.85611285742715, 104.60481029587032, 112.35331476223116),
    "DLR": (99.72767576188468, 106.60544650408355, 114.50214624512688),
    "PSA": (209.0952438322663, 223.51560547587076, 240.0723169926021),
    "INVH": (21.716129032258074, 23.213793103448275, 24.93333333333335),
    "VICI": (32.37677419354841, 34.609655172413795, 37.17333333333336),
}


@lru_cache(None)
def result(ticker: str):
    return build_batch_50_history_result(ticker=ticker, **KW)


def test_exact_denominator_outcomes_and_reliability() -> None:
    rows = [result(ticker) for ticker in BATCH_50_TICKERS]
    assert len(rows) == 10 and all(row["availability_type"] == "conditional_estimate" for row in rows)
    assert all(row["history_reliability"]["label"] == "Low" for row in rows)
    for row in rows:
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        assert observed == pytest.approx(EXPECTED[row["ticker"]])
        assert 0 < observed[0] <= observed[1] <= observed[2]
        assert all(math.isfinite(value) for value in observed)


def test_exact_controls_and_route_override() -> None:
    for issuer in BATCH_50_MANIFEST:
        row = result(issuer.ticker)
        verified = row["source_ledger"]["runtime_source_verification"]
        assert verified["verified"] and verified["ticker"] == issuer.ticker and verified["cik"] == issuer.cik
        assert verified["period_end"] == "2026-06-30" and verified["filed"] <= "2026-08-14"
        assert row["source_ledger"]["structural_top_level_period_diagnostic"]["used_for_selection"] is False
        if issuer.ticker in OPERATING_TICKERS:
            assert row["method"] == "operating_enterprise_fcff"
        else:
            assert row["method"] == "reit_affo_per_share_dcf"


def test_reit_owner_cash_sources_and_rate_only_replay() -> None:
    for ticker, spec in REIT_INPUTS.items():
        row = result(ticker)
        source = row["source_ledger"]["specialist_metric_source"]
        assert source["accession"] == spec["accession"] and source["document"] == spec["document"]
        assert row["source_ledger"]["owner_cash_conversion"]["missing_values_zero_imputed"] is False
        assert len({scenario["normalized_affo_per_share"] for scenario in row["scenario_rows"]}) == 1
        assert len({scenario["locked_cash_conversion"] for scenario in row["scenario_rows"]}) == 1
        assert [scenario["discount_rate"] for scenario in row["scenario_rows"]] == [0.0975, 0.0925, 0.0875]
        for scenario in row["scenario_rows"]:
            replay = two_stage_cash_flow_value(cash_flow_per_share=scenario["normalized_affo_per_share"], growth_rate=scenario["growth_rate"], growth_years=scenario["forecast_years"], terminal_growth=scenario["terminal_growth"], discount_rate=scenario["discount_rate"])
            assert replay == pytest.approx(scenario["conditional_value_per_share"])
    exr = result("EXR")["source_ledger"]["owner_cash_conversion"]["direct_source"]
    assert exr["peer_proxy_policy"] == "BATCH-50-EXR-OWNER-CASH-PROXY-1.0"
    assert exr["conditional_low_only"] and not exr["pass_eligible"]


def test_operating_history_bridge_and_replay() -> None:
    for ticker in OPERATING_TICKERS:
        row = result(ticker)
        annual = row["source_ledger"]["annual_cash_sources"]
        assert len(annual) == 5 and [value["period_end"] for value in annual] == [f"{year}-12-31" for year in range(2021, 2026)]
        if ticker == "CSGP":
            assert any(value["cash_fcff"] < 0 for value in annual)
        bridge = row["source_ledger"]["bridge_context"]
        assert bridge["cash"] >= 0 and bridge["debt"] > 0 and bridge["shares"] > 0
        assert bridge["preferred_claim_status"]["reported_preferred_equity"] is None
        assert bridge["preferred_claim_status"]["modeled_preferred_equity"] == 0.0
        assert not bridge["missing_values_zero_imputed"]
        assert len({scenario["starting_cash_fcff"] for scenario in row["scenario_rows"]}) == 1
        assert len({scenario["growth_rate"] for scenario in row["scenario_rows"]}) == 1
        for scenario in row["scenario_rows"]:
            replay = enterprise_cash_flow_dcf(EnterpriseCashFlowState(cash_fcff=scenario["starting_cash_fcff"], initial_growth=scenario["growth_rate"], terminal_growth=scenario["terminal_growth"], wacc=scenario["wacc"], cash_and_investments=scenario["cash"], interest_bearing_debt=scenario["debt"], preferred_equity=0.0, noncontrolling_interests=scenario["preferred_and_nci"], diluted_shares=scenario["shares"]), forecast_years=scenario["forecast_years"])
            assert replay["intrinsic_value_per_share"] == pytest.approx(scenario["conditional_value_per_share"])


def test_event_receipts_are_complete_and_cutoff_safe() -> None:
    for ticker in BATCH_50_TICKERS:
        event = result(ticker)["source_ledger"]["event_sources"]
        assert event["screened_filings"] and event["documents"]
        assert all(row["filed"] <= "2026-08-14" for row in event["screened_filings"])
        assert event["treatment"]


def test_public_model_calculator_and_leak_contract() -> None:
    from run_batch_50_history import _public

    forbidden = ("source_ledger", "reported_inputs", "governed_assumptions", "specialist_metric_source", "scenario_rows")
    for issuer in BATCH_50_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        primary = "fcff_dcf" if issuer.ticker in OPERATING_TICKERS else "affo_dcf"
        assert public["model_policy"]["primary"] == primary and set(public["models"]) == {primary}
        assert public["availability_type"] == "conditional_estimate"
        assert sanitize_public_artifact(public) == public
        assert not any(key in json.dumps(public) for key in forbidden)
        view = calculator_view(public)
        assert view["can_calculate"] and view["model_family"] == ("enterprise_fcff" if issuer.ticker in OPERATING_TICKERS else "reit")
        assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx({key: public["scenario_range"][key] for key in ("low", "base", "high")})
        if issuer.ticker in OPERATING_TICKERS:
            assert public["public_assumptions"]["initial_revenue_growth"] == pytest.approx(private["scenario_rows"][1]["growth_rate"])
            defaults = {field["key"]: field["value"] for field in view["editable_assumptions"]}
            assert defaults["initial_growth"] == pytest.approx(private["scenario_rows"][1]["growth_rate"])


def test_source_tampering_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "AMT", source / "AMT")
    (source / "AMT/companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_50_history_result(ticker="AMT", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_50_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 10, 0, 10)
    assert report["denominator_tickers"] == list(BATCH_50_TICKERS)
    assert report["batch_49_dependency_status"] == "confirmed_batch_49_recovery_catalog_and_bookkeeping_bound"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
