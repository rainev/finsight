"""WDC cyclical refresh source/identity gates."""

import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_cyclical_policy import (
    CyclicalRefreshError,
    bind_and_evaluate_cyclical_recipe,
    compile_cyclical_policy,
)
from app.us_valuation.calculation_recipe import evaluate_recipe


ROOT = Path(__file__).parents[2]
OUTPUT = ROOT / "output"


def _packets():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/WDC.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "WDC")
    wdc_root = OUTPUT / "batch-01-controlled/sources/WDC"
    stx_root = OUTPUT / "batch-30-sec-source-packets-20260901/STX"
    packet = {"submissions": json.loads((wdc_root / "submissions.json").read_text()), "companyfacts": json.loads((wdc_root / "companyfacts.json").read_text())}
    peer = {"submissions": json.loads((stx_root / "submissions.json").read_text()), "companyfacts": json.loads((stx_root / "companyfacts.json").read_text())}
    structural = json.loads((OUTPUT / "batch-01-controlled/structural-shadow-run-b/WDC/structural-filing.json").read_text())
    return recipe, entry, packet, peer, structural


def test_compile_policy_keeps_peer_and_scope_rules_without_baseline_amounts():
    recipe, entry, _, _, _ = _packets()
    policy = compile_cyclical_policy(recipe, entry)
    encoded = json.dumps(policy, sort_keys=True)
    assert policy["peer_ticker"] == "STX"
    assert policy["approved_policy"]["issuer_weighting"].startswith("equal issuer")
    assert "12919000000" not in encoded
    assert "0001628280-26-057139" not in encoded


def test_cached_wdc_stx_run_stops_on_real_wdc_cik_identity_gate():
    recipe, entry, packet, peer, structural = _packets()
    policy = compile_cyclical_policy(recipe, entry)
    with pytest.raises(CyclicalRefreshError, match="CIK identity"):
        bind_and_evaluate_cyclical_recipe(
            policy,
            recipe,
            packet,
            peer_packet=peer,
            structural_packet=structural,
            cutoff="2026-08-14",
        )


def test_peer_packet_identity_is_checked_before_cyclical_evaluation():
    recipe, entry, packet, peer, structural = _packets()
    policy = compile_cyclical_policy(recipe, entry)
    peer["submissions"]["cik"] = "0000000000"
    with pytest.raises(CyclicalRefreshError, match="STX source packet CIK"):
        bind_and_evaluate_cyclical_recipe(
            policy,
            recipe,
            packet,
            peer_packet=peer,
            structural_packet=structural,
            cutoff="2026-08-14",
        )


def test_new_captured_wdc_packet_rebounds_through_pure_cyclical_engine():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/WDC.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "WDC")
    captured = json.loads((OUTPUT / "us-refresh-runtime/acquisitions/0a0a47feb71d0ecdf4f4f1cc82bbbab937dc31f55876e119a3a97feb4d7e3c3d/packets/WDC.json").read_text())["packet"]
    peer_root = OUTPUT / "batch-30-sec-source-packets-20260901/STX"
    peer = {"submissions": json.loads((peer_root / "submissions.json").read_text()), "companyfacts": json.loads((peer_root / "companyfacts.json").read_text())}
    policy = compile_cyclical_policy(recipe, entry)
    with pytest.raises(CyclicalRefreshError, match="deferred_revenue_current:2026-07-03") as raised:
        bind_and_evaluate_cyclical_recipe(
            policy,
            recipe,
            captured,
            peer_packet=peer,
            structural_packet=captured["structural_filing"],
            cutoff="2026-09-08",
        )
    assert "deferred_revenue_current:2025-06-27" in raised.value.source_review["missing_components"]
    assert evaluate_recipe(recipe)["range"] == recipe["replay"]


def test_captured_wdc_interim_rebuilds_ttm_from_annual_and_comparable_ytd():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/WDC.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "WDC")
    base = OUTPUT / "us-refresh-runtime/acquisitions/94162fd03b5521efb7765371204f98c34b229de7fc84f99463ae4eef1fa36ef1/packets"
    captured = json.loads((base / "WDC.json").read_text())["packet"]
    peer = json.loads((base / "STX.json").read_text())["packet"]
    policy = compile_cyclical_policy(recipe, entry)
    with pytest.raises(CyclicalRefreshError, match="deferred_revenue_current:2026-04-03") as raised:
        bind_and_evaluate_cyclical_recipe(
            policy,
            recipe,
            captured,
            peer_packet=peer,
            structural_packet=captured["structural_filing"],
            cutoff="2026-05-01",
        )
    assert "deferred_revenue_current:2025-06-27" in raised.value.source_review["missing_components"]
    assert evaluate_recipe(recipe)["range"] == recipe["replay"]


def test_wdc_positive_preferred_shares_with_zero_claim_are_rejected():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/WDC.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "WDC")
    captured = json.loads((OUTPUT / "us-refresh-runtime/acquisitions/0a0a47feb71d0ecdf4f4f1cc82bbbab937dc31f55876e119a3a97feb4d7e3c3d/packets/WDC.json").read_text())["packet"]
    peer_root = OUTPUT / "batch-30-sec-source-packets-20260901/STX"
    peer = {"submissions": json.loads((peer_root / "submissions.json").read_text()), "companyfacts": json.loads((peer_root / "companyfacts.json").read_text())}
    structural = json.loads(json.dumps(captured["structural_filing"]))
    structural["facts"].append({"local_name": "PreferredStockSharesOutstanding", "qname": "us-gaap:PreferredStockSharesOutstanding", "namespace": "http://fasb.org/us-gaap/2026", "unit": "xbrli:shares", "value": 1.0, "period_start": None, "period_end": "2026-07-03", "source_accession": "0001628280-26-057139", "entity_identifier": "0000106040", "dimensions": []})
    with pytest.raises(CyclicalRefreshError, match="preferred shares"):
        bind_and_evaluate_cyclical_recipe(compile_cyclical_policy(recipe, entry), recipe, captured, peer_packet=peer, structural_packet=structural, cutoff="2026-09-08")


def test_wdc_new_positive_debt_class_must_reconcile_to_aggregate():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/WDC.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "WDC")
    captured = json.loads((OUTPUT / "us-refresh-runtime/acquisitions/0a0a47feb71d0ecdf4f4f1cc82bbbab937dc31f55876e119a3a97feb4d7e3c3d/packets/WDC.json").read_text())["packet"]
    peer_root = OUTPUT / "batch-30-sec-source-packets-20260901/STX"
    peer = {"submissions": json.loads((peer_root / "submissions.json").read_text()), "companyfacts": json.loads((peer_root / "companyfacts.json").read_text())}
    structural = json.loads(json.dumps(captured["structural_filing"]))
    structural["facts"].append({"local_name": "ShortTermBorrowings", "qname": "us-gaap:ShortTermBorrowings", "namespace": "http://fasb.org/us-gaap/2026", "unit": "USD", "value": 1.0, "period_start": None, "period_end": "2026-07-03", "source_accession": "0001628280-26-057139", "entity_identifier": "0000106040", "dimensions": []})
    with pytest.raises(CyclicalRefreshError, match="debt aggregate"):
        bind_and_evaluate_cyclical_recipe(compile_cyclical_policy(recipe, entry), recipe, captured, peer_packet=peer, structural_packet=structural, cutoff="2026-09-08")


def test_wdc_conflicting_cover_share_facts_are_rejected():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/WDC.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "WDC")
    captured = json.loads((OUTPUT / "us-refresh-runtime/acquisitions/0a0a47feb71d0ecdf4f4f1cc82bbbab937dc31f55876e119a3a97feb4d7e3c3d/packets/WDC.json").read_text())["packet"]
    peer_root = OUTPUT / "batch-30-sec-source-packets-20260901/STX"
    peer = {"submissions": json.loads((peer_root / "submissions.json").read_text()), "companyfacts": json.loads((peer_root / "companyfacts.json").read_text())}
    structural = json.loads(json.dumps(captured["structural_filing"]))
    row = next(row for row in structural["facts"] if row.get("local_name") == "EntityCommonStockSharesOutstanding" and row.get("period_end") == "2026-08-07")
    structural["facts"].append({**row, "value": float(row["value"]) + 1.0})
    with pytest.raises(CyclicalRefreshError, match="cover-page shares conflict"):
        bind_and_evaluate_cyclical_recipe(compile_cyclical_policy(recipe, entry), recipe, captured, peer_packet=peer, structural_packet=structural, cutoff="2026-09-08")


def test_complete_deferred_zero_is_test_only_and_allows_execution():
    recipe = json.loads((OUTPUT / "us-refresh-runtime/recipes/WDC.json").read_text())
    registry = json.loads((OUTPUT / "us-refresh-runtime/registry.json").read_text())
    entry = next(row for row in registry["entries"] if row["ticker"] == "WDC")
    captured = json.loads((OUTPUT / "us-refresh-runtime/acquisitions/0a0a47feb71d0ecdf4f4f1cc82bbbab937dc31f55876e119a3a97feb4d7e3c3d/packets/WDC.json").read_text())["packet"]
    peer_root = OUTPUT / "batch-30-sec-source-packets-20260901/STX"
    peer = {"submissions": json.loads((peer_root / "submissions.json").read_text()), "companyfacts": json.loads((peer_root / "companyfacts.json").read_text())}
    packet = json.loads(json.dumps(captured))
    facts = packet["companyfacts"].setdefault("facts", {}).setdefault("us-gaap", {})
    facts["ContractWithCustomerLiabilityCurrent"] = {"units": {"USD": [{"accn": "0001628280-26-057139", "end": "2026-07-03", "val": 0, "filed": "2026-08-14", "form": "10-K"}, {"accn": "0001628280-26-057139", "end": "2025-06-27", "val": 0, "filed": "2026-08-14", "form": "10-K"}]}}
    result = bind_and_evaluate_cyclical_recipe(compile_cyclical_policy(recipe, entry), recipe, packet, peer_packet=peer, structural_packet=packet["structural_filing"], cutoff="2026-09-08")
    assert result["source_ledger"]["nwc_review"]["status"] == "complete_trade_nwc"
