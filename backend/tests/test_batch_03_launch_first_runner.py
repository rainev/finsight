from __future__ import annotations

import json
from pathlib import Path
import sys

from app.us_valuation.artifacts import sanitize_public_artifact

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_batch_03_launch_first import run


PRIOR_ROOT = Path("output/batch-03-controlled/candidate-g")
SOURCE_ROOT = Path("output/batch-03-sec-source-packets-20260824")
STRUCTURAL_ROOT = Path("output/batch-03-structural-sources-20260824")


def test_launch_first_runner_stages_eight_numeric_without_serving_writes(
    tmp_path: Path,
) -> None:
    output = tmp_path / "launch-first"
    report = run(
        prior_root=PRIOR_ROOT,
        source_root=SOURCE_ROOT,
        structural_root=STRUCTURAL_ROOT,
        output_root=output,
    )

    assert report["attempted_count"] == 10
    assert report["numeric_count"] == 8
    assert report["conditional_numeric_count"] == 5
    assert report["not_available_count"] == 2
    assert report["serving_artifacts_changed"] is False
    assert report["watchlist_changed"] is False
    assert report["withheld_count"] == 0
    assert {row["ticker"] for row in report["cases"] if row["outcome"] == "not_available"} == {"ECHO", "PSKY"}

    for path in sorted((output / "staged-public").glob("*.json")):
        raw = json.loads(path.read_text())
        public = sanitize_public_artifact(raw)
        assert public == raw
        encoded = json.dumps(public)
        assert "reported_inputs" not in encoded
        assert "source_ledger" not in encoded
        assert "governed_assumptions" not in encoded
        assert "split_adjusted_close" not in encoded
        if path.stem in {"ECHO", "PSKY"}:
            assert public["availability_type"] == "not_available"
            assert public["scenario_range"]["base"] is None
        else:
            assert public["scenario_range"]["base"] is not None
        if path.stem == "APP":
            assumptions = public["public_assumptions"]
            assert assumptions["unresolved_claims_reserve_bear"] > assumptions[
                "unresolved_claims_reserve_base"
            ] > assumptions["unresolved_claims_reserve_bull"]
        if path.stem == "TKO":
            assert public["public_assumptions"]["nci_share_reconciled"] is True


def test_launch_first_runner_is_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    arguments = {
        "prior_root": PRIOR_ROOT,
        "source_root": SOURCE_ROOT,
        "structural_root": STRUCTURAL_ROOT,
    }
    run(output_root=first, **arguments)
    run(output_root=second, **arguments)

    first_files = {
        path.relative_to(first): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files
