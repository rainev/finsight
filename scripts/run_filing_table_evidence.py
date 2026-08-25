#!/usr/bin/env python3
"""Run deterministic dated-table evidence extraction on an ingestion receipt."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.us_valuation.evidence_field_registry import load_field_registry
from app.us_valuation.filing_tables import extract_numeric_table_evidence
from app.us_valuation.sec_client import normalize_cik


SERVING_ROOTS = (
    ROOT / "backend/app/data/us_valuations",
    ROOT / "frontend/public/data",
    ROOT / "frontend/src/research/generated",
)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if root.exists():
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _packages(root: Path) -> dict[tuple[str, str], Path]:
    result: dict[tuple[str, str], Path] = {}
    for manifest_path in root.rglob("package-manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entrypoint = manifest_path.parent / str(manifest.get("entrypoint_local_path") or "")
        if entrypoint.is_file():
            result.setdefault(
                (normalize_cik(manifest.get("cik", "")), str(manifest.get("accession") or "")),
                entrypoint,
            )
    return result


def run(*, ingestion_receipt: Path, package_root: Path) -> dict[str, Any]:
    receipt = json.loads(ingestion_receipt.read_text(encoding="utf-8"))
    registry = load_field_registry()
    packages = _packages(package_root)
    before = {str(root.resolve()): _tree_hash(root) for root in SERVING_ROOTS}
    issuers: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for issuer in receipt["issuers"]:
        filing = issuer["controlling_filing"]
        entrypoint = packages.get((normalize_cik(issuer["cik"]), filing["accession"]))
        requests = [
            {
                **request,
                "statement_role": (
                    registry[request["required_field"]].statement_roles[0]
                    if request["required_field"] in registry
                    else "balance_sheet"
                ),
            }
            for request in issuer["requests"]
            if request["required_field"] in registry
        ]
        if entrypoint is None:
            issuers.append(
                {
                    "ticker": issuer["ticker"],
                    "cik": issuer["cik"],
                    "status": "package_unavailable",
                    "evidence": [],
                }
            )
            status_counts["package_unavailable"] += len(requests)
            continue
        manifest_path = entrypoint.parent / "package-manifest.json"
        manifest_bytes = manifest_path.read_bytes()
        package_manifest = json.loads(manifest_bytes)
        governed_attachments = package_manifest.get("relevant_attachments")
        complete_attachment_scope = (
            isinstance(governed_attachments, list) and bool(governed_attachments)
        )
        result = extract_numeric_table_evidence(
            "\n".join(
                path.read_text(encoding="utf-8", errors="replace")
                for path in [entrypoint]
                + [
                    entrypoint.parent / item["filename"]
                    for item in package_manifest.get("relevant_attachments", [])
                    if isinstance(item, dict)
                    and isinstance(item.get("filename"), str)
                    and (entrypoint.parent / item["filename"]).is_file()
                    and Path(item["filename"]).suffix.lower() in {".htm", ".html", ".xhtml"}
                ]
            ),
            requests,
            {
                "ticker": issuer["ticker"],
                "cik": issuer["cik"],
                "source_accession": filing["accession"],
                "source_url": next(
                    item.get("source_url")
                    for item in package_manifest["files"]
                    if item.get("local_path") == entrypoint.name
                ),
                "filed_date": filing["filed"],
                "period_end": filing["report_date"],
                "form": filing["form"],
                "entity_identifier": normalize_cik(issuer["cik"]),
                "consolidation_scope": "consolidated_parent",
                "package_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "search_scope_complete": complete_attachment_scope,
                "search_scope_kind": (
                    "complete_governed_package"
                    if complete_attachment_scope
                    else "primary_document_only"
                ),
                "search_scope_hash_salt": [
                    {
                        "local_path": item.get("local_path"),
                        "sha256": item.get("sha256"),
                    }
                    for item in package_manifest["files"]
                    if item.get("local_path") == entrypoint.name
                    or any(
                        isinstance(attachment, dict)
                        and attachment.get("filename") == item.get("local_path")
                        for attachment in package_manifest.get("relevant_attachments", [])
                    )
                ],
            },
        )
        rows = [asdict(item) for item in result.evidence]
        status_counts.update(item["status"] for item in rows)
        issuers.append(
            {
                "ticker": issuer["ticker"],
                "cik": issuer["cik"],
                "status": "searched",
                "complete_search": result.complete_search,
                "scope_kind": result.scope_kind,
                "searched_table_count": result.searched_table_count,
                "search_scope_hash": result.search_scope_hash,
                "evidence": rows,
            }
        )
    after = {str(root.resolve()): _tree_hash(root) for root in SERVING_ROOTS}
    if before != after:
        raise RuntimeError("protected serving artifacts changed during table extraction")
    return {
        "schema_version": "FINSIGHT-FILING-TABLE-EVIDENCE-1",
        "source_ingestion_sha256": hashlib.sha256(ingestion_receipt.read_bytes()).hexdigest(),
        "issuer_count": len(issuers),
        "request_count": sum(len(item.get("evidence", ())) for item in issuers),
        "status_counts": dict(sorted(status_counts.items())),
        "serving_hash_before": before,
        "serving_hash_after": after,
        "serving_artifacts_changed": False,
        "issuers": issuers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ingestion-receipt", required=True, type=Path)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(
        ingestion_receipt=args.ingestion_receipt,
        package_root=args.package_root,
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output.exists() and args.output.read_text(encoding="utf-8") != encoded:
        raise FileExistsError("refusing to overwrite different table evidence")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
