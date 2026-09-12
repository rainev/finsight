import json
from pathlib import Path
import sys

from app.us_valuation.batch_43 import BATCH_43_MANIFEST
from app.us_valuation.batch_43_recovery import ATTEMPTED, build_batch_43_recovery_result
from app.us_valuation.calculator import calculator_view


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
INITIAL = ROOT / "output/batch-43-history-run-g-20260907"
KW = {"source_root": ROOT / "output/batch-43-sec-source-packets-b-20260907", "structural_root": ROOT / "output/batch-43-structural-sources-20260907", "event_root": ROOT / "output/batch-43-event-review-20260907", "structural_cache_root": ROOT / "output/batch-43-structural-cache-20260907", "cop_annual_root": ROOT / "output/batch-43-cop-annual-source-20260907"}


def result(ticker):
    return build_batch_43_recovery_result(ticker=ticker, **KW)


def test_recovery_outcomes_remain_exactly_three_withheld():
    rows = {issuer.ticker: result(issuer.ticker) for issuer in BATCH_43_MANIFEST}
    assert {ticker for ticker, row in rows.items() if row["availability_type"] == "not_available"} == ATTEMPTED
    assert all(row["availability_type"] == "conditional_estimate" for ticker, row in rows.items() if ticker not in ATTEMPTED)
    assert all(rows[ticker]["scenario_range"] == {"low": None, "base": None, "high": None} for ticker in ATTEMPTED)


def test_dvn_pro_forma_revenue_and_earnings_do_not_become_cash_flow():
    dvn = result("DVN")
    table = dvn["source_ledger"]["recovery_evidence"]["pro_forma_table"]
    assert table["accession"] == "0001193125-26-334340"
    assert table["revenue"] == {"q2_2026": 8_150_000_000., "q2_2025": 6_240_000_000., "h1_2026": 13_894_000_000., "h1_2025": 12_586_000_000.}
    assert table["net_earnings"]["h1_2026"] == 2_464_000_000
    assert table["reported_cash_flow_fields"] == []
    assert dvn["source_ledger"]["rejected_recovery_diagnostic"]["publication_allowed"] is False
    assert "PRO_FORMA_EARNINGS_NOT_CASH_FLOW" in dvn["governed_assumptions"]["reason_codes"]


def test_nem_known_payment_does_not_zero_impute_unknown_transaction_terms():
    nem = result("NEM")
    terms = nem["source_ledger"]["recovery_evidence"]["ngm_fourmile_terms"]
    assert terms["newmont_payment_after_fourmile_contribution"] == 1_950_000_000
    assert terms["barrick_deemed_contribution"] == 3_114_935_064.94
    assert terms["assumed_project_liabilities"] is None
    assert terms["confidential_settlement_value"] is None
    assert terms["final_membership_after_valuation"] is None
    assert nem["source_ledger"]["rejected_recovery_diagnostic"]["known_payment_reserve"] == 1_950_000_000
    assert nem["source_ledger"]["rejected_recovery_diagnostic"]["publication_allowed"] is False


def test_lyb_event_facts_are_exact_but_continuing_cash_fields_remain_missing():
    lyb = result("LYB")
    evidence = lyb["source_ledger"]["recovery_evidence"]
    assert evidence["reported_event_facts"]["european_sale_loss"]["value"] == -734_000_000
    assert evidence["reported_event_facts"]["cash_contribution_to_sold_businesses"]["value"] == -310_000_000
    assert evidence["reported_event_facts"]["discontinued_operations_net_income_loss"]["value"] == -27_000_000
    assert evidence["continuing_company_ocf"] is None
    assert evidence["continuing_company_capex"] is None
    assert lyb["source_ledger"]["rejected_recovery_diagnostic"]["publication_allowed"] is False


def test_attempted_public_outputs_remain_safe_and_uncalculable():
    from run_batch_43_recovery import _public

    for issuer in BATCH_43_MANIFEST:
        if issuer.ticker not in ATTEMPTED:
            continue
        private = result(issuer.ticker)
        public = _public(issuer, private)
        encoded = json.dumps(public)
        assert public["availability_type"] == "not_available"
        assert public["model_policy"]["primary"] == "fcff_dcf"
        assert public["scenario_range"]["base"] is None
        assert not calculator_view(public)["can_calculate"]
        for key in ("source_ledger", "reported_inputs", "governed_assumptions", "recovery_evidence", "rejected_recovery_diagnostic"):
            assert key not in encoded


def test_recovery_runner_pins_initial_and_preserves_protected_state(tmp_path):
    from run_batch_43_recovery import run

    output = tmp_path / "candidate"
    report = run(initial_root=INITIAL, output_root=output, **KW)
    assert (report["attempted_count"], report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (3, 0, 7, 3, 7)
    assert report["attempted_tickers"] == ["DVN", "NEM", "LYB"]
    assert report["recovered_to_conditional_tickers"] == []
    assert report["still_withheld_tickers"] == ["DVN", "NEM", "LYB"]
    initial_report = json.loads((INITIAL / "batch-43-report.json").read_text())
    initial_cases = {row["ticker"]: row for row in initial_report["cases"]}
    for issuer in BATCH_43_MANIFEST:
        if issuer.ticker in ATTEMPTED:
            continue
        assert (output / "generated" / issuer.ticker / "valuation-private.json").read_bytes() == (INITIAL / "generated" / issuer.ticker / "valuation-private.json").read_bytes()
        assert (output / "staged-public" / f"{issuer.ticker}.json").read_bytes() == (INITIAL / "staged-public" / f"{issuer.ticker}.json").read_bytes()
        assert next(row for row in report["cases"] if row["ticker"] == issuer.ticker) == initial_cases[issuer.ticker]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
