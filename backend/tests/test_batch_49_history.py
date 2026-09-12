import json
import math
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_49 import BATCH_49_MANIFEST, BATCH_49_TICKERS
from app.us_valuation.batch_49_history import INPUTS, WITHHELD_TICKERS, build_batch_49_history_result
from app.us_valuation.calculator import calculate, calculator_view
from app.us_valuation.practical_models import two_stage_cash_flow_value

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
KW = {"source_root": ROOT / "output/batch-49-sec-source-packets-20260912", "structural_root": ROOT / "output/batch-49-structural-sources-pass3-20260912", "event_root": ROOT / "output/batch-49-event-review-20260912", "structural_cache_root": ROOT / "output/batch-49-structural-cache-20260912"}
EXPECTED = {
    "REG": (53.84303077074963, 57.556343237697845, 61.81977607011995),
    "MAA": (98.7096774193549, 105.51724137931035, 113.33333333333343),
    "AVB": (None, None, None),
    "ESS": (190.30079197606398, 203.42498452613722, 218.49350189844387),
    "SBAC": (159.71225806451622, 170.72689655172414, 183.37333333333345),
    "ARE": (74.9667096774194, 80.1368275862069, 86.07288888888897),
    "BXP": (63.4872374073571, 67.86566757338169, 72.8927540602989),
    "PLD": (76.76559491944253, 82.05977387940405, 88.13827564824885),
    "CCI": (60.41032258064519, 64.57655172413793, 69.36000000000006),
    "EQIX": (565.8038709677423, 604.824827586207, 649.6266666666672),
}


@lru_cache(None)
def result(ticker: str):
    return build_batch_49_history_result(ticker=ticker, **KW)


def test_exact_outcomes_ranges_and_reliability() -> None:
    rows = [result(ticker) for ticker in BATCH_49_TICKERS]
    assert [row["ticker"] for row in rows if row["availability_type"] == "not_available"] == ["AVB"]
    assert len([row for row in rows if row["availability_type"] == "conditional_estimate"]) == 9
    for row in rows:
        observed = tuple(row["scenario_range"][key] for key in ("low", "base", "high"))
        if row["ticker"] in WITHHELD_TICKERS:
            assert observed == EXPECTED[row["ticker"]] and row["history_reliability"] is None
        else:
            assert observed == pytest.approx(EXPECTED[row["ticker"]])
            assert 0 < observed[0] <= observed[1] <= observed[2]
            assert all(math.isfinite(value) for value in observed)
            assert row["history_reliability"]["label"] == "Low"


def test_exact_controls_and_specialist_source_lineage() -> None:
    for issuer in BATCH_49_MANIFEST:
        row = result(issuer.ticker)
        verified = row["source_ledger"]["runtime_source_verification"]
        assert verified["verified"] and verified["ticker"] == issuer.ticker and verified["cik"] == issuer.cik
        assert verified["period_end"] == "2026-06-30" and verified["filed"] <= "2026-08-14"
        assert row["source_ledger"]["structural_top_level_period_diagnostic"]["used_for_selection"] is False
        if issuer.ticker in INPUTS:
            source = row["source_ledger"]["specialist_metric_source"]
            assert source["accession"] == INPUTS[issuer.ticker]["accession"] and source["unit"] == "USD/share"
            assert row["source_ledger"]["recurring_capital_basis"]["missing_values_zero_imputed"] is False
            assert row["source_ledger"]["recurring_capital_basis"]["direct_source"]["accession"] == INPUTS[issuer.ticker]["accession"]


def test_affo_dcf_is_rate_only_and_replays_exactly() -> None:
    for ticker in INPUTS:
        row = result(ticker)
        assert len({scenario["normalized_affo_per_share"] for scenario in row["scenario_rows"]}) == 1
        assert len({scenario["locked_recurring_cost_ratio"] for scenario in row["scenario_rows"]}) == 1
        assert [scenario["discount_rate"] for scenario in row["scenario_rows"]] == [0.0975, 0.0925, 0.0875]
        for scenario in row["scenario_rows"]:
            replay = two_stage_cash_flow_value(cash_flow_per_share=scenario["normalized_affo_per_share"], growth_rate=scenario["growth_rate"], growth_years=scenario["forecast_years"], terminal_growth=scenario["terminal_growth"], discount_rate=scenario["discount_rate"])
            assert replay == pytest.approx(scenario["conditional_value_per_share"])


def test_bxp_typed_dimension_repair_is_bounded_and_deterministic() -> None:
    structural = json.loads((KW["structural_root"] / "BXP/structural-filing.json").read_text())
    members = [member for fact in structural["facts"] for _, _, member in fact.get("typed_dimensions", [])]
    assert members
    assert all(member == "empty" or len(member) <= 4096 for member in members)
    assert any(member.startswith("sha256:") or member == "empty" for member in members)


def test_avb_pending_merger_is_withheld_without_successor_substitution() -> None:
    row = result("AVB")
    assert row["availability_type"] == "not_available" and row["scenario_range"] == {"low": None, "base": None, "high": None}
    assert row["source_ledger"]["cutoff_identity"] == {"ticker": "AVB", "cik": "0000915912", "name": "AvalonBay Communities", "status": "standalone legal issuer at 2026-08-14"}
    event = row["source_ledger"]["merger_approval_event"]
    assert event["accession"] == "0001104659-26-094930" and event["filed"] == "2026-08-12"
    assert "post-cutoff" not in json.dumps(row["reported_inputs"]).lower()


def test_public_model_calculator_and_leak_contract() -> None:
    from run_batch_49_history import _public

    forbidden = ("source_ledger", "reported_inputs", "governed_assumptions", "specialist_metric_source", "scenario_rows")
    for issuer in BATCH_49_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        assert public["model_policy"]["primary"] == "affo_dcf" and set(public["models"]) == {"affo_dcf"}
        assert not any(key in json.dumps(public) for key in forbidden)
        view = calculator_view(public)
        if issuer.ticker == "AVB":
            assert public["availability_type"] == "not_available" and not view["can_calculate"]
        else:
            assert public["availability_type"] == "conditional_estimate" and view["model_family"] == "reit" and view["can_calculate"]
            assert calculate(public, overrides={}, manual_price=None)["result"] == pytest.approx({key: public["scenario_range"][key] for key in ("low", "base", "high")})
            assert "recurring_cost_ratio" not in {field["key"] for field in view["editable_assumptions"]}
            with pytest.raises(ValueError, match="locked source-derived input"):
                calculate(public, overrides={"recurring_cost_ratio": 0.10}, manual_price=None)


def test_source_tampering_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "sources"
    shutil.copytree(KW["source_root"] / "REG", source / "REG")
    (source / "REG/companyfacts.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        build_batch_49_history_result(ticker="REG", **{**KW, "source_root": source})


def test_runner_preserves_serving_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_49_history import run

    report = run(output_root=tmp_path / "candidate", **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (10, 0, 9, 1, 9)
    assert report["denominator_tickers"] == list(BATCH_49_TICKERS)
    assert report["batch_48_dependency_status"] == "confirmed_batch_48_recovery_catalog_and_bookkeeping_bound"
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
