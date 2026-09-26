"""Generate public, calculator-replayed fixtures for isolated UI tests (no account)."""
import json
from pathlib import Path

from app.us_valuation.calculator import calculate, calculator_view
from app.us_valuation.catalog import load_catalog

root = Path(__file__).resolve().parents[1]
catalog = load_catalog(root / "backend/app/data/us_valuation_catalogs/US-RESET-2026-08-14-B01-B10-1.0")
artifact = json.loads(catalog.verify_artifact("AAPL").read_text())
artifact["catalog"] = {**catalog.public_metadata(), "batch": 1}
artifact["evidence_health"] = []
cases = [(case, {}) for case in ("low", "base", "high")]
cases += [("high", {"initial_growth": .11}), ("high", {"initial_growth": .115}), ("base", {"initial_growth": .12})]
payload = {
    "kind": "isolated-ui-fixture-no-account",
    "detail": artifact,
    "calculator": calculator_view(artifact),
    "list": {"count": 1, "items": [{"ticker": "AAPL", "name": artifact["issuer"]["issuer_name"], "batch": 1, "reliability": "Low", "availability_type": artifact["availability_type"]}]},
    "calculations": [calculate(artifact, scenario=case, overrides=inputs, manual_price=None) for case, inputs in cases],
}
output = root / "frontend/tests/fixtures/apple-case-inputs.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(payload, indent=2) + "\n")
print("Generated public fixture; no accounts, holdings or saved runs accessed.")
