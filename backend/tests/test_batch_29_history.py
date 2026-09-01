from pathlib import Path
import json
import sys

import pytest

from app.us_valuation.batch_29 import BATCH_29_MANIFEST, BATCH_29_TICKERS
from app.us_valuation.batch_29_history import PASS_TICKERS, CONDITIONAL_TICKERS, WITHHELD_TICKERS, build_batch_29_history_result
from app.us_valuation.calculator import calculate, calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SOURCE = ROOT / "output/batch-29-sec-source-packets-b-20260901"
STRUCTURAL = ROOT / "output/batch-29-structural-sources-b-20260901"


def result(ticker):
    return build_batch_29_history_result(ticker=ticker, source_root=SOURCE, structural_root=STRUCTURAL)


EXPECTED = {
    "TRMB": (10.353695968741611, 23.56100223508714, 49.54140126997636),
    "ROP": (213.2763192736134, 411.54803407219003, 668.0570535448302),
    "SNPS": (83.45897418204306, 209.69058006424245, 367.3919971245069),
    "INTU": (260.0699210493803, 490.0596615752675, 838.6617799454696),
    "CIEN": (14.151857480163335, 67.70787152213722, 135.95235320987638),
    "NTAP": (64.18083049151697, 116.20271539487032, 186.7274100105445),
    "VRSN": (115.92279613059422, 187.8126619310813, 277.57192863555605),
    "NVDA": (35.46340860325773, 103.54626603939504, 190.44878719789594),
    "FFIV": (156.8960080503151, 256.6761870244352, 378.1794513863351),
    "AKAM": (42.929155674935714, 89.66177879295472, 142.09756402183348),
}


def test_outcomes_ranges_and_denominator():
    rows = {ticker: result(ticker) for ticker in BATCH_29_TICKERS}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "available"} == set(PASS_TICKERS) == {"CIEN", "NTAP", "VRSN"}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "conditional_estimate"} == set(CONDITIONAL_TICKERS) == {"TRMB", "ROP", "SNPS", "INTU", "NVDA", "FFIV", "AKAM"}
    assert not WITHHELD_TICKERS
    assert len(rows) == 10
    for ticker, row in rows.items():
        values = row["scenario_range"]
        assert 0 <= values["low"] <= values["base"] <= values["high"]
        assert values["base"] > 0
        assert tuple(values[key] for key in ("low", "base", "high")) == pytest.approx(EXPECTED[ticker])


def test_customer_funds_investments_and_event_claims_are_traceable():
    intu = result("INTU")
    bridge = intu["source_ledger"]["bridge_reconciliation"]
    assert bridge["cash_and_investments"] == (6_956_000_000.,) * 3
    assert any(item.get("source_kind") == "customer_funds_reconciliation" for item in intu["source_ledger"]["event_sources"])
    assert intu["governed_assumptions"]["cash_reinvestment_adjustment"] == pytest.approx((554_666_666.6666666, 416_000_000., 0.))
    assert intu["source_ledger"]["unquantified_legal_tail_policy"]["zero_substitution_used"] is False
    nvda = result("NVDA")
    claims = nvda["source_ledger"]["bridge_reconciliation"]["other_equity_claims"]
    assert claims[0] > claims[1] > claims[2] > 8_457_000_000.
    assert nvda["source_ledger"]["bridge_reconciliation"]["future_not_commenced_lease_schedule"]["reported_total"] == 32_400_000_000.
    assert "no second claim" in nvda["source_ledger"]["bridge_reconciliation"]["infrastructure_fund_maximum_loss_exposure_treatment"]
    assert nvda["scenario_rows"][0]["cash_and_investments"] < nvda["scenario_rows"][2]["cash_and_investments"]
    akam = result("AKAM")
    assert any(item.get("value") == 205_000_000. for item in akam["source_ledger"]["event_sources"])


def test_commitments_and_acquisition_scope_are_recorded_without_zero_substitution():
    trmb = result("TRMB")
    assert any(item.get("value") == 625_800_000. for item in trmb["source_ledger"]["event_sources"])
    snps = result("SNPS")
    assert any(item.get("value") == 34_900_000_000. for item in snps["source_ledger"]["event_sources"])
    cien = result("CIEN")
    assert any(item.get("value") == 2_800_000_000. for item in cien["source_ledger"]["event_sources"])
    ntap = result("NTAP")
    assert any(item.get("value") == 1_400_000_000. for item in ntap["source_ledger"]["event_sources"])
    assert all(row["reported_inputs"]["ttm_reinvestment"] > 0 for row in (trmb, snps, cien, ntap))
    for ticker in BATCH_29_TICKERS:
        narrative = [item for item in result(ticker)["source_ledger"]["event_sources"] if item.get("source_kind") != "structural_xbrl"]
        assert narrative and all(item.get("document_sha256") and item.get("source_url") and item.get("package_manifest_sha256") for item in narrative)


def test_share_units_and_dcf_replay():
    from app.us_valuation.practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
    for ticker in BATCH_29_TICKERS:
        row = result(ticker)
        share_sources = [item for item in row["source_ledger"]["bridge_sources"] if item.get("unit") in {"shares", "xbrli:shares"}]
        assert len(share_sources) >= 2
        for scenario in row["scenario_rows"]:
            state = EnterpriseCashFlowState(scenario["starting_cash_fcff"], scenario["growth"], scenario["terminal_growth"], scenario["wacc"], scenario["cash_and_investments"], scenario["debt_and_finance_leases"], 0., scenario["other_equity_claims"], scenario["shares"])
            replay = enterprise_cash_flow_dcf(state, forecast_years=8, allow_nonpositive_equity_trace=True)
            assert float(replay["intrinsic_value_per_share"]) == pytest.approx(scenario["raw_value_per_share"])


def test_public_and_calculator_safety():
    from run_batch_29_history import _public
    for issuer in BATCH_29_MANIFEST:
        private = result(issuer.ticker)
        public = _public(issuer, private)
        raw = json.dumps(public)
        assert "source_ledger" not in raw and "reported_inputs" not in raw and "model_trace" not in raw
        view = calculator_view(public)
        assert view["can_calculate"] and view["model_family"] == "operating"
        assert calculate(public, overrides={}, manual_price=None)["result"] == private["scenario_range"]


def test_runner_preserves_protected_and_bookkeeping(tmp_path):
    from run_batch_29_history import run
    report = run(source_root=SOURCE, structural_root=STRUCTURAL, output_root=tmp_path / "candidate")
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (3, 7, 0, 10)
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]


def test_arelle_outside_serving_process():
    for path in [ROOT / "backend/app/main.py", ROOT / "backend/app/deps.py", *sorted((ROOT / "backend/app/routers").glob("*.py"))]:
        assert "arelle" not in path.read_text().lower()
