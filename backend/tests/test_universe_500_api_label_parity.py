"""Raw stored catalog labels must survive the serving sanitizer unchanged."""

from collections import Counter
import json
from pathlib import Path

from app.us_valuation.artifacts import sanitize_public_artifact


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "output/batch-50-api-runtime-a/catalogs/US-RESET-2026-08-14-B01-B50-INITIAL-1.0"


def test_all_500_stored_availability_labels_are_sanitizer_idempotent() -> None:
    manifest = json.loads((CATALOG / "manifest.json").read_text())
    expected = Counter(entry["availability_type"] for entry in manifest["entries"])
    observed = Counter()
    mismatches = []
    for entry in manifest["entries"]:
        raw = json.loads((CATALOG / "artifacts" / f"{entry['ticker']}.json").read_text())
        served = sanitize_public_artifact(raw)
        observed[served["availability_type"]] += 1
        if served["availability_type"] != entry["availability_type"]:
            mismatches.append((entry["ticker"], entry["availability_type"], served["availability_type"]))
    assert mismatches == []
    assert expected == observed == Counter({"conditional_estimate": 358, "available": 116, "not_available": 26})
