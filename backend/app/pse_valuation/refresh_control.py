"""Invite-only, stage-only control for the existing PSE summary refresh."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from psycopg.errors import UniqueViolation

from ..db import query, query_one
from ..env import env
from ..errors import AppError
from ..services import user_service


MANILA = ZoneInfo("Asia/Manila")
WEEK = timedelta(days=7)
MANUAL_SUCCESS_COOLDOWN = timedelta(hours=24)
MANUAL_RETRY_COOLDOWN = timedelta(minutes=30)


def next_friday(now: datetime) -> datetime:
    """The next 09:00 Manila Friday strictly after now."""
    local = now.astimezone(MANILA)
    days = (4 - local.weekday()) % 7
    due = (local + timedelta(days=days)).replace(hour=9, minute=0, second=0, microsecond=0)
    return due if due > local else due + WEEK


def week_window(now: datetime, first_due: datetime) -> tuple[datetime | None, datetime]:
    """Return the current due window and the next Friday cutoff."""
    due = first_due.astimezone(MANILA)
    local = now.astimezone(MANILA)
    if local < due:
        return None, due
    weeks = int((local - due).total_seconds() // WEEK.total_seconds())
    start = due + weeks * WEEK
    return start, start + WEEK


def access(user: dict) -> tuple[dict, bool]:
    """Recheck the current account, not a stale role/email inside its JWT."""
    owner_email = env.PSE_REFRESH_OWNER_EMAIL
    owner_id = env.PSE_REFRESH_OWNER_USER_ID
    if not owner_email or owner_id <= 0:
        raise AppError("PSE refresh control not found", 404)
    account = user_service.find_by_id(user["sub"])
    if not account:
        raise AppError("PSE refresh control not found", 404)
    owner = account["id"] == owner_id and account["email"].strip().casefold() == owner_email.casefold()
    if not owner and not query_one(
        "SELECT 1 FROM pse_refresh_grants WHERE user_id = %s AND invited_by = %s "
        "AND revoked_at IS NULL",
        (account["id"], owner_id),
    ):
        raise AppError("PSE refresh control not found", 404)
    return account, owner


def _first_due(now: datetime) -> datetime:
    # First authorized visit starts the countdown; restarts never reset it.
    query_one(
        "INSERT INTO pse_refresh_control_settings (id, first_due_at) VALUES (1, %s) "
        "ON CONFLICT (id) DO NOTHING RETURNING first_due_at",
        (next_friday(now),),
    )
    row = query_one("SELECT first_due_at FROM pse_refresh_control_settings WHERE id = 1")
    if row is None:
        raise AppError("PSE refresh schedule is unavailable", 503)
    return row["first_due_at"]


def _job(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "kind": row["kind"],
        "status": row["status"],
        "requested_at": row["requested_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "requested_by": row["requested_by"],
        "result": row["result"],
        "error": row["error"],
    }


def _last_manual() -> dict | None:
    return query_one(
        "SELECT requested_at, status FROM pse_refresh_jobs WHERE kind = 'manual' "
        "ORDER BY id DESC LIMIT 1"
    )


def manual_next_at(now: datetime, last: dict | None) -> datetime | None:
    if last is None:
        return None
    cooldown = MANUAL_SUCCESS_COOLDOWN if last["status"] == "succeeded" else MANUAL_RETRY_COOLDOWN
    due = last["requested_at"] + cooldown
    return due if due > now else None


def status(user: dict, *, now: datetime | None = None) -> dict:
    account, owner = access(user)
    now = now or datetime.now(timezone.utc)
    start, next_cutoff = week_window(now, _first_due(now))
    active = query_one(
        "SELECT id FROM pse_refresh_jobs WHERE status IN ('queued', 'running') "
        "ORDER BY id DESC LIMIT 1"
    )
    completed_this_week = query_one(
        "SELECT id FROM pse_refresh_jobs WHERE window_start = %s "
        "AND kind = 'weekly' AND status = 'succeeded' LIMIT 1",
        (start,),
    ) if start is not None else None
    weekly_due = start is not None and completed_this_week is None
    ready = weekly_due and active is None
    next_manual = manual_next_at(now, _last_manual())
    latest = query_one(
        "SELECT id, kind, status, requested_by, requested_at, started_at, finished_at, result, error "
        "FROM pse_refresh_jobs ORDER BY id DESC LIMIT 1"
    )
    answer = {
        "owner": owner,
        "ready": ready,
        "timezone": "Asia/Manila",
        "next_due_at": (start if weekly_due else next_cutoff).isoformat(),
        "following_friday_at": next_cutoff.isoformat(),
        "active_job": active["id"] if active else None,
        "manual_ready": active is None and next_manual is None,
        "manual_next_at": next_manual.isoformat() if next_manual else None,
        "latest_job": _job(latest),
    }
    if owner:
        answer["invites"] = query(
            "SELECT g.user_id, u.email, g.granted_at FROM pse_refresh_grants g "
            "JOIN users u ON u.id = g.user_id WHERE g.invited_by = %s "
            "AND g.revoked_at IS NULL ORDER BY u.email",
            (account["id"],),
        )
    return answer


def invite(user: dict, email: str) -> dict:
    account, owner = access(user)
    if not owner:
        raise AppError("Only the refresh owner can invite users", 403)
    matches = query(
        "SELECT id, email, is_verified FROM users WHERE lower(email) = lower(%s)",
        (email.strip(),),
    )
    if len(matches) != 1:
        raise AppError("That FinSight account must sign in before it can be invited", 409)
    target = matches[0]
    if target["id"] == account["id"]:
        raise AppError("The owner already has access", 409)
    grant = query_one(
        "INSERT INTO pse_refresh_grants (user_id, invited_by) VALUES (%s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET invited_by = EXCLUDED.invited_by, "
        "granted_at = now(), revoked_at = NULL "
        "RETURNING user_id, granted_at",
        (target["id"], account["id"]),
    )
    return {"user_id": grant["user_id"], "email": target["email"], "granted_at": grant["granted_at"]}


def revoke(user: dict, user_id: int) -> None:
    account, owner = access(user)
    if not owner:
        raise AppError("Only the refresh owner can revoke access", 403)
    changed = query_one(
        "UPDATE pse_refresh_grants SET revoked_at = now() "
        "WHERE user_id = %s AND invited_by = %s AND revoked_at IS NULL RETURNING user_id",
        (user_id, account["id"]),
    )
    if changed is None:
        raise AppError("Refresh invitation not found", 404)


def queue_run(user: dict, *, now: datetime | None = None) -> dict:
    account, _ = access(user)
    now = now or datetime.now(timezone.utc)
    start, _ = week_window(now, _first_due(now))
    if start is None:
        raise AppError("The next PSE refresh is not due yet", 409)
    try:
        job = query_one(
            "INSERT INTO pse_refresh_jobs (requested_by, window_start, status) "
            "VALUES (%s, %s, 'queued') RETURNING id, requested_at",
            (account["id"], start),
        )
    except UniqueViolation as exc:
        raise AppError("A PSE refresh is already queued, running, or completed this week", 409) from exc
    return {"id": job["id"], "status": "queued", "requested_at": job["requested_at"]}


def queue_run_now(user: dict, *, now: datetime | None = None) -> dict:
    """An on-demand stage-only run; it never consumes the Friday slot."""
    account, _ = access(user)
    now = now or datetime.now(timezone.utc)
    due = manual_next_at(now, _last_manual())
    if due is not None:
        raise AppError("Manual PSE refresh is on cooldown", 409)
    try:
        job = query_one(
            "INSERT INTO pse_refresh_jobs (requested_by, window_start, kind, status) "
            "VALUES (%s, %s, 'manual', 'queued') RETURNING id, requested_at",
            (account["id"], now),
        )
    except UniqueViolation as exc:
        raise AppError("A PSE refresh is already queued or running", 409) from exc
    return {"id": job["id"], "status": "queued", "requested_at": job["requested_at"]}
