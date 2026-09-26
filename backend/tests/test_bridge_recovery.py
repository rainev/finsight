"""Controls for repairing legacy FCFF bridge artifacts without publishing guesses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.us_valuation.bridge_recovery import (
    conflicting_resolved_evidence_fields,
    controlling_filing_record,
    discover_legacy_fcff_cases,
    evaluate_recovery_candidate,
    missing_bridge_fields,
    relevant_filing_evidence,
    recovery_source_metadata,
)
from scripts.recover_legacy_fcff_bridges import (
    promote_staged_candidate,
    quarantine_staged_candidate,
    quarantine_superseded_staging,
    quarantine_technical_failure_artifact,
)


def _legacy_artifact(*, ticker: str = "TEST") -> dict:
    return {
        "issuer": {"ticker": ticker, "cik": "0000123456", "issuer_name": "Test Inc."},
        "valuation_date": "2026-08-01",
        "model_policy": {
            "primary": "residual_income",
            "fallback_from": "fcff_dcf",
        },
        "review": {
            "publication_state": "withheld",
            "warnings": [
                "FCFF enterprise-to-equity bridge incomplete "
                "(missing commercial_paper, marketable_securities_noncurrent); "
                "valued via residual_income equity-level fallback."
            ],
        },
    }


def test_legacy_case_discovery_is_sorted_and_excludes_other_artifacts(tmp_path: Path):
    for ticker in ("ZZZ", "AAA"):
        (tmp_path / f"{ticker}.json").write_text(json.dumps(_legacy_artifact(ticker=ticker)))
    current = _legacy_artifact(ticker="CURRENT")
    current["model_policy"] = {"primary": "fcff_dcf"}
    (tmp_path / "CURRENT.json").write_text(json.dumps(current))
    (tmp_path / "broken.json").write_text("not json")

    cases = discover_legacy_fcff_cases(tmp_path)

    assert [case.ticker for case in cases] == ["AAA", "ZZZ"]
    assert cases[0].missing_fields == (
        "commercial_paper",
        "marketable_securities_noncurrent",
    )


def test_missing_bridge_fields_fails_closed_when_warning_is_unparseable():
    artifact = _legacy_artifact()
    artifact["review"]["warnings"] = ["FCFF bridge incomplete; details unavailable"]

    with pytest.raises(ValueError, match="missing bridge fields"):
        missing_bridge_fields(artifact)


def test_controlling_filing_record_requires_exact_accession_and_metadata():
    submissions = {
        "filings": {
            "recent": {
                "accessionNumber": ["0000123456-26-000001"],
                "form": ["10-Q"],
                "reportDate": ["2026-06-30"],
                "filingDate": ["2026-07-30"],
                "primaryDocument": ["test-20260630.htm"],
            }
        }
    }

    record = controlling_filing_record(submissions, "0000123456-26-000001")

    assert record == {
        "accession": "0000123456-26-000001",
        "form": "10-Q",
        "report_date": "2026-06-30",
        "filing_date": "2026-07-30",
        "primary_document": "test-20260630.htm",
    }
    with pytest.raises(ValueError, match="not found"):
        controlling_filing_record(submissions, "missing")


@pytest.mark.parametrize("missing_key", ["reportDate", "filingDate", "primaryDocument"])
def test_controlling_filing_record_rejects_incomplete_metadata(missing_key: str):
    recent = {
        "accessionNumber": ["0000123456-26-000001"],
        "form": ["10-Q"],
        "reportDate": ["2026-06-30"],
        "filingDate": ["2026-07-30"],
        "primaryDocument": ["test-20260630.htm"],
    }
    recent[missing_key] = [""]

    with pytest.raises(ValueError, match="incomplete"):
        controlling_filing_record({"filings": {"recent": recent}}, "0000123456-26-000001")


def test_recovery_source_metadata_builds_exact_sec_provenance():
    metadata = recovery_source_metadata(
        ticker="TEST",
        cik="0000123456",
        filing={
            "accession": "0000123456-26-000001",
            "form": "10-Q",
            "report_date": "2026-06-30",
            "filing_date": "2026-07-30",
            "primary_document": "test-20260630.htm",
        },
    )

    assert metadata["source_accession"] == "0000123456-26-000001"
    assert metadata["period_end"] == "2026-06-30"
    assert "unit" not in metadata
    assert metadata["source_url"] == (
        "https://www.sec.gov/Archives/edgar/data/123456/"
        "000012345626000001/test-20260630.htm"
    )


def test_relevant_filing_evidence_excludes_unrequested_parser_observations():
    records = [
        {"field": "commercial_paper", "value": 0, "status": "resolved"},
        {"field": "noncurrent_debt", "value": 123, "status": "resolved"},
        {"field": "finance_lease_total", "value": 10, "status": "resolved"},
    ]

    assert relevant_filing_evidence(records, {"commercial_paper"}) == [records[0]]
    assert relevant_filing_evidence(records, {"finance_lease_current"}) == [records[2]]


def test_conflicting_resolved_evidence_field_is_quarantined():
    records = [
        {"field": "noncurrent_debt", "value": 100, "status": "resolved"},
        {"field": "noncurrent_debt", "value": 200, "status": "resolved"},
        {"field": "commercial_paper", "value": 0, "status": "resolved"},
    ]

    assert conflicting_resolved_evidence_fields(records) == ("noncurrent_debt",)
    assert relevant_filing_evidence(records, {"noncurrent_debt", "commercial_paper"}) == [
        records[2]
    ]


def test_candidate_is_accepted_only_for_complete_nonfallback_fcff():
    private = {
        "model_policy": {"primary": "fcff_dcf"},
        "financials": {
            "balance_sheet": {
                "bridge_complete": True,
                "bridge_missing_fields": [],
            }
        },
    }
    public = {
        "model_policy": {"primary": "fcff_dcf"},
        "models": {
            "fcff_dcf": {
                "intrinsic_value_per_share": 42.0,
                "publication_state": "review_required",
            }
        },
        "scenarios": {
            "base": {
                "fcff_dcf": {
                    "intrinsic_value_per_share": 42.0,
                    "publication_state": "review_required",
                }
            }
        },
        "review": {"publication_state": "review_required"},
    }

    decision = evaluate_recovery_candidate(private, public)

    assert decision.accepted is True
    assert decision.reasons == ()


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda private, public: private["model_policy"].update(fallback_from="fcff_dcf"), "legacy_fallback"),
        (lambda private, public: private["financials"]["balance_sheet"].update(bridge_complete=False), "bridge_incomplete"),
        (lambda private, public: public["review"].update(publication_state="withheld"), "public_withheld"),
        (lambda private, public: public["models"]["fcff_dcf"].update(intrinsic_value_per_share=None), "missing_intrinsic_value"),
    ],
)
def test_candidate_gate_rejects_unsafe_recovery(mutation, reason: str):
    private = {
        "model_policy": {"primary": "fcff_dcf"},
        "financials": {
            "balance_sheet": {
                "bridge_complete": True,
                "bridge_missing_fields": [],
            }
        },
    }
    public = {
        "model_policy": {"primary": "fcff_dcf"},
        "models": {
            "fcff_dcf": {
                "intrinsic_value_per_share": 42.0,
                "publication_state": "review_required",
            }
        },
        "scenarios": {},
        "review": {"publication_state": "review_required"},
    }
    mutation(private, public)

    decision = evaluate_recovery_candidate(private, public)

    assert decision.accepted is False
    assert reason in decision.reasons


def test_promotion_rechecks_candidate_and_writes_only_accepted_artifact(tmp_path: Path):
    stage = tmp_path / "stage" / "TEST"
    data = tmp_path / "data"
    stage.mkdir(parents=True)
    private = {
        "issuer": {"ticker": "TEST"},
        "model_policy": {"primary": "fcff_dcf"},
        "financials": {
            "balance_sheet": {"bridge_complete": True, "bridge_missing_fields": []}
        },
    }
    public = {
        "issuer": {"ticker": "TEST"},
        "model_policy": {"primary": "fcff_dcf"},
        "models": {
            "fcff_dcf": {
                "intrinsic_value_per_share": 42.0,
                "publication_state": "review_required",
            }
        },
        "scenarios": {},
        "review": {"publication_state": "review_required"},
    }
    (stage / "recovery-result.json").write_text(json.dumps({"accepted": True}))
    (stage / "valuation-private.json").write_text(json.dumps(private))
    (stage / "valuation-public-candidate.json").write_text(json.dumps(public))

    target = promote_staged_candidate("TEST", output_root=tmp_path / "stage", data_root=data)

    assert target == data / "TEST.json"
    assert json.loads(target.read_text()) == public


def test_promotion_refuses_unaccepted_candidate_without_overwrite(tmp_path: Path):
    stage = tmp_path / "stage" / "TEST"
    data = tmp_path / "data"
    stage.mkdir(parents=True)
    data.mkdir()
    target = data / "TEST.json"
    target.write_text('{"preserved": true}')
    (stage / "recovery-result.json").write_text(json.dumps({"accepted": False}))

    with pytest.raises(ValueError, match="not accepted"):
        promote_staged_candidate("TEST", output_root=tmp_path / "stage", data_root=data)

    assert json.loads(target.read_text()) == {"preserved": True}


def test_quarantine_replaces_legacy_fallback_with_fresh_withheld_fcff(tmp_path: Path):
    stage = tmp_path / "stage" / "TEST"
    data = tmp_path / "data"
    stage.mkdir(parents=True)
    private = {
        "issuer": {"ticker": "TEST"},
        "model_policy": {"primary": "fcff_dcf"},
        "financials": {
            "balance_sheet": {
                "bridge_complete": False,
                "bridge_missing_fields": ["commercial_paper"],
            }
        },
    }
    public = {
        "issuer": {"ticker": "TEST"},
        "model_policy": {"primary": "fcff_dcf"},
        "models": {
            "fcff_dcf": {
                "intrinsic_value_per_share": None,
                "publication_state": "withheld",
            }
        },
        "scenarios": {},
        "review": {"publication_state": "withheld"},
    }
    (stage / "recovery-result.json").write_text(
        json.dumps({"accepted": False, "reasons": ["bridge_incomplete"]})
    )
    (stage / "valuation-private.json").write_text(json.dumps(private))
    (stage / "valuation-public-candidate.json").write_text(json.dumps(public))

    target = quarantine_staged_candidate(
        "TEST", output_root=tmp_path / "stage", data_root=data
    )

    assert target == data / "TEST.json"
    assert json.loads(target.read_text()) == public
    assert "fallback_from" not in public["model_policy"]


def test_quarantine_refuses_candidate_that_exposes_a_value(tmp_path: Path):
    stage = tmp_path / "stage" / "TEST"
    data = tmp_path / "data"
    stage.mkdir(parents=True)
    data.mkdir()
    target = data / "TEST.json"
    target.write_text('{"preserved": true}')
    private = {
        "issuer": {"ticker": "TEST"},
        "model_policy": {"primary": "fcff_dcf"},
        "financials": {
            "balance_sheet": {
                "bridge_complete": False,
                "bridge_missing_fields": ["commercial_paper"],
            }
        },
    }
    public = {
        "issuer": {"ticker": "TEST"},
        "model_policy": {"primary": "fcff_dcf"},
        "models": {
            "fcff_dcf": {
                "intrinsic_value_per_share": 42.0,
                "publication_state": "withheld",
            }
        },
        "scenarios": {},
        "review": {"publication_state": "withheld"},
    }
    (stage / "recovery-result.json").write_text(
        json.dumps({"accepted": False, "reasons": ["bridge_incomplete"]})
    )
    (stage / "valuation-private.json").write_text(json.dumps(private))
    (stage / "valuation-public-candidate.json").write_text(json.dumps(public))

    with pytest.raises(ValueError, match="exposes intrinsic value"):
        quarantine_staged_candidate(
            "TEST", output_root=tmp_path / "stage", data_root=data
        )

    assert json.loads(target.read_text()) == {"preserved": True}


def test_technical_quarantine_removes_legacy_fallback_without_exposing_value(
    tmp_path: Path,
):
    data = tmp_path / "data"
    data.mkdir()
    artifact = _legacy_artifact(ticker="TEST")
    artifact["models"] = {
        "ddm": {
            "intrinsic_value_per_share": None,
            "publication_state": "withheld",
        }
    }
    artifact["scenarios"] = {}
    (data / "TEST.json").write_text(json.dumps(artifact))

    target = quarantine_technical_failure_artifact(
        "TEST",
        reason="technical_error:ValueError:Latest common shares outstanding are required",
        data_root=data,
    )

    result = json.loads(target.read_text())
    assert result["model_policy"]["primary"] == "fcff_dcf"
    assert "fallback_from" not in result["model_policy"]
    assert result["models"]["fcff_dcf"]["intrinsic_value_per_share"] is None
    assert result["review"]["publication_state"] == "withheld"
    assert result["review"]["confidence_grade"] == "insufficient"


def test_superseded_staging_overwrites_stale_accepted_value(tmp_path: Path):
    stage = tmp_path / "stage" / "TEST"
    data = tmp_path / "data"
    stage.mkdir(parents=True)
    data.mkdir()
    stale = {
        "issuer": {"ticker": "TEST"},
        "model_policy": {"primary": "fcff_dcf"},
        "models": {"fcff_dcf": {"intrinsic_value_per_share": 42.0}},
        "review": {"publication_state": "review_required"},
    }
    current = {
        "issuer": {"ticker": "TEST"},
        "model_policy": {"primary": "fcff_dcf"},
        "models": {"fcff_dcf": {"intrinsic_value_per_share": None}},
        "review": {"publication_state": "withheld"},
    }
    (stage / "valuation-private.json").write_text(json.dumps(stale))
    (stage / "valuation-public-candidate.json").write_text(json.dumps(stale))
    (stage / "recovery-result.json").write_text(
        json.dumps({"ticker": "TEST", "accepted": True, "reasons": []})
    )
    (data / "TEST.json").write_text(json.dumps(current))

    quarantine_superseded_staging(
        "TEST",
        reason="superseded_unsafe_inference",
        output_root=tmp_path / "stage",
        data_root=data,
    )

    assert json.loads((stage / "valuation-private.json").read_text()) == current
    assert json.loads((stage / "valuation-public-candidate.json").read_text()) == current
    result = json.loads((stage / "recovery-result.json").read_text())
    assert result["accepted"] is False
    assert result["reasons"] == ["superseded_unsafe_inference", "public_withheld"]
