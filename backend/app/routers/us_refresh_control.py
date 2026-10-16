"""Authenticated, invite-only US 500-company staged-refresh controls."""

from fastapi import APIRouter, status
from pydantic import BaseModel, EmailStr

from ..deps import CurrentUser
from ..us_valuation import us_refresh_control


router = APIRouter(prefix="/us-refresh-control", tags=["us-refresh-control"])


class InviteRequest(BaseModel):
    email: EmailStr


@router.get("/status")
def get_status(user: CurrentUser) -> dict:
    return us_refresh_control.status(user)


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def queue_staged_refresh(user: CurrentUser) -> dict:
    return us_refresh_control.queue_run(user)


@router.post("/run-now", status_code=status.HTTP_202_ACCEPTED)
def queue_manual_staged_refresh(user: CurrentUser) -> dict:
    return us_refresh_control.queue_run_now(user)


@router.post("/invites", status_code=status.HTTP_201_CREATED)
def invite_user(body: InviteRequest, user: CurrentUser) -> dict:
    return us_refresh_control.invite(user, str(body.email))


@router.delete("/invites/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_user(user_id: int, user: CurrentUser) -> None:
    us_refresh_control.revoke(user, user_id)
