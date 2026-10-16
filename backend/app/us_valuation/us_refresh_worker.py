"""Process invite-only U.S. refresh requests without touching active.json.

The local worker waits for queued jobs; it never polls SEC while idle. A fixed
source-bounded runner in the isolated US worktree checks filings and stages only
supported successors. Neither this worker nor its result calls activation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from collections import Counter
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .catalog import load_active_catalog


log = logging.getLogger(__name__)
_CODE_ROOT = Path(os.environ.get("US_REFRESH_CODE_ROOT", Path(__file__).resolve().parents[3]))


def _default_worktree_root() -> Path:
    """Use the original repository worktree unless an isolated test overrides it."""

    # The prepared copy is ROOT/output/.../public-staged-quality/prepared-code/main.
    # Resolve back to ROOT only from that recognizable layout; deployed copies
    # retain the container mount fallback and never guess a live source path.
    if _CODE_ROOT.name == "main" and _CODE_ROOT.parent.name == "prepared-code":
        try:
            return _CODE_ROOT.parents[4] / ".worktrees/whole-universe-greenlight"
        except IndexError:
            pass
    return Path("/us-worktree")


_CODE_WT = Path(os.environ.get("US_REFRESH_CODE_WT", _default_worktree_root()))
_DEFAULT_RUNNER = _CODE_WT / "scripts" / "run_us_500_stage_cycle.py"
RUNNER = Path(os.environ.get("US_REFRESH_RUNNER", _DEFAULT_RUNNER))
RUNTIME_ROOT = Path(os.environ.get("US_REFRESH_RUNTIME_ROOT", "/us-runtime"))
CATALOGS_ROOT = Path(os.environ.get("US_REFRESH_CATALOGS_ROOT", "/us-catalogs"))
PRIVATE_ROOT = Path(os.environ.get("US_REFRESH_DATA_DIR", "/data"))
UA_CONFIG = Path(os.environ.get("US_REFRESH_UA_CONFIG", "/us-config/runtime-config.json"))


def safe_result(report: dict) -> dict:
    """Return only derived status and selected names, never source packets."""
    counts = report["counts"]
    held = sorted(row["ticker"] for row in report["rows"]
                  if row["outcome"] == "held_new_filing")
    candidate = report.get("candidate")
    return {
        "selected_count": report["selected_count"],
        "catalog_count": report["catalog_count"],
        "changed_regular_count": report["changed_regular_count"],
        "summary_checks": {name: int(counts.get(name, 0)) for name in
                           ("source_bound", "held_new_filing", "checked_unchanged", "prior_unavailable")},
        "staged_intrinsic_count": int(counts.get("source_bound", 0)),
        "held_count": len(held),
        "held_tickers_preview": held[:20],
        "candidate": ({"version": candidate["version"],
                       "manifest_sha256": candidate["manifest_sha256"]}
                      if candidate else None),
        "active_changed": report["active_changed"],
    }


def claim_job(conn: psycopg.Connection) -> dict | None:
    return conn.execute(
        "UPDATE us_refresh_jobs SET status = 'running', started_at = now() "
        "WHERE id = (SELECT id FROM us_refresh_jobs WHERE status = 'queued' "
        "ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id, requested_by"
    ).fetchone()


def validate_complete_report(report: dict) -> None:
    """Every approved issuer must have exactly one recorded outcome."""
    count = report["catalog_count"]
    rows = report["rows"]
    tickers = [row["ticker"] for row in rows]
    outcomes = Counter(row["outcome"] for row in rows)
    if (
        type(count) is not int or count <= 0
        or report["selected_count"] != count
        or len(rows) != count or len(set(tickers)) != count
        or dict(outcomes) != {key: value for key, value in report["counts"].items() if value}
        or set(outcomes) - {"source_bound", "held_new_filing", "checked_unchanged", "prior_unavailable"}
        or report["active_changed"] is not False
    ):
        raise ValueError("US refresh failed to preserve the complete inactive catalog")


def validate_quality06_retention_report(report: dict) -> None:
    """Quality06 is a filing-hold/status child, never a source-bound refresh."""

    validate_complete_report(report)
    if any(row["outcome"] == "source_bound" for row in report["rows"]):
        raise ValueError("Quality06 retention cannot stage source-bound recalculations")
    if report.get("auto_revaluation") is not False:
        raise ValueError("Quality06 retention must disable automatic revaluation")
    if report.get("new_filing_policy") != "hold_before_capture":
        raise ValueError("Quality06 new filing policy must hold before capture")


def run_once(*, catalogs_root: Path = CATALOGS_ROOT,
             runtime_root: Path = RUNTIME_ROOT, private_root: Path = PRIVATE_ROOT,
             runner: Path = RUNNER, ua_config: Path = UA_CONFIG,
             cutoff: str | None = None) -> dict:
    if not runner.is_file() or not (runtime_root / "registry.json").is_file():
        raise RuntimeError("US source-bound refresh runner or frozen registry is unavailable")
    if not (catalogs_root / "active.json").is_file():
        raise RuntimeError("US active catalog pointer is unavailable as a read-only input")
    pointer = (catalogs_root / "active.json").read_bytes()
    active = load_active_catalog(catalogs_root)
    inheritance = active.manifest.get("approved_base_inheritance", {}).get("schema_version")
    if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {'US-QUALITY03-OFFLINE-RETENTION-CHILD-1','US-QUALITY03-ADMITTED-RETENTION-CHILD-1'}:
        raise RuntimeError('Quality03 verification-only child cannot start another source cycle')
    if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {'US-QUALITY02-OFFLINE-RETENTION-CHILD-1','US-QUALITY02-ADMITTED-RETENTION-CHILD-1'}:
        raise RuntimeError('Quality02 verification-only child cannot start another source cycle')
    env = os.environ.copy()
    offline_root = env.get("US_REFRESH_OFFLINE_SOURCE_ROOT")
    if active.manifest.get('approved_base_inheritance', {}).get('schema_version') == 'US-B1620-LOCAL-ADMISSION-INHERITANCE-1':
        from .admitted_batches1620 import validate_catalog
        validate_catalog(active.root, active.manifest, runtime=runtime_root)
    if active.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1':
        if not offline_root or env.get('APP_ENV') != 'test':
            raise RuntimeError('staged700 worker requires isolated offline replay; no live source authority')
        from .staged_batches1620 import validate_catalog
        validate_catalog(active.root, active.manifest, runtime=runtime_root)
    if active.manifest.get('private_review', {}).get('profile') == 'B16-B20-FROZEN-PRIVATE-1':
        if not offline_root or env.get('APP_ENV') != 'test':
            raise RuntimeError('private700 worker requires isolated offline replay; no live source authority')
        from .private_batches1620 import validate_catalog
        validate_catalog(active.root, active.manifest, runtime=runtime_root)
    if (active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY03-STAGED-INHERITANCE-1'
            and (not offline_root or env.get('APP_ENV') != 'test')):
        raise RuntimeError('Quality03 staged worker requires isolated offline replay; no live source authority')
    if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {'US-QUALITY04-OFFLINE-RETENTION-CHILD-1','US-QUALITY04-ADMITTED-RETENTION-CHILD-1'}:
        raise RuntimeError('Quality04 verification-only child cannot start another source cycle')
    if active.manifest.get('approved_base_inheritance',{}).get('schema_version') in {'US-QUALITY05-OFFLINE-RETENTION-CHILD-1','US-QUALITY05-ADMITTED-RETENTION-CHILD-1'}:
        raise RuntimeError('Quality05 verification-only child cannot start another source cycle')
    if inheritance in {'US-QUALITY06-OFFLINE-RETENTION-CHILD-1','US-QUALITY06-ADMITTED-RETENTION-CHILD-1'}:
        raise RuntimeError('Quality06 verification-only child cannot start another source cycle')
    if (active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY05-STAGED-INHERITANCE-1'
            and (not offline_root or env.get('APP_ENV') != 'test')):
        raise RuntimeError('Quality05 staged worker requires isolated offline replay; no live source authority')
    if inheritance == 'US-QUALITY06-STAGED-INHERITANCE-1' and (not offline_root or env.get('APP_ENV') != 'test'):
        raise RuntimeError('Quality06 staged worker requires isolated offline replay; no live source authority')
    if (active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY04-STAGED-INHERITANCE-1'
            and (not offline_root or env.get('APP_ENV') != 'test')):
        raise RuntimeError('Quality04 staged worker requires isolated offline replay; no live source authority')
    if ((active.manifest.get('private_review', {}).get('profile') == 'B11-B15-FROZEN-PRIVATE-1'
            or active.manifest.get('approved_base_inheritance', {}).get('schema_version') in {'US-B11-B15-APPROVED-PARENT-INHERITANCE-1','US-B1115-QUALITY-STAGED-INHERITANCE-1','US-B1115-QUALITY-RETENTION-CHILD-1'})
            and (not offline_root or env.get('APP_ENV') != 'test')):
        raise RuntimeError('private650 worker requires isolated offline replay; staged650 also prohibits live SEC capture')
    if offline_root:
        if (active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-STAGED-INHERITANCE-1'
                and env.get('APP_ENV') != 'test'):
            raise RuntimeError('Quality02 stage requires isolated offline replay')
        if env.get("APP_ENV") != "test":
            raise RuntimeError("offline US source replay is available only in isolated tests")
    else:
        if active.manifest.get('approved_base_inheritance',{}).get('schema_version') == 'US-QUALITY02-STAGED-INHERITANCE-1':
            raise RuntimeError('Quality02 staged worker has no live source authority')
        if not env.get("SEC_USER_AGENT"):
            config = json.loads(ua_config.read_bytes())
            if config.get("schema_version") != "FINSIGHT-US-REFRESH-RUNTIME-1":
                raise ValueError("US monitored SEC contact configuration is invalid")
            env["SEC_USER_AGENT"] = config["sec_user_agent"]
        if "@" not in env["SEC_USER_AGENT"]:
            raise ValueError("US monitored SEC contact is required")
    private_root.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, str(runner),
        "--catalogs-root", str(catalogs_root),
        "--runtime-root", str(runtime_root),
        "--state-root", str(private_root),
        "--as-of", cutoff or datetime.now(timezone.utc).date().isoformat(),
    ]
    if offline_root:
        command.extend(["--offline-source-root", offline_root])
    completed = subprocess.run(command, env=env, capture_output=True, text=True,
                               timeout=7200, check=False)
    if completed.returncode != 0:
        # The private log stays in this worker; API errors stay generic.
        log.error("US stage runner failed (%s): %s", completed.returncode,
                  completed.stderr[-2000:])
        raise RuntimeError("US stage runner failed; inspect the private worker log")
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    report_path = Path(report["private_report_path"]).resolve()
    if not report_path.is_relative_to((private_root / "reports").resolve()):
        raise RuntimeError("US stage runner returned an unsafe private report path")
    private = json.loads(report_path.read_bytes())
    if private["base_manifest_sha256"] != report["base_manifest_sha256"]:
        raise RuntimeError("US stage report identity mismatch")
    if inheritance == 'US-QUALITY06-STAGED-INHERITANCE-1':
        validate_quality06_retention_report(private)
    else:
        validate_complete_report(private)
    if (
        private["base_manifest_sha256"] != active.manifest_sha256
        or private["catalog_count"] != len(active.entries)
        or {row["ticker"] for row in private["rows"]} != {entry.ticker for entry in active.entries}
        or (catalogs_root / "active.json").read_bytes() != pointer
    ):
        raise RuntimeError("US stage report differs from the approved active catalog")
    if active.manifest.get('private_review', {}).get('profile') == 'B16-B20-FROZEN-PRIVATE-1':
        from .private_batches1620 import anchors
        if any(row['outcome'] == 'source_bound' for row in private['rows'] if row['ticker'] in anchors()['new_identities']):
            raise RuntimeError('private700 cannot revalue frozen expansion companies')
    if active.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1':
        from .staged_batches1620 import anchors
        if any(r['outcome'] == 'source_bound' for r in private['rows'] if r['ticker'] in anchors()['new_identities']):
            raise RuntimeError('staged700 cannot revalue frozen additions')
    return private


def process_job(conn: psycopg.Connection, job: dict, *, private_root: Path = PRIVATE_ROOT) -> None:
    try:
        report = run_once(private_root=private_root)
        validate_complete_report(report)
        result = safe_result(report)
        conn.execute(
            "UPDATE us_refresh_jobs SET status = 'succeeded', finished_at = now(), "
            "result = %s WHERE id = %s AND status = 'running'",
            (Jsonb(result), job["id"]),
        )
        log.info("US stage-only refresh %s completed: %s", job["id"],
                 json.dumps({"checked": result["selected_count"], "staged": result["staged_intrinsic_count"],
                             "held": result["held_count"]}))
    except Exception:
        log.exception("US stage-only refresh %s failed", job["id"])
        conn.execute(
            "UPDATE us_refresh_jobs SET status = 'failed', finished_at = now(), "
            "error = 'US refresh failed; check the private worker log' "
            "WHERE id = %s AND status = 'running'", (job["id"],),
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            with psycopg.connect(
                host=os.environ["PGHOST"], port=os.environ["PGPORT"],
                user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
                dbname=os.environ["PGDATABASE"], autocommit=True, row_factory=dict_row,
            ) as conn:
                conn.execute(
                    "UPDATE us_refresh_jobs SET status = 'failed', finished_at = now(), "
                    "error = 'US refresh worker stopped before completion' "
                    "WHERE status = 'running' AND started_at < now() - interval '2 hours'"
                )
                while True:
                    job = claim_job(conn)
                    if job:
                        process_job(conn, job)
                    else:
                        time.sleep(5)
        except (psycopg.Error, OSError):
            log.exception("US refresh worker cannot reach its job table; retrying")
            time.sleep(10)


if __name__ == "__main__":
    main()
