"""Closed inactive650 quality-revision scope; no admission or source adapter.

The compiled anchor authenticates one immutable candidate. Unchanged records
inherit only their exact approved bytes; revised records still use ordinary
public source/model/reviewer/calculator checks.
"""
from copy import deepcopy
import hashlib
import json
from math import isfinite,ulp
from pathlib import Path

SCHEMA="US-B1115-QUALITY-STAGED-INHERITANCE-1"
REVIEW_SCHEMA="US-B1115-QUALITY-STAGED-READ-ONLY-1"
MODEL_VERSION="US-B1115-QUALITY-PUBLIC-LOW-1"
ANCHOR_SHA="c94472c5580762e126c247abe2abf9b8573aa8ec694d79e9db95585bfa9d2a07"
TARGETS=frozenset("ASTE AGCO AWI AZZ FSS DXPE HAYW GBX RUSHA SAIA MLR BOOT STRA LRN LOPE ITRI POWI ACLS VECO CTS MTSI ADUS MEDP OSIS LMAT".split())
CARRY_HELD=frozenset("APEI ENSG NYT PRDO".split())
PUBLIC_NULLS=frozenset("ALSN BDC CBT CECO ITT GATX TRN WERN ODC SHOO OXM UTI EPAC DIOD FORM ONTO CHE USPH HURN ICUI UTMD".split())
AUTHORITY_FIELDS={"schema_version","read_only","manifest_sha256","catalog_version","registry_sha256","admission","activation","publication","save","automatic_new_source_revaluation"}
ROOT_FILES={"manifest.json","artifacts","recipes","refresh-policies.json","prior-catalog","approved-parent-manifest.json","approved-parent-registry.json","approved-parent-policies.json","quality-scope-authorization.json","quality-source-binding.json","quality-private-confirmation.json"}

def require(value,why):
    if not value:raise ValueError("quality staged scope rejected: "+why)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n").encode()

def replay_matches(actual,expected):
    # Stored values, inputs and recipe economic hashes remain exact. Only
    # arithmetic replay permits four representable float steps across runtimes.
    return set(actual)==set(expected)=={'low','base','high'} and all(
        isinstance(actual[k],(int,float)) and not isinstance(actual[k],bool)
        and isinstance(expected[k],(int,float)) and not isinstance(expected[k],bool)
        and isfinite(actual[k]) and isfinite(expected[k])
        and abs(actual[k]-expected[k])<=4*max(ulp(actual[k]),ulp(expected[k]))
        for k in ('low','base','high'))

def anchors():
    path=Path(__file__).with_name("config")/"quality_b1115_staged_anchors_v2.json"
    require(not path.is_symlink(),"anchor symlink")
    raw=path.read_bytes();require(sha(raw)==ANCHOR_SHA,"compiled anchor changed")
    result=json.loads(raw);require(result["schema_version"]==SCHEMA and set(result["targets"])==TARGETS,"compiled scope changed")
    return result

def _context_uncached(root,manifest,proof_reader):
    a=anchors()
    require(callable(proof_reader),"verified proof reader missing")
    bound=proof_reader(root,"manifest.json",a["manifest_sha256"])
    require(manifest==bound,"manifest differs from compiled quality candidate")
    require(manifest.get("staged_release_only") is True and manifest.get("staged_read_only_review_ready") is True,"not inactive read-only stage")
    require(all(manifest.get(k) is False for k in ("admission","activation","publication")),"release flag present")
    require("local_admission" not in manifest and "private_review" not in manifest and not manifest.get("private_integration_only"),"wrong release lineage")
    parent=proof_reader(root,"approved-parent-manifest.json",a["parent_manifest_sha256"])
    grant=proof_reader(root,"quality-scope-authorization.json",a["approval_sha256"])
    binding=proof_reader(root,"quality-source-binding.json",a["binding_sha256"])
    confirmation=proof_reader(root,"quality-private-confirmation.json",a["confirmation_sha256"])
    require(grant.get("source")=="direct_human_user" and grant.get("public_preparation_scope_approved") is True and grant.get("staged_candidate_only") is True,"preparation authority")
    require(set(grant["targets"])==TARGETS and set(binding["targets"])==TARGETS,"approved exact25")
    require(all(grant.get(k) is False for k in ("admission","activation","publication","new_SEC_capture_or_job","policy_economics_change")),"scope expanded")
    require(all(binding.get(k) is False for k in ("admission","activation","publication","new_capture_or_refresh","economic_values_changed")),"binding grants extra scope")
    require(binding["approval_sha256"]==a["approval_sha256"] and binding["private_confirmation_sha256"]==a["confirmation_sha256"],"source/policy ancestry")
    require(confirmation["status"]=="user_confirmed_private_revisions" and confirmation["private_numeric_count"]==30 and confirmation["private_review_holds"]==20,"private confirmation")
    require(binding["cutoff"]=="2026-10-08" and binding["model_policy_version"]==MODEL_VERSION,"frozen source/model version")
    current={e["ticker"]:e for e in manifest["entries"]};old={e["ticker"]:e for e in parent["entries"]}
    require(len(current)==len(old)==650 and set(current)==set(old),"exact650 identity scope")
    require(manifest["availability_counts"]==parent["availability_counts"] and manifest["private_recipe_sha256"].keys()==parent["private_recipe_sha256"].keys(),"availability or recipe membership changed")
    require(all(current[t]==old[t] and manifest["private_recipe_sha256"].get(t)==parent["private_recipe_sha256"].get(t) for t in set(old)-TARGETS),"carried-forward row/recipe changed")
    require(all((current[t]["cik"],current[t]["batch"],current[t]["availability_type"])==(old[t]["cik"],old[t]["batch"],"conditional_estimate") for t in TARGETS),"revised issuer/batch/status changed")
    records=binding["records"]
    require(len(records)==50 and TARGETS=={t for t,r in records.items() if r["updated_value_prepared"]},"source scope changed")
    require(PUBLIC_NULLS=={t for t,r in records.items() if r["existing_public_hold"]},"existing public holds changed")
    require(all(records[t]["confirmed_quality_review_hold"] and records[t]["current_public_value_carry_forward"]["base"] is not None for t in CARRY_HELD),"held prior estimates lost")
    require(all(r["new_filing_hold_preserved"] for r in records.values()),"new-filing hold lost")
    return a,parent,binding,current


def context(root,manifest,proof_reader):
    if hasattr(proof_reader, "context_for"):
        return proof_reader.context_for(root, manifest, lambda: _context_uncached(root, manifest, proof_reader))
    return _context_uncached(root, manifest, proof_reader)

def target(root,manifest,ticker,record,entry,proof_reader):
    from .artifacts import sanitize_public_artifact
    from .automated_review import assess_artifact
    from .calculation_recipe import evaluate_recipe
    try:
        from .latest_calculator import baseline_version
    except ImportError:
        from .calculator import baseline_version
    artifact=proof_reader(root,"artifacts/"+ticker+".json",entry["artifact_sha256"])
    recipe=proof_reader(root,"recipes/"+ticker+".json",manifest["private_recipe_sha256"][ticker])
    require(artifact["issuer"]["ticker"]==ticker and str(artifact["issuer"]["cik"]).zfill(10)==record["cik"],ticker+" identity")
    require(artifact["issuer"]==anchors()["expected_issuer_mapping"][ticker],ticker+" approved issuer classification mapping changed")
    require(artifact["source_financial_statement"]==record["exact_source_header"],ticker+" frozen filing")
    require(all(artifact["source_financial_statement"][k]<="2026-10-08" for k in ("filed_date","period_end")),ticker+" future source")
    require(artifact["model_version"]==MODEL_VERSION and artifact["model_policy"]["primary"]==record["expected_model"],ticker+" model")
    require(artifact["reliability"]["label"]=="Low" and artifact["availability_type"]=="conditional_estimate",ticker+" reliability")
    require(artifact["review"]["publication_state"]=="review_required" and not artifact["review"]["errors"],ticker+" public state")
    require(assess_artifact(artifact)["blocking_reasons"]==[],ticker+" ordinary source/reviewer gate")
    require(sanitize_public_artifact(artifact)==artifact,ticker+" ordinary public projection drift")
    require(all(artifact["scenario_range"][k]==record["confirmed_private_range"][k] for k in ("low","base","high")),ticker+" confirmed value")
    economic={k:recipe[k] for k in ("scenarios","editable","warnings")}
    require(sha(canonical(economic))==record["bound_recipe_economic_sha256"],ticker+" private recipe economics changed")
    require(recipe["baseline_version"]==baseline_version(artifact) and recipe["ticker"]==ticker and recipe["cik"]==record["cik"],ticker+" calculator/source baseline")
    require(replay_matches(evaluate_recipe(recipe)["range"],record["confirmed_private_range"]),ticker+" deterministic replay")
    require(set(record["required_public_disclosures"])<=set(artifact["review"]["warnings"]),ticker+" Low disclosure")
    require(set(recipe["warnings"])<=set(artifact["review"]["warnings"]),ticker+" confirmed model warning")
    return artifact

def validate(root,manifest,*,deep=False,proof_reader=None):
    a,parent,binding,current=context(root,manifest,proof_reader)
    policies=proof_reader(root,"refresh-policies.json",a["policies_sha256"])
    oldpolicies=proof_reader(root,"approved-parent-policies.json",a["parent_policies_sha256"])
    require(set(policies)==set(oldpolicies),"policy membership")
    for t in policies:
        expected=deepcopy(oldpolicies[t])
        if t in TARGETS:
            expected["pins"].update(public_baseline=current[t]["artifact_sha256"],release_scope_approval=a["approval_sha256"],quality_source_policy_binding=a["binding_sha256"])
        require(policies[t]==expected,t+" policy changed beyond baseline pins")
    if deep:
        from .approved_inheritance import validate_inheritance
        validate_inheritance(Path(root)/"prior-catalog",parent,deep=True)
        require({p.name for p in Path(root).iterdir()}==ROOT_FILES,"unexpected catalog root files")
        require({p.name for p in (Path(root)/"artifacts").iterdir()}=={t+".json" for t in current},"artifact membership")
        require({p.name for p in (Path(root)/"recipes").iterdir()}=={t+".json" for t in manifest["private_recipe_sha256"]},"recipe membership")
        for t,e in current.items():proof_reader(root,"artifacts/"+t+".json",e["artifact_sha256"])
        for t,d in manifest["private_recipe_sha256"].items():proof_reader(root,"recipes/"+t+".json",d)
        for t in TARGETS:target(root,manifest,t,binding["records"][t],current[t],proof_reader)
    return {t:(e["cik"],e["batch"],e["availability_type"],e["artifact_sha256"]) for t,e in current.items() if t not in TARGETS}

def preserved_parent_artifact(root,manifest,ticker,raw,*,proof_reader):
    a,parent,binding,current=context(root,manifest,proof_reader)
    require(ticker in current and sha(raw)==current[ticker]["artifact_sha256"],"leaf artifact bytes changed")
    if ticker in TARGETS:
        target(root,manifest,ticker,binding["records"][ticker],current[ticker],proof_reader)
        return False
    return True

def validate_registry(root,manifest,registry,*,proof_reader):
    a,parent,binding,current=context(root,manifest,proof_reader)
    require(sha(canonical(registry))==a["registry_sha256"],"staged registry changed")
    old=proof_reader(root,"approved-parent-registry.json",a["parent_registry_sha256"])
    require(registry["baseline_manifest_sha256"]==a["manifest_sha256"] and registry["baseline_catalog_version"]==manifest["catalog_version"],"registry baseline")
    oldrows={r["ticker"]:r for r in old["entries"]};rows={r["ticker"]:r for r in registry["entries"]}
    require(len(registry["entries"])==len(rows)==650 and set(rows)==set(current),"registry exact650")
    require(all(rows[t]==oldrows[t] for t in set(rows)-TARGETS),"carried-forward registry row")
    for t in TARGETS:
        require((rows[t]["cik"],rows[t]["batch"],rows[t]["availability_type"],rows[t]["baseline_sha256"])==(current[t]["cik"],current[t]["batch"],current[t]["availability_type"],current[t]["artifact_sha256"]),"registry target identity/baseline")
        require(rows[t]["controlling_filing"]==binding["records"][t]["exact_source_header"],"registry controlling source")
    return registry

def review_selection(root,authority_file,authority,manifest,manifest_sha,*,proof_reader):
    a=anchors()
    require(set(authority)==AUTHORITY_FIELDS and authority["schema_version"]==REVIEW_SCHEMA and authority["read_only"] is True,"review authority fields")
    require(all(authority[k] is False for k in ("admission","activation","publication","save","automatic_new_source_revaluation")),"review permits write/release")
    require(authority["manifest_sha256"]==manifest_sha==a["manifest_sha256"] and authority["catalog_version"]==manifest["catalog_version"],"review manifest")
    validate(root,manifest,deep=True,proof_reader=proof_reader)
    registry=proof_reader(authority_file.parent,"runtime/registry.json",a["registry_sha256"])
    require(authority["registry_sha256"]==a["registry_sha256"],"review registry")
    validate_registry(root,manifest,registry,proof_reader=proof_reader)
    proof_reader(authority_file.parent,"runtime/refresh-policies.json",a["policies_sha256"])
    return root,manifest_sha

PUBLIC_FORECAST_FIELDS=frozenset({"accounting_bound_scope","budget_basis","cash_anchor_mode","cash_debt_bridge",
    "debt_net_borrowing_assumption","equity_risk_premium","financing_assumption","forecast_years",
    "future_acquisition_cash_budget_fraction","incremental_growth_cash_intensity","initial_growth_cap","rate_kind",
    "risk_free_rate","sector_assignment","sector_beta_prior","uncertainty_premium","cash_rejection",
    "no_claim_of_reconciled_owner_cash"})

def public_forecast_assumptions(policy):
    # Only reviewed scalar forecast assumptions, never raw facts/recipes or
    # internal private policy IDs. Future fields do not become public by default.
    result={k:deepcopy(v) for k,v in policy.items() if k in PUBLIC_FORECAST_FIELDS}
    require(all(isinstance(v,(str,int,float,bool)) or v is None for v in result.values()),"public policy scalar DTO")
    result["forecast_policy_version"]=MODEL_VERSION
    result["classification"]="ANALYST_ASSUMPTIONS_NOT_REPORTED_FACTS"
    return result

def consumer_disclosures(root,manifest,artifact,payload,*,proof_reader):
    t=artifact["issuer"]["ticker"]
    a=anchors();binding=proof_reader(root,"quality-source-binding.json",a["binding_sha256"])
    if t not in binding["records"]:return payload
    record=binding["records"][t];result=deepcopy(payload)
    warning=list(artifact["review"]["warnings"])
    if t in TARGETS:
        assumptions=public_forecast_assumptions(record["forecast_assumptions"])
        warning.append("Forecast assumptions, not reported facts: "+json.dumps(assumptions,sort_keys=True))
        result["quality_forecast_assumptions"]=assumptions
    elif t in CARRY_HELD:
        warning.append("QUALITY_UPDATE_HELD: prior dated public estimate retained; proposed revised valuation remains held. "+str(record["current_hold_reason"]))
    result["warnings"]=list(dict.fromkeys(result.get("warnings",[])+warning))
    result["staged_scope"]={"schema_version":REVIEW_SCHEMA,"read_only":True,"cutoff":"2026-10-08","admission":False,"activation":False,"publication":False,
        "revised_value_staged":t in TARGETS,"new_filing_hold":True,"quality_update_held":record["confirmed_quality_review_hold"],
        "prior_dated_public_estimate_retained":t in CARRY_HELD,"financial_reference_date":artifact["source_financial_statement"]["period_end"],
        "current_post_event_value_held":t in {"CBT","UTMD"}}
    return result
