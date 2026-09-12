"""Source gate and successor binder for WDC's issuer-balanced cyclical FCFF.

The WDC recipe is a two-issuer cyclical model (WDC plus STX).  It cannot be
refreshed from Companyfacts alone: the WDC continuation/discontinued-operation
scope and the exact current bridge come from structural filing facts.  This
module therefore validates the real cached packets and fails with a concrete
source gate when the cached structural facts do not carry issuer identity.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Mapping

from .calculation_recipe import evaluate_recipe
from .practical_models import CyclicalOperatingState, practical_cyclical_fcff_range
from .xbrl import CompanyFactsNormalizer, load_concept_config


SCHEMA = "FINSIGHT-CYCLICAL-FCFF-REFRESH-POLICY-1"
POLICY_VERSION = f"{SCHEMA}-WDC"
ROUTINE_EVENT_ITEMS = frozenset({"2.02", "9.01"})


class CyclicalRefreshError(ValueError):
    """A source, period, scope, or peer-evidence gate is not satisfied."""


def _iso(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise CyclicalRefreshError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise CyclicalRefreshError(f"{field} must be an ISO date") from exc


def _records(submissions: Mapping[str, Any]) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    return [{key: values[i] for key, values in recent.items() if isinstance(values, list) and i < len(values)} for i in range(len(accessions))]


def _select(records: list[dict[str, Any]], cutoff: str) -> dict[str, Any]:
    eligible = [row for row in records if row.get("form") in {"10-K", "10-Q"} and isinstance(row.get("accessionNumber"), str) and isinstance(row.get("reportDate"), str) and isinstance(row.get("filingDate"), str) and row["filingDate"] <= cutoff and row["reportDate"] <= cutoff]
    if not eligible:
        raise CyclicalRefreshError("no cutoff-eligible cyclical filing")
    return max(eligible, key=lambda row: (row["reportDate"], row["filingDate"], row["accessionNumber"]))


def compile_cyclical_policy(recipe: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    if recipe.get("ticker") != "WDC" or set(recipe.get("scenarios", {})) != {"bear", "base", "bull"}:
        raise ValueError("cyclical compiler currently supports WDC only")
    if {spec.get("engine") for spec in recipe["scenarios"].values()} != {"cyclical_fcff_quantile"}:
        raise ValueError("recipe is not the WDC cyclical family")
    return {
        "schema_version": SCHEMA,
        "version": POLICY_VERSION,
        "ticker": "WDC",
        "cik": str(registry_entry.get("cik", "")).zfill(10),
        "supported_engine": "cyclical_fcff_quantile",
        "execution_state": "compiled_source_validation_pending",
        "source_peers": [{"ticker":"STX","cik":"0001137789"}],
        "concept_config": load_concept_config(),
        "statement_required_fields": {"revenue":"flow","total_assets":"instant"},
        "peer_ticker": "STX",
        "peer_cik": "0001137789",
        "source_requirements": {
            "structural": True,
            "event_exhibits": True,
            "wdc_structural_filing": True,
            "stx_peer_companyfacts": True,
            "same_cutoff": True,
            "issuer_identity": True,
            "continuing_operation_scope": True,
        },
        "approved_policy": {
            "issuer_weighting": "equal issuer weight inside practical_cyclical_fcff_range",
            "terminal_horizon_years": 10,
            "peer_states_required": 3,
            "tax_states": "recipe scenario inputs",
            "other_claims": "source-reconciled only; no stale recipe claim amounts",
        },
        "unsupported_cases": [
            "WDC structural facts without fact-level CIK identity",
            "WDC discontinued-operation scope not reconciled from structural dimensions",
            "STX peer annual states not same-accession and same-cutoff",
            "non-routine corporate events requiring explicit review",
        ],
    }


def _validate_identity(packet: Mapping[str, Any], cik: str, ticker: str) -> None:
    submissions, companyfacts = packet.get("submissions"), packet.get("companyfacts")
    if not isinstance(submissions, Mapping) or not isinstance(companyfacts, Mapping):
        raise CyclicalRefreshError(f"{ticker} source packet is incomplete")
    expected = str(cik).zfill(10)
    if str(submissions.get("cik", "")).zfill(10) != expected or str(companyfacts.get("cik", "")).zfill(10) != expected:
        raise CyclicalRefreshError(f"{ticker} source packet CIK mismatch")


def _structural_identity(structural: Mapping[str, Any], *, cik: str, accession: str) -> None:
    facts = structural.get("facts", [])
    if structural.get("source_accession") != accession:
        raise CyclicalRefreshError("WDC structural accession mismatch")
    ids = {str(row.get("entity_identifier", "")).zfill(10) for row in facts if isinstance(row, Mapping)}
    if ids != {str(cik).zfill(10)}:
        raise CyclicalRefreshError("WDC structural facts lack exact issuer CIK identity")


def _qname_matches(row: Mapping[str, Any], local_name: str, *, family: str = "us-gaap") -> bool:
    qname = str(row.get("qname", ""))
    namespace = str(row.get("namespace", ""))
    if not qname.endswith(f":{local_name}"):
        return False
    return ("/dei/" in namespace or namespace.endswith("/dei")) if family == "dei" else ("/us-gaap/" in namespace or namespace.endswith("/us-gaap"))


def _fact(structural: Mapping[str, Any], *, local_name: str, period_end: str, accession: str, unit: str = "USD", period_start: str | None = None, dimensions: bool = False, family: str = "us-gaap") -> dict[str, Any]:
    rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("local_name") == local_name and _qname_matches(row, local_name, family=family) and row.get("source_accession") == accession and row.get("period_end") == period_end and row.get("period_start") == period_start and row.get("unit") == unit and (bool(row.get("dimensions")) == dimensions)]
    values = {float(row["value"]) for row in rows if isinstance(row.get("value"), (int, float)) and not isinstance(row.get("value"), bool)}
    if len(values) != 1:
        raise CyclicalRefreshError(f"WDC exact structural fact missing or conflicting: {local_name}/{period_end}")
    row = dict(rows[0]); row["value"] = values.pop(); return row


def _sandisk_dimensions(row: Mapping[str, Any]) -> bool:
    normalized = {(str(axis).split(":")[-1], str(member).split(":")[-1]) for axis, member in (row.get("dimensions") or []) if isinstance(axis, str) and isinstance(member, str)}
    return normalized == {("DisposalGroupClassificationAxis", "DiscontinuedOperationsDisposedOfByMeansOtherThanSaleSpinoffMember"), ("IncomeStatementBalanceSheetAndAdditionalDisclosuresByDisposalGroupsIncludingDiscontinuedOperationsAxis", "SandiskSemiconductorCo.Ltd.Member")}


def _discontinued(structural: Mapping[str, Any], *, local_name: str, period_end: str, period_start: str, accession: str) -> float:
    rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("local_name") == local_name and _qname_matches(row, local_name) and row.get("source_accession") == accession and row.get("period_end") == period_end and row.get("period_start") == period_start and row.get("unit") == "USD" and _sandisk_dimensions(row)]
    values = {float(row["value"]) for row in rows if isinstance(row.get("value"), (int, float)) and not isinstance(row.get("value"), bool)}
    if len(values) != 1:
        raise CyclicalRefreshError(f"WDC discontinued-operation scope missing: {local_name}/{period_end}")
    return values.pop()


def _discontinued_optional(structural: Mapping[str, Any], *, local_name: str, period_end: str, period_start: str, accession: str) -> tuple[float, bool]:
    rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("local_name") == local_name and _qname_matches(row, local_name) and row.get("source_accession") == accession and row.get("period_end") == period_end and row.get("period_start") == period_start and row.get("unit") == "USD" and _sandisk_dimensions(row)]
    if not rows:
        return 0.0, False
    values = {float(row["value"]) for row in rows if isinstance(row.get("value"), (int, float)) and not isinstance(row.get("value"), bool)}
    if len(values) != 1:
        raise CyclicalRefreshError(f"WDC discontinued-operation scope conflicting: {local_name}/{period_end}")
    return values.pop(), True


def _wdc_annual_periods(structural: Mapping[str, Any], *, accession: str) -> list[tuple[str, str]]:
    candidates = {}
    for row in structural.get("facts", []):
        if not isinstance(row, Mapping) or row.get("local_name") != "RevenueFromContractWithCustomerExcludingAssessedTax" or not _qname_matches(row, "RevenueFromContractWithCustomerExcludingAssessedTax") or row.get("source_accession") != accession or row.get("unit") != "USD" or row.get("dimensions") or not row.get("period_start") or not row.get("period_end"):
            continue
        candidates[(row["period_end"], row["period_start"])] = True
    required = ("OperatingIncomeLoss", "PaymentsToAcquirePropertyPlantAndEquipment")
    usable = []
    for end, start in candidates:
        if all(any(isinstance(row, Mapping) and row.get("local_name") == name and _qname_matches(row, name) and row.get("source_accession") == accession and row.get("unit") == "USD" and row.get("period_end") == end and row.get("period_start") == start and not row.get("dimensions") for row in structural.get("facts", [])) for name in required) and any(any(isinstance(row, Mapping) and row.get("local_name") == name and _qname_matches(row, name) and row.get("source_accession") == accession and row.get("unit") == "USD" and row.get("period_end") == end and row.get("period_start") == start and not row.get("dimensions") for row in structural.get("facts", [])) for name in ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization")):
            usable.append((end, start))
    usable.sort()
    if len(usable) < 3:
        raise CyclicalRefreshError("WDC has fewer than three exact annual continuing-operation states")
    return usable[-3:]


def _duration_pair(structural: Mapping[str, Any], *, local_name: str, accession: str, current_end: str) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("local_name") == local_name and _qname_matches(row, local_name) and row.get("source_accession") == accession and row.get("unit") == "USD" and not row.get("dimensions") and isinstance(row.get("period_start"), str) and isinstance(row.get("period_end"), str)]
    current = [row for row in rows if row.get("period_end") == current_end]
    if not current:
        raise CyclicalRefreshError(f"WDC interim current YTD fact missing: {local_name}")
    current = max(current, key=lambda row: (row["period_start"], row.get("filed_date", "")))
    duration = (date.fromisoformat(current["period_end"]) - date.fromisoformat(current["period_start"])).days
    prior = [row for row in rows if row.get("period_end") < current_end and abs((date.fromisoformat(row["period_end"]) - date.fromisoformat(row["period_start"])).days - duration) <= 8]
    if not prior:
        raise CyclicalRefreshError(f"WDC interim prior comparable YTD fact missing: {local_name}")
    return dict(current), dict(max(prior, key=lambda row: row["period_end"]))


def _ttm_structural_state(*, current_structural: Mapping[str, Any], annual_structural: Mapping[str, Any], current_accession: str, annual_accession: str, current_end: str) -> tuple[CyclicalOperatingState, dict[str, Any]]:
    annual_periods = _wdc_annual_periods(annual_structural, accession=annual_accession)
    annual_end, annual_start = annual_periods[-1]
    values: dict[str, float] = {}
    scope: dict[str, Any] = {"annual_period": annual_end, "current_period": current_end, "fields": {}}
    for local_name in ("RevenueFromContractWithCustomerExcludingAssessedTax", "OperatingIncomeLoss", "DepreciationDepletionAndAmortization", "PaymentsToAcquirePropertyPlantAndEquipment"):
        annual_name = local_name
        try:
            annual_value = _fact(annual_structural, local_name=annual_name, period_end=annual_end, accession=annual_accession, period_start=annual_start)["value"]
        except CyclicalRefreshError:
            if local_name != "DepreciationDepletionAndAmortization":
                raise
            annual_name = "DepreciationAndAmortization"
            annual_value = _fact(annual_structural, local_name=annual_name, period_end=annual_end, accession=annual_accession, period_start=annual_start)["value"]
        cur, prior = _duration_pair(current_structural, local_name=local_name, accession=current_accession, current_end=current_end)
        cur_value, prior_value = float(cur["value"]), float(prior["value"])
        if local_name in {"DepreciationDepletionAndAmortization", "PaymentsToAcquirePropertyPlantAndEquipment"}:
            for packet, row, source_acc in ((annual_structural, annual_end, annual_accession), (current_structural, cur["period_end"], current_accession), (current_structural, prior["period_end"], current_accession)):
                start = annual_start if source_acc == annual_accession else (cur["period_start"] if row == cur["period_end"] else prior["period_start"])
                excluded, found = _discontinued_optional(packet, local_name=("DepreciationAndAmortizationDiscontinuedOperations" if local_name == "DepreciationDepletionAndAmortization" else "PaymentsToAcquirePropertyPlantAndEquipment"), period_end=row, period_start=start, accession=source_acc)
                if source_acc == annual_accession: annual_value -= excluded
                elif row == cur["period_end"]: cur_value -= excluded
                else: prior_value -= excluded
                scope["fields"].setdefault(local_name, []).append({"period_end": row, "excluded": excluded, "found": found})
        values[local_name] = annual_value + cur_value - prior_value
    revenue = values["RevenueFromContractWithCustomerExcludingAssessedTax"]
    if min(revenue, values["DepreciationDepletionAndAmortization"], values["PaymentsToAcquirePropertyPlantAndEquipment"]) <= 0:
        raise CyclicalRefreshError("WDC interim continuing-operation TTM metrics are nonpositive")
    return CyclicalOperatingState("WDC", current_end, revenue, values["OperatingIncomeLoss"] / revenue, values["DepreciationDepletionAndAmortization"] / revenue, values["PaymentsToAcquirePropertyPlantAndEquipment"] / revenue), scope


def _annual_peer_states(companyfacts: Mapping[str, Any], *, accession: str, cutoff: str) -> list[CyclicalOperatingState]:
    concepts = {"revenue": "RevenueFromContractWithCustomerExcludingAssessedTax", "ebit": "OperatingIncomeLoss", "da": "DepreciationDepletionAndAmortization", "capex": "PaymentsToAcquirePropertyPlantAndEquipment"}
    rows: dict[str, dict[str, Mapping[str, Any]]] = {}
    for key, concept in concepts.items():
        units = companyfacts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", [])
        selected: dict[str, Mapping[str, Any]] = {}
        for row in units:
            if row.get("form") not in {"10-K", "10-K/A"} or row.get("filed", "") > cutoff or not row.get("start") or not row.get("end"):
                continue
            if 300 <= (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days <= 380:
                prior = selected.get(row["end"])
                if prior is None or (row.get("filed", ""), row.get("accn", "")) > (prior.get("filed", ""), prior.get("accn", "")):
                    selected[row["end"]] = row
        rows[key] = selected
    ends = sorted(set.intersection(*(set(item) for item in rows.values())))[-10:]
    if len(ends) < 3:
        raise CyclicalRefreshError("STX peer annual cycle states are incomplete")
    ends = ends[-10:]
    for end in ends:
        if len({rows[key][end].get("accn") for key in concepts}) != 1:
            raise CyclicalRefreshError(f"STX peer cycle metrics do not share one accession at {end}")
    return [CyclicalOperatingState("STX", end, float(rows["revenue"][end]["val"]), float(rows["ebit"][end]["val"]) / float(rows["revenue"][end]["val"]), float(rows["da"][end]["val"]) / float(rows["revenue"][end]["val"]), float(rows["capex"][end]["val"]) / float(rows["revenue"][end]["val"])) for end in ends]


def bind_and_evaluate_cyclical_recipe(policy: Mapping[str, Any], recipe: Mapping[str, Any], packet: Mapping[str, Any], *, peer_packet: Mapping[str, Any] | None, structural_packet: Mapping[str, Any] | None, cutoff: str) -> dict[str, Any]:
    cutoff = _iso(cutoff, "cutoff")
    _validate_identity(packet, str(policy.get("cik", "")), "WDC")
    if peer_packet is None:
        raise CyclicalRefreshError("STX peer source packet is required")
    _validate_identity(peer_packet, str(policy.get("peer_cik", "")), "STX")
    wdc_records = _records(packet["submissions"])
    stx_records = _records(peer_packet["submissions"])
    wdc = packet.get("_selected_controlling_filing") or _select(wdc_records, cutoff)
    stx = peer_packet.get("_selected_controlling_filing") or _select(stx_records, cutoff)
    if structural_packet is None:
        raise CyclicalRefreshError("WDC structural filing package is required for continuing-operation scope and bridge")
    _structural_identity(structural_packet, cik=str(policy.get("cik", "")), accession=wdc["accessionNumber"])
    accession = wdc["accessionNumber"]
    structural = structural_packet
    current_period = wdc["reportDate"]
    # Annual filings expose three continuing-operation states.  An interim
    # filing instead uses annual FY + current YTD - comparable prior YTD.
    wdc_states = []
    scope_trace = []
    interim_scope = None
    if wdc.get("form") in {"10-Q", "10-Q/A"}:
        annual_structural = packet.get("annual_structural_filing")
        annual_filing = packet.get("latest_annual_filing") or {}
        if not isinstance(annual_structural, Mapping) or annual_structural.get("source_accession") != annual_filing.get("accessionNumber"):
            raise CyclicalRefreshError("WDC interim refresh requires the matching annual structural package")
        _structural_identity(annual_structural, cik=str(policy.get("cik", "")), accession=annual_filing["accessionNumber"])
        current_state, interim_scope = _ttm_structural_state(current_structural=structural, annual_structural=annual_structural, current_accession=accession, annual_accession=annual_filing["accessionNumber"], current_end=current_period)
        annual_periods = _wdc_annual_periods(annual_structural, accession=annual_filing["accessionNumber"])
        for end, start in annual_periods[-2:]:
            rev = _fact(annual_structural, local_name="RevenueFromContractWithCustomerExcludingAssessedTax", period_end=end, accession=annual_filing["accessionNumber"], period_start=start)["value"]
            try:
                annual_da = _fact(annual_structural, local_name="DepreciationDepletionAndAmortization", period_end=end, accession=annual_filing["accessionNumber"], period_start=start)["value"]
            except CyclicalRefreshError:
                annual_da = _fact(annual_structural, local_name="DepreciationAndAmortization", period_end=end, accession=annual_filing["accessionNumber"], period_start=start)["value"]
            wdc_states.append(CyclicalOperatingState("WDC", end, rev, _fact(annual_structural, local_name="OperatingIncomeLoss", period_end=end, accession=annual_filing["accessionNumber"], period_start=start)["value"] / rev, annual_da / rev, _fact(annual_structural, local_name="PaymentsToAcquirePropertyPlantAndEquipment", period_end=end, accession=annual_filing["accessionNumber"], period_start=start)["value"] / rev))
        wdc_states.append(current_state)
    else:
        annual_periods = _wdc_annual_periods(structural, accession=accession)
    for end, start in (() if wdc.get("form") in {"10-Q", "10-Q/A"} else annual_periods):
        revenue = _fact(structural, local_name="RevenueFromContractWithCustomerExcludingAssessedTax", period_end=end, accession=accession, period_start=start)["value"]
        ebit = _fact(structural, local_name="OperatingIncomeLoss", period_end=end, accession=accession, period_start=start)["value"]
        try:
            da = _fact(structural, local_name="DepreciationDepletionAndAmortization", period_end=end, accession=accession, period_start=start)["value"]
        except CyclicalRefreshError:
            da = _fact(structural, local_name="DepreciationAndAmortization", period_end=end, accession=accession, period_start=start)["value"]
        capex = _fact(structural, local_name="PaymentsToAcquirePropertyPlantAndEquipment", period_end=end, accession=accession, period_start=start)["value"]
        da_excluded, da_found = _discontinued_optional(structural, local_name="DepreciationAndAmortizationDiscontinuedOperations", period_end=end, period_start=start, accession=accession)
        capex_excluded, capex_found = _discontinued_optional(structural, local_name="PaymentsToAcquirePropertyPlantAndEquipment", period_end=end, period_start=start, accession=accession)
        da -= da_excluded
        capex -= capex_excluded
        scope_trace.append({"period_end": end, "period_start": start, "discontinued_da_excluded": da_excluded, "discontinued_da_fact_found": da_found, "discontinued_capex_excluded": capex_excluded, "discontinued_capex_fact_found": capex_found})
        if min(revenue, da, capex) <= 0:
            raise CyclicalRefreshError(f"WDC continuing metric is nonpositive at {end}")
        wdc_states.append(CyclicalOperatingState("WDC", end, revenue, ebit / revenue, da / revenue, capex / revenue))
    current = wdc_states[-1]
    peer_accession = stx["accessionNumber"]
    peer_states = _annual_peer_states(peer_packet["companyfacts"], accession=peer_accession, cutoff=cutoff)
    normalizer = CompanyFactsNormalizer(packet["companyfacts"], fiscal_year_end=packet["submissions"].get("fiscalYearEnd"), as_of_date=cutoff, filing_records=wdc_records, concept_config=load_concept_config())
    # Current and prior operating-NWC snapshots are source facts, not recipe
    # carry-forwards.  A missing account blocks rather than becoming zero.
    missing_nwc_components: list[str] = []
    def instant(field: str, end: str) -> float:
        fact = normalizer.instant(field, end=end)
        if fact is None:
            if field == "deferred_revenue_current":
                missing_nwc_components.append(f"{field}:{end}")
                return 0.0
            raise CyclicalRefreshError(f"WDC current operating-NWC fact missing: {field}/{end}")
        return float(fact.value)
    prior_end = wdc_states[-2].period_end
    nwc_current = instant("accounts_receivable", current_period) + instant("inventory", current_period) - instant("accounts_payable", current_period) - instant("deferred_revenue_current", current_period)
    nwc_prior = instant("accounts_receivable", prior_end) + instant("inventory", prior_end) - instant("accounts_payable", prior_end) - instant("deferred_revenue_current", prior_end)
    nwc_ratio = (nwc_current - nwc_prior) / current.revenue
    cash = _fact(structural, local_name="CashAndCashEquivalentsAtCarryingValue", period_end=current_period, accession=accession)["value"]
    debt = _fact(structural, local_name="LongTermDebt", period_end=current_period, accession=accession)["value"]
    cover_rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("local_name") == "EntityCommonStockSharesOutstanding" and _qname_matches(row, "EntityCommonStockSharesOutstanding", family="dei") and row.get("source_accession") == accession and str(row.get("entity_identifier", "")).zfill(10) == str(policy.get("cik", "")).zfill(10) and row.get("unit") == "xbrli:shares" and not row.get("dimensions") and isinstance(row.get("period_end"), str) and row["period_end"] <= cutoff]
    if not cover_rows:
        raise CyclicalRefreshError("WDC current cover-page shares are missing")
    cover_period = max(row["period_end"] for row in cover_rows)
    cover_values = {float(row["value"]) for row in cover_rows if row["period_end"] == cover_period and isinstance(row.get("value"), (int, float))}
    if len(cover_values) != 1:
        raise CyclicalRefreshError("WDC current cover-page shares conflict")
    cover = cover_values.pop()
    def latest_duration(name: str) -> float:
        rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("local_name") == name and _qname_matches(row, name) and row.get("source_accession") == accession and str(row.get("entity_identifier", "")).zfill(10) == str(policy.get("cik", "")).zfill(10) and row.get("period_end") == current_period and row.get("unit") == "xbrli:shares" and isinstance(row.get("period_start"), str) and not row.get("dimensions")]
        if not rows:
            raise CyclicalRefreshError(f"WDC current share fact missing: {name}")
        latest_start = max(row["period_start"] for row in rows)
        values = {float(row["value"]) for row in rows if row["period_start"] == latest_start and isinstance(row.get("value"), (int, float))}
        if len(values) != 1:
            raise CyclicalRefreshError(f"WDC current share fact conflicts: {name}")
        return values.pop()
    weighted = latest_duration("WeightedAverageNumberOfDilutedSharesOutstanding")
    incremental = latest_duration("IncrementalCommonSharesAttributableToShareBasedPaymentArrangements")
    nonvested_rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("local_name") == "ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsNonvestedNumber" and _qname_matches(row, "ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsNonvestedNumber") and row.get("source_accession") == accession and row.get("period_end") == current_period and row.get("unit") == "xbrli:shares" and row.get("dimensions") and any(str(member).split(":")[-1] == "RestrictedStockUnitsAndPerformanceShareUnitsMember" for _, member in row.get("dimensions", []))]
    if not nonvested_rows or len({float(row["value"]) for row in nonvested_rows if isinstance(row.get("value"), (int, float))}) != 1:
        raise CyclicalRefreshError("WDC current nonvested-award share count is missing")
    nonvested = float(nonvested_rows[0]["value"])
    # The approved scenario ordering is conservative bear = highest dilution,
    # base = reported weighted average, bull = lower cover-plus-current-awards.
    shares = {"bear": cover + incremental, "base": weighted, "bull": cover + nonvested}
    # Only explicit zero claim facts are accepted for this enterprise bridge.
    preferred = _fact(structural, local_name="TemporaryEquityCarryingAmountAttributableToParent", period_end=current_period, accession=accession)["value"]
    nci_claim_rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("source_accession") == accession and str(row.get("entity_identifier", "")).zfill(10) == str(policy.get("cik", "")).zfill(10) and row.get("period_end") == current_period and row.get("unit") == "USD" and not row.get("dimensions") and any(token in str(row.get("local_name", "")) for token in ("NoncontrollingInterest", "MinorityInterest", "RedeemableNoncontrollingInterest")) and "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest" not in str(row.get("local_name", ""))]
    nci_nonzero = [row for row in nci_claim_rows if isinstance(row.get("value"), (int, float)) and float(row["value"]) != 0.0]
    preferred_shares = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("source_accession") == accession and str(row.get("entity_identifier", "")).zfill(10) == str(policy.get("cik", "")).zfill(10) and row.get("period_end") == current_period and row.get("period_start") is None and row.get("unit") in {"xbrli:shares", "shares"} and not row.get("dimensions") and any(token in str(row.get("local_name", "")) for token in ("PreferredStockSharesOutstanding", "PreferredStockSharesIssued"))]
    if any(float(row.get("value")) != 0.0 for row in preferred_shares if isinstance(row.get("value"), (int, float))):
        raise CyclicalRefreshError("WDC nonzero preferred shares conflict with zero carrying claim")
    debt_rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("source_accession") == accession and str(row.get("entity_identifier", "")).zfill(10) == str(policy.get("cik", "")).zfill(10) and row.get("period_end") == current_period and row.get("period_start") is None and row.get("unit") == "USD" and not row.get("dimensions") and row.get("local_name") in {"LongTermDebt", "LongTermDebtCurrent", "LongTermDebtNoncurrent", "DebtCurrent", "ShortTermBorrowings", "FinanceLeaseLiability", "FinanceLeaseLiabilityCurrent", "FinanceLeaseLiabilityNoncurrent"}]
    aggregate = _fact(structural, local_name="LongTermDebt", period_end=current_period, accession=accession)["value"]
    component_values = {row.get("local_name"): float(row["value"]) for row in debt_rows if isinstance(row.get("value"), (int, float))}
    extra_positive = {name: value for name, value in component_values.items() if name != "LongTermDebt" and value > 0}
    if extra_positive and abs(sum(value for name, value in component_values.items() if name != "LongTermDebt") - aggregate) > 0.01:
        raise CyclicalRefreshError("WDC new short-term/debt/finance-lease class is not covered by the reported debt aggregate")
    assets = _fact(structural, local_name="Assets", period_end=current_period, accession=accession)["value"]
    liabilities = _fact(structural, local_name="Liabilities", period_end=current_period, accession=accession)["value"]
    equity = _fact(structural, local_name="StockholdersEquity", period_end=current_period, accession=accession)["value"]
    balance_total = _fact(structural, local_name="LiabilitiesAndStockholdersEquity", period_end=current_period, accession=accession)["value"]
    if preferred != 0 or nci_nonzero or abs(assets - liabilities - equity) > 0.01 or abs(assets - balance_total) > 0.01:
        raise CyclicalRefreshError("WDC other-claim balance reconciliation is unresolved")
    observed = [*wdc_states, *peer_states]
    refreshed = deepcopy(recipe)
    conversion_rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("source_accession") == accession and row.get("period_end") == current_period and row.get("local_name") in {"TemporaryEquityValueConversionOfConvertibleSecurities", "TemporaryEquitySharesConversionOfConvertibleSecurities"}]
    current_preferred_rows = [row for row in structural.get("facts", []) if isinstance(row, Mapping) and row.get("source_accession") == accession and row.get("period_end") == current_period and row.get("period_start") is None and row.get("local_name") in {"PreferredStockSharesOutstanding", "PreferredStockSharesIssued", "TemporaryEquitySharesOutstanding", "TemporaryEquityCarryingAmountAttributableToParent"}]
    ap_current = _fact(structural, local_name="AccountsPayableCurrent", period_end=current_period, accession=accession)["value"]
    nwc_missing = sorted(set(missing_nwc_components))
    if nwc_missing:
        error = CyclicalRefreshError("WDC operating-NWC source review required: missing " + ", ".join(nwc_missing))
        error.source_review = {"missing_components": nwc_missing, "period_end": current_period, "definition": "accounts receivable + inventory - accounts payable - current deferred revenue"}  # type: ignore[attr-defined]
        raise error
    ledger = {"controlling_filing": wdc, "peer_filing": stx, "period_end": current_period, "frozen_cutoff": cutoff, "sources": {"wdc_structural_sha256": packet.get("structural_sha256"), "wdc_states": [state.__dict__ for state in wdc_states], "wdc_scope": scope_trace, "stx_states": [state.__dict__ for state in peer_states]}, "values": {"cash": cash, "debt": debt, "operating_nwc_ratio": nwc_ratio, "shares": shares, "wacc": {name: recipe["scenarios"][name]["inputs"]["wacc"] for name in ("bear", "base", "bull")}, "normalized_tax_rate": {name: recipe["scenarios"][name]["inputs"]["normalized_tax_rate"] for name in ("bear", "base", "bull")}}, "claim_review": {"preferred_equity": preferred, "preferred_conversion_trace": {"current_zero_claim_rows": current_preferred_rows, "conversion_rows": conversion_rows, "treatment": "historical preferred conversion is not a current claim; current preferred/temporary balances and shares are checked separately"}, "noncontrolling_interests": "balance-sheet assets/liabilities/parent-equity reconciliation; no nonzero current claim fact", "noncontrolling_interest_claim_rows": nci_claim_rows, "balance_reconciliation": {"assets": assets, "liabilities": liabilities, "stockholders_equity": equity, "liabilities_and_stockholders_equity": balance_total}, "supplier_finance_scope": {"status": "included_in_accounts_payable_scope", "accounts_payable_current_source": _fact(structural, local_name="AccountsPayableCurrent", period_end=current_period, accession=accession), "treatment": "no additional debt deduction without a separately reported supplier-finance claim"}, "pipeline_or_event_overlay": "none"}, "nwc_review": {"status": "complete_trade_nwc", "missing_components": [], "definition": "accounts receivable + inventory - accounts payable - current deferred revenue"}}
    for name in ("bear", "base", "bull"):
        inputs = refreshed["scenarios"][name]["inputs"]
        inputs["current_state"] = current.__dict__
        inputs["observed_states"] = [state.__dict__ for state in observed]
        inputs["operating_nwc_ratio"] = nwc_ratio
        inputs["cash"] = cash
        inputs["debt"] = debt
        inputs["diluted_shares"] = shares[name]
        inputs["other_claims"] = {"low": 0.0, "base": 0.0, "high": 0.0}
    evaluated = evaluate_recipe(refreshed)
    ledger["result"] = {"range": evaluated["range"], "recipe_hash": evaluated["recipe_hash"], "effective_recipe_hash": evaluated["effective_recipe_hash"]}
    return {"bound": ledger["values"], "baseline_replay": dict(recipe.get("replay", evaluate_recipe(recipe)["range"])), "refreshed_recipe": refreshed, "refreshed_replay": ledger["result"]["range"], "source_ledger": ledger}
