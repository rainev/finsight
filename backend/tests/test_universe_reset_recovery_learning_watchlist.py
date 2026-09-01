"""Durable not-fully-recovered watchlist contracts."""

import pytest

from app.us_valuation.universe_reset_recovery_learning_watchlist import (
    CALL_NAME,
    TITLE,
    RecoveryLearningEntry,
    load_recovery_learning_watchlist,
)
from app.us_valuation.universe_reset_withheld import load_universe_reset_withheld


def test_recovery_learning_watchlist_has_a_stable_name_and_exact_current_set() -> None:
    assert TITLE == "Universe Reset Recovery Learning Watchlist"
    assert CALL_NAME == "Recovery Learning Watchlist"
    entries = load_recovery_learning_watchlist()
    assert tuple(row.ticker for row in entries) == (
        "NEE",
        "OMC",
        "TTWO",
        "CHTR",
        "CMCSA",
        "META",
        "WBD",
        "LYV",
        "ECHO",
        "GOOGL",
        "APP",
        "FOXA",
        "TKO",
        "PSKY",
        "F",
        "GPC",
        "HAS",
        "LOW",
        "NKE",
        "MGM",
        "CCL",
        "PHM",
        "SBUX",
        "DHI",
        "RCL",
        "NVR",
        "LEN",
        "AMZN",
        "YUM",
        "EL",
        "BKNG",
        "WYNN",
        "LVS",
        "TSLA",
        "EXPE",
        "LULU",
        "KDP",
        "GM",
        "NCLH",
        "APTV",
        "ABNB",
        "CVNA",
        "DASH",
        "ADM",
        "STZ",
        "CLX",
        "KO",
        "TAP",
        "TGT",
        "DG",
        "GIS",
        "KMB",
        "MKC",
        "SJM",
        "TSN",
        "SYY",
        "CHD",
        "COST",
        "DLTR",
        "MDLZ",
        "PM",
        "KHC",
        "BG",
        "ABT",
        "BAX",
        "BDX",
        "BMY",
        "RVTY",
        "HUM",
        "LLY",
        "CVS",
        "WST",
        "UHS",
        "PFE",
        "TMO",
        "JNJ",
        "MRK",
        "SYK",
        "DHR",
        "AMGN",
        "COO",
        "CAH",
        "UNH",
        "TECH",
        "BIIB",
        "VRTX",
        "INCY",
        "GILD",
        "BSX",
        "MCK",
        "LH",
        "RMD",
        "WAT",
        "ISRG",
        "CNC",
        "ALGN",
        "A",
        "DXCM",
        "EW",
        "CRL",
        "ZBH",
        "COR",
        "ELV",
        "ABBV",
        "MDT",
        "MRNA",
        "CI",
        "VTRS",
        "GEHC",
        "KVUE",
        "SOLV",
        "BA",
        "CAT",
        "CMI",
        "DAL",
        "EMR",
        "GE",
        "HUBB",
        "MMM",
        "PCAR",
        "PH",
        "DE",
        "PNR",
        "AOS",
        "SNA",
        "LUV",
        "UAL",
        "UNP",
        "CTAS",
        "RTX",
        "LHX",
        "TXT",
        "NSC",
        "JBHT",
        "HON",
        "JCI",
        "WAB",
        "AME",
        "CHRW",
        "FDX",
        "PWR",
        "AXON",
        "UPS",
        "LDOS",
        "NOC",
        "TDG",
        "GNRC",
        "HII",
        "UBER",
        "ETN",
        "FTV",
        "DD",
        "CARR",
        "VLTO",
        "GEV",
        "FERG",
        "FDXF",
        "HONA",
        "AMD",
        "INTC",
        "IBM",
        "APH",
        "KLAC",
        "ADBE",
        "COHR",
        "FLEX",
        "QCOM",
        "CDNS",
        "MCHP",
        "GEN",
        "PTC",
        "CSCO",
        "TYL",
        "JBL",
        "TRMB",
        "ROP",
        "SNPS",
        "INTU",
        "NVDA",
        "FFIV",
        "AKAM",
        "CTSH",
        "ON",
        "STX",
        "FTNT",
        "FSLR",
        "MPWR",
        "PLTR",
        "TEL",
    )
    assert entries[0].current_status == "withheld_after_recovery"
    assert all(row.initial_outcome == "withheld" for row in entries if row.batch <= 6)
    assert all(row.initial_outcome == "conditional_numeric_low" for row in entries if row.batch == 7)
    assert all(row.initial_outcome == "conditional_numeric_low" for row in entries if row.batch == 9 and row.ticker != "CLX")
    assert all(row.initial_outcome == "conditional_numeric_low" for row in entries if row.batch == 10 and row.ticker != "KMB")
    assert all(
        row.recovery_outcome in {"withheld", "conditional_numeric_low", "not_applicable"}
        for row in entries
    )
    assert all(
        row.current_status.startswith("conditional_numeric_low")
        for row in entries[1:7]
    )
    batch_03 = entries[7:]
    assert sum(row.current_status.startswith("conditional_numeric_low") for row in batch_03[:7]) == 5
    assert sum(row.current_status == "withheld_after_recovery" for row in batch_03[:7]) == 2
    assert all(row.current_status in {"withheld_after_recovery","conditional_numeric_low","conditional_numeric_low_equity_at_risk"} for row in entries[14:])
    batch_04=[row for row in entries if row.batch==4]
    assert tuple(row.ticker for row in batch_04)==("F","GPC","HAS","LOW","NKE","MGM")
    batch_05=[row for row in entries if row.batch==5]
    assert sum(row.current_status=="conditional_numeric_low_equity_at_risk" for row in batch_05)==2
    batch_06=[row for row in entries if row.batch==6]
    assert sum(row.current_status=="conditional_numeric_low_equity_at_risk" for row in batch_06)==1
    batch_07=[row for row in entries if row.batch==7]
    assert tuple(row.ticker for row in batch_07)==("EL","BKNG","WYNN","LVS","TSLA","EXPE")
    assert all(row.recovery_outcome=="not_applicable" for row in batch_07)
    assert sum(row.current_status=="conditional_numeric_low_equity_at_risk" for row in batch_07)==2
    batch_08=[row for row in entries if row.batch==8]
    assert tuple(row.ticker for row in batch_08)==("LULU","KDP","GM","NCLH","APTV","ABNB","CVNA","DASH")
    assert all(row.recovery_outcome=="not_applicable" for row in batch_08 if row.ticker in {"LULU","KDP","GM","ABNB","CVNA","DASH"})
    assert next(row for row in batch_08 if row.ticker=="NCLH").recovery_outcome=="withheld"
    assert next(row for row in batch_08 if row.ticker=="APTV").recovery_outcome=="conditional_numeric_low"
    assert sum(row.current_status=="conditional_numeric_low_equity_at_risk" for row in batch_08)==2
    batch_09=[row for row in entries if row.batch==9]
    assert tuple(row.ticker for row in batch_09)==("ADM","STZ","CLX","KO","TAP","TGT","DG","GIS")
    assert all(row.recovery_outcome=="not_applicable" for row in batch_09 if row.ticker!="CLX")
    assert next(row for row in batch_09 if row.ticker=="CLX").recovery_outcome=="conditional_numeric_low"
    batch_10=[row for row in entries if row.batch==10]
    assert tuple(row.ticker for row in batch_10)==("KMB","MKC","SJM","TSN")
    assert all(row.recovery_outcome=="not_applicable" for row in batch_10 if row.ticker!="KMB")
    assert next(row for row in batch_10 if row.ticker=="KMB").recovery_outcome=="conditional_numeric_low"
    batch_11=[row for row in entries if row.batch==11]
    assert tuple(row.ticker for row in batch_11)==("SYY","CHD","COST","DLTR","MDLZ","PM","KHC","BG")
    assert next(row for row in batch_11 if row.ticker=="SYY").recovery_outcome=="conditional_numeric_low"
    assert next(row for row in batch_11 if row.ticker=="BG").recovery_outcome=="withheld"
    assert all(row.recovery_outcome=="not_applicable" for row in batch_11 if row.ticker not in {"SYY","BG"})
    batch_12=[row for row in entries if row.batch==12]
    assert tuple(row.ticker for row in batch_12)==("ABT","BAX","BDX","BMY","RVTY","HUM","LLY","CVS","WST","UHS")
    assert all(row.recovery_outcome=="conditional_numeric_low" for row in batch_12 if row.ticker!="UHS")
    assert next(row for row in batch_12 if row.ticker=="UHS").recovery_outcome=="withheld"
    batch_13=[row for row in entries if row.batch==13]
    assert tuple(row.ticker for row in batch_13)==("PFE","TMO","JNJ","MRK","SYK","DHR","AMGN","COO","CAH","UNH")
    assert all(row.initial_outcome=="conditional_numeric_low" for row in batch_13)
    assert all(row.recovery_outcome=="not_applicable" for row in batch_13)
    batch_14=[row for row in entries if row.batch==14]
    assert tuple(row.ticker for row in batch_14)==("TECH","BIIB","VRTX","INCY","GILD","BSX","MCK")
    assert {"HCA","REGN","IDXX"}.isdisjoint({row.ticker for row in entries})
    assert all(row.initial_outcome=="conditional_numeric_low" for row in batch_14)
    assert all(row.recovery_outcome=="not_applicable" for row in batch_14)
    batch_15=[row for row in entries if row.batch==15]
    assert tuple(row.ticker for row in batch_15)==("LH","RMD","WAT","ISRG","CNC","ALGN")
    assert all(row.initial_outcome=="conditional_numeric_low" for row in batch_15 if row.ticker in {"RMD","WAT","CNC"})
    assert all(row.recovery_outcome=="not_applicable" for row in batch_15 if row.ticker in {"RMD","WAT","CNC"})
    assert all(row.initial_outcome=="withheld" for row in batch_15 if row.ticker in {"LH","ISRG","ALGN"})
    assert all(row.recovery_outcome=="withheld" for row in batch_15 if row.ticker in {"LH","ISRG","ALGN"})
    assert next(row for row in batch_15 if row.ticker=="WAT").current_status=="conditional_numeric_low_equity_at_risk"
    batch_16=[row for row in entries if row.batch==16]
    assert tuple(row.ticker for row in batch_16)==("A","DXCM","EW","CRL","ZBH","COR","ELV")
    assert next(row for row in batch_16 if row.ticker=="A").initial_outcome=="conditional_numeric_low"
    assert next(row for row in batch_16 if row.ticker=="A").recovery_outcome=="not_applicable"
    assert all(row.initial_outcome=="withheld" for row in batch_16 if row.ticker!="A")
    assert all(row.recovery_outcome=="withheld" for row in batch_16 if row.ticker!="A")
    assert all(row.current_status=="conditional_numeric_low" for row in batch_16)
    assert "PODD" not in {row.ticker for row in entries}
    batch_17=[row for row in entries if row.batch==17]
    assert tuple(row.ticker for row in batch_17)==("ABBV","MDT","MRNA","CI","VTRS","GEHC","KVUE","SOLV")
    assert all(row.initial_outcome=="conditional_numeric_low" for row in batch_17)
    assert all(row.recovery_outcome=="not_applicable" for row in batch_17)
    assert {row.ticker for row in batch_17 if row.current_status=="conditional_numeric_low_equity_at_risk"}=={"MRNA","SOLV"}
    assert {"ZTS","STE"}.isdisjoint({row.ticker for row in entries})
    batch_18=[row for row in entries if row.batch==18]
    assert tuple(row.ticker for row in batch_18)==("BA","CAT","CMI","DAL","EMR")
    assert all(row.initial_outcome=="conditional_numeric_low" for row in batch_18)
    assert all(row.recovery_outcome=="not_applicable" for row in batch_18)
    assert next(row for row in batch_18 if row.ticker=="BA").current_status=="conditional_numeric_low_equity_at_risk"
    assert {"HWM","ADP","DOV","EFX","GD"}.isdisjoint({row.ticker for row in entries})
    batch_19=[row for row in entries if row.batch==19]
    assert tuple(row.ticker for row in batch_19)==("GE","HUBB","MMM","PCAR","PH","DE")
    assert all(row.initial_outcome=="conditional_numeric_low" for row in batch_19)
    assert all(row.recovery_outcome=="not_applicable" for row in batch_19)
    assert next(row for row in batch_19 if row.ticker=="MMM").current_status=="conditional_numeric_low_equity_at_risk"
    assert {"ITW","J","MAS","NDSN"}.isdisjoint({row.ticker for row in entries})
    batch_20=[row for row in entries if row.batch==20]
    assert tuple(row.ticker for row in batch_20)==("PNR","AOS","SNA","LUV","UAL","UNP","CTAS")
    assert all(row.initial_outcome=="conditional_numeric_low" for row in batch_20)
    assert all(row.recovery_outcome=="not_applicable" for row in batch_20)
    assert all(row.current_status=="conditional_numeric_low" for row in batch_20)
    assert {"ROL","SWK","PAYX"}.isdisjoint({row.ticker for row in entries})
    batch_21=[row for row in entries if row.batch==21]
    assert tuple(row.ticker for row in batch_21)==("RTX","LHX","TXT","NSC","JBHT")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_21)
    assert {"EME","GWW","CSX","EXPD","FAST"}.isdisjoint({row.ticker for row in entries})
    batch_22=[row for row in entries if row.batch==22]
    assert tuple(row.ticker for row in batch_22)==("HON","JCI","WAB")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_22)
    assert {"WM","IEX","ODFL","CPRT","LMT","ROK","FIX"}.isdisjoint({row.ticker for row in entries})
    batch_23=[row for row in entries if row.batch==23]
    assert tuple(row.ticker for row in batch_23)==("AME","CHRW","FDX","PWR","AXON","UPS","LDOS")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="conditional_numeric_low" and row.current_status=="conditional_numeric_low" for row in batch_23)
    assert {"RSG","URI","LII"}.isdisjoint({row.ticker for row in entries})
    batch_24=[row for row in entries if row.batch==24]
    assert tuple(row.ticker for row in batch_24)==("NOC","TDG","GNRC","HII","UBER","ETN")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="conditional_numeric_low" for row in batch_24)
    assert {row.ticker for row in batch_24 if row.current_status=="conditional_numeric_low_equity_at_risk"}=={"TDG","HII"}
    assert {"BLDR","TT","XYL","ALLE"}.isdisjoint({row.ticker for row in entries})
    batch_25=[row for row in entries if row.batch==25]
    assert tuple(row.ticker for row in batch_25)==("FTV","DD","CARR","VLTO","GEV","FERG","FDXF","HONA")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" for row in batch_25 if row.ticker!="HONA")
    assert next(row for row in batch_25 if row.ticker=="HONA").initial_outcome=="withheld"
    assert next(row for row in batch_25 if row.ticker=="HONA").recovery_outcome=="conditional_numeric_low"
    assert next(row for row in batch_25 if row.ticker=="FDXF").current_status=="conditional_numeric_low_equity_at_risk"
    assert {"IR","OTIS"}.isdisjoint({row.ticker for row in entries})
    batch_26=[row for row in entries if row.batch==26]
    assert tuple(row.ticker for row in batch_26)==("AMD","INTC","IBM","APH")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" for row in batch_26)
    assert next(row for row in batch_26 if row.ticker=="INTC").current_status=="conditional_numeric_low_equity_at_risk"
    assert {"SWKS","ADI","AMAT","GLW","HPQ","MSI"}.isdisjoint({row.ticker for row in entries})
    batch_27=[row for row in entries if row.batch==27]
    assert tuple(row.ticker for row in batch_27)==("KLAC","ADBE","COHR","FLEX")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" for row in batch_27)
    assert next(row for row in batch_27 if row.ticker=="COHR").current_status=="conditional_numeric_low_equity_at_risk"
    assert {"TER","TXN","LRCX","MU","IT","ADSK"}.isdisjoint({row.ticker for row in entries})
    batch_28=[row for row in entries if row.batch==28]
    assert tuple(row.ticker for row in batch_28)==("QCOM","CDNS","MCHP","GEN","PTC","CSCO","TYL","JBL")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_28)
    assert {"FICO","ZBRA"}.isdisjoint({row.ticker for row in entries})
    batch_29=[row for row in entries if row.batch==29]
    assert tuple(row.ticker for row in batch_29)==("TRMB","ROP","SNPS","INTU","NVDA","FFIV","AKAM")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_29)
    assert {"CIEN","NTAP","VRSN"}.isdisjoint({row.ticker for row in entries})
    batch_30=[row for row in entries if row.batch==30]
    assert tuple(row.ticker for row in batch_30)==("CTSH","ON","STX","FTNT","FSLR","MPWR","PLTR","TEL")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_30)
    assert {"TDY","BR"}.isdisjoint({row.ticker for row in entries})
    assert all(row.learning_themes for row in entries)
    assert all(row.revisit_triggers for row in entries)
    assert all(row.evidence_reports for row in entries)


def test_current_withheld_register_is_fully_bookmarked_without_changing_semantics() -> None:
    withheld = load_universe_reset_withheld()
    watchlist = load_recovery_learning_watchlist()
    assert {(row.ticker,row.cik) for row in withheld}.issubset({(row.ticker,row.cik) for row in watchlist})
    assert sum(row.current_status == "withheld_after_recovery" for row in watchlist) == 9
    assert sum(row.current_status.startswith("conditional_numeric_low") for row in watchlist) == 180


def test_watchlist_rejects_a_fully_recovered_or_unclassified_status() -> None:
    value = {
        "batch": 3,
        "ticker": "TEST",
        "cik": "0000000001",
        "issuer_name": "Test",
        "initial_outcome": "withheld",
        "recovery_outcome": "withheld",
        "current_status": "fully_recovered",
        "provisional_model": "test",
        "why_not_fully_recovered": "test",
        "learning_themes": ["test"],
        "revisit_triggers": ["test"],
        "evidence_reports": ["docs/test.md"],
    }
    with pytest.raises(ValueError, match="status"):
        RecoveryLearningEntry.from_dict(value)

    value["current_status"] = "withheld_after_recovery"
    value["initial_outcome"] = "numeric"
    with pytest.raises(ValueError, match="initial pass"):
        RecoveryLearningEntry.from_dict(value)

    value["initial_outcome"] = "conditional_numeric_low"
    value["recovery_outcome"] = "conditional_numeric_low"
    value["current_status"] = "conditional_numeric_low"
    with pytest.raises(ValueError, match="direct conditional"):
        RecoveryLearningEntry.from_dict(value)

    value["batch"] = 12
    assert RecoveryLearningEntry.from_dict(value).recovery_outcome == "conditional_numeric_low"
