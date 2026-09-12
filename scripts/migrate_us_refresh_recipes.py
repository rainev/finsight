#!/usr/bin/env python3
"""Replay private evidence into migration recipes; never activate a catalog."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.us_valuation.recipe_migration import migrate_catalog
from app.us_valuation.catalog import canonical_json_bytes, load_catalog_version, sha256_bytes
from app.us_valuation.calculator import baseline_version, _defaults_and_fields
from app.us_valuation.artifacts import sanitize_public_artifact
from app.us_valuation.calculation_recipe import evaluate_recipe, EDITABLE_FIELDS
from app.us_valuation.refresh_job import atomic, writer


def run(root: Path, private_root: Path) -> dict:
    with writer(root):
        catalog = load_catalog_version(root / 'baseline')
        report = migrate_catalog(catalog.root, [private_root])
        for row in report['migrated']:
            recipe = row['recipe']
            public = sanitize_public_artifact(json.loads(catalog.verify_artifact(row['ticker']).read_text()))
            recipe['baseline_version'] = baseline_version(public)
            recipe['evidence_cutoff'] = public['valuation_date']
            recipe['source_accession'] = public['source_financial_statement']['accession']
            # Reuse existing calculator bounds only for assumptions the exact
            # engine actually supports. Never unlock a reported balance or share.
            _, _, fields = _defaults_and_fields(public)
            aliases = {'discount_rate': ('wacc', 'cost_of_equity', 'discount_rate'),
                       'initial_growth': ('initial_growth', 'growth'),
                       'sustainable_roe': ('current_roe',), 'payout_ratio': ('current_payout_ratio',),
                       'forecast_years': ('forecast_years', 'years'), 'cash_conversion': ('cash_fcff',)}
            for field in fields:
                candidates = aliases.get(field['key'], (field['key'],))
                for target in candidates:
                    if all(target in EDITABLE_FIELDS.get(spec['engine'], set()) and target in spec['inputs'] for spec in recipe['scenarios'].values()):
                        operation = 'multiply' if field['key'] == 'cash_conversion' else 'replace' if field['key'] == 'forecast_years' else 'delta'
                        recipe['editable'][field['key']] = {'field': target, 'operation': operation, 'min': field['min'], 'max': field['max'],
                                                           'label': field['label'], 'step': field['step'], 'integer': field['key'] == 'forecast_years'}
                        break
            evaluate_recipe(recipe)
            recipe['recipe_version'] += '-' + sha256_bytes(canonical_json_bytes(recipe))[:16]
            path = root / 'recipes' / f"{row['ticker']}.json"
            if path.exists():
                previous = path.read_bytes()
                atomic(root / 'recipe-history' / f'{sha256_bytes(previous)}.json', previous)
            # These are migration working inputs, not activated recipes.
            # Published snapshots pin their own immutable copies and hashes.
            atomic(path, canonical_json_bytes(recipe), immutable=False)
        # Report names may advance while immutable, already-written recipes cannot.
        atomic(root / 'recipe-migration-report.json', canonical_json_bytes(report), immutable=False)
        summary = {key: report[key] for key in ('catalog_version','numeric_count','migrated_count','gap_count')}
        summary['gaps'] = [{key: value for key, value in row.items() if key != 'recipe'} for row in report['gaps']]
        atomic(root / 'recipe-migration-summary.json', canonical_json_bytes(summary), immutable=False)
        migrated = {row['ticker']: row for row in report['migrated']}
        gaps = {row['ticker']: row for row in report['gaps']}
        companies = []
        for entry in catalog.entries:
            public = sanitize_public_artifact(json.loads(catalog.verify_artifact(entry.ticker).read_text()))
            companies.append({'ticker': entry.ticker, 'baseline_range': public['scenario_range'],
                              'migration_status': 'exact_replay' if entry.ticker in migrated else 'migration_gap' if entry.ticker in gaps else 'prior_unavailable',
                              'reason': gaps.get(entry.ticker, {}).get('reason'), 'confidence': public.get('confidence'),
                              'reliability': public.get('reliability'), 'filing': public['source_financial_statement'],
                              'intentional_value_change': False})
        atomic(root / 'migration-company-report.json', canonical_json_bytes({'catalog_version': catalog.catalog_version, 'companies': companies}), immutable=False)
        lines = ['# Frozen migration comparison', '', 'No official values have been changed. Exact values and confidence evidence are in migration-company-report.json.', '',
                 '| Company | Low | Base | High | Migration | Reason |', '|---|---:|---:|---:|---|---|']
        for company in companies:
            numbers = [company['baseline_range'].get(key) for key in ('low','base','high')]
            formatted = ['Not available' if value is None else f'{value:.8f}' for value in numbers]
            lines.append('| ' + ' | '.join([company['ticker'], *formatted, company['migration_status'], company['reason'] or '']) + ' |')
        atomic(root / 'migration-company-report.md', ('\n'.join(lines) + '\n').encode(), immutable=False)
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, default=ROOT / 'output/us-refresh-runtime')
    parser.add_argument('--private-root', type=Path, default=ROOT / 'output')
    args = parser.parse_args()
    print(json.dumps(run(args.runtime_root, args.private_root), sort_keys=True))
