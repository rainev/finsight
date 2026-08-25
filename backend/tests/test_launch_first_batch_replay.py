from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.replay_launch_first_batches import run


BATCH_ROOTS = {
    1: Path("output/batch-01-recovery/final-confirmation-a"),
    2: Path("output/batch-02-conditional/verified-run-a"),
    3: Path("output/launch-first/batch-03-run-g"),
}


def test_launch_first_replay_has_exact_30_company_coverage(tmp_path: Path) -> None:
    report = run(batch_roots=BATCH_ROOTS, output_root=tmp_path / "replay")

    assert report["issuer_count"] == 30
    assert report["unique_ticker_count"] == 30
    assert report["numeric_count"] == 27
    assert report["not_available_count"] == 3
    assert report["conditional_count"] == 11
    assert report["relative_baseline_count"] == 0
    assert report["market_comparison_available_count"] == 0
    assert report["serving_artifacts_changed"] is False
    assert {row["ticker"] for row in report["cases"] if not row["numeric"]} == {
        "ECHO",
        "NEE",
        "PSKY",
    }


def test_launch_first_replay_is_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run(batch_roots=BATCH_ROOTS, output_root=first)
    run(batch_roots=BATCH_ROOTS, output_root=second)
    left = {path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()}
    right = {path.relative_to(second): path.read_bytes() for path in second.rglob("*") if path.is_file()}
    assert left == right
