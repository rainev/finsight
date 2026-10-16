"""Closed private700 profile template, installed only into isolated prepared code."""
from copy import deepcopy
from datetime import datetime,date
from functools import lru_cache
import json,os
from pathlib import Path
from .catalog import canonical_json_bytes,sha256_bytes

ANCHORS_SHA='278f3127c5f72185823863a5dd596cbf36b1d5eebc769c7909951b372deb1570'
PROFILE='B16-B20-FROZEN-PRIVATE-1'
SCHEMA='FINSIGHT-PRIVATE-INTEGRATION-REVIEW-B16-B20-1'
REVIEW_SCHEMA='US-B16-B20-PRIVATE700-READ-ONLY-REVIEW-1'


def need(value,reason):
 if not value:raise ValueError('private700: '+reason)


@lru_cache(maxsize=1)
def anchors():
 path=Path(__file__).with_name('config')/'private_batches1620_anchors.json'
 need(path.is_file() and not path.is_symlink(),'compiled anchors missing')
 raw=path.read_bytes();need(sha256_bytes(raw)==ANCHORS_SHA,'compiled anchors changed')
 return json.loads(raw)


def file(root,relative):
 from .approved_inheritance import _file
 return _file(Path(root),relative)


def validate_manifest(manifest):
 a=anchors();need(isinstance(manifest,dict),'manifest object required')
 need(manifest.get('private_integration_only') is True and manifest.get('catalog_kind')=='private_integration_only','private wrapper required')
 need(all(manifest.get(k) is False for k in ('admission','activation','publication','staged_release_only','staged_read_only_review_ready')),'release flags changed')
 need(not ({'approved_base_inheritance','local_admission','admission_prepared_only','release_scope_approval_sha256'}&set(manifest)),'inherited grant effective on wrapper')
 baseline_fields={'schema_version','catalog_version','universe_version','valuation_date','created_at','included_batches','entries','artifact_count',
  'artifact_tree_sha256','availability_counts','private_recipe_sha256','private_refresh_policy_sha256','private_integration_only','catalog_kind','private_review',
  'base_catalog_version','base_manifest_sha256','preserved_prior_estimate_sha256','refresh_status','refresh_cutoff','source_snapshot',
  'admission','activation','publication','staged_release_only','staged_read_only_review_ready'}
 child_fields={'publication_counts','input_fingerprints','refresh_parent_catalog_version','refresh_parent_manifest_sha256'}
 need(set(manifest)<=baseline_fields|child_fields and baseline_fields<=set(manifest),'unknown authority or manifest field')
 need(manifest.get('preserved_prior_estimate_sha256')==a['preserved_file_sha256'],'preserved provenance scope changed')
 need(manifest.get('private_review')==a['review'],'closed50 identity/range/date/warning scope changed')
 need(manifest.get('base_catalog_version')==a['parent_version'] and manifest.get('base_manifest_sha256')==a['parent_manifest_sha256'],'authentic650 parent changed')
 need(manifest.get('included_batches')==list(range(1,71)) and manifest.get('artifact_count')==700,'700/batches1-70 required')
 rows=manifest.get('entries');need(isinstance(rows,list) and len(rows)==len({r['ticker'] for r in rows})==700,'exact700 identity set required')
 need(rows==a['entries'],'inherited or new membership/artifact/status changed')
 need(manifest.get('availability_counts')=={'available':104,'conditional_estimate':479,'not_available':117},'availability scope changed')
 need(manifest.get('private_recipe_sha256')==a['recipe_sha256'] and manifest.get('private_refresh_policy_sha256')==a['policies_sha256'],'recipe/policy pins changed')
 if manifest.get('catalog_version')!=a['catalog_version']:
  need(str(manifest.get('catalog_version','')).startswith('US-REFRESH-700-') and
   manifest.get('refresh_parent_catalog_version')==a['catalog_version'] and manifest.get('refresh_parent_manifest_sha256')==a['baseline_manifest_sha256'],
   'worker child lost private700 predecessor')
 return a['review']


def project(artifact,manifest,*,ticker,artifact_sha256):
 a=anchors();validate_manifest(manifest)
 expected=a['artifact_sha256'].get(ticker)
 need(expected and artifact_sha256==expected and sha256_bytes(canonical_json_bytes(artifact))==expected,'closed artifact/source/warning bytes changed: '+ticker)
 if ticker in a['new_identities']:
  from .private_integration import _walk_forbidden_keys
  _walk_forbidden_keys(artifact)
  need(artifact.get('private_review_only') is True and artifact['issuer']['cik']==a['new_identities'][ticker],'private identity changed')
  need(artifact['model_policy']['primary']==a['new_models'][ticker],'cash/pricing/withheld model type changed')
  need({k:artifact['scenario_range'][k] for k in ('low','base','high')}==a['review']['frozen_ranges'][ticker],'range changed')
  need(artifact['valuation_date']==a['review']['cutoff'] and artifact['assumption_date']==a['review']['cutoff'],'frozen dates changed')
  need(artifact['reliability']['label']==('Low' if ticker in a['new_numeric'] else None),'Low/withheld label changed')
 else:
  need(sha256_bytes(canonical_json_bytes(artifact))==a['parent_projections'][ticker]['projection_sha256'],'actual native650 projection changed')
 return deepcopy(artifact)


def consumer_disclosures(manifest,artifact,payload):
 a=anchors();validate_manifest(manifest);t=artifact['issuer']['ticker'];result=deepcopy(payload)
 if t not in a['new_identities']:
  recorded=deepcopy(a['parent_projections'][t]['disclosures']);recorded.pop('ticker',None)
  old_warnings=recorded.pop('warnings',[]);result.update(recorded)
  if old_warnings:result['warnings']=list(dict.fromkeys([*result.get('warnings',[]),*old_warnings]))
 else:
  numeric=t in a['new_numeric'];pricing=t in a['pricing_only']
  result['warnings']=list(dict.fromkeys([*result.get('warnings',[]),*artifact['review']['warnings']]))
  result['private_scope']={'private_only':True,'public_release_authorized':False,'reliability':'Low' if numeric else None,
   'kind':'earnings_pricing_only' if pricing else 'cash_DCF' if numeric else 'held','evidence_cutoff':a['review']['cutoff'],
   'financial_reference_date':artifact['source_financial_statement']['period_end'],'new_filing_review_required':True,
   'intrinsic_cash_hold_preserved':pricing or not numeric,'economic_calibration':'unvalidated','AlphaSpread_comparison':'unavailable'}
 result['private_integration_scope']={'private_only':True,'catalog_membership':700,'active_membership_unchanged':650,
  'admission':False,'activation':False,'publication':False}
 return result


def validate_catalog(root,manifest,*,runtime=None):
 a=anchors();validate_manifest(manifest);root=Path(root)
 need(not any(root.glob('local-admission-*.json')) and not(root/'public-scope-authorization.json').exists(),'new release grant forbidden')
 for relative,digest in a['preserved_file_sha256'].items():need(sha256_bytes(file(root,relative))==digest,'preserved provenance changed: '+relative)
 parent=json.loads(file(root,'inherited-parent/manifest.json'))
 need(sha256_bytes(file(root,'inherited-parent/manifest.json'))==a['parent_manifest_sha256'],'parent manifest changed')
 current={r['ticker']:r for r in manifest['entries']}
 need(all(current[r['ticker']]==r for r in parent['entries']),'old650 row changed')
 for row in manifest['entries']:
  raw=file(root,'artifacts/'+row['ticker']+'.json');need(sha256_bytes(raw)==row['artifact_sha256'],'artifact changed')
 need({p.stem for p in (root/'artifacts').glob('*.json')}==set(current),'artifact membership changed')
 need({p.stem for p in (root/'recipes').glob('*.json')}==set(a['recipe_sha256']),'583 recipe membership changed')
 for t,digest in a['recipe_sha256'].items():need(sha256_bytes(file(root,'recipes/'+t+'.json'))==digest,'recipe changed: '+t)
 need(sha256_bytes(file(root,'refresh-policies.json'))==a['policies_sha256'],'catalog policies changed')
 if runtime is not None:
  runtime=Path(runtime);registry=json.loads(file(runtime,'registry.json'));policies=json.loads(file(runtime,'refresh-policies.json'))
  need(registry['baseline_manifest_sha256']==sha256_bytes(file(root,'manifest.json')) and registry['baseline_catalog_version']==manifest['catalog_version'],'runtime baseline changed')
  rows=registry['entries'];need(len(rows)==len({r['ticker'] for r in rows})==700,'registry denominator changed')
  need({(r['ticker'],r['cik'],r['batch']) for r in rows}=={(r['ticker'],r['cik'],r['batch']) for r in manifest['entries']},'registry identities changed')
  old_registry=json.loads(file(root,'integration-parent-registry.json'));old_policies=json.loads(file(root,'integration-parent-policies.json'))
  indexed={r['ticker']:r for r in rows};need(all(indexed[r['ticker']]==r for r in old_registry['entries']),'old650 registry row changed')
  need(all(policies[t]==p for t,p in old_policies.items()) and len(policies)==631,'old581 policy coverage changed')
  need(sha256_bytes(file(runtime,'refresh-policies.json'))==a['policies_sha256'],'runtime policy pin changed')
  for t in a['new_identities']:
   p=policies[t];need(p==a['new_hold_policies'][t],'new50 hold changed')
   row=indexed[t];need(row==a['new_registry_entries'][t],'new registry/source/status changed')
 return True


def validate_review_selection(root,authority_file,authority,manifest,manifest_sha):
 a=anchors();need(os.environ.get('APP_ENV')=='test','private700 test-only')
 need(set(authority)=={'schema_version','source','read_only','private_only','catalog_version','manifest_sha256','registry_sha256','refresh_policies_sha256','preparation_authority_sha256','admission','activation','publication','save','automatic_new_source_revaluation','new_SEC_capture'},'review authority fields changed')
 need(authority['schema_version']==REVIEW_SCHEMA and authority['source']=='direct_human_preparation_scope' and authority['private_only'] is True and authority['read_only'] is True,'read-only authority missing')
 need(all(authority[k] is False for k in ('admission','activation','publication','save','automatic_new_source_revaluation','new_SEC_capture')),'review scope widened')
 run=Path(authority_file).parent
 need(run.parent.resolve()==Path(a['phase_path']).resolve() and run.name in {'run-a','run-b'} and Path(authority_file).name=='review-authority.json','review outside authorized phase')
 need(Path(root).resolve()==(run/'catalogs'/a['catalog_version']).resolve(),'review root changed')
 need(authority['catalog_version']==a['catalog_version'] and authority['manifest_sha256']==manifest_sha==a['baseline_manifest_sha256'],'review manifest pin changed')
 need(authority['preparation_authority_sha256']==a['preparation_sha256'],'preparation authority changed')
 validate_catalog(root,manifest,runtime=run/'runtime')
 need(sha256_bytes(file(run,'runtime/registry.json'))==authority['registry_sha256'] and sha256_bytes(file(run,'runtime/refresh-policies.json'))==authority['refresh_policies_sha256'],'review runtime pin changed')
 return root,manifest_sha


def metadata_hold(ticker,submissions,as_of):
 """A material same-day event after the exact source freeze cannot be ignored."""
 a=anchors()
 if ticker not in a['new_identities']:return None
 freeze=datetime.fromisoformat(a['review']['acceptance_cutoff_UTC'].replace('Z','+00:00'))
 rows=submissions.get('filings',{}).get('recent',{})
 for i,form in enumerate(rows.get('form',[])):
  filed=(rows.get('filingDate') or ['']*len(rows.get('form',[])))[i]
  if filed>as_of:continue
  items=str((rows.get('items') or ['']*len(rows.get('form',[])))[i]);accepted=(rows.get('acceptanceDateTime') or ['']*len(rows.get('form',[])))[i]
  material=form in {'8-K','8-K/A'} and any(x in items for x in ('1.01','2.01','2.03','3.02','4.02','5.02'))
  if not material:continue
  if accepted:
   instant=datetime.fromisoformat(accepted.replace('Z','+00:00'))
   need(instant.tzinfo is not None,'material event acceptance timezone missing')
   if instant.date()>date.fromisoformat(as_of):continue
   after=instant>freeze
  else:after=rows.get('filingDate',['']*len(rows['form']))[i]>=a['review']['cutoff']
  if after:return 'Private700 material event after the exact frozen acceptance cutoff: intentional review hold before capture.'
 return None
