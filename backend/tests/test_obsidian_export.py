import json
from pathlib import Path

from scripts.export_us_valuations_to_obsidian import export_valuations


def _artifact() -> dict:
    return {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "valuation_date": "2026-08-01",
        "market": "US",
        "currency": "USD",
        "issuer": {
            "cik": "0000789019",
            "ticker": "MSFT",
            "issuer_name": "MICROSOFT CORPORATION",
            "finsight_sector": "Information Technology",
            "primary_archetype": "large_cap_operating_company",
            "classification_confidence": 0.9,
        },
        "source_financial_statement": {
            "form": "10-K",
            "period_end": "2026-06-30",
            "filed_date": "2026-07-30",
            "accession": "0000789019-26-000001",
            "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000789019",
        },
        "model_policy": {
            "primary": "residual_income",
            "supporting": ["pb_cross_check"],
            "reason": "Equity-level model selected for the filing profile.",
            "fallback_from": None,
        },
        "methodology": {
            "sector_framework": "docs/methodology/united-states/equity-valuation-engine-framework.md",
            "source_policy": "SEC Companyfacts and submissions; no exchange prices",
        },
        "public_assumptions": {
            "cost_of_equity": 0.1,
            "terminal_roe": 0.12,
            "terminal_growth": 0.03,
        },
        "models": {
            "residual_income": {
                "output_type": "intrinsic_value_per_share",
                "intrinsic_value_per_share": 250.0,
                "publication_state": "review_required",
                "warnings": [],
            }
        },
        "scenarios": {
            "bear": {"residual_income": {"intrinsic_value_per_share": 210.0}},
            "base": {"residual_income": {"intrinsic_value_per_share": 250.0}},
            "bull": {"residual_income": {"intrinsic_value_per_share": 300.0}},
        },
        "scenario_range": {
            "low": 210.0,
            "base": 250.0,
            "high": 300.0,
            "label": "assumption range, not a statistical confidence interval",
        },
        "review": {
            "publication_state": "review_required",
            "confidence_grade": "medium",
            "errors": [],
            "warnings": ["Example warning"],
        },
        "automated_review": {
            "decision": "blocked",
            "evidence_status": "incomplete",
            "blocking_reasons": ["weak_sec_provenance"],
            "repair_actions": ["refresh_sec_provenance"],
            "repair_attempts": [{"attempt": 1, "status": "no_progress"}],
        },
        "raw_text": "must never be exported",
    }


def test_export_writes_company_note_and_index_without_raw_payload(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "MSFT.json").write_text(json.dumps(_artifact()), encoding="utf-8")
    output = tmp_path / "vault" / "Finsight" / "US Valuations"

    result = export_valuations(artifacts, output)

    assert result["exported"] == 1
    note = (output / "MSFT.md").read_text(encoding="utf-8")
    assert "SEC filing" in note
    assert "Residual Income" in note
    assert "raw_text" not in note
    assert "https://www.sec.gov/" in note
    assert "Automated review" in note
    assert "weak_sec_provenance" in note
    assert "no_progress" in note
    assert (output / "README.md").exists()


def test_export_is_deterministic_and_dry_run_does_not_write(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "MSFT.json").write_text(json.dumps(_artifact()), encoding="utf-8")
    output = tmp_path / "vault"

    first = export_valuations(artifacts, output)
    first_note = (output / "MSFT.md").read_text(encoding="utf-8")
    second = export_valuations(artifacts, output)

    assert first == second
    assert first_note == (output / "MSFT.md").read_text(encoding="utf-8")
    dry_output = tmp_path / "dry-run"
    dry = export_valuations(artifacts, dry_output, dry_run=True)
    assert dry["exported"] == 1
    assert not dry_output.exists()


def test_export_skips_invalid_artifact_and_reports_error(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "BROKEN.json").write_text("{not json", encoding="utf-8")
    output = tmp_path / "vault"

    result = export_valuations(artifacts, output)

    assert result["exported"] == 0
    assert result["errors"]
    assert not (output / "BROKEN.md").exists()
