"""Invite-only Friday/on-demand controls for stage-only U.S. 500 refresh jobs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from psycopg.errors import UniqueViolation

from ..db import query, query_one
from ..env import env
from ..errors import AppError
from ..pse_valuation.refresh_control import next_friday, week_window
from ..services import user_service


MANUAL_SUCCESS_COOLDOWN = timedelta(hours=24)
MANUAL_RETRY_COOLDOWN = timedelta(minutes=30)


def access(user: dict) -> tuple[dict, bool]:
    """Use current account identity; PSE grants do not authorize U.S. access."""
    owner_email = env.PSE_REFRESH_OWNER_EMAIL
    owner_id = env.PSE_REFRESH_OWNER_USER_ID
    if not env.US_REFRESH_CONTROL_ENABLED or not owner_email or owner_id <= 0:
        raise AppError("US refresh control not found", 404)
    account = user_service.find_by_id(user["sub"])
    if not account:
        raise AppError("US refresh control not found", 404)
    owner = account["id"] == owner_id and account["email"].strip().casefold() == owner_email.casefold()
    if not owner and not query_one(
        "SELECT 1 FROM us_refresh_grants WHERE user_id = %s AND invited_by = %s "
        "AND revoked_at IS NULL", (account["id"], owner_id),
    ):
        raise AppError("US refresh control not found", 404)
    return account, owner


def _first_due(now: datetime) -> datetime:
    query_one(
        "INSERT INTO us_refresh_control_settings (id, first_due_at) VALUES (1, %s) "
        "ON CONFLICT (id) DO NOTHING RETURNING first_due_at", (next_friday(now),),
    )
    row = query_one("SELECT first_due_at FROM us_refresh_control_settings WHERE id = 1")
    if row is None:
        raise AppError("US refresh schedule is unavailable", 503)
    return row["first_due_at"]


def _last_manual() -> dict | None:
    return query_one(
        "SELECT requested_at, status FROM us_refresh_jobs WHERE kind = 'manual' "
        "ORDER BY id DESC LIMIT 1"
    )


def manual_next_at(now: datetime, last: dict | None) -> datetime | None:
    if last is None:
        return None
    due = last["requested_at"] + (
        MANUAL_SUCCESS_COOLDOWN if last["status"] == "succeeded" else MANUAL_RETRY_COOLDOWN
    )
    return due if due > now else None


def _job(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in (
        "id", "kind", "status", "requested_by", "requested_at", "started_at",
        "finished_at", "result", "error",
    )}


def status(user: dict, *, now: datetime | None = None) -> dict:
    account, owner = access(user)
    now = now or datetime.now(timezone.utc)
    start, next_cutoff = week_window(now, _first_due(now))
    active = query_one(
        "SELECT id FROM us_refresh_jobs WHERE status IN ('queued', 'running') "
        "ORDER BY id DESC LIMIT 1"
    )
    completed = query_one(
        "SELECT id FROM us_refresh_jobs WHERE window_start = %s AND kind = 'weekly' "
        "AND status = 'succeeded' LIMIT 1", (start,),
    ) if start is not None else None
    weekly_due = start is not None and completed is None
    manual_due = manual_next_at(now, _last_manual())
    latest = query_one(
        "SELECT id, kind, status, requested_by, requested_at, started_at, "
        "finished_at, result, error FROM us_refresh_jobs ORDER BY id DESC LIMIT 1"
    )
    answer = {
        "owner": owner, "ready": weekly_due and active is None,
        "timezone": "Asia/Manila",
        "next_due_at": (start if weekly_due else next_cutoff).isoformat(),
        "following_friday_at": next_cutoff.isoformat(),
        "active_job": active["id"] if active else None,
        "manual_ready": active is None and manual_due is None,
        "manual_next_at": manual_due.isoformat() if manual_due else None,
        "latest_job": _job(latest),
    }
    if owner:
        answer["invites"] = query(
            "SELECT g.user_id, u.email, g.granted_at FROM us_refresh_grants g "
            "JOIN users u ON u.id = g.user_id WHERE g.invited_by = %s "
            "AND g.revoked_at IS NULL ORDER BY u.email", (account["id"],),
        )
    return answer


def invite(user: dict, email: str) -> dict:
    account, owner = access(user)
    if not owner:
        raise AppError("Only the US refresh owner can invite users", 403)
    matches = query(
        "SELECT id, email FROM users WHERE lower(email) = lower(%s)", (email.strip(),),
    )
    if len(matches) != 1:
        raise AppError("That FinSight account must sign in before it can be invited", 409)
    target = matches[0]
    if target["id"] == account["id"]:
        raise AppError("The owner already has access", 409)
    grant = query_one(
        "INSERT INTO us_refresh_grants (user_id, invited_by) VALUES (%s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET invited_by = EXCLUDED.invited_by, "
        "granted_at = now(), revoked_at = NULL RETURNING user_id, granted_at",
        (target["id"], account["id"]),
    )
    return {"user_id": grant["user_id"], "email": target["email"],
            "granted_at": grant["granted_at"]}


def revoke(user: dict, user_id: int) -> None:
    account, owner = access(user)
    if not owner:
        raise AppError("Only the US refresh owner can revoke access", 403)
    changed = query_one(
        "UPDATE us_refresh_grants SET revoked_at = now() "
        "WHERE user_id = %s AND invited_by = %s AND revoked_at IS NULL RETURNING user_id",
        (user_id, account["id"]),
    )
    if changed is None:
        raise AppError("US refresh invitation not found", 404)


def queue_run(user: dict, *, now: datetime | None = None) -> dict:
    account, _ = access(user)
    now = now or datetime.now(timezone.utc)
    start, _ = week_window(now, _first_due(now))
    if start is None:
        raise AppError("The next US refresh is not due yet", 409)
    try:
        job = query_one(
            "INSERT INTO us_refresh_jobs (requested_by, window_start, kind, status) "
            "VALUES (%s, %s, 'weekly', 'queued') RETURNING id, requested_at",
            (account["id"], start),
        )
    except UniqueViolation as exc:
        raise AppError("A US refresh is already queued, running, or completed this week", 409) from exc
    return {"id": job["id"], "status": "queued", "requested_at": job["requested_at"]}


def queue_run_now(user: dict, *, now: datetime | None = None) -> dict:
    """On-demand staging does not consume or reset the Friday window."""
    account, _ = access(user)
    now = now or datetime.now(timezone.utc)
    if manual_next_at(now, _last_manual()) is not None:
        raise AppError("Manual US refresh is on cooldown", 409)
    try:
        job = query_one(
            "INSERT INTO us_refresh_jobs (requested_by, window_start, kind, status) "
            "VALUES (%s, %s, 'manual', 'queued') RETURNING id, requested_at",
            (account["id"], now),
        )
    except UniqueViolation as exc:
        raise AppError("A US refresh is already queued or running", 409) from exc
    return {"id": job["id"], "status": "queued", "requested_at": job["requested_at"]}
