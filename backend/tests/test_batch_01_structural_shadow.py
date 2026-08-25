"""Hermetic contract tests for the Batch 01 structural-shadow runner."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_batch_01_structural_shadow.py"
SPEC = importlib.util.spec_from_file_location("batch_01_shadow_test", SCRIPT)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _packet(root: Path, ticker: str, cik: str) -> None:
    packet = root / ticker
    packet.mkdir(parents=True)
    submissions = {"cik": cik, "name": ticker, "tickers": [ticker], "filings": {"recent": {}}}
    facts = {"cik": cik, "entityName": ticker, "facts": {}}
    for name, value in (("submissions.json", submissions), ("companyfacts.json", facts)):
        raw = (json.dumps(value, sort_keys=True) + "\n").encode()
        (packet / name).write_bytes(raw)
        (packet / name.replace(".json", ".meta.json")).write_text("{}\n")
    hashes = {name: hashlib.sha256((packet / name).read_bytes()).hexdigest() for name in ("submissions.json", "submissions.meta.json", "companyfacts.json", "companyfacts.meta.json")}
    (packet / "source-manifest.json").write_text(json.dumps({"issuer": {"ticker": ticker, "cik": cik, "issuer_name": ticker}, "valuation_date": "2026-08-14", "files": {"submissions.json": {"sha256": hashes["submissions.json"]}, "companyfacts.json": {"sha256": hashes["companyfacts.json"]}}, "packet_payload_sha256": hashes, "eligible_filings": [], "future_filings": []}, sort_keys=True) + "\n")


def test_structural_shadow_scopes_to_operating_requests_and_is_immutable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_root, output_root, cache_root, serving = (tmp_path / name for name in ("sources", "out", "cache", "serving"))
    serving.mkdir(); (serving / "sentinel").write_text("same")
    _packet(source_root, "AAPL", "0000320193")
    _packet(source_root, "MSFT", "0000789019")
    monkeypatch.setattr(runner, "BATCH_01_MANIFEST", (
        type("Issuer", (), {"ticker": "AAPL", "cik": "0000320193", "lane_hypothesis": "mature_operating_fcff"})(),
        type("Issuer", (), {"ticker": "MSFT", "cik": "0000789019", "lane_hypothesis": "intangible_investment_fcff"})(),
    ))
    calls: list[str] = []
    def build(**kwargs): return {"issuer": {"ticker": kwargs["submissions"]["tickers"][0], "cik": kwargs["submissions"]["cik"]}, "financials": {"ttm": {"controlling_filing": {"accession": "0001", "form": "10-Q", "primary_document": "a.htm"}}, "balance_sheet": {"bridge_missing_fields": ["current_debt"] if kwargs["submissions"]["tickers"][0] == "AAPL" else []}}}
    def requests(artifact):
        if artifact["issuer"]["ticker"] != "AAPL":
            return ()
        return (type("Request", (), {"normalized_concept": "current_debt"})(),)
    def cache(*args, **kwargs):
        calls.append(kwargs["cik"])
        assert kwargs["refresh"] is False
        p = cache_root / "package" / "entry.htm"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
        (p.parent / "package-manifest.json").write_text("{}\n")
        return p
    def parse(*args, **kwargs): return type("Filing", (), {"as_dict": lambda self: {"source_accession": "0001"}})()
    def evaluate(artifact, filing): return {"decisions": [{"status": "accepted", "normalized_concept": "current_debt"}]}
    summary = runner.run_structural_shadow(source_root=source_root, output_root=output_root, cache_root=cache_root, protected_serving_roots=(serving,), build=build, shadow_requests=requests, cache_package=cache, parse=parse, evaluate=evaluate)
    assert summary["attempted"] == 1 and summary["parsed"] == 1 and summary["skipped"] == 1
    assert summary["requested_field_counts"] == {"current_debt": 1}
    assert summary["serving_artifacts_changed"] is False
    assert calls == ["0000320193"]
    assert (output_root / "AAPL" / "diagnostic-private.json").exists()
    assert (output_root / "AAPL" / "structural-filing.json").exists()
    assert (output_root / "AAPL" / "structural-report.json").exists()
    first = (output_root / "summary.json").read_bytes()
    assert runner.run_structural_shadow(source_root=source_root, output_root=output_root, cache_root=cache_root, protected_serving_roots=(serving,), build=build, shadow_requests=requests, cache_package=cache, parse=parse, evaluate=evaluate)["parsed"] == 1
    assert (output_root / "summary.json").read_bytes() == first
    assert (serving / "sentinel").read_text() == "same"


def test_packet_guards_reject_future_and_identity_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "sources"; _packet(root, "AAPL", "0000320193")
    manifest_path = root / "AAPL" / "source-manifest.json"
    payload = json.loads(manifest_path.read_text()); payload["future_filings"] = [{"filed": "2026-08-15"}]; payload["eligible_filings"] = [{"filed": "2026-08-15"}]; manifest_path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="future filing"):
        runner._load_packet(root / "AAPL", type("Issuer", (), {"ticker": "AAPL", "cik": "0000320193"})())


def test_help_is_arelle_free() -> None:
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--source-root" in result.stdout
