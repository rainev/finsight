"""Load the frozen Batch 02 issuer contract without widening its scope."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

from .sec_client import normalize_cik


BATCH_02_VALUATION_DATE = "2026-08-14"
_MANIFEST_RESOURCE = "config/reset_batches_2026_08_14/batch_02.json"
_EXPECTED_TICKERS = ("OMC", "VZ", "T", "TTWO", "NFLX", "CHTR", "CMCSA", "TMUS", "META", "WBD")


@dataclass(frozen=True)
class Batch02Issuer:
    ticker: str
    cik: str
    issuer_name: str


def _load_manifest() -> tuple[Batch02Issuer, ...]:
    raw = files(__package__).joinpath(_MANIFEST_RESOURCE).read_text(encoding="utf-8")
    document = json.loads(raw)
    if document.get("batch") != 2 or document.get("valuation_date") != BATCH_02_VALUATION_DATE:
        raise ValueError("Batch 02 manifest identity is invalid")
    members = document.get("members")
    if not isinstance(members, list):
        raise ValueError("Batch 02 manifest members are invalid")
    issuers = tuple(
        Batch02Issuer(
            ticker=str(member["ticker"]),
            cik=normalize_cik(member["cik"]),
            issuer_name=str(member["issuer_name"]),
        )
        for member in members
    )
    if tuple(issuer.ticker for issuer in issuers) != _EXPECTED_TICKERS:
        raise ValueError("Batch 02 manifest ticker set or ordering is invalid")
    if len({issuer.cik for issuer in issuers}) != len(issuers):
        raise ValueError("Batch 02 manifest CIKs must be unique")
    return issuers


BATCH_02_MANIFEST = _load_manifest()
BATCH_02_TICKERS = tuple(issuer.ticker for issuer in BATCH_02_MANIFEST)
_ISSUER_BY_TICKER = {issuer.ticker: issuer for issuer in BATCH_02_MANIFEST}


def issuer_for_ticker(ticker: str) -> Batch02Issuer:
    return _ISSUER_BY_TICKER[ticker]
