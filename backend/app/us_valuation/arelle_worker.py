"""Child process for Arelle-backed structural Inline XBRL extraction."""

from __future__ import annotations

import argparse
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from collections.abc import Iterable, Iterator
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .concept_resolver import load_structural_rules
from .structural_xbrl import (
    MAX_SUPPORTED_INTEGER,
    ParseDiagnostic,
    StructuralFact,
    StructuralRelationship,
    normalize_filing_form,
)

try:
    import resource
except ImportError:  # pragma: no cover - POSIX is the supported bounded-runtime path
    resource = None  # type: ignore[assignment]


CPU_LIMIT_SECONDS = 120
ADDRESS_SPACE_LIMIT_BYTES = 2 * 1024 * 1024 * 1024
MAX_PRESENTATION_ANCESTORS = 128
MAX_PRESENTATION_DEPTH = 32
SEC_INLINE_TRANSFORM_PLUGIN = (
    Path(__file__).resolve().parent / "vendor" / "arelle_edgar_transform"
)


def _load_sec_inline_transforms(controller: Any) -> None:
    """Load the pinned official SEC transform hook before parsing Inline XBRL."""

    from arelle import PluginManager  # noqa: PLC0415 - child-process-only import

    module_info = PluginManager.addPluginModule(os.fspath(SEC_INLINE_TRANSFORM_PLUGIN))
    if module_info is None:
        raise RuntimeError("Arelle SEC Inline Transforms plugin could not be registered")
    hooks = tuple(PluginManager.pluginClassMethods("ModelManager.LoadCustomTransforms"))
    if not hooks:
        raise RuntimeError("Arelle SEC Inline Transforms plugin did not expose its transform hook")
    controller.modelManager.customTransforms = None
    controller.modelManager.loadCustomTransforms()


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
    if (
        "balance sheet" in text
        or "balancesheet" in text
        or "statementoffinancialposition" in text
        or "statement of financial position" in text
    ):
        return "balance_sheet"
    if "income statement" in text or "incomestatement" in text:
        return "income_statement"
    if "cash flow" in text or "cashflow" in text:
        return "cash_flow"
    return None


def _relationship_set_role(
    model: Any, linkrole: str | None, relationship_set: Any
) -> str | None:
    role = _role_token(model, linkrole)
    if not linkrole:
        return None

    relationships = tuple(
        relationship
        for relationship in _relationship_endpoints(relationship_set)
        if getattr(relationship, "linkrole", linkrole) in {None, linkrole}
    )
    child_keys = {
        _concept_key(getattr(relationship, "toModelObject", None))
        for relationship in relationships
        if getattr(relationship, "toModelObject", None) is not None
    }
    root_names = {
        _concept_key(parent)[1].casefold().replace("_", "").replace("-", "")
        for relationship in relationships
        if (parent := getattr(relationship, "fromModelObject", None)) is not None
        and _concept_key(parent) not in child_keys
    }
    balance_sheet_roots = {
        "statementoffinancialpositionabstract",
        "balancesheetabstract",
        "assets",
        "assetsabstract",
        "assetscurrent",
        "assetscurrentabstract",
        "assetsnoncurrent",
        "assetsnoncurrentabstract",
        "liabilities",
        "liabilitiesabstract",
        "liabilitiescurrent",
        "liabilitiescurrentabstract",
        "liabilitiesnoncurrent",
        "liabilitiesnoncurrentabstract",
        "stockholdersequity",
        "stockholdersequityabstract",
        "equity",
        "equityabstract",
    }
    root_roles: set[str | None] = set()
    for name in root_names:
        if name in balance_sheet_roots:
            root_roles.add("balance_sheet")
        elif "incomestatement" in name or "statementofoperations" in name:
            root_roles.add("income_statement")
        elif "cashflow" in name:
            root_roles.add("cash_flow")
        else:
            root_roles.add(None)
    if not root_roles:
        return None
    if len(root_roles) == 1:
        root_role = next(iter(root_roles))
        if root_role is not None and role in {None, root_role}:
            return root_role
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
    int_value = int(decimal_value)
    if Decimal(int_value) == decimal_value:
        if abs(int_value) > MAX_SUPPORTED_INTEGER:
            return None, _skip_diagnostic(
                "numeric_out_of_range", "Numeric fact xValue exceeds the supported numeric range."
            )
        return int_value, None
    numeric_value = float(decimal_value)
    if not math.isfinite(numeric_value):
        return None, _skip_diagnostic(
            "nonfinite_numeric_value", "Numeric fact xValue is not finite as a float."
        )
    if Decimal.from_float(numeric_value) != decimal_value:
        return None, _skip_diagnostic(
            "inexact_numeric_value", "Numeric fact xValue cannot be represented exactly as a float."
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


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return converted if math.isfinite(converted) else None


def _structural_links(model: Any, concept: Any, qnames: _QNameCanonicalizer) -> dict[str, Any]:
    from arelle import XbrlConst  # noqa: PLC0415 - child-process-only import

    concept_key = _concept_key(concept)
    result: dict[str, set[str]] = {
        "statement_roles": set(),
        "presentation_parents": set(),
        "calculation_parents": set(),
        "calculation_children": set(),
        "definition_parents": set(),
        "definition_children": set(),
        "presentation_ancestry": set(),
    }
    relationship_records: set[StructuralRelationship] = set()

    for linkrole, relationship_set in _relationship_sets(model, XbrlConst.parentChild):
        role = _relationship_set_role(model, linkrole, relationship_set)
        parent_map: dict[tuple[str, str], list[Any]] = {}
        for relationship in _relationship_endpoints(relationship_set):
            parent = getattr(relationship, "fromModelObject", None)
            child = getattr(relationship, "toModelObject", None)
            if parent is None or child is None:
                continue
            parent_map.setdefault(_concept_key(child), []).append(relationship)
            if concept_key in {_concept_key(parent), _concept_key(child)}:
                relationship_records.add(
                    _relationship_record(
                        relationship,
                        arcrole=XbrlConst.parentChild,
                        linkrole=linkrole,
                        statement_role=role,
                        qnames=qnames,
                    )
                )
            if _concept_key(parent) == concept_key:
                result["statement_roles"].add(role) if role else None
            if _concept_key(child) == concept_key:
                result["statement_roles"].add(role) if role else None
                result["presentation_parents"].add(qnames.qname(parent))
        frontier = [(concept, 0)]
        visited: set[tuple[str, str]] = {concept_key}
        while frontier:
            child, depth = frontier.pop(0)
            parents = parent_map.get(_concept_key(child), ())
            if parents and depth >= MAX_PRESENTATION_DEPTH:
                raise RuntimeError("presentation ancestry exceeds governed depth")
            for relationship in parents:
                parent = getattr(relationship, "fromModelObject", None)
                if parent is None:
                    continue
                key = _concept_key(parent)
                if key in visited:
                    continue
                visited.add(key)
                relationship_records.add(
                    _relationship_record(
                        relationship,
                        arcrole=XbrlConst.parentChild,
                        linkrole=linkrole,
                        statement_role=role,
                        qnames=qnames,
                    )
                )
                result["presentation_ancestry"].add(qnames.qname(parent))
                if len(result["presentation_ancestry"]) > MAX_PRESENTATION_ANCESTORS:
                    raise RuntimeError("presentation ancestry exceeds governed count")
                frontier.append((parent, depth + 1))
    for linkrole, relationship_set in _relationship_sets(model, XbrlConst.summationItem):
        role = _relationship_set_role(model, linkrole, relationship_set)
        for relationship in _relationship_endpoints(relationship_set):
            parent = getattr(relationship, "fromModelObject", None)
            child = getattr(relationship, "toModelObject", None)
            if parent is None or child is None:
                continue
            if concept_key in {_concept_key(parent), _concept_key(child)}:
                relationship_records.add(
                    _relationship_record(
                        relationship,
                        arcrole=XbrlConst.summationItem,
                        linkrole=linkrole,
                        statement_role=role,
                        qnames=qnames,
                    )
                )
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
            role = _relationship_set_role(model, _linkrole, relationship_set)
            for relationship in _relationship_endpoints(relationship_set):
                parent = getattr(relationship, "fromModelObject", None)
                child = getattr(relationship, "toModelObject", None)
                if parent is None or child is None:
                    continue
                if concept_key in {_concept_key(parent), _concept_key(child)}:
                    relationship_records.add(
                        _relationship_record(
                            relationship,
                            arcrole=arcrole,
                            linkrole=_linkrole,
                            statement_role=role,
                            qnames=qnames,
                        )
                    )
                if _concept_key(child) == concept_key:
                    result["definition_parents"].add(qnames.qname(parent))
                if _concept_key(parent) == concept_key:
                    result["definition_children"].add(qnames.qname(child))

    return {
        **{key: tuple(sorted(values)) for key, values in result.items()},
        "relationships": _deduplicate_relationship_records(relationship_records),
    }


def _relationship_record(
    relationship: Any,
    *,
    arcrole: str,
    linkrole: str | None,
    statement_role: str | None,
    qnames: _QNameCanonicalizer,
) -> StructuralRelationship:
    return StructuralRelationship(
        arcrole=str(getattr(relationship, "arcrole", None) or arcrole),
        linkrole=str(linkrole or getattr(relationship, "linkrole", None) or "default"),
        from_concept=qnames.qname(getattr(relationship, "fromModelObject")),
        to_concept=qnames.qname(getattr(relationship, "toModelObject")),
        order=_optional_float(getattr(relationship, "order", None)),
        preferred_label=(
            str(getattr(relationship, "preferredLabel"))
            if getattr(relationship, "preferredLabel", None)
            else None
        ),
        calculation_weight=_optional_float(getattr(relationship, "weight", None)),
        statement_role=statement_role,
    )


def _deduplicate_relationship_records(
    records: Iterable[StructuralRelationship],
) -> tuple[StructuralRelationship, ...]:
    groups: dict[tuple[object, ...], list[StructuralRelationship]] = {}
    for record in records:
        identity = (
            record.arcrole,
            record.linkrole,
            record.from_concept,
            record.to_concept,
            record.order,
            record.preferred_label,
            record.calculation_weight,
        )
        groups.setdefault(identity, []).append(record)

    deduplicated: list[StructuralRelationship] = []
    for identity in sorted(groups, key=lambda item: tuple(str(value) for value in item)):
        group = groups[identity]
        classified_roles = {
            record.statement_role
            for record in group
            if record.statement_role is not None
        }
        statement_role = (
            next(iter(classified_roles)) if len(classified_roles) == 1 else None
        )
        deduplicated.append(replace(group[0], statement_role=statement_role))
    return tuple(deduplicated)


def _parser_diagnostics(model: Any) -> tuple[ParseDiagnostic, ...]:
    diagnostics: list[ParseDiagnostic] = []
    for item in getattr(model, "errors", ()) or ():
        code = str(getattr(item, "code", "arelle_diagnostic"))
        message = str(getattr(item, "message", item))
        lowered = f"{code} {message}".lower()
        severity = "warning" if "warn" in lowered else "error"
        diagnostics.append(ParseDiagnostic(code=code, message=message, severity=severity))  # type: ignore[arg-type]
    return tuple(diagnostics)


def _fact_attribute(fact: Any, name: str) -> str | None:
    value = getattr(fact, name, None)
    if value is None:
        getter = getattr(fact, "get", None)
        value = getter(name) if callable(getter) else None
    return str(value) if value is not None and str(value) else None


def _package_manifest(
    entrypoint: Path, accession: str, form: str
) -> tuple[dict[str, Any] | None, tuple[tuple[str, str], ...]]:
    manifest_path = entrypoint.parent / "package-manifest.json"
    if not manifest_path.is_file():
        return None, (
            ("accession", accession),
            ("form", form),
            ("primary_document", entrypoint.name),
            ("package_generation", "local-fixture"),
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["accession"] != accession or manifest["form"] != form:
            raise ValueError("package identity mismatch")
        if manifest["entrypoint_local_path"] != entrypoint.relative_to(entrypoint.parent).as_posix():
            raise ValueError("package entrypoint mismatch")
        files = manifest["files"]
        if not isinstance(files, list) or len(files) != manifest["resource_count"]:
            raise ValueError("package resource count mismatch")
        for item in files:
            candidate = (entrypoint.parent / item["local_path"]).resolve()
            if not candidate.is_relative_to(entrypoint.parent.resolve()):
                raise ValueError("unsafe package local path")
            raw = candidate.read_bytes()
            if hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("package resource hash mismatch")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid structural package manifest: {exc}") from exc
    return manifest, (
        ("accession", accession),
        ("form", form),
        ("primary_document", entrypoint.name),
        ("package_generation", str(manifest["generation"])),
        ("manifest_version", str(manifest["manifest_version"])),
        ("primary_source_url", str(manifest["primary_source_url"])),
        ("retrieved_at_epoch", str(manifest["cached_at_epoch"])),
        ("resource_count", str(manifest["resource_count"])),
        ("total_bytes", str(manifest["total_bytes"])),
    )


def _hydrate_offline_cache(controller: Any, package_dir: Path, manifest: dict[str, Any] | None) -> None:
    if manifest is None:
        return
    for item in manifest["files"]:
        source_url = str(item["source_url"])
        if not source_url.startswith(("http://", "https://")):
            continue
        source_path = package_dir / str(item["local_path"])
        cache_path = Path(controller.webCache.urlToCacheFilepath(source_url))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, cache_path)


def _extract_payload(entrypoint: Path, accession: str, form: str = "10-K") -> dict[str, Any]:
    # These imports are intentionally inside the child worker and never occur in
    # app.us_valuation.arelle_adapter or any returned value.
    from arelle import Cntlr  # noqa: PLC0415 - child-process-only import

    controller: Any | None = None
    model: Any | None = None
    qnames = _QNameCanonicalizer()
    normalized_form = normalize_filing_form(form)
    manifest, filing_metadata = _package_manifest(entrypoint, accession, normalized_form)
    worker_temp_dir = tempfile.TemporaryDirectory(prefix="arelle-worker-")
    try:
        controller = Cntlr.Cntlr(logFileName="logToPrint", disable_persistent_config=True)
        _load_sec_inline_transforms(controller)
        controller.userAppDir = worker_temp_dir.name
        controller.webCache.cacheDir = os.path.join(worker_temp_dir.name, "cache")
        controller.webCache.workOffline = True
        os.makedirs(controller.webCache.cacheDir, exist_ok=True)
        _hydrate_offline_cache(controller, entrypoint.parent, manifest)
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
                    decimals=_fact_attribute(fact, "decimals"),
                    scale=_fact_attribute(fact, "scale"),
                    sign=_fact_attribute(fact, "sign"),
                    filing_form=normalized_form,
                    filing_metadata=filing_metadata,
                    presentation_ancestry=links["presentation_ancestry"],
                    relationships=links["relationships"],
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
            "form": normalized_form,
            "filing_metadata": filing_metadata,
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
    parser.add_argument("--form", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    _set_resource_limits()
    try:
        payload = _extract_payload(arguments.entrypoint, arguments.accession, arguments.form)
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
