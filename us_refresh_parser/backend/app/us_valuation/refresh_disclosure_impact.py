"""Classify narrow post-baseline disclosures that cannot update valuation facts.

This is intentionally not a general SEC-event classifier.  It recognizes only
amendments to third-party ownership or insider-reporting forms whose metadata
identifies no issuer financial statement, financing, security registration, or
current report.  Everything else remains an evidence-review lane.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence


DISCLOSURE_IMPACT_POLICY_VERSION = "US-DISCLOSURE-IMPACT-1"

# These amendments report holdings or transactions in already outstanding
# securities.  They are not issuer financial statements and, standing alone,
# do not change the locked period-end cash, debt, operating scope, or share
# count used by the approved recipe.  Registration statements and issuer
# current reports are deliberately absent.
NON_ECONOMIC_AMENDMENT_FORMS = frozenset({
    "SCHEDULE 13D/A",
    "SCHEDULE 13G/A",
    "13F-HR/A",
    "3/A",
    "4/A",
    "144/A",
    "S-8",
    "S-8 POS",
    "11-K/A",
})


def _iso(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def classify_non_economic_amendments(
    records: Sequence[Mapping[str, Any]],
    *,
    prior_cutoff: str,
    cutoff: str,
    submissions_sha256: str,
    changed_regular: bool,
) -> dict[str, Any] | None:
    """Return an exact metadata ledger only when every record is non-economic.

    A changed annual/interim filing always wins over this classifier.  Missing,
    mixed, wildcard, or malformed metadata fails closed by returning ``None``.
    """
    if changed_regular or not records:
        return None
    if (
        not isinstance(submissions_sha256, str)
        or len(submissions_sha256) != 64
        or any(char not in "0123456789abcdef" for char in submissions_sha256.lower())
    ):
        return None
    prior = _iso(prior_cutoff, "prior cutoff")
    current = _iso(cutoff, "cutoff")
    ledger: list[dict[str, str]] = []
    for record in records:
        form = str(record.get("form") or "").upper().strip()
        accession = record.get("accessionNumber")
        filed = record.get("filingDate")
        primary = record.get("primaryDocument")
        items = str(record.get("items") or "").strip()
        if (
            form not in NON_ECONOMIC_AMENDMENT_FORMS
            or items
            or not isinstance(accession, str)
            or not accession
            or not isinstance(primary, str)
            or not primary
        ):
            return None
        try:
            filed_iso = _iso(filed, f"{accession} filing date")
        except ValueError:
            return None
        if not prior < filed_iso <= current:
            return None
        ledger.append({
            "accession": accession,
            "filed": filed_iso,
            "form": form,
            "primary_document": primary,
        })
    return {
        "policy_version": DISCLOSURE_IMPACT_POLICY_VERSION,
        "classification": "non_economic_ownership_insider_or_plan_registration",
        "submissions_sha256": submissions_sha256.lower(),
        "records": sorted(ledger, key=lambda row: (row["filed"], row["accession"])),
        "treatment": (
            "Retain the approved valuation as current: the only newer SEC records "
            "are ownership or insider-reporting amendments, or employee-plan "
            "registration records; none reports an issued current share balance, "
            "issuer financing, current report, or issuer financial statement."
        ),
        "limitations": [
            "This classification does not approve any accompanying or later issuer filing.",
            "A changed annual/interim filing or any mixed form set bypasses this rule.",
            "Registered employee-plan capacity is not treated as issued dilution; later reported shares and compensation remain controlling.",
        ],
    }
