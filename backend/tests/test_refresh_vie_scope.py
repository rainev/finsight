from __future__ import annotations

import copy,json
from pathlib import Path

import pytest

from app.us_valuation.refresh_vie_scope import (
    VieScopeReviewRequired,bind_unconsolidated_vie_scope,unconsolidated_vie_scope_policy,
)


ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'output/batch-16-structural-sources-20260830/A/structural-filing.json'


def _bind(structural=None):
    structural=structural or json.loads(SOURCE.read_bytes());policy=unconsolidated_vie_scope_policy('A')
    return bind_unconsolidated_vie_scope(ticker='A',policy=policy,structural=structural,
        accession=structural['source_accession'],period=structural['report_date'])


def test_agilent_not_primary_beneficiary_vie_is_investment_diagnostic_not_nci():
    availability,proof=_bind()
    assert availability.state=='evidence_backed_zero' and availability.value==0
    assert proof['issuer_nci']==0
    assert proof['unconsolidated_vie_exposure']==44_000_000
    assert proof['reported_long_term_investments']==136_000_000
    assert proof['sources'][0]['statement_roles']==[]
    assert 'us-gaap:VariableInterestEntityNotPrimaryBeneficiaryDisclosuresAbstract' in proof['sources'][0]['presentation_ancestry']


def test_agilent_vie_scope_rejects_balance_sheet_nci_and_policy_tampering():
    structural=json.loads(SOURCE.read_bytes());changed=copy.deepcopy(structural)
    row=next(item for item in changed['facts'] if item.get('qname')=='us-gaap:NoncontrollingInterestInVariableInterestEntity'
             and item.get('period_end')==changed['report_date'])
    extra=copy.deepcopy(row);extra.update(qname='us-gaap:MinorityInterest',local_name='MinorityInterest',statement_roles=['balance_sheet'])
    changed['facts'].append(extra)
    with pytest.raises(VieScopeReviewRequired,match='ordinary consolidated NCI'):_bind(changed)
    policy=unconsolidated_vie_scope_policy('A');policy['version']='tampered'
    with pytest.raises(VieScopeReviewRequired,match='identity/version mismatch'):
        bind_unconsolidated_vie_scope(ticker='A',policy=policy,structural=structural,
            accession=structural['source_accession'],period=structural['report_date'])
