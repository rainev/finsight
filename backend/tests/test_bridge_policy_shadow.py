from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

from app.us_valuation.bridge_policy import (
    assess_bridge_materiality,
    reconcile_bridge,
)
from app.us_valuation.bridge_policy_shadow import (
    ArtifactEvaluationError,
    evaluate_corpus,
    evaluate_private_artifact,
)
from app.us_valuation.field_availability import (
    FieldAvailability,
    UncertaintyRange,
    availability_from_normalized_field,
)


PERIOD_END = "2026-06-30"
ACCESSION = "0000000000-26-000001"
REPO_ROOT = Path(__file__).resolve().parents[2]
SHADOW_SCRIPT = REPO_ROOT / "scripts" / "run_bridge_policy_shadow.py"
LEASE_COMPONENTS = ("finance_lease_current", "finance_lease_noncurrent")
BRIDGE_FIELDS = (
    "cash",
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
)


def legacy_private_artifact(ticker: str = "TEST") -> dict[str, Any]:
    values: dict[str, float | None] = {
        "cash": 100.0,
        "marketable_securities_current": 20.0,
        "marketable_securities_noncurrent": 5.0,
        "commercial_paper": 0.0,
        "current_debt": 10.0,
        "noncurrent_debt": 40.0,
        "finance_lease_current": 2.0,
        "finance_lease_noncurrent": 8.0,
        "finance_lease_total": 10.0,
        "preferred_equity": 0.0,
        "noncontrolling_interests": 1.0,
        "common_shares_outstanding": 10.0,
        "diluted_weighted_average_shares": 10.0,
        "incremental_dilutive_shares": 0.0,
    }
    states = {field: "reported" for field in values}
    sources = {
        field: {
            "accession": ACCESSION,
            "value_status": "reported",
            "value": value,
        }
        for field, value in values.items()
    }
    return {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "issuer": {"ticker": ticker, "cik": "0000000000"},
        "financial_period_end": PERIOD_END,
        "financials": {
            "ttm": {
                "period_end": PERIOD_END,
                "controlling_filing": {
                    "accession": ACCESSION,
                    "form": "10-Q",
                },
            },
            "balance_sheet": {
                "period_end": PERIOD_END,
                "values": values,
                "sources": sources,
                "field_states": states,
                "fully_diluted_shares_proxy": 10.0,
                "bridge_complete": True,
                "bridge_missing_fields": [],
                "total_interest_bearing_debt": 60.0,
            },
        },
        "review": {"publication_state": "review_required"},
    }


def block_legacy_field(
    artifact: dict[str, Any], field: str, *, state: str = "missing"
) -> None:
    balance = artifact["financials"]["balance_sheet"]
    balance["values"][field] = None
    balance["sources"][field] = None
    balance["field_states"][field] = state
    balance["bridge_complete"] = False
    balance["bridge_missing_fields"] = [field]


def legacy_availability(artifact: dict[str, Any]) -> dict[str, FieldAvailability]:
    balance = artifact["financials"]["balance_sheet"]
    return {
        field: availability_from_normalized_field(
            field=field,
            value=value,
            source=balance["sources"][field],
            legacy_state=balance["field_states"][field],
            period_end=balance["period_end"],
            covered_fields=LEASE_COMPONENTS if field == "finance_lease_total" else (),
            reference_date=balance["period_end"],
        )
        for field, value in balance["values"].items()
    }


def modern_private_artifact(ticker: str = "MODERN") -> dict[str, Any]:
    artifact = legacy_private_artifact(ticker)
    balance = artifact["financials"]["balance_sheet"]
    availability = legacy_availability(artifact)
    resolution = reconcile_bridge(
        availability,
        fully_diluted_shares=balance["fully_diluted_shares_proxy"],
    )
    balance["availability"] = {
        field: record.as_dict() for field, record in availability.items()
    }
    balance.update(resolution.as_balance_sheet_fields())
    balance["bridge_uncertainty"] = assess_bridge_materiality(
        resolution,
        enterprise_value=1_000.0,
    ).as_dict()
    return artifact


def write_private(path: Path, artifact: dict[str, Any]) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(artifact, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(encoded)
    return encoded


def run_shadow_cli(
    input_root: Path,
    output_dir: Path,
    *,
    tickers: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SHADOW_SCRIPT),
        "--input-root",
        str(input_root),
        "--output-dir",
        str(output_dir),
    ]
    if tickers is not None:
        command.extend(("--tickers", tickers))
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def load_shadow_cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bridge_policy_shadow_cli_test", SHADOW_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_evaluator_reconstructs_source_evidence_without_mutation() -> None:
    artifact = legacy_private_artifact()
    block_legacy_field(artifact, "commercial_paper")
    original = deepcopy(artifact)

    report = evaluate_private_artifact(artifact)

    assert artifact == original
    assert report["ticker"] == "TEST"
    assert report["financial_period_end"] == PERIOD_END
    assert report["source_schema"] == "legacy"
    assert report["legacy"] == {
        "bridge_complete": False,
        "bridge_missing_fields": ["commercial_paper"],
    }
    assert report["evidence_aware"]["decision"] == "withheld"
    assert report["evidence_aware"]["blocking_fields"] == ["commercial_paper"]
    assert report["field_evidence"]["commercial_paper"] == {
        "authority": "production",
        "covered_fields": [],
        "period_end": PERIOD_END,
        "reason_code": "UNRESOLVED_UNSPECIFIED",
        "source_accession": None,
        "state": "unresolved",
    }
    assert report["serving_artifact_changed"] is False


def test_legacy_lease_total_is_counted_once_with_matching_split() -> None:
    report = evaluate_private_artifact(legacy_private_artifact())

    assert report["evidence_aware"]["decision"] == "complete"
    assert report["evidence_aware"]["recomputed_precheck"]["total_debt"] == {
        "low": 60.0,
        "midpoint": 60.0,
        "high": 60.0,
    }


def test_legacy_compatibility_total_debt_alias_is_never_synthesized_as_evidence() -> None:
    artifact = legacy_private_artifact()
    for field in (
        "commercial_paper",
        "current_debt",
        "noncurrent_debt",
        "finance_lease_current",
        "finance_lease_noncurrent",
        "finance_lease_total",
    ):
        block_legacy_field(artifact, field)
    artifact["financials"]["balance_sheet"]["total_interest_bearing_debt"] = 60.0

    report = evaluate_private_artifact(artifact)

    assert report["evidence_aware"]["decision"] == "withheld"
    assert "total_interest_bearing_debt" not in report["field_evidence"]
    assert report["evidence_aware"]["blocking_fields"] == [
        "commercial_paper",
        "current_debt",
        "finance_lease_current",
        "finance_lease_noncurrent",
        "noncurrent_debt",
    ]


def test_modern_evaluator_recomputes_and_requires_stored_precheck_equality() -> None:
    artifact = modern_private_artifact()

    report = evaluate_private_artifact(artifact)

    assert report["source_schema"] == "modern"
    assert report["stored_precheck_match"] is True
    assert report["evidence_aware"]["decision"] == "complete"
    assert report["bridge_uncertainty"]["decision"] == "complete"


def test_modern_stored_precheck_mismatch_fails_closed() -> None:
    artifact = modern_private_artifact()
    artifact["financials"]["balance_sheet"]["bridge_precheck"][
        "reason_codes"
    ] = ["FORGED_REASON"]

    report = evaluate_private_artifact(artifact)

    assert report["stored_precheck_match"] is False
    assert report["evidence_aware"]["complete"] is False
    assert report["evidence_aware"]["can_value"] is False
    assert report["evidence_aware"]["decision"] == "withheld"
    assert report["evidence_aware"]["reason_codes"] == [
        "BRIDGE_PRECHECK_MISMATCH"
    ]


def test_modern_precheck_requires_exact_canonical_serialization() -> None:
    artifact = modern_private_artifact("PRECHECK")
    artifact["financials"]["balance_sheet"]["bridge_precheck"][
        "unexpected"
    ] = True

    report = evaluate_private_artifact(artifact)

    assert report["stored_precheck_match"] is False
    assert report["evidence_aware"]["decision"] == "withheld"
    assert report["evidence_aware"]["reason_codes"] == [
        "BRIDGE_PRECHECK_MISMATCH"
    ]


def test_precheck_mismatch_precedes_malformed_assessment() -> None:
    artifact = modern_private_artifact("PRECEDENCE")
    balance = artifact["financials"]["balance_sheet"]
    balance["bridge_precheck"]["unexpected"] = True
    balance["bridge_uncertainty"]["unexpected"] = True

    report = evaluate_private_artifact(artifact)

    assert report["stored_precheck_match"] is False
    assert report["bridge_uncertainty"] is None
    assert report["evidence_aware"]["decision"] == "withheld"
    assert report["evidence_aware"]["reason_codes"] == [
        "BRIDGE_PRECHECK_MISMATCH"
    ]


def test_modern_availability_requires_exact_canonical_serialization() -> None:
    artifact = modern_private_artifact("AVAIL")
    artifact["financials"]["balance_sheet"]["availability"]["cash"][
        "unexpected"
    ] = True

    with pytest.raises(ArtifactEvaluationError) as captured:
        evaluate_private_artifact(artifact)

    assert captured.value.reason_code == "AVAILABILITY_INVALID"


def test_modern_assessment_requires_exact_canonical_serialization() -> None:
    artifact = modern_private_artifact("ASSESS")
    artifact["financials"]["balance_sheet"]["bridge_uncertainty"][
        "unexpected"
    ] = True

    with pytest.raises(ArtifactEvaluationError) as captured:
        evaluate_private_artifact(artifact)

    assert captured.value.reason_code == "BRIDGE_ASSESSMENT_INVALID"


def test_modern_bounded_candidate_stays_diagnostic_only() -> None:
    artifact = modern_private_artifact("BOUND")
    balance = artifact["financials"]["balance_sheet"]
    availability = {
        field: FieldAvailability.from_dict(payload)
        for field, payload in balance["availability"].items()
    }
    availability["marketable_securities_noncurrent"] = FieldAvailability(
        field="marketable_securities_noncurrent",
        value=None,
        state="bounded_unresolved",
        reason_code="CURRENT_NOTE_SUPPLIES_FINITE_RANGE",
        period_end=PERIOD_END,
        source_accession=ACCESSION,
        source_kind="filing_investments_note",
        evidence_class="reported_range",
        freshness="current",
        uncertainty=UncertaintyRange(
            low=4.9,
            high=5.1,
            basis="Current filing note bounds the undisclosed balance.",
            source_accessions=(ACCESSION,),
        ),
    )
    resolution = reconcile_bridge(availability, fully_diluted_shares=10.0)
    balance["availability"] = {
        field: record.as_dict() for field, record in availability.items()
    }
    balance.update(resolution.as_balance_sheet_fields())
    balance["bridge_uncertainty"] = assess_bridge_materiality(
        resolution,
        enterprise_value=1_000.0,
    ).as_dict()

    report = evaluate_private_artifact(artifact)

    assert report["evidence_aware"]["decision"] == "bounded_candidate"
    assert report["evidence_aware"]["complete"] is False
    assert report["evidence_aware"]["can_value"] is True
    assert report["evidence_aware"]["bounded_fields"] == [
        "marketable_securities_noncurrent"
    ]
    assert report["bridge_uncertainty"]["decision"] == "bounded_review"
    assert report["serving_artifact_changed"] is False


def test_structural_candidate_presence_requires_explicit_shadow_diagnostics() -> None:
    artifact = legacy_private_artifact("SHADOW")
    artifact["unrelated"] = {"availability_candidate": {"authority": "shadow"}}
    assert (
        evaluate_private_artifact(artifact)[
            "structural_shadow_candidate_present"
        ]
        is False
    )

    artifact["structural_shadow_diagnostics"] = {
        "publication_effect": "none_shadow_only",
        "decisions": [
            {"availability_candidate": {"authority": "shadow"}}
        ],
    }

    report = evaluate_private_artifact(artifact)
    assert report["structural_shadow_candidate_present"] is True
    assert report["evidence_aware"]["decision"] == "complete"
    assert report["serving_artifact_changed"] is False


def test_corpus_counts_each_valid_input_once_and_sorts_cases(tmp_path: Path) -> None:
    original_b = write_private(
        tmp_path / "z-source" / "valuation-private.json",
        legacy_private_artifact("B"),
    )
    original_a = write_private(
        tmp_path / "a-source" / "valuation-private.json",
        legacy_private_artifact("A"),
    )

    summary = evaluate_corpus(tmp_path)

    assert summary["artifact_count"] == 2
    assert summary["valid_artifact_count"] == 2
    assert summary["invalid_artifact_count"] == 0
    assert summary["decision_counts"] == {
        "bounded_candidate": 0,
        "complete": 2,
        "withheld": 0,
    }
    assert summary["serving_artifacts_changed"] == 0
    assert summary["evidence_gate_passed"] is True
    assert [case["ticker"] for case in summary["cases"]] == ["A", "B"]
    assert [case["source_path"] for case in summary["cases"]] == [
        "a-source/valuation-private.json",
        "z-source/valuation-private.json",
    ]
    assert (tmp_path / "a-source" / "valuation-private.json").read_bytes() == original_a
    assert (tmp_path / "z-source" / "valuation-private.json").read_bytes() == original_b


def test_corpus_counts_malformed_nonobject_and_nonprivate_inputs(tmp_path: Path) -> None:
    malformed = tmp_path / "MALFORMED" / "valuation-private.json"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("{not-json\n", encoding="utf-8")
    nonobject = tmp_path / "NONOBJECT" / "valuation-private.json"
    nonobject.parent.mkdir(parents=True)
    nonobject.write_text("[]\n", encoding="utf-8")
    public = legacy_private_artifact("PUBLIC")
    public["schema_version"] = "US-PUBLIC-VALUATION-1.0"
    public["financials"] = None
    write_private(tmp_path / "PUBLIC" / "valuation-private.json", public)

    summary = evaluate_corpus(tmp_path)

    assert summary["artifact_count"] == 3
    assert summary["valid_artifact_count"] == 0
    assert summary["invalid_artifact_count"] == 3
    assert summary["decision_counts"] == {
        "bounded_candidate": 0,
        "complete": 0,
        "withheld": 3,
    }
    assert summary["evidence_gate_passed"] is False
    assert [case["ticker"] for case in summary["cases"]] == [
        "MALFORMED",
        "NONOBJECT",
        "PUBLIC",
    ]
    assert [case["error"]["reason_code"] for case in summary["cases"]] == [
        "MALFORMED_JSON",
        "PRIVATE_ARTIFACT_NOT_OBJECT",
        "NOT_PRIVATE_VALUATION_ARTIFACT",
    ]


def test_corpus_counts_dangling_candidate_symlink_as_read_error(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "DANGLING" / "valuation-private.json"
    candidate.parent.mkdir(parents=True)
    candidate.symlink_to(tmp_path / "missing-private-artifact.json")

    summary = evaluate_corpus(tmp_path)

    assert summary["artifact_count"] == 1
    assert summary["valid_artifact_count"] == 0
    assert summary["invalid_artifact_count"] == 1
    assert summary["decision_counts"]["withheld"] == 1
    assert summary["evidence_gate_passed"] is False
    assert summary["cases"][0]["error"]["reason_code"] == "INPUT_READ_ERROR"


def test_duplicate_tickers_are_preserved_and_all_fail_closed(tmp_path: Path) -> None:
    write_private(
        tmp_path / "first" / "valuation-private.json",
        legacy_private_artifact("DUP"),
    )
    write_private(
        tmp_path / "second" / "valuation-private.json",
        legacy_private_artifact("DUP"),
    )

    summary = evaluate_corpus(tmp_path)

    assert summary["artifact_count"] == 2
    assert summary["valid_artifact_count"] == 0
    assert summary["invalid_artifact_count"] == 2
    assert summary["duplicate_tickers"] == ["DUP"]
    assert len(summary["cases"]) == 2
    assert all(case["ticker"] == "DUP" for case in summary["cases"])
    assert all(
        case["evidence_aware"]["decision"] == "withheld"
        and case["evidence_aware"]["reason_codes"] == ["DUPLICATE_TICKER"]
        and case["error"]["reason_code"] == "DUPLICATE_TICKER"
        for case in summary["cases"]
    )


def test_requested_tickers_report_matches_and_missing_without_fabrication(
    tmp_path: Path,
) -> None:
    write_private(
        tmp_path / "A" / "valuation-private.json", legacy_private_artifact("A")
    )
    write_private(
        tmp_path / "B" / "valuation-private.json", legacy_private_artifact("B")
    )
    write_private(
        tmp_path / "C" / "valuation-private.json", legacy_private_artifact("C")
    )

    summary = evaluate_corpus(tmp_path, tickers=("MISSING", "B", "A", "A"))

    assert summary["requested_tickers"] == ["A", "B", "MISSING"]
    assert summary["matched_tickers"] == ["A", "B"]
    assert summary["missing_tickers"] == ["MISSING"]
    assert summary["artifact_count"] == 2
    assert [case["ticker"] for case in summary["cases"]] == ["A", "B"]
    assert summary["evidence_gate_passed"] is False


def test_policy_validation_mismatch_is_counted_as_invalid_withheld(
    tmp_path: Path,
) -> None:
    artifact = modern_private_artifact("MISMATCH")
    artifact["financials"]["balance_sheet"]["bridge_precheck"][
        "reason_codes"
    ] = ["FORGED_REASON"]
    write_private(tmp_path / "MISMATCH" / "valuation-private.json", artifact)

    summary = evaluate_corpus(tmp_path)

    assert summary["artifact_count"] == 1
    assert summary["valid_artifact_count"] == 0
    assert summary["invalid_artifact_count"] == 1
    assert summary["decision_counts"]["withheld"] == 1
    assert summary["cases"][0]["error"]["reason_code"] == (
        "BRIDGE_PRECHECK_MISMATCH"
    )


@pytest.mark.parametrize("ticker", ["", "lower", "BAD TICKER"])
def test_requested_tickers_must_be_canonical(tmp_path: Path, ticker: str) -> None:
    with pytest.raises(ValueError, match="canonical uppercase"):
        evaluate_corpus(tmp_path, tickers=(ticker,))


def test_cli_help_is_available_without_loading_arelle() -> None:
    completed = subprocess.run(
        [sys.executable, str(SHADOW_SCRIPT), "--help"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--input-root" in completed.stdout
    assert "--output-dir" in completed.stdout
    assert "--tickers" in completed.stdout
    assert "arelle" not in completed.stderr.lower()


def test_normal_cli_run_neither_imports_arelle_nor_opens_network(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "input"
    output_dir = tmp_path / "output"
    blocker_root = tmp_path / "runtime-blockers"
    blocker_root.mkdir()
    write_private(
        input_root / "TEST" / "valuation-private.json",
        legacy_private_artifact("TEST"),
    )
    (blocker_root / "sitecustomize.py").write_text(
        """import builtins
import socket

_original_import = builtins.__import__

def _guarded_import(name, *args, **kwargs):
    if name.lower().startswith("arelle"):
        raise RuntimeError("Arelle import blocked by Task 8 test")
    return _original_import(name, *args, **kwargs)

def _blocked_network(*args, **kwargs):
    raise RuntimeError("network blocked by Task 8 test")

builtins.__import__ = _guarded_import
socket.create_connection = _blocked_network
socket.socket.connect = _blocked_network
""",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(blocker_root), environment.get("PYTHONPATH")))
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SHADOW_SCRIPT),
            "--input-root",
            str(input_root),
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    assert (output_dir / "bridge-policy-shadow.json").exists()
    assert (output_dir / "bridge-policy-shadow.md").exists()


def test_cli_writes_deterministic_json_and_markdown_only(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    output_dir = tmp_path / "output"
    write_private(
        input_root / "TEST" / "valuation-private.json",
        legacy_private_artifact("TEST"),
    )

    completed = run_shadow_cli(input_root, output_dir)

    assert completed.returncode == 0, completed.stderr
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "bridge-policy-shadow.json",
        "bridge-policy-shadow.md",
    ]
    summary = json.loads(
        (output_dir / "bridge-policy-shadow.json").read_text(encoding="utf-8")
    )
    assert summary["artifact_count"] == 1
    assert summary["evidence_gate_passed"] is True
    markdown = (output_dir / "bridge-policy-shadow.md").read_text(
        encoding="utf-8"
    )
    assert "- Artifact candidates: 1" in markdown
    assert (
        "- Decision counts: bounded_candidate=0, complete=1, withheld=0"
        in markdown
    )
    assert "- Evidence gate passed: true" in markdown
    assert (
        "| TEST | TEST/valuation-private.json | — | — | — | complete | — |"
        in markdown
    )


def test_cli_writes_diagnostics_then_exits_nonzero_for_missing_ticker(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "input"
    output_dir = tmp_path / "output"
    write_private(
        input_root / "TEST" / "valuation-private.json",
        legacy_private_artifact("TEST"),
    )

    completed = run_shadow_cli(
        input_root,
        output_dir,
        tickers="TEST,MISSING",
    )

    assert completed.returncode == 2
    assert "evidence gate failed; diagnostics written" in completed.stderr
    summary = json.loads(
        (output_dir / "bridge-policy-shadow.json").read_text(encoding="utf-8")
    )
    assert summary["artifact_count"] == 1
    assert summary["missing_tickers"] == ["MISSING"]
    assert summary["evidence_gate_passed"] is False
    assert (output_dir / "bridge-policy-shadow.md").exists()


def test_cli_rerun_is_byte_identical_and_differing_output_is_immutable(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_path = input_root / "TEST" / "valuation-private.json"
    artifact = legacy_private_artifact("TEST")
    write_private(input_path, artifact)
    assert run_shadow_cli(input_root, output_dir).returncode == 0
    json_path = output_dir / "bridge-policy-shadow.json"
    markdown_path = output_dir / "bridge-policy-shadow.md"
    original_json = json_path.read_bytes()
    original_markdown = markdown_path.read_bytes()

    repeated = run_shadow_cli(input_root, output_dir)
    assert repeated.returncode == 0
    assert json_path.read_bytes() == original_json
    assert markdown_path.read_bytes() == original_markdown

    artifact["financials"]["balance_sheet"]["values"]["cash"] = 101.0
    artifact["financials"]["balance_sheet"]["sources"]["cash"]["value"] = 101.0
    write_private(input_path, artifact)
    differing = run_shadow_cli(input_root, output_dir)

    assert differing.returncode == 1
    assert "Refusing to overwrite immutable output" in differing.stderr
    assert json_path.read_bytes() == original_json
    assert markdown_path.read_bytes() == original_markdown
    assert not list(output_dir.glob("*.tmp"))


def test_output_pair_rolls_back_if_second_publication_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_shadow_cli()
    summary = evaluate_corpus(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    original_publish = module._publish_no_clobber
    calls = 0

    def fail_second(staged: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected second publication failure")
        original_publish(staged, target)

    monkeypatch.setattr(module, "_publish_no_clobber", fail_second)

    with pytest.raises(RuntimeError, match="injected second publication failure"):
        module.write_outputs(output_dir, summary, module.render_markdown(summary))

    assert not (output_dir / "bridge-policy-shadow.json").exists()
    assert not (output_dir / "bridge-policy-shadow.md").exists()
    assert not list(output_dir.iterdir())


def test_output_pair_uses_exclusive_lock_and_never_clobbers_racer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_shadow_cli()
    summary = evaluate_corpus(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    lock_path = output_dir / ".bridge-policy-shadow.lock"
    lock_path.write_text("other writer\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="already running"):
        module.write_outputs(output_dir, summary, module.render_markdown(summary))

    assert lock_path.read_text(encoding="utf-8") == "other writer\n"
    lock_path.unlink()
    original_publish = module._publish_no_clobber
    raced = False

    def publish_after_racer(staged: Path, target: Path) -> None:
        nonlocal raced
        if not raced:
            raced = True
            target.write_bytes(b"concurrent writer\n")
        original_publish(staged, target)

    monkeypatch.setattr(module, "_publish_no_clobber", publish_after_racer)

    with pytest.raises(RuntimeError, match="concurrent output publication"):
        module.write_outputs(output_dir, summary, module.render_markdown(summary))

    assert (output_dir / "bridge-policy-shadow.json").read_bytes() == (
        b"concurrent writer\n"
    )
    assert not (output_dir / "bridge-policy-shadow.md").exists()
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "bridge-policy-shadow.json"
    ]


def test_cli_resolves_aliases_before_rejecting_unsafe_output_roots(
    tmp_path: Path,
) -> None:
    module = load_shadow_cli()
    input_root = tmp_path / "input"
    nested_output = input_root / "nested"
    input_root.mkdir()

    with pytest.raises(ValueError, match="input root"):
        module.validate_paths(input_root, input_root)
    with pytest.raises(ValueError, match="input root"):
        module.validate_paths(input_root, nested_output)

    nested_output.mkdir()
    input_alias = tmp_path / "input-alias"
    input_alias.symlink_to(nested_output, target_is_directory=True)
    with pytest.raises(ValueError, match="input root"):
        module.validate_paths(input_root, input_alias)

    serving_root = REPO_ROOT / "backend" / "app" / "data" / "us_valuation_catalogs"
    with pytest.raises(ValueError, match="serving root"):
        module.validate_paths(input_root, serving_root / "task-8-shadow")
    serving_alias = tmp_path / "serving-alias"
    serving_alias.symlink_to(serving_root, target_is_directory=True)
    with pytest.raises(ValueError, match="serving root"):
        module.validate_paths(input_root, serving_alias)


def test_cli_rejects_case_variant_aliases_on_case_insensitive_filesystem(
    tmp_path: Path,
) -> None:
    module = load_shadow_cli()
    input_root = tmp_path / "CaseInput"
    input_root.mkdir()
    input_variant = tmp_path / "caseinput"
    if not input_variant.exists() or not os.path.samefile(input_root, input_variant):
        pytest.skip("filesystem is case-sensitive")

    with pytest.raises(ValueError, match="input root"):
        module.validate_paths(input_root, input_variant / "nested-output")

    for component, serving_root in (
        ("backend", REPO_ROOT / "backend" / "app" / "data" / "us_valuation_catalogs"),
        ("frontend", REPO_ROOT / "frontend" / "public" / "data"),
    ):
        variant = Path(
            str(serving_root).replace(
                f"{os.sep}{component}{os.sep}",
                f"{os.sep}{component.upper()}{os.sep}",
                1,
            )
        )
        assert variant.exists()
        assert os.path.samefile(serving_root, variant)
        with pytest.raises(ValueError, match="serving root"):
            module.validate_paths(input_root, variant / "task-8-shadow")
