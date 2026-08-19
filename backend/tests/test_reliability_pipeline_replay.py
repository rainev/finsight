from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.us_valuation import build_us_valuation
from app.us_valuation.artifacts import public_result
from scripts.run_reliability_pipeline_replay import run_replay, validate_paths


FIXTURES = ROOT / "backend" / "tests" / "fixtures" / "us"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_corpus(tmp_path: Path) -> Path:
    input_root = tmp_path / "input"
    cache = input_root / "sec-cache"
    candidate = input_root / "AAPL"
    cache.mkdir(parents=True)
    candidate.mkdir()
    submissions_path = FIXTURES / "aapl-submissions.json"
    companyfacts_path = FIXTURES / "aapl-companyfacts.json"
    submission_cache = cache / "CIK0000320193-submissions.json"
    companyfacts_cache = cache / "CIK0000320193-companyfacts.json"
    shutil.copyfile(submissions_path, submission_cache)
    shutil.copyfile(companyfacts_path, companyfacts_cache)
    manifest = {
        "status": "test_fixture",
        "records": [
            {
                "cache_file": submission_cache.name,
                "source_url": "https://data.sec.gov/submissions/CIK0000320193.json",
                "sha256": _sha256(submission_cache),
            },
            {
                "cache_file": companyfacts_cache.name,
                "source_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
                "sha256": _sha256(companyfacts_cache),
            },
        ],
    }
    submissions = json.loads(submission_cache.read_text(encoding="utf-8"))
    companyfacts = json.loads(companyfacts_cache.read_text(encoding="utf-8"))
    result = build_us_valuation(
        submissions=submissions,
        companyfacts=companyfacts,
        valuation_date="2026-08-01",
        source_manifest=manifest,
    )
    result["source_manifest"] = manifest
    public = public_result(result, submissions)
    (candidate / "valuation-private.json").write_text(
        json.dumps(result), encoding="utf-8"
    )
    (candidate / "valuation-public-candidate.json").write_text(
        json.dumps(public), encoding="utf-8"
    )
    return input_root


def test_replay_uses_real_build_path_and_emits_denominated_summary(tmp_path: Path) -> None:
    input_root = _make_corpus(tmp_path)
    summary = run_replay(input_root, tmp_path / "output")

    expected = {
        "input_candidate_count",
        "valid_private_count",
        "invalid_input_count",
        "source_verified_count",
        "numeric_before_count",
        "numeric_after_count",
        "reliability_counts",
        "fallback_level_counts",
        "fallback_level_company_counts",
        "accounting_impact_buckets",
        "scenario_movement_buckets",
        "near_boundary_cases",
        "remaining_blocker_counts",
        "source_integrity_failure_count",
        "build_error_count",
        "public_contract_failure_count",
        "unsafe_promotion_count",
        "serving_hash_before",
        "serving_hash_after",
        "serving_artifacts_changed",
        "denominators",
    }
    assert expected.issubset(summary)
    assert summary["input_candidate_count"] == 1
    assert summary["valid_private_count"] == 1
    assert summary["source_verified_count"] == 1
    assert summary["denominators"]["numeric_after_count"] == summary["numeric_after_count"]
    assert summary["serving_artifacts_changed"] is False
    assert (tmp_path / "output" / "replay-report.json").is_file()
    assert (tmp_path / "output" / "replay-report.md").is_file()


def test_public_shaped_candidate_is_invalid_but_remains_in_denominator(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    candidate = input_root / "ADBE"
    candidate.mkdir(parents=True)
    (candidate / "valuation-private.json").write_text(
        json.dumps({"schema_version": "US-PUBLIC-VALUATION-1.0", "ticker": "ADBE"}),
        encoding="utf-8",
    )
    summary = run_replay(input_root, tmp_path / "output")
    assert summary["input_candidate_count"] == 1
    assert summary["invalid_input_count"] == 1
    assert summary["valid_private_count"] == 0


def test_replay_rejects_output_inside_serving_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="serving root"):
        validate_paths(tmp_path, ROOT / "backend" / "app" / "data" / "us_valuations" / "replay")


def test_replay_rejects_source_hash_mismatch(tmp_path: Path) -> None:
    input_root = _make_corpus(tmp_path)
    source = input_root / "sec-cache" / "CIK0000320193-companyfacts.json"
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    summary = run_replay(input_root, tmp_path / "output")
    assert summary["source_integrity_failure_count"] == 1
    assert summary["source_verified_count"] == 0
