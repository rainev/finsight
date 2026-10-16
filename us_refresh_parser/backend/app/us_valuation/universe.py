"""Frozen issuer-level replacement universe for the controlled reset."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
from typing import Any, Mapping


UNIVERSE_VERSION = "US-SP500-ISSUERS-2026-08-14-1.0"


@dataclass(frozen=True)
class UniverseIssuer:
    ticker: str
    all_index_tickers: tuple[str, ...]
    issuer_name: str
    cik: str
    gics_sector: str
    gics_sub_industry: str
    filing_regime: str
    accounting_standard: str
    share_class_policy: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UniverseIssuer":
        required = (
            "ticker",
            "issuer_name",
            "cik",
            "gics_sector",
            "gics_sub_industry",
            "filing_regime",
            "accounting_standard",
            "share_class_policy",
        )
        if any(not isinstance(value.get(key), str) or not value[key].strip() for key in required):
            raise ValueError("universe issuer text fields must be nonempty")
        tickers = value.get("all_index_tickers")
        if (
            not isinstance(tickers, list)
            or not tickers
            or any(not isinstance(item, str) or not item for item in tickers)
            or len(set(tickers)) != len(tickers)
            or value["ticker"] not in tickers
        ):
            raise ValueError("universe share-class tickers are invalid")
        if len(value["cik"]) != 10 or not value["cik"].isdigit():
            raise ValueError("universe CIK must be ten digits")
        if value.get("included") is not True:
            raise ValueError("universe issuer must be explicitly included")
        if value.get("membership_effective_date") != "2026-08-14":
            raise ValueError("universe issuer effective date mismatch")
        return cls(
            ticker=value["ticker"],
            all_index_tickers=tuple(tickers),
            issuer_name=value["issuer_name"],
            cik=value["cik"],
            gics_sector=value["gics_sector"],
            gics_sub_industry=value["gics_sub_industry"],
            filing_regime=value["filing_regime"],
            accounting_standard=value["accounting_standard"],
            share_class_policy=value["share_class_policy"],
        )


def load_universe() -> tuple[UniverseIssuer, ...]:
    path = files(__package__).joinpath("config/universe_2026_08_14.json")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("universe_version") != UNIVERSE_VERSION
        or value.get("effective_date") != "2026-08-14"
        or value.get("security_count") != 503
        or value.get("issuer_count") != 500
        or not isinstance(value.get("records"), list)
    ):
        raise ValueError("universe manifest header is invalid")
    records = tuple(UniverseIssuer.from_dict(row) for row in value["records"])
    if len(records) != 500:
        raise ValueError("universe must contain exactly 500 issuers")
    if len({row.cik for row in records}) != 500:
        raise ValueError("universe contains duplicate issuer CIKs")
    if len({row.ticker for row in records}) != 500:
        raise ValueError("universe contains duplicate primary tickers")
    if records != tuple(sorted(records, key=lambda row: row.cik)):
        raise ValueError("universe must be sorted by CIK")
    multi = {row.cik: row for row in records if len(row.all_index_tickers) > 1}
    if {cik: row.ticker for cik, row in multi.items()} != {
        "0001564708": "NWSA",
        "0001652044": "GOOGL",
        "0001754301": "FOXA",
    }:
        raise ValueError("universe primary share-class policy changed")
    tickers = {row.ticker for row in records}
    if "AVB" not in tickers or "RDDT" in tickers:
        raise ValueError("universe does not represent the August 14 cutoff")
    return records
