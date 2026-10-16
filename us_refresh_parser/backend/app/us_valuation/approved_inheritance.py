"""Authenticated approved-base inheritance and read-only admission review."""
from __future__ import annotations
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

BASE_SHA = "7f0ec0dc5f9489e9d22054a12b1ba91d553d9b982e8201acd6cf71cdc5d1fbcf"
STAGE_SHA = "0cd0e2ae6f2eb49e89a048ab37a621a6f9c1f2cd5ff524ce28cf7706ae418a34"
SCHEMA = "US-APPROVED-BASE-INHERITANCE-1"
REVIEW_SCHEMA = "US-READ-ONLY-ADMISSION-REVIEW-1"
NEW = {"AIT","MSM","WCC","SITE","WTS","FELE","GRC","MWA","KAI","MLI"}
ADMISSION_PREDECESSOR_SHA = "f5e36612f7e0a9a85b9769c4460d5b2ce6e658e77aa96bd3d5511816fec2fb56"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _file(root, name):
    root = Path(root)
    path = root / name
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("inheritance proof must be a regular in-root file")
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("inheritance path contains a symlink")
    return path.read_bytes()

@lru_cache(maxsize=32)
def _decoded_proof(raw):
    # Cache only by verified bytes, never by path/mtime. Every call still
    # re-reads and hashes the actual file, so mutation cannot use stale authority.
    return json.loads(raw)

def _proof(root, name, digest):
    raw = _file(root, name)
    if sha(raw) != digest:
        raise ValueError("inheritance proof hash mismatch: " + name)
    value = _decoded_proof(raw)
    if not isinstance(value, dict):
        raise ValueError("inheritance proof is not an object")
    return value

def _rows(manifest):
    return {e["ticker"]: (e["cik"],e["batch"],e["availability_type"],e["artifact_sha256"]) for e in manifest["entries"]}

def _local_admission(root, manifest):
    """Release authority is separate from the sealed preparation receipts."""
    grant = manifest.get('local_admission')
    staged = manifest.get('staged_release_only') is True or manifest.get('admission_prepared_only') is True
    if grant is None:
        if not staged:
            raise ValueError('explicit local admission authority missing')
        return
    if not isinstance(grant, dict) or grant.get('schema_version') != 'US-B01-LOCAL-ADMISSION-1':
        raise ValueError('local admission schema invalid')
    authorization = _proof(root, 'local-admission-authorization.json', grant['authorization_sha256'])
    predecessor = _proof(root, 'local-admission-predecessor.json', ADMISSION_PREDECESSOR_SHA)
    verification = _proof(root, 'local-admission-verification.json', grant['verification_sha256'])
    if (authorization.get('user_reply') != 'yes i authorize'
            or authorization.get('predecessor_manifest_sha256') != ADMISSION_PREDECESSOR_SHA
            or authorization.get('admission_authorized') is not True
            or authorization.get('local_activation_authorized') is not True
            or authorization.get('local_public_visibility_authorized') is not True
            or any(authorization.get(k) is not False for k in ('cloud_deployment','push','next_batch','new_recovery'))
            or set(authorization.get('public_numeric_additions', [])) != {'AIT','WCC','GRC'}
            or set(authorization.get('public_unavailable_additions', [])) != NEW-{'AIT','WCC','GRC'}
            or verification.get('manifest_sha256') != ADMISSION_PREDECESSOR_SHA
            or verification.get('status') != 'verified_pending_single_activation_decision'):
        raise ValueError('local admission authorization scope invalid')
    if not staged:
        if (manifest.get('catalog_kind') != 'admitted_local_expansion'
                or manifest.get('staged_release_only') is not False
                or manifest.get('admission_prepared_only') is not False
                or manifest.get('admission_predecessor_manifest_sha256') != ADMISSION_PREDECESSOR_SHA):
            raise ValueError('local admission baseline scope invalid')
        for key in ('entries','private_recipe_sha256','private_refresh_policy_sha256','supported_refresh_integration','availability_counts'):
            if manifest.get(key) != predecessor.get(key):
                raise ValueError('local admission changed approved baseline: '+key)

def _refresh_grant(root,manifest,stage):
    grant=manifest.get('supported_refresh_integration')
    if grant is None:
        return set()
    if not isinstance(grant,dict) or grant.get('schema_version')!='US-B01-SUPPORTED-REFRESH-INTEGRATION-1':
        raise ValueError('unsupported source-refresh grant')
    authorization=_proof(root,'refresh-integration-authorization.json',grant['authorization_sha256'])
    if authorization.get('supported_refresh_integration_authorized') is not True or set(authorization.get('public_supported_tickers',[]))!={'AIT','WCC','GRC'}:
        raise ValueError('supported refresh authorization scope invalid')
    if any(authorization.get(k) is not False for k in ('admission','activation','publication','new_recovery')):
        raise ValueError('refresh integration is not release or recovery authority')
    policies=_proof(root,'refresh-policies.json',manifest['private_refresh_policy_sha256'])
    prior=_proof(root,'confirmed-stage-policies.json',stage['private_refresh_policy_sha256'])
    enabled={'AIT','WCC','GRC'}
    if set(policies)!=set(prior) or any(policies[t]!=prior[t] for t in prior if t not in enabled):
        raise ValueError('unsupported/original policies changed outside integration scope')
    for t in enabled:
        policy=policies[t]
        if (policy.get('schema_version')!='FINSIGHT-B01-SUPPORTED-REFRESH-1'
                or policy.get('ticker')!=t or policy.get('cik')!=_rows(stage)[t][0]
                or policy.get('stage_only') is not True or policy.get('auto_revaluation') is not True
                or policy.get('reliability_cap')!='Low'
                or any(policy.get(k) is not False for k in ('admission_authorized','activation_authorized','publication_authorized'))):
            raise ValueError('supported refresh policy scope invalid')
        baseline=_proof(root,'confirmed-recipes/'+t+'.json',stage['private_recipe_sha256'][t])
        current=_proof(root,'recipes/'+t+'.json',manifest['private_recipe_sha256'][t])
        if any(current['scenarios'][s]['engine']!=baseline['scenarios'][s]['engine'] for s in ('bear','base','bull')):
            raise ValueError('supported refresh changed the approved model engine')
        locked=('cost_of_equity','terminal_roe','terminal_growth','years') if t!='AIT' else ('discount_rate','terminal_growth','net_bridge')
        if any(current['scenarios'][s]['inputs'][k]!=baseline['scenarios'][s]['inputs'][k] for s in ('bear','base','bull') for k in locked):
            raise ValueError('supported refresh changed locked forecasting assumptions')
        old=_rows(stage)[t][3]
        new=_rows(manifest)[t][3]
        if old!=new:
            digest=manifest.get('source_binding_sha256',{}).get(t)
            if not digest:
                raise ValueError('updated addition lacks a source binding proof')
            ledger=_proof(root,'source-bindings/'+t+'.json',digest)
            artifact=_proof(root,'artifacts/'+t+'.json',new)
            if (ledger.get('ticker')!=t or str(ledger.get('cik')).zfill(10)!=policy['cik']
                    or ledger.get('policy_version')!=policy['version']
                    or ledger.get('gate',{}).get('ready') is not True or not ledger.get('source_facts')
                    or ledger.get('table_audit',{}).get('exceptions')!=[]):
                raise ValueError('updated addition source/model gate is not evidenced')
            from .calculation_recipe import evaluate_recipe
            replay=evaluate_recipe(current)['range']
            if any(replay[k]!=artifact['scenario_range'][k] for k in ('low','base','high')):
                raise ValueError('updated source recipe/result differs')
    return enabled

def validate_inheritance(root, manifest, *, deep=False):
    if manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-B1620-ADMITTED-RETENTION-CHILD-1'}:
        from .admitted_batches1620 import validate
        return validate(root, manifest, deep=deep, proof_reader=_proof)
    proof = manifest.get("approved_base_inheritance")
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY06-OFFLINE-RETENTION-CHILD-1':
        from .quality06_retention import validate as validate_quality06_child
        return validate_quality06_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY06-STAGED-INHERITANCE-1':
        from .quality06_staged import validate as validate_quality06
        return validate_quality06(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY06-ADMITTED-RETENTION-CHILD-1':
        from .quality06_admitted_retention import validate as validate_quality06_admitted_child
        return validate_quality06_admitted_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY05-ADMITTED-RETENTION-CHILD-1':
        from .quality05_admitted_retention import validate as validate_quality05_admitted_child
        return validate_quality05_admitted_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality06_admission import validate as validate_quality06_admitted
        return validate_quality06_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality05_admission import validate as validate_quality05_admitted
        return validate_quality05_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY05-OFFLINE-RETENTION-CHILD-1':
        from .quality05_retention import validate as validate_quality05_child
        return validate_quality05_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY05-STAGED-INHERITANCE-1':
        from .quality05_staged import validate as validate_quality05
        return validate_quality05(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY04-ADMITTED-RETENTION-CHILD-1':
        from .quality04_admitted_retention import validate as validate_quality04_admitted_child
        return validate_quality04_admitted_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality04_admission import validate as validate_quality04_admitted
        return validate_quality04_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY04-OFFLINE-RETENTION-CHILD-1':
        from .quality04_retention import validate as validate_quality04_child
        return validate_quality04_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY04-STAGED-INHERITANCE-1':
        from .quality04_staged import validate as validate_quality04
        return validate_quality04(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality03_admission import validate
        return validate(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY03-ADMITTED-RETENTION-CHILD-1':
        from .quality03_admitted_retention import validate
        return validate(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY03-STAGED-INHERITANCE-1':
        from .quality03_staged import validate as validate_quality03
        return validate_quality03(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY03-OFFLINE-RETENTION-CHILD-1':
        from .quality03_retention import validate as validate_quality03_child
        return validate_quality03_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY02-ADMITTED-RETENTION-CHILD-1':
        from .quality02_admitted_retention import validate as validate_quality02_admitted_child
        return validate_quality02_admitted_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality02_admission import validate as validate_quality02_admitted
        return validate_quality02_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY02-OFFLINE-RETENTION-CHILD-1':
        from .quality02_retention import validate as validate_quality02_child
        return validate_quality02_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-QUALITY02-STAGED-INHERITANCE-1':
        from .quality02_staged import validate as validate_quality02
        return validate_quality02(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-B1115-QUALITY-ADMITTED-RETENTION-CHILD-1':
        from .quality_batches1115_admitted_retention import validate as validate_quality_admitted_child
        return validate_quality_admitted_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-B1115-QUALITY-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality_batches1115_admission import validate as validate_quality_admitted
        return validate_quality_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-B1115-QUALITY-RETENTION-CHILD-1':
        from .quality_batches1115_retention import validate as validate_quality_child
        return validate_quality_child(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-B1115-QUALITY-STAGED-INHERITANCE-1':
        from .quality_batches1115_staged import validate as validate_quality
        return validate_quality(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-B11-B15-LOCAL-ADMISSION-INHERITANCE-1':
        from .admitted_batches1115_inheritance import validate as validate_batches1115_admitted
        return validate_batches1115_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-B11-B15-APPROVED-PARENT-INHERITANCE-1':
        from .staged_batches1115_inheritance import validate as validate_batches1115
        return validate_batches1115(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-B06-B10-LOCAL-ADMISSION-INHERITANCE-1':
        from .admitted_batches0610_inheritance import validate as validate_batches0610_admitted
        return validate_batches0610_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version') == 'US-B06-B10-APPROVED-PARENT-INHERITANCE-1':
        from .staged_batches0610_inheritance import validate as validate_batches0610
        return validate_batches0610(root,manifest,deep=deep,proof_reader=_proof)
    from .staged_batch05_inheritance import SCHEMA as B05_SCHEMA, validate as validate_batch05
    from .admitted_batch05_inheritance import SCHEMA as B05_ADMITTED, validate as validate_batch05_admitted
    from .staged_batch04_inheritance import SCHEMA as B04_SCHEMA, validate as validate_batch04
    from .admitted_batch04_inheritance import SCHEMA as B04_ADMITTED, validate as validate_batch04_admitted
    from .admitted_batch03_inheritance import SCHEMA as B03_ADMITTED, validate as validate_batch03_admitted
    from .staged_batch03_inheritance import SCHEMA as B03_SCHEMA, validate as validate_batch03
    from .admitted_batch02_inheritance import SCHEMA as B02_ADMITTED,validate as validate_batch02_admitted
    if isinstance(proof,dict) and proof.get('schema_version')==B05_SCHEMA:
        return validate_batch05(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version')==B05_ADMITTED:
        return validate_batch05_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version')==B04_SCHEMA:
        return validate_batch04(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version')==B04_ADMITTED:
        return validate_batch04_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version')==B02_ADMITTED:
        return validate_batch02_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version')==B03_ADMITTED:
        return validate_batch03_admitted(root,manifest,deep=deep,proof_reader=_proof)
    if isinstance(proof,dict) and proof.get('schema_version')==B03_SCHEMA:
        return validate_batch03(root,manifest,deep=deep,proof_reader=_proof)
    from .staged_batch02_inheritance import SCHEMA as B02_SCHEMA,validate as validate_batch02
    if isinstance(proof,dict) and proof.get('schema_version')==B02_SCHEMA:
        return validate_batch02(root,manifest,deep=deep,proof_reader=_proof)
    if not isinstance(proof, dict) or proof.get("schema_version") != SCHEMA:
        raise ValueError("approved-base inheritance authority missing")
    if proof.get("base_manifest_sha256") != BASE_SHA or proof.get("confirmed_stage_manifest_sha256") != STAGE_SHA:
        raise ValueError("inheritance is not rooted in the authenticated approved catalogs")
    if manifest.get("private_integration_only") is True or "private_review" in manifest:
        raise ValueError("private integration cannot inherit public authority")
    _local_admission(root, manifest)
    base = _proof(root, "approved-base-manifest.json", BASE_SHA)
    stage = _proof(root, "confirmed-stage-manifest.json", STAGE_SHA)
    confirmation = _proof(root, "confirmed-stage-confirmation.json", proof["stage_confirmation_sha256"])
    authorization = _proof(root, "admission-preparation-authorization.json", proof["preparation_authorization_sha256"])
    if confirmation.get("manifest_sha256") != STAGE_SHA or confirmation.get("confirmed_scope") != "sealed_staged_public_candidate_only":
        raise ValueError("staged confirmation scope mismatch")
    if authorization.get("successor_preparation_authorized") is not True or authorization.get("confirmed_stage_manifest_sha256") != STAGE_SHA:
        raise ValueError("successor preparation scope mismatch")
    for record in (authorization,):
        if any(record.get(k) is not False for k in ("admission","activation","publication","automatic_new_source_revaluation")):
            raise ValueError("preparation receipt is not a release authorization")
    current, originals, approved = _rows(manifest), _rows(base), _rows(stage)
    refresh_enabled=_refresh_grant(root,manifest,stage)
    if len(originals) != 500 or len(current) != 510 or set(current) != set(approved) or set(current)-set(originals) != NEW:
        raise ValueError("inheritance exact identity scope mismatch")
    if any(current[t][:2] != approved[t][:2] for t in current):
        raise ValueError("inheritance issuer/status identity changed")
    if any(current[t] != approved[t] for t in NEW-refresh_enabled):
        raise ValueError("held additions' approved artifact pins changed")
    index, stage_index = manifest.get("private_recipe_sha256"), stage["private_recipe_sha256"]
    required = {t for t,e in current.items() if e[2] != "not_available"}
    if not isinstance(index, dict) or set(index) != required:
        raise ValueError("inheritance recipe membership changed")
    for t in NEW:
        if t not in refresh_enabled and index.get(t) != stage_index.get(t):
            raise ValueError("held addition recipe changed")
    # A future legitimate source-bound update to an ORIGINAL issuer does not
    # inherit its old raw approval. It must use the ordinary public projection.
    # Unchanged artifacts cannot silently acquire different private recipes.
    for t,e in originals.items():
        if current[t][3] == e[3] and (current[t][2] != e[2] or index.get(t) != stage_index.get(t)):
            raise ValueError("unchanged approved original acquired a changed status/recipe")
    if not refresh_enabled and manifest.get("private_refresh_policy_sha256") != stage.get("private_refresh_policy_sha256"):
        raise ValueError("prepared inheritance new-filing policies changed")
    if deep:
        allowed = {'artifacts','recipes','manifest.json','refresh-policies.json','approved-base-manifest.json',
            'confirmed-stage-manifest.json','confirmed-stage-confirmation.json','admission-preparation-authorization.json',
            'assembly-report.json','assembly-report.md'}
        if refresh_enabled:
            allowed|={'refresh-integration-authorization.json','confirmed-stage-policies.json','confirmed-recipes','source-bindings','prior-estimates'}
        if manifest.get('local_admission'):
            allowed|={'local-admission-authorization.json','local-admission-predecessor.json','local-admission-verification.json'}
        if {p.name for p in Path(root).iterdir()} - allowed:
            raise ValueError('inheritance catalog contains unexpected root files')
        actual = {p.name for p in (Path(root)/"artifacts").iterdir()}
        if actual != {t+".json" for t in current}:
            raise ValueError("inheritance artifact file membership differs")
        for t, e in current.items():
            if sha(_file(root, "artifacts/"+t+".json")) != e[3]:
                raise ValueError("inheritance artifact changed: " + t)
        index = manifest["private_recipe_sha256"]
        if {p.name for p in (Path(root)/"recipes").iterdir()} != {t+".json" for t in index}:
            raise ValueError("inheritance recipe file membership differs")
        for t, digest in index.items():
            if sha(_file(root, "recipes/"+t+".json")) != digest:
                raise ValueError("inheritance recipe changed: " + t)
        if sha(_file(root, "refresh-policies.json")) != manifest["private_refresh_policy_sha256"]:
            raise ValueError("inheritance hold policies changed")
    return originals

def preserved_original(root, manifest, ticker, raw, *, proof_reader=None):
    if manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-B1620-ADMITTED-RETENTION-CHILD-1'}:
        from .admitted_batches1620 import preserved_parent_artifact
        return preserved_parent_artifact(root, manifest, ticker, raw, proof_reader=proof_reader or _proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY06-OFFLINE-RETENTION-CHILD-1':
        from .quality06_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY06-STAGED-INHERITANCE-1':
        from .quality06_staged import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=proof_reader or _proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY06-ADMITTED-RETENTION-CHILD-1':
        from .quality06_admitted_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY05-ADMITTED-RETENTION-CHILD-1':
        from .quality05_admitted_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY06-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality06_admission import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY05-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality05_admission import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY05-OFFLINE-RETENTION-CHILD-1':
        from .quality05_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY05-STAGED-INHERITANCE-1':
        from .quality05_staged import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=proof_reader or _proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY04-ADMITTED-RETENTION-CHILD-1':
        from .quality04_admitted_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY04-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality04_admission import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY04-OFFLINE-RETENTION-CHILD-1':
        from .quality04_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY04-STAGED-INHERITANCE-1':
        from .quality04_staged import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=proof_reader or _proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY03-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality03_admission import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY03-ADMITTED-RETENTION-CHILD-1':
        from .quality03_admitted_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if "approved_base_inheritance" not in manifest:
        return False
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY03-STAGED-INHERITANCE-1':
        from .quality03_staged import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY03-OFFLINE-RETENTION-CHILD-1':
        from .quality03_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-ADMITTED-RETENTION-CHILD-1':
        from .quality02_admitted_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality02_admission import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-OFFLINE-RETENTION-CHILD-1':
        from .quality02_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-STAGED-INHERITANCE-1':
        from .quality02_staged import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-B1115-QUALITY-ADMITTED-RETENTION-CHILD-1':
        from .quality_batches1115_admitted_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-B1115-QUALITY-LOCAL-ADMISSION-INHERITANCE-1':
        from .quality_batches1115_admission import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-B1115-QUALITY-RETENTION-CHILD-1':
        from .quality_batches1115_retention import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-B1115-QUALITY-STAGED-INHERITANCE-1':
        from .quality_batches1115_staged import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-B11-B15-LOCAL-ADMISSION-INHERITANCE-1':
        from .admitted_batches1115_inheritance import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-B11-B15-APPROVED-PARENT-INHERITANCE-1':
        from .staged_batches1115_inheritance import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get("approved_base_inheritance",{}).get("schema_version") == "US-B06-B10-LOCAL-ADMISSION-INHERITANCE-1":
        from .admitted_batches0610_inheritance import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    if manifest.get("approved_base_inheritance",{}).get("schema_version") == "US-B06-B10-APPROVED-PARENT-INHERITANCE-1":
        from .staged_batches0610_inheritance import preserved_parent_artifact
        return preserved_parent_artifact(root,manifest,ticker,raw,proof_reader=_proof)
    originals = validate_inheritance(root, manifest)
    if ticker not in originals:
        return False
    current = _rows(manifest)[ticker]
    if sha(raw) != current[3]:
        raise ValueError("declared original artifact bytes changed")
    if current[3] != originals[ticker][3]:
        return False
    return True

def review_selection():
    selected = os.environ.get("FINSIGHT_US_REVIEW_CATALOG_ROOT")
    authority_path = os.environ.get("FINSIGHT_US_REVIEW_AUTHORITY_PATH")
    digest = os.environ.get("FINSIGHT_US_REVIEW_AUTHORITY_SHA256")
    if not any((selected, authority_path, digest)):
        return None
    if not all((selected, authority_path, digest)):
        raise ValueError("review root, authority and digest are all required")
    incompatible = ("FINSIGHT_US_VALUATION_CATALOG_ROOT","FINSIGHT_US_REFRESH_ROOT",
        "FINSIGHT_US_PREVIEW_CATALOG_ROOT","FINSIGHT_US_PREVIEW_BASELINE_ROOT",
        "FINSIGHT_US_VALUATION_DATA_ROOT","FINSIGHT_US_EOD_DATA_ROOT",
        "FINSIGHT_US_SECURITY_MASTER_ROOT","FINSIGHT_US_RECIPE_ROOT")
    if any(os.environ.get(k) for k in incompatible):
        raise ValueError("read-only review cannot select active/runtime/price roots")
    root, authority_file = Path(selected), Path(authority_path)
    if root.is_symlink() or authority_file.is_symlink():
        raise ValueError("review root/authority cannot be symlinked")
    raw = authority_file.read_bytes()
    if sha(raw) != digest:
        raise ValueError("review authority digest mismatch")
    authority = json.loads(raw)
    manifest_raw = _file(root, "manifest.json")
    manifest = json.loads(manifest_raw)
    if authority.get('schema_version') == 'US-QUALITY03-STAGED-READ-ONLY-1':
        from .quality03_staged import review_selection as quality03_review_selection
        return quality03_review_selection(root,authority_file,authority,manifest,sha(manifest_raw),proof_reader=_proof)
    if authority.get('schema_version') == 'US-QUALITY02-STAGED-READ-ONLY-1':
        from .quality02_staged import review_selection as quality02_review_selection
        return quality02_review_selection(root,authority_file,authority,manifest,sha(manifest_raw),proof_reader=_proof)
    if authority.get('schema_version') == 'US-B1115-QUALITY-STAGED-READ-ONLY-1':
        from .quality_batches1115_staged import review_selection as quality_review_selection
        return quality_review_selection(root,authority_file,authority,manifest,sha(manifest_raw),proof_reader=_proof)
    if authority.get('schema_version') == 'US-B11-B15-READ-ONLY-STAGED-REVIEW-1':
        from .staged_batches1115_inheritance import AUTHORITY_FIELDS as B1115_FIELDS, validate_registry as validate_batches1115_registry
        if set(authority) != B1115_FIELDS or authority.get('read_only') is not True:
            raise ValueError('Batches11-15 staged review authority exact fields/read-only required')
        if any(authority.get(k) is not False for k in ('admission','activation','publication','save','automatic_new_source_revaluation')):
            raise ValueError('Batches11-15 staged review authority permits a prohibited action')
        if authority.get('manifest_sha256') != sha(manifest_raw) or authority.get('catalog_version') != manifest.get('catalog_version'):
            raise ValueError('Batches11-15 staged review authority does not bind the current manifest')
        if manifest.get('staged_release_only') is not True or manifest.get('staged_read_only_review_ready') is not True:
            raise ValueError('Batches11-15 review must select an unadmitted staged successor')
        validate_inheritance(root,manifest,deep=True)
        registry_raw = _file(authority_file.parent,'runtime/registry.json')
        registry = json.loads(registry_raw)
        if sha(registry_raw) != authority.get('registry_sha256') or registry.get('baseline_manifest_sha256') != sha(manifest_raw):
            raise ValueError('Batches11-15 review registry pin mismatch')
        if registry.get('baseline_catalog_version') != manifest.get('catalog_version'):
            raise ValueError('Batches11-15 review registry version mismatch')
        validate_batches1115_registry(root,manifest,registry,proof_reader=_proof)
        return root,authority['manifest_sha256']
    if authority.get('schema_version') == 'US-B06-B10-READ-ONLY-STAGED-REVIEW-1':
        from .staged_batches0610_inheritance import AUTHORITY_FIELDS as B0610_FIELDS, validate_registry as validate_batches0610_registry
        if set(authority) != B0610_FIELDS or authority.get('read_only') is not True:
            raise ValueError('Batches06-10 staged review authority exact fields/read-only required')
        if any(authority.get(k) is not False for k in ('admission','activation','publication','save','automatic_new_source_revaluation')):
            raise ValueError('Batches06-10 staged review authority permits a prohibited action')
        if authority.get('manifest_sha256') != sha(manifest_raw) or authority.get('catalog_version') != manifest.get('catalog_version'):
            raise ValueError('Batches06-10 staged review authority does not bind the current manifest')
        if manifest.get('staged_release_only') is not True or manifest.get('staged_read_only_review_ready') is not True:
            raise ValueError('Batches06-10 review must select an unadmitted staged successor')
        validate_inheritance(root,manifest,deep=True)
        registry_raw = _file(authority_file.parent,'runtime/registry.json')
        registry = json.loads(registry_raw)
        if sha(registry_raw) != authority.get('registry_sha256') or registry.get('baseline_manifest_sha256') != sha(manifest_raw):
            raise ValueError('Batches06-10 review registry pin mismatch')
        if registry.get('baseline_catalog_version') != manifest.get('catalog_version'):
            raise ValueError('Batches06-10 review registry version mismatch')
        validate_batches0610_registry(root,manifest,registry,proof_reader=_proof)
        return root,authority['manifest_sha256']
    if authority.get('schema_version') == 'US-B1620-STAGED700-READ-ONLY-1':
        from .staged_batches1620 import validate_review_selection
        return validate_review_selection(root, authority_file, authority, manifest, sha(manifest_raw))
    if authority.get('schema_version') == 'US-B16-B20-PRIVATE700-READ-ONLY-REVIEW-1':
        from .private_batches1620 import validate_review_selection
        return validate_review_selection(root, authority_file, authority, manifest, sha(manifest_raw))
    if authority.get('schema_version') == 'US-B11-B15-PRIVATE650-READ-ONLY-REVIEW-1':
        from .private_batches1115 import validate_review_selection
        return validate_review_selection(root, authority_file, authority, manifest, sha(manifest_raw))
    if authority.get('schema_version') == 'US-B06-B10-PRIVATE600-READ-ONLY-REVIEW-1':
        from .private_batches0610 import validate_review_selection
        return validate_review_selection(root, authority_file, authority, manifest, sha(manifest_raw))
    from .staged_batch02_inheritance import REVIEW_SCHEMA as B02_REVIEW,AUTHORITY_FIELDS,validate_registry
    from .quality04_staged import REVIEW_SCHEMA as Q04_REVIEW,AUTHORITY_FIELDS as Q04_AUTHORITY_FIELDS,review_selection as quality04_review_selection
    from .quality05_staged import REVIEW_SCHEMA as Q05_REVIEW,AUTHORITY_FIELDS as Q05_AUTHORITY_FIELDS,review_selection as quality05_review_selection
    from .quality06_staged import REVIEW_SCHEMA as Q06_REVIEW,AUTHORITY_FIELDS as Q06_AUTHORITY_FIELDS,review_selection as quality06_review_selection
    from .staged_batch03_inheritance import REVIEW_SCHEMA as B03_REVIEW,AUTHORITY_FIELDS as B03_AUTHORITY_FIELDS,validate_registry as validate_batch03_registry
    from .staged_batch04_inheritance import REVIEW_SCHEMA as B04_REVIEW,AUTHORITY_FIELDS as B04_AUTHORITY_FIELDS,validate_registry as validate_batch04_registry
    from .staged_batch05_inheritance import REVIEW_SCHEMA as B05_REVIEW,AUTHORITY_FIELDS as B05_AUTHORITY_FIELDS,validate_registry as validate_batch05_registry
    batch02=authority.get('schema_version')==B02_REVIEW
    if authority.get('schema_version') == Q04_REVIEW:
        return quality04_review_selection(root,authority_file,authority,manifest,sha(manifest_raw),proof_reader=_proof)
    if authority.get('schema_version') == Q05_REVIEW:
        return quality05_review_selection(root,authority_file,authority,manifest,sha(manifest_raw),proof_reader=_proof)
    if authority.get('schema_version') == Q06_REVIEW:
        return quality06_review_selection(root,authority_file,authority,manifest,sha(manifest_raw),proof_reader=_proof)
    batch03=authority.get('schema_version')==B03_REVIEW
    batch04=authority.get('schema_version')==B04_REVIEW
    batch05=authority.get('schema_version')==B05_REVIEW
    if batch02 and set(authority)!=AUTHORITY_FIELDS:
        raise ValueError('Batch02 review authority exact fields required')
    if batch03 and set(authority)!=B03_AUTHORITY_FIELDS:
        raise ValueError('Batch03 review authority exact fields required')
    if batch04 and set(authority)!=B04_AUTHORITY_FIELDS:
        raise ValueError('Batch04 review authority exact fields required')
    if batch05 and set(authority)!=B05_AUTHORITY_FIELDS:
        raise ValueError('Batch05 review authority exact fields required')
    if authority.get("schema_version") not in {REVIEW_SCHEMA,B02_REVIEW,B03_REVIEW,B04_REVIEW,B05_REVIEW} or authority.get("read_only") is not True:
        raise ValueError("review authority schema/read-only scope invalid")
    if any(authority.get(k) is not False for k in ("admission","activation","publication","save","automatic_new_source_revaluation")):
        raise ValueError("review authority permits a prohibited action")
    if authority.get("manifest_sha256") != sha(manifest_raw) or authority.get("catalog_version") != manifest.get("catalog_version"):
        raise ValueError("review authority does not bind this manifest")
    prepared=manifest.get('staged_read_only_review_ready') is True if (batch02 or batch03 or batch04 or batch05) else manifest.get('admission_prepared_only') is True
    if manifest.get("staged_release_only") is not True or not prepared:
        raise ValueError("review must select an unadmitted prepared successor")
    validate_inheritance(root, manifest, deep=True)
    registry_raw = _file(authority_file.parent, "runtime/registry.json")
    registry = json.loads(registry_raw)
    if sha(registry_raw) != authority.get("registry_sha256") or registry.get("baseline_manifest_sha256") != sha(manifest_raw):
        raise ValueError("review registry pin mismatch")
    if registry.get("baseline_catalog_version") != manifest["catalog_version"]:
        raise ValueError("review registry version mismatch")
    wanted = {(e["ticker"],e["cik"],e["batch"]) for e in manifest["entries"]}
    actual = {(e["ticker"],str(e["cik"]).zfill(10),e["batch"]) for e in registry["entries"]}
    if actual != wanted or len(registry["entries"]) != (550 if batch05 else 540 if batch04 else 530 if batch03 else 520 if batch02 else 510):
        raise ValueError("review registry identities differ")
    if batch02:
        validate_registry(root,manifest,registry,proof_reader=_proof)
    if batch03:
        validate_batch03_registry(root,manifest,registry,proof_reader=_proof)
    if batch04:
        validate_batch04_registry(root,manifest,registry,proof_reader=_proof)
    if batch05:
        validate_batch05_registry(root,manifest,registry,proof_reader=_proof)
    return root, authority["manifest_sha256"]
