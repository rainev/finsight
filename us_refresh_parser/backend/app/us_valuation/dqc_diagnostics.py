"""Fail-closed evaluation of XBRL US DQC diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DqcResult:
    status: str
    reason_codes: tuple[str, ...]
    diagnostics: tuple[dict[str, str], ...]
    ruleset: str | None
    taxonomy_year: int
    value: None = None
    can_create_value: bool = False


def evaluate_dqc(
    *,
    diagnostics: Sequence[Mapping[str, Any]],
    taxonomy_year: int,
    ruleset_metadata: Mapping[str, Any] | None,
) -> DqcResult:
    if isinstance(taxonomy_year, bool) or not isinstance(taxonomy_year, int):
        raise ValueError("taxonomy_year must be an integer")
    if not isinstance(ruleset_metadata, Mapping):
        return DqcResult(
            status="unavailable",
            reason_codes=("DQC_RULESET_UNAVAILABLE",),
            diagnostics=(),
            ruleset=None,
            taxonomy_year=taxonomy_year,
        )
    ruleset = ruleset_metadata.get("ruleset")
    ruleset_year = ruleset_metadata.get("taxonomy_year")
    if not isinstance(ruleset, str) or not ruleset:
        return DqcResult(
            status="unavailable",
            reason_codes=("DQC_RULESET_UNAVAILABLE",),
            diagnostics=(),
            ruleset=None,
            taxonomy_year=taxonomy_year,
        )
    if ruleset_year != taxonomy_year:
        return DqcResult(
            status="unavailable",
            reason_codes=("DQC_TAXONOMY_YEAR_MISMATCH",),
            diagnostics=(),
            ruleset=ruleset,
            taxonomy_year=taxonomy_year,
        )

    governed: list[dict[str, str]] = []
    for item in diagnostics:
        code = item.get("code")
        severity = item.get("severity")
        message = item.get("message")
        if not isinstance(code, str) or not code.startswith("DQC."):
            continue
        if severity not in {"info", "warning", "error"} or not isinstance(message, str):
            raise ValueError("DQC diagnostic has invalid code/severity/message")
        governed.append({"code": code, "severity": severity, "message": message})
    governed.sort(key=lambda item: (item["code"], item["severity"], item["message"]))
    reason_codes = tuple(dict.fromkeys(item["code"] for item in governed))
    if any(item["severity"] == "error" for item in governed):
        status = "diagnostic_error"
    elif any(item["severity"] == "warning" for item in governed):
        status = "diagnostic_warning"
    else:
        status = "pass"
    return DqcResult(
        status=status,
        reason_codes=reason_codes,
        diagnostics=tuple(governed),
        ruleset=ruleset,
        taxonomy_year=taxonomy_year,
    )
