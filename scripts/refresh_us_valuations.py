#!/usr/bin/env python3
"""Refresh U.S. valuations; migration and initial approval gates fail closed."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.us_valuation.refresh_job import execute, preflight, MigrationIncomplete, capture, writer, configured_sec_user_agent, atomic
from datetime import datetime, timezone
from app.us_valuation.catalog import sha256_bytes, canonical_json_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('stage','publish','replay'), default='stage')
    parser.add_argument('--runtime-root', type=Path, default=Path(os.environ.get('FINSIGHT_US_REFRESH_ROOT', ROOT / 'output/us-refresh-runtime')))
    parser.add_argument('--snapshot')
    parser.add_argument('--as-of', dest='cutoff')
    parser.add_argument('--source-file', type=Path, help='Frozen offline evidence snapshot for reproducible replay')
    parser.add_argument('--check-readiness', action='store_true')
    parser.add_argument('--work-status',action='store_true',help='Write the 440-company machine register and plain-language progress report; no capture or activation')
    parser.add_argument('--capture-only',action='store_true',help='Capture evidence without building or activating a catalog')
    parser.add_argument('--ticker',action='append',default=[],help='Limit capture-only verification to frozen-registry tickers')
    parser.add_argument('--resume-acquisition', dest='acquisition_id', help='Resume the acquisition ID recorded in acquisition-status.json; retains its original cutoff')
    args = parser.parse_args()
    try:
        if args.work_status:
            if args.mode!='stage' or args.capture_only or args.check_readiness or args.source_file or args.snapshot or args.ticker or args.acquisition_id:
                raise ValueError('work-status is reporting-only and cannot capture, replay, publish, or narrow the frozen universe')
            from app.us_valuation.refresh_work_register import build_work_register,render_markdown
            report=build_work_register(args.runtime_root)
            atomic(args.runtime_root/'work-register.json',canonical_json_bytes(report),immutable=False)
            atomic(args.runtime_root/'work-register.md',render_markdown(report).encode(),immutable=False)
            print(json.dumps({'scope':'440-company work status; not a completion percentage','counts':report['counts'],
                'family_adapter_count':report['implementation_queue']['family_adapter_count'],
                'next_working_group':(report['summary']['next']['working_group'] or {}).get('mechanism'),
                'json':str(args.runtime_root/'work-register.json'),'markdown':str(args.runtime_root/'work-register.md'),'activated':False},sort_keys=True))
            return 0
        if args.capture_only:
            if args.mode != 'stage' or args.source_file or args.snapshot or args.check_readiness:
                raise ValueError('capture-only cannot publish, replay or consume an offline snapshot')
            with writer(args.runtime_root):
                raw = (args.runtime_root/'registry.json').read_bytes()
                registry = json.loads(raw)
                wanted = set(args.ticker)
                if wanted - {entry['ticker'] for entry in registry['entries']}:
                    raise ValueError('capture ticker is outside frozen registry')
                if wanted:
                    registry = {**registry,'entries':[entry for entry in registry['entries'] if entry['ticker'] in wanted],
                        'capture_scope':'source verification subset','parent_registry_sha256':sha256_bytes(raw)}
                policies = json.loads((args.runtime_root/'refresh-policies.json').read_bytes())
                recipes = {entry['ticker']:json.loads(path.read_bytes()) for entry in registry['entries']
                    if (path := args.runtime_root/'recipes'/f"{entry['ticker']}.json").is_file()}
                cutoff = args.cutoff
                if args.acquisition_id and cutoff is None:
                    if len(args.acquisition_id) != 64 or any(char not in '0123456789abcdef' for char in args.acquisition_id):
                        raise ValueError('invalid acquisition identifier')
                    cutoff = json.loads((args.runtime_root/'acquisitions'/args.acquisition_id/'input.json').read_bytes())['cutoff']
                cutoff = cutoff or datetime.now(timezone.utc).date().isoformat()
                fingerprint = sha256_bytes(canonical_json_bytes({'policies':{entry['ticker']:policies.get(entry['ticker']) for entry in registry['entries']},
                    'recipe_cutoffs':{ticker:recipe['evidence_cutoff'] for ticker,recipe in recipes.items()}}))
                # Earlier capture-only checkpoints had no policy fingerprint.
                # They remain readable evidence but require a new capture after
                # this contract change, rather than silently resuming new rules.
                result = capture(args.runtime_root,registry,cutoff,configured_sec_user_agent(args.runtime_root),
                    acquisition_id=args.acquisition_id,context_fingerprint=fingerprint,source_policies=policies,recipe_cutoffs={ticker:recipe['evidence_cutoff'] for ticker,recipe in recipes.items()})
                failures = {ticker:packet for ticker,packet in result['packets'].items() if packet.get('acquisition_failed')}
                print(json.dumps({'scope':'source capture only','acquisition_id':result['acquisition_id'],'cutoff':cutoff,
                    'requested':len(registry['entries']),'captured':len(registry['entries'])-len(failures),'failures':failures,'activated':False},sort_keys=True))
                return 2 if failures else 0
        if args.ticker:
            raise ValueError('--ticker is available only with --capture-only')
        if args.check_readiness:
            report = preflight(args.runtime_root)
            print(json.dumps({k:v for k,v in report.items() if k != 'rows'}, sort_keys=True))
            return 0 if report['recipe_ready_count'] == report['refresh_ready_count'] == report['numeric_count'] else 2
        report = execute(args.runtime_root, mode=args.mode, cutoff=args.cutoff, snapshot=args.snapshot, source_file=args.source_file, acquisition_id=args.acquisition_id)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({'status':'blocked', 'reason':str(exc), 'activated':False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
