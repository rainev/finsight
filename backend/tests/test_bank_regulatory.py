"""FOD3 contracts for free FR Y-9C and FFIEC source parsing."""

from __future__ import annotations

import pytest

from app.us_valuation.bank_regulatory import parse_call_report_rows, parse_y9c_rows


def _rows() -> list[dict[str, object]]:
    return [
        {"rssd": "1039502", "field": "common_equity", "value": 100.0, "unit": "USD millions"},
        {"rssd": "1039502", "field": "preferred_equity", "value": 5.0, "unit": "USD millions"},
        {"rssd": "1039502", "field": "cet1_capital", "value": 90.0, "unit": "USD millions"},
        {"rssd": "1039502", "field": "total_regulatory_capital", "value": 120.0, "unit": "USD millions"},
        {"rssd": "1039502", "field": "risk_weighted_assets", "value": 800.0, "unit": "USD millions"},
        {"rssd": "1039502", "field": "cet1_ratio", "value": 0.1125, "unit": "ratio"},
        {"rssd": "1039502", "field": "loan_loss_allowance", "value": 8.0, "unit": "USD millions"},
    ]


def test_y9c_requires_parent_identity_and_all_required_capital_equity_rwa_credit_fields() -> None:
    packet = parse_y9c_rows(_rows(), rssd="1039502", period_end="2026-06-30", filed_date="2026-08-10", valuation_date="2026-08-14")
    assert packet.source_kind == "fr_y9c"
    assert {fact.field for fact in packet.facts} >= {
        "common_equity", "preferred_equity", "cet1_capital", "total_regulatory_capital",
        "risk_weighted_assets", "cet1_ratio", "loan_loss_allowance",
    }


def test_call_report_is_subsidiary_corroboration_not_parent_promotable_evidence() -> None:
    packet = parse_call_report_rows(_rows(), rssd="1039502", period_end="2026-06-30", filed_date="2026-08-10", valuation_date="2026-08-14")
    assert packet.source_kind == "ffiec_call_report"
    assert packet.authority == "subsidiary_corroboration"
    assert packet.parent_promotable is False


def test_bank_parser_rejects_wrong_rssd_and_wrong_units() -> None:
    with pytest.raises(ValueError, match="RSSD|unit"):
        parse_y9c_rows(_rows()[:-1] + [{"rssd": "OTHER", "field": "loan_loss_allowance", "value": 8.0, "unit": "EUR"}], rssd="1039502", period_end="2026-06-30", filed_date="2026-08-10", valuation_date="2026-08-14")


def test_y9c_rejects_post_cutoff_and_wrong_regulatory_code() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        parse_y9c_rows(_rows(), rssd="1039502", period_end="2026-06-30", filed_date="2026-08-15", valuation_date="2026-08-14")
    wrong = [dict(row) for row in _rows()]
    wrong[2]["source_record_id"] = "BHCKP793"
    with pytest.raises(ValueError, match="record ID"):
        parse_y9c_rows(wrong, rssd="1039502", period_end="2026-06-30", filed_date="2026-08-10", valuation_date="2026-08-14")
