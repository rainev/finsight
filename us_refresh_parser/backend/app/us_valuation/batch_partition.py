"""Deterministic global partition for replacement-universe Batches 02–50."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re
from typing import Any, Iterable, Sequence

from .batch_01 import BATCH_01_MANIFEST
from .universe import UniverseIssuer


PARTITION_VERSION = "US-RESET-PARTITION-2026-08-14-2.0"
FAMILY_TAXONOMY_VERSION = "US-PARTITION-COHORT-2.0"
FAMILY_BY_SECTOR = {
    "Communication Services": "operating_fcff",
    "Consumer Discretionary": "operating_fcff",
    "Consumer Staples": "operating_fcff",
    "Health Care": "operating_fcff",
    "Industrials": "operating_fcff",
    "Information Technology": "operating_fcff",
    "Financials": "financial_equity",
    "Utilities": "utility_fcfe",
    "Real Estate": "reit_affo",
    "Energy": "resource_cycle_fcff",
    "Materials": "resource_cycle_fcff",
}
OPERATING_BATCH_COUNTS = {
    "Communication Services": 2,
    "Consumer Discretionary": 5,
    "Consumer Staples": 3,
    "Health Care": 6,
    "Industrials": 8,
    "Information Technology": 7,
}
EXPECTED_REMAINING_SECTOR_COUNTS = {
    "Communication Services": 20,
    "Consumer Discretionary": 47,
    "Consumer Staples": 34,
    "Energy": 21,
    "Financials": 74,
    "Health Care": 59,
    "Industrials": 83,
    "Information Technology": 67,
    "Materials": 25,
    "Real Estate": 30,
    "Utilities": 30,
}
OPERATING_CROSS_BOUNDARIES = {
    "CASY": (
        "Consumer Discretionary",
        "consumer_retail_demand_boundary",
    ),
    "KDP": (
        "Consumer Discretionary",
        "consumer_brand_and_discretionary_demand_boundary",
    ),
    "EL": (
        "Consumer Discretionary",
        "premium_consumer_brand_boundary",
    ),
    "KVUE": (
        "Health Care",
        "consumer_health_product_boundary",
    ),
    "BR": (
        "Information Technology",
        "outsourced_data_processing_boundary",
    ),
    "VRSK": (
        "Information Technology",
        "data_and_analytics_platform_boundary",
    ),
    "VRT": (
        "Information Technology",
        "data_center_infrastructure_boundary",
    ),
}
FINANCIAL_RESOURCE_BOUNDARIES = {
    "WMB",
    "OKE",
    "TRGP",
    "KMI",
    "TPL",
    "VLO",
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


@dataclass(frozen=True)
class PartitionMember:
    cik: str
    ticker: str
    issuer_name: str
    gics_sector: str
    gics_sub_industry: str
    role: str
    primary_lane_id: str
    partition_family_id: str
    boundary_reason: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "cik": self.cik,
            "ticker": self.ticker,
            "issuer_name": self.issuer_name,
            "gics_sector": self.gics_sector,
            "gics_sub_industry": self.gics_sub_industry,
            "role": self.role,
            "primary_lane_id": self.primary_lane_id,
            "partition_family_id": self.partition_family_id,
            "boundary_reason": self.boundary_reason,
        }


def _member(
    issuer: UniverseIssuer,
    *,
    role: str,
    core_lane: str,
    boundary_reason: str | None = None,
) -> PartitionMember:
    return PartitionMember(
        cik=issuer.cik,
        ticker=issuer.ticker,
        issuer_name=issuer.issuer_name,
        gics_sector=issuer.gics_sector,
        gics_sub_industry=issuer.gics_sub_industry,
        role=role,
        primary_lane_id=_slug(issuer.gics_sector),
        partition_family_id=FAMILY_BY_SECTOR[issuer.gics_sector],
        boundary_reason=boundary_reason,
    )


def _max_flow_boundary_matrix(
    *,
    boundary_counts: dict[str, int],
    core_slots: dict[str, int],
) -> dict[tuple[str, str], int]:
    """Deterministic bipartite max-flow from boundary sectors to other cores."""

    source = "SOURCE"
    sink = "SINK"
    boundary_nodes = {sector: f"B:{sector}" for sector in sorted(boundary_counts)}
    core_nodes = {sector: f"C:{sector}" for sector in sorted(core_slots)}
    capacity: dict[tuple[str, str], int] = {}
    adjacency: dict[str, set[str]] = {}

    def edge(left: str, right: str, cap: int) -> None:
        capacity[(left, right)] = cap
        capacity.setdefault((right, left), 0)
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)

    total = sum(boundary_counts.values())
    for sector, count in boundary_counts.items():
        edge(source, boundary_nodes[sector], count)
    for boundary_sector, boundary_node in boundary_nodes.items():
        for core_sector, core_node in core_nodes.items():
            if boundary_sector != core_sector:
                edge(boundary_node, core_node, total)
    for sector, count in core_slots.items():
        edge(core_nodes[sector], sink, count)

    flow = {key: 0 for key in capacity}
    while True:
        parent = {source: None}
        queue = deque([source])
        while queue and sink not in parent:
            node = queue.popleft()
            for neighbor in sorted(adjacency.get(node, ())):
                if neighbor not in parent and capacity[(node, neighbor)] - flow[(node, neighbor)] > 0:
                    parent[neighbor] = node
                    queue.append(neighbor)
        if sink not in parent:
            break
        increment = total
        node = sink
        while parent[node] is not None:
            prior = parent[node]
            increment = min(
                increment,
                capacity[(prior, node)] - flow[(prior, node)],
            )
            node = prior
        node = sink
        while parent[node] is not None:
            prior = parent[node]
            flow[(prior, node)] += increment
            flow[(node, prior)] -= increment
            node = prior
    if sum(flow[(source, node)] for node in boundary_nodes.values()) != total:
        raise ValueError("operating boundary assignment is infeasible")
    return {
        (boundary_sector, core_sector): flow[
            (boundary_nodes[boundary_sector], core_nodes[core_sector])
        ]
        for boundary_sector in boundary_nodes
        for core_sector in core_nodes
        if boundary_sector != core_sector
        and flow[(boundary_nodes[boundary_sector], core_nodes[core_sector])] > 0
    }


def _batch(
    *, batch_number: int, core_lane: str, members: Iterable[PartitionMember]
) -> dict[str, Any]:
    ordered = tuple(sorted(members, key=lambda row: row.cik))
    families = sorted({row.partition_family_id for row in ordered})
    core_count = sum(row.role == "core" for row in ordered)
    boundary_count = sum(row.role == "boundary" for row in ordered)
    if (
        len(ordered) != 10
        or not 6 <= core_count <= 8
        or not 2 <= boundary_count <= 4
        or len(families) > 2
        or any(
            row.role == "boundary" and not row.boundary_reason for row in ordered
        )
    ):
        raise ValueError(f"Batch {batch_number:02d} violates partition constraints")
    return {
        "partition_version": PARTITION_VERSION,
        "universe_version": "US-SP500-ISSUERS-2026-08-14-1.0",
        "valuation_date": "2026-08-14",
        "batch": batch_number,
        "core_lane": core_lane,
        "core_count": core_count,
        "boundary_count": boundary_count,
        "partition_families": families,
        "members": [row.as_dict() for row in ordered],
    }


def _rare_subindustry_boundaries(
    rows: Sequence[UniverseIssuer], count: int
) -> tuple[list[UniverseIssuer], list[UniverseIssuer]]:
    frequencies: dict[str, int] = {}
    for row in rows:
        frequencies[row.gics_sub_industry] = frequencies.get(row.gics_sub_industry, 0) + 1
    ordered = sorted(
        rows,
        key=lambda row: (
            frequencies[row.gics_sub_industry],
            row.gics_sub_industry,
            row.cik,
        ),
    )
    boundary_ciks = {row.cik for row in ordered[:count]}
    boundary = sorted(
        (row for row in rows if row.cik in boundary_ciks), key=lambda row: row.cik
    )
    core = sorted(
        (row for row in rows if row.cik not in boundary_ciks), key=lambda row: row.cik
    )
    return core, boundary


def _cohort_batches(
    *,
    batch_number: int,
    core_lane: str,
    rows: Sequence[UniverseIssuer],
    imported_boundaries: Sequence[tuple[UniverseIssuer, str]],
    batch_count: int,
) -> tuple[list[dict[str, Any]], int]:
    """Build 8/2 cohorts with rare same-cohort and named imported boundaries."""

    if len(rows) + len(imported_boundaries) != batch_count * 10:
        raise ValueError(f"{core_lane} cohort does not fill {batch_count} batches")
    required_boundaries = batch_count * 2
    own_boundary_count = required_boundaries - len(imported_boundaries)
    if own_boundary_count < 0:
        raise ValueError(f"{core_lane} has too many imported boundaries")
    core, own_boundaries = _rare_subindustry_boundaries(rows, own_boundary_count)
    if len(core) != batch_count * 8:
        raise ValueError(f"{core_lane} core count is not eight per batch")
    boundary_queue = deque(
        sorted(
            [
                *(
                    (row, "same_cohort_rare_subindustry_boundary")
                    for row in own_boundaries
                ),
                *imported_boundaries,
            ],
            key=lambda item: (item[0].cik, item[1]),
        )
    )
    batches = []
    for index in range(batch_count):
        core_chunk = core[index * 8 : (index + 1) * 8]
        boundary_chunk = [boundary_queue.popleft(), boundary_queue.popleft()]
        batches.append(
            _batch(
                batch_number=batch_number,
                core_lane=core_lane,
                members=[
                    *(
                        _member(row, role="core", core_lane=core_lane)
                        for row in core_chunk
                    ),
                    *(
                        _member(
                            row,
                            role="boundary",
                            core_lane=core_lane,
                            boundary_reason=reason,
                        )
                        for row, reason in boundary_chunk
                    ),
                ],
            )
        )
        batch_number += 1
    if boundary_queue:
        raise ValueError(f"{core_lane} boundary queue was not exhausted")
    return batches, batch_number


def build_partition(records: Sequence[UniverseIssuer]) -> tuple[dict[str, Any], ...]:
    """Build all 49 future batches without consulting valuation outcomes."""

    records = tuple(sorted(records, key=lambda row: row.cik))
    if len(records) != 500 or len({row.cik for row in records}) != 500:
        raise ValueError("partition input must be the exact 500-issuer universe")
    batch_01_ciks = {issuer.cik for issuer in BATCH_01_MANIFEST}
    if not batch_01_ciks.issubset({row.cik for row in records}):
        raise ValueError("locked Batch 01 is not a subset of the universe")
    remaining = [row for row in records if row.cik not in batch_01_ciks]
    if len(remaining) != 490:
        raise ValueError("partition must leave exactly 490 future issuers")
    sector_rows = {
        sector: [row for row in remaining if row.gics_sector == sector]
        for sector in sorted(FAMILY_BY_SECTOR)
    }
    actual_counts = {sector: len(rows) for sector, rows in sector_rows.items()}
    if actual_counts != EXPECTED_REMAINING_SECTOR_COUNTS:
        raise ValueError("replacement-universe sector counts changed")

    batches: list[dict[str, Any]] = []
    batch_number = 2

    # Operating cohorts use same-sector rare sub-industries as boundaries.
    # Only seven named cross-sector cases may move, each with an ex-ante
    # business-model reason. This prevents arbitrary CIK-tail leftovers.
    operating_rows = {
        sector: list(sector_rows[sector]) for sector in OPERATING_BATCH_COUNTS
    }
    operating_imports: dict[str, list[tuple[UniverseIssuer, str]]] = {
        sector: [] for sector in OPERATING_BATCH_COUNTS
    }
    for ticker, (destination, reason) in OPERATING_CROSS_BOUNDARIES.items():
        found = [
            row
            for rows in operating_rows.values()
            for row in rows
            if row.ticker == ticker
        ]
        if len(found) != 1:
            raise ValueError(f"named operating boundary {ticker} is unresolved")
        row = found[0]
        operating_rows[row.gics_sector].remove(row)
        operating_imports[destination].append((row, reason))
    for sector in sorted(OPERATING_BATCH_COUNTS):
        built, batch_number = _cohort_batches(
            batch_number=batch_number,
            core_lane=_slug(sector),
            rows=operating_rows[sector],
            imported_boundaries=operating_imports[sector],
            batch_count=OPERATING_BATCH_COUNTS[sector],
        )
        batches.extend(built)

    # Six named asset-backed/resource issuers serve as explicit financial
    # capital-structure boundaries. All other roles remain within cohort.
    financial = list(sector_rows["Financials"])
    resource = sorted(
        [*sector_rows["Energy"], *sector_rows["Materials"]], key=lambda row: row.cik
    )
    imported_financial = []
    for ticker in sorted(FINANCIAL_RESOURCE_BOUNDARIES):
        found = [row for row in resource if row.ticker == ticker]
        if len(found) != 1:
            raise ValueError(f"named financial/resource boundary {ticker} is unresolved")
        row = found[0]
        resource.remove(row)
        imported_financial.append(
            (row, "asset_backed_capital_structure_boundary")
        )
    built, batch_number = _cohort_batches(
        batch_number=batch_number,
        core_lane="financials",
        rows=financial,
        imported_boundaries=imported_financial,
        batch_count=8,
    )
    batches.extend(built)
    built, batch_number = _cohort_batches(
        batch_number=batch_number,
        core_lane="resource_cycle",
        rows=resource,
        imported_boundaries=(),
        batch_count=4,
    )
    batches.extend(built)

    for sector, lane in (("Utilities", "utilities"), ("Real Estate", "real_estate_reit")):
        built, batch_number = _cohort_batches(
            batch_number=batch_number,
            core_lane=lane,
            rows=sector_rows[sector],
            imported_boundaries=(),
            batch_count=3,
        )
        batches.extend(built)

    if len(batches) != 49 or batch_number != 51:
        raise ValueError("partition must produce exactly Batches 02-50")
    assigned = [member["cik"] for batch in batches for member in batch["members"]]
    if len(assigned) != 490 or len(set(assigned)) != 490 or set(assigned) != {
        row.cik for row in remaining
    }:
        raise ValueError("partition is not an exact cover of the remaining universe")
    return tuple(batches)
