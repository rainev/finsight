---
name: verify-current-ui-not-worktree-default
description: The current FinSight redesign is in the main checkout; a protected valuation worktree can contain an older consumer UI.
metadata: { type: feedback }
---

On 2026-09-08 the user corrected verification against the old worktree UI. The current redesign is in the main checkout's `frontend/src/pages/UsValuations.tsx` and `ValuationSwipeDeck`, while valuation-pipeline work remains in `whole-universe-greenlight`.

**Why:** An API can pass in an older frontend while breaking the actual consumer's request/response contract. The redesign expects flat low/base/high presets, `scenario` requests, per-case edits, percent/number/multiple/years units, lowercase comparison verdicts, and saved selected-case metadata.

**How to apply:** Confirm the UI against the user's current screenshot before accepting browser evidence. Preserve both checkouts' uncommitted work; use the newer frontend with an isolated staged API for acceptance. Do not merge branches or replace the redesign merely to simplify testing. Old-UI checks are backend evidence, not final acceptance of the current UI.
