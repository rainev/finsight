"""Process-isolated adapter for structural Inline XBRL extraction."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .structural_xbrl import (
    ParseDiagnostic,
    StructuralFact,
    StructuralFiling,
    normalize_filing_form,
)


_BACKEND_DIR = Path(__file__).resolve().parents[2]


class ArelleError(RuntimeError):
    """Base class for failures at the Arelle process boundary."""


class ArelleUnavailable(ArelleError):
    """The child process could not import or start Arelle."""


class ArelleParseError(ArelleError):
    """The child process failed to produce a valid structural filing."""


class ArelleParseTimeout(ArelleError):
    """The child process exceeded the caller's authoritative timeout."""


def _diagnostic_from_dict(value: Mapping[str, Any]) -> ParseDiagnostic:
    context = tuple(
        (str(pair[0]), str(pair[1]))
        for pair in value.get("context", ())
        if isinstance(pair, (list, tuple)) and len(pair) == 2
    )
    return ParseDiagnostic(
        code=str(value["code"]),
        message=str(value["message"]),
        severity=str(value["severity"]),
        context=context,
    )  # type: ignore[arg-type]


def _filing_from_payload(payload: Any, accession: str, form: str) -> StructuralFiling:
    if not isinstance(payload, Mapping):
        raise ArelleParseError("worker output must be a JSON object")
    raw_facts = payload.get("facts")
    if not isinstance(raw_facts, list):
        raise ArelleParseError("worker output facts must be a JSON array")
    if not raw_facts:
        raise ArelleParseError("worker returned no facts")
    if payload.get("source_accession") != accession:
        raise ArelleParseError("worker output accession does not match the requested accession")
    if payload.get("form") != form:
        raise ArelleParseError("worker output form does not match the requested form")

    try:
        facts = tuple(StructuralFact.from_dict(fact) for fact in raw_facts)
        diagnostics = tuple(
            _diagnostic_from_dict(diagnostic)
            for diagnostic in payload.get("diagnostics", ())
        )
        filed_date = payload.get("filed_date")
        report_date = payload.get("report_date")
        if filed_date is not None and any(
            fact.filed_date != filed_date for fact in facts
        ):
            raise ValueError("worker fact filed_date does not match filing metadata")
        if report_date is not None and any(
            fact.report_date != report_date for fact in facts
        ):
            raise ValueError("worker fact report_date does not match filing metadata")
        return StructuralFiling(
            source_accession=str(payload["source_accession"]),
            period_end=str(payload["period_end"]),
            facts=facts,
            diagnostics=diagnostics,
            form=payload.get("form"),
            filed_date=filed_date,
            report_date=report_date,
            filing_metadata=tuple(
                (str(pair[0]), str(pair[1]))
                for pair in payload.get("filing_metadata", ())
                if isinstance(pair, (list, tuple)) and len(pair) == 2
            ),
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ArelleParseError(f"worker output has invalid filing data: {error}") from error


def _looks_like_missing_arelle(output: str) -> bool:
    lowered = output.lower()
    return (
        "no module named 'arelle'" in lowered
        or 'no module named "arelle"' in lowered
        or "modulenotfounderror" in lowered and "arelle" in lowered
        or "arelle is not installed" in lowered
    )


def _worker_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("PYTHON")
    }
    environment.update(
        {
            "PYTHONPATH": os.fspath(_BACKEND_DIR),
            "PYTHONNOUSERSITE": "1",
            "PYTHONHASHSEED": "0",
        }
    )
    return environment


def parse_structural_filing(
    entrypoint: Path,
    *,
    accession: str,
    form: str = "10-K",
    timeout_seconds: int = 120,
    cpu_limit_seconds: int | None = None,
) -> StructuralFiling:
    """Parse a local filing through a JSON-only child-process boundary."""

    entrypoint = Path(entrypoint).resolve()
    if not entrypoint.is_file():
        raise ArelleParseError(f"entrypoint does not exist: {entrypoint}")
    if not accession.strip():
        raise ValueError("accession must be nonempty")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if cpu_limit_seconds is not None and (isinstance(cpu_limit_seconds,bool) or not isinstance(cpu_limit_seconds,int) or not 1 <= cpu_limit_seconds <= 600):
        raise ValueError('CPU limit must be an integer from 1 to 600 seconds')
    worker_environment = _worker_environment()
    if cpu_limit_seconds is not None:
        worker_environment['FINSIGHT_ARELLE_CPU_LIMIT_SECONDS'] = str(cpu_limit_seconds)
    normalized_form = normalize_filing_form(form)

    with tempfile.TemporaryDirectory(prefix="arelle-output-") as temp_dir:
        output_path = Path(temp_dir) / "filing.json"
        command = [
            sys.executable,
            "-m",
            "app.us_valuation.arelle_worker",
            "--entrypoint",
            os.fspath(entrypoint),
            "--accession",
            accession,
            "--form",
            normalized_form,
            "--output",
            os.fspath(output_path),
        ]
        try:
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=timeout_seconds,
                    cwd=os.fspath(_BACKEND_DIR),
                    env=worker_environment,
                )
            except subprocess.TimeoutExpired as error:
                raise ArelleParseTimeout(
                    f"Arelle worker exceeded {timeout_seconds} seconds"
                ) from error
            except OSError as error:
                raise ArelleParseError(f"failed to launch Arelle worker: {error}") from error
            if completed.returncode != 0:
                details = "\n".join(part for part in (completed.stderr, completed.stdout) if part)
                if _looks_like_missing_arelle(details):
                    raise ArelleUnavailable(
                        f"Arelle is unavailable: {details.strip() or 'missing dependency'}"
                    )
                raise ArelleParseError(
                    details.strip() or f"Arelle worker exited with status {completed.returncode}"
                )
            try:
                raw_output = output_path.read_text(encoding="utf-8")
            except OSError as error:
                raise ArelleParseError(f"worker did not produce JSON output: {error}") from error
            try:
                payload = json.loads(raw_output)
            except json.JSONDecodeError as error:
                raise ArelleParseError(f"worker output is not valid JSON: {error}") from error
            return _filing_from_payload(payload, accession, normalized_form)
        finally:
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass
