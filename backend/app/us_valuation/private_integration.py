"""Strict, non-public projection for held U.S. expansion reviews.

This module is deliberately separate from :mod:`artifacts`.  The public
sanitizer is the serving boundary and must continue to withhold an artifact
whose public bridge is incomplete.  ``project_review_artifact`` is a narrow
private-review boundary for explicitly sealed B01/B02/B03/B04/B05 packages; it is not
a catalog admission or publication mechanism.  Each package is a separate
closed profile: a package cannot select a new denominator, re-hash changed
economics, or carry private privileges to another catalog row.
"""

from __future__ import annotations

import re
from copy import deepcopy
from math import isfinite
from typing import Any, Mapping

from .artifacts import sanitize_public_artifact
from .catalog import canonical_json_bytes, sha256_bytes


PRIVATE_REVIEW_SCHEMA_VERSION = "FINSIGHT-PRIVATE-INTEGRATION-REVIEW-1"
PRIVATE_REVIEW_CUTOFF = "2026-10-03"
APPROVED_RANGES_SHA256 = "de39011c21b71fcb47e5b7a9acd41f49bee5f0563581faa5c2b25d6eb99112aa"
ORIGIN_SUMMARY_SHA256 = "f86bf3837620f7e1429faf4b68f9fd21bd56c91847a9ac525e2ab5966a2643f1"
_RANGE_LABEL = "assumption range, not a statistical confidence interval"
_SCENARIOS = ("bear", "base", "bull")
_RANGE_KEYS = ("low", "base", "high")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

# These are the exact ten identities selected for the frozen B01 review.  The
# order is intentional and is part of the review package's denominator.
B01_IDENTITIES: dict[str, str] = {
    "AIT": "0000109563",
    "MSM": "0001003078",
    "WCC": "0000929008",
    "SITE": "0001650729",
    "WTS": "0000795403",
    "FELE": "0000038725",
    "GRC": "0000042682",
    "MWA": "0001350593",
    "KAI": "0000886346",
    "MLI": "0000089439",
}
_EXPECTED_IDENTITY_ITEMS: tuple[tuple[str, str], ...] = tuple(B01_IDENTITIES.items())
_EXPECTED_IDENTITIES = dict(_EXPECTED_IDENTITY_ITEMS)
_EXPECTED_TICKERS = tuple(ticker for ticker, _ in _EXPECTED_IDENTITY_ITEMS)

B01_PRIMARY_MODELS: dict[str, str] = {
    "AIT": "fcfe_dcf",
    "MSM": "fcff_dcf",
    "WCC": "residual_income",
    "SITE": "fcff_dcf",
    "WTS": "fcff_dcf",
    "FELE": "fcff_dcf",
    "GRC": "residual_income",
    "MWA": "fcff_dcf",
    "KAI": "fcff_dcf",
    "MLI": "fcff_dcf",
}
_EXPECTED_PRIMARY_MODEL_ITEMS: tuple[tuple[str, str], ...] = tuple(B01_PRIMARY_MODELS.items())
_EXPECTED_PRIMARY_MODELS = dict(_EXPECTED_PRIMARY_MODEL_ITEMS)

# A second closed profile, not caller-selected arbitrary membership/ranges.
_B02_IDENTITIES = (('TNC','0000097134'),('LNN','0000836157'),('TKR','0000098362'),
    ('KMT','0000055242'),('WDFC','0000105132'),('FIZZ','0000069891'),('GIC','0000945114'),
    ('ROG','0000084748'),('JBSS','0000880117'),('NGVC','0001547459'))
_B02_HASHES = {
    'TNC':'6d68b0a67aff937934d204d92f4230a6ac40811f0f2b32fe6d658f774d9387d6',
    'LNN':'d3935fc826084e46498a7b7e98fd1fb7d5f02c8d50be0ab2e8f997f0bb92b4cf',
    'TKR':'b8a13f9bfb98b6db72a8fa9815a32b9c2cd6b86d6d2e2349f68249054745d691',
    'KMT':'fed35205d6deb4a15f16403fddefab5b58e1269996f2b728b60a925fe06bd638',
    'WDFC':'e91dafe5262140a3f1497ab8f433f03c14a206409ab8dfc7b54bf3c351f4f616',
    'FIZZ':'162aacd130c8b8a61b20d2c74cd2a3c16b860fb51987239442be5b65eedfcdd5',
    'GIC':'62e57d777a472a5450a4447e70971ee24162c237f2b23c0f2200d9e960101a05',
    'ROG':'8e9b254121955e34cb1b4308d24132a9e8723330f5cd5a613f960daccd75541d',
    'JBSS':'751ba4f8259618ecb7ff06280dd315599278ce0186fd98bbde7b722e7a0fa84b',
    'NGVC':'057203f6b531c9b2ca4db0ba69d1a256f0a76fd0de51a650ba23d90f56cf5e15'}
_B02_SCHEMA='FINSIGHT-PRIVATE-INTEGRATION-REVIEW-2'
_B02_PROFILE='B02-FROZEN-PRIVATE-1'
_B02_ORIGIN='d8dc1a757170c63f59728238f18f99ea4d6e40f036b479a47bdf6d0c2125388a'
_B02_RANGE_HASH='2a4a984f47afacb30db4b43dbc9f818744abf7088c4bbfb94e37817ad7728a5f'

# B03 is the sealed private530 successor to the admitted B02/520 catalog.
# These values are generated from the frozen recovery-pass-01/run-a package.
# Artifact hashes are over the metadata-normalized artifacts produced by
# scripts/prepare_us_expansion_integration.py::normalize: source accession/url
# aliases and recipe metadata may change, while ranges, warnings, dates and
# model values may not.
B03_IDENTITIES: dict[str, str] = {
    "IOSP": "0001054905",
    "ALG": "0000897077",
    "AIN": "0000819793",
    "MTRN": "0001104657",
    "DORM": "0000868780",
    "ENS": "0001289308",
    "KWR": "0000081362",
    "IPAR": "0000822663",
    "UFPI": "0000912767",
    "SMID": "0000924719",
}
_B03_IDENTITIES = tuple(B03_IDENTITIES.items())
_B03_HASHES = {
    "IOSP": "e8e7b0f751787bc02ea8f28a3b1e950add671362c0dbc19734ed5699fdf38869",
    "ALG": "6db34538da843fdfc186dee82693b9a44adb0fb00fc5babcc09d48a0d6ab66ec",
    "AIN": "0bc26cb1783d8771f7b746f4b96d8452a60de5107d323ee33bbef45dbee4338f",
    "MTRN": "f16be2c15fdb1203d09540e1413cbc8a5a868d9778a8d55a91968bc3af344b5f",
    "DORM": "1a559bf3b2d93c2325ce1ae36becbbec300533b50cc3895d35a54e3dae24cb0f",
    "ENS": "19dc709ebc925307affa5c69f22e9fa842f1b8d6f48f553d925d869ee4a37e64",
    "KWR": "cce007cb0b818eab43e8762f812e1a5fd67c7148b4fbf3be614bacb7eb6617a6",
    "IPAR": "2535e11a2484061f4ce553851c7fb89a9f49cec06a1d744e4bc34498fba89d93",
    "UFPI": "b4e45798a117e76c0c2af3e5746a8125b48ede7104a56a72d293fce48cb78774",
    "SMID": "c57270d228989b4ca9c40194fe63e191b7c7b318e488f3f84bf47801a804b471",
}
_B03_SCHEMA = "FINSIGHT-PRIVATE-INTEGRATION-REVIEW-3"
_B03_PROFILE = "B03-FROZEN-PRIVATE-1"
_B03_CUTOFF = "2026-10-06"
_B03_ORIGIN = "ac91b048e816cc9887e366d7623c4d354d4822d9c86b913587dc926412cf8e88"
_B03_RANGE_HASH = "f15dae9db0d790e3c59f64a5e164348da2263b468cb2a0591492727c2fd547ab"
_B03_BASE_CATALOG_VERSION = "US-ADMITTED-B02-520-a42d5320e9a7d88a9269522f"
_B03_BASE_MANIFEST_SHA256 = "a0c1fe6caba7c0d9eb0880494e8581c657f39bd52ebdf53cf28a431673a7affe"
_B03_CONSUMER_ARCHETYPES = frozenset({"IPAR"})
_B03_KWR = "KWR"

# B04 is the sealed private initial-review successor to the admitted B03/530
# catalog.  The artifact hashes below are over the metadata-normalized
# artifacts returned by ``prepare_us_expansion_integration.normalize``.  This
# profile is intentionally disjoint from B03: no B03 identity or private
# review claim is reusable for a B04 row.
B04_IDENTITIES: dict[str, str] = {
    "ETD": "0000896156",
    "LZB": "0000057131",
    "BSET": "0000010329",
    "FLXS": "0000037472",
    "PLOW": "0001287213",
    "PATK": "0000076605",
    "UFPT": "0000914156",
    "IBP": "0001580905",
    "NPK": "0000080172",
    "MTW": "0000061986",
}
_B04_IDENTITIES = tuple(B04_IDENTITIES.items())
_B04_HASHES = {
    "ETD": "477d94a5c5b0e928a34734cee6a8dafd5cac10b4f75e13971b55cc70fc872f9b",
    "LZB": "7122f059ab83c820d3dc7a9e96c988c940f23a9fde1a1e5222b8e84465a107c9",
    "BSET": "492a81fa2d9c89552ab23e9a1e79c927931fff021c150aaaefd084d0194155e8",
    "FLXS": "daa62ac243f45fa05c9e5de6942dd9ece4fe479f8bc9e73e57bace4e655ea278",
    "PLOW": "19fccd1554a79f7a2651a715e9a28e293d169ee5a5c68181e28a91a95a7fb156",
    "PATK": "7c14b6576bb6bede3c37618dd4bde321b570c2f7be2c249bbc1bc027709720f1",
    "UFPT": "2fa25437aafd5d9c7b5131311bb9760b5a0af1f5bebec0e20e4a82e90d5d7c30",
    "IBP": "ea1a80f68dc27239a75c4dd1b7bd029c6839bb479b03042ad30833b237c56d28",
    "NPK": "28e5798a0b97ec5ab17d6b7c122b01544a1c205c2328a009f5296692afd40b64",
    "MTW": "2fd1d7ad9ad8351ffad7dc60f128077bbf887e293ceacfc7074b885e10cb1875",
}
_B04_SCHEMA = "FINSIGHT-PRIVATE-INTEGRATION-REVIEW-4"
_B04_PROFILE = "B04-FROZEN-PRIVATE-1"
_B04_CUTOFF = "2026-10-06"
_B04_ORIGIN = "e8c60a4def0fc37a280cb8ae85488b10dbd0b4cac20749cf75984b26c404c378"
_B04_RANGE_HASH = "135f19f298893efd031c836146e11a2c693018238619723b8c52b2dee2b60a90"
_B04_BASE_CATALOG_VERSION = "US-ADMITTED-B03-530-87c22806696587f23d529649"
_B04_BASE_MANIFEST_SHA256 = "368db44036f2f340b116faa3d8c79d03957efaf52a5d51acfa3f381ee8c7ff24"
_B04_CONSUMER_ARCHETYPES = frozenset({"ETD", "LZB", "BSET", "FLXS"})

# Public names make the sealed profile auditable by package builders/tests;
# they do not grant admission, activation, publication, or revaluation.
B04_APPROVED_ARTIFACT_SHA256 = dict(_B04_HASHES)
B04_FROZEN_RANGES_SHA256 = _B04_RANGE_HASH
B04_ORIGIN_SUMMARY_SHA256 = _B04_ORIGIN
B04_BASE_CATALOG_VERSION = _B04_BASE_CATALOG_VERSION
B04_BASE_MANIFEST_SHA256 = _B04_BASE_MANIFEST_SHA256
B04_PRIVATE_REVIEW_SCHEMA_VERSION = _B04_SCHEMA
B04_PRIVATE_REVIEW_PROFILE = _B04_PROFILE
B04_PRIMARY_MODELS: dict[str, str] = {ticker: "residual_income" for ticker in B04_IDENTITIES}

# B05 is the closed private550 overlay prepared from the admitted540 B04
# catalog.  Hashes are over the metadata-normalized initial-pass artifacts
# returned by prepare_us_expansion_integration.normalize; no economics or
# range values are recomputed here.
B05_IDENTITIES: dict[str, str] = {
    "USLM": "0000082020",
    "IIIN": "0000764401",
    "POWL": "0000080420",
    "PLPC": "0000080035",
    "HWKN": "0000046250",
    "AVNT": "0001122976",
    "EBF": "0000033002",
    "ACU": "0000002098",
    "TILE": "0000715787",
    "NWPX": "0001001385",
}
_B05_IDENTITIES = tuple(B05_IDENTITIES.items())
_B05_HASHES = {
    "USLM": "a17ce9db75fdf28cd7559b8e3464022ccbea453c99603e5ff3ad3d1cb204ae9c",
    "IIIN": "7fa4542eb52a48f3d51ed0684c1263db3b703f15497869e6eaa4e64687d36870",
    "POWL": "4615bd8febce7ab9c34073c0f180b88538bd7d197d39fdfc6885f5bdb3bba771",
    "PLPC": "441ecc5a5bcebdefab2c7b2bbb5dba68a28d66f48e8841958467377f6e9e5b5f",
    "HWKN": "fc2f5edc146aa94d7a36bd2e64f6d501a8e77b83285fd888942719b283396fbd",
    "AVNT": "57cb8536d9ca96a2d9f048712e49086e662bbee1e9839810c22e4f6ac4dc36bd",
    "EBF": "697d7b5b7a182ea25e03742c31b23fbb876eae893a43dc662eb0352dbd1e5627",
    "ACU": "7e6ce727a0cf54e77b27947e68f58f5aaa544febea62c7740588e3396b34a9b3",
    "TILE": "74eb3d76b79d2fa594990f058eab6ca2d3e8cb271a1e63c91e5f96e977e6ede0",
    "NWPX": "6198025aa8bae73a7449223e628512d2572e7b91f0a1b9688024d597cf3e7541",
}
_B05_SCHEMA = "FINSIGHT-PRIVATE-INTEGRATION-REVIEW-5"
_B05_PROFILE = "B05-FROZEN-PRIVATE-1"
_B05_CUTOFF = "2026-10-07"
_B05_ORIGIN = "64a1ee88f2b37a640499c36eb1c89a3cda8ee5a8cb55b17e4ed473f1d54e3132"
_B05_RANGE_HASH = "afbc69413151b05f3160d61c4803436a18b955d8f35be59ebc1558e903ae6b70"
_B05_BASE_CATALOG_VERSION = "US-ADMITTED-B04-540-868c81efc1d6625a07c4a086"
_B05_BASE_MANIFEST_SHA256 = "98609f24350af2118db0c6f3f4a9ea57ee50e1e029def0637e7f6748e411b6f5"
_B05_APPROVAL_SHA256 = "2228ebdf9ddd27c8714409c609e775d6e21b09ca5ab6dfadff11e3ac6ab83d95"
_B05_CONSUMER_ARCHETYPES = frozenset()

B05_APPROVED_ARTIFACT_SHA256 = dict(_B05_HASHES)
B05_FROZEN_RANGES_SHA256 = _B05_RANGE_HASH
B05_ORIGIN_SUMMARY_SHA256 = _B05_ORIGIN
B05_BASE_CATALOG_VERSION = _B05_BASE_CATALOG_VERSION
B05_BASE_MANIFEST_SHA256 = _B05_BASE_MANIFEST_SHA256
B05_PRIVATE_REVIEW_SCHEMA_VERSION = _B05_SCHEMA
B05_PRIVATE_REVIEW_PROFILE = _B05_PROFILE
B05_PRIMARY_MODELS: dict[str, str] = {ticker: "residual_income" for ticker in B05_IDENTITIES}

# Public names are intentionally read-only by convention and make the sealed
# profile auditable by package builders/tests without exposing any fresh
# valuation inputs.
B03_APPROVED_ARTIFACT_SHA256 = dict(_B03_HASHES)
B03_FROZEN_RANGES_SHA256 = _B03_RANGE_HASH
B03_ORIGIN_SUMMARY_SHA256 = _B03_ORIGIN
B03_BASE_CATALOG_VERSION = _B03_BASE_CATALOG_VERSION
B03_BASE_MANIFEST_SHA256 = _B03_BASE_MANIFEST_SHA256
B03_PRIVATE_REVIEW_SCHEMA_VERSION = _B03_SCHEMA
B03_PRIVATE_REVIEW_PROFILE = _B03_PROFILE
B03_PRIMARY_MODELS: dict[str, str] = {ticker: "residual_income" for ticker in B03_IDENTITIES}


def _expected_primary_model(ticker: str) -> str:
    try:
        return _EXPECTED_PRIMARY_MODELS[ticker]
    except KeyError:
        _fail("ticker is not a selected B01 identity")
        return ""  # unreachable; keeps static analyzers satisfied

_PRIVATE_REVIEW_FIELDS = frozenset(
    {
        "schema_version",
        "private_only",
        "public_release_authorized",
        "auto_revaluation",
        "cutoff",
        "approved_artifact_sha256",
        "identities",
        "frozen_ranges",
        "origin_summary_sha256",
        "approval_sha256",
    }
)

# Keys that would carry an input/recipe/evidence payload across the private
# review boundary.  We reject these rather than silently projecting around a
# tampered artifact, while ordinary unknown safe keys are simply not copied.
_FORBIDDEN_KEY_PARTS = (
    "source_ledger",
    "sourceledger",
    "source_packet",
    "companyfacts",
    "company_facts",
    "eod",
    "market_price",
    "recipe",
    "private_payload",
    "private_data",
    "private_input",
    "raw_financial",
    "raw_statement",
    "financials",
    "financial_data",
)

_ISSUER_FIELDS = (
    "cik",
    "ticker",
    "issuer_name",
    "finsight_sector",
    "primary_archetype",
    "secondary_archetypes",
)
_SOURCE_FIELDS = ("form", "period_end", "filed_date", "accession", "url", "note")
_POLICY_FIELDS = ("primary", "supporting", "blend_models", "reason", "fallback_from", "scope")
_MODEL_FIELDS = (
    "model",
    "output_type",
    "currency",
    "intrinsic_value_per_share",
    "conditional_value_per_share",
    "publication_state",
    "errors",
    "warnings",
)
_ASSUMPTION_FIELDS = (
    'scope',
    "forecast_policy_version",
    "history_policy_version",
    "history_years_used",
    "normalization_basis",
    "assumption_source_mix",
    "forecast_years",
    "forecast_mode",
    "initial_revenue_growth",
    "target_operating_margin",
    "terminal_growth",
    "discount_policy_version",
    "discount_calibration_type",
)
_REVIEW_FIELDS = (
    "publication_state",
    "confidence_grade",
    "errors",
    "warnings",
    "price_dependent_inputs_used",
)
_RELIABILITY_FIELDS = ("label", "reasons", "warnings")
_BOUNDARY_FIELDS = (
    "raw_financial_statement_values_included",
    "stock_prices_used",
    "public_payload_contains",
)
_MARKET_FIELDS = ("status", "reason")


def _fail(message: str) -> None:
    raise ValueError(f"private review artifact rejected: {message}")


def _copy_fields(value: object, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {field: deepcopy(value[field]) for field in fields if field in value}


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _string_list(value: object, *, label: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _fail(f"{label} must be a list of strings")


def _walk_forbidden_keys(value: object, path: str = "artifact") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                _fail(f"{path} contains a non-string key")
            lowered = key.casefold().replace("-", "_")
            # This is the public boundary declaration, not a financial
            # payload.  It is intentionally retained in the projection.
            boundary_declaration = (
                path.endswith(".data_boundary")
                and lowered == "raw_financial_statement_values_included"
            )
            if not boundary_declaration and any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
                _fail(f"forbidden private payload key at {path}.{key}")
            _walk_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden_keys(child, f"{path}[{index}]")


def _normalized_range(value: object, *, label: str) -> dict[str, float | None]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    keys = set(value)
    if keys not in ({"low", "base", "high"}, {"low", "base", "high", "label"}):
        _fail(f"{label} has unexpected range keys")
    if "label" in value and value["label"] != _RANGE_LABEL:
        _fail(f"{label} label changed")
    result: dict[str, float | None] = {}
    for key in _RANGE_KEYS:
        item = value[key]
        if item is not None and not _is_number(item):
            _fail(f"{label}.{key} is not a finite number or null")
        result[key] = item
    return result


def _validate_frozen_ranges(
    value: object, *, batch02: bool = False, batch03: bool = False, batch04: bool = False, batch05: bool = False
) -> dict[str, dict[str, float | None]]:
    if sum((batch02, batch03, batch04, batch05)) > 1:
        _fail("private profile selector is ambiguous")
    if batch05:
        tickers = tuple(ticker for ticker, _ in _B05_IDENTITIES)
        expected_numeric, expected_null, expected_hash = 10, 0, _B05_RANGE_HASH
    elif batch04:
        tickers = tuple(ticker for ticker, _ in _B04_IDENTITIES)
        expected_numeric, expected_null, expected_hash = 10, 0, _B04_RANGE_HASH
    elif batch03:
        tickers = tuple(ticker for ticker, _ in _B03_IDENTITIES)
        expected_numeric, expected_null, expected_hash = 8, 2, _B03_RANGE_HASH
    elif batch02:
        tickers = tuple(ticker for ticker, _ in _B02_IDENTITIES)
        expected_numeric, expected_null, expected_hash = 9, 1, _B02_RANGE_HASH
    else:
        tickers = _EXPECTED_TICKERS
        expected_numeric, expected_null, expected_hash = 7, 3, APPROVED_RANGES_SHA256
    if not isinstance(value, dict) or set(value) != set(tickers):
        _fail("frozen ranges are not the exact closed-profile denominator")
    normalized: dict[str, dict[str, float | None]] = {}
    numeric_count = 0
    null_count = 0
    for ticker in tickers:
        entry = value[ticker]
        if not isinstance(entry, dict) or set(entry) != set(_RANGE_KEYS):
            _fail(f"frozen_ranges.{ticker} must contain only low/base/high")
        row = _normalized_range(entry, label=f"frozen_ranges.{ticker}")
        if all(row[key] is None for key in _RANGE_KEYS):
            null_count += 1
        elif all(_is_number(row[key]) for key in _RANGE_KEYS):
            if not row["low"] <= row["base"] <= row["high"]:  # type: ignore[operator]
                _fail(f"frozen_ranges.{ticker} is not ordered")
            numeric_count += 1
        else:
            _fail(f"frozen_ranges.{ticker} mixes numeric and null values")
        normalized[ticker] = row
    if numeric_count != expected_numeric or null_count != expected_null:
        _fail("frozen ranges have the wrong numeric/null counts")
    if sha256_bytes(canonical_json_bytes(normalized)) != expected_hash:
        _fail("frozen ranges do not match the approved floor-range anchor")
    return normalized


def _validate_manifest(
    manifest: object,
) -> tuple[Mapping[str, Any], dict[str, dict[str, float | None]]]:
    if not isinstance(manifest, dict) or manifest.get("private_integration_only") is not True:
        _fail("private integration flag is absent")
    private_review = manifest.get("private_review")
    if not isinstance(private_review, dict):
        _fail("private_review object is missing")
    batch02 = private_review.get("schema_version") == _B02_SCHEMA
    batch03 = private_review.get("schema_version") == _B03_SCHEMA
    batch04 = private_review.get("schema_version") == _B04_SCHEMA
    batch05 = private_review.get("schema_version") == _B05_SCHEMA
    fields = set(_PRIVATE_REVIEW_FIELDS) | ({"profile"} if batch02 or batch03 or batch04 or batch05 else set())
    if set(private_review) != fields:
        _fail("private_review schema fields are not exact")
    if private_review["schema_version"] not in {
        PRIVATE_REVIEW_SCHEMA_VERSION,
        _B02_SCHEMA,
        _B03_SCHEMA,
        _B04_SCHEMA,
        _B05_SCHEMA,
    }:
        _fail("private_review schema version is not supported")
    if private_review["private_only"] is not True:
        _fail("private_only must be true")
    if private_review["public_release_authorized"] is not False:
        _fail("public release must remain unauthorized")
    if private_review["auto_revaluation"] is not False:
        _fail("auto revaluation must remain disabled")
    if batch02 and private_review['profile']!=_B02_PROFILE:
        _fail('Batch02 private profile is not supported')
    if batch03 and private_review["profile"] != _B03_PROFILE:
        _fail("Batch03 private profile is not supported")
    if batch04 and private_review["profile"] != _B04_PROFILE:
        _fail("Batch04 private profile is not supported")
    if batch05 and private_review["profile"] != _B05_PROFILE:
        _fail("Batch05 private profile is not supported")
    expected_cutoff = (
        _B05_CUTOFF
        if batch05
        else _B04_CUTOFF
        if batch04
        else _B03_CUTOFF
        if batch03
        else "2026-10-05"
        if batch02
        else PRIVATE_REVIEW_CUTOFF
    )
    if private_review["cutoff"] != expected_cutoff:
        _fail("cutoff changed")

    if batch03:
        for authority_field in (
            "admission",
            "activation",
            "publication",
            "public_release_authorized",
            "auto_revaluation",
        ):
            if manifest.get(authority_field) is True:
                _fail(f"B03 {authority_field} authority is not permitted")
        # A B03 package is only a private successor of the admitted 520
        # catalog.  Bind both the parent identity and its retained copy so a
        # later private package cannot inherit stale B01/B02 grant claims.
        # The package builder first calls this helper with only the private
        # review wrapper; once final-manifest pins are present, all three are
        # mandatory and exact.
        pin_fields = {
            "base_catalog_version",
            "base_manifest_sha256",
            "preserved_prior_estimate_sha256",
        }
        if pin_fields & set(manifest):
            if manifest.get("base_catalog_version") != _B03_BASE_CATALOG_VERSION:
                _fail("B03 base catalog version changed")
            if manifest.get("base_manifest_sha256") != _B03_BASE_MANIFEST_SHA256:
                _fail("B03 base manifest hash changed")
            preserved = manifest.get("preserved_prior_estimate_sha256")
            if (
                not isinstance(preserved, dict)
                or preserved.get("integration-parent-manifest.json")
                != _B03_BASE_MANIFEST_SHA256
            ):
                _fail("B03 parent manifest preservation pin changed")

    if batch04:
        for authority_field in (
            "admission",
            "activation",
            "publication",
            "public_release_authorized",
            "auto_revaluation",
        ):
            if manifest.get(authority_field) is True:
                _fail(f"B04 {authority_field} authority is not permitted")
        # B04 is a private overlay only.  Inherited local-admission,
        # supported-refresh, or approved-base grant wrappers would silently
        # widen this profile's authority, so reject the wrapper keys rather
        # than ignoring them.
        stale_grant_keys = {
            "approved_base_inheritance",
            "approved_base_manifest_sha256",
            "admission_prepared_only",
            "admission_predecessor_manifest_sha256",
            "local_admission",
            "supported_refresh_integration",
            "release_scope_approval_sha256",
            "admission_authorized",
            "activation_authorized",
            "publication_authorized",
            "local_activation_authorized",
            "local_public_visibility_authorized",
            "automatic_new_source_revaluation",
        }
        inherited = stale_grant_keys & set(manifest)
        if inherited:
            _fail("B04 inherited release grant keys are not permitted")
        pin_fields = {
            "base_catalog_version",
            "base_manifest_sha256",
            "preserved_prior_estimate_sha256",
        }
        if pin_fields & set(manifest):
            if manifest.get("base_catalog_version") != _B04_BASE_CATALOG_VERSION:
                _fail("B04 base catalog version changed")
            if manifest.get("base_manifest_sha256") != _B04_BASE_MANIFEST_SHA256:
                _fail("B04 base manifest hash changed")
            preserved = manifest.get("preserved_prior_estimate_sha256")
            if (
                not isinstance(preserved, dict)
                or preserved.get("integration-parent-manifest.json") != _B04_BASE_MANIFEST_SHA256
            ):
                _fail("B04 parent manifest preservation pin changed")

    if batch05:
        for authority_field in (
            "admission",
            "activation",
            "publication",
            "public_release_authorized",
            "auto_revaluation",
        ):
            if manifest.get(authority_field) is True:
                _fail(f"B05 {authority_field} authority is not permitted")
        stale_grant_keys = {
            "approved_base_inheritance",
            "approved_base_manifest_sha256",
            "admission_prepared_only",
            "admission_predecessor_manifest_sha256",
            "local_admission",
            "supported_refresh_integration",
            "release_scope_approval_sha256",
            "admission_authorized",
            "activation_authorized",
            "publication_authorized",
            "local_activation_authorized",
            "local_public_visibility_authorized",
            "automatic_new_source_revaluation",
        }
        if stale_grant_keys & set(manifest):
            _fail("B05 inherited release grant keys are not permitted")
        pin_fields = {"base_catalog_version", "base_manifest_sha256", "preserved_prior_estimate_sha256"}
        if pin_fields & set(manifest):
            if manifest.get("base_catalog_version") != _B05_BASE_CATALOG_VERSION:
                _fail("B05 base catalog version changed")
            if manifest.get("base_manifest_sha256") != _B05_BASE_MANIFEST_SHA256:
                _fail("B05 base manifest hash changed")
            preserved = manifest.get("preserved_prior_estimate_sha256")
            if not isinstance(preserved, dict) or preserved.get("integration-parent-manifest.json") != _B05_BASE_MANIFEST_SHA256:
                _fail("B05 parent manifest preservation pin changed")

    identities = private_review["identities"]
    expected_identities = (
        dict(_B05_IDENTITIES)
        if batch05
        else dict(_B04_IDENTITIES)
        if batch04
        else dict(_B03_IDENTITIES)
        if batch03
        else dict(_B02_IDENTITIES)
        if batch02
        else _EXPECTED_IDENTITIES
    )
    if identities != expected_identities:
        _fail("closed-profile identities changed")
    approved = private_review["approved_artifact_sha256"]
    if not isinstance(approved, dict) or set(approved) != set(expected_identities):
        _fail("approved artifact index is not the exact closed-profile denominator")
    if any(not _is_sha256(value) for value in approved.values()):
        _fail("approved artifact index contains an invalid hash")

    if batch02 and approved!=_B02_HASHES:
        _fail('Batch02 frozen artifact/warning hashes changed')
    if batch03 and approved != _B03_HASHES:
        _fail("Batch03 frozen artifact/warning hashes changed")
    if batch04 and approved != _B04_HASHES:
        _fail("Batch04 frozen artifact/warning hashes changed")
    if batch05 and approved != _B05_HASHES:
        _fail("Batch05 frozen artifact/warning hashes changed")
    frozen_ranges = _validate_frozen_ranges(
        private_review["frozen_ranges"], batch02=batch02, batch03=batch03, batch04=batch04, batch05=batch05
    )

    for field in ("origin_summary_sha256", "approval_sha256"):
        if not _is_sha256(private_review[field]):
            _fail(f"{field} is not a sha256")
    expected_origin = (
        _B05_ORIGIN
        if batch05
        else _B04_ORIGIN
        if batch04
        else _B03_ORIGIN
        if batch03
        else _B02_ORIGIN
        if batch02
        else ORIGIN_SUMMARY_SHA256
    )
    if private_review["origin_summary_sha256"] != expected_origin:
        _fail("origin summary is not the approved floor verification")
    if batch05 and private_review["approval_sha256"] != _B05_APPROVAL_SHA256:
        _fail("Batch05 preparation authority is not the approved direct-human record")
    return private_review, frozen_ranges


def _validate_list_fields(mapping: object, fields: tuple[str, ...], *, label: str) -> None:
    if not isinstance(mapping, dict):
        _fail(f"{label} is missing")
    for field in fields:
        if field in mapping:
            _string_list(mapping[field], label=f"{label}.{field}")


def _validate_model_surface(
    value: object,
    *,
    expected_model: str,
    expected_value: float | None,
    expected_state: str,
    label: str,
) -> None:
    if not isinstance(value, dict):
        _fail(f"{label} is missing")
    if value.get("model") != expected_model:
        _fail(f"{label}.model changed")
    if value.get("publication_state") != expected_state:
        _fail(f"{label}.publication_state changed")
    actual = value.get("intrinsic_value_per_share")
    if expected_value is None:
        if actual is not None or value.get("conditional_value_per_share") is not None:
            _fail(f"{label} contains a value for a withheld scenario")
    elif not _is_number(actual) or actual != expected_value:
        _fail(f"{label} does not equal the frozen range")
    if "conditional_value_per_share" in value and value["conditional_value_per_share"] is not None:
        _fail(f"{label} contains an extra value channel")
    _validate_list_fields(value, ("errors", "warnings"), label=label)


def _validate_artifact(
    artifact: object,
    *,
    ticker: str,
    expected_range: Mapping[str, float | None],
    artifact_sha256: object,
    approved_sha256: object,
    batch02: bool = False,
    batch03: bool = False,
    batch04: bool = False,
    batch05: bool = False,
) -> Mapping[str, Any]:
    if not isinstance(artifact, dict):
        _fail("artifact must be an object")
    if sum((batch02, batch03, batch04, batch05)) > 1:
        _fail("private profile selector is ambiguous")
    identities = (
        dict(_B05_IDENTITIES)
        if batch05
        else dict(_B04_IDENTITIES)
        if batch04
        else dict(_B03_IDENTITIES)
        if batch03
        else dict(_B02_IDENTITIES)
        if batch02
        else _EXPECTED_IDENTITIES
    )
    if not isinstance(ticker, str) or ticker not in identities:
        _fail("ticker is not a selected closed-profile identity")
    if not _is_sha256(artifact_sha256) or artifact_sha256 != approved_sha256:
        _fail("artifact hash is not the approved index hash")
    canonical_hash = sha256_bytes(canonical_json_bytes(artifact))
    if canonical_hash != artifact_sha256:
        _fail("canonical artifact bytes hash does not match the approved hash")
    _walk_forbidden_keys(artifact)

    if artifact.get("schema_version") != "US-PUBLIC-VALUATION-1.2":
        _fail("artifact schema version is not B01's frozen public schema")
    if artifact.get("ticker") != ticker:
        _fail("artifact ticker does not match the selected ticker")
    if artifact.get("private_review_only") is not True:
        _fail("artifact is not marked private-review-only")
    numeric = expected_range["base"] is not None
    if artifact.get("availability_type") != ("conditional_estimate" if numeric else "not_available"):
        _fail("availability type changed")

    if batch03:
        expected_valuation_date = "2026-06-30" if ticker == _B03_KWR else _B03_CUTOFF
        if artifact.get("valuation_date") != expected_valuation_date:
            _fail("B03 valuation date changed")
        if artifact.get("assumption_date") != _B03_CUTOFF:
            _fail("B03 assumption/evidence date changed")
    if batch04:
        if artifact.get("valuation_date") != _B04_CUTOFF:
            _fail("B04 valuation date changed")
        if artifact.get("assumption_date") != _B04_CUTOFF:
            _fail("B04 assumption/evidence date changed")
    if batch05:
        if artifact.get("valuation_date") != _B05_CUTOFF:
            _fail("B05 valuation date changed")
        if artifact.get("assumption_date") != _B05_CUTOFF:
            _fail("B05 assumption/evidence date changed")

    issuer = artifact.get("issuer")
    if not isinstance(issuer, dict):
        _fail("issuer object is missing")
    if issuer.get("ticker") != ticker or issuer.get("cik") != identities[ticker]:
        _fail("issuer identity changed")
    archetype = (
        "consumer_operating"
        if (batch02 and ticker in {"WDFC", "FIZZ", "JBSS", "NGVC"})
        or (batch03 and ticker in _B03_CONSUMER_ARCHETYPES)
        or (batch04 and ticker in _B04_CONSUMER_ARCHETYPES)
        or (batch05 and ticker in _B05_CONSUMER_ARCHETYPES)
        else "industrial"
    )
    if issuer.get("primary_archetype") != archetype:
        _fail("primary archetype is not typed")
    if "secondary_archetypes" in issuer:
        _string_list(issuer["secondary_archetypes"], label="issuer.secondary_archetypes")

    source = artifact.get("source_financial_statement", artifact.get("source"))
    if not isinstance(source, dict):
        _fail("source statement object is missing")
    accession = source.get("accession", source.get("accession_number"))
    if not isinstance(accession, str) or not accession:
        _fail("source accession is missing")
    if "accession" in source and "accession_number" in source and source["accession"] != source["accession_number"]:
        _fail("source accession aliases disagree")

    policy = artifact.get("model_policy")
    primary_model = (
        "residual_income"
        if batch02 or batch03 or batch04 or batch05
        else _expected_primary_model(ticker)
    )
    if not isinstance(policy, dict) or policy.get("primary") != primary_model:
        _fail("model policy primary model changed")
    expected_scope = (
        "private_dated_recovery_review_not_admitted"
        if batch03 and ticker == _B03_KWR
        else "private_initial_review_not_admitted"
        if batch02 or batch03 or batch04 or batch05
        else "private_batch_review_not_admitted"
    )
    if policy.get("scope") != expected_scope:
        _fail("model policy scope changed")
    if artifact.get("primary_valuation_method") != primary_model:
        _fail("primary valuation method changed")

    expected_values = dict(expected_range)
    expected_state = "review_required" if numeric else "withheld"
    expected_range = _normalized_range(artifact.get("scenario_range"), label="scenario_range")
    if expected_range != expected_values:
        _fail("artifact scenario range changed")
    if numeric:
        if not expected_range["low"] <= expected_range["base"] <= expected_range["high"]:  # type: ignore[operator]
            _fail("numeric range is not ordered")

    review = artifact.get("review")
    if not isinstance(review, dict) or review.get("publication_state") != expected_state:
        _fail("review state changed")
    _validate_list_fields(review, ("errors", "warnings"), label="review")
    boundary = artifact.get("data_boundary")
    if not isinstance(boundary, dict):
        _fail("data boundary is missing")
    if (
        boundary.get("raw_financial_statement_values_included") is not False
        or boundary.get("stock_prices_used") is not False
    ):
        _fail("data boundary is not public-safe")
    reliability = artifact.get("reliability")
    if not isinstance(reliability, dict):
        _fail("reliability object is missing")
    if reliability.get("label") != ("Low" if numeric else None):
        _fail("reliability label changed")
    _validate_list_fields(reliability, ("reasons", "warnings"), label="reliability")

    models = artifact.get("models")
    if not isinstance(models, dict) or set(models) != {primary_model}:
        _fail("model surface is not exact")
    _validate_model_surface(
        models[primary_model],
        expected_model=primary_model,
        expected_value=expected_values["base"],
        expected_state=expected_state,
        label="models." + primary_model,
    )
    scenarios = artifact.get("scenarios")
    if not isinstance(scenarios, dict) or set(scenarios) != set(_SCENARIOS):
        _fail("scenario surface is not exact")
    for scenario, range_key in zip(_SCENARIOS, ("low", "base", "high")):
        row = scenarios[scenario]
        if not isinstance(row, dict) or set(row) != {primary_model}:
            _fail(f"scenarios.{scenario} model surface is not exact")
        _validate_model_surface(
            row[primary_model],
            expected_model=primary_model,
            expected_value=expected_values[range_key],
            expected_state=expected_state,
            label=f"scenarios.{scenario}.{primary_model}",
        )
    return artifact


def _project_source(value: Mapping[str, Any]) -> dict[str, Any]:
    source = _copy_fields(value, _SOURCE_FIELDS)
    # B01's captured artifacts used ``accession_number``/``source_url``;
    # expose the normal public names without carrying the private wrapper
    # vocabulary forward.
    if "accession" not in source and "accession_number" in value:
        source["accession"] = deepcopy(value["accession_number"])
    if "url" not in source and "source_url" in value:
        source["url"] = deepcopy(value["source_url"])
    return source


def _project_model(value: Mapping[str, Any]) -> dict[str, Any]:
    return _copy_fields(value, _MODEL_FIELDS)


def _project_private_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    ticker = artifact["ticker"]
    source = artifact.get("source_financial_statement", artifact.get("source"))
    models = artifact["models"]
    scenarios = artifact["scenarios"]
    projected: dict[str, Any] = {
        key: deepcopy(artifact[key])
        for key in (
            "schema_version",
            "valuation_date",
            "assumption_date",
            "market",
            "currency",
            "ticker",
            "availability_type",
            "primary_valuation_method",
            "private_review_only",
        )
        if key in artifact
    }
    projected["issuer"] = _copy_fields(artifact["issuer"], _ISSUER_FIELDS)
    projected["source_financial_statement"] = _project_source(source)
    projected["model_policy"] = _copy_fields(artifact["model_policy"], _POLICY_FIELDS)
    projected["public_assumptions"] = _copy_fields(
        artifact.get("public_assumptions"), _ASSUMPTION_FIELDS
    )
    projected["models"] = {
        name: _project_model(models[name]) for name in sorted(models)
    }
    projected["scenarios"] = {
        scenario: {
            name: _project_model(scenarios[scenario][name])
            for name in sorted(scenarios[scenario])
        }
        for scenario in _SCENARIOS
    }
    projected["scenario_range"] = _copy_fields(
        artifact["scenario_range"], ("low", "base", "high", "label")
    )
    projected["review"] = _copy_fields(artifact["review"], _REVIEW_FIELDS)
    projected["reliability"] = _copy_fields(artifact["reliability"], _RELIABILITY_FIELDS)
    projected["data_boundary"] = _copy_fields(artifact.get("data_boundary"), _BOUNDARY_FIELDS)
    projected["market_comparison"] = _copy_fields(artifact.get("market_comparison"), _MARKET_FIELDS)
    return projected


def project_review_artifact(
    artifact: dict[str, Any],
    manifest: dict[str, Any],
    *,
    ticker: str,
    artifact_sha256: str,
) -> dict[str, Any]:
    """Return a public-safe or strictly private closed-profile projection.

    Without the exact private integration flag and schema, this function is
    intentionally just the existing public sanitizer.  A private projection
    never upgrades a source/review gate and cannot be enabled by a flag in the
    artifact itself.  A manifest that is private but whose ticker is outside
    its exact profile falls back to the ordinary sanitizer (for example, the
    old 520 rows in a B03 private530 candidate).
    """

    if isinstance(manifest, dict) and manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-B1620-LOCAL-ADMISSION-INHERITANCE-1','US-B1620-ADMITTED-RETENTION-CHILD-1'}:
        from .admitted_batches1620 import project
        return project(artifact, manifest, ticker=ticker, artifact_sha256=artifact_sha256)
    if isinstance(manifest, dict) and manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1':
        from .staged_batches1620 import project
        return project(artifact, manifest, ticker=ticker, artifact_sha256=artifact_sha256)

    if not isinstance(manifest, dict) or manifest.get("private_integration_only") is not True:
        return sanitize_public_artifact(artifact if isinstance(artifact, dict) else {})

    if manifest.get('private_review', {}).get('schema_version') == 'FINSIGHT-PRIVATE-INTEGRATION-REVIEW-B06-B10-1':
        from .private_batches0610 import project
        return project(artifact, manifest, ticker=ticker, artifact_sha256=artifact_sha256)

    if manifest.get('private_review', {}).get('schema_version') == 'FINSIGHT-PRIVATE-INTEGRATION-REVIEW-B16-B20-1':
        from .private_batches1620 import project
        return project(artifact, manifest, ticker=ticker, artifact_sha256=artifact_sha256)

    if manifest.get('private_review', {}).get('schema_version') == 'FINSIGHT-PRIVATE-INTEGRATION-REVIEW-B11-B15-1':
        from .private_batches1115 import project
        return project(artifact, manifest, ticker=ticker, artifact_sha256=artifact_sha256)

    private_review, frozen_ranges = _validate_manifest(manifest)
    batch02 = private_review["schema_version"] == _B02_SCHEMA
    batch03 = private_review["schema_version"] == _B03_SCHEMA
    batch04 = private_review["schema_version"] == _B04_SCHEMA
    batch05 = private_review["schema_version"] == _B05_SCHEMA
    # The private package is an overlay for exactly its ten selected rows.  A
    # broader manifest can still carry the original 520 (or future) universe,
    # but those rows must remain on the ordinary public sanitizer path and
    # must never inherit B01/B02/B03 private privileges.
    selected_identities = (
        dict(_B05_IDENTITIES)
        if batch05
        else dict(_B04_IDENTITIES)
        if batch04
        else dict(_B03_IDENTITIES)
        if batch03
        else dict(_B02_IDENTITIES)
        if batch02
        else _EXPECTED_IDENTITIES
    )
    if ticker not in selected_identities:
        return sanitize_public_artifact(artifact if isinstance(artifact, dict) else {})
    approved_hashes = private_review["approved_artifact_sha256"]
    if not isinstance(approved_hashes, dict):  # defensive; manifest validation already checks this
        _fail("approved artifact index is malformed")
    _validate_artifact(
        artifact,
        ticker=ticker,
        expected_range=frozen_ranges[ticker],
        artifact_sha256=artifact_sha256,
        approved_sha256=approved_hashes.get(ticker),
        batch02=batch02,
        batch03=batch03,
        batch04=batch04,
        batch05=batch05,
    )
    return _project_private_artifact(artifact)



def preserved_b03_public_parent(root, manifest: dict, ticker: str, raw: bytes) -> bool:
    """Preserve authentic admitted520 bytes, not private privileges or a new release grant."""
    if not isinstance(manifest, dict) or manifest.get("private_integration_only") is not True:
        return False
    review = manifest.get("private_review")
    if not isinstance(review, dict) or review.get("profile") != _B03_PROFILE:
        return False
    _validate_manifest(manifest)
    if ticker in dict(_B03_IDENTITIES):
        return False  # None of the ten new rows can borrow the predecessor's authority.
    from pathlib import Path
    import json
    directory = Path(root).resolve()
    parent_path = directory / "integration-parent-manifest.json"
    if parent_path.is_symlink() or not parent_path.is_file() or parent_path.resolve().parent != directory:
        _fail("B03 public parent must be a regular in-root file")
    parent_raw = parent_path.read_bytes()
    if sha256_bytes(parent_raw) != _B03_BASE_MANIFEST_SHA256:
        _fail("B03 authentic public parent bytes changed")
    parent = json.loads(parent_raw)
    if parent.get("catalog_version") != _B03_BASE_CATALOG_VERSION or len(parent.get("entries", [])) != 520:
        _fail("B03 public parent identity/count changed")
    entry = next((row for row in parent["entries"] if row["ticker"] == ticker), None)
    if entry is None or entry.get("artifact_sha256") != sha256_bytes(raw):
        _fail("B03 preserved public artifact bytes changed")
    current = next((row for row in manifest.get("entries", []) if row.get("ticker") == ticker), None)
    if current != entry:
        _fail("B03 current public parent record changed")
    return True


def preserved_b04_public_parent(root, manifest: dict, ticker: str, raw: bytes) -> bool:
    """Preserve authentic admitted530 bytes for a B04 private overlay."""
    if not isinstance(manifest, dict) or manifest.get("private_integration_only") is not True:
        return False
    review = manifest.get("private_review")
    if not isinstance(review, dict) or review.get("profile") != _B04_PROFILE:
        return False
    _validate_manifest(manifest)
    if ticker in dict(_B04_IDENTITIES):
        return False  # New B04 rows cannot borrow the predecessor's authority.
    from pathlib import Path
    import json

    directory = Path(root).resolve()
    parent_path = directory / "integration-parent-manifest.json"
    if parent_path.is_symlink() or not parent_path.is_file() or parent_path.resolve().parent != directory:
        _fail("B04 public parent must be a regular in-root file")
    parent_raw = parent_path.read_bytes()
    if sha256_bytes(parent_raw) != _B04_BASE_MANIFEST_SHA256:
        _fail("B04 authentic public parent bytes changed")
    parent = json.loads(parent_raw)
    if parent.get("catalog_version") != _B04_BASE_CATALOG_VERSION or len(parent.get("entries", [])) != 530:
        _fail("B04 public parent identity/count changed")
    entry = next((row for row in parent["entries"] if row["ticker"] == ticker), None)
    if entry is None or entry.get("artifact_sha256") != sha256_bytes(raw):
        _fail("B04 preserved public artifact bytes changed")
    current = next((row for row in manifest.get("entries", []) if row.get("ticker") == ticker), None)
    if current != entry:
        _fail("B04 current public parent record changed")
    return True


def preserved_b05_public_parent(root, manifest: dict, ticker: str, raw: bytes) -> bool:
    """Preserve authentic admitted540 bytes for a B05 private overlay."""
    if not isinstance(manifest, dict) or manifest.get("private_integration_only") is not True:
        return False
    review = manifest.get("private_review")
    if not isinstance(review, dict) or review.get("profile") != _B05_PROFILE:
        return False
    _validate_manifest(manifest)
    if ticker in dict(_B05_IDENTITIES):
        return False
    from pathlib import Path
    import json

    directory = Path(root).resolve()
    parent_path = directory / "integration-parent-manifest.json"
    if parent_path.is_symlink() or not parent_path.is_file() or parent_path.resolve().parent != directory:
        _fail("B05 public parent must be a regular in-root file")
    parent_raw = parent_path.read_bytes()
    if sha256_bytes(parent_raw) != _B05_BASE_MANIFEST_SHA256:
        _fail("B05 authentic public parent bytes changed")
    parent = json.loads(parent_raw)
    if parent.get("catalog_version") != _B05_BASE_CATALOG_VERSION or len(parent.get("entries", [])) != 540:
        _fail("B05 public parent identity/count changed")
    entry = next((row for row in parent["entries"] if row["ticker"] == ticker), None)
    if entry is None or entry.get("artifact_sha256") != sha256_bytes(raw):
        _fail("B05 preserved public artifact bytes changed")
    current = next((row for row in manifest.get("entries", []) if row.get("ticker") == ticker), None)
    if current != entry:
        _fail("B05 current public parent record changed")
    return True


__all__ = [
    "APPROVED_RANGES_SHA256",
    "B01_IDENTITIES",
    "B01_PRIMARY_MODELS",
    "B03_APPROVED_ARTIFACT_SHA256",
    "B03_BASE_CATALOG_VERSION",
    "B03_BASE_MANIFEST_SHA256",
    "B03_FROZEN_RANGES_SHA256",
    "B03_IDENTITIES",
    "B03_ORIGIN_SUMMARY_SHA256",
    "B03_PRIMARY_MODELS",
    "B03_PRIVATE_REVIEW_PROFILE",
    "B03_PRIVATE_REVIEW_SCHEMA_VERSION",
    "B04_APPROVED_ARTIFACT_SHA256",
    "B04_BASE_CATALOG_VERSION",
    "B04_BASE_MANIFEST_SHA256",
    "B04_FROZEN_RANGES_SHA256",
    "B04_IDENTITIES",
    "B04_ORIGIN_SUMMARY_SHA256",
    "B04_PRIMARY_MODELS",
    "B04_PRIVATE_REVIEW_PROFILE",
    "B04_PRIVATE_REVIEW_SCHEMA_VERSION",
    "B05_APPROVED_ARTIFACT_SHA256",
    "B05_BASE_CATALOG_VERSION",
    "B05_BASE_MANIFEST_SHA256",
    "B05_FROZEN_RANGES_SHA256",
    "B05_IDENTITIES",
    "B05_ORIGIN_SUMMARY_SHA256",
    "B05_PRIMARY_MODELS",
    "B05_PRIVATE_REVIEW_PROFILE",
    "B05_PRIVATE_REVIEW_SCHEMA_VERSION",
    "PRIVATE_REVIEW_CUTOFF",
    "PRIVATE_REVIEW_SCHEMA_VERSION",
    "preserved_b04_public_parent",
    "preserved_b05_public_parent",
    "project_review_artifact",
]
