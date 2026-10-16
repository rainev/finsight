"""Immutable source-event history attached to frozen acquisition packets."""
from pathlib import Path
from datetime import date
import json
import re

from .catalog import canonical_json_bytes, sha256_bytes
from .refresh_cash_receipts import (
    CF_CIK, CashReceiptReviewRequired, extract_cash_receipt_evidence, sum_cash_receipts,
    STANDARD_LITIGATION_GAIN_QNAME,
)


def _validate(evidence, cutoff):
    if evidence.get('schema') != 'FINSIGHT-CASH-RECEIPT-EVIDENCE-1' or evidence.get('ticker') != 'CF' or evidence.get('cik') != CF_CIK:
        raise ValueError('cash receipt history identity/schema mismatch')
    if any(evidence[field] != evidence['event'][field] for field in ('cik','accession','filing_date')):
        raise ValueError('cash receipt history envelope does not match event evidence')
    cash_date = evidence['event']['cash_received_date']
    try:
        sum_cash_receipts([evidence],window_start=cash_date,window_end=cash_date,cutoff=cutoff)
    except CashReceiptReviewRequired as exc:
        raise ValueError('stored cash receipt evidence failed validation') from exc


def load_receipt_history(root: Path, *, cutoff: str):
    rows = []
    for path in sorted(root.glob('*.json')):
        raw = path.read_bytes()
        if not re.fullmatch('[a-f0-9]{64}',path.stem) or sha256_bytes(raw) != path.stem:
            raise ValueError('immutable cash receipt history hash mismatch')
        evidence = json.loads(raw)
        filed = evidence['filing_date']
        date.fromisoformat(filed)
        if filed > cutoff:
            continue
        _validate(evidence,cutoff)
        rows.append(evidence)
    return sorted(rows,key=lambda row:(row['filing_date'],sha256_bytes(canonical_json_bytes(row))))


def _primary_bytes(receipt, *, source_root: Path):
    root = source_root.resolve()
    path = Path(receipt['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('receipt source is outside approved source root')
    raw = path.read_bytes()
    if sha256_bytes(raw) != receipt['raw_payload_sha256']:
        raise ValueError('receipt source raw hash mismatch')
    if path.suffix.lower() in {'.htm','.html'}:
        return raw, receipt['raw_payload_sha256']
    manifest_path = path.parent/'package-manifest.json'
    manifest_raw = manifest_path.read_bytes()
    if sha256_bytes(manifest_raw) != receipt['package_manifest_sha256']:
        raise ValueError('receipt primary package manifest hash mismatch')
    manifest = json.loads(manifest_raw)
    if manifest['accession'] != receipt['accession'] or manifest['cik'] != CF_CIK:
        raise ValueError('receipt primary package identity mismatch')
    name = manifest['entrypoint_local_path']
    if Path(name).name != name:
        raise ValueError('unsafe receipt primary filename')
    files = [row for row in manifest['files'] if row['local_path'] == name]
    if len(files) != 1:
        raise ValueError('receipt primary manifest entry is ambiguous')
    expected = files[0]['sha256']
    # Legacy replay folders keep the parsed JSON and raw package separately.
    # Only exact manifest-hash matches qualify; a matching filename is not proof.
    for candidate in sorted(root.rglob(name)):
        if not candidate.resolve().is_relative_to(root):
            continue
        content = candidate.read_bytes()
        if sha256_bytes(content) == expected:
            return content, expected
    raise ValueError('verified cash receipt primary HTML is not cached')


def attach_cf_receipts(packet: dict, *, history_root: Path, source_root: Path):
    if str(packet['companyfacts']['cik']).zfill(10) != CF_CIK:
        raise ValueError('CF receipt collection received another issuer')
    cutoff = packet['cutoff']
    history = load_receipt_history(history_root,cutoff=cutoff)
    additions = []
    for receipt in packet.get('structural_receipts', []):
        structural = packet.get('structural_packets',{}).get(receipt['accession'])
        if not structural:
            continue
        current_gain = [row for row in structural['facts'] if row.get('qname') == STANDARD_LITIGATION_GAIN_QNAME
                        and row.get('period_end') == receipt['report_date'] and not row.get('dimensions')
                        and isinstance(row.get('value'),(int,float)) and row['value'] > 0]
        if not current_gain:
            continue  # Preserve prior event evidence; this is not a zero inference.
        if sha256_bytes(canonical_json_bytes(structural)) != receipt['structural_sha256']:
            raise ValueError('cash receipt captured structural hash mismatch')
        raw, raw_hash = _primary_bytes(receipt,source_root=source_root)
        additions.append(extract_cash_receipt_evidence(raw,expected_sha256=raw_hash,
            structural_packet=structural,expected_structural_sha256=receipt['structural_sha256'],
            cik=CF_CIK,accession=receipt['accession'],filing_date=receipt['filed_date'],cutoff=cutoff).as_dict())
    combined = history + additions
    if not combined:
        raise FileNotFoundError('required historical CF cash receipt evidence is not captured')
    dates = [row['event']['cash_received_date'] for row in combined]
    sum_cash_receipts(combined,window_start=min(dates),window_end=max(dates),cutoff=cutoff)
    history_root.mkdir(parents=True,exist_ok=True)
    from .refresh_job import atomic
    for evidence in additions:
        raw = canonical_json_bytes(evidence)
        path = history_root/(sha256_bytes(raw)+'.json')
        atomic(path,raw)
    frozen = load_receipt_history(history_root,cutoff=cutoff)
    return {**packet,'cash_receipt_evidence':frozen,
            'cash_receipt_evidence_sha256':sha256_bytes(canonical_json_bytes(frozen))}
