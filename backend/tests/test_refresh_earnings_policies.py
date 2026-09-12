import copy
import json
from datetime import date
from pathlib import Path

import pytest

from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_earnings_policies import bind_earnings_recipe, compile_earnings_refresh_policy


ROOT = Path(__file__).parents[2]
PACKETS = {
    "F": ("batch-04-sec-source-packets-20260825", "batch-04-structural-sources-20260825"),
    "GM": ("batch-08-sec-source-packets-20260826", "batch-08-structural-sources-20260826"),
    "DHI": ("batch-05-sec-source-packets-20260825", "batch-05-structural-sources-20260825"),
    "LEN": ("batch-06-sec-source-packets-20260826", "batch-06-structural-sources-20260826"),
    "NVR": ("batch-05-sec-source-packets-20260825", "batch-05-structural-sources-20260825"),
    "PHM": ("batch-05-sec-source-packets-20260825", "batch-05-structural-sources-20260825"),
}


def _packet(ticker: str) -> tuple[dict, dict, dict]:
    recipe = json.loads((ROOT / "output/us-refresh-runtime/recipes" / f"{ticker}.json").read_text())
    sec_root, structural_root = PACKETS[ticker]
    sec = ROOT / "output" / sec_root / ticker
    submissions = json.loads((sec / "submissions.json").read_text())
    companyfacts = json.loads((sec / "companyfacts.json").read_text())
    structural = json.loads((ROOT / "output" / structural_root / ticker / "structural-filing.json").read_text())
    accession = recipe["source_accession"]
    end = next(row["reportDate"] for row in ({k: v[i] for k, v in submissions["filings"]["recent"].items() if isinstance(v, list)} for i in range(len(submissions["filings"]["recent"]["accessionNumber"]))) if row.get("accessionNumber") == accession)
    concepts = {
        "F": "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "GM": "NetIncomeLossAvailableToCommonStockholdersBasic",
        "DHI": "NetIncomeLoss",
        "LEN": "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NVR": "NetIncomeLoss",
        "PHM": "NetIncomeLoss",
    }
    candidates = [
        row for row in structural["facts"]
        if row.get("local_name") == concepts[ticker]
        and row.get("period_end") == end
        and row.get("source_accession") == accession
        and row.get("period_start")
        and not row.get("dimensions")
    ]
    period_start = max(candidates, key=lambda row: (date.fromisoformat(row["period_end"]) - date.fromisoformat(row["period_start"])).days)["period_start"]
    packet = {"submissions": submissions, "companyfacts": companyfacts, "structural_filing": structural, "_selected_controlling_filing": {"accession": accession, "period_start": period_start, "period_end": end}}
    return recipe, packet, structural


def _policy(ticker: str, recipe: dict) -> dict:
    registry = json.loads((ROOT / "output/us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == ticker)
    return compile_earnings_refresh_policy(recipe, entry)


@pytest.mark.parametrize("ticker", sorted(PACKETS))
def test_real_cached_issuers_bind_and_replay_exact_recipe(ticker: str) -> None:
    recipe, packet, _ = _packet(ticker)
    policy = _policy(ticker, recipe)
    result = bind_earnings_recipe(policy, recipe, packet, cutoff="2026-08-14")
    assert result["status"] == "bound_successor_candidate"
    # A source refresh may legitimately move a denominator (DHI/NVR/PHM); the
    # invariant is that the returned recipe is evaluated by the shared engine,
    # not hand-scaled to the frozen target.
    assert result["replay"] == evaluate_recipe(result["recipe"])["range"]
    assert result["source_ledger"]["ev_debt_bridge_applied"] is False
    assert result["source_ledger"]["current_shares"]["current"]["period_end"] == packet["_selected_controlling_filing"]["period_end"]
    assert result["source_ledger"]["current_shares"]["current"]["accession"] == packet["_selected_controlling_filing"]["accession"]


def test_policies_preserve_provenance_and_do_not_embed_filing_dates_or_amounts() -> None:
    for ticker in sorted(PACKETS):
        recipe, _, _ = _packet(ticker)
        policy = _policy(ticker, recipe)
        assert policy["baseline_binding"]["source_path"] == recipe["provenance"]["source_path"]
        assert policy["approved_sensitivities"]["multiples"]
        assert policy["ev_debt_bridge"] is False
        assert "2026-06-30" not in json.dumps(policy)
        assert all("earnings" not in key or "amount" not in key for key in policy)


def test_missing_prior_fiscal_year_cannot_be_replaced_with_older_earnings():
    recipe, packet, _ = _packet('GM')
    damaged = copy.deepcopy(packet)
    for concepts in damaged['companyfacts']['facts'].values():
        for concept in concepts.values():
            for unit, rows in concept.get('units', {}).items():
                concept['units'][unit] = [row for row in rows if row.get('end') != '2025-12-31']
    with pytest.raises(ValueError, match='not contiguous'):
        bind_earnings_recipe(_policy('GM', recipe), recipe, damaged, cutoff='2026-08-14')


def test_dhi_current_formula_is_source_arithmetic_not_target_fitting() -> None:
    recipe, packet, _ = _packet("DHI")
    result = bind_earnings_recipe(_policy("DHI", recipe), recipe, packet, cutoff="2026-08-14")
    reconstruction = result["source_ledger"]["current_earnings_reconstruction"]
    expected = reconstruction["fy"]["value"] + reconstruction["current_ytd"]["value"] - reconstruction["prior_ytd"]["value"]
    assert reconstruction["value"] == expected
    mutated = copy.deepcopy(packet)
    for row in mutated["companyfacts"]["facts"]["us-gaap"]["WeightedAverageNumberOfDilutedSharesOutstanding"]["units"]["shares"]:
        if row.get("accn") == packet["_selected_controlling_filing"]["accession"] and row.get("end") == packet["_selected_controlling_filing"]["period_end"] and row.get("start") == packet["_selected_controlling_filing"]["period_start"]:
            row["val"] += 100_000_000
    changed = bind_earnings_recipe(_policy("DHI", recipe), recipe, mutated, cutoff="2026-08-14")
    assert changed["replay"]["base"] != result["replay"]["base"]


def test_changed_selected_period_cannot_reuse_old_quarter_or_h1() -> None:
    recipe, packet, _ = _packet("GM")
    packet["_selected_controlling_filing"] = {**packet["_selected_controlling_filing"], "period_end": "2026-03-31"}
    with pytest.raises(ValueError, match="eligible|selected|period"):
        bind_earnings_recipe(_policy("GM", recipe), recipe, packet, cutoff="2026-08-14")
