"""History-backed practical baselines for controlled Universe Reset Batch 16."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from app.valuation.bank import residual_income_valuation

from .baseline import AssumptionClassification, AvailabilityType, BaselineAssumption, BaselineValuation
from .batch_02_practical_inputs import _normalizer, _normalized_tax_rate, cash_fcff_from_reported
from .batch_04_launch_first import _controlling, _duration, _point, _source_proven_no_other_equity_claims
from .batch_05_launch_first import _companyfacts_duration, _source_proven_no_debt
from .batch_07_history import _structural_flow
from .batch_08_history import _annual_cash_with_losses
from .batch_11_history import _dimension_fact, _no_preferred
from .batch_16 import BATCH_16_TICKERS, BATCH_16_VALUATION_DATE
from .equity_fact_selection import annual_facts
from .history import HISTORY_POLICY_VERSION, CompanyHistoryProfile, HistoryObservation, build_cash_fcff_history_profile, summarize_history_metric
from .practical_models import EnterpriseCashFlowState, enterprise_cash_flow_dcf
from .reliability import assess_reliability


BATCH_16_HISTORY_VERSION = "BATCH-16-HEALTH-CARE-HISTORY-1.0"
FORECAST_YEARS = 8
PASS_TICKERS = frozenset({"VEEV", "IQV"})
CONDITIONAL_TICKERS = frozenset({"A", "PODD"})
WITHHELD_TICKERS = frozenset({"DXCM", "EW", "CRL", "ZBH", "COR", "ELV"})


def _shares(weighted: float, current: float) -> tuple[float, float, float]:
    return (weighted, (weighted + current) / 2., current)


@dataclass(frozen=True)
class Policy:
    method: str
    period: str
    cash: float
    debt: float
    claims: tuple[float, float, float]
    shares: tuple[float, float, float]
    growth: tuple[float, float, float]
    wacc: tuple[float, float, float]
    terminal: tuple[float, float, float]
    warning: str
    invalidation: str
    claim_formula: str


P = {
    "A": Policy("pre_biocare_life_sciences_faded_fcff", "2026-04-30", 2_406_808_000., 3_955_000_000., (44_000_000.,) * 3, _shares(284_000_000., 282_431_944.), (-.02, .03, .06), (.11, .095, .085), (.01, .02, .025), "Conditional Low pre-Biocare life-sciences estimate. The approximately $950M pending cash acquisition is kept separate from current standalone intrinsic value; the cutoff bridge includes June's $600M note issuance and gross cash proceeds once.", "Invalidate if Biocare closes, terminates, or changes; or if note proceeds, standalone cash conversion, debt, NCI, or diluted shares changes materially.", "$44M source-reported VIE noncontrolling interest. June note principal is added to debt and 99.968% gross proceeds to cash; the pending $950M acquisition price is not deducted or probability-weighted."),
    "DXCM": Policy("diabetes_device_reported_operations_faded_fcff", "2026-06-30", 1_947_000_000., 1_295_100_000., (0.,) * 3, _shares(391_800_000., 377_360_765.), (.03, .10, .15), (.12, .10, .09), (.01, .02, .025), "Conditional Low diabetes-device reported-operations baseline. Filed cash history, securities, debt, leases, and shares are modeled; unquantified securities, derivative, and G6/G7 claims remain outside the range and can move actual value materially.", "Invalidate if device safety, growth, cash conversion, securities, debt/leases, shares, or the unresolved claim set changes materially.", "$1.105B cash plus $842M current AFS securities; $1.2428B convertible notes plus $52.3M noncurrent finance lease. No unquantified legal loss is treated as zero or deducted as a guessed amount."),
    "EW": Policy("post_autus_medtech_faded_fcff", "2026-06-30", 4_252_700_000., 598_700_000., (296_300_000., 233_800_000., 171_300_000.), _shares(579_200_000., 576_400_000.), (0., .04, .08), (.11, .095, .085), (.01, .02, .025), "Conditional Low medical-technology estimate. Autus and a newly consolidated medical-device VIE add partial-period cash, contingent consideration, NCI, and acquisition accounting; the current $56.9M litigation reserve is deducted once.", "Invalidate if acquired-device cash, contingent consideration, NCI, PASCAL/Valtech litigation, debt, investments, or diluted shares changes materially.", "$106.9M current NCI + $56.9M litigation reserve + $132.5M Autus maximum/$70M governed midpoint/$7.5M current contingent-consideration liability in bear/base/bull. The $70M midpoint is estimated, not a reported Autus fact. Long-term investments are conservatively excluded from surplus cash."),
    "CRL": Policy("life_sciences_services_reported_operations_faded_fcff", "2026-06-27", 192_025_000., 2_637_381_000., (93_891_000.,) * 3, _shares(48_486_000., 47_738_872.), (-.03, .015, .05), (.12, .105, .095), (.005, .015, .02), "Conditional Low life-sciences-services reported-operations baseline. Current cash history, debt/leases, NCI, redeemable NCI, contingent consideration, and shares are modeled; unquantified securities and derivative claims remain outside the range.", "Invalidate if demand, cash conversion, debt/leases, NCI, contingent consideration, shares, or the securities/derivative claim set changes materially.", "$6.354M NCI + $42.537M redeemable NCI + $45M current/noncurrent contingent consideration. No unquantified securities loss is treated as zero or deducted as a guessed amount."),
    "ZBH": Policy("orthopedic_medtech_reported_operations_faded_fcff", "2026-06-30", 410_000_000., 7_479_000_000., (391_200_000.,) * 3, _shares(194_300_000., 190_737_689.), (-.02, .02, .05), (.11, .095, .085), (.005, .015, .02), "Conditional Low orthopedic-medtech reported-operations baseline. Current cash history, debt, NCI, recorded litigation, contingent consideration, and shares are modeled; China distributor and tax exposure beyond recorded amounts remains outside the range.", "Invalidate if procedure demand, cash conversion, debt, NCI, contingent consideration, shares, China distributor claims, or tax disputes changes materially.", "$8.7M NCI + $137.9M litigation reserve + $244.6M Level-3 contingent consideration. No unquantified China distributor or tax loss is treated as zero or deducted as a guessed amount."),
    "COR": Policy("health_distributor_reported_operations_faded_fcff", "2026-06-30", 2_815_291_000., 11_723_241_000., (4_388_133_000.,) * 3, _shares(194_883_000., 190_827_165.), (0., .04, .07), (.105, .09, .08), (.005, .015, .02), "Conditional Low health-distributor reported-operations baseline. Current cash history, debt, NCI, and the full $4.2B recorded opioid accrual are modeled; claims, penalties, verdicts, and injunctions outside that accrual remain outside the range.", "Invalidate if distribution cash conversion, debt, NCI, shares, the opioid payment schedule, or controlled-substance matters outside the accrual changes materially.", "$188.133M NCI + the full $4.2B reported opioid accrual, including its current and noncurrent portions. No loss outside the accrual is treated as zero or deducted as a guessed amount."),
    "PODD": Policy("insulin_delivery_faded_fcff", "2026-06-30", 534_900_000., 948_400_000., (0.,) * 3, _shares(69_803_000., 69_354_199.), (.02, .07, .10), (.115, .10, .09), (.01, .02, .025), "Conditional Low insulin-delivery baseline. Current cash, debt/capital leases, shares, reinvestment, and the non-recognition of the reversed EOFlow award reconcile, while the July securities class action remains too new for a filed loss range.", "Invalidate if Omnipod growth, cash conversion, manufacturing capex, debt/leases, securities litigation, or diluted shares changes materially.", "No reported NCI or preferred-equity claim. The reversed EOFlow award is not credited as an asset."),
    "VEEV": Policy("debt_free_health_cloud_owner_cash", "2026-04-30", 7_312_719_000., 0., (0.,) * 3, _shares(165_989_000., 162_443_291.), (.05, .10, .14), (.105, .09, .08), (.015, .0225, .025), "Source-bounded debt-free health-cloud owner-cash baseline. Cash, the complete current AFS investment total, software reinvestment, debt absence, and shares reconcile; interest income is not misclassified as an expense addback.", "Invalidate if subscription growth, owner-cash conversion, software reinvestment, securities coverage, debt absence, Ostro integration, or diluted shares changes materially.", "No debt, NCI, or preferred claim. Current owner cash deducts reported software purchases; interest income remains inside operating economics and is not added to cash flow."),
    "IQV": Policy("health_data_services_faded_fcff", "2026-06-30", 2_080_000_000., 16_081_000_000., (130_000_000.,) * 3, _shares(168_600_000., 164_600_000.), (0., .04, .07), (.11, .095, .085), (.01, .02, .025), "Source-bounded health-data-services baseline. Current cash/securities, debt, NCI, shares, and immaterial acquisition consideration reconcile across stable annual cash history.", "Invalidate if bookings/cash conversion, debt, NCI, acquisitions, capex, or diluted shares changes materially.", "$130M reported NCI; current marketable securities are counted once with cash and no preferred claim is reported."),
}


SHARE_STARTS = {"A": "2025-11-01", "DXCM": "2026-01-01", "EW": "2026-01-01", "CRL": "2025-12-28", "ZBH": "2026-01-01", "COR": "2025-10-01", "PODD": "2026-01-01", "VEEV": "2026-02-01", "IQV": "2026-01-01"}
SHARE_ENDS = {"A": "2026-05-27", "DXCM": "2026-07-23", "EW": "2026-07-31", "CRL": "2026-07-25", "ZBH": "2026-07-30", "COR": "2026-07-31", "PODD": "2026-07-29", "VEEV": "2026-06-01", "IQV": "2026-07-21"}
WITHHELD_SHARE_SPECS = {"DXCM": (391_800_000., "2026-01-01", 377_360_765., "2026-07-23"), "CRL": (48_486_000., "2025-12-28", 47_738_872., "2026-07-25"), "ZBH": (194_300_000., "2026-01-01", 190_737_689., "2026-07-30"), "COR": (194_883_000., "2025-10-01", 190_827_165., "2026-07-31")}


POINT_SPECS = {
    "A": (("CashAndCashEquivalentsAtCarryingValue", 1_807_000_000.), ("LongTermDebt", 3_051_000_000.), ("ShortTermBorrowings", 304_000_000.), ("NoncontrollingInterestInVariableInterestEntity", 44_000_000.), ("PreferredStockValue", 0.)),
    "DXCM": (("CashAndCashEquivalentsAtCarryingValue", 1_105_000_000.), ("DebtSecuritiesAvailableForSaleExcludingAccruedInterest", 842_000_000.), ("ConvertibleLongTermNotesPayable", 1_242_800_000.), ("FinanceLeaseLiabilityNoncurrent", 52_300_000.), ("PreferredStockValueOutstanding", 0.)),
    "EW": (("CashAndCashEquivalentsAtCarryingValue", 2_906_500_000.), ("ShortTermInvestments", 1_346_200_000.), ("LongTermDebtNoncurrent", 598_700_000.), ("MinorityInterest", 106_900_000.), ("BusinessCombinationContingentConsiderationLiabilityCurrent", 7_500_000.), ("LitigationReserve", 56_900_000.), ("PreferredStockValue", 0.)),
    "CRL": (("CashAndCashEquivalentsAtCarryingValue", 192_025_000.), ("LongTermDebtGrossAndLeaseObligation", 2_637_381_000.), ("MinorityInterest", 6_354_000.), ("RedeemableNoncontrollingInterestEquityCarryingAmount", 42_537_000.), ("BusinessCombinationContingentConsiderationLiabilityCurrent", 22_500_000.), ("BusinessCombinationContingentConsiderationLiabilityNoncurrent", 22_500_000.), ("PreferredStockValue", 0.)),
    "ZBH": (("CashAndCashEquivalentsAtCarryingValue", 410_000_000.), ("LongTermDebtCurrent", 1_201_500_000.), ("LongTermDebtNoncurrent", 6_277_500_000.), ("MinorityInterest", 8_700_000.), ("LitigationReserve", 137_900_000.)),
    "COR": (("CashAndCashEquivalentsAtCarryingValue", 2_815_291_000.), ("LongTermDebt", 11_723_241_000.), ("MinorityInterest", 188_133_000.), ("LitigationReserveNoncurrent", 3_774_008_000.)),
    "PODD": (("CashCashEquivalentsAndRestrictedCashCurrent", 534_900_000.), ("LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities", 948_400_000.), ("PreferredStockValue", 0.)),
    "VEEV": (("CashAndCashEquivalentsAtCarryingValue", 1_896_580_000.), ("AvailableForSaleSecuritiesDebtSecuritiesCurrent", 5_416_139_000.)),
    "IQV": (("CashAndCashEquivalentsAtCarryingValue", 1_909_000_000.), ("MarketableSecuritiesCurrent", 171_000_000.), ("DebtInstrumentCarryingAmount", 16_081_000_000.), ("MinorityInterest", 130_000_000.)),
}


def _share_point(structural: dict[str, Any], *, expected: float, end: str) -> dict[str, Any]:
    rows = [row for row in structural["facts"] if row.get("local_name") == "EntityCommonStockSharesOutstanding" and row.get("period_start") is None and row.get("period_end") == end and row.get("unit") == "xbrli:shares" and not row.get("dimensions") and isinstance(row.get("value"), (int, float)) and float(row["value"]) == expected]
    if not rows:
        raise ValueError(f"share fact {expected} absent for {end}")
    row = rows[0]
    return {"source_kind": "structural_xbrl", "accession": structural["source_accession"], "period_end": end, "concept": row.get("qname"), "unit": row.get("unit"), "value": expected, "reported_vs_estimated": "reported"}


def _agilent_debt_source(event_root: Path) -> dict[str, Any]:
    packet = Path(event_root) / "A"
    receipt_path = packet / "source-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    document = packet / receipt["primary_document"]
    if receipt.get("schema_version") != "FINSIGHT-BATCH-16-EVENT-SOURCE-1" or receipt.get("valuation_date") != BATCH_16_VALUATION_DATE or receipt.get("accession") != "0001193125-26-282845" or receipt.get("filed") > BATCH_16_VALUATION_DATE or hashlib.sha256(document.read_bytes()).hexdigest() != receipt.get("document_sha256"):
        raise ValueError("Agilent debt-event source is invalid")
    expected = {"principal_usd": 600_000_000, "issue_price_ratio": .99968, "gross_cash_proceeds_before_fees_usd": 599_808_000., "coupon_rate": .049, "maturity": "2032-01-15", "status": "issued_and_outstanding"}
    if receipt.get("reported_terms") != expected:
        raise ValueError("Agilent debt-event terms changed")
    return {"source_kind": "sec_current_report", "accession": receipt["accession"], "filed": receipt["filed"], "form": receipt["form"], "period_end": receipt["report_date"], "url": receipt["url"], "document_sha256": receipt["document_sha256"], "reported_terms": expected, "treatment": "Add $600M principal to debt and 99.968% gross proceeds to cash at cutoff; issuance fees are conservatively not added to cash.", "reported_vs_estimated": "reported"}


def _bridge(ticker: str, structural: dict[str, Any], policy: Policy | None = None) -> list[dict[str, Any]]:
    period = policy.period if policy else {"DXCM": "2026-06-30", "CRL": "2026-06-27", "ZBH": "2026-06-30", "COR": "2026-06-30"}[ticker]
    rows = [_point(structural, name=name, expected=value, period_end=period) for name, value in POINT_SPECS[ticker]]
    if policy:
        rows.extend((_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=policy.shares[0], period_start=SHARE_STARTS[ticker], period_end=period), _share_point(structural, expected=policy.shares[2], end=SHARE_ENDS[ticker])))
    elif ticker in WITHHELD_SHARE_SPECS:
        weighted, start, current, current_end = WITHHELD_SHARE_SPECS[ticker]
        rows.extend((_duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=weighted, period_start=start, period_end=period), _share_point(structural, expected=current, end=current_end)))
    if ticker == "VEEV":
        rows.extend((_source_proven_no_debt(structural, period_end=period), _source_proven_no_other_equity_claims(structural, period_end=period)))
    elif ticker in {"DXCM", "PODD"}:
        rows.append(_source_proven_no_other_equity_claims(structural, period_end=period))
    elif ticker in {"ZBH", "COR", "IQV"}:
        rows.append(_no_preferred(structural, period))
    if ticker == "ZBH":
        rows.append(_dimension_fact(structural, name="BusinessCombinationContingentConsiderationLiability", expected=244_600_000., start=None, end=period, member="FairValueInputsLevel3Member"))
    if ticker == "COR":
        rows.extend((_dimension_fact(structural, name="LossContingencyAccrualAtCarryingValue", expected=4_200_000_000., start=None, end=period, member="OpioidLawsuitsandInvestigationsMember"), _dimension_fact(structural, name="LossContingencyAccrualCarryingValueCurrent", expected=396_200_000., start=None, end=period, member="OpioidLawsuitsandInvestigationsMember")))
    return rows


def _veev_history(normalizer: Any, facts: dict[str, Any]) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    software = annual_facts(facts["facts"]["us-gaap"], concepts=("PaymentsForSoftware",), unit="USD", valuation_date=BATCH_16_VALUATION_DATE)
    software_by_end = {fact.period_end: fact for fact in software.values()}
    rows = []
    for operating in normalizer.annual_series("operating_cash_flow", 5):
        revenue = normalizer.annual_at_end("revenue", operating.end)
        reinvestment = software_by_end.get(operating.end)
        if revenue is None or reinvestment is None:
            continue
        rows.append({"period_end": operating.end, "operating_cash_flow": operating.as_dict(), "capital_expenditures": {"concept": reinvestment.concept, "value": reinvestment.value, "unit": reinvestment.unit, "period_start": reinvestment.period_start, "period_end": reinvestment.period_end, "filed_date": reinvestment.filed_date, "accession": reinvestment.accession, "form": reinvestment.form}, "interest_expense": None, "income_tax": None, "pretax_income": None, "revenue": revenue.as_dict(), "cash_fcff": float(operating.value) - float(reinvestment.value), "formula": "operating cash flow - reported software purchases; no interest addback because current filing has no interest-bearing debt"})
    components = (
        _companyfacts_duration(facts, concept="PaymentsForSoftware", accession="0001393052-26-000014", start="2025-02-01", end="2026-01-31", expected=29_131_000.),
        _companyfacts_duration(facts, concept="PaymentsForSoftware", accession="0001393052-26-000026", start="2026-02-01", end="2026-04-30", expected=1_751_000.),
        _companyfacts_duration(facts, concept="PaymentsForSoftware", accession="0001393052-26-000026", start="2025-02-01", end="2025-04-30", expected=5_910_000.),
    )
    current = {"field": "software_reinvestment", "value": components[0]["value"] + components[1]["value"] - components[2]["value"], "period_end": "2026-04-30", "method": "latest_fy_plus_current_ytd_minus_prior_ytd", "sources": list(components)}
    return tuple(rows), current


def _cash_result(*, ticker: str, filing: dict[str, Any], structural: dict[str, Any], submissions: dict[str, Any], facts: dict[str, Any], event_root: Path, concept_config: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = P[ticker]
    normalizer = _normalizer(submissions, facts, concept_config=concept_config)
    flows = {name: normalizer.ttm_flow(name) for name in ("revenue", "operating_cash_flow")}
    tax_sources: list[dict[str, Any]] = []
    if ticker == "VEEV":
        annual, reinvestment = _veev_history(normalizer, facts)
        flows["capital_expenditures"] = reinvestment
        flows["interest_expense"] = None
        current_cash = float(flows["operating_cash_flow"]["value"]) - float(reinvestment["value"])
    else:
        flows["capital_expenditures"] = normalizer.ttm_flow("capital_expenditures")
        flows["interest_expense"] = normalizer.ttm_flow("interest_expense")
        try:
            tax_rate, tax_rows = _normalized_tax_rate(normalizer)
            tax_sources = list(tax_rows)
        except ValueError:
            tax_rate = .21
        if tax_rate < .05:
            tax_rate = .21
        current_cash = cash_fcff_from_reported(operating_cash_flow=float(flows["operating_cash_flow"]["value"]), capital_expenditures=float(flows["capital_expenditures"]["value"]), spectrum_investment=0., interest_expense=abs(float(flows["interest_expense"]["value"])), tax_rate=tax_rate)
        annual = _annual_cash_with_losses(normalizer)[2]
        if ticker == "PODD":
            annual = tuple(row for row in annual if row["period_end"] >= "2022-12-31")
    sources = [dict(row) for flow in flows.values() if isinstance(flow, dict) for row in flow.get("sources", []) if isinstance(row, dict)]
    revenue = float(flows["revenue"]["value"])
    profile = build_cash_fcff_history_profile(annual_cash_states=annual, ttm_revenue=revenue, ttm_cash_fcff=current_cash, ttm_period_end=policy.period, ttm_sources=sources, valuation_date=BATCH_16_VALUATION_DATE)
    cash_metric = profile.metric("cash_conversion_margin")
    growth_metric = profile.metric("revenue_growth")
    if not profile.full_history or cash_metric is None or growth_metric is None:
        raise ValueError(f"{ticker}: history insufficient")
    margins = tuple(max(.001, value) for value in (cash_metric.low, cash_metric.base, cash_metric.high))
    growth = (max(-.03, min(policy.growth[0], growth_metric.low)), max(0., min(policy.growth[1], growth_metric.base)), max(.02, min(policy.growth[2], growth_metric.high)))
    rows = []
    traces = {}
    for index, name in enumerate(("bear", "base", "bull")):
        state = EnterpriseCashFlowState(cash_fcff=revenue * margins[index], initial_growth=growth[index], terminal_growth=policy.terminal[index], wacc=policy.wacc[index], cash_and_investments=policy.cash, interest_bearing_debt=policy.debt, preferred_equity=0., noncontrolling_interests=policy.claims[index], diluted_shares=policy.shares[index])
        trace = enterprise_cash_flow_dcf(state, forecast_years=FORECAST_YEARS, allow_nonpositive_equity_trace=True)
        raw = float(trace["intrinsic_value_per_share"])
        rows.append({"name": name, "conditional_value_per_share": max(0., raw), "raw_value_per_share": raw, "starting_cash_fcff": state.cash_fcff, "cash_conversion_margin": margins[index], "growth": growth[index], "wacc": policy.wacc[index], "terminal_growth": policy.terminal[index], "cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims[index], "shares": policy.shares[index], "limited_liability_floor_applied": raw < 0})
        traces[name] = trace
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 <= scenario["low"] <= scenario["base"] <= scenario["high"] or scenario["base"] <= 0:
        raise ValueError(f"{ticker}: invalid range")
    is_pass = ticker in PASS_TICKERS
    reasons = () if is_pass else ("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="High" if is_pass else "Low", source_cap="High", reasons=reasons)
    public_history = profile.public_metadata()
    if not is_pass:
        public_history.update({"normalization_basis": "company_history_with_material_event_override", "assumption_source_mix": "reported_history_and_finsight_policy"})
    assumptions = {**public_history, "forecast_years": FORECAST_YEARS, "cash_conversion_margin": margins, "growth": growth, "wacc": policy.wacc, "terminal_growth": policy.terminal, "shares": policy.shares, "equity_floor_basis": "limited-liability floor after negative bear residual" if scenario["low"] == 0 else "not applied", "calculator_calibration": "Calculator is calibrated to the faded-cash base; private source, bridge, and event schedules remain fixed.", "invalidation": policy.invalidation}
    baseline = BaselineValuation(ticker=ticker, method=policy.method, method_version=BATCH_16_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.AVAILABLE if is_pass else AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("company history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Source-linked annual and comparable current cash history supplies cash-conversion states."), BaselineAssumption("faded operating states", str({"growth": growth, "wacc": policy.wacc, "terminal": policy.terminal}), AssumptionClassification.FINSIGHT_ASSUMPTION, "Growth fades over eight years to a terminal rate no higher than 2.5%.")), warnings=(policy.warning, policy.invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link=f"/api/us-valuations/{ticker}/calculator")
    events = []
    if ticker == "A":
        events.extend((_structural_flow(structural, name="BusinessCombinationPriceOfAcquisitionExpected", start="2025-11-01", end=policy.period, expected=950_000_000.), _agilent_debt_source(event_root)))
    if ticker == "EW":
        events.extend((_dimension_fact(structural, name="BusinessCombinationConsiderationTransferred1", expected=128_900_000., start="2026-02-06", end="2026-02-06", member="AutusValveTechnologiesInc.Member"), _dimension_fact(structural, name="BusinessCombinationConsiderationTransferred1", expected=284_700_000., start="2026-05-22", end="2026-05-22", member="MedicalDeviceCompanyMember"), _dimension_fact(structural, name="BusinessCombinationContingentConsiderationArrangementsRangeOfOutcomesValueHigh", expected=132_500_000., start=None, end="2026-02-06", member="AutusValveTechnologiesInc.Member")))
    if ticker == "PODD":
        events.append({"source_kind": "controlling_filing_narrative", "accession": filing["accession"], "filed": filing["filed"], "period_end": filing["period_end"], "event_date": "2026-07-02", "matter": "Hu securities class action", "reported_loss_probability": "not probable", "accrual_usd": 0., "possible_loss_range": None, "treatment": "Conditional Low warning; zero is the reported accrual outcome and is not substituted as a loss estimate.", "reported_vs_estimated": "reported narrative"})
    if ticker == "VEEV":
        events.extend((_dimension_fact(structural, name="BusinessCombinationConsiderationTransferred1", expected=90_000_000., start="2026-03-09", end="2026-03-09", member="OstroMember"), _dimension_fact(structural, name="PaymentsToAcquireBusinessesNetOfCashAcquired", expected=70_000_000., start="2026-03-09", end="2026-03-09", member="OstroMember")))
    if ticker == "IQV":
        events.extend((_structural_flow(structural, name="PaymentsToAcquireBusinessesNetOfCashAcquired", start="2026-01-01", end="2026-06-30", expected=200_000_000.), _dimension_fact(structural, name="BusinessCombinationRecognizedIdentifiableAssetsAcquiredGoodwillAndLiabilitiesAssumedNet", expected=240_000_000., start=None, end="2026-06-30", member="SeriesOfIndividuallyImmaterialBusinessAcquisitionsMember"), _dimension_fact(structural, name="BusinessCombinationContingentConsiderationAssetAndDeferredPurchasePayments", expected=26_000_000., start="2026-04-01", end="2026-06-30", member="SeriesOfIndividuallyImmaterialBusinessAcquisitionsMember"), _structural_flow(structural, name="RestructuringCharges", start="2026-01-01", end="2026-06-30", expected=114_000_000.)))
    return {"ticker": ticker, "method": policy.method, "model_version": BATCH_16_HISTORY_VERSION, "availability_type": "available" if is_pass else "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_revenue": flows["revenue"]["value"], "ttm_operating_cash_flow": flows["operating_cash_flow"]["value"], "ttm_reinvestment": flows["capital_expenditures"]["value"], "ttm_interest": None if flows["interest_expense"] is None else flows["interest_expense"]["value"], "ttm_cash_fcff_or_owner_cash": current_cash}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "flow_sources": flows, "tax_rate_sources": tax_sources, "company_history_profile": profile.as_private_dict(), "bridge_sources": _bridge(ticker, structural, policy), "event_sources": events, "bridge_reconciliation": {"cash_and_investments": policy.cash, "debt_and_finance_leases": policy.debt, "other_equity_claims": policy.claims, "other_equity_claim_formula": policy.claim_formula, "shares": policy.shares, "operating_liability_treatment": "Operating leases and recorded ordinary legal/contract liabilities already represented in cash conversion are not deducted again."}, "model_trace": {"forecast_years": FORECAST_YEARS, "states": traces}, "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": policy.warning, "baseline": baseline.as_private_dict()}


def _history_source(fact: Any) -> dict[str, Any]:
    return {"concept": fact.concept, "value": fact.value, "unit": fact.unit, "period_start": fact.period_start, "period_end": fact.period_end, "filed_date": fact.filed_date, "accession": fact.accession, "form": fact.form, "fiscal_year": fact.fiscal_year}


def _elv_result(filing: dict[str, Any], structural: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    gaap = facts["facts"]["us-gaap"]
    net = annual_facts(gaap, concepts=("NetIncomeLoss",), unit="USD", valuation_date=BATCH_16_VALUATION_DATE)
    nci = annual_facts(gaap, concepts=("NetIncomeLossAttributableToNoncontrollingInterest",), unit="USD", valuation_date=BATCH_16_VALUATION_DATE)
    observations = []
    annual_sources = {}
    annual_values = {}
    for year in (2021, 2022, 2023, 2024, 2025):
        fact = net[year]
        nci_fact = nci.get(year)
        value = float(fact.value) - (float(nci_fact.value) if nci_fact else 0.)
        sources = (_history_source(fact),) + ((_history_source(nci_fact),) if nci_fact else ())
        annual_values[year] = value
        annual_sources[year] = sources
        observations.append(HistoryObservation("annual", fact.period_end, fact.fiscal_year, value, "USD", "reported parent-attributable earnings", sources))
    current_net = _structural_flow(structural, name="NetIncomeLoss", start="2026-01-01", end="2026-06-30", expected=3_227_000_000.)
    current_nci = _structural_flow(structural, name="NetIncomeLossAttributableToNoncontrollingInterest", start="2026-01-01", end="2026-06-30", expected=-13_000_000.)
    prior_net = _structural_flow(structural, name="NetIncomeLoss", start="2025-01-01", end="2025-06-30", expected=3_926_000_000.)
    prior_nci = _structural_flow(structural, name="NetIncomeLossAttributableToNoncontrollingInterest", start="2025-01-01", end="2025-06-30", expected=2_000_000.)
    ttm = annual_values[2025] + current_net["value"] - current_nci["value"] - (prior_net["value"] - prior_nci["value"])
    observations.append(HistoryObservation("operating_ttm", "2026-06-30", None, ttm, "USD", "latest FY + current H1 - prior H1 parent earnings", annual_sources[2025] + (current_net, current_nci, prior_net, prior_nci)))
    metric = summarize_history_metric("normalized_common_earnings", observations)
    if metric is None:
        raise ValueError("ELV earnings history unavailable")
    profile = CompanyHistoryProfile(HISTORY_POLICY_VERSION, "managed_care_residual_income", BATCH_16_VALUATION_DATE, tuple(row.period_end for row in observations if row.period_role == "annual"), (metric,), True, "reported_and_company_history")
    beginning_equity, ending_equity = 43_882_000_000., 44_883_000_000.
    average_equity = (beginning_equity + ending_equity) / 2.
    shares = _shares(219_100_000., 216_869_290.)
    earnings = (metric.low, metric.base, metric.high)
    dividends = 749_000_000.
    payout = min(1., dividends * 2. / ttm)
    cost_of_equity, terminal_roe, terminal_growth = (.12, .10, .085), (.07, .105, .14), (.01, .02, .025)
    rows = []
    traces = {}
    multiples = []
    for index, name in enumerate(("bear", "base", "bull")):
        trace = residual_income_valuation(book_value_per_share=ending_equity / shares[index], current_roe=earnings[index] / average_equity, cost_of_equity=cost_of_equity[index], current_payout_ratio=payout, terminal_roe=terminal_roe[index], terminal_growth=terminal_growth[index], years=5)
        raw = float(trace["intrinsic_value"])
        multiple = raw * shares[index] / earnings[index]
        rows.append({"name": name, "conditional_value_per_share": raw, "raw_value_per_share": raw, "normalized_common_earnings": earnings[index], "book_value_per_share": ending_equity / shares[index], "current_roe": earnings[index] / average_equity, "current_payout_ratio": payout, "cost_of_equity": cost_of_equity[index], "terminal_roe": terminal_roe[index], "terminal_growth": terminal_growth[index], "earnings_multiple": multiple, "shares": shares[index], "limited_liability_floor_applied": False})
        traces[name] = trace
        multiples.append(multiple)
    scenario = {"low": rows[0]["conditional_value_per_share"], "base": rows[1]["conditional_value_per_share"], "high": rows[2]["conditional_value_per_share"]}
    if not 0 < scenario["low"] <= scenario["base"] <= scenario["high"]:
        raise ValueError("ELV range invalid")
    reliability = assess_reliability(accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"], scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"], model_cap="Low", source_cap="High", reasons=("CONDITIONAL_EVENT_MODEL", "SPECIALIST_MODEL_UNCERTAINTY"))
    warning = "Conditional Low managed-care residual-income estimate. Medical claims, regulated capital, current CMS loss range, Mosaic funding, and member-fund economics remain material; no industrial EV debt bridge is applied."
    invalidation = "Invalidate if common earnings/equity, medical claims, regulated capital, CMS loss range, Mosaic funding, NCI, or diluted shares changes materially."
    assumptions = {**profile.public_metadata(), "normalization_basis": "reported_common_equity_and_history_residual_income", "assumption_source_mix": "reported_common_equity_earnings_dividends_and_finsight_policy", "normalized_common_earnings": earnings, "earnings_multiples": tuple(multiples), "shares": shares, "book_equity": ending_equity, "average_common_equity": average_equity, "current_payout_ratio": payout, "cost_of_equity": cost_of_equity, "terminal_roe": terminal_roe, "terminal_growth": terminal_growth, "route_is_equity_level": True, "ev_debt_bridge_applied": False, "equity_floor_basis": "not applied", "calculator_calibration": "Calculator varies normalized common earnings and the residual-income-implied multiple around the published base.", "invalidation": invalidation}
    baseline = BaselineValuation(ticker="ELV", method="managed_care_residual_income_normalized_equity_earnings", method_version=BATCH_16_HISTORY_VERSION, low=scenario["low"], base=scenario["base"], high=scenario["high"], confidence=reliability.label, availability_type=AvailabilityType.CONDITIONAL, key_assumptions=(BaselineAssumption("reported common equity", ending_equity, AssumptionClassification.REPORTED, "Current parent equity supplies the residual-income anchor."), BaselineAssumption("company earnings history", str(profile.history_years_used), AssumptionClassification.HISTORICALLY_DERIVED, "Parent-attributable earnings history supplies the ROE range."), BaselineAssumption("managed-care residual-income policy", str({"cost_of_equity": cost_of_equity, "terminal_roe": terminal_roe}), AssumptionClassification.FINSIGHT_ASSUMPTION, "Claims and regulated capital remain inside common earnings/equity.")), warnings=(warning, invalidation), confidence_reasons=tuple(reliability.reasons), calculator_link="/api/us-valuations/ELV/calculator")
    context = [_point(structural, name="StockholdersEquity", expected=beginning_equity, period_end="2025-12-31"), _point(structural, name="StockholdersEquity", expected=ending_equity, period_end="2026-06-30"), _point(structural, name="LiabilityForClaimsAndClaimsAdjustmentExpense", expected=18_463_000_000., period_end="2026-06-30"), _dimension_fact(structural, name="RedeemableNoncontrollingInterestEquityPreferredRedemptionValue", expected=250_000_000., start=None, end="2026-06-30", member="LibertyDentalMember"), _point(structural, name="MinorityInterest", expected=139_000_000., period_end="2026-06-30"), _point(structural, name="PreferredStockValue", expected=0., period_end="2026-06-30"), _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=219_100_000., period_start="2026-01-01", period_end="2026-06-30"), _share_point(structural, expected=216_869_290., end="2026-07-10"), _structural_flow(structural, name="PaymentsOfDividends", start="2026-01-01", end="2026-06-30", expected=dividends), _dimension_fact(structural, name="LossContingencyEstimateOfPossibleLoss", expected=593_000_000., start=None, end="2026-06-30", member="CMSNoticeOfPossibleSanctionMember"), _dimension_fact(structural, name="LossContingencyEstimateOfPossibleLoss", expected=320_000_000., start=None, end="2026-06-30", member="MaximumMember"), _dimension_fact(structural, name="LossContingencyAccrualPayments", expected=342_000_000., start="2026-04-01", end="2026-06-30", member="CMSNoticeOfPossibleSanctionMember"), _dimension_fact(structural, name="EquityMethodInvestmentFundingCommitment", expected=70_000_000., start=None, end="2026-06-30", member="MosaicHealthMember")]
    return {"ticker": "ELV", "method": baseline.method, "model_version": BATCH_16_HISTORY_VERSION, "availability_type": "conditional_estimate", "scenario_rows": rows, "scenario_range": scenario, "reported_inputs": {"ttm_common_earnings": ttm, "beginning_common_equity": beginning_equity, "ending_common_equity": ending_equity, "h1_common_dividends": dividends}, "governed_assumptions": assumptions, "history_reliability": reliability.as_dict(), "source_ledger": {"controlling_filing": filing, "company_history_profile": profile.as_private_dict(), "equity_model_context": context, "residual_income_trace": {"states": traces}, "bridge_treatment": "Equity-level managed-care model; claims, member funds, investments, debt, regulated capital, and NCI remain inside parent earnings/common equity. The $593M current CMS accrual already reduces equity/earnings and is not deducted again; $320M additional downside widens reliability rather than creating an EV bridge.", "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def _withheld(ticker: str, filing: dict[str, Any], structural: dict[str, Any]) -> dict[str, Any]:
    details = {
        "DXCM": ("unavailable_unbounded_securities_and_device_class_claims", "Withheld. Current securities, derivative, and G6/G7 device class actions seek damages and related relief, while the filing says their ultimate outcomes cannot be reasonably estimated.", "Revalue after current securities/derivative and G6/G7 class claims have source-supported finite ranges."),
        "CRL": ("unavailable_unbounded_securities_class_claims", "Withheld. Current securities and related derivative actions have no reasonably estimable maximum exposure or loss range.", "Revalue after the securities and derivative claim set is resolved or source bounded."),
        "EW": ("unavailable_unbounded_patent_milestone_and_tax_claims", "Withheld. PASCAL patent, Valtech milestone, and tax matters can materially affect a reporting period, while the filing provides no finite excess-loss range beyond recorded reserves.", "Revalue after the PASCAL, Valtech, and material tax exposure beyond recorded reserves has a source-supported finite range."),
        "ZBH": ("unavailable_unbounded_china_distributor_and_tax_claims", "Withheld. China distributor lawsuits and IRS/foreign tax disputes may materially affect results, while losses beyond current accruals and proposed adjustments cannot be estimated.", "Revalue after the China distributor claims, tax-audit exposure, and any excess over recorded accruals have finite source-backed ranges."),
        "COR": ("unavailable_unbounded_opioid_claims", "Withheld. The approximately $4.2B recorded opioid liability is finite, but the filing cannot estimate losses for opioid matters outside that accrual and says ultimate loss may differ materially.", "Revalue after all material opioid matters outside the recorded settlement accrual have a finite source-backed range."),
        "ELV": ("unavailable_unbounded_medicare_risk_adjustment_litigation", "Withheld. The current CMS administrative exposure is bounded, but the separate DOJ Medicare risk-adjustment False Claims Act lawsuit alleges unspecified payments and could create material liability beyond current accruals.", "Revalue after the DOJ Medicare risk-adjustment litigation has a source-supported finite loss range or is resolved."),
    }
    method, warning, release = details[ticker]
    baseline = BaselineValuation(ticker=ticker, method=method, method_version=BATCH_16_HISTORY_VERSION, low=None, base=None, high=None, confidence=None, availability_type=AvailabilityType.NOT_AVAILABLE, warnings=(warning, release))
    if ticker == "ELV":
        bridge = [_point(structural, name="StockholdersEquity", expected=44_883_000_000., period_end="2026-06-30"), _point(structural, name="LiabilityForClaimsAndClaimsAdjustmentExpense", expected=18_463_000_000., period_end="2026-06-30"), _point(structural, name="LongTermDebt", expected=31_044_000_000., period_end="2026-06-30"), _point(structural, name="MinorityInterest", expected=139_000_000., period_end="2026-06-30"), _dimension_fact(structural, name="RedeemableNoncontrollingInterestEquityPreferredRedemptionValue", expected=250_000_000., start=None, end="2026-06-30", member="LibertyDentalMember"), _duration(structural, name="WeightedAverageNumberOfDilutedSharesOutstanding", expected=219_100_000., period_start="2026-01-01", period_end="2026-06-30"), _share_point(structural, expected=216_869_290., end="2026-07-10")]
    elif ticker == "EW":
        bridge = _bridge(ticker, structural, P["EW"])
        bridge.extend((_point(structural, name="LongTermInvestments", expected=244_100_000., period_end="2026-06-30"), _point(structural, name="DebtSecuritiesHeldToMaturityAmortizedCostAfterAllowanceForCreditLoss", expected=39_000_000., period_end="2026-06-30")))
    else:
        bridge = _bridge(ticker, structural)
    return {"ticker": ticker, "method": method, "model_version": BATCH_16_HISTORY_VERSION, "availability_type": "not_available", "scenario_rows": [], "scenario_range": {"low": None, "base": None, "high": None}, "reported_inputs": {}, "governed_assumptions": {"history_policy_version": HISTORY_POLICY_VERSION, "history_years_used": 0, "normalization_basis": "material_unbounded_current_claims", "assumption_source_mix": "reported_current_claim_disclosure_without_estimable_total_range", "invalidation": release}, "history_reliability": None, "source_ledger": {"controlling_filing": filing, "bridge_sources": bridge, "economically_suitable_model_if_released": "managed_care_residual_income_normalized_equity_earnings" if ticker == "ELV" else None, "excluded_financial_assets": {"long_term_investments_usd": 244_100_000., "held_to_maturity_component_usd": 39_000_000., "treatment": "conservatively excluded from surplus cash; the held-to-maturity component is not added separately because it is within long-term investments"} if ticker == "EW" else None, "recovery_release_condition": release, "hard_blocker": "CLAIMS_UNBOUNDED", "structural_top_level_period_diagnostic": {"value": structural.get("period_end"), "used_for_selection": False}}, "warning": warning, "baseline": baseline.as_private_dict()}


def build_batch_16_history_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path) -> dict[str, Any]:
    if ticker not in BATCH_16_TICKERS:
        raise ValueError(f"unexpected Batch 16 ticker {ticker}")
    packet = Path(source_root) / ticker
    submissions = json.loads((packet / "submissions.json").read_text())
    facts = json.loads((packet / "companyfacts.json").read_text())
    manifest = json.loads((packet / "source-manifest.json").read_text())
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    filing = _controlling(manifest, submissions)
    if structural["source_accession"] != filing["accession"]:
        raise ValueError(f"{ticker}: controlling source mismatch")
    if ticker in WITHHELD_TICKERS:
        return _withheld(ticker, filing, structural)
    if filing["period_end"] != P[ticker].period:
        raise ValueError(f"{ticker}: period mismatch")
    return _cash_result(ticker=ticker, filing=filing, structural=structural, submissions=submissions, facts=facts, event_root=event_root)


if set(P) | {"ELV"} | set(WITHHELD_TICKERS) != set(BATCH_16_TICKERS):
    raise RuntimeError("Batch 16 denominator mismatch")
