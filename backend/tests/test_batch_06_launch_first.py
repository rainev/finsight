from pathlib import Path
import pytest

from app.us_valuation.batch_06 import BATCH_06_MANIFEST,BATCH_06_TICKERS
from app.us_valuation.batch_06_launch_first import build_batch_06_launch_first_result
from app.us_valuation.calculator import calculate,calculator_view
from app.us_valuation.reliability import accounting_label
from run_batch_06_launch_first import _public
from run_batch_06_history_repair import _history_public


SOURCE=Path("output/batch-06-sec-source-packets-20260826")
STRUCTURAL=Path("output/batch-06-structural-sources-20260826")


def _result(ticker: str) -> dict:
    return build_batch_06_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)


def test_all_batch_06_baselines_are_conditional_low_and_ordered() -> None:
    for ticker in BATCH_06_TICKERS:
        result=_result(ticker);values=result["scenario_range"]
        assert 0 <= values["low"] <= values["base"] <= values["high"]
        assert values["base"] > 0
        assert result["baseline"]["availability_type"] == "conditional_estimate"
        assert result["baseline"]["confidence"] == "Low"


def test_period_exceptions_are_repaired_or_explicitly_labeled() -> None:
    bby=_result("BBY")
    assert bby["reported_inputs"]["revenue_period_end"] == "2026-05-02"
    assert bby["reported_inputs"]["operating_cash_flow_period_end"] == "2026-05-02"
    assert "Current TTM revenue is reconstructed" in bby["governed_assumptions"]["revenue_period_treatment"]
    yum=_result("YUM")
    assert yum["reported_inputs"]["interest_period_status"] == "latest_fiscal_year_carried_as_estimate"
    assert yum["source_ledger"]["interest_source"]["period_end"] == "2025-12-31"
    cmg=_result("CMG")
    assert cmg["reported_inputs"]["interest_expense"] is None
    assert cmg["reported_inputs"]["interest_period_status"] == "not_used_owner_cash_proxy"
    assert "No interest addback is used" in cmg["governed_assumptions"]["interest_period_treatment"]


def test_lennar_uses_source_traced_consolidated_equity_earnings() -> None:
    result=_result("LEN");ledger=result["source_ledger"];components=ledger["net_income_reconstruction"]["components"]
    assert result["method"] == "homebuilder_normalized_equity_earnings_baseline"
    assert result["governed_assumptions"]["route_is_mortgage_separated_fcff"] is False
    assert result["governed_assumptions"]["ev_debt_bridge_applied"] is False
    assert components["fy"]["value"]+components["current_ytd"]["value"]-components["prior_ytd"]["value"] == ledger["net_income_reconstruction"]["ttm"]
    assert all(row["accession"] and row["concept"] and row["unit"] for row in ledger["mortgage_and_land_context"])


def test_supplier_finance_and_finance_leases_are_explicit_once() -> None:
    bby=_result("BBY");tsco=_result("TSCO")
    assert any(row.get("concept")=="us-gaap:SupplierFinanceProgramObligation" and row["value"]==861_000_000 for row in bby["source_ledger"]["bridge_sources"])
    assert any(row.get("concept")=="us-gaap:SupplierFinanceProgramObligation" and row["value"]==179_000_000 for row in tsco["source_ledger"]["bridge_sources"])
    assert tsco["source_ledger"]["bridge_reconciliation"]["model_debt_and_finance_leases"] == 2_207_074_000
    assert _result("DRI")["source_ledger"]["bridge_reconciliation"]["model_debt_and_finance_leases"] == 3_929_500_000
    assert _result("MAR")["source_ledger"]["bridge_reconciliation"]["model_debt_and_finance_leases"] == 16_915_000_000
    assert _result("YUM")["source_ledger"]["bridge_reconciliation"]["model_debt_and_finance_leases"] == 9_462_000_000
    for ticker in ("DECK","CMG"):
        result=_result(ticker);bridge=result["source_ledger"]["bridge_reconciliation"]
        assert bridge["reported_debt_and_finance_leases"] is None
        assert bridge["debt_status"] == "unresolved_covered_by_reserve"
        reserve=[row for row in result["source_ledger"]["bridge_sources"] if row.get("field")=="unresolved_debt_nci_and_other_claims"]
        assert reserve[0]["value_range"]["bear"] == 2*reserve[0]["value_range"]["base"]
        assert reserve[0]["value_range"]["bull"] == 0
        assert "unreported debt" in reserve[0]["basis"]


def test_structural_summary_period_is_never_the_controlling_period() -> None:
    for ticker in BATCH_06_TICKERS:
        diagnostic=_result(ticker)["source_ledger"]["structural_top_level_period_diagnostic"]
        assert diagnostic["used_for_selection"] is False


def test_public_calculators_match_model_identity_and_default_values() -> None:
    for issuer in BATCH_06_MANIFEST:
        result=_result(issuer.ticker);artifact=_public(issuer,result);view=calculator_view(artifact)
        assert calculate(artifact,overrides={},manual_price=None)["result"]["base"] == artifact["scenario_range"]["base"]
        assert artifact["reliability"]["accounting_label"] == accounting_label(result["accounting_impact_ratio"])
        if issuer.ticker == "LEN":
            assert view["model_family"] == "equity_earnings"
            assert calculate(artifact,overrides={"normalized_earnings_factor":1.1},manual_price=None)["result"]["base"] > artifact["scenario_range"]["base"]
        else:
            assert view["model_family"] == "operating"


def test_history_backed_batch06_has_seven_pass_and_three_conditional() -> None:
    passes={"BBY","DECK","TSCO","DRI","RL","MAR","CMG"}
    for issuer in BATCH_06_MANIFEST:
        result=build_batch_06_launch_first_result(ticker=issuer.ticker,source_root=SOURCE,structural_root=STRUCTURAL,history_backed=True);expected="available" if issuer.ticker in passes else "conditional_estimate"
        assert result["availability_type"]==expected
        assert result["governed_assumptions"]["history_years_used"]>=3
        assert result["source_ledger"]["company_history_profile"]["full_history"] is True
        public=_history_public(issuer,result)
        assert public["availability_type"]==expected
        assert public["public_assumptions"]["history_policy_version"]=="US-COMPANY-HISTORY-1.0"
        assert "company_history_profile" not in public


def test_history_backed_pass_ranges_match_source_history() -> None:
    expected={"BBY":49.8188,"DECK":201.9910,"TSCO":14.5458,"DRI":150.2975,"RL":266.3982,"MAR":175.2614,"CMG":27.2352}
    for ticker,base in expected.items():
        result=build_batch_06_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL,history_backed=True)
        assert result["scenario_range"]["base"]==pytest.approx(base,abs=.0001)
        assert result["governed_assumptions"]["assumption_source_mix"]=="reported_and_company_history"
    bby=build_batch_06_launch_first_result(ticker="BBY",source_root=SOURCE,structural_root=STRUCTURAL,history_backed=True)
    assert bby["reported_inputs"]["revenue_anchor"]==41_860_000_000
    assert bby["reported_inputs"]["revenue_period_end"]=="2026-05-02"
    cmg=build_batch_06_launch_first_result(ticker="CMG",source_root=SOURCE,structural_root=STRUCTURAL,history_backed=True)
    assert cmg["source_ledger"]["bridge_reconciliation"]["debt_status"]=="source_proven_absent"
    assert len(cmg["source_ledger"]["company_history_profile"]["annual_periods"])==5
