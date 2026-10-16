"""Governed semantic registry for official valuation evidence fields."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


REGISTRY_VERSION = "FINSIGHT-EVIDENCE-FIELD-1.0"
_CONFIG_DIR = Path(__file__).with_name("config")
_REGISTRY_PATH = _CONFIG_DIR / "evidence_field_registry.json"
_ALIASES_PATH = _CONFIG_DIR / "concept_aliases.json"


def _strings(value: object, field: str, *, required: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{field} must be a list of nonempty strings")
    result = tuple(value)
    if required and not result:
        raise ValueError(f"{field} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field} must not contain duplicates")
    return result


@dataclass(frozen=True)
class AggregateReplacement:
    field: str
    covered_fields: tuple[str, ...]
    coverage_basis: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> AggregateReplacement:
        field = value.get("field")
        basis = value.get("coverage_basis")
        if not isinstance(field, str) or not field or not isinstance(basis, str) or not basis:
            raise ValueError("aggregate replacement field/basis are required")
        covered = _strings(value.get("covered_fields"), "covered_fields", required=True)
        return cls(field=field, covered_fields=covered, coverage_basis=basis)


@dataclass(frozen=True)
class GovernedField:
    field: str
    accounting_meaning: str
    economic_class: str
    standard_concepts: tuple[str, ...]
    custom_aliases: tuple[str, ...]
    statement_roles: tuple[str, ...]
    period_roles: tuple[str, ...]
    units: tuple[str, ...]
    allowed_dimensions: tuple[str, ...]
    consolidation_scopes: tuple[str, ...]
    aggregate_replacements: tuple[AggregateReplacement, ...]
    double_count_exclusions: tuple[str, ...]
    version: str = REGISTRY_VERSION

    @property
    def standard_aliases(self) -> tuple[str, ...]:
        return tuple(
            concept if ":" in concept else f"us-gaap:{concept}"
            for concept in self.standard_concepts
        )

    @property
    def consolidation_level(self) -> str:
        return self.consolidation_scopes[0] if len(self.consolidation_scopes) == 1 else "governed_multiple"

    @property
    def allowed_units(self) -> tuple[str, ...]:
        return self.units

    @property
    def period_role(self) -> str:
        return self.period_roles[0] if len(self.period_roles) == 1 else "governed_multiple"

    @property
    def valid_aggregate_replacements(self) -> tuple[str, ...]:
        if self.field.endswith("_total"):
            return tuple(item for item in self.double_count_exclusions if item != self.field)
        return tuple(item.field for item in self.aggregate_replacements)

    @property
    def double_counting_exclusions(self) -> tuple[str, ...]:
        return (self.field,) + tuple(
            item for item in self.double_count_exclusions if item != self.field
        )

    def matches_concept(self, qname: str) -> bool:
        local = qname.split(":", 1)[-1]
        return qname in self.custom_aliases or local in self.standard_concepts

    def allows(
        self,
        *,
        unit: str,
        period_role: str,
        statement_role: str,
        consolidation_scope: str,
        dimensions: tuple[tuple[str, str], ...] = (),
    ) -> bool:
        dimension_keys = {f"{axis}={member}" for axis, member in dimensions}
        return (
            unit in self.units
            and period_role in self.period_roles
            and statement_role in self.statement_roles
            and consolidation_scope in self.consolidation_scopes
            and dimension_keys == set(self.allowed_dimensions)
        )


def load_field_registry(path: Path | None = None) -> dict[str, GovernedField]:
    config_path = Path(path) if path is not None else _REGISTRY_PATH
    config = json.loads(config_path.read_text(encoding="utf-8"))
    aliases = json.loads(_ALIASES_PATH.read_text(encoding="utf-8"))
    if config.get("version") != REGISTRY_VERSION or not isinstance(config.get("fields"), Mapping):
        raise ValueError("unsupported evidence field registry")
    alias_fields = aliases.get("fields", {})
    result: dict[str, GovernedField] = {}
    for field, raw in config["fields"].items():
        if not isinstance(field, str) or not isinstance(raw, Mapping):
            raise ValueError("registry fields must be named objects")
        meaning = raw.get("accounting_meaning")
        economic_class = raw.get("economic_class")
        if not isinstance(meaning, str) or not meaning or not isinstance(economic_class, str) or not economic_class:
            raise ValueError(f"{field}: meaning and economic class are required")
        alias_record = alias_fields.get(field, {}) if isinstance(alias_fields, Mapping) else {}
        standard = _strings(alias_record.get("concepts", []), f"{field}.standard_concepts")
        aggregates = raw.get("aggregate_replacements", [])
        if not isinstance(aggregates, list):
            raise ValueError(f"{field}.aggregate_replacements must be a list")
        result[field] = GovernedField(
            field=field,
            accounting_meaning=meaning,
            economic_class=economic_class,
            standard_concepts=standard,
            custom_aliases=_strings(raw.get("custom_aliases", []), f"{field}.custom_aliases"),
            statement_roles=_strings(raw.get("statement_roles"), f"{field}.statement_roles", required=True),
            period_roles=_strings(raw.get("period_roles"), f"{field}.period_roles", required=True),
            units=_strings(raw.get("units"), f"{field}.units", required=True),
            allowed_dimensions=_strings(raw.get("allowed_dimensions", []), f"{field}.allowed_dimensions"),
            consolidation_scopes=_strings(raw.get("consolidation_scopes"), f"{field}.consolidation_scopes", required=True),
            aggregate_replacements=tuple(AggregateReplacement.from_dict(item) for item in aggregates),
            double_count_exclusions=_strings(raw.get("double_count_exclusions", []), f"{field}.double_count_exclusions"),
        )
    concept_index: dict[str, str] = {}
    for field, governed in result.items():
        for alias in governed.standard_aliases + governed.custom_aliases:
            prior = concept_index.get(alias)
            if prior is not None and prior != field:
                raise ValueError(f"ambiguous governed alias {alias}: {prior}, {field}")
            concept_index[alias] = field
        for replacement in governed.aggregate_replacements:
            if replacement.field not in result:
                raise ValueError(f"{field}: unknown aggregate replacement {replacement.field}")
            if replacement.field in replacement.covered_fields:
                raise ValueError(f"{field}: aggregate cannot cover itself")
            unknown_covered = set(replacement.covered_fields) - set(result)
            if unknown_covered:
                raise ValueError(f"{field}: unknown aggregate coverage fields {sorted(unknown_covered)}")
            if field not in replacement.covered_fields:
                raise ValueError(f"{field}: aggregate replacement must explicitly cover the target field")
    return result
