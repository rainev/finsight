"""FOD3 contracts for FERC Form 1 / 3-Q evidence."""

from __future__ import annotations

import pytest

from app.us_valuation.ferc_regulatory import parse_ferc_rows


def _rows() -> list[dict[str, object]]:
    return [
        {"entity_id": "FERC-1", "field": "rate_base", "value": 500.0, "unit": "USD millions"},
        {"entity_id": "FERC-1", "field": "allowed_return", "value": 0.095, "unit": "ratio"},
        {"entity_id": "FERC-1", "field": "utility_debt", "value": 200.0, "unit": "USD millions"},
        {"entity_id": "FERC-1", "field": "ownership_interest", "value": 1.0, "unit": "ratio"},
    ]


def test_ferc_packet_preserves_identity_rate_base_return_debt_and_ownership() -> None:
    packet = parse_ferc_rows(_rows(), entity_id="FERC-1", form="FORM1", period_end="2025-12-31", filed_date="2026-04-15", valuation_date="2026-08-14")
    assert packet.source_kind == "ferc_form_1"
    assert {fact.field for fact in packet.facts} == {"rate_base", "allowed_return", "utility_debt", "ownership_interest"}


def test_ferc_subsidiary_data_cannot_promote_to_public_parent_without_allocation() -> None:
    with pytest.raises(ValueError, match="parent|allocation|ownership"):
        parse_ferc_rows(_rows(), entity_id="FERC-1", form="FORM1", period_end="2025-12-31", filed_date="2026-04-15", valuation_date="2026-08-14", public_parent_cik="0000012345", allocation_bridge=None)


def test_ferc_rejects_post_cutoff_and_unreconciled_parent_allocation() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        parse_ferc_rows(_rows(), entity_id="FERC-1", form="FORM1", period_end="2025-12-31", filed_date="2026-08-15", valuation_date="2026-08-14")
    with pytest.raises(ValueError, match="allocation|reconciliation"):
        parse_ferc_rows(
            _rows(), entity_id="FERC-1", form="FORM1", period_end="2025-12-31",
            filed_date="2026-04-15", valuation_date="2026-08-14",
            public_parent_cik="0000012345",
            allocation_bridge={
                "allocation_method": "",
                "reconciliation_status": "fail",
            },
            source_payload_sha256="a" * 64,
        )
