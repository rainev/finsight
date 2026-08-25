"""Recovery evidence selection contracts."""

import pytest

from app.us_valuation.batch_01_recovery_inputs import structural_fact


def test_structural_fact_requires_exact_period_unit_and_dimensions() -> None:
    filing = {
        "facts": [
            {
                "local_name": "Cash",
                "period_start": None,
                "period_end": "2026-06-30",
                "unit": "USD",
                "dimensions": [],
                "value": 10,
            },
            {
                "local_name": "Cash",
                "period_start": None,
                "period_end": "2026-06-30",
                "unit": "USD",
                "dimensions": [["LegalEntityAxis", "SubsidiaryMember"]],
                "value": 4,
            },
        ]
    }
    assert structural_fact(filing, local_name="Cash", period_end="2026-06-30") == 10
    assert structural_fact(
        filing,
        local_name="Cash",
        period_end="2026-06-30",
        dimensions=(("LegalEntityAxis", "SubsidiaryMember"),),
    ) == 4
    with pytest.raises(ValueError, match="one exact"):
        structural_fact(filing, local_name="Cash", period_end="2025-12-31")
