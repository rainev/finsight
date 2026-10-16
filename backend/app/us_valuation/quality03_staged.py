"""Exact approved8 inactive650 source/model scope; never release authority."""
from copy import deepcopy
from pathlib import Path
from functools import lru_cache
import hashlib
import json

SCHEMA='US-QUALITY03-STAGED-INHERITANCE-1'
REVIEW_SCHEMA='US-QUALITY03-STAGED-READ-ONLY-1'
MODEL_VERSION='US-QUALITY03-PUBLIC-LOW-1'
ANCHOR_SHA='20e49393d8aa8ac79c6c8b017af3060e7594aae74651e470bb1069a7032ee6a1'
TARGETS=frozenset('URI HOOD IBKR MS ACU CNMD HXL IIIN'.split())
HELD=frozenset('CCI BA WAT CLX FIS INTC DD HST MRVL SMCI DOW UNH GLW KDP CSGP BLDR JCI LUV ADM CI BALL EL PYPL HPE AKAM ANF ASO BKE BSET CROX JBSS MATX NHC PRIM SON TILE'.split())
PRIVATE_ONLY=frozenset('CARR SMID NWPX PLOW UFPI'.split())
CARRY_HELD=CARRY_FORWARD=HELD|PRIVATE_ONLY|{'FAST'}
AUTHORITY_FIELDS={'schema_version','read_only','manifest_sha256','catalog_version','registry_sha256','admission','activation','publication','save','automatic_new_source_revaluation'}
ROOT_FILES={'manifest.json','artifacts','recipes','refresh-policies.json','prior-catalog','approved-parent-manifest.json','approved-parent-registry.json','approved-parent-policies.json','quality-scope-authorization.json','quality-source-binding.json','quality-private-confirmation.json','quality-eligibility-proposal.json','quality-eligibility-verification.json'}
DENIED=('admission','activation','publication','policy_economics_change','new_SEC_capture_or_job','existing_runtime_service_operation','Docker_operation','data_deletion','cloud_deployment','second_recovery_pass','next_batch')
APPROVAL_FIELDS=set(DENIED)|{'schema_version','source','user_request','recorded_at_UTC','issuer_specific_frozen_cutoffs_retained','targets','public_preparation_scope_approved','staged_candidate_only','proposal_sha256','eligibility_verification_sha256','private_confirmation_sha256','confirmed_private_values_and_Low_warnings_preserved','carry_forward_prior_active_artifact_and_recipe','private_only_diagnostic_tickers','private_held_update_tickers','FAST_unchanged_control_preserved','revision_specific_new_filing_holds_required','existing_refresh_support_and_hold_epochs_preserved'}


def require(value,reason):
    if not value: raise ValueError('Quality03 stage rejected: '+reason)
def canonical(value): return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(value): return sha(canonical(value))


def anchors():
    path=Path(__file__).with_name('config')/'quality03_staged_anchors_v1.json'
    require(path.is_file() and not path.is_symlink(),'compiled anchor file')
    raw=path.read_bytes(); require(sha(raw)==ANCHOR_SHA,'compiled anchor bytes')
    value=json.loads(raw)
    require(value['schema_version']==SCHEMA and set(value['targets'])==TARGETS,'compiled target scope')
    require(set(value['carry_forward'])==CARRY_FORWARD and set(value['held_updates'])==HELD and set(value['private_only_diagnostics'])==PRIVATE_ONLY,'compiled carry/diagnostic/held scope')
    require(set(value['expected_issuer_mapping'])==TARGETS and set(value['root_files'])==ROOT_FILES,'compiled mapping/root contract')
    return deepcopy(value)


def proof(root,name,expected,proof_reader):
    require(callable(proof_reader),'authenticated proof reader')
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader(root, name, expected)
    value=proof_reader(root,name,expected)
    value=deepcopy(value)
    require(digest(value)==expected,'parsed proof changed: '+name)
    return value


def _context_uncached(root,manifest,proof_reader):
    a=anchors(); bound=proof(root,'manifest.json',a['manifest_sha256'],proof_reader)
    require(manifest==bound,'compiled manifest')
    require(manifest['staged_release_only'] is True and manifest['staged_read_only_review_ready'] is True,'read-only stage')
    require(all(manifest[k] is False for k in ['admission','activation','publication']),'no release')
    require('local_admission' not in manifest and 'private_review' not in manifest and not manifest.get('private_integration_only'),'foreign permission lineage')
    require(manifest['catalog_kind']=='unadmitted_quality03_public_candidate' and manifest['catalog_version'].startswith('US-STAGED-QUALITY03-650-'),'namespace')
    parent=proof(root,'approved-parent-manifest.json',a['parent_manifest_sha256'],proof_reader)
    grant=proof(root,'quality-scope-authorization.json',a['approval_sha256'],proof_reader)
    binding=proof(root,'quality-source-binding.json',a['binding_sha256'],proof_reader)
    confirmation=proof(root,'quality-private-confirmation.json',a['confirmation_sha256'],proof_reader)
    proposal=proof(root,'quality-eligibility-proposal.json',a['proposal_sha256'],proof_reader)
    eligibility=proof(root,'quality-eligibility-verification.json',a['eligibility_sha256'],proof_reader)
    require(set(grant)==APPROVAL_FIELDS and grant['schema_version']=='US-QUALITY03-PUBLIC-PREPARATION-AUTHORIZATION-1','exact approval fields')
    require(grant['source']=='direct_human_user' and isinstance(grant['user_request'],str) and grant['user_request'].strip(),'direct human scope')
    require(grant['public_preparation_scope_approved'] is True and grant['staged_candidate_only'] is True and all(grant[k] is False for k in DENIED),'prep only')
    require(len(grant['targets'])==8 and set(grant['targets'])==TARGETS and set(grant['carry_forward_prior_active_artifact_and_recipe'])==CARRY_FORWARD,'exact8/42')
    require(set(grant['private_only_diagnostic_tickers'])==PRIVATE_ONLY and set(grant['private_held_update_tickers'])==HELD and grant['FAST_unchanged_control_preserved'] is True,'five/36/FAST')
    require(grant['revision_specific_new_filing_holds_required'] is True and grant['existing_refresh_support_and_hold_epochs_preserved'] is True,'filing/support guard')
    require(grant['proposal_sha256']==a['proposal_sha256'] and grant['eligibility_verification_sha256']==a['eligibility_sha256'] and grant['private_confirmation_sha256']==a['confirmation_sha256'],'approval ancestry')
    require(set(proposal['proposed_preparation_tickers'])==TARGETS and proposal['public_preparation_permission_issued'] is False,'original unbound proposal')
    require(set(eligibility['proposed_preparation_targets'])==TARGETS and eligibility['public_policy_binding'] is False and eligibility['public_candidate_created'] is False,'original eligibility')
    require(confirmation['status']=='confirmed_private_only' and confirmation['confirmed_private_Low_proposals']==13 and confirmation['held_update_count']==36,'confirmed private scope')
    require(set(confirmation['confirmed_private_Low_ranges'])==TARGETS|PRIVATE_ONLY and set(confirmation['preserved_private_held_updates'])==HELD,'13/36 private confirmation')
    require(confirmation['FAST_unchanged_control_preserved'] is True and confirmation['replacement_public_and_new_filing_holds_cleared']==0,'private holds untouched')
    require(binding['schema_version']=='US-QUALITY03-PUBLIC-SOURCE-POLICY-BINDING-1' and binding['model_policy_version']==MODEL_VERSION and binding['issuer_specific_frozen_cutoffs_retained'] is True,'source/model binding')
    for field,anchor in [('approval_sha256','approval_sha256'),('private_confirmation_sha256','confirmation_sha256'),('proposal_sha256','proposal_sha256'),('eligibility_sha256','eligibility_sha256')]: require(binding[field]==a[anchor],'binding ancestry '+field)
    require(set(binding['targets'])==TARGETS and set(binding['carry_forward'])==CARRY_FORWARD and set(binding['private_only_diagnostics'])==PRIVATE_ONLY and set(binding['private_held_updates'])==HELD,'binding scope')
    require(binding['all8_revision_specific_new_filing_holds'] is True and all(binding[k] is False for k in ['admission','activation','publication','new_capture_or_refresh','economic_values_changed']),'binding permission')
    current={e['ticker']:e for e in manifest['entries']};old={e['ticker']:e for e in parent['entries']}
    require(len(current)==len(manifest['entries'])==len(parent['entries'])==len(old)==650 and set(current)==set(old),'650 identity membership')
    require(set(manifest['private_recipe_sha256'])==set(parent['private_recipe_sha256']),'recipe membership')
    require(manifest['base_manifest_sha256']==manifest['approved_base_manifest_sha256']==a['parent_manifest_sha256'] and manifest['base_catalog_version']==parent['catalog_version'],'parent identity')
    records=binding['records']; originals={r['ticker']:r for r in proposal['rows']}
    require(set(records)==TARGETS|CARRY_FORWARD and len(records)==50 and {t for t,r in records.items() if r['updated_value_prepared']}==TARGETS,'50 reviewed records')
    for t in set(old)-TARGETS: require(current[t]==old[t] and manifest['private_recipe_sha256'].get(t)==parent['private_recipe_sha256'].get(t),t+' unchanged642 artifact/recipe')
    for t in TARGETS:
        require((current[t]['cik'],current[t]['batch'],current[t]['availability_type'])==(old[t]['cik'],old[t]['batch'],'conditional_estimate'),t+' target identity/status')
        require(records[t]['confirmed_private_range']==confirmation['confirmed_private_Low_ranges'][t]==originals[t]['confirmed_private_range'],t+' exact confirmed values')
        require(records[t]['source_to_recipe_review']==originals[t]['source_to_recipe_review'],t+' unchanged source proof')
        require(records[t]['proposed_public_valuation_date']==originals[t]['proposed_public_valuation_date'],t+' issuer cutoff')
    for t in CARRY_FORWARD:
        require(records[t]['current_public_value_carry_forward']==originals[t]['prior_active_range_retained'] and all(records[t]['current_public_value_carry_forward'][k] is not None for k in ['low','base','high']),t+' prior numeric carry')
        if t in HELD: require(records[t]['private_held_update'] is True and records[t]['reason']==confirmation['preserved_private_held_updates'][t],t+' held update')
        if t in PRIVATE_ONLY: require(records[t]['private_only_diagnostic_retained'] is True and records[t]['confirmed_private_range']==confirmation['confirmed_private_Low_ranges'][t],t+' private diagnostic')
        if t=='FAST': require(records[t]['unchanged_FAST_control'] is True and records[t]['confirmed_private_range']==confirmation['preserved_FAST_unchanged_range']==records[t]['current_public_value_carry_forward'],'FAST unchanged')
    return a,parent,binding,current


@lru_cache(maxsize=4)
def _context_bytes(files):
    # Cache immutable authenticated bytes, never mutable dictionaries. Returned
    # dictionaries are decoded afresh, and custom readers never use this path.
    records={name:(pin,raw) for name,pin,raw in files}
    def verified_memory(root,name,pin):
        wanted,raw=records[name]
        require(wanted==pin,'immutable context proof pin')
        return json.loads(raw)
    result=_context_uncached(Path('.'),json.loads(records['manifest.json'][1]),verified_memory)
    return canonical(result)


def context(root,manifest,proof_reader):
    from .approved_inheritance import _proof as native_reader,_file
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader.context_for(root, manifest, lambda: _context_uncached(root, manifest, proof_reader))
    if proof_reader is not native_reader:
        return _context_uncached(root,manifest,proof_reader)
    a=anchors()
    pins={'manifest.json':a['manifest_sha256'],'approved-parent-manifest.json':a['parent_manifest_sha256'],
        'quality-scope-authorization.json':a['approval_sha256'],'quality-source-binding.json':a['binding_sha256'],
        'quality-private-confirmation.json':a['confirmation_sha256'],'quality-eligibility-proposal.json':a['proposal_sha256'],
        'quality-eligibility-verification.json':a['eligibility_sha256']}
    files=[]
    for name,pin in sorted(pins.items()):
        raw=_file(root,name)
        require(sha(raw)==pin,'current context proof bytes: '+name)
        files.append((name,pin,raw))
    result=json.loads(_context_bytes(tuple(files)))
    raw_manifest=next(raw for name,pin,raw in files if name=='manifest.json')
    require(manifest==json.loads(raw_manifest),'current manifest object changed')
    return tuple(result)


def target(root,manifest,ticker,record,entry,proof_reader):
    from .artifacts import sanitize_public_artifact
    from .automated_review import assess_artifact
    from .calculation_recipe import evaluate_recipe
    try: from .latest_calculator import baseline_version
    except ImportError: from .calculator import baseline_version
    a=anchors(); artifact=proof(root,'artifacts/'+ticker+'.json',entry['artifact_sha256'],proof_reader)
    recipe=proof(root,'recipes/'+ticker+'.json',manifest['private_recipe_sha256'][ticker],proof_reader)
    require(artifact['issuer']==a['expected_issuer_mapping'][ticker] and artifact['issuer']['ticker']==ticker and artifact['issuer']['cik']==record['cik'],ticker+' mapping')
    require(artifact['source_financial_statement']==record['exact_source_header']==record['source_to_recipe_review']['canonical_source_header'],ticker+' canonical source header')
    cutoff=record['proposed_evidence_cutoff']
    require(artifact['valuation_date']==recipe['valuation_date']==recipe['evidence_cutoff']==cutoff,ticker+' preserved issuer date')
    require(all(artifact['source_financial_statement'][k]<=cutoff for k in ['filed_date','period_end']),ticker+' financial cutoff')
    require(artifact['model_version']==MODEL_VERSION and artifact['model_policy']['primary']==record['expected_model']==('fcff_dcf' if ticker=='URI' else 'residual_income'),ticker+' exact model')
    require(artifact['public_assumptions']['source_policy_binding_sha256']==manifest['quality_source_binding_sha256']==a['binding_sha256'],ticker+' public binding')
    require(artifact['issuer']['classification_confidence']==0.0 and 'Unrated' in artifact['issuer']['classification_reason'],ticker+' unrated guard')
    require(artifact['reliability']['label']=='Low' and artifact['availability_type']=='conditional_estimate' and artifact['review']['publication_state']=='review_required' and not artifact['review']['errors'],ticker+' Conditional/Low')
    require(not assess_artifact(artifact)['blocking_reasons'] and sanitize_public_artifact(artifact)==artifact,ticker+' ordinary public gate')
    expected=record['confirmed_private_range'];model=record['expected_model']
    require({k:artifact['scenario_range'][k] for k in ['low','base','high']}==expected,ticker+' values')
    require(set(artifact['models'])=={model} and artifact['models'][model]['intrinsic_value_per_share']==expected['base'],ticker+' base model')
    require(set(artifact['scenarios'])=={'bear','base','bull'},ticker+' scenarios')
    for name,key in [('bear','low'),('base','base'),('bull','high')]: require(set(artifact['scenarios'][name])=={model} and artifact['scenarios'][name][model]['intrinsic_value_per_share']==expected[key],ticker+' scenario value')
    require(recipe['ticker']==ticker and recipe['cik']==record['cik'] and recipe['private_only'] is True and recipe['baseline_version']==baseline_version(artifact),ticker+' recipe identity')
    require(digest({k:recipe[k] for k in ['scenarios','editable','warnings']})==record['bound_recipe_economic_sha256'],ticker+' economics')
    require(evaluate_recipe(recipe)['range']==expected,ticker+' exact replay')
    require(set(record['required_public_disclosures'])<=set(artifact['review']['warnings']) and set(recipe['warnings'])<=set(artifact['review']['warnings']),ticker+' warnings')
    if ticker=='URI': require(artifact['bridge_quality']['decision']=='bounded_review' and artifact['bridge_quality']['complete'] is False and artifact['bridge_quality']['intrinsic_value_range']['midpoint']==expected['base'],'URI bounded bridge not stale/complete')
    return artifact


def expected_policy(t,record,artifact_sha,old,approval_sha,binding_sha):
    require(old.get('source_epoch') is None or old['source_epoch']==record['proposed_review_hold_epoch'],t+' old epoch')
    return {'schema_version':'FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1','version':'US-QUALITY03-REVISION-FILING-HOLD-1',
        'ticker':t,'cik':record['cik'],'private_only':False,'public_release_authorized':False,'staged_public_candidate_authorized':True,
        'admission_authorized':False,'activation_authorized':False,'publication_authorized':False,'new_filing_hold_before_capture':True,
        'direct_binding_rejected':True,'auto_revaluation':False,'source_epoch':record['proposed_review_hold_epoch'],
        'reasons':['Revised Quality03 dated baseline requires new source/model/assumption review before any new financial filing or amendment can be recalculated.'],
        'pins':{'public_baseline':artifact_sha,'private_economic_payload':record['bound_recipe_economic_sha256'],
            'quality_source_policy_binding':binding_sha,'release_scope_approval':approval_sha,'predecessor_policy':digest(old)},
        'predecessor_policy_retained_for_existing_active_baseline':True,'revised_baseline_adapter_readiness_not_inherited':True}


def validate(root,manifest,*,deep=False,proof_reader=None):
    a,parent,binding,current=context(root,manifest,proof_reader)
    policies=proof(root,'refresh-policies.json',a['policies_sha256'],proof_reader)
    oldpolicies=proof(root,'approved-parent-policies.json',a['parent_policies_sha256'],proof_reader)
    require(set(policies)==set(oldpolicies),'policy membership')
    for t in policies:
        expected=expected_policy(t,binding['records'][t],current[t]['artifact_sha256'],oldpolicies[t],a['approval_sha256'],a['binding_sha256']) if t in TARGETS else oldpolicies[t]
        require(policies[t]==expected,t+' exact policy/support guard')
    if deep:
        require({p.name for p in Path(root).iterdir()}==ROOT_FILES,'root filenames')
        require({p.name for p in (Path(root)/'artifacts').iterdir()}=={t+'.json' for t in current},'artifact files')
        require({p.name for p in (Path(root)/'recipes').iterdir()}=={t+'.json' for t in manifest['private_recipe_sha256']},'recipe files')
        from .approved_inheritance import validate_inheritance
        validate_inheritance(Path(root)/'prior-catalog',parent,deep=True)
        for t,e in current.items(): proof(root,'artifacts/'+t+'.json',e['artifact_sha256'],proof_reader)
        for t,pin in manifest['private_recipe_sha256'].items(): proof(root,'recipes/'+t+'.json',pin,proof_reader)
        for t in TARGETS: target(root,manifest,t,binding['records'][t],current[t],proof_reader)
    return {t:(e['cik'],e['batch'],e['availability_type'],e['artifact_sha256']) for t,e in current.items() if t not in TARGETS}


def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader):
    _,parent,binding,current=context(root,manifest,proof_reader)
    require(ticker in current and sha(raw)==current[ticker]['artifact_sha256'],'leaf bytes')
    if ticker in TARGETS:
        target(root,manifest,ticker,binding['records'][ticker],current[ticker],proof_reader)
        return False
    return True


def validate_registry(root,manifest,registry,*,proof_reader):
    a,parent,binding,current=context(root,manifest,proof_reader)
    require(digest(registry)==a['registry_sha256'],'registry anchor')
    old=proof(root,'approved-parent-registry.json',a['parent_registry_sha256'],proof_reader)
    rows={r['ticker']:r for r in registry['entries']};oldrows={r['ticker']:r for r in old['entries']}
    require(len(rows)==len(registry['entries'])==650 and set(rows)==set(current),'registry650')
    require(registry['baseline_manifest_sha256']==a['manifest_sha256'] and registry['baseline_catalog_version']==manifest['catalog_version'],'registry lineage')
    for t in rows:
        expected=deepcopy(oldrows[t])
        if t in TARGETS: expected.update(baseline_sha256=current[t]['artifact_sha256'],availability_type='conditional_estimate',
            primary_model=binding['records'][t]['expected_model'],forecast_mode='enterprise_cash_fcff_exact' if t=='URI' else 'residual_income_exact',
            controlling_filing=binding['records'][t]['exact_source_header'],source_audit='docs/audit/us-quality03-public-staged.md',recipe_status='quality03_recipe_revision_new_filing_held')
        require(rows[t]==expected,t+' exact registry row')
    return registry


def review_selection(root,authority_file,authority,manifest,manifest_sha,*,proof_reader):
    a=anchors()
    require(set(authority)==AUTHORITY_FIELDS and authority['schema_version']==REVIEW_SCHEMA and authority['read_only'] is True,'review fields')
    require(all(authority[k] is False for k in ['admission','activation','publication','save','automatic_new_source_revaluation']),'review permission')
    require(authority['manifest_sha256']==manifest_sha==a['manifest_sha256'] and authority['catalog_version']==manifest['catalog_version'] and authority['registry_sha256']==a['registry_sha256'],'review ancestry')
    validate(root,manifest,deep=True,proof_reader=proof_reader)
    validate_registry(root,manifest,proof(authority_file.parent,'runtime/registry.json',a['registry_sha256'],proof_reader),proof_reader=proof_reader)
    proof(authority_file.parent,'runtime/refresh-policies.json',a['policies_sha256'],proof_reader)
    return root,manifest_sha
