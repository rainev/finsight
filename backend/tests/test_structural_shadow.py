"""Hermetic tests for the non-publishing structural XBRL shadow path."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

import app.us_valuation.structural_shadow as structural_shadow
from app.us_valuation.structural_shadow import (
    evaluate_shadow_case,
    shadow_requests_from_artifact,
)
from app.us_valuation.structural_xbrl import (
    ParseDiagnostic,
    StructuralFact,
    StructuralFiling,
    StructuralRelationship,
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
        "decimals": "0",
        "scale": None,
        "sign": None,
        "filing_form": "10-K",
        "filing_metadata": (("primary_document", "fsi-20251231.htm"),),
        "presentation_ancestry": ("us-gaap:AssetsCurrent",),
        "relationships": (
            StructuralRelationship(
                arcrole="http://www.xbrl.org/2003/arcrole/parent-child",
                linkrole="https://issuer.example/role/BalanceSheet",
                from_concept="us-gaap:AssetsCurrent",
                to_concept="fsi:LiquidInvestmentSecuritiesCurrent",
                order=1.0,
                preferred_label=None,
                calculation_weight=None,
            ),
        ),
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


SUPPORTED = {
    "marketable_securities_current",
    "marketable_securities_noncurrent",
    "commercial_paper",
    "current_debt",
    "noncurrent_debt",
    "finance_lease_current",
    "finance_lease_noncurrent",
    "finance_lease_total",
    "preferred_equity",
    "noncontrolling_interests",
}


def test_supported_structural_fields_are_the_governed_bridge_policies() -> None:
    assert structural_shadow.SUPPORTED_STRUCTURAL_FIELDS == SUPPORTED


@pytest.mark.parametrize("field", sorted(SUPPORTED))
def test_shadow_requests_every_supported_bridge_field_as_usd_balance_sheet(
    field: str,
) -> None:
    artifact = withheld_artifact(missing=[field, "unknown_bridge_field"])
    original = deepcopy(artifact)

    requests = shadow_requests_from_artifact(artifact)
    report = evaluate_shadow_case(artifact, structural_filing())

    assert artifact == original
    assert len(requests) == 1
    assert requests[0].normalized_concept == field
    assert requests[0].unit == "USD"
    assert requests[0].statement_role == "balance_sheet"
    assert len(report["decisions"]) == 1
    assert report["skipped_fields"] == ["unknown_bridge_field"]


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
        value=43_500_000,
    )

    report = evaluate_shadow_case(
        artifact,
        structural_filing(extension_fact(), alternative),
    )

    assert report["decisions"][0]["status"] == "rejected"
    assert report["decisions"][0]["reason_codes"] == ["AMBIGUOUS_FACTS"]


def test_shadow_case_stably_leaves_unsupported_form_unresolved() -> None:
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    artifact["financials"]["ttm"]["controlling_filing"]["form"] = "8-K"  # type: ignore[index]

    report = evaluate_shadow_case(
        artifact,
        StructuralFiling(
            source_accession=ACCESSION,
            period_end=PERIOD_END,
            facts=(),
            diagnostics=(),
            form="8-K",
        ),
    )

    assert report["decisions"][0]["status"] == "unresolved"
    assert report["decisions"][0]["reason_codes"] == ["INELIGIBLE_FILING_FORM"]
    assert report["decisions"][0]["form"] == "8-K"


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


def _load_shadow_cli() -> ModuleType:
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "run_structural_xbrl_shadow.py"
    )
    spec = importlib.util.spec_from_file_location("structural_shadow_cli_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_artifact(path: Path, artifact: dict[str, object]) -> bytes:
    encoded = json.dumps(artifact, indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(encoded)
    return encoded


def _install_cli_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    decision_by_ticker: dict[str, str],
    failing_accessions: frozenset[str] = frozenset(),
) -> dict[str, list[object]]:
    calls: dict[str, list[object]] = {"cache": [], "parse": []}

    class FakeSecClient:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    def cache_package(client: object, **kwargs: object) -> Path:
        calls["cache"].append(kwargs)
        return Path("/controlled-cache") / f"{kwargs['accession']}.htm"

    def parse_filing(entrypoint: Path, *, accession: str, form: str) -> object:
        calls["parse"].append((entrypoint, accession))
        if accession in failing_accessions:
            raise RuntimeError(f"controlled parser failure for {accession}")
        return object()

    def evaluate(artifact: dict[str, object], filing: object) -> dict[str, object]:
        ticker = str(artifact["ticker"])
        return {
            "ticker": ticker,
            "decisions": [{"status": decision_by_ticker[ticker]}],
            "publication_effect": "none_shadow_only",
        }

    fake_arelle = ModuleType("app.us_valuation.arelle_adapter")
    fake_arelle.parse_structural_filing = parse_filing  # type: ignore[attr-defined]
    fake_package = ModuleType("app.us_valuation.filing_package")
    fake_package.cache_structural_filing_package = cache_package  # type: ignore[attr-defined]
    fake_sec = ModuleType("app.us_valuation.sec_client")
    fake_sec.SecClient = FakeSecClient  # type: ignore[attr-defined]
    fake_shadow = ModuleType("app.us_valuation.structural_shadow")
    fake_shadow.SUPPORTED_STRUCTURAL_FIELDS = structural_shadow.SUPPORTED_STRUCTURAL_FIELDS  # type: ignore[attr-defined]
    fake_shadow.shadow_requests_from_artifact = shadow_requests_from_artifact  # type: ignore[attr-defined]
    fake_shadow.evaluate_shadow_case = evaluate  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.us_valuation.arelle_adapter", fake_arelle)
    monkeypatch.setitem(sys.modules, "app.us_valuation.filing_package", fake_package)
    monkeypatch.setitem(sys.modules, "app.us_valuation.sec_client", fake_sec)
    monkeypatch.setitem(sys.modules, "app.us_valuation.structural_shadow", fake_shadow)
    return calls


def test_shadow_cli_emits_immutable_reports_and_counts_all_decision_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "input"
    output_root = tmp_path / "output"
    cache_dir = tmp_path / "cache"
    data_root.mkdir()
    decision_by_ticker = {
        "ACPT": "accepted",
        "REVIEW": "review",
        "REJECT": "rejected",
        "UNRES": "unresolved",
    }
    original_inputs: dict[str, bytes] = {}
    for ticker in decision_by_ticker:
        artifact = withheld_artifact(missing=["marketable_securities_current"])
        artifact["ticker"] = ticker
        artifact["issuer"]["ticker"] = ticker  # type: ignore[index]
        original_inputs[ticker] = _write_artifact(data_root / f"{ticker}.json", artifact)
    missing_accession = withheld_artifact(
        missing=["marketable_securities_current"]
    )
    missing_accession["ticker"] = "BADACC"
    missing_accession["financials"]["ttm"]["controlling_filing"].pop(  # type: ignore[index]
        "accession"
    )
    original_inputs["BADACC"] = _write_artifact(
        data_root / "BADACC.json", missing_accession
    )
    malformed_period = withheld_artifact(
        missing=["marketable_securities_current"]
    )
    malformed_period["ticker"] = "BADPER"
    malformed_period["financials"]["ttm"]["period_end"] = "not-a-date"  # type: ignore[index]
    original_inputs["BADPER"] = _write_artifact(
        data_root / "BADPER.json", malformed_period
    )
    skipped = withheld_artifact(missing=["unknown_bridge_field"])
    skipped["ticker"] = "SKIP"
    original_inputs["SKIP"] = _write_artifact(data_root / "SKIP.json", skipped)
    calls = _install_cli_fakes(monkeypatch, decision_by_ticker=decision_by_ticker)
    cli = _load_shadow_cli()
    arguments = [
        "--data-root",
        str(data_root),
        "--cache-dir",
        str(cache_dir),
        "--output-root",
        str(output_root),
    ]

    assert cli.main(arguments) == 0
    report_bytes = {
        path.name: path.read_bytes() for path in output_root.glob("*.json")
    }
    report_mtimes = {
        path.name: path.stat().st_mtime_ns for path in output_root.glob("*.json")
    }
    assert len(calls["cache"]) == 4
    assert len(calls["parse"]) == 4
    assert cli.main(arguments) == 0

    assert len(calls["cache"]) == 8
    assert len(calls["parse"]) == 8
    assert report_bytes == {
        path.name: path.read_bytes() for path in output_root.glob("*.json")
    }
    assert report_mtimes == {
        path.name: path.stat().st_mtime_ns for path in output_root.glob("*.json")
    }
    assert all(
        (data_root / f"{ticker}.json").read_bytes() == contents
        for ticker, contents in original_inputs.items()
    )
    summary = json.loads((output_root / "summary.json").read_text())
    assert summary == {
        "accepted_shadow": 1,
        "discovered": 7,
        "eligible": 6,
        "parsed": 4,
        "parser_failed": 2,
        "rejected": 1,
        "review": 1,
        "skipped": 1,
        "unresolved": 1,
    }
    accession_failure = json.loads((output_root / "BADACC.json").read_text())
    assert accession_failure["decisions"] == []
    assert accession_failure["publication_effect"] == "none_shadow_only"
    assert "controlling accession is required" in accession_failure["parser_failure"]
    period_failure = json.loads((output_root / "BADPER.json").read_text())
    assert period_failure["decisions"] == []
    assert period_failure["publication_effect"] == "none_shadow_only"
    assert "period_end must be an ISO date" in period_failure["parser_failure"]


def test_shadow_cli_emits_immutable_parser_failure_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "input"
    output_root = tmp_path / "output"
    data_root.mkdir()
    failing_accession = "0000000000-26-000999"
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    artifact["ticker"] = "PARSE"
    artifact["issuer"]["ticker"] = "PARSE"  # type: ignore[index]
    artifact["financials"]["ttm"]["controlling_filing"][  # type: ignore[index]
        "accession"
    ] = failing_accession
    original = _write_artifact(data_root / "PARSE.json", artifact)
    frontend_target = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "public"
        / "data"
        / "PARSE.json"
    )
    frontend_before = (
        frontend_target.read_bytes() if frontend_target.exists() else None
    )
    calls = _install_cli_fakes(
        monkeypatch,
        decision_by_ticker={},
        failing_accessions=frozenset({failing_accession}),
    )
    cli = _load_shadow_cli()

    assert cli.main(
        [
            "--data-root",
            str(data_root),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--output-root",
            str(output_root),
        ]
    ) == 0

    assert len(calls["cache"]) == 1
    assert len(calls["parse"]) == 1
    assert (data_root / "PARSE.json").read_bytes() == original
    if frontend_before is None:
        assert not frontend_target.exists()
    else:
        assert frontend_target.read_bytes() == frontend_before
    summary = json.loads((output_root / "summary.json").read_text())
    assert summary == {
        "accepted_shadow": 0,
        "discovered": 1,
        "eligible": 1,
        "parsed": 0,
        "parser_failed": 1,
        "rejected": 0,
        "review": 0,
        "skipped": 0,
        "unresolved": 0,
    }
    failure = json.loads((output_root / "PARSE.json").read_text())
    assert failure["decisions"] == []
    assert failure["publication_effect"] == "none_shadow_only"
    assert failure["parser_failure"] == (
        f"controlled parser failure for {failing_accession}"
    )


@pytest.mark.parametrize(
    "protected_output",
    [
        Path(__file__).resolve().parents[1] / "app" / "data" / "us_valuations",
        Path(__file__).resolve().parents[2] / "frontend" / "public" / "data",
    ],
)
def test_shadow_cli_rejects_project_data_roots_with_custom_input(
    tmp_path: Path, protected_output: Path
) -> None:
    cli = _load_shadow_cli()
    data_root = tmp_path / "custom-input"
    data_root.mkdir()

    with pytest.raises(ValueError, match="protected"):
        cli.main(
            [
                "--data-root",
                str(data_root),
                "--cache-dir",
                str(tmp_path / "cache"),
                "--output-root",
                str(protected_output),
            ]
        )


@pytest.mark.parametrize("writable_option", ["--cache-dir", "--output-root"])
@pytest.mark.parametrize("alias_kind", ["direct", "descendant", "dotdot", "symlink"])
def test_shadow_cli_protects_every_writable_root_alias_before_imports(
    tmp_path: Path,
    writable_option: str,
    alias_kind: str,
) -> None:
    cli = _load_shadow_cli()
    data_root = tmp_path / "input"
    data_root.mkdir()
    if alias_kind == "direct":
        protected_alias = data_root
    elif alias_kind == "descendant":
        protected_alias = data_root / "child"
    elif alias_kind == "dotdot":
        protected_alias = data_root / "child" / ".."
    else:
        protected_alias = tmp_path / "data-alias"
        protected_alias.symlink_to(data_root, target_is_directory=True)
    cache_dir = tmp_path / "safe-cache"
    output_root = tmp_path / "safe-output"
    if writable_option == "--cache-dir":
        cache_dir = protected_alias
    else:
        output_root = protected_alias

    with pytest.raises(ValueError, match="protected"):
        cli.main(
            [
                "--data-root",
                str(data_root),
                "--cache-dir",
                str(cache_dir),
                "--output-root",
                str(output_root),
            ]
        )

    assert not list(data_root.rglob("*.json"))


@pytest.mark.parametrize("invalid_ticker", ["../escape", "nested/escape", "fsi"])
def test_shadow_cli_rejects_noncanonical_ticker_without_escaping_output_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_ticker: str,
) -> None:
    data_root = tmp_path / "input"
    data_root.mkdir()
    artifact = withheld_artifact(missing=["marketable_securities_current"])
    artifact["ticker"] = invalid_ticker
    _write_artifact(data_root / "malicious.json", artifact)
    _install_cli_fakes(
        monkeypatch, decision_by_ticker={invalid_ticker: "accepted"}
    )
    cli = _load_shadow_cli()
    output_root = tmp_path / "output"

    with pytest.raises(ValueError, match="ticker"):
        cli.main(
            [
                "--data-root",
                str(data_root),
                "--cache-dir",
                str(tmp_path / "cache"),
                "--output-root",
                str(output_root),
            ]
        )

    assert not (tmp_path / "escape.json").exists()
    assert not output_root.exists()
