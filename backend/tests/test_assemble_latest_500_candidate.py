from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.assemble_latest_500_candidate import _fingerprints, _merge_source_reports, assemble
from app.us_valuation.catalog import load_catalog_version, sha256_bytes


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "output/latest-universe-20260919/runtime"
DISCOVERY = ROOT / "output/latest-universe-20260919/final-discovery/capture-report.json"


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    manifest = json.loads((RUNTIME / "baseline/manifest.json").read_text())
    fingerprints = _fingerprints(RUNTIME)
    unchanged_rows = []
    for entry in manifest["entries"]:
        recipe = RUNTIME / "recipes" / f"{entry['ticker']}.json"
        row = {
            "ticker": entry["ticker"],
            "status": "verified_unchanged" if recipe.is_file() else "prior_unavailable",
            "recommendation": "retain approved dated baseline",
            "baseline_artifact_sha256": entry["artifact_sha256"],
        }
        if recipe.is_file():
            row["baseline_recipe_sha256"] = hashlib.sha256(recipe.read_bytes()).hexdigest()
        unchanged_rows.append(row)
    unchanged = tmp_path / "unchanged.json"
    unchanged.write_bytes(json.dumps({"schema_version": "TEST-UNCHANGED-1", **fingerprints, "rows": unchanged_rows}).encode())
    targeted = tmp_path / "targeted.json"
    targeted.write_bytes(json.dumps({"schema_version": "TEST-TARGETED-1", "companies": {}}).encode())
    source = tmp_path / "source.json"
    source.write_bytes(json.dumps({
        "scope": "cached binding verification, not publication readiness",
        **{key: fingerprints[key] for key in ("registry_sha256", "policy_sha256", "implementation_sha256")},
        "source_capture_snapshot": "test-snapshot",
        "evidence_sha256": {},
        "rows": [],
    }).encode())
    return source, targeted, unchanged


def test_assemble_requires_explicit_unchanged_and_preserves_500_baseline(tmp_path: Path) -> None:
    source, targeted, unchanged = _write_inputs(tmp_path)
    result = assemble(
        runtime_root=RUNTIME,
        discovery_report=DISCOVERY,
        source_validation_report=source,
        targeted_reviews=targeted,
        unchanged_verification=unchanged,
        output_root=tmp_path / "release-candidate",
    )
    root = Path(result["candidate_root"])
    catalog = load_catalog_version(root)
    assert len(catalog.entries) == 500
    assert len(list((root / "recipes").glob("*.json"))) == 474
    assert not (root / "active.json").exists()
    assert result["activated"] is False
    assert result["counts"]["verified_unchanged"] == 474
    assert result["counts"]["prior_unavailable_verified"] == 26
    report = json.loads((root / "assembly-report.json").read_text())
    assert len(report["rows"]) == 500
    assert report["input_fingerprints"]["baseline_manifest_sha256"] == catalog.manifest["base_manifest_sha256"]
    rows = {row["ticker"]: row for row in report["rows"]}
    assert any("historical-only" in row["recommendation"] for row in rows.values() if row["outcome"] == "verified_unchanged")
    assert "no current numeric value" in rows[next(t for t, row in rows.items() if row["outcome"] == "prior_unavailable_verified")]["recommendation"]


def test_assemble_fails_on_source_validation_fingerprint_drift(tmp_path: Path) -> None:
    source, targeted, unchanged = _write_inputs(tmp_path)
    payload = json.loads(source.read_text())
    payload["policy_sha256"] = "0" * 64
    source.write_text(json.dumps(payload))
    result = assemble(
        runtime_root=RUNTIME,
        discovery_report=DISCOVERY,
        source_validation_report=source,
        targeted_reviews=targeted,
        unchanged_verification=unchanged,
        output_root=tmp_path / "release-candidate",
    )
    report = json.loads((Path(result["candidate_root"]) / "assembly-report.json").read_text())
    assert report["source_fingerprint_summary"]["global_policy_fingerprint_mismatch_count"] == 1


def test_source_report_merge_rejects_duplicate_disagreement(tmp_path: Path) -> None:
    fingerprints = _fingerprints(RUNTIME)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    common = {
        "registry_sha256": fingerprints["registry_sha256"],
        "implementation_sha256": fingerprints["implementation_sha256"],
        "policy_sha256": fingerprints["policy_sha256"],
        "evidence_sha256": {"AAPL": "a" * 64},
    }
    first.write_text(json.dumps({**common, "rows": [{"ticker": "AAPL", "status": "cached_source_bound", "current_range": {"low": 1, "base": 2, "high": 3}}]}))
    second.write_text(json.dumps({**common, "rows": [{"ticker": "AAPL", "status": "cached_source_bound", "current_range": {"low": 1, "base": 2, "high": 4}}]}))
    with pytest.raises(ValueError, match="disagree"):
        _merge_source_reports([first, second], fingerprints)
