"""Versioned business-economics routing for the Phase A pilot."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).with_name("config") / "pilot_routes.json"


@lru_cache(maxsize=1)
def load_routes() -> dict[str, Any]:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "PSE-V2-ROUTING-1.0":
        raise ValueError("unsupported PSE routing configuration")
    routes = payload.get("routes")
    if not isinstance(routes, dict) or set(routes) != {"AP", "SCC", "ACR", "PERC", "BDO", "AREIT", "ALI", "AC"}:
        raise ValueError("Phase A routing must contain the frozen eight-company pilot")
    return payload


def route_for(ticker: str) -> dict[str, Any]:
    try:
        return load_routes()["routes"][ticker.upper()]
    except KeyError as exc:
        raise ValueError(f"No approved PSE V2 route for {ticker}") from exc

