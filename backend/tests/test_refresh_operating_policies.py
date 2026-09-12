import json
from pathlib import Path
import pytest

from app.us_valuation.refresh_operating_policies import compile_operating_policy_registry


def test_growth_binding_recalculates_new_history_instead_of_retaining_old_result():
    from app.us_valuation.refresh_bindings import arithmetic
    output = compile_operating_policy_registry(
        registry_path=Path('output/us-refresh-runtime/registry.json'),
        artifacts_dir=Path('output/us-refresh-runtime/baseline/artifacts'),
        recipes_dir=Path('output/us-refresh-runtime/recipes'))
    for ticker in ('GWW','GNRC','IR','BR','HLT','KO','PEP','HRL','PG',
        'ADI','ADP','ADSK','ALLE','AMAT','BBY','BF.B','BKNG','BLDR','CASY',
        'CDW','CIEN','CPRT','CSX','DDOG','DOV','DPZ'):
        policy = next(row['policy'] for row in output['results'] if row['ticker']==ticker)
        growth = policy['history_growth_policy']
        assert 'initial_growth' not in policy['fixed_assumptions']
        field = 'initial_growth' if policy['supported_engine']=='enterprise_cash_fcff' else 'growth'
        for index, case in enumerate(('bear','base','bull')):
            key = f'{case}_historical_growth'
            expression = policy['scenario_bindings'][case][field]
            floor,cap = growth['rule']['floors'][index],growth['rule']['caps'][index]
            for current in (-.8,.037,1.2):
                assert arithmetic(expression,{key:current}) == pytest.approx(max(floor,min(cap,current)))
            retained = growth['verification']['observed_metric'][index]
            assert arithmetic(expression,{key:retained}) == pytest.approx(growth['verification']['recipe_growth'][index])


def test_compiler_covers_frozen_registry_without_claiming_source_validation(tmp_path: Path) -> None:
    output = compile_operating_policy_registry(
        registry_path=Path("output/us-refresh-runtime/registry.json"),
        artifacts_dir=Path("output/us-refresh-runtime/baseline/artifacts"),
        recipes_dir=Path("output/us-refresh-runtime/recipes"),
        output_path=tmp_path / "refresh-policies.json",
    )
    assert output["entry_count"] == 440
    assert output["production_ready"] is False
    assert output["auto_tune"] is False
    assert all(row['status'] in {'compiled_with_gaps', 'compiled_source_validation_pending'} for row in output['results'])
    assert all(row['reason_codes'] for row in output['results'] if row['status'] == 'compiled_with_gaps')
    assert (tmp_path / "refresh-policies.json").exists()


def test_supported_policy_shape_keeps_fixed_assumptions_and_known_aliases() -> None:
    output = compile_operating_policy_registry(
        registry_path=Path("output/us-refresh-runtime/registry.json"),
        artifacts_dir=Path("output/us-refresh-runtime/baseline/artifacts"),
        recipes_dir=Path("output/us-refresh-runtime/recipes"),
    )
    adp = next(row for row in output["results"] if row["ticker"] == "ADP")
    assert adp["policy"]["execution_state"] == "compiled_source_validation_pending"
    assert adp["policy"]["auto_tune"] is False
    assert [adp['policy']['inputs'][f'{case}_cash_margin']['statistic'] for case in ('bear','base','bull')] == ['low','base','high']
    assert [adp['policy']['inputs'][f'{case}_debt']['statistic'] for case in ('bear','base','bull')] == ['high','midpoint','low']
    assert adp['policy']['scenario_bindings']['base']['cash_fcff'] == {'multiply':['ttm_revenue','base_cash_margin']}
    assert adp['policy']['baseline_non_debt_claims']['base']['preferred_equity'] == 475700000.
    assert adp['policy']['scenario_bindings']['base']['nonoperating_adjustment'] == {'subtract':[0.,'adp_claim_reserve']}
    assert adp['policy']['inputs']['adp_claim_reserve']['selector'] == 'special_claim'
    assert 'PaymentsToAcquireOtherPropertyPlantAndEquipment' in adp['policy']['concept_config']['fields']['capital_expenditures']['concepts']
    acn = next(row for row in output['results'] if row['ticker']=='ACN')
    assert 'baseline_non_debt_claim_scope_requires_source_rule' not in acn['reason_codes']
    assert acn['policy']['reported_claim_scope']['required_qnames'] == ('us-gaap:MinorityInterest','us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount')
    dva = next(row for row in output['results'] if row['ticker']=='DVA')
    assert 'baseline_non_debt_claim_scope_requires_source_rule' in dva['reason_codes']
    assert 'PaymentsToAcquireOtherPropertyPlantAndEquipment' not in acn['policy']['concept_config']['fields']['capital_expenditures']['concepts']
    assert adp["policy"]["inputs"]["ttm_revenue"]["concept_candidates"]
    assert "fixed_assumptions" in adp["policy"]
    for ticker in ('DXCM','SYY'):
        scoped = next(row for row in output['results'] if row['ticker']==ticker)
        assert 'issuer_state_scope_requires_explicit_refresh_rule' in scoped['reason_codes']
    for ticker in ('VRTX','LLY','CTSH','VRT','REGN'):
        scoped = next(row for row in output['results'] if row['ticker']==ticker)
        assert 'baseline_non_debt_claim_scope_requires_source_rule' not in scoped['reason_codes']
        claim = scoped['policy']['inputs']['acquisition_liability']
        assert claim['selector']=='special_claim'
        assert claim['policy']['ticker']==ticker
        assert scoped['policy']['scenario_bindings']['base']['nonoperating_adjustment']=={
            'subtract':[0.,'acquisition_liability']}
    for ticker in ('ABBV','STE','CAH','COO','FIS','V'):
        scoped=next(row for row in output['results'] if row['ticker']==ticker)
        assert 'baseline_non_debt_claim_scope_requires_source_rule' not in scoped['reason_codes']
        claim=scoped['policy']['inputs']['litigation_claim']
        assert claim['selector']=='special_claim' and claim['policy']['ticker']==ticker
        assert scoped['policy']['scenario_bindings']['base']['nonoperating_adjustment']=={
            'subtract':[0.,'litigation_claim']}
    for ticker in ('AVY','BALL','MPC'):
        scoped=next(row for row in output['results'] if row['ticker']==ticker)
        assert 'baseline_non_debt_claim_scope_requires_source_rule' not in scoped['reason_codes']
        keys=[key for key,value in scoped['policy']['inputs'].items()
              if value.get('selector')=='special_claim' and value['policy']['schema_version']=='FINSIGHT-OPERATING-CLAIM-1']
        assert keys
    mpc=next(row for row in output['results'] if row['ticker']=='MPC')
    assert mpc['policy']['scenario_bindings']['bear']['nonoperating_adjustment']=={
        'subtract':[0.,'bear_operating_claim']}
    assert mpc['policy']['scenario_bindings']['base']['nonoperating_adjustment']=={
        'subtract':[0.,'base_operating_claim']}
    dash=next(row for row in output['results'] if row['ticker']=='DASH')
    assert 'baseline_non_debt_claim_scope_requires_source_rule' not in dash['reason_codes']
    assert dash['policy']['scenario_bindings']['base']['cash_and_investments']=={
        'subtract':['base_cash_and_investments','base_customer_cash_reserve']}
    assert dash['policy']['inputs']['base_customer_cash_reserve']['policy']['schema_version']=='FINSIGHT-CUSTOMER-FUNDS-1'
    assert dash['policy']['cash_policy']=='DASH-OWNER-CASH-1'
    assert dash['policy']['inputs']['base_cash_margin']['additional_capex_fields']==['software_development']
    assert dash['policy']['scenario_bindings']['base']['noncontrolling_interests']=={
        'add':[{'add':['base_preferred_equity','base_noncontrolling_interests']},'litigation_claim']}
    ice=next(row for row in output['results'] if row['ticker']=='ICE')
    assert 'baseline_non_debt_claim_scope_requires_source_rule' not in ice['reason_codes']
    assert ice['policy']['scenario_bindings']['base']['nonoperating_adjustment']=={
        'subtract':[0.,'matched_customer_funds']}
    assert ice['policy']['reported_claim_scope']['required_qnames']==(
        'us-gaap:MinorityInterest','us-gaap:RedeemableNoncontrollingInterestEquityCarryingAmount')
    for ticker in ('KDP','MSCI'):
        scoped=next(row for row in output['results'] if row['ticker']==ticker)
        assert 'baseline_non_debt_claim_scope_requires_source_rule' not in scoped['reason_codes']
        claims=[value for value in scoped['policy']['inputs'].values()
                if value.get('selector')=='special_claim'
                and value['policy']['schema_version']=='FINSIGHT-ACQUISITION-FINANCING-CLAIMS-1']
        assert claims
    msci=next(row for row in output['results'] if row['ticker']=='MSCI')
    assert msci['policy']['scenario_bindings']['base']['cash_and_investments']=={
        'subtract':['base_cash_and_investments','restricted_cash']}
    assert msci['policy']['scenario_bindings']['base']['nonoperating_adjustment']=={
        'subtract':[0.,'base_acquisition_claim']}
    kdp=next(row for row in output['results'] if row['ticker']=='KDP')
    assert kdp['policy']['scenario_bindings']['base']['noncontrolling_interests']=={
        'add':[{'add':['base_preferred_equity','base_noncontrolling_interests']},
               'base_acquisition_financing_claim']}
    assert kdp['policy']['scenario_bindings']['base']['revenue']=='kdp_pro_forma_revenue'
    mchp=next(row for row in output['results'] if row['ticker']=='MCHP')
    assert 'baseline_non_debt_claim_scope_requires_source_rule' not in mchp['reason_codes']
    assert mchp['policy']['inputs']['base_convertible_dividend_pv']['policy']['schema_version']=='FINSIGHT-CONVERTIBLE-CLAIM-1'
    assert mchp['policy']['scenario_bindings']['base']['diluted_shares']=={
        'add':['source_shares','base_convertible_conversion_shares']}
    assert mchp['policy']['scenario_bindings']['base']['preferred_equity']=={
        'add':['base_preferred_equity','base_convertible_dividend_pv']}
    bmy=next(row for row in output['results'] if row['ticker']=='BMY')
    assert 'baseline_non_debt_claim_scope_requires_source_rule' not in bmy['reason_codes']
    assert bmy['policy']['inputs']['transaction_claim']['policy']['schema_version']=='FINSIGHT-TRANSACTION-CLAIMS-1'
    cohr=next(row for row in output['results'] if row['ticker']=='COHR')
    assert cohr['reason_codes']==[]
    assert cohr['policy']['reported_claim_scope']['required_qnames']==('us-gaap:MinorityInterest',)
    assert cohr['policy']['preferred_lifecycle_scope']['mode']=='settled_conversion_zero'
    assert cohr['policy']['scenario_bindings']['bear']['nonoperating_adjustment']=={
        'subtract':[0.,{'max':[0.,{'subtract':[{'multiply':['ttm_revenue','bear_cash_margin']},'ttm_cash_fcff']}]}]}
    assert cohr['policy']['aggregate_debt_scope']['component_qnames']==(
        'us-gaap:LongTermDebtCurrent','us-gaap:LongTermDebtNoncurrent','us-gaap:FinanceLeaseLiability')
    wmb=next(row for row in output['results'] if row['ticker']=='WMB')
    assert wmb['reason_codes']==[]
    assert wmb['policy']['reported_claim_scope']['required_qnames']==('us-gaap:MinorityInterest',)
    assert wmb['policy']['preferred_lifecycle_scope']['mode']=='current_carrying_claim'
    aos=next(row for row in output['results'] if row['ticker']=='AOS')
    assert aos['reason_codes']==[]
    assert aos['policy']['outside_equity_zero_scope']['ticker']=='AOS'
    assert aos['policy']['aggregate_debt_scope']['component_qnames']==(
        'us-gaap:LongTermDebtCurrent','us-gaap:LongTermDebtNoncurrent')
    agilent=next(row for row in output['results'] if row['ticker']=='A')
    assert agilent['reason_codes']==[]
    assert agilent['policy']['unconsolidated_vie_scope']['schema_version']=='FINSIGHT-UNCONSOLIDATED-VIE-SCOPE-1'
    assert 'LongTermInvestments' not in agilent['policy']['concept_config']['fields']['marketable_securities_noncurrent']['concepts']
    cmi=next(row for row in output['results'] if row['ticker']=='CMI')
    assert cmi['reason_codes']==[]
    assert cmi['policy']['reported_claim_scope']['required_qnames']==('us-gaap:MinorityInterest',)
    assert cmi['policy']['inputs']['guarantee_scope_review']['policy']['schema_version']=='FINSIGHT-NCI-OWNERSHIP-CLAIM-1'
    assert cmi['policy']['scenario_bindings']['base']['nonoperating_adjustment']=={
        'subtract':[0.,'guarantee_scope_review']}


def test_successive_evidence_does_not_bypass_source_validation_gate(tmp_path: Path) -> None:
    evidence = json.loads(Path("output/us-refresh-runtime/successive-filing-binding-evidence.json").read_text())
    custom = {"by_ticker": {"SNDK": {"rows": evidence["rows"]}}}
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(custom))
    output = compile_operating_policy_registry(
        registry_path=Path("output/us-refresh-runtime/registry.json"),
        artifacts_dir=Path("output/us-refresh-runtime/baseline/artifacts"),
        recipes_dir=Path("output/us-refresh-runtime/recipes"),
        evidence_path=evidence_path,
    )
    sndk = next(row for row in output["results"] if row["ticker"] == "SNDK")
    assert sndk["policy"]["source_contract"]["amount_fit_forbidden"] is True
    assert sndk["status"] in {"compiled_source_validation_pending", "compiled_with_gaps"}
    assert sndk['policy']['inputs']['base_cash_margin']['normalization_version'] == 'US-REFRESH-CASH-HISTORY-2'
    assert output['production_ready'] is False
