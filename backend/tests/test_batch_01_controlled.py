"""Hermetic contract tests for the controlled Batch 01 outcome runner."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.batch_01 import BATCH_01_MANIFEST
from app.us_valuation.economic_routing import load_batch_01_routing_records


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/run_batch_01_controlled.py"
SPEC = importlib.util.spec_from_file_location("batch_01_controlled_test", SCRIPT)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _packet(root: Path) -> None:
    issuer = BATCH_01_MANIFEST[0]
    packet = root / issuer.ticker
    packet.mkdir(parents=True)
    submissions = {
        "cik": issuer.cik,
        "name": issuer.issuer_name,
        "tickers": [issuer.ticker],
        "filings": {"recent": {}},
    }
    facts = {"cik": issuer.cik, "entityName": issuer.issuer_name, "facts": {}}
    hashes = {}
    for filename, value in (
        ("submissions.json", submissions),
        ("companyfacts.json", facts),
    ):
        raw = runner._json_bytes(value)
        (packet / filename).write_bytes(raw)
        hashes[filename] = hashlib.sha256(raw).hexdigest()
    manifest = {
        "valuation_date": "2026-08-14",
        "issuer": {
            "ticker": issuer.ticker,
            "cik": issuer.cik,
            "issuer_name": issuer.issuer_name,
        },
        "packet_payload_sha256": hashes,
    }
    (packet / "source-manifest.json").write_bytes(runner._json_bytes(manifest))


def test_runner_keeps_denominator_and_forces_unvalidated_route_withheld(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sources"
    output = tmp_path / "out"
    _packet(source)
    legacy = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "app/data/us_valuations/AAPL.json"
        ).read_text()
    )

    def build(**kwargs):
        return {
            "model_policy": {"primary": "fcff_dcf"},
            "scenario_range": {"low": 100.0, "base": 120.0, "high": 140.0},
            "review": {"publication_state": "review_required"},
        }

    def serialize(*args, **kwargs):
        return sanitize_public_artifact(legacy)

    summary = runner.run_batch(
        source_root=source,
        output_root=output,
        manifest=BATCH_01_MANIFEST[:1],
        routing_records=load_batch_01_routing_records()[:1],
        blocker_policy={"AAPL": ["Test source blocker."]},
        build=build,
        serialize=serialize,
    )

    assert summary["attempted_count"] == 1
    assert summary["numeric_count"] == 0
    assert summary["withheld_count"] == 1
    assert summary["serving_artifacts_changed"] is False
    case = summary["cases"][0]
    assert case["outcome"] == "withheld"
    assert case["base"] is None
    assert case["diagnostic_comparison"]["base"] == 120.0
    assert case["diagnostic_comparison"]["not_a_controlled_reset_value"] is True
    public = json.loads((output / "staged-public/AAPL.json").read_text())
    assert public["review"]["publication_state"] == "withheld"
    assert public["scenario_range"]["base"] is None
    assert "Test source blocker." in public["review"]["errors"]

    first = (output / "batch-report.json").read_bytes()
    runner.run_batch(
        source_root=source,
        output_root=output,
        manifest=BATCH_01_MANIFEST[:1],
        routing_records=load_batch_01_routing_records()[:1],
        blocker_policy={"AAPL": ["Test source blocker."]},
        build=build,
        serialize=serialize,
    )
    assert (output / "batch-report.json").read_bytes() == first


def test_runner_rejects_output_inside_source_root(tmp_path: Path) -> None:
    source = tmp_path / "sources"
    source.mkdir()
    with pytest.raises(ValueError, match="separate"):
        runner._validate_paths(source, source / "out")
