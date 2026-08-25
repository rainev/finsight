"""FOD3 contracts for source-linked specialist evidence packets."""

from __future__ import annotations

import pytest

from app.us_valuation.specialist_evidence import (
    IdentityBridge,
    RegulatedEntityIdentity,
    SpecialistFact,
    SpecialistPacket,
)


def _parent() -> RegulatedEntityIdentity:
    return RegulatedEntityIdentity(
        cik="0000019617", rssd="1039502", lei="7H6GLXDRUGQFU57RNE97",
        legal_name="Example Bancorp, Inc.", entity_kind="holding_company",
    )


def _bridge(*, proven: bool = True) -> IdentityBridge:
    return IdentityBridge(
        public_parent=_parent(), regulated_entity=_parent(),
        relationship="parent_reporting_entity", consolidation_proven=proven,
        evidence_url="https://www.federalreserve.gov/fixture", evidence_accession="FRY9C-2026Q2",
    )


def test_specialist_packet_round_trips_identity_fact_and_immutable_receipt() -> None:
    fact = SpecialistFact(
        field="cet1_capital", value=125.0, unit="USD millions", period_end="2026-06-30",
        filed_date="2026-08-10", source_url="https://www.federalreserve.gov/fixture",
        source_record_id="BHCK8274", extraction_method="fr_y9c_xbrl",
    )
    packet = SpecialistPacket(
        source_kind="fr_y9c", identity_bridge=_bridge(), facts=(fact,), valuation_date="2026-08-14",
        source_sha256="a" * 64,
    )
    assert SpecialistPacket.from_dict(packet.as_dict()) == packet
    assert packet.receipt_sha256


def test_specialist_packet_rejects_wrong_parent_post_cutoff_unit_and_unproven_consolidation() -> None:
    fact = SpecialistFact(
        field="cet1_capital", value=125.0, unit="EUR", period_end="2026-06-30",
        filed_date="2026-08-15", source_url="https://www.federalreserve.gov/fixture",
        source_record_id="BHCK8274", extraction_method="fr_y9c_xbrl",
    )
    with pytest.raises(ValueError, match="cutoff|unit|consolidation"):
        SpecialistPacket(
            source_kind="fr_y9c", identity_bridge=_bridge(proven=False), facts=(fact,),
            valuation_date="2026-08-14", source_sha256="a" * 64,
        )


def test_subsidiary_packet_requires_a_proven_parent_allocation_bridge() -> None:
    subsidiary = RegulatedEntityIdentity(
        cik=None, rssd="1234567", lei="529900TESTSUBSIDIAR1",
        legal_name="Example Bank, N.A.", entity_kind="bank_subsidiary",
    )
    with pytest.raises(ValueError, match="allocation|consolidation"):
        IdentityBridge(
            public_parent=_parent(), regulated_entity=subsidiary,
            relationship="regulated_bank_subsidiary", consolidation_proven=False,
            evidence_url="https://www.ffiec.gov/fixture", evidence_accession="CALL-2026Q2",
        )
