"""Closed Batch02 staged inheritance; no admission or activation authority."""
import json,hashlib
from pathlib import Path
PARENT_SHA='eb5c0d3caeb19470d23313fd4fbeeac6f854a5f6b1803dc4785fe6fd7c9330db'
PARENT_VERSION='US-ADMITTED-B01-510-aada560a107a48e952cd9bf5'
PARENT_REGISTRY_SHA='4e5bc79677f5f9ec7f32756e08eebc5a8f014bc810384824ecd4a9e44dd98e44'
APPROVAL_SHA='61cdf3c3e504deca89120fcfaa0248b99e41a735c0b4f47b7355df67f4220a3b'
PROPOSAL_SHA='a5d410ef4b8d47ee8cce1ae99edac993f28fbf91832a4e933341b804f3209370'
RANGES_SHA='a55e48389c15cd4327ca85e191ab4745ffe63c50fd694037b55ecc7828d7f993'
SCHEMA='US-B02-APPROVED-PARENT-INHERITANCE-1'
REVIEW_SCHEMA='US-B02-READ-ONLY-STAGED-REVIEW-1'
IDENTITIES={'TNC':'0000097134','LNN':'0000836157','TKR':'0000098362','KMT':'0000055242',
 'WDFC':'0000105132','FIZZ':'0000069891','GIC':'0000945114','ROG':'0000084748',
 'JBSS':'0000880117','NGVC':'0001547459'}
TARGETS={'TNC','LNN','TKR','WDFC','FIZZ','ROG','JBSS','NGVC'}
NULLS={'GIC','KMT'}
ROOT_FILES={'manifest.json','refresh-policies.json','approved-base-manifest.json','approved-parent-manifest.json',
 'approved-parent-registry.json','approved-parent-policies.json','public-scope-authorization.json'}
ECONOMIC_HASHES={
 'TNC':'114ee1b2deadecc2ac99a3ec2453cb58006baf48da72e91ee3bcf78f440706ff',
 'LNN':'162de24440f949e16e2daf4e1348d34fd9796fdcd952236f5defd12005833035',
 'TKR':'abea36ddcb2e273a1211ccac7b566906dc56384985f22aeb6c2c17c51361c091',
 'WDFC':'c62795abc8ce68569acbd222e7bbb927f5f5abddaab3387ee33766d4f7b3b363',
 'FIZZ':'1b8038d1cba60bae4bac76f3af474593e770846bab36436f4ace62f447a73c1e',
 'ROG':'7d081b63a29cfcf81a390ce0f86212bbae0221c8e17618804c08f1b527cd7f87',
 'JBSS':'e38f11a9214bd343226d1555e031328892ebfd4950cd6e4e174707ce162983a4',
 'NGVC':'08fd6a54da8609e3df0442135d93fac3321a8d3e45f0796156ba2463a8c4f22b'}
AUTHORITY_FIELDS={'schema_version','read_only','manifest_sha256','catalog_version','registry_sha256',
 'admission','activation','publication','save','automatic_new_source_revaluation'}
def require(value,why):
 if not value:raise ValueError('Batch02 staged review rejected: '+why)
def validate(root,manifest,*,deep=False,proof_reader=None):
 require(callable(proof_reader),'verified proof reader missing')
 proof=manifest.get('approved_base_inheritance')
 require(isinstance(proof,dict) and set(proof)=={'schema_version','parent_manifest_sha256','parent_catalog_version','scope_approval_sha256','proposal_sha256'},'inheritance exact schema')
 require(proof=={'schema_version':SCHEMA,'parent_manifest_sha256':PARENT_SHA,'parent_catalog_version':PARENT_VERSION,
  'scope_approval_sha256':APPROVAL_SHA,'proposal_sha256':PROPOSAL_SHA},'parent/scope pins')
 require(manifest.get('approved_base_manifest_sha256')==PARENT_SHA
  and manifest.get('release_scope_approval_sha256')==APPROVAL_SHA,'consistent approved base/scope metadata')
 require(str(manifest.get('catalog_version','')).startswith('US-STAGED-EXPANSION-B02-520-'),'approved staged version namespace')
 require(manifest.get('base_catalog_version')==PARENT_VERSION and manifest.get('base_manifest_sha256')==PARENT_SHA,'consistent staged starting parent')
 require(manifest.get('staged_release_only') is True and manifest.get('catalog_kind')=='unadmitted_public_contract_candidate','staged scope')
 require(not manifest.get('private_integration_only') and 'private_review' not in manifest,'no private projection privilege')
 require('local_admission' not in manifest and 'supported_refresh_integration' not in manifest,'no inherited release grants')
 require(all(manifest.get(k) is False for k in ('admission','activation','publication')),'release remains unauthorized')
 require(manifest.get('staged_read_only_review_ready') is True,'read-only review marker')
 parent=proof_reader(root,'approved-parent-manifest.json',PARENT_SHA)
 require(parent.get('catalog_version')==PARENT_VERSION and len(parent['entries'])==510,'authentic510 parent')
 approval=proof_reader(root,'public-scope-authorization.json',APPROVAL_SHA)
 require(approval.get('schema_version')=='US-B02-PUBLIC-STAGED-PREPARATION-AUTHORIZATION-1'
  and approval.get('policy_scope_approved') is True and approval.get('staged_candidate_only') is True,'approved preparation only')
 require(set(approval.get('public_preparation_targets',[]))==TARGETS and set(approval.get('public_unavailable_additions',[]))==NULLS,'approved8/2 scope')
 require(approval.get('evidence_cutoff')=='2026-10-05' and approval.get('approved_proposal_sha256')==PROPOSAL_SHA,'cutoff/proposal scope')
 require(all(approval.get(k) is False for k in ('admission','activation','publication','automatic_new_source_revaluation','new_recovery','new_source_capture','next_batch')),'no broader authorization')
 old={e['ticker']:(e['cik'],e['batch'],e['availability_type'],e['artifact_sha256']) for e in parent['entries']}
 current={e['ticker']:(e['cik'],e['batch'],e['availability_type'],e['artifact_sha256']) for e in manifest['entries']}
 require(len(manifest['entries'])==len(current)==520 and set(current)==set(old)|set(IDENTITIES),'exact520 identities')
 require(all(current[t]==row for t,row in old.items()),'old510 identity/status/artifact drift')
 require(all(current[t][0]==cik and current[t][1]==52 and current[t][2]==('conditional_estimate' if t in TARGETS else 'not_available') for t,cik in IDENTITIES.items()),'new8/2 identity/status drift')
 index=manifest.get('private_recipe_sha256')
 require(isinstance(index,dict) and set(index)=={t for t,e in current.items() if e[2]!='not_available'},'public recipe membership')
 require(all(index.get(t)==d for t,d in parent['private_recipe_sha256'].items()),'old510 recipe drift')
 require(not(set(index)&NULLS),'public-null recipes absent')
 policies=proof_reader(root,'refresh-policies.json',manifest['private_refresh_policy_sha256'])
 parent_policies=proof_reader(root,'approved-parent-policies.json',parent['private_refresh_policy_sha256'])
 require(set(policies)==set(parent_policies)|set(IDENTITIES) and all(policies[t]==p for t,p in parent_policies.items()),'old policy drift')
 for t in IDENTITIES:
  p=policies[t]
  require(p.get('schema_version')=='FINSIGHT-STAGED-EXPANSION-REVIEW-HOLD-1'
   and p.get('ticker')==t and p.get('cik')==IDENTITIES[t] and p.get('private_only') is False
   and p.get('staged_public_candidate_authorized') is True
   and p.get('new_filing_hold_before_capture') is True and p.get('direct_binding_rejected') is True
   and p.get('source_epoch')=='2026-10-05'
   and all(p.get(k) is False for k in ('public_release_authorized','auto_revaluation','admission_authorized','activation_authorized','publication_authorized')),'new-filing hold contract')
 ranges={}
 for t in IDENTITIES:
  a=proof_reader(root,'artifacts/'+t+'.json',current[t][3])
  require(a.get('issuer',{}).get('cik')==IDENTITIES[t] and a.get('ticker')==t and 'private_review_only' not in a,'public artifact identity/privacy')
  values={k:a['scenario_range'][k] for k in ('low','base','high')}
  if t in TARGETS:
   require(a.get('primary_valuation_method')=='residual_income' and a['reliability']['label']=='Low','commonRI/Low')
   require(a['reliability']['source_cap']==a['reliability']['model_cap']=='Low'
    and set(a['reliability']['reasons'])=={'SPECIALIST_MODEL_UNCERTAINTY','LOW_CLASSIFICATION_CONFIDENCE'},'canonical Low uncertainty reasons')
   score=.55 if t in {'WDFC','ROG','NGVC'} else .6
   require(a['issuer'].get('classification_confidence')==score and a['issuer'].get('override_applied') is True,'documented classification/model override')
   require(a.get('model_policy',{}).get('primary')=='residual_income'
    and a.get('public_assumptions',{}).get('forecast_policy_version')=='US-B02-PUBLIC-COMMON-RI-1','public model/disclosure policy')
   ranges[t]=values
  else:
   require(all(v is None for v in values.values()) and a.get('confidence',{}).get('label') is None
    and a.get('availability_type')=='not_available' and a['review']['publication_state']=='withheld','public-null value/grade')
 raw=(json.dumps(ranges,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
 require(hashlib.sha256(raw).hexdigest()==RANGES_SHA,'accepted8 range anchor')
 if deep:
  from .artifacts import sanitize_public_artifact
  from .calculation_recipe import evaluate_recipe
  require({p.name for p in Path(root).iterdir()}==ROOT_FILES|{'artifacts','recipes'},'exact staged root allowlist; no historical release grants')
  expected={'approved-base-manifest.json':PARENT_SHA,'approved-parent-manifest.json':PARENT_SHA,
   'approved-parent-registry.json':PARENT_REGISTRY_SHA,'approved-parent-policies.json':parent['private_refresh_policy_sha256'],
   'public-scope-authorization.json':APPROVAL_SHA}
  require(manifest.get('preserved_prior_estimate_sha256')==expected,'exact preparation proof index')
  for name,digest in expected.items():proof_reader(root,name,digest)
  for t in IDENTITIES:
   a=proof_reader(root,'artifacts/'+t+'.json',current[t][3])
   require(sanitize_public_artifact(a)==a,'ordinary public projection/idempotence')
   if t in TARGETS:
    recipe=proof_reader(root,'recipes/'+t+'.json',index[t])
    economic={k:recipe[k] for k in ('scenarios','warnings','editable')}
    encoded=(json.dumps(economic,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    require(hashlib.sha256(encoded).hexdigest()==ECONOMIC_HASHES[t],'accepted economic recipe/warning anchor')
    require(set(recipe['warnings'])<=set(a['review']['warnings']),'accepted source warnings retained')
    require(evaluate_recipe(recipe)['range']==ranges[t],'new public recipe replay')
  require({p.stem for p in (Path(root)/'artifacts').glob('*.json')}==set(current),'artifact files exact')
  require({p.stem for p in (Path(root)/'recipes').glob('*.json')}==set(index),'recipe files exact')
  for t,e in current.items():proof_reader(root,'artifacts/'+t+'.json',e[3])
  for t,d in index.items():proof_reader(root,'recipes/'+t+'.json',d)
 return old
def validate_registry(root,manifest,registry,*,proof_reader=None):
 parent=proof_reader(root,'approved-parent-registry.json',PARENT_REGISTRY_SHA)
 require(registry.get('schema_version')==parent.get('schema_version') and len(registry['entries'])==520,'registry520 schema')
 require(all(row in registry['entries'] for row in parent['entries']),'old510 registry records changed')
 actual={(e['ticker'],e['cik'],e['batch'],e['availability_type']) for e in registry['entries']}
 wanted={(e['ticker'],e['cik'],e['batch'],e['availability_type']) for e in manifest['entries']}
 require(len(actual)==520 and actual==wanted,'registry identities/statuses')
