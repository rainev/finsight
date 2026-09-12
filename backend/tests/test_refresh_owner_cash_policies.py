import copy
import json
from pathlib import Path

import pytest

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_owner_cash_policies import bind_owner_cash_recipe, compile_owner_cash_policy


ROOT = Path(__file__).parents[2]
TICKERS = ("META", "OMC", "TTWO")


def _packet(ticker: str) -> tuple[dict, dict]:
    recipe = json.loads((ROOT / "output/us-refresh-runtime/recipes" / f"{ticker}.json").read_text())
    sec = ROOT / "output/batch-02-sec-source-packets-20260824" / ticker
    structural = json.loads((ROOT / "output/batch-02-structural-sources-20260824" / ticker / "structural-filing.json").read_text())
    receipt = json.loads((ROOT / "output/batch-02-structural-sources-20260824" / ticker / "source-receipt.json").read_text())
    if ticker == 'TTWO':
        current = ROOT/'output/us-refresh-owner-source-verification/TTWO'
        structural = json.loads((current/'structural-filing.json').read_text())
        receipt = json.loads((current/'source-receipt.json').read_text())
    submissions = json.loads((sec / "submissions.json").read_text())
    companyfacts = json.loads((sec / "companyfacts.json").read_text())
    accession = recipe["source_accession"]
    rows = [{key: values[i] for key, values in submissions["filings"]["recent"].items() if isinstance(values, list) and i < len(values)} for i in range(len(submissions["filings"]["recent"]["accessionNumber"]))]
    end = next(row["reportDate"] for row in rows if row.get("accessionNumber") == accession)
    return recipe, {"submissions": submissions, "companyfacts": companyfacts, "structural_filing": structural, "structural_receipt": receipt, "_selected_controlling_filing": {"accession": accession, "period_end": end}}


def _policy(ticker: str, recipe: dict) -> dict:
    registry = json.loads((ROOT / "output/us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == ticker)
    return compile_owner_cash_policy(recipe, entry)


def test_real_cached_ttwo_owner_cash_bind_uses_shared_recipe_engine() -> None:
    ticker = "TTWO"
    recipe, packet = _packet(ticker)
    result = bind_owner_cash_recipe(_policy(ticker, recipe), recipe, packet, cutoff="2026-08-14")
    assert result["status"] == "bound_successor_candidate"
    assert result["replay"] == evaluate_recipe(result["recipe"])["range"]
    assert result["source_ledger"]["controlling_filing"]["accession"] == recipe["source_accession"]
    assert result["source_ledger"]["flow_period"]["annualization_factor"] == 4.0


@pytest.mark.parametrize("ticker", ("META", "OMC"))
def test_unbound_original_timing_claims_raise_explicit_gap(ticker: str) -> None:
    recipe, packet = _packet(ticker)
    with pytest.raises(RuntimeError, match="timing/commitment reserve waterfall"):
        bind_owner_cash_recipe(_policy(ticker, recipe), recipe, packet, cutoff="2026-08-14")


def test_owner_cash_policies_do_not_copy_filing_dates_or_cash_amounts() -> None:
    for ticker in TICKERS:
        recipe, _ = _packet(ticker)
        policy = _policy(ticker, recipe)
        assert policy["baseline_binding"]["source_path"] == recipe["provenance"]["source_path"]
        assert "2026-06-30" not in json.dumps(policy)
        assert "cash_states" in policy["fixed_assumptions"] or "tax_rate" in policy["fixed_assumptions"]
        assert policy["bridge_rule"].startswith("current source")


def test_meta_owner_cash_formula_consumes_current_source_revenue() -> None:
    recipe, packet = _packet("META")
    with pytest.raises(RuntimeError):
        bind_owner_cash_recipe(_policy("META", recipe), recipe, packet, cutoff="2026-08-14")


def test_omc_formula_uses_operating_income_da_capex_and_tax_not_net_income() -> None:
    recipe, packet = _packet("OMC")
    with pytest.raises(RuntimeError):
        bind_owner_cash_recipe(_policy("OMC", recipe), recipe, packet, cutoff="2026-08-14")


def test_ttwo_selected_period_derives_quarter_not_h1() -> None:
    recipe, packet = _packet("TTWO")
    result = bind_owner_cash_recipe(_policy("TTWO", recipe), recipe, packet, cutoff="2026-08-14")
    assert result["source_ledger"]["flow_period"]["annualization_factor"] == 4.0
    assert result["source_ledger"]["flow_period"]["period_start"] == "2026-04-01"


def test_ttwo_cash_or_debt_perturbation_moves_bound_value() -> None:
    recipe, packet = _packet("TTWO")
    baseline = bind_owner_cash_recipe(_policy("TTWO", recipe), recipe, packet, cutoff="2026-08-14")
    mutated = copy.deepcopy(packet)
    for row in mutated["structural_filing"]["facts"]:
        if row.get("local_name") == "CashAndCashEquivalentsAtCarryingValue" and row.get("period_end") == "2026-06-30" and row.get("period_start") is None and not row.get("dimensions"):
            row["value"] += 100_000_000
    changed = bind_owner_cash_recipe(_policy("TTWO", recipe), recipe, mutated, cutoff="2026-08-14")
    assert changed["replay"]["base"] > baseline["replay"]["base"]


def test_changed_dispatcher_accession_is_rejected() -> None:
    recipe, packet = _packet("OMC")
    packet["_selected_controlling_filing"] = {**packet["_selected_controlling_filing"], "accession": "0000029989-26-999999"}
    with pytest.raises(ValueError, match="eligible|accession"):
        bind_owner_cash_recipe(_policy("OMC", recipe), recipe, packet, cutoff="2026-08-14")
