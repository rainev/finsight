---
name: pse-staged-catalogs-must-not-enter-serving-root
description: Keep unconfirmed PSE candidate catalogs outside the API serving root because history scans catalog directories independently of active.json.
metadata: { type: gotcha }
---
An unchanged `active.json` does not by itself keep an unconfirmed PSE candidate private. The PSE history endpoint scans
catalog directories containing manifests, so a staged candidate under `backend/app/data/pse_valuation_catalogs/` can
appear in history before activation.

**Why:** List and detail use the active pointer, while history discovers catalogs by directory. Those are different
publication boundaries.

**How to detect / apply:** Build unconfirmed cumulative candidates under `output/pse-valuation-candidates/`, verify them
with an isolated API whose catalog root points there, and copy/select them in the serving root only after explicit
activation authorization. Recheck `backend/app/routers/pse_valuations.py` before relying on this learning because the
history implementation may later change.
