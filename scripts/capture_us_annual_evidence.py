#!/usr/bin/env python3
"""Capture explicitly selected annual accessions using existing bounded SEC/Arelle tools."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from capture_batch_02_structural_sources import (
    _dependencies, _immutable_json, _json_bytes, _sha256, _tree_hash,
    _validate_paths, PROTECTED_ROOTS,
)
from app.us_valuation.sec_client import normalize_cik


def run(*, source_root, output_root, cache_root, ticker, accessions, user_agent, cutoff=None,
        client=None, package_capture=None, parse=None):
    source_root, output_root, cache_root = map(Path, (source_root, output_root, cache_root))
    _validate_paths(source_root, output_root, cache_root)
    submissions_path = source_root / 'submissions.json'
    raw = submissions_path.read_bytes()
    submissions = json.loads(raw)
    source_manifest = json.loads((source_root / 'source-manifest.json').read_bytes())
    if source_manifest.get('packet_payload_sha256', {}).get('submissions.json') != _sha256(raw):
        raise ValueError('annual frozen submissions hash mismatch')
    cutoff = date.fromisoformat(cutoff or source_manifest['valuation_date']).isoformat()
    cik = normalize_cik(submissions['cik'])
    issuer = source_manifest.get('issuer', {})
    if issuer.get('ticker') != ticker or normalize_cik(issuer.get('cik', '')) != cik:
        raise ValueError('annual frozen packet issuer mismatch')
    if ticker not in submissions.get('tickers', []):
        raise ValueError('annual source ticker identity mismatch')
    if not accessions or len(set(accessions)) != len(accessions):
        raise ValueError('explicit unique annual accessions required')
    recent = submissions['filings']['recent']
    selected = []
    for accession in accessions:
        indices = [i for i, value in enumerate(recent['accessionNumber']) if value == accession]
        if len(indices) != 1:
            raise ValueError('annual accession missing or ambiguous in frozen submissions')
        i = indices[0]
        if recent['form'][i] not in ('10-K', '10-K/A'):
            raise ValueError('selected source is not annual')
        if not recent['reportDate'][i] <= recent['filingDate'][i] <= cutoff:
            raise ValueError('selected annual filing exceeds frozen evidence cutoff')
        selected.append({'accession': accession, 'form': recent['form'][i],
                         'filed': recent['filingDate'][i], 'report_date': recent['reportDate'][i],
                         'primary_document': recent['primaryDocument'][i]})
    if selected != sorted(selected, key=lambda row: (row['filed'], row['accession']), reverse=True):
        raise ValueError('annual sources must be acquired latest first')
    if client is None or package_capture is None or parse is None:
        sec, capture_default, parse_default = _dependencies()
        client = client or sec(user_agent=user_agent, cache_dir=cache_root / '.sec-cache')
        package_capture, parse = package_capture or capture_default, parse or parse_default
    before = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
    cases = []
    try:
        for filing in selected:
            case = {'ticker': ticker, 'cik': cik, 'filing': filing,
                    'submissions_sha256': _sha256(raw)}
            try:
                entry = package_capture(client, cik=cik, accession=filing['accession'],
                    primary_document=filing['primary_document'], form=filing['form'],
                    output_dir=cache_root / 'filings' / ticker, refresh=False,
                    filed_date=filing['filed'], report_date=filing['report_date'])
                package = json.loads((entry.parent / 'package-manifest.json').read_bytes())
                if (normalize_cik(package['cik']) != cik or package['accession'] != filing['accession']):
                    raise ValueError('annual package identity mismatch')
                parsed = parse(entry, accession=filing['accession'], form=filing['form'], timeout_seconds=300)
                structural = parsed.as_dict() if hasattr(parsed, 'as_dict') else parsed
                if (structural.get('source_accession') != filing['accession']
                    or structural.get('report_date') != filing['report_date']
                    or structural.get('filed_date') != filing['filed']
                    or structural.get('form') != filing['form']):
                    raise ValueError('annual parsed identity/period mismatch')
                target = output_root / ticker / filing['accession']
                _immutable_json(target / 'package-manifest.json', package)
                _immutable_json(target / 'structural-filing.json', structural)
                case.update(status='parsed', package_manifest_sha256=_sha256(_json_bytes(package)),
                            structural_sha256=_sha256(_json_bytes(structural)))
                _immutable_json(target / 'source-receipt.json', case)
            except Exception as exc:
                causes = []
                cause = exc.__cause__
                while cause is not None and len(causes) < 5:
                    causes.append({'error_type': type(cause).__name__, 'reason': str(cause)})
                    cause = cause.__cause__
                case.update(status='acquisition_or_parse_failed', error_type=type(exc).__name__,
                            reason=str(exc), causes=causes)
            cases.append(case)
    finally:
        after = {str(root): _tree_hash(root) for root in PROTECTED_ROOTS}
        if before != after:
            raise RuntimeError('annual acquisition changed protected serving artifacts')
    report = {'schema_version': 'FINSIGHT-SELECTED-ANNUAL-CAPTURE-WG29-1', 'cases': cases,
              'attempted': len(cases), 'parsed': sum(row['status'] == 'parsed' for row in cases),
              'serving_hash_before': before, 'serving_hash_after': after,
              'economic_validation': False}
    _immutable_json(output_root / 'capture-report.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'output-root', 'cache-root'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--ticker', required=True)
    p.add_argument('--cutoff', help='Evidence cutoff; defaults to frozen source-manifest valuation date')
    p.add_argument('--accession', action='append', dest='accessions', required=True)
    p.add_argument('--user-agent', default=os.environ.get('SEC_USER_AGENT'))
    print(json.dumps(run(**vars(p.parse_args())), sort_keys=True))
