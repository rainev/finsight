"""Closed future B02 local admission proof; preparation never grants release."""
from copy import deepcopy
from pathlib import Path
from .staged_batch02_inheritance import validate as validate_stage,ROOT_FILES,TARGETS,NULLS,PARENT_SHA,PARENT_VERSION
SCHEMA='US-B02-LOCAL-ADMISSION-INHERITANCE-1'
STAGE_SHA='b591b6e7d081d5102762c373e2474b1b08320ecc354c0efd4d8d3064c0a3c954'
CONFIRMATION_SHA='77485041a045ef547de84307bcf80761be76eb6535d1fe8b9e44ac41ef142be1'
PREPARATION_SHA='97b363e2cc6533a078afa185630ab4553c053b3e644de8e2139b759a8f377e90'
STAGE_REGISTRY_SHA='31cf53fc7e1b91ba2150574bd4ef5f47bd08562712c011c8faad95ff8e209324'
POLICIES_SHA='f7b9df0257015474f63827a0ce07cb3bb1f1f68f4c4a35e3febb99869a29c9bd'
EXTRA_FILES={'local-admission-stage.json','local-admission-confirmation.json','local-admission-preparation.json',
 'local-admission-authorization.json','local-admission-readiness.json'}
FALSE_AUTH=('automatic_new_source_revaluation','new_source_capture','new_recovery','next_batch','cloud_deployment','push','publication',
 'save','source_adapter_integration','DB_job_write','live_SEC_refresh')
AUTH_FIELDS=set(FALSE_AUTH)|{'schema_version','authorization_source','user_request','admission_authorized','local_activation_authorized',
 'local_public_visibility_authorized','confirmed_stage_manifest_sha256','readiness_sha256','readiness_preparation_sha256',
 'stage_confirmation_sha256','active_parent_manifest_sha256','public_numeric_additions','public_null_additions',
 'new_filing_holds','evidence_cutoff','staged_registry_sha256','refresh_policy_sha256'}
def require(value,why):
 if not value:raise ValueError('Batch02 local admission rejected: '+why)
def validate(root,manifest,*,deep=False,proof_reader=None):
 require(callable(proof_reader),'verified proof reader missing')
 grant=manifest.get('local_admission');proof=manifest.get('approved_base_inheritance')
 require(isinstance(grant,dict) and set(grant)=={'schema_version','authorization_sha256','readiness_sha256'}
  and grant['schema_version']=='US-B02-LOCAL-ADMISSION-1','separate local grant required')
 expected={'schema_version':SCHEMA,'confirmed_stage_manifest_sha256':STAGE_SHA,
  'stage_confirmation_sha256':CONFIRMATION_SHA,'readiness_preparation_sha256':PREPARATION_SHA}
 require(proof==expected,'exact stage/confirmation/preparation pins')
 stage=proof_reader(root,'local-admission-stage.json',STAGE_SHA)
 confirmation=proof_reader(root,'local-admission-confirmation.json',CONFIRMATION_SHA)
 preparation=proof_reader(root,'local-admission-preparation.json',PREPARATION_SHA)
 require(confirmation.get('manifest_sha256')==STAGE_SHA and confirmation.get('confirmed_scope')=='sealed_staged_public_candidate_only'
  and all(confirmation.get(k) is False for k in ('admission','activation','publication')),'confirmation is not release authority')
 require(preparation.get('readiness_preparation_authorized') is True and preparation.get('confirmed_staged_manifest_sha256')==STAGE_SHA
  and all(preparation.get(k) is False for k in ('admission','activation','publication','automatic_new_source_revaluation')),'preparation is not release authority')
 authorization=proof_reader(root,'local-admission-authorization.json',grant['authorization_sha256'])
 readiness=proof_reader(root,'local-admission-readiness.json',grant['readiness_sha256'])
 require(set(authorization)==AUTH_FIELDS and authorization.get('schema_version')=='US-B02-EXPLICIT-LOCAL-RELEASE-AUTHORIZATION-1'
  and authorization.get('authorization_source')=='direct_human_user'
  and isinstance(authorization.get('user_request'),str) and authorization['user_request'].strip()
  and all(authorization.get(k) is True for k in ('admission_authorized','local_activation_authorized','local_public_visibility_authorized'))
  and all(authorization.get(k) is False for k in FALSE_AUTH),'explicit local-only human authority')
 require(authorization.get('confirmed_stage_manifest_sha256')==STAGE_SHA
  and authorization.get('readiness_sha256')==grant['readiness_sha256']
  and authorization.get('readiness_preparation_sha256')==PREPARATION_SHA
  and authorization.get('stage_confirmation_sha256')==CONFIRMATION_SHA
  and authorization.get('active_parent_manifest_sha256')==PARENT_SHA,'release authority binds exact reviewed scope')
 require(authorization.get('staged_registry_sha256')==STAGE_REGISTRY_SHA
  and authorization.get('refresh_policy_sha256')==POLICIES_SHA,'exact staged runtime/policy authority')
 require(set(authorization.get('public_numeric_additions',[]))==TARGETS and set(authorization.get('public_null_additions',[]))==NULLS
  and authorization.get('new_filing_holds')==10 and authorization.get('evidence_cutoff')=='2026-10-05','approved8/2/10 hold scope')
 require(readiness.get('schema_version')=='US-B02-ADMISSION-READINESS-HANDOFF-1'
  and readiness.get('status')=='verified_pending_single_admission_local_activation_decision'
  and readiness.get('manifest_sha256')==STAGE_SHA and readiness.get('live_count')==510
  and readiness.get('candidate_count')==520 and readiness.get('public_numeric_count')==485 and readiness.get('public_null_count')==35
  and readiness.get('new_declared_filing_holds')==10 and readiness.get('new_auto_revaluation_ready')==0
  and readiness.get('approved_values_and_holds_preserved') is True
  and all(readiness.get(k) is False for k in ('admission','activation','publication','live_runtime_promotion')),'verified readiness receipt')
 require(readiness.get('confirmation_sha256')==CONFIRMATION_SHA and readiness.get('preparation_sha256')==PREPARATION_SHA,'readiness confirmation pins')
 require(readiness.get('staged_registry_sha256')==STAGE_REGISTRY_SHA
  and readiness.get('refresh_policy_sha256')==POLICIES_SHA
  and stage.get('private_refresh_policy_sha256')==POLICIES_SHA,'readiness runtime/policy pins')
 # Validate the authentic stage against the unchanged artifacts/policies. Do not
 # route an admitted manifest into the staged validator or weaken that validator.
 originals=validate_stage(root,stage,deep=False,proof_reader=proof_reader)
 changed={'catalog_version','catalog_kind','staged_release_only','admission_prepared_only','staged_read_only_review_ready',
  'admission','approved_base_inheritance','local_admission','preserved_prior_estimate_sha256'}
 require(set(manifest)==set(stage)|{'local_admission'},'admitted metadata exact membership')
 require(all(manifest[k]==v for k,v in stage.items() if k not in changed),'accepted stage economics/metadata changed')
 require(str(manifest.get('catalog_version','')).startswith('US-ADMITTED-B02-520-')
  and manifest.get('catalog_kind')=='admitted_local_expansion'
  and manifest.get('staged_release_only') is False and manifest.get('admission_prepared_only') is False
  and manifest.get('staged_read_only_review_ready') is False and manifest.get('admission') is True
  and manifest.get('activation') is False and manifest.get('publication') is False,'admitted baseline scope; not cloud release')
 preserved={**stage['preserved_prior_estimate_sha256'],'local-admission-stage.json':STAGE_SHA,
  'local-admission-confirmation.json':CONFIRMATION_SHA,'local-admission-preparation.json':PREPARATION_SHA,
  'local-admission-authorization.json':grant['authorization_sha256'],'local-admission-readiness.json':grant['readiness_sha256']}
 require(manifest.get('preserved_prior_estimate_sha256')==preserved,'exact admission proof index')
 require(manifest.get('base_manifest_sha256')==PARENT_SHA and manifest.get('base_catalog_version')==PARENT_VERSION,'actual510 parent')
 if deep:
  require({p.name for p in Path(root).iterdir()}==ROOT_FILES|EXTRA_FILES|{'artifacts','recipes'},'exact admitted root allowlist')
  for name,digest in preserved.items():proof_reader(root,name,digest)
  require({p.name for p in (Path(root)/'artifacts').iterdir()}=={e['ticker']+'.json' for e in stage['entries']},'artifact membership')
  for entry in stage['entries']:proof_reader(root,'artifacts/'+entry['ticker']+'.json',entry['artifact_sha256'])
  require({p.name for p in (Path(root)/'recipes').iterdir()}=={t+'.json' for t in stage['private_recipe_sha256']},'recipe membership')
  for t,digest in stage['private_recipe_sha256'].items():proof_reader(root,'recipes/'+t+'.json',digest)
 return originals
