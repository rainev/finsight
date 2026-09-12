#!/usr/bin/env python3
"""Exercise migrated refresh bindings against hashed, cached real SEC packets.

This diagnostic does not acquire network data, change the frozen universe,
create approval, or activate a catalog. It distinguishes code gaps from source
gaps and writes exact per-company input/output evidence outside tracked source.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import time
from html import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.us_valuation.catalog import canonical_json_bytes, sha256_bytes, load_catalog_version
from app.us_valuation.calculation_recipe import evaluate_recipe
from app.us_valuation.refresh_job import atomic, policy_readiness, writer, refreshed_public
from app.us_valuation.refresh_bindings import bind_current_recipe, EconomicException, AcquisitionIncomplete
from app.us_valuation.refresh_source_ingestion import capture_company_source, SourceCaptureError, _definition_hash
from app.us_valuation.refresh_source_index import load_source_index, SourceIndexError


def implementation_fingerprint():
    report_only = {'refresh_work_register.py','refresh_group_verification.py'}
    paths = [Path(__file__), *(path for path in sorted((ROOT/'backend/app/us_valuation').rglob('*.py')) if path.name not in report_only),
             *sorted((ROOT/'backend/app/us_valuation/config').rglob('*.json'))]
    return sha256_bytes(canonical_json_bytes({str(path.relative_to(ROOT)):sha256_bytes(path.read_bytes()) for path in paths}))


def readable_report(report):
    def cell(value):
        return escape(str(value or '—')).replace('|','\\|').replace('\n',' ')
    def values(row):
        return ' / '.join('Not available' if row.get(key) is None else f"${row[key]:,.2f}" for key in ('low','base','high')) if row else '—'
    lines = ['# Frozen-source verification', '',
        'Diagnostic candidates only; nothing was activated. Ranges are low / base / high, displayed to two decimals. Exact values and source provenance remain in report.json and per-company evidence.', '',
        'Counts: ' + ', '.join(f'{key}: {value}' for key,value in sorted(report['counts'].items())), '',
        '| Company | Status | Previous range | Candidate range | Candidate confidence | Reason |',
        '|---|---|---:|---:|---|---|']
    for row in report['rows']:
        lines.append('| ' + ' | '.join((cell(row['ticker']),cell(row['status']),values(row.get('previous_range')),values(row.get('current_range')),cell(row.get('confidence')),cell(row.get('reason')))) + ' |')
    return '\n'.join(lines) + '\n'


def cached_paths(output: Path, registry: dict):
    packets, structural = {}, {}
    by_cik = {}
    for entry in registry['entries']:
        by_cik.setdefault(str(entry['cik']).zfill(10), []).append(entry['ticker'])
    tickers = {entry['ticker'] for entry in registry['entries']}
    for path in sorted(output.rglob('submissions.json')):
        if (path.parent / 'companyfacts.json').is_file():
            packets.setdefault(path.parent.name, []).append(path.parent)
    for path in sorted(output.rglob('structural-filing.json')):
        if path.parent.name in tickers:
            structural.setdefault(path.parent.name, []).append(path)
        else:
            # A reparsed source may live in a verification directory rather
            # than a ticker-named folder. Route it by actual fact identities.
            payload = json.loads(path.read_bytes())
            identities = {str(row.get('entity_identifier')).zfill(10) for row in payload.get('facts', []) if row.get('entity_identifier') is not None}
            if len(identities) == 1:
                for ticker in by_cik.get(identities.pop(), []):
                    structural.setdefault(ticker, []).append(path)
    return packets, structural


def indexed_paths(output: Path, registry: dict, index_path: Path, tickers=()):
    """Load candidate paths without rescanning output; selection still occurs later."""
    index = load_source_index(index_path, allowed_output_root=output)
    wanted = set(tickers) or {entry['ticker'] for entry in registry['entries']}
    identities = {entry['ticker']:str(entry['cik']).zfill(10) for entry in registry['entries'] if entry['ticker'] in wanted}
    packets, structural, by_path = {}, {}, {'packet':{},'structural':{}}
    for ticker,cik in identities.items():
        candidates=[entry for entry in index.entries if entry.get('cik')==cik and (entry.get('ticker') in {ticker,None})]
        for entry in candidates:
            kind=entry.get('kind')
            if kind not in by_path: continue
            path=(output/entry['path']).resolve()
            by_path[kind].setdefault(str(path),[]).append(entry)
            target=packets if kind=='packet' else structural
            target.setdefault(ticker,[]).append(path)
    for target in (packets,structural):
        for ticker,paths in target.items():
            target[ticker]=sorted(set(paths))
    return packets,structural,{'index':index,'entries':by_path}


def validate_indexed_path(indexed, kind, path):
    rows=indexed['entries'][kind].get(str(Path(path).resolve()),[])
    if not rows:
        raise SourceCaptureError('selected cached source is absent from the frozen source index')
    errors=sorted({str(error) for row in rows for error in row.get('validation_errors',[])})
    if errors:
        raise SourceCaptureError('indexed cached source is invalid: '+'; '.join(errors))
    try:
        return indexed['index'].read(rows[0]),rows[0]
    except SourceIndexError as exc:
        raise SourceCaptureError('indexed cached source failed byte/identity validation: '+str(exc)) from exc


def structural_candidate_rank(indexed_entry, *, identified):
    """Prefer current-parser, fully dated evidence without relying on paths."""
    filing=(indexed_entry or {}).get('filing') or {}
    return (
        bool(identified),
        (indexed_entry or {}).get('parser_definition_sha256')==_definition_hash(),
        all(isinstance(filing.get(key),str) and filing[key] for key in ('accession','form','report_date','filed_date')),
    )


def _packet(entry, recipe, paths, structures, cache_root, cutoff, indexed=None, provenance_root=None):
    ticker = entry['ticker']
    candidates = paths.get(ticker, [])
    batch_pattern = re.compile(rf'batch[-_]?0*{entry["batch"]}(?:\D|$)', re.I)
    preferred = [path for path in candidates if batch_pattern.search(str(path))]
    candidates = preferred or candidates
    if not candidates:
        raise SourceCaptureError('no local companyfacts/submissions packet for issuer')
    # Freeze the selected path and bytes in the receipt. Multiple historical
    # captures are not combined and no alternate silently replaces corruption.
    source_path = next((path for path in candidates if (path/'source-manifest.json').is_file()), candidates[0])
    if indexed is not None:
        validate_indexed_path(indexed,'packet',source_path)
    structural_paths = {}
    structural_ranks = {}
    for path in structures.get(ticker, []):
        if indexed is not None:
            _,indexed_entry=validate_indexed_path(indexed,'structural',path)
            accession=(indexed_entry.get('filing') or {}).get('accession')
            identified=indexed_entry.get('cik') == str(entry['cik']).zfill(10) and indexed_entry.get('fact_identity_complete') is True
        else:
            header = json.loads(path.read_bytes())
            accession = header.get('source_accession')
            facts = header.get('facts', [])
            identified = bool(facts) and all(str(row.get('entity_identifier','')).zfill(10) == str(entry['cik']).zfill(10) for row in facts)
        if isinstance(accession, str):
            rank=structural_candidate_rank(indexed_entry if indexed is not None else None,identified=identified)
            if accession not in structural_paths or rank>structural_ranks[accession]:
                structural_paths[accession] = path
                structural_ranks[accession] = rank
    packet = capture_company_source(
        ticker=ticker, cik=entry['cik'], cutoff=cutoff,
        offline_packet_dir=source_path, structural_paths=structural_paths,
        require_structural=False, parsed_cache_dir=cache_root,
        event_since=recipe['evidence_cutoff'], capture_event_relationships=False,
    )
    provenance = {'packet_directory':str(source_path.relative_to(Path(provenance_root or ROOT).resolve())),
        'raw_hashes':packet['raw_hashes'],
        'structural_receipts':packet['structural_receipts'],
        'network_accessed':False,
        'limitations':['This cached-source binding check does not establish live acquisition or event-exhibit coverage.']}
    return packet, provenance


def acquired_packet(runtime_root, acquisition, entry, cutoff):
    if not re.fullmatch(r'[0-9a-f]{64}', acquisition):
        raise ValueError('acquisition must be a SHA-256 run ID')
    root = runtime_root / 'acquisitions' / acquisition
    descriptor = json.loads((root/'input.json').read_bytes())
    if sha256_bytes(canonical_json_bytes(descriptor)) != acquisition:
        raise SourceCaptureError('acquisition descriptor hash mismatch')
    if descriptor['cutoff'] != cutoff:
        raise SourceCaptureError('verification cutoff differs from captured cutoff')
    path = root/'packets'/f'{entry["ticker"]}.json'
    wrapper_raw = path.read_bytes()
    wrapper = json.loads(wrapper_raw)
    if (wrapper['ticker'], str(wrapper['cik']).zfill(10)) != (entry['ticker'], str(entry['cik']).zfill(10)):
        raise SourceCaptureError('acquired packet identity mismatch')
    packet = wrapper['packet']
    if sha256_bytes(canonical_json_bytes(packet)) != wrapper['packet_sha256']:
        raise SourceCaptureError('acquired packet hash mismatch')
    return packet, {'acquisition_id': acquisition, 'wrapper_sha256': sha256_bytes(wrapper_raw),
                    'packet_sha256': wrapper['packet_sha256'], 'network_accessed': False,
                    'limitations': ['Binding reuses the frozen live capture; no new retrieval occurs in verification.']}


def verify_sources(runtime_root: Path, tickers=(), cutoff=None, acquisition=None, source_index=None, verify_full_baseline=True, source_root=None):
    total_started=time.perf_counter();prepare_started=total_started
    runtime_root = runtime_root.resolve()
    with writer(runtime_root):
        implementation_sha = implementation_fingerprint()
        registry_raw = (runtime_root/'registry.json').read_bytes()
        policy_raw = (runtime_root/'refresh-policies.json').read_bytes()
        registry, policies = json.loads(registry_raw), json.loads(policy_raw)
        baseline = load_catalog_version(runtime_root/'baseline',expected_manifest_sha256=registry['baseline_manifest_sha256'],verify_artifacts=verify_full_baseline)
        wanted = set(tickers)
        known = {entry['ticker'] for entry in registry['entries']}
        if wanted - known:
            raise ValueError(f'issuers outside frozen registry: {sorted(wanted-known)}')
        if acquisition and (not cutoff or not wanted):
            raise ValueError('acquisition verification requires explicit --as-of and --ticker scope')
        indexed = None
        if acquisition:
            packets,structures={},{}
        elif source_index:
            packets,structures,indexed=indexed_paths(Path(source_root or ROOT/'output'),registry,Path(source_index),wanted)
        else:
            packets, structures = cached_paths(Path(source_root or ROOT/'output'),registry)
        timings={'prepare':time.perf_counter()-prepare_started,'source':0.0,'calc':0.0,'verify':0.0}
        packet_cache={}
        def resolved_packet(company_entry,company_recipe,selected_cutoff):
            key=(company_entry['ticker'],selected_cutoff,acquisition or 'cached')
            if key not in packet_cache:
                if acquisition:
                    packet_cache[key]=acquired_packet(runtime_root,acquisition,company_entry,selected_cutoff)
                else:
                    packet_cache[key]=_packet(company_entry,company_recipe,packets,structures,runtime_root/'source-validation-cache',selected_cutoff,indexed=indexed,
                        provenance_root=Path(source_root).resolve().parent if source_root else ROOT)
            packet,provenance=packet_cache[key]
            return deepcopy(packet),deepcopy(provenance)
        rows, evidence = [], {}
        for entry in registry['entries']:
            ticker = entry['ticker']
            if wanted and ticker not in wanted:
                continue
            row = {'ticker':ticker, 'activated':False}
            recipe_path = runtime_root/'recipes'/f'{ticker}.json'
            if not recipe_path.is_file():
                row.update(status='prior_unavailable',reason='No numeric baseline recipe; recovery is separate.')
            else:
                recipe = json.loads(recipe_path.read_bytes())
                ready, reason = policy_readiness(recipe, policies.get(ticker))
                row.update(previous_range=evaluate_recipe(recipe)['range'])
                if not ready:
                    row.update(status='implementation_gap',reason=reason)
                else:
                    try:
                        phase='source';phase_started=time.perf_counter()
                        selected_cutoff = cutoff or recipe['evidence_cutoff']
                        packet,provenance=resolved_packet(entry,recipe,selected_cutoff)
                        row['source_capture'] = provenance
                        if policies[ticker].get('source_peers'):
                            peers = {}
                            provenance['peers'] = {}
                            for dependency in policies[ticker]['source_peers']:
                                peer_entry = next(item for item in registry['entries'] if item['ticker'] == dependency['ticker'])
                                if str(peer_entry['cik']).zfill(10) != dependency['cik']:
                                    raise RuntimeError('source peer registry identity mismatch')
                                peer_recipe = json.loads((runtime_root/'recipes'/f'{peer_entry["ticker"]}.json').read_bytes())
                                peer,peer_provenance=resolved_packet(peer_entry,peer_recipe,selected_cutoff)
                                peer.pop('_selected_controlling_filing',None)
                                peers[peer_entry['ticker']] = peer
                                provenance['peers'][peer_entry['ticker']] = peer_provenance
                            packet = {**packet,'source_peers':peers}
                        if policies[ticker].get('cash_receipt_policy') and not packet.get('cash_receipt_evidence'):
                            from app.us_valuation.cash_receipt_store import attach_cf_receipts
                            from app.us_valuation.refresh_cash_receipts import CashReceiptReviewRequired
                            try:
                                packet = attach_cf_receipts(packet,history_root=runtime_root/'source-validation-cache'/'cash-receipts'/'CF',source_root=ROOT/'output')
                            except CashReceiptReviewRequired as exc:
                                raise EconomicException(str(exc)) from exc
                        narrative_policy = policies[ticker].get('narrative_evidence_policy')
                        if narrative_policy and not packet.get('narrative_evidence'):
                            from app.us_valuation.refresh_narrative_evidence import (
                                NarrativeEvidenceError, validate_narrative_evidence,
                            )
                            receipt_path = runtime_root/'narrative-evidence'/f'{ticker}.json'
                            if not receipt_path.is_file():
                                raise AcquisitionIncomplete('required narrative evidence receipt is not captured')
                            receipt = json.loads(receipt_path.read_bytes())
                            try:
                                packet['narrative_evidence'] = validate_narrative_evidence(
                                    receipt, narrative_policy, source_root=Path(source_root or ROOT/'output').resolve()
                                )
                            except NarrativeEvidenceError as exc:
                                raise EconomicException(str(exc)) from exc
                            provenance['narrative_evidence'] = {
                                'receipt_sha256': receipt['receipt_sha256'],
                                'document_sha256': receipt['source']['document_sha256'],
                                'extraction_version': receipt['extraction_version'],
                            }
                        timings['source']+=time.perf_counter()-phase_started
                        phase='calc';phase_started=time.perf_counter()
                        bound, ledger = bind_current_recipe({**entry,'refresh_policy':policies[ticker]},recipe,packet,selected_cutoff)
                        result = evaluate_recipe(bound)
                        timings['calc']+=time.perf_counter()-phase_started
                        phase='verify';phase_started=time.perf_counter()
                        original = json.loads(baseline.verify_artifact(ticker).read_bytes())
                        public = refreshed_public(original,bound,result,ledger,selected_cutoff)
                        timings['verify']+=time.perf_counter()-phase_started;phase=None
                        row.update(status='cached_source_bound',current_range=result['range'],period_end=ledger['period_end'],
                                   controlling_accession=bound['source_accession'],source_cutoff=selected_cutoff,
                                   confidence=public['reliability']['label'],public_contract_verified=True)
                        evidence[ticker] = {'recipe':bound,'result':result,'ledger':ledger,'source_capture':provenance,'public_artifact':public}
                    except (SourceCaptureError, AcquisitionIncomplete, OSError) as exc:
                        row.update(status='cached_source_gap',reason=str(exc))
                    except EconomicException as exc:
                        row.update(status='source_or_economic_review',reason=str(exc))
                    except (ValueError, KeyError, TypeError, RuntimeError) as exc:
                        row.update(status='implementation_failure',reason=f'{type(exc).__name__}: {exc}')
                    finally:
                        if phase in timings: timings[phase]+=time.perf_counter()-phase_started
            rows.append(row)
            print(json.dumps({'ticker':ticker,'status':row['status']}),flush=True)
        if implementation_fingerprint() != implementation_sha:
            raise RuntimeError('source verification implementation changed during run; rerun before accepting evidence')
        report = {'implementation_sha256':implementation_sha,'registry_sha256':sha256_bytes(registry_raw),'policy_sha256':sha256_bytes(policy_raw),
                  'counts':dict(Counter(row['status'] for row in rows)), 'rows':rows,
                  'evidence_sha256':{ticker:sha256_bytes(canonical_json_bytes(payload)) for ticker,payload in evidence.items()},
                  'scope':'cached binding verification, not publication readiness', 'activated':False}
        report_id = sha256_bytes(canonical_json_bytes(report))
        destination = runtime_root/'source-validation'/report_id
        for ticker, payload in evidence.items():
            atomic(destination/f'{ticker}.json',canonical_json_bytes(payload))
        atomic(destination/'report.json',canonical_json_bytes(report))
        atomic(destination/'report.md',readable_report(report).encode())
        timings['total']=time.perf_counter()-total_started
        return {**report,'report_path':str(destination/'report.json'),'timings':{key:round(value,9) for key,value in timings.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,default=ROOT/'output/us-refresh-runtime')
    parser.add_argument('--ticker',action='append',default=[])
    parser.add_argument('--as-of',dest='cutoff')
    parser.add_argument('--acquisition', help='Verify a frozen live acquisition without retrieving or activating anything')
    parser.add_argument('--source-index',type=Path,help='Frozen cached-source index; avoids recursive output discovery and revalidates selected bytes')
    parser.add_argument('--source-root',type=Path,help='Allowed source root recorded by the index (default: this checkout output)')
    args = parser.parse_args()
    report = verify_sources(args.runtime_root,args.ticker,args.cutoff,args.acquisition,args.source_index,source_root=args.source_root)
    print(json.dumps({key:value for key,value in report.items() if key not in {'rows','evidence_sha256'}},sort_keys=True))
