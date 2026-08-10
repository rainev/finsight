from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.us_valuation.arelle_adapter import (
    ArelleParseError,
    ArelleParseTimeout,
    ArelleUnavailable,
    parse_structural_filing,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "us" / "structural-xbrl"
ENTRYPOINT = FIXTURE_ROOT / "fsi-20251231.htm"
ACCESSION = "0000000000-26-000001"


def test_arelle_adapter_extracts_extension_structure() -> None:
    filing = parse_structural_filing(ENTRYPOINT, accession=ACCESSION)

    current = next(
        fact for fact in filing.facts if fact.local_name == "LiquidInvestmentSecuritiesCurrent"
    )
    assert current.value == 42_500_000
    assert current.unit == "USD"
    assert current.period_start is None
    assert current.period_end == "2025-12-31"
    assert current.context_id == "CurrentYearInstant"
    assert current.statement_roles == ("balance_sheet",)
    assert "us-gaap:AssetsCurrent" in current.presentation_parents
    assert "us-gaap:AssetsCurrent" in current.calculation_parents
    assert "us-gaap:ShortTermInvestments" in current.definition_parents
    assert "available-for-sale" in (current.documentation or "").lower()
    assert current.labels
    assert all(isinstance(label, tuple) for label in current.labels)
    assert filing.source_accession == ACCESSION
    assert filing.period_end == "2025-12-31"


def test_arelle_adapter_bootstraps_worker_when_parent_cwd_is_repository_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[2].parent)

    filing = parse_structural_filing(ENTRYPOINT, accession=ACCESSION)

    assert len(filing.facts) == 3


def test_arelle_adapter_extracts_all_representative_facts_and_relationships() -> None:
    filing = parse_structural_filing(ENTRYPOINT, accession=ACCESSION)
    facts = {fact.local_name: fact for fact in filing.facts}

    assert facts["LiquidInvestmentSecuritiesNoncurrent"].value == 8_000_000
    assert facts["LiquidInvestmentSecuritiesNoncurrent"].unit == "USD"
    assert "us-gaap:AssetsNoncurrent" in facts[
        "LiquidInvestmentSecuritiesNoncurrent"
    ].presentation_parents
    assert "us-gaap:AssetsNoncurrent" in facts[
        "LiquidInvestmentSecuritiesNoncurrent"
    ].calculation_parents
    assert "us-gaap:LongTermInvestments" in facts[
        "LiquidInvestmentSecuritiesNoncurrent"
    ].definition_parents

    strategic = facts["StrategicEquityInvestments"]
    assert strategic.value == 70_000_000
    assert strategic.unit == "USD"
    assert strategic.context_id == "CurrentYearInstant"
    assert strategic.statement_roles == ("balance_sheet",)
    assert "strategic nonmarketable equity investments" in (
        strategic.documentation or ""
    ).lower()

    assert {fact.qname for fact in filing.facts} >= {
        "fsi:LiquidInvestmentSecuritiesCurrent",
        "fsi:LiquidInvestmentSecuritiesNoncurrent",
        "fsi:StrategicEquityInvestments",
    }
    assert all(not type(fact).__module__.startswith("arelle") for fact in filing.facts)


def test_arelle_adapter_uses_worker_json_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_path = Path(command[command.index("--output") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "source_accession": ACCESSION,
                    "period_end": "2025-12-31",
                    "facts": [
                        {
                            "qname": "fsi:TestFact",
                            "namespace": "https://example.test/fsi/2025",
                            "local_name": "TestFact",
                            "labels": [["standard", "Test fact"]],
                            "documentation": None,
                            "value": 1.0,
                            "unit": "USD",
                            "period_start": None,
                            "period_end": "2025-12-31",
                            "context_id": "CurrentYearInstant",
                            "dimensions": [],
                            "statement_roles": ["balance_sheet"],
                            "presentation_parents": [],
                            "calculation_parents": [],
                            "calculation_children": [],
                            "definition_parents": [],
                            "definition_children": [],
                            "source_accession": ACCESSION,
                        }
                    ],
                    "diagnostics": [],
                    "form": "10-K",
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)

    filing = parse_structural_filing(ENTRYPOINT, accession=ACCESSION)

    command = captured["command"]
    assert isinstance(command, list)
    assert command[1:4] == ["-m", "app.us_valuation.arelle_worker", "--entrypoint"]
    assert "--accession" in command
    assert "--output" in command
    assert captured["kwargs"]["timeout"] == 120  # type: ignore[index]
    assert filing.facts[0].qname == "fsi:TestFact"


def test_arelle_adapter_converts_timeout_to_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ArelleParseTimeout):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION, timeout_seconds=1)


def test_arelle_adapter_reports_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args[0], 1, "", "ModuleNotFoundError: No module named 'arelle'"
        )

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ArelleUnavailable, match="Arelle"):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION)


def test_arelle_adapter_reports_nonzero_worker_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 2, "", "fatal parse error")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ArelleParseError, match="fatal parse error"):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION)


def test_arelle_adapter_does_not_misclassify_worker_bootstrap_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 1, "", "ModuleNotFoundError: No module named 'app'")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ArelleParseError, match="No module named 'app'"):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION)


def test_arelle_adapter_reports_malformed_worker_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        output_path = Path(args[0][args[0].index("--output") + 1])
        output_path.write_text("not-json", encoding="utf-8")
        return subprocess.CompletedProcess(args[0], 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ArelleParseError, match="JSON"):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION)


def test_arelle_adapter_reports_empty_fact_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        output_path = Path(args[0][args[0].index("--output") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "source_accession": ACCESSION,
                    "period_end": "2025-12-31",
                    "facts": [],
                    "diagnostics": [],
                    "form": "10-K",
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args[0], 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ArelleParseError, match="no facts"):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION)


def test_parent_adapter_module_does_not_import_arelle() -> None:
    import sys

    assert "arelle" not in sys.modules
