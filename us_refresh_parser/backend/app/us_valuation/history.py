"""Source-linked company-history assumptions for U.S. valuation lanes.

This module turns already-normalized, cutoff-safe filing facts into a compact
low/base/high history profile.  It does not fetch data, choose a different
economic model, or publish raw financial observations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from math import isfinite
from numbers import Real
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

from .equity_fact_selection import SelectedFact, annual_facts


HISTORY_POLICY_VERSION = "US-COMPANY-HISTORY-1.0"
MIN_ANNUAL_OBSERVATIONS = 3
MAX_ANNUAL_OBSERVATIONS = 5
MATERIAL_IMPACT_THRESHOLD = 0.05


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(float(value)):
        raise ValueError(f"{field} must be finite")
    return float(value)


def _iso(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires observations")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


@dataclass(frozen=True)
class HistoryObservation:
    period_role: str
    period_end: str
    fiscal_year: int | None
    value: float
    unit: str
    formula: str
    sources: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        if self.period_role not in {"annual", "operating_ttm"}:
            raise ValueError("history observation period_role is invalid")
        object.__setattr__(self, "period_end", _iso(self.period_end, "period_end"))
        object.__setattr__(self, "value", _finite(self.value, "history value"))
        if not self.unit.strip() or not self.formula.strip() or not self.sources:
            raise ValueError("history observations require unit, formula, and sources")


@dataclass(frozen=True)
class HistoryMetric:
    name: str
    low: float
    base: float
    high: float
    normalization_basis: str
    observations: tuple[HistoryObservation, ...]

    def __post_init__(self) -> None:
        low = _finite(self.low, "history low")
        base = _finite(self.base, "history base")
        high = _finite(self.high, "history high")
        if not low <= base <= high:
            raise ValueError("history metric range must satisfy low <= base <= high")
        if not self.name.strip() or not self.normalization_basis.strip() or not self.observations:
            raise ValueError("history metrics require a name, basis, and observations")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "high", high)


@dataclass(frozen=True)
class CompanyHistoryProfile:
    policy_version: str
    lane: str
    valuation_date: str
    annual_periods: tuple[str, ...]
    metrics: tuple[HistoryMetric, ...]
    full_history: bool
    assumption_source_mix: str

    def __post_init__(self) -> None:
        if self.policy_version != HISTORY_POLICY_VERSION:
            raise ValueError("history policy version is invalid")
        if not self.lane.strip():
            raise ValueError("history lane is required")
        object.__setattr__(self, "valuation_date", _iso(self.valuation_date, "valuation_date"))
        if len(self.annual_periods) > MAX_ANNUAL_OBSERVATIONS:
            raise ValueError("history profile exceeds the five-period maximum")
        if any(_iso(value, "annual period") > self.valuation_date for value in self.annual_periods):
            raise ValueError("history profile contains a period after the valuation date")
        for metric in self.metrics:
            for observation in metric.observations:
                if observation.period_end > self.valuation_date:
                    raise ValueError("history observation is after the valuation date")
                for source in observation.sources:
                    filed = source.get("filed") or source.get("filed_date")
                    period_end = source.get("end") or source.get("period_end")
                    if isinstance(filed, str) and filed > self.valuation_date:
                        raise ValueError("history source was filed after the valuation date")
                    if isinstance(period_end, str) and period_end > self.valuation_date:
                        raise ValueError("history source period is after the valuation date")
        expected_full = len(set(self.annual_periods)) >= MIN_ANNUAL_OBSERVATIONS
        if self.full_history != expected_full:
            raise ValueError("history profile full-history flag is inconsistent")
        expected_mix = (
            "reported_and_company_history"
            if self.full_history
            else "reported_history_and_finsight_policy"
        )
        if self.assumption_source_mix != expected_mix:
            raise ValueError("history profile source mix is inconsistent")

    @property
    def history_years_used(self) -> int:
        return len(set(self.annual_periods))

    @property
    def normalization_basis(self) -> str:
        return (
            "company_history_median_and_percentiles"
            if self.full_history
            else "insufficient_company_history_policy_fallback"
        )

    def metric(self, name: str) -> HistoryMetric | None:
        return next((metric for metric in self.metrics if metric.name == name), None)

    def public_metadata(self) -> dict[str, Any]:
        return {
            "history_policy_version": self.policy_version,
            "history_years_used": self.history_years_used,
            "normalization_basis": self.normalization_basis,
            "assumption_source_mix": self.assumption_source_mix,
        }

    def as_private_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_history_metric(
    name: str,
    observations: Iterable[HistoryObservation],
) -> HistoryMetric | None:
    rows = tuple(observations)
    if not rows:
        return None
    values = [row.value for row in rows]
    if len(values) >= 4:
        low = _percentile(values, 0.25)
        high = _percentile(values, 0.75)
        basis = "median with historical 25th/75th percentiles"
    else:
        low, high = min(values), max(values)
        basis = "median with observed minimum/maximum"
    return HistoryMetric(
        name=name,
        low=low,
        base=float(median(values)),
        high=high,
        normalization_basis=basis,
        observations=rows,
    )


def _source_tuple(*values: object) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, Mapping):
            nested = value.get("sources")
            if isinstance(nested, list):
                rows.extend(dict(item) for item in nested if isinstance(item, Mapping))
            else:
                rows.append(dict(value))
        elif isinstance(value, list):
            rows.extend(dict(item) for item in value if isinstance(item, Mapping))
    if not rows:
        raise ValueError("history observation has no source rows")
    return tuple(rows)


def _optional_source_tuple(*values: object) -> tuple[dict[str, Any], ...] | None:
    try:
        return _source_tuple(*values)
    except ValueError:
        return None


def _source_verified_annual(row: Mapping[str, Any], cutoff: str) -> bool:
    sources = row.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        return False
    for source in sources.values():
        if not isinstance(source, Mapping):
            continue
        if (
            isinstance(source.get("accession"), str)
            and isinstance(source.get("filed"), str)
            and source["filed"] <= cutoff
        ):
            return True
    return False


def build_operating_history_profile(
    financials: Mapping[str, Any],
    *,
    valuation_date: str,
) -> CompanyHistoryProfile:
    """Build the operating-FCFF history profile from normalized filing facts."""

    cutoff = _iso(valuation_date, "valuation_date")
    annual_candidates = [
        row
        for row in financials.get("annual", [])
        if isinstance(row, Mapping)
        and isinstance(row.get("period_end"), str)
        and row["period_end"] <= cutoff
        and _source_verified_annual(row, cutoff)
    ]
    annual_by_period = {str(row["period_end"]): row for row in annual_candidates}
    annual = [annual_by_period[key] for key in sorted(annual_by_period)][-MAX_ANNUAL_OBSERVATIONS:]
    annual_periods = tuple(str(row["period_end"]) for row in annual)
    metrics: list[HistoryMetric] = []

    growth_rows: list[HistoryObservation] = []
    for prior, current in zip(annual, annual[1:]):
        prior_revenue = _finite(prior.get("values", {}).get("revenue"), "prior revenue")
        current_revenue = _finite(current.get("values", {}).get("revenue"), "current revenue")
        if prior_revenue <= 0 or current_revenue <= 0:
            continue
        growth_rows.append(
            HistoryObservation(
                period_role="annual",
                period_end=str(current["period_end"]),
                fiscal_year=current.get("fiscal_year"),
                value=current_revenue / prior_revenue - 1,
                unit="ratio",
                formula="current annual revenue / prior annual revenue - 1",
                sources=_source_tuple(
                    prior.get("sources", {}).get("revenue"),
                    current.get("sources", {}).get("revenue"),
                ),
            )
        )

    ttm = financials.get("ttm", {})
    ttm_end = ttm.get("period_end")
    ttm_revenue = ttm.get("values", {}).get("revenue")
    ttm_history = financials.get("normalized", {}).get("revenue_ttm_history", [])
    if isinstance(ttm_end, str) and isinstance(ttm_revenue, Real) and not isinstance(ttm_revenue, bool):
        comparable = [
            row
            for row in ttm_history
            if isinstance(row, Mapping)
            and isinstance(row.get("period_end"), str)
            and 350 <= abs((date.fromisoformat(ttm_end) - date.fromisoformat(row["period_end"])).days) <= 380
            and isinstance(row.get("value"), Real)
            and not isinstance(row.get("value"), bool)
            and float(row["value"]) > 0
        ]
        if comparable:
            prior_ttm = comparable[-1]
            sources = _optional_source_tuple(
                prior_ttm.get("sources"), ttm.get("sources", {}).get("revenue")
            )
            if sources:
                growth_rows.append(
                HistoryObservation(
                    period_role="operating_ttm",
                    period_end=ttm_end,
                    fiscal_year=None,
                    value=float(ttm_revenue) / float(prior_ttm["value"]) - 1,
                    unit="ratio",
                    formula="current TTM revenue / prior comparable TTM revenue - 1",
                    sources=sources,
                )
                )
    growth_metric = summarize_history_metric("revenue_growth", growth_rows)
    if growth_metric:
        metrics.append(growth_metric)

    ratio_fields = {
        "operating_margin": ("operating_income", "revenue"),
        "capex_to_revenue": ("capital_expenditures", "revenue"),
        "depreciation_to_revenue": ("depreciation_amortization", "revenue"),
        "effective_tax_rate": ("income_tax", "pretax_income"),
    }
    for metric_name, (numerator_name, denominator_name) in ratio_fields.items():
        rows: list[HistoryObservation] = []
        for annual_row in annual:
            values = annual_row.get("values", {})
            numerator = values.get(numerator_name)
            denominator = values.get(denominator_name)
            if not isinstance(numerator, Real) or isinstance(numerator, bool):
                continue
            if not isinstance(denominator, Real) or isinstance(denominator, bool) or float(denominator) <= 0:
                continue
            value = float(numerator) / float(denominator)
            if metric_name in {"capex_to_revenue", "depreciation_to_revenue"}:
                value = abs(value)
            if metric_name == "effective_tax_rate" and not 0 <= value <= 1:
                continue
            rows.append(
                HistoryObservation(
                    period_role="annual",
                    period_end=str(annual_row["period_end"]),
                    fiscal_year=annual_row.get("fiscal_year"),
                    value=value,
                    unit="ratio",
                    formula=f"{numerator_name} / {denominator_name}",
                    sources=_source_tuple(
                        annual_row.get("sources", {}).get(numerator_name),
                        annual_row.get("sources", {}).get(denominator_name),
                    ),
                )
            )
        ttm_values = ttm.get("values", {})
        numerator = ttm_values.get(numerator_name)
        denominator = ttm_values.get(denominator_name)
        if (
            isinstance(ttm_end, str)
            and ttm_end not in annual_periods
            and isinstance(numerator, Real)
            and not isinstance(numerator, bool)
            and isinstance(denominator, Real)
            and not isinstance(denominator, bool)
            and float(denominator) > 0
        ):
            value = float(numerator) / float(denominator)
            if metric_name in {"capex_to_revenue", "depreciation_to_revenue"}:
                value = abs(value)
            sources = _optional_source_tuple(
                ttm.get("sources", {}).get(numerator_name),
                ttm.get("sources", {}).get(denominator_name),
            )
            if sources and (metric_name != "effective_tax_rate" or 0 <= value <= 1):
                rows.append(
                    HistoryObservation(
                        period_role="operating_ttm",
                        period_end=ttm_end,
                        fiscal_year=None,
                        value=value,
                        unit="ratio",
                        formula=f"TTM {numerator_name} / TTM {denominator_name}",
                        sources=sources,
                    )
                )
        metric = summarize_history_metric(metric_name, rows)
        if metric:
            metrics.append(metric)

    full_history = len(set(annual_periods)) >= MIN_ANNUAL_OBSERVATIONS
    return CompanyHistoryProfile(
        policy_version=HISTORY_POLICY_VERSION,
        lane="operating_fcff",
        valuation_date=cutoff,
        annual_periods=annual_periods,
        metrics=tuple(metrics),
        full_history=full_history,
        assumption_source_mix=(
            "reported_and_company_history"
            if full_history
            else "reported_history_and_finsight_policy"
        ),
    )


def _fact_source(fact: SelectedFact) -> dict[str, Any]:
    return {
        "concept": fact.concept,
        "value": fact.value,
        "unit": fact.unit,
        "period_start": fact.period_start,
        "period_end": fact.period_end,
        "filed_date": fact.filed_date,
        "accession": fact.accession,
        "form": fact.form,
        "fiscal_year": fact.fiscal_year,
    }


def _annual_instant_facts(
    gaap: Mapping[str, Any],
    *,
    concepts: tuple[str, ...],
    unit: str,
    valuation_date: str,
) -> dict[int, SelectedFact]:
    cutoff = _iso(valuation_date, "valuation_date")
    choices: dict[int, SelectedFact] = {}
    for concept in concepts:
        payload = gaap.get(concept)
        if not isinstance(payload, Mapping):
            continue
        units = payload.get("units", {})
        rows = units.get(unit, []) if isinstance(units, Mapping) else []
        for raw in rows:
            if not isinstance(raw, Mapping):
                continue
            fiscal_year = raw.get("fy")
            value = raw.get("val")
            end = raw.get("end")
            filed = raw.get("filed")
            accession = raw.get("accn")
            form = raw.get("form")
            if (
                isinstance(fiscal_year, bool)
                or not isinstance(fiscal_year, int)
                or isinstance(value, bool)
                or not isinstance(value, Real)
                or not isfinite(float(value))
                or not isinstance(end, str)
                or not isinstance(filed, str)
                or not isinstance(accession, str)
                or form not in {"10-K", "10-K/A"}
                or end > cutoff
                or filed > cutoff
            ):
                continue
            fact = SelectedFact(
                concept=concept,
                value=float(value),
                unit=unit,
                period_start=None,
                period_end=end,
                filed_date=filed,
                accession=accession,
                form=form,
                fiscal_year=fiscal_year,
            )
            prior = choices.get(fiscal_year)
            if prior is None or (
                fact.period_end,
                fact.filed_date,
                fact.accession,
            ) > (
                prior.period_end,
                prior.filed_date,
                prior.accession,
            ):
                choices[fiscal_year] = fact
        if choices:
            break
    return choices


def build_equity_history_profile(
    companyfacts: Mapping[str, Any],
    *,
    model_name: str,
    valuation_date: str,
) -> CompanyHistoryProfile:
    """Build history for residual-income, dividend, or FFO equity lanes."""

    if model_name not in {"residual_income", "ddm", "ffo"}:
        raise ValueError("unsupported equity history lane")
    cutoff = _iso(valuation_date, "valuation_date")
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    if not isinstance(gaap, Mapping):
        gaap = {}
    metrics: list[HistoryMetric] = []
    period_ends: set[str] = set()

    if model_name == "residual_income":
        income = annual_facts(
            gaap,
            concepts=("NetIncomeLoss",),
            unit="USD",
            valuation_date=cutoff,
        )
        dividends = annual_facts(
            gaap,
            concepts=("PaymentsOfDividendsCommonStock", "PaymentsOfDividends"),
            unit="USD",
            valuation_date=cutoff,
        )
        equity = _annual_instant_facts(
            gaap,
            concepts=(
                "CommonStockholdersEquity",
                "StockholdersEquity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ),
            unit="USD",
            valuation_date=cutoff,
        )
        roe_rows: list[HistoryObservation] = []
        payout_rows: list[HistoryObservation] = []
        for fiscal_year in sorted(set(income) & set(equity))[-MAX_ANNUAL_OBSERVATIONS:]:
            earnings = income[fiscal_year]
            closing_equity = equity[fiscal_year]
            prior_equity = equity.get(fiscal_year - 1)
            denominator = (
                (prior_equity.value + closing_equity.value) / 2
                if prior_equity is not None
                else closing_equity.value
            )
            if earnings.value <= 0 or denominator <= 0:
                continue
            sources = [_fact_source(earnings), _fact_source(closing_equity)]
            if prior_equity is not None:
                sources.append(_fact_source(prior_equity))
            roe_rows.append(
                HistoryObservation(
                    period_role="annual",
                    period_end=earnings.period_end,
                    fiscal_year=fiscal_year,
                    value=earnings.value / denominator,
                    unit="ratio",
                    formula="annual net income / average common equity",
                    sources=tuple(sources),
                )
            )
            period_ends.add(earnings.period_end)
            dividend = dividends.get(fiscal_year)
            if dividend is not None and dividend.value >= 0:
                payout_rows.append(
                    HistoryObservation(
                        period_role="annual",
                        period_end=earnings.period_end,
                        fiscal_year=fiscal_year,
                        value=min(1.0, dividend.value / earnings.value),
                        unit="ratio",
                        formula="common dividends / annual net income",
                        sources=(_fact_source(dividend), _fact_source(earnings)),
                    )
                )
        for name, rows in (("common_roe", roe_rows), ("payout_ratio", payout_rows)):
            metric = summarize_history_metric(name, rows)
            if metric:
                metrics.append(metric)

    elif model_name == "ddm":
        dividends = annual_facts(
            gaap,
            concepts=("CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid"),
            unit="USD/shares",
            valuation_date=cutoff,
        )
        ordered = [dividends[year] for year in sorted(dividends)][-MAX_ANNUAL_OBSERVATIONS:]
        growth_rows: list[HistoryObservation] = []
        for prior, current in zip(ordered, ordered[1:]):
            if prior.value <= 0 or current.value <= 0:
                continue
            growth_rows.append(
                HistoryObservation(
                    period_role="annual",
                    period_end=current.period_end,
                    fiscal_year=current.fiscal_year,
                    value=current.value / prior.value - 1,
                    unit="ratio",
                    formula="current annual dividend per share / prior annual dividend per share - 1",
                    sources=(_fact_source(prior), _fact_source(current)),
                )
            )
            period_ends.add(current.period_end)
        metric = summarize_history_metric("dividend_growth", growth_rows)
        if metric:
            metrics.append(metric)
        period_ends.update(fact.period_end for fact in ordered)

    else:
        income = annual_facts(gaap, concepts=("NetIncomeLoss",), unit="USD", valuation_date=cutoff)
        depreciation = annual_facts(
            gaap,
            concepts=(
                "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
                "DepreciationDepletionAndAmortization",
            ),
            unit="USD",
            valuation_date=cutoff,
        )
        gains = annual_facts(
            gaap,
            concepts=("GainLossOnSaleOfRealEstate", "GainLossOnSaleOfProperty"),
            unit="USD",
            valuation_date=cutoff,
        )
        shares = annual_facts(
            gaap,
            concepts=("WeightedAverageNumberOfDilutedSharesOutstanding",),
            unit="shares",
            valuation_date=cutoff,
        )
        ffo_rows: list[HistoryObservation] = []
        years = sorted(set(income) & set(depreciation) & set(gains) & set(shares))
        for fiscal_year in years[-MAX_ANNUAL_OBSERVATIONS:]:
            if shares[fiscal_year].value <= 0:
                continue
            value = (
                income[fiscal_year].value
                + depreciation[fiscal_year].value
                - gains[fiscal_year].value
            ) / shares[fiscal_year].value
            if value <= 0:
                continue
            fact_rows = (
                income[fiscal_year],
                depreciation[fiscal_year],
                gains[fiscal_year],
                shares[fiscal_year],
            )
            ffo_rows.append(
                HistoryObservation(
                    period_role="annual",
                    period_end=income[fiscal_year].period_end,
                    fiscal_year=fiscal_year,
                    value=value,
                    unit="USD_per_share",
                    formula="(net income + real-estate depreciation - property-sale gains) / diluted shares",
                    sources=tuple(_fact_source(fact) for fact in fact_rows),
                )
            )
            period_ends.add(income[fiscal_year].period_end)
        metric = summarize_history_metric("ffo_per_share", ffo_rows)
        if metric:
            metrics.append(metric)
        growth_rows = [
            HistoryObservation(
                period_role="annual",
                period_end=current.period_end,
                fiscal_year=current.fiscal_year,
                value=current.value / prior.value - 1,
                unit="ratio",
                formula="current annual FFO per share / prior annual FFO per share - 1",
                sources=tuple((*prior.sources, *current.sources)),
            )
            for prior, current in zip(ffo_rows, ffo_rows[1:])
            if prior.value > 0 and current.value > 0
        ]
        growth_metric = summarize_history_metric("ffo_growth", growth_rows)
        if growth_metric:
            metrics.append(growth_metric)

    annual_periods = tuple(sorted(period_ends)[-MAX_ANNUAL_OBSERVATIONS:])
    full_history = len(annual_periods) >= MIN_ANNUAL_OBSERVATIONS
    return CompanyHistoryProfile(
        policy_version=HISTORY_POLICY_VERSION,
        lane={
            "residual_income": "bank_residual_income",
            "ddm": "utility_or_equity",
            "ffo": "reit_ffo",
        }[model_name],
        valuation_date=cutoff,
        annual_periods=annual_periods,
        metrics=tuple(metrics),
        full_history=full_history,
        assumption_source_mix=(
            "reported_and_company_history"
            if full_history
            else "reported_history_and_finsight_policy"
        ),
    )


def build_cash_fcff_history_profile(
    *,
    annual_cash_states: Sequence[Mapping[str, Any]],
    ttm_revenue: float,
    ttm_cash_fcff: float,
    ttm_period_end: str,
    ttm_sources: Sequence[Mapping[str, Any]],
    valuation_date: str,
) -> CompanyHistoryProfile:
    """Build the shared cash-FCFF history used by launch-first operating lanes."""

    cutoff = _iso(valuation_date, "valuation_date")
    annual_candidates = [
        row
        for row in annual_cash_states
        if isinstance(row.get("period_end"), str)
        and row["period_end"] <= cutoff
        and isinstance(row.get("cash_fcff"), Real)
        and isinstance(row.get("revenue"), Mapping)
        and isinstance(row["revenue"].get("value"), Real)
        and float(row["revenue"]["value"]) > 0
    ]
    annual_by_period = {str(row["period_end"]): row for row in annual_candidates}
    annual = [annual_by_period[key] for key in sorted(annual_by_period)][-MAX_ANNUAL_OBSERVATIONS:]
    annual_periods = tuple(str(row["period_end"]) for row in annual)
    cash_rows = [
        HistoryObservation(
            period_role="annual",
            period_end=str(row["period_end"]),
            fiscal_year=row.get("revenue", {}).get("fiscal_year"),
            value=float(row["cash_fcff"]) / float(row["revenue"]["value"]),
            unit="ratio",
            formula="annual cash FCFF / annual revenue",
            sources=_source_tuple(
                row.get("operating_cash_flow"),
                row.get("capital_expenditures"),
                row.get("interest_expense"),
                row.get("income_tax"),
                row.get("pretax_income"),
                row.get("revenue"),
            ),
        )
        for row in annual
    ]
    if ttm_revenue <= 0:
        raise ValueError("TTM revenue must be positive")
    if ttm_period_end not in annual_periods:
        cash_rows.append(
            HistoryObservation(
                period_role="operating_ttm",
                period_end=ttm_period_end,
                fiscal_year=None,
                value=_finite(ttm_cash_fcff, "TTM cash FCFF") / _finite(ttm_revenue, "TTM revenue"),
                unit="ratio",
                formula="TTM cash FCFF / TTM revenue",
                sources=tuple(dict(row) for row in ttm_sources),
            )
        )
    metrics: list[HistoryMetric] = []
    cash_metric = summarize_history_metric("cash_conversion_margin", cash_rows)
    if cash_metric:
        metrics.append(cash_metric)

    growth_rows: list[HistoryObservation] = []
    for prior, current in zip(annual, annual[1:]):
        prior_revenue = float(prior["revenue"]["value"])
        current_revenue = float(current["revenue"]["value"])
        if prior_revenue <= 0 or current_revenue <= 0:
            continue
        growth_rows.append(
            HistoryObservation(
                period_role="annual",
                period_end=str(current["period_end"]),
                fiscal_year=current.get("revenue", {}).get("fiscal_year"),
                value=current_revenue / prior_revenue - 1,
                unit="ratio",
                formula="current annual revenue / prior annual revenue - 1",
                sources=_source_tuple(prior.get("revenue"), current.get("revenue")),
            )
        )
    growth_metric = summarize_history_metric("revenue_growth", growth_rows)
    if growth_metric:
        metrics.append(growth_metric)

    full_history = len(set(annual_periods)) >= MIN_ANNUAL_OBSERVATIONS
    return CompanyHistoryProfile(
        policy_version=HISTORY_POLICY_VERSION,
        lane="operating_cash_fcff",
        valuation_date=cutoff,
        annual_periods=annual_periods,
        metrics=tuple(metrics),
        full_history=full_history,
        assumption_source_mix=(
            "reported_and_company_history"
            if full_history
            else "reported_history_and_finsight_policy"
        ),
    )


def material_dependency_requires_conditional(
    *,
    impact_ratio: float,
    changes_economic_object: bool = False,
    determines_positive_value: bool = False,
) -> bool:
    impact = _finite(impact_ratio, "impact_ratio")
    if impact < 0:
        raise ValueError("impact_ratio must be nonnegative")
    return (
        impact > MATERIAL_IMPACT_THRESHOLD
        or bool(changes_economic_object)
        or bool(determines_positive_value)
    )
