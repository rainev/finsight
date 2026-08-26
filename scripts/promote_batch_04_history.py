#!/usr/bin/env python3
"""Atomically promote the confirmed Batch 04 history-backed public artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TARGET = (ROOT / "backend" / "app" / "data" / "us_valuations").resolve()
EXPECTED_TICKERS = ("F", "GPC", "HAS", "LOW", "MCD", "TJX", "NKE", "HD", "ROST", "MGM")
EXPECTED_REPORT_SHA256 = "47cc8b20102597b60cb1ee9109b375d171603bc169cdf814e1d136232d94b969"
CONFIRMATION = "PROMOTE_CONFIRMED_BATCH_04_HISTORY"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode()


def _write_immutable(path: Path, raw: bytes) -> None:
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"immutable evidence differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _atomic_write(path: Path, raw: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".tmp", dir=path.parent)
    stage = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(stage, path)
    finally:
        if stage.exists():
            stage.unlink()


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        path.name: _sha(path.read_bytes())
        for path in sorted(root.glob("*.json"))
        if path.is_file()
    }


def _validate_source(source_root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    report_path = source_root.parent / "history-shadow-report.json"
    if not report_path.is_file():
        raise ValueError("history shadow report is missing")
    report_raw = report_path.read_bytes()
    if _sha(report_raw) != EXPECTED_REPORT_SHA256:
        raise ValueError("history shadow report hash does not match the confirmed candidate")
    report = json.loads(report_raw)
    if (
        tuple(report.get("denominator_tickers", ())) != EXPECTED_TICKERS
        or report.get("pass_count") != 4
        or report.get("conditional_count") != 6
        or report.get("withheld_count") != 0
        or report.get("numeric_count") != 10
        or report.get("serving_artifacts_changed") is not False
        or report.get("watchlist_changed") is not False
    ):
        raise ValueError("history shadow report does not match the confirmed outcome")
    files = sorted(source_root.glob("*.json"))
    if {path.stem for path in files} != set(EXPECTED_TICKERS):
        raise ValueError("history shadow source must contain exactly the ten confirmed tickers")
    payloads: dict[str, bytes] = {}
    for path in files:
        raw = path.read_bytes()
        value = json.loads(raw)
        ticker = path.stem
        if (
            value.get("schema_version") != "US-PUBLIC-VALUATION-1.2"
            or value.get("ticker") != ticker
            or value.get("issuer", {}).get("ticker") != ticker
            or value.get("scenario_range", {}).get("base") is None
            or value.get("availability_type") not in {"available", "conditional_estimate"}
            or value.get("reliability", {}).get("label") not in {"High", "Medium", "Low"}
            or value.get("public_assumptions", {}).get("history_policy_version")
            != "US-COMPANY-HISTORY-1.0"
        ):
            raise ValueError(f"{ticker}: confirmed public artifact contract is invalid")
        forbidden = (
            "company_history_profile",
            "observations",
            "source_manifest",
            "input_provenance",
            "flow_sources",
            "bridge_sources",
        )
        serialized = raw.decode("utf-8")
        if any(token in serialized for token in forbidden):
            raise ValueError(f"{ticker}: private history evidence reached the public artifact")
        payloads[ticker] = raw
    return payloads, report


def promote(
    *,
    source_root: Path,
    target_root: Path,
    evidence_root: Path,
    confirmation: str,
    require_official_target: bool = True,
) -> dict[str, Any]:
    source_root = Path(source_root).resolve(strict=True)
    target_root = Path(target_root).resolve(strict=True)
    evidence_root = Path(evidence_root).resolve()
    if confirmation != CONFIRMATION:
        raise ValueError("explicit Batch 04 history promotion confirmation is required")
    if require_official_target and target_root != EXPECTED_TARGET:
        raise ValueError("promotion target is not the official U.S. valuation serving root")
    if source_root == target_root or evidence_root == target_root or target_root in evidence_root.parents:
        raise ValueError("source, target, and evidence roots must be separate")
    payloads, report = _validate_source(source_root)
    before_hashes = _file_hashes(target_root)
    unrelated_before = {
        name: digest
        for name, digest in before_hashes.items()
        if Path(name).stem not in EXPECTED_TICKERS
    }
    originals = {
        ticker: (target_root / f"{ticker}.json").read_bytes()
        if (target_root / f"{ticker}.json").exists()
        else None
        for ticker in EXPECTED_TICKERS
    }
    backup_manifest = {
        "schema_version": "FINSIGHT-BATCH-04-HISTORY-PROMOTION-BACKUP-1",
        "tickers": list(EXPECTED_TICKERS),
        "preexisting": {
            ticker: originals[ticker] is not None for ticker in EXPECTED_TICKERS
        },
        "before_sha256": {
            ticker: _sha(raw) if raw is not None else None
            for ticker, raw in originals.items()
        },
    }
    for ticker, raw in originals.items():
        if raw is not None:
            _write_immutable(evidence_root / "backup" / f"{ticker}.json", raw)
    _write_immutable(evidence_root / "backup-manifest.json", _json(backup_manifest))

    written: list[str] = []
    try:
        for ticker in EXPECTED_TICKERS:
            _atomic_write(target_root / f"{ticker}.json", payloads[ticker])
            written.append(ticker)
    except Exception:
        for ticker in reversed(written):
            original = originals[ticker]
            path = target_root / f"{ticker}.json"
            if original is None:
                if path.exists():
                    path.unlink()
            else:
                _atomic_write(path, original)
        raise

    after_hashes = _file_hashes(target_root)
    unrelated_after = {
        name: digest
        for name, digest in after_hashes.items()
        if Path(name).stem not in EXPECTED_TICKERS
    }
    if unrelated_before != unrelated_after:
        raise RuntimeError("promotion changed an unrelated serving artifact")
    for ticker, raw in payloads.items():
        if after_hashes.get(f"{ticker}.json") != _sha(raw):
            raise RuntimeError(f"{ticker}: promoted bytes do not match the confirmed candidate")

    receipt = {
        "schema_version": "FINSIGHT-BATCH-04-HISTORY-PROMOTION-RECEIPT-1",
        "source_report_sha256": EXPECTED_REPORT_SHA256,
        "target_root": str(target_root),
        "promoted_tickers": list(EXPECTED_TICKERS),
        "added_tickers": [
            ticker for ticker, raw in originals.items() if raw is None
        ],
        "replaced_tickers": [
            ticker for ticker, raw in originals.items() if raw is not None
        ],
        "pass_count": report["pass_count"],
        "conditional_count": report["conditional_count"],
        "withheld_count": report["withheld_count"],
        "reliability_counts": report["reliability_counts"],
        "before_sha256": backup_manifest["before_sha256"],
        "after_sha256": {
            ticker: after_hashes[f"{ticker}.json"] for ticker in EXPECTED_TICKERS
        },
        "unrelated_serving_artifacts_unchanged": True,
        "backup_root": str(evidence_root / "backup"),
    }
    _write_immutable(evidence_root / "promotion-receipt.json", _json(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    receipt = promote(
        source_root=args.source_root,
        target_root=args.target_root,
        evidence_root=args.evidence_root,
        confirmation=args.confirm,
    )
    print(json.dumps({
        "promoted_count": len(receipt["promoted_tickers"]),
        "added_tickers": receipt["added_tickers"],
        "replaced_tickers": receipt["replaced_tickers"],
        "pass_count": receipt["pass_count"],
        "conditional_count": receipt["conditional_count"],
        "withheld_count": receipt["withheld_count"],
        "unrelated_serving_artifacts_unchanged": receipt[
            "unrelated_serving_artifacts_unchanged"
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
