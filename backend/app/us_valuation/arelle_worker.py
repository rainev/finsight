"""Child process for Arelle-backed structural Inline XBRL extraction."""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Iterable, Iterator
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .concept_resolver import load_structural_rules
from .structural_xbrl import ParseDiagnostic, StructuralFact

try:
    import resource
except ImportError:  # pragma: no cover - POSIX is the supported bounded-runtime path
    resource = None  # type: ignore[assignment]


CPU_LIMIT_SECONDS = 120
ADDRESS_SPACE_LIMIT_BYTES = 2 * 1024 * 1024 * 1024


class _QNameCanonicalizer:
    _KNOWN = {
        "http://www.xbrl.org/2003/iso4217": "iso4217",
        "http://www.xbrl.org/2003/instance": "xbrli",
    }

    def qname(self, value: Any) -> str:
        value = getattr(value, "qname", value)
        namespace = getattr(value, "namespaceURI", None)
        local_name = getattr(value, "localName", None)
        if namespace is None or local_name is None:
            text = str(value)
            if ":" in text:
                return text
            return text
        return f"{self.prefix(str(namespace))}:{local_name}"

    def prefix(self, namespace: str) -> str:
        known = self._KNOWN.get(namespace)
        if known:
            return known
        if namespace in _official_us_gaap_namespaces():
            return "us-gaap"
        digest = hashlib.sha1(namespace.encode("utf-8")).hexdigest()[:10]
        return f"ns_{digest}"


@lru_cache(maxsize=1)
def _official_us_gaap_namespaces() -> frozenset[str]:
    return frozenset(load_structural_rules()["official_us_gaap_namespaces"])


def _set_resource_limits() -> None:
    if resource is None:
        return
    for name, value in (
        ("RLIMIT_CPU", (CPU_LIMIT_SECONDS, CPU_LIMIT_SECONDS)),
        ("RLIMIT_AS", (ADDRESS_SPACE_LIMIT_BYTES, ADDRESS_SPACE_LIMIT_BYTES)),
    ):
        limit = getattr(resource, name, None)
        if limit is None:
            continue
        try:
            resource.setrlimit(limit, value)
        except (AttributeError, OSError, ValueError):
            continue


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)
    return text[:10] if len(text) >= 10 else text


def _concept_key(value: Any) -> tuple[str, str]:
    value = getattr(value, "qname", value)
    return (str(getattr(value, "namespaceURI", "")), str(getattr(value, "localName", "")))


def _relationship_sets(model: Any, arcrole: str) -> Iterator[tuple[str | None, Any]]:
    seen: set[tuple[str | None, int]] = set()
    for base_set_key in getattr(model, "baseSets", {}):
        if not isinstance(base_set_key, tuple) or not base_set_key:
            continue
        if base_set_key[0] != arcrole:
            continue
        linkrole = base_set_key[1] if len(base_set_key) > 1 else None
        relationship_set = model.relationshipSet(arcrole, linkrole)
        if relationship_set is None:
            continue
        marker = (linkrole, id(relationship_set))
        if marker not in seen:
            seen.add(marker)
            yield linkrole, relationship_set
    if not seen:
        relationship_set = model.relationshipSet(arcrole)
        if relationship_set is not None:
            yield None, relationship_set


def _relationship_endpoints(relationship_set: Any) -> Iterable[Any]:
    return getattr(relationship_set, "modelRelationships", ())


def _role_token(model: Any, linkrole: str | None) -> str | None:
    if not linkrole:
        return None
    candidates = [str(linkrole)]
    role_types = getattr(model, "roleTypes", {})
    for role_type in role_types.get(linkrole, ()):
        definition = getattr(role_type, "definition", None)
        if definition:
            candidates.append(str(definition))
    text = " ".join(candidates).lower().replace("-", " ").replace("_", " ")
    if "balance sheet" in text or "balancesheet" in text:
        return "balance_sheet"
    if "income statement" in text or "incomestatement" in text:
        return "income_statement"
    if "cash flow" in text or "cashflow" in text:
        return "cash_flow"
    return None


def _skip_diagnostic(code: str, message: str) -> ParseDiagnostic:
    return ParseDiagnostic(code=code, message=message, severity="warning")


def _numeric_fact_value(fact: Any) -> tuple[int | float | None, ParseDiagnostic | None]:
    concept = getattr(fact, "concept", None)
    if concept is None or not getattr(concept, "isNumeric", False):
        return None, None
    if not hasattr(fact, "xValue"):
        return None, _skip_diagnostic("missing_fact_value", "Numeric fact has no xValue.")
    raw_value = getattr(fact, "xValue", None)
    if raw_value is None:
        return None, _skip_diagnostic("nil_fact", "Numeric fact has a nil xValue.")
    try:
        decimal_value = raw_value if isinstance(raw_value, Decimal) else Decimal(str(raw_value))
    except (InvalidOperation, TypeError, ValueError):
        return None, _skip_diagnostic(
            "invalid_numeric_value", "Numeric fact xValue is not a valid number."
        )
    if not decimal_value.is_finite():
        return None, _skip_diagnostic(
            "nonfinite_numeric_value", "Numeric fact xValue is not finite."
        )
    if decimal_value == decimal_value.to_integral_value():
        return int(decimal_value), None
    numeric_value = float(decimal_value)
    if not float("-inf") < numeric_value < float("inf"):
        return None, _skip_diagnostic(
            "nonfinite_numeric_value", "Numeric fact xValue is not finite as a float."
        )
    return numeric_value, None


def _labels_for_concept(concept: Any) -> tuple[tuple[str, str], ...]:
    roles = (
        ("standard", "http://www.xbrl.org/2003/role/label"),
        ("terse", "http://www.xbrl.org/2003/role/terseLabel"),
        ("verbose", "http://www.xbrl.org/2003/role/verboseLabel"),
        ("documentation", "http://www.xbrl.org/2003/role/documentation"),
    )
    labels: list[tuple[str, str]] = []
    for name, role in roles:
        try:
            label = concept.label(
                lang="en", preferredLabel=role, fallbackToQname=False
            )
        except (AttributeError, TypeError):
            label = None
        if label:
            labels.append((name, str(label).strip()))
    if not labels:
        try:
            label = concept.label(lang="en", fallbackToQname=False)
        except (AttributeError, TypeError):
            label = None
        if label:
            labels.append(("standard", str(label).strip()))
    return tuple(sorted(set(labels)))


def _documentation(labels: tuple[tuple[str, str], ...]) -> str | None:
    values = [value for role, value in labels if role == "documentation"]
    return values[0] if values else None


def _unit_name(model: Any, unit_id: str | None, qnames: _QNameCanonicalizer) -> str:
    if not unit_id:
        return "unknown"
    unit = getattr(model, "units", {}).get(unit_id)
    measures = getattr(unit, "measures", ((), ())) if unit is not None else ((), ())
    numerator = measures[0] if measures else ()
    measure = next(iter(numerator), None)
    if measure is None:
        return "unknown"
    namespace = str(getattr(measure, "namespaceURI", ""))
    local_name = str(getattr(measure, "localName", ""))
    if namespace == "http://www.xbrl.org/2003/iso4217":
        return local_name
    return qnames.qname(measure)


def _dimensions(context: Any, qnames: _QNameCanonicalizer) -> tuple[tuple[str, str], ...]:
    dimensions: list[tuple[str, str]] = []
    for dimension, value in sorted(
        (getattr(context, "qnameDims", {}) or {}).items(),
        key=lambda item: qnames.qname(item[0]),
    ):
        member = getattr(value, "memberQname", None)
        if member is not None:
            dimensions.append((qnames.qname(dimension), qnames.qname(member)))
        else:
            dimensions.append((qnames.qname(dimension), "typed"))
    return tuple(dimensions)


def _structural_links(model: Any, concept: Any, qnames: _QNameCanonicalizer) -> dict[str, tuple[str, ...]]:
    from arelle import XbrlConst  # noqa: PLC0415 - child-process-only import

    concept_key = _concept_key(concept)
    result: dict[str, set[str]] = {
        "statement_roles": set(),
        "presentation_parents": set(),
        "calculation_parents": set(),
        "calculation_children": set(),
        "definition_parents": set(),
        "definition_children": set(),
    }

    for linkrole, relationship_set in _relationship_sets(model, XbrlConst.parentChild):
        role = _role_token(model, linkrole)
        for relationship in _relationship_endpoints(relationship_set):
            parent = getattr(relationship, "fromModelObject", None)
            child = getattr(relationship, "toModelObject", None)
            if parent is None or child is None:
                continue
            if _concept_key(parent) == concept_key:
                result["statement_roles"].add(role) if role else None
            if _concept_key(child) == concept_key:
                result["statement_roles"].add(role) if role else None
                result["presentation_parents"].add(qnames.qname(parent))
    for linkrole, relationship_set in _relationship_sets(model, XbrlConst.summationItem):
        role = _role_token(model, linkrole)
        for relationship in _relationship_endpoints(relationship_set):
            parent = getattr(relationship, "fromModelObject", None)
            child = getattr(relationship, "toModelObject", None)
            if parent is None or child is None:
                continue
            if _concept_key(child) == concept_key:
                result["calculation_parents"].add(qnames.qname(parent))
                if role:
                    result["statement_roles"].add(role)
            if _concept_key(parent) == concept_key:
                result["calculation_children"].add(qnames.qname(child))
                if role:
                    result["statement_roles"].add(role)

    for arcrole in (XbrlConst.generalSpecial, XbrlConst.dimensionDomain, XbrlConst.domainMember):
        for _linkrole, relationship_set in _relationship_sets(model, arcrole):
            for relationship in _relationship_endpoints(relationship_set):
                parent = getattr(relationship, "fromModelObject", None)
                child = getattr(relationship, "toModelObject", None)
                if parent is None or child is None:
                    continue
                if _concept_key(child) == concept_key:
                    result["definition_parents"].add(qnames.qname(parent))
                if _concept_key(parent) == concept_key:
                    result["definition_children"].add(qnames.qname(child))

    return {key: tuple(sorted(values)) for key, values in result.items()}


def _parser_diagnostics(model: Any) -> tuple[ParseDiagnostic, ...]:
    diagnostics: list[ParseDiagnostic] = []
    for item in getattr(model, "errors", ()) or ():
        code = str(getattr(item, "code", "arelle_diagnostic"))
        message = str(getattr(item, "message", item))
        lowered = f"{code} {message}".lower()
        severity = "warning" if "warn" in lowered else "error"
        diagnostics.append(ParseDiagnostic(code=code, message=message, severity=severity))  # type: ignore[arg-type]
    return tuple(diagnostics)


def _extract_payload(entrypoint: Path, accession: str) -> dict[str, Any]:
    # These imports are intentionally inside the child worker and never occur in
    # app.us_valuation.arelle_adapter or any returned value.
    from arelle import Cntlr  # noqa: PLC0415 - child-process-only import

    controller: Any | None = None
    model: Any | None = None
    qnames = _QNameCanonicalizer()
    worker_temp_dir = tempfile.TemporaryDirectory(prefix="arelle-worker-")
    try:
        controller = Cntlr.Cntlr(logFileName="logToPrint", disable_persistent_config=True)
        controller.userAppDir = worker_temp_dir.name
        controller.webCache.cacheDir = os.path.join(worker_temp_dir.name, "cache")
        controller.webCache.workOffline = True
        os.makedirs(controller.webCache.cacheDir, exist_ok=True)
        model = controller.modelManager.load(str(entrypoint))
        if model is None:
            raise RuntimeError("Arelle returned no model")
        diagnostics = _parser_diagnostics(model)
        if any(item.severity == "error" for item in diagnostics):
            raise RuntimeError("Arelle reported fatal parser errors")

        raw_facts: list[StructuralFact] = []
        for fact in getattr(model, "facts", ()) or ():
            numeric_value, skip_diagnostic = _numeric_fact_value(fact)
            if skip_diagnostic is not None:
                diagnostics += (skip_diagnostic,)
            if numeric_value is None:
                continue
            concept = getattr(fact, "concept", None)
            if concept is None:
                continue
            context_id = str(getattr(fact, "contextID", ""))
            context = getattr(model, "contexts", {}).get(context_id)
            if context is None:
                diagnostics += (
                    ParseDiagnostic(
                        code="missing_context",
                        message=f"Context {context_id} could not be resolved.",
                        severity="warning",
                        context=(("context_id", context_id),),
                    ),
                )
                continue
            labels = _labels_for_concept(concept)
            links = _structural_links(model, concept, qnames)
            if getattr(context, "isInstantPeriod", False):
                period_start = None
                instant = getattr(context, "instantDatetime", None)
                if isinstance(instant, (date, datetime)):
                    instant -= timedelta(days=1)
                period_end = _iso_date(instant)
            else:
                period_start = _iso_date(getattr(context, "startDatetime", None))
                end = getattr(context, "endDatetime", None)
                if isinstance(end, (date, datetime)):
                    end -= timedelta(days=1)
                period_end = _iso_date(end)
            if not period_end:
                continue
            concept_qname = getattr(concept, "qname", concept)
            namespace = str(getattr(concept_qname, "namespaceURI", ""))
            local_name = str(getattr(concept_qname, "localName", ""))
            raw_facts.append(
                StructuralFact(
                    qname=qnames.qname(concept),
                    namespace=namespace,
                    local_name=local_name,
                    labels=labels,
                    documentation=_documentation(labels),
                    value=numeric_value,
                    unit=_unit_name(model, getattr(fact, "unitID", None), qnames),
                    period_start=period_start,
                    period_end=period_end,
                    context_id=context_id,
                    dimensions=_dimensions(context, qnames),
                    statement_roles=links["statement_roles"],
                    presentation_parents=links["presentation_parents"],
                    calculation_parents=links["calculation_parents"],
                    calculation_children=links["calculation_children"],
                    definition_parents=links["definition_parents"],
                    definition_children=links["definition_children"],
                    source_accession=accession,
                )
            )
        if not raw_facts:
            raise RuntimeError("Arelle model contained no numeric facts")
        period_end = max(fact.period_end for fact in raw_facts)
        return {
            "source_accession": accession,
            "period_end": period_end,
            "facts": [fact.as_dict() for fact in sorted(raw_facts, key=lambda item: item.qname)],
            "diagnostics": [
                {
                    "code": diagnostic.code,
                    "message": diagnostic.message,
                    "severity": diagnostic.severity,
                    "context": diagnostic.context,
                }
                for diagnostic in diagnostics
            ],
            "form": None,
        }
    finally:
        try:
            if model is not None:
                close_model = getattr(model, "close", None)
                if callable(close_model):
                    close_model()
        finally:
            try:
                if controller is not None:
                    close_controller = getattr(controller, "close", None)
                    if callable(close_controller):
                        close_controller()
            finally:
                worker_temp_dir.cleanup()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entrypoint", type=Path, required=True)
    parser.add_argument("--accession", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    _set_resource_limits()
    try:
        payload = _extract_payload(arguments.entrypoint, arguments.accession)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    except ModuleNotFoundError as error:
        print(f"Arelle is unavailable: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # pragma: no cover - exercised through parent boundary
        print(f"Arelle parse failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
