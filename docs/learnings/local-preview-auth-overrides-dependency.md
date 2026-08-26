---
name: local-preview-auth-overrides-dependency
description: A fake refresh response does not authenticate FastAPI calculator POSTs; override current_user in the local verification wrapper.
metadata: { type: gotcha }
---
A local preview can look signed in after returning a synthetic `/api/auth/refresh` response while still
failing every authenticated calculator POST with `Invalid or expired access token`. The frontend stores
the synthetic token and sends it, but FastAPI independently verifies the token in the `current_user`
dependency.

**Why:** UI session bootstrap and backend authorization are separate gates. Stubbing only the former
creates a misleading preview where read-only valuation routes work but assumption calculation and save
actions fail.

**How to detect / apply:** exercise an authenticated POST in the browser, not only list/detail GETs. In
the local verification wrapper, override `deps.current_user` with a fixed test user and stub persistence
only when Docker/Postgres is unavailable. Never describe that wrapper as verification of real auth or DB
persistence. Related: [[build-deploy-gotchas]] and [[project-profile]].
