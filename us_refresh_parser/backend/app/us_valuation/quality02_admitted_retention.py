"""Inactive byte-retaining children of a real human-admitted Quality02 parent."""
from collections import Counter
from pathlib import Path
import shutil
from . import quality02_admission as admission
from . import quality02_staged as stage

SCHEMA='US-QUALITY02-ADMITTED-RETENTION-CHILD-1'
ROOT_FILES={'manifest.json','artifacts','recipes','refresh-policies.json','admission-parent','quality02-admitted-parent.json','quality02-admitted-status.json'}
ALLOWED={'checked_unchanged','prior_unavailable','held_new_filing'}
require,canonical,sha=stage.require,stage.canonical,stage.sha

def validate(root,manifest,*,deep=False,proof_reader=None):
    require(callable(proof_reader),'verified admitted-child proof reader')
    a=admission.anchors();lineage=manifest.get('approved_base_inheritance')
    require(isinstance(lineage,dict) and set(lineage)=={'schema_version','admitted_parent_manifest_sha256','quality_stage_manifest_sha256','authorization_sha256','readiness_sha256'}
        and lineage['schema_version']==SCHEMA and lineage['quality_stage_manifest_sha256']==a['stage_manifest_sha256'],'exact admitted-child ancestry')
    parent=stage.proof(root,'quality02-admitted-parent.json',lineage['admitted_parent_manifest_sha256'],proof_reader)
    nested=Path(root)/'admission-parent'
    require(stage.proof(nested,'manifest.json',lineage['admitted_parent_manifest_sha256'],proof_reader)==parent,'exact retained actual admitted parent')
    originals=admission.validate(nested,parent,deep=deep,proof_reader=proof_reader)
    require(parent['local_admission']['authorization_sha256']==lineage['authorization_sha256'] and parent['local_admission']['readiness_sha256']==lineage['readiness_sha256'],'actual human grant/readiness ancestry')
    require(manifest['refresh_parent_manifest_sha256']==lineage['admitted_parent_manifest_sha256'] and manifest['refresh_parent_catalog_version']==parent['catalog_version'],'immediate actual refresh parent')
    require(manifest['base_manifest_sha256']==parent['base_manifest_sha256'] and manifest['base_catalog_version']==parent['base_catalog_version'],'approved old parent distinct from refresh parent')
    require(manifest['staged_release_only'] is True and manifest['admission_prepared_only'] is True and manifest['staged_read_only_review_ready'] is False
        and manifest['catalog_kind']=='unadmitted_quality02_admitted_retention_child','inactive child metadata')
    require(all(manifest[k] is False for k in ('admission','activation','publication')) and 'local_admission' not in manifest,'baseline release grant leaked to child')
    mutable={'catalog_version','valuation_date','publication_counts','refresh_status','refresh_cutoff','input_fingerprints','preserved_prior_estimate_sha256',
        'refresh_parent_catalog_version','refresh_parent_manifest_sha256','approved_base_inheritance','catalog_kind','staged_release_only','staged_read_only_review_ready',
        'admission_prepared_only','admission','local_admission','quality02_admitted_retention_receipt_sha256'}
    require(set(manifest)==(set(parent)-{'local_admission'})|{'refresh_parent_catalog_version','refresh_parent_manifest_sha256','refresh_cutoff','refresh_status','input_fingerprints','preserved_prior_estimate_sha256','quality02_admitted_retention_receipt_sha256'},'exact child manifest fields')
    require(all(manifest[k]==v for k,v in parent.items() if k not in mutable),'child economics/source/recipe/policy/identity changed')
    receipt=stage.proof(root,'quality02-admitted-status.json',manifest['quality02_admitted_retention_receipt_sha256'],proof_reader)
    require(receipt['schema_version']=='US-QUALITY02-ADMITTED-RETENTION-STATUS-1' and receipt['parent_manifest_sha256']==lineage['admitted_parent_manifest_sha256']
        and receipt['cutoff']==manifest['refresh_cutoff'] and receipt['active_changed'] is False and receipt['source_bound_recalculations']==0,'status parent and no recalculation authority')
    rows=receipt['rows'];require(len(rows)==len({r['ticker'] for r in rows})==650 and {r['ticker'] for r in rows}=={e['ticker'] for e in parent['entries']},'all650 issuer outcomes')
    require(set(r['outcome'] for r in rows)<=ALLOWED and dict(Counter(r['outcome'] for r in rows))==receipt['counts'],'retention-only outcomes')
    require(set(manifest['refresh_status'])=={r['ticker'] for r in rows},'exact issuer status membership')
    for row in rows:
        status=manifest['refresh_status'][row['ticker']]
        require(status['outcome']==row['outcome'] and status['checked_as_of']==receipt['cutoff'],'issuer status mapping')
        if row['ticker'] in stage.TARGETS and row.get('latest_accession')!=row.get('prior_accession'):
            require(row['outcome']=='held_new_filing','changed target lost filing hold')
        if row['ticker'] in {'CBT','UTMD'}:
            require(status['financial_reference_date']=='2026-06-30' and status['current_post_event_value_held'] is True,'older dated/current hold lost')
    if deep:
        require({p.name for p in Path(root).iterdir()}==ROOT_FILES,'exact admitted child root files')
        require({p.name for p in (Path(root)/'artifacts').iterdir()}=={e['ticker']+'.json' for e in parent['entries']},'child artifact membership')
        require({p.name for p in (Path(root)/'recipes').iterdir()}=={t+'.json' for t in parent['private_recipe_sha256']},'child recipe membership')
        require((Path(root)/'refresh-policies.json').read_bytes()==(nested/'refresh-policies.json').read_bytes(),'child exact policy bytes')
        expected={str(p.relative_to(root)):sha(p.read_bytes()) for p in Path(root).rglob('*') if p.is_file() and p!=Path(root)/'manifest.json' and not str(p.relative_to(root)).startswith(('artifacts/','recipes/'))}
        require(manifest['preserved_prior_estimate_sha256']==expected,'actual copied admitted-proof index')
        for e in parent['entries']:stage.proof(root,'artifacts/'+e['ticker']+'.json',e['artifact_sha256'],proof_reader)
        for t,d in parent['private_recipe_sha256'].items():stage.proof(root,'recipes/'+t+'.json',d,proof_reader)
    return originals

def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader):
    validate(root,manifest,proof_reader=proof_reader)
    parent=stage.proof(root,'quality02-admitted-parent.json',manifest['approved_base_inheritance']['admitted_parent_manifest_sha256'],proof_reader)
    return admission.preserved_parent_artifact(Path(root)/'admission-parent',parent,ticker,raw,proof_reader=proof_reader)

def assemble(active,manifest,destination,rows,cutoff,*,copy_function=None):
    require(active.manifest.get('approved_base_inheritance',{}).get('schema_version')==admission.SCHEMA,'real admitted Quality02 parent required')
    require(not any(r['outcome']=='source_bound' for r in rows),'source-bound changes need separate source authority')
    from .approved_inheritance import _proof
    admission.validate(active.root,active.manifest,deep=True,proof_reader=_proof)
    destination=Path(destination);shutil.copytree(active.root,destination/'admission-parent',copy_function=copy_function or shutil.copy2)
    (destination/'quality02-admitted-parent.json').write_bytes((active.root/'manifest.json').read_bytes())
    receipt={'schema_version':'US-QUALITY02-ADMITTED-RETENTION-STATUS-1','parent_manifest_sha256':active.manifest_sha256,'cutoff':cutoff,'rows':rows,
        'counts':dict(Counter(r['outcome'] for r in rows)),'active_changed':False,'source_bound_recalculations':0}
    raw=canonical(receipt);(destination/'quality02-admitted-status.json').write_bytes(raw)
    manifest.pop('local_admission',None)
    manifest.update(approved_base_inheritance={'schema_version':SCHEMA,'admitted_parent_manifest_sha256':active.manifest_sha256,
        'quality_stage_manifest_sha256':admission.anchors()['stage_manifest_sha256'],'authorization_sha256':active.manifest['local_admission']['authorization_sha256'],
        'readiness_sha256':active.manifest['local_admission']['readiness_sha256']},base_catalog_version=active.manifest['base_catalog_version'],base_manifest_sha256=active.manifest['base_manifest_sha256'],
        refresh_parent_catalog_version=active.catalog_version,refresh_parent_manifest_sha256=active.manifest_sha256,staged_release_only=True,staged_read_only_review_ready=False,
        admission_prepared_only=True,admission=False,activation=False,publication=False,catalog_kind='unadmitted_quality02_admitted_retention_child',quality02_admitted_retention_receipt_sha256=sha(raw))
    manifest['preserved_prior_estimate_sha256']={str(p.relative_to(destination)):sha(p.read_bytes()) for p in destination.rglob('*') if p.is_file() and not str(p.relative_to(destination)).startswith(('artifacts/','recipes/'))}
