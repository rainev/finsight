import pytest

from app.us_valuation.bridge_policy import BridgeRange, BridgeResolution
from app.us_valuation.refresh_financials import bridge_assessment


def test_constant_growth_bridge_preserves_combined_preferred_and_nci():
    resolution = BridgeResolution(
        complete=True, can_value=True, missing_fields=(), blocking_fields=(),
        bounded_fields=(), cash_and_investments=BridgeRange(100.,100.,100.),
        total_debt=BridgeRange(200.,200.,200.), preferred_equity=BridgeRange(30.,30.,30.),
        noncontrolling_interests=BridgeRange(40.,40.,40.),
        bridge_adjustment=BridgeRange(-170.,-170.,-170.), fully_diluted_shares=10., reason_codes=(),
    )
    recipe = {'scenarios':{'base':{'engine':'constant_growth_fcff','inputs':{
        'shares':10.,'cash_and_investments':100.,'debt':200.,'noncontrolling_interests':70.,
    }}}}
    valued = {'scenarios':{'base':{'raw_value':83.}}}
    assert bridge_assessment({'resolution':resolution.as_dict()}, recipe, valued)['complete'] is True
    recipe['scenarios']['base']['inputs']['noncontrolling_interests'] = 40.
    with pytest.raises(ValueError, match='does not reconcile'):
        bridge_assessment({'resolution':resolution.as_dict()}, recipe, valued)


def test_fixed_negative_adjustment_remains_in_assessed_equity_range():
    resolution = BridgeResolution(
        complete=True, can_value=True, missing_fields=(), blocking_fields=(), bounded_fields=(),
        cash_and_investments=BridgeRange(100.,100.,100.), total_debt=BridgeRange(200.,200.,200.),
        preferred_equity=BridgeRange(0.,0.,0.), noncontrolling_interests=BridgeRange(0.,0.,0.),
        bridge_adjustment=BridgeRange(-100.,-100.,-100.), fully_diluted_shares=10.,reason_codes=())
    recipe={'scenarios':{'base':{'engine':'enterprise_cash_fcff','inputs':{
        'diluted_shares':10.,'cash_and_investments':100.,'interest_bearing_debt':200.,
        'preferred_equity':0.,'noncontrolling_interests':0.,'nonoperating_adjustment':-50.}}}}
    valued={'scenarios':{'base':{'raw_value':85.}}}
    result=bridge_assessment({'resolution':resolution.as_dict()},recipe,valued)
    assert result['intrinsic_value_range']['midpoint'] == 85.
