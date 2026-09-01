from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.activate_us_valuation_catalog import activate
from scripts.build_us_valuation_catalog import build_catalog
from app.routers import us_valuations as router
from app.us_valuation.calculator import calculator_view
from app.us_valuation.catalog import (
    CatalogIntegrityError,
    load_active_catalog,
    load_catalog_version,
)


ROOT = Path(__file__).resolve().parents[2]
CATALOGS = ROOT / "backend" / "app" / "data" / "us_valuation_catalogs"
RESET = CATALOGS / "US-RESET-2026-08-14-B01-B10-1.0"
LEGACY = CATALOGS / "archive" / "legacy-206-2026-08-26"


def test_active_reset_catalog_has_exact_confirmed_denominator() -> None:
    catalog = load_active_catalog(CATALOGS)

    assert catalog.catalog_version == "US-RESET-2026-08-14-B01-B10-1.0"
    assert catalog.universe_version == "US-SP500-ISSUERS-2026-08-14-1.0"
    assert catalog.valuation_date == "2026-08-14"
    assert catalog.included_batches == tuple(range(1, 11))
    assert len(catalog.entries) == 100
    assert len({entry.ticker for entry in catalog.entries}) == 100
    assert len({entry.cik for entry in catalog.entries}) == 100
    assert catalog.manifest["availability_counts"] == {
        "available": 45,
        "conditional_estimate": 51,
        "not_available": 4,
    }
    assert catalog.manifest["publication_counts"] == {
        "review_required": 96,
        "withheld": 4,
    }
    assert all(
        sum(entry.batch == batch for entry in catalog.entries) == 10
        for batch in range(1, 11)
    )


def test_active_catalog_list_detail_and_calculator_contract() -> None:
    listed = router.list_us_valuations()

    assert listed["count"] == listed["artifact_count"] == 100
    assert listed["catalog_version"] == "US-RESET-2026-08-14-B01-B10-1.0"
    assert listed["included_batches"] == list(range(1, 11))
    assert [item["ticker"] for item in listed["items"]] == [
        entry.ticker for entry in router.CATALOG.entries
    ]

    calculator_counts = {True: 0, False: 0}
    for entry in router.CATALOG.entries:
        detail = router.load_generated_result(entry.ticker)
        assert detail["issuer"]["ticker"] == entry.ticker
        assert detail["availability_type"] == entry.availability_type
        can_calculate = calculator_view(detail)["can_calculate"]
        calculator_counts[can_calculate] += 1
        assert can_calculate is (entry.availability_type != "not_available")

    assert calculator_counts == {True: 96, False: 4}


def test_reset_catalog_numeric_and_unavailable_values_match_status() -> None:
    catalog = load_catalog_version(RESET)

    for entry in catalog.entries:
        artifact = json.loads(catalog.artifact_path(entry.ticker).read_text())
        scenario = artifact["scenario_range"]
        if entry.availability_type == "not_available":
            assert scenario["low"] is None
            assert scenario["base"] is None
            assert scenario["high"] is None
        else:
            # Conditional bear cases may use a disclosed limited-liability
            # equity floor; the base and high cases must remain positive.
            assert 0 <= scenario["low"] < scenario["base"] <= scenario["high"]


def test_legacy_archive_preserves_exact_pre_promotion_snapshot() -> None:
    archive = load_catalog_version(LEGACY)

    assert archive.catalog_version == "US-LEGACY-206-2026-08-26-1.0"
    assert len(archive.entries) == 206
    assert archive.manifest["publication_counts"] == {
        "review_required": 88,
        "withheld": 118,
    }
    assert archive.manifest["legacy_source"] == {
        "commit": "670f7cfe07f82a5bc6b3ae56477407131f425b39",
        "git_tree": "81fcc404ef9b25001565f7232324dbefa0b56afa",
        "rollback": "Activate this catalog only in an isolated rollback configuration, then verify every public boundary before serving it.",
    }


def test_catalog_rejects_artifact_hash_drift(tmp_path: Path) -> None:
    target = tmp_path / "catalog"
    shutil.copytree(RESET, target)
    path = target / "artifacts" / "AAPL.json"
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(CatalogIntegrityError, match="hash mismatch"):
        load_catalog_version(target)


def test_catalog_rejects_unlisted_artifact(tmp_path: Path) -> None:
    target = tmp_path / "catalog"
    shutil.copytree(RESET, target)
    shutil.copyfile(
        target / "artifacts" / "AAPL.json",
        target / "artifacts" / "EXTRA.json",
    )

    with pytest.raises(CatalogIntegrityError, match="do not exactly match"):
        load_catalog_version(target, verify_artifacts=False)


def test_active_pointer_binds_manifest_hash(tmp_path: Path) -> None:
    shutil.copytree(RESET, tmp_path / RESET.name)
    active = json.loads((CATALOGS / "active.json").read_text())
    active["manifest_sha256"] = "0" * 64
    (tmp_path / "active.json").write_text(json.dumps(active))

    with pytest.raises(CatalogIntegrityError, match="manifest hash mismatch"):
        load_active_catalog(tmp_path)


def test_extending_catalog_accumulates_base_publication_counts(tmp_path: Path) -> None:
    batch_11 = ROOT / "output/batch-11-recovery/candidate-k/staged-public"
    target = tmp_path / "extended"
    manifest = build_catalog(
        catalog_kind="reset",
        target_root=target,
        catalog_version="TEST-B01-B11",
        universe_version="US-SP500-ISSUERS-2026-08-14-1.0",
        valuation_date="2026-08-14",
        created_at="2026-08-28",
        batch_sources=((11, batch_11, "docs/audit/66-batch-11-recovery-result.md"),),
        base_catalog=RESET,
        expected_count=110,
        expected_availability={
            "available": 47,
            "conditional_estimate": 58,
            "not_available": 5,
        },
        expected_publication={"review_required": 105, "withheld": 5},
    )
    assert manifest["publication_counts"] == {
        "review_required": 105,
        "withheld": 5,
    }


def test_legacy_archive_can_be_selected_in_isolated_rollback(tmp_path: Path) -> None:
    target = tmp_path / "archive" / LEGACY.name
    shutil.copytree(LEGACY, target)

    pointer = activate(
        catalogs_root=tmp_path,
        catalog_path=f"archive/{LEGACY.name}",
        confirmation="ACTIVATE_VERIFIED_US_VALUATION_CATALOG",
        activated_at="2026-08-26",
    )
    rollback = load_active_catalog(tmp_path)

    assert pointer["catalog_version"] == "US-LEGACY-206-2026-08-26-1.0"
    assert rollback.catalog_version == pointer["catalog_version"]
    assert len(rollback.entries) == 206
