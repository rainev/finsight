"""Offline verification-only status children of the frozen Quality03 stage."""
from copy import deepcopy
from collections import Counter
from pathlib import Path
import shutil
from . import quality03_staged as stage

SCHEMA = 'US-QUALITY03-OFFLINE-RETENTION-CHILD-1'
EXTRA = {'quality03-refresh-stage.json','quality03-refresh-authorization.json','quality03-refresh-status.json'}
ALLOWED = {'checked_unchanged','prior_unavailable','held_new_filing'}
require, canonical, sha = stage.require, stage.canonical, stage.sha

def reader(proof_reader):
    def wrapped(root,name,digest):
        return proof_reader(root,'quality03-refresh-stage.json' if name=='manifest.json' else name,digest)
    return wrapped

def validate(root,manifest,*,deep=False,proof_reader=None):
    a = stage.anchors()
    parent = stage.proof(root,'quality03-refresh-stage.json',a['manifest_sha256'],proof_reader)
    grant = stage.proof(root,'quality03-refresh-authorization.json',a['approval_sha256'],proof_reader)
    require(grant['staged_candidate_only'] is True and all(grant[k] is False for k in stage.DENIED),'offline child authority is not release')
    require(manifest['approved_base_inheritance'] == {'schema_version':SCHEMA,'quality_stage_manifest_sha256':a['manifest_sha256'],'authorization_sha256':a['approval_sha256']},'exact child ancestry')
    require(manifest['catalog_kind']=='quality03_offline_verification_retention_child' and manifest['staged_release_only'] is True and manifest['staged_read_only_review_ready'] is False and manifest['admission_prepared_only'] is False,'offline-only child')
    require(all(manifest[k] is False for k in ('admission','activation','publication')) and 'local_admission' not in manifest,'child release flags')
    require(manifest['refresh_parent_catalog_version']==parent['catalog_version'] and manifest['refresh_parent_manifest_sha256']==a['manifest_sha256'],'immediate refresh parent')
    require(manifest['base_catalog_version']==parent['base_catalog_version'] and manifest['base_manifest_sha256']==parent['base_manifest_sha256'],'approved parent distinct from refresh parent')
    mutable = {'catalog_version','valuation_date','base_catalog_version','base_manifest_sha256','publication_counts','refresh_status','refresh_cutoff','input_fingerprints','preserved_prior_estimate_sha256','refresh_parent_catalog_version','refresh_parent_manifest_sha256','approved_base_inheritance','catalog_kind','staged_release_only','staged_read_only_review_ready','admission_prepared_only','quality03_retention_receipt_sha256'}
    require(set(manifest) <= set(parent)|mutable and all(manifest[k]==v for k,v in parent.items() if k not in mutable),'child economic/policy/source mutation')
    original = stage.validate(root,parent,deep=False,proof_reader=reader(proof_reader))
    receipt = stage.proof(root,'quality03-refresh-status.json',manifest['quality03_retention_receipt_sha256'],proof_reader)
    require(receipt['base_manifest_sha256']==a['manifest_sha256'] and receipt['active_changed'] is False and receipt['source_bound_recalculations']==0 and receipt['offline_verification_only'] is True,'status receipt')
    rows = receipt['rows']
    require(len(rows)==len({r['ticker'] for r in rows})==650 and {r['ticker'] for r in rows}=={e['ticker'] for e in parent['entries']},'all650 outcomes')
    require(set(r['outcome'] for r in rows)<=ALLOWED and dict(Counter(r['outcome'] for r in rows))==receipt['counts'],'no recalculations')
    require(set(manifest['refresh_status'])=={r['ticker'] for r in rows},'complete status mapping')
    for row in rows:
        status = manifest['refresh_status'][row['ticker']]
        require(status['outcome']==row['outcome'] and status['checked_as_of']==receipt['cutoff'],'status accounting')
        if row['ticker'] in stage.TARGETS and row.get('latest_accession') != row.get('prior_accession'):
            require(row['outcome']=='held_new_filing','changed target outside its hold')
    if deep:
        require({p.name for p in Path(root).iterdir()}==stage.ROOT_FILES|EXTRA,'child proof filenames')
        expected = {str(p.relative_to(root)):sha(p.read_bytes()) for p in Path(root).rglob('*') if p.is_file() and p != Path(root)/'manifest.json' and not str(p.relative_to(root)).startswith(('artifacts/','recipes/'))}
        require(manifest['preserved_prior_estimate_sha256']==expected,'actual child proof index')
        for entry in parent['entries']: stage.proof(root,'artifacts/'+entry['ticker']+'.json',entry['artifact_sha256'],proof_reader)
        for t,d in parent['private_recipe_sha256'].items(): stage.proof(root,'recipes/'+t+'.json',d,proof_reader)
        for t in stage.TARGETS:
            binding = stage.proof(root,'quality-source-binding.json',a['binding_sha256'],proof_reader)
            stage.target(root,parent,t,binding['records'][t],next(e for e in parent['entries'] if e['ticker']==t),reader(proof_reader))
        from .approved_inheritance import validate_inheritance
        old = stage.proof(root,'approved-parent-manifest.json',a['parent_manifest_sha256'],proof_reader)
        validate_inheritance(Path(root)/'prior-catalog',old,deep=True)
    return original

def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader):
    validate(root,manifest,deep=False,proof_reader=proof_reader)
    parent = stage.proof(root,'quality03-refresh-stage.json',stage.anchors()['manifest_sha256'],proof_reader)
    return stage.preserved_parent_artifact(root,parent,ticker,raw,proof_reader=reader(proof_reader))

def assemble(active,manifest,destination,rows,cutoff,*,copy_function=None):
    import os
    require(os.environ.get('APP_ENV')=='test','offline verification environment')
    a=stage.anchors()
    require(active.manifest_sha256==a['manifest_sha256'] and not any(r['outcome']=='source_bound' for r in rows),'compiled baseline and no new valuations')
    copier=copy_function or shutil.copy2
    destination=Path(destination)
    for name in stage.ROOT_FILES-{'manifest.json','artifacts','recipes','refresh-policies.json'}:
        source,target=active.root/name,destination/name
        if source.is_dir(): shutil.copytree(source,target,copy_function=copier)
        else: copier(source,target)
    for name,source,pin in [('quality03-refresh-stage.json',active.root/'manifest.json',a['manifest_sha256']),('quality03-refresh-authorization.json',active.root/'quality-scope-authorization.json',a['approval_sha256'])]:
        raw=source.read_bytes();require(sha(raw)==pin,'offline child authority bytes');(destination/name).write_bytes(raw)
    receipt={'schema_version':'US-QUALITY03-OFFLINE-RETENTION-STATUS-1','base_manifest_sha256':active.manifest_sha256,'cutoff':cutoff,'rows':rows,'counts':dict(Counter(r['outcome'] for r in rows)),'active_changed':False,'source_bound_recalculations':0,'offline_verification_only':True}
    raw=canonical(receipt);(destination/'quality03-refresh-status.json').write_bytes(raw)
    manifest.update(approved_base_inheritance={'schema_version':SCHEMA,'quality_stage_manifest_sha256':a['manifest_sha256'],'authorization_sha256':a['approval_sha256']},base_catalog_version=active.manifest['base_catalog_version'],base_manifest_sha256=active.manifest['base_manifest_sha256'],refresh_parent_catalog_version=active.catalog_version,refresh_parent_manifest_sha256=active.manifest_sha256,staged_release_only=True,staged_read_only_review_ready=False,admission_prepared_only=False,admission=False,activation=False,publication=False,catalog_kind='quality03_offline_verification_retention_child',quality03_retention_receipt_sha256=sha(raw))
    manifest['preserved_prior_estimate_sha256']={str(p.relative_to(destination)):sha(p.read_bytes()) for p in destination.rglob('*') if p.is_file() and not str(p.relative_to(destination)).startswith(('artifacts/','recipes/'))}
