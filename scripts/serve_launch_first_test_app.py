#!/usr/bin/env python3
"""Local-only authenticated test harness for launch-first browser verification."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import uvicorn

from app.main import app
from app.security.jwt import sign_access_token, sign_refresh_token
from app.services import auth_service, feed_service, valuation_service


USER = {
    "id": 7,
    "email": "launch-first@example.com",
    "role": "user",
    "is_verified": True,
}


def _auth_result() -> dict:
    return {
        "user": USER,
        "access_token": sign_access_token(USER["id"], USER["email"], USER["role"]),
        "refresh_token": sign_refresh_token(
            USER["id"], USER["email"], USER["role"], "launch-first-browser"
        ),
    }


auth_service.login = lambda _email, _password: _auth_result()
auth_service.refresh = lambda _token: _auth_result()
auth_service.logout = lambda _token: None
valuation_service.save_us = lambda **_kwargs: {"id": 42}
feed_service.feed_for_user = lambda _user_id, _limit: []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, lifespan="off")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
