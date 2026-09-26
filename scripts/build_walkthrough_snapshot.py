"""Export a small, dated public demo. Never use the loose artifacts directory.

Run from the repository root: PYTHONPATH=backend python3 scripts/build_walkthrough_snapshot.py [--check]
"""
import argparse
import json
from pathlib import Path

from app.us_valuation.calculator import calculate, calculator_view
from app.us_valuation.catalog import load_catalog

ROOT = Path(__file__).resolve().parents[1]
VERSION = "US-RESET-2026-08-14-B01-B10-1.0"
OUTPUT = ROOT / "frontend/src/walkthrough/snapshot.json"


def build_snapshot():
    catalog = load_catalog(ROOT / "backend/app/data/us_valuation_catalogs" / VERSION)
    assert catalog.included_batches == tuple(range(1, 11))
    assert len(catalog.entries) == 100
    artifact = json.loads(catalog.verify_artifact("AAPL").read_text())
    view = calculator_view(artifact)
    defaults = view["defaults"]
    scenarios = artifact["scenario_range"]
    assert [round(scenarios[k], 2) for k in ("low", "base", "high")] == [79.80, 103.33, 123.16]
    samples = []
    for step in range(25):
        growth = defaults["initial_growth"] + (0.12 - defaults["initial_growth"]) * step / 24
        calculation = calculate(artifact, overrides={"initial_growth": growth}, manual_price=None)
        samples.append({"growth": growth, "values": calculation["result"]})
    assert samples[0]["values"] == view["baseline_result"]
    return {
        "schemaVersion": 1,
        "catalogVersion": catalog.version,
        "manifestSha256": catalog.manifest_sha256,
        "artifactSha256": catalog.entry_by_ticker["AAPL"].artifact_sha256,
        "valuationDate": artifact["valuation_date"],
        "company": {"name": artifact["issuer"]["issuer_name"], "ticker": "AAPL", "sector": artifact["issuer"]["finsight_sector"], "logo": "/logos/apple.svg"},
        "scenarios": {k: scenarios[k] for k in ("low", "base", "high")},
        "assumptions": defaults,
        "assumptionFields": view["editable_assumptions"],
        "model": artifact["primary_valuation_method"],
        "filing": artifact["source_financial_statement"],
        "reliability": artifact["reliability"],
        "reviewState": artifact["automated_review"]["publication_state"],
        "calculatorDescription": "Baseline-calibrated sensitivity preview; not a full model rerun. Filing facts and the capital bridge stay locked.",
        "calculatorSamples": samples,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build_snapshot(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        assert OUTPUT.read_text() == payload, "Snapshot differs from the confirmed catalog/calculator; regenerate and review."
        print("PASS: catalog hashes, Batches 01–10, exact scenarios and all 25 calculator samples replay.")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(payload)
        print(f"Generated {OUTPUT}")
