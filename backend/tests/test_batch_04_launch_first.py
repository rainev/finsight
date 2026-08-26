from pathlib import Path

from app.us_valuation.batch_04 import BATCH_04_TICKERS
from app.us_valuation.batch_04_launch_first import PASS_TICKERS,build_batch_04_launch_first_result
from app.us_valuation.calculator import calculate,calculator_view
from run_batch_04_reclassification import _pass_public
from run_batch_04_history_shadow import run as run_history_shadow
from promote_batch_04_history import promote as promote_history_shadow
from app.us_valuation.batch_04 import BATCH_04_MANIFEST

SOURCE=Path('output/batch-04-sec-source-packets-20260825')
STRUCTURAL=Path('output/batch-04-structural-sources-20260825')


def test_batch_04_has_four_pass_and_six_conditional_low_ordered() -> None:
    for ticker in BATCH_04_TICKERS:
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        values=result['scenario_range']
        assert 0 <= values['low'] <= values['base'] <= values['high']
        assert values['base'] > 0
        assert result['baseline']['availability_type']==('available' if ticker in PASS_TICKERS else 'conditional_estimate')
        assert result['baseline']['confidence']=='Low'
        assert [row['outcome'] for row in result['baseline']['fallback_attempts']]==(['selected'] if ticker in PASS_TICKERS else ['rejected','selected'])


def test_ford_credit_debt_is_not_subtracted_as_industrial_debt() -> None:
    result=build_batch_04_launch_first_result(ticker='F',source_root=SOURCE,structural_root=STRUCTURAL)
    assert result['method']=='ford_normalized_equity_earnings_baseline'
    assert result['governed_assumptions']['route_is_captive_finance_sotp'] is False
    assert result['governed_assumptions']['ev_debt_bridge_applied'] is False
    assert 'not a Ford Credit SOTP' in result['source_ledger']['ford_credit_treatment']


def test_higher_risk_states_have_lower_values_for_standard_models() -> None:
    for ticker in BATCH_04_TICKERS[1:]:
        rows=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)['scenario_rows']
        assert rows[0]['wacc'] > rows[1]['wacc'] > rows[2]['wacc']
        assert rows[0]['conditional_value_per_share'] <= rows[1]['conditional_value_per_share'] <= rows[2]['conditional_value_per_share']


def test_standard_bridge_constants_are_source_traced_and_mcd_scale_is_explicit() -> None:
    for ticker in BATCH_04_TICKERS[1:]:
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        sources=result['source_ledger']['bridge_sources']
        assert len(sources)>=3
        assert any(row.get('unit')=='shares' for row in sources)
        assert result['source_ledger']['bridge_reconciliation']['cash_and_investments']>=0
    mcd=build_batch_04_launch_first_result(ticker='MCD',source_root=SOURCE,structural_root=STRUCTURAL)
    scaled=[row for row in mcd['source_ledger']['bridge_sources'] if row.get('source_kind')=='companyfacts_scaled_disclosure']
    assert scaled[0]['reported_value_millions']==712.3
    assert scaled[0]['value']==712_300_000


def test_mgm_and_mcd_operating_leases_stay_inside_operating_cash() -> None:
    for ticker in ('MCD','MGM'):
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        assert 'not subtracted again as debt' in result['source_ledger']['operating_lease_treatment']


def test_missing_nci_is_not_labeled_reported_zero() -> None:
    for ticker in ('LOW','NKE'):
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        bridge=result['source_ledger']['bridge_reconciliation']
        assert bridge['reported_nci'] is None
        assert bridge['nci_status']=='unresolved_covered_by_asset_reserve'
        ranges=[row for row in result['source_ledger']['bridge_sources'] if row.get('field')=='unresolved_nci_and_other_claims']
        assert ranges[0]['reported_vs_estimated']=='estimated_range'
    for ticker in ('MCD','TJX','HD','ROST'):
        result=build_batch_04_launch_first_result(ticker=ticker,source_root=SOURCE,structural_root=STRUCTURAL)
        bridge=result['source_ledger']['bridge_reconciliation']
        assert bridge['reported_nci'] is None
        assert bridge['nci_status']=='source_proven_absent'
        assert bridge['unresolved_claims_reserve_rates']==(0.,0.,0.)
        absence=[row for row in result['source_ledger']['bridge_sources'] if row.get('reported_vs_estimated')=='source_proven_absent']
        assert absence


def test_tjx_and_rost_use_current_reconstructed_inputs() -> None:
    tjx=build_batch_04_launch_first_result(ticker='TJX',source_root=SOURCE,structural_root=STRUCTURAL)
    assert tjx['reported_inputs']['ttm_revenue']==61_584_000_000
    assert tjx['source_ledger']['flow_sources']['revenue']['period_end']=='2026-05-02'
    assert all(row['filed']<='2026-08-14' for row in tjx['source_ledger']['flow_sources']['revenue']['sources'])
    rost=build_batch_04_launch_first_result(ticker='ROST',source_root=SOURCE,structural_root=STRUCTURAL)
    assert rost['source_ledger']['flow_sources']['interest_expense']['value']==43_506_000
    assert rost['source_ledger']['flow_sources']['interest_expense']['period_end']=='2026-05-02'


def test_mcd_and_hd_pass_treatments_are_source_bounded() -> None:
    mcd=build_batch_04_launch_first_result(ticker='MCD',source_root=SOURCE,structural_root=STRUCTURAL)
    assert 'not added again' in mcd['source_ledger']['pass_repair_treatment']
    investment=[row for row in mcd['source_ledger']['bridge_sources'] if row.get('concept')=='us-gaap:InvestmentsInAffiliatesSubsidiariesAssociatesAndJointVentures']
    assert investment[0]['value']==2_896_000_000
    hd=build_batch_04_launch_first_result(ticker='HD',source_root=SOURCE,structural_root=STRUCTURAL)
    assert 'current TTM cash history includes' in hd['source_ledger']['pass_repair_treatment']


def test_pass_public_artifacts_and_calculators_are_available() -> None:
    for issuer in BATCH_04_MANIFEST:
        if issuer.ticker not in PASS_TICKERS:continue
        result=build_batch_04_launch_first_result(ticker=issuer.ticker,source_root=SOURCE,structural_root=STRUCTURAL);public=_pass_public(issuer,result);view=calculator_view(public)
        assert public['availability_type']=='available'
        assert public['model_policy']['primary']=='fcff_dcf'
        assert view['can_calculate'] is True
        assert calculate(public,overrides={},manual_price=None)['result']['base']==public['scenario_range']['base']


def test_batch_04_history_mode_is_opt_in_and_source_linked() -> None:
    ordinary=build_batch_04_launch_first_result(
        ticker='MCD',source_root=SOURCE,structural_root=STRUCTURAL,history_backed=True
    )
    profile=ordinary['source_ledger']['company_history_profile']
    assert profile['policy_version']=='US-COMPANY-HISTORY-1.0'
    assert profile['full_history'] is True
    assert len(profile['annual_periods'])==5
    assert ordinary['governed_assumptions']['assumption_source_mix']=='reported_and_company_history'
    assert ordinary['baseline']['availability_type']=='available'
    assert ordinary['history_reliability']['model_cap']=='High'


def test_batch_04_history_does_not_remove_material_conditional_status() -> None:
    ford=build_batch_04_launch_first_result(
        ticker='F',source_root=SOURCE,structural_root=STRUCTURAL,history_backed=True
    )
    assert ford['baseline']['availability_type']=='conditional_estimate'
    assert ford['baseline']['confidence']=='Low'
    assert ford['history_reliability']['reasons']==['CONDITIONAL_EVENT_MODEL']
    assert 0 <= ford['scenario_range']['low'] <= ford['scenario_range']['base'] <= ford['scenario_range']['high']


def test_batch_04_history_shadow_preserves_denominator_and_protected_state(tmp_path: Path) -> None:
    report=run_history_shadow(
        source_root=SOURCE,structural_root=STRUCTURAL,output_root=tmp_path/'history-shadow'
    )
    assert report['attempted_count']==10
    assert report['pass_count']==4
    assert report['conditional_count']==6
    assert report['withheld_count']==0
    assert report['numeric_count']==10
    assert report['serving_artifacts_changed'] is False
    assert report['watchlist_changed'] is False
    assert [case['ticker'] for case in report['cases']]==list(BATCH_04_TICKERS)


def test_batch_04_history_promotion_is_exact_and_keeps_backup(tmp_path: Path) -> None:
    target=tmp_path/'serving';target.mkdir()
    prior=b'{"legacy":true}\n';(target/'MCD.json').write_bytes(prior)
    evidence=tmp_path/'evidence'
    receipt=promote_history_shadow(
        source_root=Path('output/batch-04-history-shadow/run-e/staged-public'),
        target_root=target,
        evidence_root=evidence,
        confirmation='PROMOTE_CONFIRMED_BATCH_04_HISTORY',
        require_official_target=False,
    )
    assert receipt['promoted_tickers']==list(BATCH_04_TICKERS)
    assert receipt['replaced_tickers']==['MCD']
    assert len(receipt['added_tickers'])==9
    assert (evidence/'backup'/'MCD.json').read_bytes()==prior
    assert {path.stem for path in target.glob('*.json')}==set(BATCH_04_TICKERS)
