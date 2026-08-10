from __future__ import annotations

import json
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from app.us_valuation.arelle_adapter import (
    _BACKEND_DIR,
    ArelleParseError,
    ArelleParseTimeout,
    ArelleUnavailable,
    parse_structural_filing,
)
from app.us_valuation.concept_resolver import load_structural_rules
from app.us_valuation.arelle_worker import (
    _QNameCanonicalizer,
    _labels_for_concept,
    _numeric_fact_value,
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

    assert len(filing.facts) == 5


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
        "ns_a4613fe2c4:LiquidInvestmentSecuritiesCurrent",
        "ns_a4613fe2c4:LiquidInvestmentSecuritiesNoncurrent",
        "ns_a4613fe2c4:StrategicEquityInvestments",
    }
    large = facts["LargeIntegralAmount"]
    assert large.value == 9_007_199_254_740_993
    assert isinstance(large.value, int)
    assert all(not type(fact).__module__.startswith("arelle") for fact in filing.facts)


def test_arelle_adapter_normalizes_duration_end_date_from_exclusive_datetime() -> None:
    filing = parse_structural_filing(ENTRYPOINT, accession=ACCESSION)

    duration = next(fact for fact in filing.facts if fact.local_name == "TestDurationAmount")

    assert duration.period_start == "2025-01-01"
    assert duration.period_end == "2025-12-31"


def test_qname_canonicalizer_only_trusts_exact_governed_namespaces() -> None:
    canonicalizer = _QNameCanonicalizer()

    for namespace in load_structural_rules()["official_us_gaap_namespaces"]:
        assert canonicalizer.prefix(namespace) == "us-gaap"
    assert canonicalizer.prefix("https://fasb.org/us-gaap/2025") != "us-gaap"
    assert canonicalizer.prefix("http://www.xbrl.org/2003/iso4217") == "iso4217"
    assert canonicalizer.prefix("http://www.xbrl.org/2003/instance") == "xbrli"
    for namespace in (
        "https://issuer.example/us-gaap/2025",
        "https://issuer.example/iso4217/USD",
        "https://issuer.example/fsi/2025",
    ):
        assert canonicalizer.prefix(namespace) not in {"us-gaap", "iso4217", "xbrli", "fsi"}


def test_qname_canonicalizer_preserves_unknown_namespace_in_stable_qname() -> None:
    canonicalizer = _QNameCanonicalizer()
    namespace = "https://issuer.example/us-gaap/2025"

    qname = canonicalizer.qname(type("QName", (), {"namespaceURI": namespace, "localName": "Cash"})())

    assert qname.endswith(":Cash")
    assert qname.split(":", 1)[0] == canonicalizer.prefix(namespace)
    assert canonicalizer.prefix(namespace).startswith("ns_")


def test_numeric_conversion_preserves_large_integral_values_and_rejects_nonfinite() -> None:
    large = 9_007_199_254_740_993

    converted, diagnostic = _numeric_fact_value(
        type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": Decimal(str(large))})()
    )
    assert converted == large
    assert isinstance(converted, int)
    assert diagnostic is None

    fractional, diagnostic = _numeric_fact_value(
        type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": Decimal("1.25")})()
    )
    assert fractional == 1.25
    assert isinstance(fractional, float)
    assert diagnostic is None

    nonfinite, diagnostic = _numeric_fact_value(
        type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": Decimal("Infinity")})()
    )
    assert nonfinite is None
    assert diagnostic is not None
    assert diagnostic.code == "nonfinite_numeric_value"


@pytest.mark.parametrize("value", [Decimal("0.5"), Decimal("42.25")])
def test_numeric_conversion_accepts_exactly_representable_fractional_decimals(
    value: Decimal,
) -> None:
    converted, diagnostic = _numeric_fact_value(
        type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": value})()
    )

    assert converted == float(value)
    assert isinstance(converted, float)
    assert diagnostic is None


@pytest.mark.parametrize("value", [Decimal("9007199254740993.5"), Decimal("1E-400")])
def test_numeric_conversion_rejects_inexact_fractional_decimals(value: Decimal) -> None:
    converted, diagnostic = _numeric_fact_value(
        type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": value})()
    )

    assert converted is None
    assert diagnostic is not None
    assert diagnostic.code == "inexact_numeric_value"


def test_numeric_conversion_rejects_fractional_overflow() -> None:
    overflowing_fraction = Decimal("1" + "0" * 309 + ".5")
    converted, diagnostic = _numeric_fact_value(
        type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": overflowing_fraction})()
    )

    assert converted is None
    assert diagnostic is not None
    assert diagnostic.code in {"nonfinite_numeric_value", "numeric_out_of_range"}


def test_numeric_conversion_rejects_oversized_integral_decimal() -> None:
    converted, diagnostic = _numeric_fact_value(
        type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": Decimal("1E309")})()
    )

    assert converted is None
    assert diagnostic is not None
    assert diagnostic.code == "numeric_out_of_range"


@pytest.mark.parametrize(
    ("fact", "code"),
    [
        (type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": None})(), "nil_fact"),
        (type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})()})(), "missing_fact_value"),
        (type("Fact", (), {"concept": type("Concept", (), {"isNumeric": True})(), "xValue": "not-a-number"})(), "invalid_numeric_value"),
    ],
)
def test_worker_emits_stable_diagnostic_before_skipping_invalid_fact(fact: object, code: str) -> None:
    value, diagnostic = _numeric_fact_value(fact)

    assert value is None
    assert diagnostic is not None
    assert diagnostic.code == code


def test_worker_silently_ignores_legitimate_text_facts() -> None:
    text_fact = type(
        "Fact",
        (),
        {"concept": type("Concept", (), {"isNumeric": False})(), "xValue": "Balance sheet"},
    )()

    value, diagnostic = _numeric_fact_value(text_fact)

    assert value is None
    assert diagnostic is None


def test_labels_never_fallback_to_qname_or_documentation() -> None:
    calls: list[dict[str, object]] = []

    class Concept:
        def label(self, **kwargs: object) -> None:
            calls.append(kwargs)
            return None

    assert _labels_for_concept(Concept()) == ()
    assert calls
    assert all(call.get("fallbackToQname") is False for call in calls)


def test_arelle_adapter_rejects_malformed_diagnostic_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        output_path = Path(args[0][args[0].index("--output") + 1])
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
                            "labels": [],
                            "documentation": None,
                            "value": 1,
                            "unit": "USD",
                            "period_start": None,
                            "period_end": "2025-12-31",
                            "context_id": "CurrentYearInstant",
                            "dimensions": [],
                            "statement_roles": [],
                            "presentation_parents": [],
                            "calculation_parents": [],
                            "calculation_children": [],
                            "definition_parents": [],
                            "definition_children": [],
                            "source_accession": ACCESSION,
                        }
                    ],
                    "diagnostics": ["not-an-object"],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args[0], 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ArelleParseError, match="invalid filing data"):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION)


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
    assert captured["kwargs"]["cwd"] == str(_BACKEND_DIR)  # type: ignore[index]
    assert filing.facts[0].qname == "fsi:TestFact"


def test_arelle_adapter_sanitizes_worker_import_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["env"] = kwargs["env"]
        output_path = Path(command[command.index("--output") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "source_accession": ACCESSION,
                    "period_end": "2025-12-31",
                    "facts": [],
                    "diagnostics": [],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("PYTHONPATH", "/tmp/hostile-app")
    monkeypatch.setenv("PYTHONSAFEPATH", "/tmp/hostile-safe-path")
    monkeypatch.setattr(subprocess, "run", run)

    with pytest.raises(ArelleParseError, match="no facts"):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION)

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["PYTHONPATH"] == str(_BACKEND_DIR)
    assert "PYTHONSAFEPATH" not in env
    assert "PYTHONHOME" not in env
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONHASHSEED"] == "0"


def test_arelle_adapter_extracts_with_hostile_python_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONHOME", "/tmp/hostile-python-home")
    monkeypatch.setenv("PYTHONPATH", "/tmp/hostile-app")
    monkeypatch.setenv("PYTHONSAFEPATH", "/tmp/hostile-safe-path")

    filing = parse_structural_filing(ENTRYPOINT, accession=ACCESSION)

    assert any(fact.local_name == "LiquidInvestmentSecuritiesCurrent" for fact in filing.facts)


def test_arelle_adapter_maps_worker_launch_oserror_to_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def launch_failure(*args: object, **kwargs: object) -> None:
        raise OSError("exec failed")

    monkeypatch.setattr(subprocess, "run", launch_failure)
    with pytest.raises(ArelleParseError, match="exec failed"):
        parse_structural_filing(ENTRYPOINT, accession=ACCESSION)


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
