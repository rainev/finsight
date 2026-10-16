"""Exact continuing-business cash bridges; partial disclosures stay partial."""
from copy import deepcopy
from math import isfinite
from datetime import date
from .family_forecast import fact

CONTINUING=[['us-gaap:StatementOperatingActivitiesSegmentAxis','us-gaap:SegmentContinuingOperationsMember']]
DISCONTINUED=[['us-gaap:DisposalGroupClassificationAxis','us-gaap:SegmentDiscontinuedOperationsMember']]
FIELDS={
    'cfo':{'total':['NetCashProvidedByUsedInOperatingActivities'],
           'direct':['NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'],
           'removed':['CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations']},
    'capex':{'total':['PaymentsToAcquireProductiveAssets','PaymentsToAcquirePropertyPlantAndEquipment'],
             'direct':['PaymentsToAcquirePropertyPlantAndEquipmentContinuingOperations'],
             'removed':['PaymentsToAcquireProductiveAssets','PaymentsToAcquirePropertyPlantAndEquipment']},
    'sbc':{'total':['ShareBasedCompensation'],
           'direct':[], 'removed':['ShareBasedCompensation']},
}


def reconcile_continuing_cash(packet, *, removal_scopes=None):
    """Use direct totals or subtract a complete same-period discontinued total.

    Nested disposal dimensions require a reviewed exhaustive scope; never sum
    arbitrary segment leaves or treat D&A and impairment as total operating cash.
    """
    filing=packet['controlling_filing'];metrics={};missing=[]
    for key,selectors in FIELDS.items():
        direct=fact(packet,selectors['direct'],flow=True,optional=True) if selectors['direct'] else None
        scoped=fact(packet,selectors['total'],flow=True,dimensions=CONTINUING,optional=True)
        if direct is not None and scoped is not None and direct['value']!=scoped['value']:
            raise ValueError('conflicting direct continuing '+key)
        selected=direct or scoped
        if key=='sbc' and selected is None:
            # Economic compensation charge, rather than a cash-flow addback.
            selected=fact(packet,['AllocatedShareBasedCompensationExpense'],flow=True,
                          dimensions=CONTINUING,optional=True)
        if selected is not None:
            if key!='cfo' and selected['value']<0:raise ValueError('negative continuing expenditure: '+key)
            metrics[key]={'status':'reconciled','method':'reported_continuing','value':selected['value'],'source':selected}
            continue
        total=fact(packet,selectors['total'],flow=True,optional=True)
        removed=None
        if key=='cfo':
            removed=fact(packet,selectors['removed'],flow=True,optional=True)
        if removed is None:
            removed=fact(packet,selectors['removed'],flow=True,dimensions=DISCONTINUED,optional=True)
        scope=(removal_scopes or {}).get(key)
        if removed is None and scope is not None:
            if scope.get('accession')!=filing['accessionNumber'] or not scope.get('complete_discontinued_scope') or not scope.get('source_url'):
                raise ValueError('discontinued scope review is stale or incomplete')
            removed=fact(packet,selectors['removed'],flow=True,dimensions=scope['dimensions'],optional=True)
        if total is not None and removed is not None:
            if total['period_start']!=removed['period_start'] or total['period_end']!=removed['period_end']:
                raise ValueError('consolidated/discontinued '+key+' periods differ')
            result=total['value']-removed['value']
            if key!='cfo' and (total['value']<0 or removed['value']<0 or result<0):
                raise ValueError('invalid continuing expenditure bridge: '+key)
            selected={**total,'value':result,'qname':'derived:continuing_'+key,'operands':[total,removed]}
            metrics[key]={'status':'reconciled','method':'consolidated_minus_discontinued','value':result,'source':selected}
        else:
            missing.append(key)
            metrics[key]={'status':'partial' if total is not None or removed is not None else 'missing',
                'consolidated':total,'discontinued':removed,
                'reason':'Complete continuing total or same-period discontinued total unavailable; selected adjustments are not a cash-flow total.'}
    return {'accession':filing['accessionNumber'],'period_end':filing['reportDate'],
            'complete':not missing,'missing_fields':missing,'metrics':metrics}


def resolved_flow(bridge,key,start):
    metric=bridge['metrics'][key]
    if metric['status'] not in {'reconciled','assumed_for_model'}:raise ValueError('continuing cash '+key+' bridge unresolved')
    if metric['status']=='assumed_for_model' and not bridge.get('allocation_policy'):
        raise ValueError('continuing cash proxy lacks a reviewed allocation policy')
    source=metric['source']
    if source['period_start']!=start:raise ValueError('continuing cash '+key+' period differs from revenue')
    return deepcopy(source)


def apply_reviewed_allocation(packet,bridge,rule):
    """Keep reported facts intact; fill only missing model inputs as assumptions."""
    if rule.get('schema_version')!='REVIEWED-CONTINUING-CASH-ALLOCATION-1' or rule.get('method')!='equal_cash_margin_retain_unallocated_costs':
        raise ValueError('unsupported continuing cash allocation policy')
    if not all(rule.get(k) for k in ('review_date','review_reason','method_reference')):
        raise ValueError('cash allocation review provenance incomplete')
    date.fromisoformat(rule['review_date'])
    if not rule.get('complete_discontinued_revenue_scope'):
        raise ValueError('discontinued revenue scope incomplete')
    filing=packet['controlling_filing']
    pinned=rule.get('scope_accession')
    if pinned is not None and pinned!=filing['accessionNumber']:
        raise ValueError('disposal revenue scope review requires a new filing decision')
    revenue=fact(packet,['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'],flow=True)
    discarded=fact(packet,rule['discontinued_revenue_concepts'],flow=True,dimensions=rule['discontinued_revenue_dimensions'])
    if (revenue['period_start']!=discarded['period_start'] or revenue['period_end']!=discarded['period_end']
        or revenue['value']<=0 or discarded['value']<0):
        raise ValueError('cash allocation revenue periods or values invalid')
    share=revenue['value']/(revenue['value']+discarded['value'])
    result=deepcopy(bridge);assumed=[]
    for key,metric in result['metrics'].items():
        if metric['status']=='reconciled':continue
        selector=rule.get('pool_selectors',{}).get(key)
        names=selector['concepts'] if selector else FIELDS[key]['total']
        dims=selector.get('dimensions',[]) if selector else []
        total=fact(packet,names,flow=True,dimensions=dims)
        if total['period_start']!=revenue['period_start']:
            raise ValueError('cash allocation source pool period differs')
        if key!='cfo' and total['value']<0:raise ValueError('negative cash cost pool')
        weight=share if key=='cfo' else 1.
        amount=total['value']*weight
        if not isfinite(amount):raise ValueError('nonfinite allocated cash input')
        model_input={'value':amount,'qname':'assumption:continuing_'+key,'unit':'USD',
            'period_start':total['period_start'],'period_end':total['period_end'],
            'source_accession':filing['accessionNumber'],'reported':False,
            'original_reported_source':total,'weight':weight,
            'basis':'equal cash conversion per revenue dollar' if key=='cfo' else 'retain full reported group cost as conservative budget'}
        result['metrics'][key]={'status':'assumed_for_model','method':rule['method'],'value':amount,
                              'source':model_input,'original_partial_metric':deepcopy(metric)}
        assumed.append(key)
    result.update(complete=True,missing_fields=[],reported_reconciliation_complete=bridge['complete'],
                  allocation_policy=deepcopy(rule),assumed_fields=assumed,
                  revenue_allocation={'continuing':revenue,'discontinued':discarded,'share':share})
    return result
