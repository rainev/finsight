from __future__ import annotations

from copy import deepcopy
import json

from app.us_valuation.automated_review import (
    assess_artifact,
    discover_issuers,
    repair_provenance_from_submissions,
    run_repair_loop,
)
from app.us_valuation.artifacts import frontend_company, public_result


def clean_artifact() -> dict:
    return {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "valuation_date": "2026-08-01",
        "issuer": {
            "ticker": "AAPL",
            "classification_confidence": 0.98,
        },
        "source_financial_statement": {
            "form": "10-Q",
            "period_end": "2026-03-28",
            "filed_date": "2026-05-01",
            "accession": "0000320193-26-000013",
            "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000013/aapl-20260328.htm",
        },
        "model_policy": {"primary": "fcff_dcf"},
        "review": {"publication_state": "review_required", "errors": [], "warnings": []},
        "models": {
            "fcff_dcf": {"publication_state": "pass", "intrinsic_value_per_share": 100},
            "epv": {"publication_state": "pass", "intrinsic_value_per_share": 95},
        },
        "scenarios": {
            "low": {"fcff_dcf": {"publication_state": "pass", "intrinsic_value_per_share": 90}},
            "base": {"fcff_dcf": {"publication_state": "pass", "intrinsic_value_per_share": 100}},
            "high": {"fcff_dcf": {"publication_state": "pass", "intrinsic_value_per_share": 110}},
        },
    }


def test_clean_artifact_is_automatically_approved() -> None:
    result = assess_artifact(clean_artifact())

    assert result["decision"] == "approved"
    assert result["publication_state"] == "pass"
    assert result["blocking_reasons"] == []
    assert result["evidence_status"] == "complete"


def test_unknown_model_state_is_blocked() -> None:
    artifact = clean_artifact()
    artifact["models"]["fcff_dcf"]["publication_state"] = "unknown"

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert "invalid_model_state:fcff_dcf" in result["blocking_reasons"]


def test_weak_sec_provenance_is_blocked_with_repair_reason() -> None:
    artifact = clean_artifact()
    artifact["source_financial_statement"].update(
        {"filed_date": None, "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=320193"}
    )

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert "weak_sec_provenance" in result["blocking_reasons"]
    assert "refresh_sec_provenance" in result["repair_actions"]


def test_repair_loop_retries_until_artifact_passes_and_records_attempts() -> None:
    initial = clean_artifact()
    initial["source_financial_statement"]["url"] = None
    calls = 0

    def repair(artifact: dict, assessment: dict) -> dict:
        nonlocal calls
        calls += 1
        repaired = deepcopy(artifact)
        repaired["source_financial_statement"]["url"] = clean_artifact()[
            "source_financial_statement"
        ]["url"]
        return repaired

    result = run_repair_loop(initial, repair=repair, max_attempts=3)

    assert calls == 1
    assert result["assessment"]["decision"] == "approved"
    assert len(result["repair_attempts"]) == 1
    assert result["repair_attempts"][0]["status"] == "repaired"


def test_repair_loop_stops_when_repair_makes_no_progress() -> None:
    initial = clean_artifact()
    initial["source_financial_statement"]["url"] = None

    result = run_repair_loop(initial, repair=lambda artifact, assessment: artifact, max_attempts=3)

    assert result["assessment"]["decision"] == "blocked"
    assert len(result["repair_attempts"]) == 1
    assert result["repair_attempts"][0]["status"] == "no_progress"


def test_provenance_repair_uses_submission_accession_and_document() -> None:
    artifact = clean_artifact()
    artifact["source_financial_statement"].update({"filed_date": None, "url": None})
    submissions = {
        "cik": "0000320193",
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000013"],
                "filingDate": ["2026-05-01"],
                "reportDate": ["2026-03-28"],
                "form": ["10-Q"],
                "primaryDocument": ["aapl-20260328.htm"],
            }
        },
    }

    repaired = repair_provenance_from_submissions(artifact, submissions)

    source = repaired["source_financial_statement"]
    assert source["filed_date"] == "2026-05-01"
    assert source["url"] == (
        "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019326000013/aapl-20260328.htm"
    )


def test_equity_result_uses_model_agnostic_public_serializer() -> None:
    result = {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "valuation_date": "2026-08-01",
        "market": "US",
        "currency": "USD",
        "financial_period_end": "2026-03-31",
        "issuer": {
            "cik": "0000004904", "ticker": "AEP", "issuer_name": "AEP",
            "finsight_sector": "Utilities", "primary_archetype": "us_utility",
            "secondary_archetypes": [], "classification_confidence": 0.98,
            "mapping_version": "US-ARCHETYPE-1.1", "classification_reason": "test",
            "model_route_eligible": True, "model_route_reason": "test",
        },
        "source_financial_statement": {
            "form": "10-Q", "period_end": "2026-03-31", "filed_date": None,
            "accession": "0000004904-26-000059", "url": None,
        },
        "source_manifest": {"status": "fixture"},
        "model_policy": {"primary": "ddm", "supporting": [], "blend_models": False, "reason": "test"},
        "public_assumptions": {"last_dividend": 1.0},
        "models": {"ddm": {"model": "ddm", "output_type": "intrinsic_value_per_share", "currency": "USD", "intrinsic_value_per_share": 20.0, "publication_state": "review_required", "errors": [], "warnings": []}},
        "scenarios": {name: {"ddm": {"intrinsic_value_per_share": value, "publication_state": "review_required"}} for name, value in {"bear": 18.0, "base": 20.0, "bull": 22.0}.items()},
        "scenario_range": {"low": 18.0, "base": 20.0, "high": 22.0, "label": "test"},
        "review": {"publication_state": "review_required", "confidence_grade": "medium", "errors": [], "warnings": []},
        "methodology": {"source_policy": "SEC"},
    }
    submissions = {"cik": "0000004904", "filings": {"recent": {"accessionNumber": ["0000004904-26-000059"], "filingDate": ["2026-05-01"], "reportDate": ["2026-03-31"], "form": ["10-Q"], "primaryDocument": ["aep-20260331.htm"]}}}

    public = public_result(result, submissions)

    assert public["ticker"] == "AEP"
    assert public["model_policy"]["primary"] == "ddm"
    assert set(public["models"]) == {"ddm"}
    assert public["scenarios"]["base"]["ddm"]["model"] == "ddm"
    assert public["source_financial_statement"]["filed_date"] == "2026-05-01"
    assert public["automated_review"]["decision"] == "approved"
    assert public["review"]["publication_state"] == "pass"


def test_unsanitized_candidate_preserves_values_for_repair_before_public_scrubbing() -> None:
    artifact = clean_artifact()
    artifact["review"]["warnings"] = [
        "Incremental dilutive shares were not available; the per-share denominator uses a proxy.",
        "DCF and EPV differ by more than 40%; the growth thesis requires review.",
        "Segment evidence is governed filing-table transcription.",
    ]
    from app.us_valuation.artifacts import _finalize_automated_public_artifact

    candidate = _finalize_automated_public_artifact(artifact, sanitize=False)
    assert candidate["automated_review"]["decision"] == "approved_with_caveat"
    assert candidate["review"]["publication_state"] == "review_required"
    assert candidate["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100

    sanitized = _finalize_automated_public_artifact(artifact, sanitize=True)
    assert sanitized["review"]["publication_state"] == "review_required"
    assert sanitized["models"]["fcff_dcf"]["intrinsic_value_per_share"] == 100


def test_low_classification_confidence_is_review_grade_not_a_hard_failure() -> None:
    artifact = clean_artifact()
    artifact["issuer"]["classification_confidence"] = 0.7

    result = assess_artifact(artifact)

    assert result["decision"] == "approved_with_caveat"
    assert result["publication_state"] == "review_required"
    assert result["blocking_reasons"] == []
    assert "reclassify_issuer_or_switch_model" in result["repair_actions"]


def test_structural_model_warning_remains_a_hard_failure() -> None:
    artifact = clean_artifact()
    artifact["review"]["warnings"] = [
        "Terminal value exceeds 85% of enterprise value."
    ]

    result = assess_artifact(artifact)

    assert result["decision"] == "blocked"
    assert result["publication_state"] == "withheld"


def test_frontend_metadata_uses_selected_equity_model() -> None:
    result = {
        "issuer": {"ticker": "AEP", "issuer_name": "AEP", "finsight_sector": "utilities", "primary_archetype": "regulated_utility"},
        "financial_period_end": "2026-03-31",
        "financials": {"annual": [], "quarterly": {"revenue": []}},
    }
    public = {
        "ticker": "AEP",
        "source_financial_statement": {"form": "10-Q", "period_end": "2026-03-31", "filed_date": "2026-05-01", "url": "https://www.sec.gov/Archives/edgar/data/4904/filing.htm"},
        "model_policy": {"primary": "ddm", "supporting": [], "reason": "regulated utility"},
        "review": {"publication_state": "pass", "warnings": []},
    }

    frontend = frontend_company(
        result,
        public,
        {"ticker": "AEP", "short_name": "AEP", "subsector": "utility", "insight": "test"},
    )

    assert frontend["valuation"]["modelPolicy"]["primary"] == "ddm"
    assert frontend["valuation"]["modelPolicy"]["crossChecks"] == []


def test_discover_issuers_reads_only_valid_public_artifact_identities(tmp_path) -> None:
    (tmp_path / "AAPL.json").write_text(json.dumps({"issuer": {"ticker": "AAPL", "cik": "320193", "issuer_name": "Apple Inc.", "finsight_sector": "technology"}}))
    (tmp_path / "bad.json").write_text("not json")
    (tmp_path / "wrong.json").write_text(json.dumps({"issuer": {"ticker": "MSFT", "cik": "789019"}}))

    assert discover_issuers(tmp_path) == [{
        "ticker": "AAPL", "cik": "320193", "short_name": "Apple Inc.", "subsector": "technology"
    }]
