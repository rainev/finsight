from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app import deps
import app.routers.us_valuations as router
from app.services import valuation_service


main_module.app.dependency_overrides[deps.current_user] = lambda: {
    "sub": 7,
    "email": "calculator@example.com",
    "role": "user",
}


@pytest.fixture(scope="module")
def client():
    # These routes are static-artifact/pure-calculator paths and do not need the
    # application lifespan (DB/storage). Avoid opening/closing the suite-global pool.
    return TestClient(main_module.app)


@pytest.fixture
def staged(monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(router, '_comparison_now', lambda: datetime(2026, 8, 14, tzinfo=timezone.utc))
    root = Path("output/launch-first/batch-03-run-g/staged-public")
    monkeypatch.setattr(router, "DATA_ROOT", root)
    monkeypatch.setattr(router, "EOD_DATA_ROOT", None)
    monkeypatch.setattr(router, "SECURITY_MASTER_ROOT", None)
    return root


def test_calculator_get_and_default_post_reproduce_baseline(
    client: TestClient, staged: Path
) -> None:
    detail = client.get("/api/us-valuations/NWSA").json()
    view = client.get("/api/us-valuations/NWSA/calculator")
    assert view.status_code == 200
    assert view.json()["can_calculate"] is True

    response = client.post(
        "/api/us-valuations/NWSA/calculator",
        json={"overrides": {}, "save": False},
    )
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(
        {key: detail["scenario_range"][key] for key in ("low", "base", "high")}
    )


def test_calculator_manual_price_and_validation(client: TestClient, staged: Path) -> None:
    manual = client.post(
        "/api/us-valuations/NWSA/calculator",
        json={"overrides": {"cash_conversion": 1.1}, "manual_price": 10},
    )
    assert manual.status_code == 200
    assert manual.json()["comparison_source"] == "manual"
    assert manual.json()["manual_price"] == 10
    assert manual.json()["comparison"]["verdict"] in {"undervalued", "overvalued", "fair_value"}
    assert manual.json()["comparison"]["price"] == 10

    invalid = client.post(
        "/api/us-valuations/NWSA/calculator",
        json={"overrides": {"shares": 1}},
    )
    assert invalid.status_code == 400


def test_legacy_catalog_does_not_invent_verified_case_presets(
    client: TestClient, staged: Path
) -> None:
    view = client.get("/api/us-valuations/NWSA/calculator").json()
    assert set(view["scenario_presets"]) == {"base"}
    assert view["selected_scenario"] == "base"
    assert all("unit" in field for field in view["editable_assumptions"])
    response = client.post(
        "/api/us-valuations/NWSA/calculator",
        json={
            "selected_scenario": "low",
            "overrides": {"cash_conversion": 1.1},
            "baseline_version": view["baseline_version"],
            "recipe_version": view["recipe_version"],
        },
    )
    assert response.status_code == 400
    assert 'exact recipe' in response.json()['error']


def test_calculator_save_persists_only_user_inputs(
    client: TestClient,
    staged: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def fake_save_us(**kwargs):
        captured.update(kwargs)
        return {"id": 42}

    monkeypatch.setattr(valuation_service, "save_us", fake_save_us)
    response = client.post(
        "/api/us-valuations/NWSA/calculator",
        json={
            "overrides": {"cash_conversion": 1.1},
            "manual_price": 10,
            "save": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["saved_id"] == 42
    assert captured["ticker"] == "NWSA"
    assert captured["user_price"] == 10
    assert "split_adjusted_close" not in json.dumps(captured)
    assert "provider" not in json.dumps(captured)


def test_private_eod_yields_only_derived_public_comparison(
    client: TestClient,
    staged: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    eod = tmp_path / "eod"
    security = tmp_path / "security"
    eod.mkdir()
    security.mkdir()
    (security / "NWSA.json").write_text(
        json.dumps(
            {
                "canonical_security": "NWSA",
                "primary_listing": "NASDAQ",
                "currency": "USD",
            }
        )
    )
    (eod / "NWSA.json").write_text(
        json.dumps(
            {
                "canonical_security": "NWSA",
                "primary_listing": "NASDAQ",
                "currency": "USD",
                "split_adjusted_close": 20.0,
                "price_date": "2026-08-14",
                "provider": "private-vendor",
                "payload_hash": "a" * 64,
            }
        )
    )
    monkeypatch.setattr(router, "EOD_DATA_ROOT", eod)
    monkeypatch.setattr(router, "SECURITY_MASTER_ROOT", security)

    response = client.get("/api/us-valuations/NWSA")
    assert response.status_code == 200
    body = response.json()
    assert body["market_comparison"]["status"] == "available"
    assert body["market_comparison"]["price_date"] == "2026-08-14"
    encoded = json.dumps(body)
    assert "split_adjusted_close" not in encoded
    assert "private-vendor" not in encoded
    assert '"payload_hash"' not in encoded


def test_unavailable_company_returns_noncalculable_view(
    client: TestClient, staged: Path
) -> None:
    view = client.get("/api/us-valuations/ECHO/calculator")
    assert view.status_code == 200
    assert view.json()["can_calculate"] is False
    post = client.post("/api/us-valuations/ECHO/calculator", json={})
    assert post.status_code == 400
