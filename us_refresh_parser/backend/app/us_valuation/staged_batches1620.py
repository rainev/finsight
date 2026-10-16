"""Closed staged700 template; installed only into isolated prepared copies.

The leaf predicate restricts an ordinary sanitizer.  It never approves or
calculates a value, and a failed predicate returns a public-null shell.
"""
from collections import Counter
from copy import deepcopy
from datetime import date, datetime
from functools import lru_cache
import json
import os
from pathlib import Path

from .catalog import canonical_json_bytes, sha256_bytes

ANCHORS_SHA = 'fbb633e69f4e8ee3f4aa496cd6d2a6a79d8fabbcfe26adfb0d196764ea90a0e6'
PROFILE = 'B16-B20-STAGED-PUBLIC-1'
REVIEW_SCHEMA = 'US-B1620-STAGED700-READ-ONLY-1'
MODEL_VERSION = 'US-B1620-PUBLIC-SOURCE-BOUNDED-CASH-1'
TARGETS = frozenset({'MMS', 'FCN'})
_ERROR = 'Changed or unbound B16-B20 staged leaf is not publishable.'


def need(value, reason):
    if not value:
        raise ValueError('staged700: ' + reason)


@lru_cache(maxsize=1)
def anchors():
    path = Path(__file__).with_name('config') / 'staged_batches1620_anchors.json'
    need(path.is_file() and not path.is_symlink(), 'compiled anchors missing')
    raw = path.read_bytes()
    need(sha256_bytes(raw) == ANCHORS_SHA, 'compiled anchors changed')
    return json.loads(raw)


def file(root, relative):
    from .approved_inheritance import _file
    return _file(Path(root), relative)


def validate_manifest(manifest):
    a = anchors()
    need(isinstance(manifest, dict), 'manifest object required')
    required = {
        'schema_version', 'catalog_version', 'universe_version', 'valuation_date',
        'created_at', 'included_batches', 'entries', 'artifact_count',
        'artifact_tree_sha256', 'availability_counts', 'private_recipe_sha256',
        'private_refresh_policy_sha256', 'catalog_kind', 'staged_release_only',
        'staged_read_only_review_ready', 'staged_review', 'base_catalog_version',
        'base_manifest_sha256', 'preserved_prior_estimate_sha256',
        'source_snapshot', 'refresh_status', 'refresh_cutoff',
        'admission', 'activation', 'publication',
    }
    child = {'publication_counts', 'input_fingerprints',
             'refresh_parent_catalog_version', 'refresh_parent_manifest_sha256'}
    need(required <= set(manifest) <= required | child,
         'unknown authority or manifest field')
    need(manifest['schema_version'] == 'FINSIGHT-US-VALUATION-CATALOG-1.0',
         'catalog schema changed')
    need(manifest['catalog_kind'] == 'staged_public_candidate'
         and manifest['staged_release_only'] is True
         and manifest['staged_read_only_review_ready'] is True,
         'unadmitted staged-only wrapper required')
    need(all(manifest[k] is False for k in ('admission', 'activation', 'publication')),
         'release authority forbidden')
    need(manifest['staged_review'] == a['review']
         and manifest['staged_review']['profile'] == PROFILE,
         'closed staged review changed')
    need(set(a['review']['approved_targets']) == TARGETS
         and set(a['new_numeric']) <= TARGETS
         and len(a['new_identities']) == 50,
         'approved2/50 scope changed')
    need(set(a['review']['public_nulls']) == set(a['new_identities']) - set(a['new_numeric']),
         'public-null scope changed')
    need(manifest['base_catalog_version'] == a['parent_version']
         and manifest['base_manifest_sha256'] == a['parent_manifest_sha256'],
         'authentic public650 parent changed')
    need(manifest['included_batches'] == list(range(1, 71))
         and manifest['artifact_count'] == 700,
         '700/batches1-70 required')
    need(manifest['entries'] == a['entries']
         and len({r['ticker'] for r in manifest['entries']}) == 700,
         'identity/artifact/status scope changed')
    need(manifest['availability_counts'] == a['availability_counts']
         and manifest['availability_counts'] == dict(Counter(r['availability_type'] for r in a['entries'])),
         'availability denominator changed')
    need(manifest['private_recipe_sha256'] == a['recipe_sha256']
         and manifest['private_refresh_policy_sha256'] == a['policies_sha256'],
         'recipe/policy pins changed')
    need(manifest['preserved_prior_estimate_sha256'] == a['preserved_file_sha256'],
         'preserved provenance scope changed')
    if manifest['catalog_version'] == a['catalog_version']:
        need(sha256_bytes(canonical_json_bytes(manifest)) == a['baseline_manifest_sha256'],
             'baseline manifest metadata changed')
    else:
        need(str(manifest['catalog_version']).startswith('US-REFRESH-700-')
             and manifest.get('refresh_parent_catalog_version') == a['catalog_version']
             and manifest.get('refresh_parent_manifest_sha256') == a['baseline_manifest_sha256'],
             'worker child lost staged700 predecessor')
    return a['review']


def is_exact_public_override(artifact):
    """A deny-only exact-leaf predicate; ordinary economic gates still run."""
    try:
        a = anchors()
        t = artifact['issuer']['ticker']
        if t not in a['new_identities']:
            return False
        if (artifact.get('ticker') != t
                or artifact['issuer']['cik'] != a['new_identities'][t]
                or artifact.get('model_version') != MODEL_VERSION
                or artifact['issuer'].get('classification_confidence') != 0.0):
            return False
        return sha256_bytes(canonical_json_bytes(artifact)) == a['artifact_sha256'][t]
    except (OSError, ValueError, KeyError, TypeError):
        return False


def rejected_leaf(artifact):
    """Drop every untrusted value/raw sink, including ROOT's legacy extras."""
    issuer = artifact.get('issuer', {}) if isinstance(artifact, dict) else {}
    t = issuer.get('ticker') if isinstance(issuer, dict) else None
    t = t if isinstance(t, str) and len(t) <= 32 else None
    model = {'model': 'conditional_estimate', 'publication_state': 'withheld',
             'intrinsic_value_per_share': None, 'conditional_value_per_share': None,
             'errors': [], 'warnings': [_ERROR]}
    return {
        'schema_version': 'US-PUBLIC-VALUATION-1.2', 'ticker': t,
        'market': 'US', 'currency': 'USD',
        'issuer': {'ticker': t, 'primary_archetype': 'b1620_public_hold',
                   'classification_confidence': 0.0},
        'source_financial_statement': {}, 'model_version': MODEL_VERSION,
        'model_policy': {'primary': 'conditional_estimate', 'supporting': [], 'reason': _ERROR},
        'public_assumptions': {'forecast_policy_version': MODEL_VERSION, 'forecast_mode': 'unavailable'},
        'availability_type': 'not_available',
        'models': {'conditional_estimate': deepcopy(model)},
        'scenarios': {name: {'conditional_estimate': deepcopy(model)} for name in ('bear', 'base', 'bull')},
        'scenario_range': {'low': None, 'base': None, 'high': None,
                           'label': 'assumption range, not a statistical confidence interval'},
        'review': {'publication_state': 'withheld', 'errors': [_ERROR], 'warnings': [_ERROR]},
        'reliability': {'label': None, 'reasons': ['VALUATION_WITHHELD']},
        'market_comparison': {'status': 'unavailable', 'reason': 'unbound_staged_leaf'},
        'data_boundary': {'raw_financial_statement_values_included': False, 'stock_prices_used': False},
        'sensitivities': [],
    }


def enforce_leaf(artifact):
    return artifact if is_exact_public_override(artifact) else rejected_leaf(artifact)


def project(artifact, manifest, *, ticker, artifact_sha256):
    a = anchors()
    validate_manifest(manifest)
    expected = a['artifact_sha256'].get(ticker)
    need(expected and artifact_sha256 == expected
         and sha256_bytes(canonical_json_bytes(artifact)) == expected,
         'closed artifact/source/warning changed: ' + ticker)
    if ticker not in a['new_identities']:
        need(expected == a['parent_projections'][ticker]['projection_sha256'],
             'native parent650 projection changed')
        return deepcopy(artifact)
    from .private_integration import _walk_forbidden_keys
    from .artifacts import sanitize_public_artifact
    from .automated_review import assess_artifact
    _walk_forbidden_keys(artifact)
    need(is_exact_public_override(artifact), 'staged identity/classification/leaf changed')
    ordinary = sanitize_public_artifact(artifact)
    need(ordinary == artifact and sanitize_public_artifact(ordinary) == ordinary,
         'ordinary public sanitizer changed pinned leaf')
    numeric = ticker in a['new_numeric']
    need(artifact['model_policy']['primary'] == a['new_models'][ticker], 'public model changed')
    need(artifact['valuation_date'] == a['review']['cutoff']
         and artifact['assumption_date'] == a['review']['cutoff'], 'frozen dates changed')
    need('private_review_only' not in artifact, 'private projector marker retained')
    if numeric:
        assessed = assess_artifact(artifact)
        need(assessed['publication_state'] == 'review_required'
             and not assessed['blocking_reasons'], 'ordinary automated review blocked target')
        need(ticker in TARGETS and artifact['availability_type'] == 'conditional_estimate'
             and artifact['reliability']['label'] == 'Low'
             and artifact['review']['publication_state'] == 'review_required',
             'Conditional/Low target changed')
        need(artifact['public_assumptions']['source_policy_binding_sha256'] == a['source_binding_sha256'],
             'source binding changed')
    else:
        need(artifact['availability_type'] == 'not_available'
             and artifact['review']['publication_state'] == 'withheld'
             and artifact['reliability']['label'] == 'Low'
             and all(artifact['scenario_range'][k] is None for k in ('low', 'base', 'high')),
             'public-null sink changed')
    return deepcopy(ordinary)


def consumer_disclosures(manifest, artifact, payload):
    a = anchors()
    validate_manifest(manifest)
    t = artifact['issuer']['ticker']
    result = deepcopy(payload)
    if t not in a['new_identities']:
        recorded = deepcopy(a['parent_projections'][t]['disclosures'])
        recorded.pop('ticker', None)
        old_warnings = recorded.pop('warnings', [])
        result.update(recorded)
        if old_warnings:
            result['warnings'] = list(dict.fromkeys([*result.get('warnings', []), *old_warnings]))
    else:
        result['warnings'] = list(dict.fromkeys([*result.get('warnings', []), *artifact['review']['warnings']]))
        result['staged_scope'] = {
            'staged_only': True, 'public_candidate_preparation_authorized': True,
            'public_release_authorized': False, 'evidence_cutoff': a['review']['cutoff'],
            'financial_reference_date': artifact['source_financial_statement']['period_end'],
            'new_filing_review_required': True, 'numerical_candidate': t in a['new_numeric'],
            'manual_classification': 'unrated_zero_guard_sentinel_not_measurement',
            'economic_calibration': 'unvalidated',
            'admission': False, 'activation': False, 'publication': False,
        }
    result['staged_integration_scope'] = {
        'staged_only': True, 'catalog_membership': 700, 'active_membership_unchanged': 650,
        'admission': False, 'activation': False, 'publication': False,
    }
    return result


def validate_catalog(root, manifest, *, runtime=None):
    a = anchors()
    validate_manifest(manifest)
    root = Path(root)
    expected_root = {'artifacts', 'recipes', 'manifest.json', 'refresh-policies.json'}
    expected_root |= {Path(rel).parts[0] for rel in a['preserved_file_sha256']}
    need({p.name for p in root.iterdir()} == expected_root
         and not any(p.is_symlink() for p in root.iterdir()), 'unexpected root proof/grant or symlink')
    for relative, digest in a['preserved_file_sha256'].items():
        need(sha256_bytes(file(root, relative)) == digest, 'preserved provenance changed: ' + relative)
    parent_raw = file(root, 'inherited-parent/manifest.json')
    need(sha256_bytes(parent_raw) == a['parent_manifest_sha256'], 'parent manifest changed')
    parent = json.loads(parent_raw)
    current = {r['ticker']: r for r in manifest['entries']}
    need(all(current[r['ticker']] == r for r in parent['entries']), 'old650 row changed')
    need({p.stem for p in (root / 'artifacts').glob('*.json')} == set(current), 'artifact membership changed')
    for row in manifest['entries']:
        raw = file(root, 'artifacts/' + row['ticker'] + '.json')
        need(sha256_bytes(raw) == row['artifact_sha256'], 'artifact bytes changed')
        if row['ticker'] in a['new_identities']:
            project(json.loads(raw), manifest, ticker=row['ticker'], artifact_sha256=row['artifact_sha256'])
    need({p.stem for p in (root / 'recipes').glob('*.json')} == set(a['recipe_sha256']), 'recipe membership changed')
    for t, digest in a['recipe_sha256'].items():
        raw = file(root, 'recipes/' + t + '.json')
        need(sha256_bytes(raw) == digest, 'recipe changed: ' + t)
    need(sha256_bytes(file(root, 'refresh-policies.json')) == a['policies_sha256'], 'catalog policies changed')
    auth = json.loads(file(root, 'staged-preparation-authorization.json'))
    need(auth['authorization_source'] == 'direct_human_user'
         and auth['staged_candidate_only'] is True
         and set(auth['approved_targets']) == TARGETS
         and all(auth[k] is False for k in ('admission', 'activation', 'publication',
                                           'new_source_capture', 'new_valuation_inputs',
                                           'automatic_new_source_revaluation')),
         'staged preparation authority widened')
    binding = json.loads(file(root, 'staged-source-disclosure-binding.json'))
    need(set(binding['records']) == TARGETS
         and binding['scope_approval_sha256'] == a['preparation_sha256']
         and binding['cutoff'] == a['review']['cutoff']
         and binding['acceptance_cutoff_UTC'] == a['review']['acceptance_cutoff_UTC']
         and all(binding[k] is False for k in ('admission', 'activation', 'publication',
                                              'new_source_adapter_ready', 'new_valuation_inputs',
                                              'private_values_changed')),
         'source-disclosure scope changed')
    for t in a['new_numeric']:
        record = binding['records'][t]
        need(record['source_gate']['ready'] is True
             and record['source_economic_inputs_changed'] is False
             and record['automatic_new_source_revaluation'] is False,
             'numeric source gate changed')
        recipe = json.loads(file(root, 'recipes/' + t + '.json'))
        need(recipe['scenarios'] == record['original_scenarios']
             and recipe['warnings'] == record['original_warnings']
             and recipe['editable'] == {}, 'frozen recipe economics changed')
    if runtime is not None:
        runtime = Path(runtime)
        registry = json.loads(file(runtime, 'registry.json'))
        policies = json.loads(file(runtime, 'refresh-policies.json'))
        need(registry['baseline_manifest_sha256'] == sha256_bytes(file(root, 'manifest.json'))
             and registry['baseline_catalog_version'] == manifest['catalog_version'], 'runtime baseline changed')
        rows = registry['entries']
        need(len(rows) == len({r['ticker'] for r in rows}) == 700
             and {(r['ticker'], r['cik'], r['batch']) for r in rows}
             == {(r['ticker'], r['cik'], r['batch']) for r in manifest['entries']}, 'registry identities changed')
        old_registry = json.loads(file(root, 'integration-parent-registry.json'))
        old_policies = json.loads(file(root, 'integration-parent-policies.json'))
        indexed = {r['ticker']: r for r in rows}
        need(all(indexed[r['ticker']] == r for r in old_registry['entries']), 'old650 registry changed')
        need(len(policies) == 631 and all(policies[t] == v for t, v in old_policies.items()), 'old581 policies changed')
        need(sha256_bytes(file(runtime, 'refresh-policies.json')) == a['policies_sha256'], 'runtime policies changed')
        for t in a['new_identities']:
            need(indexed[t] == a['new_registry_entries'][t]
                 and policies[t] == a['new_hold_policies'][t], 'new source/hold scope changed')
    return True


def validate_review_selection(root, authority_file, authority, manifest, manifest_sha):
    a = anchors()
    need(os.environ.get('APP_ENV') == 'test', 'staged700 test-only')
    fields = {'schema_version', 'source', 'read_only', 'staged_only', 'catalog_version',
              'manifest_sha256', 'registry_sha256', 'refresh_policies_sha256',
              'preparation_authority_sha256', 'admission', 'activation', 'publication',
              'save', 'automatic_new_source_revaluation', 'new_SEC_capture'}
    need(isinstance(authority, dict) and set(authority) == fields, 'review authority exact fields required')
    need(authority['schema_version'] == REVIEW_SCHEMA
         and authority['source'] == 'direct_human_preparation_scope'
         and authority['read_only'] is True and authority['staged_only'] is True,
         'read-only staged authority missing')
    need(all(authority[k] is False for k in ('admission', 'activation', 'publication', 'save',
                                           'automatic_new_source_revaluation', 'new_SEC_capture')),
         'review authority widened')
    authority_file = Path(authority_file)
    run = authority_file.parent
    need(run.parent.resolve() == Path(a['phase_path']).resolve()
         and run.name in {'run-a', 'run-b'} and authority_file.name == 'review-authority.json',
         'review outside authorized staged phase')
    need(Path(root).resolve() == (run / 'catalogs' / a['catalog_version']).resolve(), 'review root changed')
    need(authority['catalog_version'] == a['catalog_version']
         and authority['manifest_sha256'] == manifest_sha == a['baseline_manifest_sha256']
         and authority['preparation_authority_sha256'] == a['preparation_sha256'], 'review pins changed')
    validate_catalog(root, manifest, runtime=run / 'runtime')
    need(sha256_bytes(file(run, 'runtime/registry.json')) == authority['registry_sha256']
         and sha256_bytes(file(run, 'runtime/refresh-policies.json')) == authority['refresh_policies_sha256'],
         'review runtime pins changed')
    return root, manifest_sha


def metadata_hold(ticker, submissions, as_of):
    a = anchors()
    if ticker not in a['new_identities']:
        return None
    freeze = datetime.fromisoformat(a['review']['acceptance_cutoff_UTC'].replace('Z', '+00:00'))
    rows = submissions.get('filings', {}).get('recent', {})
    forms = rows.get('form', [])
    for field in ('filingDate', 'items', 'acceptanceDateTime'):
        need(not rows.get(field) or len(rows[field]) == len(forms), 'malformed material metadata columns')
    for i, form in enumerate(forms):
        filed = (rows.get('filingDate') or [''] * len(forms))[i]
        if filed > as_of:
            continue
        items = {v.strip() for v in str((rows.get('items') or [''] * len(forms))[i]).split(',')}
        if form not in {'8-K', '8-K/A'} or not items & {'1.01', '2.01', '2.03', '3.02', '4.02', '5.02'}:
            continue
        accepted = (rows.get('acceptanceDateTime') or [''] * len(forms))[i]
        if accepted:
            instant = datetime.fromisoformat(accepted.replace('Z', '+00:00'))
            need(instant.tzinfo is not None, 'material acceptance timezone missing')
            if instant.date() > date.fromisoformat(as_of):
                continue
            after = instant > freeze
        else:
            after = not filed or filed >= a['review']['cutoff']
        if after:
            return 'Staged700 material event after exact frozen acceptance cutoff: intentional review hold before capture.'
    return None
