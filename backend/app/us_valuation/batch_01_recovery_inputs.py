"""Validated, non-serving source inputs for Batch 01 recovery models."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence


EXPECTED_STRUCTURAL = {
    "NEE-Q2": ("0000753308-26-000060", "10-Q"),
    "NEE-FY2025": ("0000753308-26-000015", "10-K"),
    "DELL-FY2026": ("0001571996-26-000008", "10-K"),
}
EXPECTED_EXISTING = {
    "DELL-Q1": ("DELL", "0001571996-26-000030", "10-Q"),
    "WDC-FY2026": ("WDC", "0001628280-26-057139", "10-K"),
}


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"recovery source must be an object: {path}")
    return value


def load_batch_01_recovery_evidence(
    *, recovery_root: Path,
    structural_root: Path,
) -> dict[str, Any]:
    """Load exact recovery packets and verify their receipts before modeling."""

    evidence: dict[str, Any] = {}
    for key, (accession, form) in EXPECTED_STRUCTURAL.items():
        root = recovery_root / key
        parsed = _read(root / "structural-filing.json")
        receipt = _read(root / "source-receipt.json")
        if (
            parsed.get("source_accession") != accession
            or parsed.get("form") != form
            or receipt.get("filing", {}).get("accession") != accession
            or receipt.get("filing", {}).get("form") != form
            or receipt.get("filing", {}).get("filed", "") > "2026-08-14"
            or receipt.get("structural_filing_sha256")
            != hashlib.sha256(_json_bytes(parsed)).hexdigest()
        ):
            raise ValueError(f"recovery structural receipt mismatch: {key}")
        evidence[key] = parsed
        evidence[f"{key}-receipt"] = receipt

    for key, (ticker, accession, form) in EXPECTED_EXISTING.items():
        parsed = _read(structural_root / ticker / "structural-filing.json")
        if parsed.get("source_accession") != accession or parsed.get("form") != form:
            raise ValueError(f"existing structural evidence mismatch: {key}")
        evidence[key] = parsed

    peer_root = recovery_root / "STX"
    companyfacts = _read(peer_root / "companyfacts.json")
    receipt = _read(peer_root / "source-receipt.json")
    if (
        str(companyfacts.get("cik", "")).zfill(10) != "0001137789"
        or receipt.get("ticker") != "STX"
        or receipt.get("valuation_date") != "2026-08-14"
        or receipt.get("companyfacts_sha256")
        != hashlib.sha256(_json_bytes(companyfacts)).hexdigest()
    ):
        raise ValueError("STX recovery source receipt mismatch")
    evidence["STX-companyfacts"] = companyfacts
    evidence["STX-receipt"] = receipt
    return evidence


def structural_fact(
    filing: Mapping[str, Any],
    *,
    local_name: str,
    period_end: str,
    period_start: str | None = None,
    unit: str = "USD",
    dimensions: Sequence[Sequence[str]] | None = (),
) -> float:
    """Select one exact fact from a governed structural filing."""

    matches: list[float] = []
    for fact in filing.get("facts", []):
        if (
            fact.get("local_name") == local_name
            and fact.get("period_end") == period_end
            and (period_start is None or fact.get("period_start") == period_start)
            and fact.get("unit") == unit
            and (
                dimensions is None
                or list(fact.get("dimensions") or []) == [list(row) for row in dimensions]
            )
            and isinstance(fact.get("value"), (int, float))
            and not isinstance(fact.get("value"), bool)
        ):
            matches.append(float(fact["value"]))
    if len(set(matches)) != 1:
        raise ValueError(
            f"{local_name} requires one exact structural value for {period_end}"
        )
    return matches[0]


def ttm_from_structural(
    *,
    annual: Mapping[str, Any],
    interim: Mapping[str, Any],
    local_name: str,
    annual_start: str,
    annual_end: str,
    current_start: str,
    current_end: str,
    prior_start: str,
    prior_end: str,
    unit: str = "USD",
) -> float:
    return (
        structural_fact(
            annual,
            local_name=local_name,
            period_start=annual_start,
            period_end=annual_end,
            unit=unit,
        )
        + structural_fact(
            interim,
            local_name=local_name,
            period_start=current_start,
            period_end=current_end,
            unit=unit,
        )
        - structural_fact(
            interim,
            local_name=local_name,
            period_start=prior_start,
            period_end=prior_end,
            unit=unit,
        )
    )


def companyfacts_annual_rows(
    companyfacts: Mapping[str, Any],
    *,
    concept: str,
    unit: str = "USD",
) -> list[dict[str, Any]]:
    rows = (
        companyfacts.get("facts", {})
        .get("us-gaap", {})
        .get(concept, {})
        .get("units", {})
        .get(unit, [])
    )
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        if (
            row.get("form") == "10-K"
            and row.get("fp") == "FY"
            and row.get("filed", "") <= "2026-08-14"
            and isinstance(row.get("start"), str)
            and isinstance(row.get("end"), str)
            and isinstance(row.get("val"), (int, float))
            and not isinstance(row.get("val"), bool)
        ):
            duration = (
                date.fromisoformat(row["end"])
                - date.fromisoformat(row["start"])
            ).days
            if not 300 <= duration <= 380:
                continue
            prior = selected.get(row["end"])
            if prior is None or (row["filed"], row["accn"]) > (
                prior["filed"],
                prior["accn"],
            ):
                selected[row["end"]] = row
    return [selected[end] for end in sorted(selected)]
