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
        "PANW",
        "WDAY",
        "ORCL",
        "NOW",
        "SMCI",
        "NXPI",
        "ACN",
        "CRWD",
        "DDOG",
        "KEYS",
        "LITE",
        "HPE",
        "VRT",
        "AVGO",
        "MRVL",
        "SNDK",
        "Q",
        "AXP",
        "AFL",
        "AIG",
        "WRB",
        "CINF",
        "FITB",
        "MTB",
        "BEN",
        "HBAN",
        "L",
        "SPGI",
        "NTRS",
        "BRO",
        "PGR",
        "TRV",
        "KEY",
        "TFC",
        "STT",
        "WFC",
        "WMB",
        "AON",
        "SCHW",
        "GL",
        "AJG",
        "PNC",
        "RJF",
        "CFG",
        "JKHY",
        "FISV",
        "AMP",
        "C",
        "HIG",
        "GS",
        "MS",
        "CB",
        "ALL",
        "COF",
        "VLO",
        "IVZ",
        "ERIE",
        "ACGL",
        "FDS",
        "OKE",
        "MCO",
        "BRK.B",
        "MET",
        "TROW",
        "NDAQ",
        "EG",
        "GPN",
        "PFG",
        "FIS",
        "PRU",
        "WTW",
        "MA",
        "CME",
        "CPAY",
        "AIZ",
        "ARES",
        "RF",
        "CBOE",
        "IBKR",
        "TRGP",
        "BNY",
        "BX",
        "V",
        "KKR",
        "KMI",
        "MSCI",
        "XYZ",
        "ICE",
        "SYF",
        "PYPL",
        "COIN",
        "HOOD",
        "TPL",
        "APO",
        "BLK",
        "APD",
        "AVY",
        "BALL",
        "ECL",
        "EQT",
        "HAL",
        "IFF",
        "IP",
        "NUE",
        "PKG",
        "PPG",
        "SLB",
        "SHW",
        "CVX",
        "OXY",
        "EOG",
        "FCX",
        "CRH",
        "EXE",
        "ALB",
        "MLM",
        "STLD",
        "DVN",
        "COP",
        "NEM",
        "MOS",
        "CF",
        "VMC",
        "LYB",
        "LIN",
        "MPC",
        "PSX",
        "FANG",
        "BKR",
        "AMCR",
        "DOW",
        "CTVA",
        "APA",
        "SW",
        "XOM",
        "AEP",
        "ETR",
        "ES",
        "XEL",
        "SO",
        "LNT",
        "D",
        "PNW",
        "WEC",
        "PEG",
        "ATO",
        "CMS",
        "EIX",
        "AES",
        "PPL",
        "DTE",
        "AEE",
        "PCG",
        "FE",
        "SRE",
        "NRG",
        "ED",
        "EXC",
        "NI",
        "CNP",
        "DUK",
        "AWK",
        "VST",
        "EVRG",
        "CEG",
        "FRT",
        "UDR",
        "WY",
        "VTR",
        "DOC",
        "WELL",
        "KIM",
        "EQR",
        "CPT",
        "IRM",
        "REG",
        "MAA",
        "AVB",
        "ESS",
        "SBAC",
        "ARE",
        "BXP",
        "PLD",
        "CCI",
        "EQIX",
        "AMT",
        "CSGP",
        "SPG",
        "HST",
        "CBRE",
        "EXR",
        "DLR",
        "PSA",
        "INVH",
        "VICI",
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
    batch_31=[row for row in entries if row.batch==31]
    assert tuple(row.ticker for row in batch_31)==("PANW","WDAY","ORCL","NOW","SMCI","NXPI","ACN","CRWD")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" for row in batch_31 if row.ticker!="ORCL")
    assert next(row for row in batch_31 if row.ticker=="SMCI").current_status=="conditional_numeric_low_equity_at_risk"
    assert all(row.current_status=="conditional_numeric_low" for row in batch_31 if row.ticker not in {"SMCI","ORCL"})
    orcl=next(row for row in batch_31 if row.ticker=="ORCL")
    assert orcl.initial_outcome=="withheld" and orcl.recovery_outcome=="withheld" and orcl.current_status=="withheld_after_recovery"
    assert {"CDW","VRSK"}.isdisjoint({row.ticker for row in entries})
    batch_32=[row for row in entries if row.batch==32]
    assert tuple(row.ticker for row in batch_32)==("DDOG","KEYS","LITE","HPE","VRT","AVGO","MRVL","SNDK","Q")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_32)
    assert "GDDY" not in {row.ticker for row in entries}
    batch_33=[row for row in entries if row.batch==33]
    assert tuple(row.ticker for row in batch_33)==("AXP","AFL","AIG","WRB","CINF","FITB","MTB","BEN","HBAN")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_33)
    assert "MRSH" not in {row.ticker for row in entries}
    batch_34=[row for row in entries if row.batch==34]
    assert tuple(row.ticker for row in batch_34)==("L","SPGI","NTRS","BRO","PGR","TRV","KEY","TFC","STT")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.current_status=="conditional_numeric_low" for row in batch_34)
    assert all(row.recovery_outcome=="not_applicable" for row in batch_34 if row.ticker!="BRO")
    assert next(row for row in batch_34 if row.ticker=="BRO").recovery_outcome=="not_applicable"
    batch_35=[row for row in entries if row.batch==35]
    assert tuple(row.ticker for row in batch_35)==("WFC","WMB","AON","SCHW","GL","AJG","PNC","RJF","CFG","JKHY")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_35)
    batch_36=[row for row in entries if row.batch==36]
    assert tuple(row.ticker for row in batch_36)==("FISV","AMP","C","HIG","GS","MS","CB","ALL","COF","VLO")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_36 if row.ticker!="VLO")
    vlo=next(row for row in batch_36 if row.ticker=="VLO")
    assert vlo.initial_outcome=="withheld" and vlo.recovery_outcome=="withheld" and vlo.current_status=="withheld_after_recovery"
    batch_37=[row for row in entries if row.batch==37]
    assert tuple(row.ticker for row in batch_37)==("IVZ","ERIE","ACGL","FDS","OKE","MCO","BRK.B","MET","TROW","NDAQ")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_37)
    batch_38=[row for row in entries if row.batch==38]
    assert tuple(row.ticker for row in batch_38)==("EG","GPN","PFG","FIS","PRU","WTW","MA","CME","CPAY","AIZ")
    assert next(row for row in batch_38 if row.ticker=="GPN").current_status=="withheld_after_recovery"
    assert next(row for row in batch_38 if row.ticker=="GPN").recovery_outcome=="withheld"
    assert next(row for row in batch_38 if row.ticker=="CPAY").recovery_outcome=="conditional_numeric_low"
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_38 if row.ticker not in {"GPN","CPAY"})
    batch_39=[row for row in entries if row.batch==39]
    assert tuple(row.ticker for row in batch_39)==("ARES","RF","CBOE","IBKR","TRGP","BNY","BX","V","KKR","KMI")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_39)
    batch_40=[row for row in entries if row.batch==40]
    assert tuple(row.ticker for row in batch_40)==("MSCI","XYZ","ICE","SYF","PYPL","COIN","HOOD","TPL","APO","BLK")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_40 if row.ticker!="COIN")
    coin=next(row for row in batch_40 if row.ticker=="COIN")
    assert coin.initial_outcome=="withheld" and coin.recovery_outcome=="withheld" and coin.current_status=="withheld_after_recovery"
    batch_41=[row for row in entries if row.batch==41]
    assert tuple(row.ticker for row in batch_41)==("APD","AVY","BALL","ECL","EQT","HAL","IFF","IP","NUE","PKG")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_41 if row.ticker not in {"APD","IFF","IP"})
    apd=next(row for row in batch_41 if row.ticker=="APD")
    assert apd.initial_outcome=="withheld" and apd.recovery_outcome=="conditional_numeric_low" and apd.current_status=="conditional_numeric_low"
    for ticker in ("IFF","IP"):
        row=next(row for row in batch_41 if row.ticker==ticker)
        assert row.initial_outcome=="withheld" and row.recovery_outcome=="withheld" and row.current_status=="withheld_after_recovery"
    batch_42=[row for row in entries if row.batch==42]
    assert tuple(row.ticker for row in batch_42)==("PPG","SLB","SHW","CVX","OXY","EOG","FCX","CRH","EXE","ALB")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status.startswith("conditional_numeric_low") for row in batch_42 if row.ticker not in {"EXE","ALB"})
    for ticker in ("EXE","ALB"):
        row=next(row for row in batch_42 if row.ticker==ticker)
        assert row.initial_outcome=="withheld" and row.recovery_outcome=="withheld" and row.current_status=="withheld_after_recovery"
    batch_43=[row for row in entries if row.batch==43]
    assert tuple(row.ticker for row in batch_43)==("MLM","STLD","DVN","COP","NEM","MOS","CF","VMC","LYB","LIN")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status.startswith("conditional_numeric_low") for row in batch_43 if row.ticker not in {"DVN","NEM","LYB"})
    for ticker in ("DVN","NEM","LYB"):
        row=next(row for row in batch_43 if row.ticker==ticker)
        assert row.initial_outcome=="withheld" and row.recovery_outcome=="withheld" and row.current_status=="withheld_after_recovery"
    batch_44=[row for row in entries if row.batch==44]
    assert tuple(row.ticker for row in batch_44)==("MPC","PSX","FANG","BKR","AMCR","DOW","CTVA","APA","SW","XOM")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status.startswith("conditional_numeric_low") for row in batch_44 if row.ticker not in {"BKR","AMCR","SW"})
    bkr=next(row for row in batch_44 if row.ticker=="BKR")
    assert bkr.initial_outcome=="withheld" and bkr.recovery_outcome=="withheld" and bkr.current_status=="withheld_after_recovery"
    for ticker in ("AMCR","SW"):
        row=next(row for row in batch_44 if row.ticker==ticker)
        assert row.initial_outcome=="withheld" and row.recovery_outcome=="conditional_numeric_low" and row.current_status.startswith("conditional_numeric_low")
    batch_45=[row for row in entries if row.batch==45]
    assert tuple(row.ticker for row in batch_45)==("AEP","ETR","ES","XEL","SO","LNT","D","PNW","WEC","PEG")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_45)
    batch_46=[row for row in entries if row.batch==46]
    assert tuple(row.ticker for row in batch_46)==("ATO","CMS","EIX","AES","PPL","DTE","AEE","PCG","FE","SRE")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_46 if row.ticker not in {"EIX","AES","PCG","SRE"})
    assert all(row.initial_outcome=="withheld" and row.recovery_outcome=="conditional_numeric_low" and row.current_status=="conditional_numeric_low" for row in batch_46 if row.ticker in {"EIX","AES","PCG","SRE"})
    batch_47=[row for row in entries if row.batch==47]
    assert tuple(row.ticker for row in batch_47)==("NRG","ED","EXC","NI","CNP","DUK","AWK","VST","EVRG","CEG")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_47 if row.ticker not in {"NRG","VST","CEG"})
    assert all(row.initial_outcome=="withheld" and row.recovery_outcome=="withheld" and row.current_status=="withheld_after_recovery" for row in batch_47 if row.ticker in {"NRG","VST","CEG"})
    batch_48=[row for row in entries if row.batch==48]
    assert tuple(row.ticker for row in batch_48)==("FRT","UDR","WY","VTR","DOC","WELL","KIM","EQR","CPT","IRM")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_48 if row.ticker not in {"WY","EQR"})
    wy=next(row for row in batch_48 if row.ticker=="WY")
    assert wy.initial_outcome=="withheld" and wy.recovery_outcome=="conditional_numeric_low" and wy.current_status=="conditional_numeric_low"
    eqr=next(row for row in batch_48 if row.ticker=="EQR")
    assert eqr.initial_outcome=="withheld" and eqr.recovery_outcome=="withheld" and eqr.current_status=="withheld_after_recovery"
    batch_49=[row for row in entries if row.batch==49]
    assert tuple(row.ticker for row in batch_49)==("REG","MAA","AVB","ESS","SBAC","ARE","BXP","PLD","CCI","EQIX")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_49 if row.ticker!="AVB")
    avb=next(row for row in batch_49 if row.ticker=="AVB")
    assert avb.initial_outcome=="withheld" and avb.recovery_outcome=="withheld" and avb.current_status=="withheld_after_recovery"
    batch_50=[row for row in entries if row.batch==50]
    assert tuple(row.ticker for row in batch_50)==("AMT","CSGP","SPG","HST","CBRE","EXR","DLR","PSA","INVH","VICI")
    assert all(row.initial_outcome=="conditional_numeric_low" and row.recovery_outcome=="not_applicable" and row.current_status=="conditional_numeric_low" for row in batch_50)
    assert next(row for row in batch_50 if row.ticker=="CSGP").provisional_model=="operating_enterprise_fcff"
    assert next(row for row in batch_50 if row.ticker=="CBRE").provisional_model=="operating_enterprise_fcff"
    assert all(row.learning_themes for row in entries)
    assert all(row.revisit_triggers for row in entries)
    assert all(row.evidence_reports for row in entries)


def test_current_withheld_register_is_fully_bookmarked_without_changing_semantics() -> None:
    withheld = load_universe_reset_withheld()
    watchlist = load_recovery_learning_watchlist()
    assert {(row.ticker,row.cik) for row in withheld}.issubset({(row.ticker,row.cik) for row in watchlist})
    assert sum(row.current_status.startswith("conditional_numeric_low") for row in watchlist) == 358
    assert sum(row.current_status == "withheld_after_recovery" for row in watchlist) == 26


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
