"""Hermetic tests for the non-publishing structural XBRL shadow path."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest

from app.us_valuation.structural_shadow import (
    evaluate_shadow_case,
    shadow_requests_from_artifact,
)
from app.us_valuation.structural_xbrl import (
    ParseDiagnostic,
    StructuralFact,
    StructuralFiling,
)


ACCESSION = "0000000000-26-000001"
PERIOD_END = "2025-12-31"


def withheld_artifact(*, missing: list[str]) -> dict[str, object]:
    return {
        "ticker": "FSI",
        "valuation_date": "2026-08-01",
        "issuer": {"cik": "0000000001", "ticker": "FSI"},
        "review": {"publication_state": "withheld"},
        "financials": {
            "ttm": {
                "period_end": PERIOD_END,
                "controlling_filing": {
                    "accession": ACCESSION,
                    "form": "10-K",
                    "primary_document": "fsi-20251231.htm",
                },
            },
            "balance_sheet": {
                "bridge_missing_fields": missing,
                "field_states": {field: "missing" for field in missing},
            },
        },
    }


def extension_fact(**overrides: object) -> StructuralFact:
    values: dict[str, object] = {
        "qname": "fsi:LiquidInvestmentSecuritiesCurrent",
        "namespace": "https://issuer.example/fsi/2025",
        "local_name": "LiquidInvestmentSecuritiesCurrent",
        "labels": (("standard", "Liquid investment securities"),),
        "documentation": "Available-for-sale debt securities classified as current.",
        "value": 42_500_000,
        "unit": "USD",
        "period_start": None,
        "period_end": PERIOD_END,
        "context_id": "CurrentYearInstant",
        "dimensions": (),
        "statement_roles": ("balance_sheet",),
        "presentation_parents": ("us-gaap:AssetsCurrent",),
        "calculation_parents": ("us-gaap:AssetsCurrent",),
        "calculation_children": (),
        "definition_parents": ("us-gaap:ShortTermInvestments",),
        "definition_children": (),
        "source_accession": ACCESSION,
    }
    values.update(overrides)
    return StructuralFact(**values)  # type: ignore[arg-type]


def structural_filing(*facts: StructuralFact, diagnostics: tuple[ParseDiagnostic, ...] = ()) -> StructuralFiling:
    return StructuralFiling(
        source_accession=ACCESSION,
        period_end=PERIOD_END,
        facts=facts,
        diagnostics=diagnostics,
        form="10-K",
    )


def test_shadow_case_emits_candidate_without_mutating_artifact() -> None:
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    original = deepcopy(artifact)

    report = evaluate_shadow_case(artifact, structural_filing(extension_fact()))

    assert artifact == original
    assert report["publication_effect"] == "none_shadow_only"
    assert report["decisions"][0]["status"] == "accepted"
    assert report["decisions"][0]["normalized_concept"] == "marketable_securities_current"


def test_shadow_case_ignores_non_marketability_bridge_fields() -> None:
    artifact = withheld_artifact(missing=["commercial_paper"])

    report = evaluate_shadow_case(artifact, structural_filing())

    assert report["decisions"] == []
    assert report["skipped_fields"] == ["commercial_paper"]


def test_shadow_requests_require_controlling_accession() -> None:
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    artifact["financials"]["ttm"]["controlling_filing"].pop("accession")  # type: ignore[index]

    with pytest.raises(ValueError, match="controlling accession"):
        shadow_requests_from_artifact(artifact)


def test_shadow_case_reports_rejected_period_mismatch() -> None:
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    mismatched = extension_fact(period_end="2025-09-30")

    report = evaluate_shadow_case(artifact, structural_filing(mismatched))

    assert report["decisions"][0]["status"] == "rejected"
    assert report["decisions"][0]["reason_codes"] == ["PERIOD_MISMATCH"]


def test_shadow_case_includes_parser_diagnostics_and_review_candidate() -> None:
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    diagnostic = ParseDiagnostic(
        code="relationship_warning",
        message="presentation relationship incomplete",
        severity="warning",
        context=(("role", "balance_sheet"),),
    )
    review_fact = extension_fact(calculation_parents=())

    report = evaluate_shadow_case(
        artifact,
        structural_filing(review_fact, diagnostics=(diagnostic,)),
    )

    assert report["decisions"][0]["status"] == "review"
    assert report["parser_diagnostics"] == [
        {
            "code": "relationship_warning",
            "message": "presentation relationship incomplete",
            "severity": "warning",
            "context": [["role", "balance_sheet"]],
        }
    ]


def test_shadow_case_reports_rejected_ambiguous_candidates() -> None:
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    alternative = extension_fact(
        qname="fsi:OtherLiquidInvestmentSecuritiesCurrent",
        local_name="OtherLiquidInvestmentSecuritiesCurrent",
    )

    report = evaluate_shadow_case(
        artifact,
        structural_filing(extension_fact(), alternative),
    )

    assert report["decisions"][0]["status"] == "rejected"
    assert report["decisions"][0]["reason_codes"] == ["AMBIGUOUS_FACTS"]


def test_shadow_cli_help_is_available_without_running_arelle() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "run_structural_xbrl_shadow.py"

    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0
    assert "--data-root" in completed.stdout
    assert "--cache-dir" in completed.stdout
    assert "--output-root" in completed.stdout
