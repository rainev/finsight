"""End-to-end router tests via FastAPI's TestClient.

Auth is overridden and market assumptions / storage are stubbed so these run
without a live DB or MinIO — they exercise input validation, the resolve
logic, and response shaping. (Persistence paths use save=False.)"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app import deps
import app.routers.us_valuations as us_valuations_router
from app.services import market_service
from app.valuation.assumptions import PH


ACTIVE_DATA_ROOT = us_valuations_router.CATALOG.artifacts_root

# Any authenticated user.
main_module.app.dependency_overrides[deps.current_user] = lambda: {
    "sub": 1,
    "email": "a@b.com",
    "role": "user",
}


@pytest.fixture(scope="module")
def client():
    # Module-scoped: the DB pool is a global singleton and can't be reopened once
    # closed, so the lifespan (pool.open/close) must run exactly once here.
    orig_bucket = main_module.ensure_bucket
    orig_assumptions = market_service.get_assumptions
    main_module.ensure_bucket = lambda: None
    market_service.get_assumptions = lambda: PH
    try:
        with TestClient(main_module.app) as c:
            yield c
    finally:
        main_module.ensure_bucket = orig_bucket
        market_service.get_assumptions = orig_assumptions


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_dcf_endpoint(client):
    r = client.post(
        "/api/valuations/dcf",
        json={
            "projected_fcf": [100, 110, 121],
            "discount_rate": 0.10,
            "perpetual_growth_rate": 0.02,
            "shares_outstanding": 10,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "dcf"
    assert body["intrinsic_value"] == pytest.approx(143.18, abs=0.05)


def test_dcf_derives_discount_from_beta(client):
    # No discount_rate given, but beta 1.0 -> CAPM = 0.06 + 1*0.075 = 0.135.
    r = client.post(
        "/api/valuations/dcf",
        json={
            "base_fcf": 100,
            "growth_rate": 0.05,
            "years": 5,
            "beta": 1.0,
            "shares_outstanding": 10,
        },
    )
    assert r.status_code == 200


def test_dcf_missing_projection_is_400(client):
    r = client.post(
        "/api/valuations/dcf",
        json={"discount_rate": 0.10, "shares_outstanding": 10},
    )
    assert r.status_code == 400


def test_graham_uses_ph_yield_default(client):
    r = client.post(
        "/api/valuations/graham",
        json={"eps": 8.27, "growth_rate_pct": 9.63, "current_price": 315.32},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["intrinsic_value"] == pytest.approx(168.36, abs=0.1)
    assert body["verdict"] == "Sell"


def test_multiples_endpoint(client):
    r = client.post(
        "/api/valuations/multiples",
        json={
            "peers": [
                {"ticker": "META", "price": 669.21, "eps": 27.52},
                {"ticker": "AAPL", "price": 315.32, "eps": 8.27},
            ],
            "target_eps": 25.0,
        },
    )
    assert r.status_code == 200
    assert r.json()["detail"]["average_pe"] == pytest.approx((669.21 / 27.52 + 315.32 / 8.27) / 2)


def test_invalid_shares_is_422(client):
    # shares_outstanding must be > 0 (Pydantic validation -> 422).
    r = client.post(
        "/api/valuations/dcf",
        json={"projected_fcf": [100], "discount_rate": 0.1, "shares_outstanding": 0},
    )
    assert r.status_code == 422


def test_us_valuation_list_and_detail_share_safe_reliability(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for ticker in ("AAPL", "BAC"):
        artifact = json.loads(
            (ACTIVE_DATA_ROOT / f"{ticker}.json").read_text(
                encoding="utf-8"
            )
        )
        (tmp_path / f"{ticker}.json").write_text(
            json.dumps(artifact), encoding="utf-8"
        )
    monkeypatch.setattr(us_valuations_router, "DATA_ROOT", tmp_path)

    listed_response = client.get("/api/us-valuations")

    assert listed_response.status_code == 200
    listed = listed_response.json()
    assert listed["count"] == 2
    assert all(item["reliability"] in {"High", "Medium", "Low"} for item in listed["items"])

    details = {}
    for item in listed["items"]:
        detail_response = client.get(f"/api/us-valuations/{item['ticker']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        details[item["ticker"]] = detail
        assert detail["reliability"]["label"] == item["reliability"]
        assert set(detail["reliability"]) == {
            "label",
            "accounting_label",
            "scenario_label",
            "model_cap",
            "source_cap",
            "accounting_impact_ratio",
            "scenario_movement_ratio",
            "reasons",
        }

    assert details["BAC"]["scenario_range"]["base"] is not None
    assert details["BAC"]["reliability"]["label"] in {"High", "Medium", "Low"}


def test_us_valuation_endpoints_share_object_and_filename_identity_validation(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = json.loads(
        (ACTIVE_DATA_ROOT / "BAC.json").read_text(
            encoding="utf-8"
        )
    )
    (tmp_path / "BAC.json").write_text(json.dumps(valid), encoding="utf-8")
    (tmp_path / "BROKEN.json").write_text("{", encoding="utf-8")
    (tmp_path / "ARRAY.json").write_text("[]", encoding="utf-8")

    mismatched = json.loads(json.dumps(valid))
    (tmp_path / "MISMATCH.json").write_text(
        json.dumps(mismatched), encoding="utf-8"
    )
    invalid_filename = json.loads(json.dumps(valid))
    invalid_filename["issuer"]["ticker"] = "bad!"
    (tmp_path / "bad!.json").write_text(
        json.dumps(invalid_filename), encoding="utf-8"
    )
    monkeypatch.setattr(us_valuations_router, "DATA_ROOT", tmp_path)

    listed_response = client.get("/api/us-valuations")

    assert listed_response.status_code == 200
    listed = listed_response.json()
    assert listed["count"] == 1
    assert [item["ticker"] for item in listed["items"]] == ["BAC"]

    detail_response = client.get("/api/us-valuations/BAC")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    item = listed["items"][0]
    assert detail["issuer"]["ticker"] == item["ticker"]
    assert detail["scenario_range"]["base"] == item["base"]
    assert detail["review"]["publication_state"] == item["publication_state"]
    assert detail["reliability"]["label"] == item["reliability"]
    assert detail["availability_type"] == item["availability_type"]
    assert detail["confidence"] == item["confidence"]

    for ticker, error in (
        ("BROKEN", "U.S. valuation artifact is invalid"),
        ("ARRAY", "U.S. valuation artifact is invalid"),
        ("MISMATCH", "U.S. valuation artifact identity mismatch"),
    ):
        response = client.get(f"/api/us-valuations/{ticker}")
        assert response.status_code == 500
        assert response.json() == {"error": error}


@pytest.mark.parametrize(
    ("ticker", "payload", "expected_error"),
    [
        ("BROKEN", "{", "U.S. valuation artifact is invalid"),
        ("ARRAY", "[]", "U.S. valuation artifact is invalid"),
        ("MISMATCH", None, "U.S. valuation artifact identity mismatch"),
    ],
)
def test_us_valuation_detail_returns_controlled_artifact_errors(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ticker: str,
    payload: str | None,
    expected_error: str,
) -> None:
    if payload is None:
        mismatched = json.loads(
            (ACTIVE_DATA_ROOT / "BAC.json").read_text(
                encoding="utf-8"
            )
        )
        payload = json.dumps(mismatched)
    (tmp_path / f"{ticker}.json").write_text(payload, encoding="utf-8")
    monkeypatch.setattr(us_valuations_router, "DATA_ROOT", tmp_path)

    response = client.get(f"/api/us-valuations/{ticker}")

    assert response.status_code == 500
    assert response.json() == {"error": expected_error}
