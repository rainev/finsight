from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
import verify_latest_unchanged as verifier
from app.us_valuation.calculation_recipe import evaluate_recipe


def _recipe(ticker: str, source_accession: str) -> dict:
    scenarios = {}
    for name, growth, wacc in (("bear", -0.02, 0.11), ("base", 0.0, 0.10), ("bull", 0.02, 0.09)):
        scenarios[name] = {
            "engine": "enterprise_cash_fcff",
            "inputs": {
                "cash_fcff": 100.0,
                "initial_growth": growth,
                "terminal_growth": 0.01,
                "wacc": wacc,
                "cash_and_investments": 10.0,
                "interest_bearing_debt": 1.0,
                "preferred_equity": 0.0,
                "noncontrolling_interests": 0.0,
                "diluted_shares": 10.0,
                "forecast_years": 8,
            },
        }
    recipe = {
        "schema_version": "FINSIGHT-CALCULATION-RECIPE-1",
        "ticker": ticker,
        "recipe_version": f"test-{ticker}",
        "evidence_cutoff": "2026-08-14",
        "source_accession": source_accession,
        "scenarios": scenarios,
        "editable": {},
    }
    recipe["replay"] = evaluate_recipe(recipe)["range"]
    return recipe


def _write_fixture(tmp_path: Path, *, event: bool = False, changed: bool = False) -> tuple[Path, Path, Path]:
    runtime = tmp_path / "runtime"
    baseline = runtime / "baseline"
    artifacts = baseline / "artifacts"
    recipes = runtime / "recipes"
    latest = tmp_path / "latest"
    sec = latest / "final-discovery" / "sec-cache"
    for path in (artifacts, recipes, sec):
        path.mkdir(parents=True)
    entries = []
    discovery_rows = []
    for index, ticker in enumerate(("AAA", "BBB"), start=1):
        cik = f"000000000{index}"
        accession = f"{cik}-26-000001"
        recipe = _recipe(ticker, accession)
        artifact = {"ticker": ticker, "scenario_range": dict(recipe["replay"])}
        recipe_path = recipes / f"{ticker}.json"
        artifact_path = artifacts / f"{ticker}.json"
        recipe_path.write_text(json.dumps(recipe, sort_keys=True))
        artifact_path.write_text(json.dumps(artifact, sort_keys=True))
        entries.append({"ticker": ticker, "cik": cik, "baseline_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest()})
        recent = {
            "accessionNumber": [accession],
            "filingDate": ["2026-07-31"],
            "reportDate": ["2026-07-31"],
            "form": ["10-Q"],
            "items": [""],
            "primaryDocument": [f"{ticker.lower()}-20260731.htm"],
        }
        if event and ticker == "AAA":
            recent["accessionNumber"].append(f"{cik}-26-000002")
            recent["filingDate"].append("2026-09-01")
            recent["reportDate"].append("2026-09-01")
            recent["form"].append("8-K")
            recent["items"].append("8.01")
            recent["primaryDocument"].append("event.htm")
        (sec / f"CIK{cik}-submissions.json").write_text(json.dumps({"cik": int(cik), "tickers": [ticker], "filings": {"recent": recent}}))
        discovery_rows.append({
            "ticker": ticker,
            "cik": cik,
            "changed_regular": changed and ticker == "BBB",
            "latest_regular": {"accessionNumber": accession, "filingDate": "2026-07-31", "reportDate": "2026-07-31", "form": "10-Q"},
            "latest_annual": {"accessionNumber": f"{cik}-25-000001", "filingDate": "2025-10-31", "reportDate": "2025-10-31", "form": "10-K"},
            "submissions_sha256": "a" * 64,
        })
    registry = {"schema_version": "test", "baseline_manifest_sha256": "", "entries": entries}
    manifest = {"schema_version": "test", "entries": [{"ticker": row["ticker"], "artifact_sha256": row["baseline_sha256"]} for row in entries]}
    manifest_path = baseline / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    registry["baseline_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    (runtime / "registry.json").write_text(json.dumps(registry, sort_keys=True))
    (runtime / "refresh-policies.json").write_text("{}")
    (latest / "discovery-report.json").write_text(json.dumps({"cutoff": "2026-09-19", "expected_count": 2, "rows": discovery_rows}, sort_keys=True))
    discovery_hash = hashlib.sha256((latest / "discovery-report.json").read_bytes()).hexdigest()
    capture_input = {"schema_version": "FINSIGHT-LATEST-500-CAPTURE-1", "cutoff": "2026-09-19", "expected_count": 2, "discovery_sha256": discovery_hash, "retrieval_snapshot_timestamp": "2026-09-18T20:21:38Z"}
    (latest / "capture-input.json").write_text(json.dumps(capture_input, sort_keys=True))
    (latest / "capture-report.json").write_text(json.dumps({"cutoff": "2026-09-19", "retrieval_snapshot_timestamp": capture_input["retrieval_snapshot_timestamp"], "rows": []}, sort_keys=True))
    return runtime, latest, tmp_path / "report.json"


def test_two_identity_fixture_verifies_unchanged_and_writes_hashed_report(tmp_path, monkeypatch):
    monkeypatch.setattr(verifier, "EXPECTED_COUNT", 2)
    runtime, latest, output = _write_fixture(tmp_path)
    report = verifier.verify_latest_unchanged(runtime_root=runtime, latest_root=latest, output_path=output)
    assert report["identity_count"] == 2
    assert report["counts"]["verified_unchanged"] == 2
    assert output.is_file()
    on_disk = json.loads(output.read_bytes())
    recorded_hash = on_disk.pop("report_sha256")
    assert recorded_hash == hashlib.sha256(verifier.canonical_json_bytes(on_disk)).hexdigest()


def test_fixture_event_without_capture_is_acquisition_pending_not_verified(tmp_path, monkeypatch):
    monkeypatch.setattr(verifier, "EXPECTED_COUNT", 2)
    runtime, latest, output = _write_fixture(tmp_path, event=True)
    report = verifier.verify_latest_unchanged(runtime_root=runtime, latest_root=latest, output_path=output)
    row = next(row for row in report["rows"] if row["ticker"] == "AAA")
    assert row["state"] == "acquisition_pending_or_failed"


def test_fixture_changed_regular_without_capture_is_acquisition_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(verifier, "EXPECTED_COUNT", 2)
    runtime, latest, output = _write_fixture(tmp_path, changed=True)
    report = verifier.verify_latest_unchanged(runtime_root=runtime, latest_root=latest, output_path=output)
    row = next(row for row in report["rows"] if row["ticker"] == "BBB")
    assert row["state"] == "acquisition_pending_or_failed"


def test_ownership_amendment_without_capture_is_source_identified_non_economic(tmp_path, monkeypatch):
    monkeypatch.setattr(verifier, "EXPECTED_COUNT", 2)
    runtime, latest, output = _write_fixture(tmp_path)
    sec_path = latest / "final-discovery" / "sec-cache" / "CIK0000000001-submissions.json"
    submissions = json.loads(sec_path.read_bytes())
    recent = submissions["filings"]["recent"]
    for key, value in {
        "accessionNumber": "0000000001-26-000099",
        "filingDate": "2026-09-04",
        "reportDate": "",
        "form": "SCHEDULE 13G/A",
        "items": "",
        "primaryDocument": "ownership-amendment.xml",
    }.items():
        recent[key].append(value)
    sec_path.write_text(json.dumps(submissions))
    report = verifier.verify_latest_unchanged(runtime_root=runtime, latest_root=latest, output_path=output)
    row = next(row for row in report["rows"] if row["ticker"] == "AAA")
    assert row["state"] == "verified_unchanged"
    assert row["disclosure_impact"]["policy_version"] == "US-DISCLOSURE-IMPACT-1"
    assert row["disclosure_impact"]["records"][0]["form"] == "SCHEDULE 13G/A"


def test_mixed_ownership_amendment_and_current_report_stays_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(verifier, "EXPECTED_COUNT", 2)
    runtime, latest, output = _write_fixture(tmp_path, event=True)
    sec_path = latest / "final-discovery" / "sec-cache" / "CIK0000000001-submissions.json"
    submissions = json.loads(sec_path.read_bytes())
    recent = submissions["filings"]["recent"]
    for key, value in {
        "accessionNumber": "0000000001-26-000099",
        "filingDate": "2026-09-04",
        "reportDate": "",
        "form": "SCHEDULE 13G/A",
        "items": "",
        "primaryDocument": "ownership-amendment.xml",
    }.items():
        recent[key].append(value)
    sec_path.write_text(json.dumps(submissions))
    report = verifier.verify_latest_unchanged(runtime_root=runtime, latest_root=latest, output_path=output)
    row = next(row for row in report["rows"] if row["ticker"] == "AAA")
    assert row["state"] == "acquisition_pending_or_failed"
    assert "disclosure_impact" not in row


def test_material_form_classifier_covers_prospectus_and_current_reports():
    assert verifier._material_form("8-K")
    assert verifier._material_form("424B5")
    assert verifier._material_form("FWP")
    assert verifier._material_form("S-3")
    assert verifier._material_form("SC13E3")
    assert not verifier._material_form("4")


def test_employee_plan_registration_is_not_treated_as_issued_current_dilution():
    from app.us_valuation.refresh_disclosure_impact import classify_non_economic_amendments

    result = classify_non_economic_amendments(
        [{
            "accessionNumber": "0000000001-26-000099",
            "filingDate": "2026-09-04",
            "form": "S-8",
            "items": "",
            "primaryDocument": "employee-plan.htm",
        }],
        prior_cutoff="2026-08-14",
        cutoff="2026-09-19",
        submissions_sha256="a" * 64,
        changed_regular=False,
    )
    assert result is not None
    assert result["classification"] == "non_economic_ownership_insider_or_plan_registration"
