"""Closed frozen B11-B15 private650 profile; never public or automatic refresh authority."""
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
    "approval_sha256": "4335e9ed95402f87a8bd1d1ee2491b8d4ec4723ae2baa3d874d7e0c05c2d3d0f",
    "approved_artifact_sha256": {
        "ACLS": "acb8ed78b16995d2d55ba5a2112d0165746f81b48d780ea27158bae966d683ff",
        "ADUS": "3df91f19f9c90602aeabca54fc9a14b21fdebf8b1f3a0208f42f3864dfbb899c",
        "AGCO": "01981d41f0f72cfadbbdc7cfb794270e31be57b07ff95f461af1204eed88abb8",
        "ALSN": "32c2df76d11e76f833cef3e955ccd2b24dfe87366e2e8f3acf183863d7909981",
        "APEI": "f04411299c4c5a9ee864693cd57fb4159922178704f593d5f3167dde5fb6090c",
        "ASTE": "9d707e1e2e04a4cbd6da380e8326d954469893ce59581829988510f69f7cb382",
        "AWI": "50593d66ba9a7be57fd6c808a79b00016d2877fdab066fe138214b7f5601db6c",
        "AZZ": "500a8045ad580901a1697abcea14597debfaee2eb4ba155196b692fd4dfe2429",
        "BDC": "dfb547e9a74c403d0213ef59ee1312872df04526f2f192a308761a40bf17c195",
        "BOOT": "17b128f69505efae6c8f669367799637f06b05f839193e1720a27db722849a46",
        "CBT": "3defae8bfe170f2acc9261adf22ef7a066566b73c8f64f070b27281416090150",
        "CECO": "2cbb79864e50779df41166b6f23612ec592c7cefefc7229f04ef59e3744b5024",
        "CHE": "8c4697178ff38cc9ae6f2fd5d2a02b38310af84b0d665d25c63e75dc3a5cb8c9",
        "CTS": "ef503e9c56388587f4aa4c94485ee566a4eecf07062632fe02dddec8f1ad2234",
        "DIOD": "0cc8168c13881f44ffe235310872a6f8999ee22e0beab7b0cab6389230d343a4",
        "DXPE": "8c67cdaf3fbb03eff9dd8aeea0f80e1302a4c4a66f0b04b974bfc35579b84362",
        "ENSG": "abdec05b58c2b9797324440a7994db5be67c753a222a53cba8bdbe5de0b4081f",
        "EPAC": "0496064de403ff84c139cfe1212c4ad8e5508d5e5d4d176353fa50d8c3871245",
        "FORM": "6e2cb0bee3bd204e0c551ee01c02761059f0718e6fb2f6b23c23d185f39fd30a",
        "FSS": "a8287a3f690ba54e09aa59903e9df166bad95ee34dabd0b74d94de07953c50da",
        "GATX": "b31bd9f186f6d05198a2c940eba3c2aa59f3aab33df1af8c0c9fad1e9e557011",
        "GBX": "e7add89f5b343648f08ee79c1a5389d18edd82bd48c3c7506c23e7fdb6e39bd4",
        "HAYW": "53e072a59509d85b3b6359e6d497aaa567675fa8dbe199fba65e31b62c9e4f68",
        "HURN": "8ef5fe0770bb18999c658c3366d9e28e06da7d323b47d7a29cf72bcb968997fb",
        "ICUI": "832d88a7cd993bcffd7239dd79ff918c1b986bf520b9769cb0d0fb2c07b42842",
        "ITRI": "adef8569851c4de85ebbfb0f48385482fe051c9a6e1e38e2341bda18f39f00be",
        "ITT": "55ba9855ee42c7a0c13c8588a59ad794c5534e88cfe79e359994d9cc9008a76c",
        "LMAT": "4aefe42f82d1b201a70cdfc1e7a9b751f848fbe9311897e9f28778118c066f72",
        "LOPE": "940c79cc27f8e7a4a5c491c889887940957395c5e6d3117a390daeaf8cf4f4d4",
        "LRN": "7ccb41de04915ee784521cdb7e320111403410559d963a939ea21308b5a5b152",
        "MEDP": "f1a9f2bf07fa87dee76a0aecdc0b5dfc30967c70988323d43592a60962147c9c",
        "MLR": "ca0d082603fedff6ee941bb68f0cd4f62bf16f23d74036b2356c6b294cd93775",
        "MTSI": "ece8edfaf046692178105c275fab110cc658d408c456e5b142395686d5def744",
        "NYT": "e44a3103eacfd645b68706a44cbf39fbadefa203f48386294efebef256c0e3d5",
        "ODC": "435de2136978a8a7fdc1d43821db5c797edcc7ebbf6f7422aa590c4e17be827d",
        "ONTO": "fdcc7eb1ff184d4caf840496a909677ef4d6577edb73128ee5dcf562a256882f",
        "OSIS": "910f548a16b76c5659ed317bb7c3b2bb7af2340b69560777ade9772cead6c427",
        "OXM": "d9d27d8d2b95af36c08ec597d6419ee3533a29c4c104d2b95402f48691990890",
        "POWI": "4740a30e76f9523e3f8a41e878eac3ed63b9f1bfcee3ea78c9b9b89206c20827",
        "PRDO": "5f07e23a74eaed5e447a7db607d23e51f9b63fd47a064a3836dea3aac536dc05",
        "RUSHA": "4d95950b482bdbc422f2e9f348659a5f94d91c9ee048f1dc32344d766b199f76",
        "SAIA": "375c3263c8bc4160602ef389c35aa46db0da424cca721fd3619694150578b6b0",
        "SHOO": "15648639a800ac1ba5c9d145c1b63e9a44680cdc901bd01f958d8c51461109b6",
        "STRA": "7584a31f926fd0909d9509adf672ed722e1fff42fc9c5d71f70627a342a212ce",
        "TRN": "e25e5478f847cdbf194e752b3e32679a69942ddbb3be9cd2aa2a630d588f0c7f",
        "USPH": "3e161109b8ca9479fab07f848ec0b84008bffb13a0c217cb04ca2c7913ac0580",
        "UTI": "b8dd9601b64a6c5c5e4f648a800cfd01a2dc7fa415c24ddb991cfe81e712b249",
        "UTMD": "c2bfd35b9d7528769cb9cfd088d05d86dad395e475c86f054a562b956a4ec1e6",
        "VECO": "1b63d1071af495732b7c55dd16e65684e3538057af17e9aefcdbdd0be614ad24",
        "WERN": "4d810454ff07b2fb3fb0d0b75c49e33c6598ab4c4ebba536e977eb12167d578b"
    },
    "base_catalog_version": "US-ADMITTED-B06-B10-600-e49841ccb23c1f10484b822c",
    "base_manifest_sha256": "5543a20376f0921887a75de00c8a9883e33aeb0bb5ba56628529d678c37f6b27",
    "catalog_batches": {
        "ACLS": 64,
        "ADUS": 65,
        "AGCO": 61,
        "ALSN": 61,
        "APEI": 63,
        "ASTE": 61,
        "AWI": 61,
        "AZZ": 61,
        "BDC": 61,
        "BOOT": 63,
        "CBT": 61,
        "CECO": 61,
        "CHE": 65,
        "CTS": 64,
        "DIOD": 64,
        "DXPE": 62,
        "ENSG": 65,
        "EPAC": 64,
        "FORM": 64,
        "FSS": 61,
        "GATX": 62,
        "GBX": 62,
        "HAYW": 62,
        "HURN": 65,
        "ICUI": 65,
        "ITRI": 64,
        "ITT": 61,
        "LMAT": 65,
        "LOPE": 63,
        "LRN": 63,
        "MEDP": 65,
        "MLR": 62,
        "MTSI": 64,
        "NYT": 63,
        "ODC": 62,
        "ONTO": 64,
        "OSIS": 65,
        "OXM": 63,
        "POWI": 64,
        "PRDO": 63,
        "RUSHA": 62,
        "SAIA": 62,
        "SHOO": 63,
        "STRA": 63,
        "TRN": 62,
        "USPH": 65,
        "UTI": 63,
        "UTMD": 65,
        "VECO": 64,
        "WERN": 62
    },
    "frozen_ranges_sha256": "e541dbfa2801372969cda7be300207eb0a9cd8c8e95cec87875757554cd7871f",
    "identities": {
        "ACLS": "0001113232",
        "ADUS": "0001468328",
        "AGCO": "0000880266",
        "ALSN": "0001411207",
        "APEI": "0001201792",
        "ASTE": "0000792987",
        "AWI": "0000007431",
        "AZZ": "0000008947",
        "BDC": "0000913142",
        "BOOT": "0001610250",
        "CBT": "0000016040",
        "CECO": "0000003197",
        "CHE": "0000019584",
        "CTS": "0000026058",
        "DIOD": "0000029002",
        "DXPE": "0001020710",
        "ENSG": "0001125376",
        "EPAC": "0000006955",
        "FORM": "0001039399",
        "FSS": "0000277509",
        "GATX": "0000040211",
        "GBX": "0000923120",
        "HAYW": "0001834622",
        "HURN": "0001289848",
        "ICUI": "0000883984",
        "ITRI": "0000780571",
        "ITT": "0000216228",
        "LMAT": "0001158895",
        "LOPE": "0001434588",
        "LRN": "0001157408",
        "MEDP": "0001668397",
        "MLR": "0000924822",
        "MTSI": "0001493594",
        "NYT": "0000071691",
        "ODC": "0000074046",
        "ONTO": "0000704532",
        "OSIS": "0001039065",
        "OXM": "0000075288",
        "POWI": "0000833640",
        "PRDO": "0001046568",
        "RUSHA": "0001012019",
        "SAIA": "0001177702",
        "SHOO": "0000913241",
        "STRA": "0001013934",
        "TRN": "0000099780",
        "USPH": "0000885978",
        "UTI": "0001261654",
        "UTMD": "0000706698",
        "VECO": "0000103145",
        "WERN": "0000793074"
    },
    "null_tickers": [
        "BDC",
        "CECO",
        "CHE",
        "DIOD",
        "EPAC",
        "HURN",
        "ICUI",
        "ODC",
        "ONTO",
        "OXM",
        "USPH",
        "WERN"
    ],
    "numeric_tickers": [
        "ACLS",
        "ADUS",
        "AGCO",
        "ALSN",
        "APEI",
        "ASTE",
        "AWI",
        "AZZ",
        "BOOT",
        "CBT",
        "CTS",
        "DXPE",
        "ENSG",
        "FORM",
        "FSS",
        "GATX",
        "GBX",
        "HAYW",
        "ITRI",
        "ITT",
        "LMAT",
        "LOPE",
        "LRN",
        "MEDP",
        "MLR",
        "MTSI",
        "NYT",
        "OSIS",
        "POWI",
        "PRDO",
        "RUSHA",
        "SAIA",
        "SHOO",
        "STRA",
        "TRN",
        "UTI",
        "UTMD",
        "VECO"
    ],
    "origin_summary_sha256": "3bec0434d8068683b0d117522de7e030d210259f344eda24710368e656474ff2",
    "recovery_confirmation_sha256": "b96a5bf541ff64e563f19ce9b51fa58b4f279e1d2314de02092b8ff1ba1b22cb"
}
SCHEMA = 'FINSIGHT-PRIVATE-INTEGRATION-REVIEW-B11-B15-1'
PROFILE = 'B11-B15-FROZEN-PRIVATE-1'
REVIEW_SCHEMA = 'US-B11-B15-PRIVATE650-READ-ONLY-REVIEW-1'
CUTOFF = '2026-10-08'
ACCEPTANCE = '2026-10-08T15:25:21.701060+00:00'
IDENTITIES = ANCHORS['identities']
ARTIFACT_HASHES = ANCHORS['approved_artifact_sha256']
BATCHES = ANCHORS['catalog_batches']
NUMERIC = frozenset(ANCHORS['numeric_tickers'])
NULLS = frozenset(ANCHORS['null_tickers'])
BASE_REGISTRY_SHA = 'ec2de96070e5f7584f4e9b37a08af66adbd98f033a8dab89847c1e31c45e21b3'
BASE_POLICIES_SHA = '49df170ed5e3d53257d696ef6f54cc60e8b15de9e1a0900e075c1f10a0ab90fd'
PRIVATE_BINDING_SHA = 'aca1f1402524dfdf939bda995a7a427f04055638b6746f97af3acfdb89ed9349'
ROOT_ENTITIES = frozenset({'artifacts','recipes','manifest.json','refresh-policies.json',
    'predecessor-provenance','integration-parent-manifest.json','integration-parent-registry.json',
    'integration-parent-refresh-policies.json','private650-preparation-authorization.json',
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
    'live_runtime_promotion','new_source_capture','new_live_refresh_job',
    'admission_authorized','activation_authorized','publication_authorized','local_activation_authorized',
    'automatic_new_source_revaluation','save_authorized','new_SEC_capture')
DATED_ONLY = {t: {'financial_reference_date': '2026-06-30', 'current_post_event_value_held': True} for t in ('CBT','UTMD')}
PREPARATION_FIELDS = frozenset({'dated_only','schema_version','source','user_request','recorded_at_UTC','private_only',
    'baseline_count','candidate_count','catalog_batches','expansion_batches','evidence_cutoff',
    'acceptance_cutoff_UTC','origin_summary_sha256','recovery_confirmation_sha256','recovery_handoff_sha256',
    'preserve_old600_and_all_prior_private_values','new_numeric','new_withheld','admission','activation',
    'publication','live_runtime_promotion','new_source_capture','new_recovery','new_valuation_inputs',
    'new_live_refresh_job','next_batch','push','cloud_deployment','data_deletion'})
PREPARATION_FALSE = ('admission','activation','publication','live_runtime_promotion','new_source_capture',
    'new_recovery','new_valuation_inputs','new_live_refresh_job','next_batch','push','cloud_deployment','data_deletion')

def fail(why):
    raise ValueError('private review artifact rejected: B11-B15 ' + why)

def need(value, why):
    if not value:
        fail(why)

def validate_preparation(value):
    need(isinstance(value, dict) and set(value) == PREPARATION_FIELDS, 'preparation exact fields required')
    need(value['schema_version'] == 'US-B11-B15-PRIVATE650-PREPARATION-AUTHORITY-1'
         and value['source'] == 'direct_human_user', 'preparation authority source/schema changed')
    need(value['private_only'] is True and value['preserve_old600_and_all_prior_private_values'] is True,
         'private preservation authority changed')
    need(value['baseline_count'] == 600 and value['candidate_count'] == 650
         and value['catalog_batches'] == [61, 62, 63, 64, 65] and value['expansion_batches'] == [11, 12, 13, 14, 15]
         and value['new_numeric'] == 38 and value['new_withheld'] == 12, 'preparation scope/count changed')
    need(value['evidence_cutoff'] == CUTOFF and value['acceptance_cutoff_UTC'] == ACCEPTANCE,
         'preparation cutoff changed')
    need(value['origin_summary_sha256'] == ANCHORS['origin_summary_sha256']
         and value['recovery_confirmation_sha256'] == ANCHORS['recovery_confirmation_sha256']
         and value['recovery_handoff_sha256'] == '002692480c6216451e140aaf3dc99f9a0a4d9c98777128ae9e6fb4a89ecb1824',
         'confirmed recovery pin changed')
    need(value['dated_only'] == DATED_ONLY, 'dated-only/current post-event hold changed')
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
        need(isinstance(entries, list) and len(entries) == len({r['ticker'] for r in entries}) == 650,
             'exact600 entries required')
        need(manifest.get('included_batches') == list(range(1,66)) and manifest.get('artifact_count') == 650,
             'catalog batch/count changed')
        need(Counter(r['availability_type'] for r in entries) == Counter({'available':116,'conditional_estimate':465,'not_available':69}),
             'admitted600-derived availability changed')
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
    if ticker in DATED_ONLY:
        need(artifact['source_financial_statement']['period_end'] == DATED_ONLY[ticker]['financial_reference_date'], 'dated financial reference changed')
        for warnings in (artifact['review']['warnings'], artifact['reliability']['reasons']):
            need(any('DATED_FINANCIAL_REFERENCE_ONLY' in w and 'Current release remains held' in w for w in warnings), 'dated-only/current hold disclosure absent')
    # Exact closed hashes include the safe issuer/batch/event-context warnings. Do not drop those disclosures.
    return deepcopy(artifact)

def consumer_disclosures(manifest, artifact, payload):
    """Carry frozen private warnings across summary/calculator/history surfaces."""
    if manifest.get('private_review', {}).get('profile') != PROFILE:
        return payload
    ticker = artifact.get('ticker', artifact.get('issuer', {}).get('ticker'))
    if ticker not in IDENTITIES:
        return payload
    validate_manifest(manifest)
    result = deepcopy(payload)
    warnings = artifact['review']['warnings']
    result['warnings'] = list(dict.fromkeys([*result.get('warnings', []), *warnings]))
    result['private_scope'] = {'private_only': True, 'public_release_authorized': False,
        'reliability': artifact['reliability']['label'], 'evidence_cutoff': CUTOFF,
        'financial_reference_date': artifact['source_financial_statement']['period_end'],
        'new_filing_review_required': True}
    if ticker in DATED_ONLY:
        result['private_scope'].update(DATED_ONLY[ticker], valuation_scope='dated_financial_reference_only')
    return result


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
    need(parent.get('catalog_version') == ANCHORS['base_catalog_version'] and len(parent.get('entries',[])) == 600,
         'public parent identity/count changed')
    old = next((r for r in parent['entries'] if r['ticker'] == ticker), None)
    current = next((r for r in manifest.get('entries',[]) if r['ticker'] == ticker), None)
    need(old is not None and old == current and sha256_bytes(raw) == old['artifact_sha256'],
         'current public parent record/bytes changed')
    return True

def validate_binding(raw):
    need(sha256_bytes(raw) == PRIVATE_BINDING_SHA, 'private source/disclosure bytes changed')
    value = json.loads(raw)
    need(value['schema_version'] == 'US-B11-B15-FROZEN-PRIVATE-SOURCE-DISCLOSURE-1'
         and value['cutoff'] == CUTOFF and value['acceptance_cutoff_UTC'] == ACCEPTANCE,
         'private source/disclosure schema/cutoff changed')
    need(value['private_only'] is True and value['source_or_economic_gates_upgraded'] is False
         and all(value[key] is False for key in ('public_release_authorized','auto_revaluation','admission','activation','publication')),
         'private source/disclosure authority changed')
    need(value['dated_only'] == DATED_ONLY, 'source binding dated-only/current hold changed')
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
    phase = checkout / 'output/us-expansion-batches-11-15-20261008/private-650-integration'
    run = authority_file.parent
    need(run.parent.resolve() == phase.resolve() and run.name in {'run-a','run-b'}
         and authority_file.name == 'review-authority.json'
         and root.resolve() == (run/'catalogs'/manifest['catalog_version']).resolve(),
         'native private review is outside its authorized isolated phase')
    from .approved_inheritance import _file
    need({p.name for p in root.iterdir()} == ROOT_ENTITIES and not any(p.is_symlink() for p in root.iterdir()),
         'unexpected root proof/authority file or symlink')
    validate_binding(_file(root, 'private-source-disclosure-binding.json'))
    prep_raw = _file(root, 'private650-preparation-authorization.json')
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
    need(set(recipes) == needed and len(recipes) == 581
         and {p.name for p in (root/'recipes').iterdir()} == {t+'.json' for t in recipes},
         'native recipe membership differs')
    for ticker,digest in recipes.items():
        need(sha256_bytes(_file(root,'recipes/'+ticker+'.json')) == digest, 'native recipe bytes changed')
        if ticker in parent_rows:
            need(digest == parent['private_recipe_sha256'][ticker], 'native old600 recipe changed')
    registry_raw = _file(run, 'runtime/registry.json')
    policy_raw = _file(run, 'runtime/refresh-policies.json')
    need(sha256_bytes(registry_raw) == authority['registry_sha256'], 'native registry pin changed')
    need(sha256_bytes(policy_raw) == authority['refresh_policies_sha256'] == manifest['private_refresh_policy_sha256'],
         'native policies pin changed')
    registry, policies = json.loads(registry_raw), json.loads(policy_raw)
    need(registry['baseline_catalog_version'] == manifest['catalog_version']
         and registry['baseline_manifest_sha256'] == manifest_sha, 'native registry baseline differs')
    rows = registry['entries']
    need(len(rows) == 650 and {(r['ticker'],r['cik'],r['batch']) for r in rows}
         == {(r['ticker'],r['cik'],r['batch']) for r in current.values()}, 'native registry identities differ')
    old_reg_raw = _file(root, 'integration-parent-registry.json')
    old_pol_raw = _file(root, 'integration-parent-refresh-policies.json')
    need(sha256_bytes(old_reg_raw) == BASE_REGISTRY_SHA and sha256_bytes(old_pol_raw) == BASE_POLICIES_SHA,
         'native old600 runtime proof changed')
    old_reg, old_pol = json.loads(old_reg_raw), json.loads(old_pol_raw)
    registry_index = {r['ticker']:r for r in rows}
    need(all(registry_index[r['ticker']] == r for r in old_reg['entries'])
         and all(policies[t] == value for t,value in old_pol.items()), 'native old600 runtime row/policy changed')
    for ticker in IDENTITIES:
        policy = policies[ticker]
        expected_fields = {'schema_version','version','ticker','cik','private_only','public_release_authorized',
                           'auto_revaluation','source_epoch','reasons','pins'}
        if ticker in DATED_ONLY:
            expected_fields.add('dated_only')
        need(set(policy) == expected_fields, 'native private hold policy exact fields required')
        need(policy['schema_version'] == 'FINSIGHT-PRIVATE-EXPANSION-HOLD-POLICY-1'
             and policy['ticker'] == ticker and policy['cik'] == IDENTITIES[ticker]
             and policy['private_only'] is True and policy['public_release_authorized'] is False
             and policy['auto_revaluation'] is False and policy['source_epoch'] == CUTOFF
             and policy['pins']['confirmed_recovery_results'] == ANCHORS['recovery_confirmation_sha256'],
             'native new-filing hold changed')
        if ticker in DATED_ONLY:
            need(policy.get('dated_only') == DATED_ONLY[ticker], 'native dated-only/current hold policy changed')
        row = registry_index[ticker]
        need(row['availability_type'] == current[ticker]['availability_type']
             and row['baseline_sha256'] == current[ticker]['artifact_sha256']
             and row['controlling_filing'] == json.loads(_file(root,'artifacts/'+ticker+'.json'))['source_financial_statement'],
             'native new registry source/status changed')
    need(not any(root.glob('local-admission-*.json')) and not (root/'public-scope-authorization.json').exists(),
         'native historical grant became effective')
    return root, manifest_sha
