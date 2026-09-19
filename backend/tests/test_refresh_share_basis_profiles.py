from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path

import pytest

from app.us_valuation.refresh_share_basis import (
    SHARE_PROFILE_BBY,
    SHARE_PROFILE_REPORTED_YTD_AND_COVER,
    ShareBasisReviewRequired,
    bind_current_share_basis,
    compile_share_basis_profile,
)


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "output/latest-universe-20260919/runtime"


def _recipe(ticker: str) -> dict:
    return json.loads((RUNTIME / "recipes" / f"{ticker}.json").read_text())


def _parsed(path: Path) -> dict:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text())
    return value["parsed"] if isinstance(value.get("parsed"), dict) else value


def _packet(*, ticker: str, cik: str, accession: str, form: str, report: str, filed: str, annual: str, structural: dict) -> dict:
    return {
        "issuer": {"ticker": ticker, "cik": cik},
        "submissions": {"cik": cik},
        "companyfacts": {"cik": cik},
        "controlling_filing": {
            "accessionNumber": accession,
            "form": form,
            "reportDate": report,
            "filingDate": filed,
        },
        "latest_annual_filing": {"accessionNumber": "annual", "reportDate": annual},
        "structural_filing": structural,
    }


def _real_packets() -> dict[str, dict]:
    return {
        "BBY": _packet(
            ticker="BBY", cik="0000764478", accession="0000764478-26-000042", form="10-Q",
            report="2026-08-01", filed="2026-09-04", annual="2026-01-31",
            structural=_parsed(ROOT / "output/latest-universe-20260919/final-discovery/parsed/parsed-structural/0000764478-26-000042-afe0f63c3987eb87-22e48483c36e5cf0.json.gz"),
        ),
        "GILD": _packet(
            ticker="GILD", cik="0000882095", accession="0000882095-26-000031", form="10-Q",
            report="2026-06-30", filed="2026-08-06", annual="2025-12-31",
            structural=_parsed(ROOT / "output/latest-universe-20260919/parsed/parsed-structural/0000882095-26-000031-2034f72ef5944dbf-22e48483c36e5cf0.json"),
        ),
        "INCY": _packet(
            ticker="INCY", cik="0000879169", accession="0000879169-26-000056", form="10-Q",
            report="2026-06-30", filed="2026-07-28", annual="2025-12-31",
            structural=_parsed(ROOT / "output/latest-universe-20260919/parsed/parsed-structural/0000879169-26-000056-0173bbb713d0d02c-22e48483c36e5cf0.json"),
        ),
    }


@pytest.mark.parametrize('ticker',['BBY','GILD','INCY'])
def test_actual_capture_envelopes_accept_sec_integer_cik(ticker):
    path=ROOT/'output/latest-universe-20260919/final-discovery/captures'/f'{ticker}.json.gz'
    packet=json.loads(gzip.decompress(path.read_bytes()))['packet']
    profile=compile_share_basis_profile(_recipe(ticker),project_root=ROOT)
    controlling=packet['controlling_filing']
    result=bind_current_share_basis(profile,packet,ticker=ticker,cik=profile['cik'],
        accession=controlling['accessionNumber'],report_period_end=controlling['reportDate'],cutoff='2026-09-19')
    assert result['base_shares']>0
    assert result['scenario_shares']['bear']>=result['scenario_shares']['base']>=result['scenario_shares']['bull']


def test_real_lineage_profiles_bind_current_share_basis() -> None:
    profiles = {
        ticker: compile_share_basis_profile(_recipe(ticker), project_root=ROOT)
        for ticker in ("BBY", "GILD", "INCY")
    }
    packets = _real_packets()
    results = {
        "BBY": bind_current_share_basis(
            profiles["BBY"], packets["BBY"], ticker="BBY", cik="0000764478",
            accession="0000764478-26-000042", report_period_end="2026-08-01", cutoff="2026-09-19",
        ),
        "GILD": bind_current_share_basis(
            profiles["GILD"], packets["GILD"], ticker="GILD", cik="0000882095",
            accession="0000882095-26-000031", report_period_end="2026-06-30", cutoff="2026-09-19",
        ),
        "INCY": bind_current_share_basis(
            profiles["INCY"], packets["INCY"], ticker="INCY", cik="0000879169",
            accession="0000879169-26-000056", report_period_end="2026-06-30", cutoff="2026-09-19",
        ),
    }
    assert profiles["BBY"]["profile"] == SHARE_PROFILE_BBY
    assert results["BBY"]["scenario_shares"]["base"] == pytest.approx(212100000.0)
    assert results["BBY"]["scenario_shares"]["bear"] == pytest.approx(217402500.0)
    assert results["GILD"]["profile"] == SHARE_PROFILE_REPORTED_YTD_AND_COVER
    assert results["GILD"]["scenario_shares"] == {
        "bear": pytest.approx(1243000000.0),
        "base": pytest.approx(1241477577.5),
        "bull": pytest.approx(1239955155.0),
    }
    assert results["INCY"]["scenario_shares"] == {
        "bear": pytest.approx(207670000.0),
        "base": pytest.approx(205183873.0),
        "bull": pytest.approx(202697746.0),
    }
    assert results["GILD"]["sources"]["reported_cover"]["unit"] == "xbrli:shares"


def test_reported_ytd_and_cover_profile_rejects_missing_ambiguous_identity_and_future_sources() -> None:
    profile = compile_share_basis_profile(_recipe("GILD"), project_root=ROOT)
    packet = _real_packets()["GILD"]

    missing = copy.deepcopy(packet)
    missing["structural_filing"]["facts"] = [
        row for row in missing["structural_filing"]["facts"]
        if row.get("local_name") != "WeightedAverageNumberOfDilutedSharesOutstanding"
    ]
    with pytest.raises(ShareBasisReviewRequired, match="weighted-diluted shares source fact is missing"):
        bind_current_share_basis(profile, missing, ticker="GILD", cik="0000882095",
                                 accession="0000882095-26-000031", report_period_end="2026-06-30", cutoff="2026-09-19")

    ambiguous = copy.deepcopy(packet)
    row = next(row for row in ambiguous["structural_filing"]["facts"]
               if row.get("local_name") == "WeightedAverageNumberOfDilutedSharesOutstanding"
               and row.get("period_start") == "2026-01-01")
    duplicate = copy.deepcopy(row)
    duplicate["value"] += 1
    ambiguous["structural_filing"]["facts"].append(duplicate)
    with pytest.raises(ShareBasisReviewRequired, match="weighted-diluted shares source facts are ambiguous"):
        bind_current_share_basis(profile, ambiguous, ticker="GILD", cik="0000882095",
                                 accession="0000882095-26-000031", report_period_end="2026-06-30", cutoff="2026-09-19")

    wrong_identity = copy.deepcopy(packet)
    cover = next(row for row in wrong_identity["structural_filing"]["facts"]
                 if row.get("local_name") == "EntityCommonStockSharesOutstanding")
    cover["entity_identifier"] = "0000000001"
    with pytest.raises(ShareBasisReviewRequired, match="complete issuer identity"):
        bind_current_share_basis(profile, wrong_identity, ticker="GILD", cik="0000882095",
                                 accession="0000882095-26-000031", report_period_end="2026-06-30", cutoff="2026-09-19")

    future = copy.deepcopy(packet)
    cover = next(row for row in future["structural_filing"]["facts"]
                 if row.get("local_name") == "EntityCommonStockSharesOutstanding")
    cover["period_end"] = "2026-09-20"
    with pytest.raises(ShareBasisReviewRequired, match="cover common-share source fact is missing"):
        bind_current_share_basis(profile, future, ticker="GILD", cik="0000882095",
                                 accession="0000882095-26-000031", report_period_end="2026-06-30", cutoff="2026-09-19")


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("qname", "QName or taxonomy identity"),
        ("namespace", "QName or taxonomy identity"),
        ("filed_date", "filed_date and report_date"),
        ("report_date", "filed_date and report_date"),
        ("accession", "share fact accession"),
        ("typed_dimensions", "share fact dimensions"),
    ],
)
def test_weighted_share_fact_identity_and_dates_are_strict(mutation: str, message: str) -> None:
    profile = compile_share_basis_profile(_recipe("GILD"), project_root=ROOT)
    packet = _real_packets()["GILD"]
    row = next(
        row for row in packet["structural_filing"]["facts"]
        if row.get("local_name") == "WeightedAverageNumberOfDilutedSharesOutstanding"
        and row.get("period_start") == "2026-01-01"
    )
    if mutation == "qname":
        row["qname"] = "spoof:WeightedAverageNumberOfDilutedSharesOutstanding"
    elif mutation == "namespace":
        row["namespace"] = "http://attacker.invalid/us-gaap/2026"
    elif mutation == "filed_date":
        row.pop("filed_date")
    elif mutation == "report_date":
        row.pop("report_date")
    elif mutation == "accession":
        row["source_accession"] = "0000000000-00-000000"
    elif mutation == "typed_dimensions":
        row["typed_dimensions"] = [["us-gaap:SomeAxis", "us-gaap:SomeMember", "typed"]]
    with pytest.raises(ShareBasisReviewRequired, match=message):
        bind_current_share_basis(
            profile,
            packet,
            ticker="GILD",
            cik="0000882095",
            accession="0000882095-26-000031",
            report_period_end="2026-06-30",
            cutoff="2026-09-19",
        )
