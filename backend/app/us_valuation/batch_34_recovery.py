"""Single conservative recovery attempt for confirmed Batch 34.

Recovery is intentionally a thin, auditable layer over the confirmed history
run.  It does not invent data or silently promote a company: it records the
smallest missing issuer-specific release condition and leaves the numerical
baseline conditional until that condition is source-proven.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .batch_34 import BATCH_34_TICKERS
from .batch_34_history import BATCH_34_HISTORY_VERSION, build_batch_34_history_result
from app.valuation.bank import residual_income_valuation
from .reliability import assess_reliability


BATCH_34_RECOVERY_VERSION = "BATCH-34-ONE-ATTEMPT-RECOVERY-1.0"
RECOVERY_ATTEMPT = 1
RECOVERED_PASS_TICKERS = frozenset({"USB"})
RECOVERED_CONDITIONAL_TICKERS = frozenset(set(BATCH_34_TICKERS) - RECOVERED_PASS_TICKERS)
RECOVERED_WITHHELD_TICKERS = frozenset()
IMPLEMENTED_REPAIRS = frozenset({"USB", "BRO", "NTRS", "STT"})


RECOVERY_PLAN = {
    "USB": ("source_current_CET1_and_preferred_capital_package", "Tested and released to Pass after current capital ratios, preferred claims and source receipt identity reconciled; reliability follows the resulting scenario width."),
    "L": ("source_statutory_capital_and_parent_liquidity_package", "Pending: insurance-subsidiary capital, reserve development, parent liquidity/upstreaming and preferred absence remain to be source-bounded."),
    "SPGI": ("replace_generic_equity_route_with_data_and_ratings_history_route", "Pending: ratings/data segment history, acquisition integration and recurring content/software investment remain to be source-bounded."),
    "NTRS": ("source_exact_preferred_carrying_or_liquidation_claim", "Tested, but still Conditional: exact preferred carrying value is repaired; the post-cutoff redemption and custody economics remain open."),
    "BRO": ("source_proven_preferred_absence", "Tested preferred/NCI presentation; Conditional retained pending a bounded acquisition/reinvestment program treatment; retain Low reliability."),
    "PGR": ("source_statutory_capital_reserve_and_preferred_absence_package", "Pending: catastrophe/reserve volatility and statutory-capital evidence remain to be source-bounded."),
    "TRV": ("source_statutory_capital_reserve_and_preferred_absence_package", "Pending: catastrophe/reserve volatility, statutory capital, the July debt event and preferred absence remain to be source-bounded."),
    "KEY": ("source_current_capital_and_cutoff_redemption_package", "Pending: current capital and the September redemption state remain to be source-bounded; the redemption is not completed at cutoff."),
    "TFC": ("source_current_capital_and_debt_event_reconciliation", "Pending: current capital and the July note offering require final reconciliation to the quarter-end preferred/debt state without double counting."),
    "STT": ("source_exact_preferred_carrying_claim_after_series_l", "Tested, but still Conditional: Series L and exact preferred claim are repaired; the broader capital gate remains open."),
}

CAPITAL_EVIDENCE = {
    "USB": {
        "source_kind": "controlling_filing_narrative",
        "accession": "0000036104-26-000044",
        "filed": "2026-08-06",
        "report_date": "2026-06-30",
        "document": "usb-20260630.htm",
        "document_sha256": "7cefe125f517c78d775218d4ded14c907abd182a5f64fd338b0d7773b787777a",
        "cet1_ratio": 0.108,
        "tier1_ratio": 0.122,
        "total_risk_based_capital_ratio": 0.144,
        "leverage_ratio": 0.089,
        "well_capitalized": True,
        "reported_vs_estimated": "reported",
        "treatment": "Exact controlling-filing capital ratios bound the regulatory-capital uncertainty; the $6.808B preferred claim is already separately reported in the equity bridge.",
    }
}

BRO_PREFERRED_ABSENCE = {
    "source_kind": "controlling_filing_equity_presentation",
    "accession": "0001193125-26-318251",
    "filed": "2026-07-27",
    "report_date": "2026-06-30",
    "document": "bro-20260630.htm",
    "document_sha256": "863bb140e537d61df6fc35273583906a10ae5210a9f439e30a5c7e9d42a5edeb",
    "common_equity_including_nci": 12_608_000_000.,
    "reported_nci": 25_000_000.,
    "preferred_claim": 0.,
    "reported_vs_estimated": "reported_equity_presentation",
    "treatment": "The filing presents common equity and a separate $25M minority-interest component without a preferred-stock claim; common equity is reduced by NCI and no preferred placeholder is added.",
}

BRO_ACQUISITION_EVIDENCE = {
    "source_kind": "reported_acquisition_reinvestment_trace",
    "annual_filing": {
        "accession": "0001193125-26-046984",
        "filed": "2026-02-12",
        "form": "10-K",
        "period_end": "2025-12-31",
        "primary_document": "bro-20251231.htm",
    },
    "current_filing": {
        "accession": "0001193125-26-318251",
        "filed": "2026-07-27",
        "form": "10-Q",
        "period_end": "2026-06-30",
        "primary_document": "bro-20260630.htm",
    },
    "acquisition_count_2025": 43,
    "payments_to_acquire_businesses_2025": 7_854_000_000.,
    "payments_to_acquire_businesses_current_ytd": 30_000_000.,
    "payments_to_acquire_businesses_prior_ytd": 161_000_000.,
    "payments_to_acquire_businesses_ttm": 7_723_000_000.,
    "reported_revenue_2025": 5_902_000_000.,
    "pro_forma_revenue_2025": 6_947_000_000.,
    "reported_vs_estimated": "reported",
    "treatment": "Acquisition cash and pro-forma revenue are recorded as a material reinvestment dependency; no acquisition spend is subtracted from the residual-income value until a governed continuing-earnings/reinvestment bridge is built.",
}


def _companyfacts_value(facts: dict, concept: str, *, start: str, end: str, accession: str) -> float:
    rows = facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", [])
    matches = [row for row in rows if row.get("start") == start and row.get("end") == end and row.get("accn") == accession and isinstance(row.get("val"), (int, float))]
    if len(matches) != 1:
        raise ValueError(f"BRO: expected one {concept} fact for {start}/{end}/{accession}")
    return float(matches[0]["val"])


def _bro_acquisition_trace(source_root: Path) -> dict:
    facts = json.loads((Path(source_root) / "BRO" / "companyfacts.json").read_text())
    annual = _companyfacts_value(facts, "PaymentsToAcquireBusinessesNetOfCashAcquired", start="2025-01-01", end="2025-12-31", accession=BRO_ACQUISITION_EVIDENCE["annual_filing"]["accession"])
    current = _companyfacts_value(facts, "PaymentsToAcquireBusinessesNetOfCashAcquired", start="2026-01-01", end="2026-06-30", accession=BRO_ACQUISITION_EVIDENCE["current_filing"]["accession"])
    prior = _companyfacts_value(facts, "PaymentsToAcquireBusinessesNetOfCashAcquired", start="2025-01-01", end="2025-06-30", accession=BRO_ACQUISITION_EVIDENCE["current_filing"]["accession"])
    revenue = _companyfacts_value(facts, "Revenues", start="2025-01-01", end="2025-12-31", accession=BRO_ACQUISITION_EVIDENCE["annual_filing"]["accession"])
    pro_forma = _companyfacts_value(facts, "BusinessAcquisitionsProFormaRevenue", start="2025-01-01", end="2025-12-31", accession=BRO_ACQUISITION_EVIDENCE["annual_filing"]["accession"])
    if (annual, current, prior, revenue, pro_forma) != (7_854_000_000., 30_000_000., 161_000_000., 5_902_000_000., 6_947_000_000.):
        raise ValueError("BRO: acquisition trace fact mismatch")
    trace = dict(BRO_ACQUISITION_EVIDENCE)
    trace.update({
        "payments_to_acquire_businesses_2025": annual,
        "payments_to_acquire_businesses_current_ytd": current,
        "payments_to_acquire_businesses_prior_ytd": prior,
        "payments_to_acquire_businesses_ttm": annual + current - prior,
        "reported_revenue_2025": revenue,
        "pro_forma_revenue_2025": pro_forma,
        "pro_forma_revenue_uplift": pro_forma - revenue,
        "ttm_formula": "2025 FY + 2026 H1 - 2025 H1",
    })
    if trace["payments_to_acquire_businesses_ttm"] != 7_723_000_000.:
        raise ValueError("BRO: acquisition TTM arithmetic mismatch")
    return trace

EXACT_PREFERRED = {
    "NTRS": {
        "claim": 884_900_000.,
        "values": (493_500_000., 391_400_000.),
        "document": "ntrs-20260630.htm",
        "document_sha256": "439487f3afb6b3f2f05034662a686eba2496f685d987dfb1d0c73c634b81fb49",
        "accession": "0000073124-26-000047",
        "event_note": "Series D redemption announced for 2026-10-01, after the 2026-08-14 cutoff; not removed.",
    },
    "STT": {
        "claim": 4_059_000_000.,
        "values": (493_000_000., 1_481_000_000., 842_000_000., 743_000_000., 500_000_000.),
        "document": "stt-20260630.htm",
        "document_sha256": "5e546e7cf8f416ef3a9a5f4f9858ff009bea7dddba26c8545b3f8784f0ca6dad",
        "accession": "0000093751-26-000397",
        "event_note": "Series L $500M issuance completed 2026-08-12, before the cutoff; included once.",
    },
}

BEGINNING_PREFERRED_VALUES = {
    "NTRS": (493_500_000., 391_400_000.),
    "STT": (493_000_000., 1_481_000_000., 842_000_000., 743_000_000.),
}


def _dimensional_preferred_sources(
    structural_root: Path,
    ticker: str,
    *,
    period_end: str = "2026-06-30",
    values: tuple[float, ...] | None = None,
) -> tuple[dict, ...]:
    spec = EXACT_PREFERRED[ticker]
    structural = json.loads((Path(structural_root) / ticker / "structural-filing.json").read_text())
    selected_values = tuple(values if values is not None else (spec["values"][:-1] if ticker == "STT" else spec["values"]))
    wanted = set(selected_values)
    rows = []
    seen = set()
    for row in structural.get("facts", []):
        dimensions = tuple(tuple(item) for item in row.get("dimensions", []))
        if (
            row.get("local_name") == "PreferredStockValue"
            and row.get("period_start") is None
            and row.get("period_end") == period_end
            and row.get("unit") == "USD"
            and any(item[0] == "us-gaap:StatementClassOfStockAxis" for item in dimensions)
            and float(row.get("value", 0.)) in wanted
        ):
            key = (float(row["value"]), dimensions)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"source_kind": "structural_xbrl", "accession": spec["accession"], "filed": "2026-07-30", "form": "10-Q", "period_start": None, "period_end": period_end, "concept": row.get("qname"), "unit": row.get("unit"), "value": float(row["value"]), "dimensions": [list(item) for item in dimensions], "reported_vs_estimated": "reported"})
    if sum(row["value"] for row in rows) != sum(selected_values):
        raise ValueError(f"{ticker}: exact dimensional preferred claim rows incomplete")
    return tuple(rows)


def _dedupe_rows(rows: list[dict] | tuple[dict, ...]) -> list[dict]:
    """Keep one copy of identical evidence rows while preserving source order."""
    result: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        key = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _reprice_with_claim(
    initial: dict,
    ticker: str,
    claim_range: tuple[float, float, float],
    status: str,
    sources: tuple[dict, ...],
    *,
    beginning_claim_range: tuple[float, float, float] | None = None,
) -> dict:
    value = deepcopy(initial)
    current_equity = float(initial["reported_inputs"]["ending_total_equity"])
    prior_equity = float(initial["reported_inputs"]["beginning_total_equity"])
    ttm = float(initial["reported_inputs"]["ttm_common_earnings"])
    shares = tuple(initial["governed_assumptions"]["shares"])
    beginning_claim_range = tuple(beginning_claim_range or claim_range)
    bridge = initial["governed_assumptions"]["roe_scenario_bridge"]
    metric_low, metric_base, metric_high = tuple(bridge["reported_history_annual_plus_ttm_range"])
    base_begin_common = prior_equity - beginning_claim_range[1]
    base_end_common = current_equity - claim_range[1]
    history_low_roe = max(.02, min(metric_low, ttm) / max(base_end_common, 1.))
    history_high_roe = max(history_low_roe, max(metric_high, ttm) / max(base_end_common, 1.))
    history_mid_roe = max(history_low_roe, min(history_high_roe, metric_base / max(base_end_common, 1.)))
    from .batch_34_history import P
    policy_roe = P[ticker].roe
    modeled_roe = tuple(min(item, history_high_roe) for item in policy_roe)
    if not history_low_roe <= modeled_roe[0] <= modeled_roe[1] <= modeled_roe[2] <= history_high_roe or modeled_roe[0] == modeled_roe[2]:
        modeled_roe = (history_low_roe, (history_low_roe + history_high_roe) / 2., history_high_roe)
    rows, traces = [], {}
    for idx, old in enumerate(initial["scenario_rows"]):
        end_common = current_equity - claim_range[idx]
        begin_common = prior_equity - beginning_claim_range[idx]
        trace = residual_income_valuation(book_value_per_share=end_common / shares[idx], current_roe=modeled_roe[idx], cost_of_equity=old["cost_of_equity"], current_payout_ratio=old["current_payout_ratio"], terminal_roe=old["terminal_roe"], terminal_growth=old["terminal_growth"], years=5)
        raw = float(trace["intrinsic_value"])
        row = {**old, "raw_value_per_share": raw, "conditional_value_per_share": raw, "book_value_per_share": end_common / shares[idx], "current_roe": modeled_roe[idx], "normalized_common_earnings": end_common * modeled_roe[idx], "earnings_multiple": raw * shares[idx] / ttm, "preferred_claim": claim_range[idx], "beginning_preferred_claim": beginning_claim_range[idx], "beginning_common_equity": begin_common, "ending_common_equity": end_common}
        rows.append(row)
        traces[old["name"]] = trace
    scenario = {"low": rows[0]["raw_value_per_share"], "base": rows[1]["raw_value_per_share"], "high": rows[2]["raw_value_per_share"]}
    reliability_input = initial["history_reliability"]
    reliability = assess_reliability(
        accounting_low=scenario["base"], accounting_base=scenario["base"], accounting_high=scenario["base"],
        scenario_low=scenario["low"], scenario_base=scenario["base"], scenario_high=scenario["high"],
        model_cap=reliability_input["model_cap"], source_cap=reliability_input["source_cap"],
        reasons=tuple(reliability_input["reasons"]),
    )
    value["scenario_rows"] = rows
    value["scenario_range"] = scenario
    value["history_reliability"] = reliability.as_dict()
    value["reported_inputs"].update({"preferred_equity": claim_range[1], "beginning_preferred_equity": beginning_claim_range[1], "beginning_common_equity": base_begin_common, "ending_common_equity": base_end_common})
    assumptions = value["governed_assumptions"]
    assumptions.update({"preferred_claim_status": status, "preferred_claim_range": claim_range, "beginning_preferred_claim_range": beginning_claim_range, "beginning_common_equity": base_begin_common, "ending_common_equity": base_end_common, "current_roe": modeled_roe, "roe_scenario_bridge": {**bridge, "reported_ttm_roe": ttm / ((base_begin_common + base_end_common) / 2), "reported_history_roe_range": (history_low_roe, history_mid_roe, history_high_roe), "modeled_roe": modeled_roe}})
    value["source_ledger"]["preferred_context"] = _dedupe_rows([*value["source_ledger"].get("preferred_context", []), *sources])
    value["source_ledger"]["equity_model_context"] = _dedupe_rows([*value["source_ledger"].get("equity_model_context", []), *sources])
    value["source_ledger"]["residual_income_trace"] = {"states": traces, "clean_surplus_ddm_is_reconciliation_not_independent_evidence": True}
    value["baseline"] = {**value["baseline"], "low": scenario["low"], "base": scenario["base"], "high": scenario["high"], "confidence": reliability.label, "confidence_reasons": list(reliability.reasons), "availability_type": "available" if ticker in RECOVERED_PASS_TICKERS else "conditional"}
    return value


def _runtime_source_receipt(structural_root: Path, ticker: str, controlling: dict) -> dict:
    """Verify the captured controlling filing receipt used for Pass promotion."""
    root = Path(structural_root) / ticker
    receipt_path = root / "source-receipt.json"
    structural_path = root / "structural-filing.json"
    package_path = root / "package-manifest.json"
    if not receipt_path.exists() or not structural_path.exists() or not package_path.exists():
        raise ValueError(f"{ticker}: runtime source receipt is incomplete")
    receipt = json.loads(receipt_path.read_text())
    structural = json.loads(structural_path.read_text())
    package = json.loads(package_path.read_text())
    if receipt.get("schema_version") != "FINSIGHT-BATCH-34-STRUCTURAL-SOURCE-1":
        raise ValueError(f"{ticker}: unsupported runtime source receipt")
    filing = receipt.get("filing") or {}
    expected = {
        "accession": controlling.get("accession"),
        "filed": controlling.get("filed"),
        "form": controlling.get("form"),
        "report_date": controlling.get("period_end"),
    }
    actual = {
        "accession": filing.get("accession"),
        "filed": filing.get("filed"),
        "form": filing.get("form"),
        "report_date": filing.get("report_date"),
    }
    if receipt.get("ticker") != ticker or receipt.get("valuation_date") != "2026-08-14" or actual != expected:
        raise ValueError(f"{ticker}: runtime source receipt does not match controlling filing")
    if structural.get("source_accession") != controlling.get("accession") or structural.get("report_date") != controlling.get("period_end"):
        raise ValueError(f"{ticker}: runtime structural source does not match controlling filing")
    if receipt.get("structural_filing_sha256") != hashlib.sha256(structural_path.read_bytes()).hexdigest():
        raise ValueError(f"{ticker}: structural source hash mismatch")
    if receipt.get("package_manifest_sha256") != hashlib.sha256(package_path.read_bytes()).hexdigest():
        raise ValueError(f"{ticker}: package manifest hash mismatch")
    entrypoint = package.get("entrypoint_local_path")
    package_entry = next((item for item in package.get("files", []) if item.get("local_path") == entrypoint), None)
    cache_root = Path(structural_root).parent / "batch-34-structural-cache-20260903" / "filings" / ticker
    html_path = next(cache_root.glob(f"**/{entrypoint}"), None) if entrypoint else None
    if not package_entry or html_path is None:
        raise ValueError(f"{ticker}: primary source HTML is unavailable for runtime verification")
    html_sha = hashlib.sha256(html_path.read_bytes()).hexdigest()
    if html_sha != package_entry.get("sha256"):
        raise ValueError(f"{ticker}: primary source HTML hash mismatch")
    cited = (CAPITAL_EVIDENCE.get(ticker) or BRO_PREFERRED_ABSENCE) if ticker in {"USB", "BRO"} else None
    if cited and (entrypoint != cited.get("document") or html_sha != cited.get("document_sha256")):
        raise ValueError(f"{ticker}: runtime source HTML is not the cited evidence document")
    return {
        "source_kind": "runtime_verified_structural_source_receipt",
        "receipt": str(receipt_path),
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "structural_filing_sha256": receipt["structural_filing_sha256"],
        "package_manifest_sha256": receipt["package_manifest_sha256"],
        "primary_document": entrypoint,
        "primary_document_sha256": html_sha,
        "accession": filing["accession"],
        "filed": filing["filed"],
        "form": filing["form"],
        "period_end": filing["report_date"],
        "verified": True,
    }


def _versioned(initial: dict, ticker: str, *, runtime_source: dict | None = None, acquisition_trace: dict | None = None) -> dict:
    value = deepcopy(initial)
    repair, release = RECOVERY_PLAN[ticker]
    value["model_version"] = BATCH_34_RECOVERY_VERSION
    promoted = ticker in RECOVERED_PASS_TICKERS
    repair_status = "implemented" if ticker in IMPLEMENTED_REPAIRS else "assessed_pending"
    value["availability_type"] = "available" if promoted else "conditional_estimate"
    if promoted:
        scenario = value["scenario_range"]
        value["history_reliability"] = assess_reliability(
            accounting_low=scenario["base"],
            accounting_base=scenario["base"],
            accounting_high=scenario["base"],
            scenario_low=scenario["low"],
            scenario_base=scenario["base"],
            scenario_high=scenario["high"],
            model_cap="High",
            source_cap="High",
            reasons=(),
        ).as_dict()
    if promoted:
        value["warning"] = f"One recovery attempt completed; source-bounded Pass. Practical repair implemented: {repair}."
    elif repair_status == "implemented":
        value["warning"] = f"One recovery attempt completed; Conditional Low retained after implementing: {repair}."
    else:
        value["warning"] = f"One recovery assessment completed; Conditional Low retained. Pending repair: {repair}."
    if acquisition_trace:
        value["warning"] += " Brown & Brown's acquisition/reinvestment program remains a material unbounded-to-date dependency; the residual-income baseline is not a cash-FCFF reinvestment bridge."
    recovery_reason_codes = () if promoted else ("SPECIALIST_MODEL_UNCERTAINTY", "RECOVERY_RELEASE_CONDITION_OPEN")
    value["governed_assumptions"] = {
        **value["governed_assumptions"],
        "recovery_attempts": RECOVERY_ATTEMPT,
        "recovery_repair_tested": repair,
        "recovery_repair_status": repair_status,
        "recovery_release_condition": release,
        "recovery_outcome": "pass" if promoted else "conditional_numeric_low",
        "recovery_reason_codes": recovery_reason_codes,
        **({"recovery_capital_evidence": CAPITAL_EVIDENCE[ticker]} if ticker in CAPITAL_EVIDENCE else {}),
        **({"runtime_source_verification": runtime_source} if runtime_source else {}),
        **({"acquisition_reinvestment_evidence": acquisition_trace} if acquisition_trace else {}),
    }
    value["source_ledger"] = {
        **value["source_ledger"],
        "recovery_attempt": {
            "attempt_number": RECOVERY_ATTEMPT,
            "initial_model_version": BATCH_34_HISTORY_VERSION,
            "repair_tested": repair,
            "repair_status": repair_status,
            "release_condition": release,
            "initial_availability_type": initial["availability_type"],
            "recovery_outcome": "pass" if promoted else "conditional_numeric_low",
            "reason_codes": recovery_reason_codes,
            "market_price_used": False,
            "analyst_target_used": False,
            **({"capital_evidence": CAPITAL_EVIDENCE[ticker]} if ticker in CAPITAL_EVIDENCE else {}),
            **({"runtime_source_verification": runtime_source} if runtime_source else {}),
            **({"acquisition_reinvestment_evidence": acquisition_trace} if acquisition_trace else {}),
        },
    }
    value["baseline"] = {**value["baseline"], "method_version": BATCH_34_RECOVERY_VERSION, "availability_type": "available" if promoted else "conditional", "confidence": value["history_reliability"]["label"], "confidence_reasons": list(value["history_reliability"]["reasons"]), "warnings": [value["warning"], release]}
    return value


def build_batch_34_recovery_result(*, ticker: str, source_root: Path, structural_root: Path, event_root: Path | None = None) -> dict:
    if ticker not in BATCH_34_TICKERS:
        raise ValueError(ticker)
    initial = build_batch_34_history_result(ticker=ticker, source_root=source_root, structural_root=structural_root, event_root=event_root)
    if ticker == "BRO":
        initial = _reprice_with_claim(initial, ticker, (0., 0., 0.), "reported_preferred_absence", (BRO_PREFERRED_ABSENCE,), beginning_claim_range=(0., 0., 0.))
    elif ticker in EXACT_PREFERRED:
        sources = _dimensional_preferred_sources(structural_root, ticker)
        spec = EXACT_PREFERRED[ticker]
        beginning_values = BEGINNING_PREFERRED_VALUES.get(ticker)
        beginning_sources = _dimensional_preferred_sources(
            structural_root,
            ticker,
            period_end="2025-12-31",
            values=beginning_values,
        ) if beginning_values else ()
        sources = (*sources, *beginning_sources)
        event_sources = tuple(initial["source_ledger"].get("event_sources", []))
        event_rows = tuple(row for row in event_sources if row.get("accession") == "0001193125-26-346938")
        sources = (*sources, *event_rows)
        beginning_claim = None
        if beginning_values:
            beginning_claim = (sum(beginning_values),) * 3
        if ticker == "STT":
            # The post-quarter Series L issuance brought approximately $495M
            # of net proceeds. Add those proceeds to current total equity while
            # separately deducting the $500M liquidation claim below; otherwise
            # common equity is understated by the issuance proceeds.
            initial = deepcopy(initial)
            initial["reported_inputs"]["ending_total_equity"] = float(initial["reported_inputs"]["ending_total_equity"]) + 495_000_000.0
            initial["governed_assumptions"]["ending_common_equity"] = float(initial["governed_assumptions"]["ending_common_equity"]) + 495_000_000.0
            initial["source_ledger"]["equity_model_context"] = [*initial["source_ledger"].get("equity_model_context", []), {"source_kind": "derived_event_equity_proceeds", "accession": "0001193125-26-346938", "period_end": "2026-08-14", "value": 495_000_000.0, "unit": "USD", "reported_vs_estimated": "reported_net_proceeds", "formula": "Series L approximately $495M net proceeds added to post-event equity"}]
        initial = _reprice_with_claim(initial, ticker, (spec["claim"],) * 3, "reported_dimensional_preferred_claim", sources, beginning_claim_range=beginning_claim)
    acquisition_trace = _bro_acquisition_trace(source_root) if ticker == "BRO" else None
    runtime_source = _runtime_source_receipt(structural_root, ticker, initial["source_ledger"]["controlling_filing"]) if ticker in {"USB", "BRO"} else None
    return _versioned(initial, ticker, runtime_source=runtime_source, acquisition_trace=acquisition_trace)


if RECOVERED_PASS_TICKERS | RECOVERED_CONDITIONAL_TICKERS | RECOVERED_WITHHELD_TICKERS != set(BATCH_34_TICKERS):
    raise RuntimeError("Batch 34 recovery policy mismatch")
