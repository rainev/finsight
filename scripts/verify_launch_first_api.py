#!/usr/bin/env python3
"""Exercise staged launch-first list/detail/calculator flows through real HTTP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.security.jwt import sign_access_token


FORBIDDEN = {
    "split_adjusted_close",
    "provider",
    "payload_hash",
    "reported_inputs",
    "source_ledger",
    "governed_assumptions",
}


def _contains_forbidden(value: object) -> bool:
    if isinstance(value, dict):
        return bool(FORBIDDEN.intersection(value)) or any(
            _contains_forbidden(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_forbidden(item) for item in value)
    return False


def _call(
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    raw = None if body is None else json.dumps(body).encode()
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=raw,
        method="POST" if body is not None else "GET",
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return int(response.status), json.loads(response.read())
    except HTTPError as error:
        return int(error.code), json.loads(error.read())


def run(*, base_url: str, stage_root: Path) -> dict[str, Any]:
    token = sign_access_token(7, "launch-first@example.com", "user")
    expected = sorted(path.stem for path in Path(stage_root).glob("*.json"))
    list_status, listed = _call(base_url, "/api/us-valuations")
    tickers = sorted(row["ticker"] for row in listed["items"])
    if list_status != 200 or tickers != expected:
        raise ValueError("launch-first list response does not match the staged denominator")
    details = []
    calculators = []
    batch35_semantics = []
    for ticker in tickers:
        detail_status, detail = _call(base_url, f"/api/us-valuations/{ticker}")
        view_status, view = _call(base_url, f"/api/us-valuations/{ticker}/calculator")
        if detail_status != 200 or view_status != 200 or _contains_forbidden(detail):
            raise ValueError(f"{ticker}: detail/calculator public boundary failed")
        detail_base = detail["scenario_range"]["base"]
        if view["can_calculate"]:
            post_status, calculated = _call(
                base_url,
                f"/api/us-valuations/{ticker}/calculator",
                token=token,
                body={"overrides": {}, "save": False},
            )
            parity = post_status == 200 and calculated["result"]["base"] == detail_base
        else:
            post_status, calculated = _call(
                base_url,
                f"/api/us-valuations/{ticker}/calculator",
                token=token,
                body={"overrides": {}, "save": False},
            )
            parity = post_status == 400 and detail_base is None
        details.append(
            {
                "ticker": ticker,
                "status": detail_status,
                "availability_type": detail["availability_type"],
                "private_leak": _contains_forbidden(detail),
                "market_comparison_status": detail["market_comparison"]["status"],
            }
        )
        calculators.append(
            {
                "ticker": ticker,
                "model_family": view.get("model_family"),
                "get_status": view_status,
                "post_status": post_status,
                "default_base_parity": parity,
            }
        )
        if detail.get("public_assumptions", {}).get("forecast_policy_version") == "BATCH-35-SOL-AUDIT-REPAIR-1.2":
            expected_model = "fcff_dcf" if ticker == "WMB" else "residual_income"
            expected_family = "enterprise_fcff" if ticker == "WMB" else "residual_income"
            batch35_semantics.append({
                "ticker": ticker,
                "model_identity_parity": (
                    detail.get("model_policy", {}).get("primary") == expected_model
                    and set(detail.get("models", {})) == {expected_model}
                    and view.get("model_family") == expected_family
                    and view.get("assigned_model") == detail.get("primary_valuation_method")
                ),
                "exact_default_parity": parity,
                "wmb_base_discount_parity": ticker != "WMB" or view.get("defaults", {}).get("discount_rate") == 0.095,
            })
    representative = "NWSA" if "NWSA" in tickers else tickers[0]
    nws_status, nws = _call(base_url, f"/api/us-valuations/{representative}")
    manual_status, manual = _call(
        base_url,
        f"/api/us-valuations/{representative}/calculator",
        token=token,
        body={"overrides": {}, "manual_price": 10, "save": False},
    )
    default_status, default = _call(
        base_url,
        f"/api/us-valuations/{representative}/calculator",
        token=token,
        body={"overrides": {}, "save": False},
    )
    higher_status, higher = _call(
        base_url,
        f"/api/us-valuations/{representative}/calculator",
        token=token,
        body={"overrides": {"discount_rate": default["defaults"]["discount_rate"] + 0.01}, "save": False},
    )
    cash_status, cash = _call(
        base_url,
        f"/api/us-valuations/{representative}/calculator",
        token=token,
        body={"overrides": {"cash_conversion": 1.1}, "save": False},
    )
    if not (
        nws_status == manual_status == default_status == higher_status == cash_status == 200
        and manual["comparison_source"] == "manual"
        and higher["result"]["base"] < default["result"]["base"] < cash["result"]["base"]
    ):
        raise ValueError("launch-first manual/automatic/monotonic calculator flow failed")
    model_family_counts = {
        family: sum(row["model_family"] == family for row in calculators)
        for family in ("operating", "bank", "reit", "utility_or_equity", "equity_earnings", "residual_income", "enterprise_fcff")
    }
    equity_rows = [row for row in calculators if row["model_family"] == "equity_earnings"]
    equity_earnings_override_increases_value = True
    if equity_rows:
        equity_ticker = equity_rows[0]["ticker"]
        _, equity_default = _call(
            base_url,
            f"/api/us-valuations/{equity_ticker}/calculator",
            token=token,
            body={"overrides": {}, "save": False},
        )
        equity_status, equity_higher = _call(
            base_url,
            f"/api/us-valuations/{equity_ticker}/calculator",
            token=token,
            body={"overrides": {"normalized_earnings_factor": 1.1}, "save": False},
        )
        equity_earnings_override_increases_value = (
            equity_status == 200
            and equity_higher["result"]["base"] > equity_default["result"]["base"]
        )
    return {
        "schema_version": "FINSIGHT-LAUNCH-FIRST-REAL-API-1",
        "base_url": base_url,
        "list_status": list_status,
        "list_count": listed["count"],
        "detail_200_count": sum(row["status"] == 200 for row in details),
        "private_leak_count": sum(row["private_leak"] for row in details),
        "calculator_get_200_count": sum(row["get_status"] == 200 for row in calculators),
        "calculator_default_parity_count": sum(row["default_base_parity"] for row in calculators),
        "model_family_counts": model_family_counts,
        "automatic_eod_fixture_derived_only": not _contains_forbidden(nws),
        "manual_price_flow": manual["comparison_source"] == "manual",
        "higher_discount_lowers_value": higher["result"]["base"] < default["result"]["base"],
        "better_cash_conversion_increases_value": cash["result"]["base"] > default["result"]["base"],
        "equity_earnings_override_increases_value": equity_earnings_override_increases_value,
        "batch35_semantic_count": len(batch35_semantics),
        "batch35_model_identity_parity_count": sum(row["model_identity_parity"] for row in batch35_semantics),
        "batch35_exact_default_parity_count": sum(row["exact_default_parity"] for row in batch35_semantics),
        "batch35_wmb_base_discount_parity": all(row["wmb_base_discount_parity"] for row in batch35_semantics),
        "batch35_semantics": batch35_semantics,
        "details": details,
        "calculators": calculators,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--stage-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(base_url=args.base_url, stage_root=args.stage_root)
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    if args.output.exists() and args.output.read_bytes() != raw:
        raise FileExistsError("refusing to overwrite launch-first API receipt")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(json.dumps({key: result[key] for key in (
        "list_count", "detail_200_count", "private_leak_count",
        "calculator_get_200_count", "calculator_default_parity_count",
        "automatic_eod_fixture_derived_only", "manual_price_flow",
        "higher_discount_lowers_value", "better_cash_conversion_increases_value",
        "equity_earnings_override_increases_value",
        "batch35_semantic_count", "batch35_model_identity_parity_count",
        "batch35_exact_default_parity_count", "batch35_wmb_base_discount_parity",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
