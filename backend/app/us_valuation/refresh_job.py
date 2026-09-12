"""Single-writer, resumable refresh/replay orchestration without an AI runtime."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import tempfile

from .catalog import canonical_json_bytes, sha256_bytes, load_catalog_version, artifact_tree_sha256
from .calculation_recipe import evaluate_recipe, recipe_hash
from .calculator import baseline_version
from .refresh_bindings import bind_current_recipe, EconomicException, AcquisitionIncomplete
from .refresh_catalog_store import RefreshCatalogStore, load_frozen_registry, load_retry_states
from .sec_client import SecClient
from .artifacts import sanitize_public_artifact
from .reliability import assess_reliability
from .refresh_source_ingestion import capture_company_source
from .forecast_vintage_store import ForecastVintageStore
from .refresh_forecasts import track_company_refresh


class MigrationIncomplete(RuntimeError):
    pass


def refreshed_recipe_version(recipe: dict, policy: dict) -> str:
    """Pin calculation semantics, not acquisition timestamps or old version labels."""
    semantics = {'schema_version':recipe['schema_version'], 'ticker':recipe['ticker'],
        'scenarios':recipe['scenarios'], 'editable':recipe.get('editable', {}),
        'model_version':recipe.get('model_version'), 'policy':policy}
    return 'US-REFRESH-RECIPE-1-' + sha256_bytes(canonical_json_bytes(semantics))[:24]


def configured_sec_user_agent(root: Path) -> str:
    value = os.environ.get('SEC_USER_AGENT', '').strip()
    config_path = root / 'runtime-config.json'
    if not value and config_path.is_file():
        config = json.loads(config_path.read_bytes())
        if config.get('schema_version') != 'FINSIGHT-US-REFRESH-RUNTIME-1':
            raise ValueError('unsupported refresh runtime configuration')
        value = config.get('sec_user_agent', '')
    if not isinstance(value,str) or '@' not in value or any(char in value for char in '\r\n'):
        raise ValueError('SEC_USER_AGENT with monitored contact is required for live refresh')
    return value.strip()


def configured_parse_timeout(root: Path, ticker: str) -> int:
    path = root / 'runtime-config.json'
    config = json.loads(path.read_bytes()) if path.is_file() else {}
    value = config.get('issuer_parse_timeouts', {}).get(ticker,120)
    if isinstance(value,bool) or not isinstance(value,int) or not 30 <= value <= 600:
        raise ValueError('issuer parse timeout must be from 30 to 600 seconds')
    return value


def policy_readiness(recipe: dict, policy: object) -> tuple[bool, str | None]:
    """Do not equate a version string with a completed next-filing adapter."""
    if not isinstance(policy, dict) or not policy.get('version'):
        return False, 'refresh policy missing'
    engines = {spec['engine'] for spec in recipe['scenarios'].values()}
    if policy.get('schema_version') == 'FINSIGHT-CYCLICAL-FCFF-REFRESH-POLICY-1':
        if recipe.get('ticker') != 'WDC' or policy.get('ticker') != 'WDC' or engines != {'cyclical_fcff_quantile'}:
            return False, 'cyclical source adapter identity or engine mismatch'
        if policy.get('source_peers') != [{'ticker':'STX','cik':'0001137789'}] or policy.get('peer_ticker') != 'STX' or policy.get('peer_cik') != '0001137789' or not policy.get('statement_required_fields'):
            return False, 'cyclical peer/source contract incomplete'
        return True, None
    if policy.get('schema_version') == 'FINSIGHT-ASSET-RUNWAY-REFRESH-POLICY-1':
        if engines != {'asset_runway'} or policy.get('ticker') != recipe.get('ticker') or recipe.get('ticker') != 'MRNA':
            return False, 'asset-runway adapter identity or engine mismatch'
        if not policy.get('statement_required_fields') or not policy.get('burn_policy') or not policy.get('cik'):
            return False, 'asset-runway source selection contract incomplete'
        return True,None
    if policy.get('schema_version') == 'FINSIGHT-EARNINGS-REFRESH-POLICY-1':
        from .refresh_earnings_policies import SUPPORTED_TICKERS
        if engines != {'earnings_multiple'} or policy.get('ticker') != recipe.get('ticker') or recipe.get('ticker') not in SUPPORTED_TICKERS:
            return False, 'equity-earnings adapter identity or engine mismatch'
        if not policy.get('statement_required_fields') or not policy.get('approved_sensitivities') or not policy.get('cik'):
            return False, 'equity-earnings source selection contract incomplete'
        return True, None
    if policy.get('schema_version') == 'FINSIGHT-CASH-SCHEDULE-REFRESH-POLICY-1':
        if engines != {'cash_schedule'} or policy.get('ticker') != recipe.get('ticker') or recipe.get('ticker') not in {'AAPL','MSFT'}:
            return False, 'cash-schedule source adapter identity or engine mismatch'
        if not policy.get('statement_required_fields') or not policy.get('policy_assumptions'):
            return False, 'cash-schedule source selection contract missing'
        if recipe.get('ticker') == 'MSFT' and not policy.get('approved_forecast_policy'):
            return False, 'MSFT compiled forecast policy missing'
        return True, None
    if policy.get('schema_version') == 'FINSIGHT-SPECIAL-REFRESH-POLICY-1' and policy.get('ticker') == recipe.get('ticker') == 'APTV':
        if engines != {'earnings_multiple'} or policy.get('unresolved_economic_rules') or not policy.get('statement_required_fields'):
            return False, 'APTV continuing-equity source contract incomplete'
        return True, None
    if policy.get('schema_version') == 'FINSIGHT-RESIDUAL-REFRESH-POLICY-1':
        if engines != {'residual_income'} or policy.get('ticker') != recipe.get('ticker') or not policy.get('cik'):
            return False, 'residual policy identity or engine mismatch'
        if not policy.get('concept_config', {}).get('fields') or not policy.get('statement_required_fields'):
            return False, 'residual source selection contract missing'
        return True, None
    engine = policy.get('supported_engine')
    if engine not in {'enterprise_cash_fcff','constant_growth_fcff'}:
        return False, 'specialist refresh adapter not integrated'
    if engines != {engine}:
        return False, 'refresh engine does not match recipe'
    inputs, bindings = policy.get('inputs'), policy.get('scenario_bindings')
    if not isinstance(inputs, dict) or not inputs or not isinstance(bindings, dict) or set(bindings) != {'bear','base','bull'}:
        return False, 'complete source selectors and three scenario bindings required'
    required = ({'cash_fcff','cash_and_investments','interest_bearing_debt','preferred_equity','noncontrolling_interests','diluted_shares'}
                if engine == 'enterprise_cash_fcff' else {'revenue','fcff_margin','cash_and_investments','debt','noncontrolling_interests','shares'})
    if any(not isinstance(fields, dict) or not required <= set(fields) for fields in bindings.values()):
        return False, 'current cash, debt, claims and share refresh bindings incomplete'
    if policy.get('unresolved_economic_rules') or policy.get('reason_codes'):
        return False, 'issuer-specific economic rule migration remains incomplete'
    from .refresh_financials import POLICY_VERSION as cash_history_version
    if policy.get('normalization_version') != cash_history_version:
        return False, 'cash normalization policy version missing'
    if not any(rule.get('selector')=='normalized_bridge' for rule in inputs.values()):
        return False, 'source-reconciled bridge binding required'
    # This is executable-contract readiness, not a claim about an unseen filing.
    # Every source and financial check still runs before staging/activation.
    return True, None


def atomic(path: Path, payload: bytes, *, immutable: bool = True) -> None:
    if immutable and path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f'immutable output drift: {path.name}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.write-')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


@contextmanager
def writer(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'writer.lock').open('a') as handle:
        try: fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise RuntimeError('another valuation refresh is running') from exc
        try: yield
        finally: fcntl.flock(handle, fcntl.LOCK_UN)


def preflight(root: Path) -> dict:
    frozen_registry = load_frozen_registry(root / 'registry.json')
    registry = json.loads((root / 'registry.json').read_text())
    baseline = load_catalog_version(root / 'baseline')
    if {(e.ticker, e.cik, e.batch) for e in frozen_registry.entries} != {(e.ticker, e.cik, e.batch) for e in baseline.entries}:
        raise ValueError('registry identity or batch differs from frozen baseline')
    if baseline.manifest_sha256 != registry['baseline_manifest_sha256']:
        raise ValueError('migration baseline manifest drift')
    policies_path = root / 'refresh-policies.json'
    policies = json.loads(policies_path.read_text()) if policies_path.exists() else {}
    rows = []
    for entry in registry['entries']:
        path = root / 'recipes' / f"{entry['ticker']}.json"
        numeric = baseline.entry_by_ticker[entry['ticker']].availability_type != 'not_available'
        recipe_ready = path.is_file()
        if recipe_ready:
            recipe = json.loads(path.read_text())
            public = sanitize_public_artifact(json.loads(baseline.verify_artifact(entry['ticker']).read_text()))
            actual = evaluate_recipe(recipe)['range']
            import math
            if recipe.get('ticker') != entry['ticker'] or recipe.get('baseline_version') != baseline_version(public) or any(not math.isclose(actual[k], public['scenario_range'][k], abs_tol=1e-7, rel_tol=1e-9) for k in ('low','base','high')):
                raise ValueError(f"{entry['ticker']}: invalid migration recipe")
        policy = policies.get(entry['ticker'])
        ready, reason = policy_readiness(recipe, policy) if recipe_ready and numeric else (False, 'executable recipe missing' if numeric else 'prior unavailable')
        rows.append({'ticker': entry['ticker'], 'numeric': numeric, 'recipe_ready': recipe_ready,
                     'refresh_ready': ready, 'refresh_reason': reason})
    return {'issuer_count': len(rows), 'numeric_count': sum(row['numeric'] for row in rows),
            'recipe_ready_count': sum(row['numeric'] and row['recipe_ready'] for row in rows),
            'refresh_ready_count': sum(row['numeric'] and row['refresh_ready'] for row in rows), 'rows': rows}


def checked_packet(packet: object, entry: dict) -> dict:
    """Payload faults are acquisition failures, never new financial invalidity."""
    if not isinstance(packet, dict):
        return {'acquisition_failed': 'missing_or_malformed_packet'}
    if packet.get('acquisition_failed'):
        return deepcopy(packet)
    for name in ('submissions', 'companyfacts'):
        source = packet.get(name)
        cik = source.get('cik') if isinstance(source, dict) else None
        if isinstance(cik, bool) or not isinstance(cik, (int, str)) or not str(cik).isdigit() or str(cik).zfill(10) != str(entry['cik']).zfill(10):
            return {'acquisition_failed': 'source_identity_or_shape_invalid',
                    'rejected_payload_sha256': sha256_bytes(canonical_json_bytes(packet))}
    return deepcopy(packet)


def materialize_packet(root: Path, packet: object, entry: dict) -> dict:
    if isinstance(packet, dict) and 'packet_ref' in packet:
        relative = Path(packet['packet_ref'])
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to((root/'acquisitions').resolve()):
            raise ValueError('source packet reference escapes immutable acquisition storage')
        raw = path.read_bytes()
        if sha256_bytes(raw) != packet.get('sha256'):
            raise ValueError('frozen source packet reference hash mismatch')
        checkpoint = json.loads(raw)
        if checkpoint.get('ticker') != entry['ticker'] or checkpoint.get('cik') != entry['cik']:
            raise ValueError('frozen source packet reference identity mismatch')
        if sha256_bytes(canonical_json_bytes(checkpoint['packet'])) != checkpoint.get('packet_sha256'):
            raise ValueError('frozen source packet payload hash mismatch')
        return checked_packet(checkpoint['packet'], entry)
    return checked_packet(packet, entry)


def attach_source_peers(root: Path, packet: dict, policy: dict, packets: dict, registry: dict, cutoff: str) -> dict:
    """Resolve declared peer evidence from this same frozen snapshot, never the network."""
    if packet.get('acquisition_failed') or not policy.get('source_peers'):
        return packet
    entries = {row['ticker']:row for row in registry['entries']}
    peers = {}
    for dependency in policy['source_peers']:
        ticker = dependency['ticker']
        entry = entries.get(ticker)
        if not entry or entry['cik'] != dependency['cik'] or ticker in peers:
            raise RuntimeError('invalid or duplicate source peer registry binding')
        peer = materialize_packet(root, packets.get(ticker), entry)
        if peer.get('acquisition_failed') or peer.get('cutoff',cutoff) != cutoff:
            return {'acquisition_failed':'required_peer_source_unavailable','peer_ticker':ticker}
        peer.pop('_selected_controlling_filing',None)
        peers[ticker] = peer
    return {**packet,'source_peers':peers}


def checked_snapshot(evidence: object, registry: dict, cutoff: str, *, root: Path | None = None) -> dict:
    if not isinstance(evidence, dict) or evidence.get('cutoff') != cutoff or not isinstance(evidence.get('packets'), dict):
        raise ValueError('source snapshot structure or cutoff mismatch')
    expected = {row['ticker'] for row in registry['entries']}
    if set(evidence['packets']) - expected:
        raise ValueError('source snapshot has companies outside the frozen registry')
    packets = {}
    for entry in registry['entries']:
        packet = evidence['packets'].get(entry['ticker'])
        if isinstance(packet, dict) and 'packet_ref' in packet:
            if root is None: raise ValueError('referenced snapshot requires runtime root')
            materialize_packet(root, packet, entry)
            packets[entry['ticker']] = packet
        else:
            packets[entry['ticker']] = checked_packet(packet, entry)
    return {**evidence, 'packets': packets}


def capture(root: Path, registry: dict, cutoff: str, user_agent: str, *, acquisition_id: str | None = None, context_fingerprint: str | None = None, references: bool = False, source_policies: dict | None = None, recipe_cutoffs: dict | None = None) -> dict:
    """Freeze successful per-company retrievals so interruption cannot lose them.

    A resumed acquisition keeps its original cutoff and successful packets.
    Explicitly failed companies may retry through the bounded SEC client. The
    orchestration writer lock protects this multi-file transaction.
    """
    if not isinstance(user_agent, str) or '@' not in user_agent:
        raise ValueError('SEC_USER_AGENT with monitored contact is required for live refresh')
    registry_hash = sha256_bytes(canonical_json_bytes(registry))
    agent_hash = sha256_bytes(user_agent.encode())
    if acquisition_id is None:
        descriptor = {'cutoff': cutoff, 'registry_sha256': registry_hash,
                      'user_agent_sha256': agent_hash,
                      'context_fingerprint': context_fingerprint,
                      'started_at': datetime.now(timezone.utc).isoformat()}
        acquisition_id = sha256_bytes(canonical_json_bytes(descriptor))
    else:
        if len(acquisition_id) != 64 or any(c not in '0123456789abcdef' for c in acquisition_id):
            raise ValueError('invalid acquisition identifier')
        descriptor = json.loads((root / 'acquisitions' / acquisition_id / 'input.json').read_bytes())
        if sha256_bytes(canonical_json_bytes(descriptor)) != acquisition_id:
            raise ValueError('acquisition descriptor hash mismatch')
        if (descriptor['cutoff'], descriptor['registry_sha256'], descriptor['user_agent_sha256']) != (cutoff, registry_hash, agent_hash):
            raise ValueError('resume must preserve acquisition cutoff, registry and SEC contact')
        if descriptor.get('context_fingerprint') != context_fingerprint:
            raise ValueError('resume must preserve predecessor, policies and recipes')
    acquisition_root = root / 'acquisitions' / acquisition_id
    atomic(acquisition_root / 'input.json', canonical_json_bytes(descriptor))
    atomic(root / 'acquisition-status.json', canonical_json_bytes({'acquisition_id': acquisition_id, 'cutoff': cutoff, 'status': 'capturing'}), immutable=False)
    client = SecClient(user_agent=user_agent, cache_dir=root / 'source-cache')
    packets = {}
    for entry in registry['entries']:
        checkpoint = acquisition_root / 'packets' / f"{entry['ticker']}.json"
        if checkpoint.exists():
            recorded = json.loads(checkpoint.read_bytes())
            if recorded['ticker'] != entry['ticker'] or recorded['cik'] != entry['cik'] or sha256_bytes(canonical_json_bytes(recorded['packet'])) != recorded['packet_sha256']:
                raise ValueError('acquisition checkpoint identity or hash mismatch')
            packets[entry['ticker']] = {'packet_ref':str(checkpoint.relative_to(root)), 'sha256':sha256_bytes(checkpoint.read_bytes())} if references else recorded['packet']
            continue
        try:
            packets[entry['ticker']] = {'submissions': client.submissions(entry['cik'], refresh=True),
                                         'companyfacts': client.companyfacts(entry['cik'], refresh=True)}
            if source_policies is not None:
                policy = source_policies.get(entry['ticker'], {})
                requirements = policy.get('source_requirements', {})
                packets[entry['ticker']] = capture_company_source(ticker=entry['ticker'], cik=entry['cik'], cutoff=cutoff,
                    cache_dir=root/'source-cache', user_agent=user_agent, refresh=False,
                    require_structural=requirements.get('structural', True),
                    event_since=(recipe_cutoffs or {}).get(entry['ticker']),
                    allowed_event_items=policy.get('routine_8k_items', ('2.02','9.01')),
                    arelle_timeout_seconds=configured_parse_timeout(root,entry['ticker']),
                    capture_event_relationships=True)
                if policy.get('cash_receipt_policy'):
                    from .cash_receipt_store import attach_cf_receipts
                    from .refresh_cash_receipts import CashReceiptReviewRequired
                    try:
                        packets[entry['ticker']] = attach_cf_receipts(packets[entry['ticker']],history_root=root/'normalization-events'/'CF',source_root=root/'source-cache')
                    except CashReceiptReviewRequired as exc:
                        # A received but economically unreconciled disclosure
                        # is not a temporary download failure.
                        packets[entry['ticker']]['normalization_review_required'] = str(exc)
                if policy.get('narrative_evidence_policy'):
                    from .refresh_narrative_evidence import extract_narrative_evidence
                    packet=packets[entry['ticker']]
                    accession=(packet.get('controlling_filing') or {}).get('accessionNumber')
                    receipts=[row for row in packet.get('structural_receipts',[]) if row.get('accession')==accession]
                    if len(receipts)!=1:
                        raise ValueError('current narrative filing package is missing or ambiguous')
                    entrypoint=Path(str(receipts[0].get('path',''))).resolve()
                    package_manifest=entrypoint.parent/'package-manifest.json'
                    packet['narrative_evidence']=extract_narrative_evidence(
                        policy['narrative_evidence_policy'],package_manifest,source_root=(root/'source-cache').resolve())
        except (OSError, RuntimeError, ValueError) as exc:
            cause = exc
            for _ in range(8):
                if cause.__cause__ is None: break
                cause = cause.__cause__
            packets[entry['ticker']] = {'acquisition_failed': type(exc).__name__, 'diagnostic':str(exc),
                'cause_type':type(cause).__name__, 'http_status':getattr(cause,'code',None)}
            continue
        packet = packets[entry['ticker']]
        packet = checked_packet(packet, entry)
        packets[entry['ticker']] = packet
        if packet.get('acquisition_failed'):
            continue
        atomic(checkpoint, canonical_json_bytes({'ticker': entry['ticker'], 'cik': entry['cik'],
               'packet_sha256': sha256_bytes(canonical_json_bytes(packet)), 'packet': packet}))
        if references:
            packets[entry['ticker']] = {'packet_ref':str(checkpoint.relative_to(root)), 'sha256':sha256_bytes(checkpoint.read_bytes())}
    result = {'cutoff': cutoff, 'packets': packets, 'acquisition_id': acquisition_id}
    # Each completed attempt is retained; retrying failed issuers is a new
    # attempt on the same successful frozen acquisition, never an overwrite.
    atomic(acquisition_root / 'attempts' / f'{sha256_bytes(canonical_json_bytes(result))}.json', canonical_json_bytes(result))
    atomic(root / 'acquisition-status.json', canonical_json_bytes({'acquisition_id': acquisition_id, 'cutoff': cutoff,
           'status': 'captured', 'failure_count': sum('acquisition_failed' in packet for packet in packets.values())}), immutable=False)
    return result


def _unavailable(public: dict, reason: str, *, cutoff: str | None = None,
                 source_packet: dict | None = None) -> dict:
    from .refresh_unavailable import build_unavailable_public_record
    return build_unavailable_public_record(public, reason, cutoff or public['valuation_date'],
        source_packet=source_packet)


def refreshed_public(public: dict, recipe: dict, valued: dict, ledger: dict, cutoff: str) -> dict:
    """Update every canonical numeric surface together, then enforce the sanitizer."""
    value = deepcopy(public)
    value['valuation_date'] = cutoff
    value['assumption_date'] = ledger.get('assumption_date', cutoff)
    value['model_version'] = recipe.get('model_version') or recipe['recipe_version']
    filing = ledger['controlling_filing']
    cik = int(value['issuer']['cik'])
    accession = filing['accessionNumber']
    value['source_financial_statement'] = {
        'accession': accession, 'form': filing['form'], 'period_end': filing['reportDate'], 'filed_date': filing['filingDate'],
        'url': f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{filing['primaryDocument']}",
        'note': 'Current evidence selected by the deterministic refresh policy.'}
    primary = value['model_policy']['primary']
    field = 'conditional_value_per_share' if primary == 'conditional_estimate' else 'intrinsic_value_per_share'
    value['model_policy']['supporting'] = []
    value['model_policy']['reason'] = 'One primary versioned model is recalculated from current supported evidence; supporting estimates are not blended.'
    def model(amount):
        return {'model': primary, 'output_type': field, 'currency': value['currency'], field: amount,
                'publication_state': 'review_required', 'errors': [], 'warnings': []}
    value['models'] = {primary: model(valued['range']['base'])}
    value['scenarios'] = {} if primary == 'conditional_estimate' else {name: {primary: model(valued['scenarios'][name]['value'])} for name in ('bear','base','bull')}
    value['scenario_range'] = {**valued['range'], 'label': 'assumption range, not a statistical confidence interval'}
    value['sensitivities'] = []
    value['review']['publication_state'] = 'review_required'
    value['review']['errors'] = []
    value.pop('automated_review', None)
    value.pop('forecast_quality', None)  # Prior forecast checks do not certify new inputs.
    if primary == 'fcff_dcf':
        # An exact equity calculation does not establish source completeness.
        # Until the binding supplies the existing bridge validator's output,
        # this is a global implementation gate, not issuer economic invalidity.
        if not isinstance(ledger.get('bridge_quality'), dict):
            raise RuntimeError('current FCFF bridge reconciliation has not been integrated; catalog unchanged')
        from .bridge_policy import BridgeAssessment
        from .artifacts import _validated_public_bridge_quality
        assessed = BridgeAssessment.from_dict(ledger['bridge_quality'])
        raw_range = assessed.intrinsic_value_range
        bridge_dto = {'decision':assessed.decision,'complete':assessed.decision == 'complete','usable':assessed.usable,
            'bounded_fields':list(assessed.bounded_fields),'blocking_fields':list(assessed.blocking_fields),'reason_codes':list(assessed.reason_codes),
            'intrinsic_value_range':{**(raw_range.as_dict() if raw_range else {'low':None,'midpoint':None,'high':None}),
                'spread_ratio':assessed.spread_ratio,'spread_limit':assessed.spread_limit}}
        value['bridge_quality'] = _validated_public_bridge_quality(bridge_dto,allow_bounded_over_limit=True)
        if value['bridge_quality'] is None:
            raise ValueError('source-derived bridge assessment failed public DTO validation')
    source_cap = public.get('reliability', {}).get('source_cap', 'Low')
    model_cap = public.get('reliability', {}).get('model_cap', 'Low')
    accounting = (ledger.get('bridge_quality') or {}).get('intrinsic_value_range') or {}
    value['reliability'] = assess_reliability(accounting_low=accounting.get('low',valued['range']['base']), accounting_base=accounting.get('midpoint',valued['range']['base']), accounting_high=accounting.get('high',valued['range']['base']),
                                             scenario_low=valued['range']['low'], scenario_base=valued['range']['base'], scenario_high=valued['range']['high'],
                                             source_cap=source_cap, model_cap=model_cap).as_dict()
    base_inputs = recipe['scenarios']['base']['inputs']
    aliases = {'initial_growth': 'initial_revenue_growth', 'wacc': 'policy_wacc', 'terminal_growth': 'terminal_growth',
               'cost_of_equity': 'cost_of_equity', 'current_roe': 'current_roe', 'current_payout_ratio': 'current_payout_ratio', 'terminal_roe': 'terminal_roe', 'forecast_years': 'forecast_years',
               'book_value_per_share':'book_value_per_share','growth':'initial_revenue_growth'}
    for private_key, public_key in aliases.items():
        if private_key in base_inputs: value['public_assumptions'][public_key] = base_inputs[private_key]
    engine = recipe['scenarios']['base']['engine']
    assumptions = value['public_assumptions']
    share_key = 'diluted_shares' if engine in {'enterprise_cash_fcff','cyclical_fcff_quantile'} else 'shares'
    if share_key in base_inputs:
        source_shares = [spec['inputs'][share_key] for spec in recipe['scenarios'].values()]
        assumptions.update(diluted_shares=base_inputs[share_key],diluted_shares_low=min(source_shares),diluted_shares_high=max(source_shares))
    if engine == 'earnings_multiple':
        for key in ('cash_conversion_margin','cash_conversion_margin_low','cash_conversion_margin_high','starting_cash_fcff_per_share'):
            assumptions.pop(key,None)
        assumptions.update(earnings_multiple=base_inputs['multiple'],forecast_mode='normalized_equity_earnings')
    elif engine == 'cash_schedule':
        current_assumptions = ledger.get('scenario_results', {}).get('base', {}).get('assumptions', {})
        for key in ('initial_revenue_growth','target_operating_margin','sales_to_capital','normalized_tax_rate'):
            if key in current_assumptions: assumptions[key] = current_assumptions[key]
        assumptions.update(policy_wacc=base_inputs['discount_rate'],forecast_years=len(base_inputs['cash_flows']))
    elif engine == 'enterprise_cash_fcff':
        assumptions['starting_cash_fcff_per_share'] = base_inputs['cash_fcff'] / base_inputs['diluted_shares']
    floor_applied = any(row['raw_value'] < 0 and row['value'] == 0 for row in valued['scenarios'].values())
    assumptions['equity_floor_applied'] = floor_applied
    assumptions['equity_floor_basis'] = 'limited-liability floor on negative raw equity scenario' if floor_applied else 'not applied'
    value['review']['confidence_grade'] = value['reliability']['label'].lower()
    value['public_assumptions']['forecast_policy_version'] = ledger['policy_version']
    normalization = ledger.get('normalization', {})
    if normalization.get('method'):
        assumptions['normalization_basis'] = normalization['method']
    if 'cash_conversion_margin' in normalization:
        margins = normalization['cash_conversion_margin']
        value['public_assumptions'].update(cash_conversion_margin=margins['base'],cash_conversion_margin_low=margins['low'],cash_conversion_margin_high=margins['high'],
            history_years_used=len(normalization['annual']),normalization_basis='aligned annual company cash-conversion history')
        financing_explanation = ('Starts with reported operating cash flow, deducts total reported capital spending, and adds interest after the versioned tax adjustment. '
            if normalization.get('policy_version') == 'US-REFRESH-CASH-HISTORY-1' else
            'Starts with reported operating cash flow and deducts total reported capital spending. The signed financing adjustment removes net nonoperating interest income when a complete net series is reported; otherwise it adds reported gross expense as a disclosed proxy. ')
        if normalization.get('financing_adjustment_basis') == 'cash_interest_paid_proxy':
            financing_explanation = ('Starts with reported operating cash flow, deducts total reported capital spending, and adds source-linked cash interest paid after the versioned tax adjustment. Cash interest is an explicit issuer-specific proxy, not reported accrual interest expense. ')
        elif normalization.get('financing_adjustment_basis') == 'owner_cash_no_financing_adjustment':
            financing_explanation = 'The owner-cash model starts with reported operating cash flow less total reported capital spending, without an interest or tax adjustment. Its debt-free scope requires separate source validation. '
        value['normalization_explanation'] = financing_explanation + (
            'Sustainable cash conversion uses comparable company annual history. Working-capital movements remain in reported cash flow unless separately reconciled; '
            'there are no automatic unusual-item or stock-compensation addbacks. Growth applies to the post-capex cash starting point.'
        )
        if ledger.get('margin_stress'):
            margins = ledger['margin_stress']['effective_margins']
            assumptions.update(cash_conversion_margin=margins['base'],cash_conversion_margin_low=margins['bear'],cash_conversion_margin_high=margins['bull'])
            value['normalization_explanation'] += ' Scenario cash-conversion haircuts are applied after historical normalization. They are governed assumptions, not reported working-capital corrections; the source cash flows are unchanged.'
    elif ledger.get('recipe_engine') == 'residual_income':
        value['normalization_explanation'] = ('Starts with reported parent equity less evidenced preferred claims and current reported diluted shares. '
            'Common earnings/equity history informs the return-on-equity range when comparable; otherwise the approved scenario-specific ROE assumptions remain explicit. '
            'Funding debt and customer liabilities remain inside the equity model, not a second enterprise-value deduction.')
    elif ledger.get('recipe_engine') == 'earnings_multiple':
        if normalization.get('annualization_factor') is not None:
            value['normalization_explanation'] = ('Starts with current and comparable continuing earnings attributable to the parent. '
                'Annualization uses the reported fiscal duration; approved earnings-multiple and dilution sensitivities remain fixed. '
                'Minority earnings are not deducted a second time and no separate enterprise debt deduction is applied.')
        else:
            value['normalization_explanation'] = ('Starts with reported annual parent/common earnings and current reported diluted shares. '
                'The sustainable earnings range uses the approved company-history quantiles; current TTM earnings are retained as a diagnostic. '
                'Approved valuation multiples and share sensitivities remain fixed, and no second enterprise debt deduction is applied.')
    elif ledger.get('recipe_engine') == 'cash_schedule':
        value['normalization_explanation'] = ('Starts with aligned reported revenue and operating income. Company margin, growth, tax and total-capex history inform the forecast; '
            'forecast growth requires reinvestment through the approved capital-efficiency rule. Each annual cash flow and terminal value is recalculated independently. '
            'Current cash, debt, other claims and source shares are reconciled separately.')
    elif ledger.get('recipe_engine') == 'asset_runway':
        value['normalization_explanation'] = ('Starts with reported cash and investment balances, less reported debt and finance leases. '
            'Recent annual and current TTM cash burn determine the versioned runway reserves. Current reported share counts remain locked. '
            'Clinical pipeline success is explicitly outside this model, not filled in with an invented value.')
    elif ledger.get('recipe_engine') == 'cyclical_fcff_quantile':
        value['normalization_explanation'] = ('Starts with reported continuing-operation revenue, operating profit, depreciation and total capital spending. '
            'Company and peer operating histories inform the cyclical range. Working-capital inputs must be source-complete; missing balances are not zeros. '
            'Cash, financing claims and reported share sensitivities are reconciled separately.')
    if normalization.get('cash_receipt_adjustment') is not None:
        value['normalization_explanation'] += ' Identified nonrecurring operating cash receipts are removed only from the historical or current windows containing their actual cash dates, without an unsupported tax reversal.'
    if ledger.get('normalized_bridge', {}).get('capital_structure_projection'):
        value['normalization_explanation'] += ' Reported diluted shares include assumed preferred conversion; the preferred carrying value is retained as evidence but is not deducted again.'
    value['review']['warnings'] = [
        'Source-refreshed valuation under versioned model assumptions; the scenario range is not a statistical confidence interval.',
        *normalization.get('limitations', []),
        *((ledger['bridge_quality']['warning'],) if ledger.get('bridge_quality', {}).get('warning') else ()),
    ]
    sanitized = sanitize_public_artifact(value)
    if sanitized['scenario_range']['base'] != valued['range']['base']:
        raise ValueError('refreshed artifact failed canonical publication checks')
    return sanitized


def _forecast_file_index(root: Path) -> dict[str, str]:
    """Freeze append-only forecast inputs, excluding transient writer locks."""
    return {str(path.relative_to(root)): sha256_bytes(path.read_bytes())
            for path in sorted(root.rglob('*')) if path.is_file() and path.suffix in {'.json', '.sha256'}}


def _copy_forecast_inputs(source: Path, destination: Path, index: dict) -> None:
    for relative, digest in index.items():
        path = source / relative
        target = destination / relative
        if not path.resolve().is_relative_to(source.resolve()) or not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError('unsafe frozen forecast path')
        payload = path.read_bytes()
        if sha256_bytes(payload) != digest:
            raise ValueError('immutable forecast input drift')
        atomic(target, payload)


def execute(root: Path, *, mode: str, cutoff: str | None = None, snapshot: str | None = None, source_file: Path | None = None, acquisition_id: str | None = None) -> dict:
    root = root.resolve()
    if mode not in {'stage','publish','replay'}: raise ValueError('unknown refresh mode')
    if acquisition_id and (source_file is not None or mode == 'replay'):
        raise ValueError('acquisition resume cannot be combined with offline input or frozen replay')
    with writer(root):
        registry_raw = (root / 'registry.json').read_bytes()
        registry = json.loads(registry_raw)
        registry_contract = load_frozen_registry(root / 'registry.json')
        if registry_contract.registry_sha256 != sha256_bytes(registry_raw):
            raise ValueError('registry changed during refresh startup')
        store = RefreshCatalogStore(root / 'catalogs', frozen_registry=registry_contract)
        if mode == 'replay':
            if not snapshot or len(snapshot) != 64 or any(c not in '0123456789abcdef' for c in snapshot): raise ValueError('safe snapshot run id required')
            frozen = json.loads((root / 'runs' / snapshot / 'input.json').read_text())
            if frozen['registry_sha256'] != sha256_bytes(registry_raw): raise ValueError('snapshot registry drift')
            policies, recipes = frozen['policies'], frozen['recipes']
            predecessor = root / frozen['predecessor']['relative_path']
            if not predecessor.resolve().is_relative_to(root): raise ValueError('unsafe predecessor path')
            baseline = load_catalog_version(predecessor, expected_manifest_sha256=frozen['predecessor']['manifest_sha256'])
            retry_states = load_retry_states(baseline,registry_contract)
            if retry_states != frozen.get('retry_states', {}):
                raise ValueError('frozen retry states do not match the immutable predecessor')
        else:
            readiness = preflight(root)
            atomic(root / 'migration-readiness.json', canonical_json_bytes(readiness), immutable=False)
            if readiness['recipe_ready_count'] != readiness['numeric_count'] or readiness['refresh_ready_count'] != readiness['numeric_count']:
                raise MigrationIncomplete(f"migration gate: {readiness['recipe_ready_count']}/{readiness['numeric_count']} exact recipes; {readiness['refresh_ready_count']}/{readiness['numeric_count']} refresh bindings; catalog unchanged")
            policies = json.loads((root / 'refresh-policies.json').read_bytes())
            has_active = store.active_pointer_path.exists()
            baseline = store.reader().get_snapshot() if has_active else load_catalog_version(root / 'baseline')
            retry_states = load_retry_states(baseline,registry_contract)
            recipe_root = baseline.root / 'recipes' if 'private_recipe_sha256' in baseline.manifest else root / 'recipes'
            recipes = {}
            for entry in baseline.entries:
                if entry.availability_type == 'not_available':
                    if entry.ticker in retry_states:
                        recipes[entry.ticker] = deepcopy(retry_states[entry.ticker]['recipe'])
                    continue
                payload = (recipe_root / f'{entry.ticker}.json').read_bytes()
                expected = baseline.manifest.get('private_recipe_sha256', {}).get(entry.ticker)
                if expected and sha256_bytes(payload) != expected: raise ValueError('predecessor recipe hash mismatch')
                recipes[entry.ticker] = json.loads(payload)
            now = datetime.now(timezone.utc)
            if acquisition_id and cutoff is None:
                if len(acquisition_id) != 64 or any(c not in '0123456789abcdef' for c in acquisition_id):
                    raise ValueError('invalid acquisition identifier')
                cutoff = json.loads((root / 'acquisitions' / acquisition_id / 'input.json').read_text())['cutoff']
            cutoff = cutoff or now.date().isoformat()
            from datetime import date
            date.fromisoformat(cutoff)
            context_fingerprint = sha256_bytes(canonical_json_bytes({'policies': policies, 'recipes': recipes, 'predecessor': baseline.manifest_sha256}))
            evidence = json.loads(source_file.read_text()) if source_file else capture(root, registry, cutoff, configured_sec_user_agent(root), acquisition_id=acquisition_id, context_fingerprint=context_fingerprint, references=True,
                      source_policies=policies, recipe_cutoffs={ticker:recipe.get('evidence_cutoff') for ticker,recipe in recipes.items()})
            evidence = checked_snapshot(evidence, registry, cutoff, root=root)
            frozen = {'registry_sha256': sha256_bytes(registry_raw), 'cutoff': cutoff,
                      'policies': policies, 'recipes': recipes, 'evidence': evidence, 'retry_states':retry_states,
                      'predecessor': {'relative_path': str(baseline.root.relative_to(root)), 'manifest_sha256': baseline.manifest_sha256},
                      'expected_active_manifest_sha256': baseline.manifest_sha256 if has_active else None,
                      'issued_at': now.date().isoformat(),
                      'forecast_history': _forecast_file_index(root / 'forecast-vintages')}
        run_id = sha256_bytes(canonical_json_bytes(frozen))
        if mode == 'replay' and snapshot != run_id: raise ValueError('source snapshot hash mismatch')
        run_root = root / 'runs' / run_id
        atomic(run_root / 'input.json', canonical_json_bytes(frozen))
        forecast_store = None
        if 'forecast_history' in frozen:
            _copy_forecast_inputs(root / 'forecast-vintages', run_root / 'forecasts', frozen['forecast_history'])
            forecast_store = ForecastVintageStore(run_root / 'forecasts')
        cases, entries, private_hashes, retry_hashes = [], [], {}, {}
        for entry in registry['entries']:
            ticker = entry['ticker']
            previous_raw = baseline.verify_artifact(ticker).read_bytes()
            public = sanitize_public_artifact(json.loads(previous_raw))
            last_numeric_template = deepcopy(retry_states[ticker]['public_template'] if ticker in retry_states else public)
            previous_range = deepcopy(public['scenario_range'])
            packet = materialize_packet(root, frozen['evidence']['packets'].get(ticker), entry)
            packet = attach_source_peers(root,packet,policies.get(ticker,{}),frozen['evidence']['packets'],registry,frozen['cutoff'])
            outcome, reason = 'unchanged', None
            recipe = recipes.get(ticker)
            current_recipe = recipe
            ledger = None
            if not packet or packet.get('acquisition_failed'):
                outcome, reason = 'acquisition_failed', 'Source refresh failed; previous dated estimate retained.'
            elif recipe is not None:
                try:
                    updated_recipe, ledger = bind_current_recipe({**entry, 'refresh_policy': policies[ticker]}, recipe, packet, frozen['cutoff'])
                    updated_recipe['recipe_version'] = refreshed_recipe_version(updated_recipe, policies[ticker])
                    ledger['assumption_date'] = frozen.get('issued_at', frozen['cutoff'])
                    valued = evaluate_recipe(updated_recipe)
                    if public['availability_type'] == 'not_available' or updated_recipe['scenarios'] != recipe['scenarios'] or updated_recipe['source_accession'] != recipe.get('source_accession') or updated_recipe['recipe_version'] != recipe.get('recipe_version'):
                        public = refreshed_public(last_numeric_template, updated_recipe, valued, ledger, frozen['cutoff'])
                        updated_recipe['baseline_version'] = baseline_version(public)
                        outcome = 'updated'
                    updated_recipe['replay'] = deepcopy(valued['range'])
                    # Version/baseline/replay metadata is part of the recipe
                    # hash. Store a result calculated from the finalized recipe.
                    valued = evaluate_recipe(updated_recipe)
                    if isinstance(ledger.get('result'),dict):
                        ledger['result'].update(range=deepcopy(valued['range']),recipe_hash=valued['recipe_hash'],
                            effective_recipe_hash=valued['effective_recipe_hash'])
                    current_recipe = updated_recipe
                    atomic(run_root / 'private' / f'{ticker}.json', canonical_json_bytes({'recipe': updated_recipe, 'source_ledger': ledger, 'result': valued}))
                except AcquisitionIncomplete:
                    outcome, reason = 'acquisition_failed', 'New filing evidence is incomplete; previous dated estimate retained.'
                except EconomicException as exc:
                    outcome, reason = 'unavailable', str(exc)
                    # A received filing may fail economic validation. Attribute
                    # it only after checking its identity against submissions;
                    # otherwise label the old reference explicitly historical.
                    source_reference = packet if isinstance(packet.get('controlling_filing'), dict) else None
                    public = _unavailable(public, reason, cutoff=frozen['cutoff'], source_packet=source_reference)
            forecast = None
            if forecast_store is not None and ledger is not None and outcome in {'updated', 'unchanged'}:
                forecast = track_company_refresh(
                    store=forecast_store, recipe=current_recipe, ledger=ledger,
                    issued_at=frozen['issued_at'], source_cutoff=frozen['cutoff'],
                    company_id=ticker, company_cik=entry['cik'], company_family=entry['primary_model'],
                    policy_version=policies[ticker]['version'], vintage_id=f'{ticker}-{run_id}',
                )
                atomic(run_root / 'private' / f'{ticker}-forecast.json', canonical_json_bytes(forecast))
            status = {'outcome': outcome, 'checked_as_of': frozen['cutoff'], 'reason': reason}
            payload = previous_raw if outcome in {'unchanged','acquisition_failed'} else canonical_json_bytes(public)
            atomic(run_root / 'candidate' / 'artifacts' / f'{ticker}.json', payload)
            entries.append({**next(e for e in baseline.manifest['entries'] if e['ticker'] == ticker), 'artifact_sha256': sha256_bytes(payload), 'availability_type': public['availability_type']})
            if public['availability_type'] != 'not_available':
                if current_recipe is None: raise ValueError(f'{ticker}: numeric successor has no executable recipe')
                recipe_bytes = canonical_json_bytes(current_recipe)
                atomic(run_root / 'candidate' / 'recipes' / f'{ticker}.json', recipe_bytes)
                private_hashes[ticker] = sha256_bytes(recipe_bytes)
            elif current_recipe is not None:
                if last_numeric_template['availability_type'] == 'not_available':
                    raise RuntimeError(f'{ticker}: unavailable retry has no last numeric template')
                retry_payload = canonical_json_bytes({'schema_version':'FINSIGHT-RETRY-STATE-1',
                    'recipe':current_recipe,'public_template':last_numeric_template})
                atomic(run_root/'candidate'/'retry-state'/f'{ticker}.json',retry_payload)
                retry_hashes[ticker] = sha256_bytes(retry_payload)
            cases.append({'ticker': ticker, **status, 'previous_range': previous_range, 'current_range': public['scenario_range'],
                          'confidence': public.get('reliability'), 'filing': public['source_financial_statement']})
        from collections import Counter
        availability = Counter(row['availability_type'] for row in entries)
        manifest = {**baseline.manifest, 'catalog_version': 'REFRESH-' + run_id[:24], 'base_catalog_version': baseline.catalog_version,
                    'entries': entries, 'artifact_count': len(entries), 'artifact_tree_sha256': artifact_tree_sha256(entries),
                    'availability_counts': {key: availability[key] for key in ('available','conditional_estimate','not_available','relative_baseline') if key in baseline.manifest['availability_counts']}}
        manifest['refresh_status'] = {case['ticker']: {key: case[key] for key in ('outcome','checked_as_of','reason')} for case in cases}
        manifest['private_recipe_sha256'] = private_hashes
        manifest['retry_state_sha256'] = retry_hashes
        atomic(run_root / 'candidate' / 'manifest.json', canonical_json_bytes(manifest))
        candidate = store.stage_catalog(run_root / 'candidate')
        report = {'run_id': run_id, 'cutoff': frozen['cutoff'], 'counts': dict(Counter(row['outcome'] for row in cases)), 'cases': cases,
                  'candidate_version': candidate.catalog_version, 'candidate_sha256': candidate.manifest_sha256}
        atomic(run_root / 'report.json', canonical_json_bytes(report))
        summary = '\n'.join([f"Run {run_id}", json.dumps(report['counts'], sort_keys=True)] + [f"{row['ticker']}: {row['outcome']} {row['reason'] or ''}" for row in cases]) + '\n'
        atomic(run_root / 'report.txt', summary.encode())
        # Only validated staged results enter prospective tracking. Frozen replay
        # uses its original history copy and never observes later global actuals.
        if forecast_store is not None and mode != 'replay':
            _copy_forecast_inputs(run_root / 'forecasts', root / 'forecast-vintages', _forecast_file_index(run_root / 'forecasts'))
        if mode == 'publish':
            store.activate(candidate, policy_fingerprint=sha256_bytes(canonical_json_bytes(policies)), activated_at=datetime.now(timezone.utc).isoformat(),
                           expected_active_manifest_sha256=frozen['expected_active_manifest_sha256'])
        return report
