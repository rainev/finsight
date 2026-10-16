"""Closed local700 admission and inactive retention-child contract.

Installed only through an authorized verified successor. New numerical leaves
still traverse the ordinary public sanitizer; no test/private projector grant.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import json
from .catalog import canonical_json_bytes,sha256_bytes

ANCHORS_SHA='df967c5dad0cc35aea317c479a927a410dce5c993e83ab433dd97df2103cd801'
SCHEMA='US-B1620-LOCAL-ADMISSION-INHERITANCE-1'
CHILD_SCHEMA='US-B1620-ADMITTED-RETENTION-CHILD-1'


def need(v,why):
 if not v:raise ValueError('admitted700: '+why)


@lru_cache(maxsize=1)
def anchors():
 p=Path(__file__).with_name('config')/'admitted_batches1620_anchors.json';need(p.is_file() and not p.is_symlink(),'compiled anchors missing')
 raw=p.read_bytes();need(sha256_bytes(raw)==ANCHORS_SHA,'compiled anchors changed');return json.loads(raw)


def file(root,relative):
 from .approved_inheritance import _file
 return _file(Path(root),relative)


def validate_manifest(manifest):
 a=anchors();base=a['baseline_manifest'];schema=manifest.get('approved_base_inheritance',{}).get('schema_version')
 if schema==SCHEMA:
  need(manifest==base and sha256_bytes(canonical_json_bytes(manifest))==a['baseline_manifest_sha256'],'exact admitted baseline changed')
 else:
  need(schema==CHILD_SCHEMA,'unsupported inherited grant')
  mutable={'catalog_version','valuation_date','refresh_status','refresh_cutoff','input_fingerprints','publication_counts','refresh_parent_catalog_version','refresh_parent_manifest_sha256',
   'approved_base_inheritance','local_admission','admission','activation','staged_release_only','admission_prepared_only','catalog_kind'}
  need(set(manifest)==(set(base)-{'local_admission'})|{'refresh_parent_catalog_version','refresh_parent_manifest_sha256','input_fingerprints','publication_counts'},'child manifest authority fields changed')
  need(all(manifest[k]==v for k,v in base.items() if k not in mutable),'retention child changed approved financial/source scope')
  need(manifest['approved_base_inheritance']=={**a['admission_inheritance'],'schema_version':CHILD_SCHEMA},'child ancestry changed')
  need(manifest['admission'] is False and manifest['activation'] is False and manifest['publication'] is False and manifest['staged_release_only'] is True and manifest['admission_prepared_only'] is True,'child inherited release authority')
  need(manifest['refresh_parent_manifest_sha256']==a['baseline_manifest_sha256'] and manifest['refresh_parent_catalog_version']==a['catalog_version'] and str(manifest['catalog_version']).startswith('US-REFRESH-700-'),'child lost actual admitted parent')
 need(manifest['entries']==a['entries'] and manifest['private_recipe_sha256']==a['recipe_sha256'] and manifest['private_refresh_policy_sha256']==a['policies_sha256'],'values/recipes/policy membership changed')
 return a


def authorization(root):
 a=anchors();raw=file(root,'local-release-authorization.json');need(sha256_bytes(raw)==a['preparation_sha256'],'local grant changed');grant=json.loads(raw)
 need(grant['authorization_source']=='direct_human_user' and grant['schema_version']=='US-B1620-DIRECT-LOCAL-RELEASE-1' and grant['candidate_count']==700 and grant['baseline_count']==650,'local grant scope changed')
 need(grant['admission_authorized'] is True and grant['local_activation_authorized'] is True and grant['fresh_successful_writer_locked_precommit_required'] is True and grant['actual_admitted_ACTIVE_refresh_child_Linux_before_commit_required'] is True and grant['stop_if_checks_fail'] is True,'required release gate missing')
 need(grant['public_numeric_additions']==['FCN','MMS'] and set(grant['public_null_additions'])==set(a['review']['public_nulls']),'two-target scope widened')
 need(all(grant[k] is False for k in ('publication','cloud_publication','SEC_refresh_job','new_source_capture','new_valuation_inputs','new_recovery','data_deletion','next_batch')),'scope widened to prohibited action')
 need(sha256_bytes(file(root,'confirmed-readiness-handoff.json'))==a['readiness_handoff_sha256'],'readiness approval changed')
 return grant


def project(artifact,manifest,*,ticker,artifact_sha256):
 a=validate_manifest(manifest);need(artifact_sha256==a['artifact_sha256'].get(ticker) and sha256_bytes(canonical_json_bytes(artifact))==artifact_sha256,'exact leaf changed: '+ticker)
 if ticker in a['new_identities']:
  from .artifacts import sanitize_public_artifact
  public=sanitize_public_artifact(artifact);need(public==artifact and sanitize_public_artifact(public)==public,'ordinary public routing/source gate changed')
  need((public['scenario_range']['base'] is not None)==(ticker in {'MMS','FCN'}),'two numerical additions/48 nulls changed')
  if ticker in {'MMS','FCN'}:need(public['reliability']['label']=='Low' and public['review']['publication_state']=='review_required','Low/review gate changed')
  return deepcopy(public)
 need(artifact_sha256==a['parent_projections'][ticker]['projection_sha256'],'actual prior650 consumer projection changed')
 return deepcopy(artifact)


def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader=None):
 authorization(root);a=validate_manifest(manifest);digest=sha256_bytes(raw)
 project(json.loads(raw),manifest,ticker=ticker,artifact_sha256=digest)
 return digest==a['artifact_sha256'][ticker]


def consumer_disclosures(root,manifest,artifact,payload,*,proof_reader=None):
 a=validate_manifest(manifest);authorization(root);t=artifact['issuer']['ticker'];out=deepcopy(payload)
 if t not in a['new_identities']:
  prior=deepcopy(a['parent_projections'][t]['disclosures']);prior.pop('ticker',None);warnings=prior.pop('warnings',[]);out.update(prior)
  out['warnings']=list(dict.fromkeys([*out.get('warnings',[]),*warnings]))
 else:
  out['warnings']=list(dict.fromkeys([*out.get('warnings',[]),*artifact['review']['warnings']]))
  out['expansion_scope']={'local_admitted_catalog':True,'cloud_publication_authorized':False,'numerical_estimate':t in {'MMS','FCN'},'new_filing_review_required':True,
   'financial_evidence_cutoff':a['review']['cutoff'],'reliability':'Low' if t in {'MMS','FCN'} else None,'economic_calibration':'unvalidated','AlphaSpread_comparison':'unavailable'}
 return out


def validate(root,manifest,*,deep=False,proof_reader=None):
 a=validate_manifest(manifest);authorization(root)
 if not deep:return True
 for relative,pin in a['preserved_file_sha256'].items():need(sha256_bytes(file(root,relative))==pin,'preserved proof changed: '+relative)
 need({p.stem for p in (Path(root)/'artifacts').glob('*.json')}==set(a['artifact_sha256']),'artifact membership changed')
 for t,pin in a['artifact_sha256'].items():
  raw=file(root,'artifacts/'+t+'.json');need(sha256_bytes(raw)==pin,'artifact changed: '+t)
  if t in a['new_identities']:project(json.loads(raw),manifest,ticker=t,artifact_sha256=pin)
 need({p.stem for p in (Path(root)/'recipes').glob('*.json')}==set(a['recipe_sha256']),'recipe membership changed')
 for t,pin in a['recipe_sha256'].items():need(sha256_bytes(file(root,'recipes/'+t+'.json'))==pin,'recipe changed: '+t)
 need(sha256_bytes(file(root,'refresh-policies.json'))==a['policies_sha256'],'policies changed')
 return True


def validate_catalog(root,manifest,*,runtime=None):
 a=anchors();validate(root,manifest,deep=True)
 if runtime is not None:
  reg=json.loads(file(runtime,'registry.json'));pol=json.loads(file(runtime,'refresh-policies.json'))
  need(reg['baseline_manifest_sha256']==a['baseline_manifest_sha256'] and reg['baseline_catalog_version']==a['catalog_version'],'runtime baseline changed')
  need(len(reg['entries'])==700 and {(r['ticker'],r['cik'],r['batch']) for r in reg['entries']}=={(r['ticker'],r['cik'],r['batch']) for r in a['entries']},'registry identity changed')
  need(sha256_bytes(file(runtime,'refresh-policies.json'))==a['policies_sha256'] and len(pol)==631,'runtime policy scope changed')
 return True


def metadata_hold(ticker,submissions,as_of):
 from .staged_batches1620 import metadata_hold as frozen_hold
 return frozen_hold(ticker,submissions,as_of)
