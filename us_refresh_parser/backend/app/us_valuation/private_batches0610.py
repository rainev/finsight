"""Closed frozen B06-B10 private600 profile; never public or automatic refresh authority."""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
from .catalog import canonical_json_bytes, sha256_bytes
from .artifacts import sanitize_public_artifact

# Metadata-only normalization of confirmed private recovery outputs. No new economics.
ANCHORS = {
    "approval_sha256": "879cef58d98b73063dcc88a3dde802b8d46e5df663005fd6164ed205e3e47096",
    "approved_artifact_sha256": {
        "AAON": "ad0d1a32ed6dc6b52131399da83b9ae6e757c6d2f723585c47999af3430d7f33",
        "ACHC": "77aaf00fa26d521dd0a3d4ab359f9d82157ba1b8baac1dfe1025490131bb68ed",
        "AEO": "80232fc5533aa5521d7aba842d3bc569032657cd1c9a57b983d4bb368d9d465d",
        "AMPH": "790b017dbe982b41de51d202d40e467be35a2f5267ee33eba8c10372bfdf4cc3",
        "ANF": "a3496953887cba39c4f214d6fe0d881af0049988e315161a30e7ef69e5f0aaf5",
        "ASO": "9db12ef157bd5fb1d3584573bab39c5a6edea8e8851f7b0ba0d1362af1c1cd80",
        "ATI": "7c553e8db1140f26b1e3fc39b32163214d6e29260aab1769bf169a36606e17c2",
        "ATKR": "fb30b12b1adfe59f27fd535a3c7414914602b80124bd929cbd8c3fe6b043ebe3",
        "BKE": "85eb628c0176dc8ceac8212b795f993ab4417f81a34692f249f201d39a82cfc6",
        "BWXT": "d5cf8c890c55868a6d4bcc378cc492fd3d1fd7f4bb1ea6b781b2e9e2bbd8878e",
        "CACI": "16b57fcebf669286d26f71b39b438576d40948472d21be5d4ef21a21bba15076",
        "CCK": "20d5a622acb28762ccd2c59efea1ff7c70b4109817315b5125f6fe239a793208",
        "CMC": "d0daf5c26ee76f591c57426b27a3293008fb054c05d82d930763a0f7fa5350c9",
        "CNMD": "7464c208c00bfa8edc29f10bf29891243665c43db0b4cf4ac58700591664f4d6",
        "COLM": "3773b8b1ef2a564a6dc6d846a72e7b806ed02916fe3a3467eb208ea23c4ed054",
        "CROX": "0f881f463603f7c2d2674af4d24ca9d5da354a701a3d98080a41b972dcd87c64",
        "CVLT": "edcaa9f4656ee1b47cd37c9ee4813a18a8bb783104104886a56b23bd637f22af",
        "DCI": "5995812c418118815c1b86c16fb54e1c912f47fb96657f181736720fcfa11c12",
        "EHC": "3625b273f6429050fc80bd1d184af37306478e2d946a707dbcf53ab1f630c03b",
        "ELF": "9802bb2be5232abb5f250107e5ac2dc6b1f102953b5ce0130d161253c54530f9",
        "EXP": "958cb426b74f6a69222053bff4b6fb7f13313a4cc59127050d1755a3bcaa3294",
        "EXPO": "7209dab8b5d340718792d499739a1e0f238f5769142f1ef8f58bdf83ea10ea81",
        "GFF": "374562a9dbbfa0ac55956bee26f4d26fd207a4de90622a25d37ca776ae661a1c",
        "HALO": "3de88678fa203d94d31293347387d840244721707192d2d169246f1c77a4ccb3",
        "HNI": "67debbdd089e302b39ee675fa97dcb027b7211c55f819558896addfd9fa47b17",
        "HXL": "dc4206aecd1b159557c6e71f0c5f8b507cdc1d79ff44d4c472ea5f7acd1260b0",
        "KBR": "2f16b13d9474a3cc23c9de56e7e668da8681d35b66ed084b1917489bbeeded23",
        "LNTH": "b0c4e876ec40d7e33ee7bb068ce7e022bbaf49788548e7ff256e2a33336b9c91",
        "MATX": "430f90b6381bc631cb66b1e0ff456e792d6752463a615c0a755ce17f4947173d",
        "MMSI": "b73feb7b1cf7b7b5668f872faa3888ea6fc38eab1d82ef786ed490939d88a5d2",
        "MSA": "be716b0f210ebae994fcbf248a5ed89a9bdd00fcd8e6b1deefd51f586f974494",
        "MYRG": "aa7df3966a069373ff199437cc31a01efd12026423cfd53705e1c4344e20c7e5",
        "NHC": "b1e7adcaa67b8c2993e07c759bd93b37f61bfe3d29e2d3b551f0e1f253aad25c",
        "OLN": "e290da9b119f0e51f5945e29f20c8000aeff2a162722fe4880791ae489495ba6",
        "OMCL": "2003d8bd2263a7f69859d64a71f266588b8d74f6b17924d996758b6a50b96285",
        "PCTY": "1b56c1910796ce45f757c9698071bd50ba8c5bc3e1d18eefa28e36235d476dc7",
        "PEGA": "5d1e14298c29dac207023818b70f4ecd9c8dd203d81d705d03a75416c6b83510",
        "PLXS": "ffcc6d2a65dc1dd28645f533a1503eacd97f09555a76a09909912d871b1b0c28",
        "PNTG": "d72caa637bed90d8f04d1c9f6adecee6ad1345a36fe8cd51d0c43c3fab641d1c",
        "PRIM": "0779263241210114f0bdb6c67eef53f908c828a9b9b58e1f2bbf55c5f769f497",
        "RHI": "50ef50b377c686952befbd2249538a765973e05761183813edd763f3fab5a599",
        "SAIC": "f359dbbbc2d4f7316c3c429d224724bc450fb12b4a73e000e27b8389c7307109",
        "SANM": "7cb3443b2745f8782fc27cebd319f4a58c92de2145ad5c2c8c4c4d0d85891b9e",
        "SON": "2d9720dd0b54578f29e8b7c9770d611a363f4a54b5a2b3b6f944b0061711bd57",
        "SPSC": "baf988591873f5f308abab94186bb020a48f591c9740a4d9ae09dc7afb95aabe",
        "STRL": "8bf53785e2e234d590bb39fb39778398766ad0aba295393b0c12f154025ad505",
        "TREX": "aa0a7d1099a599d045c11b78f9d72a1f2f6bd068231758a1752da839a9df98bf",
        "TXRH": "8dfcab68082108c8c7ade57b20add663965fd97bfb81c0563990e2c544508c6e",
        "URBN": "b6e6f4855c4ed61b189a01716d90da4c357320e3c854a3242881be48883f1a95",
        "VMI": "feb1e533786eb16c2f1c3f7ed23aeaea4312630c94247236cc8b0be37f7b5a41"
    },
    "base_catalog_version": "US-ADMITTED-B05-550-3dfe024c73c64013f29aa12f",
    "base_manifest_sha256": "cb5376c2516dae4dddb90d7054df7bc22d173cc6e3c3dde926a76df0cb3338b0",
    "catalog_batches": {
        "AAON": 56,
        "ACHC": 60,
        "AEO": 58,
        "AMPH": 60,
        "ANF": 58,
        "ASO": 58,
        "ATI": 56,
        "ATKR": 57,
        "BKE": 58,
        "BWXT": 56,
        "CACI": 56,
        "CCK": 57,
        "CMC": 57,
        "CNMD": 60,
        "COLM": 58,
        "CROX": 58,
        "CVLT": 59,
        "DCI": 57,
        "EHC": 60,
        "ELF": 58,
        "EXP": 56,
        "EXPO": 59,
        "GFF": 56,
        "HALO": 60,
        "HNI": 58,
        "HXL": 57,
        "KBR": 59,
        "LNTH": 60,
        "MATX": 57,
        "MMSI": 60,
        "MSA": 56,
        "MYRG": 57,
        "NHC": 60,
        "OLN": 57,
        "OMCL": 60,
        "PCTY": 59,
        "PEGA": 59,
        "PLXS": 59,
        "PNTG": 60,
        "PRIM": 56,
        "RHI": 59,
        "SAIC": 59,
        "SANM": 59,
        "SON": 57,
        "SPSC": 59,
        "STRL": 56,
        "TREX": 56,
        "TXRH": 58,
        "URBN": 58,
        "VMI": 57
    },
    "frozen_ranges_sha256": "960222c439fcb244f61e1773ee19ec31c0bc725f8d50eee0f0309cbe0fc6bd64",
    "identities": {
        "AAON": "0000824142",
        "ACHC": "0001520697",
        "AEO": "0000919012",
        "AMPH": "0001297184",
        "ANF": "0001018840",
        "ASO": "0001817358",
        "ATI": "0001018963",
        "ATKR": "0001666138",
        "BKE": "0000885245",
        "BWXT": "0001486957",
        "CACI": "0000016058",
        "CCK": "0001219601",
        "CMC": "0000022444",
        "CNMD": "0000816956",
        "COLM": "0001050797",
        "CROX": "0001334036",
        "CVLT": "0001169561",
        "DCI": "0000029644",
        "EHC": "0000785161",
        "ELF": "0001600033",
        "EXP": "0000918646",
        "EXPO": "0000851520",
        "GFF": "0000050725",
        "HALO": "0001159036",
        "HNI": "0000048287",
        "HXL": "0000717605",
        "KBR": "0001357615",
        "LNTH": "0001521036",
        "MATX": "0000003453",
        "MMSI": "0000856982",
        "MSA": "0000066570",
        "MYRG": "0000700923",
        "NHC": "0001047335",
        "OLN": "0000074303",
        "OMCL": "0000926326",
        "PCTY": "0001591698",
        "PEGA": "0001013857",
        "PLXS": "0000785786",
        "PNTG": "0001766400",
        "PRIM": "0001361538",
        "RHI": "0000315213",
        "SAIC": "0001571123",
        "SANM": "0000897723",
        "SON": "0000091767",
        "SPSC": "0001092699",
        "STRL": "0000874238",
        "TREX": "0001069878",
        "TXRH": "0001289460",
        "URBN": "0000912615",
        "VMI": "0000102729"
    },
    "null_tickers": [
        "ACHC",
        "ATKR",
        "CCK",
        "EHC",
        "GFF",
        "MSA",
        "OLN",
        "SANM",
        "VMI"
    ],
    "numeric_tickers": [
        "AAON",
        "AEO",
        "AMPH",
        "ANF",
        "ASO",
        "ATI",
        "BKE",
        "BWXT",
        "CACI",
        "CMC",
        "CNMD",
        "COLM",
        "CROX",
        "CVLT",
        "DCI",
        "ELF",
        "EXP",
        "EXPO",
        "HALO",
        "HNI",
        "HXL",
        "KBR",
        "LNTH",
        "MATX",
        "MMSI",
        "MYRG",
        "NHC",
        "OMCL",
        "PCTY",
        "PEGA",
        "PLXS",
        "PNTG",
        "PRIM",
        "RHI",
        "SAIC",
        "SON",
        "SPSC",
        "STRL",
        "TREX",
        "TXRH",
        "URBN"
    ],
    "origin_summary_sha256": "dd69a3f6550d43512c6d71128d01728019869fa96da6d17bffa0139360832424",
    "recovery_confirmation_sha256": "5857ef32b327ffcdfa2989a5dfa63588c56e65a648e58c12bd40cd2bfe0f4112"
}
SCHEMA = 'FINSIGHT-PRIVATE-INTEGRATION-REVIEW-B06-B10-1'
PROFILE = 'B06-B10-FROZEN-PRIVATE-1'
REVIEW_SCHEMA = 'US-B06-B10-PRIVATE600-READ-ONLY-REVIEW-1'
CUTOFF = '2026-10-08'
ACCEPTANCE = '2026-10-07T17:04:01.759469+00:00'
IDENTITIES = ANCHORS['identities']
ARTIFACT_HASHES = ANCHORS['approved_artifact_sha256']
BATCHES = ANCHORS['catalog_batches']
NUMERIC = frozenset(ANCHORS['numeric_tickers'])
NULLS = frozenset(ANCHORS['null_tickers'])
BASE_REGISTRY_SHA = 'ba789fbdeb7edb636b52eb505894c642fcd30066101b4c8a42f5595388c56260'
BASE_POLICIES_SHA = '5285cee935c9774ccbd14a056dd75cbc492bc4a66fdee53fd5241ef65098bd48'
PRIVATE_BINDING_SHA = 'a047a23966c7ac5cb97fd9ba20bafcc78403942a916f60c387ae19905156b0b3'
ROOT_ENTITIES = frozenset({'artifacts','recipes','manifest.json','refresh-policies.json',
    'predecessor-provenance','integration-parent-manifest.json','integration-parent-registry.json',
    'integration-parent-refresh-policies.json','private600-preparation-authorization.json',
    'private-source-disclosure-binding.json'})
REVIEW_FIELDS = frozenset({'schema_version','profile','private_only','public_release_authorized',
    'auto_revaluation','cutoff','acceptance_cutoff_UTC','origin_summary_sha256','approval_sha256',
    'recovery_confirmation_sha256','approved_artifact_sha256','identities','frozen_ranges',
    'private_source_disclosure_binding_sha256'})
SELECTION_FIELDS = frozenset({'schema_version','source','read_only','private_only','catalog_version',
    'manifest_sha256','registry_sha256','refresh_policies_sha256','preparation_authority_sha256',
    'admission','activation','publication','save','automatic_new_source_revaluation','new_SEC_capture'})
PROHIBITED_GRANTS = frozenset({'approved_base_inheritance','approved_base_manifest_sha256',
    'local_admission','admission_predecessor_manifest_sha256','supported_refresh_integration',
    'release_scope_approval_sha256','confirmed_stage_catalog_version','confirmed_stage_manifest_sha256'})
NO_AUTHORITY = ('admission','activation','publication','public_release_authorized','auto_revaluation',
    'live_runtime_promotion','new_source_capture','new_live_refresh_job')
PREPARATION_FIELDS = frozenset({'schema_version','source','user_request','recorded_at_UTC','private_only',
    'baseline_count','candidate_count','catalog_batches','expansion_batches','evidence_cutoff',
    'acceptance_cutoff_UTC','origin_summary_sha256','recovery_confirmation_sha256','recovery_handoff_sha256',
    'preserve_old550_and_all_prior_private_values','new_numeric','new_withheld','admission','activation',
    'publication','live_runtime_promotion','new_source_capture','new_recovery','new_valuation_inputs',
    'new_live_refresh_job','next_batch','push','cloud_deployment','data_deletion'})
PREPARATION_FALSE = ('admission','activation','publication','live_runtime_promotion','new_source_capture',
    'new_recovery','new_valuation_inputs','new_live_refresh_job','next_batch','push','cloud_deployment','data_deletion')

def fail(why):
    raise ValueError('private review artifact rejected: B06-B10 ' + why)

def need(value, why):
    if not value:
        fail(why)

def validate_preparation(value):
    need(isinstance(value, dict) and set(value) == PREPARATION_FIELDS, 'preparation exact fields required')
    need(value['schema_version'] == 'US-B06-B10-PRIVATE600-PREPARATION-AUTHORITY-1'
         and value['source'] == 'direct_human_user', 'preparation authority source/schema changed')
    need(value['private_only'] is True and value['preserve_old550_and_all_prior_private_values'] is True,
         'private preservation authority changed')
    need(value['baseline_count'] == 550 and value['candidate_count'] == 600
         and value['catalog_batches'] == [56,57,58,59,60] and value['expansion_batches'] == [6,7,8,9,10]
         and value['new_numeric'] == 41 and value['new_withheld'] == 9, 'preparation scope/count changed')
    need(value['evidence_cutoff'] == CUTOFF and value['acceptance_cutoff_UTC'] == ACCEPTANCE,
         'preparation cutoff changed')
    need(value['origin_summary_sha256'] == ANCHORS['origin_summary_sha256']
         and value['recovery_confirmation_sha256'] == ANCHORS['recovery_confirmation_sha256']
         and value['recovery_handoff_sha256'] == '0a9f0b8abfc826fda3119710f2dc0e49461aeaa7744f442751e3748fb7c3de08',
         'confirmed recovery pin changed')
    need(all(value[key] is False for key in PREPARATION_FALSE), 'preparation authority widened')
    need(sha256_bytes(canonical_json_bytes(value)) == ANCHORS['approval_sha256'],
         'not the recorded direct-human preparation')
    return value

def validate_manifest(manifest):
    need(isinstance(manifest, dict) and manifest.get('private_integration_only') is True,
         'private integration flag absent')
    need(manifest.get('catalog_kind') == 'private_integration_only', 'catalog kind changed')
    need(all(manifest.get(key) is False for key in ('admission','activation','publication')),
         'explicitly false release authority required')
    need(not (PROHIBITED_GRANTS & set(manifest)), 'inherited release grant keys not permitted')
    need(all(manifest.get(key) is not True for key in NO_AUTHORITY), 'authority is not permitted')
    need(all(manifest.get(key) is not True for key in ('staged_release_only','staged_read_only_review_ready','admission_prepared_only')),
         'public staging/admission cannot be inferred')
    need(manifest.get('base_catalog_version') == ANCHORS['base_catalog_version'], 'base catalog version changed')
    need(manifest.get('base_manifest_sha256') == ANCHORS['base_manifest_sha256'], 'base manifest hash changed')
    preserved = manifest.get('preserved_prior_estimate_sha256')
    need(isinstance(preserved, dict) and preserved.get('integration-parent-manifest.json') == ANCHORS['base_manifest_sha256'],
         'parent manifest preservation pin changed')
    need(preserved.get('private-source-disclosure-binding.json') == PRIVATE_BINDING_SHA,
         'private disclosure preservation pin changed')
    review = manifest.get('private_review')
    need(isinstance(review, dict) and set(review) == REVIEW_FIELDS, 'review exact fields required')
    need(review['schema_version'] == SCHEMA and review['profile'] == PROFILE, 'profile/schema changed')
    need(review['private_only'] is True and review['public_release_authorized'] is False
         and review['auto_revaluation'] is False, 'private review authority widened')
    need(review['cutoff'] == CUTOFF and review['acceptance_cutoff_UTC'] == ACCEPTANCE, 'frozen cutoff changed')
    for key in ('origin_summary_sha256','approval_sha256','recovery_confirmation_sha256'):
        need(review[key] == ANCHORS[key], 'recorded ' + key + ' changed')
    need(review['private_source_disclosure_binding_sha256'] == PRIVATE_BINDING_SHA,
         'private source/disclosure hash changed')
    need(review['identities'] == IDENTITIES and review['approved_artifact_sha256'] == ARTIFACT_HASHES,
         'closed identity/artifact scope changed')
    ranges = review['frozen_ranges']
    need(isinstance(ranges, dict) and set(ranges) == set(IDENTITIES), 'exact50 frozen ranges required')
    for ticker, values in ranges.items():
        need(isinstance(values, dict) and set(values) == {'low','base','high'}, 'range fields changed')
        if ticker in NULLS:
            need(all(value is None for value in values.values()), 'held range became numeric')
        else:
            need(all(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
                     for value in values.values()), 'finite numeric range required')
            need(values['low'] <= values['base'] <= values['high'], 'unordered range')
    need(sha256_bytes(canonical_json_bytes(ranges)) == ANCHORS['frozen_ranges_sha256'], 'frozen ranges changed')
    if 'entries' in manifest:
        entries = manifest['entries']
        need(isinstance(entries, list) and len(entries) == len({r['ticker'] for r in entries}) == 600,
             'exact600 entries required')
        need(manifest.get('included_batches') == list(range(1,61)) and manifest.get('artifact_count') == 600,
             'catalog batch/count changed')
        need(Counter(r['availability_type'] for r in entries) == Counter({'available':116,'conditional_estimate':432,'not_available':52}),
             'admitted550-derived availability changed')
        indexed = {r['ticker']:r for r in entries}
        for ticker in IDENTITIES:
            row = indexed.get(ticker)
            need(row is not None and row['cik'] == IDENTITIES[ticker] and row['batch'] == BATCHES[ticker]
                 and row['artifact_sha256'] == ARTIFACT_HASHES[ticker]
                 and row['availability_type'] == ('conditional_estimate' if ticker in NUMERIC else 'not_available'),
                 'new current row changed: ' + ticker)
    return review

def project(artifact, manifest, *, ticker, artifact_sha256):
    review = validate_manifest(manifest)
    if ticker not in IDENTITIES:
        return sanitize_public_artifact(artifact if isinstance(artifact,dict) else {})
    from .private_integration import _walk_forbidden_keys
    _walk_forbidden_keys(artifact)
    need(isinstance(artifact,dict) and artifact_sha256 == ARTIFACT_HASHES[ticker]
         and sha256_bytes(canonical_json_bytes(artifact)) == ARTIFACT_HASHES[ticker],
         'approved artifact/source/date/warning bytes changed: ' + ticker)
    need(artifact.get('ticker') == ticker and artifact.get('issuer',{}).get('ticker') == ticker
         and artifact['issuer'].get('cik') == IDENTITIES[ticker], 'issuer identity changed')
    need(artifact.get('private_review_only') is True and artifact.get('valuation_date') == CUTOFF
         and artifact.get('assumption_date') == CUTOFF, 'private date/review scope changed')
    need(artifact.get('model_policy',{}).get('primary') == 'residual_income'
         and artifact['model_policy'].get('scope') == 'private_initial_review_not_admitted', 'model scope changed')
    need({key:artifact['scenario_range'][key] for key in ('low','base','high')} == review['frozen_ranges'][ticker],
         'artifact/frozen range differs')
    if ticker in NUMERIC:
        need(artifact['availability_type'] == 'conditional_estimate' and artifact['reliability']['label'] == 'Low'
             and artifact['review']['publication_state'] == 'review_required', 'Low numerical status changed')
    else:
        need(artifact['availability_type'] == 'not_available' and artifact['review']['publication_state'] == 'withheld',
             'withheld status changed')
    # Exact closed hashes include the safe issuer/batch/event-context warnings. Do not drop those disclosures.
    return deepcopy(artifact)

def preserved_public_parent(root, manifest, ticker, raw):
    if not isinstance(manifest,dict) or manifest.get('private_review',{}).get('profile') != PROFILE:
        return False
    validate_manifest(manifest)
    if ticker in IDENTITIES:
        return False
    from .approved_inheritance import _file
    parent_raw = _file(root, 'integration-parent-manifest.json')
    need(sha256_bytes(parent_raw) == ANCHORS['base_manifest_sha256'], 'authentic public parent bytes changed')
    parent = json.loads(parent_raw)
    need(parent.get('catalog_version') == ANCHORS['base_catalog_version'] and len(parent.get('entries',[])) == 550,
         'public parent identity/count changed')
    old = next((r for r in parent['entries'] if r['ticker'] == ticker), None)
    current = next((r for r in manifest.get('entries',[]) if r['ticker'] == ticker), None)
    need(old is not None and old == current and sha256_bytes(raw) == old['artifact_sha256'],
         'current public parent record/bytes changed')
    return True

def validate_binding(raw):
    need(sha256_bytes(raw) == PRIVATE_BINDING_SHA, 'private source/disclosure bytes changed')
    value = json.loads(raw)
    need(value['schema_version'] == 'US-B06-B10-FROZEN-PRIVATE-SOURCE-DISCLOSURE-1'
         and value['cutoff'] == CUTOFF and value['acceptance_cutoff_UTC'] == ACCEPTANCE,
         'private source/disclosure schema/cutoff changed')
    need(value['private_only'] is True and value['source_or_economic_gates_upgraded'] is False
         and all(value[key] is False for key in ('public_release_authorized','auto_revaluation','admission','activation','publication')),
         'private source/disclosure authority changed')
    need(set(value['records']) == set(IDENTITIES) and set(value['numerical_tickers']) == NUMERIC
         and set(value['withheld_tickers']) == NULLS, 'private source/disclosure exact scope changed')
    return value

def validate_review_selection(root, authority_file, authority, manifest, manifest_sha):
    need(os.environ.get('APP_ENV') == 'test', 'native private review requires isolated test mode')
    need(isinstance(authority,dict) and set(authority) == SELECTION_FIELDS, 'native review exact fields required')
    need(authority['schema_version'] == REVIEW_SCHEMA and authority['source'] == 'direct_human_preparation_scope',
         'native review source/schema changed')
    need(authority['read_only'] is True and authority['private_only'] is True
         and all(authority[key] is False for key in ('admission','activation','publication','save','automatic_new_source_revaluation','new_SEC_capture')),
         'native review authority widened')
    need(authority['manifest_sha256'] == manifest_sha and authority['catalog_version'] == manifest['catalog_version'],
         'native review manifest pin changed')
    validate_manifest(manifest)
    checkout = Path(__file__).resolve().parents[3]
    if checkout.parent.name == '.worktrees':
        checkout = checkout.parent.parent
    phase = checkout / 'output/us-expansion-batches-06-10-20261008/private-600-integration'
    run = authority_file.parent
    need(run.parent.resolve() == phase.resolve() and run.name in {'run-a','run-b'}
         and authority_file.name == 'review-authority.json'
         and root.resolve() == (run/'catalogs'/manifest['catalog_version']).resolve(),
         'native private review is outside its authorized isolated phase')
    from .approved_inheritance import _file
    need({p.name for p in root.iterdir()} == ROOT_ENTITIES and not any(p.is_symlink() for p in root.iterdir()),
         'unexpected root proof/authority file or symlink')
    validate_binding(_file(root, 'private-source-disclosure-binding.json'))
    prep_raw = _file(root, 'private600-preparation-authorization.json')
    need(sha256_bytes(prep_raw) == authority['preparation_authority_sha256'] == ANCHORS['approval_sha256'],
         'native preparation pin changed')
    validate_preparation(json.loads(prep_raw))
    parent_raw = _file(root, 'integration-parent-manifest.json')
    need(sha256_bytes(parent_raw) == ANCHORS['base_manifest_sha256'], 'native parent changed')
    parent = json.loads(parent_raw)
    parent_rows = {row['ticker']:row for row in parent['entries']}
    current = {row['ticker']:row for row in manifest['entries']}
    need(set(parent_rows).isdisjoint(IDENTITIES) and set(current) == set(parent_rows) | set(IDENTITIES),
         'native parent/new membership differs')
    need(all(current[ticker] == row for ticker,row in parent_rows.items()), 'native inherited row changed')
    for row in manifest['entries']:
        raw = _file(root, 'artifacts/' + row['ticker'] + '.json')
        need(sha256_bytes(raw) == row['artifact_sha256'], 'native artifact changed')
        if row['ticker'] in IDENTITIES:
            project(json.loads(raw), manifest, ticker=row['ticker'], artifact_sha256=row['artifact_sha256'])
    need({p.name for p in (root/'artifacts').iterdir()} == {t+'.json' for t in current},
         'native artifact file membership differs')
    recipes = manifest['private_recipe_sha256']
    needed = {t for t,row in current.items() if row['availability_type'] != 'not_available'}
    need(set(recipes) == needed and len(recipes) == 548
         and {p.name for p in (root/'recipes').iterdir()} == {t+'.json' for t in recipes},
         'native recipe membership differs')
    for ticker,digest in recipes.items():
        need(sha256_bytes(_file(root,'recipes/'+ticker+'.json')) == digest, 'native recipe bytes changed')
        if ticker in parent_rows:
            need(digest == parent['private_recipe_sha256'][ticker], 'native old550 recipe changed')
    registry_raw = _file(run, 'runtime/registry.json')
    policy_raw = _file(run, 'runtime/refresh-policies.json')
    need(sha256_bytes(registry_raw) == authority['registry_sha256'], 'native registry pin changed')
    need(sha256_bytes(policy_raw) == authority['refresh_policies_sha256'] == manifest['private_refresh_policy_sha256'],
         'native policies pin changed')
    registry, policies = json.loads(registry_raw), json.loads(policy_raw)
    need(registry['baseline_catalog_version'] == manifest['catalog_version']
         and registry['baseline_manifest_sha256'] == manifest_sha, 'native registry baseline differs')
    rows = registry['entries']
    need(len(rows) == 600 and {(r['ticker'],r['cik'],r['batch']) for r in rows}
         == {(r['ticker'],r['cik'],r['batch']) for r in current.values()}, 'native registry identities differ')
    old_reg_raw = _file(root, 'integration-parent-registry.json')
    old_pol_raw = _file(root, 'integration-parent-refresh-policies.json')
    need(sha256_bytes(old_reg_raw) == BASE_REGISTRY_SHA and sha256_bytes(old_pol_raw) == BASE_POLICIES_SHA,
         'native old550 runtime proof changed')
    old_reg, old_pol = json.loads(old_reg_raw), json.loads(old_pol_raw)
    registry_index = {r['ticker']:r for r in rows}
    need(all(registry_index[r['ticker']] == r for r in old_reg['entries'])
         and all(policies[t] == value for t,value in old_pol.items()), 'native old550 runtime row/policy changed')
    for ticker in IDENTITIES:
        policy = policies[ticker]
        need(policy['schema_version'] == 'FINSIGHT-PRIVATE-EXPANSION-HOLD-POLICY-1'
             and policy['ticker'] == ticker and policy['cik'] == IDENTITIES[ticker]
             and policy['private_only'] is True and policy['public_release_authorized'] is False
             and policy['auto_revaluation'] is False and policy['source_epoch'] == CUTOFF
             and policy['pins']['confirmed_recovery_results'] == ANCHORS['recovery_confirmation_sha256'],
             'native new-filing hold changed')
        row = registry_index[ticker]
        need(row['availability_type'] == current[ticker]['availability_type']
             and row['baseline_sha256'] == current[ticker]['artifact_sha256']
             and row['controlling_filing'] == json.loads(_file(root,'artifacts/'+ticker+'.json'))['source_financial_statement'],
             'native new registry source/status changed')
    need(not any(root.glob('local-admission-*.json')) and not (root/'public-scope-authorization.json').exists(),
         'native historical grant became effective')
    return root, manifest_sha
