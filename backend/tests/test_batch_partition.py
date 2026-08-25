"""Deterministic global reset-partition contracts."""

import random

from app.us_valuation.batch_01 import BATCH_01_MANIFEST
from app.us_valuation.batch_partition import _slug, build_partition
from app.us_valuation.universe import load_universe


def test_partition_is_exact_deterministic_and_input_order_independent() -> None:
    universe = load_universe()
    first = build_partition(universe)
    second = build_partition(tuple(reversed(universe)))
    assert first == second
    for seed in range(10):
        shuffled = list(universe)
        random.Random(seed).shuffle(shuffled)
        assert build_partition(shuffled) == first
    assert len(first) == 49
    assert [row["batch"] for row in first] == list(range(2, 51))
    members = [member for batch in first for member in batch["members"]]
    assert len(members) == len({row["cik"] for row in members}) == 490
    assert {row["cik"] for row in members}.isdisjoint(
        {row.cik for row in BATCH_01_MANIFEST}
    )


def test_every_future_batch_satisfies_frozen_composition_rules() -> None:
    for batch in build_partition(load_universe()):
        assert len(batch["members"]) == 10
        assert batch["core_count"] == 8
        assert batch["boundary_count"] == 2
        assert len(batch["partition_families"]) <= 2
        assert batch["members"] == sorted(batch["members"], key=lambda row: row["cik"])
        assert all(
            row["boundary_reason"]
            for row in batch["members"]
            if row["role"] == "boundary"
        )
        assert all(
            row["primary_lane_id"]
            == _slug(row["gics_sector"])
            for row in batch["members"]
        )


def test_batch_02_is_one_real_cohort_with_rare_subindustry_boundaries() -> None:
    batch = build_partition(load_universe())[0]
    assert batch["core_lane"] == "communication_services"
    assert [row["ticker"] for row in batch["members"]] == [
        "OMC",
        "VZ",
        "T",
        "TTWO",
        "NFLX",
        "CHTR",
        "CMCSA",
        "TMUS",
        "META",
        "WBD",
    ]
    assert {
        row["ticker"]: row["boundary_reason"]
        for row in batch["members"]
        if row["role"] == "boundary"
    } == {
        "TTWO": "same_cohort_rare_subindustry_boundary",
        "WBD": "same_cohort_rare_subindustry_boundary",
    }
