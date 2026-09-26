from __future__ import annotations

from app.routers import pse_valuations


USER = {"sub": 1, "role": "user"}


def test_active_api_list_has_exact_cumulative_catalog_and_counts() -> None:
    result = pse_valuations.list_pse_valuations(USER)
    assert result["catalog_status"] == "active"
    assert result["count"] == 282
    assert result["catalog_version"] == "PSE-V2-PHASE-B-B28-2026-09-26-1.0"
    tickers = [row["ticker"] for row in result["items"]]
    assert tickers == sorted(tickers)
    assert {"BLOOM", "BEL", "WEB", "SUN", "PHR", "WPI", "ACE", "BHI", "GPH", "MJC"} <= set(tickers)
    assert {"SMC", "LTG", "AGI", "COSCO", "FDC", "FPH", "ANS", "LPZ", "APO", "TFHI"} <= set(tickers)
    assert {"CPG", "ROCK", "SHNG", "DD", "ALLHC", "CDC", "ARA", "PHES", "RLT", "BRN"} <= set(tickers)
    assert {"IMI", "TECH", "ION", "CIC", "MVC", "CROWN", "STN", "LFM", "VMC", "SBS"} <= set(tickers)
    assert {"STI", "CEU", "FEU", "IPO", "MEDIC", "EURO", "MRSGI", "UPSON", "FRUIT", "KEEPR"} <= set(tickers)
    assert {"ALCO", "ALHI", "APVI", "CEI", "ELI", "GERI", "HOUSE", "KPPI", "PRMX", "SLI"} <= set(tickers)
    assert {"AXLM", "BALAI", "FCG", "FOOD", "SFI", "BCOR", "BNCOM", "BSC", "PMPC", "PPC"} <= set(tickers)
    assert {"SGP", "VVT", "PREIT", "SHLPH", "CHP", "PHN", "RCI", "TFC", "LBC", "MRC"} <= set(tickers)
    assert {"PBC", "PTC", "V", "BKR", "APC", "IPM", "SGI", "CTS", "REG", "ECP"} <= set(tickers)
    assert {"TBGI", "IS", "PHC", "LODE", "CPM", "APL", "ABA", "PAX", "LMG", "PRIM"} <= set(tickers)
    assert {"MACAY", "DMW", "HTI", "REDC", "TOP", "XG", "HI", "MBC", "LOTO", "PRC"} <= set(tickers)
    assert {"IDC", "JOH", "KEP", "LPC", "DWC", "OM", "MHC", "PHA", "SPM", "SRDC"} <= set(tickers)
    assert {"CSB", "ORE", "ECVC", "GREEN", "EGRN", "ENEX", "JAS", "NI", "WIN", "PA"} <= set(tickers)
    assert {"BC", "CA", "LC", "ATN", "OPM", "FJP", "DIZ", "IMP", "FERRO", "ABG"} <= set(tickers)
    assert {"AB", "FPI", "FAF", "BH", "GEO", "UPM", "MA", "X", "MFC", "SLF"} <= set(tickers)
    assert {"FFI", "FYN", "MAH", "MED", "MG", "ZHI", "LTL", "VLL", "VREIT", "ALLDY"} <= set(tickers)
    assert {"DHI", "HOME", "MM", "STR", "VLC", "UNH", "PNX", "ROX", "INFRA", "I"} <= set(tickers)
    assert {"AR", "BMM", "CYBR", "MGH", "MJIC", "PNC", "PORT", "SOC", "T", "TUBIG"} <= set(tickers)
    assert {"AAA", "EG", "NXGEN", "PTT"} <= set(tickers)
    assert sum(row["availability_type"] == "intrinsic_valuation" for row in result["items"]) == 34
    assert sum(row["availability_type"] == "market_relative_only" for row in result["items"]) == 205
    assert sum(row["availability_type"] == "not_available" for row in result["items"]) == 43
    assert sum(row["publication_state"] == "provisional" for row in result["items"]) == 239
    blocked = {"AB", "FAF", "GEO", "UPM", "X", "MFC", "SLF", "BC", "OPM", "CDC", "HOUSE", "IS", "PAX", "PRIM", "FYN", "MAH", "ZHI", "LTL", "VLL", "VREIT", "ALLDY", "DHI", "HOME", "STR", "VLC", "UNH", "PNX", "ROX", "INFRA", "I", "AR", "BMM", "CYBR", "MGH", "MJIC", "PNC", "PORT", "SOC", "T", "TUBIG", "AAA", "EG", "PTT"}
    assert {row["ticker"] for row in result["items"] if row["base"] is None} == blocked
    assert all(row["base"] is not None for row in result["items"] if row["ticker"] not in blocked)


def test_staged_api_detail_matches_catalog_artifact() -> None:
    result = pse_valuations.get_pse_valuation("ap", USER)
    assert result["ticker"] == "AP"
    assert result["publication_state"] == "provisional"
    assert result["catalog"]["catalog_status"] == "active"
    assert result["scenarios"]["base"]["value_per_share"] > 0


def test_market_relative_detail_preserves_intrinsic_limitations() -> None:
    result = pse_valuations.get_pse_valuation("BDO", USER)
    assert result["availability_type"] == "market_relative_only"
    assert result["publication_state"] == "provisional"
    assert result["blocking_reasons"]
    assert all(value is None for value in result["scenarios"].values())
    assert result["market_relative"]["estimates"]["base"] == 162.8
