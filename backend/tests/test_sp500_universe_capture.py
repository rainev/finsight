"""Contracts for the authorized historical S&P 500 reconstruction."""

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/capture_sp500_universe.py"
SPEC = importlib.util.spec_from_file_location("capture_sp500_universe", SCRIPT)
assert SPEC and SPEC.loader
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)


def test_pinned_source_constants_and_primary_share_classes() -> None:
    assert capture.REVISION_ID == 1369213082
    assert capture.REVISION_TIMESTAMP == "2026-08-13T15:09:18Z"
    assert capture.PRIMARY_CLASS == {
        "0001652044": "GOOGL",
        "0001754301": "FOXA",
        "0001564708": "NWSA",
    }
    assert capture.HISTORICAL_TICKER_EXCEPTIONS["EQR"]["cutoff_cik"] == "0000906107"


def test_parser_requires_the_named_constituent_table() -> None:
    with pytest.raises(ValueError, match="absent"):
        capture.parse_constituents(b"<html><table><tr><td>wrong</td></tr></table></html>")

    raw = b"""
    <table id="constituents">
      <tr><th>Symbol</th><th>Security</th><th>GICS Sector</th><th>GICS Sub-Industry</th><th>Headquarters Location</th><th>Date added</th><th>CIK</th><th>Founded</th></tr>
      <tr><td>ABC</td><td>ABC Corp</td><td>Industrials</td><td>Machinery</td><td>Boston</td><td>2020-01-01</td><td>123</td><td>1900</td></tr>
    </table>
    """
    rows = capture.parse_constituents(raw)
    assert rows == [
        {
            "Symbol": "ABC",
            "Security": "ABC Corp",
            "GICS Sector": "Industrials",
            "GICS Sub-Industry": "Machinery",
            "Headquarters Location": "Boston",
            "Date added": "2020-01-01",
            "CIK": "0000000123",
            "Founded": "1900",
        }
    ]
