"""End-to-end U.S. filing normalization, routing, valuation, and publication gates."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Iterable, Mapping

from .assumptions import (
    ForecastEvidenceUnavailable,
    US_BASE,
    USMarketAssumptions,
    build_discount_rate,
    derive_forecast_assumptions,
    load_issuer_forecast_evidence,
)
from .classification import classify_issuer
from .bridge_policy import (
    BridgeAssessment,
    BridgeResolution,
    assess_bridge_materiality,
)
from .eligibility import model_eligibility
from .equity_models import build_equity_level_result
from .field_availability import FieldAvailability
from .evidence_policy import EvidenceAvailability
from .models import (
    earnings_power_value,
    fcff_dcf,
    one_way_sensitivities,
    scenario_set,
)
from .period_fallbacks import FallbackDecision
from .reliability import assess_reliability, lowest_label
from .xbrl import CompanyFactsNormalizer


def _forecast_quality_review(
    *,
    classification: dict[str, Any],
    assumptions: dict[str, Any],
    base: dict[str, Any],
    epv: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, dict[str, Any]] = {}
    segment_forecast = assumptions.get("segment_forecast")
    schedule = base.get("detail", {}).get("forecast_schedule", [])

    segment_required = bool(classification["requires_segment_forecast"])
    if segment_required and not segment_forecast:
        warnings.append(
            "A material secondary business lacks current segment detail; the "
            "valuation uses consolidated company history and is capped at Low reliability."
        )
    checks["segment_forecast_required"] = {
        "status": (
            "pass"
            if not segment_required or segment_forecast
            else "review_required"
        ),
        "value": segment_required,
    }

    if segment_forecast:
        reconciliations = segment_forecast["reconciliation"]
        reconciliation_passed = all(
            status == "pass" for status in reconciliations.values()
        )
        if not reconciliation_passed:
            errors.append("Segment evidence does not reconcile to consolidated facts.")
        checks["segment_reconciliation"] = {
            "status": "pass" if reconciliation_passed else "fail",
            "value": reconciliations,
        }
        max_archetype_weight = max(
            segment["evidence"]["growth_weights"]["archetype_anchor"]
            for segment in segment_forecast["segments"].values()
        )
        if max_archetype_weight > 0.25:
            errors.append("Archetype growth weight exceeds the 25% policy limit.")
        checks["archetype_growth_weight"] = {
            "status": "pass" if max_archetype_weight <= 0.25 else "fail",
            "value": max_archetype_weight,
            "limit": 0.25,
        }

    forecast_years = int(assumptions["forecast_years"])
    durable_horizon_passed = not segment_required or 7 <= forecast_years <= 10
    if not durable_horizon_passed:
        errors.append(
            "Durable multi-business issuers require a seven-to-ten-year fade horizon."
        )
    checks["forecast_horizon"] = {
        "status": "pass" if durable_horizon_passed else "fail",
        "value": forecast_years,
    }

    if schedule:
        last_year = schedule[-1]
        terminal_growth_landed = abs(
            float(last_year["revenue_growth"])
            - float(assumptions["terminal_growth"])
        ) < 1e-9
        if not terminal_growth_landed:
            errors.append("Forecast growth does not land on the terminal rate.")
        checks["terminal_growth_continuity"] = {
            "status": "pass" if terminal_growth_landed else "fail",
            "value": last_year["revenue_growth"],
            "target": assumptions["terminal_growth"],
        }
        revenue_cagr = (
            float(last_year["revenue"])
            / float(assumptions["starting_revenue"])
        ) ** (1 / forecast_years) - 1
        fcff_values = [float(row["fcff"]) for row in schedule]
        fcff_cagr = (
            (fcff_values[-1] / fcff_values[0]) ** (1 / (forecast_years - 1))
            - 1
            # Both endpoints must be positive: a positive/negative ratio raised to
            # a fractional power is a complex number (crashes the comparison below).
            if len(fcff_values) > 1 and fcff_values[0] > 0 and fcff_values[-1] > 0
            else None
        )
        inconsistent_cash_flow = (
            fcff_cagr is not None
            and revenue_cagr > 0.03
            and fcff_cagr < revenue_cagr - 0.05
        )
        if inconsistent_cash_flow:
            warnings.append(
                "Revenue and FCFF growth tell materially different forecast stories."
            )
        checks["revenue_fcff_consistency"] = {
            "status": "review_required" if inconsistent_cash_flow else "pass",
            "revenue_cagr": revenue_cagr,
            "fcff_cagr": fcff_cagr,
        }

    base_value = base.get("intrinsic_value_per_share")
    epv_value = epv.get("intrinsic_value_per_share")
    dispersion = (
        abs(float(base_value) - float(epv_value)) / abs(float(base_value))
        if base_value not in {None, 0} and epv_value is not None
        else None
    )
    if dispersion is not None and dispersion > 0.40:
        warnings.append(
            "DCF and EPV differ by more than 40%; the growth thesis requires review."
        )
    checks["dcf_epv_dispersion"] = {
        "status": "review_required" if dispersion is not None and dispersion > 0.40 else "pass",
        "value": dispersion,
        "review_threshold": 0.40,
    }

    if assumptions.get("consolidated_segment_fallback"):
        checks["segment_evidence_automation"] = {
            "status": "review_required",
            "value": "consolidated_company_history_fallback",
        }
    elif assumptions.get("forecast_evidence_status") != "automated_filing_extraction":
        warnings.append(
            "Segment evidence is governed filing-table transcription; automated filing-specific inline-XBRL extraction is not yet implemented."
        )
        checks["segment_evidence_automation"] = {
            "status": "review_required",
            "value": assumptions.get("forecast_evidence_status"),
        }
    else:
        checks["segment_evidence_automation"] = {
            "status": "pass",
            "value": assumptions.get("forecast_evidence_status"),
        }

    return {
        "policy_version": "US-FORECAST-QUALITY-1.0",
        "status": "withheld" if errors else "review_required" if warnings else "pass",
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def _segment_detail_can_fallback(error: ValueError) -> bool:
    return str(error) in {
        "Segment revenue does not reconcile to consolidated TTM revenue",
        "Segment gross profit and operating expense do not reconcile to TTM operating income",
        "Segment operating income does not reconcile to consolidated TTM operating income",
    }


def _publication_review(
    *,
    classification: dict[str, Any],
    financials: dict[str, Any],
    base: dict[str, Any],
    scenarios: dict[str, Any],
    forecast_quality: dict[str, Any],
    bridge_assessment: BridgeAssessment | None = None,
) -> dict[str, Any]:
    errors = [
        *base.get("errors", []),
        *forecast_quality.get("errors", []),
    ]
    warnings = [
        *financials.get("warnings", []),
        *base.get("warnings", []),
        *forecast_quality.get("warnings", []),
    ]
    if bridge_assessment is not None:
        if bridge_assessment.decision == "bounded_review":
            assert bridge_assessment.warning is not None
            warnings.append(bridge_assessment.warning)
        elif bridge_assessment.decision == "withheld":
            errors.append(_bridge_withheld_error(bridge_assessment))
    if classification["classification_confidence"] < 0.8:
        warnings.append(
            "Classification confidence is below 0.80; the governed model remains "
            "reviewable but reliability is capped at Low."
        )
    annual_count = len(financials["annual"])
    if annual_count < 3:
        errors.append("Fewer than three annual periods were normalized.")
    if annual_count < 5:
        warnings.append("Fewer than five annual periods limits cycle evidence.")
    scenario_values = [
        scenario["fcff_dcf"].get("intrinsic_value_per_share")
        for scenario in scenarios.values()
        if scenario["fcff_dcf"].get("intrinsic_value_per_share") is not None
    ]
    if len(scenario_values) != 3:
        errors.append("All three standard valuation scenarios must complete.")
    base_value = base.get("intrinsic_value_per_share")
    if base_value is not None and base_value <= 0:
        errors.append(
            "Non-positive DCF intrinsic value; FCFF does not apply to this issuer "
            "(typically unprofitable or pre-FCFF high-growth). Withheld pending a "
            "growth-appropriate model."
        )

    if errors:
        state = "withheld"
        grade = "insufficient"
    else:
        # Basic-share and narrow-NWC proxies deliberately prevent a high grade
        # until filing-specific dilution and broader accrual mapping are added.
        state = "review_required"
        grade = "medium"
    return {
        "publication_state": state,
        "confidence_grade": grade,
        "errors": errors,
        "warnings": list(dict.fromkeys(warnings)),
        "price_dependent_inputs_used": False,
        "prohibited_output_check": {
            "current_price": False,
            "upside_downside": False,
            "buy_hold_sell": False,
            "trading_multiples": False,
        },
    }


def _bridge_withheld_error(assessment: BridgeAssessment) -> str:
    reason_codes = list(assessment.reason_codes)
    if (
        assessment.spread_ratio is not None
        and assessment.spread_ratio > assessment.spread_limit
    ):
        reason_codes.append("JOINT_INTRINSIC_VALUE_SPREAD_EXCEEDS_LIMIT")
    stable_reasons = ",".join(sorted(set(reason_codes))) or "BRIDGE_POLICY_WITHHELD"
    bounded_fields = ",".join(assessment.bounded_fields) or "none"
    return (
        "Enterprise-to-equity bridge is withheld: "
        f"reason_codes={stable_reasons}; "
        f"spread_ratio={assessment.spread_ratio}; "
        f"spread_limit={assessment.spread_limit}; "
        f"bounded_fields={bounded_fields}."
    )


def _append_bridge_warning(model: dict[str, Any], warning: str) -> None:
    warnings = model.setdefault("warnings", [])
    if warning not in warnings:
        warnings.append(warning)


def _apply_bridge_publication_ceiling(
    *,
    assessment: BridgeAssessment,
    base: dict[str, Any],
    epv: dict[str, Any],
    scenarios: dict[str, Any],
    sensitivities: list[dict[str, Any]],
) -> None:
    if assessment.decision == "complete":
        return

    models = [base, epv]
    scenario_models = [
        scenario["fcff_dcf"] for scenario in scenarios.values()
    ]
    if assessment.decision == "bounded_review":
        assert assessment.warning is not None
        for model in [*models, *scenario_models]:
            if model.get("publication_state") != "withheld":
                model["publication_state"] = "review_required"
            _append_bridge_warning(model, assessment.warning)
        for row in sensitivities:
            if row.get("publication_state") != "withheld":
                row["publication_state"] = "review_required"
        return

    for model in [*models, *scenario_models]:
        model["publication_state"] = "withheld"
    for row in sensitivities:
        row["publication_state"] = "withheld"


def _store_bridge_assessment(
    *,
    balance_sheet: dict[str, Any],
    resolution: BridgeResolution,
    enterprise_value: float | None,
) -> BridgeAssessment:
    assessment = assess_bridge_materiality(
        resolution,
        enterprise_value=enterprise_value,
    )
    serialized = assessment.as_dict()
    serialized.pop("accounting_impact_ratio")
    serialized.pop("reliability_cap")
    balance_sheet["bridge_uncertainty"] = serialized
    balance_sheet["bridge_usable"] = assessment.usable
    balance_sheet["bridge_decision"] = assessment.decision
    return assessment


def _withheld_segment_evidence_result(
    *,
    classification: dict[str, Any],
    financials: dict[str, Any],
    discount_rate: dict[str, Any],
    valuation_date: str | None,
    source_manifest: dict[str, Any] | None,
    error: ForecastEvidenceUnavailable,
) -> dict[str, Any]:
    message = str(error)
    withheld_model = {
        "model": "fcff_dcf",
        "output_type": "intrinsic_value_per_share",
        "currency": "USD",
        "intrinsic_value_per_share": None,
        "publication_state": "withheld",
        "errors": [message],
        "warnings": [],
    }
    return {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "valuation_date": valuation_date or date.today().isoformat(),
        "market": "US",
        "currency": "USD",
        "issuer": {
            key: classification[key]
            for key in (
                "cik",
                "ticker",
                "issuer_name",
                "filing_regime",
                "accounting_standard",
                "sec_sic_code",
                "sec_sic_label",
                "finsight_sector",
                "primary_archetype",
                "secondary_archetypes",
                "classification_confidence",
                "mapping_version",
                "override_applied",
                "classification_reason",
                "source_accessions",
            )
        },
        "financial_period_end": financials["ttm"]["period_end"],
        "source_manifest": source_manifest or {
            "status": "not_supplied",
            "note": "The caller did not attach SEC cache hashes to this run.",
        },
        "model_policy": {
            "primary": classification["valuation_policy"]["primary_model"],
            "supporting": classification["valuation_policy"]["supporting_models"],
            "blend_models": False,
            "reason": classification["valuation_policy"].get(
                "model_policy_reason",
                "FCFF is the primary governed model; EPV is a separate no-growth support value.",
            ),
        },
        "financials": financials,
        "forecast_assumptions": {
            "forecast_evidence_status": "unavailable_for_normalized_period",
            "segment_forecast": None,
        },
        "discount_rate": discount_rate,
        "models": {
            "fcff_dcf": withheld_model,
            "epv": {
                **withheld_model,
                "model": "epv",
            },
        },
        "scenarios": {},
        "scenario_range": {
            "low": None,
            "base": None,
            "high": None,
            "label": "assumption range, not a statistical confidence interval",
        },
        "sensitivities": [],
        "forecast_quality": {
            "policy_version": "US-FORECAST-QUALITY-1.0",
            "status": "withheld",
            "errors": [message],
            "warnings": [],
            "checks": {
                "segment_evidence_as_of": {
                    "status": "fail",
                    "normalized_period_end": error.period_end,
                    "available_periods": error.available_periods,
                }
            },
        },
        "review": {
            "publication_state": "withheld",
            "confidence_grade": "insufficient",
            "errors": [message],
            "warnings": [],
            "price_dependent_inputs_used": False,
            "prohibited_output_check": {
                "current_price": False,
                "upside_downside": False,
                "buy_hold_sell": False,
                "trading_multiples": False,
            },
        },
        "methodology": {
            "forecast_policy": "docs/methodology/united-states/forecast-discount-validation-policy.md",
            "sector_framework": "docs/methodology/united-states/equity-valuation-engine-framework.md",
            "source_policy": "SEC Companyfacts, submissions and governed filing-specific reportable-segment tables; no exchange prices",
        },
    }


def _withheld_eligibility_result(
    *,
    classification: dict[str, Any],
    eligibility: dict[str, Any],
    valuation_date: str | None,
    source_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    model_name = eligibility["model"] or "unknown"
    message = f"Model eligibility rejected: {eligibility['reason']}"
    policy = classification.get("valuation_policy")
    policy = policy if isinstance(policy, dict) else {}
    issuer_keys = (
        "cik",
        "ticker",
        "issuer_name",
        "filing_regime",
        "accounting_standard",
        "sec_sic_code",
        "sec_sic_label",
        "finsight_sector",
        "primary_archetype",
        "secondary_archetypes",
        "classification_confidence",
        "mapping_version",
        "override_applied",
        "classification_reason",
        "source_accessions",
    )
    withheld_model = {
        "model": model_name,
        "output_type": "intrinsic_value_per_share",
        "currency": "USD",
        "intrinsic_value_per_share": None,
        "publication_state": "withheld",
        "errors": [message],
        "warnings": [],
    }
    return {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "valuation_date": valuation_date or date.today().isoformat(),
        "market": "US",
        "currency": "USD",
        "issuer": {key: classification.get(key) for key in issuer_keys},
        "financial_period_end": None,
        "source_manifest": source_manifest or {"status": "not_supplied"},
        "model_policy": {
            "primary": model_name,
            "supporting": policy.get("supporting_models", []),
            "blend_models": False,
            "reason": message,
        },
        "models": {model_name: withheld_model},
        "scenarios": {},
        "scenario_range": {
            "low": None,
            "base": None,
            "high": None,
            "label": "assumption range, not a statistical confidence interval",
        },
        "review": {
            "publication_state": "withheld",
            "confidence_grade": "insufficient",
            "errors": [message],
            "warnings": [],
            "price_dependent_inputs_used": False,
            "prohibited_output_check": {
                "current_price": False,
                "upside_downside": False,
                "buy_hold_sell": False,
                "trading_multiples": False,
            },
        },
    }


def _withheld_source_data_result(
    *,
    classification: dict[str, Any],
    model_name: str,
    valuation_date: str | None,
    source_manifest: dict[str, Any] | None,
    error: ValueError,
) -> dict[str, Any]:
    message = f"Source normalization unavailable: {error}"
    policy = classification.get("valuation_policy")
    policy = policy if isinstance(policy, dict) else {}
    withheld_model = {
        "model": model_name,
        "output_type": "intrinsic_value_per_share",
        "currency": "USD",
        "intrinsic_value_per_share": None,
        "publication_state": "withheld",
        "errors": [message],
        "warnings": [],
    }
    return {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "valuation_date": valuation_date or date.today().isoformat(),
        "market": "US",
        "currency": "USD",
        "issuer": {
            key: classification.get(key)
            for key in (
                "cik", "ticker", "issuer_name", "filing_regime",
                "accounting_standard", "sec_sic_code", "sec_sic_label",
                "finsight_sector", "primary_archetype", "secondary_archetypes",
                "classification_confidence", "mapping_version", "override_applied",
                "classification_reason", "source_accessions",
            )
        },
        "financial_period_end": None,
        "source_manifest": source_manifest or {"status": "not_supplied"},
        "model_policy": {
            "primary": model_name,
            "supporting": policy.get("supporting_models", []),
            "blend_models": False,
            "reason": message,
        },
        "models": {model_name: withheld_model},
        "scenarios": {},
        "scenario_range": {
            "low": None,
            "base": None,
            "high": None,
            "label": "assumption range, not a statistical confidence interval",
        },
        "review": {
            "publication_state": "withheld",
            "confidence_grade": "insufficient",
            "errors": [message],
            "warnings": [],
            "price_dependent_inputs_used": False,
            "prohibited_output_check": {
                "current_price": False,
                "upside_downside": False,
                "buy_hold_sell": False,
                "trading_multiples": False,
            },
        },
    }


def _attach_official_evidence_trace(
    result: dict[str, Any],
    official_evidence: tuple[EvidenceAvailability, ...],
    diagnostics: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if official_evidence:
        normalized_availability = (
            result.get("financials", {}).get("balance_sheet", {}).get("availability", {})
        )
        consumption = []
        for item in official_evidence:
            projected = item.availability
            consumed = normalized_availability.get(projected.field, {})
            consumed_source = (
                consumed.get("source_accession")
                if isinstance(consumed, Mapping)
                else getattr(consumed, "source_accession", None)
            )
            consumed_value = (
                consumed.get("value")
                if isinstance(consumed, Mapping)
                else getattr(consumed, "value", None)
            )
            consumption.append(
                {
                    "field": projected.field,
                    "selected_source_accession": projected.source_accession,
                    "selected_value": projected.value,
                    "consumed_source_accession": consumed_source,
                    "consumed_value": consumed_value,
                    "status": (
                        "consumed"
                        if consumed_source == projected.source_accession
                        and consumed_value == projected.value
                        else "unused_or_mismatched"
                    ),
                }
            )
        result["official_evidence"] = {
            "availability": [item.as_dict() for item in official_evidence],
            "consumption": consumption,
            "diagnostics": dict(diagnostics or {}),
            "private_only": True,
        }
    elif diagnostics:
        result["official_evidence"] = {
            "availability": [],
            "consumption": [],
            "diagnostics": dict(diagnostics),
            "private_only": True,
        }
    return result


def build_us_valuation(
    *,
    submissions: dict[str, Any],
    companyfacts: dict[str, Any],
    market_assumptions: USMarketAssumptions = US_BASE,
    valuation_date: str | None = None,
    source_manifest: dict[str, Any] | None = None,
    filing_evidence: Iterable[Mapping[str, Any]] | None = None,
    bridge_evidence: Iterable[FieldAvailability] = (),
    official_evidence: Iterable[EvidenceAvailability] = (),
    official_evidence_diagnostics: Mapping[str, Any] | None = None,
    sector_estimates: Mapping[str, FallbackDecision] | None = None,
    major_changes: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    official_evidence = tuple(official_evidence)
    if any(not isinstance(item, EvidenceAvailability) for item in official_evidence):
        raise ValueError("official_evidence must contain EvidenceAvailability values")
    bridge_evidence = tuple(bridge_evidence) + tuple(
        item.availability for item in official_evidence
    )
    if valuation_date:
        cutoff_submissions = deepcopy(submissions)
        recent = cutoff_submissions.get("filings", {}).get("recent", {})
        filing_dates = recent.get("filingDate", [])
        allowed_indexes = [
            index for index, filed in enumerate(filing_dates) if filed <= valuation_date
        ]
        for key, values in list(recent.items()):
            if isinstance(values, list) and len(values) == len(filing_dates):
                recent[key] = [values[index] for index in allowed_indexes]
        submissions = cutoff_submissions
    classification = classify_issuer(submissions)
    if str(companyfacts.get("cik", "")).zfill(10) != classification["cik"]:
        raise ValueError("SEC submissions and Companyfacts CIK values do not match")
    eligibility = model_eligibility(classification)
    if not eligibility["eligible"]:
        return _attach_official_evidence_trace(
            _withheld_eligibility_result(
                classification=classification,
                eligibility=eligibility,
                valuation_date=valuation_date,
                source_manifest=source_manifest,
            ),
            official_evidence,
            official_evidence_diagnostics,
        )
    # Dispatch archetypes FCFF cannot value (banks -> residual income, utilities
    # -> DDM) to the equity-level path before the enterprise FCFF normalization.
    if eligibility["model"] in ("residual_income", "ddm", "ffo"):
        return _attach_official_evidence_trace(
            build_equity_level_result(
                classification=classification,
                companyfacts=companyfacts,
                valuation_date=valuation_date,
                source_manifest=source_manifest,
                submissions=submissions,
            ),
            official_evidence,
            official_evidence_diagnostics,
        )
    recent_filings = submissions.get("filings", {}).get("recent", {})
    filing_records = [
        {
            key: values[index]
            for key, values in recent_filings.items()
            if isinstance(values, list) and index < len(values)
        }
        for index in range(len(recent_filings.get("accessionNumber", [])))
    ]
    try:
        financials = CompanyFactsNormalizer(
            companyfacts,
            fiscal_year_end=submissions.get("fiscalYearEnd"),
            as_of_date=valuation_date,
            filing_records=filing_records,
        ).normalize(
            annual_count=5,
            verified_zero_bridge_fields=classification[
                "verified_zero_bridge_fields"
            ],
            governed_bridge_fields=classification["governed_bridge_fields"],
            filing_evidence=filing_evidence,
            bridge_evidence=bridge_evidence,
            sector_estimates=sector_estimates,
            major_changes=major_changes,
        )
    except ValueError as error:
        if not str(error).startswith((
            "TTM flow input ",
            "Current TTM revenue is required",
        )):
            raise
        return _attach_official_evidence_trace(
            _withheld_source_data_result(
                classification=classification,
                model_name=str(eligibility["model"] or "unknown"),
                valuation_date=valuation_date,
                source_manifest=source_manifest,
                error=error,
            ),
            official_evidence,
            official_evidence_diagnostics,
        )
    policy = classification["valuation_policy"]
    discount_rate = build_discount_rate(
        policy=policy,
        tax_rate=financials["normalized"]["tax_rate"],
        market=market_assumptions,
    )
    balance_sheet = financials["balance_sheet"]
    bridge_resolution = BridgeResolution.from_dict(
        balance_sheet["bridge_precheck"]
    )
    balance_sheet.update(bridge_resolution.as_balance_sheet_fields())
    balance_sheet["fully_diluted_shares_proxy"] = (
        bridge_resolution.fully_diluted_shares
    )
    if not bridge_resolution.can_value:
        _store_bridge_assessment(
            balance_sheet=balance_sheet,
            resolution=bridge_resolution,
            enterprise_value=None,
        )
        blocking = ", ".join(bridge_resolution.blocking_fields)
        return _attach_official_evidence_trace(
            _withheld_segment_evidence_result(
                classification=classification,
                financials=financials,
                discount_rate=discount_rate,
                valuation_date=valuation_date,
                source_manifest=source_manifest,
                error=ForecastEvidenceUnavailable(
                    period_end=financials["ttm"]["period_end"],
                    available_periods=[],
                    reason=(
                        "Enterprise-to-equity bridge requires current filing evidence for "
                        + blocking
                    ),
                ),
            ),
            official_evidence,
            official_evidence_diagnostics,
        )
    _store_bridge_assessment(
        balance_sheet=balance_sheet,
        resolution=bridge_resolution,
        enterprise_value=None,
    )
    issuer_evidence = load_issuer_forecast_evidence(classification["cik"])
    used_consolidated_segment_fallback = bool(
        classification["requires_segment_forecast"] and not issuer_evidence
    )
    try:
        forecast_assumptions = derive_forecast_assumptions(
            financials,
            policy=policy,
            discount_rate=discount_rate,
            market=market_assumptions,
            issuer_evidence=issuer_evidence,
        )
    except ForecastEvidenceUnavailable as error:
        if error.reason is not None:
            return _attach_official_evidence_trace(
                _withheld_segment_evidence_result(
                    classification=classification,
                    financials=financials,
                    discount_rate=discount_rate,
                    valuation_date=valuation_date,
                    source_manifest=source_manifest,
                    error=error,
                ),
                official_evidence,
                official_evidence_diagnostics,
            )
        forecast_assumptions = derive_forecast_assumptions(
            financials,
            policy=policy,
            discount_rate=discount_rate,
            market=market_assumptions,
            issuer_evidence=None,
        )
        used_consolidated_segment_fallback = True
    except ValueError as error:
        if not issuer_evidence or not _segment_detail_can_fallback(error):
            raise
        forecast_assumptions = derive_forecast_assumptions(
            financials,
            policy=policy,
            discount_rate=discount_rate,
            market=market_assumptions,
            issuer_evidence=None,
        )
        used_consolidated_segment_fallback = True
    forecast_assumptions["consolidated_segment_fallback"] = (
        used_consolidated_segment_fallback
    )
    base = fcff_dcf(
        assumptions=forecast_assumptions,
        discount_rate=discount_rate,
        financials=financials,
    )
    bridge_assessment = _store_bridge_assessment(
        balance_sheet=balance_sheet,
        resolution=bridge_resolution,
        enterprise_value=base.get("enterprise_value"),
    )
    epv = earnings_power_value(
        assumptions=forecast_assumptions,
        discount_rate=discount_rate,
        financials=financials,
    )
    scenarios = scenario_set(
        assumptions=forecast_assumptions,
        discount_rate=discount_rate,
        financials=financials,
    )
    sensitivities = one_way_sensitivities(
        assumptions=forecast_assumptions,
        discount_rate=discount_rate,
        financials=financials,
    )
    _apply_bridge_publication_ceiling(
        assessment=bridge_assessment,
        base=base,
        epv=epv,
        scenarios=scenarios,
        sensitivities=sensitivities,
    )
    forecast_quality = _forecast_quality_review(
        classification=classification,
        assumptions=forecast_assumptions,
        base=base,
        epv=epv,
    )
    review = _publication_review(
        classification=classification,
        financials=financials,
        base=base,
        scenarios=scenarios,
        forecast_quality=forecast_quality,
        bridge_assessment=bridge_assessment,
    )
    scenario_values = [
        scenario["fcff_dcf"]["intrinsic_value_per_share"]
        for scenario in scenarios.values()
        if scenario["fcff_dcf"].get("intrinsic_value_per_share") is not None
    ]
    scenario_range = {
        "low": min(scenario_values) if scenario_values else None,
        "base": base.get("intrinsic_value_per_share"),
        "high": max(scenario_values) if scenario_values else None,
        "label": "assumption range, not a statistical confidence interval",
    }
    result = {
        "schema_version": "US-VALUATION-RESULT-1.0",
        "valuation_date": valuation_date or date.today().isoformat(),
        "market": "US",
        "currency": "USD",
        "issuer": {
            key: classification[key]
            for key in (
                "cik",
                "ticker",
                "issuer_name",
                "filing_regime",
                "accounting_standard",
                "sec_sic_code",
                "sec_sic_label",
                "finsight_sector",
                "primary_archetype",
                "secondary_archetypes",
                "classification_confidence",
                "mapping_version",
                "override_applied",
                "classification_reason",
                "source_accessions",
            )
        },
        "financial_period_end": financials["ttm"]["period_end"],
        "source_manifest": source_manifest or {
            "status": "not_supplied",
            "note": "The caller did not attach SEC cache hashes to this run.",
        },
        "model_policy": {
            "primary": policy["primary_model"],
            "supporting": policy["supporting_models"],
            "blend_models": False,
            "reason": policy.get(
                "model_policy_reason",
                "FCFF is the primary governed model; EPV is a separate no-growth support value.",
            ),
        },
        "financials": financials,
        "forecast_assumptions": forecast_assumptions,
        "discount_rate": discount_rate,
        "models": {
            "fcff_dcf": base,
            "epv": epv,
        },
        "scenarios": scenarios,
        "scenario_range": scenario_range,
        "sensitivities": sensitivities,
        "forecast_quality": forecast_quality,
        "review": review,
        "methodology": {
            "forecast_policy": "docs/methodology/united-states/forecast-discount-validation-policy.md",
            "sector_framework": "docs/methodology/united-states/equity-valuation-engine-framework.md",
            "source_policy": "SEC Companyfacts, submissions and governed filing-specific Products/Services tables; no exchange prices",
        },
    }
    _attach_official_evidence_trace(
        result,
        official_evidence,
        official_evidence_diagnostics,
    )
    if bridge_assessment.usable and all(
        isinstance(value, (int, float))
        for value in (
            scenario_range["low"],
            scenario_range["base"],
            scenario_range["high"],
        )
    ):
        if bridge_assessment.decision == "complete":
            bridge_low = bridge_midpoint = bridge_high = scenario_range["base"]
        else:
            assert bridge_assessment.intrinsic_value_range is not None
            bridge_low = bridge_assessment.intrinsic_value_range.low
            bridge_midpoint = bridge_assessment.intrinsic_value_range.midpoint
            bridge_high = bridge_assessment.intrinsic_value_range.high
        fallback_caps = [
            decision.get("reliability_cap")
            for decision in balance_sheet.get("fallback_decisions", {}).values()
            if isinstance(decision, Mapping)
            and decision.get("reliability_cap") in {"High", "Medium", "Low"}
        ]
        source_cap = lowest_label(
            bridge_assessment.reliability_cap,
            *fallback_caps,
        )
        model_reasons: list[str] = []
        model_caps = ["High"]
        if classification["classification_confidence"] < 0.8:
            model_caps.append("Low")
            model_reasons.append("LOW_CLASSIFICATION_CONFIDENCE")
        if used_consolidated_segment_fallback:
            model_caps.append("Low")
            model_reasons.append("CONSOLIDATED_SEGMENT_FALLBACK")
        if (
            forecast_assumptions.get("assumption_source_mix")
            == "reported_history_and_finsight_policy"
        ):
            model_caps.append("Low")
            model_reasons.append("INSUFFICIENT_COMPANY_HISTORY")
        result["reliability"] = assess_reliability(
            accounting_low=bridge_low,
            accounting_base=bridge_midpoint,
            accounting_high=bridge_high,
            scenario_low=scenario_range["low"],
            scenario_base=scenario_range["base"],
            scenario_high=scenario_range["high"],
            model_cap=lowest_label(*model_caps),
            source_cap=source_cap,
            reasons=tuple(
                dict.fromkeys([*bridge_assessment.reason_codes, *model_reasons])
            ),
        ).as_dict()
    return result
