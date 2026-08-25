"""Immutable batch-freeze writer contracts."""

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/freeze_universe_batches.py"
SPEC = importlib.util.spec_from_file_location("freeze_universe_batches", SCRIPT)
assert SPEC and SPEC.loader
freeze = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(freeze)


def test_freeze_writes_all_49_batches_and_replays_identically(tmp_path: Path) -> None:
    output = tmp_path / "output"
    config = tmp_path / "config"
    first = freeze.freeze(output_root=output, config_root=config)
    second = freeze.freeze(output_root=output, config_root=config)
    assert first == second
    assert first["future_batch_count"] == 49
    assert len(list(config.glob("batch_*.json"))) == 49
    receipt = json.loads((config / "partition_receipt.json").read_text())
    assert receipt["exact_cover"] == {
        "universe_count": 500,
        "batch_01_count": 10,
        "future_count": 490,
        "pairwise_disjoint": True,
        "all_universe_ciks_covered": True,
    }
