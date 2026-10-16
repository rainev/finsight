"""Exact inactive Quality02 publication preparation; no release authority."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

SCHEMA = 'US-QUALITY02-STAGED-INHERITANCE-1'
REVIEW_SCHEMA = 'US-QUALITY02-STAGED-READ-ONLY-1'
MODEL_VERSION = 'US-QUALITY02-PUBLIC-LOW-1'
ANCHOR_SHA = 'e0bf2ea4c6194c480dad7f77038c37332e0f38dc392fda70792ccbd48cba945e'
TARGETS = frozenset('ATI DCI EXP HWKN IBP IOSP LNN MTRN NPK PLPC PLXS POWL ROG STRL TKR TNC TREX UFPT USLM'.split())
HELD = CARRY_HELD = frozenset('AEO AIT AMPH BWXT CACI CMC CVLT EBF ELF ETD EXPO FIZZ GRC IPAR KBR LNTH LZB MMSI MYRG NGVC PATK PCTY PEGA PNTG RHI SAIC SPSC TXRH URBN WCC WDFC'.split())
AUTHORITY_FIELDS = {'schema_version','read_only','manifest_sha256','catalog_version','registry_sha256','admission','activation','publication','save','automatic_new_source_revaluation'}
ROOT_FILES = {'manifest.json','artifacts','recipes','refresh-policies.json','prior-catalog','approved-parent-manifest.json','approved-parent-registry.json','approved-parent-policies.json','quality-scope-authorization.json','quality-source-binding.json','quality-private-confirmation.json','quality-eligibility-proposal.json','quality-eligibility-verification.json'}
DENIED = ('admission','activation','publication','policy_economics_change','new_SEC_capture_or_job','existing_runtime_service_operation','data_deletion','cloud_deployment','second_recovery_pass','next_batch')
APPROVAL_FIELDS = set(DENIED) | {'schema_version','source','user_request','recorded_at_UTC','financial_evidence_cutoff','targets','public_preparation_scope_approved','staged_candidate_only','proposal_sha256','eligibility_verification_sha256','private_confirmation_sha256','confirmed_private_values_and_Low_warnings_preserved','held_updates_keep_prior_estimate_and_recipe','revised_valuation_date_alignment_approved','existing_refresh_support_and_hold_epochs_preserved'}

def require(value, why):
    if not value: raise ValueError('Quality02 stage rejected: ' + why)

def canonical(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(value): return sha(canonical(value))

def anchors():
    path = Path(__file__).with_name('config') / 'quality02_staged_anchors_v2.json'
    require(path.is_file() and not path.is_symlink(), 'compiled anchor file')
    raw = path.read_bytes()
    require(sha(raw) == ANCHOR_SHA, 'compiled anchor changed')
    value = json.loads(raw)
    require(value['schema_version'] == SCHEMA and set(value['targets']) == TARGETS and set(value['held_updates']) == HELD, 'compiled scope')
    require(set(value['expected_issuer_mapping']) == TARGETS and set(value['root_files']) == ROOT_FILES, 'compiled mapping/root contract')
    return deepcopy(value)

def proof(root, name, expected, proof_reader):
    require(callable(proof_reader), 'authenticated proof reader required')
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader(root, name, expected)
    value = deepcopy(proof_reader(root,name,expected))
    require(digest(value) == expected, 'parsed proof changed: ' + name)
    return value

def _context_uncached(root, manifest, proof_reader):
    a = anchors()
    bound = proof(root,'manifest.json',a['manifest_sha256'],proof_reader)
    require(manifest == bound, 'compiled current manifest')
    require(manifest['staged_release_only'] is True and manifest['staged_read_only_review_ready'] is True, 'inactive read-only stage')
    require(all(manifest[k] is False for k in ('admission','activation','publication')), 'release flags')
    require('local_admission' not in manifest and 'private_review' not in manifest and not manifest.get('private_integration_only'), 'foreign permission lineage')
    require(manifest['catalog_kind'] == 'unadmitted_quality02_public_candidate' and manifest['catalog_version'].startswith('US-STAGED-QUALITY02-650-'), 'catalog namespace')
    parent = proof(root,'approved-parent-manifest.json',a['parent_manifest_sha256'],proof_reader)
    grant = proof(root,'quality-scope-authorization.json',a['approval_sha256'],proof_reader)
    binding = proof(root,'quality-source-binding.json',a['binding_sha256'],proof_reader)
    confirmation = proof(root,'quality-private-confirmation.json',a['confirmation_sha256'],proof_reader)
    proposal = proof(root,'quality-eligibility-proposal.json',a['proposal_sha256'],proof_reader)
    eligibility = proof(root,'quality-eligibility-verification.json',a['eligibility_sha256'],proof_reader)
    require(set(grant) == APPROVAL_FIELDS and grant['schema_version'] == 'US-QUALITY02-PUBLIC-PREPARATION-AUTHORIZATION-1', 'exact preparation authority')
    require(grant['source'] == 'direct_human_user' and isinstance(grant['user_request'],str) and grant['user_request'].strip(), 'human approval')
    require(grant['public_preparation_scope_approved'] is True and grant['staged_candidate_only'] is True and all(grant[k] is False for k in DENIED), 'preparation not release')
    require(set(grant['targets']) == TARGETS and len(grant['targets']) == 19 and set(grant['held_updates_keep_prior_estimate_and_recipe']) == HELD, 'exact approved19/31')
    require(grant['proposal_sha256'] == a['proposal_sha256'] and grant['eligibility_verification_sha256'] == a['eligibility_sha256'] and grant['private_confirmation_sha256'] == a['confirmation_sha256'], 'approval ancestry')
    require(set(proposal['proposed_public_preparation_tickers']) == TARGETS and proposal['public_preparation_permission_issued'] is False, 'original unbound proposal retained')
    require(set(eligibility['proposed_preparation_targets']) == TARGETS and eligibility['public_policy_binding'] is False and eligibility['public_candidate_created'] is False, 'original eligibility scope')
    require(confirmation['status'] == 'confirmed_private_only' and confirmation['private_numerical_proposals_confirmed'] == 19 and confirmation['private_held_updates_preserved'] == 31, 'private confirmation')
    require(set(confirmation['confirmed_private_ranges']) == TARGETS and set(confirmation['preserved_private_holds']) == HELD, 'confirmed scope')
    require(binding['schema_version'] == 'US-QUALITY02-PUBLIC-SOURCE-POLICY-BINDING-1' and binding['cutoff'] == '2026-10-08' and binding['model_policy_version'] == MODEL_VERSION, 'source/model binding version')
    require(binding['approval_sha256'] == a['approval_sha256'] and binding['private_confirmation_sha256'] == a['confirmation_sha256'] and binding['proposal_sha256'] == a['proposal_sha256'] and binding['eligibility_sha256'] == a['eligibility_sha256'], 'binding ancestry')
    require(set(binding['targets']) == TARGETS and all(binding[k] is False for k in ('admission','activation','publication','new_capture_or_refresh','economic_values_changed')), 'binding scope')
    current = {e['ticker']:e for e in manifest['entries']}
    old = {e['ticker']:e for e in parent['entries']}
    require(len(manifest['entries']) == len(current) == len(parent['entries']) == len(old) == 650 and set(current) == set(old), 'exact650 identities')
    require(manifest['availability_counts'] == parent['availability_counts'] and set(manifest['private_recipe_sha256']) == set(parent['private_recipe_sha256']), 'availability/recipe membership')
    require(manifest['base_manifest_sha256'] == manifest['approved_base_manifest_sha256'] == a['parent_manifest_sha256'] and manifest['base_catalog_version'] == parent['catalog_version'], 'approved parent identity')
    records = binding['records']
    require(set(records) == TARGETS | HELD and len(records) == 50 and {t for t,r in records.items() if r['updated_value_prepared']} == TARGETS, 'exact source records')
    originals = {r['ticker']:r for r in proposal['rows']}
    for t in set(old) - TARGETS:
        require(current[t] == old[t] and manifest['private_recipe_sha256'].get(t) == parent['private_recipe_sha256'].get(t), t+' unchanged artifact/recipe entry')
    for t in TARGETS:
        require((current[t]['cik'],current[t]['batch'],current[t]['availability_type']) == (old[t]['cik'],old[t]['batch'],'conditional_estimate'), t+' target identity/status')
        require(records[t]['confirmed_private_range'] == confirmation['confirmed_private_ranges'][t] == originals[t]['confirmed_private_range'], t+' exact confirmed range')
        source = deepcopy(records[t]['source_to_recipe'])
        for key in ('same_issuer_filing_period_unit_and_source_hashes','same_confirmed_range_required','actual_source_payload_verified'):
            require(source.pop(key) is True, t+' source verification witness')
        require(source == originals[t]['source_to_recipe'], t+' exact reviewed source proof')
    for t in HELD:
        require(records[t]['private_held_update'] is True and records[t]['reason'] == confirmation['preserved_private_holds'][t], t+' held update scope')
        require(records[t]['current_public_value_carry_forward'] == originals[t]['prior_active_range_retained'] and all(records[t]['current_public_value_carry_forward'][k] is not None for k in ('low','base','high')), t+' previous numerical value')
    return a,parent,binding,current


def context(root, manifest, proof_reader):
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader.context_for(root, manifest, lambda: _context_uncached(root, manifest, proof_reader))
    return _context_uncached(root, manifest, proof_reader)

def target(root, manifest, ticker, record, entry, proof_reader):
    from .artifacts import sanitize_public_artifact
    from .automated_review import assess_artifact
    from .calculation_recipe import evaluate_recipe
    try: from .latest_calculator import baseline_version
    except ImportError: from .calculator import baseline_version
    a = anchors()
    artifact = proof(root,'artifacts/'+ticker+'.json',entry['artifact_sha256'],proof_reader)
    recipe = proof(root,'recipes/'+ticker+'.json',manifest['private_recipe_sha256'][ticker],proof_reader)
    require(artifact['issuer'] == a['expected_issuer_mapping'][ticker] and artifact['issuer']['ticker'] == ticker and artifact['issuer']['cik'] == record['cik'], ticker+' mapping/identity')
    require(artifact['source_financial_statement'] == record['exact_source_header'] == record['source_to_recipe']['canonical_source_header'], ticker+' exact source header')
    require(all(artifact['source_financial_statement'][k] <= '2026-10-08' for k in ('filed_date','period_end')), ticker+' source dates')
    require(artifact['valuation_date'] == recipe['valuation_date'] == recipe['evidence_cutoff'] == '2026-10-08', ticker+' revised valuation date')
    require(artifact['model_version'] == MODEL_VERSION and artifact['model_policy']['primary'] == record['expected_model'], ticker+' reviewed model')
    require(manifest['quality_source_binding_sha256'] == artifact['public_assumptions']['source_policy_binding_sha256'] == a['binding_sha256'], ticker+' public binding')
    require(artifact['issuer']['classification_confidence'] == 0.0 and 'Unrated' in artifact['issuer']['classification_reason'], ticker+' unrated sentinel')
    require(artifact['reliability']['label'] == 'Low' and artifact['availability_type'] == 'conditional_estimate' and artifact['review']['publication_state'] == 'review_required' and not artifact['review']['errors'], ticker+' conditional/Low state')
    require(assess_artifact(artifact)['blocking_reasons'] == [] and sanitize_public_artifact(artifact) == artifact, ticker+' ordinary public gate')
    expected = record['confirmed_private_range']
    require({k:artifact['scenario_range'][k] for k in ('low','base','high')} == expected, ticker+' exact stored values')
    model = record['expected_model']
    require(set(artifact['models']) == {model} and artifact['models'][model]['intrinsic_value_per_share'] == expected['base'], ticker+' model output')
    require(set(artifact['scenarios']) == {'bear','base','bull'}, ticker+' scenario membership')
    for case,key in [('bear','low'),('base','base'),('bull','high')]:
        require(set(artifact['scenarios'][case]) == {model} and artifact['scenarios'][case][model]['intrinsic_value_per_share'] == expected[key], ticker+' scenario value')
    require(recipe['ticker'] == ticker and recipe['cik'] == record['cik'] and recipe['private_only'] is True and recipe['baseline_version'] == baseline_version(artifact), ticker+' private recipe/source baseline')
    require(digest({k:recipe[k] for k in ('scenarios','editable','warnings')}) == record['bound_recipe_economic_sha256'], ticker+' frozen economics')
    require(evaluate_recipe(recipe)['range'] == expected, ticker+' exact revised replay')
    require(set(record['required_public_disclosures']) <= set(artifact['review']['warnings']) and set(recipe['warnings']) <= set(artifact['review']['warnings']), ticker+' source/Low disclosures')
    return artifact

def validate(root, manifest, *, deep=False, proof_reader=None):
    a,parent,binding,current = context(root,manifest,proof_reader)
    policies = proof(root,'refresh-policies.json',a['policies_sha256'],proof_reader)
    oldpolicies = proof(root,'approved-parent-policies.json',a['parent_policies_sha256'],proof_reader)
    require(set(policies) == set(oldpolicies), 'policy membership')
    for t in policies:
        expected = deepcopy(oldpolicies[t])
        if t in TARGETS:
            expected['pins'].update(public_baseline=current[t]['artifact_sha256'],release_scope_approval=a['approval_sha256'],quality_source_policy_binding=a['binding_sha256'])
        require(policies[t] == expected, t+' policy changed outside exact baseline pins')
    if deep:
        require({p.name for p in Path(root).iterdir()} == ROOT_FILES, 'catalog root contract')
        require({p.name for p in (Path(root)/'artifacts').iterdir()} == {t+'.json' for t in current}, 'artifact files')
        require({p.name for p in (Path(root)/'recipes').iterdir()} == {t+'.json' for t in manifest['private_recipe_sha256']}, 'recipe files')
        from .approved_inheritance import validate_inheritance
        validate_inheritance(Path(root)/'prior-catalog',parent,deep=True)
        for t,e in current.items(): proof(root,'artifacts/'+t+'.json',e['artifact_sha256'],proof_reader)
        for t,d in manifest['private_recipe_sha256'].items(): proof(root,'recipes/'+t+'.json',d,proof_reader)
        for t in TARGETS: target(root,manifest,t,binding['records'][t],current[t],proof_reader)
    return {t:(e['cik'],e['batch'],e['availability_type'],e['artifact_sha256']) for t,e in current.items() if t not in TARGETS}

def preserved_parent_artifact(root, manifest, ticker, raw, *, proof_reader):
    _,parent,binding,current = context(root,manifest,proof_reader)
    require(ticker in current and sha(raw) == current[ticker]['artifact_sha256'], 'leaf bytes changed')
    if ticker in TARGETS:
        target(root,manifest,ticker,binding['records'][ticker],current[ticker],proof_reader)
        return False
    return True

def validate_registry(root, manifest, registry, *, proof_reader):
    a,parent,binding,current = context(root,manifest,proof_reader)
    require(digest(registry) == a['registry_sha256'], 'staged registry')
    old = proof(root,'approved-parent-registry.json',a['parent_registry_sha256'],proof_reader)
    rows = {r['ticker']:r for r in registry['entries']}
    oldrows = {r['ticker']:r for r in old['entries']}
    require(len(registry['entries']) == len(rows) == 650 and set(rows) == set(current), 'registry650')
    require(registry['baseline_manifest_sha256'] == a['manifest_sha256'] and registry['baseline_catalog_version'] == manifest['catalog_version'], 'registry baseline')
    for t in rows:
        expected = deepcopy(oldrows[t])
        if t in TARGETS:
            expected.update(baseline_sha256=current[t]['artifact_sha256'],primary_model=binding['records'][t]['expected_model'],forecast_mode='owner_cash_schedule_exact' if t == 'IBP' else 'residual_income_exact',controlling_filing=binding['records'][t]['exact_source_header'],source_audit='docs/audit/us-quality02-public-staged.md',recipe_status='quality02_recipe_new_filing_held')
        require(rows[t] == expected, t+' exact registry row')
    return registry

def review_selection(root, authority_file, authority, manifest, manifest_sha, *, proof_reader):
    a = anchors()
    require(set(authority) == AUTHORITY_FIELDS and authority['schema_version'] == REVIEW_SCHEMA and authority['read_only'] is True, 'review authority fields')
    require(all(authority[k] is False for k in ('admission','activation','publication','save','automatic_new_source_revaluation')), 'review permission')
    require(authority['manifest_sha256'] == manifest_sha == a['manifest_sha256'] and authority['catalog_version'] == manifest['catalog_version'] and authority['registry_sha256'] == a['registry_sha256'], 'review ancestry')
    validate(root,manifest,deep=True,proof_reader=proof_reader)
    registry = proof(authority_file.parent,'runtime/registry.json',a['registry_sha256'],proof_reader)
    validate_registry(root,manifest,registry,proof_reader=proof_reader)
    proof(authority_file.parent,'runtime/refresh-policies.json',a['policies_sha256'],proof_reader)
    return root,manifest_sha
