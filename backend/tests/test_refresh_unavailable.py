"""Fail-closed unavailable-record builder tests using frozen public/source artifacts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_unavailable import (
    UnavailableRecordError,
    build_unavailable_public_record,
)


ROOT = Path(__file__).parents[2]


def _public(ticker: str) -> dict:
    return json.loads((ROOT / "output/us-refresh-runtime/baseline/artifacts" / f"{ticker}.json").read_text())


def _cf_packet() -> dict:
    path = ROOT / 'output/us-refresh-runtime/acquisitions/a587eafaa664f46d3971d383f81d4290a6aa1a83fa14d507c405ccab5fcedab0/packets/CF.json'
    return json.loads(path.read_text())


def test_real_baseline_becomes_numeric_null_with_historical_source_label():
    previous = _public("DXCM")
    before = deepcopy(previous)
    result = build_unavailable_public_record(previous, "current source review is pending", "2026-09-08")
    assert previous == before
    assert result["review"]["publication_state"] == "withheld"
    assert result["availability_type"] == "not_available"
    assert result["scenario_range"]["low"] is None
    assert result["scenario_range"]["base"] is None
    assert result["scenario_range"]["high"] is None
    assert result["sensitivities"] == []
    assert result["scenarios"] == {}
    assert result["public_assumptions"] == {
        "forecast_mode": "unavailable_current_source_revalidation_required",
        "normalization_basis": "current_unavailable_source_revalidation_required",
        "assumption_source_mix": "current_source_not_verified",
    }
    assert "Historical last successful reference only" in result["source_financial_statement"]["note"]
    assert result["source_financial_statement"]["accession"] == previous["source_financial_statement"]["accession"]


def test_actual_captured_packet_binds_only_verified_current_reference():
    previous = _public("CF")
    result = build_unavailable_public_record(
        previous,
        "current valuation route is unavailable",
        "2026-08-14",
        source_packet=_cf_packet(),
        model_version="TEST-UNAVAILABLE-1",
    )
    assert result["model_version"] == "TEST-UNAVAILABLE-1"
    assert result["source_financial_statement"] == {
        "form": "10-Q",
        "period_end": "2026-06-30",
        "filed_date": "2026-08-06",
        "accession": "0001324404-26-000019",
        "note": "Current source reference verified from the supplied packet; no URL inferred or published.",
    }
    assert result["issuer"]["source_accessions"] == ["0001324404-26-000019"]
    assert "url" not in result["source_financial_statement"]
    assert result["models"]["conditional_estimate"]["conditional_value_per_share"] is None
    assert result['public_assumptions']['assumption_source_mix'] == 'source_identity_verified_economic_estimate_unavailable'


@pytest.mark.parametrize('field,value,reason', [
    ('reportDate','2026-08-07','reporting period is after filing'),
    ('form','8-K','not a supported financial filing'),
])
def test_matching_submission_does_not_make_an_invalid_financial_reference_valid(field,value,reason):
    packet = _cf_packet()
    filing = packet['packet']['controlling_filing']
    rows = packet['packet']['submissions']['filings']['recent']
    index = rows['accessionNumber'].index(filing['accessionNumber'])
    filing[field] = value
    rows[field][index] = value
    with pytest.raises(UnavailableRecordError,match=reason):
        build_unavailable_public_record(_public('CF'),'blocked','2026-08-14',source_packet=packet)


def test_bad_source_identity_and_cutoff_are_rejected():
    previous = _public("CF")
    packet = _cf_packet()
    with pytest.raises(UnavailableRecordError, match="CIK mismatch"):
        build_unavailable_public_record(previous, "blocked", "2026-08-14", source_packet=packet, cik="0001093557")

    bad = deepcopy(packet)
    bad["packet"]["controlling_filing"]["primaryDocument"] = "wrong.htm"
    with pytest.raises(UnavailableRecordError, match="disagrees with submissions"):
        build_unavailable_public_record(previous, "blocked", "2026-08-14", source_packet=bad)

    with pytest.raises(UnavailableRecordError, match="cutoff mismatch"):
        build_unavailable_public_record(previous, "blocked", "2026-08-05", source_packet=packet)


def test_source_packet_cutoff_and_reported_cik_are_checked():
    previous = _public("CF")
    bad = deepcopy(_cf_packet())
    bad["packet"]["cutoff"] = "2026-08-13"
    with pytest.raises(UnavailableRecordError, match="cutoff mismatch"):
        build_unavailable_public_record(previous, "blocked", "2026-08-14", source_packet=bad)

    bad = deepcopy(_cf_packet())
    bad["cik"] = "0001093557"
    with pytest.raises(UnavailableRecordError, match="source packet CIK mismatch"):
        build_unavailable_public_record(previous, "blocked", "2026-08-14", source_packet=bad)

    bad = deepcopy(_cf_packet())
    bad["packet"]["companyfacts"]["cik"] = "0001093557"
    with pytest.raises(UnavailableRecordError, match="companyfacts CIK mismatch"):
        build_unavailable_public_record(previous, "blocked", "2026-08-14", source_packet=bad)
