#!/usr/bin/env python3
"""Replay evidence-aware bridge policy without changing serving artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping


_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_DIR = _REPO_ROOT / "backend"
_SERVING_ROOTS = (
    _BACKEND_DIR / "app" / "data" / "us_valuation_catalogs",
    _REPO_ROOT / "frontend" / "public" / "data",
)
_JSON_NAME = "bridge-policy-shadow.json"
_MARKDOWN_NAME = "bridge-policy-shadow.md"
_LOCK_NAME = ".bridge-policy-shadow.lock"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--tickers",
        help="optional comma-separated canonical tickers",
    )
    return parser


def _is_within(path: Path, root: Path) -> bool:
    if path == root or path.is_relative_to(root):
        return True
    current = path
    while True:
        try:
            current.stat()
        except FileNotFoundError:
            parent = current.parent
            if parent == current:
                return False
            current = parent
            continue
        except OSError as error:
            raise ValueError(
                f"cannot validate output path identity: {type(error).__name__}"
            ) from error
        break
    while True:
        try:
            if os.path.samefile(current, root):
                return True
        except OSError as error:
            raise ValueError(
                f"cannot validate protected path identity: {type(error).__name__}"
            ) from error
        parent = current.parent
        if parent == current:
            return False
        current = parent


def validate_paths(
    input_root: str | Path, output_dir: str | Path
) -> tuple[Path, Path]:
    """Resolve aliases before enforcing input and serving-root boundaries."""

    resolved_input = Path(input_root).resolve(strict=True)
    if not resolved_input.is_dir():
        raise ValueError("input root must resolve to a directory")
    resolved_output = Path(output_dir).resolve(strict=False)
    if _is_within(resolved_output, resolved_input):
        raise ValueError("output directory must not equal or be inside the input root")
    for serving_root in _SERVING_ROOTS:
        if _is_within(resolved_output, serving_root.resolve(strict=False)):
            raise ValueError("output directory must not equal or be inside a serving root")
    return resolved_input, resolved_output


def _parse_tickers(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    tickers = tuple(part.strip() for part in raw.split(","))
    if not tickers or any(not ticker for ticker in tickers):
        raise ValueError("--tickers must contain nonempty comma-separated symbols")
    return tickers


def _format_values(values: list[str]) -> str:
    return ", ".join(values) if values else "—"


def _format_counter(counter: Mapping[str, Any]) -> str:
    return (
        ", ".join(f"{key}={counter[key]}" for key in sorted(counter))
        if counter
        else "—"
    )


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(summary: Mapping[str, Any]) -> str:
    """Render the deterministic human-readable companion to the JSON report."""

    lines = [
        "# Evidence-aware bridge policy shadow replay",
        "",
        f"- Artifact candidates: {summary['artifact_count']}",
        f"- Valid private artifacts: {summary['valid_artifact_count']}",
        f"- Invalid/error artifacts: {summary['invalid_artifact_count']}",
        f"- Decision counts: {_format_counter(summary['decision_counts'])}",
        f"- Blocker frequencies: {_format_counter(summary['blocker_frequencies'])}",
        (
            "- Bounded-field frequencies: "
            f"{_format_counter(summary['bounded_field_frequencies'])}"
        ),
        f"- Field-state counts: {_format_counter(summary['state_counts'])}",
        (
            "- Reason-code frequencies: "
            f"{_format_counter(summary['reason_code_frequencies'])}"
        ),
        f"- Serving artifacts changed: {summary['serving_artifacts_changed']}",
        f"- Requested tickers: {_format_values(summary['requested_tickers'])}",
        f"- Matched tickers: {_format_values(summary['matched_tickers'])}",
        f"- Missing tickers: {_format_values(summary['missing_tickers'])}",
        f"- Duplicate tickers: {_format_values(summary['duplicate_tickers'])}",
        (
            "- Evidence gate passed: "
            f"{str(summary['evidence_gate_passed']).lower()}"
        ),
        "",
        (
            "| Ticker | Source path | Legacy missing fields | "
            "Evidence-aware blockers | Bounded fields | Decision | Error |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in summary["cases"]:
        error = case.get("error")
        error_code = error.get("reason_code") if isinstance(error, Mapping) else None
        values = (
            case["ticker"],
            case["source_path"],
            _format_values(case["legacy"]["bridge_missing_fields"]),
            _format_values(case["evidence_aware"]["blocking_fields"]),
            _format_values(case["evidence_aware"]["bounded_fields"]),
            case["evidence_aware"]["decision"],
            error_code or "—",
        )
        lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def _json_bytes(summary: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _stage_payload(path: Path, payload: bytes) -> Path:
    descriptor, raw_temp = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def _publish_no_clobber(staged: Path, target: Path) -> None:
    try:
        os.link(staged, target)
    except FileExistsError as error:
        raise RuntimeError(
            f"Refusing concurrent output publication: {target}"
        ) from error


def _rollback_created(
    created: list[tuple[Path, Path]],
) -> None:
    for target, staged in reversed(created):
        try:
            if target.exists() and os.path.samefile(target, staged):
                target.unlink()
        except OSError:
            continue


def write_outputs(
    output_dir: Path, summary: Mapping[str, Any], markdown: str
) -> None:
    """Publish an immutable pair with exclusive no-clobber staging."""

    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / _LOCK_NAME
    try:
        lock_descriptor = os.open(
            lock_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as error:
        raise RuntimeError("bridge-policy shadow output is already running") from error
    try:
        with os.fdopen(lock_descriptor, "w", encoding="utf-8") as lock:
            lock.write(f"pid={os.getpid()}\n")
            lock.flush()
            os.fsync(lock.fileno())
    except BaseException:
        lock_path.unlink(missing_ok=True)
        raise

    targets = {
        output_dir / _JSON_NAME: _json_bytes(summary),
        output_dir / _MARKDOWN_NAME: markdown.encode("utf-8"),
    }
    staged: dict[Path, Path] = {}
    created: list[tuple[Path, Path]] = []
    try:
        for path, payload in targets.items():
            if path.exists() and path.read_bytes() != payload:
                raise RuntimeError(f"Refusing to overwrite immutable output: {path}")
        for path, payload in targets.items():
            if not path.exists():
                staged[path] = _stage_payload(path, payload)
        try:
            for target, staged_path in staged.items():
                _publish_no_clobber(staged_path, target)
                created.append((target, staged_path))
        except BaseException:
            _rollback_created(created)
            raise
    finally:
        for staged_path in staged.values():
            staged_path.unlink(missing_ok=True)
        lock_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        input_root, output_dir = validate_paths(args.input_root, args.output_dir)
        tickers = _parse_tickers(args.tickers)
        sys.path.insert(0, str(_BACKEND_DIR))
        from app.us_valuation.bridge_policy_shadow import evaluate_corpus

        summary = evaluate_corpus(input_root, tickers=tickers)
        markdown = render_markdown(summary)
        output_dir.mkdir(parents=True, exist_ok=True)
        input_root, output_dir = validate_paths(input_root, output_dir)
        write_outputs(output_dir, summary, markdown)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print(
        f"wrote {_JSON_NAME} and {_MARKDOWN_NAME} to {output_dir}",
        file=sys.stdout,
    )
    if not summary["evidence_gate_passed"]:
        print("evidence gate failed; diagnostics written", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
