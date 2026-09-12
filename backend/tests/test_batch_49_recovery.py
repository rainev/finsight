import json
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from app.us_valuation.batch_49 import BATCH_49_MANIFEST
from app.us_valuation.batch_49_recovery import ATTEMPTED_TICKERS, RECOVERY_VERSION, recover_batch_49_withheld

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
INITIAL = ROOT / "output/batch-49-history-run-e-20260912"


@lru_cache(None)
def recovered():
    initial = json.loads((INITIAL / "generated/AVB/valuation-private.json").read_text())["history_backed"]
    return recover_batch_49_withheld(initial=initial)


def test_only_avb_consumes_one_attempt_and_remains_withheld() -> None:
    assert ATTEMPTED_TICKERS == ("AVB",)
    row = recovered()
    attempt = row["source_ledger"]["recovery_attempt"]
    assert row["model_version"] == RECOVERY_VERSION and row["availability_type"] == "not_available"
    assert row["scenario_range"] == {"low": None, "base": None, "high": None}
    assert attempt["attempt_number"] == 1 and attempt["decision"] == "withheld"
    assert attempt["hard_blockers"] == ("MAJOR_EVENT_UNBOUNDED", "MODEL_UNSUPPORTED")
    assert attempt["zero_substitution_used"] is False


def test_standalone_and_transaction_diagnostics_are_exact_and_private() -> None:
    row = recovered()["source_ledger"]
    standalone, transaction = row["standalone_preclose_diagnostic"], row["transaction_diagnostic"]
    assert not standalone["publication_eligible"]
    assert standalone["h1_core_ffo_per_share"] == 5.69
    assert standalone["h1_asset_preservation_capex"] == 106_450_000
    assert standalone["h1_noi_enhancing_capex"] == 63_714_000
    assert standalone["capital_source"]["reported_apartment_homes"] == 85_739
    assert standalone["capital_source"]["reported_asset_preservation_capex"] == 106_450_000
    assert standalone["annualized_preservation_capex_per_share"] == pytest.approx(1.5064697640161462)
    assert standalone["normalized_affo_proxy_sensitivity"] == pytest.approx((8.971856073987379, 9.873530235983855))
    assert standalone["rate_only_values_using_preservation_proxy"] == pytest.approx({"bear": 129.94839794456178, "base": 138.910356423497, "bull": 149.20001245486728})
    assert transaction["fixed_exchange_ratio"] == 2.793 and transaction["expected_close"] == "2026-08-17"
    assert not transaction["used_as_intrinsic_value"] and not transaction["post_cutoff_facts_used"]
    assert not transaction["combined_affo_available"] and not transaction["final_closing_bridge_available"]


def test_public_avb_remains_withheld_and_private_safe() -> None:
    from app.us_valuation.calculator import calculator_view
    from run_batch_49_history import _public

    issuer = next(row for row in BATCH_49_MANIFEST if row.ticker == "AVB")
    public = _public(issuer, recovered())
    assert public["availability_type"] == "not_available" and public["scenario_range"]["base"] is None
    assert public["model_policy"]["primary"] == "affo_dcf" and not calculator_view(public)["can_calculate"]
    encoded = json.dumps(public)
    for key in ("recovery_attempt", "standalone_preclose_diagnostic", "transaction_diagnostic", "reported_inputs", "source_ledger"):
        assert key not in encoded


def test_recovery_runner_preserves_other_issuers_and_bookkeeping(tmp_path: Path) -> None:
    from run_batch_49_recovery import run

    report = run(initial_root=INITIAL, output_root=tmp_path / "recovery")
    assert (report["recovery_attempt_count"], report["recovered_to_conditional_count"], report["still_withheld_count"]) == (1, 0, 1)
    assert (report["pass_count"], report["conditional_count"], report["withheld_count"], report["numeric_count"]) == (0, 9, 1, 9)
    assert report["attempted_recovery_tickers"] == ["AVB"] and report["still_withheld_tickers"] == ["AVB"]
    assert not report["serving_artifacts_changed"] and not report["watchlist_changed"] and not report["withheld_register_changed"]
    assert (tmp_path / "recovery/staged-public/REG.json").read_bytes() == (INITIAL / "staged-public/REG.json").read_bytes()
    avb = json.loads((tmp_path / "recovery/staged-public/AVB.json").read_text())
    assert avb["public_assumptions"]["forecast_policy_version"] == RECOVERY_VERSION
    assert avb["review"]["confidence_grade"] == "withheld"
