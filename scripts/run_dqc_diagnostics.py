#!/usr/bin/env python3
"""Run taxonomy-matched XBRL US DQC rules offline through Xule/Arelle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.dqc_diagnostics import evaluate_dqc


DQC_VERSION = "29.0.6"
XULE_VERSION = "30052"
RULESET_SHA256 = {
    2025: "3833f7fdca869c5ccad16c0ca1cfb3ffa0f90ff30ac3b01ac3a2a4fc8bb02009",
    2026: "ec87e8ecf86c8912cf049667245a4c63efbff0bc26e72fa279b31ed81556b85c",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_manifest(entrypoint: Path, taxonomy_year: int) -> dict[str, Any]:
    path = entrypoint.parent / "package-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("entrypoint_local_path") != entrypoint.name:
        raise ValueError("DQC package entrypoint mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("DQC package file manifest is missing")
    us_gaap_namespaces = {
        str(item.get("taxonomy_namespace"))
        for item in files
        if isinstance(item, dict)
        and isinstance(item.get("taxonomy_namespace"), str)
        and "fasb.org/us-gaap/" in item["taxonomy_namespace"]
    }
    expected_namespace = f"http://fasb.org/us-gaap/{taxonomy_year}"
    if us_gaap_namespaces != {expected_namespace}:
        raise ValueError(
            "DQC primary US-GAAP namespace does not match the requested taxonomy year"
        )
    for item in files:
        candidate = entrypoint.parent / item["local_path"]
        if _sha(candidate) != item["sha256"]:
            raise ValueError("DQC package resource hash mismatch")
    return manifest


def _hydrate_cache(entrypoint: Path, manifest: dict[str, Any], cache_dir: Path) -> None:
    from arelle import Cntlr

    controller = Cntlr.Cntlr(disable_persistent_config=True)
    try:
        controller.webCache.cacheDir = os.fspath(cache_dir)
        for item in manifest["files"]:
            source_url = str(item.get("logical_url") or item["source_url"])
            if not source_url.startswith(("http://", "https://")):
                continue
            source = entrypoint.parent / str(item["local_path"])
            destination = Path(controller.webCache.urlToCacheFilepath(source_url))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    finally:
        controller.close()


def _log_diagnostics(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    root = ET.fromstring(path.read_bytes())
    diagnostics: list[dict[str, str]] = []
    for element in root.iter():
        code = element.attrib.get("code") or element.attrib.get("messageCode")
        if not isinstance(code, str) or not code.startswith("DQC."):
            continue
        level = (element.attrib.get("level") or element.attrib.get("severity") or "warning").lower()
        severity = "error" if "error" in level else "warning" if "warning" in level else "info"
        diagnostics.append(
            {
                "code": code,
                "severity": severity,
                "message": " ".join("".join(element.itertext()).split()),
            }
        )
    return diagnostics


def run_dqc(
    *, entrypoint: Path, taxonomy_year: int, runtime_root: Path
) -> dict[str, Any]:
    entrypoint = Path(entrypoint).resolve()
    runtime_root = Path(runtime_root).resolve()
    manifest = _package_manifest(entrypoint, taxonomy_year)
    ruleset = runtime_root / f"dqc-us-{taxonomy_year}-V29-ruleset.zip"
    xule = runtime_root / f"xule-{XULE_VERSION}/plugin/xule"
    python_runtime = runtime_root / "python"
    expected_sha = RULESET_SHA256.get(taxonomy_year)
    if expected_sha is None or not ruleset.is_file() or _sha(ruleset) != expected_sha:
        evaluation = evaluate_dqc(
            diagnostics=[],
            taxonomy_year=taxonomy_year,
            ruleset_metadata=None,
        )
        return {
            "status": evaluation.status,
            "reason_codes": list(evaluation.reason_codes),
            "diagnostics": [],
            "value": None,
            "can_create_value": False,
        }
    if not xule.is_dir() or not python_runtime.is_dir():
        raise ValueError("Xule runtime is incomplete")

    with tempfile.TemporaryDirectory(prefix="finsight-dqc-") as temp:
        temp_root = Path(temp)
        cache_dir = temp_root / "cache"
        log_path = temp_root / "dqc-log.xml"
        stats_path = temp_root / "rule-stats.json"
        _hydrate_cache(entrypoint, manifest, cache_dir)
        command = [
            sys.executable,
            "-m",
            "arelle.CntlrCmdLine",
            "--disablePersistentConfig",
            f"--plugins={xule}",
            f"--file={entrypoint}",
            "--validate",
            f"--xule-rule-set={ruleset}",
            "--internetConnectivity=offline",
            f"--cacheDirectory={cache_dir}",
            f"--logFile={log_path}",
            "--logFileMode=w",
            f"--xule-rule-stats-file={stats_path}",
        ]
        environment = {
            key: value for key, value in os.environ.items() if not key.startswith("PYTHON")
        }
        environment["PYTHONPATH"] = os.pathsep.join(
            (os.fspath(python_runtime), os.fspath(BACKEND))
        )
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        diagnostics = _log_diagnostics(log_path)
        rule_stats = (
            json.loads(stats_path.read_text(encoding="utf-8"))
            if stats_path.is_file()
            else None
        )
        canonical_rule_stats = (
            [
                {
                    key: item.get(key)
                    for key in (
                        "rule_name", "rule_type", "total", "pass", "skip",
                        "message", "except", "misaligned",
                    )
                }
                for item in rule_stats
                if isinstance(item, dict)
            ]
            if isinstance(rule_stats, list)
            else []
        )
        evaluation = evaluate_dqc(
            diagnostics=diagnostics,
            taxonomy_year=taxonomy_year,
            ruleset_metadata={
                "taxonomy_year": taxonomy_year,
                "ruleset": f"XBRL-US-DQC-{DQC_VERSION}",
            },
        )
        execution_proven = (
            completed.returncode == 0
            and log_path.is_file()
            and bool(canonical_rule_stats)
            and all(
                str(item.get("rule_name") or "").startswith("DQC.US.")
                for item in canonical_rule_stats
            )
        )
        applicable_rule_count = sum(
            1
            for item in canonical_rule_stats
            if int(item.get("total") or 0) > int(item.get("skip") or 0)
        )
        if execution_proven and evaluation.status == "pass" and applicable_rule_count == 0:
            reported_status = "pass_no_applicable_rules"
            reported_reasons = ["DQC_NO_APPLICABLE_ASSERTIONS"]
        else:
            reported_status = evaluation.status if execution_proven else "unavailable"
            reported_reasons = (
                list(evaluation.reason_codes)
                if execution_proven
                else ["DQC_EXECUTION_UNPROVEN"]
            )
        return {
            "status": reported_status,
            "reason_codes": reported_reasons,
            "diagnostics": list(evaluation.diagnostics),
            "value": None,
            "can_create_value": False,
            "taxonomy_year": taxonomy_year,
            "ruleset_version": DQC_VERSION,
            "ruleset_sha256": expected_sha,
            "xule_version": XULE_VERSION,
            "package_generation": manifest.get("generation"),
            "matched_taxonomy_namespace": f"http://fasb.org/us-gaap/{taxonomy_year}",
            "subprocess_returncode": completed.returncode,
            "subprocess_stderr": completed.stderr.strip(),
            "log_present": log_path.is_file(),
            "canonical_log_sha256": hashlib.sha256(
                json.dumps(diagnostics, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if log_path.is_file()
            else None,
            "rule_stats_entry_count": len(canonical_rule_stats),
            "applicable_rule_count": applicable_rule_count,
            "rule_stats_sha256": (
                hashlib.sha256(
                    json.dumps(canonical_rule_stats, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                if canonical_rule_stats
                else None
            ),
            "rule_stats": canonical_rule_stats,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrypoint", required=True, type=Path)
    parser.add_argument("--taxonomy-year", required=True, type=int)
    parser.add_argument("--runtime-root", default=ROOT / "output/dqc-runtime", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run_dqc(
        entrypoint=args.entrypoint,
        taxonomy_year=args.taxonomy_year,
        runtime_root=args.runtime_root,
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output.exists() and args.output.read_text(encoding="utf-8") != encoded:
        raise FileExistsError("refusing to overwrite a different DQC diagnostic")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
