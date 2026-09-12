#!/usr/bin/env python3
"""Freeze a verified catalog and its processed-company registry outside tracked code."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.us_valuation.catalog import load_catalog_version, canonical_json_bytes, sha256_bytes


def immutable(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'immutable baseline differs: {path}')
        return
    with path.open('xb') as handle:
        handle.write(data)


def freeze(source: Path, target: Path) -> dict:
    catalog = load_catalog_version(source)
    if source.resolve() == target.resolve() or target.resolve().is_relative_to(source.resolve()):
        raise ValueError('baseline destination must be separate')
    entries = []
    for entry in catalog.entries:
        raw = catalog.verify_artifact(entry.ticker).read_bytes()
        public = json.loads(raw)
        immutable(target / 'baseline' / 'artifacts' / f'{entry.ticker}.json', raw)
        entries.append({'ticker': entry.ticker, 'cik': entry.cik, 'batch': entry.batch,
                        'baseline_sha256': entry.artifact_sha256,
                        'availability_type': entry.availability_type,
                        'source_audit': entry.source_audit,
                        'primary_model': public['model_policy']['primary'],
                        'forecast_mode': public.get('public_assumptions', {}).get('forecast_mode'),
                        'controlling_filing': public.get('source_financial_statement', {}),
                        'recipe_status': 'migration_pending' if public['scenario_range']['base'] is not None else 'prior_unavailable'})
    immutable(target / 'baseline' / 'manifest.json', catalog.manifest_path.read_bytes())
    registry = {'schema_version': 'FINSIGHT-US-REFRESH-REGISTRY-1', 'baseline_manifest_sha256': catalog.manifest_sha256,
                'baseline_catalog_version': catalog.catalog_version, 'entries': entries}
    immutable(target / 'registry.json', canonical_json_bytes(registry))
    load_catalog_version(target / 'baseline')
    report = {'issuer_count': len(entries), 'numeric_recipe_candidates': sum(e['recipe_status'] == 'migration_pending' for e in entries),
              'registry_sha256': sha256_bytes(canonical_json_bytes(registry)), 'catalog_sha256': catalog.manifest_sha256}
    immutable(target / 'baseline-freeze.json', canonical_json_bytes(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.catalog, args.runtime_root), sort_keys=True))
