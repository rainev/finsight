"""Equity-level valuation dispatch for archetypes FCFF cannot value.

Banks and regulated utilities are not enterprise-to-equity FCFF cases: for banks
deposits are operating funding (leverage IS the business), and utilities are
dividend/regulated. This module extracts the model-specific inputs from SEC
facts and runs the EXISTING models (``app.valuation.bank.residual_income_valuation``
for banks, ``app.valuation.ddm.two_stage_ddm`` for utilities), returning the same
result contract as the FCFF path so the pipeline/harvest/artifacts are unchanged.

Price-free (no ``current_price`` passed) and default ``review_required``.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from math import isfinite
from typing import Any

from app.valuation.bank import residual_income_valuation
from app.valuation.ddm import two_stage_ddm

from .reliability import ReliabilityLabel, assess_reliability
from .equity_fact_selection import annual_facts, latest_instant, source_statement

_ISSUER_KEYS = (
    "cik", "ticker", "issuer_name", "filing_regime", "accounting_standard",
    "sec_sic_code", "sec_sic_label", "finsight_sector", "primary_archetype",
    "secondary_archetypes", "classification_confidence", "mapping_version",
    "override_applied", "classification_reason", "source_accessions",
)

_METHODOLOGY = {
    "forecast_policy": "docs/methodology/united-states/forecast-discount-validation-policy.md",
    "sector_framework": "docs/methodology/united-states/equity-valuation-engine-framework.md",
    "source_policy": "SEC Companyfacts and submissions; no exchange prices",
}


class EquityInputsUnavailable(ValueError):
    """Raised when a bank/utility cannot be valued from the filing."""


def _cutoff_eligible_fact(fact: dict[str, Any], cutoff: str | None) -> bool:
    if cutoff is None:
        return True
    filed = fact.get("filed")
    period_end = fact.get("end")
    if filed is None and fact.get("accn") is None:
        # Hand-built unit fixtures predate source-lineage enforcement. Real SEC
        # Companyfacts rows always carry an accession and must carry `filed`.
        return isinstance(period_end, str) and bool(period_end) and period_end <= cutoff
    return (
        isinstance(filed, str)
        and bool(filed)
        and filed <= cutoff
        and isinstance(period_end, str)
        and bool(period_end)
        and period_end <= cutoff
    )


def _cost_of_equity(policy: dict[str, Any]) -> float:
    return policy["risk_free_rate"] + policy["policy_beta"] * policy["equity_risk_premium"]


def _fact_dict(fact):
    return {"concept": fact.concept, "value": fact.value, "unit": fact.unit, "period_start": fact.period_start, "period_end": fact.period_end, "filed_date": fact.filed_date, "accession": fact.accession, "form": fact.form, "fiscal_year": fact.fiscal_year}


def _strict_specialist_facts(gaap, model_name, cutoff):
    if model_name == "residual_income":
        annual = annual_facts(gaap, concepts=("NetIncomeLoss",), unit="USD", valuation_date=cutoff)
        dividends = annual_facts(
            gaap,
            concepts=("PaymentsOfDividendsCommonStock", "PaymentsOfDividends"),
            unit="USD",
            valuation_date=cutoff,
        )
        equity = latest_instant(gaap, concepts=tuple(_EQUITY_CONCEPTS), unit="USD", valuation_date=cutoff)
        shares = latest_instant(gaap, concepts=("CommonStockSharesOutstanding", "CommonStockSharesIssued"), unit="shares", valuation_date=cutoff)
        if not annual or not equity or not shares: raise EquityInputsUnavailable("missing source-linked net income, common equity, or share count")
        year = max(annual)
        result = {"net_income": annual[year], "equity": equity, "shares": shares}
        if year in dividends:
            result["dividends"] = dividends[year]
        return result
    if model_name == "ddm":
        annual = annual_facts(gaap, concepts=("CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid"), unit="USD/shares", valuation_date=cutoff)
        if not annual: raise EquityInputsUnavailable("missing source-linked per-share dividend history")
        return {"dividend": annual[max(annual)]}
    if model_name == "ffo":
        ni = annual_facts(gaap, concepts=tuple(_NI_CONCEPTS), unit="USD", valuation_date=cutoff)
        dep = annual_facts(gaap, concepts=tuple(_REIT_DEP), unit="USD", valuation_date=cutoff)
        gain = annual_facts(gaap, concepts=tuple(_REIT_GAIN), unit="USD", valuation_date=cutoff)
        shares = annual_facts(
            gaap,
            concepts=("WeightedAverageNumberOfDilutedSharesOutstanding",),
            unit="shares",
            valuation_date=cutoff,
        )
        years = sorted(set(ni) & set(dep) & set(gain) & set(shares))
        if not years:
            raise EquityInputsUnavailable(
                "missing reported property-sale gain, aligned diluted shares, "
                "or other source-linked FFO input"
            )
        year = years[-1]
        return {"net_income": ni[year], "depreciation": dep[year], "property_sale_gain": gain[year], "shares": shares[year]}
    return {}


def _annual_10k(gaap: dict, names: list[str], cutoff: str | None) -> dict[int, float]:
    for name in names:
        c = gaap.get(name)
        if not c:
            continue
        chosen: dict[int, dict[str, Any]] = {}
        for u in c.get("units", {}).get("USD", []):
            if u.get("fp") == "FY" and u.get("form") in ("10-K", "10-K/A"):
                if not _cutoff_eligible_fact(u, cutoff):
                    continue
                year = u["fy"]
                prior = chosen.get(year)
                key = (u.get("filed", ""), u.get("form", "").endswith("/A"), u.get("accn", ""))
                prior_key = (
                    prior.get("filed", ""), prior.get("form", "").endswith("/A"), prior.get("accn", "")
                ) if prior is not None else None
                if prior is None or key > prior_key:
                    chosen[year] = u
        if chosen:
            return {year: row["val"] for year, row in chosen.items()}
    return {}


def _latest_instant(gaap: dict, names: list[str], unit: str, cutoff: str | None):
    for name in names:
        c = gaap.get(name)
        if not c:
            continue
        pts = [
            (
                u.get("end"), u.get("filed", ""),
                u.get("form", "").endswith("/A"), u.get("accn", ""),
                u.get("val"),
            )
            for u in c.get("units", {}).get(unit, [])
            if u.get("end") and _cutoff_eligible_fact(u, cutoff)
        ]
        if pts:
            selected = max(pts)
            return selected[0], selected[4]  # (end_date, value)
    return None


_EQUITY_CONCEPTS = [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "CommonStockholdersEquity",
]


def extract_bank_inputs(gaap: dict, cutoff: str | None) -> dict[str, Any]:
    ni = _annual_10k(gaap, ["NetIncomeLoss"], cutoff)
    eq = _latest_instant(gaap, _EQUITY_CONCEPTS, "USD", cutoff)
    sh = _latest_instant(
        gaap, ["CommonStockSharesOutstanding", "CommonStockSharesIssued"], "shares", cutoff
    )
    if not ni or not eq or not sh:
        raise EquityInputsUnavailable("missing net income, common equity, or share count")
    period_end, equity = eq
    net_income = ni[max(ni)]
    if equity <= 0 or net_income <= 0 or sh[1] <= 0:
        raise EquityInputsUnavailable("non-positive equity, net income (loss year), or shares")
    div = _annual_10k(gaap, ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"], cutoff)
    payout = min(max(div[max(div)] / net_income, 0.0), 1.0) if div else None
    return {
        "book_value_per_share": equity / sh[1],
        "current_roe": net_income / equity,
        "current_payout_ratio": payout,
        "period_end": period_end,
    }


def _annual_pershare(gaap: dict, names: list[str], cutoff: str | None) -> dict[int, float]:
    """Full-year per-share facts live under the ``USD/shares`` unit."""
    for name in names:
        c = gaap.get(name)
        if not c:
            continue
        chosen: dict[int, dict[str, Any]] = {}
        for u in c.get("units", {}).get("USD/shares", []):
            if u.get("fp") == "FY" and u.get("form") in ("10-K", "10-K/A"):
                if not _cutoff_eligible_fact(u, cutoff):
                    continue
                year = u["fy"]
                prior = chosen.get(year)
                key = (u.get("filed", ""), u.get("form", "").endswith("/A"), u.get("accn", ""))
                prior_key = (
                    prior.get("filed", ""), prior.get("form", "").endswith("/A"), prior.get("accn", "")
                ) if prior is not None else None
                if prior is None or key > prior_key:
                    chosen[year] = u
        if chosen:
            return {year: row["val"] for year, row in chosen.items()}
    return {}


def extract_utility_inputs(gaap: dict, cutoff: str | None) -> dict[str, Any]:
    dps_series = _annual_pershare(
        gaap,
        ["CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid"],
        cutoff,
    )
    # Fallback: total common dividends / shares.
    if not dps_series:
        div = _annual_10k(gaap, ["PaymentsOfDividendsCommonStock"], cutoff)
        sh = _latest_instant(gaap, ["CommonStockSharesOutstanding"], "shares", cutoff)
        if div and sh:
            last = div[max(div)] / sh[1]
            dps_series = {max(div): last}
    if not dps_series:
        raise EquityInputsUnavailable("missing per-share dividend history")
    last_dividend = dps_series[max(dps_series)]
    if last_dividend <= 0:
        raise EquityInputsUnavailable("non-positive latest dividend (not a DDM candidate)")
    # DDM needs only the dividend; take a best-effort period_end from any
    # balance-sheet or share instant (equity is NOT required for a DDM).
    anchor = _latest_instant(gaap, _EQUITY_CONCEPTS, "USD", cutoff) or _latest_instant(
        gaap, ["CommonStockSharesOutstanding"], "shares", cutoff
    )
    return {"last_dividend": last_dividend, "period_end": anchor[0] if anchor else None}



_NI_CONCEPTS = ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic", "ProfitLoss"]
_REIT_DEP = ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
             "DepreciationAmortizationAndAccretionNet", "RealEstateInvestmentPropertyDepreciation"]
_REIT_GAIN = ["GainLossOnSaleOfProperties", "GainLossOnDispositionOfRealEstate",
              "GainsLossesOnSalesOfInvestmentRealEstate"]


def extract_reit_inputs(gaap: dict, cutoff: str | None) -> dict[str, Any]:
    """FFO per share = (net income + real-estate depreciation - property-sale gains) / shares."""
    ni = _annual_10k(gaap, _NI_CONCEPTS, cutoff)
    dep = _annual_10k(gaap, _REIT_DEP, cutoff)
    sh = _latest_instant(gaap, ["CommonStockSharesOutstanding", "CommonStockSharesIssued"], "shares", cutoff)
    if not ni or not dep or not sh:
        raise EquityInputsUnavailable("missing net income, depreciation, or shares for FFO")
    if sh[1] < 1_000_000:
        # A large-cap issuer with < 1M shares is an extraction error (wrong tag /
        # par value), which would explode per-share metrics. Refuse it.
        raise EquityInputsUnavailable("implausible share count for FFO")
    common = sorted(set(ni) & set(dep))
    if not common:
        raise EquityInputsUnavailable("no common NI/depreciation fiscal year")
    year = common[-1]
    gains = _annual_10k(gaap, _REIT_GAIN, cutoff)
    if year not in gains:
        raise EquityInputsUnavailable("missing reported property-sale gain for FFO; zero is not assumed")
    ffo = ni[year] + dep[year] - gains[year]
    ffo_per_share = ffo / sh[1]
    if ffo_per_share <= 0:
        raise EquityInputsUnavailable("non-positive FFO per share")
    return {"ffo_per_share": ffo_per_share, "period_end": sh[0]}


def _shell(classification, valuation_date, source_manifest, period_end, *, source=None):
    return {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "valuation_date": valuation_date or date.today().isoformat(),
        "market": "US",
        "currency": "USD",
        "issuer": {k: classification[k] for k in _ISSUER_KEYS},
        "financial_period_end": period_end,
        "source_financial_statement": source or {
            "form": "10-K / 10-Q",
            "period_end": period_end,
            "filed_date": None,
            "accession": (classification.get("source_accessions") or [None])[0],
            "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK="
                   + classification.get("cik", ""),
            "note": "Equity-level model (residual income / DDM); no enterprise-to-equity bridge.",
        },
        "source_manifest": source_manifest or {"status": "not_supplied"},
        "model_policy": {
            "primary": classification["valuation_policy"]["primary_model"],
            "supporting": classification["valuation_policy"]["supporting_models"],
            "blend_models": False,
            "reason": classification["valuation_policy"].get("model_policy_reason", ""),
        },
        "methodology": _METHODOLOGY,
    }


def _withheld(classification, valuation_date, source_manifest, model_name, message):
    result = _shell(classification, valuation_date, source_manifest, None)
    model = {
        "model": model_name, "output_type": "intrinsic_value_per_share", "currency": "USD",
        "intrinsic_value_per_share": None, "publication_state": "withheld",
        "errors": [message], "warnings": [],
    }
    result.update({
        "models": {model_name: model},
        "scenarios": {},
        "scenario_range": {"low": None, "base": None, "high": None,
                           "label": "assumption range, not a statistical confidence interval"},
        "review": {"publication_state": "withheld", "confidence_grade": "insufficient",
                   "errors": [message], "warnings": [],
                   "prohibited_output_check": {"current_price": False, "upside_downside": False,
                                               "buy_hold_sell": False, "trading_multiples": False}},
    })
    return result


def _finalize(classification, valuation_date, source_manifest, period_end, model_name,
              scenarios: dict[str, float], public_assumptions: dict, warnings: list[str],
              *, model_cap: ReliabilityLabel = "High", reasons: tuple[str, ...] = (), source=None, input_provenance=None):
    base = scenarios["base"]
    if base is None:
        return _withheld(classification, valuation_date, source_manifest, model_name,
                         "Model did not produce a base value.")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        for value in scenarios.values()
    ):
        return _withheld(
            classification,
            valuation_date,
            source_manifest,
            model_name,
            f"Non-finite {model_name} scenario value; withheld.",
        )
    if base <= 0:
        return _withheld(
            classification,
            valuation_date,
            source_manifest,
            model_name,
            f"Non-positive {model_name} intrinsic value; equity model does not apply.",
        )
    if base > 50000:
        return _withheld(
            classification,
            valuation_date,
            source_manifest,
            model_name,
            f"Implausible {model_name} intrinsic value (~${base:,.0f}/share); withheld.",
        )
    state = "review_required"
    scenario_range = {
        "low": min(scenarios.values()),
        "base": base,
        "high": max(scenarios.values()),
        "label": "assumption range, not a statistical confidence interval",
    }
    reliability = assess_reliability(
        accounting_low=base,
        accounting_base=base,
        accounting_high=base,
        scenario_low=scenario_range["low"],
        scenario_base=scenario_range["base"],
        scenario_high=scenario_range["high"],
        model_cap=model_cap,
        reasons=reasons,
    )
    model = {
        "model": model_name, "output_type": "intrinsic_value_per_share", "currency": "USD",
        "intrinsic_value_per_share": base, "publication_state": state,
        "errors": [], "warnings": warnings,
    }
    result = _shell(classification, valuation_date, source_manifest, period_end, source=source)
    result.update({
        "public_assumptions": public_assumptions,
        "models": {model_name: model},
        "scenarios": {k: {model_name: {"intrinsic_value_per_share": v, "publication_state": state}}
                      for k, v in scenarios.items()},
        "scenario_range": scenario_range,
        "reliability": reliability.as_dict(),
        "review": {"publication_state": state, "confidence_grade": "medium",
                   "errors": [], "warnings": warnings,
                   "prohibited_output_check": {"current_price": False, "upside_downside": False,
                                               "buy_hold_sell": False, "trading_multiples": False}},
    })
    if input_provenance is not None:
        result["input_provenance"] = input_provenance
    return result


def build_equity_level_result(*, classification, companyfacts, valuation_date, source_manifest, submissions=None):
    """Dispatch a bank (residual income) or utility (DDM) valuation, price-free."""
    policy = classification["valuation_policy"]
    model_name = policy["primary_model"]
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    ce = _cost_of_equity(policy)
    strict = _strict_specialist_facts(gaap, model_name, valuation_date) if submissions is not None else {}
    provenance = {name: _fact_dict(fact) for name, fact in strict.items()}
    controlling_fact = max(
        strict.values(),
        key=lambda fact: (fact.period_end, fact.filed_date, fact.accession),
        default=None,
    )
    source = (
        source_statement(
            controlling_fact,
            submissions=submissions,
            cik=classification["cik"],
        )
        if controlling_fact is not None
        else None
    )

    if model_name == "residual_income":
        try:
            inp = extract_bank_inputs(gaap, valuation_date)
            if strict:
                inp.update({
                    "book_value_per_share": strict["equity"].value / strict["shares"].value,
                    "current_roe": strict["net_income"].value / strict["equity"].value,
                    "current_payout_ratio": (
                        strict["dividends"].value / strict["net_income"].value
                        if "dividends" in strict
                        else None
                    ),
                    "period_end": strict["equity"].period_end,
                })
        except EquityInputsUnavailable as exc:
            return _withheld(classification, valuation_date, source_manifest, model_name, str(exc))
        payout = inp["current_payout_ratio"]
        payout = policy["default_payout_ratio"] if payout is None else payout
        roe = inp["current_roe"]

        def val(mult, terminal_roe):
            return residual_income_valuation(
                book_value_per_share=inp["book_value_per_share"], current_roe=roe * mult,
                cost_of_equity=ce, current_payout_ratio=payout, terminal_roe=terminal_roe,
                terminal_growth=policy["terminal_growth"], years=policy["forecast_years"],
                current_price=None,
            )["intrinsic_value"]
        try:
            scenarios = {
                "bear": val(0.85, max(policy["terminal_roe"] - 0.02, ce + 0.01)),
                "base": val(1.00, policy["terminal_roe"]),
                "bull": val(1.15, policy["terminal_roe"] + 0.02),
            }
        except ValueError as exc:
            return _withheld(classification, valuation_date, source_manifest, model_name, str(exc))
        pa = {"cost_of_equity": ce, "risk_free_rate": policy["risk_free_rate"],
              "equity_risk_premium": policy["equity_risk_premium"], "policy_beta": policy["policy_beta"],
              "book_value_per_share": inp["book_value_per_share"], "current_roe": roe,
              "current_payout_ratio": payout, "terminal_roe": policy["terminal_roe"],
              "terminal_growth": policy["terminal_growth"]}
        warnings = ["Single-period book/ROE snapshot; average-equity and preferred-stock refinements pending."]
        return _finalize(classification, valuation_date, source_manifest, inp["period_end"],
                         model_name, scenarios, pa, warnings, source=source, input_provenance=provenance)

    if model_name == "ddm":
        try:
            inp = extract_utility_inputs(gaap, valuation_date)
            if strict: inp.update({"last_dividend": strict["dividend"].value, "period_end": strict["dividend"].period_end})
        except EquityInputsUnavailable as exc:
            return _withheld(classification, valuation_date, source_manifest, model_name, str(exc))

        def val(high_growth):
            return two_stage_ddm(
                last_dividend=inp["last_dividend"], high_growth=high_growth,
                high_growth_years=policy["high_growth_years"], terminal_growth=policy["terminal_growth"],
                discount_rate=ce, current_price=None,
            )["intrinsic_value"]
        try:
            scenarios = {"bear": val(policy["high_dividend_growth"] - 0.02),
                         "base": val(policy["high_dividend_growth"]),
                         "bull": val(policy["high_dividend_growth"] + 0.02)}
        except ValueError as exc:
            return _withheld(classification, valuation_date, source_manifest, model_name, str(exc))
        pa = {"cost_of_equity": ce, "risk_free_rate": policy["risk_free_rate"],
              "equity_risk_premium": policy["equity_risk_premium"], "policy_beta": policy["policy_beta"],
              "last_dividend": inp["last_dividend"], "high_dividend_growth": policy["high_dividend_growth"],
              "terminal_growth": policy["terminal_growth"], "high_growth_years": policy["high_growth_years"]}
        warnings = ["Dividend growth is a governed policy assumption, not a per-issuer forecast."]
        return _finalize(classification, valuation_date, source_manifest, inp["period_end"],
                         model_name, scenarios, pa, warnings, source=source, input_provenance=provenance)

    if model_name == "ffo":
        try:
            inp = extract_reit_inputs(gaap, valuation_date)
            if strict:
                inp.update({"ffo_per_share": (strict["net_income"].value + strict["depreciation"].value - strict["property_sale_gain"].value) / strict["shares"].value, "period_end": strict["shares"].period_end})
        except EquityInputsUnavailable as exc:
            return _withheld(classification, valuation_date, source_manifest, model_name, str(exc))
        ffo = inp["ffo_per_share"]
        scenarios = {"bear": ffo * policy["pffo_bear"], "base": ffo * policy["pffo_base"],
                     "bull": ffo * policy["pffo_bull"]}
        pa = {"ffo_per_share": ffo, "pffo_multiple": policy["pffo_base"],
              "risk_free_rate": policy["risk_free_rate"], "equity_risk_premium": policy["equity_risk_premium"]}
        warnings = ["FFO is a filing-derived approximation (non-GAAP); valued at a governed P/FFO multiple."]
        return _finalize(classification, valuation_date, source_manifest, inp["period_end"],
                         model_name, scenarios, pa, warnings,
                         model_cap="Low", reasons=("INTERIM_FFO_ROUTE",), source=source, input_provenance=provenance)

    raise ValueError(f"build_equity_level_result cannot handle primary_model={model_name!r}")


# Fields carried for internal/harvest use but stripped from the SERVED public
# artifact (the FCFF path strips the same via public_result). Equity results hold
# no raw financials, so stripping these two makes them public-safe.
_PUBLIC_STRIP = ("financial_period_end", "source_manifest", "input_provenance")


def public_equity_artifact(result: dict) -> dict:
    art = deepcopy(result)
    for key in _PUBLIC_STRIP:
        art.pop(key, None)
    issuer = art.get("issuer")
    if isinstance(issuer, dict) and isinstance(issuer.get("ticker"), str):
        art["ticker"] = issuer["ticker"]
    return art
