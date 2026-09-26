---
name: pse-staged-http-tests-isolate-auth-overrides
description: PSE staged HTTP tests must isolate FastAPI auth overrides before asserting a real 401/200 flow.
metadata: { type: gotcha }
---
The full backend suite can leave `app.dependency_overrides` populated by earlier API tests. A later `TestClient` request without a bearer token may then return 200 even though the real PSE route requires authentication.

**Why:** `dependency_overrides` is mutable global FastAPI application state shared across tests.

**How to detect / apply:** Run the staged API test within the full suite, not only by itself. Before checking unauthenticated 401 and authenticated 200, isolate `app.dependency_overrides` with `monkeypatch.setattr(app, "dependency_overrides", {})` so pytest restores the prior mapping afterward. See `backend/tests/test_pse_internal_refresh.py`.
