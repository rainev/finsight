"""Future-only exact Quality05 local-release contract; no grant is issued here."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import json
import re
from . import quality05_staged as stage

SCHEMA='US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1'
AUTH_SCHEMA='US-QUALITY05-EXPLICIT-LOCAL-RELEASE-1'
ANCHOR_SHA='0f4fd272ae2e751e585db259984a1e96d2edbf61745e769bc0b0185ee3a0d090'
FALSE_AUTH=('publication','cloud_deployment','push','new_SEC_capture_or_job','automatic_new_source_revaluation',
    'source_adapter_integration','DB_job_write','new_valuation','new_live_refresh_job','valuation_recalculation','new_valuation_inputs',
    'policy_economics_change','second_recovery_pass','next_batch','data_deletion')
PREPARATION_DENIED=('admission','activation','publication','Docker_operation','existing_runtime_service_operation','new_SEC_capture_or_job',
    'new_valuation','policy_economics_change','source_adapter_integration','DB_job_write','data_deletion','cloud_deployment','push','next_batch','second_recovery_pass')
AUTH_FIELDS=set(FALSE_AUTH)|{'schema_version','authorization_source','user_request','admission_authorized',
    'local_activation_authorized','local_public_visibility_authorized','data_preserving_runtime_recreation_authorized','runtime_scope',
    'confirmed_stage_manifest_sha256','stage_handoff_sha256','readiness_sha256','preparation_sha256','confirmation_sha256',
    'active_parent_manifest_sha256','revised_targets','held_updates_carry_prior','registry_sha256','policies_sha256','source_binding_sha256','issuer_cutoffs','carry_forward_prior_active','private_only_diagnostics','unchanged_control_tickers'}
FILES={'quality05-admission-stage.json','quality05-admission-confirmation.json','quality05-admission-preparation.json',
    'quality05-admission-authorization.json','quality05-admission-readiness.json'}
require,canonical,sha=stage.require,stage.canonical,stage.sha

def anchors():
    path=Path(__file__).with_name('config')/'quality05_readiness_anchors.json'
    require(path.is_file() and not path.is_symlink(),'readiness compiled anchor')
    raw=path.read_bytes();require(sha(raw)==ANCHOR_SHA,'readiness anchor changed')
    value=json.loads(raw)
    require(value['schema_version']=='US-QUALITY05-ACCEPTED-READINESS-ANCHORS-1' and set(value['targets'])==stage.TARGETS
        and len(value['targets'])==21 and set(value['held_updates'])==stage.HELD and len(value['held_updates'])==20 and set(value['carry_forward'])==stage.CARRY_FORWARD and len(value['carry_forward'])==29
        and set(value['private_only_diagnostics'])==stage.PRIVATE_ONLY and len(value['private_only_diagnostics'])==4,'readiness exact scope')
    return deepcopy(value)

def check_authorization(value,*,readiness_sha):
    a=anchors();require(set(value)==AUTH_FIELDS,'exact future grant fields')
    require(value['schema_version']==AUTH_SCHEMA and value['authorization_source']=='direct_human_user'
        and isinstance(value['user_request'],str) and value['user_request'].strip(),'explicit future human release authority')
    require(all(value[k] is True for k in ('admission_authorized','local_activation_authorized','local_public_visibility_authorized')),'release not expressly authorized')
    require(type(value['data_preserving_runtime_recreation_authorized']) is bool,'explicit separate runtime authority')
    require(value['runtime_scope']==('data_preserving_backend_worker_recreation_only' if value['data_preserving_runtime_recreation_authorized'] else 'none'),'runtime authority is narrowly scoped')
    require(all(value[k] is False for k in FALSE_AUTH),'future grant widens scope')
    require(isinstance(readiness_sha,str) and re.fullmatch('[0-9a-f]{64}',readiness_sha) and value['readiness_sha256']==readiness_sha,'readiness receipt hash')
    pins={'confirmed_stage_manifest_sha256':'stage_manifest_sha256','stage_handoff_sha256':'stage_handoff_sha256',
        'preparation_sha256':'preparation_sha256','confirmation_sha256':'confirmation_sha256',
        'active_parent_manifest_sha256':'active_parent_manifest_sha256','registry_sha256':'registry_sha256','policies_sha256':'policies_sha256',
        'source_binding_sha256':'binding_sha256','issuer_cutoffs':'issuer_cutoffs'}
    require(all(value[key]==a[pin] for key,pin in pins.items()),'future grant exact evidence ancestry')
    require(len(value['revised_targets'])==21 and set(value['revised_targets'])==stage.TARGETS
        and len(value['held_updates_carry_prior'])==20 and set(value['held_updates_carry_prior'])==stage.HELD,'future grant issuer scope')
    require(len(value['carry_forward_prior_active'])==29 and set(value['carry_forward_prior_active'])==stage.CARRY_FORWARD
        and len(value['private_only_diagnostics'])==4 and set(value['private_only_diagnostics'])==stage.PRIVATE_ONLY and set(value['unchanged_control_tickers'])==stage.CONTROLS,'future grant29/4/controls5 scope')
    require(set(value['issuer_cutoffs'])==stage.TARGETS,'exact per-issuer cutoffs')

def reader(proof_reader):
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        return proof_reader.remap_manifest('quality05-admission-stage.json')
    def wrapped(root,name,digest):
        return proof_reader(root,'quality05-admission-stage.json' if name=='manifest.json' else name,digest)
    return wrapped

@lru_cache(maxsize=4)
def _validated_frozen_semantics(files):
    # Only immutable bytes enter this cache; no cached dict can be mutated.
    records={name:(digest,raw) for name,digest,raw in files}
    def verified_memory(root,name,digest):
        wanted,raw=records[name]
        require(wanted==digest,'stage semantic proof pin')
        return json.loads(raw)
    stage.validate(Path('.'),json.loads(records['manifest.json'][1]),deep=False,proof_reader=verified_memory)
    return True

def validate_frozen_semantics(root,frozen,proof_reader):
    from .approved_inheritance import _proof as native_reader,_file
    if proof_reader is not native_reader:
        # Custom readers get full content-derived validation, never this cache.
        stage.validate(root,frozen,deep=False,proof_reader=reader(proof_reader));return
    a=stage.anchors()
    pins={'manifest.json':a['manifest_sha256'],'approved-parent-manifest.json':a['parent_manifest_sha256'],
        'quality-scope-authorization.json':a['approval_sha256'],'quality-source-binding.json':a['binding_sha256'],
        'quality-private-confirmation.json':a['confirmation_sha256'],'quality-eligibility-proposal.json':a['proposal_sha256'],
        'quality-eligibility-verification.json':a['eligibility_sha256'],'refresh-policies.json':a['policies_sha256'],
        'approved-parent-policies.json':a['parent_policies_sha256']}
    files=[]
    for name,digest in sorted(pins.items()):
        raw=_file(root,'quality05-admission-stage.json' if name=='manifest.json' else name)
        require(sha(raw)==digest,'current stage semantic proof bytes: '+name)
        files.append((name,digest,raw))
    require(_validated_frozen_semantics(tuple(files)),'frozen semantic validation')

def _metadata_uncached(root,manifest,*,proof_reader):
    require(callable(proof_reader),'verified proof reader required')
    a=anchors();grant=manifest.get('local_admission')
    require(isinstance(grant,dict) and set(grant)=={'schema_version','authorization_sha256','readiness_sha256'}
        and grant['schema_version']==AUTH_SCHEMA,'separate Quality05 release grant required')
    frozen=stage.proof(root,'quality05-admission-stage.json',a['stage_manifest_sha256'],proof_reader)
    confirmation=stage.proof(root,'quality05-admission-confirmation.json',a['confirmation_sha256'],proof_reader)
    preparation=stage.proof(root,'quality05-admission-preparation.json',a['preparation_sha256'],proof_reader)
    authorization=stage.proof(root,'quality05-admission-authorization.json',grant['authorization_sha256'],proof_reader)
    readiness=stage.proof(root,'quality05-admission-readiness.json',grant['readiness_sha256'],proof_reader)
    check_authorization(authorization,readiness_sha=grant['readiness_sha256'])
    require(confirmation['confirmed_scope']=='sealed_quality05_staged_candidate_only' and confirmation['manifest_sha256']==a['stage_manifest_sha256']
        and confirmation['handoff_sha256']==a['stage_handoff_sha256'] and all(confirmation[k] is False for k in ('admission','activation','publication')),'confirmation is not release')
    require(preparation['schema_version']=='US-QUALITY05-READINESS-PREPARATION-1' and preparation['readiness_preparation_authorized'] is True
        and preparation['confirmed_stage_manifest_sha256']==a['stage_manifest_sha256'] and preparation['stage_confirmation_sha256']==a['confirmation_sha256']
        and all(preparation[k] is False for k in PREPARATION_DENIED),'readiness preparation is not release')
    require(readiness['schema_version']=='US-QUALITY05-READINESS-HANDOFF-1' and readiness['status']=='verified_pending_single_local_admission_activation_decision','verified readiness status')
    expected={'manifest_sha256':a['stage_manifest_sha256'],'stage_handoff_sha256':a['stage_handoff_sha256'],
        'confirmation_sha256':a['confirmation_sha256'],'preparation_sha256':a['preparation_sha256'],
        'active_parent_manifest_sha256':a['active_parent_manifest_sha256'],'registry_sha256':a['registry_sha256'],
        'policies_sha256':a['policies_sha256'],'source_binding_sha256':a['binding_sha256'],
        'candidate_count':650,'numeric_count':572,'unavailable_count':78,'revised_count':21,'carried_forward_count':629,'reviewed_carry_forward_count':29,'held_update_carry_forward_count':20,'private_only_diagnostic_count':4,'unchanged_control_count':5,
        'issuer_cutoffs':a['issuer_cutoffs'],'existing_refresh_support_and_policy_epochs_preserved':True,
        'fresh_successful_post_authorization_precommit_required':True,'real_admitted_ACTIVE_and_child_verification_pending_separate_authority':True}
    require(all(readiness[k]==v for k,v in expected.items()) and all(readiness[k] is False for k in PREPARATION_DENIED),'readiness exact scope/authority')
    receipts=readiness['verification_receipts']
    require(set(receipts)=={'http_main','http_worktree','offline_workers','entrypoint_refusals','targeted_main','targeted_worktree','dated_holds','future_grant','current_preflight','source_refresh_inventory'}
        and all(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) for v in receipts.values()),'readiness final evidence pins')
    mutable={'catalog_version','catalog_kind','staged_release_only','staged_read_only_review_ready','admission_prepared_only','admission','approved_base_inheritance','local_admission'}
    require(set(manifest)==set(frozen)|{'local_admission'} and all(manifest[k]==v for k,v in frozen.items() if k not in mutable),'admission changed economics/source/holds')
    require(manifest['approved_base_inheritance']=={'schema_version':SCHEMA,'confirmed_stage_manifest_sha256':a['stage_manifest_sha256'],
        'confirmation_sha256':a['confirmation_sha256'],'preparation_sha256':a['preparation_sha256']},'exact future admitted lineage')
    require(manifest['catalog_version'].startswith('US-ADMITTED-QUALITY05-650-') and manifest['catalog_kind']=='admitted_local_quality05_revision'
        and manifest['admission'] is True and all(manifest[k] is False for k in ('staged_release_only','staged_read_only_review_ready','admission_prepared_only','activation','publication')),'local-only admission metadata')
    validate_frozen_semantics(root,frozen,proof_reader)
    binding=stage.proof(root,'quality-source-binding.json',a['binding_sha256'],proof_reader)
    policies=stage.proof(root,'refresh-policies.json',a['policies_sha256'],proof_reader)
    old=stage.proof(root,'approved-parent-policies.json',stage.anchors()['parent_policies_sha256'],proof_reader)
    new_epochs=set()
    for t in stage.TARGETS:
        row=binding['records'][t]; epoch=a['issuer_cutoffs'][t]
        require(epoch==row['proposed_evidence_cutoff']==row['proposed_public_valuation_date']==row['proposed_review_hold_epoch']==policies[t]['source_epoch'],t+' exact issuer epoch')
        if old[t].get('source_epoch') is None:new_epochs.add(t)
        else:require(old[t]['source_epoch']==epoch,t+' inherited epoch retained')
    require(new_epochs=={t for t in stage.TARGETS if old[t].get('source_epoch') is None},'new source epochs match inherited support')
    return frozen

@lru_cache(maxsize=4)
def _metadata_bytes(files,manifest_bytes):
    # Only currently authenticated immutable bytes enter the cache. A custom
    # reader always receives full content-derived verification, never this path.
    indexed={name:(pin,raw) for name,pin,raw in files}
    def memory(root,name,pin):
        expected,raw=indexed[name];require(expected==pin,'immutable admission proof pin')
        return json.loads(raw)
    frozen=_metadata_uncached(Path('.'),json.loads(manifest_bytes),proof_reader=memory)
    return canonical(frozen)

def metadata(root,manifest,*,proof_reader):
    from .approved_inheritance import _proof as authenticated_native_reader
    from .read_path_snapshot import SnapshotProofReader
    if type(proof_reader) is SnapshotProofReader:
        # The native path rehashes current proof bytes and checks the caller
        # manifest before its immutable-content semantic cache can be used.
        # Keep request-scoped fresh objects; never cache by root/path alone.
        return proof_reader.metadata_for(root, manifest, lambda: metadata(root, manifest, proof_reader=authenticated_native_reader))
    from .approved_inheritance import _proof as native_reader,_file
    if proof_reader is not native_reader:return _metadata_uncached(root,manifest,proof_reader=proof_reader)
    a=anchors();sa=stage.anchors();grant=manifest.get('local_admission')
    require(isinstance(grant,dict) and set(grant)=={'schema_version','authorization_sha256','readiness_sha256'}
        and grant['schema_version']==AUTH_SCHEMA,'separate exact Quality05 grant')
    require(all(isinstance(grant[k],str) and re.fullmatch('[0-9a-f]{64}',grant[k]) for k in ['authorization_sha256','readiness_sha256']),'grant proof digests')
    pins={'quality05-admission-stage.json':a['stage_manifest_sha256'],
        'quality05-admission-confirmation.json':a['confirmation_sha256'],
        'quality05-admission-preparation.json':a['preparation_sha256'],
        'quality05-admission-authorization.json':grant['authorization_sha256'],
        'quality05-admission-readiness.json':grant['readiness_sha256'],
        'approved-parent-manifest.json':sa['parent_manifest_sha256'],
        'quality-scope-authorization.json':sa['approval_sha256'],
        'quality-source-binding.json':sa['binding_sha256'],
        'quality-private-confirmation.json':sa['confirmation_sha256'],
        'quality-eligibility-proposal.json':sa['proposal_sha256'],
        'quality-eligibility-verification.json':sa['eligibility_sha256'],
        'refresh-policies.json':sa['policies_sha256'],
        'approved-parent-policies.json':sa['parent_policies_sha256']}
    files=[]
    for name,pin in sorted(pins.items()):
        raw=_file(root,name);require(sha(raw)==pin,'current admission proof bytes: '+name)
        files.append((name,pin,raw))
    require(json.loads(_file(root,'manifest.json'))==manifest,'current admitted manifest object changed')
    return json.loads(_metadata_bytes(tuple(files),canonical(manifest)))

def validate(root,manifest,*,deep=False,proof_reader=None):
    frozen=metadata(root,manifest,proof_reader=proof_reader)
    if deep:
        require({p.name for p in Path(root).iterdir()}==stage.ROOT_FILES|FILES,'future admitted root filenames')
        require({p.name for p in (Path(root)/'artifacts').iterdir()}=={e['ticker']+'.json' for e in frozen['entries']},'future artifact membership')
        require({p.name for p in (Path(root)/'recipes').iterdir()}=={t+'.json' for t in frozen['private_recipe_sha256']},'future recipe membership')
        for e in frozen['entries']:stage.proof(root,'artifacts/'+e['ticker']+'.json',e['artifact_sha256'],proof_reader)
        for t,d in frozen['private_recipe_sha256'].items():stage.proof(root,'recipes/'+t+'.json',d,proof_reader)
        binding=stage.proof(root,'quality-source-binding.json',anchors()['binding_sha256'],proof_reader)
        for t in stage.TARGETS:stage.target(root,frozen,t,binding['records'][t],next(e for e in frozen['entries'] if e['ticker']==t),reader(proof_reader))
        from .approved_inheritance import validate_inheritance
        parent=stage.proof(root,'approved-parent-manifest.json',stage.anchors()['parent_manifest_sha256'],proof_reader)
        validate_inheritance(Path(root)/'prior-catalog',parent,deep=True)
    return {e['ticker']:e for e in frozen['entries'] if e['ticker'] not in stage.TARGETS}

def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader):
    frozen=metadata(root,manifest,proof_reader=proof_reader)
    entry=next((e for e in frozen['entries'] if e['ticker']==ticker),None)
    require(entry is not None and sha(raw)==entry['artifact_sha256'],'current admitted artifact bytes')
    if ticker in stage.TARGETS:
        binding=stage.proof(root,'quality-source-binding.json',anchors()['binding_sha256'],proof_reader)
        stage.target(root,frozen,ticker,binding['records'][ticker],entry,reader(proof_reader))
        return False
    return True

def consumer_disclosures(root,manifest,artifact,payload,*,proof_reader):
    frozen=metadata(root,manifest,proof_reader=proof_reader)
    if artifact['issuer']['ticker'] not in stage.TARGETS|stage.CARRY_FORWARD:
        from .quality04_admission import consumer_disclosures as parent_disclosures
        parent=stage.proof(root,'approved-parent-manifest.json',stage.anchors()['parent_manifest_sha256'],proof_reader)
        return parent_disclosures(Path(root)/'prior-catalog',parent,artifact,payload,proof_reader=proof_reader)
    from .quality05_disclosures import consumer_disclosures as staged_disclosures
    result=staged_disclosures(root,frozen,artifact,payload,proof_reader=reader(proof_reader))
    scope=result.pop('staged_scope')
    for key in ('admission','activation','publication','read_only'):scope.pop(key,None)
    scope.update(schema_version=SCHEMA,local_admission_authorized=True,local_public_visibility_authorized=True,cloud_publication_authorized=False)
    result['admitted_scope']=scope
    result['warnings'].append('Inactive stage-origin wording remains historical provenance; explicit local admission permits only this dated estimate, not cloud publication, new-filing support or economic calibration.')
    return result
