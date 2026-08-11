"""Hermetic real-boundary structural-XBRL integration coverage."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ACCESSION = "0000000001-26-000001"
ARCHIVE_ACCESSION = "000000000126000001"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "us" / "structural-xbrl"
REMOTE_US_GAAP = "https://xbrl.fasb.org/us-gaap/2025/us-gaap-2025.xsd"
REMOTE_XBRLI = "https://www.xbrl.org/2003/xbrli-2003.xsd"
LEGACY_DECLARED_XBRLI = "http://www.xbrl.org/2003/xbrli-2003.xsd"


def _taxonomy_cache_path(cache_root: Path, url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_root / "taxonomy" / f"{digest}{Path(url).suffix}"


def _load_cli() -> object:
    script = Path(__file__).resolve().parents[2] / "scripts" / "run_structural_xbrl_shadow.py"
    spec = importlib.util.spec_from_file_location("structural_xbrl_real_integration", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cached_package_to_offline_arelle_to_shadow_report_is_hermetic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "valuation-input"
    cache_root = tmp_path / "sec-cache"
    output_root = tmp_path / "shadow-output"
    filing_cache = (
        cache_root
        / "archives"
        / "CIK0000000001"
        / ARCHIVE_ACCESSION
    )
    data_root.mkdir()
    filing_cache.mkdir(parents=True)

    primary = (FIXTURE_ROOT / "fsi-20251231.htm").read_bytes()
    extension_schema = (FIXTURE_ROOT / "fsi-2025.xsd").read_text().replace(
        'schemaLocation="us-gaap-2025.xsd"',
        f'schemaLocation="{REMOTE_US_GAAP}"',
    ).replace(
        'schemaLocation="xbrli-2003.xsd"',
        f'schemaLocation="{LEGACY_DECLARED_XBRLI}"',
    )
    remote_us_gaap = (FIXTURE_ROOT / "us-gaap-2025.xsd").read_text().replace(
        'schemaLocation="xbrli-2003.xsd"',
        f'schemaLocation="{LEGACY_DECLARED_XBRLI}"',
    )
    filing_files = {
        "fsi-20251231.htm": primary,
        "fsi-2025.xsd": extension_schema.encode(),
        "fsi-2025_pre.xml": (FIXTURE_ROOT / "fsi-2025_pre.xml").read_text().replace(
            'xlink:href="us-gaap-2025.xsd',
            f'xlink:href="{REMOTE_US_GAAP}',
        ).encode(),
        "fsi-2025_cal.xml": (FIXTURE_ROOT / "fsi-2025_cal.xml").read_text().replace(
            'xlink:href="us-gaap-2025.xsd',
            f'xlink:href="{REMOTE_US_GAAP}',
        ).encode(),
        "fsi-2025_lab.xml": (FIXTURE_ROOT / "fsi-2025_lab.xml").read_text().replace(
            'xlink:href="us-gaap-2025.xsd',
            f'xlink:href="{REMOTE_US_GAAP}',
        ).encode(),
    }
    index = {
        "directory": {"item": [{"name": name} for name in filing_files]}
    }
    (filing_cache / "index.json").write_text(json.dumps(index), encoding="utf-8")
    for name, raw in filing_files.items():
        (filing_cache / name).write_bytes(raw)
    for url, raw in (
        (REMOTE_US_GAAP, remote_us_gaap.encode()),
        (REMOTE_XBRLI, (FIXTURE_ROOT / "xbrli-2003.xsd").read_bytes()),
    ):
        path = _taxonomy_cache_path(cache_root, url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    artifact = {
        "ticker": "FSI",
        "valuation_date": "2026-08-01",
        "issuer": {"cik": "0000000001", "ticker": "FSI"},
        "review": {"publication_state": "withheld"},
        "financials": {
            "ttm": {
                "period_end": "2025-12-31",
                "controlling_filing": {
                    "accession": ACCESSION,
                    "form": "10-K/A",
                    "primary_document": "fsi-20251231.htm",
                },
            },
            "balance_sheet": {
                "bridge_missing_fields": ["marketable_securities_current"],
                "field_states": {"marketable_securities_current": "missing"},
            },
        },
    }
    (data_root / "FSI.json").write_text(json.dumps(artifact), encoding="utf-8")

    def network_forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("integration test attempted network access")

    monkeypatch.setattr("app.us_valuation.sec_client.urlopen", network_forbidden)
    cli = _load_cli()

    assert cli.main(
        [
            "--data-root",
            str(data_root),
            "--cache-dir",
            str(cache_root),
            "--output-root",
            str(output_root),
        ]
    ) == 0

    report = json.loads((output_root / "FSI.json").read_text())
    decision = report["decisions"][0]
    assert report["publication_effect"] == "none_shadow_only"
    assert decision["status"] == "accepted"
    assert decision["form"] == "10-K/A"
    assert decision["evidence"]["filing_form"] == "10-K/A"
    assert decision["evidence"]["decimals"] == "0"
    assert decision["evidence"]["relationships"]
    assert decision["evidence"]["filing_metadata"]
    summary = json.loads((output_root / "summary.json").read_text())
    assert summary["accepted_shadow"] == 1
    manifests = list((cache_root / "structural-filings").rglob("package-manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert {item["source_url"] for item in manifest["files"]} >= {
        REMOTE_US_GAAP,
        REMOTE_XBRLI,
    }
    assert LEGACY_DECLARED_XBRLI not in {
        item["source_url"] for item in manifest["files"]
    }
